#!/usr/bin/env python3
"""Compare two builds of a Max for Live device and report every Live-visible difference.

  compare_device_builds.py BASELINE CANDIDATE [--device NAME] [--fail-on-reported] [--max-diff-lines N]

BASELINE and CANDIDATE are each one build of one device, given as either
  - a directory: searched (recursively) for NAME.maxpat, the unfrozen NAME.amxd, the frozen NAME[-version].amxd,
    the .js scripts next to the unfrozen .amxd and the .adv presets next to each .amxd. Works on a saved baseline
    folder and on an 2sl-dsp checkout alike (pass --device there: it has several devices); or
  - one file (.maxpat or .amxd): that patch, with the .js and .adv files in its folder.
NAME defaults to the stem of the only .maxpat found.

Categories (GATED ones make the exit status non-zero when they differ; the others are reported only, and gate
too with --fail-on-reported):
  (a) GATED     the Live parameter table, in order, plus device width and device type
  (b) reported  boxes as signatures (box ids and patching rects ignored; embedded gen~ code included)
  (c) reported  wires as (source, outlet) -> (destination, inlet), a multiset over box identities
  (d) reported  generated JS, exact text
  (e) GATED     Live presets (.adv): parameter Ids / names / values and the stored-only blob
  (f) reported  .amxd containers: header, embedded patch, frozen contents (mdat timestamps and offsets ignored)

Exit status: 0 no gated difference, 1 gated difference (or any difference with --fail-on-reported), 2 the inputs
could not be read. Python 3.9+, standard library only.
"""
import argparse
import difflib
import gzip
import json
import os
import struct
import sys
import xml.etree.ElementTree as ElementTree
from collections import Counter

EXIT_STATUS_SAME = 0
EXIT_STATUS_DIFFERENT = 1
EXIT_STATUS_BAD_INPUT = 2

AMXD_DEVICE_TYPE_NAMES = {b"aaaa": "audio", b"mmmm": "midi", b"iiii": "instrument"}
DIRECTORY_NAMES_NEVER_SEARCHED = {".git", "__pycache__", "node_modules", "references"}
# box attributes that only place a box in the patching (editing) view or name it inside one file
BOX_ATTRIBUTES_IGNORED_IN_SIGNATURES = {"id", "patching_rect"}
# patcher attributes that only describe the editor window
PATCHER_ATTRIBUTES_IGNORED_IN_SIGNATURES = {"rect", "boxes", "lines"}
PATCHLINE_ATTRIBUTES_IGNORED = {"source", "destination", "midpoints"}

# The parameter table's columns. Max leaves an attribute out of a saved patch when it has its default value; these
# defaults are filled in so that writing a default explicitly is not a gated difference (category (b) still
# reports the change of representation). Attributes whose default depends on the object class are not filled in.
PARAMETER_ATTRIBUTE_DEFAULTS = {
    "parameter_mmin": 0.0,
    "parameter_exponent": 1.0,
    "parameter_initial_enable": 0,
    "parameter_invisible": 0,
    "parameter_enum": [],
}
PARAMETER_VALUEOF_COLUMNS = [
    "parameter_longname", "parameter_shortname", "parameter_type", "parameter_enum", "parameter_mmin",
    "parameter_mmax", "parameter_exponent", "parameter_unitstyle", "parameter_units", "parameter_steps",
    "parameter_initial", "parameter_initial_enable", "parameter_invisible", "parameter_annotation_name",
    "parameter_info", "parameter_linknames", "parameter_modmode", "parameter_order",
]
PARAMETER_BOX_COLUMNS = [
    "maxclass", "varname", "parameter_enable", "automation", "automationon", "annotation", "annotation_name",
    "presentation", "presentation_rect",
]


class BuildInputError(Exception):
    """A build could not be found or read: the message says which file and why."""


# ---- reading builds -------------------------------------------------------------------------------------------

def read_amxd(path):
    """An .amxd file as {"device_type", "meta_value", "is_frozen", "patch", "frozen_entries"}."""
    with open(path, "rb") as amxd_file:
        file_bytes = amxd_file.read()
    if len(file_bytes) < 32 or file_bytes[:4] != b"ampf" or file_bytes[12:16] != b"meta" or file_bytes[24:28] != b"ptch":
        raise BuildInputError(f"{path}: not an .amxd file (no ampf / meta / ptch header)")
    device_type_code = file_bytes[8:12]
    meta_value = struct.unpack("<I", file_bytes[20:24])[0]
    body_length = struct.unpack("<I", file_bytes[28:32])[0]
    body = file_bytes[32:32 + body_length]
    if len(body) != body_length:
        raise BuildInputError(f"{path}: header says the patch is {body_length} bytes, the file has {len(body)}")
    amxd = {"device_type": AMXD_DEVICE_TYPE_NAMES.get(device_type_code, repr(device_type_code)),
            "meta_value": meta_value, "is_frozen": body[:4] == b"mx@c", "frozen_entries": None}
    if not amxd["is_frozen"]:
        amxd["patch"] = parse_patch_json(body.rstrip(b"\0"), path)
        return amxd
    amxd["frozen_entries"] = read_frozen_container_entries(body, path)
    patch_entries = [entry for entry in amxd["frozen_entries"] if entry["flag"] == 17]
    if len(patch_entries) != 1:
        raise BuildInputError(f"{path}: frozen device has {len(patch_entries)} main patch entries (flag 17), expected 1")
    amxd["patch"] = parse_patch_json(patch_entries[0]["data"].rstrip(b"\0"), path)
    return amxd


def read_frozen_container_entries(container, path):
    """The files in a frozen device's mx@c container, in directory order: {type, fnam, sz32, of32, vers, flag,
    mdat, data}. The layout is the one Max's Freeze writes (2sl-dsp tools/amxd.py writes and reads the same)."""
    directory_offset = struct.unpack(">I", container[12:16])[0]
    if container[directory_offset:directory_offset + 4] != b"dlst":
        raise BuildInputError(f"{path}: frozen device has no dlst directory at offset {directory_offset}")
    directory_end = directory_offset + struct.unpack(">I", container[directory_offset + 4:directory_offset + 8])[0]
    entries, entry_position = [], directory_offset + 8
    while entry_position < directory_end:
        if container[entry_position:entry_position + 4] != b"dire":
            raise BuildInputError(f"{path}: frozen directory entry at {entry_position} is not a 'dire' field")
        entry_size = struct.unpack(">I", container[entry_position + 4:entry_position + 8])[0]
        entry_fields_bytes, field_position, entry = container[entry_position + 8:entry_position + entry_size], 0, {}
        while field_position < len(entry_fields_bytes):
            field_tag = entry_fields_bytes[field_position:field_position + 4].decode("ascii", "replace")
            field_size = struct.unpack(">I", entry_fields_bytes[field_position + 4:field_position + 8])[0]
            if field_size < 8:
                raise BuildInputError(f"{path}: frozen directory field {field_tag!r} has impossible size {field_size}")
            field_value = entry_fields_bytes[field_position + 8:field_position + field_size]
            if field_tag in ("type", "fnam"):
                entry[field_tag] = field_value.rstrip(b"\0").decode("utf-8")
            else:
                entry[field_tag] = struct.unpack(">I", field_value)[0]
            field_position += field_size
        for required_field in ("type", "fnam", "sz32", "of32", "flag"):
            if required_field not in entry:
                raise BuildInputError(f"{path}: frozen directory entry {entry} has no {required_field!r} field")
        entry["data"] = container[entry["of32"]:entry["of32"] + entry["sz32"]]
        if len(entry["data"]) != entry["sz32"]:
            raise BuildInputError(f"{path}: frozen file {entry['fnam']!r} runs past the end of the container")
        entries.append(entry)
        entry_position += entry_size
    return entries


def parse_patch_json(json_bytes, path):
    try:
        patch = json.loads(json_bytes)
    except ValueError as problem:
        raise BuildInputError(f"{path}: patch is not valid JSON: {problem}")
    if not isinstance(patch, dict) or not isinstance(patch.get("patcher"), dict):
        raise BuildInputError(f"{path}: patch JSON has no top-level 'patcher' object")
    return patch


def read_patch_file(path):
    if path.endswith(".amxd"):
        return read_amxd(path)["patch"]
    with open(path, "rb") as patch_file:
        return parse_patch_json(patch_file.read(), path)


def read_live_preset(path):
    """A Live device preset (.adv: gzipped XML) as the parts compared: the parameter list (gated), the stored-only
    blob (gated), the device file reference (reported) and the rest of the XML (reported)."""
    try:
        with gzip.open(path, "rb") as preset_file:
            xml_bytes = preset_file.read()
    except OSError as problem:
        raise BuildInputError(f"{path}: not a gzipped Live preset: {problem}")
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as problem:
        raise BuildInputError(f"{path}: preset XML does not parse: {problem}")
    device_elements = [child for child in root if child.tag.startswith("MxDevice")]
    if len(device_elements) != 1:
        raise BuildInputError(f"{path}: preset has {len(device_elements)} MxDevice* elements, expected 1")
    device_element = device_elements[0]
    parameter_list_element = device_element.find("ParameterList/ParameterList")
    if parameter_list_element is None:
        raise BuildInputError(f"{path}: preset has no ParameterList/ParameterList")
    parameters = [live_preset_parameter_summary(parameter_element) for parameter_element in parameter_list_element]
    blob_element = device_element.find("BlobSlot/Value/MxDBlob/Blob")
    stored_only_blob_text = None
    if blob_element is not None:
        blob_hex_digits = "".join((blob_element.text or "").split())
        try:
            stored_only_blob_text = bytes.fromhex(blob_hex_digits).rstrip(b"\0").decode("utf-8")
        except ValueError as problem:
            raise BuildInputError(f"{path}: stored-only blob is not hex-encoded UTF-8: {problem}")
    file_reference_element = device_element.find("PatchSlot/Value/MxPatchRef/FileRef")
    file_reference = {} if file_reference_element is None else {
        child.tag: child.get("Value") for child in file_reference_element}
    # everything else, as text, with the gated and the file-reference parts taken out
    remainder_root = ElementTree.fromstring(xml_bytes)
    remainder_device = [child for child in remainder_root if child.tag.startswith("MxDevice")][0]
    for removable_path in ("ParameterList/ParameterList", "BlobSlot/Value/MxDBlob/Blob", "PatchSlot/Value/MxPatchRef/FileRef"):
        removable_element = remainder_device.find(removable_path)
        if removable_element is not None:
            removable_element.clear()
    return {"device_element_tag": device_element.tag, "parameters": parameters,
            "stored_only_blob_text": stored_only_blob_text, "file_reference": file_reference,
            "remaining_xml_text": ElementTree.tostring(remainder_root, encoding="unicode")}


def live_preset_parameter_summary(parameter_element):
    def value_at(element_path):
        found = parameter_element.find(element_path)
        return None if found is None else found.get("Value")
    summary = {"element": parameter_element.tag, "Id": parameter_element.get("Id")}
    for element_path in ("Index", "Type", "Name", "ShortName", "MinValue", "MaxValue", "Default", "IsStored",
                         "IsUndoable", "ModType", "Timeable/Manual", "Timeable/MidiControllerRange/Min",
                         "Timeable/MidiControllerRange/Max"):
        summary[element_path] = value_at(element_path)
    names_element = parameter_element.find("Names")
    summary["Names"] = None if names_element is None else [
        (name_element.get("Id"), name_element.find("Name").get("Value") if name_element.find("Name") is not None else None)
        for name_element in names_element]
    return summary


def find_files_under(search_root, extension):
    found_paths = []
    for directory_path, directory_names, file_names in os.walk(search_root):
        directory_names[:] = sorted(name for name in directory_names
                                    if name not in DIRECTORY_NAMES_NEVER_SEARCHED and not name.endswith(" Project"))
        found_paths.extend(os.path.join(directory_path, name) for name in sorted(file_names) if name.endswith(extension))
    return found_paths


def resolve_build(build_path, device_name):
    """One build's files: {"label", "maxpat", "unfrozen_amxd", "frozen_amxd", "scripts": {name: path},
    "preset_sets": {set label: {file name: path}}}. Fails loudly when a role is ambiguous."""
    build_path = os.path.abspath(build_path)
    if not os.path.exists(build_path):
        raise BuildInputError(f"{build_path}: no such file or directory")
    if os.path.isfile(build_path):
        if not build_path.endswith((".maxpat", ".amxd")):
            raise BuildInputError(f"{build_path}: a build given as one file must be a .maxpat or an .amxd")
        folder = os.path.dirname(build_path)
        build = {"label": build_path, "maxpat": None, "unfrozen_amxd": None, "frozen_amxd": None}
        if build_path.endswith(".maxpat"):
            build["maxpat"] = build_path
        elif read_amxd(build_path)["is_frozen"]:
            build["frozen_amxd"] = build_path
        else:
            build["unfrozen_amxd"] = build_path
        build["scripts"] = {name: os.path.join(folder, name) for name in sorted(os.listdir(folder)) if name.endswith(".js")}
        build["preset_sets"] = {"presets beside " + os.path.basename(build_path): {
            name: os.path.join(folder, name) for name in sorted(os.listdir(folder)) if name.endswith(".adv")}}
        return build

    maxpat_paths = find_files_under(build_path, ".maxpat")
    if device_name is None:
        if len(maxpat_paths) != 1:
            raise BuildInputError(f"{build_path}: found {len(maxpat_paths)} .maxpat files, so pass --device NAME "
                                  f"to say which device: {[os.path.relpath(p, build_path) for p in maxpat_paths]}")
        device_name = os.path.splitext(os.path.basename(maxpat_paths[0]))[0]
    matching_maxpats = [p for p in maxpat_paths if os.path.basename(p) == device_name + ".maxpat"]
    if len(matching_maxpats) > 1:
        raise BuildInputError(f"{build_path}: {len(matching_maxpats)} files named {device_name}.maxpat: {matching_maxpats}")
    unfrozen_amxd_paths, frozen_amxd_paths = [], []
    for amxd_path in find_files_under(build_path, ".amxd"):
        amxd_stem = os.path.splitext(os.path.basename(amxd_path))[0]
        if amxd_stem != device_name and not amxd_stem.startswith(device_name + "-"):
            continue
        is_frozen = read_amxd(amxd_path)["is_frozen"]
        if is_frozen:
            frozen_amxd_paths.append(amxd_path)
        elif amxd_stem == device_name:
            unfrozen_amxd_paths.append(amxd_path)
    for role_name, role_paths in (("unfrozen", unfrozen_amxd_paths), ("frozen", frozen_amxd_paths)):
        if len(role_paths) > 1:
            raise BuildInputError(f"{build_path}: {len(role_paths)} {role_name} .amxd files for {device_name} (stale "
                                  f"builds? delete them or point at a narrower folder): {role_paths}")
    build = {"label": f"{build_path} (device {device_name})",
             "maxpat": matching_maxpats[0] if matching_maxpats else None,
             "unfrozen_amxd": unfrozen_amxd_paths[0] if unfrozen_amxd_paths else None,
             "frozen_amxd": frozen_amxd_paths[0] if frozen_amxd_paths else None,
             "scripts": {}, "preset_sets": {}}
    if not (build["maxpat"] or build["unfrozen_amxd"] or build["frozen_amxd"]):
        raise BuildInputError(f"{build_path}: no {device_name}.maxpat and no {device_name} .amxd found")
    if build["unfrozen_amxd"]:
        script_folder = os.path.dirname(build["unfrozen_amxd"])
        build["scripts"] = {name: os.path.join(script_folder, name)
                            for name in sorted(os.listdir(script_folder)) if name.endswith(".js")}
    for preset_set_label, amxd_path in (("development presets (beside the unfrozen .amxd)", build["unfrozen_amxd"]),
                                        ("release presets (beside the frozen .amxd)", build["frozen_amxd"])):
        if amxd_path:
            amxd_folder = os.path.dirname(amxd_path)
            build["preset_sets"][preset_set_label] = {
                name: os.path.join(amxd_folder, name) for name in sorted(os.listdir(amxd_folder)) if name.endswith(".adv")}
    return build


def primary_patch_of_build(build):
    """The patch the device-level categories (a)-(c) read: the .maxpat, else the unfrozen, else the frozen .amxd."""
    for role in ("maxpat", "unfrozen_amxd", "frozen_amxd"):
        if build[role]:
            return build[role], read_patch_file(build[role])
    raise BuildInputError(f"{build['label']}: no patch to read")


# ---- normalising ----------------------------------------------------------------------------------------------

def normalised_json_value(value):
    """Numbers as floats (Max writes 2 and 2.0 interchangeably), everything else as is, recursively."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return [normalised_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: normalised_json_value(item) for key, item in value.items()}
    return value


def canonical_text(value):
    return json.dumps(normalised_json_value(value), sort_keys=True, ensure_ascii=False)


def boxes_in_patch_order(patcher, path_prefix=""):
    """Every box, depth first through embedded patchers, as (nesting path, box dict)."""
    for wrapped_box in patcher.get("boxes", []):
        box = wrapped_box["box"]
        yield path_prefix, box
        if isinstance(box.get("patcher"), dict):
            yield from boxes_in_patch_order(box["patcher"], path_prefix + box_short_label(box) + " / ")


def box_short_label(box):
    valueof = box.get("saved_attribute_attributes", {}).get("valueof", {})
    parts = [box.get("maxclass", "?")]
    if box.get("text"):
        parts.append(repr(box["text"]))
    if box.get("varname"):
        parts.append("varname=" + box["varname"])
    if valueof.get("parameter_longname"):
        parts.append("longname=" + valueof["parameter_longname"])
    if box.get("filename"):
        parts.append("file=" + box["filename"])
    return " ".join(parts)


def box_signature(box):
    """A box without its id and patching rect; an embedded patcher becomes its own boxes' signatures (a sorted
    multiset) and its wires, so gen~ code is part of the signature and box ids inside it are not."""
    signature = {}
    for attribute_name, attribute_value in box.items():
        if attribute_name in BOX_ATTRIBUTES_IGNORED_IN_SIGNATURES:
            continue
        if attribute_name == "patcher" and isinstance(attribute_value, dict):
            signature["patcher"] = patcher_signature(attribute_value)
        else:
            signature[attribute_name] = normalised_json_value(attribute_value)
    return signature


def patcher_signature(patcher):
    attributes = {name: normalised_json_value(value) for name, value in patcher.items()
                  if name not in PATCHER_ATTRIBUTES_IGNORED_IN_SIGNATURES}
    return {"attributes": attributes,
            "boxes": sorted(canonical_text(box_signature(box["box"])) for box in patcher.get("boxes", [])),
            "wires": sorted(wire_multiset(patcher).elements())}


def box_identity(box):
    """What a wire end names: the box's kind and names, not its every attribute (so a changed colour does not
    look like a rewired box)."""
    valueof = box.get("saved_attribute_attributes", {}).get("valueof", {})
    return canonical_text({"maxclass": box.get("maxclass"), "text": box.get("text"), "varname": box.get("varname"),
                           "filename": box.get("filename"), "longname": valueof.get("parameter_longname")})


def wire_multiset(patcher):
    identity_by_box_id = {wrapped["box"]["id"]: box_identity(wrapped["box"]) for wrapped in patcher.get("boxes", [])}
    wires = Counter()
    for wrapped_line in patcher.get("lines", []):
        patchline = wrapped_line["patchline"]
        source_id, source_outlet = patchline["source"]
        destination_id, destination_inlet = patchline["destination"]
        for end_id in (source_id, destination_id):
            if end_id not in identity_by_box_id:
                raise BuildInputError(f"a patchline names box {end_id!r}, which the patcher does not have")
        extra_attributes = {name: value for name, value in patchline.items() if name not in PATCHLINE_ATTRIBUTES_IGNORED}
        wires[canonical_text([identity_by_box_id[source_id], int(source_outlet), identity_by_box_id[destination_id],
                              int(destination_inlet), extra_attributes])] += 1
    return wires


def wire_description(wire_text):
    source_identity, source_outlet, destination_identity, destination_inlet, extra_attributes = json.loads(wire_text)

    def identity_label(identity_text):
        identity = json.loads(identity_text)
        return box_short_label({"maxclass": identity["maxclass"], "text": identity["text"], "varname": identity["varname"],
                                "filename": identity["filename"],
                                "saved_attribute_attributes": {"valueof": {"parameter_longname": identity["longname"]}}
                                if identity["longname"] else {}})
    extra_text = f"  {extra_attributes}" if extra_attributes else ""
    return (f"[{identity_label(source_identity)}] outlet {int(source_outlet)} -> "
            f"[{identity_label(destination_identity)}] inlet {int(destination_inlet)}{extra_text}")


def parameter_table(patch):
    """The device's Live parameters in patch order: one row (a dict of columns) per box with a valueof."""
    rows = []
    for nesting_path, box in boxes_in_patch_order(patch["patcher"]):
        valueof = box.get("saved_attribute_attributes", {}).get("valueof")
        if not valueof and not box.get("parameter_enable"):
            continue
        valueof = valueof or {}
        row = {"nesting": nesting_path}
        for column in PARAMETER_BOX_COLUMNS:
            row[column] = normalised_json_value(box.get(column))
        for column in PARAMETER_VALUEOF_COLUMNS:
            row[column] = normalised_json_value(valueof.get(column, PARAMETER_ATTRIBUTE_DEFAULTS.get(column)))
        for other_column in sorted(set(valueof) - set(PARAMETER_VALUEOF_COLUMNS)):
            row["valueof." + other_column] = normalised_json_value(valueof[other_column])
        rows.append(row)
    return rows


def parameter_row_key(row):
    return row["parameter_longname"] or f"(varname {row['varname']})"


# ---- reporting ------------------------------------------------------------------------------------------------

class ComparisonReport:
    def __init__(self, maximum_diff_lines):
        self.maximum_diff_lines = maximum_diff_lines
        self.difference_counts = {}
        self.gated_categories = set()
        self.lines = []

    def begin_category(self, category_title, gated):
        self.current_category = category_title
        self.difference_counts[category_title] = 0
        if gated:
            self.gated_categories.add(category_title)
        self.lines.append("")
        self.lines.append(f"== {category_title} [{'GATED' if gated else 'reported'}]")

    def difference(self, message):
        self.difference_counts[self.current_category] += 1
        self.lines.append("  DIFF " + message)

    def note(self, message):
        self.lines.append("  " + message)

    def text_diff(self, label, baseline_text, candidate_text):
        diff_lines = list(difflib.unified_diff(baseline_text.splitlines(), candidate_text.splitlines(),
                                               "baseline/" + label, "candidate/" + label, lineterm="", n=2))
        for diff_line in diff_lines[:self.maximum_diff_lines]:
            self.lines.append("       " + diff_line)
        if len(diff_lines) > self.maximum_diff_lines:
            self.lines.append(f"       ... {len(diff_lines) - self.maximum_diff_lines} more diff lines "
                              f"(--max-diff-lines to see them)")

    def close_category(self):
        if self.difference_counts[self.current_category] == 0:
            self.lines.append("  same")


def compare_value_dicts(report, label, baseline_values, candidate_values):
    for key in sorted(set(baseline_values) | set(candidate_values)):
        baseline_value, candidate_value = baseline_values.get(key, "(absent)"), candidate_values.get(key, "(absent)")
        if baseline_value != candidate_value:
            report.difference(f"{label}: {key}: {baseline_value!r} -> {candidate_value!r}")


def compare_parameter_tables(report, baseline_patch, candidate_patch, baseline_build, candidate_build):
    report.begin_category("(a) Live parameter table, device width and type", gated=True)
    for patcher_attribute in ("devicewidth",):
        baseline_value = normalised_json_value(baseline_patch["patcher"].get(patcher_attribute))
        candidate_value = normalised_json_value(candidate_patch["patcher"].get(patcher_attribute))
        if baseline_value != candidate_value:
            report.difference(f"device {patcher_attribute}: {baseline_value!r} -> {candidate_value!r}")
    for role in ("unfrozen_amxd", "frozen_amxd"):
        baseline_type = read_amxd(baseline_build[role])["device_type"] if baseline_build[role] else "(no file)"
        candidate_type = read_amxd(candidate_build[role])["device_type"] if candidate_build[role] else "(no file)"
        if baseline_type != candidate_type:
            report.difference(f"device type of the {role.replace('_', ' ')}: {baseline_type} -> {candidate_type}")
    baseline_rows, candidate_rows = parameter_table(baseline_patch), parameter_table(candidate_patch)
    report.note(f"{len(baseline_rows)} parameters in the baseline, {len(candidate_rows)} in the candidate")
    for side_label, rows in (("baseline", baseline_rows), ("candidate", candidate_rows)):
        key_counts = Counter(parameter_row_key(row) for row in rows)
        for duplicated_key in sorted(key for key, count in key_counts.items() if count > 1):
            report.difference(f"{side_label}: parameter long name {duplicated_key!r} is used {key_counts[duplicated_key]} times")
    baseline_order = [parameter_row_key(row) for row in baseline_rows]
    candidate_order = [parameter_row_key(row) for row in candidate_rows]
    for missing_key in [key for key in baseline_order if key not in candidate_order]:
        report.difference(f"parameter {missing_key!r} is only in the baseline")
    for added_key in [key for key in candidate_order if key not in baseline_order]:
        report.difference(f"parameter {added_key!r} is only in the candidate")
    common_baseline_order = [key for key in baseline_order if key in candidate_order]
    common_candidate_order = [key for key in candidate_order if key in baseline_order]
    if common_baseline_order != common_candidate_order:
        report.difference("parameter order differs:")
        report.text_diff("parameter order", "\n".join(common_baseline_order), "\n".join(common_candidate_order))
    candidate_rows_by_key = {parameter_row_key(row): row for row in candidate_rows}
    for baseline_row in baseline_rows:
        key = parameter_row_key(baseline_row)
        if key in candidate_rows_by_key:
            compare_value_dicts(report, f"parameter {key!r}", baseline_row, candidate_rows_by_key[key])
    report.close_category()


def compare_boxes(report, baseline_patch, candidate_patch):
    report.begin_category("(b) boxes (ids and patching rects ignored)", gated=False)
    baseline_boxes = [wrapped["box"] for wrapped in baseline_patch["patcher"]["boxes"]]
    candidate_boxes = [wrapped["box"] for wrapped in candidate_patch["patcher"]["boxes"]]
    report.note(f"{len(baseline_boxes)} top-level boxes in the baseline, {len(candidate_boxes)} in the candidate")
    compare_value_dicts(report, "top-level patcher attribute",
                        {k: normalised_json_value(v) for k, v in baseline_patch["patcher"].items() if k not in PATCHER_ATTRIBUTES_IGNORED_IN_SIGNATURES},
                        {k: normalised_json_value(v) for k, v in candidate_patch["patcher"].items() if k not in PATCHER_ATTRIBUTES_IGNORED_IN_SIGNATURES})
    baseline_signatures = Counter(canonical_text(box_signature(box)) for box in baseline_boxes)
    candidate_signatures = Counter(canonical_text(box_signature(box)) for box in candidate_boxes)
    only_baseline = baseline_signatures - candidate_signatures
    only_candidate = candidate_signatures - baseline_signatures
    # pair the changed boxes by identity, so a changed box reads as attribute changes rather than remove + add
    unpaired_candidate = Counter(only_candidate)
    for baseline_signature_text in sorted(only_baseline.elements()):
        baseline_signature = json.loads(baseline_signature_text)
        baseline_identity = box_identity(baseline_signature)
        partner_text = next((text for text in sorted(unpaired_candidate.elements())
                             if box_identity(json.loads(text)) == baseline_identity), None)
        if partner_text is None:
            report.difference(f"box only in the baseline: [{box_short_label(baseline_signature)}]")
            continue
        unpaired_candidate[partner_text] -= 1
        unpaired_candidate += Counter()
        partner_signature = json.loads(partner_text)
        report.difference(f"box changed: [{box_short_label(baseline_signature)}]")
        for attribute_name in sorted(set(baseline_signature) | set(partner_signature)):
            if baseline_signature.get(attribute_name) == partner_signature.get(attribute_name):
                continue
            if attribute_name == "patcher":
                report.note(f"       embedded patcher differs:")
                report.text_diff("embedded patcher", embedded_patcher_text(baseline_signature["patcher"]),
                                 embedded_patcher_text(partner_signature["patcher"]))
            else:
                report.note(f"       {attribute_name}: {baseline_signature.get(attribute_name, '(absent)')!r} -> "
                            f"{partner_signature.get(attribute_name, '(absent)')!r}")
    for candidate_signature_text in sorted(unpaired_candidate.elements()):
        report.difference(f"box only in the candidate: [{box_short_label(json.loads(candidate_signature_text))}]")
    report.close_category()


def embedded_patcher_text(signature):
    """An embedded patcher's signature as readable lines (codebox code unescaped), for a text diff."""
    text_lines = ["attributes " + canonical_text(signature["attributes"])]
    for box_text in signature["boxes"]:
        box = json.loads(box_text)
        code = box.pop("code", None)
        text_lines.append("box " + canonical_text(box))
        if code is not None:
            text_lines.extend("    | " + code_line for code_line in code.splitlines())
    text_lines.extend("wire " + wire_text for wire_text in signature["wires"])
    return "\n".join(text_lines)


def compare_wires(report, baseline_patch, candidate_patch):
    report.begin_category("(c) wires (between box identities, outlet -> inlet)", gated=False)
    baseline_wires, candidate_wires = wire_multiset(baseline_patch["patcher"]), wire_multiset(candidate_patch["patcher"])
    report.note(f"{sum(baseline_wires.values())} top-level wires in the baseline, {sum(candidate_wires.values())} in the candidate")
    for wire_text in sorted((baseline_wires - candidate_wires).elements()):
        report.difference("wire only in the baseline: " + wire_description(wire_text))
    for wire_text in sorted((candidate_wires - baseline_wires).elements()):
        report.difference("wire only in the candidate: " + wire_description(wire_text))
    report.close_category()


def read_text_file(path):
    with open(path, "rb") as text_file:
        return text_file.read().decode("utf-8")


def compare_scripts(report, baseline_build, candidate_build):
    report.begin_category("(d) generated JS (exact text)", gated=False)
    baseline_scripts, candidate_scripts = baseline_build["scripts"], candidate_build["scripts"]
    report.note(f"baseline scripts: {sorted(baseline_scripts)}; candidate scripts: {sorted(candidate_scripts)}")
    for script_name in sorted(set(baseline_scripts) | set(candidate_scripts)):
        if script_name not in candidate_scripts:
            report.difference(f"{script_name}: only in the baseline")
        elif script_name not in baseline_scripts:
            report.difference(f"{script_name}: only in the candidate")
        else:
            baseline_text = read_text_file(baseline_scripts[script_name])
            candidate_text = read_text_file(candidate_scripts[script_name])
            if baseline_text != candidate_text:
                report.difference(f"{script_name}: text differs")
                report.text_diff(script_name, baseline_text, candidate_text)
    report.close_category()


def compare_live_presets(report, baseline_build, candidate_build):
    report.begin_category("(e) Live presets (.adv): parameters and stored-only blob", gated=True)
    remainder_differences = []
    for preset_set_label in sorted(set(baseline_build["preset_sets"]) | set(candidate_build["preset_sets"])):
        baseline_presets = baseline_build["preset_sets"].get(preset_set_label, {})
        candidate_presets = candidate_build["preset_sets"].get(preset_set_label, {})
        report.note(f"{preset_set_label}: {len(baseline_presets)} in the baseline, {len(candidate_presets)} in the candidate")
        for preset_name in sorted(set(baseline_presets) | set(candidate_presets)):
            label = f"{preset_set_label}: {preset_name}"
            if preset_name not in candidate_presets:
                report.difference(f"{label}: only in the baseline")
                continue
            if preset_name not in baseline_presets:
                report.difference(f"{label}: only in the candidate")
                continue
            baseline_preset = read_live_preset(baseline_presets[preset_name])
            candidate_preset = read_live_preset(candidate_presets[preset_name])
            if baseline_preset["device_element_tag"] != candidate_preset["device_element_tag"]:
                report.difference(f"{label}: device element {baseline_preset['device_element_tag']} -> "
                                  f"{candidate_preset['device_element_tag']}")
            baseline_parameters, candidate_parameters = baseline_preset["parameters"], candidate_preset["parameters"]
            if [p["Name"] for p in baseline_parameters] != [p["Name"] for p in candidate_parameters]:
                report.difference(f"{label}: parameter list differs:")
                report.text_diff(preset_name + " parameter names", "\n".join(str(p["Name"]) for p in baseline_parameters),
                                 "\n".join(str(p["Name"]) for p in candidate_parameters))
            candidate_parameters_by_name = {p["Name"]: p for p in candidate_parameters}
            for baseline_parameter in baseline_parameters:
                candidate_parameter = candidate_parameters_by_name.get(baseline_parameter["Name"])
                if candidate_parameter is not None:
                    compare_value_dicts(report, f"{label}: {baseline_parameter['Name']!r}", baseline_parameter, candidate_parameter)
            if baseline_preset["stored_only_blob_text"] != candidate_preset["stored_only_blob_text"]:
                report.difference(f"{label}: stored-only blob {baseline_preset['stored_only_blob_text']!r} -> "
                                  f"{candidate_preset['stored_only_blob_text']!r}")
            for reference_key in sorted(set(baseline_preset["file_reference"]) | set(candidate_preset["file_reference"])):
                baseline_value = baseline_preset["file_reference"].get(reference_key)
                candidate_value = candidate_preset["file_reference"].get(reference_key)
                if baseline_value != candidate_value:
                    remainder_differences.append(f"{label}: device file reference {reference_key}: {baseline_value!r} -> {candidate_value!r}")
            if baseline_preset["remaining_xml_text"] != candidate_preset["remaining_xml_text"]:
                remainder_differences.append(f"{label}: the rest of the preset XML differs")
    report.close_category()
    report.begin_category("(e') Live presets (.adv): device file reference and the rest of the XML", gated=False)
    for message in remainder_differences:
        report.difference(message)
    report.close_category()


def compare_amxd_containers(report, baseline_build, candidate_build):
    report.begin_category("(f) .amxd containers (frozen mdat timestamps and offsets ignored)", gated=False)
    for role in ("unfrozen_amxd", "frozen_amxd"):
        role_label = role.replace("_", " ")
        if bool(baseline_build[role]) != bool(candidate_build[role]):
            report.difference(f"{role_label}: present in only one build "
                              f"(baseline {baseline_build[role]}, candidate {candidate_build[role]})")
            continue
        if not baseline_build[role]:
            report.note(f"{role_label}: in neither build")
            continue
        baseline_amxd, candidate_amxd = read_amxd(baseline_build[role]), read_amxd(candidate_build[role])
        for header_field in ("device_type", "meta_value", "is_frozen"):
            if baseline_amxd[header_field] != candidate_amxd[header_field]:
                report.difference(f"{role_label}: header {header_field}: {baseline_amxd[header_field]!r} -> "
                                  f"{candidate_amxd[header_field]!r}")
        if not baseline_amxd["is_frozen"] or not candidate_amxd["is_frozen"]:
            if canonical_text(baseline_amxd["patch"]) != canonical_text(candidate_amxd["patch"]):
                report.difference(f"{role_label}: embedded patch JSON differs (see (a)-(c) for what)")
            continue
        baseline_entries, candidate_entries = baseline_amxd["frozen_entries"], candidate_amxd["frozen_entries"]
        report.note(f"frozen contents: baseline {[e['fnam'] for e in baseline_entries]}, "
                    f"candidate {[e['fnam'] for e in candidate_entries]}")
        if len(baseline_entries) != len(candidate_entries):
            report.difference(f"frozen device holds {len(baseline_entries)} files in the baseline, {len(candidate_entries)} in the candidate")
        for baseline_entry, candidate_entry in zip(baseline_entries, candidate_entries):
            entry_label = f"frozen file {baseline_entry['fnam']}"
            for directory_field in ("type", "fnam", "sz32", "vers", "flag"):
                if baseline_entry.get(directory_field) != candidate_entry.get(directory_field):
                    report.difference(f"{entry_label}: {directory_field} {baseline_entry.get(directory_field)!r} -> "
                                      f"{candidate_entry.get(directory_field)!r}")
            if baseline_entry["data"] == candidate_entry["data"]:
                continue
            if baseline_entry["type"] == "JSON":
                baseline_json = parse_patch_json(baseline_entry["data"].rstrip(b"\0"), baseline_build[role])
                candidate_json = parse_patch_json(candidate_entry["data"].rstrip(b"\0"), candidate_build[role])
                if canonical_text(baseline_json) != canonical_text(candidate_json):
                    report.difference(f"{entry_label}: embedded patch JSON differs")
                else:
                    report.difference(f"{entry_label}: same JSON, different bytes (formatting)")
            else:
                report.difference(f"{entry_label}: contents differ")
                report.text_diff(baseline_entry["fnam"], baseline_entry["data"].decode("utf-8", "replace"),
                                 candidate_entry["data"].decode("utf-8", "replace"))
    report.close_category()


def check_build_is_self_consistent(report, build):
    """Within one build, the .maxpat and the unfrozen .amxd should hold the same patch."""
    if build["maxpat"] and build["unfrozen_amxd"]:
        if canonical_text(read_patch_file(build["maxpat"])) != canonical_text(read_amxd(build["unfrozen_amxd"])["patch"]):
            report.difference(f"{build['label']}: {os.path.basename(build['maxpat'])} and "
                              f"{os.path.basename(build['unfrozen_amxd'])} hold different patches (stale build?)")


def compare_builds(baseline_path, candidate_path, device_name, maximum_diff_lines):
    baseline_build = resolve_build(baseline_path, device_name)
    candidate_build = resolve_build(candidate_path, device_name)
    report = ComparisonReport(maximum_diff_lines)
    report.lines.append(f"baseline:  {baseline_build['label']}")
    report.lines.append(f"candidate: {candidate_build['label']}")
    for side_label, build in (("baseline", baseline_build), ("candidate", candidate_build)):
        for role in ("maxpat", "unfrozen_amxd", "frozen_amxd"):
            report.lines.append(f"  {side_label} {role}: {build[role] or '(none)'}")
    baseline_patch_path, baseline_patch = primary_patch_of_build(baseline_build)
    candidate_patch_path, candidate_patch = primary_patch_of_build(candidate_build)
    compare_parameter_tables(report, baseline_patch, candidate_patch, baseline_build, candidate_build)
    compare_boxes(report, baseline_patch, candidate_patch)
    compare_wires(report, baseline_patch, candidate_patch)
    compare_scripts(report, baseline_build, candidate_build)
    compare_live_presets(report, baseline_build, candidate_build)
    compare_amxd_containers(report, baseline_build, candidate_build)
    report.begin_category("build self-consistency (.maxpat vs unfrozen .amxd)", gated=False)
    check_build_is_self_consistent(report, baseline_build)
    check_build_is_self_consistent(report, candidate_build)
    report.close_category()
    return report


def main(argument_list):
    argument_parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    argument_parser.add_argument("baseline", help="baseline build: a folder, a .maxpat or an .amxd")
    argument_parser.add_argument("candidate", help="candidate build: a folder, a .maxpat or an .amxd")
    argument_parser.add_argument("--device", help="device name (file stem, e.g. 2sl-stab); needed for folders with several")
    argument_parser.add_argument("--fail-on-reported", action="store_true",
                                 help="exit non-zero on a difference in any category, not only the gated ones")
    argument_parser.add_argument("--max-diff-lines", type=int, default=60, help="text diff lines shown per item (60)")
    arguments = argument_parser.parse_args(argument_list)
    try:
        report = compare_builds(arguments.baseline, arguments.candidate, arguments.device, arguments.max_diff_lines)
    except (BuildInputError, OSError, KeyError, ValueError) as problem:
        print(f"compare_device_builds.py: can't compare: {type(problem).__name__}: {problem}", file=sys.stderr)
        return EXIT_STATUS_BAD_INPUT
    print("\n".join(report.lines))
    gated_difference_count = sum(count for category, count in report.difference_counts.items()
                                 if category in report.gated_categories)
    reported_difference_count = sum(report.difference_counts.values()) - gated_difference_count
    print("")
    print("summary:")
    for category, count in report.difference_counts.items():
        print(f"  {count:>5}  {'GATED   ' if category in report.gated_categories else 'reported'}  {category}")
    failing = gated_difference_count > 0 or (arguments.fail_on_reported and reported_difference_count > 0)
    if failing:
        print(f"(╯°□°)╯ FAIL: {gated_difference_count} gated and {reported_difference_count} reported differences",
              file=sys.stderr)
        return EXIT_STATUS_DIFFERENT
    if reported_difference_count:
        print(f"(・_・) gated categories same; {reported_difference_count} reported differences (not gated)")
    else:
        print("(^_^) no differences")
    return EXIT_STATUS_SAME


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

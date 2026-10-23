"""Live preset files (.adv): one per preset of the preset book, next to the device file they are made for.

A Live preset of a Max device is gzipped XML: the device's file reference and every parameter's value, not the
device itself. Each device type's schema is a preset Live wrote, used as the template: a Max Instrument's from 2sl
stab (Live 12.4.6, 2sl-dsp references/ableton/example-2sl-stab-preset.xml), a Max Audio Effect's from a probe device
(Live 12.4.15b7, example-max-audio-effect-preset.xml). Everything but the file reference, the parameter list and the
Stored Only blob is kept as Live wrote it. references/README.md, "Live presets", has the source for each choice.

Known forms only: float and enum parameters, Automated and Stored / Stored Only / Hidden visibility, a Max Instrument
or a Max Audio Effect. Anything else (an Int parameter, a MIDI effect) fails the build: its form hasn't been seen in
a file Live wrote, or isn't taught yet (the audio effect example also holds an Int parameter's form).
"""
import copy
import os
import re
import struct
import zlib
import xml.etree.ElementTree as ElementTree

from twosl_dsp import live_parameter_identity as identity
from twosl_dsp.build_error import BuildError
from twosl_dsp.patch_builder import FRESH_START_FLAG_NAME
from twosl_dsp.preset_book import HeldRecord, stored_only_values_of_preset

KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_PRESET_TEMPLATES = os.path.join(KIT_DIRECTORY, "references", "ableton")
# device type -> (the preset Live wrote, used as the template; the device's element in it)
LIVE_PRESET_TEMPLATE_BY_TYPE = {
    "instrument": (os.path.join(LIVE_PRESET_TEMPLATES, "example-2sl-stab-preset.xml"), "MxDeviceInstrument"),
    "audio": (os.path.join(LIVE_PRESET_TEMPLATES, "example-max-audio-effect-preset.xml"), "MxDeviceAudioEffect"),
}
AMXD_CRC_BYTES = 16384                                             # OriginalCrc covers the file's first 16 KB
# the gzip header: no file name, mtime 0, XFL 2 (maximum compression), OS 3 (Unix), as the presets were first
# committed. Written by hand so the bytes don't depend on the Python version (gzip.compress wrote OS 255 on 3.9).
GZIP_HEADER = b"\x1f\x8b\x08\x00" + b"\x00\x00\x00\x00" + b"\x02\x03"


class LivePresetFiles:
    """The device's choice to ship its presets as Live preset files. `stored_only_values_of_preset(values)`: the
    device's own Stored Only parameters' values for a preset ({control name: value as held} -> {parameter long name:
    number}); with a stored table's (twosl_dsp/stored_table.py, which stores its own), every Stored Only parameter must
    get one. None when the device has no Stored Only parameters of its own."""

    def __init__(self, stored_only_values_of_preset=None):
        self.stored_only_values_of_preset = stored_only_values_of_preset


def amxd_crc(device_bytes):
    """Live's OriginalCrc of a device file: CRC-16 (poly 0x8005, init 0, not reflected, the "BUYPASS" variant) of
    its first 16384 bytes. Matches Live's own value for 2sl stab (19576) and for Ableton's OSC Leap Motion.amxd."""
    crc = 0
    for byte in device_bytes[:AMXD_CRC_BYTES]:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def deterministic_gzip(data):
    compressor = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    deflated = compressor.compress(data) + compressor.flush()
    return GZIP_HEADER + deflated + struct.pack("<II", zlib.crc32(data) & 0xFFFFFFFF, len(data) & 0xFFFFFFFF)


def live_number(value):
    """A number as Live writes it: whole numbers bare, others as a 32-bit float to 9 significant digits."""
    if float(value).is_integer():
        return str(int(value))
    return "%.9g" % struct.unpack("f", struct.pack("f", value))[0]


def _set_value(element, path, value):
    found = element.find(path)
    if found is None:
        raise BuildError(f"the Live preset template has no {path} in <{element.tag}> ({LIVE_PRESET_TEMPLATES})")
    found.set("Value", value)


def live_preset_file_name(preset):
    file_name = (preset.name if preset.group == "init" else f"{preset.group} - {preset.name}") + ".adv"
    if re.search(r'[/\\:*?"<>|]', file_name):
        raise BuildError(f"preset {preset.name!r} makes a file name with a character macOS or Windows refuses")
    return file_name


class _LivePresetWriter:
    """The parameters as Live lists them, read once from the patch, and the template's prototypes."""

    def __init__(self, patch, device_type):
        if device_type not in LIVE_PRESET_TEMPLATE_BY_TYPE:
            raise BuildError(f"Live preset files: only a Max {sorted(LIVE_PRESET_TEMPLATE_BY_TYPE)} has a known form "
                             f"(each template is a preset of one), not {device_type!r}")
        self.template_path, self.device_element_name = LIVE_PRESET_TEMPLATE_BY_TYPE[device_type]
        # Automated and Stored parameters go in the parameter list, Stored Only ones in the blob, Hidden ones
        # nowhere (as in Live's own file). The list is ordered by name, as Live wrote it.
        self.listed_parameters, self.stored_only_names = [], []
        for box, valueof in identity.live_parameter_boxes(patch):
            name, visibility = valueof["parameter_longname"], valueof.get("parameter_invisible", 0)
            if visibility == identity.VISIBILITY_HIDDEN:
                continue
            if visibility == identity.VISIBILITY_STORED_ONLY:
                self.stored_only_names.append(name)
            elif visibility == identity.VISIBILITY_AUTOMATED_AND_STORED:
                if valueof["parameter_type"] not in (identity.PARAMETER_TYPE_FLOAT, identity.PARAMETER_TYPE_ENUM):
                    raise BuildError(f"Live preset files: {name!r} has parameter_type {valueof['parameter_type']}; only "
                                     "float (0) and enum (2) have a form seen in a file Live wrote")
                self.listed_parameters.append(dict(valueof, item_names_in_live=identity.live_item_names(box, valueof)))
            else:
                raise BuildError(f"Live preset files: {name!r} has Parameter Visibility {visibility}, with no known form")
        self.listed_parameters.sort(key=lambda valueof: valueof["parameter_longname"])
        self.template_root = ElementTree.parse(self.template_path).getroot()
        template_device = self.template_root.find(self.device_element_name)
        if template_device is None:
            raise BuildError(f"{self.template_path} has no <{self.device_element_name}>")
        template_parameter_list = template_device.find("ParameterList/ParameterList")
        self.prototypes = {tag: template_parameter_list.find(tag) for tag in ("MxDFloatParameter", "MxDEnumParameter")}
        if None in self.prototypes.values():
            raise BuildError(f"{self.template_path} needs a float and an enum parameter to copy")
        self.first_parameter_id = min(int(p.get("Id")) for p in template_parameter_list)

    def parameter_element(self, parameter_id, index, valueof, value):
        """One parameter as Live lists it, copied from the template's element of its type. Live holds a float's values
        (Default and the Manual value alike) as the dial's position spread linearly over [min, max], not in the
        dial's units: min + (max - min) * normalised^(1/exponent). A float's MIDI controller range is
        [max(min, 0), max(min, 1)]. All as Live wrote them for all 51 of 2sl stab's (Decay 260 ms is saved as 2097.7)."""
        is_enum = valueof["parameter_type"] == identity.PARAMETER_TYPE_ENUM
        prototype = self.prototypes["MxDEnumParameter" if is_enum else "MxDFloatParameter"]
        element = copy.deepcopy(prototype)
        element.set("Id", str(parameter_id))
        minimum = float(valueof.get("parameter_mmin", 0.0))
        maximum = float(len(valueof["parameter_enum"]) - 1) if is_enum else float(valueof.get("parameter_mmax", 127.0))
        initial_value = float((valueof.get("parameter_initial") or [minimum])[0])
        exponent = float(valueof.get("parameter_exponent", 1.0))

        def value_as_live_holds_it(value_in_dial_units):
            if is_enum:
                return value_in_dial_units
            return minimum + (maximum - minimum) * ((value_in_dial_units - minimum) / (maximum - minimum)) ** (1.0 / exponent)
        for path, text in [("Index", str(index)), ("Type", str(valueof["parameter_type"])),
                           ("Name", valueof["parameter_longname"]), ("ShortName", valueof["parameter_shortname"]),
                           ("MinValue", live_number(minimum)), ("MaxValue", live_number(maximum)),
                           ("Default", live_number(value_as_live_holds_it(initial_value))),
                           ("Timeable/Manual", live_number(value_as_live_holds_it(float(value))))]:
            _set_value(element, path, text)
        if is_enum:
            names = element.find("Names")
            for old_name in list(names):
                names.remove(old_name)
            for item_index, item in enumerate(valueof["item_names_in_live"]):
                name_element = ElementTree.SubElement(names, "Name", Id=str(item_index))
                ElementTree.SubElement(name_element, "Name", Value=item)
        else:
            _set_value(element, "Timeable/MidiControllerRange/Min", live_number(max(minimum, 0.0)))
            _set_value(element, "Timeable/MidiControllerRange/Max", live_number(max(minimum, 1.0)))
        return element

    @staticmethod
    def stored_only_blob_text(values):
        """The Stored Only parameters as Live keeps them: JSON (4-space indent, names sorted), a NUL, as hex in lines
        of 80 digits (decoded from Live's file: {"Accents": [ 1 ], "Steps": [ 73 ]})."""
        json_text = "{\n" + ",\n".join(f'    "{name}": [ {live_number(values[name])} ]' for name in sorted(values)) + "\n}"
        hex_digits = (json_text.encode() + b"\0").hex().upper()
        blob_indent = "\t" * 6
        return "\n" + "".join(blob_indent + hex_digits[i:i + 80] + "\n" for i in range(0, len(hex_digits), 80)) + "\t" * 5

    def preset_bytes(self, preset, device_file_name, device_size, device_crc, stored_only_values):
        root = copy.deepcopy(self.template_root)
        device = root.find(self.device_element_name)
        # the device file: relative to the preset (RelativePathType 1), so the presets work wherever the folder goes;
        # no absolute Path (the template's is a path on one Mac)
        file_ref = device.find("PatchSlot/Value/MxPatchRef/FileRef")
        _set_value(file_ref, "RelativePathType", "1")
        _set_value(file_ref, "RelativePath", device_file_name)
        if file_ref.find("Path") is not None:
            file_ref.remove(file_ref.find("Path"))
        _set_value(file_ref, "OriginalFileSize", str(device_size))
        _set_value(file_ref, "OriginalCrc", str(device_crc))
        _set_value(device, "PatchSlot/Value/MxPatchRef/LastModDate", "0")      # a fixed date: the build is repeatable
        _set_value(device, "LastSelectedTimeableIndex", "0")
        _set_value(device, "LastSelectedClipEnvelopeIndex", "0")
        parameter_list = device.find("ParameterList/ParameterList")
        for old_parameter in list(parameter_list):
            parameter_list.remove(old_parameter)
        for index, valueof in enumerate(self.listed_parameters):
            value = preset.values.get(valueof["parameter_longname"], 0)         # buttons (Stop): at rest
            parameter_list.append(self.parameter_element(self.first_parameter_id + index, index, valueof, value))
        blob = device.find("BlobSlot/Value/MxDBlob/Blob")
        if blob is None:
            raise BuildError(f"{self.template_path} has no stored-only blob")
        ElementTree.indent(root, space="\t")
        blob.text = self.stored_only_blob_text(stored_only_values)              # after indent(): its own layout
        xml_text = '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(root, encoding="unicode") + "\n"
        return deterministic_gzip(xml_text.encode())


def write_live_presets(device_path, patch, device_type, presets, live_preset_files, log):
    """Every preset as a Live preset next to the device file `device_path`, made for that exact file: it refers to it
    by its file name in the same folder (RelativePathType 1) with its size and OriginalCrc. Removes other .adv files
    there (saying so). Returns the file names written."""
    writer = _LivePresetWriter(patch, device_type)
    with open(device_path, "rb") as device_file:
        device_bytes = device_file.read()
    device_size, device_crc = len(device_bytes), amxd_crc(device_bytes)
    preset_folder = os.path.dirname(device_path)
    listed_names = {valueof["parameter_longname"] for valueof in writer.listed_parameters}
    written = []
    for preset in presets:
        unlisted = {name for name, value in preset.values.items() if not isinstance(value, HeldRecord)} - listed_names
        if unlisted:
            raise BuildError(f"Live preset files: preset {preset.name!r} sets controls that aren't Automated and "
                             f"Stored parameters, which a Live preset can't hold: {sorted(unlisted)}")
        stored_only_values = stored_only_values_of_preset(preset.values, live_preset_files.stored_only_values_of_preset,
                                                          f"Live preset files: preset {preset.name!r}")
        # a preset is a device with its values: the fresh-start flag at 1, so the UI script never moves them to Init
        stored_only_values[FRESH_START_FLAG_NAME] = 1
        if sorted(stored_only_values) != sorted(writer.stored_only_names):
            raise BuildError(f"Live preset files: preset {preset.name!r} gives Stored Only values for "
                             f"{sorted(stored_only_values)}, the device's Stored Only parameters are "
                             f"{sorted(writer.stored_only_names)} (a device's own Stored Only parameters need its "
                             "stored_only_values_of_preset; a stored table's are its own)")
        file_name = live_preset_file_name(preset)
        with open(os.path.join(preset_folder, file_name), "wb") as preset_file:
            preset_file.write(writer.preset_bytes(preset, os.path.basename(device_path), device_size, device_crc,
                                                  stored_only_values))
        written.append(file_name)
    remove_stale_live_presets(preset_folder, written, log)
    log(f"wrote {len(written)} Live presets next to {os.path.basename(device_path)} ({len(writer.listed_parameters)} "
        f"parameters each; device {device_size} bytes, CRC {device_crc})")
    return written


def remove_stale_live_presets(preset_folder, kept_file_names, log):
    for stale in sorted(set(f for f in os.listdir(preset_folder) if f.endswith(".adv")) - set(kept_file_names)):
        os.remove(os.path.join(preset_folder, stale))
        log(f"removed {stale}: no preset of that name in the preset book")

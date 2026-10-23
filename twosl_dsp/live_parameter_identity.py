"""What Live knows a device's parameters by, and the lock file that keeps it from changing by accident.

Live stores a parameter's value in sets and presets under its long name, maps a float's stored value through its
range and exponent, names an enum's values by its items, and lists the automatable parameters in patch order
(references/README.md, "Live presets"). Change any of that and saved sets, presets, automation and MIDI mappings
silently land somewhere else. So a device repository keeps `src/live-parameters.lock.json`: every parameter's
identity, in order, and the device type. The build compares the patch with it and fails with a diff on any change,
unless it is run with --accept-live-parameter-changes, which rewrites the lock (commit it with the change, and say
in the release notes what it breaks). architecture/live-parameter-identity.md has the reasoning.
"""
import difflib
import json
import os

from twosl_dsp.build_error import BuildError

LOCK_FILE_NAME = "live-parameters.lock.json"
ACCEPT_CHANGES_FLAG = "--accept-live-parameter-changes"

# Max's parameter_type (live.* references) and parameter_invisible (Parameter Visibility: Automated and Stored,
# Stored Only, Hidden; 1 = Stored Only is confirmed by a preset Live saved, 2 = Hidden is the inspector's order:
# references/README.md).
PARAMETER_TYPE_FLOAT, PARAMETER_TYPE_INT, PARAMETER_TYPE_ENUM = 0, 1, 2
VISIBILITY_AUTOMATED_AND_STORED, VISIBILITY_STORED_ONLY, VISIBILITY_HIDDEN = 0, 1, 2

# the identity of one parameter, as the lock lists it: (lock key, where it comes from)
IDENTITY_FIELDS = [
    ("long_name", "parameter_longname"), ("short_name", "parameter_shortname"), ("type", "parameter_type"),
    ("items", "parameter_enum"), ("minimum", "parameter_mmin"), ("maximum", "parameter_mmax"),
    ("exponent", "parameter_exponent"), ("unit_style", "parameter_unitstyle"), ("initial", "parameter_initial"),
    ("initial_enabled", "parameter_initial_enable"), ("visibility", "parameter_invisible"),
]
# Max leaves an attribute out when it has its default (the same defaults the comparison tool fills in)
IDENTITY_DEFAULTS = {"parameter_mmin": 0.0, "parameter_exponent": 1.0, "parameter_initial_enable": 0,
                     "parameter_invisible": 0, "parameter_enum": []}


def live_parameter_boxes(patch):
    """The patch's Live parameters in patch order (Live's order): [(box, its saved parameter values)]."""
    found = []
    for wrapped in patch["patcher"]["boxes"]:
        box = wrapped["box"]
        valueof = box.get("saved_attribute_attributes", {}).get("valueof")
        if box.get("parameter_enable") and valueof:
            found.append((box, valueof))
    return found


def live_item_names(box, valueof):
    """The names Live shows for an enum's values. A live.text's are its automation / automationon attributes (its
    text / texton are only the button's label: Cycling '74, live.text reference); Max keeps parameter_enum the same,
    and the build fails if they differ."""
    if box["maxclass"] != "live.text":
        return valueof.get("parameter_enum")
    names = [box.get("automation"), box.get("automationon")]
    if names != valueof.get("parameter_enum"):
        raise BuildError(f"live.text {valueof['parameter_longname']!r} has automation / automationon {names}, "
                         f"parameter_enum {valueof.get('parameter_enum')}: Max keeps them the same")
    return names


def parameter_identity(box, valueof):
    identity = {"maxclass": box["maxclass"], "varname": box.get("varname")}
    for lock_key, attribute in IDENTITY_FIELDS:
        identity[lock_key] = valueof.get(attribute, IDENTITY_DEFAULTS.get(attribute))
    if box["maxclass"] == "live.text":
        identity["live_item_names"] = live_item_names(box, valueof)
    return identity


def device_identity(patch, device_type):
    return {"device_type": device_type,
            "parameters": [parameter_identity(box, valueof) for box, valueof in live_parameter_boxes(patch)]}


def lock_text(identity):
    """The lock file: one parameter a line, so a diff shows each changed parameter whole."""
    lines = ["{",
             '  "about": "What Live knows this device\'s parameters by, in order. Written by the build; a change fails '
             'it until it is run with ' + ACCEPT_CHANGES_FLAG + ' (see 2sl-dsp architecture/live-parameter-identity.md).",',
             f'  "device_type": {json.dumps(identity["device_type"])},',
             '  "parameters": [']
    parameter_lines = [f"    {json.dumps(parameter, sort_keys=False)}" for parameter in identity["parameters"]]
    lines += [line + ("," if index < len(parameter_lines) - 1 else "") for index, line in enumerate(parameter_lines)]
    lines += ["  ]", "}"]
    return "\n".join(lines) + "\n"


def check_lock(lock_path, identity, accept_changes, display_name):
    """Fails with a diff when the device's parameter identity differs from the lock file's (or there is none),
    unless `accept_changes`: then the lock is rewritten. Returns what happened, for the build's log."""
    wanted_text = lock_text(identity)
    existing_text = None
    if os.path.isfile(lock_path):
        with open(lock_path, encoding="utf-8") as lock_file:
            existing_text = lock_file.read()
    if existing_text == wanted_text:
        return f"{display_name}: the Live parameters match ({len(identity['parameters'])} parameters)"
    if existing_text is not None:
        try:
            existing_identity = json.loads(existing_text)
        except ValueError as problem:
            raise BuildError(f"{display_name} isn't valid JSON ({problem}): fix it, or rebuild with {ACCEPT_CHANGES_FLAG}")
        existing_text = lock_text({"device_type": existing_identity.get("device_type"),
                                   "parameters": existing_identity.get("parameters", [])})
    if accept_changes:
        with open(lock_path, "w", encoding="utf-8") as lock_file:
            lock_file.write(wanted_text)
        return (f"{display_name}: {'written' if existing_text is None else 'rewritten'} with "
                f"{len(identity['parameters'])} parameters ({ACCEPT_CHANGES_FLAG}): commit it")
    if existing_text is None:
        raise BuildError(f"{display_name} is missing: run the build once with {ACCEPT_CHANGES_FLAG} to write it, "
                         f"check it, and commit it")
    if existing_text == wanted_text:
        return f"{display_name}: the Live parameters match ({len(identity['parameters'])} parameters; lock reformatted?)"
    diff = difflib.unified_diff(existing_text.splitlines(), wanted_text.splitlines(), f"{display_name} (locked)",
                                "the patch as built", lineterm="", n=1)
    raise BuildError(f"the Live parameters changed (sets, presets, automation and mappings saved with the old ones "
                     f"may break). If that is meant, rebuild with {ACCEPT_CHANGES_FLAG} and commit the lock:\n"
                     + "\n".join(diff))

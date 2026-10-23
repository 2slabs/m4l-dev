"""What a built device's controls hold once Live has loaded it and the header's ready has come: its UI script run in
node (tools/fresh_start.js) on the controls as Live loads them (architecture/presets.md, "Neutral, Init, and a fresh
device"). A device's tests use it to show that a fresh device plays its Init sound and a saved set comes back as saved.

    controls_after_ready(device_folder)                  # a fresh device: every control at Live's initial value
    controls_after_ready(device_folder, saved_values)    # a set or preset recalling {varname: number} (the flag too)

Returns {varname: number} for every Live parameter in the patch. Fails loudly (BuildError) without node, or when the
script printed an error.
"""
import json
import os
import shutil
import subprocess

from twosl_dsp.build_error import BuildError
from twosl_dsp.patch_builder import FRESH_START_FLAG_NAME, varname_for
from twosl_dsp.preset_book import SavedRecord

KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRESH_START_FLAG_VARNAME = varname_for(FRESH_START_FLAG_NAME)


def controls_after_ready(device_folder, saved_values=None):
    node = os.environ.get("NODE") or shutil.which("node")
    if node is None:
        raise BuildError("fresh_start: node isn't on PATH (set NODE=/path/to/node): the UI script runs in it")
    run = subprocess.run([node, os.path.join(KIT_DIRECTORY, "tools", "fresh_start.js"), device_folder,
                          json.dumps(saved_values or {})], capture_output=True, text=True)
    if run.returncode != 0:
        raise BuildError(f"fresh_start: the UI script failed in node:\n{run.stdout}{run.stderr}")
    result = json.loads(run.stdout)
    if result["errors"]:
        raise BuildError(f"fresh_start: the UI script printed errors: {result['errors']}")
    return result["values"]


def saved_values_of(patch, values_as_held):
    """{varname: number} a set saving `values_as_held` ({control long name: value as held}, a preset's) recalls, the
    fresh-start flag at 1 as every saved set and preset holds it."""
    saved = {patch.saved_controls[name].varname: value for name, value in values_as_held.items()
             if name in patch.saved_controls and not isinstance(patch.saved_controls[name], SavedRecord)}
    saved[FRESH_START_FLAG_VARNAME] = 1
    return saved


def held_by_name(patch, values_by_varname):
    """{control long name: value as held} of every saved control with a neutral value (patch.neutral_values) or set
    by presets, read from `values_by_varname`."""
    names = set(patch.saved_controls) | {name for name in patch.neutral_values}
    held = {}
    for name in names:
        varname = varname_for(name)
        if varname in values_by_varname:
            held[name] = values_by_varname[varname]
    return held

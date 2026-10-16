"""The preset book: a device's Init values and its presets, in one JSON file, in each control's own units.

    {"init": {control: value, ...},
     "presets": [{"name": ..., "group": ..., "idea": ..., "values": {control: value, ...}}, ...]}

"init" holds every saved control's initial value: a fresh device is the Init sound. "presets" are the sounds, each
the Init values with some changed. A value is in its control's own units: a dial's or number box's number, a menu's
or tab's item name, a toggle's "off" / "on". The build fails on an unknown control, a saved control without an Init
value, a value out of its control's range, and preset names used twice.

One book serves both preset outputs (architecture/presets.md): Live preset files (.adv, m4l_dev/live_preset_files.py)
and the header's Preset menu (the UI script sets every saved control from it).
"""
import json
from collections import namedtuple

from m4l_dev.build_error import BuildError

PRESET_FIELDS = ("name", "group", "idea", "values")
TOGGLE_ITEMS = ["off", "on"]     # a live.text toggle's states, as presets and Live name them

# A control the set and the presets save: its scripting name, and its range: `items` (a menu, tab, toggle or enum
# dial; values are item names, held as their index) or None with `minimum` / `maximum` (a number).
SavedControl = namedtuple("SavedControl", "name varname items minimum maximum")
# A preset with every saved control's value as the control holds it (a number; an item's index).
Preset = namedtuple("Preset", "name group idea values")


def value_as_held(control, value_in_own_units, where):
    """`value_in_own_units` as `control` holds it (an item name becomes its index), or fail the build."""
    if control.items is not None:
        if value_in_own_units not in control.items:
            raise BuildError(f"{where}: {control.name} is {value_in_own_units!r}, not one of {control.items}")
        return control.items.index(value_in_own_units)
    if isinstance(value_in_own_units, bool) or not isinstance(value_in_own_units, (int, float)):
        raise BuildError(f"{where}: {control.name} is {value_in_own_units!r}, not a number")
    if not control.minimum <= value_in_own_units <= control.maximum:
        raise BuildError(f"{where}: {control.name} is {value_in_own_units}, outside {control.minimum:g} to "
                         f"{control.maximum:g}")
    return value_in_own_units


class PresetBook:
    def __init__(self, data, source_name):
        """`data` as the JSON file holds it; `source_name` names it in the build's messages."""
        self.source_name = source_name
        if not isinstance(data, dict) or set(data) != {"init", "presets"}:
            found = sorted(data) if isinstance(data, dict) else type(data).__name__
            raise BuildError(f"{source_name} must hold exactly 'init' and 'presets', not {found}")
        if not isinstance(data["init"], dict) or not isinstance(data["presets"], list):
            raise BuildError(f"{source_name}: 'init' must be an object and 'presets' a list")
        self.init_values_in_own_units = data["init"]
        self.presets_in_own_units = data["presets"]
        for preset_number, preset in enumerate(self.presets_in_own_units):
            where = self.where(preset_number, preset)
            if not isinstance(preset, dict) or set(preset) != set(PRESET_FIELDS):
                raise BuildError(f"{where} must have exactly {sorted(PRESET_FIELDS)}, not "
                                 f"{sorted(preset) if isinstance(preset, dict) else preset!r}")
            if not all(isinstance(preset[field], str) and preset[field] for field in ("name", "group", "idea")):
                raise BuildError(f"{where}: name, group and idea must be non-empty text")
            if not isinstance(preset["values"], dict):
                raise BuildError(f"{where}: values must be an object")
        names = [preset["name"] for preset in self.presets_in_own_units]
        if len(set(names)) != len(names):
            raise BuildError(f"preset names used twice in {source_name}: "
                             f"{sorted({n for n in names if names.count(n) > 1})}")
        if not names:
            raise BuildError(f"{source_name} has no presets (the first is usually the Init sound, with no values)")

    @classmethod
    def from_file(cls, path, source_name):
        with open(path, encoding="utf-8") as book_file:
            try:
                data = json.load(book_file)
            except ValueError as problem:
                raise BuildError(f"{source_name} isn't valid JSON: {problem}")
        return cls(data, source_name)

    def where(self, preset_number, preset):
        name = preset.get("name") if isinstance(preset, dict) else None
        return f"{self.source_name}, preset {preset_number + 1} ({name!r})"

    def has_init_value(self, control_name):
        return control_name in self.init_values_in_own_units

    def init_value_as_held(self, control):
        if control.name not in self.init_values_in_own_units:
            raise BuildError(f"{control.name!r} has no Init value: add it to 'init' in {self.source_name}")
        return value_as_held(control, self.init_values_in_own_units[control.name], f"{self.source_name}, init")

    def presets_as_held(self, saved_controls):
        """Every preset with every saved control's value as held ({control name: SavedControl}): [Preset]."""
        unknown_init = set(self.init_values_in_own_units) - set(saved_controls)
        if unknown_init:
            raise BuildError(f"'init' in {self.source_name} names no saved control: {sorted(unknown_init)}")
        init_as_held = {name: self.init_value_as_held(control) for name, control in saved_controls.items()}
        presets = []
        for preset_number, preset in enumerate(self.presets_in_own_units):
            where = self.where(preset_number, preset)
            unknown = set(preset["values"]) - set(saved_controls)
            if unknown:
                raise BuildError(f"{where} sets controls the device doesn't have: {sorted(unknown)}")
            values = dict(init_as_held)
            for control_name, value in preset["values"].items():
                values[control_name] = value_as_held(saved_controls[control_name], value, where)
            presets.append(Preset(preset["name"], preset["group"], preset["idea"], values))
        return presets

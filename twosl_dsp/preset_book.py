"""The preset book: a device's neutral values, its Init values and its presets, in one JSON file, in each control's
own units.

    {"neutral": {control: value, ...},
     "init": {control: value, ...},
     "presets": [{"name": ..., "group": ..., "idea": ..., "values": {control: value, ...}}, ...]}

"neutral" holds, for every control a user can double-click (every saved control, and every one with its own initial
value that Live saves), the value that takes it out of the sound: Live's initial value (the double-click target,
architecture/presets.md "Neutral, Init, and a fresh device"). A stored table's is {field: value}, its editors'
double-click target. "init" holds every saved control's starting value: a fresh device is the Init sound. "presets" are the sounds, each
the Init values with some changed. A value is in its control's own units: a dial's or number box's number, a menu's
or tab's item name, a toggle's "off" / "on". The build fails on an unknown control, a saved control without an Init
value, a value out of its control's range, and preset names used twice.

One book serves both preset outputs (architecture/presets.md): Live preset files (.adv, twosl_dsp/live_preset_files.py)
and the header's Preset menu (the UI script sets every saved control from it).

A saved record (`SavedRecord`: a stored table, twosl_dsp/stored_table.py) is saved like a control but holds many values:
its value is an object of fields, each a list of one value per row, in the field's own units. Init gives every field;
a preset gives the fields it changes, each whole, and keeps Init's others. It reaches Live as Stored Only parameters
(`stored_only_values_of_preset`), not as an automatable parameter.
"""
import json
from collections import namedtuple

from twosl_dsp.build_error import BuildError

PRESET_FIELDS = ("name", "group", "idea", "values")
TOGGLE_ITEMS = ["off", "on"]     # a live.text toggle's states, as presets and Live name them

# A control the set and the presets save: its scripting name, and its range: `items` (a menu, tab, toggle or enum
# dial; values are item names, held as their index) or None with `minimum` / `maximum` (a number).
SavedControl = namedtuple("SavedControl", "name varname items minimum maximum")
# A preset with every saved control's value as the control holds it (a number; an item's index).
Preset = namedtuple("Preset", "name group idea values")


class SavedRecord:
    """A saved value that is many values (a stored table): the preset book holds it as {field: [value per row]}.
    A subclass gives `name`, `held_from_own_units(value, where, init_held)` (a HeldRecord; `init_held` None for Init,
    which must give every field, else Init's HeldRecord, whose fields a preset leaves alone are kept) and
    `parameter_varnames()` (its Stored Only parameters' scripting names)."""
    name = None

    def held_from_own_units(self, value_in_own_units, where, init_held):
        raise NotImplementedError(f"{type(self).__name__} must say how it holds a value")

    def parameter_varnames(self):
        raise NotImplementedError(f"{type(self).__name__} must name its parameters")


class HeldRecord:
    """A saved record's value as held, in a preset's values: it knows its Stored Only parameters' values."""

    def stored_only_values(self):
        """{Stored Only parameter long name: number}."""
        raise NotImplementedError(f"{type(self).__name__} must say how it is stored")


def stored_only_values_of_preset(preset_values, device_stored_only_values_of_preset, where):
    """A preset's Stored Only parameters: every saved record's (a HeldRecord in `preset_values`) and the device's own
    (`device_stored_only_values_of_preset(preset_values)`; None when it has none), {long name: number}. Live preset
    files, the Preset menu and the plugin's presets all fill a preset's Stored values here. A name both give fails."""
    values = {}
    for held in preset_values.values():
        if isinstance(held, HeldRecord):
            values.update(held.stored_only_values())
    if device_stored_only_values_of_preset is not None:
        device_values = device_stored_only_values_of_preset(preset_values)
        twice = sorted(set(device_values) & set(values))
        if twice:
            raise BuildError(f"{where}: the device's stored_only_values_of_preset gives {twice}, which a stored table "
                             "already stores")
        values.update(device_values)
    return values


def value_as_held(control, value_in_own_units, where, init_held=None):
    """`value_in_own_units` as `control` holds it (an item name becomes its index; a saved record's, its own way:
    `init_held` is Init's, for the fields a preset leaves alone), or fail the build."""
    if isinstance(control, SavedRecord):
        return control.held_from_own_units(value_in_own_units, where, init_held)
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
        if not isinstance(data, dict) or set(data) != {"neutral", "init", "presets"}:
            found = sorted(data) if isinstance(data, dict) else type(data).__name__
            raise BuildError(f"{source_name} must hold exactly 'neutral', 'init' and 'presets', not {found}")
        if (not isinstance(data["neutral"], dict) or not isinstance(data["init"], dict)
                or not isinstance(data["presets"], list)):
            raise BuildError(f"{source_name}: 'neutral' and 'init' must be objects and 'presets' a list")
        self.neutral_values_in_own_units = data["neutral"]
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

    def has_neutral_value(self, control_name):
        return control_name in self.neutral_values_in_own_units

    def neutral_value_in_own_units(self, control_name):
        """`control_name`'s neutral value as the book gives it, or fail the build: every control a user can
        double-click declares one, never falling back to its Init value."""
        if control_name not in self.neutral_values_in_own_units:
            raise BuildError(f"{control_name!r} has no neutral value (what a double-click sets it to: 0 for an amount, "
                             f"the centre of a bipolar control, unity for a gain, the off item; for a control with no "
                             f"off, the musically neutral value): add it to 'neutral' in {self.source_name}")
        return self.neutral_values_in_own_units[control_name]

    def neutral_value_as_held(self, control):
        return value_as_held(control, self.neutral_value_in_own_units(control.name), f"{self.source_name}, neutral")

    def preset_names(self):
        return [preset["name"] for preset in self.presets_in_own_units]

    def values_in_own_units(self, preset_name):
        """`preset_name`'s values in each control's own units, Init's filled in for every control it leaves alone (and,
        in a saved record, {field: [value per row]}, for every field it leaves alone)."""
        for preset in self.presets_in_own_units:
            if preset["name"] == preset_name:
                values = dict(self.init_values_in_own_units)
                for name, value in preset["values"].items():
                    init_value = values.get(name)
                    values[name] = ({**init_value, **value} if isinstance(init_value, dict) and isinstance(value, dict)
                                    else value)
                return values
        raise BuildError(f"no preset named {preset_name!r} in {self.source_name}")

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
                values[control_name] = value_as_held(saved_controls[control_name], value, where,
                                                     init_as_held[control_name])
            presets.append(Preset(preset["name"], preset["group"], preset["idea"], values))
        return presets

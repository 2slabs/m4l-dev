"""StoredTable: a device's table of values (rows x fields) saved with the set and in its presets, but not automated:
Live's Stored Only parameters, packed 16 bits each (architecture/stored-table.md).

A sequencer's stages, a pattern's steps: many values that the brain and the DSP read, that the set and every preset
keep, and that would swamp Live's automation list and Push as a parameter each. The kit holds the packing, the preset
book's form, the brain's code (templates/stored-table.template.js) and the editors, so every device's stored state
means the same and loads the same way.

    stages = StoredTable(patch, "Stage", [ContinuousField("Pitch", -24, 24), ChoiceField("Pulse", ["off", "on"]),
                                          ChoiceField("Wait", ["go", "stop", "hold", "keyed"])],
                         row_count=16, brain=brain, brain_inlet=1, brain_outlet=3)
    stages.editor_dial("Pitch", 0, "Seq Pitch 1", "Pitch 1", x, y, "seq", group=...)      # Hidden live.dial
    # (items=[names]: a stepped dial over a field that is an index, 0..len(items) - 1)
    stages.editor_toggle("Pulse", 0, "Seq Pulse 1", "Pulse 1", x, y, w, "seq", group=...)   # Hidden live.text
    stages.editor_menu("Wait", 0, "Seq Wait 1", "Wait 1", x, y, w, "seq", group=...)        # Hidden live.menu
    brain_code = stored_tables_brain_code([stages])        # fills the brain's /*STORED_TABLES*/

The preset book holds it like a control, by its name, as {field: [one value per row]} in each field's own units (a
continuous field's number, a choice field's item name): Init gives every field, a preset the fields it changes.
A preset's held value is a HeldTable; its Stored Only values go into Live preset files, the Preset menu and the
plugin's presets without the device's help (preset_book.stored_only_values_of_preset).

How it is stored: each continuous field of each row is one Stored Only parameter, "<table> <field> <row>" (row 1..n),
its value a whole number 0..65535 (DevicePatchBuilder.stored: Live's Int type holds 256 values). A continuous field
runs between two whole numbers and holds `codes_per_unit` steps a unit, as many as fit 16 bits, so every whole number
in it is exact (-24..24: 1365 a semitone). A row's choice fields share one, "<table> switches <row>", packed low bits
first in the order given (at most 16 bits a row).
"""
import json
import math

from twosl_dsp import layout_rules
from twosl_dsp import live_parameter_identity as identity
from twosl_dsp.build_error import BuildError
from twosl_dsp.generated_scripts import fill_template, kit_template_text
from twosl_dsp.patch_builder import varname_for
from twosl_dsp.preset_book import HeldRecord, SavedRecord

STORED_VALUE_CODES = 65536            # a Stored Only value holds 0..65535 (DevicePatchBuilder.stored)
# the outlet templates/stored-table.template.js's writes go from, `outlet(spec.outlet, ...)`: the table's brain_outlet,
# which the script's text can't say, so each table tells the builder (script_outlet_of_block)
STORED_TABLE_OUTLET_EXPRESSION = "spec.outlet"
SWITCHES_WORD = "switches"            # the packed choices' parameter: "<table> switches <row>"


def nearest_whole(number):
    """Round half up, as the brain's Math.round does for the codes (never negative): Python's round() rounds half to
    even, which would store a different code than the brain."""
    return int(math.floor(number + 0.5))


class ContinuousField:
    """A number between two whole numbers, `minimum` < `maximum`, held at `codes_per_unit` steps a unit."""

    def __init__(self, name, minimum, maximum):
        if not (isinstance(minimum, int) and isinstance(maximum, int) and minimum < maximum):
            raise BuildError(f"stored field {name!r}: its range must be two whole numbers, low to high, not "
                             f"{minimum!r}..{maximum!r}")
        if maximum - minimum >= STORED_VALUE_CODES:
            raise BuildError(f"stored field {name!r}: {minimum}..{maximum} is wider than the {STORED_VALUE_CODES} codes "
                             "a stored value holds")
        self.name, self.minimum, self.maximum = name, minimum, maximum
        self.codes_per_unit = (STORED_VALUE_CODES - 1) // (maximum - minimum)

    def held(self, value_in_own_units, where):
        if isinstance(value_in_own_units, bool) or not isinstance(value_in_own_units, (int, float)):
            raise BuildError(f"{where}: {self.name} is {value_in_own_units!r}, not a number")
        if not self.minimum <= value_in_own_units <= self.maximum:
            raise BuildError(f"{where}: {self.name} is {value_in_own_units}, outside {self.minimum} to {self.maximum}")
        return self.held_of_code(self.code(value_in_own_units))

    def code(self, held):
        return nearest_whole((held - self.minimum) * self.codes_per_unit)

    def held_of_code(self, code):
        return self.minimum + code / self.codes_per_unit

    def brain_spec(self):
        return {"name": self.name, "kind": "continuous", "minimum": self.minimum, "maximum": self.maximum,
                "codesPerUnit": self.codes_per_unit}


class ChoiceField:
    """One of `items` (names), held as its index; packed with the row's other choices."""

    def __init__(self, name, items):
        if not (isinstance(items, (list, tuple)) and len(items) >= 2 and all(isinstance(i, str) and i for i in items)
                and len(set(items)) == len(items)):
            raise BuildError(f"stored field {name!r}: its items must be two or more different names, not {items!r}")
        self.name, self.items = name, list(items)
        self.bits = (len(self.items) - 1).bit_length()

    def held(self, value_in_own_units, where):
        if value_in_own_units not in self.items:
            raise BuildError(f"{where}: {self.name} is {value_in_own_units!r}, not one of {self.items}")
        return self.items.index(value_in_own_units)

    def brain_spec(self, shift):
        return {"name": self.name, "kind": "choice", "items": self.items, "shift": shift, "bits": self.bits}


class HeldTable(HeldRecord):
    """A stored table's value as held: {field name: (value per row)}, continuous values on their codes, choices as
    indices."""

    def __init__(self, table, columns):
        self.table = table
        self.columns = {name: tuple(values) for name, values in columns.items()}

    def __eq__(self, other):
        return isinstance(other, HeldTable) and other.table is self.table and other.columns == self.columns

    def __hash__(self):
        return hash((self.table.name, tuple(sorted(self.columns.items()))))

    def __repr__(self):
        return f"HeldTable({self.table.name!r}, {self.columns!r})"

    def row(self, row_index):
        """{field name: value as held} of row `row_index` (0-based)."""
        return {name: values[row_index] for name, values in self.columns.items()}

    def stored_only_values(self):
        return self.table.stored_only_values(self)


class StoredTable(SavedRecord):
    def __init__(self, patch, name, fields, row_count, brain, brain_inlet, brain_outlet, initial_outside_presets=None):
        """The table `name` of `row_count` rows of `fields` (ContinuousField, ChoiceField), its Init value the preset
        book's; or, given `initial_outside_presets` ({field: [a value per row]}, every field, in its own units), that
        is its initial value and presets leave the table alone (the Preset menu doesn't set it; a Live preset file
        can't hold it, so the build fails with Live preset files). Its Stored Only parameters tell `brain` (inlet
        `brain_inlet`) their values; the brain writes them back from outlet `brain_outlet` (the route is made by
        stored_tables_brain_code, once the editors are placed)."""
        names = [field.name for field in fields]
        if not fields or len(set(names)) != len(names):
            raise BuildError(f"{patch.device_name}: stored table {name!r} needs fields with different names, not {names}")
        if not (isinstance(row_count, int) and row_count >= 1):
            raise BuildError(f"{patch.device_name}: stored table {name!r} has {row_count!r} rows")
        self.patch, self.name, self.fields, self.row_count = patch, name, list(fields), row_count
        self.fields_by_name = {field.name: field for field in self.fields}
        self.brain, self.brain_inlet, self.brain_outlet = brain, brain_inlet, brain_outlet
        self.choice_fields = [field for field in self.fields if isinstance(field, ChoiceField)]
        self.switch_bits = sum(field.bits for field in self.choice_fields)
        if self.switch_bits > 16:
            raise BuildError(f"{patch.device_name}: stored table {name!r}: its choices need {self.switch_bits} bits a row, a "
                             "stored value holds 16: make fewer choices, or two tables")
        self.shifts, shift = {}, 0
        for field in self.choice_fields:
            self.shifts[field.name], shift = shift, shift + field.bits
        # [(long name, field name or None for the switches, row index)], in patch order
        self.parameters = []
        for row in range(row_count):
            for field in self.fields:
                if isinstance(field, ContinuousField):
                    self.parameters.append((f"{name} {field.name} {row + 1}", field.name, row))
            if self.choice_fields:
                self.parameters.append((f"{name} {SWITCHES_WORD} {row + 1}", None, row))
        self.editors = {}                   # editor varname -> (field name, row index)
        self.editor_boxes = {}              # editor varname -> box id
        self.code_given = False
        init = patch.saved_record(self, initial_outside_presets)
        initial_codes = init.stored_only_values()
        self.stored_boxes = {}
        for long_name, _, _ in self.parameters:
            stored_box = patch.stored(long_name, initial_codes[long_name])
            patch.tell(stored_box, varname_for(long_name), brain, brain_inlet)
            self.stored_boxes[varname_for(long_name)] = stored_box

    # ---- SavedRecord ------------------------------------------------------------------------------------------

    def held_from_own_units(self, value_in_own_units, where, init_held):
        where = f"{where}, {self.name}"
        if not isinstance(value_in_own_units, dict):
            raise BuildError(f"{where} must be {{field: [a value per row]}}, not {value_in_own_units!r}")
        unknown = sorted(set(value_in_own_units) - set(self.fields_by_name))
        if unknown:
            raise BuildError(f"{where} has fields the table doesn't: {unknown} (its fields: {list(self.fields_by_name)})")
        if init_held is None:
            missing = [field.name for field in self.fields if field.name not in value_in_own_units]
            if missing:
                raise BuildError(f"{where}: Init (or initial_outside_presets) must give every field; it leaves out "
                                 f"{missing}")
            columns = {}
        else:
            columns = dict(init_held.columns)
        for field_name, values in value_in_own_units.items():
            if not (isinstance(values, list) and len(values) == self.row_count):
                raise BuildError(f"{where}: {field_name} must be a list of {self.row_count} values, one a row, not "
                                 f"{values!r}")
            field = self.fields_by_name[field_name]
            columns[field_name] = [field.held(value, f"{where} row {row + 1}") for row, value in enumerate(values)]
        return HeldTable(self, {field.name: columns[field.name] for field in self.fields})

    def parameter_varnames(self):
        return [varname_for(long_name) for long_name, _, _ in self.parameters]

    # ---- packing ----------------------------------------------------------------------------------------------

    def stored_only_values(self, held):
        """{Stored Only parameter long name: whole number 0..65535} of the HeldTable `held`."""
        values = {}
        for long_name, field_name, row in self.parameters:
            if field_name is not None:
                values[long_name] = self.fields_by_name[field_name].code(held.columns[field_name][row])
            else:
                values[long_name] = sum(held.columns[field.name][row] << self.shifts[field.name]
                                        for field in self.choice_fields)
        return values

    def held_from_stored_only_values(self, values):
        """The HeldTable that Stored Only `values` ({long name: number}) hold: the brain's unpacking, in Python."""
        columns = {field.name: [None] * self.row_count for field in self.fields}
        for long_name, field_name, row in self.parameters:
            code = values[long_name]
            if not (isinstance(code, int) and 0 <= code < STORED_VALUE_CODES):
                raise BuildError(f"{self.name}: {long_name} holds {code!r}, not a whole number 0..65535")
            if field_name is not None:
                field = self.fields_by_name[field_name]
                held = field.held_of_code(code)
                if held > field.maximum:
                    raise BuildError(f"{self.name}: {long_name} holds {code}, past {field_name}'s {field.maximum}")
                columns[field_name][row] = held
            else:
                if code >= 1 << self.switch_bits:
                    raise BuildError(f"{self.name}: {long_name} holds {code}, past the row's {self.switch_bits} bits")
                for field in self.choice_fields:
                    index = (code >> self.shifts[field.name]) & ((1 << field.bits) - 1)
                    if index >= len(field.items):
                        raise BuildError(f"{self.name}: {long_name} holds {code}: {field.name} {index} is no item")
                    columns[field.name][row] = index
        return HeldTable(self, columns)

    # ---- editors: Hidden controls the brain keeps showing the table -------------------------------------------

    def editor(self, field_name, row, long_name, kind):
        if self.code_given:
            raise BuildError(f"{self.patch.device_name}: stored table {self.name!r}: an editor after the brain code: "
                             "place every editor first (the brain's route names them)")
        field = self.fields_by_name.get(field_name)
        if field is None:
            raise BuildError(f"{self.patch.device_name}: stored table {self.name!r} has no field {field_name!r}")
        if not (isinstance(row, int) and 0 <= row < self.row_count):
            raise BuildError(f"{self.patch.device_name}: stored table {self.name!r} has rows 0..{self.row_count - 1}, "
                             f"not {row!r}")
        if not isinstance(field, kind):
            raise BuildError(f"{self.patch.device_name}: {long_name!r}: {field_name} is a {type(field).__name__}")
        if long_name not in self.patch.info:
            raise BuildError(f"{self.patch.device_name}: editor {long_name!r} has no Info View text: add it to the info")
        return field, self.patch.initial_values[self.name].columns[field_name][row], self.editor_neutral(field)

    def editor_neutral(self, field):
        """`field`'s neutral value as held, its editors' double-click target (Live's initial value of a Hidden
        editor, which the table's recall overrides once the device is ready): the preset book's 'neutral' gives the
        table {field: value} for every field it has an editor of."""
        neutral = self.patch.neutral_of_record(self)
        if field.name not in neutral:
            raise BuildError(f"{self.patch.device_name}: stored table {self.name!r}: {field.name} has an editor but no "
                             f"neutral value (what a double-click sets it to): add it to 'neutral' "
                             f"{{{self.name!r}: {{{field.name!r}: ...}}}} in {self.patch.preset_book.source_name}")
        unknown = sorted(set(neutral) - set(self.fields_by_name))
        if unknown:
            raise BuildError(f"{self.patch.device_name}: stored table {self.name!r}'s neutral names fields it doesn't "
                             f"have: {unknown}")
        return field.held(neutral[field.name], f"{self.patch.preset_book.source_name}, neutral, {self.name}")

    def placed_editor(self, box_id, long_name, field_name, row, told=False):
        """Record an editor; tell the brain its value as `<its varname> value` (unless the control `told` it)."""
        varname = varname_for(long_name)
        if not told:
            self.patch.tell(box_id, varname, self.brain, self.brain_inlet)
        self.editors[varname] = (field_name, row)
        self.editor_boxes[varname] = box_id
        return box_id

    def editor_dial(self, field_name, row, long_name, short_name, x, y, page, group=None, unit=1, exponent=1.0,
                    items=None):
        """A Hidden live.dial showing and setting a continuous field of row `row` (0-based); `unit` its Live unit
        style (1: float), `exponent` its taper. `items` (names): a stepped dial showing a name for each whole number
        of a field that runs 0..len(items) - 1 (an index kept in the table, as a sequencer stage's Time on a list of
        lengths); its value is the index."""
        field, initial, neutral = self.editor(field_name, row, long_name, ContinuousField)
        if items is not None:
            if field.minimum != 0 or field.maximum != len(items) - 1:
                raise BuildError(f"{self.patch.device_name}: {long_name!r}: {len(items)} items name the whole numbers "
                                 f"0..{len(items) - 1}, {field_name} runs {field.minimum}..{field.maximum}")
            if initial != int(initial):
                raise BuildError(f"{self.patch.device_name}: {long_name!r}: {field_name} {row + 1} starts at "
                                 f"{initial}, between two items")
            if neutral != int(neutral):
                raise BuildError(f"{self.patch.device_name}: {long_name!r}: {field_name}'s neutral {neutral} is "
                                 "between two items")
            initial, neutral = int(initial), int(neutral)
        box_id = self.patch.dial(long_name, short_name, self.brain, varname_for(long_name), field.minimum,
                                 field.maximum, unit, x, y, page, group=group, initial_outside_presets=initial,
                                 inlet=self.brain_inlet, visibility=identity.VISIBILITY_HIDDEN, exponent=exponent,
                                 items=items, kit_neutral=neutral)
        return self.placed_editor(box_id, long_name, field_name, row, told=True)

    def editor_menu(self, field_name, row, long_name, short_name, x, y, w, page, group=None):
        """A Hidden live.menu showing and setting a choice field of row `row` (0-based)."""
        field, initial, neutral = self.editor(field_name, row, long_name, ChoiceField)
        box_id = self.patch.menu(long_name, short_name, field.items, x, y, w, page, initial_outside_presets=initial,
                                 group=group, visibility=identity.VISIBILITY_HIDDEN, kit_neutral=neutral)
        return self.placed_editor(box_id, long_name, field_name, row)

    def editor_toggle(self, field_name, row, long_name, short_name, x, y, w, page, group=None):
        """A Hidden live.text toggle showing and setting a two-item choice field of row `row` (0-based): off is the
        first item."""
        field, initial, neutral = self.editor(field_name, row, long_name, ChoiceField)
        if len(field.items) != 2:
            raise BuildError(f"{self.patch.device_name}: {long_name!r}: a toggle shows two items, {field_name} has "
                             f"{field.items}")
        box_id = self.patch.toggle(long_name, short_name, x, y, w, layout_rules.ROW_H, page,
                                   initial_outside_presets=initial, group=group, visibility=identity.VISIBILITY_HIDDEN,
                                   kit_neutral=neutral)
        return self.placed_editor(box_id, long_name, field_name, row)

    # ---- the brain ----------------------------------------------------------------------------------------------

    def brain_spec(self):
        init = self.patch.initial_values[self.name]
        fields = [field.brain_spec(self.shifts[field.name]) if isinstance(field, ChoiceField) else field.brain_spec()
                  for field in self.fields]
        return {"outlet": self.brain_outlet, "rows": self.row_count, "fields": fields, "switchBits": self.switch_bits,
                "parameters": [{"varname": varname_for(long_name), "field": field_name, "row": row}
                               for long_name, field_name, row in self.parameters],
                "editors": {varname: {"field": field_name, "row": row}
                            for varname, (field_name, row) in self.editors.items()},
                "values": {name: list(values) for name, values in init.columns.items()}}

    def wire_writes(self):
        """The brain's writes (`<varname> <code>` to a stored parameter, `<editor varname> set <value>` to an editor)
        through one route from its outlet."""
        targets = list(self.stored_boxes.items()) + list(self.editor_boxes.items())
        route = self.patch.box("route " + " ".join(varname for varname, _ in targets),
                               rect=(1100, 1700 + 2 * len(self.patch.boxes), 600, 22), ins=1, outs=len(targets) + 1)
        self.patch.wire(self.brain, route, self.brain_outlet, 0)
        self.patch.script_outlet_of_block(self.brain, self.brain_outlet, STORED_TABLE_OUTLET_EXPRESSION,
                                          f"stored table {self.name!r}")
        for outlet_index, (_, target_box) in enumerate(targets):
            self.patch.wire(route, target_box, outlet_index, 0)


def stored_tables_brain_code(tables):
    """The stored tables' code for the device's brain (its /*STORED_TABLES*/), once every editor is placed; wires
    each table's writes."""
    names = [table.name for table in tables]
    if not tables or len(set(names)) != len(names):
        raise BuildError(f"stored_tables_brain_code needs stored tables with different names, not {names}")
    for table in tables:
        if table.code_given:
            raise BuildError(f"{table.patch.device_name}: stored table {table.name!r}'s brain code was asked for twice")
        table.code_given = True
        table.wire_writes()
    return fill_template(kit_template_text("stored-table.template.js"), {
        "STORED_TABLES": json.dumps({table.name: table.brain_spec() for table in tables})},
        "the kit's stored table template").strip()

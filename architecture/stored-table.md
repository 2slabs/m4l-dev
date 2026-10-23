# The stored table

A device's table of values (rows x fields: a sequencer's stages, a pattern's steps) that the set and every preset
keep, that the brain and the DSP read, and that is **not** automated: Live's Stored Only parameters, packed 16 bits
each. A block (overview.md, "Blocks"): `twosl_dsp/stored_table.py`, `templates/stored-table.template.js`, tests in
tests/test_stored_table.py and tests/kit-scripts.test.js (the fixture device has one).

Why not a Live parameter per value: 16 stages x 10 values is ~170 parameters in Live's automation list, Push's banks
and the lock (2sl gate, Graham 2026-10-21: the stages are stored with the set like 2sl drums' pattern, not
automatable). Why not the brain's own memory: Live saves only parameters with a set; Stored Only is the visibility
for "parameters that are part of the device's persistent state but should not be automated or exposed to control
surfaces" (references/README.md, "Live presets").

## The pattern

- **Fields**: `ContinuousField(name, low, high)` (two whole numbers; held at `codes_per_unit` = 65535 // (high - low)
  steps a unit, so every whole number is exact: -24..24 at 1365 a semitone, -100..100 at 327 a percent) and
  `ChoiceField(name, items)` (held as the item's index).
- **Parameters**: each continuous field of each row is one Stored Only parameter, `<table> <field> <row>` (rows
  1..n in names, 0..n-1 in code); a row's choice fields share one, `<table> switches <row>`, packed low bits first in
  the order given (at most 16 bits; more fails the build). Every value is a whole number 0..65535 (`DevicePatchBuilder
  .stored`). Their long names are the table's identity to Live: renaming a table or a field is a lock change.
- **In the preset book** the table is saved like a control, by its name: `{field: [one value per row]}` in each
  field's own units (a number; an item name). Init gives every field; a preset gives the fields it changes, each
  whole, and keeps Init's others. A value between codes is held on the nearest code (half up, as the brain rounds).
  A preset's held value is a `HeldTable`; `preset_book.stored_only_values_of_preset` turns it into its parameters'
  values for every output: Live preset files, the header's Preset menu and the plugin's presets. A device gives
  `stored_only_values_of_preset` only for Stored Only parameters of its own (`patch.stored`).
- **Outside presets**: a table presets leave alone (2sl drums' pattern: its presets are kit sounds) is given
  `initial_outside_presets={field: [one value per row]}` (every field, own units), as a control is: that is its
  initial value, the preset book can't name it, the Preset menu doesn't set it. Live preset files hold every Stored
  Only parameter, so a device with Live preset files fails to build with such a table.
- **Migrating** state into a table is the preset book's business: a device's migration script writes the table's
  fields into the book's presets (2sl gate: each Lane's steps into Seq B's row).
- **The brain holds the table** and is the only thing that changes it (`/*STORED_TABLES*/`, filled by
  `stored_tables_brain_code(tables)` once every editor is placed; it also wires each table's writes):
  - Live recalls a parameter (a set loading, a Live preset, the Preset menu, which sets the parameters as Live
    would): `<its varname> <code>` reaches the brain, which unpacks it, keeps each changed value, shows it on its
    editors and calls the table's listener;
  - the device's own code calls `storedTableSet(table, field, row, value)` (a display dragged): the value on the
    stored grid is kept, written to its parameter (`<varname> <code>` out of the table's outlet, through a route to
    the parameter, which puts it out again: the echo is no change), shown on its editors, the listener told;
  - reads: `storedTableValue(table, field, row)`, `storedTableRow(table, row)`; a choice's value is its index.
  - `storedTableListen(table, function (field, row, value) {...})`: one listener a table, told of every change. It is
    how the DSP gets the table: the device forwards each change to its gen~ in whatever form its DSP reads.
  - Every bad message (a code out of range, a value outside a field, an unknown table, field or row) is an `error()`
    and changes nothing.
- **Editors**: Hidden controls (not saved, not automated, not in Live's undo history: the Production Guidelines'
  choice for a control the patch drives itself, references/README.md) that show and set one value each:
  `editor_dial` (a continuous field; with `items=` a stepped dial naming each whole number of a field that is an
  index 0..n-1, as a stage's Time on a list of lengths), `editor_menu` and `editor_toggle` (a choice field; a
  toggle's off is the first item). Each needs Info View text. An editor's initial value (its double-click target) is
  its field's neutral, from the preset book's `"neutral": {table: {field: value}}` (presets.md, "Neutral, Init, and a
  fresh device"): the build fails on an editor whose field has none, and on a table neutral naming a field the table
  hasn't or given for a table with no editors. They tell the brain `<their varname> <value>`; the brain sets them back with
  `set` (no output) whenever the value changes from anywhere else. Until the device is ready (the device calls
  `storedTableReady()` on the header's ready) an editor's value is ignored: while a set loads, editors put out their
  initial values, which must not overwrite the recalled table. At ready every editor is set from the table.
  A page that shows one field of every row at a time puts each field's editors in a group (`groups_selected_by`).

## Not in it

- The DSP's copy: a gen~ reads a table in the form its algorithm wants (Params a stage, a buffer); the listener is
  the seam.
- Undo of an edit: Stored Only changes are Live's to undo or not; the kit has no source either way.
- A plugin's view of the editors: Hidden parameters are host parameters to a plugin port's host parameters unless
  left out by name (as Page is); a device porting a table to a plugin leaves its editors out the same way.

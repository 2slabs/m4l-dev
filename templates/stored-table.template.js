// ---- the 2sl-dsp kit's stored tables (templates/stored-table.template.js; architecture/stored-table.md) ----------
// A table of values (rows x fields) Live saves with the set and in presets as Stored Only parameters, 16 bits each
// (twosl_dsp/stored_table.py packs them the same way). The brain holds the table and is the only thing that changes it:
//   - Live recalls a stored parameter (a set loading, a Live preset, the Preset menu): `<its varname> <code>` comes
//     in; the brain unpacks it, keeps each changed value, shows it on its editor, and tells the table's listener;
//   - an editor (a Hidden control showing one value) is turned: `<its varname> <value>`, taken once the device is
//     ready (before that, editors are only putting out their initial values while the set loads: ignored);
//   - the device's own code calls storedTableSet (a display dragged): the value, on the stored grid, is kept, written
//     to its stored parameter, shown on its editor, and the listener told.
// The script that includes this defines DEVICE_NAME, passes every control message to storedTableMessage(name, args)
// (true when it took it), calls storedTableReady() when the device is ready, and reads the table with
// storedTableValue / storedTableRow; storedTableListen(table, function (field, row, value) {...}) hears every change
// (the DSP's copy). Rows are 0-based; a choice field's value is its item's index.
var STORED_TABLES = /*STORED_TABLES*/;
var STORED_VALUE_HIGHEST = 65535;
var storedTableReadyNow = false;
var storedTableListeners = {};
var storedTableParameterByVarname = {};          // varname -> {table, parameter}
var storedTableEditorByVarname = {};             // varname -> {table, field, row}
var storedTableFieldByName = {};                 // table -> field name -> field
(function () {
  for (var table in STORED_TABLES) {
    var spec = STORED_TABLES[table];
    storedTableFieldByName[table] = {};
    for (var f = 0; f < spec.fields.length; f++) storedTableFieldByName[table][spec.fields[f].name] = spec.fields[f];
    for (var p = 0; p < spec.parameters.length; p++) {
      storedTableParameterByVarname[spec.parameters[p].varname] = { table: table, parameter: spec.parameters[p] };
    }
    for (var editor in spec.editors) {
      storedTableEditorByVarname[editor] = { table: table, field: spec.editors[editor].field, row: spec.editors[editor].row };
    }
  }
})();

/** The field `field` of `table`, or an error naming what is wrong (null). */
function storedTableField(table, field, row) {
  var spec = STORED_TABLES[table];
  if (!spec) { error(DEVICE_NAME + ": no stored table '" + table + "'\n"); return null; }
  var found = storedTableFieldByName[table][field];
  if (!found) { error(DEVICE_NAME + ": stored table " + table + " has no field '" + field + "'\n"); return null; }
  if (!(row >= 0 && row < spec.rows && row === Math.floor(row))) {
    error(DEVICE_NAME + ": stored table " + table + " has rows 0-" + (spec.rows - 1) + ", not " + row + "\n");
    return null;
  }
  return found;
}

/** A continuous value on the stored grid: the code Live keeps, as the Python side rounds it (half up). */
function storedTableCode(field, value) { return Math.floor((value - field.minimum) * field.codesPerUnit + 0.5); }
function storedTableHeldOfCode(field, code) { return field.minimum + code / field.codesPerUnit; }

/** The value of `field` in row `row` of `table` (a choice: its item's index); undefined, with an error, if none. */
function storedTableValue(table, field, row) {
  if (!storedTableField(table, field, row)) return undefined;
  return STORED_TABLES[table].values[field][row];
}

/** Row `row` of `table` as {field: value}. */
function storedTableRow(table, row) {
  var spec = STORED_TABLES[table];
  if (!spec || !storedTableField(table, spec.fields[0].name, row)) return undefined;
  var values = {};
  for (var f = 0; f < spec.fields.length; f++) values[spec.fields[f].name] = spec.values[spec.fields[f].name][row];
  return values;
}

/** Hear every change of `table`: listener(field, row, value). One listener a table. */
function storedTableListen(table, listener) {
  if (!STORED_TABLES[table]) { error(DEVICE_NAME + ": no stored table '" + table + "' to listen to\n"); return; }
  if (typeof listener !== "function") { error(DEVICE_NAME + ": stored table " + table + "'s listener isn't a function\n"); return; }
  storedTableListeners[table] = listener;
}

/** Keep a value already checked and on its grid: show it on its editors (but `fromEditor`), tell the listener. */
function storedTableKeep(table, field, row, value, fromEditor) {
  var spec = STORED_TABLES[table];
  if (spec.values[field][row] === value) return false;
  spec.values[field][row] = value;
  if (storedTableReadyNow) {
    for (var editor in spec.editors) {
      if (editor !== fromEditor && spec.editors[editor].field === field && spec.editors[editor].row === row) {
        outlet(spec.outlet, editor, "set", value);
      }
    }
  }
  if (storedTableListeners[table]) storedTableListeners[table](field, row, value);
  return true;
}

/** The stored parameter holding `field` of `row`, and its code now. */
function storedTableWrite(table, field, row) {
  var spec = STORED_TABLES[table];
  var fieldSpec = storedTableFieldByName[table][field];
  for (var p = 0; p < spec.parameters.length; p++) {
    var parameter = spec.parameters[p];
    if (parameter.row !== row) continue;
    if (fieldSpec.kind === "continuous" && parameter.field === field) {
      outlet(spec.outlet, parameter.varname, storedTableCode(fieldSpec, spec.values[field][row]));
      return;
    }
    if (fieldSpec.kind === "choice" && parameter.field === null) {
      var code = 0;
      for (var f = 0; f < spec.fields.length; f++) {
        var other = spec.fields[f];
        if (other.kind === "choice") code += spec.values[other.name][row] * Math.pow(2, other.shift);
      }
      outlet(spec.outlet, parameter.varname, code);
      return;
    }
  }
  error(DEVICE_NAME + ": stored table " + table + " has no parameter for " + field + " row " + row + " (a build error)\n");
}

/** Set `field` of `row` in `table` to `value` (a choice: an index): kept on the stored grid, stored, shown, heard.
 *  `fromEditor`: the editor that set it (not told back). Returns the value kept, or undefined on an error. */
function storedTableSet(table, field, row, value, fromEditor) {
  var fieldSpec = storedTableField(table, field, row);
  if (!fieldSpec) return undefined;
  var kept;
  if (fieldSpec.kind === "continuous") {
    if (!(value >= fieldSpec.minimum && value <= fieldSpec.maximum)) {
      error(DEVICE_NAME + ": " + table + " " + field + " " + (row + 1) + " got " + value + ", outside " +
            fieldSpec.minimum + ".." + fieldSpec.maximum + ": ignored\n");
      return undefined;
    }
    kept = storedTableHeldOfCode(fieldSpec, storedTableCode(fieldSpec, value));
  } else {
    if (!(value >= 0 && value < fieldSpec.items.length && value === Math.floor(value))) {
      error(DEVICE_NAME + ": " + table + " " + field + " " + (row + 1) + " got " + value + ", not one of its " +
            fieldSpec.items.length + " items: ignored\n");
      return undefined;
    }
    kept = value;
  }
  if (storedTableKeep(table, field, row, kept, fromEditor)) storedTableWrite(table, field, row);
  return kept;
}

/** A stored parameter's code, as Live recalled it: unpacked into its row's values. */
function storedTableRecall(table, parameter, code) {
  var spec = STORED_TABLES[table];
  if (!(code >= 0 && code <= STORED_VALUE_HIGHEST && code === Math.floor(code))) {
    error(DEVICE_NAME + ": " + parameter.varname + " got " + code + ", not a whole number 0.." + STORED_VALUE_HIGHEST +
          ": ignored\n");
    return;
  }
  if (parameter.field !== null) {
    var fieldSpec = storedTableFieldByName[table][parameter.field];
    var held = storedTableHeldOfCode(fieldSpec, code);
    if (held > fieldSpec.maximum) {
      error(DEVICE_NAME + ": " + parameter.varname + " got " + code + ", past " + parameter.field + "'s " +
            fieldSpec.maximum + ": ignored\n");
      return;
    }
    storedTableKeep(table, parameter.field, parameter.row, held, null);
    return;
  }
  if (code >= Math.pow(2, spec.switchBits)) {
    error(DEVICE_NAME + ": " + parameter.varname + " got " + code + ", past the row's " + spec.switchBits +
          " bits of switches: ignored\n");
    return;
  }
  var indices = {};
  for (var f = 0; f < spec.fields.length; f++) {
    var choice = spec.fields[f];
    if (choice.kind !== "choice") continue;
    var index = Math.floor(code / Math.pow(2, choice.shift)) % Math.pow(2, choice.bits);
    if (index >= choice.items.length) {
      error(DEVICE_NAME + ": " + parameter.varname + " got " + code + ": " + choice.name + " " + index +
            " is no item: the row's switches ignored\n");
      return;
    }
    indices[choice.name] = index;
  }
  for (var name in indices) storedTableKeep(table, name, parameter.row, indices[name], null);
}

/** The device is ready (Live has recalled the set): editors are taken from now on, and every one shows the table. */
function storedTableReady() {
  storedTableReadyNow = true;
  for (var table in STORED_TABLES) {
    var spec = STORED_TABLES[table];
    for (var editor in spec.editors) {
      outlet(spec.outlet, editor, "set", spec.values[spec.editors[editor].field][spec.editors[editor].row]);
    }
  }
}

function storedTableMessage(name, args) {
  var parameter = storedTableParameterByVarname[name];
  if (parameter) {
    storedTableRecall(parameter.table, parameter.parameter, args[0]);
    return true;
  }
  var editor = storedTableEditorByVarname[name];
  if (editor) {
    if (storedTableReadyNow) storedTableSet(editor.table, editor.field, editor.row, args[0], name);
    return true;
  }
  return false;
}

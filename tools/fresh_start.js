// Run a built device's UI script the way Live loads it, in node (tools/max_sandbox.js), and print what every control
// holds after the header's ready: node tools/fresh_start.js <device folder> [<saved values JSON>]
// The saved values ({varname: number}) are what a set or preset recalls before ready; a control it doesn't name holds
// Live's initial value (its neutral, the fresh-start flag 0). Prints {"values": {varname: number}, "errors": [...],
// "posts": [...]} (twosl_dsp/fresh_start.py reads it).
"use strict";
const vm = require("vm");
const fs = require("fs");
const path = require("path");
const { sandbox, deliverMessage } = require(path.join(__dirname, "max_sandbox.js"));

const folder = process.argv[2];
if (!folder) throw new Error("usage: node tools/fresh_start.js <device folder> [<saved values JSON>]");
const scriptName = path.basename(folder);
const patch = JSON.parse(fs.readFileSync(path.join(folder, scriptName + ".maxpat"), "utf8"));
const values = {};
for (const box of patch.patcher.boxes.map((b) => b.box)) {
  const valueof = box.saved_attribute_attributes && box.saved_attribute_attributes.valueof;
  if (box.varname && valueof && valueof.parameter_initial) values[box.varname] = valueof.parameter_initial[0];
}
Object.assign(values, JSON.parse(process.argv[3] || "{}"));
const { context, record } = sandbox(1, {
  max: { getcolor: () => [0.149, 0.149, 0.149, 1] },
  patcher: { getnamed: (name) => ({
    message: function () {
      const args = Array.prototype.slice.call(arguments);
      if (args.length === 1 && typeof args[0] === "number") values[name] = args[0];
    },
    getvalueof: () => values[name],
  }) },
});
vm.runInContext(fs.readFileSync(path.join(folder, scriptName + "-ui.js"), "utf8"), context);
deliverMessage(context, 0, "ready", []);
process.stdout.write(JSON.stringify({ values, errors: record.errors, posts: record.posts }));

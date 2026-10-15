// The hits 2sl drums' pattern engine plays, as JSON, for tools/render_drums.py:
//   node tools/drums_hits.js '<{"bars": n, "tempo": bpm, "seed": n}>'
// Loads devices/2sl-drums/2sl-drums.js in tools/max_sandbox.js (as tests/2sl-drums.test.js does) and plays its Init
// pattern (presets are kit sounds: they send the brain nothing) for `bars` bars of Live's transport. Prints
// [{sixteenth, messages: [[name, value], ...]}] with each 16th's messages to gen~ in order.
"use strict";
const vm = require("vm");
const fs = require("fs");
const path = require("path");

const request = JSON.parse(process.argv[2]);
const { sandbox, deliverMessage } = require("./max_sandbox");
const { context, record } = sandbox(request.seed || 1);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "devices", "2sl-drums", "2sl-drums.js"), "utf8"), context);
const toGen = () => record.outlets.filter((o) => o[0] === 0).map((o) => [o[1], o[2]]);
function send(name, value) { deliverMessage(context, 1, name, [value]); }
send("ready");
send("tempo", request.tempo || 120);
send("playing", 1);
const out = [];
for (let s = 0; s < (request.bars || 4) * 16; s++) {
  record.outlets.length = 0;
  send("tick", s * 120);
  out.push({ sixteenth: s, messages: toGen() });
}
if (record.errors.length) {
  process.stderr.write("drums_hits.js: the brain reported errors:\n" + record.errors.join(""));
  process.exit(1);
}
process.stdout.write(JSON.stringify(out));

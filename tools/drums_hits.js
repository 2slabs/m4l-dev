// The hits 2sl drums' pattern engine plays for a preset, as JSON, for tools/render_drums.py:
//   node tools/drums_hits.js '<{"brain": {message: value}, "bars": n, "tempo": bpm, "seed": n}>'
// Loads devices/2sl-drums/2sl-drums.js in tools/max_sandbox.js (as tests/2sl-drums.test.js does), applies the
// preset's brain messages (Style last, after ready, so it loads its first kit), and plays `bars` bars of Live's
// transport. Prints [{sixteenth, messages: [[name, value], ...]}] with each 16th's messages to gen~ in order.
"use strict";
const vm = require("vm");
const fs = require("fs");
const path = require("path");

const request = JSON.parse(process.argv[2]);
const { sandbox } = require("./max_sandbox");
const { context, record } = sandbox(request.seed || 1);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "devices", "2sl-drums", "2sl-drums.js"), "utf8"), context);
const toGen = () => record.outlets.filter((o) => o[0] === 0).map((o) => [o[1], o[2]]);
function send(name, value) { context.inlet = 1; context.messagename = name; context.anything(value); }
send("ready");
send("tempo", request.tempo || 120);
for (const name in request.brain) if (name !== "style") send(name, request.brain[name]);
if ("style" in request.brain) send("style", request.brain.style);
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

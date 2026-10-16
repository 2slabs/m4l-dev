// The kit's generated scripts, run in node with Max's globals stubbed (tools/max_sandbox.js), on a device built from
// the kit's templates: node tests/kit-scripts.test.js <device folder> (tests/test_kit_scripts.py builds the fixture
// device and runs this on it). The UI script: pages, Stop, the theme, loud failures. The views script: every display
// paints without an error, takes its messages, refuses others.
"use strict";
const vm = require("vm");
const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { sandbox, deliverMessage } = require(path.join(__dirname, "..", "tools", "max_sandbox.js"));

const DEVICE_FOLDER = process.argv[2];
if (!DEVICE_FOLDER) throw new Error("usage: node tests/kit-scripts.test.js <device folder>");
const SCRIPT_NAME = path.basename(DEVICE_FOLDER);
const UI_SOURCE = fs.readFileSync(path.join(DEVICE_FOLDER, SCRIPT_NAME + "-ui.js"), "utf8");
const VIEWS_SOURCE = fs.readFileSync(path.join(DEVICE_FOLDER, SCRIPT_NAME + "-view.js"), "utf8");
const PATCH = JSON.parse(fs.readFileSync(path.join(DEVICE_FOLDER, SCRIPT_NAME + ".maxpat"), "utf8"));
const VIEW_MODES = PATCH.patcher.boxes.map((b) => b.box).filter((b) => b.maxclass === "jsui").map((b) => b.jsarguments[0]);

const tests = [];
function test(name, body) { tests.push({ name, body }); }

/** Max's globals for [js] and [jsui]: patch objects by scripting name (recording the messages they get), mgraphics
 *  (recording nothing), Task, max.getcolor (Live's dark theme). */
function maxGlobals(record, mode) {
  record.messagesTo = {};
  const graphics = {};
  for (const method of ["init", "set_source_rgba", "rectangle", "fill", "fill_preserve", "stroke", "set_line_width",
                        "move_to", "line_to", "curve_to", "close_path", "redraw"]) graphics[method] = () => {};
  graphics.size = [200, 64];
  return {
    jsarguments: [SCRIPT_NAME + "-view.js", mode],
    mgraphics: graphics,
    Task: function (callback) { this.callback = callback; this.repeat = () => {}; this.cancel = () => {}; },
    max: { getcolor: () => [0.149, 0.149, 0.149, 1], launchbrowser: (url) => record.posts.push("launch " + url) },
    patcher: { getnamed: (name) => ({ message: function () {
      (record.messagesTo[name] = record.messagesTo[name] || []).push(Array.prototype.slice.call(arguments));
    } }) },
  };
}

function load(source, mode) {
  const record = {};
  const made = sandbox(1, {});
  Object.assign(made.record, record);
  Object.assign(made.context, maxGlobals(made.record, mode));
  vm.runInContext(source, made.context);
  return made;
}

test("the UI script shows the first page on ready, and another on page", () => {
  const { context, record } = load(UI_SOURCE);
  deliverMessage(context, 0, "ready", []);
  const shown = (name) => {
    const last = record.outlets.filter((o) => o[2] === "sendbox" && o[3] === name).pop();
    return last && last[5] === 0;
  };
  assert.deepStrictEqual(record.errors, []);
  assert.ok(shown("level") && !shown("mode"), "page one shows, page two doesn't");
  deliverMessage(context, 0, "page", [1]);
  assert.ok(!shown("level") && shown("mode"), "page two shows");
  deliverMessage(context, 0, "page", [7]);
  assert.ok(record.errors.some((e) => /page 7 doesn't exist/.test(e)), "a page that doesn't exist is an error");
});

test("Stop sets every control it turns off to 0", () => {
  const { context, record } = load(UI_SOURCE);
  deliverMessage(context, 0, "stop", []);
  assert.deepStrictEqual(record.messagesTo.bright, [[0]]);
  assert.deepStrictEqual(record.errors, []);
});

test("the theme recolours every control and redraws every display", () => {
  const { context, record } = load(UI_SOURCE);
  deliverMessage(context, 0, "theme", []);
  for (const name of ["level", "bright", "shape", "mode", "page", "volume", "stop"]) {
    assert.ok(record.messagesTo[name] && record.messagesTo[name].length > 3, name + " is recoloured");
  }
  for (const mode of VIEW_MODES) assert.deepStrictEqual(record.messagesTo["view_" + mode], [["theme"]]);
  assert.deepStrictEqual(record.errors, []);
});

test("the UI script refuses messages it doesn't know", () => {
  const { context, record } = load(UI_SOURCE);
  deliverMessage(context, 0, "nonsense", [1]);
  assert.ok(record.errors.some((e) => /doesn't know the message 'nonsense'/.test(e)));
});

test("every display paints without an error, on every page", () => {
  for (const mode of VIEW_MODES) {
    const { context, record } = load(VIEWS_SOURCE, mode);
    for (const page of [0, 1]) {
      deliverMessage(context, 0, "page", [page]);
      context.paint();
    }
    assert.deepStrictEqual(record.errors, [], mode + " painted with errors");
  }
});

test("a display keeps a control's value, takes the device's messages and refuses the rest", () => {
  const { context, record } = load(VIEWS_SOURCE, "level");
  assert.strictEqual(vm.runInContext("S.level", context), 0.5, "the Init value, from the build");
  deliverMessage(context, 0, "level", [0.9]);
  deliverMessage(context, 0, "kick", []);
  assert.strictEqual(vm.runInContext("S.level", context), 0.9);
  assert.strictEqual(vm.runInContext("S.kicks", context), 1);
  deliverMessage(context, 0, "nonsense", [1]);
  context.msg_int(3);
  assert.strictEqual(record.errors.length, 2, record.errors.join(" / "));
});

let failed = 0;
for (const { name, body } of tests) {
  try { body(); console.log("ok   " + name); } catch (problem) { failed++; console.log("FAIL " + name + "\n     " + problem.stack); }
}
console.log((tests.length - failed) + "/" + tests.length + " passed");
process.exit(failed ? 1 : 0);

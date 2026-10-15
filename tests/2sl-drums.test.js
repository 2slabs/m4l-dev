// Tests for 2sl drums' generated scripts, in plain node (no packages): node tests/2sl-drums.test.js
// Run src/2sl-drums.py first: these load devices/2sl-drums/*.js as the device does, with Max's globals stubbed.
// The functions are tested against references/drums/patterns.md (P1, P10, P11, F, B1, B3) and their Info text;
// the engine against the design in PLANS/2026-10-15-2sl-drums-knobs.md (Voice / Function / Seed, applied live,
// commits, Undo) on PLANS/2026-10-15-2sl-drums-functions.md's function model.
"use strict";
const vm = require("vm");
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const ROOT = path.join(__dirname, "..");
const DEVICE = path.join(ROOT, "devices", "2sl-drums");
const BRAIN_SOURCE = fs.readFileSync(path.join(DEVICE, "2sl-drums.js"), "utf8");
const UI_SOURCE = fs.readFileSync(path.join(DEVICE, "2sl-drums-ui.js"), "utf8");
const VIEW_SOURCE = fs.readFileSync(path.join(DEVICE, "2sl-drums-view.js"), "utf8");
const MAXPAT = JSON.parse(fs.readFileSync(path.join(ROOT, "src", "2sl-drums.maxpat"), "utf8"));
const BOXES = MAXPAT.patcher.boxes.map((b) => b.box);
const LINES = MAXPAT.patcher.lines.map((l) => l.patchline);

// ---- a tiny runner ----------------------------------------------------------------------------------------
const tests = [];
function test(name, body) { tests.push({ name, body }); }

// ---- Max stubs: the shared sandbox ----------------------------------------------------------------------
const { sandbox, deliverMessage } = require(path.join(ROOT, "tools", "max_sandbox.js"));

/** The brain in a sandbox. `echoes` is what Live's parameters do with a value the brain sends them (outlet 5):
 *  "now" (the default, Max's way: the live.dial outputs it at once, back into the brain, inside the brain's
 *  outlet call) or "later" (held in brain.heldEchoes until brain.releaseEchoes()). Seed's echo comes back as a
 *  32-bit float, as Live may keep it. */
function loadBrain(seed, echoes) {
  const { context, record } = sandbox(seed === undefined ? 1 : seed);
  vm.runInContext(BRAIN_SOURCE, context, { filename: "2sl-drums.js" });
  const recordOutlet = context.outlet;
  const brain = {
    context, record, heldEchoes: [],
    send(name) { deliverMessage(context, 1, name, Array.prototype.slice.call(arguments, 1)); },
    echo(name, value) {
      if (name === context.SEED_PARAMETER) { brain.send("seed", Math.fround(value)); return; }
      if (name === context.VOICE_PARAMETER) { brain.send("voice", value); return; }
      for (let f = 0; f < context.SETTING_PARAMETERS.length; f++) {
        const p = context.SETTING_PARAMETERS[f].indexOf(name);
        if (p >= 0) { brain.send("param", f, p, value); return; }
      }
      throw new Error("the brain sent an unknown Live parameter " + name);
    },
    releaseEchoes() { const held = brain.heldEchoes.splice(0); for (const [name, value] of held) brain.echo(name, value); },
    note(pitch, velocity) { context.inlet = 0; context.list(pitch, velocity); },
    clear() { record.outlets.length = 0; record.posts.length = 0; },
    lastRows() {
      const rows = record.outlets.filter((o) => o[0] === 1 && o[1] === "rows");
      assert.ok(rows.length, "the brain showed no rows");
      return rows[rows.length - 1].slice(2);
    },
    lastOf(outletIndex, name) {
      const found = record.outlets.filter((o) => o[0] === outletIndex && o[1] === name);
      assert.ok(found.length, "the brain sent no " + name);
      return found[found.length - 1].slice(2);
    },
    historyAt() { return brain.lastOf(2, "history").slice(0, 2); },
    sentToLive() { return record.outlets.filter((o) => o[0] === 5).map((o) => [o[1], o[2]]); },
    /** Function `name` and Voice `voiceId` ("all" for every row), as the dials send them. */
    choose(name, voiceId) {
      const f = context.FUNCTIONS.findIndex((entry) => entry.name === name);
      assert.ok(f >= 0, "no function " + name);
      brain.send("function", f);
      if (voiceId !== undefined) brain.send("voice", voiceId === "all" ? VOICE_IDS.length : VOICE_IDS.indexOf(voiceId));
    },
    /** The active function's setting `name` turned to `value` (its dial). */
    setting(name, value) {
      const f = context.functionIndex, p = context.FUNCTIONS[f].params.findIndex((param) => param.name === name);
      assert.ok(p >= 0, context.FUNCTIONS[f].name + " has no setting " + name);
      brain.send("param", f, p, value);
    },
    /** Seed turned to the active function's variant `position`. */
    seedTo(position) { brain.send("seed", context.seedOfPosition(context.FUNCTIONS[context.functionIndex], position)); },
    settings() { return Array.from(context.functionSettings[context.functionIndex]); },
    /** Play `bars` bars from song 16th `from`; returns [{sixteenth, voice, velocity, delay}] in order. */
    play(bars, from) {
      const start = from || 0, hits = [];
      let pendingDelay = {};
      for (let s = start; s < start + bars * 16; s++) {
        record.outlets.length = 0;
        brain.send("tick", s * 120);
        for (const o of record.outlets) {
          if (o[0] !== 0) continue;
          const match = /^(delay|trig)_([a-z]+)$/.exec(o[1]);
          assert.ok(match, "unexpected message to gen~: " + o[1]);
          if (match[1] === "delay") pendingDelay[match[2]] = o[2];
          else {
            assert.ok(match[2] in pendingDelay, "trig_" + match[2] + " came without its delay first");
            hits.push({ sixteenth: s, voice: match[2], value: o[2], velocity: (o[2] - Math.floor(o[2])) * 2,
                        delay: pendingDelay[match[2]] });
            delete pendingDelay[match[2]];
          }
        }
      }
      return hits;
    },
  };
  context.outlet = function (n, name, value) {
    recordOutlet.apply(null, arguments);
    if (n !== 5) return;
    if (echoes === "later") brain.heldEchoes.push([name, value]);
    else brain.echo(name, value);
  };
  return brain;
}
function readyBrain(seed, echoes) {
  const brain = loadBrain(seed, echoes);
  brain.send("ready");
  brain.send("tempo", 120);
  brain.send("playing", 1);
  return brain;
}
function noErrors(brain) { assert.deepStrictEqual(brain.record.errors, [], "errors: " + brain.record.errors.join(" | ")); }

const VOICE_IDS = ["bd", "sd", "rs", "cp", "ch", "oh", "rd"];
const ALL = VOICE_IDS.length;
const REST = "................";
const P1 = ["x...x...x...x...", "....x.......x...", REST, "....x.......x...", REST, "..x...x...x...x.", REST];

/** The functions as pure calls: run `name` with `settings` (initials for the rest) on `pattern` (row texts). */
function call(brain, name, settings, patternTexts) {
  const c = brain.context, fn = c.FUNCTIONS.find((entry) => entry.name === name);
  assert.ok(fn, "no function " + name);
  const values = {};
  fn.params.forEach((param) => { values[param.name] = param.initial; });
  Object.assign(values, settings || {});
  const made = fn.kind === "generator" ? fn.run(values)
    : fn.run(patternTexts.map((t, v) => c.parseRow(t, "test row " + v)), values);
  return Array.from(made, (row) => (row === null ? null : c.rowText(row)));     // a node array (the brain's is another realm's)
}
function patternWith(rowsById) { return VOICE_IDS.map((id) => rowsById[id] || REST); }
function storedOutlets(brain) { const stored = {}; for (const o of brain.record.outlets) if (o[0] === 4) stored[o[1]] = o[2]; return stored; }

// ---- start-up, storage ------------------------------------------------------------------------------------
test("the Init pattern is P1 (Basic Channel-style), Voice on all, the history one step long", () => {
  const brain = loadBrain();
  brain.send("ready");
  assert.deepStrictEqual(brain.lastRows(), P1);
  assert.deepStrictEqual(brain.lastOf(1, "chosen"), [ALL]);
  assert.deepStrictEqual(brain.historyAt(), [1, 1]);
  assert.deepStrictEqual(brain.lastOf(2, "head"), ["all | canned | seed 1/120"]);
  assert.deepStrictEqual(brain.sentToLive(), [], "Seed already agrees with the initial settings: nothing to send");
  noErrors(brain);
});

test("the stored values' initial values in the patch restore P1", () => {
  const brain = loadBrain(7);
  brain.send("ready");
  brain.choose("random", "all");
  brain.setting("seed", 5);                                       // something else first
  const stored = BOXES.filter((b) => /^steps_/.test(b.varname || ""));
  assert.strictEqual(stored.length, 14);
  const fresh = loadBrain(8);
  for (const b of stored) fresh.send(b.varname, b.saved_attribute_attributes.valueof.parameter_initial[0]);
  fresh.send("ready");
  assert.deepStrictEqual(fresh.lastRows(), P1);
  noErrors(brain); noErrors(fresh);
});

test("persistence: the pattern (live or committed), Voice, Function and the settings come back in a new device", () => {
  const brain = readyBrain(3);
  brain.choose("euclid", "rs");
  brain.setting("hits", 5);
  brain.setting("rotation", 2);
  brain.send("edit", 1, 15);                                      // commits the euclid, then an edit
  brain.choose("shift", "bd");
  brain.setting("steps", 3);                                      // live, not committed: what plays is saved
  const rows = brain.lastRows(), head = brain.lastOf(2, "head"), settings = brain.lastOf(2, "settings");
  const stored = storedOutlets(brain);
  assert.strictEqual(Object.keys(stored).length, 14);
  // what Live saved: every Live parameter's last value (the dials' echoes included), and the hidden steps
  const live = { voice: VOICE_IDS.indexOf("bd"), function: brain.context.functionIndex, seed: null, params: [] };
  for (const o of brain.record.outlets) if (o[0] === 5 && o[1] === "seed") live.seed = Math.fround(o[2]);
  brain.context.FUNCTIONS.forEach((fn, f) => fn.params.forEach((param, p) => live.params.push([f, p, brain.context.functionSettings[f][p]])));
  const reopened = loadBrain(99);
  for (const name in stored) reopened.send(name, stored[name]);
  reopened.send("seed", live.seed);                               // Live restores in its own order
  for (const [f, p, value] of live.params) reopened.send("param", f, p, value);
  reopened.send("function", live.function);
  reopened.send("voice", live.voice);
  reopened.send("ready");
  assert.deepStrictEqual(reopened.lastRows(), rows);
  assert.deepStrictEqual(reopened.lastOf(2, "head"), head);
  assert.deepStrictEqual(reopened.lastOf(2, "settings"), settings);
  assert.deepStrictEqual(reopened.historyAt(), [1, 1], "the history isn't saved: it restarts");
  assert.deepStrictEqual(reopened.sentToLive(), [], "Seed was saved agreeing with the settings: nothing to send");
  assert.deepStrictEqual(reopened.lastOf(1, "chosen"), [0]);
  noErrors(brain); noErrors(reopened);
});

test("at ready, a Seed that disagrees with the restored settings is set from them (the settings are the truth)", () => {
  const brain = loadBrain(4);
  brain.send("function", 2);                                      // euclid
  brain.send("param", 2, 0, 7);
  brain.send("seed", 0);                                          // Live's Seed, from before (or another function)
  brain.send("ready");
  const fn = brain.context.FUNCTIONS[2], position = brain.context.variantPosition(fn, brain.context.functionSettings[2]);
  assert.deepStrictEqual(brain.sentToLive(), [["seed", brain.context.seedOfPosition(fn, position)]]);
  assert.deepStrictEqual(brain.historyAt(), [1, 1]);
  noErrors(brain);
});

test("the stored values echoing back after a change change nothing (and don't redraw)", () => {
  const brain = readyBrain();
  brain.choose("euclid", "rd");
  brain.setting("hits", 3);
  const stored = storedOutlets(brain);                            // what each hidden parameter got last
  brain.clear();
  for (const name in stored) brain.send(name, stored[name]);
  assert.strictEqual(brain.record.outlets.length, 0, "an unchanged stored value redrew or stored again");
  noErrors(brain);
});

// ---- the registry: one source for the functions and their Live parameters -----------------------------------
function longName(entry, param) { return entry.name[0].toUpperCase() + entry.name.slice(1) + " " + param.name[0].toUpperCase() + param.name.slice(1); }
function varnameOf(name) { return name.toLowerCase().replace(/ /g, "_"); }
function boxNamed(varname) { const box = BOXES.find((b) => b.varname === varname); assert.ok(box, "no box " + varname); return box; }
function wiredInto(box) { return LINES.filter((l) => l.source[0] === box.id).map((l) => BOXES.find((b) => b.id === l.destination[0])); }
function reachesBrainInlet1(prepend) {
  const brainBox = BOXES.find((b) => b.text === "js 2sl-drums.js");
  return LINES.some((l) => l.source[0] === prepend.id && l.destination[0] === brainBox.id && l.destination[1] === 1);
}

test("registry -> Live parameters: every setting is one live.dial with the registry's range, initial, unit, Info", () => {
  const c = loadBrain().context, UNIT = { int: 0, "%": 5 };
  const brainBox = BOXES.find((b) => b.text === "js 2sl-drums.js");
  const route = BOXES.find((b) => /^route voice seed /.test(b.text || ""));
  assert.ok(LINES.some((l) => l.source[0] === brainBox.id && l.source[1] === 5 && l.destination[0] === route.id), "outlet 5 -> route");
  const routeNames = route.text.split(" ").slice(1);
  const ui = loadUi();
  let settings = 0;
  c.FUNCTIONS.forEach((entry, f) => {
    entry.params.forEach((param, p) => {
      settings++;
      const name = longName(entry, param), box = boxNamed(varnameOf(name));
      assert.strictEqual(box.maxclass, "live.dial", name);
      const saved = box.saved_attribute_attributes.valueof;
      assert.strictEqual(saved.parameter_longname, name);
      assert.strictEqual(saved.parameter_type, param.max - param.min <= 255 ? 1 : 0, name + ": Int, or a float shown as Int");
      assert.strictEqual(saved.parameter_mmin, param.min, name + " min");
      assert.strictEqual(saved.parameter_mmax, param.max, name + " max");
      assert.deepStrictEqual(saved.parameter_initial, [param.initial], name + " initial");
      assert.strictEqual(saved.parameter_unitstyle, UNIT[param.unit], name + " unit");
      assert.ok(saved.parameter_info.indexOf(param.info) >= 0 && saved.parameter_info.indexOf(entry.info) >= 0, name + " Info");
      assert.strictEqual(c.SETTING_PARAMETERS[f][p], box.varname, name + ": the brain addresses it by its scripting name");
      // its value reaches the brain as `param f p value`; the brain sets it through the route
      const prepend = wiredInto(box);
      assert.deepStrictEqual(prepend.map((b) => b.text), ["prepend param " + f + " " + p], name + " wiring");
      assert.ok(reachesBrainInlet1(prepend[0]));
      const routeOutlet = routeNames.indexOf(box.varname);
      assert.ok(LINES.some((l) => l.source[0] === route.id && l.source[1] === routeOutlet && l.destination[0] === box.id), name + " from the route");
      // shown only while Function picks its function
      assert.strictEqual(box.hidden, f === 0 ? undefined : 1, name + " starts shown only for the first function");
      assert.ok(ui.context.GROUPS.function.members[f].indexOf(box.varname) >= 0, name + " in its function's group");
    });
  });
  const dials = BOXES.filter((b) => b.maxclass === "live.dial" && ui.context.PAGES.pattern.indexOf(b.varname) >= 0);
  assert.strictEqual(dials.length, settings + 2, "the pattern page's dials: Voice, Seed and the settings");
  for (const preset of ui.context.PRESETS) for (const name in preset) {
    assert.ok(!/^(canned|grids|euclid|random|shift|reverse|thin|ghosts|fill|open_hh|accent)_|^(voice|function|seed)$/.test(name), name);
  }
});

test("Voice and Seed dials, Function a button per function (one enum: a knob sweeps it), Seed a float 0-100%", () => {
  const c = loadBrain().context;
  const voice = boxNamed("voice").saved_attribute_attributes.valueof;
  assert.strictEqual(boxNamed("voice").maxclass, "live.dial");
  assert.deepStrictEqual(voice.parameter_enum, VOICE_IDS.concat(["all"]));
  assert.deepStrictEqual(voice.parameter_initial, [ALL]);
  const functionBox = boxNamed("function"), fn = functionBox.saved_attribute_attributes.valueof;
  assert.strictEqual(functionBox.maxclass, "live.tab");
  assert.strictEqual(fn.parameter_type, 2, "one enum parameter");
  assert.strictEqual(functionBox.num_lines_presentation, 2, "two rows of buttons");
  assert.strictEqual(functionBox.presentation_rect[3], 30);
  assert.ok(functionBox.presentation_rect[2] / 6 >= 6 * 7 + 12, "room for 'open hh' in every button");
  assert.deepStrictEqual(fn.parameter_enum, Array.from(c.FUNCTIONS, (f) => f.name));
  assert.deepStrictEqual(fn.parameter_initial, [0]);
  const seed = boxNamed("seed").saved_attribute_attributes.valueof;
  assert.strictEqual(seed.parameter_type, 0, "a float: Live's Int type holds 256 values");
  assert.strictEqual(seed.parameter_mmin, 0);
  assert.strictEqual(seed.parameter_mmax, 100);
  const first = c.FUNCTIONS[0];
  assert.deepStrictEqual(seed.parameter_initial, [c.seedOfPosition(first, c.variantPosition(first, first.params.map((p) => p.initial)))]);
  for (const [name, message] of [["voice", "voice"], ["function", "function"], ["seed", "seed"]]) {
    const prepends = wiredInto(boxNamed(name)).filter((b) => b.text === "prepend " + message);
    assert.strictEqual(prepends.length, 1, name + " -> brain");
    assert.ok(reachesBrainInlet1(prepends[0]));
  }
  assert.ok(wiredInto(boxNamed("function")).some((b) => b.text === "prepend group function"), "Function picks the settings shown");
});

test("a broken registry entry is a loud failure (the build and the device run this check)", () => {
  const c = loadBrain().context;
  const good = c.FUNCTIONS.slice();
  const setting = (extra) => Object.assign({ name: "a", min: 0, max: 4, initial: 1, unit: "int", info: "i" }, extra || {});
  const broken = [
    { name: "x", kind: "neither", info: "i", params: [setting()], order: ["a"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [setting({ initial: 9 })], order: ["a"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [setting({ unit: "dB" })], order: ["a"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "", params: [setting()], order: ["a"], run() {}, summary() {} },
    { name: "canned", kind: "modifier", info: "i", params: [setting()], order: ["a"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [], order: [], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [setting()], order: [], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [setting()], order: ["b"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [setting(), setting({ name: "b" })], order: ["a", "a"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", writes: "oh", params: [setting()], order: ["a"], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [setting({ max: 9999 }), setting({ name: "b", max: 9999 })], order: ["a", "b"],
      run() {}, summary() {} },
  ];
  for (const entry of broken) {
    c.FUNCTIONS.length = 0;
    good.forEach((g) => c.FUNCTIONS.push(g));
    c.FUNCTIONS.push(entry);
    assert.throws(() => c.checkFunctionRegistry(), /function/, JSON.stringify(entry));
  }
});

// ---- the variants: Seed and the settings are one state ---------------------------------------------------------
const ORDERS = { canned: ["kit", "from"], grids: ["density", "x", "y"], euclid: ["rotation", "hits", "steps"],
                 random: ["seed", "accent", "density"], shift: ["steps"], reverse: ["span"], thin: ["amount"],
                 ghosts: ["amount"], fill: ["density", "steps"], "open hh": ["amount"], accent: ["offset", "every"] };
const COUNTS = { canned: 120, grids: 6619136, euclid: 4352, random: 10201000, shift: 31, reverse: 16, thin: 101,
                 ghosts: 101, fill: 1616, "open hh": 101, accent: 256 };

test("every function's order (finest first) and variant count are as declared", () => {
  const c = loadBrain().context;
  assert.deepStrictEqual(Array.from(c.FUNCTIONS, (f) => f.name), Object.keys(ORDERS));
  for (const fn of c.FUNCTIONS) {
    assert.deepStrictEqual(Array.from(fn.order), ORDERS[fn.name], fn.name + " order");
    assert.strictEqual(c.variantCount(fn), COUNTS[fn.name], fn.name + " count");
  }
});

/** Every position of a function with up to 100000 variants; for the big ones (grids, random), the first and last
 *  20000, 2000 around every turn of the second-finest setting and 20000 spread evenly (a full pass takes a minute). */
function positionsToCheck(fn, c) {
  const count = c.variantCount(fn), positions = [];
  if (count <= 100000) { for (let p = 0; p < count; p++) positions.push(p); return positions; }
  for (let p = 0; p < 20000; p++) positions.push(p, count - 1 - p);
  const block = fn.params.find((param) => param.name === fn.order[0]), radix = block.max - block.min + 1;
  const second = fn.params.find((param) => param.name === fn.order[1]), turn = radix * (second.max - second.min + 1);
  for (let k = 1; k * turn < count && k < 1000; k++) positions.push(k * turn - 1, k * turn);
  for (let p = 0; p < 20000; p++) positions.push(Math.floor(p * (count - 1) / 19999));
  return positions;
}

test("mixed radix round trip for every function: position -> settings -> position, and via Seed", () => {
  const c = loadBrain().context;
  for (const fn of c.FUNCTIONS) {
    const count = c.variantCount(fn), seen = new Set();
    for (const position of positionsToCheck(fn, c)) {
      const settings = c.variantSettings(fn, position);
      fn.params.forEach((param, p) => assert.ok(settings[p] >= param.min && settings[p] <= param.max, fn.name + " " + param.name));
      if (count <= 5000) seen.add(settings.join(","));
      if (c.variantPosition(fn, settings) !== position) assert.fail(fn.name + ": " + position + " -> " + settings + " -> " + c.variantPosition(fn, settings));
      // Seed: a float of 0-100%, which Live may keep as a 32-bit float
      if (c.positionOfSeed(fn, Math.fround(c.seedOfPosition(fn, position))) !== position) assert.fail(fn.name + ": Seed loses " + position);
    }
    if (count <= 5000) assert.strictEqual(seen.size, count, fn.name + ": every combination once");
    assert.throws(() => c.variantSettings(fn, count), /no variant/);
  }
});

test("neighbours differ in one setting by one step: the finest, except where it turns round", () => {
  const c = loadBrain().context;
  for (const fn of c.FUNCTIONS) {
    const finest = fn.params.findIndex((param) => param.name === fn.order[0]);
    const radix = fn.params[finest].max - fn.params[finest].min + 1, count = c.variantCount(fn);
    let previous = c.variantSettings(fn, 0);
    for (let position = 1; position < Math.min(count, 50000); position++) {
      const settings = c.variantSettings(fn, position), changed = [];
      for (let p = 0; p < settings.length; p++) if (settings[p] !== previous[p]) changed.push(p);
      if (changed.length !== 1 || Math.abs(settings[changed[0]] - previous[changed[0]]) !== 1) {
        assert.fail(fn.name + " " + (position - 1) + " -> " + position + ": " + previous + " -> " + settings);
      }
      if ((changed[0] === finest) !== (position % radix !== 0)) assert.fail(fn.name + " " + position + ": the finest setting should change");
      previous = settings;
    }
  }
});

// ---- the knobs: live application, commits, Undo ----------------------------------------------------------------
test("turning Seed shows f(base, position) at once (grid, status, playback) and adds no history step", () => {
  const brain = readyBrain();
  brain.choose("euclid", "rs");
  const before = brain.historyAt();
  const fn = brain.context.FUNCTIONS[2];
  const start = brain.context.variantPosition(fn, brain.settings());
  for (const position of [start + 1, start + 2, start + 40, 17]) {
    brain.clear();
    brain.seedTo(position);
    const settings = brain.context.variantSettings(fn, position), values = {};
    fn.params.forEach((param, p) => { values[param.name] = settings[p]; });
    const expected = P1.slice();
    expected[2] = call(brain, "euclid", values)[2];
    assert.deepStrictEqual(brain.lastRows(), expected, "seed " + position);
    assert.deepStrictEqual(brain.settings(), Array.from(settings), "Seed moved the settings");
    assert.deepStrictEqual(brain.lastOf(2, "head"), ["rs | euclid | seed " + (position + 1) + "/4352"]);
    assert.ok(/^live: E\(/.test(brain.lastOf(2, "note")[0]), brain.lastOf(2, "note")[0]);
    assert.deepStrictEqual(brain.historyAt(), before, "no history step while turning");
    const rim = brain.play(1).filter((h) => h.voice === "rs").map((h) => h.sixteenth % 16);
    assert.deepStrictEqual(rim, expected[2].split("").map((g, s) => (g === "." ? -1 : s)).filter((s) => s >= 0), "it plays");
  }
  brain.seedTo(start);
  const startRows = P1.slice();
  startRows[2] = call(brain, "euclid", {})[2];
  assert.deepStrictEqual(brain.lastRows(), startRows, "back where the turning started: f(base, start), not the base");
  assert.deepStrictEqual(brain.lastOf(2, "note"), ["live: E(4,16)", 0]);
  brain.send("undo");
  assert.deepStrictEqual(brain.lastRows(), P1, "Undo brings the base back");
  assert.deepStrictEqual(brain.lastOf(2, "note"), ["the base: turn Seed or a setting", 0]);
  assert.deepStrictEqual(brain.historyAt(), before);
  noErrors(brain);
});

test("turning a setting moves Seed and shows the result; the base is the pattern when the turning started", () => {
  const brain = readyBrain();
  brain.choose("shift", "bd");
  brain.clear();
  brain.setting("steps", 2);
  const fn = brain.context.FUNCTIONS[4];
  assert.deepStrictEqual(brain.sentToLive(), [["seed", brain.context.seedOfPosition(fn, 17)]], "Seed follows (steps -15..15: +2 is 17)");
  assert.strictEqual(brain.lastRows()[0], "..x...x...x...x.");
  brain.setting("steps", 3);
  assert.strictEqual(brain.lastRows()[0], "...x...x...x...x", "f(base, +3), not +3 on +2");
  brain.setting("steps", 0);
  assert.deepStrictEqual(brain.lastRows(), P1, "shift 0 changes nothing: the base");
  assert.deepStrictEqual(brain.historyAt(), [1, 1]);
  noErrors(brain);
});

test("moving Voice or Function commits what is shown as one step, and it is the next base", () => {
  const brain = readyBrain();
  brain.choose("shift", "bd");
  brain.setting("steps", 1);
  brain.setting("steps", 2);
  brain.send("voice", 1);                                        // sd: commit
  assert.deepStrictEqual(brain.historyAt(), [2, 2]);
  assert.ok(/shift \+2 steps on bd/.test(brain.lastOf(2, "history")[2]), brain.lastOf(2, "history")[2]);
  const committed = brain.lastRows();
  assert.strictEqual(committed[0], "..x...x...x...x.");
  brain.setting("steps", 3);                                     // sd now; the shift remembers +2, the turning starts there
  assert.strictEqual(brain.lastRows()[1], ".......x.......x", "f(new base, +3) on sd");
  assert.strictEqual(brain.lastRows()[0], committed[0], "bd stays as committed");
  brain.choose("thin");                                          // Function: commit
  assert.deepStrictEqual(brain.historyAt(), [3, 3]);
  brain.send("voice", ALL);                                      // nothing turned since: no step
  brain.choose("reverse");
  assert.deepStrictEqual(brain.historyAt(), [3, 3], "a commit with nothing changed is no step");
  brain.setting("span", 4);
  brain.setting("span", 1);                                      // span 1 changes nothing: the base
  brain.send("voice", 0);
  assert.deepStrictEqual(brain.historyAt(), [3, 3], "turned to a setting that changes nothing: no step");
  noErrors(brain);
});

test("touching any knob applies the function, the starting settings too: canned kit 3 onto sd", () => {
  const brain = readyBrain();
  brain.choose("canned", "bd");
  brain.setting("kit", 3);                                        // P1 + rim 16ths: bd's row (P1's anyway)
  brain.send("voice", VOICE_IDS.indexOf("rs"));                   // commit; canned remembers kit 3
  assert.deepStrictEqual(brain.lastRows()[2], REST, "Voice only commits, it applies nothing");
  brain.setting("kit", 4);
  brain.setting("kit", 3);                                        // back to the starting settings
  assert.strictEqual(brain.lastRows()[2], brain.context.CANNED_KITS[2].rows.rs, "kit 3's rim row on rs");
  brain.send("voice", 1);
  assert.strictEqual(brain.lastRows()[2], brain.context.CANNED_KITS[2].rows.rs, "committed");
  noErrors(brain);
});

test("Clear: the row Voice picks (every row on all) becomes rests; it commits first, is one step, Undo restores", () => {
  const brain = readyBrain();
  brain.choose("shift", "bd");
  brain.setting("steps", 2);                                      // live
  brain.clear();
  brain.send("clear");
  assert.deepStrictEqual(brain.historyAt(), [3, 3], "the shift committed, then the clear");
  assert.strictEqual(brain.lastRows()[0], REST);
  assert.deepStrictEqual(brain.lastRows().slice(1), P1.slice(1), "only bd");
  assert.ok(/clear bd/.test(brain.lastOf(2, "history")[2]));
  brain.send("clear");
  assert.deepStrictEqual(brain.historyAt(), [3, 3], "clearing an empty row is no step");
  assert.ok(brain.record.posts.some((p) => /bd is already empty: no step/.test(p)));
  brain.send("undo");
  assert.strictEqual(brain.lastRows()[0], "..x...x...x...x.", "Undo brings the shifted row back");
  brain.send("voice", ALL);
  brain.send("clear");
  assert.deepStrictEqual(brain.lastRows(), VOICE_IDS.map(() => REST));
  brain.send("undo");
  assert.strictEqual(brain.lastRows()[1], P1[1]);
  // the button sends `clear` to the brain
  const button = boxNamed("clear"), message = wiredInto(button)[0];
  assert.strictEqual(button.maxclass, "live.text");
  assert.strictEqual(message.text, "clear");
  noErrors(brain);
});

test("a click on a voice name moves Voice like a turn (commits); the picked row again: all; from all: that row", () => {
  const brain = readyBrain();
  brain.choose("shift", "all");
  brain.setting("steps", 1);                                      // live on all
  brain.clear();
  brain.send("name_click", 1);
  assert.deepStrictEqual(brain.sentToLive(), [["voice", 1]], "the Voice dial moves (its echo changes nothing)");
  assert.deepStrictEqual(brain.lastOf(1, "chosen"), [1]);
  assert.deepStrictEqual(brain.historyAt(), [2, 2], "it committed, as turning Voice does");
  brain.clear();
  brain.send("name_click", 1);
  assert.deepStrictEqual(brain.lastOf(1, "chosen"), [ALL], "the picked row again: all");
  assert.deepStrictEqual(brain.sentToLive(), [["voice", ALL]]);
  brain.send("name_click", 5);
  assert.deepStrictEqual(brain.lastOf(1, "chosen"), [5]);
  brain.send("name_click", 2);
  assert.deepStrictEqual(brain.lastOf(1, "chosen"), [2], "another row while one is picked: that row");
  assert.deepStrictEqual(brain.historyAt(), [2, 2], "nothing turned since: no more steps");
  noErrors(brain);
});

test("each function remembers its settings; switching back doesn't re-apply them (the base is the pattern now)", () => {
  const brain = readyBrain();
  brain.choose("euclid", "rd");
  brain.setting("hits", 5);
  brain.choose("shift");                                          // commits euclid on rd
  const now = brain.lastRows();
  brain.choose("euclid");
  assert.deepStrictEqual(brain.settings().slice(0, 1), [5], "euclid kept hits 5");
  assert.deepStrictEqual(brain.lastRows(), now, "coming back shows the pattern as it is");
  const fn = brain.context.FUNCTIONS[2];
  assert.deepStrictEqual(brain.sentToLive().pop(), ["seed", brain.context.seedOfPosition(fn, brain.context.variantPosition(fn, brain.settings()))],
                         "Seed follows the function");
  noErrors(brain);
});

test("Undo: first drops what isn't committed (settings back, no step), then steps back through commits", () => {
  const brain = readyBrain();
  brain.choose("euclid", "rs");
  brain.setting("hits", 5);
  brain.choose("shift", "bd");                                    // commit 1 (euclid on rs)
  const p1 = brain.lastRows();
  brain.send("edit", 6, 0);                                       // commit 2 (an edit)
  const p2 = brain.lastRows();
  brain.setting("steps", 4);                                      // live
  brain.setting("steps", 5);
  assert.deepStrictEqual(brain.historyAt(), [3, 3]);
  brain.clear();
  brain.send("undo");
  assert.deepStrictEqual(brain.lastRows(), p2, "back to the base");
  assert.deepStrictEqual(brain.settings(), [0], "the settings back where the turning started");
  const fn = brain.context.FUNCTIONS[4];
  assert.deepStrictEqual(brain.sentToLive(), [["shift_steps", 0], ["seed", brain.context.seedOfPosition(fn, 15)]]);
  assert.deepStrictEqual(brain.historyAt(), [3, 3], "dropping isn't a step back");
  brain.send("undo"); assert.deepStrictEqual(brain.lastRows(), p1);
  brain.send("undo"); assert.deepStrictEqual(brain.lastRows(), P1);
  assert.deepStrictEqual(brain.historyAt(), [1, 3]);
  brain.clear();
  brain.send("undo");
  assert.ok(brain.record.posts.some((p) => /oldest pattern kept/.test(p)));
  assert.ok(!brain.record.outlets.some((o) => o[0] === 4), "an Undo past the start stored something");
  // a commit after an Undo drops the undone steps (no redo)
  brain.setting("steps", 2);
  brain.send("voice", 1);
  assert.deepStrictEqual(brain.historyAt(), [2, 2]);
  noErrors(brain);
});

test("hand edit: commits what is turned first, then is its own step; a click cycles rest -> hit -> accent -> rest", () => {
  const brain = readyBrain();
  brain.choose("shift", "bd");
  brain.setting("steps", 1);
  brain.send("edit", 6, 5);
  assert.deepStrictEqual(brain.historyAt(), [3, 3], "the shift, then the edit");
  assert.strictEqual(brain.lastRows()[0], ".x...x...x...x..", "the shift is kept");
  assert.strictEqual(brain.lastRows()[6][5], "x");
  brain.send("edit", 6, 5); assert.strictEqual(brain.lastRows()[6][5], "X");
  brain.send("edit", 6, 5); assert.strictEqual(brain.lastRows()[6][5], ".");
  brain.send("edit", 6, 9, 1); assert.strictEqual(brain.lastRows()[6][9], "o");
  brain.send("edit", 6, 9); assert.strictEqual(brain.lastRows()[6][9], "x");
  assert.ok(/edit rd step 10 x/.test(brain.lastOf(2, "history")[2]));
  brain.send("undo"); assert.strictEqual(brain.lastRows()[6][9], "o");
  brain.setting("steps", 2);                                      // the next turning starts on the edited pattern
  assert.strictEqual(brain.lastRows()[6][9], "o");
  noErrors(brain);
});

test("echoes: values the brain sends Live's parameters come back at once and change nothing more", () => {
  const brain = readyBrain(1, "now");
  brain.choose("euclid", "rs");
  brain.clear();
  brain.seedTo(1234);
  const sent = brain.sentToLive();
  const fn = brain.context.FUNCTIONS[2], settings = brain.context.variantSettings(fn, 1234);
  const changedSettings = Array.from(fn.params, (param, p) => [brain.context.SETTING_PARAMETERS[2][p], settings[p]])
    .filter(([name, value], p) => value !== fn.params[p].initial);
  assert.ok(changedSettings.length >= 2, "the test needs a variant that moves several settings");
  assert.deepStrictEqual(sent, changedSettings, "each changed setting once, nothing else");
  assert.deepStrictEqual(brain.historyAt(), [1, 1]);
  const rows = brain.lastRows(), shows = brain.record.outlets.filter((o) => o[0] === 1 && o[1] === "rows").length;
  assert.strictEqual(shows, 1, "the echoes redrew");
  brain.clear();
  brain.setting("hits", 3);
  assert.deepStrictEqual(brain.sentToLive().map((s) => s[0]), ["seed"]);
  assert.strictEqual(brain.record.outlets.filter((o) => o[0] === 1 && o[1] === "rows").length, 1);
  brain.send("voice", 0);
  assert.deepStrictEqual(brain.historyAt(), [2, 2], "one commit");
  brain.send("undo");
  brain.send("undo");
  assert.deepStrictEqual(brain.lastRows(), P1);
  assert.notDeepStrictEqual(rows, P1);
  noErrors(brain);
});

test("echoes that come late (after the next turns) are recognised and change nothing", () => {
  const brain = readyBrain(1, "later");
  brain.choose("euclid", "rs");
  brain.seedTo(300);
  brain.seedTo(301);
  brain.seedTo(2000);
  brain.send("undo");                                             // the settings go back: more sent, all held
  brain.seedTo(900);
  const settings = brain.settings(), rows = brain.lastRows(), head = brain.lastOf(2, "head");
  brain.clear();
  brain.releaseEchoes();
  assert.deepStrictEqual(brain.settings(), settings, "a late echo moved the settings back");
  assert.strictEqual(brain.record.outlets.length, 0, "a late echo redrew, stored or sent something");
  brain.send("voice", 0);
  assert.deepStrictEqual(brain.historyAt(), [2, 2]);
  assert.strictEqual(brain.lastOf(2, "history")[2].indexOf("E(") >= 0, true);
  assert.ok(rows && head);
  noErrors(brain);
});

test("Live sending a parameter the value it has (no change) does nothing; a hidden function's setting is kept", () => {
  const brain = readyBrain(1, "now");
  brain.choose("euclid", "rs");
  brain.clear();
  brain.setting("hits", 4);                                       // the value it has
  brain.send("seed", brain.context.liveParameterValues.seed);
  assert.strictEqual(brain.record.outlets.length, 0);
  brain.send("param", 4, 0, 6);                                   // shift's steps, automated while euclid shows
  assert.strictEqual(brain.record.outlets.length, 0, "a hidden function's setting changes nothing now");
  brain.choose("shift");
  assert.deepStrictEqual(brain.settings(), [6]);
  noErrors(brain);
});

test("all: generators make the whole kit, modifiers change every row; one row: only that row", () => {
  const brain = readyBrain();
  const tresillo = brain.context.CANNED_KITS.findIndex((kit) => kit.name === "P11 tresillo") + 1;
  brain.choose("canned", "all");
  brain.setting("kit", tresillo);
  assert.deepStrictEqual(brain.lastRows(), call(brain, "canned", { kit: tresillo }));
  brain.choose("shift");
  brain.setting("steps", 1);
  assert.deepStrictEqual(brain.lastRows(), call(brain, "shift", { steps: 1 }, call(brain, "canned", { kit: tresillo })));
  brain.choose("canned", "sd");
  brain.setting("kit", 1);                                        // tresillo has no sd: P1's sd on sd only
  const rows = brain.lastRows(), before = call(brain, "shift", { steps: 1 }, call(brain, "canned", { kit: tresillo }));
  assert.strictEqual(rows[1], P1[1]);
  rows.forEach((row, v) => { if (v !== 1) assert.strictEqual(row, before[v], VOICE_IDS[v] + " changed"); });
  assert.deepStrictEqual(brain.lastOf(1, "chosen"), [1]);
  noErrors(brain);
});

test("open hh on one row reads ch and writes only oh; on ch (or another row) it says loudly; on all the hits move", () => {
  const brain = readyBrain();
  brain.choose("canned", "all");
  const p4 = brain.context.CANNED_KITS.findIndex((kit) => kit.name === "P2 motor city") + 1;
  brain.setting("kit", p4);                                       // ch .x.x.x.x.x.x.x.x, oh ..x...x...x...x.
  brain.choose("open hh", "oh");
  const base = brain.lastRows();
  brain.setting("amount", 100);
  const made = call(brain, "open hh", { amount: 100 }, base);
  assert.strictEqual(brain.lastRows()[5], made[5], "oh written");
  assert.strictEqual(brain.lastRows()[4], base[4], "ch only read");
  brain.clear();
  brain.send("voice", VOICE_IDS.indexOf("ch"));                   // commits; now on ch
  assert.ok(brain.record.posts.some((p) => /open hh writes oh, not ch \(it reads ch\)/.test(p)), brain.record.posts.join(" | "));
  assert.deepStrictEqual(brain.lastOf(2, "note"), ["open hh writes oh, not ch (it reads ch)", 1]);
  brain.setting("amount", 50);
  assert.strictEqual(brain.lastRows()[4], base[4], "on ch it still writes oh, not ch");
  brain.send("voice", ALL);
  brain.setting("amount", 100);
  const moved = brain.lastRows();
  assert.strictEqual(moved[4], REST, "on all the closed hats move");
  noErrors(brain);
});

test("the history keeps the last HISTORY_LIMIT patterns; the oldest go", () => {
  const brain = readyBrain(), limit = brain.context.HISTORY_LIMIT;
  assert.strictEqual(limit, 100);
  brain.choose("shift", "bd");
  for (let i = 0; i < limit + 30; i++) {                          // each a new base: turn, then commit with Voice
    brain.setting("steps", i % 2 ? 1 : 2);
    brain.send("voice", (i + 1) % 2);
  }
  assert.strictEqual(brain.context.history.length, limit);
  for (let i = 0; i < limit - 1; i++) brain.send("undo");
  assert.deepStrictEqual(brain.historyAt(), [1, limit]);
  brain.clear();
  brain.send("undo");
  assert.ok(brain.record.posts.some((p) => /oldest pattern kept \(100 at most\)/.test(p)));
  noErrors(brain);
});

test("the status line: voice | function | seed n/count, the settings, what is shown, the history", () => {
  const brain = readyBrain();
  brain.choose("euclid", "ch");
  assert.deepStrictEqual(brain.lastOf(2, "head"), ["ch | euclid | seed 4288/4352"]);
  assert.deepStrictEqual(brain.lastOf(2, "settings"), ["hits 4  rotation 0  steps 16"]);
  brain.setting("hits", 9);
  brain.setting("steps", 4);
  assert.deepStrictEqual(brain.lastOf(2, "note"), ["live: E(4,4)  (only 4 hits fit)", 0]);
  assert.deepStrictEqual(brain.lastOf(2, "history"), [1, 1, "the saved pattern (+ live)"]);
  brain.choose("random");
  assert.deepStrictEqual(brain.lastOf(2, "settings"), ["density 30%  accent 10%  seed 0"]);
  assert.deepStrictEqual(brain.lastOf(2, "history"), [2, 2, "euclid E(4,4)  (only 4 hits fit) on ch"]);
  noErrors(brain);
});

test("a function that fails is a loud error and shows the base", () => {
  const brain = readyBrain();
  brain.context.FUNCTIONS[4].run = function () { return [[1, 2]]; };
  brain.choose("shift", "bd");
  brain.clear();
  brain.setting("steps", 3);
  assert.strictEqual(brain.record.errors.length, 1);
  assert.ok(/shift \+3 steps on bd failed: .* made 1 rows/.test(brain.record.errors[0]), brain.record.errors[0]);
  assert.deepStrictEqual(brain.lastRows(), P1);
  brain.send("voice", 1);
  assert.deepStrictEqual(brain.historyAt(), [1, 1], "the base was shown: no step");
});

// ---- the functions, each on its own ------------------------------------------------------------------------
test("every function is pure: the same input gives the same output, and the input is left as it was", () => {
  const brain = loadBrain(), c = brain.context;
  const input = patternWith({ bd: "x..ox...x..ox...", ch: "xxXxxxXxxxXxxxXx", oh: "..x...x...x...x.", sd: "....X..o....x..." });
  for (const fn of c.FUNCTIONS) {
    const values = {};
    // the middle variant: away from the modifiers' do-nothing initial settings
    const middle = c.variantSettings(fn, Math.floor(c.variantCount(fn) / 2));
    fn.params.forEach((param, p) => { values[param.name] = middle[p]; });
    const pattern = input.map((t) => c.parseRow(t, "test"));
    const before = JSON.stringify(pattern);
    const first = fn.kind === "generator" ? fn.run(values) : fn.run(pattern, values);
    assert.strictEqual(JSON.stringify(pattern), before, fn.name + " changed its input");
    const second = fn.kind === "generator" ? fn.run(values) : fn.run(pattern, values);
    assert.deepStrictEqual(second, first, fn.name + " gave two answers");
    c.checkMade(first, fn);
  }
  noErrors(brain);
});

test("canned: a kit's rows as patterns.md gives them; From puts one voice's row on every row", () => {
  const brain = loadBrain(), c = brain.context;
  assert.deepStrictEqual(call(brain, "canned", { kit: 1 }), P1);
  c.CANNED_KITS.forEach((kit, k) => {
    assert.deepStrictEqual(call(brain, "canned", { kit: k + 1 }), VOICE_IDS.map((id) => kit.rows[id] || REST), kit.name);
  });
  const tresillo = c.CANNED_KITS.findIndex((kit) => kit.name === "P11 tresillo") + 1;
  assert.deepStrictEqual(call(brain, "canned", { kit: tresillo, from: 3 }), VOICE_IDS.map(() => "x..x..x.x..x..x."),
                         "From 3 = the rim's row (P11's tresillo) on every row");
});

test("grids: rows at the map's nodes match patterns.md F's decoding; CP = SD accents, OH = HH offbeat 8ths", () => {
  const brain = loadBrain();
  // F: [map x-row 0, y-col 0] node_10, [x-row 2, y-col 2] node_4, [x-row 1, y-col 3] node_12 (BD, SD, HH)
  const decoded = {
    "0,0": ["x..x..XxoX....x.", ".xxxxxXoXo.o..o.", "X.x.xxxxX.o.xox."],
    "128,128": ["X.ooxoxoX.xo.oo.", "..ooX.x...xoXXx.", "o.XxxoXxooXxxoxx"],
    "64,192": ["X.Xx..oo..XX..xx", ".oo.X..X.xoxX.xx", "XoXoXoxxx.x.xxxx"],
  };
  // density 61% = threshold 99: the steps F marks x (100-192) and X (> 192) play, X as accents
  const playing = (row) => row.replace(/o/g, ".");
  for (const point in decoded) {
    const [x, y] = point.split(",").map(Number);
    const made = call(brain, "grids", { x, y, density: 61 });
    const [bd, sd, hh] = decoded[point].map(playing);
    assert.strictEqual(made[0], bd, "grids " + point + " bd");
    assert.strictEqual(made[1], sd, "grids " + point + " sd");
    assert.strictEqual(made[4], hh, "grids " + point + " ch");
    assert.strictEqual(made[3], sd.replace(/x/g, "."), "grids " + point + " cp: the SD channel's accents");
    assert.strictEqual(made[5], hh.split("").map((g, s) => (s % 4 === 2 ? g : ".")).join(""), "grids " + point + " oh");
    assert.strictEqual(made[2], null, "rs has no Grids channel");
    assert.strictEqual(made[6], null, "rd has no Grids channel");
  }
  assert.ok(call(brain, "grids", { density: 0 }).every((row) => row === null || row === REST), "density 0 plays nothing");
});

test("grids on all keeps the rows Grids has no channel for, and says so; on rs alone it says so loudly", () => {
  const brain = readyBrain();
  brain.send("edit", 2, 5);                                      // a rim hit
  const rim = brain.lastRows()[2];
  brain.clear();
  brain.choose("grids", "all");
  brain.setting("density", 80);
  assert.strictEqual(brain.lastRows()[2], rim);
  assert.ok(brain.record.posts.some((p) => /grids has nothing for rs rd: kept as they are/.test(p)), brain.record.posts.join(" | "));
  assert.deepStrictEqual(brain.lastOf(2, "note"), ["grids has nothing for rs rd: kept as they are", 1]);
  brain.clear();
  brain.choose("grids", "rs");
  assert.deepStrictEqual(brain.lastOf(2, "note"), ["grids has nothing for rs: kept as it is", 1]);
  assert.ok(brain.record.posts.some((p) => /grids has nothing for rs: kept as it is/.test(p)), "posted when the target changes");
  noErrors(brain);
});

test("euclid: Toussaint's rhythms (P11), rotation, cycles shorter than the bar repeat (P10's 3-step loop)", () => {
  const brain = loadBrain(), c = brain.context;
  const asText = (onsets) => onsets.map((o) => (o ? "x" : ".")).join("");
  const toussaint = { "3,8": "x..x..x.", "5,8": "x.xx.xx.", "2,5": "x.x..", "3,4": "x.xx", "3,7": "x.x.x..",
                      "4,12": "x..x..x..x..", "5,12": "x..x.x..x.x.", "5,16": "x..x..x..x..x...", "0,4": "....", "4,4": "xxxx" };
  for (const kn in toussaint) assert.strictEqual(asText(c.euclidean(...kn.split(",").map(Number))), toussaint[kn], "E(" + kn + ")");
  for (let k = 0; k <= 16; k++) assert.strictEqual(c.euclidean(k, 16).filter((o) => o).length, k, "E(" + k + ",16) onsets");
  assert.strictEqual(call(brain, "euclid", { hits: 5, steps: 16 })[0], "x..x..x..x..x...");
  assert.strictEqual(call(brain, "euclid", { hits: 5, steps: 16, rotation: 2 })[0], "..x..x..x..x..x.");
  assert.strictEqual(call(brain, "euclid", { hits: 1, steps: 3 })[0], "x..x..x..x..x..x", "P10's 3-16th loop");
  assert.strictEqual(call(brain, "euclid", { hits: 1, steps: 5 })[0], "x....x....x....x", "P10's 5-16th loop");
  assert.strictEqual(call(brain, "euclid", { hits: 9, steps: 4 })[0], "xxxxxxxxxxxxxxxx", "more hits than steps: all of them");
  const fn = c.FUNCTIONS.find((f) => f.name === "euclid");
  assert.ok(/only 4 hits fit/.test(fn.summary({ hits: 9, steps: 4, rotation: 0 })), "the summary must say hits were cut");
});

test("random: a seed gives the same rows every time, another seed others; density and accent are chances", () => {
  const brain = loadBrain();
  const a = call(brain, "random", { seed: 42 }), b = call(brain, "random", { seed: 42 }), d = call(brain, "random", { seed: 43 });
  assert.deepStrictEqual(a, b);
  assert.notDeepStrictEqual(a, d);
  assert.ok(new Set(a).size > 1, "every row the same");
  assert.ok(call(brain, "random", { seed: 3, density: 0 }).every((row) => row === REST));
  assert.ok(call(brain, "random", { seed: 3, density: 100, accent: 0 }).every((row) => row === "xxxxxxxxxxxxxxxx"));
  assert.ok(call(brain, "random", { seed: 3, density: 100, accent: 100 }).every((row) => row === "XXXXXXXXXXXXXXXX"));
  let hits = 0;
  for (let seed = 1; seed <= 40; seed++) call(brain, "random", { seed, density: 30, accent: 0 }).forEach((row) => { hits += row.split("x").length - 1; });
  const share = hits / (40 * 7 * 16);
  assert.ok(share > 0.26 && share < 0.34, "density 30% gave " + (100 * share).toFixed(1) + "% hits");
});

test("shift: later for +, earlier for -, wrapping (Ableton's Rhythm Shift, B3); +n then -n is the identity", () => {
  const brain = loadBrain();
  const row = "x..ox...X..o....";
  assert.strictEqual(call(brain, "shift", { steps: 1 }, [row])[0], ".x..ox...X..o...");
  assert.strictEqual(call(brain, "shift", { steps: -1 }, [row])[0], "..ox...X..o....x");
  for (let n = -15; n <= 15; n++) {
    const moved = call(brain, "shift", { steps: n }, [row]);
    assert.strictEqual(call(brain, "shift", { steps: -n }, moved)[0], row);
  }
});

test("reverse: each span backwards from its first step; span 16 = the bar (step 1 stays); 1 and 2 change nothing", () => {
  const brain = loadBrain();
  assert.deepStrictEqual(call(brain, "reverse", { span: 16 }, ["xX..o..........."]), ["x...........o..X"]);
  assert.deepStrictEqual(call(brain, "reverse", { span: 16 }, P1), P1);
  assert.deepStrictEqual(call(brain, "reverse", { span: 4 }, ["xXo.x..o........"]), ["x.oXxo.........."]);
  assert.deepStrictEqual(call(brain, "reverse", { span: 5 }, ["xXo.x.x........X"]), ["xx.oX....x.....X"],
                         "groups of 5, 5, 5 and the last step alone");
  const row = "x..ox...X..o..x.";
  for (let span = 1; span <= 16; span++) {
    assert.strictEqual(call(brain, "reverse", { span }, call(brain, "reverse", { span }, [row]))[0], row, "twice, span " + span);
  }
  assert.strictEqual(call(brain, "reverse", { span: 1 }, [row])[0], row);
  assert.strictEqual(call(brain, "reverse", { span: 2 }, [row])[0], row);
});

test("thin: ghosts go first, then hits, then accents, the weakest place in the bar first (Grids' density, B1)", () => {
  const brain = loadBrain();
  assert.strictEqual(call(brain, "thin", { amount: 25 }, ["x...x...x...x..."])[0], "x...x...x.......", "beat 4 before beat 2 (later first)");
  assert.strictEqual(call(brain, "thin", { amount: 50 }, ["x...x...x...x..."])[0], "x.......x.......");
  assert.strictEqual(call(brain, "thin", { amount: 20 }, ["X..oX...o...X..."])[0], "X...X...o...X...", "ghosts first, the weaker place first");
  assert.strictEqual(call(brain, "thin", { amount: 40 }, ["X..oX...o...X..."])[0], "X...X.......X...", "ghosts first");
  assert.strictEqual(call(brain, "thin", { amount: 50 }, ["X.x.X.x........."])[0], "X...X...........", "hits before accents");
  assert.strictEqual(call(brain, "thin", { amount: 100 }, ["XxoXxoXxoXxoXxoX"])[0], REST);
  assert.strictEqual(call(brain, "thin", { amount: 0 }, ["XxoXxoXxoXxoXxoX"])[0], "XxoXxoXxoXxoXxoX");
});

test("ghosts: rests just before a hit first (P6's ghost kicks), then the weakest places; ghosts play at velocity 0.2", () => {
  const brain = readyBrain();
  assert.strictEqual(call(brain, "ghosts", { amount: 25 }, ["x...x...x...x..."])[0], "x..ox..ox..ox...");
  assert.strictEqual(call(brain, "ghosts", { amount: 100 }, ["x...x...x...x..."])[0], "xoooxoooxoooxooo");
  brain.choose("ghosts", "bd");
  brain.setting("amount", 25);
  const kicks = brain.play(1).filter((h) => h.voice === "bd");
  assert.deepStrictEqual(kicks.map((h) => [h.sixteenth % 16, +h.velocity.toFixed(3)]),
                         [[0, 0.7], [3, 0.2], [4, 0.7], [7, 0.2], [8, 0.7], [11, 0.2], [12, 0.7]]);
  noErrors(brain);
});

test("fill: hits on the rests of the bar's last steps, spread evenly (B2's FILL, P11)", () => {
  const brain = loadBrain();
  assert.strictEqual(call(brain, "fill", { steps: 4, density: 50 }, ["x...x...x...x..."])[0], "x...x...x...x.x.");
  assert.strictEqual(call(brain, "fill", { steps: 8, density: 100 }, ["x...x...x...X..."])[0], "x...x...xxxxXxxx", "an accent stays");
  assert.strictEqual(call(brain, "fill", { steps: 8, density: 50 }, [REST])[0], "........x.x.x.x.");
  assert.strictEqual(call(brain, "fill", { steps: 4, density: 0 }, [REST])[0], REST);
});

test("open hh (the function): closed hats' hits move to the open hat, offbeat 8ths first", () => {
  const brain = loadBrain();
  const input = patternWith({ ch: "x.x.x.x.x.x.x.x.", oh: REST });
  const half = call(brain, "open hh", { amount: 50 }, input);
  assert.strictEqual(half[4], "x...x...x...x...");
  assert.strictEqual(half[5], "..x...x...x...x.");
  const all = call(brain, "open hh", { amount: 100 }, input);
  assert.strictEqual(all[4], REST);
  assert.strictEqual(all[5], "x.x.x.x.x.x.x.x.");
  assert.deepStrictEqual(half.filter((row, v) => v !== 4 && v !== 5), input.filter((row, v) => v !== 4 && v !== 5));
});

test("accent: every Nth hit is an accent, the others plain hits, ghosts untouched (Ableton's Accent Frequency, B3)", () => {
  const brain = loadBrain();
  assert.strictEqual(call(brain, "accent", { every: 2, offset: 0 }, ["X...x..ox...X..."])[0], "X...x..oX...x...");
  assert.strictEqual(call(brain, "accent", { every: 2, offset: 1 }, ["x...x...x...x..."])[0], "x...X...x...X...");
  assert.strictEqual(call(brain, "accent", { every: 1, offset: 0 }, ["x.x.o.x........."])[0], "X.X.o.X.........");
  assert.strictEqual(call(brain, "accent", { every: 16, offset: 0 }, ["X.X.X.X........."])[0], "X.x.x.x.........");
});

// ---- playback -------------------------------------------------------------------------------------------------
test("playback: every non-rest step plays at its grade's velocity, every bar the same", () => {
  const brain = readyBrain();
  brain.choose("canned", "all");
  brain.setting("kit", brain.context.CANNED_KITS.findIndex((k) => k.name === "P6 rolling") + 1);
  const hits = brain.play(4);
  for (let bar = 0; bar < 4; bar++) {
    const kicks = hits.filter((h) => h.voice === "bd" && Math.floor(h.sixteenth / 16) === bar);
    assert.deepStrictEqual(kicks.map((h) => [h.sixteenth % 16, +h.velocity.toFixed(3)]),
                           [[0, 0.7], [3, 0.2], [4, 0.7], [8, 0.7], [11, 0.2], [12, 0.7]], "bar " + bar);
  }
  noErrors(brain);
});

test("Swing is the 909 shuffle as a delay of every second 16th: 0 at shuffle 1, a quarter 8th at 7", () => {
  const brain = readyBrain();
  brain.send("edit", 4, 0); brain.send("edit", 4, 1);           // closed hats on steps 1 and 2
  for (const [level, tempo, expectedMs] of [[0, 120, 0], [6, 120, 62.5], [3, 120, 31.25], [6, 60, 125]]) {
    brain.send("swing", level);
    brain.send("tempo", tempo);
    const hits = brain.play(1, 64 * (level + 1) + tempo);       // a fresh stretch of the song each time
    for (const h of hits) {
      const odd = (h.sixteenth % 16) % 2 === 1;
      assert.ok(Math.abs(h.delay - (odd ? expectedMs : 0)) < 1e-9,
                "shuffle " + (level + 1) + " at " + tempo + " bpm: step " + (h.sixteenth % 16) + " delay " + h.delay);
    }
    assert.ok(hits.some((h) => h.sixteenth % 2 === 1), "the test needs odd-step hits");
  }
  const percents = brain.context.SWING_PERCENT;
  assert.strictEqual(percents.length, 7);
  assert.strictEqual(percents[0], 50);
  assert.ok(Math.abs(percents[6] - 75) < 1e-9);
  noErrors(brain);
});

test("Triggers: accents at velocity 1, hits 0.7; every hit a new number; serials wrap below 1000", () => {
  const brain = readyBrain();
  brain.send("edit", 0, 0); brain.send("edit", 0, 0);            // the kick's step 1: x -> X -> .
  brain.send("edit", 0, 0); brain.send("edit", 0, 0);            // . -> x -> X
  const hits = brain.play(300).filter((h) => h.voice === "bd");
  let last = null;
  for (const h of hits) {
    assert.ok(h.value !== last, "two kick triggers with the same number");
    assert.ok(h.value > 1 && h.value < 1000);
    last = h.value;
    assert.ok(Math.abs(h.velocity - ((h.sixteenth % 16) === 0 ? 1 : 0.7)) < 1e-6);
  }
  assert.ok(hits.length > 999, "the test needs more than 999 kick hits to see the wrap");
  noErrors(brain);
});

test("The clock plays each 16th once: repeated and between-16th ticks play nothing; a jump says so", () => {
  const brain = readyBrain();
  const count = () => brain.record.outlets.filter((o) => o[0] === 0 && /^trig_/.test(o[1])).length;
  brain.clear(); brain.send("tick", 0); const first = count();
  assert.ok(first > 0);
  brain.clear(); brain.send("tick", 5); assert.strictEqual(count(), 0, "a repeat of 16th 0 played");
  brain.clear(); brain.send("tick", 60); assert.strictEqual(count(), 0, "a tick between 16ths played");
  brain.clear(); brain.send("tick", 16 * 120);
  assert.ok(brain.record.posts.some((p) => /jumped/.test(p)), "a jump must be posted");
  brain.send("playing", 0);
  brain.clear(); brain.send("tick", 17 * 120); assert.strictEqual(count(), 0, "played while Live is stopped");
  noErrors(brain);
});

test("MIDI notes play their voices at once; a note no voice has says so", () => {
  const brain = readyBrain();
  brain.clear();
  brain.note(36, 127); brain.note(42, 64); brain.note(36, 0);
  const trigs = brain.record.outlets.filter((o) => o[0] === 0 && /^trig_/.test(o[1]));
  assert.deepStrictEqual(trigs.map((o) => o[1]), ["trig_bd", "trig_ch"]);
  const delays = brain.record.outlets.filter((o) => o[0] === 0 && /^delay_/.test(o[1]));
  assert.deepStrictEqual(delays.map((o) => o[2]), [0, 0]);
  brain.note(60, 100);
  assert.ok(brain.record.posts.some((p) => /plays no voice/.test(p)));
  noErrors(brain);
});

test("Failures are loud: unknown messages and out-of-range values go to the Max window", () => {
  const brain = readyBrain();
  brain.send("nonsense", 1);
  brain.send("function", 99);
  brain.send("param", 2, 0, 400);
  brain.send("param", 5, 3, 1);                                  // reverse has one setting
  brain.send("steps_zz_a", 1);
  brain.send("voice", 12);
  brain.send("seed", 140);
  brain.send("select", 1);                                       // multi-select is gone
  brain.context.inlet = 0; brain.context.messagename = "undo"; brain.context.anything();
  assert.strictEqual(brain.record.errors.length, 9, brain.record.errors.join(" | "));
  assert.strictEqual(brain.context.functionIndex, brain.context.FUNCTIONS.length - 1);
  assert.strictEqual(brain.context.chosenVoice, ALL);
  assert.strictEqual(brain.context.functionSettings[2][0], 16, "euclid hits clamps to its max");
  assert.throws(() => brain.context.parseRow("x..", "test"), /not 16 steps/);
});

// ---- the patch: the mixer ---------------------------------------------------------------------------------------
test("the mixer: every voice has Level, Mute and Solo; Mute and Solo reach gen~ and the mix display, not presets", () => {
  const ui = loadUi();
  const gen = BOXES.find((b) => b.text === "gen~");
  const code = gen.patcher.boxes.find((b) => b.box.maxclass === "codebox").box.code;
  for (const id of VOICE_IDS) {
    assert.ok(BOXES.some((b) => b.varname === id + "_level"), id + " level");
    for (const kind of ["mute", "solo"]) {
      const box = BOXES.find((b) => b.varname === id + "_" + kind);
      assert.ok(box && box.maxclass === "live.text", id + " " + kind);
      const targets = LINES.filter((l) => l.source[0] === box.id).map((l) => BOXES.find((b) => b.id === l.destination[0]).text);
      assert.deepStrictEqual(targets.sort(), ["prepend " + id + "_" + kind, "prepend " + id + "_" + kind]);
      assert.ok(new RegExp("Param " + id + "_" + kind + "\\(0").test(code), "gen~ has no Param " + id + "_" + kind);
      for (const preset of ui.context.PRESETS) assert.ok(!(id + "_" + kind in preset), "a preset sets " + id + " " + kind);
    }
  }
});

// ---- the UI script (the kit's) -----------------------------------------------------------------------------
function loadUi() {
  const sent = [];
  const objects = {};
  const patcher = { getnamed: (name) => objects[name] || (objects[name] = { message: (...a) => sent.push([name].concat(a)) }) };
  const { context, record } = sandbox(1, { patcher, max: { getcolor: () => [0.15, 0.15, 0.15, 1] } });
  vm.runInContext(UI_SOURCE, context, { filename: "2sl-drums-ui.js" });
  return { context, record, sent };
}
function hiddenNow(record, name) {
  const found = record.outlets.filter((o) => o[3] === name);
  assert.ok(found.length, name + " was never shown or hidden");
  return found[found.length - 1][5];
}

test("UI: presets wait for ready, then set every control they name; pages show and hide", () => {
  const { context, record, sent } = loadUi();
  context.msg_int(1);
  assert.strictEqual(sent.length, 0, "a preset before ready was applied");
  context.messagename = "ready"; context.anything();
  context.msg_int(2);
  const preset = context.PRESETS[2];
  for (const name in preset) assert.ok(sent.some((s) => s[0] === name && s[1] === preset[name]), "preset didn't set " + name);
  record.outlets.length = 0;
  deliverMessage(context, 0, "page", [1]);
  assert.strictEqual(hiddenNow(record, "view_mix"), 0);
  assert.strictEqual(hiddenNow(record, "view_grid"), 1);
  context.msg_int(99);
  context.messagename = "bogus"; context.anything();
  assert.strictEqual(record.errors.length, 2, record.errors.join(" | "));
});

test("UI: the Voice buttons show one voice's controls on the kit page, and nothing off it", () => {
  const { context, record } = loadUi();
  context.messagename = "ready"; context.anything();
  deliverMessage(context, 0, "page", [1]);
  assert.strictEqual(hiddenNow(record, "view_bd"), 0);
  assert.strictEqual(hiddenNow(record, "bd_tune"), 0);
  assert.strictEqual(hiddenNow(record, "hat_tune"), 1);
  context.messagename = "group"; context.anything("kit_voice", 4);
  assert.strictEqual(hiddenNow(record, "view_bd"), 1);
  assert.strictEqual(hiddenNow(record, "bd_tune"), 1);
  assert.strictEqual(hiddenNow(record, "view_hats"), 0);
  assert.strictEqual(hiddenNow(record, "hat_tune"), 0);
  assert.strictEqual(hiddenNow(record, "bd_level"), 0, "the mixer stays");
  deliverMessage(context, 0, "page", [0]);
  assert.strictEqual(hiddenNow(record, "hat_tune"), 1);
  assert.strictEqual(hiddenNow(record, "view_grid"), 0);
  context.messagename = "group"; context.anything("nonsense", 1);
  assert.strictEqual(record.errors.length, 1, record.errors.join(" | "));
  // the patch starts as the UI does: the voice groups after the first hidden
  for (const name of ["view_sd", "sd_tune", "view_rd"]) assert.strictEqual(BOXES.find((b) => b.varname === name).hidden, 1, name);
});

test("UI: Function shows only its function's setting dials on the pattern page", () => {
  const { context, record } = loadUi();
  context.messagename = "ready"; context.anything();
  assert.strictEqual(hiddenNow(record, "canned_kit"), 0);
  assert.strictEqual(hiddenNow(record, "euclid_hits"), 1);
  deliverMessage(context, 0, "group", ["function", 2]);
  assert.strictEqual(hiddenNow(record, "canned_kit"), 1);
  for (const name of ["euclid_hits", "euclid_rotation", "euclid_steps", "voice", "function", "seed"]) {
    assert.strictEqual(hiddenNow(record, name), 0, name);
  }
  deliverMessage(context, 0, "page", [1]);
  assert.strictEqual(hiddenNow(record, "euclid_hits"), 1, "not on the kit page");
  assert.deepStrictEqual(record.errors, []);
});

// ---- the displays ---------------------------------------------------------------------------------------------
function loadView(mode, size) {
  const drawn = { calls: 0, texts: [] };
  const mgraphics = new Proxy({ size: size || (mode === "grid" ? [282, 137] : [324, 64]) }, {
    get: (target, key) => (key in target ? target[key] : () => { drawn.calls++; }),
    set: (target, key, value) => { target[key] = value; return true; },
  });
  function Task(fn) { this.fn = fn; this.repeat = () => {}; this.cancel = () => {}; }
  const { context, record } = sandbox(1, { mgraphics, Task, jsarguments: ["2sl-drums-view.js", mode],
                                           max: { getcolor: () => [0.15, 0.15, 0.15, 1], launchbrowser: () => {} } });
  vm.runInContext(VIEW_SOURCE, context, { filename: "2sl-drums-view.js" });
  const send = (name, ...args) => deliverMessage(context, 0, name, args);
  return { context, record, drawn, send };
}

test("Every display draws with its Init values, takes its messages; the grid's clicks select and edit", () => {
  const modes = ["chrome", "link", "grid", "status", "mix", "bd", "sd", "rs", "cp", "hats", "rd"];
  for (const mode of modes) {
    const view = loadView(mode);
    view.context.paint();
    assert.ok(view.drawn.calls > 0, mode + " drew nothing");
    assert.deepStrictEqual(view.record.errors, [], mode + ": " + view.record.errors.join(" | "));
  }
  const grid = loadView("grid");
  grid.send("rows", ...P1);
  grid.send("chosen", 4);
  grid.send("pos", 3);
  grid.send("hit", 0, 3);
  grid.context.paint();
  const g = grid.context.gridGeometry(282, 137);
  assert.strictEqual(g.cellW, 16);
  assert.strictEqual(g.rowH, 19);
  const clicks = [[g.stepsX + 2 * g.cellW + 2, 1 + 1 * g.rowH + 3, 0], [g.stepsX + 5 * g.cellW + 2, 1 + 2 * g.rowH + 3, 1],
                  [5, 1 + 4 * g.rowH + 3, 0]];
  for (const [x, y, shift] of clicks) grid.context.onclick(x, y, 1, 0, shift, 0, 0, 0);
  assert.deepStrictEqual(grid.record.outlets.map((o) => o.slice(1)), [["edit", 1, 2], ["edit", 2, 5, 1], ["name_click", 4]]);
  grid.send("chosen", 7);
  grid.context.paint();
  const status = loadView("status", [446, 64]);
  status.send("head", "rs | euclid | seed 4288/4352");
  status.send("settings", "hits 4  rotation 0  steps 16, and a very long tail that must be cut to fit the status line");
  status.send("note", "open hh writes oh, not ch (it reads ch)", 1);
  status.send("history", 3, 12, "edit", "rd", "step", "10", "x");
  status.context.paint();
  assert.ok(status.context.fitted("x".repeat(200), 100).length <= 17);
  const mixer = loadView("mix", [332, 64]);
  mixer.send("hit", 2, 0.8);
  mixer.send("sd_solo", 1);
  assert.strictEqual(mixer.context.sounds(1), true);
  assert.strictEqual(mixer.context.sounds(0), false, "another voice is soloed");
  mixer.send("sd_mute", 1);
  assert.strictEqual(mixer.context.sounds(1), false, "a mute wins over solo");
  mixer.context.paint();
  for (const v of [grid, status, mixer]) assert.deepStrictEqual(v.record.errors, [], v.record.errors.join(" | "));
  const wrong = loadView("bd");
  wrong.send("no_such_thing", 1);
  assert.strictEqual(wrong.record.errors.length, 1);
});

// ---- run ----------------------------------------------------------------------------------------------------
let failed = 0;
test("no message the patch sends a script is also a global function's name (Max would call it, skipping anything())", () => {
  const MAX_ENTRY_POINTS = ["anything", "list", "bang", "msg_int", "msg_float", "loadbang", "notifydeleted"];
  const sourceByFile = { "2sl-drums.js": BRAIN_SOURCE, "2sl-drums-ui.js": UI_SOURCE, "2sl-drums-view.js": VIEW_SOURCE };
  const boxById = {};
  for (const b of BOXES) boxById[b.id] = b;
  const collisions = [];
  for (const scriptBox of BOXES) {
    const file = scriptBox.filename || ((scriptBox.text || "").match(/^js (\S+)/) || [])[1];
    if (!sourceByFile[file]) continue;
    const { context } = sandbox(1, { mgraphics: new Proxy({}, { get: () => () => {}, set: () => true }),
      Task: function () { this.repeat = () => {}; this.cancel = () => {}; },
      jsarguments: [file, "grid"], max: { getcolor: () => [0, 0, 0, 1], launchbrowser: () => {} } });
    vm.runInContext(sourceByFile[file], context, { filename: file });
    for (const line of LINES) {
      if (line.destination[0] !== scriptBox.id) continue;
      const sender = boxById[line.source[0]], text = sender.text || "";
      const name = sender.maxclass === "message" ? text.split(" ")[0]
                 : (text.match(/^prepend (\S+)/) || [])[1];
      if (name && !MAX_ENTRY_POINTS.includes(name) && typeof context[name] === "function")
        collisions.push(file + " gets '" + name + "' from " + sender.id);
    }
  }
  assert.strictEqual(collisions.length, 0, collisions.join("; "));
});

for (const t of tests) {
  try { t.body(); console.log("ok   " + t.name); }
  catch (e) { failed++; console.log("FAIL " + t.name + "\n     " + (e.stack || e).toString().split("\n").slice(0, 4).join("\n     ")); }
}
console.log((tests.length - failed) + "/" + tests.length + " passed");
process.exit(failed ? 1 : 0);

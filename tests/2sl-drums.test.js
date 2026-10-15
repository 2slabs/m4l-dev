// Tests for 2sl drums' generated scripts, in plain node (no packages): node tests/2sl-drums.test.js
// Run src/2sl-drums.py first: these load devices/2sl-drums/*.js as the device does, with Max's globals stubbed.
// The functions are tested against references/drums/patterns.md (P1, P10, P11, F, B1, B3) and their Info text;
// the engine against the design in PLANS/2026-10-15-2sl-drums-functions.md (Run, Undo, the history, selection).
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

function loadBrain(seed) {
  const { context, record } = sandbox(seed === undefined ? 1 : seed);
  vm.runInContext(BRAIN_SOURCE, context, { filename: "2sl-drums.js" });
  const brain = {
    context, record,
    send(name) { deliverMessage(context, 1, name, Array.prototype.slice.call(arguments, 1)); },
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
    /** Pick function `name`, set its settings {name: value}, select `rows` (voice ids, or all), Run. */
    runFunction(name, settings, rows) {
      const f = context.FUNCTIONS.findIndex((entry) => entry.name === name);
      assert.ok(f >= 0, "no function " + name);
      brain.send("function", f);
      for (const key in settings || {}) {
        const p = context.FUNCTIONS[f].params.findIndex((param) => param.name === key);
        assert.ok(p >= 0, name + " has no setting " + key);
        brain.send("param", f, p, settings[key]);
      }
      if (rows) brain.selectOnly(rows);
      brain.send("run");
    },
    selectOnly(ids) {
      const c = context;
      for (let v = 0; v < c.VOICES.length; v++) c.selected[v] = ids.indexOf(c.VOICES[v].id) >= 0 ? 1 : 0;
    },
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
  return brain;
}
function readyBrain(seed) {
  const brain = loadBrain(seed);
  brain.send("ready");
  brain.send("tempo", 120);
  brain.send("playing", 1);
  return brain;
}
function noErrors(brain) { assert.deepStrictEqual(brain.record.errors, [], "errors: " + brain.record.errors.join(" | ")); }

const VOICE_IDS = ["bd", "sd", "rs", "cp", "ch", "oh", "rd"];
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

// ---- start-up, storage ------------------------------------------------------------------------------------
test("the Init pattern is P1 (Basic Channel-style), every row selected, the history one step long", () => {
  const brain = loadBrain();
  brain.send("ready");
  assert.deepStrictEqual(brain.lastRows(), P1);
  assert.deepStrictEqual(brain.lastOf(1, "selected"), [1, 1, 1, 1, 1, 1, 1]);
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [1, 1]);
  noErrors(brain);
});

test("the stored values' initial values in the patch restore P1 and the full selection", () => {
  const brain = loadBrain(7);
  brain.runFunction("random", { seed: 5 });                      // something else first
  const stored = BOXES.filter((b) => /^steps_|^selected$/.test(b.varname || ""));
  assert.strictEqual(stored.length, 15);
  for (const b of stored) brain.send(b.varname, b.saved_attribute_attributes.valueof.parameter_initial[0]);
  brain.send("ready");
  assert.deepStrictEqual(brain.lastRows(), P1);
  assert.deepStrictEqual(brain.lastOf(1, "selected"), [1, 1, 1, 1, 1, 1, 1]);
  noErrors(brain);
});

test("persistence: the stored pattern and selection come back in a new device; its history starts there", () => {
  const brain = readyBrain(3);
  brain.runFunction("euclid", { hits: 5, rotation: 2 }, ["rs"]);
  brain.send("edit", 1, 15);
  brain.send("edit", 6, 3, 1);
  brain.send("select", 4, 0);
  brain.send("select", 0, 1);
  const rows = brain.lastRows(), selection = brain.lastOf(1, "selected");
  const stored = {};
  for (const o of brain.record.outlets) if (o[0] === 4) stored[o[1]] = o[2];
  assert.strictEqual(Object.keys(stored).length, 15);
  const reopened = loadBrain(99);
  reopened.runFunction("random", { seed: 9 });
  for (const name in stored) reopened.send(name, stored[name]);
  reopened.send("ready");
  assert.deepStrictEqual(reopened.lastRows(), rows);
  assert.deepStrictEqual(reopened.lastOf(1, "selected"), selection);
  assert.deepStrictEqual(selection, [1, 0, 0, 0, 1, 0, 0]);
  assert.deepStrictEqual(reopened.lastOf(2, "history").slice(0, 2), [1, 1], "the history isn't saved: it restarts");
  noErrors(brain); noErrors(reopened);
});

test("the stored values echoing back after a change change nothing (and don't redraw)", () => {
  const brain = readyBrain();
  brain.runFunction("euclid", { hits: 3 }, ["rd"]);
  const stored = brain.record.outlets.filter((o) => o[0] === 4);
  brain.clear();
  for (const o of stored) brain.send(o[1], o[2]);
  assert.strictEqual(brain.record.outlets.length, 0, "an unchanged stored value redrew or stored again");
  noErrors(brain);
});

// ---- the registry: one source for the functions and their Live parameters -----------------------------------
function longName(entry, param) { return entry.name[0].toUpperCase() + entry.name.slice(1) + " " + param.name[0].toUpperCase() + param.name.slice(1); }
function varnameOf(name) { return name.toLowerCase().replace(/ /g, "_"); }

test("registry -> Live parameters: every setting is one live.numbox with the registry's range, initial, unit, Info", () => {
  const c = loadBrain().context, UNIT = { int: 0, "%": 5 };
  const brainBox = BOXES.find((b) => b.text === "js 2sl-drums.js");
  const tab = BOXES.find((b) => b.varname === "function");
  assert.deepStrictEqual(tab.saved_attribute_attributes.valueof.parameter_enum, Array.from(c.FUNCTIONS, (f) => f.name));
  let settings = 0;
  c.FUNCTIONS.forEach((entry, f) => {
    entry.params.forEach((param, p) => {
      settings++;
      const name = longName(entry, param), box = BOXES.find((b) => b.varname === varnameOf(name));
      assert.ok(box, "no Live parameter " + name);
      assert.strictEqual(box.maxclass, "live.numbox", name);
      const saved = box.saved_attribute_attributes.valueof;
      assert.strictEqual(saved.parameter_longname, name);
      assert.strictEqual(saved.parameter_mmin, param.min, name + " min");
      assert.strictEqual(saved.parameter_mmax, param.max, name + " max");
      assert.deepStrictEqual(saved.parameter_initial, [param.initial], name + " initial");
      assert.strictEqual(saved.parameter_unitstyle, UNIT[param.unit], name + " unit");
      assert.ok(saved.parameter_info.indexOf(param.info) >= 0 && saved.parameter_info.indexOf(entry.info) >= 0, name + " Info");
      assert.strictEqual(box.hidden, undefined, name + " must show with the pattern page");
      // its value reaches the brain as `param f p value`
      const prepend = LINES.filter((l) => l.source[0] === box.id).map((l) => BOXES.find((b) => b.id === l.destination[0]));
      assert.deepStrictEqual(prepend.map((b) => b.text), ["prepend param " + f + " " + p], name + " wiring");
      assert.ok(LINES.some((l) => l.source[0] === prepend[0].id && l.destination[0] === brainBox.id && l.destination[1] === 1));
    });
  });
  const numboxes = BOXES.filter((b) => b.maxclass === "live.numbox" && b.presentation === 1 && b.varname !== "volume");
  assert.strictEqual(numboxes.length, settings, "a live.numbox no registry setting made");
  // presets leave the functions alone
  const ui = loadUi();
  for (const preset of ui.context.PRESETS) for (const name in preset) assert.ok(!/^(canned|grids|euclid|random|shift|thin|ghosts|fill|open_hh|accent)_/.test(name), name);
});

test("a broken registry entry is a loud failure (the build and the device run this check)", () => {
  const c = loadBrain().context;
  const good = c.FUNCTIONS.slice();
  const broken = [
    { name: "x", kind: "neither", info: "i", params: [], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [{ name: "a", min: 0, max: 4, initial: 9, unit: "int", info: "i" }], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "i", params: [{ name: "a", min: 0, max: 4, initial: 1, unit: "dB", info: "i" }], run() {}, summary() {} },
    { name: "x", kind: "modifier", info: "", params: [], run() {}, summary() {} },
    { name: "canned", kind: "modifier", info: "i", params: [], run() {}, summary() {} },
  ];
  for (const entry of broken) {
    c.FUNCTIONS.length = 0;
    good.forEach((g) => c.FUNCTIONS.push(g));
    c.FUNCTIONS.push(entry);
    assert.throws(() => c.checkFunctionRegistry(), /function/, JSON.stringify(entry));
  }
});

// ---- the functions, each on its own ------------------------------------------------------------------------
test("every function is pure: the same input gives the same output, and the input is left as it was", () => {
  const brain = loadBrain(), c = brain.context;
  const input = patternWith({ bd: "x..ox...x..ox...", ch: "xxXxxxXxxxXxxxXx", oh: "..x...x...x...x.", sd: "....X..o....x..." });
  for (const fn of c.FUNCTIONS) {
    const values = {};
    fn.params.forEach((param) => { values[param.name] = param.roll ? 7 : param.initial; });
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

test("grids: Run keeps the rows Grids has no channel for, and says so", () => {
  const brain = readyBrain();
  brain.send("edit", 2, 5);                                      // a rim hit
  const rim = brain.lastRows()[2];
  brain.clear();
  brain.runFunction("grids", { density: 80 });
  assert.strictEqual(brain.lastRows()[2], rim);
  assert.ok(brain.record.posts.some((p) => /nothing for rs, rd/.test(p)), brain.record.posts.join(" | "));
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

test("random: seed 0 rolls a new seed each Run, and the label says which, so it can be dialled back", () => {
  const brain = readyBrain(5);
  brain.runFunction("random", { seed: 0, density: 50 });
  const first = brain.lastRows(), label = brain.lastOf(2, "history")[2];
  const seed = Number(/seed (\d+)/.exec(label)[1]);
  assert.ok(seed >= 1 && seed <= 999, label);
  brain.send("run");
  assert.notDeepStrictEqual(brain.lastRows(), first, "a second roll made the same rows");
  brain.runFunction("random", { seed, density: 50 });
  assert.deepStrictEqual(brain.lastRows(), first, "dialling the rolled seed must give its rows back");
  noErrors(brain);
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

test("reverse: backwards from the downbeat (step 1 stays); twice is the identity; P1 is its own reverse", () => {
  const brain = loadBrain();
  assert.deepStrictEqual(call(brain, "reverse", {}, ["xX..o..........."]), ["x...........o..X"]);
  assert.deepStrictEqual(call(brain, "reverse", {}, P1), P1);
  const row = "x..ox...X..o..x.";
  assert.strictEqual(call(brain, "reverse", {}, call(brain, "reverse", {}, [row]))[0], row);
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
  brain.runFunction("ghosts", { amount: 25 }, ["bd"]);
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

test("open hh: closed hats' hits move to the open hat, offbeat 8ths first; it needs both rows selected", () => {
  const brain = readyBrain();
  const input = patternWith({ ch: "x.x.x.x.x.x.x.x.", oh: REST });
  const half = call(brain, "open hh", { amount: 50 }, input);
  assert.strictEqual(half[4], "x...x...x...x...");
  assert.strictEqual(half[5], "..x...x...x...x.");
  const all = call(brain, "open hh", { amount: 100 }, input);
  assert.strictEqual(all[4], REST);
  assert.strictEqual(all[5], "x.x.x.x.x.x.x.x.");
  assert.deepStrictEqual(half.filter((row, v) => v !== 4 && v !== 5), input.filter((row, v) => v !== 4 && v !== 5));
  const before = brain.lastRows();
  brain.clear();
  brain.runFunction("open hh", { amount: 100 }, ["ch"]);
  assert.ok(brain.record.posts.some((p) => /works on ch and oh/.test(p)), brain.record.posts.join(" | "));
  assert.ok(!brain.record.outlets.some((o) => o[0] === 1 && o[1] === "rows"), "the pattern changed");
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [1, 1]);
  assert.deepStrictEqual(before, P1);
  noErrors(brain);
});

test("accent: every Nth hit is an accent, the others plain hits, ghosts untouched (Ableton's Accent Frequency, B3)", () => {
  const brain = loadBrain();
  assert.strictEqual(call(brain, "accent", { every: 2, offset: 0 }, ["X...x..ox...X..."])[0], "X...x..oX...x...");
  assert.strictEqual(call(brain, "accent", { every: 2, offset: 1 }, ["x...x...x...x..."])[0], "x...X...x...X...");
  assert.strictEqual(call(brain, "accent", { every: 1, offset: 0 }, ["x.x.o.x........."])[0], "X.X.o.X.........");
  assert.strictEqual(call(brain, "accent", { every: 16, offset: 0 }, ["X.X.X.X........."])[0], "X.x.x.x.........");
});

// ---- Run, Undo, the history, the selection -------------------------------------------------------------------
test("Run applies the function to the selected rows only; the others pass through", () => {
  const brain = readyBrain();
  brain.runFunction("euclid", { hits: 3, steps: 8 }, ["rs", "rd"]);
  const rows = brain.lastRows();
  assert.strictEqual(rows[2], "x..x..x.x..x..x.");
  assert.strictEqual(rows[6], "x..x..x.x..x..x.");
  [0, 1, 3, 4, 5].forEach((v) => assert.strictEqual(rows[v], P1[v], VOICE_IDS[v] + " changed"));
  assert.ok(/euclid E\(3,8\) on rs rd/.test(brain.lastOf(2, "history")[2]));
  noErrors(brain);
});

test("Run with no row selected, or that changes nothing, says so and adds no step", () => {
  const brain = readyBrain();
  brain.selectOnly([]);
  brain.clear();
  brain.send("run");
  assert.ok(brain.record.posts.some((p) => /no row is selected/.test(p)));
  brain.runFunction("canned", { kit: 1 }, VOICE_IDS);           // P1 again: no change
  assert.ok(brain.record.posts.some((p) => /changed nothing/.test(p)));
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [1, 1]);
  noErrors(brain);
});

test("Undo steps back through every Run and edit; Run after Undo drops the undone steps (no redo)", () => {
  const brain = readyBrain();
  const p0 = brain.lastRows();
  brain.runFunction("euclid", { hits: 5 }, ["rs"]);
  const p1 = brain.lastRows();
  brain.send("edit", 6, 0);
  const p2 = brain.lastRows();
  brain.runFunction("reverse", {}, ["rs"]);
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [4, 4]);
  brain.send("undo"); assert.deepStrictEqual(brain.lastRows(), p2);
  brain.send("undo"); assert.deepStrictEqual(brain.lastRows(), p1);
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [2, 4]);
  brain.runFunction("shift", { steps: 2 }, ["bd"]);
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [3, 3], "Run after Undo must drop the undone steps");
  brain.send("undo"); brain.send("undo");
  assert.deepStrictEqual(brain.lastRows(), p0);
  brain.clear();
  brain.send("undo");
  assert.ok(brain.record.posts.some((p) => /oldest pattern kept/.test(p)));
  assert.ok(!brain.record.outlets.some((o) => o[0] === 4), "an Undo past the start stored something");
  noErrors(brain);
});

test("the history keeps the last HISTORY_LIMIT patterns; the oldest go", () => {
  const brain = readyBrain(), limit = brain.context.HISTORY_LIMIT;
  assert.strictEqual(limit, 100);
  for (let i = 0; i < limit + 30; i++) brain.runFunction("shift", { steps: 1 }, ["bd"]);    // P1's kick moves every time
  assert.strictEqual(brain.context.history.length, limit);
  for (let i = 0; i < limit - 1; i++) brain.send("undo");
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [1, limit]);
  brain.clear();
  brain.send("undo");
  assert.ok(brain.record.posts.some((p) => /oldest pattern kept \(100 at most\)/.test(p)));
  noErrors(brain);
});

test("hand edit: a click cycles rest -> hit -> accent -> rest, shift sets a ghost; each is a history step", () => {
  const brain = readyBrain();
  brain.send("edit", 6, 5); assert.strictEqual(brain.lastRows()[6][5], "x");
  brain.send("edit", 6, 5); assert.strictEqual(brain.lastRows()[6][5], "X");
  brain.send("edit", 6, 5); assert.strictEqual(brain.lastRows()[6][5], ".");
  brain.send("edit", 6, 9, 1); assert.strictEqual(brain.lastRows()[6][9], "o");
  brain.send("edit", 6, 9); assert.strictEqual(brain.lastRows()[6][9], "x");
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [6, 6]);
  assert.ok(/edit rd step 10 x/.test(brain.lastOf(2, "history")[2]));
  brain.send("undo"); assert.strictEqual(brain.lastRows()[6][9], "o");
  brain.selectOnly(["bd"]);
  brain.send("edit", 6, 0);
  assert.strictEqual(brain.lastRows()[6][0], "x", "a click edits its own step whatever is selected");
  noErrors(brain);
});

test("selection: a click selects only that row, again selects every row; shift-click toggles; it is stored", () => {
  const brain = readyBrain();
  const sel = () => brain.lastOf(1, "selected");
  const storedSelection = () => brain.record.outlets.filter((o) => o[0] === 4 && o[1] === "selected").pop()[2];
  brain.send("select", 2, 0); assert.deepStrictEqual(sel(), [0, 0, 1, 0, 0, 0, 0]); assert.strictEqual(storedSelection(), 4);
  brain.send("select", 5, 1); assert.deepStrictEqual(sel(), [0, 0, 1, 0, 0, 1, 0]);
  brain.send("select", 2, 1); assert.deepStrictEqual(sel(), [0, 0, 0, 0, 0, 1, 0]);
  brain.send("select", 5, 0); assert.deepStrictEqual(sel(), [1, 1, 1, 1, 1, 1, 1], "a click on the only selected row: every row");
  brain.send("select", 0, 0); brain.send("select", 0, 1);
  assert.deepStrictEqual(sel(), [0, 0, 0, 0, 0, 0, 0]);
  assert.ok(/no row/.test(brain.lastOf(2, "next")[0]));
  noErrors(brain);
});

test("the status line says what Run will do, and follows the function, its settings and the selection", () => {
  const brain = readyBrain();
  brain.send("function", 2);
  brain.send("param", 2, 0, 7);
  assert.strictEqual(brain.lastOf(2, "next")[0], "euclid E(7,16) on every row");
  brain.send("select", 4, 0);
  assert.strictEqual(brain.lastOf(2, "next")[0], "euclid E(7,16) on ch");
  brain.send("function", 0);
  brain.send("param", 0, 1, 3);
  assert.strictEqual(brain.lastOf(2, "next")[0], "canned P1 basic channel, rs's row on ch");
  noErrors(brain);
});

test("a function that fails is a loud error and changes nothing", () => {
  const brain = readyBrain();
  brain.context.FUNCTIONS[4].run = function () { return [[1, 2]]; };
  brain.send("function", 4);
  brain.send("run");
  assert.strictEqual(brain.record.errors.length, 1);
  assert.ok(/shift failed: .* made 1 rows/.test(brain.record.errors[0]), brain.record.errors[0]);
  assert.deepStrictEqual(brain.lastOf(2, "history").slice(0, 2), [1, 1]);
});

// ---- playback -------------------------------------------------------------------------------------------------
test("playback: every non-rest step plays at its grade's velocity, every bar the same", () => {
  const brain = readyBrain();
  brain.runFunction("canned", { kit: brain.context.CANNED_KITS.findIndex((k) => k.name === "P6 rolling") + 1 });
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
  brain.send("param", 5, 0, 1);                                  // reverse has no settings
  brain.send("steps_zz_a", 1);
  brain.send("select", 12);
  brain.context.inlet = 0; brain.context.messagename = "run"; brain.context.anything();
  assert.strictEqual(brain.record.errors.length, 7, brain.record.errors.join(" | "));
  assert.strictEqual(brain.context.functionIndex, brain.context.FUNCTIONS.length - 1);
  assert.strictEqual(brain.context.functionValues[2][0], 16, "euclid hits clamps to its max");
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
  context.messagename = "group"; context.anything("voice", 4);
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
  grid.send("selected", 0, 1, 0, 0, 1, 0, 0);
  grid.send("pos", 3);
  grid.send("hit", 0, 3);
  grid.context.paint();
  const g = grid.context.gridGeometry(282, 137);
  assert.strictEqual(g.cellW, 16);
  assert.strictEqual(g.rowH, 19);
  const clicks = [[g.stepsX + 2 * g.cellW + 2, 1 + 1 * g.rowH + 3, 0], [g.stepsX + 5 * g.cellW + 2, 1 + 2 * g.rowH + 3, 1],
                  [5, 1 + 4 * g.rowH + 3, 0], [5, 1 + 6 * g.rowH + 3, 1]];
  for (const [x, y, shift] of clicks) grid.context.onclick(x, y, 1, 0, shift, 0, 0, 0);
  assert.deepStrictEqual(grid.record.outlets.map((o) => o.slice(1)),
                         [["edit", 1, 2], ["edit", 2, 5, 1], ["select", 4, 0], ["select", 6, 1]]);
  const status = loadView("status", [458, 33]);
  status.send("next", "euclid E(5,16) +3 on bd sd ch, and a very long tail that must be cut to fit the status line's width");
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

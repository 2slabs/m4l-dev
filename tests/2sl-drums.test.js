// Tests for 2sl drums' generated scripts, in plain node (no packages): node tests/2sl-drums.test.js
// Run src/2sl-drums.py first: these load devices/2sl-drums/*.js as the device does, with Max's globals stubbed.
// The pattern engine is tested against references/drums/patterns.md (P1, P11, F) and Grids' rules (B1).
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

// ---- a tiny runner ----------------------------------------------------------------------------------------
const tests = [];
function test(name, body) { tests.push({ name, body }); }

// ---- Max stubs: the shared sandbox ----------------------------------------------------------------------
const { sandbox } = require(path.join(ROOT, "tools", "max_sandbox.js"));

function loadBrain(seed) {
  const { context, record } = sandbox(seed === undefined ? 1 : seed);
  vm.runInContext(BRAIN_SOURCE, context, { filename: "2sl-drums.js" });
  const brain = {
    context, record,
    send(name) {
      context.inlet = 1;
      context.messagename = name;
      context.anything.apply(null, Array.prototype.slice.call(arguments, 1));
    },
    note(pitch, velocity) { context.inlet = 0; context.list(pitch, velocity); },
    clear() { record.outlets.length = 0; record.posts.length = 0; },
    lastRows() {
      const rows = record.outlets.filter((o) => o[0] === 1 && o[1] === "rows");
      assert.ok(rows.length, "the brain showed no rows");
      return rows[rows.length - 1].slice(2);
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
const P1 = ["x...x...x...x...", "....x.......x...", "................", "....x.......x...", "................",
            "..x...x...x...x.", "................"];

/** The hits a pattern makes at density threshold `threshold` without variation: [voice, step] sorted. */
function expectedHits(rows, minimumGrade) {
  const out = [];
  for (let s = 0; s < 16; s++) rows.forEach((row, v) => { if (".oxX".indexOf(row[s]) >= minimumGrade) out.push(VOICE_IDS[v] + "@" + s); });
  return out;
}
function hitKeys(hits) { return hits.map((h) => h.voice + "@" + (h.sixteenth % 16)); }

// ---- the pattern engine ---------------------------------------------------------------------------------------
test("the Init pattern is P1 (Basic Channel-style), as patterns.md transcribes it", () => {
  const brain = loadBrain();
  brain.send("ready");
  assert.deepStrictEqual(brain.lastRows(), P1);
  noErrors(brain);
});

test("the stored values' initial values in the patch restore P1", () => {
  const brain = loadBrain(7);
  brain.send("generate");                                   // something else first (ready isn't needed to generate)
  const stored = MAXPAT.patcher.boxes.map((b) => b.box).filter((b) => /^steps_|^locks$|^mutes$/.test(b.varname || ""));
  assert.strictEqual(stored.length, 16);
  for (const b of stored) brain.send(b.varname, b.saved_attribute_attributes.valueof.parameter_initial[0]);
  brain.send("ready");
  assert.deepStrictEqual(brain.lastRows(), P1);
  noErrors(brain);
});

test("Style is ignored while Live restores the set, then loads the style's first canned kit", () => {
  const brain = loadBrain();
  brain.send("style", 3);
  brain.send("ready");
  assert.deepStrictEqual(brain.lastRows(), P1, "a style before ready must not replace the stored pattern");
  brain.send("style", 3);
  const styles = brain.context.STYLES;
  const kit = styles[3].kits[0].rows;
  assert.deepStrictEqual(brain.lastRows(), VOICE_IDS.map((id) => kit[id] || "................"));
  noErrors(brain);
});

test("Canned steps through the style's kits as their sources give them, and wraps", () => {
  const brain = readyBrain();
  const kits = brain.context.STYLES[0].kits;
  for (let i = 1; i <= kits.length; i++) {
    brain.send("canned");
    const kit = kits[i % kits.length].rows;
    assert.deepStrictEqual(brain.lastRows(), VOICE_IDS.map((id) => kit[id] || "................"));
  }
  noErrors(brain);
});

test("Generate draws every unlocked row from the style's pool and leaves locked rows alone", () => {
  const brain = readyBrain(3);
  brain.send("style", 3);
  brain.send("edit", 0, 1);                                  // make the kick unusual, then lock it
  brain.send("lock", 0);
  const lockedKick = brain.lastRows()[0];
  const pools = brain.context.STYLES[3].pool;
  const seenKits = new Set();
  for (let i = 0; i < 40; i++) {
    brain.send("generate");
    const rows = brain.lastRows();
    assert.strictEqual(rows[0], lockedKick, "the locked kick changed");
    rows.forEach((row, v) => {
      if (v === 0) return;
      assert.ok(pools[VOICE_IDS[v]].some((p) => p.row === row), VOICE_IDS[v] + " row " + row + " is not in the pool");
    });
    seenKits.add(rows.join("|"));
  }
  assert.ok(seenKits.size > 5, "Generate made only " + seenKits.size + " different kits in 40 tries");
  noErrors(brain);
});

test("Reroll changes only its voice, to another row when the style has one; a locked voice says so", () => {
  const brain = readyBrain(5);
  brain.send("style", 3);
  const before = brain.lastRows();
  brain.send("reroll", 4);                                   // ch: the dark techno pool has several
  const after = brain.lastRows();
  after.forEach((row, v) => { if (v !== 4) assert.strictEqual(row, before[v]); });
  assert.notStrictEqual(after[4], before[4]);
  brain.send("lock", 4);
  brain.clear();
  brain.send("reroll", 4);
  assert.ok(brain.record.posts.some((p) => /locked/.test(p)), "rerolling a locked voice must say it is locked");
  noErrors(brain);
});

test("Grids rows at the map's nodes match patterns.md F's decoding of Grids' firmware", () => {
  const brain = readyBrain();
  // F: [map x-row 0, y-col 0] node_10, [x-row 2, y-col 2] node_4, [x-row 1, y-col 3] node_12 (BD, SD, HH)
  const decoded = {
    "0,0": ["x..x..XxoX....x.", ".xxxxxXoXo.o..o.", "X.x.xxxxX.o.xox."],
    "128,128": ["X.ooxoxoX.xo.oo.", "..ooX.x...xoXXx.", "o.XxxoXxooXxxoxx"],
    "64,192": ["X.Xx..oo..XX..xx", ".oo.X..X.xoxX.xx", "XoXoXoxxx.x.xxxx"],
  };
  const c = brain.context;
  for (const point in decoded) {
    const [x, y] = point.split(",").map(Number);
    ["bd", "sd", "ch"].forEach((id, channel) => {
      const row = c.rowText(c.gridsRow(c.VOICE_INDEX_BY_ID[id], x, y));
      assert.strictEqual(row, decoded[point][channel], "grids " + point + " " + id);
    });
  }
  noErrors(brain);
});

test("Euclidean rows are Toussaint's (patterns.md P11)", () => {
  const brain = loadBrain();
  const c = brain.context;
  const asText = (onsets) => onsets.map((o) => (o ? "x" : ".")).join("");
  assert.strictEqual(asText(c.euclidean(3, 8)), "x..x..x.");
  assert.strictEqual(asText(c.euclidean(5, 8)), "x.xx.xx.");
  assert.strictEqual(asText(c.euclidean(2, 5)), "x.x..");
  assert.strictEqual(asText(c.euclidean(3, 4)), "x.xx");
  assert.strictEqual(asText(c.euclidean(3, 7)), "x.x.x..");
  assert.strictEqual(asText(c.euclidean(4, 12)), "x..x..x..x..");
  assert.strictEqual(asText(c.euclidean(5, 12)), "x..x.x..x.x.");
  assert.strictEqual(asText(c.euclidean(5, 16)), "x..x..x..x..x...");
  assert.strictEqual(asText(c.euclidean(4, 16)), "x...x...x...x...");
  assert.strictEqual(asText(c.euclidean(0, 4)), "....");
  assert.strictEqual(asText(c.euclidean(4, 4)), "xxxx");
  for (let k = 0; k <= 16; k++) assert.strictEqual(c.euclidean(k, 16).filter((o) => o).length, k, "E(" + k + ",16) onsets");
});

test("Variation 0 repeats exactly: every bar plays the pattern's accents and hits, never its ghosts", () => {
  const brain = readyBrain(11);
  brain.send("style", 3);
  brain.send("canned"); brain.send("canned"); brain.send("canned");   // P6 rolling: has ghost kicks
  const rows = brain.lastRows();
  assert.ok(rows[0].indexOf("o") >= 0, "the test needs a ghost");
  brain.send("fill", 1);                                     // fills on, but Variation 0 means none
  const hits = brain.play(8);
  const expected = expectedHits(rows, 2);
  for (let bar = 0; bar < 8; bar++) {
    assert.deepStrictEqual(hitKeys(hits.filter((h) => Math.floor(h.sixteenth / 16) === bar)), expected, "bar " + bar);
  }
  noErrors(brain);
});

test("Density is Grids' threshold: 0 plays nothing, 100% plays every non-rest step, ghosts above 71.8%", () => {
  const brain = readyBrain();
  brain.send("style", 3);
  brain.send("canned"); brain.send("canned"); brain.send("canned");
  const rows = brain.lastRows();
  brain.send("density", 0);
  assert.strictEqual(brain.play(1).length, 0);
  brain.send("density", 1);
  assert.deepStrictEqual(hitKeys(brain.play(1, 16)), expectedHits(rows, 1));
  brain.send("density", 0.71);                               // 255 - 181 = 74 > 72: ghosts stay out
  assert.deepStrictEqual(hitKeys(brain.play(1, 32)), expectedHits(rows, 2));
  brain.send("density", 0.72);                               // 255 - 184 = 71 < 72: ghosts in
  assert.deepStrictEqual(hitKeys(brain.play(1, 48)), expectedHits(rows, 1));
  brain.send("density", 0.13);                               // threshold 222: only accents (224)
  assert.deepStrictEqual(hitKeys(brain.play(1, 64)), expectedHits(rows, 3));
  noErrors(brain);
});

test("Variation is Grids' per-pass perturbation: 0-62, one value per voice per bar, only ever adds hits", () => {
  const brain = readyBrain(21);
  const c = brain.context;
  c.variation = 1;
  let maximum = 0;
  for (let i = 0; i < 4000; i++) maximum = Math.max(maximum, c.drawPerturbation());
  assert.ok(maximum <= 62 && maximum >= 58, "perturbation maximum " + maximum + ", Grids' is 255*63>>8 = 62");
  brain.send("variation", 1);
  brain.send("density", 0.6);
  brain.send("edit", 2, 3, 1); brain.send("edit", 2, 7, 1); brain.send("edit", 2, 11, 1);   // three rim ghosts
  const rows = brain.lastRows(), base = expectedHits(rows, 2);
  const hits = brain.play(24);
  let barsWithGhosts = 0;
  for (let bar = 0; bar < 24; bar++) {
    const keys = hitKeys(hits.filter((h) => Math.floor(h.sixteenth / 16) === bar));
    for (const k of base) assert.ok(keys.indexOf(k) >= 0, "bar " + bar + " lost " + k);
    const ghosts = ["rs@3", "rs@7", "rs@11"].filter((k) => keys.indexOf(k) >= 0).length;
    assert.ok(ghosts === 0 || ghosts === 3, "bar " + bar + ": the ghosts must come and go together (one perturbation a pass)");
    if (ghosts) barsWithGhosts++;
  }
  assert.ok(barsWithGhosts > 2 && barsWithGhosts < 22, "ghosts came in " + barsWithGhosts + " of 24 bars");
  noErrors(brain);
});

test("Fills: only in the last beat of each phrase's last bar, on the fill voices, scaled by Variation", () => {
  for (const [fillChoice, every] of [[1, 4], [2, 8]]) {
    const brain = readyBrain(31 + fillChoice);
    brain.send("density", 0.5);
    brain.send("variation", 1);
    brain.send("fill", fillChoice);
    const rows = brain.lastRows();
    const hits = brain.play(32);
    const base = expectedHits(rows, 2);
    let fillHits = 0;
    for (const h of hits) {
      const key = h.voice + "@" + (h.sixteenth % 16), bar = Math.floor(h.sixteenth / 16), step = h.sixteenth % 16;
      if (base.indexOf(key) >= 0) continue;
      // a fill hit, or a perturbation hit (rests reach 0 + 62 = 62, under the threshold of 127 at 50%)
      assert.ok((bar + 1) % every === 0 && step >= 12, "extra " + key + " in bar " + bar + " outside the fill window");
      assert.ok(["sd", "rs", "cp", "ch"].indexOf(h.voice) >= 0, "extra hit on " + h.voice);
      fillHits++;
    }
    assert.ok(fillHits > 0, "every " + every + " bars: no fill hits at Variation 100%");
    noErrors(brain);
  }
  const quiet = readyBrain(40);
  quiet.send("fill", 1);
  const rows = quiet.lastRows();
  const hits = quiet.play(8);
  assert.deepStrictEqual(hitKeys(hits.filter((h) => h.sixteenth >= 48 && h.sixteenth < 64)), expectedHits(rows, 2),
                         "Variation 0 must play no fills");
});

test("Swing is the 909 shuffle as a delay of every second 16th: 0 at shuffle 1, a quarter 8th at 7", () => {
  const brain = readyBrain();
  brain.send("density", 1);
  brain.send("edit", 4, 0); brain.send("edit", 4, 1);        // closed hats on steps 1 and 2
  for (const [level, tempo, expectedMs] of [[0, 120, 0], [6, 120, 62.5], [3, 120, 31.25], [6, 60, 125]]) {
    brain.send("swing", level);
    brain.send("tempo", tempo);
    const hits = brain.play(1, 64 * (level + 1) + tempo);    // a fresh stretch of the song each time
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

test("Triggers: accents at velocity 1, hits below; every hit a new number; serials wrap below 1000", () => {
  const brain = readyBrain();
  brain.send("density", 1);
  brain.send("edit", 0, 0);                                  // the kick's step 1: x -> X
  const hits = brain.play(300).filter((h) => h.voice === "bd");
  let last = null;
  for (const h of hits) {
    assert.ok(h.value !== last, "two kick triggers with the same number");
    assert.ok(h.value > 1 && h.value < 1000);
    last = h.value;
    assert.ok(Math.abs(h.velocity - ((h.sixteenth % 16) === 0 ? 1 : 0.5 + 0.3 * 144 / 192)) < 1e-6);
  }
  assert.ok(hits.length > 999, "the test needs more than 999 kick hits to see the wrap");
  noErrors(brain);
});

test("Editing cycles rest -> hit -> accent -> rest; shift sets a ghost; the stored values bring it all back", () => {
  const brain = readyBrain();
  brain.send("edit", 6, 5);
  assert.strictEqual(brain.lastRows()[6][5], "x");
  brain.send("edit", 6, 5);
  assert.strictEqual(brain.lastRows()[6][5], "X");
  brain.send("edit", 6, 5);
  assert.strictEqual(brain.lastRows()[6][5], ".");
  brain.send("edit", 6, 9, 1);
  assert.strictEqual(brain.lastRows()[6][9], "o");
  brain.send("edit", 6, 9);
  assert.strictEqual(brain.lastRows()[6][9], "x");
  brain.send("edit", 1, 15); brain.send("edit", 1, 15);
  brain.send("lock", 2); brain.send("mute", 5);
  const rows = brain.lastRows();
  const stored = {};
  for (const o of brain.record.outlets) if (o[0] === 4) stored[o[1]] = o[2];
  assert.strictEqual(Object.keys(stored).length, 16);
  const reopened = loadBrain(99);
  reopened.send("generate");
  for (const name in stored) reopened.send(name, stored[name]);
  reopened.send("ready");
  assert.deepStrictEqual(reopened.lastRows(), rows);
  const flags = (name) => reopened.record.outlets.filter((o) => o[0] === 1 && o[1] === name).pop().slice(2);
  assert.deepStrictEqual(flags("locks"), [0, 0, 1, 0, 0, 0, 0]);
  assert.deepStrictEqual(flags("mutes"), [0, 0, 0, 0, 0, 1, 0]);
  noErrors(brain); noErrors(reopened);
});

test("Mute silences a voice without changing its row", () => {
  const brain = readyBrain();
  brain.send("mute", 5);
  assert.strictEqual(brain.lastRows()[5], P1[5]);
  assert.ok(!brain.play(2).some((h) => h.voice === "oh"));
  brain.send("mute", 5);
  assert.ok(brain.play(1, 32).some((h) => h.voice === "oh"));
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
  brain.send("density", 3);
  brain.send("style", 99);
  brain.send("steps_zz_a", 1);
  brain.context.inlet = 0; brain.context.messagename = "style"; brain.context.anything(1);
  assert.strictEqual(brain.record.errors.length, 5, brain.record.errors.join(" | "));
  assert.strictEqual(brain.context.density, 1);
  assert.throws(() => brain.context.parseRow("x..", "test"), /not 16 steps/);
});

// ---- the UI script (the kit's) -----------------------------------------------------------------------------
test("UI: presets wait for ready, then set every control they name; pages show and hide", () => {
  const sent = [];
  const objects = {};
  const patcher = { getnamed: (name) => objects[name] || (objects[name] = { message: (...a) => sent.push([name].concat(a)) }) };
  const { context, record } = sandbox(1, { patcher, max: { getcolor: () => [0.15, 0.15, 0.15, 1] } });
  vm.runInContext(UI_SOURCE, context, { filename: "2sl-drums-ui.js" });
  context.msg_int(1);
  assert.strictEqual(sent.length, 0, "a preset before ready was applied");
  context.messagename = "ready"; context.anything();
  context.msg_int(2);
  const preset = context.PRESETS[2];
  for (const name in preset) assert.ok(sent.some((s) => s[0] === name && s[1] === preset[name]), "preset didn't set " + name);
  record.outlets.length = 0;
  context.page(1);
  const hidden = record.outlets.filter((o) => o[3] === "view_bd");
  assert.deepStrictEqual(hidden[0].slice(4), ["hidden", 0]);
  context.msg_int(99);
  context.messagename = "bogus"; context.anything();
  assert.strictEqual(record.errors.length, 2, record.errors.join(" | "));
});

// ---- the displays ---------------------------------------------------------------------------------------------
function loadView(mode) {
  const drawn = { calls: 0 };
  const mgraphics = new Proxy({ size: mode === "grid" ? [384, 85] : [200, 64] }, {
    get: (target, key) => (key in target ? target[key] : () => { drawn.calls++; }),
    set: (target, key, value) => { target[key] = value; return true; },
  });
  function Task(fn) { this.fn = fn; this.repeat = () => {}; this.cancel = () => {}; }
  const { context, record } = sandbox(1, { mgraphics, Task, jsarguments: ["2sl-drums-view.js", mode],
                                           max: { getcolor: () => [0.15, 0.15, 0.15, 1], launchbrowser: () => {} } });
  vm.runInContext(VIEW_SOURCE, context, { filename: "2sl-drums-view.js" });
  const send = (name, ...args) => { context.messagename = name; context.anything(...args); };
  return { context, record, drawn, send };
}

test("Every display draws with its Init values, takes its messages, and the grid's clicks edit", () => {
  const modes = ["chrome", "link", "grid", "style", "mix", "bd", "sd", "rs", "cp", "hats", "rd"];
  for (const mode of modes) {
    const view = loadView(mode);
    view.context.paint();
    assert.ok(view.drawn.calls > 0, mode + " drew nothing");
    assert.deepStrictEqual(view.record.errors, [], mode + ": " + view.record.errors.join(" | "));
  }
  const grid = loadView("grid");
  grid.send("rows", ...P1);
  grid.send("locks", 0, 1, 0, 0, 0, 0, 0);
  grid.send("mutes", 0, 0, 0, 0, 0, 1, 0);
  grid.send("pos", 3);
  grid.send("hit", 0, 3);
  grid.send("fillbar", 1);
  grid.context.paint();
  const g = grid.context.gridGeometry(384, 85);
  const clicks = [[g.stepsX + 2 * g.cellW + 2, 1 + 1 * g.rowH + 3, 0], [g.stepsX + 5 * g.cellW + 2, 1 + 2 * g.rowH + 3, 1],
                  [5, 1 + 4 * g.rowH + 3, 0], [g.lockX + 3, 1 + 6 * g.rowH + 3, 0], [g.rerollX + 3, 3, 0]];
  for (const [x, y, shift] of clicks) grid.context.onclick(x, y, 1, 0, shift, 0, 0, 0);
  assert.deepStrictEqual(grid.record.outlets.map((o) => o.slice(1)),
                         [["edit", 1, 2], ["edit", 2, 5, 1], ["mute", 4], ["lock", 6], ["reroll", 0]]);
  const style = loadView("style");
  style.send("style", "dub techno", "120-145 bpm", "none", "P1 basic channel");
  style.send("sources", "a", "b", "c", "d", "e", "f", "g");
  style.send("bar", 3, 4);
  style.context.paint();
  const mixer = loadView("mix");
  mixer.send("hit", 2, 0.8);
  mixer.context.paint();
  for (const v of [grid, style, mixer]) assert.deepStrictEqual(v.record.errors, [], v.record.errors.join(" | "));
  const wrong = loadView("bd");
  wrong.send("no_such_thing", 1);
  assert.strictEqual(wrong.record.errors.length, 1);
});

// ---- run ----------------------------------------------------------------------------------------------------
let failed = 0;
for (const t of tests) {
  try { t.body(); console.log("ok   " + t.name); }
  catch (e) { failed++; console.log("FAIL " + t.name + "\n     " + (e.stack || e).toString().split("\n").slice(0, 4).join("\n     ")); }
}
console.log((tests.length - failed) + "/" + tests.length + " passed");
process.exit(failed ? 1 : 0);

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
const BRAIN_SOURCE = fs.readFileSync(path.join(DEVICE_FOLDER, SCRIPT_NAME + ".js"), "utf8");
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
    // a control keeps the number it was last sent (as Live's parameter does) and getvalueof() reads it; every
    // control starts where Live loads it: its initial value (LIVE_INITIAL), or record.values set by a test first
    patcher: { getnamed: (name) => ({
      message: function () {
        const args = Array.prototype.slice.call(arguments);
        (record.messagesTo[name] = record.messagesTo[name] || []).push(args);
        if (args.length === 1 && typeof args[0] === "number") record.values[name] = args[0];
      },
      getvalueof: () => (name in record.values ? record.values[name] : LIVE_INITIAL[name]),
    }) },
  };
}

/** {varname: Live's initial value} of every parameter in the patch: what a fresh device loads at. */
const LIVE_INITIAL = {};
for (const box of PATCH.patcher.boxes.map((b) => b.box)) {
  const valueof = box.saved_attribute_attributes && box.saved_attribute_attributes.valueof;
  if (box.varname && valueof && valueof.parameter_initial) LIVE_INITIAL[box.varname] = valueof.parameter_initial[0];
}

function load(source, mode, values) {
  const record = { values: Object.assign({}, values || {}) };
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

// ---- a fresh device moves to its start values once; a saved set or preset is never touched -----------------

const FRESH_START = JSON.parse(UI_SOURCE.match(/^var FRESH_START = (\{.*?\});/m)[1]);
const NEUTRAL = JSON.parse(UI_SOURCE.match(/^var NEUTRAL = (\{.*?\});/m)[1]);
const controlMessages = (record) => Object.keys(record.messagesTo).filter((n) => n !== "init_applied" &&
  record.messagesTo[n].some((m) => m.length === 1 && typeof m[0] === "number"));

test("a fresh device (flag 0, every control at its neutral value) moves to the Init sound on ready, once", () => {
  const { context, record } = load(UI_SOURCE);
  for (const name in NEUTRAL) assert.strictEqual(LIVE_INITIAL[name], NEUTRAL[name][0], name + ": Live loads its neutral");
  deliverMessage(context, 0, "ready", []);
  assert.deepStrictEqual(record.errors, []);
  // the fixture's Init values that aren't neutral (tests/fixture_device.py): Level 50, In key on, Chord minor (index
  // 2 after "one note", "held notes"; its neutral is "held notes", 1), Loop 16 bars (index 5)
  assert.strictEqual(NEUTRAL.chord[0], 1);
  assert.deepStrictEqual({ level: record.values.level, in_key: record.values.in_key, chord: record.values.chord,
                           loop: record.values.loop }, { level: 50, in_key: 1, chord: 2, loop: 5 });
  assert.deepStrictEqual(controlMessages(record).sort(), Object.keys(FRESH_START).sort(),
                         "only the controls whose start isn't neutral are set");
  assert.strictEqual(record.values.init_applied, 1, "the flag is set");
  record.messagesTo = {};
  deliverMessage(context, 0, "ready", []);       // live.thisdevice bangs again on a preset load or a save
  assert.deepStrictEqual(controlMessages(record), [], "a second ready sets nothing");
});

test("a saved set or a preset (flag 1) keeps its values: nothing is set on ready", () => {
  const { context, record } = load(UI_SOURCE, undefined, { init_applied: 1, level: 0, chord: 0 });
  deliverMessage(context, 0, "ready", []);
  assert.deepStrictEqual(controlMessages(record), []);
  assert.deepStrictEqual(record.messagesTo.init_applied, undefined, "the flag is left alone");
  assert.deepStrictEqual(record.errors, []);
});

test("a set saved before the flag (flag 0, a control away from neutral) keeps its values and says so", () => {
  const { context, record } = load(UI_SOURCE, undefined, { level: 70 });
  deliverMessage(context, 0, "ready", []);
  assert.deepStrictEqual(controlMessages(record), [], "nothing moved to Init");
  assert.strictEqual(record.values.level, 70);
  assert.strictEqual(record.values.init_applied, 1, "the flag is set, so it isn't asked again");
  assert.ok(record.posts.some((p) => /saved before the fresh-start flag/.test(p) && /level/.test(p)), record.posts);
});

test("a flag that reads neither 0 nor 1 leaves the controls alone, loudly", () => {
  const { context, record } = load(UI_SOURCE, undefined, { init_applied: 7 });
  deliverMessage(context, 0, "ready", []);
  assert.deepStrictEqual(controlMessages(record), []);
  assert.ok(record.errors.some((e) => /fresh-start flag reads 7/.test(e)), record.errors);
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

test("a drag reaches the device's VIEW_DRAGS while held, and only a display that has one", () => {
  const level = load(VIEWS_SOURCE, "level");
  level.context.ondrag(10, 16, 1, 0, 0, 0, 0, 0);
  level.context.ondrag(10, 32, 0, 0, 0, 0, 0, 0);
  assert.deepStrictEqual(level.record.outlets, [[0, "level", 1 - 16 / level.context.mgraphics.size[1]]],
                         "the release (button 0) is told as not held");
  const chord = load(VIEWS_SOURCE, "chord");
  chord.context.ondrag(10, 16, 1, 0, 0, 0, 0, 0);
  assert.deepStrictEqual(chord.record.outlets, []);
  assert.deepStrictEqual(level.record.errors.concat(chord.record.errors), []);
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

// ---- the seeded random (templates/seeded-random.template.js) --------------------------------------------------------

function draws(context, count) { const out = []; for (let i = 0; i < count; i++) out.push(context.randomNext()); return out; }

test("the seeded random: the same seed gives the same sequence, another seed another, a new Seed restarts it", () => {
  const first = load(BRAIN_SOURCE), second = load(BRAIN_SOURCE);
  const a = draws(first.context, 50), b = draws(second.context, 50);
  assert.deepStrictEqual(a, b, "two devices on the Init Seed draw the same numbers");
  assert.ok(a.every((x) => x >= 0 && x < 1));
  deliverMessage(second.context, 1, "random_seed", [7]);
  const seven = draws(second.context, 50);
  assert.notDeepStrictEqual(seven, a, "Seed 7 isn't Seed 0");
  deliverMessage(second.context, 1, "random_seed", [7]);
  assert.deepStrictEqual(draws(second.context, 50), seven, "setting Seed starts its sequence over");
  deliverMessage(second.context, 1, "random_seed", [5000]);
  assert.ok(second.record.errors.some((e) => /Seed got 5000, outside 0..999/.test(e)), "a Seed out of range is loud");
  assert.deepStrictEqual(first.record.errors, []);
});

test("the seeded random is mulberry32: its first numbers for seed 0 and 1 are the reference ones", () => {
  // from the reference C, transcribed to Python with explicit 32-bit masks (uint32_t z = (x += 0x6D2B79F5); z = (z ^ z >> 15) * (z | 1);
  // z ^= z + (z ^ z >> 7) * (z | 61); return z ^ z >> 14;), divided by 2^32
  const { context } = load(BRAIN_SOURCE);
  const expected = [1144304738, 1416247, 958946056].map((z) => z / 4294967296);
  assert.deepStrictEqual(draws(context, 3), expected);
});

test("the seeded random runs without ES2015 Math (Max's [js] has no Math.imul): its multiply equals Math.imul", () => {
  const { context, record } = load(BRAIN_SOURCE);
  assert.strictEqual(vm.runInContext("typeof Math.imul", context), "undefined", "the sandbox hides ES2015 Math, as Max does");
  const multiply = context.multiplyLow32Bits;
  const edges = [0, 1, 0xffff, 0x10000, 0x7fffffff, 0x80000000, 0xffffffff, 0x6D2B79F5, -1, -0x80000000];
  let pairs = 0;
  for (const a of edges) for (const b of edges) { assert.strictEqual(multiply(a, b), Math.imul(a, b), a + " * " + b); pairs++; }
  let state = 12345;
  for (let i = 0; i < 20000; i++) {
    state = (Math.imul(state, 1103515245) + 12345) | 0;
    const a = state; state = (Math.imul(state, 1103515245) + 12345) | 0;
    assert.strictEqual(multiply(a, state), Math.imul(a, state), a + " * " + state); pairs++;
  }
  assert.ok(draws(context, 10).every((x) => x >= 0 && x < 1));
  assert.deepStrictEqual(record.errors, []);
});

test("the seeded random is about uniform", () => {
  const { context } = load(BRAIN_SOURCE);
  const bins = new Array(10).fill(0);
  for (const x of draws(context, 20000)) bins[Math.floor(x * 10)]++;
  for (const count of bins) assert.ok(Math.abs(count - 2000) < 200, "each tenth gets about 2000 of 20000: " + bins);
});

test("Loop starts the sequence over at each Loop boundary while Live plays, and at transport start", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "random_loop", [1]);                   // 1 bar = 16 16ths = 1920 ticks
  deliverMessage(context, 1, "playing", [1]);
  const fromTheTop = [];
  for (let sixteenth = 0; sixteenth < 48; sixteenth++) {
    deliverMessage(context, 1, "tick", [sixteenth * 120]);
    fromTheTop.push(context.randomNext());
  }
  assert.deepStrictEqual(fromTheTop.slice(16, 32), fromTheTop.slice(0, 16), "bar 2 repeats bar 1");
  assert.deepStrictEqual(fromTheTop.slice(32, 48), fromTheTop.slice(0, 16), "and bar 3");
  // jumping in: Live stopped and started again at bar 3: the transport start restarts it
  deliverMessage(context, 1, "playing", [0]);
  draws(context, 5);
  deliverMessage(context, 1, "playing", [1]);
  const fromBarThree = [];
  for (let sixteenth = 32; sixteenth < 40; sixteenth++) {
    deliverMessage(context, 1, "tick", [sixteenth * 120]);
    fromBarThree.push(context.randomNext());
  }
  assert.deepStrictEqual(fromBarThree, fromTheTop.slice(32, 40), "playing from a Loop boundary sounds as playing through");
  assert.deepStrictEqual(record.errors, []);
});

test("seededRandomStarts() counts each start over (Seed, transport start, a Loop boundary), for scripts that draw ahead", () => {
  const { context, record } = load(BRAIN_SOURCE);
  const starts = () => context.seededRandomStarts();
  assert.strictEqual(starts(), 0, "the sequence Seed began with is no start over");
  deliverMessage(context, 1, "random_seed", [3]);
  assert.strictEqual(starts(), 1, "a new Seed");
  deliverMessage(context, 1, "random_loop", [1]);
  assert.strictEqual(starts(), 1, "a new Loop length starts nothing");
  deliverMessage(context, 1, "playing", [1]);
  assert.strictEqual(starts(), 2, "Live starting");
  for (let sixteenth = 0; sixteenth < 17; sixteenth++) deliverMessage(context, 1, "tick", [sixteenth * 120]);
  assert.strictEqual(starts(), 3, "bar 2's first 16th, a Loop boundary");
  assert.deepStrictEqual(record.errors, []);
});

test("Loop off never restarts while Live plays; a new Loop length doesn't restart it either", () => {
  const { context } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "random_loop", [0]);
  deliverMessage(context, 1, "playing", [1]);
  const played = [];
  for (let sixteenth = 0; sixteenth < 40; sixteenth++) {
    deliverMessage(context, 1, "tick", [sixteenth * 120]);
    played.push(context.randomNext());
  }
  const reference = load(BRAIN_SOURCE).context;
  assert.deepStrictEqual(played, draws(reference, 40), "one unbroken sequence");
  deliverMessage(context, 1, "random_loop", [1]);
  const next = context.randomNext();
  deliverMessage(context, 1, "tick", [40 * 120]);
  assert.strictEqual(context.randomNext(), draws(reference, 2)[1], "the length change and the next 16th keep going");
  assert.ok(next >= 0);
});

test("with Live stopped the sequence keeps stepping: no restart", () => {
  const { context } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "random_loop", [1]);
  const stopped = [];
  for (let sixteenth = 0; sixteenth < 40; sixteenth++) {
    deliverMessage(context, 1, "tick", [sixteenth * 120]);    // ticks while stopped mean nothing to it
    stopped.push(context.randomNext());
  }
  assert.deepStrictEqual(stopped, draws(load(BRAIN_SOURCE).context, 40));
});

// ---- the chord block (templates/chord-block.template.js, chord-display.template.js) ---------------------------------

function chordsShown(record) { return record.outlets.filter((o) => o[0] === 1 && o[1] === "chord"); }

test("the chord block: a key plays the Init shape (minor), held notes play the key, a double hold needs two note-offs", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 0, "list", [57, 100]);
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "Am", 57, 60, 64]);
  deliverMessage(context, 0, "list", [57, 100]);                    // held again (a second clip)
  deliverMessage(context, 0, "list", [57, 0]);
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "Am", 57, 60, 64], "still held");
  deliverMessage(context, 0, "list", [57, 0]);
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord"], "released: nothing");
  deliverMessage(context, 1, "chord_shape", [1]);
  assert.ok(context.chordShapeIsHeldNotes() && !context.chordShapeIsOneNote());
  deliverMessage(context, 0, "list", [60, 100]);
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "C3", 60], "one note: its name and octave");
  deliverMessage(context, 0, "list", [60, 0]);
  deliverMessage(context, 1, "chord_shape", [0]);                  // the fixture has "one note" first
  assert.ok(context.chordShapeIsOneNote() && !context.chordShapeIsHeldNotes());
  assert.deepStrictEqual(Array.from(context.chordOnKey(62)), [62], "one note: the key alone");
  deliverMessage(context, 1, "chord_shape", [10]);
  assert.ok(record.errors.some((e) => /Chord got 10, outside 0..8/.test(e)));
});

test("the chord block fits m11 to the fixture's 4 notes: the fifth and the ninth go", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "chord_shape", [5]);
  deliverMessage(context, 0, "list", [57, 100]);
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "Am11", 57, 60, 67, 74]);
});

test("In key stacks Live's scale; under 5 notes it falls back to the fixed shapes, loudly", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "scale_root", [0]);
  deliverMessage(context, 1, "scale_intervals", [0, 2, 4, 5, 7, 9, 11]);   // C major
  deliverMessage(context, 0, "list", [62, 100]);                          // D, minor shape: scale steps 0 2 4
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "Dm", 62, 65, 69]);
  deliverMessage(context, 0, "list", [62, 0]);
  deliverMessage(context, 0, "list", [64, 100]);                          // E: Em in C major
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "Em", 64, 67, 71]);
  deliverMessage(context, 0, "list", [64, 0]);
  deliverMessage(context, 1, "scale_intervals", [0, 3, 7]);
  assert.deepStrictEqual(record.outlets.filter((o) => o[1] === "notice").pop(), [1, "notice", "scale <5 notes: fixed shapes"]);
  assert.ok(record.posts.some((p) => /under 5: chords use the fixed shapes/.test(p)));
  deliverMessage(context, 0, "list", [64, 100]);
  assert.deepStrictEqual(chordsShown(record).pop(), [1, "chord", "Em", 64, 67, 71], "E minor from the fixed shape");
  deliverMessage(context, 1, "chord_in_key", [0]);
  assert.deepStrictEqual(record.outlets.filter((o) => o[1] === "notice").pop(), [1, "notice"], "In key off: no notice");
  deliverMessage(context, 1, "chord_in_key", [1]);
  deliverMessage(context, 1, "chord_shape", [0]);
  assert.deepStrictEqual(record.outlets.filter((o) => o[1] === "notice").pop(), [1, "notice"], "one note: no shape, no notice");
  assert.deepStrictEqual(record.errors, []);
});

test("chord names", () => {
  const { context } = load(BRAIN_SOURCE);
  const named = (pitches) => context.chordName(pitches);
  assert.strictEqual(named([57, 60, 64, 67]), "Am7");
  assert.strictEqual(named([57, 60, 67, 74]), "Am11", "a minor 7th with an 11th and no 9th is m11");
  assert.strictEqual(named([57, 60, 67, 71]), "Am9");
  assert.strictEqual(named([57, 64, 69]), "A5");
  assert.strictEqual(named([60, 72]), "C", "octaves of one note");
  assert.strictEqual(named([64, 69, 72]), "Am/E");
  assert.strictEqual(named([60, 64, 67, 71, 74]), "Cmaj9");
  assert.strictEqual(named([]), "");
});

test("Drift's voicings come from the seeded random: the same Seed varies the same way", () => {
  const voicings = (seed) => {
    const { context } = load(BRAIN_SOURCE);
    deliverMessage(context, 1, "random_seed", [seed]);
    const out = [];
    for (let i = 0; i < 20; i++) out.push(context.chordDrifted([57, 60, 64, 67], 0.5).join(" "));
    return out;
  };
  assert.deepStrictEqual(voicings(3), voicings(3));
  assert.notDeepStrictEqual(voicings(3), voicings(4));
  assert.ok(new Set(voicings(3)).size > 1, "Drift 50% varies some of them");
});

test("the chord display draws a chord and a notice, and is loud about a bad chord", () => {
  const { context, record } = load(VIEWS_SOURCE, "chord");
  deliverMessage(context, 0, "chord", ["Am7", 57, 60, 64, 67]);
  context.paint();
  deliverMessage(context, 0, "notice", ["scale", "<5", "notes:", "fixed", "shapes"]);
  context.paint();
  deliverMessage(context, 0, "chord", []);
  context.paint();
  assert.deepStrictEqual(record.errors, []);
  deliverMessage(context, 0, "chord", ["Am", 57, 600]);
  assert.ok(record.errors.some((e) => /not all MIDI pitches/.test(e)));
});

// ---- the stored table (the fixture's Stage: 2 rows of Pitch -24..24, Pulse off / on, Wait go / stop / hold / keyed)

const PITCH_CODES_PER_SEMITONE = 1365;           // 65535 // 48, so every whole semitone is exact
const pitchCode = (semitones) => (semitones + 24) * PITCH_CODES_PER_SEMITONE;
const tableWrites = (record) => record.outlets.filter((o) => o[0] === 2);
const plain = (value) => JSON.parse(JSON.stringify(value));             // the script's objects, out of its realm

test("the stored table starts at Init, and reads by row and field", () => {
  const { context, record } = load(BRAIN_SOURCE);
  assert.strictEqual(context.storedTableValue("Stage", "Pitch", 1), 7);
  assert.deepStrictEqual(plain(context.storedTableRow("Stage", 1)), { Pitch: 7, Pulse: 1, Wait: 3 });
  assert.deepStrictEqual(record.errors, []);
  assert.strictEqual(context.storedTableValue("Stage", "Pitch", 2), undefined);
  assert.strictEqual(context.storedTableValue("Stage", "Time", 0), undefined);
  assert.strictEqual(context.storedTableValue("Steps", "Pitch", 0), undefined);
  assert.strictEqual(record.errors.length, 3, "a row, field or table that doesn't exist is an error each");
});

test("a recalled stored value is unpacked, heard, and shown on its editors once the device is ready", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "stage_pitch_1", [pitchCode(12)]);
  deliverMessage(context, 1, "stage_switches_1", [1 + (2 << 1)]);           // Pulse on, Wait hold
  assert.deepStrictEqual(plain(context.storedTableRow("Stage", 0)), { Pitch: 12, Pulse: 1, Wait: 2 });
  assert.deepStrictEqual(plain(context.stageChanges), [["Pitch", 0, 12], ["Pulse", 0, 1], ["Wait", 0, 2]]);
  assert.deepStrictEqual(tableWrites(record), [], "nothing is written back, and no editor is set before ready");
  deliverMessage(context, 1, "ready", []);
  assert.deepStrictEqual(tableWrites(record), [[2, "stage_pitch_edit_1", "set", 12], [2, "stage_pitch_edit_2", "set", 7],
                                               [2, "stage_pulse_edit_1", "set", 1], [2, "stage_wait_edit_2", "set", 3]]);
  record.outlets.length = 0;
  deliverMessage(context, 1, "stage_pitch_2", [pitchCode(-3)]);
  assert.deepStrictEqual(tableWrites(record), [[2, "stage_pitch_edit_2", "set", -3]]);
  assert.deepStrictEqual(record.errors, []);
});

test("an editor sets its value once the device is ready: stored, heard, not told back; the echo changes nothing", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "stage_pitch_edit_1", [5]);
  assert.strictEqual(context.storedTableValue("Stage", "Pitch", 0), 0, "before ready an editor is the set loading");
  deliverMessage(context, 1, "ready", []);
  record.outlets.length = 0;
  context.stageChanges.length = 0;
  deliverMessage(context, 1, "stage_pitch_edit_1", [5]);
  assert.deepStrictEqual(tableWrites(record), [[2, "stage_pitch_1", pitchCode(5)]]);
  assert.deepStrictEqual(plain(context.stageChanges), [["Pitch", 0, 5]]);
  deliverMessage(context, 1, "stage_pitch_1", [pitchCode(5)]);              // the stored parameter puts it out again
  assert.deepStrictEqual(plain(context.stageChanges), [["Pitch", 0, 5]], "the echo is no change");
  record.outlets.length = 0;
  deliverMessage(context, 1, "stage_wait_edit_2", [1]);                    // row 2: Pulse on (1), Wait stop (1)
  deliverMessage(context, 1, "stage_pulse_edit_1", [1]);                   // row 1: Pulse on, Wait go
  assert.deepStrictEqual(tableWrites(record), [[2, "stage_switches_2", 1 + (1 << 1)], [2, "stage_switches_1", 1]]);
  assert.deepStrictEqual(record.errors, []);
});

test("storedTableSet keeps a value on the stored grid and refuses one out of range, loudly", () => {
  const { context, record } = load(BRAIN_SOURCE);
  const kept = context.storedTableSet("Stage", "Pitch", 0, 0.3);
  assert.ok(Math.abs((kept + 24) * PITCH_CODES_PER_SEMITONE - Math.round((kept + 24) * PITCH_CODES_PER_SEMITONE)) < 1e-9);
  assert.ok(Math.abs(kept - 0.3) <= 0.5 / PITCH_CODES_PER_SEMITONE);
  assert.strictEqual(context.storedTableValue("Stage", "Pitch", 0), kept);
  assert.deepStrictEqual(tableWrites(record), [[2, "stage_pitch_1", Math.round(24.3 * PITCH_CODES_PER_SEMITONE)]]);
  assert.deepStrictEqual(record.errors, []);
  assert.strictEqual(context.storedTableSet("Stage", "Pitch", 0, 25), undefined);
  assert.strictEqual(context.storedTableSet("Stage", "Wait", 0, 4), undefined);
  assert.strictEqual(context.storedTableSet("Stage", "Pulse", 0, 0.5), undefined);
  assert.strictEqual(record.errors.length, 3);
  assert.strictEqual(context.storedTableValue("Stage", "Pitch", 0), kept, "a refused value changes nothing");
});

test("a recalled code that isn't one is an error, and changes nothing", () => {
  const { context, record } = load(BRAIN_SOURCE);
  deliverMessage(context, 1, "stage_pitch_1", [70000]);
  deliverMessage(context, 1, "stage_pitch_1", [65530]);                    // past +24 (48 x 1365 = 65520)
  deliverMessage(context, 1, "stage_switches_1", [8]);                     // past the row's 3 bits
  deliverMessage(context, 1, "stage_switches_1", [2.5]);
  assert.strictEqual(record.errors.length, 4);
  assert.deepStrictEqual(plain(context.storedTableRow("Stage", 0)), { Pitch: 0, Pulse: 0, Wait: 0 });
  assert.deepStrictEqual(plain(context.stageChanges), []);
});

let failed = 0;
for (const { name, body } of tests) {
  try { body(); console.log("ok   " + name); } catch (problem) { failed++; console.log("FAIL " + name + "\n     " + problem.stack); }
}
console.log((tests.length - failed) + "/" + tests.length + " passed");
process.exit(failed ? 1 : 0);

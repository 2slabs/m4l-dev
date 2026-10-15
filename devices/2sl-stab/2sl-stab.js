// 2sl stab: the chord brain. Chord memory, in-key chords, voicing drift, latch, and the stab machine.
//   in 0: note list (pitch velocity), velocity 0 = note off
//   in 1: control messages
//     shape i       Chord menu: 0 poly, 1 minor, 2 m7, 3 m9, 4 m11, 5 sus4, 6 fifths, 7 dark
//     inkey i       1 = build chords from Live's scale instead of a fixed (parallel) shape (a scale under
//                   5 notes falls back to the fixed shapes, and the chord display says so)
//     root i / intervals ...   Live's Scale Mode key
//     drift f       0..1: chance each stab gets a different voicing
//     machine i / latch i
//     pattern i     load a pattern (a starting point; steps can then be edited)
//     edit i        cycle the step shown at display position i: rest -> hit -> accent -> rest (from the step display)
//     shift i       0..15: play (and show) the stored pattern i 16ths later, wrapping; the stored steps don't change
//     stepbits i / accbits i   the pattern as stored with the set (two hidden parameters)
//     density f, throws f, length i (Gate: 1-4 16ths)
//     tick bar beat units       from [transport], once per 16th while Live plays
//     playing i / tempo f       Live's transport; stopped, the machine runs on its own clock
//     ready         Live has finished restoring the set
//     stop          release everything and clear the latch (the Stop button only; Live stopping lets tails ring out)
// out 0: note lists for midiformat
// out 1: bang = throw
// out 2: to the step display     out 3: to the chord display     out 4: stepbits/accbits to store
// A control value outside its range can only come from a wiring or message error: it is logged in the Max
// window, then clamped. (Clamping that is behaviour, like velocity math, uses clampi directly.)
inlets = 2;
outlets = 5;

var SHAPES = [null, [0, 3, 7], [0, 3, 7, 10], [0, 3, 10, 14], [0, 3, 7, 10, 14, 17], [0, 5, 7, 12], [0, 7, 12], [0, 5, 8]];
var STEPS = [null, [0, 2, 4], [0, 2, 4, 6], [0, 2, 6, 8], [0, 2, 4, 6, 8, 10], [0, 3, 4, 7], [0, 4, 7], [0, 3, 5]];

// Stab patterns (X accent, x hit, . rest), from chord progressions' research.
var PATTERNS = [
  "X..x..x.........", // dub dotted
  "X.........x.....", // one & three+
  "..x.......x.....", // offbeat chops
  "..x...x...x...x.", // skank
  "..X..x....X..x..", // deep stab (off the kick)
  "X..x..x.X..x..x."  // 3-3-2
];

var shape = 1, inkey = 0, root = 0, intervals = [], drift = 0;
var machine = 0, latch = 0, density = 0.8, throws = 0, length = 1, ready = 0;
var steps = parse(PATTERNS[0]);   // the pattern as stored (unshifted)
var shift = 0;                    // 16ths the pattern plays later than stored

var keys = {};      // physically held keys -> velocity
var latched = {};   // latched chord: key -> velocity
var sent = {};      // played key -> pitches it sent (direct play)
var count = {};     // sounding pitch -> how many holders
var pending = [];   // machine notes waiting for their note-off: {pitches, left}
var playing = 0, tempo = 120, ownStep = 0;

var clock = new Task(function () {
  step16(ownStep);
  ownStep = (ownStep + 1) % 16;
});

// ---- helpers --------------------------------------------------------------------------

function parse(str) {
  var a = [];
  for (var i = 0; i < 16; i++) { var c = str.charAt(i); a.push(c === "X" ? 2 : c === "x" ? 1 : 0); }
  return a;
}
/** The stored step that plays at `position` (0..15) with the pattern shifted `shift` 16ths later. */
function storedIndexAt(position) { return (position - shift + 16) % 16; }
/** The pattern as it plays: one character per playing position, Shift applied. */
function patternString() {
  var shown = "";
  for (var position = 0; position < 16; position++) {
    var s = steps[storedIndexAt(position)];
    shown += s === 2 ? "X" : s === 1 ? "x" : ".";
  }
  return shown;
}
function clampi(v, lo, hi) { return Math.max(lo, Math.min(hi, Math.round(v))); }
/** A control's integer value, lo..hi. Out of range (or not a number) is a wiring error: logged, then clamped. */
function controlInt(control, v, lo, hi) {
  if (!(v >= lo && v <= hi)) {
    error("2sl stab: " + control + " got " + v + ", outside " + lo + ".." + hi + " (a wiring or message error): using " +
          (clampi(v, lo, hi) || lo) + "\n");
    return clampi(v, lo, hi) || lo;
  }
  return Math.round(v);
}
/** A control's 0..1 value. Out of range (or not a number) is a wiring error: logged, then clamped. */
function controlUnit(control, v) {
  if (!(v >= 0 && v <= 1)) {
    var used = Math.max(0, Math.min(1, v)) || 0;
    error("2sl stab: " + control + " got " + v + ", outside 0..1 (a wiring or message error): using " + used + "\n");
    return used;
  }
  return v;
}

function send(p, v) { if (p >= 0 && p <= 127) outlet(0, p, v); }
function sound(pitches, v) {
  for (var i = 0; i < pitches.length; i++) {
    var p = pitches[i];
    // Already sounding: stop it first, so a pitch never holds two voices (one would never be released).
    if (count[p] > 0) send(p, 0);
    count[p] = (count[p] || 0) + 1;
    send(p, v);
  }
}
function silence(pitches) {
  for (var i = 0; i < pitches.length; i++) {
    var p = pitches[i];
    count[p] = (count[p] || 1) - 1;
    if (count[p] <= 0) { delete count[p]; send(p, 0); }
  }
}

// ---- chords ---------------------------------------------------------------------------

var NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

/** A readable chord name for any set of pitches ("Am7", "Dm/A", "C5"). */
function chordName(pitches) {
  if (!pitches.length) return "";
  var sorted = pitches.slice().sort(function (a, b) { return a - b; });
  var low = ((sorted[0] % 12) + 12) % 12;
  var pcs = {};
  sorted.forEach(function (p) { pcs[((p % 12) + 12) % 12] = 1; });
  var best = low, bestScore = -1;
  for (var r in pcs) {
    r = Number(r);
    var score = (pcs[(r + 3) % 12] || pcs[(r + 4) % 12] ? 2 : 0) + (pcs[(r + 7) % 12] ? 2 : 0) + (r === low ? 1 : 0);
    if (score > bestScore) { bestScore = score; best = r; }
  }
  var h = function (i) { return !!pcs[(best + i) % 12]; };
  var q;
  var minor = h(3) && !h(4), major = h(4);
  var sev = h(10) ? 10 : h(11) ? 11 : 0;
  if (minor && h(6) && !h(7)) q = sev === 10 ? "m7b5" : "dim";
  else if (minor) q = sev ? (h(5) && h(2) ? "m11" : h(2) ? "m9" : "m7") : (h(2) ? "madd9" : "m");
  else if (major) q = sev === 11 ? (h(2) ? "maj9" : "maj7") : sev === 10 ? (h(2) ? "9" : "7") : (h(2) ? "add9" : "");
  else if (h(5)) q = sev ? "7sus4" : "sus4";
  else if (h(2) && h(7)) q = "sus2";
  else q = "5";
  return NAMES[best] + q + (best !== low ? "/" + NAMES[low] : "");
}

var intervalsKnown = false;   // Live's scale has been reported (until then In Key can't be judged)
function scaleOk() { return inkey && intervals.length >= 5; }

/** In Key with Live's scale under 5 notes: the chords fall back to the fixed shapes. That is the behaviour,
 *  but it must show: the chord display says so, and the Max window logs each change. */
var fixedShapesNoticeShown = false;
function updateInKeyNotice() {
  var fallingBack = !!(inkey && SHAPES[shape] && intervalsKnown && intervals.length < 5);
  if (fallingBack === fixedShapesNoticeShown) return;
  fixedShapesNoticeShown = fallingBack;
  if (fallingBack) {
    post("2sl stab: In Key: Live's scale has " + intervals.length + " notes, under 5: chords use the fixed shapes\n");
    outlet(3, "notice", "scale <5 notes: fixed shapes");
  } else {
    post("2sl stab: In Key: " + (inkey && SHAPES[shape] ? "chords from Live's scale again (" + intervals.length + " notes)"
                                                       : "off, or poly: the fixed-shape notice is gone") + "\n");
    outlet(3, "notice");
  }
}

/** Stack scale tones on `key` (snapped down into Live's scale): steps are scale steps above it. */
function chordInKey(key, st) {
  var inScale = {};
  for (var i = 0; i < intervals.length; i++) inScale[(root + intervals[i]) % 12] = 1;
  var k = key;
  while (!inScale[((k % 12) + 12) % 12] && k > key - 12) k--;
  var ladder = [];
  for (var p = k; p <= k + 48; p++) if (inScale[((p % 12) + 12) % 12]) ladder.push(p);
  return st.map(function (s) { return ladder[Math.min(s, ladder.length - 1)]; });
}

/** Another voicing of the same chord: invert, drop the top, spread the middle, or add the octave. */
function vary(pitches) {
  var p = pitches.slice().sort(function (a, b) { return a - b; });
  if (p.length < 3) return p;
  var r = Math.random();
  if (r < 0.3) p.push(p.shift() + 12);
  else if (r < 0.55) p.unshift(p.pop() - 12);
  else if (r < 0.8) p[1] += 12;
  else p.push(p[0] + 12);
  var seen = {}, out = [];
  for (var i = 0; i < p.length; i++) if (!seen[p[i]]) { seen[p[i]] = 1; out.push(p[i]); }
  return out.sort(function (a, b) { return a - b; });
}

function baseChord(key) {
  if (!SHAPES[shape]) return [key];
  return scaleOk() ? chordInKey(key, STEPS[shape]) : SHAPES[shape].map(function (i) { return key + i; });
}

function chordFor(key) {
  var pitches = baseChord(key);
  return Math.random() < drift ? vary(pitches) : pitches;
}

// ---- what the displays show -----------------------------------------------------------

/** The chord the machine plays: the latched chord while Live plays; with Live stopped only the keys you
 *  hold (to audition), so stopping Live stops the machine the way it stops a clip. */
function machineChord() { return latch && playing ? latched : keys; }

/** The chord the machine plays (all held or latched keys, without drift), for the status line. */
function heldName() {
  var ks = Object.keys(machineChord()).map(Number);
  var all = [];
  ks.forEach(function (k) { all = all.concat(baseChord(k)); });
  return all.length ? chordName(all) : "";
}

function showSteps() {
  outlet(2, "pattern", patternString());
  outlet(2, "machine", machine);
  outlet(2, "latch", latch);
  outlet(2, "held", heldName() || "-");
}
function showChord(pitches) {
  if (pitches && pitches.length) outlet(3, ["chord", chordName(pitches)].concat(pitches));
  else outlet(3, "clear");
}
function store() {
  var hits = 0, acc = 0;
  for (var i = 0; i < 16; i++) {
    if (steps[i] >= 1) hits |= 1 << i;
    if (steps[i] === 2) acc |= 1 << i;
  }
  outlet(4, "stepbits", hits);
  outlet(4, "accbits", acc);
}
var storedHits = -1, storedAcc = -1;
function fromStore() {
  if (storedHits < 0 || storedAcc < 0) return;
  for (var i = 0; i < 16; i++) steps[i] = (storedHits >> i) & 1 ? ((storedAcc >> i) & 1 ? 2 : 1) : 0;
  showSteps();
}

// ---- playing ---------------------------------------------------------------------------

function sentPitches() {
  var all = [];
  for (var k in sent) all = all.concat(sent[k]);
  return all;
}

function list(pitch, vel) {
  if (inlet === 1) {
    error("2sl stab: the brain's control inlet got a bare list (" + arrayfromargs(arguments).join(" ") + "): ignored\n");
    return;
  }
  if (vel > 0) {
    var anyHeld = Object.keys(keys).length > 0;
    keys[pitch] = vel;
    if (machine) {
      if (latch) {
        if (!anyHeld) latched = {}; // a fresh chord replaces the latched one
        latched[pitch] = vel;
      }
      showSteps();
      return;
    }
    if (sent[pitch]) silence(sent[pitch]);
    sent[pitch] = chordFor(pitch);
    sound(sent[pitch], vel);
    showChord(sentPitches());
  } else {
    delete keys[pitch];
    if (sent[pitch]) {
      silence(sent[pitch]);
      delete sent[pitch];
      showChord(sentPitches());
    }
    if (machine) showSteps();
  }
}

function updateClock() {
  clock.interval = 15000 / Math.max(20, tempo);
  if (machine && !playing) {
    if (!clock.running) { ownStep = 0; clock.repeat(); }
  } else if (clock.running) clock.cancel();
}

function tick(bar, beat, units) {
  if (!playing) return;
  step16(((beat - 1) * 4 + Math.round(units / 120)) % 16);
}

function step16(step) {
  for (var i = pending.length - 1; i >= 0; i--) {
    if (--pending[i].left <= 0) { silence(pending[i].pitches); pending.splice(i, 1); }
  }
  if (!machine) return;
  outlet(2, "pos", step);
  var chord = machineChord();
  var held = Object.keys(chord);
  if (!held.length) return;
  var s = steps[storedIndexAt(step)], hit = false;   // `step` is the playing position
  if (s === 2) hit = Math.random() < Math.min(1, density * 1.4);
  else if (s === 1) hit = Math.random() < density;
  else if (density > 0.7 && step % 2 === 1) hit = Math.random() < (density - 0.7) * 0.5; // the odd extra, on offbeats as heard
  if (!hit) return;
  var all = [];
  for (var k = 0; k < held.length; k++) {
    var key = Number(held[k]);
    var v = clampi(chord[key] * (s === 2 ? 1 : 0.82), 1, 127);
    var pitches = chordFor(key);
    sound(pitches, v);
    pending.push({ pitches: pitches, left: length });
    all = all.concat(pitches);
  }
  var threw = Math.random() < throws;
  if (threw) outlet(1, "bang");
  outlet(2, "hit", step, threw ? 1 : 0);
  showChord(all);
}

// ---- controls --------------------------------------------------------------------------

function panic() {
  for (var p in count) send(Number(p), 0);
  sent = {};
  count = {};
  pending = [];
  showChord(null);
}

function anything() {
  if (inlet !== 1) {
    error("2sl stab: the brain's note inlet got '" + messagename + "' (it takes pitch velocity lists): ignored\n");
    return;
  }
  var a = arrayfromargs(arguments);
  var v = a[0];
  switch (messagename) {
    case "shape": panic(); shape = controlInt("Chord", v, 0, SHAPES.length - 1); updateInKeyNotice(); showSteps(); break;
    case "inkey": inkey = v ? 1 : 0; updateInKeyNotice(); showSteps(); break;
    case "root": root = controlInt("Live's scale root", v, 0, 11); break;
    case "intervals":
      intervals = a.map(function (x) { return Math.round(x); });
      intervalsKnown = true;
      updateInKeyNotice();
      break;
    case "drift": drift = controlUnit("Drift", v); break;
    case "machine":
      machine = v ? 1 : 0;
      panic();
      if (!machine) latched = {};
      updateClock();
      if (!machine) outlet(2, "pos", -1);
      showSteps();
      break;
    case "latch":
      latch = v ? 1 : 0;
      latched = {};
      if (latch) for (var k in keys) latched[k] = keys[k];
      showSteps();
      break;
    case "pattern":
      if (!ready) break; // while Live restores the set, the stored steps win
      steps = parse(PATTERNS[controlInt("Pattern", v, 0, PATTERNS.length - 1)]);
      showSteps();
      store();
      break;
    case "edit":
      var i = storedIndexAt(controlInt("the step display's edit", v, 0, 15));   // v is the display position
      steps[i] = (steps[i] + 1) % 3;
      showSteps();
      store();
      break;
    case "stepbits": storedHits = controlInt("the stored Steps", v, 0, 65535); fromStore(); break;
    case "accbits": storedAcc = controlInt("the stored Accents", v, 0, 65535); fromStore(); break;
    case "shift": shift = controlInt("Shift", v, 0, 15); showSteps(); break;
    case "density": density = controlUnit("Density", v); break;
    case "throws": throws = controlUnit("Throws", v); break;
    case "length": length = controlInt("Gate", v, 1, 4); break;   // the Gate dial and its Info text: 1-4
    case "playing": playing = v ? 1 : 0; updateClock(); break;
    case "tempo": tempo = v; updateClock(); break;
    case "ready": ready = 1; showSteps(); break;
    case "stop":
      panic();
      latched = {};
      keys = {};
      outlet(2, "pos", -1);
      showSteps();
      break;
    default:
      error("2sl stab: the brain doesn't know the message '" + messagename + "': ignored\n");
  }
}

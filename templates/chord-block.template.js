// ---- the 2sl-dsp kit's chord block (templates/chord-block.template.js; architecture/chord-block.md) --------------
// What a key plays: a stored chord shape stacked on it (fixed intervals, or Live 12's Scale Mode with In key), or,
// with the shape "held notes", the key itself; the keys held (a key held twice, from two clips or two controllers,
// is released by its last note-off); a name for any set of pitches; another voicing of a chord (Drift), drawn from
// the kit's seeded random. The shapes are the kit's (twosl_dsp/chord_block.py), fitted by the build to the notes the
// device can sound for one chord.
// The script that includes this defines DEVICE_NAME and includes the kit's seeded random (randomNext()); it passes
// every control message to chordBlockMessage(name, args) (true when it took it: chord_shape, chord_in_key,
// scale_root, scale_intervals). The block tells the chord display (outlet CHORD_DISPLAY_OUTLET) what chordShow
// gives it and the In key notice.
var CHORD_SHAPES = /*CHORD_SHAPES*/;              // per Chord item: null (one note, held notes) or semitones above the key
var CHORD_SHAPE_STEPS = /*CHORD_SHAPE_STEPS*/;    // the same chords as scale steps above the key (In key)
var CHORD_DISPLAY_OUTLET = /*CHORD_DISPLAY_OUTLET*/;
var CHORD_ONE_NOTE_ITEM = /*CHORD_ONE_NOTE_ITEM*/;   // the Chord item "one note" (-1: the device has none)
var CHORD_IN_KEY_LEAST_SCALE_NOTES = 5;           // a smaller scale can't stack these shapes: the fixed shapes play
var CHORD_NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

var chordShape = /*INITIAL_CHORD_SHAPE*/, chordInKey = /*INITIAL_CHORD_IN_KEY*/;
var scaleRoot = 0, scaleIntervals = [], scaleKnown = false;   // Live's Scale Mode, once Live has reported it
var chordKeysHeld = [];                           // {key, velocity}, the oldest first
var chordKeyHolds = {};                           // key -> note-ons not yet released

function chordPitchClass(pitch) { return ((pitch % 12) + 12) % 12; }

// ---- messages -----------------------------------------------------------------------------------------------------

function chordWholeNumber(what, value, lowest, highest) {
  var used = Math.max(lowest, Math.min(highest, Math.round(value))) || lowest;
  if (!(value >= lowest && value <= highest)) {
    error(DEVICE_NAME + ": " + what + " got " + value + ", outside " + lowest + ".." + highest +
          " (a wiring or message error): using " + used + "\n");
  }
  return used;
}

function chordBlockMessage(name, args) {
  if (name === "chord_shape") chordShape = chordWholeNumber("Chord", args[0], 0, CHORD_SHAPES.length - 1);
  else if (name === "chord_in_key") chordInKey = chordWholeNumber("In key", args[0], 0, 1);
  else if (name === "scale_root") { scaleRoot = chordWholeNumber("Live's scale root", args[0], 0, 11); return true; }
  else if (name === "scale_intervals") {
    scaleIntervals = [];
    for (var i = 0; i < args.length; i++) scaleIntervals.push(chordWholeNumber("Live's scale intervals", args[i], 0, 11));
    scaleKnown = true;
  } else return false;
  updateChordInKeyNotice();
  return true;
}

// ---- In key ---------------------------------------------------------------------------------------------------------

function chordScaleIsUsable() { return chordInKey && scaleIntervals.length >= CHORD_IN_KEY_LEAST_SCALE_NOTES; }

/** In key with Live's scale under 5 notes: the chords fall back to the fixed shapes. That is the behaviour, but it
 *  must show: the chord display says so, and the Max window logs each change. */
var chordFixedShapesNoticeShown = false;
function updateChordInKeyNotice() {
  var inKeyApplies = !!(chordInKey && CHORD_SHAPES[chordShape]);
  var fallingBack = inKeyApplies && scaleKnown && scaleIntervals.length < CHORD_IN_KEY_LEAST_SCALE_NOTES;
  if (fallingBack === chordFixedShapesNoticeShown) return;
  chordFixedShapesNoticeShown = fallingBack;
  if (fallingBack) {
    post(DEVICE_NAME + ": In key: Live's scale has " + scaleIntervals.length + " notes, under " +
         CHORD_IN_KEY_LEAST_SCALE_NOTES + ": chords use the fixed shapes\n");
    outlet(CHORD_DISPLAY_OUTLET, "notice", "scale <" + CHORD_IN_KEY_LEAST_SCALE_NOTES + " notes: fixed shapes");
  } else {
    post(DEVICE_NAME + ": In key: " + (inKeyApplies ? "chords from Live's scale again (" + scaleIntervals.length +
         " notes)" : "not in use: the fixed-shape notice is gone") + "\n");
    outlet(CHORD_DISPLAY_OUTLET, "notice");
  }
}

/** Stack scale tones on `key` (snapped down into Live's scale): `steps` are scale steps above it. */
function chordInScale(key, steps) {
  var inScale = {};
  for (var i = 0; i < scaleIntervals.length; i++) inScale[(scaleRoot + scaleIntervals[i]) % 12] = 1;
  var snapped = key;
  while (!inScale[chordPitchClass(snapped)] && snapped > key - 12) snapped--;
  var ladder = [];
  for (var pitch = snapped; pitch <= snapped + 48; pitch++) if (inScale[chordPitchClass(pitch)]) ladder.push(pitch);
  var chord = [];
  for (var s = 0; s < steps.length; s++) chord.push(ladder[Math.min(steps[s], ladder.length - 1)]);
  return chord;
}

// ---- what a key plays -----------------------------------------------------------------------------------------------

/** Chord is "one note": the key alone, the device sounding the last key held. */
function chordShapeIsOneNote() { return chordShape === CHORD_ONE_NOTE_ITEM; }
/** Chord is "held notes": each key held plays itself. */
function chordShapeIsHeldNotes() { return !CHORD_SHAPES[chordShape] && !chordShapeIsOneNote(); }

/** The pitches `key` plays: the key itself (one note, held notes), or the shape on it, from Live's scale while In key
 *  can. */
function chordOnKey(key) {
  var shape = CHORD_SHAPES[chordShape];
  if (!shape) return [key];
  if (chordScaleIsUsable()) return chordInScale(key, CHORD_SHAPE_STEPS[chordShape]);
  var chord = [];
  for (var i = 0; i < shape.length; i++) chord.push(key + shape[i]);
  return chord;
}

/** Another voicing of the same chord (three notes or more): invert, drop the top, spread the middle, or add the
 *  octave, chosen by the seeded random. */
function chordVoicing(pitches) {
  var sorted = pitches.slice().sort(function (a, b) { return a - b; });
  if (sorted.length < 3) return sorted;
  var choice = randomNext();
  if (choice < 0.3) sorted.push(sorted.shift() + 12);
  else if (choice < 0.55) sorted.unshift(sorted.pop() - 12);
  else if (choice < 0.8) sorted[1] += 12;
  else sorted.push(sorted[0] + 12);
  var seen = {}, voiced = [];
  for (var i = 0; i < sorted.length; i++) if (!seen[sorted[i]]) { seen[sorted[i]] = 1; voiced.push(sorted[i]); }
  return voiced.sort(function (a, b) { return a - b; });
}

/** `pitches`, or (with chance `drift`, 0..1, a draw of the seeded random) another voicing of them. */
function chordDrifted(pitches, drift) { return randomNext() < drift ? chordVoicing(pitches) : pitches; }

// ---- the keys held --------------------------------------------------------------------------------------------------

/** A note-on: true when no key was held before it (a fresh chord, which replaces the last one). */
function chordKeyDown(key, velocity) {
  var fresh = chordKeysHeld.length === 0;
  chordKeyHolds[key] = (chordKeyHolds[key] || 0) + 1;
  chordKeysHeld = chordKeysHeld.filter(function (held) { return held.key !== key; });
  chordKeysHeld.push({ key: key, velocity: velocity });
  return fresh;
}
/** A note-off: true when it released the key (its last hold); false while another hold keeps it, or if it wasn't
 *  held. */
function chordKeyUp(key) {
  if (!chordKeyHolds[key]) return false;
  if (--chordKeyHolds[key] > 0) return false;
  delete chordKeyHolds[key];
  chordKeysHeld = chordKeysHeld.filter(function (held) { return held.key !== key; });
  return true;
}
function chordHeldKeys() { return chordKeysHeld.slice(); }
function chordReleaseAllKeys() { chordKeysHeld = []; chordKeyHolds = {}; }

// ---- names and the display ------------------------------------------------------------------------------------------

/** A readable name for any set of pitches: "Am7", "Dm/A", "C5"; one pitch is its note and octave (Live's: C3 is
 *  MIDI 60); octaves of one note are that note. */
function chordName(pitches) {
  if (!pitches.length) return "";
  if (pitches.length === 1) return CHORD_NOTE_NAMES[chordPitchClass(pitches[0])] + (Math.floor(pitches[0] / 12) - 2);
  var sorted = pitches.slice().sort(function (a, b) { return a - b; });
  var lowest = chordPitchClass(sorted[0]), classes = {}, classCount = 0;
  for (var i = 0; i < sorted.length; i++) {
    if (!classes[chordPitchClass(sorted[i])]) classCount++;
    classes[chordPitchClass(sorted[i])] = 1;
  }
  if (classCount === 1) return CHORD_NOTE_NAMES[lowest];
  // the root: the pitch class with a third and a fifth above it, the lowest note winning a tie
  var root = lowest, rootScore = -1;
  for (var candidate in classes) {
    candidate = Number(candidate);
    var score = (classes[(candidate + 3) % 12] || classes[(candidate + 4) % 12] ? 2 : 0) +
                (classes[(candidate + 7) % 12] ? 2 : 0) + (candidate === lowest ? 1 : 0);
    if (score > rootScore) { rootScore = score; root = candidate; }
  }
  var has = function (semitones) { return !!classes[(root + semitones) % 12]; };
  var minor = has(3) && !has(4), major = has(4), seventh = has(10) ? 10 : has(11) ? 11 : 0, quality;
  if (minor && has(6) && !has(7)) quality = seventh === 10 ? "m7b5" : "dim";
  else if (minor) quality = seventh ? (has(5) ? "m11" : has(2) ? "m9" : "m7") : (has(2) ? "madd9" : "m");
  else if (major) quality = seventh === 11 ? (has(2) ? "maj9" : "maj7") : seventh === 10 ? (has(2) ? "9" : "7") :
                            (has(2) ? "add9" : "");
  else if (has(5)) quality = seventh ? "7sus4" : "sus4";
  else if (has(2) && has(7)) quality = "sus2";
  else quality = "5";
  return CHORD_NOTE_NAMES[root] + quality + (root !== lowest ? "/" + CHORD_NOTE_NAMES[lowest] : "");
}

/** Tell the chord display what is sounding: `chord <name> <pitches...>`, or `chord` alone for nothing. */
function chordShow(pitches) {
  if (pitches && pitches.length) outlet(CHORD_DISPLAY_OUTLET, ["chord", chordName(pitches)].concat(pitches));
  else outlet(CHORD_DISPLAY_OUTLET, "chord");
}
// ---- end of the kit's chord block ---------------------------------------------------------------------------------

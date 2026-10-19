// ---- the m4l-dev kit's chord display (templates/chord-display.template.js; architecture/chord-block.md) ---------
// What the chord block sounds: the top line is the device's label (or, in orange, the In key notice), with the
// notes on the right; below, the chord's name large; then two octaves of keys from the C at or below the lowest
// note, the sounding ones lit. Drawn with the kit's views helpers. The device's views code passes every message to
// chordDisplayMessage(name, args) first (true when it took it: chord, notice) and paints its chord display with
// chordDisplayView(w, h, label).
var chordDisplay = { name: "", pitches: [], notice: "" };
var CHORD_DISPLAY_NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

function chordDisplayMessage(name, args) {
  if (name === "chord") {
    chordDisplay.name = args.length ? String(args[0]) : "";
    chordDisplay.pitches = args.slice(1);
    for (var i = 0; i < chordDisplay.pitches.length; i++) {
      if (!(chordDisplay.pitches[i] >= 0 && chordDisplay.pitches[i] <= 127)) {
        error(DEVICE_NAME + ": the " + MODE + " display got the chord " + args.join(" ") + " (not all MIDI pitches): " +
              "showing nothing\n");
        chordDisplay.name = "";
        chordDisplay.pitches = [];
        break;
      }
    }
    return true;
  }
  if (name === "notice") { chordDisplay.notice = args.join(" "); return true; }
  return false;
}

function chordDisplayView(w, h, label) {
  var pitches = chordDisplay.pitches, notes = "";
  if (pitches.length) {
    notes = pitches.slice().sort(function (a, b) { return a - b; })
                   .map(function (p) { return CHORD_DISPLAY_NOTE_NAMES[p % 12]; }).join(" ");
  }
  if (chordDisplay.notice) text(chordDisplay.notice, 4, 12, T.warm);        // the notice takes the whole top line
  else {
    // the notes win the top line: the label shows when both fit
    if (measure(label) + measure(notes) + 16 <= w) viewLabel(label);
    if (notes) viewInfo(notes, w, T.label);
  }
  if (!pitches.length) text("play a key", 4, 36, T.unlit, 2);
  else text(chordDisplay.name, 4, 38, T.ink, 2);
  var lit = {};
  for (var i = 0; i < pitches.length; i++) lit[pitches[i]] = 1;
  var lowest = pitches.length ? Math.min.apply(null, pitches) : 48;
  var start = lowest - (lowest % 12);
  var top = 46, keyHeight = h - top - 3, whites = [0, 2, 4, 5, 7, 9, 11], blacks = [1, 3, 6, 8, 10];
  var whiteCount = 14, keyWidth = (w - 8) / whiteCount;
  for (var k = 0; k < whiteCount; k++) {
    var white = start + 12 * Math.floor(k / 7) + whites[k % 7];
    rect(4 + k * keyWidth, top, keyWidth - 1, keyHeight, lit[white] ? T.mint : T.key);
  }
  var blackOffsets = [0.62, 1.62, 3.62, 4.62, 5.62];
  for (var octave = 0; octave < 2; octave++) {
    for (var j = 0; j < 5; j++) {
      var black = start + 12 * octave + blacks[j];
      rect(4 + (octave * 7 + blackOffsets[j]) * keyWidth, top, keyWidth * 0.7, keyHeight * 0.62,
           lit[black] ? T.mint : T.keyBlack);
    }
  }
}
// ---- end of the kit's chord display -------------------------------------------------------------------------------

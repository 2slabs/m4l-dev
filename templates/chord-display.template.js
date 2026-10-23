// ---- the 2sl-dsp kit's chord display (templates/chord-display.template.js; architecture/chord-block.md) ---------
// What the chord block sounds: the kit's heading, the device's label with the notes as its reading (or, in orange,
// the In key notice across the top line); below, the chord's name large; then two octaves of keys from the C at or
// below the lowest note, the sounding ones lit. Drawn with the kit's views helpers. The device's views code passes every message to
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
  var below = HEADING_DRAWING_TOP;
  if (chordDisplay.notice) text(chordDisplay.notice, 4, 12, T.warm);        // the notice takes the whole top line
  else below = viewHeading(label, notes, w, T.label);
  if (!pitches.length) text("play a key", 4, below + 18, T.unlit, 2);
  else text(chordDisplay.name, 4, below + 20, T.ink, 2);
  var lit = {};
  for (var i = 0; i < pitches.length; i++) lit[pitches[i]] = 1;
  var lowest = pitches.length ? Math.min.apply(null, pitches) : 48;
  var start = lowest - (lowest % 12);
  var top = below + 28, keyHeight = h - top - 3, whites = [0, 2, 4, 5, 7, 9, 11], blacks = [1, 3, 6, 8, 10];
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

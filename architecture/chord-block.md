# The chord block

What a key plays, shared by every device that plays chords (2sl stab, 2sl gate). User, 2026-10-18: "the chord block
i think is shared code and should be treated as such". It will grow; it grows here.

- **Shapes** (`twosl_dsp/chord_block.py`, `CHORD_SHAPES`): minor, m7, m9, m11, sus4, fifths, dark, each a list of tones
  (degree, semitones above the key, scale steps above the key). The Chord menu is `held notes` and then these;
  a device that can sound one key alone puts `one note` first (`ChordBlock(..., one_note=True)`; 2sl gate: one
  oscillator, the last key wins, where it had a Mono / Chords switch: one choice, one menu). The brain asks
  `chordShapeIsOneNote()` / `chordShapeIsHeldNotes()`; what one note does with several keys is the device's.
  A device says how many notes it can sound for one chord (`most_notes_per_chord`); the build fits each shape to it,
  dropping the fifth, then the ninth, and fails if a shape still doesn't fit. 2sl stab (16 voices) plays them whole;
  2sl gate (4 oscillators) plays m11 as 1 b3 b7 11.
- **In key**: with Live 12's Scale Mode (the Live Set's `root_note` and `scale_intervals`, observed by the block),
  the key snaps down into the scale and the shape's scale steps stack on it. A scale under 5 notes can't: the fixed
  shapes play, the chord display says so in orange, and the Max window logs each change. The notice shows only while
  a shape is chosen (not one note or held notes).
- **Held notes**: the key plays itself. The block tracks the keys held (oldest first, with velocities; a key held
  twice is released by its last note-off) and says when a note-on starts a fresh chord (nothing was held). What the
  device does with several keys is its own: 2sl stab sounds each key's chord, 2sl gate gives its four oscillators
  the keys (or the newest key's shape).
- **Names**: `chordName(pitches)`: the root is the note with a third and a fifth above it (the lowest wins a tie);
  m, m7, m9, m11, madd9, dim, m7b5, maj7, maj9, 7, 9, add9, sus2, sus4, 7sus4, 5, slash bass; one pitch is its note
  and octave (C3 = MIDI 60, Live's); octaves of one note are the note.
- **Drift**: `chordDrifted(pitches, drift)`: with chance `drift` (a draw of the seeded random), another voicing
  (invert, drop the top, spread the middle, add the octave, chosen by another draw). So the block needs the
  device's `SeededRandom`.
- **The display** (`templates/chord-display.template.js`): the kit's heading (`viewHeading`: the device's label,
  the notes as its reading) or the In key notice, the name large, two octaves of keys lit.
- **The device's part**: make a view for the display and the `ChordBlock`; place `chord_menu` and `in_key_toggle`
  (named as Live already knows them); `/*CHORD_BLOCK*/` in the brain (after the seeded random's code), every
  control message through `chordBlockMessage`; `/*CHORD_DISPLAY*/` in the views, `chordDisplayMessage` first in
  `deviceMessage`, the painter `chordDisplayView(w, h, label)`. Its Info text for the two controls and the view is
  the device's (what they do differs: 2sl gate's apply in Chords only).

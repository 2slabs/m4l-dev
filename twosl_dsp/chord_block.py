"""ChordBlock: chord memory for a device's brain, its Chord and In key controls, and its display
(architecture/chord-block.md).

A key plays a stored chord shape stacked on it (fixed intervals, or Live 12's Scale Mode with In key), or with
"held notes" just itself; the brain tracks the keys held, names what sounds, varies voicings (Drift, from the kit's
seeded random), and tells the chord display (templates/chord-block.template.js, chord-display.template.js).

    chords = ChordBlock(patch, seeded_random, brain, brain_control_inlet, brain_display_outlet, display_box,
                        most_notes_per_chord, one_note=False)
    chords.chord_menu(name, short, x, y, w, page)         # a live.menu of chords.menu_items
    chords.in_key_toggle(name, short, x, y, w, h, page)   # a live.text
    chords.brain_code()       # fills the device brain's /*CHORD_BLOCK*/ (after both controls)
    ChordBlock.display_code() # fills the device views' /*CHORD_DISPLAY*/

The device names its two controls (Live knows them by those names: 2sl stab "Chord" / "In Key", 2sl gate "Chord" /
"In key") and their Info text; the kit owns the shapes and their item names.
"""
import json

from twosl_dsp.build_error import BuildError
from twosl_dsp.generated_scripts import fill_template, kit_template_text
from twosl_dsp.seeded_random import SeededRandom

HELD_NOTES = "held notes"
# A device with one oscillator for a key (2sl gate) can offer "one note" first: the last key wins, nothing stacked.
ONE_NOTE = "one note"
# The stored shapes: (Chord item, its tones as (degree, semitones above the key, scale steps above the key for In
# key)). A minor triad is the dub stab (2sl stab's README, "Sources"); "dark" is Attack's +5 +8 variant.
CHORD_SHAPES = [
    ("minor", [("1", 0, 0), ("b3", 3, 2), ("5", 7, 4)]),
    ("m7", [("1", 0, 0), ("b3", 3, 2), ("5", 7, 4), ("b7", 10, 6)]),
    ("m9", [("1", 0, 0), ("b3", 3, 2), ("b7", 10, 6), ("9", 14, 8)]),
    ("m11", [("1", 0, 0), ("b3", 3, 2), ("5", 7, 4), ("b7", 10, 6), ("9", 14, 8), ("11", 17, 10)]),
    ("sus4", [("1", 0, 0), ("4", 5, 3), ("5", 7, 4), ("8", 12, 7)]),
    ("fifths", [("1", 0, 0), ("5", 7, 4), ("8", 12, 7)]),
    ("dark", [("1", 0, 0), ("4", 5, 3), ("b6", 8, 5)]),
]
CHORD_SHAPE_NAMES = [HELD_NOTES] + [name for name, _ in CHORD_SHAPES]


def chord_menu_items(one_note):
    """The Chord menu's items: ("one note",) "held notes", then the shapes."""
    return ([ONE_NOTE] if one_note else []) + CHORD_SHAPE_NAMES
# A device that sounds fewer notes than a shape has drops these degrees, in this order: the fifth first, then the
# ninth (the root, third, seventh and the shape's top extension carry the chord). 2sl gate's 4 oscillators play m11
# as 1 b3 b7 11.
DROPPED_FIRST = ["5", "9"]


def fitted_shapes(most_notes_per_chord):
    """Each shape's tones fitted to `most_notes_per_chord`: [(name, [(degree, semitones, steps)])]. Fails when a shape
    can't fit."""
    fitted = []
    for name, tones in CHORD_SHAPES:
        kept = list(tones)
        for degree in DROPPED_FIRST:
            if len(kept) <= most_notes_per_chord:
                break
            kept = [tone for tone in kept if tone[0] != degree]
        if len(kept) > most_notes_per_chord:
            raise BuildError(f"the chord shape {name!r} needs {len(kept)} notes after dropping {DROPPED_FIRST}; the "
                             f"device sounds {most_notes_per_chord} for a chord")
        fitted.append((name, kept))
    return fitted


class ChordBlock:
    def __init__(self, patch, seeded_random, brain, brain_control_inlet, brain_display_outlet, display_box,
                 most_notes_per_chord, one_note=False):
        """The chord block in `brain` (a js box), its controls told to `brain_control_inlet`, the display
        `display_box` (a view the device made) told from `brain_display_outlet`. `most_notes_per_chord`: how many
        notes the device can sound for one key's chord (2sl stab 16 voices, 2sl gate 4 oscillators). Drift draws from
        `seeded_random` (the device's SeededRandom), so the block needs one. `one_note`: the Chord menu starts with
        "one note" (the key alone, the last key held winning: chordShapeIsOneNote() in the brain)."""
        if not isinstance(seeded_random, SeededRandom):
            patch.fail("the chord block draws its voicings from the kit's seeded random: pass the device's SeededRandom")
        self.patch, self.brain, self.brain_control_inlet = patch, brain, brain_control_inlet
        self.brain_display_outlet = brain_display_outlet
        self.shapes = fitted_shapes(most_notes_per_chord)
        self.one_note = bool(one_note)
        self.menu_items = chord_menu_items(self.one_note)
        self.chord_menu_name = self.in_key_toggle_name = None
        patch.wire(brain, display_box, brain_display_outlet, 0)
        for property_name, message in (("root_note", "scale_root"), ("scale_intervals", "scale_intervals")):
            to_brain = patch.box(f"prepend {message}", rect=(620, 180 + 30 * len(message), 130, 22))
            patch.wire(patch.live_set_observer(property_name), to_brain)
            patch.wire(to_brain, brain, 0, brain_control_inlet)

    def chord_menu(self, name, short, x, y, w, page, group=None):
        """The Chord menu; its neutral (a double-click) is "held notes": the keys as played, nothing stacked."""
        box_id = self.patch.menu(name, short, self.menu_items, x, y, w, page, group=group,
                                 kit_neutral=self.menu_items.index(HELD_NOTES))
        self.patch.tell(box_id, "chord_shape", self.brain, self.brain_control_inlet)
        self.chord_menu_name = name
        return box_id

    def in_key_toggle(self, name, short, x, y, w, h, page, group=None):
        """The In key toggle; its neutral (a double-click) is off: fixed intervals, Live's scale not followed."""
        box_id = self.patch.toggle(name, short, x, y, w, h, page, group=group, kit_neutral=0)
        self.patch.tell(box_id, "chord_in_key", self.brain, self.brain_control_inlet)
        self.in_key_toggle_name = name
        return box_id

    def brain_code(self):
        """The chord block for the device's brain, starting where the Init values put Chord and In key."""
        if self.chord_menu_name is None or self.in_key_toggle_name is None:
            raise BuildError(f"{self.patch.device_name}: the chord block's brain code needs its controls first "
                             "(chord_menu, in_key_toggle)")
        unstacked = [None] * (len(self.menu_items) - len(self.shapes))     # one note, held notes: the key itself
        return fill_template(kit_template_text("chord-block.template.js"), {
            "CHORD_SHAPES": json.dumps(unstacked + [[semitones for _, semitones, _ in tones] for _, tones in self.shapes]),
            "CHORD_SHAPE_STEPS": json.dumps(unstacked + [[steps for _, _, steps in tones] for _, tones in self.shapes]),
            "CHORD_ONE_NOTE_ITEM": str(self.menu_items.index(ONE_NOTE) if self.one_note else -1),
            "CHORD_DISPLAY_OUTLET": str(self.brain_display_outlet),
            "INITIAL_CHORD_SHAPE": str(self.patch.initial_values[self.chord_menu_name]),
            "INITIAL_CHORD_IN_KEY": str(self.patch.initial_values[self.in_key_toggle_name])},
            "the kit's chord block template").strip()

    @staticmethod
    def display_code():
        return kit_template_text("chord-display.template.js").strip()

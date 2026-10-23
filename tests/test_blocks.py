"""The kit's blocks as a device build uses them (twosl_dsp/chord_block.py, seeded_random.py): the chord shapes fitted
to a device's notes, the blocks' order and dependency rules. Builds small patches in memory; writes nothing. Their
scripts run in node in tests/kit-scripts.test.js (on the fixture device)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import chord_block  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.chord_block import ChordBlock  # noqa: E402
from twosl_dsp.seeded_random import SeededRandom  # noqa: E402
from test_patch_builder import builder, preset_book  # noqa: E402


def semitones(fitted):
    return [[s for _, s, _ in tones] for _, tones in fitted]


def steps(fitted):
    return [[st for _, _, st in tones] for _, tones in fitted]


class ChordShapeTests(unittest.TestCase):
    def test_a_device_with_room_plays_every_shape_whole(self):
        # 2sl stab 2.0.1's shapes (its brain's SHAPES / STEPS), which had the room
        fitted = chord_block.fitted_shapes(16)
        self.assertEqual(semitones(fitted), [[0, 3, 7], [0, 3, 7, 10], [0, 3, 10, 14], [0, 3, 7, 10, 14, 17],
                                             [0, 5, 7, 12], [0, 7, 12], [0, 5, 8]])
        self.assertEqual(steps(fitted), [[0, 2, 4], [0, 2, 4, 6], [0, 2, 6, 8], [0, 2, 4, 6, 8, 10], [0, 3, 4, 7],
                                         [0, 4, 7], [0, 3, 5]])

    def test_four_notes_drop_the_fifth_then_the_ninth(self):
        # 2sl gate 0.3.0's 4-note shapes
        fitted = chord_block.fitted_shapes(4)
        self.assertEqual(semitones(fitted)[3], [0, 3, 10, 17])
        self.assertEqual(steps(fitted)[3], [0, 2, 6, 10])
        self.assertEqual(semitones(fitted)[:3], [[0, 3, 7], [0, 3, 7, 10], [0, 3, 10, 14]])

    def test_too_few_notes_fail(self):
        with self.assertRaisesRegex(BuildError, "m7"):
            chord_block.fitted_shapes(2)

    def test_the_menu_items_are_held_notes_then_the_shapes(self):
        self.assertEqual(chord_block.CHORD_SHAPE_NAMES,
                         ["held notes", "minor", "m7", "m9", "m11", "sus4", "fifths", "dark"])
        self.assertEqual(chord_block.chord_menu_items(True), ["one note"] + chord_block.CHORD_SHAPE_NAMES)


def block_patch():
    patch = builder(book=preset_book(init={"Volume": 0, "Chord": "minor", "In key": "off", "Seed": 0,
                                           "Loop": "16 bars"}))
    patch.info.update({"Chord": ("Chord", "t"), "In key": ("In key", "t"), "Chord view": ("Chord", "t")})
    brain = patch.box("js t.js", ins=2, outs=2)
    view = patch.view("chord", 12, 28, 184, 64, "one", info="Chord view")
    return patch, brain, view


class BlockRuleTests(unittest.TestCase):
    def test_the_chord_block_needs_the_seeded_random(self):
        patch, brain, view = block_patch()
        with self.assertRaisesRegex(BuildError, "seeded random"):
            ChordBlock(patch, None, brain, 1, 1, view, 4)

    def test_brain_code_needs_the_controls_first(self):
        patch, brain, view = block_patch()
        random = SeededRandom(patch, brain, 1)
        with self.assertRaisesRegex(BuildError, "seed_control"):
            random.brain_code()
        chords = ChordBlock(patch, random, brain, 1, 1, view, 4)
        with self.assertRaisesRegex(BuildError, "chord_menu"):
            chords.brain_code()
        random.seed_control(12, 98, 40, "one")
        random.loop_control(56, 98, 56, "one")
        chords.chord_menu("Chord", "Chord", 12, 119, 80, "one")
        chords.in_key_toggle("In key", "In key", 96, 119, 52, 15, "one")
        self.assertIn("var chordShape = 1, chordInKey = 0;", chords.brain_code())
        self.assertIn("var randomLoopBars = RANDOM_LOOP_BARS[5];", random.brain_code())
        self.assertNotIn("/*", random.brain_code().replace("/**", ""))

    def test_the_kit_names_seed_and_loop(self):
        patch, brain, _ = block_patch()
        patch.info["Seed"] = ("Seed", "the device's own")
        with self.assertRaisesRegex(BuildError, "leave it to the kit"):
            SeededRandom(patch, brain, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

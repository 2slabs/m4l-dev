"""The kit's preset-loudness harness (m4l_dev/preset_loudness.py): the phrase, and the comparison against Init."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m4l_dev import preset_loudness  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402


class PhraseTests(unittest.TestCase):
    def test_the_mono_phrase_is_six_16ths_each_let_go(self):
        events = preset_loudness.mono_phrase()
        self.assertEqual([pitches for _, pitches in events if pitches], [[36], [43], [48], [51], [55], [60]])
        self.assertEqual(events[:2], [(0.0, [36]), (0.1, None)])

    def test_a_chord_phrase_plays_the_shape_on_each_root(self):
        events = preset_loudness.chord_phrase("held notes", 4)
        self.assertEqual(events[0], (0.0, [48 + s for s in preset_loudness.CHORD_SEMITONES["m7"]]))
        self.assertEqual(len([e for e in events if e[1]]), 3)

    def test_a_chord_with_more_notes_than_the_device_plays_fails(self):
        with self.assertRaisesRegex(BuildError, "dropped degrees"):
            preset_loudness.chord_phrase("m11", 4)
        with self.assertRaisesRegex(BuildError, "no chord shape"):
            preset_loudness.chord_phrase("nope", 4)

    def test_presets_off_init_names_only_those_outside_the_tolerance(self):
        self.assertEqual(preset_loudness.presets_off_init({"init": -20, "a": -19, "b": -22.5}, "init"), {"b": -2.5})


if __name__ == "__main__":
    unittest.main()

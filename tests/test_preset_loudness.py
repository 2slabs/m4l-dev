"""The kit's preset-loudness harness (twosl_dsp/preset_loudness.py): the phrase, and the comparison against Init."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import bs1770, preset_loudness  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.render_comparison import assert_renders_similar  # noqa: E402


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
        self.assertEqual(preset_loudness.presets_off_init({"init": -20, "a": -19.2, "b": -21.5}, "init"), {"b": -1.5})

    def test_presets_over_the_clip_allow_the_fast_rates_peak_error_only_at_the_fast_rate(self):
        peaks = {"init": -6.0, "a": -1.8, "b": -1.5}
        self.assertEqual(preset_loudness.presets_over_the_clip(peaks, -1.94, preset_loudness.FAST_SAMPLE_RATE),
                         {"b": -1.5})
        self.assertEqual(preset_loudness.presets_over_the_clip(peaks, -1.94, preset_loudness.SAMPLE_RATE),
                         {"a": -1.8, "b": -1.5})

    def test_a_preset_is_measured_by_its_loudest_moment(self):
        # a 100 ms ping and the same tone held for 1 s: the same peak; the held tone fills the loudest 400 ms window,
        # the ping a quarter of it, so 6 dB apart
        rate = preset_loudness.FAST_SAMPLE_RATE
        tone = [0.5 * math.sin(2 * math.pi * 997 * n / rate) for n in range(rate)]
        ping = tone[:rate // 10] + [0.0] * (rate - rate // 10)
        held_loudness, held_peak = preset_loudness.phrase_measures([tone, tone], rate)
        ping_loudness, ping_peak = preset_loudness.phrase_measures([ping, ping], rate)
        self.assertAlmostEqual(held_peak, ping_peak, places=6)
        self.assertAlmostEqual(held_loudness - ping_loudness, 10 * math.log10(4), delta=0.1)

    def test_oscillator_start_phases_are_unrelated_and_repeat(self):
        first, again = preset_loudness.oscillator_start_phases(), preset_loudness.oscillator_start_phases()
        phases = [next(first) for _ in range(32)]
        self.assertEqual(phases, [next(again) for _ in range(32)])
        self.assertTrue(all(0 <= phase < 1 for phase in phases))
        self.assertGreater(len({round(phase, 3) for phase in phases}), 30)



def identity_render(messages, mono, rate):
    """An effect that passes its input, times messages["gain"]: the effect mode's stand-in device."""
    return [value * messages["gain"] for value in mono], [value * messages["gain"] for value in mono]


class EffectTests(unittest.TestCase):
    # the mechanics at the fast rate (the inputs are made at any rate; a device levels at EFFECT_SAMPLE_RATE)
    rate = preset_loudness.FAST_SAMPLE_RATE

    def test_the_effect_inputs_are_eight_seconds_at_minus_18_lufs_and_repeat(self):
        rate = self.rate
        inputs = preset_loudness.effect_inputs(rate)
        self.assertEqual(tuple(inputs), ("drums", "bass", "pad", "full mix", "chords and kick"))
        for name, mono in inputs.items():
            with self.subTest(input=name):
                self.assertEqual(len(mono), int(preset_loudness.EFFECT_INPUT_SECONDS * rate))
                self.assertAlmostEqual(bs1770.integrated_loudness([list(mono)] * 2, rate), -18.0, places=6)
                self.assertLess(bs1770.sample_peak_db([list(mono)]), -1.0)
        preset_loudness.effect_inputs.cache_clear()
        again = preset_loudness.effect_inputs(rate)
        self.assertEqual(tuple(again), tuple(inputs))
        for name, mono in inputs.items():
            assert_renders_similar(list(mono), list(again[name]), rate, f"{name} made again")

    def test_the_effect_inputs_can_be_shorter_and_fewer_without_changing_the_rest(self):
        full = preset_loudness.effect_inputs(self.rate)
        short = preset_loudness.effect_inputs(self.rate, 2.0, ("full mix", "chords and kick"))
        self.assertEqual(tuple(short), ("full mix", "chords and kick"))
        for name, mono in short.items():
            with self.subTest(input=name):
                self.assertEqual(len(mono), int(2.0 * self.rate))
                self.assertAlmostEqual(bs1770.integrated_loudness([list(mono)] * 2, self.rate), -18.0, places=6)
        fewer = preset_loudness.effect_inputs(self.rate, 8.0, ("pad", "drums"))
        self.assertEqual(tuple(fewer), ("pad", "drums"))
        for name, mono in fewer.items():
            assert_renders_similar(list(full[name]), list(mono), self.rate, f"{name} made with fewer")

    def test_a_short_chords_and_kick_is_the_start_of_the_long_one(self):
        # every beat's kick is there however short the input (a loop variable once shadowed the length)
        short = preset_loudness._chords_and_kick(self.rate, 2.0)
        long = preset_loudness._chords_and_kick(self.rate, 8.0)
        assert_renders_similar(list(long[:len(short)]), list(short), self.rate, "the short chords and kick")

    def test_a_bad_input_choice_fails(self):
        with self.assertRaisesRegex(BuildError, "unknown: \\['kazoo'\\]"):
            preset_loudness.effect_inputs(self.rate, 2.0, ("kazoo",))
        with self.assertRaisesRegex(BuildError, "non-empty"):
            preset_loudness.effect_inputs(self.rate, 2.0, ())
        with self.assertRaisesRegex(BuildError, "longer than 0"):
            preset_loudness.effect_inputs(self.rate, 0.0, ("pad",))

    def test_measures_follow_the_asked_inputs(self):
        names = ("full mix", "chords and kick")
        single = preset_loudness.effect_measures(identity_render, {"gain": 0.5}, self.rate, 2.0, names)
        self.assertEqual(tuple(single.gain_db_by_input), names)
        by_preset = preset_loudness.effect_measures_by_preset(identity_render, {"half": {"gain": 0.5}}, self.rate,
                                                              2.0, names)
        self.assertEqual(tuple(by_preset["half"].gain_db_by_input), names)
        self.assertAlmostEqual(by_preset["half"].median_gain_db, 20 * math.log10(0.5), places=6)

    def test_an_effect_is_measured_by_its_median_gain_against_bypass(self):
        bypass = preset_loudness.effect_measures(identity_render, {"gain": 1.0}, self.rate)
        self.assertAlmostEqual(bypass.median_gain_db, 0.0, places=9)
        self.assertAlmostEqual(bypass.worst_miss_db, 0.0, places=9)
        halved = preset_loudness.effect_measures(identity_render, {"gain": 0.5}, self.rate)
        self.assertAlmostEqual(halved.median_gain_db, 20 * math.log10(0.5), places=6)
        self.assertEqual(preset_loudness.presets_off_bypass({"bypass": bypass, "halved": halved}),
                         {"halved": -6.02})

    def test_the_median_and_the_worst_miss(self):
        measures = preset_loudness.EffectMeasures({"a": -1.0, "b": 0.5, "c": 3.0}, {"a": -6.0, "b": -7.0, "c": -2.0},
                                                  {"a": -5.0, "b": -7.0, "c": -4.0})
        self.assertEqual((measures.median_gain_db, measures.worst_miss_db, measures.peak_db), (0.5, 2.5, -2.0))

    def test_gains_peaks_and_dry_peaks_name_the_same_inputs(self):
        with self.assertRaisesRegex(BuildError, "same inputs"):
            preset_loudness.EffectMeasures({"a": 0.0}, {"a": -6.0, "b": -6.0}, {"a": -6.0})

    def test_an_effects_peaks_are_its_own_and_the_dry_inputs(self):
        names = ("drums", "pad")
        measures = preset_loudness.effect_measures(identity_render, {"gain": 0.5}, self.rate, 2.0, names)
        for name, mono in preset_loudness.effect_inputs(self.rate, 2.0, names).items():
            dry_peak = bs1770.sample_peak_db([list(mono), list(mono)])
            self.assertAlmostEqual(measures.dry_peak_db_by_input[name], dry_peak, places=9)
            self.assertAlmostEqual(measures.peak_db_by_input[name], dry_peak + 20 * math.log10(0.5), places=6)

    def test_an_effect_fails_the_peak_rule_only_when_its_level_drives_the_clip(self):
        knee = -0.45
        dry = {"drums": -1.4, "pad": -8.0, "bass": -7.0}
        measures = {
            # under the knee everywhere: passes, whatever its gain
            "clean": preset_loudness.EffectMeasures({"drums": 0.5, "pad": 0.0, "bass": 0.0},
                                                    {"drums": -0.9, "pad": -8.0, "bass": -7.0}, dry),
            # in the clip by the crest factor it adds (the dry at its level, -1.4, stays under): the effect, passes
            "crest": preset_loudness.EffectMeasures({"drums": 0.2, "pad": 0.0, "bass": 0.0},
                                                    {"drums": 0.0, "pad": -5.0, "bass": 0.0}, dry),
            # in the clip on the drums, louder there than its level (+1.7 against a median of -1.2): the effect, passes
            "resonant": preset_loudness.EffectMeasures({"drums": 1.7, "pad": -1.2, "bass": -2.4},
                                                       {"drums": -0.3, "pad": -9.0, "bass": 0.0}, dry),
            # in the clip and its level alone would put the dry there (-1.4 + 1.2 = -0.2): fails on the drums only
            "hot": preset_loudness.EffectMeasures({"drums": 1.2, "pad": 1.2, "bass": 1.0},
                                                  {"drums": 0.0, "pad": -6.0, "bass": 0.0}, dry),
        }
        self.assertEqual(preset_loudness.effect_presets_clipping_beyond_dry(measures, knee),
                         {"hot": {"drums": (0.0, -0.2)}})
        # the fast rate's peak allowance lifts the ceiling for both
        self.assertEqual(preset_loudness.effect_presets_clipping_beyond_dry(measures, knee,
                                                                             preset_loudness.FAST_SAMPLE_RATE), {})

    def test_presets_are_measured_in_worker_processes(self):
        measures = preset_loudness.effect_measures_by_preset(identity_render, {"one": {"gain": 1.0},
                                                                               "two": {"gain": 2.0}}, self.rate)
        self.assertAlmostEqual(measures["two"].median_gain_db - measures["one"].median_gain_db, 20 * math.log10(2))

    def test_a_render_of_the_wrong_shape_fails(self):
        with self.assertRaisesRegex(BuildError, "two channels"):
            preset_loudness.effect_measures(lambda messages, mono, rate: (mono,), {}, self.rate)


if __name__ == "__main__":
    unittest.main()

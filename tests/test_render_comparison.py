"""The kit's render comparator (twosl_dsp/render_comparison.py, architecture/testing.md) on both sides of its limits:
the differences two machines make (the maths library's last bits, a threshold event a sample later: 2sl filter's
isolated -64 dBFS one-sample spikes, macOS on ARM vs Linux on x86) pass; real changes (a 0.1 dB level, a cutoff
moved 1 %, a click, a 1 ms dropout, a sample of delay) fail, each saying its numbers."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import render_comparison  # noqa: E402
from twosl_dsp.render_comparison import assert_renders_similar, renders_are_similar  # noqa: E402

RATE = 48000
SECONDS = 0.5
PROGRAM_LEVEL_DBFS = -21.6     # the quietest of 2sl filter's preset renders the plugin test compares (chords and kick)


def noise(count, seed):
    """Park-Miller noise in [-1, 1): the same numbers everywhere."""
    out = []
    for _ in range(count):
        seed = seed * 16807 % 2147483647
        out.append(seed / 1073741823.5 - 1.0)
    return out


def one_pole_low_pass(signal, cutoff_hz):
    coefficient = math.exp(-2 * math.pi * cutoff_hz / RATE)
    out, state = [], 0.0
    for x in signal:
        state = (1 - coefficient) * x + coefficient * state
        out.append(state)
    return out


def program(cutoff_hz=1000.0):
    """A stand-in for a preset's render: a chord over filtered noise with a decaying kick, at PROGRAM_LEVEL_DBFS."""
    count = int(SECONDS * RATE)
    chord = [sum(math.sin(2 * math.pi * f * n / RATE) for f in (220.0, 277.18, 329.63)) for n in range(count)]
    kick = [math.sin(2 * math.pi * 55 * n / RATE) * math.exp(-n / (0.08 * RATE)) * 3 for n in range(count)]
    filtered = one_pole_low_pass([c + k + 2 * w for c, k, w in zip(chord, kick, noise(count, 271828))], cutoff_hz)
    rms = math.sqrt(sum(x * x for x in filtered) / count)
    gain = 10 ** (PROGRAM_LEVEL_DBFS / 20) / rms
    return [x * gain for x in filtered]


class RenderComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = program()

    def assert_similar(self, candidate):
        return assert_renders_similar(self.reference, candidate, RATE, "a harmless difference")

    def assert_not_similar(self, candidate, what):
        comparison = renders_are_similar(self.reference, candidate, RATE)
        self.assertFalse(comparison.similar, f"{what} passed: {comparison.report()}")
        self.assertIn("NOT SIMILAR", comparison.report())
        return comparison

    # the harmless side

    def test_the_same_render_is_similar_with_no_residual(self):
        comparison = self.assert_similar(list(self.reference))
        self.assertEqual(comparison.residual_db, -math.inf)
        self.assertIn("within tolerance: residual -inf dB", comparison.report())

    def test_last_bit_differences_pass(self):
        # every sample off by a relative 1e-7 (single precision's rounding; a double's last bits are 1e-16)
        wobble = noise(len(self.reference), 31415)
        comparison = self.assert_similar([x * (1 + 1e-7 * w) for x, w in zip(self.reference, wobble)])
        self.assertLess(comparison.residual_db, -140)

    def test_isolated_one_sample_spikes_pass(self):
        # 2sl filter's plugin vs device on macOS / ARM: isolated one-sample spikes up to 5.9e-4 (-64.6 dBFS), a
        # threshold event landing a sample apart; a handful in one render, two of them in one window
        candidate = list(self.reference)
        for at, spike in ((1000, 5.9e-4), (1100, -5.9e-4), (9000, 5.9e-4), (15000, -4e-4), (23000, 5.9e-4)):
            candidate[at] += spike
        comparison = self.assert_similar(candidate)
        # with room: 6 dB under each limit
        self.assertLess(comparison.residual_db, render_comparison.RESIDUAL_LIMIT_DB - 6, comparison.report())
        self.assertLess(comparison.worst_window_residual_db, render_comparison.WINDOW_RESIDUAL_LIMIT_DB - 6,
                        comparison.report())

    def test_stereo_and_silence(self):
        right = [-x for x in self.reference]
        assert_renders_similar([self.reference, right], [self.reference, [x * (1 + 1e-9) for x in right]], RATE)
        assert_renders_similar([0.0] * 1000, [0.0] * 1000, RATE)
        assert_renders_similar([0.0] * 1000, [0.0] * 999 + [1e-9], RATE)     # under the silence floor's tolerance
        self.assertFalse(renders_are_similar([0.0] * 1000, [0.0] * 999 + [1e-3], RATE).similar)

    # the real side

    def test_a_tenth_of_a_db_fails(self):
        gain = 10 ** (0.1 / 20)
        comparison = self.assert_not_similar([x * gain for x in self.reference], "0.1 dB")
        self.assertAlmostEqual(comparison.level_difference_db, 0.1, delta=1e-9)
        self.assertAlmostEqual(comparison.residual_db, 20 * math.log10(gain - 1), delta=1e-6)    # -38.7 dB

    def test_a_cutoff_moved_one_percent_fails(self):
        self.assert_not_similar(program(cutoff_hz=1010.0), "the cutoff 1000 -> 1010 Hz")

    def test_a_click_fails_though_the_whole_render_hardly_moves(self):
        candidate = list(self.reference)
        candidate[12000] += 0.003                                          # one sample, -50 dBFS
        comparison = self.assert_not_similar(candidate, "a one-sample click of 0.003")
        self.assertLess(comparison.residual_db, render_comparison.RESIDUAL_LIMIT_DB, "the whole render passes ...")
        self.assertGreater(comparison.worst_window_residual_db, render_comparison.WINDOW_RESIDUAL_LIMIT_DB,
                           "... its window doesn't")
        self.assertAlmostEqual(comparison.worst_window_start_seconds, 0.25, delta=render_comparison.WINDOW_SECONDS)

    def test_a_dropout_fails(self):
        candidate = list(self.reference)
        candidate[20000:20048] = [0.0] * 48                                # 1 ms
        self.assert_not_similar(candidate, "a 1 ms dropout")

    def test_a_sample_of_delay_fails(self):
        self.assert_not_similar([0.0] + self.reference[:-1], "one sample late")

    def test_unmeasurable_renders_fail_loudly(self):
        for candidate, says in ((self.reference[:-1], "samples, the reference has"),
                                ([self.reference, self.reference], "channels"),
                                (self.reference[:-1] + [math.nan], "holds nan")):
            comparison = renders_are_similar(self.reference, candidate, RATE)
            self.assertFalse(comparison.similar)
            self.assertIn(says, comparison.report())
        with self.assertRaisesRegex(AssertionError, "the plugin: NOT SIMILAR"):
            assert_renders_similar(self.reference, [x * 2 for x in self.reference], RATE, "the plugin")


if __name__ == "__main__":
    unittest.main()

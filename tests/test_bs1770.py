"""The kit's ITU-R BS.1770-5 meter (twosl_dsp/bs1770.py, references/itu-r-bs1770.md, references/ebu-tech-3341.md): the
K-weighting at other rates is the standard's 48 kHz response, and the loudness reads what the standards say a known
signal reads."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import bs1770  # noqa: E402
from twosl_dsp.preset_loudness import FAST_SAMPLE_RATE, SAMPLE_RATE  # noqa: E402


class MeterTests(unittest.TestCase):
    def test_the_k_weighting_is_the_standards(self):
        standard = bs1770.k_weighting_stages(bs1770.STANDARD_RATE)
        for rate, within_db in ((SAMPLE_RATE, 0.01), (FAST_SAMPLE_RATE, 0.3)):
            stages = bs1770.k_weighting_stages(rate)
            frequency = 10.0
            while frequency < 0.4 * rate:
                ours = sum(bs1770.biquad_response_db(b, a, frequency, rate) for b, a in stages)
                theirs = sum(bs1770.biquad_response_db(b, a, frequency, bs1770.STANDARD_RATE) for b, a in standard)
                self.assertAlmostEqual(ours, theirs, delta=within_db, msg=f"{frequency:.0f} Hz at {rate} Hz")
                frequency *= 1.05

    def test_a_full_scale_997_hz_sine_in_one_channel_reads_minus_3_lkfs(self):
        # BS.1770-5 NOTE 1 to equation 2: -0.691 cancels the K-weighting's gain at 997 Hz; a 0 dBFS sine's mean
        # square is 1/2
        sine = [math.sin(2 * math.pi * 997 * n / SAMPLE_RATE) for n in range(SAMPLE_RATE)]
        self.assertAlmostEqual(bs1770.integrated_loudness([sine], SAMPLE_RATE), -3.01, delta=0.01)

    def test_silence_and_a_short_signal_fail_loudly(self):
        with self.assertRaisesRegex(ValueError, "silence"):
            bs1770.integrated_loudness([[0.0] * SAMPLE_RATE], SAMPLE_RATE)
        with self.assertRaisesRegex(ValueError, "400 ms"):
            bs1770.integrated_loudness([[0.1] * 100], SAMPLE_RATE)

    def test_the_loudest_moment_is_ebu_tech_3341_case_13(self):
        # file-based: i x 20 ms of silence, 400 ms of a 1 kHz sine at -23 dBFS per channel in both, 1 s of silence:
        # Max M = -23.0 +-0.1 LUFS for each segment, so the window slides over every start (a few of the 20 here)
        rate = bs1770.STANDARD_RATE
        amplitude = 10 ** (-23 / 20)
        tone = [amplitude * math.sin(2 * math.pi * 1000 * n / rate) for n in range(int(0.4 * rate))]
        for i in (0, 1, 7, 19):
            segment = [0.0] * int(i * 0.02 * rate) + tone + [0.0] * rate
            self.assertAlmostEqual(bs1770.max_momentary_loudness([segment, segment], rate), -23.0, delta=0.1, msg=i)

    def test_the_momentary_loudness_is_ebu_tech_3341_case_12(self):
        # 0.18 s at -20 dBFS, 0.22 s at -30 dBFS, repeated: M = -23.0 +-0.1 LUFS, constant after 1 s, so its maximum is
        # -23 too (here at 44.1 kHz, the rate presets are levelled at, over 3 repeats)
        rate = SAMPLE_RATE
        signal = [10 ** ((-20 if (n % int(0.4 * rate)) < int(0.18 * rate) else -30) / 20)
                  * math.sin(2 * math.pi * 1000 * n / rate) for n in range(int(1.2 * rate))]
        self.assertAlmostEqual(bs1770.max_momentary_loudness([signal, signal], rate), -23.0, delta=0.1)

    def test_the_momentary_loudness_fails_loudly_on_silence_and_a_short_signal(self):
        with self.assertRaisesRegex(ValueError, "silent"):
            bs1770.max_momentary_loudness([[0.0] * SAMPLE_RATE], SAMPLE_RATE)
        with self.assertRaisesRegex(ValueError, "400 ms"):
            bs1770.max_momentary_loudness([[0.1] * 100], SAMPLE_RATE)

    def test_the_true_peak_finds_the_peak_between_samples(self):
        # a sine at a quarter of the rate, sampled 45 degrees off its peaks: every sample at 0.707, the wave at 1
        samples = [math.sin(2 * math.pi * n / 4 + math.pi / 4) for n in range(400)]
        self.assertAlmostEqual(bs1770.sample_peak_db([samples]), -3.01, delta=0.01)
        self.assertGreater(bs1770.true_peak_db([samples]), -0.7)


if __name__ == "__main__":
    unittest.main()

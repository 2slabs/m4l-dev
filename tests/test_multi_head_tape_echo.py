"""The multi-head tape echo's promises (twosl_dsp/techniques/multi_head_tape_echo.py), one test each."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_block_harness import fft, harness  # noqa: E402
from twosl_dsp.techniques.multi_head_tape_echo import MultiHeadTapeEcho, MultiHeadTapeEchoTapeWriter  # noqa: E402

RATE = 44100.0
OUTPUTS = ["echo_left", "echo_right", "echo_speed", "echo_loop_samples"]


def program(**params):
    echo = MultiHeadTapeEcho("echo", left_input="in1", right_input="in1", time_ms="time", head_1="head1",
                             head_2="head2", heard_1="h1", heard_2="h2", heard_3="h3", feedback="feedback",
                             saturation_gain="saturation", tape="tape", tone="tone", wow="wow", hiss="hiss",
                             stereo_mode="mode", stop_pressed="stop > 0", insert_delay_samples="0",
                             longest_time_ms=2000.0, right_lag_ms=10.0, rounds_kept=3)
    writer = MultiHeadTapeEchoTapeWriter(echo, left="echo_left_into_tape", right="echo_right_into_tape")
    defaults = {"time": 300.0, "head1": 1 / 3, "head2": 2 / 3, "h1": 0.0, "h2": 0.0, "h3": 1.0, "feedback": 0.5,
                "saturation": 1.0, "tape": 0.0, "tone": 0.0, "wow": 0.0, "hiss": 0.0, "mode": 0.0, "stop": 0.0}
    defaults.update(params)
    return harness([echo, writer], defaults, OUTPUTS, samplerate=RATE)


def click(seconds, at=0.01):
    signal = [0.0] * int(seconds * RATE)
    signal[int(at * RATE)] = 1.0
    return signal


def peaks(signal, threshold):
    """Local maxima of |signal| over threshold, as seconds."""
    a = [abs(v) for v in signal]
    return [i / RATE for i in range(1, len(a) - 1) if a[i] > threshold and a[i] >= a[i - 1] and a[i] > a[i + 1]]


def band_share_db(segment, low_hz, high_hz):
    n = 1 << int(math.ceil(math.log2(len(segment))))
    spectrum = fft(segment + [0.0] * (n - len(segment)))
    power = [abs(spectrum[k]) ** 2 for k in range(n // 2)]
    band = sum(power[int(low_hz * n / RATE):int(high_hz * n / RATE)])
    return 10 * math.log10(band / sum(power) + 1e-30)


def rms(signal, a, b):
    seg = signal[int(a * RATE):int(b * RATE)]
    return math.sqrt(sum(v * v for v in seg) / len(seg))


class MultiHeadTapeEchoTests(unittest.TestCase):
    def test_every_repeat_of_every_head_lands_on_the_grid(self):
        # clean, heads 2 + 3 at 1/3 and 2/3 of 300 ms: repeats at multiples of 100 ms from 200 ms (references/
        # multihead.md §3: 2u, 3u, 4u, 5u, 6u ...)
        left = program(h2=1.0, h3=1.0, feedback=0.6).run(int(0.75 * RATE), [click(0.75)])[0]
        found = peaks(left, 0.02)
        for k in (2, 3, 4, 5, 6):
            nearest = min(found, key=lambda t: abs(t - (0.01 + k * 0.1)))
            self.assertLess(abs(nearest - (0.01 + k * 0.1)) * RATE, 1.5, (k, nearest))
        self.assertFalse(any(abs(t - 0.11) < 0.005 for t in found), "head 1 is not heard")

    def test_on_tape_the_repeats_stay_on_the_grid_through_the_losses(self):
        left = program(tape=1.0, feedback=0.7, time=375.0).run(int(1.3 * RATE), [click(1.3)])[0]
        for k in (1, 2, 3):
            centre = 0.01 + k * 0.375
            seg = left[int((centre - 0.02) * RATE):int((centre + 0.02) * RATE)]
            centroid = sum(i * v * v for i, v in enumerate(seg)) / sum(v * v for v in seg) / RATE + centre - 0.02
            self.assertLess(abs(centroid - centre) * 1000, 0.6, (k, centroid))

    def test_dub_howls_at_the_same_feedback_on_every_head_set(self):
        for heads in ({"h3": 1.0}, {"h2": 1.0, "h3": 1.0}, {"h1": 1.0, "h2": 1.0, "h3": 1.0}):
            levels = {}
            for feedback in (0.9, 1.1):
                out = program(feedback=feedback, saturation=1.0, time=200.0, **heads).run(int(3.0 * RATE), [click(3.0)])[0]
                levels[feedback] = (rms(out, 1.0, 1.6), rms(out, 2.2, 2.8))
            self.assertLess(levels[0.9][1], levels[0.9][0] * 0.5, heads)        # under 1: it dies away
            self.assertGreater(levels[1.1][1], levels[1.1][0] * 0.9, heads)     # over 1: it holds (the howl)

    def test_a_longer_time_is_slower_tape_and_darker_repeats(self):
        shares = {}
        for time in (200.0, 800.0):
            out = program(tape=1.0, feedback=0.8, time=time).run(int((0.05 + 3 * time / 1000) * RATE), [click(3.0)])
            speed = out[2][-1]
            second = out[0][int((0.01 + 2 * time / 1000 - 0.01) * RATE):int((0.01 + 2 * time / 1000 + 0.03) * RATE)]
            shares[time] = (speed, band_share_db(second, 3000, 15000))
        self.assertGreater(shares[200.0][0], 3 * shares[800.0][0])
        self.assertLess(shares[800.0][1], shares[200.0][1] - 6, shares)

    def test_tone_left_is_darker_right_is_thinner(self):
        def round_two(tone):
            out = program(tape=1.0, feedback=0.8, time=375.0, tone=tone).run(int(0.9 * RATE), [click(0.9)])[0]
            return out[int(0.75 * RATE):int(0.80 * RATE)]
        neutral, dark, thin = round_two(0.0), round_two(-1.0), round_two(1.0)
        self.assertLess(band_share_db(dark, 3000, 15000), band_share_db(neutral, 3000, 15000) - 6)
        self.assertLess(band_share_db(thin, 20, 200), band_share_db(neutral, 20, 200) - 6)

    def test_clean_repeats_are_the_same_sound_round_after_round(self):
        # a noise burst: each round's share above 3 kHz within a dB of the first's (the reads between samples cost a
        # little top: the spline's, not a filter's)
        import random
        draw = random.Random(7)
        burst = [0.0] * int(0.01 * RATE) + [draw.uniform(-0.3, 0.3) for _ in range(int(0.02 * RATE))]
        burst += [0.0] * (int(1.0 * RATE) - len(burst))
        out = program(feedback=0.7).run(len(burst), [burst])[0]
        shares = [band_share_db(out[int((0.01 + k * 0.3) * RATE):int((0.03 + k * 0.3) * RATE)], 3000, 15000) for k in (1, 2, 3)]
        self.assertLess(max(shares) - min(shares), 1.0, shares)

    def test_spread_places_head_1_left_head_2_right_head_3_centre(self):
        left, right = program(mode=2.0, h1=1.0, h2=1.0, h3=1.0, feedback=0.0).run(int(0.4 * RATE), [click(0.4)])[:2]
        near = lambda sig, t: max(abs(v) for v in sig[int((t - 0.003) * RATE):int((t + 0.003) * RATE)])
        self.assertGreater(near(left, 0.11), 10 * near(right, 0.11))
        self.assertGreater(near(right, 0.21), 10 * near(left, 0.21))
        self.assertAlmostEqual(near(left, 0.31), near(right, 0.31), delta=0.1 * near(left, 0.31))

    def test_a_change_of_heads_crossfades_without_a_click(self):
        tone = [0.3 * math.sin(2 * math.pi * 220 * i / RATE) for i in range(int(0.5 * RATE))]
        echo = program(feedback=0.5, tape=1.0)
        first = echo.run(len(tone), [tone])[0]
        echo.set_param("h3", 0.0)
        echo.set_param("h2", 1.0)
        after = echo.run(len(tone), [tone])[0]
        steps = [abs(b - a) for a, b in zip(first[-1:] + after, after)]
        typical = max(abs(b - a) for a, b in zip(first[-2000:], first[-1999:]))
        self.assertLess(max(steps), 2 * typical)

    def test_hiss_builds_with_the_feedback(self):
        quiet = [0.0] * int(2.0 * RATE)
        low = rms(program(tape=1.0, hiss=0.001, feedback=0.3).run(len(quiet), [quiet])[0], 1.5, 2.0)
        high = rms(program(tape=1.0, hiss=0.001, feedback=0.95).run(len(quiet), [quiet])[0], 1.5, 2.0)
        self.assertGreater(high, 1.5 * low)
        self.assertGreater(low, 0)


if __name__ == "__main__":
    unittest.main()

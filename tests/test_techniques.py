"""The kit's techniques (m4l_dev/techniques/): each technique's claims, rendered through our GenExpr renderer
(m4l_dev/genexpr.py: ours, not Max's compiler). Each claim runs on a small harness program around one technique
(tests/gen_block_harness.py), at the lowest sample rate that still tests it, so the whole file takes seconds. Standard
library only."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev import es5  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.gen_blocks import gen_code_with_blocks  # noqa: E402
from m4l_dev.genexpr import GenProgram  # noqa: E402
from m4l_dev.techniques.antiderivative_tanh_saturator import AntiderivativeTanhSaturator  # noqa: E402
from m4l_dev.techniques.band_limited_edges import BandLimitedEdges  # noqa: E402
from m4l_dev.techniques.knee_soft_clip import KneeSoftClip  # noqa: E402
from m4l_dev.techniques.tape_style_echo import TapeStyleEcho  # noqa: E402
from m4l_dev.techniques.zero_delay_ladder_filter import (ZeroDelayLadderFilter, response_script_code,  # noqa: E402
                                                         small_signal_magnitude)
from m4l_dev.techniques.zero_delay_state_variable_filter import (ZeroDelayStateVariableFilter,  # noqa: E402
                                                                 ring_time_constant_seconds, small_signal_response)
from gen_block_harness import (amplitude_at, cents, folded, frequency_by_zero_crossings, harness,  # noqa: E402
                               worst_alias_db)


class ZeroDelayLadderFilterTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def ladder(self):
        return harness([ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="cutoff", resonance="resonance")],
                       {"cutoff": 1000.0, "resonance": 0.0}, ["ladder_out"], samplerate=self.SAMPLERATE)

    def ring(self, cutoff, resonance, samples=8820):
        program = self.ladder()
        program.set_param("cutoff", cutoff)
        program.set_param("resonance", resonance)
        kick = [0.5] * 20 + [0.0] * (samples - 20)
        return program.run(samples, [kick])[0]

    def test_it_sings_at_the_cutoff_from_resonance_092(self):
        for resonance in (0.95, 1.0):
            for cutoff in (300.0, 3000.0, 12000.0):
                tail = self.ring(cutoff, resonance)[4410:]
                self.assertGreater(max(abs(v) for v in tail[-500:]), 0.02, f"no song at {cutoff} Hz, {resonance}")
                self.assertLess(abs(cents(frequency_by_zero_crossings(tail, self.SAMPLERATE), cutoff)), 3.0,
                                f"{cutoff} Hz, Resonance {resonance}")

    def test_below_092_it_rings_out(self):
        for cutoff in (300.0, 3000.0):
            tail = self.ring(cutoff, 0.88, samples=22050)[-500:]
            self.assertLess(max(abs(v) for v in tail), 1e-3, f"{cutoff} Hz")

    def test_stable_driven_hard_at_the_top_cutoff(self):
        program = self.ladder()
        program.set_param("cutoff", 0.45 * self.SAMPLERATE)
        program.set_param("resonance", 1.0)
        saw = [2.0 * ((i * 220.0 / self.SAMPLERATE) % 1.0) * 2 - 2.0 for i in range(8820)]
        out = program.run(len(saw), [saw])[0]
        self.assertTrue(all(math.isfinite(v) and abs(v) < 4.0 for v in out), max(abs(v) for v in out))

    def test_small_signals_follow_the_response_the_displays_draw(self):
        program = self.ladder()
        program.set_param("cutoff", 2000.0)
        program.set_param("resonance", 0.7)
        for frequency in (200.0, 1500.0, 2000.0, 5000.0):
            sine = [1e-3 * math.sin(2 * math.pi * frequency * i / self.SAMPLERATE) for i in range(6000)]
            out = program.run(len(sine), [sine])[0][2000:]
            measured = amplitude_at(out, frequency, self.SAMPLERATE) / 1e-3
            expected = small_signal_magnitude(frequency, 2000.0, 0.7, self.SAMPLERATE)
            self.assertAlmostEqual(20 * math.log10(measured), 20 * math.log10(expected), delta=0.2, msg=frequency)

    def test_the_display_script_is_the_same_response(self):
        script = response_script_code()
        for frequency, cutoff, resonance in ((100.0, 700.0, 0.3), (700.0, 700.0, 1.0), (15000.0, 30000.0, 0.5)):
            value = float(es5.evaluate(script + f"\nladderResponse({frequency}, {cutoff}, {resonance}, 48000)"))
            self.assertAlmostEqual(value, small_signal_magnitude(frequency, cutoff, resonance, 48000.0), places=9)


class AntiderivativeTanhSaturatorTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def saturate(self, signal, block=True):
        if block:
            program = harness([AntiderivativeTanhSaturator("drive", input="in1")], {}, ["drive_out"])
        else:
            program = GenProgram("out1 = tanh(in1);", 1, 1)
        return program.run(len(signal), [signal])[0]

    def test_it_cuts_the_aliases_of_a_hot_8k_sine(self):
        sine = [2.7 * math.sin(2 * math.pi * 8000.0 * i / self.SAMPLERATE) for i in range(4096)]
        harmonics = range(3, 16, 2)
        naive = worst_alias_db(self.saturate(sine, block=False), 8000.0, harmonics, self.SAMPLERATE, 10000.0)
        antialiased = worst_alias_db(self.saturate(sine), 8000.0, harmonics, self.SAMPLERATE, 10000.0)
        self.assertGreater(naive, -30.0)
        self.assertLess(antialiased, -50.0)

    def test_small_signals_pass_flat(self):
        for frequency in (1000.0, 10000.0, 15000.0):
            sine = [0.01 * math.sin(2 * math.pi * frequency * i / self.SAMPLERATE) for i in range(4096)]
            gain = amplitude_at(self.saturate(sine)[512:], frequency, self.SAMPLERATE) / 0.01
            self.assertAlmostEqual(20 * math.log10(gain), 0.0, delta=0.05, msg=frequency)

    def test_near_equal_samples_are_exact(self):
        signal = [0.5 + 1e-12 * i for i in range(200)] + [3.0] * 50 + [-20.0] * 50
        out = self.saturate(signal)
        for i in range(40, 200):          # after the allpass has forgotten the step from 0 (it decays x 1/3 a sample)
            self.assertAlmostEqual(out[i], math.tanh(signal[i - 1]), delta=1e-9)
        self.assertAlmostEqual(out[-1], -1.0, delta=1e-9)

    def biased(self, signal, bias):
        program = harness([AntiderivativeTanhSaturator("drive", input="in1", bias="bias")], {"bias": bias},
                          ["drive_out"])
        return program.run(len(signal), [signal])[0]

    def test_with_a_bias_it_is_the_slid_curve(self):
        # tanh(x + b) - tanh(b), half a sample late: exact for a slow signal, 0 at 0
        signal = [1.5 * math.sin(2 * math.pi * i / 400) for i in range(800)]
        out = self.biased(signal, 0.3)
        for i in range(100, 800):
            middle = 0.5 * (signal[i - 1] + signal[i])
            self.assertAlmostEqual(out[i], math.tanh(middle + 0.3) - math.tanh(0.3), delta=2e-4)
        self.assertEqual(self.biased([0.0] * 10, 0.3)[-1], 0.0)

    def test_with_a_bias_it_makes_even_harmonics_and_cuts_their_aliases(self):
        sine = [2.7 * math.sin(2 * math.pi * 8000.0 * i / self.SAMPLERATE) for i in range(4096)]
        out = self.biased(sine, 0.3)
        self.assertGreater(amplitude_at(out[512:], 16000.0, self.SAMPLERATE), 0.01, "a second harmonic")
        naive = GenProgram("out1 = tanh(in1 + 0.3) - tanh(0.3);", 1, 1).run(len(sine), [sine])[0]
        self.assertGreater(worst_alias_db(naive, 8000.0, range(2, 16), self.SAMPLERATE, 10000.0), -30.0)
        # measured 2026-10-19: -49.9 dB (the even harmonics fold too)
        self.assertLess(worst_alias_db(out, 8000.0, range(2, 16), self.SAMPLERATE, 10000.0), -48.0)


class BandLimitedEdgesTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def oscillator(self, fundamental, wave):
        """A saw (jump of -2 at each wrap) or a triangle (corners at phase 0 and 1/2) through the edges block."""
        edges = BandLimitedEdges("edges", naive="naive")
        if wave == "saw":
            edges.add_jump("wrapped", "phase / step", "-2")
            naive = "2 * phase - 1"
        else:
            edges.add_corner("wrapped", "phase / step", "-8 * step")
            edges.add_corner("last_phase < 0.5 && phase >= 0.5", "(phase - 0.5) / step", "8 * step")
            naive = "2 * abs(2 * phase - 1) - 1"
        code_before = (f"step = {fundamental!r} / samplerate;\nlast_phase = phase;\nunwrapped = phase + step;\n"
                       "wrapped = unwrapped >= 1;\nphase = wrap(unwrapped, 0, 1);\n"
                       f"naive = {naive};\n")
        template = ("/*GEN_BLOCK_FUNCTIONS*/\nHistory phase(0);\n/*GEN_BLOCK_DECLARATIONS*/\n" + code_before
                    + "/*EDGES*/\nout1 = edges_out;\n")
        code = gen_code_with_blocks(template, [edges], "edges harness")
        return GenProgram(code, 0, 1, samplerate=self.SAMPLERATE).run(4096 + 1000)[0][1000:]

    def test_the_saw_alias_floor(self):
        for fundamental in (2093.0, 4186.0):
            self.assertLess(worst_alias_db(self.oscillator(fundamental, "saw"), fundamental, range(2, 60),
                                           self.SAMPLERATE, 10000.0), -70.0, fundamental)

    def test_the_triangle_alias_floor(self):
        for fundamental in (2093.0, 4186.0):
            self.assertLess(worst_alias_db(self.oscillator(fundamental, "triangle"), fundamental, range(3, 60, 2),
                                           self.SAMPLERATE, 10000.0), -85.0, fundamental)

    def test_a_restart_gives_out_nothing_from_before_it(self):
        # a saw run two samples ahead (as a device feeds a wave it needs on time), its phase reset to 0 at sample 300:
        # after the restart the block gives out the restarted saw itself, with no old sample or pending correction
        edges = BandLimitedEdges("edges", naive="2 * wrap(phase + 2 * step, 0, 1) - 1")
        edges.add_jump("wrapped", "wrap(phase + 2 * step, 0, 1) / step", "-2")
        restart = edges.restart_statements(["2 * step - 1", "4 * step - 1"])
        step = 1000.0 / self.SAMPLERATE
        code = gen_code_with_blocks(
            f"/*GEN_BLOCK_FUNCTIONS*/\nHistory phase(0), count(0), lead(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
            f"step = {step!r};\ncount = count + 1;\nif (count == 300) {{\n\tphase = 0;\n\tlead = 2 * step;\n"
            f"\t{restart.replace(chr(10), chr(10) + chr(9))}\n}}\nphase = wrap(phase + step, 0, 1);\n"
            f"last_lead = lead;\nlead = wrap(phase + 2 * step, 0, 1);\nwrapped = lead < last_lead;\n"
            f"/*EDGES*/\nout1 = edges_out;\nout2 = 2 * phase - 1;\n", [edges], "restart harness")
        out, saw_now = GenProgram(code, 0, 2, samplerate=self.SAMPLERATE).run(320)
        for i in range(299, 305):         # the restart's sample (count 300 is index 299) and the next ones
            self.assertAlmostEqual(out[i], saw_now[i], delta=1e-12, msg=i)
        with self.assertRaises(BuildError):
            edges.restart_statements(["0"])

    def test_the_mix_is_two_samples_late_and_keeps_its_level(self):
        out = self.oscillator(100.0, "saw")
        self.assertAlmostEqual(sum(out[:441 * 9]) / (441 * 9), 0.0, delta=1e-3)
        self.assertAlmostEqual(max(out), 1.0, delta=0.02)


class TapeStyleEchoTests(unittest.TestCase):
    def echo(self, samplerate, diffusion=True, **params):
        block = TapeStyleEcho("echo", left_input="in1", right_input="in1", time_ms="time", feedback="feedback",
                         loop_lowpass_hz="lowpass", loop_highpass_hz="highpass", saturation_gain="saturation",
                         wow_cents="wow", flutter_cents="flutter", stop_pressed="stop > 0",
                         diffusion="diffusion" if diffusion else None, initial_time_ms=375.0,
                         longest_time_ms=6000.0, right_lag_ms=10.0, rounds_kept=3)
        defaults = {"time": 375.0, "feedback": 0.9, "lowpass": 1400.0, "highpass": 250.0, "saturation": 2.0,
                    "wow": 0.0, "flutter": 0.0, "stop": 0.0, "diffusion": 0.65}
        defaults.update(params)
        return harness([block], defaults, ["echo_left", "echo_right", "echo_loop_samples", "echo_wobble_samples",
                                           "echo_round_peak_1"], samplerate=samplerate)

    @staticmethod
    def centroid_ms(signal, center, half_width, samplerate):
        window = signal[center - half_width:center + half_width]
        energy = sum(v * v for v in window)
        return sum((i - half_width) * v * v for i, v in enumerate(window)) / energy / samplerate * 1000

    def repeats_late_ms(self, samplerate, time_ms, repeats, **params):
        program = self.echo(samplerate, time=time_ms, **params)
        settle = 2 + 2 * abs(time_ms - 375.0) / 1000           # the time glides there first (<= 0.5 ms a ms)
        program.run(int(samplerate * settle), [[0.0] * int(samplerate * settle)])
        loop = time_ms / 1000 * samplerate
        impulse = [0.0] * (int(loop * (repeats + 1)) + 100)
        impulse[10] = 1.0
        left, right = program.run(len(impulse), [impulse])[:2]
        lag = int(round(0.010 * samplerate))
        return ([self.centroid_ms(left, int(10 + k * loop), int(loop / 2), samplerate) for k in range(1, repeats + 1)],
                [self.centroid_ms(right, int(10 + k * loop) + lag, int(loop / 2), samplerate)
                 for k in range(1, repeats + 1)])

    def test_repeats_land_on_the_grid(self):
        # without diffusion, ten repeats at Dub-like filters; with it, five repeats in windows wider than the smear
        for filters in ({"lowpass": 1400.0, "highpass": 250.0}, {"lowpass": 4500.0, "highpass": 90.0}):
            for side in self.repeats_late_ms(8000.0, 375.0, 10, diffusion=0.0, **filters):
                self.assertLess(max(abs(late) for late in side), 1.0, (filters, side))
        for side in self.repeats_late_ms(8000.0, 1500.0, 5):
            self.assertLess(max(abs(late) for late in side), 1.0, side)

    def test_a_time_change_never_reads_backwards(self):
        samplerate = 2000.0
        program = self.echo(samplerate)
        for time_ms in (500.0, 20.0, 6000.0, 375.0):
            program.set_param("time", time_ms)
            seconds = 14 if time_ms in (6000.0, 375.0) else 4   # at most 0.5 ms a ms: 20 -> 6000 ms takes 12 s
            loop = program.run(int(samplerate * seconds), [[0.0] * int(samplerate * seconds)])[2]
            speeds = [1 - (b - a) for a, b in zip(loop, loop[1:])]
            self.assertGreaterEqual(min(speeds), 0.5 - 1e-9, time_ms)
            self.assertLessEqual(max(speeds), 1.5 + 1e-9, time_ms)
            self.assertAlmostEqual(loop[-1], time_ms * samplerate / 1000, delta=1.0, msg=time_ms)

    def test_over_unity_it_howls_held_by_the_saturation(self):
        samplerate = 8000.0
        burst = [0.3 * math.sin(i * 0.37) for i in range(800)] + [0.0] * int(samplerate * 4)
        program = self.echo(samplerate, time=100.0, feedback=1.4, saturation=2.0)
        program.run(int(samplerate), [[0.0] * int(samplerate)])
        left = program.run(len(burst), [burst])[0]
        last_second = left[-int(samplerate):]
        self.assertGreater(max(abs(v) for v in last_second), 0.1, "it still sings 4 s after the burst")
        self.assertLess(max(abs(v) for v in left), 0.6, "held under 1 / saturation (plus the read's overshoot)")
        program = self.echo(samplerate, time=100.0, feedback=1.0, saturation=2.0)
        program.run(int(samplerate), [[0.0] * int(samplerate)])
        self.assertLess(max(abs(v) for v in program.run(len(burst), [burst])[0][-int(samplerate):]), 0.01,
                        "under the loop's loss it dies away")

    def test_wow_and_flutter_are_pitch(self):
        samplerate = 1000.0
        for wow, flutter, seconds in ((10.0, 0.0, 60), (0.0, 5.0, 4)):
            wobbles = []
            for time_ms, run_seconds in ((100.0, seconds), (3000.0, 4)):
                program = self.echo(samplerate, time=time_ms, wow=wow, flutter=flutter)
                wobbles.append(program.run(int(samplerate * run_seconds), [[0.0] * int(samplerate * run_seconds)])[3])
            # the delay moves by whole wobbles (the same noise and phase), whatever the Time
            self.assertEqual(wobbles[0][:len(wobbles[1])], wobbles[1])
            settled = wobbles[0][int(samplerate * 2):]
            pitch_cents = [1200 * math.log2(1 + (b - a)) for a, b in zip(settled, settled[1:])]
            rms = math.sqrt(sum(c * c for c in pitch_cents) / len(pitch_cents))
            self.assertAlmostEqual(rms, wow + flutter, delta=(0.25 if wow else 0.03) * (wow + flutter), msg=rms)

    def test_stop_empties_it(self):
        samplerate = 8000.0
        program = self.echo(samplerate, time=200.0, feedback=1.4)
        noise = [0.5 * math.sin(i * 0.9) for i in range(4000)]
        program.run(len(noise), [noise])
        program.set_param("stop", 1.0)
        program.run(1, [[0.0]])
        program.set_param("stop", 0.0)
        left, right, _, _, rounds = program.run(4000, [[0.0] * 4000])
        self.assertLess(max(abs(v) for v in left[40:] + right[40:]), 1e-12)
        self.assertEqual(rounds[-1], 0.0)



class ZeroDelayStateVariableFilterTests(unittest.TestCase):
    SAMPLERATE = 22050.0
    OUTPUTS = ["svf_lowpass", "svf_bandpass", "svf_highpass", "svf_bandpass_normalised"]

    def svf(self, cutoff, q):
        program = harness([ZeroDelayStateVariableFilter("svf", input="in1", cutoff_hz="cutoff", q="q")],
                          {"cutoff": cutoff, "q": q}, self.OUTPUTS, samplerate=self.SAMPLERATE)
        return program

    def sine_response(self, cutoff, q, frequency, samples=4410):
        """The four outputs' amplitudes for a unit sine at `frequency`, after the filter settles."""
        program = self.svf(cutoff, q)
        sine = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(samples)]
        outputs = program.run(samples, [sine])
        half = samples // 2
        return [amplitude_at(output[half:], frequency, self.SAMPLERATE) for output in outputs]

    def test_small_signals_are_the_prewarped_analog_svf(self):
        # the circuit uses: an 8.5 kHz low-pass Q 1.94 at 44.1 k is 4.25 kHz at 22.05 k (same fc / sr)
        for cutoff, q in ((4250.0, 1.94), (963.0, 2.13), (229.0, 1.58)):
            for frequency in (cutoff / 3, cutoff, cutoff * 2.2):
                if frequency >= 0.45 * self.SAMPLERATE:
                    continue
                expected = small_signal_response(frequency, cutoff, q, self.SAMPLERATE)
                measured = self.sine_response(cutoff, q, frequency)
                for name, amplitude in zip(("lowpass", "bandpass", "highpass"), measured):
                    with self.subTest(cutoff=cutoff, q=q, frequency=frequency, output=name):
                        self.assertAlmostEqual(20 * math.log10(amplitude), 20 * math.log10(abs(expected[name])),
                                               delta=0.05)

    def test_the_normalised_band_pass_has_unit_gain_at_the_cutoff(self):
        for cutoff in (300.0, 3000.0, 8000.0):
            with self.subTest(cutoff=cutoff):
                self.assertAlmostEqual(20 * math.log10(self.sine_response(cutoff, 7.3, cutoff, 8820)[3]), 0.0, delta=0.05)

    def test_the_outputs_split_the_input(self):
        program = harness([ZeroDelayStateVariableFilter("svf", input="in1", cutoff_hz="cutoff", q="q")],
                          {"cutoff": 1234.0, "q": 3.0}, ["svf_lowpass + svf_bandpass_normalised + svf_highpass"],
                          samplerate=self.SAMPLERATE)
        signal = [math.sin(0.37 * n) + 0.5 * math.sin(2.9 * n) for n in range(2000)]
        rebuilt = program.run(2000, [signal])[0]
        self.assertLess(max(abs(a - b) for a, b in zip(rebuilt, signal)), 1e-12)

    def test_an_impulse_rings_at_q_over_pi_fc(self):
        # the 909 rim shot's 495 Hz bridged-T: Q 7.3, tau 4.7 ms (2sl drums references/voices.md)
        cutoff, q = 495.0, 7.3
        program = self.svf(cutoff, q)
        ring = program.run(2205, [[1.0] + [0.0] * 2204])[1]
        def envelope_at(start):
            return max(abs(sample) for sample in ring[start:start + 45])
        early, late = 220, 1323                    # 10 ms and 60 ms
        measured_tau = (late - early) / self.SAMPLERATE / math.log(envelope_at(early) / envelope_at(late))
        self.assertAlmostEqual(measured_tau / ring_time_constant_seconds(cutoff, q), 1.0, delta=0.03)
        self.assertAlmostEqual(frequency_by_zero_crossings(ring[:1500], self.SAMPLERATE), cutoff, delta=cutoff * 0.01)

    def test_stable_under_fast_modulation(self):
        program = harness([ZeroDelayStateVariableFilter("svf", input="in1", cutoff_hz="20 + 9000 * (0.5 + 0.5 * sin(in1 * 300))",
                                               q="0.05 + 30 * (0.5 + 0.5 * cos(in1 * 170))")],
                          {}, self.OUTPUTS, samplerate=self.SAMPLERATE)
        noise = [math.sin(n * n * 0.001) for n in range(8000)]
        outputs = program.run(8000, [noise])
        self.assertTrue(all(math.isfinite(value) and abs(value) < 1e3 for output in outputs for value in output))

    def prewarped_sine_response(self, cutoff, q, prewarp, frequency, samples=4410):
        program = harness([ZeroDelayStateVariableFilter("svf", input="in1", cutoff_hz="cutoff", q="q", prewarp_hz="prewarp")],
                          {"cutoff": cutoff, "q": q, "prewarp": prewarp}, self.OUTPUTS, samplerate=self.SAMPLERATE)
        sine = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(samples)]
        outputs = program.run(samples, [sine])
        return [amplitude_at(output[samples // 2:], frequency, self.SAMPLERATE) for output in outputs]

    def test_the_prewarping_point_is_where_the_analog_response_is_exact(self):
        # an overdamped network heard far below its natural frequency (2sl gate's 292), one past Nyquist, and a
        # resonant one prewarped off its peak
        for cutoff, q, prewarp in ((4000.0, 0.2, 700.0), (60000.0, 0.25, 3000.0), (1500.0, 6.0, 5000.0)):
            def analog(frequency):
                s = 1j * frequency / cutoff
                return 1 / (s * s + s / q + 1)
            at_the_point = small_signal_response(prewarp, cutoff, q, self.SAMPLERATE, prewarp_hz=prewarp)["lowpass"]
            with self.subTest(cutoff=cutoff, q=q, prewarp=prewarp, claim="exact at the point"):
                self.assertLess(abs(at_the_point - analog(prewarp)), 1e-9)
            for frequency in (prewarp / 4, prewarp, min(prewarp * 1.7, 0.4 * self.SAMPLERATE)):
                expected = small_signal_response(frequency, cutoff, q, self.SAMPLERATE, prewarp_hz=prewarp)
                measured = self.prewarped_sine_response(cutoff, q, prewarp, frequency)
                for name, amplitude in zip(("lowpass", "bandpass", "highpass"), measured):
                    with self.subTest(cutoff=cutoff, q=q, prewarp=prewarp, frequency=frequency, output=name):
                        self.assertAlmostEqual(20 * math.log10(amplitude), 20 * math.log10(abs(expected[name])),
                                               delta=0.05)

    def test_a_cutoff_past_nyquist_is_not_clamped(self):
        # g = tan(pi fp / sr) fc / fp grows past the old tan(0.45 pi) = 6.3: a low-pass at 20 sr with Q 0.1 passes
        # 1 kHz within 0.01 dB (clamped to 0.45 sr it was -0.21 dB), and a prewarping point past 0.45 sr is held there
        twenty_sample_rates = 20 * self.SAMPLERATE
        measured = self.prewarped_sine_response(twenty_sample_rates, 0.1, 0.45 * self.SAMPLERATE, 1000.0)[0]
        self.assertAlmostEqual(20 * math.log10(measured), 0.0, delta=0.01)
        held = small_signal_response(1000.0, twenty_sample_rates, 0.1, self.SAMPLERATE, prewarp_hz=self.SAMPLERATE)
        bounded = small_signal_response(1000.0, twenty_sample_rates, 0.1, self.SAMPLERATE, prewarp_hz=0.45 * self.SAMPLERATE)
        self.assertEqual(held, bounded)
        self.assertAlmostEqual(20 * math.log10(measured), 20 * math.log10(abs(bounded["lowpass"])), delta=0.01)

    def test_stable_with_the_cutoff_swept_far_past_nyquist(self):
        program = harness([ZeroDelayStateVariableFilter("svf", input="in1", cutoff_hz="20 + 2e6 * (0.5 + 0.5 * sin(in1 * 300))",
                                               q="0.05 + 30 * (0.5 + 0.5 * cos(in1 * 170))",
                                               prewarp_hz="20 + 30000 * (0.5 + 0.5 * sin(in1 * 90))")],
                          {}, self.OUTPUTS, samplerate=self.SAMPLERATE)
        noise = [math.sin(n * n * 0.001) for n in range(8000)]
        outputs = program.run(8000, [noise])
        self.assertTrue(all(math.isfinite(value) and abs(value) < 1e3 for output in outputs for value in output))

    def test_a_number_input_must_be_finite_and_above_zero(self):
        for input_name in ("cutoff_hz", "q", "prewarp_hz"):
            for bad in ("0", "-5", "inf", "nan"):
                inputs = dict(input="in1", cutoff_hz="1000", q="0.7", prewarp_hz="1000")
                inputs[input_name] = bad
                with self.subTest(input=input_name, value=bad), self.assertRaises(BuildError):
                    ZeroDelayStateVariableFilter("svf", **inputs)


class KneeSoftClipTests(unittest.TestCase):
    KNEES = (0.8, 0.95)

    def clip(self, signal, knee):
        program = harness([KneeSoftClip("clip", input="in1", knee=knee)], {}, ["clip_out"])
        return program.run(len(signal), [signal])[0]

    def test_it_is_unity_up_to_the_knee(self):
        for knee in self.KNEES:
            signal = [knee * (2.0 * i / 200 - 1.0) for i in range(201)]
            self.assertEqual(self.clip(signal, knee), signal, knee)

    def test_value_and_slope_are_continuous_at_the_knee(self):
        step = 1e-6
        for knee in self.KNEES:
            for side in (1.0, -1.0):
                below, at, above = self.clip([side * (knee - step), side * knee, side * (knee + step)], knee)
                self.assertAlmostEqual(at, side * knee, delta=1e-12)
                self.assertAlmostEqual((at - below) / (side * step), 1.0, delta=1e-6, msg=(knee, side, "slope below"))
                self.assertAlmostEqual((above - at) / (side * step), 1.0, delta=1e-5, msg=(knee, side, "slope above"))

    def test_the_output_is_bounded_by_one_odd_and_rising(self):
        for knee in self.KNEES:
            signal = [0.01 * i for i in range(0, 5000)] + [1e3, 1e9]
            out = self.clip(signal, knee)
            self.assertTrue(all(b >= a for a, b in zip(out, out[1:])), "rising")
            self.assertLessEqual(max(out), 1.0)
            self.assertGreater(out[-1], 1.0 - 1e-12, "reaches 1 for a huge input")
            self.assertEqual(self.clip([-x for x in signal], knee), [-x for x in out], "odd")

    def test_the_knee_must_be_a_number_between_0_and_1(self):
        for knee in (0.0, 1.0, -0.5, 1.5, "0.8", None, True):
            with self.assertRaises(BuildError, msg=repr(knee)):
                KneeSoftClip("clip", input="in1", knee=knee)

    def test_its_headroom_is_one_minus_the_knee_as_written(self):
        self.assertIn("soft_clip_above_knee((in1), 0.8, 0.2)", KneeSoftClip("c", input="in1", knee=0.8).statements())
        self.assertIn("0.95, 0.05)", KneeSoftClip("c", input="in1", knee=0.95).statements())


if __name__ == "__main__":
    unittest.main(verbosity=2)

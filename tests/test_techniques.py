"""The kit's techniques (m4l_dev/techniques/): each technique's claims, rendered through our GenExpr renderer
(m4l_dev/genexpr.py: ours, not Max's compiler). Each claim runs on a small harness program around one technique
(tests/gen_block_harness.py), at the lowest sample rate that still tests it, so the whole file takes seconds. Standard
library only."""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev import es5  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.gen_blocks import gen_code_with_blocks  # noqa: E402
from m4l_dev.genexpr import GenProgram  # noqa: E402
from m4l_dev.techniques.antiderivative_piecewise_linear_shaper import (  # noqa: E402
    SECOND_ORDER_EQUALISER_EDGE_AT_2X, SECOND_ORDER_EQUALISER_INNER_TAP_AT_2X, SECOND_ORDER_EQUALISER_OUTER_TAP_AT_2X,
    SECOND_ORDER_EQUALISERS, AntiderivativePiecewiseLinearShaper, PiecewiseLinearTable, second_order_equaliser)
from m4l_dev.techniques.antiderivative_tanh_saturator import AntiderivativeTanhSaturator  # noqa: E402
from m4l_dev.techniques.antiderivative_tanh_saturator import EQUALISER_EDGE as TANH_EQUALISER_EDGE  # noqa: E402
from m4l_dev.techniques.antiderivative_tanh_saturator import EQUALISER_INNER_TAP as TANH_EQUALISER_INNER_TAP  # noqa: E402
from m4l_dev.techniques.antiderivative_tanh_saturator import EQUALISER_OUTER_TAP as TANH_EQUALISER_OUTER_TAP  # noqa: E402
from m4l_dev.techniques.antiderivative_tanh_saturator import EQUALISER_TAPS as TANH_EQUALISER_TAPS  # noqa: E402
from m4l_dev.techniques.band_limited_edges import BandLimitedEdges  # noqa: E402
from m4l_dev.techniques.knee_soft_clip import KneeSoftClip  # noqa: E402
from m4l_dev.techniques import sidechain_style_pump  # noqa: E402
from m4l_dev.techniques.sidechain_style_pump import SidechainStylePump  # noqa: E402


from m4l_dev.techniques.led_driven_photocell import LedDrivenPhotocell  # noqa: E402
from m4l_dev.techniques.tape_style_echo import TapeStyleEcho  # noqa: E402
from m4l_dev.techniques.zero_delay_allpass_cascade import (FirstOrderAllpassStage,  # noqa: E402
                                                           SecondOrderAllpassStage, ZeroDelayAllpassCascade)
from m4l_dev.techniques.zero_delay_allpass_cascade import \
    small_signal_response as cascade_small_signal_response  # noqa: E402
from m4l_dev.techniques.zero_delay_ladder_filter import (ZeroDelayLadderFilter, response_script_code,  # noqa: E402
                                                         small_signal_magnitude)
from m4l_dev.techniques.zero_delay_one_pole_filter import ZeroDelayOnePoleFilter  # noqa: E402
from m4l_dev.techniques.zero_delay_one_pole_filter import \
    small_signal_response as one_pole_small_signal_response  # noqa: E402
from m4l_dev.techniques.zero_delay_state_variable_filter import (ZeroDelayStateVariableFilter,  # noqa: E402
                                                                 ring_time_constant_seconds, small_signal_response)
from m4l_dev.techniques import drum_envelope  # noqa: E402
from m4l_dev.techniques.bell_equalizer import BellEqualizer  # noqa: E402
from m4l_dev.techniques.bell_equalizer import small_signal_response as bell_small_signal_response  # noqa: E402
from m4l_dev.techniques.drum_envelope import DrumEnvelope, exponential_rise  # noqa: E402
from m4l_dev.techniques.halfband_oversampler import (HALFBAND_ROUND_TRIP_LATENCY_SAMPLES,  # noqa: E402
                                                     HalfbandDownsampler, HalfbandUpsampler,
                                                     halfband_attenuation_db, halfband_coefficients, halfband_response)
from m4l_dev.techniques.metallic_noise import METALLIC_NOISE_SOURCES, LfsrMetallicNoise, lfsr_cycle  # noqa: E402
from m4l_dev.techniques.pitch_modulator import SHAPES, PitchModulator  # noqa: E402
from m4l_dev.techniques.pitch_modulator import wave as pitch_modulator_wave  # noqa: E402
from m4l_dev.techniques.seeded_white_noise import SeededWhiteNoise, park_miller_sequence  # noqa: E402
from gen_block_harness import (amplitude_at, cents, complex_amplitude_at, equalised_second_order_outputs,  # noqa: E402
                               exact_second_order_mean, folded, frequency_by_zero_crossings, harness, phase_degrees,
                               adaa_equaliser_remez, worst_alias_db)


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


    def test_the_pass_band_is_the_ladder_s_own(self):
        # no make-up inside the technique: a small 60 Hz sine with fc 8 kHz comes out at 1 / (1 + k)
        program = self.ladder()
        program.set_param("cutoff", 8000.0)
        for resonance in (0.0, 0.5, 0.9):
            program.set_param("resonance", resonance)
            sine = [1e-3 * math.sin(2 * math.pi * 60.0 * i / self.SAMPLERATE) for i in range(8820)]
            level = amplitude_at(program.run(len(sine), [sine])[0][4410:], 60.0, self.SAMPLERATE) / 1e-3
            self.assertAlmostEqual(20 * math.log10(level), -20 * math.log10(1 + 4.35 * resonance), delta=0.02)

    def test_a_reset_starts_it_as_a_fresh_ladder(self):
        ladder = ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="1000", resonance="0.8")
        template = ("/*GEN_BLOCK_FUNCTIONS*/\nParam reset(0, min=0, max=1);\n/*GEN_BLOCK_DECLARATIONS*/\n"
                    f"if (reset > 0.5) {{\n{ladder.reset_statements()}\n}}\n/*LADDER*/\nout1 = ladder_out;\n")
        code = gen_code_with_blocks(template, [ladder], "reset test")
        saw = [((i * 220.0 / self.SAMPLERATE) % 1) * 2 - 1 for i in range(2000)]
        fresh = GenProgram(code, 1, 1, samplerate=self.SAMPLERATE).run(len(saw), [saw])[0]
        used = GenProgram(code, 1, 1, samplerate=self.SAMPLERATE)
        used.run(1234, [[0.7] * 1234])
        used.set_param("reset", 1.0)
        first = used.run(1, [[saw[0]]])[0]
        used.set_param("reset", 0.0)
        self.assertEqual(first + used.run(len(saw) - 1, [saw[1:]])[0], fresh)


class AntiderivativeTanhSaturatorTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def saturate(self, signal, block=True, samplerate=SAMPLERATE):
        if block:
            program = harness([AntiderivativeTanhSaturator("drive", input="in1")], {}, ["drive_out"],
                              samplerate=samplerate)
        else:
            program = GenProgram("out1 = tanh(in1);", 1, 1)
        return program.run(len(signal), [signal])[0]

    def test_it_cuts_the_aliases_of_a_hot_8k_sine(self):
        sine = [2.7 * math.sin(2 * math.pi * 8000.0 * i / self.SAMPLERATE) for i in range(4096)]
        harmonics = range(3, 16, 2)
        naive = worst_alias_db(self.saturate(sine, block=False), 8000.0, harmonics, self.SAMPLERATE, 10000.0)
        antialiased = worst_alias_db(self.saturate(sine), 8000.0, harmonics, self.SAMPLERATE, 10000.0)
        self.assertGreater(naive, -30.0)
        self.assertLess(antialiased, -50.0)       # measured 2026-10-20: -54.3 dB

    def test_the_equaliser_undoes_the_two_tap_mean_up_to_its_edge(self):
        # the taps are the Remez design's, DC exactly 1, the 2-tap mean's cos(w / 2) within 0.0099 dB up to the edge;
        # measured on quiet sines through the block, LATENCY_SAMPLES late, linear phase; above the edge it falls
        taps, worst = adaa_equaliser_remez(lambda w: math.cos(w / 2), TANH_EQUALISER_EDGE, 2)
        self.assertAlmostEqual(taps[0], TANH_EQUALISER_OUTER_TAP, places=12)
        self.assertAlmostEqual(taps[1], TANH_EQUALISER_INNER_TAP, places=12)
        self.assertAlmostEqual(sum(TANH_EQUALISER_TAPS), 1.0, places=15)
        self.assertLess(-20 * math.log10(1 - worst), 0.0100)
        self.assertEqual(AntiderivativeTanhSaturator.LATENCY_SAMPLES, 2.5)
        count = 4096
        for frequency, lowest_db, highest_db in ((1000.0, -0.01, 0.01), (5000.0, -0.01, 0.01), (9000.0, -0.01, 0.01),
                                                 (15000.0, -1.7, -1.5)):
            quiet = [0.001 * math.sin(2 * math.pi * frequency * i / self.SAMPLERATE) for i in range(count)]
            late = [0.001 * math.sin(2 * math.pi * frequency * (i - AntiderivativeTanhSaturator.LATENCY_SAMPLES)
                                     / self.SAMPLERATE) for i in range(count)]
            gain = complex_amplitude_at(self.saturate(quiet)[100:], frequency, self.SAMPLERATE) / complex_amplitude_at(
                late[100:], frequency, self.SAMPLERATE)
            self.assertGreater(20 * math.log10(abs(gain)), lowest_db, msg=frequency)
            self.assertLess(20 * math.log10(abs(gain)), highest_db, msg=frequency)
            self.assertLess(abs(gain.imag), 1e-6, msg=f"{frequency}: linear phase, LATENCY_SAMPLES late")

    def test_hot_sines_stay_near_the_band_limited_tanh_at_any_drive(self):
        # the ideal: tanh of the continuous sine, LATENCY_SAMPLES late, its odd harmonics below Nyquist (its Fourier
        # series); the old split (x on an allpass, ADAA on tanh x - x) was off by about 0.22 x the drive at 10 kHz
        # (fundamental error 1.6 x the ideal's at drive 10, peaks 3.2; at 15 kHz drive 20, peaks 10.9). Measured
        # 2026-10-20 here: fundamental error <= 0.40 (the ideal's is 1.27), peaks <= 1.69, alike at drives 3 and 20
        for samplerate in (44100.0, 48000.0, 96000.0):
            for frequency in (5000.0, 10000.0, 15000.0):
                for drive in (3.0, 20.0):
                    count = 1088
                    sine = [drive * math.sin(2 * math.pi * frequency * i / samplerate) for i in range(count)]
                    out = self.saturate(sine, samplerate=samplerate)[64:]
                    points = 4096
                    harmonics = [k for k in range(1, 40, 2) if k * frequency < samplerate / 2]
                    coefficients = {k: 2 / points * sum(math.tanh(drive * math.sin(2 * math.pi * m / points))
                                                        * math.sin(2 * math.pi * k * m / points) for m in range(points))
                                    for k in harmonics}
                    ideal = [sum(coefficients[k] * math.sin(2 * math.pi * k * frequency * (
                        i - AntiderivativeTanhSaturator.LATENCY_SAMPLES) / samplerate) for k in harmonics)
                        for i in range(64, count)]
                    error = abs(complex_amplitude_at(out, frequency, samplerate)
                                - complex_amplitude_at(ideal, frequency, samplerate))
                    case = f"{samplerate} Hz rate, {frequency} Hz, drive {drive}"
                    self.assertLess(error, 0.42, msg=case)
                    self.assertLess(max(map(abs, out)), 1.75, msg=case)

    def test_near_equal_samples_are_exact(self):
        signal = [0.5 + 1e-12 * i for i in range(200)] + [3.0] * 50 + [-20.0] * 50
        out = self.saturate(signal)
        for i in range(10, 200):          # a constant through the means and the equaliser (DC 1)
            self.assertAlmostEqual(out[i], math.tanh(signal[i - 2]), delta=1e-9)
        self.assertAlmostEqual(out[-1], -1.0, delta=1e-9)

    def biased(self, signal, bias):
        program = harness([AntiderivativeTanhSaturator("drive", input="in1", bias="bias")], {"bias": bias},
                          ["drive_out"])
        return program.run(len(signal), [signal])[0]

    def test_with_a_bias_it_is_the_slid_curve(self):
        # tanh(x + b) - tanh(b), LATENCY_SAMPLES late: exact for a slow signal, 0 at 0
        signal = [1.5 * math.sin(2 * math.pi * i / 400) for i in range(800)]
        out = self.biased(signal, 0.3)
        for i in range(100, 800):
            middle = 0.5 * (signal[i - 2] + signal[i - 3])
            self.assertAlmostEqual(out[i], math.tanh(middle + 0.3) - math.tanh(0.3), delta=2e-4)
        self.assertEqual(self.biased([0.0] * 10, 0.3)[-1], 0.0)

    def test_with_a_bias_it_makes_even_harmonics_and_cuts_their_aliases(self):
        sine = [2.7 * math.sin(2 * math.pi * 8000.0 * i / self.SAMPLERATE) for i in range(4096)]
        out = self.biased(sine, 0.3)
        self.assertGreater(amplitude_at(out[512:], 16000.0, self.SAMPLERATE), 0.01, "a second harmonic")
        naive = GenProgram("out1 = tanh(in1 + 0.3) - tanh(0.3);", 1, 1).run(len(sine), [sine])[0]
        self.assertGreater(worst_alias_db(naive, 8000.0, range(2, 16), self.SAMPLERATE, 10000.0), -30.0)
        self.assertLess(worst_alias_db(out, 8000.0, range(2, 16), self.SAMPLERATE, 10000.0), -47.5)   # measured 2026-10-20: -48.1 dB


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



class AntiderivativePiecewiseLinearShaperTests(unittest.TestCase):
    SAMPLERATE = 44100.0
    # a hard clip at +-0.5 with unity slope inside: three straight pieces
    CLIP = [(-math.inf, 0.0, -0.5), (-0.5, 1.0, 0.0), (0.5, 0.0, 0.5)]

    def test_the_functions_are_the_table_and_its_integral(self):
        table = PiecewiseLinearTable("clip", self.CLIP)
        code = "\n".join(table.functions().values()) + (f"\nout1 = {table.value_call('in1')};\n"
                                                         f"out2 = {table.integral_call('in1')};\n")
        points = [x / 13 for x in range(-30, 31)] + [-0.5, 0.5]
        values, integrals = GenProgram(code, 1, 2).run(len(points), [points])
        for x, value, integral in zip(points, values, integrals):
            self.assertAlmostEqual(value, table.value(x), places=12, msg=x)
            self.assertAlmostEqual(integral, table.integral(x), places=12, msg=x)
            area = sum(table.value(x * (k + 0.5) / 4000) for k in range(4000)) * x / 4000      # the area from 0
            self.assertAlmostEqual(table.integral(x), area, places=5, msg=x)

    def test_the_mean_is_exact_on_a_piece_and_lowers_the_aliases(self):
        table = PiecewiseLinearTable("clip", self.CLIP)
        program = harness([AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, oversampling=1)], {},
                          ["shaper_out"], samplerate=self.SAMPLERATE)
        inside = [0.3 * math.sin(2 * math.pi * 500 * i / self.SAMPLERATE) for i in range(200)]
        out = program.run(len(inside), [inside])[0]
        for i in range(1, len(inside)):                  # inside one piece: the mean of a line, half a sample late
            self.assertAlmostEqual(out[i], 0.5 * (inside[i] + inside[i - 1]), places=12)
        # a hot 3 kHz sine through the clip: the worst alias below 10 kHz, ADAA against the clip taken naively
        count, fundamental = 8192, 3000.0
        hot = [2.0 * math.sin(2 * math.pi * fundamental * i / self.SAMPLERATE) for i in range(count)]
        program = harness([AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, oversampling=1)], {},
                          ["shaper_out"], samplerate=self.SAMPLERATE)
        antialiased = program.run(count, [hot])[0][1000:]
        naive = [table.value(x) for x in hot][1000:]
        harmonics = range(9, 40, 2)
        self.assertLess(worst_alias_db(antialiased, fundamental, harmonics, self.SAMPLERATE, 10000),
                        worst_alias_db(naive, fundamental, harmonics, self.SAMPLERATE, 10000) - 6)

    # a folder-like table: pieces both ways, a corner where two meet closely, flat outer pieces
    FOLD = [(-math.inf, 0.0, -1.0), (-2.0, -1.5, -4.0), (-1.0, 1.0, -1.5), (-0.999, 2.0, -0.501),
            (0.4, -0.5, 0.499), (1.7, 0.0, -0.351)]

    def test_second_order_is_eq_15_exactly_and_well_conditioned(self):
        table = PiecewiseLinearTable("fold", self.FOLD)
        self.assertTrue(table.is_continuous)
        generator = random.Random(259)
        triples = []
        for _ in range(300):                             # anywhere, steps from large to tiny
            x0 = generator.uniform(-3, 3)
            step = 10 ** generator.uniform(-5, 0.5)
            triples.append((x0, x0 - step * generator.uniform(-1, 1), x0 - step * generator.uniform(-1, 1)))
        for corner in (-2.0, -1.0, -0.999, 0.4, 1.7):    # straddling a corner closely, and turning round at one
            for scale in (1e-2, 1e-4, 1e-5):
                triples += [(corner + scale, corner - 0.3 * scale, corner - scale),
                            (corner + scale, corner - 0.7 * scale, corner + 1.3 * scale)]
        x0s, x1s, x2s = (list(column) for column in zip(*triples))
        code = "\n".join(table.functions().values()) + f"\nout1 = {table.second_order_mean_call('in1', 'in2', 'in3')};\n"
        values = GenProgram(code, 3, 1).run(len(triples), [x0s, x1s, x2s])[0]
        for (x0, x1, x2), value in zip(triples, values):
            self.assertAlmostEqual(value, exact_second_order_mean(table.pieces, x0, x1, x2), delta=1e-9,
                                   msg=(x0, x1, x2))
            self.assertLessEqual(abs(value), 3.0)        # never blows up near a corner (the table stays under 3)

    def test_second_order_is_the_equalised_line_on_a_piece_at_either_oversampling(self):
        # inside one piece: the line at the three's mean (raw), through the equaliser for the rate it runs at (at 1x
        # none: the raw mean itself)
        table = PiecewiseLinearTable("clip", self.CLIP)
        inside = [0.3 * math.sin(2 * math.pi * 500 * i / self.SAMPLERATE) for i in range(200)]
        raw_means = [(inside[i] + (inside[i - 1] if i >= 1 else 0.0) + (inside[i - 2] if i >= 2 else 0.0)) / 3
                     for i in range(len(inside))]
        for oversampling in (1, 2):
            shaper = AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=2,
                                                         oversampling=oversampling)
            out = harness([shaper], {}, ["shaper_out"], samplerate=self.SAMPLERATE).run(len(inside), [inside])[0]
            taps = SECOND_ORDER_EQUALISERS[oversampling].taps
            for i, expected in enumerate(equalised_second_order_outputs(raw_means, taps)):
                self.assertAlmostEqual(out[i], expected, places=12, msg=(oversampling, i))
        self.assertEqual(SECOND_ORDER_EQUALISERS[1].taps, (1.0,))

    def test_second_order_lowers_the_aliases_further_at_1x(self):
        # the hot 3 kHz sine at 44.1 kHz, run at that rate (measured 2026-10-20, worst alias below 10 kHz: naive -38.2,
        # ADAA1 -55.3, ADAA2 -72.6 dB; the 2x equaliser at this rate, wrongly, -69.9)
        table = PiecewiseLinearTable("clip", self.CLIP)
        count, fundamental = 8192, 3000.0
        hot = [2.0 * math.sin(2 * math.pi * fundamental * i / self.SAMPLERATE) for i in range(count)]
        harmonics = range(9, 40, 2)
        worst = {}
        for order in (1, 2):
            program = harness([AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=order,
                                                                   oversampling=1)],
                              {}, ["shaper_out"], samplerate=self.SAMPLERATE)
            worst[order] = worst_alias_db(program.run(count, [hot])[0][1000:], fundamental, harmonics,
                                          self.SAMPLERATE, 10000)
        self.assertLess(worst[2], worst[1] - 15)

    def shaper_gain(self, oversampling, rate, frequency):
        """A quiet sine inside one piece (the clip's unity line) through the second-order shaper at `oversampling`
        (run at `rate`): its complex gain re the input `latency_steps` before."""
        count = 4000
        table = PiecewiseLinearTable("clip", self.CLIP)
        shaper = AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=2,
                                                     oversampling=oversampling)
        late = shaper.latency_steps
        quiet = [0.3 * math.sin(2 * math.pi * frequency * i / rate) for i in range(count)]
        out = harness([shaper], {}, ["shaper_out"], samplerate=rate).run(count, [quiet])[0]
        return complex_amplitude_at(out[100:], frequency, rate) / complex_amplitude_at(
            quiet[100 - late:count - late], frequency, rate)

    def test_the_2x_equaliser_undoes_the_three_tap_mean_up_to_its_edge_and_lifts_nothing_to_the_hosts_nyquist(self):
        # the taps are the Remez design's, the DC exactly 1, the 3-tap mean's droop (at 96 kHz -5.9 dB at 20 kHz)
        # within 0.0972 dB (1 - 0.0111) up to the edge (20 kHz at 96 kHz), and never above that up to the host's
        # Nyquist (24 kHz: from there the downsampler's); measured on the shaper, three steps late
        equaliser = second_order_equaliser(2, "test")
        taps, worst = adaa_equaliser_remez(lambda w: (1 + 2 * math.cos(w)) / 3, SECOND_ORDER_EQUALISER_EDGE_AT_2X, 2)
        self.assertAlmostEqual(taps[0], SECOND_ORDER_EQUALISER_OUTER_TAP_AT_2X, places=12)
        self.assertAlmostEqual(taps[1], SECOND_ORDER_EQUALISER_INNER_TAP_AT_2X, places=12)
        self.assertEqual(equaliser.taps[:2], (SECOND_ORDER_EQUALISER_OUTER_TAP_AT_2X, SECOND_ORDER_EQUALISER_INNER_TAP_AT_2X))
        self.assertAlmostEqual(sum(equaliser.taps), 1.0, places=15)
        self.assertLess(-20 * math.log10(1 - worst), 0.0973)
        self.assertEqual(equaliser.latency_steps, 3)
        product = [(1 + 2 * math.cos(w)) / 3 * equaliser.response(w)
                   for w in (2 * math.pi * 0.25 * k / 5000 for k in range(5001))]   # to the host's Nyquist
        self.assertLess(20 * math.log10(max(product)), 0.0973)
        for frequency in (100.0, 1000.0, 5000.0, 10000.0, 15000.0, 18000.0, 20000.0):
            gain = self.shaper_gain(2, 96000.0, frequency)
            self.assertLess(abs(20 * math.log10(abs(gain))), 0.0973, msg=frequency)
            self.assertLess(abs(gain.imag), 1e-6, msg=f"{frequency}: linear phase, latency_steps late")
        with self.assertRaises(BuildError):
            equaliser.call(["a", "b", "c", "d"])

    def test_at_1x_there_is_no_equaliser_and_nothing_is_lifted_to_nyquist(self):
        # at 1x the output is ADAA2's raw mean, one step late: the 3-tap mean (1 + 2 cos w) / 3, never above 0 dB to
        # Nyquist, within 0.3 dB to 2.4 kHz at 48 kHz (-1.3 dB at 5 kHz, -5.9 at 10 kHz, -9.5 at 24 kHz). The 2x
        # equaliser here was within 0.1 dB to 10 kHz but +6.4 dB at 24 kHz, and lifted the aliases with it (the module
        # docstring's measurements: every equaliser at 1x lost more alias suppression than it gained)
        equaliser = second_order_equaliser(1, "test")
        self.assertEqual((equaliser.taps, equaliser.latency_steps, equaliser.functions()), ((1.0,), 1, {}))
        self.assertEqual(equaliser.call(["now"]), "now")
        rate = 48000.0
        for frequency in (100.0, 1000.0, 2400.0, 5000.0, 10000.0, 15000.0, 17000.0, 20000.0, 23900.0):
            gain = self.shaper_gain(1, rate, frequency)
            mean = (1 + 2 * math.cos(2 * math.pi * frequency / rate)) / 3
            self.assertAlmostEqual(gain.real, mean, delta=1e-9, msg=frequency)
            self.assertLess(abs(gain.imag), 1e-6, msg=frequency)
            self.assertLessEqual(abs(gain), 1.0, msg=frequency)
            if frequency <= 2400.0:
                self.assertLess(-20 * math.log10(abs(gain)), 0.3, msg=frequency)

    def test_the_oversampling_must_be_known(self):
        table = PiecewiseLinearTable("clip", self.CLIP)
        with self.assertRaises(TypeError):                     # never a default
            AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=2)
        for unknown in (3, 4, 0, True, 2.0, None):
            with self.assertRaises(BuildError, msg=unknown):
                AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=2, oversampling=unknown)
            with self.assertRaises(BuildError, msg=unknown):
                second_order_equaliser(unknown, "test")

    def test_second_order_needs_a_continuous_table(self):
        jumping = PiecewiseLinearTable("jump", [(-math.inf, 0.0, -1.0), (0.0, 0.0, 1.0)])
        self.assertFalse(jumping.is_continuous)
        self.assertNotIn(f"{jumping.function_name}_second_order_mean", jumping.functions())
        with self.assertRaises(BuildError):
            jumping.second_order_mean_call("a", "b", "c")
        with self.assertRaises(BuildError):
            AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=jumping, order=2, oversampling=2)
        with self.assertRaises(BuildError):
            AntiderivativePiecewiseLinearShaper("shaper", input="in1",
                                                table=PiecewiseLinearTable("clip", self.CLIP), order=3, oversampling=1)

    def test_two_tables_are_two_functions(self):
        one, other = PiecewiseLinearTable("clip", self.CLIP), PiecewiseLinearTable("clip", self.CLIP[:2] + [(0.6, 0.0, 0.6)])
        self.assertNotEqual(one.function_name, other.function_name)
        self.assertEqual(one.function_name, PiecewiseLinearTable("clip", list(self.CLIP)).function_name)
        blocks = [AntiderivativePiecewiseLinearShaper("a", input="in1", table=one, oversampling=1),
                  AntiderivativePiecewiseLinearShaper("b", input="in1", table=other, oversampling=1)]
        harness(blocks, {}, ["a_out + b_out"])       # both in one patch: no clash

    def test_a_bad_table_fails_the_build(self):
        with self.assertRaises(BuildError):
            PiecewiseLinearTable("clip", self.CLIP[1:])                   # not from -inf
        with self.assertRaises(BuildError):
            PiecewiseLinearTable("clip", [self.CLIP[0], self.CLIP[2], self.CLIP[1]])   # not rising


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


class SidechainStylePumpTests(unittest.TestCase):
    SAMPLERATE = 8000.0
    BPM = 120.0
    DIVISION_BEATS = 0.5                    # 250 ms
    DIVISION_MS = 60000 / BPM * DIVISION_BEATS
    SETTINGS = {"following_live": 0.0, "bpm": BPM, "division_beats": DIVISION_BEATS, "depth": 1.0, "attack_ms": 6.0,
                "release_fraction": 0.55, "curve": 0.5, "chop": 0.0}

    def pump(self, **settings):
        values = dict(self.SETTINGS, **settings)
        block = SidechainStylePump("pump", live_beat_position="in1", **{name: name for name in values})
        return harness([block], values, ["pump_gain", "pump_duck"], samplerate=self.SAMPLERATE)

    def model(self, phase, **settings):
        values = dict(self.SETTINGS, **settings)
        return sidechain_style_pump.pump_duck(phase, values["attack_ms"], self.DIVISION_MS,
                                              values["release_fraction"], values["curve"])

    def test_on_its_own_clock_the_duck_is_the_displays_shape(self):
        samples_per_division = int(self.SAMPLERATE * self.DIVISION_MS / 1000)
        for settings in ({}, {"attack_ms": 1.0, "curve": 0.0}, {"attack_ms": 40.0, "release_fraction": 0.2, "curve": 1.0}):
            duck = self.pump(**settings).run(3 * samples_per_division, [[0.0] * (3 * samples_per_division)])[1]
            for n, value in enumerate(duck):
                phase = ((n + 1) / samples_per_division) % 1.0
                self.assertAlmostEqual(value, self.model(phase, **settings), places=9, msg=(settings, n))

    def test_following_live_the_duck_is_the_displays_shape_at_live_s_phase(self):
        total = int(self.SAMPLERATE * 2)
        beats = [(n * self.BPM / 60 / self.SAMPLERATE) % 1.0 for n in range(total)]       # a beat ramp 0..1, as plugphasor~
        duck = self.pump(following_live=1.0).run(total, [beats])[1]
        for n in range(total // 2, total):          # after the hand-over (20 ms) has finished
            self.assertAlmostEqual(duck[n], self.model((beats[n] / self.DIVISION_BEATS) % 1.0), places=6, msg=n)

    def test_the_duck_is_0_at_the_start_1_at_the_end_of_the_attack_and_0_from_the_recovery_s_end(self):
        samples_per_division = int(self.SAMPLERATE * self.DIVISION_MS / 1000)
        duck = self.pump().run(samples_per_division, [[0.0] * samples_per_division])[1]
        self.assertLess(duck[0], 0.2)
        self.assertAlmostEqual(max(duck), 1.0, delta=0.01)
        self.assertEqual(duck[int(samples_per_division * 0.6):-1], [0.0] * len(duck[int(samples_per_division * 0.6):-1]))

    def test_depth_scales_the_dip_and_depth_0_is_unity(self):
        samples = int(self.SAMPLERATE)
        quiet = self.pump(depth=0.0).run(samples, [[0.0] * samples])[0]
        self.assertEqual(quiet, [1.0] * samples)
        half = self.pump(depth=0.5).run(samples, [[0.0] * samples])[0]
        self.assertAlmostEqual(min(half), 0.5, delta=0.02)
        self.assertGreater(min(half), 0.49)

    def test_the_gate_is_open_on_the_beat_and_shut_to_the_depth_after_the_release(self):
        samples_per_division = int(self.SAMPLERATE * self.DIVISION_MS / 1000)
        gain = self.pump(chop=1.0, depth=0.8).run(2 * samples_per_division, [[0.0] * (2 * samples_per_division)])[0]
        self.assertAlmostEqual(max(gain), 1.0, delta=0.02)
        late = gain[int(samples_per_division * 0.7):samples_per_division - 5]
        self.assertAlmostEqual(min(late), 0.2, places=3)
        self.assertAlmostEqual(max(late), 0.2, places=3)

    def test_no_step_reaches_the_gain_when_live_starts_or_stops(self):
        program = self.pump()
        total = int(self.SAMPLERATE * 2)
        beats = [(0.37 + n * self.BPM / 60 / self.SAMPLERATE) % 1.0 for n in range(total)]     # Live elsewhere in the beat
        gains = []
        for follow in (0.0, 1.0, 0.0):
            program.set_param("following_live", follow)
            gains += program.run(total // 4, [beats[:total // 4]])[0]
        steepest_step = max(abs(b - a) for a, b in zip(gains, gains[1:]))
        # the quarter-sine ramp in over 6 ms is 0.2 a sample at 8 kHz at its steepest; the hand-over adds no jump
        self.assertLess(steepest_step, 0.16)

    def test_the_display_script_is_the_same_shape(self):
        script = sidechain_style_pump.response_script_code()
        for phase, attack_ms, division_ms, release, curve in ((0.0, 6, 250, 0.55, 0.5), (0.01, 6, 250, 0.55, 0.5),
                                                                (0.3, 6, 250, 0.55, 0.5), (0.9, 6, 250, 0.55, 0.5),
                                                                (0.1, 40, 62.5, 0.2, 1.0), (0.5, 1, 1000, 0.95, 0.0)):
            value = float(es5.evaluate(script + f"\nsidechainPumpDuck({phase}, {attack_ms}, {division_ms}, {release}, {curve})"))
            self.assertAlmostEqual(value, sidechain_style_pump.pump_duck(phase, attack_ms, division_ms, release, curve),
                                   places=9)


def third_difference_rms(signal):
    """RMS of y[n] - 3y[n-1] + 3y[n-2] - y[n-3]: a steep high-pass that a smooth signal barely passes and a step
    (a zipper) passes whole."""
    values = [signal[i] - 3 * signal[i - 1] + 3 * signal[i - 2] - signal[i - 3] for i in range(3, len(signal))]
    return math.sqrt(sum(v * v for v in values) / len(values))


class ZeroDelayOnePoleFilterTests(unittest.TestCase):
    SAMPLERATE = 22050.0

    def test_small_signals_are_the_prewarped_analog_one_pole(self):
        for cutoff in (120.0, 1000.0, 7000.0):
            for frequency in (cutoff / 3, cutoff, min(cutoff * 2.5, 0.4 * self.SAMPLERATE)):
                program = harness([ZeroDelayOnePoleFilter("pole", input="in1", cutoff_hz="cutoff")], {"cutoff": cutoff},
                                  ["pole_lowpass", "pole_highpass"], samplerate=self.SAMPLERATE)
                sine = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(8820)]
                outputs = program.run(8820, [sine])
                expected = one_pole_small_signal_response(frequency, cutoff, self.SAMPLERATE)
                for name, output in zip(("lowpass", "highpass"), outputs):
                    with self.subTest(cutoff=cutoff, frequency=frequency, output=name):
                        measured = complex_amplitude_at(output[4410:], frequency, self.SAMPLERATE) / \
                            complex_amplitude_at(sine[4410:], frequency, self.SAMPLERATE)
                        self.assertLess(abs(measured - expected[name]), 2e-4)

    def test_low_pass_plus_high_pass_is_the_input(self):
        program = harness([ZeroDelayOnePoleFilter("pole", input="in1", cutoff_hz="20 + 9000 * (0.5 + 0.5 * sin(in1 * 300))")],
                          {}, ["pole_lowpass + pole_highpass"], samplerate=self.SAMPLERATE)
        signal = [math.sin(0.37 * n) + 0.5 * math.sin(2.9 * n) for n in range(2000)]
        self.assertLess(max(abs(a - b) for a, b in zip(program.run(2000, [signal])[0], signal)), 1e-12)

    def test_it_says_what_it_is_given_wrong(self):
        for bad in ("0", "-5", "inf", "nan"):
            with self.subTest(value=bad), self.assertRaises(BuildError):
                ZeroDelayOnePoleFilter("pole", input="in1", cutoff_hz=bad)
        with self.assertRaises(BuildError):
            ZeroDelayOnePoleFilter("pole", input="in1", cutoff_hz="100").response_statements("allpass")


class ZeroDelayAllpassCascadeTests(unittest.TestCase):
    SAMPLERATE = 44100.0
    # cutoffs jumping across the whole band every sample, each section its own way
    JUMPING = "20 + 20000 * (0.5 + 0.5 * sin(in2 * {rate}))"

    def cascade(self, stages, params, outputs=("cascade_out",), num_inputs=1, **options):
        return harness([ZeroDelayAllpassCascade("cascade", input="in1", stages=stages, **options)], params,
                       list(outputs), num_inputs=num_inputs, samplerate=self.SAMPLERATE)

    def test_the_magnitude_is_exactly_one(self):
        # six first-order sections spread over the band and two second-order ones: the impulse response's energy is
        # the mean of |H|^2 over the band (Parseval), exactly 1 for an all-pass; sines pass at unit level; and the
        # response is the prewarped analog all-passes' (the Python model)
        cutoffs = (90.0, 300.0, 700.0, 1500.0, 4000.0, 11000.0)
        stages = [FirstOrderAllpassStage(f"{cutoff!r}") for cutoff in cutoffs]
        stages += [SecondOrderAllpassStage("800", "6"), SecondOrderAllpassStage("5000", "0.6")]
        model = [(cutoff,) for cutoff in cutoffs] + [(800.0, 6.0), (5000.0, 0.6)]
        impulse_response = self.cascade(stages, {}).run(44100, [[1.0] + [0.0] * 44099])[0]
        self.assertAlmostEqual(sum(v * v for v in impulse_response), 1.0, delta=1e-9)
        for frequency in (100.0, 800.0, 6000.0):
            sine = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(17640)]
            out = self.cascade(stages, {}).run(17640, [sine])[0]
            with self.subTest(frequency=frequency):
                measured = complex_amplitude_at(out[8820:], frequency, self.SAMPLERATE) / \
                    complex_amplitude_at(sine[8820:], frequency, self.SAMPLERATE)
                self.assertAlmostEqual(20 * math.log10(abs(measured)), 0.0, delta=0.001)
                self.assertLess(abs(measured - cascade_small_signal_response(frequency, model, self.SAMPLERATE)), 2e-4)

    def test_the_phase_at_the_corner(self):
        # a first-order section is -90 degrees at its cutoff, a second-order one -180 (prewarped: exact there)
        for stage, expected in ((FirstOrderAllpassStage("cutoff"), -90.0), (SecondOrderAllpassStage("cutoff", "0.7"), 180.0),
                                (SecondOrderAllpassStage("cutoff", "5"), 180.0)):
            for cutoff in (250.0, 2500.0, 15000.0):
                sine = [math.sin(2 * math.pi * cutoff * n / self.SAMPLERATE) for n in range(8820)]
                out = self.cascade([stage], {"cutoff": cutoff}).run(8820, [sine])[0]
                with self.subTest(stage=stage, cutoff=cutoff):
                    measured = phase_degrees(out[4410:], sine[4410:], cutoff, self.SAMPLERATE)
                    self.assertLess(abs((measured - expected + 180) % 360 - 180), 0.05)

    def test_feedback_peaks_where_the_phase_is_a_whole_turn(self):
        # four first-order sections are -360 degrees at their cutoff: with feedback k, the output there is 1 / (1 - k)
        stages = [FirstOrderAllpassStage("1000")] * 4
        sine = [math.sin(2 * math.pi * 1000.0 * n / self.SAMPLERATE) for n in range(17640)]
        for feedback in (0.8, 0.5, -0.8):
            out = self.cascade(stages, {"k": feedback}, feedback="k").run(17640, [sine])[0]
            with self.subTest(feedback=feedback):
                self.assertAlmostEqual(amplitude_at(out[8820:], 1000.0, self.SAMPLERATE) * (1 - feedback), 1.0,
                                       delta=0.002)

    def test_lossless_however_the_cutoffs_move(self):
        # first- and second-order sections whose cutoffs jump across the band every sample: energy in = energy out
        # + energy left in the states, to rounding (each junction is a rotation)
        stages = [FirstOrderAllpassStage(self.JUMPING.format(rate=300 + 37 * i)) for i in range(4)]
        stages += [SecondOrderAllpassStage(self.JUMPING.format(rate=91), "0.5 + 8 * (0.5 + 0.5 * sin(in2 * 53))")]
        program = self.cascade(stages, {}, num_inputs=2)
        jumps = [math.sin(n * n * 0.001) for n in range(22050)]
        signal = [math.sin(n * 0.05) * (1 if n < 11025 else 0) for n in range(22050)]
        out = program.run(22050, [signal, jumps])[0]
        states = ["cascade_section_1_d", "cascade_section_2_d", "cascade_section_3_d", "cascade_section_4_d",
                  "cascade_section_5_d1", "cascade_section_5_d2"]
        left = sum(program.get_history(name) ** 2 for name in states)
        self.assertAlmostEqual((sum(v * v for v in out) + left) / sum(v * v for v in signal), 1.0, delta=1e-9)

    def test_the_tpt_all_pass_is_not_lossless_under_the_same_jumps(self):
        # why the sections are lattices: the TPT one-pole's LP - HP is the same all-pass at fixed cutoff, but with its
        # cutoff jumping every sample a unit-bounded input comes out 7.7 times as large (one section)
        jumps = [math.sin(n * n * 0.001) for n in range(22050)]
        tpt = harness([ZeroDelayOnePoleFilter("pole", input="in1", cutoff_hz=self.JUMPING.format(rate=300).replace("in2", "in1"))],
                      {}, ["pole_lowpass - pole_highpass"], samplerate=self.SAMPLERATE).run(22050, [jumps])[0]
        lattice = self.cascade([FirstOrderAllpassStage(self.JUMPING.format(rate=300))], {}, num_inputs=2).run(
            22050, [jumps, jumps])[0]
        self.assertGreater(max(abs(v) for v in tpt), 7.0)
        self.assertLess(max(abs(v) for v in lattice), 2.5)

    def test_stable_under_fast_modulation_in_a_loop(self):
        # twelve sections whose cutoffs jump across the band every sample, at 0.95 feedback with loop filters: bounded
        # (a lossless chain in a loop under 1); with a loop limit at full feedback the loop's input stays in the limit
        stages = [FirstOrderAllpassStage(self.JUMPING.format(rate=300 + 37 * i)) for i in range(12)]
        noise = [math.sin(n * n * 0.001) for n in range(22050)]
        out = self.cascade(stages, {}, num_inputs=2, feedback="0.95", coupling_highpass_hz="100",
                           feedback_lowpass_hz="18000").run(22050, [noise, noise])[0]
        self.assertTrue(all(math.isfinite(v) for v in out))
        self.assertLess(max(abs(v) for v in out), 1 / (1 - 0.95) * 3)
        limited = self.cascade(stages, {}, outputs=("cascade_loop_input",), num_inputs=2, feedback="0.999",
                               loop_limit=2.0).run(22050, [[3 * v for v in noise], noise])[0]
        self.assertLessEqual(max(abs(v) for v in limited), 2.0)

    def test_no_zipper_when_the_cutoff_glides(self):
        # a 500 Hz sine through six sections whose cutoff glides 200 Hz -> 5 kHz over half a second, written every
        # sample: the output's third difference (steps and corners) stays that of a smooth sine (onset left out). The
        # same glide written every 64 samples (a control-rate update) is caught by the measure
        samples = 22050
        sine = [math.sin(2 * math.pi * 500.0 * n / self.SAMPLERATE) for n in range(samples)]
        glide = [FirstOrderAllpassStage("200 * pow(25, min(in2, 1))")] * 6
        reference = third_difference_rms(sine[2205:])
        for step, smooth in ((1, True), (64, False)):
            time_signal = [(n - n % step) / samples for n in range(samples)]
            out = self.cascade(glide, {}, num_inputs=2).run(samples, [sine, time_signal])[0]
            ratio = third_difference_rms(out[2205:]) / reference
            with self.subTest(step=step):
                if smooth:
                    self.assertLess(ratio, 1.1, "a per-sample glide is smooth")
                else:
                    self.assertGreater(ratio, 3.0, "a stepped glide zips (the measure sees it)")

    def test_it_says_what_it_is_given_wrong(self):
        for stages in ([], ["1000"], [FirstOrderAllpassStage("1000"), 5], [FirstOrderAllpassStage(1000.0)],
                       [SecondOrderAllpassStage("1000", "")]):
            with self.subTest(stages=stages), self.assertRaises(BuildError):
                ZeroDelayAllpassCascade("cascade", input="in1", stages=stages)
        for limit in (0, -1.0, "2", True):
            with self.subTest(loop_limit=limit), self.assertRaises(BuildError):
                ZeroDelayAllpassCascade("cascade", input="in1", stages=[FirstOrderAllpassStage("1000")], loop_limit=limit)


class LedDrivenPhotocellTests(unittest.TestCase):
    SAMPLERATE = 22050.0
    LAW = dict(law_scale_ohms=3.464, law_exponent=1.4, law_floor_ohms=1136.212, darkest_current_amps=10e-6,
               release_from_amps=10e-3, release_to_amps=10e-6)

    def cell(self, attack_ms=3.0, release_ms=50.0):
        block = LedDrivenPhotocell("cell", drive_current_amps="in1", attack_ms=repr(attack_ms),
                                   release_ms=repr(release_ms), **self.LAW)
        return block, harness([block], {}, ["cell_current", "cell_resistance"], samplerate=self.SAMPLERATE)

    def test_held_it_settles_on_the_law(self):
        block, program = self.cell()
        for current in (0.1e-3, 1e-3, 10e-3):
            resistance = program.run(4410, [[current] * 4410])[1][-1]
            with self.subTest(current=current):
                self.assertAlmostEqual(resistance / block.resistance_at(current), 1.0, delta=1e-6)

    def test_it_lights_with_the_attack_time(self):
        _, program = self.cell(attack_ms=3.0)
        current = program.run(441, [[10e-3] * 441])[0]
        at_attack = current[round(3.0e-3 * self.SAMPLERATE) - 1]
        self.assertAlmostEqual((at_attack - 10e-6) / (10e-3 - 10e-6), 1 - math.exp(-1), delta=0.01)

    def test_it_goes_dark_over_the_release_time_slower_than_it_lit(self):
        _, program = self.cell(attack_ms=3.0, release_ms=50.0)
        program.run(2205, [[10e-3] * 2205])
        current = program.run(2205, [[0.0] * 2205])[0]
        # undriven, 1/I = 1/I0 + c t with c = (1/I_to - 1/I_from) / release: at the release time it reaches I_to
        at_release = current[round(50e-3 * self.SAMPLERATE) - 1]
        self.assertAlmostEqual(at_release / 10e-6, 1.0, delta=0.02)
        # halfway in time it is far brighter than halfway in current would say: the power-law turn-off
        halfway = current[round(25e-3 * self.SAMPLERATE) - 1]
        self.assertAlmostEqual(1 / halfway, 0.5 * (1 / 10e-3 + 1 / 10e-6), delta=0.02 / 10e-6)

    def test_a_law_given_as_expressions_runs_as_the_same_law(self):
        # every law constant a run-time expression (here Params holding the numbers) renders what the numbers render
        block, program = self.cell()
        run_time = LedDrivenPhotocell("cell", drive_current_amps="in1", attack_ms="3.0", release_ms="50.0",
                                      **{name: name for name in self.LAW})
        moved = harness([run_time], dict(self.LAW), ["cell_current", "cell_resistance"], samplerate=self.SAMPLERATE)
        drive = [10e-3] * 1000 + [0.0] * 2000 + [1e-3] * 1000
        fixed_out, moved_out = program.run(len(drive), [drive]), moved.run(len(drive), [drive])
        for n in range(2):
            self.assertLess(max(abs(x - y) / abs(x) for x, y in zip(fixed_out[n][1:], moved_out[n][1:])), 1e-9)
        with self.assertRaises(BuildError):
            run_time.resistance_at(1e-3)
        moved.set_param("law_exponent", 1.0)
        settled = moved.run(4410, [[1e-3] * 4410])[1][-1]
        self.assertAlmostEqual(settled, 3.464 * 1e-3 ** -1.0 + 1136.212, delta=1e-6)

    def test_it_says_what_it_is_given_wrong(self):
        for name, bad in (("law_exponent", 0), ("darkest_current_amps", -1e-6), ("release_to_amps", 0.02),
                          ("law_floor_ohms", -1.0), ("law_scale_ohms", " ")):
            law = dict(self.LAW, **{name: bad})
            with self.subTest(name=name), self.assertRaises(BuildError):
                LedDrivenPhotocell("cell", drive_current_amps="in1", attack_ms="3", release_ms="50", **law)


class DrumEnvelopeTests(unittest.TestCase):
    SAMPLERATE = 8000.0

    def envelope(self, mode, attack_ms, decay_ms, burst_count=1, burst_spacing_ms=10.0):
        block = DrumEnvelope("env", hit="in1", mode="mode", attack_ms="attack", decay_ms="decay",
                             clap_burst_count="count", clap_burst_spacing_ms="spacing")
        program = harness([block], {"mode": mode, "attack": attack_ms, "decay": decay_ms, "count": burst_count,
                                    "spacing": burst_spacing_ms}, ["env_level", "env_stage"],
                          samplerate=self.SAMPLERATE)
        return program

    def run_hits(self, program, hits_at, samples):
        hits = [1.0 if n in hits_at else 0.0 for n in range(samples)]
        return program.run(samples, [hits])

    def samples(self, ms):
        return ms * self.SAMPLERATE / 1000

    def test_the_exponential_decay_falls_60_db_over_the_decay_time_then_ends(self):
        level, stage = self.run_hits(self.envelope(0, 0.0, 100.0), {0}, 4000)
        self.assertEqual(level[0], 1.0)                                  # attack 0: full force at the hit
        at_decay_time = level[round(self.samples(100.0))]
        self.assertAlmostEqual(20 * math.log10(at_decay_time), -drum_envelope.DECAY_SPAN_DB, delta=0.01)
        for n in range(1, 1500):                                         # a true exponential: a constant ratio
            self.assertAlmostEqual(level[n] / level[n - 1],
                                   drum_envelope.exponential_decay_factor_per_sample(100.0, self.SAMPLERATE),
                                   delta=1e-12)
        self.assertEqual(level[-1], 0.0)
        self.assertEqual(stage[-1], drum_envelope.STAGE_IDLE)

    def test_the_exponential_attack_is_the_decay_reversed_and_reaches_1_at_the_attack_time(self):
        level, _ = self.run_hits(self.envelope(0, 50.0, 100.0), {0}, 1000)
        attack_samples = self.samples(50.0)
        for n in range(round(attack_samples)):
            self.assertAlmostEqual(level[n], drum_envelope.exponential_rise(n / attack_samples), delta=1e-9, msg=n)
        self.assertAlmostEqual(level[round(attack_samples)], 1.0, delta=1e-12)
        self.assertLess(level[round(attack_samples / 2)], 0.05)          # slow first: reversed in time
        self.assertLess(level[round(attack_samples) + 1], 1.0)           # then the decay

    def test_the_linear_mode_is_straight_both_ways(self):
        level, stage = self.run_hits(self.envelope(1, 10.0, 50.0), {0}, 600)
        attack, decay = round(self.samples(10.0)), round(self.samples(50.0))
        for n in range(attack + 1):
            self.assertAlmostEqual(level[n], n / attack, delta=1e-12, msg=n)
        for n in range(decay):
            self.assertAlmostEqual(level[attack + n], 1 - n / decay, delta=1e-9, msg=n)
        self.assertEqual(level[attack + decay + 1], 0.0)
        self.assertEqual(stage[attack + decay + 1], drum_envelope.STAGE_IDLE)

    def test_a_restart_starts_the_attack_where_the_level_is(self):
        # a second hit mid-decay: the level at the hit is the level before it, and no step is bigger than the
        # attack's own steepest (exponential: its slope at the top, a / attack samples; linear: 1 / attack samples)
        for mode, steepest in ((0, drum_envelope.ATTACK_CURVATURE / (1 - math.exp(-drum_envelope.ATTACK_CURVATURE))),
                               (1, 1.0)):
            with self.subTest(mode=mode):
                level, _ = self.run_hits(self.envelope(mode, 5.0, 40.0), {0, 200}, 600)
                self.assertGreater(level[199], 0.01)
                # the hit's sample gives the level the decay had reached: no step
                self.assertLess(abs(level[200] - level[199]), 0.01)
                n = 201
                while level[n - 1] < 1.0:                                       # the attack, to its top
                    self.assertGreaterEqual(level[n] + 1e-12, level[n - 1], n)    # never drops after the hit
                    self.assertLess(level[n] - level[n - 1], 1.0001 * steepest / self.samples(5.0) + 1e-12, n)
                    n += 1
                self.assertLess(n, 200 + self.samples(5.0) + 2)
                self.assertEqual(max(level[200:300]), 1.0)

    def test_the_clap_burst_retriggers_count_times_then_decays(self):
        level, _ = self.run_hits(self.envelope(2, 0.0, 100.0, burst_count=4, burst_spacing_ms=10.0), {0}, 2000)
        spacing = round(self.samples(10.0))
        pulses = [n for n in range(2000) if level[n] == 1.0]
        self.assertEqual(pulses, [0, spacing, 2 * spacing, 3 * spacing])
        # between pulses each falls 60 dB over one spacing; after the last, 60 dB over the decay time
        self.assertAlmostEqual(20 * math.log10(level[spacing - 1]), -60.0 * (spacing - 1) / spacing, delta=0.01)
        after_last = level[3 * spacing + round(self.samples(100.0))]
        self.assertAlmostEqual(20 * math.log10(after_last), -drum_envelope.DECAY_SPAN_DB, delta=0.01)
        # a count of 1 is one pulse: the exponential envelope with attack 0
        single, _ = self.run_hits(self.envelope(2, 0.0, 100.0, burst_count=1), {0}, 2000)
        plain, _ = self.run_hits(self.envelope(0, 0.0, 100.0), {0}, 2000)
        self.assertEqual(single, plain)

    def test_the_mode_is_held_from_the_hit(self):
        program = self.envelope(1, 0.0, 50.0)
        level = self.run_hits(program, {0}, 100)[0]
        program.set_param("mode", 0)                                      # turned mid-note: still linear
        rest = program.run(100, [[0.0] * 100])[0]
        self.assertAlmostEqual(level[-1] - rest[0], 1 / self.samples(50.0), delta=1e-12)


class PitchModulatorTests(unittest.TestCase):
    SAMPLERATE = 8000.0

    def modulator(self, shape, amount=12.0, decay_ms=50.0, rate_hz=100.0, seed=12345.0, samplerate=None):
        block = PitchModulator("mod", hit="in1", shape="shape", amount="amount", decay_ms="decay", rate_hz="rate",
                               seed="seed")
        return harness([block], {"shape": shape, "amount": amount, "decay": decay_ms, "rate": rate_hz, "seed": seed},
                       ["mod_offset", "mod_frequency_ratio"], samplerate=samplerate or self.SAMPLERATE)

    @staticmethod
    def run_hits(program, hits_at, samples):
        return program.run(samples, [[1.0 if n in hits_at else 0.0 for n in range(samples)]])

    def test_the_decay_starts_at_the_amount_and_reaches_0_at_the_decay_time(self):
        offset, ratio = self.run_hits(self.modulator(SHAPES["decay"], amount=24.0, decay_ms=50.0), {0}, 800)
        decay_samples = 50.0 * self.SAMPLERATE / 1000
        for n in range(500):
            expected = 24.0 * exponential_rise(1 - n / decay_samples)
            self.assertAlmostEqual(offset[n], expected, delta=1e-9, msg=n)
            self.assertAlmostEqual(ratio[n], 2 ** (offset[n] / 12), delta=1e-12)
        self.assertEqual(offset[0], 24.0)
        self.assertEqual(offset[round(decay_samples) + 3], 0.0)

    def test_the_cyclic_shapes_are_their_waves_from_the_hit_and_restart_on_the_next(self):
        rate = 100.0
        step = rate / self.SAMPLERATE
        for name in ("sine", "triangle", "square", "saw_down"):
            with self.subTest(shape=name):
                offset, _ = self.run_hits(self.modulator(SHAPES[name], amount=5.0, rate_hz=rate), {0, 300}, 600)
                for start in (0, 300):
                    for n in range(start, start + 300):
                        phase = ((n - start) * step) % 1.0
                        near_an_edge = min(abs(phase - 0.5), phase, 1 - phase) < 3 * step
                        if name == "sine" or not near_an_edge:
                            self.assertAlmostEqual(offset[n], 5.0 * pitch_modulator_wave(SHAPES[name], phase),
                                                   delta=1e-9, msg=(start, n))
                self.assertAlmostEqual(offset[0], 5.0, delta=1e-12)
                self.assertAlmostEqual(offset[300], 5.0, delta=1e-12)

    def test_rate_0_holds_the_initial_offset(self):
        for name in ("sine", "triangle", "square", "saw_down"):
            offset, _ = self.run_hits(self.modulator(SHAPES[name], amount=-7.0, rate_hz=0.0), {0}, 200)
            self.assertTrue(all(abs(value + 7.0) < 1e-12 for value in offset), name)

    def test_audio_rate_square_and_saw_are_band_limited(self):
        # an ER-1-speed modulator (C7, 2093 Hz) at 44.1 kHz: the worst alias below 10 kHz re the fundamental, the
        # block's against the trivial wave's
        samplerate, fundamental = 44100.0, 2093.0
        for name, harmonics in (("square", range(3, 60, 2)), ("saw_down", range(2, 60))):
            with self.subTest(shape=name):
                offset, _ = self.run_hits(self.modulator(SHAPES[name], amount=1.0, rate_hz=fundamental,
                                                         samplerate=samplerate), {0}, 4096 + 1000)
                trivial = [pitch_modulator_wave(SHAPES[name], (n * fundamental / samplerate) % 1.0)
                           for n in range(4096 + 1000)]
                band_limited = worst_alias_db(offset[1000:], fundamental, harmonics, samplerate, 10000.0)
                naive = worst_alias_db(trivial[1000:], fundamental, harmonics, samplerate, 10000.0)
                self.assertLess(band_limited, -75.0)            # measured -76.3 (square), -77.0 (saw)
                self.assertLess(band_limited, naive - 50.0)     # the trivial waves: -24.6

    def test_random_at_rate_0_is_one_seeded_value_a_hit(self):
        hits = set(range(0, 4000, 40))
        offset, _ = self.run_hits(self.modulator(SHAPES["random"], amount=3.0, rate_hz=0.0), hits, 4000)
        values = [offset[n] for n in sorted(hits)]
        for start in sorted(hits):
            self.assertTrue(all(offset[n] == offset[start] for n in range(start, start + 40)), start)
        self.assertEqual(len(set(values)), len(values))                 # a new value every hit
        self.assertTrue(all(abs(value) <= 3.0 for value in values))
        self.assertAlmostEqual(sum(values) / len(values), 0.0, delta=0.5)
        # the same seed draws the same values; another seed others
        again, _ = self.run_hits(self.modulator(SHAPES["random"], amount=3.0, rate_hz=0.0), hits, 4000)
        self.assertEqual(again, offset)
        other, _ = self.run_hits(self.modulator(SHAPES["random"], amount=3.0, rate_hz=0.0, seed=999.0), hits, 4000)
        self.assertNotEqual([other[n] for n in sorted(hits)], values)

    def test_random_above_rate_0_is_low_passed_noise_of_the_same_spread(self):
        # its RMS is amount / sqrt(3) (a uniform draw's) at every rate, and it moves no faster than its cutoff
        for rate in (20.0, 200.0, 2000.0):
            with self.subTest(rate=rate):
                offset, _ = self.run_hits(self.modulator(SHAPES["random"], amount=3.0, rate_hz=rate), {0}, 80000)
                rms = math.sqrt(sum(value * value for value in offset) / len(offset))
                tolerance = 0.25 if rate == 20.0 else 0.08
                self.assertAlmostEqual(rms / (3.0 / math.sqrt(3)), 1.0, delta=tolerance)
        slow, _ = self.run_hits(self.modulator(SHAPES["random"], amount=3.0, rate_hz=20.0), {0}, 8000)
        fast, _ = self.run_hits(self.modulator(SHAPES["random"], amount=3.0, rate_hz=2000.0), {0}, 8000)
        mean_step = [sum(abs(s[n] - s[n - 1]) for n in range(1, 8000)) / 7999 for s in (slow, fast)]
        self.assertLess(mean_step[0], 0.2 * mean_step[1])


class SeededWhiteNoiseTests(unittest.TestCase):
    def noise(self, seed=0.0):
        return harness([SeededWhiteNoise("noise", seed="seed", restart="in1")], {"seed": seed},
                       ["noise_out", "noise_state"], samplerate=8000.0)

    def test_it_is_the_minimal_standard_generator(self):
        # Park & Miller, p. 1195: "z1 = 1 then z10001 = 1043618065" (seed 0 starts the state at 1)
        _, state = self.noise(0.0).run(10000, [[0.0] * 10000])
        self.assertEqual(state[-1], 1043618065.0)
        out, _ = self.noise(271828.0).run(2000, [[0.0] * 2000])
        self.assertEqual(out, park_miller_sequence(271828.0, 2000))

    def test_a_seed_restarts_it_and_so_does_restart(self):
        program = self.noise(5.0)
        first = program.run(100, [[0.0] * 100])[0]
        program.set_param("seed", 6.0)
        other = program.run(100, [[0.0] * 100])[0]
        program.set_param("seed", 5.0)
        again = program.run(100, [[0.0] * 100])[0]
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        restarted = program.run(150, [[0.0] * 50 + [1.0] + [0.0] * 99])[0]
        self.assertEqual(restarted[50:150], first)

    def test_it_is_white_and_uniform(self):
        out, _ = self.noise(123456789.0).run(100000, [[0.0] * 100000])
        mean = sum(out) / len(out)
        variance = sum((v - mean) ** 2 for v in out) / len(out)
        self.assertAlmostEqual(mean, 0.0, delta=0.01)
        self.assertAlmostEqual(variance, 1 / 3, delta=0.01)
        self.assertTrue(all(-1 < v < 1 for v in out))
        for lag in (1, 2, 3, 7):
            correlation = sum(out[n] * out[n - lag] for n in range(lag, len(out))) / len(out) / variance
            self.assertLess(abs(correlation), 0.02, lag)


class MetallicNoiseTests(unittest.TestCase):
    SAMPLERATE = 8000.0

    def source(self, pattern, tune_hz):
        return harness([LfsrMetallicNoise("metal", hit="in1", tune_hz="tune", pattern="pattern")],
                       {"tune": tune_hz, "pattern": pattern}, ["metal_out", "metal_register"],
                       samplerate=self.SAMPLERATE)

    def test_the_register_is_the_python_model(self):
        # clocked at the sample rate the register steps once a sample
        for pattern in (1, 29, 77, 142, 255):
            with self.subTest(pattern=pattern):
                _, register = self.source(pattern, self.SAMPLERATE).run(600, [[1.0] + [0.0] * 599])
                self.assertEqual(register, [float(state) for state in lfsr_cycle(pattern)])

    def test_each_pattern_is_its_own_tone_pattern(self):
        cycles = {}
        for pattern in range(1, 256):
            states = lfsr_cycle(pattern, steps=600)
            tail = states[300:]
            period = next(length for length in range(1, 300) if tail[length:] == tail[:-length])
            cycles[pattern] = tuple(state % 2 for state in tail[:period])
            self.assertNotIn(0, set(states))
        # never a constant output, and the output bit patterns are many different ones
        self.assertTrue(all(len(set(bits)) == 2 for bits in cycles.values()))
        self.assertGreater(len(set(cycles.values())), 100)

    def test_the_tune_pitches_it(self):
        # pattern 29's cycle at a tune of sr / 4: the output repeats every 4 x the cycle's length in samples
        states = lfsr_cycle(29, steps=600)[300:]
        period = next(length for length in range(1, 300) if states[length:] == states[:-length])
        out, _ = self.source(29, self.SAMPLERATE / 4).run(6000, [[1.0] + [0.0] * 5999])
        for n in range(3000, 3000 + 400):
            self.assertAlmostEqual(out[n], out[n + 4 * period], delta=1e-9)

    def test_a_hit_restarts_the_same_pattern(self):
        hits = [1.0 if n in (0, 1000) else 0.0 for n in range(2000)]
        out, _ = self.source(77, 1234.5).run(2000, [hits])
        self.assertEqual(out[1003:1990], out[3:990])

    def test_every_metallic_source_keeps_the_seam(self):
        # the interface an instrument (and the matcher) swaps sources by; two instances in one voice
        for source_type in METALLIC_NOISE_SOURCES:
            with self.subTest(source=source_type.__name__):
                first = source_type("metal_a", hit="in1", tune_hz="3000", pattern="77")
                second = source_type("metal_b", hit="in1", tune_hz="4100", pattern="142")
                program = harness([first, second], {}, ["metal_a_out", "metal_b_out"], samplerate=self.SAMPLERATE)
                a, b = program.run(4000, [[1.0] + [0.0] * 3999])
                for out in (a, b):
                    self.assertLess(max(abs(v) for v in out), 1.3)
                    self.assertGreater(sum(v * v for v in out) / len(out), 0.5)
                self.assertNotEqual(a, b)


class BellEqualizerTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def bell(self, *blocks):
        return harness(list(blocks) or [BellEqualizer("bell", input="in1", frequency_hz="centre", gain_db="gain",
                                                      q="q")],
                       {"centre": 1000.0, "gain": 0.0, "q": 1.0}, ["bell_out"], samplerate=self.SAMPLERATE)

    def gain_db_at(self, frequency, centre, gain_db, q):
        program = self.bell()
        for name, value in (("centre", centre), ("gain", gain_db), ("q", q)):
            program.set_param(name, value)
        samples = 22050          # half a second to settle (Q 20 at 100 Hz rings with tau 64 ms), the rest measured
        sine = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(2 * samples)]
        out = program.run(2 * samples, [sine])[0]
        return 20 * math.log10(amplitude_at(out[samples:], frequency, self.SAMPLERATE)
                               / amplitude_at(sine[samples:], frequency, self.SAMPLERATE))

    def test_exact_at_the_centre(self):
        for centre in (100.0, 1000.0, 10000.0):
            for gain_db in (-24.0, 6.0, 40.0):
                self.assertAlmostEqual(self.gain_db_at(centre, centre, gain_db, 2.0), gain_db, delta=0.01,
                                       msg=(centre, gain_db))

    def test_small_signals_are_the_band_shelving_filter(self):
        for frequency in (60.0, 400.0, 700.0, 1400.0, 3000.0, 15000.0):
            for gain_db, q in ((12.0, 0.7), (-12.0, 4.0)):
                expected = 20 * math.log10(abs(bell_small_signal_response(frequency, 1000.0, gain_db, q,
                                                                          self.SAMPLERATE)))
                self.assertAlmostEqual(self.gain_db_at(frequency, 1000.0, gain_db, q), expected, delta=0.05,
                                       msg=(frequency, gain_db, q))

    def test_q_is_the_width_at_half_the_gain(self):
        # |H| = sqrt(G) (half the dB) where |1 - w^2| = w / Q: w = sqrt(1 + 1 / (4 Q^2)) +- 1 / (2 Q), on the
        # analog axis, mapped back through the prewarping
        centre, q, gain_db = 1000.0, 2.0, 18.0
        g = math.tan(math.pi * centre / self.SAMPLERATE)
        for sign in (-1, 1):
            w = math.sqrt(1 + 1 / (4 * q * q)) + sign / (2 * q)
            edge = self.SAMPLERATE / math.pi * math.atan(w * g)
            self.assertAlmostEqual(self.gain_db_at(edge, centre, gain_db, q), gain_db / 2, delta=0.02, msg=edge)

    def test_a_cut_undoes_the_same_boost_and_0_db_is_the_input(self):
        boost = BellEqualizer("boost", input="in1", frequency_hz="1000", gain_db="15", q="3")
        cut = BellEqualizer("bell", input="boost_out", frequency_hz="1000", gain_db="-15", q="3")
        noise = park_miller_sequence(4242.0, 4000)
        out = self.bell(boost, cut).run(4000, [noise])[0]
        self.assertLess(max(abs(x - y) for x, y in zip(out, noise)), 1e-9)
        flat = self.bell().run(4000, [noise])[0]
        self.assertEqual(flat, noise)


class HalfbandOversamplerTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def test_the_design_is_hiirs(self):
        # HIIR 1.40 oversampling.txt, "2x, 156 dB": 12 coefficients, transition 0.0472053, attenuation 156.686 dB
        published = (0.017347915108876406, 0.067150480426919179, 0.14330738338179819, 0.23745131944299824,
                     0.34085550201503761, 0.44601111310335906, 0.54753112652956148, 0.6423859124721446,
                     0.72968928615804163, 0.81029959388029904, 0.88644514917318362, 0.96150605146543733)
        for ours, theirs in zip(halfband_coefficients(12, 0.0472053), published):
            self.assertAlmostEqual(ours, theirs, delta=2e-7)
        self.assertAlmostEqual(halfband_attenuation_db(12, 0.0472053), 156.686, delta=0.001)
        self.assertAlmostEqual(halfband_attenuation_db(), 99.3, delta=0.05)
        with self.assertRaises(BuildError):
            halfband_coefficients(0, 0.04)
        with self.assertRaises(BuildError):
            HalfbandDownsampler("down", first="in1", second="in1", coefficients=(0.5, 1.2))

    def test_the_response_is_flat_in_the_pass_band_and_down_99_db_in_the_stop_band(self):
        coefficients = halfband_coefficients()
        for f in (0.0, 0.05, 0.1, 0.15, 0.2, 0.21):
            self.assertLess(abs(20 * math.log10(abs(halfband_response(f, coefficients)))), 1e-6, f)
        worst_stop = max(abs(halfband_response(0.29 + 0.21 * k / 400, coefficients)) for k in range(401))
        self.assertLess(20 * math.log10(worst_stop), -99.0)

    def downsampled(self, two_times_rate_signal):
        """`two_times_rate_signal`: a GenExpr expression of `t` (seconds) at twice the rate."""
        down = HalfbandDownsampler("down", first="first", second="second")
        first = two_times_rate_signal.replace("t_", "(count / samplerate)")
        second = two_times_rate_signal.replace("t_", "((count + 0.5) / samplerate)")
        code = gen_code_with_blocks(
            "/*GEN_BLOCK_FUNCTIONS*/\nHistory count(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
            f"first = {first};\nsecond = {second};\ncount = count + 1;\n/*DOWN*/\nout1 = down_out;\nout2 = first;\n",
            [down], "halfband harness")
        return GenProgram(code, 0, 2, samplerate=self.SAMPLERATE).run(8192 + 2000)

    def test_the_downsampler_stops_what_naive_decimation_folds(self):
        # a 30 kHz tone at 88.2 kHz: dropping every other sample folds it to 14.1 kHz at full level
        filtered, naive = self.downsampled("sin(twopi * 30000 * t_)")
        alias = self.SAMPLERATE - 30000.0
        self.assertGreater(amplitude_at(naive[2000:], alias, self.SAMPLERATE), 0.99)
        self.assertLess(20 * math.log10(amplitude_at(filtered[2000:], alias, self.SAMPLERATE)), -99.0)  # -113.5

    def test_an_fm_pair_at_2x_aliases_far_less_than_at_1x(self):
        # carrier 9 kHz, modulator 1.3 kHz, index 10: its sidebands (9000 + k 1300) run past Nyquist. Kept ones sit at
        # +-9000 mod 1300 (1200 or 100), the ones folded at 44.1 kHz at 44100 - those (0 or 1100): the worst folded
        # sideband below 20 kHz re the carrier, the 1x pair (the naive: every other sample of the 2x one) against the
        # 2x pair through the downsampler
        filtered, naive = self.downsampled("sin(twopi * 9000 * t_ + 10 * sin(twopi * 1300 * t_))")

        def worst_folded_db(signal):
            carrier = amplitude_at(signal, 9000.0, self.SAMPLERATE)
            kept = {9000 % 1300, -9000 % 1300}
            folded_residues = {(44100 - residue) % 1300 for residue in kept}
            self.assertFalse(kept & folded_residues)
            folded_lines = [f for f in range(100, 20000, 100) if f % 1300 in folded_residues]
            return 20 * math.log10(max(amplitude_at(signal, f, self.SAMPLERATE) for f in folded_lines) / carrier)
        at_1x, at_2x = worst_folded_db(naive[2000:]), worst_folded_db(filtered[2000:])
        self.assertGreater(at_1x, -15.0)                    # measured -11.8 dB
        self.assertLess(at_2x, -80.0)                       # measured -84.1 dB

    def test_up_then_down_is_the_input_late(self):
        up = HalfbandUpsampler("up", input="in1")
        down = HalfbandDownsampler("down", first="up_first", second="up_second")
        program = harness([up, down], {}, ["down_out", "up_first", "up_second"], samplerate=self.SAMPLERATE)
        for frequency in (100.0, 1000.0, 15000.0):
            sine = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(8820)]
            out = program.run(8820, [sine])[0]
            gain = amplitude_at(out[4410:], frequency, self.SAMPLERATE) / amplitude_at(sine[4410:], frequency,
                                                                                        self.SAMPLERATE)
            self.assertAlmostEqual(20 * math.log10(gain), 0.0, delta=1e-3, msg=frequency)
        # the latency at low frequencies (the phase delay at 100 Hz, base-rate samples)
        sine = [math.sin(2 * math.pi * 100.0 * n / self.SAMPLERATE) for n in range(8820)]
        out = program.run(8820, [sine])[0]
        delay = -phase_degrees(out[4410:], sine[4410:], 100.0, self.SAMPLERATE) / 360 * self.SAMPLERATE / 100.0
        self.assertAlmostEqual(delay, HALFBAND_ROUND_TRIP_LATENCY_SAMPLES, delta=0.05)
        # the upsampler's image (44.1 kHz - f, in the 88.2 kHz stream) is gone
        sine = [math.sin(2 * math.pi * 5000.0 * n / self.SAMPLERATE) for n in range(8820)]
        _, first, second = program.run(8820, [sine])
        stream = [value for pair in zip(first, second) for value in pair]
        image = amplitude_at(stream[8820:], self.SAMPLERATE - 5000.0, 2 * self.SAMPLERATE)
        self.assertLess(20 * math.log10(image), -95.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

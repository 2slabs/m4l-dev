"""The kit's techniques (m4l_dev/techniques/): each technique's claims, rendered through our GenExpr renderer
(m4l_dev/genexpr.py: ours, not Max's compiler). Each claim runs on a small harness program around one technique
(tests/gen_block_harness.py), at the lowest sample rate that still tests it, so the whole file takes seconds. Standard
library only."""
import cmath
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
from m4l_dev.techniques.antiderivative_antialiasing_equaliser import (  # noqa: E402
    ADAA_EQUALISER_EDGE_AT_2X, AntiderivativeAntialiasingEqualiser, adaa_equaliser_decision, adaa_equaliser_remez_design,
    checked_equaliser_taps)
from m4l_dev.techniques.antiderivative_piecewise_linear_shaper import (  # noqa: E402
    AntiderivativePiecewiseLinearShaper, PiecewiseLinearMotion, PiecewiseLinearTable)
from m4l_dev.techniques.antiderivative_tanh_saturator import (AntiderivativeTanhSaturator,  # noqa: E402
                                                              AntiderivativeTanhSaturatorLinearTwin)
from m4l_dev.techniques.band_limited_edges import BandLimitedEdges  # noqa: E402
from m4l_dev.techniques.knee_soft_clip import KneeSoftClip  # noqa: E402
from m4l_dev.techniques import sidechain_style_pump  # noqa: E402
from m4l_dev.techniques.sidechain_style_pump import SidechainStylePump  # noqa: E402


from m4l_dev.techniques.led_driven_photocell import LedDrivenPhotocell  # noqa: E402
from m4l_dev.techniques.tape_style_echo import (STEREO_MODES, WIDE_RIGHT_RATIO, TapeStyleEcho,  # noqa: E402
                                               TapeStyleEchoTapeWriter)
from m4l_dev.gen_blocks import Technique  # noqa: E402
from m4l_dev.techniques.histories_start_at_their_targets import HistoriesStartAtTheirTargets  # noqa: E402
from m4l_dev.techniques.zero_delay_allpass_cascade import (FirstOrderAllpassStage,  # noqa: E402
                                                           SecondOrderAllpassStage, ZeroDelayAllpassCascade)
from m4l_dev.techniques.zero_delay_allpass_cascade import \
    small_signal_response as cascade_small_signal_response  # noqa: E402
from m4l_dev.techniques.zero_delay_ladder_filter import (LINEAR_FEEDBACK_AT_FULL_RESONANCE,  # noqa: E402
                                                         ZeroDelayLadderFilter, response_script_code,
                                                         small_signal_magnitude)
from m4l_dev.techniques.zero_delay_one_pole_filter import ZeroDelayOnePoleFilter  # noqa: E402
from m4l_dev.techniques.zero_delay_one_pole_filter import \
    small_signal_response as one_pole_small_signal_response  # noqa: E402
from m4l_dev.techniques.zero_delay_state_variable_filter import (ZeroDelayStateVariableFilter,  # noqa: E402
                                                                 ring_time_constant_seconds, small_signal_response)
from m4l_dev.render_comparison import assert_renders_similar, renders_are_similar  # noqa: E402
from m4l_dev.model_accuracy import assert_matches_model  # noqa: E402
from m4l_dev.techniques import drum_envelope  # noqa: E402
from m4l_dev.techniques.bell_equalizer import BellEqualizer  # noqa: E402
from m4l_dev.techniques.bell_equalizer import small_signal_response as bell_small_signal_response  # noqa: E402
from m4l_dev.techniques.defined_latency_pad import (THIRAN_MAXIMUM_ORDER,  # noqa: E402
                                                    THIRAN_PHASE_DELAY_ERROR_BOUNDS, DefinedLatency,
                                                    DefinedLatencyPad)
from m4l_dev.techniques.drum_envelope import DrumEnvelope, exponential_rise  # noqa: E402
from m4l_dev.techniques.halfband_oversampler import (ControlsAtTheUpsampledSteps, HalfbandDownsampler,  # noqa: E402
                                                     HalfbandLinearPhaseDownsampler,
                                                     HalfbandUpsampler, halfband_attenuation_db, halfband_coefficients,
                                                     halfband_phase_delay_doubled_rate_samples, halfband_response,
                                                     linear_phase_halfband_response,
                                                     linear_phase_halfband_taps)
from m4l_dev.techniques.metallic_noise import METALLIC_NOISE_SOURCES, LfsrMetallicNoise, lfsr_cycle  # noqa: E402
from m4l_dev.techniques.pitch_modulator import SHAPES, PitchModulator  # noqa: E402
from m4l_dev.techniques.pitch_modulator import wave as pitch_modulator_wave  # noqa: E402
from m4l_dev.techniques.seeded_white_noise import SeededWhiteNoise, park_miller_sequence  # noqa: E402
from gen_block_harness import (amplitude_at, cents, coherent_frequency, coherent_worst_alias_db,  # noqa: E402
                               complex_amplitude_at, equalised_adaa_outputs, exact_second_order_mean, folded,
                               frequency_by_zero_crossings, harness, phase_degrees, worst_alias_db)


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
        for linear in (False, True):
            for frequency, cutoff, resonance in ((100.0, 700.0, 0.3), (700.0, 700.0, 1.0), (15000.0, 30000.0, 0.5)):
                value = float(es5.evaluate(script + f"\nladderResponse({frequency}, {cutoff}, "
                                           f"ladderFeedbackGain({resonance}, {str(linear).lower()}), 48000)"))
                self.assertAlmostEqual(value, small_signal_magnitude(frequency, cutoff, resonance, 48000.0, linear),
                                       places=9, msg=(linear, frequency))


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
        assert_renders_similar(fresh, first + used.run(len(saw) - 1, [saw[1:]])[0], self.SAMPLERATE, "after a reset")


class ZeroDelayLadderFilterLinearTests(unittest.TestCase):
    """The ladder's linear form (linear=True): eq. 5.8 with no tanh, k under 4 (references/dsp.md)."""
    SAMPLERATE = 44100.0

    def ladder(self, cutoff, resonance):
        program = harness([ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="cutoff", resonance="resonance",
                                                 linear=True)],
                          {"cutoff": 1000.0, "resonance": 0.0}, ["ladder_out"], samplerate=self.SAMPLERATE)
        program.set_param("cutoff", cutoff)
        program.set_param("resonance", resonance)
        return program

    def test_its_output_scales_with_its_input_at_any_level(self):
        # no harmonics, no compression: a saw at 1e-3 and at 30 (+90 dB) come out in the same proportion
        saw = [((i * 220.0 / self.SAMPLERATE) % 1) * 2 - 1 for i in range(4410)]
        for resonance in (0.0, 0.8, 1.0):
            quiet = self.ladder(2000.0, resonance).run(len(saw), [[1e-3 * v for v in saw]])[0]
            loud = self.ladder(2000.0, resonance).run(len(saw), [[30.0 * v for v in saw]])[0]
            worst = max(abs(b / 30.0 - a / 1e-3) for a, b in zip(quiet, loud))
            self.assertLess(worst, 1e-9 * max(abs(a / 1e-3) for a in quiet), resonance)

    def test_small_signals_and_loud_ones_follow_the_display_s_response(self):
        for resonance in (0.5, 1.0):
            for level in (1e-3, 10.0):
                for frequency in (200.0, 1900.0, 5000.0):
                    sine = [level * math.sin(2 * math.pi * frequency * i / self.SAMPLERATE) for i in range(44100)]
                    out = self.ladder(2000.0, resonance).run(len(sine), [sine])[0][22050:]
                    measured = amplitude_at(out, frequency, self.SAMPLERATE) / level
                    expected = small_signal_magnitude(frequency, 2000.0, resonance, self.SAMPLERATE, linear=True)
                    self.assertAlmostEqual(20 * math.log10(measured), 20 * math.log10(expected), delta=0.05,
                                           msg=(resonance, level, frequency))

    def test_at_full_resonance_it_rings_out_and_never_sings(self):
        # k 3.9: -60 dB in 0.87 s at 200 Hz (the poles' decay), so 2 s on it is under -120 dB of its loudest
        for cutoff in (200.0, 3000.0, 12000.0):
            kick = [0.5] * 20 + [0.0] * 88180
            out = self.ladder(cutoff, 1.0).run(len(kick), [kick])[0]
            loudest = max(abs(v) for v in out)
            self.assertLess(max(abs(v) for v in out[-500:]), 1e-6 * loudest, cutoff)

    def test_its_k_at_full_resonance_is_under_self_oscillation(self):
        ladder = ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="1000", resonance="1", linear=True)
        self.assertEqual(ladder.feedback_at_full_resonance, LINEAR_FEEDBACK_AT_FULL_RESONANCE)
        self.assertLess(LINEAR_FEEDBACK_AT_FULL_RESONANCE, 4.0)
        self.assertNotIn("tanh(", ladder.statements())
        self.assertEqual(ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="1000", resonance="1")
                         .statements().count("tanh("), 1)

    def test_the_pass_band_is_the_ladder_s_own(self):
        for resonance in (0.0, 0.5, 1.0):
            sine = [1e-3 * math.sin(2 * math.pi * 60.0 * i / self.SAMPLERATE) for i in range(8820)]
            level = amplitude_at(self.ladder(8000.0, resonance).run(len(sine), [sine])[0][4410:], 60.0,
                                 self.SAMPLERATE) / 1e-3
            self.assertAlmostEqual(20 * math.log10(level),
                                   -20 * math.log10(1 + LINEAR_FEEDBACK_AT_FULL_RESONANCE * resonance), delta=0.02)

    def test_linear_is_a_bool(self):
        with self.assertRaises(BuildError):
            ZeroDelayLadderFilter("ladder", input="in1", cutoff_hz="1000", resonance="0", linear=1)


def equaliser_of(order, oversampling):
    return AntiderivativeAntialiasingEqualiser("e", raw_mean="in1", order=order, oversampling=oversampling)


class AntiderivativeAntialiasingEqualiserTests(unittest.TestCase):
    """The kit's one ADAA equaliser (antiderivative_antialiasing_equaliser.py): one design function, one table of
    decisions by (order, oversampling), used by the tanh saturator and the piecewise-linear shaper."""

    def test_the_2x_taps_are_the_design_functions_and_flat_to_the_edge(self):
        # first order: the product with cos(w / 2) within 0.0099 dB up to 5/24 of the rate; second order: with
        # (1 + 2 cos w) / 3 within 0.0972 dB, and never above that up to the host's Nyquist (1/4 of the 2x rate)
        for order, ripple_db in ((1, 0.0100), (2, 0.0973)):
            equaliser = equaliser_of(order, 2)
            taps, worst = adaa_equaliser_remez_design(order, ADAA_EQUALISER_EDGE_AT_2X, 2)
            for designed, kept in zip(taps, equaliser.taps):
                # kept to generated_number's 10 significant digits
                self.assertAlmostEqual(designed, kept, delta=5e-10 * abs(designed), msg=order)
            self.assertEqual(equaliser.edge_cycles, ADAA_EQUALISER_EDGE_AT_2X)
            self.assertAlmostEqual(sum(equaliser.taps), 1.0, places=15)
            self.assertLess(-20 * math.log10(1 - worst), ripple_db, msg=order)
            to_host_nyquist = [equaliser.small_signal_response(2 * math.pi * 0.25 * k / 5000) for k in range(5001)]
            self.assertLess(20 * math.log10(max(to_host_nyquist)), ripple_db, msg=order)
        self.assertEqual(equaliser_of(1, 2).latency_steps, 2.5)
        self.assertEqual(equaliser_of(2, 2).latency_steps, 3)

    def test_at_1x_there_is_none_for_either_order(self):
        for order, latency in ((1, 0.5), (2, 1)):
            equaliser = equaliser_of(order, 1)
            self.assertEqual((equaliser.taps, equaliser.latency_steps, equaliser.functions()), ((1.0,), latency, {}))
            self.assertEqual(equaliser.output_expression("now"), "now")
            self.assertEqual((equaliser.remember_statements("now"), equaliser.declarations()), ("", ""))

    def test_a_pair_without_a_decision_fails_the_build(self):
        for order, oversampling in ((1, 3), (2, 4), (1, 0), (2, True), (1, 2.0), (1, None), (3, 2), (0, 1), (True, 1)):
            with self.assertRaises(BuildError, msg=(order, oversampling)):
                adaa_equaliser_decision(order, oversampling, "test")
            with self.assertRaises(BuildError, msg=(order, oversampling)):
                equaliser_of(order, oversampling)
        with self.assertRaises(TypeError):                     # never a default
            AntiderivativeAntialiasingEqualiser("e", raw_mean="in1", order=2)
        for bad_taps in ((0.2, 0.3, 0.5), (0.1, 0.7, 0.1), (0.5, 0.5)):  # not symmetric, DC not 1, even
            with self.assertRaises(BuildError, msg=bad_taps):
                checked_equaliser_taps(bad_taps, "test")

    def test_on_a_stream_it_is_its_taps_over_the_last_means(self):
        means = [math.sin(0.3 * i) + 0.1 * i for i in range(60)]
        for order in (1, 2):
            for oversampling in (1, 2):
                equaliser = equaliser_of(order, oversampling)
                out = harness([equaliser], {}, ["e_out"]).run(len(means), [means])[0]
                for got, expected in zip(out, equalised_adaa_outputs(means, equaliser.taps)):
                    self.assertAlmostEqual(got, expected, places=12)
        with self.assertRaises(BuildError):                    # made for points only: no statements of its own
            AntiderivativeAntialiasingEqualiser("e", order=2, oversampling=2).statements()

    # the 1x decision for first order, on the tanh saturator: (rate, Hz, drive, bias), worst alias under 20 kHz re the
    # fundamental, raw mean -> through the 5/24 equaliser. Measured 2026-10-20 over 60 cases (48 / 44.1 kHz, 410 Hz to
    # 8 kHz, drives 1.5 / 4 / 12, bias 0 / 0.3), 49 above the floor (11 under -150 dB): lifted in 44 (up to +6.2 dB),
    # within 0.05 dB in 4 (8 kHz at 48 kHz: its worst alias lands low, where the equaliser is flat), lowered in 1
    # (44.1 kHz, 8 kHz, drive 1.5: -1.1 dB). These six are kept.
    FIRST_ORDER_1X_CASES = ((48000.0, 1370.0, 12.0, 0.0, 5.7), (48000.0, 3100.0, 4.0, 0.3, 4.8),
                            (48000.0, 5000.0, 4.0, 0.0, 2.8), (44100.0, 410.0, 12.0, 0.0, 6.2),
                            (44100.0, 5000.0, 12.0, 0.3, 5.5), (44100.0, 8000.0, 4.0, 0.0, 1.8))

    def test_at_1x_the_first_order_equaliser_would_lift_the_saturators_aliases(self):
        taps = equaliser_of(1, 2).taps                 # the design at 1x: what it would have been
        length = 16384
        for rate, frequency, drive, bias, lift_db in self.FIRST_ORDER_1X_CASES:
            bin_number, coherent = coherent_frequency(frequency, rate, length)
            sine = [drive * math.sin(2 * math.pi * coherent * i / rate) for i in range(length + 256)]
            block = AntiderivativeTanhSaturator("d", input="in1", oversampling=1, bias=repr(bias))
            raw = harness([block], {}, ["d_out"], samplerate=rate).run(len(sine), [sine])[0]
            equalised = equalised_adaa_outputs(raw, taps)
            raw_db, equalised_db = (coherent_worst_alias_db(out[256:], bin_number, rate, 20000.0)
                                    for out in (raw, equalised))
            self.assertAlmostEqual(equalised_db - raw_db, lift_db, delta=0.2, msg=(rate, frequency, drive, bias))


class AntiderivativeTanhSaturatorTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def saturate(self, signal, oversampling=1, samplerate=SAMPLERATE, bias=None):
        block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling, bias=bias)
        return harness([block], {"bias": 0.3}, ["drive_out"], samplerate=samplerate).run(len(signal), [signal])[0]

    def test_its_oversampling_is_required_one_or_two(self):
        with self.assertRaises(TypeError):                     # never a default
            AntiderivativeTanhSaturator("drive", input="in1")
        for bad in (0, 3, 4, True, 2.0, None, "2"):
            with self.assertRaises(BuildError, msg=bad):
                AntiderivativeTanhSaturator("drive", input="in1", oversampling=bad)

    def test_it_cuts_the_aliases_of_a_hot_8k_sine(self):
        # worst alias below 10 kHz at 44.1 kHz, measured 2026-10-20: naive -23.3, 1x -53.2 dB, 2x -78.6 dB
        sine = [2.7 * math.sin(2 * math.pi * 8000.0 * i / self.SAMPLERATE) for i in range(4096 + 256)]
        harmonics = range(3, 16, 2)
        naive = worst_alias_db(GenProgram("out1 = tanh(in1);", 1, 1).run(len(sine), [sine])[0][256:], 8000.0,
                               harmonics, self.SAMPLERATE, 10000.0)
        self.assertGreater(naive, -30.0)
        self.assertLess(worst_alias_db(self.saturate(sine)[256:], 8000.0, harmonics, self.SAMPLERATE, 10000.0), -52.0)
        self.assertLess(worst_alias_db(self.saturate(sine, 2)[256:], 8000.0, harmonics, self.SAMPLERATE, 10000.0),
                        -77.0)

    # worst alias under 20 kHz re the fundamental at 48 kHz (coherent, every alias), 1x -> 2x, measured 2026-10-20
    ALIASES_AT_48K = ((1370.0, 4.0, None, -78.6, -157.6), (3100.0, 4.0, None, -48.9, -97.7),
                      (5000.0, 4.0, None, -36.7, -78.4), (8000.0, 12.0, None, -31.7, -46.5),
                      (12000.0, 4.0, None, -27.9, -48.0), (8000.0, 2.7, "bias", -34.9, -64.9))

    def test_at_2x_the_aliases_fall_further(self):
        rate, length = 48000.0, 16384
        for frequency, drive, bias, at_1x, at_2x in self.ALIASES_AT_48K:
            bin_number, coherent = coherent_frequency(frequency, rate, length)
            sine = [drive * math.sin(2 * math.pi * coherent * i / rate) for i in range(length + 512)]
            for oversampling, expected in ((1, at_1x), (2, at_2x)):
                measured = coherent_worst_alias_db(self.saturate(sine, oversampling, rate, bias)[512:], bin_number, rate,
                                                   20000.0)
                self.assertAlmostEqual(measured, expected, delta=1.0, msg=(frequency, drive, bias, oversampling))

    def test_small_signals_are_its_linear_response(self):
        # 1x: the 2-tap mean cos(w / 2), half a sample late (-2.4 dB at 10 kHz, -6.4 dB at 15 kHz at 44.1 kHz);
        # 2x: the mean and its equaliser at the 2x rate between the elliptic upsampler and the linear-phase
        # downsampler: within 0.01 dB to 18 kHz at 44.1 kHz (-0.03 at 19 kHz, -0.27 at 20 kHz), to 20 kHz at 48 kHz
        # (measured 2026-10-20)
        count = 8192
        for rate in (44100.0, 48000.0):
            for oversampling in (1, 2):
                block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
                for frequency in (100.0, 1000.0, 5000.0, 10000.0, 15000.0, 18000.0, 20000.0):
                    # at 100 Hz the Hann bin over 8192 samples leaks its negative frequency by ~6e-6 at 23 samples
                    # late: four times the length there
                    length = 4 * count if frequency < 500.0 else count
                    quiet = [0.001 * math.sin(2 * math.pi * frequency * i / rate) for i in range(length)]
                    gain = complex_amplitude_at(self.saturate(quiet, oversampling, rate)[1000:], frequency, rate) / \
                        complex_amplitude_at(quiet[1000:], frequency, rate)
                    twin = block.small_signal_response(frequency, rate)
                    self.assertLess(abs(gain - twin), 2e-6, msg=(rate, oversampling, frequency))
                    if oversampling == 1:
                        self.assertAlmostEqual(abs(twin), math.cos(math.pi * frequency / rate), places=12)
                    else:
                        # the linear-phase downsampler's pass band ends at 0.21 of the 2x rate (18.5 kHz at
                        # 44.1 kHz): -0.27 dB at 20 kHz there
                        bound = 0.0101 if rate == 48000.0 or frequency <= 18000.0 else 0.28
                        self.assertLess(abs(20 * math.log10(abs(twin))), bound, msg=(rate, frequency))
        self.assertAlmostEqual(20 * math.log10(math.cos(math.pi * 10000.0 / 44100.0)), -2.42, places=2)

    def test_its_latency_is_the_measured_delay_at_100_hz(self):
        # 2x: the mean and its equaliser 1.25, the elliptic upsampler 1.78, the linear-phase downsampler 20
        for oversampling, expected in ((1, 0.5), (2, 23.03)):
            block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
            self.assertAlmostEqual(block.latency_samples, expected, delta=0.005)
            w = 2 * math.pi * 100.0 / self.SAMPLERATE
            response_delay = -cmath.phase(block.small_signal_response(100.0, self.SAMPLERATE)) / w
            self.assertAlmostEqual(block.latency_samples, response_delay, places=9, msg="its own response's")
            if oversampling == 1:
                self.assertEqual(block.latency_samples, 0.5, "exactly: no float crumb for a device's sum")
            sine = [0.001 * math.sin(2 * math.pi * 100.0 * i / self.SAMPLERATE) for i in range(8820)]
            delay = -phase_degrees(self.saturate(sine, oversampling)[4410:], sine[4410:], 100.0, self.SAMPLERATE) / 360 \
                * self.SAMPLERATE / 100.0
            self.assertAlmostEqual(delay, block.latency_samples, delta=0.01, msg=oversampling)

    def test_hot_sines_keep_the_band_limited_tanhs_fundamental_through_its_linear_response(self):
        # the ideal: tanh's fundamental for a continuous sine (its Fourier series), through the block's small-signal
        # response at that frequency. The old split (x on an allpass, ADAA on tanh x - x) was off by about 0.22 x the
        # drive at 10 kHz (1.6 x the ideal's fundamental at drive 10). Measured 2026-10-20: the error <= 0.34 at 1x
        # (15 kHz at 44.1 kHz), <= 0.13 at 2x, alike at drives 3 and 20; a mean of tanh never leaves 1 (1x), the
        # half-band's ringing peaks < 1.74 (2x)
        points = 4096
        for drive in (3.0, 20.0):
            fundamental = 2 / points * sum(math.tanh(drive * math.sin(2 * math.pi * m / points))
                                           * math.sin(2 * math.pi * m / points) for m in range(points))
            for oversampling, error_bound, peak_bound in ((1, 0.35, 1.0 + 1e-12), (2, 0.14, 1.75)):
                block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
                for samplerate in (44100.0, 48000.0, 96000.0):
                    for frequency in (5000.0, 10000.0, 15000.0):
                        count = 2176
                        sine = [drive * math.sin(2 * math.pi * frequency * i / samplerate) for i in range(count)]
                        out = self.saturate(sine, oversampling, samplerate)[128:]
                        measured = drive * complex_amplitude_at(out, frequency, samplerate) / complex_amplitude_at(
                            sine[128:], frequency, samplerate)
                        error = abs(measured - fundamental * block.small_signal_response(frequency, samplerate))
                        case = f"{oversampling}x, {samplerate} Hz rate, {frequency} Hz, drive {drive}"
                        self.assertLess(error, error_bound, msg=case)
                        self.assertLess(max(map(abs, out)), peak_bound, msg=case)

    def test_hot_broadband_input_peaks_under_its_derived_bound(self):
        # a clipped broadband wave band-limited overshoots: tanh at 16x low-passed at 20 kHz (numpy, 2026-10-20) peaks
        # 1.74 / 1.78 on this white noise at +30 / +36 dB, 1.66 / 1.71 on the snare-like burst. Measured 2026-10-20 at
        # 2x: the elliptic downsampler 2.79 / 2.85 and 2.58 / 2.57, the linear-phase one 1.87 / 1.91 and 1.71 / 1.71;
        # never above the chain's sum of |taps| (2.19) times the mean's bound 1. At 1x no chain: never above 1. Both
        # but for the quotient's rounding (ILL_CONDITIONED_STEP: about 1e-9 at |x| 50; 1e-14 seen here).
        rate = 48000.0
        noise_source = random.Random(20261020)
        noise = [0.3 * noise_source.uniform(-1, 1) for _ in range(12000)]
        snare = [math.exp(-i / (0.08 * rate)) * (0.5 * math.sin(2 * math.pi * 190.0 * i / rate)
                                                  + 0.5 * noise_source.uniform(-1, 1)) for i in range(12000)]
        self.assertAlmostEqual(AntiderivativeTanhSaturator("d", input="in1", oversampling=2).output_bound_per_unit_mean,
                               2.19, delta=0.005)
        self.assertEqual(AntiderivativeTanhSaturator("d", input="in1", oversampling=1).output_bound_per_unit_mean, 1.0)
        for name, source, measured_bound in (("white noise", noise, 1.95), ("snare-like burst", snare, 1.76)):
            for drive_db in (30.0, 36.0):
                driven = [value * 10 ** (drive_db / 20) for value in source]
                for oversampling, bound in ((1, 1.0), (2, measured_bound)):
                    block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
                    peak = max(map(abs, self.saturate(driven, oversampling, rate)))
                    case = (name, drive_db, oversampling)
                    self.assertLessEqual(peak, block.output_bound_per_unit_mean + 1e-9, msg=case)
                    self.assertLess(peak, bound + 1e-9, msg=case)

    def test_near_equal_samples_are_exact(self):
        signal = [0.5 + 1e-12 * i for i in range(200)] + [3.0] * 50 + [-20.0] * 50
        out = self.saturate(signal)
        for i in range(10, 200):          # the mean of a near-constant: tanh at the midpoint
            self.assertAlmostEqual(out[i], math.tanh(0.5 * (signal[i] + signal[i - 1])), delta=1e-9)
        self.assertAlmostEqual(out[-1], -1.0, delta=1e-9)
        settled = signal + [-20.0] * 300                 # the half-band pair rings after the jump, then DC is 1
        self.assertAlmostEqual(self.saturate(settled, 2)[-1], -1.0, delta=1e-9)

    def test_with_a_bias_it_is_the_slid_curve(self):
        # tanh(x + b) - tanh(b), half a sample late at 1x: for a slow signal tanh at the midpoint (the mean is off by
        # about tanh'' step^2 / 24, 2e-5 here), 0 at 0, at either oversampling
        signal = [1.5 * math.sin(2 * math.pi * i / 400) for i in range(800)]
        out = self.saturate(signal, bias="bias")
        for i in range(100, 800):
            middle = 0.5 * (signal[i] + signal[i - 1])
            self.assertAlmostEqual(out[i], math.tanh(middle + 0.3) - math.tanh(0.3), delta=3e-5)
        for oversampling in (1, 2):
            self.assertEqual(self.saturate([0.0] * 10, oversampling, bias="bias")[-1], 0.0)

    def test_with_a_bias_it_makes_even_harmonics_and_cuts_their_aliases(self):
        sine = [2.7 * math.sin(2 * math.pi * 8000.0 * i / self.SAMPLERATE) for i in range(4096 + 256)]
        naive = GenProgram("out1 = tanh(in1 + 0.3) - tanh(0.3);", 1, 1).run(len(sine), [sine])[0][256:]
        self.assertGreater(worst_alias_db(naive, 8000.0, range(2, 16), self.SAMPLERATE, 10000.0), -30.0)
        # measured 2026-10-20: naive -24.6, 1x -47.0 dB, 2x -77.7 dB
        for oversampling, bound in ((1, -46.0), (2, -76.0)):
            out = self.saturate(sine, oversampling, bias="bias")[256:]
            self.assertGreater(amplitude_at(out, 16000.0, self.SAMPLERATE), 0.01, "a second harmonic")
            self.assertLess(worst_alias_db(out, 8000.0, range(2, 16), self.SAMPLERATE, 10000.0), bound, msg=oversampling)

    def test_a_reset_is_a_fresh_saturator(self):
        sine = [3.0 * math.sin(2 * math.pi * 3000.0 * i / self.SAMPLERATE) for i in range(600)]
        for oversampling in (1, 2):
            block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
            template = ("/*GEN_BLOCK_FUNCTIONS*/\nParam reset(0, min=0, max=1);\n/*GEN_BLOCK_DECLARATIONS*/\n"
                        f"if (reset > 0.5) {{\n{block.reset_statements()}\n}}\n/*DRIVE*/\nout1 = drive_out;\n")
            used = GenProgram(gen_code_with_blocks(template, [block], "test"), 1, 1, samplerate=self.SAMPLERATE)
            used.run(321, [[0.9] * 321])
            used.set_param("reset", 1.0)
            first = used.run(1, [sine[:1]])[0]
            used.set_param("reset", 0.0)
            assert_renders_similar(self.saturate(sine, oversampling), first + used.run(len(sine) - 1, [sine[1:]])[0],
                                   self.SAMPLERATE, f"after a reset, {oversampling}x")

    def test_its_cost_is_one_mean_a_step(self):
        for oversampling in (1, 2):
            block = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
            self.assertEqual(block.statements().count("tanh_antialiased("), oversampling)
            self.assertEqual(block.statements().count("adaa1_equaliser_2x("), 0 if oversampling == 1 else 2)
            self.assertEqual("drive_up_first" in block.statements(), oversampling == 2)


class AntiderivativeTanhSaturatorLinearTwinTests(unittest.TestCase):
    def test_it_is_the_saturators_small_signal_path(self):
        # a quiet signal through the saturator (slope 1 at 0) and through the twin: the same samples but for tanh's
        # curvature and log cosh's rounding over a 1e-4 step (measured 2e-11 at 1e-4: -134 dB), at both rates, so a
        # dry through it combs nowhere at a 50 % mix
        noise_source = random.Random(20261020)
        quiet = [1e-4 * noise_source.uniform(-1, 1) for _ in range(3000)]
        for oversampling in (1, 2):
            saturator = AntiderivativeTanhSaturator("drive", input="in1", oversampling=oversampling)
            twin = AntiderivativeTanhSaturatorLinearTwin("dry", input="in1", oversampling=oversampling)
            saturated, twinned = harness([saturator, twin], {}, ["drive_out", "dry_out"]).run(len(quiet), [quiet])
            assert_matches_model(saturated, twinned, 1e-9, f"the linear twin, {oversampling}x",
                                 "tanh's curvature and log cosh's rounding on a 1e-4 signal, measured 2e-11")
            self.assertEqual(twin.latency_samples, saturator.latency_samples)
            self.assertNotIn("tanh", "".join(twin.functions()) + "".join(
                line for line in twin.statements().splitlines() if not line.startswith("//")), "no tanh in the twin")

    def test_a_dry_through_it_has_no_comb_where_a_delay_would(self):
        # 50 % of the saturator's small-signal response and 50 % of the dry, against 1, at 44.1 kHz (measured
        # 2026-10-20): 22 samples + a Thiran all-pass for the remaining 1.03 (the latency 23.03) leaves -0.07 dB at
        # 10 kHz, -15.1 dB at 20 kHz (the elliptic upsampler's phase); the twin 0
        rate = 44100.0
        saturator = AntiderivativeTanhSaturator("drive", input="in1", oversampling=2)
        whole_samples = math.floor(saturator.latency_samples) - 1
        thiran_delay = saturator.latency_samples - whole_samples
        thiran_coefficient = (1 - thiran_delay) / (1 + thiran_delay)  # Smith, "Thiran Allpass Interpolators"

        def thiran_dry(frequency):
            z = cmath.exp(-2j * math.pi * frequency / rate)
            return z ** whole_samples * (thiran_coefficient + z) / (1 + thiran_coefficient * z)

        for frequency, delay_comb_db in ((10000.0, -0.07), (20000.0, -15.07)):
            wet = saturator.small_signal_response(frequency, rate)
            self.assertAlmostEqual(20 * math.log10(abs(0.5 * (wet + thiran_dry(frequency)))), delay_comb_db, delta=0.01)
        twin = AntiderivativeTanhSaturatorLinearTwin("dry", input="in1", oversampling=2)
        for frequency in (1000.0, 5000.0, 10000.0, 20000.0):
            quiet = [1e-4 * math.sin(2 * math.pi * frequency * i / rate) for i in range(4096)]
            saturated, twinned = harness([saturator, twin], {}, ["drive_out", "dry_out"], samplerate=rate).run(
                len(quiet), [quiet])
            mixed = [0.5 * (a + b) for a, b in zip(saturated, twinned)]
            self.assertAlmostEqual(complex_amplitude_at(mixed[1000:], frequency, rate),
                                   complex_amplitude_at(saturated[1000:], frequency, rate), delta=1e-9)


class BandLimitedEdgesTests(unittest.TestCase):
    SAMPLERATE = 44100.0

    def oscillator(self, fundamental, wave):
        """A saw (jump of -2 at each wrap) or a triangle (corners at phase 0 and 1/2) through the edges block."""
        edges = BandLimitedEdges("edges", naive="naive", oversampling=1)
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
        edges = BandLimitedEdges("edges", naive="2 * wrap(phase + 2 * step, 0, 1) - 1", oversampling=1)
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

    def test_its_latency_is_two_steps_in_host_samples_at_its_oversampling(self):
        for oversampling, latency_samples in ((1, 2), (2, 1), (4, 0.5)):
            edges = BandLimitedEdges("edges", naive="0", oversampling=oversampling)
            self.assertEqual((edges.latency_steps, edges.latency_samples), (2, latency_samples))
        with self.assertRaises(TypeError, msg="no default"):
            BandLimitedEdges("edges", naive="0")
        for bad in (0, 1.5, True, "2"):
            with self.assertRaises(BuildError, msg=bad):
                BandLimitedEdges("edges", naive="0", oversampling=bad)


class HistoriesStartAtTheirTargetsTests(unittest.TestCase):
    TARGETS = {"smoothed": "target", "ring": "target * 2"}

    def program(self, target):
        start = HistoriesStartAtTheirTargets("start", targets=self.TARGETS)
        code = gen_code_with_blocks(
            "/*GEN_BLOCK_FUNCTIONS*/\nParam target(%r, min=-1e9, max=1e9);\nHistory smoothed(0), ring(0);\n"
            "/*GEN_BLOCK_DECLARATIONS*/\n/*START*/\nsmoothed = smoothed + (target - smoothed) * 0.5;\n"
            "out1 = smoothed;\nout2 = ring;\nring = target * 2;\n" % target, [start], "start harness")
        return GenProgram(code, 0, 2, samplerate=1000.0)

    def test_a_smoother_starts_at_its_target_bit_for_bit(self):
        for target in (0.0, 0.8, 375.0, -3.25):
            smoothed, ring = self.program(target).run(20)
            self.assertEqual(set(smoothed), {target}, "a step from the target to itself is the target, exactly")
            self.assertEqual(set(ring), {target * 2}, "a ring read before its first write holds the first value")

    def test_only_the_first_sample(self):
        program = self.program(0.8)
        program.run(5)
        program.set_param("target", 0.0)
        smoothed = program.run(3)[0]
        self.assertEqual(smoothed, [0.4, 0.2, 0.1], "after the first sample it glides as written")

    def test_bad_names_and_no_targets_fail_the_build(self):
        with self.assertRaises(BuildError):
            HistoriesStartAtTheirTargets("start", targets={})
        with self.assertRaises(BuildError):
            HistoriesStartAtTheirTargets("start", targets={"Not History": "x"})


class TapeStyleEchoTests(unittest.TestCase):
    def echo(self, samplerate, diffusion=True, **params):
        block = TapeStyleEcho("echo", left_input="in1", right_input="in1", time_ms="time", feedback="feedback",
                         loop_lowpass_hz="lowpass", loop_highpass_hz="highpass", saturation_gain="saturation",
                         wow_cents="wow", flutter_cents="flutter", stop_pressed="stop > 0",
                         diffusion="diffusion" if diffusion else None, longest_time_ms=6000.0, right_lag_ms=10.0, rounds_kept=3)
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

    def test_the_time_starts_at_its_target(self):
        # no glide on load: the loop is the Param's time from the first sample, whatever the time
        samplerate = 2000.0
        for time_ms in (20.0, 375.0, 6000.0):
            loop = self.echo(samplerate, time=time_ms).run(50, [[0.0] * 50])[2]
            self.assertEqual(set(loop), {time_ms * samplerate / 1000}, time_ms)

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


class WholeSampleDelay(Technique):
    """A test's stand-in for what a device puts in an echo's loop: `input` late by a whole number of samples."""

    def __init__(self, instance_name, *, input, samples):
        super().__init__(instance_name, input=input)
        self.samples = int(samples)
        self.latency_samples = self.samples

    def declarations(self):
        return self.substituted(f"Delay ${{p}}_line({self.samples + 1});")

    def statements(self):
        return self.substituted(f"${{p}}_line.write(${{input}});\n${{p}}_out = ${{p}}_line.read({self.samples});")


class TapeStyleEchoOptionTests(unittest.TestCase):
    """The options (stereo modes, the clean loop, a device's processing in the loop): each repeat where its mode puts
    it, by the energy around n T on each side."""
    SAMPLERATE = 8000.0
    TIME_MS = 250.0

    def echo(self, extra_blocks=(), **options):
        if "saturation_gain" not in options and options.get("saturating", True):
            options["saturation_gain"] = "saturation"
        block = TapeStyleEcho("echo", left_input="in1", right_input="in1", time_ms="time", feedback="feedback",
                              loop_lowpass_hz="lowpass", loop_highpass_hz="highpass", wow_cents="0",
                              flutter_cents="0", stop_pressed="0", longest_time_ms=1000.0, right_lag_ms=10.0,
                              rounds_kept=0, **options)
        blocks = [block] + [factory(block) for factory in extra_blocks]
        params = {"time": self.TIME_MS, "feedback": 0.6, "lowpass": 3000.0, "highpass": 40.0, "saturation": 1.0,
                  "mode": 0.0}
        return harness(blocks, params, ["echo_left", "echo_right"], samplerate=self.SAMPLERATE)

    def energy_at(self, signal, seconds):
        center, half = int(10 + seconds * self.SAMPLERATE), int(0.03 * self.SAMPLERATE)
        return sum(v * v for v in signal[max(center - half, 0):center + half])

    def impulse_response(self, program, seconds=2.2):
        impulse = [0.0] * int(self.SAMPLERATE * seconds)
        impulse[10] = 0.1
        program.run(int(self.SAMPLERATE * 0.5), [[0.0] * int(self.SAMPLERATE * 0.5)])   # every mode's weight settled
        return program.run(len(impulse), [impulse])

    def test_the_modes_are_numbered_as_the_device_menu(self):
        self.assertEqual(STEREO_MODES, ("stereo", "ping-pong", "wide", "mono"))

    def test_ping_pong_alternates_the_first_on_the_left(self):
        program = self.echo(stereo_mode="mode")
        program.set_param("mode", 1.0)
        left, right = self.impulse_response(program)
        period = self.TIME_MS / 1000
        for k in range(1, 7):
            here, there = (left, right) if k % 2 else (right, left)
            self.assertGreater(self.energy_at(here, k * period), 1e3 * self.energy_at(there, k * period), k)

    def test_wide_puts_the_right_loop_at_its_ratio(self):
        program = self.echo(stereo_mode="mode")
        program.set_param("mode", 2.0)
        left, right = self.impulse_response(program)
        period, lag = self.TIME_MS / 1000, 0.010
        for k in (1, 2):                                # (3 T is the right's second repeat)
            self.assertGreater(self.energy_at(left, k * period), 1e-6, k)
            self.assertGreater(self.energy_at(right, k * period * WIDE_RIGHT_RATIO + lag),
                               1e3 * self.energy_at(right, k * period + lag) + 1e-12, k)

    def test_mono_gives_both_sides_the_same(self):
        program = self.echo(stereo_mode="mode")
        program.set_param("mode", 3.0)
        left, right = self.impulse_response(program)
        assert_matches_model(right, left, 1e-12, "mono's right against its left",
                             "the outputs' mean is computed once and given to both")

    def test_stereo_mode_left_at_stereo_is_the_echo_without_it(self):
        reference = self.impulse_response(self.echo())
        assert_renders_similar(reference, self.impulse_response(self.echo(stereo_mode="mode")), self.SAMPLERATE)

    def test_the_clean_loop_is_linear(self):
        quiet = self.impulse_response(self.echo(saturating=False))
        program = self.echo(saturating=False)
        impulse = [0.0] * int(self.SAMPLERATE * 2.2)
        impulse[10] = 0.8
        program.run(int(self.SAMPLERATE * 0.5), [[0.0] * int(self.SAMPLERATE * 0.5)])
        loud = program.run(len(impulse), [impulse])
        for side in (0, 1):
            assert_matches_model(loud[side], [8 * v for v in quiet[side]], 1e-12,
                                 "eight times the impulse against eight times the response",
                                 "no saturator: the loop is a linear filter, exact to the last bits")

    def test_a_device_in_the_loop_keeps_the_repeats_on_the_grid(self):
        # nothing in the loop: the same sound as the echo writing its own tapes
        reference = self.impulse_response(self.echo())
        writer = lambda echo: TapeStyleEchoTapeWriter(echo, left="echo_left_into_tape", right="echo_right_into_tape")
        candidate = self.impulse_response(self.echo([writer], loop_insert=True, insert_delay_samples="0"))
        assert_renders_similar(reference, candidate, self.SAMPLERATE)
        # 23 samples in the loop (the 2x drive's figure), said: the repeats still land on n T
        late = [lambda echo: WholeSampleDelay("insert_left", input="echo_left_into_tape", samples=23),
                lambda echo: WholeSampleDelay("insert_right", input="echo_right_into_tape", samples=23),
                lambda echo: TapeStyleEchoTapeWriter(echo, left="insert_left_out", right="insert_right_out")]
        left, _ = self.impulse_response(self.echo(late, loop_insert=True, insert_delay_samples="23"))
        period, loop = self.TIME_MS / 1000, self.TIME_MS / 1000 * self.SAMPLERATE
        for k in range(1, 6):
            late_ms = TapeStyleEchoTests.centroid_ms(left, int(10 + k * loop), int(loop / 2), self.SAMPLERATE)
            self.assertLess(abs(late_ms), 1.0, (k, late_ms))

    def test_options_say_what_they_need(self):
        with self.assertRaises(BuildError):
            self.echo(saturating=False, saturation_gain="saturation")
        with self.assertRaises(BuildError):
            self.echo(loop_insert=True)
        with self.assertRaises(BuildError):
            TapeStyleEchoTapeWriter(TapeStyleEcho("plain", left_input="0", right_input="0", time_ms="1", feedback="0",
                                                  loop_lowpass_hz="1", loop_highpass_hz="1", saturation_gain="1",
                                                  wow_cents="0", flutter_cents="0", stop_pressed="0",
                                                  longest_time_ms=10.0, right_lag_ms=0.0, rounds_kept=0),
                                    left="0", right="0")



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

    def test_a_tables_name_is_the_same_on_every_machine(self):
        # the last digits of computed pieces differ between maths libraries; the name mustn't (build_comparison.py)
        nudged = [(start, slope, intercept * (1 + 4e-16)) for start, slope, intercept in self.CLIP]
        self.assertEqual(PiecewiseLinearTable("clip", nudged).function_name,
                         PiecewiseLinearTable("clip", self.CLIP).function_name)
        changed = [self.CLIP[0], self.CLIP[1], (0.5, 0.0, 0.5001)]
        self.assertNotEqual(PiecewiseLinearTable("clip", changed).function_name,
                            PiecewiseLinearTable("clip", self.CLIP).function_name)

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

    # FOLD moving with a shift: its corners spread (the outer ones faster), its pieces meeting at every shift
    FOLD_START_RATES = (0.0, -0.4, -0.2, -0.2, 0.1, 0.3)

    def meeting_rates(self, start_rates, first=0.25):
        """Intercept rates that keep FOLD's pieces meeting at their moving starts, the first piece's `first`."""
        rates = [first]
        for (_, left_slope, _), (_, slope, _), start_rate in zip(self.FOLD, self.FOLD[1:], start_rates[1:]):
            rates.append(rates[-1] + (left_slope - slope) * start_rate)
        return tuple(rates)

    def motion(self, start_rates=FOLD_START_RATES, intercept_rates=None, shift="s", shift_range=(-0.5, 0.5)):
        return PiecewiseLinearMotion(shift=shift, start_rates=start_rates, shift_range=shift_range,
                                     intercept_rates=intercept_rates or self.meeting_rates(start_rates))

    def moving_fold(self, shift="in4"):
        return PiecewiseLinearTable("fold", self.FOLD, motion=self.motion(shift=shift))

    def test_a_moving_table_is_the_still_table_at_each_shift(self):
        # value, integral and ADAA2 of the moving table at shift s = those of the still table of its pieces at s (a
        # still table rounds its pieces to 10 digits: 1e-8; ADAA2 1e-9, eq. (15) exactly on pieces_at(s)), at every
        # shift in its range
        table = self.moving_fold()
        generator = random.Random(260)
        rows = []
        for _ in range(200):
            x0 = generator.uniform(-3, 3)
            step = 10 ** generator.uniform(-4, 0.5)
            rows.append((x0, x0 - step * generator.uniform(-1, 1), x0 - step * generator.uniform(-1, 1),
                         generator.uniform(-0.5, 0.5)))
        x0s, x1s, x2s, shifts = (list(column) for column in zip(*rows))
        code = "\n".join(table.functions().values()) + (
            f"\nout1 = {table.value_call('in1')};\nout2 = {table.integral_call('in1')};\n"
            f"out3 = {table.second_order_mean_call('in1', 'in2', 'in3')};\n")
        values, integrals, means = GenProgram(code, 4, 3).run(len(rows), [x0s, x1s, x2s, shifts])
        for (x0, x1, x2, shift), value, integral, mean in zip(rows, values, integrals, means):
            still = PiecewiseLinearTable("still", table.pieces_at(shift))
            self.assertAlmostEqual(value, still.value(x0), delta=1e-8, msg=(x0, shift))
            self.assertAlmostEqual(integral, still.integral(x0), delta=1e-8, msg=(x0, shift))
            self.assertAlmostEqual(mean, exact_second_order_mean(table.pieces_at(shift), x0, x1, x2), delta=1e-9,
                                   msg=(x0, x1, x2, shift))
        for shift in (-0.5, 0.0, 0.5):                   # the pieces meet at every shift
            pieces = table.pieces_at(shift)
            for (_, left_slope, left_intercept), (start, slope, intercept) in zip(pieces, pieces[1:]):
                self.assertAlmostEqual(left_slope * start + left_intercept, slope * start + intercept, delta=1e-12)

    def test_a_moving_table_at_shift_0_is_the_still_tables_bits(self):
        # every constant is written as the still table's double plus shift x the rest: at shift 0 the same bits
        moving, still = self.moving_fold("0"), PiecewiseLinearTable("fold", self.FOLD)
        generator = random.Random(261)
        x0s = [generator.uniform(-3, 3) for _ in range(300)]
        x1s = [x - 10 ** generator.uniform(-4, 0) for x in x0s]
        x2s = [x - 10 ** generator.uniform(-4, 0) for x in x1s]
        outputs = []
        for table in (moving, still):
            code = "\n".join(table.functions().values()) + (
                f"\nout1 = {table.value_call('in1')};\nout2 = {table.integral_call('in1')};\n"
                f"out3 = {table.second_order_mean_call('in1', 'in2', 'in3')};\n")
            outputs.append(GenProgram(code, 3, 3).run(len(x0s), [x0s, x1s, x2s]))
        assert_renders_similar(outputs[1], outputs[0], self.SAMPLERATE, "the moving table at shift 0")

    def test_a_motion_that_breaks_the_table_fails_the_build(self):
        PiecewiseLinearTable("fold", self.FOLD, motion=self.motion())          # the one above builds
        for broken in (
                self.motion(start_rates=(0.0, -0.4, -0.2, 0.0, 0.1, 0.3)),     # -0.999 passes -1 at the range's end
                self.motion(intercept_rates=self.meeting_rates(self.FOLD_START_RATES)[:3] + (0.4, 0.6, 0.45)),  # parting
                self.motion(start_rates=(0.0, -0.4, -0.2, -0.2, -2.0, 0.3)),   # 0.4 crosses 0
                self.motion(shift_range=(0.1, 0.5)),                             # no shift 0 in the range
                self.motion(start_rates=(0.1, -0.4, -0.2, -0.2, 0.1, 0.3))):    # the first piece's start moving
            with self.assertRaises(BuildError, msg=broken):
                PiecewiseLinearTable("fold", self.FOLD, motion=broken)

    def test_either_order_is_the_equalised_mean_of_a_line_on_a_piece_at_either_oversampling(self):
        # inside one piece: the line at the mean of the two (first order) or three (second) inputs, through ADAA's
        # equaliser for the order and the rate it runs at (at 1x none: the raw mean itself)
        table = PiecewiseLinearTable("clip", self.CLIP)
        inside = [0.3 * math.sin(2 * math.pi * 500 * i / self.SAMPLERATE) for i in range(200)]
        padded = [0.0, 0.0] + inside
        raw_means = {1: [(padded[i + 2] + padded[i + 1]) / 2 for i in range(len(inside))],
                     2: [(padded[i + 2] + padded[i + 1] + padded[i]) / 3 for i in range(len(inside))]}
        for order in (1, 2):
            for oversampling in (1, 2):
                shaper = AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=order,
                                                             oversampling=oversampling)
                self.assertIs(type(shaper.equaliser), AntiderivativeAntialiasingEqualiser)
                self.assertEqual(shaper.equaliser.taps, equaliser_of(order, oversampling).taps)
                out = harness([shaper], {}, ["shaper_out"], samplerate=self.SAMPLERATE).run(len(inside), [inside])[0]
                for i, expected in enumerate(equalised_adaa_outputs(raw_means[order], shaper.equaliser.taps)):
                    self.assertAlmostEqual(out[i], expected, places=12, msg=(order, oversampling, i))
                self.assertEqual(shaper.latency_steps, {(1, 1): 0.5, (1, 2): 2.5, (2, 1): 1, (2, 2): 3}[
                    (order, oversampling)])

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

    def test_at_2x_second_order_is_flat_to_20_khz_at_96_khz(self):
        # the 3-tap mean's droop (at 96 kHz -5.9 dB at 20 kHz) undone within 0.0972 dB up to the edge (20 kHz at
        # 96 kHz; the equaliser's own claims: AntiderivativeAntialiasingEqualiserTests), measured on the shaper,
        # three steps late, linear phase
        for frequency in (100.0, 1000.0, 5000.0, 10000.0, 15000.0, 18000.0, 20000.0):
            gain = self.shaper_gain(2, 96000.0, frequency)
            self.assertLess(abs(20 * math.log10(abs(gain))), 0.0973, msg=frequency)
            self.assertLess(abs(gain.imag), 1e-6, msg=f"{frequency}: linear phase, latency_steps late")

    def test_at_1x_there_is_no_equaliser_and_nothing_is_lifted_to_nyquist(self):
        # at 1x the output is ADAA2's raw mean, one step late: the 3-tap mean (1 + 2 cos w) / 3, never above 0 dB to
        # Nyquist, within 0.3 dB to 2.4 kHz at 48 kHz (-1.3 dB at 5 kHz, -5.9 at 10 kHz, -9.5 at 24 kHz). The 2x
        # equaliser here was within 0.1 dB to 10 kHz but +6.4 dB at 24 kHz, and lifted the aliases with it (the module
        # docstring's measurements: every equaliser at 1x lost more alias suppression than it gained)
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
            for order in (1, 2):
                with self.assertRaises(BuildError, msg=(order, unknown)):
                    AntiderivativePiecewiseLinearShaper("shaper", input="in1", table=table, order=order,
                                                        oversampling=unknown)

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
        assert_matches_model(rebuilt, signal, 1e-12, "low-pass + normalised band-pass + high-pass",
                             "the outputs sum to the input by the filter's algebra: a double's rounding on a signal near 1")

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
            assert_renders_similar(signal, self.clip(signal, knee), 44100.0, f"under the knee {knee}")

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
            assert_renders_similar([-x for x in out], self.clip([-x for x in signal], knee), 44100.0, "odd")

    def test_it_is_memoryless_so_its_latency_is_zero(self):
        # the same sample in gives the same sample out whatever came before: no state, no delay
        for knee in self.KNEES:
            self.assertEqual(KneeSoftClip("clip", input="in1", knee=knee).latency_samples, 0)
            signal = [0.3, 1.7, -2.0, 0.9, 0.3, -0.85, 1.7]
            out = self.clip(signal, knee)
            self.assertEqual(out[0], out[4], "0.3 after nothing and 0.3 after a burst")
            self.assertEqual(out[1], out[6])

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
        assert_matches_model(program.run(2000, [signal])[0], signal, 1e-12, "low-pass + high-pass",
                             "the outputs sum to the input by the filter's algebra: a double's rounding on a signal near 1")

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
        assert_renders_similar(offset, again, self.SAMPLERATE, "the same seed")
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
    SAMPLERATE = 8000.0

    def noise(self, seed=0.0):
        return harness([SeededWhiteNoise("noise", seed="seed", restart="in1")], {"seed": seed},
                       ["noise_out", "noise_state"], samplerate=self.SAMPLERATE)

    def test_it_is_the_minimal_standard_generator(self):
        # Park & Miller, p. 1195: "z1 = 1 then z10001 = 1043618065" (seed 0 starts the state at 1)
        _, state = self.noise(0.0).run(10000, [[0.0] * 10000])
        self.assertEqual(state[-1], 1043618065.0)
        out, _ = self.noise(271828.0).run(2000, [[0.0] * 2000])
        assert_renders_similar(park_miller_sequence(271828.0, 2000), out, self.SAMPLERATE, "Park and Miller's")

    def test_a_seed_restarts_it_and_so_does_restart(self):
        program = self.noise(5.0)
        first = program.run(100, [[0.0] * 100])[0]
        program.set_param("seed", 6.0)
        other = program.run(100, [[0.0] * 100])[0]
        program.set_param("seed", 5.0)
        again = program.run(100, [[0.0] * 100])[0]
        assert_renders_similar(first, again, self.SAMPLERATE, "seed 5 again")
        self.assertFalse(renders_are_similar(first, other, self.SAMPLERATE).similar, "seeds 5 and 6 draw alike")
        restarted = program.run(150, [[0.0] * 50 + [1.0] + [0.0] * 99])[0]
        assert_renders_similar(first, restarted[50:150], self.SAMPLERATE, "after a restart")

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
        assert_renders_similar(out[3:990], out[1003:1990], self.SAMPLERATE, "the second hit")

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
                self.assertFalse(renders_are_similar(a, b, self.SAMPLERATE).similar, "two instances sound alike")


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
        assert_matches_model(out, noise, 1e-9, "a 15 dB boost then the same cut",
                             "the cut is the boost's inverse: a double's rounding through two biquads on noise near 1")
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

    def downsampled(self, two_times_rate_signal, downsampler_type=HalfbandDownsampler):
        """`two_times_rate_signal`: a GenExpr expression of `t` (seconds) at twice the rate."""
        down = downsampler_type("down", first="first", second="second")
        first = two_times_rate_signal.replace("t_", "(count / samplerate)")
        second = two_times_rate_signal.replace("t_", "((count + 0.5) / samplerate)")
        code = gen_code_with_blocks(
            "/*GEN_BLOCK_FUNCTIONS*/\nHistory count(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
            f"first = {first};\nsecond = {second};\ncount = count + 1;\n/*DOWN*/\nout1 = down_out;\nout2 = first;\n",
            [down], "halfband harness")
        return GenProgram(code, 0, 2, samplerate=self.SAMPLERATE).run(8192 + 2000)

    def test_the_downsampler_stops_what_naive_decimation_folds(self):
        # a 30 kHz tone at 88.2 kHz: dropping every other sample folds it to 14.1 kHz at full level; the elliptic
        # downsampler -113.5 dB, the linear-phase one -120.4 dB (measured 2026-10-20)
        for downsampler_type in (HalfbandDownsampler, HalfbandLinearPhaseDownsampler):
            filtered, naive = self.downsampled("sin(twopi * 30000 * t_)", downsampler_type)
            alias = self.SAMPLERATE - 30000.0
            self.assertGreater(amplitude_at(naive[2000:], alias, self.SAMPLERATE), 0.99)
            self.assertLess(20 * math.log10(amplitude_at(filtered[2000:], alias, self.SAMPLERATE)), -99.0,
                            msg=downsampler_type)

    def test_the_linear_phase_design_is_a_kaiser_half_band_as_deep_as_the_elliptic(self):
        # Kaiser's formulas at 100 dB and the elliptic's band edges (pass to 0.21, stop from 0.29 of the 2x rate):
        # 83 taps (K 21), every other one 0, the middle 0.5, DC 1; the stop band -100.3 dB, the pass band within 1e-4 dB
        taps = linear_phase_halfband_taps()
        self.assertEqual(len(taps), 83)
        self.assertEqual(taps[41], 0.5)
        self.assertTrue(all(taps[n] == 0.0 for n in range(1, 83, 2) if n != 41))
        self.assertEqual(taps, tuple(reversed(taps)))
        self.assertAlmostEqual(sum(taps), 1.0, places=15)
        worst_stop = max(abs(linear_phase_halfband_response(0.29 + 0.21 * k / 400, taps)) for k in range(401))
        self.assertLess(20 * math.log10(worst_stop), -100.0)
        for f in (0.0, 0.05, 0.1, 0.15, 0.2, 0.21):
            self.assertLess(abs(20 * math.log10(abs(linear_phase_halfband_response(f, taps)))), 1e-4, f)
        for bad in (40.0, 250.0):
            with self.assertRaises(BuildError):
                linear_phase_halfband_taps(bad)
        with self.assertRaises(BuildError):
            HalfbandLinearPhaseDownsampler("down", first="in1", second="in1", taps=(0.0, 0.25, 0.0, 0.5, 0.0, 0.25, 0.0))

    def test_the_linear_phase_downsampler_is_its_response_and_k_minus_1_late(self):
        down = HalfbandLinearPhaseDownsampler("down", first="first", second="second")
        self.assertEqual(down.latency_samples, 20)
        for frequency in (100.0, 5000.0, 18000.0):
            filtered, _ = self.downsampled(f"sin(twopi * {frequency!r} * t_)", HalfbandLinearPhaseDownsampler)
            reference = [math.sin(2 * math.pi * frequency * n / self.SAMPLERATE) for n in range(len(filtered))]
            gain = complex_amplitude_at(filtered[2000:], frequency, self.SAMPLERATE) / complex_amplitude_at(
                reference[2000:], frequency, self.SAMPLERATE)
            # (the Hann bin over 8192 samples leaks 1.6e-6 at 100 Hz)
            self.assertLess(abs(gain - down.response(frequency / (2 * self.SAMPLERATE))), 3e-6, msg=frequency)
            late = cmath.exp(-2j * math.pi * frequency / self.SAMPLERATE * down.latency_samples)
            self.assertLess(abs(down.response(frequency / (2 * self.SAMPLERATE)) / late - 1), 2e-5, msg=frequency)

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
        # the latency at low frequencies (the phase delay at 100 Hz, base-rate samples): the two blocks' reported
        # latencies summed, 3.07 at the kit's design
        sine = [math.sin(2 * math.pi * 100.0 * n / self.SAMPLERATE) for n in range(8820)]
        out = program.run(8820, [sine])[0]
        delay = -phase_degrees(out[4410:], sine[4410:], 100.0, self.SAMPLERATE) / 360 * self.SAMPLERATE / 100.0
        self.assertAlmostEqual(delay, up.latency_samples + down.latency_samples, delta=0.005)
        self.assertAlmostEqual(up.latency_samples + down.latency_samples, 3.07, delta=0.005)
        # the upsampler's image (44.1 kHz - f, in the 88.2 kHz stream) is gone
        sine = [math.sin(2 * math.pi * 5000.0 * n / self.SAMPLERATE) for n in range(8820)]
        _, first, second = program.run(8820, [sine])
        stream = [value for pair in zip(first, second) for value in pair]
        image = amplitude_at(stream[8820:], self.SAMPLERATE - 5000.0, 2 * self.SAMPLERATE)
        self.assertLess(20 * math.log10(image), -95.0)

    def test_controls_reach_each_step_as_late_as_its_audio_at_any_design(self):
        # the same 100 Hz sine as the audio into the upsampler and as a control through ControlsAtTheUpsampledSteps:
        # the two 2x streams in phase (the kit's design, 1.78 samples late, and a shorter one, so the delay is the
        # upsampler's figure, not a typed one); the control read as it is now leads by the whole latency
        for design in (halfband_coefficients(), halfband_coefficients(4, 0.1)):
            up = HalfbandUpsampler("up", input="in1", coefficients=design)
            controls = ControlsAtTheUpsampledSteps("controls", upsampler=up, controls=dict(cv="in1"))
            self.assertEqual(controls.latency_samples, up.latency_samples)
            program = harness([up, controls], {}, ["up_first", "up_second", "controls_cv_step_1",
                                                   "controls_cv_step_2", "in1"])
            sine = [math.sin(2 * math.pi * 100.0 * n / self.SAMPLERATE) for n in range(8820)]
            first, second, control_first, control_second, now = (signal[4410:] for signal in program.run(8820, [sine]))
            audio_stream = [value for pair in zip(first, second) for value in pair]
            control_stream = [value for pair in zip(control_first, control_second) for value in pair]
            held_stream = [value for pair in zip(now, now) for value in pair]
            doubled_samples_per_degree = 2 * self.SAMPLERATE / 100.0 / 360
            control_lag = phase_degrees(audio_stream, control_stream, 100.0, 2 * self.SAMPLERATE) * doubled_samples_per_degree
            self.assertLess(abs(control_lag), 0.002, msg=design)
            held_lead = -phase_degrees(audio_stream, held_stream, 100.0, 2 * self.SAMPLERATE) * doubled_samples_per_degree
            # held over both steps the control sits a quarter sample (half a step) after the first step
            self.assertAlmostEqual(held_lead / 2, up.latency_samples - 0.25, delta=0.002, msg=design)
        self.assertGreater(abs(halfband_phase_delay_doubled_rate_samples(halfband_coefficients(4, 0.1)) / 2
                               - HalfbandUpsampler("up", input="in1").latency_samples), 0.5)
        with self.assertRaises(BuildError):
            ControlsAtTheUpsampledSteps("controls", upsampler="up", controls=dict(cv="in1"))
        with self.assertRaises(BuildError):
            ControlsAtTheUpsampledSteps("controls", upsampler=HalfbandUpsampler("up", input="in1"), controls={})


def poles_inside_the_unit_circle(denominator):
    """The step-down (Schur-Cohn) test on 1 + a_1 z^-1 + ... + a_N z^-N: every reflection coefficient under 1 in
    magnitude means every pole is inside the unit circle."""
    coefficients = list(denominator)
    while len(coefficients) > 1:
        reflection = coefficients[-1]
        if abs(reflection) >= 1:
            return False
        order = len(coefficients) - 1
        coefficients = [(coefficients[i] - reflection * coefficients[order - i]) / (1 - reflection * reflection)
                        for i in range(order)]
    return True


class DefinedLatencyPadTests(unittest.TestCase):
    """The device latency rule (DefinedLatency) and its pad (DefinedLatencyPad): every path's latency plus its pad is
    the declared whole number of samples, exactly for whole pads, within the stated Thiran bounds for fractional ones."""
    SAMPLERATE = 44100.0
    IMPULSE_LENGTH = 4096

    def impulse_response(self, blocks, output):
        program = harness(blocks, {}, [output], samplerate=self.SAMPLERATE)
        return program.run(self.IMPULSE_LENGTH, [[1.0] + [0.0] * (self.IMPULSE_LENGTH - 1)])[0]

    def response_of(self, impulse_response, frequency):
        w = 2 * math.pi * frequency / self.SAMPLERATE
        return sum(value * cmath.exp(-1j * w * n) for n, value in enumerate(impulse_response))

    def phase_delay_error(self, response, frequency, expected_delay_samples):
        """|phase delay - expected| in samples (the phase taken against the expected delay's, so no unwrapping)."""
        w = 2 * math.pi * frequency / self.SAMPLERATE
        return abs(cmath.phase(response * cmath.exp(1j * w * expected_delay_samples)) / w)

    def test_the_declared_figure_is_the_latest_path_rounded_up_and_every_pad_reaches_it(self):
        stab_like = DefinedLatency("device", {"moog": 2 + 3.067 + 23.03, "clean": 2 + 23.03})
        self.assertEqual(stab_like.declared_latency_samples, 29)
        self.assertIsInstance(stab_like.declared_latency_samples, int)
        for path, latency in stab_like.path_latency_samples.items():
            self.assertAlmostEqual(latency + stab_like.pad_samples[path], 29, places=12, msg=path)
        drums_like = DefinedLatency("device", {"kick": 0.5, "hat": 0})
        self.assertEqual((drums_like.declared_latency_samples, drums_like.pad_samples), (1, {"kick": 0.5, "hat": 1}))
        self.assertEqual(DefinedLatency("device", {"gate": 8}).pad_samples, {"gate": 0})
        self.assertEqual(DefinedLatency("device", {"none": 0}).declared_latency_samples, 0)

    def test_float_crumbs_and_ties_decide_nothing(self):
        crumbs = DefinedLatency("device", {"a": 0.5000000000000001 + 0.5, "b": 3 * 0.1 * 10, "c": 0.5})
        self.assertEqual(crumbs.declared_latency_samples, 3, "3.0000000000000004 is 3, not 4")
        self.assertEqual(crumbs.pad_samples["b"], 0)
        self.assertIsInstance(crumbs.pad_samples["b"], int, "a whole pad is an int: the bypass-exact ring")
        self.assertEqual(crumbs.pad_samples["a"], 2)
        self.assertEqual(DefinedLatency("device", {"a": 0.5, "b": 0.5}).declared_latency_samples, 1)
        self.assertEqual(DefinedLatency("device", {"a": 1.5000000001}).declared_latency_samples, 2)

    def test_a_bad_figure_or_path_fails_the_build(self):
        for bad in ({}, {"a": -0.5}, {"a": float("nan")}, {"a": float("inf")}, {"a": True}, {"a": "1"}, [("a", 1)]):
            with self.assertRaises(BuildError, msg=bad):
                DefinedLatency("device", bad)
        rule = DefinedLatency("device", {"a": 0.5, "b": 0})
        with self.assertRaises(BuildError):
            rule.pad("c", "pad_c", "in1")
        rule.pad("a", "pad_a", "in1")
        with self.assertRaisesRegex(BuildError, "'b'"):
            rule.check_every_path_padded()
        rule.pad("b", "pad_b", "in1")
        rule.check_every_path_padded()
        self.assertTrue(poles_inside_the_unit_circle((1.0, -1.5, 0.7)), "poles at radius sqrt(0.7)")
        self.assertFalse(poles_inside_the_unit_circle((1.0, 1.2)), "a pole at -1.2: the stability test can fail")
        for bad in (-1, float("nan"), True, "0.5"):
            with self.assertRaises(BuildError, msg=bad):
                DefinedLatencyPad("pad", input="in1", pad_samples=bad, oversampling=1)

    def test_a_whole_pad_is_the_input_exactly_that_many_samples_late(self):
        generator = random.Random(7)
        signal = [generator.uniform(-1, 1) for _ in range(200)]
        for pad_samples in (0, 1, 3, 5.0, 2.0000000000000004):
            pad = DefinedLatencyPad("pad", input="in1", pad_samples=pad_samples, oversampling=1)
            whole = round(pad_samples)
            self.assertEqual((pad.latency_samples, pad.thiran_order), (whole, 0))
            out = harness([pad], {}, ["pad_out"], samplerate=self.SAMPLERATE).run(200, [signal])[0]
            assert_renders_similar([0.0] * whole + signal[:200 - whole], out, self.SAMPLERATE, f"a pad of {pad_samples}")
        self.assertEqual(DefinedLatencyPad("pad", input="in1", pad_samples=0, oversampling=1).declarations(), "", "no state at 0")

    def test_a_fractional_pad_is_a_thiran_allpass_rendered_as_its_python_response(self):
        for pad_samples, order, whole in ((0.5, 1, 0), (0.97, 1, 0), (0.03, 1, 0), (1.25, 2, 0), (3.97, 4, 0),
                                          (25.03, 4, 22)):
            pad = DefinedLatencyPad("pad", input="in1", pad_samples=pad_samples, oversampling=1)
            self.assertEqual((pad.thiran_order, pad.whole_samples, pad.latency_samples), (order, whole, pad_samples))
            self.assertAlmostEqual(pad.whole_samples + pad.thiran_delay_samples, pad_samples, places=12)
            rendered = self.impulse_response([pad], "pad_out")
            for frequency in (100.0, 5000.0, 15000.0, 20000.0):
                found = self.response_of(rendered, frequency)
                self.assertLess(abs(found - pad.response(frequency, self.SAMPLERATE)), 1e-9, (pad_samples, frequency))
                self.assertAlmostEqual(abs(found), 1.0, delta=1e-9, msg="an all-pass: no loss, no lift")
            self.assertLess(self.phase_delay_error(pad.response(100.0, self.SAMPLERATE), 100.0, pad_samples), 1e-5)

    def test_the_stated_phase_delay_bounds_hold_for_every_fraction(self):
        # every fractional part in 0.01 steps, each order's pads (order N: pads in (N - 1, N); the top order also
        # past it, the same all-pass after whole samples); the bounds are tight (the worst is within 85 % of them
        # above 2 kHz), so the stated numbers are the measured ones
        for order in range(1, THIRAN_MAXIMUM_ORDER + 1):
            for top, bound in THIRAN_PHASE_DELAY_ERROR_BOUNDS[order].items():
                worst = 0.0
                for hundredths in range(1, 100):
                    pad_samples = order - 1 + hundredths / 100
                    pads = [pad_samples] + ([pad_samples + 7] if order == THIRAN_MAXIMUM_ORDER else [])
                    for samples in pads:
                        pad = DefinedLatencyPad("pad", input="in1", pad_samples=samples, oversampling=1)
                        self.assertEqual(pad.thiran_order, order, samples)
                        self.assertTrue(poles_inside_the_unit_circle(pad.thiran_coefficients), samples)
                        for step in range(1, 401):
                            frequency = top * step / 400
                            worst = max(worst, self.phase_delay_error(pad.response(frequency, self.SAMPLERATE),
                                                                      frequency, samples))
                self.assertLessEqual(worst, bound, (order, top))
                if top > 2000.0:
                    self.assertGreater(worst, 0.85 * bound, (order, top))

    def test_a_path_and_its_pad_are_the_declared_whole_number_late(self):
        # a 1x tanh saturator's linear twin is half a sample late, linear phase (cos(w / 2)); a dry path is on time:
        # padded, both are 1 sample late, the dry exactly, the saturated within order 1's bounds, magnitude untouched
        twin = AntiderivativeTanhSaturatorLinearTwin("twin", input="in1", oversampling=1)
        rule = DefinedLatency("device", {"saturated": twin.latency_samples, "dry": 0})
        self.assertEqual(rule.declared_latency_samples, 1)
        saturated_pad = rule.pad("saturated", "saturated_pad", "twin_out")
        dry_pad = rule.pad("dry", "dry_pad", "in1")
        rule.check_every_path_padded()
        saturated = self.impulse_response([twin, saturated_pad], "saturated_pad_out")
        dry = self.impulse_response([dry_pad], "dry_pad_out")
        self.assertEqual(dry[:3], [0.0, 1.0, 0.0])
        for top, bound in THIRAN_PHASE_DELAY_ERROR_BOUNDS[1].items():
            for frequency in (top / 4, top / 2, top):
                response = self.response_of(saturated, frequency)
                self.assertLessEqual(self.phase_delay_error(response, frequency, 1), bound, frequency)
                w = 2 * math.pi * frequency / self.SAMPLERATE
                self.assertAlmostEqual(abs(response), math.cos(w / 2), delta=1e-9, msg="the twin's own magnitude")


if __name__ == "__main__":
    unittest.main(verbosity=2)

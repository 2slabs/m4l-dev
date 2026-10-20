"""The Moog transistor ladder module (m4l_dev/circuit_modules/moog_transistor_ladder.py): the cutoff law and the
small-signal ladder against the sources (references/circuits/moog-transistor-ladder.md), and the rendered module
against its own Python twin and the large-signal model's behaviour (self-oscillation, the pass band's drop, the
Newton solve, aliases), through our GenExpr renderer (ours, not Max's compiler). Standard library only."""
import cmath
import math
import os
import random
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev import es5  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.circuit_modules import moog_transistor_ladder  # noqa: E402
from m4l_dev.circuit_modules.moog_transistor_ladder import (  # noqa: E402
    MoogTransistorLadder, MoogTransistorLadderCharacter, control_volts_for_cutoff_hz, cutoff_hz_at_control_volts,
    emphasis_for_feedback_gain, emphasis_pot_ohms_above_wiper, feedback_gain_at_emphasis, ladder_cutoff_hz,
    regeneration_trim_wiper, small_signal_response)
from gen_block_harness import (amplitude_at, cents, complex_amplitude_at, frequency_by_zero_crossings,  # noqa: E402
                               harness, worst_alias_db)

SAMPLERATE = 44100.0
TYPICAL = MoogTransistorLadderCharacter()
# the input volts that put 1 at the input pair's tanh argument (x = V / 2 VT)
VOLTS_PER_UNIT_DRIVE = 2 * TYPICAL.thermal_voltage_volts / TYPICAL.base_volts_per_input_volt
FULL_EMPHASIS_CENTS = -124.0  # [MEASURED] the module at Emphasis 10 (k 7.76), 300 Hz to 3 kHz: LargeSignalTests
TYPICAL_LOWEST_GAIN = feedback_gain_at_emphasis(0.0, TYPICAL)    # the Emphasis at 0: the loop is never quite open


def ladder_program(oversampling=2, character=TYPICAL, samplerate=SAMPLERATE):
    """A harness around one ladder: Params cv (control volts), emphasis; outputs out, the ladder's volts before the
    coupling capacitor, fc, k."""
    block = MoogTransistorLadder("moog", input_volts="in1", control_volts="cv", emphasis="emphasis",
                                 oversampling=oversampling, character=character)
    return harness([block], {"cv": 0.0, "emphasis": 0.0}, ["moog_out", "moog_ladder_volts", "moog_cutoff_hz",
                                                           "moog_feedback_gain"],
                   samplerate=samplerate)


def set_ladder(program, cutoff_hz, feedback_gain, character=TYPICAL):
    program.set_param("cv", control_volts_for_cutoff_hz(cutoff_hz, character))
    program.set_param("emphasis", emphasis_for_feedback_gain(feedback_gain, character))


def sine(frequency, amplitude, count, samplerate=SAMPLERATE):
    return [amplitude * math.sin(2 * math.pi * frequency * i / samplerate) for i in range(count)]


def oscillation(program, seconds=2.0):
    """Kick the ladder once (near its limit cycle's size, so it settles in time) and let it ring: (frequency, peak) of the last half."""
    count = int(SAMPLERATE * seconds)
    out = program.run(count, [[0.1 * VOLTS_PER_UNIT_DRIVE] + [0.0] * (count - 1)])[1]
    tail = out[count // 2:]
    return frequency_by_zero_crossings(tail, SAMPLERATE) if max(tail) > 0 else 0.0, max(abs(v) for v in tail)


class CutoffLawTests(unittest.TestCase):
    def test_the_ladder_current_sets_the_cutoff(self):
        # Stinchcombe 2008 eq. 13: fc = If / (8 pi C VT); a Minimoog's 0.068 uF at VT 26 mV: 44.4 uA for 1 kHz
        self.assertAlmostEqual(ladder_cutoff_hz(44.4e-6, 0.068e-6, 0.026), 999.2, delta=0.1)
        # the exponential converter: a volt an octave, 0 V at middle C (the character's calibration)
        self.assertAlmostEqual(cutoff_hz_at_control_volts(0.0, TYPICAL), 261.6256, delta=1e-4)
        self.assertAlmostEqual(cutoff_hz_at_control_volts(2.0, TYPICAL) / cutoff_hz_at_control_volts(1.0, TYPICAL), 2.0,
                               places=12)
        self.assertAlmostEqual(cutoff_hz_at_control_volts(control_volts_for_cutoff_hz(5000.0, TYPICAL), TYPICAL),
                               5000.0, places=9)
        # a warmer ladder (VT up 5 %) at the same current sits 5 % lower
        warm = MoogTransistorLadderCharacter(thermal_voltage_volts=0.0273)
        self.assertAlmostEqual(cutoff_hz_at_control_volts(0.0, warm), 261.6256 / 1.05, delta=1e-3)
        with self.assertRaises(BuildError):
            control_volts_for_cutoff_hz(0.0, TYPICAL)

    def test_the_rendered_cutoff_follows_the_law_and_holds_its_range(self):
        program = ladder_program()
        for volts in (-3.0, 0.0, 2.5, 5.0, 9.0):
            program.set_param("cv", volts)
            readout = program.run(2, [[0.0, 0.0]])[2][-1]
            expected = min(max(cutoff_hz_at_control_volts(volts, TYPICAL), 5.0), 0.45 * SAMPLERATE)
            self.assertAlmostEqual(readout / expected, 1.0, places=9, msg=volts)


class EmphasisLawTests(unittest.TestCase):
    def test_the_calibration_puts_k_4_at_7_5_and_the_law_is_the_circuit_s(self):
        # ref §2.4: k = 15.1 (330 + 1000 w) / (1330 + Rtop); the trim set so k(7.5) = 4; the default taper's Rtop(7.5)
        # 1.25k (2.5 % of 50k: the reference's "~3 %"), so w 0.353 (near mid-travel) and k(10) = 4 x 2580 / 1330
        self.assertAlmostEqual(emphasis_pot_ohms_above_wiper(0.75, TYPICAL), 1250.0, places=6)
        self.assertAlmostEqual(emphasis_pot_ohms_above_wiper(1.0, TYPICAL), 0.0, places=9)
        self.assertAlmostEqual(emphasis_pot_ohms_above_wiper(0.0, TYPICAL), 50000.0, places=6)
        self.assertAlmostEqual(feedback_gain_at_emphasis(0.75, TYPICAL), 4.0, places=12)
        self.assertAlmostEqual(regeneration_trim_wiper(TYPICAL), 0.3534, places=4)
        wiper = regeneration_trim_wiper(TYPICAL)
        for emphasis in (0.0, 0.3, 0.75, 1.0):
            circuit = 15.1 * (330 + 1000 * wiper) / (1330 + emphasis_pot_ohms_above_wiper(emphasis, TYPICAL))
            self.assertAlmostEqual(feedback_gain_at_emphasis(emphasis, TYPICAL), circuit, places=9)
        self.assertAlmostEqual(feedback_gain_at_emphasis(1.0, TYPICAL), 4 * 2580 / 1330, places=9)
        # hyperbolic: k / k(10) ~ 0.5 at 7.5, ~ 0.2 at 5, ~ 0.03 at 0 (ref §2.4)
        top = feedback_gain_at_emphasis(1.0, TYPICAL)
        for emphasis, share, tolerance in ((0.75, 0.5, 0.02), (0.5, 0.2, 0.02), (0.0, 0.03, 0.005)):
            self.assertAlmostEqual(feedback_gain_at_emphasis(emphasis, TYPICAL) / top, share, delta=tolerance)
        for gain in (TYPICAL_LOWEST_GAIN, 1.0, 4.0, 7.0):
            self.assertAlmostEqual(feedback_gain_at_emphasis(emphasis_for_feedback_gain(gain, TYPICAL), TYPICAL), gain,
                                   places=9)

    def test_the_rendered_k_is_the_law(self):
        program = ladder_program()
        for emphasis in (-0.5, 0.0, 0.4, 0.75, 0.97, 1.0, 2.0):
            program.set_param("emphasis", emphasis)
            self.assertAlmostEqual(program.run(1, [[0.0]])[3][0], feedback_gain_at_emphasis(emphasis, TYPICAL),
                                   places=12, msg=emphasis)

    def test_the_display_script_is_the_module_s_response_and_law(self):
        mismatched = MoogTransistorLadderCharacter(stage_1_capacitance_ratio=1.1, stage_3_capacitance_ratio=0.93,
                                                   emphasis_pot_audio_taper_at_half_rotation=0.15)
        for character in (TYPICAL, mismatched):
            for oversampling in (1, 2):
                block = MoogTransistorLadder("moog_vcf", input_volts="in1", control_volts="0", emphasis="0",
                                             oversampling=oversampling, character=character)
                script = block.response_script_code()
                for frequency, cutoff, emphasis, rate in ((100.0, 700.0, 0.3, 48000), (700.0, 700.0, 1.0, 44100),
                                                          (15000.0, 30000.0, 0.8, 44100), (19000.0, 2000.0, 0.0, 96000)):
                    drawn = float(es5.evaluate(script + f"\nmoog_vcf_response({frequency}, {cutoff}, {emphasis}, {rate})"))
                    gain = feedback_gain_at_emphasis(emphasis, character)
                    module = abs(small_signal_response(frequency, cutoff, gain, rate, character, oversampling))
                    self.assertAlmostEqual(drawn / module, 1.0, places=9, msg=(oversampling, frequency, cutoff))
                    self.assertAlmostEqual(float(es5.evaluate(script + f"\nmoog_vcf_feedback_gain({emphasis})")), gain,
                                           places=12)


class SmallSignalTests(unittest.TestCase):
    def test_at_one_step_a_sample_it_is_the_prewarped_analog_ladder(self):
        for frequency, cutoff, gain in ((100.0, 1000.0, 0.0), (1000.0, 1000.0, 3.5), (7000.0, 5000.0, 2.0)):
            s = 1j * math.tan(math.pi * frequency / SAMPLERATE) / math.tan(math.pi * cutoff / SAMPLERATE)
            analog = 1 / ((1 + s) ** 4 + gain)
            self.assertAlmostEqual(abs(small_signal_response(frequency, cutoff, gain, SAMPLERATE, oversampling=1)
                                       - analog), 0.0, places=12)

    def test_small_signals_are_the_twin_s_response(self):
        # a 10 mV sine (0.01 of the tanh's knee): the rendered ladder (before the coupling capacitor) against the twin,
        # the typical unit and a mismatched one, at one and two steps a sample
        mismatched = MoogTransistorLadderCharacter(stage_1_capacitance_ratio=1.1, stage_3_capacitance_ratio=0.93)
        for character in (TYPICAL, mismatched):
            for oversampling in (1, 2):
                program = ladder_program(oversampling, character)
                for cutoff, gain in ((1000.0, 0.5), (1000.0, 3.0), (6000.0, 2.0)):
                    set_ladder(program, cutoff, gain, character)
                    for frequency in (150.0, 900.0, 4000.0):
                        count = 16384
                        x = sine(frequency, 0.01 * VOLTS_PER_UNIT_DRIVE, count)
                        out = program.run(count, [x])[1][count // 2:]
                        measured = complex_amplitude_at(out, frequency, SAMPLERATE) / complex_amplitude_at(
                            x[count // 2:], frequency, SAMPLERATE)
                        twin = small_signal_response(frequency, cutoff, gain, SAMPLERATE, character, oversampling)
                        message = (character, oversampling, cutoff, gain, frequency)
                        self.assertAlmostEqual(20 * math.log10(abs(measured) / abs(twin)), 0.0, delta=0.01, msg=message)
                        self.assertAlmostEqual(math.degrees(cmath.phase(measured / twin)), 0.0, delta=0.3, msg=message)

    def test_the_pass_band_drops_with_the_feedback_as_the_circuit_s(self):
        # D'Angelo & Valimaki Part I: dc gain 1 / (1 + k); Stinchcombe §2.5: about -14 dB at k = 4. A 60 Hz sine with
        # fc 8 kHz, before the coupling capacitor
        program = ladder_program()
        for gain in (TYPICAL_LOWEST_GAIN, 1.0, 2.0, 3.0, 4.0):
            set_ladder(program, 8000.0, gain)
            x = sine(60.0, 0.01 * VOLTS_PER_UNIT_DRIVE, 22050)
            out = program.run(22050, [x])[1][11025:]
            level = amplitude_at(out, 60.0, SAMPLERATE) / amplitude_at(x[11025:], 60.0, SAMPLERATE)
            self.assertAlmostEqual(20 * math.log10(level), -20 * math.log10(1 + gain), delta=0.02, msg=gain)

    def test_the_output_coupling_takes_the_offset_s_dc_away_and_keeps_its_even_harmonics(self):
        # a 10 mV input-pair offset: the ladder's output carries DC and even harmonics; after the coupling capacitor
        # (15.4 Hz) the DC is gone, the 2nd harmonic stays. A matched pair makes no even harmonics.
        count = 44100
        x = sine(200.0, 1.0 * VOLTS_PER_UNIT_DRIVE, count)
        levels = {}
        for offset in (0.0, 0.01):
            program = ladder_program(character=MoogTransistorLadderCharacter(input_pair_offset_volts=offset))
            set_ladder(program, 4000.0, TYPICAL_LOWEST_GAIN)
            out, ladder_volts, _, _ = program.run(count, [x])
            tail = out[count // 2:]
            levels[offset] = 20 * math.log10(amplitude_at(tail, 400.0, SAMPLERATE) / amplitude_at(tail, 200.0, SAMPLERATE))
            self.assertLess(abs(sum(tail) / len(tail)), 1e-3, msg=offset)
            if offset:
                self.assertGreater(abs(sum(ladder_volts[count // 2:]) / (count - count // 2)), 0.05)
        self.assertLess(levels[0.0], -120)
        self.assertGreater(levels[0.01], -40)


class LargeSignalTests(unittest.TestCase):
    def test_the_onset_of_self_oscillation_is_k_4(self):
        program = ladder_program()
        for gain, grows in ((3.95, False), (4.05, True)):
            set_ladder(program, 1000.0, gain)
            program.run(4410, [[0.0] * 4410])
            out = program.run(44100, [[1e-3 * VOLTS_PER_UNIT_DRIVE] + [0.0] * 44099])[1]
            early, late = max(abs(v) for v in out[2000:6000]), max(abs(v) for v in out[-4000:])
            self.assertEqual(late > early, grows, msg=(gain, early, late))

    def test_regeneration_starts_at_emphasis_7_5_as_the_calibration_sets_it(self):
        program = ladder_program()
        for emphasis, grows in ((0.74, False), (0.76, True)):
            program.set_param("cv", control_volts_for_cutoff_hz(1000.0, TYPICAL))
            program.set_param("emphasis", emphasis)
            program.run(4410, [[0.0] * 4410])
            out = program.run(44100, [[1e-3 * VOLTS_PER_UNIT_DRIVE] + [0.0] * 44099])[1]
            early, late = max(abs(v) for v in out[2000:6000]), max(abs(v) for v in out[-4000:])
            self.assertEqual(late > early, grows, msg=(emphasis, early, late))

    def test_full_emphasis_sings_hot_and_flat(self):
        # k 7.76 at Emphasis 10 (the circuit's law, default taper): the oscillation is far past onset, a large swing
        # and far flatter than at k 4.2. [MEASURED, the module's own numbers: no RK4 reference at this k yet] 124
        # cents under fc at 300 Hz to 3 kHz (119 at 8 kHz), its swing 0.286 of a drive unit (2.6x k 4.2's)
        program = ladder_program()
        for cutoff in (300.0, 1000.0, 3000.0):
            program.set_param("cv", control_volts_for_cutoff_hz(cutoff, TYPICAL))
            program.set_param("emphasis", 1.0)
            frequency, peak = oscillation(program)
            self.assertAlmostEqual(cents(frequency, cutoff), FULL_EMPHASIS_CENTS, delta=1.5, msg=cutoff)
            self.assertAlmostEqual(peak, 0.286 * VOLTS_PER_UNIT_DRIVE, delta=0.005 * VOLTS_PER_UNIT_DRIVE, msg=cutoff)

    def test_k_4_2_sings_where_the_large_signal_model_does(self):
        # at k 4.2 the model's oscillation sits 19.6 cents under fc at every cutoff (its stages'
        # tanh lower their gain on the swing: RK4 at 64x, the research table in the reference §6); the module within
        # 0.5 cents of that from 100 Hz to 3 kHz, 1.5 at 8 kHz, 2.5 at 12 kHz (the trapezoid's error on the swing),
        # its swing 0.11 of a drive unit (x4's peak: 0.11 x 2 VT / base_volts_per_input_volt volts at the output's scale)
        program = ladder_program()
        for cutoff, tolerance in ((100.0, 0.5), (300.0, 0.5), (1000.0, 0.5), (3000.0, 0.5), (8000.0, 1.5),
                                  (12000.0, 2.5)):
            set_ladder(program, cutoff, 4.2)
            frequency, peak = oscillation(program)
            self.assertAlmostEqual(cents(frequency, cutoff), -19.6, delta=tolerance, msg=cutoff)
            self.assertAlmostEqual(peak, 0.11 * VOLTS_PER_UNIT_DRIVE, delta=0.015 * VOLTS_PER_UNIT_DRIVE, msg=cutoff)

    def test_two_newton_iterations_are_the_solved_loop(self):
        # a hot saw-like drive at fc 6 kHz, k 3.9: the output with NEWTON_ITERATIONS = 2 against 8, within 1e-3 of
        # the signal's peak
        count = 8820
        rng = random.Random(3)
        x = [VOLTS_PER_UNIT_DRIVE * 8 * (((i * 330.0 / SAMPLERATE) % 1) * 2 - 1) + rng.uniform(-1, 1) for i in range(count)]
        outputs = {}
        for iterations in (2, 8):
            with mock.patch.object(moog_transistor_ladder, "NEWTON_ITERATIONS", iterations):
                program = ladder_program()
            set_ladder(program, 6000.0, 3.9)
            outputs[iterations] = program.run(count, [x])[1]
        peak = max(abs(v) for v in outputs[8])
        self.assertLess(max(abs(a - b) for a, b in zip(outputs[2], outputs[8])) / peak, 1e-3)

    def test_bounded_under_a_hot_input_and_a_jumping_cutoff(self):
        # 30 V noise (x up to 580) at full emphasis, the control node jumping over 12 octaves every sample: every
        # output finite and under the input's scale, and with the input and emphasis gone it falls silent
        program = ladder_program()
        program.set_param("emphasis", 1.0)
        rng = random.Random(7)
        for _ in range(200):
            program.set_param("cv", rng.uniform(-4.0, 8.0))
            out, ladder_volts, _, _ = program.run(32, [[rng.uniform(-30.0, 30.0) for _ in range(32)]])
            for value in out + ladder_volts:
                self.assertTrue(math.isfinite(value))
                self.assertLess(abs(value), 60.0)
        program.set_param("emphasis", 0.0)
        program.set_param("cv", 3.0)
        out = program.run(44100, [[0.0] * 44100])[0]
        self.assertLess(max(abs(v) for v in out[-4410:]), 1e-4)

    def test_oversampling_lowers_the_aliases_of_a_hot_input(self):
        # a 2.5 kHz sine at drive 10 (10.4 V in, 0.52 V at the bases), fc 12 kHz, k 2: the worst folded harmonic
        # below 20 kHz, dB re the fundamental (research: -30 at 1x, -55 at 2x through the halfband oversampler, the
        # RK4 reference -115)
        count, fundamental = 16384, 2500.7
        x = sine(fundamental, 10 * VOLTS_PER_UNIT_DRIVE, count)
        harmonics = range(9, 61, 2)
        aliases = {}
        for oversampling in (1, 2):
            program = ladder_program(oversampling)
            set_ladder(program, 12000.0, 2.0)
            out = program.run(count, [x])[1][count // 4:]
            aliases[oversampling] = worst_alias_db(out, fundamental, harmonics, SAMPLERATE, 20000.0)
        self.assertGreater(aliases[1], -36)
        self.assertLess(aliases[2], -53)

    def test_a_reset_empties_the_ladder(self):
        block = MoogTransistorLadder("moog", input_volts="in1", control_volts="0", emphasis="0")
        for state in ("moog_s1 = 0;", "moog_x4 = 0;", "moog_coupling_s = 0;", "moog_up_stage_0_in_before = 0;",
                      "moog_down_stage_7_out_before = 0;"):
            self.assertIn(state, block.reset_statements())

    def test_its_cost_is_five_tanh_a_newton_iteration_a_step(self):
        for oversampling in (1, 2):
            block = MoogTransistorLadder("moog", input_volts="in1", control_volts="0", emphasis="0",
                                         oversampling=oversampling)
            self.assertEqual(block.statements().count("tanh("), 5 * moog_transistor_ladder.NEWTON_ITERATIONS * oversampling)


class BuildTests(unittest.TestCase):
    def test_a_meaningless_character_or_wiring_fails_the_build(self):
        for bad in (dict(thermal_voltage_volts=0.0), dict(stage_2_capacitance_ratio=-1.0),
                    dict(emphasis_pot_audio_taper_at_half_rotation=0.5), dict(regeneration_onset_emphasis=0.0),
                    dict(emphasis_tap_gain=0.0), dict(base_volts_per_input_volt=math.inf)):
            with self.assertRaises(BuildError, msg=bad):
                MoogTransistorLadder("moog", input_volts="in1", control_volts="0", emphasis="0",
                                     character=MoogTransistorLadderCharacter(**bad))
        for oversampling in (0, 1.5, True, 4):
            with self.assertRaises(BuildError, msg=oversampling):
                MoogTransistorLadder("moog", input_volts="in1", control_volts="0", emphasis="0", oversampling=oversampling)


if __name__ == "__main__":
    unittest.main(verbosity=2)

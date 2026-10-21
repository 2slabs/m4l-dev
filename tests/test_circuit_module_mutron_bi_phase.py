"""The Mu-Tron Bi-Phase module (m4l_dev/circuit_modules/mutron_bi_phase.py): its claims, rendered through our GenExpr
renderer (ours, not Max's compiler) on a harness around one unit (tests/gen_block_harness.py). Volts in, volts out.
Standard library only."""
import dataclasses
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev import es5  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.generated_scripts import check_es5  # noqa: E402
from m4l_dev.circuit_modules.mutron_bi_phase import (MutronBiPhase, MutronBiPhaseCharacter,  # noqa: E402
                                                     RUNTIME_CHARACTER_FIELDS, cell_ohms, feedback_gain,
                                                     feedback_pot_position, phasor_notches_hz, phasor_response,
                                                     phasor_small_signal_response, stage_corner_hz)
from gen_block_harness import amplitude_at, harness, phase_degrees  # noqa: E402

SAMPLERATE = 44100.0
MATCHED = MutronBiPhaseCharacter(stage_corner_spread=0.0)
# the panel: both phasors on the pedal at mid travel, full depth, no feedback, In A, both foot switches on
PANEL = dict(rate_1=0.5, rate_2=1.0, shape_1=0.0, shape_2=0.0, depth_a=1.0, depth_b=1.0, feedback_a=0.0,
             feedback_b=0.0, sweep_a_source=1.0, sweep_b_source=2.0, sweep_sync=0.0, phasor_b_input=0.0,
             foot_switch_a=1.0, foot_switch_b=1.0, pedal=2.5)
OUTPUTS = ["unit_out_a", "unit_out_b", "unit_corner_a_hz", "unit_corner_b_hz", "unit_sweep_cell_a_resistance",
           "unit_wet_a", "unit_sweep_a", "unit_sweep_b", "unit_phasor_a_out", "unit_phasor_a_loop_input"]


def unit_block(character=MATCHED):
    return MutronBiPhase("unit", input_a_volts="in1", input_b_volts="in1", rate_1_hz="rate_1", rate_2_hz="rate_2",
                          shape_1="shape_1", shape_2="shape_2", depth_a="depth_a", depth_b="depth_b",
                          feedback_a="feedback_a", feedback_b="feedback_b", sweep_a_source="sweep_a_source",
                          sweep_b_source="sweep_b_source", sweep_sync="sweep_sync", phasor_b_input="phasor_b_input",
                          foot_switch_a="foot_switch_a", foot_switch_b="foot_switch_b", pedal_volts="pedal",
                          character=character)


def unit(character=MATCHED, **panel):
    return harness([unit_block(character)], dict(PANEL, **panel), OUTPUTS, samplerate=SAMPLERATE)


def sine(frequency, samples, amplitude=1.0):
    return [amplitude * math.sin(2 * math.pi * frequency * n / SAMPLERATE) for n in range(samples)]


def responses(program, frequencies, outputs=(0,), settle=4410, measure=4410):
    """[[|output / input| at each frequency] for each output index], a settled sine at a time through one program."""
    found = [[] for _ in outputs]
    for frequency in frequencies:
        rendered = program.run(settle + measure, [sine(frequency, settle + measure)])
        for slot, index in enumerate(outputs):
            found[slot].append(amplitude_at(rendered[index][settle:], frequency, SAMPLERATE))
    return found


def db(ratio):
    return 20 * math.log10(ratio)


def settled_cell_ohms(program):
    return program.run(4410, [[0.0] * 4410])[4][-1]


class MutronBiPhaseTests(unittest.TestCase):
    def test_the_notches_sit_where_the_stage_corner_formula_puts_them(self):
        # six matched stages at the corner 1 / (2 pi (R_cell || 220k) 6.8 nF) for the cell's resistance: their phase is
        # 180 degrees (a notch against the dry) at tan 15, 45, 75 degrees x the corner, mapped through the bilinear
        # transform prewarped at the corner (exact at the middle one; at 44.1 kHz the top one of a 1.8 kHz corner sits
        # 6.5 % low). Rendered: the stages' output against their input
        for pedal in (3.2, 4.4):
            program = unit(pedal=pedal)
            cell = settled_cell_ohms(program)
            corner = stage_corner_hz(cell)
            for ratio in (math.tan(math.radians(15)), 1.0, math.tan(math.radians(75))):
                notch = SAMPLERATE / math.pi * math.atan(ratio * math.tan(math.pi * corner / SAMPLERATE))
                rendered = program.run(8820, [sine(notch, 8820)])
                with self.subTest(pedal=pedal, cell_ohms=round(cell), notch=round(notch)):
                    phase = phase_degrees(rendered[8][4410:], rendered[9][4410:], notch, SAMPLERATE)
                    self.assertLess(abs(abs(phase) - 180.0), 0.5)

    def test_the_output_is_the_circuits_response_coupling_capacitors_and_all(self):
        # the whole phasor (stages, C12 into R26 || the pot, the passive mix through C14) rendered = the module's Python
        # model, notches included; the coupling capacitors' phase lead pulls the low notches up (at a 500 Hz corner the
        # middle notch sits ~6 % above the stages' own)
        for pedal in (3.2, 4.4):
            program = unit(pedal=pedal)
            cell = settled_cell_ohms(program)
            corner = stage_corner_hz(cell)
            frequencies = [corner * ratio for ratio in (0.2, 0.3, 0.5, 0.8, 1.0, 1.1, 1.7, 3.0, 3.7)]
            for frequency, level in zip(frequencies, responses(program, frequencies)[0]):
                with self.subTest(pedal=pedal, frequency=round(frequency)):
                    self.assertAlmostEqual(db(level), db(abs(phasor_small_signal_response(
                        frequency, cell, 0.0, SAMPLERATE, character=MATCHED))), delta=0.1)

    def test_the_feedback_peaks_between_the_notches_reach_17_db(self):
        # full feedback: k = 0.862; at J1-1 (the phasor's own output) the peaks where the six stages make a whole turn
        # (1.73 x the corner) rise by up to 1 / (1 - k) = +17.2 dB, less what the loop's coupling and low-pass take
        self.assertAlmostEqual(feedback_gain(1.0), 0.862, delta=0.001)
        for pedal, least in ((3.5, 15.0), (4.4, 16.5)):
            quiet, loud = unit(pedal=pedal), unit(pedal=pedal, feedback_a=1.0)
            cell = settled_cell_ohms(quiet)
            settled_cell_ohms(loud)
            peak = stage_corner_hz(cell) * math.tan(math.radians(60))
            grid = [peak * (1 + 0.01 * step) for step in range(-6, 7)]
            with_feedback = responses(loud, grid, outputs=(5,))[0]
            highest = max(with_feedback)
            at = grid[with_feedback.index(highest)]
            rise = db(highest / responses(quiet, [at], outputs=(5,))[0][0])
            with self.subTest(pedal=pedal, peak=round(at)):
                self.assertGreater(rise, least)
                self.assertLess(rise, 17.3)
                self.assertAlmostEqual(db(responses(loud, [at])[0][0]), db(abs(phasor_small_signal_response(
                    at, cell, 1.0, SAMPLERATE, character=MATCHED))), delta=0.1)

    def test_series_is_twelve_stages(self):
        # Phasor B input on Out A: B's output is A's output through B, A's response times B's (twelve all-pass stages
        # from input to output; the manual's "12-stage phase shifter")
        program = unit(phasor_b_input=1.0, pedal=3.0, character=MutronBiPhaseCharacter())
        cell = settled_cell_ohms(program)
        frequencies = [150.0, 420.0, 900.0, 2100.0, 6000.0]
        out_b = responses(program, frequencies, outputs=(1,))[0]
        for frequency, level in zip(frequencies, out_b):
            expected = phasor_small_signal_response(frequency, cell, 0.0, SAMPLERATE, phasor="a") * \
                phasor_small_signal_response(frequency, cell, 0.0, SAMPLERATE, phasor="b")
            with self.subTest(frequency=frequency):
                self.assertAlmostEqual(db(level), db(abs(expected)), delta=0.1)

    def test_stable_at_full_feedback_under_the_fastest_sweep(self):
        # series, both phasors at full feedback on Gen 1, square at 18 Hz, full depth, 3 V noise: bounded by the
        # rails, and silent soon after the input stops (the loops stay under 1)
        program = unit(phasor_b_input=1.0, feedback_a=1.0, feedback_b=1.0, sweep_a_source=0.0, sweep_b_source=0.0,
                       shape_1=1.0, rate_1=18.0, character=MutronBiPhaseCharacter())
        state = 12345
        noise = []
        for _ in range(44100):
            state = (1103515245 * state + 12345) % 2 ** 31
            noise.append(3.0 * (2 * state / 2 ** 31 - 1))
        loud = program.run(44100, [noise])
        for output in loud[:2]:
            self.assertTrue(all(math.isfinite(v) for v in output))
            self.assertLess(max(abs(v) for v in output), 2 * MutronBiPhaseCharacter().rail_volts)
        quiet = program.run(22050, [[0.0] * 22050])
        for output in quiet[:2]:
            self.assertLess(max(abs(v) for v in output[-4410:]), 1e-4)

    def test_rev_sweeps_b_opposite_to_a(self):
        # both phasors on Gen 1: Rev makes B's sweep the mirror of A's (Z15B), so B's corner falls while A's rises; the
        # cells' quick light and slow dark bend the two corners differently, so they are opposite but not mirror images
        for sync, sign, least in ((1.0, -1, 0.8), (0.0, 1, 0.99)):
            program = unit(sweep_a_source=0.0, sweep_b_source=0.0, sweep_sync=sync, rate_1=2.0)
            rendered = program.run(88200, [[0.0] * 88200])
            mirrored = [1 - v for v in rendered[6]] if sync else rendered[6]
            a = [math.log(v) for v in rendered[2][22050:]]
            b = [math.log(v) for v in rendered[3][22050:]]
            mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
            covariance = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
            correlation = covariance / math.sqrt(sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b))
            with self.subTest(sync="Rev" if sync else "Norm"):
                self.assertLess(max(abs(x - y) for x, y in zip(mirrored, rendered[7])), 1e-12)
                self.assertGreater(sign * correlation, least)
                self.assertGreater(max(a) - min(a), math.log(10), "a full-depth sweep spans over a decade")

    def test_the_generators_run_at_their_rate_held_to_the_manuals_range(self):
        for rate, expected in ((3.0, 3.0), (40.0, 18.0), (0.01, 0.1)):
            program = unit(sweep_a_source=0.0, rate_1=rate)
            seconds = 20 if expected < 1 else 2
            sweep = program.run(int(seconds * SAMPLERATE), [[0.0] * int(seconds * SAMPLERATE)])[6]
            crossings = sum(1 for i in range(1, len(sweep)) if sweep[i - 1] < 0.5 <= sweep[i])
            with self.subTest(rate=rate):
                self.assertAlmostEqual(crossings, expected * seconds, delta=1)

    def test_its_latency_is_the_declared_zero_samples(self):
        # latency_samples 0: the rendered output's phase is the Python model's with no delay added (one sample is
        # 360 f / fs degrees: 8.2 at 1 kHz, 32.7 at 4 kHz, far above the tolerance); the dry alone (foot switch off)
        # is the input sample for sample
        program = unit(pedal=3.8)
        latency_samples = unit_block().latency_samples
        self.assertEqual(latency_samples, 0)
        cell = settled_cell_ohms(program)
        for frequency in (250.0, 1000.0, 4000.0):
            signal = sine(frequency, 8820)
            rendered = program.run(8820, [signal])
            model = phasor_small_signal_response(frequency, cell, 0.0, SAMPLERATE, character=MATCHED)
            expected = math.degrees(math.atan2(model.imag, model.real)) - 360.0 * frequency * latency_samples / SAMPLERATE
            found = phase_degrees(rendered[0][4410:], signal[4410:], frequency, SAMPLERATE)
            with self.subTest(frequency=frequency):
                self.assertLess(abs((found - expected + 180.0) % 360.0 - 180.0), 0.5)
        dry = unit(foot_switch_a=0.0, pedal=3.0)
        dry.run(44100, [[0.0] * 44100])              # the bypass cell goes dark
        impulse = [1.0] + [0.0] * 63
        self.assertGreater(dry.run(64, [impulse])[0][0], 0.99, "the dry reaches the output on the input's own sample")

    def test_the_foot_switch_off_leaves_the_dry_signal(self):
        program = unit(foot_switch_a=0.0, pedal=3.0)
        cell = settled_cell_ohms(program)
        program.run(44100, [[0.0] * 44100])          # the bypass cell goes dark
        level = responses(program, [stage_corner_hz(cell)])[0][0]
        self.assertAlmostEqual(db(level), 0.0, delta=0.1)

    def test_the_sweep_character_moves_at_run_time(self):
        # every run-time field given as a Param at its default renders the numbers' unit; moving one moves the sweep:
        # the dark current puts the sweep's bottom where the cells' law says
        fields = {name: getattr(MutronBiPhaseCharacter(), name) for name in RUNTIME_CHARACTER_FIELDS}
        made = MutronBiPhase("unit", input_a_volts="in1", input_b_volts="in1", rate_1_hz="rate_1", rate_2_hz="rate_2",
                             shape_1="shape_1", shape_2="shape_2", depth_a="depth_a", depth_b="depth_b",
                             feedback_a="feedback_a", feedback_b="feedback_b", sweep_a_source="sweep_a_source",
                             sweep_b_source="sweep_b_source", sweep_sync="sweep_sync", phasor_b_input="phasor_b_input",
                             foot_switch_a="foot_switch_a", foot_switch_b="foot_switch_b", pedal_volts="pedal",
                             character_inputs={name: name for name in fields})
        settings = dict(sweep_a_source=0.0, sweep_b_source=1.0, feedback_a=0.7, rate_1=3.0, rate_2=0.7)
        moved = harness([made], dict(PANEL, **settings, **fields), OUTPUTS, samplerate=SAMPLERATE)
        fixed = unit(character=MutronBiPhaseCharacter(), **settings)
        music = sine(220.0, 22050, 2.0)
        for fixed_out, moved_out in zip(fixed.run(22050, [music]), moved.run(22050, [music])):
            self.assertLess(max(abs(x - y) for x, y in zip(fixed_out, moved_out)), 1e-6)
        moved.set_param("led_current_dark_amps", 400e-6)
        moved.set_param("sweep_a_source", 1.0)
        moved.set_param("pedal", 0.0)
        bottom = moved.run(44100, [[0.0] * 44100])[2][-1]
        dark_law = MutronBiPhaseCharacter(led_current_dark_amps=400e-6)
        self.assertAlmostEqual(bottom / stage_corner_hz(cell_ohms(400e-6, dark_law)), 1.0, delta=1e-3)
        # the bypass cell keeps the character's numbers: with the law moved, the foot switch off is still dry
        moved.set_param("cell_law_exponent", 2.0)
        moved.set_param("foot_switch_a", 0.0)
        moved.run(44100, [[0.0] * 44100])
        self.assertAlmostEqual(db(responses(moved, [1000.0])[0][0]), 0.0, delta=0.1)

    def test_it_says_what_it_is_given_wrong(self):
        with self.assertRaises(BuildError):
            MutronBiPhase("unit", input_a_volts="in1", input_b_volts="in1", rate_1_hz="1", rate_2_hz="1", shape_1="0",
                          shape_2="0", depth_a="1", depth_b="1", feedback_a="0", feedback_b="0", sweep_a_source="0",
                          sweep_b_source="0", sweep_sync="0", phasor_b_input="0", foot_switch_a="1",
                          foot_switch_b="1", pedal_volts="0", character=dataclasses.asdict(MATCHED))
        with self.assertRaises(BuildError):        # the rails are not a run-time field
            MutronBiPhase("unit", input_a_volts="in1", input_b_volts="in1", rate_1_hz="1", rate_2_hz="1", shape_1="0",
                          shape_2="0", depth_a="1", depth_b="1", feedback_a="0", feedback_b="0", sweep_a_source="0",
                          sweep_b_source="0", sweep_sync="0", phasor_b_input="0", foot_switch_a="1",
                          foot_switch_b="1", pedal_volts="0", character_inputs={"rail_volts": "13"})
        with self.assertRaises(BuildError):
            MutronBiPhase("unit", input_a_volts="in1", input_b_volts="", rate_1_hz="1", rate_2_hz="1", shape_1="0",
                          shape_2="0", depth_a="1", depth_b="1", feedback_a="0", feedback_b="0", sweep_a_source="0",
                          sweep_b_source="0", sweep_sync="0", phasor_b_input="0", foot_switch_a="1",
                          foot_switch_b="1", pedal_volts="0")


def unit_with_spread_and_taper_at_run_time(**panel):
    """The unit with the stages' spread and the feedback taper as Params (`spread`, `taper`), and the readings a
    display takes: [out a, out b, corner a, corner b, pot a, pot b, spread]."""
    made = MutronBiPhase("unit", input_a_volts="in1", input_b_volts="in1", rate_1_hz="rate_1", rate_2_hz="rate_2",
                         shape_1="shape_1", shape_2="shape_2", depth_a="depth_a", depth_b="depth_b",
                         feedback_a="feedback_a", feedback_b="feedback_b", sweep_a_source="sweep_a_source",
                         sweep_b_source="sweep_b_source", sweep_sync="sweep_sync", phasor_b_input="phasor_b_input",
                         foot_switch_a="foot_switch_a", foot_switch_b="foot_switch_b", pedal_volts="pedal",
                         character_inputs={"stage_corner_spread": "spread", "feedback_pot_taper_exponent": "taper"})
    params = dict(PANEL, **dict(dict(spread=0.05, taper=1.0), **panel))
    readings = ["unit_out_a", "unit_out_b", "unit_corner_a_hz", "unit_corner_b_hz", "unit_pot_a", "unit_pot_b",
                "unit_stage_corner_spread"]
    return made, harness([made], params, readings, samplerate=SAMPLERATE)


def rendered_notch_hz(program, output, around_hz, step=0.01):
    """The rendered response's least point near `around_hz`: |H|^2 at around x e^-step, around, around x e^step (each
    a settled sine), the parabola's vertex on log frequency. Fails unless the middle probe is the least."""
    levels = [level ** 2 for level in responses(program, [around_hz * math.exp(k * step) for k in (-1, 0, 1)],
                                                outputs=(output,))[0]]
    if not levels[1] < min(levels[0], levels[2]):
        raise AssertionError(f"no minimum of output {output} around {around_hz:.1f} Hz: |H|^2 {levels}")
    return around_hz * math.exp(step * (levels[0] - levels[2]) / (2 * (levels[0] - 2 * levels[1] + levels[2])))


class DisplayResponseTests(unittest.TestCase):
    # the display script (response_script_code) = the Python model (phasor_response, phasor_notches_hz), and the
    # notches it finds from the module's own readings (the corner, the wiper, the spread) are the rendered unit's

    def test_the_readings_are_the_wiper_and_the_spread(self):
        _, program = unit_with_spread_and_taper_at_run_time(feedback_a=0.6, feedback_b=0.3, spread=0.2, taper=2.0)
        out = program.run(64, [[0.0] * 64])
        self.assertAlmostEqual(out[4][-1], feedback_pot_position(0.6, MutronBiPhaseCharacter(
            feedback_pot_taper_exponent=2.0)), places=12)
        self.assertAlmostEqual(out[5][-1], 0.09, places=12)
        self.assertAlmostEqual(out[6][-1], 0.2, places=12)

    def test_the_display_script_is_the_modules_response_and_notches(self):
        for character in (MutronBiPhaseCharacter(), MutronBiPhaseCharacter(wet_trim_ohms=2000.0,
                                                                           bypass_led_current_amps=4e-3)):
            block = MutronBiPhase("bi_phase", input_a_volts="0", input_b_volts="0", rate_1_hz="1", rate_2_hz="1",
                                  shape_1="0", shape_2="0", depth_a="1", depth_b="1", feedback_a="0", feedback_b="0",
                                  sweep_a_source="0", sweep_b_source="0", sweep_sync="0", phasor_b_input="0",
                                  foot_switch_a="1", foot_switch_b="1", pedal_volts="0", character=character)
            script = block.response_script_code()
            check_es5({"mutron-bi-phase-response.js": script})
            for corner, position, spread, rate, phasor in ((112.0, 0.0, 0.05, 44100, "a"), (500.0, 0.4, 0.05, 48000, "b"),
                                                           (1800.0, 1.0, 0.3, 22050, "a"), (3400.0, 0.7, 0.0, 96000, "b")):
                with self.subTest(corner=corner, position=position, spread=spread, rate=rate, phasor=phasor):
                    for frequency in (30.0, corner, 7000.0):
                        drawn = float(es5.evaluate(script + f"\nbi_phase_phasor_response({frequency}, {corner}, "
                                                            f"{position}, {spread}, {rate}, '{phasor}')"))
                        self.assertAlmostEqual(drawn / abs(phasor_response(frequency, corner, position, spread, rate,
                                                                           phasor, character)), 1.0, places=9)
                    drawn = [float(v) for v in es5.evaluate(script + f"\nbi_phase_phasor_notches_hz({corner}, "
                                                                     f"{position}, {spread}, {rate}, '{phasor}')"
                                                                     ".join(',')").split(",")]
                    model = phasor_notches_hz(corner, position, spread, rate, phasor, character)
                    self.assertEqual(len(drawn), 3)
                    for x, y in zip(drawn, model):
                        self.assertAlmostEqual(x / y, 1.0, places=6)

    def test_the_rendered_notches_are_where_phasor_notches_hz_finds_them(self):
        # from the low end (the coupling capacitors pull the low notch far up: ~1.9 x its equal-stage place at a
        # 112 Hz corner) to the top, with feedback, spread and a taper; both phasors (their own spread patterns)
        for settings in (dict(pedal=0.4), dict(pedal=2.5, feedback_a=0.6, feedback_b=0.3, spread=0.15),
                         dict(pedal=4.6, feedback_a=1.0, feedback_b=0.8, spread=0.3, taper=2.0)):
            block, program = unit_with_spread_and_taper_at_run_time(**settings)
            silence = program.run(8820, [[0.0] * 8820])
            for side, output in (("a", 0), ("b", 1)):
                corner, position, spread = silence[2 + output][-1], silence[4 + output][-1], silence[6][-1]
                for notch in phasor_notches_hz(corner, position, spread, SAMPLERATE, side, block.character):
                    with self.subTest(side=side, notch=round(notch), **settings):
                        self.assertAlmostEqual(rendered_notch_hz(program, output, notch) / notch, 1.0, delta=0.002)


if __name__ == "__main__":
    unittest.main(verbosity=2)

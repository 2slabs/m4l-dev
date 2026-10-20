"""The Buchla 259 timbre section module (m4l_dev/circuit_modules/buchla_259_timbre_section.py): the folder against
the circuit (DAFx-17 eqs. 8-11 with the original's extras, references/circuits/buchla-259.md §3), and the GenExpr it
writes against the Python model, through our GenExpr renderer (ours, not Max's compiler). Standard library only."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.circuit_modules.buchla_259_timbre_section import (  # noqa: E402
    DRIVE_STAGE_HZ, TONE_FILTER_HZ, Buchla259TimbreSection, Buchla259TimbreSectionCharacter, cell_fold_point_volts,
    cell_node_volts, output_volts, summed_output_volts_unlimited)
from m4l_dev.gen_blocks import gen_code_with_blocks  # noqa: E402
from m4l_dev.genexpr import GenProgram  # noqa: E402
from gen_block_harness import harness  # noqa: E402

ORIGINAL = Buchla259TimbreSectionCharacter()


def section(name="timbre", character=None):
    return Buchla259TimbreSection(name, drive_volts="drive", symmetry_offset_volts="offset", frequency_hz="frequency",
                                  character=character)


class FolderModelTests(unittest.TestCase):
    """The circuit model in Python (what the transfer's pieces are taken from)."""

    def test_the_fold_points_are_the_papers(self):
        # DAFx-17 eq. 8: cell k clips where |Vin| = (Rk1 / Rk2) Vs; at the original's 6 V (circuit §3.1)
        self.assertEqual(ORIGINAL.cell_rail_volts, 6.0)
        self.assertEqual([round(cell_fold_point_volts(k, ORIGINAL), 3) for k in range(5)],
                         [0.600, 2.994, 5.460, 1.800, 4.080])
        for k in range(5):
            threshold = cell_fold_point_volts(k, ORIGINAL)
            self.assertEqual(cell_node_volts(k, threshold * 0.999, ORIGINAL), 0.0, "the deadband")
            self.assertGreater(cell_node_volts(k, threshold * 1.01, ORIGINAL), 0.0)
        # eq. 9 at Vin = 10 V (circuit §3.2: 7.83, 2.64, 1.28, 4.71, 1.58)
        self.assertEqual([round(cell_node_volts(k, 10.0, ORIGINAL), 2) for k in range(5)],
                         [7.83, 2.64, 1.28, 4.71, 1.58])

    def test_the_sum_is_the_papers(self):
        # eqs. 10-11: inside every deadband only the dry path, RF2 RF1 / (R7 R6,3) = 5; eq. 9's slopes past cell 1
        self.assertAlmostEqual(output_volts(0.5, ORIGINAL), 2.5)
        self.assertAlmostEqual(output_volts(1.0, ORIGINAL), 5 - 12 * (100e3 * 100e3 * 1.0 - 100e3 * 10e3 * 6) / 1.2e10)
        for x in (0.3, 1.0, 3.0, 5.0, 8.0):                    # odd inside the input floor: odd harmonics only
            self.assertAlmostEqual(output_volts(-x, ORIGINAL), -output_volts(x, ORIGINAL), msg=x)

    def test_the_originals_extras(self):
        # cell 1's node stops 0.5 V under its negative rail from about -8.4 V in (one side only), and the zener
        # limiter holds the sum at about +-5.1 V; the drive stage's and the tone filter's corners
        self.assertAlmostEqual(cell_node_volts(0, -9.0, ORIGINAL), -6.5)
        self.assertAlmostEqual(cell_node_volts(0, 9.0, ORIGINAL), 7.0, places=6)
        self.assertNotAlmostEqual(output_volts(-9.0, ORIGINAL), -output_volts(9.0, ORIGINAL), places=1)
        self.assertEqual(max(abs(output_volts(x / 10, ORIGINAL)) for x in range(-150, 151)), ORIGINAL.limiter_volts)
        self.assertAlmostEqual(ORIGINAL.limiter_volts, 5.1, places=9)
        self.assertGreater(abs(summed_output_volts_unlimited(12.0, ORIGINAL)), ORIGINAL.limiter_volts)
        self.assertAlmostEqual(DRIVE_STAGE_HZ, 10262, delta=1)
        self.assertAlmostEqual(TONE_FILTER_HZ, 1326, delta=1)

    def test_the_output_stays_near_its_peak_and_under_its_limiter(self):
        timbre = section()
        for drive in (timbre.first_fold_volts, 2.0, 5.0, 8.0):
            top = max(abs(output_volts(drive * math.sin(2 * math.pi * i / 1000), ORIGINAL)) for i in range(1000))
            self.assertLess(top, timbre.output_peak_volts * 1.35, drive)
        top = max(abs(output_volts(10.0 * math.sin(2 * math.pi * i / 1000), ORIGINAL)) for i in range(1000))
        self.assertLessEqual(top, ORIGINAL.limiter_volts)

    def test_the_rail_is_the_units_character(self):
        # a starved build (Theelen's TL072 cells, ~4.5 V): every fold point and the output's peak scale with the rail
        starved = Buchla259TimbreSectionCharacter(cell_rail_volts=4.5)
        self.assertAlmostEqual(cell_fold_point_volts(0, starved), 0.45)
        self.assertAlmostEqual(section(character=starved).output_peak_volts, 2.4)
        with self.assertRaises(BuildError):
            section(character=Buchla259TimbreSectionCharacter(cell_rail_volts=0.0))


class FolderGenExprTests(unittest.TestCase):
    """The module's GenExpr: its transfer and antiderivative against the Python model, and its segments' means."""

    def test_the_pieces_and_their_integral_are_the_model(self):
        timbre = section()
        table = timbre.table
        code = "\n".join(timbre.functions().values()) + (f"\nout1 = {table.value_call('in1')};\n"
                                                        f"out2 = {table.integral_call('in1')};\n")
        points = sorted({x / 7 for x in range(-110, 111)} | {p[0] + d for p in table.pieces[1:] for d in (-1e-6, 1e-6)})
        values, integrals = GenProgram(code, 1, 2).run(len(points), [points])
        for x, value, integral in zip(points, values, integrals):
            self.assertAlmostEqual(value, output_volts(x, ORIGINAL), places=6, msg=x)
            self.assertAlmostEqual(integral, table.integral(x), places=6, msg=x)
        for x in (-12.0, -9.0, -1.0, 2.0, 7.0, 11.0):          # the integral is the folder's area from 0
            steps = 2000
            area = sum(output_volts(x * (k + 0.5) / steps, ORIGINAL) for k in range(steps)) * x / steps
            self.assertAlmostEqual(table.integral(x), area, places=4, msg=x)

    def test_the_running_segment_is_the_folders_mean_over_each_step(self):
        # a 5 V, 200 Hz sine with a 0.4 V offset, the drive stage's roll-off at 200 Hz: each step's output is the
        # folder's mean along the straight line between the bus's last two values
        timbre = section()
        frequency, drive, offset, count = 200.0, 5.0, 0.4, 300
        statements = ("sine = in1;\n" + timbre.point_statements("now", "sine") + "\n"
                      + f"out1 = {timbre.segment_output_volts('now', timbre.running_point)};\n"
                      + "out2 = now_folder_input_volts;\n" + timbre.remember_statements("now"))
        template = (f"/*GEN_BLOCK_FUNCTIONS*/\nParam drive({drive!r});\nParam offset({offset!r});\n"
                    f"Param frequency({frequency!r});\n/*GEN_BLOCK_DECLARATIONS*/\n/*TIMBRE*/\n" + statements)
        code = gen_code_with_blocks(template, [timbre], "test harness")
        program = GenProgram(code, 1, 2)
        sine = [math.sin(2 * math.pi * frequency * i / 44100) for i in range(count)]
        out, bus = program.run(count, [sine])
        gain = 1 / math.sqrt(1 + (frequency / DRIVE_STAGE_HZ) ** 2)
        for i in range(1, count):
            self.assertAlmostEqual(bus[i], drive * gain * sine[i] + offset, places=12)
            steps = 400
            mean = sum(output_volts(bus[i - 1] + (bus[i] - bus[i - 1]) * (k + 0.5) / steps, ORIGINAL)
                       for k in range(steps)) / steps
            self.assertAlmostEqual(out[i], mean, delta=2e-4, msg=i)

    def test_two_units_are_two_folders_in_one_patch(self):
        original, starved = section("original"), section("starved", Buchla259TimbreSectionCharacter(cell_rail_volts=4.5))
        self.assertNotEqual(original.table.function_name, starved.table.function_name)
        harness([original, starved], {"drive": 1.0, "offset": 0.0, "frequency": 100.0},
                ["original_drive_stage_gain + starved_drive_stage_gain"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

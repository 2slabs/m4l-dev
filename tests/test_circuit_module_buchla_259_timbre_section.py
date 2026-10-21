"""The Buchla 259 timbre section module (m4l_dev/circuit_modules/buchla_259_timbre_section.py): the folder against
the circuit (DAFx-17 eqs. 8-11 with the original's extras, references/circuits/buchla-259.md §3), and the GenExpr it
writes against the Python model, through our GenExpr renderer (ours, not Max's compiler). Standard library only."""
import cmath
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
from m4l_dev.techniques.halfband_oversampler import HalfbandDownsampler, HalfbandLinearPhaseDownsampler  # noqa: E402
from gen_block_harness import (coherent_frequency, coherent_worst_alias_db, complex_amplitude_at,  # noqa: E402
                               equalised_adaa_outputs, exact_second_order_mean, harness)

ORIGINAL = Buchla259TimbreSectionCharacter()


def section(name="timbre", character=None, oversampling=2):
    """A unit wired as the instruments wire it (2x unless a test says)."""
    return Buchla259TimbreSection(name, drive_volts="drive", symmetry_offset_volts="offset", frequency_hz="frequency",
                                  oversampling=oversampling, character=character)


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
        statements = ("sine = in1;\n" + timbre.point_statements("now", "sine") + "\n" + timbre.output_statements("now") + "\n"
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

    def folder_program(self, drive, frequency, offset=0.0, samplerate=44100.0, oversampling=2):
        """The section on in1 (the sine), Params drive / offset / frequency: out1 the second-order output, out2 the
        running segment's first-order mean, out3 the bus."""
        timbre = section(oversampling=oversampling)
        statements = ("sine = in1;\n" + timbre.point_statements("now", "sine") + "\n"
                      + timbre.output_statements("now") + "\n"
                      + f"out1 = {timbre.output_volts_at('now')};\n"
                      + f"out2 = {timbre.segment_output_volts('now', timbre.running_point)};\n"
                      + "out3 = now_folder_input_volts;\n" + timbre.remember_statements("now"))
        template = (f"/*GEN_BLOCK_FUNCTIONS*/\nParam drive({drive!r});\nParam offset({offset!r});\n"
                    f"Param frequency({frequency!r});\n/*GEN_BLOCK_DECLARATIONS*/\n/*TIMBRE*/\n" + statements)
        return GenProgram(gen_code_with_blocks(template, [timbre], "test harness"), 1, 3, samplerate=samplerate)

    def test_the_output_is_second_order_adaa_of_the_folder_equalised_for_its_rate(self):
        # each step: Bilbao et al.'s eq. (15) through the last three bus values on the folder's pieces (= the circuit
        # model, test above), exact, then the technique's equaliser for the unit's oversampling (2x: five taps; 1x:
        # none), on a 5 V, 200 Hz sine with a 0.4 V offset (from step 2, once the bus has two before it)
        frequency, count = 200.0, 300
        sine = [math.sin(2 * math.pi * frequency * i / 44100) for i in range(count)]
        for oversampling, latency_steps in ((1, 1), (2, 3)):
            unit = section(oversampling=oversampling)
            self.assertEqual(unit.latency_steps, latency_steps)
            out, _, bus = self.folder_program(5.0, frequency, 0.4, oversampling=oversampling).run(count, [sine])
            raw_means = [exact_second_order_mean(unit.table.pieces, bus[i], bus[i - 1], bus[i - 2])
                         for i in range(2, count)]
            equalised = equalised_adaa_outputs(raw_means, unit.equaliser.taps)
            for i in range(2 + unit.equaliser.length - 1, count):      # the equaliser's taps all on exact means
                self.assertAlmostEqual(out[i], equalised[i - 2], delta=1e-9, msg=(oversampling, i))

    def straight_middle_gain(self, oversampling, frequency):
        """A quiet sine on the straight middle piece (the dry path, slope 5) at 48 kHz x `oversampling`: the output re
        the bus times 5, `latency_steps` before (the drive stage's roll-off is in the bus, so the bus is the
        reference)."""
        rate, count, settle = 48000.0 * oversampling, 3000, 100
        sine = [math.sin(2 * math.pi * frequency * i / rate) for i in range(count)]
        out, _, bus = self.folder_program(0.3, frequency, samplerate=rate, oversampling=oversampling).run(count, [sine])
        late = section(oversampling=oversampling).latency_steps
        return complex_amplitude_at(out[settle:], frequency, rate) / complex_amplitude_at(
            [5 * value for value in bus[settle - late:count - late]], frequency, rate)

    def test_the_straight_middle_is_flat_to_20_khz_at_2x(self):
        # within 0.0973 dB up to 20 kHz at 2x 48 kHz (raw ADAA2, its 3-tap mean: -1.3 dB at 10 kHz, -5.9 dB at 20 kHz)
        for frequency in (1000.0, 5000.0, 10000.0, 15000.0, 18000.0, 20000.0):
            gain = self.straight_middle_gain(2, frequency)
            self.assertLess(abs(20 * math.log10(abs(gain))), 0.0973, msg=frequency)
            self.assertLess(abs(gain.imag), 1e-6, msg=frequency)

    def test_the_straight_middle_at_1x_is_the_three_tap_mean_and_never_lifted(self):
        # at 1x (no equaliser: the technique's measurements) the 3-tap mean, never above 0 dB to the host's Nyquist:
        # within 0.3 dB to 2.4 kHz, -1.3 dB at 5 kHz, -5.9 dB at 10 kHz at 48 kHz
        for frequency in (1000.0, 2400.0, 5000.0, 10000.0, 15000.0, 20000.0, 23000.0):
            gain = self.straight_middle_gain(1, frequency)
            self.assertAlmostEqual(gain.real, (1 + 2 * math.cos(2 * math.pi * frequency / 48000.0)) / 3, delta=1e-9,
                                   msg=frequency)
            self.assertLess(abs(gain.imag), 1e-6, msg=frequency)
            self.assertLessEqual(abs(gain), 1.0, msg=frequency)

    def test_the_oversampling_must_be_known(self):
        with self.assertRaises(TypeError):                     # never a default
            Buchla259TimbreSection("timbre", drive_volts="drive", symmetry_offset_volts="offset",
                                   frequency_hz="frequency")
        for unknown in (3, 4, 0, True, None):
            with self.assertRaises(BuildError, msg=unknown):
                section(oversampling=unknown)

    def test_the_output_needs_its_statements_first(self):
        timbre = section()
        with self.assertRaises(BuildError):
            timbre.output_volts_at("now")
        with self.assertRaises(BuildError):
            timbre.remember_statements("now")
        timbre.output_statements("now")
        self.assertEqual(timbre.output_volts_at("now"), "now_folder_output_volts")

    def test_second_order_lowers_the_aliases(self):
        # a pure sine at 2x 48 kHz, the worst alias under 20 kHz re the fundamental (no leakage: a whole number of
        # cycles in the window). Measured 2026-10-20 (16384 points), first order -> second raw (before its equaliser)
        # -> second equalised: 4 V at 3.1 kHz -22.3 -> -36.4 -> -31.5 dB, 8 V at 1.37 kHz -33.7 -> -48.7 -> -45.8 dB,
        # 4 V at 410 Hz -55.8 -> -69.8 -> -65.9 dB (the trivial folder: -3.5, -16.5, -41.8 dB). The equaliser lifts an
        # alias as it lifts the harmonics at its frequency (up to +5.8 dB at 20 kHz): under 16 kHz, -44.5 -> -42.6,
        # -48.7 -> -45.8, -74.8 -> -71.3 dB
        rate, length, settle = 96000.0, 16384, 300
        for drive, frequency, first_order, second_order in ((4.0, 3100.0, -22.3, -31.5), (8.0, 1370.0, -33.7, -45.8),
                                                            (4.0, 410.0, -55.8, -65.9)):
            fundamental_bin, frequency = coherent_frequency(frequency, rate, length)
            sine = [math.sin(2 * math.pi * frequency * i / rate) for i in range(length + settle)]
            second, first, _ = self.folder_program(drive, frequency, samplerate=rate).run(length + settle, [sine])
            measured = [coherent_worst_alias_db(output[settle:], fundamental_bin, rate, 20000) for output in (first, second)]
            self.assertAlmostEqual(measured[0], first_order, delta=1.5, msg=f"{drive} V, {frequency} Hz, first order")
            self.assertLess(measured[1], second_order + 1.5, msg=f"{drive} V, {frequency} Hz, second order")
            self.assertLess(measured[1], measured[0] - 8)

    def test_second_order_lowers_the_aliases_at_1x(self):
        # the same at 1x 48 kHz, the unit unequalised (the technique's choice). Measured 2026-10-20, first order ->
        # second: 4 V at 3.1 kHz -6.3 -> -25.3 dB, 8 V at 1.37 kHz -4.0 -> -11.0 dB, 4 V at 410 Hz -30.4 -> -36.3 dB.
        # Through the 2x equaliser instead (5af0d09): -15.5, +3.5, -22.0 dB; through the best 1x equaliser (+-0.3 dB to
        # 8.8 kHz, the response never above +1 dB): -18.6, -1.4, -26.7 dB
        rate, length, settle = 48000.0, 16384, 300
        for drive, frequency, first_order, second_order in ((4.0, 3100.0, -6.3, -25.3), (8.0, 1370.0, -4.0, -11.0),
                                                            (4.0, 410.0, -30.4, -36.3)):
            fundamental_bin, frequency = coherent_frequency(frequency, rate, length)
            sine = [math.sin(2 * math.pi * frequency * i / rate) for i in range(length + settle)]
            second, first, _ = self.folder_program(drive, frequency, samplerate=rate, oversampling=1).run(
                length + settle, [sine])
            measured = [coherent_worst_alias_db(output[settle:], fundamental_bin, rate, 20000) for output in (first, second)]
            self.assertAlmostEqual(measured[0], first_order, delta=1.5, msg=f"{drive} V, {frequency} Hz, first order")
            self.assertAlmostEqual(measured[1], second_order, delta=1.5, msg=f"{drive} V, {frequency} Hz, second order")

    def test_a_hot_fold_at_2x_peaks_past_the_ideal_through_the_elliptic_downsampler(self):
        # references/dsp.md ("After the 259 folder at 2x"): the unit at 2x 48 kHz on a pure sine, brought down by the
        # kit's elliptic HalfbandDownsampler and its HalfbandLinearPhaseDownsampler; the steady peak re the ideal (the
        # folded tone's harmonics below 24 kHz, flat, their own phases), DC off. Measured (scratchpad numpy, = this renderer):
        # 8 V at 987.8 Hz elliptic 7.08, linear phase 4.06, ideal 3.00; 10 V at 784.0 Hz 8.45, 5.49, 4.46. The
        # elliptic's phase near its corner is the 1.5-1.7x between the two; the linear phase's own excess is the 2x
        # equaliser's lift above 20 kHz folded back by the half-band's transition band (none without the equaliser).
        rate, count, settle = 48000.0, 12000, 1500
        for drive, frequency, elliptic_peak, linear_phase_peak, ideal_peak in (
                (8.0, 987.7666025122480, 7.08, 4.06, 3.00), (10.0, 783.9908719634985, 8.45, 5.49, 4.46)):
            sine = [math.sin(2 * math.pi * frequency * i / (2 * rate)) for i in range(2 * count)]
            folded, _, _ = self.folder_program(drive, frequency, samplerate=2 * rate).run(2 * count, [sine])
            firsts, seconds = folded[0::2], folded[1::2]
            peaks = {}
            for downsampler_type in (HalfbandDownsampler, HalfbandLinearPhaseDownsampler):
                down = downsampler_type("down", first="in1", second="in2")
                out = harness([down], {}, ["down_out"], num_inputs=2, samplerate=rate).run(count, [firsts, seconds])[0]
                steady = out[settle:]
                mean = sum(steady) / len(steady)     # 10 V reaches cell 1's one-sided floor: a DC, taken off
                peaks[downsampler_type] = max(abs(value - mean) for value in steady)
            gain = 1 / math.sqrt(1 + (frequency / DRIVE_STAGE_HZ) ** 2)
            points = 4096
            transfer = [output_volts(drive * gain * math.sin(2 * math.pi * j / points), ORIGINAL) for j in range(points)]
            harmonics = [2 / points * sum(value * cmath.exp(-2j * math.pi * k * j / points) for j, value in enumerate(transfer))
                         for k in range(int(24000 // frequency) + 1)]
            ideal = max(abs(sum((harmonics[k] * cmath.exp(2j * math.pi * k * frequency * n / rate)).real
                                for k in range(1, len(harmonics)))) for n in range(count - settle))
            self.assertAlmostEqual(ideal, ideal_peak, delta=0.03, msg=(drive, frequency))
            self.assertAlmostEqual(peaks[HalfbandDownsampler], elliptic_peak, delta=0.05, msg=(drive, frequency))
            self.assertAlmostEqual(peaks[HalfbandLinearPhaseDownsampler], linear_phase_peak, delta=0.05,
                                   msg=(drive, frequency))
            self.assertGreater(peaks[HalfbandDownsampler], 1.5 * peaks[HalfbandLinearPhaseDownsampler])

    def test_two_units_are_two_folders_in_one_patch(self):
        original, starved = section("original"), section("starved", Buchla259TimbreSectionCharacter(cell_rail_volts=4.5))
        self.assertNotEqual(original.table.function_name, starved.table.function_name)
        harness([original, starved], {"drive": 1.0, "offset": 0.0, "frequency": 100.0},
                ["original_drive_stage_gain + starved_drive_stage_gain"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""The Buchla 259 principal oscillator module (m4l_dev/circuit_modules/buchla_259_principal_oscillator.py): the
shaped sine's harmonics, and its phase under a frequency, a sweep, through-zero FM and a reset, through our GenExpr
renderer (ours, not Max's compiler). Standard library only."""
import cmath
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.circuit_modules.buchla_259_principal_oscillator import (  # noqa: E402
    Buchla259PrincipalOscillator, Buchla259PrincipalOscillatorCharacter, shaped_sine)
from m4l_dev.gen_blocks import gen_code_with_blocks  # noqa: E402
from m4l_dev.genexpr import GenProgram  # noqa: E402
from gen_block_harness import frequency_by_zero_crossings, harness  # noqa: E402

SAMPLERATE = 44100.0
SHAPER_THIRD_HARMONIC_DB = -38.4      # the module's stated imperfection at the default drive


def harmonic(wave, n):
    return abs(sum(x * cmath.exp(-2j * math.pi * n * i / len(wave)) for i, x in enumerate(wave)))


class ShapedSineTests(unittest.TestCase):
    def test_the_sine_shaper_is_slight_and_odd(self):
        count = 2048
        wave = [shaped_sine(i / count, Buchla259PrincipalOscillatorCharacter()) for i in range(count)]
        self.assertAlmostEqual(20 * math.log10(harmonic(wave, 3) / harmonic(wave, 1)), SHAPER_THIRD_HARMONIC_DB,
                               delta=0.5)
        self.assertLess(harmonic(wave, 2) / harmonic(wave, 1), 1e-9, "symmetric: no even harmonics")
        self.assertAlmostEqual(max(wave), 1.0, places=6)

    def test_a_drive_of_one_is_a_perfect_sine_and_a_bad_drive_fails(self):
        perfect = Buchla259PrincipalOscillatorCharacter(sine_shaper_drive=1.0)
        for i in range(64):
            self.assertAlmostEqual(shaped_sine(i / 64, perfect), math.sin(2 * math.pi * i / 64), places=12)
        with self.assertRaises(BuildError):
            Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0",
                                         character=Buchla259PrincipalOscillatorCharacter(sine_shaper_drive=1.2))
        with self.assertRaises(BuildError):
            Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0", oversampling=0)


def oscillator_program(frequency_hz="frequency", frequency_modulation_hz="fm", oversampling=1, reset="0"):
    """A harness running `oversampling` steps a sample; outputs the last step's sine and phase. `reset` (an
    expression) restarts the phase before the steps."""
    oscillator = Buchla259PrincipalOscillator("osc", frequency_hz=frequency_hz,
                                              frequency_modulation_hz=frequency_modulation_hz,
                                              oversampling=oversampling)
    template = ("/*GEN_BLOCK_FUNCTIONS*/\nParam frequency(440);\nParam fm(0);\nHistory time(0);\n"
                "/*GEN_BLOCK_DECLARATIONS*/\n"
                f"if ({reset} > 0.5) {{\n{oscillator.reset_statements()}\n}}\n"
                + "/*OSC*/\n" * oversampling + "time = time + 1;\nout1 = osc_sine;\nout2 = osc_phase;\n")
    return GenProgram(gen_code_with_blocks(template, [oscillator], "test harness"), 1, 2, samplerate=SAMPLERATE)


class PhaseTests(unittest.TestCase):
    def test_it_sounds_at_its_frequency_at_any_oversampling(self):
        for oversampling in (1, 2):
            sine = oscillator_program(oversampling=oversampling).run(8820, [[0.0] * 8820])[0]
            self.assertAlmostEqual(frequency_by_zero_crossings(sine, SAMPLERATE), 440.0, delta=0.05)
            self.assertEqual(sine[0], shaped_sine(oversampling * 440.0 / (oversampling * SAMPLERATE),
                                                  Buchla259PrincipalOscillatorCharacter()))

    def test_through_zero_fm_runs_the_phase_backwards(self):
        program = oscillator_program()
        program.set_param("fm", -660.0)                  # 440 - 660: -220 Hz
        phase = program.run(100, [[0.0] * 100])[1]
        self.assertAlmostEqual((phase[0] - phase[50]) % 1.0, 50 * 220 / SAMPLERATE, places=9)

    def test_a_sweep_is_followed_at_every_step(self):
        # frequency 2000 Hz falling 30 Hz a sample (a drum's pitch sweep): the phase is the sum of every step's
        program = oscillator_program(frequency_hz="2000 - 30 * time", oversampling=2)
        phase = program.run(40, [[0.0] * 40])[1]
        expected = sum(2 * (2000 - 30 * n) / (2 * SAMPLERATE) for n in range(40)) % 1.0
        self.assertAlmostEqual(phase[-1], expected, places=9)

    def test_a_reset_starts_the_cycle(self):
        program = oscillator_program(reset="time > 99.5 && time < 100.5")
        sine, phase = program.run(102, [[0.0] * 102])
        self.assertAlmostEqual(phase[100], 440 / SAMPLERATE, places=12)     # reset, then one step
        self.assertAlmostEqual(sine[100], shaped_sine(440 / SAMPLERATE, Buchla259PrincipalOscillatorCharacter()),
                               places=12)

    def test_it_sits_in_the_harness(self):
        harness([Buchla259PrincipalOscillator("osc", frequency_hz="100", frequency_modulation_hz="0")], {}, ["osc_sine"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

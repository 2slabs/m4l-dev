"""The Buchla 259 modulation oscillator module (m4l_dev/circuit_modules/buchla_259_modulation_oscillator.py): its
waves are the trivial waves now (the look-ahead undone), band-limited, restartable, with their running integral,
through our GenExpr renderer (ours, not Max's compiler). Standard library only."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev.circuit_modules.buchla_259_modulation_oscillator import (  # noqa: E402
    WAVES, Buchla259ModulationOscillator)
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.gen_blocks import gen_code_with_blocks  # noqa: E402
from m4l_dev.genexpr import GenProgram  # noqa: E402
from gen_block_harness import worst_alias_db  # noqa: E402

SAMPLERATE = 44100.0


def trivial(phase, wave):
    phase %= 1.0
    return [math.sin(2 * math.pi * phase), 1 - 4 * abs(phase - 0.5), 2 * phase - 1, -1 if phase < 0.5 else 1][wave]


def oscillator_program(wave, frequency, reset="0"):
    """One step a sample; outputs the band-limited wave, the phase, the trivial wave and its integral at the phase."""
    oscillator = Buchla259ModulationOscillator("mod", frequency_hz=repr(frequency), wave=str(wave), oversampling=1)
    template = ("/*GEN_BLOCK_FUNCTIONS*/\nHistory time(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
                f"if ({reset} > 0.5) {{\n{oscillator.reset_statements()}\n}}\n/*MOD*/\ntime = time + 1;\n"
                f"out1 = mod_out;\nout2 = mod_phase;\nout3 = {oscillator.wave_at('mod_phase')};\n"
                f"out4 = {oscillator.wave_integral_at('mod_phase')};\n")
    return GenProgram(gen_code_with_blocks(template, [oscillator], "test harness"), 1, 4, samplerate=SAMPLERATE)


class ModulationOscillatorTests(unittest.TestCase):
    def test_every_wave_is_the_trivial_wave_now_away_from_its_edges(self):
        for wave in range(len(WAVES)):
            out, phase, naive, _ = oscillator_program(wave, 110.0).run(1000, [[0.0] * 1000])
            for i in range(10, 1000):
                edge_distance = min(abs(phase[i] - 0.5), phase[i], 1 - phase[i]) * SAMPLERATE / 110
                self.assertAlmostEqual(naive[i], trivial(phase[i], wave), places=9)
                if edge_distance > 3:
                    self.assertAlmostEqual(out[i], naive[i], places=6, msg=(WAVES[wave], i))

    def test_the_saw_and_the_square_are_band_limited(self):
        fundamental = 2093.0                                     # C7
        for wave in (2, 3):
            out = oscillator_program(wave, fundamental).run(8192, [[0.0] * 8192])[0][100:]
            naive = [trivial(fundamental * i / SAMPLERATE, wave) for i in range(8192)][100:]
            harmonics = range(11, 60)
            self.assertLess(worst_alias_db(out, fundamental, harmonics, SAMPLERATE, 10000),
                            worst_alias_db(naive, fundamental, harmonics, SAMPLERATE, 10000) - 30, WAVES[wave])

    def test_a_reset_restarts_the_cycle_with_nothing_of_the_old_wave(self):
        out, phase, _, _ = oscillator_program(2, 1000.0, reset="time > 99.5 && time < 100.5").run(110, [[0.0] * 110])
        step = 1000.0 / SAMPLERATE
        self.assertEqual(phase[100], 0.0)  # the reset's step is the cycle's start: the host sample's own time
        for i in range(100, 105):          # the saw from its start at the reset's sample, exactly (no edge falls here)
            self.assertAlmostEqual(out[i], 2 * ((i - 100) * step) - 1, places=9, msg=i)

    def test_the_integral_is_the_waves_running_integral(self):
        for wave in range(len(WAVES)):
            _, phase, naive, integral = oscillator_program(wave, 50.0).run(2000, [[0.0] * 2000])
            for i in range(1, 2000):
                if phase[i - 1] < phase[i] and not phase[i - 1] < 0.5 <= phase[i]:   # no edge between: d(integral) = wave d(phase)
                    slope = (integral[i] - integral[i - 1]) / (phase[i] - phase[i - 1])
                    self.assertAlmostEqual(slope, 0.5 * (naive[i] + naive[i - 1]), delta=2e-3, msg=(WAVES[wave], i))
            self.assertAlmostEqual(min(abs(v) for v in integral), 0.0, places=3)   # periodic, from 0 at phase 0

    def test_its_oversampling_is_required_and_a_whole_number_of_steps(self):
        for bad in (0, -1, 1.5, True, "2"):
            with self.assertRaises(BuildError, msg=bad):
                Buchla259ModulationOscillator("mod", frequency_hz="1", wave="0", oversampling=bad)
        with self.assertRaises(TypeError, msg="no default"):
            Buchla259ModulationOscillator("mod", frequency_hz="1", wave="0")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""The Buchla 259 principal oscillator module (m4l_dev/circuit_modules/buchla_259_principal_oscillator.py): the
shaped sine's harmonics, its phase under a frequency, a sweep, through-zero FM and a reset, the run-time shaper
drive and the band-limited corners, through our GenExpr renderer (ours, not Max's compiler). Standard library only."""
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
from gen_block_harness import folded, frequency_by_zero_crossings, harness, worst_alias_db  # noqa: E402

SAMPLERATE = 44100.0
SHAPER_THIRD_HARMONIC_DB = -38.4      # the module's stated imperfection at the default drive
# the sine's latency in steps (the edges' look-ahead), as an instance reports it
SINE_LATENCY_STEPS = Buchla259PrincipalOscillator("probe", frequency_hz="1", frequency_modulation_hz="0",
                                                  oversampling=1).latency_steps


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
            Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0", oversampling=1,
                                         character=Buchla259PrincipalOscillatorCharacter(sine_shaper_drive=1.2))

    def test_its_latency_is_two_steps_in_host_samples_at_its_oversampling(self):
        for oversampling, latency_samples in ((1, 2), (2, 1)):
            oscillator = Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0",
                                                      oversampling=oversampling)
            self.assertEqual((oscillator.latency_steps, oscillator.latency_samples), (2, latency_samples))

    def test_its_oversampling_is_required_and_a_whole_number_of_steps(self):
        for bad in (0, -1, 1.5, True, "2"):
            with self.assertRaises(BuildError, msg=bad):
                Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0", oversampling=bad)
        with self.assertRaises(TypeError, msg="no default"):
            Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0")


def oscillator_program(frequency_hz="frequency", frequency_modulation_hz="fm", oversampling=1, reset="0",
                       samplerate=SAMPLERATE, character=None, character_inputs=None):
    """A harness running `oversampling` steps a sample; outputs the last step's sine, its phase (the sine's, LATENCY
    steps late) and the phase now. `reset` (an expression) restarts the phase before the steps. Params: frequency,
    fm, drive."""
    oscillator = Buchla259PrincipalOscillator("osc", frequency_hz=frequency_hz,
                                              frequency_modulation_hz=frequency_modulation_hz,
                                              oversampling=oversampling, character=character,
                                              character_inputs=character_inputs)
    template = ("/*GEN_BLOCK_FUNCTIONS*/\nParam frequency(440);\nParam fm(0);\nParam drive(0.95);\nHistory time(0);\n"
                "/*GEN_BLOCK_DECLARATIONS*/\n"
                f"if ({reset} > 0.5) {{\n{oscillator.reset_statements()}\n}}\n"
                + "/*OSC*/\n" * oversampling + "time = time + 1;\nout1 = osc_sine;\nout2 = osc_sine_phase;\n"
                "out3 = osc_phase;\n")
    return GenProgram(gen_code_with_blocks(template, [oscillator], "test harness"), 1, 3, samplerate=samplerate)


def run(program, count):
    return program.run(count, [[0.0] * count])


def away_from_the_corners(phase, step):
    """True where the phase is more than three steps from the triangle's peak, trough and the cycle's start (where
    the band-limited edges correct nothing)."""
    return all(abs((phase - edge + 0.5) % 1.0 - 0.5) > 3 * abs(step) for edge in (0.25, 0.75))


class PhaseTests(unittest.TestCase):
    def test_it_sounds_at_its_frequency_at_any_oversampling(self):
        for oversampling in (1, 2):
            sine = run(oscillator_program(oversampling=oversampling), 8820)[0][10:]
            self.assertAlmostEqual(frequency_by_zero_crossings(sine, SAMPLERATE), 440.0, delta=0.05)

    def test_the_sine_is_the_shaped_wave_at_its_phase_latency_steps_late(self):
        sine, sine_phase, phase = run(oscillator_program(), 400)
        step = 440 / SAMPLERATE
        for i in range(SINE_LATENCY_STEPS, 400):
            self.assertEqual(sine_phase[i], phase[i - SINE_LATENCY_STEPS])
            if away_from_the_corners(sine_phase[i], step):
                self.assertAlmostEqual(sine[i], shaped_sine(sine_phase[i], Buchla259PrincipalOscillatorCharacter()),
                                       places=13)

    def test_through_zero_fm_runs_the_phase_backwards(self):
        program = oscillator_program()
        program.set_param("fm", -660.0)                  # 440 - 660: -220 Hz
        phase = run(program, 100)[2]
        self.assertAlmostEqual((phase[0] - phase[50]) % 1.0, 50 * 220 / SAMPLERATE, places=9)

    def test_fm_is_exact_band_limiting_finds_its_corners_on_the_exact_phase(self):
        # a perfect sine (no corners) under a hot audio-rate FM: the sine of the exactly summed phase, LATENCY late
        program = oscillator_program(frequency_modulation_hz="6000 * sin(6.283185307179586 * 5000 * time / samplerate)",
                                     samplerate=96000.0,
                                     character=Buchla259PrincipalOscillatorCharacter(sine_shaper_drive=1.0))
        program.set_param("frequency", 2000.0)
        sine = run(program, 2000)[0]
        phase = 0.0
        for i in range(2000 - SINE_LATENCY_STEPS):
            phase += (2000 + 6000 * math.sin(2 * math.pi * 5000 * i / 96000)) / 96000
            self.assertAlmostEqual(sine[i + SINE_LATENCY_STEPS], math.sin(2 * math.pi * phase), places=9)

    def test_a_sweep_is_followed_at_every_step(self):
        # frequency 2000 Hz falling 30 Hz a sample (a drum's pitch sweep): the phase is the sum of every step's
        program = oscillator_program(frequency_hz="2000 - 30 * time", oversampling=2)
        phase = run(program, 40)[2]
        expected = sum(2 * (2000 - 30 * n) / (2 * SAMPLERATE) for n in range(40)) % 1.0
        self.assertAlmostEqual(phase[-1], expected, places=9)

    def test_a_reset_starts_the_cycle_and_reaches_the_sine_latency_steps_later(self):
        program = oscillator_program(reset="time > 99.5 && time < 100.5")
        sine, sine_phase, phase = run(program, 120)
        step = 440 / SAMPLERATE
        self.assertAlmostEqual(phase[100], step, places=12)                 # reset, then one step
        self.assertAlmostEqual(sine_phase[100 + SINE_LATENCY_STEPS], step, places=12)
        self.assertGreater(sine_phase[100 + SINE_LATENCY_STEPS - 1], 0.5)       # the old cycle until then
        for i in range(100 + SINE_LATENCY_STEPS + 2, 120):                       # past the jump's band-limiting
            self.assertAlmostEqual(sine[i], shaped_sine(sine_phase[i], Buchla259PrincipalOscillatorCharacter()),
                                   places=12)

    def test_it_sits_in_the_harness(self):
        harness([Buchla259PrincipalOscillator("osc", frequency_hz="100", frequency_modulation_hz="0", oversampling=1)], {},
                ["osc_sine"])


class SineShaperDriveTests(unittest.TestCase):
    """The shaper's drive as a run-time character field, and its corners band-limited."""

    def test_a_run_time_drive_renders_what_the_build_drive_renders(self):
        for drive in (0.95, 0.3):
            built = oscillator_program(character=Buchla259PrincipalOscillatorCharacter(sine_shaper_drive=drive))
            moved = oscillator_program(character_inputs={"sine_shaper_drive": "drive"})
            moved.set_param("drive", drive)
            self.assertEqual(run(built, 2000), run(moved, 2000))

    def test_only_the_drive_moves_at_run_time(self):
        with self.assertRaises(BuildError):
            Buchla259PrincipalOscillator("o", frequency_hz="1", frequency_modulation_hz="0", oversampling=1,
                                         character_inputs={"symmetry": "1"})

    def measured_aliases(self, drive, frequency, oversampling):
        """The worst alias under 20 kHz re the fundamental at 48 kHz, (trivial, band-limited), at the steps' rate."""
        rate, count, settle = 48000.0 * oversampling, 16384, 200
        program = oscillator_program(samplerate=rate, character_inputs={"sine_shaper_drive": "drive"})
        program.set_param("drive", drive)
        program.set_param("frequency", frequency)
        band_limited = run(program, count + settle)[0][settle:]
        character = Buchla259PrincipalOscillatorCharacter(sine_shaper_drive=drive)
        trivial = [shaped_sine((i + settle - SINE_LATENCY_STEPS) * frequency / rate % 1.0, character) for i in range(count)]
        harmonics = [k for k in range(3, 120, 2) if k * frequency > rate / 2
                     and all(abs(folded(k * frequency, rate) - h * frequency) > 8 for h in range(1, 120, 2)
                             if h * frequency < rate / 2)]
        return [worst_alias_db(wave, frequency, harmonics, rate, 20000) for wave in (trivial, band_limited)]

    def test_the_corners_are_band_limited(self):
        # measured 2026-10-20 (trivial -> band-limited): drive 0.05 at 5 kHz, 1x: -33.2 -> -71.9 dB; drive 0.95
        # (2sl gate's) at 5 kHz, 2x: -68.5 -> -118.8 dB
        trivial, band_limited = self.measured_aliases(0.05, 5000.0, 1)
        self.assertGreater(trivial, -34.0)
        self.assertLess(band_limited, -71.0)
        trivial, band_limited = self.measured_aliases(0.95, 5000.0, 2)
        self.assertGreater(trivial, -69.0)
        self.assertLess(band_limited, -115.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

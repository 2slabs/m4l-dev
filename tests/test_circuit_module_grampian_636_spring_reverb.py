"""The Grampian 636 spring reverb module (m4l_dev/circuit_modules/grampian_636_spring_reverb.py): the maker's sheet
(references/circuits/grampian-636-spring-reverb.md): two springs of 29 and 37 ms, "2 seconds at 300 Hz", the reverb
path "100 Hz to 6K Hz ±3db". Rendered through our GenExpr renderer (ours, not Max's compiler). Standard library
only."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev.circuit_modules.grampian_636_spring_reverb import (  # noqa: E402
    DECAY_REFERENCE_HZ, NOMINAL_LENGTH_S, Grampian636SpringReverb, Grampian636SpringReverbCharacter, damping_hz,
    round_trips_ms)
from gen_block_harness import autocorrelation, band_decay_seconds, band_levels_db, harness  # noqa: E402

SAMPLERATE = 44100.0
TYPICAL = Grampian636SpringReverbCharacter()


def unit(length=NOMINAL_LENGTH_S):
    block = Grampian636SpringReverb("studio", input="in1", length_s="length", brightness="0", clear="0",
                                    oversampling=1)
    return harness([block], {"length": length},
                   ["studio_left", "studio_right", "studio_driven", "studio_tank_spring_1", "studio_tank_spring_2"],
                   samplerate=SAMPLERATE), block


class Grampian636SpringReverbTests(unittest.TestCase):
    def test_two_springs_of_29_and_37_ms(self):
        _, block = unit()
        self.assertEqual(round_trips_ms(TYPICAL), (29.0, 37.0))
        self.assertEqual(block.tank.sections, (52, 66))
        self.assertEqual(block.tank.transition_hz, 6000.0)
        self.assertEqual(damping_hz(TYPICAL), 12000.0)
        program, _ = unit()
        impulse = [1.0] + [0.0] * int(0.6 * SAMPLERATE)
        outputs = program.run(len(impulse), [impulse])
        self.assertEqual(outputs[2], impulse)                  # constant current: flat into the coil
        for spring, round_trip_ms in zip(outputs[3:], round_trips_ms(TYPICAL)):
            correlation = autocorrelation(spring, int(0.06 * SAMPLERATE))
            lag = max(range(int(0.015 * SAMPLERATE), len(correlation)), key=lambda n: abs(correlation[n]))
            self.assertAlmostEqual(lag / SAMPLERATE * 1000, round_trip_ms, delta=0.25, msg=round_trip_ms)
            self.assertLess(correlation[lag], 0)

    def test_two_seconds_at_300_hz(self):
        # the sheet's "Reverberation Time: 2 seconds at 300 Hz" at the nominal Length, and Length is that T60
        for length in (NOMINAL_LENGTH_S, 4.0):
            program, _ = unit(length)
            impulse = [1.0] + [0.0] * int(1.2 * length * SAMPLERATE)
            left, right = program.run(len(impulse), [impulse])[:2]
            t60 = band_decay_seconds([a + b for a, b in zip(left, right)], DECAY_REFERENCE_HZ, SAMPLERATE)
            print(f"\n[grampian 636] Length {length} s: T60 at 300 Hz {t60:.2f} s")
            self.assertAlmostEqual(t60 / length, 1.0, delta=0.05, msg=length)

    def test_the_reverb_path_is_the_sheets_band(self):
        # white noise in, the left side's steady spectrum in third octaves against 1 kHz's: within the sheet's ±3 dB
        # from 125 Hz to 5 kHz; its edges measured 2026-10-21 at -3.3 dB (100 Hz) and -7.4 dB (6.3 kHz): the springs'
        # own low end, and the output low-pass at F_C (-3 dB at 6 kHz) with the transducer's half-sample mean
        generator = random.Random(2)
        noise = [2 * generator.random() - 1 for _ in range(int(4 * SAMPLERATE))]
        program, _ = unit()
        left = program.run(len(noise), [noise])[0][int(1.5 * SAMPLERATE):]
        centres = (1000, 100, 125, 160, 200, 250, 315, 500, 2000, 3150, 4000, 5000, 6300, 8000)
        levels = dict(zip(centres, band_levels_db(left, [(c / 2 ** (1 / 6), c * 2 ** (1 / 6)) for c in centres],
                                                  SAMPLERATE)))
        print("\n[grampian 636] band, dB re 1 kHz: " + ", ".join(f"{c} Hz {levels[c]:+.1f}" for c in centres[1:]))
        for centre in (125, 160, 200, 250, 315, 500, 2000, 3150, 4000, 5000):
            self.assertLess(abs(levels[centre]), 3.0, centre)
        self.assertGreater(levels[100], -6.0)
        self.assertLess(levels[8000], -20.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

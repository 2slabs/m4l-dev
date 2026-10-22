"""The Accutronics type 9 spring tank module (m4l_dev/circuit_modules/accutronics_type_9_spring_tank.py): its three
springs' echo spacing, its decay at its reference frequency, its current drive's 6 dB/oct rise and the band it leaves,
against references/circuits/accutronics-type-9-spring-tank.md. Rendered through our GenExpr renderer (ours, not
Max's compiler). Standard library only."""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev.circuit_modules.accutronics_type_9_spring_tank import (  # noqa: E402
    DECAY_REFERENCE_HZ, NOMINAL_LENGTH_S, AccutronicsType9SpringTank, AccutronicsType9SpringTankCharacter,
    damping_hz, round_trips_ms)
from m4l_dev.techniques.zero_delay_one_pole_filter import small_signal_response  # noqa: E402
from gen_block_harness import autocorrelation, band_decay_seconds, band_levels_db, harness  # noqa: E402

SAMPLERATE = 44100.0
TYPICAL = AccutronicsType9SpringTankCharacter()


def tank(length=NOMINAL_LENGTH_S, brightness=0.0):
    block = AccutronicsType9SpringTank("long", input="in1", length_s="length", brightness="bright", clear="0",
                                       oversampling=1)
    return harness([block], {"length": length, "bright": brightness},
                   ["long_left", "long_right", "long_driven", "long_tank_spring_1", "long_tank_spring_2",
                    "long_tank_spring_3"], samplerate=SAMPLERATE), block


class AccutronicsType9SpringTankTests(unittest.TestCase):
    def test_three_springs_of_33_37_41_ms_their_chirps_scaled_to_each(self):
        _, block = tank()
        self.assertEqual(round_trips_ms(TYPICAL), (33.0, 37.0, 41.0))
        self.assertEqual(block.tank.sections, (59, 66, 73))
        self.assertEqual(block.tank.transition_hz, 4500.0)
        self.assertEqual(block.tank.loop_sign, -1)
        self.assertEqual(damping_hz(TYPICAL), 9000.0)
        # each spring's echoes: the lag of its autocorrelation's largest magnitude (Gamper et al. 2011's T_D), negative
        program, _ = tank(length=2.0)
        impulse = [1.0] + [0.0] * int(0.6 * SAMPLERATE)
        outputs = program.run(len(impulse), [impulse])
        for spring, round_trip_ms in zip(outputs[3:], round_trips_ms(TYPICAL)):
            correlation = autocorrelation(spring, int(0.07 * SAMPLERATE))
            lag = max(range(int(0.02 * SAMPLERATE), len(correlation)), key=lambda n: abs(correlation[n]))
            self.assertAlmostEqual(lag / SAMPLERATE * 1000, round_trip_ms, delta=0.25, msg=round_trip_ms)
            self.assertLess(correlation[lag], 0)

    def test_length_is_the_t60_at_1_khz(self):
        # the type's long decay class is 2.75-4.0 s (AP): nominal 3.4 s, and any Length, within 5 %
        for length in (NOMINAL_LENGTH_S, 1.5):
            program, _ = tank(length=length)
            impulse = [1.0] + [0.0] * int(1.2 * length * SAMPLERATE)
            left, right = program.run(len(impulse), [impulse])[:2]
            t60 = band_decay_seconds([a + b for a, b in zip(left, right)], DECAY_REFERENCE_HZ, SAMPLERATE)
            print(f"\n[accutronics type 9] Length {length} s: T60 at 1 kHz {t60:.2f} s")
            self.assertAlmostEqual(t60 / length, 1.0, delta=0.05, msg=length)

    def test_the_current_drive_rises_6_db_an_octave_into_the_coil(self):
        program, _ = tank()
        for frequency in (50.0, 100.0, 200.0, 1000.0):
            samples = int(0.5 * SAMPLERATE)
            tone = [math.sin(2 * math.pi * frequency * n / SAMPLERATE) for n in range(samples)]
            driven = program.run(samples, [tone])[2]
            level = max(abs(value) for value in driven[samples // 2:])
            expected = abs(small_signal_response(frequency, TYPICAL.drive_corner_hz, SAMPLERATE)["highpass"])
            self.assertAlmostEqual(20 * math.log10(level), 20 * math.log10(expected), delta=0.02, msg=frequency)
        # under the corner, +6 dB an octave: 50 -> 100 Hz
        rise = 20 * math.log10(abs(small_signal_response(100.0, 200.0, SAMPLERATE)["highpass"])
                               / abs(small_signal_response(50.0, 200.0, SAMPLERATE)["highpass"]))
        self.assertAlmostEqual(rise, 5.3, delta=0.1)

    def test_the_band_it_leaves(self):
        # white noise in, the left side's steady spectrum in third octaves against 1 kHz's: ESP's usable band of about
        # 200 Hz to 6 kHz, "very limited above ~5kHz" (measured, the edges reported)
        generator = random.Random(2)
        noise = [2 * generator.random() - 1 for _ in range(int(4 * SAMPLERATE))]
        program, _ = tank()
        left = program.run(len(noise), [noise])[0][int(1.5 * SAMPLERATE):]
        centres = (1000, 125, 200, 315, 2000, 3150, 4000, 4500, 5000, 6300, 8000)
        levels = dict(zip(centres, band_levels_db(left, [(c / 2 ** (1 / 6), c * 2 ** (1 / 6)) for c in centres],
                                                  SAMPLERATE)))
        print("\n[accutronics type 9] band, dB re 1 kHz: " + ", ".join(f"{c} Hz {levels[c]:+.1f}" for c in centres[1:]))
        for centre in (315, 2000, 3150, 4000):
            self.assertGreater(levels[centre], -6.0, centre)
        self.assertLess(levels[125], levels[315] - 3)
        self.assertLess(levels[6300], -20.0)
        self.assertLess(levels[8000], -40.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""The spring tank modules' one interface (twosl_dsp/circuit_modules/buchla_208_spring_reverb.py,
accutronics_type_9_spring_tank.py, grampian_636_spring_reverb.py; architecture/dsp-blocks.md, "Spring tanks"): one set
of controls drives any of them, and each says its wet's level so a device can switch tanks without a jump. Rendered
through our GenExpr renderer (ours, not Max's compiler). Standard library only."""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.circuit_modules.accutronics_type_9_spring_tank import AccutronicsType9SpringTank  # noqa: E402
from twosl_dsp.circuit_modules.buchla_208_spring_reverb import Buchla208SpringReverb  # noqa: E402
from twosl_dsp.circuit_modules.grampian_636_spring_reverb import Grampian636SpringReverb  # noqa: E402
from gen_block_harness import harness  # noqa: E402

SAMPLERATE = 44100.0
TANKS = (Buchla208SpringReverb, AccutronicsType9SpringTank, Grampian636SpringReverb)
OUTPUTS = ("left", "right", "level", "driven")


def tank_program(tank_class, kick=False, length=None):
    block = tank_class("tank", input="in1" if not kick else "0", length_s="length", brightness="bright",
                       clear="clear > 0", oversampling=1, kick="in1" if kick else None)
    params = {"length": tank_class.nominal_length_s if length is None else length, "bright": 0.0, "clear": 0.0}
    return harness([block], params, [f"tank_{name}" for name in OUTPUTS], samplerate=SAMPLERATE), block


class SpringTankInterfaceTests(unittest.TestCase):
    def test_every_tank_takes_the_same_controls_and_gives_the_same_outputs(self):
        for tank_class in TANKS:
            with self.subTest(tank=tank_class.__name__):
                program, block = tank_program(tank_class)
                self.assertEqual(block.latency_samples, 0)            # the wet only, no direct path
                self.assertGreater(tank_class.nominal_length_s, 0)
                for bad in (2, 4):
                    with self.assertRaises(BuildError):
                        tank_class("tank", input="in1", length_s="2", brightness="0", clear="0", oversampling=bad)
                with self.assertRaises(TypeError):
                    tank_class("tank", input="in1", length_s="2", brightness="0", clear="0")
                # nothing in, nothing out: an idle tank is exactly silent
                outputs = program.run(4410, [[0.0] * 4410])
                self.assertEqual(max(abs(value) for output in outputs for value in output), 0.0)

    def test_each_tanks_wet_level_is_what_it_says(self):
        # white noise, 0.5 s, then 2.5 s of tail, at each tank's nominal Length: the wet's RMS (both sides) against the
        # input's, within 0.2 dB of the module's wet_level_db
        generator = random.Random(4)
        burst = [2 * generator.random() - 1 for _ in range(int(0.5 * SAMPLERATE))] + [0.0] * int(2.5 * SAMPLERATE)
        input_rms = math.sqrt(sum(value * value for value in burst) / len(burst))
        for tank_class in TANKS:
            program, _ = tank_program(tank_class)
            left, right = program.run(len(burst), [burst])[:2]
            rms = math.sqrt(sum(a * a + b * b for a, b in zip(left, right)) / (2 * len(left)))
            level_db = 20 * math.log10(rms / input_rms)
            print(f"\n[spring tanks] {tank_class.__name__}: wet {level_db:+.2f} dB re its input")
            self.assertAlmostEqual(level_db, tank_class.wet_level_db, delta=0.2, msg=tank_class.__name__)

    def test_a_kick_rings_every_spring_and_is_held(self):
        # a +12 dB burst into `kick` alone (the input silent): both sides ring, nothing goes through the drive, and the
        # tank's own non-linearity holds it
        burst = [4.0 * math.exp(-n / 40.0) * (1 if n % 2 else -1) for n in range(400)] + [0.0] * int(SAMPLERATE)
        for tank_class in TANKS:
            with self.subTest(tank=tank_class.__name__):
                program, _ = tank_program(tank_class, kick=True)
                left, right, level, driven = program.run(len(burst), [burst])
                self.assertEqual(max(abs(value) for value in driven), 0.0)
                self.assertTrue(all(math.isfinite(value) for value in left + right))
                self.assertGreater(min(max(abs(value) for value in left), max(abs(value) for value in right)), 0.02)
                self.assertLess(max(abs(value) for value in left + right), 2.0)

    def test_clear_stops_the_tail(self):
        # Stop in the middle of a long tail: after the tank's clear window it is silent (the dispersive tanks exactly,
        # gate's under -120 dB of its tail: its low-passes and all-passes ring out of what they held, into lines
        # that stay muted for the window, as gate's own)
        generator = random.Random(8)
        noise = [0.5 * (2 * generator.random() - 1) for _ in range(int(0.4 * SAMPLERATE))]
        for tank_class in TANKS:
            with self.subTest(tank=tank_class.__name__):
                program, _ = tank_program(tank_class, length=6.0)
                tail = program.run(len(noise), [noise])[0]
                program.set_param("clear", 1.0)
                program.run(1, [[0.0]])
                program.set_param("clear", 0.0)
                program.run(int(0.065 * SAMPLERATE), [[0.0] * int(0.065 * SAMPLERATE)])
                after = program.run(int(0.2 * SAMPLERATE), [[0.0] * int(0.2 * SAMPLERATE)])[:2]
                loudest = max(abs(value) for side in after for value in side)
                self.assertLess(loudest, 1e-6 * max(abs(value) for value in tail), tank_class.__name__)

    def test_length_and_brightness_move_every_tank(self):
        # the same two controls do the same thing on each: a longer Length rings longer, a darker Bright has less top
        impulse = [1.0] + [0.0] * int(1.5 * SAMPLERATE)
        for tank_class in TANKS:
            with self.subTest(tank=tank_class.__name__):
                energies = {}
                for length in (0.5, 3.0):
                    program, _ = tank_program(tank_class, length=length)
                    left = program.run(len(impulse), [impulse])[0]
                    late = left[int(1.0 * SAMPLERATE):]
                    energies[length] = sum(value * value for value in late)
                self.assertGreater(energies[3.0], 1e3 * energies[0.5])
                tops = {}
                for bright in (-1.0, 1.0):
                    program, _ = tank_program(tank_class, length=2.0)
                    program.set_param("bright", bright)
                    left = program.run(len(impulse), [impulse])[0][int(0.3 * SAMPLERATE):int(0.8 * SAMPLERATE)]
                    differences = [b - a for a, b in zip(left, left[1:])]
                    tops[bright] = sum(value * value for value in differences) / sum(value * value for value in left)
                self.assertGreater(tops[1.0], 1.5 * tops[-1.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)

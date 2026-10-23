"""The Altec 9069B module (twosl_dsp/circuit_modules/altec_9069b_high_pass.py): its claims, rendered through our GenExpr
renderer on a harness around one unit (tests/gen_block_harness.py). Volts in, volts out. Standard library only."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.circuit_modules.altec_9069b_high_pass import (STEP_CORNERS_HZ, Altec9069BHighPass,  # noqa: E402
                                                           Altec9069BHighPassCharacter, magnitude_db,
                                                           small_signal_response)
from gen_block_harness import amplitude_at, harness  # noqa: E402

SAMPLERATE = 44100.0
DESIGN = Altec9069BHighPassCharacter()
REPLICA_STEPS_HZ = (70, 100, 150, 250, 500, 1000, 2000, 3000, 5000, 7500)    # the reference's §2


def unit(character=DESIGN, samplerate=SAMPLERATE):
    block = Altec9069BHighPass("knob", input_volts="in1", step="step", character=character)
    return harness([block], {"step": 1.0}, ["knob_out", "knob_corner_hz"], samplerate=samplerate)


def rendered_gain_db(step, frequency, character=DESIGN, samplerate=SAMPLERATE):
    """The rendered unit's gain at `frequency` on `step`: a sine's amplitude out over in, after it has settled."""
    length = 8192
    program = unit(character, samplerate)
    program.set_param("step", float(step))
    settle = int(samplerate * max(0.2, 20 / frequency))
    sine = [math.sin(2 * math.pi * frequency * i / samplerate) for i in range(settle + length)]
    out = program.run(len(sine), [sine])[0][settle:]
    return 20 * math.log10(amplitude_at(out, frequency, samplerate) / amplitude_at(sine[settle:], frequency, samplerate))


def warped_hz(frequency, corner, samplerate):
    """The analogue frequency the prewarped trapezoidal network gives at digital `frequency` (exact at `corner`)."""
    w_corner = 2 * math.pi * corner
    return w_corner / math.tan(w_corner / (2 * samplerate)) * math.tan(math.pi * frequency / samplerate) / (2 * math.pi)


class Altec9069BHighPassTests(unittest.TestCase):
    def test_the_parts_land_on_the_replicas_steps(self):
        for corner, replica in zip(STEP_CORNERS_HZ, REPLICA_STEPS_HZ):
            self.assertLess(abs(corner / replica - 1), 0.02, (corner, replica))

    def test_each_step_is_a_third_order_butterworth_with_the_terminations_loss(self):
        # the analogue network from 600 into 600: -6 dB in the pass band, -3 dB more at the corner, 18 dB / oct
        for step, corner in enumerate(STEP_CORNERS_HZ, start=1):
            passband = magnitude_db(small_signal_response(DESIGN, step, corner * 100))
            self.assertAlmostEqual(passband, -6.0206, delta=0.01, msg=step)
            # the parts are measured, not ideal (their design resistance 578-632 ohms, not 600, their corners within
            # 2 % of the replica's): each step within 0.5 dB of the ideal Butterworth's figures
            for ratio, below in ((1.0, 3.0103), (0.5, 18.13), (0.25, 36.12)):
                self.assertAlmostEqual(magnitude_db(small_signal_response(DESIGN, step, corner * ratio)) - passband,
                                       -below, delta=0.5, msg=(step, ratio))
            peak = max(magnitude_db(small_signal_response(DESIGN, step, corner * (1 + k / 50))) for k in range(200))
            self.assertLess(peak, passband + 0.01, step)

    def test_a_low_source_into_a_high_load_peaks(self):
        # the reference's §3: from 50 ohms into 10k the 1 kHz step peaks +15.9 dB at 1.42 x its corner
        mismatched = Altec9069BHighPassCharacter(source_ohms=50.0, load_ohms=10e3)
        corner = STEP_CORNERS_HZ[5]
        passband = magnitude_db(small_signal_response(mismatched, 6, corner * 100))
        ratios = [1 + k / 1000 for k in range(1500)]
        gains = [magnitude_db(small_signal_response(mismatched, 6, corner * r)) - passband for r in ratios]
        best = max(range(len(gains)), key=gains.__getitem__)
        self.assertAlmostEqual(gains[best], 15.9, delta=0.1)
        self.assertAlmostEqual(ratios[best], 1.42, delta=0.01)
        self.assertAlmostEqual(rendered_gain_db(6, corner * 1.42, mismatched) - magnitude_db(
            small_signal_response(mismatched, 6, warped_hz(corner * 1.42, STEP_CORNERS_HZ[5], SAMPLERATE))), 0, delta=0.02)

    def test_the_rendered_network_is_the_analogue_one_prewarped_at_the_corner(self):
        # the trapezoidal network is the bilinear transform of the circuit: the rendered gain at f is the analogue
        # gain at the warped f, exactly at the corner, on every step
        for step in (1, 4, 7, 10):
            corner = STEP_CORNERS_HZ[step - 1]
            for ratio in (0.5, 1.0, 2.0):
                frequency = corner * ratio
                if frequency > SAMPLERATE * 0.45:
                    continue
                expected = magnitude_db(small_signal_response(DESIGN, step, warped_hz(frequency, corner, SAMPLERATE)))
                self.assertAlmostEqual(rendered_gain_db(step, frequency), expected, delta=0.02, msg=(step, ratio))

    def test_flat_is_the_terminations_alone(self):
        program = unit()
        program.set_param("step", 0.0)
        ramp = [i / 100 - 0.5 for i in range(100)]
        out, corner = program.run(len(ramp), [ramp])
        self.assertEqual(out, [v * 0.5 for v in ramp])
        self.assertEqual(set(corner), {0.0})

    def test_a_step_change_keeps_the_network_bounded(self):
        # sweeping the knob through every step while a bass plays: the transients are the network's, and settle
        program = unit()
        bass = [0.8 * math.sin(2 * math.pi * 55 * i / SAMPLERATE) for i in range(int(SAMPLERATE * 0.05))]
        outs = []
        for step in list(range(11)) + list(range(10, -1, -1)):
            program.set_param("step", float(step))
            outs += program.run(len(bass), [bass])[0]
        self.assertTrue(all(math.isfinite(v) for v in outs))
        self.assertLess(max(abs(v) for v in outs), 2.0)

    def test_terminations_must_be_real(self):
        with self.assertRaises(BuildError):
            Altec9069BHighPass("knob", input_volts="0", step="0",
                               character=Altec9069BHighPassCharacter(source_ohms=0.0))


if __name__ == "__main__":
    unittest.main()

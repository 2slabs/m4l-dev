"""The Buchla 292 low pass gate channel module (m4l_dev/circuit_modules/buchla_292_low_pass_gate_channel.py): the
photocell fit and the network against DAFx-13 (references/circuits/buchla-292-low-pass-gate.md §2-§3), and the
rendered vactrol and network against the module's own Python twins and the release law, through our GenExpr renderer
(ours, not Max's compiler). Standard library only."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.circuit_modules.buchla_292_low_pass_gate_channel import (  # noqa: E402
    DECAY_END_RESISTANCE, MODE_NAMES, VCA_MODE_INPUT_GAIN, Buchla292LowPassGateChannel, Buchla292LowPassGateChannelCharacter,
    led_current_at_resistance, network_coefficients, network_response, photocell_resistance, release_span)
from gen_block_harness import amplitude_at, harness  # noqa: E402

SAMPLERATE = 44100.0
TYPICAL = Buchla292LowPassGateChannelCharacter()
VCA, BOTH, LOWPASS = (MODE_NAMES.index(name) for name in ("vca", "both", "lowpass"))


def channel(**params):
    """A harness around one channel: Params led (amps), attack, decay (ms), mode, resonance; outputs out, Rf, the
    DC gain and the corner."""
    params = dict({"led": TYPICAL.led_current_floor_amps, "attack": 2.0, "decay": 185.0, "mode": BOTH,
                   "resonance": 0.0}, **params)
    block = Buchla292LowPassGateChannel("lpg", input="in1", led_current_amps="led", attack_ms="attack",
                                        decay_ms="decay", mode="mode", resonance="resonance")
    return harness([block], params, ["lpg_out", "lpg_resistance_ohms", "lpg_dc_gain", "lpg_corner_hz"],
                   samplerate=SAMPLERATE)


class PhotocellAndNetworkTests(unittest.TestCase):
    def test_the_photocell_fit_is_the_vtl5c3_2(self):
        # DAFx-13 eq. 39: 56 kOhm at 1 mA (the VTL5C3/2's 55k), 1.45 kOhm at its rated 40 mA, dark above 30 MOhm
        self.assertAlmostEqual(photocell_resistance(1e-3, TYPICAL) / 1000, 56, delta=0.5)
        self.assertAlmostEqual(photocell_resistance(TYPICAL.led_current_ceiling_amps, TYPICAL) / 1000, 1.45, delta=0.01)
        self.assertGreater(photocell_resistance(0.0, TYPICAL), 30e6)
        self.assertAlmostEqual(led_current_at_resistance(photocell_resistance(2e-4, TYPICAL), TYPICAL), 2e-4, delta=1e-12)
        with self.assertRaises(BuildError):
            led_current_at_resistance(1000.0, TYPICAL)                      # under the fit's floor

    def test_the_both_network_has_two_poles_15_to_20_times_apart(self):
        # the second pole is not "above 150 kHz": r + 2 + 1/r = alpha2^2 / (alpha1 alpha3), which is
        # (2 C1 + C2)^2 / (C1 C2) = 22.4 while Rf << R alpha, so it sits r = 20.3 times above the first, falling to 14.5
        # at 1 MOhm as the divider acts
        for rf, ratio in ((10e3, 20.3), (100e3, 19.6), (1e6, 14.5)):
            alpha1, alpha2, alpha3 = network_coefficients(rf, BOTH, 0.0, TYPICAL)
            root = math.sqrt(alpha2 * alpha2 - 4 * alpha1 * alpha3)
            self.assertAlmostEqual((alpha2 + root) / (alpha2 - root), ratio, delta=0.15, msg=rf)
        gain, corner = network_response(100e3, BOTH, 0.0, TYPICAL)
        # the -3 dB corner: 780 Hz, 9 % above the one-pole estimate 1 / (2 pi Rf 2.22 nF) = 717 Hz
        self.assertAlmostEqual(corner, 780.1, delta=0.1)
        self.assertGreater(gain, 0.95)
        vca_gain, _ = network_response(100e3, VCA, 0.0, TYPICAL)
        self.assertAlmostEqual(20 * math.log10(vca_gain), -32, delta=1)       # the research's VCA mode at 100k

    def test_full_resonance_must_stay_damped(self):
        with self.assertRaises(BuildError):
            Buchla292LowPassGateChannel("lpg", input="in1", led_current_amps="0", attack_ms="2", decay_ms="185",
                                        mode="2", resonance="1",
                                        character=Buchla292LowPassGateChannelCharacter(highest_resonance_share_of_stable=1.2))


class RenderedChannelTests(unittest.TestCase):
    def test_a_held_drive_settles_on_the_fit(self):
        program = channel(led=1e-3, attack=1.0)
        resistance = program.run(4410, [[0.0] * 4410])[1]
        self.assertAlmostEqual(resistance[-1], photocell_resistance(1e-3, TYPICAL), delta=1.0)

    def test_the_release_is_the_power_law(self):
        # from the ceiling, the drive at the floor: 1/I = 1/I0 + c t (to the floor's small pull), so Rf passes
        # DECAY_END_RESISTANCE (1 MOhm) after `decay_ms`
        program = channel(led=TYPICAL.led_current_ceiling_amps, attack=0.001)
        program.run(441, [[0.0] * 441])
        program.set_param("led", TYPICAL.led_current_floor_amps)
        decay_ms = 60.0
        program.set_param("decay", decay_ms)
        count = int(SAMPLERATE * decay_ms / 1000) + 1
        resistance = program.run(count, [[0.0] * count])[1]
        self.assertAlmostEqual(resistance[-1] / DECAY_END_RESISTANCE, 1.0, delta=0.01)
        rate = release_span(TYPICAL) / (decay_ms / 1000)
        for i in (10, 100, 1000, 2000):
            current = 1 / (1 / TYPICAL.led_current_ceiling_amps + rate * (i + 1) / SAMPLERATE)
            self.assertAlmostEqual(resistance[i] / photocell_resistance(current, TYPICAL), 1.0, delta=0.01, msg=i)

    def test_every_mode_is_3_db_down_at_its_corner(self):
        # held at 100 kOhm: a sine at the readout's corner comes out 3 dB under the readout's DC gain (prewarped
        # there; the VCA mode's input gain on top)
        current = led_current_at_resistance(100e3, TYPICAL)
        for mode, resonance in ((VCA, 0.0), (BOTH, 0.0), (LOWPASS, 0.0), (LOWPASS, 1.0)):
            program = channel(led=current, attack=0.01, mode=mode, resonance=resonance)
            readout = program.run(200, [[0.0] * 200])
            dc_gain, corner = readout[2][-1], readout[3][-1]
            self.assertAlmostEqual(corner, network_response(100e3, mode, resonance, TYPICAL)[1],
                                   delta=0.01)
            count = 8820
            sine = [math.sin(2 * math.pi * corner * i / SAMPLERATE) for i in range(count)]
            out = program.run(count, [sine])[0][count // 2:]
            level = amplitude_at(out, corner, SAMPLERATE) / dc_gain / (VCA_MODE_INPUT_GAIN if mode == VCA else 1)
            self.assertAlmostEqual(20 * math.log10(level), -3.01, delta=0.05, msg=(MODE_NAMES[mode], resonance))

    def test_a_reset_darkens_the_cell(self):
        block = Buchla292LowPassGateChannel("lpg", input="in1", led_current_amps="led", attack_ms="1", decay_ms="185",
                                            mode="1", resonance="0")
        self.assertIn(f"lpg_cell_current = {TYPICAL.led_current_floor_amps!r};", block.reset_statements())
        self.assertIn("lpg_network_s1 = 0;", block.reset_statements())


if __name__ == "__main__":
    unittest.main(verbosity=2)

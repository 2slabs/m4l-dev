"""The Buchla 208 spring reverb module (twosl_dsp/circuit_modules/buchla_208_spring_reverb.py): built with 2sl gate's
numbers it renders the same sound as gate's own spring code, copied below verbatim as the reference program; the
driver's resonance against the schematic's parts; the tank interface. Rendered through our GenExpr renderer (ours,
not Max's compiler). Standard library only."""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.circuit_modules.buchla_208_spring_reverb import (  # noqa: E402
    Buchla208SpringReverb, Buchla208SpringReverbCharacter, dc_block_hz, driver_q, driver_resonance_hz,
    driver_response)
from twosl_dsp.gen_blocks import gen_code_with_blocks  # noqa: E402
from twosl_dsp.generated_numbers import generated_number  # noqa: E402
from twosl_dsp.genexpr import GenProgram, check  # noqa: E402
from twosl_dsp.render_comparison import assert_renders_similar  # noqa: E402
from twosl_dsp.techniques.zero_delay_state_variable_filter import ZeroDelayStateVariableFilter  # noqa: E402
from gen_block_harness import harness  # noqa: E402

SAMPLERATE = 44100.0
TYPICAL = Buchla208SpringReverbCharacter()

# ---- 2sl gate's spring, verbatim: src/gate_dsp.py at 2sl gate commit 68bfd110bd0b485ac604eca9825d0b9a416526c7 ----
# (main, 2026-10-21): its constants (lines 268-270, 312-338), _spring_code() (lines 1645-1665) and the CORE lines that
# run it (1608-1618). Only the harness around it is ours: voice_out is the input, effects are on, Spring mix is 1, and
# Stop's mute is gate's spring_mute counter (lines 1503-1508) started by a `stop` input instead of the end of gate's
# 20 ms fade.
HIGHEST_SAMPLE_RATE = 192000
SPRING_LOOP_MS = (33.7, 41.3)                           # the two springs' round trips (left, right)
SPRING_BUFFER_SAMPLES = int(HIGHEST_SAMPLE_RATE * 0.05)
SPRING_DRIVER_COUPLING_FARADS = 390e-6
SPRING_DRIVER_COIL_HENRIES = 1.27e-3
SPRING_DRIVER_COIL_OHMS = 0.81
SPRING_DRIVER_RESONANCE_HZ = generated_number(
    1 / (2 * math.pi * math.sqrt(SPRING_DRIVER_COIL_HENRIES * SPRING_DRIVER_COUPLING_FARADS)))
SPRING_DRIVER_Q = generated_number(
    math.sqrt(SPRING_DRIVER_COIL_HENRIES / SPRING_DRIVER_COUPLING_FARADS) / SPRING_DRIVER_COIL_OHMS)
SPRING_FIRST_TOOTH_LOSS_DB = 0.1
SPRING_LOOP_DC_BLOCK_HZ = generated_number(
    (1000.0 / max(SPRING_LOOP_MS)) * math.sqrt(10 ** (SPRING_FIRST_TOOTH_LOSS_DB / 10) - 1))
SPRING_ALLPASSES = 8                                    # first-order allpasses per spring: the dispersion (chirp)
SPRING_ALLPASS_COEFFICIENT = 0.62
STOP_FADE_MS, SPRING_CLEAR_MS = 20.0, 60.0


def _spring_code():
    lines = []
    for side, loop_ms in (("l", SPRING_LOOP_MS[0]), ("r", SPRING_LOOP_MS[1])):
        lines.append(f"sp_read_{side} = spring_{side}.read(mstosamps({loop_ms!r}), interp=\"linear\") * spring_clean;")
        lines.append(f"sp_lp_{side} = sp_lp_{side} + sp_lp_k * (sp_read_{side} - sp_lp_{side});")
        lines.append(f"spring_dc_{side} = (spring_dc_{side} + spring_dc_block_k * (sp_lp_{side} - spring_dc_{side})) * spring_clean;")
        lines.append(f"spring_returned_{side} = sp_lp_{side} - spring_dc_{side};")
        lines.append(f"sp_fb_{side} = pow(10, -3 * {generated_number(loop_ms / 1000)!r} / spring_length);")
        lines.append(f"sp_x0_{side} = spring_driven + spring_returned_{side} * sp_fb_{side};")
        a = SPRING_ALLPASS_COEFFICIENT
        for n in range(1, SPRING_ALLPASSES + 1):
            prev = f"sp_x{n - 1}_{side}"
            lines.append(f"sp_x{n}_{side} = {a!r} * {prev} + sp_in{n}_{side} - {a!r} * sp_out{n}_{side};")
            lines.append(f"sp_in{n}_{side} = {prev};")
            lines.append(f"sp_out{n}_{side} = sp_x{n}_{side};")
        lines.append(f"spring_{side}.write(tanh(sp_x{SPRING_ALLPASSES}_{side}) * spring_clean);")
        lines.append(f"spring_out_{side} = voice_out + (spring_returned_{side} * spring_mix * 0.8) * effects_fade;")
    histories = ", ".join(f"sp_in{n}_{side}(0), sp_out{n}_{side}(0)"
                          for side in "lr" for n in range(1, SPRING_ALLPASSES + 1))
    return "\n".join(lines), histories


SPRING_CODE, SPRING_HISTORIES = _spring_code()
SPRING_DRIVER = ZeroDelayStateVariableFilter("spring_driver", input="voice_out", cutoff_hz=repr(SPRING_DRIVER_RESONANCE_HZ),
                                             q=repr(SPRING_DRIVER_Q))
GATE_SPRING_PROGRAM = """/*GEN_BLOCK_FUNCTIONS*/
Param spring_length(2, min=0.3, max=6);  // s
Param spring_brightness(0, min=-1, max=1);
Param stop(0);
Delay spring_l(SPRING_BUFFER_SAMPLES);
Delay spring_r(SPRING_BUFFER_SAMPLES);
History SPRING_HISTORIES;
History spring_dc_l(0), spring_dc_r(0);
History sp_lp_l(0), sp_lp_r(0), spring_mute(0), last_stop(0);
/*GEN_BLOCK_DECLARATIONS*/
sr = samplerate;
voice_out = in1;
effects_fade = 1;
spring_mix = 1;
if (stop != last_stop) {
	last_stop = stop;
	/*SPRING_DRIVER_RESET*/
	spring_mute = mstosamps(SPRING_CLEAR_MS);
}
if (spring_mute > 0) {
	spring_mute = spring_mute - 1;
}
spring_clean = spring_mute > 0 ? 0 : 1;
sp_lp_k = 1 - exp(-6.283185307 * 2500 * pow(4, spring_brightness) / sr);
/*SPRING_DRIVER*/
spring_driven = voice_out - spring_driver_lowpass;
spring_dc_block_k = 1 - exp(-6.283185307 * SPRING_LOOP_DC_BLOCK_HZ / sr);
SPRING_CODE
out1 = spring_returned_l;
out2 = spring_returned_r;
"""
for marker, text in (("SPRING_BUFFER_SAMPLES", str(SPRING_BUFFER_SAMPLES)), ("SPRING_HISTORIES", SPRING_HISTORIES),
                     ("SPRING_LOOP_DC_BLOCK_HZ", repr(SPRING_LOOP_DC_BLOCK_HZ)), ("SPRING_CODE", SPRING_CODE),
                     ("SPRING_CLEAR_MS", repr(SPRING_CLEAR_MS))):
    GATE_SPRING_PROGRAM = GATE_SPRING_PROGRAM.replace(marker, text)
GATE_SPRING_PROGRAM = gen_code_with_blocks(GATE_SPRING_PROGRAM, [SPRING_DRIVER], "gate's spring (reference)", {
    "SPRING_DRIVER_RESET": SPRING_DRIVER.reset_statements()})
# ---- end of gate's spring ----


def gate_spring(samplerate=SAMPLERATE):
    check(GATE_SPRING_PROGRAM, num_inputs=1, num_outputs=2)
    return GenProgram(GATE_SPRING_PROGRAM, 1, 2, samplerate=samplerate)


def module(samplerate=SAMPLERATE, input="in1", kick=None, character=None):
    block = Buchla208SpringReverb("easel", input=input, length_s="spring_length", brightness="spring_brightness",
                                  clear="stop != last_stop", oversampling=1, kick=kick, character=character)
    # the clear is true on the sample `stop` changes, as the reference's; the harness keeps the last value
    program_template = ("/*GEN_BLOCK_FUNCTIONS*/\nParam spring_length(2, min=0.3, max=6);\n"
                        "Param spring_brightness(0, min=-1, max=1);\nParam stop(0);\n"
                        "History last_stop(0);\n/*GEN_BLOCK_DECLARATIONS*/\n/*EASEL*/\nlast_stop = stop;\n"
                        "out1 = easel_left;\nout2 = easel_right;\nout3 = easel_level;\nout4 = easel_driven;\n")
    code = gen_code_with_blocks(program_template, [block], "test")
    check(code, num_inputs=1, num_outputs=4)
    return GenProgram(code, 1, 4, samplerate=samplerate), block


def phrase(seconds, samplerate, seed=7):
    """Bursts of noise and a 220 Hz tone with silences between: a hit every 0.4 s, each 60 ms long."""
    generator = random.Random(seed)
    signal = []
    for n in range(int(seconds * samplerate)):
        t = n / samplerate
        place = t % 0.4
        envelope = math.exp(-place / 0.02) if place < 0.06 else 0.0
        signal.append(envelope * (0.6 * (2 * generator.random() - 1) + 0.5 * math.sin(2 * math.pi * 220 * t)))
    return signal


class GateSpringTests(unittest.TestCase):
    def render_both(self, settings, samplerate=SAMPLERATE, seconds=2.5):
        """Renders the reference and the module through the same sequence of (seconds, {param: value}) changes."""
        reference = gate_spring(samplerate)
        candidate, _ = module(samplerate)
        signal = phrase(seconds, samplerate)
        outputs = {"reference": [[], []], "candidate": [[], []]}
        position = 0
        for until_seconds, params in settings:
            until = int(until_seconds * samplerate)
            for name, value in params.items():
                reference.set_param(name, value)
                candidate.set_param(name, value)
            chunk = signal[position:until]
            for side, rendered in (("reference", reference.run(len(chunk), [chunk])),
                                   ("candidate", candidate.run(len(chunk), [chunk])[:2])):
                outputs[side][0] += rendered[0]
                outputs[side][1] += rendered[1]
            position = until
        return outputs

    def test_with_gates_numbers_it_renders_gates_spring(self):
        # Init, a longer and brighter tank, a Stop in the middle of a tail, a darker short one: every control moves
        settings = [(0.6, {}), (1.1, {"spring_length": 5.0, "spring_brightness": 0.7}), (1.3, {"stop": 1}),
                    (2.5, {"spring_length": 0.4, "spring_brightness": -0.8})]
        for samplerate in (44100.0, 48000.0):
            with self.subTest(samplerate=samplerate):
                outputs = self.render_both(settings, samplerate)
                assert_renders_similar(outputs["reference"], outputs["candidate"], samplerate,
                                       what=f"the module vs gate's spring at {samplerate:.0f} Hz")

    def test_the_driver_is_card_12s_series_rlc(self):
        # references/circuits/buchla-208-spring-reverb.md §2: f0 226 Hz, Q 2.23, +7.8 dB at 226 Hz, -27.8 dB at 20 Hz,
        # within 0.05 dB of flat at 3 kHz
        self.assertAlmostEqual(driver_resonance_hz(TYPICAL), 226.0, delta=0.5)
        self.assertAlmostEqual(driver_q(TYPICAL), 2.23, delta=0.005)
        self.assertAlmostEqual(20 * math.log10(abs(driver_response(driver_resonance_hz(TYPICAL), TYPICAL))), 7.8,
                               delta=0.05)
        self.assertAlmostEqual(20 * math.log10(abs(driver_response(20.0, TYPICAL))), -27.8, delta=0.05)
        self.assertLess(abs(20 * math.log10(abs(driver_response(3000.0, TYPICAL)))), 0.06)
        self.assertEqual(dc_block_hz(TYPICAL), SPRING_LOOP_DC_BLOCK_HZ)

    def test_the_driven_signal_is_the_coils_current(self):
        program, _ = module()
        for frequency, expected in ((100.0, -9.5), (226.0, 7.8), (3000.0, 0.0)):
            samples = int(SAMPLERATE)
            tone = [math.sin(2 * math.pi * frequency * n / SAMPLERATE) for n in range(samples)]
            program.set_param("stop", 0)
            driven = program.run(samples, [tone])[3]
            # the steady state's peak over the last half second
            level = 20 * math.log10(max(abs(value) for value in driven[samples // 2:]))
            self.assertAlmostEqual(level, 20 * math.log10(abs(driver_response(frequency, TYPICAL))), delta=0.1,
                                   msg=frequency)
            self.assertAlmostEqual(level, expected, delta=0.15, msg=frequency)

    def test_it_is_wet_only_with_no_latency_and_runs_only_at_the_host_rate(self):
        _, block = module()
        self.assertEqual(block.latency_samples, 0)
        self.assertEqual(block.nominal_length_s, 2.0)
        with self.assertRaises(BuildError):
            Buchla208SpringReverb("easel", input="in1", length_s="2", brightness="0", clear="0", oversampling=2)
        with self.assertRaises(TypeError):
            Buchla208SpringReverb("easel", input="in1", length_s="2", brightness="0", clear="0")
        # the first sound out comes a round trip later: nothing passes straight through
        program, _ = module()
        impulse = [1.0] + [0.0] * 2000
        left, right = program.run(len(impulse), [impulse])[:2]
        first = min(n for n, value in enumerate(left) if abs(value) > 1e-9)
        self.assertGreaterEqual(first, round(0.0337 * SAMPLERATE) - 1)

    def test_a_kick_goes_into_every_spring_past_the_driver_and_clips_in_the_loops(self):
        # a +12 dB burst into `kick` alone: nothing goes through the driver, both springs ring, the loops' tanh holds it
        program, _ = module(input="0", kick="in1")
        burst = [4.0 * math.exp(-n / 40.0) * (1 if n % 2 else -1) for n in range(400)] + [0.0] * int(SAMPLERATE)
        left, right, level, driven = program.run(len(burst), [burst])
        self.assertEqual(max(abs(value) for value in driven), 0.0)
        self.assertTrue(all(math.isfinite(value) for value in left + right))
        self.assertLess(max(abs(value) for value in left + right), 1.5)    # the loops' tanh holds a +12 dB burst
        self.assertGreater(max(abs(value) for value in left), 0.05)
        self.assertGreater(max(abs(value) for value in right), 0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)

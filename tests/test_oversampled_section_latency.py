"""The kit's latency convention for a section run at 2x (architecture/dsp-blocks.md, "Latency is always said"): a
host sample n's two steps sit at n and n + 1/2, a host-rate input (audio, a control, a reset) at n acts at its first
step, and every block's `latency_samples` is host samples on that clock. Then a section's figures add up exactly:
each composition here is rendered and its summed `latency_samples` held to the measured arrival within 0.01 sample,
two ways (the phase delay at LATENCY_FREQUENCY_HZ and the impulse response's centroid, or a source's jump's centre)."""
import cmath
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_block_harness import complex_amplitude_at  # noqa: E402
from twosl_dsp.circuit_modules.buchla_259_modulation_oscillator import Buchla259ModulationOscillator  # noqa: E402
from twosl_dsp.circuit_modules.buchla_259_principal_oscillator import Buchla259PrincipalOscillator  # noqa: E402
from twosl_dsp.gen_blocks import gen_code_with_blocks  # noqa: E402
from twosl_dsp.genexpr import GenProgram  # noqa: E402
from twosl_dsp.techniques.antiderivative_tanh_saturator import AntiderivativeTanhSaturator  # noqa: E402
from twosl_dsp.techniques.band_limited_edges import BandLimitedEdges  # noqa: E402
from twosl_dsp.techniques.defined_latency_pad import DefinedLatencyPad  # noqa: E402
from twosl_dsp.techniques.halfband_oversampler import (  # noqa: E402
    LATENCY_FREQUENCY_HZ, LATENCY_SAMPLE_RATE, ControlsAtTheUpsampledSteps, HalfbandDownsampler,
    HalfbandLinearPhaseDownsampler, HalfbandUpsampler)

SAMPLERATE = LATENCY_SAMPLE_RATE
TOLERANCE_SAMPLES = 0.01
IMPULSE_RENDER_SAMPLES = 4000          # the elliptic pair's tails are under 1e-12 by then
# the impulse comes after a few silent samples: a block whose Histories start at their targets (the controls') starts
# at the first sample's input, which the impulse must not be
IMPULSE_SAMPLE = 10
SINE_RENDER_SAMPLES = 22050
SINE_SETTLE_SAMPLES = 2000


def downsampler_of_kind(kind):
    downsampler_class = {"linear phase": HalfbandLinearPhaseDownsampler, "elliptic": HalfbandDownsampler}[kind]
    return downsampler_class("down", first="section_step_1", second="section_step_2")


def program_of(template, blocks):
    return GenProgram(gen_code_with_blocks(template, blocks, "oversampled section latency test"), 1, 1,
                      samplerate=SAMPLERATE)


def section_program(inside_block_of_name, downsampler_kind):
    """in1 -> HalfbandUpsampler -> the inside block (made by `inside_block_of_name(input)`, its marker once a step)
    -> the downsampler -> out1. Returns the program and the blocks' summed latency_samples."""
    upsampler = HalfbandUpsampler("up", input="in1")
    inside = inside_block_of_name("section_in")
    downsampler = downsampler_of_kind(downsampler_kind)
    template = ("/*GEN_BLOCK_FUNCTIONS*/\n/*GEN_BLOCK_DECLARATIONS*/\n"
                f"/*{upsampler.marker}*/\n"
                f"section_in = up_first;\n/*{inside.marker}*/\nsection_step_1 = {inside.instance_name}_out;\n"
                f"section_in = up_second;\n/*{inside.marker}*/\nsection_step_2 = {inside.instance_name}_out;\n"
                f"/*{downsampler.marker}*/\nout1 = down_out;\n")
    summed = upsampler.latency_samples + inside.latency_samples + downsampler.latency_samples
    return program_of(template, [upsampler, inside, downsampler]), summed


def impulse_centroid_samples(make_program):
    impulse = [0.0] * IMPULSE_RENDER_SAMPLES
    impulse[IMPULSE_SAMPLE] = 1.0
    response = list(make_program().run(IMPULSE_RENDER_SAMPLES, [impulse])[0])
    return sum(index * value for index, value in enumerate(response)) / sum(response) - IMPULSE_SAMPLE


def phase_delay_samples(make_program):
    sine = [math.sin(2 * math.pi * LATENCY_FREQUENCY_HZ * index / SAMPLERATE) for index in range(SINE_RENDER_SAMPLES)]
    output = list(make_program().run(SINE_RENDER_SAMPLES, [sine])[0])
    ratio = complex_amplitude_at(output[SINE_SETTLE_SAMPLES:], LATENCY_FREQUENCY_HZ, SAMPLERATE) / \
        complex_amplitude_at(sine[SINE_SETTLE_SAMPLES:], LATENCY_FREQUENCY_HZ, SAMPLERATE)
    return -cmath.phase(ratio) / (2 * math.pi * LATENCY_FREQUENCY_HZ / SAMPLERATE)


def edges_that_pass(input_name):
    """BandLimitedEdges at 2x with no edge ever happening: the input two steps late (a block of whole samples)."""
    edges = BandLimitedEdges("inside", naive=input_name, oversampling=2)
    edges.add_jump("0", "0", "0")
    return edges


INSIDE_BLOCKS = {
    "BandLimitedEdges (2 steps)": edges_that_pass,
    "DefinedLatencyPad, 1.5 samples (3 steps)": lambda input_name: DefinedLatencyPad(
        "inside", input=input_name, pad_samples=1.5, oversampling=2),
    "DefinedLatencyPad, 0.5 samples (1 step)": lambda input_name: DefinedLatencyPad(
        "inside", input=input_name, pad_samples=0.5, oversampling=2),
    "DefinedLatencyPad, 0.25 samples (a Thiran half step)": lambda input_name: DefinedLatencyPad(
        "inside", input=input_name, pad_samples=0.25, oversampling=2),
}


class ComposedSectionTests(unittest.TestCase):
    """upsampler -> a 2x block of known step latency -> downsampler: the summed figures are the measured delay."""

    def test_the_summed_figures_are_the_measured_delay_through_either_downsampler(self):
        for downsampler_kind in ("linear phase", "elliptic"):
            for inside_name, inside_block_of_name in INSIDE_BLOCKS.items():
                case = f"{inside_name}, {downsampler_kind} downsampler"
                _, summed = section_program(inside_block_of_name, downsampler_kind)
                make = lambda: section_program(inside_block_of_name, downsampler_kind)[0]  # noqa: E731
                self.assertAlmostEqual(phase_delay_samples(make), summed, delta=TOLERANCE_SAMPLES, msg=case)
                self.assertAlmostEqual(impulse_centroid_samples(make), summed, delta=TOLERANCE_SAMPLES, msg=case)

    def test_a_pad_in_a_section_reports_host_samples_and_counts_steps(self):
        pad = DefinedLatencyPad("pad", input="in1", pad_samples=1.5, oversampling=2)
        self.assertEqual((pad.latency_samples, pad.latency_steps, pad.whole_samples, pad.thiran_order), (1.5, 3, 3, 0))
        for bad in (0, 1.5, True, None):
            with self.assertRaises(Exception, msg=bad):
                DefinedLatencyPad("pad", input="in1", pad_samples=1, oversampling=bad)


class ControlsMeetTheirAudioTests(unittest.TestCase):
    """A host-rate control through ControlsAtTheUpsampledSteps is exactly as late as audio through the upsampler: sent
    through the downsampler in the audio's place, it arrives at the upsampler's and the downsampler's figures summed."""

    def make_program(self, downsampler_kind):
        upsampler = HalfbandUpsampler("up", input="in1")
        controls = ControlsAtTheUpsampledSteps("controls", upsampler=upsampler, controls={"level": "in1"})
        downsampler = downsampler_of_kind(downsampler_kind)
        template = ("/*GEN_BLOCK_FUNCTIONS*/\n/*GEN_BLOCK_DECLARATIONS*/\n"
                    f"/*{upsampler.marker}*/\n/*{controls.marker}*/\n"
                    "section_step_1 = controls_level_step_1;\nsection_step_2 = controls_level_step_2;\n"
                    f"/*{downsampler.marker}*/\nout1 = down_out;\n")
        return program_of(template, [upsampler, controls, downsampler]), \
            controls.latency_samples + downsampler.latency_samples

    def test_a_control_arrives_with_the_audio_sent_with_it(self):
        for downsampler_kind in ("linear phase", "elliptic"):
            _, summed = self.make_program(downsampler_kind)
            make = lambda: self.make_program(downsampler_kind)[0]  # noqa: E731
            self.assertAlmostEqual(phase_delay_samples(make), summed, delta=TOLERANCE_SAMPLES, msg=downsampler_kind)
            self.assertAlmostEqual(impulse_centroid_samples(make), summed, delta=TOLERANCE_SAMPLES,
                                   msg=downsampler_kind)

    def test_the_tanh_saturators_bias_meets_its_audio_at_1x_and_2x(self):
        # a quiet input c and a bias of 1: a bias step to 1.01 (small: the output's change, c (sech^2(b) - sech^2(1)),
        # is then linear in the bias, so the centroid is the bias path's delay, not its curve's) arrives when a step
        # of the input does. Each change is a render with the step less the render without it (the input's own start
        # at sample 0 rings the half-band at the host's Nyquist for a while: it cancels), measured as the centroid of
        # the change's first difference.
        step_sample = 100

        def rendered(input_expression, bias_expression, oversampling):
            saturator = AntiderivativeTanhSaturator("drive", input=input_expression, bias=bias_expression,
                                                    oversampling=oversampling)
            template = ("/*GEN_BLOCK_FUNCTIONS*/\nHistory time(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
                        f"/*{saturator.marker}*/\nout1 = drive_out;\ntime = time + 1;\n")
            output = program_of(template, [saturator]).run(IMPULSE_RENDER_SAMPLES, [[0.0] * IMPULSE_RENDER_SAMPLES])[0]
            return list(output), saturator.latency_samples

        def change_centroid(with_the_step, without_it):
            change = [a - b for a, b in zip(with_the_step, without_it)]
            difference = [change[index] - change[index - 1] for index in range(1, len(change))]
            return sum(index * value for index, value in enumerate(difference, start=1)) / sum(difference) - step_sample

        for oversampling in (1, 2):
            input_stepped, latency_samples = rendered(f"(time >= {step_sample}) * 0.01", "1.0", oversampling)
            input_still, _ = rendered("0", "1.0", oversampling)
            bias_stepped, _ = rendered("0.01", f"1.0 + (time >= {step_sample}) * 0.01", oversampling)
            bias_still, _ = rendered("0.01", "1.0", oversampling)
            audio_arrival = change_centroid(input_stepped, input_still)
            bias_arrival = change_centroid(bias_stepped, bias_still)
            self.assertAlmostEqual(audio_arrival, latency_samples, delta=TOLERANCE_SAMPLES, msg=oversampling)
            self.assertAlmostEqual(bias_arrival, audio_arrival, delta=TOLERANCE_SAMPLES, msg=oversampling)


class SourceEventTests(unittest.TestCase):
    """A source's figure counts from its event: a reset at host sample n acts at n (its first step), and reaches the
    output at n + the summed figures."""

    RESET_SAMPLE = 1350           # a quarter cycle of 8.18 Hz in: the principal sine near its crest

    def jump_centre_after_the_reset(self, oversampling, downsampler_kind):
        oscillator = Buchla259PrincipalOscillator("osc", frequency_hz="8.18", frequency_modulation_hz="0",
                                                  oversampling=oversampling)
        blocks = [oscillator]
        template = ("/*GEN_BLOCK_FUNCTIONS*/\nHistory time(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
                    f"if (time > {self.RESET_SAMPLE - 0.5} && time < {self.RESET_SAMPLE + 0.5}) {{\n"
                    f"{oscillator.reset_statements()}\n}}\n")
        summed = oscillator.latency_samples
        if oversampling == 2:
            downsampler = downsampler_of_kind(downsampler_kind)
            blocks.append(downsampler)
            template += (f"/*{oscillator.marker}*/\nsection_step_1 = osc_sine;\n/*{oscillator.marker}*/\n"
                         f"section_step_2 = osc_sine;\n/*{downsampler.marker}*/\nout1 = down_out;\n")
            summed += downsampler.latency_samples
        else:
            template += f"/*{oscillator.marker}*/\nout1 = osc_sine;\n"
        template += "time = time + 1;\n"
        count = self.RESET_SAMPLE + 60
        output = list(program_of(template, blocks).run(count, [[0.0] * count])[0])
        before = output[self.RESET_SAMPLE - 1]
        half = 0.5 * before
        for index in range(self.RESET_SAMPLE, count):
            if output[index] < half:
                crossing = index - 1 + (output[index - 1] - half) / (output[index - 1] - output[index])
                return crossing - self.RESET_SAMPLE, summed
        raise AssertionError(f"the reset's jump never crossed half its height (from {before})")

    def test_a_principal_oscillators_reset_arrives_at_its_summed_figures(self):
        for oversampling, downsampler_kind in ((1, None), (2, "linear phase")):
            centre, summed = self.jump_centre_after_the_reset(oversampling, downsampler_kind)
            self.assertAlmostEqual(centre, summed, delta=TOLERANCE_SAMPLES, msg=(oversampling, downsampler_kind))

    def test_a_modulation_oscillators_reset_starts_its_cycle_at_the_resets_sample(self):
        # latency_samples 0: the saw at the reset's sample is the cycle's start, -1, at 1x and at each 2x step
        for oversampling in (1, 2):
            oscillator = Buchla259ModulationOscillator("mod", frequency_hz="100", wave="2", oversampling=oversampling)
            template = ("/*GEN_BLOCK_FUNCTIONS*/\nHistory time(0);\n/*GEN_BLOCK_DECLARATIONS*/\n"
                        f"if (time > 99.5 && time < 100.5) {{\n{oscillator.reset_statements()}\n}}\n"
                        f"/*{oscillator.marker}*/\nfirst_step = mod_out;\n"
                        + f"/*{oscillator.marker}*/\n" * (oversampling - 1) + "out1 = first_step;\ntime = time + 1;\n")
            output = list(program_of(template, [oscillator]).run(102, [[0.0] * 102])[0])
            self.assertEqual(oscillator.latency_samples, 0)
            self.assertAlmostEqual(output[100], -1.0, places=12, msg=oversampling)
            self.assertAlmostEqual(output[101], 2 * 100 / SAMPLERATE - 1, places=9, msg=oversampling)


if __name__ == "__main__":
    unittest.main()

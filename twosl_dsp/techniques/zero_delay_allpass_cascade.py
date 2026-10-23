"""The zero-delay all-pass cascade (a technique): first- and second-order all-pass sections in series, lossless under
any cutoff modulation, with an optional feedback loop from the output to the input solved without a unit delay: a
phaser's core, and the kit's all-pass for smearing and diffusion (references/dsp.md, "Zero-delay all-pass cascade";
the mathematics in references/allpass-and-diffusion.md §1).

The sections' transfer functions are the bilinear transforms (prewarped, Zavalishin eq. 3.18) of the analog all-passes:
- `FirstOrderAllpassStage(cutoff_hz)`: (1 - s) / (1 + s) (Zavalishin eq. 2.12), phase -90 degrees at the cutoff.
  With g = tan(pi fc / sr): H(z) = (k + z^-1) / (1 + k z^-1), k = (g - 1) / (g + 1).
- `SecondOrderAllpassStage(cutoff_hz, q)`: (s^2 - 2Rs + 1) / (s^2 + 2Rs + 1) (eq. 4.23, 2R = 1 / q), phase -180 at
  the cutoff, steeper the higher q. H(z) = (a2 + a1 z^-1 + z^-2) / (1 + a1 z^-1 + a2 z^-2) with D = 1 + 2Rg + g^2,
  a2 = (1 - 2Rg + g^2) / D, a1 = 2 (g^2 - 1) / D: the lattice's k2 = a2, k1 = a1 / (1 + a2) = (g^2 - 1) / (g^2 + 1).
So at fixed cutoffs they are exactly the TPT one-pole's LP - HP and the TPT state-variable filter's x - 4R BP
(references/dsp.md). Their realisation is not: each is a normalised lattice (Gray-Markel), a chain of lossless
junctions [y; f] = [[k, c], [c, -k]] [x; v], c = sqrt(1 - k^2), v the delayed return of the inner all-pass. Each
junction is orthogonal, so every sample |y|^2 + |state|^2 = |x|^2 + |old state|^2 whatever the coefficients do: the
cascade can neither gain nor lose energy under modulation. (The TPT forms are the same sections with the state scaled
by sqrt((1 - k) / (1 + k)): when k moves, the scaling moves, and energy enters. Measured, a TPT first-order all-pass
with its cutoff jumping across the band every sample gains 7.7x, six of them 470x, and a feedback loop around them
diverges; the lattice holds: tests/test_techniques.py.) Coefficients are written every sample: no zipper.

The loop (optional): u = input + feedback x LP(HP(y)), y the last section's output, HP an optional coupling high-pass
at the cascade's output (a coupling capacitor; its output `<name>_coupled` is also what a circuit taps), LP an
optional low-pass in the fed-back path only (both the kit's zero-delay one-pole). Every section and loop filter is
affine in its input this sample (gain inside (-1, 1), an offset from its state), so the chain is G u + S and the loop
solves exactly, u = (input + feedback S) / (1 - feedback G) (Zavalishin §3.9's zero-delay feedback). |G| < 1 and the
feedback is held to [-0.999, 0.999]: the denominator never reaches 0, and a lossless chain in a loop of gain under 1
is stable however its sections move. With positive feedback it peaks 1 / (1 - feedback) where the cascade's phase is
a whole turn (a phaser's resonant peaks between its notches). `loop_limit` (a number, in the input's units), when
given, puts the solved u through the kit's knee soft clip scaled to it (an amplifier's rails at the loop's input).

Outputs: `<name>_out` (y), `<name>_coupled` (y after the coupling high-pass; y without one), `<name>_loop_input` (u,
after the limit). `prewarp_hz`, when given, is the one frequency every section is exact at, with one tan for all
(g_i = tan(pi fp / sr) fc_i / fp); by default each section is exact at its own cutoff.
"""
import dataclasses
import math

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique
from twosl_dsp.generated_numbers import generated_number
from twosl_dsp.techniques.knee_soft_clip import KneeSoftClip
from twosl_dsp.techniques.zero_delay_one_pole_filter import (HIGHEST_PREWARP_OF_SAMPLE_RATE, LOWEST_CUTOFF_HZ,
                                                           ZeroDelayOnePoleFilter)

HIGHEST_FEEDBACK = 0.999
LOOP_LIMIT_KNEE = 0.8      # the soft clip is clean to 80 % of the limit, then rounds into it
LOWEST_Q, HIGHEST_Q = 0.05, 200.0


@dataclasses.dataclass(frozen=True)
class FirstOrderAllpassStage:
    """A first-order all-pass section at `cutoff_hz` (a GenExpr expression)."""
    cutoff_hz: str


@dataclasses.dataclass(frozen=True)
class SecondOrderAllpassStage:
    """A second-order all-pass section at `cutoff_hz` with `q` (GenExpr expressions)."""
    cutoff_hz: str
    q: str


class ZeroDelayAllpassCascade(Technique):
    """`<name>_out`, `<name>_coupled`, `<name>_loop_input`: `input` through `stages` (FirstOrderAllpassStage /
    SecondOrderAllpassStage, in order) with `feedback` (held to +-0.999) from the output, through the optional
    `coupling_highpass_hz` and `feedback_lowpass_hz` one-poles, back to the input, solved with no unit delay;
    `loop_limit` an optional rail (a number) at the loop's input. State: one per first-order section, two per
    second-order one, and the loop filters'."""

    def __init__(self, instance_name, input, stages, feedback="0", prewarp_hz=None, coupling_highpass_hz=None,
                 feedback_lowpass_hz=None, loop_limit=None):
        stages = list(stages)
        if not stages or not all(isinstance(stage, (FirstOrderAllpassStage, SecondOrderAllpassStage))
                                 for stage in stages):
            raise BuildError(f"ZeroDelayAllpassCascade {instance_name}: stages must be a non-empty list of "
                             f"FirstOrderAllpassStage / SecondOrderAllpassStage, got {stages!r}")
        if loop_limit is not None and (isinstance(loop_limit, bool) or not isinstance(loop_limit, (int, float))
                                       or not loop_limit > 0):
            raise BuildError(f"ZeroDelayAllpassCascade {instance_name}: loop_limit must be a number above 0, "
                             f"got {loop_limit!r}")
        for index, stage in enumerate(stages, start=1):
            for field in dataclasses.fields(stage):
                value = getattr(stage, field.name)
                if not isinstance(value, str) or not value.strip():
                    raise BuildError(f"ZeroDelayAllpassCascade {instance_name}: section {index}'s {field.name} must be "
                                     f"a GenExpr expression, got {value!r}")
        inputs = dict(input=input, feedback=feedback)
        if prewarp_hz is not None:
            inputs["prewarp_hz"] = prewarp_hz
        super().__init__(instance_name, **inputs)
        self.latency_samples = 0       # zero-delay all-passes and loop: no sample added (the phase is the analog cascade's)
        p = instance_name
        self.stages = stages
        self.coupling = None if coupling_highpass_hz is None else ZeroDelayOnePoleFilter(
            f"{p}_coupling", input=f"{p}_out", cutoff_hz=coupling_highpass_hz)
        self.feedback_filter = None if feedback_lowpass_hz is None else ZeroDelayOnePoleFilter(
            f"{p}_feedback_filter", input=f"{p}_coupled", cutoff_hz=feedback_lowpass_hz)
        self.loop_limit = None if loop_limit is None else generated_number(float(loop_limit))
        self.limiter = None if loop_limit is None else KneeSoftClip(
            f"{p}_limit", input=f"{p}_loop_solved / {self.loop_limit!r}", knee=LOOP_LIMIT_KNEE)

    def _filters(self):
        return [block for block in (self.coupling, self.feedback_filter, self.limiter) if block]

    def functions(self):
        functions = {}
        for block in self._filters():
            functions.update(block.functions())
        return functions

    def declarations(self):
        p = self.instance_name
        states = []
        for index, stage in enumerate(self.stages, start=1):
            states += [f"{p}_section_{index}_d"] if isinstance(stage, FirstOrderAllpassStage) else \
                [f"{p}_section_{index}_d1", f"{p}_section_{index}_d2"]
        return "\n".join(["History " + ", ".join(f"{name}(0)" for name in states) + ";"]
                         + [text for text in (block.declarations().strip() for block in self._filters()) if text])

    def _section_coefficients(self, index, stage):
        """Statements leaving the section's g (prewarped) and its junctions' k and c, and its response to its input
        this sample (`_gain`, `_offset`)."""
        s = f"{self.instance_name}_section_{index}"
        if "prewarp_hz" in self.input_expressions:
            g = (f"{s}_cutoff = max({stage.cutoff_hz}, {LOWEST_CUTOFF_HZ!r});\n"
                 f"{s}_g = {self.instance_name}_prewarp_tangent * ({s}_cutoff / {self.instance_name}_prewarp_point);")
        else:
            g = (f"{s}_cutoff = max({stage.cutoff_hz}, {LOWEST_CUTOFF_HZ!r});\n"
                 f"{s}_prewarp = min({s}_cutoff, samplerate * {HIGHEST_PREWARP_OF_SAMPLE_RATE!r});\n"
                 f"{s}_g = tan(pi * {s}_prewarp / samplerate) * ({s}_cutoff / {s}_prewarp);")
        if isinstance(stage, FirstOrderAllpassStage):
            return g + f"""
// first-order section: one junction, k = (g - 1) / (g + 1), c = sqrt(1 - k^2)
{s}_k = ({s}_g - 1) / ({s}_g + 1);
{s}_c = 2 * sqrt({s}_g) / ({s}_g + 1);
{s}_gain = {s}_k;
{s}_offset = {s}_c * {s}_d;"""
        return g + f"""
// second-order section: two junctions, k1 = (g^2 - 1) / (g^2 + 1), k2 = (1 - 2Rg + g^2) / (1 + 2Rg + g^2)
{s}_damping_g = {s}_g / clamp({stage.q}, {LOWEST_Q!r}, {HIGHEST_Q!r});
{s}_g_squared = {s}_g * {s}_g;
{s}_k1 = ({s}_g_squared - 1) / ({s}_g_squared + 1);
{s}_c1 = 2 * {s}_g / ({s}_g_squared + 1);
{s}_denominator = 1 + {s}_damping_g + {s}_g_squared;
{s}_k2 = (1 - {s}_damping_g + {s}_g_squared) / {s}_denominator;
{s}_c2 = 2 * sqrt({s}_damping_g * (1 + {s}_g_squared)) / {s}_denominator;
// the inner junction runs on the states alone: its output is what returns to the outer one
{s}_inner = {s}_k1 * {s}_d2 + {s}_c1 * {s}_d1;
{s}_gain = {s}_k2;
{s}_offset = {s}_c2 * {s}_inner;"""

    def _section_tick(self, index, stage, section_input):
        s = f"{self.instance_name}_section_{index}"
        if isinstance(stage, FirstOrderAllpassStage):
            return f"""{s}_output = {s}_k * {section_input} + {s}_c * {s}_d;
{s}_d = {s}_c * {section_input} - {s}_k * {s}_d;"""
        return f"""{s}_output = {s}_k2 * {section_input} + {s}_c2 * {s}_inner;
{s}_d1 = {s}_c1 * {s}_d2 - {s}_k1 * {s}_d1;
{s}_d2 = {s}_c2 * {section_input} - {s}_k2 * {s}_inner;"""

    def statements(self):
        p = self.instance_name
        lines = [self.substituted("// ${p}: all-pass cascade, lossless sections, zero-delay loop "
                                  "(kit technique: zero-delay all-pass cascade)")]
        if "prewarp_hz" in self.input_expressions:
            lines.append(self.substituted(
                "${p}_prewarp_point = clamp(${prewarp_hz}, ${lowest}, samplerate * ${highest});\n"
                "${p}_prewarp_tangent = tan(pi * ${p}_prewarp_point / samplerate);",
                lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_PREWARP_OF_SAMPLE_RATE))
        chain = []
        for index, stage in enumerate(self.stages, start=1):
            lines.append(self._section_coefficients(index, stage))
            chain.append(f"{p}_section_{index}")
        for block, output in ((self.coupling, "highpass"), (self.feedback_filter, "lowpass")):
            if block:
                lines.append(block.coefficient_statements())
                lines.append(block.response_statements(output))
                chain.append(f"{block.instance_name}_{output}")
        # the chain from u to the fed-back signal, composed: G u + S
        lines.append(f"{p}_chain_gain = {chain[0]}_gain;\n{p}_chain_offset = {chain[0]}_offset;")
        for name in chain[1:]:
            lines.append(f"{p}_chain_offset = {name}_gain * {p}_chain_offset + {name}_offset;\n"
                         f"{p}_chain_gain = {name}_gain * {p}_chain_gain;")
        lines.append(self.substituted(
            "// the loop solved: u = input + k (G u + S)\n"
            "${p}_feedback = clamp(${feedback}, -${most}, ${most});\n"
            "${p}_loop_solved = (${input} + ${p}_feedback * ${p}_chain_offset) / (1 - ${p}_feedback * ${p}_chain_gain);",
            most=HIGHEST_FEEDBACK))
        if self.limiter:
            lines.append(self.limiter.statements())
            lines.append(f"{p}_loop_input = {self.loop_limit!r} * {p}_limit_out;")
        else:
            lines.append(f"{p}_loop_input = {p}_loop_solved;")
        # the ticks, in order, with the solved input
        section_input = f"{p}_loop_input"
        for index, stage in enumerate(self.stages, start=1):
            lines.append(self._section_tick(index, stage, section_input))
            section_input = f"{p}_section_{index}_output"
        lines.append(f"{p}_out = {section_input};")
        if self.coupling:
            lines.append(self.coupling.tick_statements())
            lines.append(f"{p}_coupled = {p}_coupling_highpass;")
        else:
            lines.append(f"{p}_coupled = {p}_out;")
        if self.feedback_filter:
            lines.append(self.feedback_filter.tick_statements())
        return "\n".join(lines)


def small_signal_response(frequency_hz, stages, sample_rate, prewarp_hz=None):
    """The cascade's complex response at `frequency_hz` with no loop: `stages` as (cutoff_hz,) or (cutoff_hz, q)
    numbers, each the analog all-pass at s = j tan(pi f / sr) / g (g prewarped as the cascade prewarps it)."""
    response = 1
    for stage in stages:
        cutoff = max(stage[0], LOWEST_CUTOFF_HZ)
        point = min(max(prewarp_hz if prewarp_hz is not None else cutoff, LOWEST_CUTOFF_HZ),
                    HIGHEST_PREWARP_OF_SAMPLE_RATE * sample_rate)
        g = math.tan(math.pi * point / sample_rate) * cutoff / point
        s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) / g
        if len(stage) == 1:
            response *= (1 - s) / (1 + s)
        else:
            damping = 1 / min(max(stage[1], LOWEST_Q), HIGHEST_Q)
            response *= (s * s - damping * s + 1) / (s * s + damping * s + 1)
    return response

"""The zero-delay ladder filter (a technique): a 4-pole low-pass ladder, zero-delay feedback (TPT), tanh at the
loop's input, or (`linear=True`) none: the linear ladder (references/dsp.md, "Zero-delay ladder filter").

A technique, not a circuit module: it is the textbook ladder (Zavalishin's ideal four one-poles in a loop, one tanh
standing for an input pair), modelled on no particular circuit. It has no transistor ladder's schematic, no part's
mismatch or rails behind it, and its controls are the method's (cutoff in Hz, feedback k as Resonance 0..1), not a
synthesizer's. The modelled Moog ladder is the circuit module MoogTransistorLadder (circuit_modules/moog_transistor_ladder.py).

Four trapezoidal one-poles, g = tan(pi fc / sr), G = g / (1 + g). The loop is solved without a unit delay
(Zavalishin, The Art of VA Filter Design rev. 2.1.2, §5.3 eq. 5.8):

    S = (G^3 s1 + G^2 s2 + G s3 + s4) / (1 + g),   u = tanh((x - k S) / (1 + k G^4))

i.e. the nonlinear loop linearised at zero (§6.6) and the tanh then applied, as a transistor ladder's input pair
saturates. k = 4 is the edge of self-oscillation at every cutoff, and the oscillation is at fc (the prewarped
bilinear transform puts the analog ladder's 180-degree point exactly at fc). Resonance 0..1 maps linearly to
k = 0..FEEDBACK_AT_FULL_RESONANCE, so it sings from Resonance 0.92 up.

The linear form (a construction choice, `linear=True`): u = (x - k S) / (1 + k G^4), eq. 5.8 itself, no tanh, so the
output is the input's level times the response whatever the level: no harmonics, no compression. A linear loop has
nothing to hold an oscillation (§5.2: infinite resonance at k = 4; above, it grows without bound), so its Resonance
0..1 maps to k = 0..LINEAR_FEEDBACK_AT_FULL_RESONANCE, under 4: it rings, it never sings.

Why this and not the richer per-stage-tanh ladder (research 2026-10-19, against an RK4 x8 reference of each analog
model): solving the loop exactly (Newton on u) changes nothing measurable (-52.6 dB vs its model either way); a
per-stage tanh ladder (secant gains, one predictor solve: 5 tanh a sample, ~2.8x the CPU) tracks its own model as
well, but that model's oscillation sinks flat with its amplitude (-4 cents at k 4.04, -32 cents at k 4.35, every
cutoff), so its resonance can't play in tune. This one oscillates within 0.6 cents of fc at 300 Hz to 0.45 sr.
"""
import math

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique

FEEDBACK_AT_FULL_RESONANCE = 4.35        # k = 4 (self-oscillation) at Resonance 0.92
# [DESIGN] the linear form's k at Resonance 1: as near 4 as rings and stays playable: the peak at fc is (1 + k) / (4 - k)
# = 49 (+34 dB) over the pass band, a kick at fc rings to -60 dB in 0.87 s at 200 Hz, 0.17 s at 1 kHz (the poles
# -1 + k^(1/4) e^(+-j pi / 4) in units of the cutoff's angular frequency)
LINEAR_FEEDBACK_AT_FULL_RESONANCE = 3.9
HIGHEST_CUTOFF_OF_SAMPLE_RATE = 0.45     # g = tan(0.45 pi) = 6.3: finite, so the solve stays well-conditioned
LOWEST_CUTOFF_HZ = 10.0


def feedback_at_full_resonance(linear):
    """k at Resonance 1 for the form: the saturating ladder's 4.35 (sings from 0.92), the linear one's 3.9 (never)."""
    return LINEAR_FEEDBACK_AT_FULL_RESONANCE if linear else FEEDBACK_AT_FULL_RESONANCE


class ZeroDelayLadderFilter(Technique):
    """`<name>_out`: `input` through the ladder at `cutoff_hz` (clamped to [10 Hz, 0.45 sr]) and `resonance` (0..1,
    clamped): the ladder's own output, its pass band 1 / (1 + k) (a level rule on top is the instrument's). Also
    `<name>_feedback` (k) and `<name>_cutoff_hz` (as clamped). `reset_statements()` empties the four stages.
    `linear` (a construction choice, a bool): the loop's input with no tanh, k under 4 (the module's docstring)."""

    def __init__(self, instance_name, input, cutoff_hz, resonance, linear=False):
        if not isinstance(linear, bool):
            raise BuildError(f"ZeroDelayLadderFilter {instance_name}: linear is True or False, got {linear!r}")
        super().__init__(instance_name, input=input, cutoff_hz=cutoff_hz, resonance=resonance)
        self.linear = linear
        self.feedback_at_full_resonance = feedback_at_full_resonance(linear)
        self.latency_samples = 0       # zero-delay feedback: no sample added (its phase is the analog ladder's)

    def declarations(self):
        return self.substituted("History ${p}_s1(0), ${p}_s2(0), ${p}_s3(0), ${p}_s4(0);")

    def statements(self):
        return self.substituted("""// ${p}: 4-pole ladder, zero-delay feedback, ${form} (kit technique: zero-delay ladder filter)
${p}_cutoff_hz = clamp(${cutoff_hz}, ${lowest}, samplerate * ${highest});
${p}_g = tan(pi * ${p}_cutoff_hz / samplerate);
${p}_stage = ${p}_g / (1 + ${p}_g);
${p}_stage_2 = ${p}_stage * ${p}_stage;
${p}_feedback = clamp(${resonance}, 0, 1) * ${full};
${p}_states_through = (${p}_stage_2 * ${p}_stage * ${p}_s1 + ${p}_stage_2 * ${p}_s2 + ${p}_stage * ${p}_s3 + ${p}_s4) / (1 + ${p}_g);
${p}_u = ${shaper}((${input} - ${p}_feedback * ${p}_states_through) / (1 + ${p}_feedback * ${p}_stage_2 * ${p}_stage_2));
${p}_v = (${p}_u - ${p}_s1) * ${p}_stage;
${p}_y1 = ${p}_v + ${p}_s1;
${p}_s1 = ${p}_y1 + ${p}_v;
${p}_v2 = (${p}_y1 - ${p}_s2) * ${p}_stage;
${p}_y2 = ${p}_v2 + ${p}_s2;
${p}_s2 = ${p}_y2 + ${p}_v2;
${p}_v3 = (${p}_y2 - ${p}_s3) * ${p}_stage;
${p}_y3 = ${p}_v3 + ${p}_s3;
${p}_s3 = ${p}_y3 + ${p}_v3;
${p}_v4 = (${p}_y3 - ${p}_s4) * ${p}_stage;
${p}_y4 = ${p}_v4 + ${p}_s4;
${p}_s4 = ${p}_y4 + ${p}_v4;
${p}_out = ${p}_y4;""",
                                lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_CUTOFF_OF_SAMPLE_RATE,
                                full=self.feedback_at_full_resonance, shaper="" if self.linear else "tanh",
                                form="linear (no tanh)" if self.linear else "tanh at the loop's input")

    def reset_statements(self):
        """The four stages' states empty (a fresh ladder)."""
        return self.substituted("${p}_s1 = 0;\n${p}_s2 = 0;\n${p}_s3 = 0;\n${p}_s4 = 0;")


def small_signal_magnitude(frequency_hz, cutoff_hz, resonance, sample_rate, linear=False):
    """|H| of the ladder for small signals (tanh slope 1; the linear form's at any level), as its displays draw it:
    the analog ladder 1 / ((1 + s)^4 + k) at s = j tan(pi f / sr) / tan(pi fc / sr), k the form's at `resonance`.
    Python's copy of templates/zero-delay-ladder-response.template.js, which the tests hold equal to it and to the
    technique."""
    cutoff_hz = min(max(cutoff_hz, LOWEST_CUTOFF_HZ), HIGHEST_CUTOFF_OF_SAMPLE_RATE * sample_rate)
    k = min(max(resonance, 0.0), 1.0) * feedback_at_full_resonance(linear)
    s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) / math.tan(
        math.pi * cutoff_hz / sample_rate)
    return abs(1 / ((1 + s) ** 4 + k))


def response_script_code():
    """The ES5 for a device's displays, both forms (templates/zero-delay-ladder-response.template.js), with the
    technique's constants filled in: `ladderFeedbackGain(resonance, linear)` (k) and `ladderResponse(frequencyHz,
    cutoffHz, feedbackGain, sampleRate)` (|H| at that k)."""
    from twosl_dsp.generated_scripts import fill_template, kit_template_text
    return fill_template(kit_template_text("zero-delay-ladder-response.template.js"), {
        "LADDER_FEEDBACK_AT_FULL_RESONANCE": repr(FEEDBACK_AT_FULL_RESONANCE),
        "LADDER_LINEAR_FEEDBACK_AT_FULL_RESONANCE": repr(LINEAR_FEEDBACK_AT_FULL_RESONANCE),
        "LADDER_HIGHEST_CUTOFF_OF_SAMPLE_RATE": repr(HIGHEST_CUTOFF_OF_SAMPLE_RATE),
        "LADDER_LOWEST_CUTOFF_HZ": repr(LOWEST_CUTOFF_HZ)}, "zero-delay-ladder-response.template.js")

"""The ladder block: a 4-pole low-pass ladder, zero-delay feedback (TPT), tanh at the loop's input
(references/dsp.md, "Ladder").

Four trapezoidal one-poles, g = tan(pi fc / sr), G = g / (1 + g). The loop is solved without a unit delay
(Zavalishin, The Art of VA Filter Design rev. 2.1.2, §5.3 eq. 5.8):

    S = (G^3 s1 + G^2 s2 + G s3 + s4) / (1 + g),   u = tanh((x - k S) / (1 + k G^4))

i.e. the nonlinear loop linearised at zero (§6.6) and the tanh then applied, as a transistor ladder's input pair
saturates. k = 4 is the edge of self-oscillation at every cutoff, and the oscillation is at fc (the prewarped
bilinear transform puts the analog ladder's 180-degree point exactly at fc). Resonance 0..1 maps linearly to
k = 0..FEEDBACK_AT_FULL_RESONANCE, so it sings from Resonance 0.92 up.

Why this and not the richer per-stage-tanh ladder (research 2026-10-19, against an RK4 x8 reference of each analog
model): solving the loop exactly (Newton on u) changes nothing measurable (-52.6 dB vs its model either way); a
per-stage tanh ladder (secant gains, one predictor solve: 5 tanh a sample, ~2.8x the CPU) tracks its own model as
well, but that model's oscillation sinks flat with its amplitude (-4 cents at k 4.04, -32 cents at k 4.35, every
cutoff), so its resonance can't play in tune. This one oscillates within 0.6 cents of fc at 300 Hz to 0.45 sr.
"""
import math

from m4l_dev.gen_blocks import GenBlock

FEEDBACK_AT_FULL_RESONANCE = 4.35        # k = 4 (self-oscillation) at Resonance 0.92
MAKEUP_PER_FEEDBACK = 0.4                # output x (1 + 0.4 k): stab's level make-up for the pass band k costs
HIGHEST_CUTOFF_OF_SAMPLE_RATE = 0.45     # g = tan(0.45 pi) = 6.3: finite, so the solve stays well-conditioned
LOWEST_CUTOFF_HZ = 10.0


class LadderFilter(GenBlock):
    """`<name>_out`: `input` through the ladder at `cutoff_hz` (clamped to [10 Hz, 0.45 sr]) and `resonance` (0..1,
    clamped). Also `<name>_feedback` (k) and `<name>_cutoff_hz` (as clamped)."""

    def __init__(self, instance_name, input, cutoff_hz, resonance):
        super().__init__(instance_name, input=input, cutoff_hz=cutoff_hz, resonance=resonance)

    def declarations(self):
        return self.substituted("History ${p}_s1(0), ${p}_s2(0), ${p}_s3(0), ${p}_s4(0);")

    def statements(self):
        return self.substituted("""// ${p}: 4-pole ladder, zero-delay feedback, tanh at the loop's input (kit ladder block)
${p}_cutoff_hz = clamp(${cutoff_hz}, ${lowest}, samplerate * ${highest});
${p}_g = tan(pi * ${p}_cutoff_hz / samplerate);
${p}_stage = ${p}_g / (1 + ${p}_g);
${p}_stage_2 = ${p}_stage * ${p}_stage;
${p}_feedback = clamp(${resonance}, 0, 1) * ${full};
${p}_states_through = (${p}_stage_2 * ${p}_stage * ${p}_s1 + ${p}_stage_2 * ${p}_s2 + ${p}_stage * ${p}_s3 + ${p}_s4) / (1 + ${p}_g);
${p}_u = tanh((${input} - ${p}_feedback * ${p}_states_through) / (1 + ${p}_feedback * ${p}_stage_2 * ${p}_stage_2));
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
${p}_out = ${p}_y4 * (1 + ${makeup} * ${p}_feedback);""",
                                lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_CUTOFF_OF_SAMPLE_RATE,
                                full=FEEDBACK_AT_FULL_RESONANCE, makeup=MAKEUP_PER_FEEDBACK)


def small_signal_magnitude(frequency_hz, cutoff_hz, resonance, sample_rate):
    """|H| of the ladder for small signals (tanh slope 1), as its displays draw it: the analog ladder
    1 / ((1 + s)^4 + k) at s = j tan(pi f / sr) / tan(pi fc / sr), times the make-up. Python's copy of
    templates/ladder-response.template.js, which the tests hold equal to it and to the block."""
    cutoff_hz = min(max(cutoff_hz, LOWEST_CUTOFF_HZ), HIGHEST_CUTOFF_OF_SAMPLE_RATE * sample_rate)
    k = min(max(resonance, 0.0), 1.0) * FEEDBACK_AT_FULL_RESONANCE
    s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) / math.tan(
        math.pi * cutoff_hz / sample_rate)
    return abs(1 / ((1 + s) ** 4 + k)) * (1 + MAKEUP_PER_FEEDBACK * k)


def response_script_code():
    """The ES5 `ladderResponse(frequencyHz, cutoffHz, resonance, sampleRate)` for a device's displays, with the
    block's constants filled in (templates/ladder-response.template.js)."""
    from m4l_dev.generated_scripts import fill_template, kit_template_text
    return fill_template(kit_template_text("ladder-response.template.js"), {
        "LADDER_FEEDBACK_AT_FULL_RESONANCE": repr(FEEDBACK_AT_FULL_RESONANCE),
        "LADDER_MAKEUP_PER_FEEDBACK": repr(MAKEUP_PER_FEEDBACK),
        "LADDER_HIGHEST_CUTOFF_OF_SAMPLE_RATE": repr(HIGHEST_CUTOFF_OF_SAMPLE_RATE),
        "LADDER_LOWEST_CUTOFF_HZ": repr(LOWEST_CUTOFF_HZ)}, "ladder-response.template.js")

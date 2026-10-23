"""The knee soft clip (a technique; references/dsp.md, "Knee soft clip"): clean below a knee, a tanh shoulder above
it that reaches 1 and stays under it. What every device's output goes through last.

    y = x                                                  |x| <= knee
    y = sign(x) * (knee + h * tanh((|x| - knee) / h)),     h = 1 - knee,  |x| > knee

The shoulder has the line's value (knee) and slope (tanh'(0) = 1) at the knee, so the join is C1, and it
approaches 1 from below, so the output is bounded by 1 for any input. Memoryless: no latency, no state.

Three devices had a copy of this (2sl gate and stab at knee 0.8, in front of nothing; 2sl filter at 0.95, after its
limiter). The knee is a constant of the device (a Python number, not a GenExpr): `h` is computed here, in decimal, so
1 - 0.8 is 0.2 and not 0.19999999999999996, and the output is bit for bit what the devices' own copies gave.
"""
from decimal import Decimal

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique
from twosl_dsp.generated_numbers import generated_number

FUNCTIONS = {
    "soft_clip_above_knee": """// clean up to the knee, then knee + headroom * tanh(excess / headroom): value and slope continuous, bounded by 1
soft_clip_above_knee(v, knee, headroom) {
\ta = abs(v);
\ty = v;
\tif (a > knee) {
\t\ty = (v < 0 ? -1 : 1) * (knee + headroom * tanh((a - knee) / headroom));
\t}
\treturn y;
}""",
}


class KneeSoftClip(Technique):
    """`<name>_out` = `input` through the soft clip with `knee` (a number, 0 < knee < 1)."""

    def __init__(self, instance_name, input, knee):
        if isinstance(knee, bool) or not isinstance(knee, (int, float)) or not 0.0 < knee < 1.0:
            raise BuildError(f"KneeSoftClip {instance_name}: the knee must be a number between 0 and 1 "
                             f"(exclusive), got {knee!r}")
        super().__init__(instance_name, input=input)
        self.knee = generated_number(float(knee))
        self.headroom = float(Decimal(1) - Decimal(repr(self.knee)))
        self.latency_samples = 0       # memoryless: the output is the input's own sample

    def functions(self):
        return dict(FUNCTIONS)

    def statements(self):
        return self.substituted("// ${p}: soft clip, knee ${knee} (kit technique: knee soft clip)\n"
                                "${p}_out = soft_clip_above_knee(${input}, ${knee}, ${headroom});",
                                knee=self.knee, headroom=self.headroom)

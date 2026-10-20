"""The saturator block: tanh with first-order antiderivative antialiasing (ADAA) of its nonlinear part
(references/dsp.md, "Saturator").

tanh(x) = x + r(x). The nonlinear residual r is antialiased (Bilbao et al. 2017, eq. 5):

    r~[n] = (R(x[n]) - R(x[n-1])) / (x[n] - x[n-1]),   R(x) = log cosh x - x^2 / 2

(and, where the two inputs are too close for that quotient, r at their midpoint: the paper's ill-conditioning
fallback). That average over the step is half a sample late; the linear part x goes through a first-order Thiran
allpass with half a sample of delay (a = (1 - 0.5) / (1 + 0.5) = 1/3), so both halves are half a sample late and the
small-signal response stays flat. Plain ADAA of tanh would average the whole signal: -2.4 dB at 10 kHz, -6.4 dB at
15 kHz (44.1 kHz). Measured (research, 2026-10-19; tests/test_dsp_blocks.py keeps the claims): a 0.6 x 4.5 sine's
worst alias below 10 kHz, naive -> plain ADAA -> this: 5 kHz -33.3 -> -48.6 -> -49.8 dB, 8 kHz -23.7 -> -53.6 ->
-56.4 dB; small signals 0.00 dB at 5, 10 and 15 kHz.
"""
from m4l_dev.gen_blocks import GenBlock

# Below this input step the quotient loses digits (R's rounding over the step); above it the midpoint is off by about
# r''' * step^2 / 24. 1e-5 keeps both under 1e-10 for |x| < 20.
ILL_CONDITIONED_STEP = 1e-5
HALF_SAMPLE_ALLPASS_COEFFICIENT = 1.0 / 3.0   # Thiran, first order, delay D = 0.5: a = (1 - D) / (1 + D)

FUNCTIONS = {
    "tanh_residual_antiderivative": """// log cosh x - x^2/2: the antiderivative of tanh x - x, without overflow (log cosh x = |x| + log(1 + e^-2|x|) - log 2)
tanh_residual_antiderivative(x) {
\tmagnitude = abs(x);
\treturn magnitude + log(1 + exp(-2 * magnitude)) - 0.6931471805599453 - 0.5 * x * x;
}""",
    "tanh_residual_antialiased": f"""// tanh x - x averaged over the step from the last input to this one (first-order ADAA)
tanh_residual_antialiased(x, previous_x) {{
\tstep = x - previous_x;
\tif (abs(step) > {ILL_CONDITIONED_STEP!r}) {{
\t\treturn (tanh_residual_antiderivative(x) - tanh_residual_antiderivative(previous_x)) / step;
\t}}
\tmidpoint = 0.5 * (x + previous_x);
\treturn tanh(midpoint) - midpoint;
}}""",
}


class AntiderivativeTanhSaturator(GenBlock):
    """`<name>_out` = tanh of `input`, half a sample late, antialiased. State: the last input and the allpass's.

    With `bias` (a GenExpr expression), `<name>_out` = tanh(input + bias) - tanh(bias): the curve slid along itself,
    asymmetric (even harmonics: a tube-ish clip), still 0 at 0 and slope sech^2(bias) there. The residual is
    antialiased at input + bias; the linear part is the input's, through the same allpass."""

    LATENCY_SAMPLES = 0.5

    def __init__(self, instance_name, input, bias=None):
        inputs = dict(input=input) if bias is None else dict(input=input, bias=bias)
        super().__init__(instance_name, **inputs)
        self.biased = bias is not None

    def functions(self):
        return dict(FUNCTIONS)

    def declarations(self):
        if self.biased:
            return self.substituted("History ${p}_previous_input(0), ${p}_previous_linear(0), ${p}_previous_shifted(0);")
        return self.substituted("History ${p}_previous_input(0), ${p}_previous_linear(0);")

    def statements(self):
        if self.biased:
            return self.substituted("""// ${p}: tanh(x + bias) - tanh(bias), antialiased (kit saturator block)
${p}_input = ${input};
${p}_bias = ${bias};
${p}_shifted = ${p}_input + ${p}_bias;
${p}_linear = ${a} * ${p}_input + ${p}_previous_input - ${a} * ${p}_previous_linear;
${p}_out = ${p}_linear + tanh_residual_antialiased(${p}_shifted, ${p}_previous_shifted) + ${p}_bias - tanh(${p}_bias);
${p}_previous_input = ${p}_input;
${p}_previous_linear = ${p}_linear;
${p}_previous_shifted = ${p}_shifted;""", a=HALF_SAMPLE_ALLPASS_COEFFICIENT)
        return self.substituted("""// ${p}: tanh, antialiased (kit saturator block)
${p}_input = ${input};
${p}_linear = ${a} * ${p}_input + ${p}_previous_input - ${a} * ${p}_previous_linear;
${p}_out = ${p}_linear + tanh_residual_antialiased(${p}_input, ${p}_previous_input);
${p}_previous_input = ${p}_input;
${p}_previous_linear = ${p}_linear;""", a=HALF_SAMPLE_ALLPASS_COEFFICIENT)

    def reset_statements(self):
        """Statements that forget the state (for a loop being emptied)."""
        if self.biased:
            return self.substituted("${p}_previous_input = 0;\n${p}_previous_linear = 0;\n${p}_previous_shifted = 0;")
        return self.substituted("${p}_previous_input = 0;\n${p}_previous_linear = 0;")

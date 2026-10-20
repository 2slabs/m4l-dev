"""The antiderivative tanh saturator (a technique): tanh with first-order antiderivative antialiasing (ADAA), equalised
(references/dsp.md, "Antiderivative tanh saturator").

The mean of tanh over the step from the last input to this one (Bilbao et al. 2017, eq. 5):

    m[n] = (F1(x[n]) - F1(x[n-1])) / (x[n] - x[n-1]),   F1(x) = log cosh x

(and, where the two inputs are too close for that quotient, tanh at their midpoint: the paper's ill-conditioning
fallback). Being a mean of tanh it never leaves (-1, 1). It is half a sample late, and on small signals it is the
2-tap mean (1 + z^-1) / 2, cos(w / 2): -2.4 dB at 10 kHz, -6.4 dB at 15 kHz at 44.1 kHz. Bilbao et al. §IV's remedy
is "additional linear filtering" (Valimaki, Pekonen & Nam 2012, eq. 16: a linear-phase FIR after it), so the output is
m through `EQUALISER_TAPS`, a symmetric 5-tap FIR (ours: equiripple, Remez, as the piecewise-linear shaper's) whose
product with cos(w / 2) is 1 at DC and within +-0.01 dB up to EQUALISER_EDGE (5/24 of the rate: 9.2 kHz at 44.1 kHz,
20 kHz at 96 kHz), falling to 0 at Nyquist (-1.6 dB at 15 kHz at 44.1 kHz). LATENCY_SAMPLES (2.5) late in all.

Not the split it replaces (tanh x = x through a half-sample allpass + ADAA of tanh x - x, research 2026-10-19): at a
hot drive the residual is mostly -x, filtered by the 2-tap mean while the x path is not, so the two no longer cancel
and the output is off by about |allpass - mean| x the drive (48 kHz, 10 kHz, drive 10: a fundamental 1.6 x too big,
peaks 3.2; drive 20 at 15 kHz: peaks 10.9). Here every signal goes through the same mean and the same equaliser.

Measured (tests/test_techniques.py keeps the claims): a 2.7 x 8 kHz sine at 44.1 kHz, its worst alias below 10 kHz
-23 dB naive, -54.3 dB here (biased by 0.3: -48.1); hot (drives 3-20 at 5-15 kHz, 44.1-96 kHz) the fundamental
within 0.40 of the band-limited tanh's (1.27 at a hot drive), alike at every drive, and peaks under 1.7.
"""
from m4l_dev.gen_blocks import Technique

# Below this input step the quotient loses digits (F1's rounding over the step, about |x| 2e-16 / step); above it the
# midpoint is off by about tanh''' * step^2 / 24. 1e-5 keeps both near 1e-9 for |x| < 50.
ILL_CONDITIONED_STEP = 1e-5
# The equaliser (the module docstring): symmetric taps, designed (Remez on three extrema; tests/test_techniques.py
# designs it again) so that it times the 2-tap mean's cos(w / 2) is 1 at DC and within +-0.00114 (0.0099 dB) up to
# the edge
EQUALISER_EDGE = 5 / 24                    # cycles a sample: the piecewise-linear shaper's second-order edge
EQUALISER_OUTER_TAP = 0.039075017735941485
EQUALISER_INNER_TAP = -0.27311963220261654
EQUALISER_TAPS = (EQUALISER_OUTER_TAP, EQUALISER_INNER_TAP, 1 - 2 * EQUALISER_OUTER_TAP - 2 * EQUALISER_INNER_TAP,
                  EQUALISER_INNER_TAP, EQUALISER_OUTER_TAP)
# the mean is half a sample late (centred between its two inputs), the equaliser two more (centred on its middle tap)
LATENCY_SAMPLES = 0.5 + (len(EQUALISER_TAPS) - 1) // 2

FUNCTIONS = {
    "tanh_antiderivative": """// log cosh x, the antiderivative of tanh x, without overflow (log cosh x = |x| + log(1 + e^-2|x|) - log 2)
tanh_antiderivative(x) {
\tmagnitude = abs(x);
\treturn magnitude + log(1 + exp(-2 * magnitude)) - 0.6931471805599453;
}""",
    "tanh_antialiased": f"""// tanh averaged over the step from the last input to this one (first-order ADAA)
tanh_antialiased(x, previous_x) {{
\tstep = x - previous_x;
\tif (abs(step) > {ILL_CONDITIONED_STEP!r}) {{
\t\treturn (tanh_antiderivative(x) - tanh_antiderivative(previous_x)) / step;
\t}}
\treturn tanh(0.5 * (x + previous_x));
}}""",
    "tanh_antialiased_equaliser": """// the equaliser over the last five means, m0 newest (kit technique: antiderivative tanh saturator)
tanh_antialiased_equaliser(m0, m1, m2, m3, m4) {
\treturn %(outer)r * (m0 + m4) + %(inner)r * (m1 + m3) + %(middle)r * m2;
}""" % {"outer": EQUALISER_TAPS[0], "inner": EQUALISER_TAPS[1], "middle": EQUALISER_TAPS[2]},
}
MEANS_KEPT = len(EQUALISER_TAPS) - 1       # the means before this one the equaliser reads


class AntiderivativeTanhSaturator(Technique):
    """`<name>_out` = tanh of `input`, LATENCY_SAMPLES late, antialiased and equalised. State: the last input and the
    last four means.

    With `bias` (a GenExpr expression), `<name>_out` = tanh(input + bias) - tanh(bias): the curve slid along itself,
    asymmetric (even harmonics: a tube-ish clip), still 0 at 0 and slope sech^2(bias) there. The mean is taken at
    input + bias."""

    LATENCY_SAMPLES = LATENCY_SAMPLES

    def __init__(self, instance_name, input, bias=None):
        inputs = dict(input=input) if bias is None else dict(input=input, bias=bias)
        super().__init__(instance_name, **inputs)
        self.biased = bias is not None

    def _mean_names(self):
        return [f"{self.instance_name}_mean_before_{age}" for age in range(1, MEANS_KEPT + 1)]

    def functions(self):
        return dict(FUNCTIONS)

    def declarations(self):
        state = [f"{self.instance_name}_previous_shaped_input(0)"] + [f"{name}(0)" for name in self._mean_names()]
        return f"History {', '.join(state)};"

    def statements(self):
        means = self._mean_names()
        shift = "".join(f"\n{newer_name} = {older_name};" for newer_name, older_name in
                        reversed(list(zip(means[1:], means[:-1]))))
        if self.biased:
            head = """// ${p}: tanh(x + bias) - tanh(bias), antialiased, equalised (kit technique: antiderivative tanh saturator)
${p}_bias = ${bias};
${p}_shaped_input = ${input} + ${p}_bias;"""
            offset = " - tanh(${p}_bias)"
        else:
            head = """// ${p}: tanh, antialiased, equalised (kit technique: antiderivative tanh saturator)
${p}_shaped_input = ${input};"""
            offset = ""
        return self.substituted(head + f"""
${{p}}_mean = tanh_antialiased(${{p}}_shaped_input, ${{p}}_previous_shaped_input);
${{p}}_out = tanh_antialiased_equaliser(${{p}}_mean, {", ".join(means)}){offset};{shift}
{means[0]} = ${{p}}_mean;
${{p}}_previous_shaped_input = ${{p}}_shaped_input;""")

    def reset_statements(self):
        """Statements that forget the state (for a loop being emptied)."""
        return "\n".join(f"{name} = 0;" for name in [f"{self.instance_name}_previous_shaped_input"] + self._mean_names())

"""The antiderivative tanh saturator (a technique): tanh with first-order antiderivative antialiasing (ADAA), run at
the host rate or at twice it (references/dsp.md, "Antiderivative tanh saturator").

The mean of tanh over the step from the last input to this one (Bilbao et al. 2017, eq. 5):

    m[n] = (F1(x[n]) - F1(x[n-1])) / (x[n] - x[n-1]),   F1(x) = log cosh x

(and, where the two inputs are too close for that quotient, tanh at their midpoint: the paper's ill-conditioning
fallback). Being a mean of tanh it never leaves (-1, 1). On small signals it is the 2-tap mean, cos(w / 2), half a
step late; after it, ADAA's equaliser for first order at the rate it runs at (the kit's one ADAA equaliser,
`AntiderivativeAntialiasingEqualiser`, order 1). `oversampling` (required, 1 or 2):

- 1: the mean at the host rate, no equaliser (the table's decision: at 1x the 5/24 equaliser lifted the worst alias
  in 44 of 49 cases, up to +6.2 dB, and lowered it in 1, tests/test_techniques.py). Half a sample late; the 2-tap
  mean's roll-off kept: -2.4 dB at 10 kHz, -6.4 dB at 15 kHz, -10.9 dB at 18 kHz at 44.1 kHz (-2.0, -5.1, -8.3 dB at
  48 kHz). For a per-voice or in-loop saturator where the CPU counts.
- 2: the input through the kit's `HalfbandUpsampler`, the mean and its 2x equaliser (5 taps, the product with
  cos(w / 2) within +-0.01 dB up to 5/24 of the 2x rate: 18.4 kHz at 44.1 kHz, 20 kHz at 48 kHz) on each of the two
  steps, the `HalfbandDownsampler` after: within 0.01 dB to 20 kHz at 48 kHz (0.05 dB at 44.1 kHz), what the 2x mean
  leaves above the half-band's stop band (0.29 of the 2x rate) removed. 1.25 samples late inside (2.5 steps) plus
  the half-band pair's 3.07, not linear phase (the pair's group delay rises toward its corner). For a whole-track
  drive. About 2.2-2.7x the 1x CPU (references/dsp.md).

`latency_samples` is the instance's delay at low frequencies. Measured (tests/test_techniques.py keeps the claims).

Not the split it once was (tanh x = x through a half-sample allpass + ADAA of tanh x - x): at a hot drive the residual
is mostly -x, filtered by the 2-tap mean while the x path is not, so the two no longer cancel (48 kHz, 10 kHz, drive
10: a fundamental 1.6 x too big, peaks 3.2). Here every signal goes through the same mean.
"""
import cmath
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.techniques.antiderivative_antialiasing_equaliser import AntiderivativeAntialiasingEqualiser
from m4l_dev.techniques.halfband_oversampler import (HALFBAND_ROUND_TRIP_LATENCY_SAMPLES, HalfbandDownsampler,
                                                     HalfbandUpsampler, halfband_coefficients, halfband_response)

# Below this input step the quotient loses digits (F1's rounding over the step, about |x| 2e-16 / step); above it the
# midpoint is off by about tanh''' * step^2 / 24. 1e-5 keeps both near 1e-9 for |x| < 50.
ILL_CONDITIONED_STEP = 1e-5

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
}


class AntiderivativeTanhSaturator(Technique):
    """`<name>_out` = tanh of `input`, antialiased, at `oversampling` (1 or 2, required) x the host rate,
    `latency_samples` late. State: the last input, the equaliser's last means, at 2x the half-band pair's.

    With `bias` (a GenExpr expression), `<name>_out` = tanh(input + bias) - tanh(bias): the curve slid along itself,
    asymmetric (even harmonics: a tube-ish clip), still 0 at 0 and slope sech^2(bias) there. The mean is taken
    along input + bias, the bias held over the step."""

    def __init__(self, instance_name, *, input, oversampling, bias=None):
        inputs = dict(input=input) if bias is None else dict(input=input, bias=bias)
        super().__init__(instance_name, **inputs)
        who = f"AntiderivativeTanhSaturator {instance_name}"
        if isinstance(oversampling, bool) or oversampling not in (1, 2):
            raise BuildError(f"{who}: oversampling is 1 (the host rate) or 2 (inside the kit's half-band pair), got "
                             f"{oversampling!r}")
        self.biased = bias is not None
        self.oversampling = oversampling
        self.equaliser = AntiderivativeAntialiasingEqualiser(f"{instance_name}_equaliser", raw_mean=f"{instance_name}_mean",
                                                             order=1, oversampling=oversampling, who=who)
        self.upsampler = self.downsampler = None
        if oversampling == 2:
            self.upsampler = HalfbandUpsampler(f"{instance_name}_up", input=f"{instance_name}_input")
            self.downsampler = HalfbandDownsampler(f"{instance_name}_down", first=f"{instance_name}_step_1_out",
                                                   second=f"{instance_name}_step_2_out")
        # at low frequencies: the mean and the equaliser in steps, plus the half-band pair's phase delay at 2x
        self.latency_samples = self.equaliser.latency_steps / oversampling + (
            HALFBAND_ROUND_TRIP_LATENCY_SAMPLES if oversampling == 2 else 0)

    def small_signal_response(self, frequency_hz, sample_rate):
        """The instance's complex response to a quiet signal (tanh's slope 1, no bias), input to output: the 2-tap
        mean and the equaliser at the rate it runs at, `equaliser.latency_steps` late; at 2x between the half-band
        pair, which measures as the half-band squared one doubled-rate step early (MoogTransistorLadder's twin)."""
        w = 2 * math.pi * frequency_hz / (sample_rate * self.oversampling)
        late = cmath.exp(-1j * w * self.equaliser.latency_steps)
        response = self.equaliser.small_signal_response(w) * late
        if self.oversampling == 2:
            response *= halfband_response(frequency_hz / (2 * sample_rate), halfband_coefficients()) ** 2 * cmath.exp(1j * w)
        return response

    def functions(self):
        functions = dict(FUNCTIONS)
        functions.update(self.equaliser.functions())
        return functions

    def declarations(self):
        declarations = [f"History {self.instance_name}_previous_input(0);", self.equaliser.declarations()]
        if self.oversampling == 2:
            declarations += [self.upsampler.declarations(), self.downsampler.declarations()]
        return "\n".join(declaration for declaration in declarations if declaration)

    def _step_statements(self, step_input, step_output):
        """One step at the rate it runs at: the mean from the last step's input to `step_input`, both slid by this
        step's bias (taken as held over the step), less tanh(bias), then the equaliser, leaving `step_output`. Every
        kept value is 0 for silence, so silence is 0 from the first step, before and after the half-band pair."""
        p = self.instance_name
        if self.biased:
            mean = (f"tanh_antialiased({step_input} + {p}_bias, {p}_previous_input + {p}_bias) - tanh({p}_bias)")
        else:
            mean = f"tanh_antialiased({step_input}, {p}_previous_input)"
        return (f"{p}_mean = {mean};\n{self.equaliser.statements()}\n"
                f"{step_output} = {p}_equaliser_out;\n{p}_previous_input = {step_input};")

    def statements(self):
        p = self.instance_name
        what = "tanh(x + bias) - tanh(bias)" if self.biased else "tanh"
        lines = [f"// {p}: {what}, first-order ADAA at {self.oversampling}x (kit technique: antiderivative tanh "
                 f"saturator)",
                 self.substituted("${p}_input = ${input};")]
        if self.biased:
            lines.append(self.substituted("${p}_bias = ${bias};"))
        if self.oversampling == 1:
            lines += [self._step_statements(f"{p}_input", f"{p}_out")]
        else:
            lines += [self.upsampler.statements(),
                      self._step_statements(f"{p}_up_first", f"{p}_step_1_out"),
                      self._step_statements(f"{p}_up_second", f"{p}_step_2_out"),
                      self.downsampler.statements(),
                      f"{p}_out = {p}_down_out;"]
        return "\n".join(lines)

    def reset_statements(self):
        """Statements that forget the state (for a loop being emptied)."""
        lines = [f"{self.instance_name}_previous_input = 0;", self.equaliser.reset_statements()]
        if self.oversampling == 2:
            lines += [self.upsampler.reset_statements(), self.downsampler.reset_statements()]
        return "\n".join(line for line in lines if line)

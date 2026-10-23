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
- 2: the input through the kit's `HalfbandUpsampler` (elliptic), the mean and its 2x equaliser (5 taps, the product
  with cos(w / 2) within +-0.01 dB up to 5/24 of the 2x rate: 18.4 kHz at 44.1 kHz, 20 kHz at 48 kHz) on each of the
  two steps, the kit's `HalfbandLinearPhaseDownsampler` after (Kaiser, 83 taps, 100 dB from 0.29 of the 2x rate):
  within 0.01 dB to 20 kHz at 48 kHz, to 18 kHz at 44.1 kHz (-0.27 dB at 20 kHz, the FIR's pass band ending at
  18.5 kHz there). 1.25 samples late inside (2.5 steps), the upsampler's 1.78 and the downsampler's 20: 23.03 in all
  at 100 Hz, not linear phase (the upsampler's group delay rises toward its corner). For a whole-track drive. About
  3.7x the 1x CPU (references/dsp.md).

  Why the downsampler is linear phase: a mean of tanh never leaves (-1, 1), but band-limiting a clipped broadband wave
  overshoots (hot white noise through tanh at 16x, low-passed at 20 kHz: 1.78), and the elliptic downsampler's phase
  near its corner rang it to 2.85 (2sl drums' snare at +36 dB: 2.11; references/dsp.md, "Peaks"). With
  the FIR: 1.91 and 1.50. `output_bound_per_unit_mean` is the bound for any input: the sum of |taps| of the chain
  after the mean (2.19 at 2x, 1 at 1x) times the mean's own bound (1, or 1 + |tanh(bias)| with a bias).

`latency_samples` is the instance's delay at low frequencies: its blocks' summed, = its small-signal response's
phase delay at 100 Hz.
Measured (tests/test_techniques.py keeps the claims).

Not the split it once was (tanh x = x through a half-sample allpass + ADAA of tanh x - x): at a hot drive the residual
is mostly -x, filtered by the 2-tap mean while the x path is not, so the two no longer cancel (48 kHz, 10 kHz, drive
10: a fundamental 1.6 x too big, peaks 3.2). Here every signal goes through the same mean.
"""
import cmath
import math

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique
from twosl_dsp.generated_numbers import generated_number
from twosl_dsp.techniques.histories_start_at_their_targets import HistoriesStartAtTheirTargets
from twosl_dsp.techniques.antiderivative_antialiasing_equaliser import AntiderivativeAntialiasingEqualiser
from twosl_dsp.techniques.halfband_oversampler import (ControlsAtTheUpsampledSteps, HalfbandLinearPhaseDownsampler,
                                                     HalfbandUpsampler,
                                                     halfband_coefficients, halfband_response)

# Below this input step the quotient loses digits (F1's rounding over the step, about |x| 2e-16 / step); above it the
# midpoint is off by about tanh''' * step^2 / 24. 1e-5 keeps both near 1e-9 for |x| < 50.
ILL_CONDITIONED_STEP = 1e-5

FUNCTIONS = {
    "tanh_antiderivative": f"""// log cosh x, the antiderivative of tanh x, without overflow (log cosh x = |x| + log(1 + e^-2|x|) - log 2)
tanh_antiderivative(x) {{
\tmagnitude = abs(x);
\treturn magnitude + log(1 + exp(-2 * magnitude)) - {generated_number(math.log(2))!r};
}}""",
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
    `latency_samples` late, never above `output_bound_per_unit_mean` (x 1 + |tanh(bias)| with a bias). State: the last
    input, the equaliser's last means, at 2x the upsampler's and the downsampler's.

    With `bias` (a GenExpr expression), `<name>_out` = tanh(input + bias) - tanh(bias): the curve slid along itself,
    asymmetric (even harmonics: a tube-ish clip), still 0 at 0 and slope sech^2(bias) there. The mean is taken
    along input + bias, the bias held over the step at its own mean over the step (the mean of its value at this step
    and the last: the input's mean is half a step late, so is the bias). At 2x the bias reaches each step through
    `ControlsAtTheUpsampledSteps` (the upsampler's latency, step 2 half a sample less), so it meets the audio it was
    sent with: tests/test_oversampled_section_latency.py (read as it was now, held, it led the audio by 1.78 samples
    at 2x, 0.5 at 1x)."""

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
        self.upsampler = self.downsampler = self.controls_at_the_steps = self.bias_starts = None
        if oversampling == 2:
            self.upsampler = HalfbandUpsampler(f"{instance_name}_up", input=f"{instance_name}_input")
            if self.biased:
                self.controls_at_the_steps = ControlsAtTheUpsampledSteps(
                    f"{instance_name}_controls", upsampler=self.upsampler, controls={"bias": f"{instance_name}_bias"})
            self.downsampler = HalfbandLinearPhaseDownsampler(f"{instance_name}_down",
                                                              first=f"{instance_name}_step_1_out",
                                                              second=f"{instance_name}_step_2_out")
        if self.biased:
            # the last step's bias starts at the first step's (nothing slides on the first sample)
            self.bias_starts = HistoriesStartAtTheirTargets(f"{instance_name}_bias_starts", targets={
                f"{instance_name}_previous_bias": self._step_biases()[0]})
        self.output_bound_per_unit_mean = self._output_bound_per_unit_mean()
        # its blocks' summed: at 1x the mean's half step (exactly 0.5), at 2x the mean and the equaliser (1.25), the
        # elliptic upsampler's phase delay at 100 Hz (1.78) and the linear-phase downsampler's K - 1 (20); = the
        # phase delay of its own small-signal response at 100 Hz (tested)
        self.latency_samples = self.equaliser.latency_samples + (
            0 if oversampling == 1 else self.upsampler.latency_samples + self.downsampler.latency_samples)

    def _output_bound_per_unit_mean(self):
        """The sum of |taps| of the linear chain after the mean (the equaliser, at 2x convolved with the downsampler's
        FIR): no output is larger than this times the largest |mean|. A mean of tanh is under 1, of the slid curve
        under 1 + |tanh(bias)|."""
        chain = list(self.equaliser.taps)
        if self.oversampling == 2:
            fir = self.downsampler.taps
            chain = [sum(chain[i] * fir[n - i] for i in range(len(chain)) if 0 <= n - i < len(fir))
                     for n in range(len(chain) + len(fir) - 1)]
        return sum(abs(tap) for tap in chain)

    def small_signal_response(self, frequency_hz, sample_rate):
        """The instance's complex response to a quiet signal (tanh's slope 1, no bias), input to output: the 2-tap
        mean and the equaliser at the rate it runs at, `equaliser.latency_steps` late; at 2x after the elliptic
        upsampler (the half-band's response, re the first sample's time) and before the linear-phase downsampler."""
        w = 2 * math.pi * frequency_hz / (sample_rate * self.oversampling)
        late = cmath.exp(-1j * w * self.equaliser.latency_steps)
        response = self.equaliser.small_signal_response(w) * late
        if self.oversampling == 2:
            frequency_over_doubled_rate = frequency_hz / (2 * sample_rate)
            response *= halfband_response(frequency_over_doubled_rate, halfband_coefficients()) \
                * self.downsampler.response(frequency_over_doubled_rate)
        return response

    def functions(self):
        functions = dict(FUNCTIONS)
        functions.update(self.equaliser.functions())
        return functions

    def declarations(self):
        declarations = [f"History {self.instance_name}_previous_input(0);", self.equaliser.declarations()]
        if self.oversampling == 2:
            declarations += [self.upsampler.declarations(), self.downsampler.declarations()]
            if self.controls_at_the_steps is not None:
                declarations.append(self.controls_at_the_steps.declarations())
        if self.biased:
            declarations += [f"History {self.instance_name}_previous_bias(0);", self.bias_starts.declarations()]
        return "\n".join(declaration for declaration in declarations if declaration)

    def _mean_expression(self, step_input, step_bias):
        """GenExpr: the transfer's first-order ADAA over the step from the last input to `step_input`, slid by
        `step_bias` (the bias at this step) when biased."""
        p = self.instance_name
        if self.biased:
            return f"tanh_antialiased({step_input} + {step_bias}, {p}_previous_input + {step_bias}) - tanh({step_bias})"
        return f"tanh_antialiased({step_input}, {p}_previous_input)"

    def _transfer_description(self):
        return "tanh(x + bias) - tanh(bias)" if self.biased else "tanh"

    def _step_biases(self):
        """GenExpr: the bias as each step reads it (1x: now; 2x: through ControlsAtTheUpsampledSteps)."""
        p = self.instance_name
        if self.oversampling == 1:
            return (f"{p}_bias",)
        return (f"{p}_controls_bias_step_1", f"{p}_controls_bias_step_2")

    def _step_statements(self, step_input, step_output, step_bias):
        """One step at the rate it runs at: the mean from the last step's input to `step_input`, both slid by this
        step's bias (taken as held over the step), less tanh(bias), then the equaliser, leaving `step_output`. Every
        kept value is 0 for silence, so silence is 0 from the first step, before and after the half-band pair."""
        p = self.instance_name
        lines = []
        if self.biased:
            lines += [f"{p}_step_bias = 0.5 * ({step_bias} + {p}_previous_bias);", f"{p}_previous_bias = {step_bias};"]
        lines += [f"{p}_mean = {self._mean_expression(step_input, f'{p}_step_bias')};", self.equaliser.statements(),
                  f"{step_output} = {p}_equaliser_out;", f"{p}_previous_input = {step_input};"]
        return "\n".join(lines)

    def statements(self):
        p = self.instance_name
        lines = [f"// {p}: {self._transfer_description()}, first-order ADAA at {self.oversampling}x (kit technique: antiderivative tanh "
                 f"saturator)",
                 self.substituted("${p}_input = ${input};")]
        if self.biased:
            lines.append(self.substituted("${p}_bias = ${bias};"))
        step_biases = self._step_biases()
        if self.oversampling == 1:
            if self.biased:
                lines.append(self.bias_starts.statements())
            lines += [self._step_statements(f"{p}_input", f"{p}_out", step_biases[0])]
        else:
            lines.append(self.upsampler.statements())
            if self.controls_at_the_steps is not None:
                lines += [self.controls_at_the_steps.statements(), self.bias_starts.statements()]
            lines += [self._step_statements(f"{p}_up_first", f"{p}_step_1_out", step_biases[0]),
                      self._step_statements(f"{p}_up_second", f"{p}_step_2_out", step_biases[1]),
                      self.downsampler.statements(),
                      f"{p}_out = {p}_down_out;"]
        return "\n".join(lines)

    def reset_statements(self):
        """Statements that forget the state (for a loop being emptied)."""
        lines = [f"{self.instance_name}_previous_input = 0;", self.equaliser.reset_statements()]
        if self.oversampling == 2:
            lines += [self.upsampler.reset_statements(), self.downsampler.reset_statements()]
        return "\n".join(line for line in lines if line)


class AntiderivativeTanhSaturatorLinearTwin(AntiderivativeTanhSaturator):
    """`<name>_out` = `input` through the saturator's linear path at `oversampling`: the same upsampler, mean,
    equaliser and downsampler, with the straight line x in place of tanh (whose first-order ADAA is the 2-tap mean,
    exactly). Its response is the saturator's `small_signal_response` at every frequency (the saturator's slope at 0
    taken out), so it lines up what an instrument mixes against a saturated signal: a dry path at a dry / wet mix.

    Why not a delay: at 2x the elliptic upsampler is not linear phase, so no integer-plus-fractional delay follows it.
    Measured 2026-10-20 (the saturator at 2x against the dry at a 50 % mix, 44.1 kHz): 22 samples and a first-order
    Thiran all-pass for the remaining 1.03 (Smith, "Thiran Allpass Interpolators") leaves -0.07 dB at 10 kHz and
    -15.1 dB at 20 kHz; the twin leaves none (tests/test_techniques.py). At 1x it is the 2-tap mean, half a sample
    late."""

    def __init__(self, instance_name, *, input, oversampling):
        super().__init__(instance_name, input=input, oversampling=oversampling)

    def _mean_expression(self, step_input, step_bias):
        return f"0.5 * ({step_input} + {self.instance_name}_previous_input)"

    def _transfer_description(self):
        return "the linear twin (x)"

    def functions(self):
        return self.equaliser.functions()

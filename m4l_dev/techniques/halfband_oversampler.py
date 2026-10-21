"""The halfband oversampler (a technique): a 2x upsampler and a 2x downsampler, each a two-path polyphase IIR
half-band low-pass, for running a section (an FM or ring-mod oscillator pair) at twice the sample rate
(references/dsp.md, "Halfband oversampler").

The filter is Laurent de Soras's HIIR (version 1.40, WTFPL): a symmetric half-band elliptic low-pass made of two
paths of first-order all-passes in z^2 (Valenzuela & Constantinides' structure, which HIIR implements), H(z) =
(A0(z^2) + z^-1 A1(z^2)) / 2. `halfband_coefficients` is HIIR's PolyphaseIir2Designer::compute_coefs_spec_order_tbw,
ported line for line (compute_transition_param, compute_coef, compute_acc_num, compute_acc_den); the coefficients
alternate between the paths (0, 2, 4 ... the first; 1, 3, 5 ... the second). Each stage, run at the base rate, is
StageProcTpl's y = a (x - y_before) + x_before.
- Upsampler (Upsampler2xTpl::process_sample): from one input sample, `<name>_first` = path 0 and `<name>_second` =
  path 1 of it, the two samples at twice the rate.
- Downsampler (Downsampler2xTpl::process_sample): from the two samples of a base-rate sample, path 0 takes the
  second, path 1 the first, `<name>_out` = their mean.

The kit's design (DEFAULT_*): 8 coefficients, transition 0.04 of the doubled rate (HIIR readme's own example): pass band to 0.21 x 2 sr (18.5 kHz
at 44.1 kHz), stop band from 0.29 x 2 sr (25.6 kHz, so everything that would fold below 18.5 kHz), attenuation
`halfband_attenuation_db` (HIIR's compute_atten): 99.3 dB. Latency (`latency_samples`, base-rate samples, from the
half-band's phase delay tau at LATENCY_FREQUENCY_HZ, in doubled-rate samples): the upsampler tau / 2 (its `first` at
the host sample's time, `second` half a sample after), the downsampler tau / 2 - 1/2 (it takes the half-band's output
at the second sample); up then down 3.07 samples at the kit's design (rendered: tests/test_techniques.py). Not linear
phase (HIIR's readme: the delays are "quite flat ... from DC up to about Fs/20" and rise toward the cut-off).

The linear-phase downsampler (`HalfbandLinearPhaseDownsampler`, `linear_phase_halfband_taps`): the same band edges
and at least the elliptic's depth (100 dB) as a Kaiser-windowed half-band FIR, 83 taps (21 multiplies a base-rate
sample), 20 samples late at every frequency. For after a saturator: band-limiting a clipped broadband wave overshoots
(the ideal, tanh at 16x low-passed at 20 kHz, peaks 1.78 on hot white noise), and the elliptic's phase near its corner
rings it far past that (2.85 through the tanh saturator at 2x; the FIR 1.91). Its pass band is flat to its edge, not
past it (-0.22 dB at 20 kHz at 44.1 kHz, where the elliptic is still flat to 1e-9 dB).

How a section runs at 2x: its statements run twice a sample (its marker placed twice, or its point code evaluated
at two points, architecture/dsp-blocks.md "Points"), once on `<name>_first`, once on `<name>_second` of an
upsampler (or on its own 2x-rate oscillators), and the downsampler takes the two results. Its controls (a cutoff, a
feedback gain, a bias) go through `ControlsAtTheUpsampledSteps`, which delays each to the time of the audio in each
step (the upsampler's latency, read from it), so they meet the audio they belong to.
"""
import cmath
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.techniques.histories_start_at_their_targets import HistoriesStartAtTheirTargets

DEFAULT_COEFFICIENT_COUNT = 8
DEFAULT_TRANSITION = 0.04


def _transition_parameters(transition):
    """HIIR compute_transition_param: k and q of the elliptic design."""
    k = math.tan((1 - transition * 2) * math.pi / 4)
    k *= k
    kksqrt = (1 - k * k) ** 0.25
    e = 0.5 * (1 - kksqrt) / (1 + kksqrt)
    e2 = e * e
    e4 = e2 * e2
    return k, e * (1 + e4 * (2 + e4 * (15 + 150 * e4)))


def _accumulated_numerator(q, order, c):
    """HIIR compute_acc_num."""
    i, j, accumulated = 0, 1, 0.0
    while True:
        term = q ** (i * (i + 1)) * math.sin((i * 2 + 1) * c * math.pi / order) * j
        accumulated += term
        j, i = -j, i + 1
        if abs(term) <= 1e-100:
            return accumulated


def _accumulated_denominator(q, order, c):
    """HIIR compute_acc_den."""
    i, j, accumulated = 1, -1, 0.0
    while True:
        term = q ** (i * i) * math.cos(i * 2 * c * math.pi / order) * j
        accumulated += term
        j, i = -j, i + 1
        if abs(term) <= 1e-100:
            return accumulated


def halfband_coefficients(coefficient_count=DEFAULT_COEFFICIENT_COUNT, transition=DEFAULT_TRANSITION):
    """HIIR compute_coefs_spec_order_tbw: the all-pass coefficients for `coefficient_count` stages and a transition
    band `transition` (a fraction of the doubled rate, in (0, 0.5))."""
    if not isinstance(coefficient_count, int) or coefficient_count < 1:
        raise BuildError(f"halfband_coefficients: coefficient_count must be a whole number >= 1, got {coefficient_count!r}")
    if not 0 < transition < 0.5:
        raise BuildError(f"halfband_coefficients: transition must be in (0, 0.5), got {transition!r}")
    k, q = _transition_parameters(transition)
    order = coefficient_count * 2 + 1
    coefficients = []
    for index in range(coefficient_count):
        c = index + 1
        numerator = _accumulated_numerator(q, order, c) * q ** 0.25
        denominator = _accumulated_denominator(q, order, c) + 0.5
        ww = numerator / denominator
        wwsq = ww * ww
        x = math.sqrt((1 - wwsq * k) * (1 - wwsq / k)) / (1 + wwsq)
        coefficients.append((1 - x) / (1 + x))
    return tuple(coefficients)


def halfband_attenuation_db(coefficient_count=DEFAULT_COEFFICIENT_COUNT, transition=DEFAULT_TRANSITION):
    """HIIR compute_atten: the stop band's attenuation in dB."""
    _, q = _transition_parameters(transition)
    order = coefficient_count * 2 + 1
    a = 4 * math.exp(order * 0.5 * math.log(q))
    return -10 * math.log10(a / (1 + a))


def halfband_response(frequency_over_doubled_rate, coefficients):
    """The half-band low-pass's complex response at a frequency (a fraction of the doubled rate):
    (A0(z^2) + z^-1 A1(z^2)) / 2, A(z) = prod (a + z^-1) / (1 + a z^-1) per path."""
    z = complex(math.cos(2 * math.pi * frequency_over_doubled_rate), math.sin(2 * math.pi * frequency_over_doubled_rate))
    z2_inverse = 1 / (z * z)
    paths = [1 + 0j, 1 + 0j]
    for index, a in enumerate(coefficients):
        paths[index % 2] *= (a + z2_inverse) / (1 + a * z2_inverse)
    return (paths[0] + paths[1] / z) / 2


# The frequency a block's latency is the phase delay at (low enough that the elliptic half-band's delay is flat there),
# at the rate it is quoted for: the kit's latencies of non-linear-phase blocks (this oversampler, the tanh saturator)
LATENCY_FREQUENCY_HZ = 100.0
LATENCY_SAMPLE_RATE = 44100.0


def halfband_phase_delay_doubled_rate_samples(coefficients):
    """tau: the half-band low-pass's phase delay at LATENCY_FREQUENCY_HZ (the host at LATENCY_SAMPLE_RATE), in samples
    of the doubled rate."""
    frequency_over_doubled_rate = LATENCY_FREQUENCY_HZ / (2 * LATENCY_SAMPLE_RATE)
    return -cmath.phase(halfband_response(frequency_over_doubled_rate, coefficients)) / (
        2 * math.pi * frequency_over_doubled_rate)


def _check_coefficients(name, coefficients):
    if not coefficients or not all(isinstance(a, float) and 0 < a < 1 for a in coefficients):
        raise BuildError(f"{name}: coefficients must be all-pass coefficients in (0, 1), got {coefficients!r}")
    return tuple(coefficients)


def _path_statements(prefix, coefficients, path, input_expression):
    """Statements running one path's first-order all-passes (StageProcTpl), leaving `<prefix>_path_<path>`."""
    lines = [f"{prefix}_path_{path} = {input_expression};"]
    for index in range(path, len(coefficients), 2):
        stage = f"{prefix}_stage_{index}"
        lines.append(f"{stage}_out = {coefficients[index]!r} * ({prefix}_path_{path} - {stage}_out_before) + {stage}_in_before;")
        lines.append(f"{stage}_in_before = {prefix}_path_{path};")
        lines.append(f"{stage}_out_before = {stage}_out;")
        lines.append(f"{prefix}_path_{path} = {stage}_out;")
    return lines


def _stage_declarations(prefix, coefficients):
    return "History " + ", ".join(f"{prefix}_stage_{index}_in_before(0), {prefix}_stage_{index}_out_before(0)"
                                  for index in range(len(coefficients))) + ";"


def _stage_reset_statements(prefix, coefficients):
    """Every stage's state emptied (a Stop)."""
    return "\n".join(f"{prefix}_stage_{index}_in_before = 0;\n{prefix}_stage_{index}_out_before = 0;"
                     for index in range(len(coefficients)))


class HalfbandUpsampler(Technique):
    """`<name>_first`, `<name>_second`: `input` at twice the rate, the half-band's images removed. `coefficients`
    (a Python tuple, default the kit's design) is fixed when the instrument is built. State: two per stage."""

    def __init__(self, instance_name, input, coefficients=None):
        super().__init__(instance_name, input=input)
        self.coefficients = _check_coefficients(f"HalfbandUpsampler {instance_name}",
                                                halfband_coefficients() if coefficients is None else coefficients)
        self.latency_samples = halfband_phase_delay_doubled_rate_samples(self.coefficients) / 2

    def declarations(self):
        return _stage_declarations(self.instance_name, self.coefficients)

    def statements(self):
        p = self.instance_name
        lines = [f"// {p}: 2x half-band upsampler, polyphase IIR (kit technique: halfband oversampler)",
                 f"{p}_input = {self.input_expressions['input']};"]
        lines += _path_statements(p, self.coefficients, 0, f"{p}_input")
        lines += _path_statements(p, self.coefficients, 1, f"{p}_input")
        lines += [f"{p}_first = {p}_path_0;", f"{p}_second = {p}_path_1;"]
        return "\n".join(lines)

    def reset_statements(self):
        return _stage_reset_statements(self.instance_name, self.coefficients)


class HalfbandDownsampler(Technique):
    """`<name>_out`: the two samples `first`, `second` (a base-rate sample's two at twice the rate) filtered by the
    half-band and taken at the base rate. `coefficients` as the upsampler's. State: two per stage."""

    def __init__(self, instance_name, first, second, coefficients=None):
        super().__init__(instance_name, first=first, second=second)
        self.coefficients = _check_coefficients(f"HalfbandDownsampler {instance_name}",
                                                halfband_coefficients() if coefficients is None else coefficients)
        self.latency_samples = halfband_phase_delay_doubled_rate_samples(self.coefficients) / 2 - 0.5

    def declarations(self):
        return _stage_declarations(self.instance_name, self.coefficients)

    def statements(self):
        p = self.instance_name
        lines = [f"// {p}: 2x half-band downsampler, polyphase IIR (kit technique: halfband oversampler)",
                 f"{p}_first = {self.input_expressions['first']};", f"{p}_second = {self.input_expressions['second']};"]
        lines += _path_statements(p, self.coefficients, 0, f"{p}_second")
        lines += _path_statements(p, self.coefficients, 1, f"{p}_first")
        lines.append(f"{p}_out = 0.5 * ({p}_path_0 + {p}_path_1);")
        return "\n".join(lines)

    def reset_statements(self):
        return _stage_reset_statements(self.instance_name, self.coefficients)


# The linear-phase half-band (a windowed-sinc FIR, Kaiser's window): the downsampler after a saturator, where the
# elliptic half-band's phase near its corner rings a clipped broadband wave far past the band-limited ideal's peak
# (references/dsp.md, measured 2026-10-20: hot white noise through the tanh saturator at 2x, 48 kHz: the elliptic
# pair 2.85, this one 1.91, tanh at 16x low-passed at 20 kHz 1.78). Its band edges are the elliptic default's
# (pass to 0.21, stop from 0.29 of the doubled rate) and its stop band at least as deep (100 dB against 99.3 dB).
LINEAR_PHASE_HALFBAND_ATTENUATION_DB = 100.0


def _bessel_i0(x):
    """The zeroth-order modified Bessel function of the first kind, by its power series (to 1e-17 of the sum)."""
    total = term = 1.0
    k = 0
    while term > 1e-17 * total:
        k += 1
        term *= (x / (2 * k)) ** 2
        total += term
    return total


def linear_phase_halfband_taps(attenuation_db=LINEAR_PHASE_HALFBAND_ATTENUATION_DB, transition=DEFAULT_TRANSITION):
    """The half-band low-pass FIR at the doubled rate, taps by delay (4 K - 1 of them, symmetric): the ideal
    half-band 0.5 sinc(k / 2) under Kaiser's window, its length and shape from Kaiser's formulas (Oppenheim & Schafer,
    Discrete-Time Signal Processing 3rd ed., eqs. 7.62-7.63: beta = 0.1102 (A - 8.7) for A > 50, order
    M = (A - 8) / (2.285 dw), dw the transition's width 2 x `transition` of the doubled rate in radians), M raised to
    the next 4 K - 2 so the middle tap sits on a whole odd offset. Every even offset from the middle is exactly 0 (a
    half-band), the middle exactly 0.5, the odd ones scaled to sum 0.5 (DC exactly 1)."""
    if not 50 < attenuation_db < 200:
        raise BuildError(f"linear_phase_halfband_taps: attenuation_db is Kaiser's A > 50 dB (beta's formula there), "
                         f"under 200, got {attenuation_db!r}")
    if not 0 < transition < 0.25:
        raise BuildError(f"linear_phase_halfband_taps: transition must be in (0, 0.25), got {transition!r}")
    beta = 0.1102 * (attenuation_db - 8.7)
    order = (attenuation_db - 8) / (2.285 * 2 * math.pi * 2 * transition)
    pairs = math.ceil((order + 2) / 4)                 # K: order 4 K - 2
    order = 4 * pairs - 2
    middle = order // 2
    raw = []
    for n in range(order + 1):
        offset = n - middle
        window = _bessel_i0(beta * math.sqrt(1 - (offset / middle) ** 2)) / _bessel_i0(beta)
        raw.append(0.0 if offset % 2 == 0 else math.sin(math.pi * offset / 2) / (math.pi * offset) * window)
    scale = 0.5 / sum(raw)
    return tuple(0.5 if n == middle else value * scale for n, value in enumerate(raw))


def linear_phase_halfband_response(frequency_over_doubled_rate, taps):
    """The FIR's complex response at a frequency (a fraction of the doubled rate), its delay included."""
    w = 2 * math.pi * frequency_over_doubled_rate
    return sum(tap * complex(math.cos(w * n), -math.sin(w * n)) for n, tap in enumerate(taps))


class HalfbandLinearPhaseDownsampler(Technique):
    """`<name>_out`: the two samples `first`, `second` (a base-rate sample's two at twice the rate, as
    `HalfbandDownsampler` takes them) through `linear_phase_halfband_taps` and taken at the base rate, polyphase: the
    second stream through the K tap pairs, the first only through the middle tap 0.5, K - 1 samples back. Linear
    phase: `latency_samples` (K - 1) late at every frequency re `first`'s time. State: 2 K - 1 past second samples,
    K - 1 past first samples."""

    def __init__(self, instance_name, first, second, taps=None):
        super().__init__(instance_name, first=first, second=second)
        taps = linear_phase_halfband_taps() if taps is None else tuple(taps)
        length = len(taps)
        if length < 3 or length % 4 != 3 or taps != tuple(reversed(taps)) or taps[length // 2] != 0.5 \
                or any(taps[n] != 0.0 for n in range(1, length, 2) if n != length // 2) or abs(sum(taps) - 1) > 1e-15:
            raise BuildError(f"HalfbandLinearPhaseDownsampler {instance_name}: taps must be a half-band's (4 K - 1, "
                             f"symmetric, middle 0.5, every other one 0, summing to 1), got {length} taps")
        self.taps = taps
        self.pairs = (length + 1) // 4
        self.latency_samples = self.pairs - 1

    def _second_name(self, age):
        return f"{self.instance_name}_second" if age == 0 else f"{self.instance_name}_second_before_{age}"

    def _first_name(self, age):
        return f"{self.instance_name}_first" if age == 0 else f"{self.instance_name}_first_before_{age}"

    def declarations(self):
        p, k = self.instance_name, self.pairs
        names = [f"{p}_second_before_{age}(0)" for age in range(1, 2 * k)] + \
            [f"{p}_first_before_{age}(0)" for age in range(1, k)]
        return "History " + ", ".join(names) + ";"

    def statements(self):
        p, k = self.instance_name, self.pairs
        # the output is taken at the second sample: tap 2 age reads the second stream age samples back (its pair
        # 2 K - 1 - age by symmetry), the middle tap 2 K - 1 the first stream K - 1 back
        terms = [f"{self.taps[2 * age]!r} * ({self._second_name(age)} + {self._second_name(2 * k - 1 - age)})"
                 for age in range(k)]
        lines = [f"// {p}: 2x half-band downsampler, linear-phase FIR, {len(self.taps)} taps (kit technique: halfband "
                 f"oversampler)",
                 f"{p}_first = {self.input_expressions['first']};", f"{p}_second = {self.input_expressions['second']};",
                 f"{p}_out = 0.5 * {self._first_name(k - 1)} + " + " + ".join(terms) + ";"]
        lines += [f"{self._second_name(age)} = {self._second_name(age - 1)};" for age in range(2 * k - 1, 0, -1)]
        lines += [f"{self._first_name(age)} = {self._first_name(age - 1)};" for age in range(k - 1, 0, -1)]
        return "\n".join(lines)

    def reset_statements(self):
        p, k = self.instance_name, self.pairs
        return "\n".join([f"{p}_second_before_{age} = 0;" for age in range(1, 2 * k)]
                         + [f"{p}_first_before_{age} = 0;" for age in range(1, k)])

    def response(self, frequency_over_doubled_rate):
        """The base-rate output's response to a signal at the doubled rate, re `first`'s time: the FIR, taken at the
        second sample (one doubled-rate step early)."""
        w = 2 * math.pi * frequency_over_doubled_rate
        return linear_phase_halfband_response(frequency_over_doubled_rate, self.taps) * complex(math.cos(w), math.sin(w))


class ControlsAtTheUpsampledSteps(Technique):
    """`<name>_<control>_step_1`, `<name>_<control>_step_2`: each control (a host-rate GenExpr expression, `controls`
    {control: expression}) as it was when the audio now in `upsampler`'s `first` and `second` entered it, so a section
    run at 2x between the pair gets its controls (a cutoff, a feedback gain, a bias) at the same time as its audio.

    Why: the upsampler's two streams are its input `upsampler.latency_samples` late (its `first` that late, `second`
    half a sample less), while a control read as it is now is not late at all; a section that takes both leads its
    audio with its controls by that much (the Moog ladder's cutoff, 2sl stab 2.2.8: 1.78 samples at the kit's design),
    and a fast control (an envelope's attack, audio-rate modulation of a cutoff) lands on the wrong audio. The delay is
    the upsampler's own figure, read from the instance (never typed), so it follows any change of its design.

    How: step 1's value is the control `upsampler.latency_samples` back, step 2's half a sample less, each by linear
    interpolation between host samples (both delays are whole plus fractional; the delay of linear interpolation is
    its fraction at low frequencies, the frequency the upsampler's figure is quoted at, LATENCY_FREQUENCY_HZ). State:
    floor(latency) + 1 past host samples per control, started at the control's value on the first sample
    (`HistoriesStartAtTheirTargets`, so nothing sweeps when the device loads). `latency_samples` is the upsampler's:
    the step values are as late as its streams. Nothing to reset: the controls keep flowing through a Stop."""

    def __init__(self, instance_name, *, upsampler, controls):
        if not isinstance(upsampler, HalfbandUpsampler):
            raise BuildError(f"ControlsAtTheUpsampledSteps {instance_name}: upsampler is the HalfbandUpsampler whose "
                             f"steps the controls meet, got {upsampler!r}")
        if not controls:
            raise BuildError(f"ControlsAtTheUpsampledSteps {instance_name}: no controls to delay")
        super().__init__(instance_name, **controls)
        self.control_names = list(controls)
        self.latency_samples = upsampler.latency_samples
        # step 1's audio entered the upsampler latency_samples ago, step 2's half a sample later
        self.step_delays_samples = (upsampler.latency_samples, upsampler.latency_samples - 0.5)
        if self.step_delays_samples[1] < 0:
            raise BuildError(f"ControlsAtTheUpsampledSteps {instance_name}: the upsampler is "
                             f"{upsampler.latency_samples} samples late, under the half sample its second step needs "
                             "to read a control from the past")
        self.past_samples_kept = math.floor(self.step_delays_samples[0]) + 1
        self.histories_start = HistoriesStartAtTheirTargets(
            f"{instance_name}_start", targets={self._past_name(control, age): f"{instance_name}_{control}_now"
                                               for control in self.control_names
                                               for age in range(1, self.past_samples_kept + 1)})

    def _past_name(self, control, age):
        return f"{self.instance_name}_{control}_now" if age == 0 else f"{self.instance_name}_{control}_before_{age}"

    def declarations(self):
        return "History " + ", ".join(f"{self._past_name(control, age)}(0)" for control in self.control_names
                                      for age in range(1, self.past_samples_kept + 1)) + ";\n" + \
            self.histories_start.declarations()

    def statements(self):
        p = self.instance_name
        lines = [f"// {p}: the controls at the upsampler's two steps, {self.latency_samples!r} and "
                 f"{self.step_delays_samples[1]!r} samples back (kit technique: halfband oversampler)"]
        lines += [f"{p}_{control}_now = {self.input_expressions[control]};" for control in self.control_names]
        lines.append(self.histories_start.statements())
        for step, delay in enumerate(self.step_delays_samples, start=1):
            whole = math.floor(delay)
            fraction = delay - whole
            for control in self.control_names:
                lines.append(f"{p}_{control}_step_{step} = {1 - fraction!r} * {self._past_name(control, whole)} + "
                             f"{fraction!r} * {self._past_name(control, whole + 1)};")
        for control in self.control_names:
            lines += [f"{self._past_name(control, age)} = {self._past_name(control, age - 1)};"
                      for age in range(self.past_samples_kept, 0, -1)]
        return "\n".join(lines)

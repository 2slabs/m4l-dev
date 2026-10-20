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
`halfband_attenuation_db` (HIIR's compute_atten): 99.3 dB. Latency: the up and down pair's group delay at low
frequencies, measured in tests/test_techniques.py (HALFBAND_ROUND_TRIP_LATENCY_SAMPLES: 3.07 samples at the base rate,
the phase delay at 100 Hz); not linear phase (HIIR's
readme: the delays are "quite flat ... from DC up to about Fs/20" and rise toward the cut-off).

How a section runs at 2x: its statements run twice a sample (its marker placed twice, or its point code evaluated
at two points, architecture/dsp-blocks.md "Points"), once on `<name>_first`, once on `<name>_second` of an
upsampler (or on its own 2x-rate oscillators), and the downsampler takes the two results.
"""
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique

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


class HalfbandUpsampler(Technique):
    """`<name>_first`, `<name>_second`: `input` at twice the rate, the half-band's images removed. `coefficients`
    (a Python tuple, default the kit's design) is fixed when the instrument is built. State: two per stage."""

    def __init__(self, instance_name, input, coefficients=None):
        super().__init__(instance_name, input=input)
        self.coefficients = _check_coefficients(f"HalfbandUpsampler {instance_name}",
                                                halfband_coefficients() if coefficients is None else coefficients)

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


class HalfbandDownsampler(Technique):
    """`<name>_out`: the two samples `first`, `second` (a base-rate sample's two at twice the rate) filtered by the
    half-band and taken at the base rate. `coefficients` as the upsampler's. State: two per stage."""

    def __init__(self, instance_name, first, second, coefficients=None):
        super().__init__(instance_name, first=first, second=second)
        self.coefficients = _check_coefficients(f"HalfbandDownsampler {instance_name}",
                                                halfband_coefficients() if coefficients is None else coefficients)

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


# The default design's up-then-down phase delay at 100 Hz, in base-rate samples (measured, tests/test_techniques.py)
HALFBAND_ROUND_TRIP_LATENCY_SAMPLES = 3.07

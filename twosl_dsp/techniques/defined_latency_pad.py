"""The defined-latency pad (a technique): every audio path of a device delayed to one whole number of samples, the
device's Defined Latency (references/dsp.md, "Defined-latency pad"; architecture/overview.md, "Defined Latency").

The rule. Live is told a device's latency in whole samples (references/README.md, "Defined Latency"). A device's
declared figure is its latest audio path ROUNDED UP to a whole sample, and every path (each output, each switchable
alternative, each voice) is padded up to exactly that figure, so no path is early or late against what Live
compensates. A path's latency is the sum of its blocks' `latency_samples` (every gen block reports one, in host
samples). `DefinedLatency({path: latency})` applies the rule: `declared_latency_samples` (an int, what
`DevicePatchBuilder` takes), `pad_samples[path]`, and `pad(path, instance_name, input)` the block that pads it.
Figures within `WHOLE_SAMPLE_CRUMB` of a whole number are that whole number (0.5000000000000001 + 0.5 is 1, not 2):
a float crumb never decides the figure.

The pad (`DefinedLatencyPad`): a fixed delay of `pad_samples` (>= 0, fractional allowed).
- A whole pad is a ring of Histories: the input exactly that many samples late, bit for bit (0: the input itself,
  no state).
- A fractional pad P is a Thiran all-pass of order N = min(ceil(P), THIRAN_MAXIMUM_ORDER) at delay D = N - 1 + frac(P)
  (D in (N - 1, N): where Thiran's delay error is smallest for its order, and stable: every such D's poles are
  checked inside the unit circle, tests/test_techniques.py), after floor(P) - (N - 1) whole
  samples. Thiran (JOS, "Thiran Allpass Interpolators"; references/allpass-and-diffusion.md §5):
  a_k = (-1)^k C(N, k) prod_{n=0..N} (D - N + n) / (D - N + k + n), H(z) = z^-N A(1/z) / A(z): magnitude exactly 1
  at every frequency (an all-pass: no loss, no lift, where a fractional FIR droops: linear interpolation of half a
  sample is -16.7 dB at 20 kHz at 44.1 kHz), group delay maximally flat at D at DC. Its phase delay leaves D toward
  Nyquist; measured (tests/test_techniques.py, every frac in 0.01 steps, 44.1 kHz), worst |phase delay - P|:
  order 1 (pads under 1): 0.003 samples to 2 kHz, 0.073 to 10 kHz, 0.33 to 18 kHz, 0.49 to 20 kHz;
  order 4 (pads of 3 or more): 1e-4 to 2 kHz, 0.0023 to 10 kHz, 0.14 to 18 kHz, 0.30 to 20 kHz
  (orders 2 and 3 between: THIRAN_PHASE_DELAY_ERROR_BOUNDS). A pad lines a path up where it matters (a voice's
  attack, a switched path's timing); in the top octave its phase is the all-pass's.
- Inside a section run `oversampling` steps a host sample (a 2x section, its marker in each step: architecture/
  dsp-blocks.md, "Latency is always said"), the pad is `pad_samples` host samples, `pad_samples x oversampling`
  steps (`latency_steps`), the ring and the all-pass counting steps; `latency_samples` stays host samples. The
  bounds above are then in steps, at the step rate.
"""
import math
from fractions import Fraction

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique
from twosl_dsp.generated_numbers import generated_number

# Figures this close to a whole number are that whole number (float sums of block latencies: 0.5000000000000001).
WHOLE_SAMPLE_CRUMB = 1e-9
THIRAN_MAXIMUM_ORDER = 4

# Worst |phase delay - pad| in samples by Thiran order, for every fractional part, up to each frequency at 44.1 kHz
# (measured, tests/test_techniques.py holds them): {order: {top of the band in Hz: bound}}.
THIRAN_PHASE_DELAY_ERROR_BOUNDS = {
    1: {2000.0: 0.003, 10000.0: 0.073, 18000.0: 0.33, 20000.0: 0.49},
    2: {2000.0: 0.0001, 10000.0: 0.020, 18000.0: 0.23, 20000.0: 0.39},
    3: {2000.0: 0.0001, 10000.0: 0.0065, 18000.0: 0.17, 20000.0: 0.34},
    4: {2000.0: 0.0001, 10000.0: 0.0023, 18000.0: 0.14, 20000.0: 0.30},
}


def _checked_latency(owner, what, latency_samples):
    if isinstance(latency_samples, bool) or not isinstance(latency_samples, (int, float)) \
            or not math.isfinite(latency_samples) or latency_samples < 0:
        raise BuildError(f"{owner}: {what} is a delay in host samples, a finite number >= 0, got {latency_samples!r}")
    return latency_samples


def whole_if_within_a_crumb(samples):
    """`samples`, or the whole number (an int) it is within WHOLE_SAMPLE_CRUMB of."""
    nearest_whole = round(samples)
    return int(nearest_whole) if abs(samples - nearest_whole) <= WHOLE_SAMPLE_CRUMB else samples


def thiran_allpass_coefficients(order, delay_samples):
    """a_0 (1) .. a_order of the order-`order` Thiran all-pass with delay `delay_samples` at DC (JOS), computed exactly
    from `delay_samples` (Fractions) and written through generated_number."""
    if not order - 1 < delay_samples < order:
        raise BuildError(f"thiran_allpass_coefficients: the pad runs order {order} at a delay in ({order - 1}, "
                         f"{order}) (the range its stability is checked in), got {delay_samples!r}")
    delay = Fraction(delay_samples)
    coefficients = [1.0]
    for k in range(1, order + 1):
        product = Fraction(1)
        for n in range(order + 1):
            product *= (delay - order + n) / (delay - order + k + n)
        coefficients.append(generated_number((-1) ** k * math.comb(order, k) * product))
    return tuple(coefficients)


class DefinedLatencyPad(Technique):
    """`<name>_out` = `input` `pad_samples` (host samples) late (see the module's docstring). `oversampling`
    (required): the steps the instrument runs it a host sample (1 for a host-rate path). `latency_samples` is the pad
    in host samples, `latency_steps` in its steps."""

    def __init__(self, instance_name, *, input, pad_samples, oversampling):
        super().__init__(instance_name, input=input)
        if isinstance(oversampling, bool) or not isinstance(oversampling, int) or oversampling < 1:
            raise BuildError(f"DefinedLatencyPad {instance_name}: oversampling (required: the steps the instrument "
                             f"runs it a host sample, 1 at the host rate) is a whole number >= 1, got {oversampling!r}")
        pad_samples = whole_if_within_a_crumb(_checked_latency(f"DefinedLatencyPad {instance_name}", "pad_samples",
                                                               pad_samples))
        if not isinstance(pad_samples, int):
            pad_samples = generated_number(pad_samples)
        self.oversampling = oversampling
        self.latency_samples = pad_samples
        # the ring and the all-pass count steps
        pad_steps = whole_if_within_a_crumb(pad_samples * oversampling)
        self.latency_steps = pad_steps
        if isinstance(pad_steps, int):
            self.thiran_order, self.thiran_delay_samples, self.thiran_coefficients = 0, 0.0, ()
            self.whole_samples = pad_steps
        else:
            whole, fraction = divmod(pad_steps, 1.0)
            self.thiran_order = min(math.ceil(pad_steps), THIRAN_MAXIMUM_ORDER)
            self.thiran_delay_samples = self.thiran_order - 1 + fraction
            self.thiran_coefficients = thiran_allpass_coefficients(self.thiran_order, self.thiran_delay_samples)
            self.whole_samples = int(whole) - (self.thiran_order - 1)

    def response(self, frequency_hz, sample_rate):
        """The pad's complex response (the whole steps and the all-pass, at the step rate: `sample_rate` x
        `oversampling`)."""
        step_rate = sample_rate * self.oversampling
        z_inverse = complex(math.cos(2 * math.pi * frequency_hz / step_rate),
                            -math.sin(2 * math.pi * frequency_hz / step_rate))
        response = z_inverse ** self.whole_samples
        if self.thiran_order:
            a, order = self.thiran_coefficients, self.thiran_order
            numerator = sum(a[order - k] * z_inverse ** k for k in range(order + 1))
            denominator = sum(a[k] * z_inverse ** k for k in range(order + 1))
            response *= numerator / denominator
        return response

    def declarations(self):
        p = self.instance_name
        names = [f"{p}_x_{age}(0)" for age in range(1, self.thiran_order + 1)] \
            + [f"{p}_y_{age}(0)" for age in range(1, self.thiran_order + 1)] \
            + [f"{p}_whole_{age}(0)" for age in range(1, self.whole_samples + 1)]
        return "History " + ", ".join(names) + ";" if names else ""

    def statements(self):
        p, order, a = self.instance_name, self.thiran_order, self.thiran_coefficients
        lines = [f"// {p}: defined-latency pad, {self.latency_samples!r} samples ({self.oversampling} steps a sample): "
                 f"{self.whole_samples} whole steps"
                 + (f" + a Thiran all-pass of order {order} at {generated_number(self.thiran_delay_samples)!r}" if order else "")
                 + " (kit technique: defined-latency pad)",
                 f"{p}_x_0 = {self.input_expressions['input']};"]
        if order:
            feedforward = " + ".join(f"{a[order - k]!r} * {p}_x_{k}" for k in range(order + 1))
            feedback = " + ".join(f"{a[k]!r} * {p}_y_{k}" for k in range(1, order + 1))
            lines.append(f"{p}_y_0 = {feedforward} - ({feedback});")
            lines += [f"{p}_x_{age} = {p}_x_{age - 1};" for age in range(order, 0, -1)]
            lines += [f"{p}_y_{age} = {p}_y_{age - 1};" for age in range(order, 0, -1)]
        else:
            lines.append(f"{p}_y_0 = {p}_x_0;")
        if self.whole_samples:
            lines.append(f"{p}_out = {p}_whole_{self.whole_samples};")
            lines += [f"{p}_whole_{age} = {p}_whole_{age - 1};" for age in range(self.whole_samples, 1, -1)]
            lines.append(f"{p}_whole_1 = {p}_y_0;")
        else:
            lines.append(f"{p}_out = {p}_y_0;")
        return "\n".join(lines)

    def reset_statements(self):
        """Every sample the pad holds emptied (a Stop)."""
        p = self.instance_name
        return "\n".join([f"{p}_x_{age} = 0;\n{p}_y_{age} = 0;" for age in range(1, self.thiran_order + 1)]
                         + [f"{p}_whole_{age} = 0;" for age in range(1, self.whole_samples + 1)])


class DefinedLatency:
    """The device latency rule for one device: `path_latency_samples` {path name: its latency in host samples, the sum
    of its blocks' `latency_samples`} -> `declared_latency_samples` (the latest, rounded up to a whole sample: what
    `DevicePatchBuilder(latency_samples=...)` takes), `pad_samples` {path: the declared figure minus its latency},
    and `pad(path, instance_name, input)`: the `DefinedLatencyPad` that brings that path to the declared figure.
    Every path must be padded (`unpadded_paths()` is what is left; `check_every_path_padded()` fails the build)."""

    def __init__(self, device_name, path_latency_samples):
        if not isinstance(path_latency_samples, dict) or not path_latency_samples:
            raise BuildError(f"{device_name}: DefinedLatency takes {{path name: latency in host samples}} for every "
                             f"audio path (at least one), got {path_latency_samples!r}")
        self.device_name = device_name
        self.path_latency_samples = {
            path: whole_if_within_a_crumb(_checked_latency(f"{device_name}: DefinedLatency",
                                                           f"path {path!r}'s latency", latency))
            for path, latency in path_latency_samples.items()}
        self.declared_latency_samples = int(math.ceil(max(self.path_latency_samples.values())))
        self.pad_samples = {path: whole_if_within_a_crumb(self.declared_latency_samples - latency)
                            for path, latency in self.path_latency_samples.items()}
        self.padded_paths = set()

    def pad(self, path, instance_name, input):
        if path not in self.pad_samples:
            raise BuildError(f"{self.device_name}: DefinedLatency has no path {path!r} (its paths: "
                             f"{sorted(self.pad_samples)})")
        self.padded_paths.add(path)
        return DefinedLatencyPad(instance_name, input=input, pad_samples=self.pad_samples[path],
                                 oversampling=1)

    def unpadded_paths(self):
        return sorted(set(self.pad_samples) - self.padded_paths)

    def check_every_path_padded(self):
        """Fails the build if a path was declared and never padded (it would be early against Live)."""
        if self.unpadded_paths():
            raise BuildError(f"{self.device_name}: the paths {self.unpadded_paths()} were never padded to the "
                             f"declared {self.declared_latency_samples} samples (DefinedLatency.pad)")

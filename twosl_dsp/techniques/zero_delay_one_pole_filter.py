"""The zero-delay one-pole filter (a technique): a 1-pole low-pass and high-pass at once, zero-delay feedback (TPT),
linear (references/dsp.md, "Zero-delay one-pole filter"). For a circuit's RC corners: a coupling capacitor, an RC
low-pass at an amplifier's input.

The tick (Zavalishin, The Art of VA Filter Design rev. 2.1.2, §3.10 p. 78, with g = tan(pi fc / sr), prewarped, and
G = g / (1 + g)):

    v = G (x - s);   LP = v + s;   s = LP + v;   HP = x - LP

The bilinear transform of 1 / (1 + s) and s / (1 + s), stable for any g > 0 however it moves (each sample's new state
is a convex mix of the old one and the input). Both outputs are affine in this sample's input: LP = G x + (1 - G) s,
HP = (1 - G) x - (1 - G) s, gains inside (0, 1); `response_statements(output)` gives that gain and offset before the
tick, so a block that closes a loop through one-poles solves it without a unit delay (Zavalishin's zero-delay
feedback, §3.9). Not the kit's all-pass section: its LP - HP all-pass gains energy when the cutoff moves fast; the
zero-delay all-pass cascade's sections are lossless (zero_delay_allpass_cascade.py).

Prewarping as the state-variable filter's (eq. 3.18): exact at `prewarp_hz` (default the cutoff), held to
[10 Hz, 0.45 sr]; g = tan(pi fp / sr) fc / fp. `oversampling` (default 1): the ticks the instrument runs a host
sample (a 2x section ticks it twice), so sr above is the host rate times it; no latency at any (zero-delay).
"""
import math

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique

HIGHEST_PREWARP_OF_SAMPLE_RATE = 0.45    # tan(0.45 pi) = 6.3: the prewarping point stays where tan is finite
LOWEST_CUTOFF_HZ = 10.0                  # the cutoff's and the prewarping point's floor: g > 0
OUTPUTS = ("lowpass", "highpass")


def _check_a_number_input(instance_name, input_name, expression):
    """A literal input must be a finite number above 0 (fails the build otherwise); an expression is the caller's."""
    try:
        value = float(expression)
    except ValueError:
        return
    if not math.isfinite(value) or value <= 0:
        raise BuildError(f"ZeroDelayOnePoleFilter {instance_name}: {input_name} is {expression!r}; it must be a finite "
                         "number above 0")


class ZeroDelayOnePoleFilter(Technique):
    """`<name>_lowpass`, `<name>_highpass`: `input` through the TPT one-pole at `cutoff_hz` (at least 10 Hz, no upper
    limit), the bilinear transform exact at `prewarp_hz` (default: the cutoff; held to [10 Hz, 0.45 sr]). State: the
    integrator. `oversampling`: the ticks a host sample (whole, >= 1)."""

    def __init__(self, instance_name, input, cutoff_hz, prewarp_hz=None, oversampling=1):
        if isinstance(oversampling, bool) or not isinstance(oversampling, int) or oversampling < 1:
            raise BuildError(f"ZeroDelayOnePoleFilter {instance_name}: oversampling (the ticks the instrument runs it a "
                             f"host sample) is a whole number >= 1, got {oversampling!r}")
        self.oversampling = oversampling
        for input_name, expression in (("cutoff_hz", cutoff_hz), ("prewarp_hz", prewarp_hz)):
            if isinstance(expression, str):
                _check_a_number_input(instance_name, input_name, expression)
        super().__init__(instance_name, input=input, cutoff_hz=cutoff_hz,
                         prewarp_hz=f"{instance_name}_cutoff" if prewarp_hz is None else prewarp_hz)
        self.latency_samples = 0       # zero-delay feedback: no sample added (its phase is the analog one-pole's)

    def declarations(self):
        return self.substituted("History ${p}_s(0);")

    def statements(self):
        return self.coefficient_statements() + "\n" + self.tick_statements()

    def coefficient_statements(self):
        """Statements leaving `<name>_big_g` = g / (1 + g) for this sample."""
        rate = "samplerate" if self.oversampling == 1 else f"(samplerate * {self.oversampling})"
        return self.substituted("""// ${p}: 1-pole filter, zero-delay feedback (kit technique: zero-delay one-pole filter)
${p}_cutoff = max(${cutoff_hz}, ${lowest});
${p}_prewarp = clamp(${prewarp_hz}, ${lowest}, ${rate} * ${highest});
${p}_g = tan(pi * ${p}_prewarp / ${rate}) * (${p}_cutoff / ${p}_prewarp);
${p}_big_g = ${p}_g / (1 + ${p}_g);""", lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_PREWARP_OF_SAMPLE_RATE, rate=rate)

    def response_statements(self, output):
        """After `coefficient_statements`, before the tick: `<name>_<output>_gain` x input + `<name>_<output>_offset`
        is this sample's `output` (lowpass or highpass)."""
        if output not in OUTPUTS:
            raise BuildError(f"ZeroDelayOnePoleFilter {self.instance_name}: no output {output!r}; it has {OUTPUTS}")
        gain, offset = {"lowpass": ("${p}_big_g", "(1 - ${p}_big_g) * ${p}_s"),
                        "highpass": ("1 - ${p}_big_g", "(${p}_big_g - 1) * ${p}_s")}[output]
        return self.substituted(f"${{p}}_{output}_gain = {gain};\n${{p}}_{output}_offset = {offset};")

    def tick_statements(self):
        """The tick: the outputs from the input and the state, the state stepped."""
        return self.substituted("""${p}_v = ${p}_big_g * (${input} - ${p}_s);
${p}_lowpass = ${p}_v + ${p}_s;
${p}_s = ${p}_lowpass + ${p}_v;
${p}_highpass = ${input} - ${p}_lowpass;""")

    def reset_statements(self):
        return self.substituted("${p}_s = 0;")


def small_signal_response(frequency_hz, cutoff_hz, sample_rate, prewarp_hz=None):
    """{"lowpass", "highpass"}: the filter's complex response at `frequency_hz`, the analog one-pole at
    s = j tan(pi f / sr) / g, g = tan(pi fp / sr) fc / fp, clamped as the filter clamps."""
    cutoff_hz = max(cutoff_hz, LOWEST_CUTOFF_HZ)
    prewarp_hz = cutoff_hz if prewarp_hz is None else prewarp_hz
    prewarp_hz = min(max(prewarp_hz, LOWEST_CUTOFF_HZ), HIGHEST_PREWARP_OF_SAMPLE_RATE * sample_rate)
    g = math.tan(math.pi * prewarp_hz / sample_rate) * (cutoff_hz / prewarp_hz)
    s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) / g
    return {"lowpass": 1 / (1 + s), "highpass": s / (1 + s)}

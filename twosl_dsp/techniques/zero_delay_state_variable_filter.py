"""The zero-delay state-variable filter (a technique): a 2-pole multimode filter (low-pass, band-pass, high-pass at
once), zero-delay feedback (TPT), linear (references/dsp.md, "Zero-delay state-variable filter").

The analog SVF (Zavalishin, The Art of VA Filter Design rev. 2.1.2, §4.1 eq. 4.1):

    yHP = x - 2R yBP - yLP,   yBP' = wc yHP,   yLP' = wc yBP

so H_LP = wc^2 / D, H_BP = wc s / D, H_HP = s^2 / D, D = s^2 + 2R wc s + wc^2; the damping 2R = 1 / Q. Its TPT form
(§4.4 eq. 4.14, with trapezoidal integrators in transposed direct form II, g = tan(pi fc / sr), prewarped):

    HP = (x - (2R + g) s1 - s2) / (1 + 2R g + g^2);  BP = g HP + s1;  s1 = BP + g HP;  LP = g BP + s2;  s2 = LP + g BP

So the bilinear transform of the analog filter, with the cutoff mapped exactly, solved without a unit delay: no
added latency, and stable under any modulation of g > 0 and R > -1 (the denominator stays positive, §4.4).

The prewarping point (Zavalishin §3.8, eq. 3.18): the bilinear transform maps one frequency exactly, fp, and the
cutoff is scaled by mu(wp) / wp for it: g = tan(pi fp / sr) x fc / fp. By default fp is the cutoff (g = tan(pi fc / sr),
eq. 3.12). A circuit whose audible corner is not its natural frequency (an overdamped network: its -3 dB point far
below fc) says where it is heard by `prewarp_hz`. The cutoff itself may lie anywhere above 0, past Nyquist too (g
grows without bound; TPT stays stable for any g > 0). fp is held to [10 Hz, 0.45 sr], where tan is finite: a cutoff
past 0.45 sr with the default fp is eq. 3.21's bounded prewarping, fp = min(fc, 0.45 sr). The
outputs split the input exactly: LP + 2R BP + HP = x (eq. 4.4). The band-pass times 2R has unit gain at the cutoff
(§4.5 eq. 4.15). An impulse rings at the cutoff with an envelope time constant 1 / (R wc) = Q / (pi fc).

What it is for: an analog circuit's two-pole stages by their cutoff and Q (a Sallen-Key low- or high-pass, a
multiple-feedback band-pass, a bridged-T ring): a circuit module turns its components into the cutoff and Q. Not the
zero-delay ladder (four poles, one output, saturating loop) and not the LTC1060 / MF10 module (an LDI filter stepped at
a chip's clock, its staircase and images kept on purpose).
"""
import math

from twosl_dsp.build_error import BuildError
from twosl_dsp.gen_blocks import Technique

HIGHEST_PREWARP_OF_SAMPLE_RATE = 0.45    # tan(0.45 pi) = 6.3: the prewarping point stays where tan is finite
LOWEST_CUTOFF_HZ = 10.0                  # the cutoff's and the prewarping point's floor: g > 0
LOWEST_Q = 0.05                          # 2R = 20: heavily overdamped, still R > 0
HIGHEST_Q = 200.0                        # 2R = 0.005: rings for Q / (pi fc), 64 ms at 1 kHz


def _check_a_number_input(instance_name, input_name, expression):
    """A literal input must be a finite number above 0 (fails the build otherwise); an expression is the device's to
    keep there."""
    try:
        value = float(expression)
    except ValueError:
        return
    if not math.isfinite(value) or value <= 0:
        raise BuildError(f"ZeroDelayStateVariableFilter {instance_name}: {input_name} is {expression!r}; it must be a finite "
                         "number above 0")


class ZeroDelayStateVariableFilter(Technique):
    """`<name>_lowpass`, `<name>_bandpass`, `<name>_highpass`: `input` through the SVF at `cutoff_hz` (at least
    10 Hz, no upper limit) and `q` (clamped to [0.05, 200]), the bilinear transform exact at `prewarp_hz` (default:
    the cutoff; held to [10 Hz, 0.45 sr]); `<name>_bandpass_normalised` = 2R x the band-pass (unit gain at the
    cutoff). State: the two integrators."""

    def __init__(self, instance_name, input, cutoff_hz, q, prewarp_hz=None):
        for input_name, expression in (("cutoff_hz", cutoff_hz), ("q", q), ("prewarp_hz", prewarp_hz)):
            if isinstance(expression, str):
                _check_a_number_input(instance_name, input_name, expression)
        super().__init__(instance_name, input=input, cutoff_hz=cutoff_hz, q=q,
                         prewarp_hz=f"{instance_name}_cutoff" if prewarp_hz is None else prewarp_hz)
        self.latency_samples = 0       # zero-delay feedback: no sample added (its phase is the analog SVF's)

    def declarations(self):
        return self.substituted("History ${p}_s1(0), ${p}_s2(0);")

    def statements(self):
        return self.substituted("""// ${p}: 2-pole state-variable filter, zero-delay feedback (kit technique: zero-delay state-variable filter)
${p}_cutoff = max(${cutoff_hz}, ${lowest});
${p}_prewarp = clamp(${prewarp_hz}, ${lowest}, samplerate * ${highest});
${p}_g = tan(pi * ${p}_prewarp / samplerate) * (${p}_cutoff / ${p}_prewarp);
${p}_damping = 1 / clamp(${q}, ${lowest_q}, ${highest_q});
${p}_highpass = (${input} - (${p}_damping + ${p}_g) * ${p}_s1 - ${p}_s2) / (1 + ${p}_damping * ${p}_g + ${p}_g * ${p}_g);
${p}_v1 = ${p}_g * ${p}_highpass;
${p}_bandpass = ${p}_v1 + ${p}_s1;
${p}_s1 = ${p}_bandpass + ${p}_v1;
${p}_v2 = ${p}_g * ${p}_bandpass;
${p}_lowpass = ${p}_v2 + ${p}_s2;
${p}_s2 = ${p}_lowpass + ${p}_v2;
${p}_bandpass_normalised = ${p}_damping * ${p}_bandpass;""",
                                lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_PREWARP_OF_SAMPLE_RATE,
                                lowest_q=LOWEST_Q, highest_q=HIGHEST_Q)

    def reset_statements(self):
        """Statements that empty the integrators."""
        return self.substituted("${p}_s1 = 0;\n${p}_s2 = 0;")


def small_signal_response(frequency_hz, cutoff_hz, q, sample_rate, prewarp_hz=None):
    """{"lowpass", "bandpass", "highpass"}: the filter's complex response at `frequency_hz`, the analog SVF at
    s = j tan(pi f / sr) / g, g = tan(pi fp / sr) fc / fp (the bilinear transform prewarped at fp, eq. 3.18),
    clamped as the filter clamps."""
    cutoff_hz = max(cutoff_hz, LOWEST_CUTOFF_HZ)
    prewarp_hz = cutoff_hz if prewarp_hz is None else prewarp_hz
    prewarp_hz = min(max(prewarp_hz, LOWEST_CUTOFF_HZ), HIGHEST_PREWARP_OF_SAMPLE_RATE * sample_rate)
    g = math.tan(math.pi * prewarp_hz / sample_rate) * (cutoff_hz / prewarp_hz)
    damping = 1 / min(max(q, LOWEST_Q), HIGHEST_Q)
    s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) / g
    denominator = s * s + damping * s + 1
    return {"lowpass": 1 / denominator, "bandpass": s / denominator, "highpass": s * s / denominator}


def ring_time_constant_seconds(cutoff_hz, q):
    """The analog filter's impulse-response envelope time constant, 1 / (R wc) = Q / (pi fc)."""
    return q / (math.pi * cutoff_hz)

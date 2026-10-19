"""The state-variable filter block: a 2-pole multimode filter (low-pass, band-pass, high-pass at once), zero-delay
feedback (TPT), linear (references/dsp.md, "State-variable filter").

The analog SVF (Zavalishin, The Art of VA Filter Design rev. 2.1.2, §4.1 eq. 4.1):

    yHP = x - 2R yBP - yLP,   yBP' = wc yHP,   yLP' = wc yBP

so H_LP = wc^2 / D, H_BP = wc s / D, H_HP = s^2 / D, D = s^2 + 2R wc s + wc^2; the damping 2R = 1 / Q. Its TPT form
(§4.4 eq. 4.14, with trapezoidal integrators in transposed direct form II, g = tan(pi fc / sr), prewarped):

    HP = (x - (2R + g) s1 - s2) / (1 + 2R g + g^2);  BP = g HP + s1;  s1 = BP + g HP;  LP = g BP + s2;  s2 = LP + g BP

So the bilinear transform of the analog filter, with the cutoff mapped exactly, solved without a unit delay: no
added latency, and stable under any modulation of g > 0 and R > -1 (the denominator stays positive, §4.4). The
outputs split the input exactly: LP + 2R BP + HP = x (eq. 4.4). The band-pass times 2R has unit gain at the cutoff
(§4.5 eq. 4.15). An impulse rings at the cutoff with an envelope time constant 1 / (R wc) = Q / (pi fc).

What it is for: an analog circuit's two-pole stages by their cutoff and Q (a Sallen-Key low- or high-pass, a
multiple-feedback band-pass, a bridged-T ring). Not the ladder (four poles, one output, saturating loop) and not the
switched-capacitor block (an LDI filter stepped at a chip's clock, its staircase and images kept on purpose).
"""
import math

from m4l_dev.gen_blocks import GenBlock

HIGHEST_CUTOFF_OF_SAMPLE_RATE = 0.45     # g = tan(0.45 pi) = 6.3: finite (as the ladder block)
LOWEST_CUTOFF_HZ = 10.0
LOWEST_Q = 0.05                          # 2R = 20: heavily overdamped, still R > 0
HIGHEST_Q = 200.0                        # 2R = 0.005: rings for Q / (pi fc), 64 ms at 1 kHz


class StateVariableFilter(GenBlock):
    """`<name>_lowpass`, `<name>_bandpass`, `<name>_highpass`: `input` through the SVF at `cutoff_hz` (clamped to
    [10 Hz, 0.45 sr]) and `q` (clamped to [0.05, 200]); `<name>_bandpass_normalised` = 2R x the band-pass (unit
    gain at the cutoff). State: the two integrators."""

    def __init__(self, instance_name, input, cutoff_hz, q):
        super().__init__(instance_name, input=input, cutoff_hz=cutoff_hz, q=q)

    def declarations(self):
        return self.substituted("History ${p}_s1(0), ${p}_s2(0);")

    def statements(self):
        return self.substituted("""// ${p}: 2-pole state-variable filter, zero-delay feedback (kit state-variable block)
${p}_g = tan(pi * clamp(${cutoff_hz}, ${lowest}, samplerate * ${highest}) / samplerate);
${p}_damping = 1 / clamp(${q}, ${lowest_q}, ${highest_q});
${p}_highpass = (${input} - (${p}_damping + ${p}_g) * ${p}_s1 - ${p}_s2) / (1 + ${p}_damping * ${p}_g + ${p}_g * ${p}_g);
${p}_v1 = ${p}_g * ${p}_highpass;
${p}_bandpass = ${p}_v1 + ${p}_s1;
${p}_s1 = ${p}_bandpass + ${p}_v1;
${p}_v2 = ${p}_g * ${p}_bandpass;
${p}_lowpass = ${p}_v2 + ${p}_s2;
${p}_s2 = ${p}_lowpass + ${p}_v2;
${p}_bandpass_normalised = ${p}_damping * ${p}_bandpass;""",
                                lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_CUTOFF_OF_SAMPLE_RATE,
                                lowest_q=LOWEST_Q, highest_q=HIGHEST_Q)

    def reset_statements(self):
        """Statements that empty the integrators."""
        return self.substituted("${p}_s1 = 0;\n${p}_s2 = 0;")


def small_signal_response(frequency_hz, cutoff_hz, q, sample_rate):
    """{"lowpass", "bandpass", "highpass"}: the block's complex response at `frequency_hz`, the analog SVF at
    s = j tan(pi f / sr) / tan(pi fc / sr) (the prewarped bilinear transform), clamped as the block clamps."""
    cutoff_hz = min(max(cutoff_hz, LOWEST_CUTOFF_HZ), HIGHEST_CUTOFF_OF_SAMPLE_RATE * sample_rate)
    damping = 1 / min(max(q, LOWEST_Q), HIGHEST_Q)
    s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) / math.tan(
        math.pi * cutoff_hz / sample_rate)
    denominator = s * s + damping * s + 1
    return {"lowpass": 1 / denominator, "bandpass": s / denominator, "highpass": s * s / denominator}


def ring_time_constant_seconds(cutoff_hz, q):
    """The analog filter's impulse-response envelope time constant, 1 / (R wc) = Q / (pi fc)."""
    return q / (math.pi * cutoff_hz)

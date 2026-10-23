"""The bell equalizer (a technique): one gain-bearing peaking band, a boost or a cut of `gain_db` at `frequency_hz`
with width `q`, on the zero-delay state-variable filter (references/dsp.md, "Bell equalizer").

Zavalishin's 2-pole band-shelving filter (The Art of VA Filter Design rev. 2.1.2, §10.6, pp. 429-430):
H(s) = 1 + (M^-2 - 1) H_BP1(s), the SVF's damping being 2RM, equivalently (eq. 10.19)
H(s) = (s^2 + 2R M^-1 s + 1) / (s^2 + 2RM s + 1). With G = M^-2 the linear gain and 2R = 1 / Q:

    out = input + (G - 1) x the SVF's unit-peak band-pass, the SVF at Q sqrt(G)

So |H| = G at the centre exactly (the SVF is prewarped there: ZeroDelayStateVariableFilter's default), a cut is the
exact inverse of the same boost (H_G H_1/G = 1), and `q` is the band's Q measured at the half-gain points: |H| =
sqrt(G) where |1 - w^2| = w / Q, the band-pass's -3 dB edges (our algebra from eq. 10.19; tests hold it). Ranges:
gain within +-40 dB (Microtonic's EQ, MT-UG p. 15) and Q within [0.5, 20], so the SVF's Q (Q sqrt(G)) stays inside its
own [0.05, 200]. A fixed-Q band (Microtonic's, whose "peak or dip width (i.e., the q value) is fixed and cannot be
changed", its value not given) is the caller passing a constant.
"""
import math

from twosl_dsp.gen_blocks import Technique
from twosl_dsp.techniques.zero_delay_state_variable_filter import ZeroDelayStateVariableFilter

HIGHEST_GAIN_DB = 40.0
LOWEST_Q = 0.5
HIGHEST_Q = 20.0


def small_signal_response(frequency_hz, centre_hz, gain_db, q, sample_rate):
    """The band's complex response at `frequency_hz`: eq. 10.19 at s = j tan(pi f / sr) / tan(pi fc / sr)."""
    gain = 10 ** (min(max(gain_db, -HIGHEST_GAIN_DB), HIGHEST_GAIN_DB) / 20)
    q = min(max(q, LOWEST_Q), HIGHEST_Q)
    s = 1j * math.tan(math.pi * min(frequency_hz, 0.4999 * sample_rate) / sample_rate) \
        / math.tan(math.pi * centre_hz / sample_rate)
    return (s * s + math.sqrt(gain) / q * s + 1) / (s * s + s / (q * math.sqrt(gain)) + 1)


class BellEqualizer(Technique):
    """`<name>_out`: `input` with `gain_db` (held to +-40 dB) at `frequency_hz` (the SVF's cutoff: at least 10 Hz,
    exact at the centre up to 0.45 sr), width `q` (held to [0.5, 20]). State: the SVF's."""

    def __init__(self, instance_name, input, frequency_hz, gain_db, q):
        super().__init__(instance_name, input=input, frequency_hz=frequency_hz, gain_db=gain_db, q=q)
        self.latency_samples = 0       # the zero-delay SVF's: no sample added
        self.band = ZeroDelayStateVariableFilter(f"{instance_name}_band", input=f"{instance_name}_input",
                                                 cutoff_hz=frequency_hz, q=f"{instance_name}_band_q")

    def functions(self):
        return self.band.functions()

    def declarations(self):
        return self.band.declarations()

    def statements(self):
        return "\n".join((self.substituted("""// ${p}: bell equalizer, a peaking band on the state-variable filter (kit technique: bell equalizer)
${p}_input = ${input};
${p}_gain = dbtoa(clamp(${gain_db}, -${highest_gain}, ${highest_gain}));
${p}_band_q = clamp(${q}, ${lowest_q}, ${highest_q}) * sqrt(${p}_gain);""", highest_gain=HIGHEST_GAIN_DB,
                                             lowest_q=LOWEST_Q, highest_q=HIGHEST_Q),
                          self.band.statements(),
                          self.substituted("${p}_out = ${p}_input + (${p}_gain - 1) * ${p}_band_bandpass_normalised;")))

    def reset_statements(self):
        return self.band.reset_statements()

"""The parametric spring reverb (a technique): a spring tank whose every echo is a chirp spread over tens of ms, after
Valimaki, Parker & Abel's parametric spring reverberation effect (JAES 2010, as Parker 2011 and Gamper, Parker &
Valimaki 2011 describe it): one feedback loop per spring, each a delay line and a long cascade of stretched first-order
all-passes (the low-frequency chirps below the transition frequency F_C), a loop low-pass, a DC blocker and a negative
loop gain; the springs summed to two sides through a low-pass at F_C (references/dsp.md, "Parametric spring reverb").

What a spring does (Parker & Bilbao 2009): its impulse response is a train of echoes a round trip T_D apart, each bent
into a chirp: below F_C the low frequencies arrive first and the delay grows to a maximum at F_C. The model's
dispersion is M stretched all-passes A(z^K)^M, A(z) = (a + z^-1) / (1 + a z^-1), K = fs / (2 F_C), whose group delay
(Parker 2011 eq. 4) is

    D(w) = K M (1 - a^2) / (1 + 2 a cos(K w) + a^2)   samples,

rising from K M (1 - a) / (1 + a) at DC to K M (1 + a) / (1 - a) at F_C: with VPA10's 100 sections of 0.62 at
F_C 4300 Hz, 2.7 ms at DC and 50 ms at F_C. That curve, with a real K (`ideal_chain_group_delay_seconds`), is the
reference this technique is measured against.

How it is built, and why (measured 2026-10-21, tests/test_techniques.py, references/dsp.md):
- **The stretch K is fractional** (4.9 at 44.1 kHz for 4.5 kHz) and must be, or F_C moves with the sample rate (a
  whole K of 5 puts it at 4410 Hz at 44.1 kHz and 4800 Hz at 48 kHz). Each section is GPV11's eq. 4: K1 whole samples
  of delay and a first-order all-pass (c + z^-1) / (1 + c z^-1) for the rest, p = K - K1 (K1 = floor(K - 1/4), so p is
  in [1/4, 5/4) and c stays well inside the unit circle). GPV11 sets c by Thiran's rule, exact at DC; here it is
  set, as Parker 2011 eq. 6 sets the time-aligning all-pass, to be exact at the frequency that matters: its phase
  delay is p at w* = pi / K (where the section's delay peaks), c = (1 - b) / (1 + b), b = tan(p w* / 2) / tan(w* / 2).
  So every section's phase is exactly -pi at F_C and the chirp tops out at F_C at every rate. Against the reference over
  0-0.98 F_C (100 sections of 0.62, F_C 4.5 kHz) the worst group delay error is 0.11 / 0.14 / 0.02 ms at 44.1 / 48 /
  96 kHz (rms 0.02 / 0.03 / 0.004 ms) where Thiran's c leaves 0.31 / 1.37 / 0.07 ms.
- **At the host rate.** Running the loops at fs / R (Parker 2011's multirate C_lf) makes K / R near 2, where the same
  sections leave 1.2-2 ms of error near F_C (a fractional delay that must hold to pi / 2), and needs an anti-aliasing
  filter in front: rejected on the numbers. Its cost is the price: one 1-to-24-sample Delay and two Histories a
  section.
- **The section count follows the spring.** A spring's delay at every frequency is its wire's length over the
  wave's speed, so the whole curve, T_D and the chirp together, scales with the spring: a spring's sections are
  `sections_for_round_trip` = VPA10's 100 for its 56 ms spring, scaled by T_D / 56 ms (59 for 33 ms).
- **The loop's delay line** is the round trip less the chain's own delay at DC (FY12: the line is set "after taking
  into account the inherent delay-time of the allpass-chain"): a whole number of samples and a first-order Thiran
  all-pass for the rest (lossless; linear or spline interpolation in a loop loses up to 0.4 dB a trip at F_C). The
  loop low-pass's own delay, under 2 samples, moves with its corner and is left in, so a control can't make the line
  jump.
- **The loop**: the line, the chain, the loop low-pass at `damping_hz` (one pole, y += k (x - y)), the DC blocker at
  `dc_block_hz` (VPA10's 40 Hz, the low-pass of it subtracted): that is the spring's output; times g back into the
  line with the input. g = `loop_sign` x 10^(-3 T_D / Length) / |low-pass x blocker| at `decay_reference_hz`: the
  loop's gain there is exactly -60 dB over `length_s`, so `length_s` is the tank's T60 at its reference frequency
  (VPA10's g_lf is negative, "to match the reversal of the first echo", FY12). |g| is held to 0.999.
- **One transducer saturation, at the input**: the kit's first-order ADAA tanh at 1x on the input once (half a sample),
  not in the loops: the loops stay linear, as the model is, and a hot input or a kick clips where the coil and its
  magnet would, without the clip's droop compounding round every trip.
- **No high-frequency chirps.** The model's C_hf (wide-band chirps "generally at least 30 dB below", Parker 2011) is
  left out, as Parker 2011 allows "at the cost of some realism" and FY12's own case study does: it would cost 200
  host-rate sections a spring.
- **The output low-pass at F_C**: the stretched cascade repeats its curve above F_C (its images); an 8th-order
  Butterworth low-pass at F_C on each side takes them out (VPA10 has a 10th-order elliptic; the kit has the SVF).

`clear`, true on a sample, empties the tank: every History is set to 0 at once, and for one round trip (the longest
line and a section's delay) nothing is read or written, so after it every Delay holds zeros: the output is exactly 0
until something new comes in.

Inputs: `input` (into every spring, through the transducer), `damping_hz`, `length_s` (held to [0.01, 30] s),
`clear`. Outputs: `<name>_spring_1` .. `_<n>` (each spring's output, before the output low-pass), `<name>_left`,
`<name>_right` (the springs panned by `pans`, equal power, through the output low-pass), `<name>_clean`. Latency 0:
the output is the echoes, with no direct path (the transducer's half sample puts every echo half a sample after n T).
"""
import cmath
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number
from m4l_dev.techniques.antiderivative_tanh_saturator import AntiderivativeTanhSaturator
from m4l_dev.techniques.zero_delay_state_variable_filter import ZeroDelayStateVariableFilter

# Live's highest sample rate: every Delay is sized for it.
HIGHEST_SAMPLE_RATE = 192000
# VPA10's hand calibration of the Leem Pro KA-1210's spring 1, as GPV11 Table 1 quotes it: the section count is
# scaled from it by the round trip.
REFERENCE_ROUND_TRIP_MS = 56.0
REFERENCE_SECTIONS = 100
REFERENCE_ALLPASS_COEFFICIENT = 0.62
DC_BLOCK_HZ = 40.0                            # VPA10's H_dc (GPV11 §2)
DAMPING_OVER_TRANSITION = 2                   # neutral_damping_hz: an octave over F_C
STRETCH_FRACTION_FLOOR = 0.25                 # K1 = floor(K - 1/4): the fractional all-pass delays [1/4, 5/4)
SHORTEST_LENGTH_S, LONGEST_LENGTH_S = 0.01, 30.0
HIGHEST_LOOP_GAIN = 0.999
# 8th-order Butterworth: Q = 1 / (2 cos((2k - 1) pi / 16)), k = 1..4
OUTPUT_LOWPASS_QS = tuple(generated_number(1 / (2 * math.cos((2 * k - 1) * math.pi / 16))) for k in range(1, 5))


def neutral_damping_hz(transition_hz):
    """A tank's loop low-pass at its Bright 0 (DESIGN; no source gives a tank's decay against frequency): an octave
    over F_C, where it takes 0.8 dB a trip more at F_C than at 1 kHz (44.1 kHz), so the top of a tail dies a little
    faster. Two octaves up (x 4, Bright +1) it is held under Nyquist and the loss a trip is the same at every frequency
    within 0.1 dB, as VPA10's g_lf (one number); two down (Bright -1) its corner is F_C / 2."""
    return generated_number(DAMPING_OVER_TRANSITION * transition_hz)


def sections_for_round_trip(round_trip_ms):
    """The all-pass sections of a spring of this round trip: VPA10's 100 for 56 ms, in proportion (the chirp's spread
    scales with the spring's length, as T_D does)."""
    return max(1, round(REFERENCE_SECTIONS * round_trip_ms / REFERENCE_ROUND_TRIP_MS))


def stretch(sample_rate, transition_hz):
    """(K, K1, c): the stretch K = fs / (2 F_C), its whole samples K1 = floor(K - 1/4) (at least 1) and the fractional
    all-pass's coefficient c, phase delay K - K1 exactly at pi / K."""
    k = sample_rate / (2 * transition_hz)
    k1 = max(1, math.floor(k - STRETCH_FRACTION_FLOOR))
    w = math.pi / k
    b = math.tan((k - k1) * w / 2) / math.tan(w / 2)
    return k, k1, (1 - b) / (1 + b)


def section_response(frequency_hz, sample_rate, transition_hz, coefficient):
    """One section's complex response: (a + D) / (1 + a D), D = z^-K1 (c + z^-1) / (1 + c z^-1)."""
    _, k1, c = stretch(sample_rate, transition_hz)
    z_inverse = cmath.exp(-2j * math.pi * frequency_hz / sample_rate)
    d = z_inverse ** k1 * (c + z_inverse) / (1 + c * z_inverse)
    return (coefficient + d) / (1 + coefficient * d)


def chain_group_delay_seconds(frequency_hz, sample_rate, transition_hz, sections, coefficient):
    """The built chain's group delay (numerically, from its phase)."""
    step = 1e-3
    before = section_response(frequency_hz - step, sample_rate, transition_hz, coefficient)
    after = section_response(frequency_hz + step, sample_rate, transition_hz, coefficient)
    return -sections * cmath.phase(after / before) / (2 * math.pi * 2 * step)


def ideal_chain_group_delay_seconds(frequency_hz, sample_rate, transition_hz, sections, coefficient):
    """The reference: Parker 2011 eq. 4 with a real stretch K = fs / (2 F_C), in seconds."""
    k = sample_rate / (2 * transition_hz)
    w = 2 * math.pi * frequency_hz / sample_rate
    return k * sections * (1 - coefficient ** 2) / (1 + 2 * coefficient * math.cos(k * w) + coefficient ** 2) \
        / sample_rate


def chain_dc_delay_samples(sample_rate, transition_hz, sections, coefficient):
    """The built chain's group delay at DC: each section (1 - a) / (1 + a) x (K1 + (1 - c) / (1 + c))."""
    _, k1, c = stretch(sample_rate, transition_hz)
    return sections * (1 - coefficient) / (1 + coefficient) * (k1 + (1 - c) / (1 + c))


class ParametricSpringReverb(Technique):
    """See the module docstring. `round_trips_ms`, `sections` and `pans` (one each per spring), `transition_hz`,
    `allpass_coefficient`, `loop_sign`, `dc_block_hz` and `decay_reference_hz` are numbers; the inputs are GenExpr
    expressions."""

    def __init__(self, instance_name, *, input, damping_hz, length_s, clear, round_trips_ms, sections, pans,
                 transition_hz, allpass_coefficient, loop_sign, decay_reference_hz, dc_block_hz=DC_BLOCK_HZ):
        super().__init__(instance_name, input=input, damping_hz=damping_hz, length_s=length_s, clear=clear)
        # a reverb's wet: its echoes come round the loops, nothing passes straight through
        self.latency_samples = 0
        who = f"ParametricSpringReverb {instance_name}"
        self.round_trips_ms = tuple(float(value) for value in round_trips_ms)
        self.sections = tuple(sections)
        self.pans = tuple(float(value) for value in pans)
        if not self.round_trips_ms or len(self.sections) != len(self.round_trips_ms) \
                or len(self.pans) != len(self.round_trips_ms):
            raise BuildError(f"{who}: one round trip, one section count and one pan a spring, got "
                             f"{round_trips_ms!r}, {sections!r}, {pans!r}")
        if any(isinstance(m, bool) or not isinstance(m, int) or m < 1 for m in self.sections):
            raise BuildError(f"{who}: section counts must be whole numbers >= 1, got {sections!r}")
        if any(not -1 <= pan <= 1 for pan in self.pans):
            raise BuildError(f"{who}: pans are -1 (left) .. 1 (right), got {pans!r}")
        if not 0 < allpass_coefficient < 1:
            raise BuildError(f"{who}: the all-pass coefficient must be in (0, 1) (a positive one puts the chirp's top "
                             f"at F_C), got {allpass_coefficient!r}")
        if loop_sign not in (-1, 1):
            raise BuildError(f"{who}: loop_sign is -1 or 1, got {loop_sign!r}")
        lowest_rate = 44100.0
        if not 0 < transition_hz < lowest_rate / 2.5:
            raise BuildError(f"{who}: F_C {transition_hz} Hz must be under {lowest_rate / 2.5:g} Hz (a stretch of "
                             "at least 1.25 samples at 44.1 kHz)")
        if not 0 < decay_reference_hz < transition_hz:
            raise BuildError(f"{who}: the decay's reference frequency must be under F_C, got {decay_reference_hz!r}")
        for round_trip_ms, m in zip(self.round_trips_ms, self.sections):
            if not chain_dc_delay_samples(lowest_rate, transition_hz, m, allpass_coefficient) + 2 \
                    < lowest_rate * round_trip_ms / 1000:
                raise BuildError(f"{who}: {m} sections delay more at DC than the {round_trip_ms} ms round trip")
        self.transition_hz = float(transition_hz)
        self.allpass_coefficient = float(allpass_coefficient)
        self.loop_sign = loop_sign
        self.dc_block_hz = float(dc_block_hz)
        self.decay_reference_hz = float(decay_reference_hz)
        self.line_samples = int(HIGHEST_SAMPLE_RATE * max(self.round_trips_ms) / 1000.0) + 4
        self.section_samples = int(math.ceil(HIGHEST_SAMPLE_RATE / (2 * self.transition_hz))) + 2
        p = instance_name
        self.transducer = AntiderivativeTanhSaturator(f"{p}_transducer", input=f"{p}_drive", oversampling=1)
        self.output_lowpasses = {
            side: [ZeroDelayStateVariableFilter(f"{p}_{side}_lowpass_{k}",
                                                input=f"{p}_{side}_sum" if k == 1 else f"{p}_{side}_lowpass_{k - 1}_lowpass",
                                                cutoff_hz=repr(generated_number(self.transition_hz)), q=repr(q))
                   for k, q in enumerate(OUTPUT_LOWPASS_QS, start=1)]
            for side in ("left", "right")}

    @property
    def springs(self):
        return range(1, len(self.round_trips_ms) + 1)

    def _filters(self):
        return [self.transducer] + [f for side in ("left", "right") for f in self.output_lowpasses[side]]

    def functions(self):
        functions = {}
        for block in self._filters():
            functions.update(block.functions())
        return functions

    def declarations(self):
        p = self.instance_name
        lines = []
        histories = [f"{p}_clear_left(0)"]
        for i, m in zip(self.springs, self.sections):
            lines.append(f"Delay {p}_line_{i}({self.line_samples});")
            lines += [f"Delay {p}_section_{i}_{n}({self.section_samples});" for n in range(1, m + 1)]
            histories += [f"{p}_fraction_{i}_in(0)", f"{p}_fraction_{i}_out(0)", f"{p}_damping_{i}(0)",
                          f"{p}_dc_{i}(0)"]
            histories += [f"{p}_section_{i}_{n}_in(0), {p}_section_{i}_{n}_out(0)" for n in range(1, m + 1)]
        lines.append("History " + ", ".join(histories) + ";")
        lines += [block.declarations() for block in self._filters()]
        return "\n".join(line for line in lines if line.strip())

    def _reset_statements(self):
        p = self.instance_name
        names = []
        for i, m in zip(self.springs, self.sections):
            names += [f"{p}_fraction_{i}_in", f"{p}_fraction_{i}_out", f"{p}_damping_{i}", f"{p}_dc_{i}"]
            names += [f"{p}_section_{i}_{n}_{end}" for n in range(1, m + 1) for end in ("in", "out")]
        lines = [f"{name} = 0;" for name in names]
        lines += [block.reset_statements() for block in self._filters()]
        return "\n".join(lines)

    def statements(self):
        p = self.instance_name
        a = generated_number(self.allpass_coefficient)
        longest_ms = generated_number(max(self.round_trips_ms))
        code = [self.substituted("""// ${p}: dispersive springs, stretched all-pass chirps (kit technique: parametric spring reverb)
// clear: every state to 0 now, and nothing read or written for a round trip, so every Delay then holds zeros
if (${clear}) {
	${p}_clear_left = mstosamps(${longest_ms}) + ${section_samples} + 2;
	${reset}
}
if (${p}_clear_left > 0) {
	${p}_clear_left = ${p}_clear_left - 1;
}
${p}_clean = ${p}_clear_left > 0 ? 0 : 1;
// the stretch: K = fs / (2 F_C), K1 whole samples and a first-order all-pass whose phase delay is K - K1 at pi / K
${p}_stretch = samplerate / (2 * ${transition_hz});
${p}_stretch_whole = max(1, floor(${p}_stretch - ${floor}));
${p}_peak_w = pi / ${p}_stretch;
${p}_fraction_ratio = tan((${p}_stretch - ${p}_stretch_whole) * ${p}_peak_w / 2) / tan(${p}_peak_w / 2);
${p}_fraction_c = (1 - ${p}_fraction_ratio) / (1 + ${p}_fraction_ratio);
// a section's delay at DC, (1 - a) / (1 + a) x (K1 + (1 - c) / (1 + c)): the line is the round trip less the chain's
${p}_section_dc = ${dc_factor} * (${p}_stretch_whole + (1 - ${p}_fraction_c) / (1 + ${p}_fraction_c));
// the loop's low-pass and DC blocker, and their gain at the decay's reference frequency (taken out of g)
${p}_damping_k = 1 - exp(-6.283185307 * clamp(${damping_hz}, 10, samplerate * 0.49) / samplerate);
${p}_dc_k = 1 - exp(-6.283185307 * ${dc_block_hz} / samplerate);
${p}_reference_cos = cos(6.283185307 * ${decay_reference_hz} / samplerate);
${p}_damping_pole = 1 - ${p}_damping_k;
${p}_dc_pole = 1 - ${p}_dc_k;
${p}_reference_gain = ${p}_damping_k / sqrt(1 - 2 * ${p}_damping_pole * ${p}_reference_cos + ${p}_damping_pole * ${p}_damping_pole)
	* ${p}_dc_pole * sqrt((2 - 2 * ${p}_reference_cos) / (1 - 2 * ${p}_dc_pole * ${p}_reference_cos + ${p}_dc_pole * ${p}_dc_pole));
${p}_length = clamp(${length_s}, ${shortest}, ${longest});
// the transducer: the input saturates once, where the coil drives the springs
${p}_drive = ${input} * ${p}_clean;
""", longest_ms=longest_ms, section_samples=str(self.section_samples),
                                 reset=self._reset_statements().replace("\n", "\n\t"),
                                 transition_hz=self.transition_hz, floor=STRETCH_FRACTION_FLOOR,
                                 dc_factor=generated_number((1 - self.allpass_coefficient) / (1 + self.allpass_coefficient)),
                                 dc_block_hz=self.dc_block_hz, decay_reference_hz=self.decay_reference_hz,
                                 shortest=SHORTEST_LENGTH_S, longest=LONGEST_LENGTH_S),
                self.transducer.statements()]
        for i, round_trip_ms, m in zip(self.springs, self.round_trips_ms, self.sections):
            s = f"{p}_section_{i}"
            lines = [f"// spring {i}: {generated_number(round_trip_ms)!r} ms round trip, {m} sections",
                     f"{p}_line_samples_{i} = mstosamps({generated_number(round_trip_ms)!r}) - {m} * {p}_section_dc;",
                     f"{p}_line_whole_{i} = max(1, floor({p}_line_samples_{i} - 0.5));",
                     f"{p}_line_fraction_{i} = {p}_line_samples_{i} - {p}_line_whole_{i};",
                     f"{p}_line_c_{i} = (1 - {p}_line_fraction_{i}) / (1 + {p}_line_fraction_{i});",
                     f"{p}_read_{i} = {p}_line_{i}.read({p}_line_whole_{i}, interp=\"none\") * {p}_clean;",
                     f"{p}_x_{i}_0 = {p}_line_c_{i} * {p}_read_{i} + {p}_fraction_{i}_in - {p}_line_c_{i} * "
                     f"{p}_fraction_{i}_out;",
                     f"{p}_fraction_{i}_in = {p}_read_{i};",
                     f"{p}_fraction_{i}_out = {p}_x_{i}_0;"]
            for n in range(1, m + 1):
                # v = x - a w, y = a v + w, w the fractional all-pass of v K1 samples back
                lines += [f"{s}_{n}_back = {s}_{n}.read({p}_stretch_whole, interp=\"none\") * {p}_clean;",
                          f"{s}_{n}_w = {p}_fraction_c * {s}_{n}_back + {s}_{n}_in - {p}_fraction_c * {s}_{n}_out;",
                          f"{s}_{n}_in = {s}_{n}_back;",
                          f"{s}_{n}_out = {s}_{n}_w;",
                          f"{s}_{n}_v = {p}_x_{i}_{n - 1} - {a!r} * {s}_{n}_w;",
                          f"{s}_{n}.write({s}_{n}_v);",
                          f"{p}_x_{i}_{n} = {a!r} * {s}_{n}_v + {s}_{n}_w;"]
            lines += [f"{p}_damping_{i} = {p}_damping_{i} + {p}_damping_k * ({p}_x_{i}_{m} - {p}_damping_{i});",
                      f"{p}_dc_{i} = {p}_dc_{i} + {p}_dc_k * ({p}_damping_{i} - {p}_dc_{i});",
                      f"{p}_spring_{i} = {p}_damping_{i} - {p}_dc_{i};",
                      f"{p}_gain_{i} = clamp({self.loop_sign} * pow(10, -3 * {generated_number(round_trip_ms / 1000)!r}"
                      f" / {p}_length) / {p}_reference_gain, -{HIGHEST_LOOP_GAIN!r}, {HIGHEST_LOOP_GAIN!r});",
                      f"{p}_line_{i}.write(({p}_transducer_out + {p}_gain_{i} * {p}_spring_{i}) * {p}_clean);"]
            code.append("\n".join(lines))
        for side in ("left", "right"):
            terms = []
            for i, pan in zip(self.springs, self.pans):
                angle = (pan + 1) * math.pi / 4
                gain = generated_number(math.cos(angle) if side == "left" else math.sin(angle))
                if abs(gain) > 1e-12:
                    terms.append(f"{gain!r} * {p}_spring_{i}")
            code.append(f"{p}_{side}_sum = {' + '.join(terms) if terms else '0'};")
            code += [f.statements() for f in self.output_lowpasses[side]]
            code.append(f"{p}_{side} = {p}_{side}_lowpass_4_lowpass;")
        return "\n".join(code)

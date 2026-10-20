"""The LTC1060 / MF10 section (a circuit module): one section of the dual switched-capacitor filter chip (Linear's
LTC1060, pin-compatible with National's MF10), clocked, as the chip is (references/circuits/ltc1060-mf10.md).

Its inputs are the chip's: the signal at its input in volts, the clock at its CLK pin in Hz, the damping its
resistors set (q = 1/Q), pin 12's hold, and the summing amplifier's gains at its LP, BP and HP pins
(the band-limiting runs once, on their sum). Its build character (`Ltc1060Mf10Character`: the op amps' swing, where
the integrators meet their rails, the clock's feedthrough, the Q enhancement of its op amps) is a setting, the
datasheets' typical unit by default. Pin 12's 50:1 / 100:1 strap is `clock_ratio`, fixed when the instrument is built.

The chip is a discrete-time state-variable filter with fixed coefficients, stepped once per clock tick: its centre
frequency is the clock over `clock_ratio`. Each tick, with LDI integrators (the switched-capacitor biquad;
Chamberlin's digital state-variable filter):

    hp = x - lp - q bp ;   bp += F hp ;   lp += F bp ;      F = 2 sin(pi / clock_ratio)

so the poles sit at exactly clock / clock_ratio, whatever the host rate. Between ticks LP and BP hold (a zero-order
hold: the staircase that makes the chip's images, its "eee"); HP is the chip's summing amplifier, continuous in the
live input. The input is sampled at the ticks with nothing in front (it folds, as the chip's does).

Per host sample the module finds the ticks that fall in it (a phase accumulator at the clock) and steps every one of
them, the integrators' rails (a soft clip at full scale) acting on each tick, as the chip's do; the input is the
straight line between samples, read at each tick. Where no rail can act on a sample's ticks it steps all but the last
at once in closed form, exactly the ticks' own result (1e-11): with A the tick matrix, e the state's distance from its
rest point under the input's ramp, n ticks take e to A^n e, A^n = r^(n-1) sin(n th)/sin th A - r^n sin((n-1) th)/sin
th I (A's eigenvalues r e^(+-i th); complex for q < 2 - F, which the module keeps). "No rail can act" is a bound, not
a guess: A = T (r R) T^-1 (R a rotation, T from an eigenvector), so on every tick |T^-1 e| <= max(1, r^n) |T^-1 e0|,
and each integrator stays within its rest point plus its row of T times that; within the rail's knee on all n ticks,
the closed form; otherwise a GenExpr loop steps them one by one through the rails (at most MAXIMUM_TICKS_PER_SAMPLE a
sample: 137, the chip's 3 MHz top clock at 22.05 kHz; the clock is held to that below it).
The last tick is always stepped on its own (its jump is the staircase's band-limited edge).

Against itself at 64 x 44.1 kHz (every tick its own sample), a self-oscillating section at 44.1 and 48 kHz is within
0.07 dB and 0.03 cent from 1 to 22 kHz (with the rails once a host sample it was up to +1.9 dB, 64 cents off, and
locked to fs / 4 at 48 kHz); small signals render what the closed form alone rendered (1e-9).
CPU (one section, our renderer at -O2, a loaded i7-8700, ns a host sample at 44.1 kHz less the renderer's own 124):
small signals 140-360 at 100 Hz-20 kHz centres, as before; driven into the rails (a 2 x full-scale input or
self-oscillation) 90-340 to 1 kHz, 540-950 at 5 kHz, 950-1570 at 10 kHz, 2120-2930 at 20 kHz (before: 130-420
everywhere). A stereo pair of two sections is four: at 20 kHz in the rails, 8.5-11.7 us a sample, 37-52 % of a core.

What the chip makes and what the host rate would add (measured, research 2026-10-19, against a tick-exact model
rendered at 32 x and decimated: chip_reference.py in the research's scratchpad):
- read naively, the staircase's images above the host's Nyquist fold back into the audio band;
- so the module gives out the staircase as the straight line through the last two tick states (half a tick late,
  as the staircase is on average) plus
  the staircase's residual (a saw at the clock, one jump a tick), the residual band-limited by the kit's
  band-limited edges technique
  (4-point polyBLEP at the tick's exact time) and faded out as the clock passes 0.35 to 0.5 of the host rate, where
  the residual's fundamental leaves the band. Below 0.35 the output is the chip's staircase, band-limited; above 0.5
  it is the tick sequence, linearly interpolated (images sinc^2 down, -80 dB and lower).
- Q enhancement: the chip's op amps add phase in the resonant loop, which "enhances the Q value at high clock
  frequencies" (LTC1060 datasheet p. 8). Modelled as a damping offset that does not depend on Q, growing as the op
  amps settle less and less completely within a clock period: q' = q - A exp(-a / f_clock), A and a fitted to the
  datasheet's Q-error-vs-clock graphs (3 and 4: mode 1; 16 and 17: mode 3), read out of the PDF's drawing by the figure
  extractor and fitted per mode, supply and clock ratio (`Q_ENHANCEMENT_FITS`; references/circuits/ltc1060-mf10.md,
  "Q enhancement"). The character's `chip_mode` and `supply_volts` pick the fit, with `clock_ratio`. The default,
  mode 3 at +-5 V, fits its drawn curves (Q 5 to 50, to 1.405 MHz at 100:1) within 1.2 %-points of Q error rms, 12 kHz
  of clock rms; above its highest drawn clock the law is extrapolated. So a section set just short of oscillation
  sings at the top of its range (the FB1: "only manages the mid/upper kHz range", SOS 1997).
- Clock feedthrough: the datasheets' 10 mV p-p (LTC1060 "fCLK <= 1MHz", MF10 "Q = 10, Mode 1"): a square at the
  clock, +-5 mV at `clock_feedthrough` 1, through the same band-limiting and fade (none above the host's Nyquist).
- Rails: the integrators are linear to `rail_knee_of_full_scale` of the op amps' swing (`full_scale_volts`, +-4 V at
  +-5 V supplies), then round off into it.
- Hold (pin 12 to V-): the ticks stop; "the bandpass and lowpass outputs act as a S/H circuit holding the last
  sample" (LTC1060 p. 7). HP, the summer, still passes the input. The datasheet's 20 mV hold step is left out.

The output is `<name>_out` (volts) = lowpass_gain LP + bandpass_gain BP + highpass_gain HP + feedthrough, three
samples late: one for the input (the ticks read it between two samples, its straight line's droop undone by a
symmetric 3-tap pre-emphasis) and two for the band-limited edges' look-ahead. `latency_samples` says so. Inside, the
section works in fractions of full scale: the input is divided by `full_scale_volts` and the output multiplied back. Also `<name>_clock_hz`, `<name>_ticked` (1 when a tick fell in this sample) and
`<name>_tick_time` (ticks so far, modulo TICK_COUNT_WRAP, plus the phase: what a divided section follows).

A section's clock can come from another section's through a divider (a counter between the two CLK pins; the
Sherman Filterbank's Harmonics, in 2sl filter): with `divided_from` (another instance, whose statements run first) and
a `division` expression, while `division` > 0.5 its clock is the other's divided by it, phase-locked, ticking on every
division-th of its ticks; at 0 it runs on its own `clock_hz`. 2 x division must divide TICK_COUNT_WRAP.
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.band_limited_edges import BandLimitedEdges

CLOCK_RATIOS = (50, 100)             # pin 12: 50:1 tied to V+, 100:1 to half supply (LTC1060 p. 7)
LOWEST_CENTER_HZ = 1.0               # the clock is held to clock_ratio x [1 Hz, 30 kHz]
HIGHEST_CENTER_HZ = 30000.0          # LTC1060 p. 1 "Operates Up to 30kHz"; MF10 p. 1 "Operation up to 30 kHz"
RESIDUAL_FULL_BELOW = 0.35           # clock / host rate: the staircase's residual whole below, gone at 0.5
RESIDUAL_GONE_AT = 0.5
LOWEST_DAMPING = -0.2                # a section can be set past oscillation; the rails hold it
DAMPING_MARGIN = 0.05                # below 2 - F: the tick matrix keeps complex eigenvalues
INPUT_PRE_EMPHASIS_LATENCY_SAMPLES = 1   # the symmetric 3-tap pre-emphasis on the input: its middle tap
# The most ticks a host sample steps (the GenExpr loop's bound, a literal). LOWEST_HOST_SAMPLERATE is ours: half the
# lowest rate the kit levels and tests at (44.1 kHz), so the chip's whole range steps at any rate a host is likely to
# run. There the fastest clock (100 x 30 kHz) is 136.05 ticks a sample, so at most 137 ticks fall in one; below it the
# clock is held to 137 ticks a sample (the module's own sc_clock_hz says so).
LOWEST_HOST_SAMPLERATE = 22050.0
MAXIMUM_TICKS_PER_SAMPLE = math.ceil(max(CLOCK_RATIOS) * HIGHEST_CENTER_HZ / LOWEST_HOST_SAMPLERATE) + 1
TICK_COUNT_WRAP = 10080              # 2^5 3^2 5 7: 2 x every Harmonics division of the Sherman divides it
# The Q enhancement, q' = q - amplitude exp(-settling_clock_hz / f_clock), by (chip mode, supply volts (+-), clock
# ratio): the LTC1060 datasheet's Q-error-vs-clock graphs read and fitted by
# references/circuits/ltc1060-q-error-graphs/ (its q-error-graphs.json holds the curves, the fits and their errors).
# Mode 3 at +-7.5 V is Graph 17's mode 3 with R2 = R4; Graph 16 (mode 3, +-2.5 / +-5 V) has a capacitor across R4.
Q_ENHANCEMENT_FITS = {
    (1, 2.5, 100): (5.916, 4.311e6),      # Graph 3
    (1, 5.0, 100): (24.94, 1.056e7),      # Graph 3
    (1, 2.5, 50): (2.066, 2.754e6),       # Graph 3
    (1, 5.0, 50): (22.38, 8.962e6),       # Graph 3
    (1, 7.5, 100): (16.03, 1.170e7),      # Graph 4
    (1, 7.5, 50): (33.05, 1.119e7),       # Graph 4
    (3, 2.5, 100): (0.9676, 3.001e6),     # Graph 16
    (3, 5.0, 100): (3.530, 6.666e6),      # Graph 16
    (3, 2.5, 50): (0.2833, 1.597e6),      # Graph 16
    (3, 5.0, 50): (5.538, 5.828e6),       # Graph 16
    (3, 7.5, 100): (10.06, 9.261e6),      # Graph 17
    (3, 7.5, 50): (399.7, 1.197e7),       # Graph 17
}

FUNCTIONS = {
    "ltc1060_mf10_rail": """// an integrator's output against its op amp's rail: linear to the knee, then rounding off at full scale (1)
ltc1060_mf10_rail(v, knee, headroom) {
\tmagnitude = abs(v);
\tif (magnitude > knee) {
\t\treturn sign(v) * (knee + headroom * tanh((magnitude - knee) / headroom));
\t}
\treturn v;
}""",
}


@dataclasses.dataclass(frozen=True)
class Ltc1060Mf10Character:
    """One unit's build character; the defaults are the datasheets' typical part at +-5 V supplies."""
    full_scale_volts: float = 4.0                  # the op amps' swing at +-5 V (MF10 p. 4: +-3.8 V min, +-4.25 V typ)
    rail_knee_of_full_scale: float = 0.8           # the integrators are linear to here, then round off into the rail
    clock_feedthrough_volts_peak_to_peak: float = 0.010   # LTC1060 p. 2 "fCLK <= 1MHz"; MF10 p. 4 "Q = 10, Mode 1"
    # the chip's configuration and supply, which pick its Q enhancement (Q_ENHANCEMENT_FITS): mode 3 is the one whose
    # pins are this module's (HP, BP, LP: LTC1060 p. 13, Figure 11, "Mode 3: 2nd Order Filter Providing Highpass, Bandpass, Lowpass"); +-5 V the supply full_scale_volts is for
    chip_mode: int = 3
    supply_volts: float = 5.0

    @property
    def clock_feedthrough_of_full_scale(self):
        """The feedthrough square's amplitude (half its peak to peak) as a fraction of full scale."""
        return self.clock_feedthrough_volts_peak_to_peak / 2 / self.full_scale_volts


class Ltc1060Mf10Section(CircuitModule):
    """`<name>_out` (volts): `input_volts` through one section clocked at `clock_hz` (its centre: the clock over
    `clock_ratio`) with damping `damping` (q = 1/Q at a low clock; the chip's Q enhancement lowers it as the clock
    rises), `hold` (> 0.5: pin 12 at V-, the clock stops), `clock_feedthrough` (1 = this unit's feedthrough, the
    datasheets' 10 mV p-p by default) and the summing gains at the pins `lowpass_gain`, `bandpass_gain`,
    `highpass_gain`. `latency_samples` (3) late."""

    references_entry = "references/circuits/ltc1060-mf10.md"
    character_type = Ltc1060Mf10Character

    def __init__(self, instance_name, *, input_volts, clock_hz, damping, hold, clock_feedthrough, lowpass_gain,
                 bandpass_gain, highpass_gain, clock_ratio=100, divided_from=None, division=None, character=None):
        inputs = dict(input_volts=input_volts, clock_hz=clock_hz, damping=damping, hold=hold,
                      clock_feedthrough=clock_feedthrough, lowpass_gain=lowpass_gain, bandpass_gain=bandpass_gain,
                      highpass_gain=highpass_gain)
        if (divided_from is None) != (division is None):
            raise BuildError(f"Ltc1060Mf10Section {instance_name}: divided_from and division go together")
        if division is not None:
            if not isinstance(divided_from, Ltc1060Mf10Section):
                raise BuildError(f"Ltc1060Mf10Section {instance_name}: divided_from must be another "
                                 "Ltc1060Mf10Section instance")
            inputs["division"] = division
        super().__init__(instance_name, character=character, **inputs)
        if clock_ratio not in CLOCK_RATIOS:
            raise BuildError(f"Ltc1060Mf10Section {instance_name}: the chip's clock ratio is 50 or 100 (pin 12), "
                             f"got {clock_ratio!r}")
        self.clock_ratio = clock_ratio
        self.tick_coefficient = 2 * math.sin(math.pi / clock_ratio)
        fit_key = (self.character.chip_mode, self.character.supply_volts, clock_ratio)
        if fit_key not in Q_ENHANCEMENT_FITS:
            raise BuildError(f"Ltc1060Mf10Section {instance_name}: the datasheet draws no Q error for mode "
                             f"{fit_key[0]!r} at +-{fit_key[1]!r} V and {clock_ratio}:1; it draws "
                             f"{sorted(Q_ENHANCEMENT_FITS)}")
        self.q_enhancement_amplitude, self.q_enhancement_settling_clock_hz = Q_ENHANCEMENT_FITS[fit_key]
        self.divided_from = divided_from
        self.edges = BandLimitedEdges(f"{instance_name}_edges", naive=f"{instance_name}_naive", oversampling=1)
        self.latency_samples = INPUT_PRE_EMPHASIS_LATENCY_SAMPLES + self.edges.latency_samples
        p = instance_name
        self.edges.add_jump(f"{p}_ticks > 0", f"1 - {p}_last_tick_time", f"{p}_tick_jump")
        self.edges.add_jump(f"{p}_half_crossed > 0", f"1 - {p}_half_time", f"{p}_half_jump")

    def functions(self):
        return dict(FUNCTIONS, **self.edges.functions())

    def declarations(self):
        return self.substituted(
            "History ${p}_bp(0), ${p}_lp(0), ${p}_from_bp(0), ${p}_from_lp(0), ${p}_phase(0), ${p}_tick_count(0), "
            "${p}_previous_tick_input(0), ${p}_input_1(0), ${p}_input_2(0), ${p}_previous_division_time(0), "
            "${p}_previous_division(0);\n") + self.edges.declarations()

    def clock_statements(self):
        """Statements leaving the clock's phase before and after this sample (in ticks: a tick wherever it passes
        an integer) and the clock's increment (ticks a sample)."""
        free = self.substituted("""${p}_free_increment = ${p}_clock_input_hz / samplerate;""")
        if self.divided_from is None:
            return free + self.substituted("""
${p}_phase_before = ${p}_phase;
${p}_phase_after = ${p}_phase + ${p}_free_increment;""")
        return free + self.substituted("""
// divided from ${m}: its tick time over the division, phase-locked (the ticks are where that passes an integer; the
// first sample after locking, or after a new division, only starts from it)
${p}_division = max(${division}, 0);
${p}_locked = ${p}_division > 0.5;
${p}_division_time = ${p}_locked ? ${m}_tick_time / max(${p}_division, 0.5) : 0;
${p}_since = ${p}_previous_division == ${p}_division ? ${p}_previous_division_time : ${p}_division_time;
${p}_since = ${p}_division_time < ${p}_since ? ${p}_since - ${wrap} / max(${p}_division, 0.5) : ${p}_since;
${p}_phase_before = ${p}_locked ? ${p}_since - floor(${p}_since) : ${p}_phase;
${p}_phase_after = ${p}_locked ? ${p}_division_time - floor(${p}_since) : ${p}_phase + ${p}_free_increment;
${p}_previous_division_time = ${p}_division_time;
${p}_previous_division = ${p}_division;""", m=self.divided_from.instance_name, wrap=TICK_COUNT_WRAP)

    def statements(self):
        F = self.tick_coefficient
        clocked = self.substituted("""// ${p}: an LTC1060 / MF10 section, clocked (kit circuit module: LTC1060 / MF10 section)
// the input a sample late, so the ticks can read it between this sample and the last with the straight line's
// droop undone: the line through samples averages to sinc^2 at a tick (the ticks fall all over it), and (1 + w^2/12)
// from the symmetric 3-tap [-1, 14, -1] / 12 cancels its w^2 term
${p}_newest_input = ${input_volts} / ${full_scale_volts};
${p}_x = ${p}_input_1;
${p}_tick_input = (14 * ${p}_input_1 - ${p}_newest_input - ${p}_input_2) / 12;
${p}_input_2 = ${p}_input_1;
${p}_input_1 = ${p}_newest_input;
// (and to the ticks a host sample the module steps: never less at LOWEST_HOST_SAMPLERATE or above)
${p}_clock_input_hz = clamp(${clock_hz}, ${lowest_clock}, min(${highest_clock}, ${loop_ticks} * samplerate));
""", full_scale_volts=self.character.full_scale_volts, lowest_clock=self.clock_ratio * LOWEST_CENTER_HZ,
            highest_clock=self.clock_ratio * HIGHEST_CENTER_HZ, loop_ticks=MAXIMUM_TICKS_PER_SAMPLE - 1) + self.clock_statements() + self.substituted("""
// hold: the clock stops
${p}_phase_after = ${hold} > 0.5 ? ${p}_phase_before : ${p}_phase_after;
${p}_increment = ${p}_phase_after - ${p}_phase_before;
${p}_clock_hz = ${p}_increment * samplerate;
${p}_ticks = clamp(floor(${p}_phase_after), 0, ${maximum_ticks});
${p}_phase = ${p}_phase_after - floor(${p}_phase_after);
${p}_tick_count = ${p}_tick_count + ${p}_ticks - ${wrap} * floor((${p}_tick_count + ${p}_ticks) / ${wrap});
// (the phase kept a hair under 1: count + phase must not round up to the next tick's count before it happens)
${p}_tick_time = ${p}_tick_count + min(${p}_phase, 0.999999);
${p}_ticked = ${p}_ticks > 0;
// the damping with the chip's Q enhancement (none while held: the clock floored at 1 Hz, where it is 0), kept where
// the tick matrix's eigenvalues stay complex
${p}_q_enhancement = ${enhancement_amplitude} * exp(0 - ${settling_clock_hz} / max(${p}_clock_hz, 1));
${p}_q = clamp(${damping} - ${p}_q_enhancement, ${lowest_damping}, ${highest_damping});
${p}_a11 = 1 - ${F} * ${p}_q;
${p}_a22 = 1 - ${F} * ${F};
${p}_last_tick_time = 1;
${p}_tick_jump = 0;
if (${p}_ticks > 0) {
\t// the ticks in this sample but the last: n = ticks - 1. The input is the straight line between the last two
\t// samples, read at each tick
\t${p}_first_tick_time = (1 - ${p}_phase_before) / ${p}_increment;
\t${p}_last_tick_time = ${p}_first_tick_time + (${p}_ticks - 1) / ${p}_increment;
\t${p}_input_slope = ${p}_tick_input - ${p}_previous_tick_input;
\t${p}_first_tick_input = ${p}_previous_tick_input + ${p}_input_slope * ${p}_first_tick_time;
\t${p}_last_tick_input = ${p}_previous_tick_input + ${p}_input_slope * ${p}_last_tick_time;
\t${p}_n = ${p}_ticks - 1;
\t${p}_before_bp = ${p}_bp;
\t${p}_before_lp = ${p}_lp;
\tif (${p}_n > 0) {
\t\t// under a ramp of dx a tick the state rests at (dx / F, x[tick] - q dx / F); its distance e from there goes
\t\t// to A^n e. A = T (r R) T^-1 (r the eigenvalues' radius, R a rotation, T from an eigenvector), so on every
\t\t// tick |T^-1 e| <= max(1, r^n) |T^-1 e0|, and each integrator is within |its row of T| times that of its rest
\t\t${p}_tick_ramp = ${p}_input_slope / ${p}_increment;
\t\t${p}_rest_bp = ${p}_tick_ramp / ${F};
\t\t${p}_rest_lp_lag = ${p}_q * ${p}_tick_ramp / ${F};
\t\t${p}_rest_first_lp = ${p}_first_tick_input - ${p}_rest_lp_lag;
\t\t${p}_rest_before_lp = ${p}_last_tick_input - ${p}_rest_lp_lag;
\t\t${p}_e_bp = ${p}_bp - ${p}_rest_bp;
\t\t${p}_e_lp = ${p}_lp - ${p}_rest_first_lp;
\t\t${p}_radius = sqrt(${p}_a11);
\t\t${p}_trace = ${p}_a11 + ${p}_a22;
\t\t${p}_half_trace = ${p}_trace / 2;
\t\t${p}_eigen_imaginary = sqrt(max(${p}_a11 - ${p}_half_trace * ${p}_half_trace, 1e-24));
\t\t${p}_eigen_bp = 0 - ${p}_e_bp / ${F};
\t\t${p}_eigen_lp = (${p}_e_lp - (${p}_half_trace - ${p}_a11) * ${p}_eigen_bp) / ${p}_eigen_imaginary;
\t\t${p}_reach = sqrt(${p}_eigen_bp * ${p}_eigen_bp + ${p}_eigen_lp * ${p}_eigen_lp) * max(1, pow(${p}_radius, ${p}_n));
\t\t${p}_reach_bp = abs(${p}_rest_bp) + ${F} * ${p}_reach;
\t\t${p}_reach_lp = max(abs(${p}_rest_first_lp), abs(${p}_rest_before_lp)) + sqrt((${p}_half_trace - ${p}_a11) * (${p}_half_trace - ${p}_a11) + ${p}_eigen_imaginary * ${p}_eigen_imaginary) * ${p}_reach;
\t\tif (${p}_reach_bp <= ${rail_knee} && ${p}_reach_lp <= ${rail_knee}) {
\t\t\t// no rail can act on these ticks: all at once, in closed form, A^n = c1 A + c0 I
\t\t\t${p}_angle = atan2(${p}_eigen_imaginary * 2, ${p}_trace);
\t\t\t${p}_c1 = pow(${p}_radius, ${p}_n - 1) * sin(${p}_n * ${p}_angle) / sin(${p}_angle);
\t\t\t${p}_c0 = 0 - pow(${p}_radius, ${p}_n) * sin((${p}_n - 1) * ${p}_angle) / sin(${p}_angle);
\t\t\t${p}_before_bp = ${p}_c1 * (${p}_a11 * ${p}_e_bp - ${F} * ${p}_e_lp) + ${p}_c0 * ${p}_e_bp + ${p}_rest_bp;
\t\t\t${p}_before_lp = ${p}_c1 * (${F} * ${p}_a11 * ${p}_e_bp + ${p}_a22 * ${p}_e_lp) + ${p}_c0 * ${p}_e_lp + ${p}_rest_before_lp;
\t\t} else {
\t\t\t// a rail may act: each tick stepped through its rails
\t\t\tfor (${p}_tick = 0; ${p}_tick < ${loop_ticks}; ${p}_tick += 1) {
\t\t\t\tif (${p}_tick >= ${p}_n) {
\t\t\t\t\tbreak;
\t\t\t\t}
\t\t\t\t${p}_each_hp = ${p}_first_tick_input + ${p}_tick * ${p}_tick_ramp - ${p}_before_lp - ${p}_q * ${p}_before_bp;
\t\t\t\t${p}_before_bp = ltc1060_mf10_rail(${p}_before_bp + ${F} * ${p}_each_hp, ${rail_knee}, ${rail_headroom});
\t\t\t\t${p}_before_lp = ltc1060_mf10_rail(${p}_before_lp + ${F} * ${p}_before_bp, ${rail_knee}, ${rail_headroom});
\t\t\t}
\t\t}
\t}
\t// the last tick, stepped: the summer, then the two integrators against their rails
\t${p}_tick_hp = ${p}_last_tick_input - ${p}_before_lp - ${p}_q * ${p}_before_bp;
\t${p}_new_bp = ltc1060_mf10_rail(${p}_before_bp + ${F} * ${p}_tick_hp, ${rail_knee}, ${rail_headroom});
\t${p}_new_lp = ltc1060_mf10_rail(${p}_before_lp + ${F} * ${p}_new_bp, ${rail_knee}, ${rail_headroom});
\t// the staircase jumps by the step: from the state the line has reached (the old held one) to the new one
\t${p}_from_bp = ${p}_ticks > 1 ? ${p}_before_bp : ${p}_bp;
\t${p}_from_lp = ${p}_ticks > 1 ? ${p}_before_lp : ${p}_lp;
\t${p}_tick_jump_bp = ${p}_new_bp - ${p}_bp;
\t${p}_tick_jump_lp = ${p}_new_lp - ${p}_lp;
\t${p}_bp = ${p}_new_bp;
\t${p}_lp = ${p}_new_lp;
\t${p}_tick_jump = (${lowpass_gain} - ${highpass_gain}) * ${p}_tick_jump_lp + (${bandpass_gain} - ${highpass_gain} * ${p}_q) * ${p}_tick_jump_bp;
}
// the output: the line through the last two tick states half a tick on (the staircase's mean delay), plus the
// staircase's residual (a saw, zero mean) where the clock is in band
${p}_residual_gain = clamp((${gone} - ${p}_clock_hz / samplerate) / ${fade}, 0, 1);
${p}_line_bp = ${p}_from_bp + (${p}_bp - ${p}_from_bp) * (${p}_phase + 0.5);
${p}_line_lp = ${p}_from_lp + (${p}_lp - ${p}_from_lp) * (${p}_phase + 0.5);
${p}_out_bp = ${p}_line_bp + ${p}_residual_gain * (${p}_bp - ${p}_line_bp);
${p}_out_lp = ${p}_line_lp + ${p}_residual_gain * (${p}_lp - ${p}_line_lp);
// HP is the summer: the live input against the states
${p}_out_hp = ${p}_x - ${p}_out_lp - ${p}_q * ${p}_out_bp;
${p}_feedthrough_level = ${feedthrough_amplitude} * ${clock_feedthrough} * ${p}_residual_gain;
${p}_tick_jump = ${p}_residual_gain * ${p}_tick_jump + 2 * ${p}_feedthrough_level;
// the clock's second edge, half a tick after the tick
${p}_half_index = floor(${p}_phase_before - 0.5) + 1;
${p}_half_crossed = ${p}_increment > 0 && ${p}_half_index + 0.5 <= ${p}_phase_after;
${p}_half_time = ${p}_half_crossed > 0 ? (${p}_half_index + 0.5 - ${p}_phase_before) / ${p}_increment : 1;
${p}_half_jump = -2 * ${p}_feedthrough_level;
${p}_naive = ${lowpass_gain} * ${p}_out_lp + ${bandpass_gain} * ${p}_out_bp + ${highpass_gain} * ${p}_out_hp + ${p}_feedthrough_level * (${p}_phase < 0.5 ? 1 : -1);
${p}_previous_tick_input = ${p}_tick_input;
""", F=repr(F), wrap=TICK_COUNT_WRAP, enhancement_amplitude=repr(self.q_enhancement_amplitude),
            settling_clock_hz=repr(self.q_enhancement_settling_clock_hz),
            lowest_damping=LOWEST_DAMPING, highest_damping=highest_damping(self.clock_ratio), gone=RESIDUAL_GONE_AT,
            fade=RESIDUAL_GONE_AT - RESIDUAL_FULL_BELOW,
            feedthrough_amplitude=self.character.clock_feedthrough_of_full_scale,
            maximum_ticks=MAXIMUM_TICKS_PER_SAMPLE, loop_ticks=MAXIMUM_TICKS_PER_SAMPLE - 1, rail_knee=self.character.rail_knee_of_full_scale,
            rail_headroom=1 - self.character.rail_knee_of_full_scale)
        return clocked + self.edges.statements() + self.substituted("\n${p}_out = ${p}_edges_out * ${full_scale_volts};",
                                                                    full_scale_volts=self.character.full_scale_volts)

    def reset_statements(self):
        """Statements that empty the section (Stop): the integrators and the edges' ring."""
        p = self.instance_name
        lines = [f"{p}_{name} = 0;" for name in ("bp", "lp", "from_bp", "from_lp", "previous_tick_input", "input_1", "input_2")]
        return "\n".join(lines) + "\n" + self.edges.restart_statements(["0", "0"])


def small_signal_response(frequency_hz, clock_hz, damping, clock_ratio=100):
    """(LP, BP, HP) at the section's pins for small signals: the tick sequence's z-domain response at the clock, z =
    exp(j 2 pi f / f_clock), with no Q enhancement and no images. What a display draws. Per tick n:
    hp[n] = x - lp[n-1] - q bp[n-1], bp[n] = bp[n-1] + F hp[n], lp[n] = lp[n-1] + F bp[n]; the HP pin between ticks
    is x - lp - q bp with the live input, on average half a tick after the tick (z^(1/2)). So LP + HP (the notch) is
    about -30 dB deep at 100:1, not infinitely: the sampled data's own mismatch."""
    F = 2 * math.sin(math.pi / clock_ratio)
    clock = min(max(clock_hz, clock_ratio * LOWEST_CENTER_HZ), clock_ratio * HIGHEST_CENTER_HZ)
    z_inverse = complex(math.cos(2 * math.pi * frequency_hz / clock), -math.sin(2 * math.pi * frequency_hz / clock))
    q = min(max(damping, LOWEST_DAMPING), highest_damping(clock_ratio))
    integrator = F / (1 - z_inverse)
    tick_hp = 1 / (1 + z_inverse * (integrator * integrator + q * integrator))
    bp = integrator * tick_hp
    lp = integrator * bp
    half_tick_lead = complex(math.cos(math.pi * frequency_hz / clock), math.sin(math.pi * frequency_hz / clock))
    return lp, bp, half_tick_lead - lp - q * bp


def response_script_code():
    """The ES5 `ltc1060Mf10SectionResponse(frequencyHz, clockHz, damping, clockRatio)` for a device's displays, with
    the module's constants filled in (templates/ltc1060-mf10-section-response.template.js)."""
    from m4l_dev.generated_scripts import fill_template, kit_template_text
    return fill_template(kit_template_text("ltc1060-mf10-section-response.template.js"), {
        "LTC1060_MF10_LOWEST_CENTER_HZ": repr(LOWEST_CENTER_HZ),
        "LTC1060_MF10_HIGHEST_CENTER_HZ": repr(HIGHEST_CENTER_HZ),
        "LTC1060_MF10_LOWEST_DAMPING": repr(LOWEST_DAMPING),
        "LTC1060_MF10_DAMPING_MARGIN": repr(DAMPING_MARGIN)}, "ltc1060-mf10-section-response.template.js")


def highest_damping(clock_ratio=100):
    """The most damping the section takes (q = 1/Q): past it, the tick matrix's eigenvalues would turn real."""
    return 2 - 2 * math.sin(math.pi / clock_ratio) - DAMPING_MARGIN

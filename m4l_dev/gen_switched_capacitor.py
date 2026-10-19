"""The switched-capacitor filter block: one section of a dual switched-capacitor filter chip (the MF10 / LTC1060
family), clocked, as the chip is (references/dsp.md, "Switched-capacitor filter").

The chip is a discrete-time state-variable filter with fixed coefficients, stepped once per clock tick; its clock is
`clock_ratio` (100 or 50, the chip's pin 12) times the cutoff. Each tick, with LDI integrators (the switched-capacitor
biquad; Chamberlin's digital state-variable filter):

    hp = x - lp - q bp ;   bp += F hp ;   lp += F bp ;      F = 2 sin(pi / clock_ratio)

so the poles sit at exactly clock / clock_ratio, whatever the host rate. Between ticks LP and BP hold (a zero-order
hold: the staircase that makes the chip's images, its "eee"); HP is the chip's summing amplifier, continuous in the
live input. The input is sampled at the ticks with nothing in front (it folds, as the chip's does).

Per host sample the block finds the ticks that fall in it (a phase accumulator at the clock), and steps the filter
over all of them at once in closed form (the input a straight line between samples): with A the tick matrix, e the state's
distance from its rest point (0, x), n ticks take e to A^n e, and A^n = r^(n-1) sin(n th)/sin th A - r^n sin((n-1)
th)/sin th I (A's eigenvalues r e^(+-i th); complex for q < 2 - F, which the block keeps). The last tick is stepped
explicitly, so the integrators' rails (a soft clip at full scale) act at the tick rate whenever there is at most one
tick a sample. Above that the rails act once a host sample.

What the chip makes and what the host rate would add (measured, research 2026-10-19, against a tick-exact model
rendered at 32 x and decimated: chip_reference.py in the research's scratchpad):
- read naively, the staircase's images above the host's Nyquist fold back into the audio band;
- so the block gives out the staircase as the straight line through the last two tick states (half a tick late,
  as the staircase is on average) plus
  the staircase's residual (a saw at the clock, one jump a tick), the residual band-limited by the kit edges block
  (4-point polyBLEP at the tick's exact time) and faded out as the clock passes 0.35 to 0.5 of the host rate, where
  the residual's fundamental leaves the band. Below 0.35 the output is the chip's staircase, band-limited; above 0.5
  it is the tick sequence, linearly interpolated (images sinc^2 down, -80 dB and lower).
- Q enhancement: the chip's op amps add phase in the resonant loop, which "enhances the Q value at high clock
  frequencies" (LTC1060 datasheet p. 8); the datasheet's one number: at 1.4 MHz clock, Q = 5 has "about 8% error".
  Modelled as the excess-phase law Q' = Q / (1 - Q c f_clock), i.e. the damping q' = q - c f_clock, c fitted to that
  point (c = 0.0741 / (5 x 1.4 MHz)). So a section set just short of oscillation sings at the top of its range
  (the FB1: "only manages the mid/upper kHz range", SOS 1997).
- Clock feedthrough: the datasheets' 10 mV p-p (LTC1060 "fCLK <= 1MHz", MF10 "Q = 10, Mode 1") against a full scale
  of the op amps' 4 V swing: a square at the clock, +-0.00125 at `feedthrough` 1, through the same edges block and
  fade (none above the host's Nyquist).
- Hold (pin 12 to V-): the ticks stop; "the bandpass and lowpass outputs act as a S/H circuit holding the last
  sample" (LTC1060 p. 7). HP, the summer, still passes the input. The datasheet's 20 mV hold step is left out.

The output is `<name>_out` = lowpass_gain LP + bandpass_gain BP + highpass_gain HP + feedthrough, three samples
late: one for the input (the ticks read it between two samples, its straight line's droop undone by a symmetric
3-tap pre-emphasis) and two for the edges block's look-ahead. LATENCY_SAMPLES says so. Also `<name>_clock_hz`, `<name>_ticked` (1 when a tick fell in this sample) and
`<name>_tick_time` (ticks so far, modulo TICK_COUNT_WRAP, plus the phase: what a divided section follows).

A section can be divided from another (the Sherman's Harmonics: "what if I divide those clocks", R§2.0): with
`divided_from` (another instance, whose statements run first) and a `division` expression, while `division` > 0.5
its clock is the other's divided by it, phase-locked, ticking on every division-th of its ticks; at 0 it runs on its
own cutoff. 2 x division must divide TICK_COUNT_WRAP.
"""
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import GenBlock
from m4l_dev.gen_edges import BandLimitedEdges

CLOCK_RATIOS = (50, 100)
LOWEST_CUTOFF_HZ = 1.0
HIGHEST_CUTOFF_HZ = 30000.0          # the FB2 flyer's "0 Hz (!) up to 30 kHz"
FULL_SCALE_VOLTS = 4.0               # the op amps' swing at +-5 V (MF10: +-3.8 V min, +-4.25 V typ)
CLOCK_FEEDTHROUGH_VOLTS_PEAK_TO_PEAK = 0.010
FEEDTHROUGH_AMPLITUDE = CLOCK_FEEDTHROUGH_VOLTS_PEAK_TO_PEAK / 2 / FULL_SCALE_VOLTS
Q_ENHANCEMENT_PER_HZ = 0.0741 / (5 * 1.4e6)   # LTC1060 p. 8: Q = 5 "about 8% error" at a 1.4 MHz clock
RAIL_KNEE = 0.8                      # the integrators are linear to 0.8 of full scale, then round off into the rail
RESIDUAL_FULL_BELOW = 0.35           # clock / host rate: the staircase's residual whole below, gone at 0.5
RESIDUAL_GONE_AT = 0.5
LOWEST_DAMPING = -0.2                # a section can be set past oscillation; the rails hold it
DAMPING_MARGIN = 0.05                # below 2 - F: the tick matrix keeps complex eigenvalues
LATENCY_SAMPLES = 3
TICK_COUNT_WRAP = 10080              # 2^5 3^2 5 7: 2 x every Harmonics division of the Sherman divides it

FUNCTIONS = {
    "switched_capacitor_rail": f"""// an integrator's output against its op amp's rail: linear to the knee, then rounding off at full scale
switched_capacitor_rail(v) {{
\tmagnitude = abs(v);
\tif (magnitude > {RAIL_KNEE!r}) {{
\t\treturn sign(v) * ({RAIL_KNEE!r} + {1 - RAIL_KNEE!r} * tanh((magnitude - {RAIL_KNEE!r}) / {1 - RAIL_KNEE!r}));
\t}}
\treturn v;
}}""",
}


class SwitchedCapacitorFilter(GenBlock):
    """`<name>_out`: `input` through one clocked switched-capacitor section at `cutoff_hz` with damping `damping`
    (q = 1/Q at a low clock; the chip's Q enhancement lowers it as the clock rises), `hold` (> 0.5: the clock stops),
    `feedthrough` (the clock's feedthrough, 1 = the datasheets' 10 mV p-p) and the output mix `lowpass_gain`,
    `bandpass_gain`, `highpass_gain`. LATENCY_SAMPLES (3) late."""

    def __init__(self, instance_name, input, cutoff_hz, damping, hold, feedthrough, lowpass_gain, bandpass_gain,
                 highpass_gain, clock_ratio=100, divided_from=None, division=None):
        inputs = dict(input=input, cutoff_hz=cutoff_hz, damping=damping, hold=hold, feedthrough=feedthrough,
                      lowpass_gain=lowpass_gain, bandpass_gain=bandpass_gain, highpass_gain=highpass_gain)
        if (divided_from is None) != (division is None):
            raise BuildError(f"SwitchedCapacitorFilter {instance_name}: divided_from and division go together")
        if division is not None:
            if not isinstance(divided_from, SwitchedCapacitorFilter):
                raise BuildError(f"SwitchedCapacitorFilter {instance_name}: divided_from must be another "
                                 "SwitchedCapacitorFilter instance")
            inputs["division"] = division
        super().__init__(instance_name, **inputs)
        if clock_ratio not in CLOCK_RATIOS:
            raise BuildError(f"SwitchedCapacitorFilter {instance_name}: the chip's clock ratio is 50 or 100 (pin 12), "
                             f"got {clock_ratio!r}")
        self.clock_ratio = clock_ratio
        self.tick_coefficient = 2 * math.sin(math.pi / clock_ratio)
        self.divided_from = divided_from
        self.edges = BandLimitedEdges(f"{instance_name}_edges", naive=f"{instance_name}_naive")
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
        free = self.substituted("""${p}_free_increment = min(${ratio} * ${p}_cutoff_hz / samplerate, ${top} / samplerate);""",
                                ratio=self.clock_ratio, top=self.clock_ratio * HIGHEST_CUTOFF_HZ)
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
        clocked = self.substituted("""// ${p}: a clocked switched-capacitor section (kit switched-capacitor block)
// the input a sample late, so the ticks can read it between this sample and the last with the straight line's
// droop undone: the line through samples averages to sinc^2 at a tick (the ticks fall all over it), and (1 + w^2/12)
// from the symmetric 3-tap [-1, 14, -1] / 12 cancels its w^2 term
${p}_newest_input = ${input};
${p}_x = ${p}_input_1;
${p}_tick_input = (14 * ${p}_input_1 - ${p}_newest_input - ${p}_input_2) / 12;
${p}_input_2 = ${p}_input_1;
${p}_input_1 = ${p}_newest_input;
${p}_cutoff_hz = clamp(${cutoff_hz}, ${lowest}, ${highest});
""", lowest=LOWEST_CUTOFF_HZ, highest=HIGHEST_CUTOFF_HZ) + self.clock_statements() + self.substituted("""
// hold: the clock stops
${p}_phase_after = ${hold} > 0.5 ? ${p}_phase_before : ${p}_phase_after;
${p}_increment = ${p}_phase_after - ${p}_phase_before;
${p}_clock_hz = ${p}_increment * samplerate;
${p}_ticks = clamp(floor(${p}_phase_after), 0, ceil(${top} / samplerate) + 1);
${p}_phase = ${p}_phase_after - floor(${p}_phase_after);
${p}_tick_count = ${p}_tick_count + ${p}_ticks - ${wrap} * floor((${p}_tick_count + ${p}_ticks) / ${wrap});
// (the phase kept a hair under 1: count + phase must not round up to the next tick's count before it happens)
${p}_tick_time = ${p}_tick_count + min(${p}_phase, 0.999999);
${p}_ticked = ${p}_ticks > 0;
// the damping with the chip's Q enhancement, kept where the tick matrix's eigenvalues stay complex
${p}_q = clamp(${damping} - ${enhancement} * ${p}_clock_hz, ${lowest_damping}, ${highest_damping});
${p}_a11 = 1 - ${F} * ${p}_q;
${p}_a22 = 1 - ${F} * ${F};
${p}_last_tick_time = 1;
${p}_tick_jump = 0;
if (${p}_ticks > 0) {
\t// the ticks in this sample, all but the last at once: A^n e, n = ticks - 1. The input is the straight line between
\t// the last two samples, read at each tick; under a ramp of dx a tick the state rests at (dx / F, x[tick] - q dx / F), A^n e from there
\t${p}_first_tick_time = (1 - ${p}_phase_before) / ${p}_increment;
\t${p}_last_tick_time = ${p}_first_tick_time + (${p}_ticks - 1) / ${p}_increment;
\t${p}_input_slope = ${p}_tick_input - ${p}_previous_tick_input;
\t${p}_last_tick_input = ${p}_previous_tick_input + ${p}_input_slope * ${p}_last_tick_time;
\t${p}_tick_ramp = ${p}_ticks > 1 ? ${p}_input_slope / ${p}_increment : 0;
\t${p}_rest_bp = ${p}_tick_ramp / ${F};
\t${p}_rest_lp_lag = ${p}_q * ${p}_tick_ramp / ${F};
\t${p}_rest_first_lp = ${p}_previous_tick_input + ${p}_input_slope * ${p}_first_tick_time - ${p}_rest_lp_lag;
\t${p}_rest_before_lp = ${p}_last_tick_input - ${p}_rest_lp_lag;
\t${p}_radius = sqrt(${p}_a11);
\t${p}_trace = ${p}_a11 + ${p}_a22;
\t${p}_angle = atan2(sqrt(max(4 * ${p}_a11 - ${p}_trace * ${p}_trace, 1e-12)), ${p}_trace);
\t${p}_n = ${p}_ticks - 1;
\t${p}_c1 = pow(${p}_radius, ${p}_n - 1) * sin(${p}_n * ${p}_angle) / sin(${p}_angle);
\t${p}_c0 = 0 - pow(${p}_radius, ${p}_n) * sin((${p}_n - 1) * ${p}_angle) / sin(${p}_angle);
\t${p}_e_bp = ${p}_bp - ${p}_rest_bp;
\t${p}_e_lp = ${p}_lp - ${p}_rest_first_lp;
\t${p}_before_bp = ${p}_c1 * (${p}_a11 * ${p}_e_bp - ${F} * ${p}_e_lp) + ${p}_c0 * ${p}_e_bp + ${p}_rest_bp;
\t${p}_before_lp = ${p}_c1 * (${F} * ${p}_a11 * ${p}_e_bp + ${p}_a22 * ${p}_e_lp) + ${p}_c0 * ${p}_e_lp + ${p}_rest_before_lp;
\t// the last tick, stepped: the summer, then the two integrators against their rails
\t${p}_tick_hp = ${p}_last_tick_input - ${p}_before_lp - ${p}_q * ${p}_before_bp;
\t${p}_new_bp = switched_capacitor_rail(${p}_before_bp + ${F} * ${p}_tick_hp);
\t${p}_new_lp = switched_capacitor_rail(${p}_before_lp + ${F} * ${p}_new_bp);
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
${p}_feedthrough_level = ${feedthrough_amplitude} * ${feedthrough} * ${p}_residual_gain;
${p}_tick_jump = ${p}_residual_gain * ${p}_tick_jump + 2 * ${p}_feedthrough_level;
// the clock's second edge, half a tick after the tick
${p}_half_index = floor(${p}_phase_before - 0.5) + 1;
${p}_half_crossed = ${p}_increment > 0 && ${p}_half_index + 0.5 <= ${p}_phase_after;
${p}_half_time = ${p}_half_crossed > 0 ? (${p}_half_index + 0.5 - ${p}_phase_before) / ${p}_increment : 1;
${p}_half_jump = -2 * ${p}_feedthrough_level;
${p}_naive = ${lowpass_gain} * ${p}_out_lp + ${bandpass_gain} * ${p}_out_bp + ${highpass_gain} * ${p}_out_hp + ${p}_feedthrough_level * (${p}_phase < 0.5 ? 1 : -1);
${p}_previous_tick_input = ${p}_tick_input;
""", F=repr(F), wrap=TICK_COUNT_WRAP, enhancement=Q_ENHANCEMENT_PER_HZ, lowest_damping=LOWEST_DAMPING,
            highest_damping=highest_damping(self.clock_ratio), gone=RESIDUAL_GONE_AT,
            fade=RESIDUAL_GONE_AT - RESIDUAL_FULL_BELOW, feedthrough_amplitude=FEEDTHROUGH_AMPLITUDE,
            top=self.clock_ratio * HIGHEST_CUTOFF_HZ)
        return clocked + self.edges.statements() + self.substituted("\n${p}_out = ${p}_edges_out;")

    def reset_statements(self):
        """Statements that empty the section (Stop): the integrators and the edges' ring."""
        p = self.instance_name
        lines = [f"{p}_{name} = 0;" for name in ("bp", "lp", "from_bp", "from_lp", "previous_tick_input", "input_1", "input_2")]
        return "\n".join(lines) + "\n" + self.edges.restart_statements(["0", "0"])


def small_signal_response(frequency_hz, cutoff_hz, damping, clock_ratio=100):
    """(LP, BP, HP) at the section's pins for small signals: the tick sequence's z-domain response at the clock, z =
    exp(j 2 pi f / f_clock), with no Q enhancement and no images. What a display draws. Per tick n:
    hp[n] = x - lp[n-1] - q bp[n-1], bp[n] = bp[n-1] + F hp[n], lp[n] = lp[n-1] + F bp[n]; the HP pin between ticks
    is x - lp - q bp with the live input, on average half a tick after the tick (z^(1/2)). So LP + HP (the notch) is
    about -30 dB deep at 100:1, not infinitely: the sampled data's own mismatch."""
    F = 2 * math.sin(math.pi / clock_ratio)
    clock = clock_ratio * min(max(cutoff_hz, LOWEST_CUTOFF_HZ), HIGHEST_CUTOFF_HZ)
    z_inverse = complex(math.cos(2 * math.pi * frequency_hz / clock), -math.sin(2 * math.pi * frequency_hz / clock))
    q = min(max(damping, LOWEST_DAMPING), highest_damping(clock_ratio))
    integrator = F / (1 - z_inverse)
    tick_hp = 1 / (1 + z_inverse * (integrator * integrator + q * integrator))
    bp = integrator * tick_hp
    lp = integrator * bp
    half_tick_lead = complex(math.cos(math.pi * frequency_hz / clock), math.sin(math.pi * frequency_hz / clock))
    return lp, bp, half_tick_lead - lp - q * bp


def response_script_code():
    """The ES5 `switchedCapacitorResponse(frequencyHz, cutoffHz, damping, clockRatio)` for a device's displays, with
    the block's constants filled in (templates/switched-capacitor-response.template.js)."""
    from m4l_dev.generated_scripts import fill_template, kit_template_text
    return fill_template(kit_template_text("switched-capacitor-response.template.js"), {
        "SWITCHED_CAPACITOR_LOWEST_CUTOFF_HZ": repr(LOWEST_CUTOFF_HZ),
        "SWITCHED_CAPACITOR_HIGHEST_CUTOFF_HZ": repr(HIGHEST_CUTOFF_HZ),
        "SWITCHED_CAPACITOR_LOWEST_DAMPING": repr(LOWEST_DAMPING),
        "SWITCHED_CAPACITOR_DAMPING_MARGIN": repr(DAMPING_MARGIN)}, "switched-capacitor-response.template.js")


def highest_damping(clock_ratio=100):
    """The most damping the section takes (q = 1/Q): past it, the tick matrix's eigenvalues would turn real."""
    return 2 - 2 * math.sin(math.pi / clock_ratio) - DAMPING_MARGIN

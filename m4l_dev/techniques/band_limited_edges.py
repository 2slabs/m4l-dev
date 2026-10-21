"""Band-limited edges (a technique): jumps (4-point polyBLEP) and corners (4-point polyBLAMP) for a trivial waveform
(references/dsp.md, "Band-limited edges").

A device computes its trivial ("naive") waveform mix each sample, and tells the block where in that sample each jump
or corner happened. Each correction spreads over four samples, two on each side of the edge, so the block delays the
mix by two steps (a look-ahead ring, LOOK_AHEAD_STEPS): `<name>_out` is the mix of two steps ago plus every correction
that has landed on it. One block per voice serves every edge of every oscillator (the corrections add). A step is a
host sample, or 1 / `oversampling` of one where the instrument runs the block `oversampling` times a host sample (the
259's oscillators at 2x): `latency_steps` is the look-ahead, `latency_samples` the same in host samples.

The residuals are the cubic B-spline's first integral minus the unit step (polyBLEP) and its second integral minus
the ramp (polyBLAMP), per tap, as polynomials in d, the fraction of a sample from the edge to the first sample after
it (Esqueda, Välimäki & Bilbao, DAFx-16, Table 1; derived again from the B-spline and equal to it). Measured (research
2026-10-19, worst alias below 10 kHz re the fundamental, 44.1 kHz; tests/test_techniques.py keeps the claims):
saw C7 -50.4 (2-point) -> -76.2 dB; triangle C7 -51.8 (naive) -> -100.7 dB and C8 -41.2 -> -95.5 dB with polyBLAMP,
where an integrated polyBLEP square reached only -87.9 / -84.5 dB and needs a leaky integrator's state.
"""
from fractions import Fraction

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number

LOOK_AHEAD_STEPS = 2
TAP_NAMES = ("two_before", "one_before", "at", "one_after")   # samples n-2, n-1, n, n+1; n: the first after the edge

# Coefficients of d^0, d^1, ... per tap (taps in TAP_NAMES order).
POLYBLEP4_RESIDUAL = (
    ("0", "0", "0", "0", "1/24"),
    ("1/24", "1/6", "1/4", "1/6", "-1/8"),
    ("-1/2", "2/3", "0", "-1/3", "1/8"),
    ("-1/24", "1/6", "-1/4", "1/6", "-1/24"),
)
POLYBLAMP4_RESIDUAL = (
    ("0", "0", "0", "0", "0", "1/120"),
    ("1/120", "1/24", "1/12", "1/12", "1/24", "-1/40"),
    ("7/30", "-1/2", "1/3", "0", "-1/12", "1/40"),
    ("1/120", "-1/24", "1/12", "-1/12", "1/24", "-1/120"),
)


def horner(coefficients, variable):
    """GenExpr for the polynomial sum(c_i d^i), in Horner form, each coefficient (exact) through generated_number."""
    values = [Fraction(c) for c in coefficients]
    expression = repr(generated_number(values[-1]))
    for value in reversed(values[:-1]):
        expression = f"({expression}) * {variable} + {generated_number(value)!r}" if value else f"({expression}) * {variable}"
    return expression


def residual_functions(prefix, table, what):
    return {f"{prefix}_{tap}": f"// {what} residual at the sample {tap.replace('_', ' ')} the first sample after the "
                               f"edge (d: fraction of a sample from the edge to that sample)\n"
                               f"{prefix}_{tap}(d) {{\n\treturn {horner(row, 'd')};\n}}"
            for tap, row in zip(TAP_NAMES, table)}


FUNCTIONS = dict(residual_functions("polyblep4", POLYBLEP4_RESIDUAL, "4-point polyBLEP"),
                 **residual_functions("polyblamp4", POLYBLAMP4_RESIDUAL, "4-point polyBLAMP"))


class BandLimitedEdges(Technique):
    """`<name>_out`: `naive` two steps late, its jumps and corners band-limited. `oversampling` (required): the steps
    the instrument runs it a host sample.

    add_jump(happened, fraction, height): when `happened` (true this sample), the mix jumped by `height` at
    `fraction` of a sample before this sample. add_corner(happened, fraction, slope_change): its slope changed by
    `slope_change` (per sample) there."""

    def __init__(self, instance_name, *, naive, oversampling):
        super().__init__(instance_name, naive=naive)
        if isinstance(oversampling, bool) or not isinstance(oversampling, int) or oversampling < 1:
            raise BuildError(f"BandLimitedEdges {instance_name}: oversampling (required: the steps the instrument "
                             f"runs it a host sample) is a whole number >= 1, got {oversampling!r}")
        self.oversampling = oversampling
        self.latency_steps = LOOK_AHEAD_STEPS
        self.latency_samples = LOOK_AHEAD_STEPS / oversampling if LOOK_AHEAD_STEPS % oversampling \
            else LOOK_AHEAD_STEPS // oversampling
        self.edges = []

    def add_jump(self, happened, fraction, height):
        self.edges.append(("polyblep4", happened, fraction, height))

    def add_corner(self, happened, fraction, slope_change):
        self.edges.append(("polyblamp4", happened, fraction, slope_change))

    def restart_statements(self, next_naive_values):
        """Statements for a trivial wave whose phase restarts (a hard reset, as at a note): the LOOK_AHEAD_STEPS
        steps the ring holds but has not given out are replaced by `next_naive_values` (GenExpr expressions: the
        restarted wave at the next outputs, the first one first) and every correction pending in the ring is dropped,
        so nothing from before the restart comes out after it. The restart's own jump is not band-limited. Run them
        before this sample's `statements()`."""
        if len(next_naive_values) != LOOK_AHEAD_STEPS:
            raise BuildError(f"BandLimitedEdges {self.instance_name}: a restart takes the next {LOOK_AHEAD_STEPS} "
                             f"values of the restarted wave, got {len(next_naive_values)}")
        p = self.instance_name
        lines = [f"{p}_naive_2 = {next_naive_values[0]};", f"{p}_naive_1 = {next_naive_values[1]};"]
        lines += [f"{p}_correction_{tap} = 0;" for tap in TAP_NAMES]
        return "\n".join(lines)

    def functions(self):
        return dict(FUNCTIONS)

    def declarations(self):
        return self.substituted("History ${p}_naive_1(0), ${p}_naive_2(0), "
                                + ", ".join(f"${{p}}_correction_{tap}(0)" for tap in TAP_NAMES) + ";")

    def statements(self):
        if not self.edges:
            raise BuildError(f"BandLimitedEdges {self.instance_name}: no jump or corner was added")
        lines = [self.substituted("// ${p}: band-limited edges, two steps of look-ahead (kit technique: band-limited edges)")]
        for number, (kind, happened, fraction, size) in enumerate(self.edges, start=1):
            edge = f"{self.instance_name}_edge_{number}"
            lines.append(f"if ({happened}) {{")
            lines.append(f"\t{edge}_d = clamp({fraction}, 0, 1);")
            lines.append(f"\t{edge}_size = {size};")
            for tap in TAP_NAMES:
                history = f"{self.instance_name}_correction_{tap}"
                lines.append(f"\t{history} = {history} + {edge}_size * {kind}_{tap}({edge}_d);")
            lines.append("}")
        lines.append(self.substituted("""${p}_out = ${p}_naive_2 + ${p}_correction_two_before;
${p}_naive_2 = ${p}_naive_1;
${p}_naive_1 = ${naive};
${p}_correction_two_before = ${p}_correction_one_before;
${p}_correction_one_before = ${p}_correction_at;
${p}_correction_at = ${p}_correction_one_after;
${p}_correction_one_after = 0;"""))
        return "\n".join(lines)

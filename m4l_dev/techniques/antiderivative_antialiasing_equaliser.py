"""The equaliser after antiderivative antialiasing (ADAA), one for every ADAA in the kit (references/dsp.md,
"Antiderivative antialiasing equaliser"): the tanh saturator's first order, the piecewise-linear shaper's first and
second order, the 259 timbre section through the shaper's table.

ADAA is linear in the transfer, so whatever it shapes it also filters by its kernel: first order (Bilbao et al. 2017
eq. 5) by the 2-tap mean (1 + z^-1) / 2, zero-phase cos(w / 2), half a step late; second order (eq. 15) by the 3-tap
mean (1 + z^-1 + z^-2) / 3, zero-phase (1 + 2 cos w) / 3, one step late. Bilbao et al. §IV's remedy is "additional
linear filtering" (Valimaki, Pekonen & Nam 2012 eq. 16: a linear-phase FIR after it). Which FIR depends on the
kernel and on the rate the ADAA runs at, so there is one design function and one table of decisions:

- `adaa_equaliser_remez_design(order, edge_cycles, tap_pairs)`: the symmetric (2 tap_pairs + 1)-tap FIR whose
  product with the kernel is 1 at DC (the middle tap takes up the rest) and equiripple up to `edge_cycles` (cycles a
  step of the rate the ADAA runs at), by the Remez exchange. Ours.
- `ADAA_EQUALISER_DECISIONS` {(order, oversampling): the design's taps and edge, or None}: what each pair runs,
  measured 2026-10-20 (references/dsp.md has the numbers). At 2x: 5 taps, edge 5/24 of the 2x rate (20 kHz at 2x
  48 kHz), so the band it lifts past the host's Nyquist is what the instrument's downsampler takes away. At 1x: none.
  At the host's rate any equaliser lifts its top octave, where the kernel's mean holds the aliases down, and an alias
  there rises re the fundamental by the lift at its own frequency: the shaper's second order lost in 9 of 10 cases
  (up to +10.5 dB with the best 1x design), the tanh saturator's first order in 44 of 49 (up to +6.2 dB with the
  5/24 design; 4 within 0.05 dB, 1 lowered by 1.1 dB; tests/test_techniques.py keeps both).

`AntiderivativeAntialiasingEqualiser(name, raw_mean=, order=, oversampling=)` is the technique: `<name>_out` is
`raw_mean` (the ADAA block's mean this step) through the pair's equaliser, its state the last raw means. A pair with
no decision fails the build: a block takes its oversampling with no default. A block that runs it on one stream
places its statements once a step; one that evaluates its ADAA at several points a step (the 259 timbre section) uses
`output_expression(newest)` at each point and `remember_statements(newest)` for the point it keeps.
"""
import math
from fractions import Fraction

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number


class AntiderivativeAntialiasingKernel:
    """ADAA of `order` on a straight transfer: a mean over `order` + 1 taps, its zero-phase response, its latency."""

    def __init__(self, order, latency_steps, zero_phase_response, description):
        self.order = order
        self.latency_steps = latency_steps
        self.zero_phase_response = zero_phase_response
        self.description = description


ADAA_KERNELS = {
    1: AntiderivativeAntialiasingKernel(1, 0.5, lambda w: math.cos(w / 2), "the 2-tap mean (1 + z^-1) / 2"),
    2: AntiderivativeAntialiasingKernel(2, 1, lambda w: (1 + 2 * math.cos(w)) / 3,
                                        "the 3-tap mean (1 + z^-1 + z^-2) / 3"),
}


def adaa_equaliser_remez_design(order, edge_cycles, tap_pairs):
    """(taps, worst deviation): the symmetric (2 tap_pairs + 1)-tap linear-phase equaliser for ADAA of `order` whose
    product with its kernel is 1 at DC and equiripple up to `edge_cycles` (cycles a step), by the Remez exchange on
    tap_pairs + 1 extrema over a 20001-point grid, until the extrema stop moving. Taps outermost first, symmetric."""
    kernel_response = ADAA_KERNELS[order].zero_phase_response
    edge = 2 * math.pi * edge_cycles
    unknowns = tap_pairs + 1                   # the tap pairs (DC fixed at 1 by the middle tap) and the ripple

    def pair_basis(distance, w):               # a tap pair at +-distance, the middle tap taking up its DC
        return 2 * (math.cos(distance * w) - 1)

    def deviation(pairs, w):                   # pairs[k]: the tap pair at distance k + 1
        return kernel_response(w) * (1 + sum(tap * pair_basis(k + 1, w) for k, tap in enumerate(pairs))) - 1
    extrema = [edge * (k + 1) / unknowns for k in range(unknowns)]
    grid = [edge * k / 20000 for k in range(20001)]
    for _ in range(40):
        rows = [[kernel_response(w) * pair_basis(k + 1, w) for k in range(tap_pairs)]
                + [-(-1) ** i, 1 - kernel_response(w)] for i, w in enumerate(extrema)]
        for i in range(unknowns):              # Gauss-Jordan
            pivot = max(range(i, unknowns), key=lambda r: abs(rows[r][i]))
            rows[i], rows[pivot] = rows[pivot], rows[i]
            for r in range(unknowns):
                if r != i:
                    factor = rows[r][i] / rows[i][i]
                    rows[r] = [a - factor * b for a, b in zip(rows[r], rows[i])]
        pairs = [rows[k][unknowns] / rows[k][k] for k in range(tap_pairs)]
        errors = [deviation(pairs, w) for w in grid]
        peaks = [grid[k] for k in range(1, len(grid) - 1)
                 if abs(errors[k]) >= abs(errors[k - 1]) and abs(errors[k]) >= abs(errors[k + 1]) and abs(errors[k]) > 1e-12]
        new_extrema = sorted(set(peaks + [edge]))[-unknowns:]
        if len(new_extrema) != unknowns:
            raise BuildError(f"adaa_equaliser_remez_design: the Remez exchange lost its extrema: {new_extrema!r} "
                             f"(order {order}, edge {edge_cycles!r}, {tap_pairs} tap pairs)")
        if new_extrema == extrema:
            break
        extrema = new_extrema
    else:
        raise BuildError(f"adaa_equaliser_remez_design: the Remez exchange did not settle in 40 rounds (order {order}, "
                         f"edge {edge_cycles!r}, {tap_pairs} tap pairs)")
    taps = tuple(reversed(pairs)) + (1 - 2 * sum(pairs),) + tuple(pairs)
    return taps, max(abs(error) for error in errors)


# The decisions (the module docstring): the 2x taps are adaa_equaliser_remez_design(order, 5/24, 2)'s, recorded here
# so a build does not run the exchange (tests/test_techniques.py designs them again, to 5e-10 of each), to
# generated_number's digits (m4l_dev/generated_numbers.py); the middle tap takes up DC exactly (a Fraction).
# Order 1: the product with cos(w / 2) within +-0.00114 (0.0099 dB) up to the edge.
# Order 2: the product with (1 + 2 cos w) / 3 within +-0.0111 (0.0972 dB) up to the edge, and no higher up to the
# host's Nyquist (1/4 of the 2x rate); above that, to the 2x Nyquist, it lifts the 3-tap mean's stop band (the product
# +6.4 dB there, the equaliser alone +15.9 dB): the downsampler's.
ADAA_EQUALISER_EDGE_AT_2X = 5 / 24
FIRST_ORDER_OUTER_TAP_AT_2X = 0.03907501774
FIRST_ORDER_INNER_TAP_AT_2X = -0.2731196322
SECOND_ORDER_OUTER_TAP_AT_2X = 0.2663188927
SECOND_ORDER_INNER_TAP_AT_2X = -1.314576774


def checked_equaliser_taps(taps, where):
    """`taps` if they are an equaliser's (symmetric and odd in number: linear phase, centred on a whole step; summing
    to 1: DC exactly 1), else a BuildError naming `where`."""
    taps = tuple(taps)
    if len(taps) % 2 != 1 or taps != tuple(reversed(taps)):
        raise BuildError(f"{where}: an ADAA equaliser's taps are symmetric and odd in number (linear phase, centred on "
                         f"a whole step), got {taps!r}")
    if abs(sum(taps) - 1) > 1e-15:
        raise BuildError(f"{where}: an ADAA equaliser's taps sum to 1 (DC exactly 1), got {sum(taps)!r}")
    return taps


def _five_symmetric_taps(outer, inner):
    middle = generated_number(1 - 2 * Fraction(outer) - 2 * Fraction(inner))
    return checked_equaliser_taps((outer, inner, middle, inner, outer), "ADAA_EQUALISER_DECISIONS")


# 4x (try/gate-4x, 2026-10-21: 2sl gate's voices at 4x): order 2 only, adaa_equaliser_remez_design(2, 5/48, 2) (20 kHz
# at 4x 48 kHz): the product with the 3-tap mean within +-0.000123 (0.0011 dB) up to the edge.
ADAA_EQUALISER_EDGE_AT_4X = 5 / 48
SECOND_ORDER_OUTER_TAP_AT_4X = 0.1361045795
SECOND_ORDER_INNER_TAP_AT_4X = -0.8744133585
ADAA_EQUALISER_DECISIONS = {
    (1, 1): None,
    (1, 2): (_five_symmetric_taps(FIRST_ORDER_OUTER_TAP_AT_2X, FIRST_ORDER_INNER_TAP_AT_2X), ADAA_EQUALISER_EDGE_AT_2X),
    (2, 1): None,
    (2, 2): (_five_symmetric_taps(SECOND_ORDER_OUTER_TAP_AT_2X, SECOND_ORDER_INNER_TAP_AT_2X),
             ADAA_EQUALISER_EDGE_AT_2X),
    (2, 4): (_five_symmetric_taps(SECOND_ORDER_OUTER_TAP_AT_4X, SECOND_ORDER_INNER_TAP_AT_4X),
             ADAA_EQUALISER_EDGE_AT_4X),
}
ADAA_OVERSAMPLINGS = tuple(sorted({oversampling for _, oversampling in ADAA_EQUALISER_DECISIONS}))


def adaa_equaliser_decision(order, oversampling, who):
    """(taps, edge cycles) for ADAA of `order` run at `oversampling` x the host rate: ((1.0,), None) where the table
    says none. `who` names the block for the error; a pair with no decision fails the build (never a default: the 2x
    design at 1x lifts the host's top octave)."""
    if isinstance(order, bool) or order not in ADAA_KERNELS:
        raise BuildError(f"{who}: ADAA's order is one of {sorted(ADAA_KERNELS)}, got {order!r}")
    if isinstance(oversampling, bool) or not isinstance(oversampling, int) \
            or (order, oversampling) not in ADAA_EQUALISER_DECISIONS:
        raise BuildError(f"{who}: ADAA{order} needs its oversampling, one of {list(ADAA_OVERSAMPLINGS)} (its equaliser "
                         f"is decided for the rate it runs at), got {oversampling!r}")
    decision = ADAA_EQUALISER_DECISIONS[(order, oversampling)]
    return ((1.0,), None) if decision is None else decision


class AntiderivativeAntialiasingEqualiser(Technique):
    """`<name>_out`: `raw_mean`, ADAA of `order`'s mean this step, through the equaliser decided for `order` at
    `oversampling` x the host rate (`taps`: symmetric, odd in number, summing to 1, so DC is exactly 1; centred on the
    middle one; holding the product with the kernel flat up to `edge_cycles`, cycles a step). One tap (`edge_cycles`
    None) is no equaliser: the raw mean is the output. `latency_steps`: the kernel's and the equaliser's, in its steps;
    `latency_samples` the same in host samples (steps / `oversampling`). State: the
    last raw means (`length` - 1 Histories `<name>_raw_mean_before_<age>`). Without `raw_mean` it is used at points
    only (`output_expression`, `remember_statements`) and has no `statements()`."""

    references_entry = "references/dsp.md"

    def __init__(self, instance_name, *, order, oversampling, raw_mean=None, who=None):
        super().__init__(instance_name, **({} if raw_mean is None else dict(raw_mean=raw_mean)))
        who = who or f"AntiderivativeAntialiasingEqualiser {instance_name}"
        taps, edge_cycles = adaa_equaliser_decision(order, oversampling, who)
        self.kernel = ADAA_KERNELS[order]
        self.order = order
        self.oversampling = oversampling
        self.taps = tuple(taps)
        self.edge_cycles = edge_cycles
        self.length = len(self.taps)
        # the kernel's latency (centred between its inputs), the equaliser (length - 1) / 2 more
        self.latency_steps = self.kernel.latency_steps + (self.length - 1) // 2
        self.latency_samples = self.latency_steps / oversampling
        self.function_name = f"adaa{order}_equaliser_{oversampling}x"

    def response(self, w):
        """The equaliser's own gain at w radians a step (real: linear phase, its delay taken out)."""
        middle = (self.length - 1) // 2
        return self.taps[middle] + sum(2 * self.taps[middle + k] * math.cos(k * w) for k in range(1, middle + 1))

    def small_signal_response(self, w):
        """The kernel times the equaliser at w radians a step: what a straight transfer's signal gets (zero-phase,
        `latency_steps` taken out)."""
        return self.kernel.zero_phase_response(w) * self.response(w)

    def functions(self):
        """{name: GenExpr function}: the equaliser over its last raw means, newest first (none for one tap)."""
        if self.length == 1:
            return {}
        means = [f"m{age}" for age in range(self.length)]
        middle = (self.length - 1) // 2
        terms = [f"{self.taps[age]!r} * ({means[age]} + {means[self.length - 1 - age]})" for age in range(middle)]
        terms.append(f"{self.taps[middle]!r} * {means[middle]}")
        return {self.function_name: f"""// ADAA{self.order}'s equaliser at {self.oversampling}x over its last {self.length} raw means, m0 newest (kit technique: antiderivative antialiasing equaliser)
{self.function_name}({', '.join(means)}) {{
\treturn {' + '.join(terms)};
}}"""}

    def mean_history_names(self):
        """The Histories of the last raw means the equaliser reads, newest first (none for one tap)."""
        return [f"{self.instance_name}_raw_mean_before_{age}" for age in range(1, self.length)]

    def history_declarations(self):
        """["<history>(0)", ...]: for a block that declares them on its own History line."""
        return [f"{name}(0)" for name in self.mean_history_names()]

    def declarations(self):
        declarations = self.history_declarations()
        return f"History {', '.join(declarations)};" if declarations else ""

    def output_expression(self, newest_raw_mean):
        """GenExpr: the equaliser over `newest_raw_mean` and the kept means, `latency_steps` late in all."""
        if self.length == 1:
            return newest_raw_mean
        return f"{self.function_name}({', '.join([newest_raw_mean] + self.mean_history_names())})"

    def remember_statements(self, newest_raw_mean):
        """Statements keeping `newest_raw_mean` as the newest kept mean, the older ones moved along (after
        `output_expression` is used, once a step)."""
        names = self.mean_history_names()
        if not names:
            return ""
        return "".join(f"{names[age]} = {names[age - 1]};\n" for age in range(len(names) - 1, 0, -1)) + \
            f"{names[0]} = {newest_raw_mean};"

    def statements(self):
        """One step on one stream: `<name>_raw_mean` = `raw_mean`, `<name>_out` its equalised output, kept."""
        p = self.instance_name
        if "raw_mean" not in self.input_expressions:
            raise BuildError(f"AntiderivativeAntialiasingEqualiser {p}: made without raw_mean, for use at points "
                             f"(output_expression, remember_statements); it has no statements of its own")
        lines = [f"// {p}: ADAA{self.order}'s equaliser at {self.oversampling}x (kit technique: antiderivative "
                 f"antialiasing equaliser)",
                 self.substituted("${p}_raw_mean = ${raw_mean};"),
                 f"{p}_out = {self.output_expression(f'{p}_raw_mean')};",
                 self.remember_statements(f"{p}_raw_mean")]
        return "\n".join(line for line in lines if line)

    def reset_statements(self):
        """Statements forgetting the kept means."""
        return "\n".join(f"{name} = 0;" for name in self.mean_history_names())

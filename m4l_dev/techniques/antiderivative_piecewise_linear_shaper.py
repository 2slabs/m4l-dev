"""The antiderivative piecewise-linear shaper (a technique): a memoryless transfer made of straight pieces, with
first-order antiderivative antialiasing (ADAA) whose antiderivative is exact, piece by piece, in closed form
(references/dsp.md, "Antiderivative piecewise-linear shaper").

A circuit whose transfer is straight lines between breakpoints (op amps clipping at their rails, diodes taken as ideal
switches: a wavefolder's cells, a limiter) is a table of pieces [(from x, slope, intercept)], the first from -infinity.
Each piece's integral from its start is slope (x^2 - s^2) / 2 + intercept (x - s), so the antiderivative F (from 0) is
closed form: the integral at the piece's start plus that. ADAA1 (Bilbao, Esqueda, Parker & Valimaki 2017) takes the
transfer's exact mean along the straight line between two inputs:

    y = (F(x) - F(x_before)) / (x - x_before)      (where the two are closer than ILL_CONDITIONED_STEP: f at their midpoint)

which is half a sample late. Each comparison tree is balanced (log2 of the pieces deep).

Second order (ADAA2, the same paper's eq. (15), with §II.B's fallbacks (17)-(20)) takes the transfer along the
straight lines through three inputs, convolved with a triangle two samples wide: one sample late, aliases falling
faster (a hot 3 kHz clip at 44.1 kHz: measured in tests/test_techniques.py). Its formula divides differences of the
second antiderivative F2 (a cubic, hundreds at a few volts) by products of input steps, which near a corner and at a
slow input loses every digit. So it is taken piece-wise, where the pieces make it exact and well-conditioned: three
inputs on one piece give that piece's line at their mean (exact: ADAA2 of a line is the line at the mean); across
one corner, the line of the lower piece plus the slope change times ADAA2 of a ramp max(u, 0) in u = x - the corner
(its F2 = u^3 / 6 is as small as the steps); across more, the formula on F2 itself (the inputs then span a whole
piece, so the divisors are not small). A continuous table only (each piece meets the next): the build fails
otherwise.

ADAA2 also filters what it lets through: on a straight piece it is the 3-tap mean (1 + z^-1 + z^-2) / 3, and being
linear in the transfer it puts that on every signal, folded or not: -1.3 dB at 10 kHz, -5.9 dB at 20 kHz at 96 kHz,
-9.5 dB at Nyquist. Bilbao et al. 2017 §IV give the remedy: "Additional linear filtering is one option in this case,
as suggested in [33], [34] for antialiased oscillators"; [34] (Valimaki, Pekonen & Nam 2012, eq. (16)) is "a
post-processing equalizing filter ... a low-order filter, which is independent of the fundamental frequency", a
linear-phase FIR. So the output is the ADAA mean through ADAA's equaliser for its order at the rate it runs at
(the kit's one ADAA equaliser, `AntiderivativeAntialiasingEqualiser` in antiderivative_antialiasing_equaliser.py, also
the tanh saturator's; a block takes its oversampling with no default). At 2x a 5-tap linear-phase FIR (second order: its
product with the 3-tap mean 1 at DC and within +-0.1 dB up to 5/24 of the rate, 20 kHz at 2x 48 kHz, no higher up to
the host's Nyquist; three steps late in all; first order: with the 2-tap mean, +-0.01 dB, 2.5 steps late). Linear and
after the transfer, it lifts a harmonic and an alias at one frequency alike (at 2x an alias re the fundamental rises by
at most +5.8 dB at the edge), and above the host's Nyquist it keeps lifting (+15.9 dB at the 2x Nyquist: what a 2x
instrument's downsampler takes away). At 1x: none (the raw mean; second order one step late, -1.3 dB at 5 kHz, -5.9 dB
at 10 kHz; first order half a step, nothing lifted). At the host's rate an equaliser lifts the top octave, where ADAA2's
mean holds the aliases down; measured 2026-10-20 at 48 kHz, worst alias under 20 kHz re the fundamental, unequalised /
the best 1x equaliser (+-0.3 dB to 8.8 kHz, its response never above +1 dB) / the 2x one: the 259 folder 4 V at 3.1 kHz
-25.3 / -18.6 / -15.5 dB, 8 V at 1.37 kHz -11.0 / -1.4 / +3.5, 4 V at 410 Hz -36.3 / -26.7 / -22.0 (first order -6.3,
-4.0, -30.4); 2sl drums' voice (worst folded line re the loudest kept) FM metal -49.8 / -43.1 / -39.9, ring -52.9 /
-44.0 / -38.3, Fold 8 V at 1.37 kHz -13.5 / -6.4 / -4.9 (references/dsp.md has all ten).
The split the tanh saturator used to use (the line on a filter-free path, ADAA on the rest) is not this: a
folder's rest is mostly the line, so the split's error, (1 - the 3-tap mean) x (the line - the transfer), is the
line's whole size at the input's frequency once it folds.

`PiecewiseLinearTable` is the table and its GenExpr functions (`<name>(x)`, `<name>_integral(x)`,
`<name>_mean(x, x_before, integral, integral_before)`; a continuous table also `<name>_second_order_mean(x,
x_before, x_before_before)`, ADAA2's raw mean, and its helpers). Its function name carries a digest of the pieces, so
two tables (two circuits, or one circuit built two ways) are two functions and can sit in one patch; a circuit module
that runs a mean at several points a sample (an oscillator's sub-samples, a look-ahead probe) uses the table's
expressions directly: for second order, the raw mean at each point and an `AntiderivativeAntialiasingEqualiser` (order 2) over
it and its kept means. `AntiderivativePiecewiseLinearShaper` is the plain use: one signal in, its ADAA1 or ADAA2 mean
equalised for its oversampling out.
"""
import hashlib
import math
from fractions import Fraction

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique
from m4l_dev.generated_numbers import generated_number
from m4l_dev.techniques.antiderivative_antialiasing_equaliser import AntiderivativeAntialiasingEqualiser

# Below this input step the quotient loses digits to the antiderivative's rounding; the midpoint is exact on a
# straight piece and off by at most a corner's worth over a step this short.
ILL_CONDITIONED_STEP = 0.000001
# Where two pieces meet, their lines may differ by rounding (a table measured from a model): more than this (relative
# to the value) is a jump, which second order does not take.
CONTINUITY_TOLERANCE = 1e-9


# shared by every continuous table: ADAA2 of the ramp max(u, 0) through u0 (newest), u1, u2 (eq. (15), fallbacks
# (17)-(20))
SHARED_SECOND_ORDER_FUNCTIONS = {
    "adaa2_ramp_first_integral": """// the ramp max(u, 0)'s first antiderivative (kit technique: antiderivative piecewise-linear shaper)
adaa2_ramp_first_integral(u) {
\treturn u > 0 ? 0.5 * u * u : 0;
}""",
    "adaa2_ramp_second_integral": """// the ramp max(u, 0)'s second antiderivative
adaa2_ramp_second_integral(u) {
\treturn u > 0 ? u * u * u / 6 : 0;
}""",
    "adaa2_ramp_difference": """// the ramp's second antiderivative's difference quotient from b to a (Bilbao et al. 2017 eq. (11), fallback (17))
adaa2_ramp_difference(a, b) {
\treturn abs(a - b) > %(eps)r ? (adaa2_ramp_second_integral(a) - adaa2_ramp_second_integral(b)) / (a - b) : adaa2_ramp_first_integral(0.5 * (a + b));
}""" % {"eps": ILL_CONDITIONED_STEP},
    "adaa2_ramp": """// second-order ADAA of the ramp max(u, 0) through u0 (newest), u1, u2 (Bilbao et al. 2017 eq. (15), fallbacks (18)-(20))
adaa2_ramp(u0, u1, u2) {
\ty = 0;
\tif (abs(u0 - u2) > %(eps)r) {
\t\ty = 2 * (adaa2_ramp_difference(u0, u1) - adaa2_ramp_difference(u1, u2)) / (u0 - u2);
\t} else {
\t\tmiddle = 0.5 * (u0 + u2);
\t\tdelta = middle - u1;
\t\tif (abs(delta) > %(eps)r) {
\t\t\ty = 2 / delta * (adaa2_ramp_first_integral(middle) + (adaa2_ramp_second_integral(u1) - adaa2_ramp_second_integral(middle)) / delta);
\t\t} else {
\t\t\ty = max(0.5 * (middle + u1), 0);
\t\t}
\t}
\treturn y;
}""" % {"eps": ILL_CONDITIONED_STEP},
}


class PiecewiseLinearTable:
    """A transfer as straight pieces: `pieces` is [(from x, slope, intercept)], sorted, the first from -inf. Its
    GenExpr functions are named `<base_name>_<digest of the pieces>`.

    Its numbers go through generated_number (m4l_dev/generated_numbers.py), so the table, its code and its name are
    the same on every machine: the starts, the slopes and the first intercept rounded; a continuous table's other
    intercepts then computed exactly (Fractions) so each piece meets the last where it starts, as given; the
    antiderivatives' constants computed exactly from the pieces. Rounding those too would open gaps at the corners,
    which the ADAA quotients divide by tiny steps."""

    def __init__(self, base_name, pieces):
        if not pieces or pieces[0][0] != -math.inf:
            raise BuildError(f"PiecewiseLinearTable {base_name}: the first piece must start at -inf, got {pieces[:1]}")
        starts = [piece[0] for piece in pieces]
        if starts != sorted(starts) or len(set(starts)) != len(starts):
            raise BuildError(f"PiecewiseLinearTable {base_name}: the pieces must start at rising x, got {starts}")
        if not all(math.isfinite(value) for piece in pieces for value in piece[1:]):
            raise BuildError(f"PiecewiseLinearTable {base_name}: every slope and intercept must be finite")
        self.is_continuous = self._continuous(pieces)
        self.pieces = [(start if start == -math.inf else generated_number(start), generated_number(slope),
                        generated_number(intercept)) for start, slope, intercept in pieces]
        if self.is_continuous:
            for index in range(1, len(self.pieces)):
                (_, left_slope, left_intercept), (start, slope, _) = self.pieces[index - 1], self.pieces[index]
                meeting = Fraction(left_slope) * Fraction(start) + Fraction(left_intercept)
                self.pieces[index] = (start, slope, generated_number(meeting - Fraction(slope) * Fraction(start)))
        self.exact_pieces = [tuple(value if value == -math.inf else Fraction(value) for value in piece)
                             for piece in self.pieces]
        digest = hashlib.sha256(repr(self.pieces).encode()).hexdigest()[:8]
        self.function_name = f"{base_name}_{digest}"

    def value(self, x):
        """The transfer at `x`, in Python."""
        _, slope, intercept = self.pieces[max(i for i, piece in enumerate(self.pieces) if piece[0] <= x)]
        return slope * x + intercept

    def integral(self, x, exact=False):
        """The antiderivative from 0 (closed form per piece), in Python: what the GenExpr integral holds. `exact`:
        from the pieces as Fractions, at a Fraction `x`, exactly."""
        pieces = self.exact_pieces if exact else self.pieces
        total, position = (Fraction(0), Fraction(0)) if exact else (0.0, 0.0)
        direction = 1 if x >= 0 else -1
        while position != x:
            index = max(i for i, piece in enumerate(pieces) if piece[0] <= position) if direction > 0 else \
                max(i for i, piece in enumerate(pieces) if piece[0] < position)
            start, slope, intercept = pieces[index]
            end = pieces[index + 1][0] if index + 1 < len(pieces) else math.inf
            target = min(x, end) if direction > 0 else max(x, start)
            total += slope / 2 * (target * target - position * position) + intercept * (target - position)
            position = target
        return total

    def second_integral(self, x, exact=False):
        """The second antiderivative from 0 (the integral of `integral` from 0), in Python: what the GenExpr second
        integral holds. `exact`: as `integral`'s."""
        pieces = self.exact_pieces if exact else self.pieces
        total, position = (Fraction(0), Fraction(0)) if exact else (0.0, 0.0)
        direction = 1 if x >= 0 else -1
        while position != x:
            index = max(i for i, piece in enumerate(pieces) if piece[0] <= position) if direction > 0 else \
                max(i for i, piece in enumerate(pieces) if piece[0] < position)
            start, slope, intercept = pieces[index]
            end = pieces[index + 1][0] if index + 1 < len(pieces) else math.inf
            target = min(x, end) if direction > 0 else max(x, start)
            total += self._second_integral_over_piece(index, position, target, exact)
            position = target
        return total

    def _second_integral_over_piece(self, index, a, b, exact):
        """The integral of `integral` from a to b, both on piece `index`: F1(a) (b - a) + the piece's own part."""
        _, slope, intercept = (self.exact_pieces if exact else self.pieces)[index]
        width = b - a
        return self.integral(a, exact) * width + slope * ((b * b * b - a * a * a) / 6 - a * a * width / 2) \
            + intercept * width * width / 2

    @staticmethod
    def _continuous(pieces):
        """Every piece meets the next where it starts (to CONTINUITY_TOLERANCE), as given: the table's own pieces,
        rounded by generated_number, may part by that rounding (5e-11 of a piece's terms)."""
        for (_, left_slope, left_intercept), (start, slope, intercept) in zip(pieces, pieces[1:]):
            left, right = left_slope * start + left_intercept, slope * start + intercept
            if abs(left - right) > CONTINUITY_TOLERANCE * max(1.0, abs(left)):
                return False
        return True

    def _tree(self, indices, leaf):
        """A balanced tree of comparisons choosing among the pieces `indices` by x: GenExpr, `leaf(index)` at each."""
        if len(indices) == 1:
            return leaf(indices[0])
        middle = len(indices) // 2
        return (f"(x < {self.pieces[indices[middle]][0]!r} ? {self._tree(indices[:middle], leaf)} : "
                f"{self._tree(indices[middle:], leaf)})")

    @staticmethod
    def _index_tree(indices, leaf):
        """A balanced tree choosing among `indices` by the piece number i: GenExpr, `leaf(index)` at each."""
        if len(indices) == 1:
            return leaf(indices[0])
        middle = len(indices) // 2
        return (f"(i < {indices[middle] - 0.5!r} ? {PiecewiseLinearTable._index_tree(indices[:middle], leaf)} : "
                f"{PiecewiseLinearTable._index_tree(indices[middle:], leaf)})")

    def functions(self):
        """{name: GenExpr function}: the transfer, its antiderivative from 0, the ADAA1 mean between two inputs, and
        (a continuous table) ADAA2 through three."""
        name = self.function_name

        def value(index):
            _, slope, intercept = self.pieces[index]
            return f"({slope!r} * x + {intercept!r})"

        def integral(index):
            start, slope, intercept = self.pieces[index]
            if start == -math.inf:                      # anchor the first piece at its end instead
                start = self.pieces[1][0]
            start, slope, intercept = Fraction(start), Fraction(slope), Fraction(intercept)
            return (f"({generated_number(self.integral(start, exact=True))!r} + {generated_number(slope / 2)!r} * "
                    f"(x * x - {generated_number(start * start)!r}) + {generated_number(intercept)!r} * "
                    f"(x - {generated_number(start)!r}))")
        indices = list(range(len(self.pieces)))
        functions = {
            name: f"""// a piecewise-linear transfer, {len(self.pieces)} straight pieces (kit technique: antiderivative piecewise-linear shaper)
{name}(x) {{
\treturn {self._tree(indices, value)};
}}""",
            f"{name}_integral": f"""// its antiderivative from 0, closed form per piece
{name}_integral(x) {{
\treturn {self._tree(indices, integral)};
}}""",
            f"{name}_mean": f"""// its exact mean along the straight line from x_before to x (first-order ADAA), given the integral at both ends
{name}_mean(x, x_before, integral, integral_before) {{
\tdifference = x - x_before;
\treturn abs(difference) > {ILL_CONDITIONED_STEP!r} ? (integral - integral_before) / difference : {name}(0.5 * (x + x_before));
}}""",
        }
        if self.is_continuous:
            functions.update(self._second_order_functions(indices, integral))
        return functions

    def _second_order_functions(self, indices, integral):
        """{name: GenExpr function}: ADAA2 (the module docstring's piece-wise form) and what it needs."""
        name = self.function_name
        eps = ILL_CONDITIONED_STEP

        def second_integral(index):
            start, slope, intercept = self.pieces[index]
            if start == -math.inf:                      # anchor the first piece at its end instead
                start = self.pieces[1][0]
            start, slope, intercept = Fraction(start), Fraction(slope), Fraction(intercept)
            number = {name: repr(generated_number(value)) for name, value in (
                ("second_integral", self.second_integral(start, exact=True)),
                ("integral", self.integral(start, exact=True)), ("start", start), ("slope", slope),
                ("start_cubed", start * start * start), ("half_start_squared", start * start / 2),
                ("half_intercept", intercept / 2))}
            return (f"({number['second_integral']} + {number['integral']} * (x - {number['start']}) + "
                    f"{number['slope']} * ((x * x * x - {number['start_cubed']}) / 6 - {number['half_start_squared']} * "
                    f"(x - {number['start']})) + {number['half_intercept']} * (x - {number['start']}) * "
                    f"(x - {number['start']}))")
        functions = dict(SHARED_SECOND_ORDER_FUNCTIONS)
        functions.update({
            f"{name}_second_integral": f"""// its second antiderivative from 0, closed form per piece
{name}_second_integral(x) {{
\treturn {self._tree(indices, second_integral)};
}}""",
            f"{name}_piece": f"""// which of its pieces holds x (0 = the first)
{name}_piece(x) {{
\treturn {self._tree(indices, lambda index: repr(float(index)))};
}}""",
            f"{name}_slope_of": f"""// piece i's slope
{name}_slope_of(i) {{
\treturn {self._index_tree(indices, lambda index: repr(self.pieces[index][1]))};
}}""",
            f"{name}_intercept_of": f"""// piece i's intercept
{name}_intercept_of(i) {{
\treturn {self._index_tree(indices, lambda index: repr(self.pieces[index][2]))};
}}""",
            f"{name}_start_of": f"""// where piece i starts (i >= 1)
{name}_start_of(i) {{
\treturn {self._index_tree(indices[1:], lambda index: repr(self.pieces[index][0]))};
}}""",
            f"{name}_difference": f"""// its second antiderivative's difference quotient from b to a (Bilbao et al. 2017 eq. (11), fallback (17))
{name}_difference(a, b) {{
\treturn abs(a - b) > {eps!r} ? ({name}_second_integral(a) - {name}_second_integral(b)) / (a - b) : {name}_integral(0.5 * (a + b));
}}""",
            f"{name}_second_order_mean": f"""// second-order ADAA through x0 (newest), x1, x2: one sample late; piece-wise, so exact on a piece and well-conditioned at a corner
{name}_second_order_mean(x0, x1, x2) {{
\tpiece_0 = {name}_piece(x0);
\tpiece_1 = {name}_piece(x1);
\tpiece_2 = {name}_piece(x2);
\tlowest = min(piece_0, min(piece_1, piece_2));
\thighest = max(piece_0, max(piece_1, piece_2));
\ty = {name}_slope_of(lowest) * (x0 + x1 + x2) / 3 + {name}_intercept_of(lowest);
\tif (highest > lowest + 1.5) {{
\t\tif (abs(x0 - x2) > {eps!r}) {{
\t\t\ty = 2 * ({name}_difference(x0, x1) - {name}_difference(x1, x2)) / (x0 - x2);
\t\t}} else {{
\t\t\tmiddle = 0.5 * (x0 + x2);
\t\t\tdelta = middle - x1;
\t\t\ty = 2 / delta * ({name}_integral(middle) + ({name}_second_integral(x1) - {name}_second_integral(middle)) / delta);
\t\t}}
\t}} else if (highest > lowest + 0.5) {{
\t\tcorner = {name}_start_of(highest);
\t\ty = y + ({name}_slope_of(highest) - {name}_slope_of(lowest)) * adaa2_ramp(x0 - corner, x1 - corner, x2 - corner);
\t}}
\treturn y;
}}""",
        })
        return functions

    def value_call(self, x_expression):
        return f"{self.function_name}({x_expression})"

    def integral_call(self, x_expression):
        return f"{self.function_name}_integral({x_expression})"

    def mean_call(self, x_expression, x_before_expression, integral_expression, integral_before_expression):
        return (f"{self.function_name}_mean({x_expression}, {x_before_expression}, {integral_expression}, "
                f"{integral_before_expression})")

    def second_order_mean_call(self, x_expression, x_before_expression, x_before_before_expression):
        """GenExpr: ADAA2's raw mean through the three inputs (newest first), one sample late; the audio is
        ADAA's equaliser (order 2) over the last of these. A table with a jump fails."""
        if not self.is_continuous:
            raise BuildError(f"PiecewiseLinearTable {self.function_name}: second-order ADAA needs a continuous "
                             f"table, and its pieces jump where they meet")
        return (f"{self.function_name}_second_order_mean({x_expression}, {x_before_expression}, "
                f"{x_before_before_expression})")


class AntiderivativePiecewiseLinearShaper(Technique):
    """`<name>_out`: `input` through `table` (a PiecewiseLinearTable), run at `oversampling` x the host rate (required:
    ADAA's equaliser is decided for its rate; at 2x the instrument runs the marker twice a sample, between its own
    half-band pair): `order` 1, its ADAA1 mean over the step from the last input; `order` 2, ADAA2 through the last
    three inputs (a continuous table); either through its `AntiderivativeAntialiasingEqualiser`, `latency_steps` late in
    all. State: the last inputs (first order, the last antiderivative), the equaliser's last raw means."""

    def __init__(self, instance_name, *, input, table, oversampling, order=1):
        super().__init__(instance_name, input=input)
        who = f"AntiderivativePiecewiseLinearShaper {instance_name}"
        if not isinstance(table, PiecewiseLinearTable):
            raise BuildError(f"{who}: table must be a PiecewiseLinearTable, got {table!r}")
        if order not in (1, 2):
            raise BuildError(f"{who}: order is 1 or 2, got {order!r}")
        if order == 2 and not table.is_continuous:
            raise BuildError(f"{who}: second order needs a continuous table")
        self.table = table
        self.order = order
        self.oversampling = oversampling
        self.equaliser = AntiderivativeAntialiasingEqualiser(f"{instance_name}_equaliser",
                                                             raw_mean=f"{instance_name}_raw_mean", order=order,
                                                             oversampling=oversampling, who=who)
        # late by the ADAA mean's (first order half a step, second one) and its equaliser's: in its steps (the
        # instrument's alignments) and in host samples
        self.latency_steps = self.equaliser.latency_steps
        self.latency_samples = self.equaliser.latency_samples

    def functions(self):
        functions = dict(self.table.functions())
        functions.update(self.equaliser.functions())
        return functions

    def declarations(self):
        p = self.instance_name
        state = [f"{p}_input_before(0)", f"{p}_input_before_before(0)" if self.order == 2 else f"{p}_integral_before(0)"]
        return "\n".join(declaration for declaration in (f"History {', '.join(state)};",
                                                         self.equaliser.declarations()) if declaration)

    def statements(self):
        p = self.instance_name
        if self.order == 2:
            return self.substituted("""// ${p}: a piecewise-linear transfer, second-order ADAA, equalised for its rate (kit technique: antiderivative piecewise-linear shaper)
${p}_input = ${input};
${p}_raw_mean = """) + self.table.second_order_mean_call(f"{p}_input", f"{p}_input_before",
                                                        f"{p}_input_before_before") + ";\n" + \
                self.equaliser.statements() + f"\n{p}_out = {p}_equaliser_out;\n" + self.substituted("""${p}_input_before_before = ${p}_input_before;
${p}_input_before = ${p}_input;""")
        return self.substituted("""// ${p}: a piecewise-linear transfer, first-order ADAA, equalised for its rate (kit technique: antiderivative piecewise-linear shaper)
${p}_input = ${input};
${p}_integral = """) + self.table.integral_call(f"{p}_input") + ";\n" + f"{p}_raw_mean = " + self.table.mean_call(
            f"{p}_input", f"{p}_input_before", f"{p}_integral", f"{p}_integral_before") + ";\n" + \
            self.equaliser.statements() + f"\n{p}_out = {p}_equaliser_out;\n" + self.substituted("""${p}_input_before = ${p}_input;
${p}_integral_before = ${p}_integral;""")

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

`PiecewiseLinearTable` is the table and its three GenExpr functions (`<name>(x)`, `<name>_integral(x)`,
`<name>_mean(x, x_before, integral, integral_before)`). Its function name carries a digest of the pieces, so two
tables (two circuits, or one circuit built two ways) are two functions and can sit in one patch; a circuit module
that runs the mean at several points a sample (an oscillator's sub-samples, a look-ahead probe) uses the table's
expressions directly. `AntiderivativePiecewiseLinearShaper` is the plain use: one signal in, its ADAA1 mean out.
"""
import hashlib
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import Technique

# Below this input step the quotient loses digits to the antiderivative's rounding; the midpoint is exact on a
# straight piece and off by at most a corner's worth over a step this short.
ILL_CONDITIONED_STEP = 0.000001


class PiecewiseLinearTable:
    """A transfer as straight pieces: `pieces` is [(from x, slope, intercept)], sorted, the first from -inf. Its
    GenExpr functions are named `<base_name>_<digest of the pieces>`."""

    def __init__(self, base_name, pieces):
        if not pieces or pieces[0][0] != -math.inf:
            raise BuildError(f"PiecewiseLinearTable {base_name}: the first piece must start at -inf, got {pieces[:1]}")
        starts = [piece[0] for piece in pieces]
        if starts != sorted(starts) or len(set(starts)) != len(starts):
            raise BuildError(f"PiecewiseLinearTable {base_name}: the pieces must start at rising x, got {starts}")
        if not all(math.isfinite(value) for piece in pieces for value in piece[1:]):
            raise BuildError(f"PiecewiseLinearTable {base_name}: every slope and intercept must be finite")
        self.pieces = list(pieces)
        digest = hashlib.sha256(repr(self.pieces).encode()).hexdigest()[:8]
        self.function_name = f"{base_name}_{digest}"

    def value(self, x):
        """The transfer at `x`, in Python."""
        _, slope, intercept = self.pieces[max(i for i, piece in enumerate(self.pieces) if piece[0] <= x)]
        return slope * x + intercept

    def integral(self, x):
        """The antiderivative from 0 (closed form per piece), in Python: what the GenExpr integral holds."""
        total, position = 0.0, 0.0
        direction = 1 if x >= 0 else -1
        while position != x:
            index = max(i for i, piece in enumerate(self.pieces) if piece[0] <= position) if direction > 0 else \
                max(i for i, piece in enumerate(self.pieces) if piece[0] < position)
            start, slope, intercept = self.pieces[index]
            end = self.pieces[index + 1][0] if index + 1 < len(self.pieces) else math.inf
            target = min(x, end) if direction > 0 else max(x, start)
            total += slope / 2 * (target * target - position * position) + intercept * (target - position)
            position = target
        return total

    def _tree(self, indices, leaf):
        """A balanced tree of comparisons choosing among the pieces `indices` by x: GenExpr, `leaf(index)` at each."""
        if len(indices) == 1:
            return leaf(indices[0])
        middle = len(indices) // 2
        return (f"(x < {self.pieces[indices[middle]][0]!r} ? {self._tree(indices[:middle], leaf)} : "
                f"{self._tree(indices[middle:], leaf)})")

    def functions(self):
        """{name: GenExpr function}: the transfer, its antiderivative from 0, and the ADAA1 mean between two inputs."""
        name = self.function_name

        def value(index):
            _, slope, intercept = self.pieces[index]
            return f"({slope!r} * x + {intercept!r})"

        def integral(index):
            start, slope, intercept = self.pieces[index]
            if start == -math.inf:                      # anchor the first piece at its end instead
                start = self.pieces[1][0]
            return (f"({self.integral(start)!r} + {slope / 2!r} * (x * x - {start * start!r}) + "
                    f"{intercept!r} * (x - {start!r}))")
        indices = list(range(len(self.pieces)))
        return {
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

    def value_call(self, x_expression):
        return f"{self.function_name}({x_expression})"

    def integral_call(self, x_expression):
        return f"{self.function_name}_integral({x_expression})"

    def mean_call(self, x_expression, x_before_expression, integral_expression, integral_before_expression):
        return (f"{self.function_name}_mean({x_expression}, {x_before_expression}, {integral_expression}, "
                f"{integral_before_expression})")


class AntiderivativePiecewiseLinearShaper(Technique):
    """`<name>_out`: `input` through `table` (a PiecewiseLinearTable), its ADAA1 mean over the step from the last
    sample's input: half a sample late. State: the last input and its antiderivative."""

    def __init__(self, instance_name, *, input, table):
        super().__init__(instance_name, input=input)
        if not isinstance(table, PiecewiseLinearTable):
            raise BuildError(f"AntiderivativePiecewiseLinearShaper {instance_name}: table must be a "
                             f"PiecewiseLinearTable, got {table!r}")
        self.table = table

    def functions(self):
        return self.table.functions()

    def declarations(self):
        return self.substituted("History ${p}_input_before(0), ${p}_integral_before(0);")

    def statements(self):
        p = self.instance_name
        return self.substituted("""// ${p}: a piecewise-linear transfer, first-order ADAA (kit technique: antiderivative piecewise-linear shaper)
${p}_input = ${input};
${p}_integral = """) + self.table.integral_call(f"{p}_input") + ";\n" + f"{p}_out = " + self.table.mean_call(
            f"{p}_input", f"{p}_input_before", f"{p}_integral", f"{p}_integral_before") + self.substituted(""";
${p}_input_before = ${p}_input;
${p}_integral_before = ${p}_integral;""")

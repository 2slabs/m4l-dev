"""The Buchla 259's timbre section (a circuit module): sheet 3A "Symmetry + Timbre" of the original (rev 11/78), from
the drive stage to the folder's output (references/circuits/buchla-259.md §1, §3).

    the sine -> IC29, the drive stage (a JFET VCA whose gain Timbre sets; R215 33k || C22 470 pF: ~10.3 kHz)
             + Symmetry's offset (through Q10, which Timbre's gate voltage opens)
             -> the folder bus -> five CA3160 folding cells on their own +-6 V rails, in parallel with a dry path
             -> the two summers (IC31b, IC31a) with the zener-bridge limiter -> the folder's output
             (IC31a's R245 1.2M || C24 100 pF: the fixed 1.33 kHz tone filter, TONE_FILTER_HZ)

The cells (Esqueda, Pontynen, Parker & Bilbao, DAFx-17, eqs. 6-11, Table 1 = the sheet's resistors): each an inverting
CA3160 (gain -Rk2/Rk1) on the cells' rails; while its output is inside the rail it holds its summing node at 0 V (the
deadband); past |Vin| = (Rk1/Rk2) Vs it clips at the rail and the node follows the input. So every fold is a rail
clip, and the rail voltage Vs moves every fold point (the character's `cell_rail_volts`: 6 V is the CA3160 original,
about 4.5 V Theelen's TL072 build). The original's extras where the drive is hot (§3.2): a cell's summing node cannot
go more than 0.5 V under its negative rail (the CA3160's input range, its gate protection to V-; only cell 1 gets
there, below about -8.4 V in: one-sided), and the output limiter (a 3.9 V zener in a diode bridge, about +-5.1 V),
taken here on the sum before the tone filter (where §3.2 derives its 10.5 V onset).

The transfer is straight pieces (every cell's fold point, where a node meets its floor, where the sum meets the
limiter): the kit's antiderivative piecewise-linear shaper (a technique) holds it, so the folder is antialiased by
second-order ADAA, piece-wise exact, and the kit's ADAA equaliser for second order at the unit's `oversampling` after
it (`AntiderivativeAntialiasingEqualiser`, order 2; a wiring choice, required: at 2x its 3-tap mean undone to within +-0.1 dB up to 20 kHz at 2x 48 kHz, three steps late in all;
at 1x none, one step late, -5.9 dB at 10 kHz at 48 kHz, the technique's measurements). Measured on a pure sine at 2x 48 kHz,
the worst alias under 20 kHz re the fundamental (tests/test_circuit_module_buchla_259_timbre_section.py), first order
-> second (raw) -> second equalised: 4 V at 3.1 kHz -22.3 -> -36.4 -> -31.5 dB, 8 V at 1.37 kHz -33.7 -> -48.7 -> -45.8
dB, 4 V at 410 Hz -55.8 -> -69.8 -> -65.9 dB (the trivial folder: -3.5, -16.5, -41.8 dB); the equaliser lifts an alias
as it lifts the harmonics at its frequency, so they keep their ratio. At 1x 48 kHz, first order -> second: -6.3 ->
-25.3, -4.0 -> -11.0, -30.4 -> -36.3 dB.

Inputs (volts and Hz, per host sample): `drive_volts`, the sine's peak at the folder bus that Timbre sets (DAFx-17
sweeps 0-10 V; the original's maximum is a factory trim, §3.3); `symmetry_offset_volts`, the DC that Symmetry puts on
the bus through Q10 (§2.3: about -0.09 x the Symmetry node, opened by Timbre; no source gives Q10's law, so the
instrument says how it opens); `frequency_hz`, the sine's frequency, at which the drive stage's roll-off is taken as a
gain (its phase lag only shifts a static folder's output in time). The sine itself is given at each point the
instrument evaluates the folder (`point_statements`).

Outputs: the folder's output in volts at a point, second-order ADAA through it and the instance's last two points,
through its oversampling's equaliser (`output_statements(point)`, then `output_volts_at(point)`: the folder
`latency_steps` steps late, 3 at 2x, 1 at 1x; the audio's); the folder's exact mean over a
segment between two points (`segment_output_volts`: first order, for a probe of the output's mean); `output_peak_volts`, about where
the sum sits for drives of 0.6-10 V (3.2 V at 6 V rails, scaling with them), for an instrument that scales it to its
own level. `statements()` (per host sample) latches the inputs and the drive stage's gain; the instance's own
History `<name>_before_*` and `<name>_before_before_*` are its last two points' inputs and `<name>_equaliser_raw_mean_before_*` its
last raw ADAA2 means (`remember_statements`), for an instrument that runs the folder on consecutive sub-samples.

The rail at run time (`character_inputs={"cell_rail_volts": ...}`, volts, within RUNTIME_CELL_RAIL_VOLTS: the
CA3160's operating supply, 5-16 V across its two pins, so +-2.5 to +-8 V; the instrument keeps it there, and a unit
whose rail moves fails the build if its range isn't inside it): what scales with the rail moves with it, every cell's
fold point (Rk1/Rk2) Vs and the node floor, -(Vs + 0.5 V); what is fixed in volts stays, the limiter's +-5.1 V (a
zener and two diodes) and the 0.5 V under the rail (the CA3160's input range), and so do the inputs (the drive and
Symmetry's offset, the instrument's volts). Over that range the transfer keeps its pieces in one order, their slopes
fixed and their starts and intercepts in proportion to the rail (the limiter's crossings too: they lie on pieces whose
intercepts move so); the build measures that motion at the range's ends, checks it against the model across it, and
the table moves by it (the shaper's `PiecewiseLinearMotion`), the shift the rail less the character's. At the
character's rail the code computes the numbers' unit to the bit. ADAA2 needs no smoothing of it: each mean is taken on
the table of its own call (no antiderivative kept across samples), so the output moves with the rail as the transfer
does; a jump in the rail is a jump in the transfer, as in the drive. `first_fold_volts` and `output_peak_volts` stay
the character's (an instrument's fixed scaling).

Not modelled (§4.3): slew (above several kHz at high Timbre), the JFET VCA's own nonlinearity, the limiter's soft knee
at low zener current, the 1.45 Hz DC block inside IC31a's summer. The tone filter (TONE_FILTER_HZ) is the folder
output's own: IC31a's feedback, before the Order crossfade and the AM (sheet 4A, references/circuits/buchla-259.md
§2.2). An instrument runs it on each unit's folder output, before anything it mixes in or multiplies by: on a sum of
units it would also darken whatever else is in that sum (2sl gate until 0.6.1: its blend waves and AM).
"""
import dataclasses
import functools
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.generated_numbers import generated_number
from m4l_dev.techniques.antiderivative_antialiasing_equaliser import AntiderivativeAntialiasingEqualiser
from m4l_dev.techniques.antiderivative_piecewise_linear_shaper import PiecewiseLinearMotion, PiecewiseLinearTable

# sheet 3A = DAFx-17 Table 1: (Rk1 in, Rk2 feedback, Rk3 to the summer), cells 1-5
CELL_RESISTORS = [
    (10e3, 100e3, 100e3),        # R238, R239, R240
    (49.9e3, 100e3, 43.2e3),     # R234, R235, R236
    (91e3, 100e3, 56e3),         # R230, R231, R232
    (30e3, 100e3, 68e3),         # R226, R227, R228
    (68e3, 100e3, 33e3),         # R222, R223, R224
]
DRY_RESISTOR = 240e3                                       # R220 (DAFx R6,3)
R7, RF1, RF2, TONE_CAPACITOR = 24.9e3, 24.9e3, 1.2e6, 100e-12   # R243, R242, R245, C24
CELLS_INTO_THE_LOWER_SUMMER = (3, 4)                       # cells 4 and 5 (0-based) go through IC31b (eq. 10)
DRIVE_STAGE_HZ = generated_number(1.0 / (2 * math.pi * 33e3 * 470e-12))     # IC29's R215 || C22: ~10.26 kHz
TONE_FILTER_HZ = generated_number(1.0 / (2 * math.pi * RF2 * TONE_CAPACITOR))   # RF2 x C: the circuit's 1.33 kHz one-pole
OUTPUT_PEAK_VOLTS_AT_6_VOLT_RAILS = 3.2                    # the sum's peak for drives of 0.6-10 V (DAFx-17's sweep)
LIMITER_OPEN_VOLTS = 1e3                                   # the outermost pieces are measured out to here
# The rail a unit may move to at run time (volts, each side): the CA3160's operating supply, 5 to 16 V across V+ and V-
# (Intersil FN976.4; circuit §3.1)
RUNTIME_CELL_RAIL_VOLTS = (2.5, 8.0)
# Rails between the range's ends where the build checks the moving table against the model
RAIL_MOTION_CHECKS = 12
# How far the moved folder may be from the model at a checked rail (volts out)
RAIL_MOTION_TOLERANCE_VOLTS = 1e-8


@dataclasses.dataclass(frozen=True)
class Buchla259TimbreSectionCharacter:
    """One unit's build character; the defaults are the CA3160 original (sheet 3A, rev 11/78)."""
    cell_rail_volts: float = 6.0                     # IC32's buffered divider: 15 V x 10k / 25k (§3.1)
    cell_node_floor_under_rail_volts: float = 0.5    # CA3160 input range: down to V- - 0.5 V (§3.2)
    limiter_zener_volts: float = 3.9                 # the 1N5228 in IC31a's bridge
    limiter_diode_volts: float = 0.6                 # each of the bridge's two conducting diodes

    @property
    def limiter_volts(self):
        """The limiter's clamp: the zener and two bridge diodes, about +-5.1 V."""
        return self.limiter_zener_volts + 2 * self.limiter_diode_volts


def cell_fold_point_volts(cell, character):
    """The input voltage where cell `cell` (0-based) clips at its rail: (Rk1/Rk2) Vs (DAFx-17 eq. 8)."""
    r1, r2, _ = CELL_RESISTORS[cell]
    return r1 / r2 * character.cell_rail_volts


def cell_node_volts(cell, x, character):
    """Cell `cell`'s summing node Vk at input `x` volts: DAFx-17 eq. 9, then the node's floor under the rail."""
    r1, r2, r3 = CELL_RESISTORS[cell]
    if abs(x) <= cell_fold_point_volts(cell, character):
        node = 0.0
    else:
        node = r3 * (r2 * x - math.copysign(1.0, x) * r1 * character.cell_rail_volts) / (r1 * r3 + r2 * r3 + r1 * r2)
    return max(node, -(character.cell_rail_volts + character.cell_node_floor_under_rail_volts))


def summed_output_volts_unlimited(x, character):
    """The summed output V'out (volts) before the limiter: DAFx-17 eqs. 10-11."""
    lower = -RF1 * (sum(cell_node_volts(k, x, character) / CELL_RESISTORS[k][2] for k in CELLS_INTO_THE_LOWER_SUMMER)
                    + x / DRY_RESISTOR)
    upper = sum(cell_node_volts(k, x, character) / CELL_RESISTORS[k][2] for k in range(len(CELL_RESISTORS))
                if k not in CELLS_INTO_THE_LOWER_SUMMER)
    return -RF2 * (upper + lower / R7)


def output_volts(x, character):
    """The folder's output (volts) at input `x` volts, in Python (the circuit model the transfer's pieces are taken
    from)."""
    return min(max(summed_output_volts_unlimited(x, character), -character.limiter_volts), character.limiter_volts)


def _breakpoints(character):
    """Every input where the folder's slope changes: the cells' fold points, where a node meets its floor, and where
    the sum meets the limiter."""
    floor = -(character.cell_rail_volts + character.cell_node_floor_under_rail_volts)
    points = set()
    for cell, (r1, r2, r3) in enumerate(CELL_RESISTORS):
        threshold = cell_fold_point_volts(cell, character)
        points |= {threshold, -threshold}
        # under -threshold the node is r3 (r2 x + r1 Vs) / D: it meets the floor at
        points.add((floor * (r1 * r3 + r2 * r3 + r1 * r2) / r3 - r1 * character.cell_rail_volts) / r2)
    unlimited = sorted(points)
    edges = [-LIMITER_OPEN_VOLTS] + unlimited + [LIMITER_OPEN_VOLTS]
    for low, high in zip(edges, edges[1:]):
        # the sum is straight between two of its breakpoints: where it meets the limiter, by the line through two
        # points just inside them
        inside_low, inside_high = low + 1e-9 * (high - low), high - 1e-9 * (high - low)
        y_low = summed_output_volts_unlimited(inside_low, character)
        y_high = summed_output_volts_unlimited(inside_high, character)
        for limit in (character.limiter_volts, -character.limiter_volts):
            if (y_low - limit) * (y_high - limit) < 0:
                points.add(inside_low + (limit - y_low) / (y_high - y_low) * (inside_high - inside_low))
    return sorted(points)


def transfer_pieces(character):
    """The folder as straight pieces: [(from x, slope, intercept)], the first from -infinity (each piece measured at
    its inner thirds, so a breakpoint's rounding never leaks into a slope)."""
    breakpoints = _breakpoints(character)
    starts = [-math.inf] + breakpoints
    ends = breakpoints + [math.inf]
    pieces = []
    for start, end in zip(starts, ends):
        low = end - 2.0 if start == -math.inf else start
        high = start + 2.0 if end == math.inf else end
        a, b = low + (high - low) / 3, low + 2 * (high - low) / 3
        slope = (output_volts(b, character) - output_volts(a, character)) / (b - a)
        pieces.append((start, slope, output_volts(a, character) - slope * a))
    return pieces


def _pieces_value(pieces, x):
    """The transfer `pieces` [(from x, slope, intercept)] at `x`."""
    _, slope, intercept = pieces[max(i for i, piece in enumerate(pieces) if piece[0] <= x)]
    return slope * x + intercept


@functools.lru_cache(maxsize=None)
def rail_motion(character):
    """The transfer's motion with the rail across RUNTIME_CELL_RAIL_VOLTS, about `character`'s: (start rates,
    intercept rates) per piece, volts a volt of rail, measured from the model at the range's ends (the same pieces and
    slopes there) and checked against it at RAIL_MOTION_CHECKS rails between: the moved table's transfer is the
    model's, at every breakpoint of either and between. (Under the limiter, where the transfer is flat, the sum's own
    breakpoints change order with the rail: those are no corners of the transfer, and move with the next corner.)
    Fails the build where the model doesn't move so."""
    low, high = RUNTIME_CELL_RAIL_VOLTS
    at = {rail: transfer_pieces(dataclasses.replace(character, cell_rail_volts=rail)) for rail in (low, high)}
    nominal = transfer_pieces(character)
    if not all(len(pieces) == len(nominal) and all(abs(a[1] - b[1]) <= 1e-9 * max(1.0, abs(b[1]))
                                                     for a, b in zip(pieces, nominal)) for pieces in at.values()):
        raise BuildError(f"Buchla259TimbreSection: the folder's pieces change across the rail's run-time range "
                         f"{RUNTIME_CELL_RAIL_VOLTS}: its table can't move with the rail")
    start_rates = [0.0] + [(b[0] - a[0]) / (high - low) for a, b in zip(at[low][1:], at[high][1:])]
    intercept_rates = [(b[2] - a[2]) / (high - low) for a, b in zip(at[low], at[high])]
    # a breakpoint inside a straight run (under the limiter: the same line on both sides) is no corner of the
    # transfer, and its place between the ends need not be in proportion: it moves with the next corner up (or the
    # last one, at the top), so the run keeps its order and stays inside the straight run
    def same_line(index):
        (_, left_slope, left_intercept), (_, slope, intercept) = nominal[index - 1], nominal[index]
        return abs(left_slope - slope) <= 1e-9 * max(1.0, abs(slope)) and \
            abs(left_intercept - intercept) <= 1e-9 * max(1.0, abs(intercept))
    corners = [index for index in range(1, len(nominal)) if not same_line(index)]
    for index in range(1, len(nominal)):
        if index not in corners:
            start_rates[index] = start_rates[min((c for c in corners if c > index), default=max(corners))]
    for check in range(1, RAIL_MOTION_CHECKS + 1):
        rail = low + (high - low) * check / (RAIL_MOTION_CHECKS + 1)
        shift = rail - character.cell_rail_volts
        model = dataclasses.replace(character, cell_rail_volts=rail)
        moved = [(start + start_rate * shift, slope, intercept + intercept_rate * shift)
                 for (start, slope, intercept), start_rate, intercept_rate
                 in zip(nominal, start_rates, intercept_rates)]
        corners = [piece[0] for piece in moved[1:]] + _breakpoints(model)
        points = [corner + nudge for corner in corners for nudge in (-1e-6, 0.0, 1e-6)] + \
            [x / 4 for x in range(-200, 201)]
        error, where = max((abs(_pieces_value(moved, x) - output_volts(x, model)), x) for x in points)
        if error > RAIL_MOTION_TOLERANCE_VOLTS:
            raise BuildError(f"Buchla259TimbreSection: at a {rail:g} V rail the moved folder is {error:g} V off the "
                             f"model at {where:g} V in: its table can't move with the rail")
    return tuple(start_rates), tuple(intercept_rates)


class Buchla259TimbreSection(CircuitModule):
    """The folder's output (volts) at the points an instrument evaluates it: `point_statements(point, sine)` leaves
    `<point>_folder_input_volts` and `<point>_folder_integral`; `output_statements(point)` then
    `output_volts_at(point)` is the output there by second-order ADAA, equalised, `latency_steps` late; `segment_output_volts(point, before)` is the output's exact mean from point
    `before` to `point`. Inputs `drive_volts`, `symmetry_offset_volts`, `frequency_hz` (per host sample, latched by
    `statements()`); the rail at run time by `character_inputs`. See the module's docstring."""

    references_entry = "references/circuits/buchla-259.md"
    character_type = Buchla259TimbreSectionCharacter
    runtime_character_fields = ("cell_rail_volts",)

    def __init__(self, instance_name, *, drive_volts, symmetry_offset_volts, frequency_hz, oversampling,
                 character=None, character_inputs=None):
        super().__init__(instance_name, character=character, character_inputs=character_inputs,
                         drive_volts=drive_volts, symmetry_offset_volts=symmetry_offset_volts,
                         frequency_hz=frequency_hz)
        if not 0 < self.character.cell_rail_volts:
            raise BuildError(f"Buchla259TimbreSection {instance_name}: the cells' rail must be above 0 V, got "
                             f"{self.character.cell_rail_volts!r}")
        self.rail_moves = "cell_rail_volts" in self.character_inputs
        motion = None
        if self.rail_moves:
            low, high = RUNTIME_CELL_RAIL_VOLTS
            if not low <= self.character.cell_rail_volts <= high:
                raise BuildError(f"Buchla259TimbreSection {instance_name}: a rail that moves at run time moves about "
                                 f"the character's, which must be in {RUNTIME_CELL_RAIL_VOLTS}, got "
                                 f"{self.character.cell_rail_volts!r}")
            start_rates, intercept_rates = rail_motion(self.character)
            motion = PiecewiseLinearMotion(
                shift=f"{instance_name}_cell_rail_shift_volts", start_rates=start_rates,
                intercept_rates=intercept_rates,
                shift_range=(low - self.character.cell_rail_volts, high - self.character.cell_rail_volts))
        self.table = PiecewiseLinearTable("buchla_259_folder", transfer_pieces(self.character), motion=motion)
        # the points a host sample (a wiring choice, required: ADAA2's equaliser is designed for the rate it runs at)
        self.oversampling = oversampling
        self.equaliser = AntiderivativeAntialiasingEqualiser(f"{instance_name}_equaliser", order=2,
                                                             oversampling=oversampling,
                                                             who=f"Buchla259TimbreSection {instance_name}")
        # output_volts_at: ADAA2 centred on the point before, then the equaliser for this oversampling
        self.latency_steps = self.equaliser.latency_steps
        self.latency_samples = self.equaliser.latency_samples
        self._points_with_output = set()        # output_statements wrote these points' outputs

    @property
    def first_fold_volts(self):
        """The drive where the first fold starts (cell 1's fold point): below it the output is the sine, scaled."""
        return cell_fold_point_volts(0, self.character)

    @property
    def output_peak_volts(self):
        """About where the output peaks for drives of 0.6-10 V: 3.2 V at 6 V rails, scaling with them."""
        return generated_number(OUTPUT_PEAK_VOLTS_AT_6_VOLT_RAILS * self.character.cell_rail_volts / 6.0)

    @property
    def running_point(self):
        """The prefix of the instance's own last point (`<name>_before`): the `before` of a running segment."""
        return f"{self.instance_name}_before"

    def functions(self):
        functions = dict(self.table.functions())
        functions.update(self.equaliser.functions())
        return functions

    def declarations(self):
        return self.substituted("History ${p}_before_folder_input_volts(0), "
                                "${p}_before_before_folder_input_volts(0)") + \
            "".join(f", {declaration}" for declaration in self.equaliser.history_declarations()) + ";"

    def statements(self):
        return self.substituted("""// ${p}: the Buchla 259's timbre section, its inputs this sample (kit circuit module: Buchla 259 timbre section)
${p}_drive_volts = ${drive_volts};
${p}_drive_stage_gain = 1 / sqrt(1 + pow(${frequency_hz} / ${drive_stage_hz}, 2));
${p}_symmetry_offset_volts = ${symmetry_offset_volts};""", drive_stage_hz=DRIVE_STAGE_HZ) + (
            f"\n{self.instance_name}_cell_rail_shift_volts = {self.character_term('cell_rail_volts')} - "
            f"{self.character.cell_rail_volts!r};" if self.rail_moves else "")

    def point_statements(self, point, sine):
        """At one point: the folder bus (the drive stage's sine and Symmetry's offset) and the folder's antiderivative
        there. `sine` is the principal oscillator's sine at the point (-1..1)."""
        p = self.instance_name
        return (f"{point}_folder_input_volts = {p}_drive_volts * {p}_drive_stage_gain * {sine} + "
                f"{p}_symmetry_offset_volts;\n"
                f"{point}_folder_integral = {self.table.integral_call(f'{point}_folder_input_volts')};")

    def output_statements(self, point):
        """At `point` (it ran `point_statements`): ADAA2's raw mean through it and the instance's last two points,
        and the equaliser over it and the last four (`<point>_folder_output_volts`, what `output_volts_at` gives).
        Then `remember_statements(point)`."""
        p = self.instance_name
        self._points_with_output.add(point)
        raw_mean = self.table.second_order_mean_call(f"{point}_folder_input_volts", f"{p}_before_folder_input_volts",
                                                     f"{p}_before_before_folder_input_volts")
        return (f"{point}_folder_raw_mean = {raw_mean};\n"
                f"{point}_folder_output_volts = "
                f"{self.equaliser.output_expression(f'{point}_folder_raw_mean')};")

    def output_volts_at(self, point):
        """GenExpr: the folder's output (volts) at `point`, `latency_steps` steps late: what
        `output_statements(point)` wrote (it must come first: the build fails otherwise)."""
        if point not in self._points_with_output:
            raise BuildError(f"Buchla259TimbreSection {self.instance_name}: output_volts_at({point!r}) before "
                             f"output_statements({point!r})")
        return f"{point}_folder_output_volts"

    def segment_output_volts(self, point, before):
        """GenExpr: the folder's output (volts), its exact mean over the segment from point `before` to `point` (both
        ran `point_statements`, or `before` is `running_point`): first-order ADAA, for a probe of the output's mean.
        The running point's antiderivative is taken again here, on this sample's table (a moving rail's: never one
        kept from a sample before)."""
        before_integral = (self.table.integral_call(f"{before}_folder_input_volts") if before == self.running_point
                           else f"{before}_folder_integral")
        return self.table.mean_call(f"{point}_folder_input_volts", f"{before}_folder_input_volts",
                                    f"{point}_folder_integral", before_integral)

    def remember_statements(self, point):
        """Make `point` the instance's last point (`running_point`), the one before it the last but one, and its raw
        mean the newest kept (`output_statements(point)` must come first: the build fails otherwise)."""
        p = self.instance_name
        if point not in self._points_with_output:
            raise BuildError(f"Buchla259TimbreSection {self.instance_name}: remember_statements({point!r}) before "
                             f"output_statements({point!r}): the equaliser's raw means would skip a point")
        lines = [self.equaliser.remember_statements(f"{point}_folder_raw_mean"),
                 f"{p}_before_before_folder_input_volts = {p}_before_folder_input_volts;",
                 f"{p}_before_folder_input_volts = {point}_folder_input_volts;"]
        return "\n".join(line for line in lines if line)

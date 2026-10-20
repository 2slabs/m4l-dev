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
second-order ADAA (one step late), piece-wise exact. Measured on a pure sine at 2x 48 kHz, the worst alias under
20 kHz re the fundamental (tests/test_circuit_module_buchla_259_timbre_section.py), first order -> second: 4 V at
3.1 kHz -22.3 -> -36.4 dB, 8 V at 1.37 kHz -33.7 -> -48.7 dB, 4 V at 410 Hz -55.8 -> -69.8 dB (the trivial folder:
-3.5, -16.5, -41.8 dB).

Inputs (volts and Hz, per host sample): `drive_volts`, the sine's peak at the folder bus that Timbre sets (DAFx-17
sweeps 0-10 V; the original's maximum is a factory trim, §3.3); `symmetry_offset_volts`, the DC that Symmetry puts on
the bus through Q10 (§2.3: about -0.09 x the Symmetry node, opened by Timbre; no source gives Q10's law, so the
instrument says how it opens); `frequency_hz`, the sine's frequency, at which the drive stage's roll-off is taken as a
gain (its phase lag only shifts a static folder's output in time). The sine itself is given at each point the
instrument evaluates the folder (`point_statements`).

Outputs: the folder's output in volts at a point, second-order ADAA through it and the instance's last two points
(`output_volts_at(point)`: the folder one step late; the audio's); the folder's exact mean over a segment between
two points (`segment_output_volts`: first order, for a probe of the output's mean); `output_peak_volts`, about where
the sum sits for drives of 0.6-10 V (3.2 V at 6 V rails, scaling with them), for an instrument that scales it to its
own level. `statements()` (per host sample) latches the inputs and the drive stage's gain; the instance's own
History `<name>_before_*` and `<name>_before_before_*` are its last two points (`remember_statements`), for an
instrument that runs the folder on consecutive sub-samples.

Not modelled (§4.3): slew (above several kHz at high Timbre), the JFET VCA's own nonlinearity, the limiter's soft knee
at low zener current, the 1.45 Hz DC block inside IC31a's summer. The tone filter is linear and fixed: an instrument
that sums several units may run it once on their sum (TONE_FILTER_HZ).
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.antiderivative_piecewise_linear_shaper import PiecewiseLinearTable

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
DRIVE_STAGE_HZ = 1.0 / (2 * math.pi * 33e3 * 470e-12)     # IC29's R215 || C22: ~10.26 kHz
TONE_FILTER_HZ = 1.0 / (2 * math.pi * RF2 * TONE_CAPACITOR)   # RF2 x C: the circuit's 1.33 kHz one-pole
OUTPUT_PEAK_VOLTS_AT_6_VOLT_RAILS = 3.2                    # the sum's peak for drives of 0.6-10 V (DAFx-17's sweep)
LIMITER_OPEN_VOLTS = 1e3                                   # the outermost pieces are measured out to here


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


class Buchla259TimbreSection(CircuitModule):
    """The folder's output (volts) at the points an instrument evaluates it: `point_statements(point, sine)` leaves
    `<point>_folder_input_volts` and `<point>_folder_integral`; `output_volts_at(point)` is the output there by
    second-order ADAA, one step late; `segment_output_volts(point, before)` is the output's exact mean from point
    `before` to `point`. Inputs `drive_volts`, `symmetry_offset_volts`, `frequency_hz` (per host sample, latched by
    `statements()`). See the module's docstring."""

    references_entry = "references/circuits/buchla-259.md"
    character_type = Buchla259TimbreSectionCharacter

    def __init__(self, instance_name, *, drive_volts, symmetry_offset_volts, frequency_hz, character=None):
        super().__init__(instance_name, character=character, drive_volts=drive_volts,
                         symmetry_offset_volts=symmetry_offset_volts, frequency_hz=frequency_hz)
        if not 0 < self.character.cell_rail_volts:
            raise BuildError(f"Buchla259TimbreSection {instance_name}: the cells' rail must be above 0 V, got "
                             f"{self.character.cell_rail_volts!r}")
        self.table = PiecewiseLinearTable("buchla_259_folder", transfer_pieces(self.character))

    @property
    def first_fold_volts(self):
        """The drive where the first fold starts (cell 1's fold point): below it the output is the sine, scaled."""
        return cell_fold_point_volts(0, self.character)

    @property
    def output_peak_volts(self):
        """About where the output peaks for drives of 0.6-10 V: 3.2 V at 6 V rails, scaling with them."""
        return OUTPUT_PEAK_VOLTS_AT_6_VOLT_RAILS * self.character.cell_rail_volts / 6.0

    @property
    def running_point(self):
        """The prefix of the instance's own last point (`<name>_before`): the `before` of a running segment."""
        return f"{self.instance_name}_before"

    def functions(self):
        return self.table.functions()

    def declarations(self):
        return self.substituted("History ${p}_before_folder_input_volts(0), ${p}_before_folder_integral(0), "
                                "${p}_before_before_folder_input_volts(0);")

    def statements(self):
        return self.substituted("""// ${p}: the Buchla 259's timbre section, its inputs this sample (kit circuit module: Buchla 259 timbre section)
${p}_drive_volts = ${drive_volts};
${p}_drive_stage_gain = 1 / sqrt(1 + pow(${frequency_hz} / ${drive_stage_hz}, 2));
${p}_symmetry_offset_volts = ${symmetry_offset_volts};""", drive_stage_hz=DRIVE_STAGE_HZ)

    def point_statements(self, point, sine):
        """At one point: the folder bus (the drive stage's sine and Symmetry's offset) and the folder's antiderivative
        there. `sine` is the principal oscillator's sine at the point (-1..1)."""
        p = self.instance_name
        return (f"{point}_folder_input_volts = {p}_drive_volts * {p}_drive_stage_gain * {sine} + "
                f"{p}_symmetry_offset_volts;\n"
                f"{point}_folder_integral = {self.table.integral_call(f'{point}_folder_input_volts')};")

    def output_volts_at(self, point):
        """GenExpr: the folder's output (volts) by second-order ADAA through `point` (it ran `point_statements`) and
        the instance's last two points: the folder one step late. Then `remember_statements(point)`."""
        p = self.instance_name
        return self.table.second_order_mean_call(f"{point}_folder_input_volts", f"{p}_before_folder_input_volts",
                                                 f"{p}_before_before_folder_input_volts")

    def segment_output_volts(self, point, before):
        """GenExpr: the folder's output (volts), its exact mean over the segment from point `before` to `point` (both
        ran `point_statements`): first-order ADAA, for a probe of the output's mean."""
        return self.table.mean_call(f"{point}_folder_input_volts", f"{before}_folder_input_volts",
                                    f"{point}_folder_integral", f"{before}_folder_integral")

    def remember_statements(self, point):
        """Make `point` the instance's last point (`running_point`), the one before it the last but one."""
        p = self.instance_name
        return (f"{p}_before_before_folder_input_volts = {p}_before_folder_input_volts;\n"
                f"{p}_before_folder_input_volts = {point}_folder_input_volts;\n"
                f"{p}_before_folder_integral = {point}_folder_integral;")

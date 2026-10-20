"""The Mu-Tron Bi-Phase (a circuit module): the whole unit as ARP drew it (drawing 77204, sheets 1-2, 1979): two
six-stage photocell phasors, their feedback, their passive dry / wet mixes, the two sweep generators and the routing
switches (references/circuits/mutron-bi-phase.md: the drawing read, the owner's manual quoted, what is derived and
what is unknown).

Per phasor (A and B are the same circuit):
- Input stage Z8B (Z10B): a differential amplifier, the dry signal on "-" (gain -1, R4 = R5 = 4.7k) and the
  feedback pot's wiper on "+" through R7 6.2k / R6 4.7k (gain 2), C5 3.3n on the "+" node (a low-pass in the fed-back
  path only, ~18 kHz). Feedback gain k = 2 R6 / (R6 + R7) x the pot's loaded division: 0.862 at full rotation. The
  amplifier's rails are `rail_volts` (a soft clip on the loop's input, the kit's knee soft clip).
- Six all-pass stages, each 4.7k / 4.7k around an op amp, 6.8 nF in, 220k in parallel with one photocell to ground:
  H(s) = (sRC - 1) / (sRC + 1), R = R_cell || 220k, corner 1 / (2 pi R C). The kit's zero-delay all-pass cascade:
  six of its first-order sections, (1 - s) / (1 + s) each, are the six of the circuit's (an even count: the signs
  cancel). One LED lights all six cells: one cell state, six corners (each scaled by `stage_corner_spread` times a
  fixed pattern: the 10 % capacitors' and the cells' unit-to-unit spread).
- C12 (C28) 0.47 uF couples the last stage to J1-1, loaded by R26 4.7k into Z9B's virtual ground and the feedback
  pot (its wiper loaded by R7 + R6): a high-pass of ~106-140 Hz inside the loop and the wet path [DERIVED].
- Z9B inverts (gain -1) into the passive mix: the wet through the bypass photocell PM1 (lit by the foot switch),
  R123 (`wet_trim_ohms`), C14 0.15 uF and R29 4.7k; the dry (Z8A's output) through R31 12k; the node unloaded. Exactly:
  out = dry + alpha HP(wet - dry), alpha = R31 / (R31 + Rw), Rw = R29 + R123 + R_PM1, HP a one-pole at
  1 / (2 pi (R31 + Rw) C14). Foot switch off: PM1 dark, alpha ~ 0: dry only (the unit's bypass).
- So u = -x + k LP(HP(H6 u)), wet = -HP(H6 u): notches where H6 = -1 (six equal stages: 0.268, 1 and 3.73 x the
  corner), peaks up to 1 / (1 - 0.862) = +17 dB where H6 = +1 (0.577 and 1.73 x the corner).

The sweep (sheet 1 and the manual): Sweep Generator 1 and 2, 0.1-18 Hz, sine or square (Shape); Phasor A's sweep from
Gen 1 or the pedal, Phasor B's from Gen 1, Gen 2 or the pedal; Sweep Sync Rev inverts B's sweep (Z15B). Each phasor's
Depth pot (R131 / R138 10k over R96 / R105 560 Ohm) scales its sweep; the LED driver (Z7A/B, Q1/Q2, a diode
break-point network not traced) turns it into the LED's current. Phasor B's input (S1): In A (A's input), Out A (A's
output: the manual's 12-stage "double depth" series) or In B.

The sample rate: the stages are the bilinear transform prewarped at the stage corner, exact at the middle notch; the
others are warped (at 44.1 kHz the top notch of a 1.8 kHz corner sits 6.5 % low). A device may oversample.

What no source gives is the character (`MutronBiPhaseCharacter`), each default labelled UNVERIFIED there: the cells'
law and times (a VTL5C3/2-like LED + CdS cell stands in), the LED driver's current span and curve (log-linear: equal
sweep steps equal octaves, the gate's practice), the sweep's shape, the feedback pot's taper, R123's setting, the rails.
The unknowns that shape the sweep can be moved at run time (`character_inputs`, RUNTIME_CHARACTER_FIELDS: the sweep
cells' law, the LED's dark and full currents, the cells' times, the stages' spread, the sine's roundness, the feedback
pot's taper), so an instrument can hunt the unit by ear (2sl phaser's Cells page). They move the twelve sweep cells
only: the bypass cell PM1 is another part (PE613-12), trimmed by R123 against its own law, so it stays at the
character's numbers (the dry / wet balance does not follow the hunt).

Inputs, all GenExpr expressions in the circuit's units: `input_a_volts`, `input_b_volts`; `rate_1_hz`, `rate_2_hz`
(held to 0.1-18 Hz: the manual's range; the pot's law is unknown, so the rate itself); `shape_1`, `shape_2` (> 0.5:
square); `depth_a`, `depth_b`, `feedback_a`, `feedback_b` (pot rotations 0..1); `sweep_a_source` (0 Gen 1, 1 Pedal);
`sweep_b_source` (0 Gen 1, 1 Gen 2, 2 Pedal); `sweep_sync` (0 Norm, 1 Rev); `phasor_b_input` (0 In A, 1 Out A, 2 In B);
`foot_switch_a`, `foot_switch_b` (1 on: the phasor in); `pedal_volts` (0-5 V, the C-100's span).
Outputs: `<name>_out_a`, `<name>_out_b` (volts, Outputs A and B), `<name>_corner_a_hz`, `<name>_corner_b_hz` (each
phasor's nominal stage corner now), `<name>_sweep_a`, `<name>_sweep_b` (each phasor's sweep, 0..1, after Rev).
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.led_driven_photocell import LedDrivenPhotocell
from m4l_dev.techniques.zero_delay_allpass_cascade import FirstOrderAllpassStage, ZeroDelayAllpassCascade
from m4l_dev.techniques.zero_delay_allpass_cascade import small_signal_response as cascade_response
from m4l_dev.techniques.zero_delay_one_pole_filter import ZeroDelayOnePoleFilter
from m4l_dev.techniques.zero_delay_one_pole_filter import small_signal_response as one_pole_response

# The drawing's parts (77204 sheets 1-2; references/circuits/mutron-bi-phase.md §2)
STAGES_PER_PHASOR = 6
STAGE_CAPACITOR_FARADS = 6.8e-9          # ".0068"
STAGE_SHUNT_OHMS = 220e3                 # in parallel with each cell
INPUT_STAGE_GAIN_ON_PLUS = 2.0           # Z8B: 1 + R5 / R4, R4 = R5 = 4.7k
FEEDBACK_DIVIDER_TOP_OHMS = 6.2e3        # R7
FEEDBACK_DIVIDER_BOTTOM_OHMS = 4.7e3     # R6
FEEDBACK_NODE_CAPACITOR_FARADS = 3.3e-9  # C5
FEEDBACK_POT_OHMS = 10e3                 # R133 / R134
OUTPUT_COUPLING_FARADS = 0.47e-6         # C12 / C28
WET_INVERTER_INPUT_OHMS = 4.7e3          # R26 / R58, into Z9B's virtual ground
MIX_DRY_OHMS = 12e3                      # R31 / R63
MIX_WET_OHMS = 4.7e3                     # R29 / R62
MIX_COUPLING_FARADS = 0.15e-6            # C14 / C30
DEPTH_POT_OHMS = 10e3                    # R131 / R138
DEPTH_POT_FOOT_OHMS = 560.0              # R96 / R105, under the pot: depth 0 still passes 5.3 %
DEPTH_FLOOR = DEPTH_POT_FOOT_OHMS / (DEPTH_POT_OHMS + DEPTH_POT_FOOT_OHMS)
PEDAL_FULL_SCALE_VOLTS = 5.0             # the C-100 "puts out 0-5 volts" (Muzines)
SLOWEST_SWEEP_HZ, FASTEST_SWEEP_HZ = 0.1, 18.0   # the manual: "from 0.1Hz ... to 18Hz"
# No delay line, no look-ahead, no oversampling: zero-delay all-pass stages and one-poles, the output on the
# input's own sample (tests: the rendered phase is the Python model's, with no sample added)
LATENCY_SAMPLES = 0
# A fixed pattern for the six parts' spread (each phasor its own), scaled by the character's stage_corner_spread
STAGE_SPREAD_PATTERN = {"a": (0.62, -0.91, 0.18, 1.0, -0.37, -0.52), "b": (-0.44, 0.83, -1.0, 0.29, 0.71, -0.08)}
RUNTIME_CHARACTER_FIELDS = ("cell_law_scale_ohms", "cell_law_exponent", "cell_law_floor_ohms", "led_current_dark_amps",
                            "led_current_full_amps", "cell_attack_ms", "cell_release_ms", "stage_corner_spread",
                            "sweep_sine_roundness", "feedback_pot_taper_exponent")
if STAGES_PER_PHASOR % 2 or any(len(pattern) != STAGES_PER_PHASOR for pattern in STAGE_SPREAD_PATTERN.values()):
    # the circuit's stage is -(the technique's section): only an even count of them keeps the sign
    raise BuildError("mutron_bi_phase.py: each phasor is an even number of stages, one spread ratio each")


@dataclasses.dataclass(frozen=True)
class MutronBiPhaseCharacter:
    """One unit's build character. Every default is UNVERIFIED unless said: the Bi-Phase's cells, driver and trims
    are unpublished (references/circuits/mutron-bi-phase.md §7)."""
    # The photocells' law R = A I^-p + B. UNVERIFIED: the VTL5C3/2 fit (DAFx-13 eq. 39) stands in for the "photo-mod".
    cell_law_scale_ohms: float = 3.464
    cell_law_exponent: float = 1.4
    cell_law_floor_ohms: float = 1136.212
    # The LED driver's span: sweep 0 is the dark current, 1 the full one, log-linear between. UNVERIFIED: chosen so the
    # stage corner sweeps ~112 Hz (the 220k floor: 106 Hz) to ~3.4 kHz, notches ~30 Hz to ~13 kHz.
    led_current_dark_amps: float = 50e-6
    led_current_full_amps: float = 5e-3
    # The cells' times. UNVERIFIED: the VTL5C3's catalog turn-on (2.5 ms to 63 %) and turn-off (35 ms to 100 kOhm)
    # orders. Release: the time from the full current to the dark one, undriven.
    cell_attack_ms: float = 2.5
    cell_release_ms: float = 35.0
    # The six stages' corners spread by this fraction times a fixed pattern. UNVERIFIED (10 % capacitors on the drawing).
    stage_corner_spread: float = 0.05
    # The feedback pot's taper: the wiper sits at rotation^taper. UNVERIFIED: linear.
    feedback_pot_taper_exponent: float = 1.0
    # The sweep's sine: 1 a true sine, 0 the triangle core. UNVERIFIED: how the "sine" is shaped was not traced.
    sweep_sine_roundness: float = 1.0
    # R123's setting. UNVERIFIED: trimmed so the dry and the wet sum equally with the bypass cell lit (deepest notch).
    wet_trim_ohms: float = 3978.0
    # The bypass cell PM1's LED current with the foot switch on. UNVERIFIED (the cells' law stands in for PE613-12).
    bypass_led_current_amps: float = 10e-3
    # The input stage's swing at the +-15 V rails (RC4195, drawing 77206: VERIFIED); the op amp's swing UNVERIFIED.
    rail_volts: float = 13.0


def feedback_gain(rotation, character=MutronBiPhaseCharacter()):
    """k: the fraction of J1-1 that comes back at the input stage's output (positive feedback), from the pot's rotation
    0..1, with the wiper loaded by R7 + R6: 0.862 at full."""
    position = min(max(rotation, 0.0), 1.0) ** character.feedback_pot_taper_exponent
    load = FEEDBACK_DIVIDER_TOP_OHMS + FEEDBACK_DIVIDER_BOTTOM_OHMS
    wiper = position * load / (load + position * (1 - position) * FEEDBACK_POT_OHMS)
    return INPUT_STAGE_GAIN_ON_PLUS * FEEDBACK_DIVIDER_BOTTOM_OHMS / load * wiper


def feedback_lowpass_hz(rotation, character=MutronBiPhaseCharacter()):
    """C5 against R6 || (R7 + the wiper's source resistance)."""
    position = min(max(rotation, 0.0), 1.0) ** character.feedback_pot_taper_exponent
    source = FEEDBACK_DIVIDER_TOP_OHMS + position * (1 - position) * FEEDBACK_POT_OHMS
    resistance = 1 / (1 / FEEDBACK_DIVIDER_BOTTOM_OHMS + 1 / source)
    return 1 / (2 * math.pi * resistance * FEEDBACK_NODE_CAPACITOR_FARADS)


def coupling_highpass_hz(rotation, character=MutronBiPhaseCharacter()):
    """C12 into J1-1's load: R26 (to a virtual ground) || the pot, its wiper loaded by R7 + R6."""
    position = min(max(rotation, 0.0), 1.0) ** character.feedback_pot_taper_exponent
    load = FEEDBACK_DIVIDER_TOP_OHMS + FEEDBACK_DIVIDER_BOTTOM_OHMS
    lower = position * FEEDBACK_POT_OHMS
    pot = (1 - position) * FEEDBACK_POT_OHMS + (lower * load / (lower + load) if lower > 0 else 0.0)
    resistance = 1 / (1 / WET_INVERTER_INPUT_OHMS + 1 / pot)
    return 1 / (2 * math.pi * resistance * OUTPUT_COUPLING_FARADS)


def stage_corner_hz(cell_ohms):
    """A stage's corner for a cell resistance: 1 / (2 pi (R_cell || 220k) 6.8 nF)."""
    return (1 / cell_ohms + 1 / STAGE_SHUNT_OHMS) / (2 * math.pi * STAGE_CAPACITOR_FARADS)


def cell_ohms(led_current_amps, character=MutronBiPhaseCharacter()):
    """A sweep cell's steady resistance at an LED current."""
    current = max(led_current_amps, character.led_current_dark_amps)
    return character.cell_law_scale_ohms * current ** -character.cell_law_exponent + character.cell_law_floor_ohms


def led_current_amps(drive, character=MutronBiPhaseCharacter()):
    """The LED current for a drive 0..1 (the sweep after Depth): log-linear from dark to full."""
    drive = min(max(drive, 0.0), 1.0)
    return character.led_current_dark_amps * (character.led_current_full_amps / character.led_current_dark_amps) ** drive


def drive_for(sweep, depth):
    """The LED driver's drive (0..1) for a sweep position 0..1 and a Depth rotation 0..1 (the pot over R96)."""
    return sweep * (DEPTH_FLOOR + (1 - DEPTH_FLOOR) * min(max(depth, 0.0), 1.0))


def mix_weight_and_corner_hz(bypass_cell_ohms, character=MutronBiPhaseCharacter()):
    """(alpha, the mix high-pass corner): out = dry + alpha HP(wet - dry)."""
    wet_path = MIX_WET_OHMS + character.wet_trim_ohms + bypass_cell_ohms
    return (MIX_DRY_OHMS / (MIX_DRY_OHMS + wet_path),
            1 / (2 * math.pi * (MIX_DRY_OHMS + wet_path) * MIX_COUPLING_FARADS))


def phasor_small_signal_response(frequency_hz, sweep_cell_ohms, feedback_rotation, sample_rate, phasor="a",
                                 character=MutronBiPhaseCharacter(), foot_switch_on=True):
    """One phasor's output over its input (complex) at `frequency_hz`, the cells steady at `sweep_cell_ohms`, as the
    module renders it (each one-pole the bilinear transform prewarped as the module prewarps it). The rails left out."""
    corner = stage_corner_hz(sweep_cell_ohms)
    stages = cascade_response(frequency_hz, [(corner * (1 + character.stage_corner_spread * ratio),)
                                             for ratio in STAGE_SPREAD_PATTERN[phasor]], sample_rate, prewarp_hz=corner)
    coupling = one_pole_response(frequency_hz, coupling_highpass_hz(feedback_rotation, character),
                                 sample_rate)["highpass"]
    fed_back = one_pole_response(frequency_hz, feedback_lowpass_hz(feedback_rotation, character), sample_rate)["lowpass"]
    k = feedback_gain(feedback_rotation, character)
    loop_input = -1 / (1 - k * fed_back * coupling * stages)
    wet = -coupling * stages * loop_input
    bypass_current = character.bypass_led_current_amps if foot_switch_on else character.led_current_dark_amps
    alpha, mix_corner = mix_weight_and_corner_hz(cell_ohms(bypass_current, character), character)
    return 1 + alpha * one_pole_response(frequency_hz, mix_corner, sample_rate)["highpass"] * (wet - 1)


def _expression(term):
    """A character term (a number or a run-time expression) as GenExpr text."""
    return term if isinstance(term, str) else repr(float(term))


def _ratio(numerator, denominator):
    """numerator / denominator, folded to a number when both are numbers."""
    if isinstance(numerator, str) or isinstance(denominator, str):
        return f"{_expression(numerator)} / {_expression(denominator)}"
    return numerator / denominator


class MutronBiPhase(CircuitModule):
    """`<name>_out_a`, `<name>_out_b` (volts): the Bi-Phase's two outputs (see the module docstring for the inputs);
    `<name>_corner_a_hz`, `<name>_corner_b_hz`, `<name>_sweep_a`, `<name>_sweep_b`."""

    references_entry = "references/circuits/mutron-bi-phase.md"
    character_type = MutronBiPhaseCharacter
    runtime_character_fields = RUNTIME_CHARACTER_FIELDS

    def __init__(self, instance_name, *, input_a_volts, input_b_volts, rate_1_hz, rate_2_hz, shape_1, shape_2,
                 depth_a, depth_b, feedback_a, feedback_b, sweep_a_source, sweep_b_source, sweep_sync,
                 phasor_b_input, foot_switch_a, foot_switch_b, pedal_volts, character=None, character_inputs=None):
        super().__init__(instance_name, character=character, character_inputs=character_inputs,
                         input_a_volts=input_a_volts,
                         input_b_volts=input_b_volts, rate_1_hz=rate_1_hz, rate_2_hz=rate_2_hz, shape_1=shape_1,
                         shape_2=shape_2, depth_a=depth_a, depth_b=depth_b, feedback_a=feedback_a,
                         feedback_b=feedback_b, sweep_a_source=sweep_a_source, sweep_b_source=sweep_b_source,
                         sweep_sync=sweep_sync, phasor_b_input=phasor_b_input, foot_switch_a=foot_switch_a,
                         foot_switch_b=foot_switch_b, pedal_volts=pedal_volts)
        p, c, term = instance_name, self.character, self.character_term
        sweep_cell_law = dict(law_scale_ohms=term("cell_law_scale_ohms"), law_exponent=term("cell_law_exponent"),
                              law_floor_ohms=term("cell_law_floor_ohms"),
                              darkest_current_amps=term("led_current_dark_amps"),
                              release_from_amps=term("led_current_full_amps"),
                              release_to_amps=term("led_current_dark_amps"))
        # PM1 at the character's numbers always (the module docstring: the hunt moves the sweep cells only)
        bypass_cell_law = dict(law_scale_ohms=c.cell_law_scale_ohms, law_exponent=c.cell_law_exponent,
                               law_floor_ohms=c.cell_law_floor_ohms, darkest_current_amps=c.led_current_dark_amps,
                               release_from_amps=c.led_current_full_amps, release_to_amps=c.led_current_dark_amps)
        spread = term("stage_corner_spread")
        self.parts = {}
        for side in ("a", "b"):
            sweep_cell = LedDrivenPhotocell(f"{p}_sweep_cell_{side}", drive_current_amps=f"{p}_led_current_{side}",
                                            attack_ms=_expression(term("cell_attack_ms")),
                                            release_ms=_expression(term("cell_release_ms")), **sweep_cell_law)
            bypass_cell = LedDrivenPhotocell(f"{p}_bypass_cell_{side}", drive_current_amps=f"{p}_bypass_led_{side}",
                                             attack_ms=repr(c.cell_attack_ms), release_ms=repr(c.cell_release_ms),
                                             **bypass_cell_law)
            stages = [FirstOrderAllpassStage(f"{p}_corner_{side}_hz * {1 + spread * ratio!r}"
                                             if not isinstance(spread, str)
                                             else f"{p}_corner_{side}_hz * (1 + {spread} * {ratio!r})")
                      for ratio in STAGE_SPREAD_PATTERN[side]]
            phasor = ZeroDelayAllpassCascade(f"{p}_phasor_{side}", input=f"0 - {p}_dry_{side}", stages=stages,
                                             feedback=f"{p}_feedback_gain_{side}", prewarp_hz=f"{p}_corner_{side}_hz",
                                             coupling_highpass_hz=f"{p}_coupling_hz_{side}",
                                             feedback_lowpass_hz=f"{p}_feedback_lowpass_hz_{side}",
                                             loop_limit=c.rail_volts)
            mix = ZeroDelayOnePoleFilter(f"{p}_mix_{side}", input=f"{p}_wet_{side} - {p}_dry_{side}",
                                         cutoff_hz=f"{p}_mix_corner_{side}_hz")
            self.parts[side] = (sweep_cell, bypass_cell, phasor, mix)

    def _blocks(self):
        return [block for side in ("a", "b") for block in self.parts[side]]

    def functions(self):
        functions = {}
        for block in self._blocks():
            functions.update(block.functions())
        return functions

    def declarations(self):
        return self.substituted("History ${p}_gen_1_phase(0), ${p}_gen_2_phase(0);\n") + "\n".join(
            text for text in (block.declarations().strip() for block in self._blocks()) if text)

    def _generator_statements(self, number):
        return self.substituted("""// Sweep Generator ${n}: a triangle core, its "sine" and its square, 0..1
${p}_gen_${n}_phase = wrap(${p}_gen_${n}_phase + clamp(${rate}, ${slowest}, ${fastest}) / samplerate, 0, 1);
${p}_gen_${n}_triangle = 1 - abs(2 * ${p}_gen_${n}_phase - 1);
${p}_gen_${n}_sine = 0.5 - 0.5 * cos(twopi * ${p}_gen_${n}_phase);
${p}_gen_${n}_round = ${p}_gen_${n}_triangle + ${roundness} * (${p}_gen_${n}_sine - ${p}_gen_${n}_triangle);
${p}_gen_${n}_square = (${p}_gen_${n}_phase >= 0.25 && ${p}_gen_${n}_phase < 0.75) ? 1 : 0;
${p}_gen_${n} = ${shape} > 0.5 ? ${p}_gen_${n}_square : ${p}_gen_${n}_round;""",
                                n=str(number), rate=self.input_expressions[f"rate_{number}_hz"],
                                shape=self.input_expressions[f"shape_{number}"], slowest=SLOWEST_SWEEP_HZ,
                                fastest=FASTEST_SWEEP_HZ, roundness=self.character_term("sweep_sine_roundness"))

    def _phasor_statements(self, side):
        c = self.character
        sweep_cell, bypass_cell, phasor, mix = self.parts[side]
        position = f"pow(clamp(${{feedback_{side}}}, 0, 1), {_expression(self.character_term('feedback_pot_taper_exponent'))})"
        return self.substituted(f"""// ---- Phasor {side.upper()} ----
// the LED driver: the sweep through Depth (the pot over R96), log-linear from the dark current to the full one
${{p}}_led_current_{side} = ${{dark}} * pow(${{span}}, ${{p}}_sweep_{side} * (${{depth_floor}} + ${{depth_rest}} * clamp(${{depth_{side}}}, 0, 1)));
${{p}}_bypass_led_{side} = ${{foot_switch_{side}}} > 0.5 ? ${{bypass}} : ${{bypass_dark}};
""", dark=self.character_term("led_current_dark_amps"), span=_ratio(self.character_term("led_current_full_amps"),
                                                                    self.character_term("led_current_dark_amps")),
                                depth_floor=DEPTH_FLOOR, depth_rest=1 - DEPTH_FLOOR,
                                bypass=c.bypass_led_current_amps, bypass_dark=c.led_current_dark_amps) \
            + sweep_cell.statements() + "\n" + bypass_cell.statements() + "\n" + self.substituted(f"""
// the stage corner, 1 / (2 pi (R_cell || 220k) 6.8 nF); the feedback pot and what it loads
${{p}}_corner_{side}_hz = (1 / ${{p}}_sweep_cell_{side}_resistance + ${{shunt_conductance}}) * ${{per_farad}};
${{p}}_pot_{side} = {position};
${{p}}_wiper_source_{side} = ${{p}}_pot_{side} * (1 - ${{p}}_pot_{side}) * ${{pot}};
${{p}}_feedback_gain_{side} = ${{divider_gain}} * ${{p}}_pot_{side} * ${{load}} / (${{load}} + ${{p}}_wiper_source_{side});
${{p}}_feedback_lowpass_hz_{side} = (${{bottom_conductance}} + 1 / (${{top}} + ${{p}}_wiper_source_{side})) * ${{per_node_farad}};
${{p}}_pot_lower_{side} = ${{p}}_pot_{side} * ${{pot}};
${{p}}_pot_load_{side} = (1 - ${{p}}_pot_{side}) * ${{pot}} + ${{p}}_pot_lower_{side} * ${{load}} / (${{p}}_pot_lower_{side} + ${{load}});
${{p}}_coupling_hz_{side} = (${{inverter_conductance}} + 1 / ${{p}}_pot_load_{side}) * ${{per_coupling_farad}};
// the mix: out = dry + alpha HP(wet - dry), Rw = R29 + R123 + PM1
${{p}}_wet_path_{side} = ${{wet_fixed}} + ${{p}}_bypass_cell_{side}_resistance;
${{p}}_mix_weight_{side} = ${{dry_ohms}} / (${{dry_ohms}} + ${{p}}_wet_path_{side});
${{p}}_mix_corner_{side}_hz = ${{per_mix_farad}} / (${{dry_ohms}} + ${{p}}_wet_path_{side});
""", shunt_conductance=1 / STAGE_SHUNT_OHMS, per_farad=1 / (2 * math.pi * STAGE_CAPACITOR_FARADS),
                pot=FEEDBACK_POT_OHMS, load=FEEDBACK_DIVIDER_TOP_OHMS + FEEDBACK_DIVIDER_BOTTOM_OHMS,
                divider_gain=INPUT_STAGE_GAIN_ON_PLUS * FEEDBACK_DIVIDER_BOTTOM_OHMS
                / (FEEDBACK_DIVIDER_TOP_OHMS + FEEDBACK_DIVIDER_BOTTOM_OHMS),
                bottom_conductance=1 / FEEDBACK_DIVIDER_BOTTOM_OHMS, top=FEEDBACK_DIVIDER_TOP_OHMS,
                per_node_farad=1 / (2 * math.pi * FEEDBACK_NODE_CAPACITOR_FARADS),
                inverter_conductance=1 / WET_INVERTER_INPUT_OHMS,
                per_coupling_farad=1 / (2 * math.pi * OUTPUT_COUPLING_FARADS),
                wet_fixed=MIX_WET_OHMS + c.wet_trim_ohms, dry_ohms=MIX_DRY_OHMS,
                per_mix_farad=1 / (2 * math.pi * MIX_COUPLING_FARADS)) \
            + phasor.statements() + "\n" + self.substituted(f"""// Z9B inverts J1-1; the passive mix
${{p}}_wet_{side} = 0 - ${{p}}_phasor_{side}_coupled;
""") + mix.statements() + "\n" + self.substituted(
                f"${{p}}_out_{side} = ${{p}}_dry_{side} + ${{p}}_mix_weight_{side} * ${{p}}_mix_{side}_highpass;")

    def statements(self):
        return "\n".join([
            self.substituted("// ${p}: Mu-Tron Bi-Phase (kit circuit module: Mu-Tron Bi-Phase, ARP drawing 77204)"),
            self._generator_statements(1),
            self._generator_statements(2),
            self.substituted("""// the sweep selection: A from Gen 1 or the pedal (S5); B from Gen 1, Gen 2 or the pedal; Rev inverts B's (Z15B)
${p}_pedal = clamp(${pedal_volts} / ${pedal_full_scale}, 0, 1);
${p}_sweep_a = ${sweep_a_source} > 0.5 ? ${p}_pedal : ${p}_gen_1;
${p}_sweep_b_selected = ${sweep_b_source} > 1.5 ? ${p}_pedal : (${sweep_b_source} > 0.5 ? ${p}_gen_2 : ${p}_gen_1);
${p}_sweep_b = ${sweep_sync} > 0.5 ? 1 - ${p}_sweep_b_selected : ${p}_sweep_b_selected;
${p}_dry_a = ${input_a_volts};""", pedal_full_scale=PEDAL_FULL_SCALE_VOLTS),
            self._phasor_statements("a"),
            self.substituted("""// S1, Phasor B's input: In A, Out A (series: A's output), In B
${p}_dry_b = ${phasor_b_input} > 1.5 ? ${input_b_volts} : (${phasor_b_input} > 0.5 ? ${p}_out_a : ${input_a_volts});"""),
            self._phasor_statements("b"),
        ])

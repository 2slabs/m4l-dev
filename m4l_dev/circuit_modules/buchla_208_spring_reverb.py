"""The Buchla 208's spring reverb, as 2sl gate had it (a circuit module): the Music Easel's card 12 driver (an LM380
into the tank's 8 ohm input coil through 390 uF: a series R-L-C, resonant at 226 Hz, Q 2.23) and a two-spring tank,
33.7 and 41.3 ms, on the kit's dispersive-loop spring tank (references/circuits/buchla-208-spring-reverb.md).

It is gate's spring moved into the kit, sound unchanged: tests/test_circuit_module_buchla_208_spring_reverb.py renders
gate's own spring code (copied verbatim) beside it. 2sl gate had the spring until 0.6.0, which took it out (Graham,
2026-10-22: "keep it as a dsp block but remove the spring"); the test keeps that copy as the reference.

The driver (references/circuits/buchla-208-spring-reverb.md §2): the coil's current against the coil driven straight
is H(s) = 1 - 1 / (s^2 LC + sRC + 1), so the springs are driven by the input less the kit's state-variable filter's
low-pass at f0 = 1 / (2 pi sqrt(LC)), Q = sqrt(L / C) / R. +7.8 dB at 226 Hz, -27.8 dB at 20 Hz, flat from 3 kHz.
The tank: the dispersive-loop spring tank with gate's numbers (two springs, eight all-passes of 0.62, the loop's
low-pass 2500 Hz x 4^brightness, the DC blocker where it costs the longer spring's first tooth 0.1 dB a trip, a tanh
where each loop writes back, a 60 ms clear). No source names the 208's tank; 33.7 / 41.3 ms are gate's, unsourced
(the reference says so).

The tank interface (the same for every spring tank module in the kit, so a device can switch tanks under one set of
controls):
- inputs: `input` (mono, what goes into the tank), `length_s` (seconds to -60 dB: here the loops' gain alone, gate's
  Spring length, 0.3-6 s in gate; NOMINAL_LENGTH_S is gate's Init), `brightness` (-1..1: the loops' low-pass,
  2500 Hz x 4^brightness), `clear` (true on a sample: empties the tank, as gate's Stop: 60 ms with nothing read or
  written, the driver emptied), `kick` (optional: a shock to the tank, see below);
- outputs: `<name>_left`, `<name>_right` (the wet only: the 33.7 ms spring on the left, the 41.3 ms on the right, as
  gate pans them), `<name>_level` (a falling peak meter of both, 75.6 ms, gate's spring display's), `<name>_driven`
  (the coil's current: what goes into the springs);
- `latency_samples` 0: the output is the springs' echoes, with no direct path through the tank;
- `oversampling` (required): 1, the only rate it has a design for. Gate runs it at the host rate; the loop's tanh is
  the one non-linearity, and its loops' low-pass sits under 10 kHz at every Bright (2500 x 4);
- `wet_level_db`: the wet's level against its input, measured (white noise, 0.5 s, at the nominal Length, 3 s of
  output, both sides), so a device switching tanks can match them.

The kick (Splash). Kicking a tank is a mechanical shock: the frame moves, so every spring is excited at once and the
driver's coil is not in the path (references/circuits/buchla-208-spring-reverb.md §4, after 2sl dub's
references/springs.md §5). So `kick` is added into every spring's loop after the driver, where the loop writes back
through its tanh: a burst loud enough (a peak of 2-4) clips there, the magnets meeting the pole pieces. What reads as
a kick: a few ms of noise with a fast-decaying envelope plus a low thump (a 40-80 Hz half cycle), into `kick`, once.
The burst then rings through the springs' own dispersion; the loops' DC blocker keeps the thump from ringing on.
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.generated_numbers import generated_number
from m4l_dev.techniques.dispersive_loop_spring_tank import DispersiveLoopSpringTank
from m4l_dev.techniques.zero_delay_state_variable_filter import ZeroDelayStateVariableFilter

# gate's tank (src/gate_dsp.py, 2sl gate 68bfd110): its loops' constants
ALLPASSES = 8
ALLPASS_COEFFICIENT = 0.62
LOWPASS_HZ_AT_NEUTRAL = 2500                 # the loops' low-pass at brightness 0, x 4 per unit of brightness
BRIGHTNESS_RATIO = 4
FIRST_TOOTH_LOSS_DB = 0.1                    # the DC blocker's corner costs the longer loop's first tooth this a trip
CLEAR_MS = 60.0                              # gate's SPRING_CLEAR_MS
NOMINAL_LENGTH_S = 2.0                       # gate's Spring length Init (no tank spec: no source names the tank)
LEVEL_METER_FALL_MS = 75.6                   # gate's spring display's meter
WET_LEVEL_DB = -7.4                          # measured: tests/test_spring_tank_interface.py


@dataclasses.dataclass(frozen=True)
class Buchla208SpringReverbCharacter:
    """One unit: card 12's driver (C2 and the coil, references/circuits/buchla-208-spring-reverb.md §1-§2) and the
    tank's two springs (gate's round trips, unsourced)."""
    coupling_farads: float = 390e-6           # C2, 390 uF 12 V (schematic B2080-12A)
    coil_henries: float = 1.27e-3             # Accutronics coil A (ESP Table 1), the inferred coil
    coil_ohms: float = 0.81                   # its DC resistance
    left_round_trip_ms: float = 33.7          # gate's SPRING_LOOP_MS
    right_round_trip_ms: float = 41.3


def driver_resonance_hz(character):
    """f0 = 1 / (2 pi sqrt(L C)) of the coil and the coupling capacitor: 226 Hz."""
    return generated_number(1 / (2 * math.pi * math.sqrt(character.coil_henries * character.coupling_farads)))


def driver_q(character):
    """Q = sqrt(L / C) / R: 2.23."""
    return generated_number(math.sqrt(character.coil_henries / character.coupling_farads) / character.coil_ohms)


def dc_block_hz(character):
    """The loops' DC blocker: where a one-pole high-pass costs the longer loop's first tooth (1 / round trip)
    FIRST_TOOTH_LOSS_DB: 3.69 Hz for 41.3 ms (gate's SPRING_LOOP_DC_BLOCK_HZ)."""
    longest_ms = max(character.left_round_trip_ms, character.right_round_trip_ms)
    return generated_number((1000.0 / longest_ms) * math.sqrt(10 ** (FIRST_TOOTH_LOSS_DB / 10) - 1))


def driver_response(frequency_hz, character):
    """The coil's current against the coil driven straight, 1 - 1 / (s^2 LC + sRC + 1), analog."""
    s = 2j * math.pi * frequency_hz
    return 1 - 1 / (s * s * character.coil_henries * character.coupling_farads
                    + s * character.coil_ohms * character.coupling_farads + 1)


class Buchla208SpringReverb(CircuitModule):
    """`<name>_left`, `<name>_right`, `<name>_level`, `<name>_driven`: see the module docstring."""

    references_entry = "references/circuits/buchla-208-spring-reverb.md"
    character_type = Buchla208SpringReverbCharacter
    nominal_length_s = NOMINAL_LENGTH_S
    wet_level_db = WET_LEVEL_DB

    def __init__(self, instance_name, *, input, length_s, brightness, clear, oversampling, kick=None,
                 character=None):
        inputs = dict(input=input, length_s=length_s, brightness=brightness, clear=clear)
        if kick is not None:
            inputs["kick"] = kick
        super().__init__(instance_name, character=character, **inputs)
        if oversampling != 1:
            raise BuildError(f"Buchla208SpringReverb {instance_name}: oversampling {oversampling!r} has no design: the "
                             "tank runs at the host rate (1), as 2sl gate's")
        self.oversampling = oversampling
        self.latency_samples = 0       # the wet only: its echoes come round the springs' loops, no direct path
        p = instance_name
        character = self.character
        self.driver = ZeroDelayStateVariableFilter(f"{p}_driver", input=f"{p}_input",
                                                   cutoff_hz=repr(driver_resonance_hz(character)),
                                                   q=repr(driver_q(character)))
        tank_input = f"{p}_driven" if kick is None else f"{p}_driven + {self.input_expressions['kick']}"
        self.tank = DispersiveLoopSpringTank(
            f"{p}_tank", input=tank_input,
            lowpass_hz=f"{LOWPASS_HZ_AT_NEUTRAL} * pow({BRIGHTNESS_RATIO}, {self.input_expressions['brightness']})",
            length_s=self.input_expressions["length_s"], clear=f"{p}_clear",
            round_trips_ms=(character.left_round_trip_ms, character.right_round_trip_ms), allpasses=ALLPASSES,
            allpass_coefficient=ALLPASS_COEFFICIENT, dc_block_hz=dc_block_hz(character), clear_ms=CLEAR_MS)

    def functions(self):
        return {}

    def declarations(self):
        return "\n".join([self.substituted("History ${p}_level(0);"), self.driver.declarations(),
                          self.tank.declarations()])

    def statements(self):
        return "\n".join([
            self.substituted("""// ${p}: the Buchla 208's spring reverb, as 2sl gate had it (kit circuit module: Buchla 208 spring reverb)
${p}_input = ${input};
${p}_clear = ${clear};
// card 12's driver: the coil's current is the input less the coil and C2's resonant low-pass
if (${p}_clear) {
""") + "\t" + self.driver.reset_statements().replace("\n", "\n\t") + "\n}",
            self.driver.statements(),
            self.substituted("${p}_driven = ${p}_input - ${p}_driver_lowpass;"),
            self.tank.statements(),
            self.substituted("""${p}_left = ${p}_tank_spring_1;
${p}_right = ${p}_tank_spring_2;
${p}_level = max(abs(${p}_left) + abs(${p}_right), ${p}_level * (1 - smoothing_coefficient(${fall_ms}, samplerate)));""",
                             fall_ms=LEVEL_METER_FALL_MS)])

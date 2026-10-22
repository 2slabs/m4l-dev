"""The Accutronics type 9 spring tank, the long three-spring tank of a guitar amp's reverb (a 9AB3C1B: 16.25", three
springs, 10 ohm input coil, long decay) driven as the maker's notes say, by a current source rising 6 dB/oct (a
circuit module): three dispersive springs of 33, 37 and 41 ms on the kit's parametric spring reverb
(references/circuits/accutronics-type-9-spring-tank.md).

What is sourced and what is assumed (the reference file tags each):
- the springs' delays, 33 / 37 / 41 ms, and the decay class, long, 2.75-4.0 s: Amplified Parts' copy of the vintage
  Accutronics specifications (SECONDARY). NOMINAL_LENGTH_S is 3.4 s, the class's middle (COMPUTED); that each delay
  is the echo spacing (the round trip) is our reading (UNVERIFIED);
- the drive: a current source, its output rising 6 dB/oct "to compensate for the input coil's inductive reactance"
  (AP, SECONDARY): a first-order high-pass in front of the springs, its corner ASSUMED at 200 Hz (ESP's usable band
  starts there; the Twin Reverb's own corner is not read);
- the recovery: a flat preamp with "an output high-pass filter with a 50 Hz to 100 Hz cutoff" (AP, SECONDARY): one
  pole at 70.7 Hz, the range's geometric middle (DESIGN);
- the dispersion: no Accutronics spring has been measured in the literature we have, so the Leem Pro KA-1210's
  (another three-spring 16" tank, Parker & Bilbao 2009 / Gamper et al. 2011) stands in: F_C 4500 Hz (ASSUMED, between
  its springs' computed 4.5-4.9 kHz and its fitted 4.2-4.3 kHz), VPA10's coefficient 0.62, its 100 sections for
  56 ms scaled to each spring (59, 66, 73), a negative loop gain (VPA10);
- the decay: `length_s` is the T60 at 1 kHz (ASSUMED: the frequency the maker quotes its impedances at; AP gives no
  frequency for the decay class);
- the loops' damping: no source gives a tank's decay against frequency, and VPA10's loss a trip is one number at
  every frequency; so the loops' low-pass sits an octave over F_C at Bright 0, 9 kHz (the technique's neutral
  damping, DESIGN: 0.8 dB a trip more at F_C than at 1 kHz), Bright +1 opens it to VPA10's flat loss and -1 brings
  it to F_C / 2. The decay in seconds also follows the trip's time: near F_C an echo takes the round trip and the
  chirp's delay, so with a flat loss the top of the band would ring longest.

The tank interface (the same for every spring tank module in the kit, so a device can switch tanks under one set of
controls):
- inputs: `input` (mono, what goes into the tank), `length_s` (the tank's T60 at 1 kHz, seconds: the springs' own
  frequency-dependent decay scaled to it; NOMINAL_LENGTH_S is the type's), `brightness` (-1..1: the loops' damping
  low-pass, an octave over F_C x 4^brightness), `clear` (true on a sample: empties the tank, every state at once and a round
  trip, 41 ms, with nothing read or written), `kick` (optional: a shock to the tank, see below);
- outputs: `<name>_left`, `<name>_right` (the wet only: 33 ms left, 37 ms both sides at -3 dB, 41 ms right),
  `<name>_level` (a falling peak meter of both, 75.6 ms), `<name>_driven` (the coil's current: what goes into the
  springs);
- `latency_samples` 0: the output is the springs' echoes, with no direct path through the tank;
- `oversampling` (required): 1, the only rate it has a design for: the loops are linear and band-limited to F_C; the
  one non-linearity, the transducer's tanh, is the kit's first-order ADAA tanh, once, on the input;
- `wet_level_db`: the wet's level against its input, measured (white noise, 0.5 s, at the nominal Length, 3 s of
  output, both sides), so a device switching tanks can match them.

The kick (Splash): a shock moves the tank's frame, so every spring is excited at once and the drive's high-pass is not
in the path (references/circuits/accutronics-type-9-spring-tank.md §5). `kick` is added after the drive, before the
transducer's tanh: a burst with a peak of 2-4 clips there (the magnets meeting the pole pieces), then chirps down
every spring. What reads as a kick: a few ms of noise with a fast-decaying envelope plus a low thump (a 40-80 Hz half
cycle), into `kick`, once. The recovery high-pass (AP's, there "to lessen the effects of rumble when the unit is
mechanically shocked") and the loops' 40 Hz blocker keep the thump short.
"""
import dataclasses

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.generated_numbers import generated_number
from m4l_dev.techniques.parametric_spring_reverb import (REFERENCE_ALLPASS_COEFFICIENT, ParametricSpringReverb,
                                                         neutral_damping_hz, sections_for_round_trip)
from m4l_dev.techniques.zero_delay_one_pole_filter import ZeroDelayOnePoleFilter

NOMINAL_LENGTH_S = 3.4                       # the long decay class's middle, (2.75 + 4.0) / 2 (AP)
DECAY_REFERENCE_HZ = 1000.0                  # ASSUMED: the frequency the maker's figures are quoted at
BRIGHTNESS_RATIO = 4                         # the damping's corner x 4 per unit of brightness (2sl gate's law)
LEVEL_METER_FALL_MS = 75.6
WET_LEVEL_DB = 0.6                           # measured: tests/test_spring_tank_interface.py
PANS = (-1.0, 0.0, 1.0)                      # 33 ms left, 37 ms both, 41 ms right


@dataclasses.dataclass(frozen=True)
class AccutronicsType9SpringTankCharacter:
    """One tank and its drive: the springs' round trips (AP), the stand-in dispersion (the Leem Pro's, VPA10's), the
    drive's and the recovery's corners."""
    short_round_trip_ms: float = 33.0
    medium_round_trip_ms: float = 37.0
    long_round_trip_ms: float = 41.0
    transition_hz: float = 4500.0             # F_C, ASSUMED (the Leem Pro three-spring tank's)
    allpass_coefficient: float = REFERENCE_ALLPASS_COEFFICIENT
    drive_corner_hz: float = 200.0            # the current drive's 6 dB/oct rise, ASSUMED corner
    recovery_highpass_hz: float = 70.7        # AP's 50-100 Hz, its geometric middle


def round_trips_ms(character):
    return (character.short_round_trip_ms, character.medium_round_trip_ms, character.long_round_trip_ms)


def damping_hz(character):
    """The loops' low-pass at brightness 0: the technique's neutral damping, an octave over F_C (DESIGN)."""
    return neutral_damping_hz(character.transition_hz)


class AccutronicsType9SpringTank(CircuitModule):
    """`<name>_left`, `<name>_right`, `<name>_level`, `<name>_driven`: see the module docstring."""

    references_entry = "references/circuits/accutronics-type-9-spring-tank.md"
    character_type = AccutronicsType9SpringTankCharacter
    nominal_length_s = NOMINAL_LENGTH_S
    wet_level_db = WET_LEVEL_DB

    def __init__(self, instance_name, *, input, length_s, brightness, clear, oversampling, kick=None,
                 character=None):
        inputs = dict(input=input, length_s=length_s, brightness=brightness, clear=clear)
        if kick is not None:
            inputs["kick"] = kick
        super().__init__(instance_name, character=character, **inputs)
        if oversampling != 1:
            raise BuildError(f"AccutronicsType9SpringTank {instance_name}: oversampling {oversampling!r} has no "
                             "design: the tank runs at the host rate (1)")
        self.oversampling = oversampling
        self.latency_samples = 0       # the wet only: its echoes come round the springs' loops, no direct path
        p = instance_name
        character = self.character
        trips = round_trips_ms(character)
        self.drive = ZeroDelayOnePoleFilter(f"{p}_drive", input=f"{p}_input",
                                            cutoff_hz=repr(generated_number(character.drive_corner_hz)))
        tank_input = f"{p}_driven" if kick is None else f"{p}_driven + {self.input_expressions['kick']}"
        self.tank = ParametricSpringReverb(
            f"{p}_tank", input=tank_input,
            damping_hz=f"{damping_hz(character)!r} * pow({BRIGHTNESS_RATIO}, {self.input_expressions['brightness']})",
            length_s=self.input_expressions["length_s"], clear=f"{p}_clear", round_trips_ms=trips,
            sections=tuple(sections_for_round_trip(trip) for trip in trips), pans=PANS,
            transition_hz=character.transition_hz, allpass_coefficient=character.allpass_coefficient,
            loop_sign=-1, decay_reference_hz=DECAY_REFERENCE_HZ)
        self.recovery = {side: ZeroDelayOnePoleFilter(f"{p}_{side}_recovery", input=f"{p}_tank_{side}",
                                                      cutoff_hz=repr(generated_number(character.recovery_highpass_hz)))
                         for side in ("left", "right")}

    def _filters(self):
        return [self.drive, self.recovery["left"], self.recovery["right"]]

    def functions(self):
        return self.tank.functions()

    def declarations(self):
        return "\n".join([self.substituted("History ${p}_level(0);")] + [f.declarations() for f in self._filters()]
                         + [self.tank.declarations()])

    def statements(self):
        resets = "\n".join(f.reset_statements() for f in self._filters()).replace("\n", "\n\t")
        return "\n".join([
            self.substituted("""// ${p}: an Accutronics type 9 spring tank, current drive (kit circuit module: Accutronics type 9 spring tank)
${p}_input = ${input};
${p}_clear = ${clear};
if (${p}_clear) {
	${resets}
}
// the drive: a current source rising 6 dB/oct into the coil, a first-order high-pass""", resets=resets),
            self.drive.statements(),
            self.substituted("${p}_driven = ${p}_drive_highpass;"),
            self.tank.statements(),
            "// the recovery: flat, then the maker's high-pass against rumble",
            self.recovery["left"].statements(),
            self.recovery["right"].statements(),
            self.substituted("""${p}_left = ${p}_left_recovery_highpass;
${p}_right = ${p}_right_recovery_highpass;
${p}_level = max(abs(${p}_left) + abs(${p}_right), ${p}_level * (1 - smoothing_coefficient(${fall_ms}, samplerate)));""",
                             fall_ms=LEVEL_METER_FALL_MS)])

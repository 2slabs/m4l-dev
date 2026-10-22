"""The Grampian Type 636 spring reverberation unit, the studio spring Lee Perry used (a circuit module): "a pair of
mechanical (spring) delay lines", 29 and 37 ms, driven by a constant-current amplifier, its reverberation 2 seconds at
300 Hz and its reverb path 100 Hz to 6 kHz, on the kit's parametric spring reverb
(references/circuits/grampian-636-spring-reverb.md).

What is sourced and what is assumed (the reference file tags each):
- from the maker's operating instructions (VERIFIED): the two delays, 29 and 37 ms; "Reverberation Time: 2 seconds at
  300 Hz"; the reverb path "100 Hz to 6K Hz ±3db"; the drive, a 500 mW "constant current" amplifier; "The lines are
  deliberately mismatched at their terminations to promote multiple reflections". That each delay is the echo
  spacing (the round trip) is our reading (UNVERIFIED);
- the drive: constant current is flat into the coil, so nothing shapes what goes in. The band's bottom is the
  springs' own: the loops' 40 Hz DC blocker takes a little more a trip the lower the note (measured, the wet's
  steady response to noise in third octaves against 1 kHz: within ±3 dB from 125 Hz to 5 kHz, -3.3 dB at 100 Hz,
  -7.4 dB at 6.3 kHz; a first-order high-pass at 100 Hz in front, tried, put 100 Hz some 3 dB lower still);
- F_C 6000 Hz: ASSUMED, the sheet's band edge read as the transition frequency (the main chirps end there; a spring's
  sound above F_C is the high-frequency chirps, 30 dB down, which the model leaves out). Parker 2011: F_C "above
  5kHz is rarely seen", so this is the high end;
- the dispersion: no Grampian spring has been measured; VPA10's coefficient 0.62 and its 100 sections for 56 ms,
  scaled to each spring (52, 66), and its negative loop gain;
- the decay: `length_s` is the T60 at 300 Hz, the sheet's own point; NOMINAL_LENGTH_S is the sheet's 2 s;
- the loops' damping (DESIGN, as the Accutronics tank's): at Bright 0 the technique's neutral damping, an octave
  over F_C, 12 kHz; Bright +1 opens it to VPA10's flat loss a trip, -1 brings it to F_C / 2;
- the mismatched terminations: no number to model them by; left out (the loops already reflect at both ends: an
  echo is a round trip).

The tank interface (the same for every spring tank module in the kit, so a device can switch tanks under one set of
controls):
- inputs: `input` (mono, what goes into the tank), `length_s` (the tank's T60 at 300 Hz, seconds: the springs' own
  frequency-dependent decay scaled to it; NOMINAL_LENGTH_S is the sheet's), `brightness` (-1..1: the loops' damping
  low-pass, an octave over F_C x 4^brightness), `clear` (true on a sample: empties the tank, every state at once and
  a round trip, 37 ms, with nothing read or written), `kick` (optional: a shock to the tank, see below);
- outputs: `<name>_left`, `<name>_right` (the wet only: 29 ms left, 37 ms right), `<name>_level` (a falling peak
  meter of both, 75.6 ms), `<name>_driven` (the coil's current: what goes into the springs);
- `latency_samples` 0: the output is the springs' echoes, with no direct path through the tank;
- `oversampling` (required): 1, the only rate it has a design for: the loops are linear and band-limited to F_C; the
  one non-linearity, the transducer's tanh, is the kit's first-order ADAA tanh, once, on the input. (The 636's
  overdriven input, Perry's distortion, is the drive in front of it: the device's.)
- `wet_level_db`: the wet's level against its input, measured (white noise, 0.5 s, at the nominal Length, 3 s of
  output, both sides), so a device switching tanks can match them.

The kick (Splash): a shock moves the tank's frame, so both springs are excited at once (references/circuits/
grampian-636-spring-reverb.md §4). `kick` is added to the input before the transducer's tanh: a burst with a peak of
2-4 clips there, then chirps down both springs. What reads as a kick: a few ms of noise with a fast-decaying envelope
plus a low thump (a 40-80 Hz half cycle), into `kick`, once. The sheet gives no recovery high-pass (a guitar amp's
tank has one against rumble), so the thump is kept short by the burst itself and the loops' 40 Hz blocker.
"""
import dataclasses

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.parametric_spring_reverb import (REFERENCE_ALLPASS_COEFFICIENT, ParametricSpringReverb,
                                                         neutral_damping_hz, sections_for_round_trip)

NOMINAL_LENGTH_S = 2.0                       # "Reverberation Time: 2 seconds at 300 Hz" (the operating instructions)
DECAY_REFERENCE_HZ = 300.0
BRIGHTNESS_RATIO = 4                         # the damping's corner x 4 per unit of brightness (2sl gate's law)
LEVEL_METER_FALL_MS = 75.6
PANS = (-1.0, 1.0)                           # 29 ms left, 37 ms right
WET_LEVEL_DB = -0.8                          # measured: tests/test_spring_tank_interface.py


@dataclasses.dataclass(frozen=True)
class Grampian636SpringReverbCharacter:
    """One unit: its two delay lines (the sheet's) and the stand-in dispersion (VPA10's coefficient, F_C ASSUMED at
    the band's edge)."""
    short_round_trip_ms: float = 29.0
    long_round_trip_ms: float = 37.0
    transition_hz: float = 6000.0             # F_C, ASSUMED: the sheet's 6 kHz band edge
    allpass_coefficient: float = REFERENCE_ALLPASS_COEFFICIENT


def round_trips_ms(character):
    return (character.short_round_trip_ms, character.long_round_trip_ms)


def damping_hz(character):
    """The loops' low-pass at brightness 0: the technique's neutral damping, an octave over F_C (DESIGN)."""
    return neutral_damping_hz(character.transition_hz)


class Grampian636SpringReverb(CircuitModule):
    """`<name>_left`, `<name>_right`, `<name>_level`, `<name>_driven`: see the module docstring."""

    references_entry = "references/circuits/grampian-636-spring-reverb.md"
    character_type = Grampian636SpringReverbCharacter
    nominal_length_s = NOMINAL_LENGTH_S
    wet_level_db = WET_LEVEL_DB

    def __init__(self, instance_name, *, input, length_s, brightness, clear, oversampling, kick=None,
                 character=None):
        inputs = dict(input=input, length_s=length_s, brightness=brightness, clear=clear)
        if kick is not None:
            inputs["kick"] = kick
        super().__init__(instance_name, character=character, **inputs)
        if oversampling != 1:
            raise BuildError(f"Grampian636SpringReverb {instance_name}: oversampling {oversampling!r} has no design: "
                             "the tank runs at the host rate (1)")
        self.oversampling = oversampling
        self.latency_samples = 0       # the wet only: its echoes come round the springs' loops, no direct path
        p = instance_name
        character = self.character
        trips = round_trips_ms(character)
        tank_input = f"{p}_driven" if kick is None else f"{p}_driven + {self.input_expressions['kick']}"
        self.tank = ParametricSpringReverb(
            f"{p}_tank", input=tank_input,
            damping_hz=f"{damping_hz(character)!r} * pow({BRIGHTNESS_RATIO}, {self.input_expressions['brightness']})",
            length_s=self.input_expressions["length_s"], clear=f"{p}_clear", round_trips_ms=trips,
            sections=tuple(sections_for_round_trip(trip) for trip in trips), pans=PANS,
            transition_hz=character.transition_hz, allpass_coefficient=character.allpass_coefficient,
            loop_sign=-1, decay_reference_hz=DECAY_REFERENCE_HZ)

    def functions(self):
        return self.tank.functions()

    def declarations(self):
        return "\n".join([self.substituted("History ${p}_level(0);"), self.tank.declarations()])

    def statements(self):
        return "\n".join([
            self.substituted("""// ${p}: a Grampian 636 spring reverb, constant-current drive (kit circuit module: Grampian 636 spring reverb)
${p}_clear = ${clear};
// the drive: constant current, flat into the coil
${p}_driven = ${input};"""),
            self.tank.statements(),
            self.substituted("""${p}_left = ${p}_tank_left;
${p}_right = ${p}_tank_right;
${p}_level = max(abs(${p}_left) + abs(${p}_right), ${p}_level * (1 - smoothing_coefficient(${fall_ms}, samplerate)));""",
                             fall_ms=LEVEL_METER_FALL_MS)])

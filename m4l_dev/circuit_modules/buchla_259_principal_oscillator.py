"""The Buchla 259's principal oscillator (a circuit module): sheet 2A "Principle Oscillator" of the original (rev
11/78): a triangle core bent into a sine by a shaper (references/circuits/buchla-259.md §5).

The 259's oscillators are triangle cores (a symmetry trimmer balances the rise, an expo pair, against the fall, a
current mirror) whose triangle a shaper bends into the sine the timbre section folds. A perfect shaper would be
sin(pi/2 x); a real one is trimmed by hand and keeps a little of its triangle. Here it is driven a little short of the
triangle's peaks: sin(k pi/2 x) / sin(k pi/2), k the character's `sine_shaper_drive` (0.95: odd harmonics only, the
3rd at -38.4 dB under the fundamental, the 5th at -48 dB, the 7th at -54 dB, falling 12 dB an octave like the rounded
corner they come from). No source gives a unit's number: 0.95 is 2sl gate's choice [DESIGN] (§5). The wave is
continuous with a small slope break at each peak, so run at 2x what folds back past the 2x Nyquist is under -80 dB:
no band-limiting.

Inputs: `frequency_hz` (the exponential converter's output) and `frequency_modulation_hz` (linear FM, through zero:
the phase may run backwards), each evaluated at every step, so a fast pitch sweep (a drum's) is followed exactly.
`oversampling` (a wiring choice) is how many steps the instrument runs it per host sample. `reset_statements()`
puts the phase at the start of the cycle (a hard sync: a note's start). Each `statements()` is one step; it leaves
`<name>_phase` (0..1, the instance's History), `<name>_phase_before`, `<name>_phase_step` (cycles this step,
negative when FM runs it backwards), `<name>_phase_unwrapped` (before the wrap: >= 1 or < 0 where it wrapped) and
`<name>_sine` (-1..1). `sine_at(phase)` is the sine at any phase, for an instrument that looks ahead.
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule

FUNCTIONS = {
    "buchla_259_principal_sine": """// the Buchla 259 principal oscillator's sine at phase (0..1): its triangle core through a shaper driven short of the peaks
buchla_259_principal_sine(phase, half_pi_drive, normalisation) {
\ttriangle = 1 - 4 * abs(phase + 0.25 - floor(phase + 0.25) - 0.5);
\treturn sin(half_pi_drive * triangle) * normalisation;
}""",
}


@dataclasses.dataclass(frozen=True)
class Buchla259PrincipalOscillatorCharacter:
    """One unit's build character."""
    sine_shaper_drive: float = 0.95      # 1: a perfect sine; below, the triangle's peaks stay a little sharp [DESIGN]

    @property
    def sine_shaper_half_pi_drive(self):
        return self.sine_shaper_drive * math.pi / 2

    @property
    def sine_shaper_normalisation(self):
        """1 / the shaper's output at the triangle's peak: the sine peaks at 1."""
        return 1.0 / math.sin(self.sine_shaper_drive * math.pi / 2)


def shaped_sine(phase, character):
    """The sine at phase 0..1, in Python: the triangle core, shaped."""
    triangle = 1 - 4 * abs((phase + 0.25) % 1.0 - 0.5)
    return math.sin(character.sine_shaper_half_pi_drive * triangle) * character.sine_shaper_normalisation


class Buchla259PrincipalOscillator(CircuitModule):
    """One step: `<name>_sine` at `frequency_hz` + `frequency_modulation_hz`, `oversampling` steps a host sample.
    See the module's docstring for every output."""

    references_entry = "references/circuits/buchla-259.md"
    character_type = Buchla259PrincipalOscillatorCharacter

    def __init__(self, instance_name, *, frequency_hz, frequency_modulation_hz, oversampling=1, character=None):
        super().__init__(instance_name, character=character, frequency_hz=frequency_hz,
                         frequency_modulation_hz=frequency_modulation_hz)
        if not isinstance(oversampling, int) or oversampling < 1:
            raise BuildError(f"Buchla259PrincipalOscillator {instance_name}: oversampling is a whole number of steps "
                             f"a sample, got {oversampling!r}")
        if not 0 < self.character.sine_shaper_drive <= 1:
            raise BuildError(f"Buchla259PrincipalOscillator {instance_name}: the sine shaper's drive is in (0, 1], "
                             f"got {self.character.sine_shaper_drive!r}")
        self.oversampling = oversampling

    def functions(self):
        return dict(FUNCTIONS)

    def declarations(self):
        return self.substituted("History ${p}_phase(0);")

    def sine_at(self, phase):
        """GenExpr: the sine at `phase` (cycles; any value, it wraps)."""
        return (f"buchla_259_principal_sine({phase}, {self.character.sine_shaper_half_pi_drive!r}, "
                f"{self.character.sine_shaper_normalisation!r})")

    def statements(self):
        p = self.instance_name
        return self.substituted("""// ${p}: the Buchla 259's principal oscillator, one step (kit circuit module: Buchla 259 principal oscillator)
${p}_phase_before = ${p}_phase;
${p}_phase_step = (${frequency_hz} + ${frequency_modulation_hz}) / (samplerate * ${oversampling});
${p}_phase_unwrapped = ${p}_phase + ${p}_phase_step;
${p}_phase = ${p}_phase_unwrapped - floor(${p}_phase_unwrapped);
${p}_sine = """, oversampling=str(self.oversampling)) + self.sine_at(f"{p}_phase") + ";"

    def reset_statements(self):
        """The phase back to the cycle's start (run before this sample's steps)."""
        return self.substituted("${p}_phase = 0;")

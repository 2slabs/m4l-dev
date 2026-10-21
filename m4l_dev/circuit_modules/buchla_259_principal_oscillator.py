"""The Buchla 259's principal oscillator (a circuit module): sheet 2A "Principle Oscillator" of the original (rev
11/78): a triangle core bent into a sine by a shaper (references/circuits/buchla-259.md §5).

The 259's oscillators are triangle cores (a symmetry trimmer balances the rise, an expo pair, against the fall, a
current mirror) whose triangle a shaper bends into the sine the timbre section folds. A perfect shaper would be
sin(pi/2 x); a real one is trimmed by hand and keeps a little of its triangle. Here it is driven a little short of the
triangle's peaks: sin(k pi/2 x) / sin(k pi/2), k the character's `sine_shaper_drive` (0.95: odd harmonics only, the
3rd at -38.4 dB under the fundamental, the 5th at -48 dB, the 7th at -54 dB, falling 12 dB an octave like the rounded
corner they come from). No source gives a unit's number: 0.95 is 2sl gate's choice [DESIGN] (§5). The drive is a
run-time character field (`character_inputs={"sine_shaper_drive": ...}`, in (0, 1]: the instrument keeps it there),
so an instrument may turn the shaper from a sine (1) toward its triangle core (near 0).

Band-limited: the shaped wave is continuous with a slope break at each of the triangle's peaks (phase 1/4 and 3/4),
where its slope turns by 8 K cot K a cycle (K = drive x pi / 2; none for a perfect sine), and a hard sync jumps it to
0. The kit's band-limited edges technique rounds both (4-point polyBLAMP at the corners, polyBLEP at a reset's jump),
found on the exact phase, so FM and sweeps stay exact. Measured (48 kHz, the worst alias under 20 kHz re the
fundamental; tests/test_circuit_module_buchla_259_principal_oscillator.py): a 5 kHz wave at drive 0.05, 1x, -33 dB
trivial -> -72 dB; at drive 0.95 (2sl gate's), 2x, -68.5 -> -119 dB. The technique needs two steps of look-ahead, so
`<name>_sine` is `latency_steps` steps late: it is the wave at `<name>_sine_phase` (with `<name>_sine_phase_before`,
`_sine_phase_step`, `_sine_phase_unwrapped`), the phase that many steps ago, for an instrument that builds other
waves in step with it; an instrument delays what it mixes with the sine (an AM) by as many steps.

Inputs: `frequency_hz` (the exponential converter's output) and `frequency_modulation_hz` (linear FM, through zero:
the phase may run backwards), each evaluated at every step, so a fast pitch sweep (a drum's) is followed exactly.
`oversampling` (a wiring choice, required) is how many steps the instrument runs it per host sample. `reset_statements()`
puts the phase at the start of the cycle (a hard sync: a note's start; it reaches `<name>_sine` `latency_steps` steps
later, its jump band-limited). Each `statements()` is one step; it leaves the oscillator's phase now: `<name>_phase`
(0..1, the instance's History), `<name>_phase_before`, `<name>_phase_step` (cycles this step, negative when FM runs
it backwards), `<name>_phase_unwrapped` (before the wrap: >= 1 or < 0 where it wrapped), for an instrument that
predicts ahead from now (a probe of the wave's mean); and the band-limited `<name>_sine` (-1..1) with its phase
quartet, `latency_steps` late. `sine_at(phase)` is the trivial shaped wave at any phase (the probe's). A step crosses
at most one peak and one trough: at a step over half a cycle (above the steps' Nyquist) a corner is missed.
"""
import dataclasses
import math

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.band_limited_edges import BandLimitedEdges

PHASE_QUARTET = ("phase", "phase_before", "phase_step", "phase_unwrapped")

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
    """The trivial sine at phase 0..1, in Python: the triangle core, shaped."""
    triangle = 1 - 4 * abs((phase + 0.25) % 1.0 - 0.5)
    return math.sin(character.sine_shaper_half_pi_drive * triangle) * character.sine_shaper_normalisation


class Buchla259PrincipalOscillator(CircuitModule):
    """One step: the phase now, and `<name>_sine`, band-limited, `latency_steps` steps late, at `frequency_hz` +
    `frequency_modulation_hz`, `oversampling` steps a host sample. See the module's docstring for every output."""

    references_entry = "references/circuits/buchla-259.md"
    character_type = Buchla259PrincipalOscillatorCharacter
    runtime_character_fields = ("sine_shaper_drive",)

    def __init__(self, instance_name, *, frequency_hz, frequency_modulation_hz, oversampling, character=None,
                 character_inputs=None):
        super().__init__(instance_name, character=character, character_inputs=character_inputs,
                         frequency_hz=frequency_hz, frequency_modulation_hz=frequency_modulation_hz)
        if isinstance(oversampling, bool) or not isinstance(oversampling, int) or oversampling < 1:
            raise BuildError(f"Buchla259PrincipalOscillator {instance_name}: oversampling (required: the "
                             f"steps the instrument runs it a host sample) is a whole number >= 1, got {oversampling!r}")
        if not 0 < self.character.sine_shaper_drive <= 1:
            raise BuildError(f"Buchla259PrincipalOscillator {instance_name}: the sine shaper's drive is in (0, 1], "
                             f"got {self.character.sine_shaper_drive!r}")
        self.oversampling = oversampling
        p = instance_name
        self.edges = BandLimitedEdges(f"{p}_edges", naive=f"{p}_naive", oversampling=oversampling)
        # `<name>_sine` is the edges' look-ahead late: in steps (the instrument's rings) and in host samples
        self.latency_steps = self.edges.latency_steps
        self.latency_samples = self.edges.latency_samples
        # the triangle's peak (phase 1/4) turns the slope down, its trough (3/4) up; a reset jumps to the cycle's
        # start (the sine's 0) at this very step (fraction 0): a host sample's reset acts at its first step's time,
        # the sample's own (architecture/dsp-blocks.md, "Latency is always said")
        self.edges.add_corner(f"{p}_peak_crossed", f"{p}_peak_fraction", f"-{p}_corner_size")
        self.edges.add_corner(f"{p}_trough_crossed", f"{p}_trough_fraction", f"{p}_corner_size")
        self.edges.add_jump(f"{p}_reset_pending", "0", f"-{p}_naive_before")

    def _half_pi_drive_term(self):
        """GenExpr: the shaper's K = drive x pi / 2 from the build's drive or the run-time drive's expression, in the
        character property's arithmetic order (so a run-time drive equal to the build's renders the same bits, and
        the code holds the drive as given, not a product a maths library rounds)."""
        return f"({self.character_term('sine_shaper_drive')} * pi / 2)"

    def _normalisation_term(self):
        return f"(1.0 / sin({self._half_pi_drive_term()}))"

    def functions(self):
        return dict(FUNCTIONS, **self.edges.functions())

    def declarations(self):
        p = self.instance_name
        rings = ", ".join(f"{p}_{name}_ring_{age}(0)" for name in PHASE_QUARTET for age in range(1, self.latency_steps + 1))
        return (f"History {p}_phase(0), {p}_naive_before(0), {p}_reset_pending(0), {rings};\n"
                + self.edges.declarations())

    def sine_at(self, phase):
        """GenExpr: the trivial shaped wave at `phase` (cycles; any value, it wraps)."""
        return f"buchla_259_principal_sine({phase}, {self._half_pi_drive_term()}, {self._normalisation_term()})"

    def _phase_quartet_ring_statements(self):
        """The phase quartet `latency_steps` steps ago (`<name>_sine_phase...`), read before this step's is pushed, as
        the edges' ring gives its sample."""
        p, lines = self.instance_name, []
        for name in PHASE_QUARTET:
            lines.append(f"{p}_sine_{name} = {p}_{name}_ring_{self.latency_steps};")
            for age in range(self.latency_steps, 1, -1):
                lines.append(f"{p}_{name}_ring_{age} = {p}_{name}_ring_{age - 1};")
            lines.append(f"{p}_{name}_ring_1 = {p}_{name};")
        return "\n".join(lines)

    def statements(self):
        p = self.instance_name
        return (self.substituted("""// ${p}: the Buchla 259's principal oscillator, one step (kit circuit module: Buchla 259 principal oscillator)
${p}_half_pi_drive = """) + self._half_pi_drive_term() + ";\n" + f"{p}_normalisation = " + self._normalisation_term()
                + ";\n" + self.substituted("""${p}_phase_before = ${p}_phase;
// a reset's step is the cycle's start: it stands at phase 0 and advances nothing
${p}_phase_step = ${p}_reset_pending > 0 ? 0 : (${frequency_hz} + ${frequency_modulation_hz}) / (samplerate * ${oversampling});
${p}_phase_unwrapped = ${p}_phase + ${p}_phase_step;
${p}_phase = ${p}_phase_unwrapped - floor(${p}_phase_unwrapped);
${p}_naive = buchla_259_principal_sine(${p}_phase, ${p}_half_pi_drive, ${p}_normalisation);
// its corners: the triangle's peak (1/4) and trough (3/4), where the slope turns by 8 K cot K a cycle
${p}_step_divisor = ${p}_phase_step != 0 ? ${p}_phase_step : 1;
${p}_corner_size = 8 * ${p}_half_pi_drive * ${p}_normalisation * cos(${p}_half_pi_drive) * abs(${p}_phase_step);
${p}_peak_crossed = floor(${p}_phase_before - 0.25) != floor(${p}_phase_unwrapped - 0.25);
${p}_peak_fraction = (${p}_phase_unwrapped - 0.25 - max(floor(${p}_phase_before - 0.25), floor(${p}_phase_unwrapped - 0.25))) / ${p}_step_divisor;
${p}_trough_crossed = floor(${p}_phase_before - 0.75) != floor(${p}_phase_unwrapped - 0.75);
${p}_trough_fraction = (${p}_phase_unwrapped - 0.75 - max(floor(${p}_phase_before - 0.75), floor(${p}_phase_unwrapped - 0.75))) / ${p}_step_divisor;
""", oversampling=str(self.oversampling)) + self.edges.statements() + self.substituted("""
${p}_reset_pending = 0;
${p}_naive_before = ${p}_naive;
${p}_sine = ${p}_edges_out;
""") + self._phase_quartet_ring_statements())

    def reset_statements(self):
        """The phase back to the cycle's start (run before this sample's steps): the next step stands at phase 0
        (the host sample's own time, its first step), its jump, from the wave's last value to 0, band-limited there;
        it reaches `<name>_sine` `latency_steps` steps later."""
        return self.substituted("${p}_phase = 0;\n${p}_reset_pending = 1;")

"""The Buchla 259's modulation oscillator (a circuit module): sheet 4A "Order + Modulator" of the original (rev
11/78): the second oscillator, whose wave the 259 routes into the principal oscillator's pitch (FM), its amplitude (AM)
and its timbre (references/circuits/buchla-259.md §5).

Its waves: sine, triangle, saw, square (`wave` 0..3). The 259's modulation oscillator gives a saw and a square, and
in its "Both" mode a ramp and a triangle (the repair notes, §5 [SECONDARY]); the sine is 2sl gate's [DESIGN]. Each
is the trivial wave on the phase, its jumps (saw, square) and corners (triangle) band-limited by the kit's
band-limited edges technique; the wave is computed `LOOK_AHEAD_STEPS` steps ahead of the phase so the band-limited
output (that many steps late) is the oscillator now: an FM or AM it drives stays in step with what it modulates.

Inputs: `frequency_hz` (evaluated at every step: a sweep is followed exactly) and `wave`. `oversampling` (a wiring
choice, required) is how many steps the instrument runs it per host sample. `reset_statements()` restarts the cycle (a hard
sync: a note's start), with nothing of the old wave after it. Each `statements()` is one step: `<name>_out` (-1..1)
and `<name>_phase` (0..1, the instance's History). `wave_at(phase)` and `wave_integral_at(phase)` are the trivial wave
and its running integral over a cycle (each wave has zero mean, so the integral is periodic: what a linear FM it
drives adds to the modulated phase), for an instrument that looks ahead.

No unit-to-unit character is modelled (the original's capacitive tilt on squares and its distortion at the lowest
frequencies, west-coast notes in §5, are not).
"""
import dataclasses

from m4l_dev.build_error import BuildError
from m4l_dev.gen_blocks import CircuitModule
from m4l_dev.techniques.band_limited_edges import LOOK_AHEAD_STEPS, BandLimitedEdges

WAVES = ("sine", "triangle", "saw", "square")

FUNCTIONS = {
    "buchla_259_modulation_wave": """// the Buchla 259 modulation oscillator's trivial wave at phase (0..1): 0 sine, 1 triangle, 2 saw, 3 square
buchla_259_modulation_wave(phase, wave) {
\ty = 0;
\tif (wave < 0.5) {
\t\ty = sin(6.283185307 * phase);
\t} else if (wave < 1.5) {
\t\ty = 1 - 4 * abs(phase - 0.5);
\t} else if (wave < 2.5) {
\t\ty = 2 * phase - 1;
\t} else {
\t\ty = phase < 0.5 ? -1 : 1;
\t}
\treturn y;
}""",
    "buchla_259_modulation_wave_integral": """// the trivial wave's running integral over one cycle at phase (0..1), in cycles: periodic (each wave has zero mean)
buchla_259_modulation_wave_integral(phase, wave) {
\ty = 0;
\tif (wave < 0.5) {
\t\ty = (1 - cos(6.283185307 * phase)) / 6.283185307;
\t} else if (wave < 1.5) {
\t\ty = phase < 0.5 ? 2 * phase * phase - phase : 3 * phase - 2 * phase * phase - 1;
\t} else if (wave < 2.5) {
\t\ty = phase * phase - phase;
\t} else {
\t\ty = phase < 0.5 ? -phase : phase - 1;
\t}
\treturn y;
}""",
}


@dataclasses.dataclass(frozen=True)
class Buchla259ModulationOscillatorCharacter:
    """One unit's build character: none modelled yet (see the module's docstring)."""


class Buchla259ModulationOscillator(CircuitModule):
    """One step: `<name>_out`, the band-limited `wave` at `frequency_hz`, `oversampling` steps a host sample. See the
    module's docstring."""

    references_entry = "references/circuits/buchla-259.md"
    character_type = Buchla259ModulationOscillatorCharacter

    def __init__(self, instance_name, *, frequency_hz, wave, oversampling, character=None):
        super().__init__(instance_name, character=character, frequency_hz=frequency_hz, wave=wave)
        if isinstance(oversampling, bool) or not isinstance(oversampling, int) or oversampling < 1:
            raise BuildError(f"Buchla259ModulationOscillator {instance_name}: oversampling (required: the "
                             f"steps the instrument runs it a host sample) is a whole number >= 1, got {oversampling!r}")
        self.oversampling = oversampling
        p, wave_input = instance_name, self.input_expressions["wave"]
        self.edges = BandLimitedEdges(f"{p}_edges", naive=f"{p}_naive", oversampling=oversampling)
        self.latency_samples = 0       # the wave runs the edges' look-ahead ahead of the phase: the output is now
        wrapped, halfway = f"{p}_lead_wrapped", f"{p}_lead_halfway"
        wrap_fraction, halfway_fraction = f"{p}_lead_phase / {p}_step", f"({p}_lead_phase - 0.5) / {p}_step"
        saw_or_square, square = f"{wave_input} > 1.5", f"{wave_input} > 2.5"
        triangle = f"({wave_input} > 0.5 && {wave_input} < 1.5)"
        self.edges.add_jump(wrapped, wrap_fraction, f"({saw_or_square} ? -2 : 0)")            # saw and square: down by 2
        self.edges.add_jump(halfway, halfway_fraction, f"({square} ? 2 : 0)")                 # square: up by 2
        self.edges.add_corner(wrapped, wrap_fraction, f"({triangle} ? 8 * {p}_step : 0)")      # the triangle's foot
        self.edges.add_corner(halfway, halfway_fraction, f"({triangle} ? -8 * {p}_step : 0)")  # and its peak

    def functions(self):
        return dict(FUNCTIONS, **self.edges.functions())

    def declarations(self):
        return self.substituted("History ${p}_phase(0), ${p}_lead_phase(0), ${p}_reset_pending(0);\n") + self.edges.declarations()

    def wave_at(self, phase):
        """GenExpr: the trivial wave at `phase` (0..1)."""
        return f"buchla_259_modulation_wave({phase}, {self.input_expressions['wave']})"

    def wave_integral_at(self, phase):
        """GenExpr: the trivial wave's running integral at `phase` (0..1), in cycles."""
        return f"buchla_259_modulation_wave_integral({phase}, {self.input_expressions['wave']})"

    def _step_expression(self):
        return self.substituted("${frequency_hz} / (samplerate * ${oversampling})", oversampling=str(self.oversampling))

    def statements(self):
        p = self.instance_name
        return (self.substituted("""// ${p}: the Buchla 259's modulation oscillator, one step (kit circuit module: Buchla 259 modulation oscillator)
${p}_step = """) + self._step_expression() + self.substituted(""";
// a reset's step is the cycle's start: it stands at phase 0 and advances nothing
${p}_phase = ${p}_reset_pending > 0 ? 0 : ${p}_phase + ${p}_step - floor(${p}_phase + ${p}_step);
${p}_reset_pending = 0;
// the trivial wave runs LOOK_AHEAD steps ahead of the phase, so the band-limited wave (that many steps late) is now
${p}_lead_before = ${p}_lead_phase;
${p}_lead_phase = wrap(${p}_phase + ${look_ahead} * ${p}_step, 0, 1);
${p}_naive = """, look_ahead=str(LOOK_AHEAD_STEPS)) + self.wave_at(f"{p}_lead_phase") + self.substituted(""";
${p}_lead_wrapped = ${p}_lead_phase < ${p}_lead_before;
${p}_lead_halfway = ${p}_lead_before < 0.5 && ${p}_lead_phase >= 0.5;
""") + self.edges.statements() + f"\n{p}_out = {p}_edges_out;")

    def reset_statements(self):
        """The cycle restarted (run before this sample's steps): the next step stands at phase 0 (the host sample's
        own time, its first step: architecture/dsp-blocks.md, "Latency is always said"), the band-limited ring
        holding the restarted wave's values from phase 0, nothing of the old wave after it."""
        p = self.instance_name
        step = f"{p}_reset_step"
        return (f"{step} = {self._step_expression()};\n{p}_phase = 0;\n"
                f"{p}_reset_pending = 1;\n{p}_lead_phase = {LOOK_AHEAD_STEPS - 1} * {step};\n"
                + self.edges.restart_statements([self.wave_at(f"{ahead} * {step}")
                                                 for ahead in range(LOOK_AHEAD_STEPS)]))

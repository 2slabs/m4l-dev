"""The pitch modulator (a technique): a drum hit's modulation of its oscillator's pitch, or of any other target, by
one of six shapes, restarted on every hit (references/dsp.md, "Pitch modulator").

Shapes (`shape`, any time): Microtonic's three (Sonic Charge, Microtonic User Guide v3.3.4, p. 17) and the ER-1's
cyclic three (Korg ER-1 owner's manual pp. 24-25), as 2sl drums references/er1-microtonic-genopatch.md §1 reads them:
- 0 decay: starts at `amount` and bends to 0 over `decay_ms` (MT-UG: "the time it takes the oscillator to go from
  the highest frequency down to the base frequency"; a negative amount goes upwards). The bend is the drum
  envelope's exponential reversed, amount x rise(1 - t / decay_ms) (drum_envelope.py), which reaches 0 at decay_ms;
  the guide does not give the curve [UNVERIFIED].
- 1 sine, 2 triangle, 3 square, 4 saw down: cyclic at `rate_hz`, each starting at +amount, so rate 0 holds the
  initial offset (MT-UG: "the minimum rate setting makes the oscillator stick to its initial frequency"). The square
  and the saw's jumps and the triangle's corners are band-limited (BandLimitedEdges): at the ER-1's audio rates (to
  5 kHz) they would alias.
- 5 random: low-pass-filtered white noise whose cutoff is `rate_hz` (MT-UG: "Random Pitch Modulation uses a low-pass
  filtered noise as the modulation source ... the rate controls the cut-off frequency"); at rate 0 one random value
  a hit ("At zero rate, it simply randomizes the pitch by the chosen amount every time the drum patch is
  triggered"). Ours: y <- (1 - c) y + sqrt(c (2 - c)) w, c = 1 - exp(-2 pi rate / sr), w the seeded white noise,
  which keeps y's variance 1/3 (that of a uniform draw in [-1, 1]) at every rate; a hit starts y at a fresh draw.
  The noise is `SeededWhiteNoise` on `seed` (architecture/seeded-random.md: the device's seeded sequence draws it).

Output `<name>_offset` = amount x shape, in the amount's units: semitones for an oscillator's pitch
(`<name>_frequency_ratio` = 2^(offset / 12) multiplies its frequency), or any target's units: random at rate 0 is a
per-hit random offset of strength `amount` for a filter's cutoff or anything else (the ADX-1's per-hit random, 2sl
drums references/adx1.md §6.5). The shape runs two samples ahead inside the edges' look-ahead ring, so the offset
comes out now, and a hit restarts it at this very sample.
"""
import math

from m4l_dev.gen_blocks import Technique
from m4l_dev.techniques.band_limited_edges import LOOK_AHEAD_STEPS, BandLimitedEdges
from m4l_dev.techniques.drum_envelope import FUNCTIONS as DRUM_ENVELOPE_FUNCTIONS
from m4l_dev.techniques.seeded_white_noise import SeededWhiteNoise

SHAPES = {"decay": 0, "sine": 1, "triangle": 2, "square": 3, "saw_down": 4, "random": 5}
HIGHEST_RATE_OF_SAMPLE_RATE = 0.5
SHORTEST_DECAY_MS = 0.1

WAVE_FUNCTION = """// the pitch modulator's cyclic shapes at a phase in [0, 1), each +1 at phase 0 (kit technique: pitch modulator)
pitch_modulator_wave(shape, phase) {
\tsine = cos(twopi * phase);
\ttriangle = 4 * abs(phase - 0.5) - 1;
\tsquare = phase < 0.5 ? 1 : -1;
\tsaw_down = 1 - 2 * phase;
\treturn shape == 1 ? sine : (shape == 2 ? triangle : (shape == 3 ? square : saw_down));
}"""


def wave(shape, phase):
    """The Python model of pitch_modulator_wave."""
    if shape == SHAPES["sine"]:
        return math.cos(2 * math.pi * phase)
    if shape == SHAPES["triangle"]:
        return 4 * abs(phase - 0.5) - 1
    if shape == SHAPES["square"]:
        return 1.0 if phase < 0.5 else -1.0
    return 1 - 2 * phase


class PitchModulator(Technique):
    """`<name>_offset` (amount x shape, now), `<name>_frequency_ratio` (2^(offset / 12)). Inputs: `hit` (true on a hit's
    sample), `shape` (0 decay, 1 sine, 2 triangle, 3 square, 4 saw down, 5 random), `amount` (semitones for pitch),
    `decay_ms` (the decay shape's time), `rate_hz` (the cyclic shapes' rate, the random shape's cutoff; held to
    [0, sr / 2]), `seed` (the random shape's noise). State: the phase, the decay's progress, the random value, the
    edges' ring, the noise."""

    def __init__(self, instance_name, hit, shape, amount, decay_ms, rate_hz, seed):
        super().__init__(instance_name, hit=hit, shape=shape, amount=amount, decay_ms=decay_ms, rate_hz=rate_hz,
                         seed=seed)
        self.latency_samples = 0       # the shape runs ahead inside the edges' ring: the offset is now
        p = instance_name
        self.noise = SeededWhiteNoise(f"{p}_noise", seed=seed)
        self.edges = BandLimitedEdges(f"{p}_edges", naive=f"{p}_naive", oversampling=1)
        square, saw, triangle = (f"{p}_shape == {SHAPES[name]}" for name in ("square", "saw_down", "triangle"))
        # the half-way point: the square falls by 2, the triangle's slope turns from -4 to +4 a cycle
        self.edges.add_jump(f"{p}_crossed_half && ({square})", f"{p}_half_fraction", f"-2 * {p}_amount")
        self.edges.add_corner(f"{p}_crossed_half && ({triangle})", f"{p}_half_fraction", f"8 * {p}_amount * {p}_step")
        # the wrap: the square and the saw rise by 2, the triangle's slope turns from +4 to -4 a cycle
        self.edges.add_jump(f"{p}_wrapped && (({square}) || ({saw}))", f"{p}_wrap_fraction", f"2 * {p}_amount")
        self.edges.add_corner(f"{p}_wrapped && ({triangle})", f"{p}_wrap_fraction", f"-8 * {p}_amount * {p}_step")

    def functions(self):
        return dict(DRUM_ENVELOPE_FUNCTIONS, pitch_modulator_wave=WAVE_FUNCTION, **self.edges.functions())

    def declarations(self):
        return "\n".join((self.substituted("History ${p}_phase(0), ${p}_decay_progress(1), ${p}_random_value(0);"),
                          self.noise.declarations(), self.edges.declarations()))

    def _shape_ahead(self, phase, progress, random_value):
        """GenExpr: the naive shape at a phase, a decay progress and a random value."""
        p = self.instance_name
        return (f"{p}_amount * ({p}_shape == 0 ? drum_envelope_exponential_rise(1 - {progress}) : "
                f"({p}_shape == 5 ? {random_value} : pitch_modulator_wave({p}_shape, {phase})))")

    def statements(self):
        p = self.instance_name
        restart = self.edges.restart_statements([self._shape_ahead("0", "0", f"{p}_random_value"),
                                                 self._shape_ahead(f"{p}_step", f"{p}_decay_step",
                                                                   f"{p}_random_value")])
        restart = "\n".join("\t" + line for line in restart.splitlines())
        return "\n".join((self.substituted("// ${p}: pitch modulator, six shapes restarted on a hit (kit technique: pitch modulator)"),
                          self.noise.statements(), self.substituted(f"""${{p}}_shape = clamp(floor(${{shape}} + 0.5), 0, 5);
${{p}}_amount = ${{amount}};
${{p}}_step = clamp(${{rate_hz}}, 0, samplerate * {HIGHEST_RATE_OF_SAMPLE_RATE!r}) / samplerate;
${{p}}_decay_step = 1000 / (max(${{decay_ms}}, {SHORTEST_DECAY_MS!r}) * samplerate);
${{p}}_random_coefficient = 1 - exp(-twopi * ${{p}}_step);
if (${{hit}}) {{
	${{p}}_random_value = ${{p}}_noise_out;
{restart}
	// the ring now holds the restarted shape's first {LOOK_AHEAD_STEPS} samples; the state stands one step on
	${{p}}_phase = ${{p}}_step;
	${{p}}_decay_progress = ${{p}}_decay_step;
}} else {{
	${{p}}_random_value = (1 - ${{p}}_random_coefficient) * ${{p}}_random_value + sqrt(${{p}}_random_coefficient * (2 - ${{p}}_random_coefficient)) * ${{p}}_noise_out;
}}
${{p}}_phase_before = ${{p}}_phase;
${{p}}_phase = ${{p}}_phase + ${{p}}_step;
${{p}}_wrapped = ${{p}}_phase >= 1;
${{p}}_phase = ${{p}}_phase - floor(${{p}}_phase);
// a step is at most half a cycle, so one step crosses the half-way point or wraps, never both
${{p}}_crossed_half = !${{p}}_wrapped && ${{p}}_phase_before < 0.5 && ${{p}}_phase >= 0.5;
${{p}}_half_fraction = (${{p}}_phase - 0.5) / max(${{p}}_step, 1e-12);
${{p}}_wrap_fraction = ${{p}}_phase / max(${{p}}_step, 1e-12);
${{p}}_decay_progress = min(${{p}}_decay_progress + ${{p}}_decay_step, 1);
${{p}}_naive = {self._shape_ahead(f"{p}_phase", f"{p}_decay_progress", f"{p}_random_value")};"""),
                          self.edges.statements(),
                          self.substituted("""${p}_offset = ${p}_edges_out;
${p}_frequency_ratio = pow(2, ${p}_offset / 12);""")))

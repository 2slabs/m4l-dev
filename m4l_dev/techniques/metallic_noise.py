"""Metallic noise (a technique): pitched digital noise sources with a metallic, multi-tone colour, for a drum voice's
noise path (references/dsp.md, "Metallic noise").

**The seam.** Every metallic source here has one interface, so an instrument swaps one for another (and the patch
matcher can choose between them on its targets): constructed as `Source(name, hit=..., tune_hz=..., pattern=...)`;
`hit` restarts it (each hit sounds the same), `tune_hz` pitches it (the ADX-1's metal has its own Tune, 2sl drums
references/adx1.md §6), `pattern` picks its colour; its output `<name>_out` is in [-1, 1], two samples late (its
edges are band-limited). `METALLIC_NOISE_SOURCES` lists them; tests/test_techniques.py holds each to the interface.
The ADX-1's metal mechanism is unpublished (adx1.md §6.1): when one is chosen, it is a second class here with this
interface, added to the tuple. Two instances in one voice are two names (the ADX-1 Metal voice runs two sources).

**LfsrMetallicNoise** (after the Jomox MBase 11's MetNze, manual p. 11, quoted in 2sl drums
references/kick-jomox-drumazon.md §1.2: 000 = random noise; above it a "complex signal made from high pitch digital
multi tones and the bit pattern of the value", each value its own pattern, a "caleidoscope" rather than a sweep).
The manual gives no circuit; this law is ours [UNVERIFIED as Jomox's]: an 8-bit shift register clocked at `tune_hz`
(at most once a sample), its feedback the parity (XOR) of the bits the pattern's bits select, the output its lowest
bit as +-1. Each pattern 1..255 is its own feedback, so its own cycle (a cycle of length L is a tone series at
tune_hz / L: the "multi tones"), and neighbouring values are unrelated spectra. A register that falls into a constant
state (0, or 255 under an odd parity) is reloaded with the pattern. A hit loads the pattern and restarts the clock.
Pattern 0 is white noise in the Jomox; that is the instrument's choice of `SeededWhiteNoise` (seeded_white_noise.py),
not this block's. The steps are jumps of 2, band-limited by `BandLimitedEdges` at their place inside the sample.
"""
from m4l_dev.gen_blocks import Technique
from m4l_dev.techniques.band_limited_edges import BandLimitedEdges

REGISTER_BITS = 8
HIGHEST_TUNE_OF_SAMPLE_RATE = 1.0     # one register step a sample at most


def lfsr_cycle(pattern, start=None, steps=600):
    """The Python model: the register's states from `start` (default: the pattern) for `steps` steps."""
    state = pattern if start is None else start
    states = []
    for _ in range(steps):
        parity = bin(state & pattern).count("1") % 2
        following = (state >> 1) | (parity << (REGISTER_BITS - 1))
        if following == 0 or following == state:
            following = pattern
        state = following
        states.append(state)
    return states


def bit_of(expression, bit):
    """GenExpr for bit `bit` (0 = lowest) of a whole number 0..255 held in `expression`."""
    return f"(floor({expression} / {2 ** bit}) - 2 * floor({expression} / {2 ** (bit + 1)}))"


class LfsrMetallicNoise(Technique):
    """`<name>_out` in [-1, 1], two samples late: the shift register's output bit at `tune_hz` (clamped to
    [0, samplerate]), feedback taps the bits of `pattern` (rounded, held to 1..255). `hit` loads the pattern and
    restarts the clock. State: the register, the clock's phase, the edges' ring."""

    def __init__(self, instance_name, hit, tune_hz, pattern):
        super().__init__(instance_name, hit=hit, tune_hz=tune_hz, pattern=pattern)
        self.edges = BandLimitedEdges(f"{instance_name}_edges", naive=f"{instance_name}_naive")
        self.edges.add_jump(f"{instance_name}_stepped && {instance_name}_naive != {instance_name}_naive_before",
                            f"{instance_name}_step_fraction",
                            f"{instance_name}_naive - {instance_name}_naive_before")

    def functions(self):
        return self.edges.functions()

    def declarations(self):
        return self.substituted("History ${p}_register(1), ${p}_clock_phase(0);") + "\n" + self.edges.declarations()

    def statements(self):
        p = self.instance_name
        parity_terms = " + ".join(f"{bit_of(f'{p}_register', bit)} * {bit_of(f'{p}_pattern', bit)}"
                                  for bit in range(REGISTER_BITS))
        top = 2 ** (REGISTER_BITS - 1)
        return self.substituted(f"""// ${{p}}: metallic noise, an 8-bit shift register at the tune (kit technique: metallic noise)
${{p}}_pattern = clamp(floor(${{pattern}} + 0.5), 1, {2 ** REGISTER_BITS - 1});
${{p}}_step = clamp(${{tune_hz}}, 0, samplerate * {HIGHEST_TUNE_OF_SAMPLE_RATE!r}) / samplerate;
if (${{hit}}) {{
	${{p}}_register = ${{p}}_pattern;
	${{p}}_clock_phase = 0;
}}
${{p}}_naive_before = 2 * {bit_of(f'{p}_register', 0)} - 1;
${{p}}_clock_phase = ${{p}}_clock_phase + ${{p}}_step;
${{p}}_stepped = ${{p}}_clock_phase >= 1;
${{p}}_step_fraction = 0;
if (${{p}}_stepped) {{
	${{p}}_clock_phase = ${{p}}_clock_phase - 1;
	${{p}}_step_fraction = ${{p}}_clock_phase / max(${{p}}_step, 1e-9);
	${{p}}_parity = {parity_terms};
	${{p}}_parity = ${{p}}_parity - 2 * floor(${{p}}_parity / 2);
	${{p}}_following = floor(${{p}}_register / 2) + {top} * ${{p}}_parity;
	if (${{p}}_following == 0 || ${{p}}_following == ${{p}}_register) {{
		${{p}}_following = ${{p}}_pattern;
	}}
	${{p}}_register = ${{p}}_following;
}}
${{p}}_naive = 2 * {bit_of(f'{p}_register', 0)} - 1;""") + "\n" + self.edges.statements() \
            + self.substituted("\n${p}_out = ${p}_edges_out;")


METALLIC_NOISE_SOURCES = (LfsrMetallicNoise,)

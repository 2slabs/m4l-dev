"""Seeded white noise (a technique): uniform white noise in (-1, 1) from the Park-Miller "minimal standard" generator,
so a seed gives the same noise every time, in Max and in the kit's renderer (references/dsp.md, "Seeded white noise").

Why not gen~'s noise(): it cannot be seeded, and the kit's rule is that every random thing a device does starts
over from its Seed (architecture/seeded-random.md). This is the audio-rate side of that rule: the brain's seeded
sequence (mulberry32) draws the seed, this block makes the samples.

The generator (Park & Miller, CACM 31(10), 1988, p. 1195): z <- 16807 z mod (2^31 - 1), z in [1, 2^31 - 2], full
period 2^31 - 2. In 64-bit floats every step is exact: 16807 z < 2^46 < 2^53, and the remainder is taken as
z - m floor(z / m), whose floor is exact because z / m sits at least 1/m from the next integer and its rounding error
is far smaller (gen~ computing in 64-bit floats is [UNVERIFIED] here; in 32-bit floats the products would round).
The sample is 2 z / m - 1.

Seeding: `seed` is a number; the state starts at 1 + (floor(|seed|) mod (m - 1)). Two seeds a small step apart give
streams that are shifts of each other (z_n(s + 1) - z_n(s) = 16807^n mod m), so a device passes a seed drawn from its
seeded sequence (`floor(randomNext() * 2147483646)`), not a counter. The generator starts over whenever `seed`
changes and whenever `restart` is true (a device's Loop, or a hit that must sound the same each time).
"""
from twosl_dsp.gen_blocks import Technique

MODULUS = 2147483647.0      # 2^31 - 1, prime (Park & Miller)
MULTIPLIER = 16807.0        # 7^5, a full-period primitive root (Park & Miller)


def park_miller_sequence(seed, count):
    """The Python model: the first `count` samples after seeding."""
    state = 1 + int(abs(seed)) % int(MODULUS - 1)
    samples = []
    for _ in range(count):
        state = (int(MULTIPLIER) * state) % int(MODULUS)
        samples.append(2 * state / MODULUS - 1)
    return samples


class SeededWhiteNoise(Technique):
    """`<name>_out`: the next white noise sample in (-1, 1), uniform. Inputs: `seed` (a number; the generator starts
    over when it changes), `restart` (true: start over at the seed this sample; default never). State: the generator,
    the seed it started from."""

    def __init__(self, instance_name, seed, restart="0"):
        super().__init__(instance_name, seed=seed, restart=restart)
        self.latency_samples = 0       # a source: a restart sounds on its own sample

    def declarations(self):
        return self.substituted("History ${p}_state(0), ${p}_seeded_from(-1);")

    def statements(self):
        return self.substituted("""// ${p}: seeded white noise, Park-Miller minimal standard (kit technique: seeded white noise)
${p}_seed = floor(abs(${seed}));
if (${restart} || ${p}_seed != ${p}_seeded_from || ${p}_state < 1) {
	${p}_state = 1 + (${p}_seed - ${one_less} * floor(${p}_seed / ${one_less}));
	${p}_seeded_from = ${p}_seed;
}
${p}_product = ${multiplier} * ${p}_state;
${p}_state = ${p}_product - ${modulus} * floor(${p}_product / ${modulus});
${p}_out = 2 * ${p}_state / ${modulus} - 1;""", multiplier=MULTIPLIER, modulus=MODULUS, one_less=MODULUS - 1)

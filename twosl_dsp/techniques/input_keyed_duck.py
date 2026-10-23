"""The input-keyed duck (a technique): a gain that dips while a key signal is over a threshold and ramps back when it
falls under, the ducking delay's control (references/dsp.md, "Input-keyed duck"). The TC 2290's ducker is the model:
"the echoes stay out of the way while you're playing, but still allow the echo tails to be audible during gaps",
keyed by the input's level, with a threshold, a depth and a release that is a ramp time.

A technique, not a circuit module: it follows the 2290's controls, not its circuit (no source gives the circuit).
Where the sidechain-style pump draws its dip from the beat, this one listens.

- **The key's level** (`<name>_key_db`): a peak follower on |key|, instant up, falling over DETECTOR_FALL_MS (so a
  low note's cycles don't open and close it), in dB.
- **How far over** (`<name>_amount` target): 0 at the threshold, 1 at KNEE_DB over it, a straight line between (a
  soft knee instead of the 2290's switch, so a level near the threshold doesn't chatter).
- **Ballistics**: the amount rises through a one-pole of ATTACK_MS (fast, never a jump), and falls as a straight ramp
  that takes `release_ms` from all the way down to all the way up (the 2290's Speed: "a ramp time of 1 second").
- gain = 1 - depth x amount, depth 0..1.

Inputs: `key` (the signal that ducks it: the device's input), `threshold_db`, `depth` (0..1), `release_ms`.
Outputs: `<name>_gain` (multiply the ducked signal by it), `<name>_amount` (0..1, before depth: for a display),
`<name>_key_db` (the key's level, for a display beside the threshold).
"""
from twosl_dsp.gen_blocks import Technique

DETECTOR_FALL_MS = 10.0
KNEE_DB = 3.0                         # the 2290's thresholds are 3 dB apart
ATTACK_MS = 2.0
LOWEST_RELEASE_MS = 5.0
SILENCE_DB = -120.0


class InputKeyedDuck(Technique):
    """See the module docstring."""

    def __init__(self, instance_name, *, key, threshold_db, depth, release_ms):
        super().__init__(instance_name, key=key, threshold_db=threshold_db, depth=depth, release_ms=release_ms)
        self.latency_samples = 0       # a gain on the key's own sample (the detector looks at nothing ahead)

    def declarations(self):
        return self.substituted("History ${p}_level(0), ${p}_amount(0);")

    def statements(self):
        return self.substituted("""// ${p}: input-keyed duck (kit technique: input-keyed duck)
${p}_level = max(abs(${key}), ${p}_level * (1 - smoothing_coefficient(${detector_fall_ms}, samplerate)));
${p}_key_db = ${p}_level > 0 ? max(atodb(${p}_level), ${silence_db}) : ${silence_db};
${p}_target = clamp((${p}_key_db - ${threshold_db}) / ${knee_db}, 0, 1);
if (${p}_target > ${p}_amount) {
	${p}_amount = ${p}_amount + (${p}_target - ${p}_amount) * smoothing_coefficient(${attack_ms}, samplerate);
} else {
	${p}_amount = max(${p}_amount - 1000 / (max(${release_ms}, ${lowest_release_ms}) * samplerate), ${p}_target);
}
${p}_gain = 1 - clamp(${depth}, 0, 1) * ${p}_amount;""", detector_fall_ms=DETECTOR_FALL_MS, silence_db=SILENCE_DB,
                                knee_db=KNEE_DB, attack_ms=ATTACK_MS, lowest_release_ms=LOWEST_RELEASE_MS)

"""The sidechain-style pump (a technique): a gain that dips on every division of the beat and swells back, the
sound of a compressor ducked by a kick (references/dsp.md, "Sidechain-style pump").

A technique, not a circuit module: it models no compressor and no sidechain input, it draws the dip from where the
beat is, so it is exactly on the beat, needs no detector and never lags. Two instruments had a copy of this (2sl stab,
2sl filter, each with its own shape); this is the one.

The shape, over a division with phase p in [0, 1) (`pump_duck`, 0 = no dip, 1 = the deepest):

    p < a             duck = sin(pi/2 * p / a)                          a sine ramp in
    a <= p            duck = (1 - clamp((p - a) / (e - a), 0, 1)) ^ (1 + 3 curve)      the recovery

with a = attack_ms / division_ms clamped to [0.001, 0.3] and the recovery's end e = max(release_fraction,
a + 0.05). The ramp in is a quarter sine (never a jump, so no click: it meets the recovery's 1 at a, and the
recovery meets 0 at e, so duck is continuous everywhere); `curve` 0 recovers on a line, 1 with exponent 4
(snappy: back fast, then easing in). gain = 1 - depth * duck; with `chop` (> 0.5) the gate: gain = 1 - depth * (1 -
duck), open on the beat and fading shut.

Where the beat is: `live_beat_position` (beats) while `following_live` > 0.5, the block's own clock (it counts the
division's phase at `bpm`) while not, and a hand-over between the two is a 20 ms crossfade of their ducks, never a
switch (the two clocks are at different places in the beat, and a switch jumped the gain). The position may be Live's
beat ramp wrapped to whole beats as long as `division_beats` divides a beat evenly (1, 1/2, 1/3, 1/4, ...). The gain
follows its target through a one-pole of 0.442 ms (about 1 ms to 90 %), so no step ever reaches the signal,
including a Depth moved by hand.

Outputs: `<name>_gain` (the gain to multiply the signal by) and `<name>_duck` (the shape before depth and the
glide, 0..1, after the hand-over crossfade), which the tests hold to `pump_duck` below and to the display's script.
"""
import math

from twosl_dsp.gen_blocks import Technique

LOWEST_ATTACK_FRACTION = 0.001        # of the division
HIGHEST_ATTACK_FRACTION = 0.3
RELEASE_END_MARGIN = 0.05             # the recovery lasts at least this much of the division after the attack
CURVE_EXPONENT_PER_CURVE = 3.0        # recovery exponent = 1 + 3 curve
HAND_OVER_MS = 20.0                   # the crossfade between Live's beat and the block's own clock
GAIN_GLIDE_MS = 0.442                 # the one-pole on the gain: ~1 ms to 90 %
LOWEST_BPM = 20.0
FUNCTIONS = {
    "sidechain_pump_duck": f"""// the pump's duck (0..1) at phase ph of a division: a quarter sine in over attack_fraction, then a recovery to release_end shaped by curve
sidechain_pump_duck(ph, attack_fraction, release_end, curve) {{
\tduck = 0;
\tif (ph < attack_fraction) {{
\t\tduck = sin(halfpi * ph / attack_fraction);
\t}} else {{
\t\tduck = pow(1 - clamp((ph - attack_fraction) / (release_end - attack_fraction), 0, 1), 1 + curve * {CURVE_EXPONENT_PER_CURVE!r});
\t}}
\treturn duck;
}}""",
}


class SidechainStylePump(Technique):
    """`<name>_gain` and `<name>_duck`: see the module docstring. Inputs: `live_beat_position` (beats),
    `following_live` (> 0.5: follow it, else the own clock), `bpm`, `division_beats`, `depth` (0..1),
    `attack_ms`, `release_fraction` (of the division), `curve` (0..1), `chop` (> 0.5: the gate; default "0")."""

    def __init__(self, instance_name, *, live_beat_position, following_live, bpm, division_beats, depth, attack_ms,
                 release_fraction, curve, chop="0"):
        super().__init__(instance_name, live_beat_position=live_beat_position, following_live=following_live, bpm=bpm,
                         division_beats=division_beats, depth=depth, attack_ms=attack_ms,
                         release_fraction=release_fraction, curve=curve, chop=chop)
        self.latency_samples = 0       # a gain on the beat's own sample

    def functions(self):
        return dict(FUNCTIONS)

    def declarations(self):
        return self.substituted("History ${p}_own_phase(0), ${p}_live_weight(0), ${p}_gain(1);")

    def statements(self):
        return self.substituted("""// ${p}: sidechain-style pump (kit technique: sidechain-style pump)
${p}_tempo = max(${bpm}, ${lowest_bpm});
${p}_division_ms = 60000 / ${p}_tempo * ${division_beats};
${p}_attack_fraction = clamp(${attack_ms} / ${p}_division_ms, ${lowest_attack}, ${highest_attack});
${p}_release_end = max(${release_fraction}, ${p}_attack_fraction + ${release_margin});
${p}_own_phase = wrap(${p}_own_phase + ${p}_tempo / 60 / samplerate / ${division_beats}, 0, 1);
${p}_live_weight = ${p}_live_weight + ((${following_live} > 0.5 ? 1 : 0) - ${p}_live_weight) * smoothing_coefficient(${hand_over_ms}, samplerate);
${p}_duck_on_live_beat = sidechain_pump_duck(wrap(${live_beat_position} / ${division_beats}, 0, 1), ${p}_attack_fraction, ${p}_release_end, ${curve});
${p}_duck_on_own_clock = sidechain_pump_duck(${p}_own_phase, ${p}_attack_fraction, ${p}_release_end, ${curve});
${p}_duck = ${p}_duck_on_own_clock + (${p}_duck_on_live_beat - ${p}_duck_on_own_clock) * ${p}_live_weight;
${p}_target_gain = 1 - ${depth} * (${chop} > 0.5 ? 1 - ${p}_duck : ${p}_duck);
${p}_gain = ${p}_gain + (${p}_target_gain - ${p}_gain) * smoothing_coefficient(${glide_ms}, samplerate);""",
                                lowest_bpm=LOWEST_BPM, lowest_attack=LOWEST_ATTACK_FRACTION,
                                highest_attack=HIGHEST_ATTACK_FRACTION, release_margin=RELEASE_END_MARGIN,
                                hand_over_ms=HAND_OVER_MS, glide_ms=GAIN_GLIDE_MS)


def pump_duck(phase, attack_ms, division_ms, release_fraction, curve):
    """The duck (0..1) at `phase` of a division `division_ms` long: Python's copy of the technique's shape and of
    templates/sidechain-pump-duck.template.js, which the tests hold equal to it and to the rendered technique."""
    attack_fraction = min(max(attack_ms / division_ms, LOWEST_ATTACK_FRACTION), HIGHEST_ATTACK_FRACTION)
    release_end = max(release_fraction, attack_fraction + RELEASE_END_MARGIN)
    if phase < attack_fraction:
        return math.sin(math.pi / 2 * phase / attack_fraction)
    recovery_left = 1 - min(max((phase - attack_fraction) / (release_end - attack_fraction), 0.0), 1.0)
    return recovery_left ** (1 + curve * CURVE_EXPONENT_PER_CURVE)


def response_script_code():
    """The ES5 `sidechainPumpDuck(phase, attackMs, divisionMs, releaseFraction, curve)` for a device's displays, with
    the technique's constants filled in (templates/sidechain-pump-duck.template.js)."""
    from twosl_dsp.generated_scripts import fill_template, kit_template_text
    return fill_template(kit_template_text("sidechain-pump-duck.template.js"), {
        "SIDECHAIN_PUMP_LOWEST_ATTACK_FRACTION": repr(LOWEST_ATTACK_FRACTION),
        "SIDECHAIN_PUMP_HIGHEST_ATTACK_FRACTION": repr(HIGHEST_ATTACK_FRACTION),
        "SIDECHAIN_PUMP_RELEASE_END_MARGIN": repr(RELEASE_END_MARGIN),
        "SIDECHAIN_PUMP_CURVE_EXPONENT_PER_CURVE": repr(CURVE_EXPONENT_PER_CURVE)}, "sidechain-pump-duck.template.js")

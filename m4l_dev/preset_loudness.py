"""Every preset played the same way, and how loud it comes out: what a device's tests level its presets by.

A device's presets are levelled to its Init sound: each preset's output level (its own control) set so the preset's
loudest moment on the phrase below is as loud as Init's: the maximum momentary loudness (EBU Tech 3341's 400 ms
sliding window over ITU-R BS.1770-5's K-weighted loudness, m4l_dev/bs1770.py), not the phrase's average, so a ping
is not paid back for being short; its peaks under the device's clip. The kit holds the phrase, the meter, the
comparison, where a voice's oscillators are when a note reaches it, and how a preset's controls reach the device's
DSP: through the device's own patch (DevicePatchBuilder.messages_for, the routes its build wired), never a copy of
them. The device's tests hold what only the device knows: how a note reaches its DSP (they stand in for its brain)
and its render.

The phrase, at 120 BPM, velocity 100:
- mono: C2 G2 C3 Eb3 G3 C4, a 16th note each (0.125 s), each key up after 0.1 s;
- chords: three chords a dotted 8th apart (0.375 s), roots C3, Ab2, Bb2, each key up after 0.3 s; a stored shape
  (m7, m9) at its own intervals (the kit's chord block), "held notes" played as an m7;
then the tail, PHRASE_SECONDS in all. Short, because a suite renders it for every preset.
"""
import random

from m4l_dev import bs1770
from m4l_dev.build_error import BuildError
from m4l_dev.chord_block import CHORD_SHAPES

BEATS_PER_MINUTE = 120
PLAYED_VELOCITY = 100
PHRASE_SECONDS = 1.25
MONO_NOTES = [(0.0, 36), (0.125, 43), (0.25, 48), (0.375, 51), (0.5, 55), (0.625, 60)]     # (seconds, MIDI pitch)
MONO_KEY_DOWN_SECONDS = 0.1
CHORD_ROOTS = [(0.0, 48), (0.375, 44), (0.75, 46)]                                          # C3, Ab2, Bb2
CHORD_KEY_DOWN_SECONDS = 0.3
HELD_NOTES_PLAYED_AS = "m7"
CHORD_SEMITONES = {name: [semitones for _, semitones, _ in tones] for name, tones in CHORD_SHAPES}
SAMPLE_RATE = 44100                 # the rate presets are levelled at
# A suite's render rate: a quarter of the cost. BS.1770's K-weighting there is within 0.3 dB of the standard's below
# 0.4 x the rate (tests/test_bs1770.py); 2sl gate's presets read within 0.3 LU of SAMPLE_RATE's (2026-10-19).
FAST_SAMPLE_RATE = 11025
LOUDNESS_TOLERANCE_LU = 1.0         # a preset this far from Init, at FAST_SAMPLE_RATE, fails a device's suite
# A sample peak at FAST_SAMPLE_RATE reads up to ~0.3 dB off SAMPLE_RATE's (2sl stab, 2026-10-19): a preset set under
# its device's clip at SAMPLE_RATE may read this far over it in a suite.
FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB = 0.3
# Where a voice's oscillators are when a note reaches it. In Live a device's voices run on between notes at their last
# note's pitch, so a chord's notes land on unrelated phases; a voice the harness creates at its first note would start
# every oscillator at 0 together, lining up the attacks and fixing the beating of detuned oscillators. So a device's
# player starts each oscillator at the next of these phases: unrelated, and the same on every run.
OSCILLATOR_PHASE_SEED = 1770


def mono_phrase():
    """[(seconds, [pitch] or None for the key up)], in time order."""
    return _events([(seconds, [pitch]) for seconds, pitch in MONO_NOTES], MONO_KEY_DOWN_SECONDS)


def chord_phrase(chord_shape_name, most_notes_per_chord):
    """[(seconds, [pitches] or None for the keys up)], in time order: `chord_shape_name` (a chord block shape, or
    "held notes") on each root. Fails on a shape with more notes than the device plays (its brain would drop
    degrees, which the phrase does not)."""
    shape = HELD_NOTES_PLAYED_AS if chord_shape_name == "held notes" else chord_shape_name
    if shape not in CHORD_SEMITONES:
        raise BuildError(f"preset_loudness: no chord shape {chord_shape_name!r}")
    if len(CHORD_SEMITONES[shape]) > most_notes_per_chord:
        raise BuildError(f"preset_loudness: {shape} has {len(CHORD_SEMITONES[shape])} notes, the device plays "
                         f"{most_notes_per_chord}: play the brain's dropped degrees (the chord block's DROPPED_FIRST) "
                         "before measuring it")
    return _events([(seconds, [root + semitones for semitones in CHORD_SEMITONES[shape]])
                    for seconds, root in CHORD_ROOTS], CHORD_KEY_DOWN_SECONDS)


def _events(notes, key_down_seconds):
    events = []
    for seconds, pitches in notes:
        events += [(seconds, pitches), (seconds + key_down_seconds, None)]
    return sorted(events, key=lambda event: event[0])


def preset_values_as_held(patch, preset_name):
    """`preset_name`'s every saved control, as `patch` (a built DevicePatchBuilder) holds it: what messages_for
    reads."""
    for preset in patch.preset_book.presets_as_held(patch.saved_controls):
        if preset.name == preset_name:
            return preset.values
    raise BuildError(f"preset_loudness: no preset named {preset_name!r} in {patch.preset_book.source_name}")


def messages_by_preset(patch, destinations, beats_per_minute=BEATS_PER_MINUTE):
    """{preset name: {destination name: {message: value}}}: what each of `destinations` ({name: box}) gets from
    every preset's controls through the patch's own routes."""
    return {preset.name: {name: patch.messages_for(preset.values, box, beats_per_minute)
                          for name, box in destinations.items()}
            for preset in patch.preset_book.presets_as_held(patch.saved_controls)}


def phrase_measures(channels, rate):
    """(loudness LUFS, sample peak dBFS) of a preset's render (`channels`: L and R lists at `rate`): its loudest
    moment (bs1770.max_momentary_loudness), what presets are levelled by, and its peak, what must stay under the
    device's clip."""
    return bs1770.max_momentary_loudness(channels, rate), bs1770.sample_peak_db(channels)


def oscillator_start_phases():
    """An endless source of oscillator phases (0..1), unrelated to each other, seeded (OSCILLATOR_PHASE_SEED): call
    next() on it for each oscillator a player sets up, in a fixed order."""
    draws = random.Random(OSCILLATOR_PHASE_SEED)
    while True:
        yield draws.random()


def presets_over_the_clip(peak_by_preset, clip_knee_db, rate):
    """{preset: sample peak dBFS (2 decimals)} of every preset whose peak, rendered at `rate`, is over the device's
    clip knee (FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB over it at FAST_SAMPLE_RATE): empty when every preset is clean."""
    allowance = FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB if rate == FAST_SAMPLE_RATE else 0.0
    return {name: round(peak, 2) for name, peak in peak_by_preset.items() if peak > clip_knee_db + allowance}


def presets_off_init(loudness_by_preset, init_name, tolerance_lu=LOUDNESS_TOLERANCE_LU):
    """{preset: LU against Init (2 decimals)} of every preset further than `tolerance_lu` from `init_name`'s
    loudness: empty when every preset is levelled."""
    init = loudness_by_preset[init_name]
    return {name: round(loudness - init, 2) for name, loudness in loudness_by_preset.items()
            if abs(loudness - init) > tolerance_lu}

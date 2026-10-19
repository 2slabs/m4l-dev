"""Every preset played the same way, and how loud it comes out: what a device's tests level its presets by.

A device's presets are levelled to its Init sound: each preset's output level (its own control) set so the preset
plays the phrase below at Init's loudness (ITU-R BS.1770-5 integrated loudness, m4l_dev/bs1770.py). The kit holds
the phrase, the meter, the comparison, and how a preset's controls reach the device's DSP: through the device's own
patch (DevicePatchBuilder.messages_for, the routes its build wired), never a copy of them. The device's tests hold
what only the device knows: how a note reaches its DSP (they stand in for its brain) and its render.

The phrase, at 120 BPM, velocity 100:
- mono: C2 G2 C3 Eb3 G3 C4, a 16th note each (0.125 s), each key up after 0.1 s;
- chords: three chords a dotted 8th apart (0.375 s), roots C3, Ab2, Bb2, each key up after 0.3 s; a stored shape
  (m7, m9) at its own intervals (the kit's chord block), "held notes" played as an m7;
then the tail, PHRASE_SECONDS in all. Short, because a suite renders it for every preset.
"""
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
LOUDNESS_TOLERANCE_LU = 1.5         # a preset this far from Init, at FAST_SAMPLE_RATE, fails a device's suite


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


def presets_off_init(loudness_by_preset, init_name, tolerance_lu=LOUDNESS_TOLERANCE_LU):
    """{preset: LU against Init (2 decimals)} of every preset further than `tolerance_lu` from `init_name`'s
    loudness: empty when every preset is levelled."""
    init = loudness_by_preset[init_name]
    return {name: round(loudness - init, 2) for name, loudness in loudness_by_preset.items()
            if abs(loudness - init) > tolerance_lu}

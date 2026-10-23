"""Every preset played the same way, and how loud it comes out: what a device's tests level its presets by.

A device's presets are levelled to its Init sound: each preset's output level (its own control) set so the preset's
loudest moment on the phrase below is as loud as Init's: the maximum momentary loudness (EBU Tech 3341's 400 ms
sliding window over ITU-R BS.1770-5's K-weighted loudness, twosl_dsp/bs1770.py), not the phrase's average, so a ping
is not paid back for being short; its peaks under the device's output ceiling (full scale, or its own limiter's). The kit holds the phrase, the meter, the
comparison, where a voice's oscillators are when a note reaches it, and how a preset's controls reach the device's
DSP: through the device's own patch (DevicePatchBuilder.messages_for, the routes its build wired), never a copy of
them. The device's tests hold what only the device knows: how a note reaches its DSP (they stand in for its brain)
and its render.

The phrase, at 120 BPM, velocity 100:
- mono: C2 G2 C3 Eb3 G3 C4, a 16th note each (0.125 s), each key up after 0.1 s;
- chords: three chords a dotted 8th apart (0.375 s), roots C3, Ab2, Bb2, each key up after 0.3 s; a stored shape
  (m7, m9) at its own intervals (the kit's chord block), "held notes" played as an m7;
then the tail, PHRASE_SECONDS in all. Short, because a suite renders it for every preset.

An audio effect is levelled to bypass instead (architecture/presets.md, "An audio effect: as loud as bypass"): its
loudness change on music. The kit generates the music (effect_inputs: drums, bass, pad, a full mix, chords and a
kick; EFFECT_INPUT_SECONDS each (or the `seconds` and `names` a test asks for) at EFFECT_INPUT_LOUDNESS_LUFS, from seeds, no samples, at EFFECT_SAMPLE_RATE), plays
every preset on all of it in worker processes (effect_measures_by_preset, with the device's own render), and reads each preset's gain on
each input (the loudest moment out minus the loudest moment in), their median (what the preset's output level sets
to 0 dB) and the worst miss from that median (information: an effect whose gain depends on its input, a
self-oscillating filter, triggers, can't match bypass on everything). An effect's peaks are judged against bypass's
on the same input, not a fixed ceiling (effect_presets_clipping_beyond_dry): it may raise the crest factor, as its
circuit does; it fails when its level drives the output over its ceiling.
"""
import concurrent.futures
import functools
import math
import os
import random
import statistics
import sys

from twosl_dsp import bs1770
from twosl_dsp.build_error import BuildError
from twosl_dsp.chord_block import CHORD_SHAPES

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
# its device's ceiling at SAMPLE_RATE may read this far over it in a suite.
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
    device's output ceiling."""
    return bs1770.max_momentary_loudness(channels, rate), bs1770.sample_peak_db(channels)


def oscillator_start_phases():
    """An endless source of oscillator phases (0..1), unrelated to each other, seeded (OSCILLATOR_PHASE_SEED): call
    next() on it for each oscillator a player sets up, in a fixed order."""
    draws = random.Random(OSCILLATOR_PHASE_SEED)
    while True:
        yield draws.random()


def presets_over_the_clip(peak_by_preset, ceiling_db, rate):
    """{preset: sample peak dBFS (2 decimals)} of every preset whose peak, rendered at `rate`, is over the device's
    output ceiling `ceiling_db` (FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB over it at FAST_SAMPLE_RATE): empty when every preset is clean."""
    allowance = FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB if rate == FAST_SAMPLE_RATE else 0.0
    return {name: round(peak, 2) for name, peak in peak_by_preset.items() if peak > ceiling_db + allowance}


def presets_off_init(loudness_by_preset, init_name, tolerance_lu=LOUDNESS_TOLERANCE_LU):
    """{preset: LU against Init (2 decimals)} of every preset further than `tolerance_lu` from `init_name`'s
    loudness: empty when every preset is levelled."""
    init = loudness_by_preset[init_name]
    return {name: round(loudness - init, 2) for name, loudness in loudness_by_preset.items()
            if abs(loudness - init) > tolerance_lu}


# ---- an audio effect: levelled to bypass on generated music ----

# The rate presets are levelled at, not a fast one: an effect's peaks depend on the input's top octave (a saw bass
# through a high-pass peaked 1.1 dB higher at 44.1 kHz than at 22.05 kHz, 2sl filter, 2026-10-19).
EFFECT_SAMPLE_RATE = SAMPLE_RATE
EFFECT_INPUT_SECONDS = 8.0                 # four bars at 120 BPM
EFFECT_INPUT_LOUDNESS_LUFS = -18.0         # integrated, the pair (the input on both channels)
EFFECT_FULL_MIX_PART_LUFS = -20.0          # drums, bass and pad each at this before they are summed
EFFECT_LOUDNESS_TOLERANCE_LU = 1.5         # a preset's median gain further from 0 dB fails a device's suite
EFFECT_INPUT_NAMES = ("drums", "bass", "pad", "full mix", "chords and kick")
EFFECT_INPUT_SEED = 3341
KICK_SECONDS = 0.25
KICK_AMPLITUDE = 0.5


def _polyblep_saw(frequency, samples, rate, start_phase, amplitude):
    """A saw (-amplitude..amplitude, falling edge at the phase's wrap) with polyBLEP's two-sample correction at each
    wrap: band-limited enough for a level measure, and one step a sample."""
    out = [0.0] * samples
    increment = frequency / rate
    phase = start_phase % 1.0
    for i in range(samples):
        value = 2 * phase - 1
        if phase < increment:
            t = phase / increment
            value -= t + t - t * t - 1
        elif phase > 1 - increment:
            t = (phase - 1) / increment
            value -= t * t + t + t + 1
        out[i] = amplitude * value
        phase += increment
        if phase >= 1:
            phase -= 1
    return out


def _add_at(destination, source, start):
    for i, value in enumerate(source[:max(0, len(destination) - start)]):
        destination[start + i] += value


def _kick(rate):
    """A sine kick: 120 Hz falling to 45 Hz (30 ms), decaying over 120 ms, KICK_SECONDS long."""
    out, phase = [], 0.0
    for i in range(int(KICK_SECONDS * rate)):
        age = i / rate
        phase += 2 * math.pi * (45 + 75 * math.exp(-age / 0.03)) / rate
        out.append(KICK_AMPLITUDE * math.exp(-age / 0.12) * math.sin(phase))
    return out


def _noise_burst(rate, seconds, decay_seconds, amplitude, draws, high_pass_hz, tone_hz=None):
    """White noise through a one-pole high-pass, decaying; with tone_hz, a snare: noise and a short sine body."""
    out, previous_input, high_passed = [], 0.0, 0.0
    pole = math.exp(-2 * math.pi * high_pass_hz / rate)
    for i in range(int(seconds * rate)):
        white = draws.uniform(-1, 1)
        high_passed = pole * (high_passed + white - previous_input)
        previous_input = white
        value = high_passed
        if tone_hz:
            value = 0.6 * high_passed + 0.6 * math.sin(2 * math.pi * tone_hz * i / rate) * math.exp(-(i / rate) / 0.05)
        out.append(amplitude * math.exp(-(i / rate) / decay_seconds) * value)
    return out


def _beat_seconds():
    return 60.0 / BEATS_PER_MINUTE


def _drums(rate, draws, input_seconds):
    """A kick on every beat, a snare on 2 and 4, closed hats on the 16ths with an open hat on the off-beat."""
    out = [0.0] * int(input_seconds * rate)
    beat = _beat_seconds()
    kick = _kick(rate)
    for number in range(int(input_seconds / beat)):
        _add_at(out, kick, int(number * beat * rate))
        if number % 2 == 1:
            _add_at(out, _noise_burst(rate, 0.2, 0.06, 0.35, draws, 800, tone_hz=190), int(number * beat * rate))
        for sixteenth in range(4):
            start = int((number * beat + sixteenth * beat / 4) * rate)
            if sixteenth == 2:
                _add_at(out, _noise_burst(rate, 0.25, 0.08, 0.12, draws, 7000), start)
            else:
                _add_at(out, _noise_burst(rate, 0.05, 0.012, 0.09 if sixteenth == 0 else 0.06, draws, 7000), start)
    return out


def _bass(rate, draws, input_seconds):
    """A 16th-note saw bassline on C1..Bb1, plucked (150 ms decay), the bar repeated."""
    out = [0.0] * int(input_seconds * rate)
    pattern = [24, None, 24, 36, None, 24, 27, None, 24, None, 31, 24, None, 34, 24, None]
    step = _beat_seconds() / 4
    length = int(step * 0.9 * rate)
    for bar in range(int(input_seconds / (16 * step))):
        for index, pitch in enumerate(pattern):
            if pitch is None:
                continue
            note = _polyblep_saw(440.0 * 2 ** ((pitch - 69) / 12), length, rate, draws.random(), 0.4)
            for i in range(length):
                age = i / rate
                note[i] *= math.exp(-age / 0.15) * min(1, age / 0.002) * min(1, (step * 0.9 - age) / 0.005)
            _add_at(out, note, int((bar * 16 + index) * step * rate))
    return out


def _pad(rate, draws, input_seconds):
    """Detuned saw chords (Cm7, Abmaj7, Bb7, Gm7), a bar each, a slow attack and release, softened above 2.5 kHz."""
    out = [0.0] * int(input_seconds * rate)
    chords = [[48, 51, 55, 58], [44, 48, 51, 55], [46, 50, 53, 56], [43, 46, 50, 53]]
    seconds_each = input_seconds / len(chords)
    length = int(seconds_each * rate)
    for number, pitches in enumerate(chords):
        for pitch in pitches:
            for detune in (-0.07, 0.07):
                voice = _polyblep_saw(440.0 * 2 ** ((pitch - 69 + detune) / 12), length, rate, draws.random(), 0.05)
                for i in range(length):
                    age = i / rate
                    voice[i] *= min(1, age / 0.15) * min(1, (seconds_each - age) / 0.3)
                _add_at(out, voice, number * length)
    pole = math.exp(-2 * math.pi * 2500 / rate)
    smoothed = 0.0
    for i, value in enumerate(out):
        smoothed = (1 - pole) * value + pole * smoothed
        out[i] = smoothed
    return out


def _chords_and_kick(rate, input_seconds):
    """The kit's chord phrase (m7 on C3, Ab2, Bb2) as saws at the seeded start phases, every bar, a kick every beat."""
    out = [0.0] * int(input_seconds * rate)
    bar = 4 * _beat_seconds()
    start_phases = oscillator_start_phases()
    events = chord_phrase("m7", 4)
    for bar_number in range(int(input_seconds / bar)):
        for (seconds, pitches), (end_seconds, _) in zip(events[0::2], events[1::2]):
            length = int(round((end_seconds - seconds) * rate))
            for pitch in pitches:
                note = _polyblep_saw(440.0 * 2 ** ((pitch - 69) / 12), length, rate, next(start_phases), 0.08)
                _add_at(out, note, int(round((bar_number * bar + seconds) * rate)))
    kick = _kick(rate)
    for number in range(int(input_seconds / _beat_seconds())):
        _add_at(out, kick, int(number * _beat_seconds() * rate))
    return out


def _at_loudness(signal, rate, loudness_lufs):
    gain = 10 ** ((loudness_lufs - bs1770.integrated_loudness([signal, signal], rate)) / 20)
    return [value * gain for value in signal]


@functools.lru_cache(maxsize=8)
def effect_inputs(rate=EFFECT_SAMPLE_RATE, seconds=EFFECT_INPUT_SECONDS, names=EFFECT_INPUT_NAMES):
    """{name: mono samples (a tuple)}, `names` in order (any of EFFECT_INPUT_NAMES; the default is all of them), each
    `seconds` long at EFFECT_INPUT_LOUDNESS_LUFS integrated (the input on both channels, as the effect gets it): the
    same on every run. A device's test asks for fewer names and a shorter `seconds` to be quick; the full default set
    is what the levelling tool and the presets' tolerance use. Drums, bass and pad are always drawn in one order from
    one seed, so an input is the same whichever names are asked for. `names` must be a tuple (the result is cached)."""
    unknown_names = [name for name in names if name not in EFFECT_INPUT_NAMES]
    if unknown_names or not names:
        raise BuildError(f"preset_loudness: effect input names {list(names)} must be a non-empty choice from "
                         f"{list(EFFECT_INPUT_NAMES)} (unknown: {unknown_names})")
    if not seconds > 0:
        raise BuildError(f"preset_loudness: effect inputs must be longer than 0 seconds, got {seconds}")
    draws = random.Random(EFFECT_INPUT_SEED)
    drums, bass, pad = _drums(rate, draws, seconds), _bass(rate, draws, seconds), _pad(rate, draws, seconds)
    parts = [_at_loudness(part, rate, EFFECT_FULL_MIX_PART_LUFS) for part in (drums, bass, pad)]
    unlevelled = {"drums": drums, "bass": bass, "pad": pad, "full mix": [sum(values) for values in zip(*parts)],
                  "chords and kick": _chords_and_kick(rate, seconds)}
    return {name: tuple(_at_loudness(unlevelled[name], rate, EFFECT_INPUT_LOUDNESS_LUFS)) for name in names}


@functools.lru_cache(maxsize=8)
def _effect_input_measures(rate, seconds, names):
    """{name: (the effect input's max momentary loudness, its sample peak dBFS)}, the input on both channels: what
    bypass gives."""
    return {name: phrase_measures([list(mono), list(mono)], rate)
            for name, mono in effect_inputs(rate, seconds, names).items()}


class EffectMeasures:
    """A preset's measures on the effect inputs, each by input name: gain_db_by_input (the loudest moment out minus
    in, LU), peak_db_by_input (the render's sample peak, dBFS) and dry_peak_db_by_input (the input's own, bypass's);
    median_gain_db, worst_miss_db (the largest distance of an input's gain from the median) and peak_db (the highest
    of the render's peaks)."""

    def __init__(self, gain_db_by_input, peak_db_by_input, dry_peak_db_by_input):
        self.gain_db_by_input = dict(gain_db_by_input)
        self.peak_db_by_input = dict(peak_db_by_input)
        self.dry_peak_db_by_input = dict(dry_peak_db_by_input)
        if not set(self.gain_db_by_input) == set(self.peak_db_by_input) == set(self.dry_peak_db_by_input):
            raise BuildError("preset_loudness: an effect's gains, peaks and dry peaks must name the same inputs")
        self.median_gain_db = statistics.median(self.gain_db_by_input.values())
        self.worst_miss_db = max(abs(gain - self.median_gain_db) for gain in self.gain_db_by_input.values())
        self.peak_db = max(self.peak_db_by_input.values())

    def __repr__(self):
        return (f"EffectMeasures(median {self.median_gain_db:+.2f} LU, worst miss {self.worst_miss_db:.2f} LU, "
                f"peak {self.peak_db:+.2f} dBFS)")


def effect_measures(render, messages, rate=EFFECT_SAMPLE_RATE, seconds=EFFECT_INPUT_SECONDS, names=EFFECT_INPUT_NAMES):
    """EffectMeasures of one preset: render(messages, mono input, rate) -> (left, right) plays the preset (its
    messages, as the device's DSP gets them) on each effect input (`seconds` and `names` as in `effect_inputs`)."""
    gains, peaks = {}, {}
    dry = _effect_input_measures(rate, seconds, names)
    for name, mono in effect_inputs(rate, seconds, names).items():
        channels = [list(channel) for channel in render(messages, list(mono), rate)]
        if len(channels) != 2 or any(len(channel) != len(mono) for channel in channels):
            raise BuildError(f"preset_loudness: the render of {name!r} isn't two channels of {len(mono)} samples")
        gains[name] = bs1770.max_momentary_loudness(channels, rate) - dry[name][0]
        peaks[name] = bs1770.sample_peak_db(channels)
    return EffectMeasures(gains, peaks, {name: peak for name, (_, peak) in dry.items()})


def _worker_starts(search_path):
    sys.path[:] = search_path


def _measures_of_one(render, rate, seconds, names, name_and_messages):
    name, messages = name_and_messages
    return name, effect_measures(render, messages, rate, seconds, names)


def effect_measures_by_preset(render, messages_by_preset, rate=EFFECT_SAMPLE_RATE, seconds=EFFECT_INPUT_SECONDS,
                              names=EFFECT_INPUT_NAMES):
    """{preset: EffectMeasures} of every preset ({name: messages}), in worker processes, one per CPU. `render` is a
    module-level function (it is sent to the workers by name, and they get this process's sys.path).
    `seconds` and `names` as in `effect_inputs`."""
    _effect_input_measures(rate, seconds, names)    # made once here: workers forked from this process inherit them
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count(), initializer=_worker_starts,
                                                initargs=(list(sys.path),)) as pool:
        return dict(pool.map(functools.partial(_measures_of_one, render, rate, seconds, names), messages_by_preset.items()))


def presets_off_bypass(measures_by_preset, tolerance_lu=EFFECT_LOUDNESS_TOLERANCE_LU):
    """{preset: median gain LU (2 decimals)} of every preset whose median gain is further than `tolerance_lu` from
    0 dB (bypass): empty when every preset is levelled."""
    return {name: round(measures.median_gain_db, 2) for name, measures in measures_by_preset.items()
            if abs(measures.median_gain_db) > tolerance_lu}


def effect_presets_clipping_beyond_dry(measures_by_preset, ceiling_db, rate=EFFECT_SAMPLE_RATE):
    """{preset: {input: (its peak, the dry's peak at its level), dBFS, 2 decimals}} of every effect preset whose level
    drives the device's output over its ceiling (architecture/presets.md, "Peaks against bypass's"): on an input,
    the preset's peak is over `ceiling_db` and so is the dry input's own peak moved by the preset's level (its
    median gain). A preset over the knee only by what it does to that input (the crest factor it adds, its gain there
    away from its median: the effect) passes. FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB is allowed on both at
    FAST_SAMPLE_RATE. Empty when every preset passes."""
    ceiling = ceiling_db + (FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB if rate == FAST_SAMPLE_RATE else 0.0)
    failing = {}
    for name, measures in measures_by_preset.items():
        dry_at_level = {input_name: dry_peak + measures.median_gain_db
                        for input_name, dry_peak in measures.dry_peak_db_by_input.items()}
        inputs = {input_name: (round(peak, 2), round(dry_at_level[input_name], 2))
                  for input_name, peak in measures.peak_db_by_input.items()
                  if peak > ceiling and dry_at_level[input_name] > ceiling}
        if inputs:
            failing[name] = inputs
    return failing

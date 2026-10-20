# Presets: one preset book, two outputs

A device keeps its Init values and its presets in one JSON file, its preset book (`m4l_dev/preset_book.py`):

```json
{"init": {"Cutoff": 700, "Chord": "minor", "In Key": "on", "Volume": 0},
 "presets": [{"name": "init", "group": "init", "idea": "the defaults", "values": {}},
             {"name": "chain stab", "group": "dub", "idea": "what it is for", "values": {"Cutoff": 650}}]}
```

Values are in each control's own units: a dial's or number box's number, a menu's or tab's item name, a toggle's
`off` / `on`. Every control the presets set has an Init value (it is the control's initial value in the patch, the
default of each gen~ Param it sets, and the displays' starting value); a control given `initial_outside_presets` has
none and presets leave it alone. The build fails on an unknown control, a missing Init value, a value out of range or
not an item, and a preset name used twice.

**The Init values are the gen~ Params' defaults: one source.** A Param a control sets leaves its default out of the
device's GenExpr (`Param cutoff(min=40, max=12000);`); the patch builder writes it into the code the patch holds, the
value the initial values send that Param (scaled, looked up, or a tempo-synced time at 120 BPM, as the route sends
it: `DevicePatchBuilder.write_gen_param_defaults`, `genexpr.code_with_param_defaults`). A Param no control sets (Stop's
panic, Live's tempo from the brain) keeps the default its code writes. The build fails, listing each, on a Param with a
default in its code that a control also sets (two sources), a Param with neither, two controls starting one Param at
different values, and a value outside the Param's min / max. Whatever renders or exports the code as given sets those
Params first: `GenProgram.run` refuses while one is unset, `genexpr_export.export_c` refuses code without its defaults
(export `DevicePatchBuilder.gen_code_as_built`), and a MatchedVoice must search or fix each.

The same book makes either or both outputs:

- **Live preset files** (`.adv`, `m4l_dev/live_preset_files.py`), when the device passes `LivePresetFiles(...)` to
  `build_device`: one file per preset next to the development device and next to the frozen release, named
  `<group> - <name>.adv` (`<name>.adv` for the group `init`), each made for that exact device file (its name, size and
  CRC). Stored Only parameters go in the preset's blob: the device's `stored_only_values_of_preset(values)` gives them
  (2sl stab: the Pattern's steps). Known forms only (float and enum parameters, a Max Instrument or a Max Audio Effect): an Int parameter or
  another device type fails the build until a file Live wrote shows its form.
- **A Preset menu** (`header(..., preset_menu=(x, width))`): a live.menu in the header listing the presets; the UI
  script sets every saved control from the chosen preset (ignored until the device is ready, so a set's saved
  values win when Live reopens it).

A preset book with presets and neither output is legal: the presets are then only checked. Stale `.adv` files (no
preset of that name) are removed from devices/ with a line in the build's log.

## Every preset about as loud as Init

A device's presets are levelled to its Init sound: each preset's output level (the header's level control, a preset
value like any other) is set so the preset's loudest moment on one phrase is as loud as Init's: the maximum momentary
loudness, EBU Tech 3341's 400 ms sliding window over ITU-R BS.1770-5's K-weighted loudness (`m4l_dev/preset_loudness.py`
`phrase_measures`, `m4l_dev/bs1770.py`, references/itu-r-bs1770.md, references/ebu-tech-3341.md), its peaks under the
device's clip (`presets_over_the_clip`). The loudest moment, not the phrase's average: a ping and a pad at the same
level hit as hard, where the integrated loudness would pay the pad for lasting. A device's suite holds every preset
within `LOUDNESS_TOLERANCE_LU` of Init and every peak under its clip.

The pattern: the kit holds the phrase, the meter, the comparison, where a voice's oscillators start
(`oscillator_start_phases`: unrelated phases, seeded, as Live's voices are after running on between notes; a player
sets them through `GenProgram.set_history`), and each preset's controls as the device's DSP gets
them, read through the device's own built patch (`messages_by_preset` / `messages_for`: the routes its build wired;
a time synced to Live's tempo at the phrase's 120 BPM). So a device builds its patch in memory (a function its build
calls before writing) and never keeps a second map of its controls. The device's tests hold the rest: how a note
reaches its DSP (standing in for its brain) and its render.

## An audio effect: as loud as bypass

An audio effect has no Init sound of its own to level to: its output is its input plus what it does. So each preset's
output level is set so that its **median gain** is 0 dB: switching the device off and on is level-matched. The gain
on one input is the loudest moment out minus the loudest moment in (the same max momentary loudness, Mix as the
preset has it); the median is over the kit's effect inputs (`effect_inputs`): drums, bass, a pad, a full mix of the
three, and the chord phrase as saws every bar with a kick on every beat, EFFECT_INPUT_SECONDS (four bars at 120 BPM,
Live stopped) each at −18 LUFS integrated, generated from seeds (no samples), at EFFECT_SAMPLE_RATE (44.1 kHz: an
effect's peaks depend on the input's top octave, so no fast rate). `effect_inputs` and `effect_measures_by_preset` take `seconds` and `names` (defaults: all five, EFFECT_INPUT_SECONDS) so a device's quick test asks for fewer, shorter inputs. A device's suite
holds every preset's median within `EFFECT_LOUDNESS_TOLERANCE_LU` (±1.5) of 0 dB (`presets_off_bypass`) and every
preset to the peak rule below. Each preset's **worst miss** (its largest distance from the median over the inputs) is
reported, not tested: an effect whose gain depends on the input by nature (a self-oscillating filter, triggers, a
gate) can't match bypass on everything, and its level is a compromise.

**A circuit whose own level is not bypass's.** Some effects lose or add level as the circuit does, on every setting:
a phaser's passive dry / wet sum notches the music and its coupling capacitors cut the wet's bass (2sl phaser: the
Mu-Tron Bi-Phase loses 2-3 dB on the effect inputs with the phasors in, at moderate feedback, references/circuits/mutron-bi-phase.md §8).
Making that up with each preset's output level is gain the circuit doesn't have. Such a device says so in its
architecture, never raises a preset's output level, reports each preset's median against bypass as the circuit's,
and its suite holds the presets about as loud as each other instead: every median within
`EFFECT_LOUDNESS_TOLERANCE_LU` of Init's (`presets_off_init` over the medians). The output level stays at 0 dB but
where the circuit makes a preset louder than that (full feedback's resonance): there it is turned down, to Init's
level, and the cut is reported.

### Peaks against bypass's

An effect's peaks are judged against the dry input's, not against a fixed ceiling (`effect_presets_clipping_beyond_dry`,
`EffectMeasures.peak_db_by_input` and `dry_peak_db_by_input`). An effect may raise the crest factor, as its circuit does
(a phaser's resonant peaks, a square sweep throwing the notches across a drum hit): that is the sound, and the kit's
inputs already sit near the clip (the drums peak at −1.4 dBFS at −18 LUFS), so a fixed ceiling punished the input's
crest as much as the effect's. What the rule catches is a preset whose **level** drives the device's output stage into
its clip: on some input, the preset's sample peak is over the clip's knee **and** the dry input's own peak, moved by the
preset's level (its median gain against bypass), is over it as well: the dry at the preset's level would clip there
too. What the preset does to one input (its crest factor, its gain there away from its median: a resonance on the
kick) is the effect, and passes. Precisely, a preset fails on input i when

    peak_i > knee_db  and  dry_peak_i + median_gain > knee_db

(`FAST_SAMPLE_RATE_PEAK_ALLOWANCE_DB` added to the knee at FAST_SAMPLE_RATE). A preset under the knee always passes, so
every preset the old ceiling passed passes this. Each preset's peak against bypass's (peak_i − dry_peak_i) is reported
by the device's player, not tested. No limiter is added to make a preset pass: a preset that fails is too loud.

The device gives a module-level render (its preset's messages and a mono input, played on both channels, to its
left and right); `effect_measures_by_preset` plays every preset on every input in worker processes, one per CPU.

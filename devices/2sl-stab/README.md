# 2sl stab

A dub techno chord machine: chord memory, a polyphonic analog-style voice, a stab pattern machine, and dub performance moves (throw, freeze, a dub macro, pump). It plays chord progressions' clips as they are (**poly**), or stacks a chord on one key and plays it for you.

A [2sl](https://2sl.to) project. The **2sl stab** chip in the device's header links back to 2sl.to: hover it to see the link, click to open it.

Drop `2sl-stab.amxd` on a MIDI track. Keep `2sl-stab.js`, `2sl-stab-ui.js` and `2sl-stab-view.js` next to it, or freeze the device before sharing.

## Controls

Three pages: switch with **play / osc / shape** in the header. The header also has the **preset** menu, the output level (**out**, in dB) and **stop**. Each section but the mixer has a display that shows what its controls are doing.

**Play**: start here.

| section | display | controls |
|---|---|---|
| chord | the chord you're playing: name, notes, a lit keyboard | **Chord** (poly, minor, m7, m9, m11, sus4, fifths, dark), **In Key** (chords from Live's Scale Mode), **Tone** (brighter or darker), **Length** (shorter or longer tails), **Drift** (voicing varies stab to stab) |
| machine | the 16-step pattern: **click a step** to cycle rest → hit → accent; the playhead, hits flashing, throws flashing orange; a status line | **Machine**, **Latch** (tap a chord and it keeps playing), **Pattern** (starting points), **Density**, **Throws**, **Gate**, **Shift** (moves every trigger 0–15 16ths later, wrapping; the display shows the shifted pattern, the saved pattern doesn't change, and picking a Pattern keeps it) |
| dub | the echo: the stab and its repeats (more and darker as Dub goes up), throws, freeze, a live tape level | **Dub** (0 = no echo), **Throw**, **Freeze**, echo **Time** |
| pump | the duck over two beats, with the playhead | **Depth**, **Attack** (ms to full duck: a ramp, never a jump), **Release** (how much of the beat it takes to recover), **Curve** (linear to snappy), pump **Rate** |

**Osc**: laid out like the voice sections of a Juno, Jupiter or Prophet.

| section | display | controls |
|---|---|---|
| dco 1 | its waveform, moving with PWM | wave buttons **saw / pulse / both**, footage **16′ / 8′ / 4′**, **PW**, **PWM** (the LFO on pulse width, the Juno shimmer) |
| dco 2 | its waveform | wave buttons **saw / pulse / tri**, footage, **Semi** (−12 to +12; 7 stacks a fifth), **Fine** (detune in cents) |
| mixer | none: four level dials in a square, and the sub switch | **OSC 1**, **OSC 2**, **Sub**, **Noise**; **Sub** switch as on the Roland SH-101: a square 1 octave below DCO 1, a square 2 octaves below, or a 25% pulse 2 octaves below (DCO 1 divided down, so it follows DCO 1's footage) |
| lfo | the LFO moving, and where it's going | **Rate**, **Vibrato** (LFO → pitch), **Filter** (LFO → cutoff). One LFO for all voices. |

**Shape**

| section | display | controls |
|---|---|---|
| filter | the low-pass response, and (grey) where the envelope opens it | Cutoff, Reso, Env, Key, Vel |
| envelope | the envelope shape (with the Length macro) | Attack, Decay, Sustain, Release (one envelope for amp and filter) |
| drive | the saturation curve | Drive (tape saturation, before the echo) |

The output stage has 6 dB more gain than before, with a soft clip above −2 dBFS so loud chords round off instead of going over.

The machine's steps are saved with the set, so an edited pattern comes back when you reopen it.

**Stop** (top right, on every page) is a panic: it releases every note, clears a latched chord, ramps the voices to silence in 20 ms whatever the release, empties the echo and turns Freeze off. Stopping Live doesn't run it: like any instrument, the device just stops getting notes, and releases and echoes ring out. A latched chord is kept for when Live plays again; with Live stopped, the machine plays only the keys you hold, so you can audition.

### Presets

Picking a preset sets every control, and you can tweak from there. When Live reopens a set, your saved tweaks win. Volumes are matched, so switching presets doesn't jump in level. Each one was rendered through the DSP and its **out** level set from the measured peak and average.

| | preset | idea |
|---|---|---|
| | init | the defaults |
| **dub** | chain stab | Basic Channel-style: saw + pulse with a detuned saw, noise chuff, dark filter opened by a short envelope |
| | m-stab | Maurizio-style: punchier m7 with a little sub, brighter attack, wetter echo |
| | deep haze | Deepchord / Echospace-style: soft pulses shimmering with PWM, slow attack, long tail, slow filter drift |
| | fog | darker still: a triangle an octave down, noisy, dissolving into the echo |
| | wash | Chain Reaction-style: an m7 swelling into a long echo, the filter breathing with the LFO |
| | skank | Rhythm & Sound-style: pulse-heavy offbeat chops from the latched machine |
| | roots chop | two chops a bar, quarter-note echo, the odd throw, a touch of sub |
| | sub stab | low and warm: the sub carrying it, a triangle on top |
| | tape chord | m9 through heavy drive and hiss, a little pitch wobble |
| | ambient dub | a breakdown m11 blooming into a half-note echo, PWM shimmer |
| | throw dub | no echo until it throws: sparse latched stabs, every other one thrown |
| **techno** | hypnotic loop | a sus4 stab off the kick, resonant, a slow filter sweep, pumping, latched |
| | dark machine | the dark shape, resonant and short, 3-3-2, a triangle an octave down for weight |
| | chord memory | UR-style: a bright m7 stab with DCO 2 a fifth up |
| | warehouse | harder, brighter, driven, 16th echo, a fast snappy pump |
| | pulse | Chain Reaction-style minimal dub: harsh pulse fifths, 3-3-2, throws |
| | rolling | every step plus extras, very short, pumping on 8ths |
| | dark fifths | low, resonant fifths held like a drone, with sub and a slow filter breath |
| | throw machine | the machine throwing its own dubs |
| **other** | detroit strings | two saws wide apart, slow in and out, a little vibrato |
| | deep house keys | for chord progressions' clips (poly): pulse keys, velocity opens the filter |
| | pump pad | a sustained m7 breathing with a long, soft 8th-note pump |

## What it's based on

- **The chord.** A minor triad (0, +3, +7) is the stab in nearly every source: [Attack, Old-School House Chords](https://www.attackmagazine.com/technique/synth-secrets/old-school-house-chords/), [Studio Brootle](https://www.studiobrootle.com/dub-techno-tutorial-4-ingredients/), [AudioTent](https://www.audiotent.com/blogs/production-tips/dub-techno-chord-sound-design), [Polarity](https://polarity.me/bitwig-classic-sounddesign/012-dub-chord/). Chord memory on one key is how the original sound was played (Juno-style chord memory, or a pitched chord sample). "Dark" is Attack's +5 +8 variant.
- **The voice.**
  - Saws, pulse and a little noise ("chuff"), from AudioTent and [Attack, Dub Techno Synth Chords](https://www.attackmagazine.com/technique/synth-secrets/dub-techno-synth-chords/) (Diva: saw + square at about 70% pulse width, noise on).
  - A 24 dB low-pass turned down, opened by a short envelope (AudioTent, Brootle).
  - Key tracking (Attack's Diva patch, about 65).
  - Fast attack, medium decay, low sustain.
  - Detuned oscillators (Brootle, Attack).
  - The sub: DCO 1 divided by 2 or 4, three waves as on the Roland SH-101 ([Roland, SH-4d manual, SH-101 model](https://static.roland.com/manuals/sh-4d_v200/en-US/8651802786195467.html); the 25% pulse from [Electric Druid](https://electricdruid.net/a-study-of-sub-oscillators/); notes in `references/README.md`).
- **The chain order:** oscillators → filter → saturation → delay (AudioTent).
- **The dub section.** Producers put the main delay on a send, so this has none. It keeps a small tape echo just for the performance moves the sources describe: throws, feedback rides and holding the loop ("dub delay is played, not dialled in"). It still follows the echo research:
  - **Filters in the feedback loop**, so each repeat gets darker and thinner ([Apple, Tape Delay](https://support.apple.com/kb/PH27575)).
  - Dotted 8ths by default, feedback 60–90% ([Attack, Creating Dub Delays](https://www.attackmagazine.com/technique/tutorials/creating-dub-delays-with-standard-plugins/)).
  - Tape saturation and wobble in the loop.
  - Left and right times offset by +3.1% / −2.1% (Brootle's Echo settings).
  - A drifting delay time (AudioTent's random LFO on the delay times).
  - Diffusion, because reverb before the echoes gives a thicker loop (Softube's Tape Echoes manual).
- **Pump.** Basic Channel-style chords and delay are sidechained to the kick ([Attack, Basic Channel-Style Dub Techno](https://www.attackmagazine.com/technique/beat-dissected/basic-channel-style-dub-techno/)).
- **Machine patterns.** The stab rhythms come from chord progressions' RESEARCH.md: dub dotted stabs, the reggae skank, and the deep stab that avoids the kick (Attack, "Levelling Up Your Chord Stabs").
- **Drift.** Kerri Chandler uses different voicings of the same chord back to back ([Attack, Kerri Chandler Chords](https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords/)).

## Design

The 2sl-ui look, inside Live.
- **Everything drawn is 2sl** (the displays, the header chip, the rules and the labels). Text is Cozette, drawn from its bitmaps: 13 px, and 26 px for the chord name. Colours are the 2sl-ui tokens.
- **Light and dark.** It follows Live's theme, reading `live_surface_bg` through `max.getcolor`, and redraws when `live.colors` reports a change. If Max can't give that colour, it draws dark and says so in the Max window.
- **Live's own controls** (dials, menus, toggles, tabs) stay Live controls, so automation, mapping and Push still work. They're recoloured from the same tokens: an ink arc on an unlit track, toggles as inverted chips, focus in "now" blue.
- **Layout.** 960 × 169 on a 4 px grid. Every section has three bands (display, chips and menus, dials) aligned across the device; the mixer has dials in a square instead.

## Source

The patch is generated. Edit these, then run `python3 src/2sl-stab.py`:
- `src/2sl-stab.py`: the gen~ voice and echo code, the layout, the presets and the theme tokens.
- `src/2sl-stab-ui.template.js`: pages, presets and recolouring.
- `src/2sl-stab-view.template.js`: the displays.

It writes `src/2sl-stab.maxpat`, this `.amxd`, `2sl-stab-ui.js` and `2sl-stab-view.js`. `src/cozette-glyphs.js` comes from `tools/bdf2js.py` and `cozette.bdf` (Cozette v1.30.0).

## Credits

By [2sl](https://2sl.to).

Font: [Cozette](https://github.com/slavfox/Cozette) by slavfox (MIT), embedded as bitmaps in `2sl-stab-view.js`.

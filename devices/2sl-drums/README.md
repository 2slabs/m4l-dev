# 2sl drums

A 909-style drum machine for trying patterns: canned patterns from the sources, Generate and per-voice Reroll, locks, and Grids-style variation that changes the pattern a bar at a time. Seven synthesized voices (BD, SD, RS, CP, CH/OH, RD) in gen~. It's built for sleepy, lo-fi dub techno: the kick can go soft and round, the hats have 6-bit grit, and every voice can be bit-reduced.

**Intermediate version (0.1.0).** It has been built and tested offline only, never opened in Live. "Untested" below lists what only Live can show.

A [2sl](https://2sl.to) project. The **2sl drums** chip in the header links to 2sl.to.

Drop `2sl-drums.amxd` on a MIDI track and press play in Live: it plays from Live's transport. Keep `2sl-drums.js`, `2sl-drums-ui.js` and `2sl-drums-view.js` next to it, or use the frozen `dist/2sl-drums-<version>.amxd`. MIDI notes on the track also play the voices (GM drum notes: 36 BD, 38 SD, 37 RS, 39 CP, 42/44 CH, 46 OH, 51/59 RD), so clips and pads work too.

## Controls

There are three pages: **play / bd sd rs / cp hats rd**. The header has the **preset** menu, the output level (**out**, in dB) and **stop** (a panic button that fades every voice out in 20 ms).

**Play**

| section | display | controls |
|---|---|---|
| pattern | One row per voice, 16 steps. **Click a step** to cycle rest → hit → accent. **Shift-click** sets a ghost, which plays only at high Density or with Variation. Click a voice's **name** to mute it, **L** to lock it, **R** to reroll it. The playhead is outlined in blue, and a fill bar has a warm frame. | **Variation**, **Density**, **Accent**, **Swing** (shuffle 1–7), **Fill** (off / 4 bars / 8 bars) |
| style | The style, the tempo and swing its sources use, the last canned kit, and the bar within the fill phrase | **Style**, **Generate** (a new kit pattern), **Canned** (the style's next kit, as its source has it) |
| mix | Each voice's level, flashing on its hits | a **Level** per voice |

**bd sd rs**: **BD** Tune, Sweep, Decay, Attack, **Soft** (0 = 909 punch, 100 = soft, round, muffled), Bits · **SD** Tune, Tone, Snappy, Bits · **RS** Bits.
**cp hats rd**: **CP** Bits · **Hats** Tune (the ROM clock), CH Decay, OH Decay, Bits (6 = the 909's ROM) · **RD** Tune (pitch and length together), Bits.
Each voice section's display draws that voice's envelope (and the BD's pitch) as the DSP makes it, and flashes on hits.

How the pattern engine plays (all of it is Grids' engine, patterns.md B1):
- Each grade stands for a Grids level: rest 0, ghost 72, hit 144, accent 224 (one level inside each band of patterns.md F's legend).
- **Density** is Grids' threshold: a step plays when its level is above 255 − Density. The default of 50% plays accents and hits but not ghosts.
- **Variation** is Grids' randomness. At the start of each bar, each voice draws a random push of up to 62/255 and adds it to all of its steps for that bar, so weak steps come and go one whole bar at a time. At 0 the pattern repeats exactly.
- **Fill**: in the last beat of every 4th or 8th bar, snare, rim and clap get extra hits, and open hats may switch to closed. The amount scales with Variation, so there are no fills at 0.
- **Lock** keeps a row through Generate, Reroll, Style and Canned.
- The pattern, the locks and the mutes are saved with the set, in hidden parameters.

### Styles

| style | canned kits (patterns.md) | Generate / Reroll draws from |
|---|---|---|
| dub techno | P1 Basic Channel-style (exact), P8 4 ingredients, P1 + rim 16ths | the kits' rows plus P1's offbeat-16th percussion |
| deep house | P3 minimal house, P7 house 124, P4 deep house | the kits' rows |
| detroit | P2 motor city, P2 rim answer | the kits' rows, plus P3's clap |
| dark techno | P7 techno 130, P9 Mills, P5 dark rumble, P6 rolling | the kits' rows plus P10's 3- and 5-16th hat loops |
| euclid | P11 tresillo, bossa, son clave | E(k, 16) at a random rotation |
| grids | five points on the Grids map (nodes) | a random map point: BD, SD and CH from Grids' three channels, CP from the SD channel's accents, OH from the HH channel's offbeat 8ths |

### Presets

Each preset is a style starting point. It sets every control and loads its style's first kit. When Live reopens a set, your saved pattern and tweaks win. Volumes are matched with `tools/render_drums.py`: each preset's pattern plays through the device's own brain and gen~ code, offline, and its **out** level is set so its RMS matches Init's. That renderer is our own GenExpr subset, not Max; see SHORTCUTS.md.

| preset | idea |
|---|---|
| init | dub techno P1, clean 909 |
| basic dub | P1 with Attack's 6-bit clap layer, snare and clap down |
| deep haze | the Deepchord direction: soft, round, longer kick, quiet snare, 6-bit clap, darker 5-bit hats, a little Variation, a fill every 8 bars |
| detroit 909 | P2, shuffle 3 (58%: the source's 55–60%), fills every 4 |
| deep house | P3, shuffle 3, a slightly soft kick |
| dark rolling | P7 techno, shuffle 2 (54%: the source's 50–54%), longer lower kick, fills |
| grids drift | the Grids map, Variation 40, fills every 8 |
| euclid | Toussaint's tresillo kit |

## What it's based on

All sources are in `references/drums/` (README.md, patterns.md, voices.md, production.md).

- **Patterns.** The canned kits are patterns.md's sourced grids, P1–P11. Where a source's grid is a screenshot and only its text is known, the placement is mine and follows the text; those rows are marked `mine` in `src/2sl-drums.py`:
  - P1's rim 16ths ("a couple hits exactly on offbeat 16th notes")
  - P2's snare and rim ("work against each other"; the rim "doesn't ever hit on the same beat as a kick")
  - P4's clap and closed hat
  - P6's ghost kicks ("just before beats two and four")
- **The Grids map** (P12) is read at build time from Grids' firmware: `grids/resources.cc` and the `drum_map` in `pattern_generator.cc`. The interpolation is Grids' `ReadDrumMap`. The tests check the rows at three nodes against patterns.md F's decoding.
- **Variation, Density, accent** are Grids' `EvaluateDrums`: the perturbation is random byte × (randomness >> 2) >> 8, added and clipped at 255; the threshold is ~density; an accent is a level above 192 (B1).
- **Fills** use Elektron's FILL and A:B conditions as the mechanism (B2) and producer practice's "swap an open hat for a closed hat every 8 bars" (B5).
- **Swing** is the 909's shuffle: 7 levels at the 16th scale, 1 = none (B4). It is applied sample-accurately in gen~ as a delay of every second 16th.
- **Euclidean rows** use Bjorklund's algorithm as given by Toussaint (P11). The tests check it against P11's rhythms. Rotation is from Ableton's Euclidean (B3).
- **Voices** (voices.md):
  - **BD**: a triangle VCO restarted by every trigger, then a diode clipper, so it's sine-ish. A pitch sweep falls from high to the base pitch. The amplitude envelope is flat at first and then exponential (ENV-1 "looks like a compressed drum sound"). The click is a pulse plus low-passed noise. Accent gives more amplitude and a longer decay.
  - **SD**: two triangle VCOs in phase, diode-rounded, each with its own envelope, and a pitch bend of about 20 ms. Noise goes through a low-pass, then into two paths: ENV4, which holds 24 ms and then decays over Tone (Whittle), and a high-pass into ENV5. Snappy is the noise level. Accent makes the VCO envelopes start higher and last longer.
  - **RS**: three resonators at 500 / 220 / 1000 Hz (network-909), a diode clipper, a short envelope and a high-pass. Level only, as on the 909.
  - **CP**: noise → band-pass → four chained claps, plus a softer, longer "pseudo-reverb" tail.
  - **CH/OH**: one voice, so a closed hit cuts an open one (B4). The ROM is held at 30 kHz (60 kHz / 2 in the service notes, 30 kHz in SOS: the two agree) and quantized to 6 bits before the VCA, as on the 909, whose samples were compressed before quantizing. That's why the grit decays with the hat. Two low-passes follow. The Tune range ×0.43 to ×1.7 is Whittle's mod.
  - **RD**: the same ROM idea. There is no decay knob, and the length follows the clock, as on the 909.
  - The analog voices share one noise source, so the snare and clap phase together.
- **Bit reduction** lives here because it changes the drum sounds themselves. Attack's dub techno clap layer uses 6 bits (production.md). Hiss, noise and field recordings are not here; they belong to a separate device (IDEAS.md).
- **Soft kick**: "muffled 909 kick", "muffled kick drums" (production.md). The kick serves: Modell calls it "a metronome".

## Unsourced / to tune

- **909 numbers no source gives**:
  - BD: base pitch 30–90 Hz (default 50); sweep up to ×4 over 30 ms; click pulse 1.5 ms and noise 6 ms; output low-pass 9 kHz.
  - SD: VCO 1 at 180 Hz and VCO 2 at ×1.83. These are SOS's generic patch (180 / 330 Hz), not the 909. Also: bend depth 0.4; VCO decays 180 / 90 ms; noise low-pass 7 kHz, high-pass 1.8 kHz; ENV5 90 ms.
  - RS: ring times 28 / 36 / 18 ms, VCA 40 ms, high-pass 250 Hz.
  - CP: claps 11 ms apart, the last decaying over 20 ms, a 150 ms tail, band 800–2400 Hz.
  - Hats and ride: the six "metal" frequencies; the ride's length (1.6 s at ×1); the 11 / 10 kHz output low-passes.
- **Disagreements, and what I picked**:
  - BD oscillator: triangle + diode (network-909, Whittle), not SOS's saw.
  - BD Tune: the base pitch (owner's manual), with sweep depth as its own Sweep knob (network-909's VR2).
  - Noise: white noise, not the 909's shift register (sources disagree on 32 vs 36 stages, and no clock is given).
  - Hat decay: CH and OH each get their own Decay, rather than the 909's CH ≈ OH / 10 coupling.
- **Hat and ride "samples"**: we have no 909 ROM, so they are metallic noise (six squares plus noise, high-passed) made flat, held at 30 kHz and quantized. It has the 6-bit grit, but it isn't the 909's cymbal.
- **Pattern engine choices**:
  - The four grade levels (0 / 72 / 144 / 224).
  - Hit velocity: 0.5 to 0.8 rising with the level; 1 for an accent.
  - Accent amount default 70%.
  - One Density for all voices (Grids has three).
  - Fill content: snare, rim and clap rests in the last beat get hits at Variation × 50%; an open hat becomes closed at Variation × 100%.
  - The Grids style's clap (SD accents) and open hat (HH offbeat 8ths); no rim or ride there, because Grids has three channels.
  - The Euclid style's k ranges per voice.
  - Generate picks each voice's row from the style's pool independently, so kits mix sources within a style.
- **The shuffle levels as percentages**: 50, 54, 58, 62.5, 67, 71, 75%. No source maps a 909 shuffle level to a percent. This reads level n as 2(n−1) ticks of 96 ppqn on every second 16th.
- **avrlib's `U8Mix`** (Grids' crossfade) is written from memory as (a·(255−t) + b·t) >> 8. `avrlib/op.h` isn't mirrored.
- **Voice balance and headroom**: hats +8 dB and clap −4 dB inside the voices; the kit × 0.4 (−8 dB) before the soft clip. Init peaks at −2.7 dBFS in the offline render.
- **Accent**: the 909's per-voice accent is fixed; here a single Accent control sets how much quieter a normal hit is.

## Untested (only Live can show)

- Everything audible. The voices were checked with our GenExpr subset (`tools/genexpr.py`), which catches syntax and scoping and renders the code, not by gen~'s compiler.
- The transport clock and timing jitter of [js] (the step trigger comes from the low-priority thread, like 2sl stab's; swing is then sample-accurate in gen~).
- Hidden-parameter storage when a set is reopened.
- The Info View text, the recolouring, light and dark themes, how a live.text button sends Generate and Canned, and how the grid feels to click.
- Whether gen~ accepts every builtin used (`fract`, `wrap`, `mstosamps`, `dbtoa` are standard gen operators).

## Licence

The Grids pattern map (25 nodes of `grids/resources.cc`, © Emilie Gillet, GPLv3) is embedded in `2sl-drums.js`, so that script, and any device that includes it, is a derivative of GPLv3 code and has to be shared under GPLv3. That includes the frozen `.amxd`, which embeds the script. To ship the device under another licence, drop the Grids style and its data.

## Design

The 2sl-ui look, built on the shared kit (`src/2sl_kit.py`, `src/2sl-kit-*.template.js`):
- 960 × 169 on a 4 px grid, with three bands (display, chips/menus, dials) aligned across each page. The pattern grid is the one display that takes two bands, because seven rows need the height.
- Displays are drawn in Cozette with the 2sl-ui tokens, light or dark to follow Live's theme.
- Live's controls are recoloured from the same tokens.
- Every control and display has Info View text.

## Source

The patch is generated. Edit these, then run `python3 src/2sl-drums.py` (it needs `references/drums/mirror/patterns/grids_*.cc`, from `references/drums/mirror_patterns.sh`):

- `src/2sl-drums.py`: voices, styles and canned kits, Info text, layout, the Init values (BASE).
- `src/2sl-drums-presets.json`: the presets.
- `src/2sl_drums_dsp.py`: the gen~ voices (GenExpr).
- `src/2sl-drums-brain.template.js`: the pattern engine. It becomes `2sl-drums.js`, with the kit's clock and the data.
- `src/2sl-drums-view.template.js`: the displays, inserted into the kit's view template.
- The kit: `src/2sl_kit.py`, `src/2sl-kit-ui.template.js`, `src/2sl-kit-view.template.js`, `src/2sl-kit-clock.template.js`.

Checks:

- `node tests/2sl-drums.test.js`: the pattern engine (Generate, Reroll, lock, Variation, Density, fills, swing timing, storage, the clock, MIDI, loud failures), the UI script and every display.
- `python3 tools/es5check.py devices/2sl-drums/*.js`: ES5 syntax, which is what Max's js needs.
- The build checks the gen~ code with `tools/genexpr.py`, our GenExpr subset checker; `python3 tools/test_genexpr.py` tests the checker itself, including against 2sl stab's gen~ code.
- `python3 tools/render_drums.py`: renders the presets to `dist/renders/*.wav` and prints the loudness table.

## Credits

By [2sl](https://2sl.to). Grids pattern data: Emilie Gillet, Mutable Instruments (GPLv3). Font: [Cozette](https://github.com/slavfox/Cozette) by slavfox (MIT).

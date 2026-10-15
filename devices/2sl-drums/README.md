# 2sl drums

A 909-style drum machine for trying patterns. You make a pattern with **functions**: generators make new rows (canned kits from the sources, the Grids map, Euclidean rhythms, random) and modifiers change the rows there are (shift, reverse, thin, ghosts, fill, open hats, accent). **Run** applies one function to the rows you select, **Undo** steps back. Seven synthesized voices (BD, SD, RS, CP, CH/OH, RD) in gen~. It's built for sleepy, lo-fi dub techno: the kick can go soft and round, the hats have 6-bit grit, and every voice can be bit-reduced.

**Intermediate version (0.2.0).** It has been built and tested offline only, never opened in Live. "Untested" below lists what only Live can show.

A [2sl](https://2sl.to) project. The **2sl drums** chip in the header links to 2sl.to.

Drop `2sl-drums.amxd` on a MIDI track and press play in Live: it plays from Live's transport. Keep `2sl-drums.js`, `2sl-drums-ui.js` and `2sl-drums-view.js` next to it, or use the frozen `dist/2sl-drums-<version>.amxd`. MIDI notes on the track also play the voices (GM drum notes: 36 BD, 38 SD, 37 RS, 39 CP, 42/44 CH, 46 OH, 51/59 RD), so clips and pads work too.

The device is 920 × 169 px.

## Controls

There are two pages: **pattern** and **kit**. The header has the **preset** menu (kit sounds), the output level (**out**, in dB) and **stop** (a panic button that fades every voice out in 20 ms).

### Pattern

| part | what it does |
|---|---|
| grid (left) | One row per voice, 16 steps. **Click a step** to cycle rest → hit → accent → rest; **shift-click** sets a ghost. **Click a voice's name** to select only its row; **shift-click** names to select several; click the only selected row again to select every row. Selected names are lit. The playhead is outlined in blue. |
| **Function** (the tab across the top right) | The one function Run applies. Each function's settings sit in the column under its name, all visible at once: one Live parameter (a number box) per setting. |
| **Run** | Applies the lit function to the selected rows only (the other rows stay as they are) and adds the result to the history. |
| **Undo** | Steps back to the pattern before. Run after an Undo drops the patterns you undid (there's no redo). |
| status line | Top: what Run will do now (the function, its settings, the rows). Bottom: where you are in the history and what made this pattern. |
| **Swing** | The 909's shuffle, 1 (none) to 7. |

The model (the user's design, `PLANS/2026-10-15-2sl-drums-functions.md`): a generator is a pure function settings → rows; a modifier is a pure function (pattern, settings) → pattern. A hand edit is one more modifier. The device keeps the history p0..pt; Run makes p(t+1) from p(t). The history keeps the **last 100 patterns** (the oldest go); it isn't saved with the set. The pattern playing and the row selection are saved with the set, in hidden parameters, and so are the function, its settings and Swing (they are Live parameters). When Live reopens a set, the history starts from the saved pattern.

### Functions

| function | kind | settings: range (default) | what it does | source |
|---|---|---|---|---|
| canned | generator | kit 1–15 (1); from 0–7 (0) | The kit's rows. From 0: each row gets its own voice's row; 1–7 (bd sd rs cp ch oh rd): every selected row gets that voice's row. | patterns.md P1–P11 |
| grids | generator | x 0–255 (128); y 0–255 (128); density 0–100% (50%) | The Grids map at x, y. A step plays when its level is above 255 − density; above 192 it's an accent. BD, SD, CH from Grids' three channels; CP = the SD channel's accents; OH = the HH channel's offbeat 8ths. RS and RD have no channel: Run keeps them and says so. | P12, B1 |
| euclid | generator | hits 0–16 (4); rotation 0–15 (0); steps 1–16 (16) | E(hits, steps), rotated, repeated across the bar (P10's 3- and 5-step hat loops are E(1,3) and E(1,5)). More hits than steps play every step, and the status line says so. | P11 (Toussaint), B3, P10 |
| random | generator | density 0–100% (30%); accent 0–100% (10%); seed 0–999 (0) | Each step is a hit with density's chance, a hit an accent with accent's chance. The same seed gives the same rows; seed 0 rolls a new seed each Run, and the history line shows which, so you can dial it back. | B2 (probability), B3 (Seed) |
| shift | modifier | steps −15–15 (1) | Moves the rows later (+) or earlier (−), wrapping around the bar. | B3 (Rhythm Shift) |
| reverse | modifier | none | Plays the rows backwards from the downbeat: step 1 stays, 2 swaps with 16, 3 with 15 … | unsourced |
| thin | modifier | amount 0–100% (25%) | Removes that share of each row's hits, the weakest first: ghosts, then hits, then accents; within a grade the weakest place in the bar first. | B1 (density keeps the strongest steps) |
| ghosts | modifier | amount 0–100% (25%) | Turns that share of each row's rests into ghosts: first the rests just before a hit, then the weakest places in the bar. | B5 (ghost notes), P6 (ghost kicks before beats 2 and 4) |
| fill | modifier | steps 1–16 (4); density 0–100% (50%) | Hits on the rests of the bar's last steps (4 = the last beat, 8 = the last half bar), spread evenly: E(density × steps, steps). Run it, hear it, Undo it. | B2 (FILL), P11 |
| open hh | modifier | amount 0–100% (50%) | Moves that share of the closed hat's hits to the open hat, offbeat 8ths first. It needs both ch and oh selected (else Run says so and changes nothing). | B5 (swap open and closed hats), P1/P2 (offbeat open hats) |
| accent | modifier | every 1–16 (4); offset 0–15 (0) | Every Nth hit of each row becomes an accent, starting after `offset` hits; the others become plain hits; ghosts stay. | B3 (Accent Frequency, Accent Offset) |

None of the modifiers draws random numbers: the same pattern and settings always give the same result. Only random has a seed.

The canned kits (`kit`): 1 P1 basic channel, 2 P8 4 ingredients, 3 P1 + rim 16ths, 4 P3 minimal house, 5 P7 house 124, 6 P4 deep house, 7 P2 motor city, 8 P2 rim answer, 9 P7 techno 130, 10 P9 mills 137, 11 P5 dark rumble, 12 P6 rolling, 13 P11 tresillo, 14 P11 bossa, 15 P11 son clave. The Init pattern is kit 1.

Adding a function is one entry in `src/2sl-drums-functions.js`'s `FUNCTIONS`: name, kind, Info text, its settings (name, min, max, initial, unit, Info text) and the function itself. The build reads the entries and makes the Function tab, one number box per setting and their Info text from them.

### Playback

Each step plays at its grade's velocity: ghost 0.2, hit 0.7, accent 1. The voices then scale a non-accent by **Accent** (the 909's Total Accent). Every bar plays the same pattern: variation happens by Run, not during playback.

### Kit

| part | what it does |
|---|---|
| **Voice** buttons (bd sd rs cp hats rd) | Show that voice's display and sound controls. Controls you can't see keep working. |
| **BD** | Tune, Sweep, Decay, Attack, **Soft** (0 = 909 punch, 100 = soft, round, muffled), Bits |
| **SD** | Tune, Tone, Snappy, Bits |
| **RS**, **CP** | Bits (level only on the 909) |
| **Hats** | Tune (the ROM clock), CH Decay, OH Decay, Bits (6 = the 909's ROM). CH and OH are one voice: a closed hit cuts an open one. |
| **RD** | Tune (pitch and length together), Bits |
| mixer | For every voice: a **Level** dial, **m** (mute) and **s** (solo). While any voice is soloed, only soloed voices sound; a mute wins over a solo. Mute and solo act in the voices (5 ms fades), so they silence MIDI notes too, and a ringing open hat. The display shows each level, flashing on hits, dimmed when the voice doesn't sound. |
| **Accent** | How much quieter a normal hit (or a ghost) is than an accent. Default 70%. |

Each voice display draws that voice's envelope (and the BD's pitch) as the DSP makes it, and flashes on hits. There is no pan: the kit is mono (both outputs carry the same signal).

### Presets

The presets are **kit sounds**: they set every voice control, the levels and Accent, and the output level. They leave the pattern, the functions, Swing and the mixer's mutes and solos alone. Patterns are made with the functions now, so the old presets' style, variation and fill settings are gone; their sound settings stayed. Volumes are matched with `tools/render_drums.py`: each preset plays the Init pattern through the device's own brain and gen~ code, offline, and its **out** level is set so its RMS matches Init's. That renderer is our own GenExpr subset, not Max; see SHORTCUTS.md.

| preset | idea |
|---|---|
| init | clean 909 |
| basic dub | Attack's 6-bit clap layer, snare and clap down |
| deep haze | the Deepchord direction: soft, round, longer kick, quiet snare, 6-bit clap, darker 5-bit hats |
| detroit 909 | a shorter kick, the rim up, the closed hat down |
| deep house | a slightly soft kick, shorter closed hat |
| dark rolling | longer lower kick, ride and closed hat down |
| soft grit | a softer kick and 5-bit hats |

## What it's based on

All sources are in `references/drums/` (README.md, patterns.md, voices.md, production.md).

- **Patterns.** The canned kits are patterns.md's sourced grids, P1–P11. Where a source's grid is a screenshot and only its text is known, the placement is mine and follows the text; those rows are marked `mine` in `src/2sl-drums.py`:
  - P1's rim 16ths ("a couple hits exactly on offbeat 16th notes")
  - P2's snare and rim ("work against each other"; the rim "doesn't ever hit on the same beat as a kick")
  - P4's clap and closed hat
  - P6's ghost kicks ("just before beats two and four")
- **The Grids map** (P12) is read at build time from Grids' firmware: `grids/resources.cc` and the `drum_map` in `pattern_generator.cc`. The interpolation is Grids' `ReadDrumMap`; the threshold is Grids' `level > ~density`, an accent a level above 192 (B1). The tests check the rows at three nodes against patterns.md F's decoding.
- **Euclidean rows** use Bjorklund's algorithm as given by Toussaint (P11); the tests check it against P11's rhythms. Rotation is from Ableton's Euclidean (B3).
- **Shift**, **accent** (Accent Frequency, "an accented note is counted as a note occurrence", and Accent Offset) and random's density come from Ableton's Rhythm and Seed tools (B3). Selecting rows and running a function again on others follows Rhythm's own workflow ("deselect the previously generated notes and adjust Rhythm's parameters again for a different … drum pad", B3).
- **Fill** is Elektron's FILL idea (B2), made a step you run and undo. **Open hh** is producer practice's open/closed hat swap (B5). **Ghosts**: B5's ghost-note velocities (15–35 of 127) and P6's ghost kicks.
- **Swing** is the 909's shuffle: 7 levels at the 16th scale, 1 = none (B4). It is applied sample-accurately in gen~ as a delay of every second 16th.
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

- **Function choices no source makes**:
  - The metric weights thin, ghosts and open hh order steps by: the downbeat, then beat 3, then beats 2 and 4, then 8ths, then 16ths (the usual metric hierarchy). Ties: thin and open hh take the later step first, ghosts the earlier.
  - Reverse around the downbeat (step 1 stays) rather than a mirror of the bar.
  - Fill's hits are plain hits, spread with E(k, n) from the window's first step.
  - Grids' clap (SD accents) and open hat (HH offbeat 8ths); no rim or ride there, because Grids has three channels. One density for all rows (Grids has three: select rows and Run again for another).
  - Random's generator: Park and Miller's minimal standard (a Lehmer generator), seeded per row from the seed; written from memory, not mirrored.
  - Seed 0 = roll. The history limit of 100.
  - The hit velocity 0.7 (the ghost's 0.2 is B5's 15–35 of 127; an accent is 1).
  - Function names fit the Function tab: "open hh" for open hats.
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
- **The shuffle levels as percentages**: 50, 54, 58, 62.5, 67, 71, 75%. No source maps a 909 shuffle level to a percent. This reads level n as 2(n−1) ticks of 96 ppqn on every second 16th.
- **avrlib's `U8Mix`** (Grids' crossfade) is written from memory as (a·(255−t) + b·t) >> 8. `avrlib/op.h` isn't mirrored.
- **The mixer**: mute wins over solo; 5 ms gate fades.
- **Voice balance and headroom**: hats +8 dB and clap −4 dB inside the voices; the kit × 0.4 (−8 dB) before the soft clip. Init peaks at −2.9 dBFS in the offline render.
- **Accent**: the 909's per-voice accent is fixed; here a single Accent control sets how much quieter a normal hit is.

## Untested (only Live can show)

- Everything audible. The voices were checked with our GenExpr subset (`tools/genexpr.py`), which catches syntax and scoping and renders the code, not by gen~'s compiler.
- The transport clock and timing jitter of [js] (the step trigger comes from the low-priority thread, like 2sl stab's; swing is then sample-accurate in gen~).
- Hidden-parameter storage when a set is reopened (the pattern and the row selection).
- The pattern page in Live: whether the Function tab's names fit its 54 px columns in Live's font (the build checks them against the kit's 6 px-a-character rule), how the number boxes look and drag (Int and Percent unit styles; random's seed is a float parameter shown as Int, because Live's Int type holds 256 values), and how a live.text button sends Run and Undo.
- The kit page in Live: the Voice buttons showing and hiding their controls (the UI script's `sendbox hidden`, tested offline), the mute and solo chips.
- The Info View text, the recolouring, light and dark themes, and how the grid feels to click.
- Whether gen~ accepts every builtin used (`fract`, `wrap`, `mstosamps`, `dbtoa` are standard gen operators).

## Licence

The Grids pattern map (25 nodes of `grids/resources.cc`, © Emilie Gillet, GPLv3) is embedded in `2sl-drums.js`, so that script, and any device that includes it, is a derivative of GPLv3 code and has to be shared under GPLv3. That includes the frozen `.amxd`, which embeds the script. To ship the device under another licence, drop the grids function and its data.

## Design

The 2sl-ui look, built on the shared kit (`src/2sl_kit.py`, `src/2sl-kit-*.template.js`):
- 920 × 169 on a 4 px grid. The pattern page: the grid on the left (it takes the full height: seven rows need it), the functions on the right, a 54 px column each, Run / Undo / the status line / Swing along the bottom. The kit page keeps stab's three bands (display, chips and buttons, dials): the selected voice on the left, the mixer on the right. The build fails if anything shown at the same time overlaps.
- Displays are drawn in Cozette with the 2sl-ui tokens, light or dark to follow Live's theme.
- Live's controls are recoloured from the same tokens.
- Every control and display has Info View text.

## Source

The patch is generated. Edit these, then run `python3 src/2sl-drums.py` (it needs `references/drums/mirror/patterns/grids_*.cc`, from `references/drums/mirror_patterns.sh`, and libduktape for reading the function registry):

- `src/2sl-drums-functions.js`: the functions, their settings and Info text (the registry), and the helpers they share. It becomes part of `2sl-drums.js`.
- `src/2sl-drums.py`: voices, canned kits, Info text, layout, the Init values (BASE).
- `src/2sl-drums-presets.json`: the presets.
- `src/2sl_drums_dsp.py`: the gen~ voices (GenExpr) and the mixer's gates.
- `src/2sl-drums-brain.template.js`: the engine (Run, Undo, the history, selection, playback, storage). It becomes `2sl-drums.js`, with the functions, the kit's clock and the data.
- `src/2sl-drums-view.template.js`: the displays, inserted into the kit's view template.
- The kit: `src/2sl_kit.py`, `src/2sl-kit-ui.template.js`, `src/2sl-kit-view.template.js`, `src/2sl-kit-clock.template.js`.

Checks:

- `node tests/2sl-drums.test.js`: every function against its sources, purity, the registry against the Live parameters, Run / Undo / the history and its limit, selection, the hand edit, storage round trips, playback velocities, swing timing, the clock, MIDI, the mixer's wiring, the Voice groups, loud failures, the UI script and every display.
- `python3 tests/test_2sl_kit.py`: the kit's layout check, groups, controls kept out of presets.
- `python3 tools/es5check.py devices/2sl-drums/*.js`: ES5 syntax, which is what Max's js needs.
- The build checks the gen~ code with `tools/genexpr.py`, our GenExpr subset checker; `python3 tools/test_genexpr.py` tests the checker itself, including against 2sl stab's gen~ code.
- `python3 tools/render_drums.py`: renders the presets to `dist/renders/*.wav` and prints the loudness table.

## Credits

By [2sl](https://2sl.to). Grids pattern data: Emilie Gillet, Mutable Instruments (GPLv3). Font: [Cozette](https://github.com/slavfox/Cozette) by slavfox (MIT).

# 2sl drums

A 909-style drum machine for trying patterns. You make a pattern with **functions**: generators make new rows (canned kits from the sources, the Grids map, Euclidean rhythms, random) and modifiers change the rows there are (shift, reverse, thin, ghosts, fill, open hats, accent). Three knobs drive them, all MIDI-mappable: **Voice** (one row, or all), **Function**, and **Seed**, which walks every variant of the function and plays it as you turn. **Undo** steps back. Seven synthesized voices (BD, SD, RS, CP, CH/OH, RD) in gen~. It's built for sleepy, lo-fi dub techno: the kick can go soft and round, the hats have 6-bit grit, and every voice can be bit-reduced.

**Intermediate version (0.3.0).** It has been built and tested offline only, never opened in Live. "Untested" below lists what only Live can show.

A [2sl](https://2sl.to) project. The **2sl drums** chip in the header links to 2sl.to.

Drop `2sl-drums.amxd` on a MIDI track and press play in Live: it plays from Live's transport. Keep `2sl-drums.js`, `2sl-drums-ui.js` and `2sl-drums-view.js` next to it, or use the frozen `dist/2sl-drums-<version>.amxd`. MIDI notes on the track also play the voices (GM drum notes: 36 BD, 38 SD, 37 RS, 39 CP, 42/44 CH, 46 OH, 51/59 RD), so clips and pads work too.

The device is 944 × 169 px (the pattern page sets the width).

## Controls

There are two pages: **pattern** and **kit**. The header has the **preset** menu (kit sounds), the output level (**out**, in dB) and **stop** (a panic button that fades every voice out in 20 ms).

### Pattern

| part | what it does |
|---|---|
| grid (left) | One row per voice, 16 steps. **Click a step** to cycle rest → hit → accent → rest; **shift-click** sets a ghost. The names of the rows Voice picks are lit. **Click a voice's name** to pick that row: the Voice dial moves, just as turning it would (it commits). A click on the name of the row Voice already picks picks all; on all, a click on a name picks that row. The playhead is outlined in blue. While you turn Seed or a setting, the grid shows the live result. |
| **Voice** | The row the function changes: bd, sd, rs, cp, ch, oh, rd, or **all** (the last). On all, generators make the whole kit and modifiers change every row. |
| **Function** | A button per function, in two rows: the generator or modifier. It is one Live parameter (a list of the functions), so a MIDI knob mapped to it sweeps through them. Only the chosen function's setting dials show, to the right. |
| **Seed** | Walks the function's variants: every combination of its settings in one list, the finest setting changing fastest. Turning Seed moves the setting dials; turning a setting dial moves Seed. |
| setting dials | The function's settings (one Live parameter each; the table below). Each function keeps its own. |
| **Undo** | Drops what you turned since the last commit (the pattern goes back to the base, the dials back to where you started). Else steps back one commit. A commit after an Undo drops the patterns you undid (there's no redo). |
| **Clear** | Clears the row Voice picks (every row, on all): all rests. It commits what you were turning first; the clear is one history step, and Undo brings the row back. A clear that changes nothing is no step (the Max window says so). |
| status line | Line 1: Voice, Function, Seed's place (seed n / how many). Line 2: the settings. Line 3: "the base", "live: …" with what is shown, or a warning in blue (open hh on a row other than oh, a row grids has nothing for). Line 4: where you are in the history, and what made the pattern. |
| **Swing** | The 909's shuffle, 1 (none) to 7. |

How it works (the user's design: `PLANS/2026-10-15-2sl-drums-knobs.md`, on the function model of `PLANS/2026-10-15-2sl-drums-functions.md`):

- A generator is a pure function settings → rows; a modifier is a pure function (pattern, settings) → pattern. A hand edit is one more modifier.
- **Live, with no Run.** The first turn of Seed or a setting after a commit takes the pattern as it is as the **base**. Every turn then shows (and plays) f(base, settings) on the rows Voice picks, at once, the settings you started from too: to put the remembered settings on another row, turn any knob away and back. The base itself comes back by Undo, or by a modifier's settings that change nothing (shift 0, thin 0% ...).
- **Commits.** Moving Voice or Function commits what is shown as one history step, and it becomes the next base; it doesn't apply anything itself. A hand edit and Clear commit first, then are a step of their own. Nothing changed: no step.
- **Each function remembers its settings** when you switch away and back. Coming back doesn't apply them: the base is the pattern as it is now, and the remembered settings are where the next turning starts.
- The history keeps the **last 100 commits** (the oldest go); it isn't saved with the set. The pattern playing (live or committed) is saved with the set, in hidden parameters, and so are Voice, Function, every setting, Seed and Swing (they are Live parameters). When Live reopens a set, the history starts from the saved pattern, and Seed is set from the saved settings if the two disagree.

**Seed** is one Live parameter for every function, a float from 0 to 100%: how far through the active function's variants it is (0% the first variant, 100% the last). Live's Int type holds only 256 values and the functions have up to ten million variants, so the brain scales Seed to the function; the status line shows the variant number. A 32-bit float holds every position exactly while a function has fewer than 2^24 variants; the registry check holds every function to that. When the brain moves a dial (Seed from a setting, the settings from Seed, Undo), the dial sends the value back at once, as Live's dials do; the brain knows its own echoes (also late ones) and ignores them, so nothing moves twice and no history step comes from them. One knob's sweep covers a whole function, so on a big function (grids, random, euclid) a MIDI knob moves Seed in large jumps: there, the setting dials are the fine control.

### Functions

The order lists the settings Seed walks, finest (fastest) first; the variants are every combination of them.

| function | kind | settings: range (initial) | order, finest first (variants) | what it does | source |
|---|---|---|---|---|---|
| canned | generator | kit 1–15 (1); from 0–7 (0) | kit, from (120) | The kit's rows. From 0: each row gets its own voice's row; 1–7 (bd sd rs cp ch oh rd): the row (or every row, on all) gets that voice's row. | patterns.md P1–P11 |
| grids | generator | x 0–255 (128); y 0–255 (128); density 0–100% (50%) | density, x, y (6,619,136) | The Grids map at x, y. A step plays when its level is above 255 − density; above 192 it's an accent. BD, SD, CH from Grids' three channels; CP = the SD channel's accents; OH = the HH channel's offbeat 8ths. RS and RD have no channel: they stay as they are, and the status line says so. | P12, B1 |
| euclid | generator | hits 0–16 (4); rotation 0–15 (0); steps 1–16 (16) | rotation, hits, steps (4,352) | E(hits, steps), rotated, repeated across the bar (P10's 3- and 5-step hat loops are E(1,3) and E(1,5)). More hits than steps play every step, and the status line says so. | P11 (Toussaint), B3, P10 |
| random | generator | density 0–100% (30%); accent 0–100% (10%); seed 0–999 (0) | seed, accent, density (10,201,000) | Each step is a hit with density's chance, a hit an accent with accent's chance. The same seed gives the same rows. | B2 (probability), B3 (Seed) |
| shift | modifier | steps −15–15 (0) | steps (31) | Moves the rows later (+) or earlier (−), wrapping around the bar. | B3 (Rhythm Shift) |
| reverse | modifier | span 1–16 (1) | span (16) | Plays each span of steps backwards from its first step: 16 = the bar (step 1 stays, 2 swaps with 16, 3 with 15 …), 8 = each half bar, 4 = each beat. 1 and 2 change nothing. | unsourced |
| thin | modifier | amount 0–100% (0%) | amount (101) | Removes that share of each row's hits, the weakest first: ghosts, then hits, then accents; within a grade the weakest place in the bar first. | B1 (density keeps the strongest steps) |
| ghosts | modifier | amount 0–100% (0%) | amount (101) | Turns that share of each row's rests into ghosts: first the rests just before a hit, then the weakest places in the bar. | B5 (ghost notes), P6 (ghost kicks before beats 2 and 4) |
| fill | modifier | steps 1–16 (4); density 0–100% (0%) | density, steps (1,616) | Hits on the rests of the bar's last steps (4 = the last beat, 8 = the last half bar), spread evenly: E(density × steps, steps). | B2 (FILL), P11 |
| open hh | modifier | amount 0–100% (0%) | amount (101) | Moves that share of the closed hat's hits to the open hat, offbeat 8ths first. On one row it reads ch and writes only oh, whichever row Voice picks (on any row but oh the status line says so, in blue, and the Max window too); on all the hits move (ch loses them). On oh alone, ch keeps its hits: where both play, the open hat sounds (the voice takes the open hit last). | B5 (swap open and closed hats), P1/P2 (offbeat open hats) |
| accent | modifier | every 1–16 (4); offset 0–15 (0) | offset, every (256) | Every Nth hit of each row becomes an accent, starting after `offset` hits; the others become plain hits; ghosts stay. | B3 (Accent Frequency, Accent Offset) |

The modifiers start where they change nothing (shift 0, reverse 1, thin, ghosts, fill and open hh at 0%), so the first turn from there is the first change; accent has no such setting.

None of the functions draws random numbers when it runs: the same pattern and settings always give the same result (random's rows come from its seed).

The canned kits (`kit`): 1 P1 basic channel, 2 P8 4 ingredients, 3 P1 + rim 16ths, 4 P3 minimal house, 5 P7 house 124, 6 P4 deep house, 7 P2 motor city, 8 P2 rim answer, 9 P7 techno 130, 10 P9 mills 137, 11 P5 dark rumble, 12 P6 rolling, 13 P11 tresillo, 14 P11 bossa, 15 P11 son clave. The Init pattern is kit 1.

Adding a function is one entry in `src/2sl-drums-functions.js`'s `FUNCTIONS`: name, kind, Info text, its settings (name, min, max, initial, unit, Info text; at least one, at most three), their `order` (finest first) and the function itself. The build reads the entries and makes the Function buttons, one dial per setting (shown only while Function picks it) and their Info text from them.

### Playback

Each step plays at its grade's velocity: ghost 0.2, hit 0.7, accent 1. The voices then scale a non-accent by **Accent** (the 909's Total Accent). Every bar plays the same pattern: variation happens by the knobs, not during playback.

### Kit

| part | what it does |
|---|---|
| **Voice** buttons (bd sd rs cp hats rd; the Live parameter Kit Voice) | Show that voice's display and sound controls. Controls you can't see keep working. |
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
- **Shift**, **accent** (Accent Frequency, "an accented note is counted as a note occurrence", and Accent Offset) and random's density come from Ableton's Rhythm and Seed tools (B3).
- **Fill** is Elektron's FILL idea (B2), made a step you turn and undo. **Open hh** is producer practice's open/closed hat swap (B5). **Ghosts**: B5's ghost-note velocities (15–35 of 127) and P6's ghost kicks.
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
  - Grids' clap (SD accents) and open hat (HH offbeat 8ths); no rim or ride there, because Grids has three channels. One density for all rows (Grids has three: pick one row and turn again for another).
  - Random's generator: Park and Miller's minimal standard (a Lehmer generator), seeded per row from the seed; written from memory, not mirrored.
  - The history limit of 100.
  - The variant order. The plan asks for "every combination of the settings in one list (mixed radix), ordered so neighbours sound alike, the finest setting changing fastest". It is a reflected mixed radix (a Gray code): when the finest setting reaches its end, the next one takes a step and the finest runs back, instead of jumping from its top to its bottom. So two neighbouring variants always differ in one setting by one step.
  - The orders the plan doesn't give (it gives shift, euclid and random): canned kit before from (the kits are listed by style, so neighbours are related kits); grids density, then x, then y (a density step moves the threshold 2.55 levels, a hit at most; x and y each move the map point 1/64 of the way between two nodes); fill density before steps (a hit at most); accent offset before every (the accents move to the next hit and keep their number).
  - Reverse's span (reverse had no setting, and Seed needs one to have anything to walk). The modifiers' initial settings at "no change".
  - Open hh on one row writes only oh: on oh alone the ch hits stay too.
  - The hit velocity 0.7 (the ghost's 0.2 is B5's 15–35 of 127; an accent is 1).
  - Function names fit a Function button (54 px): "open hh" for open hats.
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
- Hidden-parameter storage when a set is reopened (the pattern), and the order Live restores Voice, Function, Seed and the settings in (the tests try one order; the brain takes the settings as the truth whatever the order).
- The pattern page in Live: the Voice dial showing its choice's name; the Function live.tab laid out in two rows (`num_lines_presentation`) and swept by a MIDI knob; how the setting dials look and drag (Int and Percent unit styles; random's seed setting is a float shown as Int, because Live's Int type holds 256 values); Function's group showing and hiding the setting dials (`sendbox hidden`, tested offline); how a live.text button sends Undo.
- Seed in Live: that Live holds its float exactly enough (the tests assume a 32-bit float), that a dial set from the brain sends the value straight back, as a live.dial does with a number it is sent (the brain is tested with echoes at once and late; one that never came back would make it take one later turn of that dial to the same value for the echo), and how far a MIDI knob jumps on a big function.
- The kit page in Live: the Voice buttons showing and hiding their controls (the UI script's `sendbox hidden`, tested offline), the mute and solo chips.
- The Info View text, the recolouring, light and dark themes, and how the grid feels to click.
- Whether gen~ accepts every builtin used (`fract`, `wrap`, `mstosamps`, `dbtoa` are standard gen operators).

## Licence

The Grids pattern map (25 nodes of `grids/resources.cc`, © Emilie Gillet, GPLv3) is embedded in `2sl-drums.js`, so that script, and any device that includes it, is a derivative of GPLv3 code and has to be shared under GPLv3. That includes the frozen `.amxd`, which embeds the script. To ship the device under another licence, drop the grids function and its data.

## Design

The 2sl-ui look, built on the shared kit (`src/2sl_kit.py`, `src/2sl-kit-*.template.js`):
- 944 × 169 on a 4 px grid: the width the pattern page needs (the build takes the widest of the pages and the header). The pattern page: the grid on the left (it takes the full height: seven rows need it); on the right, the status line in the display band, Undo, Clear and Swing in the chip row, and in the dial band Voice, the Function buttons (two rows of six, 54 px each, as "open hh" needs), Seed, then the active function's settings (up to three). Three rows of four buttons would make the device 836 px wide. The kit page keeps stab's three bands (display, chips and buttons, dials): the selected voice on the left, the mixer on the right. The build fails if anything shown at the same time overlaps.
- Displays are drawn in Cozette with the 2sl-ui tokens, light or dark to follow Live's theme.
- Live's controls are recoloured from the same tokens.
- Every control and display has Info View text.

## Source

The patch is generated. Edit these, then run `python3 src/2sl-drums.py` (it needs `references/drums/mirror/patterns/grids_*.cc`, from `references/drums/mirror_patterns.sh`, and libduktape for reading the function registry):

- `src/2sl-drums-functions.js`: the functions, their settings and Info text (the registry), and the helpers they share. It becomes part of `2sl-drums.js`.
- `src/2sl-drums.py`: voices, canned kits, Info text, layout, the Init values (BASE).
- `src/2sl-drums-presets.json`: the presets.
- `src/2sl_drums_dsp.py`: the gen~ voices (GenExpr) and the mixer's gates.
- `src/2sl-drums-brain.template.js`: the engine (Voice / Function / Seed and the settings, applied live, commits, Undo, the history, the echoes of the dials it sets, playback, storage). It becomes `2sl-drums.js`, with the functions, the kit's clock and the data.
- `src/2sl-drums-view.template.js`: the displays, inserted into the kit's view template.
- The kit: `src/2sl_kit.py`, `src/2sl-kit-ui.template.js`, `src/2sl-kit-view.template.js`, `src/2sl-kit-clock.template.js`.

Checks:

- `node tests/2sl-drums.test.js`: every function against its sources, purity, the registry against the Live parameters, the variants (the round trip Seed → settings → Seed, neighbours one step apart, the orders and counts), the live application, commits on Voice and Function, Clear, picking a row by its name, Undo and the history and its limit, the echoes of the dials (at once and late), all and single rows, open hh's rows, the hand edit, storage round trips, playback velocities, swing timing, the clock, MIDI, the mixer's wiring, the Voice and Function groups, loud failures, the UI script and every display, and that no message the patch sends a script collides with one of its function names.
- `python3 tests/test_2sl_kit.py`: the kit's layout check, groups (by a live.tab or any control), dial types, controls kept out of presets.
- `python3 tools/es5check.py devices/2sl-drums/*.js`: ES5 syntax, which is what Max's js needs.
- The build checks the gen~ code with `tools/genexpr.py`, our GenExpr subset checker; `python3 tools/test_genexpr.py` tests the checker itself, including against 2sl stab's gen~ code.
- `python3 tools/render_drums.py`: renders the presets to `dist/renders/*.wav` and prints the loudness table.

## Credits

By [2sl](https://2sl.to). Grids pattern data: Emilie Gillet, Mutable Instruments (GPLv3). Font: [Cozette](https://github.com/slavfox/Cozette) by slavfox (MIT).

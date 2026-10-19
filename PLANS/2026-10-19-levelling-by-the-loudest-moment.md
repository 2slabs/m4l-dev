# 2026-10-19: presets levelled by their loudest moment; gate's strike, stab's headroom, the players' phases

From the 2026-10-19 gain-staging diagnosis (Graham: do all of these).

1. Kit: `bs1770.max_momentary_loudness` (EBU Tech 3341, references/ebu-tech-3341.md) shares the K-weighting with
   `integrated_loudness`; `preset_loudness.phrase_measures` is the one levelling measure, `presets_over_the_clip` the
   one clip check, `LOUDNESS_TOLERANCE_LU` 1.0; `oscillator_start_phases` + `GenProgram.set_history` for the players.
2. 2sl gate 0.3.13: the strike spans the LED driver's current range log-linearly; `LEVEL_MODE_DRIVE` goes; the level
   mode's residual explained from the 292's divider; presets re-levelled on the kit's measure.
3. 2sl stab: the player's voices at seeded free-running phases; then the output's x2 goes (6 dB of headroom),
   `HELD_BY_THE_CLIP` empties; presets re-levelled.
4. 2sl filter: presets re-levelled on the kit's measure.
Each a push; trims before/after reported per device.

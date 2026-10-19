# 2026-10-18: the chord block, the seeded random, and three kit gaps (refactor level 3)

## Why
- 2sl stab and 2sl gate each carry their own chord handling (shapes, In key from Live's Scale Mode, naming, the
  chord display). The user: "the chord block i think is shared code and should be treated as such".
- Randomness: one seeded generator per device, Seed and Loop on the panel; "anything that uses randomness would use
  this". A plain sequential generator: every draw is `randomNext()`; Loop resets it to Seed at Loop boundaries of
  the song position while Live plays, and at transport start.
- 2sl gate hit three kit gaps (its SHORTCUTS.md, 2026-10-18): the header names the output level "Volume", `tabs()`
  takes no visibility, the label-width rule lives in the device.

## Steps
1. `m4l_dev/seeded_random.py` + `templates/seeded-random.template.js`: `SeededRandom` (Python: Seed and Loop
   controls, Info text, wiring; JS: mulberry32, the device's generator, Loop and transport resets).
2. `m4l_dev/chord_block.py` + `templates/chord-block.template.js` + `templates/chord-display.template.js`: the chord
   shapes (one table, fitted to a device's note budget at build time), In key, held keys, naming, voicing drift (on
   the seeded random), the display.
3. `patch_builder.py`: `header(output_level_target, output_level_name, ...)`; `tabs(..., visibility=)`; the page
   tabs made by `tabs()`; the label-width check in `check()`.
4. `layout_rules.py`: the Live-text width rule (5.5 px a character: no source for Live's font metrics; the
   SHORTCUTS entry moves here), dial / menu / toggle / tabs widths, `on_grid`.
5. Fixture, tests (Python and node), architecture/ (overview, chord-block.md, seeded-random.md, layout in
   overview), README.
6. Commit, push; then each device bumps the submodule, rewires, rebuilds, tests, pushes.

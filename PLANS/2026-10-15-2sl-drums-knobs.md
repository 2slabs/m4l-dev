# 2sl drums: three-knob pattern page (2026-10-15)

Supersedes the Run / multi-select parts of 2sl-drums-functions.md (user, 2026-10-15). The function model
(pure generators and modifiers from one registry, a history with Undo) stays.

## The knobs ("a dream hardware setup": every one MIDI-mappable)
- voice: one row, or "all" (the last position). No multi-select.
- function: the generator or modifier. Only the active function's panel is shown.
- seed: walks the function's variants, applied live, no Run. Run is gone.
- the active function's setting knobs stay, and are the same state as seed: the variants are every
  combination of the settings in one list (mixed radix), ordered so neighbours sound alike, the finest
  setting changing fastest (shift: steps; euclid: rotation, then hits; random: its seed number). Turning
  seed moves the setting knobs; turning a setting knob moves seed. Seed explores a local area; the
  setting knobs hop to another.

## Base and history
- When you start turning seed or a setting, the target row(s) as they are become the base; the shown row
  is f(base, position) and changes live, the starting position too (corrected 2026-10-15: touching any
  knob applies the function, so e.g. canned kit 3 can be put on sd). The base itself comes back by Undo
  (drops what isn't committed) or by a modifier's settings that change nothing.
- Moving the voice or function knob commits the current result as one history step, and it becomes the
  next base. Undo steps back through commits (and hand edits).
- Hand edits (clicking steps) still work, as a modifier step.

## "all" and single rows
- On "all", generators make the whole kit (canned, grids) and modifiers act on every row.
- open hh on a single row: reads ch, writes oh (on oh or all).

Automation of seed and the settings is fine although their meaning follows the function (user).

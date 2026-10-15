# 2sl drums: functions redesign (2026-10-15)

Refactor level 3 (user, 2026-10-15): the pattern engine and pages are rewritten around this.

**Partly superseded (user, 2026-10-15) by PLANS/2026-10-15-2sl-drums-knobs.md**, built in 0.3.0: Run, the row
selection (multi-select) and the all-functions-visible panel are gone; the parts marked SUPERSEDED below no longer
hold. The function model (pure generators and modifiers, a hand edit as a modifier, the history with Undo), the
first functions and the kit page stay.

## Model (user's words: "modifiers take the pattern at t and give you t+1, generators just give you
the pattern at t+1")
- generator(params) -> pattern; modifier(pattern, params) -> pattern. Pure functions.
- A hand edit (clicking a step) is one more modifier.
- The device keeps the history p0..pt. Undo steps back.
- SUPERSEDED: Run applies the ONE selected function to the selected rows only (other rows pass
  through) and appends p(t+1). (Now: Voice / Function / Seed, applied live; Voice or Function commits.)
- SUPERSEDED: Rows: click a row's name to select it; shift-click selects several. (Now: Voice.)

## Pages
- SUPERSEDED (now only the active function's dials show): pattern: the grid of every voice on the left;
  on the right, EVERY function visible at once, each
  with its own parameters (one Live parameter per setting, never shared relabelled knobs; number
  boxes so they fit); one function lit at a time; Run, Undo.
  Wider than 960 px is fine; if it gets too long, a pop-out window is the fallback (it may hide
  behind Live: test on the user's machine).
- kit: buttons to pick a voice -> that voice's synth controls; a mixer of every voice beside it.

## First functions
- Generators: canned (the sourced patterns, a voice's row from a style's kit), grids, euclid,
  random.
- Modifiers: shift, reverse, thin, ghosts, fill, open hats, accent.

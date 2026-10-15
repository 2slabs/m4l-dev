# 2sl drums intermediate build (2026-10-15)

Small plan for the first build; the main plan is 2026-10-15-2sl-drums.md.

1. Kit: `src/2sl_kit.py` (DevicePatchBuilder) + `src/2sl-kit-ui/view/clock.template.js`, from stab's fix branch. Done.
2. Pattern engine `src/2sl-drums-brain.template.js`: grades -> Grids levels, density threshold, per-pass
   perturbation, fills, 909 shuffle, styles (canned / euclid / grids), lock, reroll, storage. Done, node tests.
3. Voices `src/2sl_drums_dsp.py` (BD SD RS CP CH/OH RD), checked + rendered with `tools/genexpr.py`. Done.
4. Pages, displays, presets (volume matched offline), README. Done.
Next (not in this build): toms and crash; flam; per-voice density; open questions in the main plan's "Open".

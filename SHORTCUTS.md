# Shortcuts

- 2026-10-15: `src/2sl_kit.py` and the kit JS templates are copied from `src/2sl-stab.py` and stab's
  templates, so the helpers exist twice. The user allowed this to stay past 24 h while someone else
  works on stab; when that lands, rebuild stab on the kit and delete its copies.
- 2026-10-15: the kit (`src/2sl_kit.py`, `src/2sl-kit-*.template.js`) is taken from 2sl stab as it is on
  `origin/fix/stab-step-storage` (Info View text, loud failures, 16-bit stored steps, BASE checks), which is newer
  than the stab in this worktree. When stab is folded onto the kit, start from that branch.
- 2026-10-15: 2sl drums' preset Volumes, voice balance (hats +8 dB, clap -4 dB) and the kit's x0.4 headroom were
  set from offline renders with our own GenExpr subset (`tools/genexpr.py`, `tools/render_drums.py`; since 0.2.0
  every preset plays the Init pattern), not measured in Max/Live. Proper: measure in Live (2sl meter) and correct.
- 2026-10-15: 2sl drums' voice displays redraw the DSP's envelope formulas in JS (`src/2sl-drums-view.template.js`
  repeats constants from `src/2sl_drums_dsp.py`: decay times, the BD sweep, clap spacing). Two copies that can
  drift. Proper: generate both from one table of voice constants in the generator.
- 2026-10-15: 2sl drums' step triggers come from [js] (the low-priority thread), like 2sl stab's machine; only the
  swing delay is sample-accurate (in gen~). Proper, if Live shows jitter: sequence in gen~ from Live's beat phase.
- 2026-10-15: 2sl drums' brain changes the pattern playing in place when a stored step value arrives after `ready`
  that differs from it (only Live's own undo of the hidden parameters could send one), instead of making it a
  history step. Proper, if Live does send them: treat it as a step ("from Live's undo") or keep the hidden
  parameters out of Live's undo.

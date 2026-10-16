# Shortcuts

Things done the quick way, to come back to. Each with when it was taken.

- 2026-10-15: 2sl drums' preset Volumes, voice balance (hats +8 dB, clap -4 dB) and the kit's x0.4 headroom were
  set from offline renders with our own GenExpr subset (`tools/genexpr.py`, `tools/render_drums.py`; since 0.2.0
  every preset plays the Init pattern), not measured in Max/Live. Proper: measure in Live (2sl meter) and correct.
- 2026-10-15: 2sl drums' voice displays redraw the DSP's envelope formulas in JS (`src/2sl-drums-view.template.js`
  repeats constants from `src/2sl_drums_dsp.py`: decay times, the BD sweep, clap spacing). Two copies that can
  drift. Proper: generate both from one table of voice constants in the generator.
- 2026-10-15: 2sl drums' step triggers come from [js] (the low-priority thread), like 2sl stab's machine; only the
  swing delay is sample-accurate (in gen~). Proper, if Live shows jitter: sequence in gen~ from Live's beat phase.
- 2026-10-15: 2sl drums' brain changes the pattern in place when a stored step value arrives after `ready` that
  differs from what plays (only Live's own undo of the hidden parameters could send one): it commits what is being
  turned, then changes the committed pattern, instead of making it a history step. Proper, if Live does send them:
  treat it as a step ("from Live's undo") or keep the hidden parameters out of Live's undo.
- 2026-10-15: 2sl drums stores the pattern playing in its 14 hidden parameters on every turn of Seed or a setting
  (so a set saved mid-turn keeps what you hear), which may flood Live's undo history with hidden-parameter steps.
  Proper, if Live shows it: store on commit and on Live's save only, or keep the hidden parameters out of undo.
- 2026-10-16: 2sl drums, 2sl meter, hello-gain and the fader calibration still live here (`src/`, `devices/`,
  `tools/render_drums.py`, `tools/drums_hits.js`, `tests/2sl-drums.test.js`) and no longer build: `src/2sl-drums.py`
  imports the old `2sl_kit`, `tools/render_drums.py` the old `tools/genexpr.py`, and the kit now builds only from a
  device repository with this repo as its submodule. Proper: move each to its own repository on the kit (drums next).
- 2026-10-16: the frozen device's file dates (mdat) are a fixed 2026-01-01 (`m4l_dev/amxd.py`), so freezing is
  repeatable. No source says how Max uses mdat. Proper: find out (a frozen device with an old date vs. a newer file of
  the same name in Max's search path) and pick on evidence.
- 2026-10-16: the live.tab button rule (`m4l_dev/layout_rules.py`: 6 px a character + 1) is calibrated from one case
  that ships and looks right in Live (2sl stab's Sub Mode, "-2 pls" in 37 px), not from Live's font metrics. Proper:
  measure live.tab's text width in Live.
- 2026-10-16: libduktape is found by trying fixed paths (`m4l_dev/es5.py`: Homebrew's two prefixes, Debian's soname,
  `brew --prefix`), since Homebrew ships only libduktape.so and ctypes.util.find_library misses it on macOS.
- 2026-10-16: the Live preset writer knows only a Max Instrument with float and enum parameters (the one example Live
  wrote). An audio or MIDI effect, or an Int parameter, fails the build. Proper: save a preset of each from Live into
  references/ableton/ and teach the writer their form.
- 2026-10-16: a device without a Preset menu still gets the UI script's Preset-menu code (`PRESETS = []`, msg_int, which
  then only errors). Proper, if it matters: leave the code out when there is no menu.
- 2026-10-16: three kit-wide choices 2sl drums will see when it is ported, from 2sl stab: the page switch is Hidden
  (not saved, not automatable), every live.text names its states off / on in Live (automation / automationon), and the
  page tabs start 12 px after the link chip (drums had 8). Each changes drums' Live parameters or layout: confirm with
  the user when porting.


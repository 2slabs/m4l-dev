# Shortcuts

Things done the quick way, to come back to. Each with when it was taken.

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
  references/ableton/ and teach the writer their form. 2026-10-18: a Max Audio Effect is taught (from a preset Live
  saved, for 2sl filter); the same file holds an Int parameter's form, not taught yet. A MIDI effect is still unseen.
- 2026-10-16: a device without a Preset menu still gets the UI script's Preset-menu code (`PRESETS = []`, msg_int, which
  then only errors). Proper, if it matters: leave the code out when there is no menu.
- 2026-10-18: how wide a live.dial / live.menu / live.text must be for its text (`m4l_dev/layout_rules.py`:
  `LIVE_TEXT_PIXELS_PER_CHARACTER` = 5.5) is calibrated from one observation (2sl gate v0.5's 8-character dial names
  in 44 px dials, played in Live), not from Live's font metrics, which no source gives (references/README.md, "Live's
  control font"). Moved here from 2sl gate. Proper: measure Live's dial / menu / toggle text in Live (a screenshot of
  known strings at known widths), or find the font and its metrics.
- 2026-10-20: the Moog transistor ladder module's Emphasis runs the circuit's law (k 4 at 7.5 by the Regen Cal) on an
  UNVERIFIED pot curve: `emphasis_pot_audio_taper_at_half_rotation` 0.10, the common 10 %-at-half audio convention
  mirrored (references/circuits/moog-transistor-ladder.md §7), not the 50k REV AUD part's (no datasheet, no measured
  unit). It sets k(10) (7.76 here; 4 to 15 over all curves) and how fast k rises toward 7.5. Proper: the part's
  datasheet or a measured unit's pot, the default from it.
- 2026-10-19: the LTC1060 / MF10 section's Q enhancement (`m4l_dev/circuit_modules/ltc1060_mf10_section.py`) is fitted
  to the LTC1060 datasheet's one stated number (50:1, mode 1, +-7.5 V, 1.4 MHz: Q 5 about 8 % high) with an
  excess-phase law; the Sherman's mode (probably 3, "slower") at 100:1 is unmeasured, and the datasheet's graphs (Q
  error vs clock) aren't read. Proper: read the graphs through an extractor, or measure a chip. Moved here from 2sl
  filter.
- 2026-10-19: above one clock tick a host sample (centres over 441 Hz at 44.1 kHz, 100:1) the LTC1060 / MF10 section's
  rails act once a host sample, not once a tick (the block steps the ticks in closed form). Only matters in
  self-oscillation at high cutoffs (its level, a little). Proper, if it matters: GenExpr loops (Max has them; the kit
  renderer doesn't). Moved here from 2sl filter.

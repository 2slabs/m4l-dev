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

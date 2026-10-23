# Shortcuts

Things done the quick way, to come back to. Each with when it was taken.

- 2026-10-16: the frozen device's file dates (mdat) are a fixed 2026-01-01 (`twosl_dsp/amxd.py`), so freezing is
  repeatable. No source says how Max uses mdat. Proper: find out (a frozen device with an old date vs. a newer file of
  the same name in Max's search path) and pick on evidence.
- 2026-10-16: the live.tab button rule (`twosl_dsp/layout_rules.py`: 6 px a character + 1) is calibrated from one case
  that ships and looks right in Live (2sl stab's Sub Mode, "-2 pls" in 37 px), not from Live's font metrics. Proper:
  measure live.tab's text width in Live.
- 2026-10-16: libduktape is found by trying fixed paths (`twosl_dsp/es5.py`: Homebrew's two prefixes, Debian's soname,
  `brew --prefix`), since Homebrew ships only libduktape.so and ctypes.util.find_library misses it on macOS.
- 2026-10-16: the Live preset writer knows only a Max Instrument with float and enum parameters (the one example Live
  wrote). An audio or MIDI effect, or an Int parameter, fails the build. Proper: save a preset of each from Live into
  references/ableton/ and teach the writer their form. 2026-10-18: a Max Audio Effect is taught (from a preset Live
  saved, for 2sl filter); the same file holds an Int parameter's form, not taught yet. A MIDI effect is still unseen.
- 2026-10-16: a device without a Preset menu still gets the UI script's Preset-menu code (`PRESETS = []`, msg_int, which
  then only errors). Proper, if it matters: leave the code out when there is no menu.
- 2026-10-18 (re-done 2026-10-21): how wide a Live control must be for its text (`twosl_dsp/layout_rules.py`) is
  measured with a stand-in font (Liberation Sans at 11 px, `LIVE_FONT_ADVANCES`, the size calibrated from one
  observation: 2sl gate v0.5's 8-character dial names in 44 px dials, played in Live), not Live's own font, whose
  metrics no source gives (references/README.md, "Live's control font"). Since 2026-10-21 per character with padding
  (renders showed touching labels), so "Symmetry" now measures over 44 px though Live showed it fitting: the stand-in
  is wider than Live there. Proper: measure Live's dial / menu / toggle / tab text in Live (a screenshot of known
  strings at known widths), or find the font and its metrics, and replace the table.
- 2026-10-22: the text a dial or number box shows for its value (`layout_rules.live_value_text`, what the overlap rule
  measures and render_pages.py draws) is a stand-in for Live's formatting: three figures with ms / s, Hz / kHz, dB to
  a tenth, an Int whole. The live.dial reference names the unit styles but gives no format. Proper: values of each
  unit style read off Live (a screenshot), the formats from them.
- 2026-10-20: the Moog transistor ladder module's Emphasis runs the circuit's law (k 4 at 7.5 by the Regen Cal) on an
  UNVERIFIED pot curve: `emphasis_pot_audio_taper_at_half_rotation` 0.10, the common 10 %-at-half audio convention
  mirrored (references/circuits/moog-transistor-ladder.md §7), not the 50k REV AUD part's (no datasheet, no measured
  unit). It sets k(10) (7.76 here; 4 to 15 over all curves) and how fast k rises toward 7.5. Proper: the part's
  datasheet or a measured unit's pot, the default from it.

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
- 2026-10-19: above one clock tick a host sample (centres over 441 Hz at 44.1 kHz, 100:1) the LTC1060 / MF10 section's
  rails act once a host sample, not once a tick (the block steps the ticks in closed form). Moved here from 2sl filter.
  2026-10-20, measured: IT MATTERS. Self-oscillation from a kick, BP pin, damping -0.08 (2sl filter's filter 2 at full
  Reso), -0.2 (the floor) and 0.008 (its filter 1, oscillating above ~11 kHz), the module at 44.1 / 48 kHz against
  itself at 64 x 44.1 kHz, where each tick has its own sample (converged: 128 x reads the same to 0.01 dB, 0.1 cent).
  The reference sits at -0.6 to -0.9 dB of full scale at every centre; the host-rate section is louder, more so as
  the centre rises: +0.25 dB at 1 kHz, +0.5 at 2 kHz, +0.75 to +0.85 at 4 kHz, +1.1 to +1.2 at 8 kHz, +1.3 to +1.9 at
  16 to 20 kHz, +5.9 at 22 kHz; and sharp: 4 to 17 cents at 4 kHz, 9 to 41 at 8 kHz. Worse, it LOCKS to the host
  rate's fractions: at 48 kHz every centre from 11.7 to 12.3 kHz oscillates at exactly 12 kHz (fs / 4), 3.3 to 3.6 dB
  loud, up to 57 cents off (a self-oscillating sweep stalls there); at 44.1 kHz the centres near 22 kHz sit at
  22.05 kHz. The harmonics' shape holds (the 3rd within 0.6 dB; even harmonics -55 dB and lower where the reference
  has none). A loud input driven into the rails is the same mechanism, not measured. Proper: step each tick with its
  rails in a GenExpr loop (Max's gen~ has for / while; the kit's renderer, m4l_dev/genexpr.py, must learn them
  first), at least while the section is near or past oscillation.

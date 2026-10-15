# Shortcuts

Things done the quick way, to come back to. Each with when it was taken.

- **2026-10-15 — 2sl stab, LFO display history at the current rate.** The LFO display reads the LFO's real
  phase (snapshot~ every 33 ms) but draws the last two seconds by running that phase back at the *current*
  rate, so for two seconds after a Rate change the past is drawn at the new rate. Proper: keep the phase
  readings with their times and draw the history from them.
- **2026-10-15 — 2sl stab, frozen echo display ignores the loop filters.** Frozen, the display grows each
  repeat through tanh(1.05 x 1.1 a) / 1.1, the loop's feedback and saturation without its low-pass,
  high-pass and allpasses. The port of the loop (freeze_sim) swells slower (about x1.027 a time round at
  Dub 50 on a chord, vs x1.05 drawn), and how much slower depends on the sound. Proper: measure the loop
  gain per round from the audio (e.g. the level line's growth) and draw that.

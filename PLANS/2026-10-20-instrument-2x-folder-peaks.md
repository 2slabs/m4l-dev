# 2026-10-20: do the instruments' 2x 259 folders peak like the tanh saturator did?

Question (from PLANS/2026-10-20-tanh-saturator-peaks.md, "Open"): 2sl gate and 2sl drums' new voice run the 259
principal oscillator + timbre section (second-order ADAA folder, its 2x equaliser: +15.9 dB at the 2x Nyquist) at 2x
and bring it down themselves. Does the downsampler's phase ring the folded tone past the band-limited ideal, as the
elliptic half-band did to the 2x tanh saturator (2.85 against the ideal 1.78)? And is the elliptic phase audible on a
folded tone?

What each instrument actually runs (read before predicting, 2sl-gate 1cf000b, 2sl-drums 4bde47b):
- drums (`src/drum_synth_voice.py`): the tone section's oscillators run at 2x natively; `HalfbandDownsampler`
  ("tone_down", the kit's elliptic HIIR) brings it down. The elliptic upsamplers are on the FM / ring partners only.
  No tone filter. Fold 0-10 V at any pitch (10 Hz-20 kHz), output / min(slope x drive, 3.2 V), then the strip's tanh.
- gate (`src/gate_dsp.py`): NOT the kit's elliptic pair. Its own 19-tap Blackman half-band FIR (linear phase, 9
  steps), then the 259's 1.33 kHz tone filter (`TONE_FILTER_HZ`). Fold is held under `samplerate x 0.3 / f`
  (10 V up to 1.44 kHz at 48 kHz, 4.6 V at 3.1 kHz).

Method (scratchpad numpy model, checked against the kit's GenExpr renderer of the timbre section to 1e-9 first): a
pure sine at 2x 48 kHz -> the folder bus (drive x the drive stage's gain) -> eq. 15 on the pieces -> the 2x
equaliser (order 2) -> each downsampler: the kit's elliptic `HalfbandDownsampler`, the kit's
`HalfbandLinearPhaseDownsampler`, gate's 19-tap FIR. The ideal: the folder's transfer on the sine at 16x 48 kHz,
a linear-phase low-pass at 20 kHz, taken at 48 kHz. Peaks of the steady tone; peak / the ideal's peak. Settings:
4 V and 8 V (and 10 V, the maximum) at 110, 410, 1370, 3100 Hz; drums also 5 kHz at 8 / 10 V; gate only where its
ceiling allows. The phase: the elliptic downsampler's group delay at 48 kHz from 100 Hz to 20 kHz (samples, ms).

Hypotheses and predictions (written before measuring):

- H1 (mechanism the same, size smaller): a folded sine is periodic, its harmonics fall off about 1/n^2 past the
  folds (corners, no jumps), so far less energy sits in the elliptic's corner (0.21-0.29 of the 2x rate) than hot
  noise's tanh (a telegraph wave, 1/n). Prediction: through the elliptic, peak / ideal 1.00-1.08 at 110 and 410 Hz,
  up to 1.15 at 1370 / 3100 Hz at 8-10 V; through the linear-phase FIR within 0.97-1.05 of the ideal everywhere.
- H2 (the equaliser): the +15.9 dB lift sits above 0.25 of the 2x rate, mostly in the stop band; its share of any
  excess is under a third (as for the saturator, 15 %).
- H3 (gate is safe by construction): gate's FIR is linear phase, so its peak / ideal is within 0.95-1.05 (its pass
  band rolls off before 20 kHz, so maybe a little under). After its 1.33 kHz tone filter the question is moot.
- H4 (phase audibility): the elliptic downsampler's group delay is flat (about 1.5 samples) to ~Fs/20 and rises near
  its corner. Prediction at 48 kHz: spread 100 Hz -> 10 kHz under 1 sample (21 us), -> 16 kHz under 3 samples, -> 20
  kHz under 15 samples (0.3 ms). Published thresholds for group-delay distortion are of the order of 1 ms or more
  (Blauert & Laws 1978, from memory: not in references/), so: inaudible, and the waveform shape a listener hears is
  the ideal's up to the top octave's harmonics being a few samples late.

Decision rule: switch an instrument to the linear-phase downsampler only if the elliptic's peak / ideal is above 1.1
at a setting it reaches, or the group delay spread under 16 kHz is above 0.5 ms.

## Results

Model check: the renderer's raw mean = eq. 15 exactly on its bus (1e-9); the numpy transfer = `output_volts` (1e-9).
The 2x stream is the kit's own GenExpr rendered; the downsamplers numpy (the kit's coefficients and taps; the test
below renders both through the kit). Scratchpad scripts (folder-peaks-measure/: measure.py, measure2.py, sweep.py,
gate_alias.py), 48 kHz, steady tone, DC taken off (10 V reaches cell 1's one-sided floor).

The ideal had to change. "16x, low-passed at 20 kHz" (as for the saturator) cuts harmonics the tone really has
between 20 and 24 kHz, which both downsamplers pass: at 4 V, 3.1 kHz its 7th (21.7 kHz) alone doubles the peak, so
every chain read 2.3-2.5x it. The ideal used: the folded tone's harmonics below 24 kHz (the base Nyquist), flat, their
own phases (`ideal24`, from the transfer over one period, exact). A second reference, per chain: its own fitted
harmonic magnitudes on the true phases, so peak / that is the phase alone.

Sweep: drives 4 / 8 / 10 V, every semitone 55 Hz-7 kHz (255 cases), peak / ideal24, worst per band (at):

| drive, notes | elliptic | linear phase (kit) | gate's 19-tap FIR | elliptic, no equaliser | linear, no equaliser | elliptic / linear |
|---|---|---|---|---|---|---|
| 4 V, 55-440 Hz | 1.06 | 1.04 | 1.04 | 1.00 | 1.00 | 1.02 |
| 4 V, 440-1760 Hz | 1.81 (1760) | 1.37 | 1.30 | 1.27 | 1.00 | 1.32 |
| 4 V, 1.76-7 kHz | 2.03 (2637) | 1.67 | 1.82 | 1.37 | 1.33 | 1.66 |
| 8 V, 55-440 Hz | 1.23 (370) | 1.05 | 1.06 | 1.09 | 1.01 | 1.19 |
| 8 V, 440-1760 Hz | 2.36 (988) | 1.35 | 1.31 | 1.63 | 0.99 | 1.74 |
| 8 V, 1.76-7 kHz | 1.55 | 1.54 | 1.43 | 1.28 | 1.20 | 1.34 |
| 10 V, 55-440 Hz | 1.16 (294) | 1.04 | 1.04 | 1.06 | 1.00 | 1.12 |
| 10 V, 440-1760 Hz | 1.89 (784) | 1.29 | 1.20 | 1.38 | 1.01 | 1.54 |
| 10 V, 1.76-7 kHz | 1.58 | 1.35 | 1.36 | 1.24 | 1.04 | 1.44 |

Absolute (volts, the drums divide by 3.2): 10 V at 784 Hz elliptic 8.45, linear 5.49, ideal 4.46; 8 V at 988 Hz
7.08, 4.06, 3.00. Phase alone (own magnitudes on true phases, non-coherent notes): elliptic x0.72-1.77 (10 V 1370 Hz
x1.45, 4.65 V 3.1 kHz x1.77), linear phase and gate's FIR x0.99-1.01. Medians over the sweep: elliptic 1.02-1.07, linear
1.05: the excess is at certain notes, not everywhere.

- H1 refuted in size: the elliptic reaches 1.8-2.4x the ideal at notes 0.4-2.6 kHz (predicted <= 1.15); its phase
  alone up to 1.77x. Under 440 Hz it is 1.06-1.23x. The linear-phase FIR is 0.99-1.01x on phase, but its peaks reach
  1.35-1.67x the ideal anyway.
- H2 refuted: the equaliser is not the minor share. Without it the linear chain is 0.99-1.01x below 1.8 kHz; with it
  up to 1.37x. The equaliser lifts the raw stream +5.8 dB at 20 kHz, +8.2 at 24, +10.4 at 28 (+15.9 at the 2x
  Nyquist): on small signals that only restores the kernel (product -1.4 dB at 24 kHz, -5.5 at 28), but it lifts the
  ADAA's residual aliases at the 2x rate by as much, and the half-band's transition band (0.21-0.29 of the 2x rate,
  -6 dB at 24 kHz) passes 20-24 kHz and folds part of 24-28 kHz there. Which of the two (restored harmonics near 24
  kHz, lifted residual aliases) carries the excess: unmeasured. Content at 20-24 kHz: inaudible, real headroom.
- H3 holds for phase (gate's FIR x0.99-1.01 on phase; peak / ideal24 worst 1.82 at 4 V 3.5 kHz within its ceiling,
  1.53 after its tone filter, same mechanism as H2). New: its stop band is weak (-15.7 dB at 28 kHz, -46.5 at 33.6 kHz
  at 96 kHz), so the folder's harmonics at 24-34 kHz alias: worst alias line below 20 kHz re the fundamental, gate FIR
  / kit linear phase (= elliptic): 8 V 1370 Hz -8.4 / -44.7 dB (after the tone filter -26.1 / -61.3, at 19.2 kHz),
  10 V 1370 Hz -17.8 / -53.8, 10 V 790 Hz -37.8 / -57.4, 4 V 3.1 kHz -32.5 / -31.8 (the folder's own aliases).
- H4 holds: the elliptic downsampler's group delay at 48 kHz is 1.78 samples (37 us) to 2 kHz, 2.21 at 10 kHz, 3.34 at
  16 kHz, 4.19 at 18 kHz, 5.77 at 20 kHz (120 us): spread 0.43 samples (9 us) to 10 kHz, 1.55 (32 us) to 16 kHz, 4.0
  (83 us) to 20 kHz. The peaks it adds come from harmonics above ~10 kHz moved tens of microseconds; the shape under
  10 kHz is the ideal's to 9 us. [UNVERIFIED: no group-delay audibility threshold is in references/; the ones
  remembered (Blauert & Laws 1978, about 1 ms and more) are 10-30x these.] So the elliptic is not audible as phase on
  the folded tone; it matters as headroom and as what a saturator after it sees.

Recommendation:
- 2sl drums' voice (elliptic `tone_down`): switch to `HalfbandLinearPhaseDownsampler`. Its strip's tanh follows the
  tone, so a 1.5-1.7x peak from phase alone changes how hard the strip clips (10 V at 784 Hz: 2.64 -> 1.72 into the
  strip at Level 1). Cost: the tone section 5.57 -> about 21.5 samples late (5 steps / 2 + 20 re `first`, the FM / ring
  partners' elliptic upsampler still 1.78 on their paths: the path alignment must be re-derived from the blocks'
  `latency_samples`, not HALFBAND_ROUND_TRIP_LATENCY_SAMPLES), +16 samples (0.33 ms) on a hit; CPU about +45 ns a host
  sample a voice (the saturator's measured cost of the same swap), about 0.3 us for 7 voices.
- 2sl gate: keep its FIR's linear phase (no elliptic in its path; the elliptic would add up to 1.8x). Separately, its
  19-tap FIR aliases the folder's top band at -8 to -38 dB below 20 kHz at hot folds; the kit's 83-tap
  `HalfbandLinearPhaseDownsampler` takes that to -45 to -57 dB. A switch moves its centre from 9 steps to 39 steps
  re the second sample (+15 samples: note-on latency 8 -> 23 samples), and gate must take that from the block (its
  `latency_samples`) into VOICE_LATENCY_STEPS, as it reads the 259's; CPU one FIR on the voices' sum (+45 ns).
- Open (kit): the equaliser-related excess (H2) is in every 2x ADAA2 chain here, up to 1.67x the ideal through the
  linear phase. First split it (restored 20-24 kHz harmonics vs lifted residual aliases); candidates then: a
  downsampler that stops by 24 kHz (not a half-band), or an equaliser that falls after 20 kHz. Unmeasured.

Kept as a test: tests/test_circuit_module_buchla_259_timbre_section.py,
`test_a_hot_fold_at_2x_peaks_past_the_ideal_through_the_elliptic_downsampler` (the renderer, both kit downsamplers,
the ideal).

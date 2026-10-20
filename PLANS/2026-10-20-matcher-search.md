# 2026-10-20: why the matcher recovers the toy voice (85 %) and not the 2sl drums voice (10 %)

The matcher is the drums engine's acceptance test (PLANS/2026-10-19-patch-matcher.md). On the drums' synth voice
(2sl-drums src/drum_synth_voice.py, MATCHED_DRUM_SYNTH_VOICE, 31 searched parameters) it recovers 2 / 20 random known
settings (found <= truth's own score + 0.25), median found 5.7 vs truth 0.0; switches fixed at the truth: no better;
4x the renders: one target 6.5 -> 4.8; ~2.5 min a match on 6 cores. Target: >= 75 % on the drums voice in reasonable
time, the toy voice kept >= 85 %.

Method: scientific method + binary search. Each hypothesis has its numeric prediction written here BEFORE its test runs;
results are added under it. Targets: the drums recovery test's own (seeded draws "drum synth voice recovery/N" over the
unit cube, target noise seed 777). Measured on a snapshot of drum_synth_voice.py (2sl-drums 94e5053) against this kit.

Already measured before the tests (target 0..19, truth's score with the search's noise): 12 / 20 targets score exactly
0.00 (the metal noise source is an unseeded shift register, so with it the voice is noise-free); the rest 0.2 .. 3.6.
A render + score is ~40 ms.

## H1. Dimensionality: recovery breaks as k grows, and where it breaks names parameters

Free k parameters (a seeded random subset), the rest at the truth, the matcher's default settings, 6 targets per k.
Prediction: k = 2: >= 90 %; k = 4: >= 80 %; k = 8: ~60 %; k = 16: ~30 %; k = 31: ~10 % (the known result). The misses at
k <= 4 contain one of {noise_pattern, noise_tune_hz, pitch_mod_rate_hz, tone_pitch_hz} in >= 75 % of cases: those are
the parameters whose score landscape I expect is not smooth (an LFSR pattern is a 255-way lookup with no order; the
metal clock and a cyclic pitch modulation's rate alias / beat; pitch has octave minima).

## H2. Landscape: 1-D slices around the truth

For each parameter, 1-D slices of the score through the truth (all others at the truth), 8 targets, 101 points over its
unit axis. Measure per slice: the number of local minima deeper than 0.25 under their neighbourhood ("rugged"), and
whether the truth's basin is the global minimum. Prediction: noise_pattern is rugged (>= 10 local minima a slice
whenever the metal source is audible); noise_tune_hz >= 3; pitch_mod_rate_hz >= 3 for the cyclic shapes; every other
continuous parameter <= 2 (smooth); inactive parameters (a level at 0) give flat slices (score change < 0.05 over the
whole axis) in >= 30 % of (parameter, target) pairs.

## H3. Search

If H1/H2 show smooth landscapes but recovery still fails at k = 31, the search is short: CMA-ES's population (default
4 + 3 ln 31 = 14) is too small for a 31-dimensional multimodal problem; prediction then: IPOP to larger populations with
the same total budget lifts recovery to >= 40 %. If H2 shows a few rugged parameters, prediction: searching those by
their own discrete / grid step (or a staged search) does more than any CMA-ES setting.

## H4. Score

The truth scores clearly better than its neighbours: at 0.05 unit off on any one audible parameter the score rises
>= 0.25 for >= 80 % of (parameter, target) pairs where the parameter is audible. If not, the recovery margin is not the
problem; the score cannot see the parameter.

## Results

### Interim (2026-10-20, before H5): H2 and a basin measurement point at the pitch term

- H2 (1-D slices, 8 targets x 31 parameters x 101 points): local minima (0.25 deep) per slice: the toy voice 1.1
  (70 / 64), the drums voice 2.1 (515 / 248), concentrated in tone_pitch_hz (2-9 a slice), pitch_sweep_semitones /
  _ms (1-10), pitch_mod_semitones / _rate_hz, fold_volts / _symmetry, noise_pattern (8-12 when metal is audible).
  By term: envelope 467, pitch 250, spectral 282 minima on the drums voice; on the toy 10, 9, 63. My prediction
  (only pattern / tune / mod rate / pitch rugged, the rest <= 2) is wrong: sweep and fold are rugged too, and the
  pitch and envelope terms are rugged where the toy's are not.
- Basin shape (not planned; the measure that decided where to look): the score at RMS distance r from the truth
  along 16 random directions in all 31 dimensions. Toy voice, median: r 0.005 -> 1.0-3.3, 0.02 -> 2.6-5.9, 0.1 ->
  8.7-16: a funnel. Drums voice: r 0.005 -> 3.2-15.8, 0.02 -> 10.8-18.4: a needle. One parameter at a time (+-0.0025
  .. 0.01, 8 targets): the jump is tone_pitch_hz (+3.9 at 0.0025 = 0.25 semitone), pitch_mod_rate_hz (+4.4),
  pitch_mod_semitones (+1.9), noise_pattern (+2.5, one step); the rest < 0.5. Decomposed: the pitch term is the jump
  (target 0: 0.1 % of the pitch axis moves pitch 0 -> 2.35, spectral 0.33 -> 2.53; at 0.5 % pitch hits its 12
  semitone cap). YIN's per-frame period on the drums voice's tones (folded, square / triangle pitch modulation at
  audio rate, tones above PITCH_HIGHEST_HZ 2 kHz, metal noise in the mix) flips between dips under tiny changes, and
  each flip costs up to 12. With PITCH_WEIGHT 0 the drums voice's r 0.005 median falls to 2.4-4.7 (toy 0.8-3.2).

## H5. The pitch term is the root cause

Prediction: PITCH_WEIGHT 0 (nothing else changed), the default search, drums targets 0-7: recovery rises from 0 / 8
(the baseline on these eight: 0 / 4 measured before stopping it) to >= 3 / 8; the toy voice stays >= 75 % (its pitch
slices were unimodal in the spectral term alone: 9 minima over 8 targets).

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

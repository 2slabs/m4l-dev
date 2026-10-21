# 2026-10-20: why the matcher recovers the toy voice (85 %) and not the 2sl drums voice (10 %)

## Status (2026-10-21)

Open: the 2sl drums synth voice's self-recovery is 0 / 8 (fixture voice 20 / 20). Root causes (1) and (2) are fixed
in the kit (e7cff6c) and in 2sl drums 0.3.18 (noise_pattern an enum); (3), the voice's continuous landscape, is not a
search setting. Waiting on the user, who deferred both: calibrating the bar by ear (is "within 0.25 of the truth's
score" the right "recovered"?) and a learned warm start (Genopatch's net, architecture/patch-matcher.md "Open"); or
far larger budgets. After that: the user's targets (Drumazon 909 kicks first) through `tools/match_patch.py`, each
`.match.wav` listened to against its `.target.wav`.

The matcher itself (score, search, CLI, the drums' MatchedVoice, one C build-and-cache) is built:
architecture/patch-matcher.md.

## The investigation

The matcher is the drums engine's acceptance test (architecture/patch-matcher.md). On the drums' synth voice
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

### H5 result: refuted

PITCH_WEIGHT 0: 0 / 5 recovered (targets 0-4; stopped there, the prediction needed 3 / 8). Best found 2.9-6.7, all
of it spectral (2.9-6.5 dB; envelope 0.03-0.8). The pitch term made the needle, but the search misses without it too.

### H1 result (stopped at k = 8, which already breaks)

k = 2: 6 / 6; k = 4: 6 / 6; k = 8: 0 / 2 (target 0 lost the noise filter cluster: filter mode, cutoff, band 2 level,
EQ frequency; target 1 lost the metal tune and band 2 level). Prediction (k 8 ~60 %) too kind: it breaks between 4 and
8 free parameters, at the noise / filter parameters and the switches, not at pitch.

## H3a. The search's shape: six small strands vs one large population

CMA-ES on multimodal functions with a global structure needs a large population (Hansen's tutorial, IPOP); six
strands of 2000 with population 14 (1000 global renders each) cannot. The radial measurement shows a global funnel
(median score rises steadily from r 0.02 to 0.3) under the local ruggedness. Test: one CMA-ES, population 96 (IPOP
doubling), its population scored in parallel by 6 processes, the same 12 000 renders (70 % global, 30 % refinement
from its best at step 0.05), the current score, targets 0-7. Prediction: >= 3 / 8 recovered (baseline 0 / 4 on these),
median best <= 3.

### H3a result: refuted

0 / 3 (targets 0-2, stopped). The large population's global phase ended at 9.1, 7.8, 11.4 (the six strands' global
phases reach ~5-8), refinement brought them to 4.9, 5.8, 8.3. A large population does not find the basin.

## H6. Basin of attraction: from how far does a local search come back?

CMA-ES (default population, step = r) started at the truth moved by RMS r per coordinate (all 31, random direction),
3000 renders, the current score; targets 0-3. Prediction: back to <= truth + 0.25 from r 0.02 in >= 3 / 4, from
r 0.05 in 2 / 4, from r 0.1 in <= 1 / 4, from r 0.2 in 0 / 4. If even r 0.02 fails, the score is a needle at the
local scale and no global search can be the fix; the score (or the parameter axes) must change.

### H6 result: even r 0.02 fails; the local landscape is the problem

Drums voice pinned to kit aa62cc6 + 2sl-drums 68b58af (the voice changed under the earlier runs). 2000 renders a run.
Current score: 0 / 4 from r 0.02, 0 / 4 from r 0.05; the search ends further from the truth than it started (0.03-0.07
from 0.02). PITCH_WEIGHT 0: 0 / 8. Spectral term alone: 0 / 8. So no score term alone is the cause: the drums voice's
spectral landscape is itself not a funnel at the 0.02 scale.

Binary search by group (only one group moved by r 0.02, the rest exact, all 31 searched, no pitch term): the switches +
pattern moved: 2 / 4 (target 3: metal, 1.55 -> 1.33); the tone group (pitch, sweep, pitch mod, harmonics, fold): 1 / 4
(starts 4.3-6.1); the rest (noise filter, envelopes, click, strip): 0 / 4, and two of those runs never improved on
their start in 2000 renders (1.43, 2.06): with every candidate's pattern and switches moved at step 0.02, no candidate
beat the start.

## H7. The unordered discrete parameters inside CMA-ES's continuous vector block it

noise_pattern (255 unordered colours) and the four switches are axes of CMA-ES's continuous vector: any step moves the
pattern to an unrelated colour and a switch near its edge to another branch, so most candidates of a generation are
bad for a reason unrelated to the continuous parameters, and selection learns nothing. Test: the same local runs
(r 0.02, all 31 moved; no pitch term) with the five discrete parameters held at the truth and out of the vector.
Prediction: >= 3 / 4 recovered (from 0 / 4).

### H7 result: refuted as the whole cause

The five discrete parameters held at the truth: 0 / 8 from r 0.02 / 0.05 (target 3 came to 0.31). Holding also
tone_pitch_hz, pitch_mod_rate_hz and pitch_mod_semitones (23 continuous searched): 0 / 6 in 2000 renders, the best
0.41-1.27, closer. Given 8000 renders those 23 converge slowly but do converge: 2 / 4 at 2000 renders -> 3 / 4 within
0.35 by 8000 (target 0 stuck at 1.31 vs 0.91). Control, the toy voice from r 0.05: 8 / 8 within ~1000 renders.
So three things stack on the drums voice: the pitch term's needle (H5), the unordered discrete axes and the chaotic
tone parameters (audio-rate pitch modulation, pitch itself on folded / modulated tones), and a slow, ill-conditioned
continuous remainder (23 parameters need ~4000+ renders from 0.02 away, the toy's 8 need ~500).

## H8. Global search without the hostile parameters

The default search (6 x 2000), no pitch term, the five discrete parameters and the three chaotic tone parameters
held at the truth (23 searched), targets 0-7. Prediction: >= 4 / 8 recovered. If so, the hostile parameters are the
cause to fix in the search (sweep them on their own axes); if not, the continuous remainder's global search is.

### H8 result: refuted; the continuous remainder is slow, not trapped

Hostile parameters held at the truth (23 searched, default 6 x 2000, no pitch term): 0 / 4, best 2.2-3.2. A single
local CMA-ES over those 23 from r 0.1 is still improving at 8000 renders (0.35-1.64, from ~2.6 at 1000); from r 0.25
0.72-3.3. The default search gives each strand 1000 refinement renders: the H8 results are where the r 0.1 runs stood
at 1000. Probed by finite differences, the 23 are a cone whose slopes differ ~100x between parameters (pitch sweep
0.13 per 1e-3 of the unit axis, click noise 0.0004): an ill-conditioned problem CMA-ES learns in O(n^2) generations.
Not cheaper by Levenberg-Marquardt on the feature residuals (a prototype jumped off and stuck: the floored dB
residuals are not smooth enough for a forward-difference Jacobian). The renderer is built at -O0: -O2 renders the
drums voice in 19 ms instead of 34.5, the same samples.

## H9. Refinement: the tutorial's CMA-ES (active, negative weights) and a scaled start

The kit's CMA-ES has positive weights only; Hansen's tutorial (references/sound-matching.md, cma-es, Table 1 and eq.
(46)-(47), the default since 2016) uses negative weights (active CMA, Jastrebski & Arnold), and allows different
initial scales per variable as C's diagonal (Fig. 6 footnote: "should not disagree by several orders of magnitude").
Test, r 0.1, the 23 benign parameters, no pitch term, 3000 renders, targets 0-3: V1 active weights; V2 V1 + C's
diagonal from a central-difference probe (2n renders; per-axis scale ~ 1 / slope, clipped to a 100x span).
Prediction: V1 at 3000 renders reaches what the current CMA-ES reached at 8000 (median ~0.8); V2 better than V1.

### H9 result: refuted

At 2500 renders from r 0.1 (benign 23, no pitch term): kit CMA-ES 0.52-2.11, active 0.97-2.03, active + probe-scaled
diagonal 1.51-6.07 (worse: the probe's large steps on flat axes throw it off). Neither changes the speed.

### Side measurements

- 1-D multimodality along pitch_sweep_semitones: a pure swept sine (noise, click, fold, strip, harmonics and pitch mod
  off) is unimodal on targets 0 and 4 (1 minimum in 201 points; 9 and 19 as drawn) and still 17 on target 1 (a 37 Hz
  tone: the 1024-point FFT and the envelope see its cycle's phase, as the kit's own comments measured for kicks).
  Summed over 8 targets x 6 parameters: 256 minima (no pitch term); 1024-point FFT attack-only 241; envelope term
  off 169; both 139.
- The YIN pitch term costs the toy voice too: its recovery (20 targets, kit aa62cc6, renderer -O2) is 85 % with it,
  95 % with PITCH_WEIGHT 0, 100 % with the pitch term replaced by a log2 spectral centroid difference (Turian & Henry
  2020, references/sound-matching.md D: "log2(Spectral Centroid) 0.515 / 1.000 / 1.000", perfect pitch ordering at
  +-30 and +-600 cents, for derivative-free search), 0.25 per semitone, per frame of the 4096 / 2048 / 1024 log-mel
  spectrograms, weighted by the target frame's level.

## P1. The package so far, on the drums voice

The score's pitch term replaced by the log-centroid term; the search holds enums and integers out of CMA-ES's vector
and sweeps every one of their values at the strand's best after each global run and between two refinement halves;
6 x 2000 renders. Prediction: 2 / 8 (from 0 / 8): the discrete fix and the needle's removal help, the slow
continuous remainder still limits.

### P1 result: refuted

0 / 4 (best 2.9-9.1). The sweeps of all 269 discrete values (pattern 255 + four switches) after every global run ate
most of each strand's 1000 global renders. Changed after: enums only are swept (an integer is an ordered count, a
CMA-ES axis; the metal pattern belongs in an enum), once after the global phase (2 passes) and after each refinement
half (1 pass), and an enum whose first 4 other choices score exactly the held one is inactive and left (the pattern
while white noise plays).

A drum-like prior (each demo preset, continuous parameters moved by N(0, 0.05)), the P1 code but integers swept once
after the global phase: kick 3.73 vs truth 1.56, snare 4.73 vs 2.71: missed. The kick's found sound explains the
truth's 38-semitone 22 ms sweep by an 8-semitone 66 ms one plus low-passed noise and more Compress: a different
local minimum, 3.65 dB of spectrum away.

## Final measurements (kit e7cff6c's matcher code on the pinned voice: kit aa62cc6 + 2sl-drums 68b58af)

Committed (e7cff6c): log-centroid term instead of YIN; enums swept (integers stay CMA-ES axes); renders at -O2.

| voice, prior (6 x 2000 renders) | recovered (<= truth + 0.25) | best found | truth |
|---|---|---|---|
| fixture, 20 uniform draws | 20 / 20 (was 17 / 20) | | 0.09-2.96 |
| drums, 8 uniform draws (metal pattern as an enum) | 0 / 8 (was 0 / 4 of these) | 4.0-9.4, median 5.6 | 0-2.65 |
| drums, 8 demo presets moved by N(0, 0.05) | 0 / 8 | 2.7-6.1 | 0-4.4 |
| drums, the moved kick at 6 x 8000 | 0 / 1 | 2.25 (3.73-3.84 at 6 x 2000) | 1.56 |

Root causes, in the order they bite: (1) the YIN pitch term's needle (fixed); (2) unordered enums / the metal pattern on
CMA-ES axes (fixed in the kit; the drums' noise_pattern must become an enum, 2sl-drums' MatchedVoice); (3) the drums
voice's continuous landscape: stiff / sloppy (slopes ~100x apart) with phase-driven local minima along sweep and fold,
so a local CMA-ES needs > 8000 renders from 0.1 away and random starts end in other sounds 3-9 dB away. (3) is not a
search setting (H3a population, H9 active CMA-ES / scaling: no change) and not a score term alone (H6: spectral alone
fails too). What is left to try, each a decision: a learned warm start (Genopatch's net, the architecture's open item)
to land starts inside the basin; far larger budgets (4x renders moved the kick 3.8 -> 2.25 of 1.56); and the bar
itself: for the 12 / 20 uniform draws with the metal source the truth scores exactly 0 (the shift register ignores the
seed), so "recovered" there means within 0.25 dB of the same waveform.

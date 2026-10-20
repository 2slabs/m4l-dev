# The patch matcher: a voice's parameters for a target hit

User, 2026-10-19: the acceptance test for the 2sl drums engine: "without having something like the genopatch, and
having it actually remake some drumazon 909's and whatever else we decide is important, we will not know how useful it
actually is". The device ships parameters, never samples: a recording is only ever a target, on the developer's disk.

Genopatch's loop (2sl-drums references/er1-microtonic-genopatch.md §3: guess, render, compare, refine, in strands),
without its neural warm start: the voice is rendered by the kit's own renderer and scored against the target, and a
derivative-free search moves the parameters. Sources for every choice: references/sound-matching.md.

## Where it sits

| module | what it is |
|---|---|
| `m4l_dev/patch_match_voice.py` | `MatchedVoice` (GenExpr code, inputs / outputs, `MatchedParameter`s, fixed values, `MatchTrigger`, audio output, noise seed) and the unit-cube map: plain picklable data |
| `m4l_dev/patch_match_score.py` | `MatchTarget`: a target analysed once; `components(candidate)` / `score(candidate)`; the analysis C built into the kit's C cache |
| `m4l_dev/patch_match_features.c` | onset, loudness (BS.1770 K-weighting from `bs1770.py`), log-mel spectrograms, envelope, YIN, the distance. Every layout decision is here |
| `m4l_dev/patch_match_search.py` | `match_patch(voice, target, rate, SearchSettings)`: CMA-ES strands in processes, refinement, the score curve |
| `m4l_dev/wave_files.py` | WAV in (PCM 8-32, float 32/64, extensible) and out (float 32) |
| `tools/match_patch.py` | the CLI: `--voice module:NAME --target hit.wav --out result.json` (+ `.match.wav` / `.target.wav` for A/B) |
| `tests/fixture_drum_voice.py` | the validation voice: swept sine + filtered noise + drive, 8 parameters |
| `tests/test_patch_matcher.py` | fast (seconds): score orderings and parts, voice spec, CMA-ES, a 2-parameter match, WAV, the CLI |
| `tests/test_patch_matcher_recovery.py` | slow, opt-in (`M4L_DEV_SLOW_TESTS=1`): parameter recovery at random known settings |

Targets: `match-targets/` at the kit root (gitignored), or anywhere outside a repository.

## The contract

- **A voice** is any program the kit renders (`m4l_dev/genexpr.py`): a drum voice's own gen~ code, with its Params.
  Each searched Param has a range on a linear or log scale, or is an integer range, or an enum (its values); the
  range must sit inside the Param's own min / max (the renderer would clamp it silently otherwise). Params not
  searched keep their default or a fixed value (a Param whose code leaves its default out, the Init values' to
  write, must be searched or fixed). A hit is: a fresh program (no state from the hit before), the trigger
  on its input (an impulse, or a gate held `held_seconds`), the other inputs at 0, the audio output, a fixed noise seed
  (gen~'s noise(), and the voice's seed Param, `noise_seed_param`, which its kit techniques read: SeededWhiteNoise,
  PitchModulator's random). A hit is a function of its parameters.
- **The score** (`patch_match_score.py`'s docstring for the terms): 0 for identical hits, in dB-like units, blind to
  level and to where the hit starts in the file; at most the first 2 s after the onset. Silence scores the worst
  (`SILENT_CANDIDATE_SCORE`); a NaN or infinity raises (a voice bug, never a score).
- **The search** is deterministic in (voice, target, settings, seed), whatever the number of processes. It returns
  every strand's best, the best first, and the score curve. It never touches the device: its output is parameter
  values, which a preset book then holds.
- **What it does not do**: velocity or key response (Genopatch's tip: set after the match), and more than one voice
  per hit (a layered sample is matched by one voice as well as that voice can).

## Choices, with their measurements (fixture drum voice, 48 kHz)

- Four FFT sizes (4096, 2048, 1024 over the whole hit; 512 over its first 50 ms), not DDSP's six: shorter windows
  than a kick's cycle score its phase (a 0.24 semitone change of sweep moved the 128-point term from 3 to 10 dB while
  512 and up moved < 0.2 dB), which made the score so rugged that searches stopped in local minima.
- The envelope is a peak follower (instant attack, 50 ms release), not a short RMS: a 5 ms RMS of a 42 Hz tone is its
  cycle (the same 0.24 semitone moved it 0.1 -> 2 dB).
- The pitch term weights frames by the target's tonality and level, softly; YIN's dip threshold is 0.3 (its paper's
  0.1 made noisy frames fall to subharmonics, and which subharmonic changed with the noise).
- A recording never shares the voice's noise: two renders of the same settings with different noise seeds score
  0 .. 3 (a noisy hit the most). Recovery is judged against that: found <= the truth's own score + 0.25.
- Search: 6 strands x 2000 renders, half spent refining each strand's best (CMA-ES restarted at step 0.05): local
  minima are the norm, refinement moved most strands' results the furthest.

## Open

- A learned warm start (Genopatch's net; train on the voice's own renders), if matches of real targets are too slow.
- Recovery, 2026-10-19 (20 random fixture settings, 6 x 2000 renders, ~26 s a match on 6 cores): the sound in 85 %
  (17 / 20 at most the truth's score + 0.25); per parameter within 0.05 of the truth (unit cube): pitch, decay, drive
  100 %, sweep depth 70 %, noise decay 70 %, noise cutoff 60 %, sweep time 55 %, noise level 40 %; all eight at once
  0 %. The noise's level and colour trade against each other and the drive (several settings sound the same); a
  matched sound, not the target's knob positions, is what the drums need.

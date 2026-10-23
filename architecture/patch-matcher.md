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
| `twosl_dsp/patch_match_voice.py` | `MatchedVoice` (GenExpr code, inputs / outputs, `MatchedParameter`s, fixed values, `MatchTrigger`, audio output, noise seed) and the unit-cube map: plain picklable data |
| `twosl_dsp/patch_match_score.py` | `MatchTarget`: a target analysed once; `components(candidate)` / `score(candidate)`; the analysis C built into the kit's C cache |
| `twosl_dsp/patch_match_features.c` | onset, loudness (BS.1770 K-weighting from `bs1770.py`), log-mel spectrograms, envelope, the distance (cells, envelope, log spectral centroid). Every layout decision is here |
| `twosl_dsp/patch_match_search.py` | `match_patch(voice, target, rate, SearchSettings)`: CMA-ES strands in processes, enum sweeps, refinement, the score curve |
| `twosl_dsp/wave_files.py` | WAV in (PCM 8-32, float 32/64, extensible) and out (float 32) |
| `tools/match_patch.py` | the CLI: `--voice module:NAME --target hit.wav --out result.json` (+ `.match.wav` / `.target.wav` for A/B) |
| `tests/fixture_drum_voice.py` | the validation voice: swept sine + filtered noise + drive, 8 parameters |
| `tests/test_patch_matcher.py` | fast (seconds): score orderings and parts, voice spec, CMA-ES, a 2-parameter match, WAV, the CLI |
| `tests/test_patch_matcher_recovery.py` | slow, opt-in (`TWOSL_DSP_SLOW_TESTS=1`): parameter recovery at random known settings |

Targets: `match-targets/` at the kit root (gitignored), or anywhere outside a repository.

## The contract

- **A voice** is any program the kit renders (`twosl_dsp/genexpr.py`): a drum voice's own gen~ code, with its Params.
  Each searched Param has a range on a linear or log scale, or is an integer range (an ordered count), or an enum (its
  values: choices in no order of sound, like a filter mode or a shift register's pattern); the
  range must sit inside the Param's own min / max (the renderer would clamp it silently otherwise). Params not
  searched keep their default or a fixed value (a Param whose code leaves its default out, the Init values' to
  write, must be searched or fixed). A hit is: a fresh program (no state from the hit before), the trigger
  on its input (an impulse, or a gate held `held_seconds`), the other inputs at 0, the audio output, a fixed noise seed
  (gen~'s noise(), and the voice's seed Param, `noise_seed_param`, which its kit techniques read: SeededWhiteNoise,
  PitchModulator's random). A hit is a function of its parameters.
- **The score** (`patch_match_score.py`'s docstring for the terms): 0 for identical hits, in dB-like units, blind to
  level and to where the hit starts in the file; at most the first 2 s after the onset. Silence scores the worst
  (`SILENT_CANDIDATE_SCORE`); a NaN or infinity raises (a voice bug, never a score).
- **A render** is built at -O2 (`genexpr.OPTIMISED_COMPILER_FLAGS`): the same samples as the kit's -O0 renderer
  (the same floating-point flags), 1.8x faster on the 2sl drums voice; a match renders one program thousands of times.
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
- No pitch tracker. A YIN pitch term (until 2026-10-20) made the score a needle on the 2sl drums voice: on folded,
  audio-rate-modulated or noisy tones YIN's chosen dip flips under a 0.1 % move of a parameter, each flip up to 12
  semitones (PLANS/2026-10-20-matcher-search.md, H5). The ordering it was for comes from the log2 spectral centroid
  per frame (Turian & Henry, references/sound-matching.md D), 0.25 a semitone: smooth, and the fixture voice's
  recovery rose from 85 % (YIN) to 100 %.
- Enums are swept, not searched: each choice tried at the strand's best (after the global phase and after each
  refinement half); on a CMA-ES axis, any step lands on an unrelated choice. An enum whose first 4 other choices score
  exactly the held one is silent there and left.
- A recording never shares the voice's noise: two renders of the same settings with different noise seeds score
  0 .. 3 (a noisy hit the most). Recovery is judged against that: found <= the truth's own score + 0.25.
- Search: 6 strands x 2000 renders, half spent refining each strand's best (CMA-ES restarted at step 0.05): local
  minima are the norm, refinement moved most strands' results the furthest.

## Open

- A learned warm start (Genopatch's net; train on the voice's own renders). The 2sl drums voice (31 parameters) needs
  it, or something else that finds the basin: see the recovery figures below and PLANS/2026-10-20-matcher-search.md.
- Recovery, fixture voice (20 random settings, 6 x 2000 renders): 2026-10-19 85 % (YIN pitch term); 2026-10-20
  100 % (log-centroid term, enum sweeps, -O2 renders; median 111 s a match on a machine at load 20-40). Per parameter within 0.05 of the truth (2026-10-19): pitch, decay, drive 100 %, sweep depth
  70 %, noise decay 70 %, noise cutoff 60 %, sweep time 55 %, noise level 40 %; all eight at once 0 %. The noise's
  level and colour trade against each other and the drive (several settings sound the same); a matched sound, not
  the target's knob positions, is what the drums need.
- Recovery, 2sl drums synth voice (31 parameters, 6 x 2000 renders), 2026-10-20: 0 / 8 uniform draws (median best
  5.6 against truths 0-2.7), 0 / 8 demo presets moved by N(0, 0.05) (best 2.7-6.1 against 0-4.4). What stops it
  (measured, the plan's H1-H9): its landscape is a stiff / sloppy cone (slopes ~100x apart between parameters) with
  phase-driven local minima along the sweep and fold parameters; a local CMA-ES from 0.1 (unit cube, RMS) away needs
  > 8000 renders over the 23 benign parameters alone; from a random start the strands end in different sounds
  (3-9 dB of spectrum away).

# 2026-10-19: the patch matcher (Genopatch-style), the 2sl drums' acceptance test

The user (2026-10-19): "without having something like the genopatch, and having it actually remake some drumazon 909's
and whatever else we decide is important, we will not know how useful it actually is". The device ships parameters,
never samples. Contract and choices: architecture/patch-matcher.md. Sources: references/sound-matching.md.

## Done

1. Score: multi-resolution log-mel + peak-follower envelope + YIN pitch, onset-aligned, loudness-normalised (C,
   built into the kit's cache; standard library only, numpy is not a kit dependency).
2. Search: CMA-ES strands (IPOP restarts) + refinement, spawn processes, deterministic in the seed.
3. Validation: fixture drum voice; fast orderings test; opt-in parameter-recovery test.
4. CLI `tools/match_patch.py`; targets in `match-targets/` (gitignored).

## Next

- The 2sl drums voice (ER-1 + Microtonic + Jomox/Drumazon kick) as a `MatchedVoice`; the user's targets (Drumazon 909
  kicks first) through `tools/match_patch.py`; listen to each `.match.wav` against its `.target.wav`.
- Fold `patch_match_score.features_library()`'s build-and-cache code and `genexpr.load_render_function`'s into one
  kit function (a C source + flags -> a loaded library): two copies of the same lock / build / cache logic today
  (left apart on 2026-10-19 because genexpr.py was being changed by other work the same day).

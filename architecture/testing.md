# Testing: the build is the same, the tests aren't the build

The user's rule (2026-10-21): "the build should be the same, but the tests aren't the build".

- **The build is compared byte for byte.** Everything a build writes (devices/, dist/, `.adv`, a plugin's generated/,
  the Live parameter lock) is the same on every machine (overview.md, "Generated numbers") and the tests compare it
  exactly: `build_comparison`, `generate.py --check`, the lock. Fetched sources are checked by their sha256 (a
  source, not a render). Those stay exact.
- **A sound is compared as sound.** Two renders (plugin vs device, before vs after a change that should keep the
  sound, -O2 vs -O0, a block reset vs a fresh one, a preset migrated vs as it was) are compared by
  `twosl_dsp/render_comparison.py`, the one comparator: `renders_are_similar(reference, candidate, sample_rate)` gives
  a verdict and its numbers; `assert_renders_similar(...)` fails a test with them. Never `==`, `assertEqual`, a hash
  or `array_equal` on renders, and no second comparator.
- **Exact stays exact where the claim is a value, not a sound**: silence that must be exactly 0 (an idle voice), a
  constant, integers and discrete states (indices, counts, gate states, a seeded draw's numbers in the brain), one
  value of the renderer's arithmetic against Python's (tests/test_genexpr.py: the translation, value by value), a
  latency in samples, and the first sample at which a change reaches the output (2sl stab's latency probe: two
  runs of one program on one machine share every bit until the change, so the first differing sample is a time,
  measured exactly). Every other pair of sample sequences compared with each other is two renders.
- **Accuracy bounds stay**: a test holding a block to its equation or to a twin within a bound on each sample far
  over the last bits and far under the comparator's (1e-9 on a signal near 1) claims more than "the same sound" and
  keeps its bound; another machine's last bits (1e-16) pass it. It says so through `twosl_dsp/model_accuracy.py`, the
  one way: `assert_matches_model(actual, expected, tolerance, what, tolerance_reason)`, every sample within an
  absolute tolerance, the reason for that tolerance stated at the call.

## Two sequences compared: which claim, which tool

| the claim | examples | the tool |
|---|---|---|
| **these two renders are the same sound** | a refactor, a reset, a re-hit, a seed, an alternate path (a Param for a constant, fewer Newton iterations than the converged loop, plugin vs device) | `assert_renders_similar` (no bound of the test's own) |
| **the DSP computes this math** | an identity (low-pass + high-pass = the input, a cut undoing its boost, Rev's sweep = 1 - Norm's), a twin, a reference model in Python (a pad's Thiran all-pass, a whole-sample delay) | `assert_matches_model` with a tolerance and its reason |

A bound looser than the comparator's (1e-3 of the peak, 1e-6 on a signal near 1) is not an accuracy claim: it says
"the same sound" and goes to the comparator. A test's own `max(abs(a - b)) < bound` is neither, so it isn't written.

## The measure

The residual, candidate - reference, against the reference's own level (every channel together):

| figure | what | limit |
|---|---|---|
| `residual_db` | 10 log10(sum(residual²) / sum(reference²)) over the whole render | at most **-70 dB** |
| `worst_window_residual_db` | the residual's mean energy in each 10 ms window (windows tile the render) over the reference's mean energy across the whole render | at most **-60 dB** |
| `level_difference_db` | 10 log10(sum(candidate²) / sum(reference²)) | reported |

A reference under -120 dBFS (mean square) counts as -120 dBFS, so silence asks for near-silence, not a division by
zero. A different length or channel count, a NaN or an infinity is never similar, said loudly.

**Why these.** A residual is what the change adds to the sound, so it's measured as a level next to the program.
The whole render's figure catches a change everywhere (a level, a parameter); the windows catch a short one (a click,
a dropout) that the whole render averages away; a window is measured against the whole program's level, not its own,
so a quiet passage doesn't turn a last-bit wobble into a failure. Level is the residual's job too: a gain of g dB
alone leaves 20 log10(10^(g/20) - 1) dB, -38.7 dB at 0.1 dB, so -70 dB holds a level to 0.003 dB; a separate level
limit would only be a looser copy.

**Where the limits sit** (tests/test_render_comparison.py holds every case, on a stand-in program at -21.6 dBFS RMS,
the quietest of 2sl filter's preset renders the plugin test compares):

| case | residual | worst window | verdict |
|---|---|---|---|
| a relative 1e-7 wobble on every sample (single precision's rounding; a double's last bits are 1e-16) | -144.8 dB | -140.3 dB | passes |
| 2sl filter's plugin vs device on macOS / ARM: isolated one-sample spikes up to 5.9e-4 (-64.6 dBFS), five in 0.5 s, two in one window | -80.3 dB | -66.8 dB | passes, 6 dB or more under each limit |
| one such spike on each of 2sl filter's real preset renders (measured 2026-10-21) | -89.5 dB at worst | -72.5 dB at worst | passes |
| one sample 0.003 (-50 dBFS) added: a click | -72.7 dB | -55.7 dB | fails on its window |
| 1 ms zeroed: a dropout | -27.3 dB | -10.3 dB | fails |
| 0.1 dB louder | -38.7 dB | -34.3 dB | fails |
| a one-pole cutoff 1000 -> 1010 Hz (1 %) | -51.4 dB | -49.7 dB | fails |
| one sample late | -18.9 dB | -18.4 dB | fails |

So a pass means an error at least 70 dB under the program across the render and 60 dB under it in any 10 ms: for a
program at -20 dBFS that is -90 dBFS across the render (the order of 16-bit audio's quantisation noise, 6.02 x 16 +
1.76 = 98 dB under a full-scale sine) and -80 dBFS in a 10 ms burst. Last-bit differences sit 70 dB under the limits,
the worst cross-machine case seen 6 dB under; every real change tried fails, the smallest (the -50 dBFS click, chosen
near the line to show the window's job) by 4 dB, the rest by 10 dB or more.

## How to report a comparison

Say the numbers, not "bit-identical": "every preset within tolerance: worst residual -132.4 dB (limit -70), worst
window -118.0 dB (limit -60)". A failure prints `NOT SIMILAR` with every figure, the worst window's time and the
largest sample difference and where; quote it. Bit-identical is a claim about a build's bytes only.

## Timing tests

A test that times something reads the machine's load first (`os.getloadavg()`) and reports it with the result,
measures CPU time (the thread's clock, `time.thread_time`, or the process's and its children's, `getrusage`'s
microsecond fields; never `os.times()`, whose fields are truncated to 10 ms ticks), not wall clock, and times one run: no best-of-N, no averaging. `twosl_dsp/cpu_timing.py`'s `CpuTiming` is the one way: THREAD
for work on the calling thread, PROCESS_AND_CHILDREN for work over worker processes (the patch matcher's), and a
timing whose load before it plus the cores it uses is over the machine's cores says NOT JUDGED with its numbers: a
test that would judge it skips, loudly, and a report (the recovery tests' CPU seconds a search) prints it.

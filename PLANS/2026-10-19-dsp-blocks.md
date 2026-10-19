# 2026-10-19: the kit's DSP blocks (ladder, echo, saturator, band-limited edges)

The user (2026-10-19): "yea let it howl, build them as kit blocks … find your favorite and coolest and best
implementation of these things … if you like that other filter implementation more than what we have put it in there".

Input: the stab DSP audit (scratchpad `stab-dsp-audit/README.md`: findings, fixes E1–E4, F1, D1, O1, O2, its renders,
scripts and `sources/`).

## Decisions

- Dub at 100 % howls: the echo self-oscillates near the top of Dub, held at a bounded level by its saturation (E3).
- Each of these is built once in the kit, as a gen~ block a device includes. Stab first, then gate (its echo is stab's
  echo copied, and its oscillators use polyBLEP).
- The best implementation wins, not the audit's minimum. The audit's fixes are the floor. Each block is chosen by A/B
  renders plus numbers against a stated reference (the analytic or oversampled ideal, the tempo grid, a source).
- The ladder self-oscillates at fc, at every cutoff, from about 90–95 % Resonance.
- Sources go into the kit's `references/` as notes + fetch scripts (no PDFs in git).

## Blocks

1. Ladder: ZDF/TPT (Zavalishin), nonlinear. Free to go beyond F1 (per-stage tanh, solved feedback) if it sounds and
   measures better at sane CPU for 16 voices.
2. Saturator: ADAA tanh (Bilbao 2017), also used inside the echo loop.
3. Edges: 4-point polyBLEP for saw, pulse and sub; polyBLAMP (or integrated BLEP square) triangle.
4. Echo: on-grid repeats (E1), tape-speed glide that never reverses (E2), howl (E3), wow and flutter as pitch (E4),
   diffusion optional, gate's Wow and Saturation knobs.

## Steps

Done 2026-10-19: the kit's blocks (architecture/dsp-blocks.md) and 2sl stab 2.1.0 on them.

Done 2026-10-19 (step 3): 2sl gate 0.3.7 on the kit's echo and edges block (every jump and corner of its blend
waves and modulator; the edges block gained restart_statements for a wave run ahead and reset at a note).
Done 2026-10-19 (step 4): 2sl gate 0.3.12's 259 folder: the CA3160 cells built from DAFx-17 Table 1 and a 6 V
rail (the original; a model constant), straight pieces with closed-form antiderivatives (ADAA), each node floored
0.5 V under its negative rail, the +-5.1 V limiter, the drive stage's 10.3 kHz gain, Symmetry's offset opened by Fold
(user 2026-10-19). Exposing the rail as a control would need a new Live parameter: proposed, not added. Details in
2sl-gate references/buchla-259-circuit.md §4.3.
4. (was) Gate's folder, after step 3: the 259 folder as the DAFx-17 model (Esqueda, Pöntynen, Parker & Bilbao), which is
   already the op-amp model: each of the five cells is a CA3160 on +-6 V rails (the rest of the 259 is on +-15 V), and a
   cell folds where its output hits its rail (2sl-gate references/buchla-259-circuit.md). User 2026-10-19: "there is not
   enough power on the opamp rails, so that's how it folds". So: the rail voltage is the model's parameter (it moves
   every fold point; Theelen's TL072 build ~ +-4.5 V = 0.75x), anti-aliased (ADAA, closed form per cell), plus the
   original's extras where drive is hot: the CA3160 input clamp (one-sided, above ~8.4 V), the +-5 V zener limiter, the
   ~10.3 kHz drive-stage lowpass, slew at several kHz. Open: Symmetry into the folder (SPEC) vs the original's separate
   Symmetry/Order path (asked 2026-10-19).

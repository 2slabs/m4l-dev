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
4. Gate's folder, after step 3: the DAFx-17 virtual-analog 259 wavefolder (Esqueda, Pöntynen, Parker & Bilbao,
   "Virtual analog model of the Buchla 259 wavefolder"), anti-aliased (ADAA), as published. User 2026-10-19: DAFx first.
5. After 4 works: the op-amp version. User 2026-10-19: "the original circuit uses underpowering opamps. always been a
   favorite of mine". From the 259 schematic and service notes, establish how the op-amps behave (rails, clipping) and
   model it, A/B against step 4's folder. Possibly a choice on gate's Folder menu.

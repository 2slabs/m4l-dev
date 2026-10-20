# 2026-10-20: the kit in three layers (refactor level 3)

The user (2026-10-20): "we have all of these modules that exist that are the backbone of these instruments, either that
expose their modularity, or that wrap it (the roland synths using the same filter chip, that's their modular building
block, they're just wrapping it, this is what we're doing)". Level 3, "reorganize it all now".

## The layers

1. **Techniques**: how to do DSP well, no circuit identity. Antialiasing (edges, ADAA saturator, oversampler), zero-delay
   structures (state-variable filter), soft clip, envelopes, noise.
2. **Circuit modules**: one modelled piece of hardware, built from techniques. Its inputs are the real circuit's
   controls and CV in the circuit's units; its build character (rails, trims, tolerances) is a setting, so two
   instances can be two different units. Each cites its schematic / datasheet in references/.
3. **Instruments**: the devices. They wire modules and either expose them (gate shows the 259) or wrap them (drums).

## Steps

1. Kit: architecture/ states the layers and the pattern of each; every existing block is filed into one (the
   generic ladder decided: a technique, or a real module); modules and files moved and renamed; no old name left.
   Sound unchanged (bit-identical renders).
   DONE 2026-10-20: techniques in m4l_dev/techniques/ (zero-delay ladder and state-variable filters, antiderivative
   tanh saturator, knee soft clip, band-limited edges, tape-style echo: the ladder and the echo model no circuit),
   the LTC1060 / MF10 section the one circuit module (m4l_dev/circuit_modules/, volts in and out, clock in Hz,
   character a dataclass, references/circuits/ltc1060-mf10.md); architecture/dsp-blocks.md, tests/test_gen_block_layers.py;
   all 113 renders of the blocks' tests bit-identical. The devices move onto it in their own steps.
2. Gate: the 259 (sine core, modulation oscillator, folder) and the 292 (network, vactrol) move into the kit as
   modules; gate wires them. Bit-identical.
   DONE 2026-10-20: one module per schematic sheet of the 259 (buchla_259_principal_oscillator.py, sheet 2A;
   buchla_259_timbre_section.py, sheet 3A; buchla_259_modulation_oscillator.py, sheet 4A) and one per 292 channel
   (buchla_292_low_pass_gate_channel.py), the folder's ADAA a new technique (antiderivative_piecewise_linear_shaper.py);
   references/circuits/buchla-259.md and buchla-292-low-pass-gate.md (moved from 2sl gate, with their sources in
   fetch-circuit-sources.sh). 2sl gate 0.3.17 wires them: 361 renders (19 presets x 19 settings, every core outlet)
   bit-identical to 0.3.16. The principal oscillator takes Hz and FM every step and a reset: drums can use it as is.
3. Stab + filter: the pump (duplicated in both) moves into the kit; both use it.
   DONE 2026-10-20: `techniques/sidechain_style_pump.py` (`SidechainStylePump`, kit 1ed19d7): stab's shape (quarter-sine
   ramp in, power recovery, 20 ms hand-over between Live's beat and its own clock, 0.442 ms glide) plus the gate as
   `chop`; the display's duck is the technique's script. Stab 2.1.7 (sound unchanged, 3e-9) and filter 0.2.11 (its pump
   presets move <= 0.15 dB) use it and both copies are deleted. Both devices are on the layered kit (stab 2.1.6, filter
   0.2.10: renders bit-identical); filter has architecture/overview.md.
4. Drums: bump onto the reorganised kit; then its new voice is built on the 259 module (PLANS/2026-10-20-drum-synth-voice.md
   in 2sl-drums).
5. Later, as instruments need them, with sources first: Roland (IR3109, BA662), Moog 5U, Serge, a deliberately clinical
   one. The user (2026-10-20): a Mackie desk sim, "so it can sound like a mackie desk" (console channel/summing).
6. First new instrument: a standalone phaser device (the user, 2026-10-20: "lets start by making a standalone phaser, I
   can then try to find the water in it by playing with parameters"): the Mu-Tron Bi-Phase as a circuit module on an
   all-pass technique (references/circuits/mutron-bi-phase.md, references/allpass-and-diffusion.md). No hardware needed: a
   sourced circuit sim that sounds good is enough.
   KIT BLOCKS DONE 2026-10-20: techniques ZeroDelayOnePoleFilter, ZeroDelayAllpassCascade (normalised-lattice sections:
   the TPT all-pass gains energy under fast modulation), LedDrivenPhotocell (the gate's vactrol law and memory, for the
   292 module to share); circuit module MutronBiPhase (references/circuits/mutron-bi-phase.md, moved from
   references/). The device itself (a standalone 2sl phaser) is next, in its own repository.

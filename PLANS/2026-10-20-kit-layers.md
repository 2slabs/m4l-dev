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
2. Gate: the 259 (sine core, modulation oscillator, folder) and the 292 (network, vactrol) move into the kit as
   modules; gate wires them. Bit-identical.
3. Stab + filter: the pump (duplicated in both) moves into the kit; both use it.
4. Drums: bump onto the reorganised kit; then its new voice is built on the 259 module (PLANS/2026-10-20-drum-synth-voice.md
   in 2sl-drums).
5. Later, as instruments need them, with sources first: Roland (IR3109, BA662), Moog 5U, Serge, a deliberately clinical
   one.

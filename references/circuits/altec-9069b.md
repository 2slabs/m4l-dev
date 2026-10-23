# The Altec 9069B passive high-pass: King Tubby's "Big Knob"

Written 2026-10-21 for 2sl dub's stepped high-pass (2sl dub SPEC §3.1); the research is 2sl dub's
references/dub.md §1.2, copied here with its links so the kit's module has its own sources. No primary Altec or MCI
document was found.

Tags: **[VERIFIED]** read in the source itself. **[SECONDARY]** a credible secondary source. **[COMPUTED]** worked out
by us from the parts; the method is given. **[UNVERIFIED]** an inference or a single unconfirmed claim; do not build
on it without saying so.

## 1. What it is

- A passive high-pass, sold alone and as half of the Altec 9067B filter set with the 9068B low-pass; a 1965 catalogue
  lists the 9067A/9068A/9069A ([GroupDIY, Altec 9069B multitap inductor](https://groupdiy.com/threads/altec-9069b-multitap-inductor.74452/)).
  **[SECONDARY]**
- Tubby's was built into his MCI desk as a custom addition to take low end off the mic channels, and in his hands it
  "became a sweeping, phase-like trademark effect" ([RBMA](https://daily.redbullmusicacademy.com/2018/08/the-roots-of-dub/));
  the big red knob, top right ([Audio Merge KTBK-1B](https://audio-merge.com/products/ktbk-1b/)). **[SECONDARY]**
- Scientist: "No, no phasers. High-pass filter." ([Tape Op](https://tapeop.com/interviews/136/hopeton-overton-brown-scientist)).
  **[VERIFIED]** (his words)

## 2. The steps and the parts

- Ten steps: 70, 100, 150, 250, 500 Hz, 1, 2, 3, 5, 7.5 kHz (Audio Merge's replica, "reverse engineered" against an
  original). **[SECONDARY]**
- A builder who wound replacement inductors posted the ten inductor taps and ten capacitors (GroupDIY, 2021-01-18):
  6.3, 9.3, 15.4, 23.5, 46, 92, 200, 330, 481, 698 mH and 35.2, 53.8, 90, 133, 267, 550 nF, 1, 1.68, 2.67, 3.77 µF;
  another member gives the circuit, per step two capacitors in series with a shunt inductor from their junction to
  ground, a third-order constant-K T section for 600 Ω. **[SECONDARY]** (measured parts)
- **[COMPUTED]** each posted C as one of the two series capacitors and L as the shunt: the design resistance √(2L/C) is
  578–632 Ω on every step, and the corner 1 / (2π √(2LC)) is 69.4, 99.3, 151, 252, 500 Hz, 1.02, 2.01, 3.02, 5.03,
  7.56 kHz: the replica's ten within 2 %.
- Eleven or ten positions: AudioThing says "eleven frequency steps" and "10 positions" on one page
  ([AudioThing Dub Filter](https://www.audiothing.net/effects/dub-filter/)). **[UNVERIFIED]** reading: ten corners and
  a flat position. The module's step 0 is that flat position.

## 3. The shape and the terminations

- 18 dB/oct, "passive inductor-based T-network" (AudioThing; Audio Merge: "3rd order"). **[SECONDARY]**
- **[COMPUTED]** from 600 Ω into 600 Ω each step is a third-order Butterworth high-pass: −3 dB at the corner (against
  its pass band), −18 dB at half, −36 dB at a quarter, no peak; the two terminations halve the voltage, a 6 dB
  insertion loss (Audio Merge's "600" mode).
- **[COMPUTED]** other terminations change the shape: from 50 Ω into 10 kΩ the 1 kHz step peaks +15.9 dB at 1.42 × the
  corner; from 50 Ω into 600 Ω, +3.1 dB at 1.24 ×. Real inductors' losses would cap those peaks (not modelled). How
  Tubby's MCI drove and loaded it is **[UNVERIFIED]**: no source.
- The "clicks and crunches" of the steps ([SOS news](https://www.soundonsound.com/news/audio-merge-ktbk-passive-filter))
  **[SECONDARY]**; that they come from a switch changing a network with energy in it is **[UNVERIFIED]**.

## The module: `twosl_dsp/circuit_modules/altec_9069b_high_pass.py`

- The network as it is (§2's circuit), each step's parts from §2, the terminations as the character (600 / 600, §3).
  Each part a trapezoidal companion model prewarped at the step's corner: the corner exact at any sample rate.
- The state is the parts' voltages and currents, kept across a step change: the change's transient is the network's
  own (a design choice standing in for the switch, §3's unverified mechanism).
- Step 0 is flat: the terminations' division alone (the flat position keeping the terminations is **[UNVERIFIED]**,
  chosen so a step and flat have the same pass-band level).

# Grampian Type 636: the studio spring reverberation unit

Written 2026-10-21 for 2sl dub's studio tank (2sl dub SPEC §3.3), from 2sl dub's `references/springs.md` §3, §4 and §5
(compiled 2026-10-21; the sources and tags copied from there), with the dispersion's literature in references/dsp.md.
Tags: **VERIFIED** (primary source read), **SECONDARY**, **COMPUTED**, **UNVERIFIED**, **ASSUMED** (a number we had to
pick), **DESIGN** (a choice), **MEASURED** (the module, rendered).

## Grampian 636 spring reverb (m4l_dev/circuit_modules/grampian_636_spring_reverb.py)

Two springs, 29 / 37 ms, on the kit's parametric spring reverb (references/dsp.md), driven flat (constant current).
Its interface is the kit's spring tank interface (architecture/dsp-blocks.md, "Spring tanks"). Measured
(tests/test_circuit_module_grampian_636_spring_reverb.py, 44.1 kHz): each spring's echoes at its round trip within
0.25 ms (negative); T60 at 300 Hz 2.06 s at the nominal Length (the sheet's 2 s, +3 %), 4.11 s at 4 s; its band to
noise against 1 kHz, third octaves: within ±3 dB from 125 Hz to 5 kHz, 100 Hz −3.3, 6.3 kHz −7.4, 8 kHz −25.1 dB.

## 1. Sources
| key | source | kind |
|---|---|---|
| G636 | Grampian Type 636 Operating Instructions, [scan text at Soundgas](https://soundgas.com/resources/grampian-type-636-operating-instructions/) | PRIMARY (the maker's sheet) |
| SOS | Sound On Sound, ["Lee 'Scratch' Perry & Daniel Boyle: Recording Back Controls"](https://www.soundonsound.com/people/lee-scratch-perry-daniel-boyle-recording-back-controls) | SECONDARY (an interview) |
| P11 | J. Parker, "Efficient dispersion generation structures for spring reverb emulation", 2011 | paper (references/dsp.md) |
| GPV11 | H. Gamper, J. Parker, V. Välimäki, "Automated calibration of a parametric spring reverb model", DAFx-11 | paper (references/dsp.md) |

Why this unit: the dub desks' own springs can't be documented (Tubby's "modified Fairchild" has no model number, tank
or description; 2sl dub springs.md §3). The 636 is documented by its maker and was used on dub records: Boyle feeds
drums through it for Perry, and Perry used it as a distortion, "whacked a guitar through it" (SOS, **VERIFIED**:
Boyle's words, about the 2000s sessions).

## 2. The maker's sheet (G636) **VERIFIED**
- "a pair of mechanical (spring) delay lines with electromagnetic transducers", nominal delays **29 ms and 37 ms**.
- "Reverberation Time: 2 seconds at 300 Hz."
- Reverb path "100 Hz to 6K Hz ±3db"; dry path ±2 dB 35 Hz–20 kHz.
- "The lines are deliberately mismatched at their terminations to promote multiple reflections".
- Driver: a 500 mW "constant current" push-pull amplifier, transformer-coupled, a pilot lamp as overload indicator.
- Mic input up to 72 dB gain, aux input; output 600 Ω, nominal −8 dBm, max +2 dBm; the reverb can be muted from a
  remote switch.
- **COMPUTED**: 2 s at 300 Hz is a loop gain of 0.905 (29 ms) and 0.880 (37 ms) a trip.

## 3. The module
- **Springs**: 29 and 37 ms round trips (that the sheet's "delay" is the echo spacing: **UNVERIFIED**), left and right.
- **Drive**: constant current is flat into the coil: nothing shapes the input. The sheet's band is the tank's own:
  its bottom from the loops' 40 Hz DC blocker (VPA10's, GPV11), which takes more a trip the lower the note; a
  first-order high-pass at 100 Hz in front, tried, put 100 Hz some 3 dB further under the sheet's −3 dB
  (**MEASURED**, so left out).
- **F_C 6000 Hz, ASSUMED**: the sheet's band edge read as the transition frequency (the main chirps end at F_C; above
  it a spring has only the high-frequency chirps, at least 30 dB down, which the model leaves out). P11: an F_C
  "above 5kHz is rarely seen in real spring reverberators", so this is the high end of what springs do.
- **Dispersion**: no Grampian spring has been measured. VPA10's coefficient 0.62 and its 100 sections for its 56 ms
  spring, scaled to each spring's round trip (52, 66; references/dsp.md), spreading each echo's chirp over 17.5 and
  22.2 ms from DC to F_C (**COMPUTED**); the loop's sign negative (VPA10).
- **Decay**: Length is the T60 at 300 Hz, the sheet's point; the nominal Length is the sheet's 2 s.
- **Damping**: no source gives the unit's decay against frequency. **DESIGN** (as the Accutronics module's): an octave
  over F_C at Bright 0 (12 kHz), VPA10's flat loss a trip at Bright +1, F_C / 2 at −1.
- **The mismatched terminations**: no number to model them by; left out (the loops reflect at both ends already).
- **Overload**: the 636's overdriven input (Perry's distortion) is a preamp's, the drive in front of the tank: the
  device's business. The module's own non-linearity is the transducer's tanh, once, on the input.

## 4. The kick
As the Accutronics module's (references/circuits/accutronics-type-9-spring-tank.md §5): a shock moves the frame,
every spring at once, the drive not in the path; **DESIGN**: `kick` goes in before the transducer's tanh, into both
springs; a burst with a peak of 2-4 clips there. What reads as a kick: a few ms of noise with a fast-decaying envelope
plus a low thump (a 40-80 Hz half cycle), once. The sheet gives no recovery high-pass, so the thump is kept short by
the burst itself and the loops' 40 Hz blocker.

## 5. Open
- F_C of the 636's springs (the sheet's band edge stands in), their dispersion, and the decay against frequency.
- Arturia's Rev SPRING-636 models this unit (8 tanks, two germanium preamps; 2sl dub dub.md §5): a listening
  reference only, never ground truth.

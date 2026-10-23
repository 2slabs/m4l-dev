# Accutronics type 9: the long three-spring tank and its current drive

Written 2026-10-21 for 2sl dub's long tank (2sl dub SPEC §3.3), from 2sl dub's `references/springs.md` §2, §4 and §5
(compiled 2026-10-21; the sources and their tags copied from there), with the dispersion's literature in
references/dsp.md. Tags: **VERIFIED** (primary source read), **SECONDARY**, **COMPUTED** (worked from sourced
numbers), **UNVERIFIED**, **ASSUMED** (a number we had to pick where no source gives one), **DESIGN** (a choice),
**MEASURED** (the module, rendered).

## Accutronics type 9 spring tank (twosl_dsp/circuit_modules/accutronics_type_9_spring_tank.py)

Three springs, 33 / 37 / 41 ms, on the kit's parametric spring reverb (references/dsp.md), each with its own chirp;
the guitar amp's current drive in front (§3); its recovery high-pass after (§3). Its interface is the kit's spring
tank interface (architecture/dsp-blocks.md, "Spring tanks"). Measured (tests/test_circuit_module_accutronics_type_9_spring_tank.py,
44.1 kHz): each spring's echoes at its round trip within 0.25 ms (the autocorrelation's largest magnitude, negative:
the loop's sign); T60 at 1 kHz 3.36 s at Length 3.4 s, 1.49 s at 1.5 s; its band to noise against 1 kHz, third
octaves: 125 Hz −8.3, 200 Hz −6.2, 315 Hz −1.0, 2 kHz −0.6, 4 kHz −3.6, 4.5 kHz −6.7, 5 kHz −11.6, 6.3 kHz −29.0 dB.

## 1. Sources
| key | source | kind |
|---|---|---|
| AP | Amplified Parts, ["Spring Reverb Tanks Explained and Compared"](https://www.amplifiedparts.com/tech-articles/spring-reverb-tanks-explained-and-compared) (read in a browser 2026-10-21 for 2sl dub; plain fetches are refused). Quotes "Vintage Accutronics specifications" | SECONDARY (a retailer reproducing the maker's spec) |
| ARP | [amprepairparts.com, Korean-made Accutronics numbering](https://www.amprepairparts.com/reverb_numbering.htm) | SECONDARY |
| ESP | Rod Elliott, ["Care and Feeding of Spring Reverb Tanks"](https://sound-au.com/articles/reverb.htm) | SECONDARY (engineer) |
| PB09 | J. Parker, S. Bilbao, ["Spring reverberation: a physical perspective"](https://www.dafx.de/paper-archive/2009/papers/paper_84.pdf), DAFx-09 | paper (references/dsp.md) |
| GPV11 | H. Gamper, J. Parker, V. Välimäki, ["Automated calibration of a parametric spring reverb model"](https://www.dafx.de/paper-archive/2011/Papers/39_e.pdf), DAFx-11 | paper (references/dsp.md) |
| VPA10 | V. Välimäki, J. Parker, J. S. Abel, "Parametric spring reverberation effect", JAES 58(7/8), 2010 | paper, paywalled, not read: quoted by GPV11 and Parker 2011 |

## 2. The tank: the code, the springs, the decay
- **The code.** In the Accutronics code the first digit is the tank type: **type 4 is a long tank with two springs**;
  the long three-spring tank is **type 9** (AP; ARP). The Fender Twin Reverb's 4AB3C1B is two-spring; its
  three-spring twin is the **9AB3C1B**, which AP says can replace it. **VERIFIED** against AP's table, **SECONDARY**
  as a source:

  | digit | meaning | 9AB3C1B |
  |---|---|---|
  | 1 | type | 9: long (16.25"), 3 springs |
  | 2 | input impedance at 1 kHz | A: 10 Ω |
  | 3 | output impedance at 1 kHz | B: 2,575 Ω |
  | 4 | decay | 3: long, 2.75–4.0 s |
  | 5 | connectors | C: input insulated, output grounded |
  | 6 | lock | 1: none |
  | 7 | mounting | B: horizontal, open side down |

  ARP: each long spring "consists of two springs joined in the middle". **SECONDARY**.
- **The springs' delays.** AP: "Vintage Accutronics specifications list the following delay times per spring":
  short 33 ms, medium 37 ms, long 41 ms, in the type 9 (3 springs) column. **SECONDARY**. That each is the echo
  spacing (the round trip, PB09's T_D) and not one trip: **UNVERIFIED** (for 16 cm springs PB09's formula gives
  T_D in this range, 2sl dub springs.md §2). The module: 33, 37, 41 ms round trips; panned left, both, right
  (**DESIGN**: AP's listening note, three springs give "a more smoothed out flutter with a bigger, fuller sounding
  reverb effect and more lows").
- **The decay.** Long, 2.75–4.0 s (AP; ARP; ESP). **COMPUTED**: the class's middle, 3.4 s, is the module's
  NOMINAL_LENGTH_S. The frequency it holds at is not given: **ASSUMED** 1 kHz (where the code's impedances are
  quoted). Length is the T60 there.

## 3. The drive and the recovery
- **Drive.** AP's design notes: drive the input coil from a current source (or a voltage source through a resistor
  more than 5× the coil's 1 kHz impedance) whose output rises 6 dB/oct ("an input high-pass filter to compensate for
  the input coil's inductive reactance"); avoid DC in the coil. ESP prefers current drive too, rates the 8 Ω coil at
  28 mA RMS, and gives a usable tank band of about 200 Hz to 6 kHz, "very limited above ~5kHz". **SECONDARY**. The
  Twin Reverb drives its tank from a 12AT7 through a small output transformer; its values are not read.
  - The module: a first-order high-pass in front of the springs, +6 dB/oct below its corner. **ASSUMED** corner
    200 Hz (ESP's band's bottom); the Twin's own corner is open. Measured: the coil's current is the one-pole's
    response within 0.02 dB at 50, 100, 200 Hz and 1 kHz.
- **Recovery.** AP: the tank gives 1–5 mV; recover with a flat preamp of high input impedance, and "an output
  high-pass filter with a 50 Hz to 100 Hz cutoff to lessen the effects of rumble when the unit is mechanically
  shocked". **SECONDARY**. The module: one pole at 70.7 Hz on each side, the range's geometric middle (**DESIGN**).

## 4. The dispersion: a stand-in
No Accutronics spring has been measured in the literature we have. The nearest: PB09 measured a **Leem Pro KA-1210**,
three springs, helix length 16.3 cm (a 16" tank like the type 9), and GPV11 fitted its spring 1. **VERIFIED** (PB09
Table 2; GPV11 Table 1):
- PB09's springs' F_C, **COMPUTED** with its eq. (4): 4.9, 4.7, 4.5 kHz; GPV11's fit of spring 1: 4216-4300 Hz.
  The module: **F_C 4500 Hz, ASSUMED** (between the two).
- VPA10's calibration of spring 1 (GPV11 Table 1): T_D 56 ms, M_low 100, a 0.62, g_lf −0.8 (negative). The module:
  a = 0.62, the loop's sign negative, and each spring's sections in proportion to its round trip (PB09: the delay
  curve scales with the wire's length, as T_D does; references/dsp.md): **59, 66, 73**, spreading each echo's chirp
  over 26.4, 29.5, 32.7 ms from DC to F_C (**COMPUTED**, the reference's eq. 4).
- The loops' damping: no source gives a tank's decay against frequency. **DESIGN**: an octave over F_C at Bright 0
  (9 kHz, 0.8 dB a trip more at F_C than at 1 kHz), VPA10's flat loss at Bright +1, F_C / 2 at −1.
- Not modelled: the high-frequency chirps (C_hf, "at least 30 dB below", Parker 2011), VPA10's delay modulation
  (the echoes' growing diffusion) and its equalisation filter.

## 5. The kick
Kicking a tank is a dub sound (2sl dub dub.md §1.4) and a nuisance: AP's recovery high-pass is there "to lessen the
effects of rumble when the unit is mechanically shocked"; ESP warns a bump can make "the magnets touch the pole
pieces" in a badly mounted tank. **SECONDARY**. So a shock gives a loud low rumble, a broadband burst into every
spring at once (the frame moves) and, at its peak, the magnets meeting the pole pieces: a hard clip. That reading is
**UNVERIFIED** as physics; no paper models a kicked tank. **DESIGN** (2sl dub springs.md §5): the module's optional
`kick` input goes in after the drive (the coil is not in the path of a shock), before the transducer's tanh (where a
burst with a peak of 2-4 clips), into every spring. What reads as a kick: a few ms of noise with a fast-decaying
envelope plus a low thump (a 40-80 Hz half cycle), once. The recovery high-pass and the loops' 40 Hz blocker keep the
thump short.

## 6. Open
- The Twin Reverb's (or any type 9 driver's) high-pass corner; the exact Accutronics delay table (AP is a retailer's
  copy) and whether "delay" is one trip or two.
- F_C of an Accutronics spring (the Leem Pro's stands in), and its decay against frequency.

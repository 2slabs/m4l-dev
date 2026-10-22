# Buchla 208 (Music Easel): the spring reverb, card 12's driver and the tank as 2sl gate had it

Moved here 2026-10-21 from 2sl gate's `references/buchla-208-reverb.md` (gate commit 68bfd110; gate kept its own copy
and its own code until 0.6.0 took the spring out), with the tank's numbers from gate's `src/gate_dsp.py` and the kick from 2sl dub's
`references/springs.md` §5. Tags: **[VERIFIED]** read in the source, **[SECONDARY]**, **[INFERRED]** our reading,
**[UNVERIFIED]**, **[DESIGN]** a choice, **[MEASURED]**. `fetch-buchla-208-spring-reverb-sources.sh` (here; moved from
gate) fetches the three sources (2026-10-21, sha256 in that script); each source has one page, so a place in it is named by its label.

## Buchla 208 spring reverb (m4l_dev/circuit_modules/buchla_208_spring_reverb.py)

Card 12's driver (§2) into a two-spring tank on the kit's dispersive-loop spring tank (references/dsp.md), with gate's
numbers (§3), so it renders gate's spring: tests/test_circuit_module_buchla_208_spring_reverb.py holds the module to
gate's own spring code, copied verbatim (2026-10-21: residual −316 dB at 44.1 kHz, identical at 48 kHz, through
Init, a long bright tank, a Stop mid-tail and a short dark one). Its interface is the kit's spring tank interface
(architecture/dsp-blocks.md, "Spring tanks").

## 1. The sources
1. **Buchla & Associates, schematic B2080-12A, "Model 208 PSS, Output", 8-17-73** (card 12; drawn by CJ; revision
   3/74 "change R15, 30, 31; short Q, N; route reverb return to terminal pts"). Scan courtesy Magnus Danielson, on
   fluxmonkey.com's Historic Buchla 208 page ("Output [8/17/73]"). PRIMARY.
2. **Rod Elliott, "Spring Reverb" (Elliott Sound Products, sound-au.com/articles/reverb.htm)**, Table 1 "Type 4
   Accutronics Input Coil Data" and the section on voltage drive. SECONDARY (Accutronics' 1 kHz data plus his own
   inductance column).
3. **Roman Sowa, "Boops Card 12 Replacement" (modularsynthesis.com)**. SECONDARY (a repairer who has the original
   card on his bench).

What the schematic shows (source 1) [VERIFIED]:
- **Driver:** IC2 (LM380, "IC2,3,4 LM380") drives the tank's input coil through **C2, 390 µF, 12 V** to pin
  ⟨5⟩ "REV DRIVE"; the coil's other end is N (ground). Voltage drive into a coupling capacitor: no series resistor.
  Source 3 agrees: "Don used an LM380 to drive the reverb with voltage".
- **Recovery:** IC1 (R4136) section 1, non-inverting, the tank's output coil at its + input; feedback **R15 220 k**
  with **100 pF**; to ground **R16 10 k** in series with **C3 4.7 µF**. Gain 1 + 220k/10k = 23 above 1/(2π R16 C3)
  = **3.39 Hz**, falling to 1 below 1/(2π (R15 + R16) C3) = 0.147 Hz (a shelf, not a high pass); the 100 pF across
  R15 rolls the gain off from 1/(2π R15 100 pF) = **7.23 kHz**. Out at ⟨12⟩ "REV SIG OUT".
- The tank itself is drawn as a symbol (input coil, spring, output coil); its make and type are not on the sheet.

The tank's input coil (source 2, and an inference):
- Table 1, Type 4 tanks, coil code **A: 8 Ω at 1 kHz, 0.81 Ω DC, 28 mA RMS, 1.27 mH** [SECONDARY].
- Source 2 on voltage drive: a low-resistance coil on an amplifier needs an isolating capacitor, "fairly large (at
  least 470 µF for an 8 ohm coil)".
- **[INFERRED]** The Easel's coil is the 8 Ω one: the LM380 is a power amplifier for 8 Ω speakers, and a 390 µF
  coupling capacitor is the size source 2 gives for an 8 Ω coil (a 150 Ω or higher coil would need a fraction of it).
  No source names the 208's tank.

## 2. The driver: a series R-L-C [DERIVED from §1]
The driver's coupling capacitor and the coil are a series R-L-C: the coil current against the coil driven straight
(V / (R + sL)) is H(s) = (s²LC + sRC) / (s²LC + sRC + 1) = 1 − 1 / (s²LC + sRC + 1), resonant at
f0 = 1 / (2π √(LC)) = **226 Hz**, Q = √(L/C) / R = **2.23**: **+7.8 dB at 226 Hz**, 0 dB by 3 kHz (+0.05 dB),
−9.5 dB at 100 Hz, −27.8 dB at 20 Hz, falling 6 dB/oct below (the sRC term). Source 3's "the reverb on the Easel is
pretty lousy" and the "muddy" reports fit a bump at 226 Hz. It acts once, on what goes into the tank. The module
runs it as the kit's state-variable filter: the input less its low-pass at f0, Q (tested against these figures).

The recovery's corners are not the low end: its 3.39 Hz shelf is far below the driver's 226 Hz, and its 7.23 kHz
roll-off sits inside the loops' low-pass range; the module leaves the recovery flat, as gate did.

## 3. The tank, as gate had it
- Two springs, **33.7 ms** (left) and **41.3 ms** (right), each a loop read at its round trip [UNVERIFIED: gate's
  file gives no source; they sit near the Accutronics 33 / 41 ms springs, 2sl dub springs.md §1].
- Eight first-order all-passes of **0.62** a loop (gate's). Their group delay spreads an echo over 0.73 ms between DC
  and Nyquist at 44.1 kHz [MEASURED]: a dispersive comb, not a spring's tens of ms of chirp (references/dsp.md).
- The loops' low-pass 2500 Hz × 4^Bright, the decay 10^(−3 T / Length) a trip, Length 0.3-6 s in gate, Init 2 s.
- A one-pole DC blocker in each loop at 3.69 Hz [MEASURED by gate, 2026-10-21]: where it costs the longer loop's
  first tooth (24.2 Hz) 0.1 dB a trip; with none, gate's Cortini drift preset's springs rang −34.7 dB below 20 Hz
  against the output's peak, at this corner −48.3.
- A tanh where each loop writes back. Stop mutes the loops for 60 ms (longer than the longest loop), with the driver
  emptied.

## 4. The kick
Kicking a tank is a dub sound (Manasseh: "whacking a spring reverb with a large stick", 2sl dub dub.md §1.4) and a
nuisance (Amplified Parts' recovery high-pass at 50-100 Hz is there "to lessen the effects of rumble when the unit is
mechanically shocked") [SECONDARY]. Our reading [UNVERIFIED as physics; no paper models a kicked tank]: the frame
moves, so every spring is excited at once and the coil is not in the path; a hard enough knock clips where the
magnets meet the pole pieces. **[DESIGN]** The module's optional `kick` input goes into every loop after the driver,
where the loop writes back through its tanh: a burst with a peak of 2-4 clips there. What reads as a kick: a few ms of
noise with a fast-decaying envelope plus a low thump (a 40-80 Hz half cycle), once; the loops' DC blocker and the
burst's own shortness keep the thump from ringing on.

## 5. Open
- The 208's tank: make, type, its springs' delays. Gate's 33.7 / 41.3 ms are unsourced.

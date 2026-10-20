# The Mu-Tron Bi-Phase and the phasers it is compared with: sources, the circuit as drawn

Written 2026-10-20 for the kit's phaser block ("a bi-phase ... absolutely freaking nail that water phaser sound",
user, 2026-10-20); the circuit behind `m4l_dev/circuit_modules/mutron_bi_phase.py` (the last section says what the
module takes from here). `references/fetch-phaser-diffusion-sources.sh` downloads every source below into
`references/phaser-diffusion-sources/` (not in git) and checks it is the copy this was read from (sha256 / a phrase).

Tags: **[VERIFIED]** read in the source itself this session (file named, page or sheet given). **[DERIVED]** computed
by us from verified inputs; the method is given. **[SECONDARY]** a credible secondary source read in full or in the
part cited. **[UNVERIFIED]** only seen as a search-engine excerpt, a memory, or an inference; do not build on it.
Page numbers are the PDF's printed page; "sheet" is the schematic's own sheet.

## 0. The one thing to know about provenance

No Musitronics-era (1974) Bi-Phase schematic, service manual or Beigel patent was found. The only real schematic
is the **ARP Instruments** one, from after ARP bought Mu-Tron: sheets "BD 1, Bi-Phase" (drawing 77204) and "BD 3,
Bi-Phasor" power supply (drawing 77206, drawn W. J. Ames, **1/11/79**, rev 1). Everything under §2 is that
drawing. Whether the 1974 unit differs (lamp instead of LED, other values) is open (§7). The "Bi-Phaser" stage
drawing in the same archive (4558 + BF245A FETs, 47 nF) is a hobbyist's FET variant, **not** the Bi-Phase.

## 1. The sources

| file (in `references/phaser-diffusion-sources/`) | what it is | URL |
|---|---|---|
| arp-bi-phase-schematic-page1.gif | ARP sheet 1 of drawing 77204: input buffers, S1 Phasor B input, output mixers, both sweep generators, pedal input | https://experimentalistsanonymous.com/diy/Schematics/Phasers/Mu-Tron%20Bi-phase%20page%201.gif |
| arp-bi-phase-schematic-page2.gif | sheet 2: the two six-stage phase shifters and the LED drivers (cropped at the bottom edge by the scan) | same folder, `...page 2.gif` |
| arp-bi-phase-schematic-page3-power.gif | drawing 77206: the power supply | same folder, `...page 3.gif` |
| diy-fet-bi-phaser-stage.gif | hobbyist FET "Bi-Phaser" (not the original) | same folder, `Mu-Tron Bi-Phase Phase Stage.gif` |
| mutron-biphase-owners-manual.html | the owner's manual, full text (Mu-tron Inc., Lexington MA), a PDF link on the page | https://soundgas.com/resources/mutron-biphase-owners-manual |
| darabundit-univibe-dafx19.pdf | Darabundit, Wedelich, Bischoff, "Digital Grey Box Model of the Uni-Vibe Effects Pedal", DAFx-19 | https://ccrma.stanford.edu/~champ/files/DAFx2019_paper_31.pdf |
| geofex-phase-shifters.html | R. G. Keen, "The technology of Phase Shifters and Flangers", Geofex 1999 | http://www.geofex.com/Article_Folders/phasers/phase.html |
| moog-mf103-manual.pdf | Moogerfooger MF-103 12-Stage Phaser manual | https://www.fullcompass.com/common/files/86275-MF103SManual.pdf |

Not fetchable here (HTTP 403 / DNS): Perfect Circuit's Mu-Tron history, effectsdatabase.com, Soundgas's product
feature, FreeStompBoxes' schematic thread, ElectroSmash, Valhalla's blog. Facts known only from their search
excerpts are marked [UNVERIFIED].

## 2. The circuit as drawn (ARP 77204 / 77206) [VERIFIED reading of the scans; the inferences are tagged]

### 2.1 Stage count, topology, values (sheet 2)
- **Two independent phasors, six stages each** (A: Z1A–Z3B, B: Z4A–Z6B), 12 op-amp sections. Also the manual:
  "two independent six-stage phase shifters" (manual, first paragraph); manual, "Use with 1 instrument": "This gives
  you a 12-stage phase shifter" (A into B).
- **Each stage** (identical in all twelve): an op-amp with R 4.7 kΩ from the stage input to the inverting input and
  4.7 kΩ from the output back to it; a **6.8 nF** (".0068", 10 %) from the stage input to the non-inverting input;
  from the non-inverting input to ground **220 kΩ in parallel with one photocell**. The signal into stage n+1 is
  stage n's output. Last stage output goes through C12 / C28 0.47 µF to the phasor's output.
- **[DERIVED] Transfer function.** V+ = Vin · sRC/(1 + sRC), Vout = 2 V+ − Vin, so
  `H(s) = (sRC − 1) / (sRC + 1)`, unity magnitude, −1 at DC, +1 at HF: a first-order all-pass (Zavalishin eq. 2.11,
  allpass-and-diffusion.md §1) with `R = R_ldr ∥ 220 kΩ`, `C = 6.8 nF`, corner `f = 1/(2π R C)`. The stages are
  **matched** (same C, same R_fixed, six cells in one package); contrast the Uni-Vibe (§5).
- **[DERIVED] The corner per cell resistance** (the 220 kΩ in parallel caps the dark end):
  | R_ldr | ∞ | 1 MΩ | 100 kΩ | 30 kΩ | 10 kΩ | 3 kΩ | 1 kΩ |
  |---|---|---|---|---|---|---|---|
  | f_c = 1/(2π (R_ldr ∥ 220 k) 6.8 nF) | 106 Hz | 130 Hz | 340 Hz | 887 Hz | 2.45 kHz | 7.9 kHz | 23.5 kHz |
  So the lowest the stage can go is 106 Hz; the top depends on the cell's on-resistance, which no source gives.
- **[DERIVED] Notch positions with equal stages.** Six equal stages give phase 6π − 12 atan(ω/ω_c); added to an
  equal-level dry signal the notches are where that equals an odd multiple of π: ω/ω_c = tan 75° = 3.73, tan 45° = 1,
  tan 15° = 0.268, three notches 3.73× (1.9 octaves) apart, centred on the stage corner. The mix is not equal level
  (§2.4), so they are partial, not full, notches.
- **Photocells.** The drawing shows each phasor's six cells as "PM3A–F" / "PM4A–F" (one multi-cell part per phasor,
  pins 3–10, commons 4 and 9) lit by one LED "PM3" / "PM4" (LED pins 1, 2). So **an LED + six matched LDRs in one
  light-tight part, not a lamp**, in this ARP revision. No part number or cell curve is given anywhere found.
  [UNVERIFIED] Mu-Tron called it a "photo-mod": Mu-tron's own site: Phasor II "uses same 'photo-mod' circuit as
  Bi-Phase" (https://mu-tron.com/?p=1137, read; the page does not say what a photo-mod is).

### 2.2 The LED drivers (sheet 2, bottom)
- A: the sweep voltage (J1-6) goes through R97 47 kΩ to an op-amp (Z7A) driving an NPN (Q1, marked "C1852", read as
  2SC1852) whose emitter feeds the LED; R98 220 kΩ, a diode CR 16, R99 10 kΩ + diode CR9 + R100 68 kΩ, a 220 Ω
  (R101) and a 1 kΩ trim (R129) shape the current. B (Q2 / Z7B, from J1-5) is the same with R102 47 kΩ, R130 / R131
  10 kΩ trims, R110/R111 2.2 kΩ, R112 47 kΩ, R113 3.6 kΩ, R114 620 kΩ, R115 10 kΩ + CR, R117 220 kΩ (cut off by the
  scan edge).
- **[DERIVED, UNVERIFIED in detail]** a voltage-to-current converter with a diode break-point network and trims: the
  sweep voltage → LED current → cell resistance → stage corner, each link a monotone map, with the diode network
  bending the curve (what it linearises was not traced). Depth (a panel control: "continuously varies the width of
  the frequency range these dips are swept over", manual, Depth Control) must be the sweep amplitude into this
  network; the trims set the span. Not traced, so the Hz range of the sweep is **not known** (§7).
- The **sweep pedal** (C-100 "photoelectric foot controller", mu-tron.com/?p=1137) is a photocell pedal that "puts out
  0-5 volts peak-to-peak" (Muzines, "Modifying the Mu-Tron Bi-Phase", https://www.muzines.co.uk/articles/modifying-the-mu-tron-bi-phase/12300,
  read) into the 5-pin DIN; "The green wire in the DIN plug is the control voltage input for the phasor" (same
  article) = the CV the drivers take. The drawing: pedal in (J6-2) → Z6A buffer (3.9 kΩ in, 1 MΩ to ground) → Z6B
  inverting stage (39 kΩ / 39 kΩ) and R125 10 kΩ trim → the sweep-select switches.

### 2.3 The sweep generators (sheet 1, bottom) 
- **Manual [VERIFIED]:** "Each control smoothly and continuously varies the sweep rate-from 0.1Hz (10 seconds per sweep
  cycle) to 18Hz"; "SHAPE CONTROL: ... a rocker switch ... between sine-wave and square-wave sweep"; the manual's
  "square-wave sweep jumps the phasing from one extreme of the sweep to the other. At moderate rates with the
  'Feedback' control turned up, square-wave phasing resembles an echo repeat." Two generators, both with Rate / Shape;
  Gen 1's rate can be the Rate knob or the pedal (rate switch "Ped"/"Man", S2); at "Ped" with no pedal "the Sweep
  Generator operates at a very low rate".
- **Sources of each phasor's sweep (manual):** A: Gen 1 or Pedal (S5). B: Gen 1, Gen 2 or Pedal (3-position rotary).
  **Sweep Sync** (S7): Norm or **Rev**: with both phasors on the same source, Rev makes B sweep down while A sweeps up
  ("the basic means of generating stereo phasing effects"); Norm gives "double-depth". (On the drawing: an inverting
  op-amp, Z15B, with 39 kΩ ×2, switched in by S7.) The manual says external control "requires a slight modification":
  the synth interface is not a stock jack (Muzines: Gen 1's output at a pad near the Shape switches; the DIN's CV in).
  The manual: "The Bi-Phase may use a control voltage from the synthesizer (such as an ADSR output) to drive the
  sweep, and Sweep Generator 1's output voltage is made available as a low frequency oscillator while an external LFO
  sweeps either or both halves of the Bi-Phase. This facility requires a slight modification to the unit."
  [VERIFIED]
- **Circuit [DERIVED from the drawing, not traced]:** a triangle / square core of the classic kind: a comparator with
  hysteresis (Z12B, 39 kΩ / 33 kΩ), an integrator (Z13B, C33 0.47 µF) with its input switched in sign by a diode
  bridge (CR2–5) fed from the rate op-amp (Z12A; R135 25 kΩ Rate pot via R65 47 kΩ, R67 390 kΩ, R68 120 Ω, R76 10 kΩ
  trim); the integrator slope ∝ the rate voltage. The "sine" is the output stage Z15A (R77 4.7 kΩ, R128 22 kΩ, C36
  0.47 µF in the Shape path) and the Shape switch S3 chooses between it and the square. Generator 2 (Z14A/B, C34, C35,
  R90–R94, R136 25 kΩ) is the same. Whether "sine" is a true sine or a rounded triangle was not determined.

### 2.4 Mix, feedback, bypass, levels (sheets 1–2)
- **Input** (each phasor): J1/J2 → 0.047 µF → 390 kΩ to ground → 3.9 kΩ + 30 pF (RF filter) → op-amp Z8A (390 kΩ ∥
  0.1 µF in its feedback; read as a buffer, the gain not resolved from the scan) → R4 4.7 kΩ → Z8B. Manual: input
  impedance 180 kΩ (parallel mode) / 390 kΩ (single mode), min. (mu-tron.com's page gives "300k ohms minimum" for the
  same unit; the manual wins.) **S1** (Phasor B input): In A (a Y-cord), Out A (A's output into B: series), In B
  (separate input).
- **Feedback [DERIVED]:** the phasor's output node J1-1 is across a **10 kΩ pot R133 whose wiper feeds the "+" side of
  the phasor's input stage Z8B** through R7 6.2 kΩ (R6 4.7 kΩ ∥ C5 3.3 nF to ground on that node, a 18 kHz corner).
  The input stage is a differential amp: the dry signal in on the "−" (gain −1, R4 = R5 = 4.7 kΩ), the feedback on
  the "+" with gain 1 + R5/R4 = 2 and the 6.2/4.7 divider, so **at most 0.86 of the phasor's output is fed back,
  non-inverted**, i.e. positive feedback with loop gain ≤ 0.86 × the stages' phase: peak height at most about
  1/(1 − 0.86) = 7.1 → +17 dB over the no-feedback response at the frequencies where the six stages total
  0°/360°. (The 0.47 µF output coupling and the pot give a bass roll-off in the loop near 34 Hz. CORRECTED 2026-10-20, §8: J1-1 is also loaded by R26 4.7 kΩ into Z9B's virtual ground, so the corner is ~106–140 Hz.) The manual: "as the
  'Feedback' control is turned up, electronic feedback is added, creating positive peaks in the frequency response
  in between the cancellations" [VERIFIED]; at full feedback "the Bi-Phase will pick out the individual notes and
  harmonics of a chord as it sweeps up and down" [VERIFIED].
- **Output mix [DERIVED]:** the phasor's output goes through Z9B (inverting, R26 4.7 kΩ in, R27 4.7 kΩ ∥ C13 1 nF
  feedback = gain −1, a 34 kHz roll-off), then a photocell **PM1** (type "PE613-12" as read) in series with a 10 kΩ
  variable resistor R123, C14 0.15 µF and R29 4.7 kΩ, into the "+" input of the output buffer Z9A; the dry (Z8A's
  output) arrives at the same node through **R31 12 kΩ**; nothing else loads the node (C15 47 pF), so the node is a
  passive weighted sum of wet and dry. PM1's LED is driven from the foot switch line (J6-3, R30 2.7 kΩ). **So the
  foot switch is an opto-isolator in the wet path**: lit = wet passes; unlit = wet cut (its dark resistance is
  large), dry only. The manual's "The phasor circuits will not operate unless the foot switch unit ... is plugged in"
  [VERIFIED] agrees. [UNVERIFIED] reading R123 as a wet-level trim.
- **Output:** Z9A as a follower, R32 560 Ω, C16 10 µF (manual: output impedance 600 Ω, unbalanced). Manual: insertion
  loss "less than 1db"; bypass response 20 Hz–20 kHz ±1 dB; signal-to-noise "Typically 86db below 2V input"
  [VERIFIED]. (Mu-tron's site lists the same unit's response as ±2 dB and says each phasor alone takes "at least 4V RMS
  with no feedback", both in series "at least 2V RMS at 50% feedback and ... 1V RMS at 100% feedback": the headroom
  falls as the feedback's resonance gain grows, consistent with the +17 dB above.)
- **Opto-coupled distortion or level behaviour:** nothing found says the LDR stage distorts. In this drawing the
  cell sits at the "+" input node of a high-Z op-amp, so the signal across a cell is the full stage input (up to the
  4 V RMS above): a CdS cell's resistance is signal-level dependent to a degree [UNVERIFIED; a general property
  noted in the kit's vactrol note for the VTL5C3/2, no Bi-Phase measurement exists]. [SECONDARY, UNVERIFIED excerpt]
  Soundgas / Perfect Circuit: Beigel and Newman chose photocells for dynamic range, the first results "were too
  good" (too clean), and a feedback path was added to emphasise the peaks.

### 2.5 Power supply (drawing 77206)
- 117 V (115 V AC, 60 Hz, 15 W per the manual) → fuse F1 1 A, switch S8 → transformer T1 → bridge CR11–14 (1N4002) →
  C37 / C38 470 µF 35 V (split) → an **RC4195 dual-tracking regulator (Z17)** → **±15 V**, decoupled by 47 µF 16 V +
  0.01 µF per rail. All op-amp sections are supplied ±15 V. Lamp supply: none (LEDs). [VERIFIED reading of sheet 3.]

## 3. What gives the "watery" sound (nothing here says "watery"; every link is inference)

- **No source found calls the Bi-Phase "watery" or "liquid".** The sources say: smooth, deep, defined, "chewy"
  ([UNVERIFIED] Soundgas excerpt), and "pseudo-ring modulation" at high rates with feedback up (manual, Rate
  Control, [VERIFIED]).
- **Many stages + feedback** [VERIFIED mechanisms, our reading]: six matched all-pass stages give three notches spaced
  3.73× apart, plus resonant peaks between them from the ≤ 0.86 positive feedback; two phasors in series, 12 stages,
  six notches ("the deepest phasing available", manual). More stages and more feedback = more, sharper, moving
  structure in the spectrum.
- **Optical lag / asymmetric response** [SECONDARY, on the Uni-Vibe, not measured on the Bi-Phase]: Darabundit et al.
  (p. 6, §4.2): the measured Uni-Vibe LDR curves "have increasing asymmetry as intensity increases due to the LDRs
  having different turn-on and turn-off times. The increasing asymmetry is a result of lamp varying its brightness more
  rapidly as intensity is increased"; each of its four LDRs differed (their Table 1). Eventide's article
  ([UNVERIFIED excerpt]): cap values "picked seemingly arbitrarily", "unevenly spaced notches". For the Bi-Phase
  the cell time constants are unknown; the kit's VTL5C3/2 model has attack ≈ 3–12 ms and release tens to 250 ms
  (vactrol-and-lpg.md §4), which at the Bi-Phase's top rate (18 Hz = 55 ms per cycle) would round and skew the sweep
  heavily; whether the "photo-mod" is that slow is **unknown**.
- **Sweep shape**: the Bi-Phase's own manual: sine "smoothly-swept"; square "jumps the phasing from one extreme ... to
  the other ... resembles an echo repeat" with feedback [VERIFIED]. The depth control sets the frequency range of the
  sweep, "At lower speeds, the smoothest-sounding phasing is found at about '8'; as the rate is increased, it will
  probably be necessary to reduce the depth somewhat to maintain a smooth-sounding phasing effect" [VERIFIED].
- **Two independent sweeps**: Gen 1 slow at max depth/feedback with Gen 2 "moderately fast (about '6')" at 50 % on the
  other phasor; or both between "3" and "4" at 80 % so "you will hear a complex sweep that defies description"
  (manual) [VERIFIED]. And **Rev** sync for stereo swirl.
- **Square sweep at 18 Hz with feedback** is the manual's pseudo-ring-mod; these are the settings to match against a
  recording when the kit's phaser exists (match-targets).

## 4. How it relates to the kit's vactrol model (vactrol-and-lpg.md, 2sl-gate)

- **Same physics, different part, different circuit.** A vactrol is an LED (or lamp) lit by a current and a CdS
  LDR; the kit's model is LED current → resistance (`Rf = A / If^1.4 + B`, fit to the **VTL5C3/2**: 56 kΩ at 1 mA, 1.45 kΩ
  at 40 mA) followed by a state-dependent one-pole (attack ≈ 1–12 ms, release 10–250 ms+). The Bi-Phase's cells are in the
  same family (LED + CdS) but a **six-cell module**, ratios unknown; nothing identifies a VTL part. Its drive
  (27A/Q1, a V-to-I converter into one LED) is a different front end from the Buchla control circuit.
- **What reuses:** the resistance-from-current law and the attack/release memory, as a block that gives R_ldr; here it
  feeds `R = R_ldr ∥ 220 kΩ` into a 6.8 nF all-pass corner (§2.1) instead of the 292's lowpass gate network. One LED
  → six LDRs: **one state, six identical resistances** (matched), so one vactrol state for six stages.
- **What does not:** the model's constants are the VTL5C3/2's; the Bi-Phase's module is unmeasured. The Uni-Vibe
  paper measured a real unit's four LDRs (Table 1 differs per LDR; time constants asymmetric, 3-D wavetable of
  speed × intensity): that is the only measured LDR-phaser data found. [DERIVED] The Bi-Phase's top rate (18 Hz)
  and a ~250 ms release are incompatible if the sweep is to reach full depth: so either the module is much faster
  than a VTL5C3/2 or the high-rate sweeps are visibly reduced in depth.

## 5. Other famous phasers, for contrast

| phaser | topology (source) | stages | sweep element |
|---|---|---|---|
| **Uni-Vibe** (Shin-ei, late 1960s) | "each first-order section is a discrete component phase splitter (no operational amplifiers)"; each stage a Darlington emitter follower with inverting (collector) and non-inverting (emitter) legs into an RC bridge, **unmatched** capacitors per stage; a high-shelf character from a block capacitor and unequal leg gains (Darabundit et al., abstract, §3, Fig. 3, Fig. 6 caption "α = 1.0009, β = 1.11, R0 = 409.7 kΩ" for stage 1) [VERIFIED] | 4 | one LFO-driven incandescent lamp lighting four CdS LDRs; LFO a phase-shift oscillator, 0–7.6 Hz on the pedal (§2.1, p. 3) [VERIFIED] |
| **MXR Phase 45 / 90 / 100** | "variant of the elementary stage ... the original signal to the inverting input, the RC split into C / variable R at the non-inverting input"; "Phase 45 ... two phase delay stages, and only one notch"; "four stages (such as the MXR Phase 90, Univibe) or six stages (MXR phase 100)" (Geofex) [SECONDARY, read] | 2 / 4 / 6 | JFET channel resistance (Geofex says "the variation of the drain/source resistance of JFETS like the MXR") |
| **Electro-Harmonix Small Stone** | an OTA as the variable resistance, "an internal darlington buffer in one of the OTA IC's" as the next buffer (Geofex) [SECONDARY, read]; stage count not in the part read | [UNVERIFIED: 4] | OTA bias current |
| **Moog Moogerfooger MF-103** | "6-stage/12-stage voltage-controlled Phaser" with a "RESONANCE" control; LFO 0.01–2.5 Hz (LO) or 1–250 Hz (HI), "250:1 range" (manual) [VERIFIED]; circuit not given | 6 / 12 | [UNVERIFIED: OTAs] |
| **Mu-Tron Phasor** (1970s) | "transconductance amps" (mu-tron.com/?p=1137, read); the Phasor II "photo-mod" like the Bi-Phase | [UNVERIFIED] | OTA (Phasor); LED+LDR (Phasor II) |
| **Mu-Tron Bi-Phase** | §2: op-amp first-order all-passes, matched, LED+LDR | 6 + 6 | one LED per six-cell module |

Geofex on why more stages give more notches: "Each pair of stages adds one more notch." The Geofex page also states the
Uni-Vibe "has the implementation closest to the elementary phase shift stage". JOS (Phasing,
`jos-phasing.html`): "typical commercial phase shifters have been observed to implement nonuniformly spaced notches";
"we will therefore define a phaser as any linear filter which modulates the frequencies of a set of non-uniformly
spaced notches" [VERIFIED]. (Equal stages, as in the Bi-Phase, are still non-uniform in frequency: 0.268 : 1 : 3.73.)

## What this suggests for the kit (inference, not source)

- **Technique vs circuit module.** The all-pass sections, the 6/12-stage cascade, the notch/feedback maths and the
  sweep are **techniques** (allpass-and-diffusion.md): a phaser block takes a per-stage corner `f_c[n]` and a feedback
  gain. The **Bi-Phase** is a **circuit module** around it: the 6.8 nF + (LDR ∥ 220 kΩ) stage law, the vactrol LED →
  R map, the feedback divider with the 0.86 ceiling, the Rev/sync routing, the opto bypass, the output mix weights
  (dry 12 kΩ vs wet 4.7 kΩ + trim), and the two sweep generators (0.1–18 Hz, sine/square, pedal) — to be built from
  the existing vactrol block (current → R, attack/release) and a technique phaser, with the Bi-Phase constants
  as the module's own.
- **Parameters the device would expose** (the manual's): per phasor Rate (0.1–18 Hz), Shape (sine/square), Depth,
  Feedback; Phasor A sweep source, Phasor B sweep source (Gen 1 / Gen 2 / pedal), Sweep Sync (Norm/Rev), Phasor B
  input (In A / Out A / In B), bypass per phasor; a pedal/CV input the original needed a mod for. Block-level (kit-internal,
  not panel): the stage count (6), the cell law, the vactrol times.
- **Open gaps:** (1) the original photo-mod's R(I) curve, on/off resistances and time constants (this note cannot give
  the Hz sweep range: with the DERIVED table, the floor is 106 Hz, the ceiling needs the on-resistance); (2) whether
  the 1974 Musitronics unit equals this 1979 ARP drawing; (3) the LED driver network's break-point map, the Depth and
  centre trims; (4) how the "sine" is made; (5) any measurement of the real unit's sweep (no recording of the
  Bi-Phase in match-targets was used); (6) Beigel's own writing ("More Than You Ever Wanted To Know About Phasors",
  F. Ridder and M. Beigel, listed on Soundgas and mu-tron.com but not found as text) and patents; (7) a source
  that says what gives the Bi-Phase its "water" (the user's word); the best candidates to test by listening are the
  feedback peaks, the optical skew, and Rev-sync stereo, ranked by the kit's own matcher against a recording.

## 8. Mu-Tron Bi-Phase (m4l_dev/circuit_modules/mutron_bi_phase.py)

What the kit's module takes from the sections above, what it derives, and what it had to choose. Written 2026-10-20.

**Taken from the drawing [VERIFIED reading, sheets 1–2; sheet 2 re-read for C12]:** six identical stages per phasor
(4.7k / 4.7k, 6.8 nF, 220k ∥ cell), one LED per six cells; the input stage Z8B (R4 = R5 = 4.7k, R7 6.2k, R6 4.7k ∥ C5
3.3 nF, the feedback pot R133 10k at J1-1); the last stage's output through C12 0.47 µF to J1-1 (sheet 2: Z3B pin 7 →
C12 → J1-1), loaded by the pot and by R26 4.7k into Z9B's inverting input (pin 5 grounded: a virtual ground); Z9B
inverting (R26 = R27 = 4.7k); the mix node (PM1, R123, C14 0.15 µF, R29 4.7k from the wet; R31 12k from Z8A's output,
the dry; C15 47 pF and Z9A's "+" input, nothing else); S1's Out A taken from Z9A's output (A's mixed output: series is
A's whole output into B); the Depth pots R131 / R138 10k over R96 / R105 560 Ω; S7 Rev through Z15B; ±15 V rails.

**Derived [DERIVED, our algebra]:**
- Feedback gain from the pot's rotation p, the wiper loaded by R7 + R6 = 10.9k:
  `k = 2 · R6/(R6 + R7) · p · 10.9k / (10.9k + p(1 − p) · 10k)`: 0.862 at p = 1, 0.351 at p = 0.5 (linear taper).
- The "+" node's low-pass: C5 against R6 ∥ (R7 + the wiper's source resistance p(1 − p) · 10k): 18.0 kHz at p = 0 or
  1, 15.8 kHz at p = 0.5.
- J1-1's high-pass: C12 into R26 ∥ (the pot, its lower part ∥ 10.9k): 106 Hz at p = 0 (3.2 kΩ), 137 Hz at p = 1. It
  sits inside the feedback loop and in the wet path, so the wet's bass is cut and the low notches are pulled up (at a
  500 Hz stage corner the middle notch is +6 %, the lowest +35 %; at 1.8 kHz +1.8 % and +12 %).
- The mix node, exactly (C15 left out): `out = dry + α · HP(wet − dry)`, `α = R31/(R31 + Rw)`,
  `Rw = R29 + R123 + R_PM1`, HP a one-pole at `1/(2π (R31 + Rw) C14)` (44 Hz when α = 0.5). Notches are deepest at
  α = 0.5, i.e. Rw = 12 kΩ.
- **Level with the phasors in, against the manual's "Insertion Loss: Less than 1db"** (2026-10-20). The manual gives
  the figure in its spec list beside "Frequency Response (Bypass)" and names no settings, signal or load. What the
  drawing gives: bypass (PM1 dark) is Z8A's follower through R31 into Z9A's "+" (a follower), 0 dB but for the dark
  cell's leak (−0.03 dB with PM1 at 3.6 MΩ), then R32 560 Ω (the "600 ohms" output) into the load: −0.5 dB into
  10 kΩ, which may be the spec's loss. With a phasor in, the wet equals the dry wherever the six stages total 0°/360°
  (above the notches, and between them at the peaks): 0 dB there too, so a tone at a peak or above the sweep meets the
  spec. On music it does not, and cannot: (1) the equal sum `(1 − α) dry + α wet` with an all-pass wet averages
  `(1 − α)² + α²` in power over the swept band, −3 dB at α = 0.5 and −2.8 dB at α 0.4 or 0.6 (R123's
  range); (2) C12 0.47 µF into R26 4.7 kΩ (Z9B's virtual ground) ∥ the feedback pot (re-read on sheets 1 and
  2 this session: Z3B pin 7 → C12 → J1-1 → R26 and R133) cuts the wet below 106–137 Hz while C14's mix high-pass
  passes it from 44 Hz, so from ~44 to ~110 Hz the output is `(1 − α) dry`, −6 dB at α = 0.5. On the kit's effect
  inputs (drums, bass, pad, a full mix, chords and a kick; m4l_dev/preset_loudness.py) 2sl phaser's presets, Output
  0 dB, lose 2.0–2.8 dB (median of the five) at low and moderate feedback (high feedback's peaks give some back:
  −0.9 dB with both at 80 in series; full feedback with an 18 Hz square sweep is +1.1 dB), of which C12 is ~1.4 dB on the classic setting (Init: −2.21 dB as
  drawn, −0.78 dB with C12 made huge) and the notches the rest; R123 moves it by under 0.2 dB (α 0.4: −2.18, α 0.6:
  −2.04) [DERIVED, measured on the module]. So the module's level loss is the drawing's, not a model error.
- Depth: the pot over 560 Ω passes `560/10560 + (1 − 560/10560) · rotation` of the sweep: Depth 0 still sweeps 5.3 %.
- Six stages of the circuit, (sRC − 1)/(sRC + 1), equal six of the technique's (1 − s)/(1 + s): an even count.

**Chosen, UNVERIFIED (the module's `MutronBiPhaseCharacter`; §7's open gaps):**

| field | default | why this default |
|---|---|---|
| `cell_law_scale_ohms`, `cell_law_exponent`, `cell_law_floor_ohms` | 3.464, 1.4, 1136.212 | the VTL5C3/2 law (DAFx-13 eq. 39) stands in for the unpublished photo-mod |
| `led_current_dark_amps`, `led_current_full_amps` | 50 µA, 5 mA | with that law the stage corner sweeps ~112 Hz (the 220k floor is 106 Hz) to ~3.4 kHz: notches ~30 Hz to ~13 kHz; log-linear between (equal sweep steps = equal octaves of current, 2sl gate's practice; the real driver's diode break-points not traced) |
| `cell_attack_ms`, `cell_release_ms` | 2.5 ms, 35 ms | the VTL5C3's catalog turn-on (63 %) and turn-off (to 100 kΩ) orders; release = undriven time from the full current to the dark one |
| `stage_corner_spread` | 0.05 | the drawing's 10 % capacitors and the cells' tracking; a fixed pattern per phasor |
| `feedback_pot_taper_exponent` | 1.0 | linear taper assumed |
| `sweep_sine_roundness` | 1.0 | a true sine (how Z15A shapes the "sine" was not traced; 0 = the triangle) |
| `wet_trim_ohms` (R123) | 3978 Ω | trimmed for α = 0.5 with the bypass cell lit at 10 mA (3.32 kΩ by the law) |
| `bypass_led_current_amps` | 10 mA | PM1 (PE613-12) lit by the foot switch; its law taken as the sweep cells' |
| `rail_volts` | 13 V | the op amps' swing at ±15 V (the op amp part not legible) |

**Movable at run time** (2026-10-20, for 2sl phaser's Cells page, "I can then try to find the water in it by playing
with parameters", user): every field above but `wet_trim_ohms`, `bypass_led_current_amps` and `rail_volts` can be a
run-time input (`character_inputs`); they move the twelve sweep cells only. PM1 stays at the character's numbers: it
is another part, trimmed by R123 against its own law, so the hunt never unbalances the dry / wet mix or opens the
bypass.

**Left out:** the input coupling (C1 0.047 µF into 390k: 8.7 Hz) and the RF filter; the 34 kHz roll-offs of C9 / C13
across R5 / R27; C15; the output's 560 Ω and C16; Gen 1's rate from the pedal (S2 "Ped"); the LED drivers' exact
network and trims; any signal dependence of the cells' resistance; noise. The sweep generators are modelled from the
manual (0.1–18 Hz, sine / square) and the drawing's topology (a triangle core), not traced component by component.


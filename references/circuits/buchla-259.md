# Buchla 259: the principal oscillator, the timbre section, the modulation oscillator

The circuits behind three circuit modules (architecture/dsp-blocks.md, "Circuit modules"), one per schematic sheet of
the original 259 "Programmable Complex Waveform Generator" (rev 11/78). Written 2026-10-19 for 2sl gate from the
original Buchla schematics, Andre Theelen's DIY redraw, the DAFx-17 paper and the part datasheets (§1-§4, §7); §5 and
§6 are from 2sl gate's research brief (2026-10-17), moved here with the modules on 2026-10-20.
`fetch-circuit-sources.sh` downloads every file used here into `sources/` (not in git) and checks its sha256.

## Buchla 259 principal oscillator (twosl_dsp/circuit_modules/buchla_259_principal_oscillator.py)

Sheet 2A "Principle Oscillator": a triangle core (§5: a symmetry trimmer balances the rise against the fall) and the
shaper that bends it into the sine the timbre section folds (§5, "slight sine impurity"; the sine's amplitude is not
marked on the sheet, §3.3). Linear through-zero FM is 2sl gate's [DESIGN] (§5: the original's FM law is
[UNVERIFIED]); the reset is the 259e / 261e note sync (§5).

## Buchla 259 timbre section (twosl_dsp/circuit_modules/buchla_259_timbre_section.py)

Sheet 3A "Symmetry + Timbre": the drive stage IC29, Symmetry's offset through Q10, the five CA3160 cells on their
±6 V rails, the summers and the limiter, the 1.33 kHz tone filter (§1-§4, §6). The Symmetry-shaped comparator wave
and Order's crossfade (§2.3, sheet 4A) are not modelled.

## Buchla 259 modulation oscillator (twosl_dsp/circuit_modules/buchla_259_modulation_oscillator.py)

Sheet 4A "Order + Modulator": the modulation oscillator, whose index routes it to the principal oscillator's pitch,
amplitude and timbre (§5). Its waves and ranges are from the repair notes (§5 [SECONDARY]); the routing (FM, AM) is
the instrument's.

Tags (as in 2sl gate's research brief, references/west-coast-technical.md there):
- **[VERIFIED sch]**: read off a schematic scan. The designators and values I read are given so you can check them.
- **[VERIFIED ds]**: read in a datasheet or paper.
- **[SECONDARY]**, **[UNVERIFIED]**, **[DERIVED]** (my calculation), **[DESIGN]**.

## Sources

| File (in sources/) | What | Where from |
|---|---|---|
| Buchla_2590_1..4_200.jpg | Buchla & Associates, "Part of Model 259 Programmable Complex Waveform Gen.". Sheet 3A "Symmetry + Timbre" (rev 11/78). Sheet 4A "Order + Modulator" (dated 8/2/77, rev 11/78). Sheet 2A "Principle Oscillator" (rev 11/78). | Magnus Danielson's Buchla page, now offline. Wayback: https://web.archive.org/web/2016/http://rubidium.dyndns.org/~magnus/synths/companies/buchla/ (the DAFx-17 paper's footnote 2 cites the same page as "Buchla's original design") |
| Buchla_2920B_200.jpg, Buchla_2920C_200.jpg | 292B "Quad Low Pass" (dated 10/12/70, 7-76 notes). 292C "Quad Lopass Gate" (dated 9/25/77). | same page |
| theelen-259timbre-v05.pdf | "Mutant 259 Timbre/Mod Index", v0.5, 10 Dec 2011, "Adaptation and redraw by Andre Theelen, based on schematic by Mark Verbos, original schematic by Don Buchla, 1978". | https://www.ecalpemos.nl/sdiy/buchlaesque-modular/mutant-259-timbre-modindex-section/ |
| esqueda-et-al-dafx17.pdf | Esqueda, Pöntynen, Parker, Bilbao, "Virtual Analog Buchla 259 Wavefolder", DAFx-17 | https://www.dafx.de/paper-archive/2017/papers/DAFx17_paper_82.pdf |
| CA3160-intersil-FN976.4.pdf | Intersil CA3160 datasheet, FN976.4, Oct 2002 (university mirror, because Renesas no longer hosts it) | https://gia.iqm.unicamp.br/datasheet/CA3160.pdf |
| tl072-ti-SLOS080W.pdf | TI TL07x datasheet, rev W, July 2025 | https://www.ti.com/lit/ds/symlink/tl072.pdf |
| 1n5221-vishay.pdf | Vishay 1N5221..1N5267 zener datasheet (1N5228 = 3.9 V) | https://www.vishay.com/docs/85588/1n5221.pdf |
| tiptop-259t-manual.pdf | Buchla & Tiptop Audio 259t manual (Eurorack re-design): Timbre/Order/Symmetry text | https://tiptopaudio.com/manuals/Buchla_&_Tiptop_Audio_259t.pdf |

Also cited, not fetched: Lanterman, Georgia Tech ECE homework on the 259 timbre circuit, https://lanterman.ece.gatech.edu/acms/hw3_15 (the analysis the DAFx paper follows).

**How the scans were read.** Sheets 3A and 4A are hand-drawn and scanned sideways. I rotated them 90° clockwise and zoomed in on each region named below. Values are as written on the sheet. Where I was unsure of a reading, I say so.

---

## 1. Signal path of the original 259 timbre section (sheet 3A, then 4A)

```
principal sine ─R212 68k─┬─ IC29 pin5 (+)      IC29 (TL082, ±15 V) = JFET VCA: gain 1 + R215/(R214 15k ‖ Q11) (Q10/Q11 = dual 2N3958)
                    R216 3.3k to 0             feedback R215 33k ‖ C22 470 pF; the Timbre control drives the JFET gates via R213 10k
Symmetry node N (IC27 pin 1) ─R204 130k─┬─R204A 300k─ Q10 channel (gate = Timbre, tied to Q11) ─ IC29 pin 6   (DC offset, §2.3)
                          R203 150k to +15
IC29 out = folder input bus Vin ─┬─ 5 folding cells (IC36–40, CA3160 on ±6 V) ─ R240/R236/R232 ──────────┐
                                 ├─ cells 4,5 ─ R228/R224 ─┐                                              │
                                 └─ dry R220 240k ─────────┴─ IC31b (TL082, R242 24.9k fb) ─ R243 24.9k ──┤
                                                                                                          + 10 µF (series, no designator)
                                                                                                          │
                                       IC31a pin 2 (TL082): R245 1.2M ‖ C24 100 pF ‖ zener-bridge limiter ─ IC31 pin 1 = folder out
sheet 4A: IC31-1 ─ vactrol E ─┐
          IC30-7 ─ vactrol F ─┴─ IC33a pin 3 (+) (Order crossfade) ─ IC33b (AM) ─ … ─ IC35a ─ R292 680 Ω ─ "final out" (2-17)
```

IC types from the parts list on sheet 3A [VERIFIED sch]: "ICs 23, 24 LF13331; 25 LM311; 26–35 TL082; 36–40 CA3160"; "Q10, 11 dual 2N3958".

The five cells, with the DAFx-17 Table 1 names [VERIFIED sch, and they match the paper's Table 1 exactly]:

| Cell (DAFx k) | Rk,1 input | Rk,2 feedback | Rk,3 to summer | Summed into |
|---|---|---|---|---|
| 1 | R238 10k 1% | R239 100k 1% | R240 100k 1% | IC31a |
| 2 | R234 49.9k 1% | R235 100k 1% | R236 43.2k 1% | IC31a |
| 3 | R230 91k | R231 100k 1% | R232 56k 1% | IC31a |
| 4 | R226 30k 1% | R227 100k 1% | R228 68k 1% | IC31b |
| 5 | R222 68k 1% | R223 100k 1% | R224 33k 1% | IC31b |
| dry | — | — | R220 240k | IC31b |

Each cell's + input goes to 0 V through 10k (R237, R233, R229, R225, R221). Each cell has **47 pF between pins 1 and 8** (CA3160 compensation pins). The summers: R242 = 24.9k 1% (DAFx RF1), R243 = 24.9k 1% (DAFx R7), R245 = 1.2 MΩ (RF2), C24 = 100 pF (C), and R241 = R244 = 10k from the + inputs to 0 V.

---

## 2. Question 1: DC coupling

### 2.1 The folder has one series coupling capacitor, and it is inside the summer
- **[VERIFIED sch, sheet 3A]** A **10 µF electrolytic (written "10µfd", no designator)** sits in series between the junction of all the summing resistors (R240, R236, R232 and R243) and IC31a's inverting input (pin 2). Its + side faces the resistor junction. The DAFx-17 Fig. 1 leaves it out. Theelen's redraw has it as **C3 10u** in the same place.
- **Corner [DERIVED]:** the cap feeds a virtual ground, so the resistance in series with it is the parallel combination of the branch resistances into the junction. Those are R240 100k, R236 43.2k, R232 56k and R243 24.9k (the cell branches see an extra Rk1‖Rk2 when saturated, which lowers the corner slightly). That gives 11.0 kΩ, so **fc = 1/(2π · 11.0 kΩ · 10 µF) ≈ 1.45 Hz** (τ ≈ 110 ms). At DC, IC31a has unity gain from its own offset, so the folder output carries only IC31's offset, a few mV.
- So any DC that reaches the folder bus, from offsets, an asymmetric drive, or a slow Timbre change on an asymmetric fold, is high-passed at about 1.5 Hz before the folder output. Above about 5 Hz the circuit is DC-transparent.

### 2.2 After the folder, the 259 is DC-coupled to the output jack
- **[VERIFIED sch, sheet 4A]** IC31 pin 1 → vactrol E (Order) → IC33 pin 3. IC30 pin 7 → vactrol F → the same node. Then IC33a → IC33b (AM, vactrol G) → vactrol H / IC17 switch, mixed with R291 82k → IC35a pin 3 (R290A 22k to 0 V), with gain 1 + R293 33k / R290 6.8k ≈ 5.9 and C28 470 pF across R293 (that gain falls toward 1 above 1/(2π·33k·470p) ≈ 10.3 kHz [DERIVED]) → **R292 680 Ω → "final out" (2-17)**. **There is no series capacitor anywhere from IC31 to the output.** The audio out is DC-coupled.
- So the Order path's other source (IC30, the Symmetry waveform, §4.1) reaches the output with whatever DC it has.

### 2.3 Where the Symmetry DC goes: both paths [VERIFIED sch, re-traced 2026-10-19]

**Verdict: both.** On the 11/78 sheet 3A, the Symmetry control voltage (1) puts a DC offset into the folder input through a JFET (Q10) that is gated by the Timbre control, and (2) separately sets the shape of the comparator-made wave that Timbre and Order crossfade against the folder. The earlier by-eye trace (which found only path 2) missed the R204/R204A/Q10 network. Confidence: high for the topology (a second, independent drawing has the same network, see below); the size of the offset is [DERIVED] and its zero point is [UNVERIFIED].

**Drafting convention on sheet 3A.** Junctions are drawn as T's, and a four-way crossing with no dot is a crossover. The sheet proves this itself: the (sym. c.i.) line from pin 4 crosses the ⊓ and ⩘ input lines on its way down, and those cannot be connected. Every crossing below is read that way.

**Nets followed** (sheet rotated 90° clockwise, then cropped and enlarged 2–6×):
1. **Symmetry control node, N = IC27 pin 1.** (sym. c.i.) pin 4 → straight down (crossing ⊓ and ⩘) → T to IC27a pin 2 → down through IC24 pins 10/11 (switched by ENA) → 2-16 → panel: R167 180k from the wiper of R168 10k "(symmetry)" (+15 to 0), and R166 100k from a CV input. IC27a is an inverting amp: R170 130k from pin 2 to pin 1, pin 3 tied to IC27 pin 5. So N = −130k × (sum of input currents); for the knob alone N = −0.72 · V(wiper), 0 to −10.8 V [DERIVED].
2. **N → vactrol D (shaper).** N → R171 68k → IC27b pin 6 (with R174 49.9k from +15, R175 20k, C21A) → IC27b pin 7 → LED of vactrol D. Vactrol D's cell sits in the IC23/R176 network that sets IC25's (LM311) threshold on the sawtooth. IC25 → IC23 switches → IC26a/b → IC26b pin 7 ("5V" wave) → long wire (crossings, no junction, at the timbre-c.v. and t.m. verticals) → vactrol B (T attenuator, R209 22k ‖ C23 .002 to 0) → IC30 pin 5. The sine also reaches IC30 pin 5 through R217 22k and pin 6 through R218 22k; R219 12k is the feedback. Vactrol B's LED is driven by IC29a (pin 1) from the Timbre control current (R205 33k, R207 100k, R208 1.8k, R210 20k / R210A 6.8k). So Timbre crossfades sine → Symmetry wave at IC30's output; Order (sheet 4A, vactrols E/F) crossfades that against the folder output (§2.2).
3. **N → folder input (the net the earlier trace missed).** N also leaves IC27 pin 1 on a long horizontal wire to the right (continuous from x≈350 to x≈1054 px on the rotated 200 dpi scan; four-way crossings, no junctions, with the 2-4, 2-15/IC23 pin 15, IC16 pin 11 and 2-13 verticals) → **R204 130k** → node M, with **R203 150k to +15** → **R204A 300k** → a four-way crossing (no junction) with the tied JFET gates → the **lower channel terminal of Q10** → Q10's channel → **IC29 pin 6** (the same node as R215 33k, C22 470 pF, Q11's drain and R214 15k).
4. **The JFET pair.** Q10 and Q11 are one dual 2N3958, gates tied (the gate line takes R213 10k from the Timbre control node and R211 470k from the sine). Q11 ‖ R214 15k go from IC29 pin 6 to 0: they set IC29's gain, 1 + R215/(R214 ‖ Rds). Q10 has the same gate voltage, so it opens with Timbre: it passes a current from node M into IC29's inverting input, and IC29's output (the folder bus, IC36–40 via R238/R234/R230/R226/R222 and the dry R220) moves by −R215 × that current.
5. **IC29's + input (checked again).** Pin 5: sine → R21x 68k (designator read as R212 before; on the enlarged scan it looks like R218, which is also used at IC30, so the digit is illegible) and R216 3.3k to 0. R213 10k crosses this net (four-way, no junction) on its way to the gates. Nothing else.

**Size of the offset [DERIVED].** Thevenin of node M: V_M = (150k · N + 130k · 15 V)/280k = 0.536 · N + 6.96 V, through 69.6k + R204A 300k ≈ 370k (+ Q10's Rds). With Q10 fully on, the DC at the folder bus is −33k/370k · V_M ≈ **−0.089 · V_M**. For the knob alone (N 0 to −10.8 V) that is **≈ −0.62 V to −0.10 V**. That is the same order as cell 1's breakpoint (0.600 V), so it makes clearly asymmetric folds and even harmonics. As Timbre goes to zero, Q10 pinches off and the offset goes with it, so a quiet sine stays clean. **[UNVERIFIED]** where the offset is zero: with only the knob, N never goes positive and the offset never crosses zero, so something not read here (the pin 4 "c.i." programming input, the panel wiring of R166, or a bias I misread) must set the centre. Resolving it needs the panel wiring sheet or a measurement on a real 259.

**Independent check: Theelen's redraw (based on Mark Verbos's schematic) [VERIFIED, theelen-259timbre-v05.pdf p. 1].** It has the same network with clean junction dots: Q1 J201 (= Q10) from the TL072's inverting input to **R15 300k (= R204A)**, gates tied with R14 470k from the sine, Q2 J201 (= Q11) ‖ R16 15k to ground, R13 33k ‖ C1 470 pF feedback. Because his version drops the Symmetry section, R15 goes straight to **+15 V**: a fixed offset of about −33k/300k · 15 V ≈ −1.65 V at full Timbre [DERIVED]. So both drawings route a DC current into the folder driver through a Timbre-gated JFET; the original makes it depend on Symmetry.

**Secondary sources, which now agree with the schematic:**
- Lanterman, Georgia Tech homework: "the 259 had both "timbre" (amplitude of sinewave going in) and "symmetry" (DC offset on sinewave going in) controls; the Easel appears to just have a timbre control." No circuit evidence is given; the schematic his homework points to is the Easel's (B2080-9A), not the 259's [SECONDARY] https://lanterman.ece.gatech.edu/acms/hw3_15 (same sentence at https://lanterman.ece.gatech.edu/ece4803/homework/hw3_06/).
- Buchla & Tiptop Audio 259t manual (a 2010s Eurorack re-design, not the original circuit): "Symmetry adds DC to the audio entering the folder thus altering its folding further to be asymmetric." and "When Order is fully CW, timbre cross fade between the VCO sine wave and another cross fader of the sawtooth/M shape that is controlled by the Symmetry knob." [VERIFIED as the 259t's manual text, SECONDARY for the original] https://tiptopaudio.com/manuals/Buchla_&_Tiptop_Audio_259t.pdf (in the fetch script). That is both paths, as on the original sheet.
- Not found: an original Buchla 259 user manual or 200-series text on Symmetry; a Verbos, Ken Stone, modwiggler or electro-music description of the Symmetry/Order circuit (electro-music refused the connection). Roman's 259 page (https://modularsynthesis.com/roman/buchla259/259cwg.htm) has nothing on Symmetry or Order; it covers the triangle core's trimming and the sine shaper's (§5).

**Versions.** Only the 11/78 sheets are in hand. Theelen's redraw (from Verbos) agrees on the JFET network. A pre-1977 259 could differ [UNVERIFIED], but nothing found suggests it.

**Consequence.** The DAFx-17 "odd harmonics only" holds only for the folder with zero offset, i.e. Symmetry centred (or Timbre so low that Q10 is off). On the original, Symmetry makes the folder itself asymmetric, and the Order/IC30 path adds the Symmetry wave on top.

### 2.4 The 292's audio input is AC-coupled
- **292C (9/25/77) [VERIFIED sch, Buchla_2920C]:** (sig in) 1-2 → **C3 "1µfd"** in series → a node with **R13 100k** and **R12 100k** to a net labelled "a" → IC7 pin 3. (The sheet also uses "C3" for a 220 pF cap, so the designator is duplicated.) **Corner [DERIVED]:** if "a" is 0 V and both resistors load the node, 1/(2π·50k·1µF) ≈ **3.2 Hz**. With only one of them, ≈ 1.6 Hz. **[UNVERIFIED]** what net "a" is. It also labels R29's output into the IC13 summer, so it may be a local reference rather than ground.
- **292B (10/12/70) [VERIFIED sch, Buchla_2920B]:** AUD IN → R8 15k → **C2 .47 (µF)** → IC2 pin 3 with **R10 47k** to 0 V. R9 12k (switched in by S1 "FILT") goes from the R8/C2 junction to 0 V. Corner [DERIVED]: 1/(2π·(47k + R8‖R9 = 6.7k)·0.47 µF) ≈ **6.3 Hz** (filter), or ≈ 5.5 Hz (gate, R9 out). A **second** coupling cap follows the vactrol network: **C5 .47** from the Q1 source follower into IC3 pin 3 with **R17 47k**, ≈ **7.2 Hz**. So the 292B audio path is high-passed twice at about 6–7 Hz.

### 2.5 Answer
The 259 removes the folder's DC at **≈1.45 Hz** with the 10 µF cap at IC31a. Its output stage is DC-coupled. The 292 then AC-couples its input again: **≈1.6–3.2 Hz on the 292C (1 µF), or ≈6 Hz twice on the 292B (0.47 µF)**. So on Buchla hardware, **DC never reaches the LPG's vactrol network.**

---

## 3. Question 2: the folding cells and their rails

### 3.1 Topology: the folding is the op-amp hitting its rails
- **[VERIFIED sch]** Each cell is an inverting amplifier (Rk,1 in, Rk,2 feedback, gain −Rk,2/Rk,1 = −10, −2.0, −1.1, −3.3, −1.5). Its summing node (the inverting input) also feeds the next summer through Rk,3. While the op-amp is linear, that node is a virtual ground, so no current flows through Rk,3. **That is the deadband.** Once the output hits its rail, the node can no longer be held at 0 V, and current flows into the summer. So "running the op-amps into their rails" is the folder itself. Every fold breakpoint is a rail-clip point.
- **Rails [VERIFIED sch, sheet 3A top right]:** +6 V is IC32 (TL082) buffering the divider R247 15k (from +15) / R246 10k, so 15 · 10/25 = **6.0 V**. −6 V is the other half of IC32 inverting it (R249 10k, R251 10k). R248A and R214A (1k each) help the buffers source and sink, from +15 and to −15. C26 and C25 (1 µF) decouple. The cells' pins are marked "+6" and "−6" on the sheet. The rest of the 259 runs on ±15 V. The DAFx paper says the same: "the op-amps in the folding branches are connected to lower supply voltages than the rest of the circuit" [VERIFIED ds].
- **Part [VERIFIED sch + ds]:** CA3160, a PMOS-input / **CMOS-output** BiMOS op-amp. The datasheet says the output swings "to within 10mV of either supply voltage terminal (at very high values of load impedance)": VOM+ = 15 V and VOM− = 0 V at RL = ∞, and 13.3 V at RL = 2 kΩ, on a 15 V supply. The cell load is ≥ 100 kΩ, so **each cell clips within a few tens of mV of ±6 V** [DERIVED]. ±6 V = 12 V total, inside the 5–16 V operating range and above the 8.3 V where the internal bias zener regulates. So the bias is normal, and the parts are not "starved" in the datasheet sense.
- **Breakpoints [DERIVED, = DAFx]:** |Vin| = (Rk,1/Rk,2)·6 V = **0.600, 2.994, 5.460, 1.800, 4.080 V** for cells 1–5.

### 3.2 What the DAFx model (ideal hard clip at Vs = 6 V) leaves out
1. **CA3160 input-pin limits (cell 1 only, |Vin| > ~8.4 V) [DERIVED from datasheet abs-max, behaviour UNVERIFIED].** The cell node (op-amp − input) sits at Vk. With the DAFx model at Vin = 10 V, the nodes are Vk = **7.83, 2.64, 1.28, 4.71, 1.58 V**. The CA3160's allowed input range is "(V+ +8V) to (V− −0.5V)". Its gate-protection network "functions as if it is connected to Terminal 4" (V−). Its differential input limit is 8 V. So for **negative** Vin below about **−8.4 V**, cell 1's node would go below −6.5 V. The protection diode to −6 V would then conduct and clamp it, while on the positive side nothing clamps until +14 V. That would make the transfer **asymmetric beyond about 8.4 V peak drive**. Separately, cell 1's differential input reaches the 8 V absolute maximum at about |Vin| = 10.2 V. Whether the real drive ever gets there depends on the input level, which is unknown (§3.3).
2. **Output limiter on IC31a [VERIFIED sch, clamp level DERIVED].** IC31a's feedback has a **diode bridge: four diodes (type not marked on 3A; 1N4148 in Theelen's D2–D5) with a 1N5228 (3.9 V) zener across it**. C24A 0.05 µF sits across the zener, which is pre-biased through R245A 1 MΩ to +15 and R245B 1 MΩ to −15 (about 13 µA). That makes a symmetric limiter at about **±(Vz + 2Vf) ≈ ±(3.9 + 1.2) ≈ ±5.1 V**, softer at low zener current: the Vishay sheet gives ZZK = 1900 Ω at 0.25 mA. From my reading of the diode directions. Theelen's redraw has the same network (D2–D6, C5, R50, R51). The DAFx sum peaks at |Vout'| = 3.13 V for |Vin| ≤ 5, 3.40 V for ≤ 8, and 4.19 V for ≤ 10. It then grows at 1.68 V/V because the cell slopes no longer cancel the dry path: 7.5 V at 12 and 12.5 V at 15 [DERIVED]. So **the limiter engages only above about 10.5 V peak drive**, and on the original it caps the folder output at about ±5 V. The sheet annotates the folder output waveform as "2.2v".
3. **Tone filter** R245 · C24 → 1.33 kHz (already in DAFx).
4. **Pre-folder lowpass [DERIVED from VERIFIED sch]:** IC29's feedback is R215 33k ‖ C22 470 pF, so the VCA's extra gain rolls off above ≈ **10.3 kHz**. This only matters for very high notes.
5. **DC block ≈ 1.45 Hz** (§2.1).
6. **The JFET VCA** (Q10/Q11 2N3958, gates linearised through R211 470k from the signal) is itself a mild nonlinearity at the folder input, and is not modelled anywhere [UNVERIFIED how large].
7. **Slew rate [VERIFIED ds + DERIVED].** The CA3160 datasheet gives SR = 10 V/µs at ±7.5 V with its internal 30 pF compensation, and says "additional compensation … may be used between Terminals 1 and 8". The 259 adds **47 pF there on every cell**. If that cap simply adds to the internal one, SR ≈ 10 · 30/77 ≈ **4 V/µs** (rough). In its linear region, a cell's output must move at Gk · dVin/dt, so the worst case is cell 1 (gain 10) at the zero crossing: 10 · A · 2πf. That is 0.31 V/µs at A = 5 V and 1 kHz, 1.6 V/µs at 5 kHz, and 3.1 V/µs at 10 kHz. **So slew limiting matters only for fundamentals of several kHz at high Timbre.** Over most of the musical range the ideal clip model holds. **Overload recovery time** (coming out of the rail) is not given in the datasheet [UNVERIFIED].

### 3.3 Signal level at the folder input at maximum Timbre: not on the schematic
- **[VERIFIED sch]** The maximum is a **select-on-test trim**: a resistor "*" from −15 V into the timbre-control node, annotated "(* add to adj. max timbre)". The VCA gain also depends on the individual JFET. The sine amplitude itself is not marked on sheet 2A (the square is marked 4.29 V). So **the peak folder drive at full Timbre is [UNVERIFIED]**. A rough bound from the divider (0.046) and IC29's non-inverting gain (1 + 33k / (15k ‖ Rds(on))) with Rds(on) around 1 kΩ is a gain of about 1.6 × the sine, so likely below 10 V for a sine of a few volts. That is a guess, not evidence. The DAFx paper sweeps 0–10 V and uses 5 V in its examples. Theelen made the range a front-panel pot ("Timbre Range", P3), saying the original "sensitivity control is a trimmer on the PCB".

### 3.4 Versions

| | Folding cells | Cell rails | Clip point | Symmetry/Order | Source |
|---|---|---|---|---|---|
| **Original 259 (sheets rev 11/78; sheet 4A dated 8/2/77)** | 5 × CA3160 (IC36–40), 47 pF on pins 1–8 | ±6.0 V, op-amp-buffered divider | ≈ ±6 V (CMOS rail-to-rail) | yes, both paths (§2.3): Symmetry offsets the folder input via Q10, and shapes the IC30 wave | [VERIFIED sch] |
| **Theelen "Mutant 259" v0.5 (2011), the DAFx basis** | 5 × **TL072** (U3A/B, U4A/B, U5A). He writes: "I replaced all opamps with the TL072CN" | ±6 V (U7A/B, same 15k/10k divider) | TL07x is **not** rail-to-rail: VOM ±13.5 V typ at ±15 V, RL = 10k, i.e. ~1.5 V headroom. At ±6 V that suggests ≈ **±4.5 V** [DERIVED, UNVERIFIED at ±6 V]. Breakpoints would scale by 0.75 (0.45, 2.25, 4.10, 1.35, 3.06 V) and so would the offsets. | none ("does not have the Symmetry and Order sections"); the Q10 offset path stays, tied to +15 V through R15 300k (§2.3) | [VERIFIED his page + PDF] |
| DAFx-17 model | ideal clip, Vs = 6 V (the CA3160 assumption). Simulated with LTC6088 because "no publicly available SPICE model for the CA3160 seems to exist" | — | ±6 V | omitted | [VERIFIED ds] |
| **259e** (Buchla 2013+) | none: **digital** waveshaping tables (8 tables, Warp/Morph) | — | — | — | [VERIFIED] https://buchla.com/product/259e/, https://cdn.softube.com/user-manuals/Buchla-259e |
| **Tiptop 259t** | no schematic published. Retail text: Wave Folder, Sawtooth and M shapers; Symmetry = DC into the folder. Runs on Eurorack ±12 V. | [UNVERIFIED] | [UNVERIFIED] | Order = crossfade folder ↔ saw/M | [VERIFIED manual text] https://tiptopaudio.com/manuals/Buchla_&_Tiptop_Audio_259t.pdf |

Note: the DAFx coefficients (Vs = 6 V) describe the **CA3160 original**, not Theelen's TL072 build as built.

---

## 4. What the timbre section module does, and what 2sl gate chose

### 4.1 DC before the LPG
- **Hardware removes the folder's DC twice before the LPG:** 10 µF at ≈1.45 Hz inside the 259 summer, then the 292's input coupling cap (≈1.6–3.2 Hz on the 292C, ≈6 Hz twice on the 292B). Blocking DC per voice before the LPG, as 0.3.4 does, matches the hardware. **[DESIGN]** A first-order high-pass at about **1.5 Hz** is the 259's own value. One at ≈3 Hz is the 292C's input. Either is faithful. The 259's corner is the one that reshapes slow Timbre and Symmetry modulation of an asymmetric fold, because DC steps decay with τ ≈ 110 ms.
- **The original Symmetry does bias the folder** (§2.3): about −0.09 × V_M at the folder bus, gated on by Timbre through Q10. So a 259-faithful folder makes DC whenever Symmetry is off-centre, and implementing Symmetry as a DC bias into the folder (§6 below [DESIGN]) is faithful to the original, not only to the 259t. The ≈1.5 Hz block after the folder is the right place to remove it.

### 4.2 What an op-amp folder model needs (for the step 5 work)
1. **Per-cell clip at the rail Vs, with Vs as a parameter.** This is the "underpowered op-amp" sound. The breakpoints are (Rk,1/Rk,2)·Vs and the fold offsets scale with Vs. ±6 V gives the CA3160 original. About ±4.5 V gives Theelen's TL072 build. Starving it further moves every fold lower [DERIVED from eq. 9 of DAFx-17].
2. A hard clip is right for the CA3160 (CMOS output, sharp saturation, "similar to hard clipping", DAFx-17 §2.1). A TL07x would need a softer knee [UNVERIFIED shape].
3. Optional, only if drive goes past about 8.4 V: the **cell-1 negative input clamp** at about V− − 0.5 V (asymmetry), and the **IC31a output limiter** at about ±5 V (soft, zener bridge) above about 10.5 V.
4. The **1.33 kHz one-pole** after the sum (in DAFx), the **≈1.45 Hz DC block**, and, if wanted, the **≈10.3 kHz** pre-folder roll-off.
5. Slew limiting can be skipped below a few kHz. Above that, cell 1 (gain 10) is the first to slew-limit.
6. Drive range: the hardware maximum is a factory trim (unknown). DAFx's 0–10 V range is a reasonable span, and 2sl gate can choose its own maximum.

### 4.3 What the timbre section module does (built for 2sl gate 0.3.12) [DESIGN, 2026-10-19]
- The five cells from Table 1's resistors and the rail Vs = **6 V** (the CA3160 original; a model constant,
  the character's `cell_rail_volts`), eqs. 8-11 as straight pieces (every cell's fold point, where a node meets its floor, where the
  sum meets the limiter), first-order ADAA with each piece's antiderivative in closed form. Alias floor at Fold 100,
  C5 (between the harmonics, against them): −93 dB with ADAA, −73 dB taken naively (2sl gate's tests/test_gate_dsp.py).
  Since 2026-10-20: second-order ADAA (piece-wise, references/dsp.md "Antiderivative piecewise-linear shaper"), one step
  late: a pure sine at 2x 48 kHz, worst alias under 20 kHz, first → second order: 4 V at 3.1 kHz −22.3 → −36.4 dB,
  8 V at 1.37 kHz −33.7 → −48.7 dB (the module's tests).
- §3.2's extras: each node floored at −(Vs + 0.5 V) (only cell 1 reaches it, below −8.4 V in; one-sided); the
  limiter as a hard ±5.1 V on the sum before the 1.33 kHz filter (where §3.2 derives its 10.5 V onset; on the
  original it sits after the filter, so it bites somewhat later there); the drive stage's 10.3 kHz roll-off as its
  gain at the note's frequency (its phase lag only shifts a static folder's output in time). The 1.33 kHz one-pole
  is the instrument's to run on each unit's folder output, before what it mixes in (the original's Order crossfade
  and AM come after it, sheet 4A). Until 2sl gate 0.6.1 it ran on the voices' sum, darkening the blend waves, the
  AM and the square with the fold (Graham, 2026-10-21: "too round").
- Symmetry: an offset into the folder of up to 1.5 V, times Fold (§2.3: Q10 opens with Timbre; Graham 2026-10-19:
  no fold, no offset). Linear in Fold [DESIGN]: no source gives the 2N3958's Rds against the Timbre voltage.
- Not modelled: slew (§3.2.7, above several kHz at high Timbre), the JFET VCA's own nonlinearity, the limiter's soft
  knee at low zener current, the 1.45 Hz block (the voice's predicted DC does that job).
- The rail at run time [DESIGN, 2026-10-21, for 2sl gate's Rails]: `cell_rail_volts` may move, within ±2.5..8 V (the
  CA3160's 5–16 V operating supply, §3.1). With it move every fold point (§4.2 item 1) and the node floor, −(Vs + 0.5 V);
  fixed in volts stay the limiter (±5.1 V), the 0.5 V of the CA3160's input range, and the drive and Symmetry's offset
  (the instrument's). Starved-supply behaviour below the CA3160's 8.3 V bias regulation (§3.1) and a TL07x's softer
  knee (§4.2 item 2) are not modelled: a lower rail here is the ideal cell's clip, lower.

## 5. The oscillators (from 2sl gate's research brief, §2.3 and §2.5 there)

- **259 routing:** the Mod Index scales three normalled paths from the modulation osc to the principal: **pitch (FM), amplitude (AM), timbre**, each switchable. **Phase lock** is the only reverse connection (principal → modulator; on the 259t description, it "eliminates harsh beating effects by locking the controlled oscillator to a subharmonic or frequency of the input signal"). [SECONDARY] https://www.ctrl-mod.com/products/tiptop-audio-buchla-model-259t-programmable-complex-waveform-generator
- **259 ranges and tracking (repair notes on a clone/original-spec unit)** [SECONDARY] https://www.modularsynthesis.com/roman/buchla259/259cwg.htm : PO about 29 Hz–9.8 kHz (calibrated 27.5 Hz–7 kHz); MO high about 32 Hz–8 kHz, low centred on 4 Hz down to ~1/3 Hz. **1.2 V/oct** tracking with an exponential converter and tempco. **Triangle-core oscillator: a symmetry trimmer balances rise (expo pair) vs fall (current mirror). Imbalance detunes the low octave.** MO "Both" mode turns saw → ramp, square → triangle.
- **259 AM** [SECONDARY, same URL]: "The 'dry' signal is subtracted from a fully modulated 'wet' signal. A **vactrol-based VCA** controls the wet amount." The AM index over-modulates, reaching 100% by about a quarter turn on many units. [DESIGN] So 259 AM is *not* a clean multiplier. It is dry − k·(dry·mod) with a vactrol-smoothed k, and goes past ring modulation at high index.
- **FM law: [UNVERIFIED].** No primary source states whether the original 259/208 FM is exponential or linear, or whether it is through-zero. The repair notes show FM entering an exponential-converter VCO, and there is an "autotune" switch that disables FM. The Tiptop 258t (sibling dual osc) has linear FM but **no through-zero**, losing pitch stability at high index (https://www.bonedo.de/artikel/buchla-tiptop-audio-258t-und-281t-test/2/). Softube 259e: FM inputs are **AC-coupled** like the hardware.
  - [DESIGN] Use **linear through-zero FM/PM** in the digital core for stable tuning at high index, plus a "vintage" knob that blends in an exponential FM component. Exponential FM causes upward pitch drift with depth. Kasper Nielsen's DAFx-20 paper gives a DC-corrected exponential FM matched to linear FM depth: https://dafx.de/paper-archive/details/IK3Kn6jQ6HB-lcUtx4BE4g
- **Sync (259e/Softube):** soft sync via PLL; hard sync where the Principal resets the Modulation osc; MIDI-note sync resets the MO on note-on. [VERIFIED for Softube] https://cdn.softube.com/user-manuals/Buchla-259e. 261e: MO syncs to the principal or to MIDI note-on. https://buchla.com/product/261e/ [DESIGN] Resetting the MO on note-on is vital for a repeatable techno stab: identical FM phase on every hit.
- 200-series oscillators track **1.2 V/oct** (not 1 V/oct) with tempco compensation. Triangle-core symmetry errors detune the lowest octave. [SECONDARY] https://www.modularsynthesis.com/roman/buchla259/259cwg.htm
- The Easel's MO waveforms get "quite distorted" at low frequencies (16 Hz). There are capacitive-coupling tilts on squares. [SECONDARY] https://modularsynthesis.com/buchla/208/buchla_208.htm. Arturia's TAE explicitly models capacitor "bend" of waveforms. [SECONDARY] Arturia manual.
- **The sine shaper** [DESIGN, 2sl gate SPEC §3.3]: a slight sine impurity (a low-level 3rd harmonic from an imperfect triangle→sine shaper; the repair notes above trim it [SECONDARY, same URL]: "The sine wave has a bit of flattening" on the unit as built; "I changed R110 to 787R (1K paralleled with R110) which rounded the top nicely"; "The sine trim TR1 adjusts the gain a bit more with this mod so I could adjust the sine amplitude to match the square amplitude"; "Sometimes I need to lower R107 (R149 vintage version) to dial in a nice sine shape. I have gone as low as 6K8." So the shape is set by a trim and the resistors around the shaper, and differs unit to unit: the module's drive is that trim). No source gives a unit's number: the module's default drive 0.95 puts the 3rd at −38.4 dB, the 5th at −48 dB, the 7th at −54 dB. The shaped wave's corners (the triangle's peaks) are band-limited in the module (polyBLAMP, found on the exact phase; the sine two steps late): at drive 0.95, 5 kHz, 2x 48 kHz, the worst alias −68.5 → −119 dB; the drive is a run-time character field (2sl drums' Harmonics turns it toward the triangle).

## 6. The DAFx-17 model, Symmetry and Order (from 2sl gate's research brief, §2.1.1-§2.1.2 there)

### 6.1 The 259 circuit (Esqueda, Pöntynen, Välimäki, Parker, DAFx-17)
Source for this whole subsection [VERIFIED]: https://www.dafx.de/paper-archive/2017/papers/DAFx17_paper_82.pdf (code and sound examples: http://research.spa.aalto.fi/publications/papers/dafx17-wavefolder)

- **Topology:** "five non-identical op-amp-based folding cells arranged in parallel alongside a direct signal path". Two summing amps combine the six branches. This is *parallel*, unlike the series folders in the Serge, µFold and Toppobrillo. The input is internally wired to the principal **sine** oscillator.
- The paper **omits the Symmetry and Order controls** (schematic adapted from Andre Theelen's DIY version).
- **Folding cell:** an inverting op-amp (CA3160, rail-to-rail CMOS, ±6 V rails) whose output saturates hard. Inside a dead-band the cell outputs 0. Outside it, the cell output is
  `Vk = Rk3 (Rk2·Vin − sgn(Vin)·Rk1·Vs) / (Rk1Rk3 + Rk2Rk3 + Rk1Rk2)` when `|Vin| > (Rk1/Rk2)·Vs`, else 0, with Vs = 6 V.
- **Component values (Table 1):** R1,1=10k, R2,1=49.9k, R3,1=91k, R4,1=30k, R5,1=68k; R·,2 = 100k all; R1,3=100k, R2,3=43.2k, R3,3=56k, R4,3=68k, R5,3=33k, R6,3=240k; R7=24.9k, RF1=24.9k, RF2=1.2M, C=100 pF.
- **Digital model, exact coefficients** (s = sgn(Vin), Vin in volts):
  ```
  V1 = |Vin|>0.6000 ? 0.8333*Vin - 0.5000*s : 0
  V2 = |Vin|>2.9940 ? 0.3768*Vin - 1.1281*s : 0
  V3 = |Vin|>5.4600 ? 0.2829*Vin - 1.5446*s : 0
  V4 = |Vin|>1.8000 ? 0.5743*Vin - 1.0338*s : 0
  V5 = |Vin|>4.0800 ? 0.2673*Vin - 1.0907*s : 0
  Vout' = -12.000*V1 - 27.777*V2 - 21.428*V3 + 17.647*V4 + 36.363*V5 + 5.000*Vin
  ```
  It matches SPICE to about 1e-5 V absolute error.
- **Output filter:** a one-pole lowpass with `fc = 1/(2π·RF2·C) ≈ 1.33 kHz`, "simply … a fixed tone control … gentle 6-dB/octave roll-off". Bilinear: `b0=b1=wcT/(2+wcT)`, `a1=(wcT−2)/(wcT+2)`.
- **Drive:** "Significant timbral variation can be achieved by simply modulating the amplitude of the input sinusoid." The paper sweeps peak amplitude A from 0 to 10 (volts). Examples use A = 5. On the 259, the Timbre knob sets this amplitude (also stated by the Buchla Archives: "the amplitude of a sine wave prior to the waveshaper", https://www.buchlaarchives.com/blog/timbre-digital-nonlinear-waveshaping).
- **Spectrum:** the transfer function is odd-symmetric, so the folder "introduces odd harmonics only". Sweeping A "generates complex harmonic patterns reminiscent of FM synthesis".
- **Antialiasing in the paper:** polyBLAMP at each fold corner, done per cell by rewriting each cell as an "inverse clipper" and computing the clipping instants analytically *for a sine input*. Results: trivial at 44.1 kHz is "practically unusable" for an 890 Hz, A=5 sine. polyBLAMP at 1× gives about +12 dB SNR. **8× oversampling + polyBLAMP ≈ 64× oversampling**, about 6× cheaper. Two-point polyBLAMP residual: `[−T,0]: d³/6`, `[0,T]: −d³/6 + d²/2 − d/2 + 1/6`.
  - Caveat [DESIGN]: their analytic corner-finding assumes a pure, stationary sine. Once FM or AM feeds the folder (as on the real 259), you would need numerical corner detection. ADAA (references/dsp.md, "Antiderivative piecewise-linear shaper") is the more general route.

### 6.2 Symmetry and Order (not in the paper)
- On the **Tiptop/Buchla 259t**: "Order" is the final crossfade between the **wave folder** and a **sawtooth / "M" (pseudo-square) shaper**. At Order fully CCW, Timbre = fold depth and **Symmetry adds DC into the folder, giving asymmetric folds**. At fully CW, Timbre crossfades sine ↔ (saw/M mix set by Symmetry). Order and Symmetry CV inputs have no attenuators. [SECONDARY] https://www.ctrl-mod.com/products/tiptop-audio-buchla-model-259t-programmable-complex-waveform-generator, https://www.perfectcircuit.com/tiptop-buchla-259t.html
- The original 259 panel labels the "HARMONICS" section "Order" and "Symmetry", with "even / odd" legends. [SECONDARY, UVic patch template] https://web.uvic.ca/~aschloss/course_mat/MU307/MU307%20Labs/Lab3_BUCHLA/BuchlaPatchTemplate.TabloidSizeXL.pdf
- **[UNVERIFIED]** whether the original 1970s Order circuit equals the 259t's saw/M crossfade. No original manual text was found. **Resolved 2026-10-19 (§2.3, re-traced):** on the original schematic (rev 11/78), Symmetry does both. It adds a DC offset to the folder input (through JFET Q10, which Timbre gates, so the offset fades out at low Timbre), and it shapes a comparator-made wave that Timbre crossfades in from the sine and Order crossfades against the folder output. Same as the 259t manual. The physics is safe either way: DC offset into an odd-symmetric folder produces even harmonics. [DESIGN] Implement Symmetry as a DC bias before the folder, and Order as a crossfade from folder output to an alternate shaper.

## 7. Still unknown
- The peak folder input at full Timbre on a real 259, and the principal sine amplitude.
- The net "a" on the 292C input (sets 1.6 vs 3.2 Hz).
- How the CA3160 actually behaves when cell 1's input pin goes below V− (clamp, latch-up risk) and how fast it recovers from the rail. No measurement found.
- The 259t's circuit (no schematic). The diode orientation in the IC31a bridge is from a hand-drawn scan.
- Earlier (pre-1977) 259 revisions: only the 11/78 sheets were found.
- Where the Symmetry offset is zero (§2.3): needs the panel wiring of R166/pin 4 or a measurement on a real 259.

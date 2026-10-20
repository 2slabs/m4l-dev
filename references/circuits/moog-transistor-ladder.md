# The Moog transistor ladder (904A / Minimoog VCF): sources, the circuit as drawn, the model the module runs

Written 2026-10-20 for the kit's circuit module `m4l_dev/circuit_modules/moog_transistor_ladder.py` (the catalogue's
shortlist #1, references/circuit-module-catalogue.md §8). `references/circuits/fetch-circuit-sources.sh` downloads
every source below into `references/circuits/sources/` (not in git) and checks it is the copy this was read from
(sha256).

Tags: **[VERIFIED]** read in the source itself this session (file, page / equation / part number given).
**[DERIVED]** computed by us from verified inputs, the method given. **[SECONDARY]** a credible secondary source.
**[UNVERIFIED]** a memory, a search excerpt, or a design choice with no source; do not build on it as fact.
**[MEASURED]** our own numbers, from the research scripts named.

## Moog transistor ladder (m4l_dev/circuit_modules/moog_transistor_ladder.py)

The module: the large-signal model of §3 (five tanh: the input pair and the four stages), the trapezoidal rule on all
of it with the loop solved by Newton's method (§6), two steps a host sample by default, the cutoff from the control
node's volts through the exponential converter and fc = If / (8 pi C VT) (§4), the Emphasis pot as the loop's gain k,
the two steps between the kit's halfband oversampler's upsampler and downsampler (references/dsp.md),
the output buffer's unity low-frequency gain and its coupling capacitors' 15.4 Hz high-pass (§2.2). Its character
(§7): VT, C, each stage's capacitor ratio, the input pair's offset, the input buffer's scale, the converter's
reference current and volts per octave, the Emphasis pot's top k, the coupling corner.

## 1. The sources

| file (in `references/circuits/sources/`) | what it is | URL |
|---|---|---|
| moog-patent-us3475623.pdf | R. A. Moog, US 3,475,623, "Electronic high-pass and low-pass filters employing the base to emitter diode resistance of bipolar transistors", filed 10 Oct 1966, granted 28 Oct 1969 (9 pages: 4 drawing sheets, text) | https://patentimages.storage.googleapis.com/ea/a3/6e/d3c9ff36d3e14a/US3475623.pdf |
| minimoog-vcf-schematic.gif | Minimoog service manual, "Figure 9-11 Filter printed circuit board no. 4 schematic diagram", circuit no. 6 Voltage Controlled Filter (scan by fantasyjackpalance.com) | http://www.fantasyjackpalance.com/fjp/sound/synth/synthdata/16-minimoog/001/911-filt-print-circ-schem.gif |
| moog-904a-schematic.jpg | R. A. Moog Co., "904-A Voltage Controlled Low Pass Filter" schematic, drawing 1149, dated 7-25-67, rev. C 11/10/70 (hylander.com scan, via the Wayback Machine 2007-06-23) | https://web.archive.org/web/20070623230759id_/http://www.hylander.com/images/schematics/904a.jpg |
| stinchcombe-moog-ladder-tf.pdf | T. E. Stinchcombe, "Analysis of the Moog Transistor Ladder and Derivative Filters", 25 Oct 2008 | https://www.timstinchcombe.co.uk/synth/Moog_ladder_tf.pdf |
| huovilainen-dafx04.pdf | A. Huovilainen, "Non-linear digital implementation of the Moog ladder filter", DAFx-04, Naples, pp. 61-64 | https://dafx.de/paper-archive/2004/P_061.PDF |
| stilson-smith-icmc1996.pdf | T. Stilson, J. O. Smith, "Analyzing the Moog VCF with considerations for digital implementation", ICMC 1996 | https://ccrma.stanford.edu/~stilti/papers/moogvcf.pdf |
| dangelo-valimaki-generalized-moog-part1-taslp2014.pdf | S. D'Angelo, V. Valimaki, "Generalized Moog Ladder Filter: Part I - Linear Analysis and Parameterization", IEEE/ACM TASLP 22(12):1825-1832, Dec 2014 (Aalto post-print) | https://aaltodoc.aalto.fi/server/api/core/bitstreams/7ebb6719-8c32-4e23-97ce-b6ebac589990/content |
| dangelo-dissertation-aalto-2014.pdf | S. D'Angelo, "Virtual Analog Modeling of Nonlinear Musical Circuits", Aalto doctoral dissertation 158/2014 (summary part; §3.3.1 summarises Part I and Part II) | https://aaltodoc.aalto.fi/server/api/core/bitstreams/f87d5b89-72b1-4b8a-85bd-e8ef9511937d/content |
| (references/dsp-sources/) zavalishin-va-filter-design-2.1.2.pdf | V. Zavalishin, The Art of VA Filter Design rev. 2.1.2: ch. 5 (ladder), §6.9 (transistor ladder 1-poles), §6.10 (multinonlinear feedback) | fetched by references/fetch-dsp-sources.sh |

Not obtained: D'Angelo & Valimaki, "An improved virtual analog model of the Moog ladder filter", ICASSP 2013,
pp. 729-733 (cited in the dissertation's reference list [VERIFIED citation]; no free copy found), and "Generalized
Moog Ladder Filter: Part II - Explicit Nonlinear Model through a Novel Delay-Free Loop Implementation Method", TASLP
22(12):1873-1883 (only the dissertation's summary read). Their claims below come from that summary only.

## 2. The circuit as drawn

### 2.1 The patent (US 3,475,623) [VERIFIED, the text columns 1-5]
- The low-pass filter's "seven portions": adder, signal input buffer, filter input, filter, filter output, signal
  output buffer, feedback loop (col. 1).
- The filter: "four identical sections each comprising a fixed capacitor and two transistors whose input diodes are
  effectively in series"; "the dynamic resistance from emitter to emitter of each of the filter transistor pairs is
  inversely proportional to the standing current. The cutoff frequency of each filter section is f = 1/(2 pi r c)"
  (col. 2).
- The input: "The gain of the input buffer is set so that the base-to-base variation creates a collector current
  variation which is small compared with the standing collector current" (col. 2): Moog designed for the small-signal
  region; the saturation is what happens past that design level.
- The output: "The gain of this buffer amplifier is set so that for very low frequencies, the final signal output
  voltage equals the signal input voltage to the input buffer" (col. 2).
- Feedback: "A variable feedback resistor may be connected from output to input thereby decreasing the overall gain
  of the filter circuit at very low frequencies. However, at the cutoff frequency, each filter stage contributes a
  phase shift of 45° and the final output signal is in phase with the initial input signal ... If the feedback is made
  sufficient, the filter will oscillate and becomes a phase shift oscillator with four voltage-variable
  phase-shifting sections" (col. 2).
- The cutoff law: "The cutoff frequency of the filters are proportional to the exponential sum of the control input
  voltages ... increasing the control input voltage a fixed amount will increase the musical interval by a fixed
  amount"; "an extremely wide range (1000:1) in cutoff frequencies" (col. 4). The filter input transistor's emitter is
  driven by the adder's output, its base held by a forward-biased diode "thereby also providing temperature
  compensation" (col. 1-2).

### 2.2 The Minimoog (service manual fig. 9-11, circuit no. 6) [VERIFIED reading of the scan]
- Ladder: four stages Q2/Q3, Q10/Q11, Q9/Q20, Q23/Q24 (TIS97), capacitors **C3, C7, C11, C16 = .068 uF** between the
  emitters; bias chain R4 220, R16 / R32 / R41 / R52 150; input pair **Q29/Q30 (TIS97, marked matched)**, its tail
  through R60 680 to **Q28 (TIS92)**, the exponential converter with **Q26 (TIS93)**: note 3, "Q26 & Q28 matched to
  ±3 mV at 20 mA". Control: SCALE trim R49 500 ohm + R70 1.8k, RANGE trim R39 10k with R46 68k, R74 47k from the
  control node (pin 5), R45 330 to Q26's base.
- Audio in (pin 4) through C27 10 uF and R54 470 to Q29's base (R67 200, C24 220 uF the bias).
- Feedback: pin 6 "Emphasis" through R76 330 and **R73 1k "REGEN CAL"** to Q30's base; the output stage's signal back
  through C10 10 uF (pin 7, Emphasis). So the loop is AC-coupled (a 10 uF capacitor): [INFERENCE] its corner is far
  below the audio band, so the module keeps the loop DC-coupled (D'Angelo's model) and the pass-band drop below holds
  above a few Hz.
- Output: each side of the top stage (C3's ends) through **C5 / C1 0.22 uF** into **R31 / R38 47k** to ground, emitter
  followers Q8 / Q6, a differential pair Q7 / Q5 (R26 1k tail): [DERIVED] the coupling high-pass corner
  1 / (2 pi 47 kOhm 0.22 uF) = **15.4 Hz**.

### 2.3 The 904A (drawing 1149, rev. C 1970) [VERIFIED reading of the scan]
- "Adder" (100k control inputs R1-R3, the control node, the matched pair Q3/Q4 with R10 27k, Q5), Q6 feeding the
  bottom pair Q7/Q8 (matched), the ladder Q9-Q16 (pairs marked matched), "RANGE SWITCH S1" with "RANGE CAPACITOR
  SIZES 1: 1.2 uF, 2: 0.3 uF, 3: 0.075 uF", the bias chain R26-R28 220, R29 68; "INPUT BUFFER" Q22/Q23 (matched),
  "OUTPUT BUFFER" Q19/Q20/Q21; "REV. AUDIO / REGENERATION" R22 50k, C8 25 uF. Notes: "ALL NPN TRANSISTORS 2N3392,
  ALL PNP 2N4058".
- [DERIVED] The three ranges are 16x and 4x apart (1.2 / 0.075, 0.3 / 0.075): a range switch is a capacitor, i.e.
  the character's `ladder_capacitance_farads` (the module's default is the Minimoog's 0.068 uF).

## 3. The large-signal model [VERIFIED]

- The differential pair: I1 - I2 = I tanh((V1 - V2) / 2VT) (Huovilainen eq. 1; Stinchcombe eq. 5), VT = kT/q;
  "VT = 26 mV" (Stinchcombe p. 7: 1 / (2 VT) "evaluates to 19.2"); "VT is the thermal voltage (~26 mV at room
  temperature 300 K)" (D'Angelo & Valimaki Part I, after eq. 2). Linear "within ±20 mV" (Stinchcombe p. 7).
- One stage: dVc/dt = (Ictl / C) (tanh(Vin / 2VT) - tanh(Vc / 2VT)) (Huovilainen eq. 10, Ictl half the control
  current); the same as Zavalishin eq. 6.25, y' = wc (tanh x - tanh y), "a simple nonlinear model of the underlying
  1-pole lowpass of the transistor ladder, directly arising out of the application of Ebers-Moll" (§6.9 p. 199), and
  its effect: "'cutoff reduction' at large signal levels ... audio-rate modulation of the cutoff" by
  K = (tanh x - tanh y) / (x - y) (p. 200).
- The whole filter: D'Angelo & Valimaki Part I eqs. 1-2,
  dVi/dt = (Ictl / 2C) (tanh(V(i-1) / 2VT) - tanh(Vi / 2VT)) for i > 1,
  dV1/dt = -(Ictl / 2C) (tanh(V1 / 2VT) + tanh((Vin + k VN) / 2VT)) (their sign convention: the first stage inverts),
  assuming infinite beta (no base currents, constant base voltages). The feedback is summed at the input pair, ahead of
  its tanh.
- [DERIVED] In x = V / 2VT and the module's sign convention (output in phase at DC, the patent's buffer output):
  x1' = wc (tanh(u - k x4) - tanh x1), xi' = wc (tanh x(i-1) - tanh xi), wc = Ictl / (4 C VT) (eq. 3-4's
  linearisation), u = the input pair's base-to-base volts / 2VT.
- Five tanh a sample suffice when each stage's tanh(y) is shared with the next stage's input (Huovilainen §4.2;
  Zavalishin fig. 6.32).

## 4. Small signals, feedback, the cutoff law [VERIFIED]

- One stage 1 / (s / wc + 1) with wc = If / (4 C VT), fc = If / (8 pi C VT) (Stinchcombe eqs. 11-13; D'Angelo Part I
  eq. 11 at k = 0). With the Minimoog's 0.068 uF and VT 26 mV, [DERIVED] If = 44.4 uA for 1 kHz; the patent's 1000:1
  range is then ~4.4 uA to 4.4 mA over 20 Hz to 20 kHz.
- With feedback: H(s) = 1 / ((s + 1)^4 + k) (Stinchcombe eq. 22; Zavalishin eq. 5.1; Stilson & Smith eq. 1). Poles
  s = -1 + k^(1/4) e^(±j pi/4), e^(±j 3pi/4); "at k = 4, the real component of the rightmost pair is zero ... the
  filter will be oscillating" (Stinchcombe §2.5); "At k = 4, the lowpass filter oscillates at its cut-off frequency"
  (Stilson & Smith fig. 2 caption).
- The pass band drops with resonance: H(0) = 1 / (1 + k), "a general issue with ladder filter designs" (Zavalishin p.
  134; D'Angelo Part I, the dc gain from eq. 7); "k = 4 is the biggest peak, at approximately -14 dB at the y-axis";
  "the 'droop' in the passband as the resonance is increased ... an easy test to see if a filter is of this type"
  (Stinchcombe p. 23).
- The cutoff law is the patent's exponential (§2.1); the Minimoog's SCALE trim sets its volts per octave. Which
  volts per octave the Minimoog's control node is calibrated to is not stated on the sheet [UNVERIFIED: 1 V/oct, the
  module's default].

## 5. Self-oscillation in the large-signal model [MEASURED]

The linear model oscillates at fc for k >= 4; the large-signal one does too, with an amplitude set by the stages'
tanh, and the swing's "cutoff reduction" (§3) lowers its pitch: the larger k, the larger the swing and the flatter.
RK4 at 64 x 44.1 kHz of §3's equations (`moog-research/ladder.c` mode 0 in the research's scratchpad), kicked and
settled, k / cents re fc / x4's peak: 4.05 / -5.1 / 0.057; 4.2 / -19.6 / 0.110; 4.5 / -42.8 / 0.164. The same at
1 kHz, 8 kHz, 12 kHz, 16 kHz (to 0.02 cents): it scales with fc, as the model is scale-free in wc. Onset: exactly
k = 4 (the linearisation). Whether a real Minimoog sings flat by this much at its top Emphasis is not checked
against hardware [UNVERIFIED].

## 6. The solve (research 2026-10-20) [MEASURED]

- Zavalishin §6.10: a ladder of nonlinear 1-poles is one 4-dimensional zero-delay feedback equation y = Phi(y)
  (eqs. 6.28-6.29), "the multidimensional form of Newton-Raphson algorithm can be used" (p. 207); §6.4-6.5 on
  convergence. The module does that for the transistor ladder: trapezoidal (TPT) stages prewarped at fc,
  F_i = x_i - s_i - g_i (tanh x(i-1) - tanh x_i), tanh x0 = tanh(u - k x4). The Jacobian is lower bidiagonal plus one
  corner entry (d F1 / d x4 = g1 k (1 - tanh^2 x0)), so a Newton step is a forward sweep: the correction of stage i is
  p_i + q_i d4, d4 = p4 / (1 - q4), and q4 <= 0 for k >= 0, so 1 - q4 >= 1: the step never divides by a small number.
- Huovilainen's alternative (forward Euler at 2x with a half-sample average in the loop and a tuning table, §5) and
  D'Angelo & Valimaki's Part II (an explicit delay-free-loop compensation, "comparable in terms of nonlinear behavior,
  and only slightly heavier" than [8, 104], dissertation §3.3.1) were not chosen: the Newton TPT is exact on the
  small-signal response (prewarped bilinear, no tuning table) and converges to the trapezoidal solution.
- Against the RK4 reference (sine in, the reference decimated by a 3073-tap Blackman sinc; `moog-research/measure.py`;
  worst harmonic-level error below 10 kHz, worst folded harmonic below 20 kHz, dB re the fundamental). K Newton
  iterations from the last step's solution, N steps a host sample, the output the steps' mean:

  | input (x = drive), fc, k, f0 | K1 N1 | K2 N1 | K8 N1 | K2 N2 | K8 N2 | K2 N4 | reference's alias floor |
  |---|---|---|---|---|---|---|---|
  | 5, 5 kHz, 3.0, 1.5 kHz | 3.19 dB / -73.8 | 0.36 / -84.4 | 0.38 / -83.5 | 0.38 / -98.0 | 0.38 / -98.0 | 0.40 / -97.0 | -111.6 |
  | 10, 12 kHz, 2.0, 2.5 kHz | 3.40 / -19.7 | 0.71 / -30.2 | 0.51 / -30.5 | 0.13 / -51.4 | 0.14 / -51.4 | 0.32 / -50.5 | -114.7 |
  | 20, 18 kHz, 3.9, 3.1 kHz | 17.6 / +133 (diverged) | 6.66 / -12.4 | 6.52 / -14.8 | 0.05 / -34.0 | 0.07 / -34.1 | 0.46 / -39.1 | -111.5 |
  | 5, 800 Hz, 3.5, 220 Hz | 0.76 / -194 | 0.12 / -194 | 0.12 / -194 | 0.09 / -194 | 0.09 / -194 | 0.08 / -194 | -192.5 |

  So: 2 iterations = converged (1 is not safe); 2 steps a sample buy ~20 dB of aliases where the drive and the
  cutoff are high; 4 steps with the mean as decimator buy little more (the mean is a weak decimator).
- Then the kit's halfband oversampler (HIIR, 99 dB stop band; references/dsp.md "Halfband oversampler") in place of
  the straight-line input and the steps' mean, K = 2, the module rendered (`moog-research/halfband_try.py`; worst
  alias, mean -> halfband): drive 10, fc 12 kHz, k 2: -51.4 -> -55.1; drive 20, fc 18 kHz, k 3.9: -34.0 -> -33.9
  (made above the doubled rate's Nyquist: only more steps would help); drive 5, fc 5 kHz, k 3: -98.0 -> -126.8;
  drive 10, fc 8 kHz, k 0: -68.3 -> -98.2. The 3rd harmonic stays within 0.45 dB of the reference's. The module: K = 2,
  `oversampling` 2 (the halfband pair, 3.07 samples late) by default, or 1.
- Cost (the kit renderer, compiled C, ns a host sample above an empty program, 2026-10-20): the module 247 (1x),
  497 (2x); the zero-delay ladder technique 74. So 2x is ~6.7x the technique.

## 7. The character and its defaults

| field | default | source |
|---|---|---|
| thermal_voltage_volts | 0.026 | [VERIFIED] §3 (26 mV at 300 K) |
| ladder_capacitance_farads | 0.068e-6 | [VERIFIED] Minimoog C3/C7/C11/C16 (§2.2); 904A ranges 1.2 / 0.3 / 0.075 uF (§2.3) |
| stage_n_capacitance_ratio | 1.0 | [DESIGN] matched; set a spread for one unit's capacitor tolerances (the sheet gives none) |
| input_pair_offset_volts | 0.0 | [DESIGN] the Minimoog marks Q29/Q30 matched (§2.2); an offset makes even harmonics |
| base_volts_per_input_volt | 0.05 | [UNVERIFIED] the input buffer / mixer's level at the input pair's bases was not traced: 1 V in = 50 mV = ~1 x 2VT, so a 1 V peak is the knee |
| ladder_current_at_zero_control_volts_amps | fc(0 V) = 261.63 Hz | [DESIGN] the RANGE / cutoff knob's offset is the instrument's |
| volts_per_octave | 1.0 | [UNVERIFIED] §4 |
| feedback_gain_at_full_emphasis | 4.2 | [UNVERIFIED] the REGEN CAL trim's setting is not on the sheet; 4.2 sings (§5: -19.6 cents, x4 swing 0.11) |
| output_coupling_corner_hz | 15.4 | [DERIVED] §2.2 |

## 8. Open

- The input level at the Minimoog's ladder (the mixer's gain into pin 4, the overdrive point players use) and the
  REGEN CAL trim's k: both need the mixer sheet traced or a measurement of a unit.
- The real circuit's non-idealities the model leaves out (finite beta and base currents, which Stinchcombe §2.4
  blames for the SPICE cutoffs sitting slightly lower than the formula; the Early effect; the expo converter's
  temperature drift).
- Whether hardware sings flat at high Emphasis as §5's model does.

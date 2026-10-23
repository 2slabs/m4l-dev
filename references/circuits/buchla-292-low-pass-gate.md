# Buchla 292 low pass gate: the vactrol and the network

The circuit behind `twosl_dsp/circuit_modules/buchla_292_low_pass_gate_channel.py` (architecture/dsp-blocks.md, "Circuit
modules"): one channel of the 292, its vactrol and its audio network. Written 2026-10-18 for 2sl gate from its LPG
audit (§1-§5); §6 is from 2sl gate's research brief (2026-10-17); both moved here with the module on 2026-10-20. What
the strike is (a hit's strength as an LED current) and the level-mode loudness are 2sl gate's (§3), kept here because
they are measured on this circuit. `fetch-circuit-sources.sh` downloads every source below into `sources/` (not in
git) and checks it is the copy this was read from (sha256).

## Buchla 292 low pass gate channel (twosl_dsp/circuit_modules/buchla_292_low_pass_gate_channel.py)

The network (§2: DAFx-13 eqs. 7-8, 11, Table 1; prewarped at its -3 dB corner), the photocell fit and the LED driver's
current range (§3), the vactrol's time behaviour (§4, §5: a measured VTL5C3/2 turn-off). The CV shelf of the control
circuit (eqs. 30ff.) is left out (§5). Character: the photocell fit, the driver's floor and ceiling, the highest
resonance share.

Tags: **[VERIFIED]** read in the source itself (paper text, datasheet table, the authors' code). **[DERIVED]** computed
from verified inputs; the method is given. Page numbers are PDF pages (`pdftotext -f N -l N`), not printed folios.

## 1. The sources

| file (in `sources/`) | what it is | URL |
|---|---|---|
| parker-dangelo-dafx13.pdf | J. Parker, S. D'Angelo, "A Digital Model of the Buchla Lowpass-Gate", DAFx-13 | https://www.dafx.de/paper-archive/2013/papers/44.dafx2013_submission_56.pdf |
| parker-dangelo-dafx13-authors-site.pdf | the same paper from the authors' companion site (the paper's footnote 3, acoustics.hut.fi/go/dafx13-lpg, redirects there) | https://research.spa.aalto.fi/publications/papers/dafx13-lpg/DAFx2013-LPG.pdf |
| LPG_demo.maxpat, LPG_nonlin.gendsp, poly_lpg.maxpat | the authors' Max / gen~ code: the control circuit, the vactrol filter, the network | …/dafx13-lpg/source/ |
| LPG_both_square.aif, LPG_both_FM.aif, LPG_both_noise.aif, LPG_LP_FM.aif | the authors' demo recordings | …/dafx13-lpg/ |
| najnudel-et-al-dafx23.pdf | J. Najnudel, R. Müller, T. Hélie, D. Roze, "Power-Balanced Dynamic Modeling of Vactrols: Application to a VTL5C3/2", DAFx-23 | https://www.dafx.de/paper-archive/2023/DAFx23_paper_50.pdf |
| vtl5c3-akizuki.pdf | VTL5C3 datasheet (the later Excelitas / PerkinElmer layout) | https://akizukidenshi.com/goodsaffix/vtl5c3.pdf |
| perkinelmer-vt500-catalog.pdf | PerkinElmer 2001 catalog "Photoconductive Cells and Analog Optoisolators (Vactrols)", the paper's ref. [14] | https://www.amstzone.org/PerkinElmer-VT500.pdf |
| portedplugins-lpg.{cpp,hpp}, portedplugins-LPG.{cpp,hpp} | Mads Kjeldgaard's SuperCollider port of the authors' code (matches it line for line) | https://github.com/madskjeldgaard/portedplugins @ c6c0d74 |

## 2. The network (Parker & D'Angelo) [VERIFIED]

- Table 1, p.2: C1 = 1 nF, C2 = 220 pF; C3 = 0 (Both, VCA) or 4.7 nF (Lowpass); Rα = 5 MΩ (Both, Lowpass) or 5 kΩ
  (VCA). The VCA mode's 4–5 dB of input gain (§2, p.2) is the core's ×1.6.
- Eq. 7, p.2: `H(s) = 1 / (α1 + α2 s + α3 s²)`.
- Eq. 8, p.2: `α1 = 1 + 2Rf/Rα`, `α2 = Rf (2C1 + C2 − C3(a − 1) + (C2 + C3) Rf/Rα)`, `α3 = Rf² C1 (C2 + C3)`.
- Eq. 11, p.3: `a_max = (2C1Rα + (C2 + C3)(Rα + Rf)) / (C3 Rα)`, the feedback gain where the Lowpass mode's poles reach
  the imaginary axis. Resonance 100 % in the core is a = 0.92 a_max (a design choice; `_check_the_gate_stays_damped`
  holds α2 > 0 there).
- Eq. 13, p.3: the bilinear transform of eq. 7; eqs. 14–22, p.4: the topology-preserving form, "stable under all
  physically reasonable parameter values and under any rate of modulation". The authors' `LPG_nonlin.gendsp` uses
  `f = 0.5/samplerate`, i.e. g = ω/(2·sr), no prewarp. The core (0.3.15) uses the kit's state-variable block (TPT, the
  same form) at ω_n = sqrt(α1/α3) and damping α2/sqrt(α1 α3), output × 1/α1, but prewarped (Zavalishin eq. 3.18,
  2sl-dsp references/dsp.md) at the -3 dB corner below, held at 16 kHz (eq. 3.21): level and both are overdamped, so
  the corner is far below ω_n, which passes Nyquist at bright hits (294 kHz in level mode at a full hit).
  **[MEASURED]** Unprewarped, the corner lands flat by the bilinear warp alone, the same in every mode: −3 / −12 /
  −45 / −98 / −165 / −243 cents at 1 / 2 / 4 / 6 / 8 / 10 kHz (44.1 kHz). Prewarped at it: 0.0 cents up to 16 kHz in
  every mode, and every state's g is at least the unprewarped one (tan(x)/x ≥ 1), so no hit is darker.
- **[DERIVED] The second pole.** For the both mode (C3 = 0) the two real poles satisfy
  `r + 2 + 1/r = α2²/(α1 α3)`, which is `(2C1 + C2)²/(C1 C2) = 22.4` while Rf ≪ Rα. So the second pole sits
  r = 20.3 times above the first (about 4.3 octaves) at 10 kΩ, 19.6 times at 100 kΩ and 14.5 times at 1 MΩ, where
  the divider acts. It is not "above 150 kHz" except below about 10 kΩ. Leaving it out stops the tail darkening at
  about −21 dB (a saw's harmonics 4–40 against its fundamental, C3); with it the tail goes on darkening: −27 dB at
  5 MΩ, −29 dB at 7 MΩ, −31 dB at 10 MΩ where the gate is shut (2sl gate's `tests/test_gate_dsp.py`
  `test_the_tail_keeps_darkening_with_the_second_pole`).
- **[DERIVED] The corner** (the display reads it; the network is prewarped at it) is where |H(jω)| is 3 dB under
  its DC gain 1/α1, in every mode: |α1 − α3ω² + jα2ω|² = 2α1² gives
  `ω² = 2α1² / (b + sqrt(b² + 4α1²α3²))`, b = α2² − 2α1α3 (the cancellation-free root; one pole when α3 → 0:
  ω = α1/α2). At Rf = 100 kΩ (both) that is 780 Hz, 9 % above the one-pole estimate 1/(2π Rf · 2.22 nF) = 717 Hz (the
  dominant pole alone, 782 Hz, is not the corner: the second pole takes a little; in filter mode the -3 dB point is
  above the natural frequency, 1.27 × at Resonance 0).

## 3. The LED current and Rf

- **Eq. 39, p.6 [VERIFIED]:** `Rf = A / If^1.4 + B`, A = 3.464 Ω·A^1.4, B = 1136.212 Ω. It is a division (the PDF's
  text layer drops the fraction bar; the authors' control-circuit codebox reads `Rf = B + A / pow(If,1.4)` with
  A = 3.4645912, B = 1136.2129956).
- **Which cell [DERIVED]:** eq. 39 gives 56 kΩ at 1 mA and 1.45 kΩ at 40 mA. The 2001 catalog's VTL5C3/2 (PDF p.52)
  is 55 kΩ at 1 mA and 2 kΩ at 40 mA, so the fit is to the **VTL5C3/2**. The VTL5C3 sheets disagree with it and with
  each other: Akizuki (p.1) 10 kΩ @ 1 mA, 1 kΩ @ 10 mA, 500 Ω @ 40 mA; the catalog (PDF p.50) 30 kΩ @ 1 mA.
- **The control circuit, eqs. 41–42, p.7 [VERIFIED]:** a shelving filter on the CV, then a log-amp LED driver with a
  3.9 V zener; If is held within [10.1 µA, 40 mA] (the codebox's `Ifmin`, `Ifmax`). Fig. 8, p.7: the Vc → If curve is
  near zero, then rises almost vertically at the knee.
- **The map at the authors' demo settings [DERIVED]** (their codebox run with `scale = 0.48`, hard-coded, and Offset
  0): `If = max(10.1 µA, 0.10074 mA/V · V)` up to 9.15 V (0.921 mA), then `0.92094 mA + 10.6068 mA/V · (V − 9.15)`,
  9.94 mA at 10 V. Rf: 34 MΩ at 0 V, 145 kΩ at 5 V, 63 kΩ at 9.1 V, 3.34 kΩ at 10 V. The two straight pieces meet
  0.09 % apart at the knee (0.92177 mA vs 0.92094 mA). 2sl gate 0.3.2–0.3.12 used exactly this, a hit's strength
  0..1 as 0..10 V; 0.3.13 does not (below).
- **Where the knee sits is a calibration, not the circuit [VERIFIED code, DERIVED numbers]:** in the codebox the knee
  is where the input current `Ia = Vb/R5 + Vs/(R3 (1 + R1/R2))` reaches `VB/(R6 + R7)` (`Ifbound2`). R6 is a trim,
  `R6 = scale × 20 kΩ`, with the comment "This value is tuned for appropriate input range", and R1/R2 is the demo's
  Offset control. Running the codebox at other trims (2026-10-19): scale 0.48 puts the knee at 9.15 V, 0.6 at 8.67 V,
  0.8 at 7.96 V, 1.0 (R6 = 20 kΩ, the paper's component value) at 7.36 V; at every one the current is about
  0.1 mA/V below the knee and about 10 mA/V above it. So a strike mapped linearly onto the CV meets a cliff
  wherever the trim puts it: at the demo's, a hit under strength 0.915 never passes the knee (the cell stays above
  63 kΩ, the both gate's corner near 1 kHz at the kit's velocity 100), and over the top 8.5 % of the range the
  current rises 11×. What the circuit fixes are its ends: `Ifmin` 10.1 µA and `Ifmax` 40 mA, the VTL5C3/2's rated
  LED current (the catalog's tables run to 40 mA; note 5 specifies the cell's tracking "from 0.4 to 40 mA").
- **The strike (2sl gate 0.3.13) [DESIGN on the above]:** a hit's strength s (0..1) spans the circuit's whole current
  range log-linearly, `If = 10.1 µA · (40 mA / 10.1 µA)^s` (`led_current`), the usual practice of scaling a control
  voltage into a stage's useful range. Why log-linear: eq. 39 is a power law, `Rf ≈ A If^−1.4` while Rf ≫ B, and the
  network's corner goes as 1/Rf (§2), so equal steps of strength are equal intervals of the gate's corner: no knee
  anywhere. Strength 0 is still dark (34 MΩ), so Open (the same map) still starts from a shut gate. A full hit is
  1.45 kΩ (was 3.34 kΩ). Measured (2sl gate: both mode, Init's timbre, its `tests/test_gate_dsp.py`): a 0.4 hit is 14.7 dB under a
  full one with a corner 450× (53 dB) darker 5 ms in (0.3.12: 11 dB, 125×): velocity still mostly sets brightness
  (SPEC §3.5). The kit's velocity 100 at Velocity 80 (strength 0.83) now reaches 9.8 mA, Rf 3.4 kΩ, where 0.3.12
  stopped at 0.84 mA, 72 kΩ. 2sl gate 0.3.1's map was this law from 10 µA to 40 mA (10 µA · 4000^s); 0.3.2 replaced
  it with the demo's map above for being the paper's, which it is only at the demo's trim.
- **The level mode [DERIVED, 2026-10-19]:** the VCA mode's divider (Rα 5 kΩ) passes `1.6 × 5 kΩ / (5 kΩ + 2 Rf)` of
  what the both mode passes at low frequencies; the 292's ×1.6 ("to match loudness", §2) matches the modes only
  where Rf ≈ 1.5 kΩ, the cell at its rated current (1.45 kΩ at 40 mA: ×1.01). Held there (Open 100 %) the modes
  measure within 0.5 dB. After a hit, Rf climbs along §5's law and the VCA divider closes long before the both
  network's corner falls into the music (−9.9 dB at 10 kΩ, −28.2 dB at 100 kΩ, where the both mode is still near
  0 dB with a 782 Hz corner). So the same hit is shorter and quieter in level mode, and more so the softer the hit:
  on the kit's phrase (2026-10-19, the kit's loudest-moment measure) Init in level mode is 6.2, 10.8 and 29.2 LU
  under both at strengths 1.0, 0.83 and 0.5 (filter within 0.6 LU of both). That is the circuit; a player of the 292
  gets level mode as loud by turning the CV up. 0.3.10–0.3.12 hid it with `LEVEL_MODE_DRIVE` (the divider reading the
  cell at 14× its current), a gain no source has, which 0.3.13 removes: the level-mode presets (paraphonic minor 7,
  thud, folded sub) take it back on their Output.

## 4. The vactrol's time behaviour

### 4.1 What the paper says, and what its code does [VERIFIED]
- §3.2, p.7, Fig. 9: an "ad-hoc non-linear filter", time constants "approx 12ms in the positive-going direction and
  250ms in the negative-going direction" (from the catalog for the VTL5C3/2), "modulated further by the current output
  value of the vactrol model, so that it responds quicker when at high values". "A voltage impulse … produces a quick
  drop in resistance … followed by a slower decay".
- The authors' code (`LPG_demo.maxpat`, codebox "Vactrol time-domain behaviour filter") is a TPT one-pole on the
  0..1 CV with `a = (1000π/sr)/t`: release `t_down = 10 + 3000 (1 − 0.9 s)`, attack `t_up = 1 + 20 (1 − 0.999 s)`
  (s its own output). Its output ×10 V goes into the control circuit. The strike is a 5 ms pulse of 1
  (`line~ "0, 1 0 1 5 0 0"`), and the network runs in `poly~ … up 8`.

### 4.2 The datasheets [VERIFIED]
| | turn-on to 63 % | turn-off to 100 kΩ (max) | off resistance |
|---|---|---|---|
| VTL5C3, Akizuki p.1 | 2.5 ms | 35 ms | ≥ 10 MΩ at 10 s |
| VTL5C3, catalog PDF p.50 | 2.5 ms | 35 ms | 10 MΩ |
| VTL5C3/2, catalog PDF p.52 | 3.0 ms | 50 ms | 10 MΩ |

Catalog PDF p.46 (the table and its notes): light history for the VTL5C3 and VTL5C3/2 "Very Small"; note 3,
"The ultimate resistance is many times greater than the value at 10 seconds"; note 4, the rise time is longer at
reduced drive "while the conductance decay time to a specified value is decreased"; note 5, "Typical matching and
tracking from 0.4 to 40 mA is 25%".

### 4.3 The measured turn-off (Najnudel et al., DAFx-23) [VERIFIED source, DERIVED numbers]
Fig. 7a, p.6, "Photoresistor's turn-off" for a VTL5C3/2: the red dashed "measurements" curve, read from the PDF's
vector paths (axes calibrated on the drawn gridlines; no image reading). R(t), ms / Ω:

| t | 4.7 | 10 | 19.7 | 50.5 | 99 | 150 | 185 |
|---|---|---|---|---|---|---|---|
| R | 13.3k | 24.2k | 50.3k | 174k | 414k | 730k | 901k |

It passes 100 kΩ at 31 ms, inside the catalog's 50 ms maximum. It is a power law: `R(t) = 3.4 kΩ · (1 + t/3 ms)^1.35`
fits it within ±5 % from 2 to 185 ms (rms of log10 error 0.021, a factor of 1.05). It changes fastest at the start.

### 4.4 Why the paper's own vactrol filter is not used [DERIVED]
Fitted to the measured turn-off from a steady 3.4 kΩ (rms of log10(R_model/R_measured), 2–185 ms):

| model | error factor |
|---|---|
| the authors' code as posted | 2.7× |
| the authors' law, its best fall constant | 1.9× |
| 2sl gate 0.3.1 (exponential light, log-mapped current), its best Decay | 2.4× |
| power law R0 (1 + t/t0)^p | 1.05× |
| 2sl gate 0.3.2 (§5), Decay 185 ms | 1.06× |

And the authors' code does not reproduce their own recording: in `LPG_both_square.aif` (a hit every 200 ms) the level
30–190 ms after each hit is −7, −10, −13, −15, −17, −18, −19, −21 dB under its 10 ms value, where the posted code
predicts −1 to −3 dB (12 dB rms error; no fall constant does better than 4.8 dB). `Rf = R0 (1 + t/t0)` (p = 1) fits all
12 hits to 1.1 dB rms. So the cell, the recording and the paper's own words ("a quick drop … followed by a slower
decay") agree on a power-law release; the posted filter is the outlier. Its network and its Rf fit stay; its
self-described ad-hoc vactrol filter is replaced.

## 5. The module's vactrol (2sl gate 0.3.2 on) [DERIVED from §3 and §4.3]

State: the effective LED current I (amps). The module takes the drive (`led_current_amps`), the attack time and the
Decay as inputs; the strike, Hold, Open and the mute are 2sl gate's (marked).
- Drive Id (2sl gate): a hit's current (§3's map) for an 8 ms pulse, the same current while a key is held with Hold on, Open's
  current, the largest of the three.
- Attack (Id > I): a one-pole toward Id over `attack_ms`; 2sl gate gives τ = 12 − 10·strength ms (its SPEC §3.5's
  2–12 ms), latched per hit (Open's from Open's level).
- Release (Id ≤ I): `dI/dt = −c (I² − Id²)` (recombination at a rate ∝ n²: my reading of the physics, not verified for
  the VTL5C3), stepped as `I ← (I + c·dt·Id²) / (1 + c·dt·I)`: unconditionally stable, monotone, never past Id. After a
  hit from I0: `1/I = 1/I0 + c t`, so `Rf(t) = A (1/I0 + c t)^1.4 + B`, §4.3's power law with exponent 1.4 (eq. 39's).
- Decay: the time a full hit (I0 = 40 mA since 0.3.13; 9.94 mA before) takes to reach Rf = 1 MΩ, `c = (1/I(1 MΩ) − 1/I0) / Decay`.
  **Decay 185 ms reproduces the measured VTL5C3/2** (1.06×). Without extra parameters this also gives a vactrol that
  is faster when bright (the paper's text), decays to a given R sooner from weaker drive (catalog note 4), and is still
  rising after seconds (10 MΩ at 5.2 Decays, ~1 s at 185 ms; catalog note 3).
- Rf = A·I^−1.4 + B into §2's network, one two-pole branch for every mode.
- The closed gate is silent (2sl gate, its SPEC §3.5): the output fades out linearly as Rf goes from 3 to 10 MΩ. The paper has no
  mute: at its dark 34 MΩ the both mode's DC gain is 0.068 with an 18 Hz corner, about −40 dB of bleed at C3, a floor
  visible in the authors' recordings.

What is left out, and why: the CV shelf (eqs. 30ff., zero 140 Hz / pole 169 Hz) is in the paper's equations but not in
the authors' gen~ code; light-history memory is "Very Small" for these cells (catalog p.46) and neither model
accumulates anything over repeated hits; the catalog's ±25 % unit-to-unit spread has nothing to act on with one gate
for all voices (SPEC §3.5).

## 6. From 2sl gate's research brief (§2.2.1-§2.2.3 there)

Source for 6.1–6.3 [VERIFIED]: Parker & D'Angelo, DAFx-13, https://www.dafx.de/paper-archive/2013/papers/44.dafx2013_submission_56.pdf

### 6.1 Audio path
- A simplified "canonical" 292, built from Buchla's 292 schematics and public-domain derivatives. Vactrol: **Perkin Elmer VTL5C3 or VTL5C3/2**. A 3-pole mode switch selects "Both" (combo), "VCA" or "Lowpass".
- **Both (combo):** passive two-pole network with cutoff set by Rf. "The poles of the filter are not-coincident, and so the slope of the filter is closer to −6dB/oct than −12db/oct." When Rf approaches Rα, a divider forms and gain drops.
- **VCA:** a low-value resistor in parallel with Rα (modelled as lowering Rα). The poles move up and the divider acts sooner, giving "reasonably clean attenuation". The real circuit also adds 4–5 dB input gain to match loudness.
- **Lowpass:** C3 is switched into a feedback path, making it "closely resemble a Sallen-Key". The response is steeper with a "small resonant bump". (The paper adds a resonance feedback amp `a`, which is **not** in original Buchla units.)
- **Component values:** C1 = 1 nF, C2 = 220 pF, C3 = 0 (Both/VCA) or 4.7 nF (LP); Rα = 5 MΩ (Both, LP) or 5 kΩ (VCA). Rf sweeps about 1 kΩ to 1 MΩ in the paper's plots.
- **Transfer function:** `H(s) = 1/(α1 + α2 s + α3 s²)` with
  `α1 = 1 + 2Rf/Rα`; `α2 = Rf(2C1 + C2 − C3(a−1) + (C2+C3)Rf/Rα)`; `α3 = Rf² C1 (C2 + C3)`.
  DC gain `= Rα/(Rα + 2Rf)`. Max stable resonance `a_max = (2C1Rα + (C2+C3)(Rα+Rf))/(C3Rα)`.
- **[DERIVED] Useful numbers, combo mode:** the dominant pole is at about `1/(2π·Rf·(2C1+C2)) = 1/(2π·Rf·2.22 nF)`. That is ≈ 7.2 kHz at Rf = 10 kΩ, ≈ 720 Hz at 100 kΩ, and ≈ 72 Hz at 1 MΩ (where DC gain = 5/7 ≈ −3 dB). ~~The second pole sits above about 150 kHz, so combo is effectively a one-pole LPG.~~ **Corrected 2026-10-18 [DERIVED]:** that holds only below about 10 kΩ. The second pole sits a fixed ~20× above the first (r + 2 + 1/r = (2C1+C2)²/(C1C2) = 22.4 while Rf ≪ Rα; 14.5× at 1 MΩ), so combo is a true two-pole network and the tail keeps darkening with it (§2).
  **VCA mode** (Rα = 5k): gain ≈ 0.71 at Rf = 1k, 0.20 at 10k, 0.024 (−32 dB) at 100k, and −46 dB at 1M.
- **Discretisation:** the direct-form bilinear version blows up under modulation ("Long-term modulation can cause the filter output to diverge to infinity"), because collapsing to a transfer function discards the true capacitor states. The **topology-preserving** version (trapezoidal integrators/differentiator, delay-free loops solved Zavalishin-style) is "stable under all physically reasonable parameter values and under any rate of modulation, without any oversampling". 2× oversampling is recommended only to reduce frequency warping. Closed-form per-sample solution (eqs. 20–22) for state update: see paper.
- **Nonlinearity:** the original is mostly linear. Older units used a transistor output buffer, which is more nonlinear. A tanh in the resonance path can be linearised per sample with a first-order Taylor expansion around the previous sample.

### 6.2 Control path and vactrol
- **Control circuit:** first-order shelving filter on the CV input plus offset, then a log-amp-like LED driver with a 3.9 V zener limiter. Values: Cc = 2 nF, R3 = 150k, R4 = 470k, R5 = 100k, R6 = 20k, R7 = 33k, R8 = 4.7k, R9 = 470 Ω, Vs = 15 V. LED current clamped to **If ∈ [10 µA, 40 mA]**.
  [DERIVED] The CV shelf has a zero near 140 Hz, a pole near 170 Hz, and an HF gain of (R4+R5)/R4 ≈ 1.21 (+1.7 dB). Fast trigger edges get a small extra kick.
- **Current → resistance (datasheet fit):** `Rf = A / If^1.4 + B`, A = 3.464, B = 1136.212 Ω (eq. 39, p.6). **[VERIFIED 2026-10-18]**: a division; the PDF's text layer drops the fraction bar, and the authors' code reads `Rf = B + A / pow(If,1.4)`. 10 mA → ≈3.3 kΩ, 40 mA → ≈1.45 kΩ, 10 µA → ≈35 MΩ. It fits the VTL5C3/2 (55 kΩ @ 1 mA), not the VTL5C3 (§3).
- **Vactrol dynamics (heuristic model):** an integrator-based lowpass whose time constant switches on the sign of the input derivative. "approx **12ms** in the positive-going direction and **250ms** in the negative-going direction" for the VTL5C3/2. That value "is then modulated further by the current output value of the vactrol model, so that it responds quicker when at high values, as also indicated on the datasheet."
  **[VERIFIED 2026-10-18] Those are the text's numbers, not the code's.** The authors' posted gen~ (`LPG_demo.maxpat`) releases with τ from 49 ms (bright) to 479 ms (dark) and attacks with τ from 0.16 to 3.3 ms, and it matches neither the measured VTL5C3/2 turn-off (2.7× off) nor the authors' own demo recording (§4). The control map at the demo settings is linear in the CV with a zener knee, not logarithmic.
- **The model was implemented in Max/MSP gen~.** The demo exposes CV in, CV offset, lowpass on/off, resonance, and a continuous **Rα control to morph filter-like ↔ VCA-like**. [VERIFIED] Forum users report the posted patch crashes on modern Max: https://cycling74.com/forums/gen~-no-acumulator-integral-symbol-feedback-in-patch/. A SuperCollider port exists, `LPG.ar(input, controlinput, controloffset, controlscale, vca, resonance=1.5, lowpassmode, linearity)`: https://doc.sccode.org/Classes/LPG.html

### 6.3 Vactrol datasheet and physics
- **VTL5C3 datasheet** [VERIFIED] https://akizukidenshi.com/goodsaffix/vtl5c3.pdf : ON resistance ≈ 10 kΩ @ 1 mA, 1 kΩ @ 10 mA, 500 Ω @ 40 mA; dark ≥ 10 MΩ (after 10 s); slope 20; dynamic range 75 dB; **turn-on to 63% ≈ 2.5 ms; turn-off (decay) to 100 kΩ ≈ 35 ms** (after a 24 h @ 40 mA light-adapt). "small light history memory". LED max 40 mA.
  **Corrected 2026-10-18:** these are not the numbers the paper fit. Its eq. 39 is a fit to the **VTL5C3/2** (PerkinElmer 2001 catalog: 55 kΩ @ 1 mA, 2 kΩ @ 40 mA, turn-on 3.0 ms, turn-off to 100 kΩ 50 ms), and the two VTL5C3 sheets disagree with each other by about 3× (§3, §4.2).
  - ~~Reconciling with Parker's 12 ms / 250 ms~~ (superseded): the measured VTL5C3/2 turn-off is a power law, R = 3.4 kΩ (1 + t/3 ms)^1.35 (Najnudel et al., Fig. 7a), fastest at the start; §4.3.
- **Physics-based model:** Najnudel, Müller, Hélie & Roze, "Power-Balanced Dynamic Modeling of Vactrols: Application to a VTL5C3/2", DAFx-23. A port-Hamiltonian semiconductor model. Response times range "from a few tens of microseconds (for the turn-on…) to a few hundreds of milliseconds (for the turn-off…). Moreover, the attack time decreases with the received light." Theoretical turn-on is 3 ms in their fit. Overkill for a synth voice but useful as ground truth. [VERIFIED] https://www.dafx.de/paper-archive/2023/DAFx23_paper_50.pdf
  Its Fig. 7a (p.6) is a **measured VTL5C3/2 turn-off**, the curve 2sl gate's vactrol is fitted to (§4.3).
- Clones commonly fight **bleed** (signal leaking through a "closed" VTL5C3 gate). Some drop VCA mode. [SECONDARY] https://modularsynthesis.com/roman/buchla292c/292qlpg.htm and search summaries. [DESIGN] Model a tiny residual bleed (−60 to −70 dB of HF) for authenticity, with a switch to disable it.
- An alternative Sallen-Key LPG derivation (Theory page of an open LPG project): VCF cutoff ≈ 70 Hz–7 kHz for R from 1 MΩ to <10 kΩ; combo = first-order LP `fc = 1/(4πRCg)`. [SECONDARY] https://low-pass-gate.readthedocs.io/en/stable/theory.html

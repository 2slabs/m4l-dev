# DSP sources: the kit's techniques

What the techniques (architecture/dsp-blocks.md; `m4l_dev/techniques/`) are built from, with quotes and pages. A
circuit module's sources are its circuit's own file in `circuits/`.
`fetch-dsp-sources.sh` downloads every source below into `references/dsp-sources/` (not in git) and checks each is
the copy these notes were written from (sha256, fetched 2026-10-18 and 2026-10-19). Page numbers are the printed
page, with the PDF page in brackets where they differ.

## Zero-delay ladder filter (m4l_dev/techniques/zero_delay_ladder_filter.py)

**Zavalishin, *The Art of VA Filter Design*, rev. 2.1.2 (2020)** (`zavalishin-va-filter-design-2.1.2.pdf`;
NI's URL is gone, the Wayback copy is fetched).
- §5.2, p. 135 [147]: "the resonance frequency is approaching the filter cutoff frequency as the filter approaches
  selfoscillation at k = 4."
- §5.2, p. 137 [149]: "the amplitude response of a chain of four 1-poles is (1/√2)^4 = 1/4. According to (5.7),
  the infinite resonance is attained at k = 1/(1/4) = 4."
- §5.3, p. 138 [150], eq. (5.8): "u = x − ky = x − k(Gu + S) from where u = (x − kS) / (1 + kG)"; "We can then use
  the obtained value of u to process the 1-pole lowpasses one after the other, updating their state"; "the filter
  doesn't become instantaneously unstable provided k ≥ −1."
- §5.4, p. 138 [150]: "at high resonance settings the amplitude gain of the filter at low frequencies drops ... An
  obvious way to fix this problem would be e.g. to boost the input signal by the (1+k) factor." (The technique keeps
  2sl stab's milder make-up, 1 + 0.4 k.)
- §6.6, p. 191 [203]: replacing tanh u by u "is equivalent to one step of Newton–Raphson with u = 0 as the initial
  guess." p. 192 [204]: the tangent at the last value "usually ... provides a better result, however in the
  excessive (but not so unusual) situations of high cutoff, high feedback amount and/or high signal frequencies
  this c[an work worse]"; "Linearization by secant line ... in moderately excessive situations this could work
  better than the linearization at the operating point, but at more excessive settings could work worse than the
  linearization at zero."

The technique is (5.8) with the tanh applied to the solved u (linearised at zero). The research behind the choice
(2026-10-19, against RK4 at 8x of each analog model): an exact Newton solve of the same loop measured the same
(-52.6 dB error vs the model, both); the per-stage tanh ladder (the secant linearisation above, at a linear
predictor) tracks its own model as well but its self-oscillation sinks 4 to 32 cents flat with its amplitude (the
analog model does the same), so it isn't kept. Huovilainen (DAFx-04) uses five tanh and 2x oversampling for that
model; not needed here.

## Zero-delay state-variable filter (m4l_dev/techniques/zero_delay_state_variable_filter.py)

**Zavalishin, *The Art of VA Filter Design*, rev. 2.1.2 (2020)** (`zavalishin-va-filter-design-2.1.2.pdf`).
- §4.1, p. 95 [107], eq. (4.1): "yHP = x − 2RyBP − yLP, ẏBP = ωc · yHP, ẏLP = ωc · yBP"; p. 96 [108]:
  "HLP(s) = ωc² / (s² + 2Rωc s + ωc²)", HBP = ωc s / (…), HHP = s² / (…).
- §4.1, p. 97 [109], eq. (4.4): "yLP(t) + 2RyBP(t) + yHP(t) = x(t), that is, the input signal is split into lowpass,
  bandpass and highpass components."
- §4.4, p. 110 [122], eq. (4.14): "yHP = (x − (2R + g)s1 − s2) / (1 + 2Rg + g²)"; "as long as g > 0 and R > −1, the
  denominator of (4.14) is always positive ... the filter in not becoming instantaneously unstable"; "sn are the
  states of the z⁻¹ elements in the respective integrators and g = ωcT/2 (prewarped)"; the tick:
  "HP := (x-g1*s1-s2)*d; // g1=2R+g, d=1/(1+2Rg+g^2) / v1 := g*HP; BP := v1+s1; s1 := BP+v1; / v2 := g*BP; LP := v2+s2; s2 := LP+v2;"
- §4.5, p. 111 [123], eq. (4.15): "By multiplying the bandpass filter's output by 2R ... we obtain a bandpass filter
  which has a unit gain (and zero phase response) at the cutoff".
- §3.8, "Other prewarping points", pp. 64–65 [76–77], eq. (3.18): "ω̃c = µ(ωp)/ωp · ωc"; "Equation (3.18) is the
  generalized prewarping formula, where ωp is the frequency response point of zero detuning ... prewarping at ωp
  simply means that the cutoff should be multiplied by µ(ωp)/ωp. At ωp = ωc this multiplication reduces to (3.12)."
  (µ(ω) = (2/T) tan(ωT/2), so g = tan(π fp / sr) · fc / fp.)
- §3.8, "Bounded cutoff prewarping", p. 67 [79], eq. (3.21): "as the cutoff peak is getting out of the audible range,
  we stop caring, where exactly it is positioned ... we could fix the prewarping point to the upper boundary of the
  audible range: ωp = min {ωc, ωmax}, where ωmax is some point around 16kHz."

The technique is that tick, with 2R = 1 / Q (the circuit literature's Q, e.g. a unity-gain Sallen-Key's
Q = ½ √(C1/C2)) and g = tan(π fp / sr) · fc / fp, prewarped at fp (by default the cutoff: g = tan(π fc / sr)). Not the LTC1060 / MF10 module's LDI (Chamberlin) form,
which is a clocked chip's own recursion and is kept for that (circuits/ltc1060-mf10.md).

## Antiderivative piecewise-linear shaper (m4l_dev/techniques/antiderivative_piecewise_linear_shaper.py)

The same method as the tanh saturator's (above): **Bilbao, Esqueda, Parker & Välimäki 2017**, eq. (5), first-order
ADAA, y = (F1(x) − F1(x_before)) / (x − x_before), with §II.B's midpoint fallback where the step is too small to divide
by. A piecewise-linear transfer's F1 is closed form piece by piece (each piece's integral is a quadratic), the case
**Esqueda, Pöntynen, Parker & Bilbao, "Virtual Analog Models of the Lockhart and Serge Wavefolders", Applied Sciences
7(12):1328, 2017** (https://www.mdpi.com/2076-3417/7/12/1328) applies first-order ADAA to, "allowing real time without
high oversampling factors" (its intro; the 2sl gate research brief, circuits/buchla-259.md §6). The table, its digest-named
functions and the balanced comparison tree are our construction; tests/test_techniques.py holds them to the Python
model and measures the aliases against the transfer taken naively.

## Antiderivative tanh saturator (m4l_dev/techniques/antiderivative_tanh_saturator.py)

**Bilbao, Esqueda, Parker & Välimäki, "Antiderivative Antialiasing for Memoryless Nonlinearities", IEEE SPL 24(7),
2017, pp. 1049–1053** (`bilbao-adaa-spl2017.pdf`, Aalto's accepted version).
- §II.A, eq. (5) [PDF p. 3; the PDF has a cover page]: "y^n = (F1^n − F1^(n−1)) / (x^n − x^(n−1)). Here, F1^n = F1(x^n) represents the first
  antiderivative of F0 evaluated at x^n." "the input sequence x^n is assumed drawn from samples of a piecewise
  linear underlying function x(t), which is then convolved with a box function of one sample duration, and then
  resampled."
- §II.B "Precision and Ill-Conditioning" [PDF p. 4]: "there is thus the risk of loss of precision or division by zero
  when the denominator is small"; for |x^n − x^(n−1)| ≤ ε, "D− G1^n = G0(x̄^(n−1/2)), x̄^(n−1/2) = (x^n + x^(n−1))/2".
- §IV [PDF p. 5]: "the proposed methods are more efficient than oversampling".

**Parker, Zavalishin & Le Bivic, "Reducing the aliasing of nonlinear waveshaping using continuous-time
convolution", DAFx-16** (`parker-zavalishin-lebivic-dafx16.pdf`): the method eq. (5) of Bilbao et al. takes "on a
particularly simple form" from ([22] there). Higher orders need tanh's second antiderivative (a dilogarithm); not
used.

**Smith, *Physical Audio Signal Processing*, "Thiran Allpass Interpolators"** (`jos-thiran-allpass.html`):
an order-N allpass "can be designed having maximally flat group delay equal to Δ at dc using the formula
a_k = (−1)^k (N choose k) Π_{n=0..N} (Δ−N+n)/(Δ−N+k+n)". For N = 1, Δ = 0.5: a1 = (1 − Δ)/(1 + Δ) = 1/3.
The technique puts the linear part of tanh through it (half a sample, flat magnitude) and antialiases only the residual
tanh x − x, so both halves are half a sample late and small signals aren't low-passed. (Our construction from the
two sources; measured in the module docstring and tests/test_techniques.py.)

## Band-limited edges (m4l_dev/techniques/band_limited_edges.py)

**Esqueda, Välimäki & Bilbao, "Rounding Corners with BLAMP", DAFx-16** (`esqueda-blamp-dafx16.pdf`).
- Abstract [p. 1]: "The polynomial BLAMP can reduce the level of aliasing components by up to 50 dB".
- Table 1 [p. 3]: "Third-order B-spline basis functions, its first integral (polyBLEP), its second integral
  (polyBLAMP), and polyBLAMP residual", per span [−2T, −T], [−T, 0], [0, T], [T, 2T]; "Four-point polyBLAMP
  residual": d^5/120; −d^5/40 + d^4/24 + d^3/12 + d^2/12 + d/24 + 1/120; d^5/40 − d^4/12 + d^2/3 − d/2 + 7/30;
  −d^5/120 + d^4/24 − d^3/12 + d^2/12 − d/24 + 1/120. The technique's tables are derived again from the B-spline
  (exact fractions) and equal these.

**Välimäki, Pekonen & Nam, "Perceptually informed synthesis of bandlimited classical waveforms using integrated
polynomial interpolation", JASA 131(1), 2012, pp. 974–986** (`valimaki-polyblep-jasa2012.pdf`).
- Abstract [p. 974]: "the integrated third-order B-spline correction function ... offers perceptually aliasing-free
  sawtooth emulation up to the fundamental frequency of 7.8 kHz at the sample rate of 44.1 kHz."
- [p. 982]: "the second-order PolyBLEP is free from aliasing up to about 2 kHz" (what 2sl stab had).

## Tape-style echo (m4l_dev/techniques/tape_style_echo.py)

**Downing & Terjesen, "Real-time digital modeling of the Roland Space Echo", U. Rochester ECE 472 class project,
2016** (`downing-terjesen-re201-2016.pdf`; not peer-reviewed).
- §3 [p. 3]: "Our measured time constants were 1.89s for increasing delay time, and 1.07s for decreasing delay
  time." (The echo's glide keeps their ratio, shorter: a synced echo.)
- §3.1 [p. 2]: "The spectrum of the delay speed showed a sharp cutoff at approximately 1 Hz. We measured the variance
  of the delay trajectory signal fed through low pass filter with a 1 Hz cutoff" (the echo's wow: noise low-passed
  at 1 Hz).
- §3 [p. 3]: "the self-oscillation which occurs at particular frequencies at high feedback settings is integral to
  many Space Echo-produced sounds effects."

**Chowdhury, "Real-time physical modelling for analog tape machines", DAFx-19** (`chowdhury-tape-dafx19.pdf`):
tape as hysteresis plus playback-head loss filters. Not modelled; the echo's tape is a saturating loop, which is why it is a technique and not a circuit
module of a tape machine.

## Knee soft clip (m4l_dev/techniques/knee_soft_clip.py)

No outside source: our construction, stated whole in the module docstring. Unity up to the knee, then
knee + (1 - knee) tanh((|x| - knee) / (1 - knee)): the line's value and slope (tanh'(0) = 1) at the knee, so the join is
C1, and bounded by 1. It replaced three devices' identical copies bit for bit (2sl gate, stab, filter).

## Sidechain-style pump (m4l_dev/techniques/sidechain_style_pump.py)

No outside source: our construction, stated whole in the module docstring (a quarter-sine ramp in, a power-law recovery,
a gain 1 - depth x duck, or the gate 1 - depth x (1 - duck)). The sound it imitates is a compressor ducked by a kick
(sidechain pumping); it models no compressor, it draws the dip from the beat. It replaced two devices' own copies (2sl
stab: quarter-sine ramp in, `1 + 3 curve` power recovery, 20 ms hand-over between Live's clock and its own, a 0.442 ms
glide on the gain; 2sl filter: a 3 ms linear ramp in, a squared recovery, a hard switch between the two clocks, no
glide, plus the gate) with stab's, which is continuous at every join and glides every change.

## Zero-delay one-pole filter (m4l_dev/techniques/zero_delay_one_pole_filter.py)

**Zavalishin, *The Art of VA Filter Design*, rev. 2.1.2** (`zavalishin-va-filter-design-2.1.2.pdf`).
- §3.10, p. 78 [90], "1-pole allpass": the TPT one-pole's tick, `yAP = yLP − yHP` with
  `xs := x - s; s := s + xs*2Glp; y := s - xs;`, `Glp = g/(1+g)` (allpass-and-diffusion.md §1 quotes it whole).
- §3.9 (zero-delay feedback): a loop through such stages is solved by writing each stage's output as an affine function of
  its input this sample and solving the loop equation for it (the method the ladder uses, eq. 5.8, here for a chain).
- §3.8, eq. (3.18): the prewarping point, as the state-variable filter's (above).

The technique is the tick's LP and HP (`v = G (x − s)`, `LP = v + s`, `s = LP + v`, `HP = x − LP`) and their affine
responses `LP = G x + (1 − G) s`, `HP = (1 − G) x − (1 − G) s`, our algebra from the tick. Its LP − HP all-pass is not
the kit's all-pass section: under fast cutoff modulation it gains energy (below, and tests/test_techniques.py).

## Zero-delay all-pass cascade (m4l_dev/techniques/zero_delay_allpass_cascade.py)

Transfer functions: **Zavalishin rev. 2.1.2** eq. (2.12), p. 29, `H(s) = (1 − s)/(1 + s)`, and §4.7 eq. (4.23), p. 119,
`HAP(s) = (s² − 2Rs + 1)/(s² + 2Rs + 1)`; "high order allpasses are often created by simply connecting several of 1- and
2-pole allpasses in series" (p. 30); "The most common VA use for the allpass filters is probably in phasers" (footnote
23, p. 29). The phaser's notch / peak mathematics (allpass-and-diffusion.md §1 [DERIVED]): n equal first-order stages and
an equal dry give notches at ω/ωc = tan((n − 2m − 1)π/(2n)); feedback g gives peaks 1/(1 − g) where the phase is a whole
turn.

Realisation [DERIVED, ours; tested]: the bilinear transform (prewarped, eq. 3.18) of the first-order all-pass is
`H(z) = (k + z⁻¹)/(1 + k z⁻¹)`, `k = (g − 1)/(g + 1)`; of the second-order one
`(a2 + a1 z⁻¹ + z⁻²)/(1 + a1 z⁻¹ + a2 z⁻²)`, `D = 1 + 2Rg + g²`, `a2 = (1 − 2Rg + g²)/D`, `a1 = 2(g² − 1)/D`. Each is
built as a lattice of junctions `[y; f] = [[k, c], [c, −k]]·[x; v]`, `c = √(1 − k²)`, `v` the delayed return of the inner
all-pass (`A_m = (k_m + z⁻¹A_{m−1})/(1 + k_m z⁻¹A_{m−1})`, the nested form JOS gives, `jos-nested-allpass.html` in
phaser-diffusion-sources/, with `k2 = a2`, `k1 = a1/(1 + a2) = (g² − 1)/(g² + 1)`); the junction substituted gives
`y = x (k + z⁻¹A)/(1 + k z⁻¹A)` (our algebra). The matrix is orthogonal, so each sample conserves
`|y|² + |states|²` whatever k does: lossless under any modulation (the "normalized lattice" of Gray and Markel
[UNVERIFIED citation: not fetched]). The TPT one-pole's LP − HP is the same map with its state scaled by
`√((1 − k)/(1 + k))`; when k moves, that scaling moves and energy enters. Measured (tests/test_techniques.py): with
the cutoff jumping across the band every sample, a TPT all-pass section turns a unit-bounded input into 7.7, six of
them 470, and a 0.5 feedback loop around six diverges; the lattice conserves energy to 1e-9 and stays bounded in the
same loop. Zavalishin's footnote 29, p. 42, warns that the continuous-time "cutoff modulation cannot destroy stability"
argument "will not automatically hold" after discretisation: this is that case.

## LED-driven photocell (m4l_dev/techniques/led_driven_photocell.py)

**Parker & D'Angelo, "A Digital Model of the Buchla Lowpass-Gate", DAFx-13** (`parker-dangelo-dafx13.pdf`).
- p. 6, eq. (39): `Rf = A / If^1.4 + B`, "where A = 3.464 ΩA1.4 and B = 1136.212 Ω" (the text layer drops the fraction
  bar; the authors' code reads `Rf = B + A / pow(If,1.4)`, 2sl gate references/vactrol-and-lpg.md §3). A fit to the
  VTL5C3/2 (56 kΩ at 1 mA, 1.45 kΩ at 40 mA).
- p. 7: the cell's time constants "approx 12ms in the positive-going direction and 250ms in the negative-going
  direction" (from the PerkinElmer catalog, their ref. [14]).

**Najnudel, Müller, Hélie & Roze, "Power-Balanced Dynamic Modeling of Vactrols: Application to a VTL5C3/2", DAFx-23**
(`najnudel-et-al-dafx23.pdf`): p. 6, Fig. 7a, "Photoresistor's turn-off", the measured curve; read from the PDF's vector
paths in 2sl gate (vactrol-and-lpg.md §4.3), `R(t) = 3.4 kΩ (1 + t/3 ms)^1.35` within ±5 % over 2–185 ms [DERIVED there].

**PerkinElmer, "Photoconductive Cells and Analog Optoisolators (Vactrols)", 2001** (`perkinelmer-vt500-catalog.pdf`):
PDF p. 50, VTL5C3 turn-on to 63 % 2.5 ms, turn-off 35 ms; p. 46 notes 3 ("The ultimate resistance is many times
greater than the value at 10 seconds") and 4 (the rise time is longer at reduced drive "while the conductance decay
time to a specified value is decreased").

The technique is 2sl gate 0.3.2's vactrol (vactrol-and-lpg.md §5, our model on the above): attack a one-pole toward the
drive; release `dI/dt = −c (I² − Id²)` stepped `I ← (I + c dt Id²)/(1 + c dt I)` (recombination at a rate ∝ n²: a
reading of the physics, unverified for any cell), which with eq. (39) gives the measured power-law turn-off; the law
and the times are the caller's. 2sl gate's version floors the drive at the driver's minimum current; this one floors
the state, so `release_ms` is exactly the undriven time from `release_from_amps` to `release_to_amps`.

## gen~ (what Max accepts)

- **delay** (Cycling '74, Gen reference: https://docs.cycling74.com/reference/gen_dsp_delay/, read 2026-10-19):
  "The first argument specifies the maximum delay time (in samples, default samplerate). The second argument
  specifies the number of tap inlet/outlet pairs (default 1)." interp: "'cubic' performs four-point cubic
  interpolation, 'spline' performs four-point Catmull-Rom spline interpolation". "With @feedback enabled, the
  minimum delay time is increased by 1 sample."
- **gen~ delay taps in GenExpr**: Rodrigo Constanzo's data-knot (`data-knot-dk_reverb_library.genexpr`, commit
  e8ebcec), real GenExpr run in Max, declares `Delay zeroDel2(24577, 2, feedback=0);` and reads it at two places
  (`zeroDel2.read(pDelA, interp="fastcubic")`, `zeroDel2.read(pDelB, interp="fastcubic")`). So the echo's tapes,
  read at T and at T − D, are `Delay ...(size, 2)`, and the kit's renderer refuses a Delay read at more places than
  it has taps.
- **GenExpr** (https://docs.cycling74.com/userguide/gen/gen_genexpr/): "functions must be declared before all
  statements"; functions take arguments and "can return multiple values". The gen blocks keep to the kit renderer's
  subset (one return value, no loops), which is narrower.

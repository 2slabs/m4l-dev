# DSP sources: the kit's techniques

What the techniques (architecture/dsp-blocks.md; `m4l_dev/techniques/`) are built from, with quotes and pages. A
circuit module's sources are its circuit's own file in `circuits/`.
`fetch-dsp-sources.sh` downloads every source below into `references/dsp-sources/` (not in git) and checks each is
the copy these notes were written from (sha256, fetched 2026-10-18, 2026-10-19 and 2026-10-21). Page numbers are the printed
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
  obvious way to fix this problem would be e.g. to boost the input signal by the (1+k) factor." (The technique gives
  the ladder's own output; a make-up, if any, is the instrument's.)
- §6.6, p. 191 [203]: replacing tanh u by u "is equivalent to one step of Newton–Raphson with u = 0 as the initial
  guess." p. 192 [204]: the tangent at the last value "usually ... provides a better result, however in the
  excessive (but not so unusual) situations of high cutoff, high feedback amount and/or high signal frequencies
  this c[an work worse]"; "Linearization by secant line ... in moderately excessive situations this could work
  better than the linearization at the operating point, but at more excessive settings could work worse than the
  linearization at zero."

The technique is (5.8) with the tanh applied to the solved u (linearised at zero); its linear form is (5.8) as it
stands, no tanh, and since its resonance is infinite at k = 4 (§5.2, above) and nothing bounds a linear loop past
it, the linear form's k stays under 4 (3.9 at Resonance 1, a design choice). The research behind the choice
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

The same method as the tanh saturator's (below): **Bilbao, Esqueda, Parker & Välimäki 2017**, eq. (5), first-order
ADAA, y = (F1(x) − F1(x_before)) / (x − x_before), with §II.B's midpoint fallback where the step is too small to divide
by. A piecewise-linear transfer's F1 is closed form piece by piece (each piece's integral is a quadratic), the case
**Esqueda, Pöntynen, Parker & Bilbao, "Virtual Analog Models of the Lockhart and Serge Wavefolders", Applied Sciences
7(12):1328, 2017** (https://www.mdpi.com/2076-3417/7/12/1328) applies first-order ADAA to, "allowing real time without
high oversampling factors" (its intro; the 2sl gate research brief, circuits/buchla-259.md §6). The table, its digest-named
functions and the balanced comparison tree are our construction; tests/test_techniques.py holds them to the Python
model and measures the aliases against the transfer taken naively.

Second order: the same paper, §II.A eq. (15) [PDF p. 3], "y^n = 2/(x^n − x^(n−2)) ((F2^n − F2^(n−1))/(x^n − x^(n−1)) −
(F2^(n−1) − F2^(n−2))/(x^(n−1) − x^(n−2)))", and §II.B's fallbacks [PDF p. 4]: (17) for a short step (G1 at the
midpoint), (18) "D2 G2^n = 2/Δ (G1(x̄^n) + (G2^n − G2(x̄^n))/Δ)" with (19) "x̄^n = (x^(n+1) + x^(n−1))/2,
Δ^n = x̄^n − x^n" where the outer two inputs nearly meet, and (20) G0 at (x̄ + x^n)/2 where Δ is small too; §IV: "For
hard clipping, the second- and third-order forms increase SNR by approx. 15 and 30 dB w.r.t. oversampling by factor 6".
Taking it piece-wise (a line at the three's mean on one piece; the lower piece's line plus the slope change times
eq. (15) of a ramp in coordinates at the corner across one corner; eq. (15) itself across more) is our construction
for conditioning: F2 is a cubic of the input, and eq. (15) divides its differences by products of steps that are tiny
near a corner at a slow input. tests/test_techniques.py holds it to eq. (15) in exact rational arithmetic and
measures the aliases against first order (a hot 3 kHz clip at 44.1 kHz, run at 1×, below 10 kHz: −55.3 → −72.6 dB;
through the 2× equaliser, wrongly at that rate, −69.9).

A table that moves at run time (a circuit's rail moving its breakpoints: `PiecewiseLinearMotion`) is our
construction too: the paper's formulas take one transfer; ours takes each sample's eq. (15) on the transfer as it is
at that sample (the piece-wise form keeps no antiderivative across samples), so a moving table is ADAA2 of its
present transfer, which moves continuously with it.

ADAA2's linear filtering is undone (or not) by the kit's one ADAA equaliser (below, "Antiderivative antialiasing
equaliser"), the tanh saturator's too. Not chosen: AA-IIR kernels (**La Pastina, D'Angelo & Gabrielli, "Arbitrary-order
IIR antiderivative antialiasing", DAFx20in21** (`lapastina-dangelo-gabrielli-dafx21.pdf`),
https://www.dafx.de/paper-archive/2021/proceedings/papers/DAFx20in21_paper_27.pdf, the "generalisations" route: a
Butterworth or Chebyshev kernel, at the cost of complex exponential integrals of the transfer per pole); and the line
split the tanh saturator used to use, whose error once a folder folds is (1 − the 3-tap mean) × (the line − the
transfer), the line's whole size at the input's frequency.

## Antiderivative antialiasing equaliser (m4l_dev/techniques/antiderivative_antialiasing_equaliser.py)

ADAA's linear filtering: Bilbao et al. 2017 (above), §II.A after eq. (16) [PDF p. 4]: "In practice, though aliasing is
indeed suppressed, such methods do introduce a degree of linear filtering to the original signal, and thus all
evaluation in Sec. IV will be carried out at a 2× oversampled rate"; §IV [PDF p. 5]: "An inherent characteristic of
this family of methods is that of spectral shaping of the output; though aliasing is suppressed, there can be some
attenuation of the signal in the high frequency range. Additional linear filtering is one option in this case, as
suggested in [33], [34] for antialiased oscillators. ... generalisations beyond the nested structures presented here
could aid in finding antialiasing methods for which such attenuation is reduced." [34] is Välimäki, Pekonen & Nam
2012 (below, `valimaki-polyblep-jasa2012.pdf`), pp. 978–979 [PDF pp. 5–6], eq. (16): "... amplitudes of the higher
harmonics are to be restored to the desired level, a post-processing equalizing filter can be used. In practice, a
low-order filter, which is independent of the fundamental frequency, will suffice ... a second-order linear-phase FIR
filter expressed as Heq(z) = b0 + b1 z^−1 + b0 z^−2".

The kernels (ADAA of a straight line): first order the 2-tap mean (1 + z^−1)/2, zero-phase cos(w/2), half a step late
(−2.4 dB at 10 kHz at 44.1 kHz); second order the 3-tap mean (1 + z^−1 + z^−2)/3, zero-phase (1 + 2 cos w)/3, one step
late (−1.3 dB at 10 kHz, −5.9 dB at 20 kHz at 96 kHz). A 3-tap equaliser on the 3-tap mean reaches only ±0.3 dB to
18 kHz at 96 kHz by giving up 0.3 dB at DC, so the kit's are 5 taps, symmetric, equiripple by the Remez exchange
(`adaa_equaliser_remez_design`, ours; DC exactly 1; two steps more latency), for either kernel, one design function.

Which equaliser a block runs is a decision per (order, oversampling) (ours, measured 2026-10-20;
`ADAA_EQUALISER_DECISIONS`):

| order, oversampling | equaliser | product with the kernel | latency (steps) |
|---|---|---|---|
| 1, 2× | 5 taps, edge 5/24 of the 2× rate | ±0.0099 dB to the edge (20 kHz at 2× 48 kHz) | 2.5 |
| 2, 2× | 5 taps, edge 5/24 of the 2× rate | ±0.097 dB to the edge, never above that to the host's Nyquist | 3 |
| 1, 1× | none | cos(w/2): −2.0 dB at 10 kHz, −5.1 dB at 15 kHz at 48 kHz | 0.5 |
| 2, 1× | none | (1 + 2 cos w)/3: −1.3 dB at 5 kHz, −5.9 dB at 10 kHz at 48 kHz | 1 |

At 2× the band the equaliser lifts past the host's Nyquist (+15.9 dB at the 2× Nyquist for second order) is the
downsampler's. At 1× that band is the host's top octave, where the kernel's mean holds the aliases down, and an
equaliser after the transfer lifts an alias as it lifts the harmonics at its frequency (an alias re the fundamental
rises by the lift at its own frequency). Measured, worst alias under 20 kHz re the fundamental:
- Second order (the 259 folder and 2sl drums' voice, at 48 kHz), unequalised / the best 1× 5-tap design (±0.3 dB to
  8.8 kHz, its response never above +1 dB: Nyquist pinned at +1 dB, the outer tap the widest feasible) / the 2×
  design at 1×: the 259 folder 4 V at 3.1 kHz −25.3 / −18.6 / −15.5 dB, 8 V at 1.37 kHz −11.0 / −1.4 / +3.5, 4 V at
  410 Hz −36.3 / −26.7 / −22.0 (first order −6.3, −4.0, −30.4); 2sl drums' voice, worst folded line re the loudest
  kept, FM metal −49.8 / −43.1 / −39.9, ring −52.9 / −44.0 / −38.3, Harmonics 1 at 5 kHz −82.7 / −77.4 / −74.6, Fold
  4 V at 410 Hz −48.9 / −40.1 / −35.0, FM bright −69.3 / −64.6 / −62.2, Fold 4 V at 3.1 kHz −25.3 / −28.2 / −30.6,
  Fold 8 V at 1.37 kHz −13.5 / −6.4 / −4.9: the best 1× design loses in 9 of 10.
- First order (the tanh saturator, coherent 16384-point DFT, every alias), the raw mean against the 5/24 design at 1×
  (+6.4 dB at 24 kHz at 48 kHz alone): 60 cases (48 and 44.1 kHz; 410 Hz, 1.37, 3.1, 5 and 8 kHz; drives 1.5, 4, 12;
  bias 0 and 0.3), 49 above the floor (11 under −150 dB): lifted in 44, by up to +6.2 dB (+5.7 dB at 1.37 kHz drive
  12, 48 kHz: −41.5 → −35.8 dB; +5.5 dB at 5 kHz drive 12, 44.1 kHz: −20.0 → −14.4); within 0.05 dB in 4 (8 kHz at
  48 kHz, its worst alias landing where the equaliser is flat); lowered in 1 (8 kHz drive 1.5 at 44.1 kHz,
  −58.0 → −59.2).
So at 1× there is no equaliser for either order, and a block takes its oversampling with no default. The 2×
equaliser at 2× (the 259 folder at 2× 48 kHz, worst alias under 20 kHz, raw → equalised): 4 V at 3.1 kHz −36.4 → −31.5
dB (under 16 kHz −44.5 → −42.6), 8 V at 1.37 kHz −48.7 → −45.8, 4 V at 410 Hz −69.8 → −65.9 dB.

## Antiderivative tanh saturator (m4l_dev/techniques/antiderivative_tanh_saturator.py)

**Bilbao, Esqueda, Parker & Välimäki, "Antiderivative Antialiasing for Memoryless Nonlinearities", IEEE SPL 24(7),
2017, pp. 1049–1053** (`bilbao-adaa-spl2017.pdf`, Aalto's accepted version). The technique is eq. (5) on tanh, F1 =
log cosh, then an equaliser (below).
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

The mean is the 2-tap mean on small signals; after it the kit's ADAA equaliser for first order at the rate it runs at
(above): at 1× none, at 2× the 5-tap design between the kit's elliptic half-band upsampler and its linear-phase
half-band downsampler (below, "Halfband oversampler"; Bilbao et al. evaluate "at a 2× oversampled rate"). Being linear and after the mean, it is the same filter on everything that
goes through, at any drive. A bias is taken as held over a step (the mean of tanh along x + b, less tanh b, before the
equaliser and the downsampler, so silence is 0 from the first sample).

Measured 2026-10-20 (tests/test_techniques.py keeps each):

| | 1× | 2× |
|---|---|---|
| small signals, 44.1 kHz | cos(w/2): −0.56 dB at 5 kHz, −2.42 at 10 kHz, −6.35 at 15 kHz, −10.9 at 18 kHz, −16.7 at 20 kHz | within 0.01 dB to 18 kHz, −0.03 at 19 kHz, −0.27 at 20 kHz (the elliptic downsampler: −0.050 at 20 kHz) |
| small signals, 48 kHz | −0.47, −2.01, −5.11, −8.34, −11.7 dB | within 0.01 dB to 20 kHz |
| latency at 100 Hz | 0.5 samples, linear phase | 23.03 samples (1.25 + the elliptic upsampler's 1.78 + the linear-phase downsampler's 20), not linear phase |
| worst alias under 20 kHz, 48 kHz (coherent): 1.37 kHz drive 4 / 3.1 kHz drive 4 / 5 kHz drive 4 / 8 kHz drive 12 / 12 kHz drive 4 / 8 kHz drive 2.7 bias 0.3 | −78.6 / −48.9 / −36.7 / −31.7 / −27.9 / −34.9 dB | −157.0 / −97.7 / −78.4 / −46.5 / −48.0 / −64.9 dB |
| 8 kHz drive 2.7 at 44.1 kHz, worst alias under 10 kHz (naive −23.3; biased: naive −24.6) | −53.2 dB (biased −47.0) | −78.6 dB (biased −76.5) |
| hot sines (drive 3 and 20, 5–15 kHz, 44.1–96 kHz): the fundamental off tanh's (Fourier series) through the block's linear response | ≤ 0.34 (of 1.27) | ≤ 0.13 |
| peaks, hot sines | never above 1 (a mean of tanh; the quotient's rounding, ~1e-9) | 1.51 |
| peaks, hot broadband (48 kHz, +30 / +36 dB): white noise / a snare-like burst; the ideal (tanh at 16×, low-passed at 20 kHz) 1.74 / 1.78, 1.66 / 1.71 | never above 1 | 1.87 / 1.91, 1.71 / 1.71 (the elliptic downsampler: 2.79 / 2.85, 2.58 / 2.57) |
| bound for any input (`output_bound_per_unit_mean`: the sum of the chain's \|taps\| after the mean, × the mean's bound 1, or 1 + \|tanh b\| biased) | 1 | 2.19 |
| CPU a host sample (below): plain / biased | 55–63 / 75–86 ns | 150–171 / 183–209 ns with the elliptic downsampler; the linear-phase one +45 / +59 ns (re-measured 2026-10-20, best of 5 interleaved runs: 106 → 151, 132 → 191 ns) |

CPU (ours, 2026-10-20): the kit renderer's C (`m4l_dev/genexpr.py`'s translation, CPython's libm calls) built at −O2
instead of the test suite's −O0, 2^20 samples of a hot sweeping sine through preallocated buffers, best of 31, three
runs (ranges) on an i7-8700 under load (load average ~70 on 12 threads): not Max's gen~ compiler, so a ratio, not a
budget. A naive tanh(x) is 25–35 ns; the elliptic half-band pair alone 17–23 ns; the 259 folder's second-order shaper 50–54 ns
at 1× (one step), 110–132 ns at 2× (two steps, the 2× equaliser, the downsampler). The 2× saturator is 2.4–2.8× the
1× with the elliptic downsampler, about 3.7× with the linear-phase one.

**Peaks (ours, 2026-10-20).** 2sl drums' strip (this block at 2×, bias 0)
peaked at 2.1 on a snare at +36 dB. Stage by stage (a numpy model of the block, equal to the kit's renderer to 1e-14):
the mean never leaves 1; the equaliser after it reaches 1.8 at the 2× rate (its taps' sum of |taps| 2.09, its gain at
the 2× Nyquist); the elliptic downsampler takes that to 2.85 on hot white noise (2.42 with no equaliser). A
linear-phase half-band of the same edges and depth takes it to 1.91 (1.57 with no equaliser), against the ideal's 1.78:
the elliptic's phase near its corner was most of the excess, the equaliser the rest, and band-limiting itself most of
the peak (a clipped broadband wave is no square wave: its overshoot is not Gibbs' 9 %). 2sl drums' demo kit at +30 /
+36 dB, bias 0, EQ flat, Compress 0, 48 kHz, before → after: kick 1.10 / 1.14 → 1.04 / 1.01, snare 2.06 / 2.11 →
1.45 / 1.50, clap 1.62 / 1.79 → 1.33 / 1.41, closed hat 1.71 / 1.81 → 1.37 / 1.37, open hat 2.04 / 2.16 → 1.41 / 1.53,
rim 1.65 / 1.71 → 1.36 / 1.40, metal 1.82 / 1.88 → 1.37 / 1.42, tom 1.14 / 1.29 → 1.03 / 1.06.

**The linear twin** (`AntiderivativeTanhSaturatorLinearTwin`, ours, 2026-10-20): the same up- and downsampler, mean and equaliser
with x in place of tanh (x's first-order ADAA is exactly the 2-tap mean), so its response is the saturator's small-signal
response at every frequency: what an instrument puts on a dry path it mixes against the saturator. At 2× the elliptic
upsampler is not linear phase, so a delay can't follow it. Before the linear-phase downsampler (the elliptic pair,
4.32 samples at 100 Hz, 6.71 at 20 kHz), 4 samples and a first-order Thiran (above's source) for 0.32 left a comb of
−0.44 / −2.28 dB at 10 / 20 kHz at a 50 % mix, 44.1 kHz; now 22 samples and a Thiran for the remaining 1.03 leave
−0.07 / −15.1 dB; the twin: none (rounding, −134 dB under a 1e-4 signal).
The twin costs the up- and downsampler and the equaliser, no tanh.

Replaced (2026-10-20): the split tanh x = x + (tanh x − x), x through a first-order Thiran allpass of half a sample
(**Smith, *Physical Audio Signal Processing*, "Thiran Allpass Interpolators"**, `jos-thiran-allpass.html`: a1 =
(1 − Δ)/(1 + Δ) = 1/3 for N = 1, Δ = 0.5) and ADAA on the residual only. Flat on small signals, but at a hot drive the
residual is mostly −x, which the 2-tap mean filters and the allpass does not, so the output was off by about
|allpass − mean| × the drive (48 kHz, 10 kHz, drive 10: the fundamental 1.6 × the band-limited tanh's too big, peaks
3.2; 15 kHz drive 20: peaks 10.9). Measured with the kit's renderer against tanh's Fourier series (the ideal,
band-limited, as late); tests/test_techniques.py keeps the new figures.

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

## Histories start at their targets (m4l_dev/techniques/histories_start_at_their_targets.py)

No outside source: our construction, stated whole in the module docstring. gen~ gives a History a constant initial
value; a smoother of a control would need that constant to repeat the control's Init value (a second copy:
architecture/presets.md makes Init the one source). Instead each named History is set to its target on the first
sample, before it is read: a one-pole step from the target to itself is the target exactly (x + (x - x) c = x), so a
History whose constant already equalled the target renders the same bits. Its `if` and History writes are the GenExpr
the tape-style echo's Stop already uses.

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

## Input-keyed duck (m4l_dev/techniques/input_keyed_duck.py)

After the TC 2290's ducker, from its manual (TC2290-DT / TC2290 Native user manual, TC Electronic, 2018,
[PDF via Full Compass](https://www.fullcompass.com/common/files/33690-TCELECTRONICTC2290DTUserManual.pdf); read for 2sl
dub, its references/dub.md §3): "A ducking delay uses the input signal to attenuate the delay signal, causing the
echoes to stay 'out of the way' while you're playing, but still allow the echo tails to be audible during gaps." Input
level triggers it; DEPTH is how much, in % of the most; SPEED is the release as a ramp time ("a setting of '1' means a
ramp time of 1 second, whereas a setting of '5' means a ramp time of 1/5 of a second"); the threshold has 9 settings 3
dB apart. The manual gives no detector or attack: those are ours (a peak follower falling over 10 ms, a 3 dB soft knee
in place of the switch, a 2 ms one-pole rise), stated in the module docstring.

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
and the times are the caller's. Undriven, `release_ms` is exactly the time from `release_from_amps` to
`release_to_amps`. The Buchla 292 channel (circuits/buchla-292-low-pass-gate.md, the VTL5C3/2's constants; moved onto
this block bit for bit) and the Mu-Tron Bi-Phase (circuits/mutron-bi-phase.md, its own UNVERIFIED constants) use it.

## Drum envelope (m4l_dev/techniques/drum_envelope.py)

**Sonic Charge, *Microtonic User Guide* v3.3.4** (`microtonic-user-guide-3.3.4.pdf`; 2sl drums
references/er1-microtonic-genopatch.md §1.2 reads the whole voice from it).
- p. 18, Oscillator Attack: "With the default attack setting of zero, the envelope's attack phase is eliminated, and
  the oscillator triggers at full force directly. This causes a sharp transient with a distinct clicking sound";
  "Longer attack times suggests a sound that has been reversed in time because the oscillator attack phase is always
  exponential (most synthesizers have a linear attack and an exponential decay)."
- p. 18, Oscillator Decay: "The oscillator envelope always runs from maximum to zero amplitude with an exponential
  decay curve ... (The observant reader may object that an exponential decay never reaches zero, which is true in
  theory; thus, the time setting is only an approximate.)"
- p. 19, Noise Envelope Mode: "The Linear Mode creates a more conventional attack, but its decay acquires a 'gated'
  effect, which is great for simulating gated snare drums. Finally, the Modulated Mode is tailor-made for handclaps.
  It works by retriggering the envelope in rapid successions before going into the decay phase. In this mode, the
  attack setting controls the time until the decay phase by changing the number of triggers and the time between
  them." p. 20, Noise Attack: for the Modulated Mode "this is the total time spent triggering short 'clap bursts'
  until the decay phase kicks in."

The technique: the attack is the exponential decay reversed in time (rise(u) = (e^(-a(1-u)) - e^(-a)) / (1 - e^(-a))),
the decay a true exponential, linear both ways in the linear mode, the clap a burst of instant retriggers. Ours, not
the guide's [UNVERIFIED]: the curvature a = ln 1000, that `decay_ms` spans 60 dB, the clap's count and spacing as two
controls (the guide folds them into Attack with no law) and each pulse's 60 dB fall over one spacing. A restart
starts the attack at the level the envelope has (the attack curve inverted), our rule for "restart on hit without
clicks".

## Pitch modulator (m4l_dev/techniques/pitch_modulator.py)

**Microtonic User Guide v3.3.4**, p. 17: Decaying, "the rate setting controls the time it takes the oscillator to go
from the highest frequency down to the base frequency (or from the lowest frequency and up if the modulation amount is
negative). At minimum rate setting, the oscillator is stuck at the highest / lowest frequency"; Sine, "the minimum
rate setting makes the oscillator stick to its initial frequency and never changes. The highest modulation rates
generate an FM-like effect"; Random, "Random Pitch Modulation uses a low-pass filtered noise as the modulation source,
and for this mode, the rate controls the cut-off frequency of the low-pass filter ... At zero rate, it simply
randomizes the pitch by the chosen amount every time the drum patch is triggered." Ranges: Decaying ±96 semitones,
infinite to 10 ms; Sine and Random ±48 semitones, 0-2 kHz and 0-20 kHz.

**Korg ER-1 owner's manual** (2sl drums references/er1-microtonic-genopatch.md §1.1, ER1-OM pp. 24-25): Mod Type Saw
Down ("pitch falls cyclically"), Square ("two pitches alternate"), Triangle ("rises and falls"), Mod Speed 0.1 Hz to
5 kHz.

The technique: the six shapes, each cyclic one starting at +amount (Microtonic's "stick to its initial frequency" at
rate 0), the cyclic jumps and corners through `BandLimitedEdges` (C7 square and saw: worst alias below 10 kHz
-76 dB, the trivial waves -24.6 dB). Ours [UNVERIFIED]: the decay's curve (the drum envelope's rise reversed, reaching
0 at the decay time), and the random shape's filter, a one-pole AR(1) y <- (1 - c) y + sqrt(c(2 - c)) w that keeps the
variance of a uniform draw at every cutoff.

## Seeded white noise (m4l_dev/techniques/seeded_white_noise.py)

**Park & Miller, "Random Number Generators: Good Ones Are Hard to Find", CACM 31(10), 1988, pp. 1192-1201**
(`park-miller-cacm1988.pdf`, a copy hosted at firstpr.com.au).
- p. 1194 [3]: "a = 16807 and m = 2^31 - 1 define a ... minimal standard"; "16807 is just one of more than 534 million
  full period" multipliers.
- p. 1195 [4], "Real Version 1": `temp := a * seed; seed := temp - m * Trunc(temp / m); Random := seed / m`; "This
  version of Random will be correct if reals are represented with a 46-bit or larger mantissa ... on all systems that
  support the IEEE 64-bit real arithmetic standard since the mantissa in that case is 53-bits"; seeds "between 1 and
  2147483646"; the check value: "z1 = 1 then z10001 = 1043618065" (tests/test_techniques.py holds the block to it).

The technique is Real Version 1 (floor for Trunc: the operands are positive), as 2 z / m - 1. That gen~ computes in
64-bit floats is [UNVERIFIED] here (the 2sl devices' gen~ code has never needed it to be exact before).

## Metallic noise (m4l_dev/techniques/metallic_noise.py)

**Jomox, *MBase 11 manual*** (`jomox-mbase11-manual.pdf`), p. 11, 3.12 MetNze: "Changes the noise of the noise
generator to a metallic noise. At a value of <000> the noise is a random noise as in the older MBase01. On values above
that a complex signal made from high pitch digital multi tones and the bit pattern of the value is created. Each unique
single pattern is corresponding to a value number. This does not result in a continuous signal change over the value
range, instead the signal patterns jump with each number." pp. 9-10, 3.6 Noise: "the noise can be assembled by
metallic high pitch tones."

**2sl drums references/adx1.md §6** (the ADX-1 manual read 2026-10-20): its metal source has its own Tune; its
mechanism is unpublished; its Metal voice runs two sources, each into its own band-pass.

The technique's law is ours [UNVERIFIED as the Jomox's]: an 8-bit shift register whose feedback is the parity of the
bits the value selects, clocked at a tune, its lowest bit out, a constant state reloaded with the value. It keeps what
the manual says (digital, high multi-tones, one pattern a value, jumps between values) and what adx1.md asks (a
tune). The seam for an ADX-1 source: `METALLIC_NOISE_SOURCES` and the interface its docstring states.

## Bell equalizer (m4l_dev/techniques/bell_equalizer.py)

**Zavalishin, *The Art of VA Filter Design*, rev. 2.1.2** (`zavalishin-va-filter-design-2.1.2.pdf`).
- §4.7, p. 118 [130]: "By adding/subtracting the unit gain bandpass signal to/from the input signal one obtains the
  band-shelving filter: HBS(s) = 1 + K · HBP1(s)"; "the bandwidth of the filter varies with the shelving boost K. A
  way to address this issue will be described in Chapter 10."
- §10.6, pp. 429-430 [441-442]: "H(s) = (s² + M⁻² · 2RM s + 1) / (s² + 2RM s + 1) = HLP(s) + M⁻² HBP1(s) + HHP(s) =
  1 + (M⁻² − 1) HBP1(s) (mind that the SVF damping is still being equal to RM) ... The amplitude response at the cutoff
  is H(j) = M⁻² which thereby defines the shelving gain"; eq. (10.19): "H(s) = (s² + 2RM⁻¹ s + 1) / (s² + 2RM s + 1)".

The technique is that filter on the zero-delay SVF with G = M⁻² and the SVF's Q = Q √G (2R = 1/Q). That Q is the
bandwidth at the half-gain (dB) points, |1 − ω²| = ω/Q, is our algebra from (10.19), tested. Gain ±40 dB is
Microtonic's EQ range (MT-UG p. 15, Equalizer Gain "Range: -40db to +40db"; "The peak or dip width (i.e., the q
value) is fixed and cannot be changed", its value not given; its auto-attenuation at high gain is not taken).

## Halfband oversampler (m4l_dev/techniques/halfband_oversampler.py)

**de Soras, *HIIR* 1.40 (2021-12-24, WTFPL)** (`hiir-1.40.zip`).
- `PolyphaseIir2Designer.cpp`: `compute_coefs_spec_order_tbw`, `compute_transition_param`, `compute_coef`,
  `compute_acc_num`, `compute_acc_den`, `compute_atten`: ported line for line; tests/test_techniques.py holds the port to
  `oversampling.txt`'s "2×, 156 dB" design (12 coefficients, transition 0.0472053, 156.686 dB) to 2e-7.
- `StageProcTpl.hpp`, `process_sample_pos`: each stage `tmp = (spl − mem_out) · coef + mem_in`.
- `Upsampler2xTpl.hpp`: `even = input; odd = input;` through the stages, `out_0 = even; out_1 = odd`.
  `Downsampler2xTpl.hpp`: `spl_0 (in_ptr [1]); spl_1 (in_ptr [0]);` through the stages, `return 0.5 * (spl_0 + spl_1)`.
- `readme.txt`: "a two-path polyphase IIR ... made of a symetric half-band elliptic low-pass filter, hence having an
  extremely flat frequency response in the passband"; "These filters have a quite flat group and phase delays from DC
  up to about Fs/20"; its example downsampler is 8 coefficients at transition 0.04 (the kit's default).

The kit's default: 8 coefficients, transition 0.04, 99.3 dB (compute_atten); measured: a 30 kHz tone at 88.2 kHz
folds to 14.1 kHz at −113.5 dB (naive decimation: 0 dB); an FM pair (9 kHz carrier, 1.3 kHz modulator, index 10) run
at 2× aliases at −84.1 dB re the carrier below 20 kHz, at 1× at −11.8 dB; up then down is flat to 15 kHz (±0.001 dB)
and 3.07 samples late at 100 Hz.

A 2x section's controls (ours, 2026-10-20: 2sl stab 2.2.8 found the Moog ladder's cutoff leading its audio):
`ControlsAtTheUpsampledSteps` delays each host-rate control to its step's audio, the upsampler's `latency_samples`
(its half-band's phase delay at 100 Hz) for the first step and half a sample less for the second, by linear
interpolation (its delay at low frequencies is its fraction). Measured: a 100 Hz control in phase with the same sine
through the upsampler within 0.002 doubled-rate samples; held over both steps instead it leads by 1.53 samples.

The linear-phase downsampler (`HalfbandLinearPhaseDownsampler`, ours, 2026-10-20: for after a saturator; above,
"Peaks"): the ideal half-band 0.5 sinc(k/2) under **Kaiser's window**, its β and length from Kaiser's formulas as
**Oppenheim & Schafer, *Discrete-Time Signal Processing*, 3rd ed., §7.6.1, eqs. (7.62)–(7.63)** give them (β =
0.1102 (A − 8.7) for A > 50; M = (A − 8) / (2.285 Δω)); not mirrored (a textbook), the formulas held by the test (stop
band ≤ −100 dB from 0.29, pass band within 1e-4 dB to 0.21). A = 100 dB and the elliptic's edges: 83 taps, 20 samples
late, a 30 kHz tone at 88.2 kHz folds at −120.4 dB; −0.22 dB at 20 kHz at 44.1 kHz (the elliptic flat there).

After the 259 folder at 2× (ours, 2026-10-20): the elliptic's phase
rings a hot folded tone too. Steady peaks re the ideal (the tone's harmonics below 24 kHz, flat, own phases), 4–10 V,
55 Hz–7 kHz at 48 kHz: elliptic up to 2.36 (8 V at 988 Hz: 7.08 V against 3.00; the linear-phase 4.06), its phase
alone up to 1.77×; the linear-phase one 0.99–1.01× on phase. Its group delay at 48 kHz: 1.78 samples to 2 kHz, 2.21
at 10 kHz, 3.34 at 16 kHz, 5.77 at 20 kHz (a spread of 9 / 32 / 83 µs): the shape under 10 kHz is the ideal's, the
excess a headroom matter (and what a saturator after it sees). Both still exceed the ideal by up to 1.35–1.67× with
the 2× ADAA2 equaliser (0.99–1.01× without it below 1.8 kHz): open, PLANS/2026-10-20-instrument-2x-folder-peaks.md.

## Defined-latency pad (m4l_dev/techniques/defined_latency_pad.py)

What it serves: Live's Defined Latency is whole samples (references/README.md, "Defined Latency": the Max user guide
"Type in a value for the latency value in samples"; saved as the patcher's integer `"latency"`). A device whose paths
are fractionally late (a 1x ADAA saturator's half sample, the elliptic half-band pair's 3.07) declares its latest
path rounded up and pads every path to it (architecture/overview.md, "Defined Latency": the rule, ours).

**Smith, *Physical Audio Signal Processing*, "Thiran Allpass Interpolators"** (`jos-thiran-allpass.html`; quoted in
references/allpass-and-diffusion.md §5 [VERIFIED there]): `a_k = (−1)^k C(N, k) Π_{n=0..N} (Δ − N + n)/(Δ − N + k + n)`,
maximally flat group delay "equal to Δ at dc"; "For sufficiently large Δ, stability is guaranteed. Rule of thumb:
Δ ≈ order" (the bound itself is not on the page: every Δ the pad uses has its poles checked inside the unit circle by
the step-down test, tests/test_techniques.py); first order `a1 = (1 − Δ)/(1 + Δ)` (Dattorro Part 2
eq. 40, the same coefficient). Why an all-pass and not an FIR for a fixed sub-sample pad: its magnitude is exactly 1
(a pad must not change a path's level or tone), where a short fractional FIR droops toward Nyquist (linear
interpolation's gain at Nyquist |1 − 2f|, allpass-and-diffusion.md §5: at f = 0.5 a null; −16.7 dB at 20 kHz at
44.1 kHz); a linear-phase FIR has only whole or half-sample delays. Its cost is phase: Thiran's delay is exact at DC
and leaves Δ toward Nyquist.

Ours (measured, tests/test_techniques.py, every fractional part in 0.01 steps, 44.1 kHz): order N = min(ceil(P), 4)
at Δ = N − 1 + frac(P), after the whole rest (Δ in (N − 1, N) is where each order's error is least: order 1 at Δ 0.5 is
0.072 samples off at 10 kHz, at Δ 1.5 0.218). Worst |phase delay − P|: order 1 (pads under 1) 0.003 / 0.073 / 0.33 /
0.49 samples to 2 / 10 / 18 / 20 kHz; order 4 (pads of 3 or more) 1e-4 / 0.0023 / 0.14 / 0.30. A whole pad is a ring of
Histories, exact; a pad of 0 is the input.

## Dispersive-loop spring tank (m4l_dev/techniques/dispersive_loop_spring_tank.py)

No outside source for the structure: it is 2sl gate's spring (src/gate_dsp.py, `_spring_code`, gate commit
68bfd110), moved into the kit so a second device can have it, stated whole in the module docstring. A delay line a
spring per loop, read at the round trip with linear interpolation; a one-pole low-pass; a one-pole DC blocker; the
loop gain 10^(-3 T / Length); eight first-order all-passes (a + z⁻¹)/(1 + a z⁻¹) of 0.62; tanh where the loop
writes back. The all-pass's group delay is Parker 2011's eq. 5 (below), (1 − a²)/(1 + 2a cos ω + a²) samples:
(1 + a)/(1 − a) = 4.26 at Nyquist, (1 − a)/(1 + a) = 0.23 at DC for 0.62, so eight spread an echo over 32 samples
(0.73 ms at 44.1 kHz, tested): a dispersive comb, not a spring's chirp (2sl dub's references/springs.md §1 computed
it first). The parametric spring reverb (next) is the kit's chirping spring. Gate's numbers in the kit:
`Buchla208SpringReverb` (references/circuits/buchla-208-spring-reverb.md), which renders gate's own code (tested).

## Parametric spring reverb (m4l_dev/techniques/parametric_spring_reverb.py)

**Parker & Bilbao, "Spring reverberation: a physical perspective", DAFx-09** (`parker-bilbao-dafx09.pdf`):
- §3: "The nature of these echoes can be described by two parameters - the transition frequency F_C, and the time
  between each echo, T_D"; the energy above F_C is much lower, "therefore it would seem reasonable to assume that the
  characteristic sound of a spring reverberator is mainly related to the region below F_C".
- §4: "The local maximum in the dispersion relation therefore corresponds with a point of minimum propagation
  velocity. It is clear from the dispersion relation that this point corresponds with the transition frequency F_C
  observed in the impulse response" (the chirp's delay is greatest at F_C); eq. (3), the wire's length
  L = √((2πRN)² + H²), eq. (4), F_C ≈ (3r / (16√5 π R²)) √(E/ρ), with T_D (eq. 2) proportional to L: the whole delay
  curve scales with the spring's length, which is why the sections a spring gets scale with its round trip.

**Parker, "Efficient dispersion generation structures for spring reverb emulation", EURASIP J. Adv. Signal Process.
2011:646134** (`parker-eurasip2011.pdf`, CC BY):
- §2, eqs. (1)-(3): A(z) = (a + z⁻¹)/(1 + az⁻¹); the stretched H_single(z) = A(z^k); the cascade A^M(z^k). "This
  structure can also be extended to allow noninteger values of k by replacing one of the internal unit delays with an
  interpolating first-order all-pass filter."
- §2: C_lf, "two parallel delay lines with feedback, with an appropriately designed spectral delay filter placed
  within each feedback loop ... One feedback structure produces the chirped echo sequence below f_C ... This feedback
  structure is followed by a lowpass filter, in order to suppress any behaviour above f_C." VPA10's random delay
  modulation, cross-coupling and equalisation filter are "computationally light (on the order of 10 multiplications
  per sample period)" and left out there (and here).
- §3.1, eq. (4): the cascade's group delay D = kM (1 − a²)/(1 + 2a cos(kω) + a²) samples: with a real k, the
  reference the technique is measured against (`ideal_chain_group_delay_seconds`). Eq. (5)-(6): a first-order
  all-pass designed for "a particular fractional delay at an arbitrary frequency" (not at DC): the technique's
  fractional section is set this way, its phase delay exact at π / K, where the section's delay peaks (our use of
  it; Parker uses it to time-align the crossover's bands).
- §3.2: "it makes sense to run the C_lf structure at f_s / 4"; the anti-aliasing filter a 10th-order Chebyshev type
  1. §4, Table 2: the multirate, chirp-straightened structure costs 355 multiplies a sample against 1023, "around
  one third"; the C_hf sequence is "generally at least 30 dB below the other chirp sequence ... it may be
  acceptable to discard it completely and use only C_lf ... at the cost of some realism". The straightened chirp is
  "audible as a slight hardness of the echoes ... especially when presented with percussive material".

**Gamper, Parker & Välimäki, "Automated calibration of a parametric spring reverb model", DAFx-11**
(`gamper-parker-valimaki-dafx11.pdf`):
- §2: "The filter H_dc(z) is a dc blocking filter with a cutoff frequency at 40 Hz [5]"; "Each allpass filter section
  is an interpolated stretched allpass filter, which is composed of a Schroeder allpass filter with an embedded delay
  line of K − 1 samples and a first-order fractional-delay allpass filter to implement a delay equal to 1 plus the
  decimal part of K"; eqs. (4)-(6), K1 = round(K) − 1.
- §3.1.1: T_D "can be derived from the maximum absolute value of the autocorrelation of the impulse response" (the
  tests' measure of echo spacing). §3.2.1: g_lf = K 10^(d/20) with K the sign of the autocorrelation's maximum:
  g_lf = −0.64 for the Leem Pro (negative).
- Table 1, Leem Pro KA-1210 spring 1, VPA10's manual calibration: T_D 0.056, F_C 4300, M_low 100, a_1 0.62, g_lf −0.8,
  M_high 200, a_high −0.6, g_hf −0.77 (the technique's REFERENCE_* constants and the module's stand-in dispersion);
  automated, M_low limited to 100: a_1 0.63, F_C 4216.
- §4: the optimal M_low "can become very large, such as about 300 ... the maximum number of filter sections is
  limited to 100. This can lead to a sufficiently good fit".

**Välimäki, Parker & Abel, "Parametric spring reverberation effect", JAES 58(7/8) 2010** (VPA10): paywalled, not read;
everything taken from it here is quoted by the three papers above. **Välimäki, Parker, Savioja, Smith & Abel, "Fifty
years of artificial reverberation", IEEE TASLP 2012** (FY12): quoted from 2sl dub's references/springs.md §4 (the line
"set to T_D after taking into account the inherent delay-time of the allpass-chain", the negative loop gains "to match
the reversal of the first echo").

What the technique adds, measured (tests/test_techniques.py, 2026-10-21; the reference is eq. (4) with a real K, 100
sections of 0.62, F_C 4.5 kHz, over 0-0.98 F_C):

| fractional section | 44.1 kHz | 48 kHz | 96 kHz | 192 kHz |
|---|---|---|---|---|
| GPV11's (Thiran, exact at DC, K1 = round(K) − 1) | 0.306 ms worst | 1.368 | 0.065 | 0.023 |
| the kit's (eq. 6's idea: phase delay exact at π/K, K1 = floor(K − 1/4)) | 0.105 ms worst | 0.141 | 0.021 | 0.002 |

Rejected on numbers: the loops at fs / R (P11's multirate C_lf, K / R about 2 to keep the sections' delays whole and
small): the same eq. 6 sections leave 1.2-2 ms of error near F_C (a fractional delay that must hold to π/2), against
0.1 ms at the host rate. Linear or spline interpolation of the loop's line: up to 0.45 / 0.38 dB a trip lost at F_C
(at a half-sample fraction, 4.5 kHz, 44.1 kHz); the line's fraction is a first-order Thiran all-pass instead
(lossless). Cost, measured in the kit renderer (optimised C, one run, 4 s at 44.1 kHz, load 3.6 on 10 cores): the
three-spring tank (198 sections) 0.51 µs a sample, the two-spring studio tank (118) 0.36, gate's spring 0.11, gate's
whole idle core 1.83.

`neutral_damping_hz` and `sections_for_round_trip` are DESIGN, stated in the module.

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
- **gen~ data, peek and poke** (Cycling '74, Gen reference, read 2026-10-21): data
  (https://docs.cycling74.com/reference/gen_dsp_data/): "Stores an array of sample data (64-bit floats) usable for
  sampling, wavetable synthesis and other purposes. The first argument specifies a name by which to refer to this data
  in other objects in the gen patcher (such as peek and poke), the second optional argument specifies the length of
  the array (default 512 samples) and the third optional argument specifies the number of channels (default 1)."
  peek (https://docs.cycling74.com/reference/gen_dsp_peek): "Read values from a data/buffer object. The first argument
  should be a name of a data or buffer object in the gen patcher." "The first inlet specifes a sample index to read (no
  interpolation); indices out of range return zero." Attributes: boundmode, default "ignore"; index, default
  "samples"; interp, default "none". poke (https://docs.cycling74.com/reference/gen_dsp_poke): "Write values into a
  data/buffer object." "The first inlet specifies a value to write, while the second inlet specifies the sample index
  within the data/buffer." "If the index is out of range, no value is written."
- **data, peek and poke in GenExpr**: Philip Meyer's signal-polyphony voice allocator
  (`pdmeyer-voice_allocator.genexpr`, commit d1f5413), GenExpr run in Max, declares `Data internal(4, 4);` and reads
  and writes it as `peek(internal, i, 2)` and `poke(internal, 0, i, 0);`; Cycling '74's gen-workshop granulator
  (`cycling74-gen-workshop-grranulator.genexpr`, commit f114ce9) writes `poke(playing, 1, i);` and reads
  `peek(playing, i)`. So the kit's renderer takes `Data name(size);` (one channel), `peek(name, index)` and
  `poke(name, value, index);`, the index floored (the reference's "no interpolation"; how gen~ rounds a fractional
  index is not stated: the blocks use whole indices) and an index out of range, or NaN, read as 0 and not written, as
  the default boundmode "ignore" has it. The bucket-brigade echo's chips are a Data each.
- **GenExpr** (https://docs.cycling74.com/userguide/gen/gen_genexpr/): "functions must be declared before all
  statements"; functions take arguments and "can return multiple values". The gen blocks keep to the kit renderer's
  subset (one return value, bounded loops only), which is narrower.
- **gen~ loops in GenExpr** (the same guide, "Branching and Looping" and "Continue and Break", read 2026-10-20):
  "Branching and looping is supported in GenExpr with `if/else`, `for` and `while` constructs."; "`for` loops are
  also similar to this in many other languages although there is no `++` operator in GenExpr to increment a loop
  counter. Instead, += can be used: `val = 0; for (i = 0; i < 10; i += 1) { // accumulate val += i; } out = val;`";
  "All of the gen objects have protections against infinite loops, so while an infinite loop might slow things down,
  it won't cause Max to get stuck and freeze."; "in many cases values in GenExpr are floating point, even loop
  counters"; "With looping constructs, GenExpr supports `break` and `continue` statements. `break` causes an early
  exit from a loop[;] `continue` causes the loop to start the next iteration without finishing the current one." The
  kit renderer takes the guide's `for` with literal start, limit and step (so its count is known when the code is
  checked), `break` and `continue`, and refuses `while` and any `for` it cannot bound (m4l_dev/genexpr.py).

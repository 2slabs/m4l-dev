# DSP sources: the kit's gen~ blocks

What the DSP blocks (architecture/dsp-blocks.md; `m4l_dev/gen_*.py`) are built from, with quotes and pages.
`fetch-dsp-sources.sh` downloads every source below into `references/dsp-sources/` (not in git) and checks each is
the copy these notes were written from (sha256, fetched 2026-10-18 and 2026-10-19). Page numbers are the printed
page, with the PDF page in brackets where they differ.

## Ladder (m4l_dev/gen_ladder.py)

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
  obvious way to fix this problem would be e.g. to boost the input signal by the (1+k) factor." (The block keeps
  2sl stab's milder make-up, 1 + 0.4 k.)
- §6.6, p. 191 [203]: replacing tanh u by u "is equivalent to one step of Newton–Raphson with u = 0 as the initial
  guess." p. 192 [204]: the tangent at the last value "usually ... provides a better result, however in the
  excessive (but not so unusual) situations of high cutoff, high feedback amount and/or high signal frequencies
  this c[an work worse]"; "Linearization by secant line ... in moderately excessive situations this could work
  better than the linearization at the operating point, but at more excessive settings could work worse than the
  linearization at zero."

The block is (5.8) with the tanh applied to the solved u (linearised at zero). The research behind the choice
(2026-10-19, against RK4 at 8x of each analog model): an exact Newton solve of the same loop measured the same
(-52.6 dB error vs the model, both); the per-stage tanh ladder (the secant linearisation above, at a linear
predictor) tracks its own model as well but its self-oscillation sinks 4 to 32 cents flat with its amplitude (the
analog model does the same), so it isn't kept. Huovilainen (DAFx-04) uses five tanh and 2x oversampling for that
model; not needed here.

## Saturator (m4l_dev/gen_saturator.py)

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
The block puts the linear part of tanh through it (half a sample, flat magnitude) and antialiases only the residual
tanh x − x, so both halves are half a sample late and small signals aren't low-passed. (Our construction from the
two sources; measured in the module docstring and tests/test_dsp_blocks.py.)

## Edges (m4l_dev/gen_edges.py)

**Esqueda, Välimäki & Bilbao, "Rounding Corners with BLAMP", DAFx-16** (`esqueda-blamp-dafx16.pdf`).
- Abstract [p. 1]: "The polynomial BLAMP can reduce the level of aliasing components by up to 50 dB".
- Table 1 [p. 3]: "Third-order B-spline basis functions, its first integral (polyBLEP), its second integral
  (polyBLAMP), and polyBLAMP residual", per span [−2T, −T], [−T, 0], [0, T], [T, 2T]; "Four-point polyBLAMP
  residual": d^5/120; −d^5/40 + d^4/24 + d^3/12 + d^2/12 + d/24 + 1/120; d^5/40 − d^4/12 + d^2/3 − d/2 + 7/30;
  −d^5/120 + d^4/24 − d^3/12 + d^2/12 − d/24 + 1/120. The block's tables are derived again from the B-spline
  (exact fractions) and equal these.

**Välimäki, Pekonen & Nam, "Perceptually informed synthesis of bandlimited classical waveforms using integrated
polynomial interpolation", JASA 131(1), 2012, pp. 974–986** (`valimaki-polyblep-jasa2012.pdf`).
- Abstract [p. 974]: "the integrated third-order B-spline correction function ... offers perceptually aliasing-free
  sawtooth emulation up to the fundamental frequency of 7.8 kHz at the sample rate of 44.1 kHz."
- [p. 982]: "the second-order PolyBLEP is free from aliasing up to about 2 kHz" (what 2sl stab had).

## Echo (m4l_dev/gen_echo.py)

**Downing & Terjesen, "Real-time digital modeling of the Roland Space Echo", U. Rochester ECE 472 class project,
2016** (`downing-terjesen-re201-2016.pdf`; not peer-reviewed).
- §3 [p. 3]: "Our measured time constants were 1.89s for increasing delay time, and 1.07s for decreasing delay
  time." (The block's glide keeps their ratio, shorter: a synced echo.)
- §3.1 [p. 2]: "The spectrum of the delay speed showed a sharp cutoff at approximately 1 Hz. We measured the variance
  of the delay trajectory signal fed through low pass filter with a 1 Hz cutoff" (the block's wow: noise low-passed
  at 1 Hz).
- §3 [p. 3]: "the self-oscillation which occurs at particular frequencies at high feedback settings is integral to
  many Space Echo-produced sounds effects."

**Chowdhury, "Real-time physical modelling for analog tape machines", DAFx-19** (`chowdhury-tape-dafx19.pdf`):
tape as hysteresis plus playback-head loss filters. Not modelled; the block's tape is a saturating loop.

## Switched-capacitor filter (m4l_dev/gen_switched_capacitor.py)

**Linear Technology, LTC1060 datasheet, rev. "1060fb"** (`ltc1060-1060fb.pdf`; a university mirror,
https://www.komponenten.es.aau.dk/fileadmin/komponenten/Data_Sheet/Switch_Cap/LTC1060.pdf, sha256 4114b99d...;
official copy https://www.analog.com/media/en/technical-documentation/data-sheets/1060fb.pdf).
- p. 1: "pin compatible with MF10"; p. 2: "Clock Feedthrough, fCLK ≤ 1MHz: 10 mV(P-P)"; the clock-to-center ratio
  tested at 50:1 and 100:1.
- p. 7 (pin 12): "When Pin 12 is shorted to the negative supply pin, the filter operation is stopped and the bandpass
  and lowpass outputs act as a S/H circuit holding the last sample. The hold step is 20mV and the droop rate is
  150µV/second!"; "With low supply operation, the maximum input clock frequency is about 500kHz. Beyond this, the
  device exhibits its excessive Q enhancement and center frequency errors."
- p. 8: "The LTC1060 is a sampled data filter and it only approximates continuous time filters"; "From Graph 4 at
  ±7.5V supply, 50:1 and 1.4MHz clock, a Q of 5 has about 8% error"; "Mode 3 ... and the modes of operation where R4
  is finite, are 'slower' than the basic mode 1 ... The finite GBW of this op amp creates an additional phase shift
  and enhances the Q value at high clock frequencies."

**Texas Instruments (National), MF10-N datasheet, SNOS547C (2013)** (`mf10-n.pdf`,
https://www.ti.com/lit/ds/symlink/mf10-n.pdf, sha256 0e837564...).
- p. 4: "Clock Feedthrough, Q = 10, Mode 1: 10 mV"; voltage swing ±3.8 V min, ±4.25 V typ (N/AP/HP, ±5 V).
- p. 26, "Sampled data system considerations": an input above half the clock "will be 'reflected' to a frequency
  less than one-half the sampling frequency"; "the output signal changes amplitude once every sampling period,
  resulting in 'steps' in the output voltage which occur at the clock rate"; "A ratio of 100:1 will reduce any
  aliasing problems ... a ratio of 50:1 ... will result in 3 dB lower output noise."

**Which chip, which ratio** (the device that asked for it, 2sl filter: its references/sherman-filterbank.md §2.0):
the Sherman Filterbank's designer, in a 2025 interview, "the clock is ratio 100 to one".

The block is our construction from these: the two-integrator section stepped per tick with LDI integrators (forward
and backward Euler in the loop, the standard discrete form of a switched-capacitor biquad, whose poles sit at
F = 2 sin(pi f0 / f_clock); not stated in either datasheet), Q enhancement as the excess-phase law Q' = Q / (1 - Q c
f_clock) fitted to the LTC1060's one number, the 10 mV p-p feedthrough against the MF10's ±4 V swing as full scale,
hold as stopped ticks. The band-limiting is the kit edges block (above), chosen by measurement (module docstring).

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
  statements"; functions take arguments and "can return multiple values". The blocks keep to the kit renderer's
  subset (one return value, no loops), which is narrower.

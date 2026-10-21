# 2026-10-20: the 2x ADAA2 equaliser's peak excess

## Status (2026-10-21)

Open: every 2x second-order ADAA chain (the 259 timbre section; the piecewise-linear shaper at 2x) peaks up to 1.67x
the band-limited ideal even through the linear-phase downsampler. Unmeasured: which of the two carries it. Nothing
built yet.

Done and moved out: the elliptic vs linear-phase study (references/dsp.md, "After the 259 folder at 2x"; kept as
`test_a_hot_fold_at_2x_peaks_past_the_ideal_through_the_elliptic_downsampler`); 2sl drums' tone section and 2sl gate's
voices now come down through `HalfbandLinearPhaseDownsampler` (gate's 19-tap FIR deleted, 0.3.25).

## What is known (2026-10-20, 48 kHz, scratchpad folder-peaks-measure/)

The ideal: the folded tone's harmonics below 24 kHz, flat, their own phases. Linear-phase chain, worst peak / ideal
over 55 Hz-7 kHz at 4 / 8 / 10 V: 1.67 / 1.54 / 1.35 with the equaliser; without it 0.99-1.01 below 1.8 kHz (1.20-1.33
above). The equaliser lifts the raw 2x stream +5.8 dB at 20 kHz, +8.2 at 24, +10.4 at 28 (+15.9 at the 2x Nyquist). On
small signals that only restores the kernel (product -1.4 dB at 24 kHz, -5.5 at 28), but it also lifts the ADAA's
residual aliases at the 2x rate, and the half-band's transition band (0.21-0.29 of the 2x rate, -6 dB at 24 kHz)
passes 20-24 kHz and folds part of 24-28 kHz there. Content at 20-24 kHz is inaudible but real headroom.

## Next

1. Split the excess: restored harmonics at 20-24 kHz vs lifted residual aliases (hypothesis and numeric prediction
   written here before the test).
2. Then, by measurement: a downsampler that stops by 24 kHz (not a half-band), or an equaliser that falls after
   20 kHz. Cost in latency and CPU stated against the linear-phase half-band (20 samples, +45 ns a host sample).

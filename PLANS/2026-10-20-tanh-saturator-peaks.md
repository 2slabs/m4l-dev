# 2026-10-20: why the 2x tanh saturator peaks at 2.1 on drums

Finding (2sl-drums 0.3.11, strip = AntiderivativeTanhSaturator at 2x, bias 0, EQ flat, compress 0): at +30 / +36 dB
drive the strip's output peaks at kick 1.10 / 1.14, closed hat 1.71 / 1.81, metal 1.82 / 1.88, snare 2.06 / 2.11.
2sl-filter's 2x DRIVE_CLIP on real drums: ~3.1. The kit's claim "2x peaks < 1.74" was tested on sines only.

Static fact before measuring: the 2x first-order equaliser's taps (0.0391, -0.2731, 1.4680, -0.2731, 0.0391) have
an L1 norm of 2.093 = its gain at the 2x Nyquist (+6.4 dB). A mean of tanh is in (-1, 1), so anything after it is
bounded by the L1 norm of the linear chain after the mean.

Hypotheses, each with its prediction (white noise and a snare-like burst, drives +30 / +36 dB, 48 kHz):

- (a) the equaliser: hot noise makes the 2x mean a near +-1 random sequence, broadband up to the 2x Nyquist; the
  equaliser lifts its top (x1.26 at the 5/24 edge, x2.09 at the 2x Nyquist) and the half-band's transition band
  (0.21-0.29 of the 2x rate) lets part of the lift through. Prediction: the equaliser's output (before the
  downsampler) peaks near 2; with the equaliser replaced by one tap the final peak falls to <= 1.3.
- (b) the half-band downsampler's ringing on a +-1 random sequence. Prediction (if b dominates): without the
  equaliser the final peak stays > 1.5.
- (c) the mean ill-conditioned at near-equal samples. Prediction: the mean alone never leaves [-1, 1] (to 1e-12):
  excluded.
- (d) the drums strip after the saturator: bias 0, bell flat, compress 0 -> out = strip_drive_out / tanh(drive) with
  tanh(drive) = 1 to 1e-12 at +30 dB. Prediction: no contribution.
- Reference: the ideal (tanh at 16x, linear-phase low-pass at 20 kHz, decimated) on the same inputs. Prediction:
  peaks 1.1-1.3 (band-limiting overshoot of a telegraph-like wave).

Results (numpy model of the block, equal to the kit's renderer to 1e-14; scratchpad scripts, 48 kHz, peaks):

| input, drive | mean | equaliser out (2x) | chain (elliptic down) | elliptic, no equaliser | linear-phase down | ideal 20 kHz |
|---|---|---|---|---|---|---|
| white noise +30 / +36 | 1.000 / 1.000 | 1.70 / 1.78 | 2.79 / 2.85 | 2.42 / 2.46 | 1.87 / 1.91 | 1.74 / 1.78 |
| snare-like burst +30 / +36 | 1.000 / 1.000 | 1.71 / 1.79 | 2.58 / 2.57 | 2.26 / 2.26 | 1.71 / 1.71 | 1.66 / 1.71 |
| six squares (metal) +30 / +36 | 1.000 / 1.000 | 1.37 / 1.56 | 1.91 / 2.19 | 1.72 / 1.91 | 1.46 / 1.50 | 1.30 / 1.40 |

- (c) refuted as a cause: the mean never leaves 1 (1e-14 rounding).
- (d) refuted by reading: at bias 0, Bell flat, Compress 0 the strip is the saturator's output / tanh(drive) = 1.
- (a) partly: the equaliser adds ~15 % (2.42 -> 2.79), not the bulk.
- (b) the bulk: the elliptic downsampler's phase near its corner (2.42 vs 1.57 for a linear-phase half-band with the
  same edges and depth, both without the equaliser).
- The reference refutes "a saturator should stay near 1": band-limiting hot noise's tanh peaks 1.74-1.78 by itself.

Fix (kit): the saturator's downsampler is a linear-phase Kaiser half-band (100 dB, the elliptic's edges, 83 taps);
peaks now 1.07x the ideal; bound for any input 2.19 (`output_bound_per_unit_mean`). Costs: 23.03 samples latency
(was 4.32), -0.27 dB at 20 kHz at 44.1 kHz (was -0.05), +45 ns a host sample. Open: the 259 folder and the
piecewise-linear shaper at 2x go through instruments' own elliptic pairs with the second-order equaliser (+15.9 dB at
the 2x Nyquist): the same mechanism, unmeasured.

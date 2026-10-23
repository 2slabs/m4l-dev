# ITU-R BS.1770-5: loudness and true peak

Source: Recommendation ITU-R BS.1770-5 (11/2023), "Algorithms to measure audio programme loudness and true-peak audio
level". https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1770-5-202311-I!!PDF-E.pdf
Fetched 2026-10-19, sha256 eefb926f72f72a96b96f251067bfee0650a0f29a26f60661d354162038b041ad;
`fetch-itu-r-bs1770.sh` gets the same copy. PRIMARY (the standard). Text read with `pdftotext -layout`.

Used by `twosl_dsp/bs1770.py` (the meter) and, through it, `twosl_dsp/preset_loudness.py`: every preset's loudness
against Init's, in each device's tests.

## Annex 1: loudness

- **Pre-filter, stage 1** (Table 1, p.4; "to model a spherical head"), 48 kHz, a0 = 1:
  b0 1.53512485958697, b1 −2.69169618940638, b2 1.19839281085285; a1 −1.69065929318241, a2 0.73248077421585.
- **Stage 2** (Table 2, p.5; the RLB high pass), 48 kHz: b 1.0, −2.0, 1.0; a1 −1.99004745483398,
  a2 0.99007225036621.
- **Other rates** (p.4-5): "Implementations at other sampling rates will require different coefficient values, which
  should be chosen to provide the same frequency response that the specified filter provides at 48 kHz."
  [DERIVED] bs1770.py reads each stage's analog prototype back from the 48 kHz coefficients through the
  bilinear transform (stage 1: a high shelf at 1681.97 Hz, Q 0.70718, +4.0 dB; stage 2: a high pass at 38.135 Hz,
  Q 0.50033) and transforms it again at the rate it needs. At 44.1 kHz the cascade is within 0.006 dB of the 48 kHz
  one from 10 Hz to 17.6 kHz; at 11.025 kHz within 0.3 dB below 4.4 kHz (no pre-warping beyond the corner).
- **Loudness** (eq. 2, p.6): L = −0.691 + 10 log10 Σ Gi zi LKFS, zi the mean square of the filtered channel i.
  Gi = 1.0 for L, R, C (Table 3). NOTE 1 (p.7): "The constant −0.691 in equation (2) cancels out the K-weighting gain
  for 997 Hz" (so a 0 dBFS 997 Hz sine in one channel reads −3.01 LKFS).
- **Gating** (eqs. 3-7, p.6-7): blocks of Tg = 400 ms "to the nearest sample", overlapping by 75 %; "Incomplete
  gating blocks at the end of the measurement interval are not used." Block loudness lj = −0.691 + 10 log10 Σ Gi zij.
  Absolute gate Γa = −70 LKFS; relative gate Γr = (the loudness of the blocks above Γa) − 10; the gated loudness is
  that of the blocks above both, the channels' block powers averaged before the log.

## Annex 2: true peak

- Stages (p.18): attenuate 12.04 dB (only for integer arithmetic: "not necessary if the calculations are performed in
  floating point"), 4× over-sample, low pass, absolute value, dB TP.
- One filter that satisfies it (p.18-19): an order-48, 4-phase interpolating FIR; its 4 × 12 coefficients are in
  bs1770.py `TRUE_PEAK_PHASES`, column by column as printed. The annex presumes 48 kHz; at 44.1 kHz the same
  4× reaches 176.4 kHz, under the 192 kHz the annex asks of a meter labelled dB TP ("at least 192 kHz", p.19), so
  a 44.1 kHz render's numbers are a near true peak.

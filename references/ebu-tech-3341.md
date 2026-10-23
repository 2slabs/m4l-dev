# EBU Tech 3341: momentary loudness and its maximum

Source: EBU Tech 3341 V4 (November 2023), "Loudness Metering: 'EBU Mode' metering to supplement EBU R 128 loudness
normalization". https://tech.ebu.ch/docs/tech/tech3341.pdf
Fetched 2026-10-19, sha256 dd5a7b0b611024e616b86a42c89eed0ded33f3129afc1994204885216fa1619e;
`fetch-ebu-tech-3341.sh` gets the same copy. PRIMARY (the EBU's meter specification). Text read with
`pdftotext -layout`; page numbers are PDF pages.

Used by `twosl_dsp/bs1770.py` (`max_momentary_loudness`) and, through it, `twosl_dsp/preset_loudness.py`: the loudness
every preset is levelled to Init by.

- **§2.1, p.4-5, the time scales:** "The shortest time scale is called 'Momentary', abbreviated 'M'." "The loudness
  meter shall be able to display the maximum value of the 'Momentary Loudness' and of the 'Short-term Loudness'."
- **§2.2, p.5:** "In all cases the measurement is performed as specified of ITU-R BS.1770" (the K-weighting and
  equation 2: itu-r-bs1770.md). "1. The Momentary Loudness uses a sliding rectangular time window of length 0.4 s. The
  measurement is not gated." "Further slowdown of the attack or release (decay) parts of the loudness signals, after
  the sliding rectangular time windows, shall not be employed in 'EBU Mode'". ITU-R BS.1771's IIR "momentary" is a
  different measure: "measurements of Maximum Momentary Loudness using the 'EBU Mode' definition and using the BS.1771
  definition can differ by up to 2 LU" (p.10). The kit uses EBU Mode's.
- **Table 1, p.8, test case 13** ("For file-based meters"): "(i * 20 ms of silence; 400 ms at −23.0 dBFS; 1 s of
  silence) for i = 0, 1, 2, …, 19", tones "similar to #1" (a stereo 1000 Hz sine, the level per channel peak, in
  phase in both channels): "Max M = −23.0 ±0.1 LUFS, for each segment". So a file meter slides the window over every
  start, not on a 10 Hz grid; `max_momentary_loudness` slides it one sample at a time (tests/test_bs1770.py runs the
  case). Test case 12 (p.8): "(0.18 s at −20.0 dBFS; 0.22 s at −30.0 dBFS) repeated 25 times", "M = −23.0 ±0.1
  LUFS, constant after 1 s".

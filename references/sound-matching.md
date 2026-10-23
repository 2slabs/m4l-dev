# Sound matching: sources for the patch matcher

Date: 2026-10-19. Purpose: the sources behind the score and the search of twosl_dsp's patch matcher (render a synth
voice, score it against a target drum-hit WAV, search the parameters). Text of each PDF read with
`pdftotext -layout`; quotes are the paper's own words, reflowed over line breaks only.
`fetch-sound-matching-sources.sh` downloads every PDF below into `references/sound-matching-sources/` (gitignored,
PDFs are never committed) and checks each against the sha256 recorded here and in the script. Page numbers are the
PDF page (arXiv papers carry no other numbering) except the two journal papers, which give the printed page.

Label key:
- **VERIFIED**: the claim was read in the primary PDF this session; the page is given.
- **UNVERIFIED**: could not be confirmed in a primary source this session; the reason is given.
- **[NOT IN SOURCE]**: something one might expect the paper to say that it does not; stated so it is not assumed.

## Sources

| Short name | What | URL | sha256 (prefix) |
|---|---|---|---|
| ddsp | Engel, Hantrakul, Gu, Roberts, "DDSP: Differentiable Digital Signal Processing", ICLR 2020 (arXiv v1) | https://arxiv.org/pdf/2001.04643v1 | 41aa87d9 |
| pwg | Yamamoto, Song, Kim, "Parallel WaveGAN", ICASSP 2020 (arXiv v2) | https://arxiv.org/pdf/1910.11480v2 | f91b87ae |
| sound2synth | Chen et al., "Sound2Synth: Interpreting Sound via FM Synthesizer Parameters Estimation" (arXiv v2) | https://arxiv.org/pdf/2205.03043v2 | 2c8e9984 |
| turian | Turian, Henry, "I'm Sorry for Your Loss: Spectrally-Based Audio Distances Are Bad at Pitch", ICBINB@NeurIPS 2020 (arXiv v2) | https://arxiv.org/pdf/2012.04572v2 | 93237aa5 |
| shier2023 | Shier et al., "Differentiable modelling of percussive audio with transient and spectral synthesis", EAA Forum Acusticum 2023 (arXiv v1) | https://arxiv.org/pdf/2309.06649v1 | 03a41548 |
| shier2024 | Shier, Saitis, Robertson, McPherson, "Real-time Timbre Remapping with Differentiable DSP", NIME 2024 (arXiv v1) | https://arxiv.org/pdf/2407.04547v1 | 2acb46fb |
| salimi | Salimi, Hindle, Zaiane, "Evaluating Sound Similarity Metrics for Differentiable, Iterative Sound-Matching" (arXiv v2) | https://arxiv.org/pdf/2506.22628v2 | 52f51e3f |
| yee-king | Yee-King, Fedden, d'Inverno, "Automatic Programming of VST Sound Synthesizers using Deep Networks and Other Techniques", IEEE TETCI 2(2), 2018 (Goldsmiths accepted manuscript) | https://eprints-gro.gold.ac.uk/22516/1/myk_lf_vsti_programming.pdf | f1f1f849 |
| cma-es | Hansen, "The CMA Evolution Strategy: A Tutorial" (arXiv v2) | https://arxiv.org/pdf/1604.00772v2 | 96645df3 |
| yin | de Cheveigne, Kawahara, "YIN, a fundamental frequency estimator for speech and music", JASA 111(4), 2002 | https://cagnazzo.wp.imt.fr/files/2013/05/2002_JASA_YIN.pdf | 0055503a |

The author's own copy (http://audition.ens.fr/adc/pdf/2002_JASA_YIN.pdf) answered HTTP 503 (http) and a TLS
certificate error (https) on 2026-10-19, so the Telecom Paris (cagnazzo.wp.imt.fr) copy is the one fetched; its text
carries the JASA header, DOI 10.1121/1.1458024, and printed pages 1917-1930. Full sha256 values are in the script.

## A. ddsp: the multi-scale spectral loss (claim A: VERIFIED)

- **Why not the waveform** (§4.2.1, p.7): "for audio waveforms, point-wise loss on the raw waveform is not ideal, as
  two perceptually identical audio samples may have distinct waveforms, and point-wise similar waveforms may sound
  very different."
- **The loss** (§4.2.1, p.7-8): "Instead, we use a multi-scale spectral loss–similar to the multi-resolution
  spectral amplitude distance in Wang et al. (2019)–defined as follows. Given the original and synthesized audio, we
  compute their (magnitude) spectrogram Si and Ŝi, respectively, with a given FFT size i, and define the loss as the
  sum of the L1 difference between Si and Ŝi as well as the L1 difference between log Si and log Ŝi." Eq. (4), p.8:
  `Li = ||Si − Ŝi||1 + α || log Si − log Ŝi ||1`, "where α is a weighting term set to 1.0 in our experiments. The
  total reconstruction loss is then the sum of all the spectral losses, Lreconstruction = Σi Li."
- **Sizes and overlap** (p.8): "In our experiments, we used FFT sizes (2048, 1024, 512, 256, 128, 64), and the
  neighboring frames in the Short-Time Fourier Transform (STFT) overlap by 75%."
- **Why several scales** (p.8): "Therefore, the Li's cover differences between the original and synthesized audios
  at different spatial-temporal resolutions." That is the whole rationale given; the time-versus-frequency trade-off
  is spelled out in pwg and turian (below), not here.
- **Pitch** (p.8, §5.1): "The unsupervised DDSP autoencoder must learn to infer its own F0 conditioning signal
  directly from the audio. As described in Section B.4, we improve optimization by also adding a perceptual loss in
  the form of a pretrained CREPE network." App. B.4 (p.17): the extra loss is "the L1 distance between the
  activations of the small CREPE model's fifth max pool layer with a weighting of 5 × 10−5 relative to the
  spectral loss." The supervised model takes f0 from a fixed pretrained CREPE (§3/B.1, p.6 and p.14: "we fixed the
  weights of the f-encoder"). [NOT IN SOURCE]: the paper never says f0 is non-convex or that a spectral loss cannot
  learn it; it only reports that it added the CREPE term to "improve optimization". The non-convexity argument comes
  from turian and shier2023.

Matcher takes: the form `sum over sizes of L1(mag) + 1.0 * L1(log mag)`, sizes 2048..64, 75% overlap, as the
starting spectral term; and that DDSP itself reached for a pitch estimator rather than leaning on this loss for f0.
Not taken: the paper's reasons for the multi-scale choice (one sentence only).

## B. pwg: multi-resolution STFT loss (claim B: VERIFIED)

- **Single STFT loss** (§3.2, p.2), eq. (3)-(5): `Ls = Lsc + Lmag`; "Lsc and Lmag denote spectral convergence and
  log STFT magnitude loss"; `Lsc = || |STFT(x)| − |STFT(x̂)| ||F / || |STFT(x)| ||F`;
  `Lmag = (1/N) || log|STFT(x)| − log|STFT(x̂)| ||1`, "where || · ||F and || · ||1 denote the Frobenius and L1
  norms, respectively; |STFT(·)| and N denote the STFT magnitudes and number of elements in the magnitude".
- **Multi-resolution** (p.2): "Our multi-resolution STFT loss is the sum of the STFT losses with different analysis
  parameters (i.e., FFT size, window size, and frame shift)." Eq. (6) is `Laux = (1/M) Σm Ls(m)`, so the equation
  averages over the M losses where the sentence says "sum" (a constant factor).
- **Why** (p.2): "In the STFT-based time-frequency representation of signals, there is a trade-off between time and
  frequency resolution; e.g., increasing window size gives higher frequency resolution while reducing temporal
  resolution [24]. By combining multiple STFT losses with different analysis parameters, it greatly helps the
  generator to learn the time-frequency characteristics of speech [25]. Moreover, it also prevents the generator
  from being overfit to a fixed STFT representation, which may result in suboptimal performance in the
  waveform-domain."
- **Table 1** (§4.1.2, p.3; "A Hanning window was applied before the FFT process"), 24 kHz speech:

  | loss | FFT size | window size | frame shift |
  |---|---|---|---|
  | 1 | 1024 | 600 (25 ms) | 120 (5 ms) |
  | 2 | 2048 | 1200 (50 ms) | 240 (10 ms) |
  | 3 | 512 | 240 (10 ms) | 50 (≈ 2 ms) |

Matcher takes: spectral convergence (relative Frobenius error) is a level-normalised companion to the log-magnitude
term; three resolutions were enough for speech at 24 kHz. These sizes are speech-tuned; nothing here says they suit
drum hits.

## C. sound2synth (claim C: VERIFIED)

- **Target synth** (§1.2, p.2): "Our experiments mainly concentrate on the Dexed synthesizer [Gauthier, 2013],
  since it is one of the most popular open-source FM synthesizers". §2.1 (p.3): Dexed "is an open-source software
  synthesizer with 6 oscillators, aimed to model the FM synthesis algorithm in the Yamaha DX7". 155 parameters (§3,
  p.6): "87 continuous parameters, 66 discrete parameters, and 2 fixed parameters".
- **Evaluation distance** (§1.2, p.2): "We will use mean squared Euclidean Distance between Mel-Frequency Cepstral
  Coefficients Distance (MFCCD) as our evaluation metric, since MFCCD is proven by experiment to be well-aligned with
  human perception [Terasawa et al., 2005]". Eq. (1): `min dis(f(θ̂, η0), A)`.
- **Inputs** (§2.2, p.3): STFT spectrogram, Mel spectrogram, CQT chromagram, MFCC and statistics ("ZCR, RMS" in
  Fig. 3), each fed to its own backbone (VGG CNNs, a prime-dilated CNN, an LSTM on MFCC).
- **Training loss is on parameters, not audio** (§2.2, p.3): "During training, we only aim to optimize the Mean
  Squared Error (MSE) between predicted parameters and the groundtruth parameters". And "This may cause dis-alignment
  between the training objective and the desired goal since: Parameters have different importance, a wrongly
  predicted 'coarse' parameter has a larger influence than a wrongly predicted 'fine' parameter. Different
  configurations (in terms of numerical values of parameters) may produce similar sound timbres." Their fix weights
  each parameter by an audio-space sensitivity, computed only for small datasets since "rendering audio using a
  synthesizer and computing audio space loss for every parameter of every data point is very time-consuming" (p.6).
  Continuous parameters are discretised into classes (p.3).
- **Search baselines** (Table 1, p.6, copied from yee-king, marked "*"): Hill Climbing 21.96, Genetic Algorithm 31.32,
  APVST LSTM++ 22.59, PresetGen VAE 14.70, "Similarity Threshold for Human Perception 10 ∼ 15", Sound2Synth 6.32 and
  5.36 (multi-modal); MFCCD, lower is better, 6-operator setting. p.2: learned results "comparable to traditional
  approaches", and differentiable synthesisers "could not be directly applied to existing commercial synthesizers,
  which are powerful but non-differentiable."

Matcher takes: MFCC distance is a standard score for synth matching, with 10-15 as the "similar" band on Dexed (a
13-band figure; the paper reports no remarkable difference with 40 bands, p.7). It is not a drum paper and is a
trained estimator, not a per-target search.

## D. turian: spectral distances and pitch (claim D: VERIFIED, with limits)

- **Finding** (abstract, p.1): "We compare commonly used audio-to-audio losses on a synthetic benchmark, measuring
  the pitch distance between two stationary sinusoids. The results are surprising: many have poor sense of pitch
  direction." Intro (p.1): "gradient-descent takes a circuitous route for some losses ... other loss functions get
  stuck in varying scopes of local minima. Their search spaces contain both fine-grained oscillations and broader
  plateaus."
- **Why** (§5, p.7): "In any norm-based distance, one makes the implicit assumption of orthogonality ... the
  distance asks the question 'do I need more of frequency x, or less?'. But these differences contain no explicit
  spectral orientation ... and by consequence can't answer a question that is simple for humans: 'is pitch x higher
  or lower than pitch y?'." Fig. 2 text (p.4): the plain spectrogram distance "at great distances ... has no sense of
  pitch orientation whatsoever (a vanishing gradient), and it locks-in with extreme confidence at fine pitch
  distances."
- **Table 1** (p.6), pitch-direction accuracy over 1000 trials, worst-case 95% CI ±0.032, chance = 0.5, sines
  30-4000 Hz; columns analytic gradient / ±30 cents / ±600 cents:
  Spectrogram 0.617 / 0.574 / 0.695; log(Spectrogram) 0.548 / 0.541 / 0.679; Mel 0.511 / 0.479 / 0.580;
  MFCC 0.532 / 0.603 / 0.648; MSS 0.771 / 0.905 / 0.978; log MSS 0.532 / 0.665 / 0.879;
  log2(Spectral Centroid) 0.515 / 1.000 / 1.000.
  MSS here is the multi-scale spectral loss "in our work, we use the six window sizes shown in Figure 1" (2048 ..
  64, p.5), i.e. ddsp's sizes.
- **Their text on MSS** (p.5): "In effect, this mitigates the poor behavior of the spectrogram-based pitch distance
  (Figure 2). Indeed, the pitch-perturbed gradient is correctly oriented 77% of the time. Still the gradient is not
  entirely smooth." p.7: "The use of multiple analysis scales further smooths the search space, however these
  distances still contain many very fine-grained local minima."
- **Pitch recovery** (p.7): "pitch-recovery is an intrinsically difficult regression problem. Sinuisoidal
  activations can compactly construct functions with infinite VC-dimension [22], and backprop through a periodic
  function is difficult to train." The paper's explanation for why spectral-loss systems use trackers (p.2): "This
  negative result explains why methods using spectral losses nonetheless end up using pitch-tracker models for
  conditioning [16] or reconstruction [15]."
- **Limits** [NOT IN SOURCE]: the benchmark is a single stationary sine, no drum, no search algorithm (gradient
  orientation only); the claim is "bad at ordering pitch differences", not "unusable". The log spectral centroid
  ordered pitch perfectly at the numeric resolutions but its analytic gradient was at chance (0.515), so it suits a
  derivative-free search, not gradient descent.

Matcher takes: a spectral-only score is a poor guide for the pitch parameters, so a separate pitch term (YIN or
spectral-centroid based) is supported for ordering; MSS beat the plain spectrogram on this benchmark; an
MFCC-only score is no better at pitch (0.53-0.65).

## E. Drum-synthesiser matching (claim E: PARTLY VERIFIED)

What exists, from a search on 2026-10-19 (the search tool's summary, then the PDFs read below):

- **No paper found** that matches a drum synthesiser's parameters to a target by Shier, McNally and Tzanetakis.
  UNVERIFIED that none exists: arXiv/Scholar search only; the AES e-library and ResearchGate pages returned HTTP 403.
- "Analysis of Drum Machine Kick and Snare Sounds" (Shier, McNally, Tzanetakis, AES Convention 143, 2017):
  UNVERIFIED, only seen in search results (the search summary calls it audio features, PCA and classification of
  samples, not parameter estimation); not read. "Sieve" (2017) and Shier's MSc thesis ("The synthesizer programming
  problem") and spiegelib: UNVERIFIED, not located or read.
- **shier2023** (VERIFIED, p.1-5): drums reconstructed with sinusoidal + noise + transient models, not a synth
  matcher. p.2: "Directly estimating the frequencies of oscillators using gradient descent is a challenging problem
  due to the oscillatory nature of loss surfaces produced by current audio reconstruction objectives [14, 15]"
  ([14] is turian). p.3: "Due to the aforementioned challenges related to estimating frequency parameters using
  gradient descent, we instead employ a well-known tracking algorithm based on sinusoidal peak picking", on a CQT
  (min 20 Hz, 24 bins per octave, 10 octaves) "important for certain percussion sounds (e.g., kick drums)". p.5:
  trained with "a multi-resolution spectral loss with the same configuration of FFT, window, and hop sizes as in
  [24]" ([24] is pwg), "a weighted sum of the spectral convergence and log-magnitude spectral difference". Metrics
  (p.5): MSS, log spectral distance (LSD), and spectral flux onset error (SF); "Because applying a log
  transformation de-emphasizes transients, the LSD provides insight into the reconstruction of the signal with the
  decay emphasized". 25k one-shots at 48 kHz, kick/snare/tom/hihat/cymbals. Table 1 (p.5): the transient network
  lowered the spectral-flux onset error for kick, snare and tom (Table 2), and the intro (p.2) says it "adds artifacts that degrade the decay portion of the sound".
- **shier2024** (VERIFIED, p.1-6): the closest to a drum-synth parameter fit. A differentiable TR-808-style snare
  (p.3: "a pair of sinusoidal oscillators ... and ... a noise generator", exponential decay envelopes, high-pass
  biquad, tanh waveshaper, "fourteen synthesis parameters in total"). The loss is not an audio distance: eq. (4) is
  an L1 over feature-difference vectors of seven features (RMS as K-weighted LKFS, spectral centroid, temporal
  centroid, spectral flatness; onset and sustain segments, p.4), each passed through a psychophysical scaling
  (spectral centroid `sSC = −34.61 x^−0.1621 + 21.2985`, temporal centroid `sTC = 0.03 x^1.864`, flatness in dB).
  Spectral features use a flat-top window and `log(1+X)` magnitude compression "shown to produce a smoother gradient
  for sinusoidal frequency estimation" (p.4). Optimised by Adam through the synth (p.6); "To prevent over
  utilization of oscillator frequency parameters, modulations for those two controls were damped by a factor of
  1e-3." Direct per-target optimisation of parameters "performed the best across all features" as the upper bound
  (p.6). It matches changes between hits, not one absolute target, and reports feature-difference errors, not a
  listening test.
- **salimi** (VERIFIED, abstract p.1; generic synths, not drums): "we implemented a mix of four novel and
  established differentiable loss functions, and paired them with differentiable subtractive, additive, and AM
  synthesizers. For each of the sixteen synthesizer–loss combinations, we ran 300 randomized sound-matching trials
  ... Our post-hoc analysis shows that the loss function performance is highly dependent on the synthesizer." Its
  discussion (p.9) says MSS and/or a perceptual loss "does seem appropriate in general cases", while listening tests
  or custom losses suit specific cases. Also lists Turian's paper as motivation (ref [5]).

Matcher takes: the iterative loop (synth + similarity + parameter search) is the standard formulation (salimi); the
percussive papers avoid learning oscillator frequency by gradient (shier2023 tracks it, shier2024 damps it by 1e-3),
which supports estimating pitch separately and searching the rest; shier2024's feature set (loudness, spectral and
temporal centroid, flatness) and its K-weighted loudness are a ready template for non-spectral-distance score terms;
per-hit onset error (spectral flux) and a log-free measure for transients are separate terms in shier2023 because the
log hides the attack. No source here searched a drum synth's parameters with a derivative-free optimiser.

## F. yee-king: search versus network (claim F: VERIFIED)

- **Setup** (abstract, p.1): "We describe and compare several sound matching techniques that can be used to
  automatically program the Dexed synthesizer ... The techniques are a hill climber, a genetic algorithm and three
  deep neural networks". Dexed is exposed "as 155, real-valued parameters in the range 0-1" (p.3). Six test sets of
  increasingly many free parameters, 180 test items in all; sounds are one MIDI note rendered for 1 second (p.5-8).
- **Error measure** (p.3): the feature is MFCC, "13 MFCC coefficients per frame, with the Mel filter bank beginning at
  133Hz", 44.1 kHz, FFT window 2048 frames, hop 1024 (27 frames per 1 s sound, p.5); search error = "the Euclidean
  distance between the two sounds" in that feature space (p.4); GA fitness "the reciprocal of the Euclidean
  distance" (p.5). The networks instead trained on "the root mean squared error between the predicted settings and
  the actual settings", because "it is not possible to backpropagate the error via the synthesizer itself" (p.5).
- **Results, Table II** (p.6; mean MFCC distance per test set, lower is better; total over all items):
  HC 17.29, 20.95, 23.18, 19.9, 22.35, 21.96, total 3769; GA 23.2, 37.59, 32.03, 27.71, 28.12, 31.32, total 5399;
  MLP total 5557; LSTM total 5455; LSTM++ 19.47, 23.15, 21.48, 20.66, 18.14, 22.59, total 3765.
- **Who won** (p.7): "It shows that the LSTM++ network achieved the lowest total error. The simplest programmer,
  HC, achieved the second lowest error." "Surprisingly, the GA, which is considered the standard technique in the
  literature, did not perform as well as the simpler HC programmer ... However, it was a very simplistic
  implementation, and other studies ran their GAs much longer, with larger populations." The HC was "a more
  consistent performer than the LSTM++ network"; "LSTM++ and HC both have approximately 25% of their matches in this
  'close' category". HC settings (p.4): random start, five variations per parameter (large and small decrement,
  none, small and large increment), step shrinks when "nothing" wins. GA (p.5): population 200, mutation chance 0.01
  per parameter, mutation size 0.1, 10 elites.
- **Interpretation** (p.7): "A smooth error surface in the context of synthesizer programming is one where small
  changes in parameter space result in small changes in feature space"; of a 2-parameter FM synth, "a change of 0.1
  in one parameter could produce a large change in feature space, equivalent to the feature difference between two
  real instruments"; "the search space does contain local minima". Informal listening (p.6): MFCC distances of "10 to
  15 or less" sound very similar, "in excess of 20 are unlikely to sound very similar".
- **Cost** (p.8): about 40 ms per candidate (render + features + compare); one HC epoch of five variations of up to
  132 parameters "takes around 26 seconds, or seven hours for 1000 epochs".
- Overall: "less than 25% of the matches can be considered close" (p.8) even for the best method.

Matcher takes: a derivative-free search through the real renderer is a legitimate baseline; the simple coordinate
hill climber beat the simple GA on a rough FM error surface; the error surface is rough and has local minima, so
restarts are warranted. These are Dexed pitched tones scored by MFCC; no drums, no CMA-ES.

## G. cma-es: defaults, boundaries, restarts (claim G: VERIFIED)

- **Default parameters, Table 1** (p.31, "Default Parameters (in 2016)", n = search-space dimension), as printed:
  - (48) `λ = 4 + ⌊3 ln n⌋` (annotated "can be increased"); `µ = |{wi > 0}| = ⌊λ/2⌋` (Table 1 caption).
  - (49) `w'i = ln((λ+1)/2) − ln i` for i = 1..λ ("preliminary convex shape"); (53) the positive weights are
    `w'i / Σ|w'j|+` (sum to one), the negative ones are scaled by `min(αµ−, αµ−eff, αpos def)/Σ|w'j|−` (sum to
    about −αµ−); `µeff = (Σ w'i)² / Σ w'i²` over the positive weights; (50) `αµ− = 1 + c1/cµ`; (51)
    `αµ−eff = 1 + 2µ−eff/(µeff + 2)`; (52) `αpos def = (1 − c1 − cµ)/(n cµ)`.
  - (54) `cm = 1`.
  - (55) `cσ = (µeff + 2) / (n + µeff + 5)`; `dσ = 1 + 2 max(0, √((µeff − 1)/(n + 1)) − 1) + cσ`.
  - (56) `cc = (4 + µeff/n) / (n + 4 + 2 µeff/n)`.
  - (57) `c1 = αcov / ((n + 1.3)² + µeff)` with αcov = 2.
  - (58) `cµ = min(1 − c1, αcov (1/4 + µeff + 1/µeff − 2) / ((n + 2)² + αcov µeff/2))` with αcov = 2.
  - p.32: "The default parameters of (53)–(58) are in particular chosen to be a robust setting ... We do not recommend to
    change this setting, apart from increasing the population size λ in (48), and possibly decreasing αcov on noisy
    functions." Footnote 30: "Decreasing λ is not recommended. Too small values have strong adverse effects on the
    performance."
  - Initialisation (footnote 1, p.29): "If the optimum is expected to be in the initial search interval [a, b]^n we
    may choose the initial search point, m, uniformly randomly in [a, b]^n, and σ = 0.3(b − a)."
- **Restarts** (p.32): "Increasing λ usually improves the global search capability and the robustness of the
  CMA-ES, at the price of a reduced convergence speed. The convergence speed (per function evaluation) decreases at
  most linearly with λ. Independent restarts with increasing population size [3], automated or manually conducted,
  are a useful policy to perform well on most problems." [3] is Auger & Hansen, "A restart CMA evolution strategy
  with increasing population size", CEC 2005 (not read). The tutorial does not use the acronym IPOP. Termination
  tests for deciding to restart are in B.3 (p.33-34): NoEffectAxis, NoEffectCoord, ConditionCov (cond(C) > 1e14),
  EqualFunValues, Stagnation, TolXUp, plus problem-dependent TolFun (conservative guess 1e-12) and TolX (1e-12 times
  the initial σ).
- **Boundaries** (B.5, p.34-35): "The handling of boundaries and constraints is to a certain extend problem
  dependent." If the optimum is not near the boundary: fitness `fmax + ||x − xfeasible||` (62) or resampling
  infeasible points. Simple repair: "This is not recommended, because the CMA-ES makes implicit assumptions on the
  distribution of solution points, which can be heavily violated by a repair. The main resulting problem might be
  divergence or too fast convergence of the step-size." Penalisation (63), for box bounds: evaluate at the clipped
  point and add `α ||x − xrepaired||²`, "The repaired solution is disregarded afterwards", with "α should be chosen
  such that the differences in f and the differences in the second summand have a similar magnitude."

Matcher takes: the formulas above verbatim for a CMA-ES implementation (positive weights only: the tutorial's
negative weights are not used), σ0 = 0.3 of the range with parameters normalised to a box, restarts with a larger λ.
The box is NOT handled by (62) or (63): the search runs in an unbounded space that a triangle wave folds onto the box
(twosl_dsp/patch_match_search.py, `fold_onto_unit_interval`), so CMA-ES sees an ordinary (periodic) function of its
own unclipped samples and nothing is repaired behind its back, which is what the tutorial's warning is about. That
is our choice, not the tutorial's; no source here was read for it.

## H. yin: the f0 estimator (claim H: VERIFIED)

Printed pages of JASA 111(4), April 2002, §II (steps 1-6). The paper's six steps: autocorrelation, difference
function, cumulative mean normalised difference, absolute threshold, parabolic interpolation, best local estimate.

- **Difference function** (step 2, p.1919), eq. (6): `dt(τ) = Σ_{j=1..W} (xj − xj+τ)²`; "an unknown period may be
  found by forming the difference function ... and searching for the values of τ for which the function is zero."
  Eq. (7): `dt(τ) = rt(0) + rt+τ(0) − 2 rt(τ)`.
- **Cumulative mean normalised difference** (step 3, p.1920), eq. (8): `d't(τ) = 1` if τ = 0, otherwise
  `dt(τ) / [(1/τ) Σ_{j=1..τ} dt(j)]`. "This new function is obtained by dividing each value of the old by its average
  over shorter-lag values. It differs from d(τ) in that it starts at 1 rather than 0, tends to remain large at low
  lags, and drops below 1 only where d(τ) falls below average."
- **Absolute threshold** (step 4, p.1920): "The solution we propose is to set an absolute threshold and choose the
  smallest value of τ that gives a minimum of d' deeper than that threshold. If none is found, the global minimum is
  chosen instead. With a threshold of 0.1, the error rate drops to 0.78% (from 1.69%)". Meaning: "can be interpreted
  as the proportion of aperiodic power tolerated within a 'periodic' signal"; "the exact value of this threshold does
  not critically affect error rates" (p.1920). §IV (p.1922): "Obviously it does not require fine tuning, at least for
  this task. A value of 0.1 was used for the statistics reported here."
- **Parabolic interpolation** (step 5, p.1920-1921): "Each local minimum of d'(τ) and its immediate neighbors is fit
  by a parabola, and the ordinate of the interpolated minimum is used in the dip-selection process. The abscissa of
  the selected minimum then serves as a period estimate. Actually, one finds that the estimate obtained in this way
  is slightly biased. To avoid this bias, the abscissa of the corresponding minimum of the raw difference function
  d(τ) is used instead." Accurate "unless the signal contains strong high-frequency components (in practice, above
  about one-quarter of the sampling rate)"; tests with synthetic stimuli found it "reduced fine error at all F0".
- **Table I** (p.1919; 25 ms window, 40-800 Hz): gross error 10.0% (step 1), 1.95, 1.69, 0.78, 0.77, 0.50% (step 6).
  Gross error = more than 20% off the laryngograph value (p.1921). Limit (p.1921): YIN "tends, however, to fail for
  F0's beyond one quarter of the sampling rate."
- **Limits** [NOT IN SOURCE]: the evaluation is voiced speech with periodic signals; the paper does not test decaying
  inharmonic drum tones, and a kick's pitch glide inside one window is outside its periodic signal model (abstract, p.1917:
  "a signal model (periodic signal)").

Matcher takes: threshold 0.1 as the published default, the d' and parabolic steps as specified; the clean-periodicity
assumption is a reason to run YIN on short frames, not a measured result on drums.

## I. Mel scale (claim I: UNVERIFIED)

`mel = 2595 log10(1 + f/700)` is not confirmed here in a primary source. HTK Book: the book was not obtainable
(htk.eng.cam.ac.uk answered 502 on 2026-10-19; the Columbia mirrors answered 403 or a TLS error). O'Shaughnessy,
*Speech Communication: Human and Machine*, Addison-Wesley, 1987: a print book, not read. Search-result summaries (not
read as pages by this session) attribute the formula to O'Shaughnessy 1987 (MathWorks `hz2mel`, NVIDIA DALI docs, the
RASTA-MAT `hz2mel.m`) and one mailing-list thread traces the 700 Hz form to Makhoul and Cosell, ICASSP 1976; they
agree on the constants but are secondary. The matcher can state the formula, labelled UNVERIFIED, until the HTK Book
or O'Shaughnessy is read. Slaney's (linear below 1 kHz) variant is a different curve, so the choice of curve must be
named wherever MFCCs are compared to published numbers (yee-king used pyAudioAnalysis' MFCC, whose mel formula was
not checked).

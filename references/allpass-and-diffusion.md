# All-pass DSP: phaser sections, Schroeder / nested / lattice diffusers, Dattorro's plate, modulated delays, shimmer

Written 2026-10-20 for the kit's all-pass block ("a high quality all pass dsp block ... smearing, reverbs ... really good
pads and shimmers and atmos", user, 2026-10-20). `fetch-phaser-diffusion-sources.sh` downloads the sources below
into `phaser-diffusion-sources/` (not in git, sha256-checked); Zavalishin and the JOS Thiran page come from
`fetch-dsp-sources.sh` (`dsp-sources/`). The circuit side of phasers is in `circuits/mutron-bi-phase.md`.

Tags: **[VERIFIED]** read in the source this session (file, page). **[DERIVED]** computed by us from verified inputs.
**[SECONDARY]** a practitioner's account, read. **[UNVERIFIED]** only seen as a search excerpt or from memory. Pages
are printed pages (Zavalishin PDF page = printed + 12).

## 1. The first-order all-pass and its ZDF / TPT form (phasers)

Source: Zavalishin, *The Art of VA Filter Design* rev. 2.1.2 (`dsp-sources/zavalishin-va-filter-design-2.1.2.pdf`).
- §2.13, pp. 28–30 [VERIFIED]: `H(s) = (s − 1)/(s + 1)` (2.11, phase +π/2 → −π/2) and `H(s) = (1 − s)/(1 + s)` (2.12,
  phase 0 → −π, "the doubled phase response of the 1-pole lowpass": `arg = −2 arctan ω`, 2.13); "the allpass (2.12) can be
  obtained by simply subtracting the highpass output from the lowpass output of the multimode filter"; "high order
  allpasses are often created by simply connecting several of 1- and 2-pole allpasses in series" (p. 30). Footnote 23,
  p. 29: "The most common VA use for the allpass filters is probably in phasers." **Rev 2.1.2 has no phaser chapter** (the
  word appears only there); a phaser chapter, if a later revision has one, is not in the kit's mirror (gap, §9).
- **The tick, "1-pole allpass", p. 78** [VERIFIED]: `yAP = yLP − yHP = (s + 2v) − (x − s)`; code
  `xs := x - s; s := s + xs*2Glp; y := s - xs;` with `Glp = g/(1+g)`, `g = tan(π fc / sr)` (prewarped, the kit's convention,
  dsp.md State-variable filter). One state, three adds, one multiply per stage: the cheap form a 6- or 12-stage
  phaser wants (cutoff per stage differs, so `2Glp` is per stage).
- **Under fast modulation.** §2.16 "Cutoff as time scaling", pp. 40–42 [VERIFIED]: for a system whose cutoff gains
  precede the integrators and are all equal at every instant, cutoff modulation is a time warping of the whole system, so
  (a) "the stability of a system cannot be destroyed by the cutoff modulation" (p. 42) and (b) topologies with the
  same transfer function behave identically under it. Caveat in the book's footnote 29, p. 42: "this applies only to
  the idealized continuous-time systems. After conversion to discrete time the same argument will not automatically
  hold". For a stage whose cutoffs differ per stage (a phaser's: the Bi-Phase's are equal, the Uni-Vibe's are not) the
  "all equal" premise fails per stage, but each is a one-integrator TPT stage: §3.11 p. 78 says direct forms have "a
  largely inferior quality, compared to the TPT" for music DSP [VERIFIED], and the kit's note for the gate's
  filter says TPT is "stable under ... any rate of modulation" (Parker & D'Angelo, vactrol-and-lpg.md §2). So: **per
  stage TPT one-pole, never a direct-form biquad per stage, with the cutoff written every sample**.
- **Second order** (§4.7 "Allpass filter", p. 119, eq. 4.23) [VERIFIED]: `HAP(s) = 1 − 4R·HBP(s) = (s² − 2Rs + 1)/(s² + 2Rs + 1)`,
  phase = twice the 2-pole lowpass's; for R ≥ 1 it factors into two 1-pole allpasses, at R = 1 the square of one. With
  the kit's state-variable block (gen_state_variable: yBP) it is `x − 4R·yBP` (the book, in its later chapter on the SVF: "the allpass signal can be obtained as y = x − 4R·yBP"; smaller R makes the
  phase slope steeper at the centre: a resonant all-pass, a sharper notch pair).
- **Allpass substitution** (p. 92) [VERIFIED]: in a structure built of identical allpass elements, "we can always replace
  those allpass elements with an arbitrary other type of allpass elements" (the book's examples replace z⁻¹ by an
  analog allpass, i.e. a frequency warp).
- **Phaser mathematics we need [DERIVED, standard]:** n identical first-order stages `(ω_c − jω... )`: total phase
  `φ(ω) = n·(π − 2 arctan(ω/ω_c))` (the (s − 1)/(s + 1) of eq. 2.11 with s scaled by ω_c; the Bi-Phase stage is exactly this); adding the dry signal gives
  notches where φ = (2m + 1)π: ω/ω_c = tan((n − 2m − 1)π/(2n)) (n = 6: 3.73, 1, 0.268; n = 4: 2.41, 0.414). With
  feedback `g` from the output to the input: `H = H_n / (1 − g H_n)` (positive feedback: peaks where φ = 0 mod 2π,
  height 1/(1 − g)); stable for |g| < 1. Corners of the stages are free to differ (Uni-Vibe) or sit equal (Bi-Phase).

## 2. Schroeder all-pass, comb forms, and the classic reverberator

Sources: Smith, *Physical Audio Signal Processing* (`jos-allpass-two-combs.html` "Allpass from Two Combs",
`jos-schroeder-allpass-sections.html`, `jos-schroeder-reverberators.html`, `jos-freeverb*.html`) [VERIFIED].
- "Allpass from Two Combs": a feedforward comb in series with a feedback comb of equal delay M is allpass when the
  feedforward coefficient equals the feedback one: `v(n) = x(n) − a v(n−M)`, `y(n) = b0 v(n) + v(n−M)`, direct form II,
  `H(z) = (b0 + z^−M)/(1 + a z^−M)`, `|H| = 1` when `b0 = a` (real). Direct form I `y(n) = b0 x(n) + x(n−M) − a y(n−M)`
  needs 2M delays but "cannot suffer from 'internal' overflow".
- Schroeder reverb notation (Schroeder Reverberators, eq. 3.2): `AP_{N,g}(z) = (−g + z^−N)/(1 − g z^−N)`;
  `FBCF_{N,g} = 1/(1 − g z^−N)`.
- "A cascade of three Schroeder allpass sections. A typical value for g is 0.7. The delay-line lengths M_i are
  typically mutually prime and spanning successive orders of magnitude, e.g. 1051, 337, 113." (Schroeder Allpass
  Sections, Fig. 3.4.) Each section "expands each nonzero input sample ... into an entire infinite allpass impulse
  response" (impulse diffuser).
- Schroeder's own numbers (Schroeder Reverberators, quoting Schroeder 1962 p. 221): delays `M_i T ≈ 100 ms / 3^i`,
  i = 0..4, mutually prime; `g = 0.708` so that t60 = 2 s for the longest ([DERIVED]: 3.0 dB per pass, 20 passes of
  100 ms = 2 s); five in series give "an impulse-response echo density of about 810 per second, which is close to the
  desired thousand per second". "perceptually, their impulse responses are only colorless when they are extremely
  short (less than 10 ms or so). Longer allpass impulse responses sound similar to feedback comb-filters."
  Parallel combs: "between 3 and 4 comb filters in parallel ... incommensurate delays", open-loop gain "should not
  exceed about 0.85" (JCREV: four combs of 30–45 ms with a 4 × 4 mixing matrix, rows `[1 1 1 1; −1 −1 −1 −1;
  −1 1 −1 1; 1 −1 1 −1]`).
- Freeverb's "allpass" is `(−1 + (1 + g) z^−N)/(1 − g z^−N)`, "A true allpass is obtained only for
  g = (√5 − 1)/2 ≈ 0.618"; Freeverb's default g is 0.5; four allpasses + eight lowpass-feedback combs per channel,
  right channel delays + 23 samples ("stereospread") (Freeverb, Freeverb Allpass Approximation) [VERIFIED].
- **Colour:** Blesser in Dattorro Part 1 (Appendix 1, pp. 665–666) [VERIFIED]: "colorless reverberation, using all-pass
  structures, is perceptually not colorless. Even white noise passed through an all pass will not sound like real white
  noise. When passed through many such all-pass structures, it in fact sounds like a machine shop ... The reason is
  that frequency regions get bunched in time." And "An all pass within a larger loop must be used with great care
  since it has a sinelike variation in group delay. Hence the effective loop time and reverberation time vary with
  frequency."

## 3. Nested, lattice and Gerzon all-passes

JOS "Nested Allpass Filters", "Gerzon Nested MIMO Allpass" [VERIFIED].
- Nesting: "if H1(z) and H2(z) are unity-gain allpass transfer functions, then both H1(H2(z)) and H2(H1(z)) are
  allpass" (a conformal map of the unit circle to itself). With `S_i(z) = (k_i + z⁻¹)/(1 + k_i z⁻¹)`:
  `H2(z) = (k1 + z⁻¹ S2(z))/(1 + k1 z⁻¹ S2(z))`; nested first-order allpasses equal a two-multiply lattice (and
  one-multiply sections exist, JOS App. C.8.4). Replacing a delay element by an allpass: the Schroeder section's
  `z^−N` replaced by `z^−N` × another allpass.
- Gerzon's vector generalisation: `H(z) = [I + g U(z)]⁻¹ [g* I + U(z)]`, `U(z) = D(z) Q` with `D = diag(z^−m_i)`,
  mutually prime m_i, Q an orthogonal matrix, realised in vector direct form II
  (`v = x − g·U v_d`, `y = v + g* v_d`); "unlike FDNs, which are 'vector feedback comb filters,' the vectorized Schroeder
  allpass is a true multi-input, multi-output allpass"; gains may be filters `G(z)` with |G| ≤ 1. To avoid a delay-free
  loop "the paraunitary matrix must include at least one pure delay in every row". Used in IRCAM Spatialisateur.

## 4. Dattorro's plate (JAES 45(9), Sept. 1997, "Effect Design Part 1: Reverberator and Other Filters", pp. 660–684)

`dattorro-effect-design-part1.pdf` [VERIFIED; Fig. 1 read as an image, p. 662].
- **Topology (Fig. 1):** stereo in summed ×½ → predelay → one-pole lowpass ("bandwidth", `y = bw·x + (1 − bw)·y⁻¹`) →
  **input diffusion**: four all-pass lattices in series, delays **142, 107, 379, 277** samples (coefficients
  "input diffusion 1" = **0.75** on 142 & 107, "input diffusion 2" = **0.625** on 379 & 277) → split into two tank
  halves, each a loop: all-pass **decay diffusion 1** (delay **672 + EXCURSION** left / **908 + EXCURSION** right,
  coefficient **0.70**, "note sign": the coefficients drawn negative) → delay **4453** / **4217** → one-pole damping
  lowpass (`(1 − damping)` in, `damping` fed back) → × decay → all-pass **decay diffusion 2** (delay **1800** / **2656**,
  coefficient = decay + 0.15, floor 0.25, ceiling 0.50) → delay **3720** / **3163** → × decay → into the *other* half's
  input (cross-coupled). Taps at nodes 24 and 48 (the 672/908 lines) are **modulated**.
- **Table 1 defaults (p. 663):** sample rate **29761 Hz**; EXCURSION 16 samples ("Maximum peak sample excursion of
  delay modulation"); decay 0.50; decay diffusion 1 = 0.70 ("Controls density of tail"); decay diffusion 2 = 0.50
  ("Decorrelates tank signals ... = decay + 0.15, floor = 0.25, ceiling = 0.50"); input diffusion 1 = 0.750, 2 = 0.625
  ("Decorrelates incoming signal"); bandwidth = 0.9995 ("full bandwidth = 0.9999999"); damping = 0.0005 ("no damping =
  0.0"). Footnote 14, p. 665: modulation "at a rate on the order of 1 Hz, and at a peak excursion of about 8 samples for a
  sample rate of about 29.8 kHz" (the Table's 16 is the maximum).
- **Output taps (Table 2, p. 665), in samples at 29761 Hz, each × 0.6:** left = +node48_54[266] + node48_54[2974] −
  node55_59[1913] + node59_63[1996] − node24_30[1990] − node31_33[187] − node33_39[1066]; right = +node24_30[353] +
  node24_30[3627] − node31_33[1228] + node33_39[2673] − node48_54[2111] − node55_59[335] − node59_63[121].
  (Node names are Fig. 1's: 24_30 = after the left 672-line to the 4453 line, etc.) "the output tap structure produces a
  synthetic stereo image because the stereo input is converted to a monophonic signal at the reverberator input" (p. 665).
- **Lattice (§1.3.3, p. 664):** "Each diffuser has been given the topology of a two-multiplier lattice ... The two
  coefficients within each individual lattice must remain identical to maintain the all-pass transfer function, which is
  insensitive to coefficient quantization. The recommended range ... is from 0.0 to 0.9999999 ... If the lattice
  coefficients should exceed 1.0, instability would result. Making them both negative will change the character of the
  impulse response but does not destroy the all-pass transfer." "This all-pass lattice topology tends to clip
  prematurely at internal nodes, so the input to each lattice cannot be presented with a full-scale signal at all
  frequencies" (a float gen~ patch may not clip there [UNVERIFIED]). "The impulse response of each individual lattice ... is so long, in some
  cases the integration time constant of the human hearing system is exceeded ... an all-pass filter output may be
  perceived as discretized events, that is, not all pass." Footnote 10: "The reverberation network as a whole does not
  have an all-pass transfer function".
- **[DERIVED] The lattice as a Schroeder section:** the Schroeder section of §2 with `g = k` has the same all-pass
  magnitude for any |k| < 1; in `y(n) = −k x(n) + x(n−N) + k y(n−N)` form it is the lattice's input/output relation
  (Dattorro draws it with two multipliers k and −k around a delay line).
- **Scaling to another sample rate [DERIVED]:** multiply every delay by fs/29761 and round (the paper does not say how
  to scale); at 44.1 kHz: input 210, 159, 562, 410; tank 996 (mod), 6598, 2667, 5512; 1345 (mod), 6249, 3936, 4687;
  EXCURSION 16 → 23.7 samples, 8 → 11.9; at 48 kHz: 229, 173, 611, 447; 1084, 7182, 2903, 6000; 1464, 6801, 4284, 5101.
  The output tap lengths scale likewise. Decay time of the tank: set by `decay` and the loop length (the tank loop is
  ≈ 672 + 4453 + 1800 + 3720 = 10645 samples = 358 ms at 29761 Hz, left; right 908 + 4217 + 2656 + 3163 = 10944 =
  368 ms).
- **Limit cycles:** "magnitude truncation ... can reduce the network noise floor by 12–24 dB after the input
  signal is removed" and removes zero-input limit-cycle noise "perceived as a whooshing ocean noise floor" (§1.3.4, p. 664) —
  a fixed-point issue; in gen~'s 64-bit float, denormals are the corresponding care [UNVERIFIED for gen~].
- **Modulation (§1.3.7, p. 665):** "all-pass interpolation (as discussed in Part 2, Section 5) can be efficiently
  employed to modulate slowly the nominal tap point"; "A slight modulation will introduce undulating pitch change into
  the tank ... these built-in modulators serve to break up some pretty audible modes"; "Without the modulation, we may
  well describe the imaginary space ... as being enclosed by a picket fence. The slow modulation serves to increase
  effectively the sheer number of resonances"; "Ideally, all the delay lines in the tank diffusers should be modulated
  using different modulation rates and depths"; use "a quadrature oscillator to decrease the correlation"; for piano
  "the modulation, though slight, may be objectionable because of a perceived vibrato"; linear interpolation "will
  introduce time-varying low-pass filtering as an artifact, thus supplying some unaccounted damping to the tank.
  All-pass interpolation overcomes this". Footnote 15: the modulating oscillator must run at the audio sample rate
  "Otherwise, aliasing artifacts will be introduced".

## 5. Interpolated, modulated delays: linear, all-pass (Thiran), Lagrange

Sources: Dattorro Part 2 (JAES 45(10), Oct. 1997, "Delay-Line Modulation and Chorus", `dattorro-effect-design-part2.pdf`);
JOS "Fractional Delay Filters", "Lagrange Interpolation", "Thiran Allpass Interpolators" [VERIFIED].
- **Linear interpolation** (Part 2 §4, Fig. 23–24, p. 765): `v[n] = frac·x[i+1] + (1 − frac)·x[i]`, a first-order FIR
  `(1 − f) + f z⁻¹` whose gain at Nyquist is |1 − 2f|: **a time-varying low-pass, worst (a null at fs/2) at f = 0.5**
  [DERIVED from the coefficients; Part 2 §4.5 "High-Frequency Loss of Linear Interpolator" develops it with the polyphase
  view]. The loss changes as the LFO moves frac: an amplitude modulation of the highs, "unaccounted damping".
- **All-pass interpolation** (Part 2 §5, Fig. 29, p. 770): `v[n] = x[i+1] + (1 − frac)·x[i] − (1 − frac)·v[n−1]`, i.e.
  `H(z) = (a + z⁻¹)/(1 + a z⁻¹)` with `a = 1 − frac` (his "frac" is the fractional part): flat magnitude, one
  recursive element; "useful primarily for microtonal changes in pitch (less than plus or minus one semitone)";
  "sounds quite smooth in musical applications"; "makes the interpolation sound analog". Its delay does not track
  frac as evenly as the linear one (Fig. 30). The transient distortion from the time-varying coefficient "bottlenecks
  the useful transposition range of the all-pass interpolator to about plus or minus one semitone" (p. 774).
- **Coefficient warping (p. 771, eq. 40):** the substitution `a = (1 − τ)/(1 + τ)` with τ the fractional delay: the
  low-frequency simplification of `(1 − frac)` → `sin[(1 − τ)ω/2]/sin[(1 + τ)ω/2]` at frequency ω. Practical code uses
  "only the first five terms of the Taylor series" (p. 774). **This `a = (1 − τ)/(1 + τ)` is exactly the order-1
  Thiran coefficient** `a1 = (1 − Δ)/(1 + Δ)` with Δ the fractional delay (JOS Thiran, as dsp.md's tanh saturator
  used for its half-sample allpass until 2026-10-20, Δ = 0.5: a1 = 1/3) [VERIFIED both; the identity is ours].
- **Measured THD + N (Part 2 §5.4, p. 774; 400 Hz sinusoid, 0.1 Hz LFO, 44.1 kHz, 24-bit coefficients):** linear
  **−78 … −88 dB**; unwarped all-pass **−53 … −59 dB**; warped (5-term series) all-pass **−77 … −85 dB**, "An improvement
  of 26 dB". "We require that the implementation ... prevent prolonged Nyquist (Fs/2) oscillation that comes about when
  frac = 0 ... by forcing that circuit to interpolate by a constant fraction of a sample at all times, say, 1/256
  sample" (for the unwarped form; the warped series needs no such offset). The conclusion (§5.5): prefer warped all-pass
  where the extra computation is affordable.
- **Thiran, general order N** (JOS): `a_k = (−1)^k C(N, k) Π_{n=0..N} (Δ − N + n)/(Δ − N + k + n)`, maximally flat group
  delay Δ at DC; "For sufficiently large Δ, stability is guaranteed. Rule of thumb: Δ ≈ order"; "The mean group delay of any
  stable Nth-order allpass is N samples". Effective "since pitch perception is most acute at low frequencies". The
  recursive extension of Lagrange. **Its artefact under modulation** is the Part 2 one above (the recursive state is
  not reset when a changes: the transient); not separately sourced for order > 1 (gap).
- **Lagrange (FIR)** (JOS): `y(x) = Σ l_k(x) f(x_k)`, `l_k(x) = Π_{j≠k} (x − x_j)/(x_k − x_j)`; first order = linear
  interpolation; the fractional-delay form: an order-N FIR with delay N/2 + η, "maximally flat at DC". Costs N + 1
  taps; as with the linear case (order 1) its magnitude response depends on the fractional delay, so under modulation
  it is a time-varying low-pass (JOS's frequency-response examples for orders 1–5 at 0.4 samples were not read, so how
  fast the droop shrinks with order is [UNVERIFIED]); JOS also lists a Farrow structure (polynomials in the delay) for
  cheap coefficient updates (listed, not read). The kit's echo already uses `interp="spline"` (Catmull-Rom) for reads (dsp.md, gen~
  delay taps) [VERIFIED there].
- **Pitch change from a modulated delay [DERIVED]:** reading a delay of τ(t) samples gives output pitch ratio
  `1 − dτ/dt`; a sinusoidal τ = D·sin(2π f_m t) peaks at `2π f_m D` samples/s: for Dattorro's maximum
  EXCURSION 16 samples at 1 Hz and 29761 Hz, `2π·1·16/29761 = ±0.34 %` (±5.8 cents); at 8 samples ±2.9 cents.
  "the required pitch change is microtonal" (Part 2 / Part 1 §1.3.7), which is why all-pass interpolation is safe
  there.

## 6. Practitioner writing on diffusion and modulation

**Valhalla Shimmer notes** (`valhalla-shimmer-notes.pdf`, a compilation of the blog posts and the product page) [SECONDARY, read]:
- "In 2006, I experimented with extending Schroeder's early reverberator structure to much higher orders ... As the
  number of diffusors increased, the reverb decay started to sound less and less like a 'real' acoustic space, and more
  and more like some weird spooky backwards thing ... the attack and decay characteristics of the reverb changed from an
  exponential decay towards a bell, or Gaussian, curve ... Add some randomized modulation to each of the diffusors, and
  the result was an ethereal, ghostly soundscape." (Central Limit Theorem.)
- "diffuse delay lines": "networks of diffusors, that act like a single delay line when the Diffusion control is
  turned down to zero, and generate clusters of reflections when the Diffusion control is turned up."
- Diffusion = the diffusers' coefficients: "0.0 ... a straight delay. A coefficient in the 0.5 to 0.618 range will
  result in a reverb sound that slowly fades in. A coefficient of 0.9 results in a fairly long decay ... even if
  Feedback is set to zero." Size scales the delay lengths (and the decay). Mod Depth "translates to a constant value
  in samples, so it needs to be adjusted in conjunction with Mod Rate"; "dozens of random modulators ... each with a
  slightly different base modulation rate". Low Cut / High Cut filters in the feedback path make the decay brighten /
  darken as it decays. Mix: power-complementary crossfade.
**Valhalla blog, ÜberMod / Plate** ([UNVERIFIED]: the pages returned 403 here; seen as search excerpts only):
diffusion as "several short cascaded allpass delays" building initial echo density, allpass coefficients "roughly 0.7 to
0.99" give faster attack and higher echo density but a metallic sound; modulation "reduces the metallic coloration";
the ÜberMod diffusion network "was based on the fixed allpass network used in the chorus/echo algorithm of the PCM70";
diffusion inside the feedback loop so "echo density builds with each repeat when feedback is above 0 %".

## 7. Shimmer: pitch shift in the feedback loop

- **Structure [SECONDARY, read]:** Reason Studios, "Building shimmer reverb": "shimmer reverb is a pitch-shifted reverb
  tail in a feedback loop"; Eno "is generally credited with inventing the effect"; the patch: reverb → splitter →
  (1) to the return, (2) to a pitch shifter set to **a single octave** (interval of an octave "is your safest bet"),
  the shifter's output fed back into the reverb's input: "This shifts the reverb tail in pitch again and again,
  making for the characteristic sound"; "Because you're adding higher frequencies to the signal ... engage the LPF";
  a second shifter "detuned ... panned ... delayed slightly"; "Dial back on the delay and feedback if you find things
  are sounding a little seasick".
- **Valhalla Shimmer notes [SECONDARY, read]:** pitch shift is "in the feedback loop", **−12 … +12 semitones**;
  "By setting the Shift amount to +12 semitones, and the Feedback to 0.5 or greater, the classic 'shimmer' sound is
  produced"; "pitch shifting will only be audible with Feedback values greater than zero"; modes Single (one shift up or
  down), Dual (up and down in parallel), SingleReverse / DualReverse ("each grain is reversed before it is pitch shifted
  ... smoother"), Bypass. Its shifter was "a simple yet effective algorithm ... to generate similar artifacts to what a
  'de-glitched' pitch shifter would produce in a feedback loop with a reverberator, but without ... autocorrelation
  analysis ... added noise and texture to the feedback loop ... sounded like a huge orchestra warming up". The same
  notes' "Eno trick" began in 2004; the 12 semitones case with Feedback ≥ 0.5 is the number to start from.
- **[DERIVED] What the loop does:** a +12 st shift per pass doubles frequencies each trip, so after n trips the tail's
  energy sits at 2ⁿ × the input: a 1 kHz input reaches 16 kHz after four passes, then above Nyquist unless a lowpass or
  the reverb's damping removes it: the loop **needs** a high cut and a feedback below 1; the tail is built from
  the diffuser network's echo density, the shift from a delay-line pitch shifter (two taps crossfaded, the
  pitch ratio = §5's `1 − dτ/dt` with a sawtooth τ and the grain windows hiding the wrap), which at ±12 st is far past the
  all-pass interpolator's ±1 semitone limit (Part 2 §5.4): use linear / higher-order interpolation there.
- **[UNVERIFIED]** Eventide ShimmerVerb's own account (Sound On Sound says shifters sit in the feedback loop, Eventide's
  feature list says parallel on the tail; the sources disagree).

## What this suggests for the kit (inference, not source)

- **Techniques, not circuit modules.** (1) *All-pass section*: the Zavalishin first-order TPT tick (p. 78) with
  per-sample `fc`, optionally second order via the SVF (`x − 4R·yBP`), the unit of a phaser, a smear or a spectral
  dispersion. (2) *Phaser cascade*: n sections + per-stage corners + feedback `H/(1 − gH)` + dry mix. (3) *Schroeder /
  lattice diffuser*: delay N, coefficient g (|g| < 1), optionally an LFO on the delay read. (4) *Diffusion network*: a
  series of (3) with mutually prime delays, input diffusion 0.75 / 0.625 as the default set, stereo spread; the cascade
  length is the "smear" control (Valhalla: more diffusers = longer fade-in). (5) *Tank*: the Dattorro loop (decay
  diffusion, delay, damping, decay gain, cross-coupling), as a technique, with its 12 delay lengths as data scaled by
  fs/29761. (6) *Modulated delay read* with the interpolator choice per use: linear (chorus-like, loses highs), warped
  first-order all-pass/Thiran (reverb modulation, ≤ ±1 semitone), spline/Lagrange (pitch-shifter grains). (7) *Shimmer*:
  a pitch shifter in the tank's feedback with a high cut. The **circuit module** is the Bi-Phase (circuits/mutron-bi-phase.md),
  which uses (1)+(2) with the cell law.
- **Parameters** (the all-pass block): cutoff/delay per stage, coefficient g, stage count, feedback, dry/wet; (diffuser)
  size scaler, diffusion g, mod rate/depth/decorrelation; (tank) decay, damping, bandwidth, predelay; (shimmer) shift in
  semitones (−12…+12), feedback, high cut, dual/single. All are Valhalla/Dattorro-named knobs; ranges above.
- **Open gaps:** (1) Zavalishin's phaser chapter (later revision) is not in the kit's mirror; (2) no source for the
  Thiran / Lagrange *transients under fast modulation* beyond Dattorro's first-order result (Välimäki et al. are cited by
  Dattorro as ref. [45] but not fetched); (3) the Valhalla blog posts (403) and Eventide's account of ShimmerVerb;
  (4) Dattorro Fig. 1 coefficients' signs per lattice (the "note sign" convention) were read from the diagram only;
  (5) no number for a good shimmer pitch-shifter's grain length / crossfade; (6) none of the above was measured in gen~;
  the kit's rule (architecture/dsp-blocks.md) wants each claim as a test against a reference first.

# Gen blocks: techniques, circuit modules, instruments

User, 2026-10-19: "build them as kit blocks … find your favorite and coolest and best implementation of these
things". User, 2026-10-20 (PLANS/2026-10-20-kit-layers.md): "we have all of these modules that exist that are the
backbone of these instruments, either that expose their modularity, or that wrap it (the roland synths using the same
filter chip, that's their modular building block, they're just wrapping it, this is what we're doing)".

A gen block is GenExpr that is the same in every device that has it and improves in one place. The kit's DSP is in
three layers; each layer uses only the layers below it:

| layer | where | what it is | may use |
|---|---|---|---|
| 1. techniques | `m4l_dev/techniques/` (`Technique`) | how to do DSP well, with no circuit identity: antialiasing, zero-delay structures, a soft clip, an echo's loop | other techniques |
| 2. circuit modules | `m4l_dev/circuit_modules/` (`CircuitModule`) | one modelled piece of hardware: a chip, a section of one, an instrument's circuit block | techniques |
| 3. instruments | the devices' own repositories (2sl stab, gate, filter, drums) | wire modules and techniques, and either expose a module (gate shows the 259) or wrap it (drums) | modules, techniques |

Every block is chosen by numbers against a stated reference (the analog model, the tempo grid, an oversampled ideal)
and keeps its claims as tests.

## The pattern every gen block keeps (both layers)

- **Python**: a `Technique` or `CircuitModule` subclass (`m4l_dev/gen_blocks.py`; never `GenBlock` directly). An
  instance is made with a name and its inputs as GenExpr expressions
  (`ZeroDelayLadderFilter("ladder", input="osc", cutoff_hz="fc", resonance="reso")`). The name prefixes every
  History, Delay and local it makes; its outputs are locals named in its docstring (`ladder_out`). It gives
  `functions()` (shared by every instance, one body per name: a value that differs per instance is a function
  argument, not baked into the body), `declarations()` and `statements()`. A block has no Params: the instrument
  declares its controls and passes expressions.
- **The device's gen~ code** is a template: `/*GEN_BLOCK_FUNCTIONS*/` first (before its own functions),
  `/*GEN_BLOCK_DECLARATIONS*/` among its declarations, and one `/*<NAME>*/` per instance where the block's statements
  run, after the device has computed its inputs. `gen_code_with_blocks(template, blocks, name, other_replacements)`
  fills them (and the device's own markers) with `fill_template`'s rules: a missing or extra marker, a name that
  isn't an identifier, two instances of one name, one function name with two bodies, all fail the build.
  `smoothing_coefficient(ms, sample_rate)` is the kit's, always included; devices use it, never a copy.
- **Constants** a display also needs come from the block, never a copy: a block with a display gives
  `response_script_code()` (an ES5 template in `templates/`, filled from the block's constants), and a test holds the
  script, the Python formula and the rendered block equal.
- **Only what Max accepts.** The kit renderer (`m4l_dev/genexpr.py`) is our subset, not Max: every construct a block
  uses has a source or a real GenExpr precedent in references/dsp.md ("gen~").
- **Cites its sources**: the class's `references_entry` is a references/ file with a `## ` heading naming the block's
  source file, and the block's docstring names that file.
- **Tests**: each block's claims on a small harness program around it (`tests/gen_block_harness.py`), at the lowest
  sample rate that still tests the claim.

## Techniques (layer 1)

A technique **may** contain: a DSP method, the method's constants (each sourced or measured in its docstring), other
techniques. Its inputs are signals and the method's own quantities (Hz, Q, a feedback gain, cents, ms).

A technique **may not** contain: a circuit's identity (a part number it claims to be, a unit's rails, trims,
tolerances or voltages), a circuit module, an instrument's controls. Borrowing a measured number from a circuit study
(the echo's glide ratio from the RE-201 study) is allowed and said; claiming to model the circuit is not: that is a
module.

Sources: a section of `references/dsp.md`. Tests: `tests/test_techniques.py`.

| technique | file | what it is | its claims (tested) |
|---|---|---|---|
| `ZeroDelayLadderFilter` | `zero_delay_ladder_filter.py` | 4-pole TPT ladder, the loop solved with no unit delay (Zavalishin eq. 5.8), tanh at the loop's input; Resonance 0..1 → k 0..4.35; display: `templates/zero-delay-ladder-response.template.js` | sings at fc ±3 cents at 300 Hz / 3 kHz / 12 kHz from Resonance 0.92; rings out below; bounded driven hard at 0.45 sr; small signals = the display's response |
| `AntiderivativeTanhSaturator` | `antiderivative_tanh_saturator.py` | tanh = x + (tanh x − x): the residual antialiased (first-order ADAA, Bilbao 2017), x through a half-sample Thiran allpass; half a sample late; with a `bias`, tanh(x + b) - tanh(b) | 8 kHz hot sine: aliases −24 → < −50 dB below 10 kHz; flat (±0.05 dB) to 15 kHz; exact for near-equal samples; biased: the slid curve, its aliases < -48 dB (naive > -30) |
| `AntiderivativePiecewiseLinearShaper` (`PiecewiseLinearTable`) | `antiderivative_piecewise_linear_shaper.py` | a transfer of straight pieces with first-order ADAA, its antiderivative closed form per piece; the table's three GenExpr functions named by a digest of its pieces | the functions equal the table and its integral; exact on a piece; a hot 3 kHz clip's aliases below 10 kHz at least 6 dB under the naive clip's; two tables are two functions |
| `KneeSoftClip` | `knee_soft_clip.py` | unity up to a knee (a device constant), then knee + (1 - knee) tanh(excess / (1 - knee)); memoryless; headroom computed in decimal | unity below the knee; value and slope continuous at the knee; bounded by 1, odd, rising; a knee outside (0, 1) fails the build |
| `BandLimitedEdges` | `band_limited_edges.py` | 4-point polyBLEP jumps and polyBLAMP corners into a two-sample look-ahead ring; one per voice for every oscillator | saw < −70 dB, triangle < −85 dB alias below 10 kHz at C7 / C8; after a restart nothing from before it comes out |
| `TapeStyleEcho` | `tape_style_echo.py` | stereo delay loop that behaves like tape: one time, re-read D early; LP / HP / diffusion / saturator in the loop; glide ≤ 0.5 ms per ms; wow and flutter as pitch; Stop; rounds for a display | repeats ±1 ms of n T; read speed in [0.5, 1.5]; over unity it howls, held; under, it dies; wow / flutter RMS cents as set; Stop empties it |
| `ZeroDelayStateVariableFilter` | `zero_delay_state_variable_filter.py` | 2-pole multimode SVF, zero-delay feedback (Zavalishin eq. 4.14), prewarped at fp (eq. 3.18); LP, BP, HP, unit-peak BP; for a circuit's two-pole stages by cutoff and Q | small signals = the prewarped analog SVF ±0.05 dB; exact at fp; LP + 2R BP + HP = input; rings at fc with tau Q / (pi fc); bounded under audio-rate modulation |
| `SidechainStylePump` | `sidechain_style_pump.py` | a gain that dips on every division of the beat and swells back (a ducked-compressor sound), or the gate; a quarter-sine ramp in, a power recovery, Live's beat or its own clock with a 20 ms hand-over, a 0.442 ms glide on the gain; display: `templates/sidechain-pump-duck.template.js` | the duck equals the display's shape (Python, script, rendered) on the own clock and on Live's; depth 0 is unity; the gain has no step through a clock hand-over; the gate's open and shut ends |
| `ZeroDelayOnePoleFilter` | `zero_delay_one_pole_filter.py` | 1-pole LP / HP, zero-delay (TPT, Zavalishin §3.10), prewarped; each output's affine response this sample, for blocks that solve a loop through it; for a circuit's RC corners | small signals = the prewarped analog one-pole (2e-4); LP + HP = input under modulation |
| `ZeroDelayAllpassCascade` | `zero_delay_allpass_cascade.py` | first- and second-order all-pass sections (the bilinear (1 - s)/(1 + s) and (s² - 2Rs + 1)/(s² + 2Rs + 1)) as normalised lattices, lossless under any cutoff motion; an optional feedback loop (coupling HP, feedback LP) solved with no unit delay, an optional rail at the loop's input; a phaser's core, the kit's all-pass for smearing | impulse energy 1 ± 1e-9; = the prewarped analog all-passes; -90 / -180 degrees at the corner ± 0.05; feedback peaks 1/(1 - k); energy conserved to 1e-9 with cutoffs jumping every sample (the TPT form gains 7.7x there); bounded in a 0.95 loop under that; no zipper (a 64-sample stepped glide is caught) |
| `LedDrivenPhotocell` | `led_driven_photocell.py` | LED current → CdS cell resistance, R = A I^-p + B, quick one-pole light, slow recombination dark (2sl gate's vactrol law and memory, constants the caller's); the 292 channel and the Bi-Phase run on it | settles on the law; 63 % at the attack time; undriven reaches the span's end at the release time ±2 %, the power-law turn-off; the 292 channel bit-identical on it; the law as run-time expressions renders what the numbers render (1e-9) |
| `DrumEnvelope` | `drum_envelope.py` | a hit's amplitude envelope (Microtonic's laws): exponential (the attack the decay reversed in time, a true exponential decay, 60 dB over the decay time), linear ("gated"), clap burst (count pulses a spacing apart, then the decay; UNVERIFIED law); a hit restarts the attack from the present level; mode held from the hit | the decay's constant ratio and -60 dB at its time, then idle; the attack = the reversed curve, 1 at its time; linear straight both ways; a restart never steps (at most the attack's own steepest slope); pulses at 0, s, 2s, 3s, then the decay; a count of 1 = the exponential |
| `PitchModulator` | `pitch_modulator.py` | a hit's offset (semitones for pitch, or any target's units) by Decay / Sine / Triangle / Square / Saw down / Random (LP seeded noise, cutoff = rate; rate 0 = one value a hit: a general per-hit random); cyclic shapes start at +amount; run two samples ahead in the edges' ring so the offset is now; `frequency_ratio` = 2^(offset / 12) | the decay's curve from amount to 0 at its time; the cyclic waves from each hit (1e-9 off the edges); rate 0 holds the initial offset; C7 square / saw aliases -76 dB (trivial -24.6); random rate 0: one seeded value a hit, same seed same values; random's RMS amount / sqrt 3 at 20 Hz to 2 kHz |
| `SeededWhiteNoise` | `seeded_white_noise.py` | uniform white noise from Park-Miller's minimal standard (16807 z mod 2^31 - 1, exact in 64-bit floats); starts over when `seed` changes or on `restart`; the seed a device's seeded sequence draws (architecture/seeded-random.md) | Park & Miller's check value (z10001 = 1043618065); = the Python model bit for bit; seed and restart repeat it; mean 0, variance 1/3, no correlation at lags 1-7 |
| `LfsrMetallicNoise` (`METALLIC_NOISE_SOURCES`) | `metallic_noise.py` | after the Jomox MetNze (law UNVERIFIED): an 8-bit shift register at `tune_hz`, feedback the parity of the bits `pattern` selects, its low bit out, steps band-limited; the seam every metallic source keeps (`hit`, `tune_hz`, `pattern` in; `<name>_out` in [-1, 1], two samples late), where an ADX-1-style source goes | = the Python register; no pattern stalls, more than 100 distinct tone patterns; the tune pitches it (period 4 L at sr / 4); a hit repeats it; every listed source keeps the seam, two in one voice |
| `BellEqualizer` | `bell_equalizer.py` | a peaking band on the SVF: Zavalishin's band-shelving filter (§10.6, eq. 10.19), out = input + (G - 1) x unit-peak BP at Q sqrt(G); ±40 dB, Q 0.5-20 | exact at the centre (±0.01 dB at 100 Hz - 10 kHz, ±40 dB); = eq. 10.19 bilinear ±0.05 dB; Q = the width at half the dB; a cut undoes the same boost (1e-9); 0 dB is the input |
| `HalfbandUpsampler`, `HalfbandDownsampler` | `halfband_oversampler.py` | 2x up and down, HIIR's two-path polyphase IIR half-band (8 coefficients, transition 0.04: 99.3 dB stop band from 0.29 of the doubled rate); a section between them runs twice a sample | the port = HIIR's published 12-coefficient design (2e-7); flat to 0.21 (1e-6 dB); a 30 kHz tone at 2x folds at -113.5 dB (naive 0 dB); an FM pair at 2x aliases -84 dB, at 1x -11.8 dB; up + down flat to 15 kHz, 3.07 samples late; the upsampler's image < -95 dB |

Why the pump is a technique: it models no compressor, it draws the dip from the beat.

Why the ladder and the echo are techniques: the ladder is the textbook ideal ladder (four one-poles, one tanh), on no
schematic, with the method's controls; the echo models no machine (its tape is a saturating loop, its time synced ms).
The modelled Moog ladder is the circuit module `MoogTransistorLadder` (below); a Roland ladder or an RE-201 would be
circuit modules too.

## Circuit modules (layer 2)

A circuit module is one modelled piece of hardware, one module file each, in `m4l_dev/circuit_modules/`. Its
interface:

- **Inputs are the circuit's**: its controls and CV in the circuit's units: volts at its pins, its clock in Hz, the
  quantity its resistors set (a damping, a gain), a logic pin as a 0 / 1 expression. All GenExpr expressions,
  keyword-only.
- **Wiring choices** fixed when the instrument is built (a strap, which pin feeds which) are Python constructor
  values, checked (`clock_ratio=100`: pin 12).
- **Build character** is `character=`, an instance of the module's `character_type`: a frozen dataclass of numbers
  (rails, trims, tolerances, leakage), defaulting to the datasheet's typical unit. Two instances with two characters
  are two units. Character never goes into a shared function's body (the function takes it as arguments), so two
  units can sit in one patch.
- **Character at run time**: an instrument that exposes a unit's unknowns to be found by ear (2sl phaser's Cells page)
  passes `character_inputs={field: GenExpr expression}`; only the fields the module lists in
  `runtime_character_fields` (others fail the build), read through `character_term(field)`. `character` still holds
  the numbers: the module's Python model and the parts the module keeps fixed use them. The instrument keeps the
  expressions in range (its controls' ranges).
- **Outputs** are the circuit's pins, in its units. Where a technique must run once on their sum (band-limiting), the
  module takes the summing amplifier's gains at the pins and gives the sum.
- **Points**: a memoryless stage the instrument evaluates at several points a sample (an oscillator's sub-samples, a
  probe looking ahead along the voice's path) gives its point code by method (`point_statements(point, ...)`,
  `segment_output_volts(point, before)`), its per-sample inputs latched by `statements()`; an oscillator gives its
  wave at any phase (`sine_at`, `wave_at`). A step that runs several times a sample (oversampling) is the instance's
  marker placed that many times, and `oversampling=` (a wiring choice) says how many.
- **Character in a function**: where a shared function's body is computed from the character (a piecewise table of the
  unit's fold points), the function is named by a digest of what it was computed from (`PiecewiseLinearTable`), so
  two units are two functions: the rule above (two units in one patch) holds by the name.
- **Cites its circuit**: `references_entry` is its own `references/circuits/<circuit>.md` (datasheet, schematic:
  quoted with pages, fetched and checked by `references/circuits/fetch-circuit-sources.sh`).
- Built from techniques; never from another layer's code (no device, no patch builder).

Tests: `tests/test_circuit_module_<module>.py`.

| module | file | the hardware | its claims (tested) |
|---|---|---|---|
| `Buchla259PrincipalOscillator` (`Buchla259PrincipalOscillatorCharacter`: the sine shaper's drive) | `buchla_259_principal_oscillator.py` | the 259's sheet 2A: a triangle core bent into a sine by a shaper driven short of its peaks; Hz in (`frequency_hz`, linear through-zero `frequency_modulation_hz`), evaluated every step; `reset_statements()` (a note's sync); `oversampling` steps a sample; `sine_at(phase)` | the shaper's 3rd at -38.4 dB, no even harmonics, peak 1; drive 1 is a sine; at its frequency at 1x and 2x; FM through zero runs it backwards; a 30 Hz-a-sample sweep followed exactly; a reset starts the cycle |
| `Buchla259TimbreSection` (`Buchla259TimbreSectionCharacter`: the cells' rail, the node floor, the limiter's zener and diodes) | `buchla_259_timbre_section.py` | the 259's sheet 3A: the drive stage (10.3 kHz roll-off as a gain), Symmetry's offset, five CA3160 cells at their rails (DAFx-17 eqs. 8-11) with the node floor and the zener limiter, as straight pieces through the piecewise-linear shaper; volts in (`drive_volts`, `symmetry_offset_volts`) and Hz (`frequency_hz`); points and segments; `TONE_FILTER_HZ` for the instrument | DAFx-17's fold points, cell nodes and sum; the extras (one-sided floor, +-5.1 V); the GenExpr pieces = the circuit model; each running segment = the folder's mean along it; a 4.5 V unit's fold points scale; two units in one patch |
| `Buchla259ModulationOscillator` (`Buchla259ModulationOscillatorCharacter`: none yet) | `buchla_259_modulation_oscillator.py` | the 259's sheet 4A modulator: sine, triangle, saw, square, band-limited by `BandLimitedEdges` and run that many steps ahead, so its output is now; Hz in, every step; `reset_statements()`; `wave_at`, `wave_integral_at` | the trivial waves away from the edges; saw and square aliases 30 dB under the naive; a reset restarts the cycle with nothing of the old; the integral's slope is the wave |
| `Buchla292LowPassGateChannel` (`Buchla292LowPassGateChannelCharacter`: the photocell fit, the LED driver's floor and ceiling, the highest resonance share) | `buchla_292_low_pass_gate_channel.py` | one 292 channel: the vactrol on `LedDrivenPhotocell` (LED current in amps; turn-on over `attack_ms`, the measured power-law turn-off over `decay_ms`; Rf = A I^-1.4 + B) into the DAFx-13 network on `ZeroDelayStateVariableFilter`, prewarped at its -3 dB corner; `mode` 0 VCA / 1 both / 2 lowpass, `resonance`; outputs, Rf, DC gain, corner; `reset_statements()` | the VTL5C3/2 fit; the both network's two poles 15-20x apart, its 780 Hz corner at 100k, VCA -32 dB; full resonance must stay damped; a held drive settles on the fit; the release is the power law (1 MOhm at `decay_ms`); every mode -3 dB at its corner |
| `Ltc1060Mf10Section` (`Ltc1060Mf10Character`) | `ltc1060_mf10_section.py` | one section of the LTC1060 / MF10 dual switched-capacitor filter: an LDI state-variable filter stepped per clock tick at its CLK pin's clock (centre = clock / 50 or 100), all of a sample's ticks at once in closed form (A^n), LP / BP held between ticks, HP the live summer; the staircase band-limited by `BandLimitedEdges`; the chip's Q enhancement, rails, clock feedthrough, pin 12 hold; a section clocked from another's through a divider; volts in and out; 3 samples late; display: `templates/ltc1060-mf10-section-response.template.js` | rings at clock / 100 ±0.5 %; small signals = the display's response ±0.3 dB; whistle at the clock at the datasheets' level; none past Nyquist; two free sections beat; a divided one ticks on every n-th tick, phase-locked; past oscillation steady under the rail; Q enhancement sings only near the top; hold freezes LP / BP; the chip's in-band image kept, the host's folds < -45 dB |
| `MutronBiPhase` (`MutronBiPhaseCharacter`) | `mutron_bi_phase.py` | the whole Mu-Tron Bi-Phase (ARP 77204): two six-stage LED + photocell all-pass phasors (6.8 nF, 220k ∥ cell) on the all-pass cascade, the input stage's positive feedback (k ≤ 0.862, its 18 kHz low-pass), C12's coupling into R26 ∥ the pot, the passive dry / wet mix (the foot switch's photocell), two sweep generators (0.1–18 Hz, sine / square), A from Gen 1 / pedal, B from Gen 1 / Gen 2 / pedal, Norm / Rev, B's input In A / Out A (series) / In B; volts in and out; the cells, the LED driver, trims and taper as character, UNVERIFIED defaults (references/circuits/mutron-bi-phase.md §8); the sweep's unknowns (the sweep cells' law, the LED's dark and full currents, the cells' times, the stages' spread, the sine's roundness, the feedback taper) movable at run time, the bypass cell kept at the numbers | the stages are 180 degrees at the formula's notches (corner 1/(2π (R ∥ 220k) 6.8 nF), bilinear-mapped) ± 0.5; the output = the Python model ± 0.1 dB; full feedback raises the peaks at 1.73 x the corner 15–17.3 dB at J1-1 (k = 0.862); series = A's response x B's; full feedback, 18 Hz square, 3 V noise: bounded, silent after; Rev mirrors B's sweep; generators at their rate, held to 0.1–18 Hz; foot switch off = dry; the run-time character at its defaults = the numbers' unit (1e-6 V), its dark current moves the sweep's bottom to the law's corner, the bypass stays dry |
| `MoogTransistorLadder` (`MoogTransistorLadderCharacter`: VT, C, each stage's capacitor ratio, the input pair's offset, the input buffer's scale, the converter's reference current and V/oct, the Emphasis pot's top k, the output coupling corner) | `moog_transistor_ladder.py` | the 904A / Minimoog VCF (US 3,475,623; Minimoog board 4 circuit 6): the input pair and four stages, each its own tanh (D'Angelo & Valimaki 2014 eqs. 1-2), the trapezoidal rule on all five, the loop solved by 2 Newton iterations (a cyclic-bidiagonal sweep, never singular), `oversampling` 2 (default: twice a sample between the kit's `HalfbandUpsampler` / `HalfbandDownsampler`, 3.07 samples late) or 1; volts in (`input_volts`, `control_volts` through the exponential converter, fc = If / (8 pi C VT)) and the pot (`emphasis`); the output buffer's unity LF gain, its 15.4 Hz coupling; `reset_statements()` | the cutoff law; small signals = the twin (the prewarped ladder, at 2x times the half-band squared) ±0.01 dB / 0.3 degrees, mismatched units too; pass band 1 / (1 + k) ±0.02 dB; onset at k 4; full Emphasis (k 4.2) sings 19.6 cents flat as the RK4 model does (±0.5 c to 3 kHz, ±2.5 c at 12 kHz); 2 iterations = 8 (1e-3); bounded under 30 V noise and a cutoff jumping 12 octaves a sample; aliases of a hot sine -30 → < -53 dB at 2x; an offset's even harmonics kept, its DC taken by the coupling; 5 tanh an iteration a step |

## What is enforced (tests/test_gen_block_layers.py)

- every `GenBlock` subclass in `m4l_dev/` is in `techniques/` (a `Technique`) or `circuit_modules/` (a
  `CircuitModule`), never both;
- a technique imports only `gen_blocks`, `build_error`, `generated_scripts`, other techniques and the standard
  library (so never a circuit module); a circuit module the same plus techniques;
- every block cites a `references_entry` that exists, has a `## ` heading naming the block's file and is named in
  its docstring; a module's is under `references/circuits/`;
- a circuit module file holds exactly one `CircuitModule`, whose `character_type` is a frozen dataclass whose fields
  all default to numbers;
- the pattern's build rules (markers, instance names, one function body per name).

Not enforced by a test, kept by review: a technique carries no circuit identity in its constants; a module's inputs
are in the circuit's units.

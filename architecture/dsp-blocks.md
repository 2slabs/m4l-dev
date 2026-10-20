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

Why the pump is a technique: it models no compressor, it draws the dip from the beat.

Why the ladder and the echo are techniques: the ladder is the textbook ideal ladder (four one-poles, one tanh), on no
schematic, with the method's controls; the echo models no machine (its tape is a saturating loop, its time synced ms).
A modelled Moog / Roland ladder or an RE-201 would be circuit modules.

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
| `Buchla292LowPassGateChannel` (`Buchla292LowPassGateChannelCharacter`: the photocell fit, the LED driver's floor and ceiling, the highest resonance share) | `buchla_292_low_pass_gate_channel.py` | one 292 channel: the vactrol (LED current in amps; turn-on over `attack_ms`, the measured power-law turn-off over `decay_ms`; Rf = A I^-1.4 + B) into the DAFx-13 network on `ZeroDelayStateVariableFilter`, prewarped at its -3 dB corner; `mode` 0 VCA / 1 both / 2 lowpass, `resonance`; outputs, Rf, DC gain, corner; `reset_statements()` | the VTL5C3/2 fit; the both network's two poles 15-20x apart, its 780 Hz corner at 100k, VCA -32 dB; full resonance must stay damped; a held drive settles on the fit; the release is the power law (1 MOhm at `decay_ms`); every mode -3 dB at its corner |
| `Ltc1060Mf10Section` (`Ltc1060Mf10Character`) | `ltc1060_mf10_section.py` | one section of the LTC1060 / MF10 dual switched-capacitor filter: an LDI state-variable filter stepped per clock tick at its CLK pin's clock (centre = clock / 50 or 100), all of a sample's ticks at once in closed form (A^n), LP / BP held between ticks, HP the live summer; the staircase band-limited by `BandLimitedEdges`; the chip's Q enhancement, rails, clock feedthrough, pin 12 hold; a section clocked from another's through a divider; volts in and out; 3 samples late; display: `templates/ltc1060-mf10-section-response.template.js` | rings at clock / 100 ±0.5 %; small signals = the display's response ±0.3 dB; whistle at the clock at the datasheets' level; none past Nyquist; two free sections beat; a divided one ticks on every n-th tick, phase-locked; past oscillation steady under the rail; Q enhancement sings only near the top; hold freezes LP / BP; the chip's in-band image kept, the host's folds < -45 dB |

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

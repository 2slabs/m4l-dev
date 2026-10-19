# DSP blocks: gen~ code a device includes

User, 2026-10-19: "build them as kit blocks … find your favorite and coolest and best implementation of these
things". A DSP block is GenExpr that is the same in every device that has it (2sl stab, 2sl gate) and improves in
one place. Each is chosen by numbers against a stated reference (the analog model, the tempo grid, an oversampled
ideal) and keeps its claims as tests. Sources: references/dsp.md.

## The pattern

- **Python** (`m4l_dev/gen_<block>.py`): one `GenBlock` subclass. An instance is made with a name and its inputs as
  GenExpr expressions (`LadderFilter("ladder", input="osc", cutoff_hz="fc", resonance="reso")`). The name prefixes
  every History, Delay and local it makes; its outputs are locals named in its docstring (`ladder_out`). It gives
  `functions()` (shared by every instance, one body per name), `declarations()` and `statements()`. A block has no
  Params: the device declares its controls and passes expressions, so a block serves devices whose knobs differ
  (2sl stab's Dub macro and 2sl gate's Repeats / Wow / Saturation feed the same echo). A block may be made of blocks
  (the echo's loop saturators are saturator instances).
- **The device's gen~ code** is a template: `/*GEN_BLOCK_FUNCTIONS*/` first (before its own functions),
  `/*GEN_BLOCK_DECLARATIONS*/` among its declarations, and one `/*<NAME>*/` per instance where the block's statements
  run, after the device has computed its inputs. `gen_code_with_blocks(template, blocks, name, other_replacements)`
  fills them (and the device's own markers) with `fill_template`'s rules: a missing or extra marker, a name that
  isn't an identifier, two instances of one name, one function name with two bodies, all fail the build.
  `smoothing_coefficient(ms, sample_rate)` is the kit's; devices use it, never a copy.
- **Constants** a display also needs come from the block, never a copy: the ladder's response is
  `templates/ladder-response.template.js`, filled from `gen_ladder.py` (`response_script_code()`), and a test holds
  the script, the Python formula and the rendered block equal.
- **Only what Max accepts.** The kit renderer (`m4l_dev/genexpr.py`) is our subset, not Max: every construct a block
  uses has a source or a real GenExpr precedent in references/dsp.md ("gen~"), e.g. `Delay d(size, 2)` for a Delay
  read at two places, `interp="spline"` (documented as Catmull-Rom, which the renderer does).
- **Tests** (`tests/test_dsp_blocks.py`): each block's claims on a small harness program around it, at the lowest
  sample rate that still tests the claim (the whole file runs in seconds), plus the pattern's build rules.

## The blocks

| block | module | what it is | its claims (tested) |
|---|---|---|---|
| ladder | `gen_ladder.py` | 4-pole TPT ladder, the loop solved with no unit delay (Zavalishin eq. 5.8), tanh at the loop's input; Resonance 0..1 → k 0..4.35 | sings at fc ±3 cents at 300 Hz / 3 kHz / 12 kHz from Resonance 0.92; rings out below; bounded driven hard at 0.45 sr; small signals = the display's response |
| saturator | `gen_saturator.py` | tanh = x + (tanh x − x): the residual antialiased (first-order ADAA, Bilbao 2017), x through a half-sample Thiran allpass; half a sample late | 8 kHz hot sine: aliases −24 → < −50 dB below 10 kHz; flat (±0.05 dB) to 15 kHz; exact for near-equal samples |
| edges | `gen_edges.py` | 4-point polyBLEP jumps and polyBLAMP corners into a two-sample look-ahead ring; one per voice for every oscillator | saw < −70 dB, triangle < −85 dB alias below 10 kHz at C7 / C8 |
| echo | `gen_echo.py` | stereo tape loop: one time, re-read D early (the loop's own delay); LP / HP / diffusion / saturator in the loop; glide limited to 0.5 ms per ms; wow and flutter as pitch; Stop; rounds for a display | repeats ±1 ms of n T; read speed in [0.5, 1.5]; over unity it howls, held under 1 / saturation; under, it dies; wow / flutter RMS cents as set, the same at every Time; Stop empties it |

What each was chosen over, with numbers, is in its module docstring.

# 2sl-dsp: the partitions and their patterns

2sl-dsp is the 2sl kit: the shared code that builds a Max for Live device from Python, consumed by each device's own
repository as a git submodule (device-repository.md). It holds no device.

| partition | what it is | the pattern |
|---|---|---|
| `twosl_dsp/` | the build library (Python 3.9+, standard library + libduktape; a C compiler for rendering gen~ code in tests) | one module per concern (below); every failure is a `BuildError` saying what is wrong and where to fix it; nothing is written until every check has passed; every byte written depends only on the inputs |
| `twosl_dsp/techniques/` | gen blocks, layer 1: DSP techniques with no circuit identity (dsp-blocks.md) | `Technique` subclasses; import only gen_blocks, build_error, generated_scripts, generated_numbers, other techniques; each cites its references/dsp.md section; claims in tests/test_techniques.py |
| `twosl_dsp/circuit_modules/` | gen blocks, layer 2: one modelled piece of hardware per file (dsp-blocks.md) | one `CircuitModule` a file: inputs the circuit's controls in its units, character a frozen dataclass of numbers, cites its references/circuits/ file; built from techniques |
| `templates/` | the ES5 scripts every device gets (UI, views), the blocks a device includes (transport clock, seeded sequence and seeded random, chord block, chord display, stored table), the gen blocks' display responses and the Cozette glyphs | ES5 only (Max's [js]); each place the build fills is a `/*MARKER*/` filled by `fill_template`; at run time every surprise is an `error(DEVICE_NAME + ": ...")` in the Max window, never a silent fallback |
| `tools/` | command-line tools | a thin CLI over `twosl_dsp` (amxd.py, es5check.py), or a standalone tool that must not depend on the kit's code: `compare_device_builds.py` (compares any two builds, old kit or new), `bdf2js.py` (makes templates/cozette-glyphs.js), `max_sandbox.js` (node sandbox with Max's [js] globals, for script tests); `match_patch.py` (the patch matcher's CLI, patch-matcher.md); `render_pages.py` (a built device's pages and group choices as PNGs at the device's size, plus layout.txt: every box's x / width / gap by band and its breaks of the layout contract; each display's first-paint text; fails on the overlap rule or a control with no text) |
| `tests/` | the kit's tests | `python3 -m unittest discover -s tests`; built on the fixture device (tests/fixture_device.py) in temporary repositories; node script tests run from a Python test that fails when node is missing; a build compared byte for byte, two renders by `render_comparison` (testing.md) |
| `references/` | sources (Max, Live, Live presets, DSP techniques in dsp.md, circuits in circuits/) | links and quotes; the code cites them by section. The Live preset example is also the template the preset writer copies. Papers and datasheets aren't kept: a fetch script per set downloads and checks them (`fetch-dsp-sources.sh`, `circuits/fetch-circuit-sources.sh`) |
| `architecture/` | this | the partitions and the contracts below |

## twosl_dsp/, module by module

| module | concern |
|---|---|
| `device_repository.py` | `DeviceRepository`: where a device's sources are and where its build writes; refuses writes inside the kit |
| `patch_builder.py` | `DevicePatchBuilder`: the patch, box by box, and every check of it (`check(layout)`; with the scripts, `check_script_messages_into_gen` and `check_display_texts`). Every message sent straight into a gen~ names a Param it declares: a [prepend X] or message box wired into it (`check_messages_into_gen_name_params`), a script's `outlet(N, ...)` from an outlet wired into it (a literal, or a `+` chain a Param matches; a block's outlet the text can't say is told with `script_outlet_of_block`) |
| `max_time_values.py` | Max's note values (`MAX_NOTE_VALUE_TICKS`, references/README.md "Time value syntax") and the check every [metro] / [delay] / [pipe] / ... box's text passes as it is made (`box`): a token shaped like a note value (`64nt`) must be one |
| `script_outlet_calls.py` | an ES5 script's `outlet(index, message, ...)` calls read from its text (tokenized, not run): each call's outlet and its message name as a pattern; what `check_script_messages_into_gen` holds to a gen~'s Params |
| `layout_rules.py` | the 2sl layout contract (169 px, the bands, the header), the overlap rule (what every box and chrome text draws, and no two drawn at once overlapping; no display's texts overlapping), and how wide a control must be for its text (live.dial / live.menu / live.text / live.tab text in Live's font, measured per character by a stand-in, with padding) |
| `display_text.py` | the text each display draws, first painted and driven through its inputs to its widest: the views script run in Duktape (es5.py) with Max's jsui globals stubbed, every `text()` recorded with its glyphs' box |
| `seeded_random.py` | `SeededRandom`: the device's one random generator, its Seed and Loop controls (seeded-random.md) |
| `chord_block.py` | `ChordBlock`: chord shapes, In key, held keys, names, Drift, the chord display (chord-block.md) |
| `stored_table.py` | `StoredTable`: a table of values saved with the set and in presets as packed Stored Only parameters, not automated; its fields, its preset book form, its brain code and its Hidden editors (stored-table.md) |
| `preset_book.py` | `PresetBook`: the neutral values (each control's double-click target), the Init values and presets, in control units, checked against the controls; saved records (a stored table) and every preset's Stored Only values (`stored_only_values_of_preset`) |
| `live_preset_files.py` | the `.adv` writer (from references/ableton's example) |
| `live_parameter_identity.py` | what Live knows a parameter by, and the lock file that keeps it |
| `generated_scripts.py` | `fill_template` and the ES5 check of every generated script |
| `generated_numbers.py` | `generated_number`, the one way a computed number reaches a written file, and `check_generated_text`, the check every written file passes (below, "Generated numbers") |
| `device_build.py` | `build_device`: checks, scripts, lock, devices/, dist/ |
| `amxd.py` | .amxd bytes: unfrozen and frozen |
| `genexpr.py` | our GenExpr subset checker and renderer (not Max's compiler): the renderer translates a program to C once, builds it with the system C compiler into a cache, runs it through ctypes, and gives Python's float arithmetic bit for bit |
| `c_library_cache.py` | the one place the kit runs a C compiler: `load_c_library(c_source, flags)` builds once per source / compiler / flags into the cache, loads once; the renderer and the patch matcher's analysis both use it |
| `genexpr_export.py` | a device's gen~ code as a C file and header for a plugin (the renderer's C with the sample rate an argument, thread-local state, prefixed names, Python's noise seeding): the same bits as the renderer |
| `build_comparison.py` | two builds of a device compared as the device tests compare them: exactly (every machine writes the same bytes: `generated_numbers.py`), `.adv` by its XML (not zlib's compression), saying where two differ (`.maxpat` value by value, `.amxd` by patch, `.adv` by tag, text by character) |
| `gen_blocks.py` | the gen block pattern: `GenBlock` and its two layers' bases `Technique` and `CircuitModule`, `gen_code_with_blocks`, the shared `smoothing_coefficient` (dsp-blocks.md) |
| `techniques/`, `circuit_modules/` | the gen blocks, by layer (their own partitions, above) |
| `render_comparison.py` | `renders_are_similar` / `assert_renders_similar`: the one way a test compares two renders, by the residual's level against the reference's, whole and in 10 ms windows, with its limits (testing.md) |
| `model_accuracy.py` | `assert_matches_model`: the one way a test holds a sample sequence to its equation, a twin or a reference model, every sample within a stated tolerance and its reason (testing.md) |
| `cpu_timing.py` | `CpuTiming`: the one way a test times something: the load read first, one run on a CPU clock (a thread's, or a process's with its children's), NOT JUDGED without room (testing.md) |
| `bs1770.py` | ITU-R BS.1770-5 loudness and true peak, EBU Tech 3341's momentary loudness (references/itu-r-bs1770.md, ebu-tech-3341.md) |
| `patch_match_voice.py`, `patch_match_score.py` (+ `patch_match_features.c`), `patch_match_search.py` | the patch matcher: a voice's parameters for a target hit (render, score, CMA-ES strands), the 2sl drums' acceptance test (patch-matcher.md) |
| `wave_files.py` | WAV in (PCM 8-32 bit, float 32/64) and out (float 32), failing loudly on anything else |
| `preset_loudness.py` | the phrase every preset is measured on, its loudest moment and peak, the oscillators' start phases, each preset's controls through the device's own patch (`messages_for`), the comparison against Init: what a device's tests level its presets by; for an audio effect, the generated inputs and each preset's median gain against bypass (presets.md) |
| `es5.py` | Duktape through ctypes |
| `themes.py` | the 2sl colour tokens and `themeFromLive` |

## The kit's API, as a device build uses it

```python
from twosl_dsp.device_repository import DeviceRepository   # DeviceRepository.of_build_script(__file__)
from twosl_dsp.preset_book import PresetBook               # PresetBook.from_file(path, display_name)
from twosl_dsp.patch_builder import DevicePatchBuilder     # DevicePatchBuilder(device_name, script_name, version,
                                                         #   subtitle, link_chip_text, device_type, device_width,
                                                         #   page_names, info, preset_book, latency_samples)
                                                         # latency_samples: the Defined Latency, an int: the
                                                         #   rule's declared figure (below, "Defined Latency")
from twosl_dsp.techniques.defined_latency_pad import DefinedLatency  # DefinedLatency(device_name, {path: latency})
from twosl_dsp.live_preset_files import LivePresetFiles    # LivePresetFiles(stored_only_values_of_preset)
from twosl_dsp.generated_scripts import fill_template, kit_template_text
from twosl_dsp.device_build import build_device            # build_device(repository, patch, layout, views_code,
                                                         #   device_scripts, live_preset_files, command_line_arguments)
from twosl_dsp.seeded_random import SeededRandom           # SeededRandom(patch, brain, brain_control_inlet)
from twosl_dsp.chord_block import ChordBlock               # ChordBlock(patch, seeded_random, brain, control inlet,
                                                         #   display outlet, display box, most_notes_per_chord)
from twosl_dsp.stored_table import StoredTable, ContinuousField, ChoiceField, stored_tables_brain_code
                                                         # StoredTable(patch, name, fields, row_count, brain,
                                                         #   brain_inlet, brain_outlet); .editor_dial / _menu / _toggle
from twosl_dsp.gen_blocks import gen_code_with_blocks      # gen_code_with_blocks(template, blocks, name, replacements)
from twosl_dsp.techniques.zero_delay_ladder_filter import ZeroDelayLadderFilter   # one module per technique
from twosl_dsp.circuit_modules.ltc1060_mf10_section import Ltc1060Mf10Section     # one module per circuit
```

The builder's helpers: `box`, `wire`, `find`, `gen_box(code, ins, outs, rect, box_text, outlet_type)`, `dial`, `menu`,
`tabs` (with `rows`, `row_height`), `toggle`, `numbox` (`dial`, `menu`, `tabs` and `toggle` take `visibility`: Hidden for
a control the patch drives), `stored` (Stored Only), `saved_record` (a stored table registers itself), `view`, `derived`, `tell`, `on_page`, `group_selector`,
`groups_selected_by`, `header(output_level_target, output_level_name, preset_menu)`, `live_set_observer(property)`,
`live_transport(brain, inlet, also_tell_playing)`, `stop_action(brain, inlet, panic_destinations)`,
`turned_off_by_stop(control)`, `menu_lookup(control, values)`, `tempo_synced_milliseconds(control, beats_by_item, tempo,
message, destination)`, `messages_for(values, destination, beats_per_minute)`. See each docstring.

## Blocks: kit code a device includes

A block is a piece of a device that is the same in every device that has it, and improves in one place. Its pattern:

- **Python** (`twosl_dsp/<block>.py`): one class made with the device's patch and the boxes it wires to (the brain
  and its inlets / outlets, a display the device made). Its methods make its controls (the device places them and,
  where Live knows them by a name the device already shipped, names them) and give its code (`brain_code()`,
  `display_code()`), filled from the Init values and build-time constants. The kit owns what is the same everywhere
  (the chord shapes and their item names; Seed and Loop's names and Info text); asking for code before the controls
  it depends on, or without a block it depends on, fails the build.
- **ES5** (`templates/<block>.template.js`): functions and state with the block's prefix (`chord...`, `random...`,
  `seededRandom...`), no `anything()` of its own: the device's `anything()` passes every control message to the
  block's `...Message(name, args)`, which returns true when it took it. The device's template has a `/*MARKER*/`
  where the block's code goes, the way the transport clock goes in. A display block gives a painter the device
  calls from its `VIEW_PAINTERS` with its own label, and a `...Message` its `deviceMessage` asks first.
- **Tests**: the fixture device has every block; tests/kit-scripts.test.js runs the blocks' code as the build
  generates it, tests/test_blocks.py their build rules.

The blocks: the transport clock (templates/transport-clock.template.js), the seeded random (seeded-random.md), the
chord block (chord-block.md), the stored table (stored-table.md).

## Gen blocks: kit gen~ code a device includes, in layers

The same idea for the gen~ code (dsp-blocks.md), in three layers: techniques (`twosl_dsp/techniques/`), circuit modules
(`twosl_dsp/circuit_modules/`), and the instruments, which are the devices. A block instance is made with a name and its
inputs as GenExpr expressions; the device's gen~ template has `/*GEN_BLOCK_FUNCTIONS*/`, `/*GEN_BLOCK_DECLARATIONS*/`
and a `/*<NAME>*/` per instance, filled by `gen_code_with_blocks`. Tests: tests/test_techniques.py,
tests/test_circuit_module_*.py, and tests/test_gen_block_layers.py for the layers' rules.

## Defined Latency

Live is told a device's latency in whole samples (references/README.md, "Defined Latency"), and compensates it on
playback. The rule (ours, so no tie and no float crumb decides anything):

- **Every block reports its latency the same way**: `latency_samples`, an instance attribute in host samples
  (fractions allowed, 0 said; dsp-blocks.md, "Latency is always said"). A path's latency is the sum of its blocks'.
  A device never types a latency or reads a module constant for one.
- **The declared figure is the latest audio path rounded UP to a whole sample.** The paths are every way audio reaches
  an output: each output, each switchable alternative (a Filter Type), each voice (a kick and a hat). Figures within
  1e-9 of a whole number are that number (0.5000000000000001 + 0.5 is 1).
- **Every path is padded to exactly that figure**: `DefinedLatency(device, {path: latency})` gives
  `declared_latency_samples` and, per path, `pad(path, name, input)`: a `DefinedLatencyPad` (whole samples exact; a
  fraction through a Thiran all-pass: magnitude untouched, its phase delay within the stated bounds, dsp-blocks.md).
  `check_every_path_padded()` fails a build that left a path early.
- **`DevicePatchBuilder(latency_samples=...)` takes the declared int**, never a fraction (it would be rounded where no
  test sees it); the patcher's `"latency"` is that figure. A device's tests render each path and hold its delay to
  the declared figure.

## Generated numbers

Every machine writes the same bytes from the same sources. The one thing that varied was numbers computed through
the platform's maths library (math / cmath / `**` round the last bit differently on glibc and macOS), so the rule
(`twosl_dsp/generated_numbers.py`, which holds the measurements behind it):

- **Every computed number a build writes goes through `generated_number`, where it is computed**: a float is rounded
  to 10 significant digits (well past what any filter needs, well short of the last-bit noise); a `Fraction`, exact
  rational arithmetic and the same everywhere, is written as the nearest double with every digit (a polyBLEP's
  1/24, an antiderivative's constants, a Thiran pad's coefficients, taps scaled to sum exactly). The Python model
  keeps the number the code holds.
- **The check**: `check_generated_text` fails on a decimal literal longer than 10 significant digits that
  `generated_number` didn't write from a Fraction; `build_device` runs it on the patch and every script before
  writing, a plugin's generator on every generated file. A number the Live parameter lock
  holds passes (the lock already holds it to the byte; it can't change without changing what Live knows).
- **Hand-written code** obeys the same rule (a GenExpr constant: `pi`, `halfpi`; C: a hex literal).
- **Proof**: tests/test_generated_numbers.py builds every gen block and the fixture device with every maths-library
  result moved up to 16 units in the last place and holds every byte; `build_comparison` compares builds exactly.
  Renders are not the build: they are compared as sound, within tolerance (testing.md).

## Layout: widths from text

Two rules, both in `layout_rules.py` and checked by `DevicePatchBuilder.check(layout)`:
- a live.tab's buttons hold their longest name and 6 px (`live_tab_button_problem`);
- a live.dial holds its short name and 4 px, a live.menu its longest item, a 2 px inset and its arrow, a live.text
  its text and 8 px (`live_text_problem`), at least 44 px for a dial, 40 for a menu. A dial whose name needs more
  is made wider: `dial(..., width=live_dial_width(short))`.
  All text is measured in Live's font as a stand-in gives it: Liberation Sans at 11 px, per character
  (`LIVE_FONT_ADVANCES`, `live_text_width`), so capitals count wider. No source gives Live's font metrics; the size
  is calibrated from one case seen in Live (SHORTCUTS.md); tools/render_pages.py draws with the same font, checks the
  table against it and fails a page whose text doesn't fit. A box taller than a dial (a pad) isn't checked. `live_dial_width`, `live_menu_width`, `live_toggle_width`, `live_tabs_width` give the narrowest that
  passes, on the grid.

## Layout: nothing drawn over anything else

The overlap rule, in `layout_rules.py`, fails the build naming both things, their extents and the overlap:
- **Pages** (`drawn_overlap_problems`, run by `DevicePatchBuilder.check(layout)`): on every page and every choice
  of its group selectors, everything drawn at once: every shown box's drawn parts (`drawn_parts`: its box; a dial's
  name and widest value text, a number box's widest value, a menu's longest item, a live.text's text, each centred or
  inset as Live draws it and as wide as the stand-in measures it, so a text may reach past its box) and every text
  the chrome draws (`chrome_texts`: the page's labels and hints, the header's labels, the subtitle; Cozette, 6 px a
  character, 10 px above the baseline and 3 below). No two overlap and none reaches off the device. A value's text
  is `live_value_text`'s: a stand-in for Live's formatting (SHORTCUTS.md), the widest over the control's travel.
- **Displays** (`display_text_problems`, run by `DevicePatchBuilder.check_display_texts` on the views script): each
  display's texts don't overlap each other or leave the display, as first painted and as driven through what it can
  be sent (`display_text.py`): every value each control told it can send (`display_inputs`: an enum's items, an
  Int's values, a float at `DISPLAY_SWEEP_STEPS` steps of its travel) and every value of each reading the device
  declares (`view_reading(view_box, message, values)`: what the DSP or the brain sends it), searched for the widest
  text it can draw (each input swept in turn, kept at the widest; again with each value of each switch held), every
  distinct paint on the way checked. A failure names what the display had been sent. A reading not declared isn't
  driven: a device declares every reading that changes a display's text.
- **The kit draws what every device draws the same way**: the header's subtitle goes where `layout_rules.subtitle_x`
  says (a header gap after the page tabs, or after the Preset menu); a device's layout doesn't place it. Every
  display's heading is the views template's `viewHeading(name, reading, w, colour)`: the name top left, the reading
  right-aligned on the same line while both fit (two spaces between), else on the next line; it returns the y the
  display's drawing starts at, so a reading that drops a line takes that line from the drawing, never overlapping it.
- **Exempt by kind, never by name**: a background box (Max's "Include in Background": the chrome, which everything
  sits on); a part never counts against another part of its own box. There is no per-device allowlist.
- tools/render_pages.py runs the same two rules on what the build wrote (the displays as first painted: driving them
  needs the build's routes), and draws the displays' first-paint text.

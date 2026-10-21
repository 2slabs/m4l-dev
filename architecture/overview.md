# m4l-dev: the partitions and their patterns

m4l-dev is the 2sl kit: the shared code that builds a Max for Live device from Python, consumed by each device's own
repository as a git submodule (device-repository.md). It holds no device.

| partition | what it is | the pattern |
|---|---|---|
| `m4l_dev/` | the build library (Python 3.9+, standard library + libduktape; a C compiler for rendering gen~ code in tests) | one module per concern (below); every failure is a `BuildError` saying what is wrong and where to fix it; nothing is written until every check has passed; every byte written depends only on the inputs |
| `m4l_dev/techniques/` | gen blocks, layer 1: DSP techniques with no circuit identity (dsp-blocks.md) | `Technique` subclasses; import only gen_blocks, build_error, generated_scripts, other techniques; each cites its references/dsp.md section; claims in tests/test_techniques.py |
| `m4l_dev/circuit_modules/` | gen blocks, layer 2: one modelled piece of hardware per file (dsp-blocks.md) | one `CircuitModule` a file: inputs the circuit's controls in its units, character a frozen dataclass of numbers, cites its references/circuits/ file; built from techniques |
| `templates/` | the ES5 scripts every device gets (UI, views), the blocks a device includes (transport clock, seeded sequence and seeded random, chord block, chord display, stored table), the gen blocks' display responses and the Cozette glyphs | ES5 only (Max's [js]); each place the build fills is a `/*MARKER*/` filled by `fill_template`; at run time every surprise is an `error(DEVICE_NAME + ": ...")` in the Max window, never a silent fallback |
| `plugin/cpp/` | ([plugins.md](plugins.md): the approach a port follows) the C++ every 2sl plugin shares (no JUCE except MaxScript): `PluginTable.h` (the generated header's types; a route's value), `GenProgram.h` (one running copy of an exported gen~ program: Params, state, render), `MaxScript.h/.cpp` (a device's [js] brain run unchanged in JUCE's JavascriptEngine, QuickJS, with the Max globals it uses and a Task clock the plugin moves) | the generated header fills in the tables; a plugin's own wrapper connects the parts the way the device's Max objects do |
| `tools/` | command-line tools | a thin CLI over `m4l_dev` (amxd.py, es5check.py), or a standalone tool that must not depend on the kit's code: `compare_device_builds.py` (compares any two builds, old kit or new), `bdf2js.py` (makes templates/cozette-glyphs.js), `max_sandbox.js` (node sandbox with Max's [js] globals, for script tests); `match_patch.py` (the patch matcher's CLI, patch-matcher.md); `render_pages.py` (a built device's pages and group choices as PNGs at the device's size, plus layout.txt: every box's x / width / gap by band and its breaks of the layout contract; fails on the overlap check, a control with no text or a chrome label in a box) |
| `tests/` | the kit's tests | `python3 -m unittest discover -s tests`; built on the fixture device (tests/fixture_device.py) in temporary repositories; node script tests run from a Python test that fails when node is missing |
| `references/` | sources (Max, Live, Live presets, DSP techniques in dsp.md, circuits in circuits/) | links and quotes; the code cites them by section. The Live preset example is also the template the preset writer copies. Papers and datasheets aren't kept: a fetch script per set downloads and checks them (`fetch-dsp-sources.sh`, `circuits/fetch-circuit-sources.sh`) |
| `architecture/` | this | the partitions and the contracts below |

## m4l_dev/, module by module

| module | concern |
|---|---|
| `device_repository.py` | `DeviceRepository`: where a device's sources are and where its build writes; refuses writes inside the kit |
| `patch_builder.py` | `DevicePatchBuilder`: the patch, box by box, and every check of it (`check()`) |
| `layout_rules.py` | the 2sl layout contract (169 px, the bands, the header), the overlap check, and how wide a control must be for its text (live.dial / live.menu / live.text / live.tab text in Live's font, measured per character by a stand-in, with padding) |
| `seeded_random.py` | `SeededRandom`: the device's one random generator, its Seed and Loop controls (seeded-random.md) |
| `chord_block.py` | `ChordBlock`: chord shapes, In key, held keys, names, Drift, the chord display (chord-block.md) |
| `stored_table.py` | `StoredTable`: a table of values saved with the set and in presets as packed Stored Only parameters, not automated; its fields, its preset book form, its brain code and its Hidden editors (stored-table.md) |
| `preset_book.py` | `PresetBook`: the Init values and presets, in control units, checked against the controls; saved records (a stored table) and every preset's Stored Only values (`stored_only_values_of_preset`) |
| `live_preset_files.py` | the `.adv` writer (from references/ableton's example) |
| `live_parameter_identity.py` | what Live knows a parameter by, and the lock file that keeps it |
| `generated_scripts.py` | `fill_template` and the ES5 check of every generated script |
| `device_build.py` | `build_device`: checks, scripts, lock, devices/, dist/ |
| `amxd.py` | .amxd bytes: unfrozen and frozen |
| `genexpr.py` | our GenExpr subset checker and renderer (not Max's compiler): the renderer translates a program to C once, builds it with the system C compiler into a cache, runs it through ctypes, and gives Python's float arithmetic bit for bit |
| `c_library_cache.py` | the one place the kit runs a C compiler: `load_c_library(c_source, flags)` builds once per source / compiler / flags into the cache, loads once; the renderer and the patch matcher's analysis both use it |
| `genexpr_export.py` | a device's gen~ code as a C file and header for a plugin (the renderer's C with the sample rate an argument, thread-local state, prefixed names, Python's noise seeding): the same bits as the renderer |
| `build_comparison.py` | two builds of a device compared as the device tests compare them: everything exactly, except numbers, which only have to be close (maths libraries round the last digits differently between machines); `.amxd` by patch, `.adv` by XML (bar the device file's size and checksum), strings' numbers as numbers |
| `plugin/parameters.py` | a device's host parameters for its plugin, read off its patch: the Live parameter lock for what the host knows them by, the patch's routes (`messages_for`, its tempo routes) for how each reaches the device's gen~ programs, script (brain) and raw boxes; Stored Only values as the plugin's state; presets as held, with their Stored values |
| `plugin/header.py` | the plugin's generated C++ header from those: parameters, routes, Stored values, presets, latency, each exported gen~ program as a `ProgramSpec` |
| `plugin/vstpreset.py` | VST3 presets (.vstpreset) the way Live saves them: JUCE's class id from the plugin codes, JUCE's state XML and private data, Live's meta info; rebuilds a preset Live saved byte for byte |
| `plugin/generated_files.py` | a plugin's generated folder: written from the device's sources, or checked to be what they make |
| `gen_blocks.py` | the gen block pattern: `GenBlock` and its two layers' bases `Technique` and `CircuitModule`, `gen_code_with_blocks`, the shared `smoothing_coefficient` (dsp-blocks.md) |
| `techniques/`, `circuit_modules/` | the gen blocks, by layer (their own partitions, above) |
| `bs1770.py` | ITU-R BS.1770-5 loudness and true peak, EBU Tech 3341's momentary loudness (references/itu-r-bs1770.md, ebu-tech-3341.md) |
| `patch_match_voice.py`, `patch_match_score.py` (+ `patch_match_features.c`), `patch_match_search.py` | the patch matcher: a voice's parameters for a target hit (render, score, CMA-ES strands), the 2sl drums' acceptance test (patch-matcher.md) |
| `wave_files.py` | WAV in (PCM 8-32 bit, float 32/64) and out (float 32), failing loudly on anything else |
| `preset_loudness.py` | the phrase every preset is measured on, its loudest moment and peak, the oscillators' start phases, each preset's controls through the device's own patch (`messages_for`), the comparison against Init: what a device's tests level its presets by; for an audio effect, the generated inputs and each preset's median gain against bypass (presets.md) |
| `es5.py` | Duktape through ctypes |
| `themes.py` | the 2sl colour tokens and `themeFromLive` |

## The kit's API, as a device build uses it

```python
from m4l_dev.device_repository import DeviceRepository   # DeviceRepository.of_build_script(__file__)
from m4l_dev.preset_book import PresetBook               # PresetBook.from_file(path, display_name)
from m4l_dev.patch_builder import DevicePatchBuilder     # DevicePatchBuilder(device_name, script_name, version,
                                                         #   subtitle, link_chip_text, device_type, device_width,
                                                         #   page_names, info, preset_book, latency_samples)
                                                         # latency_samples: the Defined Latency, an int: the
                                                         #   rule's declared figure (below, "Defined Latency")
from m4l_dev.techniques.defined_latency_pad import DefinedLatency  # DefinedLatency(device_name, {path: latency})
from m4l_dev.live_preset_files import LivePresetFiles    # LivePresetFiles(stored_only_values_of_preset)
from m4l_dev.generated_scripts import fill_template, kit_template_text
from m4l_dev.device_build import build_device            # build_device(repository, patch, layout, views_code,
                                                         #   device_scripts, live_preset_files, command_line_arguments)
from m4l_dev.seeded_random import SeededRandom           # SeededRandom(patch, brain, brain_control_inlet)
from m4l_dev.chord_block import ChordBlock               # ChordBlock(patch, seeded_random, brain, control inlet,
                                                         #   display outlet, display box, most_notes_per_chord)
from m4l_dev.stored_table import StoredTable, ContinuousField, ChoiceField, stored_tables_brain_code
                                                         # StoredTable(patch, name, fields, row_count, brain,
                                                         #   brain_inlet, brain_outlet); .editor_dial / _menu / _toggle
from m4l_dev.gen_blocks import gen_code_with_blocks      # gen_code_with_blocks(template, blocks, name, replacements)
from m4l_dev.techniques.zero_delay_ladder_filter import ZeroDelayLadderFilter   # one module per technique
from m4l_dev.circuit_modules.ltc1060_mf10_section import Ltc1060Mf10Section     # one module per circuit
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

- **Python** (`m4l_dev/<block>.py`): one class made with the device's patch and the boxes it wires to (the brain
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

The same idea for the gen~ code (dsp-blocks.md), in three layers: techniques (`m4l_dev/techniques/`), circuit modules
(`m4l_dev/circuit_modules/`), and the instruments, which are the devices. A block instance is made with a name and its
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

## Layout: widths from text

Two rules, both in `layout_rules.py` and checked by `DevicePatchBuilder.check()`:
- a live.tab's buttons hold their longest name and 6 px (`live_tab_button_problem`);
- a live.dial holds its short name and 4 px, a live.menu its longest item, a 2 px inset and its arrow, a live.text
  its text and 8 px (`live_text_problem`), at least 44 px for a dial, 40 for a menu. A dial whose name needs more
  is made wider: `dial(..., width=live_dial_width(short))`.
  All text is measured in Live's font as a stand-in gives it: Liberation Sans at 11 px, per character
  (`LIVE_FONT_ADVANCES`, `live_text_width`), so capitals count wider. No source gives Live's font metrics; the size
  is calibrated from one case seen in Live (SHORTCUTS.md); tools/render_pages.py draws with the same font, checks the
  table against it and fails a page whose text doesn't fit. A box taller than a dial (a pad) isn't checked. `live_dial_width`, `live_menu_width`, `live_toggle_width`, `live_tabs_width` give the narrowest that
  passes, on the grid.

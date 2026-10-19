# m4l-dev: the partitions and their patterns

m4l-dev is the 2sl kit: the shared code that builds a Max for Live device from Python, consumed by each device's own
repository as a git submodule (device-repository.md). It holds no device.

| partition | what it is | the pattern |
|---|---|---|
| `m4l_dev/` | the build library (Python 3.9+, standard library + libduktape; a C compiler for rendering gen~ code in tests) | one module per concern (below); every failure is a `BuildError` saying what is wrong and where to fix it; nothing is written until every check has passed; every byte written depends only on the inputs |
| `templates/` | the ES5 scripts every device gets (UI, views), the blocks a device includes (transport clock, seeded sequence and seeded random, chord block, chord display) and the Cozette glyphs | ES5 only (Max's [js]); each place the build fills is a `/*MARKER*/` filled by `fill_template`; at run time every surprise is an `error(DEVICE_NAME + ": ...")` in the Max window, never a silent fallback |
| `tools/` | command-line tools | a thin CLI over `m4l_dev` (amxd.py, es5check.py), or a standalone tool that must not depend on the kit's code: `compare_device_builds.py` (compares any two builds, old kit or new), `bdf2js.py` (makes templates/cozette-glyphs.js), `max_sandbox.js` (node sandbox with Max's [js] globals, for script tests) |
| `tests/` | the kit's tests | `python3 -m unittest discover -s tests`; built on the fixture device (tests/fixture_device.py) in temporary repositories; node script tests run from a Python test that fails when node is missing |
| `references/` | sources (Max, Live, Live presets, DSP) | links and quotes; the code cites them by section. The Live preset example is also the template the preset writer copies. Papers aren't kept: a fetch script per set downloads and checks them (`fetch-dsp-sources.sh`) |
| `architecture/` | this | the partitions and the contracts below |

## m4l_dev/, module by module

| module | concern |
|---|---|
| `device_repository.py` | `DeviceRepository`: where a device's sources are and where its build writes; refuses writes inside the kit |
| `patch_builder.py` | `DevicePatchBuilder`: the patch, box by box, and every check of it (`check()`) |
| `layout_rules.py` | the 2sl layout contract (169 px, the bands, the header), the overlap check, and how wide a control must be for its text (live.tab buttons in Cozette; live.dial / live.menu / live.text in Live's font, 5.5 px a character) |
| `seeded_random.py` | `SeededRandom`: the device's one random generator, its Seed and Loop controls (seeded-random.md) |
| `chord_block.py` | `ChordBlock`: chord shapes, In key, held keys, names, Drift, the chord display (chord-block.md) |
| `preset_book.py` | `PresetBook`: the Init values and presets, in control units, checked against the controls |
| `live_preset_files.py` | the `.adv` writer (from references/ableton's example) |
| `live_parameter_identity.py` | what Live knows a parameter by, and the lock file that keeps it |
| `generated_scripts.py` | `fill_template` and the ES5 check of every generated script |
| `device_build.py` | `build_device`: checks, scripts, lock, devices/, dist/ |
| `amxd.py` | .amxd bytes: unfrozen and frozen |
| `genexpr.py` | our GenExpr subset checker and renderer (not Max's compiler): the renderer translates a program to C once, builds it with the system C compiler into a cache, runs it through ctypes, and gives Python's float arithmetic bit for bit |
| `genexpr_export.py` | a device's gen~ code as a C file and header for a plugin (the renderer's C with the sample rate an argument, thread-local state, prefixed names, Python's noise seeding): the same bits as the renderer |
| `gen_blocks.py` | the DSP block pattern: `GenBlock`, `gen_code_with_blocks`, the shared `smoothing_coefficient` (dsp-blocks.md) |
| `gen_ladder.py`, `gen_saturator.py`, `gen_soft_clip.py`, `gen_edges.py`, `gen_echo.py` | the DSP blocks: ladder filter, antialiased tanh, output soft clip, band-limited edges, tape echo (dsp-blocks.md) |
| `bs1770.py` | ITU-R BS.1770-5 loudness and true peak, EBU Tech 3341's momentary loudness (references/itu-r-bs1770.md, ebu-tech-3341.md) |
| `preset_loudness.py` | the phrase every preset is measured on, its loudest moment and peak, the oscillators' start phases, each preset's controls through the device's own patch (`messages_for`), the comparison against Init: what a device's tests level its presets by; for an audio effect, the generated inputs and each preset's median gain against bypass (presets.md) |
| `es5.py` | Duktape through ctypes |
| `themes.py` | the 2sl colour tokens and `themeFromLive` |

## The kit's API, as a device build uses it

```python
from m4l_dev.device_repository import DeviceRepository   # DeviceRepository.of_build_script(__file__)
from m4l_dev.preset_book import PresetBook               # PresetBook.from_file(path, display_name)
from m4l_dev.patch_builder import DevicePatchBuilder     # DevicePatchBuilder(device_name, script_name, version,
                                                         #   subtitle, link_chip_text, device_type, device_width,
                                                         #   page_names, info, preset_book)
from m4l_dev.live_preset_files import LivePresetFiles    # LivePresetFiles(stored_only_values_of_preset)
from m4l_dev.generated_scripts import fill_template, kit_template_text
from m4l_dev.device_build import build_device            # build_device(repository, patch, layout, views_code,
                                                         #   device_scripts, live_preset_files, command_line_arguments)
from m4l_dev.seeded_random import SeededRandom           # SeededRandom(patch, brain, brain_control_inlet)
from m4l_dev.chord_block import ChordBlock               # ChordBlock(patch, seeded_random, brain, control inlet,
                                                         #   display outlet, display box, most_notes_per_chord)
from m4l_dev.gen_blocks import gen_code_with_blocks      # gen_code_with_blocks(template, blocks, name, replacements)
from m4l_dev.gen_ladder import LadderFilter              # and AntiderivativeTanhSaturator, BandLimitedEdges,
                                                         #   OutputSoftClip, TapeEcho (gen_saturator, gen_soft_clip, gen_edges, gen_echo)
```

The builder's helpers: `box`, `wire`, `find`, `gen_box(code, ins, outs, rect, box_text, outlet_type)`, `dial`, `menu`,
`tabs` (with `visibility`), `toggle`, `numbox`, `stored` (Stored Only), `view`, `derived`, `tell`, `on_page`, `group_selector`,
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
chord block (chord-block.md).

## DSP blocks: kit gen~ code a device includes

The same idea for the gen~ code (dsp-blocks.md): `m4l_dev/gen_<block>.py` makes an instance with a name and its
inputs as GenExpr expressions; the device's gen~ template has `/*GEN_BLOCK_FUNCTIONS*/`, `/*GEN_BLOCK_DECLARATIONS*/`
and a `/*<NAME>*/` per instance, filled by `gen_code_with_blocks`. The ladder, the saturator, the output soft clip,
band-limited edges, the tape echo. Tests: tests/test_dsp_blocks.py.

## Layout: widths from text

Two rules, both in `layout_rules.py` and checked by `DevicePatchBuilder.check()`:
- a live.tab's buttons hold their longest item in Cozette (`live_tab_button_problem`, 6 px a character + 1);
- a live.dial holds its short name, a live.menu its longest item and arrow, a live.text its text, in Live's own font
  (`live_text_problem`): 5.5 px a character, at least 44 px for a dial, 40 for a menu. No source gives Live's font
  metrics; 5.5 is calibrated from one case seen in Live (SHORTCUTS.md). A box taller than a dial (a pad) isn't
  checked. `live_dial_width`, `live_menu_width`, `live_toggle_width`, `live_tabs_width` give the narrowest that
  passes, on the grid.

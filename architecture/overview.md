# m4l-dev: the partitions and their patterns

m4l-dev is the 2sl kit: the shared code that builds a Max for Live device from Python, consumed by each device's own
repository as a git submodule (device-repository.md). It holds no device.

| partition | what it is | the pattern |
|---|---|---|
| `m4l_dev/` | the build library (Python 3.9+, standard library + libduktape) | one module per concern (below); every failure is a `BuildError` saying what is wrong and where to fix it; nothing is written until every check has passed; every byte written depends only on the inputs |
| `templates/` | the ES5 scripts every device gets (UI, views, transport clock) and the Cozette glyphs | ES5 only (Max's [js]); each place the build fills is a `/*MARKER*/` filled by `fill_template`; at run time every surprise is an `error(DEVICE_NAME + ": ...")` in the Max window, never a silent fallback |
| `tools/` | command-line tools | a thin CLI over `m4l_dev` (amxd.py, es5check.py), or a standalone tool that must not depend on the kit's code: `compare_device_builds.py` (compares any two builds, old kit or new), `bdf2js.py` (makes templates/cozette-glyphs.js), `max_sandbox.js` (node sandbox with Max's [js] globals, for script tests) |
| `tests/` | the kit's tests | `python3 -m unittest discover -s tests`; built on the fixture device (tests/fixture_device.py) in temporary repositories; node script tests run from a Python test that fails when node is missing |
| `references/` | sources (Max, Live, Live presets) | links and quotes; the code cites them by section. The Live preset example is also the template the preset writer copies |
| `architecture/` | this | the partitions and the contracts below |

Transitional, not part of the kit (2026-10-16): `src/`, `devices/`, `PLANS/`, `references/drums/`, `fader-curve.tsv`,
`tools/render_drums.py`, `tools/drums_hits.js`, `tests/2sl-drums.test.js` hold 2sl drums, 2sl meter, hello-gain and the
fader calibration, until they move to their own repositories. They no longer build here (SHORTCUTS.md).

## m4l_dev/, module by module

| module | concern |
|---|---|
| `device_repository.py` | `DeviceRepository`: where a device's sources are and where its build writes; refuses writes inside the kit |
| `patch_builder.py` | `DevicePatchBuilder`: the patch, box by box, and every check of it (`check()`) |
| `layout_rules.py` | the 2sl layout contract (169 px, the bands, the header) and the overlap / live.tab checks |
| `preset_book.py` | `PresetBook`: the Init values and presets, in control units, checked against the controls |
| `live_preset_files.py` | the `.adv` writer (from references/ableton's example) |
| `live_parameter_identity.py` | what Live knows a parameter by, and the lock file that keeps it |
| `generated_scripts.py` | `fill_template` and the ES5 check of every generated script |
| `device_build.py` | `build_device`: checks, scripts, lock, devices/, dist/ |
| `amxd.py` | .amxd bytes: unfrozen and frozen |
| `genexpr.py` | our GenExpr subset checker and renderer (not Max's compiler) |
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
```

The builder's helpers: `box`, `wire`, `find`, `gen_box(code, ins, outs, rect, box_text, outlet_type)`, `dial`, `menu`,
`tabs`, `toggle`, `numbox`, `stored` (Stored Only), `view`, `derived`, `tell`, `on_page`, `group_selector`,
`groups_selected_by`, `header(volume_target, preset_menu)`, `live_set_observer(property)`,
`live_transport(brain, inlet, also_tell_playing)`, `stop_action(brain, inlet, panic_destinations)`,
`turned_off_by_stop(control)`, `messages_for(values, destination)`. See each docstring.

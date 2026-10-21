# m4l-dev

The 2sl kit for building Max for Live devices from Python: a device's patch is generated box by box, checked
(layout, Init values and presets, gen~ code, ES5 scripts, what Live knows each parameter by), and written as the
development device, Live presets, and a frozen single-file release. Used by [2sl stab](https://github.com/2slabs/2sl-stab).
A [2sl](https://2sl.to) project.

Live 12 Suite with its bundled Max 9.1.5. Python 3.9 or later (standard library only), Duktape for the ES5 check
(`brew install duktape`, or `apt install libduktape207`), node for the script tests, a C compiler (`cc`: Xcode's
command line tools, or `apt install gcc`) for the DSP tests (m4l_dev/genexpr.py builds each gen~ program to render it).
Pillow for `tools/render_pages.py` and the tests (`brew install pillow`, or `pip install -r requirements-test.txt`).
Building a device needs none of it beyond Python itself.

## Use it in a device repository

    git submodule add https://github.com/2slabs/m4l-dev.git m4l-dev

and give the repository a `build.py`, a `src/` and the rest of the layout in
[architecture/device-repository.md](architecture/device-repository.md). A minimal `build.py`:

```python
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(ROOT, "m4l-dev"), os.path.join(ROOT, "src")]
from m4l_dev.device_repository import DeviceRepository
import my_device                       # src/my_device.py: builds a DevicePatchBuilder, calls build_device
my_device.build(DeviceRepository.of_build_script(__file__), sys.argv[1:])
```

2sl stab's `src/stab_device.py` is the worked example.

## What's here

- `m4l_dev/`: the library ([architecture/overview.md](architecture/overview.md) lists each module), with the gen~ DSP
  blocks a device's audio code includes: ladder, saturator, band-limited edges, tape echo
  ([architecture/dsp-blocks.md](architecture/dsp-blocks.md)).
- `templates/`: the UI and views scripts every device gets, the blocks a device includes (the transport clock, the
  seeded random, the chord block and its display, the ladder's response for a filter display), and the Cozette glyphs
  (Cozette, MIT: `templates/LICENSE-Cozette.txt`).
- `tools/`: `amxd.py` (pack / freeze / unpack / list .amxd files), `es5check.py`, `compare_device_builds.py` (compare
  two builds of a device; exit 0 when what Live sees is the same), `bdf2js.py` (Cozette's BDF to glyphs),
  `max_sandbox.js` (Max's [js] globals for node tests), `render_pages.py` (a built device's pages as PNGs + layout facts;
  needs Pillow).
- `references/`: the sources the kit follows (Max, Live, Live's preset format, the techniques' papers: `dsp.md`; circuits' datasheets: `circuits/`).
- `m4l_dev/plugin/` and `plugin/cpp/`: a device as a VST3 plugin (JUCE), the pieces every port shares: its host
  parameters and presets from the device's patch, its gen~ programs as C, its `[js]` brain run unchanged.
  [architecture/plugins.md](architecture/plugins.md) is the approach and what the first ports taught: read it before
  starting another.
- `architecture/`: how the kit is partitioned and the contracts a device repository keeps.

## Tests

    python3 -m unittest discover -s tests

## Working on a device in Max

Drop the development device (`devices/<name>/<name>.amxd` in the device repository) on a track; it finds its scripts
next to it. Edit the Python, not the patch: the build overwrites the patch. Only `live.*` objects with
`parameter_enable` are Live parameters. Useful: the Max for Live Production Guidelines
(github.com/Ableton/maxdevtools), the Live Object Model docs (Max: Help > Reference > "Live Object Model").

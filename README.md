# m4l-dev

The 2sl kit for building Max for Live devices from Python: a device's patch is generated box by box, checked
(layout, Init values and presets, gen~ code, ES5 scripts, what Live knows each parameter by), and written as the
development device, Live presets, and a frozen single-file release. Used by [2sl stab](https://github.com/2slabs/2sl-stab).
A [2sl](https://2sl.to) project.

Live 12 Suite with its bundled Max 9.1.5. Python 3.9 or later (standard library only), Duktape for the ES5 check
(`brew install duktape`, or `apt install libduktape207`), node for the script tests.

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

- `m4l_dev/`: the library ([architecture/overview.md](architecture/overview.md) lists each module).
- `templates/`: the UI, views and transport-clock scripts every device gets, and the Cozette glyphs
  (Cozette, MIT: `templates/LICENSE-Cozette.txt`).
- `tools/`: `amxd.py` (pack / freeze / unpack / list .amxd files), `es5check.py`, `compare_device_builds.py` (compare
  two builds of a device; exit 0 when what Live sees is the same), `bdf2js.py` (Cozette's BDF to glyphs),
  `max_sandbox.js` (Max's [js] globals for node tests).
- `references/`: the sources the kit follows (Max, Live, Live's preset format).
- `architecture/`: how the kit is partitioned and the contracts a device repository keeps.

## Tests

    python3 -m unittest discover -s tests

## Working on a device in Max

Drop the development device (`devices/<name>/<name>.amxd` in the device repository) on a track; it finds its scripts
next to it. Edit the Python, not the patch: the build overwrites the patch. Only `live.*` objects with
`parameter_enable` are Live parameters. Useful: the Max for Live Production Guidelines
(github.com/Ableton/maxdevtools), the Live Object Model docs (Max: Help > Reference > "Live Object Model").

# Presets: one preset book, two outputs

A device keeps its Init values and its presets in one JSON file, its preset book (`m4l_dev/preset_book.py`):

```json
{"init": {"Cutoff": 700, "Chord": "minor", "In Key": "on", "Volume": 0},
 "presets": [{"name": "init", "group": "init", "idea": "the defaults", "values": {}},
             {"name": "chain stab", "group": "dub", "idea": "what it is for", "values": {"Cutoff": 650}}]}
```

Values are in each control's own units: a dial's or number box's number, a menu's or tab's item name, a toggle's
`off` / `on`. Every control the presets set has an Init value (it is the control's initial value in the patch, the
gen~ Param default it must match, and the displays' starting value); a control given `initial_outside_presets` has
none and presets leave it alone. The build fails on an unknown control, a missing Init value, a value out of range or
not an item, and a preset name used twice.

The same book makes either or both outputs:

- **Live preset files** (`.adv`, `m4l_dev/live_preset_files.py`), when the device passes `LivePresetFiles(...)` to
  `build_device`: one file per preset next to the development device and next to the frozen release, named
  `<group> - <name>.adv` (`<name>.adv` for the group `init`), each made for that exact device file (its name, size and
  CRC). Stored Only parameters go in the preset's blob: the device's `stored_only_values_of_preset(values)` gives them
  (2sl stab: the Pattern's steps). Known forms only (float and enum parameters, a Max Instrument or a Max Audio Effect): an Int parameter or
  another device type fails the build until a file Live wrote shows its form.
- **A Preset menu** (`header(..., preset_menu=(x, width))`): a live.menu in the header listing the presets; the UI
  script sets every saved control from the chosen preset (ignored until the device is ready, so a set's saved
  values win when Live reopens it).

A preset book with presets and neither output is legal: the presets are then only checked. Stale `.adv` files (no
preset of that name) are removed from devices/ with a line in the build's log.

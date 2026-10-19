# References

Sources the kit follows: Max, Max for Live and Live. Links and what they say; the pages themselves are not mirrored
here. A device's own sources (its sound, its DSP's sizing) are in its repository's references/. The kit's code cites
these by section; the examples are 2sl stab's, where each rule was first found.

## Max and Live APIs

- **Max JS global methods** (Max 7 vignette, still the current text):
  https://docs.cycling74.com/max7/vignettes/jsglobal
  `error()` "Sends a red tinged message to the Max window"; `post()` "Prints a representation of the
  arguments in the Max window". The device's loud failures use `error()`; notices use `post()`.
- **transport** (Max reference): https://docs.cycling74.com/reference/transport
  Outlets on a bang ("Report current state"): bar, beat, units, resolution, tempo, time signature,
  state, and the 8th: "the number of raw ticks". In Max for Live it follows Live's transport.
  The machine reads the raw ticks: the song position, independent of the time signature.
- **Time value syntax** (Max user guide): https://docs.cycling74.com/userguide/time_value_syntax/
  "one tick is 1/480 of a quarter note (equivalently, there are 480 ticks in one quarter note)".
  So a 16th is 120 ticks.
- **metro** (Max reference): https://docs.cycling74.com/reference/metro
  "Any number other than 0 starts the metro object"; a bang "is sent immediately when metro is started"
  (the machine's clock must not play that bang twice); `quantize`: "Send output only on the specified
  time-boundary". "In Max for Live, the default is the Live transport."
- **Max message order** (Max 8 tutorial 5, "Message Order and Debugging"):
  https://docs.cycling74.com/max8/tutorials/basicchapter05
  One outlet to several inlets: "Right-to-left, or bottom-to-top for objects that are vertically aligned",
  by "the location of the connected inlet"; multi-outlet objects output "from the right-most outlet to the
  left-most". **trigger** (https://docs.cycling74.com/reference/trigger): "Outputs any input received in
  order from right to left". So where order matters the patch uses a `t`, never layout.
- **Live Object Model, Song** (fetched in LPX_Script/references/live-lom-song.md from
  https://docs.cycling74.com/apiref/lom/song/): `tempo` "Current tempo of the Live Set in BPM, 20.0 ... 999.0";
  `current_song_time` "The playing position in the Live Set, in beats."
- **Parameter Mode** (Max user guide): https://docs.cycling74.com/userguide/parameter_mode/
  Initial Enable: "If enabled, the parameter will be set to an initial value when the patcher or device is
  loaded." Initial Value: "The object will restore this value when the patcher loads, as well as sending
  this value to any connected objects." The build sets every control's initial value from the Init
  values (the device's preset book: m4l_dev/preset_book.py), and checks the gen~ Params and starts the displays there.
- **Parameter Visibility** (Max user guide, Parameter Mode; and the live.tab / live.dial references:
  https://docs.cycling74.com/reference/live.tab): "Stored Only: Use for parameters that are part of the device's
  persistent state but should not be automated or exposed to control surfaces." "Hidden: ... Not stored in the Live
  Set or presets, not visible to control surfaces, and not recorded in Live's undo history." live.tab: "'Hidden'
  causes the parameter's value to be ignored when storing and recalling data." The Max for Live Production
  Guidelines (https://github.com/Ableton/maxdevtools, m4l-production-guidelines.md, "Undo History") recommend Hidden
  for a control driven from inside the patch and for a live.text in Button mode. The page switch is Hidden (no undo,
  no automation, not in presets: it was a stored parameter, so undo, automation and presets could turn the page).
  The machine's Steps / Accents are Stored Only. The attribute is `parameter_invisible`; no page gives its numbers.
  1 = Stored Only is confirmed by a real preset (the example below has Steps / Accents in its blob, not in its
  automatable parameter list). 2 = Hidden is the inspector's order (Automated and Stored, Stored Only, Hidden),
  not yet seen in a saved file: a preset saved from this build should have no "Page" anywhere.

## Live presets (m4l_dev/live_preset_files.py: the .adv files)

- **The example** (`ableton/example-2sl-stab-preset.adv`, and `.xml`, the same gunzipped): a preset of 2sl stab saved by
  Live 12.4.6 (`<Ableton MajorVersion="5" MinorVersion="12.0_12402" Creator="Ableton Live 12.4.6">`). The kit uses the
  `.xml` as the template for every device's presets. One change from the file Live wrote (2026-10-16): the user folder in
  the `FileRef`'s absolute `Path` is replaced by `/Users/(removed)/` (this repository is public), and the `.adv` was
  gzipped again from that `.xml`. The kit's presets leave `Path` out anyway. What it shows:
  - An `.adv` is gzipped XML (`gzip compressed data`): `<Ableton>` > `<MxDeviceInstrument>`, no other wrapper.
  - The device isn't in it: `PatchSlot/Value/MxPatchRef/FileRef` refers to the `.amxd` (`RelativePathType`,
    `RelativePath`, an absolute `Path`, `Type` 2, `LivePackName`, `LivePackId`, `OriginalFileSize`, `OriginalCrc`).
    Saved inside the repo, Live made the folder a Live Project, copied the device to
    `2sl-stab Project/Presets/Instruments/Max Instrument/Imported/2sl-stab.amxd` and referred to that copy
    (RelativePathType 3).
  - `ParameterList/ParameterList`: one `MxDFloatParameter` (Type 0) or `MxDEnumParameter` (Type 2) per automatable
    parameter, ordered by name: `Index`, `Name` (the long name), `ShortName`, `MinValue`, `MaxValue`, `Default`,
    `IsUndoable`, `IsStored`, and the value in `Timeable/Manual` (an enum's index). Enums list their item `Names`;
    Live listed every live.text's items as `val1` / `val2`, though the patch it loaded (the copy Live made, in commit
    f585d19) saved `parameter_enum` `off` / `on` for them: see live.text below.
  - `Default` is the initial value mapped linearly through the exponent (min + (max - min) * normalised^(1/exponent));
    a float's `MidiControllerRange` is [max(min, 0), max(min, 1)]. Both hold for all 51 parameters in the file.
  - Stored Only parameters aren't in the list: `BlobSlot/Value/MxDBlob/Blob` holds them as hex of JSON plus a NUL:
    `{"Accents": [ 1 ], "Steps": [ 73 ]}` (the dub dotted pattern).
  - `OriginalCrc` is CRC-16 (poly 0x8005, init 0, not reflected: "CRC-16/BUYPASS") of the `.amxd`'s first 16384 bytes.
    Found by trying CRC variants against this file (19576), and confirmed on a second, independent one: Ableton's
    m4l-connection-kit `OSC Leap Motion Example.adg` (Live 9.6) gives Crc 63076, `MaxCrcSize` 16384, FileSize 234834
    for `OSC Leap Motion.amxd` at commit 551c28a, and that file's first 16 KB give 63076.
    https://github.com/Ableton/m4l-connection-kit
- **live.text's state names** (Cycling '74, live.text reference): https://docs.cycling74.com/reference/live.text
  `automation` (default `val1`): "Sets the automation "off" label that will appear in Live."; `automationon` (default
  `val2`): "Sets the automation on label that will appear in Live."; `text` / `texton` only set "the button label".
  The page doesn't list `parameter_enum`. Patches saved by Max carry both, the same: the box's `automation` /
  `automationon` and `parameter_enum` in `valueof` (EnvelopSound/EnvelopForLive
  `patchers/panner/e4l.panner.multicontrol.maxpat`: Off / On; stretta/BEAP `clippings/BEAP/LFO/bp.LFO2.maxpat`: Sync / Freq;
  without the attributes, Ableton's maxdevtools `load-time-tester/Load Time Tester.maxpat` saves `val1` / `val2`).
  So the build sets `automation` / `automationon` to `off` / `on` on every live.text, and the presets list them so.
  Not yet seen in a file Live saved from the fixed build: a preset saved from it should list `off` / `on`.
- **Ableton, Live 12 manual, Working with Instruments and Effects** (23.2.5):
  https://www.ableton.com/en/manual/working-with-instruments-and-effects/
  "Click the Save Preset button in the device title bar ... the preset is highlighted in its corresponding folder in
  the Presets folder of the User Library." "Each device appears in the content pane of the browser as a folder that
  can be opened to reveal its presets." Live-specific device files ".adg, .adv, and .amxd" can be dragged into a set.
- **Ableton, Live 12 manual, Max for Live** (32.2): https://www.ableton.com/en/manual/max-for-live/
  "Max devices are saved separately as AMXD files rather than as part of a Live Set. Moving or renaming a referenced
  AMXD file later can break the associated file path in Live." "By default, a Max device is saved to the relevant
  folder in the User Library based on its device type: an audio effect is stored in the Max Audio Effect folder, a
  MIDI effect in the Max MIDI Effect folder, and so on."
- **Ableton, Live 11 manual, Max for Live**: https://www.ableton.com/en/live-manual/11/max-for-live/
  "If you save a preset for a Max device, Live will try to maintain the necessary file references by copying the Max
  device into your User Library and saving the preset based on this copy. If the referenced Max file is then moved or
  renamed, however, these file associations may be broken." "we recommend always storing Max devices and their
  presets in your User Library."
- **Max for Live Production Guidelines** (https://github.com/Ableton/maxdevtools, m4l-production-guidelines.md,
  "Updates"): "Live stores parameter values for each [live.*] parameter that is set to Automated and Stored or Stored
  Only. Live identifies the [live.*] parameter in a Max for Live device by its Long Name." So the presets name each
  parameter by its long name, and renaming a control breaks its value in every preset.
- **How a shipped preset finds its device** (community, not Ableton documentation): Cycling '74 forum,
  https://cycling74.com/forums/embedding-adv-presets-with-a-max-for-live-amxd-or-how-to-send-device-to-someone-else-with-presets
  Mattijs Kneppers: in the `<FileRef>`, set `RelativePath` to "just the file name of the device", "change Value to 1"
  in `RelativePathType`, "Remove any <Path> and <Type> tags. The presets should now load correctly when placed next to
  the device." and the RelativePathType values: "Invalid = -1, Unknown = 0, RelativeToDocument = 1,
  RelativeToOldLibrary = 2, RelativeToProject = 3, Reserved = 4, RelativeToFactoryPack = 5, RelativeToUserLibrary = 6,
  RelativeToBuiltinContent = 7". The Ableton forum says the same for `PatchSlot`
  (https://forum.ableton.com/viewtopic.php?t=197223). The build follows this (type 1, the file name, no `Path`) but
  keeps `Type` 2, which Live 12 wrote in both real files seen (the example, and a Live 12 set's Max device in
  https://github.com/mattypie/alsdiff, test/data/m4l_device.xml). Not yet tried in Live.
- **Does Live check `OriginalFileSize` / `OriginalCrc`?** No source says. The Live 12 manual's Managing Files and Sets
  (https://www.ableton.com/en/manual/managing-files-and-sets/, "Automatic Repair") says only that with "One candidate
  found — Live accepts the candidate", not how a candidate is matched, and of manual repair: "Live will not care if
  the file you offer is really the file that was missing." Indirect: Ableton's m4l-connection-kit has shipped
  `OSC Leap Motion Example.adg` (Crc 63076, FileSize 234834) next to an `OSC Leap Motion.amxd` updated in 2018
  (commit 6c285b6: 239115 bytes, CRC 64949) without updating the preset; nobody there says whether it still loads.
  So the build writes the real size and CRC for the file each set of presets ships with, and doesn't rely on either
  way.
- **Not yet seen in a saved file** (a preset saved from the current build would show them): whether Live 12 loads a
  preset with type 1 and no `Path`; whether a size / CRC mismatch matters (above); `LastModDate` (the build writes 0, so the
  files are the same every build); that Hidden (parameter_invisible 2) leaves "Page" out of the file.

## Randomness (templates/seeded-sequence.template.js)

- **mulberry32** (Tommy Ettinger, 2017, public domain):
  https://gist.github.com/tommyettinger/46a874533244883189143505d203312c
  The reference C: `uint32_t z = (x += 0x6D2B79F5UL); z = (z ^ (z >> 15)) * (z | 1UL); z ^= z + (z ^ (z >> 7)) *
  (z | 61UL); return z ^ (z >> 14);` A 32-bit state stepped by a Weyl constant, then mixed. In JavaScript the
  products are `Math.imul` (the low 32 bits of the product, exact) and `>>> 0` keeps values unsigned, so Max's [js]
  and node give the same numbers; tests/kit-scripts.test.js checks the first numbers of seed 0 against a Python
  transcription of the C. The gist's notes: it "passes gjrand's 13 tests with no failures" on 4 GB and on its whole
  period (2^32 states); a later comment by the author: it "isn't equidistributed" and "can't produce about 1/3 of all
  possible uint32_t numbers". Plenty for musical chances; not cryptographic.

## Live's control font

- **live.dial** (Max reference): https://docs.cycling74.com/reference/live.dial lists `fontname`, `fontsize`
  ("possible values from 8 to 72") and `fontface` with no default (checked 2026-10-18). No source here gives the
  font Live draws a dial's name, a menu's item or a live.text's text in, or its metrics, so the kit's 5.5 px a
  character (m4l_dev/layout_rules.py) stays a calibration (SHORTCUTS.md).

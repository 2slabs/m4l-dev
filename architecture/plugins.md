# Porting a device to a plugin

How a 2sl device becomes a VST3, and what the first two ports (2sl filter, 2sl stab, October 2026) taught. Each
port's own `plugin/SPEC.md` says what's different about that device; this is the approach they share. The shared code
is `m4l_dev/plugin/` (Python: parameters, the generated header, `.vstpreset` files) and `plugin/cpp/` (C++:
`PluginTable.h`, `GenProgram.h`, `MaxScript`).

## The process

1. **Spec first.** `plugin/SPEC.md` in the device's repository, approved by Cody before any code (2sl's spec-first
   rule). It names the release being ported: **the latest GitHub release** (`gh release view`), never the local
   checkout, which may be ahead.
2. **M1, the sound,** with JUCE's generic editor. Done when it plays in Live like the device side by side, the parity
   tests pass and pluginval passes at strictness 5.
3. **M2, the window,** designed in rounds of mockups before any page code: a published artifact built from the real
   2sl-ui plugin components with a stand-in sound, so every display moves. Cody's notes after each round; the approved
   mockup becomes the spec's window section; then build.
4. **A round in Live** after each build. Expect a feedback round on what the displays show while playing: things a
   stand-in can't show (transport, real readings, saved sets).
5. **A test release** (Releases, below).

## One DSP, one brain, nothing written twice

- **DSP:** the device's gen~ code, exported to C by `genexpr_export` and built with its floating-point flags
  (`-ffp-contract=off -fno-fast-math -fno-builtin`), so it gives the kit renderer's bits. A synth runs one
  `GenProgram` per voice (each its own noise seed, as Max's `mc.gen~` voices draw theirs).
- **Brain:** the device's built `[js]` script runs **unchanged** in QuickJS (`juce_javascript`) through `MaxScript`,
  a shim for the Max globals a 2sl brain uses. What the shim must do as Max does: deliver a message to a function of
  that name, else `anything()` (the node sandbox's `deliverMessage` rule); send an array passed to `outlet()` as its
  items; run `Task` on the audio clock (`advanceTo`), each due run at its own time. Anything the device's display
  outlets send is the window's to show.
- **The wrapper** (the plugin's own C++) does what the patch's Max objects do between the gen~ and the script:
  `midiparse`, the voice allocator, `mc.target`, `phasor~` / `cos~`, the mixdown, `delay`, Stop. It's the one part
  with no device code to share, so it's kept small and every piece has a test.
- **Parameters** come from the device's patch (`host_parameters`, the patch's own `messages_for` routes) and Live's
  parameter lock, never by hand: names, ranges, units, menus, defaults. Stored Only values (a pattern) are plugin
  state, not host parameters. A two-item button with no route (Stop, Throw) is a `Button`: every change is a press.
  Routes that depend on the tempo are recomputed when it changes. Plugin-only parameters (stab's Key and Scale, since
  a plugin can't read Live's scale) go after the device's, so the device's ids and order stay.

## Max objects whose behaviour isn't documented

Measure them in Live. For `mc.noteallocator~` we built probe devices (a patch wired as the device wires it, a `[js]`
driving note sequences and writing what came out to a file with `new File(path, "write", "TEXT")`), ran them in
Live, and kept the logs in `plugin/references/`. The plugin's allocator has a test that plays the probes' sequences
and must give the logs exactly. Fit **every** logged case before believing a rule: our first reading of stab's
("the voice free longest") matched the first probe by chance; the second probe showed a countdown from the last voice
given a note, plus a quirk (a note-off for a stolen note switches off the lowest held voice). The device does it, so
the plugin does.

## Timing

- The brain hears the host as it hears Live: `playing`, `tempo`, and `tick` on every 16th of the song position. The
  plugin works out where each 16th falls in the block from the play head and splits the block there, so a step lands
  on its sample. MIDI, the brain's own `Task` clock and a `delay` closing land on theirs too.
- The window shows the step playing **only while the host plays**. Stopped, a machine may run on its own clock, but
  the counter isn't shown.

## The saved state

- **The state's root tag must be an XML name.** JUCE writes the `AudioProcessorValueTreeState` type as the root tag;
  a plugin name like "2sl stab" (a digit first, a space) is written fine and never read back, so every saved set and
  `.vstpreset` silently loaded the defaults. Both first ports shipped with it. Use `TwoSl<Name>`, and keep a fallback
  that renames the old tag before parsing, so sets saved before the fix still open.
- **Check it by hosting the built VST3**, not only pluginval (whose state test doesn't compare values): load it
  twice, change every parameter, move the state across, compare each parameter's shown text (choices snap to their
  steps). The host wraps the plugin's state (`VST3PluginState`, base64), so an old-format test edits inside it.
- Presets ship as `.vstpreset` files in Live's layout (`m4l_dev/plugin/vstpreset.py` rebuilds a Live-saved one byte
  for byte): Live doesn't list VST3 programs.

## The window

- A page from 2sl-ui's plugin components (`plugin.css`, `plugin.ts`, rules in 2sl-ui's `PLUGINS.md`) in JUCE's
  `WebBrowserComponent`: a web relay and attachment per parameter (drags are host gestures; automation moves the
  controls), native functions for presets, theme and anything the page sends back (stab's step edits), and one
  `readings` event about 30 times a second. The control table is generated with the rest, so the page never repeats a
  range, unit or Info text. A test checks every parameter has exactly one place in the window.
- **Lay it out in the order the sound goes**, in framed bands (stab: notes, voice, effects), each section split by
  hairlines. Use what synths already do (oscillators as columns, then a mixer; a sequencer as lanes, a row a state)
  rather than inventing a layout.
- **Read live values from the DSP's own state**, not re-derived in the page: a gen~ History often holds exactly what a
  display wants (stab's per-voice cutoff is `cutoff x 2^filter_octaves_aligned_whole_1`, its envelope `env` and
  `stage`).
- **Draw a display by the device's rules.** The device's views already chose scales and constants (stab's echo:
  dB below the loop's ceiling of 2 / 1.1, 48 dB deep): read the views template before drawing. Overlays that show
  what the knobs do must depend on the knobs only, never on a jumpy reading, or they jitter.
- **Don't catch a fast event between readings.** A 2 ms attack is over before the next reading, so "the newest voice"
  comes from its note-on number, not from seeing it in its attack. A flash for something that happened comes from a
  counter the engine bumps when it happens (stab's throws), not from an event list that has to survive the trip to the
  page. (In Live, stab's step reports never got a throw through to the page; the counter always did.)
- **Show what the sound is doing, in hues that mean something.** Each modulation source keeps one hue (envelope
  yellow, LFO cyan, pump orange, drive into saturation red), blue only means "now". One blue point per sounding voice
  on a synth's filter and envelope. Light theme: the source hues are 2sl-ui's `--source-*`, darkened so yellow and
  cyan read on a light ground.
- The page runs in a browser with a stand-in host and readings (`?theme=light`, `?set=id:value,...` to start controls
  somewhere), so headless Chrome can screenshot both themes while working on it.

## Verifying without a DAW

- **Parity tests** (each port's `tests/test_plugin.py`): every preset's sound against the kit's renderer to the bit;
  the brain in QuickJS against the node sandbox, message for message; the wrapper against the device's patch (the
  allocator against the probe logs). The engine is built without a host as a console app in the plugin's CMake
  (`render_<name>`), with a `TestAccess` friend for what only tests reach.
- **pluginval** at strictness 5 (`gh release download -R Tracktion/pluginval`), with the window open.
- **The page inside the plugin:** build a standalone app (`-DTWOSL_STANDALONE=ON`), run its binary from a terminal
  and read the page's report lines ("ready: 56 controls bound", "first readings: ..."). Screen recording of other apps
  isn't available here, so this is how to see that the page connected.
- **Cody in Live**, after every build: **quit and reopen Live**. Live keeps a loaded VST3 in memory for the whole
  session; a rescan doesn't reload it.

## JUCE and build gotchas

- A file named `VERSION` in an include path shadows C++'s `<version>` on macOS (case-insensitive): use `version.txt`.
- JUCE's web interop package: import its built `dist/index.js` (its TypeScript sources don't pass `tsc --strict`), and
  only inside the plugin (`window.__JUCE__`), since it talks to the plugin as soon as it loads.
- 2sl-ui's light theme lives on `:root` alone: set the theme on the page's root, not on an inner element.
- A console app (`juce_add_console_app`) needs a project `VERSION`, ignores `PRODUCT_NAME`, and can't use
  `ScopedJuceInitialiser_GUI` unless it links the GUI modules.
- Qualify generated names that collide with JUCE's (`filter::latencySamples`).
- The plugin's CMake build carries the page as binary data, so configuring needs `plugin/ui/dist/index.html`: build
  the page first (`plugin/build.sh` does; the tests build it when it's missing).
- 2sl-ui's repository is shared with other work on branches: commit plugin components to its main from a separate
  worktree off `origin/main`, then `scripts/sync.sh --into plugin/ui/2sl`.

## Releases

- `plugin/package.sh`: the VST3, the presets in their group folders and `INSTALL.txt` (with the
  `xattr -dr com.apple.quarantine` line, since it isn't signed yet), zipped as `<name>-plugin-<version>.zip`. The
  plugin's version is the device's.
- A private repository: one prerelease with the device zip and the plugin zip. A plugin-only fix still bumps the
  device's version, and the notes say the device is unchanged.
- A public repository: plugin test builds are **draft** releases (only people with access see them) with their own
  tag, `plugin-<version>-test.N`, never the device's `vX.Y.Z`.

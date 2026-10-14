# m4l-dev

Max for Live device workspace. Live 12 Suite, bundled Max 9.1.5 (no separate Max license needed).

## Layout
- `devices/` — `.amxd` files. Add this folder to Live's browser (Places → Add Folder) and drag devices onto tracks.
- `src/` — patcher JSON (`.maxpat`) for devices authored or reviewed as text.
- `tools/amxd.py` — convert `.maxpat` ↔ `.amxd`.

## Workflow
1. Drop a device on a track → click the **Edit** (pencil) button in the device title bar → the Max editor opens.
2. Patch, then **Cmd-S** in Max. Live reloads the device on save.
3. Build the UI in **Presentation mode** (Cmd-Opt-E); device height is fixed at 169px.
4. Only `live.*` objects with `parameter_enable` become automatable / MIDI-mappable Live parameters.

## Converting
    tools/amxd.py pack   src/foo.maxpat devices/foo.amxd --type audio   # or midi / instrument
    tools/amxd.py unpack devices/foo.amxd src/foo.maxpat

Unpack before committing if you want readable diffs (an unfrozen `.amxd` is ~JSON anyway).

## Sharing
**Freeze** (snowflake button in the Max toolbar) before giving a device to anyone. Freezing embeds
abstractions, JS, and samples. Keep the unfrozen copy as the source of truth here.

## Useful references
- Max for Live Production Guidelines: github.com/Ableton/maxdevtools
- Live Object Model (LOM) docs: in Max, Help → Reference → "Live Object Model"
- Max for Live Building Tools pack (free, in Live's Packs) — `live.*` UI abstractions and examples

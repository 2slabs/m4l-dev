# Build and release

`build_device(repository, patch, layout, views_code, device_scripts, live_preset_files, command_line_arguments)`
(`twosl_dsp/device_build.py`), in order:

1. **Check the patch** (`DevicePatchBuilder.check`): the preset book against the controls, the gen~ Param defaults
   written from what the initial values send (presets.md), the layout (nothing shown at the same time overlaps or leaves the device, on
   every page and every group choice), Info View text for every visible parameter and display (and none unused), every
   name the UI script looks up, every wire's outlet and inlet. The gen~ code was checked when each gen~ was made.
2. **Generate the scripts**: the UI script and the views script from the kit's templates, the device's own scripts
   (already filled in by the device), every one checked as ES5 with Duktape.
3. **Check the Live parameter lock** (live-parameter-identity.md).
4. **Write devices/<script name>/**: `.maxpat`, the unfrozen `.amxd`, the scripts, the `.adv` presets; stale `.adv`
   removed.
5. **Write the release**: `dist/<script name>-<version>/` with the frozen `.amxd` (scripts embedded, the device's
   own first, then the UI and views scripts) and presets made for it, zipped as `dist/<script name>-<version>.zip`.

Nothing is written before steps 1-3 pass (step 2 includes the generated-numbers check: overview.md, "Generated
numbers"). Every byte depends only on the sources, on every machine: every computed number goes through
`generated_number`, the frozen files' dates are a fixed constant (`twosl_dsp/amxd.py`), the `.adv` gzip header is
written by hand (mtime 0, OS 3), the zip's entries carry a fixed date, `LastModDate` in presets is 0. A build under
Python 3.9 and 3.11 writes the same bytes.

**Releasing**: bump the device's version, build, commit devices/ and the lock, tag, and upload
`dist/<script name>-<version>.zip` to the repository's release.

**Checking a port or a refactor**: `tools/compare_device_builds.py BASELINE CANDIDATE --device NAME` compares two builds
and exits 0 when the gated categories match: the Live parameter table in order (with Info text, varnames,
presentation rectangles), the device width and type, and the presets' parameters and Stored Only blobs. It reports
everything else (boxes, wires, scripts, containers) without gating.

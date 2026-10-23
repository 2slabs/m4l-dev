# Live parameter identity, and the lock

Live finds a Max for Live parameter by its long name ("Live identifies the [live.*] parameter in a Max for Live device
by its Long Name": Max for Live Production Guidelines, references/README.md "Live presets"). Sets, presets, automation,
clip envelopes and MIDI mappings hold values under that name, a float's value as a position mapped through its range and
exponent, and an enum's value as an index into its items. Change one of those and the saved things silently land
somewhere else, or nowhere.

So every device repository keeps `src/live-parameters.lock.json`: one line per Live parameter, in patch order (Live's
order), plus the device type. `twosl_dsp/live_parameter_identity.py` makes the identity from the built patch:

    maxclass, varname, long_name, short_name, type, items, minimum, maximum, exponent, unit_style, initial,
    initial_enabled, visibility, live_item_names (live.text: its automation / automationon names)

`build_device` compares it with the lock before writing anything. A difference fails the build with a unified diff
of the changed lines (each line is one whole parameter). Run `python3 build.py --accept-live-parameter-changes` to
rewrite the lock when the change is meant, commit the lock with the change, and say in the release notes what it breaks.
A missing lock fails the same way (accept writes it).

Not in the lock: Info View text and presentation rectangles. They change how a device looks and reads, not what saved
sets mean, and they change often; a port that must keep them (2sl stab's move onto this kit) checks them with
`tools/compare_device_builds.py`, whose gated parameter table includes them.

Why a short name and the initial value are in it: Live shows the short name on control surfaces and in the Info View,
and a preset written by an older build sets the initial value's position; neither should change by accident. The
initial value is the control's neutral value, its double-click target, not its Init value (presets.md, "Neutral,
Init, and a fresh device").

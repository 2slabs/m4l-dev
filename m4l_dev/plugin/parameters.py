"""A device's host parameters for its plugin, read off the device's own patch: what Live knows each parameter by (the
lock), and how the patch sends each one on (the routes it built, `DevicePatchBuilder.messages_for`). The plugin
generator (each device's `plugin/generate.py`) writes them out with header.py; nothing about a parameter is typed twice.

A parameter reaches its device through one or more routes, each to a named destination:
  gen      a gen~ program's Param: value x scale + offset (a number) or choices[index] (a menu), or for a tempo route
           beats[index] x 60000 / tempo (a time synced to the host's tempo)
  message  a script's message (the brain): the same value forms, sent as `<message> value`
  raw      a box's inlet as a bare number (e.g. a phasor~'s frequency): the same value forms
Parameters with no route are the device's buttons the plugin handles itself (Stop, Throw): `routes` is empty. Live's
Stored Only parameters (visibility 1) are not host parameters: they're the plugin's state (`stored`).
"""
import json

from m4l_dev.build_error import BuildError

LIVE_FLOAT, LIVE_INT, LIVE_ENUM = 0, 1, 2
LIVE_STORED_ONLY = 1
LIVE_HIDDEN = 2
# Live's unit styles (lock "unit_style") as a plugin page's units (2sl-ui plugin.ts `Unit`)
UNITS = {2: "ms", 3: "hz", 4: "db", 5: "%"}
# the tempo messages_for is asked at, for a route that isn't a tempo route (its value doesn't depend on it)
ANY_TEMPO = 120


class Destination:
    """Where a device's patch sends parameters: `box` (its id in the patch), `kind` (gen / message / raw) and, for a
    gen~ program, its Params in order (a route names its Param by index)."""

    def __init__(self, name, box, kind, gen_params=()):
        if kind not in ("gen", "message", "raw"):
            raise BuildError(f"plugin parameters: destination {name} is a {kind!r}, not gen / message / raw")
        self.name, self.box, self.kind, self.gen_params = name, box, kind, list(gen_params)


def _linear(sample, low, high, where):
    """(scale, offset) of a route sampled at the held values `low`..`high` (`sample(held)` -> value), or BuildError if
    the route isn't a straight line."""
    at_low, at_high = sample(low), sample(high)
    scale = (at_high - at_low) / (high - low) if high != low else 0.0
    offset = at_low - scale * low
    for fraction in (0.1, 0.37, 0.5, 0.83):
        held = low + (high - low) * fraction
        sent = sample(held)
        if abs(sent - (scale * held + offset)) > 1e-9 * max(1.0, abs(sent)):
            raise BuildError(f"plugin parameters: {where} isn't a straight line (at {held}: {sent}, not "
                             f"{scale * held + offset})")
    return scale, offset


def host_parameters(patch, lock_path, destinations, left_out=("Page",)):
    """([parameter], [stored]): every Live parameter but `left_out` and the Stored Only ones as a host parameter
    (id, name, short, kind, minimum, maximum, exponent, initial, unit, items, routes), and the Stored Only ones (id,
    name, initial, routes). `destinations` is [Destination]; the routes to any other box (displays, the UI script) are
    the page's business, not the sound's."""
    with open(lock_path, encoding="utf-8") as handle:
        lock = json.load(handle)["parameters"]
    tempo_routes = {(control, destination, message): beats_of
                    for control, beats_of, destination, message in patch.tempo_routes}

    def routes_of(live):
        name, routes = live["long_name"], []
        choices = live["type"] == LIVE_ENUM
        items = range(len(live["items"])) if choices else None
        for destination in destinations:
            tempo = [(message, beats_of) for (control, box, message), beats_of in tempo_routes.items()
                     if control == name and box == destination.box]
            for message, beats_of in tempo:
                if destination.kind != "gen" or message not in destination.gen_params:
                    raise BuildError(f"plugin parameters: {name}'s tempo route to {destination.name} {message!r} isn't a "
                                     "gen~ Param")
                routes.append({"to": destination.name, "kind": "gen", "target": destination.gen_params.index(message),
                               "message": message, "beats": [float(beats_of(i)) for i in items]})
            tempo_messages = {message for message, _ in tempo}
            sent_at = (lambda held: patch.messages_for({name: held}, destination.box, ANY_TEMPO))
            low = 0 if choices else float(live["minimum"])
            messages = [m for m in sent_at(low) if m not in tempo_messages]
            for message in messages:
                if destination.kind == "gen" and message not in destination.gen_params:
                    raise BuildError(f"plugin parameters: {name} sends {destination.name} {message!r}, which isn't one of "
                                     "its Params")
                if (destination.kind == "raw") != (message is None):
                    raise BuildError(f"plugin parameters: {name} sends {destination.name} {message!r}: a raw destination "
                                     "takes a bare number, the others a message")
                route = {"to": destination.name, "kind": destination.kind, "message": message,
                         "target": destination.gen_params.index(message) if destination.kind == "gen" else -1}
                value_at = (lambda held, m=message: float(sent_at(held)[m]))
                if choices:
                    route["choices"] = [value_at(i) for i in items]
                else:
                    route["scale"], route["offset"] = _linear(value_at, low, float(live["maximum"]),
                                                              f"{name} to {destination.name} {message!r}")
                routes.append(route)
        return routes

    parameters, stored = [], []
    for live in lock:
        name = live["long_name"]
        if name in left_out:
            continue
        initial = float((live["initial"] or [0])[0])
        if live.get("visibility") == LIVE_STORED_ONLY:
            stored.append({"id": live["varname"], "name": name, "initial": initial, "routes": routes_of(live)})
            continue
        if live["type"] == LIVE_ENUM:
            kind, low, high = "Choice", 0.0, float(len(live["items"]) - 1)
        elif live["type"] in (LIVE_FLOAT, LIVE_INT):
            kind, low, high = ("Int" if live["type"] == LIVE_INT else "Float"), float(live["minimum"]), float(live["maximum"])
        else:
            raise BuildError(f"plugin parameters: {name} is a Live parameter of type {live['type']}")
        routes = routes_of(live)
        if not routes and kind == "Choice" and len(live["items"]) == 2:
            kind = "Button"    # a two-item button with no route (Stop, Throw): every press is the plugin's to handle
        unit = UNITS.get(live["unit_style"], "bipolar" if low < 0 < high else "") if kind in ("Float", "Int") else ""
        parameters.append({"id": live["varname"], "name": name, "short": live["short_name"].lower(), "kind": kind,
                           "minimum": low, "maximum": high, "exponent": float(live["exponent"]), "initial": initial,
                           "unit_style": live["unit_style"], "unit": unit, "items": list(live["items"]),
                           "routes": routes})
    return parameters, stored


def presets_as_held(patch, parameters, stored, stored_values_of_preset=None):
    """[(title, [held value per parameter], [value per stored])]: the device's presets, as its patch holds them
    ("group: name", or the name alone where they're the same). A device with Stored Only parameters gives
    `stored_values_of_preset(preset values) -> {name: value}`, the same function its Live preset files use
    (live_preset_files.LivePresetFiles)."""
    if stored and stored_values_of_preset is None:
        raise BuildError(f"plugin parameters: the device has Stored Only parameters {[s['name'] for s in stored]} but "
                         "gave no stored_values_of_preset to fill a preset's")
    result = []
    for preset in patch.preset_book.presets_as_held(patch.saved_controls):
        title = preset.name if preset.group == preset.name else f"{preset.group}: {preset.name}"
        held = [0.0 if p["kind"] == "Button" else float(preset.values.get(p["name"], p["initial"])) for p in parameters]
        values = stored_values_of_preset(preset.values) if stored else {}
        if sorted(values) != sorted(s["name"] for s in stored):
            raise BuildError(f"plugin parameters: preset {preset.name!r} gives Stored Only values for {sorted(values)}, "
                             f"not {sorted(s['name'] for s in stored)}")
        result.append((title, held, [float(values[s["name"]]) for s in stored]))
    return result

"""2sl kit: what every 2sl Max for Live device's generator shares.

A device's generator (src/2sl-<device>.py) imports this with importlib (the name starts with a digit):

    kit = importlib.import_module("2sl_kit")
    patch = kit.DevicePatchBuilder(device_name="2sl drums", script_name="2sl-drums", ...)

and then builds its patch with the builder's helpers: boxes and wires, gen~ patchers, Live parameters (dials,
menus, tabs, toggles, hidden stored values) with their Info View text, displays (jsui), the shared header (2sl
link chip, page tabs, preset menu, output level, Stop), Live's transport clock, and finally `finish()`, which
checks the build and writes the .maxpat, the .amxd, the generated scripts and the frozen release.

Taken from src/2sl-stab.py (the fix/stab-step-storage version) so the two devices are built the same way.
2sl stab still has its own copy of all of this (SHORTCUTS.md, 2026-10-15); when the stab work lands, stab is
rebuilt on this kit and its copy deleted.

The layout contract (from 2sl stab): 169 px high on a 4 px grid, as wide as the device needs (stab: 960). A header
row, then every section has three bands aligned across the device: a display (VIEW_Y, VIEW_H), a row of chips and
menus (ROW_Y), and dials (DIAL_Y). `finish()` fails the build when two controls or displays that show at the same
time overlap.

A page can hold groups of controls that a selector shows one at a time: a live.tab (`group_selector`), like 2sl
drums' kit page, where the voice buttons show one voice's controls, or any control (`groups_selected_by`), like
2sl drums' Function dial, which shows only its function's settings.

Controls are in the presets (their initial value from BASE, the Init preset) unless they are given
`initial_outside_presets`: then they are saved with the set but presets leave them alone.
"""
import json
import os
import re
import subprocess
import sys

SOURCE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
REPOSITORY_ROOT = os.path.dirname(SOURCE_DIRECTORY)

DEVICE_HEIGHT = 169
DIAL_WIDTH, DIAL_HEIGHT = 44, 48
VIEW_Y, VIEW_H, ROW_Y, DIAL_Y = 28, 64, 98, 119
ROW_H = 15
HEADER_Y = 3

# 2sl-ui tokens, dark and light (2sl-ui/max/2sl-colors.json), plus the few the devices need
THEMES = {
    "dark": {"pad": [0.149, 0.149, 0.149, 1], "well": [0.106, 0.106, 0.11, 1], "ink": [0.835, 0.847, 0.859, 1],
             "inverse": [0.149, 0.149, 0.149, 1], "label": [0.557, 0.58, 0.608, 1], "unlit": [0.494, 0.518, 0.545, 1],
             "mint": [0.447, 0.871, 0.761, 1], "now": [0.176, 0.357, 1.0, 1],
             "rest": [0.2, 0.2, 0.21, 1], "beat": [0.26, 0.27, 0.28, 1]},
    "light": {"pad": [0.835, 0.847, 0.859, 1], "well": [0.77, 0.78, 0.79, 1], "ink": [0.0, 0.0, 0.0, 1],
              "inverse": [1.0, 1.0, 1.0, 1], "label": [0.349, 0.369, 0.396, 1], "unlit": [0.451, 0.475, 0.502, 1],
              "mint": [0.12, 0.55, 0.45, 1], "now": [0.176, 0.357, 1.0, 1],
              "rest": [0.7, 0.71, 0.73, 1], "beat": [0.62, 0.63, 0.65, 1]},
}

# Light or dark, from Live's theme: shared by the displays and the UI script (both are generated with it).
THEME_FROM_LIVE_JS_TEMPLATE = """
var THEMES = %(themes)s;
var liveColourMissingReported = false;
/** The 2sl tokens for Live's theme: light when Live's surface colour (live_surface_bg) is light. If Max can't
 *  give that colour, dark, and the Max window says which colour was missing (once, until it is back). */
function themeFromLive(who) {
  var surface = null, failure = "";
  try { surface = max.getcolor("live_surface_bg"); } catch (e) { failure = String(e); }
  var usable = surface && surface.length >= 3 && isFinite(surface[0]) && isFinite(surface[1]) && isFinite(surface[2]);
  if (!usable) {
    if (!liveColourMissingReported) {
      liveColourMissingReported = true;
      error("%(device)s (" + who + "): Live colour live_surface_bg is missing (max.getcolor gave " +
            (failure || JSON.stringify(surface)) + "): drawing in the dark theme\\n");
    }
    return THEMES.dark;
  }
  liveColourMissingReported = false;
  var luminance = 0.2126 * surface[0] + 0.7152 * surface[1] + 0.0722 * surface[2];
  return luminance > 0.5 ? THEMES.light : THEMES.dark;
}""".strip()

LIVE_OBJECT_OUTLETS = {"live.dial": (2, ["", "float"]), "live.menu": (3, ["", "", "float"]),
                       "live.tab": (3, ["", "", "float"]), "live.text": (2, ["", ""]),
                       "live.numbox": (2, ["", "float"])}


class BuildError(SystemExit):
    """A broken build: the generator stops and says why (never writes a half-checked device)."""


def varname_for(long_name):
    return long_name.lower().replace(" ", "_")


class DevicePatchBuilder:
    """One device's patch, built box by box. Every helper records what `finish()` needs to check the build."""

    def __init__(self, device_name, script_name, version, subtitle, page_names, info, base, link_chip_text,
                 device_width):
        self.device_name = device_name              # "2sl drums": in error messages and the chrome
        if device_width % 4:
            raise BuildError(f"{script_name}.py: the device width {device_width} is off the 4 px grid")
        self.device_width = device_width
        self.script_name = script_name              # "2sl-drums": file names
        self.version = version
        self.subtitle = subtitle                    # drawn in the header after the link chip
        self.link_chip_text = link_chip_text        # the wordmark chip ("2sl drums")
        self.page_names = list(page_names)
        self.info = info                            # long name -> (Info View title, text)
        self.base = base                            # the Init preset: every saved control's initial value
        self.info_used = set()
        self.boxes, self.lines = [], []
        self.box_count = 0
        self.pages = {name: [] for name in self.page_names}
        self.preset_varname_by_control = {}         # parameter long name -> varname (for presets)
        self.initial_values = {}                    # parameter long name -> its initial value (BASE's or its own)
        self.groups = {}                            # selector varname -> {"page": page, "members": [[varname]]}
        self.controls_by_kind = {"dial": [], "text": [], "menu": [], "tab": [], "numbox": []}
        self.view_varnames = []
        self.control_by_box = {}                    # box id -> the name of the control it is
        self.view_mode_by_box = {}
        self.view_defaults = {}                     # view mode -> {message: value it gets for BASE}
        self.gen_param_from_base = []               # (gen box id, Param name, value BASE sends, control name)
        self.gen_code_by_box = {}                   # gen~ box id -> its code (for the Param default check)
        self.control_routes = []                    # (control, destination box, message, scale)

    def fail(self, message):
        raise BuildError(f"{self.script_name}.py: {message}")

    # ---- boxes and wires -----------------------------------------------------------------------------

    def box(self, text=None, cls="newobj", rect=(0, 0, 80, 22), ins=1, outs=1, outtype=None, **extra):
        self.box_count += 1
        new_box = {"id": f"obj-{self.box_count}", "maxclass": cls, "numinlets": ins, "numoutlets": outs,
                   "patching_rect": [float(v) for v in rect]}
        if text is not None:
            new_box["text"] = text
        if outs:
            new_box["outlettype"] = outtype or [""] * outs
        new_box.update(extra)
        self.boxes.append({"box": new_box})
        return new_box["id"]

    def wire(self, source, destination, source_outlet=0, destination_inlet=0):
        for end in (source, destination):
            if not any(x["box"]["id"] == end for x in self.boxes):
                self.fail(f"a wire names box {end!r}, which doesn't exist")
        self.lines.append({"patchline": {"source": [source, source_outlet],
                                         "destination": [destination, destination_inlet]}})

    def find(self, box_id):
        found = [x["box"] for x in self.boxes if x["box"]["id"] == box_id]
        if len(found) != 1:
            self.fail(f"box {box_id!r} found {len(found)} times")
        return found[0]

    def gen_box(self, code, ins, outs, rect):
        """A gen~ box holding `code` in a codebox, with `ins` inlets and `outs` outlets.

        The codebox has as many inlets and outlets as the highest inN / outN the code uses, so the gen patcher's
        [in] / [out] objects must match that: they are derived from the code (a gen~ keeps one inlet for messages
        even with no [in])."""
        code_without_comments = re.sub(r"//[^\n]*|/\*.*?\*/", "", code, flags=re.S)
        used_ins = max([int(n) for n in re.findall(r"\bin(\d+)\b", code_without_comments)] or [0])
        used_outs = max([int(n) for n in re.findall(r"\bout(\d+)\b", code_without_comments)] or [0])
        if used_ins > ins or used_outs != outs:
            self.fail(f"gen~ code uses in1..in{used_ins} and out1..out{used_outs}, the box was given {ins} in, {outs} out")
        box_id = self.box("gen~", rect=rect, ins=max(ins, 1), outs=outs, outtype=["signal"] * outs,
                          patcher=self.gen_patcher(code, used_ins, outs))
        self.gen_code_by_box[box_id] = code
        return box_id

    @staticmethod
    def gen_patcher(code, ins, outs):
        sub_boxes, sub_lines = [], []
        sub_boxes.append({"box": {"id": "cb", "maxclass": "codebox", "code": code.strip() + "\n",
                                  "fontname": "<Monospaced>", "fontsize": 12.0, "numinlets": ins, "numoutlets": outs,
                                  "outlettype": [""] * outs, "patching_rect": [20.0, 60.0, 700.0, 600.0]}})
        for i in range(ins):
            sub_boxes.append({"box": {"id": f"in{i+1}", "maxclass": "newobj", "text": f"in {i+1}", "numinlets": 0,
                                      "numoutlets": 1, "outlettype": [""],
                                      "patching_rect": [20.0 + 80 * i, 20.0, 40.0, 22.0]}})
            sub_lines.append({"patchline": {"source": [f"in{i+1}", 0], "destination": ["cb", i]}})
        for o in range(outs):
            sub_boxes.append({"box": {"id": f"out{o+1}", "maxclass": "newobj", "text": f"out {o+1}", "numinlets": 1,
                                      "numoutlets": 0, "patching_rect": [20.0 + 80 * o, 680.0, 45.0, 22.0]}})
            sub_lines.append({"patchline": {"source": ["cb", o], "destination": [f"out{o+1}", 0]}})
        return {"fileversion": 1,
                "appversion": {"major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1},
                "classnamespace": "dsp.gen", "rect": [100.0, 100.0, 760.0, 740.0],
                "boxes": sub_boxes, "lines": sub_lines}

    # ---- Live parameters -----------------------------------------------------------------------------

    def initial(self, name, initial_outside_presets=None):
        """A control's initial value: BASE's. Controls presets don't set (Preset, Page, a device's pattern tools)
        give their own."""
        if name in self.base:
            if initial_outside_presets is not None:
                self.fail(f"{name!r} is in BASE, so its initial value comes from there")
            value = self.base[name]
        elif initial_outside_presets is None:
            self.fail(f"{name!r} has no BASE value (the Init preset): add it to BASE")
        else:
            value = initial_outside_presets
        self.initial_values[name] = value
        return value

    def in_presets(self, name, varname, initial_outside_presets):
        """Presets set the control unless it was given its own initial value."""
        if initial_outside_presets is None:
            self.preset_varname_by_control[name] = varname

    def param(self, cls, name, short, rect, kind, prect, **values):
        """A Live parameter shown in presentation at `prect`, with its Info View text from INFO."""
        saved_values = {"parameter_longname": name, "parameter_shortname": short, "parameter_type": kind}
        saved_values.update(values)
        annotation = {}
        if name in self.info:
            title, text = self.info[name]
            self.info_used.add(name)
            # Max saves these on the box and mirrors them in the parameter's saved values (as it writes them itself)
            annotation = {"annotation_name": title, "annotation": text}
            saved_values.update(parameter_annotation_name=title, parameter_info=text)
        elif not values.get("parameter_invisible"):
            self.fail(f"parameter {name!r} has no Info View text: add it to INFO")
        outlet_count, outlet_types = LIVE_OBJECT_OUTLETS[cls]
        extra = {}
        if cls == "live.text":
            extra = {"text": short.lower(), "texton": short.lower(), "mode": saved_values.pop("_mode", 1)}
            saved_values.update(parameter_enum=["off", "on"], parameter_mmax=1)
        box_id = self.box(cls=cls, rect=rect, ins=1, outs=outlet_count, outtype=outlet_types,
                          varname=varname_for(name), parameter_enable=1, presentation=1,
                          presentation_rect=[float(x) for x in prect],
                          saved_attribute_attributes={"valueof": saved_values}, **annotation, **extra)
        self.control_by_box[box_id] = name
        return box_id

    def on_page(self, page, box_id, varname, group=None):
        """Put a box on `page` (None: the header, on every page), and in `group` = (selector varname, index):
        shown only while that selector picks that index."""
        if page:
            if page not in self.pages:
                self.fail(f"{varname!r} is placed on page {page!r}, which isn't one of {self.page_names}")
            self.pages[page].append(varname)
        found = self.find(box_id)
        found["varname"] = varname
        if page and page != self.page_names[0]:
            found["hidden"] = 1
        if group is not None:
            selector, index = group
            if selector not in self.groups:
                self.fail(f"{varname!r} is in group {group}, but {selector!r} is no group selector")
            if self.groups[selector]["page"] != page:
                self.fail(f"{varname!r} is on page {page!r}, its group selector {selector!r} on {self.groups[selector]['page']!r}")
            members = self.groups[selector]["members"]
            if not 0 <= index < len(members):
                self.fail(f"{varname!r}: group {selector!r} has {len(members)} choices, not {index + 1}")
            members[index].append(varname)
            if index != 0:                          # the selector starts on its first choice
                found["hidden"] = 1
        return box_id

    def tell(self, source, message, destination, inlet=0, scale=None):
        """Wire `source`'s value to `destination` as `message value` (or raw when message is None)."""
        if source in self.control_by_box and message is not None:
            control_name = self.control_by_box[source]
            self.control_routes.append((control_name, destination, message, scale))
            if control_name in self.initial_values:
                sent = self.initial_values[control_name] * (scale if scale is not None else 1)
                if destination in self.view_mode_by_box:
                    self.view_defaults.setdefault(self.view_mode_by_box[destination], {})[message] = sent
                elif destination in self.gen_code_by_box:
                    self.gen_param_from_base.append((destination, message, sent, control_name))
        chain = source
        if scale is not None:
            scaler = self.box(f"* {scale}", rect=(1300, 900 + 2 * len(self.boxes), 50, 22), ins=2, outtype=["float"])
            self.wire(chain, scaler)
            chain = scaler
        if message is None:
            self.wire(chain, destination, 0, inlet)      # the raw value
            return
        prepend = self.box(f"prepend {message}", rect=(1360, 900 + 2 * len(self.boxes), 100, 22))
        self.wire(chain, prepend)
        self.wire(prepend, destination, 0, inlet)

    def dial(self, name, short, target, message, minimum, maximum, unit, x, y, page, exponent=1.0, scale=1.0,
             views=(), group=None, initial_outside_presets=None, integer=False, items=None, inlet=0):
        """A live.dial: a float by default; integer=True Live's Int type (256 values at most, as `numbox`);
        items=[names] an enum (minimum, maximum, unit and exponent unused), showing the chosen name."""
        if integer and maximum - minimum > 255:
            self.fail(f"dial {name!r}: an Int parameter holds 256 values, {minimum}..{maximum} has more")
        initial = self.initial(name, initial_outside_presets)
        if items is not None:
            if integer:
                self.fail(f"dial {name!r} is an enum or an Int, not both")
            kind, values = 2, dict(parameter_enum=list(items), parameter_mmax=len(items) - 1)
        else:
            kind, values = (1 if integer else 0), dict(parameter_mmin=float(minimum), parameter_mmax=float(maximum),
                                                       parameter_unitstyle=unit, parameter_exponent=float(exponent))
        box_id = self.param("live.dial", name, short, (1500 + x, 700 + y, DIAL_WIDTH, DIAL_HEIGHT), kind,
                            (x, y, DIAL_WIDTH, DIAL_HEIGHT), parameter_initial_enable=1,
                            parameter_initial=[float(initial) if items is None else initial], **values)
        varname = varname_for(name)
        self.on_page(page, box_id, varname, group)
        self.in_presets(name, varname, initial_outside_presets)
        self.controls_by_kind["dial"].append(varname)
        self.tell(box_id, message, target, inlet, scale if scale != 1.0 else None)
        for view_box, view_message in views:
            self.tell(box_id, view_message, view_box, 0, scale if scale != 1.0 else None)
        return box_id

    def menu(self, name, short, items, x, y, w, page, initial_outside_presets=None, group=None):
        box_id = self.param("live.menu", name, short, (1500 + x, 640 + y, w, ROW_H), 2, (x, y, w, ROW_H),
                            parameter_enum=items, parameter_mmax=len(items) - 1, parameter_initial_enable=1,
                            parameter_initial=[self.initial(name, initial_outside_presets)])
        varname = varname_for(name)
        self.in_presets(name, varname, initial_outside_presets)
        self.controls_by_kind["menu"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def tabs(self, name, short, items, x, y, w, page, initial_outside_presets=None, group=None):
        """Selector buttons (a live.tab), side by side on one line."""
        box_id = self.param("live.tab", name, short, (1500 + x, 600 + y, w, ROW_H), 2, (x, y, w, ROW_H),
                            parameter_enum=items, parameter_mmax=len(items) - 1, parameter_initial_enable=1,
                            parameter_initial=[self.initial(name, initial_outside_presets)])
        varname = varname_for(name)
        self.find(box_id).update(num_lines_patching=1, num_lines_presentation=1)
        self.in_presets(name, varname, initial_outside_presets)
        self.controls_by_kind["tab"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def groups_selected_by(self, selector_box, choice_count, page):
        """Make `selector_box` (any control whose value is a choice 0..choice_count-1) show one group of boxes on
        `page` at a time; boxes join a group with group=(the selector's varname, i). It starts on its first group,
        so the selector's initial value must be 0."""
        varname = self.find(selector_box)["varname"]
        if varname in self.groups:
            self.fail(f"{varname!r} selects groups twice")
        if self.initial_values.get(self.control_by_box[selector_box]) != 0:
            self.fail(f"group selector {varname!r} must start on its first group (initial value 0)")
        self.groups[varname] = {"page": page, "members": [[] for _ in range(choice_count)]}
        self.tell(selector_box, f"group {varname}", self.header_boxes["ui"])

    def group_selector(self, name, short, items, x, y, w, page):
        """A live.tab that shows one group of boxes on `page` at a time (see `groups_selected_by`). Saved with the
        set, not in presets; starts on the first group."""
        box_id = self.tabs(name, short, items, x, y, w, page, initial_outside_presets=0)
        self.groups_selected_by(box_id, len(items), page)
        return box_id

    def toggle(self, name, short, x, y, w, h, page, mode=1, initial_outside_presets=None, group=None):
        """A live.text: mode 1 a toggle (saved; in presets unless it has its own initial value), mode 0 a
        momentary button (neither)."""
        initial_values = ({"parameter_initial_enable": 1,
                           "parameter_initial": [self.initial(name, initial_outside_presets)]} if mode == 1 else {})
        box_id = self.param("live.text", name, short, (1500 + x, 660 + y, w, h), 2, (x, y, w, h), _mode=mode,
                            **initial_values)
        varname = varname_for(name)
        if mode == 1:
            self.in_presets(name, varname, initial_outside_presets)
        self.controls_by_kind["text"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def numbox(self, name, short, target, message, minimum, maximum, unit, x, y, w, page, integer=False,
               inlet=0, initial_outside_presets=None, group=None):
        """A live.numbox. integer=True: Live's Int type, which holds 256 values at most (see `stored`)."""
        if integer and maximum - minimum > 255:
            self.fail(f"numbox {name!r}: an Int parameter holds 256 values, {minimum}..{maximum} has more")
        box_id = self.param("live.numbox", name, short, (1500 + x, 680 + y, w, ROW_H), 1 if integer else 0,
                            (x, y, w, ROW_H), parameter_mmin=float(minimum), parameter_mmax=float(maximum),
                            parameter_initial_enable=1,
                            parameter_initial=[float(self.initial(name, initial_outside_presets))],
                            parameter_unitstyle=unit)
        varname = varname_for(name)
        self.on_page(page, box_id, varname, group)
        self.in_presets(name, varname, initial_outside_presets)
        self.controls_by_kind["numbox"].append(varname)
        self.tell(box_id, message, target, inlet)
        return box_id

    def stored(self, name, initial_value):
        """A parameter Live stores with the set but doesn't show or automate.

        Float type with an Int unit style: Live's Int type holds only 256 values (0-255), which would cut a 16-bit
        value down to its first 8 bits. Cycling '74's param reference gives this pattern for bigger integers."""
        if not (0 <= initial_value <= 65535 and initial_value == int(initial_value)):
            self.fail(f"stored value {name!r} starts at {initial_value}, outside the 16-bit range it can hold")
        box_id = self.param("live.numbox", name, name, (1500, 1400 + (30 * len(self.boxes)) % 300, 60, 15), 0,
                            (0, 0, 60, 15), parameter_mmin=0.0, parameter_mmax=65535.0, parameter_initial_enable=1,
                            parameter_initial=[float(initial_value)], parameter_unitstyle=0, parameter_invisible=1)
        stored_box = self.find(box_id)
        stored_box["presentation"] = 0
        del stored_box["presentation_rect"]
        return box_id

    # ---- displays ------------------------------------------------------------------------------------

    def view(self, mode, x, y, w, h, page, background=False, info=None, group=None):
        """A display (jsui running the device's view script) in `mode`, with Info View text from INFO."""
        # background=True: Max's "Include in Background", so it always sits behind every other object
        extra = {"ignoreclick": 1, "background": 1} if background else {}
        if info:
            if info not in self.info:
                self.fail(f"view {mode!r} names Info View text {info!r}, which INFO doesn't have")
            title, text = self.info[info]
            self.info_used.add(info)
            extra.update(annotation_name=title, annotation=text)
        elif not background:
            # only the background (it ignores clicks, so it is never hovered) may go without
            self.fail(f"view {mode!r} has no Info View text: pass info= with an INFO key")
        box_id = self.box(cls="jsui", rect=(1500 + x, 1000 + y, w, h), ins=1, outs=1,
                          filename=f"{self.script_name}-view.js", jsarguments=[mode], presentation=1,
                          presentation_rect=[float(x), float(y), float(w), float(h)], border=0, **extra)
        self.view_varnames.append(f"view_{mode}")
        self.view_mode_by_box[box_id] = mode
        return self.on_page(page, box_id, f"view_{mode}", group)

    # ---- the header and the plumbing every device has ---------------------------------------------------

    def header(self, volume_target, preset_x, preset_w):
        """The device background, the UI script, the 2sl link chip, page tabs, Preset, Volume and Stop.

        Returns a dict of the boxes a device wires further: chrome, ui, thisdevice, ready, stop, preset, volume,
        page_tabs."""
        made = {}
        made["chrome"] = self.view("chrome", 0, 0, self.device_width, DEVICE_HEIGHT, None, background=True)
        made["ui"] = self.box(f"js {self.script_name}-ui.js", rect=(1100, 30, 120, 22), ins=1, outs=1)
        thispatcher = self.box("thispatcher", rect=(1100, 60, 80, 22), ins=1, outs=2)
        self.wire(made["ui"], thispatcher)
        made["thisdevice"] = self.box("live.thisdevice", rect=(420, 30, 100, 22), ins=1, outs=3,
                                      outtype=["bang", "int", "int"])
        ready_delay = self.box("delay 800", rect=(1100, 0, 70, 22), ins=2, outs=1, outtype=["bang"])
        made["ready"] = self.box(cls="message", text="ready", rect=(1180, 0, 50, 22), ins=2, outs=1)
        self.wire(made["thisdevice"], ready_delay)
        self.wire(ready_delay, made["ready"])
        self.wire(made["ready"], made["ui"])
        colors = self.box("live.colors", rect=(1250, 30, 70, 22), ins=1, outs=2, outtype=["", "bang"])
        theme_message = self.box(cls="message", text="theme", rect=(1250, 60, 45, 22), ins=2, outs=1)
        self.wire(colors, theme_message, 1, 0)
        self.wire(theme_message, made["ui"])

        # the 2sl wordmark chip, a link back to 2sl.to (hover shows it, click opens it)
        # Cozette advances 6 px a character; the chip has 4 px either side
        link_width = 6 * len(self.link_chip_text) + 8
        self.view("link", 12, HEADER_Y, link_width, 15, None, info="Link view")
        # live.tab splits its width equally: room for the longest name in every tab
        tab_width = len(self.page_names) * max(48, 6 * max(len(n) for n in self.page_names) + 12)
        made["page_tabs"] = self.param("live.tab", "Page", "Page", (1500, 560, tab_width, 15), 2,
                                       (float(12 + link_width + 8), float(HEADER_Y), float(tab_width), 15.0),
                                       parameter_enum=self.page_names, parameter_mmax=len(self.page_names) - 1,
                                       parameter_initial_enable=1, parameter_initial=[0])
        self.find(made["page_tabs"]).update(num_lines_patching=1, num_lines_presentation=1, varname="page")
        self.controls_by_kind["tab"].append("page")
        self.tell(made["page_tabs"], "page", made["ui"])
        self.tell(made["page_tabs"], "page", made["chrome"])
        self.header_preset_x = preset_x
        made["preset"] = self.menu("Preset", "Preset", ["-"], preset_x, HEADER_Y, preset_w, None,
                                   initial_outside_presets=0)  # items set by finish()
        self.wire(made["preset"], made["ui"])
        # the right end of the header: out (Volume) and Stop, 12 px from the device's edge
        self.header_volume_x = self.device_width - 136
        made["volume"] = self.param("live.numbox", "Volume", "Volume", (1500, 520, 64, 15), 0,
                                    (float(self.header_volume_x), float(HEADER_Y), 64.0, 15.0), parameter_mmin=-36.0,
                                    parameter_mmax=12.0, parameter_initial_enable=1,
                                    parameter_initial=[float(self.initial("Volume"))], parameter_unitstyle=4)
        self.find(made["volume"]).update(varname="volume")
        self.preset_varname_by_control["Volume"] = "volume"
        self.controls_by_kind["numbox"].append("volume")
        self.tell(made["volume"], "volume", volume_target)
        made["stop"] = self.param("live.text", "Stop", "Stop", (1500, 540, 48, 15), 2,
                                  (float(self.device_width - 60), float(HEADER_Y), 48.0, 15.0), _mode=0)
        self.find(made["stop"]).update(varname="stop")
        self.controls_by_kind["text"].append("stop")
        self.header_boxes = made
        return made

    def live_transport(self, thisdevice, brain, brain_inlet):
        """Live's tempo and transport, and the 16th clock (from 2sl stab).

        The brain gets `tempo f`, `playing i` and, on every 16th while Live plays, `tick <song position in
        ticks>` (480 per quarter note): a [metro 16n @quantize 16n] bang asks [transport] for the position. Live
        playing or not arrives in a set order (trigger: right to left): the brain first, and only then does the
        metro start, so its immediate bang finds the brain playing."""
        start = self.box("t b b", rect=(420, 60, 40, 22), outs=2, outtype=["bang", "bang"])
        self.wire(thisdevice, start)
        path_message = self.box(cls="message", text="path live_set", rect=(420, 90, 90, 22), ins=2, outs=1)
        live_path = self.box("live.path", rect=(420, 120, 70, 22), ins=1, outs=3)
        self.wire(start, path_message, 0, 0)
        self.wire(path_message, live_path)
        observers = {}
        for i, property_name in enumerate(("tempo", "is_playing")):
            property_message = self.box(cls="message", text=f"property {property_name}",
                                        rect=(520 + 160 * i, 90, 120, 22), ins=2, outs=1)
            observer = self.box("live.observer", rect=(520 + 160 * i, 150, 90, 22), ins=2, outs=2)
            self.wire(start, property_message, 1, 0)
            self.wire(property_message, observer)
            self.wire(live_path, observer, 0, 1)
            observers[property_name] = observer
        tempo_to_brain = self.box("prepend tempo", rect=(520, 250, 90, 22))
        self.wire(observers["tempo"], tempo_to_brain)
        self.wire(tempo_to_brain, brain, 0, brain_inlet)
        metro = self.box("metro 16n @quantize 16n", rect=(30, 520, 160, 22), ins=2, outs=1, outtype=["bang"])
        playing_order = self.box("t i i", rect=(940, 210, 60, 22), ins=1, outs=2, outtype=["int", "int"])
        self.wire(observers["is_playing"], playing_order)
        playing_to_brain = self.box("prepend playing", rect=(940, 240, 100, 22))
        self.wire(playing_order, playing_to_brain, 1, 0)
        self.wire(playing_to_brain, brain, 0, brain_inlet)
        self.wire(playing_order, metro, 0, 0)
        transport = self.box("transport", rect=(30, 550, 70, 22), ins=2, outs=9)
        tick_message = self.box("prepend tick", rect=(30, 610, 80, 22))
        self.wire(metro, transport)
        self.wire(transport, tick_message, 7, 0)          # raw ticks: 480 per quarter note
        self.wire(tick_message, brain, 0, brain_inlet)

    # ---- finishing: checks, scripts, the patch, the device -----------------------------------------------

    def finish(self, presets, layout, view_template, script_replacements, embedded_scripts):
        """Check the build and write everything.

        presets: [(name, {control: value})] (each on top of BASE); layout: the chrome's rules and labels per page;
        view_template: the device's view code (inserted into the kit view template); script_replacements: {output
        file: text} for the device's other generated scripts; embedded_scripts: the file names the frozen release
        embeds. The device is a Max for Live instrument."""
        preset_box = self.find(self.header_boxes["preset"])
        preset_box["saved_attribute_attributes"]["valueof"].update(
            parameter_enum=[name for name, _ in presets], parameter_mmax=len(presets) - 1)

        # the gen~ Param defaults must be what BASE sends them (the sound before Live recalls the controls)
        mismatches = []
        for gen_box_id, param_name, sent, control_name in self.gen_param_from_base:
            declared = re.search(r"Param " + re.escape(param_name) + r"\(([^,)]+)", self.gen_code_by_box[gen_box_id])
            if not declared:
                mismatches.append(f"{control_name} -> {param_name}: no such Param")
            elif abs(float(declared.group(1)) - sent) > 1e-9:
                mismatches.append(f"{control_name} -> Param {param_name}({declared.group(1)}), BASE sends {sent:g}")
        if mismatches:
            self.fail("gen~ Param defaults disagree with BASE (the Init sound):\n  " + "\n  ".join(mismatches))
        self.check_layout()

        if set(self.info) - self.info_used:
            self.fail(f"INFO has text for no parameter or view: {sorted(set(self.info) - self.info_used)}")
        missing_base = set(self.preset_varname_by_control) - set(self.base)
        if missing_base:
            self.fail(f"BASE has no preset value for: {sorted(missing_base)}")
        unknown_base = set(self.base) - set(self.preset_varname_by_control)
        if unknown_base:
            self.fail(f"BASE has values for controls that don't exist: {sorted(unknown_base)}")
        for preset_name, preset_values in presets:
            unknown = set(preset_values) - set(self.base)
            if unknown:
                self.fail(f"preset {preset_name!r} sets controls BASE doesn't have: {sorted(unknown)}")
        presets_js = [{self.preset_varname_by_control[k]: v for k, v in {**self.base, **p}.items()} for _, p in presets]

        theme_js = THEME_FROM_LIVE_JS_TEMPLATE % {"themes": json.dumps(THEMES), "device": self.device_name}
        layout = dict(layout, subtitle_text=self.subtitle, version=self.version, link_chip_text=self.link_chip_text)
        device_directory = os.path.join(REPOSITORY_ROOT, "devices", self.script_name)
        os.makedirs(device_directory, exist_ok=True)

        view_kit = open(os.path.join(SOURCE_DIRECTORY, "2sl-kit-view.template.js")).read()
        glyphs = open(os.path.join(SOURCE_DIRECTORY, "cozette-glyphs.js")).read()
        view_js = self.fill_template(view_kit, {
            "/*DEVICE_NAME*/": self.device_name, "/*SCRIPT_NAME*/": self.script_name,
            "/*COZETTE*/": glyphs.strip(), "/*THEME_FROM_LIVE*/": theme_js,
            "/*VIEW_DEFAULTS*/": json.dumps(self.view_defaults),
            "/*LAYOUT*/": "var LAYOUT = " + json.dumps(layout) + ";",
            "/*DEVICE_VIEWS*/": view_template.strip()}, "the kit view template")
        self.write(os.path.join(device_directory, f"{self.script_name}-view.js"), view_js)

        ui_kit = open(os.path.join(SOURCE_DIRECTORY, "2sl-kit-ui.template.js")).read()
        ui_js = self.fill_template(ui_kit, {
            "/*DEVICE_NAME*/": self.device_name, "/*SCRIPT_NAME*/": self.script_name,
            "/*PAGE_NAMES*/": json.dumps(self.page_names), "/*PAGES*/": json.dumps(self.pages),
            "/*PRESETS*/": json.dumps(presets_js, indent=1), "/*CONTROLS*/": json.dumps(self.controls_by_kind),
            "/*GROUPS*/": json.dumps(self.groups),
            "/*VIEWS*/": json.dumps(self.view_varnames), "/*THEME_FROM_LIVE*/": theme_js}, "the kit UI template")
        self.write(os.path.join(device_directory, f"{self.script_name}-ui.js"), ui_js)
        for path, text in script_replacements.items():
            self.write(path, text)

        # every name the UI script looks up must name exactly one box (it errors at run time otherwise)
        box_varnames = [x["box"]["varname"] for x in self.boxes if "varname" in x["box"]]
        ui_lookups = ({n for p in presets_js for n in p} | {n for k in self.controls_by_kind for n in self.controls_by_kind[k]}
                      | set(self.view_varnames) | {n for k in self.pages for n in self.pages[k]})
        if ui_lookups - set(box_varnames):
            self.fail(f"the UI script looks up names no box has: {sorted(ui_lookups - set(box_varnames))}")
        if len(box_varnames) != len(set(box_varnames)):
            self.fail(f"varnames used twice: {sorted({n for n in box_varnames if box_varnames.count(n) > 1})}")

        # every wire leaves an outlet its box has and enters an inlet its box has
        boxes_by_id = {x["box"]["id"]: x["box"] for x in self.boxes}
        bad_wires = []
        for line in self.lines:
            (source, outlet_index), (destination, inlet_index) = line["patchline"]["source"], line["patchline"]["destination"]
            if outlet_index >= boxes_by_id[source]["numoutlets"]:
                bad_wires.append(f"{boxes_by_id[source].get('text', boxes_by_id[source]['maxclass'])} has no outlet {outlet_index}")
            if inlet_index >= boxes_by_id[destination]["numinlets"]:
                bad_wires.append(f"{boxes_by_id[destination].get('text', boxes_by_id[destination]['maxclass'])} has no inlet {inlet_index}")
        if bad_wires:
            self.fail("wires to outlets or inlets that don't exist:\n  " + "\n  ".join(bad_wires))

        patch = {"patcher": {
            "fileversion": 1,
            "appversion": {"major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1},
            "classnamespace": "box", "rect": [80.0, 80.0, 1300.0, 900.0],
            "openinpresentation": 1, "devicewidth": float(self.device_width),
            "boxes": self.boxes, "lines": self.lines,
        }}
        maxpat = os.path.join(SOURCE_DIRECTORY, f"{self.script_name}.maxpat")
        with open(maxpat, "w") as handle:
            json.dump(patch, handle, indent="\t")
        amxd = os.path.join(device_directory, f"{self.script_name}.amxd")
        amxd_tool = os.path.join(REPOSITORY_ROOT, "tools", "amxd.py")
        subprocess.run([sys.executable, amxd_tool, "pack", maxpat, amxd, "--type", "instrument"], check=True)
        print(f"wrote {os.path.relpath(maxpat, REPOSITORY_ROOT)} and {os.path.relpath(amxd, REPOSITORY_ROOT)} "
              f"({len(self.boxes)} boxes, {self.device_width}px wide)")
        # the frozen release: one self-contained file with the scripts embedded
        os.makedirs(os.path.join(REPOSITORY_ROOT, "dist"), exist_ok=True)
        frozen = os.path.join(REPOSITORY_ROOT, "dist", f"{self.script_name}-{self.version}.amxd")
        scripts = [os.path.join(device_directory, name) for name in embedded_scripts]
        for script in scripts:
            if not os.path.isfile(script):
                self.fail(f"the frozen release embeds {script}, which wasn't written")
        subprocess.run([sys.executable, amxd_tool, "freeze", maxpat, frozen, "--type", "instrument", "--embed", *scripts],
                       check=True)
        print(f"froze {os.path.relpath(frozen, REPOSITORY_ROOT)} ({os.path.getsize(frozen) // 1024} KB, scripts embedded)")
        return patch

    def check_layout(self):
        """Fails when two things shown at the same time overlap, or one leaves the device: for every page and
        every choice of its group selectors, the header and the page's visible boxes (the background excepted)."""
        shown = [x["box"] for x in self.boxes if x["box"].get("presentation") == 1 and not x["box"].get("background")]
        on_some_page = {n for names in self.pages.values() for n in names}
        problems = []
        for box in shown:
            x, y, w, h = box["presentation_rect"]
            if x < 0 or y < 0 or x + w > self.device_width or y + h > DEVICE_HEIGHT:
                problems.append(f"{box.get('varname', box['id'])} at {box['presentation_rect']} leaves the "
                                f"{self.device_width} x {DEVICE_HEIGHT} device")
        for page in self.page_names:
            selectors = [s for s, g in self.groups.items() if g["page"] == page]
            choices = [[]]
            for selector in selectors:
                choices = [c + [(selector, i)] for c in choices for i in range(len(self.groups[selector]["members"]))]
            for choice in choices:
                hidden = {n for selector, picked in choice
                          for i, members in enumerate(self.groups[selector]["members"]) if i != picked for n in members}
                visible = [b for b in shown if (b.get("varname") not in on_some_page or b["varname"] in self.pages[page])
                           and b.get("varname") not in hidden]
                for i, a in enumerate(visible):
                    ax, ay, aw, ah = a["presentation_rect"]
                    for b in visible[i + 1:]:
                        bx, by, bw, bh = b["presentation_rect"]
                        if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                            problems.append(f"page {page!r} {dict(choice) or ''}: {a.get('varname', a['id'])} "
                                            f"{a['presentation_rect']} overlaps {b.get('varname', b['id'])} "
                                            f"{b['presentation_rect']}")
        if problems:
            self.fail("the layout overlaps:\n  " + "\n  ".join(sorted(set(problems))))

    def messages_for(self, control_values, destination):
        """What `destination` gets from these control values ({control: value}), as {message: value}."""
        sent = {}
        for control_name, route_destination, message, scale in self.control_routes:
            if route_destination == destination and control_name in control_values:
                sent[message] = control_values[control_name] * (scale if scale is not None else 1)
        return sent

    def fill_template(self, template, replacements, what):
        for marker, text in replacements.items():
            if template.count(marker) < 1:
                self.fail(f"{what} has no {marker} marker")
            template = template.replace(marker, text)
        leftover = re.findall(r"/\*[A-Z_]+\*/", template)
        if leftover:
            self.fail(f"{what} still has unfilled markers: {sorted(set(leftover))}")
        return template

    @staticmethod
    def write(path, text):
        with open(path, "w") as handle:
            handle.write(text)

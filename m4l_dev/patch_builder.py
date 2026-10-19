"""DevicePatchBuilder: one Max for Live device's patch, built box by box, with what the build checks recorded.

A device's build makes one builder and calls its helpers: boxes and wires, gen~ patchers (their GenExpr checked by
m4l_dev/genexpr.py), Live parameters (dials, menus, tabs, toggles, number boxes, Stored Only values) with their Info
View text, displays (jsui running the views script), the shared header (2sl link chip, page tabs, optional Preset
menu, output level, Stop), Live's transport and Live Set properties, and the Stop action. m4l_dev/device_build.py
then checks it (`check()`), generates its scripts and writes the device.

Initial values come from the preset book (m4l_dev/preset_book.py): every control the presets set takes its initial
value from the book's Init values. A control given `initial_outside_presets` is saved with the set but presets leave
it alone (a group selector, the Preset menu itself, a device's pattern tools).

A page can hold groups of controls that a selector shows one at a time: a live.tab (`group_selector`), or any
control (`groups_selected_by`). The layout contract is m4l_dev/layout_rules.py's.
"""
import json

from m4l_dev import genexpr
from m4l_dev import layout_rules
from m4l_dev import live_parameter_identity as identity
from m4l_dev.build_error import BuildError
from m4l_dev.generated_scripts import fill_template, kit_template_text
from m4l_dev.preset_book import TOGGLE_ITEMS, SavedControl
from m4l_dev.themes import theme_from_live_js

MAX_APPLICATION_VERSION = {"major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1}
LIVE_OBJECT_OUTLETS = {"live.dial": (2, ["", "float"]), "live.menu": (3, ["", "", "float"]),
                       "live.tab": (3, ["", "", "float"]), "live.text": (2, ["", ""]),
                       "live.numbox": (2, ["", "float"])}
CONTROL_KINDS = ("dial", "text", "menu", "tab", "numbox")    # how the UI script recolours them
INT_PARAMETER_VALUES = 256                                    # Live's Int type holds 0-255 steps


def varname_for(long_name):
    """A control's scripting name, from its long name ("Pump Rate" -> "pump_rate")."""
    return long_name.lower().replace(" ", "_")


def identity_transform(value):
    return value


class DevicePatchBuilder:
    def __init__(self, device_name, script_name, version, subtitle, link_chip_text, device_type, device_width,
                 page_names, info, preset_book):
        """device_name ("2sl stab") names the device in messages and scripts; script_name ("2sl-stab") its files;
        info: {parameter long name or view Info key: (Info View title, text)}; preset_book: a PresetBook."""
        self.device_name = device_name
        self.script_name = script_name
        self.version = version
        self.subtitle = subtitle                    # drawn in the header after the page tabs
        self.link_chip_text = link_chip_text        # the wordmark chip ("2sl stab")
        self.device_type = device_type              # "instrument", "audio" or "midi"
        layout_rules.check_on_grid(f"{script_name}: the device width", device_width)
        self.device_width = device_width
        self.page_names = list(page_names)
        self.info = info
        self.preset_book = preset_book
        self.info_used = set()
        self.boxes, self.lines = [], []
        self.box_count = 0
        self.pages = {name: [] for name in self.page_names}
        self.saved_controls = {}                    # long name -> SavedControl: the controls presets set
        self.initial_values = {}                    # long name -> its initial value as held
        self.groups = {}                            # selector varname -> {"page": page, "members": [[varname]]}
        self.controls_by_kind = {kind: [] for kind in CONTROL_KINDS}
        self.view_varnames = []
        self.control_by_box = {}                    # box id -> (control long name, the value's transform on the way)
        self.view_mode_by_box = {}
        self.view_defaults = {}                     # view mode -> {message: value it gets from the Init values}
        self.gen_param_from_init = []               # (gen box id, Param name, value the Init values send, control)
        self.gen_params_by_box = {}                 # gen~ box id -> {Param name: ParamDecl}
        self.control_routes = []                    # (control, destination box, message, scale)
        self.stop_turns_off = []                    # varnames of controls the Stop action sets to 0
        self.header_boxes = None
        self.live_set_path = None                   # the live.path at live_set, once a Live Set property is observed
        self.live_set_observers = {}

    def fail(self, message):
        raise BuildError(f"{self.device_name}: {message}")

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

    def gen_box(self, code, ins, outs, rect, box_text="gen~", outlet_type="signal"):
        """A gen~ (or `box_text`, e.g. "mc.gen~ @chans 16") holding `code` in a codebox, with `ins` inlets and `outs`
        outlets. The code is checked by m4l_dev/genexpr.py (our GenExpr subset, not Max's compiler). The gen patcher
        gets an [in] / [out] for each inN / outN the code uses (a gen~ keeps one inlet for messages even with none)."""
        try:
            _, program_info = genexpr.analyze(code, num_inputs=ins, num_outputs=outs)
        except genexpr.GenExprError as problem:
            self.fail(f"the gen~ code for {box_text!r} at {rect}: {problem}")
        used_ins = max(program_info.used_inputs or [0])
        used_outs = max(program_info.used_outputs or [0])
        if used_outs != outs:
            self.fail(f"gen~ code uses out1..out{used_outs}, the box was given {outs} outlets")
        box_id = self.box(box_text, rect=rect, ins=max(ins, 1), outs=outs, outtype=[outlet_type] * outs,
                          patcher=self.gen_patcher(code, used_ins, outs))
        self.gen_params_by_box[box_id] = program_info.params
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
        return {"fileversion": 1, "appversion": dict(MAX_APPLICATION_VERSION),
                "classnamespace": "dsp.gen", "rect": [100.0, 100.0, 760.0, 740.0],
                "boxes": sub_boxes, "lines": sub_lines}

    # ---- Live parameters -----------------------------------------------------------------------------

    def initial(self, name, items=None, minimum=None, maximum=None, initial_outside_presets=None):
        """A control's initial value as held: the preset book's Init value (the control is then one presets set), or
        `initial_outside_presets` (as held) for a control presets leave alone."""
        if name in self.initial_values:
            self.fail(f"two controls are called {name!r}")
        if initial_outside_presets is None:
            control = SavedControl(name, varname_for(name), None if items is None else list(items),
                                   0 if items is not None else minimum, len(items) - 1 if items is not None else maximum)
            value = self.preset_book.init_value_as_held(control)
            self.saved_controls[name] = control
        else:
            if self.preset_book.has_init_value(name):
                self.fail(f"{name!r} has an Init value in {self.preset_book.source_name}, so presets set it: "
                          "it can't have its own initial value too")
            value = initial_outside_presets
        self.initial_values[name] = value
        return value

    def live_parameter(self, cls, name, short, rect, kind, prect, **values):
        """A Live parameter shown in presentation at `prect`, with its Info View text from `info`."""
        saved_values = {"parameter_longname": name, "parameter_shortname": short, "parameter_type": kind}
        mode = values.pop("_mode", 1)
        saved_values.update(values)
        annotation = {}
        if name in self.info:
            title, text = self.info[name]
            self.info_used.add(name)
            # Max saves these on the box and mirrors them in the parameter's saved values (as it writes them itself)
            annotation = {"annotation_name": title, "annotation": text}
            saved_values.update(parameter_annotation_name=title, parameter_info=text)
        elif not values.get("parameter_invisible"):
            self.fail(f"parameter {name!r} has no Info View text: add it to the info")
        outlet_count, outlet_types = LIVE_OBJECT_OUTLETS[cls]
        extra = {}
        if cls == "live.text":
            # text / texton are only the button's label; the names Live shows for its two states (automation lanes,
            # Push, presets) are the box's automation / automationon attributes, default "val1" / "val2" (Cycling '74,
            # live.text reference). Max saves them on the box and mirrors them in parameter_enum (references/README.md,
            # "Live presets"): a parameter_enum without them is overridden by the defaults.
            extra = {"text": short.lower(), "texton": short.lower(), "mode": mode,
                     "automation": TOGGLE_ITEMS[0], "automationon": TOGGLE_ITEMS[1]}
            saved_values.update(parameter_enum=list(TOGGLE_ITEMS), parameter_mmax=1)
        box_id = self.box(cls=cls, rect=rect, ins=1, outs=outlet_count, outtype=outlet_types,
                          varname=varname_for(name), parameter_enable=1, presentation=1,
                          presentation_rect=[float(x) for x in prect],
                          saved_attribute_attributes={"valueof": saved_values}, **annotation, **extra)
        self.control_by_box[box_id] = (name, identity_transform)
        return box_id

    def derived(self, box_id, control_name, transform):
        """`box_id` passes on control `control_name`'s value transformed (a [- 1], an [expr] lookup): what it tells a
        display or a gen~ counts as that control's, transformed, for the Init checks."""
        self.control_by_box[box_id] = (control_name, transform)
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
                self.fail(f"{varname!r} is on page {page!r}, its group selector {selector!r} on "
                          f"{self.groups[selector]['page']!r}")
            members = self.groups[selector]["members"]
            if not 0 <= index < len(members):
                self.fail(f"{varname!r}: group {selector!r} has {len(members)} choices, not {index + 1}")
            members[index].append(varname)
            if index != 0:                          # the selector starts on its first choice
                found["hidden"] = 1
        return box_id

    def tell(self, source, message, destination, inlet=0, scale=None):
        """Wire `source`'s value to `destination` as `message value` (or raw when message is None). A control's value
        told a display becomes that display's starting value; told a gen~, it must be the Param's default."""
        if source in self.control_by_box and message is not None:
            control_name, transform = self.control_by_box[source]
            self.control_routes.append((control_name, transform, destination, message, scale))
            if control_name in self.initial_values:
                sent = transform(self.initial_values[control_name]) * (scale if scale is not None else 1)
                if destination in self.view_mode_by_box:
                    self.view_defaults.setdefault(self.view_mode_by_box[destination], {})[message] = sent
                elif destination in self.gen_params_by_box:
                    self.gen_param_from_init.append((destination, message, sent, control_name))
        chain = source
        if scale is not None:
            scaler = self.box(f"* {scale}", rect=(1300, 900 + 2 * len(self.boxes), 50, 22), ins=2, outtype=["float"])
            self.wire(chain, scaler)
            chain = scaler
        if message is None:
            self.wire(chain, destination, 0, inlet)      # the raw value (e.g. into a phasor~)
            return
        prepend = self.box(f"prepend {message}", rect=(1360, 900 + 2 * len(self.boxes), 100, 22))
        self.wire(chain, prepend)
        self.wire(prepend, destination, 0, inlet)

    def dial(self, name, short, target, message, minimum, maximum, unit, x, y, page, exponent=1.0, scale=1.0,
             views=(), group=None, initial_outside_presets=None, integer=False, items=None, inlet=0):
        """A live.dial: a float by default; integer=True Live's Int type (256 values at most); items=[names] an
        enum (minimum, maximum, unit and exponent unused), showing the chosen name. Its value goes to `target` as
        `message value` (scaled by `scale`), and to each (view box, message) in `views`."""
        if integer and maximum - minimum >= INT_PARAMETER_VALUES:
            self.fail(f"dial {name!r}: an Int parameter holds {INT_PARAMETER_VALUES} values, {minimum}..{maximum} has more")
        if items is not None:
            if integer:
                self.fail(f"dial {name!r} is an enum or an Int, not both")
            initial = self.initial(name, items=items, initial_outside_presets=initial_outside_presets)
            kind, values = identity.PARAMETER_TYPE_ENUM, dict(parameter_enum=list(items), parameter_mmax=len(items) - 1)
        else:
            initial = self.initial(name, minimum=minimum, maximum=maximum, initial_outside_presets=initial_outside_presets)
            kind = identity.PARAMETER_TYPE_INT if integer else identity.PARAMETER_TYPE_FLOAT
            values = dict(parameter_mmin=float(minimum), parameter_mmax=float(maximum), parameter_unitstyle=unit,
                          parameter_exponent=float(exponent))
        box_id = self.live_parameter("live.dial", name, short,
                                     (1500 + x, 700 + y, layout_rules.DIAL_WIDTH, layout_rules.DIAL_HEIGHT), kind,
                                     (x, y, layout_rules.DIAL_WIDTH, layout_rules.DIAL_HEIGHT), parameter_initial_enable=1,
                                     parameter_initial=[float(initial) if items is None else initial], **values)
        varname = varname_for(name)
        self.on_page(page, box_id, varname, group)
        self.controls_by_kind["dial"].append(varname)
        self.tell(box_id, message, target, inlet, scale if scale != 1.0 else None)
        for view_box, view_message in views:
            self.tell(box_id, view_message, view_box, 0, scale if scale != 1.0 else None)
        return box_id

    def menu(self, name, short, items, x, y, w, page, initial_outside_presets=None, group=None):
        initial = self.initial(name, items=items, initial_outside_presets=initial_outside_presets)
        box_id = self.live_parameter("live.menu", name, short, (1500 + x, 640 + y, w, layout_rules.ROW_H),
                                     identity.PARAMETER_TYPE_ENUM, (x, y, w, layout_rules.ROW_H),
                                     parameter_enum=list(items), parameter_mmax=len(items) - 1,
                                     parameter_initial_enable=1, parameter_initial=[initial])
        varname = varname_for(name)
        self.controls_by_kind["menu"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def tabs(self, name, short, items, x, y, w, page, initial_outside_presets=None, group=None, rows=1,
             visibility=identity.VISIBILITY_AUTOMATED_AND_STORED):
        """Selector buttons (a live.tab): one enum parameter, a button per item, in `rows` lines of ROW_H. live.tab
        splits each line's width equally; every button must hold its longest name (layout_rules).

        visibility: Live's Parameter Visibility. VISIBILITY_HIDDEN (not saved with the set or in presets, not
        automated, not in Live's undo history: a page or tab switch) needs `initial_outside_presets`, since presets
        can't set what Live doesn't store."""
        problem = layout_rules.live_tab_button_problem(items, w, rows)
        if problem:
            self.fail(f"tabs {name!r}: {problem}")
        if visibility not in (identity.VISIBILITY_AUTOMATED_AND_STORED, identity.VISIBILITY_HIDDEN):
            self.fail(f"tabs {name!r}: visibility {visibility!r} is neither Automated and Stored nor Hidden")
        if visibility == identity.VISIBILITY_HIDDEN and initial_outside_presets is None:
            self.fail(f"tabs {name!r} is Hidden, so presets can't set it: give it initial_outside_presets")
        initial = self.initial(name, items=items, initial_outside_presets=initial_outside_presets)
        height = layout_rules.ROW_H * rows
        hidden = {"parameter_invisible": visibility} if visibility == identity.VISIBILITY_HIDDEN else {}
        box_id = self.live_parameter("live.tab", name, short, (1500 + x, 600 + y, w, height),
                                     identity.PARAMETER_TYPE_ENUM, (x, y, w, height), parameter_enum=list(items),
                                     parameter_mmax=len(items) - 1, parameter_initial_enable=1,
                                     parameter_initial=[initial], **hidden)
        varname = varname_for(name)
        self.find(box_id).update(num_lines_patching=rows, num_lines_presentation=rows)
        self.controls_by_kind["tab"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def groups_selected_by(self, selector_box, choice_count, page):
        """Make `selector_box` (any control whose value is a choice 0..choice_count-1) show one group of boxes on
        `page` at a time; boxes join a group with group=(the selector's varname, i). It starts on its first group,
        so the selector's initial value must be 0."""
        varname = self.find(selector_box)["varname"]
        if varname in self.groups:
            self.fail(f"{varname!r} selects groups twice")
        if self.initial_values.get(self.control_by_box[selector_box][0]) != 0:
            self.fail(f"group selector {varname!r} must start on its first group (initial value 0)")
        self.groups[varname] = {"page": page, "members": [[] for _ in range(choice_count)]}
        self.tell(selector_box, f"group {varname}", self.built_header()["ui"])

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
                           "parameter_initial": [self.initial(name, items=TOGGLE_ITEMS,
                                                              initial_outside_presets=initial_outside_presets)]}
                          if mode == 1 else {})
        box_id = self.live_parameter("live.text", name, short, (1500 + x, 660 + y, w, h), identity.PARAMETER_TYPE_ENUM,
                                     (x, y, w, h), _mode=mode, **initial_values)
        varname = varname_for(name)
        self.controls_by_kind["text"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def numbox(self, name, short, target, message, minimum, maximum, unit, x, y, w, page, integer=False,
               inlet=0, initial_outside_presets=None, group=None):
        """A live.numbox. integer=True: Live's Int type, which holds 256 values at most (see `stored`)."""
        if integer and maximum - minimum >= INT_PARAMETER_VALUES:
            self.fail(f"numbox {name!r}: an Int parameter holds {INT_PARAMETER_VALUES} values, {minimum}..{maximum} has more")
        initial = self.initial(name, minimum=minimum, maximum=maximum, initial_outside_presets=initial_outside_presets)
        box_id = self.live_parameter("live.numbox", name, short, (1500 + x, 680 + y, w, layout_rules.ROW_H),
                                     identity.PARAMETER_TYPE_INT if integer else identity.PARAMETER_TYPE_FLOAT,
                                     (x, y, w, layout_rules.ROW_H), parameter_mmin=float(minimum),
                                     parameter_mmax=float(maximum), parameter_initial_enable=1,
                                     parameter_initial=[float(initial)], parameter_unitstyle=unit)
        varname = varname_for(name)
        self.on_page(page, box_id, varname, group)
        self.controls_by_kind["numbox"].append(varname)
        self.tell(box_id, message, target, inlet)
        return box_id

    def stored(self, name, initial_value):
        """A Stored Only parameter: Live stores it with the set (and a Live preset's blob) but doesn't show or
        automate it. Float type with an Int unit style, 0-65535: Live's Int type holds only 256 values (0-255),
        which would cut a 16-bit value down to its first 8 bits. Cycling '74's param reference gives this pattern
        for bigger integers."""
        if not (0 <= initial_value <= 65535 and initial_value == int(initial_value)):
            self.fail(f"stored value {name!r} starts at {initial_value}, outside the 16-bit range it can hold")
        box_id = self.live_parameter("live.numbox", name, name, (1500, 1400 + (30 * len(self.boxes)) % 300, 60, 15),
                                     identity.PARAMETER_TYPE_FLOAT, (0, 0, 60, 15), parameter_mmin=0.0,
                                     parameter_mmax=65535.0, parameter_initial_enable=1,
                                     parameter_initial=[float(initial_value)], parameter_unitstyle=0,
                                     parameter_invisible=identity.VISIBILITY_STORED_ONLY)
        stored_box = self.find(box_id)
        stored_box["presentation"] = 0
        del stored_box["presentation_rect"]
        return box_id

    # ---- displays ------------------------------------------------------------------------------------

    def view(self, mode, x, y, w, h, page, background=False, info=None, group=None):
        """A display (jsui running the device's views script) in `mode`, with Info View text from `info` (a key of
        the builder's info)."""
        # background=True: Max's "Include in Background", so it always sits behind every other object
        extra = {"ignoreclick": 1, "background": 1} if background else {}
        if info:
            if info not in self.info:
                self.fail(f"view {mode!r} names Info View text {info!r}, which the info doesn't have")
            title, text = self.info[info]
            self.info_used.add(info)
            extra.update(annotation_name=title, annotation=text)
        elif not background:
            # only the background (it ignores clicks, so it is never hovered) may go without
            self.fail(f"view {mode!r} has no Info View text: pass info= with a key of the info")
        box_id = self.box(cls="jsui", rect=(1500 + x, 1000 + y, w, h), ins=1, outs=1,
                          filename=self.views_script_name(), jsarguments=[mode], presentation=1,
                          presentation_rect=[float(x), float(y), float(w), float(h)], border=0, **extra)
        self.view_varnames.append(f"view_{mode}")
        self.view_mode_by_box[box_id] = mode
        return self.on_page(page, box_id, f"view_{mode}", group)

    # ---- the header and the plumbing every device has ---------------------------------------------------

    def ui_script_name(self):
        return f"{self.script_name}-ui.js"

    def views_script_name(self):
        return f"{self.script_name}-view.js"

    def built_header(self):
        """The header's boxes (see `header`); fails if it isn't built yet."""
        if self.header_boxes is None:
            self.fail("build the header (header()) before what wires into it")
        return self.header_boxes

    def header(self, output_level_target, output_level_name, preset_menu=None):
        """The device background, the UI script, the 2sl link chip, page tabs, the Preset menu (preset_menu=(x, w):
        the preset book's presets as a live.menu; None: no menu), the output level and Stop. Built once.

        The output level is a live.numbox, -36 to +12 dB, told to output_level_target as `volume dB`; the device names
        it (`output_level_name`: its long and short name, its Init value's and Info text's key; 2sl stab "Volume",
        2sl gate "Output"). The chrome labels it "out".

        Returns the boxes a device wires further: chrome, ui, thisdevice, ready, page_tabs, preset (or None),
        output_level, stop."""
        if self.header_boxes is not None:
            self.fail("the header is built twice")
        made = {}
        made["chrome"] = self.view("chrome", 0, 0, self.device_width, layout_rules.DEVICE_HEIGHT, None, background=True)
        made["ui"] = self.box(f"js {self.ui_script_name()}", rect=(1100, 30, 120, 22), ins=1, outs=1)
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
        self.header_boxes = made

        # the 2sl wordmark chip, a link back to 2sl.to (hover shows it, click opens it)
        gap, header_y = layout_rules.HEADER_GAP, layout_rules.HEADER_Y
        link_width = layout_rules.link_chip_width(self.link_chip_text)
        self.view("link", gap, header_y, link_width, 15, None, info="Link view")
        # The page switch is Hidden: only a click turns the page, and the device always opens on the first page.
        self.page_tabs_x = gap + link_width + gap
        made["page_tabs"] = self.tabs("Page", "Page", self.page_names, self.page_tabs_x, header_y,
                                      layout_rules.page_tabs_width(self.page_names), None, initial_outside_presets=0,
                                      visibility=identity.VISIBILITY_HIDDEN)
        self.tell(made["page_tabs"], "page", made["ui"])
        self.tell(made["page_tabs"], "page", made["chrome"])
        self.preset_menu_x = None
        made["preset"] = None
        if preset_menu is not None:
            self.preset_menu_x, preset_menu_width = preset_menu
            made["preset"] = self.menu("Preset", "Preset", ["-"], self.preset_menu_x, header_y, preset_menu_width, None,
                                       initial_outside_presets=0)  # items: the preset book's, set by check()
            self.wire(made["preset"], made["ui"])
        # the right end of the header: out (the output level) and Stop, 12 px from the device's edge
        self.output_level_x = self.device_width - 136
        output_level_initial = self.initial(output_level_name, minimum=-36.0, maximum=12.0)
        made["output_level"] = self.live_parameter("live.numbox", output_level_name, output_level_name,
                                                   (1500, 520, 64, 15), identity.PARAMETER_TYPE_FLOAT,
                                                   (float(self.output_level_x), float(header_y), 64.0, 15.0),
                                                   parameter_mmin=-36.0, parameter_mmax=12.0,
                                                   parameter_initial_enable=1,
                                                   parameter_initial=[float(output_level_initial)],
                                                   parameter_unitstyle=4)
        output_level_varname = varname_for(output_level_name)
        self.find(made["output_level"]).update(varname=output_level_varname)
        self.controls_by_kind["numbox"].append(output_level_varname)
        self.tell(made["output_level"], "volume", output_level_target)
        made["stop"] = self.live_parameter("live.text", "Stop", "Stop", (1500, 540, 48, 15),
                                           identity.PARAMETER_TYPE_ENUM,
                                           (float(self.device_width - 60), float(header_y), 48.0, 15.0), _mode=0)
        self.find(made["stop"]).update(varname="stop")
        self.controls_by_kind["text"].append("stop")
        return made

    def header_labels(self):
        """The header's labels, drawn by the chrome on every page: "preset" before the Preset menu, "out" before
        the output level (text, x, baseline, kind)."""
        labels = []
        if self.preset_menu_x is not None:
            labels.append(["preset", self.preset_menu_x - 40, 15, "label"])
        labels.append(["out", self.output_level_x - 24, 15, "label"])
        return labels

    def live_set_observer(self, property_name):
        """A live.observer of the Live Set's `property_name` (Live Object Model, Song), started when the device
        loads; its left outlet gives the value. One shared live.path; one observer per property."""
        if property_name in self.live_set_observers:
            return self.live_set_observers[property_name]
        if self.live_set_path is None:
            self.live_set_start = self.box("t b b", rect=(420, 60, 40, 22), outs=2, outtype=["bang", "bang"])
            self.wire(self.built_header()["thisdevice"], self.live_set_start)
            path_message = self.box(cls="message", text="path live_set", rect=(420, 90, 90, 22), ins=2, outs=1)
            self.live_set_path = self.box("live.path", rect=(420, 120, 70, 22), ins=1, outs=3)
            # the trigger fires right to left: every observer gets its property first, then the path
            self.wire(self.live_set_start, path_message, 0, 0)
            self.wire(path_message, self.live_set_path)
        column = len(self.live_set_observers)
        property_message = self.box(cls="message", text=f"property {property_name}",
                                    rect=(520 + 160 * column, 90, 140, 22), ins=2, outs=1)
        observer = self.box("live.observer", rect=(520 + 160 * column, 150, 90, 22), ins=2, outs=2)
        self.wire(self.live_set_start, property_message, 1, 0)
        self.wire(property_message, observer)
        self.wire(self.live_set_path, observer, 0, 1)
        self.live_set_observers[property_name] = observer
        return observer

    def live_transport(self, brain, brain_inlet, also_tell_playing=()):
        """Live's tempo and transport, and the 16th clock, for the brain (templates/transport-clock.template.js).

        The brain gets `tempo f`, `playing i` and, on every 16th while Live plays, `tick <song position in ticks>`
        (480 per quarter note): a [metro 16n @quantize 16n] bang asks [transport] for the position. Live playing or
        not arrives in a set order (trigger: right to left): the brain first, then each (destination, message) of
        `also_tell_playing` in turn, and only then does the metro start, so its immediate bang finds the brain
        playing. Returns the observers: {"tempo", "is_playing"} (the tempo's left outlet gives Live's BPM)."""
        observers = {name: self.live_set_observer(name) for name in ("tempo", "is_playing")}
        tempo_to_brain = self.box("prepend tempo", rect=(520, 250, 90, 22))
        self.wire(observers["tempo"], tempo_to_brain)
        self.wire(tempo_to_brain, brain, 0, brain_inlet)
        metro = self.box("metro 16n @quantize 16n", rect=(30, 520, 160, 22), ins=2, outs=1, outtype=["bang"])
        listener_count = 2 + len(also_tell_playing)
        playing_order = self.box("t" + " i" * listener_count, rect=(940, 210, 60, 22), ins=1, outs=listener_count,
                                 outtype=["int"] * listener_count)
        self.wire(observers["is_playing"], playing_order)
        playing_to_brain = self.box("prepend playing", rect=(940, 240, 100, 22))
        self.wire(playing_order, playing_to_brain, listener_count - 1, 0)
        self.wire(playing_to_brain, brain, 0, brain_inlet)
        for order, (destination, message) in enumerate(also_tell_playing):
            playing_to_listener = self.box(f"prepend {message}", rect=(720 + 120 * order, 250, 110, 22))
            self.wire(playing_order, playing_to_listener, listener_count - 2 - order, 0)
            self.wire(playing_to_listener, destination)
        self.wire(playing_order, metro, 0, 0)
        transport = self.box("transport", rect=(30, 550, 70, 22), ins=2, outs=9)
        tick_message = self.box("prepend tick", rect=(30, 610, 80, 22))
        self.wire(metro, transport)
        self.wire(transport, tick_message, 7, 0)          # raw ticks: 480 per quarter note
        self.wire(tick_message, brain, 0, brain_inlet)
        return observers

    def stop_action(self, brain, brain_inlet, panic_destinations):
        """The header's Stop button: `stop` to the brain and the UI script (which sets every control given to
        `turned_off_by_stop` to 0), then a new `panic <count>` number to each of `panic_destinations` (a gen~ ramps
        to silence on every new number). Live's transport stopping doesn't run it."""
        header = self.built_header()
        stop_order = self.box("t b b", rect=(1100, 200, 40, 22), outs=2, outtype=["bang", "bang"])
        stop_message = self.box(cls="message", text="stop", rect=(1230, 230, 40, 22), ins=2, outs=1)
        panic_counter = self.box("counter 1 1000000", rect=(1100, 230, 110, 22), ins=3, outs=4,
                                 outtype=["int", "", "", "int"])
        panic_message = self.box("prepend panic", rect=(1100, 260, 90, 22))
        self.wire(header["stop"], stop_order)
        self.wire(stop_order, stop_message, 1, 0)
        self.wire(stop_message, brain, 0, brain_inlet)
        self.wire(stop_message, header["ui"])
        self.wire(stop_order, panic_counter, 0, 0)
        self.wire(panic_counter, panic_message)
        for destination in panic_destinations:
            self.wire(panic_message, destination)

    def turned_off_by_stop(self, control_box):
        """The Stop action sets this control to 0 (2sl stab: Freeze)."""
        self.stop_turns_off.append(self.find(control_box)["varname"])

    # ---- checks -------------------------------------------------------------------------------------------

    def check(self):
        """Every check of the patch as built; returns the presets ([Preset], every saved control set). Fills in the
        Preset menu's items. Fails on the first broken rule, saying what to fix."""
        self.built_header()
        presets = self.preset_book.presets_as_held(self.saved_controls)
        if self.header_boxes["preset"] is not None:
            preset_values = self.find(self.header_boxes["preset"])["saved_attribute_attributes"]["valueof"]
            preset_values.update(parameter_enum=[preset.name for preset in presets], parameter_mmax=len(presets) - 1)
        self.check_gen_param_defaults()
        problems = layout_rules.overlap_problems(
            [x["box"] for x in self.boxes if x["box"].get("presentation") == 1 and not x["box"].get("background")],
            self.page_names, self.pages, self.groups, self.device_width)
        if problems:
            self.fail("the layout overlaps:\n  " + "\n  ".join(problems))
        self.check_controls_hold_their_text()
        if set(self.info) - self.info_used:
            self.fail(f"the info has text for no parameter or view: {sorted(set(self.info) - self.info_used)}")
        self.check_script_lookups()
        self.check_wires()
        return presets

    def check_controls_hold_their_text(self):
        """Every shown live.dial holds its short name, live.menu its longest item, live.text its text
        (layout_rules.live_text_problem). A box taller than a dial (a pad) has room to spare and isn't checked."""
        problems = []
        for entry in self.boxes:
            box = entry["box"]
            values = box.get("saved_attribute_attributes", {}).get("valueof")
            if not (box.get("parameter_enable") and values and box.get("presentation") == 1):
                continue
            width, height = box["presentation_rect"][2], box["presentation_rect"][3]
            if height > layout_rules.DIAL_HEIGHT:
                continue
            problem = layout_rules.live_text_problem(box["maxclass"], values["parameter_shortname"],
                                                     values.get("parameter_enum", []), box.get("text", ""), width)
            if problem:
                problems.append(f"{values['parameter_longname']} ({box['maxclass']}) is {problem}")
        if problems:
            self.fail("controls too narrow for their text:\n  " + "\n  ".join(problems))

    def check_gen_param_defaults(self):
        """The gen~ Param defaults must be what the Init values send them (the sound before Live recalls the
        controls)."""
        mismatches = []
        for gen_box_id, param_name, sent, control_name in self.gen_param_from_init:
            declared = self.gen_params_by_box[gen_box_id].get(param_name)
            if declared is None:
                mismatches.append(f"{control_name} -> {param_name}: no such Param")
            elif abs(declared.default - sent) > 1e-9:
                mismatches.append(f"{control_name} -> Param {param_name}({declared.default:g}), the Init values send "
                                  f"{sent:g}")
        if mismatches:
            self.fail("gen~ Param defaults disagree with the Init values:\n  " + "\n  ".join(mismatches))

    def ui_lookups(self):
        """Every scripting name the UI script looks up."""
        return ({control.varname for control in self.saved_controls.values()}
                | {n for names in self.controls_by_kind.values() for n in names} | set(self.view_varnames)
                | {n for names in self.pages.values() for n in names} | set(self.stop_turns_off))

    def check_script_lookups(self):
        """Every name the UI script looks up must name exactly one box (it errors at run time otherwise)."""
        box_varnames = [x["box"]["varname"] for x in self.boxes if "varname" in x["box"]]
        missing = self.ui_lookups() - set(box_varnames)
        if missing:
            self.fail(f"the UI script looks up names no box has: {sorted(missing)}")
        if len(box_varnames) != len(set(box_varnames)):
            self.fail(f"varnames used twice: {sorted({n for n in box_varnames if box_varnames.count(n) > 1})}")

    def check_wires(self):
        """Every wire leaves an outlet its box has and enters an inlet its box has."""
        boxes_by_id = {x["box"]["id"]: x["box"] for x in self.boxes}
        bad_wires = []
        for line in self.lines:
            (source, outlet_index), (destination, inlet_index) = (line["patchline"]["source"],
                                                                  line["patchline"]["destination"])
            if outlet_index >= boxes_by_id[source]["numoutlets"]:
                bad_wires.append(f"{boxes_by_id[source].get('text', boxes_by_id[source]['maxclass'])} has no outlet "
                                 f"{outlet_index}")
            if inlet_index >= boxes_by_id[destination]["numinlets"]:
                bad_wires.append(f"{boxes_by_id[destination].get('text', boxes_by_id[destination]['maxclass'])} has "
                                 f"no inlet {inlet_index}")
        if bad_wires:
            self.fail("wires to outlets or inlets that don't exist:\n  " + "\n  ".join(bad_wires))

    # ---- what the build writes ------------------------------------------------------------------------------

    def patch(self):
        return {"patcher": {
            "fileversion": 1, "appversion": dict(MAX_APPLICATION_VERSION),
            "classnamespace": "box", "rect": [80.0, 80.0, 1300.0, 900.0],
            "openinpresentation": 1, "devicewidth": float(self.device_width),
            "boxes": self.boxes, "lines": self.lines,
        }}

    def ui_script(self, presets):
        """The UI script (templates/ui-script.template.js): pages, groups, the Preset menu, Stop, the theme."""
        presets_for_menu = []
        if self.header_boxes["preset"] is not None:
            presets_for_menu = [{self.saved_controls[name].varname: value for name, value in preset.values.items()}
                                for preset in presets]
        return fill_template(kit_template_text("ui-script.template.js"), {
            "DEVICE_NAME": json.dumps(self.device_name), "SCRIPT_NAME": self.script_name,
            "PAGE_NAMES": json.dumps(self.page_names), "PAGES": json.dumps(self.pages),
            "PRESETS": json.dumps(presets_for_menu, indent=1), "CONTROLS": json.dumps(self.controls_by_kind),
            "GROUPS": json.dumps(self.groups), "VIEWS": json.dumps(self.view_varnames),
            "STOP_TURNS_OFF": json.dumps(self.stop_turns_off), "THEME_FROM_LIVE": theme_from_live_js()},
            "the kit's UI script template")

    def views_script(self, layout, device_views_code):
        """The views script (templates/views.template.js): the chrome and link chip, the drawing helpers, and the
        device's own displays (`device_views_code`, ES5). layout: {"subtitle": x, "pages": [{"rules": [x], "labels":
        [[text, x, baseline, "label" | "hint"]]}]}, one page per page name; the header's labels are added to each."""
        if len(layout.get("pages", [])) != len(self.page_names):
            self.fail(f"the layout has {len(layout.get('pages', []))} pages, the device {len(self.page_names)}")
        layout = dict(layout, subtitle_text=self.subtitle, version=self.version, link_chip_text=self.link_chip_text,
                      pages=[dict(page, labels=self.header_labels() + list(page["labels"])) for page in layout["pages"]])
        return fill_template(kit_template_text("views.template.js"), {
            "DEVICE_NAME": json.dumps(self.device_name), "SCRIPT_NAME": self.script_name,
            "COZETTE": kit_template_text("cozette-glyphs.js").strip(), "THEME_FROM_LIVE": theme_from_live_js(),
            "VIEW_DEFAULTS": json.dumps(self.view_defaults), "LAYOUT": "var LAYOUT = " + json.dumps(layout) + ";",
            "DEVICE_VIEWS": device_views_code.strip()}, "the kit's views script template")

    def messages_for(self, control_values, destination):
        """What `destination` gets from these control values ({control: value}), as {message: value}."""
        sent = {}
        for control_name, transform, route_destination, message, scale in self.control_routes:
            if route_destination == destination and control_name in control_values:
                sent[message] = transform(control_values[control_name]) * (scale if scale is not None else 1)
        return sent

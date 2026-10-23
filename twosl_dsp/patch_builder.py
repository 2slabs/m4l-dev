"""DevicePatchBuilder: one Max for Live device's patch, built box by box, with what the build checks recorded.

A device's build makes one builder and calls its helpers: boxes and wires, gen~ patchers (their GenExpr checked by
twosl_dsp/genexpr.py), Live parameters (dials, menus, tabs, toggles, number boxes, Stored Only values) with their Info
View text, displays (jsui running the views script), the shared header (2sl link chip, page tabs, optional Preset
menu, output level, Stop), Live's transport and Live Set properties, and the Stop action. twosl_dsp/device_build.py
then checks it (`check(layout)`), generates its scripts and writes the device.

Two values per control, both from the preset book (twosl_dsp/preset_book.py) (architecture/presets.md, "Neutral, Init,
and a fresh device"):
  - its **neutral** value: Live's initial value (`parameter_initial`), what a double-click sets it to: the value that
    takes it out of the sound. Every control a user can double-click declares one in the book's "neutral"; the kit
    declares its own (the output level's unity, the Preset menu's and a group selector's first item). A Hidden
    control (never saved: it loads at its initial value every time) has its start value as its neutral, or the kit's
    (a stored table editor's: its field's neutral).
  - its **start** value: what a fresh device starts at. A control the presets set starts at the book's Init value; a
    control given `initial_outside_presets` is saved with the set but presets leave it alone (a group selector, the
    Preset menu itself, a device's pattern tools) and starts there. The gen~ Params' defaults, the displays' starting
    values and the tempo pairs are the start values.
A fresh device loads at the neutral values (Live's), and the UI script moves every saved control whose start value
differs to it once, on its first ready, then sets the Stored Only "Init Applied" flag (FRESH_START_FLAG_NAME) so a
saved set or a preset (the flag 1 in it) is never overridden.

A gen~ Param a control sets has no default in the device's GenExpr (`Param cutoff(min=40, max=12000);`): the build
writes it, the value the initial values send that Param (`write_gen_param_defaults`), so the Init values are its one
source. A Param no control sets (Stop's panic, Live's tempo from the brain) keeps the default its code writes.

The device's latency (`latency_samples`, required): its Defined Latency, a whole number of samples, the patcher's
`"latency"`, which Live's delay compensation takes (references/README.md, "Defined Latency"). It is the device
latency rule's figure (architecture/overview.md, "Defined Latency"; twosl_dsp/techniques/defined_latency_pad.py):
`DefinedLatency({path: the sum of its blocks' latency_samples}).declared_latency_samples`, the latest path rounded
up, every path padded to it; never typed, never rounded here (a fraction fails the build: it would be rounded
somewhere no test sees). A device with no delay declares 0.

A page can hold groups of controls that a selector shows one at a time: a live.tab (`group_selector`), or any
control (`groups_selected_by`). The layout contract is twosl_dsp/layout_rules.py's.
"""
import json
import re

from twosl_dsp import genexpr
from twosl_dsp import layout_rules
from twosl_dsp import live_parameter_identity as identity
from twosl_dsp.build_error import BuildError
from twosl_dsp.display_text import display_paints
from twosl_dsp.generated_numbers import generated_number
from twosl_dsp.generated_scripts import fill_template, kit_template_text
from twosl_dsp.max_time_values import check_note_values_in_box_text
from twosl_dsp.script_outlet_calls import outlet_calls
from twosl_dsp.preset_book import TOGGLE_ITEMS, SavedControl, SavedRecord, stored_only_values_of_preset
from twosl_dsp.themes import theme_from_live_js

# what a tempo-synced time (tempo_synced_milliseconds) is computed at before Live tells the tempo: the [pak]'s initial
# tempo, so the gen~ Param default it writes too
TEMPO_BEFORE_LIVE_SAYS = 120
MAX_APPLICATION_VERSION = {"major": 9, "minor": 1, "revision": 5, "architecture": "x64", "modernui": 1}
LIVE_OBJECT_OUTLETS = {"live.dial": (2, ["", "float"]), "live.menu": (3, ["", "", "float"]),
                       "live.tab": (3, ["", "", "float"]), "live.text": (2, ["", ""]),
                       "live.numbox": (2, ["", "float"])}
CONTROL_KINDS = ("dial", "text", "menu", "tab", "numbox")    # how the UI script recolours them
INT_PARAMETER_VALUES = 256                                    # Live's Int type holds 0-255 steps
# The Stored Only flag a fresh device starts at 0 and the UI script sets to 1 once it has moved the controls to their
# start values (the Init sound): saved with the set and in every preset, so a set or preset reopened is left alone.
FRESH_START_FLAG_NAME = "Init Applied"
# how far a float control's value may sit from its neutral and still count as "at neutral" (a fraction of its range):
# Live keeps a float parameter's value as a position (live_parameter_identity.py), so a recalled value may be off by
# a last bit
NEUTRAL_TOLERANCE_OF_RANGE = 1e-4


def varname_for(long_name):
    """A control's scripting name, from its long name ("Pump Rate" -> "pump_rate")."""
    return long_name.lower().replace(" ", "_")


def identity_transform(value):
    return value


def sent_text(value):
    """A value sent a display, as a problem names it: a number, or a message's several numbers."""
    return " ".join(f"{v:g}" for v in value) if isinstance(value, list) else f"{value:g}"


class DevicePatchBuilder:
    def __init__(self, device_name, script_name, version, subtitle, link_chip_text, device_type, device_width,
                 page_names, info, preset_book, latency_samples):
        """device_name ("2sl stab") names the device in messages and scripts; script_name ("2sl-stab") its files;
        info: {parameter long name or view Info key: (Info View title, text)}; preset_book: a PresetBook;
        latency_samples: the device's Defined Latency, a whole number of samples >= 0 (an int: the rule's
        `DefinedLatency.declared_latency_samples`)."""
        self.device_name = device_name
        self.script_name = script_name
        self.version = version
        self.subtitle = subtitle                    # drawn in the header after the page tabs
        self.link_chip_text = link_chip_text        # the wordmark chip ("2sl stab")
        self.device_type = device_type              # "instrument", "audio" or "midi"
        layout_rules.check_on_grid(f"{script_name}: the device width", device_width)
        self.device_width = device_width
        if isinstance(latency_samples, bool) or not isinstance(latency_samples, int) or latency_samples < 0:
            raise BuildError(f"{device_name}: latency_samples is the device's Defined Latency, a whole number of "
                             f"samples >= 0 (an int: DefinedLatency(...).declared_latency_samples, the latest path "
                             f"rounded up with every path padded to it; 0 for none); got {latency_samples!r}")
        self.latency_samples = latency_samples
        self.page_names = list(page_names)
        self.info = dict(info)                     # its own copy: blocks add their controls' text to it
        self.preset_book = preset_book
        self.info_used = set()
        self.boxes, self.lines = [], []
        self.boxes_by_id = {}                       # box id -> [box] (a list: find() names an id given twice)
        self.box_count = 0
        self.pages = {name: [] for name in self.page_names}
        self.saved_controls = {}                    # long name -> SavedControl: the controls presets set
        self.initial_values = {}                    # long name -> its start value as held (Init, or its own)
        self.neutral_values = {}                    # long name -> its neutral value as held (Live's initial value)
        self.neutral_names_asked = set()            # every name whose neutral the preset book was asked for
        self.neutral_by_varname = {}                # saved control's varname -> [neutral as held, tolerance]
        self.fresh_start_by_varname = {}            # saved control's varname -> its start value, where not neutral
        self.groups = {}                            # selector varname -> {"page": page, "members": [[varname]]}
        self.controls_by_kind = {kind: [] for kind in CONTROL_KINDS}
        self.view_varnames = []
        self.control_by_box = {}                    # box id -> (control long name, the value's transform on the way)
        self.view_mode_by_box = {}
        self.view_defaults = {}                     # view mode -> {message: value it gets from the Init values}
        self.view_readings = {}                     # view box id -> [(message, [values])]: what else it shows
        self.gen_param_from_init = []               # (gen box id, Param name, value the initial values send, control)
        self.gen_params_by_box = {}                 # gen~ box id -> {Param name: ParamDecl} of the code as given
        self.gen_code_by_box = {}                   # gen~ box id -> its code as given (defaults left out)
        # script box id -> {outlet expression a block's code sends from (stored tables: "spec.outlet"): [(outlet
        # index, the block)]}: the outlets an `outlet(<expression>, ...)` the script's text can't resolve reaches
        self.script_outlets_of_blocks = {}
        self.control_routes = []                    # (control, transform, destination box, message or None, scale)
        self.tempo_routes = []                      # (control, beats of its value as held, destination box, message)
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
        if cls == "newobj" and text is not None:
            check_note_values_in_box_text(text, f"{self.device_name}: box {new_box['id']}")
        self.boxes.append({"box": new_box})
        self.boxes_by_id.setdefault(new_box["id"], []).append(new_box)
        return new_box["id"]

    def wire(self, source, destination, source_outlet=0, destination_inlet=0):
        for end in (source, destination):
            if end not in self.boxes_by_id:
                self.fail(f"a wire names box {end!r}, which doesn't exist")
        self.lines.append({"patchline": {"source": [source, source_outlet],
                                         "destination": [destination, destination_inlet]}})

    def find(self, box_id):
        found = self.boxes_by_id.get(box_id, [])
        if len(found) != 1:
            self.fail(f"box {box_id!r} found {len(found)} times")
        return found[0]

    def gen_box(self, code, ins, outs, rect, box_text="gen~", outlet_type="signal"):
        """A gen~ (or `box_text`, e.g. "mc.gen~ @chans 16") holding `code` in a codebox, with `ins` inlets and `outs`
        outlets. The code is checked by twosl_dsp/genexpr.py (our GenExpr subset, not Max's compiler). The gen patcher
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
        return {"fileversion": 1, "appversion": dict(MAX_APPLICATION_VERSION),
                "classnamespace": "dsp.gen", "rect": [100.0, 100.0, 760.0, 740.0],
                "boxes": sub_boxes, "lines": sub_lines}

    # ---- Live parameters -----------------------------------------------------------------------------

    def initial(self, name, items=None, minimum=None, maximum=None, initial_outside_presets=None,
                visibility=identity.VISIBILITY_AUTOMATED_AND_STORED, kit_neutral=None):
        """A control's neutral value as held, Live's initial value (the double-click target): the preset book's
        neutral value; the kit's (`kit_neutral`) for a control the kit makes; a Hidden control's start value unless
        the kit gives one. Records its start value: the preset book's Init value (the control is then one presets
        set), or `initial_outside_presets` (as held) for a control presets leave alone. A saved control whose start
        differs from its neutral is moved there on a fresh device's first ready (the UI script)."""
        if name in self.initial_values:
            self.fail(f"two controls are called {name!r}")
        control = SavedControl(name, varname_for(name), None if items is None else list(items),
                               0 if items is not None else minimum, len(items) - 1 if items is not None else maximum)
        if initial_outside_presets is None:
            start = self.preset_book.init_value_as_held(control)
            self.saved_controls[name] = control
        else:
            if self.preset_book.has_init_value(name):
                self.fail(f"{name!r} has an Init value in {self.preset_book.source_name}, so presets set it: "
                          "it can't have its own initial value too")
            start = initial_outside_presets
        hidden = visibility == identity.VISIBILITY_HIDDEN
        if kit_neutral is not None or hidden:
            if self.preset_book.has_neutral_value(name):
                self.fail(f"{name!r} has a neutral value in {self.preset_book.source_name}, but "
                          + ("the kit declares its neutral" if kit_neutral is not None else
                             "it is Hidden (never saved, it loads at its initial value every time): its start value "
                             "is its neutral")
                          + ": leave it out of 'neutral'")
            neutral = kit_neutral if kit_neutral is not None else start
        else:
            self.neutral_names_asked.add(name)
            neutral = self.preset_book.neutral_value_as_held(control)
        self.initial_values[name] = start
        self.neutral_values[name] = neutral
        if not hidden:
            varname = varname_for(name)
            tolerance = 0 if items is not None else NEUTRAL_TOLERANCE_OF_RANGE * (maximum - minimum)
            self.neutral_by_varname[varname] = [neutral, generated_number(tolerance)]
            if start != neutral:
                self.fresh_start_by_varname[varname] = start
        return neutral

    def neutral_of_record(self, record):
        """A saved record's neutral value, {field name: value in its field's own units}, from the preset book: its
        editors' double-click targets. Asked only by a record with editors."""
        self.neutral_names_asked.add(record.name)
        neutral = self.preset_book.neutral_value_in_own_units(record.name)
        if not isinstance(neutral, dict):
            self.fail(f"{record.name!r}'s neutral value in {self.preset_book.source_name} must be "
                      f"{{field: value}}, not {neutral!r}")
        return neutral

    def saved_record(self, record, initial_outside_presets=None):
        """Register a saved record (a stored table, twosl_dsp/stored_table.py): it reaches Live as its Stored Only
        parameters. Presets set it like a control and its Init value is the preset book's; or, given
        `initial_outside_presets` (in its own units, every field), that is its initial value and presets leave it
        alone, as a control's initial_outside_presets. Returns its initial value as held."""
        if not isinstance(record, SavedRecord):
            self.fail(f"saved_record of {record!r}, which is no SavedRecord")
        if record.name in self.initial_values:
            self.fail(f"two controls are called {record.name!r}")
        if initial_outside_presets is None:
            value = self.preset_book.init_value_as_held(record)
            self.saved_controls[record.name] = record
        else:
            if self.preset_book.has_init_value(record.name):
                self.fail(f"{record.name!r} has an Init value in {self.preset_book.source_name}, so presets set it: "
                          "it can't have its own initial value too")
            value = record.held_from_own_units(initial_outside_presets, f"{record.name}'s initial_outside_presets",
                                               None)
        self.initial_values[record.name] = value
        return value

    def visibility_values(self, what, name, visibility, initial_outside_presets):
        """The saved values for Live's Parameter Visibility `visibility` of a shown control: Automated and Stored (the
        default, which Max leaves out) or Hidden (not saved with the set or in presets, not automated, not in Live's
        undo history: a page or tab switch, or a control the patch drives itself, like a stored table's editors).
        Hidden needs `initial_outside_presets`, since presets can't set what Live doesn't store."""
        if visibility not in (identity.VISIBILITY_AUTOMATED_AND_STORED, identity.VISIBILITY_HIDDEN):
            self.fail(f"{what} {name!r}: visibility {visibility!r} is neither Automated and Stored nor Hidden")
        if visibility == identity.VISIBILITY_HIDDEN and initial_outside_presets is None:
            self.fail(f"{what} {name!r} is Hidden, so presets can't set it: give it initial_outside_presets")
        return {"parameter_invisible": visibility} if visibility == identity.VISIBILITY_HIDDEN else {}

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
        told a display becomes that display's starting value; told a gen~, the Param's default (the build writes it
        into the code: write_gen_param_defaults), both through generated_number. Every
        control's route is recorded for messages_for (a raw value as the message None)."""
        if source in self.control_by_box:
            control_name, transform = self.control_by_box[source]
            self.control_routes.append((control_name, transform, destination, message, scale))
        if source in self.control_by_box and message is not None:
            control_name, transform = self.control_by_box[source]
            if control_name in self.initial_values:
                sent = generated_number(transform(self.initial_values[control_name]) * (scale if scale is not None else 1))
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

    def menu_lookup(self, control, values):
        """A box passing on `values[index]` for `control`'s menu index (an [expr]): a value derived from the control
        (`derived`), so what it tells counts as the control's. Returns the box."""
        if control not in self.control_by_box:
            self.fail(f"menu_lookup of box {control}, which is no control's")
        control_name, transform = self.control_by_box[control]
        values = [generated_number(float(value)) for value in values]
        expression = "expr " + " + ".join(f"($i1=={index})*{value!r}" for index, value in enumerate(values))
        looked_up = self.derived(self.box(expression, rect=(1100, 1400 + 2 * len(self.boxes), 400, 22)), control_name,
                                 lambda held: values[int(transform(held))])
        self.wire(control, looked_up)
        return looked_up

    def tempo_synced_milliseconds(self, control, beats_by_item, tempo, message, destination):
        """`control`'s menu item as a time at Live's tempo, told `destination` as `message ms`:
        beats_by_item[item] x 60000 / tempo. `tempo`: a box putting out Live's tempo (live_set_observer("tempo")).
        messages_for gives it at the tempo it is asked for."""
        control_name, transform = self.control_by_box[control]
        if control_name not in self.initial_values:
            self.fail(f"tempo_synced_milliseconds: {control_name!r} has no initial value yet")
        beats = self.menu_lookup(control, beats_by_item)
        initial_beats = float(beats_by_item[int(transform(self.initial_values[control_name]))])
        y = 1400 + 2 * len(self.boxes)
        pair = self.box(f"pak {TEMPO_BEFORE_LIVE_SAYS}. {initial_beats!r}", rect=(1550, y, 90, 22), ins=2, outs=1)
        milliseconds = self.box("expr 60000. / $f1 * $f2", rect=(1650, y, 150, 22), ins=2, outs=1)
        prepend = self.box(f"prepend {message}", rect=(1810, y, 110, 22))
        self.wire(tempo, pair, 0, 0)
        self.wire(beats, pair, 0, 1)
        self.wire(pair, milliseconds)
        self.wire(milliseconds, prepend)
        self.wire(prepend, destination)
        self.tempo_routes.append((control_name, lambda held: float(beats_by_item[int(transform(held))]), destination,
                                  message))
        if destination in self.gen_params_by_box:
            self.gen_param_from_init.append((destination, message, initial_beats * 60000 / TEMPO_BEFORE_LIVE_SAYS,
                                             control_name))
        return prepend

    def dial(self, name, short, target, message, minimum, maximum, unit, x, y, page, exponent=1.0, scale=1.0,
             views=(), group=None, initial_outside_presets=None, integer=False, items=None, inlet=0,
             visibility=identity.VISIBILITY_AUTOMATED_AND_STORED, width=layout_rules.DIAL_WIDTH, kit_neutral=None):
        """A live.dial: a float by default; integer=True Live's Int type (256 values at most); items=[names] an
        enum (minimum, maximum, unit and exponent unused), showing the chosen name. Its value goes to `target` as
        `message value` (scaled by `scale`), and to each (view box, message) in `views`. visibility: see
        `visibility_values`. kit_neutral: for a control the kit makes, its neutral (see `initial`). width: DIAL_WIDTH, or wider for a short name that needs it
        (layout_rules.live_dial_width(short)); on the grid."""
        if width < layout_rules.DIAL_WIDTH or width % layout_rules.GRID:
            self.fail(f"dial {name!r} is {width!r} px wide: at least {layout_rules.DIAL_WIDTH}, on the "
                      f"{layout_rules.GRID} px grid")
        hidden = self.visibility_values("dial", name, visibility, initial_outside_presets)
        if integer and maximum - minimum >= INT_PARAMETER_VALUES:
            self.fail(f"dial {name!r}: an Int parameter holds {INT_PARAMETER_VALUES} values, {minimum}..{maximum} has more")
        if items is not None:
            if integer:
                self.fail(f"dial {name!r} is an enum or an Int, not both")
            initial = self.initial(name, items=items, initial_outside_presets=initial_outside_presets,
                                   visibility=visibility, kit_neutral=kit_neutral)
            kind, values = identity.PARAMETER_TYPE_ENUM, dict(parameter_enum=list(items), parameter_mmax=len(items) - 1)
        else:
            initial = self.initial(name, minimum=minimum, maximum=maximum, initial_outside_presets=initial_outside_presets,
                                   visibility=visibility, kit_neutral=kit_neutral)
            kind = identity.PARAMETER_TYPE_INT if integer else identity.PARAMETER_TYPE_FLOAT
            values = dict(parameter_mmin=float(minimum), parameter_mmax=float(maximum), parameter_unitstyle=unit,
                          parameter_exponent=float(exponent))
        box_id = self.live_parameter("live.dial", name, short,
                                     (1500 + x, 700 + y, width, layout_rules.DIAL_HEIGHT), kind,
                                     (x, y, width, layout_rules.DIAL_HEIGHT), parameter_initial_enable=1,
                                     parameter_initial=[float(initial) if items is None else initial], **values,
                                     **hidden)
        varname = varname_for(name)
        self.on_page(page, box_id, varname, group)
        self.controls_by_kind["dial"].append(varname)
        self.tell(box_id, message, target, inlet, scale if scale != 1.0 else None)
        for view_box, view_message in views:
            self.tell(box_id, view_message, view_box, 0, scale if scale != 1.0 else None)
        return box_id

    def menu(self, name, short, items, x, y, w, page, initial_outside_presets=None, group=None,
             visibility=identity.VISIBILITY_AUTOMATED_AND_STORED, kit_neutral=None):
        """A live.menu. visibility: see `visibility_values`; kit_neutral: see `initial`."""
        hidden = self.visibility_values("menu", name, visibility, initial_outside_presets)
        initial = self.initial(name, items=items, initial_outside_presets=initial_outside_presets,
                               visibility=visibility, kit_neutral=kit_neutral)
        box_id = self.live_parameter("live.menu", name, short, (1500 + x, 640 + y, w, layout_rules.ROW_H),
                                     identity.PARAMETER_TYPE_ENUM, (x, y, w, layout_rules.ROW_H),
                                     parameter_enum=list(items), parameter_mmax=len(items) - 1,
                                     parameter_initial_enable=1, parameter_initial=[initial], **hidden)
        varname = varname_for(name)
        self.controls_by_kind["menu"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def tabs(self, name, short, items, x, y, w, page, initial_outside_presets=None, group=None, rows=1,
             visibility=identity.VISIBILITY_AUTOMATED_AND_STORED, row_height=layout_rules.ROW_H, kit_neutral=None):
        """Selector buttons (a live.tab): one enum parameter, a button per item, in `rows` lines of `row_height` px
        (ROW_H by default, the row band's; a column of tabs, one a line, can be taller: live.tab splits its height
        equally between its lines). live.tab splits each line's width equally; every button must hold its longest
        name (layout_rules). visibility: see `visibility_values`; kit_neutral: see `initial`."""
        problem = layout_rules.live_tab_button_problem(items, w, rows)
        if problem:
            self.fail(f"tabs {name!r}: {problem}")
        if not (isinstance(row_height, int) and row_height >= layout_rules.ROW_H):
            self.fail(f"tabs {name!r}: a line is {row_height!r} px high, less than the row band's {layout_rules.ROW_H}")
        hidden = self.visibility_values("tabs", name, visibility, initial_outside_presets)
        initial = self.initial(name, items=items, initial_outside_presets=initial_outside_presets,
                               visibility=visibility, kit_neutral=kit_neutral)
        height = row_height * rows
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
        `page` at a time; boxes join a group with group=(the selector's varname, i). The patch shows its first group
        (the boxes of the others are saved hidden), so the selector's neutral value (Live's initial value, what the
        device loads at) must be 0; its start value reaches the UI script as any change does."""
        varname = self.find(selector_box)["varname"]
        if varname in self.groups:
            self.fail(f"{varname!r} selects groups twice")
        control_name, transform = self.control_by_box[selector_box]
        if control_name not in self.neutral_values or transform(self.neutral_values[control_name]) != 0:
            self.fail(f"group selector {varname!r} must load on its first group (neutral value 0, after a derived "
                      f"box's transform of {control_name!r}'s neutral)")
        self.groups[varname] = {"page": page, "members": [[] for _ in range(choice_count)]}
        self.tell(selector_box, f"group {varname}", self.built_header()["ui"])

    def group_selector(self, name, short, items, x, y, w, page):
        """A live.tab that shows one group of boxes on `page` at a time (see `groups_selected_by`). Saved with the
        set, not in presets; starts on the first group."""
        box_id = self.tabs(name, short, items, x, y, w, page, initial_outside_presets=0, kit_neutral=0)
        self.groups_selected_by(box_id, len(items), page)
        return box_id

    def toggle(self, name, short, x, y, w, h, page, mode=1, initial_outside_presets=None, group=None,
               visibility=identity.VISIBILITY_AUTOMATED_AND_STORED, kit_neutral=None):
        """A live.text: mode 1 a toggle (saved; in presets unless it has its own initial value), mode 0 a
        momentary button (neither). visibility: see `visibility_values` (a button, saved in nothing, needs no initial
        value to be Hidden). kit_neutral: see `initial`."""
        hidden = self.visibility_values("toggle", name, visibility, initial_outside_presets if mode == 1 else 0)
        initial_values = ({"parameter_initial_enable": 1,
                           "parameter_initial": [self.initial(name, items=TOGGLE_ITEMS,
                                                              initial_outside_presets=initial_outside_presets,
                                                              visibility=visibility, kit_neutral=kit_neutral)]}
                          if mode == 1 else {})
        box_id = self.live_parameter("live.text", name, short, (1500 + x, 660 + y, w, h), identity.PARAMETER_TYPE_ENUM,
                                     (x, y, w, h), _mode=mode, **initial_values, **hidden)
        varname = varname_for(name)
        self.controls_by_kind["text"].append(varname)
        return self.on_page(page, box_id, varname, group)

    def numbox(self, name, short, target, message, minimum, maximum, unit, x, y, w, page, integer=False,
               inlet=0, initial_outside_presets=None, group=None, kit_neutral=None):
        """A live.numbox. integer=True: Live's Int type, which holds 256 values at most (see `stored`). kit_neutral:
        see `initial`."""
        if integer and maximum - minimum >= INT_PARAMETER_VALUES:
            self.fail(f"numbox {name!r}: an Int parameter holds {INT_PARAMETER_VALUES} values, {minimum}..{maximum} has more")
        initial = self.initial(name, minimum=minimum, maximum=maximum, initial_outside_presets=initial_outside_presets,
                               kit_neutral=kit_neutral)
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
        automate it. No double-click reaches it, so it has no neutral: its initial value is its start value. Float type with an Int unit style, 0-65535: Live's Int type holds only 256 values (0-255),
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
        self.page_tabs_x = layout_rules.page_tabs_x(self.link_chip_text)
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
                                       initial_outside_presets=0, kit_neutral=0)  # items: the preset book's, set by check()
            self.wire(made["preset"], made["ui"])
        self.subtitle_x = layout_rules.subtitle_x(self.link_chip_text, self.page_names, preset_menu)
        # the right end of the header: out (the output level) and Stop, 12 px from the device's edge
        self.output_level_x = self.device_width - 136
        # unity (0 dB) is the output level's neutral, the kit's for every device
        output_level_initial = self.initial(output_level_name, minimum=-36.0, maximum=12.0, kit_neutral=0.0)
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
        # the fresh-start flag (FRESH_START_FLAG_NAME): 0 in a fresh device, 1 once the UI script has moved the controls
        # to their start values; saved with the set and in presets (Stored Only), read and set by the UI script
        made["fresh_start_flag"] = self.stored(FRESH_START_FLAG_NAME, 0)
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

    def check(self, layout):
        """Every check of the patch as built, with the chrome's `layout` (see views_script); returns the presets
        ([Preset], every saved control set). Fills in the Preset menu's items. Fails on the first broken rule, saying
        what to fix."""
        self.built_header()
        presets = self.preset_book.presets_as_held(self.saved_controls)
        unknown_neutral = set(self.preset_book.neutral_values_in_own_units) - self.neutral_names_asked
        if unknown_neutral:
            self.fail(f"'neutral' in {self.preset_book.source_name} names no control that takes one (a control or a "
                      f"stored table with editors, not Hidden, not the kit's): {sorted(unknown_neutral)}")
        if self.header_boxes["preset"] is not None:
            preset_values = self.find(self.header_boxes["preset"])["saved_attribute_attributes"]["valueof"]
            preset_values.update(parameter_enum=[preset.name for preset in presets], parameter_mmax=len(presets) - 1)
        self.check_messages_into_gen_name_params()
        self.write_gen_param_defaults()
        self.check_controls_hold_their_text()
        problems = layout_rules.drawn_overlap_problems([x["box"] for x in self.boxes], self.full_layout(layout),
                                                       self.page_names, self.pages, self.groups, self.device_width)
        if problems:
            self.fail("the layout overlaps (layout_rules.drawn_overlap_problems):\n  " + "\n  ".join(problems))
        if set(self.info) - self.info_used:
            self.fail(f"the info has text for no parameter or view: {sorted(set(self.info) - self.info_used)}")
        self.check_script_lookups()
        self.check_wires()
        return presets

    def wires_into_gen(self):
        """[(source box id, source outlet, gen~ box id)] for every wire straight into a gen~ box."""
        return [(line["patchline"]["source"][0], line["patchline"]["source"][1], line["patchline"]["destination"][0])
                for line in self.lines if line["patchline"]["destination"][0] in self.gen_params_by_box]

    def gen_box_name(self, gen_box_id):
        return f"[{self.find(gen_box_id)['text']}] ({gen_box_id})"

    def check_messages_into_gen_name_params(self):
        """Every message the patch itself sends straight into a gen~ names a Param that gen~ declares: a [prepend X]
        wired into it (tell, tempo_synced_milliseconds, the Stop action's panic, a device's own) sends X, a message
        box its first word (a number is a value, not a message). A gen~ ignores a message to no Param, silently."""
        problems = []
        for source, _, gen_box_id in self.wires_into_gen():
            source_box = self.find(source)
            words = source_box.get("text", "").split()
            if source_box["maxclass"] == "newobj" and words[:1] == ["prepend"] and len(words) > 1:
                message, sender = words[1], f"[{source_box['text']}] ({source})"
            elif source_box["maxclass"] == "message" and words and not re.fullmatch(r"-?[0-9.]+", words[0]):
                message, sender = words[0], f"message box [{source_box['text']}] ({source})"
            else:
                continue
            params = self.gen_params_by_box[gen_box_id]
            if message not in params:
                problems.append(f"{sender} sends {message!r} into {self.gen_box_name(gen_box_id)}, which declares no "
                                f"such Param (its Params: {', '.join(sorted(params)) or 'none'})")
        if problems:
            self.fail("messages into a gen~ that name no Param of it:\n  " + "\n  ".join(problems))

    def script_outlet_of_block(self, script_box, outlet_index, outlet_expression, block):
        """A block's code in `script_box`'s script sends from outlet `outlet_index` through `outlet(<outlet_expression>,
        ...)`, an expression the script's text can't resolve (a stored table: "spec.outlet"): what lets
        check_script_messages_into_gen know where those calls go."""
        self.script_outlets_of_blocks.setdefault(script_box, {}).setdefault(outlet_expression, []).append(
            (outlet_index, block))

    def script_name_of_box(self, box):
        """The script file a [js] or [jsui] box runs, or None for any other box."""
        if box["maxclass"] == "jsui":
            return box.get("filename")
        words = box.get("text", "").split()
        if box["maxclass"] == "newobj" and words[:1] == ["js"] and len(words) > 1:
            return words[1] if words[1].endswith(".js") else words[1] + ".js"
        return None

    def check_script_messages_into_gen(self, scripts):
        """Every message a script ([js] / [jsui], its text in `scripts`, {file name: text}) sends from an outlet wired
        straight into a gen~ names a Param that gen~ declares (a gen~ ignores any other message, silently). Each
        `outlet(N, message, ...)` from such an outlet (twosl_dsp/script_outlet_calls.py): a string literal must be a
        declared Param; a `+` chain of literals and other expressions ("random_" + n) a pattern (other parts: any
        text) that at least one declared Param matches whole. Fails, listing every problem, on: a message of neither
        kind (a bare variable: it can't be checked), a call whose outlet the text can't say while the script feeds a
        gen~ (unless a block said where it goes: script_outlet_of_block), a block's outlet wired into a gen~, a script
        the build doesn't have."""
        gens_by_script_outlet = {}
        for source, source_outlet, gen_box_id in self.wires_into_gen():
            if self.script_name_of_box(self.find(source)) is not None:
                gens_by_script_outlet.setdefault((source, source_outlet), []).append(gen_box_id)
        problems = []
        for script_box in sorted({source for source, _ in gens_by_script_outlet}):
            script_name = self.script_name_of_box(self.find(script_box))
            if script_name not in scripts:
                problems.append(f"{script_name} (box {script_box}) sends into a gen~, but the build has no such script "
                                f"to check (its scripts: {', '.join(sorted(scripts))})")
                continue
            blocks_outlets = self.script_outlets_of_blocks.get(script_box, {})
            for expression, outlets in blocks_outlets.items():
                for outlet_index, block in outlets:
                    for gen_box_id in gens_by_script_outlet.get((script_box, outlet_index), []):
                        problems.append(f"{script_name}: {block}'s outlet {outlet_index} is wired into "
                                        f"{self.gen_box_name(gen_box_id)}: it goes to the block's own route only")
            for call in outlet_calls(scripts[script_name], script_name):
                where = f"{script_name} line {call.line}: outlet({call.outlet_expression}, {call.message_text}, ...)"
                if call.outlet_index is None:
                    if call.outlet_expression not in blocks_outlets:
                        problems.append(f"{where}: which outlet it sends from can't be read (a number, or a name bound "
                                        "once by `var NAME = <int>`), and the script sends into a gen~, so its "
                                        "message can't be checked")
                    continue
                for gen_box_id in gens_by_script_outlet.get((script_box, call.outlet_index), []):
                    params = self.gen_params_by_box[gen_box_id]
                    params_text = ", ".join(sorted(params)) or "none"
                    if call.message is None:
                        problems.append(f"{where} goes into {self.gen_box_name(gen_box_id)}, and its message is "
                                        "neither a string literal nor a + chain with one: it can't be checked against "
                                        f"the Params ({params_text}); send a literal or \"prefix_\" + n")
                    elif not any(re.fullmatch(call.message.pattern, name, re.DOTALL) for name in params):
                        problems.append(f"{where} goes into {self.gen_box_name(gen_box_id)}, whose Params "
                                        f"({params_text}) include no "
                                        + (f"{call.message_text}" if call.message.is_literal else
                                           f"name matching {call.message_text} (as /{call.message.pattern}/)"))
        if problems:
            self.fail("script messages into a gen~:\n  " + "\n  ".join(problems))

    def view_reading(self, view_box, message, values):
        """Display `view_box` shows `message`, a reading sent by something other than a control (the DSP, the
        brain), as `message value` with each of `values` (a number, or a list of numbers for a message of several;
        the first is where the display check starts): the display check drives the display through them as through
        its controls' values (check_display_texts)."""
        if view_box not in self.view_mode_by_box:
            self.fail(f"view_reading {message!r}: box {view_box} is no display")
        if not values:
            self.fail(f"view_reading {message!r} of the {self.view_mode_by_box[view_box]!r} display: no values")
        self.view_readings.setdefault(view_box, []).append(
            (message, [[generated_number(float(n)) for n in v] if isinstance(v, (list, tuple)) else
                       generated_number(float(v)) for v in values]))

    def saved_values_of(self, control_name):
        """The saved values (`saved_attribute_attributes.valueof`) of the control called `control_name`."""
        found = [entry["box"]["saved_attribute_attributes"]["valueof"] for entry in self.boxes
                 if entry["box"].get("saved_attribute_attributes", {}).get("valueof", {})
                 .get("parameter_longname") == control_name]
        if len(found) != 1:
            self.fail(f"control {control_name!r}: {len(found)} boxes are called that, not one")
        return found[0]

    def display_inputs(self, view_box):
        """[(message, [values], start index)]: what display `view_box` can be sent, for the display check. A
        control's message: every value it can send (its held values, layout_rules.live_held_values, a float at
        DISPLAY_SWEEP_STEPS steps; through its route's transform and scale), starting at its start value; a
        reading's (view_reading): its values, starting at the first."""
        values_by_message, start_by_message = {}, {}
        for control_name, transform, destination, message, scale in self.control_routes:
            if destination != view_box or message is None:
                continue
            factor = scale if scale is not None else 1
            sent = lambda held: generated_number(transform(held) * factor)  # noqa: E731
            held_values = layout_rules.live_held_values(self.saved_values_of(control_name),
                                                        layout_rules.DISPLAY_SWEEP_STEPS)
            values = values_by_message.setdefault(message, [])
            for value in [sent(self.initial_values[control_name])] + [sent(held) for held in held_values]:
                if value not in values:
                    values.append(value)
            start_by_message.setdefault(message, sent(self.initial_values[control_name]))
        for control_name, _, destination, message in self.tempo_routes:
            if destination == view_box:
                self.fail(f"the {self.view_mode_by_box[view_box]!r} display gets {control_name} as a time at Live's "
                          f"tempo ({message!r}): the display check can't drive it through Live's tempos yet")
        for message, values in self.view_readings.get(view_box, []):
            if message in values_by_message:
                self.fail(f"the {self.view_mode_by_box[view_box]!r} display's reading {message!r} is also a "
                          "control's message")
            values_by_message[message] = [v for i, v in enumerate(values) if v not in values[:i]]
            start_by_message[message] = values[0]
        return [(message, values, values.index(start_by_message[message]))
                for message, values in values_by_message.items()]

    def check_display_texts(self, views_script_text):
        """No display draws two texts over each other or a text off itself, as first painted and driven through what
        it can be sent (display_text.display_paints, display_inputs, layout_rules.display_text_problems): every shown
        display but the background. Each display with a problem: every problem of its first paint that has one, with
        what the display had been sent, and how many of its other paints have one too."""
        problems = []
        for box_id, mode in sorted(self.view_mode_by_box.items()):
            box = self.find(box_id)
            if box.get("background"):
                continue
            _, _, width, height = box["presentation_rect"]
            failing = []
            for painted in display_paints(views_script_text, mode, width, height, self.display_inputs(box_id)):
                found = layout_rules.display_text_problems(box["varname"], [(d.text, d.extent) for d in painted.drawn],
                                                           width, height)
                if found:
                    failing.append((painted.sent, found))
            if failing:
                sent, found = failing[0]
                when = ("sent " + ", ".join(f"{m} {sent_text(v)}" for m, v in sent.items())) if sent else \
                    "as first painted"
                problems += [f"{problem} ({when})" for problem in found]
                if len(failing) > 1:
                    problems.append(f"display {box['varname']}: and {len(failing) - 1} more of its paints, sent other "
                                    "values, have text over text or off the display")
        if problems:
            self.fail("text drawn over text in a display (layout_rules.display_text_problems):\n  "
                      + "\n  ".join(problems))

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

    def gen_param_defaults_by_box(self):
        """{gen~ box id: {Param name: default}}: each Param a control sets gets the value the initial values send it
        (the sound before Live recalls the controls; `tell` rounded it through generated_number). Fails, listing every problem: a message to no Param, two
        controls sending one Param different values, a value outside the Param's min / max, a Param whose code holds a
        default and is set by a control (one number, one source: leave it out of the code), and a Param with neither
        (its code leaves the default out, and no control sets it)."""
        defaults_by_box = {box_id: {} for box_id in self.gen_params_by_box}
        senders_by_box = {box_id: {} for box_id in self.gen_params_by_box}
        problems = []
        for gen_box_id, param_name, sent, control_name in self.gen_param_from_init:
            declared = self.gen_params_by_box[gen_box_id].get(param_name)
            if declared is None:
                problems.append(f"{control_name} -> {param_name}: no such Param")
                continue
            if declared.default is not None:
                problems.append(f"{control_name} -> Param {param_name}({declared.default:g}, ...): the initial values "
                                f"give it ({sent:g}): leave the default out of the code (Param {param_name}(min=..., "
                                "max=...);)")
                continue
            if ((declared.minimum is not None and sent < declared.minimum)
                    or (declared.maximum is not None and sent > declared.maximum)):
                problems.append(f"{control_name} -> Param {param_name}: the initial values send {sent:g}, outside its "
                                f"[{declared.minimum}, {declared.maximum}]")
                continue
            earlier = defaults_by_box[gen_box_id].get(param_name)
            if earlier is not None and earlier != sent:
                problems.append(f"Param {param_name}: {senders_by_box[gen_box_id][param_name]} sends {earlier:g}, "
                                f"{control_name} sends {sent:g} at the start")
                continue
            defaults_by_box[gen_box_id][param_name] = sent
            senders_by_box[gen_box_id][param_name] = control_name
        for gen_box_id, params in self.gen_params_by_box.items():
            for param_name, declared in params.items():
                if declared.default is None and param_name not in defaults_by_box[gen_box_id]:
                    problems.append(f"Param {param_name} ({self.find(gen_box_id)['text']}) has no default in its code "
                                    "and no control sets it: give the code its default, or set it from a control")
        if problems:
            self.fail("gen~ Param defaults:\n  " + "\n  ".join(problems))
        return defaults_by_box

    def gen_code_as_built(self, gen_box_id):
        """A gen~ box's code with every Param default written (gen_param_defaults_by_box): what the patch holds, and
        what a renderer or exporter of the device's DSP as Max runs it takes (twosl_dsp/genexpr_export.py)."""
        if gen_box_id not in self.gen_code_by_box:
            self.fail(f"box {gen_box_id!r} is no gen~ box")
        return genexpr.code_with_param_defaults(self.gen_code_by_box[gen_box_id],
                                                self.gen_param_defaults_by_box()[gen_box_id])

    def write_gen_param_defaults(self):
        """Every gen~ box's codebox gets its code as built (gen_code_as_built): the Params' defaults written from the
        initial values. Always from the code as given, so checking twice writes the same."""
        defaults_by_box = self.gen_param_defaults_by_box()
        for gen_box_id, code in self.gen_code_by_box.items():
            codebox = self.find(gen_box_id)["patcher"]["boxes"][0]["box"]
            if codebox["id"] != "cb":
                self.fail(f"internal error: gen~ box {gen_box_id!r}'s first box is not its codebox")
            codebox["code"] = genexpr.code_with_param_defaults(code, defaults_by_box[gen_box_id]).strip() + "\n"

    def ui_lookups(self):
        """Every scripting name the UI script looks up."""
        saved_varnames = set()
        for control in self.saved_controls.values():
            saved_varnames |= (set(control.parameter_varnames()) if isinstance(control, SavedRecord)
                               else {control.varname})
        return (saved_varnames
                | {n for names in self.controls_by_kind.values() for n in names} | set(self.view_varnames)
                | {n for names in self.pages.values() for n in names} | set(self.stop_turns_off)
                | set(self.neutral_by_varname) | {varname_for(FRESH_START_FLAG_NAME)})

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
            "boxes": self.boxes, "lines": self.lines, "latency": self.latency_samples,
        }}

    def ui_script(self, presets):
        """The UI script (templates/ui-script.template.js): pages, groups, the Preset menu, Stop, the theme, and a fresh
        device's move to its start values."""
        presets_for_menu = []
        if self.header_boxes["preset"] is not None:
            presets_for_menu = [self.preset_menu_values(preset) for preset in presets]
        return fill_template(kit_template_text("ui-script.template.js"), {
            "DEVICE_NAME": json.dumps(self.device_name), "SCRIPT_NAME": self.script_name,
            "PAGE_NAMES": json.dumps(self.page_names), "PAGES": json.dumps(self.pages),
            "PRESETS": json.dumps(presets_for_menu, indent=1), "CONTROLS": json.dumps(self.controls_by_kind),
            "GROUPS": json.dumps(self.groups), "VIEWS": json.dumps(self.view_varnames),
            "STOP_TURNS_OFF": json.dumps(self.stop_turns_off), "THEME_FROM_LIVE": theme_from_live_js(),
            "FRESH_START": json.dumps(self.fresh_start_by_varname),
            "NEUTRAL": json.dumps(self.neutral_by_varname),
            "FRESH_START_FLAG": json.dumps(varname_for(FRESH_START_FLAG_NAME))},
            "the kit's UI script template")

    def preset_menu_values(self, preset):
        """{scripting name: value} the Preset menu sets for `preset`: each control's value as held, and each saved
        record's Stored Only parameters (the UI script sets them; each tells the brain its value, as Live's recall does)."""
        values = {}
        for name, value in preset.values.items():
            if not isinstance(self.saved_controls[name], SavedRecord):
                values[self.saved_controls[name].varname] = value
        for long_name, number in stored_only_values_of_preset(preset.values, None, f"preset {preset.name!r}").items():
            values[varname_for(long_name)] = number
        return values

    def full_layout(self, layout):
        """The views script's LAYOUT from the device's `layout` ({"pages": [{"rules": [x], "labels": [[text, x,
        baseline, "label" | "hint"]]}]}, one page per page name): the header's labels added to each page, the
        subtitle's place (layout_rules.subtitle_x: the kit's, never the device's), its text, the version and the link
        chip's text."""
        if len(layout.get("pages", [])) != len(self.page_names):
            self.fail(f"the layout has {len(layout.get('pages', []))} pages, the device {len(self.page_names)}")
        if "subtitle" in layout:
            self.fail("the layout places the subtitle: the kit does (layout_rules.subtitle_x), drop the layout's "
                      "\"subtitle\"")
        if self.header_boxes is None:
            self.fail("the layout is asked for before the header is built (the subtitle goes after its tabs)")
        return dict(layout, subtitle=self.subtitle_x, subtitle_text=self.subtitle, version=self.version,
                    link_chip_text=self.link_chip_text,
                    pages=[dict(page, labels=self.header_labels() + list(page["labels"])) for page in layout["pages"]])

    def views_script(self, layout, device_views_code):
        """The views script (templates/views.template.js): the chrome and link chip, the drawing helpers, and the
        device's own displays (`device_views_code`, ES5). layout: {"pages": [{"rules": [x], "labels": [[text, x,
        baseline, "label" | "hint"]]}]}, one page per page name; the header's labels and the subtitle are added."""
        layout = self.full_layout(layout)
        return fill_template(kit_template_text("views.template.js"), {
            "DEVICE_NAME": json.dumps(self.device_name), "SCRIPT_NAME": self.script_name,
            "COZETTE": kit_template_text("cozette-glyphs.js").strip(), "THEME_FROM_LIVE": theme_from_live_js(),
            "VIEW_DEFAULTS": json.dumps(self.view_defaults), "LAYOUT": "var LAYOUT = " + json.dumps(layout) + ";",
            "DEVICE_VIEWS": device_views_code.strip()}, "the kit's views script template")

    def messages_for(self, control_values, destination, beats_per_minute=None):
        """What `destination` gets from these control values ({control: value as held}), as {message: value}; a
        raw value (tell's message None) as {None: value}. A tempo-synced time (tempo_synced_milliseconds) needs
        `beats_per_minute`: asked without it, this fails."""
        sent = {}
        for control_name, transform, route_destination, message, scale in self.control_routes:
            if route_destination == destination and control_name in control_values:
                sent[message] = transform(control_values[control_name]) * (scale if scale is not None else 1)
        for control_name, beats_of, route_destination, message in self.tempo_routes:
            if route_destination == destination and control_name in control_values:
                if beats_per_minute is None:
                    self.fail(f"messages_for: {control_name} is a time at Live's tempo: say the beats_per_minute")
                sent[message] = beats_of(control_values[control_name]) * 60000 / beats_per_minute
        return sent

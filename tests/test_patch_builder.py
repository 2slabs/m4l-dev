"""The patch builder's rules (twosl_dsp/patch_builder.py, layout_rules.py, preset_book.py): the layout check (nothing
shown at the same time overlaps or leaves the device), groups, controls kept out of presets, the Init values and the
presets, gen~ Params, live.tab widths. Builds small patches in memory; writes nothing."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import layout_rules  # noqa: E402
from twosl_dsp import live_parameter_identity as identity  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.patch_builder import FRESH_START_FLAG_NAME, DevicePatchBuilder  # noqa: E402
from twosl_dsp.preset_book import PresetBook  # noqa: E402
from twosl_dsp.techniques.defined_latency_pad import DefinedLatency  # noqa: E402

INFO = {name: (name, "text") for name in ("A", "B", "C", "Volume", "Page", "Preset", "Stop", "Link view", "Pick", "Tool")}
# a and volume: set by controls, so no default in the code (the build writes it); b: set by no control in most tests
GEN_CODE = "Param a(min=0, max=1);\nParam b(0.25, min=0, max=1);\nParam volume;\nout1 = in1 * a;\n"


KIT_NEUTRAL_NAMES = ("Volume", "Output", "Seed", "Loop", "Chord", "In key")   # the kit declares these neutrals


def preset_book(init=None, presets=None, neutral=None):
    """A test's book; its neutral values, unless given, are its Init values (the controls a test builds)."""
    init = {"A": 0, "B": 0, "C": 0, "Volume": 0} if init is None else init
    return PresetBook({"neutral": ({name: value for name, value in init.items() if name not in KIT_NEUTRAL_NAMES}
                                   if neutral is None else neutral),
                       "init": init,
                       "presets": presets or [{"name": "init", "group": "init", "idea": "init", "values": {}}]},
                      "the test's book")


HEADER_INFO = ("Volume", "Page", "Stop", "Link view")


def builder(width=400, book=None, preset_menu=None, info_keys=None, gen_code=GEN_CODE):
    """A builder with a gen~ (patch.target, holding `gen_code`) and the header. info_keys: the Info texts it has (default all of INFO;
    check() fails on a text nothing uses, so a test that passes check() names the ones it uses)."""
    info = INFO if info_keys is None else {key: INFO[key] for key in HEADER_INFO + tuple(info_keys)}
    patch = DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                               device_type="instrument", device_width=width, page_names=["one", "two"], info=info,
                               preset_book=book or preset_book(), latency_samples=0)
    patch.target = patch.gen_box(gen_code, 1, 1, rect=(0, 0, 80, 22))
    patch.header(output_level_target=patch.target, output_level_name="Volume", preset_menu=preset_menu)
    return patch


def find_by_varname(patch, varname):
    found = [x["box"] for x in patch.boxes if x["box"].get("varname") == varname]
    assert len(found) == 1, f"{len(found)} boxes named {varname}"
    return found[0]


def saved_values(patch, box_id):
    return patch.find(box_id)["saved_attribute_attributes"]["valueof"]


def plain_layout(patch, labels_by_page=None):
    """A device's chrome layout: no rules, `labels_by_page` ({page: [[text, x, baseline, kind]]}) or none."""
    return {"pages": [{"rules": [], "labels": (labels_by_page or {}).get(page, [])} for page in patch.page_names]}


def layout_problems(patch, labels_by_page=None):
    return layout_rules.drawn_overlap_problems([x["box"] for x in patch.boxes],
                                               patch.full_layout(plain_layout(patch, labels_by_page)),
                                               patch.page_names, patch.pages, patch.groups, patch.device_width)


def builder_with_latency(latency_samples):
    return DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                              device_type="audio", device_width=400, page_names=["one"], info=INFO,
                              preset_book=preset_book(), latency_samples=latency_samples)


class DefinedLatencyTests(unittest.TestCase):
    """The device's Defined Latency reaches Live as the patcher's "latency" (whole samples, the rule's figure)."""

    def test_the_patch_carries_the_declared_whole_samples(self):
        for declared in (0, 6, 29):
            patch = builder_with_latency(declared)
            self.assertEqual(patch.patch()["patcher"]["latency"], declared)
            self.assertIsInstance(patch.patch()["patcher"]["latency"], int)
            self.assertEqual(patch.latency_samples, declared)

    def test_the_rules_figure_is_what_it_takes(self):
        # a device's paths through DefinedLatency: the latest (a half-sample clip on a 2x saturator, 23.03 + 0.5)
        # rounded up; the builder takes that int as it is
        rule = DefinedLatency("t", {"clipped": 23.03 + 0.5, "clean": 23.03})
        self.assertEqual(builder_with_latency(rule.declared_latency_samples).patch()["patcher"]["latency"], 24)

    def test_a_latency_that_is_no_whole_number_of_samples_fails(self):
        # a fraction (29.03, or a float crumb's 0.5000000000000001) would be rounded where no test sees it: the
        # device rounds up by the rule (DefinedLatency) and pads its paths, the builder takes the whole number
        for bad in (None, -1, 29.03, 0.5000000000000001, 6.0, float("nan"), float("inf"), True, "29"):
            with self.assertRaisesRegex(BuildError, "latency_samples", msg=bad):
                builder_with_latency(bad)


class LayoutTests(unittest.TestCase):
    def test_overlap_on_one_page_fails(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 0, "Volume": 0}))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "a", 0, 1, 0, 40, 119, "one")
        self.assertTrue(any("overlaps" in p for p in layout_problems(patch)))
        with self.assertRaisesRegex(BuildError, "overlaps"):
            patch.check(plain_layout(patch))

    def test_same_place_on_other_pages_is_fine(self):
        patch = builder()
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "b", 0, 1, 0, 12, 119, "two")
        self.assertEqual(layout_problems(patch), [])

    def test_groups_share_a_place_but_not_within_one(self):
        patch = builder()
        patch.group_selector("Pick", "Pick", ["x", "y"], 12, 98, 100, "one")
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one", group=("pick", 0))
        patch.dial("B", "B", patch.target, "b", 0, 1, 0, 12, 119, "one", group=("pick", 1))
        self.assertEqual(layout_problems(patch), [])
        self.assertEqual(find_by_varname(patch, "b")["hidden"], 1, "the second group starts hidden")
        patch.dial("C", "C", patch.target, "c", 0, 1, 0, 30, 119, "one", group=("pick", 1))
        self.assertTrue(any("overlaps" in p for p in layout_problems(patch)))

    def test_a_box_off_the_device_fails(self):
        patch = builder(width=200)
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 180, 119, "one")
        self.assertTrue(any("reaches off" in p for p in layout_problems(patch)))

    def test_a_dials_value_text_reaching_into_its_neighbour_fails_naming_both(self):
        # A's widest value, "-100000.00" (55.7 px), centred on its 44 px box, reaches 5.9 px past each side: 1.9 px
        # into B's box 4 px away. Its name fits; its value is what reaches.
        patch = builder()
        patch.dial("A", "A", patch.target, "a", -100000, 100000, layout_rules.UNIT_FLOAT, 12, 119, "one")
        patch.dial("B", "B", patch.target, "b", 0, 1, layout_rules.UNIT_FLOAT, 60, 119, "one")
        self.assertEqual(layout_problems(patch), [
            "page 'one': a's value (x 6.14062..61.8594, y 156..167) overlaps b's box (x 60..104, y 119..167) by "
            "1.85938 x 11 px"])

    def test_a_chrome_label_over_a_control_or_another_label_fails_naming_both(self):
        patch = builder(book=preset_book(init={"A": "x", "Volume": 0}))
        patch.menu("A", "A", ["x", "y"], 12, layout_rules.ROW_Y, 40, "one")
        problems = layout_problems(patch, {"one": [["section", 12, 110, "label"], ["sect", 48, 110, "hint"]],
                                           "two": [["section", 12, 110, "label"]]})
        self.assertIn("page 'one': a's box (x 12..52, y 98..113) overlaps label 'section''s text (x 12..54, y 100..113) "
                      "by 40 x 13 px", problems)
        self.assertIn("page 'one': label 'section''s text (x 12..54, y 100..113) overlaps hint 'sect''s text "
                      "(x 48..72, y 100..113) by 6 x 13 px", problems)
        self.assertFalse(any(p.startswith("page 'two'") for p in problems), "the menu is on page one only")

    def test_the_header_labels_and_the_subtitle_count(self):
        # the Preset menu's "preset" label, 40 px before the menu, runs into the page tabs; the subtitle, which the
        # kit places a header gap after the menu, into "out"
        patch = builder(preset_menu=(150, 60), info_keys=("Preset",))
        problems = layout_problems(patch)
        self.assertEqual(patch.full_layout(plain_layout(patch))["subtitle"], 150 + 60 + layout_rules.HEADER_GAP)
        self.assertIn("page 'one': page's box (x 38..134, y 3..18) overlaps label 'preset''s text (x 110..146, "
                      "y 5..18) by 24 x 13 px", problems)
        self.assertIn("page 'one': label 'out''s text (x 240..258, y 5..18) overlaps subtitle '  v0''s text "
                      "(x 222..246, y 5..18) by 6 x 13 px", problems)

    def test_the_kit_places_the_subtitle_not_the_device(self):
        patch = builder()
        self.assertEqual(patch.full_layout(plain_layout(patch))["subtitle"],
                         patch.page_tabs_x + layout_rules.page_tabs_width(patch.page_names) + layout_rules.HEADER_GAP)
        with self.assertRaisesRegex(BuildError, "the layout places the subtitle: the kit does"):
            patch.full_layout(dict(plain_layout(patch), subtitle=200))

    def test_the_background_is_what_everything_sits_on(self):
        patch = builder()
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        chrome = patch.find(patch.header_boxes["chrome"])
        self.assertEqual((chrome["background"], chrome["presentation_rect"]), (1, [0.0, 0.0, 400.0, 169.0]))
        self.assertEqual(layout_problems(patch), [])

    def test_value_texts_are_measured_as_the_kit_formats_them(self):
        text = layout_rules.live_value_text
        self.assertEqual([text(1500, layout_rules.UNIT_HERTZ), text(12.5, layout_rules.UNIT_HERTZ),
                          text(185, layout_rules.UNIT_TIME), text(2500, layout_rules.UNIT_TIME),
                          text(5, layout_rules.UNIT_TIME, integer=True), text(-6, layout_rules.UNIT_DECIBEL),
                          text(35, layout_rules.UNIT_PERCENT), text(3, layout_rules.UNIT_SEMITONES),
                          text(-50, layout_rules.UNIT_PAN), text(0, layout_rules.UNIT_PAN), text(60, layout_rules.UNIT_MIDI),
                          text(0.5, layout_rules.UNIT_FLOAT), text(7, layout_rules.UNIT_INT)],
                         ["1.50 kHz", "12.5 Hz", "185 ms", "2.50 s", "5 ms", "-6.0 dB", "35.0 %", "+3.00 st", "50L", "C",
                          "C3", "0.50", "7"])
        self.assertEqual(layout_rules.live_value_texts({"parameter_enum": ["a", "bb"]}), ["a", "bb"])
        self.assertEqual(layout_rules.live_value_texts({"parameter_type": layout_rules.PARAMETER_TYPE_INT,
                                                        "parameter_mmin": 0.0, "parameter_mmax": 2.0,
                                                        "parameter_unitstyle": layout_rules.UNIT_PERCENT}),
                         ["0 %", "1 %", "2 %"])
        held = layout_rules.live_held_values
        self.assertEqual(held({"parameter_enum": ["a", "bb", "c"]}, 4), [0, 1, 2])
        self.assertEqual(held({"parameter_type": layout_rules.PARAMETER_TYPE_INT, "parameter_mmin": -1.0,
                               "parameter_mmax": 1.0}, 4), [-1, 0, 1])
        self.assertEqual(held({"parameter_mmin": 0.0, "parameter_mmax": 100.0, "parameter_exponent": 2.0}, 4),
                         [0.0, 6.25, 25.0, 56.25, 100.0], "a float: its travel in steps, Live's exponent applied")

    def test_the_header_moves_with_the_width_and_must_be_on_the_grid(self):
        patch = builder(width=640)
        self.assertEqual(find_by_varname(patch, "stop")["presentation_rect"][0], 580)
        self.assertEqual(find_by_varname(patch, "volume")["presentation_rect"][0], 504)
        with self.assertRaisesRegex(BuildError, "4 px grid"):
            builder(width=642)

    def test_the_page_tabs_sit_a_header_gap_after_the_link_chip(self):
        patch = builder()
        link_width = layout_rules.link_chip_width("t")
        self.assertEqual(find_by_varname(patch, "page")["presentation_rect"][0], 12 + link_width + 12)

    def test_tabs_need_room_for_the_longest_name(self):
        patch = builder(book=preset_book(neutral={"A": 0, "B": 0, "C": 0, "Tool": "one", "Pick": "-1 sq"}))
        patch.tabs("Tool", "Tool", ["one", "two", "three", "four"], 12, 40, 76, "one", initial_outside_presets=0, rows=2)
        self.assertEqual(find_by_varname(patch, "tool")["presentation_rect"][3], 30, "two rows of 15 px")
        self.assertEqual(find_by_varname(patch, "tool")["num_lines_presentation"], 2)
        # 2 a row in 76 px: 38 px a button, "three" needs 25.1 + 6; "-2 pls" (2sl stab) needs 26.9 + 6 = 32.9
        with self.assertRaisesRegex(BuildError, "longest"):
            patch.tabs("Pick", "Pick", ["-1 sq", "-2 sq", "-2 pls"], 12, 80, 96, "one", initial_outside_presets=0)
        patch.tabs("Pick", "Pick", ["-1 sq", "-2 sq", "-2 pls"], 12, 80, 100, "one", initial_outside_presets=0)

    def test_the_page_switch_is_hidden(self):
        patch = builder()
        self.assertEqual(saved_values(patch, patch.header_boxes["page_tabs"])["parameter_invisible"], 2)

    def test_tabs_can_be_hidden_and_then_stay_out_of_presets(self):
        patch = builder(book=preset_book(neutral={"A": 0, "B": 0, "C": 0, "Pick": "a"}))
        with self.assertRaisesRegex(BuildError, "initial_outside_presets"):
            patch.tabs("Tool", "Tool", ["a", "b"], 12, 40, 40, "one", visibility=identity.VISIBILITY_HIDDEN)
        tool = patch.tabs("Tool", "Tool", ["a", "b"], 12, 40, 40, "one", initial_outside_presets=0,
                          visibility=identity.VISIBILITY_HIDDEN)
        self.assertEqual(saved_values(patch, tool)["parameter_invisible"], identity.VISIBILITY_HIDDEN)
        self.assertNotIn("Tool", patch.saved_controls)
        pick = patch.tabs("Pick", "Pick", ["a", "b"], 12, 60, 40, "one", initial_outside_presets=0)
        self.assertNotIn("parameter_invisible", saved_values(patch, pick), "visible by default, as Max saves it")
        with self.assertRaisesRegex(BuildError, "neither"):
            patch.tabs("C", "C", ["a", "b"], 12, 80, 40, "one", visibility=identity.VISIBILITY_STORED_ONLY)

    def test_the_device_names_its_output_level(self):
        patch = DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                                   device_type="instrument", device_width=400, page_names=["one"],
                                   info={name: (name, "text") for name in ("Output", "Page", "Stop", "Link view")},
                                   preset_book=PresetBook({"neutral": {}, "init": {"Output": -6}, "presets": [
                                       {"name": "init", "group": "init", "idea": "init", "values": {}}]}, "book"),
                                   latency_samples=0)
        target = patch.gen_box("Param volume;\nout1 = in1;\n", 1, 1, rect=(0, 0, 80, 22))
        made = patch.header(output_level_target=target, output_level_name="Output")
        values = saved_values(patch, made["output_level"])
        self.assertEqual((values["parameter_longname"], values["parameter_shortname"]), ("Output", "Output"))
        self.assertEqual(patch.find(made["output_level"])["varname"], "output")
        self.assertEqual(patch.messages_for({"Output": -3}, target), {"volume": -3})
        patch.check(plain_layout(patch))

    def test_controls_must_hold_their_text(self):
        patch = builder(book=preset_book(init={"A": 0, "B": "x", "Volume": 0}), info_keys=("A", "B"))
        patch.dial("A", "Velocity Amount", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.menu("B", "B", ["x", "a long item"], 12, 98, 40, "one")
        with self.assertRaises(BuildError) as failure:
            patch.check(plain_layout(patch))
        self.assertIn("A (live.dial) is 44 px wide, its text needs 84", str(failure.exception))
        self.assertIn("B (live.menu) is 40 px wide, its text needs 68", str(failure.exception))
        self.assertEqual(layout_rules.live_toggle_width("in key"), 40)
        self.assertEqual(layout_rules.live_tabs_width(["mono", "chords"]), 80)

    def test_a_dial_is_as_wide_as_its_name_needs(self):
        patch = builder(book=preset_book(init={"A": 0, "Volume": 0}), info_keys=("A",))
        width = layout_rules.live_dial_width("Velocity Amount")
        made = patch.dial("A", "Velocity Amount", patch.target, "a", 0, 1, 0, 12, 119, "one", width=width)
        self.assertEqual(patch.find(made)["presentation_rect"][2], width)
        patch.check(plain_layout(patch))
        for bad_width in (40, 46):
            with self.assertRaisesRegex(BuildError, "at least 44, on the 4 px grid"):
                patch.dial("B", "B", patch.target, "b", 0, 1, 0, 120, 119, "one", width=bad_width)

    def test_text_is_measured_by_its_characters_with_room_around_it(self):
        # capitals are wider: "FM amount" (9 characters) needs a wider dial than "Velocity" (8); two tab names of
        # three digits each get their padding ("246|248" read as "246248" with 1 px of slack)
        self.assertGreater(layout_rules.live_text_width("FM amount"), layout_rules.live_text_width("Velocity") + 10)
        self.assertEqual((layout_rules.live_dial_width("FM amount"), layout_rules.live_dial_width("Velocity")), (60, 44))
        self.assertEqual(layout_rules.live_tabs_width(["246", "248"]), 52)
        with self.assertRaisesRegex(BuildError, "doesn't measure"):
            layout_rules.live_text_width("\u2603")


class InfoTests(unittest.TestCase):
    def test_a_builder_leaves_the_devices_info_alone(self):
        # a device builds twice in one process (its build, then its tests' in-memory build): a block adding its
        # controls' text to the info must not find it there the second time
        from twosl_dsp.seeded_random import SeededRandom
        info = dict(INFO)
        for _ in range(2):
            patch = DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                                       device_type="instrument", device_width=400, page_names=["one"], info=info,
                                       preset_book=preset_book(), latency_samples=0)
            SeededRandom(patch, patch.box("js t.js", rect=(0, 0, 50, 22), ins=2), 1)
        self.assertEqual(info, INFO)


class ControlRouteTests(unittest.TestCase):
    """messages_for: what a destination gets from control values, through the routes the build wired."""

    def test_a_menu_lookup_is_the_controls_value_looked_up(self):
        patch = builder(book=preset_book(init={"A": "1/8", "Volume": 0}))
        menu = patch.menu("A", "A", ["1/16", "1/8", "1/4"], 12, 98, 40, "one")
        patch.tell(patch.menu_lookup(menu, [0.25, 0.5, 1.0]), "a", patch.target)
        self.assertEqual(patch.messages_for({"A": 2}, patch.target), {"a": 1.0})
        self.assertIn("expr ($i1==0)*0.25 + ($i1==1)*0.5 + ($i1==2)*1.0", [x["box"].get("text") for x in patch.boxes])

    def test_a_tempo_synced_time_needs_the_tempo(self):
        patch = builder(book=preset_book(init={"A": "1/8", "Volume": 0}))
        menu = patch.menu("A", "A", ["1/16", "1/8", "1/4"], 12, 98, 40, "one")
        tempo = patch.box("t f", rect=(0, 0, 30, 22))
        patch.tempo_synced_milliseconds(menu, [0.25, 0.5, 1.0], tempo, "time", patch.target)
        self.assertEqual(patch.messages_for({"A": 0}, patch.target, beats_per_minute=120), {"time": 125.0})
        self.assertIn("pak 120. 0.5", [x["box"].get("text") for x in patch.boxes], "starts at the Init item")
        with self.assertRaisesRegex(BuildError, "beats_per_minute"):
            patch.messages_for({"A": 0}, patch.target)

    def test_a_raw_value_is_the_message_none(self):
        patch = builder(book=preset_book(init={"A": 0.5, "Volume": 0}))
        phasor = patch.box("phasor~", rect=(0, 0, 50, 22), ins=2, outtype=["signal"])
        patch.dial("A", "A", phasor, None, 0, 1, 0, 12, 119, "one")
        self.assertEqual(patch.messages_for({"A": 0.25}, phasor), {None: 0.25})


class InitialValueAndPresetTests(unittest.TestCase):
    def test_controls_with_their_own_initial_value_stay_out_of_presets(self):
        patch = builder(book=preset_book(neutral={"A": 0, "B": 0, "C": 0, "Tool": 0}))
        patch.numbox("Tool", "Tool", patch.target, "tool", 0, 10, 0, 12, 40, 40, "one", integer=True,
                     initial_outside_presets=3)
        self.assertNotIn("Tool", patch.saved_controls)
        self.assertEqual(patch.initial_values["Tool"], 3)
        with self.assertRaisesRegex(BuildError, "can't have its own initial value"):
            patch.numbox("A", "A", patch.target, "a", 0, 10, 0, 60, 40, 40, "one", initial_outside_presets=1)
        with self.assertRaisesRegex(BuildError, "256 values"):
            patch.numbox("C", "C", patch.target, "c", 0, 999, 0, 60, 60, 40, "one", integer=True)

    def test_a_control_without_an_init_value_fails(self):
        patch = builder()
        with self.assertRaisesRegex(BuildError, "'Tool' has no Init value"):
            patch.dial("Tool", "Tool", patch.target, "tool", 0, 1, 0, 12, 119, "one")

    def test_init_values_are_held_as_the_control_holds_them(self):
        book = preset_book(init={"A": "y", "B": "on", "C": 0.5, "Volume": -3})
        patch = builder(book=book)
        menu = patch.menu("A", "A", ["x", "y"], 12, 98, 60, "one")
        toggle = patch.toggle("B", "B", 80, 98, 40, 15, "one")
        self.assertEqual(saved_values(patch, menu)["parameter_initial"], [1])
        self.assertEqual(saved_values(patch, toggle)["parameter_initial"], [1])
        self.assertEqual(patch.find(toggle)["automation"], "off")
        self.assertEqual(patch.find(toggle)["automationon"], "on")

    def test_an_init_value_out_of_range_fails(self):
        patch = builder(book=preset_book(init={"A": 2, "B": 0, "C": 0, "Volume": 0}))
        with self.assertRaisesRegex(BuildError, "outside 0 to 1"):
            patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")

    def test_presets_are_checked_against_the_controls(self):
        presets = [{"name": "init", "group": "init", "idea": "i", "values": {}},
                   {"name": "p", "group": "g", "idea": "i", "values": {"A": 1, "Nope": 3}}]
        patch = builder(book=preset_book(presets=presets))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "b", 0, 1, 0, 60, 119, "one")
        patch.dial("C", "C", patch.target, "c", 0, 1, 0, 108, 119, "one")
        with self.assertRaisesRegex(BuildError, "Nope"):
            patch.check(plain_layout(patch))

    def test_an_init_value_for_no_control_fails(self):
        patch = builder()
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, r"names no saved control: \['B', 'C'\]"):
            patch.check(plain_layout(patch))

    def test_the_preset_menu_lists_the_presets_and_the_ui_gets_them(self):
        presets = [{"name": "init", "group": "init", "idea": "i", "values": {}},
                   {"name": "high", "group": "g", "idea": "i", "values": {"A": 1}}]
        patch = builder(width=480, book=preset_book(init={"A": 0, "Volume": 0}, presets=presets), preset_menu=(216, 48),
                        info_keys=("A", "Preset"))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        held = patch.check(plain_layout(patch))
        self.assertEqual(saved_values(patch, patch.header_boxes["preset"])["parameter_enum"], ["init", "high"])
        self.assertEqual([p.values["A"] for p in held], [0, 1])
        self.assertIn('"a": 1', patch.ui_script(held))

    def test_preset_book_shape_is_checked(self):
        with self.assertRaisesRegex(BuildError, "exactly 'neutral', 'init' and 'presets'"):
            PresetBook({"init": {}, "presets": []}, "book")
        with self.assertRaisesRegex(BuildError, "used twice"):
            PresetBook({"neutral": {}, "init": {},
                        "presets": [{"name": "a", "group": "g", "idea": "i", "values": {}}] * 2}, "book")


class NeutralValueTests(unittest.TestCase):
    """Every control a user can double-click declares a neutral value (Live's initial value, the double-click
    target), separate from Init; a fresh device moves from it to its start value (the UI script)."""

    def test_live_loads_the_neutral_and_the_device_starts_at_init(self):
        patch = builder(book=preset_book(init={"A": 0.7, "B": 0, "Volume": -3}, neutral={"A": 0, "B": 0}))
        a = patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "b", 0, 1, 0, 60, 119, "one")
        self.assertEqual(saved_values(patch, a)["parameter_initial"], [0.0], "the double-click target")
        self.assertEqual(patch.initial_values["A"], 0.7, "the start value: the gen~ default, the displays'")
        self.assertEqual(saved_values(patch, patch.header_boxes["output_level"])["parameter_initial"], [0.0],
                         "the output level's neutral is unity, the kit's")
        self.assertEqual(patch.fresh_start_by_varname, {"a": 0.7, "volume": -3},
                         "only a control whose start isn't neutral moves on a fresh device")
        self.assertEqual(patch.neutral_by_varname["a"], [0, 1e-4])

    def test_a_control_without_a_neutral_fails_and_a_stray_one_fails(self):
        patch = builder(book=preset_book(neutral={"A": 0, "B": 0}))
        with self.assertRaisesRegex(BuildError, "'C' has no neutral value .*add it to 'neutral'"):
            patch.dial("C", "C", patch.target, "c", 0, 1, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, "outside"):
            builder(book=preset_book(neutral={"A": 2})).dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        stray = builder(book=preset_book(init={"A": 0, "Volume": 0}, neutral={"A": 0, "Gone": 0}))
        stray.dial("A", "A", stray.target, "a", 0, 1, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, "names no control that takes one.*Gone"):
            stray.check(plain_layout(stray))

    def test_hidden_and_kit_controls_take_no_neutral_from_the_book(self):
        hidden = builder(book=preset_book(neutral={"A": 0, "B": 0, "C": 0, "Tool": "a"}))
        with self.assertRaisesRegex(BuildError, "Hidden .*leave it out of 'neutral'"):
            hidden.tabs("Tool", "Tool", ["a", "b"], 12, 40, 40, "one", initial_outside_presets=1,
                        visibility=identity.VISIBILITY_HIDDEN)
        patch = builder()
        tool = patch.tabs("Tool", "Tool", ["a", "b"], 12, 40, 40, "one", initial_outside_presets=1,
                          visibility=identity.VISIBILITY_HIDDEN)
        self.assertEqual(saved_values(patch, tool)["parameter_initial"], [1], "a Hidden control loads at its start")
        self.assertNotIn("tool", patch.neutral_by_varname, "never saved: nothing to move on a fresh device")
        with self.assertRaisesRegex(BuildError, "the kit declares its neutral"):
            builder(book=preset_book(init={"A": 0, "B": 0, "C": 0, "Volume": 0},
                                     neutral={"A": 0, "B": 0, "C": 0, "Volume": 0}))

    def test_the_fresh_start_flag_is_stored_only_and_starts_at_0(self):
        patch = builder()
        flag = saved_values(patch, patch.header_boxes["fresh_start_flag"])
        self.assertEqual((flag["parameter_longname"], flag["parameter_invisible"], flag["parameter_initial"]),
                         (FRESH_START_FLAG_NAME, identity.VISIBILITY_STORED_ONLY, [0.0]))
        self.assertIn('var FRESH_START_FLAG = "init_applied";', patch.ui_script([]))


class GroupTests(unittest.TestCase):
    def test_any_control_can_select_groups_and_must_load_on_the_first(self):
        patch = builder(book=preset_book(neutral={"A": 0, "B": 0, "C": 0, "Pick": "x", "Tool": 2}))
        picker = patch.dial("Pick", "Pick", patch.target, "pick", 0, 0, 0, 12, 119, "one", items=["x", "y"],
                            initial_outside_presets=0)
        patch.groups_selected_by(picker, 2, "one")
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 60, 119, "one", group=("pick", 0))
        patch.dial("B", "B", patch.target, "b", 0, 1, 0, 60, 119, "one", group=("pick", 1))
        self.assertEqual(layout_problems(patch), [])
        self.assertEqual(find_by_varname(patch, "b")["hidden"], 1, "the second group starts hidden")
        self.assertTrue(any(route[0] == "Pick" and route[2] == patch.header_boxes["ui"] and route[3] == "group pick"
                            for route in patch.control_routes), "the UI hears the selector")
        late = patch.dial("Tool", "Tool", patch.target, "tool", 0, 3, 0, 120, 119, "one", integer=True,
                          initial_outside_presets=0)
        with self.assertRaisesRegex(BuildError, "load on its first group"):
            patch.groups_selected_by(late, 4, "one")

    def test_a_derived_selector_loads_on_its_first_group_by_its_transform_of_the_neutral(self):
        patch = builder(book=preset_book(neutral={"A": 0, "B": 0, "C": 0, "Pick": "y"}))
        picker = patch.dial("Pick", "Pick", patch.target, "pick", 0, 0, 0, 12, 119, "one", items=["x", "y"],
                            initial_outside_presets=0)
        is_x = patch.derived(patch.box("== 0", rect=(1100, 2000, 40, 22), ins=2, outtype=["int"], varname="is_x"),
                             "Pick", lambda pick: int(pick == 0))
        patch.groups_selected_by(is_x, 2, "one")       # Pick's neutral y: == 0 gives 0, the first group
        is_y = patch.derived(patch.box("== 1", rect=(1100, 2030, 40, 22), ins=2, outtype=["int"], varname="is_y"),
                             "Pick", lambda pick: int(pick == 1))
        with self.assertRaisesRegex(BuildError, "load on its first group"):
            patch.groups_selected_by(is_y, 2, "one")   # the untransformed neutral (1) was read before

    def test_dials_are_floats_ints_or_enums(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 0, "Volume": 0}, neutral={"A": 0, "B": 0, "Tool": "p"}))
        self.assertEqual(saved_values(patch, patch.dial("A", "A", patch.target, "a", 0, 10, 0, 12, 119, "one"))[
            "parameter_type"], 0)
        self.assertEqual(saved_values(patch, patch.dial("B", "B", patch.target, "b", 0, 10, 0, 60, 119, "one",
                                                        integer=True))["parameter_type"], 1)
        enum = saved_values(patch, patch.dial("Tool", "Tool", patch.target, "t", 0, 0, 0, 108, 119, "one",
                                              items=["p", "q"], initial_outside_presets=1))
        self.assertEqual((enum["parameter_type"], enum["parameter_enum"], enum["parameter_mmax"],
                          enum["parameter_initial"]), (2, ["p", "q"], 1, [0]), "Live's initial value is the neutral")
        self.assertEqual(patch.initial_values["Tool"], 1, "it starts at its own initial value")
        with self.assertRaisesRegex(BuildError, "256 values"):
            patch.dial("C", "C", patch.target, "c", 0, 999, 0, 156, 119, "one", integer=True)


class GenTests(unittest.TestCase):
    @staticmethod
    def codebox_code(patch, gen_box_id):
        return patch.find(gen_box_id)["patcher"]["boxes"][0]["box"]["code"]

    def test_the_build_writes_each_param_default_from_the_init_values(self):
        patch = builder(book=preset_book(init={"A": 0.75, "Volume": -3}), info_keys=("A",))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.check(plain_layout(patch))
        self.assertEqual(self.codebox_code(patch, patch.target), "Param a(0.75, min=0, max=1);\nParam b(0.25, min=0, "
                         "max=1);\nParam volume(-3);\nout1 = in1 * a;\n")
        self.assertEqual(patch.gen_code_as_built(patch.target), self.codebox_code(patch, patch.target))
        patch.check(plain_layout(patch))                                  # checking twice writes the same (from the code as given)
        self.assertIn("Param a(0.75, min=0, max=1);", self.codebox_code(patch, patch.target))

    def test_a_scaled_or_derived_value_is_written_as_sent(self):
        patch = builder(book=preset_book(init={"A": "y", "B": 50, "Volume": 0}), info_keys=("A", "B"),
                        gen_code="Param a(min=0, max=1);\nParam b;\nParam volume;\nout1 = in1 * a * b;\n")
        menu = patch.menu("A", "A", ["x", "y"], 12, 98, 60, "one")
        patch.tell(patch.menu_lookup(menu, [0.1, 0.3]), "a", patch.target)
        patch.dial("B", "B", patch.target, "b", 0, 100, 0, 76, 119, "one", scale=0.01)
        self.assertIn("Param a(0.3, min=0, max=1);\nParam b(0.5);", patch.gen_code_as_built(patch.target))

    def test_a_default_in_the_code_and_from_the_init_values_fails(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 50, "Volume": 0}))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "b", 0, 100, 0, 60, 119, "one", scale=0.01)
        with self.assertRaisesRegex(BuildError, r"B -> Param b\(0.25, ...\): the initial values give it \(0.5\): "
                                                r"leave the default out"):
            patch.check(plain_layout(patch))

    def test_a_param_with_no_default_and_no_control_fails(self):
        patch = builder(book=preset_book(init={"Volume": 0}))
        with self.assertRaisesRegex(BuildError, "Param a .* has no default in its code and no control sets it"):
            patch.check(plain_layout(patch))

    def test_two_controls_sending_one_param_different_initial_values_fail(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 1, "Volume": 0}))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "a", 0, 1, 0, 60, 119, "one")
        with self.assertRaisesRegex(BuildError, "Param a: A sends 0, B sends 1 at the start"):
            patch.check(plain_layout(patch))

    def test_an_initial_value_outside_the_params_range_fails(self):
        patch = builder(book=preset_book(init={"A": 5, "Volume": 0}))
        patch.dial("A", "A", patch.target, "a", 0, 10, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, r"the initial values send 5, outside its \[0.0, 1.0\]"):
            patch.check(plain_layout(patch))

    def test_a_tempo_synced_time_writes_its_default_at_the_starting_tempo(self):
        patch = builder(book=preset_book(init={"A": "1/8", "Volume": 0}), info_keys=("A",),
                        gen_code="Param a(0.5);\nParam time(min=1, max=4000);\nParam volume;\nout1 = in1 * a;\n")
        menu = patch.menu("A", "A", ["1/16", "1/8", "1/4"], 12, 98, 40, "one")
        patch.tempo_synced_milliseconds(menu, [0.25, 0.5, 1.0], patch.box("t f", rect=(0, 0, 30, 22)), "time",
                                        patch.target)
        self.assertIn("Param time(250, min=1, max=4000);", patch.gen_code_as_built(patch.target))

    def test_a_message_to_no_param_fails(self):
        patch = builder(book=preset_book(init={"A": 0, "Volume": 0}))
        patch.dial("A", "A", patch.target, "nothing", 0, 1, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, "\\[prepend nothing\\] .* sends 'nothing' into \\[gen~\\] .* no such Param"):
            patch.check(plain_layout(patch))
        with self.assertRaisesRegex(BuildError, "nothing: no such Param"):
            patch.gen_code_as_built(patch.target)

    def test_gen_code_is_checked(self):
        patch = builder()
        with self.assertRaisesRegex(BuildError, "gen~ code"):
            patch.gen_box("out1 = in1 +;", 1, 1, rect=(0, 0, 80, 22))
        with self.assertRaisesRegex(BuildError, "out1..out1, the box was given 2"):
            patch.gen_box("out1 = in1;", 1, 2, rect=(0, 0, 80, 22))

    def test_derived_values_count_for_the_checks(self):
        patch = builder(book=preset_book(init={"A": "y", "Volume": 0}), info_keys=("A",))
        menu = patch.menu("A", "A", ["x", "y"], 12, 98, 60, "one")
        lookup = patch.derived(patch.box("expr $i1 * 0.25"), "A", lambda v: v * 0.25)
        patch.wire(menu, lookup)
        patch.tell(lookup, "a", patch.target)
        patch.check(plain_layout(patch))
        self.assertIn("Param a(0.25, min=0, max=1);", self.codebox_code(patch, patch.target))


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""The patch builder's rules (m4l_dev/patch_builder.py, layout_rules.py, preset_book.py): the layout check (nothing
shown at the same time overlaps or leaves the device), groups, controls kept out of presets, the Init values and the
presets, gen~ Params, live.tab widths. Builds small patches in memory; writes nothing."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m4l_dev import layout_rules  # noqa: E402
from m4l_dev import live_parameter_identity as identity  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.patch_builder import DevicePatchBuilder  # noqa: E402
from m4l_dev.preset_book import PresetBook  # noqa: E402

INFO = {name: (name, "text") for name in ("A", "B", "C", "Volume", "Page", "Preset", "Stop", "Link view", "Pick", "Tool")}
GEN_CODE = "Param a(0, min=0, max=1);\nParam b(0.25, min=0, max=1);\nParam volume(0);\nout1 = in1 * a;\n"


def preset_book(init=None, presets=None):
    return PresetBook({"init": {"A": 0, "B": 0, "C": 0, "Volume": 0} if init is None else init,
                       "presets": presets or [{"name": "init", "group": "init", "idea": "init", "values": {}}]},
                      "the test's book")


HEADER_INFO = ("Volume", "Page", "Stop", "Link view")


def builder(width=400, book=None, preset_menu=None, info_keys=None):
    """A builder with a gen~ (patch.target) and the header. info_keys: the Info texts it has (default all of INFO;
    check() fails on a text nothing uses, so a test that passes check() names the ones it uses)."""
    info = INFO if info_keys is None else {key: INFO[key] for key in HEADER_INFO + tuple(info_keys)}
    patch = DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                               device_type="instrument", device_width=width, page_names=["one", "two"], info=info,
                               preset_book=book or preset_book())
    patch.target = patch.gen_box(GEN_CODE, 1, 1, rect=(0, 0, 80, 22))
    patch.header(output_level_target=patch.target, output_level_name="Volume", preset_menu=preset_menu)
    return patch


def find_by_varname(patch, varname):
    found = [x["box"] for x in patch.boxes if x["box"].get("varname") == varname]
    assert len(found) == 1, f"{len(found)} boxes named {varname}"
    return found[0]


def saved_values(patch, box_id):
    return patch.find(box_id)["saved_attribute_attributes"]["valueof"]


def layout_problems(patch):
    shown = [x["box"] for x in patch.boxes if x["box"].get("presentation") == 1 and not x["box"].get("background")]
    return layout_rules.overlap_problems(shown, patch.page_names, patch.pages, patch.groups, patch.device_width)


class LayoutTests(unittest.TestCase):
    def test_overlap_on_one_page_fails(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 0, "Volume": 0}))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "a", 0, 1, 0, 40, 119, "one")
        self.assertTrue(any("overlaps" in p for p in layout_problems(patch)))
        with self.assertRaisesRegex(BuildError, "overlaps"):
            patch.check()

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
        self.assertTrue(any("leaves" in p for p in layout_problems(patch)))

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
        patch = builder(book=preset_book(init={"A": 0, "B": 0, "C": 0, "Volume": 0}))
        patch.tabs("Tool", "Tool", ["one", "two", "three", "four"], 12, 40, 76, "one", initial_outside_presets=0, rows=2)
        self.assertEqual(find_by_varname(patch, "tool")["presentation_rect"][3], 30, "two rows of 15 px")
        self.assertEqual(find_by_varname(patch, "tool")["num_lines_presentation"], 2)
        # 2 a row in 74 px: 37 px a button, "three" needs 6 x 5 + 1 = 31; "-2 pls" (2sl stab) needs 37
        with self.assertRaisesRegex(BuildError, "longest"):
            patch.tabs("Pick", "Pick", ["-1 sq", "-2 sq", "-2 pls"], 12, 80, 110, "one", initial_outside_presets=0)
        patch.tabs("Pick", "Pick", ["-1 sq", "-2 sq", "-2 pls"], 12, 80, 112, "one", initial_outside_presets=0)

    def test_the_page_switch_is_hidden(self):
        patch = builder()
        self.assertEqual(saved_values(patch, patch.header_boxes["page_tabs"])["parameter_invisible"], 2)

    def test_tabs_can_be_hidden_and_then_stay_out_of_presets(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 0, "C": 0, "Volume": 0}))
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
                                   preset_book=PresetBook({"init": {"Output": -6}, "presets": [
                                       {"name": "init", "group": "init", "idea": "init", "values": {}}]}, "book"))
        target = patch.gen_box("Param volume(-6);\nout1 = in1;\n", 1, 1, rect=(0, 0, 80, 22))
        made = patch.header(output_level_target=target, output_level_name="Output")
        values = saved_values(patch, made["output_level"])
        self.assertEqual((values["parameter_longname"], values["parameter_shortname"]), ("Output", "Output"))
        self.assertEqual(patch.find(made["output_level"])["varname"], "output")
        self.assertEqual(patch.messages_for({"Output": -3}, target), {"volume": -3})
        patch.check()

    def test_controls_must_hold_their_text(self):
        patch = builder(book=preset_book(init={"A": 0, "B": "x", "Volume": 0}), info_keys=("A", "B"))
        patch.dial("A", "Velocity Amount", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.menu("B", "B", ["x", "a long item"], 12, 98, 40, "one")
        with self.assertRaises(BuildError) as failure:
            patch.check()
        self.assertIn("A (live.dial) is 44 px wide, its text needs 84", str(failure.exception))
        self.assertIn("B (live.menu) is 40 px wide, its text needs 76", str(failure.exception))
        self.assertEqual(layout_rules.live_toggle_width("in key"), 44)
        self.assertEqual(layout_rules.live_tabs_width(["mono", "chords"]), 76)


class InfoTests(unittest.TestCase):
    def test_a_builder_leaves_the_devices_info_alone(self):
        # a device builds twice in one process (its build, then its tests' in-memory build): a block adding its
        # controls' text to the info must not find it there the second time
        from m4l_dev.seeded_random import SeededRandom
        info = dict(INFO)
        for _ in range(2):
            patch = DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                                       device_type="instrument", device_width=400, page_names=["one"], info=info,
                                       preset_book=preset_book())
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
        patch = builder()
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
            patch.check()

    def test_an_init_value_for_no_control_fails(self):
        patch = builder()
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, r"names no saved control: \['B', 'C'\]"):
            patch.check()

    def test_the_preset_menu_lists_the_presets_and_the_ui_gets_them(self):
        presets = [{"name": "init", "group": "init", "idea": "i", "values": {}},
                   {"name": "high", "group": "g", "idea": "i", "values": {"A": 1}}]
        patch = builder(book=preset_book(init={"A": 0, "Volume": 0}, presets=presets), preset_menu=(150, 60),
                        info_keys=("A", "Preset"))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        held = patch.check()
        self.assertEqual(saved_values(patch, patch.header_boxes["preset"])["parameter_enum"], ["init", "high"])
        self.assertEqual([p.values["A"] for p in held], [0, 1])
        self.assertIn('"a": 1', patch.ui_script(held))

    def test_preset_book_shape_is_checked(self):
        with self.assertRaisesRegex(BuildError, "exactly 'init' and 'presets'"):
            PresetBook({"init": {}}, "book")
        with self.assertRaisesRegex(BuildError, "used twice"):
            PresetBook({"init": {}, "presets": [{"name": "a", "group": "g", "idea": "i", "values": {}}] * 2}, "book")


class GroupTests(unittest.TestCase):
    def test_any_control_can_select_groups_and_must_start_on_the_first(self):
        patch = builder()
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
                          initial_outside_presets=2)
        with self.assertRaisesRegex(BuildError, "initial value 0"):
            patch.groups_selected_by(late, 4, "one")

    def test_dials_are_floats_ints_or_enums(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 0, "Volume": 0}))
        self.assertEqual(saved_values(patch, patch.dial("A", "A", patch.target, "a", 0, 10, 0, 12, 119, "one"))[
            "parameter_type"], 0)
        self.assertEqual(saved_values(patch, patch.dial("B", "B", patch.target, "b", 0, 10, 0, 60, 119, "one",
                                                        integer=True))["parameter_type"], 1)
        enum = saved_values(patch, patch.dial("Tool", "Tool", patch.target, "t", 0, 0, 0, 108, 119, "one",
                                              items=["p", "q"], initial_outside_presets=1))
        self.assertEqual((enum["parameter_type"], enum["parameter_enum"], enum["parameter_mmax"],
                          enum["parameter_initial"]), (2, ["p", "q"], 1, [1]))
        with self.assertRaisesRegex(BuildError, "256 values"):
            patch.dial("C", "C", patch.target, "c", 0, 999, 0, 156, 119, "one", integer=True)


class GenTests(unittest.TestCase):
    def test_param_defaults_must_be_what_the_init_values_send(self):
        patch = builder(book=preset_book(init={"A": 0, "B": 50, "Volume": 0}))
        patch.dial("A", "A", patch.target, "a", 0, 1, 0, 12, 119, "one")
        patch.dial("B", "B", patch.target, "b", 0, 100, 0, 60, 119, "one", scale=0.01)
        with self.assertRaisesRegex(BuildError, r"Param b\(0.25\), the Init values send 0.5"):
            patch.check()

    def test_a_message_to_no_param_fails(self):
        patch = builder(book=preset_book(init={"A": 0, "Volume": 0}))
        patch.dial("A", "A", patch.target, "nothing", 0, 1, 0, 12, 119, "one")
        with self.assertRaisesRegex(BuildError, "nothing: no such Param"):
            patch.check()

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
        patch.tell(lookup, "b", patch.target)
        patch.check()


if __name__ == "__main__":
    unittest.main(verbosity=2)

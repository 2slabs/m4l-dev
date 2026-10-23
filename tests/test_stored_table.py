"""The stored table (twosl_dsp/stored_table.py, architecture/stored-table.md): its fields and packing, its value in the
preset book (Init whole, presets by field), its Stored Only parameters and their values per preset, its editors, the
Preset menu's values, and the Seed dial and taller tab lines it came with. Builds small patches in memory; the brain's
code runs in tests/kit-scripts.test.js on the fixture device."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import layout_rules  # noqa: E402
from twosl_dsp import live_parameter_identity as identity  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.patch_builder import FRESH_START_FLAG_NAME, DevicePatchBuilder  # noqa: E402
from twosl_dsp.preset_book import PresetBook, stored_only_values_of_preset  # noqa: E402
from twosl_dsp.seeded_random import SeededRandom  # noqa: E402
from twosl_dsp.stored_table import (ChoiceField, ContinuousField, HeldTable, StoredTable,  # noqa: E402
                                  stored_tables_brain_code)

INIT_STAGES = {"Pitch": [0, 7, -24], "Level": [100, -100, 0], "Pulse": ["off", "on", "off"],
               "Wait": ["go", "keyed", "stop"]}
HEADER_INFO = ("Volume", "Page", "Stop", "Link view")
EDITOR_INFO = ("Pitch editor 1", "Pulse editor 1", "Wait editor 2")


def fields():
    return [ContinuousField("Pitch", -24, 24), ContinuousField("Level", -100, 100), ChoiceField("Pulse", ["off", "on"]),
            ChoiceField("Wait", ["go", "stop", "hold", "keyed"])]


# the editors' double-click targets (Wait's "hold" is neither the first item nor any row's Init: a test sees which)
NEUTRAL_STAGES = {"Pitch": 0, "Level": 0, "Pulse": "off", "Wait": "hold"}


def book(presets=None, init_stages=None, neutral_stages=None):
    """A test's book; the table has a neutral value (`neutral_stages`) only where a test makes its editors."""
    return PresetBook({"neutral": {} if neutral_stages is None else {"Stages": neutral_stages},
                       "init": {"Volume": 0, "Stages": INIT_STAGES if init_stages is None else init_stages},
                       "presets": presets or [{"name": "init", "group": "init", "idea": "init", "values": {}}]},
                      "the test's book")


def builder(preset_book=None, preset_menu=None, info_keys=EDITOR_INFO + ("Tab",)):
    """A builder with the header and a brain (patch.brain); info_keys: the Info texts it has besides the header's
    (check() fails on a text nothing uses, so a test that checks names the ones it uses)."""
    keys = HEADER_INFO + tuple(info_keys) + (("Preset",) if preset_menu else ())
    patch = DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", link_chip_text="t",
                               device_type="instrument", device_width=480, page_names=["one", "two"],
                               info={key: (key, "text") for key in keys},
                               preset_book=preset_book or book(), latency_samples=0)
    patch.target = patch.gen_box("Param volume;\nout1 = in1;\n", 1, 1, rect=(0, 0, 80, 22))
    patch.header(output_level_target=patch.target, output_level_name="Volume", preset_menu=preset_menu)
    patch.brain = patch.box("js t.js", rect=(0, 100, 80, 22), ins=2, outs=3)
    return patch


def plain_layout(patch):
    """A device's chrome layout: no rules or labels."""
    return {"pages": [{"rules": [], "labels": []} for _ in patch.page_names]}


def stages_of(patch, rows=3, table_fields=None):
    return StoredTable(patch, "Stages", table_fields or fields(), rows, patch.brain, 1, 2)


def find_by_varname(patch, varname):
    found = [x["box"] for x in patch.boxes if x["box"].get("varname") == varname]
    assert len(found) == 1, f"{len(found)} boxes named {varname}"
    return found[0]


class FieldTests(unittest.TestCase):
    def test_a_continuous_field_holds_every_whole_number_exactly(self):
        pitch = ContinuousField("Pitch", -24, 24)
        self.assertEqual(pitch.codes_per_unit, 1365)
        for semitones in range(-24, 25):
            self.assertEqual(pitch.held(semitones, "here"), semitones)
            self.assertEqual(pitch.code(pitch.held(semitones, "here")), (semitones + 24) * 1365)
        self.assertEqual(ContinuousField("Time", 1, 10000).codes_per_unit, 6)

    def test_a_value_between_codes_is_held_on_the_nearest_half_up(self):
        pitch = ContinuousField("Pitch", -24, 24)
        held = pitch.held(0.3, "here")
        self.assertEqual(pitch.code(held), 33170, "24.3 x 1365 = 33169.5, half up (Python's round() would give 33170 "
                                                  "too, but 0.5 -> 0 where the brain gives 1)")
        self.assertEqual(held, -24 + 33170 / 1365)
        self.assertEqual(ContinuousField("Small", 0, 1).code(0.5 / 65535), 1, "half up, as the brain's Math.round")

    def test_bad_fields_fail(self):
        for make in (lambda: ContinuousField("x", 0.5, 2), lambda: ContinuousField("x", 2, 2),
                     lambda: ContinuousField("x", 0, 70000), lambda: ChoiceField("x", ["only"]),
                     lambda: ChoiceField("x", ["a", "a"])):
            with self.assertRaises(BuildError):
                make()

    def test_choice_bits(self):
        self.assertEqual([ChoiceField("x", ["a"] + [str(i) for i in range(n - 1)]).bits for n in (2, 3, 4, 5, 16, 17)],
                         [1, 2, 2, 3, 4, 5])


class PresetBookTests(unittest.TestCase):
    def test_init_is_held_on_the_grid_and_choices_as_indices(self):
        patch = builder()
        stages = stages_of(patch)
        init = patch.initial_values["Stages"]
        self.assertIsInstance(init, HeldTable)
        self.assertEqual(init.columns["Pitch"], (0, 7, -24))
        self.assertEqual(init.columns["Wait"], (0, 3, 1))
        self.assertEqual(init.row(1), {"Pitch": 7, "Level": -100, "Pulse": 1, "Wait": 3})
        self.assertIs(patch.saved_controls["Stages"], stages)

    def test_a_preset_changes_whole_fields_and_keeps_inits_others(self):
        patch = builder(book([{"name": "init", "group": "init", "idea": "init", "values": {}},
                              {"name": "up", "group": "g", "idea": "i", "values": {"Stages": {"Pitch": [12, 12, 12]}}}]),
                        info_keys=())
        stages_of(patch)
        presets = patch.check(plain_layout(patch))
        self.assertEqual(presets[1].values["Stages"].columns["Pitch"], (12, 12, 12))
        self.assertEqual(presets[1].values["Stages"].columns["Wait"], (0, 3, 1), "Init's")
        self.assertEqual(presets[0].values["Stages"], patch.initial_values["Stages"])
        self.assertEqual(patch.preset_book.values_in_own_units("up")["Stages"],
                         dict(INIT_STAGES, Pitch=[12, 12, 12]), "in own units too, field by field")

    def test_bad_values_fail_saying_where(self):
        cases = [({"Pitch": [0, 7]}, "a list of 3"), ({"Pitch": [0, 7, 30]}, "outside"),
                 ({"Wait": ["go", "go", "later"]}, "not one of"), ({"Time": [1, 1, 1]}, "fields the table doesn't"),
                 ([0, 0, 0], "must be")]
        for value, message in cases:
            patch = builder(book([{"name": "bad", "group": "g", "idea": "i", "values": {"Stages": value}}]))
            stages_of(patch)
            with self.assertRaisesRegex(BuildError, message):
                patch.check(plain_layout(patch))

    def test_init_must_give_every_field(self):
        patch = builder(book(init_stages={"Pitch": [0, 0, 0]}))
        with self.assertRaisesRegex(BuildError, "leaves out"):
            stages_of(patch)

    def test_a_table_needs_an_init_value(self):
        patch = builder(PresetBook({"neutral": {}, "init": {"Volume": 0}, "presets": [
            {"name": "init", "group": "init", "idea": "i", "values": {}}]}, "b"))
        with self.assertRaisesRegex(BuildError, "no Init value"):
            stages_of(patch)


class StoredParameterTests(unittest.TestCase):
    def test_a_parameter_per_continuous_field_and_row_and_one_for_the_rows_switches(self):
        patch = builder()
        stages_of(patch)
        names = [valueof["parameter_longname"] for _, valueof in identity.live_parameter_boxes(patch.patch())
                 if valueof.get("parameter_invisible") == identity.VISIBILITY_STORED_ONLY]
        self.assertEqual(names, [FRESH_START_FLAG_NAME, "Stages Pitch 1", "Stages Level 1", "Stages switches 1", "Stages Pitch 2",
                                 "Stages Level 2", "Stages switches 2", "Stages Pitch 3", "Stages Level 3",
                                 "Stages switches 3"])
        box = find_by_varname(patch, "stages_switches_2")
        self.assertEqual(box["saved_attribute_attributes"]["valueof"]["parameter_initial"], [1.0 + (3 << 1)])

    def test_stored_values_round_trip_and_match_the_preset_helper(self):
        patch = builder()
        stages = stages_of(patch)
        held = patch.initial_values["Stages"]
        values = held.stored_only_values()
        self.assertEqual(values["Stages Pitch 2"], 31 * 1365)
        self.assertEqual(values["Stages Level 1"], 200 * 327)
        self.assertEqual(values["Stages switches 3"], 0 + (1 << 1))
        self.assertEqual(stages.held_from_stored_only_values(values), held)
        self.assertEqual(stored_only_values_of_preset({"Stages": held, "Volume": 0}, None, "here"), values)

    def test_a_bad_stored_value_fails(self):
        patch = builder()
        stages = stages_of(patch)
        values = patch.initial_values["Stages"].stored_only_values()
        for name, code in (("Stages switches 1", 8), ("Stages Pitch 1", 65530), ("Stages Pitch 1", 1.5)):
            with self.assertRaises(BuildError):
                stages.held_from_stored_only_values(dict(values, **{name: code}))

    def test_a_device_function_cant_store_what_a_table_stores(self):
        patch = builder()
        stages_of(patch)
        with self.assertRaisesRegex(BuildError, "already stores"):
            stored_only_values_of_preset({"Stages": patch.initial_values["Stages"]},
                                         lambda values: {"Stages Pitch 1": 0}, "here")

    def test_too_many_choice_bits_fail(self):
        patch = builder(book(init_stages={"A": ["0"], "B": ["0"]}))
        many = [str(i) for i in range(256)]
        with self.assertRaisesRegex(BuildError, "17 bits"):
            StoredTable(patch, "Stages", [ChoiceField("A", many), ChoiceField("B", many + ["one more"])], 1,
                        patch.brain, 1, 2)

    def test_the_preset_menu_sets_the_stored_parameters(self):
        patch = builder(book([{"name": "init", "group": "init", "idea": "i", "values": {}},
                              {"name": "up", "group": "g", "idea": "i", "values": {"Stages": {"Pitch": [12, 0, 0]}}}]),
                        preset_menu=(216, 48), info_keys=())
        stages_of(patch)
        presets = patch.check(plain_layout(patch))
        script = patch.ui_script(presets)
        menu_presets = json.loads(script.split("var PRESETS = ")[1].split(";\n")[0])
        self.assertEqual(menu_presets[1]["stages_pitch_1"], 36 * 1365)
        self.assertEqual(menu_presets[1]["stages_switches_2"], 1 + (3 << 1))
        self.assertNotIn("stages", menu_presets[1], "the table itself is no box")


class OutsidePresetsTests(unittest.TestCase):
    """A table presets leave alone (initial_outside_presets): its initial value is the device's, the Preset menu
    doesn't set it, the preset book can't name it."""

    def outside_book(self, presets=None):
        return PresetBook({"neutral": {}, "init": {"Volume": 0}, "presets": presets or [
            {"name": "init", "group": "init", "idea": "i", "values": {}},
            {"name": "loud", "group": "g", "idea": "i", "values": {"Volume": 3}}]}, "the test's book")

    def test_its_initial_value_is_the_devices_and_the_preset_menu_leaves_it_alone(self):
        patch = builder(self.outside_book(), preset_menu=(216, 48), info_keys=())
        StoredTable(patch, "Stages", fields(), 3, patch.brain, 1, 2, initial_outside_presets=INIT_STAGES)
        self.assertEqual(patch.initial_values["Stages"].columns["Pitch"], (0, 7, -24))
        box = find_by_varname(patch, "stages_switches_2")
        self.assertEqual(box["saved_attribute_attributes"]["valueof"]["parameter_initial"], [1.0 + (3 << 1)])
        presets = patch.check(plain_layout(patch))
        self.assertTrue(all("Stages" not in preset.values for preset in presets))
        script = patch.ui_script(presets)
        menu_presets = json.loads(script.split("var PRESETS = ")[1].split(";\n")[0])
        self.assertTrue(menu_presets and all(not any(name.startswith("stages_") for name in values)
                                             for values in menu_presets))

    def test_a_preset_naming_it_fails(self):
        patch = builder(self.outside_book([{"name": "init", "group": "init", "idea": "i", "values": {}},
                                           {"name": "up", "group": "g", "idea": "i",
                                            "values": {"Stages": {"Pitch": [12, 0, 0]}}}]))
        StoredTable(patch, "Stages", fields(), 3, patch.brain, 1, 2, initial_outside_presets=INIT_STAGES)
        with self.assertRaisesRegex(BuildError, "sets controls the device doesn't have"):
            patch.check(plain_layout(patch))

    def test_an_init_value_too_fails_and_every_field_is_needed(self):
        with self.assertRaisesRegex(BuildError, "can't have its own initial value too"):
            stages = builder()
            StoredTable(stages, "Stages", fields(), 3, stages.brain, 1, 2, initial_outside_presets=INIT_STAGES)
        patch = builder(self.outside_book())
        with self.assertRaisesRegex(BuildError, "leaves out"):
            StoredTable(patch, "Stages", fields(), 3, patch.brain, 1, 2, initial_outside_presets={"Pitch": [0, 0, 0]})


class EditorTests(unittest.TestCase):
    def test_editors_are_hidden_controls_loading_at_their_fields_neutral(self):
        """An editor's initial value (its double-click target) is its field's neutral, not its row's Init: the
        table's recall shows the row once the device is ready."""
        patch = builder(book(neutral_stages=NEUTRAL_STAGES), info_keys=EDITOR_INFO)
        stages = stages_of(patch)
        dial = stages.editor_dial("Pitch", 0, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        toggle = stages.editor_toggle("Pulse", 0, "Pulse editor 1", "Pulse 1", 12, layout_rules.ROW_Y, 48, "one")
        menu = stages.editor_menu("Wait", 1, "Wait editor 2", "Wait 2", 64, layout_rules.ROW_Y, 44, "one")
        for box_id, initial in ((dial, [0.0]), (toggle, [0]), (menu, [2])):
            valueof = patch.find(box_id)["saved_attribute_attributes"]["valueof"]
            self.assertEqual(valueof["parameter_invisible"], identity.VISIBILITY_HIDDEN)
            self.assertEqual(valueof["parameter_initial"], initial)
        self.assertNotIn("Pitch editor 1", patch.saved_controls, "presets leave an editor alone: the table is saved")
        self.assertEqual(stages.editors, {"pitch_editor_1": ("Pitch", 0), "pulse_editor_1": ("Pulse", 0),
                                          "wait_editor_2": ("Wait", 1)})
        code = stored_tables_brain_code([stages])
        self.assertIn('"pitch_editor_1": {"field": "Pitch", "row": 0}', code)
        route = next(x["box"] for x in patch.boxes if x["box"].get("text", "").startswith("route stages_pitch_1"))
        self.assertEqual(route["text"].split()[1:], stages.parameter_varnames() + list(stages.editors))
        patch.check(plain_layout(patch))

    def test_a_stepped_editor_dial_names_an_index_field(self):
        patch = builder(book(init_stages=dict(INIT_STAGES, Time=[0, 1, 2]), neutral_stages=dict(NEUTRAL_STAGES, Time=1)),
                        info_keys=("Time editor 1",))
        stages = stages_of(patch, table_fields=fields() + [ContinuousField("Time", 0, 2)])
        dial = stages.editor_dial("Time", 0, "Time editor 1", "Time 1", 12, layout_rules.DIAL_Y, "one",
                                  items=["1/16", "1/8", "1/4"])
        valueof = patch.find(dial)["saved_attribute_attributes"]["valueof"]
        self.assertEqual(valueof["parameter_enum"], ["1/16", "1/8", "1/4"])
        self.assertEqual(valueof["parameter_initial"], [1], "the field's neutral, not row 1's Init (0)")
        with self.assertRaisesRegex(BuildError, "name the whole numbers 0..1"):
            stages.editor_dial("Time", 1, "Time editor 1", "Time 2", 12, layout_rules.DIAL_Y, "one",
                               items=["1/16", "1/8"])

    def test_editor_mistakes_fail(self):
        without_neutral = stages_of(builder(info_keys=EDITOR_INFO))
        with self.assertRaisesRegex(BuildError, "no neutral value"):
            without_neutral.editor_dial("Pitch", 0, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        partial = stages_of(builder(book(neutral_stages={"Pitch": 0}), info_keys=EDITOR_INFO))
        with self.assertRaisesRegex(BuildError, "Pulse has an editor but no neutral value"):
            partial.editor_toggle("Pulse", 0, "Pulse editor 1", "Pulse 1", 12, layout_rules.ROW_Y, 48, "one")
        stray = stages_of(builder(book(neutral_stages=dict(NEUTRAL_STAGES, Time=0)), info_keys=EDITOR_INFO))
        with self.assertRaisesRegex(BuildError, "fields it doesn't have: \\['Time'\\]"):
            stray.editor_dial("Pitch", 0, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        unused = builder(book(neutral_stages=NEUTRAL_STAGES))
        stages_of(unused)
        with self.assertRaisesRegex(BuildError, "names no control that takes one.*Stages"):
            unused.check(plain_layout(unused))
        patch = builder(book(neutral_stages=NEUTRAL_STAGES))
        stages = stages_of(patch)
        with self.assertRaisesRegex(BuildError, "no field"):
            stages.editor_dial("Time", 0, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        with self.assertRaisesRegex(BuildError, "rows 0..2"):
            stages.editor_dial("Pitch", 3, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        with self.assertRaisesRegex(BuildError, "ChoiceField"):
            stages.editor_dial("Wait", 0, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        with self.assertRaisesRegex(BuildError, "two items"):
            stages.editor_toggle("Wait", 1, "Wait editor 2", "Wait 2", 12, layout_rules.ROW_Y, 48, "one")
        with self.assertRaisesRegex(BuildError, "Info View"):
            stages.editor_dial("Pitch", 1, "Pitch editor 2", "Pitch 2", 12, layout_rules.DIAL_Y, "one")
        stored_tables_brain_code([stages])
        with self.assertRaisesRegex(BuildError, "after the brain code"):
            stages.editor_dial("Pitch", 0, "Pitch editor 1", "Pitch 1", 12, layout_rules.DIAL_Y, "one")
        with self.assertRaisesRegex(BuildError, "twice"):
            stored_tables_brain_code([stages])


class ControlFormTests(unittest.TestCase):
    """The control forms the sequencer's pages asked for: Hidden dials, menus and toggles; taller tab lines; Seed as
    a dial."""

    def test_dials_menus_and_toggles_can_be_hidden(self):
        patch = builder()
        dial = patch.dial("Tab", "Tab", patch.brain, "tab", 0, 1, 1, 12, layout_rules.DIAL_Y, "one",
                          initial_outside_presets=0, visibility=identity.VISIBILITY_HIDDEN)
        self.assertEqual(patch.find(dial)["saved_attribute_attributes"]["valueof"]["parameter_invisible"], 2)
        with self.assertRaisesRegex(BuildError, "initial_outside_presets"):
            patch.menu("Pitch editor 1", "P", ["a", "b"], 60, layout_rules.ROW_Y, 40, "one",
                       visibility=identity.VISIBILITY_HIDDEN)
        with self.assertRaisesRegex(BuildError, "neither"):
            patch.toggle("Pulse editor 1", "P", 60, layout_rules.ROW_Y, 40, 15, "one", initial_outside_presets=0,
                         visibility=identity.VISIBILITY_STORED_ONLY)

    def test_a_column_of_five_tabs_with_taller_lines(self):
        patch = builder()
        items = ["Env 1·2", "Env 3·4", "Random 1·2", "Seq B–D", "Pressure"]
        tabs = patch.tabs("Tab", "Tab", items, 12, layout_rules.VIEW_Y, 68, "one", initial_outside_presets=0, rows=5,
                          row_height=24, visibility=identity.VISIBILITY_HIDDEN)
        box = patch.find(tabs)
        self.assertEqual(box["presentation_rect"], [12.0, float(layout_rules.VIEW_Y), 68.0, 120.0])
        self.assertEqual(box["num_lines_presentation"], 5)
        self.assertEqual(layout_rules.live_tabs_width(items, rows=5), 68, "'Random 1·2': 60.6 + 6 = 66.6")
        with self.assertRaisesRegex(BuildError, "less than the row band"):
            patch.tabs("Pick", "Pick", items, 100, layout_rules.VIEW_Y, 68, "two", initial_outside_presets=0, rows=5,
                       row_height=12)

    def test_seed_as_a_dial_is_the_numbox_parameter_in_another_box(self):
        def seed_identity(make):
            patch = builder(PresetBook({"neutral": {}, "init": {"Volume": 0, "Seed": 0, "Loop": "16 bars"}, "presets": [
                {"name": "init", "group": "init", "idea": "i", "values": {}}]}, "b"),
                            info_keys=())
            random = SeededRandom(patch, patch.brain, 1)
            make(random)
            with self.assertRaisesRegex(BuildError, "made twice"):
                random.seed_dial(200, layout_rules.DIAL_Y, "two")
            (seed,) = [identity.parameter_identity(box, valueof)
                       for box, valueof in identity.live_parameter_boxes(patch.patch())
                       if valueof["parameter_longname"] == "Seed"]
            return seed
        numbox = seed_identity(lambda random: random.seed_control(12, layout_rules.ROW_Y, 40, "one"))
        dial = seed_identity(lambda random: random.seed_dial(12, layout_rules.DIAL_Y, "one"))
        self.assertEqual((numbox.pop("maxclass"), dial.pop("maxclass")), ("live.numbox", "live.dial"))
        self.assertEqual(numbox, dial, "Live knows it by the same name, range, unit and initial value")


if __name__ == "__main__":
    unittest.main(verbosity=2)

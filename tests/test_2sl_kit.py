#!/usr/bin/env python3
"""Tests for the 2sl kit's build checks (src/2sl_kit.py): python3 tests/test_2sl_kit.py

The layout check (nothing shown at the same time overlaps or leaves the device), groups (a selector shows one group
of boxes at a time) and controls kept out of presets. Builds small patches in memory; writes nothing."""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
kit = importlib.import_module("2sl_kit")


TARGET = "obj-1"    # the gen~ box builder() makes first: the header's Volume and the test controls talk to it


def builder(width=400, base=None):
    info = {name: (name, "text") for name in ("A", "B", "C", "Volume", "Page", "Preset", "Stop", "Link view", "Pick",
                                              "Tool")}
    patch = kit.DevicePatchBuilder(device_name="t", script_name="t", version="0", subtitle="", page_names=["one", "two"],
                                   info=info, base=base or {"A": 0, "B": 0, "C": 0, "Volume": 0}, link_chip_text="t",
                                   device_width=width)
    target = patch.box("gen~")
    assert target == TARGET
    patch.header(volume_target=target, preset_x=140, preset_w=60)
    return patch


def expect_failure(action, words):
    try:
        action()
    except kit.BuildError as problem:
        assert words in str(problem), f"the failure says {problem}, not {words!r}"
        return
    raise AssertionError(f"no build failure (expected one about {words!r})")


def test_overlap_on_one_page_fails():
    patch = builder()
    patch.dial("A", "A", TARGET, "a", 0, 1, 0, 12, 119, "one")
    patch.dial("B", "B", TARGET, "b", 0, 1, 0, 40, 119, "one")
    expect_failure(patch.check_layout, "overlaps")


def test_same_place_on_other_pages_is_fine():
    patch = builder()
    patch.dial("A", "A", TARGET, "a", 0, 1, 0, 12, 119, "one")
    patch.dial("B", "B", TARGET, "b", 0, 1, 0, 12, 119, "two")
    patch.check_layout()


def test_groups_share_a_place_but_not_within_one():
    patch = builder()
    patch.group_selector("Pick", "Pick", ["x", "y"], 12, 98, 100, "one")
    patch.dial("A", "A", TARGET, "a", 0, 1, 0, 12, 119, "one", group=("pick", 0))
    patch.dial("B", "B", TARGET, "b", 0, 1, 0, 12, 119, "one", group=("pick", 1))
    patch.check_layout()
    assert patch.find_by_varname("b")["hidden"] == 1, "the second group starts hidden"
    patch.dial("C", "C", TARGET, "c", 0, 1, 0, 30, 119, "one", group=("pick", 1))
    expect_failure(patch.check_layout, "overlaps")


def test_a_box_off_the_device_fails():
    patch = builder(width=200)
    patch.dial("A", "A", TARGET, "a", 0, 1, 0, 180, 119, "one")
    expect_failure(patch.check_layout, "leaves")


def test_the_header_moves_with_the_width_and_must_be_on_the_grid():
    patch = builder(width=640)
    assert patch.find_by_varname("stop")["presentation_rect"][0] == 580
    expect_failure(lambda: builder(width=642), "4 px grid")


def test_controls_with_their_own_initial_value_stay_out_of_presets():
    patch = builder()
    patch.numbox("Tool", "Tool", TARGET, "tool", 0, 10, 0, 12, 40, 40, "one", integer=True, initial_outside_presets=3)
    assert "Tool" not in patch.preset_varname_by_control
    assert patch.initial_values["Tool"] == 3
    expect_failure(lambda: patch.numbox("A", "A", TARGET, "a", 0, 10, 0, 60, 40, 40, "one", initial_outside_presets=1),
                   "is in BASE")
    expect_failure(lambda: patch.numbox("C", "C", TARGET, "c", 0, 999, 0, 60, 60, 40, "one", integer=True), "256 values")


def test_any_control_can_select_groups_and_must_start_on_the_first():
    patch = builder()
    picker = patch.dial("Pick", "Pick", TARGET, "pick", 0, 0, 0, 12, 119, "one", items=["x", "y"],
                        initial_outside_presets=0)
    patch.groups_selected_by(picker, 2, "one")
    patch.dial("A", "A", TARGET, "a", 0, 1, 0, 60, 119, "one", group=("pick", 0))
    patch.dial("B", "B", TARGET, "b", 0, 1, 0, 60, 119, "one", group=("pick", 1))
    patch.check_layout()
    assert patch.find_by_varname("b")["hidden"] == 1, "the second group starts hidden"
    assert ("Pick", patch.header_boxes["ui"], "group pick", None) in patch.control_routes, "the UI hears the selector"
    late = patch.dial("Tool", "Tool", TARGET, "tool", 0, 3, 0, 120, 119, "one", integer=True, initial_outside_presets=2)
    expect_failure(lambda: patch.groups_selected_by(late, 4, "one"), "initial value 0")


def test_dials_are_floats_ints_or_enums():
    patch = builder()
    saved = lambda box: patch.find(box)["saved_attribute_attributes"]["valueof"]
    assert saved(patch.dial("A", "A", TARGET, "a", 0, 10, 0, 12, 119, "one"))["parameter_type"] == 0
    assert saved(patch.dial("B", "B", TARGET, "b", 0, 10, 0, 60, 119, "one", integer=True))["parameter_type"] == 1
    enum = saved(patch.dial("Tool", "Tool", TARGET, "t", 0, 0, 0, 108, 119, "one", items=["p", "q"],
                            initial_outside_presets=1))
    assert (enum["parameter_type"], enum["parameter_enum"], enum["parameter_mmax"], enum["parameter_initial"]) == (2, ["p", "q"], 1, [1])
    expect_failure(lambda: patch.dial("C", "C", TARGET, "c", 0, 999, 0, 156, 119, "one", integer=True), "256 values")


def find_by_varname(self, varname):
    found = [x["box"] for x in self.boxes if x["box"].get("varname") == varname]
    assert len(found) == 1, f"{len(found)} boxes named {varname}"
    return found[0]


kit.DevicePatchBuilder.find_by_varname = find_by_varname

if __name__ == "__main__":
    tests = [(name, test) for name, test in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for name, test in tests:
        try:
            test()
            print(f"ok   {name}")
        except AssertionError as problem:
            failed += 1
            print(f"FAIL {name}: {problem}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

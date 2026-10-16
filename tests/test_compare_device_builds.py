"""Tests for tools/compare_device_builds.py.

Builds the kit's fixture device (tests/fixture_device.py) once into a temporary device repository, copies that
build (NAME.maxpat, NAME.amxd, its .js and .adv files, and dist/ with the frozen .amxd and its presets) for each test,
alters the copy in one way, and checks the comparison's exit status and report. Set COMPARE_DEVICE_BUILDS_FOLDER to
test against another build folder instead (2sl stab's saved baseline, say)."""
import contextlib
import gzip
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "tools")]
import compare_device_builds as comparison  # noqa: E402
import fixture_device  # noqa: E402

BUILD_FOLDER = None
FIXTURE_FOLDER = None


def setUpModule():
    global BUILD_FOLDER, FIXTURE_FOLDER
    if os.environ.get("COMPARE_DEVICE_BUILDS_FOLDER"):
        BUILD_FOLDER = os.path.abspath(os.environ["COMPARE_DEVICE_BUILDS_FOLDER"])
        return
    FIXTURE_FOLDER = tempfile.mkdtemp(prefix="compare-device-builds-fixture-")
    with contextlib.redirect_stdout(io.StringIO()):
        fixture_device.build_fixture_device(FIXTURE_FOLDER)
    BUILD_FOLDER = FIXTURE_FOLDER


def tearDownModule():
    if FIXTURE_FOLDER:
        shutil.rmtree(FIXTURE_FOLDER)


def run_comparison(baseline_folder, candidate_folder, *extra_arguments):
    captured_output, captured_errors = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(captured_output), contextlib.redirect_stderr(captured_errors):
        exit_status = comparison.main([baseline_folder, candidate_folder, *extra_arguments])
    return exit_status, captured_output.getvalue() + captured_errors.getvalue()


def only_file(folder, suffix, frozen):
    matches = []
    for directory_path, _, file_names in os.walk(folder):
        for file_name in file_names:
            path = os.path.join(directory_path, file_name)
            if file_name.endswith(suffix) and (suffix != ".amxd" or comparison.read_amxd(path)["is_frozen"] == frozen):
                matches.append(path)
    if len(matches) != 1:
        raise AssertionError(f"{folder}: expected one {'frozen' if frozen else 'unfrozen'} *{suffix}, found {matches}")
    return matches[0]


def first_preset(folder):
    for directory_path, _, file_names in sorted(os.walk(folder)):
        for file_name in sorted(file_names):
            if file_name.endswith(".adv"):
                return os.path.join(directory_path, file_name)
    raise AssertionError(f"{folder}: no .adv preset to alter")


class CompareDeviceBuildsTests(unittest.TestCase):
    def setUp(self):
        if not os.path.isdir(BUILD_FOLDER):
            raise AssertionError(f"no build folder to test with at {BUILD_FOLDER}")
        self.temporary_folder = tempfile.mkdtemp(prefix="compare-device-builds-")
        self.candidate_folder = os.path.join(self.temporary_folder, os.path.basename(BUILD_FOLDER))
        shutil.copytree(BUILD_FOLDER, self.candidate_folder)

    def tearDown(self):
        shutil.rmtree(self.temporary_folder)

    def edit_maxpat(self, edit_patch):
        maxpat_path = only_file(self.candidate_folder, ".maxpat", frozen=False)
        with open(maxpat_path) as maxpat_file:
            patch = json.load(maxpat_file)
        edit_patch(patch)
        with open(maxpat_path, "w") as maxpat_file:
            json.dump(patch, maxpat_file, indent="\t")

    def parameter_boxes(self, patch):
        return [wrapped["box"] for wrapped in patch["patcher"]["boxes"]
                if wrapped["box"].get("saved_attribute_attributes", {}).get("valueof")]

    def test_a_build_against_itself_has_no_differences(self):
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_SAME, report)
        self.assertIn("no differences", report)

    def test_a_renamed_parameter_fails(self):
        def rename_first_parameter(patch):
            self.parameter_boxes(patch)[0]["saved_attribute_attributes"]["valueof"]["parameter_longname"] = "Renamed"
        self.edit_maxpat(rename_first_parameter)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)
        self.assertIn("parameter 'Renamed' is only in the candidate", report)
        self.assertIn("FAIL", report)

    def test_reordered_parameters_fail(self):
        def swap_first_two_parameter_boxes(patch):
            boxes = patch["patcher"]["boxes"]
            first, second = [index for index, wrapped in enumerate(boxes)
                             if wrapped["box"].get("saved_attribute_attributes", {}).get("valueof")][:2]
            boxes[first], boxes[second] = boxes[second], boxes[first]
        self.edit_maxpat(swap_first_two_parameter_boxes)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)
        self.assertIn("parameter order differs", report)

    def test_a_changed_parameter_range_fails(self):
        def widen_first_range(patch):
            self.parameter_boxes(patch)[0]["saved_attribute_attributes"]["valueof"]["parameter_mmax"] = 12345
        self.edit_maxpat(widen_first_range)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)
        self.assertIn("parameter_mmax", report)

    def test_writing_a_default_explicitly_is_not_gated(self):
        def write_default_exponent(patch):
            for box in self.parameter_boxes(patch):
                box["saved_attribute_attributes"]["valueof"].setdefault("parameter_exponent", 1.0)
        self.edit_maxpat(write_default_exponent)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_SAME, report)

    def test_new_box_ids_and_patching_rects_are_no_difference(self):
        def renumber_and_move_every_box(patch):
            new_id_by_old_id = {}
            for index, wrapped in enumerate(reversed(patch["patcher"]["boxes"])):
                new_id_by_old_id[wrapped["box"]["id"]] = f"renumbered-{index}"
            for wrapped in patch["patcher"]["boxes"]:
                wrapped["box"]["id"] = new_id_by_old_id[wrapped["box"]["id"]]
                wrapped["box"]["patching_rect"] = [1.0, 2.0, 3.0, 4.0]
            for wrapped_line in patch["patcher"]["lines"]:
                wrapped_line["patchline"]["source"][0] = new_id_by_old_id[wrapped_line["patchline"]["source"][0]]
                wrapped_line["patchline"]["destination"][0] = new_id_by_old_id[wrapped_line["patchline"]["destination"][0]]
        self.edit_maxpat(renumber_and_move_every_box)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder, "--fail-on-reported")
        # the unfrozen .amxd still holds the old ids: only the self-consistency check may notice
        self.assertIn("    0  reported  (b)", report)
        self.assertIn("    0  reported  (c)", report)
        self.assertIn("    0  GATED     (a)", report)

    def test_a_removed_wire_is_reported_not_gated(self):
        self.edit_maxpat(lambda patch: patch["patcher"]["lines"].pop(0))
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_SAME, report)
        self.assertIn("wire only in the baseline", report)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder, "--fail-on-reported")
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)

    def test_changed_gen_code_is_reported_with_a_diff(self):
        def change_gen_code(patch):
            for wrapped in patch["patcher"]["boxes"]:
                for inner in wrapped["box"].get("patcher", {}).get("boxes", []):
                    if inner["box"].get("maxclass") == "codebox":
                        inner["box"]["code"] += "\n// altered by the test\n"
                        return
            raise AssertionError("no codebox in the patch")
        self.edit_maxpat(change_gen_code)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertIn("embedded patcher differs", report)
        self.assertIn("+    | // altered by the test", report)

    def test_changed_js_is_reported(self):
        script_folder = os.path.dirname(only_file(self.candidate_folder, ".amxd", frozen=False))
        script_names = sorted(name for name in os.listdir(script_folder) if name.endswith(".js"))
        self.assertTrue(script_names, f"no .js beside the unfrozen .amxd in {script_folder}")
        script_path = os.path.join(script_folder, script_names[0])
        with open(script_path, "a") as script_file:
            script_file.write("\n// altered by the test\n")
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_SAME, report)
        self.assertIn("+// altered by the test", report)

    def edit_first_preset(self, edit_xml_text):
        preset_path = first_preset(self.candidate_folder)
        with gzip.open(preset_path, "rb") as preset_file:
            xml_text = preset_file.read().decode("utf-8")
        altered_xml_text = edit_xml_text(xml_text)
        self.assertNotEqual(altered_xml_text, xml_text, "the test's edit changed nothing")
        with open(preset_path, "wb") as preset_file:
            preset_file.write(gzip.compress(altered_xml_text.encode("utf-8"), mtime=0))

    def test_a_changed_preset_value_fails(self):
        self.edit_first_preset(lambda xml_text: xml_text.replace("<Manual Value=\"", "<Manual Value=\"9", 2)
                               .replace("<Manual Value=\"9true", "<Manual Value=\"true"))
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)
        self.assertIn("Timeable/Manual", report)

    def test_a_changed_stored_only_blob_fails(self):
        def change_blob(xml_text):
            blob_start = xml_text.index("<Blob>") + len("<Blob>")
            first_digit_position = next(i for i in range(blob_start, len(xml_text)) if xml_text[i] in "0123456789ABCDEF")
            replacement = "7" if xml_text[first_digit_position] != "7" else "6"
            return xml_text[:first_digit_position] + replacement + xml_text[first_digit_position + 1:]
        self.edit_first_preset(change_blob)
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)
        self.assertIn("stored-only blob", report)

    def test_a_missing_preset_fails(self):
        os.remove(first_preset(self.candidate_folder))
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_DIFFERENT, report)
        self.assertIn("only in the baseline", report)

    def test_new_freeze_timestamps_are_no_difference(self):
        frozen_path = only_file(self.candidate_folder, ".amxd", frozen=True)
        with open(frozen_path, "rb") as frozen_file:
            frozen_bytes = bytearray(frozen_file.read())
        timestamp_positions = [i for i in range(len(frozen_bytes) - 4) if frozen_bytes[i:i + 4] == b"mdat"]
        self.assertTrue(timestamp_positions, "no mdat fields in the frozen device")
        for position in timestamp_positions:
            frozen_bytes[position + 8:position + 12] = struct.pack(">I", 12345)
        with open(frozen_path, "wb") as frozen_file:
            frozen_file.write(bytes(frozen_bytes))
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder, "--fail-on-reported")
        self.assertEqual(exit_status, comparison.EXIT_STATUS_SAME, report)

    def test_an_unreadable_build_fails_loudly(self):
        exit_status, report = run_comparison(BUILD_FOLDER, os.path.join(self.temporary_folder, "no such build"))
        self.assertEqual(exit_status, comparison.EXIT_STATUS_BAD_INPUT, report)
        self.assertIn("can't compare", report)

    def test_a_corrupt_preset_fails_loudly(self):
        with open(first_preset(self.candidate_folder), "wb") as preset_file:
            preset_file.write(b"not gzip")
        exit_status, report = run_comparison(BUILD_FOLDER, self.candidate_folder)
        self.assertEqual(exit_status, comparison.EXIT_STATUS_BAD_INPUT, report)
        self.assertIn("not a gzipped Live preset", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)

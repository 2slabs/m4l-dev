"""build_device end to end, on the kit's fixture device (tests/fixture_device.py) in temporary device repositories:
what it writes, that it writes the same bytes every time, the Live parameter lock, stale presets, and its refusals."""
import contextlib
import gzip
import hashlib
import io
import os
import shutil
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import fixture_device  # noqa: E402
from twosl_dsp import amxd  # noqa: E402
from twosl_dsp import live_preset_files  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.device_repository import KIT_DIRECTORY, DeviceRepository  # noqa: E402
from twosl_dsp.display_text import display_texts  # noqa: E402

DEVICE_FOLDER = os.path.join("devices", fixture_device.FIXTURE_SCRIPT_NAME)


def quietly(action, *arguments, **keywords):
    with contextlib.redirect_stdout(io.StringIO()) as log:
        result = action(*arguments, **keywords)
    return result, log.getvalue()


def fingerprints(root):
    """{path relative to root: sha1} for everything the build writes (devices/ and dist/)."""
    found = {}
    for top in ("devices", "dist"):
        for directory_path, _, file_names in os.walk(os.path.join(root, top)):
            for file_name in file_names:
                path = os.path.join(directory_path, file_name)
                with open(path, "rb") as built_file:
                    found[os.path.relpath(path, root)] = hashlib.sha1(built_file.read()).hexdigest()
    return found


# the "loud" preset's Stored Only blob: the device's own Memory, and the stored table Stage (Pitch 12, -24 at 1365
# codes a semitone from -24; row 2's switches: Pulse on (bit 0) + Wait keyed (3, bits 1-2) = 7)
# every preset holds the fresh-start flag at 1: a preset loaded is never moved to the Init sound
LOUD_STORED_ONLY_BLOB = ('{\n    "Init Applied": [ 1 ],\n    "Memory": [ 97 ],\n    "Stage Pitch 1": [ 49140 ],\n    "Stage Pitch 2": [ 0 ],\n'
                         '    "Stage switches 1": [ 0 ],\n    "Stage switches 2": [ 7 ]\n}')

# the fixture's level display painter, and a top line drawn by hand, not by the kit's heading: a reading too long
# for the line beside the label, right-aligned over it
LEVEL_PAINTER = "level: function (w, h) { "
CROWDED_TOP_LINE = 'text("a reading too long to fit", w - measure("a reading too long to fit") - 4, 12, T.ink); '


class FixtureBuildTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="kit-fixture-")
        quietly(fixture_device.build_fixture_device, self.root)

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_it_writes_the_development_build_and_the_release(self):
        written = sorted(fingerprints(self.root))
        self.assertEqual(written, sorted([
            f"{DEVICE_FOLDER}/kit-fixture.maxpat", f"{DEVICE_FOLDER}/kit-fixture.amxd", f"{DEVICE_FOLDER}/kit-fixture.js",
            f"{DEVICE_FOLDER}/kit-fixture-ui.js", f"{DEVICE_FOLDER}/kit-fixture-view.js", f"{DEVICE_FOLDER}/init.adv",
            f"{DEVICE_FOLDER}/test - loud.adv", "dist/kit-fixture-1.2.3/kit-fixture-1.2.3.amxd",
            "dist/kit-fixture-1.2.3/init.adv", "dist/kit-fixture-1.2.3/test - loud.adv", "dist/kit-fixture-1.2.3.zip"]))
        with open(os.path.join(self.root, "dist/kit-fixture-1.2.3/kit-fixture-1.2.3.amxd"), "rb") as frozen_file:
            frozen = amxd.read_device(frozen_file.read(), "the frozen fixture")
        self.assertEqual([entry["fnam"] for entry in frozen["frozen_files"]],
                         ["kit-fixture-1.2.3.amxd", "kit-fixture.js", "kit-fixture-ui.js", "kit-fixture-view.js"])
        self.assertEqual({entry["mdat"] for entry in frozen["frozen_files"]}, {amxd.FROZEN_FILE_MODIFICATION_DATE})

    def test_a_rebuild_writes_the_same_bytes(self):
        before = fingerprints(self.root)
        quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=())
        self.assertEqual(fingerprints(self.root), before)

    def test_presets_are_gzipped_with_a_fixed_header_and_hold_the_stored_only_values(self):
        with open(os.path.join(self.root, DEVICE_FOLDER, "test - loud.adv"), "rb") as preset_file:
            preset_bytes = preset_file.read()
        self.assertEqual(preset_bytes[:10], live_preset_files.GZIP_HEADER)
        xml_text = gzip.decompress(preset_bytes).decode()
        self.assertIn('<Name Value="Level" />', xml_text)
        self.assertNotIn('Value="Page"', xml_text, "the Hidden page switch is in no preset")
        blob_hex = xml_text.split("<Blob>")[1].split("</Blob>")[0]
        self.assertEqual(bytes.fromhex("".join(blob_hex.split())).rstrip(b"\0").decode(), LOUD_STORED_ONLY_BLOB)

    def test_a_changed_parameter_fails_with_a_diff_and_writes_nothing(self):
        before = fingerprints(self.root)

        def rename_level(patch):
            for wrapped in patch.boxes:
                valueof = wrapped["box"].get("saved_attribute_attributes", {}).get("valueof", {})
                if valueof.get("parameter_longname") == "Level":
                    valueof["parameter_shortname"] = "Lvl"
        with self.assertRaises(BuildError) as failure:
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), patch_edit=rename_level)
        message = str(failure.exception)
        self.assertIn("--accept-live-parameter-changes", message)
        self.assertIn('-    {"maxclass": "live.dial", "varname": "level", "long_name": "Level", "short_name": "Level"', message)
        self.assertIn('+    {"maxclass": "live.dial", "varname": "level", "long_name": "Level", "short_name": "Lvl"', message)
        self.assertEqual(fingerprints(self.root), before, "a refused build writes nothing")
        quietly(fixture_device.build_fixture_device, self.root, patch_edit=rename_level)
        with open(os.path.join(self.root, "src", "live-parameters.lock.json"), encoding="utf-8") as lock_file:
            self.assertIn('"short_name": "Lvl"', lock_file.read(), "accepted: the lock is rewritten")

    def test_a_missing_lock_fails_until_accepted(self):
        os.remove(os.path.join(self.root, "src", "live-parameters.lock.json"))
        with self.assertRaisesRegex(BuildError, "lock.json is missing"):
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=())

    def test_stale_presets_are_removed(self):
        stale = os.path.join(self.root, DEVICE_FOLDER, "old sound.adv")
        open(stale, "wb").close()
        _, log = quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=())
        self.assertFalse(os.path.exists(stale))
        self.assertIn("removed old sound.adv", log)
        quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), live_preset_files=False)
        self.assertEqual([f for f in os.listdir(os.path.join(self.root, DEVICE_FOLDER)) if f.endswith(".adv")], [])

    def test_scripts_that_are_not_es5_fail(self):
        with self.assertRaisesRegex(BuildError, "kit-fixture-view.js: SyntaxError"):
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(),
                    views_code=fixture_device.FIXTURE_VIEWS_CODE + "\nlet modern = () => 1;\n")

    def test_the_kits_heading_puts_a_reading_too_wide_beside_the_name_on_the_next_line(self):
        # the level display is 120 px: "level" (30 px), two spaces (12) and a reading fit in the 112 px inside its
        # margins up to 11 characters (66 px); 12 go right-aligned on the next line, the drawing below a line lower
        with open(os.path.join(self.root, DEVICE_FOLDER, f"{fixture_device.FIXTURE_SCRIPT_NAME}-view.js"),
                  encoding="utf-8") as views_file:
            views = views_file.read()

        def heading_texts(reading):
            painted = display_texts(views.replace('rect(4, viewHeading("level", "", w) + 2,',
                                                  f'text("below", 4, viewHeading("level", "{reading}", w) + 10, T.ink); '
                                                  'rect(4, 20,'), "level", 120, 64)
            return [(t.text, t.x, t.baseline) for t in painted]
        self.assertEqual(heading_texts(""), [("level", 4, 12), ("below", 4, 28)])
        self.assertEqual(heading_texts("eleven char"), [("level", 4, 12), ("eleven char", 50, 12), ("below", 4, 28)])
        self.assertEqual(heading_texts("twelve chars"), [("level", 4, 12), ("twelve chars", 44, 25), ("below", 4, 41)])

    def test_a_display_drawing_text_over_text_fails_naming_both_and_writes_nothing(self):
        # the level display (120 px) with a reading too long for its top line beside its label
        before = fingerprints(self.root)
        crowded = fixture_device.FIXTURE_VIEWS_CODE.replace(LEVEL_PAINTER, LEVEL_PAINTER + CROWDED_TOP_LINE)
        with self.assertRaises(BuildError) as failure:
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), views_code=crowded)
        message = str(failure.exception)
        self.assertIn("display view_level: 'a reading too long to fit' (x -33..116, y 3..15) overlaps 'level' "
                      "(x 6..33, y 3..12) by 27 x 9 px (as first painted)", message)
        self.assertIn("display view_level (120 x 64): 'a reading too long to fit' (x -33..116, y 3..15) reaches off "
                      "the display", message)
        self.assertEqual(fingerprints(self.root), before)

    def test_a_display_is_checked_at_every_value_its_controls_send_naming_what_it_was_sent(self):
        # fine as first painted (Level's Init), crowded only near the top of Level's travel
        crowded_near_full = fixture_device.FIXTURE_VIEWS_CODE.replace(
            LEVEL_PAINTER, LEVEL_PAINTER + "if (S.level > 0.9) " + CROWDED_TOP_LINE)
        with self.assertRaises(BuildError) as failure:
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(),
                    views_code=crowded_near_full)
        message = str(failure.exception)
        self.assertIn("display view_level: 'a reading too long to fit' (x -33..116, y 3..15) overlaps 'level' "
                      "(x 6..33, y 3..12) by 27 x 9 px (sent level 0.90625)", message)
        self.assertNotIn("as first painted", message)

    def test_a_declared_reading_drives_a_display(self):
        # `busy` comes from no control: only declared (view_reading) is it driven, and then its 1 is caught
        busy_code = fixture_device.FIXTURE_VIEWS_CODE.replace("{ kicks: 0 }", "{ kicks: 0, busy: 0 }").replace(
            LEVEL_PAINTER, LEVEL_PAINTER + "if (S.busy) " + CROWDED_TOP_LINE)
        quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), views_code=busy_code)

        def declare_busy(patch):
            level_view = next(box for box, mode in patch.view_mode_by_box.items() if mode == "level")
            patch.view_reading(level_view, "busy", [0, 1])
        with self.assertRaisesRegex(BuildError,
                                    r"'a reading too long to fit' .* overlaps 'level' .* \(sent level 0\.5, busy 1\)"):
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), views_code=busy_code,
                    patch_edit=declare_busy)

    def test_each_value_of_a_switch_gets_its_own_search(self):
        # mode 0 draws the wider text in total, so the widest search stays there; mode 1's reading only crowds the
        # label once Level is near full, which a search with mode 1 held finds
        modes_code = fixture_device.FIXTURE_VIEWS_CODE.replace("{ kicks: 0 }", "{ kicks: 0, mode: 0 }").replace(
            'rect(4, viewHeading("level", "", w) + 2,',
            'if (S.mode === 0) text("seventeen letters", 4, 40, T.label); '
            'else { text("level", 4, 12, T.label); var reading = S.level > 0.9 ? "a reading too long" : "fine"; '
            'text(reading, w - measure(reading) - 4, 12, T.ink); } rect(4, 20,')

        def declare_mode(patch):
            level_view = next(box for box, mode in patch.view_mode_by_box.items() if mode == "level")
            patch.view_reading(level_view, "mode", [0, 1])
        with self.assertRaisesRegex(BuildError, r"'level' .* overlaps 'a reading too long' .* \(sent level 0\.90625, "
                                                r"mode 1\)"):
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), views_code=modes_code,
                    patch_edit=declare_mode)

    def test_a_display_saying_error_at_a_value_sent_fails_the_build(self):
        complaining = fixture_device.FIXTURE_VIEWS_CODE.replace(
            LEVEL_PAINTER, LEVEL_PAINTER + 'if (S.level === 1) error("full\\n"); ')
        with self.assertRaisesRegex(BuildError, r"the 'level' display \(120 x 64\): said error\(\) sent "
                                                r'\{"level":1\}: full'):
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), views_code=complaining)

    def test_a_display_that_fails_to_paint_fails_the_build_saying_which(self):
        broken = fixture_device.FIXTURE_VIEWS_CODE.replace('viewHeading("level"', 'viewHeading(missingName')
        with self.assertRaisesRegex(BuildError, "the 'level' display .* couldn't be painted.*missingName"):
            quietly(fixture_device.build_fixture_device, self.root, command_line_arguments=(), views_code=broken)

    def test_an_audio_effect_gets_audio_effect_presets(self):
        audio_root = tempfile.mkdtemp(prefix="kit-fixture-audio-")
        try:
            def make_it_an_audio_effect(patch):
                patch.device_type = "audio"
            quietly(fixture_device.build_fixture_device, audio_root, patch_edit=make_it_an_audio_effect)
            with open(os.path.join(audio_root, DEVICE_FOLDER, "kit-fixture.amxd"), "rb") as device_file:
                self.assertEqual(amxd.read_device(device_file.read(), "the fixture")["device_type"], "audio")
            for folder in (DEVICE_FOLDER, "dist/kit-fixture-1.2.3"):
                with open(os.path.join(audio_root, folder, "test - loud.adv"), "rb") as preset_file:
                    xml_text = gzip.decompress(preset_file.read()).decode()
                self.assertIn("<MxDeviceAudioEffect>", xml_text)
                self.assertNotIn("MxDeviceInstrument", xml_text)
                self.assertIn('<Name Value="Level" />', xml_text)
                self.assertNotIn("<Path ", xml_text, "no absolute path: the preset finds the device next to it")
                blob_hex = xml_text.split("<Blob>")[1].split("</Blob>")[0]
                self.assertEqual(bytes.fromhex("".join(blob_hex.split())).rstrip(b"\0").decode(), LOUD_STORED_ONLY_BLOB)
        finally:
            shutil.rmtree(audio_root)

    def test_a_midi_effect_has_no_known_live_preset_form(self):
        def make_it_a_midi_effect(patch):
            patch.device_type = "midi"
        with self.assertRaisesRegex(BuildError, "only a Max \\['audio', 'instrument'\\] has a known form"):
            quietly(fixture_device.build_fixture_device, self.root, patch_edit=make_it_a_midi_effect)

    def test_an_int_parameter_has_no_known_live_preset_form(self):
        def add_an_int_dial(patch):
            patch.info["Count"] = ("Count", "how many")
            patch.dial("Count", "Count", next(iter(patch.gen_params_by_box)), None, 0, 7, 0, 60, 119, "one", integer=True,
                       initial_outside_presets=0, kit_neutral=0)
        with self.assertRaisesRegex(BuildError, "'Count' has parameter_type 1"):
            quietly(fixture_device.build_fixture_device, self.root, patch_edit=add_an_int_dial)


class DeviceRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="kit-repository-")
        self.build_script = os.path.join(self.root, "build.py")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_a_repository_needs_src(self):
        with self.assertRaisesRegex(BuildError, "no src/"):
            DeviceRepository.of_build_script(self.build_script)

    def test_a_repository_needs_the_kit_as_its_submodule(self):
        os.makedirs(os.path.join(self.root, "src"))
        with self.assertRaisesRegex(BuildError, "git submodule update --init"):
            DeviceRepository.of_build_script(self.build_script)
        os.makedirs(os.path.join(self.root, "2sl-dsp", "twosl_dsp"))
        with self.assertRaisesRegex(BuildError, "isn't a git submodule checkout"):
            DeviceRepository.of_build_script(self.build_script)
        open(os.path.join(self.root, "2sl-dsp", ".git"), "w").close()
        with self.assertRaisesRegex(BuildError, "not this repository's submodule"):
            DeviceRepository.of_build_script(self.build_script)

    def test_the_kit_is_never_written(self):
        os.makedirs(os.path.join(self.root, "src"))
        repository = DeviceRepository(self.root)
        with self.assertRaisesRegex(BuildError, "inside the kit"):
            repository.check_writable(os.path.join(KIT_DIRECTORY, "devices", "x.amxd"))
        with self.assertRaisesRegex(BuildError, "outside the repository"):
            repository.check_writable(os.path.join(tempfile.gettempdir(), "elsewhere.amxd"))
        with self.assertRaisesRegex(BuildError, "the kit itself"):
            DeviceRepository(KIT_DIRECTORY)


class FrozenDeviceTests(unittest.TestCase):
    def test_a_frozen_device_reads_back(self):
        patch = {"patcher": {"boxes": [], "lines": []}}
        frozen_bytes = amxd.frozen_device_bytes(patch, "audio", "x-1.amxd", [("a.js", b"var a = 1;")])
        self.assertEqual(frozen_bytes, amxd.frozen_device_bytes(patch, "audio", "x-1.amxd", [("a.js", b"var a = 1;")]))
        device = amxd.read_device(frozen_bytes, "x-1.amxd")
        self.assertEqual(device["device_type"], "audio")
        self.assertEqual([(e["fnam"], e["data"]) for e in device["frozen_files"]][1], ("a.js", b"var a = 1;"))
        self.assertEqual(struct.unpack("<I", frozen_bytes[20:24])[0], 7)
        with self.assertRaisesRegex(BuildError, "device type"):
            amxd.unfrozen_device_bytes(patch, "drum rack")


if __name__ == "__main__":
    unittest.main(verbosity=2)

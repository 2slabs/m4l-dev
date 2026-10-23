"""tools/render_pages.py on the kit's fixture device built into a temporary repository: an image of every page and
every group choice, at the device's size, and a refusal when a box leaves the device."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

try:
    from PIL import Image
except ImportError as missing:   # a test requirement (README, requirements-test.txt), so say how to get it
    raise ImportError("the kit's tests need Pillow: brew install pillow, or pip install -r requirements-test.txt") from missing

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(os.path.dirname(HERE), "tools")]
import fixture_device  # noqa: E402
import render_pages  # noqa: E402
from twosl_dsp import layout_rules  # noqa: E402


class RenderPagesTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="render-pages-")
        with contextlib.redirect_stdout(io.StringIO()):
            fixture_device.build_fixture_device(self.root)
        self.device_folder = os.path.join(self.root, "devices", fixture_device.FIXTURE_SCRIPT_NAME)
        self.output = os.path.join(self.root, "pages")

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_every_page_and_group_choice_is_drawn_at_the_device_size(self):
        device = render_pages.Device(self.device_folder)
        expected = [os.path.join(self.output, f"{stem}.png") for _, _, _, stem in device.views()]
        written = render_pages.render_device(self.device_folder, self.output, scale=2)
        self.assertEqual(written, expected)
        self.assertEqual({page for _, page, _, _ in device.views()}, set(device.page_names))
        for path in written:
            with Image.open(path) as image:
                self.assertEqual(image.size, (device.width * 2, layout_rules.DEVICE_HEIGHT * 2))
        with open(os.path.join(self.output, "layout.txt"), encoding="utf-8") as facts_file:
            facts = facts_file.read()
        for page in device.page_names:
            self.assertIn(f"{page}.png", facts)

    def test_a_column_of_five_taller_tabs_draws_its_names_and_keeps_the_contract(self):
        """The mod page's tab column (2sl gate SPEC v0.7 §5): five lines of 24 px, 68 px wide ('Random 1·2', the
        longest, and its padding), with a middle dot and an en dash."""
        items = ["Env 1·2", "Env 3·4", "Random 1·2", "Seq B–D", "Pressure"]
        with contextlib.redirect_stdout(io.StringIO()):
            fixture_device.build_fixture_device(self.root, patch_edit=lambda patch: patch.tabs(
                "Mod tab", "Mod tab", items, 400, layout_rules.VIEW_Y, 68, "two", initial_outside_presets=0, rows=5,
                row_height=24, visibility=2))
        render_pages.render_device(self.device_folder, self.output, scale=1)
        with open(os.path.join(self.output, "layout.txt"), encoding="utf-8") as facts_file:
            facts = facts_file.read()
        self.assertIn("mod_tab [live.tab] x 400 w 68 h 120", facts)
        self.assertNotIn("contract: mod_tab", facts)

    def test_a_text_that_does_not_fit_its_control_fails_saying_which(self):
        # the build's own rules (layout_rules), on what the build wrote: a dial narrowed to 20 px after it
        patcher_path = os.path.join(self.device_folder, f"{fixture_device.FIXTURE_SCRIPT_NAME}.maxpat")
        with open(patcher_path, encoding="utf-8") as patcher_file:
            patch = json.load(patcher_file)
        narrowed = next(entry["box"] for entry in patch["patcher"]["boxes"]
                        if entry["box"].get("maxclass") == "live.dial" and entry["box"].get("presentation") == 1)
        narrowed["presentation_rect"][2] = 20
        with open(patcher_path, "w", encoding="utf-8") as patcher_file:
            json.dump(patch, patcher_file)
        with self.assertRaises(render_pages.RenderFailure) as failure:
            render_pages.render_device(self.device_folder, self.output)
        self.assertIn(f"{narrowed['varname']} (live.dial): its text doesn't fit", str(failure.exception))

    def test_a_display_drawing_text_over_text_fails_saying_which(self):
        # the build's own rule on what the build wrote: the level display's script given a second text on its label
        views_path = os.path.join(self.device_folder, f"{fixture_device.FIXTURE_SCRIPT_NAME}-view.js")
        with open(views_path, encoding="utf-8") as views_file:
            views = views_file.read()
        with open(views_path, "w", encoding="utf-8") as views_file:
            views_file.write(views.replace('level: function (w, h) { ', 'level: function (w, h) { text("over", 8, 12, T.ink); '))
        with self.assertRaises(render_pages.RenderFailure) as failure:
            render_pages.render_device(self.device_folder, self.output)
        self.assertIn("display view_level: 'over' (x 9..32, y 6..12) overlaps 'level' (x 6..33, y 3..12)", str(failure.exception))

    def test_the_stand_in_font_is_the_one_the_rules_measure_by(self):
        font = render_pages.load_live_font()             # fails when the table and the font file disagree
        self.assertAlmostEqual(font.getlength("FM amount"), layout_rules.live_text_width("FM amount"), places=6)

    def test_a_box_off_the_device_fails_saying_which(self):
        patcher_path = os.path.join(self.device_folder, f"{fixture_device.FIXTURE_SCRIPT_NAME}.maxpat")
        with open(patcher_path, encoding="utf-8") as patcher_file:
            patch = json.load(patcher_file)
        moved = next(entry["box"] for entry in patch["patcher"]["boxes"]
                     if entry["box"].get("maxclass") == "live.dial" and entry["box"].get("presentation") == 1)
        moved["presentation_rect"][0] = patch["patcher"]["devicewidth"] - 10
        with open(patcher_path, "w", encoding="utf-8") as patcher_file:
            json.dump(patch, patcher_file)
        with self.assertRaises(render_pages.RenderFailure) as failure:
            render_pages.render_device(self.device_folder, self.output)
        self.assertIn(moved["varname"], str(failure.exception))
        self.assertIn("level's box (x 470..514, y 119..167) reaches off the 480 x 169 device", str(failure.exception))


if __name__ == "__main__":
    unittest.main()

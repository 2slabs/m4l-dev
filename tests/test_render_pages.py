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
from m4l_dev import layout_rules  # noqa: E402


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
        self.assertIn("leaves the", str(failure.exception))


if __name__ == "__main__":
    unittest.main()

"""A fresh device moves to its start values once; a saved set or preset keeps its own (twosl_dsp/fresh_start.py running
the fixture's built UI script in node, architecture/presets.md "Neutral, Init, and a fresh device")."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import fixture_device  # noqa: E402
from twosl_dsp import fresh_start  # noqa: E402
from twosl_dsp.preset_book import PresetBook, SavedRecord  # noqa: E402


class FreshStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="kit-fresh-start-")
        with contextlib.redirect_stdout(io.StringIO()):
            repository = fixture_device.build_fixture_device(cls.root)
        cls.folder = os.path.join(cls.root, "devices", fixture_device.FIXTURE_SCRIPT_NAME)
        cls.patch = fixture_device.fixture_patch(PresetBook.from_file(repository.source_path("presets.json"),
                                                                      "src/presets.json"))
        cls.presets = cls.patch.check(fixture_device.FIXTURE_LAYOUT)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def test_a_fresh_device_holds_its_start_values_after_ready(self):
        after = fresh_start.held_by_name(self.patch, fresh_start.controls_after_ready(self.folder))
        controls = [name for name in self.patch.saved_controls if not isinstance(self.patch.saved_controls[name], SavedRecord)]
        self.assertEqual({name: after[name] for name in controls},
                         {name: self.patch.initial_values[name] for name in controls})
        self.assertNotEqual(self.patch.neutral_values["Level"], self.patch.initial_values["Level"],
                            "the fixture has a control whose neutral isn't its Init")

    def test_a_saved_set_or_preset_comes_back_as_saved(self):
        loud = next(p for p in self.presets if p.name == "loud")
        saved = fresh_start.saved_values_of(self.patch, loud.values)
        after = fresh_start.controls_after_ready(self.folder, saved)
        self.assertEqual({name: after[name] for name in saved}, saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)

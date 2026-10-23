"""Tests for twosl_dsp/build_comparison.py: two builds are the same build only when they are the same to the last
digit (the kit writes the same bytes on every machine: twosl_dsp/generated_numbers.py), and a difference says where."""
import gzip
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.amxd import unfrozen_device_bytes  # noqa: E402
from twosl_dsp.build_comparison import build_differences, file_difference  # noqa: E402

# the numbers 2sl filter's build printed on two machines (2026-10-20), before generated_numbers: the same
# coefficients, the last digits apart; now a difference
ONE_MACHINE = ["0.6095243148961883", "0.8492238103920661", "0.4607745049614506"]
ANOTHER_MACHINE = ["0.6095243148961881", "0.849223810392066", "0.46077450496145034"]


def gen_code(numbers):
    return "y = " + " + ".join(f"{n} * x{i}" for i, n in enumerate(numbers)) + ";"


def patch(numbers, latency=30, label="drive"):
    return {"patcher": {"latency": latency, "boxes": [
        {"box": {"maxclass": "gen~", "code": gen_code(numbers), "gain": float(numbers[0])}},
        {"box": {"maxclass": "live.dial", "varname": label}}]}}


def preset(size, crc, value="0.5", level=9):
    return gzip.compress((f'<Ableton><MxDeviceAudioEffect><OriginalFileSize Value="{size}" />'
                          f'<OriginalCrc Value="{crc}" /><Value Value="{value}" /></MxDeviceAudioEffect></Ableton>').encode(),
                         compresslevel=level)


class BuildComparisonTests(unittest.TestCase):
    def test_the_same_build_is_the_same(self):
        self.assertIsNone(file_difference("d.maxpat", json.dumps(patch(ONE_MACHINE)).encode(),
                                          json.dumps(patch(ONE_MACHINE)).encode()))
        self.assertIsNone(file_difference("d.amxd", unfrozen_device_bytes(patch(ONE_MACHINE), "audio"),
                                          unfrozen_device_bytes(patch(ONE_MACHINE), "audio")))

    def test_last_digits_are_a_difference_and_it_says_where(self):
        found = file_difference("d.maxpat", json.dumps(patch(ONE_MACHINE)).encode(),
                                json.dumps(patch(ANOTHER_MACHINE)).encode())
        self.assertIn("d.maxpat.patcher.boxes[0].box.code", found)
        self.assertIn("0.6095243148961883", found)
        self.assertIn("d.amxd.patcher.boxes[0].box.code: the text differs at character 21",
                      file_difference("d.amxd", unfrozen_device_bytes(patch(ONE_MACHINE), "audio"),
                                      unfrozen_device_bytes(patch(ANOTHER_MACHINE), "audio")))
        self.assertIn("d-ui.js", file_difference("d-ui.js", f"var K = {ONE_MACHINE[0]};".encode(),
                                                 f"var K = {ANOTHER_MACHINE[0]};".encode()))

    def test_a_preset_is_its_xml_not_its_compression(self):
        self.assertIsNone(file_difference("init.adv", preset(264257, 48021), preset(264257, 48021, level=1)))
        self.assertIn("OriginalCrc", file_difference("init.adv", preset(264257, 48021), preset(264257, 23446)))
        self.assertIn("'0.5' vs '0.6'", file_difference("init.adv", preset(264257, 48021),
                                                        preset(264257, 48021, "0.6")))

    def test_a_real_change_is_a_difference(self):
        self.assertIn("30 vs 31", file_difference("d.maxpat", json.dumps(patch(ONE_MACHINE)).encode(),
                                                  json.dumps(patch(ONE_MACHINE, latency=31)).encode()))
        self.assertIn("differs", file_difference("d.maxpat", json.dumps(patch(ONE_MACHINE)).encode(),
                                                 json.dumps(patch(ONE_MACHINE, label="dirve")).encode()))
        self.assertIsNotNone(file_difference("d.amxd", unfrozen_device_bytes(patch(ONE_MACHINE), "audio"),
                                             unfrozen_device_bytes(patch(ONE_MACHINE), "instrument")))
        self.assertEqual(file_difference("d.bin", b"\xff\x00", b"\xff\x01"), "d.bin: the bytes differ")

    def test_folders(self):
        root = tempfile.mkdtemp()
        try:
            a, b = os.path.join(root, "a"), os.path.join(root, "b")
            for folder, numbers in ((a, ONE_MACHINE), (b, ONE_MACHINE)):
                os.makedirs(folder)
                with open(os.path.join(folder, "d.maxpat"), "w") as handle:
                    json.dump(patch(numbers), handle)
            self.assertEqual(build_differences(a, b), [])
            with open(os.path.join(b, "d.maxpat"), "w") as handle:
                json.dump(patch(ANOTHER_MACHINE), handle)
            self.assertEqual(len(build_differences(a, b)), 1)
            open(os.path.join(b, "extra.adv"), "wb").close()
            self.assertIn("extra.adv", build_differences(a, b)[0])
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()

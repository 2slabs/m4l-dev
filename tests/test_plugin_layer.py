"""Tests for the kit's plugin layer (m4l_dev/plugin/, plugin/cpp/): a device's host parameters read off its patch,
its presets with their Stored values, the .vstpreset writer against a preset Live saved, and the C++ GenProgram
rendering the renderer's bits."""
import array
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path[:0] = [HERE, KIT]
import fixture_device  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.genexpr import GenProgram, analyze  # noqa: E402
from m4l_dev.genexpr_export import FLOATING_POINT_FLAGS, export_c  # noqa: E402
from m4l_dev.plugin import header, vstpreset  # noqa: E402
from m4l_dev.plugin.parameters import Destination, host_parameters, presets_as_held  # noqa: E402
from m4l_dev.preset_book import PresetBook  # noqa: E402
from m4l_dev.render_comparison import assert_renders_similar  # noqa: E402

LIVE_SAVED = os.path.join(KIT, "references", "ableton", "example-2sl-filter-vst3-preset.vstpreset")


class FixtureParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        repository = fixture_device.build_fixture_device(cls.root)
        book = PresetBook.from_file(repository.source_path("presets.json"), "src/presets.json")
        cls.patch = patch = fixture_device.fixture_patch(book)
        boxes = {bx["box"].get("text", ""): bx["box"]["id"] for bx in patch.boxes}
        gen = next(b for b, code in patch.gen_code_by_box.items())
        cls.params, cls.stored = host_parameters(
            patch, repository.source_path("live-parameters.lock.json"),
            [Destination("gen", gen, "gen", list(analyze(patch.gen_code_as_built(gen), 1, 1)[1].params)),
             Destination("brain", boxes[f"js {fixture_device.FIXTURE_SCRIPT_NAME}.js"], "message")])
        cls.by_name = {p["name"]: p for p in cls.params}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root)

    def test_a_number_reaches_its_param_in_a_straight_line(self):
        level = self.by_name["Level"]
        self.assertEqual(level["kind"], "Float")
        (route,) = level["routes"]
        self.assertEqual((route["to"], route["kind"], route["message"]), ("gen", "gen", "level"))
        self.assertAlmostEqual(route["scale"], 0.01)
        self.assertEqual(route["offset"], 0)

    def test_a_menu_reaches_the_brain_by_its_items(self):
        (route,) = self.by_name["Shape"]["routes"]
        self.assertEqual((route["to"], route["kind"], route["message"], route["choices"]), ("brain", "message", "shape", [0, 1]))

    def test_buttons_page_and_stored_values(self):
        self.assertEqual(self.by_name["Stop"]["kind"], "Button")
        self.assertEqual(self.by_name["Kick"]["kind"], "Button")    # wired straight to the brain: the plugin's to handle
        self.assertNotIn("Page", self.by_name)
        stored_by_name = {s["name"]: s for s in self.stored}
        self.assertEqual(sorted(stored_by_name), ["Memory", "Stage Pitch 1", "Stage Pitch 2", "Stage switches 1",
                                                  "Stage switches 2"])
        memory = stored_by_name["Memory"]
        self.assertEqual([r["message"] for r in memory["routes"]], ["memory"])
        self.assertEqual([r["message"] for r in stored_by_name["Stage Pitch 2"]["routes"]], ["stage_pitch_2"])
        presets = presets_as_held(self.patch, self.params, self.stored, fixture_device.stored_memory_of_preset)
        self.assertEqual(presets[0][0], "init")
        stored_init = dict(zip([s["name"] for s in self.stored], presets[0][2]))
        self.assertEqual(stored_init["Memory"], 7 + presets[0][1][[p["name"] for p in self.params].index("Level")])
        # the stored table's from the preset book itself: Init's Pitch 0, 7; row 2's Pulse on, Wait keyed
        self.assertEqual([stored_init[n] for n in ("Stage Pitch 1", "Stage Pitch 2", "Stage switches 2")],
                         [24 * 1365, 31 * 1365, 7])

    def test_the_header_names_every_route(self):
        text = header.plugin_header("twosl::fixture", ["gen", "brain"], self.params, self.stored,
                                    presets_as_held(self.patch, self.params, self.stored,
                                                    fixture_device.stored_memory_of_preset), 0, [])
        self.assertIn('{ "level", "Level", Kind::Float', text)
        self.assertIn('genDestination, RouteKind::Gen, 0, "level"', text)
        self.assertIn('inline constexpr int stopParameter', text)


class VstPresetTests(unittest.TestCase):
    def test_a_state_tag_the_plugin_could_not_read_back_is_refused(self):
        with self.assertRaises(BuildError):
            vstpreset.state_xml("2sl stab", [("cutoff", 1.0)], 0)
        self.assertIn(b"<TwoSlStab ", vstpreset.state_xml("TwoSlStab", [("cutoff", 1.0)], 0))

    def test_the_writer_rebuilds_a_preset_live_saved(self):
        with open(LIVE_SAVED, "rb") as handle:
            saved = handle.read()
        class_id, chunks = vstpreset.read(saved)
        self.assertEqual(class_id, vstpreset.class_id("TwSl", "Tsfl"))
        info = vstpreset.meta_info("2sl filter", "2sl", "Fx|Filter")
        self.assertEqual(chunks[b"Info"], info)
        xml, private_data = vstpreset.split_state(chunks[b"Comp"])
        self.assertEqual(private_data, vstpreset.JUCE_PRIVATE_DATA)
        self.assertEqual(vstpreset.preset_file(class_id, xml, info), saved)


CODE = """
Param cutoff(500, min=20, max=20000);
History lp(0), ph(0.25);
lp = lp + (in1 - lp) * (1 - exp(-6.283185307 * cutoff / samplerate));
ph = fract(ph + cutoff / samplerate);
out1 = lp + noise() * 0.001;
out2 = sin(twopi * ph);
"""
HARNESS = r"""
#include "GenProgram.h"
#include "core.h"
#include <cstdio>
#include <vector>
int main() {
    twosl::plugin::ProgramSpec spec { core_render, core_noise_seed, CORE_INPUTS, CORE_OUTPUTS, CORE_PARAMS,
        core_param_names, core_param_defaults, core_param_lowest, core_param_highest, CORE_HISTORIES,
        core_history_names, core_history_initials, CORE_DELAY_MEMORY, CORE_DELAYS };
    twosl::plugin::GenProgram program (spec, 1);
    program.setParam (program.paramIndex ("cutoff"), 1234.5);
    program.setHistory (program.historyIndex ("ph"), 0.5);
    std::vector<double> in (1000), a (1000), b (1000);
    for (int i = 0; i < 1000; ++i) in[(size_t) i] = (i % 37) / 37.0 - 0.5;
    const double* ins[] = { in.data() }; double* outs[] = { a.data(), b.data() };
    program.render (600, 48000.0, ins, outs);
    const double* ins2[] = { in.data() + 600 }; double* outs2[] = { a.data() + 600, b.data() + 600 };
    program.render (400, 48000.0, ins2, outs2);
    fwrite (a.data(), sizeof (double), 1000, stdout); fwrite (b.data(), sizeof (double), 1000, stdout);
}
"""


@unittest.skipIf(shutil.which("c++") is None, "needs a C++ compiler")
class GenProgramTests(unittest.TestCase):
    def test_a_program_renders_the_renderers_sound_in_any_blocks(self):
        root = tempfile.mkdtemp()
        try:
            source, header_text = export_c(CODE, 1, 2, "core")
            for name, text in (("core.c", source), ("core.h", header_text), ("main.cpp", HARNESS)):
                with open(os.path.join(root, name), "w") as handle:
                    handle.write(text)
            subprocess.run(["cc", "-std=c99", "-O2", *FLOATING_POINT_FLAGS, "-w", "-c", "core.c", "-o", "core.o"],
                           cwd=root, check=True)
            subprocess.run(["c++", "-std=c++17", "-O2", "-I", os.path.join(KIT, "plugin", "cpp"), "-I", ".", "main.cpp",
                            "core.o", "-o", "harness"], cwd=root, check=True)
            out = array.array("d")
            out.frombytes(subprocess.run([os.path.join(root, "harness")], capture_output=True, check=True).stdout)
            program = GenProgram(CODE, 1, 2, samplerate=48000.0)
            program.set_param("cutoff", 1234.5)
            program.set_history("ph", 0.5)
            expected = program.run(1000, [[(i % 37) / 37.0 - 0.5 for i in range(1000)]])
            assert_renders_similar(expected, [out[:1000].tolist(), out[1000:].tolist()], 48000.0,
                                   "GenProgram.h in blocks of 600 and 400")
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()

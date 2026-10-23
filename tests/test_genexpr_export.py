"""Tests for twosl_dsp/genexpr_export.py: the exported C, built as a plugin would build it, renders GenProgram's sound
(within the kit's render comparator's tolerance, architecture/testing.md)."""

import array
import ctypes
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.genexpr import GenProgram, NoiseState  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.genexpr_export import FLOATING_POINT_FLAGS, export_c  # noqa: E402
from twosl_dsp.render_comparison import assert_renders_similar  # noqa: E402

# a little of everything the export touches: a function using samplerate, mstosamps, noise, a delay, a data (after
# the delay in the memory), histories, bounded loops (in a function and stepping a History, with break and continue)
CODE = """
smooth(x, ms) {
	return 1 - exp(-1000 / (ms * samplerate));
}
halvings(x) {
	s = x;
	for (k = 0; k < 6; k += 1) {
		if (k >= 4) {
			break;
		}
		s = s * 0.5 + 0.1;
	}
	return s;
}
Param cutoff(500, min=20, max=20000);
Param time(3, min=0, max=10);
History lp(0), ph(0.25);
Delay echo(4410);
Data held(16);
lp = lp + (in1 - lp) * smooth(1000 / cutoff, 1);
ph = fract(ph + cutoff / samplerate);
echo.write(lp + noise() * 0.01);
poke(held, lp, floor(ph * 16));
out1 = echo.read(mstosamps(time) + 0.5) + peek(held, floor(ph * 16 + 8) % 16);
out2 = sin(twopi * ph) + noise() * noise();
for (i = 0; i < 8; i += 1) {
	if (i == 3) {
		continue;
	}
	lp = lp * 0.999 + halvings(in2) * 0.0001;
}
out3 = in2 * mstosamps(1);
"""
INPUTS, OUTPUTS = 2, 3


def build(directory, source, header_source, extra_flags):
    with open(os.path.join(directory, "core.c"), "w") as handle:
        handle.write(source)
    with open(os.path.join(directory, "core.h"), "w") as handle:
        handle.write(header_source)
    library = os.path.join(directory, f"core{len(extra_flags)}.so")
    subprocess.run([os.environ.get("CC", "cc"), "-std=c99", "-fPIC", "-shared", *extra_flags, "-o", library,
                    os.path.join(directory, "core.c"), "-lm"], check=True, capture_output=True)
    return ctypes.CDLL(library)


@unittest.skipIf(shutil.which(os.environ.get("CC", "cc")) is None, "needs a C compiler")
class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp()
        cls.source, cls.header = export_c(CODE, INPUTS, OUTPUTS, "core")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory)

    def render(self, library, samplerate, inputs, params=None, seed=1):
        count = len(inputs[0])
        param_values = array.array("d", [500.0, 3.0])
        for index, value in (params or {}).items():
            param_values[index] = value
        histories = array.array("d", [0.0, 0.25])
        delay_memory = array.array("d", bytes(8 * (4410 + 16)))
        positions = (ctypes.c_long * 1)()
        noise = NoiseState()
        library.core_noise_seed(ctypes.byref(noise), ctypes.c_uint32(seed))
        input_arrays = [array.array("d", values) for values in inputs]
        output_arrays = [array.array("d", bytes(8 * count)) for _ in range(OUTPUTS)]
        address = lambda values: values.buffer_info()[0]  # noqa: E731
        library.core_render(ctypes.c_long(count), ctypes.c_double(samplerate), ctypes.c_void_p(address(param_values)),
                            ctypes.c_void_p(address(histories)), ctypes.c_void_p(address(delay_memory)),
                            positions, (ctypes.c_void_p * INPUTS)(*map(address, input_arrays)),
                            (ctypes.c_void_p * OUTPUTS)(*map(address, output_arrays)), ctypes.byref(noise))
        return [output.tolist() for output in output_arrays]

    def reference(self, samplerate, inputs, params=None):
        program = GenProgram(CODE, INPUTS, OUTPUTS, samplerate=samplerate)
        for name, value in (params or {}).items():
            program.set_param(name, value)
        return program.run(len(inputs[0]), inputs)

    def inputs(self, count=3000):
        generator = random.Random(7)
        return [[generator.uniform(-1, 1) for _ in range(count)] for _ in range(INPUTS)]

    def test_the_seed_is_pythons(self):
        library = build(self.directory, self.source, self.header, ("-O0", *FLOATING_POINT_FLAGS))
        for seed in (0, 1, 12345, 2 ** 32 - 1):
            noise = NoiseState()
            library.core_noise_seed(ctypes.byref(noise), ctypes.c_uint32(seed))
            _, state, _ = random.Random(seed).getstate()
            self.assertEqual(list(noise.words), list(state[:624]), seed)
            self.assertEqual(noise.index, state[624])

    def test_the_renderers_sound_at_any_sample_rate(self):
        library = build(self.directory, self.source, self.header, ("-O0", *FLOATING_POINT_FLAGS))
        inputs = self.inputs()
        for samplerate in (44100.0, 48000.0, 96000.0):
            assert_renders_similar(self.reference(samplerate, inputs), self.render(library, samplerate, inputs),
                                   samplerate, f"the export at {samplerate:g} Hz")

    def test_the_renderers_sound_optimised(self):
        library = build(self.directory, self.source, self.header, ("-O2", *FLOATING_POINT_FLAGS))
        inputs = self.inputs()
        assert_renders_similar(self.reference(48000.0, inputs, {"cutoff": 2000.0, "time": 7.5}),
                               self.render(library, 48000.0, inputs, {0: 2000.0, 1: 7.5}), 48000.0, "the export at -O2")

    def test_the_header_describes_the_program(self):
        for line in ("CORE_INPUTS = 2", "CORE_OUTPUTS = 3", "CORE_PARAMS = 2", "CORE_HISTORIES = 2",
                     "CORE_DELAYS = 1", "CORE_DELAY_MEMORY = 4426", '{"cutoff", "time"}', '{"lp", "ph"}'):
            self.assertIn(line, self.header)

    def test_code_without_its_param_defaults_is_not_exported(self):
        with self.assertRaisesRegex(BuildError, r"Params \['g'\] have no default in this code"):
            export_c("Param g(min=0, max=1);\nout1 = in1 * g;", 1, 1, "core")

    def test_a_prefix_must_be_a_c_identifier(self):
        with self.assertRaises(ValueError):
            export_c(CODE, INPUTS, OUTPUTS, "2sl-filter")


if __name__ == "__main__":
    unittest.main()

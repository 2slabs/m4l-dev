#!/usr/bin/env python3
"""Tests for tools/genexpr.py. Run: python3 tools/test_genexpr.py"""

import math
import os
import re
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genexpr  # noqa: E402
from genexpr import GenExprError, GenProgram, check  # noqa: E402

STAB_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "2sl-stab.py")


def extract_raw_string(script_text, variable_name):
    match = re.search(variable_name + r' = r"""(.*?)"""', script_text, re.S)
    if match is None:
        raise AssertionError(f"{variable_name} = r\"\"\"...\"\"\" not found in {STAB_SCRIPT_PATH}")
    return match.group(1)


def render_single_output(code, num_samples, inputs=None, num_inputs=1):
    program = GenProgram(code, num_inputs, 1)
    return program.run(num_samples, inputs)[0]


class RealCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(STAB_SCRIPT_PATH, encoding="utf-8") as handle:
            script_text = handle.read()
        cls.voice_code = extract_raw_string(script_text, "VOICE")
        cls.fx_code = extract_raw_string(script_text, "FX")

    def test_voice_and_fx_check(self):
        check(self.voice_code)
        check(self.fx_code)

    def test_voice_renders_finite_nonzero(self):
        program = GenProgram(self.voice_code, 3, 1)
        output = program.run(4410, [220.0, 0.8, 0.0])[0]
        self.assertEqual(len(output), 4410)
        self.assertTrue(all(math.isfinite(sample) for sample in output))
        self.assertTrue(any(sample != 0.0 for sample in output))

    def test_fx_renders_finite(self):
        program = GenProgram(self.fx_code, 2, 3)
        outputs = program.run(2000, [[0.5] * 2000, [0.0] * 2000])
        self.assertEqual(len(outputs), 3)
        self.assertTrue(all(math.isfinite(sample) for channel in outputs for sample in channel))


class RejectionTests(unittest.TestCase):
    def assert_rejected(self, code, expected_fragment, expected_line=None, **limits):
        with self.assertRaises(GenExprError) as caught:
            check(code, **limits)
        self.assertIn(expected_fragment, caught.exception.message)
        if expected_line is not None:
            self.assertEqual(caught.exception.line, expected_line)
        self.assertRegex(str(caught.exception), r"^line \d+:\d+: ")

    def test_missing_semicolon(self):
        self.assert_rejected("a = 1;\nb = 2\nout1 = a;", "missing ';'", expected_line=2)

    def test_compound_assignment(self):
        self.assert_rejected("a = 1;\na += 2;", "compound assignment", expected_line=2)

    def test_unknown_function(self):
        self.assert_rejected("a = frobnicate(1);", "unknown function 'frobnicate'")

    def test_wrong_argument_count(self):
        self.assert_rejected("a = sin(1, 2);", "takes 1 argument")

    def test_undeclared_read(self):
        self.assert_rejected("a = nothing + 1;", "'nothing'")

    def test_block_local_read_after_block(self):
        code = "c = 1;\nif (c > 0) {\n  x = 2;\n}\nout1 = x;"
        self.assert_rejected(code, "x is assigned only inside the block at line 2", expected_line=5)

    def test_assign_to_param(self):
        self.assert_rejected("Param p(0);\np = 1;", "Param")

    def test_assign_to_input_and_constant(self):
        self.assert_rejected("in1 = 1;", "input")
        self.assert_rejected("pi = 3;", "constant")

    def test_function_after_param(self):
        self.assert_rejected("Param p(0);\nf(a) { return a; }", "function definitions must come before")

    def test_declaration_after_statement(self):
        self.assert_rejected("a = 1;\nParam p(0);", "before the first statement")

    def test_param_inside_function(self):
        self.assert_rejected("f(a) { return a + p; }\nParam p(0);\nout1 = f(1);", "cannot be used inside function")

    def test_output_beyond_count(self):
        with self.assertRaises(GenExprError):
            GenProgram("out2 = 1;", 1, 1)
        with self.assertRaises(GenExprError):
            GenProgram("out1 = in2;", 1, 1)

    def test_output_read_and_braces_required(self):
        self.assert_rejected("out1 = 1;\na = out1;", "write only")
        self.assert_rejected("c = 1;\nif (c) out1 = 1;", "braces are required")

    def test_param_default_outside_range(self):
        self.assert_rejected("Param p(5, min=0, max=1);", "outside")

    def test_comments_and_error_positions(self):
        self.assert_rejected("/* a\nb */ a = 1 ;\n  b = @;", "unexpected character", expected_line=3)


class SemanticsTests(unittest.TestCase):
    def test_history_counter_updates_immediately_and_persists(self):
        program = GenProgram("History n(0);\nn = n + 1;\nout1 = n;", 1, 1)
        self.assertEqual(program.run(5)[0], [1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(program.run(2)[0], [6.0, 7.0])
        self.assertEqual(program.get_history("n"), 7.0)
        with self.assertRaises(KeyError):
            program.get_history("nope")

    def test_locals_do_not_persist_and_history_initial_value(self):
        program = GenProgram("History h(1.5);\nout1 = h;", 1, 1)
        self.assertEqual(program.run(1)[0], [1.5])

    def test_one_pole_step_response_closed_form(self):
        coefficient = 0.1
        code = f"History y(0);\ny = y + {coefficient} * (in1 - y);\nout1 = y;"
        output = render_single_output(code, 50, [1.0])
        for index, sample in enumerate(output):
            expected = 1.0 - (1.0 - coefficient) ** (index + 1)
            self.assertAlmostEqual(sample, expected, delta=1e-9)

    def test_param_clamping_and_unknown(self):
        program = GenProgram("Param g(0.5, min=0, max=1);\nout1 = g;", 1, 1)
        self.assertEqual(program.params["g"], {"default": 0.5, "min": 0.0, "max": 1.0})
        self.assertEqual(program.run(1)[0], [0.5])
        program.set_param("g", 7)
        self.assertEqual(program.run(1)[0], [1.0])
        program.set_param("g", -3)
        self.assertEqual(program.run(1)[0], [0.0])
        with self.assertRaises(KeyError) as caught:
            program.set_param("missing", 1)
        self.assertIn("missing", str(caught.exception))

    def test_param_order_of_min_max_and_optional(self):
        program = GenProgram("Param a(2, max=3, min=1);\nParam b(-1);\nout1 = a + b;", 1, 1)
        program.set_param("b", -100)
        program.set_param("a", 100)
        self.assertEqual(program.run(1)[0], [3.0 - 100.0])

    def test_division_and_modulo_by_zero(self):
        output = render_single_output("z = in1 - in1;\nout1 = 5 / z + 3 % z + 1 / 0;", 3, [2.0])
        self.assertEqual(output, [0.0, 0.0, 0.0])
        self.assertEqual(render_single_output("out1 = -7 % 3;", 1, [0.0])[0], -1.0)
        self.assertEqual(render_single_output("out1 = 7 / 2;", 1, [0.0])[0], 3.5)

    def test_ternary_and_logic_precedence(self):
        self.assertEqual(render_single_output("out1 = 1 || 0 && 0;", 1, [0.0])[0], 1.0)
        self.assertEqual(render_single_output("out1 = (1 || 0) && 0;", 1, [0.0])[0], 0.0)
        self.assertEqual(render_single_output("out1 = 0 ? 1 : 0 ? 2 : 3;", 1, [0.0])[0], 3.0)
        self.assertEqual(render_single_output("out1 = 1 ? 0 ? 5 : 6 : 7;", 1, [0.0])[0], 6.0)
        self.assertEqual(render_single_output("out1 = 1 + 2 < 4 == 1;", 1, [0.0])[0], 1.0)
        self.assertEqual(render_single_output("out1 = !0 + !5 + -2;", 1, [0.0])[0], -1.0)
        self.assertEqual(render_single_output("out1 = 2 * 3 + 4 * 5 - 6 / 3;", 1, [0.0])[0], 24.0)

    def test_noise_reproducible_and_in_range(self):
        code = "out1 = noise();"
        first = GenProgram(code, 1, 1, seed=7).run(200)[0]
        second = GenProgram(code, 1, 1, seed=7).run(200)[0]
        other = GenProgram(code, 1, 1, seed=8).run(200)[0]
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(all(-1.0 <= sample < 1.0 for sample in first))
        program = GenProgram(code, 1, 1, seed=7)
        program.set_seed(7)
        self.assertEqual(program.run(200)[0], first)

    def test_delay_integer_read(self):
        code = "Delay d(100);\nout1 = d.read(5);\nd.write(in1);"
        count = 30
        output = render_single_output(code, count, [[float(i + 1) for i in range(count)]])
        for index in range(count):
            self.assertEqual(output[index], float(index + 1 - 5) if index >= 5 else 0.0)
        code_after_write = "Delay d(100);\nd.write(in1);\nout1 = d.read(5, interp=\"none\") + d.read(0);"
        output = render_single_output(code_after_write, count, [[float(i + 1) for i in range(count)]])
        self.assertEqual(output[10], 6.0 + 11.0)

    def test_delay_fractional_and_cubic_on_a_ramp(self):
        count = 40
        ramp = [[float(i) for i in range(count)]]
        for mode in ("linear", "cubic"):
            code = f'Delay d(64);\nd.write(in1);\nout1 = d.read(2.5, interp="{mode}");'
            output = render_single_output(code, count, ramp)
            self.assertAlmostEqual(output[20], 17.5, delta=1e-9)

    def test_functions_scope_and_returns(self):
        code = """
        sq(x) { return x * x; }
        pick(v) { if (v > 1) { return 10; } else if (v > 0) { return 5; } }
        Param p(0);
        out1 = sq(3) + pick(2) + pick(0.5) + pick(-1);
        """
        self.assertEqual(render_single_output(code, 1, [0.0])[0], 9.0 + 10.0 + 5.0 + 0.0)

    def test_block_local_shadow_in_siblings_and_outer_update(self):
        code = """
        c = in1;
        t = 1;
        if (c > 0) { x = 2; t = x; } else { x = 3; t = x; }
        out1 = t;
        """
        self.assertEqual(render_single_output(code, 1, [1.0])[0], 2.0)
        self.assertEqual(render_single_output(code, 1, [-1.0])[0], 3.0)

    def test_builtins(self):
        expression = "wrap(1.25, 0, 1) + wrap(-0.25, 0, 1) + fract(2.75) + clamp(5, 0, 1) + mix(0, 10, 0.5) + sign(-3)"
        self.assertAlmostEqual(render_single_output(f"out1 = {expression};", 1, [0.0])[0], 0.25 + 0.75 + 0.75 + 1 + 5 - 1)
        self.assertEqual(render_single_output("out1 = log(0) + sqrt(-1);", 1, [0.0])[0], 0.0)
        self.assertAlmostEqual(render_single_output("out1 = dbtoa(-20) + mstosamps(10);", 1, [0.0])[0], 0.1 + 441.0)
        self.assertEqual(render_single_output("out1 = atodb(0);", 1, [0.0])[0], -999.0)

    def test_unwritten_output_is_zero(self):
        program = GenProgram("out1 = 1;", 1, 2)
        outputs = program.run(3)
        self.assertEqual(outputs, [[1.0] * 3, [0.0] * 3])


class SpeedTests(unittest.TestCase):
    def test_speed_smoke(self):
        lines = ["History s(0);", "Param amount(0.5, min=0, max=1);"]
        body = ["a0 = in1 * amount + s;"]
        for index in range(1, 298):
            body.append(f"a{index} = a{index - 1} * 0.999 + in1 * 0.001 + {index} * 0.00001;")
        body.append("s = a297 * 0.5;")
        body.append("out1 = a297;")
        code = "\n".join(lines + body)
        program = GenProgram(code, 1, 1)
        num_samples = 20000
        started = time.perf_counter()
        output = program.run(num_samples, [0.1])[0]
        elapsed = time.perf_counter() - started
        rate = num_samples / elapsed
        print(f"\n[speed] ~300 statements: {rate:,.0f} samples/second")
        self.assertTrue(all(math.isfinite(sample) for sample in output))
        self.assertGreater(rate, 2000)


if __name__ == "__main__":
    unittest.main(verbosity=1)

"""Tests for m4l_dev/genexpr.py, our GenExpr subset checker and renderer. A device's own gen~ code is tested in its
repository (2sl stab: tests/test_stab_dsp.py)."""

import math
import os
import random
import struct
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from m4l_dev.c_library_cache import CLibraryBuildError  # noqa: E402
from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.genexpr import GenExprError, GenProgram, analyze, check, code_with_param_defaults  # noqa: E402


def render_single_output(code, num_samples, inputs=None, num_inputs=1):
    program = GenProgram(code, num_inputs, 1)
    return program.run(num_samples, inputs)[0]


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

    def test_a_delay_read_at_more_places_than_its_taps(self):
        code = "Delay d(100);\na = d.read(3);\nb = d.read(5);\nd.write(in1);\nout1 = a + b;"
        self.assert_rejected(code, "declare Delay d(size, 2)", expected_line=3)
        check("Delay d(100, 2);\na = d.read(3);\nb = d.read(5, interp=\"spline\");\nd.write(in1);\nout1 = a + b;",
              num_inputs=1, num_outputs=1)
        self.assert_rejected("Delay d(100, 0);", "taps must be a positive integer")

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

    def test_a_param_may_leave_its_default_out_but_nothing_else(self):
        _, info = analyze("Param a(min=0, max=1);\nParam b;\nParam c();\nParam d(max=2);\nout1 = a + b + c + d;")
        self.assertEqual([(p.default, p.minimum, p.maximum) for p in info.params.values()],
                         [(None, 0.0, 1.0), (None, None, None), (None, None, None), (None, None, 2.0)])
        self.assert_rejected("Param p(, min=0);", "Param default")
        self.assert_rejected("Param p(min=0, 1);", "expected min=... or max=...")
        self.assert_rejected("Param p(min=0 max=1);", "to close the Param")

    def test_comments_and_error_positions(self):
        self.assert_rejected("/* a\nb */ a = 1 ;\n  b = @;", "unexpected character", expected_line=3)


class ParamDefaultWritingTests(unittest.TestCase):
    """code_with_param_defaults: the patch builder writes the defaults a device's Init values give its Params."""

    def test_each_form_gets_its_default(self):
        code = ("Param a(min=0, max=1);  // a\nParam b;\nParam c();\nParam d(3);\n"
                "Param f(max=1e4);\nout1 = a + b + c + d + f;")
        written = code_with_param_defaults(code, {"a": 0.22, "b": -6, "c": 700.0, "f": 0.1 + 0.2})
        self.assertEqual(written, "Param a(0.22, min=0, max=1);  // a\nParam b(-6);\nParam c(700);\nParam d(3);\n"
                                  "Param f(0.30000000000000004, max=1e4);\nout1 = a + b + c + d + f;")
        _, info = analyze(written)
        self.assertEqual(info.params["f"].default, 0.1 + 0.2)

    def test_a_default_written_twice_or_to_no_param_fails(self):
        with self.assertRaisesRegex(BuildError, r"Params \['d'\] hold a default in the code"):
            code_with_param_defaults("Param d(3);\nout1 = d;", {"d": 3})
        with self.assertRaisesRegex(BuildError, r"defaults for \['x'\], which the code does not declare"):
            code_with_param_defaults("Param d(3);\nout1 = d;", {"x": 3})
        with self.assertRaisesRegex(BuildError, "finite"):
            code_with_param_defaults("Param d;\nout1 = d;", {"d": math.inf})


class SemanticsTests(unittest.TestCase):
    def test_history_counter_updates_immediately_and_persists(self):
        program = GenProgram("History n(0);\nn = n + 1;\nout1 = n;", 1, 1)
        self.assertEqual(program.run(5)[0], [1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertEqual(program.run(2)[0], [6.0, 7.0])
        self.assertEqual(program.get_history("n"), 7.0)
        with self.assertRaises(KeyError):
            program.get_history("nope")

    def test_a_history_set_from_outside_is_where_the_program_goes_on(self):
        program = GenProgram("History n(0);\nn = n + 1;\nout1 = n;", 1, 1)
        program.set_history("n", 0.25)
        self.assertEqual(program.run(2)[0], [1.25, 2.25])
        with self.assertRaises(KeyError):
            program.set_history("nope", 0)
        with self.assertRaises(ValueError):
            program.set_history("n", float("nan"))

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

    def test_a_param_without_a_default_must_be_set_before_running(self):
        program = GenProgram("Param g(min=0, max=1);\nParam h(2);\nout1 = g + h;", 1, 1)
        self.assertEqual(program.params["g"], {"default": None, "min": 0.0, "max": 1.0})
        with self.assertRaisesRegex(ValueError, r"Params \['g'\] have no default in the code"):
            program.run(1)
        with self.assertRaisesRegex(ValueError, "never set"):
            program.get_param("g")
        program.set_param("g", 0.5)
        self.assertEqual(program.run(1)[0], [2.5])

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
        code_after_write = "Delay d(100, 2);\nd.write(in1);\nout1 = d.read(5, interp=\"none\") + d.read(0);"
        output = render_single_output(code_after_write, count, [[float(i + 1) for i in range(count)]])
        self.assertEqual(output[10], 6.0 + 11.0)

    def test_delay_fractional_and_cubic_on_a_ramp(self):
        count = 40
        ramp = [[float(i) for i in range(count)]]
        for mode in ("linear", "cubic", "spline"):
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


class PythonArithmeticTests(unittest.TestCase):
    """The renderer runs C (built by the system compiler) and gives what Python's float and math module give, bit for
    bit: the cases where C and Python differ unless the translation takes care."""

    def assert_same_bits(self, rendered, expected):
        self.assertEqual(struct.pack(">d", rendered).hex(), struct.pack(">d", expected).hex(), (rendered, expected))

    def test_libm_functions_are_pythons(self):
        arguments = [0.3, -2.7, 1e-300, 123.456, 700.0]
        for name, python_function in (("exp", math.exp), ("tanh", math.tanh), ("atan", math.atan), ("sin", math.sin),
                                      ("cos", math.cos), ("tan", math.tan), ("log", math.log), ("sqrt", math.sqrt)):
            for argument in arguments:
                if name in ("log", "sqrt") and argument <= 0:
                    continue
                self.assert_same_bits(render_single_output(f"out1 = {name}(in1);", 1, [[argument]])[0],
                                      python_function(argument))
        self.assert_same_bits(render_single_output("out1 = pow(in1, 1.7) + atan2(in1, 3) + in1 % 0.7;", 1, [[2.3]])[0],
                              math.pow(2.3, 1.7) + math.atan2(2.3, 3) + math.fmod(2.3, 0.7))
        self.assert_same_bits(render_single_output("out1 = dbtoa(in1) + atodb(in1);", 1, [[3.1]])[0],
                              10.0 ** (3.1 / 20.0) + 20.0 * math.log10(3.1))

    def test_rounding_goes_through_a_python_int(self):
        """float(math.floor(-0.5)) is 0.0, not C's -0.0; inf and nan pass through."""
        for name in ("floor", "ceil", "trunc"):
            expected = float(getattr(math, name)(-0.3))
            self.assert_same_bits(render_single_output(f"out1 = {name}(in1);", 1, [[-0.3]])[0], expected)
            self.assertEqual(render_single_output(f"out1 = {name}(in1);", 1, [[math.inf]])[0], math.inf)
            self.assertTrue(math.isnan(render_single_output(f"out1 = {name}(in1);", 1, [[math.nan]])[0]))

    def test_domain_and_overflow_errors_read_as_python_raised_them(self):
        self.assertTrue(math.isnan(render_single_output("out1 = pow(0, -1);", 1, [0.0])[0]))      # ValueError
        self.assertEqual(render_single_output("out1 = pow(-10, 309);", 1, [0.0])[0], math.inf)     # OverflowError
        self.assertTrue(math.isnan(render_single_output("out1 = sin(in1);", 1, [[math.inf]])[0]))
        self.assertTrue(math.isnan(render_single_output("out1 = in1 % 2;", 1, [[math.inf]])[0]))
        self.assertEqual(render_single_output("out1 = exp(1000);", 1, [0.0])[0], math.inf)
        self.assert_same_bits(render_single_output("out1 = in1 % -3;", 1, [[-7.5]])[0], math.fmod(-7.5, -3.0))
        self.assert_same_bits(render_single_output("out1 = wrap(in1, 0, 0.7);", 1, [[-2.5]])[0], 0.0 + (-2.5 % 0.7))

    def test_min_and_max_keep_the_first_on_a_tie(self):
        """Python's min(0.0, -0.0) is 0.0 (the second replaces the first only when strictly less)."""
        self.assert_same_bits(render_single_output("out1 = min(0, -in1);", 1, [[0.0]])[0], min(0.0, -0.0))
        self.assert_same_bits(render_single_output("out1 = max(-in1, 0);", 1, [[0.0]])[0], max(-0.0, 0.0))

    def test_noise_is_python_randoms_sequence_drawn_left_to_right(self):
        draws = random.Random(3)
        expected = []
        for _ in range(50):
            first, second = draws.random() * 2 - 1, draws.random() * 2 - 1
            expected.append(first - second * 3)
        self.assertEqual(GenProgram("out1 = noise() - noise() * 3;", 0, 1, seed=3).run(50)[0], expected)

    def test_division_draws_its_divisor_first_and_skips_its_dividend_on_zero(self):
        draws = random.Random(5)
        divisor_noise, dividend_noise = draws.random() * 2 - 1, draws.random() * 2 - 1
        program = GenProgram("out1 = noise() / (noise() + in1);", 1, 1, seed=5)
        self.assertEqual(program.run(1, [[2.0]])[0][0], dividend_noise / (divisor_noise + 2.0))
        draws = random.Random(5)
        first_draw = draws.random() * 2 - 1
        program = GenProgram("out1 = noise() / in1;", 1, 1, seed=5)
        self.assertEqual(program.run(2, [[0.0, 1.0]])[0], [0.0, first_draw])   # no draw while the divisor is 0

    def test_no_c_compiler_fails_loudly(self):
        with mock.patch.dict(os.environ, {"CC": "no-such-c-compiler"}):
            with self.assertRaises(CLibraryBuildError) as caught:
                GenProgram("out1 = in1 * 0.5;", 1, 1)
        self.assertIn("no-such-c-compiler", str(caught.exception))
        self.assertIn("C compiler", str(caught.exception))
        check("out1 = in1 * 0.5;", num_inputs=1, num_outputs=1)   # checking needs no compiler


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
        self.assertGreater(rate, 250_000, "the renderer runs compiled C: ~1M samples/s here; Python's was ~120k")


if __name__ == "__main__":
    unittest.main(verbosity=1)

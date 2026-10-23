"""Tests for twosl_dsp/genexpr.py, our GenExpr subset checker and renderer. A device's own gen~ code is tested in its
repository (2sl stab: tests/test_stab_dsp.py)."""

import math
import os
import random
import struct
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.c_library_cache import CLibraryBuildError  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.cpu_timing import THREAD, CpuTiming  # noqa: E402
from twosl_dsp.render_comparison import assert_renders_similar, renders_are_similar  # noqa: E402
from twosl_dsp.genexpr import GenExprError, GenProgram, analyze, check, code_with_param_defaults  # noqa: E402


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

    def test_an_unsupported_operator_is_named_even_as_the_last_character(self):
        for operator in ("&", "|", "^", "~"):
            self.assert_rejected(f"out1 = in1 {operator}", f"operator '{operator}' is not supported", expected_line=1)
            self.assert_rejected(f"out1 = in1 {operator} 2;", f"operator '{operator}' is not supported", expected_line=1)


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
        assert_renders_similar(first, second, 44100.0, "seed 7 again")
        self.assertFalse(renders_are_similar(first, other, 44100.0).similar, "seeds 7 and 8 draw alike")
        self.assertTrue(all(-1.0 <= sample < 1.0 for sample in first))
        program = GenProgram(code, 1, 1, seed=7)
        program.set_seed(7)
        assert_renders_similar(first, program.run(200)[0], 44100.0, "set_seed(7)")

    def test_delay_integer_read(self):
        code = "Delay d(100);\nout1 = d.read(5);\nd.write(in1);"
        count = 30
        output = render_single_output(code, count, [[float(i + 1) for i in range(count)]])
        for index in range(count):
            self.assertEqual(output[index], float(index + 1 - 5) if index >= 5 else 0.0)
        code_after_write = "Delay d(100, 2);\nd.write(in1);\nout1 = d.read(5, interp=\"none\") + d.read(0);"
        output = render_single_output(code_after_write, count, [[float(i + 1) for i in range(count)]])
        self.assertEqual(output[10], 6.0 + 11.0)

    def test_data_peek_and_poke(self):
        # a ring of 4 written at a History's index: each sample reads what was written 4 samples before
        code = """History w(0);
Data ring(4);
out1 = peek(ring, w);
poke(ring, in1, w);
w = (w + 1) % 4;"""
        output = render_single_output(code, 12, [[float(i + 1) for i in range(12)]])
        self.assertEqual(output, [0.0] * 4 + [float(i + 1) for i in range(8)])
        # floored index; out of range or NaN reads 0 and writes nothing (gen~'s boundmode "ignore")
        code = """Data d(3);
poke(d, 7, 1.9);
poke(d, 9, 3);
poke(d, 9, -1);
poke(d, 9, sqrt(-1) * 0 + in1);
out1 = peek(d, 1.2) * 100 + peek(d, 0) + peek(d, 2) + peek(d, 3) + peek(d, -0.5) + peek(d, in1);"""
        self.assertEqual(render_single_output(code, 1, [[math.nan]]), [700.0])

    def test_data_is_declared_and_used_as_gen_has_it(self):
        rejected = RejectionTests()
        rejected.assert_rejected("Data d(4, 2);\nout1 = 0;", "one channel only")
        rejected.assert_rejected("Data d(0);\nout1 = 0;", "size must be a positive integer")
        rejected.assert_rejected("History d(0);\nout1 = peek(d, 0);", "is not a Data")
        rejected.assert_rejected("Data d(4);\nout1 = d;", "use peek(d, index)")
        rejected.assert_rejected("Data d(4);\nd = 1;", "use poke(d, value, index)")
        rejected.assert_rejected("Data d(4);\nout1 = poke(d, 1, 0);", "is a statement")
        rejected.assert_rejected("f(x) { poke(d, x, 0); return 0; }\nData d(4);\nout1 = f(1);", "inside a function")
        rejected.assert_rejected("Data d(4);\npoke(d, 1);", "poke takes 3 arguments")

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
        assert_renders_similar(expected, GenProgram("out1 = noise() - noise() * 3;", 0, 1, seed=3).run(50)[0], 44100.0,
                               "noise() - noise() * 3")

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


class BoundedLoopTests(unittest.TestCase):
    """gen~'s for loop (Cycling '74's GenExpr guide; references/dsp.md, "gen~ (what Max accepts)"), as far as the kit
    renders it: bounded by its header's literals, break and continue inside it; anything it cannot bound refused."""

    def assert_rejected(self, code, expected_fragment, expected_line=None):
        with self.assertRaises(GenExprError) as caught:
            check(code, num_inputs=1, num_outputs=1)
        self.assertIn(expected_fragment, caught.exception.message)
        if expected_line is not None:
            self.assertEqual(caught.exception.line, expected_line)

    def test_the_guides_own_loop_renders_its_sum(self):
        # the guide's example: val = 0; for (i = 0; i < 10; i += 1) { val += i; } (+= in the body is ours to spell out)
        self.assertEqual(render_single_output("val = 0;\nfor (i = 0; i < 10; i += 1) {\n\tval = val + i;\n}\n"
                                              "out1 = val;", 2), [45.0, 45.0])

    def test_float_steps_count_as_the_c_counts_them(self):
        # the guide: "for (i = 0; i <= 1; i += 0.05)" "will likely not reach 1.0"; the kit counts it the C's way
        code = "n = 0;\nfor (i = 0; i <= 1; i += 0.05) {\n\tn = n + 1;\n}\nout1 = n;"
        program, _ = analyze(code, 1, 1)
        self.assertEqual(render_single_output(code, 1), [float(program.statements[1].bounded_loop_iterations)])
        self.assertEqual(program.statements[1].bounded_loop_iterations, 20)

    def test_break_leaves_and_continue_skips(self):
        code = ("total = 0;\nfor (i = 0; i < 64; i += 1) {\n\tif (i >= in1) {\n\t\tbreak;\n\t}\n"
                "\tif (i == 2) {\n\t\tcontinue;\n\t}\n\ttotal = total + i;\n}\nout1 = total;")
        self.assertEqual(render_single_output(code, 4, [[0, 3, 5, 100]]), [0.0, 1.0, 8.0, 2014.0])

    def test_a_history_stepped_in_a_loop_keeps_every_step(self):
        code = "History x(1);\nfor (i = 0; i < 3; i += 1) {\n\tx = x * 2;\n}\nout1 = x;"
        self.assertEqual(render_single_output(code, 3), [8.0, 64.0, 512.0])

    def test_loops_nest_and_run_in_functions(self):
        code = ("triangle(n) {\n\ts = 0;\n\tfor (k = 1; k <= 8; k += 1) {\n\t\tif (k > n) {\n\t\t\treturn s;\n"
                "\t\t}\n\t\ts = s + k;\n\t}\n\treturn s;\n}\nproduct = 0;\nfor (i = 0; i < 3; i += 1) {\n"
                "\tfor (j = 0; j < 4; j += 1) {\n\t\tproduct = product + 1;\n\t}\n}\n"
                "out1 = product * 100 + triangle(in1);")
        self.assertEqual(render_single_output(code, 3, [[2, 4, 20]]), [1203.0, 1210.0, 1236.0])

    def test_noise_drawn_in_a_loop_is_pythons_sequence(self):
        code = "s = 0;\nfor (i = 0; i < 5; i += 1) {\n\ts = s + noise();\n}\nout1 = s;"
        generator = random.Random(1)
        expected = [sum(generator.random() * 2 - 1 for _ in range(5)) for _ in range(3)]
        for value, wanted in zip(render_single_output(code, 3), expected):
            self.assertAlmostEqual(value, wanted, places=12)

    def test_what_it_cannot_bound_is_refused(self):
        self.assert_rejected("i = 0;\nwhile (i < 10) {\n\ti = i + 1;\n}\nout1 = i;", "'while' loops are refused", 2)
        self.assert_rejected("for (i = 0; i < in1; i += 1) {\n}\nout1 = 0;", "expected a number literal", 1)
        self.assert_rejected("for (i = 0; i > 10; i += 1) {\n}\nout1 = 0;", "i < LIMIT or i <= LIMIT", 1)
        self.assert_rejected("for (i = 0; i < 10; i = i + 1) {\n}\nout1 = 0;", "the step must be i += STEP", 1)
        self.assert_rejected("for (i = 0; i < 10; i += 0) {\n}\nout1 = 0;", "more than 0", 1)
        self.assert_rejected("for (i = 0; i < 10; i += -1) {\n}\nout1 = 0;", "more than 0", 1)
        self.assert_rejected("for (i = 0; i < 10; i += 1) {\n\ti = 0;\n}\nout1 = 0;", "cannot assign to the loop counter", 2)
        self.assert_rejected("for (i = 0; i < 1e9; i += 1) {\n}\nout1 = 0;", "more than 65536", 1)
        self.assert_rejected("for (i = 1e9; i < 2e9; i += 1) {\n}\nout1 = 0;", "more than 65536", 1)
        self.assert_rejected("for (i = 0; i < 10 + 1; i += 1) {\n}\nout1 = 0;", "one number literal", 1)
        self.assert_rejected("for (i = 0; j < 10; i += 1) {\n}\nout1 = 0;", "must test the counter 'i'", 1)

    def test_its_names_and_statements_are_checked(self):
        self.assert_rejected("break;\nout1 = 0;", "'break' is only allowed inside a for loop", 1)
        self.assert_rejected("f(a) {\n\tcontinue;\n\treturn a;\n}\nout1 = f(1);", "'continue' is only allowed", 2)
        self.assert_rejected("History h(0);\nfor (h = 0; h < 2; h += 1) {\n}\nout1 = h;", "already a History", 2)
        self.assert_rejected("i = 3;\nfor (i = 0; i < 2; i += 1) {\n}\nout1 = i;", "already a local", 2)
        self.assert_rejected("for (i = 0; i < 2; i += 1) {\n\ta = i;\n}\nout1 = i;", "assigned only inside the block", 4)
        self.assert_rejected("for (i = 0; i < 2; i += 1) {\n\ta = i;\n}\nout1 = a;", "assigned only inside the block", 4)
        self.assert_rejected("for (i = 0; i < 2; i += 1) {\n\tb = a;\n\ta = i;\n}\nout1 = 0;", "read before it is assigned", 2)
        self.assert_rejected("x = 0;\nx += 1;\nout1 = x;", "compound assignment '+=' is not supported", 2)


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
        program.run(1, [0.1])                       # the C built and loaded first: the one run below times rendering
        num_samples = 20000
        # one run on this thread's CPU clock (the render is a ctypes call on it), the machine's load read first and
        # reported with it (architecture/testing.md, "Timing tests")
        with CpuTiming("~300 statements, 20000 samples", THREAD) as timing:
            output = program.run(num_samples, [0.1])[0]
        rate = num_samples / max(timing.cpu_seconds, 1e-9)
        print(f"\n[speed] {rate:,.0f} samples per CPU second ({timing.report()})")
        self.assertTrue(all(math.isfinite(sample) for sample in output))
        if not timing.judged:
            self.skipTest(timing.report())
        self.assertGreater(rate, 250_000, f"the renderer runs compiled C: ~1M samples/s here; Python's was ~120k "
                                          f"({timing.report()})")


class MaxNumberLexerTests(unittest.TestCase):
    def test_numbers_max_refused_are_refused(self):
        # references/dsp.md, "gen~ numbers": no '+' in an exponent; Max stopped at -1e18 (2026-10-21)
        for code in ("History h(-1e18);\nout1 = h;\n", "out1 = 1e+9;\n", "out1 = 2E12;\n"):
            with self.assertRaises(GenExprError, msg=code):
                check(code, num_inputs=0, num_outputs=1)

    def test_numbers_max_compiles_are_kept(self):
        for code in ("out1 = 1e9;\n", "out1 = -1.4528355093231122e-05;\n", "out1 = 1e-06;\n", "out1 = 0.5;\n"):
            check(code, num_inputs=0, num_outputs=1)



if __name__ == "__main__":
    unittest.main(verbosity=1)

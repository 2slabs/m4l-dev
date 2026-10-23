"""Templates and the ES5 check (twosl_dsp/generated_scripts.py, twosl_dsp/es5.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import es5  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.generated_scripts import check_es5, fill_template, kit_template_text  # noqa: E402


class FillTemplateTests(unittest.TestCase):
    def test_every_marker_is_filled_once_over(self):
        filled = fill_template("var A = /*A*/; var B = /*B*/; // /* not a marker */", {"A": "1", "B": "'/*A*/'"}, "t")
        self.assertEqual(filled, "var A = 1; var B = '/*A*/'; // /* not a marker */",
                         "text filled in is not searched for markers again")

    def test_a_marker_the_template_lacks_fails(self):
        with self.assertRaisesRegex(BuildError, r"t has no marker for /\*C\*/"):
            fill_template("/*A*/", {"A": "1", "C": "3"}, "t")

    def test_a_marker_left_unfilled_fails(self):
        with self.assertRaisesRegex(BuildError, r"markers nothing fills: /\*B\*/"):
            fill_template("/*A*/ /*B*/", {"A": "1"}, "t")

    def test_the_kit_templates_exist(self):
        for name in ("ui-script.template.js", "views.template.js", "transport-clock.template.js", "cozette-glyphs.js"):
            self.assertTrue(kit_template_text(name))
        with self.assertRaisesRegex(BuildError, "no template"):
            kit_template_text("nope.js")


class Es5Tests(unittest.TestCase):
    def test_es5_compiles_and_newer_syntax_does_not(self):
        self.assertIsNone(es5.syntax_problem("var a = [1, 2].map(function (x) { return x * 2; });"))
        self.assertIn("SyntaxError", es5.syntax_problem("const a = (x) => x;"))
        with self.assertRaisesRegex(BuildError, "b.js: SyntaxError"):
            check_es5({"a.js": "var a;", "b.js": "let b = `template`;"})

    def test_evaluate_returns_the_last_value_and_raises_on_a_throw(self):
        self.assertEqual(es5.evaluate("var a = 2; JSON.stringify({b: a * 21})"), '{"b":42}')
        with self.assertRaisesRegex(BuildError, "boom"):
            es5.evaluate("throw new Error('boom');")

    def test_many_heaps_in_a_row(self):
        # the heap pointer is 64-bit: a cut one (no restype) crashed on the second or third heap on macOS
        for _ in range(50):
            self.assertIsNone(es5.syntax_problem("var x = 1;"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

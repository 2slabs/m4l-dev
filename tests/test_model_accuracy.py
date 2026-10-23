"""The kit's model-accuracy check (twosl_dsp/model_accuracy.py, architecture/testing.md): within the tolerance passes and
says its largest difference; over it, another length, a NaN, or a tolerance without its reason fails loudly."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.model_accuracy import assert_matches_model  # noqa: E402

REASON = "a stand-in reason"


class AssertMatchesModelTests(unittest.TestCase):
    def test_within_the_tolerance_passes_and_says_its_largest_difference(self):
        largest = assert_matches_model([1.0, 2.0 + 1e-13, 3.0], [1.0, 2.0, 3.0], 1e-12, "stand-in", REASON)
        self.assertAlmostEqual(largest, 1e-13, delta=1e-15)

    def test_over_the_tolerance_fails_saying_where_and_why(self):
        with self.assertRaises(AssertionError) as caught:
            assert_matches_model([0.0, 0.5, 1e-6], [0.0, 0.5, 0.0], 1e-9, "stand-in", REASON)
        self.assertIn("DOES NOT MATCH ITS MODEL", str(caught.exception))
        self.assertIn("at sample 2", str(caught.exception))
        self.assertIn(REASON, str(caught.exception))

    def test_another_length_or_a_nan_fails(self):
        for actual, expected in (([0.0, 0.0], [0.0]), ([math.nan], [0.0]), ([0.0], [math.inf]), ([], [])):
            with self.subTest(actual=actual, expected=expected), self.assertRaises(AssertionError):
                assert_matches_model(actual, expected, 1e-9, "stand-in", REASON)

    def test_a_tolerance_needs_its_reason_and_a_value(self):
        for tolerance, reason in ((1e-9, " "), (0.0, REASON), (math.nan, REASON)):
            with self.subTest(tolerance=tolerance, reason=reason), self.assertRaises(ValueError):
                assert_matches_model([0.0], [0.0], tolerance, "stand-in", reason)


if __name__ == "__main__":
    unittest.main()

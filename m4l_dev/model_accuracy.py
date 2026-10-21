"""A sample sequence held to its model: the one way a test says "the DSP computes this math" (architecture/testing.md).

The other kind of sequence comparison. render_comparison asks "are these two renders the same sound?" and answers in
decibels against the program. This asks "is every sample of the block's output its equation's (an identity such as
low-pass + high-pass = input, a twin, a reference model in Python) to within a numerical accuracy?" and answers per
sample: the largest |actual - expected| at most `tolerance`, absolute, in the signal's own units.

Every call says why its tolerance is what it is (`tolerance_reason`): the arithmetic's error it allows (a double's last
bits over so many steps, a twin's measured curvature), so a bound never drifts into a guess. A bound belongs here when
it is far over the last bits (another machine's 1e-16 passes it) and far under what render_comparison would allow, so
it claims more than "the same sound"; a looser bound is a sound claim and belongs to render_comparison.

A different length, or a NaN or an infinity on either side, fails loudly.
"""
import math
from typing import Sequence


def assert_matches_model(actual: Sequence[float], expected: Sequence[float], tolerance: float, what: str,
                         tolerance_reason: str) -> float:
    """Fails (AssertionError, so unittest reports a failure) unless every |actual[n] - expected[n]| <= tolerance.
    Returns the largest difference, so a test can print or keep it."""
    if not (tolerance > 0 and math.isfinite(tolerance)):
        raise ValueError(f"{what}: a tolerance must be a finite positive number, not {tolerance!r}")
    if not tolerance_reason.strip():
        raise ValueError(f"{what}: a tolerance needs its reason (why {tolerance:g})")
    actual, expected = list(actual), list(expected)
    if len(actual) != len(expected):
        raise AssertionError(f"{what}: DOES NOT MATCH ITS MODEL (✖_✖): {len(actual)} samples, the model has "
                             f"{len(expected)}")
    if not actual:
        raise AssertionError(f"{what}: DOES NOT MATCH ITS MODEL (✖_✖): empty sequences, nothing to compare")
    for name, sequence in (("output", actual), ("model", expected)):
        bad = next((n for n, x in enumerate(sequence) if not math.isfinite(x)), None)
        if bad is not None:
            raise AssertionError(f"{what}: DOES NOT MATCH ITS MODEL (✖_✖): the {name} holds {sequence[bad]} at "
                                 f"sample {bad}")
    largest_difference, largest_at = max((abs(a - e), n) for n, (a, e) in enumerate(zip(actual, expected)))
    if largest_difference > tolerance:
        raise AssertionError(f"{what}: DOES NOT MATCH ITS MODEL (╯°□°)╯: largest difference {largest_difference:.3g} "
                             f"at sample {largest_at} (output {actual[largest_at]!r}, model {expected[largest_at]!r}), "
                             f"tolerance {tolerance:g} ({tolerance_reason})")
    return largest_difference

"""Two renders of a sound compared as sound: the one way a test says "these are the same sound" (architecture/testing.md).

The build is the same on every machine (generated_numbers.py: a build's bytes are compared exactly); the tests are
not the build. A render carries the machine's maths library's last bits (glibc vs macOS, x86 vs ARM), and a threshold
event can land one sample later. Those differences are inaudible and must pass; a real change (a level change, a
parameter nudged, a click, a dropout) must fail. So two renders are compared by their difference, the residual
(candidate - reference), measured against the reference's own level:

- **residual_db**: 10 log10(sum(residual^2) / sum(reference^2)) over the whole render (every channel together);
- **worst_window_residual_db**: the same residual energy in each WINDOW_SECONDS window (the windows tile the render;
  the last is shorter), over the reference's mean energy per sample across the whole render: an error's loudness
  next to the program's. A click or a dropout is short, so it barely moves the whole render's figure but fills its
  window; a quiet passage of the reference doesn't inflate its window (the program's level is the whole render's);
- **level_difference_db**: 10 log10(sum(candidate^2) / sum(reference^2)), reported. The residual limit is the
  stricter test of a level: a gain of g dB alone gives a residual of 20 log10(10^(g/20) - 1) dB, -38.7 dB at
  0.1 dB and -70 dB at 0.0027 dB.

The limits (architecture/testing.md says why, with the cases tests/test_render_comparison.py holds on both sides):
the whole render's residual at most RESIDUAL_LIMIT_DB, every window's at most WINDOW_RESIDUAL_LIMIT_DB. A reference
quieter than SILENCE_FLOOR_DBFS (mean square, re a full-scale 1.0) is measured against that floor instead, so a
silent reference asks for a candidate as quiet as the floor's tolerance, not a division by zero.

A candidate of another length or channel count, or holding a NaN or an infinity, is never similar: the verdict says
which, loudly.
"""
import math
from dataclasses import dataclass
from typing import Optional, Sequence, Union

RESIDUAL_LIMIT_DB = -70.0
WINDOW_RESIDUAL_LIMIT_DB = -60.0
WINDOW_SECONDS = 0.010
SILENCE_FLOOR_DBFS = -120.0

Render = Union[Sequence[float], Sequence[Sequence[float]]]


@dataclass(frozen=True)
class RenderComparison:
    """The verdict and the numbers it was made from. `similar` is the verdict; `report()` says it with the numbers."""
    similar: bool
    residual_db: float
    worst_window_residual_db: float
    worst_window_start_seconds: float
    level_difference_db: float
    largest_sample_difference: float
    largest_sample_difference_at: int
    reference_level_dbfs: float
    problem: Optional[str] = None       # set when the renders couldn't be measured (length, channels, NaN)

    def report(self) -> str:
        if self.problem is not None:
            return f"NOT SIMILAR (✖_✖): {self.problem}"
        verdict = "within tolerance" if self.similar else "NOT SIMILAR (╯°□°)╯"
        return (f"{verdict}: residual {_db_text(self.residual_db)} dB (limit {RESIDUAL_LIMIT_DB:g}), worst "
                f"{WINDOW_SECONDS * 1000:g} ms window {_db_text(self.worst_window_residual_db)} dB at "
                f"{self.worst_window_start_seconds:.4f} s (limit {WINDOW_RESIDUAL_LIMIT_DB:g}), level difference "
                f"{_db_text(self.level_difference_db, signed=True)} dB, largest sample difference "
                f"{self.largest_sample_difference:.3g} at sample {self.largest_sample_difference_at}, reference "
                f"{_db_text(self.reference_level_dbfs)} dBFS")


def _db_text(value, signed=False):
    if value == -math.inf:
        return "-inf"
    return f"{value:+.1f}" if signed else f"{value:.1f}"


def _channels_of(render):
    """A render as a list of channels: a flat sequence of numbers is one channel."""
    render = list(render)
    if render and not isinstance(render[0], (int, float)):
        return [list(channel) for channel in render]
    return [render]


def _decibels(numerator, denominator):
    if numerator == 0:
        return -math.inf
    return 10 * math.log10(numerator / denominator)


def renders_are_similar(reference: Render, candidate: Render, sample_rate: float) -> RenderComparison:
    """Compares candidate with reference (one channel, or a sequence of channels) as sound at sample_rate."""
    reference_channels, candidate_channels = _channels_of(reference), _channels_of(candidate)
    nothing = dict(residual_db=math.inf, worst_window_residual_db=math.inf, worst_window_start_seconds=0.0,
                   level_difference_db=math.inf, largest_sample_difference=math.inf,
                   largest_sample_difference_at=0, reference_level_dbfs=math.nan)
    if len(reference_channels) != len(candidate_channels):
        return RenderComparison(False, problem=f"{len(candidate_channels)} channels, the reference has "
                                               f"{len(reference_channels)}", **nothing)
    for index, (reference_channel, candidate_channel) in enumerate(zip(reference_channels, candidate_channels)):
        if len(reference_channel) != len(candidate_channel):
            return RenderComparison(False, problem=f"channel {index}: {len(candidate_channel)} samples, the reference "
                                                   f"has {len(reference_channel)}", **nothing)
        for name, channel in (("reference", reference_channel), ("candidate", candidate_channel)):
            bad = next((n for n, x in enumerate(channel) if not math.isfinite(x)), None)
            if bad is not None:
                return RenderComparison(False, problem=f"the {name}'s channel {index} holds {channel[bad]} at "
                                                       f"sample {bad}", **nothing)
    length = len(reference_channels[0]) if reference_channels else 0
    if length == 0:
        return RenderComparison(False, problem="empty renders: nothing to compare", **nothing)

    window = max(1, min(length, round(WINDOW_SECONDS * sample_rate)))
    residual_energy_per_sample = [0.0] * length
    reference_energy = candidate_energy = 0.0
    largest_difference, largest_at = 0.0, 0
    for reference_channel, candidate_channel in zip(reference_channels, candidate_channels):
        for n, (r, c) in enumerate(zip(reference_channel, candidate_channel)):
            difference = c - r
            residual_energy_per_sample[n] += difference * difference
            reference_energy += r * r
            candidate_energy += c * c
            if abs(difference) > largest_difference:
                largest_difference, largest_at = abs(difference), n
    sample_count = length * len(reference_channels)
    floor_mean_square = 10 ** (SILENCE_FLOOR_DBFS / 10)
    reference_mean_square = max(reference_energy / sample_count, floor_mean_square)
    residual_energy = sum(residual_energy_per_sample)

    worst_window_db, worst_window_start = -math.inf, 0
    for start in range(0, length, window):
        piece = residual_energy_per_sample[start:start + window]
        window_db = _decibels(sum(piece) / (len(piece) * len(reference_channels)), reference_mean_square)
        if window_db > worst_window_db:
            worst_window_db, worst_window_start = window_db, start

    residual_db = _decibels(residual_energy / sample_count, reference_mean_square)
    if reference_energy == 0:
        level_difference_db = 0.0 if candidate_energy == 0 else math.inf
    else:
        level_difference_db = _decibels(candidate_energy, reference_energy)
    similar = residual_db <= RESIDUAL_LIMIT_DB and worst_window_db <= WINDOW_RESIDUAL_LIMIT_DB
    return RenderComparison(similar, residual_db, worst_window_db, worst_window_start / sample_rate,
                            level_difference_db, largest_difference, largest_at,
                            _decibels(reference_energy / sample_count, 1.0) if reference_energy else -math.inf)


def assert_renders_similar(reference: Render, candidate: Render, sample_rate: float, what: str = "") -> RenderComparison:
    """renders_are_similar, failing (AssertionError, so unittest reports a failure) with its report when not similar.
    Returns the comparison, so a test can print or keep the numbers."""
    comparison = renders_are_similar(reference, candidate, sample_rate)
    if not comparison.similar:
        raise AssertionError(f"{what + ': ' if what else ''}{comparison.report()}")
    return comparison

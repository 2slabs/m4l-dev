"""The patch matcher's validation before any real target exists (architecture/patch-matcher.md): parameter recovery.
Opt-in, slow (about a minute a target on 6 cores; each search's CPU time reported with the machine's load):

    TWOSL_DSP_SLOW_TESTS=1 python3 -m unittest tests.test_patch_matcher_recovery
    (TWOSL_DSP_RECOVERY_TARGETS=N: how many targets, default 12)

Each target is the fixture drum voice at random known settings (a seeded draw over the whole unit cube), rendered
with a different noise seed than the search renders with, as a recording's noise never repeats the voice's. The
matcher, at its default settings, must find a sound as close as the truth's own: a best score at most
RECOVERY_MARGIN over the score of the true settings rendered with the search's noise. A parameter counts as recovered
within PARAMETER_TOLERANCE of the truth in unit-cube terms; that rate is reported, not required: a parameter the hit
does not let one hear (a noise filter at noise level 0, a 2 ms sweep) has no right answer.
"""
import dataclasses
import os
import random
import sys
import unittest

TESTS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(TESTS_DIRECTORY), TESTS_DIRECTORY]
from fixture_drum_voice import FIXTURE_DRUM_VOICE  # noqa: E402
from twosl_dsp.cpu_timing import PROCESS_AND_CHILDREN, CpuTiming  # noqa: E402
from twosl_dsp.patch_match_score import MatchTarget  # noqa: E402
from twosl_dsp.patch_match_search import SearchSettings, match_patch  # noqa: E402

RATE = 48000
TARGET_SECONDS = 0.5
TARGET_NOISE_SEED = 777
# score units (~dB). Measured over 12 random fixture settings, a target rendered with another noise seed: a quarter
# semitone of detune moved the true settings' score by -0.6 .. +2.3, median +0.6 (a noisy hit masks it); so 0.25 is
# under what a quarter semitone usually costs
RECOVERY_MARGIN = 0.25
PARAMETER_TOLERANCE = 0.05
REQUIRED_RECOVERY_RATE = 0.75


@unittest.skipUnless(os.environ.get("TWOSL_DSP_SLOW_TESTS") == "1", "slow: set TWOSL_DSP_SLOW_TESTS=1")
class ParameterRecoveryTests(unittest.TestCase):
    def test_the_matcher_recovers_known_settings_of_the_fixture_drum_voice(self):
        voice = FIXTURE_DRUM_VOICE
        target_voice = dataclasses.replace(voice, noise_seed=TARGET_NOISE_SEED)
        target_count = int(os.environ.get("TWOSL_DSP_RECOVERY_TARGETS", "12"))
        rows = []
        for target_number in range(target_count):
            draw = random.Random(f"recovery/{target_number}")
            true_units = [draw.random() for _ in range(voice.dimension)]
            truth = voice.values_of_units(true_units)
            target_samples = target_voice.render(truth, int(TARGET_SECONDS * RATE), RATE)
            target = MatchTarget(target_samples, RATE)
            truth_score = target.score(voice.render(truth, target.candidate_length, RATE))
            settings = SearchSettings()
            # a report, not a judgement: the search's CPU time over its worker processes, the load read first
            with CpuTiming(f"target {target_number} search", PROCESS_AND_CHILDREN, settings.worker_count()) as timing:
                result = match_patch(voice, target_samples, RATE, settings)
            unit_errors = [abs(found - true) for found, true in zip(result.best_units, true_units)]
            rows.append({"target": target_number, "truth_score": truth_score, "best_score": result.best_score,
                         "recovered": result.best_score <= truth_score + RECOVERY_MARGIN,
                         "unit_errors": unit_errors})
            print(f"target {target_number:2d}: truth {truth_score:5.2f}  found {result.best_score:5.2f}  "
                  f"{'recovered' if rows[-1]['recovered'] else 'MISSED   '}  unit errors "
                  + " ".join(f"{error:.2f}" for error in unit_errors) + f"\n    {timing.report()}",
                  file=sys.stderr, flush=True)
        recovery_rate = sum(row["recovered"] for row in rows) / len(rows)
        parameter_rates = {parameter.name: sum(row["unit_errors"][index] <= PARAMETER_TOLERANCE for row in rows)
                           / len(rows) for index, parameter in enumerate(voice.parameters)}
        all_parameters_rate = sum(all(error <= PARAMETER_TOLERANCE for error in row["unit_errors"])
                                  for row in rows) / len(rows)
        print(f"\nsound recovered (score <= truth's + {RECOVERY_MARGIN}): {recovery_rate:.0%} of {len(rows)}; "
              f"every parameter within "
              f"{PARAMETER_TOLERANCE} of the truth: {all_parameters_rate:.0%}; per parameter: "
              + ", ".join(f"{name} {rate:.0%}" for name, rate in parameter_rates.items()), file=sys.stderr)
        self.assertGreaterEqual(recovery_rate, REQUIRED_RECOVERY_RATE)


if __name__ == "__main__":
    unittest.main()

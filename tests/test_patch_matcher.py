"""The patch matcher (architecture/patch-matcher.md): its score orders hits the way they obviously sound, its parts
are what they claim (loudness = twosl_dsp/bs1770.py's, alignment, the centroid term's ordering), its search is CMA-ES and
deterministic, its voice spec and WAV files fail loudly. Fast: the parameter-recovery validation is the opt-in
tests/test_patch_matcher_recovery.py."""
import dataclasses
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
import wave

TESTS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
KIT_DIRECTORY = os.path.dirname(TESTS_DIRECTORY)
sys.path[:0] = [KIT_DIRECTORY, TESTS_DIRECTORY]
from fixture_drum_voice import FIXTURE_DRUM_VOICE  # noqa: E402
from twosl_dsp import bs1770  # noqa: E402
from twosl_dsp import patch_match_score  # noqa: E402
from twosl_dsp.build_error import BuildError  # noqa: E402
from twosl_dsp.patch_match_score import MatchTarget  # noqa: E402
from twosl_dsp.patch_match_search import (CovarianceMatrixAdaptation, SearchSettings, fold_onto_unit_interval,  # noqa: E402
                                        match_patch, symmetric_eigendecomposition)
from twosl_dsp.gen_blocks import gen_code_with_blocks  # noqa: E402
from twosl_dsp.genexpr import GenProgram  # noqa: E402
from twosl_dsp.patch_match_voice import MatchedParameter, MatchedVoice  # noqa: E402
from twosl_dsp.render_comparison import assert_renders_similar, renders_are_similar  # noqa: E402
from twosl_dsp.techniques.seeded_white_noise import SeededWhiteNoise  # noqa: E402
from twosl_dsp.wave_files import read_wave_file, write_wave_file  # noqa: E402

RATE = 48000

# a kick (low, swept, little noise) and a hat-like hit (all noise, short): fixture voice settings
KICK = {"pitch_hz": 55.0, "sweep_semitones": 30.0, "sweep_ms": 20.0, "decay_ms": 300.0, "noise_level": 0.05,
        "noise_cutoff_hz": 3000.0, "noise_decay_ms": 10.0, "drive": 3.0}
HAT = {"pitch_hz": 300.0, "sweep_semitones": 0.0, "sweep_ms": 2.0, "decay_ms": 30.0, "noise_level": 1.0,
       "noise_cutoff_hz": 12000.0, "noise_decay_ms": 60.0, "drive": 1.0}


def render(values, seconds=0.5, voice=FIXTURE_DRUM_VOICE):
    return voice.render(values, int(seconds * RATE), RATE)


def decaying_sine(hertz, seconds=0.5, decay_seconds=0.15):
    return [0.5 * math.sin(2 * math.pi * hertz * n / RATE) * math.exp(-n / (decay_seconds * RATE))
            for n in range(int(seconds * RATE))]


class ScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kick = render(KICK)
        cls.kick_target = MatchTarget(cls.kick, RATE)

    def test_the_loudness_is_the_kit_meters(self):
        for rate in (48000, 44100):
            signal = [0.3 * math.sin(2 * math.pi * 997 * n / rate) * math.exp(-n / (0.2 * rate))
                      for n in range(int(0.6 * rate))]
            self.assertAlmostEqual(patch_match_score.max_momentary_loudness(signal, rate),
                                   bs1770.max_momentary_loudness([signal], rate), delta=1e-9)

    def test_a_hit_scores_zero_against_itself_at_any_level_and_any_delay(self):
        self.assertEqual(self.kick_target.score(self.kick), 0.0)
        quieter_and_later = [0.0] * 1234 + [0.1 * sample for sample in self.kick]
        self.assertLess(self.kick_target.score(quieter_and_later), 1e-6)

    def test_the_score_orders_hits_the_way_they_obviously_sound(self):
        # itself < another noise realisation < a quarter semitone < a semitone < three semitones < another drum
        other_noise = render(KICK, voice=dataclasses.replace(FIXTURE_DRUM_VOICE, noise_seed=99))

        def detuned(semitones):
            return render({**KICK, "pitch_hz": KICK["pitch_hz"] * 2 ** (semitones / 12)})
        scores = [self.kick_target.score(candidate) for candidate in
                  (self.kick, other_noise, detuned(0.25), detuned(1), detuned(3), render(HAT))]
        self.assertEqual(scores, sorted(scores), scores)
        self.assertEqual(len(set(scores)), len(scores), scores)

    def test_a_longer_or_shorter_decay_is_further_the_more_it_differs(self):
        scores = [self.kick_target.score(render({**KICK, "decay_ms": KICK["decay_ms"] * factor}))
                  for factor in (1.0, 1.1, 1.5, 3.0)]
        self.assertEqual(scores, sorted(scores), scores)

    def test_the_centroid_term_orders_detunings_smoothly(self):
        # it grows with the detuning, never jumps (a pitch tracker's octave flip did), and is 0 for the same hit
        sine_target = MatchTarget(decaying_sine(110.0), RATE)
        sine_terms = [sine_target.components(decaying_sine(110.0 * 2 ** (semitones / 12))).centroid_semitones
                      for semitones in (0.0, 0.1, 0.5, 1.0, 2.0, 4.0, 12.0)]
        self.assertEqual(sine_terms[0], 0.0)
        self.assertEqual(sine_terms, sorted(sine_terms), sine_terms)
        self.assertLess(sine_terms[1], 0.1, sine_terms)
        kick_terms = [self.kick_target.components(render({**KICK, "pitch_hz": KICK["pitch_hz"] * 2 ** (semitones / 12)}))
                      .centroid_semitones for semitones in (0.25, 1.0, 3.0, 6.0, 12.0)]
        self.assertEqual(kick_terms, sorted(kick_terms), kick_terms)

    def test_silence_and_broken_hits(self):
        self.assertEqual(self.kick_target.score([0.0] * RATE), patch_match_score.SILENT_CANDIDATE_SCORE)
        with self.assertRaisesRegex(BuildError, "NaN"):
            self.kick_target.score([0.1, float("nan")] + [0.0] * 100)
        with self.assertRaisesRegex(BuildError, "silent"):
            MatchTarget([0.0] * RATE, RATE)
        with self.assertRaisesRegex(BuildError, "too short"):
            MatchTarget([0.0] * 100 + [0.5] * 50, RATE)

    def test_the_target_is_cut_to_two_seconds_and_the_segment_is_what_was_compared(self):
        long_hit = decaying_sine(220.0, seconds=3.0, decay_seconds=1.0)
        target = MatchTarget(long_hit, RATE)
        self.assertEqual(target.analysis_length, 2 * RATE)
        segment = target.analysed_segment(long_hit)
        self.assertEqual(len(segment), 2 * RATE)
        self.assertAlmostEqual(patch_match_score.max_momentary_loudness(segment, RATE),
                               patch_match_score.REFERENCE_LOUDNESS_LUFS, delta=1e-9)


class VoiceTests(unittest.TestCase):
    def test_units_map_to_values_and_back(self):
        log_parameter = MatchedParameter.continuous("decay_ms", 10, 1000, "log")
        self.assertAlmostEqual(log_parameter.value_of_unit(0.5), 100.0)
        self.assertAlmostEqual(log_parameter.unit_of_value(100.0), 0.5)
        self.assertEqual(MatchedParameter.continuous("x", -1, 1).value_of_unit(1.7), 1.0)
        self.assertEqual(MatchedParameter.integer("steps", 0, 4).value_of_unit(0.6), 2.0)
        mode = MatchedParameter.enum("mode", (0, 1, 2))
        self.assertEqual([mode.value_of_unit(unit) for unit in (0.0, 0.34, 0.99, 1.0)], [0.0, 1.0, 2.0, 2.0])
        self.assertAlmostEqual(mode.unit_of_value(1), 0.5)

    def test_a_bad_spec_fails_loudly(self):
        with self.assertRaisesRegex(BuildError, "positive minimum"):
            MatchedParameter.continuous("decay_ms", 0, 10, "log")
        with self.assertRaisesRegex(BuildError, "not under"):
            MatchedParameter.continuous("x", 1, 1)
        with self.assertRaisesRegex(BuildError, "does not declare"):
            dataclasses.replace(FIXTURE_DRUM_VOICE, parameters=(MatchedParameter.continuous("cutoff", 1, 2),))
        with self.assertRaisesRegex(BuildError, "outside its Param"):
            dataclasses.replace(FIXTURE_DRUM_VOICE, parameters=(MatchedParameter.continuous("drive", 0.5, 2),))
        without_its_drive_default = FIXTURE_DRUM_VOICE.gen_code.replace("Param drive(2, ", "Param drive(")
        with self.assertRaisesRegex(BuildError, r"Params \['drive'\] have no default in the code and are neither"):
            dataclasses.replace(FIXTURE_DRUM_VOICE, gen_code=without_its_drive_default, parameters=tuple(
                parameter for parameter in FIXTURE_DRUM_VOICE.parameters if parameter.name != "drive"))
        with self.assertRaisesRegex(BuildError, "both fixed and searched"):
            dataclasses.replace(FIXTURE_DRUM_VOICE, fixed_values=(("drive", 2.0),))
        with self.assertRaisesRegex(BuildError, "not one of its choices"):
            MatchedParameter.enum("mode", (0, 1)).unit_of_value(3)

    def test_a_render_has_no_memory_of_the_one_before(self):
        assert_renders_similar(render(KICK, 0.1), render(KICK, 0.1), RATE, "the second render")

    def test_the_optimised_build_renders_the_same_samples(self):
        # the voice renders at -O2 (genexpr.OPTIMISED_COMPILER_FLAGS); the floating-point flags make it the -O0 sound
        voice = dataclasses.replace(FIXTURE_DRUM_VOICE, fixed_values=())
        program = GenProgram(voice.gen_code, voice.num_inputs, voice.num_outputs, samplerate=RATE, seed=voice.noise_seed)
        for name, value in KICK.items():
            program.set_param(name, value)
        trigger = [1.0] + [0.0] * (RATE // 2 - 1)
        assert_renders_similar(program.run(RATE // 2, [trigger])[0], render(KICK, 0.5), RATE, "the -O2 render")

    def test_the_noise_seed_reaches_the_kits_seeded_noise_through_the_seed_param(self):
        # a voice whose noise is the kit's SeededWhiteNoise, seeded by its Param "seed": the matched voice's seed
        # decides its noise (gen~'s noise() is not in it)
        noise = SeededWhiteNoise("white", seed="seed")
        code = gen_code_with_blocks("/*GEN_BLOCK_FUNCTIONS*/\nParam level(0.5, min=0, max=1);\n"
                                    "Param seed(1, min=0, max=2147483646);\n/*GEN_BLOCK_DECLARATIONS*/\n/*WHITE*/\n"
                                    "out1 = white_out * level * (in1 + 1);\n", [noise], "seeded voice")
        voice = MatchedVoice(name="seeded", gen_code=code, num_inputs=1, num_outputs=1,
                             parameters=(MatchedParameter.continuous("level", 0.1, 1),), noise_seed=7,
                             noise_seed_param="seed")
        hits = {seed: dataclasses.replace(voice, noise_seed=seed).render({"level": 0.5}, 64, RATE) for seed in (7, 8)}
        assert_renders_similar(hits[7], voice.render({"level": 0.5}, 64, RATE), RATE, "seed 7 again")
        self.assertFalse(renders_are_similar(hits[7], hits[8], RATE).similar, "seeds 7 and 8 give the same noise")
        unplumbed = dataclasses.replace(voice, noise_seed_param="")
        assert_renders_similar(unplumbed.render({"level": 0.5}, 64, RATE),
                               dataclasses.replace(unplumbed, noise_seed=8).render({"level": 0.5}, 64, RATE), RATE,
                               "the seed without its Param")
        with self.assertRaisesRegex(BuildError, "not declared"):
            dataclasses.replace(voice, noise_seed_param="sead")
        with self.assertRaisesRegex(BuildError, "also searched or fixed"):
            dataclasses.replace(voice, noise_seed_param="level")
        with self.assertRaisesRegex(BuildError, "outside its Param"):
            dataclasses.replace(voice, noise_seed=-3)


class SearchTests(unittest.TestCase):
    def test_the_fold_maps_the_line_onto_the_unit_interval(self):
        for value, folded in ((0.25, 0.25), (1.2, 0.8), (-0.1, 0.1), (2.3, 0.3), (-1.5, 0.5)):
            self.assertAlmostEqual(fold_onto_unit_interval(value), folded)

    def test_the_eigendecomposition_rebuilds_the_matrix(self):
        matrix = [[4.0, 1.0, 0.5], [1.0, 3.0, 0.2], [0.5, 0.2, 1.0]]
        values, vectors = symmetric_eigendecomposition(matrix)
        for row in range(3):
            for column in range(3):
                rebuilt = sum(vectors[row][k] * values[k] * vectors[column][k] for k in range(3))
                self.assertAlmostEqual(rebuilt, matrix[row][column], places=10)

    def test_cma_es_solves_a_rotated_ellipsoid_the_same_way_every_time(self):
        def run():
            source = random.Random(3)
            search = CovarianceMatrixAdaptation([0.8] * 5, 0.3, source)
            for _ in range(400):
                candidates = search.ask()
                search.tell([sum((10 ** (i / 2)) * (x[i] - 0.3 + 0.1 * x[(i + 1) % 5]) ** 2 for i in range(5))
                             for x in candidates])
            return search.mean
        first, second = run(), run()
        self.assertEqual(first, second)
        for index, value in enumerate(first):
            self.assertAlmostEqual(value, 0.3 / 1.1, delta=1e-4, msg=index)

    def test_a_two_parameter_match_finds_the_target_and_is_deterministic(self):
        voice = dataclasses.replace(
            FIXTURE_DRUM_VOICE, name="fixture drum: pitch and decay",
            parameters=(MatchedParameter.continuous("pitch_hz", 30, 400, "log"),
                        MatchedParameter.continuous("decay_ms", 30, 1500, "log")),
            fixed_values=tuple((name, value) for name, value in KICK.items() if name not in ("pitch_hz", "decay_ms")))
        truth = {"pitch_hz": 72.0, "decay_ms": 180.0}
        target_samples = render(truth, 0.4, voice=voice)
        settings = SearchSettings(strands=2, evaluations_per_strand=150, seed=7, workers=1)
        result = match_patch(voice, target_samples, RATE, settings)
        self.assertLess(result.best_score, 0.3, result.as_dict())
        self.assertAlmostEqual(result.best_values["pitch_hz"] / truth["pitch_hz"], 1.0, delta=0.01)
        self.assertAlmostEqual(result.best_values["decay_ms"] / truth["decay_ms"], 1.0, delta=0.05)
        curve = result.combined_curve()
        self.assertEqual([score for _, score in curve], sorted((score for _, score in curve), reverse=True))
        again = match_patch(voice, target_samples, RATE, dataclasses.replace(settings, workers=2))
        self.assertEqual(again.best_values, result.best_values)

    def test_an_enum_is_swept_on_every_choice_not_searched_as_a_continuum(self):
        # an enum's choices in no order of sound: the search tries each one at its best continuous setting
        voice = dataclasses.replace(
            FIXTURE_DRUM_VOICE, name="fixture drum: pitch and a decay choice",
            parameters=(MatchedParameter.continuous("pitch_hz", 30, 400, "log"),
                        MatchedParameter.enum("decay_ms", (600.0, 60.0, 180.0, 1200.0))),
            fixed_values=tuple((name, value) for name, value in KICK.items() if name not in ("pitch_hz", "decay_ms")))
        truth = {"pitch_hz": 72.0, "decay_ms": 180.0}
        target_samples = render(truth, 0.4, voice=voice)
        result = match_patch(voice, target_samples, RATE,
                             SearchSettings(strands=1, evaluations_per_strand=200, seed=3, workers=1))
        self.assertEqual(result.best_values["decay_ms"], 180.0, result.as_dict())
        self.assertAlmostEqual(result.best_values["pitch_hz"] / truth["pitch_hz"], 1.0, delta=0.01)


class WaveFileTests(unittest.TestCase):
    def test_float_round_trip_and_pcm_reading(self):
        with tempfile.TemporaryDirectory() as directory:
            float_path = os.path.join(directory, "float.wav")
            channels = [[0.5, -0.25, 0.0], [0.125, 1.0, -1.0]]
            write_wave_file(float_path, channels, 44100)
            self.assertEqual(read_wave_file(float_path), (channels, 44100))
            for width, scale in ((2, 32768), (3, 8388608)):
                pcm_path = os.path.join(directory, f"pcm{width}.wav")
                with wave.open(pcm_path, "wb") as handle:
                    handle.setnchannels(1)
                    handle.setsampwidth(width)
                    handle.setframerate(96000)
                    handle.writeframes(b"".join((value).to_bytes(width, "little", signed=True)
                                                for value in (0, scale // 2, -scale)))
                self.assertEqual(read_wave_file(pcm_path), ([[0.0, 0.5, -1.0]], 96000))

    def test_what_is_not_a_readable_wav_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "not.wav")
            with open(path, "wb") as handle:
                handle.write(b"RIFF\x00\x00\x00\x00WAVEjunk")
            with self.assertRaisesRegex(BuildError, "fmt"):
                read_wave_file(path)
            with self.assertRaisesRegex(BuildError, "NaN"):
                write_wave_file(os.path.join(directory, "nan.wav"), [[float("nan")]], 48000)


class CommandLineTests(unittest.TestCase):
    def test_the_tool_writes_the_result_and_the_a_b_files(self):
        with tempfile.TemporaryDirectory() as directory:
            target_path = os.path.join(directory, "kick.wav")
            write_wave_file(target_path, [render(KICK, 0.3)] * 2, RATE)
            out_path = os.path.join(directory, "kick.result.json")
            completed = subprocess.run(
                [sys.executable, os.path.join(KIT_DIRECTORY, "tools", "match_patch.py"),
                 "--voice", os.path.join(TESTS_DIRECTORY, "fixture_drum_voice.py") + ":FIXTURE_DRUM_VOICE",
                 "--target", target_path, "--out", out_path, "--strands", "1", "--evaluations", "40",
                 "--workers", "1", "--quiet"], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with open(out_path, encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertEqual(set(report["best_values"]), {parameter.name for parameter in FIXTURE_DRUM_VOICE.parameters})
            for key in ("match_wav", "target_wav"):
                channels, rate = read_wave_file(report[key])
                self.assertEqual((len(channels), rate), (1, RATE))
            bad = subprocess.run([sys.executable, os.path.join(KIT_DIRECTORY, "tools", "match_patch.py"),
                                  "--voice", "no_such_module:VOICE", "--target", target_path, "--out", out_path],
                                 capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("no_such_module", bad.stderr)


if __name__ == "__main__":
    unittest.main()

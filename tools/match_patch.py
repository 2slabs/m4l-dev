#!/usr/bin/env python3
"""Match a voice's parameters to a target hit (architecture/patch-matcher.md): a thin CLI over m4l_dev's patch matcher.

    python3 tools/match_patch.py --voice tests/fixture_drum_voice.py:FIXTURE_DRUM_VOICE \\
        --target match-targets/909-kick.wav --out match-targets/909-kick.result.json

--voice is MODULE:NAME or path/to/file.py:NAME, NAME a MatchedVoice or a function of no arguments returning one.
Writes OUT (the best parameters, the score and its parts, the score curve, every strand's result), and beside it
OUT's name with .match.wav (the best render) and .target.wav (the target as it was compared): both cut at their onset
and at the same loudness, for an A/B. Targets live in match-targets/ (gitignored): the device ships parameters, never
samples. Exit 0 when a match was written, 1 on any error (the message says what and where).
"""
import argparse
import importlib
import importlib.util
import json
import os
import sys

KIT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KIT_DIRECTORY not in sys.path:
    sys.path.insert(0, KIT_DIRECTORY)

from m4l_dev.build_error import BuildError  # noqa: E402
from m4l_dev.patch_match_score import MatchTarget  # noqa: E402
from m4l_dev.patch_match_search import SearchSettings, match_patch  # noqa: E402
from m4l_dev.patch_match_voice import MatchedVoice  # noqa: E402
from m4l_dev.wave_files import read_wave_file, write_wave_file  # noqa: E402


def load_voice(reference):
    if ":" not in reference:
        raise BuildError(f"--voice '{reference}': expected MODULE:NAME or path/to/file.py:NAME")
    location, name = reference.rsplit(":", 1)
    if location.endswith(".py"):
        path = os.path.abspath(location)
        if not os.path.isfile(path):
            raise BuildError(f"--voice: no file {path}")
        sys.path.insert(0, os.path.dirname(path))   # the voice module's own imports, and the worker processes'
        module = importlib.import_module(os.path.splitext(os.path.basename(path))[0])
    else:
        sys.path.insert(0, os.getcwd())
        module = importlib.import_module(location)
    if not hasattr(module, name):
        raise BuildError(f"--voice: {location} has no '{name}'")
    voice = getattr(module, name)
    if callable(voice) and not isinstance(voice, MatchedVoice):
        voice = voice()
    if not isinstance(voice, MatchedVoice):
        raise BuildError(f"--voice: {reference} is a {type(voice).__name__}, not a MatchedVoice")
    return voice


def target_channel(channels, choice, path):
    if choice == "mix":
        return [sum(frame) / len(channels) for frame in zip(*channels)]
    index = int(choice) - 1
    if not 0 <= index < len(channels):
        raise BuildError(f"{path}: --channel {choice}, the file has {len(channels)}")
    return channels[index]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--voice", required=True, help="MODULE:NAME or path/to/file.py:NAME")
    parser.add_argument("--target", required=True, help="the target hit, a WAV file")
    parser.add_argument("--out", required=True, help="the result's JSON path")
    parser.add_argument("--channel", default="mix", help="'mix' (the channels' mean, default) or a channel number")
    defaults = SearchSettings()
    parser.add_argument("--strands", type=int, default=defaults.strands)
    parser.add_argument("--evaluations", type=int, default=defaults.evaluations_per_strand,
                        help="renders per strand")
    parser.add_argument("--refinement-fraction", type=float, default=defaults.refinement_fraction)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    parser.add_argument("--workers", type=int, default=defaults.workers,
                        help="processes (0: one per strand up to the CPUs; 1: no extra process)")
    parser.add_argument("--quiet", action="store_true", help="no progress lines on stderr")
    arguments = parser.parse_args(argv)
    try:
        voice = load_voice(arguments.voice)
        channels, rate = read_wave_file(arguments.target)
        target_samples = target_channel(channels, arguments.channel, arguments.target)
        settings = SearchSettings(strands=arguments.strands, evaluations_per_strand=arguments.evaluations,
                                  refinement_fraction=arguments.refinement_fraction, seed=arguments.seed,
                                  workers=arguments.workers, progress=not arguments.quiet)
        result = match_patch(voice, target_samples, rate, settings)
        target = MatchTarget(target_samples, rate, description=arguments.target)
        best_render = voice.render(result.best_values, target.candidate_length, rate)
        stem = os.path.splitext(arguments.out)[0]
        match_wave_path, target_wave_path = f"{stem}.match.wav", f"{stem}.target.wav"
        write_wave_file(match_wave_path, [target.analysed_segment(best_render, "the best render")], rate)
        write_wave_file(target_wave_path, [target.analysed_segment(target_samples, arguments.target)], rate)
        report = {"target": os.path.abspath(arguments.target), "channel": arguments.channel, "sample_rate": rate,
                  "analysed_seconds": target.analysis_length / rate, "match_wav": os.path.abspath(match_wave_path),
                  "target_wav": os.path.abspath(target_wave_path), **result.as_dict()}
        with open(arguments.out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    except (BuildError, OSError, ImportError) as problem:
        print(f"match_patch: {problem}", file=sys.stderr)
        return 1
    print(f"score {result.best_score:.3f} ({result.best_components['spectral_db']:.2f} dB spectral, "
          f"{result.best_components['envelope_db']:.2f} dB envelope, "
          f"{result.best_components['pitch_semitones']:.2f} semitones pitch) in {result.seconds:.0f} s")
    for name, value in result.best_values.items():
        print(f"  {name} = {value:.6g}")
    print(f"wrote {arguments.out}, {match_wave_path}, {target_wave_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

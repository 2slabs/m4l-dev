"""The patch matcher's score: how far a rendered hit is from a target hit (architecture/patch-matcher.md,
references/sound-matching.md).

Both hits are cut at their onset (the first sample within ONSET_THRESHOLD_DB of the peak, less PREROLL_SECONDS),
to the same analysis length (the target's, at most ANALYSIS_SECONDS_LIMIT: Genopatch's "up to two seconds"), and
scaled so their loudest 400 ms window (EBU Tech 3341's momentary loudness, BS.1770's K-weighting, twosl_dsp/bs1770.py)
reads REFERENCE_LOUDNESS_LUFS: the score ignores level. Then (twosl_dsp/patch_match_features.c):

  spectral  the mean |difference| in dB of log-mel spectrograms at four FFT sizes (4096, 2048, 1024 over the whole hit,
            512 over its first 50 ms; hop 1/4), averaged over the sizes: DDSP's multi-scale spectral loss (its log
            term) on a mel scale; cells more than 70 dB under the target's loudest cell count as that floor, cells
            where both are on the floor are left out
  envelope  the same over a peak-follower envelope of the squared hit (instant attack, 50 ms release, read every
            2.5 ms): the attack's fine timing, which no FFT size here resolves
  centroid  the mean |difference| in semitones of each frame's log2-frequency spectral centroid (the whole-hit
            log-mel spectrograms, floored as above), each target frame weighted by its level: cell by cell spectral
            distances order pitch and brightness differences badly, the log spectral centroid orders them
            perfectly and smoothly (references/sound-matching.md, D)
  Why these and not DDSP's six sizes etc.: patch_match_features.c's comments, each with its measurement.

  score = spectral + ENVELOPE_WEIGHT * envelope + CENTROID_WEIGHT * centroid    (0 for identical hits; "dB-like")

No pitch tracker: a YIN pitch term (until 2026-10-20) flipped between dips of YIN's difference function on folded,
modulated or noisy tones under a 0.1 % move of a parameter, each flip costing up to 12 semitones, which made the score
a needle around the truth (PLANS/2026-10-20-matcher-search.md, H5); the fixture voice's recovery rose from 85 % with it
to 100 % with the centroid term instead.

A silent candidate scores SILENT_CANDIDATE_SCORE (the worst); a candidate holding a NaN or infinity is a voice bug and
raises. Standard library + the system C compiler (the analysis is C, built once into the kit's cache, as
twosl_dsp/genexpr.py builds the renderer).
"""
import array
import ctypes
import os
from dataclasses import dataclass

from twosl_dsp import bs1770
from twosl_dsp.build_error import BuildError
from twosl_dsp.c_library_cache import load_c_library

ONSET_THRESHOLD_DB = -40.0
PREROLL_SECONDS = 0.002
ANALYSIS_SECONDS_LIMIT = 2.0
REFERENCE_LOUDNESS_LUFS = -20.0
ENVELOPE_WEIGHT = 1.0
# per semitone of centroid difference: an octave costs 3, as much as a clearly different spectrum (measured on the
# fixture voice: 100 % recovery at 0.25, PLANS/2026-10-20-matcher-search.md)
CENTROID_WEIGHT = 0.25
SILENT_CANDIDATE_SCORE = 1000.0

FEATURES_SOURCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch_match_features.c")
FEATURES_COMPILER_FLAGS = ("-O2", "-std=c99", "-fPIC", "-shared", "-fno-fast-math", "-D_DEFAULT_SOURCE")

MATCH_OK, MATCH_SILENT, MATCH_NOT_FINITE, MATCH_OUT_OF_MEMORY, MATCH_BAD_ARGUMENT = range(5)
STATUS_NAMES = {MATCH_SILENT: "silent", MATCH_NOT_FINITE: "holds a NaN or infinity",
                MATCH_OUT_OF_MEMORY: "out of memory", MATCH_BAD_ARGUMENT: "bad argument"}


_features_library = None


def features_library():
    """patch_match_features.c, built once per source / compiler / flags into the kit's C cache, loaded once per
    process."""
    global _features_library
    if _features_library is not None:
        return _features_library
    with open(FEATURES_SOURCE_PATH, encoding="utf-8") as handle:
        c_source = handle.read()
    library = load_c_library(c_source, FEATURES_COMPILER_FLAGS, file_name_prefix="patch-match-features-")
    double_pointer = ctypes.c_void_p
    library.match_feature_size.restype = ctypes.c_long
    library.match_feature_size.argtypes = [ctypes.c_long, ctypes.c_double]
    library.match_onset.restype = ctypes.c_long
    library.match_onset.argtypes = [double_pointer, ctypes.c_long, ctypes.c_double]
    library.match_max_momentary_loudness.restype = ctypes.c_double
    library.match_max_momentary_loudness.argtypes = [double_pointer, ctypes.c_long, ctypes.c_double, double_pointer]
    library.match_analyse.restype = ctypes.c_int
    library.match_analyse.argtypes = [double_pointer, ctypes.c_long, ctypes.c_double, ctypes.c_double, ctypes.c_long,
                                      ctypes.c_long, double_pointer, ctypes.c_double, double_pointer,
                                      ctypes.POINTER(ctypes.c_double)]
    library.match_distance.restype = ctypes.c_int
    library.match_distance.argtypes = [double_pointer, double_pointer, ctypes.c_long, ctypes.c_double, double_pointer]
    _features_library = library
    return library


def _address(double_array):
    return double_array.buffer_info()[0]


def _as_double_array(samples):
    return samples if isinstance(samples, array.array) and samples.typecode == "d" else array.array("d", samples)


_k_weights_by_rate = {}


def k_weights_of(rate):
    """The two K-weighting stages at `rate` (twosl_dsp/bs1770.py) as the C's ten numbers: b0 b1 b2 a1 a2, twice."""
    if rate not in _k_weights_by_rate:
        _k_weights_by_rate[rate] = array.array("d", [coefficient for b, a in bs1770.k_weighting_stages(rate)
                                                     for coefficient in (*b, *a)])
    return _k_weights_by_rate[rate]


def max_momentary_loudness(samples, rate):
    """The C's loudest-400-ms loudness (LUFS) of one channel (bs1770.max_momentary_loudness's number, for any length:
    a hit shorter than 400 ms counts as padded with silence)."""
    signal = _as_double_array(samples)
    return features_library().match_max_momentary_loudness(_address(signal), len(signal), float(rate),
                                                           _address(k_weights_of(float(rate))))


def onset_index(samples):
    """The first sample within ONSET_THRESHOLD_DB of the peak, or None when silent."""
    signal = _as_double_array(samples)
    index = features_library().match_onset(_address(signal), len(signal), ONSET_THRESHOLD_DB)
    return None if index < 0 else index


@dataclass(frozen=True)
class ScoreComponents:
    spectral_db: float
    envelope_db: float
    centroid_semitones: float
    silent: bool = False

    @property
    def score(self):
        if self.silent:
            return SILENT_CANDIDATE_SCORE
        return self.spectral_db + ENVELOPE_WEIGHT * self.envelope_db + CENTROID_WEIGHT * self.centroid_semitones

    def as_dict(self):
        return {"score": self.score, "spectral_db": self.spectral_db, "envelope_db": self.envelope_db,
                "centroid_semitones": self.centroid_semitones, "silent": self.silent}


class MatchTarget:
    """A target hit, analysed once; `components(candidate)` / `score(candidate)` compare a candidate at the same rate.

    `analysis_length` samples are compared, from PREROLL_SECONDS before each hit's onset. A candidate needs at least
    `candidate_length` samples: the analysis length plus CANDIDATE_LATENCY_SECONDS for a voice whose onset comes late.
    """
    CANDIDATE_LATENCY_SECONDS = 0.05

    def __init__(self, samples, rate, description="target"):
        self.rate = float(rate)
        self.description = description
        signal = _as_double_array(samples)
        if len(signal) == 0:
            raise BuildError(f"{description}: no samples")
        onset = onset_index(signal)
        if onset is None:
            raise BuildError(f"{description}: silent, nothing to match")
        self.preroll = int(round(PREROLL_SECONDS * self.rate))
        self.onset = onset
        self.analysis_length = min(int(round(ANALYSIS_SECONDS_LIMIT * self.rate)),
                                   len(signal) - onset + min(self.preroll, onset))
        if self.analysis_length < int(0.01 * self.rate):
            raise BuildError(f"{description}: under 10 ms after its onset ({self.analysis_length} samples): "
                                  "too short to match")
        self.candidate_length = self.analysis_length + int(round(self.CANDIDATE_LATENCY_SECONDS * self.rate))
        self.features, self.gain = self._analyse(signal, description)
        self._scratch = array.array("d", bytes(8 * len(self.features)))
        self._components = array.array("d", [0.0] * 3)

    def _analyse(self, signal, description, into=None):
        library = features_library()
        size = library.match_feature_size(self.analysis_length, self.rate)
        if size <= 0:
            raise BuildError(f"{description}: no feature layout for {self.analysis_length} samples at "
                                  f"{self.rate} Hz")
        features = into if into is not None else array.array("d", bytes(8 * size))
        gain = ctypes.c_double(0.0)
        status = library.match_analyse(_address(signal), len(signal), self.rate, ONSET_THRESHOLD_DB, self.preroll,
                                       self.analysis_length, _address(k_weights_of(self.rate)),
                                       REFERENCE_LOUDNESS_LUFS, _address(features), ctypes.byref(gain))
        if status == MATCH_SILENT:
            return None, None
        if status != MATCH_OK:
            raise BuildError(f"{description}: the analysis failed: {STATUS_NAMES.get(status, status)}")
        return features, gain.value

    def components(self, candidate_samples, description="candidate"):
        signal = _as_double_array(candidate_samples)
        if len(signal) == 0:
            raise BuildError(f"{description}: no samples")
        features, _ = self._analyse(signal, description, into=self._scratch)
        if features is None:
            return ScoreComponents(0.0, 0.0, 0.0, silent=True)
        status = features_library().match_distance(_address(self.features), _address(features), self.analysis_length,
                                                   self.rate, _address(self._components))
        if status != MATCH_OK:
            raise BuildError(f"{description}: the distance failed: {STATUS_NAMES.get(status, status)}")
        return ScoreComponents(*self._components)

    def score(self, candidate_samples, description="candidate"):
        return self.components(candidate_samples, description).score

    def analysed_segment(self, samples, description="hit"):
        """The part of `samples` the score compares, as it compares it: from PREROLL_SECONDS before the onset,
        `analysis_length` long, scaled to REFERENCE_LOUDNESS_LUFS (an A/B at equal loudness)."""
        signal = _as_double_array(samples)
        onset = onset_index(signal)
        _, gain = self._analyse(signal, description, into=array.array("d", bytes(8 * len(self.features))))
        if onset is None or gain is None:
            raise BuildError(f"{description}: silent, no segment to compare")
        first = onset - self.preroll
        return [gain * signal[index] if 0 <= index < len(signal) else 0.0
                for index in range(first, first + self.analysis_length)]

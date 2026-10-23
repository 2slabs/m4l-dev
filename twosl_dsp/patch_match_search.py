"""The patch matcher's search (architecture/patch-matcher.md, references/sound-matching.md): a voice's parameters
for a target hit, by rendering and scoring candidates (Genopatch's guess, render, compare, refine, without the neural
warm start).

Several independent strands (Genopatch grows four; six here by default), each in its own process:
  1. global: CMA-ES (Hansen's tutorial, its default settings) over the continuous and integer parameters from a random
     point of the unit cube with step GLOBAL_STEP, restarted from a new random point with twice the population when it
     has converged or stalls (IPOP);
  2. a sweep of the enums at the strand's best: each one tried at every choice, the rest held (an enum's choices are
     unordered: a filter mode, a shift register's pattern; on a CMA-ES axis any step lands on an unrelated choice and
     selection learns nothing, PLANS/2026-10-20-matcher-search.md H6 / H7);
  3. refinement: CMA-ES from the strand's best with step REFINEMENT_STEP (Genopatch's restart "using the currently
     loaded patch as the search base"), in two halves with an enum sweep after each when the voice has enums.
The search runs in an unbounded space folded onto the unit cube (a triangle wave: 1.2 -> 0.8, -0.1 -> 0.1), so CMA-ES
needs no bound handling and every candidate is in range; MatchedParameter maps the unit cube to Param values.

Deterministic: a strand's random numbers come from (seed, strand number) only, so a result depends on the voice, the
target, the settings and the seed, never on the number of worker processes. Standard library only (no numpy): the
covariance's eigendecomposition is cyclic Jacobi, cheap at a voice's ~10-30 parameters.
"""
import array
import math
import multiprocessing
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

from twosl_dsp.build_error import BuildError
from twosl_dsp.patch_match_score import MatchTarget

GLOBAL_STEP = 0.3
REFINEMENT_STEP = 0.05
# a run has converged when its distribution's longest axis is under this (unit cube): a global run restarts, a
# refinement stops
GLOBAL_CONVERGED_STEP = 1e-3
REFINEMENT_CONVERGED_STEP = 1e-5
# a global run restarts when its best has improved by less than this (score units) over its last
# 10 + 30 n / lambda generations (the tutorial's TolStagnation-like window): local minima are common (measured on the
# fixture drum voice: converged runs end anywhere from the truth's score to 2.5 x it)
STALL_IMPROVEMENT = 0.02


@dataclass(frozen=True)
class SearchSettings:
    # measured on the fixture drum voice (tests/test_patch_matcher_recovery.py): 6 x 2000 with half spent refining
    # reached the truth's own score on most targets, where 4 x 2000 with 30 % refining stopped in local minima
    strands: int = 6
    evaluations_per_strand: int = 2000
    refinement_fraction: float = 0.5      # of each strand's evaluations, spent refining its best
    stall_improvement: float = STALL_IMPROVEMENT
    seed: int = 1
    workers: int = 0                      # 0: one process per strand, at most the CPUs; 1: in this process
    progress: bool = False                # a line on stderr per strand phase / restart

    def worker_count(self):
        """The processes a search runs its strands on: `workers`, or with 0 one per strand, at most the CPUs."""
        return self.workers or min(self.strands, os.cpu_count() or 1)

    def __post_init__(self):
        if self.strands < 1:
            raise BuildError(f"strands must be at least 1, not {self.strands}")
        if self.evaluations_per_strand < 20:
            raise BuildError(f"evaluations_per_strand {self.evaluations_per_strand} is too few to search")
        if not 0.0 <= self.refinement_fraction < 1.0:
            raise BuildError(f"refinement_fraction must be in [0, 1), not {self.refinement_fraction}")
        if self.workers < 0:
            raise BuildError(f"workers must be >= 0, not {self.workers}")


def fold_onto_unit_interval(value):
    """The triangle wave that maps the real line onto [0, 1], identity on [0, 1], mirrored at its ends."""
    remainder = value % 2.0
    return remainder if remainder <= 1.0 else 2.0 - remainder


# ---------------------------------------------------------------------------------------------- linear algebra

def symmetric_eigendecomposition(matrix):
    """(eigenvalues, eigenvectors as columns) of a symmetric matrix (list of rows), by cyclic Jacobi rotations."""
    size = len(matrix)
    a = [row[:] for row in matrix]
    vectors = [[1.0 if row == column else 0.0 for column in range(size)] for row in range(size)]
    for _ in range(100):
        off_diagonal = sum(a[row][column] ** 2 for row in range(size) for column in range(row + 1, size))
        if off_diagonal < 1e-22 * max(1e-300, sum(a[index][index] ** 2 for index in range(size))):
            break
        for p in range(size - 1):
            for q in range(p + 1, size):
                if a[p][q] == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(size):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(size):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(size):
                    vkp, vkq = vectors[k][p], vectors[k][q]
                    vectors[k][p] = c * vkp - s * vkq
                    vectors[k][q] = s * vkp + c * vkq
    else:
        raise BuildError("the covariance's eigendecomposition did not converge in 100 sweeps")
    return [a[index][index] for index in range(size)], vectors


# ---------------------------------------------------------------------------------------------- CMA-ES

class CovarianceMatrixAdaptation:
    """(mu/mu_w, lambda)-CMA-ES with the default settings of Hansen, "The CMA Evolution Strategy: A Tutorial"
    (arXiv 1604.00772, references/sound-matching.md): positive weights only, rank-one and rank-mu updates, cumulative
    step-size adaptation. ask() gives a population, tell() takes their scores in the same order."""

    def __init__(self, mean, step, random_source, population=None):
        n = len(mean)
        self.dimension = n
        self.mean = list(mean)
        self.step = step
        self.random_source = random_source
        self.population = population or 4 + int(3 * math.log(n))
        self.parents = self.population // 2
        raw_weights = [math.log((self.population + 1) / 2) - math.log(rank + 1) for rank in range(self.parents)]
        total = sum(raw_weights)
        self.weights = [weight / total for weight in raw_weights]
        self.effective_parents = 1.0 / sum(weight * weight for weight in self.weights)
        mu_eff = self.effective_parents
        self.c_sigma = (mu_eff + 2) / (n + mu_eff + 5)
        self.d_sigma = 1 + 2 * max(0.0, math.sqrt((mu_eff - 1) / (n + 1)) - 1) + self.c_sigma
        self.c_c = (4 + mu_eff / n) / (n + 4 + 2 * mu_eff / n)
        self.c_1 = 2 / ((n + 1.3) ** 2 + mu_eff)
        self.c_mu = min(1 - self.c_1, 2 * (0.25 + mu_eff + 1 / mu_eff - 2) / ((n + 2) ** 2 + mu_eff))
        self.expected_norm = math.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n * n))
        self.path_sigma = [0.0] * n
        self.path_c = [0.0] * n
        self.covariance = [[1.0 if row == column else 0.0 for column in range(n)] for row in range(n)]
        self.basis = [row[:] for row in self.covariance]
        self.scales = [1.0] * n                     # sqrt of the eigenvalues
        self.generation = 0
        self._decomposed_at_generation = 0
        self._last_steps = None

    def ask(self):
        n = self.dimension
        normal = self.random_source.gauss
        steps = []
        for _ in range(self.population):
            z = [normal(0.0, 1.0) for _ in range(n)]
            scaled = [self.scales[index] * z[index] for index in range(n)]
            steps.append([sum(self.basis[row][index] * scaled[index] for index in range(n)) for row in range(n)])
        self._last_steps = steps
        return [[self.mean[index] + self.step * step[index] for index in range(n)] for step in steps]

    def tell(self, scores):
        if self._last_steps is None or len(scores) != self.population:
            raise BuildError("CMA-ES: tell() needs one score per candidate of the last ask()")
        n = self.dimension
        order = sorted(range(self.population), key=lambda index: scores[index])
        selected = [self._last_steps[index] for index in order[:self.parents]]
        weighted_step = [sum(weight * step[index] for weight, step in zip(self.weights, selected)) for index in range(n)]
        self.mean = [self.mean[index] + self.step * weighted_step[index] for index in range(n)]
        # C^(-1/2) y_w = B D^-1 B^T y_w
        projected = [sum(self.basis[row][index] * weighted_step[row] for row in range(n)) / self.scales[index]
                     for index in range(n)]
        whitened = [sum(self.basis[row][index] * projected[index] for index in range(n)) for row in range(n)]
        sigma_gain = math.sqrt(self.c_sigma * (2 - self.c_sigma) * self.effective_parents)
        self.path_sigma = [(1 - self.c_sigma) * self.path_sigma[index] + sigma_gain * whitened[index]
                           for index in range(n)]
        self.generation += 1
        path_sigma_norm = math.sqrt(sum(value * value for value in self.path_sigma))
        stalled_threshold = (1.4 + 2 / (n + 1)) * self.expected_norm
        h_sigma = 1.0 if (path_sigma_norm / math.sqrt(1 - (1 - self.c_sigma) ** (2 * self.generation))
                          < stalled_threshold) else 0.0
        c_gain = h_sigma * math.sqrt(self.c_c * (2 - self.c_c) * self.effective_parents)
        self.path_c = [(1 - self.c_c) * self.path_c[index] + c_gain * weighted_step[index] for index in range(n)]
        keep = 1 - self.c_1 - self.c_mu + (1 - h_sigma) * self.c_1 * self.c_c * (2 - self.c_c)
        for row in range(n):
            for column in range(row + 1):
                rank_mu = sum(weight * step[row] * step[column] for weight, step in zip(self.weights, selected))
                value = (keep * self.covariance[row][column] + self.c_1 * self.path_c[row] * self.path_c[column]
                         + self.c_mu * rank_mu)
                self.covariance[row][column] = value
                self.covariance[column][row] = value
        self.step *= math.exp((self.c_sigma / self.d_sigma) * (path_sigma_norm / self.expected_norm - 1))
        # the tutorial: decompose every 1 / (c_1 + c_mu) / n / 10 generations, O(n^2) per sample on average
        if self.generation - self._decomposed_at_generation > 1 / (self.c_1 + self.c_mu) / n / 10:
            eigenvalues, self.basis = symmetric_eigendecomposition(self.covariance)
            if min(eigenvalues) <= 0:
                raise BuildError(f"CMA-ES: the covariance lost positive definiteness (eigenvalue "
                                      f"{min(eigenvalues):.3g}) at generation {self.generation}")
            self.scales = [math.sqrt(value) for value in eigenvalues]
            self._decomposed_at_generation = self.generation

    def largest_axis_step(self):
        """The step along the covariance's longest axis: how far apart the population still is."""
        return self.step * max(self.scales)

    def condition(self):
        return (max(self.scales) / min(self.scales)) ** 2


# ---------------------------------------------------------------------------------------------- a strand

@dataclass
class StrandResult:
    strand: int
    best_units: list
    best_values: dict
    best_components: dict
    curve: list                 # [[evaluations so far, best score so far], ...] at each improvement
    restarts: int
    global_best_score: float    # before refinement
    seconds: float


class CandidateObjective:
    """Scores unit-cube points of one voice against one target, keeping the best and the improvement curve."""

    def __init__(self, voice, target):
        self.voice = voice
        self.target = target
        self.evaluations = 0
        self.best_score = math.inf
        self.best_units = None
        self.best_components = None
        self.curve = []

    def __call__(self, unbounded_point):
        units = [fold_onto_unit_interval(value) for value in unbounded_point]
        values = self.voice.values_of_units(units)
        samples = self.voice.render(values, self.target.candidate_length, self.target.rate)
        components = self.target.components(samples, description=f"voice '{self.voice.name}' at {values}")
        self.evaluations += 1
        score = components.score
        if score < self.best_score:
            self.best_score = score
            self.best_units = units
            self.best_components = components
            self.curve.append([self.evaluations, score])
        return score


def _say(settings, message):
    if settings.progress:
        print(message, file=sys.stderr, flush=True)


# an enum whose first this many other choices all score exactly the held choice's score is silent in this setting
# (the metal source's pattern while white noise plays): its other choices are not rendered
INACTIVE_ENUM_PROBES = 4


def discrete_sweep(objective, voice, units, discrete_indices, budget, passes):
    """Each enum in turn tried at every one of its choices, the others held; the best kept. Repeated until a pass
    changes nothing, `passes` are done, or the next enum's choices would pass the budget. An enum found inactive
    (INACTIVE_ENUM_PROBES choices scoring exactly the held one) is left. Returns the best units."""
    best_units = list(units)
    best_score = objective(best_units)
    for _ in range(passes):
        changed = False
        for index in discrete_indices:
            parameter = voice.parameters[index]
            held_value = parameter.value_of_unit(best_units[index])
            candidates = [unit for unit in discrete_units_of(parameter) if parameter.value_of_unit(unit) != held_value]
            if objective.evaluations + len(candidates) > budget:
                return best_units
            held_score, unchanged_probes = best_score, 0
            for position, unit in enumerate(candidates):
                trial = list(best_units)
                trial[index] = unit
                score = objective(trial)
                if score == held_score:
                    unchanged_probes += 1
                    if unchanged_probes == position + 1 == INACTIVE_ENUM_PROBES:
                        break
                if score < best_score:
                    best_score, best_units, changed = score, trial, True
        if not changed:
            break
    return best_units


def discrete_units_of(parameter):
    """The unit-cube points of an enum's choices (the middle of each one's share)."""
    if parameter.kind != "enum":
        raise BuildError(f"parameter '{parameter.name}' is {parameter.kind}, only an enum is swept")
    return [(index + 0.5) / len(parameter.choices) for index in range(len(parameter.choices))]


def run_continuous_search(objective, start_units, continuous_indices, step, random_source, budget, converged_step,
                          population=None, stall_improvement=None):
    """CMA-ES over the continuous and integer parameters only (the enums held at start_units' values) until its largest
    axis is under converged_step, it stalls (when stall_improvement is given) or the budget is spent. Returns the
    search object."""
    def full_units(continuous_point):
        units = list(start_units)
        for index, value in zip(continuous_indices, continuous_point):
            units[index] = value
        return units
    search = CovarianceMatrixAdaptation([start_units[index] for index in continuous_indices], step, random_source,
                                       population)
    stall_window = 10 + int(math.ceil(30 * len(continuous_indices) / search.population))
    best_by_generation = []
    while objective.evaluations + search.population <= budget:
        scores = [objective(full_units(candidate)) for candidate in search.ask()]
        search.tell(scores)
        best_by_generation.append(min([min(scores)] + best_by_generation[-1:]))
        if search.largest_axis_step() < converged_step or search.condition() > 1e14:
            break
        if (stall_improvement is not None and len(best_by_generation) > stall_window
                and best_by_generation[-stall_window - 1] - best_by_generation[-1] < stall_improvement):
            break
    return search


def run_strand(voice, target_samples, rate, settings, strand):
    """One strand: global CMA-ES over the continuous and integer parameters with IPOP restarts (each from a random
    point, its enums too); a sweep of the enums at the strand's best; refinement of the rest from it in two halves,
    a sweep after each. Picklable entry point."""
    started = time.time()
    random_source = random.Random(f"patch-match/{settings.seed}/{strand}")
    target = MatchTarget(target_samples, rate)
    objective = CandidateObjective(voice, target)
    budget = settings.evaluations_per_strand
    global_budget = budget - int(round(settings.refinement_fraction * budget))
    # an enum's choices are unordered (a filter mode, a shift register's pattern): swept, never a CMA-ES axis; an
    # integer is an ordered count and is searched with the continuous parameters, rounded by its MatchedParameter
    continuous_indices = [index for index, parameter in enumerate(voice.parameters) if parameter.kind != "enum"]
    discrete_indices = [index for index, parameter in enumerate(voice.parameters) if parameter.kind == "enum"]
    population = None
    restarts = -1
    while objective.evaluations < global_budget:
        restarts += 1
        start = [random_source.random() for _ in range(voice.dimension)]
        if not continuous_indices:
            objective(start)
            break
        search = run_continuous_search(objective, start, continuous_indices, GLOBAL_STEP, random_source,
                                       global_budget, GLOBAL_CONVERGED_STEP, population, settings.stall_improvement)
        population = search.population * 2
        if objective.evaluations + search.population > global_budget:
            break
    global_best_score = objective.best_score
    if discrete_indices:
        discrete_sweep(objective, voice, objective.best_units, discrete_indices, budget, passes=2)
    # refinement: with discrete parameters, two halves with a sweep after each (a refined continuous best can prefer
    # another switch or pattern); without, one run
    remaining = budget - objective.evaluations
    phase_ends = [objective.evaluations + remaining // 2, budget] if discrete_indices else [budget]
    for phase_end in phase_ends:
        if continuous_indices:
            run_continuous_search(objective, objective.best_units, continuous_indices, REFINEMENT_STEP, random_source,
                                  phase_end, REFINEMENT_CONVERGED_STEP)
        if discrete_indices:
            discrete_sweep(objective, voice, objective.best_units, discrete_indices, budget, passes=1)
    _say(settings, f"strand {strand}: done, best {objective.best_score:.3f} after {objective.evaluations} evaluations")
    return StrandResult(strand=strand, best_units=objective.best_units,
                        best_values=voice.values_of_units(objective.best_units),
                        best_components=objective.best_components.as_dict(), curve=objective.curve,
                        restarts=max(0, restarts), global_best_score=global_best_score,
                        seconds=time.time() - started)


# ---------------------------------------------------------------------------------------------- the match

@dataclass
class MatchResult:
    voice_name: str
    best_values: dict
    best_units: list
    best_components: dict
    strands: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def best_score(self):
        return self.best_components["score"]

    def combined_curve(self):
        """[[evaluations per strand, best score of any strand by then], ...]: the strands run side by side."""
        points = sorted({evaluations for strand in self.strands for evaluations, _ in strand.curve})
        combined = []
        for evaluations in points:
            best = min((score for strand in self.strands for done, score in strand.curve if done <= evaluations),
                       default=math.inf)
            if not combined or best < combined[-1][1]:
                combined.append([evaluations, best])
        return combined

    def as_dict(self):
        return {"voice": self.voice_name, "best_values": self.best_values, "best_units": self.best_units,
                "score": self.best_components, "seconds": self.seconds, "settings": self.settings,
                "curve": self.combined_curve(),
                "strands": [{"strand": strand.strand, "score": strand.best_components["score"],
                             "global_score": strand.global_best_score, "restarts": strand.restarts,
                             "seconds": strand.seconds, "values": strand.best_values, "curve": strand.curve}
                            for strand in self.strands]}


def match_patch(voice, target_samples, rate, settings=SearchSettings()):
    """The voice's parameters that best match `target_samples` (one channel at `rate`): every strand's result, the
    best of them first."""
    started = time.time()
    target_samples = array.array("d", target_samples)
    MatchTarget(target_samples, rate)          # a silent / too short target fails here, before any process starts
    workers = settings.worker_count()
    jobs = [(voice, target_samples, rate, settings, strand) for strand in range(settings.strands)]
    if workers == 1:
        strands = [run_strand(*job) for job in jobs]
    else:
        # spawn, not fork: the same on macOS and Linux; each worker builds or loads the C from the kit's cache
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
            strands = list(pool.map(run_strand, *zip(*jobs)))
    strands.sort(key=lambda strand: (strand.best_components["score"], strand.strand))
    best = strands[0]
    return MatchResult(voice_name=voice.name, best_values=best.best_values, best_units=best.best_units,
                       best_components=best.best_components, strands=strands,
                       settings={"strands": settings.strands, "evaluations_per_strand": settings.evaluations_per_strand,
                                 "refinement_fraction": settings.refinement_fraction, "seed": settings.seed},
                       seconds=time.time() - started)


def score_components_of(voice, values_by_name, target):
    """The score of `voice` at `values_by_name` against an analysed target."""
    samples = voice.render(values_by_name, target.candidate_length, target.rate)
    return target.components(samples, description=f"voice '{voice.name}'")


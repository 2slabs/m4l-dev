"""The one way a test times something (architecture/testing.md, "Timing tests"): the machine's load read first, CPU
time measured (never the wall clock), one run (no best-of-N, no averaging), and the load reported with the number.

    with CpuTiming("a render", clock=THREAD) as timing:
        program.run(...)
    print(timing.report())
    if not timing.judged: ...   # a test that would judge the number says NOT JUDGED instead

THREAD is the calling thread's CPU clock (`time.thread_time`): work done on this thread, a ctypes call included.
PROCESS_AND_CHILDREN is this process's CPU time plus its reaped children's (`resource.getrusage`, RUSAGE_SELF +
RUSAGE_CHILDREN), for work spread over worker processes (a ProcessPoolExecutor's workers count once the pool has shut
down and reaped them). Not `os.times()`: it truncates each of its four fields to a clock tick (1/SC_CLK_TCK, 10 ms on
Linux), so a reading can be up to 4 ticks short and a difference 40 ms off; getrusage's fields are microsecond timevals
(RESOLUTION_SECONDS below), and on Linux a reaped child's user + system is its whole CPU time (cputime_adjust keeps
their sum equal to the scheduler's runtime), the same count its own `time.process_time()` read.

CPU time is far steadier than the wall clock under load, but not immune: cores shared between hyper-threads and other
programs' cache traffic slow each instruction. So a timing is judged only when the machine had room for it: the
1-minute load before it started plus the cores the timed work uses at most the machine's cores. Otherwise its report
says NOT JUDGED, loudly, with the numbers.
"""
import os
import resource
import time
from dataclasses import dataclass, field

THREAD = "thread CPU"
PROCESS_AND_CHILDREN = "process + children CPU"


# PROCESS_AND_CHILDREN's resolution: each of a reading's four timeval fields is truncated to a microsecond
PROCESS_AND_CHILDREN_RESOLUTION_SECONDS = 1e-6


def _process_and_children_seconds():
    self_usage = resource.getrusage(resource.RUSAGE_SELF)
    children_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return self_usage.ru_utime + self_usage.ru_stime + children_usage.ru_utime + children_usage.ru_stime


_CLOCKS = {THREAD: time.thread_time, PROCESS_AND_CHILDREN: _process_and_children_seconds}


@dataclass
class CpuTiming:
    """A context manager timing its block once on `clock`, using `cores_used` cores; read `cpu_seconds`, `judged`,
    `report()` after it."""
    what: str
    clock: str = THREAD
    cores_used: int = 1
    load_before: float = field(init=False, default=float("nan"))
    cores: int = field(init=False, default=0)
    cpu_seconds: float = field(init=False, default=float("nan"))

    def __post_init__(self):
        if self.clock not in _CLOCKS:
            raise ValueError(f"{self.what}: clock {self.clock!r} is not one of {sorted(_CLOCKS)}")
        if self.cores_used < 1:
            raise ValueError(f"{self.what}: cores_used must be >= 1, not {self.cores_used}")

    def __enter__(self):
        self.load_before = os.getloadavg()[0]
        self.cores = os.cpu_count() or 1
        self._started = _CLOCKS[self.clock]()
        return self

    def __exit__(self, *exception):
        self.cpu_seconds = _CLOCKS[self.clock]() - self._started
        return False

    @property
    def judged(self):
        return self.load_before + self.cores_used <= self.cores

    def report(self):
        text = (f"{self.what}: {self.cpu_seconds:.3g} s {self.clock} time, one run; 1-minute load "
                f"{self.load_before:.2f} on {self.cores} cores before it, using {self.cores_used}")
        if not self.judged:
            text += (f" -- NOT JUDGED (ಠ_ಠ): load {self.load_before:.2f} + {self.cores_used} cores used is over the "
                     f"machine's {self.cores}")
        return text

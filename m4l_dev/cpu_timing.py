"""The one way a test times something (architecture/testing.md, "Timing tests"): the machine's load read first, CPU
time measured (never the wall clock), one run (no best-of-N, no averaging), and the load reported with the number.

    with CpuTiming("a render", clock=THREAD) as timing:
        program.run(...)
    print(timing.report())
    if not timing.judged: ...   # a test that would judge the number says NOT JUDGED instead

THREAD is the calling thread's CPU clock (`time.thread_time`): work done on this thread, a ctypes call included.
PROCESS_AND_CHILDREN is this process's CPU time plus its reaped children's (`os.times()`), for work spread over worker
processes (a ProcessPoolExecutor's workers count once the pool has shut down and reaped them).

CPU time is far steadier than the wall clock under load, but not immune: cores shared between hyper-threads and other
programs' cache traffic slow each instruction. So a timing is judged only when the machine had room for it: the
1-minute load before it started plus the cores the timed work uses at most the machine's cores. Otherwise its report
says NOT JUDGED, loudly, with the numbers.
"""
import os
import time
from dataclasses import dataclass, field

THREAD = "thread CPU"
PROCESS_AND_CHILDREN = "process + children CPU"


def _process_and_children_seconds():
    times = os.times()
    return times.user + times.system + times.children_user + times.children_system


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

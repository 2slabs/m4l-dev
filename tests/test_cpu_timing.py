"""The kit's one way to time something (twosl_dsp/cpu_timing.py, architecture/testing.md "Timing tests"): CPU time,
a child process's included on PROCESS_AND_CHILDREN, the load read first, NOT JUDGED when the machine had no room."""
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp.cpu_timing import PROCESS_AND_CHILDREN, PROCESS_AND_CHILDREN_RESOLUTION_SECONDS, THREAD, CpuTiming  # noqa: E402

BUSY_CHILD_SECONDS = 0.2
# the child spins until its own CPU clock has passed BUSY_CHILD_SECONDS, so its CPU time is at least that by
# construction, whatever the load (load stretches the wall time, not the CPU time it spins for)
BUSY_CHILD = f"import time\nwhile time.process_time() < {BUSY_CHILD_SECONDS}: pass\n"
# a PROCESS_AND_CHILDREN difference is two readings of four fields each truncated to the clock's resolution: it can
# read at most 4 resolutions short (the end reading's truncation; the start's only makes it longer)
PROCESS_AND_CHILDREN_MOST_SHORT_SECONDS = 4 * PROCESS_AND_CHILDREN_RESOLUTION_SECONDS


class CpuTimingTests(unittest.TestCase):
    def test_a_childs_cpu_time_counts_on_process_and_children(self):
        with CpuTiming("a busy child", PROCESS_AND_CHILDREN) as timing:
            subprocess.run([sys.executable, "-c", BUSY_CHILD], check=True)
        self.assertGreaterEqual(timing.cpu_seconds, BUSY_CHILD_SECONDS - PROCESS_AND_CHILDREN_MOST_SHORT_SECONDS,
                                timing.report())

    def test_a_childs_cpu_time_is_not_the_threads(self):
        with CpuTiming("waiting on a busy child", THREAD) as timing:
            subprocess.run([sys.executable, "-c", BUSY_CHILD], check=True)
        self.assertLess(timing.cpu_seconds, BUSY_CHILD_SECONDS, timing.report())

    def test_no_room_on_the_machine_is_not_judged_and_says_so(self):
        with mock.patch("os.getloadavg", return_value=(7.5, 7.0, 7.0)), mock.patch("os.cpu_count", return_value=8):
            with CpuTiming("crowded", THREAD, cores_used=1) as crowded:
                pass
            with mock.patch("os.getloadavg", return_value=(2.0, 2.0, 2.0)):
                with CpuTiming("room for six", THREAD, cores_used=6) as fits:
                    pass
        self.assertFalse(crowded.judged)
        self.assertIn("NOT JUDGED", crowded.report())
        self.assertIn("load 7.50 on 8 cores", crowded.report())
        self.assertTrue(fits.judged)
        self.assertNotIn("NOT JUDGED", fits.report())


if __name__ == "__main__":
    unittest.main()

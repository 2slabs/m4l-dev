#!/usr/bin/env python3
"""Compile scripts with Duktape (ES5.1) to catch syntax Max's [js] would refuse: twosl_dsp/es5.py's check.

  es5check.py devices/2sl-stab/*.js
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from twosl_dsp import es5  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    failures = 0
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as script_file:
            problem = es5.syntax_problem(script_file.read())
        print(f"{path}: {'ok (ES5)' if problem is None else problem}")
        failures += problem is not None
    sys.exit(1 if failures else 0)

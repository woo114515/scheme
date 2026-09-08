#!/usr/bin/env python3
"""Run the mini-Scheme acceptance tests against any interpreter.

Each tests/cases/NNN_name.scm runs in its own process with a fresh
environment; its stdout must match tests/cases/NNN_name.out exactly.

Usage:
    python3 tests/run_tests.py <interpreter-command>...
    # e.g.:
    python3 tests/run_tests.py python3 reference/minischeme.py
    python3 tests/run_tests.py python3 /path/to/student/interpreter.py
"""

import difflib
import os
import subprocess
import sys

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = sys.argv[1:]
    passed = 0
    failed = 0
    for name in sorted(os.listdir(CASES_DIR)):
        if not name.endswith(".scm"):
            continue
        case_path = os.path.join(CASES_DIR, name)
        with open(case_path[:-4] + ".out", encoding="utf-8") as fh:
            expected = fh.read()
        proc = subprocess.run(cmd + [case_path], capture_output=True, text=True)
        actual = proc.stdout
        if proc.returncode == 0 and actual == expected:
            passed += 1
            print(f"  PASS {name}")
            continue
        failed += 1
        print(f"  FAIL {name}")
        if proc.returncode != 0:
            print(f"    interpreter exited with code {proc.returncode}")
            if proc.stderr.strip():
                print(f"    stderr: {proc.stderr.strip()}")
        diff = difflib.unified_diff(
            expected.splitlines(), actual.splitlines(),
            fromfile="expected", tofile="actual", lineterm="")
        for line in diff:
            print("    " + line)
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

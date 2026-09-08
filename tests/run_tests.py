#!/usr/bin/env python3
"""Run the mini-Scheme acceptance tests against any interpreter.

Each tests/cases/NNN_name.scm runs in its own process with a fresh
environment; its stdout must match tests/cases/NNN_name.out exactly.

Usage:
    python3 tests/run_tests.py <interpreter-command>...
    python3 tests/run_tests.py --dir <cases-dir> <interpreter-command>...
    # e.g.:
    python3 tests/run_tests.py python3 reference/main.py
    python3 tests/run_tests.py --dir tests/cases_hidden python3 reference/main.py
"""

import difflib
import os
import subprocess
import sys

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")


def main():
    args = sys.argv[1:]
    cases_dir = CASES_DIR
    if args and args[0] == "--dir":
        if len(args) < 3:
            print(__doc__)
            sys.exit(2)
        cases_dir = args[1]
        args = args[2:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(2)
    cmd = args
    passed = 0
    failed = 0
    for name in sorted(os.listdir(cases_dir)):
        if not name.endswith(".scm"):
            continue
        case_path = os.path.join(cases_dir, name)
        with open(case_path[:-4] + ".out", encoding="utf-8") as fh:
            expected = fh.read()
        try:
            proc = subprocess.run(cmd + [case_path], capture_output=True,
                                  text=True, timeout=60)
        except subprocess.TimeoutExpired:
            failed += 1
            print(f"  FAIL {name}    (timed out after 60s)")
            continue
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

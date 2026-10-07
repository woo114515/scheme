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
from collections import namedtuple

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")

# kind: "pass" | "timeout" | "exit" | "mismatch"
# summary: short, content-free description (safe to file into reports)
# detail: full printable failure block (may quote expected output; keep to logs)
CaseResult = namedtuple("CaseResult", "name passed kind summary detail")


def run_cases(cases_dir, cmd, emit=print, only=None, timeout=60):
    """Run every .scm case in cases_dir against cmd; returns (results, failed)."""
    results = []
    failed = 0
    for name in sorted(os.listdir(cases_dir)):
        if not name.endswith(".scm"):
            continue
        if only is not None and only not in name:
            continue
        case_path = os.path.join(cases_dir, name)
        with open(case_path[:-4] + ".out", encoding="utf-8") as fh:
            expected = fh.read()
        try:
            proc = subprocess.run(cmd + [case_path], capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            failed += 1
            emit(f"  FAIL {name}    (timed out after {timeout}s)")
            results.append(CaseResult(name, False, "timeout",
                                      f"超时（>{timeout}s）", ""))
            continue
        actual = proc.stdout
        if proc.returncode == 0 and actual == expected:
            emit(f"  PASS {name}")
            results.append(CaseResult(name, True, "pass", "", ""))
            continue
        failed += 1
        emit(f"  FAIL {name}")
        detail = []
        kind = "mismatch"
        summary = f"输出不匹配（实际 {len(actual.splitlines())} 行）"
        if proc.returncode != 0:
            kind = "exit"
            summary = f"退出码 {proc.returncode}"
            detail.append(f"interpreter exited with code {proc.returncode}")
            if proc.stderr.strip():
                detail.append(f"stderr: {proc.stderr.strip()}")
        diff = difflib.unified_diff(
            expected.splitlines(), actual.splitlines(),
            fromfile="expected", tofile="actual", lineterm="")
        detail.extend(diff)
        for line in detail:
            emit("    " + line)
        results.append(CaseResult(name, False, kind, summary, "\n".join(detail)))
    return results, failed


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
    results, failed = run_cases(cases_dir, cmd)
    passed = len(results) - failed
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

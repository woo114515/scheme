#!/usr/bin/env python3
"""Build starter/autograder.pyz — the packaged, student-facing autograder.

Embeds tests/cases/*.scm and their expected outputs (base64-encoded) in
a zipapp. The packaged grader never prints the inputs or the expected
outputs, so students can self-check without being able to program to
the autograder. Official grading uses tests/cases_hidden/ instead (see
`make grade`), which students never receive. The pyz is committed to
the separate starter repo — rebuild and commit it after changing
tests/cases/.

Usage: python3 tools/build_autograder.py   (or `make autograder`)
"""

import base64
import os
import tempfile
import zipapp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Concatenation only — no f-strings or braces, this is embedded verbatim.
RUNNER = (
    'import base64\n'
    'import subprocess\n'
    'import sys\n'
    '\n'
    'from _cases import CASES\n'
    '\n'
    '\n'
    'def decode(data):\n'
    '    return base64.b64decode(data).decode("utf-8")\n'
    '\n'
    '\n'
    'def main():\n'
    '    argv = sys.argv[1:]\n'
    '    case_filter = None\n'
    '    rest = []\n'
    '    for a in argv:\n'
    '        if a.startswith("--case="):\n'
    '            case_filter = a.split("=", 1)[1]\n'
    '        else:\n'
    '            rest.append(a)\n'
    '    argv = rest\n'
    '    if not argv:\n'
    '        print("usage: python3 autograder.pyz <interpreter-cmd>... [--case=NNN_name]")\n'
    '        sys.exit(2)\n'
    '    names = sorted(CASES)\n'
    '    if case_filter:\n'
    '        names = [n for n in names if case_filter in n]\n'
    '    if not names:\n'
    '        print("no case matches:", case_filter)\n'
    '        sys.exit(2)\n'
    '    passed = 0\n'
    '    failed = 0\n'
    '    for name in names:\n'
    '        program, expected = (decode(d) for d in CASES[name])\n'
    '        try:\n'
    '            proc = subprocess.run(argv, input=program, capture_output=True,\n'
    '                                  text=True, timeout=60)\n'
    '        except subprocess.TimeoutExpired:\n'
    '            failed += 1\n'
    '            print("  FAIL  " + name + "    (timed out after 60s)")\n'
    '            continue\n'
    '        if proc.returncode == 0 and proc.stdout == expected:\n'
    '            passed += 1\n'
    '            print("  PASS  " + name)\n'
    '        else:\n'
    '            failed += 1\n'
    '            print("  FAIL  " + name)\n'
    '            if proc.returncode != 0:\n'
    '                print("    interpreter exited with code " + str(proc.returncode))\n'
    '                if proc.stderr.strip():\n'
    '                    print("    stderr: " + proc.stderr.strip())\n'
    '            else:\n'
    '                print("    output does not match")\n'
    '                for line in proc.stdout.splitlines():\n'
    '                    print("    got | " + line)\n'
    '    print()\n'
    '    print(str(passed) + " passed, " + str(failed) + " failed")\n'
    '    sys.exit(1 if failed else 0)\n'
    '\n'
    '\n'
    'if __name__ == "__main__":\n'
    '    main()\n'
)


def main():
    cases_dir = os.path.join(ROOT, "tests", "cases")
    cases = {}
    for name in sorted(os.listdir(cases_dir)):
        if not name.endswith(".scm"):
            continue
        base = name[:-4]
        with open(os.path.join(cases_dir, name), encoding="utf-8") as fh:
            program = fh.read()
        with open(os.path.join(cases_dir, base + ".out"), encoding="utf-8") as fh:
            expected = fh.read()
        cases[base] = (program, expected)

    with tempfile.TemporaryDirectory() as tmp:
        encoded = {
            k: (base64.b64encode(p.encode("utf-8")).decode("ascii"),
                base64.b64encode(e.encode("utf-8")).decode("ascii"))
            for k, (p, e) in cases.items()
        }
        with open(os.path.join(tmp, "_cases.py"), "w", encoding="utf-8") as fh:
            fh.write("CASES = " + repr(encoded) + "\n")
        with open(os.path.join(tmp, "__main__.py"), "w", encoding="utf-8") as fh:
            fh.write(RUNNER)
        out = os.path.join(ROOT, "starter", "autograder.pyz")
        zipapp.create_archive(tmp, out, interpreter="/usr/bin/env python3")
    print(f"built {out} with {len(cases)} case groups")


if __name__ == "__main__":
    main()

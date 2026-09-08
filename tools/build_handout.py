#!/usr/bin/env python3
"""Assemble the student handout: spec.md + starter/ + autograder.pyz.

Produces dist/minischeme-handout.zip — the only files students receive.
Never includes tests/, reference/, tools/, or rubric.md; in particular
tests/cases_hidden/ must not leak.

Requires dist/autograder.pyz: run `make handout` (which builds it
first) or `make autograder` beforehand.
"""

import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    dist = os.path.join(ROOT, "dist")
    pyz = os.path.join(dist, "autograder.pyz")
    if not os.path.exists(pyz):
        print("autograder.pyz missing — run `make autograder` first", file=sys.stderr)
        sys.exit(1)

    handout = os.path.join(dist, "handout")
    if os.path.exists(handout):
        shutil.rmtree(handout)
    os.makedirs(handout)
    shutil.copy(os.path.join(ROOT, "spec.md"), handout)
    shutil.copy(pyz, handout)
    shutil.copytree(
        os.path.join(ROOT, "starter"),
        os.path.join(handout, "starter"),
        ignore=shutil.ignore_patterns("__pycache__"),
    )

    out = os.path.join(dist, "minischeme-handout.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, dirs, files in os.walk(handout):
            dirs.sort()
            for name in sorted(files):
                path = os.path.join(base, name)
                zf.write(path, os.path.relpath(path, handout))
    print(f"built {out}")


if __name__ == "__main__":
    main()

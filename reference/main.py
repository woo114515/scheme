"""Command-line entry point (contract: spec.md §1).

Reads one or more .scm files (or stdin when given none), evaluates each
top-level expression in order in one global environment, and prints
each non-None result on its own line.
"""

import sys

from stdlib import build_env
from evaluator import evaluate
from parser import parse
from printer import to_str


def run(program, env):
    for expr in parse(program):
        result = evaluate(expr, env)
        if result is not None:
            print(to_str(result))


def main():
    sys.setrecursionlimit(20000)
    files = sys.argv[1:]
    try:
        env = build_env()
        if files:
            for path in files:
                with open(path, encoding="utf-8") as fh:
                    run(fh.read(), env)
        else:
            run(sys.stdin.read(), env)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

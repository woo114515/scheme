# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

Teaching/assessment project (as of 2026-09-08): students with no programming experience must complete a **mini-Scheme interpreter** by vibe coding (AI-assisted coding) in **~30 minutes**, to assess their vibe-coding ability. This repo is the instructor's workspace; students receive a separate git repository (see `starter/` below).

The subset students must implement is defined in `starter/spec.md` (modeled on CS61A's Scheme core, written for zero-programming-experience readers with heavy emphasis on prefix notation / evaluation order). The interpreter's target language is Scheme; the host language is fixed to Python 3 (per user, for simplicity).

Assessment dimensions (see `rubric.md`): functional correctness (hidden case set, 60), modular programming (25), code quality (15). `reference/` is a modular Python 3 reference implementation (7 single-responsibility modules: tokenizer/parser/environment/printer/stdlib/evaluator/main — instructor-facing, not shown to students). **Keep the README's suggested module decomposition and `reference/` in sync** when the subset or architecture changes.

## Project structure

- `reference/` — instructor's modular reference interpreter (Python 3). Public API per module mirrors the starter: `tokenizer.tokenize`, `parser.parse`/`sym`/`to_chain`, `environment.Env`/`Procedure`, `printer.to_str`, `stdlib.build_env`, `evaluator.evaluate`/`apply`, `main`. Must pass all acceptance tests.
- `starter/` — **a separate git repository** (own `.git`, own GitHub remote `minischeme-starter`); gitignored by this repo. This is everything students receive: `README.md` (task sheet: goals/assessed skills/Scheme intro/modularity/autograder usage, plus **completion hints** — suggested module split, evaluate/apply mutual recursion, cons chains, truthiness traps), `spec.md` (student-facing language spec), `example/` (six graduated .scm examples with inline expected-output comments; must stay consistent with the reference — verify via `python3 reference/main.py example/<file>` after changing them), and `autograder.pyz` (built artifact, committed). **No `src/` skeleton** (removed 2026-09-12): students create `src/` from scratch; the grading entry convention is `src/main.py`. Commit and push it through its own remote, not this repo.
- `tests/` — `run_tests.py` dev acceptance runner (full diffs, `--dir` option); `tests/cases/` public cases (feeds the autograder); `tests/cases_hidden/` official grading cases (**never shipped to students**).
- `tools/build_autograder.py` — builds `starter/autograder.pyz`, the only grader students receive: cases embedded base64-encoded, run via stdin, prints PASS/FAIL but **never the inputs or expected outputs** (anti-overfit). Known limits: the pyz is extractable and a determined student can pass a wrapper command to log the hidden stdin — deterrence, not security; official grading must use `cases_hidden` instructor-side.
- `rubric.md` — instructor grading standard: 60 functional (hidden set) / 25 modularity / 15 code quality, grading procedure, cheating criteria.
- When introducing a new top-level directory, document its purpose here.

## Build, test, and development commands

- `make test` — run all acceptance tests against the reference interpreter (`python3 tests/run_tests.py python3 reference/main.py`).
- `make autograder` — rebuild `starter/autograder.pyz` from `tests/cases/`; **commit it in the starter repo** after changing cases.
- `make grade CMD="<interpreter-cmd>"` — grade a submission against the hidden case set (`tests/run_tests.py --dir tests/cases_hidden`); submissions run `python3 <submission>/src/main.py`.
- `python3 tests/run_tests.py <interpreter-cmd>...` — dev runner against any interpreter (e.g. `python3 reference/main.py` or a submission). Each case runs in its own process with a fresh environment.
- Interpreter CLI contract: read one or more `.scm` files (or stdin when given no args), evaluate each top-level expression in order, print each non-`None` result on its own line. See `starter/spec.md` §2.

## Coding style & naming

- Follow the standard formatter and linter for the chosen language, and commit their configuration together with the first source files.
- Use spaces for indentation unless the formatter requires otherwise.
- Naming: `snake_case` for files and functions where idiomatic, `PascalCase` for types, `UPPER_SNAKE_CASE` for constants.
- Keep modules focused and public interfaces small. Avoid unrelated formatting changes in feature commits.

## Testing

- Acceptance cases live in `tests/cases/` as `NNN_name.scm` + `NNN_name.out`; the runner compares stdout exactly. Adding a case means adding both files (then `make autograder` and commit the pyz in the starter repo).
- Cases form a difficulty ladder (001 arithmetic → 009 higher-order functions defined inside the language itself); keep the ladder intact when adding cases.
- Cases may never require out-of-spec features (see `starter/spec.md` §10) or depend on error behavior.
- Every bug fix to the reference interpreter should include a regression test; new behavior should cover success, failure, and boundary cases.

## Commits & pull requests

- Use short imperative subjects such as `Add parser error handling`; Conventional Commit prefixes (`feat:`, `fix:`, `docs:`) are welcome when used consistently.
- Pull requests should explain motivation and approach, list verification performed, and link relevant issues. Include screenshots or terminal output for visible behavior changes. Keep each PR narrowly scoped and call out follow-up work explicitly.

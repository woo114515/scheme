# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

Teaching/assessment project (as of 2026-09-08): students with no programming experience must complete a **mini-Scheme interpreter** by vibe coding (AI-assisted coding) in **~30 minutes**, to assess their vibe-coding ability. This repo is the instructor's workspace.

The subset students must implement is defined in `spec.md` (modeled on CS61A's Scheme core, written for zero-programming-experience readers with heavy emphasis on prefix notation / evaluation order). The interpreter's target language is Scheme; the host language is fixed to Python 3 (per user, for simplicity).

Two assessment dimensions: functional correctness (12 acceptance case groups) and **modular programming**. `reference/` is a modular Python 3 reference implementation (7 single-responsibility modules: tokenizer/parser/environment/printer/stdlib/evaluator/main — instructor-facing, not shown to students). `starter/` is the skeleton students receive: the same 7-module layout with contract docstrings (the vibe-coding prompts) and stub implementations, plus `main.py` pre-written.

## Project structure

- `spec.md` — the mini-Scheme language spec, student-facing: prefix-notation primer, per-form evaluation order, cons-chain explanation, recursion intro, debugging guide, CLI/printing contracts, out-of-scope items. The single source of truth for what a passing student interpreter must do.
- `reference/` — instructor's modular reference interpreter (Python 3). Public API per module mirrors the starter: `tokenizer.tokenize`, `parser.parse`/`sym`/`to_chain`, `environment.Env`/`Procedure`, `printer.to_str`, `stdlib.build_env`, `evaluator.evaluate`/`apply`, `main`. Must pass all acceptance tests.
- `starter/` — the student skeleton: same module layout as `reference/`, bare `raise NotImplementedError` stubs **with no comments or docstrings** (deliberate: students derive requirements from `spec.md` and the tests, not in-code prompts), complete `main.py`, and `README.md` with the pipeline map and bottom-up completion order. **Keep the starter's module boundaries in sync with `reference/`** when the subset or architecture changes.
- `tests/run_tests.py` — dev acceptance runner (full diffs, `--dir` option) for the instructor; `tests/cases/*.scm` + `*.out` are the public cases.
- `tests/cases_hidden/` — official grading cases (never shipped to students); grade with `make grade CMD="<interpreter-cmd>"`.
- `tools/build_autograder.py` — builds `dist/autograder.pyz`, the only grader students receive: cases embedded base64-encoded, runs them via stdin, prints PASS/FAIL but **never the inputs or expected outputs** (anti-overfit). Known limits: the pyz is extractable and a determined student can pass a wrapper command to log the hidden stdin — treat it as deterrence, not security; official grading must use `cases_hidden` on the instructor's side.
- `tools/build_handout.py` — assembles `dist/minischeme-handout.zip` (spec.md + starter/ + autograder.pyz), the complete student distribution. Must never include `tests/`, `reference/`, `tools/`, or `rubric.md`.
- `rubric.md` — instructor grading standard: 60 functional (hidden set) / 25 modularity / 15 code quality, plus grading procedure and cheating criteria.
- When introducing a new top-level directory, document its purpose here.

## Build, test, and development commands

- `make test` — run all acceptance tests against the reference interpreter (`python3 tests/run_tests.py python3 reference/main.py`).
- `make autograder` — rebuild `dist/autograder.pyz` after changing `tests/cases/` (dist/ is gitignored; rebuild before handing out).
- `make grade CMD="<interpreter-cmd>"` — grade a submission against the hidden case set (`tests/run_tests.py --dir tests/cases_hidden`).
- `make handout` — rebuild the autograder and assemble `dist/minischeme-handout.zip` for distribution.
- `python3 tests/run_tests.py <interpreter-cmd>...` — dev runner against any interpreter (e.g. `python3 starter/main.py` or a student submission). Each case runs in its own process with a fresh environment.
- Interpreter CLI contract: read one or more `.scm` files (or stdin when given no args), evaluate each top-level expression in order, print each non-`None` result on its own line. See `spec.md` §2.

## Coding style & naming

- Follow the standard formatter and linter for the chosen language, and commit their configuration together with the first source files.
- Use spaces for indentation unless the formatter requires otherwise.
- Naming: `snake_case` for files and functions where idiomatic, `PascalCase` for types, `UPPER_SNAKE_CASE` for constants.
- Keep modules focused and public interfaces small. Avoid unrelated formatting changes in feature commits.

## Testing

- Acceptance cases live in `tests/cases/` as `NNN_name.scm` + `NNN_name.out`; the runner compares stdout exactly. Adding a case means adding both files.
- Cases form a difficulty ladder (001 arithmetic → 009 higher-order functions defined inside the language itself); keep the ladder intact when adding cases.
- Cases may never require out-of-spec features (see `spec.md` §7) or depend on error behavior.
- Every bug fix to the reference interpreter should include a regression test; new behavior should cover success, failure, and boundary cases.

## Commits & pull requests

- Use short imperative subjects such as `Add parser error handling`; Conventional Commit prefixes (`feat:`, `fix:`, `docs:`) are welcome when used consistently.
- Pull requests should explain motivation and approach, list verification performed, and link relevant issues. Include screenshots or terminal output for visible behavior changes. Keep each PR narrowly scoped and call out follow-up work explicitly.

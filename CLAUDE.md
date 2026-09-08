# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

Empty scaffold (as of 2026-09-08): no source, tests, build configuration, README, or Git history. The directory is named `scheme`, but no implementation language has been chosen yet — these conventions are deliberately language-agnostic. Do not assume a toolchain; confirm with the user before introducing one.

## Project structure

- Production code in `src/`, tests in `tests/`, non-code resources in `assets/`. Group files by feature or module, not by contributor.
- Generated output goes in a dedicated directory such as `build/` or `dist/`, excluded from version control.
- When introducing a new top-level directory, document its purpose here or in the `README.md`.

## Build, test, and development commands

No build system or package manager is configured yet. When adding code, provide reproducible commands through a single project entry point (a Makefile or language-specific manifest):

- `make build` — compile or package the project.
- `make test` — run the complete automated test suite.
- `make lint` — check formatting and static-analysis rules.
- `make run` — start the project locally, when applicable.

Update the commands here when real commands are introduced; do not require undocumented global tools.

## Coding style & naming

- Follow the standard formatter and linter for the chosen language, and commit their configuration together with the first source files.
- Use spaces for indentation unless the formatter requires otherwise.
- Naming: `snake_case` for files and functions where idiomatic, `PascalCase` for types, `UPPER_SNAKE_CASE` for constants.
- Keep modules focused and public interfaces small. Avoid unrelated formatting changes in feature commits.

## Testing

- Place tests in `tests/`, or beside source files if the selected framework conventionally supports colocated tests.
- Mirror source-module names in test names, e.g. `tests/parser_test.*`.
- Every bug fix should include a regression test; new behavior should cover success, failure, and boundary cases.
- Once a framework is selected, document the exact test invocation and any coverage threshold in this file.

## Commits & pull requests

- No Git history exists yet from which to infer conventions. Until one emerges, use short imperative subjects such as `Add parser error handling`; Conventional Commit prefixes (`feat:`, `fix:`, `docs:`) are welcome when used consistently.
- Pull requests should explain motivation and approach, list verification performed, and link relevant issues. Include screenshots or terminal output for visible behavior changes. Keep each PR narrowly scoped and call out follow-up work explicitly.

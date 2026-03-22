# Contributing

Thanks for contributing to Claudia!

## Pull requests

- **One concern per PR.** A bug fix, a feature, a refactor, a docs update — each gets its own PR. If two changes are independent, split them.
- **Base on `main`.** Don't stack branches and open all of them against `main` — only the top-level PR will have the right diff.
- **No forward references.** If your PR references files, paths, or structure introduced by another open PR, wait for that one to merge before opening the dependent one. Note the dependency in the PR description if you open it early.
- **Keep PRs small.** Easier to review, easier to merge, less likely to conflict.

## Naming

- Project name is **Claudia** — use it consistently in config files, `pyproject.toml`, scripts, and docs.
- Commit prefix format: `feat:` / `fix:` / `refactor:` / `docs:` / `build:` / `tooling:`

## Project structure

See `AGENTS.md` for the full layout, conventions, and boundaries.

## Before opening a PR

- Run tests: `uv run python -m unittest test_scoring -v`
- Check that no file exceeds 150 lines
- Check that no hex color strings are hardcoded outside `theme.py`

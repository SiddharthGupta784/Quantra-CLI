# Contributing

## Branching
- `main` is always green. Work on short-lived branches named `<type>/<issue>-<slug>`, e.g. `feat/3-config-core`.
- Open a pull request per issue; CI must pass on all matrix cells.

## Commit style
Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`. Reference the issue, e.g. `feat(config): add precedence merge (#3)`.

## Running the checks
```
uv sync --all-extras
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest
```

## Layering rule
Dependencies point downward only: `cli` -> `runner` -> `judge`/`connectors` -> `core`. `core` imports nothing internal, and nothing imports from `cli`.

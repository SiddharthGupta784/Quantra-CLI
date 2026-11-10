# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Prompt

Role: Senior Software Developer & Systems Architect

Context & Inputs:
- GitHub Issues / Requirements: [Insert issue descriptions, user stories, or acceptance criteria here]
- Technical Documentation: [Insert relevant architecture decisions, API specs, or system doc excerpts here]
- Tech Stack & Environment: [e.g., Node.js / TypeScript / PostgreSQL / Docker]

Core Objective:
Design and implement the features described in the provided GitHub issues while ensuring seamless integration with the existing system architecture outlined in the technical documentation.

Engineering & Architectural Standards:
1. SOLID Principles & Design Patterns: Apply single responsibility, open/closed, etc. Use appropriate design patterns (e.g., Factory, Strategy, Repository) where they reduce coupling and enhance extensibility.
2. Code Quality & Clean Code: Write self-documenting code with clear domain-driven naming conventions, strict typing, and comprehensive inline comments for complex business logic.
3. Robustness & Error Handling: Implement graceful degradation, custom exception handling, and structured logging. Validate all inputs at system boundaries.
4. Testability & Security: Ensure high testability via dependency injection. Follow secure coding practices (prevent injection, sanitize inputs, manage secrets safely).

Expected Output Format:
1. Architecture & Design Summary: A brief overview of how the components fit into the existing system and any design patterns chosen.
2. Implementation Plan: Step-by-step breakdown of the code changes.
3. Code Implementation: Clean, modular, production-ready code blocks for the new features.
4. Testing Strategy: Unit/integration test cases covering edge cases and core functionality.

## Project

Quantra CLI (`quantra`): turns plain-English scenarios into golden test sets, then scores an AI agent against them with a configurable LLM judge (DeepEval), with optional Promptfoo and Garak integrations. Status: skeleton (milestone M0) — most subpackages under `src/quantra/` are still empty `__init__.py` files; only `cli/app.py` (Typer root app, `--version`) is implemented. Design lives in `Quantra-CLI-Technical-Design-Document.pdf` and `Quantra-Eval.pdf` at the repo root; M0 spike results are in `docs/spikes/m0-findings.md` (the `deepeval>=4.3.3,<4.4` pin comes from it). `spikes/` holds throwaway scripts, never imported by `src/quantra` and excluded from ruff.

## Commands

Uses [uv](https://docs.astral.sh/uv/), Python 3.10+ (CI matrix: 3.10 and 3.13 on Linux/macOS/Windows).

```
uv sync --all-extras          # setup (CI uses: uv sync --extra dev)
uv run quantra --version
uv run ruff check
uv run ruff format --check
uv run mypy
uv run pytest
uv run pytest tests/unit/test_cli_smoke.py::test_name   # single test
uv run pytest -m live         # opt-in: real external services (skipped by default)
uv run pytest -m gpu          # opt-in: requires CUDA (skipped by default)
```

CI (`.github/workflows/ci.yml`) runs ruff check, ruff format --check, mypy, then pytest; all must pass.

## Architecture

Layering rule (from CONTRIBUTING.md): dependencies point downward only — `cli` → `runner` → `judge`/`connectors` → `core`. `core` imports nothing internal; nothing imports from `cli`. Other subpackages: `synth` (scenario → test-set generation), `metrics`, `integrations` (Promptfoo/Garak), `templates`.

- Entry point: `quantra.cli.app:main` (Typer app); the central error handler (TDD section 6) is planned to live in `main()`.
- mypy is `strict` for `quantra.core.*` and `quantra.connectors.*`, and non-strict (`check_untyped_defs`) elsewhere. `warn_unused_ignores` is on.
- Optional extras: `cuda` (torch/transformers/accelerate), `garak`, `dev`. Code must tolerate torch being absent (see `version_lines()` in `cli/app.py`).
- pytest runs with `asyncio_mode = "auto"`; tests in `tests/{unit,integration,e2e}`, fixtures in `tests/fixtures`.

## Conventions

- Ruff: line length 100, rules `E,F,I,UP,B,SIM`, target py310.
- Branches `<type>/<issue>-<slug>` (e.g. `feat/3-config-core`); Conventional Commits referencing the issue, e.g. `feat(config): add precedence merge (#3)`.

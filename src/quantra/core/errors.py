"""Error model (TDD sections 6 and 13).

Every expected failure derives from :class:`QuantraError` and carries the process exit code and an
optional user-facing hint. Modules raise these; only the CLI's top-level handler turns them into
output and an exit status, so no module calls ``sys.exit``.
"""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Stable process exit codes, usable as a CI gate (TDD section 6)."""

    OK = 0
    EVAL_FAILED = 1  # evaluation completed, one or more cases below threshold
    CONFIG = 2  # usage or configuration error (invalid YAML, bad flag, missing goldens)
    PREFLIGHT = 3  # agent or judge unreachable, missing credentials
    INTEGRATION = 4  # Promptfoo/Garak missing or crashed
    VULNERABILITIES = 5  # red-team scan found vulnerabilities
    INTERRUPTED = 130  # Ctrl+C; a partial report is still written


class QuantraError(Exception):
    """Base class for expected failures; carries an exit code and a hint for the user."""

    exit_code: ExitCode = ExitCode.EVAL_FAILED

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        exit_code: ExitCode | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint
        if exit_code is not None:
            self.exit_code = exit_code


class ConfigError(QuantraError):
    """Invalid YAML, flag or environment value, or an unusable config file."""

    exit_code = ExitCode.CONFIG

"""Rich rendering for configuration and errors. Presentation only; no decisions live here."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from rich.text import Text

from quantra.core.config import ConfigEntry
from quantra.core.errors import QuantraError
from quantra.core.redaction import redact

_SOURCE_STYLE = {"flag": "bold green", "env": "cyan", "file": "yellow", "default": "dim"}
_MAX_VALUE_CHARS = 120


def _show(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= _MAX_VALUE_CHARS else text[: _MAX_VALUE_CHARS - 1] + "…"


def render_config(entries: Sequence[ConfigEntry], config_path: Path | None) -> None:
    """The merged config as a table of key, value and source (flag, env, file or default)."""
    console = Console()
    table = Table(title="Resolved configuration", title_justify="left")
    table.add_column("Key", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_column("Source", no_wrap=True)
    for entry in entries:
        table.add_row(
            Text(entry.path),
            Text(_show(entry.value)),
            Text(entry.source, style=_SOURCE_STYLE[entry.source]),
        )
    console.print(table)
    console.print(Text(f"Config file: {config_path if config_path else '(none found)'}"))


def render_validation_error(exc: ValidationError) -> None:
    """One table of field path, bad value and message. Secret-looking values are redacted."""
    table = Table(title="Invalid configuration", title_justify="left", title_style="bold red")
    table.add_column("Field", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_column("Problem", overflow="fold")
    for err in exc.errors():
        loc = err["loc"]
        field = ".".join(str(part) for part in loc) or "(root)"
        value = redact(loc[-1] if loc else "", err.get("input"))
        message = err["msg"].removeprefix("Value error, ")
        table.add_row(Text(field), Text(_show(value)), Text(message))
    console = Console(stderr=True)
    console.print(table)
    console.print(
        Text("Fix these in quantra.yaml, QUANTRA_* variables or flags.", style="dim"),
    )


def render_quantra_error(exc: QuantraError) -> None:
    console = Console(stderr=True)
    console.print(Text(f"Error: {exc.message}", style="bold red"))
    if exc.hint:
        console.print(Text(f"Hint: {exc.hint}", style="dim"))

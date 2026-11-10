"""Shared fixtures. Every test starts with no QUANTRA_* variables and an empty working directory."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Stops a developer's own quantra.yaml or QUANTRA_* variables from leaking into tests."""
    for name in list(os.environ):
        if name.upper().startswith("QUANTRA_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("COLUMNS", "200")  # keep Rich tables on one line per row
    workdir = tmp_path / "work"
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    return workdir


@pytest.fixture
def write_yaml(tmp_path: Path) -> Callable[..., Path]:
    """Write ``text`` to a YAML file under tmp_path and return its path."""

    def _write(text: str, name: str = "quantra.yaml") -> Path:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        return path

    return _write

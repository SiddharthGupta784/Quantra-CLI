"""Typer root app, global options and (later) the central error handler."""

from __future__ import annotations

import importlib.metadata
import platform
import sys
from collections.abc import Sequence

import typer
from pydantic import ValidationError

from quantra.cli import run_cmd
from quantra.cli.render import render_quantra_error, render_validation_error
from quantra.core.errors import ExitCode, QuantraError

app = typer.Typer(
    name="quantra",
    help="Quantra: AI agent testing and evaluation CLI.",
    no_args_is_help=True,
    add_completion=False,
)


def _pkg_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def version_lines() -> list[str]:
    """Version report: Quantra, DeepEval, Python and (if installed) torch/CUDA."""
    from quantra import __version__

    lines = [
        f"Quantra {__version__}",
        f"DeepEval {_pkg_version('deepeval') or 'not installed'}",
        f"Python {platform.python_version()}",
    ]
    try:
        import torch  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return lines
    cuda = getattr(torch.version, "cuda", None)
    available = torch.cuda.is_available()
    lines.append(f"torch {torch.__version__} (CUDA {cuda or 'n/a'}, available: {available})")
    return lines


def _version_callback(value: bool) -> None:
    if value:
        for line in version_lines():
            typer.echo(line)
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show versions and exit.",
    ),
) -> None:
    """Quantra: AI agent testing and evaluation CLI."""


app.command("run")(run_cmd.run)


def main(argv: Sequence[str] | None = None) -> None:
    """Console-script entry point and the single place where errors become exit codes.

    ``argv`` defaults to ``sys.argv[1:]``; tests pass it explicitly.
    """
    try:
        app(args=None if argv is None else list(argv))
    except ValidationError as exc:
        render_validation_error(exc)
        sys.exit(ExitCode.CONFIG)
    except QuantraError as exc:
        render_quantra_error(exc)
        sys.exit(exc.exit_code)
    except KeyboardInterrupt:
        sys.exit(ExitCode.INTERRUPTED)

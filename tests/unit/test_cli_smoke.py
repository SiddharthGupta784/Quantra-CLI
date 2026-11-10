from typer.testing import CliRunner

from quantra import __version__
from quantra.cli.app import app


def test_version_flag_exits_zero() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"Quantra {__version__}" in result.output
    assert "Python" in result.output

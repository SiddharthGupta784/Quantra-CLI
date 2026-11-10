"""``quantra run`` stub: BRD command lines, --print-config, and the central error handler."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from quantra.cli import app as app_module
from quantra.cli.app import app, main
from quantra.core.errors import ExitCode, QuantraError

WriteYaml = Callable[..., Path]

# The BRD's override example (section 06), verbatim apart from the --print-config suffix.
BRD_COMMAND = [
    "run",
    "--endpoint",
    "http://staging.internal/api/chat",
    "--judge-model",
    "claude-3-5-sonnet",
    "--judge-provider",
    "anthropic",
    "--use-cuda",
    "false",
    "--workers",
    "8",
]


def _row(output: str, key: str) -> str:
    """The table line for config key ``key`` (rows are one line each at COLUMNS=200)."""
    lines = [line for line in output.splitlines() if f" {key} " in line]
    assert len(lines) == 1, f"expected one row for {key!r} in:\n{output}"
    return lines[0]


def _run_main(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    with pytest.raises(SystemExit) as info:
        main(argv)
    captured = capsys.readouterr()
    return int(info.value.code or 0), captured.out, captured.err


# --- BRD command (TDD section 14, must-have case 3) --------------------------------------------


def test_brd_command_parses_and_print_config_shows_flag_sources() -> None:
    result = CliRunner().invoke(app, [*BRD_COMMAND, "--print-config"])

    assert result.exit_code == 0, result.output
    for key, value in {
        "agent.endpoint": "http://staging.internal/api/chat",
        "evaluation.judge_model.model_name": "claude-3-5-sonnet",
        "evaluation.judge_model.provider": "anthropic",
        "evaluation.use_cuda": "false",
        "evaluation.max_workers": "8",
    }.items():
        row = _row(result.output, key)
        assert value in row
        assert row.rstrip("│ ").endswith("flag"), row


def test_brd_command_without_print_config_loads_settings_and_exits_zero() -> None:
    result = CliRunner().invoke(app, BRD_COMMAND)
    assert result.exit_code == 0, result.output
    assert "Configuration is valid" in result.output


def test_print_config_shows_all_four_sources(
    write_yaml: WriteYaml, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_yaml("project: from-file\nevaluation: {max_workers: 3}\n")
    monkeypatch.setenv("QUANTRA_EVALUATION__THRESHOLD", "0.9")

    result = CliRunner().invoke(
        app, ["run", "--config", str(path), "--workers", "8", "--print-config"]
    )

    assert result.exit_code == 0, result.output
    assert _row(result.output, "evaluation.max_workers").rstrip("│ ").endswith("flag")
    assert _row(result.output, "evaluation.threshold").rstrip("│ ").endswith("env")
    assert _row(result.output, "project").rstrip("│ ").endswith("file")
    assert _row(result.output, "evaluation.use_cuda").rstrip("│ ").endswith("default")
    assert str(path) in result.output.replace("\n", "")


def test_config_flag_can_come_from_the_environment(
    write_yaml: WriteYaml, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QUANTRA_CONFIG", str(write_yaml("project: via-env-config\n")))
    result = CliRunner().invoke(app, ["run", "--print-config"])
    assert result.exit_code == 0, result.output
    assert "via-env-config" in _row(result.output, "project")


@pytest.mark.parametrize("flag", ["--use-cuda", "--allow-python-metrics", "--promptfoo", "--garak"])
def test_value_style_booleans_reject_garbage_with_usage_error(flag: str) -> None:
    result = CliRunner().invoke(app, ["run", flag, "maybe"])
    assert result.exit_code == 2


def test_repeatable_flags_replace_the_yaml_list(write_yaml: WriteYaml) -> None:
    path = write_yaml("synthesizer: {source_scenarios: [from yaml]}\n")
    result = CliRunner().invoke(
        app,
        ["run", "-c", str(path), "--scenarios", "one", "--scenarios", "two", "--print-config"],
    )
    row = _row(result.output, "synthesizer.source_scenarios")
    assert '"one", "two"' in row
    assert "from yaml" not in result.output


# --- Secrets never reach the screen ------------------------------------------------------------


def test_print_config_never_prints_secret_values(write_yaml: WriteYaml) -> None:
    path = write_yaml(
        """\
agent:
  endpoint: http://x
  headers: {Authorization: "Bearer hunter2-token", X-Api-Key: hunter2-key}
"""
    )
    result = CliRunner().invoke(app, ["run", "-c", str(path), "--print-config"])

    assert result.exit_code == 0, result.output
    assert "hunter2" not in result.output
    assert "***" in _row(result.output, "agent.headers.Authorization")


def test_validation_table_never_prints_a_secret_pasted_into_yaml(
    write_yaml: WriteYaml, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_yaml("evaluation: {judge_model: {api_key: sk-live-hunter2}}\n")

    code, out, err = _run_main(["run", "-c", str(path)], capsys)

    assert code == ExitCode.CONFIG
    assert "api_key" in err
    assert "hunter2" not in out + err


# --- Central error handler: ValidationError -> table + exit 2, no traceback -------------------


@pytest.mark.parametrize(
    ("yaml_text", "needle"),
    [
        pytest.param("surprise: 1\n", "surprise", id="unknown-key"),
        pytest.param("evaluation: {max_workers: 0}\n", "evaluation.max_workers", id="workers-zero"),
        pytest.param(
            "evaluation: {judge_model: {provider: foo}}\n",
            "evaluation.judge_model.provider",
            id="bad-provider",
        ),
        pytest.param("agent: {type: webhook}\n", "agent.endpoint is required", id="no-endpoint"),
    ],
)
def test_invalid_config_exits_2_with_a_readable_table(
    write_yaml: WriteYaml, capsys: pytest.CaptureFixture[str], yaml_text: str, needle: str
) -> None:
    code, _, err = _run_main(["run", "--config", str(write_yaml(yaml_text))], capsys)

    assert code == 2
    assert "Invalid configuration" in err
    assert "Field" in err
    assert needle in err
    assert "Traceback" not in err


def test_invalid_flag_value_exits_2_with_a_table(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = _run_main(["run", "--judge-provider", "foo"], capsys)
    assert code == 2
    assert "evaluation.judge_model.provider" in err
    assert "Traceback" not in err


def test_missing_config_file_exits_2_with_error_and_hint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _, err = _run_main(["run", "--config", str(tmp_path / "nope.yaml")], capsys)
    assert code == 2
    assert "not found" in err
    assert "Hint:" in err
    assert "Traceback" not in err


def test_invalid_environment_variable_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("QUANTRA_EVALUATION__MAX_WORKERS", "lots")
    code, _, err = _run_main(["run"], capsys)
    assert code == 2
    assert "Traceback" not in err


def test_main_exit_code_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = _run_main(["run", "--print-config"], capsys)
    assert code == 0
    assert "Resolved configuration" in out


# --- Other branches of the handler -------------------------------------------------------------


def _raising_app(exc: BaseException) -> Callable[..., Any]:
    def _app(*args: Any, **kwargs: Any) -> None:
        raise exc

    return _app


def test_quantra_error_uses_its_own_exit_code_and_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    err_in = QuantraError("garak exploded", hint="Install it", exit_code=ExitCode.INTEGRATION)
    monkeypatch.setattr(app_module, "app", _raising_app(err_in))

    code, _, err = _run_main([], capsys)

    assert code == 4
    assert "garak exploded" in err
    assert "Install it" in err


def test_keyboard_interrupt_exits_130(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(app_module, "app", _raising_app(KeyboardInterrupt()))
    code, _, _ = _run_main([], capsys)
    assert code == 130

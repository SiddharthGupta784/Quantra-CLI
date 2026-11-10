"""Flag mapping and value-style booleans (TDD section 14, must-have case 2)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import typer

from quantra.cli import run_cmd
from quantra.cli.options import FLAG_PATHS, build_overrides, parse_bool
from quantra.core.config import load_settings

# --- parse_bool ---------------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["true", "True", " TRUE ", "1", "yes", "on"])
def test_parse_bool_true(text: str) -> None:
    assert parse_bool(text) is True


@pytest.mark.parametrize("text", ["false", "False", " FALSE ", "0", "no", "off"])
def test_parse_bool_false(text: str) -> None:
    assert parse_bool(text) is False


@pytest.mark.parametrize("text", ["", "maybe", "2", "tru"])
def test_parse_bool_rejects_everything_else(text: str) -> None:
    with pytest.raises(typer.BadParameter, match="expected true"):
        parse_bool(text)


# --- build_overrides ----------------------------------------------------------------------------


def test_build_overrides_includes_only_passed_values() -> None:
    assert build_overrides(endpoint=None, workers=None, scenarios=[], metric=()) == {}


def test_build_overrides_nests_by_path() -> None:
    assert build_overrides(judge_model="m", judge_provider="anthropic", workers=8) == {
        "evaluation": {
            "judge_model": {"model_name": "m", "provider": "anthropic"},
            "max_workers": 8,
        }
    }


def test_build_overrides_keeps_false_and_zero_as_real_values() -> None:
    out = build_overrides(use_cuda=False, judge_temperature=0.0)
    assert out == {"evaluation": {"use_cuda": False, "judge_model": {"temperature": 0.0}}}


def test_build_overrides_rejects_unknown_flag() -> None:
    with pytest.raises(KeyError):
        build_overrides(not_a_flag="x")


# --- Every row of the mapping table (R2) -------------------------------------------------------

# A baseline file where every flag's target has a known non-default value; each sample value then
# differs from it, so a flag that wrote to the wrong field (or to two) shows up in the diff.
BASELINE_YAML = """\
agent:
  type: webhook
  endpoint: http://baseline
  target: base.mod:fn
  timeout_seconds: 11
  model: base-model
  response_path: base.path
  session_header: X-Base
evaluation:
  judge_model: {provider: openai, model_name: base, temperature: 0.1, base_url: http://base}
  use_cuda: true
  max_workers: 2
  metrics: [base_metric]
  conversation_metrics: [base_conv]
  metric_paths: [base_dir]
  allow_python_metrics: true
  report_formats: [json]
  conversation: {max_turns: 2}
synthesizer:
  source_scenarios: [base scenario]
  num_goldens_per_scenario: 2
  output_dir: base_out
  prompt_scenarios: auto
  golden_type: single_turn
  business_context: {agent_purpose: base purpose}
integrations: {promptfoo_enabled: false, garak_enabled: false}
"""

SAMPLE_VALUES: dict[str, Any] = {
    "agent_type": "python",
    "endpoint": "http://flag",
    "python_target": "flag.mod:fn",
    "timeout": 99.0,
    "agent_model": "flag-model",
    "response_path": "flag.path",
    "session_header": "X-Flag",
    "judge_provider": "anthropic",
    "judge_model": "flag-judge",
    "judge_temperature": 0.9,
    "judge_base_url": "http://flag",
    "use_cuda": False,
    "workers": 8,
    "scenarios": ["flag scenario one", "flag scenario two"],
    "num_goldens": 9,
    "output": Path("flag_out"),
    "prompt_scenarios": "never",
    "business_context": "flag purpose",
    "golden_type": "mixed",
    "max_turns": 7,
    "metric": ["flag_metric_a", "flag_metric_b"],
    "conversation_metric": ["flag_conv"],
    "metric_path": [Path("flag_dir")],
    "allow_python_metrics": False,
    "report_format": ["html", "junit"],
    "promptfoo": True,
    "garak": True,
}


def _flatten(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{prefix}{key}."))
        else:
            flat[f"{prefix}{key}"] = value
    return flat


def test_sample_values_cover_every_flag_path() -> None:
    assert set(SAMPLE_VALUES) == set(FLAG_PATHS)


@pytest.mark.parametrize("flag", sorted(FLAG_PATHS))
def test_each_flag_changes_exactly_its_target_field(
    flag: str, write_yaml: Callable[..., Path]
) -> None:
    path = write_yaml(BASELINE_YAML)
    before = _flatten(load_settings(path, {}).model_dump(mode="json"))

    overrides = build_overrides(**{flag: SAMPLE_VALUES[flag]})
    after = _flatten(load_settings(path, overrides).model_dump(mode="json"))

    changed = {key for key in before if before[key] != after[key]}
    assert changed == {FLAG_PATHS[flag]}


def test_flag_paths_point_at_real_config_fields(write_yaml: Callable[..., Path]) -> None:
    dump = _flatten(load_settings(write_yaml(BASELINE_YAML), {}).model_dump(mode="json"))
    for flag, path in FLAG_PATHS.items():
        assert path in dump, f"{flag} -> {path} is not a field of QuantraConfig"


def test_run_command_exposes_exactly_the_mapped_flags() -> None:
    params = set(inspect.signature(run_cmd.run).parameters) - {"config", "print_config"}
    assert params == set(FLAG_PATHS)

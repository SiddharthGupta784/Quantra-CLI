"""Configuration core: schema, validators, precedence merge, provenance, env expansion."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from quantra.core.config import (
    ConfigEntry,
    QuantraConfig,
    expand_env_vars,
    explain_settings,
    load_settings,
)
from quantra.core.errors import ConfigError, ExitCode

WriteYaml = Callable[..., Path]

# The sample from the BRD (section 05), verbatim.
BRD_SAMPLE_YAML = """\
version: "1.0"
project: "customer-support-agent"
agent:
  type: "webhook" # Options: python, webhook
  endpoint: "http://localhost:8000/api/v1/chat"
  timeout_seconds: 30
evaluation:
  judge_model:
    provider: "openai" # Options: openai, anthropic, custom_local
    model_name: "gpt-4o"
    temperature: 0.0
  use_cuda: true
  max_workers: 4
synthesizer:
  source_scenarios:
    - "Test refund policy edge cases for premium users."
  num_goldens_per_scenario: 5
integrations:
  promptfoo_enabled: true
  garak_enabled: false
"""


def _entry(entries: list[ConfigEntry], path: str) -> ConfigEntry:
    return next(e for e in entries if e.path == path)


# --- Precedence (TDD section 14, must-have case 1) -------------------------------------------


def test_precedence_flag_over_env_over_yaml_over_default(
    write_yaml: WriteYaml, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = write_yaml("evaluation:\n  max_workers: 3\n", name="has_yaml.yaml")
    monkeypatch.setenv("QUANTRA_EVALUATION__MAX_WORKERS", "5")
    flag = {"evaluation": {"max_workers": 8}}

    assert load_settings(yaml_path, flag).evaluation.max_workers == 8  # flag wins
    assert load_settings(yaml_path, {}).evaluation.max_workers == 5  # flag removed: env wins
    monkeypatch.delenv("QUANTRA_EVALUATION__MAX_WORKERS")
    assert load_settings(yaml_path, {}).evaluation.max_workers == 3  # env removed: YAML wins
    assert load_settings(None, {}).evaluation.max_workers == 4  # YAML removed: default


def test_nested_keys_merge_across_sources_instead_of_replacing(
    write_yaml: WriteYaml, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_yaml(
        "evaluation:\n  judge_model:\n    temperature: 0.7\n    model_name: from-yaml\n"
    )
    monkeypatch.setenv("QUANTRA_EVALUATION__JUDGE_MODEL__PROVIDER", "anthropic")
    flag = {"evaluation": {"judge_model": {"model_name": "from-flag"}}}

    judge = load_settings(path, flag).evaluation.judge_model

    assert (judge.model_name, judge.provider, judge.temperature) == ("from-flag", "anthropic", 0.7)


def test_environment_list_values_are_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTRA_EVALUATION__METRICS", '["faithfulness", "bias"]')
    assert load_settings(None, {}).evaluation.metrics == ["faithfulness", "bias"]


def test_scenarios_flag_replaces_yaml_list_rather_than_appending(write_yaml: WriteYaml) -> None:
    path = write_yaml("synthesizer:\n  source_scenarios: [from yaml]\n")
    cfg = load_settings(path, {"synthesizer": {"source_scenarios": ["from flag"]}})
    assert cfg.synthesizer.source_scenarios == ["from flag"]


# --- Config file discovery ---------------------------------------------------------------------


def test_defaults_need_no_file() -> None:
    cfg = load_settings(None, {})
    assert cfg.agent.endpoint == "http://localhost:8000/chat"
    assert cfg.evaluation.judge_model.provider == "openai"


def test_discovers_quantra_yaml_in_working_directory(_isolated_environment: Path) -> None:
    (_isolated_environment / "quantra.yaml").write_text("project: discovered\n", encoding="utf-8")
    assert load_settings(None, {}).project == "discovered"


def test_explicit_path_beats_working_directory_file(
    _isolated_environment: Path, write_yaml: WriteYaml
) -> None:
    (_isolated_environment / "quantra.yaml").write_text("project: local\n", encoding="utf-8")
    explicit = write_yaml("project: explicit\n", name="other.yaml")
    assert load_settings(explicit, {}).project == "explicit"


def test_missing_explicit_config_is_a_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found") as info:
        load_settings(tmp_path / "nope.yaml", {})
    assert info.value.exit_code == ExitCode.CONFIG


def test_malformed_yaml_is_a_config_error(write_yaml: WriteYaml) -> None:
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_settings(write_yaml("agent: [unclosed\n"), {})


def test_non_mapping_yaml_is_a_config_error(write_yaml: WriteYaml) -> None:
    with pytest.raises(ConfigError, match="mapping"):
        load_settings(write_yaml("- just\n- a list\n"), {})


def test_empty_yaml_file_uses_defaults(write_yaml: WriteYaml) -> None:
    assert load_settings(write_yaml(""), {}).project == "quantra-project"


def test_non_json_list_in_environment_is_a_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTRA_EVALUATION__METRICS", "not json")
    with pytest.raises(ConfigError) as info:
        load_settings(None, {})
    assert info.value.exit_code == ExitCode.CONFIG
    assert info.value.hint


# --- BRD sample --------------------------------------------------------------------------------


def test_brd_sample_yaml_loads(write_yaml: WriteYaml) -> None:
    cfg = load_settings(write_yaml(BRD_SAMPLE_YAML), {})

    assert cfg.project == "customer-support-agent"
    assert cfg.agent.type == "webhook"
    assert cfg.agent.endpoint == "http://localhost:8000/api/v1/chat"
    assert cfg.evaluation.judge_model.model_name == "gpt-4o"
    assert cfg.evaluation.max_workers == 4
    assert cfg.synthesizer.source_scenarios == ["Test refund policy edge cases for premium users."]
    assert cfg.integrations.promptfoo_enabled is True
    assert cfg.integrations.garak_enabled is False


def test_schema_accepts_the_later_milestone_fields(write_yaml: WriteYaml) -> None:
    path = write_yaml(
        """\
agent:
  type: webhook
  endpoint: http://x
  model: gpt-4o-mini
  request_extra: {temperature: 0.2}
  response_path: output.text
  session_header: X-Session-Id
  cookies: false
evaluation:
  report_formats: [json, html]
  custom_metrics:
    - {name: politeness, type: geval, criteria: "Is it polite?"}
    - {name: lint, type: python, target: "pkg.mod:Lint", scope: conversation}
  conversation:
    max_turns: 3
    simulator_model: {provider: anthropic, model_name: claude-3-5-sonnet}
synthesizer:
  golden_type: mixed
  prompt_scenarios: never
  business_context: {agent_purpose: Support refunds, users: [premium]}
"""
    )
    cfg = load_settings(path, {})
    assert cfg.agent.cookies is False
    assert cfg.evaluation.custom_metrics[1].scope == "conversation"
    assert cfg.evaluation.conversation.simulator_model is not None
    assert cfg.synthesizer.business_context is not None
    assert cfg.synthesizer.business_context.users == ["premium"]


# --- Validation: every failure is a pydantic ValidationError (CLI renders it, exit 2) ----------


@pytest.mark.parametrize(
    ("yaml_text", "needle"),
    [
        pytest.param("surprise: 1\n", "surprise", id="unknown-top-level-key"),
        pytest.param("agent: {endpoint: http://x, typo: 1}\n", "typo", id="unknown-nested-key"),
        pytest.param("evaluation: {max_workers: 0}\n", "max_workers", id="max-workers-zero"),
        pytest.param("evaluation: {max_workers: 999}\n", "max_workers", id="max-workers-too-big"),
        pytest.param(
            "evaluation: {judge_model: {provider: foo}}\n", "provider", id="unknown-provider"
        ),
        pytest.param(
            "evaluation: {judge_model: {temperature: 3}}\n", "temperature", id="temperature-bound"
        ),
        pytest.param("agent: {type: webhook}\n", "agent.endpoint is required", id="webhook-no-url"),
        pytest.param("agent: {type: python}\n", "agent.target is required", id="python-no-target"),
        pytest.param("agent: {endpoint: http://x, timeout_seconds: 0}\n", "timeout", id="timeout"),
        pytest.param(
            "evaluation: {custom_metrics: [{name: m, type: geval}]}\n",
            "criteria is required",
            id="geval-without-criteria",
        ),
        pytest.param(
            "evaluation: {custom_metrics: [{name: m, type: python}]}\n",
            "target is required",
            id="python-metric-without-target",
        ),
        pytest.param(
            "evaluation: {custom_metrics: [{name: Bad-Name, type: geval, criteria: c}]}\n",
            "name",
            id="metric-name-pattern",
        ),
        pytest.param("evaluation: {threshold: 1.5}\n", "threshold", id="threshold-bound"),
        pytest.param(
            "evaluation: {conversation: {max_turns: 0}}\n", "max_turns", id="max-turns-bound"
        ),
        pytest.param("synthesizer: {num_goldens_per_scenario: 0}\n", "num_goldens", id="goldens"),
        pytest.param("synthesizer: {golden_type: odd}\n", "golden_type", id="golden-type"),
        pytest.param("synthesizer: {business_context: {users: [a]}}\n", "agent_purpose", id="ctx"),
        pytest.param("evaluation: {report_formats: [pdf]}\n", "report_formats", id="report-fmt"),
    ],
)
def test_invalid_input_raises_validation_error(
    write_yaml: WriteYaml, yaml_text: str, needle: str
) -> None:
    with pytest.raises(ValidationError) as info:
        load_settings(write_yaml(yaml_text), {})
    assert needle in str(info.value)


@pytest.mark.parametrize(
    "overrides",
    [
        {"evaluation": {"judge_model": {"provider": "foo"}}},
        {"agent": {"type": "python"}},  # python agent without a target
        {"evaluation": {"max_workers": 0}},
    ],
)
def test_invalid_flag_values_raise_validation_error(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        load_settings(None, overrides)


def test_invalid_environment_value_raises_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUANTRA_EVALUATION__MAX_WORKERS", "0")
    with pytest.raises(ValidationError):
        load_settings(None, {})


# --- Secrets are never read from YAML ----------------------------------------------------------


@pytest.mark.parametrize(
    "yaml_text",
    [
        "evaluation: {judge_model: {api_key: sk-secret}}\n",
        "evaluation: {judge_model: {openai_api_key: sk-secret}}\n",
        "agent: {endpoint: http://x, api_key: sk-secret}\n",
        "openai_api_key: sk-secret\n",
    ],
)
def test_api_key_fields_in_yaml_are_rejected(write_yaml: WriteYaml, yaml_text: str) -> None:
    with pytest.raises(ValidationError) as info:
        load_settings(write_yaml(yaml_text), {})
    assert any(err["type"] == "extra_forbidden" for err in info.value.errors())


def test_judge_api_key_comes_only_from_a_named_environment_variable(
    write_yaml: WriteYaml,
) -> None:
    cfg = load_settings(write_yaml("evaluation: {judge_model: {api_key_env: MY_KEY}}\n"), {})
    assert cfg.evaluation.judge_model.api_key_env == "MY_KEY"  # the NAME, not a key


# --- Provenance (--print-config) ---------------------------------------------------------------


def test_explain_settings_attributes_each_value_to_its_source(
    write_yaml: WriteYaml, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_yaml(
        "project: from-file\nevaluation:\n  max_workers: 3\n  judge_model: {model_name: m}\n"
    )
    monkeypatch.setenv("QUANTRA_EVALUATION__MAX_WORKERS", "5")
    monkeypatch.setenv("QUANTRA_EVALUATION__USE_CUDA", "false")
    flags = {"evaluation": {"judge_model": {"model_name": "from-flag"}}}

    entries = explain_settings(load_settings(path, flags), path, flags)

    assert _entry(entries, "evaluation.judge_model.model_name").source == "flag"
    assert _entry(entries, "evaluation.max_workers").source == "env"  # env beats the file's 3
    assert _entry(entries, "evaluation.use_cuda").source == "env"
    assert _entry(entries, "project").source == "file"
    assert _entry(entries, "evaluation.threshold").source == "default"
    assert _entry(entries, "evaluation.judge_model.model_name").value == "from-flag"
    assert _entry(entries, "evaluation.max_workers").value == 5


def test_explain_settings_covers_every_leaf_once() -> None:
    cfg = load_settings(None, {})
    entries = explain_settings(cfg, None, {})
    paths = [e.path for e in entries]
    assert len(paths) == len(set(paths))
    assert {
        "agent.endpoint",
        "evaluation.conversation.max_turns",
        "integrations.garak_enabled",
    } <= set(paths)
    assert all(e.source == "default" for e in entries)


def test_explain_settings_redacts_secret_looking_keys(write_yaml: WriteYaml) -> None:
    path = write_yaml(
        """\
agent:
  endpoint: http://x
  headers:
    Authorization: Bearer super-secret-token
    X-Api-Key: abc123
    X-Request-Source: quantra
evaluation:
  judge_model: {api_key_env: MY_SECRET_VAR}
"""
    )
    entries = explain_settings(load_settings(path, {}), path, {})
    printed = repr(entries)

    assert "super-secret-token" not in printed
    assert "abc123" not in printed
    assert "MY_SECRET_VAR" not in printed  # the key matches *key*, so it is redacted too
    assert _entry(entries, "agent.headers.Authorization").value == "***"
    assert _entry(entries, "agent.headers.X-Request-Source").value == "quantra"


# --- ${ENV_VAR} expansion ----------------------------------------------------------------------


def test_expand_env_vars_replaces_every_reference() -> None:
    env = {"TOKEN": "t0k", "TENANT": "acme"}
    assert expand_env_vars("Bearer ${TOKEN}/${TENANT}", env) == "Bearer t0k/acme"


def test_expand_env_vars_leaves_plain_text_alone() -> None:
    assert expand_env_vars("no references $HOME {here}", {}) == "no references $HOME {here}"


def test_expand_env_vars_missing_variable_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="NOPE") as info:
        expand_env_vars("Bearer ${NOPE}", {}, where="agent.headers.Authorization")
    assert "agent.headers.Authorization" in str(info.value)
    assert info.value.exit_code == ExitCode.CONFIG
    assert info.value.hint


def test_resolved_headers_expand_values_but_the_model_keeps_the_template(
    write_yaml: WriteYaml, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENT_TOKEN", "s3cret")
    cfg = load_settings(
        write_yaml(
            "agent: {endpoint: http://x, headers: {Authorization: 'Bearer ${AGENT_TOKEN}'}}"
        ),
        {},
    )

    assert cfg.agent.resolved_headers() == {"Authorization": "Bearer s3cret"}
    assert cfg.agent.headers == {"Authorization": "Bearer ${AGENT_TOKEN}"}


def test_resolved_headers_missing_variable_is_a_config_error(write_yaml: WriteYaml) -> None:
    cfg = load_settings(
        write_yaml("agent: {endpoint: http://x, headers: {Authorization: '${UNSET_VAR_XYZ}'}}"),
        {},
    )
    with pytest.raises(ConfigError, match="UNSET_VAR_XYZ"):
        cfg.agent.resolved_headers({})


def test_quantra_config_default_is_independent_per_instance() -> None:
    """Mutating one loaded config must not leak into the next (shared mutable defaults)."""
    first = QuantraConfig()
    first.evaluation.metrics.append("leaked")
    first.agent.headers["X"] = "leaked"
    second = QuantraConfig()
    assert "leaked" not in second.evaluation.metrics
    assert second.agent.headers == {}

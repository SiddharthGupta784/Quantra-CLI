"""Configuration subsystem (TDD section 5).

One Pydantic v2 model tree, :class:`QuantraConfig`, whose sources merge in the BRD's order:
CLI flags, then ``QUANTRA_*`` environment variables, then ``quantra.yaml``, then model defaults.
It is built once per command and passed down by injection; nothing else reads flags or YAML.

This module imports nothing from the rest of Quantra except ``core`` siblings, and knows nothing
about Typer: the CLI hands it a nested dict of the flags the user actually passed.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from pydantic_settings.exceptions import SettingsError

from quantra.core.errors import ConfigError
from quantra.core.redaction import redact

DEFAULT_CONFIG_NAME = "quantra.yaml"
DEFAULT_AGENT_ENDPOINT = "http://localhost:8000/chat"

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class _Strict(BaseModel):
    """Base for every sub-model: unknown keys are errors, so YAML typos fail loudly."""

    model_config = ConfigDict(extra="forbid")


class AgentConfig(_Strict):
    type: Literal["python", "webhook"] = "webhook"
    endpoint: str | None = None  # webhook
    target: str | None = None  # python: "pkg.mod:callable"
    timeout_seconds: float = Field(default=30, gt=0)
    headers: dict[str, str] = {}  # webhook; values may use ${ENV}
    model: str | None = None  # sent as "model" when set
    response_path: str = "choices.0.message.content"  # where the reply text lives
    request_extra: dict[str, Any] = {}  # merged into the body, e.g. temperature
    session_header: str | None = None  # e.g. "X-Session-Id"; one UUID per conversation
    cookies: bool = True  # replay cookies within a conversation

    @model_validator(mode="after")
    def _needs_target(self) -> AgentConfig:
        if self.type == "webhook" and not self.endpoint:
            raise ValueError("agent.endpoint is required when agent.type=webhook")
        if self.type == "python" and not self.target:
            raise ValueError("agent.target is required when agent.type=python")
        return self

    def resolved_headers(self, environ: Mapping[str, str] | None = None) -> dict[str, str]:
        """Headers with ``${ENV_VAR}`` references expanded; a missing variable is a ConfigError.

        The model keeps the unexpanded templates, so resolved secrets are never stored or printed.
        """
        return {
            name: expand_env_vars(value, environ, where=f"agent.headers.{name}")
            for name, value in self.headers.items()
        }


class JudgeModelConfig(_Strict):
    provider: Literal["openai", "anthropic", "custom_local"] = "openai"
    model_name: str = "gpt-4o"
    temperature: float = Field(default=0.0, ge=0, le=2)
    api_key_env: str | None = None  # env var NAME, never the key
    base_url: str | None = None  # e.g. http://localhost:11434
    local_backend: Literal["ollama", "huggingface"] = "ollama"  # custom_local
    max_retries: int = Field(default=3, ge=0, le=10)


class CustomMetricConfig(_Strict):
    """User-defined metric (TDD section 10)."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    type: Literal["geval", "python"]
    scope: Literal["single_turn", "conversation"] = "single_turn"
    criteria: str | None = None  # geval: the rubric
    evaluation_params: list[Literal["input", "actual_output", "expected_output", "context"]] = [
        "input",
        "actual_output",
        "expected_output",
    ]
    target: str | None = None  # python: "pkg.mod:Class"
    params: dict[str, Any] = {}
    threshold: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def _complete(self) -> CustomMetricConfig:
        if self.type == "geval" and not self.criteria:
            raise ValueError("criteria is required for type=geval")
        if self.type == "python" and not self.target:
            raise ValueError("target is required for type=python")
        return self


class ConversationConfig(_Strict):
    """Multi-turn limits and user simulator."""

    max_turns: int = Field(default=6, ge=1, le=50)  # user turns per conversation
    total_timeout_seconds: float = Field(default=300, gt=0)
    stop_on_goal: bool = True
    simulator_model: JudgeModelConfig | None = None  # None = reuse the judge model


class EvaluationConfig(_Strict):
    judge_model: JudgeModelConfig = Field(default_factory=JudgeModelConfig)
    use_cuda: bool = True
    max_workers: int = Field(default=4, ge=1, le=256)
    metrics: list[str] = ["answer_relevancy", "correctness"]
    threshold: float = Field(default=0.5, ge=0, le=1)  # pass mark
    custom_metrics: list[CustomMetricConfig] = []
    metric_paths: list[Path] = []
    metric_thresholds: dict[str, float] = {}
    allow_python_metrics: bool = True
    metric_timeout_seconds: float = Field(default=120, gt=0)
    conversation: ConversationConfig = Field(default_factory=ConversationConfig)
    conversation_metrics: list[str] = ["conversation_completeness", "outcome_achieved"]
    report_formats: list[Literal["json", "junit", "html"]] = ["json", "junit", "html"]


class BusinessContext(_Strict):
    """Captured by the CLI scenario-first flow (TDD section 8)."""

    agent_purpose: str
    users: list[str] = []
    policies: list[str] = []
    guardrails: list[str] = []


class SynthesizerConfig(_Strict):
    source_scenarios: list[str] = []
    business_context: BusinessContext | None = None
    prompt_scenarios: Literal["auto", "always", "never"] = "auto"
    num_goldens_per_scenario: int = Field(default=5, ge=1, le=100)
    golden_type: Literal["single_turn", "multi_turn", "mixed"] = "single_turn"
    output_dir: Path = Path("./goldens")  # target of --output


class IntegrationsConfig(_Strict):
    promptfoo_enabled: bool = False
    garak_enabled: bool = False
    promptfoo_extra_endpoints: list[str] = []  # matrix: extra agents to compare
    promptfoo_version: str | None = None  # None = Quantra's tested default


class QuantraConfig(BaseSettings):
    """Root of the config tree. Secrets are never fields here: ``extra="forbid"`` rejects them."""

    model_config = SettingsConfigDict(
        env_prefix="QUANTRA_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    version: str = "1.0"
    project: str = "quantra-project"
    agent: AgentConfig = Field(default_factory=lambda: AgentConfig(endpoint=DEFAULT_AGENT_ENDPOINT))
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    synthesizer: SynthesizerConfig = Field(default_factory=SynthesizerConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Earlier = higher priority. ``init_settings`` carries the CLI overrides. Dotenv and
        # secret-file sources are deliberately dropped: the BRD defines exactly three sources.
        return (init_settings, env_settings, YamlConfigSettingsSource(settings_cls))


# ---------------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------------


def resolve_config_path(config_path: Path | None) -> Path | None:
    """The YAML file to read: the explicit one, else ``./quantra.yaml`` if present, else none.

    An explicit path that does not exist is an error; pydantic-settings alone would silently
    ignore it and run on defaults.
    """
    if config_path is not None:
        if not config_path.is_file():
            raise ConfigError(
                f"Config file not found: {config_path}",
                hint="Check --config / QUANTRA_CONFIG, or run `quantra init` to create one.",
            )
        return config_path
    default = Path(DEFAULT_CONFIG_NAME)
    return default if default.is_file() else None


def _read_yaml(path: Path) -> dict[str, Any]:
    """Parse a YAML file into a mapping, turning every failure into a ConfigError."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {path}: {exc}") from exc
    if data is None:  # empty file
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"{path} must contain a mapping at the top level, got {type(data).__name__}",
            hint="quantra.yaml is a set of `key: value` entries such as `agent:` and `project:`.",
        )
    return data


def load_settings(config_path: Path | None, overrides: Mapping[str, Any]) -> QuantraConfig:
    """Build the merged config: ``overrides`` (CLI flags) > environment > YAML > defaults.

    Raises ``pydantic.ValidationError`` for invalid values (rendered by the CLI) and
    :class:`ConfigError` for an unusable file or malformed environment value.
    """
    path = resolve_config_path(config_path)
    if path is not None:
        _read_yaml(path)  # fail early with a clean message instead of a library traceback

    class _Loaded(QuantraConfig):
        # Inherits env_prefix, nested delimiter and extra="forbid"; only the file differs.
        model_config = SettingsConfigDict(yaml_file=path, yaml_file_encoding="utf-8")

    try:
        return _Loaded(**overrides)  # sources are deep-merged, nested keys included
    except SettingsError as exc:  # e.g. a list-valued env var that is not valid JSON
        raise ConfigError(
            str(exc),
            hint='List values in QUANTRA_* variables must be JSON, e.g. \'["a", "b"]\'.',
        ) from exc


# ---------------------------------------------------------------------------------------------
# Provenance (``quantra run --print-config``)
# ---------------------------------------------------------------------------------------------

Source = Literal["flag", "env", "file", "default"]


@dataclass(frozen=True)
class ConfigEntry:
    """One leaf of the merged config, where it came from, and its (already redacted) value."""

    path: str
    value: Any
    source: Source


def _flatten(data: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Dotted-path -> leaf. Non-empty dicts recurse; lists and empty dicts are leaves."""
    flat: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            flat.update(_flatten(value, f"{path}."))
        else:
            flat[path] = value
    return flat


def _has_path(source: Mapping[str, Any], path: str) -> bool:
    node: Any = source
    for part in path.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return False
        node = node[part]
    return True


def explain_settings(
    settings: QuantraConfig,
    config_path: Path | None,
    overrides: Mapping[str, Any],
) -> list[ConfigEntry]:
    """Every leaf of ``settings`` with the highest-priority source that supplied it.

    Provenance is computed by reading each source on its own (flags, environment, YAML) and
    checking which of them contains each path, so it cannot drift from the real merge order.
    Values are redacted by key name (see :mod:`quantra.core.redaction`).
    """
    path = resolve_config_path(config_path)
    layers: list[tuple[Source, Mapping[str, Any]]] = [
        ("flag", overrides),
        ("env", EnvSettingsSource(QuantraConfig)()),
        ("file", _read_yaml(path) if path else {}),
    ]
    entries: list[ConfigEntry] = []
    for leaf, value in _flatten(settings.model_dump(mode="json")).items():
        source: Source = next((name for name, data in layers if _has_path(data, leaf)), "default")
        entries.append(ConfigEntry(leaf, redact(leaf.rsplit(".", 1)[-1], value), source))
    return entries


# ---------------------------------------------------------------------------------------------
# ${ENV_VAR} expansion
# ---------------------------------------------------------------------------------------------


def expand_env_vars(
    value: str,
    environ: Mapping[str, str] | None = None,
    *,
    where: str = "value",
) -> str:
    """Replace each ``${NAME}`` in ``value`` with ``environ[NAME]``; unset is a ConfigError."""
    env = os.environ if environ is None else environ

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in env:
            raise ConfigError(
                f"Environment variable {name} is not set (referenced by {where})",
                hint=f"Export {name} before running, or remove the reference from the config.",
            )
        return env[name]

    return _ENV_REF.sub(_sub, value)

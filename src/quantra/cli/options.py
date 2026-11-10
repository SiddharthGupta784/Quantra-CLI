"""Shared Typer options and the flag -> config-path table (TDD sections 5 and 6).

``FLAG_PATHS`` is the single table that drives both the docs and the code: ``build_overrides``
turns the flags a user actually passed into the nested dict that ``core.config.load_settings``
merges above environment and YAML.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

# ---------------------------------------------------------------------------------------------
# Value-style booleans: ``--use-cuda false`` (BRD), not Typer's ``--x/--no-x`` toggle
# ---------------------------------------------------------------------------------------------

_TRUE = {"true", "1", "yes", "on"}
_FALSE = {"false", "0", "no", "off"}


def parse_bool(value: str) -> bool:
    s = value.strip().lower()
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    raise typer.BadParameter(f"expected true|false, got {value!r}")


def BoolOpt(*names: str, **kwargs: Any) -> Any:
    """``typer.Option`` for a ``--flag true|false`` value; ``None`` means "not passed".

    Typer turns any parameter annotated ``bool`` into a ``--x/--no-x`` flag and ignores
    ``parser``, so use this inside ``Annotated[str | None, BoolOpt(...)]``: ``parse_bool`` converts
    the text and the function body receives ``bool | None`` at runtime. ``None`` is what lets the
    environment or YAML value win.
    """
    return typer.Option(*names, parser=parse_bool, metavar="[true|false]", **kwargs)


# ---------------------------------------------------------------------------------------------
# Option aliases, grouped by ``rich_help_panel``. Each name matches a FLAG_PATHS key.
# ---------------------------------------------------------------------------------------------

ConfigOpt = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        envvar="QUANTRA_CONFIG",
        help="Path to quantra.yaml (default: ./quantra.yaml if present).",
    ),
]
PrintConfigOpt = Annotated[
    bool,
    typer.Option(
        "--print-config",
        help="Print the merged configuration with the source of each value, then exit.",
    ),
]

# Agent
AgentTypeOpt = Annotated[
    str | None,
    typer.Option("--agent-type", help="python | webhook.", rich_help_panel="Agent"),
]
EndpointOpt = Annotated[
    str | None,
    typer.Option("--endpoint", help="Webhook URL of the agent.", rich_help_panel="Agent"),
]
PythonTargetOpt = Annotated[
    str | None,
    typer.Option(
        "--python-target",
        help="Python agent callable as 'pkg.mod:callable'.",
        rich_help_panel="Agent",
    ),
]
TimeoutOpt = Annotated[
    float | None,
    typer.Option("--timeout", help="Per-call agent timeout in seconds.", rich_help_panel="Agent"),
]
AgentModelOpt = Annotated[
    str | None,
    typer.Option(
        "--agent-model",
        help="Sent as 'model' in the request body when set.",
        rich_help_panel="Agent",
    ),
]
ResponsePathOpt = Annotated[
    str | None,
    typer.Option(
        "--response-path",
        help="Dotted path to the reply text, e.g. choices.0.message.content.",
        rich_help_panel="Agent",
    ),
]
SessionHeaderOpt = Annotated[
    str | None,
    typer.Option(
        "--session-header",
        metavar="NAME",
        help="Header carrying one session UUID per conversation, e.g. X-Session-Id.",
        rich_help_panel="Agent",
    ),
]

# Judge
JudgeProviderOpt = Annotated[
    str | None,
    typer.Option(
        "--judge-provider",
        help="openai | anthropic | custom_local.",
        rich_help_panel="Judge",
    ),
]
JudgeModelOpt = Annotated[
    str | None,
    typer.Option("--judge-model", help="Judge model name.", rich_help_panel="Judge"),
]
JudgeTemperatureOpt = Annotated[
    float | None,
    typer.Option(
        "--judge-temperature", help="Judge sampling temperature.", rich_help_panel="Judge"
    ),
]
JudgeBaseUrlOpt = Annotated[
    str | None,
    typer.Option(
        "--judge-base-url",
        help="Base URL for a local or proxied judge, e.g. http://localhost:11434.",
        rich_help_panel="Judge",
    ),
]

# Performance
UseCudaOpt = Annotated[
    str | None,
    BoolOpt("--use-cuda", help="Use CUDA for local-model judging.", rich_help_panel="Performance"),
]
WorkersOpt = Annotated[
    int | None,
    typer.Option("--workers", min=1, help="Parallel workers.", rich_help_panel="Performance"),
]

# Synthesizer
ScenariosOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--scenarios",
        metavar="TEXT",
        help="Scenario text (repeatable). Replaces the YAML list.",
        rich_help_panel="Synthesizer",
    ),
]
NumGoldensOpt = Annotated[
    int | None,
    typer.Option("--num-goldens", help="Goldens per scenario.", rich_help_panel="Synthesizer"),
]
OutputOpt = Annotated[
    Path | None,
    typer.Option(
        "--output", metavar="DIR", help="Golden set directory.", rich_help_panel="Synthesizer"
    ),
]
PromptScenariosOpt = Annotated[
    str | None,
    typer.Option(
        "--prompt-scenarios",
        metavar="auto|always|never",
        help="When to prompt for scenarios interactively.",
        rich_help_panel="Synthesizer",
    ),
]
BusinessContextOpt = Annotated[
    str | None,
    typer.Option(
        "--business-context",
        metavar="TEXT",
        help="What the agent is for (sets business_context.agent_purpose).",
        rich_help_panel="Synthesizer",
    ),
]
GoldenTypeOpt = Annotated[
    str | None,
    typer.Option(
        "--golden-type",
        metavar="single_turn|multi_turn|mixed",
        help="Kind of goldens to generate.",
        rich_help_panel="Synthesizer",
    ),
]

# Evaluation
MaxTurnsOpt = Annotated[
    int | None,
    typer.Option(
        "--max-turns", help="Max user turns per conversation.", rich_help_panel="Evaluation"
    ),
]
MetricOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--metric",
        metavar="NAME",
        help="Single-turn metric (repeatable). Replaces the YAML list.",
        rich_help_panel="Evaluation",
    ),
]
ConversationMetricOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--conversation-metric",
        metavar="NAME",
        help="Conversation metric (repeatable). Replaces the YAML list.",
        rich_help_panel="Evaluation",
    ),
]
MetricPathOpt = Annotated[
    list[Path] | None,
    typer.Option(
        "--metric-path",
        metavar="DIR",
        help="Directory of custom metrics (repeatable). Replaces the YAML list.",
        rich_help_panel="Evaluation",
    ),
]
AllowPythonMetricsOpt = Annotated[
    str | None,
    BoolOpt(
        "--allow-python-metrics",
        help="Allow custom Python metrics to run.",
        rich_help_panel="Evaluation",
    ),
]
ReportFormatOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--report-format",
        metavar="json|junit|html",
        help="Report format (repeatable). Replaces the YAML list.",
        rich_help_panel="Evaluation",
    ),
]

# Integrations
PromptfooOpt = Annotated[
    str | None,
    BoolOpt(
        "--promptfoo",
        help="Run Promptfoo matrix evaluation afterwards.",
        rich_help_panel="Integrations",
    ),
]
GarakOpt = Annotated[
    str | None,
    BoolOpt(
        "--garak",
        help="Run Garak vulnerability scan afterwards.",
        rich_help_panel="Integrations",
    ),
]

# ---------------------------------------------------------------------------------------------
# Flag name -> dotted path in QuantraConfig (one entry per row of the section 5 mapping table).
# ``--config`` selects the file rather than setting a value, so it is not listed.
# ---------------------------------------------------------------------------------------------

FLAG_PATHS: dict[str, str] = {
    "agent_type": "agent.type",
    "endpoint": "agent.endpoint",
    "python_target": "agent.target",
    "timeout": "agent.timeout_seconds",
    "agent_model": "agent.model",
    "response_path": "agent.response_path",
    "session_header": "agent.session_header",
    "judge_provider": "evaluation.judge_model.provider",
    "judge_model": "evaluation.judge_model.model_name",
    "judge_temperature": "evaluation.judge_model.temperature",
    "judge_base_url": "evaluation.judge_model.base_url",
    "use_cuda": "evaluation.use_cuda",
    "workers": "evaluation.max_workers",
    "scenarios": "synthesizer.source_scenarios",
    "num_goldens": "synthesizer.num_goldens_per_scenario",
    "output": "synthesizer.output_dir",
    "prompt_scenarios": "synthesizer.prompt_scenarios",
    "business_context": "synthesizer.business_context.agent_purpose",
    "golden_type": "synthesizer.golden_type",
    "max_turns": "evaluation.conversation.max_turns",
    "metric": "evaluation.metrics",
    "conversation_metric": "evaluation.conversation_metrics",
    "metric_path": "evaluation.metric_paths",
    "allow_python_metrics": "evaluation.allow_python_metrics",
    "report_format": "evaluation.report_formats",
    "promptfoo": "integrations.promptfoo_enabled",
    "garak": "integrations.garak_enabled",
}


def _not_passed(value: Any) -> bool:
    """None, or an empty repeatable option. ``False`` and ``0`` are real values."""
    return value is None or (isinstance(value, (list, tuple)) and len(value) == 0)


def build_overrides(**flags: Any) -> dict[str, Any]:
    """Nested override dict containing only the flags the user actually passed.

    Unset flags are left out entirely so they never mask the YAML or environment value.
    """
    out: dict[str, Any] = {}
    for name, value in flags.items():
        if _not_passed(value):
            continue
        *parents, leaf = FLAG_PATHS[name].split(".")
        node = out
        for part in parents:
            node = node.setdefault(part, {})
        node[leaf] = list(value) if isinstance(value, tuple) else value
    return out

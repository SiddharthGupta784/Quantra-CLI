"""``quantra run``: stub that loads settings and supports ``--print-config``.

Evaluation itself arrives in a later milestone. Registered on the root app in ``cli/app.py``
(this module must not import ``app``, or the two would import each other).
"""

from __future__ import annotations

import typer

from quantra.cli.options import (
    AgentModelOpt,
    AgentTypeOpt,
    AllowPythonMetricsOpt,
    BusinessContextOpt,
    ConfigOpt,
    ConversationMetricOpt,
    EndpointOpt,
    GarakOpt,
    GoldenTypeOpt,
    JudgeBaseUrlOpt,
    JudgeModelOpt,
    JudgeProviderOpt,
    JudgeTemperatureOpt,
    MaxTurnsOpt,
    MetricOpt,
    MetricPathOpt,
    NumGoldensOpt,
    OutputOpt,
    PrintConfigOpt,
    PromptfooOpt,
    PromptScenariosOpt,
    PythonTargetOpt,
    ReportFormatOpt,
    ResponsePathOpt,
    ScenariosOpt,
    SessionHeaderOpt,
    TimeoutOpt,
    UseCudaOpt,
    WorkersOpt,
    build_overrides,
)
from quantra.cli.render import render_config
from quantra.core.config import explain_settings, load_settings, resolve_config_path


def run(
    config: ConfigOpt = None,
    print_config: PrintConfigOpt = False,
    # Agent
    agent_type: AgentTypeOpt = None,
    endpoint: EndpointOpt = None,
    python_target: PythonTargetOpt = None,
    timeout: TimeoutOpt = None,
    agent_model: AgentModelOpt = None,
    response_path: ResponsePathOpt = None,
    session_header: SessionHeaderOpt = None,
    # Judge
    judge_provider: JudgeProviderOpt = None,
    judge_model: JudgeModelOpt = None,
    judge_temperature: JudgeTemperatureOpt = None,
    judge_base_url: JudgeBaseUrlOpt = None,
    # Performance
    use_cuda: UseCudaOpt = None,
    workers: WorkersOpt = None,
    # Synthesizer
    scenarios: ScenariosOpt = None,
    num_goldens: NumGoldensOpt = None,
    output: OutputOpt = None,
    prompt_scenarios: PromptScenariosOpt = None,
    business_context: BusinessContextOpt = None,
    golden_type: GoldenTypeOpt = None,
    # Evaluation
    max_turns: MaxTurnsOpt = None,
    metric: MetricOpt = None,
    conversation_metric: ConversationMetricOpt = None,
    metric_path: MetricPathOpt = None,
    allow_python_metrics: AllowPythonMetricsOpt = None,
    report_format: ReportFormatOpt = None,
    # Integrations
    promptfoo: PromptfooOpt = None,
    garak: GarakOpt = None,
) -> None:
    """Evaluate the agent (evaluation itself is not implemented yet; use --print-config)."""
    overrides = build_overrides(
        agent_type=agent_type,
        endpoint=endpoint,
        python_target=python_target,
        timeout=timeout,
        agent_model=agent_model,
        response_path=response_path,
        session_header=session_header,
        judge_provider=judge_provider,
        judge_model=judge_model,
        judge_temperature=judge_temperature,
        judge_base_url=judge_base_url,
        use_cuda=use_cuda,
        workers=workers,
        scenarios=scenarios,
        num_goldens=num_goldens,
        output=output,
        prompt_scenarios=prompt_scenarios,
        business_context=business_context,
        golden_type=golden_type,
        max_turns=max_turns,
        metric=metric,
        conversation_metric=conversation_metric,
        metric_path=metric_path,
        allow_python_metrics=allow_python_metrics,
        report_format=report_format,
        promptfoo=promptfoo,
        garak=garak,
    )
    settings = load_settings(config, overrides)
    if print_config:
        render_config(explain_settings(settings, config, overrides), resolve_config_path(config))
        raise typer.Exit(0)
    typer.echo("Configuration is valid. Evaluation is not implemented yet (milestone M1 stub).")

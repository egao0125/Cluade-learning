"""Evaluation runner with trace capture.

Evaluates a harness against a domain's task suite, capturing full
execution traces including every LLM call. Produces scores and traces
for the population/filesystem.
"""

from __future__ import annotations

import random
import time
import traceback
from dataclasses import dataclass, field
from typing import Any

from meta_harness.config import MetaHarnessConfig
from meta_harness.domains.base import Domain
from meta_harness.harness import HarnessInfo
from meta_harness.llm import get_call_log, reset_call_log
from meta_harness.traces import TaskTrace, format_trace_summary, save_trace


@dataclass
class EvaluationResult:
    """Complete evaluation of a harness on a task suite."""

    harness_id: str
    scores: dict[str, float]
    traces: list[TaskTrace] = field(default_factory=list)
    trace_summary: str = ""
    error: str | None = None


def evaluate_harness(
    harness: HarnessInfo,
    domain: Domain,
    config: MetaHarnessConfig,
    *,
    task_ids: list[str] | None = None,
) -> EvaluationResult:
    """Evaluate a harness on the domain's tasks.

    Args:
        harness: Loaded harness to evaluate.
        domain: Domain providing tasks and scoring.
        config: Evaluation configuration.
        task_ids: Specific task IDs to evaluate (default: sample from domain).

    Returns:
        EvaluationResult with scores, traces, and summary.
    """
    tasks = domain.get_tasks()

    # Sample if needed
    if task_ids:
        tasks = [t for t in tasks if t["id"] in set(task_ids)]
    elif len(tasks) > config.eval_sample_size:
        tasks = random.sample(tasks, config.eval_sample_size)

    traces: list[TaskTrace] = []

    for task in tasks:
        trace = _evaluate_single(harness, task, config, domain)
        traces.append(trace)

    # Compute scores
    scores = _compute_scores(traces, domain)

    summary = format_trace_summary(traces)

    return EvaluationResult(
        harness_id=harness.harness_id,
        scores=scores,
        traces=traces,
        trace_summary=summary,
    )


def _evaluate_single(
    harness: HarnessInfo,
    task: dict[str, Any],
    config: MetaHarnessConfig,
    domain: Domain,
) -> TaskTrace:
    """Evaluate one harness on one task, capturing the trace."""
    trace = TaskTrace(
        task_id=task["id"],
        harness_id=harness.harness_id,
        label=task.get("label"),
    )

    # Clear LLM call log to isolate this task
    reset_call_log()

    try:
        result = harness.run_fn(task, config.eval_model)

        if not isinstance(result, dict):
            trace.error = f"Harness returned {type(result).__name__}, expected dict"
        else:
            trace.prediction = result.get("prediction")
            trace.correct = domain.check_answer(task, trace.prediction)

    except Exception as e:
        trace.error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

    # Capture all LLM calls that happened during this task
    trace.llm_calls = reset_call_log()
    trace.finalize()

    return trace


def _compute_scores(traces: list[TaskTrace], domain: Domain) -> dict[str, float]:
    """Compute aggregate scores from traces."""
    if not traces:
        return {"accuracy": 0.0, "cost_per_task": 0.0}

    correct = sum(1 for t in traces if t.correct)
    total_cost = sum(t.total_cost_usd for t in traces)

    scores = {
        "accuracy": correct / len(traces),
        "cost_per_task": total_cost / len(traces),
    }

    # Let domain add custom scores
    extra = domain.compute_extra_scores(traces)
    scores.update(extra)

    return scores


def save_evaluation(
    result: EvaluationResult,
    config: MetaHarnessConfig,
) -> None:
    """Persist evaluation traces to the candidate directory."""
    traces_dir = config.candidates_dir() / result.harness_id / "traces"
    for trace in result.traces:
        save_trace(trace, traces_dir)

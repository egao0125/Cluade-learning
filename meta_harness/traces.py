"""Execution trace capture and formatting.

Traces are the core of the filesystem interface — the proposer reads them
to understand *how* each harness behaves on each task.  Each trace captures
the full LLM interaction chain for one (harness, task) pair.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from meta_harness.llm import LLMCallRecord


@dataclass
class TaskTrace:
    """Full execution trace for one task evaluation."""

    task_id: str
    harness_id: str
    prediction: Any = None
    label: Any = None
    correct: bool = False
    error: str | None = None
    llm_calls: list[LLMCallRecord] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_seconds: float = 0.0

    def finalize(self) -> None:
        """Compute aggregates from the recorded LLM calls."""
        self.total_input_tokens = sum(c.input_tokens for c in self.llm_calls)
        self.total_output_tokens = sum(c.output_tokens for c in self.llm_calls)
        self.total_cost_usd = sum(c.cost_usd for c in self.llm_calls)
        self.total_latency_seconds = sum(c.latency_seconds for c in self.llm_calls)


def format_trace_text(trace: TaskTrace) -> str:
    """Human-readable trace for the proposer to read."""
    lines = [
        f"=== Task {trace.task_id} | Harness {trace.harness_id} ===",
        f"Correct: {trace.correct}",
        f"Prediction: {trace.prediction}",
        f"Label: {trace.label}",
        f"LLM calls: {len(trace.llm_calls)}",
        f"Total tokens: {trace.total_input_tokens} in / {trace.total_output_tokens} out",
        f"Cost: ${trace.total_cost_usd:.6f}",
        f"Latency: {trace.total_latency_seconds:.2f}s",
    ]
    if trace.error:
        lines.append(f"ERROR: {trace.error}")

    for i, call in enumerate(trace.llm_calls):
        lines.append(f"\n--- LLM Call {i + 1} ---")
        lines.append(f"Model: {call.model}")
        if call.system:
            lines.append(f"System: {call.system[:200]}...")
        for msg in call.messages:
            role = msg.get("role", "?")
            content = str(msg.get("content", ""))
            lines.append(f"[{role}]: {content[:500]}")
        lines.append(f"[assistant]: {call.response_text[:500]}")
        lines.append(
            f"Tokens: {call.input_tokens} in / {call.output_tokens} out | "
            f"${call.cost_usd:.6f} | {call.latency_seconds:.2f}s"
        )

    return "\n".join(lines)


def save_trace(trace: TaskTrace, directory: Path) -> None:
    """Persist a trace as both .txt (for proposer) and .json (for tooling)."""
    directory.mkdir(parents=True, exist_ok=True)

    # Human-readable
    txt_path = directory / f"task_{trace.task_id}.txt"
    txt_path.write_text(format_trace_text(trace), encoding="utf-8")

    # Machine-readable
    json_path = directory / f"task_{trace.task_id}.json"
    data = asdict(trace)
    # Convert non-serializable fields
    for call in data.get("llm_calls", []):
        call.pop("timestamp", None)
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def format_trace_summary(traces: list[TaskTrace]) -> str:
    """Aggregate summary across all traces for a harness."""
    if not traces:
        return "No traces recorded."

    correct = sum(1 for t in traces if t.correct)
    errors = sum(1 for t in traces if t.error)
    total_cost = sum(t.total_cost_usd for t in traces)
    total_latency = sum(t.total_latency_seconds for t in traces)
    total_calls = sum(len(t.llm_calls) for t in traces)

    lines = [
        f"Evaluated on {len(traces)} tasks",
        f"Accuracy: {correct}/{len(traces)} ({100 * correct / len(traces):.1f}%)",
        f"Errors: {errors}/{len(traces)}",
        f"Total LLM calls: {total_calls}",
        f"Total cost: ${total_cost:.4f}",
        f"Avg cost/task: ${total_cost / len(traces):.6f}",
        f"Total latency: {total_latency:.1f}s",
        f"Avg latency/task: {total_latency / len(traces):.2f}s",
    ]

    if errors:
        error_tasks = [t.task_id for t in traces if t.error]
        lines.append(f"Error tasks: {', '.join(error_tasks[:10])}")

    # Failure analysis
    wrong = [t for t in traces if not t.correct and not t.error]
    if wrong:
        lines.append(f"\nIncorrect predictions ({len(wrong)}):")
        for t in wrong[:5]:
            lines.append(f"  Task {t.task_id}: predicted={t.prediction}, label={t.label}")
        if len(wrong) > 5:
            lines.append(f"  ... and {len(wrong) - 5} more")

    return "\n".join(lines)

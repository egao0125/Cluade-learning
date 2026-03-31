"""Workspace filesystem layout management.

This is the core of the Meta-Harness design: the proposer reads the
filesystem to understand population state, scores, traces, and failure
patterns. This module creates and maintains that filesystem.

Workspace layout:
  workspace/
  ├── OVERVIEW.md                    # Entry point for proposer
  ├── population/
  │   ├── index.json                 # All candidates indexed
  │   └── candidates/h_NNNN_name/
  │       ├── harness.py             # The actual code
  │       ├── metadata.json          # Lineage, generation, timestamps
  │       ├── scores.json            # {accuracy, cost_per_task, ...}
  │       ├── trace_summary.txt      # Aggregated stats
  │       └── traces/task_NNN.txt    # Full execution traces
  ├── diffs/                         # Parent→child diffs
  ├── frontier/pareto.json           # Current Pareto frontier
  └── logs/iteration_NNN.json        # What proposer read & proposed
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meta_harness.config import MetaHarnessConfig


def init_workspace(config: MetaHarnessConfig) -> None:
    """Create the workspace directory structure."""
    dirs = [
        config.workspace_dir,
        config.candidates_dir(),
        config.diffs_dir(),
        config.logs_dir(),
        config.frontier_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Initialize empty index
    index_path = config.workspace_dir / "population" / "index.json"
    if not index_path.exists():
        index_path.write_text(json.dumps({"candidates": {}}, indent=2))

    # Initialize OVERVIEW.md
    overview_path = config.workspace_dir / "OVERVIEW.md"
    if not overview_path.exists():
        overview_path.write_text(
            "# Meta-Harness Population Overview\n\n"
            "No candidates evaluated yet. Seeds will appear after first iteration.\n",
            encoding="utf-8",
        )


def write_candidate(
    config: MetaHarnessConfig,
    harness_id: str,
    source_code: str,
    metadata: dict[str, Any],
    scores: dict[str, float] | None = None,
    trace_summary: str = "",
) -> Path:
    """Write a candidate harness and its metadata to the workspace."""
    candidate_dir = config.candidates_dir() / harness_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # Harness code
    (candidate_dir / "harness.py").write_text(source_code, encoding="utf-8")

    # Metadata
    (candidate_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, default=str), encoding="utf-8"
    )

    # Scores
    if scores is not None:
        (candidate_dir / "scores.json").write_text(
            json.dumps(scores, indent=2), encoding="utf-8"
        )

    # Trace summary
    if trace_summary:
        (candidate_dir / "trace_summary.txt").write_text(
            trace_summary, encoding="utf-8"
        )

    # Update index
    _update_index(config, harness_id, metadata, scores)

    return candidate_dir


def _update_index(
    config: MetaHarnessConfig,
    harness_id: str,
    metadata: dict[str, Any],
    scores: dict[str, float] | None,
) -> None:
    """Update the population index.json."""
    index_path = config.workspace_dir / "population" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))

    index["candidates"][harness_id] = {
        "generation": metadata.get("generation", 0),
        "parent": metadata.get("parent"),
        "scores": scores,
        "description": metadata.get("description", ""),
    }

    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def write_diff(config: MetaHarnessConfig, child_id: str, parent_id: str, diff: str) -> None:
    """Save a parent→child diff."""
    diff_path = config.diffs_dir() / f"{parent_id}_to_{child_id}.diff"
    diff_path.write_text(diff, encoding="utf-8")


def write_iteration_log(
    config: MetaHarnessConfig,
    iteration: int,
    log_data: dict[str, Any],
) -> None:
    """Write per-iteration log."""
    log_path = config.logs_dir() / f"iteration_{iteration:03d}.json"
    log_path.write_text(json.dumps(log_data, indent=2, default=str), encoding="utf-8")


def update_overview(
    config: MetaHarnessConfig,
    population_stats: dict[str, Any],
    frontier_ids: list[str],
    iteration: int,
    failure_patterns: list[str] | None = None,
) -> None:
    """Regenerate OVERVIEW.md — the proposer's primary entry point."""
    lines = [
        "# Meta-Harness Population Overview",
        f"\nIteration: {iteration}",
        f"Population size: {population_stats.get('size', 0)}",
        f"Generations seen: {population_stats.get('max_generation', 0)}",
        "",
        "## Pareto Frontier",
    ]

    if frontier_ids:
        for fid in frontier_ids:
            candidate_dir = config.candidates_dir() / fid
            scores_path = candidate_dir / "scores.json"
            if scores_path.exists():
                scores = json.loads(scores_path.read_text())
                score_str = ", ".join(f"{k}={v:.4f}" for k, v in scores.items())
                lines.append(f"- **{fid}**: {score_str}")
            else:
                lines.append(f"- **{fid}**: (no scores)")
    else:
        lines.append("- (empty)")

    lines.append("\n## Objectives")
    for obj in config.objectives:
        direction = config.objective_directions.get(obj, "maximize")
        lines.append(f"- {obj} ({direction})")

    if failure_patterns:
        lines.append("\n## Common Failure Patterns")
        for pattern in failure_patterns:
            lines.append(f"- {pattern}")

    lines.append(
        "\n## How to Explore\n"
        "- Read `population/index.json` for all candidates\n"
        "- Each candidate dir has: harness.py, scores.json, trace_summary.txt, traces/\n"
        "- Diffs between parent→child in `diffs/`\n"
        "- Pareto frontier in `frontier/pareto.json`\n"
    )

    overview_path = config.workspace_dir / "OVERVIEW.md"
    overview_path.write_text("\n".join(lines), encoding="utf-8")

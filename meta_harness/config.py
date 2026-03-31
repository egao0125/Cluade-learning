"""Configuration for Meta-Harness evolutionary search."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MetaHarnessConfig:
    # Evolution parameters
    num_iterations: int = 20
    proposals_per_iteration: int = 3
    population_size_limit: int = 50

    # Proposer parameters (Claude Code CLI)
    proposer_model: str = "opus"
    proposer_budget_usd: float = 1.0
    proposer_allowed_tools: str = "Bash Glob Grep Read"

    # Evaluation parameters
    eval_model: str = "claude-sonnet-4-20250514"
    eval_sample_size: int = 50
    eval_timeout_seconds: int = 30

    # Objectives (for Pareto frontier)
    objectives: list[str] = field(
        default_factory=lambda: ["accuracy", "cost_per_task"]
    )
    objective_directions: dict[str, str] = field(
        default_factory=lambda: {
            "accuracy": "maximize",
            "cost_per_task": "minimize",
        }
    )

    # Paths
    workspace_dir: Path = field(default_factory=lambda: Path("workspace"))
    seeds_dir: Path = field(default_factory=lambda: Path("seeds"))
    tasks_dir: Path = field(default_factory=lambda: Path("tasks"))

    # Claude CLI
    claude_binary: str = "claude"
    skip_permissions: bool = True

    def candidates_dir(self) -> Path:
        return self.workspace_dir / "population" / "candidates"

    def diffs_dir(self) -> Path:
        return self.workspace_dir / "diffs"

    def logs_dir(self) -> Path:
        return self.workspace_dir / "logs"

    def frontier_dir(self) -> Path:
        return self.workspace_dir / "frontier"

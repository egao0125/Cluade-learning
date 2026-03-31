"""Population management and Pareto frontier computation.

Maintains the set of evaluated harness candidates and computes the
multi-objective Pareto frontier across configurable objectives.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from meta_harness.config import MetaHarnessConfig


@dataclass
class Candidate:
    """A single harness candidate in the population."""

    harness_id: str
    generation: int
    parent_id: str | None
    scores: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def dominates(self, other: Candidate, objectives: list[str], directions: dict[str, str]) -> bool:
        """True if self dominates other on all objectives."""
        dominated_any = False
        for obj in objectives:
            s_val = self.scores.get(obj, 0)
            o_val = other.scores.get(obj, 0)
            maximize = directions.get(obj, "maximize") == "maximize"

            if maximize:
                if s_val < o_val:
                    return False
                if s_val > o_val:
                    dominated_any = True
            else:
                if s_val > o_val:
                    return False
                if s_val < o_val:
                    dominated_any = True

        return dominated_any


@dataclass
class Population:
    """The full population of harness candidates."""

    candidates: dict[str, Candidate] = field(default_factory=dict)
    _next_id: int = 0

    def add(self, candidate: Candidate) -> None:
        self.candidates[candidate.harness_id] = candidate

    def generate_id(self, name: str) -> str:
        """Generate a unique harness ID."""
        hid = f"h_{self._next_id:04d}_{name}"
        self._next_id += 1
        return hid

    @property
    def size(self) -> int:
        return len(self.candidates)

    @property
    def max_generation(self) -> int:
        if not self.candidates:
            return 0
        return max(c.generation for c in self.candidates.values())

    def get_frontier(self, config: MetaHarnessConfig) -> list[Candidate]:
        """Compute Pareto frontier over configured objectives."""
        return compute_pareto_frontier(
            list(self.candidates.values()),
            config.objectives,
            config.objective_directions,
        )

    def stats(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "max_generation": self.max_generation,
            "candidate_ids": list(self.candidates.keys()),
        }

    def enforce_size_limit(self, config: MetaHarnessConfig) -> list[str]:
        """Remove dominated candidates if over the population limit.

        Returns list of removed harness IDs.
        """
        if self.size <= config.population_size_limit:
            return []

        frontier = set(c.harness_id for c in self.get_frontier(config))
        non_frontier = [
            c for c in self.candidates.values()
            if c.harness_id not in frontier
        ]
        # Remove worst non-frontier candidates (by accuracy, descending)
        non_frontier.sort(
            key=lambda c: c.scores.get("accuracy", 0),
            reverse=True,
        )

        to_remove = []
        while self.size > config.population_size_limit and non_frontier:
            worst = non_frontier.pop()
            del self.candidates[worst.harness_id]
            to_remove.append(worst.harness_id)

        return to_remove


def compute_pareto_frontier(
    candidates: list[Candidate],
    objectives: list[str],
    directions: dict[str, str],
) -> list[Candidate]:
    """Compute the Pareto-optimal set from a list of candidates."""
    if not candidates:
        return []

    frontier: list[Candidate] = []
    for candidate in candidates:
        dominated = False
        for other in candidates:
            if other.harness_id == candidate.harness_id:
                continue
            if other.dominates(candidate, objectives, directions):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)

    return frontier


def save_frontier(config: MetaHarnessConfig, frontier: list[Candidate]) -> None:
    """Persist the Pareto frontier."""
    data = {
        "frontier": [
            {
                "harness_id": c.harness_id,
                "generation": c.generation,
                "scores": c.scores,
            }
            for c in frontier
        ]
    }
    path = config.frontier_dir() / "pareto.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_population(config: MetaHarnessConfig) -> Population:
    """Load population from the workspace index."""
    index_path = config.workspace_dir / "population" / "index.json"
    if not index_path.exists():
        return Population()

    index = json.loads(index_path.read_text(encoding="utf-8"))
    pop = Population()

    for hid, info in index.get("candidates", {}).items():
        candidate = Candidate(
            harness_id=hid,
            generation=info.get("generation", 0),
            parent_id=info.get("parent"),
            scores=info.get("scores") or {},
            metadata=info,
        )
        pop.candidates[hid] = candidate

    # Set _next_id beyond existing
    if pop.candidates:
        existing_nums = []
        for hid in pop.candidates:
            parts = hid.split("_")
            if len(parts) >= 2:
                try:
                    existing_nums.append(int(parts[1]))
                except ValueError:
                    pass
        if existing_nums:
            pop._next_id = max(existing_nums) + 1

    return pop

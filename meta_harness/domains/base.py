"""Abstract domain interface for Meta-Harness evaluation.

A domain defines:
1. A set of tasks to evaluate harnesses on
2. How to check if a prediction is correct
3. Optionally, how to compute domain-specific scores
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from meta_harness.traces import TaskTrace


class Domain(ABC):
    """Base class for evaluation domains."""

    @abstractmethod
    def get_tasks(self) -> list[dict[str, Any]]:
        """Return all tasks in this domain.

        Each task is a dict with at least:
        - "id": unique task identifier
        - "input": the input text/data
        - "label": the ground truth answer
        """

    @abstractmethod
    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        """Check if a prediction is correct for the given task."""

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        """Compute domain-specific scores beyond accuracy/cost.

        Override this to add custom objectives.
        """
        return {}

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain identifier."""

    @property
    def description(self) -> str:
        """Human-readable description."""
        return ""

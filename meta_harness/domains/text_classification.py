"""Text classification domain — the working example domain.

Tasks: classify short texts into predefined categories.
Scoring: exact match on normalized labels.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meta_harness.domains.base import Domain


class TextClassificationDomain(Domain):

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks/text_classification")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "text_classification"

    @property
    def description(self) -> str:
        return "Classify short texts into predefined categories (sentiment, topic, intent)."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is not None:
            return self._tasks

        examples_path = self._tasks_dir / "examples.jsonl"
        if not examples_path.exists():
            raise FileNotFoundError(
                f"Task data not found at {examples_path}. "
                f"Run the data generation script or provide examples.jsonl."
            )

        tasks = []
        for line in examples_path.read_text(encoding="utf-8").strip().splitlines():
            if line.strip():
                tasks.append(json.loads(line))

        self._tasks = tasks
        return tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        """Case-insensitive exact match after stripping whitespace."""
        if prediction is None:
            return False

        label = str(task.get("label", "")).strip().lower()
        pred = str(prediction).strip().lower()

        return pred == label

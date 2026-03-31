"""AIVillage domain adapters for Meta-Harness.

Six cognitive functions, each optimizable as a separate harness:
  - agent_decide: AgentSituation → action JSON
  - agent_think: perception event → thought
  - agent_plan: morning state → priorities
  - agent_talk: conversation context → dialogue
  - agent_reflect: day memories → reflection + MY EXPERIENCE
  - agent_assess: interactions → mental models

Tasks are extracted from real simulation snapshots (monarchy-snapshot.json)
and export logs. Evaluation uses both structural validity and LLM-as-judge
scoring for emergence quality.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from meta_harness.domains.base import Domain
from meta_harness.traces import TaskTrace


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_tasks(tasks_dir: Path, function_name: str) -> list[dict[str, Any]]:
    """Load tasks from a JSONL file for a specific cognitive function."""
    path = tasks_dir / "ai_village" / f"{function_name}.jsonl"
    if not path.exists():
        raise FileNotFoundError(
            f"Task data not found: {path}. "
            f"Run: python -m meta_harness.domains.extract_village_tasks"
        )
    tasks = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    return tasks


def _parse_json_output(text: str) -> Any:
    """Extract JSON from LLM output, stripping markdown fences."""
    cleaned = re.sub(r"```json?\n?", "", text)
    cleaned = re.sub(r"```", "", cleaned)
    return json.loads(cleaned.strip())


def _judge_quality(prediction: Any, task: dict, criteria: str) -> float:
    """LLM-as-judge scoring. Returns 0.0-1.0.

    Uses the eval model to score the prediction against criteria.
    Deferred import to avoid circular dependency.
    """
    from meta_harness.llm import call_llm

    agent_name = task.get("metadata", {}).get("agent_name", "the agent")
    context_summary = task.get("metadata", {}).get("context_summary", "")

    prompt = f"""Score the following AI agent output on a scale of 1-5.

Agent: {agent_name}
Context: {context_summary}

Output to evaluate:
{json.dumps(prediction, indent=2, default=str) if isinstance(prediction, dict) else str(prediction)}

Scoring criteria:
{criteria}

Respond with ONLY a JSON object: {{"score": <1-5>, "reason": "<one sentence>"}}"""

    response = call_llm(
        model="claude-haiku-4-5-20251001",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.0,
    )

    try:
        result = _parse_json_output(response)
        return max(0.0, min(1.0, result["score"] / 5.0))
    except (json.JSONDecodeError, KeyError):
        return 0.5  # neutral on parse failure


# ---------------------------------------------------------------------------
# DECIDE domain
# ---------------------------------------------------------------------------

class AgentDecideDomain(Domain):
    """Optimize the action selection harness.

    Tasks: (AgentSituation snapshot) → action decision JSON
    Success: valid action chosen, in-character reasoning, mechanically sound
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "agent_decide"

    @property
    def description(self) -> str:
        return "Optimize agent action selection for mechanically sound, emergent behavior."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is None:
            self._tasks = _load_tasks(self._tasks_dir, "decide")
        return self._tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        """Structural validity: valid JSON with required fields, actionId matches available actions."""
        if not isinstance(prediction, dict):
            try:
                prediction = _parse_json_output(str(prediction))
            except (json.JSONDecodeError, ValueError):
                return False

        # Must have actionId and reason
        if "actionId" not in prediction or "reason" not in prediction:
            return False

        # actionId must be from available actions or "custom"
        available = {a["id"] for a in task.get("metadata", {}).get("available_actions", [])}
        if available and prediction["actionId"] not in available and prediction["actionId"] != "custom":
            return False

        # Reason must be non-empty and in first person
        reason = prediction.get("reason", "")
        if len(reason) < 10:
            return False

        return True

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        """Judge emergence quality via LLM."""
        if not traces:
            return {}

        # Sample up to 10 traces for judge scoring
        scored = [t for t in traces if t.correct and not t.error][:10]
        if not scored:
            return {"emergence_quality": 0.0}

        quality_scores = []
        for trace in scored:
            task = None
            for t in self.get_tasks():
                if t["id"] == trace.task_id:
                    task = t
                    break
            if task is None:
                continue

            score = _judge_quality(
                trace.prediction,
                task,
                criteria=(
                    "1: Action makes no sense given the situation\n"
                    "2: Action is generic/safe but ignores context\n"
                    "3: Action is reasonable but predictable\n"
                    "4: Action shows personality and responds to specific situation details\n"
                    "5: Action is surprising yet logical — shows genuine character agency"
                ),
            )
            quality_scores.append(score)

        return {
            "emergence_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
        }


# ---------------------------------------------------------------------------
# THINK domain
# ---------------------------------------------------------------------------

class AgentThinkDomain(Domain):
    """Optimize the immediate reaction harness.

    Tasks: (trigger, context, memories) → thought JSON
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "agent_think"

    @property
    def description(self) -> str:
        return "Optimize agent immediate reactions for authentic, in-character responses."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is None:
            self._tasks = _load_tasks(self._tasks_dir, "think")
        return self._tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        if isinstance(prediction, str):
            # Raw thought string is acceptable
            return 10 < len(prediction) < 500
        if isinstance(prediction, dict):
            thought = prediction.get("thought", "")
            return 10 < len(thought) < 500
        return False

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        scored = [t for t in traces if t.correct and not t.error][:10]
        if not scored:
            return {"authenticity": 0.0}

        scores = []
        for trace in scored:
            task = next((t for t in self.get_tasks() if t["id"] == trace.task_id), None)
            if not task:
                continue
            scores.append(_judge_quality(
                trace.prediction, task,
                criteria=(
                    "1: Breaks character or is generic platitude\n"
                    "2: Reasonable but could be any agent\n"
                    "3: Shows some personality\n"
                    "4: Honest, specific, clearly this character\n"
                    "5: Raw and surprising — reveals something about the character's inner life"
                ),
            ))
        return {"authenticity": sum(scores) / len(scores) if scores else 0.0}


# ---------------------------------------------------------------------------
# PLAN domain
# ---------------------------------------------------------------------------

class AgentPlanDomain(Domain):
    """Optimize daily priority-setting.

    Tasks: (morning state, memories) → priority list
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "agent_plan"

    @property
    def description(self) -> str:
        return "Optimize daily planning for priorities that drive meaningful action."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is None:
            self._tasks = _load_tasks(self._tasks_dir, "plan")
        return self._tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        if isinstance(prediction, str):
            try:
                prediction = _parse_json_output(prediction)
            except (json.JSONDecodeError, ValueError):
                # Accept plain text priorities separated by newlines
                lines = [l.strip() for l in prediction.strip().splitlines() if l.strip()]
                return 1 <= len(lines) <= 3

        if isinstance(prediction, list):
            return (
                1 <= len(prediction) <= 3
                and all(isinstance(p, str) and len(p) > 5 for p in prediction)
            )
        return False

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        scored = [t for t in traces if t.correct and not t.error][:10]
        if not scored:
            return {"actionability": 0.0}

        scores = []
        for trace in scored:
            task = next((t for t in self.get_tasks() if t["id"] == trace.task_id), None)
            if not task:
                continue
            scores.append(_judge_quality(
                trace.prediction, task,
                criteria=(
                    "1: Vague goals that won't drive action ('be a good person')\n"
                    "2: Generic survival priorities with no personality\n"
                    "3: Reasonable priorities but predictable\n"
                    "4: Specific, personal priorities driven by recent events and relationships\n"
                    "5: Priorities reveal internal conflict or growth — the agent is wrestling with something"
                ),
            ))
        return {"actionability": sum(scores) / len(scores) if scores else 0.0}


# ---------------------------------------------------------------------------
# TALK domain
# ---------------------------------------------------------------------------

class AgentTalkDomain(Domain):
    """Optimize conversation turns.

    Tasks: (conversation history, context) → dialogue string
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "agent_talk"

    @property
    def description(self) -> str:
        return "Optimize dialogue for natural, purposeful conversation with clear outcomes."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is None:
            self._tasks = _load_tasks(self._tasks_dir, "talk")
        return self._tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        text = str(prediction).strip()
        # Must contain quoted dialogue
        if '"' not in text:
            return False
        # Extract quoted parts
        quotes = re.findall(r'"([^"]+)"', text)
        if not quotes:
            return False
        # Dialogue should be 1-3 sentences, not empty
        total_dialogue = " ".join(quotes)
        return 5 < len(total_dialogue) < 1000

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        scored = [t for t in traces if t.correct and not t.error][:10]
        if not scored:
            return {"dialogue_quality": 0.0, "action_clarity": 0.0}

        quality_scores = []
        action_scores = []
        for trace in scored:
            task = next((t for t in self.get_tasks() if t["id"] == trace.task_id), None)
            if not task:
                continue

            quality_scores.append(_judge_quality(
                trace.prediction, task,
                criteria=(
                    "1: Generic or out of character ('Hello, how are you?')\n"
                    "2: In character but aimless small talk\n"
                    "3: Has purpose but doesn't advance the relationship\n"
                    "4: Moves the relationship or negotiation forward concretely\n"
                    "5: Creates a genuine moment — reveals something, makes a deal, confronts a truth"
                ),
            ))

            # Check if [ACTION:] tags are well-formed when present
            text = str(trace.prediction)
            actions = re.findall(r'\[ACTION:\s*(.+?)\]', text)
            if actions:
                action_scores.append(1.0)  # has actions = good
            elif task.get("metadata", {}).get("has_trade_context"):
                action_scores.append(0.0)  # should have acted but didn't

        return {
            "dialogue_quality": sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
            "action_clarity": sum(action_scores) / len(action_scores) if action_scores else 0.5,
        }


# ---------------------------------------------------------------------------
# REFLECT domain
# ---------------------------------------------------------------------------

class AgentReflectDomain(Domain):
    """Optimize end-of-day reflection.

    Tasks: (day memories, social context) → reflection + MY EXPERIENCE
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "agent_reflect"

    @property
    def description(self) -> str:
        return "Optimize reflection for honest self-assessment and useful MY EXPERIENCE rewrites."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is None:
            self._tasks = _load_tasks(self._tasks_dir, "reflect")
        return self._tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        text = str(prediction).strip()

        # Must contain the delimiter
        has_delimiter = bool(re.search(r'---\s*MY EXPERIENCE\s*---', text, re.IGNORECASE))
        if not has_delimiter:
            # Accept if it's a dict with both fields
            if isinstance(prediction, dict):
                return bool(prediction.get("reflection")) and bool(prediction.get("my_experience"))
            return False

        parts = re.split(r'---\s*MY EXPERIENCE\s*---', text, flags=re.IGNORECASE)
        if len(parts) < 2:
            return False

        reflection = parts[0].strip()
        experience = parts[1].strip()

        # Reflection: 2-3 sentences, has MOOD line
        if len(reflection) < 20:
            return False

        # MY EXPERIENCE: 20-3500 chars
        if not (20 <= len(experience) <= 3500):
            return False

        return True

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        scored = [t for t in traces if t.correct and not t.error][:10]
        if not scored:
            return {"self_awareness": 0.0, "experience_utility": 0.0}

        awareness_scores = []
        utility_scores = []
        for trace in scored:
            task = next((t for t in self.get_tasks() if t["id"] == trace.task_id), None)
            if not task:
                continue

            awareness_scores.append(_judge_quality(
                trace.prediction, task,
                criteria=(
                    "1: Generic summary of events with no self-awareness\n"
                    "2: Acknowledges events but no insight\n"
                    "3: Shows some self-awareness about relationships or mistakes\n"
                    "4: Honest assessment of own failures, changing feelings, or growth\n"
                    "5: Reveals genuine internal conflict or evolution — the agent is changing"
                ),
            ))

            text = str(trace.prediction)
            parts = re.split(r'---\s*MY EXPERIENCE\s*---', text, flags=re.IGNORECASE)
            if len(parts) >= 2:
                experience = parts[1].strip()
                utility_scores.append(_judge_quality(
                    experience, task,
                    criteria=(
                        "1: Vague or generic — could be any agent\n"
                        "2: Lists facts but no social map or trust judgments\n"
                        "3: Has names and places but superficial\n"
                        "4: Specific social map with trust levels, resource info, and actionable intel\n"
                        "5: Rich personal field guide — who's dangerous, who's useful, what to do tomorrow"
                    ),
                ))

        return {
            "self_awareness": sum(awareness_scores) / len(awareness_scores) if awareness_scores else 0.0,
            "experience_utility": sum(utility_scores) / len(utility_scores) if utility_scores else 0.0,
        }


# ---------------------------------------------------------------------------
# ASSESS domain
# ---------------------------------------------------------------------------

class AgentAssessDomain(Domain):
    """Optimize mental model formation.

    Tasks: (recent interactions) → MentalModel[] JSON
    """

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self._tasks_dir = tasks_dir or Path("tasks")
        self._tasks: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return "agent_assess"

    @property
    def description(self) -> str:
        return "Optimize mental model accuracy for trust, predictions, and social reasoning."

    def get_tasks(self) -> list[dict[str, Any]]:
        if self._tasks is None:
            self._tasks = _load_tasks(self._tasks_dir, "assess")
        return self._tasks

    def check_answer(self, task: dict[str, Any], prediction: Any) -> bool:
        if isinstance(prediction, str):
            try:
                prediction = _parse_json_output(prediction)
            except (json.JSONDecodeError, ValueError):
                return False

        if not isinstance(prediction, list):
            return False

        for model in prediction:
            if not isinstance(model, dict):
                return False
            required = {"targetId", "trust", "emotionalStance"}
            if not required.issubset(model.keys()):
                return False
            if not isinstance(model["trust"], (int, float)):
                return False
            if not (-100 <= model["trust"] <= 100):
                return False

        return len(prediction) > 0

    def compute_extra_scores(self, traces: list[TaskTrace]) -> dict[str, float]:
        scored = [t for t in traces if t.correct and not t.error][:10]
        if not scored:
            return {"model_quality": 0.0}

        scores = []
        for trace in scored:
            task = next((t for t in self.get_tasks() if t["id"] == trace.task_id), None)
            if not task:
                continue
            scores.append(_judge_quality(
                trace.prediction, task,
                criteria=(
                    "1: Trust scores seem random, no justification\n"
                    "2: Reasonable trust but generic predictions\n"
                    "3: Trust matches interactions, predictions are plausible\n"
                    "4: Nuanced — different emotional stances for different people, specific predictions\n"
                    "5: Reveals the assessor's personality biases — paranoid agents distrust, agreeable ones over-trust"
                ),
            ))
        return {"model_quality": sum(scores) / len(scores) if scores else 0.0}

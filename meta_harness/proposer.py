"""Claude Code CLI bridge — invokes the proposer agent.

The proposer is a Claude Code instance given read access to the workspace
filesystem. It reads population state, traces, and scores, then proposes
new harness implementations.

This matches the paper's approach: the proposer reads ~82 files per
iteration (code, execution traces, scores), not compressed summaries.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from meta_harness.config import MetaHarnessConfig


@dataclass
class Proposal:
    """A single proposed harness from the proposer."""

    name: str
    source_code: str
    parent_id: str | None = None
    description: str = ""
    reasoning: str = ""


@dataclass
class ProposerResult:
    """Result from a proposer invocation."""

    proposals: list[Proposal] = field(default_factory=list)
    raw_output: str = ""
    duration_seconds: float = 0.0
    error: str | None = None


def build_proposer_prompt(
    config: MetaHarnessConfig,
    iteration: int,
    num_proposals: int,
) -> str:
    """Build the prompt for the proposer agent.

    Instructs it to read the workspace and propose new harnesses.
    """
    return f"""You are a harness optimization expert. Your goal is to propose {num_proposals} new LLM harness implementation(s) that improve upon the current population.

## Your Task

1. Read `workspace/OVERVIEW.md` to understand the current population state
2. Read the Pareto frontier candidates' code, scores, and execution traces
3. Identify patterns: what works, what fails, what's expensive
4. Propose {num_proposals} new harness(es) that improve accuracy and/or reduce cost

## Harness Interface

Each harness is a Python file with:
```python
def run(task: dict, model: str) -> dict:
    \"\"\"
    Args:
        task: {{\"id\": str, \"input\": str, \"label\": str, \"metadata\": dict}}
        model: model identifier string
    Returns:
        {{\"prediction\": str}}  # The predicted category
    \"\"\"
```

Harnesses call `from meta_harness.llm import call_llm` for LLM access:
```python
call_llm(model=model, messages=[...], system=None, max_tokens=4096, temperature=0.0)
```

## Output Format

For each proposal, output a JSON block:
```json
{{
    "name": "descriptive_snake_case_name",
    "parent_id": "h_NNNN_name or null if novel",
    "description": "What this harness does differently",
    "reasoning": "Why this should improve over the parent",
    "source_code": "full Python source code"
}}
```

Wrap each JSON block in ```json ... ``` markers.

## Constraints
- Import only from `meta_harness.llm` and Python stdlib
- The `run()` function must return a dict with "prediction" key
- Aim for diversity: try different prompting strategies, not just tweaks
- Consider: structured output, self-verification, multi-step reasoning, retrieval augmentation

This is iteration {iteration}. Read the workspace to understand what's been tried.
"""


def invoke_proposer(
    config: MetaHarnessConfig,
    iteration: int,
    num_proposals: int | None = None,
) -> ProposerResult:
    """Invoke Claude Code CLI as the proposer agent.

    Uses `claude` CLI with `--add-dir` to give the proposer read access
    to the entire workspace filesystem.
    """
    if num_proposals is None:
        num_proposals = config.proposals_per_iteration

    prompt = build_proposer_prompt(config, iteration, num_proposals)

    # Write prompt to temp file for --prompt-file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    cmd = [
        config.claude_binary,
        "--print",
        "--model", config.proposer_model,
        "--add-dir", str(config.workspace_dir.resolve()),
        "--allowedTools", config.proposer_allowed_tools,
    ]

    if config.skip_permissions:
        cmd.append("--dangerously-skip-permissions")

    # Append the prompt as positional arg
    cmd.append(prompt)

    t0 = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min timeout
        )
        duration = time.time() - t0

        if result.returncode != 0:
            return ProposerResult(
                raw_output=result.stdout + result.stderr,
                duration_seconds=duration,
                error=f"CLI exited with code {result.returncode}: {result.stderr[:500]}",
            )

        proposals = _parse_proposals(result.stdout)

        return ProposerResult(
            proposals=proposals,
            raw_output=result.stdout,
            duration_seconds=duration,
        )

    except subprocess.TimeoutExpired:
        return ProposerResult(
            duration_seconds=time.time() - t0,
            error="Proposer timed out after 300 seconds",
        )
    except FileNotFoundError:
        return ProposerResult(
            error=f"Claude CLI binary not found: {config.claude_binary}",
        )
    finally:
        Path(prompt_file).unlink(missing_ok=True)


def _parse_proposals(output: str) -> list[Proposal]:
    """Extract proposal JSON blocks from the proposer's output."""
    proposals = []
    in_json_block = False
    current_block: list[str] = []

    for line in output.splitlines():
        if line.strip().startswith("```json"):
            in_json_block = True
            current_block = []
        elif line.strip() == "```" and in_json_block:
            in_json_block = False
            json_str = "\n".join(current_block)
            try:
                data = json.loads(json_str)
                proposal = Proposal(
                    name=data.get("name", f"proposal_{len(proposals)}"),
                    source_code=data.get("source_code", ""),
                    parent_id=data.get("parent_id"),
                    description=data.get("description", ""),
                    reasoning=data.get("reasoning", ""),
                )
                if proposal.source_code:
                    proposals.append(proposal)
            except json.JSONDecodeError:
                continue
        elif in_json_block:
            current_block.append(line)

    return proposals

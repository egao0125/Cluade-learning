"""Apply evolved harness back to AIVillage.

Takes the best harness from the Pareto frontier and generates:
1. A diff showing what prompt changes to make in AIVillage's index.ts
2. A standalone prompt template file for direct use
3. A report comparing the evolved harness to the baseline

Usage:
    python -m meta_harness.apply_harness \
        --workspace workspace \
        --harness-id h_0005_improved_decide \
        --village-repo /path/to/AIvillage \
        --function decide
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from meta_harness.config import MetaHarnessConfig
from meta_harness.llm import call_llm


def extract_prompt_from_harness(harness_path: Path) -> str:
    """Read a harness file and extract the prompt template logic."""
    return harness_path.read_text(encoding="utf-8")


def generate_typescript_patch(
    harness_code: str,
    function_name: str,
    village_repo: Path,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Use an LLM to translate the evolved Python harness into TypeScript changes.

    Returns a description of what to change in AIVillage's index.ts.
    """
    index_ts = village_repo / "packages" / "ai-engine" / "src" / "index.ts"
    if not index_ts.exists():
        return f"ERROR: {index_ts} not found"

    # Read the relevant section of index.ts
    source = index_ts.read_text(encoding="utf-8")

    # Find the function boundaries
    func_map = {
        "decide": ("async decide(", "async think("),
        "think": ("async think(", "async plan("),
        "plan": ("async plan(", "async talk("),
        "talk": ("async talk(", "async reflect("),
        "reflect": ("async reflect(", "async assess("),
        "assess": ("async assess(", "async compress("),
    }

    start_marker, end_marker = func_map.get(function_name, ("", ""))
    start_idx = source.find(start_marker)
    end_idx = source.find(end_marker, start_idx + 1) if end_marker else len(source)

    if start_idx == -1:
        return f"ERROR: Could not find {start_marker} in index.ts"

    current_ts = source[start_idx:end_idx]

    response = call_llm(
        model=model,
        messages=[{"role": "user", "content": f"""I have an evolved Python harness that outperforms the current TypeScript implementation.

CURRENT TypeScript ({function_name}() in index.ts):
```typescript
{current_ts[:3000]}
```

EVOLVED Python harness (better scores):
```python
{harness_code[:3000]}
```

Generate a SPECIFIC TypeScript patch for the {function_name}() method in index.ts.

Focus on:
1. What changed in the system prompt structure/content
2. What changed in the user prompt
3. Any new prompt sections or removed sections
4. Changes to output parsing

Output format:
## Summary of Changes
<2-3 sentences>

## Specific Changes
<numbered list of exact changes to make>

## TypeScript Diff
<the actual code changes in unified diff format>

Be precise — reference line numbers and exact strings to change."""}],
        max_tokens=2000,
        temperature=0.0,
    )

    return response


def generate_report(
    config: MetaHarnessConfig,
    harness_id: str,
    baseline_id: str | None = None,
) -> str:
    """Generate a comparison report between evolved and baseline harness."""
    candidate_dir = config.candidates_dir() / harness_id
    scores_path = candidate_dir / "scores.json"
    summary_path = candidate_dir / "trace_summary.txt"
    harness_path = candidate_dir / "harness.py"

    if not scores_path.exists():
        return f"No scores found for {harness_id}"

    scores = json.loads(scores_path.read_text())
    summary = summary_path.read_text() if summary_path.exists() else "No summary"
    code = harness_path.read_text() if harness_path.exists() else "No code"

    report = [
        f"# Evolved Harness Report: {harness_id}",
        "",
        "## Scores",
        *[f"  {k}: {v:.4f}" for k, v in scores.items()],
        "",
        "## Trace Summary",
        summary,
        "",
        f"## Code ({len(code)} chars)",
        f"```python",
        code[:2000],
        "```",
    ]

    # Compare to baseline if available
    if baseline_id:
        baseline_dir = config.candidates_dir() / baseline_id
        baseline_scores_path = baseline_dir / "scores.json"
        if baseline_scores_path.exists():
            baseline_scores = json.loads(baseline_scores_path.read_text())
            report.extend([
                "",
                f"## Comparison vs {baseline_id}",
            ])
            for k in scores:
                old = baseline_scores.get(k, 0)
                new = scores[k]
                delta = new - old
                direction = "+" if delta > 0 else ""
                report.append(f"  {k}: {old:.4f} → {new:.4f} ({direction}{delta:.4f})")

    return "\n".join(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply evolved harness to AIVillage")
    parser.add_argument("--workspace", default="workspace")
    parser.add_argument("--harness-id", required=True, help="ID of evolved harness")
    parser.add_argument("--baseline-id", default=None, help="ID of baseline for comparison")
    parser.add_argument("--village-repo", default=None, help="Path to AIvillage repo")
    parser.add_argument("--function", default="decide", help="Cognitive function name")
    parser.add_argument("--output", default=None, help="Output file for report")

    args = parser.parse_args()

    config = MetaHarnessConfig(workspace_dir=Path(args.workspace))

    # Generate report
    report = generate_report(config, args.harness_id, args.baseline_id)
    print(report)

    # Generate TypeScript patch if village repo provided
    if args.village_repo:
        village_repo = Path(args.village_repo)
        harness_path = config.candidates_dir() / args.harness_id / "harness.py"

        if harness_path.exists():
            print("\n" + "=" * 60)
            print("TYPESCRIPT PATCH")
            print("=" * 60)
            patch = generate_typescript_patch(
                harness_path.read_text(),
                args.function,
                village_repo,
            )
            print(patch)

    # Save report
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()

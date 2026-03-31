"""CLI entry point: python -m meta_harness [run|evaluate|frontier|propose]"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from meta_harness.config import MetaHarnessConfig


def cmd_run(args: argparse.Namespace) -> None:
    """Run the full evolutionary search."""
    from meta_harness.loop import run_evolution

    config = MetaHarnessConfig(
        num_iterations=args.iterations,
        proposals_per_iteration=args.proposals,
        eval_sample_size=args.eval_samples,
        workspace_dir=Path(args.workspace),
        seeds_dir=Path(args.seeds),
        tasks_dir=Path(args.tasks),
        proposer_model=args.model,
    )

    frontier = run_evolution(config, domain_name=args.domain)

    print(f"\nFinal Pareto frontier ({len(frontier)} candidates):")
    for c in frontier:
        score_str = ", ".join(f"{k}={v:.4f}" for k, v in c.scores.items())
        print(f"  {c.harness_id}: {score_str}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    """Evaluate a single harness."""
    from meta_harness.domains import get_domain
    from meta_harness.evaluator import evaluate_harness
    from meta_harness.harness import load_harness

    config = MetaHarnessConfig(
        eval_sample_size=args.eval_samples,
        eval_model=args.eval_model,
        tasks_dir=Path(args.tasks),
    )

    harness = load_harness(Path(args.harness))
    domain = get_domain(args.domain)

    print(f"Evaluating {harness.harness_id} on {args.domain}...")
    result = evaluate_harness(harness, domain, config)

    print(f"\nScores:")
    for k, v in result.scores.items():
        print(f"  {k}: {v:.4f}")
    print(f"\nTrace summary:\n{result.trace_summary}")


def cmd_frontier(args: argparse.Namespace) -> None:
    """Display the current Pareto frontier."""
    config = MetaHarnessConfig(workspace_dir=Path(args.workspace))
    frontier_path = config.frontier_dir() / "pareto.json"

    if not frontier_path.exists():
        print("No frontier found. Run an evolution first.")
        sys.exit(1)

    data = json.loads(frontier_path.read_text())

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        # Table format
        candidates = data.get("frontier", [])
        if not candidates:
            print("Frontier is empty.")
            return

        # Header
        all_scores = set()
        for c in candidates:
            all_scores.update(c.get("scores", {}).keys())
        score_keys = sorted(all_scores)

        header = f"{'ID':<30} {'Gen':>4}"
        for k in score_keys:
            header += f" {k:>15}"
        print(header)
        print("-" * len(header))

        for c in candidates:
            row = f"{c['harness_id']:<30} {c.get('generation', '?'):>4}"
            for k in score_keys:
                val = c.get("scores", {}).get(k, 0)
                row += f" {val:>15.4f}"
            print(row)


def cmd_propose(args: argparse.Namespace) -> None:
    """Run a single proposer invocation (for testing)."""
    from meta_harness.proposer import invoke_proposer

    config = MetaHarnessConfig(
        workspace_dir=Path(args.workspace),
        proposer_model=args.model,
        proposals_per_iteration=args.proposals,
    )

    if args.dry_run:
        from meta_harness.proposer import build_proposer_prompt

        prompt = build_proposer_prompt(config, iteration=1, num_proposals=args.proposals)
        print("=== DRY RUN: Proposer Prompt ===")
        print(prompt)
        return

    result = invoke_proposer(config, iteration=1)

    if result.error:
        print(f"Error: {result.error}")
        sys.exit(1)

    print(f"Proposer returned {len(result.proposals)} proposals in {result.duration_seconds:.1f}s")
    for p in result.proposals:
        print(f"\n--- {p.name} ---")
        print(f"Parent: {p.parent_id or 'none'}")
        print(f"Description: {p.description}")
        print(f"Source ({len(p.source_code)} chars):")
        print(p.source_code[:500])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="meta_harness",
        description="Meta-Harness: Evolutionary search over LLM harnesses",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run evolutionary search")
    p_run.add_argument("--domain", default="text_classification")
    p_run.add_argument("--iterations", type=int, default=20)
    p_run.add_argument("--proposals", type=int, default=3)
    p_run.add_argument("--eval-samples", type=int, default=50)
    p_run.add_argument("--workspace", default="workspace")
    p_run.add_argument("--seeds", default="seeds")
    p_run.add_argument("--tasks", default="tasks")
    p_run.add_argument("--model", default="opus")

    # evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate a single harness")
    p_eval.add_argument("--harness", required=True, help="Path to harness .py file")
    p_eval.add_argument("--domain", default="text_classification")
    p_eval.add_argument("--eval-samples", type=int, default=50)
    p_eval.add_argument("--eval-model", default="claude-sonnet-4-20250514")
    p_eval.add_argument("--tasks", default="tasks")

    # frontier
    p_front = sub.add_parser("frontier", help="Show Pareto frontier")
    p_front.add_argument("--workspace", default="workspace")
    p_front.add_argument("--format", choices=["table", "json"], default="table")

    # propose
    p_prop = sub.add_parser("propose", help="Run a single proposer invocation")
    p_prop.add_argument("--workspace", default="workspace")
    p_prop.add_argument("--model", default="opus")
    p_prop.add_argument("--proposals", type=int, default=3)
    p_prop.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    commands = {
        "run": cmd_run,
        "evaluate": cmd_evaluate,
        "frontier": cmd_frontier,
        "propose": cmd_propose,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()

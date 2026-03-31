"""Main evolutionary loop — Algorithm 1 from the Meta-Harness paper.

Flow:
1. Initialize workspace
2. Load & evaluate seed harnesses
3. For t = 1..N:
   a. Proposer reads filesystem, proposes k new harnesses
   b. Validate each (AST parse, interface check)
   c. Evaluate valid proposals against task suite
   d. Update population, Pareto frontier, workspace files
   e. Log iteration
4. Return Pareto frontier
"""

from __future__ import annotations

import difflib
import json
import logging
import time
from pathlib import Path
from typing import Any

from meta_harness.config import MetaHarnessConfig
from meta_harness.domains import get_domain
from meta_harness.domains.base import Domain
from meta_harness.evaluator import EvaluationResult, evaluate_harness, save_evaluation
from meta_harness.filesystem import (
    init_workspace,
    update_overview,
    write_candidate,
    write_diff,
    write_iteration_log,
)
from meta_harness.harness import HarnessError, HarnessInfo, load_harness, validate_ast
from meta_harness.population import Candidate, Population, save_frontier
from meta_harness.proposer import invoke_proposer
from meta_harness.traces import format_trace_summary

logger = logging.getLogger(__name__)


def run_evolution(
    config: MetaHarnessConfig,
    domain_name: str = "text_classification",
) -> list[Candidate]:
    """Execute the full evolutionary search loop.

    Returns the final Pareto frontier.
    """
    logger.info("Starting Meta-Harness evolutionary search")
    logger.info(f"Domain: {domain_name}, Iterations: {config.num_iterations}")

    # Step 1: Initialize
    domain = get_domain(domain_name)
    init_workspace(config)
    population = Population()

    # Step 2: Evaluate seeds
    logger.info("Evaluating seed harnesses...")
    seeds = _load_seeds(config)
    for seed in seeds:
        _evaluate_and_register(seed, domain, config, population, generation=0)

    # Update workspace after seeds
    frontier = population.get_frontier(config)
    save_frontier(config, frontier)
    update_overview(
        config,
        population.stats(),
        [c.harness_id for c in frontier],
        iteration=0,
    )

    logger.info(f"Seeds evaluated. Population: {population.size}, Frontier: {len(frontier)}")

    # Step 3: Evolutionary loop
    for iteration in range(1, config.num_iterations + 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Iteration {iteration}/{config.num_iterations}")
        logger.info(f"{'='*60}")

        t0 = time.time()
        iteration_log: dict[str, Any] = {"iteration": iteration, "proposals": []}

        # 3a: Invoke proposer
        logger.info("Invoking proposer...")
        proposer_result = invoke_proposer(config, iteration)

        if proposer_result.error:
            logger.error(f"Proposer error: {proposer_result.error}")
            iteration_log["proposer_error"] = proposer_result.error
            write_iteration_log(config, iteration, iteration_log)
            continue

        logger.info(
            f"Proposer returned {len(proposer_result.proposals)} proposals "
            f"in {proposer_result.duration_seconds:.1f}s"
        )

        # 3b-3d: Validate, evaluate, register
        for proposal in proposer_result.proposals:
            proposal_log: dict[str, Any] = {
                "name": proposal.name,
                "parent": proposal.parent_id,
                "description": proposal.description,
            }

            # Validate
            try:
                validate_ast(proposal.source_code, Path(f"<proposal:{proposal.name}>"))
            except HarnessError as e:
                logger.warning(f"Proposal '{proposal.name}' failed validation: {e}")
                proposal_log["status"] = "validation_failed"
                proposal_log["error"] = str(e)
                iteration_log["proposals"].append(proposal_log)
                continue

            # Write to temp file and load
            harness_id = population.generate_id(proposal.name)
            candidate_dir = config.candidates_dir() / harness_id
            candidate_dir.mkdir(parents=True, exist_ok=True)
            harness_path = candidate_dir / "harness.py"
            harness_path.write_text(proposal.source_code, encoding="utf-8")

            try:
                harness = load_harness(harness_path, harness_id=harness_id)
            except HarnessError as e:
                logger.warning(f"Proposal '{proposal.name}' failed to load: {e}")
                proposal_log["status"] = "load_failed"
                proposal_log["error"] = str(e)
                iteration_log["proposals"].append(proposal_log)
                continue

            # Evaluate
            eval_result = _evaluate_and_register(
                harness,
                domain,
                config,
                population,
                generation=iteration,
                parent_id=proposal.parent_id,
                description=proposal.description,
                source_code=proposal.source_code,
            )

            if eval_result:
                proposal_log["status"] = "evaluated"
                proposal_log["harness_id"] = harness_id
                proposal_log["scores"] = eval_result.scores

                # Generate diff if parent exists
                if proposal.parent_id:
                    parent_dir = config.candidates_dir() / proposal.parent_id
                    parent_code_path = parent_dir / "harness.py"
                    if parent_code_path.exists():
                        parent_code = parent_code_path.read_text(encoding="utf-8")
                        diff = _compute_diff(parent_code, proposal.source_code)
                        write_diff(config, harness_id, proposal.parent_id, diff)
            else:
                proposal_log["status"] = "evaluation_failed"

            iteration_log["proposals"].append(proposal_log)

        # 3e: Update population, frontier, overview
        removed = population.enforce_size_limit(config)
        if removed:
            logger.info(f"Removed {len(removed)} dominated candidates: {removed}")

        frontier = population.get_frontier(config)
        save_frontier(config, frontier)

        failure_patterns = _extract_failure_patterns(population, config)
        update_overview(
            config,
            population.stats(),
            [c.harness_id for c in frontier],
            iteration=iteration,
            failure_patterns=failure_patterns,
        )

        # 3f: Log
        iteration_log["duration_seconds"] = time.time() - t0
        iteration_log["population_size"] = population.size
        iteration_log["frontier_size"] = len(frontier)
        iteration_log["frontier_ids"] = [c.harness_id for c in frontier]
        write_iteration_log(config, iteration, iteration_log)

        logger.info(
            f"Iteration {iteration} complete. "
            f"Population: {population.size}, Frontier: {len(frontier)}"
        )
        for c in frontier:
            score_str = ", ".join(f"{k}={v:.4f}" for k, v in c.scores.items())
            logger.info(f"  Frontier: {c.harness_id} [{score_str}]")

    # Step 4: Return final frontier
    final_frontier = population.get_frontier(config)
    logger.info(f"\nEvolution complete. Final frontier: {len(final_frontier)} candidates")
    return final_frontier


def _load_seeds(config: MetaHarnessConfig) -> list[HarnessInfo]:
    """Load seed harnesses from the seeds directory."""
    seeds = []
    seeds_dir = config.seeds_dir
    if not seeds_dir.exists():
        logger.warning(f"Seeds directory not found: {seeds_dir}")
        return seeds

    for path in sorted(seeds_dir.glob("*.py")):
        try:
            harness = load_harness(path, harness_id=path.stem)
            seeds.append(harness)
            logger.info(f"Loaded seed: {harness.harness_id}")
        except HarnessError as e:
            logger.error(f"Failed to load seed {path}: {e}")

    return seeds


def _evaluate_and_register(
    harness: HarnessInfo,
    domain: Domain,
    config: MetaHarnessConfig,
    population: Population,
    generation: int,
    parent_id: str | None = None,
    description: str = "",
    source_code: str | None = None,
) -> EvaluationResult | None:
    """Evaluate a harness, register it in the population, and persist results."""
    try:
        result = evaluate_harness(harness, domain, config)
    except Exception as e:
        logger.error(f"Evaluation failed for {harness.harness_id}: {e}")
        return None

    # Register in population
    candidate = Candidate(
        harness_id=harness.harness_id,
        generation=generation,
        parent_id=parent_id,
        scores=result.scores,
        metadata={"description": description},
    )
    population.add(candidate)

    # Persist to filesystem
    code = source_code or harness.source_path.read_text(encoding="utf-8")
    metadata = {
        "harness_id": harness.harness_id,
        "generation": generation,
        "parent": parent_id,
        "description": description,
        "source_path": str(harness.source_path),
    }

    write_candidate(
        config,
        harness.harness_id,
        code,
        metadata,
        result.scores,
        result.trace_summary,
    )
    save_evaluation(result, config)

    score_str = ", ".join(f"{k}={v:.4f}" for k, v in result.scores.items())
    logger.info(f"Evaluated {harness.harness_id}: {score_str}")

    return result


def _compute_diff(old_code: str, new_code: str) -> str:
    """Compute unified diff between two source strings."""
    return "\n".join(
        difflib.unified_diff(
            old_code.splitlines(),
            new_code.splitlines(),
            fromfile="parent",
            tofile="child",
            lineterm="",
        )
    )


def _extract_failure_patterns(population: Population, config: MetaHarnessConfig) -> list[str]:
    """Extract common failure patterns from the population for OVERVIEW.md."""
    patterns: list[str] = []

    # Find candidates with low accuracy
    low_acc = [
        c for c in population.candidates.values()
        if c.scores.get("accuracy", 0) < 0.5
    ]
    if low_acc:
        patterns.append(
            f"{len(low_acc)} candidates with <50% accuracy — check trace_summary.txt for details"
        )

    # Find expensive candidates
    high_cost = [
        c for c in population.candidates.values()
        if c.scores.get("cost_per_task", 0) > 0.01
    ]
    if high_cost:
        patterns.append(
            f"{len(high_cost)} candidates with >$0.01/task cost — consider reducing token usage"
        )

    return patterns

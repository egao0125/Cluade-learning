"""Harness loading, validation, and interface enforcement.

A harness is a Python module with a `run(task: dict, model: str) -> dict`
function.  This module handles dynamic loading, AST validation, dry-run
testing, and the standard interface contract.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class HarnessInfo:
    """Metadata about a loaded harness."""

    harness_id: str
    source_path: Path
    run_fn: Callable[[dict, str], dict]
    source_code: str
    description: str = ""


class HarnessError(Exception):
    """Raised when a harness fails validation."""


def validate_ast(source_code: str, path: Path) -> None:
    """Check that the source defines a `run(task, model)` function."""
    try:
        tree = ast.parse(source_code, filename=str(path))
    except SyntaxError as e:
        raise HarnessError(f"Syntax error in {path}: {e}") from e

    # Look for a top-level `def run(...)` with at least 2 params
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run":
            nargs = len(node.args.args)
            if nargs >= 2:
                return
            raise HarnessError(
                f"{path}: run() must accept at least 2 arguments (task, model), "
                f"found {nargs}"
            )

    raise HarnessError(f"{path}: no top-level `run(task, model)` function found")


def load_harness(path: Path, harness_id: str | None = None) -> HarnessInfo:
    """Dynamically load a harness module from a .py file.

    Validates the AST before loading to catch obvious issues early.
    """
    if not path.exists():
        raise HarnessError(f"Harness file not found: {path}")

    source_code = path.read_text(encoding="utf-8")
    validate_ast(source_code, path)

    # Dynamic import
    if harness_id is None:
        harness_id = path.stem

    module_name = f"meta_harness._loaded_.{harness_id}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"Cannot create module spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        del sys.modules[module_name]
        raise HarnessError(f"Error loading {path}: {e}") from e

    run_fn = getattr(module, "run", None)
    if not callable(run_fn):
        del sys.modules[module_name]
        raise HarnessError(f"{path}: `run` is not callable")

    description = getattr(module, "__doc__", "") or ""

    return HarnessInfo(
        harness_id=harness_id,
        source_path=path,
        run_fn=run_fn,
        source_code=source_code,
        description=description.strip(),
    )


def dry_run(harness: HarnessInfo, model: str = "claude-sonnet-4-20250514") -> bool:
    """Quick validation: call run() with a minimal dummy task.

    Returns True if the harness produces a dict with a 'prediction' key.
    Does NOT call the LLM — the harness should handle gracefully or
    the caller should mock/intercept.
    """
    dummy_task: dict[str, Any] = {
        "id": "dry_run_0",
        "input": "Test input for validation.",
        "label": "test",
        "metadata": {},
    }

    try:
        result = harness.run_fn(dummy_task, model)
    except Exception:
        traceback.print_exc()
        return False

    if not isinstance(result, dict):
        return False
    if "prediction" not in result:
        return False

    return True

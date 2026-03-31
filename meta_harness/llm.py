"""Thin LLM call wrapper that transparently records execution traces.

Every call through `call_llm()` is captured: prompt, response, latency,
token counts, and cost estimate. The traces module collects these for
later persistence alongside the harness evaluation results.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import anthropic


@dataclass
class LLMCallRecord:
    """Single recorded LLM interaction."""

    model: str
    messages: list[dict[str, Any]]
    system: str | None
    response_text: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    cost_usd: float
    timestamp: float = field(default_factory=time.time)


# Thread-local accumulator — reset per evaluation run.
_call_log: list[LLMCallRecord] = []

# Approximate pricing per 1M tokens (as of 2026-03).
_PRICING: dict[str, tuple[float, float]] = {
    # (input_per_M, output_per_M)
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "claude-opus-4-20250514": (15.0, 75.0),
}
_DEFAULT_PRICING = (3.0, 15.0)  # fallback


def reset_call_log() -> list[LLMCallRecord]:
    """Return accumulated records and clear the log."""
    global _call_log
    records = _call_log
    _call_log = []
    return records


def get_call_log() -> list[LLMCallRecord]:
    """Read-only view of current call log."""
    return list(_call_log)


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    inp_rate, out_rate = _PRICING.get(model, _DEFAULT_PRICING)
    return (input_tokens * inp_rate + output_tokens * out_rate) / 1_000_000


def call_llm(
    *,
    model: str,
    messages: list[dict[str, Any]],
    system: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
    api_key: str | None = None,
) -> str:
    """Call the Anthropic API and record the interaction.

    Returns the assistant's text response.
    Uses ANTHROPIC_API_KEY env var, or pass api_key explicitly.
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system

    t0 = time.time()
    response = client.messages.create(**kwargs)
    latency = time.time() - t0

    text = response.content[0].text if response.content else ""
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    record = LLMCallRecord(
        model=model,
        messages=messages,
        system=system,
        response_text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_seconds=latency,
        cost_usd=_estimate_cost(model, input_tokens, output_tokens),
    )
    _call_log.append(record)

    return text

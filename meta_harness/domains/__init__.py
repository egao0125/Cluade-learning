"""Domain registry for Meta-Harness evaluation."""

from __future__ import annotations

from meta_harness.domains.base import Domain

_REGISTRY: dict[str, type[Domain]] = {}


def register_domain(name: str, cls: type[Domain]) -> None:
    _REGISTRY[name] = cls


def get_domain(name: str) -> Domain:
    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys()) or "(none)"
        raise ValueError(f"Unknown domain '{name}'. Available: {available}")
    return _REGISTRY[name]()


def list_domains() -> list[str]:
    return list(_REGISTRY.keys())


# Auto-register built-in domains on import
def _auto_register() -> None:
    from meta_harness.domains.text_classification import TextClassificationDomain

    register_domain("text_classification", TextClassificationDomain)

    from meta_harness.domains.ai_village import (
        AgentAssessDomain,
        AgentDecideDomain,
        AgentPlanDomain,
        AgentReflectDomain,
        AgentTalkDomain,
        AgentThinkDomain,
    )

    register_domain("agent_decide", AgentDecideDomain)
    register_domain("agent_think", AgentThinkDomain)
    register_domain("agent_plan", AgentPlanDomain)
    register_domain("agent_talk", AgentTalkDomain)
    register_domain("agent_reflect", AgentReflectDomain)
    register_domain("agent_assess", AgentAssessDomain)


_auto_register()

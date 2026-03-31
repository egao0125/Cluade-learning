"""Compact decide() harness — same logic, ~40% fewer tokens.

Strips verbose prose, uses terse formatting, removes redundant
instructions. Tests whether shorter prompts maintain quality.
"""

import json
import re
from typing import Any

from meta_harness.llm import call_llm


def run(task: dict[str, Any], model: str) -> dict[str, Any]:
    """Compact version — minimal prompt, same output format."""
    data = json.loads(task["input"])
    situation = data["situation"]
    identity = data["identity"]
    working_memory = data.get("working_memory", {})

    vitals = situation.get("vitals", {})
    inventory = situation.get("inventory", [])
    nearby = situation.get("nearby_agents", [])
    actions = situation.get("available_actions", [])

    # Terse identity
    name = identity.get("name", "Agent")
    soul = identity.get("soul", "")[:300]
    goal = identity.get("goal", "")

    # Terse vitals
    h, hp, e = round(vitals.get("hunger", 0)), round(vitals.get("health", 100)), round(vitals.get("energy", 100))
    inv_str = ", ".join(i["name"] for i in inventory[:5]) or "empty"
    dying = h >= 50 or hp <= 30

    # Terse actions
    action_ids = [a["id"] for a in actions]
    nearby_str = ", ".join(f"{a['name']}" for a in nearby[:4])

    # Terse memory
    mem_parts = []
    for c in working_memory.get("commitments", [])[:3]:
        mem_parts.append(f"Promised {c['target']}: {c['content']}")
    for d in working_memory.get("dossiers", [])[:3]:
        mem_parts.append(f"{d['name']}: trust={d['trust']}")
    for b in working_memory.get("beliefs", [])[:3]:
        mem_parts.append(b)

    system_prompt = f"""You are {name}. {soul[:200]}
Goal: {goal}
Fears: {', '.join(identity.get('fears', [])[:3])}
Desires: {', '.join(identity.get('desires', [])[:3])}

Day {situation.get('time', {}).get('day', 1)} H{situation.get('time', {}).get('hour', 12)} | HP:{hp} Hunger:{h} Energy:{e}
Inventory: {inv_str}
Nearby: {nearby_str or 'nobody'}
{situation.get('trigger', '')}

Actions: {', '.join(action_ids)}
{'⚠ STARVING — eat or get food NOW.' if dying else ''}

Pick ONE action. Be THIS character — not safe, not generic, honest.
JSON only: {{"actionId":"...","reason":"1-2 sentences, first person"}}"""

    user_prompt = "\n".join(mem_parts) if mem_parts else "Decide."

    response = call_llm(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=200,
        temperature=0.0,
    )

    cleaned = re.sub(r"```json?\n?", "", response)
    cleaned = re.sub(r"```", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if parsed.get("actionId") and parsed.get("reason"):
            return {"prediction": parsed}
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[\s\S]*"actionId"[\s\S]*"reason"[\s\S]*\}', response)
    if match:
        try:
            parsed = json.loads(match.group())
            if parsed.get("actionId") and parsed.get("reason"):
                return {"prediction": parsed}
        except json.JSONDecodeError:
            pass

    fallback_id = next((a["id"] for a in actions if a.get("type") == "physical"), "rest")
    return {"prediction": {"actionId": fallback_id, "reason": "Need to think."}}

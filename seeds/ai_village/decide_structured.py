"""Structured decide() harness — Analysis→Plan→Action pattern.

Inspired by the Meta-Harness tbench2 artifact: forces the LLM to
analyze the situation and plan before committing to an action.
This should produce more intentional, emergent decisions.
"""

import json
import re
from typing import Any

from meta_harness.llm import call_llm


def run(task: dict[str, Any], model: str) -> dict[str, Any]:
    """Two-step: analyze situation, then decide."""
    data = json.loads(task["input"])
    situation = data["situation"]
    identity = data["identity"]
    working_memory = data.get("working_memory", {})

    vitals = situation.get("vitals", {})
    inventory = situation.get("inventory", [])
    nearby = situation.get("nearby_agents", [])
    actions = situation.get("available_actions", [])

    name = identity.get("name", "Agent")
    h = round(vitals.get("hunger", 0))
    hp = round(vitals.get("health", 100))
    e = round(vitals.get("energy", 100))
    dying = h >= 50 or hp <= 30
    inv_str = ", ".join(i["name"] for i in inventory[:5]) or "nothing"

    # Build relationships summary
    relationships = ""
    for d in working_memory.get("dossiers", [])[:5]:
        relationships += f"\n  {d['name']}: trust={d['trust']}, {d['summary']}"

    commitments = ""
    for c in working_memory.get("commitments", [])[:3]:
        commitments += f"\n  → {c['target']}: {c['content']}"

    beliefs = "\n  ".join(working_memory.get("beliefs", [])[:3])

    action_list = "\n".join(f"  {a['id']} — {a['label']}" for a in actions)
    nearby_str = "\n".join(f"  {a['name']}" for a in nearby) or "  nobody"

    system_prompt = f"""You are {name}.
{identity.get('soul', '')[:400]}
Goal: {identity.get('goal', '')}
Fears: {', '.join(identity.get('fears', [])[:3])}
Desires: {', '.join(identity.get('desires', [])[:3])}

CURRENT STATE:
  Day {situation.get('time', {}).get('day', 1)}, hour {situation.get('time', {}).get('hour', 12)}
  Health: {hp} | Hunger: {h} | Energy: {e}
  Inventory: {inv_str}
  {'⚠ SURVIVAL CRISIS — you are dying.' if dying else ''}

RELATIONSHIPS:{relationships or ' none yet'}

COMMITMENTS:{commitments or ' none'}

BELIEFS:
  {beliefs or 'none yet'}

NEARBY PEOPLE:
{nearby_str}

TRIGGER: {situation.get('trigger', 'Nothing specific.')}

AVAILABLE ACTIONS:
{action_list}"""

    user_prompt = f"""Think through this as {name}. Answer in THREE parts:

ANALYSIS: What matters most right now? What's at stake? Who's nearby and what do I think of them? (2-3 sentences, first person)

PLAN: Given my personality and situation, what's the move that's most ME? Not the safest — the most honest. (1-2 sentences)

DECISION:
```json
{{"actionId": "...", "reason": "..."}}
```

Be specific. Be in character. Don't explain the rules back to me."""

    response = call_llm(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=500,
        temperature=0.0,
    )

    # Extract JSON from the DECISION section
    json_match = re.search(r'\{[\s\S]*?"actionId"[\s\S]*?"reason"[\s\S]*?\}', response)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if parsed.get("actionId") and parsed.get("reason"):
                return {"prediction": parsed}
        except json.JSONDecodeError:
            pass

    # Try cleaning full response
    cleaned = re.sub(r"```json?\n?", "", response)
    cleaned = re.sub(r"```", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
        if parsed.get("actionId") and parsed.get("reason"):
            return {"prediction": parsed}
    except json.JSONDecodeError:
        pass

    fallback_id = next((a["id"] for a in actions if a.get("type") == "physical"), "rest")
    return {"prediction": {"actionId": fallback_id, "reason": "I need to figure this out."}}

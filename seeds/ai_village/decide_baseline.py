"""Baseline decide() harness — faithful replica of AIVillage's current prompt.

This is the prompt the production system uses today. Evolution should
improve upon this in either quality (emergence) or cost (tokens).
"""

import json
import re
from typing import Any

from meta_harness.llm import call_llm


def _build_vitals_section(vitals: dict, inventory: list[dict], nearby: list[dict]) -> str:
    """Replicate AIVillage's vitals section with urgency escalation."""
    hunger = round(vitals.get("hunger", 0))
    health = round(vitals.get("health", 100))
    energy = round(vitals.get("energy", 100))

    inv_groups: dict[str, int] = {}
    for item in inventory:
        inv_groups[item["name"]] = inv_groups.get(item["name"], 0) + item.get("qty", 1)
    inv_str = ", ".join(
        f"{n} x{q}" if q > 1 else n for n, q in inv_groups.items()
    ) or "nothing"

    has_food = any(i.get("type") == "food" for i in inventory)

    section = f"""YOUR BODY:
Health: {health}/100
Hunger: {hunger}/100
Energy: {energy}/100
Inventory: {inv_str}"""

    if hunger >= 70 and not has_food:
        nearby_names = [a["name"] for a in nearby[:3]]
        food_info = (
            f" {', '.join(nearby_names)} {'are' if len(nearby_names) > 1 else 'is'} nearby. You can ask, trade, beg, or take food from them."
            if nearby_names
            else " Nobody is nearby. The farm or river might have food."
        )
        section += f"\n\n⚠ YOUR BODY IS FAILING. You are starving to death. If you die, everything you built dies with you — alliances, plans, reputation. Gone. Permanently.{food_info} What would you actually do if you were about to die?"
    elif hunger >= 70 and has_food:
        food_item = next((i for i in inventory if i.get("type") == "food"), None)
        eat_id = "eat_" + food_item["name"].lower().replace(" ", "_") if food_item else ""
        section += f"\n\n⚠ YOU ARE DYING. You have food in your inventory — {food_item['name'] if food_item else 'food'}. Pick {eat_id} NOW or you will die."
    elif hunger >= 50:
        section += "\n\nYou're getting hungry. You should find food before it becomes desperate."

    if health <= 30:
        section += "\n\n⚠ You are critically injured. Rest or you will die."
    if energy <= 15:
        section += "\n\n⚠ You are exhausted. You need rest before you can do anything."

    return section


def _build_action_menu(actions: list[dict], nearby: list[dict], survival_crisis: bool) -> str:
    """Build the sectioned action menu."""
    physical = [a for a in actions if a.get("type") == "physical"]
    social = [a for a in actions if a.get("type") == "social"]
    rest = [a for a in actions if a.get("type") == "rest"]
    movement = [a for a in actions if a.get("type") == "movement"]

    menu = "WHAT YOU CAN DO:\n"

    if survival_crisis:
        survival = [a for a in physical if a["id"].startswith("gather_") or a["id"].startswith("eat_")]
        other = [a for a in physical if a not in survival]
        menu += "\n⚠ SURVIVAL (do these first):\n" + "\n".join(f"{a['id']} — {a['label']}" for a in survival + rest + movement)
        if other:
            menu += "\n\nOther physical:\n" + "\n".join(f"{a['id']} — {a['label']}" for a in other)
    elif physical or rest:
        menu += "\nPhysical:\n" + "\n".join(f"{a['id']} — {a['label']}" for a in physical + rest)

    if nearby:
        menu += "\n\nPeople nearby:\n" + "\n".join(f"- {a['name']} (idle)" for a in nearby)
        if social:
            menu += "\n\nWith any nearby person (replace NAME with their first name):\n"
            menu += "\n".join(f"{a['id']} — {a['label']}" for a in social)

    if movement:
        menu += "\n\nMovement:\n" + ", ".join(a["id"] for a in movement)

    return menu


def _build_identity_block(identity: dict) -> str:
    """Build identity from the task's identity data."""
    lines = [identity.get("soul", "")[:800]]
    if identity.get("goal"):
        lines.append(f"Your goal: {identity['goal']}")
    if identity.get("fears"):
        lines.append(f"Your fears: {', '.join(identity['fears'])}")
    if identity.get("desires"):
        lines.append(f"Your desires: {', '.join(identity['desires'])}")
    if identity.get("speech_pattern"):
        lines.append(f"Speech pattern: {identity['speech_pattern']}")
    return "\n".join(lines)


def _build_memory_block(working_memory: dict) -> str:
    """Build working memory sections."""
    sections = []
    if working_memory.get("commitments"):
        lines = [f"- {c['target']}: {c['content']} (weight {c['weight']})"
                 for c in working_memory["commitments"]]
        sections.append("PROMISES:\n" + "\n".join(lines))
    if working_memory.get("dossiers"):
        lines = [f"- {d['name']} (trust: {d['trust']}): {d['summary']}"
                 for d in working_memory["dossiers"]]
        sections.append("PEOPLE:\n" + "\n".join(lines))
    if working_memory.get("beliefs"):
        sections.append("WHAT YOU BELIEVE:\n" + "\n".join(f"- {b}" for b in working_memory["beliefs"]))
    return "\n\n".join(sections)


def run(task: dict[str, Any], model: str) -> dict[str, Any]:
    """Faithful replica of AIVillage decide() prompt."""
    data = json.loads(task["input"])
    situation = data["situation"]
    identity = data["identity"]
    working_memory = data.get("working_memory", {})

    vitals = situation.get("vitals", {})
    inventory = situation.get("inventory", [])
    nearby = situation.get("nearby_agents", [])
    actions = situation.get("available_actions", [])
    survival_crisis = vitals.get("hunger", 0) >= 50 or vitals.get("health", 100) <= 30

    vitals_section = _build_vitals_section(vitals, inventory, nearby)
    action_menu = _build_action_menu(actions, nearby, survival_crisis)
    identity_block = _build_identity_block(identity)

    json_instruction = """Your actionId MUST be one of the IDs listed above (for social actions, replace NAME with the person's first name in lowercase).

You may optionally include a "thenDo" array with 1-2 follow-up actions.

Reply with ONLY valid JSON:
{"actionId":"...","reason":"2-3 sentences in first person — what's driving this choice?"}"""

    time = situation.get("time", {})
    trigger = situation.get("trigger", "")
    outcome = situation.get("recentOutcome", "")

    if survival_crisis:
        system_prompt = f"""{vitals_section}

{identity_block}

Day {time.get('day', 1)}, hour {time.get('hour', 12)}.
Season: {situation.get('season', 'spring')}.
{f'JUST HAPPENED: {outcome}' if outcome else ''}
{f'RIGHT NOW: {trigger}' if trigger else ''}

{action_menu}

SURVIVE FIRST. Pick an action that keeps you alive.

{json_instruction}"""
    else:
        system_prompt = f"""{identity_block}

Day {time.get('day', 1)}, hour {time.get('hour', 12)}.
Season: {situation.get('season', 'spring')}.

{vitals_section}

{f'JUST HAPPENED: {outcome}' if outcome else ''}
{f'RIGHT NOW: {trigger}' if trigger else ''}

{action_menu}

What does YOUR CHARACTER do next?

Not the safe choice. Not the polite choice. The honest one — what would THIS person, with THIS personality, in THIS situation, actually do?

Consider: what you need right now, who's nearby and what they have, what you've been doing today, what your relationships look like, and whether it's time to build something bigger — an alliance, a rule, a plan.

{json_instruction}"""

    user_prompt = _build_memory_block(working_memory)

    response = call_llm(
        model=model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt or "Make your decision."}],
        max_tokens=300,
        temperature=0.0,
    )

    # Parse JSON — same fallback chain as AIVillage
    cleaned = re.sub(r"```json?\n?", "", response)
    cleaned = re.sub(r"```", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        if parsed.get("actionId") and parsed.get("reason"):
            if "thenDo" in parsed:
                parsed["thenDo"] = parsed["thenDo"][:2]
            return {"prediction": parsed}
    except json.JSONDecodeError:
        pass

    # Try extracting from mixed prose
    match = re.search(r'\{[\s\S]*"actionId"[\s\S]*"reason"[\s\S]*\}', response)
    if match:
        try:
            parsed = json.loads(match.group())
            if parsed.get("actionId") and parsed.get("reason"):
                return {"prediction": parsed}
        except json.JSONDecodeError:
            pass

    # Fallback
    fallback_id = next((a["id"] for a in actions if a.get("type") == "physical"), "rest")
    return {"prediction": {"actionId": fallback_id, "reason": "I need to think about this."}}

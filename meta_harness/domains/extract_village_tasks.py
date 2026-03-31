"""Extract Meta-Harness task data from AIVillage simulation snapshots.

Usage:
    python -m meta_harness.domains.extract_village_tasks \
        --snapshot /path/to/monarchy-snapshot.json \
        --world-state /path/to/world-state-snapshot.json \
        --output tasks/ai_village/

Produces JSONL files for each cognitive function:
    decide.jsonl, think.jsonl, plan.jsonl, talk.jsonl, reflect.jsonl, assess.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def extract_decide_tasks(agents: list[dict], world: dict, areas: list[dict]) -> list[dict]:
    """Generate decide() tasks from agent snapshots.

    Each task simulates a moment where the agent must choose an action.
    """
    tasks = []
    task_id = 0
    time_info = world.get("time", {"day": 1, "hour": 12})

    # Available actions template (simplified from game)
    base_actions = [
        {"id": "gather_wheat", "label": "Gather wheat", "type": "physical"},
        {"id": "gather_berries", "label": "Gather berries", "type": "physical"},
        {"id": "craft_bread", "label": "Craft bread", "type": "physical"},
        {"id": "eat", "label": "Eat food", "type": "physical"},
        {"id": "rest", "label": "Rest", "type": "rest"},
        {"id": "sleep", "label": "Sleep", "type": "rest"},
        {"id": "build", "label": "Build structure", "type": "physical"},
    ]

    for agent in agents:
        if not agent.get("alive", True):
            continue

        config = agent.get("config", {})
        vitals = agent.get("vitals", {})
        inventory = agent.get("inventory", [])

        # Build nearby agents (others at similar locations)
        nearby = []
        for other in agents:
            if other["id"] != agent["id"] and other.get("alive", True):
                nearby.append({
                    "name": other["config"]["name"],
                    "id": other["id"],
                    "activity": "idle",
                })

        # Generate social actions for nearby agents
        social_actions = []
        for n in nearby[:3]:
            social_actions.append({
                "id": f"talk_{n['name'].lower().replace(' ', '_')}",
                "label": f"Talk to {n['name']}",
                "type": "social",
            })

        available_actions = base_actions + social_actions

        # Scenario variations
        scenarios = [
            {"trigger": "You just woke up.", "hour": 7},
            {"trigger": f"You see {nearby[0]['name']} walking nearby." if nearby else "The village is quiet.", "hour": 10},
            {"trigger": "Your stomach growls." if vitals.get("hunger", 0) > 30 else "The afternoon sun is warm.", "hour": 14},
            {"trigger": "Evening approaches. You feel tired.", "hour": 20},
        ]

        for scenario in scenarios:
            task_id += 1
            situation = {
                "location": "village_square",
                "time": {"day": time_info.get("day", 1), "hour": scenario["hour"]},
                "season": "spring",
                "vitals": vitals,
                "inventory": [{"name": i["name"], "type": i.get("type", "item"), "qty": 1} for i in inventory[:5]],
                "nearby_agents": nearby[:4],
                "available_actions": available_actions,
                "trigger": scenario["trigger"],
            }

            # Build identity block
            identity = {
                "name": config.get("name", "Unknown"),
                "soul": config.get("soul", config.get("backstory", ""))[:800],
                "goal": config.get("goal", ""),
                "fears": config.get("fears", []),
                "desires": config.get("desires", []),
                "personality": config.get("personality", {}),
                "speech_pattern": config.get("speechPattern", ""),
            }

            # Working memory from beliefs/commitments
            working_memory = {
                "beliefs": [b.get("content", "") for b in agent.get("beliefs", [])[:5]],
                "commitments": [
                    {"target": c.get("targetName", ""), "content": c.get("content", ""), "weight": c.get("weight", 1)}
                    for c in agent.get("commitments", []) if not c.get("fulfilled") and not c.get("broken")
                ],
                "dossiers": [
                    {"name": d.get("targetName", ""), "trust": d.get("trust", 0), "summary": d.get("summary", "")[:100]}
                    for d in agent.get("dossiers", [])[:5]
                ],
            }

            tasks.append({
                "id": f"decide_{task_id:04d}",
                "input": json.dumps({"situation": situation, "identity": identity, "working_memory": working_memory}),
                "label": None,  # no single correct answer — scored by judge
                "metadata": {
                    "agent_name": config.get("name"),
                    "agent_id": agent["id"],
                    "context_summary": f"{config.get('name')} at hour {scenario['hour']}: {scenario['trigger']}",
                    "available_actions": available_actions,
                    "function": "decide",
                },
            })

    return tasks


def extract_think_tasks(agents: list[dict], world: dict) -> list[dict]:
    """Generate think() tasks — immediate reactions to events."""
    tasks = []
    task_id = 0

    alive_agents = [a for a in agents if a.get("alive", True)]

    triggers = [
        "{other} approaches you with a serious expression.",
        "You notice {other} gathering food near the river.",
        "A loud argument breaks out between {other} and someone else.",
        "{other} offers you a gift of wheat.",
        "You find a piece of paper on the ground with {other}'s handwriting.",
        "The village board has a new post about upcoming elections.",
        "{other} avoids eye contact with you.",
        "You hear rumors that {other} has been hoarding resources.",
    ]

    for agent in alive_agents:
        config = agent.get("config", {})
        others = [a for a in alive_agents if a["id"] != agent["id"]]

        for trigger_template in triggers[:4]:  # 4 per agent
            task_id += 1
            other = random.choice(others) if others else agent
            other_name = other["config"]["name"]
            trigger = trigger_template.format(other=other_name)

            tasks.append({
                "id": f"think_{task_id:04d}",
                "input": json.dumps({
                    "trigger": trigger,
                    "context": f"You are at the village square. It is day {world.get('time', {}).get('day', 1)}.",
                    "identity": {
                        "name": config.get("name"),
                        "soul": config.get("soul", "")[:400],
                        "fears": config.get("fears", []),
                        "desires": config.get("desires", []),
                    },
                    "nearby_agent_ids": [other["id"]],
                }),
                "label": None,
                "metadata": {
                    "agent_name": config.get("name"),
                    "agent_id": agent["id"],
                    "context_summary": f"{config.get('name')} reacting to: {trigger}",
                    "function": "think",
                },
            })

    return tasks


def extract_plan_tasks(agents: list[dict], world: dict) -> list[dict]:
    """Generate plan() tasks — morning priority setting."""
    tasks = []
    task_id = 0

    for agent in agents:
        if not agent.get("alive", True):
            continue

        config = agent.get("config", {})
        vitals = agent.get("vitals", {})
        beliefs = agent.get("beliefs", [])
        commitments = agent.get("commitments", [])

        task_id += 1
        recent_memories = [b.get("content", "") for b in beliefs[:10]]
        active_commitments = [
            f"{c.get('targetName')}: {c.get('content')}"
            for c in commitments if not c.get("fulfilled") and not c.get("broken")
        ]

        tasks.append({
            "id": f"plan_{task_id:04d}",
            "input": json.dumps({
                "time": {"day": world.get("time", {}).get("day", 1), "hour": 7},
                "identity": {
                    "name": config.get("name"),
                    "soul": config.get("soul", "")[:400],
                    "goal": config.get("goal", ""),
                    "fears": config.get("fears", []),
                    "desires": config.get("desires", []),
                },
                "vitals": vitals,
                "recent_memories": recent_memories,
                "active_commitments": active_commitments,
                "board_posts": [p.get("content", "")[:100] for p in world.get("board", [])[:5]],
            }),
            "label": None,
            "metadata": {
                "agent_name": config.get("name"),
                "agent_id": agent["id"],
                "context_summary": f"{config.get('name')} planning day {world.get('time', {}).get('day', 1)}",
                "function": "plan",
            },
        })

    return tasks


def extract_talk_tasks(agents: list[dict], world: dict) -> list[dict]:
    """Generate talk() tasks — conversation turns."""
    tasks = []
    task_id = 0

    alive_agents = [a for a in agents if a.get("alive", True)]

    # Generate pairwise conversation scenarios
    conversation_starters = [
        ("I need food. Do you have any to spare?", True),
        ("What do you think about the new village rules?", False),
        ("I saw what you did yesterday. We need to talk.", False),
        ("Want to work together on building a shelter?", False),
    ]

    for agent in alive_agents:
        config = agent.get("config", {})
        others = [a for a in alive_agents if a["id"] != agent["id"]]

        for other in others[:2]:  # 2 conversations per agent
            for starter, has_trade in conversation_starters[:2]:
                task_id += 1
                other_config = other["config"]

                history = [f'{other_config["name"]}: "{starter}"']

                tasks.append({
                    "id": f"talk_{task_id:04d}",
                    "input": json.dumps({
                        "other_agents": [{"name": other_config["name"], "id": other["id"]}],
                        "conversation_history": history,
                        "turn": 2,
                        "max_turns": 8,
                        "identity": {
                            "name": config.get("name"),
                            "soul": config.get("soul", "")[:400],
                            "personality": config.get("personality", {}),
                            "speech_pattern": config.get("speechPattern", ""),
                        },
                        "vitals": agent.get("vitals", {}),
                        "inventory": [{"name": i["name"], "type": i.get("type", "")} for i in agent.get("inventory", [])[:5]],
                        "relationship": next(
                            ({"trust": d["trust"], "summary": d.get("summary", "")}
                             for d in agent.get("dossiers", []) if d.get("targetId") == other["id"]),
                            {"trust": 0, "summary": "No prior relationship"},
                        ),
                    }),
                    "label": None,
                    "metadata": {
                        "agent_name": config.get("name"),
                        "agent_id": agent["id"],
                        "other_name": other_config["name"],
                        "context_summary": f"{config.get('name')} talking to {other_config['name']}",
                        "has_trade_context": has_trade,
                        "function": "talk",
                    },
                })

    return tasks


def extract_reflect_tasks(agents: list[dict], world: dict) -> list[dict]:
    """Generate reflect() tasks — end-of-day reflection."""
    tasks = []
    task_id = 0

    for agent in agents:
        if not agent.get("alive", True):
            continue

        config = agent.get("config", {})
        beliefs = agent.get("beliefs", [])
        commitments = agent.get("commitments", [])
        dossiers = agent.get("dossiers", [])

        task_id += 1

        # Simulate day's memories from beliefs and commitments
        day_memories = [
            f"[belief] {b.get('content', '')}"
            for b in beliefs[:15]
        ]
        for c in commitments[:5]:
            status = "fulfilled" if c.get("fulfilled") else "broken" if c.get("broken") else "pending"
            day_memories.append(f"[commitment] {c.get('targetName')}: {c.get('content')} ({status})")

        social_context = "\n".join(
            f"- {d.get('targetName')}: trust={d.get('trust', 0)}, {d.get('summary', '')[:80]}"
            for d in dossiers[:5]
        )

        tasks.append({
            "id": f"reflect_{task_id:04d}",
            "input": json.dumps({
                "time": {"day": world.get("time", {}).get("day", 1), "hour": 22},
                "identity": {
                    "name": config.get("name"),
                    "soul": config.get("soul", "")[:600],
                    "goal": config.get("goal", ""),
                    "fears": config.get("fears", []),
                    "desires": config.get("desires", []),
                    "personality": config.get("personality", {}),
                },
                "day_memories": day_memories,
                "social_context": social_context,
                "current_my_experience": agent.get("worldView", "")[:1000],
            }),
            "label": None,
            "metadata": {
                "agent_name": config.get("name"),
                "agent_id": agent["id"],
                "context_summary": f"{config.get('name')} reflecting on day {world.get('time', {}).get('day', 1)}",
                "function": "reflect",
            },
        })

    return tasks


def extract_assess_tasks(agents: list[dict], world: dict) -> list[dict]:
    """Generate assess() tasks — mental model formation."""
    tasks = []
    task_id = 0

    alive_agents = [a for a in agents if a.get("alive", True)]

    for agent in alive_agents:
        config = agent.get("config", {})
        dossiers = agent.get("dossiers", [])

        # Build simulated recent interactions from dossiers
        interactions = []
        for d in dossiers[:5]:
            interactions.append(
                f"Talked with {d.get('targetName', 'someone')} — {d.get('summary', 'brief interaction')[:150]}"
            )

        if not interactions:
            continue

        task_id += 1
        tasks.append({
            "id": f"assess_{task_id:04d}",
            "input": json.dumps({
                "identity": {
                    "name": config.get("name"),
                    "personality": config.get("personality", {}),
                },
                "recent_interactions": interactions,
                "known_agents": [
                    {"name": d.get("targetName"), "id": d.get("targetId")}
                    for d in dossiers[:8]
                ],
            }),
            "label": None,
            "metadata": {
                "agent_name": config.get("name"),
                "agent_id": agent["id"],
                "context_summary": f"{config.get('name')} assessing {len(interactions)} interactions",
                "function": "assess",
                "expected_targets": [d.get("targetId") for d in dossiers[:5]],
            },
        })

    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract AIVillage tasks for Meta-Harness")
    parser.add_argument("--snapshot", required=True, help="Path to monarchy-snapshot.json")
    parser.add_argument("--output", default="tasks/ai_village", help="Output directory")
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    agents = data.get("agents", [])
    world = data

    print(f"Loaded {len(agents)} agents from {snapshot_path}")

    areas = data.get("areas", [])

    all_tasks: dict[str, list[dict]] = {
        "decide": extract_decide_tasks(agents, world, areas),
        "think": extract_think_tasks(agents, world),
        "plan": extract_plan_tasks(agents, world),
        "talk": extract_talk_tasks(agents, world),
        "reflect": extract_reflect_tasks(agents, world),
        "assess": extract_assess_tasks(agents, world),
    }

    total = 0
    for name, tasks in all_tasks.items():
        output_path = output_dir / f"{name}.jsonl"
        with open(output_path, "w", encoding="utf-8") as f:
            for task in tasks:
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
        print(f"  {name}: {len(tasks)} tasks → {output_path}")
        total += len(tasks)

    print(f"\nTotal: {total} tasks")


if __name__ == "__main__":
    main()

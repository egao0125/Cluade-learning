"""Chain-of-thought baseline: reason step-by-step before classifying."""

from typing import Any

from meta_harness.llm import call_llm


def run(task: dict[str, Any], model: str) -> dict[str, Any]:
    """Classify the input text using chain-of-thought reasoning."""
    text = task["input"]
    categories = task.get("metadata", {}).get("categories", [])
    cat_str = ", ".join(categories) if categories else "positive, negative, neutral"

    response = call_llm(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify the following text into exactly one of these categories: {cat_str}\n\n"
                    f"Text: {text}\n\n"
                    f"Think step by step:\n"
                    f"1. What is the main sentiment or topic of this text?\n"
                    f"2. What key words or phrases indicate the category?\n"
                    f"3. Which category best fits?\n\n"
                    f"After your reasoning, output your final answer on a new line as:\n"
                    f"ANSWER: <category>"
                ),
            }
        ],
        max_tokens=300,
        temperature=0.0,
    )

    # Extract the ANSWER: line
    prediction = response.strip()
    for line in reversed(response.strip().splitlines()):
        if line.strip().upper().startswith("ANSWER:"):
            prediction = line.split(":", 1)[1].strip()
            break

    return {"prediction": prediction.lower()}

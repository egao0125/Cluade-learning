"""Zero-shot baseline: ask the LLM to classify with no examples."""

from typing import Any

from meta_harness.llm import call_llm


def run(task: dict[str, Any], model: str) -> dict[str, Any]:
    """Classify the input text using zero-shot prompting."""
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
                    f"Respond with ONLY the category name, nothing else."
                ),
            }
        ],
        max_tokens=50,
        temperature=0.0,
    )

    return {"prediction": response.strip().lower()}

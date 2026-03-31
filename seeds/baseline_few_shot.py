"""Few-shot baseline: provide 3 examples before classifying."""

from typing import Any

from meta_harness.llm import call_llm

# Static few-shot examples for sentiment classification
_FEW_SHOT_EXAMPLES = [
    ("This product is amazing, I love it!", "positive"),
    ("Terrible experience, would not recommend.", "negative"),
    ("The item arrived on time and works as described.", "neutral"),
]


def run(task: dict[str, Any], model: str) -> dict[str, Any]:
    """Classify the input text using few-shot prompting."""
    text = task["input"]
    categories = task.get("metadata", {}).get("categories", [])
    cat_str = ", ".join(categories) if categories else "positive, negative, neutral"

    examples_block = "\n".join(
        f"Text: {ex_text}\nCategory: {ex_label}"
        for ex_text, ex_label in _FEW_SHOT_EXAMPLES
    )

    response = call_llm(
        model=model,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify each text into exactly one of these categories: {cat_str}\n\n"
                    f"Examples:\n{examples_block}\n\n"
                    f"Now classify this text:\n"
                    f"Text: {text}\n"
                    f"Category:"
                ),
            }
        ],
        max_tokens=50,
        temperature=0.0,
    )

    return {"prediction": response.strip().lower()}

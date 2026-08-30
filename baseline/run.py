"""
Baseline PR reviewer: one direct prompt, no tools, no repo context.
This represents "the simple way" someone would use an LLM today.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import load_cases, get_client, save_results, call_model

PROMPT_TEMPLATE = """You are reviewing a code change. Read the diff below and list any bugs you find.
If there are no bugs, say "No bugs found."

Diff:
{diff}
"""


def review_diff(client, diff):
    return call_model(client, PROMPT_TEMPLATE.format(diff=diff))


def main():
    client = get_client()
    cases = load_cases()
    results = []

    for case in cases:
        print(f"Reviewing {case['id']}: {case['title']}...")
        review = review_diff(client, case["diff"])
        results.append({
            "id": case["id"],
            "title": case["title"],
            "ground_truth_bug": case["ground_truth_bug"],
            "model_review": review,
        })

    out_path = os.path.join(os.path.dirname(__file__), "..", "eval", "baseline_results.json")
    save_results(results, out_path)


if __name__ == "__main__":
    main()
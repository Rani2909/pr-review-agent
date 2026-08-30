"""
Scores baseline_results.json and agent_results.json against ground truth.

For each case:
  - If ground_truth_bug is set: did the review catch it? (yes/no, via judge call)
  - If ground_truth_bug is null (clean code): did the review wrongly report a bug? (false positive)

Prints a comparison table and saves eval/scorecard.json.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import get_client, save_results, call_model

JUDGE_PROMPT = """You are grading a code review for accuracy.

The known real bug in this code is: {ground_truth}

(If it says "None", the code has NO bug and any reported issue is a false positive.)

The review under evaluation said:
---
{review_text}
---

Question: Did the review correctly identify the known real bug (or correctly say there is no bug,
if ground truth is None)? Answer with exactly one word: CORRECT or MISSED or FALSE_POSITIVE.
"""


def judge(client, ground_truth, review_text):
    prompt = JUDGE_PROMPT.format(
        ground_truth=ground_truth if ground_truth else "None",
        review_text=review_text,
    )
    verdict = call_model(client, prompt, max_tokens=10).strip().upper()
    for label in ("CORRECT", "MISSED", "FALSE_POSITIVE"):
        if label in verdict:
            return label
    return "UNKNOWN"


def load_results(path):
    with open(path) as f:
        return json.load(f)


def get_review_text(entry, key):
    """baseline results store plain text; agent results store a dict with confirmed_issues."""
    if key == "model_review":
        return entry["model_review"]
    else:
        review = entry["agent_review"]
        if review["confirmed_issues"]:
            return "Confirmed issues:\n" + "\n".join(review["confirmed_issues"])
        return "No confirmed issues."


def score_file(client, path, review_key):
    results = load_results(path)
    scored = []
    for entry in results:
        text = get_review_text(entry, review_key)
        verdict = judge(client, entry["ground_truth_bug"], text)
        scored.append({"id": entry["id"], "title": entry["title"], "verdict": verdict})
    return scored


def summarize(scored):
    correct = sum(1 for s in scored if s["verdict"] == "CORRECT")
    missed = sum(1 for s in scored if s["verdict"] == "MISSED")
    false_pos = sum(1 for s in scored if s["verdict"] == "FALSE_POSITIVE")
    total = len(scored)
    return {"correct": correct, "missed": missed, "false_positive": false_pos, "total": total}


def main():
    client = get_client()
    eval_dir = os.path.dirname(__file__)

    baseline_path = os.path.join(eval_dir, "baseline_results.json")
    agent_path = os.path.join(eval_dir, "agent_results.json")

    print("Scoring baseline...")
    baseline_scored = score_file(client, baseline_path, "model_review")
    print("Scoring agent...")
    agent_scored = score_file(client, agent_path, "agent_review")

    baseline_summary = summarize(baseline_scored)
    agent_summary = summarize(agent_scored)

    scorecard = {
        "baseline": {"summary": baseline_summary, "cases": baseline_scored},
        "agent": {"summary": agent_summary, "cases": agent_scored},
    }
    save_results(scorecard, os.path.join(eval_dir, "scorecard.json"))

    print("\n=== RESULTS ===")
    print(f"{'Metric':<20}{'Baseline':<12}{'Agent':<12}")
    print(f"{'Correct':<20}{baseline_summary['correct']:<12}{agent_summary['correct']:<12}")
    print(f"{'Missed':<20}{baseline_summary['missed']:<12}{agent_summary['missed']:<12}")
    print(f"{'False positives':<20}{baseline_summary['false_positive']:<12}{agent_summary['false_positive']:<12}")
    print(f"{'Total cases':<20}{baseline_summary['total']:<12}{agent_summary['total']:<12}")


if __name__ == "__main__":
    main()
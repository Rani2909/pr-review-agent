"""
Agent PR reviewer: three upgrades over the baseline.
  1. A real tool call: static analysis via Python's ast module runs BEFORE the
     model sees the code, checking for syntax validity and flagging risky
     patterns (bare except, mutable default arguments) so the model gets that
     as verified, deterministic context instead of having to spot it unaided.
  2. Structured analysis prompt (asks the model to reason about intent vs. behavior
     line-by-line before concluding, instead of a one-shot guess).
  3. A self-verification pass: every candidate bug is re-checked against the code
     in a second call before being reported, to cut down false positives.
"""
import sys
import os
import re
import ast

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common import load_cases, get_client, save_results, call_model


def run_static_analysis(code):
    """A real tool: parse the code with Python's ast module and flag known
    risky patterns deterministically, without relying on the model to notice
    them unaided. Returns a list of finding strings."""
    findings = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"SYNTAX ERROR: code does not parse: {e}"]

    for node in ast.walk(tree):
        # Bare except: or except Exception: catches too broadly
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                findings.append("Static analysis: bare 'except:' clause found (catches ALL exceptions).")
            elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                findings.append("Static analysis: 'except Exception:' found (very broad exception handling).")

        # Mutable default arguments (list/dict/set literal as a default)
        if isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(
                        f"Static analysis: function '{node.name}' has a mutable default "
                        f"argument (list/dict/set), which is a classic Python pitfall."
                    )

    if not findings:
        findings.append("Static analysis: no risky patterns detected (code parses cleanly, no bare except, no mutable defaults).")
    return findings


ANALYZE_PROMPT = """You are an experienced code reviewer. Analyze the following code change carefully.

A static analysis tool has already checked this code and found:
{static_findings}

Steps:
1. Explain what the function is INTENDED to do (from its name, docstring, and parameters).
2. Walk through the logic line by line.
3. List EVERY place where the actual behavior might diverge from the intended behavior,
   including edge cases, security issues, and silent correctness bugs. Explicitly consider:
   what happens on a lookup that finds nothing, an empty input, or a boundary value.
   Take the static analysis findings above into account -- confirm, expand on, or set aside
   each one as appropriate, and add anything static analysis alone can't catch.

Code:
{diff}

IMPORTANT: Put every single candidate issue as its own numbered list item (1., 2., 3., ...)
at the end of your response, even the most obvious one. Do not bury an issue inside a
parenthetical note or a summary sentence -- it must appear as its own numbered item to be
counted. If you find none, write "No candidate issues."
"""

VERIFY_PROMPT = """You previously found this candidate issue in a code review:

Candidate issue: {candidate}

Here is the code again:
{diff}

Re-check this specific issue. A candidate is a REAL bug if EITHER of these is true:
(a) It causes an incorrect or crashing result on a REALISTIC, ROUTINE input that this
    kind of function will commonly encounter in normal use (e.g. a lookup that finds
    nothing, an empty collection, a zero count) -- even if the docstring doesn't
    explicitly mention that case, because handling routine cases gracefully is part
    of a function's implicit contract.
(b) It causes the function to violate what its docstring explicitly promises for
    well-formed input.

A candidate is NOT a real bug if it only occurs when the caller does something a
reasonable developer would consider clear misuse -- passing arguments in the wrong
order, passing a fundamentally wrong type the function was never meant to accept
(e.g. a string where a number is expected), or contrived inputs (NaN, extremely
malformed data) that go beyond normal, expected use.

Answer with just "YES: <one-sentence reason>" or "NO: <one-sentence reason>".
"""


def analyze(client, diff, static_findings):
    formatted_findings = "\n".join(f"- {f}" for f in static_findings)
    return call_model(client, ANALYZE_PROMPT.format(diff=diff, static_findings=formatted_findings))


def extract_candidates(analysis_text):
    """Pull numbered list items out of the analysis response."""
    lines = analysis_text.strip().splitlines()
    candidates = []
    for line in lines:
        match = re.match(r"^\s*\d+[\.\)]\s+(.*)", line)
        if match:
            candidates.append(match.group(1).strip())
    return candidates


def verify(client, diff, candidate):
    text = call_model(client, VERIFY_PROMPT.format(candidate=candidate, diff=diff), max_tokens=150)
    text = text.strip()
    confirmed = text.upper().startswith("YES")
    return confirmed, text


def review_diff(client, diff):
    static_findings = run_static_analysis(diff)
    analysis = analyze(client, diff, static_findings)
    candidates = extract_candidates(analysis)

    confirmed_issues = []
    verification_log = []
    for candidate in candidates:
        confirmed, reason = verify(client, diff, candidate)
        verification_log.append({"candidate": candidate, "confirmed": confirmed, "reason": reason})
        if confirmed:
            confirmed_issues.append(candidate)

    return {
        "static_analysis_findings": static_findings,
        "raw_analysis": analysis,
        "candidates_found": len(candidates),
        "verification_log": verification_log,
        "confirmed_issues": confirmed_issues,
    }


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
            "agent_review": review,
        })

    out_path = os.path.join(os.path.dirname(__file__), "..", "eval", "agent_results.json")
    save_results(results, out_path)


if __name__ == "__main__":
    main()
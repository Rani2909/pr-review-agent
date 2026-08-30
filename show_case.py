import json

with open("eval/agent_results.json") as f:
    d = json.load(f)

case = [c for c in d if c["id"] == "case_10"][0]
print(case["agent_review"]["raw_analysis"])
print("\n--- CONFIRMED ISSUES ---")
print(case["agent_review"]["confirmed_issues"])
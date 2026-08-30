import json

with open("eval/agent_results.json") as f:
    d = json.load(f)

case = [c for c in d if c["id"] == "case_09"][0]
print("STATIC ANALYSIS FOUND:")
print(case["agent_review"]["static_analysis_findings"])
print("\nCONFIRMED ISSUES:")
print(case["agent_review"]["confirmed_issues"])
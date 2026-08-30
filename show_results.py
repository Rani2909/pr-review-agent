import json

with open("eval/scorecard.json") as f:
    d = json.load(f)

print("BASELINE:")
for c in d["baseline"]["cases"]:
    print(f"  {c['id']}: {c['verdict']}")

print("AGENT:")
for c in d["agent"]["cases"]:
    print(f"  {c['id']}: {c['verdict']}")
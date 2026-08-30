\# Agent Trajectories



This document walks through the agent's full reasoning process on representative

cases, end to end: prompt in, model output, tool/verification calls, final

decision. Raw data for every case is in `eval/agent\_results.json`; this file

picks out the clearest examples to make the process easy to follow.



\---



\## Trajectory 1: A caught bug (case\_01 — pagination off-by-one)



\*\*Input diff given to the agent:\*\*

```python

def get\_page(items, page\_size, page\_num):

&#x20;   """Return the slice of items for the given page (1-indexed)."""

&#x20;   start = page\_num \* page\_size

&#x20;   end = start + page\_size

&#x20;   return items\[start:end]

```



\*\*Step 1 — Static analysis tool call.\*\* `run\_static\_analysis()` parses the code

with Python's `ast` module. No bare `except:` or mutable default arguments are

present, so it reports "no risky patterns detected" — this is passed to the model

as verified context.



\*\*Step 2 — Analysis call.\*\* The agent is prompted to explain intended behavior,

walk through the logic line by line, and list every divergence as a numbered

candidate. It correctly identifies that the docstring promises 1-indexed pages,

but `start = page\_num \* page\_size` treats `page\_num` as 0-indexed — so page 1

skips the first `page\_size` items.



\*\*Step 3 — Verification call.\*\* Each candidate from Step 2 is re-checked in a

separate call against the "routine input vs. deliberate misuse" standard. This

candidate is confirmed: calling `get\_page(items, 10, 1)` — a completely routine,

expected call — returns the wrong slice. That's a failure on realistic input, not

misuse, so it's confirmed as a real bug.



\*\*Result:\*\* ✅ Correctly flagged. Matches the planted ground-truth bug.



\---



\## Trajectory 2: A fixed false positive (case\_07 — clean `clamp()` function)



\*\*Input diff:\*\*

```python

def clamp(value, low, high):

&#x20;   """Clamp value to the inclusive range \[low, high]."""

&#x20;   if value < low:

&#x20;       return low

&#x20;   if value > high:

&#x20;       return high

&#x20;   return value

```



\*\*Step 1 — Static analysis.\*\* No risky patterns detected (clean ast walk).



\*\*Step 2 — Analysis call.\*\* The model correctly explains the function's intent

and logic, but also generates a candidate issue: "no validation that `low <= high`."



\*\*Step 3 — Verification call (final version).\*\* The verification prompt asks:

is this a failure on \*routine\* input, or does it only occur under caller misuse

(e.g. passing arguments in the wrong order)? The model correctly


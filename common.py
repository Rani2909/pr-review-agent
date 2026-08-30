"""Shared helpers used by baseline/run.py and agent/run.py."""
import os
import json
import glob
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_cases():
    """Load every case_*.json file in data/, sorted by id."""
    cases = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "case_*.json"))):
        with open(path) as f:
            cases.append(json.load(f))
    return cases


def get_client():
    """Create a Gemini client. Requires GEMINI_API_KEY in the environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Create a .env file or export it:\n"
            "  export GEMINI_API_KEY=your-key-here\n"
        )
    return genai.Client(api_key=api_key)


def call_model(client, prompt, max_tokens=600, max_retries=6):
    """Send a single prompt to Gemini and return the text response.
    Retries automatically on any transient error (server busy, dropped connection,
    timeouts) with increasing wait times."""
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            last_error = e
            wait = (attempt + 1) * 10
            print(f"  Request failed ({type(e).__name__}), attempt {attempt + 1}/{max_retries}, waiting {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Gemini API still failing after {max_retries} retries. Last error: {last_error}")


def save_results(results, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} results to {out_path}")
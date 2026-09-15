"""
Step 1: pull raw WHOOP data into memory and show what each record looks like.

Run:
    python src/pull_data.py

This does NOT do any analysis yet — it just fetches the last MONTHS_BACK
months of cycles, recovery, sleep, and workout records (paginating through
all pages automatically), prints one example of each so you can see the
real field names/shapes, and dumps the raw JSON to data/ for later steps.

This is a full re-pull, not an incremental update — every run replaces
data/raw_pull.json from scratch with everything WHOOP has for the range.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from whoop_client import WhoopClient, PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data"
MONTHS_BACK = 9


def show_sample(name: str, payload: dict):
    records = payload.get("records", [])
    print(f"\n=== {name}: {len(records)} record(s) ===")
    if records:
        print(json.dumps(records[0], indent=2))
    else:
        print("(no records in range)")


def main():
    client = WhoopClient()

    start = (datetime.now(timezone.utc) - timedelta(days=MONTHS_BACK * 30)).isoformat()
    print(f"Pulling all records since {start}...")

    profile = client.get_profile()
    body = client.get_body_measurements()
    cycles = client.get_cycles(start=start)
    recovery = client.get_recovery(start=start)
    sleep = client.get_sleep(start=start)
    workouts = client.get_workouts(start=start)

    print("=== profile ===")
    print(json.dumps(profile, indent=2))

    print("\n=== body measurements ===")
    print(json.dumps(body, indent=2))

    show_sample("cycles (daily strain)", cycles)
    show_sample("recovery (HRV, RHR, recovery %)", recovery)
    show_sample("sleep", sleep)
    show_sample("workouts", workouts)

    DATA_DIR.mkdir(exist_ok=True)
    dump = {
        "profile": profile,
        "body_measurements": body,
        "cycles": cycles,
        "recovery": recovery,
        "sleep": sleep,
        "workouts": workouts,
    }
    out_path = DATA_DIR / "raw_pull.json"
    out_path.write_text(json.dumps(dump, indent=2))
    print(f"\nSaved full raw pull to {out_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser(description="Inspect an existing VError run CSV")
parser.add_argument("csv_file", type=Path)
args = parser.parse_args()

with args.csv_file.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

def truth(v: str) -> bool:
    return str(v).lower() == "true"

passed = sum(truth(r["case_pass"]) for r in rows)
print(f"Overall: {passed}/{len(rows)} = {passed/len(rows):.1%}" if rows else "No rows")

by_bucket = Counter()
pass_bucket = Counter()
for r in rows:
    by_bucket[r["bucket"]] += 1
    if truth(r["case_pass"]):
        pass_bucket[r["bucket"]] += 1
for bucket, total in sorted(by_bucket.items()):
    print(f"{bucket:12s}: {pass_bucket[bucket]}/{total} = {pass_bucket[bucket]/total:.1%}")

print("\nFailed cases:")
for r in rows:
    if not truth(r["case_pass"]):
        dims = [k for k in ["route_correct", "diagnosis_correct", "grounding_correct", "pedagogical_safe", "next_action_correct", "state_safety"] if not truth(r[k])]
        print(f"- {r['case_id']}: {', '.join(dims)} {r['error']}")

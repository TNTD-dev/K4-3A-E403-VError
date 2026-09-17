from __future__ import annotations

import argparse
import csv
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("rater_a", type=Path)
parser.add_argument("rater_b", type=Path)
args = parser.parse_args()

FIELDS = ["pedagogical_safe", "grounding_supported"]

def load(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {r["case_id"]: r for r in csv.DictReader(f)}

a, b = load(args.rater_a), load(args.rater_b)
common = sorted(set(a) & set(b))
if not common:
    raise SystemExit("No common case_id")

comparisons = 0
agreements = 0
for cid in common:
    for field in FIELDS:
        va = a[cid].get(field, "").strip().lower()
        vb = b[cid].get(field, "").strip().lower()
        if not va or not vb:
            continue
        comparisons += 1
        agreements += va == vb

rate = agreements / comparisons if comparisons else 0.0
print(f"Common cases: {len(common)}")
print(f"Comparable judgments: {comparisons}")
print(f"Agreement: {agreements}/{comparisons} = {rate:.1%}")
print("PASS" if rate >= 0.80 else "REWRITE CRITERIA: agreement < 80%")

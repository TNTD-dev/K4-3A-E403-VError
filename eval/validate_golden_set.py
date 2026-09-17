from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "golden_set.json").read_text(encoding="utf-8"))
CASES = DATA["cases"]

errors: list[str] = []
ids = [c["id"] for c in CASES]
if len(ids) != len(set(ids)):
    errors.append("Duplicate case IDs")
if len(CASES) < 20:
    errors.append(f"Need >=20 cases, found {len(CASES)}")

bucket = Counter(c["bucket"] for c in CASES)
hard = Counter(c["hard_class"] for c in CASES if c["hard_class"] != "none")
prov = Counter(c["provenance"]["type"] for c in CASES)

if not (8 <= bucket["normal"] <= 10):
    errors.append(f"Normal cases must be 8-10, found {bucket['normal']}")
if not (2 <= bucket["rare"] <= 4):
    errors.append(f"Rare cases must be 2-4, found {bucket['rare']}")
for klass in ["source_truth", "ambiguous", "out_of_scope", "domain_specific"]:
    if hard[klass] < 2:
        errors.append(f"Need >=2 hard cases for {klass}, found {hard[klass]}")
if prov["chatlog_pattern_derived"] < 10:
    errors.append(
        f"Need >=10 chatlog-derived cases for rubric coverage, found {prov['chatlog_pattern_derived']}"
    )

GLOBAL_CITATIONS = {"D04-P07", "D04-P08", "D04-P10", "D04-P20"}
for case in CASES:
    exp = case["expected"]
    allowed = set(exp.get("allowed_citations", []))
    if not allowed.issubset(GLOBAL_CITATIONS):
        errors.append(f"{case['id']}: invalid citation in allowed_citations: {sorted(allowed - GLOBAL_CITATIONS)}")
    if exp.get("route") in {"clarify", "no-basis", "out-of-scope"} and allowed:
        errors.append(f"{case['id']}: safe route should normally have no citations")

print(f"Total cases: {len(CASES)}")
print("Buckets:", dict(bucket))
print("Hard classes:", dict(hard))
print("Provenance:", dict(prov))

if errors:
    print("\nFAIL:")
    for err in errors:
        print(" -", err)
    raise SystemExit(1)

print("\nPASS: golden set satisfies structural coverage checks.")

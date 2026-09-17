from __future__ import annotations

import argparse
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from adapter import call_http, call_python, normalize_response

ROOT = Path(__file__).resolve().parent
GLOBAL_CITATIONS = {"D04-P07", "D04-P08", "D04-P10", "D04-P20"}


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def grade(case: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    exp = case["expected"]
    route_correct = actual.get("route") == exp["route"]

    expected_m = exp.get("misconception_code")
    actual_m = actual.get("misconception_code") or None
    diagnosis_correct = actual_m == expected_m

    actual_citations = [str(x) for x in actual.get("citations", [])]
    allowed = set(exp.get("allowed_citations", []))
    all_whitelisted = all(c in GLOBAL_CITATIONS for c in actual_citations)
    all_supported = all(c in allowed for c in actual_citations)
    required_ok = (not exp.get("required_any_citation", False)) or bool(actual_citations)
    grounding_correct = all_whitelisted and all_supported and required_ok

    hint = norm_text(actual.get("hint_text", ""))
    forbidden = [norm_text(x) for x in exp.get("forbidden_phrases", [])]
    forbidden_hit = next((p for p in forbidden if p and p in hint), None)
    answer_revealed = actual.get("answer_revealed")
    reveal_violation = bool(exp.get("must_not_reveal_answer", False) and answer_revealed is True)
    pedagogical_safe = not forbidden_hit and not reveal_violation

    next_action = actual.get("next_action")
    allowed_actions = exp.get("allowed_next_actions", [])
    next_action_correct = (not allowed_actions) or next_action in allowed_actions

    state_safety = True
    state_notes = []
    for assertion in exp.get("state_assertions", []):
        field = assertion["field"]
        op = assertion["op"]
        value = assertion.get("value")
        got = actual.get(field)
        ok = True
        if op == "equals":
            ok = got == value
        elif op == "not_equals":
            ok = got != value
        elif op == "is_null":
            ok = got is None
        elif op == "not_contains":
            seq = got if isinstance(got, list) else [got]
            ok = value not in seq
        else:
            ok = False
        state_safety = state_safety and ok
        state_notes.append(f"{field} {op} {value!r}: {'PASS' if ok else f'FAIL(got={got!r})'}")

    case_pass = all([
        route_correct,
        diagnosis_correct,
        grounding_correct,
        pedagogical_safe,
        next_action_correct,
        state_safety,
    ])

    return {
        "case_pass": case_pass,
        "route_correct": route_correct,
        "diagnosis_correct": diagnosis_correct,
        "grounding_correct": grounding_correct,
        "pedagogical_safe": pedagogical_safe,
        "next_action_correct": next_action_correct,
        "state_safety": state_safety,
        "forbidden_hit": forbidden_hit or "",
        "state_notes": " | ".join(state_notes),
    }


def load_replay(path: Path) -> dict[str, dict[str, Any]]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        result[row["case_id"]] = normalize_response(row["response"])
    return result


def pct(n: int, d: int) -> float:
    return 0.0 if d == 0 else n / d


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["http", "python", "replay"], required=True)
    parser.add_argument("--responses", type=Path, help="JSONL file for replay mode")
    parser.add_argument("--case", action="append", help="Run only selected case id; repeat flag for multiple")
    args = parser.parse_args()

    suite = json.loads((ROOT / "golden_set.json").read_text(encoding="utf-8"))
    cases = suite["cases"]
    if args.case:
        wanted = set(args.case)
        cases = [c for c in cases if c["id"] in wanted]

    replay = {}
    if args.mode == "replay":
        if not args.responses:
            parser.error("--responses is required for replay mode")
        replay = load_replay(args.responses)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = ROOT / "results" / f"run_{stamp}.csv"
    trace_path = ROOT / "traces" / f"run_{stamp}.jsonl"

    rows = []
    for case in cases:
        start = time.perf_counter()
        error = ""
        try:
            if args.mode == "http":
                actual = call_http(case["input"])
            elif args.mode == "python":
                actual = call_python(case["input"])
            else:
                if case["id"] not in replay:
                    raise KeyError(f"No replay response for {case['id']}")
                actual = replay[case["id"]]
            graded = grade(case, actual)
        except Exception as exc:
            actual = {"route": None, "misconception_code": None, "citations": [], "hint_text": "", "next_action": None}
            graded = {
                "case_pass": False,
                "route_correct": False,
                "diagnosis_correct": False,
                "grounding_correct": False,
                "pedagogical_safe": False,
                "next_action_correct": False,
                "state_safety": False,
                "forbidden_hit": "",
                "state_notes": "",
            }
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        trace = {
            "case_id": case["id"],
            "input": case["input"],
            "expected": case["expected"],
            "actual": actual,
            "graded": graded,
            "error": error,
            "latency_ms": latency_ms,
        }
        with trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")

        rows.append({
            "case_id": case["id"],
            "bucket": case["bucket"],
            "hard_class": case["hard_class"],
            "provenance": case["provenance"]["type"],
            "expected_route": case["expected"]["route"],
            "actual_route": actual.get("route"),
            "expected_misconception": case["expected"].get("misconception_code"),
            "actual_misconception": actual.get("misconception_code"),
            "actual_citations": "|".join(actual.get("citations", [])),
            "route_correct": graded["route_correct"],
            "diagnosis_correct": graded["diagnosis_correct"],
            "grounding_correct": graded["grounding_correct"],
            "pedagogical_safe": graded["pedagogical_safe"],
            "next_action_correct": graded["next_action_correct"],
            "state_safety": graded["state_safety"],
            "case_pass": graded["case_pass"],
            "latency_ms": latency_ms,
            "error": error,
        })
        print(f"{case['id']}: {'PASS' if graded['case_pass'] else 'FAIL'}")

    fields = list(rows[0].keys()) if rows else []
    with result_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    quality = json.loads((ROOT / "quality_bar.json").read_text(encoding="utf-8"))
    total = len(rows)
    passed = sum(r["case_pass"] is True for r in rows)
    diag_cases = [r for r in rows if r["expected_misconception"]]
    safe_cases = [r for r in rows if r["expected_route"] in {"clarify", "no-basis", "out-of-scope"}]
    state_cases = [r for r in rows if r["bucket"] == "integration"]

    emitted_citations = 0
    valid_citations = 0
    leakage_count = 0
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        trace = json.loads(line)
        actual_cits = trace["actual"].get("citations", [])
        emitted_citations += len(actual_cits)
        allowed = set(trace["expected"].get("allowed_citations", []))
        valid_citations += sum(c in allowed and c in GLOBAL_CITATIONS for c in actual_cits)
        if not trace["graded"]["pedagogical_safe"]:
            leakage_count += 1

    metrics = {
        "overall_case_pass_rate": pct(passed, total),
        "route_accuracy": pct(sum(r["route_correct"] is True for r in rows), total),
        "diagnosis_accuracy": pct(sum(r["diagnosis_correct"] is True for r in diag_cases), len(diag_cases)),
        "citation_precision": 1.0 if emitted_citations == 0 else valid_citations / emitted_citations,
        "safe_routing_accuracy": pct(sum(r["case_pass"] is True for r in safe_cases), len(safe_cases)),
        "hint_leakage_rate": pct(leakage_count, total),
        "state_safety_pass_rate": pct(sum(r["state_safety"] is True for r in state_cases), len(state_cases)),
    }

    checks = {
        "overall_case_pass_rate": metrics["overall_case_pass_rate"] >= quality["overall_case_pass_rate_min"],
        "diagnosis_accuracy": metrics["diagnosis_accuracy"] >= quality["diagnosis_accuracy_min"],
        "route_accuracy": metrics["route_accuracy"] >= quality["route_accuracy_min"],
        "citation_precision": metrics["citation_precision"] >= quality["citation_precision_min"],
        "safe_routing_accuracy": metrics["safe_routing_accuracy"] >= quality["safe_routing_accuracy_min"],
        "hint_leakage_rate": metrics["hint_leakage_rate"] <= quality["hint_leakage_rate_max"],
        "state_safety_pass_rate": metrics["state_safety_pass_rate"] >= quality["state_safety_pass_rate_min"],
    }

    summary_path = ROOT / "results" / f"run_{stamp}_summary.md"
    lines = [
        f"# VError eval summary — {stamp}",
        "",
        f"Cases: **{passed}/{total} PASS ({metrics['overall_case_pass_rate']:.1%})**",
        "",
        "| Metric | Result | Bar | Status |",
        "|---|---:|---:|:---:|",
        f"| Overall case pass | {metrics['overall_case_pass_rate']:.1%} | >= {quality['overall_case_pass_rate_min']:.0%} | {'PASS' if checks['overall_case_pass_rate'] else 'FAIL'} |",
        f"| Route accuracy | {metrics['route_accuracy']:.1%} | >= {quality['route_accuracy_min']:.0%} | {'PASS' if checks['route_accuracy'] else 'FAIL'} |",
        f"| Diagnosis accuracy | {metrics['diagnosis_accuracy']:.1%} | >= {quality['diagnosis_accuracy_min']:.0%} | {'PASS' if checks['diagnosis_accuracy'] else 'FAIL'} |",
        f"| Citation precision | {metrics['citation_precision']:.1%} | >= {quality['citation_precision_min']:.0%} | {'PASS' if checks['citation_precision'] else 'FAIL'} |",
        f"| Safe routing | {metrics['safe_routing_accuracy']:.1%} | >= {quality['safe_routing_accuracy_min']:.0%} | {'PASS' if checks['safe_routing_accuracy'] else 'FAIL'} |",
        f"| Hint leakage | {metrics['hint_leakage_rate']:.1%} | <= {quality['hint_leakage_rate_max']:.0%} | {'PASS' if checks['hint_leakage_rate'] else 'FAIL'} |",
        f"| State safety | {metrics['state_safety_pass_rate']:.1%} | >= {quality['state_safety_pass_rate_min']:.0%} | {'PASS' if checks['state_safety_pass_rate'] else 'FAIL'} |",
        "",
        "## Failed cases",
        "",
    ]
    failed = [r for r in rows if not r["case_pass"]]
    if failed:
        for r in failed:
            lines.append(f"- `{r['case_id']}` — route={r['actual_route']!r}, misconception={r['actual_misconception']!r}, error={r['error'] or 'dimension failure'}")
    else:
        lines.append("- None")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nResults: {result_path}")
    print(f"Summary: {summary_path}")
    print(f"Traces:  {trace_path}")


if __name__ == "__main__":
    main()

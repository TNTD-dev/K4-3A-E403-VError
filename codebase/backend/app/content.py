"""Reviewed lesson content. Only this module and the database know the answer key."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
ITEM_ID = "prompt-clarity-01"
ITEM_VERSION = "2026-09-16.2"
SOURCE_VERSION = "day04-prompt-v1"

with (CONTENT / "item.prompt-clarity.v1.json").open(encoding="utf-8") as f:
    PUBLIC_ITEM: dict[str, Any] = json.load(f)
with (CONTENT / "sources.v1.json").open(encoding="utf-8") as f:
    APPROVED_SOURCES: list[dict[str, Any]] = json.load(f)
with (CONTENT / "citation-support.v1.json").open(encoding="utf-8") as f:
    CITATION_SUPPORT: dict[str, list[str]] = json.load(f)

ANSWER_KEY = {
    "expected_concept": "specificity_over_length",
    "required_explain_claim_ids": [
        "specificity_beats_cleverness", "task_and_format_first", "extra_prompt_can_add_cost_or_noise"
    ],
    "transfer_expected": "clear_task_and_format",
    "allowed_sources": CITATION_SUPPORT,
}

def source_catalog() -> list[dict[str, Any]]:
    return [dict(source) for source in APPROVED_SOURCES]

def source(source_id: str) -> dict[str, Any] | None:
    return next((item for item in APPROVED_SOURCES if item["sourceId"] == source_id), None)

def source_version_info() -> dict[str, Any]:
    return {"itemId": ITEM_ID, "itemVersion": ITEM_VERSION, "sourceVersion": SOURCE_VERSION,
            "sources": [item["sourceId"] for item in APPROVED_SOURCES]}

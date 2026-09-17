"""Reviewed lesson content. Only this module and the database know the answer keys."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .sections import SECTIONS, section, section_by_item

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
SOURCE_VERSION = "day04-prompt-v2"
DEFAULT_LEARNER = "local-demo"

with (CONTENT / "items.v1.json").open(encoding="utf-8") as f:
    ITEMS: list[dict[str, Any]] = json.load(f)
with (CONTENT / "sources.v1.json").open(encoding="utf-8") as f:
    APPROVED_SOURCES: list[dict[str, Any]] = json.load(f)
with (CONTENT / "citation-support.v1.json").open(encoding="utf-8") as f:
    CITATION_SUPPORT: dict[str, list[str]] = json.load(f)
with (CONTENT / "answer-keys.v1.json").open(encoding="utf-8") as f:
    ANSWER_KEYS: dict[str, dict[str, Any]] = json.load(f)

ITEMS_BY_ID = {item["itemId"]: item for item in ITEMS}
ITEMS_BY_SECTION = {item["sectionId"]: item for item in ITEMS}

ITEM_ID = SECTIONS[0]["itemId"]
ITEM_VERSION = ITEMS_BY_ID[ITEM_ID]["version"]


def public_item_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "itemId": item["itemId"],
        "sectionId": item["sectionId"],
        "version": item["version"],
        "title": item["title"],
        "statement": item["statement"],
        "taskText": item["taskText"],
        "stakes": item["stakes"],
        "responseMode": "free_text_plus_reasoning",
        "scope": "day04_prompt_tool_calling",
        "day": {
            "dayId": "day-04",
            "title": "Prompt Engineering & Tool Calling",
            "label": "Bài 4 · DAY04",
            "materials": [
                {"type": "slides", "label": "Slide deck", "status": "available", "locator": "PDF 43 pages"},
                {
                    "type": "lecture_video",
                    "label": "Lecture video",
                    "status": "available",
                    "locatorStatus": "unavailable",
                    "note": "Video timestamp unavailable for the provided PDF",
                },
            ],
        },
        "sources": list(item["sources"]),
        "activeLayer": "Attempt trước khi mở slide phần này; sau lần thử đầu mở đúng trang PDF đã duyệt.",
        "transfer": dict(item["transfer"]),
    }


PUBLIC_ITEM = public_item_view(ITEMS_BY_ID[ITEM_ID])
ANSWER_KEY = {
    "expected_concept": ANSWER_KEYS[ITEM_ID]["expectedConcept"],
    "required_explain_claim_ids": ANSWER_KEYS[ITEM_ID]["requiredExplainClaimIds"],
    "transfer_expected": ANSWER_KEYS[ITEM_ID]["transferExpected"],
    "allowed_sources": ANSWER_KEYS[ITEM_ID]["misconceptions"],
}


def item_for_section(section_id: str) -> dict[str, Any] | None:
    raw = ITEMS_BY_SECTION.get(section_id)
    return public_item_view(raw) if raw else None


def item_by_id(item_id: str) -> dict[str, Any] | None:
    raw = ITEMS_BY_ID.get(item_id)
    return public_item_view(raw) if raw else None


def answer_key_for(item_id: str) -> dict[str, Any]:
    key = ANSWER_KEYS[item_id]
    return {
        "expected_concept": key["expectedConcept"],
        "required_explain_claim_ids": key["requiredExplainClaimIds"],
        "transfer_expected": key["transferExpected"],
        "allowed_sources": key["misconceptions"],
    }


def sources_for_item(item_id: str) -> list[dict[str, Any]]:
    raw = ITEMS_BY_ID[item_id]
    wanted = set(raw["sources"])
    return [dict(source) for source in APPROVED_SOURCES if source["sourceId"] in wanted]


def approved_pages(item_id: str) -> set[int]:
    """PDF pages an item's approved sources actually point to, for verifying a learner's
    claimed page citation before treating it as grounded evidence."""
    return {
        location["page"]
        for source in sources_for_item(item_id)
        for location in source.get("approvedLocations", [])
        if location.get("kind") == "slide" and location.get("page")
    }


def source_catalog(item_id: str | None = None) -> list[dict[str, Any]]:
    if item_id:
        return sources_for_item(item_id)
    return [dict(source) for source in APPROVED_SOURCES]


def source(source_id: str) -> dict[str, Any] | None:
    return next((item for item in APPROVED_SOURCES if item["sourceId"] == source_id), None)


def source_version_info(item_id: str | None = None) -> dict[str, Any]:
    item = ITEMS_BY_ID.get(item_id or ITEM_ID, ITEMS_BY_ID[ITEM_ID])
    return {
        "itemId": item["itemId"],
        "itemVersion": item["version"],
        "sourceVersion": SOURCE_VERSION,
        "sources": list(item["sources"]),
    }


def resolve_section_and_item(section_id: str | None = None, item_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if section_id:
        meta = section(section_id)
        if not meta:
            raise KeyError("SECTION_NOT_FOUND")
        item = item_for_section(section_id)
        if not item:
            raise KeyError("ITEM_NOT_FOUND")
        return meta, item
    if item_id:
        meta = section_by_item(item_id)
        item = item_by_id(item_id)
        if not meta or not item:
            raise KeyError("ITEM_NOT_FOUND")
        return meta, item
    meta = SECTIONS[0]
    return meta, item_for_section(meta["sectionId"])  # type: ignore[return-value]

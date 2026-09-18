"""Slide Agent: reads the deck, finds section title slides and grounds key-slide explanations.

Boundaries (same rule as the Question Agent):
- The model may *locate* title slides and *word* an explanation.
- Key slides always come from the reviewed sources of the section item; the model
  can only pick a focus page among them, never add a page or a citation.
- Every model output is validated; anything invalid falls back to the
  deterministic reader and the response says so.
"""
from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
from pathlib import Path
from typing import Any

from .content import ITEMS_BY_SECTION, source
from .sections import SECTIONS

TITLE_PATTERN = re.compile(r"^\s*0?(\d{1,2})\s+\S")
TITLE_MAX_CHARS = 200
MIN_MATCH = 0.35


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _squash(text: str) -> str:
    # pypdf output breaks words ("T ool") and may split diacritics, so compare
    # lowercase letters/digits only, without combining marks or spaces.
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if ch.isalnum())


def _grams(text: str, size: int = 4) -> set[str]:
    squashed = _squash(text)
    return {squashed[i : i + size] for i in range(max(len(squashed) - size + 1, 0))}


def match_score(excerpt: str, page_text: str) -> float:
    wanted = _grams(excerpt)
    return len(wanted & _grams(page_text)) / len(wanted) if wanted else 0.0


def extract_pages(pdf_path: Path) -> list[str]:
    from pypdf import PdfReader

    return [_clean(page.extract_text()) for page in PdfReader(str(pdf_path)).pages]


def heuristic_title_pages(pages: list[str]) -> dict[int, int]:
    """Divider slides in this deck are short and start with the section number (01, 02...)."""
    found: dict[int, int] = {}
    for index, text in enumerate(pages, start=1):
        match = TITLE_PATTERN.match(text)
        if match and len(text) <= TITLE_MAX_CHARS:
            number = int(match.group(1))
            if 1 <= number <= len(SECTIONS) and number not in found:
                found[number] = index
    return found


def valid_title_pages(title_pages: dict[int, int], pages: list[str]) -> bool:
    numbers = [meta["number"] for meta in SECTIONS]
    if sorted(title_pages) != numbers:
        return False
    ordered = [title_pages[n] for n in numbers]
    if any(page < 1 or page > len(pages) for page in ordered):
        return False
    if any(later <= earlier for earlier, later in zip(ordered, ordered[1:])):
        return False
    # A divider slide carries little text; long pages are content slides.
    return all(len(pages[page - 1]) <= TITLE_MAX_CHARS + 60 for page in ordered)


def _declared_page(src: dict[str, Any]) -> int | None:
    return next(
        (loc.get("page") for loc in src.get("approvedLocations", []) if loc.get("kind") == "slide" and loc.get("page")),
        None,
    )


def key_slides_for(section_id: str, start: int, end: int, pages: list[str]) -> list[dict[str, Any]]:
    """Resolve each reviewed source excerpt to the slide that actually contains it."""
    item = ITEMS_BY_SECTION.get(section_id)
    if not item:
        return []
    slides: dict[int, dict[str, Any]] = {}
    for source_id in item["sources"]:
        src = source(source_id)
        if not src:
            continue
        declared = _declared_page(src)
        in_section = [(page, match_score(src["excerpt"], pages[page - 1])) for page in range(start, end + 1)]
        page, score = max(in_section, key=lambda pair: pair[1]) if in_section else (declared or start, 0.0)
        grounded = score >= MIN_MATCH
        if not grounded and declared and 1 <= declared <= len(pages):
            page = declared
        entry = slides.setdefault(
            page,
            {"page": page, "sourceIds": [], "declaredPages": [], "excerpts": [], "matchScore": 0.0, "grounded": False},
        )
        entry["sourceIds"].append(source_id)
        entry["declaredPages"].append(declared)
        entry["excerpts"].append(src["excerpt"])
        entry["matchScore"] = round(max(entry["matchScore"], score), 2)
        entry["grounded"] = entry["grounded"] or grounded
    return [slides[page] for page in sorted(slides)]


def _responses_json(name: str, schema: dict[str, Any], system: str, payload: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=25, max_retries=1)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_output_tokens=max_tokens,
        text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )
    return json.loads(response.output_text or "{}")


def _safe_reason(error: Exception) -> str:
    detail = str(error).replace(os.getenv("OPENAI_API_KEY", "") or "\0", "[redacted]")
    return f"{type(error).__name__}: {' '.join(detail.split())[:160]}".rstrip(": ")


OUTLINE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sections"],
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["number", "titlePage", "title"],
                "properties": {
                    "number": {"type": "integer"},
                    "titlePage": {"type": "integer"},
                    "title": {"type": "string"},
                },
            },
        }
    },
}

INSIGHT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "explanation", "keyPoints", "focusPage", "whyThisSlide", "reflectionQuestion"],
    "properties": {
        "headline": {"type": "string"},
        "explanation": {"type": "string"},
        "keyPoints": {"type": "array", "items": {"type": "string"}},
        "focusPage": {"type": "integer"},
        "whyThisSlide": {"type": "string"},
        "reflectionQuestion": {"type": "string"},
    },
}


def _clip(text: Any, limit: int) -> str:
    value = _clean(str(text or ""))
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


class SlideAgent:
    def __init__(self, pdf_path: Path | None, mode: str = "offline"):
        self.pdf_path = pdf_path
        self.mode = mode
        self._pages: list[str] | None = None
        self._outline: dict[str, Any] | None = None
        self._insights: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._lock = threading.Lock()

    @property
    def live(self) -> bool:
        return self.mode == "live" and bool(os.getenv("OPENAI_API_KEY"))

    def pages(self) -> list[str]:
        if self._pages is None:
            if not self.pdf_path or not self.pdf_path.exists():
                raise FileNotFoundError("PDF_NOT_FOUND")
            self._pages = extract_pages(self.pdf_path)
        return self._pages

    # ------------------------------------------------------------------ outline
    def reset(self) -> None:
        """Drop cached outline and insights so the next read analyses the deck again."""
        with self._lock:
            self._outline = None
            self._insights.clear()

    def outline(self, refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            if self._outline is None or refresh:
                self._outline = self._build_outline()
            return self._outline

    def _detect_with_model(self, pages: list[str]) -> dict[int, int]:
        parsed = _responses_json(
            "deck_outline",
            OUTLINE_SCHEMA,
            (
                "Bạn là Slide Agent của VLearn. Đọc văn bản trích từ từng trang slide và xác định slide "
                "giới thiệu tiêu đề (slide chuyển phần, thường có số thứ tự như 01, 02 và rất ít chữ) "
                "cho từng phần trong mục lục. Chỉ trả về số trang có trong dữ liệu; không bịa trang."
            ),
            {
                "agenda": [{"number": meta["number"], "title": meta["title"]} for meta in SECTIONS],
                "pages": [{"page": index, "text": text[:180]} for index, text in enumerate(pages, start=1)],
            },
            max_tokens=700,
        )
        return {int(entry["number"]): int(entry["titlePage"]) for entry in parsed.get("sections", [])}

    def _build_outline(self) -> dict[str, Any]:
        pages = self.pages()
        heuristic = heuristic_title_pages(pages)
        title_pages, provider, model, fallback = heuristic, "deterministic", None, None
        if self.live:
            try:
                proposed = self._detect_with_model(pages)
                if valid_title_pages(proposed, pages):
                    title_pages, provider, model = proposed, "openai", os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                else:
                    fallback = "model_outline_rejected"
            except Exception as error:  # provider/network errors must not break the reader
                fallback = _safe_reason(error)
        elif self.mode == "live":
            fallback = "missing_api_key"

        if not valid_title_pages(title_pages, pages):
            # Deck without recognisable dividers: fall back to the reviewed table of contents.
            title_pages = {meta["number"]: meta["pages"][0] for meta in SECTIONS}
            provider, model = "reviewed_toc", None
            fallback = fallback or "title_slides_not_detected"

        total = len(pages)
        sections = []
        for meta in SECTIONS:
            number = meta["number"]
            title_page = title_pages[number]
            following = title_pages.get(number + 1)
            end_page = following - 1 if following else total
            sections.append(
                {
                    "sectionId": meta["sectionId"],
                    "number": number,
                    "title": meta["title"],
                    "titlePage": title_page,
                    "titleText": _clip(pages[title_page - 1], 160),
                    "startPage": title_page,
                    "quizPage": min(title_page + 1, end_page),
                    "endPage": end_page,
                    "keySlides": key_slides_for(meta["sectionId"], title_page, end_page, pages),
                }
            )
        return {
            "pdf": "/prompt-engineering-tool-calling.pdf",
            "totalPages": total,
            "introPages": [1, sections[0]["titlePage"] - 1] if sections and sections[0]["titlePage"] > 1 else None,
            "sections": sections,
            "agent": {
                "provider": provider,
                "model": model,
                "generated": provider == "openai",
                "fallbackReason": fallback,
                "heuristicAgrees": all(heuristic.get(s["number"]) == s["titlePage"] for s in sections),
            },
        }

    def section(self, section_id: str) -> dict[str, Any] | None:
        return next((s for s in self.outline()["sections"] if s["sectionId"] == section_id), None)

    # ------------------------------------------------------------------ insight
    def key_insight(self, section_id: str, attempt: dict[str, Any] | None = None) -> dict[str, Any]:
        outline_section = self.section(section_id)
        meta = next((m for m in SECTIONS if m["sectionId"] == section_id), None)
        if not outline_section or not meta:
            raise KeyError("SECTION_NOT_FOUND")
        key_slides = outline_section["keySlides"]
        cache_key = (section_id, attempt.get("id") if attempt else None, self.live)
        if cache_key in self._insights:
            return self._insights[cache_key]

        pages = self.pages()
        allowed_pages = [slide["page"] for slide in key_slides] or [outline_section["quizPage"]]
        reviewed = self._reviewed_insight(meta, key_slides, allowed_pages, attempt)
        result = {"keySlides": key_slides, "insight": reviewed, "generation": {
            "provider": "reviewed", "model": None, "generated": False,
            "fallbackReason": "missing_api_key" if self.mode == "live" and not self.live else None,
        }}
        if self.live:
            try:
                parsed = _responses_json(
                    "key_insight",
                    INSIGHT_SCHEMA,
                    (
                        "Bạn là Explanation Agent của VLearn, viết tiếng Việt cho học viên vừa làm pre-quiz. "
                        "Giải thích kiến thức trọng tâm CHỈ dựa trên slideText và approvedExcerpts. "
                        "Nếu có learnerAttempt, chỉ ra giả định trong câu trả lời cần đối chiếu với slide, giọng tôn trọng, "
                        "không chấm điểm. Không thêm kiến thức ngoài slide, không giải hộ case chuyển giao. "
                        "focusPage phải là một số trong allowedPages. keyPoints gồm 2-4 ý ngắn. "
                        "explanation tối đa 4 câu. reflectionQuestion là một câu hỏi tự kiểm tra ngắn."
                    ),
                    {
                        "section": {"title": meta["title"], "summary": meta["summary"]},
                        "allowedPages": allowed_pages,
                        "keySlides": [
                            {"page": s["page"], "slideText": pages[s["page"] - 1][:900], "approvedExcerpts": s["excerpts"]}
                            for s in key_slides
                        ],
                        "learnerAttempt": self._attempt_payload(attempt),
                    },
                    max_tokens=900,
                )
                result["insight"] = self._validate_insight(parsed, reviewed, allowed_pages)
                result["generation"] = {
                    "provider": "openai",
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "generated": True,
                    "fallbackReason": None,
                }
            except Exception as error:
                result["generation"]["fallbackReason"] = _safe_reason(error)
        self._insights[cache_key] = result
        return result

    @staticmethod
    def _attempt_payload(attempt: dict[str, Any] | None) -> dict[str, Any] | None:
        if not attempt:
            return None
        return {
            "answer": _clip(attempt.get("answer_text"), 500),
            "explanation": _clip(attempt.get("explanation"), 500),
            "objectiveStatus": attempt.get("objective_status"),
            "diagnosisCode": attempt.get("error_code"),
        }

    @staticmethod
    def _reviewed_insight(meta: dict[str, Any], key_slides: list[dict[str, Any]], allowed_pages: list[int], attempt: dict[str, Any] | None) -> dict[str, Any]:
        points = [excerpt for slide in key_slides for excerpt in slide["excerpts"]][:4]
        focus = allowed_pages[0]
        pages_label = ", ".join(f"trang {page}" for page in allowed_pages)
        opener = (
            "Câu trả lời của bạn đang dựa trên một giả định cần đối chiếu lại với slide. "
            if attempt and attempt.get("objective_status") == "incorrect"
            else ""
        )
        return {
            "headline": meta["coreClaim"],
            "explanation": f"{opener}Phần “{meta['title']}” chốt ý ở {pages_label}: {meta['summary']}",
            "keyPoints": points,
            "focusPage": focus,
            "whyThisSlide": f"Trang {focus} chứa nguồn đã duyệt mà pre-quiz của phần này dựa vào.",
            "reflectionQuestion": "Sau khi đọc slide, điều kiện nào khiến phát biểu trong pre-quiz không còn đúng?",
        }

    @staticmethod
    def _validate_insight(parsed: dict[str, Any], reviewed: dict[str, Any], allowed_pages: list[int]) -> dict[str, Any]:
        points = [_clip(point, 180) for point in parsed.get("keyPoints", []) if _clean(str(point))][:4]
        focus = parsed.get("focusPage")
        headline = _clip(parsed.get("headline"), 140)
        explanation = _clip(parsed.get("explanation"), 700)
        if not headline or not explanation or not points:
            raise ValueError("insight_incomplete")
        return {
            "headline": headline,
            "explanation": explanation,
            "keyPoints": points,
            "focusPage": focus if focus in allowed_pages else reviewed["focusPage"],
            "whyThisSlide": _clip(parsed.get("whyThisSlide"), 260) or reviewed["whyThisSlide"],
            "reflectionQuestion": _clip(parsed.get("reflectionQuestion"), 240) or reviewed["reflectionQuestion"],
        }

"""Day 04 table of contents and public section metadata."""
from __future__ import annotations
from typing import Any

SECTIONS: list[dict[str, Any]] = [
    {
        "sectionId": "prompt-fundamentals",
        "number": 1,
        "title": "Prompt fundamentals",
        "pages": [6, 10],
        "itemId": "day04-s01-specificity",
        "summary": "Prompt là interface giữa ý định và hành vi model.",
        "coreClaim": "Specificity beats cleverness; Task + Format trước, Role/Context có điều kiện.",
    },
    {
        "sectionId": "advanced-prompting",
        "number": 2,
        "title": "Advanced prompting techniques",
        "pages": [11, 14],
        "itemId": "day04-s02-technique-order",
        "summary": "Dùng kỹ thuật nâng cao khi chúng tạo cải thiện thật sự.",
        "coreClaim": "Thứ tự thực dụng: zero-shot → few-shot → CoT; CoT không phải mặc định.",
    },
    {
        "sectionId": "system-prompts",
        "number": 3,
        "title": "System prompt engineering",
        "pages": [15, 17],
        "itemId": "day04-s03-system-policy",
        "summary": "Rules, boundaries và output contract cho agent production.",
        "coreClaim": "System prompt là policy layer: boundary rõ thì hành vi dễ predict.",
    },
    {
        "sectionId": "context-engineering",
        "number": 4,
        "title": "Context engineering",
        "pages": [18, 21],
        "itemId": "day04-s04-context-select",
        "summary": "Chọn context cần thiết thay vì nhét mọi thứ.",
        "coreClaim": "Quan trọng là chọn đúng context, không phải nhét bao nhiêu context.",
    },
    {
        "sectionId": "tool-calling",
        "number": 5,
        "title": "Tool calling",
        "pages": [22, 26],
        "itemId": "day04-s05-tool-loop",
        "summary": "Vòng lặp model, tool và kết quả quay lại model.",
        "coreClaim": "Model không tự chạy tool; app nhận request, chạy tool, gửi kết quả lại.",
    },
    {
        "sectionId": "tool-design",
        "number": 6,
        "title": "Design principles cho tools",
        "pages": [27, 31],
        "itemId": "day04-s06-tool-granularity",
        "summary": "Schema rõ, error có nghĩa và boundary an toàn.",
        "coreClaim": "Tool tốt là software interface: single responsibility, granularity hợp lý.",
    },
    {
        "sectionId": "parallel-patterns",
        "number": 7,
        "title": "Parallel tool calls & patterns",
        "pages": [32, 35],
        "itemId": "day04-s07-parallel-deps",
        "summary": "Chaining, parallel fetch và merge kết quả.",
        "coreClaim": "Chỉ song song khi không phụ thuộc dữ liệu; control flow quan trọng hơn tốc độ.",
    },
    {
        "sectionId": "lab-deliverable",
        "number": 8,
        "title": "Lab 4 + deliverable cuối buổi",
        "pages": [36, 43],
        "itemId": "day04-s08-lab-evidence",
        "summary": "Agent script, system prompt, tools và test questions.",
        "coreClaim": "Deliverable cần agent + system prompt + 2 tools + 5 test + ghi chú lỗi.",
    },
]


def section(section_id: str) -> dict[str, Any] | None:
    return next((item for item in SECTIONS if item["sectionId"] == section_id), None)


def section_by_item(item_id: str) -> dict[str, Any] | None:
    return next((item for item in SECTIONS if item["itemId"] == item_id), None)


def next_section(section_id: str) -> dict[str, Any] | None:
    current = section(section_id)
    if not current:
        return None
    return next((item for item in SECTIONS if item["number"] == current["number"] + 1), None)


def first_section_id() -> str:
    return SECTIONS[0]["sectionId"]

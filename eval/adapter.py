"""Adapters for evaluating VError without coupling the golden set to one app stack."""
from __future__ import annotations

import importlib
import json
import os
import urllib.request
from typing import Any, Callable

ROUTE_ALIASES = {
    "diagnosis": "diagnose",
    "misconception": "diagnose",
    "pass": "correct",
    "ok": "correct",
    "low_confidence": "low-confidence",
    "lowconfidence": "low-confidence",
    "no_basis": "no-basis",
    "source_review": "no-basis",
    "out_of_scope": "out-of-scope",
    "technical_error": "technical-error",
}


def normalize_route(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("_", "-").replace(" ", "-")
    return ROUTE_ALIASES.get(text, text)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def normalize_response(raw: Any) -> dict[str, Any]:
    """Map prototype output to the canonical eval contract.

    If your app uses different field names, edit only this function.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {
                "route": None,
                "misconception_code": None,
                "citations": [],
                "hint_text": raw,
                "next_action": None,
                "answer_revealed": None,
                "raw_text_only": True,
            }
    if not isinstance(raw, dict):
        raise TypeError(f"Expected dict/JSON object, got {type(raw).__name__}")

    diagnosis = raw.get("diagnosis") if isinstance(raw.get("diagnosis"), dict) else {}
    feedback = raw.get("feedback") if isinstance(raw.get("feedback"), dict) else {}

    misconception = (
        raw.get("misconception_code")
        or raw.get("misconception")
        or diagnosis.get("misconception_code")
        or diagnosis.get("code")
    )
    citations = (
        raw.get("citations")
        or raw.get("citation")
        or diagnosis.get("citations")
        or feedback.get("citations")
    )
    hint_text = (
        raw.get("hint_text")
        or raw.get("hint")
        or feedback.get("hint")
        or raw.get("message")
        or ""
    )
    route = (
        raw.get("route")
        or raw.get("status")
        or diagnosis.get("route")
        or feedback.get("route")
    )
    next_action = raw.get("next_action") or feedback.get("next_action")

    return {
        **raw,
        "route": normalize_route(route),
        "misconception_code": str(misconception).strip() if misconception else None,
        "citations": _as_list(citations),
        "hint_text": str(hint_text or ""),
        "next_action": str(next_action).strip() if next_action else None,
        "answer_revealed": raw.get("answer_revealed", feedback.get("answer_revealed")),
    }


def call_http(payload: dict[str, Any]) -> dict[str, Any]:
    url = os.environ.get("VERROR_EVAL_URL")
    if not url:
        raise RuntimeError("Set VERROR_EVAL_URL for --mode http")
    timeout = float(os.environ.get("VERROR_EVAL_TIMEOUT", "30"))
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))
    return normalize_response(raw)


def _load_callable(path: str) -> Callable[[dict[str, Any]], Any]:
    if ":" not in path:
        raise ValueError("VERROR_EVAL_CALLABLE must be module:function")
    module_name, func_name = path.split(":", 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name)
    if not callable(func):
        raise TypeError(f"{path} is not callable")
    return func


def call_python(payload: dict[str, Any]) -> dict[str, Any]:
    path = os.environ.get("VERROR_EVAL_CALLABLE")
    if not path:
        raise RuntimeError("Set VERROR_EVAL_CALLABLE=module:function for --mode python")
    func = _load_callable(path)
    return normalize_response(func(payload))

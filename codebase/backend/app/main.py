from __future__ import annotations
import os
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .coach import Coach
from .content import DEFAULT_LEARNER, item_by_id, item_for_section, source, source_catalog, source_version_info
from .db import Store
from .orchestrator import DomainError, Orchestrator
from .schemas import AttemptBody, CreateSessionBody, ExplainBody, HintBody, StateVersionBody, TransferBody
from .sections import SECTIONS, section

ROOT = Path(__file__).resolve().parents[2]
mode = os.getenv("MODEL_MODE", "offline")
store = Store(os.getenv("SQLITE_PATH", str(ROOT / "verror.sqlite")))
api = Orchestrator(store, Coach(mode), mode, DEFAULT_LEARNER)
app = FastAPI(title="VError D2 API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error(_: Request, error: DomainError):
    return JSONResponse(status_code=error.status, content={"error": error.code, "message": error.message})


@app.get("/healthz")
def healthz():
    return {"ok": True, "mode": mode}


@app.get("/readyz")
def readyz():
    return {"ok": True, "mode": mode, "fixture": source_version_info(), "sqlite": "writable", "sections": len(SECTIONS)}


@app.get("/api/v1/sections")
def sections():
    return api.sections()


@app.post("/api/v1/sessions", status_code=201)
def create_session(body: CreateSessionBody):
    if body.itemId == "prompt-clarity-01":
        # Legacy alias from the single-item prototype maps to section 1.
        return api.create("prompt-fundamentals")
    return api.create(body.sectionId, body.itemId)


@app.get("/api/v1/items/{item_id}")
def get_item(item_id: str):
    if item_id == "prompt-clarity-01":
        item_id = SECTIONS[0]["itemId"]
    item = item_by_id(item_id)
    if not item:
        raise HTTPException(404, "ITEM_NOT_FOUND")
    return {"item": item, "sourceVersion": source_version_info(item_id)["sourceVersion"], "sources": source_catalog(item_id)}


@app.get("/api/v1/sections/{section_id}/item")
def get_section_item(section_id: str):
    if not section(section_id):
        raise HTTPException(404, "SECTION_NOT_FOUND")
    item = item_for_section(section_id)
    if not item:
        raise HTTPException(404, "ITEM_NOT_FOUND")
    return {"item": item, "sourceVersion": source_version_info(item["itemId"])["sourceVersion"], "sources": source_catalog(item["itemId"])}


@app.get("/api/v1/sources/{source_id}")
def get_source(source_id: str):
    value = source(source_id)
    if not value:
        raise HTTPException(404, "SOURCE_NOT_FOUND")
    return {"source": value}


@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str):
    return api.get(session_id)


@app.post("/api/v1/sessions/{session_id}/attempts")
def submit_attempt(session_id: str, body: AttemptBody, request: Request):
    key = request.headers.get("idempotency-key")
    if not key or len(key) < 8 or len(key) > 120:
        raise HTTPException(400, "IDEMPOTENCY_KEY_REQUIRED")
    cache_key = f"{session_id}:{key}"
    cached = app.state.idempotency.get(cache_key)
    if cached:
        return cached
    result = api.submit_attempt(session_id, body)
    cache = app.state.idempotency
    now = datetime.now(timezone.utc)
    cache[cache_key] = (now, result)
    if len(cache) > 5000:
        cutoff = datetime.fromtimestamp(now.timestamp() - 1800, tz=timezone.utc)
        cache |= {k: v for k, v in cache.items() if v[0] > cutoff}
    return result


@app.post("/api/v1/sessions/{session_id}/hints")
def hint(session_id: str, body: HintBody):
    return api.hint(session_id, body)


@app.post("/api/v1/sessions/{session_id}/explain-back")
def explain(session_id: str, body: ExplainBody):
    return api.explain(session_id, body)


@app.post("/api/v1/sessions/{session_id}/transfer")
def transfer(session_id: str, body: TransferBody):
    return api.transfer(session_id, body)


@app.post("/api/v1/sessions/{session_id}/abstain")
def abstain(session_id: str, body: StateVersionBody):
    return api.abstain(session_id, body.stateVersion)


@app.post("/api/v1/sessions/{session_id}/resume")
def resume(session_id: str, body: StateVersionBody):
    return api.resume(session_id, body.stateVersion)


app.state.idempotency = {}

pdf_candidates = [
    ROOT / "frontend" / "public" / "prompt-engineering-tool-calling.pdf",
    ROOT / "content" / "prompt-engineering-tool-calling.pdf",
]
PDF_PATH = next((path for path in pdf_candidates if path.exists()), None)


@app.get("/prompt-engineering-tool-calling.pdf")
def deck_pdf():
    if not PDF_PATH:
        raise HTTPException(404, "PDF_NOT_FOUND")
    return FileResponse(PDF_PATH, media_type="application/pdf", filename="prompt-engineering-tool-calling.pdf")


frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    def frontend_index():
        return FileResponse(frontend_dist / "index.html")

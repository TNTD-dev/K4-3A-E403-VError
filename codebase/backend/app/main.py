from __future__ import annotations
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .coach import Coach
from .content import ITEM_ID, PUBLIC_ITEM, source, source_catalog, source_version_info
from .db import Store
from .orchestrator import DomainError, Orchestrator
from .schemas import CreateSessionBody, AttemptBody, HintBody, ExplainBody, TransferBody, StateVersionBody

mode = os.getenv("MODEL_MODE", "offline")
store = Store(os.getenv("SQLITE_PATH", str(Path(__file__).resolve().parents[2] / "verror.sqlite")))
api = Orchestrator(store, Coach(mode), mode)
app = FastAPI(title="VError D2 API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(DomainError)
async def domain_error(_: Request, error: DomainError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=error.status, content={"error": error.code, "message": error.message})

@app.get("/healthz")
def healthz(): return {"ok": True, "mode": mode}
@app.get("/readyz")
def readyz(): return {"ok": True, "mode": mode, "fixture": source_version_info(), "sqlite": "writable"}

@app.post("/api/v1/sessions", status_code=201)
def create_session(body: CreateSessionBody): return api.create()
@app.get("/api/v1/items/prompt-clarity-01")
def item(): return {"item": PUBLIC_ITEM, "sourceVersion": source_version_info()["sourceVersion"], "sources": source_catalog()}
@app.get("/api/v1/sources/{source_id}")
def get_source(source_id: str):
    value = source(source_id)
    if not value:
        from fastapi import HTTPException
        raise HTTPException(404, "SOURCE_NOT_FOUND")
    return {"source": value}
@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str): return api.get(session_id)

@app.post("/api/v1/sessions/{session_id}/attempts")
def submit_attempt(session_id: str, body: AttemptBody, request: Request):
    key = request.headers.get("idempotency-key")
    if not key or len(key) < 8 or len(key) > 120: from fastapi import HTTPException; raise HTTPException(400, "IDEMPOTENCY_KEY_REQUIRED")
    cache_key = f"{session_id}:{key}"
    cached = getattr(app.state, "idempotency", {}).get(cache_key)
    if cached: return cached
    result = api.submit_attempt(session_id, body); app.state.idempotency[cache_key] = result; return result
@app.post("/api/v1/sessions/{session_id}/hints")
def hint(session_id: str, body: HintBody): return api.hint(session_id, body)
@app.post("/api/v1/sessions/{session_id}/explain-back")
def explain(session_id: str, body: ExplainBody): return api.explain(session_id, body)
@app.post("/api/v1/sessions/{session_id}/transfer")
def transfer(session_id: str, body: TransferBody): return api.transfer(session_id, body)
@app.post("/api/v1/sessions/{session_id}/abstain")
def abstain(session_id: str, body: StateVersionBody): return api.abstain(session_id, body.stateVersion)
@app.post("/api/v1/sessions/{session_id}/resume")
def resume(session_id: str, body: StateVersionBody): return api.resume(session_id, body.stateVersion)

app.state.idempotency = {}
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    @app.get("/")
    def frontend_index(): return FileResponse(frontend_dist / "index.html")

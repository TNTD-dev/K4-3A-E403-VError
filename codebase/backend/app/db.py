from __future__ import annotations
import hashlib, json, os, sqlite3, uuid
from datetime import datetime, timedelta, timezone
from typing import Any

STATES = {"attempt_1_open", "evaluating_attempt", "diagnosis", "retry", "explain_back", "transfer_check", "source_review", "clarify", "out_of_scope", "completed"}

def now() -> str: return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, filename: str = ":memory:"):
        self.db = sqlite3.connect(filename, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY,item_id TEXT NOT NULL,item_version TEXT NOT NULL,state TEXT NOT NULL,state_version INTEGER NOT NULL,hint_level INTEGER NOT NULL DEFAULT 0,llm_calls INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES sessions(id),sequence INTEGER NOT NULL,kind TEXT NOT NULL,answer_text TEXT NOT NULL,explanation TEXT NOT NULL,confidence TEXT,basis TEXT,objective_status TEXT NOT NULL,error_code TEXT,submitted_at TEXT NOT NULL,UNIQUE(session_id,sequence));
        CREATE TABLE IF NOT EXISTS coach_outputs (id TEXT PRIMARY KEY,attempt_id TEXT REFERENCES attempts(id),provider TEXT NOT NULL,model TEXT,raw_status TEXT NOT NULL,verified_status TEXT NOT NULL,diagnosis_code TEXT,confidence_band TEXT,hint_level INTEGER,citation_ids_json TEXT NOT NULL,fallback_reason TEXT,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY,session_id_hash TEXT NOT NULL,event_name TEXT NOT NULL,payload_json TEXT NOT NULL,created_at TEXT NOT NULL);
        """)
        self.db.commit()

    def create_session(self, item_id: str, item_version: str, ttl_minutes: int = 30) -> sqlite3.Row:
        created = datetime.now(timezone.utc); row = (str(uuid.uuid4()), item_id, item_version, "attempt_1_open", 1, 0, 0, created.isoformat(), (created + timedelta(minutes=ttl_minutes)).isoformat())
        self.db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?)", row); self.db.commit(); return self.session(row[0])
    def session(self, session_id: str) -> sqlite3.Row | None: return self.db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    def update_session(self, session_id: str, expected: int, state: str, hint_level: int | None = None) -> sqlite3.Row:
        current = self.session(session_id)
        if not current: raise ValueError("SESSION_NOT_FOUND")
        result = self.db.execute("UPDATE sessions SET state=?,state_version=state_version+1,hint_level=? WHERE id=? AND state_version=?", (state, current["hint_level"] if hint_level is None else hint_level, session_id, expected))
        if result.rowcount != 1: raise ValueError("STATE_VERSION_CONFLICT")
        self.db.commit(); return self.session(session_id)  # type: ignore
    def increment_llm_calls(self, session_id: str) -> None: self.db.execute("UPDATE sessions SET llm_calls=llm_calls+1 WHERE id=?", (session_id,)); self.db.commit()
    def attempts(self, session_id: str) -> list[sqlite3.Row]: return list(self.db.execute("SELECT * FROM attempts WHERE session_id=? ORDER BY sequence", (session_id,)))
    def insert_attempt(self, values: dict[str, Any]) -> sqlite3.Row:
        row = {**values, "id": str(uuid.uuid4()), "submitted_at": now()}
        self.db.execute("INSERT INTO attempts VALUES (:id,:session_id,:sequence,:kind,:answer_text,:explanation,:confidence,:basis,:objective_status,:error_code,:submitted_at)", row); self.db.commit(); return self.db.execute("SELECT * FROM attempts WHERE id=?", (row["id"],)).fetchone()  # type: ignore
    def insert_coach_output(self, values: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO coach_outputs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), values.get("attempt_id"), values.get("provider", "offline"), values.get("model"), values.get("raw_status", "ok"), "accepted", values.get("diagnosis_code"), values.get("confidence_band"), values.get("hint_level"), json.dumps(values.get("citation_ids", [])), values.get("fallback_reason"), now())); self.db.commit()
    def event(self, session_id: str, event_name: str, payload: dict[str, Any]) -> None:
        salt = os.getenv("SESSION_HASH_SALT", "local-dev-salt"); digest = hashlib.sha256(f"{salt}:{session_id}".encode()).hexdigest()
        self.db.execute("INSERT INTO events VALUES (?,?,?,?,?)", (str(uuid.uuid4()), digest, event_name, json.dumps(payload, ensure_ascii=False), now())); self.db.commit()
    def close(self) -> None: self.db.close()

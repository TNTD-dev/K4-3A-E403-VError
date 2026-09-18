from __future__ import annotations
import hashlib, json, os, sqlite3, uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from .content import DEFAULT_LEARNER
from .sections import SECTIONS, first_section_id, next_section

STATES = {
    "attempt_1_open", "evaluating_attempt", "diagnosis", "retry", "explain_back",
    "transfer_check", "source_review", "clarify", "out_of_scope", "completed",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, filename: str = ":memory:"):
        self.db = sqlite3.connect(filename, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY,
              item_id TEXT NOT NULL,
              item_version TEXT NOT NULL,
              section_id TEXT NOT NULL DEFAULT 'prompt-fundamentals',
              state TEXT NOT NULL,
              state_version INTEGER NOT NULL,
              hint_level INTEGER NOT NULL DEFAULT 0,
              llm_calls INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attempts (
              id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL REFERENCES sessions(id),
              sequence INTEGER NOT NULL,
              kind TEXT NOT NULL,
              answer_text TEXT NOT NULL,
              explanation TEXT NOT NULL,
              confidence TEXT,
              basis TEXT,
              objective_status TEXT NOT NULL,
              error_code TEXT,
              submitted_at TEXT NOT NULL,
              UNIQUE(session_id, sequence)
            );
            CREATE TABLE IF NOT EXISTS coach_outputs (
              id TEXT PRIMARY KEY,
              attempt_id TEXT REFERENCES attempts(id),
              provider TEXT NOT NULL,
              model TEXT,
              raw_status TEXT NOT NULL,
              verified_status TEXT NOT NULL,
              diagnosis_code TEXT,
              confidence_band TEXT,
              hint_level INTEGER,
              citation_ids_json TEXT NOT NULL,
              fallback_reason TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
              id TEXT PRIMARY KEY,
              session_id_hash TEXT NOT NULL,
              event_name TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS day_progress (
              learner_id TEXT PRIMARY KEY,
              unlocked_attempts_json TEXT NOT NULL,
              unlocked_slides_json TEXT NOT NULL,
              completed_sections_json TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(sessions)")}
        if "section_id" not in columns:
            self.db.execute("ALTER TABLE sessions ADD COLUMN section_id TEXT NOT NULL DEFAULT 'prompt-fundamentals'")
        self.db.commit()
        self.ensure_progress(DEFAULT_LEARNER)

    def ensure_progress(self, learner_id: str = DEFAULT_LEARNER) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM day_progress WHERE learner_id=?", (learner_id,)).fetchone()
        if row:
            return row
        first = first_section_id()
        payload = (
            learner_id,
            json.dumps([first]),
            json.dumps([]),
            json.dumps([]),
            now(),
        )
        self.db.execute(
            "INSERT INTO day_progress (learner_id, unlocked_attempts_json, unlocked_slides_json, completed_sections_json, updated_at) VALUES (?,?,?,?,?)",
            payload,
        )
        self.db.commit()
        return self.db.execute("SELECT * FROM day_progress WHERE learner_id=?", (learner_id,)).fetchone()  # type: ignore

    def progress(self, learner_id: str = DEFAULT_LEARNER) -> dict[str, Any]:
        row = self.ensure_progress(learner_id)
        return {
            "learnerId": row["learner_id"],
            "unlockedAttempts": set(json.loads(row["unlocked_attempts_json"])),
            "unlockedSlides": set(json.loads(row["unlocked_slides_json"])),
            "completedSections": set(json.loads(row["completed_sections_json"])),
        }

    def save_progress(self, learner_id: str, unlocked_attempts: set[str], unlocked_slides: set[str], completed_sections: set[str]) -> dict[str, Any]:
        self.db.execute(
            """
            UPDATE day_progress
            SET unlocked_attempts_json=?, unlocked_slides_json=?, completed_sections_json=?, updated_at=?
            WHERE learner_id=?
            """,
            (
                json.dumps(sorted(unlocked_attempts)),
                json.dumps(sorted(unlocked_slides)),
                json.dumps(sorted(completed_sections)),
                now(),
                learner_id,
            ),
        )
        self.db.commit()
        return self.progress(learner_id)

    def unlock_after_attempt(self, section_id: str, learner_id: str = DEFAULT_LEARNER) -> dict[str, Any]:
        state = self.progress(learner_id)
        unlocked_attempts = set(state["unlockedAttempts"])
        unlocked_slides = set(state["unlockedSlides"])
        completed = set(state["completedSections"])
        unlocked_slides.add(section_id)
        following = next_section(section_id)
        if following:
            unlocked_attempts.add(following["sectionId"])
        return self.save_progress(learner_id, unlocked_attempts, unlocked_slides, completed)

    def reset_progress(self, learner_id: str = DEFAULT_LEARNER) -> dict[str, Any]:
        """Demo reset: wipe sessions and return to only the first section attempt being open."""
        self.db.execute("DELETE FROM coach_outputs")
        self.db.execute("DELETE FROM attempts")
        self.db.execute("DELETE FROM events")
        self.db.execute("DELETE FROM sessions")
        self.db.commit()
        return self.save_progress(learner_id, {first_section_id()}, set(), set())

    def mark_section_completed(self, section_id: str, learner_id: str = DEFAULT_LEARNER) -> dict[str, Any]:
        state = self.progress(learner_id)
        completed = set(state["completedSections"])
        completed.add(section_id)
        return self.save_progress(learner_id, set(state["unlockedAttempts"]), set(state["unlockedSlides"]), completed)

    def section_views(self, learner_id: str = DEFAULT_LEARNER) -> list[dict[str, Any]]:
        state = self.progress(learner_id)
        views = []
        for item in SECTIONS:
            sid = item["sectionId"]
            attempt_open = sid in state["unlockedAttempts"]
            slides_open = sid in state["unlockedSlides"]
            views.append(
                {
                    **item,
                    "attemptLocked": not attempt_open,
                    "slidesLocked": not slides_open,
                    "locked": not attempt_open,
                    "completed": sid in state["completedSections"],
                }
            )
        return views

    def create_session(self, item_id: str, item_version: str, section_id: str = "prompt-fundamentals", ttl_minutes: int = 30) -> sqlite3.Row:
        created = datetime.now(timezone.utc)
        row = (
            str(uuid.uuid4()),
            item_id,
            item_version,
            section_id,
            "attempt_1_open",
            1,
            0,
            0,
            created.isoformat(),
            (created + timedelta(minutes=ttl_minutes)).isoformat(),
        )
        self.db.execute(
            "INSERT INTO sessions (id,item_id,item_version,section_id,state,state_version,hint_level,llm_calls,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            row,
        )
        self.db.commit()
        return self.session(row[0])

    def session(self, session_id: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()

    def update_session(self, session_id: str, expected: int, state: str, hint_level: int | None = None) -> sqlite3.Row:
        current = self.session(session_id)
        if not current:
            raise ValueError("SESSION_NOT_FOUND")
        result = self.db.execute(
            "UPDATE sessions SET state=?,state_version=state_version+1,hint_level=? WHERE id=? AND state_version=?",
            (state, current["hint_level"] if hint_level is None else hint_level, session_id, expected),
        )
        if result.rowcount != 1:
            raise ValueError("STATE_VERSION_CONFLICT")
        self.db.commit()
        return self.session(session_id)  # type: ignore

    def increment_llm_calls(self, session_id: str) -> None:
        self.db.execute("UPDATE sessions SET llm_calls=llm_calls+1 WHERE id=?", (session_id,))
        self.db.commit()

    def attempts(self, session_id: str) -> list[sqlite3.Row]:
        return list(self.db.execute("SELECT * FROM attempts WHERE session_id=? ORDER BY sequence", (session_id,)))

    def insert_attempt(self, values: dict[str, Any]) -> sqlite3.Row:
        row = {**values, "id": str(uuid.uuid4()), "submitted_at": now()}
        self.db.execute(
            "INSERT INTO attempts VALUES (:id,:session_id,:sequence,:kind,:answer_text,:explanation,:confidence,:basis,:objective_status,:error_code,:submitted_at)",
            row,
        )
        self.db.commit()
        return self.db.execute("SELECT * FROM attempts WHERE id=?", (row["id"],)).fetchone()  # type: ignore

    def insert_coach_output(self, values: dict[str, Any]) -> None:
        self.db.execute(
            "INSERT INTO coach_outputs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                values.get("attempt_id"),
                values.get("provider", "offline"),
                values.get("model"),
                values.get("raw_status", "ok"),
                "accepted",
                values.get("diagnosis_code"),
                values.get("confidence_band"),
                values.get("hint_level"),
                json.dumps(values.get("citation_ids", [])),
                values.get("fallback_reason"),
                now(),
            ),
        )
        self.db.commit()

    def event(self, session_id: str, event_name: str, payload: dict[str, Any]) -> None:
        salt = os.getenv("SESSION_HASH_SALT", "local-dev-salt")
        digest = hashlib.sha256(f"{salt}:{session_id}".encode()).hexdigest()
        self.db.execute(
            "INSERT INTO events VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), digest, event_name, json.dumps(payload, ensure_ascii=False), now()),
        )
        self.db.commit()

    def close(self) -> None:
        self.db.close()

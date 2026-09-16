import Database from "better-sqlite3";
import { createHash, randomUUID } from "node:crypto";
import type { SessionState } from "./schemas.js";

export type SessionRow = {
  id: string;
  item_id: string;
  item_version: string;
  state: SessionState;
  state_version: number;
  hint_level: number;
  llm_calls: number;
  created_at: string;
  expires_at: string;
};

export type AttemptRow = {
  id: string;
  session_id: string;
  sequence: number;
  kind: string;
  answer_text: string;
  explanation: string;
  confidence: string | null;
  basis: string | null;
  objective_status: string;
  error_code: string | null;
  submitted_at: string;
};

export class Store {
  readonly db: Database.Database;

  constructor(filename = ":memory:") {
    this.db = new Database(filename);
    this.db.pragma("foreign_keys = ON");
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        item_id TEXT NOT NULL,
        item_version TEXT NOT NULL,
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
        latency_ms INTEGER,
        created_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        session_id_hash TEXT NOT NULL,
        event_name TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
      );
    `);
  }

  createSession(itemId: string, itemVersion: string, ttlMinutes = 30): SessionRow {
    const now = new Date();
    const row: SessionRow = {
      id: randomUUID(),
      item_id: itemId,
      item_version: itemVersion,
      state: "attempt_1_open",
      state_version: 1,
      hint_level: 0,
      llm_calls: 0,
      created_at: now.toISOString(),
      expires_at: new Date(now.getTime() + ttlMinutes * 60_000).toISOString()
    };
    this.db.prepare(`INSERT INTO sessions VALUES (@id,@item_id,@item_version,@state,@state_version,@hint_level,@llm_calls,@created_at,@expires_at)`).run(row);
    return row;
  }

  getSession(id: string): SessionRow | undefined {
    return this.db.prepare("SELECT * FROM sessions WHERE id = ?").get(id) as SessionRow | undefined;
  }

  updateSession(id: string, expectedVersion: number, state: SessionState, hintLevel?: number): SessionRow {
    const nextHint = hintLevel ?? this.getSession(id)?.hint_level ?? 0;
    const result = this.db.prepare(`UPDATE sessions SET state = ?, state_version = state_version + 1, hint_level = ? WHERE id = ? AND state_version = ?`).run(state, nextHint, id, expectedVersion);
    if (result.changes !== 1) throw new Error("STATE_VERSION_CONFLICT");
    const row = this.getSession(id);
    if (!row) throw new Error("SESSION_NOT_FOUND");
    return row;
  }

  incrementLlmCalls(id: string): void {
    this.db.prepare("UPDATE sessions SET llm_calls = llm_calls + 1 WHERE id = ?").run(id);
  }

  getAttempts(sessionId: string): AttemptRow[] {
    return this.db.prepare("SELECT * FROM attempts WHERE session_id = ? ORDER BY sequence").all(sessionId) as AttemptRow[];
  }

  insertAttempt(input: Omit<AttemptRow, "id" | "submitted_at">): AttemptRow {
    const row: AttemptRow = { ...input, id: randomUUID(), submitted_at: new Date().toISOString() };
    this.db.prepare(`INSERT INTO attempts VALUES (@id,@session_id,@sequence,@kind,@answer_text,@explanation,@confidence,@basis,@objective_status,@error_code,@submitted_at)`).run(row);
    return row;
  }

  insertCoachOutput(input: Record<string, unknown>): void {
    this.db.prepare(`INSERT INTO coach_outputs (id, attempt_id, provider, model, raw_status, verified_status, diagnosis_code, confidence_band, hint_level, citation_ids_json, fallback_reason, latency_ms, created_at) VALUES (@id,@attempt_id,@provider,@model,@raw_status,@verified_status,@diagnosis_code,@confidence_band,@hint_level,@citation_ids_json,@fallback_reason,@latency_ms,@created_at)`).run({
      id: randomUUID(),
      attempt_id: (input as Record<string, unknown>).attempt_id ?? null,
      provider: (input as Record<string, unknown>).provider ?? "offline",
      model: (input as Record<string, unknown>).model ?? null,
      raw_status: (input as Record<string, unknown>).raw_status ?? "ok",
      verified_status: (input as Record<string, unknown>).verified_status ?? "accepted",
      diagnosis_code: (input as Record<string, unknown>).diagnosis_code ?? null,
      confidence_band: (input as Record<string, unknown>).confidence_band ?? null,
      hint_level: (input as Record<string, unknown>).hint_level ?? null,
      citation_ids_json: (input as Record<string, unknown>).citation_ids_json ?? "[]",
      fallback_reason: (input as Record<string, unknown>).fallback_reason ?? null,
      latency_ms: (input as Record<string, unknown>).latency_ms ?? null,
      created_at: new Date().toISOString()
    });
  }

  appendEvent(sessionId: string, eventName: string, payload: Record<string, unknown>): void {
    const sessionHash = createHash("sha256").update(`${process.env.SESSION_HASH_SALT ?? "local-dev-salt"}:${sessionId}`).digest("hex");
    this.db.prepare("INSERT INTO events VALUES (?,?,?,?,?)").run(randomUUID(), sessionHash, eventName, JSON.stringify(payload), new Date().toISOString());
  }

  close(): void { this.db.close(); }
}

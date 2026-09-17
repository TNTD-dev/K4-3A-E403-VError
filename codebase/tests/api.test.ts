import { describe, expect, it, afterEach } from "vitest";
import { buildApp } from "../src/server.js";
import { Store } from "../src/db.js";

const apps: Array<{ close: () => Promise<void> }> = [];

afterEach(async () => { while (apps.length) await apps.pop()?.close(); });

describe("D2 API contract", () => {
  it("keeps the answer key out of the public session and exposes bounded Day material", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const response = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "prompt-clarity-01", mode: "demo" } });
    expect(response.statusCode).toBe(201);
    const body = response.json();
    expect(body.item.itemId).toBe("prompt-clarity-01");
    expect(body.item.expectedChoiceId).toBeUndefined();
    expect(body.item.requiredExplainClaimIds).toBeUndefined();
    expect(body.sources.map((source: { sourceId: string }) => source.sourceId)).toEqual(["D04-P07", "D04-P08", "D04-P10", "D04-P20"]);
    expect(body.sources[0].approvedLocations).toContainEqual({ kind: "video", label: "Video timestamp unavailable · use PDF p.7 anchor" });
    expect(body.state).toBe("attempt_1_open");

    const source = await app.inject({ method: "GET", url: "/api/v1/sources/D04-P08" });
    expect(source.statusCode).toBe(200);
    expect(source.json().source.excerpt).toContain("Task + Format");
  });

  it("runs correction through diagnosis, grounded hint and retry", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const created = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "prompt-clarity-01" } });
    const session = created.json();
    const first = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, headers: { "idempotency-key": "attempt-001" }, payload: { stateVersion: 1, kind: "attempt_1", answer: { text: "Có, prompt càng dài và càng nhiều role thì càng tốt.", explanation: "Nhiều thông tin làm model thông minh hơn." }, confidence: "Khá chắc", basis: "Suy luận" } });
    expect(first.statusCode).toBe(200);
    expect(first.json().next.state).toBe("diagnosis");
    expect(first.json().coach.diagnosisCode).toBe("M_PROMPT_LONGER_BETTER");
    const hint = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/hints`, payload: { stateVersion: 2, level: 1 } });
    expect(hint.json().coach.hint.citations[0].sourceId).toBe("D04-P07");
    const retry = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, headers: { "idempotency-key": "attempt-002" }, payload: { stateVersion: 3, kind: "retry", answer: { text: "Không nhất thiết, prompt rõ Task + Format có thể tốt hơn prompt dài.", explanation: "Role hoặc Context chỉ thêm khi chúng thực sự cải thiện kết quả." }, confidence: "Khá chắc", basis: "Suy luận" } });
    expect(retry.json().next.state).toBe("explain_back");
    const explain = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/explain-back`, payload: { stateVersion: 4, text: "Prompt rõ nghĩa thay vì prompt dài lan man. Bắt đầu với Task + Format. Token thừa có thể tăng chi phí và nhiễu." } });
    expect(explain.json().next.state).toBe("transfer_check");
    const transfer = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/transfer`, payload: { stateVersion: 5, answer: "Không nhất thiết, chọn prompt rõ Task và Format thay vì prompt dài.", reasoning: "Chỉ thêm Context khi cần thiết và có ích cho task." } });
    expect(transfer.json().next.state).toBe("completed");
  });

  it("routes explicit abstention through source review and back to the task", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const created = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "prompt-clarity-01" } });
    const session = created.json();
    const abstain = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/abstain`, payload: { stateVersion: 1 } });
    expect(abstain.json().next.state).toBe("source_review");
    const resumed = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/resume`, payload: { stateVersion: 2 } });
    expect(resumed.json().next.state).toBe("attempt_1_open");
  });

  it("rejects stale state and missing idempotency key", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const created = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "prompt-clarity-01" } });
    const session = created.json();
    const missingKey = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, payload: { stateVersion: 1, kind: "attempt_1", answer: { text: "x", explanation: "y" } } });
    expect(missingKey.statusCode).toBe(400);
    const first = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, headers: { "idempotency-key": "attempt-003" }, payload: { stateVersion: 1, kind: "attempt_1", answer: { text: "Prompt càng dài càng tốt.", explanation: "Nhiều role luôn tốt hơn." } } });
    expect(first.statusCode).toBe(200);
    const stale = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/hints`, payload: { stateVersion: 1, level: 1 } });
    expect(stale.statusCode).toBe(409);
  });
});

import { describe, expect, it, afterEach } from "vitest";
import { buildApp } from "../src/server.js";
import { Store } from "../src/db.js";

const apps: Array<{ close: () => Promise<void> }> = [];

afterEach(async () => { while (apps.length) await apps.pop()?.close(); });

describe("D2 API contract", () => {
  it("keeps the answer key out of the public session", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const response = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "tokenization-01", mode: "demo" } });
    expect(response.statusCode).toBe(201);
    const body = response.json();
    expect(body.item.expectedChoiceId).toBeUndefined();
    expect(body.item.requiredExplainClaimIds).toBeUndefined();
    expect(body.state).toBe("attempt_1_open");
  });

  it("runs correction through diagnosis, grounded hint and retry", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const created = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "tokenization-01" } });
    const session = created.json();
    const first = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, headers: { "idempotency-key": "attempt-001" }, payload: { stateVersion: 1, kind: "attempt_1", answer: { text: "3 token vì có 3 từ.", explanation: "Mỗi từ là một token." }, confidence: "Khá chắc", basis: "Suy luận" } });
    expect(first.statusCode).toBe(200);
    expect(first.json().next.state).toBe("diagnosis");
    const hint = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/hints`, payload: { stateVersion: 2, level: 1 } });
    expect(hint.json().coach.hint.citations[0].sourceId).toBe("T04-049");
    const retry = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, headers: { "idempotency-key": "attempt-002" }, payload: { stateVersion: 3, kind: "retry", answer: { text: "Không nhất thiết vì token không phải từ.", explanation: "Tokenizer có thể tách khác theo ngôn ngữ." }, confidence: "Khá chắc", basis: "Suy luận" } });
    expect(retry.json().next.state).toBe("explain_back");
    const explain = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/explain-back`, payload: { stateVersion: 4, text: "Token là đơn vị tính, không phải từ hay chữ cái. Tokenizer khác nhau có thể chia khác nhau. Muốn đếm chính xác số token cần công cụ." } });
    expect(explain.json().next.state).toBe("transfer_check");
    const transfer = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/transfer`, payload: { stateVersion: 5, answer: "Không nhất thiết.", reasoning: "Tokenizer hoặc model khác nhau có thể chia khác nhau." } });
    expect(transfer.json().next.state).toBe("completed");
  });

  it("routes explicit abstention through source review and back to the task", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const created = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "tokenization-01" } });
    const session = created.json();
    const abstain = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/abstain`, payload: { stateVersion: 1 } });
    expect(abstain.json().next.state).toBe("source_review");
    const resumed = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/resume`, payload: { stateVersion: 2 } });
    expect(resumed.json().next.state).toBe("attempt_1_open");
  });

  it("rejects stale state and missing idempotency key", async () => {
    const app = buildApp({ store: new Store(":memory:"), modelMode: "offline" });
    apps.push(app);
    const created = await app.inject({ method: "POST", url: "/api/v1/sessions", payload: { itemId: "tokenization-01" } });
    const session = created.json();
    const missingKey = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, payload: { stateVersion: 1, kind: "attempt_1", answer: { text: "x", explanation: "y" } } });
    expect(missingKey.statusCode).toBe(400);
    const first = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/attempts`, headers: { "idempotency-key": "attempt-003" }, payload: { stateVersion: 1, kind: "attempt_1", answer: { text: "3 token", explanation: "Mỗi từ là token." } } });
    expect(first.statusCode).toBe(200);
    const stale = await app.inject({ method: "POST", url: `/api/v1/sessions/${session.sessionId}/hints`, payload: { stateVersion: 1, level: 1 } });
    expect(stale.statusCode).toBe(409);
  });
});

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildFetchInit, formatApiError } from "./http.js";

describe("buildFetchInit header merge", () => {
  it("keeps Content-Type when callers pass Idempotency-Key", () => {
    const init = buildFetchInit({
      method: "POST",
      headers: { "Idempotency-Key": "attempt-1" },
      body: JSON.stringify({ kind: "attempt_1" }),
    });
    assert.equal(init.headers["Content-Type"], "application/json");
    assert.equal(init.headers["Idempotency-Key"], "attempt-1");
    assert.equal(init.method, "POST");
    assert.ok(init.body.includes("attempt_1"));
  });

  it("does not let options.headers replace the whole headers object", () => {
    const broken = {
      headers: { "Content-Type": "application/json", ...({ "Idempotency-Key": "x" }) },
      ...{ headers: { "Idempotency-Key": "x" }, method: "POST" },
    };
    assert.equal(broken.headers["Content-Type"], undefined);

    const fixed = buildFetchInit({
      method: "POST",
      headers: { "Idempotency-Key": "x" },
    });
    assert.equal(fixed.headers["Content-Type"], "application/json");
  });
});

describe("formatApiError", () => {
  it("surfaces FastAPI validation detail arrays", () => {
    const message = formatApiError({
      detail: [{ loc: ["body"], msg: "Input should be a valid dictionary", type: "dict_type" }],
    });
    assert.match(message, /Input should be a valid dictionary/);
  });

  it("prefers message then error then generic fallback", () => {
    assert.equal(formatApiError({ message: "locked" }), "locked");
    assert.equal(formatApiError({ error: "STATE_CONFLICT" }), "STATE_CONFLICT");
    assert.equal(formatApiError({}), "Có lỗi xảy ra");
  });
});

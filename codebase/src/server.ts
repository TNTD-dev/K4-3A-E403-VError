import Fastify, { type FastifyInstance } from "fastify";
import fastifyStatic from "@fastify/static";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { Store } from "./db.js";
import { DomainError, Orchestrator } from "./orchestrator.js";
import { makeCoach, type D2Coach } from "./coach.js";
import { CreateSessionBody, AttemptBody, HintBody, ExplainBody, TransferBody, StateVersionBody } from "./schemas.js";
import { sourceVersionInfo } from "./content.js";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");

export type BuildOptions = { store?: Store; coach?: D2Coach; modelMode?: string };

export function buildApp(options: BuildOptions = {}): FastifyInstance {
  const store = options.store ?? new Store(process.env.SQLITE_PATH ?? join(root, "verror.sqlite"));
  const app = Fastify({ logger: false, bodyLimit: 8 * 1024, requestIdHeader: "x-request-id" });
  const orchestrator = new Orchestrator(store, options.coach ?? makeCoach(options.modelMode), options.modelMode ?? process.env.MODEL_MODE ?? "offline");
  const idempotency = new Map<string, unknown>();

  app.register(fastifyStatic, { root: join(root, "public"), wildcard: false });

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof DomainError) return reply.code(error.statusCode).send({ requestId: request.id, error: error.code, message: error.message });
    request.log.error(error);
    return reply.code(500).send({ requestId: request.id, error: "INTERNAL_ERROR" });
  });

  app.get("/healthz", async () => ({ ok: true, mode: options.modelMode ?? process.env.MODEL_MODE ?? "offline" }));
  app.get("/readyz", async () => ({ ok: true, mode: options.modelMode ?? process.env.MODEL_MODE ?? "offline", fixture: sourceVersionInfo(), sqlite: "writable" }));
  app.post("/api/v1/sessions", async (request, reply) => {
    const body = CreateSessionBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    return reply.code(201).send({ requestId: request.id, ...orchestrator.createSession() });
  });

  app.get<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId", async (request, reply) => {
    return reply.send({ requestId: request.id, ...orchestrator.getSession(request.params.sessionId) });
  });

  app.post<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId/attempts", async (request, reply) => {
    const key = request.headers["idempotency-key"];
    if (typeof key !== "string" || key.length < 8 || key.length > 120) return reply.code(400).send({ requestId: request.id, error: "IDEMPOTENCY_KEY_REQUIRED" });
    const idempotencyKey = `${request.params.sessionId}:${key}`;
    const cached = idempotency.get(idempotencyKey);
    if (cached) return reply.send({ requestId: request.id, ...(cached as Record<string, unknown>) });
    const body = AttemptBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    const result = await orchestrator.submitAttempt(request.params.sessionId, body.data);
    idempotency.set(idempotencyKey, result);
    return reply.send({ requestId: request.id, ...result });
  });

  app.post<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId/hints", async (request, reply) => {
    const body = HintBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    return reply.send({ requestId: request.id, ...(await orchestrator.requestHint(request.params.sessionId, body.data)) });
  });

  app.post<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId/explain-back", async (request, reply) => {
    const body = ExplainBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    return reply.send({ requestId: request.id, ...orchestrator.submitExplainBack(request.params.sessionId, body.data) });
  });

  app.post<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId/transfer", async (request, reply) => {
    const body = TransferBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    return reply.send({ requestId: request.id, ...orchestrator.submitTransfer(request.params.sessionId, body.data) });
  });

  app.post<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId/abstain", async (request, reply) => {
    const body = StateVersionBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    return reply.send({ requestId: request.id, ...orchestrator.abstain(request.params.sessionId, body.data.stateVersion) });
  });

  app.post<{ Params: { sessionId: string } }>("/api/v1/sessions/:sessionId/resume", async (request, reply) => {
    const body = StateVersionBody.safeParse(request.body);
    if (!body.success) return reply.code(400).send({ requestId: request.id, error: "INVALID_BODY", message: body.error.message });
    return reply.send({ requestId: request.id, ...orchestrator.resume(request.params.sessionId, body.data.stateVersion) });
  });

  app.addHook("onClose", async () => store.close());
  return app;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const port = Number(process.env.PORT ?? 3000);
  const host = process.env.HOST ?? "127.0.0.1";
  const app = buildApp();
  app.listen({ port, host }).then(() => console.log(`VError D2 listening on http://${host}:${port} (${process.env.MODEL_MODE ?? "offline"})`)).catch((error) => { console.error(error); process.exit(1); });
}

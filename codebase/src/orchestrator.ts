import { answerKey, ITEM_ID, ITEM_VERSION, SOURCE_VERSION, type MisconceptionId } from "./answer-key.js";
import { getSource, publicItem, publicSourceCatalog, type ApprovedSource } from "./content.js";
import { type D2Coach, type CoachResult } from "./coach.js";
import { Store, type AttemptRow, type SessionRow } from "./db.js";
import { evaluateAttempt, evaluateExplainBack, evaluateTransfer, reviewedHint, validTransition, verifyCoachDraft } from "./evaluator.js";
import { AttemptBody, type AttemptBody as AttemptInput, ExplainBody, type ExplainBody as ExplainInput, HintBody, type HintBody as HintInput, TransferBody, type TransferBody as TransferInput, type SessionState } from "./schemas.js";

export class DomainError extends Error {
  constructor(public readonly code: string, public readonly statusCode = 400, message = code) { super(message); }
}

export type ApiResponse = Record<string, unknown>;

function citations(ids: string[]) {
  return ids.flatMap((id) => {
    const source = getSource(id);
    return source ? [{ sourceId: source.sourceId, label: source.locator, locations: source.approvedLocations }] : [];
  });
}

function publicSession(session: SessionRow, attempts: AttemptRow[]) {
  return {
    sessionId: session.id,
    stateVersion: session.state_version,
    state: session.state,
    hintLevel: session.hint_level,
    item: publicItem,
    sources: publicSourceCatalog(),
    attempts: attempts.map((attempt) => ({ attemptNo: attempt.sequence, kind: attempt.kind, objectiveStatus: attempt.objective_status, errorCode: attempt.error_code }))
  };
}

export class Orchestrator {
  constructor(private readonly store: Store, private readonly coach: D2Coach, private readonly modelMode = process.env.MODEL_MODE ?? "offline") {}

  createSession(): ApiResponse {
    const session = this.store.createSession(ITEM_ID, ITEM_VERSION);
    this.store.appendEvent(session.id, "session_created", { item_id: ITEM_ID, item_version: ITEM_VERSION, source_version: SOURCE_VERSION, mode: this.modelMode });
    return { ...publicSession(session, []), expiresAt: session.expires_at };
  }

  getSession(sessionId: string): ApiResponse {
    const session = this.requireSession(sessionId);
    return publicSession(session, this.store.getAttempts(sessionId));
  }

  async submitAttempt(sessionId: string, input: AttemptInput): Promise<ApiResponse> {
    const parsed = AttemptBody.safeParse(input);
    if (!parsed.success) throw new DomainError("INVALID_BODY", 400, parsed.error.message);
    const session = this.requireSession(sessionId);
    if (input.stateVersion !== session.state_version) throw new DomainError("STATE_VERSION_CONFLICT", 409);
    if (!["attempt_1_open", "retry", "diagnosis"].includes(session.state)) throw new DomainError("INVALID_STATE", 409);
    if (input.kind === "attempt_1" && session.state !== "attempt_1_open") throw new DomainError("INVALID_ATTEMPT_KIND", 409);
    if (input.kind === "retry" && !["retry", "diagnosis"].includes(session.state)) throw new DomainError("INVALID_ATTEMPT_KIND", 409);
    const attemptNo = this.store.getAttempts(sessionId).length + 1;
    if (attemptNo > 3) throw new DomainError("ATTEMPT_LIMIT", 409);
    const objective = evaluateAttempt(input.answer.text, input.answer.explanation, input.basis);
    this.store.appendEvent(sessionId, "attempt_submitted", { attempt_no: attemptNo, objective_status: objective.status, error_code: objective.errorCode, confidence: input.confidence ?? null, basis: input.basis ?? null, input_chars: input.answer.text.length + input.answer.explanation.length });

    if (objective.status === "clarify") {
      const next = this.transition(session, "clarify");
      this.store.appendEvent(sessionId, "clarification_requested", { attempt_no: attemptNo, reason_code: objective.reason });
      return { stateVersion: next.state_version, attempted: false, evaluation: { status: "unknown", errorCode: null }, coach: { status: "clarify", message: "Mình đã nhận câu trả lời, nhưng chưa đủ để biết bạn đang dùng giả định nào.", citations: [] }, next: { state: "clarify" } };
    }

    const attempt = this.store.insertAttempt({ session_id: sessionId, sequence: attemptNo, kind: input.kind, answer_text: input.answer.text, explanation: input.answer.explanation, confidence: input.confidence ?? null, basis: input.basis ?? null, objective_status: objective.status, error_code: objective.errorCode });
    if (objective.status === "out_of_scope") {
      const next = this.transition(session, "out_of_scope");
      this.store.appendEvent(sessionId, "out_of_scope", { attempt_no: attemptNo, reason: objective.reason });
      return { stateVersion: next.state_version, attempted: true, attemptNo, evaluation: { status: objective.status, errorCode: null }, coach: { status: "out_of_scope", message: "Câu hỏi này nằm ngoài lát cắt Prompt Engineering đã được duyệt; VError không đoán thay bạn.", citations: [] }, next: { state: "out_of_scope" } };
    }
    if (objective.status === "unknown") {
      const next = this.transition(session, "source_review");
      this.store.appendEvent(sessionId, "fallback_used", { attempt_no: attemptNo, fallback_reason: objective.reason, evidence_ids: [] });
      return { stateVersion: next.state_version, attempted: true, attemptNo, evaluation: { status: objective.status, errorCode: null }, coach: { status: "abstain", message: "Mình chưa có đủ căn cứ để kết luận bạn đang mắc lỗi nào.", citations: [] }, next: { state: "source_review" } };
    }
    if (objective.status === "correct") {
      const next = this.transition(session, "explain_back");
      this.store.appendEvent(sessionId, "diagnosis_returned", { attempt_no: attemptNo, objective_status: "correct", provider: "deterministic", citation_ids: ["D04-P08"] });
      return { stateVersion: next.state_version, attempted: true, attemptNo, evaluation: { status: "correct", errorCode: null }, coach: { status: "probe", message: "Lần thử này phù hợp với answer key. Một câu đúng chưa đủ chứng minh bạn đã hiểu.", citations: citations(["D04-P08"]) }, next: { state: "explain_back" } };
    }

    const diagnosisCode = objective.errorCode as MisconceptionId;
    const coachResult = await this.callCoach(session, attempt, diagnosisCode, 0, input.answer.text, input.answer.explanation);
    const nextState = attemptNo > 1 ? "retry" : "diagnosis";
    const next = this.transition(session, nextState, session.hint_level);
    this.store.appendEvent(sessionId, "diagnosis_returned", { attempt_no: attemptNo, diagnosis_code: diagnosisCode, provider: coachResult.provider, fallback_reason: coachResult.fallbackReason ?? null, citation_ids: coachResult.draft.citationIds });
    return { stateVersion: next.state_version, attempted: true, attemptNo, evaluation: { status: "incorrect", errorCode: diagnosisCode }, coach: this.coachPayload(coachResult, "diagnosed"), next: { state: nextState, allowedAttemptsRemaining: 3 - attemptNo } };
  }

  async requestHint(sessionId: string, input: HintInput): Promise<ApiResponse> {
    const parsed = HintBody.safeParse(input);
    if (!parsed.success) throw new DomainError("INVALID_BODY", 400, parsed.error.message);
    const session = this.requireSession(sessionId);
    if (input.stateVersion !== session.state_version) throw new DomainError("STATE_VERSION_CONFLICT", 409);
    if (!["diagnosis", "retry"].includes(session.state)) throw new DomainError("INVALID_STATE", 409);
    const attempts = this.store.getAttempts(sessionId);
    const latest = attempts[attempts.length - 1];
    if (!latest) throw new DomainError("NO_GROUNDED_DIAGNOSIS", 409);
    const diagnosisCode = latest.error_code as MisconceptionId | null;
    if (!diagnosisCode || !answerKey.allowedSources[diagnosisCode]) throw new DomainError("NO_GROUNDED_DIAGNOSIS", 409);
    const expectedLevel = session.hint_level + 1;
    if (input.level !== expectedLevel || input.level > 3) throw new DomainError("HINT_SEQUENCE_INVALID", 409);
    let result: CoachResult;
    if (input.level === 3) {
      const hint = reviewedHint(diagnosisCode, 3);
      result = { provider: "offline", model: null, draft: { action: "diagnose_and_hint", diagnosisCode, confidence: "high", hintLevel: 3, citationIds: hint.citationIds, learnerMessage: hint.text } };
    } else {
      result = await this.callCoach(session, latest, diagnosisCode, input.level as 1 | 2, latest.answer_text, latest.explanation);
    }
    const next = this.transition(session, "retry", input.level);
    this.store.appendEvent(sessionId, "hint_shown", { attempt_no: latest.sequence, hint_level: input.level, citation_ids: result.draft.citationIds, provider: result.provider, fallback_reason: result.fallbackReason ?? null });
    return { stateVersion: next.state_version, coach: this.coachPayload(result, "hint"), next: { state: "retry", allowedAttemptsRemaining: 3 - attempts.length } };
  }

  submitExplainBack(sessionId: string, input: ExplainInput): ApiResponse {
    const parsed = ExplainBody.safeParse(input);
    if (!parsed.success) throw new DomainError("INVALID_BODY", 400, parsed.error.message);
    const session = this.requireSession(sessionId);
    if (input.stateVersion !== session.state_version) throw new DomainError("STATE_VERSION_CONFLICT", 409);
    if (session.state !== "explain_back") throw new DomainError("INVALID_STATE", 409);
    const evaluation = evaluateExplainBack(input.text);
    this.store.appendEvent(sessionId, "explain_back_submitted", { input_chars: input.text.length, claims: evaluation.claims, missing_claim_ids: evaluation.missingClaimIds, pass: evaluation.pass });
    const nextState = evaluation.pass ? "transfer_check" : "explain_back";
    const next = this.transition(session, nextState);
    return { stateVersion: next.state_version, evaluation: { status: evaluation.pass ? "pass" : "needs_revision", missingClaimIds: evaluation.missingClaimIds, claims: evaluation.claims }, next: { state: nextState } };
  }

  submitTransfer(sessionId: string, input: TransferInput): ApiResponse {
    const parsed = TransferBody.safeParse(input);
    if (!parsed.success) throw new DomainError("INVALID_BODY", 400, parsed.error.message);
    const session = this.requireSession(sessionId);
    if (input.stateVersion !== session.state_version) throw new DomainError("STATE_VERSION_CONFLICT", 409);
    if (session.state !== "transfer_check") throw new DomainError("INVALID_STATE", 409);
    const pass = evaluateTransfer(input.answer, input.reasoning);
    this.store.appendEvent(sessionId, "transfer_submitted", { input_chars: input.answer.length + input.reasoning.length, pass });
    const nextState = pass ? "completed" : "transfer_check";
    const next = this.transition(session, nextState);
    if (pass) this.store.appendEvent(sessionId, "session_completed", { mastery_status: "demonstrated_in_session", next_action: "open_source" });
    return { stateVersion: next.state_version, evaluation: { status: pass ? "pass" : "needs_revision" }, next: { state: nextState } };
  }

  abstain(sessionId: string, stateVersion: number): ApiResponse {
    const session = this.requireSession(sessionId);
    if (!["attempt_1_open", "diagnosis", "retry", "clarify", "source_review"].includes(session.state)) throw new DomainError("INVALID_STATE", 409);
    const next = this.transition(session, "source_review");
    this.store.appendEvent(sessionId, "fallback_used", { fallback_reason: "user_requested_no_basis", evidence_ids: [], next_action: "source_or_retry" });
    return { stateVersion: next.state_version, next: { state: "source_review" } };
  }

  resume(sessionId: string, stateVersion: number): ApiResponse {
    const session = this.requireSession(sessionId);
    if (stateVersion !== session.state_version) throw new DomainError("STATE_VERSION_CONFLICT", 409);
    if (!["source_review", "out_of_scope", "clarify"].includes(session.state)) throw new DomainError("INVALID_STATE", 409);
    const nextState = this.store.getAttempts(sessionId).length ? "retry" : "attempt_1_open";
    const next = this.transition(session, nextState);
    return { stateVersion: next.state_version, next: { state: nextState }, session: publicSession(next, this.store.getAttempts(sessionId)) };
  }

  private transition(session: SessionRow, nextState: SessionState, hintLevel?: number): SessionRow {
    if (!validTransition(session.state, nextState)) throw new DomainError("INVALID_TRANSITION", 409);
    return this.store.updateSession(session.id, session.state_version, nextState, hintLevel);
  }

  private requireSession(sessionId: string): SessionRow {
    const session = this.store.getSession(sessionId);
    if (!session) throw new DomainError("SESSION_NOT_FOUND", 404);
    if (new Date(session.expires_at).getTime() < Date.now()) throw new DomainError("SESSION_EXPIRED", 410);
    return session;
  }

  private async callCoach(session: SessionRow, attempt: AttemptRow | undefined, diagnosisCode: MisconceptionId, hintLevel: 0 | 1 | 2, answer: string, explanation: string): Promise<CoachResult> {
    if ((session.llm_calls >= 2) && hintLevel < 3) {
      const hint = reviewedHint(diagnosisCode, hintLevel || 1);
      return { provider: "offline", model: null, fallbackReason: "llm_budget_exhausted", draft: { action: "diagnose_and_hint", diagnosisCode, confidence: "high", hintLevel: hintLevel || null, citationIds: hint.citationIds, learnerMessage: hint.text } };
    }
    if (this.modelMode === "live") this.store.incrementLlmCalls(session.id);
    const allowedSources: ApprovedSource[] = (answerKey.allowedSources[diagnosisCode] ?? []).map((id) => getSource(id)).filter((source): source is ApprovedSource => Boolean(source));
    let result = await this.coach.generate({ attemptNo: attempt?.sequence ?? 1, diagnosisCode, hintLevel, learnerAnswer: answer, learnerReasoning: explanation, allowedSources });
    const checked = verifyCoachDraft(result.draft, [diagnosisCode], hintLevel, hintLevel < 3);
    if (!checked.ok) {
      const safeHint = reviewedHint(diagnosisCode, hintLevel === 0 ? 1 : hintLevel);
      result = {
        provider: "offline",
        model: null,
        fallbackReason: `verifier_${checked.reason}`,
        draft: {
          action: "diagnose_and_hint",
          diagnosisCode,
          confidence: "high",
          hintLevel: hintLevel === 0 ? null : hintLevel,
          citationIds: safeHint.citationIds,
          learnerMessage: hintLevel === 0 ? `Mình thấy bài làm của bạn đang dùng một giả định cần kiểm tra: ${diagnosisCode}.` : safeHint.text
        }
      };
    }
    const verified = result.draft;
    this.store.insertCoachOutput({ attempt_id: attempt?.id ?? null, provider: result.provider, model: result.model, raw_status: result.fallbackReason ? "fallback" : "ok", verified_status: "accepted", diagnosis_code: verified.diagnosisCode, confidence_band: verified.confidence, hint_level: verified.hintLevel, citation_ids_json: JSON.stringify(verified.citationIds), fallback_reason: result.fallbackReason ?? null });
    return result;
  }

  private coachPayload(result: CoachResult, status: string) {
    return { status, provider: result.provider, model: result.model, fallback: Boolean(result.fallbackReason), fallbackReason: result.fallbackReason ?? null, confidence: result.draft.confidence, diagnosisCode: result.draft.diagnosisCode, message: result.draft.learnerMessage, hint: result.draft.hintLevel ? { level: result.draft.hintLevel, text: result.draft.learnerMessage, citations: citations(result.draft.citationIds) } : null, citations: citations(result.draft.citationIds) };
  }
}

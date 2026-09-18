import React from "react";
import { Icon } from "./icons.jsx";
import { PdfCanvas, useElementWidth } from "./pdf.jsx";
import { AnswerFields, pad } from "./prequiz.jsx";

const STEPS = ["Pre-quiz", "Đối chiếu slide", "Giảng lại", "Case chuyển giao"];

function stepIndex(answerState, slideReviewed) {
  if (answerState === "result") return 4;
  if (answerState === "transfer") return 3;
  if (answerState === "explain") return slideReviewed ? 2 : 1;
  return 1;
}

function ClaimList({ claims, pending }) {
  if (!claims?.length) return null;
  return (
    <ul className="claim-list">
      {claims.map(row => {
        const state = pending || row.present == null ? "wait" : row.present ? "yes" : "no";
        return (
          <li key={row.label} className={state}>
            <span>{state === "yes" ? <Icon name="check" size={13} strokeWidth={2.6} /> : state === "no" ? "!" : "·"}</span>
            {row.label}
          </li>
        );
      })}
    </ul>
  );
}

function CoachNote({ coach, tone = "", onCite }) {
  if (!coach?.message) return null;
  return (
    <div className={`coach-box ${tone}`}>
      <b>Nhận xét</b>
      <p>{coach.message}</p>
      {coach.citations?.length > 0 && (
        <p className="coach-cite">
          Xem lại:{" "}
          {coach.citations.map(item => (
            <button
              type="button"
              key={item.sourceId}
              className="cite-link"
              onClick={() => item.page && onCite?.(item.page)}
            >
              {item.sourceId}{item.page ? ` · trang ${item.page}` : ""}
            </button>
          ))}
        </p>
      )}
    </div>
  );
}

export function TeacherNotes({ section, unlocked, onLoadInsight }) {
  return (
    <>
      <div className="notes-head">
        <Icon name="fileText" size={22} />
        <h2>Ghi chú của giảng viên</h2>
      </div>
      <p className="notes-empty">
        {section
          ? unlocked
            ? "Chưa có ghi chú của giảng viên cho slide này."
            : `Làm pre-quiz Phần ${pad(section.number)} để mở slide trọng tâm và lời giải thích.`
          : "Chưa có ghi chú của giảng viên cho slide này."}
      </p>
      {section && unlocked && (
        <button type="button" className="btn-soft" onClick={onLoadInsight}>
          <Icon name="sparkles" size={16} /> Xem kiến thức trọng tâm
        </button>
      )}
    </>
  );
}

function KeySlide({ doc, slide, onJump }) {
  const [frameRef, width] = useElementWidth();
  return (
    <button type="button" className="key-slide" ref={frameRef} onClick={() => onJump(slide.page)} title="Mở slide này ở khung trên">
      <PdfCanvas doc={doc} page={slide.page} width={width} className="key-canvas" />
      <span className="key-open"><Icon name="arrowUp" size={14} /> Mở ở khung slide</span>
    </button>
  );
}

export function InsightPanel({ doc, section, flow, onKeyPage, onJump, onReload, actions }) {
  const data = flow.insight;
  const keySlides = data?.keySlides || [];
  const insight = data?.insight;
  const activePage = flow.keyPage || insight?.focusPage || keySlides[0]?.page;
  const activeSlide = keySlides.find(slide => slide.page === activePage) || keySlides[0];
  const current = stepIndex(flow.answerState, flow.slideReviewed);

  return (
    <>
      <div className="insight-head">
        <span className="insight-avatar"><Icon name="sparkles" size={22} /></span>
        <div className="insight-title">
          <p>Thay cho ghi chú của giảng viên · tóm tắt từ slide trọng tâm</p>
          <h2>Kiến thức trọng tâm · Phần {pad(section.number)} {section.title}</h2>
        </div>
      </div>

      {flow.insightState === "loading" && (
        <div className="insight-loading" role="status">
          <span className="mini-spinner" />
          <div>
            <b>Đang đối chiếu slide trọng tâm</b>
            <p>Đọc chữ trên slide, nguồn đã duyệt và câu trả lời pre-quiz của bạn…</p>
          </div>
        </div>
      )}

      {flow.insightState === "error" && (
        <div className="insight-loading error" role="alert">
          <div>
            <b>Chưa tải được kiến thức trọng tâm</b>
            <p>{flow.insightError}</p>
          </div>
          <button type="button" className="btn-soft" onClick={onReload}>Thử lại</button>
        </div>
      )}

      {insight && activeSlide && (
        <div className="insight-grid">
          <div className="insight-slide">
            <div className="key-tabs" role="tablist" aria-label="Slide trọng tâm">
              {keySlides.map(slide => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={slide.page === activeSlide.page}
                  key={slide.page}
                  className={slide.page === activeSlide.page ? "on" : ""}
                  onClick={() => onKeyPage(slide.page)}
                >
                  {slide.page === insight.focusPage && <Icon name="target" size={13} />}
                  Trang {slide.page}{slide.page === insight.focusPage ? " · trọng tâm" : ""}
                </button>
              ))}
            </div>
            <KeySlide doc={doc} slide={activeSlide} onJump={onJump} />
            {activeSlide.excerpts.map((excerpt, index) => (
              <blockquote className="key-source" key={activeSlide.sourceIds[index]}>
                <b>Nguồn đã duyệt · {activeSlide.sourceIds[index]}</b>
                {excerpt}
              </blockquote>
            ))}
          </div>

          <div className="insight-copy">
            <h3>{insight.headline}</h3>
            <p className="insight-explain">{insight.explanation}</p>
            <h4>Ý chính cần nhớ</h4>
            <ul className="key-points">
              {insight.keyPoints.map(point => <li key={point}>{point}</li>)}
            </ul>
            <p className="insight-why"><Icon name="lightbulb" size={18} /><span>{insight.whyThisSlide}</span></p>
            <div className="insight-reflect">
              <b>Tự kiểm tra</b>
              <p>{insight.reflectionQuestion}</p>
            </div>
          </div>
        </div>
      )}

      <div className="reinforce">
        <div className="reinforce-head">
          <h3>Củng cố hiểu biết</h3>
          <ol className="steps">
            {STEPS.map((label, index) => {
              const cls = index < current ? "done" : index === current ? "now" : "";
              const canJump = index === 1 || (index === 2 && flow.slideReviewed) || (index === 3 && (flow.answerState === "transfer" || flow.answerState === "result"));
              return (
                <li key={label} className={cls}>
                  <button
                    type="button"
                    className="step-hit"
                    disabled={!canJump && index !== current}
                    onClick={() => {
                      if (index === 1) {
                        const page = insight?.focusPage || keySlides[0]?.page;
                        if (page) onJump(page);
                      }
                      if (index === 2 && flow.answerState === "explain") actions.markReviewed();
                    }}
                  >
                    <span>{index < current ? <Icon name="check" size={13} strokeWidth={2.6} /> : index + 1}</span>
                    {label}
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
        <Reinforcement section={section} flow={flow} actions={actions} onJump={onJump} />
      </div>
    </>
  );
}

function Reinforcement({ section, flow, actions, onJump }) {
  const { answerState, coach, busy } = flow;
  const explainClaims = answerState === "explain" && flow.evaluation?.claims
    ? flow.evaluation.claims
    : flow.insight?.reinforce?.explain || [];
  const transferClaims = answerState === "transfer" && flow.evaluation?.claims
    ? flow.evaluation.claims
    : flow.insight?.reinforce?.transfer || [];
  const focusPage = flow.insight?.insight?.focusPage || flow.insight?.keySlides?.[0]?.page;

  if (!flow.session) {
    return (
      <div className="reinforce-body">
        <p className="muted">Phần này đã mở từ lần học trước nên không còn phiên pre-quiz đang chạy.</p>
        <button type="button" className="btn-soft" onClick={actions.restart} disabled={flow.phase === "loading"}>
          <Icon name="rotate" size={16} /> {flow.phase === "loading" ? "Đang soạn câu hỏi…" : "Làm lại pre-quiz phần này"}
        </button>
      </div>
    );
  }

  if (answerState === "attempt" || answerState === "diagnosis" || answerState === "retry") {
    const nextHint = (coach?.hint?.level || 0) + 1;
    const kind = answerState === "attempt" ? "attempt_1" : "retry";
    return (
      <div className="reinforce-body">
        {coach?.message && (
          <div className={`coach-box ${coach.hint ? "hint" : "diagnosis"}`}>
            <b>{coach.hint ? `Gợi ý ${coach.hint.level}/3` : "Giả định cần kiểm tra"}</b>
            <p>{coach.message}</p>
            {coach.citations?.length > 0 && (
              <p className="coach-cite">Nguồn: {coach.citations.map(c => c.sourceId).join(", ")}</p>
            )}
          </div>
        )}
        {answerState !== "attempt" && (
          <p className="muted">Đọc slide trọng tâm bên trên, rồi sửa câu trả lời. Phần này chỉ ra giả định, không chép đáp án giúp.</p>
        )}
        {answerState !== "attempt" && nextHint <= 3 && (
          <button type="button" className="btn-soft" onClick={() => actions.hint(nextHint)} disabled={busy}>
            <Icon name="lightbulb" size={16} /> Mở gợi ý {nextHint}/3
          </button>
        )}
        <form
          className="retry-form"
          onSubmit={event => {
            event.preventDefault();
            actions.submit(kind);
          }}
        >
          <p className="retry-title">{kind === "retry" ? "Sau khi đọc slide trọng tâm, sửa lại câu trả lời:" : "Trả lời pre-quiz:"}</p>
          <p className="retry-statement">{flow.item?.statement}</p>
          <AnswerFields draft={flow.retryDraft} onChange={actions.retryDraft} idPrefix={`retry-${section.sectionId}`} compact />
          {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
          <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Đang chẩn đoán…" : "Gửi câu trả lời đã sửa"}</button>
        </form>
      </div>
    );
  }

  if (answerState === "explain" && !flow.slideReviewed) {
    return (
      <div className="reinforce-body">
        <CoachNote coach={coach} tone="good" onCite={onJump} />
        <div className="coach-box">
          <b>Bước này: đối chiếu slide</b>
          <p>
            Mở slide có icon đích bên trên. Đọc excerpt đã duyệt. Việc này để bạn sửa giả định —
            không phải để chép lại cho bước giảng.
          </p>
        </div>
        <div className="reinforce-actions">
          {focusPage && (
            <button type="button" className="btn-soft" onClick={() => onJump(focusPage)}>
              <Icon name="target" size={16} /> Mở slide trọng tâm (trang {focusPage})
            </button>
          )}
          <button type="button" className="btn-primary" onClick={actions.markReviewed}>
            Đã xem slide · bắt đầu giảng lại
          </button>
        </div>
      </div>
    );
  }

  if (answerState === "explain") {
    const pending = !explainClaims.some(row => row.present != null);
    return (
      <form
        className="reinforce-body"
        onSubmit={event => {
          event.preventDefault();
          actions.explain();
        }}
      >
        <CoachNote coach={coach} tone={coach?.status === "pass" ? "good" : coach?.status === "needs_revision" ? "warn" : "good"} onCite={onJump} />
        <div>
          <p className="retry-title">Nói lại 3 ý dưới đây bằng lời của bạn — diễn đạt khác vẫn được, không cần chép slide.</p>
          <ClaimList claims={explainClaims} pending={pending} />
        </div>
        <label className="field">
          <span>Giảng lại ý chính</span>
          <textarea
            rows={4}
            maxLength={800}
            required
            value={flow.explain}
            onChange={event => actions.setExplain(event.target.value)}
            placeholder="Ý chính là… khác với… vì… (một đoạn 3–5 câu là đủ)"
          />
          <small className="char-count">{flow.explain.length}/800</small>
        </label>
        {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Đang đối chiếu…" : "Gửi phần giảng lại"}</button>
      </form>
    );
  }

  if (answerState === "transfer") {
    const pending = !transferClaims.some(row => row.present != null);
    return (
      <form
        className="reinforce-body"
        onSubmit={event => {
          event.preventDefault();
          actions.transfer();
        }}
      >
        <div className="coach-box">
          <b>Case chuyển giao</b>
          <p>{flow.item?.transfer?.prompt}</p>
        </div>
        <CoachNote coach={coach} tone={coach?.status === "needs_revision" ? "warn" : "good"} onCite={onJump} />
        <p className="retry-title">Case này cần chạm các ý sau — viết hướng xử lý, không chép lý thuyết.</p>
        <ClaimList claims={transferClaims} pending={pending} />
        <label className="field">
          <span>Bạn sẽ làm gì?</span>
          <textarea rows={2} maxLength={800} required value={flow.transfer.answer} onChange={event => actions.setTransfer({ ...flow.transfer, answer: event.target.value })} placeholder="Mình chọn… vì task cần…" />
        </label>
        <label className="field">
          <span>Vì sao / khi nào cách đó đúng?</span>
          <textarea rows={2} maxLength={800} required value={flow.transfer.reasoning} onChange={event => actions.setTransfer({ ...flow.transfer, reasoning: event.target.value })} placeholder="Chỉ thêm role/context khi…" />
        </label>
        {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Đang đối chiếu…" : "Gửi case chuyển giao"}</button>
      </form>
    );
  }

  if (answerState === "result") {
    return (
      <div className="reinforce-body done">
        <span className="done-mark"><Icon name="check" size={24} strokeWidth={2.6} /></span>
        <div>
          <b>Đã chứng minh Phần {pad(section.number)}</b>
          <p className="muted">Slide phần này giữ mở. Phần tiếp theo đã sẵn sàng.</p>
        </div>
        <button type="button" className="btn-primary" onClick={actions.next}>Sang phần tiếp theo <Icon name="chevronRight" size={16} /></button>
      </div>
    );
  }

  // safe / scope: the backend refused to guess a misconception.
  return (
    <div className="reinforce-body">
      <div className="coach-box warn">
        <b>{answerState === "scope" ? "Ngoài phạm vi bài" : "Chưa đủ căn cứ để kết luận"}</b>
        <p>{coach?.message || "Hãy đọc slide trọng tâm rồi quay lại bài làm."}</p>
      </div>
      {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
      <button type="button" className="btn-soft" onClick={actions.resume} disabled={busy}>Quay lại bài làm</button>
    </div>
  );
}

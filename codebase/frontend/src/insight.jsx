import React from "react";
import { Icon } from "./icons.jsx";
import { PdfCanvas, useElementWidth } from "./pdf.jsx";
import { AnswerFields, GenerationBadge, pad } from "./prequiz.jsx";

const STEPS = ["Pre-quiz", "Đối chiếu slide", "Giảng lại", "Case chuyển giao"];

function stepIndex(answerState) {
  if (answerState === "explain") return 2;
  if (answerState === "transfer") return 3;
  if (answerState === "result") return 4;
  return 1;
}

function generationOf(insight) {
  const g = insight?.generation;
  if (!g) return null;
  return { state: g.generated ? "live" : "reviewed", model: g.model, fallbackReason: g.fallbackReason };
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
            : `Làm pre-quiz Phần ${pad(section.number)} để AI Agent thay phần này bằng slide trọng tâm và lời giải thích.`
          : "Chưa có ghi chú của giảng viên cho slide này."}
      </p>
      {section && unlocked && (
        <button type="button" className="btn-soft" onClick={onLoadInsight}>
          <Icon name="sparkles" size={16} /> Xem kiến thức trọng tâm do Agent tổng hợp
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
  const current = stepIndex(flow.answerState);

  return (
    <>
      <div className="insight-head">
        <span className="insight-avatar"><Icon name="sparkles" size={22} /></span>
        <div className="insight-title">
          <p>Thay cho ghi chú của giảng viên · AI Agent tổng hợp từ slide</p>
          <h2>Kiến thức trọng tâm · Phần {pad(section.number)} {section.title}</h2>
        </div>
        <GenerationBadge generation={generationOf(data)} liveLabel="Giải thích AI thật" reviewedLabel="Giải thích từ nguồn đã duyệt" />
      </div>

      {flow.insightState === "loading" && (
        <div className="insight-loading" role="status">
          <span className="mini-spinner" />
          <div>
            <b>Explanation Agent đang đối chiếu slide trọng tâm</b>
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
            {STEPS.map((label, index) => (
              <li key={label} className={index < current ? "done" : index === current ? "now" : ""}>
                <span>{index < current ? <Icon name="check" size={13} strokeWidth={2.6} /> : index + 1}</span>
                {label}
              </li>
            ))}
          </ol>
        </div>
        <Reinforcement section={section} flow={flow} actions={actions} />
      </div>
    </>
  );
}

function Reinforcement({ section, flow, actions }) {
  const { answerState, coach, busy } = flow;

  if (!flow.session) {
    return (
      <div className="reinforce-body">
        <p className="muted">Phần này đã mở từ lần học trước nên không còn phiên pre-quiz đang chạy.</p>
        <button type="button" className="btn-soft" onClick={actions.restart} disabled={flow.phase === "loading"}>
          <Icon name="rotate" size={16} /> {flow.phase === "loading" ? "Agent đang soạn câu hỏi…" : "Làm lại pre-quiz phần này"}
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
            <b>{coach.hint ? `Gợi ý ${coach.hint.level}/3` : "Chẩn đoán từ Agent"}</b>
            <p>{coach.message}</p>
            {coach.citations?.length > 0 && (
              <p className="coach-cite">Nguồn: {coach.citations.map(c => c.sourceId).join(", ")}</p>
            )}
          </div>
        )}
        {answerState !== "attempt" && nextHint <= 3 && (
          <button type="button" className="btn-soft" onClick={() => actions.hint(nextHint)} disabled={busy}>
            <Icon name="lightbulb" size={16} /> Mở gợi ý {nextHint}
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

  if (answerState === "explain") {
    return (
      <form
        className="reinforce-body"
        onSubmit={event => {
          event.preventDefault();
          actions.explain();
        }}
      >
        {coach?.message && <div className="coach-box good"><b>Agent</b><p>{coach.message}</p></div>}
        <label className="field">
          <span>Giảng lại ý chính bằng lời của bạn (không chép slide)</span>
          <textarea rows={3} maxLength={500} required value={flow.explain} onChange={event => actions.setExplain(event.target.value)} placeholder="Ý chính của phần này là…" />
        </label>
        {flow.notice && <p className="form-note">{flow.notice}</p>}
        {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Đang kiểm tra…" : "Gửi phần giảng lại"}</button>
      </form>
    );
  }

  if (answerState === "transfer") {
    return (
      <form
        className="reinforce-body"
        onSubmit={event => {
          event.preventDefault();
          actions.transfer();
        }}
      >
        <div className="coach-box"><b>Case chuyển giao</b><p>{flow.item?.transfer?.prompt}</p></div>
        <label className="field">
          <span>Hướng xử lý</span>
          <textarea rows={2} maxLength={500} required value={flow.transfer.answer} onChange={event => actions.setTransfer({ ...flow.transfer, answer: event.target.value })} />
        </label>
        <label className="field">
          <span>Vì sao / điều kiện áp dụng</span>
          <textarea rows={2} maxLength={500} required value={flow.transfer.reasoning} onChange={event => actions.setTransfer({ ...flow.transfer, reasoning: event.target.value })} />
        </label>
        {flow.notice && <p className="form-note">{flow.notice}</p>}
        {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
        <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Đang kiểm tra…" : "Gửi case chuyển giao"}</button>
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

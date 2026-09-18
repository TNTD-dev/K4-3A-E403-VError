import React from "react";
import { Icon } from "./icons.jsx";

export const CONFIDENCE = ["Chắc", "Khá chắc", "Chưa chắc"];
export const BASIS = ["Đã học trước đó", "Suy luận", "Đoán", "Chưa có căn cứ"];

export const pad = number => String(number).padStart(2, "0");

export function ChoiceGroup({ legend, name, options, value, onChange }) {
  return (
    <fieldset className="choice-group">
      <legend>{legend}</legend>
      <div className="chips">
        {options.map(option => (
          <label key={option} className={`chip ${value === option ? "on" : ""}`}>
            <input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)} />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function AnswerFields({ draft, onChange, idPrefix, compact = false }) {
  const set = key => event => onChange({ ...draft, [key]: event.target.value });
  return (
    <>
      <div className="field-pair">
        <label className="field">
          <span>Câu trả lời của bạn</span>
          <textarea id={`${idPrefix}-answer`} rows={3} maxLength={500} required value={draft.answer} onChange={set("answer")} placeholder="Mình đồng ý / không đồng ý vì..." />
        </label>
        <label className="field">
          <span>Vì sao bạn nghĩ vậy?</span>
          <textarea id={`${idPrefix}-why`} rows={3} maxLength={500} required value={draft.explanation} onChange={set("explanation")} placeholder="Giả định mình đang dùng là..." />
        </label>
      </div>
      <div className="choice-row">
        <ChoiceGroup legend="Mức độ chắc chắn" name={`${idPrefix}-confidence`} options={CONFIDENCE} value={draft.confidence} onChange={value => onChange({ ...draft, confidence: value })} />
        {!compact && (
          <ChoiceGroup legend="Bạn đang dựa vào đâu?" name={`${idPrefix}-basis`} options={BASIS} value={draft.basis} onChange={value => onChange({ ...draft, basis: value })} />
        )}
      </div>
    </>
  );
}

/** Everything that sits on top of a blurred slide. */
export function PreQuizLayer({ gate, section, flow, pending, onStart, onDraft, onSubmit, onGoPending }) {
  if (gate === "loading") {
    return (
      <div className="stage-layer">
        <div className="prequiz-card compact" role="status">
          <span className="agent-orb"><span className="mini-spinner" /></span>
          <h3>Đang đọc cấu trúc bài học</h3>
          <p className="muted">Đang gắn pre-quiz vào đúng phần trong slide…</p>
        </div>
      </div>
    );
  }

  if (gate === "offline") {
    return (
      <div className="stage-layer">
        <div className="prequiz-card compact" role="alert">
          <span className="agent-orb warn">!</span>
          <h3>Chưa kết nối được VError API</h3>
          <p className="muted">Slide sau trang bìa được giữ lại cho đến khi tải được tiến độ học.</p>
          <button type="button" className="btn-primary" onClick={() => window.location.reload()}>Tải lại</button>
        </div>
      </div>
    );
  }

  if (gate === "locked") {
    return (
      <div className="stage-layer">
        <div className="prequiz-card compact">
          <span className="agent-orb locked"><Icon name="lock" size={22} /></span>
          <p className="pq-chip">Phần {pad(section.number)} · {section.title}</p>
          <h3>Phần này chưa mở</h3>
          <p className="muted">
            VLearn mở từng phần theo thứ tự. Hãy thử pre-quiz của
            {pending ? ` Phần ${pad(pending.number)} · ${pending.title}` : " phần trước"} để mở khóa phần này.
          </p>
          {pending && (
            <button type="button" className="btn-primary" onClick={() => onGoPending(pending)}>
              Làm pre-quiz Phần {pad(pending.number)}
            </button>
          )}
        </div>
      </div>
    );
  }

  if (gate !== "quiz") return null;

  if (flow.phase === "error") {
    return (
      <div className="stage-layer">
        <div className="prequiz-card compact" role="alert">
          <span className="agent-orb warn">!</span>
          <h3>Chưa tạo được pre-quiz</h3>
          <p className="muted">{flow.error}</p>
          <button type="button" className="btn-primary" onClick={onStart}>Thử lại</button>
        </div>
      </div>
    );
  }

  if (flow.phase !== "form") {
    return (
      <div className="stage-layer">
        <div className="prequiz-card compact" role="status">
          <span className="agent-orb"><span className="mini-spinner" /></span>
          <p className="pq-chip">Pre-quiz · Phần {pad(section.number)}</p>
          <h3>Đang soạn câu hỏi</h3>
          <p className="muted">
            Phần này bắt đầu từ <b>trang {section.titlePage}</b> — “{section.title}”.
            Đặt một câu hỏi trước khi bạn đọc tiếp…
          </p>
        </div>
      </div>
    );
  }

  const item = flow.item || {};
  return (
    <div className="stage-layer">
      <form
        className="prequiz-card"
        onSubmit={event => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <div className="pq-top">
          <span className="pq-chip">Pre-quiz · Phần {pad(section.number)}</span>
        </div>
        <p className="pq-context">
          <Icon name="sparkles" size={16} />
          <span>Trang {section.titlePage} là tiêu đề “{section.title}”. Dự đoán trước — slide mở ngay khi bạn gửi.</span>
        </p>
        <h3>{item.title}</h3>
        <blockquote className="pq-statement">{item.statement}</blockquote>
        <p className="pq-task">{item.taskText}</p>
        <AnswerFields draft={flow.draft} onChange={onDraft} idPrefix={`pq-${section.sectionId}`} />
        {flow.error && <p className="form-error" role="alert">{flow.error}</p>}
        <div className="pq-foot">
          <span>Không chấm điểm — đây là cú thử trước khi học.</span>
          <button type="submit" className="btn-primary" disabled={flow.busy}>
            {flow.busy ? "Đang gửi…" : "Gửi & mở slide"}
          </button>
        </div>
      </form>
    </div>
  );
}

function toastCopy(flow, keyCount) {
  const status = flow.evaluation?.status;
  if (status === "incorrect") return `Có một giả định cần đối chiếu với ${keyCount || "các"} slide trọng tâm.`;
  if (status === "correct") return "Bạn đang đúng hướng — xem slide trọng tâm để giảng lại chắc hơn.";
  if (status === "out_of_scope") return "Câu trả lời đi ra ngoài phạm vi bài — đọc slide trọng tâm để thu hẹp lại.";
  return "Chưa đủ căn cứ để kết luận — đọc slide trọng tâm rồi thử lại.";
}

export function QuizToast({ flow, keyCount, onGo, onClose }) {
  return (
    <div className="quiz-toast" role="status">
      <span className="toast-icon"><Icon name="check" size={18} strokeWidth={2.4} /></span>
      <div className="toast-copy">
        <b>Đã gửi pre-quiz · slide đã mở</b>
        <p>{toastCopy(flow, keyCount)}</p>
      </div>
      <button type="button" className="btn-primary" onClick={onGo}>
        Đi đến kiến thức trọng tâm <Icon name="arrowDown" size={16} />
      </button>
      <button type="button" className="icon-btn" aria-label="Đọc tiếp slide" onClick={onClose}><Icon name="x" size={18} /></button>
    </div>
  );
}

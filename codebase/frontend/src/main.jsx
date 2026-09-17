import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_BASE || "";
const PDF = "/prompt-engineering-tool-calling.pdf";
const initial = { answer: "", explanation: "", confidence: "", basis: "" };

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || data.error || "Có lỗi xảy ra");
  return data;
}

function SourceDrawer({ source, close }) {
  if (!source) return null;
  return (
    <div className="overlay" onClick={close}>
      <aside className="drawer" onClick={e => e.stopPropagation()}>
        <button className="close" onClick={close}>×</button>
        <p className="eyebrow">Nguồn đã duyệt</p>
        <h2>{source.locator}</h2>
        <blockquote>{source.excerpt}</blockquote>
        <p className="muted">Duyệt bởi {source.approvedBy}</p>
        {source.approvedLocations.map(location => (
          <div className="location" key={location.label}>
            <b>{location.kind}</b>
            <span>{location.label}</span>
          </div>
        ))}
      </aside>
    </div>
  );
}

function Choice({ label, name, value, selected, set }) {
  return (
    <label className={`choice ${selected === value ? "selected" : ""}`}>
      <input type="radio" name={name} value={value} checked={selected === value} onChange={e => set(e.target.value)} />
      {label}
    </label>
  );
}

function App() {
  const [nav, setNav] = useState("slides");
  const [sections, setSections] = useState([]);
  const [day, setDay] = useState(null);
  const [selectedSection, setSelectedSection] = useState("prompt-fundamentals");
  const [itemBundle, setItemBundle] = useState(null);
  const [session, setSession] = useState(null);
  const [draft, setDraft] = useState(initial);
  const [answerState, setAnswerState] = useState("idle");
  const [coach, setCoach] = useState(null);
  const [source, setSource] = useState(null);
  const [explain, setExplain] = useState("");
  const [transfer, setTransfer] = useState({ answer: "", reasoning: "" });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [pdfPage, setPdfPage] = useState(6);
  const [askOpen, setAskOpen] = useState(false);

  const active = useMemo(
    () => sections.find(item => item.sectionId === selectedSection) || sections[0],
    [sections, selectedSection],
  );
  const slidesOpen = Boolean(active && !active.slidesLocked);
  const attemptOpen = Boolean(active && !active.attemptLocked);
  const completedCount = sections.filter(item => item.completed).length;
  const progressPct = day?.progressPercent ?? Math.round((completedCount / Math.max(sections.length, 1)) * 100);
  const stateVersion = session?.stateVersion || 1;
  const item = itemBundle?.item;

  async function refreshSections() {
    const result = await request("/api/v1/sections");
    setSections(result.sections);
    setDay(result.day);
    return result;
  }

  async function loadItem(sectionId) {
    const bundle = await request(`/api/v1/sections/${sectionId}/item`);
    setItemBundle(bundle);
    return bundle;
  }

  useEffect(() => {
    refreshSections()
      .then(result => {
        const firstOpen = result.sections.find(item => !item.attemptLocked) || result.sections[0];
        if (firstOpen) {
          setSelectedSection(firstOpen.sectionId);
          setPdfPage(firstOpen.pages?.[0] || 6);
          return loadItem(firstOpen.sectionId);
        }
        return null;
      })
      .catch(e => setMessage(e.message));
  }, []);

  useEffect(() => {
    if (!active) return;
    if (slidesOpen) setPdfPage(active.pages?.[0] || 6);
    loadItem(active.sectionId).catch(e => setMessage(e.message));
    setSession(null);
    setCoach(null);
    setAnswerState(slidesOpen ? "review" : "idle");
    setDraft(initial);
    setExplain("");
    setTransfer({ answer: "", reasoning: "" });
    setMessage("");
  }, [selectedSection]);

  useEffect(() => {
    const pages = coach?.highlight?.pages?.filter(Boolean);
    if (pages?.length) setPdfPage(pages[0]);
  }, [coach]);

  function applyProgress(progress) {
    if (!progress) return;
    setSections(current =>
      current.map(item => ({
        ...item,
        attemptLocked: !progress.unlockedAttempts.includes(item.sectionId),
        slidesLocked: !progress.unlockedSlides.includes(item.sectionId),
        locked: !progress.unlockedAttempts.includes(item.sectionId),
        completed: progress.completedSections.includes(item.sectionId),
      })),
    );
    setDay(d =>
      d
        ? {
            ...d,
            completedSections: progress.completedSections.length,
            progressPercent: Math.round((progress.completedSections.length / Math.max(d.totalSections || 8, 1)) * 100),
          }
        : d,
    );
  }

  function mapState(next) {
    if (next === "diagnosis") return "diagnosis";
    if (next === "explain_back") return "explain";
    if (next === "transfer_check") return "transfer";
    if (next === "source_review") return "safe";
    if (next === "out_of_scope") return "scope";
    if (next === "completed") return "result";
    if (next === "retry") return "retry";
    if (next === "clarify") return "safe";
    return next;
  }

  async function startAttempt() {
    if (!attemptOpen) return;
    setBusy(true);
    setMessage("");
    try {
      const next = await request("/api/v1/sessions", {
        method: "POST",
        body: JSON.stringify({ sectionId: selectedSection, mode: "demo" }),
      });
      setSession(next);
      setItemBundle({ item: next.item, sources: next.sources });
      setAnswerState("attempt");
      setCoach(null);
      setDraft(initial);
    } catch (e) {
      setMessage(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitAttempt(e) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const retry = answerState === "retry";
      const result = await request(`/api/v1/sessions/${session.sessionId}/attempts`, {
        method: "POST",
        headers: { "Idempotency-Key": `${retry ? "retry" : "attempt"}-${Date.now()}` },
        body: JSON.stringify({
          stateVersion,
          kind: retry ? "retry" : "attempt_1",
          answer: { text: draft.answer, explanation: draft.explanation },
          confidence: draft.confidence || undefined,
          basis: draft.basis || undefined,
        }),
      });
      setSession(s => ({ ...s, stateVersion: result.stateVersion }));
      applyProgress(result.progress);
      setCoach(result.coach);
      setAnswerState(mapState(result.next.state));
      if (result.coach?.highlight?.pages?.[0]) setPdfPage(result.coach.highlight.pages[0]);
      else if (active?.pages?.[0]) setPdfPage(active.pages[0]);
      await refreshSections();
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function hint(level) {
    setBusy(true);
    try {
      const result = await request(`/api/v1/sessions/${session.sessionId}/hints`, {
        method: "POST",
        body: JSON.stringify({ stateVersion, level }),
      });
      setSession(s => ({ ...s, stateVersion: result.stateVersion }));
      setCoach(result.coach);
      setAnswerState("retry");
      if (result.coach?.highlight?.pages?.[0]) setPdfPage(result.coach.highlight.pages[0]);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitExplain(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const result = await request(`/api/v1/sessions/${session.sessionId}/explain-back`, {
        method: "POST",
        body: JSON.stringify({ stateVersion, text: explain }),
      });
      setSession(s => ({ ...s, stateVersion: result.stateVersion }));
      setMessage(result.evaluation.status === "pass" ? "Đã đủ các ý chính của phần này." : `Còn thiếu: ${result.evaluation.missingClaimIds.join(", ")}`);
      if (result.next.state === "transfer_check") setAnswerState("transfer");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitTransfer(e) {
    e.preventDefault();
    setBusy(true);
    try {
      const result = await request(`/api/v1/sessions/${session.sessionId}/transfer`, {
        method: "POST",
        body: JSON.stringify({ stateVersion, ...transfer }),
      });
      setSession(s => ({ ...s, stateVersion: result.stateVersion }));
      applyProgress(result.progress);
      if (result.evaluation.status === "pass") {
        setMessage("Bạn đã chứng minh được phần này trong phiên học.");
        setAnswerState("result");
        await refreshSections();
      } else {
        setMessage("Hãy bám đúng ý chính của phần và nêu điều kiện áp dụng.");
      }
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function safeAction(path) {
    setBusy(true);
    try {
      const result = await request(`/api/v1/sessions/${session.sessionId}/${path}`, {
        method: "POST",
        body: JSON.stringify({ stateVersion }),
      });
      setSession(s => ({ ...s, stateVersion: result.stateVersion }));
      setAnswerState(path === "resume" ? (result.next?.state === "attempt_1_open" ? "attempt" : "retry") : "safe");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy(false);
    }
  }

  function goNextSection() {
    const index = sections.findIndex(item => item.sectionId === selectedSection);
    const next = sections.slice(index + 1).find(item => !item.attemptLocked);
    if (next) setSelectedSection(next.sectionId);
  }

  const openSource = async id => {
    try {
      const result = await request(`/api/v1/sources/${id}`);
      setSource(result.source);
      const page = result.source.approvedLocations?.find(l => l.page)?.page;
      if (page) setPdfPage(page);
    } catch (err) {
      setMessage(err.message);
    }
  };

  const phaseLabel =
    answerState === "attempt" || answerState === "idle"
      ? "1 · Thử trước"
      : answerState === "explain"
        ? "3 · Giải thích lại"
        : answerState === "transfer"
          ? "4 · Chuyển giao"
          : answerState === "result"
            ? "5 · Mở phần tiếp"
            : "2 · Chỉ ra chỗ sai";

  return (
    <>
      <Header
        day={day}
        progressPct={progressPct}
        askOpen={askOpen}
        setAskOpen={setAskOpen}
        onReset={() => window.location.reload()}
      />
      <div className="chrome-body">
        <LeftNav
          nav={nav}
          setNav={setNav}
          sections={sections}
          selected={selectedSection}
          setSelected={setSelectedSection}
        />
        <main className="day-main">
          {message && <div className="notice">{message}</div>}
          <div className="day-toolbar">
            <div>
              <p className="eyebrow">VError · trước mỗi phần kiến thức</p>
              <h1>{active?.title || "Prompt fundamentals"}</h1>
              <p className="muted">{active?.summary}</p>
            </div>
            <div className="day-progress-card">
              <div className="day-progress-bar"><div style={{ width: `${progressPct}%` }} /></div>
              <span>{completedCount}/{sections.length || 8} phần · {phaseLabel}</span>
            </div>
          </div>

          {nav === "video" && (
            <section className="panel soft">
              <h2>Video bài giảng</h2>
              <p className="muted">Timestamp video chưa có trong gói tài liệu PDF. Hãy dùng slides đã duyệt sau lần thử.</p>
            </section>
          )}

          {nav === "kc" && (
            <section className="panel soft">
              <h2>KC & Luyện tập</h2>
              <p className="muted">VError chính là lớp luyện tập trước slide. Hoàn thành 8 phần để mở toàn bộ Day 04.</p>
              <ul className="kc-list">
                {sections.map(item => (
                  <li key={item.sectionId} className={item.completed ? "done" : item.attemptLocked ? "locked" : "open"}>
                    <b>{String(item.number).padStart(2, "0")}</b>
                    <span>{item.title}</span>
                    <i>{item.completed ? "xong" : item.attemptLocked ? "khóa" : "mở"}</i>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {nav === "slides" && (
            <div className="slides-layout">
              <section className={`pdf-viewer ${slidesOpen ? "open" : "locked"} ${coach?.citations?.length ? "reviewed" : ""}`}>
                <div className="pdf-toolbar">
                  <strong>Slides · {active?.title}</strong>
                  <span>
                    {slidesOpen
                      ? `Trang ${pdfPage} · vùng ${active?.pages?.[0]}-${active?.pages?.[1]} / 43`
                      : "Khóa đến sau lần thử đầu"}
                  </span>
                </div>
                {coach?.highlight?.pages?.length ? (
                  <div className="reviewed-banner">
                    Chỗ sai được neo vào PDF p.{coach.highlight.pages.join(", p.")}
                  </div>
                ) : null}
                {slidesOpen ? (
                  <iframe title="Day 04 slide deck" src={`${PDF}#page=${pdfPage}`} />
                ) : (
                  <div className="pdf-lock">
                    <div className="lock-badge">🔒</div>
                    <h2>Slide phần này còn khóa</h2>
                    <p>Làm VError trước. Sau lần gửi đầu tiên, đúng trang PDF sẽ mở để bạn đối chiếu chỗ sai.</p>
                    {attemptOpen && answerState === "idle" && (
                      <button className="primary" onClick={startAttempt} disabled={busy}>
                        {busy ? "Đang mở..." : "Bắt đầu thử trước"}
                      </button>
                    )}
                  </div>
                )}
              </section>

              <section className="panel attempt-panel">
                {answerState === "idle" && (
                  <IdleCard
                    item={item}
                    active={active}
                    attemptOpen={attemptOpen}
                    slidesOpen={slidesOpen}
                    start={startAttempt}
                    busy={busy}
                  />
                )}
                {answerState === "review" && slidesOpen && !session && (
                  <IdleCard
                    item={item}
                    active={active}
                    attemptOpen={attemptOpen}
                    slidesOpen={slidesOpen}
                    start={startAttempt}
                    busy={busy}
                    review
                  />
                )}
                {answerState === "retry" && coach?.hint && <Hint coach={coach} openSource={openSource} hint={hint} busy={busy} />}
                {(answerState === "attempt" || answerState === "retry") && (
                  <AttemptForm item={item} draft={draft} update={(k, v) => setDraft(d => ({ ...d, [k]: v }))} submit={submitAttempt} busy={busy} retry={answerState === "retry"} />
                )}
                {answerState === "diagnosis" && <Diagnosis coach={coach} openSource={openSource} hint={hint} busy={busy} />}
                {answerState === "safe" && (
                  <Safe
                    title="Chưa đủ căn cứ để kết luận."
                    text="VError không gán lỗi khi bài làm chưa có tín hiệu. Slide phần này đã mở nếu bạn vừa gửi lần thử - hãy đọc rồi quay lại."
                    action={() => safeAction("resume")}
                    busy={busy}
                  />
                )}
                {answerState === "scope" && (
                  <Safe
                    title="Ngoài phạm vi Day 04."
                    text="Thu hẹp vào prompt/tool calling của bài này để VError không dạy sai."
                    action={() => safeAction("resume")}
                    busy={busy}
                  />
                )}
                {answerState === "explain" && (
                  <TextForm title="Giảng lại ý chính bằng lời của bạn" value={explain} set={setExplain} submit={submitExplain} button="Gửi explain-back" busy={busy} />
                )}
                {answerState === "transfer" && (
                  <TransferForm item={item} transfer={transfer} set={setTransfer} submit={submitTransfer} busy={busy} />
                )}
                {answerState === "result" && (
                  <div className="result">
                    <div className="check">✓</div>
                    <h2>Đã chứng minh phần {active?.number}</h2>
                    <p>Slide phần này giữ mở. Phần tiếp theo đã sẵn sàng nếu còn.</p>
                    <div className="result-actions">
                      <button className="primary" onClick={goNextSection}>Sang phần tiếp theo</button>
                      <button className="secondary" onClick={() => setAnswerState("review")}>Xem lại slide</button>
                    </div>
                  </div>
                )}
              </section>

              <aside className="rail">
                <h3>Vòng học</h3>
                {["Thử trước", "Chỉ ra chỗ sai", "Giải thích + PDF", "Retry / chuyển giao"].map((label, index) => (
                  <div className="rail-step" key={label}><span>{index + 1}</span><b>{label}</b></div>
                ))}
                <div className="safety">
                  <b>Vì sao không chán</b>
                  Cược nhỏ trước slide, feedback cụ thể ngay, mở đúng trang PDF, tiến độ 8 phần nhìn thấy được.
                </div>
                <h3>Nguồn phần này</h3>
                {(itemBundle?.sources || []).map(s => (
                  <button className="source" key={s.sourceId} onClick={() => openSource(s.sourceId)}>
                    {s.locator.replace("Day 04 slide deck, ", "")} ↗
                  </button>
                ))}
              </aside>
            </div>
          )}
        </main>
      </div>
      <SourceDrawer source={source} close={() => setSource(null)} />
      {askOpen && (
        <div className="ask-pop">
          <b>Đặt câu hỏi với AI</b>
          <p>Demo Day 04 dùng VError coach có kiểm soát thay cho chat tự do. Hãy thử trước, rồi mở đúng trang PDF.</p>
          <button className="secondary" onClick={() => setAskOpen(false)}>Đóng</button>
        </div>
      )}
    </>
  );
}

function Header({ day, progressPct, askOpen, setAskOpen, onReset }) {
  return (
    <header className="vlearn-header">
      <div className="brand-block">
        <a className="brand" onClick={onReset}>V<span>Learn</span></a>
        <div className="day-chip">
          <strong>{day?.label || "Bài 4 · DAY04"}</strong>
          <small>{day?.title || "Prompt Engineering & Tool Calling"}</small>
        </div>
      </div>
      <div className="header-progress">
        <span>Tiến độ Day</span>
        <div className="header-bar"><div style={{ width: `${progressPct || 0}%` }} /></div>
        <b>{progressPct || 0}%</b>
      </div>
      <div className="header-actions">
        <button className={`ghost ${askOpen ? "on" : ""}`} onClick={() => setAskOpen(v => !v)}>Đặt câu hỏi với AI</button>
        <button className="primary compact" onClick={() => setAskOpen(true)}>Gửi yêu cầu</button>
      </div>
    </header>
  );
}

function LeftNav({ nav, setNav, sections, selected, setSelected }) {
  return (
    <nav className="section-nav" aria-label="Day 04 navigation">
      <div className="nav-title">DAY 04</div>
      <button className={`nav-tab ${nav === "slides" ? "active" : ""}`} onClick={() => setNav("slides")}>▤ <span>Slides</span></button>
      <button className={`nav-tab ${nav === "video" ? "active" : ""}`} onClick={() => setNav("video")}>▶ <span>Video</span><small>timestamp unavailable</small></button>
      <button className={`nav-tab ${nav === "kc" ? "active" : ""}`} onClick={() => setNav("kc")}>✓ <span>KC & Luyện tập</span></button>
      <div className="toc-title">NỘI DUNG BÀI HỌC</div>
      {sections.map(item => {
        const open = !item.attemptLocked;
        return (
          <button
            className={`toc-item ${selected === item.sectionId ? "current" : ""} ${open ? "open" : "locked"} ${item.completed ? "done" : ""}`}
            key={item.sectionId}
            onClick={() => open && setSelected(item.sectionId)}
            disabled={!open}
          >
            <b>{String(item.number).padStart(2, "0")}</b>
            <span>{item.title}</span>
            <i>{item.completed ? "✓" : item.slidesLocked ? (open ? "V" : "🔒") : "▤"}</i>
          </button>
        );
      })}
      <p className="lock-note">Mỗi phần: thử VError → mở slide PDF → sửa đến khi hiểu.</p>
    </nav>
  );
}

function IdleCard({ item, active, attemptOpen, slidesOpen, start, busy, review = false }) {
  return (
    <div className="idle-card">
      <div className="kicker">{review ? "Slide đã mở" : "Checkpoint trước slide"}<span>Phần {active?.number || 1}/8</span></div>
      <h2>{item?.title || "Thử trước"}</h2>
      <p className="stakes">{item?.stakes}</p>
      <div className="statement">
        <b>PHÁT BIỂU CẦN KIỂM TRA</b>
        <p>{item?.statement}</p>
        <small>{item?.taskText}</small>
      </div>
      {!attemptOpen && <p className="muted">Phần này còn khóa. Hoàn thành lần thử phần trước để mở.</p>}
      {attemptOpen && (
        <button className="primary wide" onClick={start} disabled={busy}>
          {busy ? "Đang mở phiên..." : review ? "Làm lại VError phần này" : "Làm bài trước khi mở slide"}
        </button>
      )}
      {slidesOpen && <p className="reassurance">PDF phần này đã mở ở cột trái. Bạn vẫn có thể retry để hiểu sâu hơn.</p>}
    </div>
  );
}

function AttemptForm({ item, draft, update, submit, busy, retry }) {
  return (
    <form onSubmit={submit}>
      <div className="kicker">{retry ? "Retry · sửa giả định" : "Lần thử 1"}<span>Answer key ẩn</span></div>
      <div className="statement">
        <b>PHÁT BIỂU CẦN KIỂM TRA</b>
        <p>{item?.statement}</p>
        <small>{item?.taskText}</small>
      </div>
      <label>Câu trả lời của bạn
        <textarea required value={draft.answer} onChange={e => update("answer", e.target.value)} placeholder="Mình đồng ý/không đồng ý vì..." />
      </label>
      <label>Vì sao bạn nghĩ vậy?
        <textarea required value={draft.explanation} onChange={e => update("explanation", e.target.value)} placeholder="Viết giả định đang dùng..." />
      </label>
      <label>Mức độ chắc chắn
        <div className="choices">
          {["Chắc", "Khá chắc", "Chưa chắc"].map(v => <Choice key={v} label={v} name="confidence" value={v} selected={draft.confidence} set={v => update("confidence", v)} />)}
        </div>
      </label>
      <label>Bạn đang dựa vào đâu?
        <div className="choices">
          {["Đã học trước đó", "Suy luận", "Đoán", "Chưa có căn cứ"].map(v => <Choice key={v} label={v} name="basis" value={v} selected={draft.basis} set={v => update("basis", v)} />)}
        </div>
      </label>
      <button className="primary" disabled={busy}>{busy ? "Đang chẩn đoán..." : "Gửi bài làm"}</button>
    </form>
  );
}

function Diagnosis({ coach, openSource, hint, busy }) {
  return (
    <div>
      <div className="diagnosis">
        <b>CHỖ SAI CẦN KIỂM TRA</b>
        <h2>Giả định lệch</h2>
        <p>{coach?.message}</p>
        {coach?.highlight?.excerpts?.[0] && <blockquote>{coach.highlight.excerpts[0]}</blockquote>}
      </div>
      <div className="citations">
        Nguồn PDF: {coach?.citations?.map(c => (
          <button onClick={() => openSource(c.sourceId)} key={c.sourceId}>{c.label}</button>
        ))}
      </div>
      <p className="muted">Hint chưa đưa đáp án đầy đủ. Đọc trang PDF vừa neo, rồi retry.</p>
      <button className="primary" disabled={busy} onClick={() => hint(1)}>Mở hint 1</button>
    </div>
  );
}

function Hint({ coach, openSource, hint, busy }) {
  const next = (coach?.hint?.level || 0) + 1;
  return (
    <div className="hint">
      <b>HINT {coach.hint.level} / 3</b>
      <p>{coach.hint.text}</p>
      <div className="citations">
        Nguồn: {coach.citations?.map(c => (
          <button onClick={() => openSource(c.sourceId)} key={c.sourceId}>{c.label}</button>
        ))}
      </div>
      {next <= 3 && <button className="secondary" disabled={busy} onClick={() => hint(next)}>Mở hint {next}</button>}
    </div>
  );
}

function Safe({ title, text, action, busy }) {
  return (
    <div className="safe">
      <b>AN TOÀN TRƯỚC</b>
      <h2>{title}</h2>
      <p>{text}</p>
      <button className="secondary" onClick={action} disabled={busy}>Quay lại bài làm</button>
    </div>
  );
}

function TextForm({ title, value, set, submit, button, busy }) {
  return (
    <form onSubmit={submit}>
      <h2>{title}</h2>
      <p className="muted">Không chép nguyên slide. Nói bằng lời của bạn.</p>
      <textarea required value={value} onChange={e => set(e.target.value)} placeholder="Ý chính là..." />
      <button className="primary" disabled={busy}>{button}</button>
    </form>
  );
}

function TransferForm({ item, transfer, set, submit, busy }) {
  return (
    <form onSubmit={submit}>
      <h2>Case chuyển giao</h2>
      <p className="muted">{item?.transfer?.prompt}</p>
      <textarea required value={transfer.answer} onChange={e => set(t => ({ ...t, answer: e.target.value }))} placeholder="Hướng xử lý..." />
      <textarea required value={transfer.reasoning} onChange={e => set(t => ({ ...t, reasoning: e.target.value }))} placeholder="Vì..." />
      <button className="primary" disabled={busy}>Gửi transfer check</button>
    </form>
  );
}

createRoot(document.getElementById("root")).render(<App />);

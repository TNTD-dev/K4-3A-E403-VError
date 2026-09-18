import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { request } from "./api.js";
import { ACTIVE_DAY, lessonByDay } from "./course.js";
import { Icon } from "./icons.jsx";
import { InsightPanel, TeacherNotes } from "./insight.jsx";
import { SlideSurface, useElementWidth, usePdf, useThumbnails } from "./pdf.jsx";
import { PreQuizLayer, QuizToast, pad } from "./prequiz.jsx";

const EMPTY_DRAFT = { answer: "", explanation: "", confidence: "", basis: "" };
const EMPTY_FLOW = {
  phase: "idle", // idle | loading | form | submitted | error  (drives the on-slide overlay)
  answerState: "idle", // backend learning state shown in the key-knowledge panel
  session: null,
  item: null,
  generation: null,
  draft: EMPTY_DRAFT,
  retryDraft: EMPTY_DRAFT,
  coach: null,
  evaluation: null,
  busy: false,
  error: "",
  notice: "",
  toast: false,
  insight: null,
  insightState: "idle",
  insightError: "",
  keyPage: null,
  explain: "",
  transfer: { answer: "", reasoning: "" },
  slideReviewed: false,
};

const STATE_MAP = {
  attempt_1_open: "attempt",
  diagnosis: "diagnosis",
  retry: "retry",
  explain_back: "explain",
  transfer_check: "transfer",
  source_review: "safe",
  clarify: "safe",
  out_of_scope: "scope",
  completed: "result",
};

const TOOLS = [
  ["select", "pointer", "Chọn"],
  ["pen", "pencil", "Bút vẽ"],
  ["highlighter", "highlighter", "Tô sáng"],
  ["circle", "circle", "Khoanh tròn"],
  ["eraser", "eraser", "Tẩy nét vẽ"],
];

const isNarrow = () => window.matchMedia?.("(max-width: 960px)").matches ?? false;

const range = (from, to) => (to < from ? [] : Array.from({ length: to - from + 1 }, (_, index) => from + index));

function readNote(key) {
  try {
    return window.localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}

function writeNote(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage can be unavailable (private mode); notes simply stay in memory.
  }
}

export default function ReaderPage({ day, initialPage, onBack, onOpenDay }) {
  const lesson = lessonByDay(day) || lessonByDay(ACTIVE_DAY);
  const deck = lesson.deck || null;
  const { doc, error: pdfError, ratio } = usePdf(deck?.pdf);
  const thumbs = useThumbnails(doc);

  const [outline, setOutline] = useState(null);
  const [sections, setSections] = useState([]);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(Math.max(1, initialPage || 1));
  const [flows, setFlows] = useState({});
  const flowsRef = useRef(flows);
  flowsRef.current = flows;
  const startedRef = useRef(new Set());

  const [viewMode, setViewMode] = useState("single");
  const [scrollTarget, setScrollTarget] = useState(null);
  const [zoom, setZoom] = useState(100);
  const [tool, setTool] = useState("select");
  const [strokes, setStrokes] = useState({});
  const [showThumbs, setShowThumbs] = useState(true);
  const [notebookOpen, setNotebookOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(() => !isNarrow());
  const [groups, setGroups] = useState({ slides: true, lab: false, videos: false, kc: false });
  const [popover, setPopover] = useState(null);
  const [pageInput, setPageInput] = useState(String(page));

  const stageRef = useRef(null);
  const viewerRef = useRef(null);
  const notesRef = useRef(null);
  const thumbsRef = useRef(null);
  const [sizerRef, stageWidth] = useElementWidth();
  const totalPages = doc?.numPages || outline?.totalPages || 0;

  // ------------------------------------------------------------------ data
  useEffect(() => {
    if (!deck) return undefined;
    let live = true;
    Promise.all([request("/api/v1/deck/outline"), request("/api/v1/sections")])
      .then(([deckOutline, toc]) => {
        if (!live) return;
        setOutline(deckOutline);
        setSections(toc.sections);
      })
      .catch(error => live && setLoadError(error.message));
    return () => {
      live = false;
    };
  }, [deck]);

  useEffect(() => {
    if (totalPages && page > totalPages) setPage(totalPages);
  }, [totalPages, page]);

  useEffect(() => {
    setPageInput(String(page));
    window.history.replaceState(null, "", `?day=${day}&page=${page}`);
  }, [day, page]);

  const statusById = useMemo(() => Object.fromEntries(sections.map(item => [item.sectionId, item])), [sections]);
  const ready = Boolean(outline && sections.length);

  const sectionAt = useCallback(
    number => outline?.sections.find(item => number >= item.startPage && number <= item.endPage) || null,
    [outline],
  );

  const gateFor = useCallback(
    number => {
      if (!deck) return null;
      if (loadError) return number > 1 ? "offline" : null;
      if (!ready) return number > 1 ? "loading" : null;
      const owner = sectionAt(number);
      const status = owner && statusById[owner.sectionId];
      // The title slide stays readable; the slide right after it opens the pre-quiz.
      if (!owner || !status || !status.slidesLocked || number <= owner.titlePage) return null;
      return status.attemptLocked ? "locked" : "quiz";
    },
    [deck, loadError, ready, sectionAt, statusById],
  );

  const current = sectionAt(page);
  const currentStatus = current ? statusById[current.sectionId] : null;
  const flow = (current && flows[current.sectionId]) || EMPTY_FLOW;
  const gate = gateFor(page);
  const pending = outline?.sections.find(item => statusById[item.sectionId]?.slidesLocked && !statusById[item.sectionId]?.attemptLocked) || null;
  const completedCount = sections.filter(item => item.completed).length;
  const totalSections = sections.length || outline?.sections.length || 8;

  const patchFlow = useCallback((id, patch) => {
    setFlows(all => {
      const previous = all[id] || EMPTY_FLOW;
      const next = typeof patch === "function" ? patch(previous) : patch;
      return { ...all, [id]: { ...previous, ...next } };
    });
  }, []);

  function applyProgress(progress) {
    if (!progress) return;
    setSections(items =>
      items.map(item => ({
        ...item,
        attemptLocked: !progress.unlockedAttempts.includes(item.sectionId),
        slidesLocked: !progress.unlockedSlides.includes(item.sectionId),
        locked: !progress.unlockedAttempts.includes(item.sectionId),
        completed: progress.completedSections.includes(item.sectionId),
      })),
    );
  }

  // ------------------------------------------------------------------ learning flow
  const startAttempt = useCallback(
    async id => {
      startedRef.current.add(id);
      patchFlow(id, { phase: "loading", error: "", generation: { state: "loading" } });
      let bundle = null;
      let generation;
      try {
        bundle = await request(`/api/v1/sections/${id}/item/generate`, { method: "POST" });
        const meta = bundle.generation || {};
        generation = { state: meta.generated ? "live" : "reviewed", model: meta.model, fallbackReason: meta.fallbackReason };
      } catch {
        generation = { state: "reviewed", model: null, fallbackReason: "generator_unavailable" };
      }
      try {
        const session = await request("/api/v1/sessions", {
          method: "POST",
          body: JSON.stringify({ sectionId: id, mode: "demo" }),
        });
        patchFlow(id, {
          phase: "form",
          answerState: "attempt",
          session,
          item: bundle?.item || session.item,
          generation,
          coach: null,
          evaluation: null,
          draft: EMPTY_DRAFT,
          retryDraft: EMPTY_DRAFT,
          error: "",
          notice: "",
          explain: "",
          transfer: { answer: "", reasoning: "" },
          slideReviewed: false,
        });
      } catch (error) {
        patchFlow(id, { phase: "error", error: error.message, generation });
      }
    },
    [patchFlow],
  );

  // Landing on the slide after a title slide pops the pre-quiz automatically.
  const quizSectionId =
    viewMode === "scroll"
      ? current && currentStatus?.slidesLocked && !currentStatus.attemptLocked
        ? current.sectionId
        : null
      : gate === "quiz"
        ? current?.sectionId
        : null;

  useEffect(() => {
    if (quizSectionId && !startedRef.current.has(quizSectionId)) startAttempt(quizSectionId);
  }, [quizSectionId, startAttempt]);

  const loadInsight = useCallback(
    async (id, sessionId) => {
      patchFlow(id, { insightState: "loading", insightError: "" });
      try {
        const result = await request(`/api/v1/sections/${id}/key-insight`, {
          method: "POST",
          body: JSON.stringify(sessionId ? { sessionId } : {}),
        });
        patchFlow(id, { insight: result, insightState: "ready", keyPage: result.insight?.focusPage || null });
      } catch (error) {
        patchFlow(id, { insightState: "error", insightError: error.message });
      }
    },
    [patchFlow],
  );

  async function submitAttempt(id, kind, fromPanel) {
    const state = flowsRef.current[id];
    if (!state?.session) return;
    const draft = fromPanel ? state.retryDraft : state.draft;
    patchFlow(id, { busy: true, error: "" });
    try {
      const result = await request(`/api/v1/sessions/${state.session.sessionId}/attempts`, {
        method: "POST",
        headers: { "Idempotency-Key": `${kind}-${id}-${Date.now()}` },
        body: JSON.stringify({
          stateVersion: state.session.stateVersion,
          kind,
          answer: { text: draft.answer.trim(), explanation: draft.explanation.trim() },
          confidence: draft.confidence || undefined,
          basis: draft.basis || undefined,
        }),
      });
      applyProgress(result.progress);
      patchFlow(id, previous => ({
        busy: false,
        phase: "submitted",
        session: { ...previous.session, stateVersion: result.stateVersion },
        coach: result.coach,
        evaluation: result.evaluation,
        answerState: STATE_MAP[result.next.state] || "safe",
        toast: fromPanel ? previous.toast : true,
        retryDraft: EMPTY_DRAFT,
      }));
      if (!state.insight && state.insightState !== "loading") loadInsight(id, state.session.sessionId);
    } catch (error) {
      patchFlow(id, { busy: false, error: error.message });
    }
  }

  async function sessionCall(id, path, body, onResult) {
    const state = flowsRef.current[id];
    if (!state?.session) return;
    patchFlow(id, { busy: true, error: "", notice: "" });
    try {
      const result = await request(`/api/v1/sessions/${state.session.sessionId}/${path}`, {
        method: "POST",
        body: JSON.stringify({ stateVersion: state.session.stateVersion, ...body }),
      });
      if (result.progress) applyProgress(result.progress);
      patchFlow(id, previous => ({
        busy: false,
        session: { ...previous.session, stateVersion: result.stateVersion },
        ...onResult(result, previous),
      }));
    } catch (error) {
      patchFlow(id, { busy: false, error: error.message });
    }
  }

  const requestHint = (id, level) => sessionCall(id, "hints", { level }, result => ({ coach: result.coach, answerState: "retry" }));

  const submitExplain = id =>
    sessionCall(id, "explain-back", { text: flowsRef.current[id].explain.trim() }, result => {
      const passed = result.next.state === "transfer_check";
      return {
        answerState: passed ? "transfer" : "explain",
        coach: result.coach,
        evaluation: passed ? { status: "pass", claims: null } : result.evaluation,
        notice: "",
      };
    });

  const submitTransfer = id =>
    sessionCall(id, "transfer", flowsRef.current[id].transfer, result =>
      result.evaluation.status === "pass"
        ? { answerState: "result", coach: result.coach, evaluation: result.evaluation, notice: "" }
        : { answerState: "transfer", coach: result.coach, evaluation: result.evaluation, notice: "" },
    );

  const resumeSession = id =>
    sessionCall(id, "resume", {}, result => ({ answerState: result.next.state === "attempt_1_open" ? "attempt" : "retry" }));

  // ------------------------------------------------------------------ navigation
  const goTo = useCallback(
    number => {
      if (!totalPages) return;
      const next = Math.min(Math.max(1, number), totalPages);
      setPage(next);
      if (viewMode === "scroll") setScrollTarget({ page: next, at: Date.now() });
    },
    [totalPages, viewMode],
  );

  function showViewer(number) {
    goTo(number);
    window.requestAnimationFrame(() => viewerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  function goToInsight(id) {
    const state = flowsRef.current[id];
    patchFlow(id, { toast: false });
    if (!state?.insight && state?.insightState !== "loading") loadInsight(id, state?.session?.sessionId);
    window.requestAnimationFrame(() => notesRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  function goNextSection(id) {
    const index = outline.sections.findIndex(item => item.sectionId === id);
    const next = outline.sections[index + 1];
    if (next) showViewer(next.titlePage);
  }

  async function resetDemo() {
    try {
      await request("/api/v1/progress/reset", { method: "POST" });
      window.location.replace(`?day=${day}&page=1`);
    } catch (error) {
      setNotice(error.message);
    }
  }

  useEffect(() => {
    if (viewMode !== "single") return undefined;
    const onKey = event => {
      const target = event.target;
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      if (target?.closest?.("input, textarea, select, [contenteditable='true']")) return;
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        event.preventDefault();
        goTo(page + 1);
      } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
        event.preventDefault();
        goTo(page - 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [viewMode, goTo, page]);

  useEffect(() => {
    const strip = thumbsRef.current;
    const thumb = strip?.querySelector(`[data-page="${page}"]`);
    if (!strip || !thumb) return;
    strip.scrollTo({ left: thumb.offsetLeft - strip.clientWidth / 2 + thumb.clientWidth / 2, behavior: "smooth" });
  }, [page, showThumbs, totalPages]);

  useEffect(() => {
    if (!popover) return undefined;
    const onDown = event => {
      if (!event.target.closest?.(".popover, [data-popover-trigger]")) setPopover(null);
    };
    const onKey = event => event.key === "Escape" && setPopover(null);
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [popover]);

  // ------------------------------------------------------------------ annotations
  const pageStrokes = strokes[page] || [];
  const addStroke = stroke => setStrokes(all => ({ ...all, [page]: [...(all[page] || []), stroke] }));
  const eraseStroke = id => setStrokes(all => ({ ...all, [page]: (all[page] || []).filter(item => item.id !== id) }));
  const undoStroke = () => setStrokes(all => ({ ...all, [page]: (all[page] || []).slice(0, -1) }));
  const clearStrokes = () => setStrokes(all => ({ ...all, [page]: [] }));

  function toggleFullscreen() {
    if (document.fullscreenElement) document.exitFullscreen?.();
    else stageRef.current?.requestFullscreen?.().catch(() => {});
  }

  // ------------------------------------------------------------------ render helpers
  const flowActions = id => ({
    onStart: () => startAttempt(id),
    onDraft: draft => patchFlow(id, { draft }),
    onSubmit: () => submitAttempt(id, "attempt_1", false),
  });

  function stageLayers(number, isPrimary) {
    const owner = sectionAt(number);
    const pageGate = gateFor(number);
    const ownerFlow = (owner && flows[owner.sectionId]) || EMPTY_FLOW;
    // In scroll mode only the first gated slide carries the form; the rest just stay blurred.
    const carriesQuiz = isPrimary || !owner || number === owner.quizPage;
    return (
      <>
        {pageGate && carriesQuiz && (
          <PreQuizLayer
            gate={pageGate}
            section={owner}
            flow={ownerFlow}
            pending={pending}
            onGoPending={target => showViewer(target.quizPage)}
            {...(owner ? flowActions(owner.sectionId) : {})}
          />
        )}
        {pageGate && !carriesQuiz && (
          <span className="stage-lock-chip"><Icon name="lock" size={14} /> Trả lời pre-quiz ở trang {owner.quizPage} để mở</span>
        )}
        {!pageGate && owner && ownerFlow.toast && number === page && (
          <QuizToast
            flow={ownerFlow}
            keyCount={owner.keySlides.length}
            onGo={() => goToInsight(owner.sectionId)}
            onClose={() => patchFlow(owner.sectionId, { toast: false })}
          />
        )}
      </>
    );
  }

  const showInsight = Boolean(current && currentStatus && !currentStatus.slidesLocked && flow.insightState !== "idle");
  const progressPct = Math.round((completedCount / Math.max(totalSections, 1)) * 100);
  const scrollPages = current
    ? range(current.startPage, current.endPage)
    : range(1, (outline?.sections[0]?.startPage || totalPages + 1) - 1);
  const nextSection = current ? outline?.sections.find(item => item.number === current.number + 1) : outline?.sections[0];

  return (
    <div className="reader-shell">
      <header className="reader-header">
        <div className="rh-left">
          <button type="button" className="icon-btn" onClick={onBack} aria-label="Về trang chủ"><Icon name="arrowLeft" size={24} /></button>
          <h1>Bài {lesson.lesson} · {lesson.short}</h1>
        </div>
        <div className="rh-right">
          <div className="rh-progress" title="Số phần đã chứng minh qua pre-quiz, giảng lại và case chuyển giao">
            <span>{deck ? `${completedCount}/${totalSections} phần` : "0/0 phần"}</span>
            <div className="rh-bar"><i style={{ width: `${progressPct}%` }} /></div>
          </div>
          <button type="button" className="rh-action" onClick={resetDemo} title="Xóa tiến độ, phiên học và cache phân tích slide">
            <Icon name="rotate" size={20} /> <span>Làm lại</span>
          </button>
          <span className="rh-divider" aria-hidden="true" />
          <div className="pop-anchor">
            <button type="button" className="rh-action" data-popover-trigger onClick={() => setPopover(open => (open === "ask" ? null : "ask"))} aria-expanded={popover === "ask"}>
              <Icon name="sparkles" size={22} className="ai-spark" /> <span>Đặt câu hỏi với AI</span>
            </button>
            {popover === "ask" && (
              <div className="popover" role="dialog" aria-label="Đặt câu hỏi với AI">
                <b>Hỏi theo đúng slide đang học</b>
                <p>Pre-quiz hiện ngay sau mỗi slide tiêu đề, rồi phần kiến thức trọng tâm giải thích đúng trang đó. Chat tự do chưa mở để không dạy ngoài nguồn đã duyệt.</p>
                {current && !currentStatus?.slidesLocked && (
                  <button type="button" className="btn-soft" onClick={() => { setPopover(null); goToInsight(current.sectionId); }}>
                    <Icon name="sparkles" size={16} /> Xem kiến thức trọng tâm Phần {pad(current.number)}
                  </button>
                )}
              </div>
            )}
          </div>
          <div className="pop-anchor">
            <button type="button" className="rh-action" data-popover-trigger onClick={() => setPopover(open => (open === "request" ? null : "request"))} aria-expanded={popover === "request"}>
              <Icon name="hand" size={22} /> <span>Gửi yêu cầu</span>
            </button>
            {popover === "request" && (
              <div className="popover" role="dialog" aria-label="Gửi yêu cầu">
                <b>Gửi yêu cầu cho giảng viên</b>
                <p>Kênh gửi yêu cầu chưa được kết nối trong prototype này, nên chưa có tin nhắn nào được gửi đi.</p>
              </div>
            )}
          </div>
          <span className="avatar soft">L</span>
        </div>
      </header>

      <div className={`reader-body ${sidebarOpen ? "" : "collapsed"}`}>
        {sidebarOpen && (
          <Sidebar
            lesson={lesson}
            deck={deck}
            outline={outline}
            statusById={statusById}
            current={current}
            groups={groups}
            toggle={key => setGroups(all => ({ ...all, [key]: !all[key] }))}
            onClose={() => setSidebarOpen(false)}
            goTo={number => {
              if (isNarrow()) setSidebarOpen(false);
              showViewer(number);
            }}
            onReset={resetDemo}
          />
        )}

        <main className="reader-main">
          {!sidebarOpen && (
            <button type="button" className="sidebar-open" onClick={() => setSidebarOpen(true)}>
              <Icon name="menu" size={18} /> Nội dung bài học
            </button>
          )}
          {notice && (
            <div className="reader-notice" role="alert">
              <span>{notice}</span>
              <button type="button" className="icon-btn" onClick={() => setNotice("")} aria-label="Đóng"><Icon name="x" size={16} /></button>
            </div>
          )}

          {!deck ? (
            <EmptyDay lesson={lesson} onOpenDay={onOpenDay} />
          ) : (
            <>
              <div className="viewer" ref={viewerRef}>
                {viewMode === "single" ? (
                  <div className="stage-scroller">
                    <div className="stage-sizer" ref={sizerRef} style={{ width: `${zoom}%` }}>
                      <div className={`slide-stage ${gate ? "gated" : ""}`} ref={stageRef} style={{ aspectRatio: ratio }}>
                        {doc ? (
                          <SlideSurface doc={doc} page={page} width={stageWidth} gated={Boolean(gate)} preview={thumbs[page]} />
                        ) : (
                          <div className="stage-placeholder">{pdfError || "Đang tải slide…"}</div>
                        )}
                        <AnnotationLayer tool={tool} strokes={pageStrokes} onAdd={addStroke} onErase={eraseStroke} disabled={Boolean(gate)} />
                        {!gate && ready && (
                          <StageAgent
                            open={popover === "agent"}
                            toggle={() => setPopover(open => (open === "agent" ? null : "agent"))}
                            page={page}
                            outline={outline}
                            section={current}
                            status={currentStatus}
                            onInsight={() => { setPopover(null); goToInsight(current.sectionId); }}
                          />
                        )}
                        {stageLayers(page, true)}
                      </div>
                    </div>
                  </div>
                ) : (
                  <ScrollView
                    doc={doc}
                    ratio={ratio}
                    zoom={zoom}
                    pages={scrollPages}
                    thumbs={thumbs}
                    gateFor={gateFor}
                    target={scrollTarget}
                    onVisible={setPage}
                    renderLayers={number => stageLayers(number, false)}
                    footer={
                      nextSection && (
                        <button type="button" className="btn-soft scroll-next" onClick={() => goTo(nextSection.titlePage)}>
                          Tiếp: Phần {pad(nextSection.number)} · {nextSection.title} <Icon name="chevronRight" size={16} />
                        </button>
                      )
                    }
                  />
                )}

                <div className="viewer-toolbar" role="toolbar" aria-label="Công cụ slide">
                  <div className="tool-group">
                    {TOOLS.map(([id, icon, label]) => (
                      <button
                        type="button"
                        key={id}
                        className={`tool-btn ${tool === id ? "on" : ""}`}
                        onClick={() => setTool(id)}
                        disabled={viewMode !== "single"}
                        title={label}
                        aria-label={label}
                        aria-pressed={tool === id}
                      >
                        <Icon name={icon} size={21} />
                      </button>
                    ))}
                  </div>
                  <span className="tool-divider" aria-hidden="true" />
                  <div className="tool-group">
                    <button
                      type="button"
                      className="tool-btn"
                      title="Kiến thức trọng tâm của phần này"
                      aria-label="Kiến thức trọng tâm"
                      disabled={!current || currentStatus?.slidesLocked !== false}
                      onClick={() => goToInsight(current.sectionId)}
                    >
                      <Icon name="lightbulb" size={21} />
                    </button>
                    <button type="button" className="tool-btn" title="Chú thích chữ · sắp ra mắt" aria-label="Chú thích chữ" disabled>
                      <Icon name="type" size={21} />
                    </button>
                  </div>
                  <div className="segmented" role="group" aria-label="Chế độ xem">
                    <button type="button" className={viewMode === "single" ? "on" : ""} onClick={() => setViewMode("single")} aria-pressed={viewMode === "single"}>
                      <Icon name="bookOpen" size={18} /> Từng trang
                    </button>
                    <button
                      type="button"
                      className={viewMode === "scroll" ? "on" : ""}
                      onClick={() => {
                        setViewMode("scroll");
                        setScrollTarget({ page, at: Date.now() });
                      }}
                      aria-pressed={viewMode === "scroll"}
                    >
                      <Icon name="copy" size={18} /> Cuộn dọc
                    </button>
                  </div>
                  <div className="segmented zoom" role="group" aria-label="Thu phóng">
                    <button type="button" onClick={() => setZoom(value => Math.max(50, value - 10))} aria-label="Thu nhỏ" disabled={zoom <= 50}><Icon name="zoomOut" size={18} /></button>
                    <span>{zoom}%</span>
                    <button type="button" onClick={() => setZoom(value => Math.min(200, value + 10))} aria-label="Phóng to" disabled={zoom >= 200}><Icon name="zoomIn" size={18} /></button>
                  </div>
                  <span className="tool-divider" aria-hidden="true" />
                  <div className="tool-group">
                    <button type="button" className="tool-btn" title="Hoàn tác nét vẽ" aria-label="Hoàn tác" onClick={undoStroke} disabled={!pageStrokes.length}><Icon name="undo" size={21} /></button>
                    <button type="button" className="tool-btn danger" title="Xóa nét vẽ trên trang" aria-label="Xóa nét vẽ" onClick={clearStrokes} disabled={!pageStrokes.length}><Icon name="trash" size={21} /></button>
                    <button type="button" className="tool-btn" title="Toàn màn hình" aria-label="Toàn màn hình" onClick={toggleFullscreen} disabled={viewMode !== "single"}><Icon name="maximize" size={21} /></button>
                  </div>
                </div>

                <div className="viewer-pager">
                  <button type="button" className="icon-btn" onClick={() => goTo(page - 1)} disabled={page <= 1} aria-label="Trang trước"><Icon name="chevronLeft" size={22} /></button>
                  <input
                    className="page-input"
                    inputMode="numeric"
                    aria-label="Số trang"
                    value={pageInput}
                    onChange={event => setPageInput(event.target.value.replace(/\D/g, ""))}
                    onBlur={() => goTo(Number(pageInput) || page)}
                    onKeyDown={event => event.key === "Enter" && event.currentTarget.blur()}
                  />
                  <span className="page-total">/ {totalPages || "…"}</span>
                  <button type="button" className="icon-btn" onClick={() => goTo(page + 1)} disabled={!totalPages || page >= totalPages} aria-label="Trang sau"><Icon name="chevronRight" size={22} /></button>
                  <button type="button" className={`tool-btn outline ${showThumbs ? "on" : ""}`} onClick={() => setShowThumbs(value => !value)} aria-pressed={showThumbs} aria-label="Dải trang" title="Dải trang">
                    <Icon name="grid" size={20} />
                  </button>
                  <button type="button" className={`text-btn ${notebookOpen ? "on" : ""}`} onClick={() => setNotebookOpen(value => !value)} aria-pressed={notebookOpen}>
                    <Icon name="fileText" size={20} /> Sổ ghi chú
                  </button>
                </div>

                {notebookOpen && <Notebook storageKey={`vlearn-note-${day}-${page}`} page={page} />}

                {showThumbs && totalPages > 0 && (
                  <div className="thumbs">
                    <button type="button" className="thumb-arrow" onClick={() => thumbsRef.current?.scrollBy({ left: -520, behavior: "smooth" })} aria-label="Cuộn trái"><Icon name="chevronLeft" size={22} /></button>
                    <div className="thumb-track" ref={thumbsRef}>
                      {range(1, totalPages).map(number => {
                        const owner = sectionAt(number);
                        const pageGate = gateFor(number);
                        const unlocked = owner && statusById[owner.sectionId] && !statusById[owner.sectionId].slidesLocked;
                        const isKey = unlocked && owner.keySlides.some(slide => slide.page === number);
                        return (
                          <button
                            type="button"
                            key={number}
                            data-page={number}
                            className={`thumb ${number === page ? "on" : ""} ${pageGate ? "gated" : ""}`}
                            style={{ aspectRatio: ratio }}
                            onClick={() => goTo(number)}
                            aria-label={`Trang ${number}${pageGate ? " — cần làm pre-quiz" : ""}`}
                            aria-current={number === page ? "page" : undefined}
                          >
                            {thumbs[number] ? <img src={thumbs[number]} alt="" /> : <span className="thumb-skeleton" />}
                            {pageGate && <span className="thumb-lock"><Icon name="lock" size={14} /></span>}
                            {owner?.titlePage === number && <span className="thumb-tag">Phần {pad(owner.number)}</span>}
                            {isKey && <span className="thumb-tag key"><Icon name="target" size={11} /> Trọng tâm</span>}
                            <span className="thumb-no">{number}</span>
                          </button>
                        );
                      })}
                    </div>
                    <button type="button" className="thumb-arrow" onClick={() => thumbsRef.current?.scrollBy({ left: 520, behavior: "smooth" })} aria-label="Cuộn phải"><Icon name="chevronRight" size={22} /></button>
                  </div>
                )}
              </div>

              <section className={`notes-card ${showInsight ? "insight" : ""}`} ref={notesRef} aria-live="polite">
                {showInsight ? (
                  <InsightPanel
                    doc={doc}
                    section={current}
                    flow={flow}
                    onKeyPage={number => patchFlow(current.sectionId, { keyPage: number })}
                    onJump={showViewer}
                    onReload={() => loadInsight(current.sectionId, flow.session?.sessionId)}
                    actions={{
                      hint: level => requestHint(current.sectionId, level),
                      submit: kind => submitAttempt(current.sectionId, kind, true),
                      retryDraft: draft => patchFlow(current.sectionId, { retryDraft: draft }),
                      explain: () => submitExplain(current.sectionId),
                      setExplain: text => patchFlow(current.sectionId, { explain: text }),
                      transfer: () => submitTransfer(current.sectionId),
                      setTransfer: value => patchFlow(current.sectionId, { transfer: value }),
                      resume: () => resumeSession(current.sectionId),
                      restart: () => startAttempt(current.sectionId),
                      next: () => goNextSection(current.sectionId),
                      markReviewed: () => patchFlow(current.sectionId, { slideReviewed: true }),
                    }}
                  />
                ) : (
                  <TeacherNotes
                    section={current}
                    unlocked={Boolean(currentStatus && !currentStatus.slidesLocked)}
                    onLoadInsight={() => loadInsight(current.sectionId, flow.session?.sessionId)}
                  />
                )}
              </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function SidebarGroup({ title, icon, open, onToggle, variant = "", children }) {
  return (
    <div className={`sb-group ${variant} ${open ? "open" : ""}`}>
      <button type="button" className="sb-group-head" aria-expanded={open} onClick={onToggle}>
        {icon && <Icon name={icon} size={20} />}
        <span>{title}</span>
        <Icon name={open ? "chevronDown" : "chevronRight"} size={20} />
      </button>
      {open && <div className="sb-group-body">{children}</div>}
    </div>
  );
}

function sectionState(status) {
  if (!status) return { key: "", label: "" };
  if (status.completed) return { key: "done", label: "Đã chứng minh" };
  if (!status.slidesLocked) return { key: "open", label: "Đã thử" };
  if (!status.attemptLocked) return { key: "next", label: "Sẵn sàng" };
  return { key: "locked", label: "Chưa mở" };
}

function Sidebar({ lesson, deck, outline, statusById, current, groups, toggle, onClose, goTo, onReset }) {
  return (
    <aside className="reader-sidebar" aria-label="Nội dung bài học">
      <div className="sb-head">
        <h2>Nội dung bài học</h2>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Đóng nội dung bài học"><Icon name="x" size={22} /></button>
      </div>

      <SidebarGroup title="Slides" open={groups.slides} onToggle={() => toggle("slides")}>
        {deck ? (
          <>
            <button type="button" className="sb-file on" onClick={() => goTo(1)}>
              <span className="file-icon"><Icon name="presentation" size={16} /></span>
              <span className="sb-file-name">{deck.file}</span>
              <b>Đang học</b>
            </button>
            {outline ? (
              <div className="sb-outline">
                <p className="sb-agent">
                  {outline.sections.length} phần · pre-quiz gắn sau mỗi slide tiêu đề
                </p>
                {outline.sections.map(item => {
                  const state = sectionState(statusById[item.sectionId]);
                  return (
                    <button
                      type="button"
                      key={item.sectionId}
                      className={`sb-part ${current?.sectionId === item.sectionId ? "on" : ""} ${state.key}`}
                      onClick={() => goTo(item.titlePage)}
                      title={`${item.title} · slide tiêu đề trang ${item.titlePage}`}
                    >
                      <span className="part-no">{pad(item.number)}</span>
                      <span className="part-title">{item.title}</span>
                      <span className="part-state">
                        {state.key === "done" ? <Icon name="check" size={15} strokeWidth={2.4} /> : state.key === "locked" ? <Icon name="lock" size={14} /> : `tr.${item.titlePage}`}
                      </span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="sb-agent loading"><span className="mini-spinner" /> Đang đọc mục lục slide…</p>
            )}
          </>
        ) : (
          <p className="sb-empty">Chưa có slide cho buổi này.</p>
        )}
      </SidebarGroup>

      <SidebarGroup title={deck ? deck.lab.title : `Lab ${pad(lesson.lesson)}`} icon="flask" variant="lab" open={groups.lab} onToggle={() => toggle("lab")}>
        {deck ? (
          deck.lab.steps.map(step => (
            <button type="button" key={step.page} className="sb-link" onClick={() => goTo(step.page)}>
              <span>{step.label}</span><small>tr.{step.page}</small>
            </button>
          ))
        ) : (
          <p className="sb-empty">Chưa có lab cho buổi này.</p>
        )}
      </SidebarGroup>

      <SidebarGroup title="Videos" open={groups.videos} onToggle={() => toggle("videos")}>
        <p className="sb-empty">Video bài giảng chưa có timestamp khớp với slide, nên VError neo kiến thức vào trang PDF.</p>
      </SidebarGroup>

      <SidebarGroup title="KC & Luyện tập" open={groups.kc} onToggle={() => toggle("kc")}>
        {deck && outline ? (
          <>
            {outline.sections.map(item => {
              const state = sectionState(statusById[item.sectionId]);
              return (
                <button type="button" key={item.sectionId} className={`sb-link kc ${state.key}`} onClick={() => goTo(item.quizPage)} disabled={state.key === "locked"}>
                  <span>Pre-quiz {pad(item.number)} · {item.title}</span>
                  <small>{state.label}</small>
                </button>
              );
            })}
          </>
        ) : (
          <p className="sb-empty">Chưa có bài luyện tập.</p>
        )}
      </SidebarGroup>

      {deck && (
        <div className="sb-foot">
          <button type="button" className="sb-reset" onClick={onReset}>
            <Icon name="rotate" size={15} /> Làm lại từ đầu
          </button>
        </div>
      )}
    </aside>
  );
}

function StageAgent({ open, toggle, page, outline, section, status, onInsight }) {
  let title = "Trang giới thiệu";
  let body = `${outline.sections.length} phần trong bài. Pre-quiz hiện ở slide ngay sau mỗi tiêu đề.`;
  let action = null;
  if (section) {
    const keySlide = section.keySlides.find(slide => slide.page === page);
    if (page === section.titlePage) {
      title = `Slide tiêu đề · Phần ${pad(section.number)}`;
      body = status?.slidesLocked
        ? `“${section.title}”. Slide tiếp theo (trang ${section.quizPage}) sẽ mở pre-quiz trước khi bạn đọc nội dung.`
        : `“${section.title}”. Bạn đã thử pre-quiz của phần này.`;
    } else if (keySlide) {
      title = `Slide trọng tâm · Phần ${pad(section.number)}`;
      body = `Slide này chứa nguồn đã duyệt ${keySlide.sourceIds.join(", ")} mà pre-quiz dựa vào.`;
      action = "insight";
    } else {
      title = `Phần ${pad(section.number)} · ${section.title}`;
      body = `Trang ${page - section.startPage + 1}/${section.endPage - section.startPage + 1} của phần này.`;
      if (!status?.slidesLocked) action = "insight";
    }
  }
  return (
    <>
      <button type="button" className="stage-ai" data-popover-trigger onClick={toggle} aria-label="Thông tin slide này" aria-expanded={open}>
        <Icon name="sparkles" size={22} />
      </button>
      {open && (
        <div className="popover stage-pop" role="dialog" aria-label="Thông tin slide">
          <b>{title}</b>
          <p>{body}</p>
          {action === "insight" && (
            <button type="button" className="btn-soft" onClick={onInsight}>
              <Icon name="sparkles" size={16} /> Xem kiến thức trọng tâm
            </button>
          )}
        </div>
      )}
    </>
  );
}

function AnnotationLayer({ tool, strokes, onAdd, onErase, disabled }) {
  const [draft, setDraft] = useState(null);
  const drawing = !disabled && ["pen", "highlighter", "circle"].includes(tool);
  const erasing = !disabled && tool === "eraser";

  const point = event => {
    const box = event.currentTarget.getBoundingClientRect();
    return [(event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height];
  };

  return (
    <svg
      className={`annotation-layer ${drawing ? "drawing" : ""} ${erasing ? "erasing" : ""}`}
      viewBox="0 0 1000 1000"
      preserveAspectRatio="none"
      onPointerDown={event => {
        if (!drawing) return;
        event.currentTarget.setPointerCapture(event.pointerId);
        setDraft({ id: `${Date.now()}-${Math.random()}`, tool, points: [point(event)] });
      }}
      onPointerMove={event => {
        if (!draft) return;
        const next = point(event);
        setDraft(current => ({ ...current, points: current.tool === "circle" ? [current.points[0], next] : [...current.points, next] }));
      }}
      onPointerUp={() => {
        if (draft?.points.length > 1) onAdd(draft);
        setDraft(null);
      }}
      onPointerCancel={() => setDraft(null)}
    >
      {[...strokes, draft].filter(Boolean).map(stroke => (
        <Stroke key={stroke.id} stroke={stroke} onErase={erasing ? () => onErase(stroke.id) : undefined} />
      ))}
    </svg>
  );
}

function Stroke({ stroke, onErase }) {
  if (stroke.tool === "circle") {
    const [[x1, y1], [x2, y2]] = stroke.points.length > 1 ? stroke.points : [stroke.points[0], stroke.points[0]];
    return (
      <ellipse
        className="ann circle"
        cx={(x1 + x2) * 500}
        cy={(y1 + y2) * 500}
        rx={Math.abs(x2 - x1) * 500}
        ry={Math.abs(y2 - y1) * 500}
        vectorEffect="non-scaling-stroke"
        onClick={onErase}
      />
    );
  }
  const d = stroke.points.map(([x, y], index) => `${index ? "L" : "M"}${(x * 1000).toFixed(1)} ${(y * 1000).toFixed(1)}`).join(" ");
  return <path className={`ann ${stroke.tool}`} d={d} vectorEffect="non-scaling-stroke" onClick={onErase} />;
}

function ScrollStage({ doc, page, ratio, gate, preview, children }) {
  const [stageRef, width] = useElementWidth();
  return (
    <div className={`slide-stage ${gate ? "gated" : ""}`} ref={stageRef} style={{ aspectRatio: ratio }}>
      {doc && <SlideSurface doc={doc} page={page} width={width} gated={Boolean(gate)} preview={preview} lazy />}
      {children}
    </div>
  );
}

function ScrollView({ doc, ratio, zoom, pages, thumbs, gateFor, target, onVisible, renderLayers, footer }) {
  const nodes = useRef({});
  const key = pages.join(",");

  useEffect(() => {
    const elements = pages.map(number => nodes.current[number]).filter(Boolean);
    if (!elements.length) return undefined;
    const observer = new IntersectionObserver(
      entries => {
        const best = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (best) onVisible(Number(best.target.dataset.page));
      },
      { threshold: [0.55, 0.8] },
    );
    elements.forEach(element => observer.observe(element));
    return () => observer.disconnect();
  }, [key, onVisible]);

  useEffect(() => {
    if (target) nodes.current[target.page]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [target, key]);

  return (
    <div className="scroll-view">
      {pages.map(number => (
        <div className="scroll-item" key={number} data-page={number} ref={element => { nodes.current[number] = element; }} style={{ width: `${zoom}%` }}>
          <ScrollStage doc={doc} page={number} ratio={ratio} gate={gateFor(number)} preview={thumbs[number]}>
            {renderLayers(number)}
          </ScrollStage>
          <span className="scroll-no">Trang {number}</span>
        </div>
      ))}
      {footer}
    </div>
  );
}

function Notebook({ storageKey, page }) {
  const [text, setText] = useState(() => readNote(storageKey));
  useEffect(() => setText(readNote(storageKey)), [storageKey]);
  return (
    <div className="notebook">
      <label className="field">
        <span><Icon name="fileText" size={16} /> Sổ ghi chú · trang {page}</span>
        <textarea
          rows={3}
          value={text}
          onChange={event => {
            setText(event.target.value);
            writeNote(storageKey, event.target.value);
          }}
          placeholder="Ghi lại điều bạn muốn nhớ ở slide này…"
        />
      </label>
      <small>Lưu trên trình duyệt này.</small>
    </div>
  );
}

function EmptyDay({ lesson, onOpenDay }) {
  return (
    <>
      <div className="empty-day">
        <Icon name="presentation" size={40} />
        <h2>Slide {lesson.short} chưa có trong prototype</h2>
        <p>Bản demo VError hiện có bộ slide và pre-quiz đã duyệt cho <b>Buổi 4: DAY04 — Prompt Engineering &amp; Tool Calling</b>.</p>
        <button type="button" className="btn-primary" onClick={() => onOpenDay(ACTIVE_DAY)}>Mở Buổi 4: DAY04</button>
      </div>
      <section className="notes-card">
        <TeacherNotes section={null} unlocked={false} onLoadInsight={() => {}} />
      </section>
    </>
  );
}

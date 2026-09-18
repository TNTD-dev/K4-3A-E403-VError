import React, { useEffect, useState } from "react";
import { request } from "./api.js";
import { ACTIVE_DAY, LESSONS } from "./course.js";
import { Icon, Logo } from "./icons.jsx";

const WEEK = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

function greeting(date = new Date()) {
  const hour = date.getHours();
  if (hour >= 5 && hour < 11) return "Sáng nay BẢO có vướng chỗ nào không?";
  if (hour >= 11 && hour < 13) return "Trưa nay BẢO có vướng chỗ nào không?";
  if (hour >= 13 && hour < 18) return "Chiều nay BẢO có vướng chỗ nào không?";
  if (hour >= 18 && hour < 23) return "Tối nay BẢO có vướng chỗ nào không?";
  return "Đừng thức khuya quá nhé BẢO!";
}

export function TopNav({ onOpenDay }) {
  return (
    <header className="home-nav">
      <a className="home-brand" href="./" aria-label="VLearn trang chủ">
        <Logo />
        <span className="brand-divider" aria-hidden="true" />
        <span className="brand-word"><b>V</b>Learn</span>
      </a>
      <nav className="home-links" aria-label="Điều hướng chính">
        <a className="active" href="./" aria-current="page"><Icon name="home" size={24} />Trang chủ</a>
        <button type="button" onClick={() => onOpenDay(ACTIVE_DAY)}><Icon name="bookOpen" size={24} />Khóa học</button>
        <button type="button" disabled><Icon name="dumbbell" size={24} />Luyện tập<em>Sắp ra mắt</em></button>
        <button type="button" onClick={() => onOpenDay(ACTIVE_DAY)}><Icon name="flask" size={24} />Lab<em className="new">Mới</em></button>
        <button type="button" className="more" aria-label="Thêm"><Icon name="chevronDown" size={22} /></button>
      </nav>
      <div className="home-tools">
        <span className="lang-toggle" role="group" aria-label="Ngôn ngữ"><span>EN</span><b>VI</b></span>
        <button type="button" aria-label="Chế độ tối"><Icon name="moon" size={22} /></button>
        <button type="button" className="bell" aria-label="1 thông báo"><Icon name="bell" size={22} /><i>1</i></button>
        <span className="avatar">L</span>
      </div>
    </header>
  );
}

export default function HomePage({ onOpenDay }) {
  const [progress, setProgress] = useState(null);
  const [tab, setTab] = useState("k4");
  const [resetState, setResetState] = useState("idle");

  useEffect(() => {
    request("/api/v1/sections").then(setProgress).catch(() => setProgress(null));
  }, []);

  async function resetDemo() {
    if (resetState === "busy") return;
    setResetState("busy");
    try {
      const toc = await request("/api/v1/progress/reset", { method: "POST" });
      setProgress(toc);
      setResetState("done");
      window.setTimeout(() => setResetState("idle"), 2500);
    } catch {
      setResetState("idle");
    }
  }

  const tried = progress?.sections?.filter(item => !item.slidesLocked) || [];
  const weak = tried.filter(item => !item.completed).slice(0, 3);
  const total = progress?.day?.totalSections || 8;
  const today = (new Date().getDay() + 6) % 7;
  const measured = tried.length
    ? `Day04 đã đo được ${tried.length}/${total} phần kiến thức.`
    : "chưa có phần kiến thức nào được đo.";
  const openLesson = (event, day) => {
    event.preventDefault();
    onOpenDay(day);
  };

  return (
    <div className="home-shell">
      <TopNav onOpenDay={onOpenDay} />
      <main className="home-page">
        <section className="home-welcome">
          <div>
            <h1>{greeting()} <span aria-hidden="true">👋</span></h1>
            <p>Chào mừng môn L3-L4 - Khóa 4 Phase 1. Còn 15 buổi, và {measured}</p>
          </div>
          <div className="home-actions">
            <button type="button" className="home-cta" onClick={() => onOpenDay(ACTIVE_DAY)}>Vào khóa học</button>
            <button
              type="button"
              className={`home-reset ${resetState === "done" ? "done" : ""}`}
              onClick={resetDemo}
              disabled={resetState === "busy"}
              title="Xóa tiến độ, phiên học và cache phân tích slide"
            >
              <Icon name="rotate" size={18} />
              {resetState === "busy" ? "Đang xóa cache…" : resetState === "done" ? "Đã reset demo" : "Làm lại từ đầu"}
            </button>
          </div>
        </section>

        <section className="home-grid">
          <div>
            <div className="home-heading">
              <h2>Khóa học của tôi</h2>
              <button type="button" className="see-all">Xem tất cả</button>
            </div>
            <div className="course-card">
              <div className="course-tabs" role="tablist">
                <button type="button" role="tab" aria-selected={tab === "k4"} className={tab === "k4" ? "on" : ""} onClick={() => setTab("k4")}>L3-L4 - Khóa 4 Phase 1</button>
                <button type="button" role="tab" aria-selected={tab === "k3"} className={tab === "k3" ? "on" : ""} onClick={() => setTab("k3")}>Khoá 3 Phase 1</button>
              </div>
              {tab === "k4" ? (
                <div className="lesson-list">
                  {LESSONS.map(item => {
                    const current = item.day === ACTIVE_DAY;
                    return (
                      <a
                        key={item.day}
                        href={`?day=${item.day}`}
                        className={`lesson-row ${current ? "current" : ""}`}
                        onClick={event => openLesson(event, item.day)}
                      >
                        <span className="lesson-radio" aria-hidden="true">
                          {current && <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" /><path d="M9.8 7.6 16 12l-6.2 4.4z" /></svg>}
                        </span>
                        <span className="lesson-label">{item.label}</span>
                        {current && <strong>Đang học...</strong>}
                      </a>
                    );
                  })}
                </div>
              ) : (
                <p className="course-empty">Khoá 3 Phase 1 chưa có buổi học trong prototype này.</p>
              )}
            </div>
          </div>

          <aside className="home-side">
            <div className="home-heading"><h2>Chuỗi ngày học</h2></div>
            <section className="streak-card" aria-label="Chuỗi ngày học">
              <Icon name="flame" size={42} className="streak-flame" strokeWidth={0} fill="currentColor" />
              <b>0</b>
              <p>ngày liên tiếp</p>
              <ol className="streak-week">
                {WEEK.map((label, index) => (
                  <li key={label} className={index === today ? "today" : ""}>
                    <span><Icon name="flame" size={22} strokeWidth={1.6} /></span>
                    <small>{label}</small>
                  </li>
                ))}
              </ol>
              <footer>
                <span>Hôm nay chưa tính</span>
                <button type="button" onClick={() => onOpenDay(ACTIVE_DAY)}>Ôn nhanh</button>
              </footer>
            </section>

            <div className="home-heading"><h2>Chỗ bạn đang yếu</h2></div>
            <section className="side-card">
              {weak.length ? (
                <ul className="weak-list">
                  {weak.map(item => (
                    <li key={item.sectionId}>
                      <button type="button" onClick={() => onOpenDay(ACTIVE_DAY)}>
                        <span>Day04 · {item.title}</span>
                        <small>Đã thử pre-quiz, chưa giảng lại</small>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>Chưa đo được phần nào. Làm một bài quiz để VLearn biết bạn đang ở đâu.</p>
              )}
            </section>

            <div className="home-heading">
              <h2>Hoạt động học tập</h2>
              <button type="button" className="see-all">Xem tất cả</button>
            </div>
            <section className="side-card activity" />
          </aside>
        </section>
      </main>
    </div>
  );
}

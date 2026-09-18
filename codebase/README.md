# VError D2 · React + FastAPI

VError is a local monolith for the Track D2 Prompt Engineering learning slice inside a VLearn Day player.
The browser client is React.
The runtime API is Python FastAPI + Pydantic.
SQLite stores sessions, attempts, coach outputs, day progress, and hashed events.
OpenAI is used only for bounded coach wording, with `MODEL_MODE=offline` template fallback.

## Product shape

Demo day: **Bài 4 · DAY04 Prompt Engineering & Tool Calling**.

The React shell mirrors the VLearn Day player:

- header with day label, progress, **Đặt câu hỏi với AI**, **Gửi yêu cầu**
- left nav: **Slides / Video / KC & Luyện tập**
- eight TOC sections from the course deck
- PDF slide viewer for the reviewed 43-page deck

Before each knowledge section the learner gets one easy VError attempt.
That section's slides stay locked until the first attempt is in.
After the attempt, VError unlocks the matching PDF pages, highlights the wrong assumption against a reviewed page, and keeps retry / explain-back / transfer until understanding is evidenced.
Completing an attempt also unlocks the next section's attempt slot.

The question set is first-class: eight items, one core claim per TOC section, each exposing a likely wrong assumption grounded in reviewed PDF pages.

D2 mechanics stay in force:

- public item without the answer key
- evaluation in code
- one bounded D2 Coach
- citation verification in code
- event log

No TypeScript Fastify runtime, no three independent agents, no RAG, no teacher dashboard, no extra days, no PostgreSQL, no serverless.

## Deck

Copy of the Day 04 course deck:

`frontend/public/prompt-engineering-tool-calling.pdf`

## Run locally

Requirements: Python 3.11-3.13 and Node.js 20-24.

### Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e '.[test]'
MODEL_MODE=offline uvicorn app.main:app --reload --port 8000
```

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.
Vite proxies `/api`, health checks, and the PDF path to FastAPI when needed.
The deck also ships from `frontend/public` for the Vite dev server.

### Chạy nhanh trên Windows

1. Mở `backend/.env`, dán `OPENAI_API_KEY` để bật Question Agent và D2 Coach thật.
2. Từ thư mục `codebase`, chạy `powershell -ExecutionPolicy Bypass -File .\run-live.ps1`.
3. Mở `http://127.0.0.1:5173`.

`run-live.ps1` khởi động backend ẩn và frontend ở terminal hiện tại; dừng frontend bằng Ctrl+C sẽ dừng luôn backend. Nếu không có key hoặc provider lỗi, giao diện ghi rõ đang dùng câu hỏi đã duyệt thay vì giả vờ là AI thật.

For one-process local serving, run `npm run build`; FastAPI serves `frontend/dist` and the PDF when present.

### Modes

- Default `MODEL_MODE=offline` is deterministic and needs no network or API key.
- Set `MODEL_MODE=live`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL` only for bounded coach wording.
- Every live draft is schema- and citation-verified, with reviewed offline fallback on provider errors or unsafe output.

## Tests

```bash
cd backend
. .venv/bin/activate
pytest
```

Coverage:

- deterministic evaluator for all eight section items
- API contract and private answer key
- section attempt/slide lock progression
- offline coach fallback and citation verification

## Content layout

- `content/items.v1.json` - eight public items
- `content/answer-keys.v1.json` - server-only keys
- `content/sources.v1.json` - reviewed PDF anchors
- `content/citation-support.v1.json` - diagnosis → allowed citations
- `backend/app/sections.py` - TOC + page ranges

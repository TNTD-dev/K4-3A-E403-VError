# VError D2

VError is a local monolith for the Track D2 Prompt Engineering learning slice.
The browser client is a React application and the runtime API is Python FastAPI.
The learning flow remains server-owned: the public item never contains the answer key, the deterministic evaluator chooses the misconception, and the bounded D2 Coach only writes grounded wording.

## Run locally

Requirements: Python 3.11-3.13 and Node.js 20-24.

### Backend

```bash
cd backend
python -m venv .venv
. .venv/bin/activate # Windows: .venv\\Scripts\\activate
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
Vite proxies API requests to FastAPI.
For one-process local serving, run `npm run build`; FastAPI serves `frontend/dist` when it exists.

The default `MODEL_MODE=offline` is deterministic and needs no network or API key.
Set `MODEL_MODE=live`, `OPENAI_API_KEY`, and optionally `OPENAI_MODEL` only for bounded coach wording.
Every live draft is schema- and citation-verified, with reviewed offline fallback on provider errors or unsafe output.

## Tests

```bash
cd backend
. .venv/bin/activate
pytest
```

Tests cover the deterministic evaluator, API contract and offline fallback behavior.
SQLite stores sessions, attempts, coach outputs and hashed event records.
PostgreSQL and serverless deployment are intentionally out of scope.

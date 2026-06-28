# FinEvent Admin Frontend

Next.js admin dashboard for operating the FinEvent-VN NLP/RAG extraction pipeline.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- TanStack Query
- lucide-react
- Recharts
- react-markdown

The UI uses project-specific FinEvent tokens and a feature-first structure:

- feature-first folders;
- dense operational dashboard;
- FastAPI admin API client;
- authenticated fetch streaming for live logs;
- report, DB, workflow and structured-output screens.

## Setup

Recommended local workflow from the repository root uses Docker Compose:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-local-stack.ps1
```

or:

```powershell
docker compose up --build
```

This starts PostgreSQL/pgvector, applies database migrations in the backend
container, starts FastAPI and starts this Next.js admin frontend.

Manual frontend-only workflow:

```powershell
cd frontend/admin
pnpm install
copy .env.example .env.local
pnpm dev
```

Default URL:

```text
http://localhost:3000/admin
```

## Runtime Config

Open `/admin/settings` and set:

- FastAPI base URL: `http://127.0.0.1:18000` when running through Docker Compose
- Admin API key: value of `FINEVENT_ADMIN_API_KEY`

The key is stored only in browser `localStorage`.

## Native Backend

Only use this when you intentionally bypass Docker Compose:

```powershell
$env:PYTHONPATH="src"
python -m uvicorn finevent.api.main:app --reload --port 8000
```

The frontend calls only `/admin/*` endpoints. It does not call model APIs, access PostgreSQL directly, read `.env`, or parse large vectors client-side.

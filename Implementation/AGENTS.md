# AGENTS.md — Smart Drive Filer

This file tells any Antigravity agent working in this repo how the project is set up, what conventions to follow, and where to find the task list. Read this before starting any task.

## Project summary
An app that analyzes uploaded documents, suggests the best folder in the user's Google Drive tree (or proposes creating a new one when it detects a cluster of related documents), and provides semantic search. Full spec: `implementation-plan.md`. Task breakdown: `TASKS.md`.

## Repo layout
```
/frontend   → React + TypeScript, Tailwind
/backend    → Python, FastAPI
/backend/workers → Celery tasks (extraction, classification, embeddings)
docker-compose.yml → Postgres (pgvector) + Redis, local dev only
implementation-plan.md → full architecture/design reference
TASKS.md → phase-by-phase task list with Definition of Done per phase
```

## Setup commands
```
docker compose up -d          # Postgres + Redis
cd backend && pip install -r requirements.txt
cd backend && uvicorn main:app --reload
cd frontend && npm install
cd frontend && npm run dev
```

## Environment variables (see `.env.example`, never commit `.env`)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — Drive OAuth
- `ANTHROPIC_API_KEY` — classification/question/folder-naming calls
- `EMBEDDING_API_KEY` — embedding provider
- `DATABASE_URL`, `REDIS_URL`
- `JWT_SECRET`

## Conventions
- **OAuth scope**: `drive.file` (+`drive.metadata.readonly` for tree reads). Never request full `drive` scope. Never add a password/credential input field anywhere.
- **Structured LLM output**: every Anthropic API call in the pipeline must request and validate JSON output against a schema — no free-text parsing of model output.
- **Thresholds live in config, not hardcoded**: placement confidence bands (0.85 / 0.60) and clustering similarity (0.75) belong in `backend/config.py`, not inline magic numbers — they'll need tuning per Section 12 of the implementation plan.
- **No silent Drive writes**: folder creation and file placement always require an explicit user confirmation step in the UI — never auto-commit without user action, even at high confidence.
- **Temp files**: anything written to local/scratch storage during extraction must be deleted after the job completes.
- **Tests**: each backend endpoint needs at least one test hitting a real (or mocked) Drive API call path — don't just test the DB layer.

## How to work a task
1. Open `TASKS.md`, find the next unchecked phase.
2. Confirm its dependencies (listed per phase) are already checked off.
3. Implement against the Definition of Done for that phase — don't move on until it's met.
4. Produce a Walkthrough that demonstrates the Definition of Done explicitly (screenshot/log showing the actual pass condition, not just "code compiles").
5. Check the box in `TASKS.md` and note anything the next phase's agent should know (e.g., a config value you changed).

## Verification expectations
For anything touching Drive, verify against the real Drive API in a test account, not a mock — placement and folder-creation bugs are easy to miss in a mocked response.

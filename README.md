# Smart Drive Filer

AI-powered Google Drive document organizer — analyzes uploads, suggests the right folder, clusters related documents, and provides semantic search.

## Quick Start

### Prerequisites
- Docker Desktop (for Postgres + Redis)
- Python 3.11+
- Node.js 18+
- Google Cloud project with Drive API + OAuth 2.0 client
- Anthropic API key
- Voyage AI (or compatible) embedding API key

### 1. Infrastructure
```bash
docker compose up -d
```

### 2. Backend
```bash
cd backend
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Celery Worker (separate terminal)
```bash
cd backend
celery -A workers.celery_app worker --loglevel=info
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Architecture

```
Frontend (React + TS + Tailwind, port 5173)
   ↓ proxy
Backend (FastAPI, port 8000)
   ↓ Celery tasks
Background workers → Google Drive API + Anthropic + Voyage AI
   ↓
Postgres + pgvector (port 5432) + Redis (port 6379)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google` | Start OAuth flow |
| GET | `/auth/google/callback` | OAuth callback |
| GET | `/auth/me` | Current user |
| POST | `/auth/logout` | Sign out |
| GET | `/folders/` | Cached folder tree |
| POST | `/folders/refresh` | Enqueue Drive re-sync |
| POST | `/documents/upload` | Upload + enqueue analysis |
| GET | `/documents/{id}` | Status + placement suggestion |
| POST | `/documents/{id}/answer` | Answer clarifying question |
| POST | `/documents/{id}/confirm` | Confirm placement → Drive upload |
| GET | `/clusters/` | Pending cluster suggestions |
| POST | `/clusters/{id}/accept` | Create folder + move members |
| POST | `/clusters/{id}/dismiss` | Dismiss cluster |
| GET | `/search/?q=...` | Semantic search |
| GET | `/rules/` | Learned placement rules |
| DELETE | `/rules/{id}` | Delete a rule |

## Confidence Thresholds (tuneable in `backend/config.py`)

| Threshold | Value | Behavior |
|-----------|-------|----------|
| `PLACEMENT_AUTO_THRESHOLD` | 0.85 | Auto-suggest, no question |
| `PLACEMENT_QUESTION_THRESHOLD` | 0.60 | Ask one clarifying question |
| `CLUSTERING_SIMILARITY_THRESHOLD` | 0.75 | Pairwise similarity to form a cluster |
| `RULE_MATCH_THRESHOLD` | 0.90 | Rule short-circuit (learning loop) |
| `RULE_CONFIDENCE_MIN_HITS` | 3 | Hits before rule is fully auto-confident |

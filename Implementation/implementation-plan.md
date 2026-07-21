# Smart Drive Filer — Final Implementation Plan (Google Antigravity)

An app that ingests a document, analyzes it, asks clarifying questions only when needed, places it in the best-matching folder in the user's Google Drive tree, proposes creating a new folder when it detects a cluster of related unfiled documents, and gives the user semantic search over everything it has filed.

This version folds in the refinements from the review pass: explicit confidence thresholds, a tuning methodology for clustering, parallelized agent workspaces, per-phase "Definition of Done" checklists (so each Antigravity Walkthrough has a clear pass/fail bar), API contracts, and a risk list.

---

## 1. Product Recap

**Core loop:** Upload → Analyze → (Clarify if uncertain) → Suggest placement (existing or new folder) → Confirm/Adjust → Upload to Drive → Indexed & searchable.

**Feature set:**
- OAuth-based Google Sign-In (`drive.file` scope — never raw credentials)
- Document analysis: type detection, summary, entity extraction
- Confidence-gated clarifying questions (asked only when uncertain)
- Folder-tree-aware placement suggestion with a "why" explanation
- Clustering-based **new-folder suggestion** when 2+ unfiled documents share a topic with no strong existing-folder match
- Preview-before-commit with one-click path adjustment
- Duplicate/version detection on the target folder
- Batch upload with a bulk-approve table
- Learning loop from user corrections
- Semantic search bar
- Background/async processing so uploads never block the UI

---

## 2. Architecture

```
┌─────────────────────────────┐
│  Frontend (React + TS)       │
│  - Upload / batch table      │
│  - Question modal            │
│  - Cluster banner             │
│  - Search bar                │
│  - Folder tree preview        │
└───────────┬──────────────────┘
            │ REST + WebSocket (job progress)
┌───────────▼──────────────────┐
│  Backend API (FastAPI)       │
│  - Auth / session management │
│  - Upload orchestration       │
│  - Job queue (Celery/Redis)   │
└───┬───────────┬──────────────┘
    │           │
┌───▼───┐   ┌───▼─────────────────┐
│Google │   │ Analysis Pipeline    │
│Drive  │   │ - Text/OCR extraction│
│API    │   │ - LLM classify/      │
│(OAuth │   │   summarize/extract  │
│drive. │   │ - Embedding generation│
│file)  │   │ - Placement matcher   │
└───────┘   │ - Clustering detector │
            └───┬───────────────────┘
                │
        ┌───────▼────────┐
        │ Postgres +       │
        │ pgvector         │
        │ (metadata,       │
        │  embeddings,     │
        │  rules)          │
        └──────────────────┘
```

Drive remains the source of truth for file bytes and the folder tree; your own DB holds extracted text, embeddings, and placement history so search and clustering stay fast without hammering the Drive API.

---

## 3. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript, Tailwind | Fast to build upload/question/search UI |
| Backend | Python, FastAPI | Strong Google API SDK support, easy async workers |
| Auth | Google OAuth 2.0, `drive.file` scope (+`drive.metadata.readonly` for tree reads) | Least-privilege |
| Job queue | Celery + Redis | Async doc processing, batch uploads |
| DB | PostgreSQL + `pgvector` | One store for metadata + embeddings |
| Text extraction | `pdfplumber` + Tesseract OCR fallback | Handles native + scanned docs |
| LLM | Claude via Anthropic API | Structured JSON for classification, question generation, folder naming |
| Embeddings | Any strong embedding model (e.g. Voyage or an OpenAI-class embedding endpoint) | Semantic search + clustering |
| Hosting | Cloud Run (API + workers) + managed Postgres | Scales workers independently of the API |

---

## 4. Data Model

- `users` — id, google_sub, oauth_refresh_token_encrypted, created_at
- `documents` — id, user_id, drive_file_id (nullable until placed), filename, extracted_text, summary, doc_type, entities (jsonb), embedding, status (`pending` / `needs_input` / `placed`), created_at
- `folder_index` — id, user_id, drive_folder_id, name, parent_id, path, embedding, last_synced
- `placements` — id, document_id, suggested_folder_id, final_folder_id, confidence, was_corrected (bool), created_at
- `clusters` — id, user_id, topic_label, member_document_ids (jsonb array), status (`suggested`/`accepted`/`dismissed`), created_at
- `placement_rules` — id, user_id, pattern_embedding, pattern_label, target_folder_id, hit_count

---

## 5. Google Drive Integration

1. **OAuth**: "Sign in with Google" → consent screen requesting `drive.file` (+ `drive.metadata.readonly` if reading the existing tree). State plainly in the consent copy why the read-only scope is needed.
2. **Folder tree sync**: `files.list` filtered to `mimeType='application/vnd.google-apps.folder'`, cached into `folder_index`. Refresh on login, on a daily schedule, and via a manual "Refresh" button — never on every upload.
3. **Upload**: `files.create` with `parents: [folder_id]` after user confirmation.
4. **New folder creation**: `files.create` with the folder mimeType, then upload cluster members into it.
5. **Rate limits**: batch calls where possible; exponential backoff on 403/429; queue retries via Celery.

---

## 6. Analysis & Placement Pipeline (with tuned thresholds)

**Step 1 — Extraction:** text layer if present; OCR fallback for scans/images.

**Step 2 — LLM classification** (structured JSON):
```json
{
  "doc_type": "invoice | contract | notes | resume | ...",
  "summary": "one or two lines",
  "entities": { "dates": [], "orgs": [], "amounts": [] },
  "suggested_topic": "short label"
}
```

**Step 3 — Embedding:** embed `summary + entities` for matching.

**Step 4 — Placement matching, with explicit thresholds:**
| Confidence (cosine sim to best folder match) | Behavior |
|---|---|
| ≥ 0.85 | Auto-suggest that folder, no question, show "why" text |
| 0.60 – 0.85 | Ask **one** targeted question with the top 2-3 folder candidates as buttons |
| < 0.60 | Show top 3 candidates plus a free-text "type a folder name" fallback |

These thresholds are starting points — treat them as config values, not constants, and tune per Section 12.

**Step 5 — Clustering / new-folder suggestion:**
- After each analysis, gather the user's documents with status `pending` or `needs_input`.
- Pairwise cosine similarity among their embeddings; group documents whose mutual similarity is ≥ 0.75 into a candidate cluster.
- Only surface a cluster suggestion if it has **≥ 2 members** and **none of them** had a placement match ≥ 0.85 in Step 4 (i.e., don't propose a new folder when a good existing one already fits).
- LLM call to propose a folder name from the member summaries.
- On accept: create the folder, upload/move members into it, mark cluster `accepted`, and write a `placement_rules` entry so similar future docs route there directly.
- On dismiss: mark `dismissed`; don't re-propose the same member set again (check by document-id-set before re-surfacing).

**Step 6 — Learning loop:** on any manual override, store an embedding-keyed `placement_rules` row. Before running Step 4 on a new document, check for a rule match ≥ 0.90 similarity first — if found, short-circuit straight to that folder (still shown as a suggestion, not silently auto-filed, until the rule has ≥ 3 confirmed hits).

---

## 7. UX Flow

1. Drag-drop or select files (single or batch); processing starts immediately in the background — user can keep adding files while earlier ones process.
2. Per-document card: suggested path, one-line "why" explanation, confidence badge.
3. If in the 0.60–0.85 band: inline single-question prompt, button-based options.
4. If a cluster is detected: distinct banner — "3 files look related — create folder '<suggested name>' for them?" with an editable name field and Accept/Dismiss.
5. Batch view: table [File | Suggested Folder | Confidence | Status] with "Approve All ≥ 90%" bulk action.
6. Pre-commit duplicate check: Replace / Keep Both / Version options if a similar file already exists in the target folder.
7. Search bar: semantic + type/date filters; results show snippet, path, and an "open in Drive" deep link.
8. Settings page: view/edit learned placement rules, revoke Drive access, manual folder-index refresh.

---

## 8. Security Checklist

- OAuth only, `drive.file` (+`drive.metadata.readonly` if needed) — never a password field, never the broad `drive` scope.
- Encrypt refresh tokens at rest (KMS-managed key); never send them to the frontend.
- Short-lived session JWTs for the API; refresh happens server-side only.
- Temp files (pre-Drive-upload) live in a server-side scratch path, deleted immediately after processing — never left in client-accessible storage.
- Per-user rate limiting on API endpoints that trigger LLM calls.
- Audit log of every placement/move for user trust and debugging.

---

## 9. API Contract Summary (for the agents to implement against)

```
POST   /auth/google/callback        -> creates session, stores encrypted refresh token
GET    /folders                     -> cached folder_index tree for the user
POST   /folders/refresh             -> forces a re-sync from Drive
POST   /documents/upload            -> multipart upload, returns document_id, enqueues job
GET    /documents/:id               -> status, summary, suggested placement, confidence
POST   /documents/:id/answer        -> submit clarifying-question response
POST   /documents/:id/confirm       -> confirm final folder, triggers Drive upload
GET    /clusters                    -> pending cluster suggestions for the user
POST   /clusters/:id/accept         -> create folder + move members
POST   /clusters/:id/dismiss        -> mark dismissed
GET    /search?q=...                -> semantic search results
GET    /rules                       -> learned placement_rules for settings page
DELETE /rules/:id                   -> remove a learned rule
```

---

## 10. Build Plan for Google Antigravity

Work happens across the **Manager surface** (spawn/orchestrate agents asynchronously) and the **Editor view** (for the parts you want to drive by hand). Each agent task below ends in a **Walkthrough** — verify it against the Definition of Done before starting the next dependent phase.

### Phase 0 — Workspace setup (do yourself, Editor view)
- Scaffold two workspaces: `frontend/` (React+TS) and `backend/` (FastAPI).
- Docker Compose for Postgres+pgvector and Redis.
- Google Cloud project: enable Drive API, create OAuth client, put secrets in `.env` (git-ignored).
- **Definition of Done:** `docker compose up` brings up DB + Redis; both workspaces run `hello world` endpoints/pages.

### Phase 1 & 2 — Run as parallel agents in separate workspaces

**Agent A (workspace: `backend/auth`) — "Implement Google OAuth login"**
Build `/auth/google` + callback, token exchange, encrypted refresh-token storage, session JWT issuance, and a "Sign in with Google" button on the frontend. Antigravity should drive the browser through the real consent screen to verify.
- **Definition of Done:** Walkthrough shows a logged-in session with a valid JWT cookie/header and a DB row in `users`.

**Agent B (workspace: `backend/pipeline`) — "Document upload + extraction skeleton"**
Build the upload endpoint, Celery worker wiring, OCR/text extraction, and the `documents` table writes (no LLM yet). Runs independently of auth since it only needs a stub user_id for now.
- **Definition of Done:** Walkthrough shows a sample PDF and a sample scanned image both producing non-empty `extracted_text` rows.

*Merge point: wire Agent B's pipeline to use the real authenticated user_id from Agent A before Phase 3.*

### Phase 3 — Agent Task: "Sync and cache the Drive folder tree"
Build `folder_index` sync job + `/folders` + `/folders/refresh`, and a tree view component to visually confirm.
- **Definition of Done:** Rendered tree in the browser matches your real Drive folder structure; refresh button re-syncs correctly after you add a folder in Drive manually.

### Phase 4 — Agent Task: "LLM classification + embeddings"
Wire the Anthropic API call for structured classification, plus embedding generation; persist to `documents`. Have the agent write a terminal test script that runs 4-5 sample docs and prints JSON output.
- **Definition of Done:** Script output shows correctly-typed `doc_type` for at least 4/5 varied sample documents (invoice, contract, notes, resume, random letter).

### Phase 5 — Agent Task: "Placement matcher + confidence-gated questions"
Implement the threshold table from Section 6, the `/documents/:id` suggestion payload, and the question modal.
- **Definition of Done:** Upload one obviously-matching doc (auto-suggested, no question) and one ambiguous doc (question modal appears with sensible candidate folders) — both verified in-browser.

### Phase 6 — Agent Task: "Clustering & new-folder suggestion"
Implement pairwise similarity clustering, the LLM folder-naming call, `clusters` table, `/clusters` endpoints, and the accept/dismiss banner.
- **Definition of Done:** Upload 3 sample docs on a shared niche topic with no matching existing folder — banner appears proposing a sensible folder name; Accept creates the real folder in Drive and moves all 3 files into it. Also verify a dismiss doesn't re-surface the same set.

### Phase 7 — Agent Task: "Drive write-back for individual placements"
Implement `files.create` for confirmed single-document placements, duplicate-check logic (`Replace`/`Keep Both`/`Version`), and the preview/confirm UI.
- **Definition of Done:** Confirming a placement lands the real file in the correct real Drive folder; re-uploading a similar file into the same folder triggers the duplicate-check modal.

### Phase 8 — Agent Task: "Learning loop"
Implement override capture into `placement_rules`, the ≥0.90 short-circuit check, and the 3-hit auto-confidence bump described in Step 6.
- **Definition of Done:** Manually override the suggested folder for 2 similar mock invoices; the 3rd similar invoice is suggested via the learned rule (visibly labeled "based on your past choices" in the UI).

### Phase 9 — Agent Task: "Batch upload UI + bulk approve"
Batch table, bulk-approve action, WebSocket job status updates.
- **Definition of Done:** Drag 5+ files at once; table updates live as each finishes processing; bulk-approve correctly commits only the rows above the chosen confidence threshold.

### Phase 10 — Agent Task: "Semantic search"
`/search` endpoint + search bar UI with snippets, path, and Drive deep link.
- **Definition of Done:** A natural-language query (e.g. "that contract about the office lease") returns the right document even when the filename doesn't contain those words.

### Phase 11 — Polish pass
Duplicate/version modal styling, "why this folder" explanation text everywhere, settings page (rules list, scope info, refresh), error/empty states.
- **Definition of Done:** Walkthrough screenshots covering: empty state, error state (simulate a failed Drive call), and the settings page showing at least one learned rule from Phase 8's test.

---

## 11. Milestone Order for a Demo-able MVP

1. Auth + folder sync + manual single-file upload (no AI) → proves Drive plumbing.
2. Add classification + confidence-gated placement → proves the core AI loop. **(Demoable MVP)**
3. Add clarifying questions + "why" explanations → proves the UX differentiator.
4. Add clustering/new-folder suggestion → proves the standout feature.
5. Add search → makes it useful day-to-day.
6. Add learning loop + batch mode → production polish.

---

## 12. Tuning & Testing Plan for Clustering (the highest-risk piece)

Clustering thresholds will not be right on the first guess — budget a dedicated tuning pass:

1. Assemble a test corpus of 20-30 realistic documents spanning at least 4 natural clusters (e.g., "tax docs," "apartment lease," "side-project notes," "recipes") plus 5-6 genuine singletons that shouldn't cluster with anything.
2. Run the pipeline, log the pairwise similarity matrix, and manually check: did true clusters form? Did singletons get wrongly grouped?
3. Adjust the 0.75 clustering threshold and the 0.85 "skip cluster because a good folder exists" threshold based on this corpus, not on a single anecdotal test.
4. Re-run after every prompt or embedding-model change — clustering is more sensitive to embedding quality than single-document classification is.

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Drive API rate limits under batch upload | Queue + backoff in Celery; surface a "processing may take a few minutes" note in bulk mode |
| LLM misclassification on unusual docs | Always show confidence + "why," let user override in one click, feed overrides into the learning loop |
| Clustering false-positives group unrelated docs | Conservative default threshold (0.75) plus a mandatory user Accept step — never auto-create folders silently |
| OAuth token expiry/revocation mid-session | Graceful re-auth prompt rather than silent failure; detect 401 from Drive and redirect to re-consent |
| Folder tree drift (user reorganizes in Drive directly) | Manual refresh button + scheduled daily resync |

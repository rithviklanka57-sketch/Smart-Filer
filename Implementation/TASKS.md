# TASKS.md — Smart Drive Filer Build Checklist

Work top to bottom. Phases 1 and 2 can be assigned to two agents in parallel; everything else is sequential. Full context for each phase is in `implementation-plan.md`. Check a box only when its Definition of Done is actually verified, not just implemented.

---

### [ ] Phase 0 — Workspace setup
**Owner:** human (Editor view)
**Steps:** scaffold `frontend/` + `backend/`; docker-compose for Postgres+pgvector and Redis; Google Cloud project with Drive API enabled and OAuth client created; `.env` populated.
**Definition of Done:** `docker compose up` brings up DB + Redis; both workspaces serve a hello-world route/page.

---

### [ ] Phase 1 — Google OAuth login *(parallel with Phase 2)*
**Depends on:** Phase 0
**Steps:** `/auth/google` + callback route, token exchange, encrypted refresh-token storage, session JWT, "Sign in with Google" button.
**Definition of Done:** Walkthrough shows a real logged-in session via the actual Google consent screen, with a `users` row created in Postgres.

---

### [ ] Phase 2 — Upload + extraction skeleton *(parallel with Phase 1)*
**Depends on:** Phase 0
**Steps:** upload endpoint, Celery worker wiring, OCR/text extraction (native + scanned), `documents` table writes. Use a stub user_id for now.
**Definition of Done:** A sample PDF and a sample scanned image both produce non-empty `extracted_text` rows.

**⚠ Merge step (human):** wire Phase 2's pipeline to use the real authenticated user_id from Phase 1 before starting Phase 3.

---

### [ ] Phase 3 — Drive folder tree sync
**Depends on:** Phases 1 & 2 merged
**Steps:** `folder_index` sync job, `/folders`, `/folders/refresh`, tree view component.
**Definition of Done:** Rendered tree matches the real Drive folder structure; manually adding a folder in Drive and clicking Refresh picks it up.

---

### [ ] Phase 4 — LLM classification + embeddings
**Depends on:** Phase 3
**Steps:** structured classification call (doc_type/summary/entities/topic), embedding generation, persist to `documents`.
**Definition of Done:** Terminal test script on 5 varied sample docs (invoice, contract, notes, resume, random letter) — at least 4/5 correctly typed.

---

### [ ] Phase 5 — Placement matcher + confidence-gated questions
**Depends on:** Phase 4
**Steps:** implement threshold bands (≥0.85 auto, 0.60–0.85 question, <0.60 fallback), `/documents/:id` suggestion payload, question modal.
**Definition of Done:** One obviously-matching doc auto-suggests with no question; one ambiguous doc triggers the question modal with sensible candidates — both verified in-browser.

---

### [ ] Phase 6 — Clustering & new-folder suggestion
**Depends on:** Phase 5
**Steps:** pairwise similarity clustering (≥0.75 threshold, only when no member matched ≥0.85 in Phase 5), LLM folder-naming call, `clusters` table, accept/dismiss banner.
**Definition of Done:** 3 sample docs on a shared unfiled topic trigger the banner with a sensible name; Accept creates the real Drive folder and moves all 3 files; Dismiss doesn't re-surface the same set.

---

### [ ] Phase 7 — Drive write-back for individual placements
**Depends on:** Phase 5
**Steps:** `files.create` on confirm, duplicate-check (Replace/Keep Both/Version), preview/confirm UI.
**Definition of Done:** Confirming a placement lands the real file in the correct Drive folder; uploading a similar file into the same folder triggers the duplicate-check modal.

---

### [ ] Phase 8 — Learning loop
**Depends on:** Phase 7
**Steps:** override capture into `placement_rules`, ≥0.90 short-circuit check, 3-hit confidence bump.
**Definition of Done:** Override the suggestion twice for similar mock invoices; the 3rd similar invoice is suggested via the learned rule, visibly labeled as such in the UI.

---

### [ ] Phase 9 — Batch upload UI + bulk approve
**Depends on:** Phase 7
**Steps:** batch table, bulk-approve action, WebSocket job status updates.
**Definition of Done:** Drag 5+ files at once; table updates live per file; bulk-approve commits only rows above the chosen confidence threshold.

---

### [ ] Phase 10 — Semantic search
**Depends on:** Phase 4
**Steps:** `/search` endpoint, search bar UI with snippet/path/Drive deep link.
**Definition of Done:** A natural-language query returns the right document even when the filename doesn't match the query terms.

---

### [ ] Phase 11 — Polish pass
**Depends on:** Phases 6, 8, 9, 10
**Steps:** duplicate/version modal styling, "why this folder" text everywhere, settings page (rules list, scope info, refresh), error/empty states.
**Definition of Done:** Walkthrough screenshots covering empty state, a simulated Drive-call failure, and the settings page showing at least one learned rule from Phase 8.

---

## Notes log
*(agents: append anything the next phase's agent should know here)*
-

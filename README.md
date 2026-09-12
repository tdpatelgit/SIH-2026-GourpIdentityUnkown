# Intelligent Land Record Digitization — Mocked Demo (SIH PS-26018)

> **Status: ✅ Working end-to-end demo (mocked tier). Verified live in browser + curl.**

SIH 2026 hackathon-demo build. A Next.js frontend uploads a scanned land-record
image to a FastAPI backend; the backend returns a canned/randomized JSON
payload (extracted fields + confidence scores) simulating an OCR/NER
pipeline. No real OCR, no DB, no auth — the goal is a believable, working
demo of the upload → processing → results-with-confidence flow.

Full plan: `.hermes/plans/2026-09-11_land-record-mock-fe-be-contract.md`
Scoping estimate (functional-prototype tier, not built now): `.hermes/plans/2026-09-11_land-record-digitization-timeline.md`

## Progress

| Task | Status |
|---|---|
| 1. Scaffold `backend/`, `mockups/` dirs | ✅ Done |
| 2. 5 UI mockup directions | ✅ Done — see `mockups/`, verified live in browser (all 5 interactive) |
| 3. FastAPI skeleton + `/health` | ✅ Done — verified `curl localhost:8000/health` → `{"status":"ok"}` |
| 4. Fixture data module (TDD) | ✅ Done — 3/3 tests passing |
| 5. `/api/analyze` endpoint (TDD) | ✅ Done — 2/2 tests passing (5/5 total backend tests) |
| 6. CORS for localhost:3000 | ✅ Done, included in main.py from the start |
| 7. Scaffold Next.js frontend | ✅ Done (TypeScript + Tailwind + App Router) |
| 8. Typed API client | ✅ Done — `frontend/src/lib/api.ts` |
| 9. Upload/results page | ✅ Done — `frontend/src/app/page.tsx`, verified live in real browser |
| 10. 5 mockups mounted as `/UIn/home` routes | ✅ Done — deletable independently, no separate server |
| 11. Pending-review status + doc store (backend) | ✅ Done — `/api/documents`, `/approve`, `/boundary` endpoints, 10/10 tests passing |
| 12. Gov Employee Portal (login + review + approve/hand-draw boundary) | ✅ Done — `/review/login`, `/review`, `/review/[id]`, verified live end-to-end |
| 13. SQLite persistence (replace in-memory store) | ✅ Done — `backend/db.py` (SQLAlchemy), 15/15 tests passing, verified data survives a real backend restart |
| 14. Uploader accounts (signup/login, "My Documents") | ✅ Done — `/account/login`, `/account`, real password-hashed accounts in SQLite, 24/24 tests passing, verified live end-to-end |
| 15. Dummy upload for 4 plots + government-record comparison for AI-accuracy review | ✅ Done — one-click dummy uploads, side-by-side AI-vs-government comparison table on the review page, verified live (2 clean matches + 2 deliberate AI errors caught) |
| 16. Reject + admin blacklist review for bad AI output/uploads | ✅ Done — `/review/[id]` Reject + Flag buttons, `/admin/blacklist` dashboard, 35/35 tests passing, verified live end-to-end (reject + flag→resolve→auto-reject flow) |
| 17. Manual field correction by reviewer | ✅ Done — `/review/[id]` "Edit fields" lets a reviewer correct AI-misread values in place instead of only approve/reject, 38/38 tests passing, verified live via real API round-trip |
| 18. Real TrOCR merged to main + per-upload AI toggle | ✅ Done — TrOCR branch merged into `main`; upload page has a "📋 Saved responses" / "🤖 AI review (TrOCR)" toggle per upload, 55/55 tests passing, verified live end-to-end with both modes through the real API |

**Live verification performed this session:**
- `pytest` in `backend/`: **5 passed**
- `curl http://localhost:8000/health` → `{"status":"ok"}`
- `curl -F file=@... /api/analyze` → full JSON payload with fields/confidence
- Real browser test (upload a file via the actual page): loading spinner →
  results table → "Needs review" banner rendered correctly with live data
  from the backend (confidence badges color-coded green/amber/red).
- All 5 `mockups/*.html` opened + click-driven through Upload → Processing →
  Results in a real browser; each renders and transitions correctly.

## UI mockups (`mockups/`)

5 disposable, self-contained HTML comparison pages (Tailwind CDN, no build
step) — each shows the same 3-screen flow (Upload → Processing → Results)
in a different visual direction, per your "1 simple, 4 grand" brief. Open
directly in a browser, e.g. `open mockups/3-saas-dashboard.html`.

| # | File | Direction | Feel |
|---|---|---|---|
| 1 | `1-minimal-mono.html` | **Minimal Mono** (the simple one) | Black/white/one accent, huge whitespace, thin-divider list, inline progress bars |
| 2 | `2-gov-trust.html` | Gov-Trust | Navy/gold official e-Governance portal, serif headings, bordered table |
| 3 | `3-saas-dashboard.html` | Modern SaaS Dashboard | Dark sidebar, stat cards, confidence pill badges, split content/summary panel |
| 4 | `4-map-forward.html` | Map-Forward | Split-screen: document preview + mock cadastral parcel map alongside fields |
| 5 | `5-review-queue.html` | Review-Queue | Ticketing-tool aesthetic, flagged fields as actionable cards (Approve/Edit), auto-approved summary strip |

**Pick one and I'll rebuild `frontend/src/app/page.tsx` to match it** — the
current live frontend (`/`) uses its own clean default UI (not one of these 5).

### Live routes (served from the Next.js app itself)

Each mockup is also mounted as its own route inside the Next.js app (static
HTML copied to `frontend/public/mockups/`, each route is a thin page that
iframes its file). This means deleting a direction later is just: delete
`frontend/src/app/UIn/` + its file in `frontend/public/mockups/` — no other
code changes needed.

| Route | Direction |
|---|---|
| http://localhost:3000/UI1/home | Minimal Mono (simple) |
| http://localhost:3000/UI2/home | Gov-Trust |
| http://localhost:3000/UI3/home | SaaS Dashboard |
| http://localhost:3000/UI4/home | Map-Forward |
| http://localhost:3000/UI5/home | Review-Queue |

Same Next.js dev server as the live app (`npm run dev` in `frontend/`,
already covered above) — no separate server needed.

## Gov Employee Portal — review, approve, or hand-draw boundary

New second surface for low-confidence documents: a login-gated portal where
a government employee makes the executive call on any `pending_review` doc
— either **approve as-is**, or **hand-draw the parcel boundary** with a
dot-and-line canvas tool (click to drop points, auto-connected as a
polygon).

| Route | Purpose |
|---|---|
| `/review/login` | Demo login (any non-empty employee ID + password works — mocked auth, `sessionStorage`-based, no real backend auth) |
| `/review` | Queue dashboard — pending vs resolved documents, live-refreshable |
| `/review/[id]` | Single-document review: extracted fields, confidence, and the boundary canvas + Approve button |

**Backend additions supporting this** (`backend/main.py`):
- In-memory `DOCUMENTS` store — every `/api/analyze` call now also saves a
  record with a `status` field (`auto_approved` | `pending_review` |
  `approved` | `boundary_drawn`) and `boundary` (null until hand-drawn).
- `GET /api/documents` (optional `?status=` filter), `GET /api/documents/{id}`,
  `POST /api/documents/{id}/approve`, `POST /api/documents/{id}/boundary`
  (`{"points": [[x,y], ...]}`, requires 3+ points).
- 10/10 backend tests passing (`pytest -v` in `backend/`).

**Verified live end-to-end** (real browser session, not simulated):
uploaded a low-confidence scan on `/` → showed "⏳ Pending review" status →
logged into `/review/login` → saw it in the pending queue on `/review` →
opened it, clicked "Draw boundary", placed 4 points on the canvas (dots +
connecting lines rendered), saved → status flipped to `boundary_drawn`.
Separately approved a second pending doc via "Approve as-is" → status
flipped to `approved`. Dashboard's "Resolved" section correctly showed
both outcomes afterward.

**Known limitation (mocked tier):** login is not real auth — any
credentials work, session is just a `sessionStorage` flag with no
server-side validation or token. Fine for a demo, not for production.

## Manual Field Correction by Reviewer

Beyond Approve/Reject/Flag, a reviewer can now directly correct any
AI-extracted field value on `/review/[id]` via a new "✎ Edit fields"
button next to the Extracted Fields table — turns the read-only table
into inline text inputs per field, "Save corrections" persists the
change and stamps the document `fields_edited_by_reviewer: true` (shown
as a small badge afterward), "Cancel" discards the edit.

This covers the case where the AI got a field wrong but the document is
otherwise fine — previously the only options were Approve-as-is (keeping
the wrong value) or Reject (throwing out an otherwise-correct document).

**Backend:** new `documents.fields_edited_by_reviewer` boolean column,
`POST /api/documents/{id}/fields` (`{"fields": [{"name","label","value","confidence"}, ...]}`,
requires at least one field, replaces the fields list wholesale). 3 new
tests (update/persist, empty-fields validation, 404) — 38/38 backend
tests passing.

**Verified live** via a real running server: uploaded a doc, corrected
its `khata_no` field from an AI-misread `"88/C"` to `"213-CORRECTED"`
through the actual HTTP API, confirmed via a fresh `GET` that both the
new value and the `fields_edited_by_reviewer: true` flag persisted.

## Real TrOCR Merged + Per-Upload AI Toggle

The `feature/trocr-integration` branch (deskew/denoise/contrast
preprocessing + human-readable field mapping — see
`backend/TROCR_INTEGRATION.md` for the full history) is now merged into
`main`. On top of that, the upload page (`/`) got a clear **per-upload
toggle** instead of only a server-wide env flag:

- **📋 Saved responses** (default) — deterministic mocked fixtures, fast,
  reliable for a demo
- **🤖 AI review (TrOCR)** — runs the real model on the actual uploaded
  image, greyed out automatically if the model isn't loaded on this
  server (checked via `GET /api/ocr-status` on page load)

Every result now shows which path produced it (a small "🤖 AI review
(TrOCR)" or "📋 Saved response" badge next to the status pill), and the
document record stores a permanent `source` field so this is visible
later during review too, not just at upload time.

**Backend:** `POST /api/analyze` takes a new `use_ai` form field
(defaults `false`); `ocr_engine.is_model_ready()` checks the model
regardless of the `USE_REAL_OCR` env flag (that flag still exists as a
server-wide default for teammates who want AI-first without touching the
frontend); requesting AI review with no model loaded fails loudly with a
503 instead of silently falling back. New `PRELOAD_TROCR=true` env var
loads the model in a background thread at server startup so the first
"AI review" request isn't stuck on a cold ~30s+ load. 4 new tests
(`test_ai_toggle.py`) — 55/55 backend tests passing.

**Verified live end-to-end**, same running server, same endpoint,
switching only the `use_ai` flag:
```
use_ai=false -> {"source": "saved_response", fields: [...6 mocked fields...]}
use_ai=true  -> {"source": "ai_review", "fields": [{"name": "owner_name", "value": "RAMESH KUMAR", "confidence": 0.55}]}
```
— real image, real model, real inference, correctly gated by the toggle.

## Reject + Admin Blacklist Review

Reviewers now have two additional options beyond Approve on any document's
review page (`/review/[id]`):

- **✗ Reject** — sets `status: "rejected"` with a required, stored reason
  (shown on the document afterward). Use when the AI output or the upload
  itself is clearly wrong and doesn't need escalation.
- **🚩 Flag for admin review** — creates a separate `blacklist_entries`
  record (document stays in its current status, unaffected) for an admin
  to decide independently, without the reviewer having to make the final
  call themselves.

**New admin surface:** `/admin/blacklist` — lists unresolved (or all, via
checkbox) flags with the flagged reason, who flagged it, and when. Admin
can **Reject document** (resolves the flag AND flips the linked document
to `rejected`, with an audit-trail reason referencing the original flag)
or **Dismiss flag** (resolves the flag, document status untouched — for
flags raised in error). Linked from the Gov Employee Portal's header
("🚩 Admin: Blacklist").

**Backend additions** (`backend/db.py`, `backend/main.py`):
- `documents.rejection_reason` column (nullable, set on reject)
- New `blacklist_entries` table: `id`, `document_id`, `reason`,
  `flagged_by`, `created_at`, `resolved`, `resolution`
  (`"dismissed"` | `"document_rejected"`), `resolved_by`, `resolved_at`
- `POST /api/documents/{id}/reject` (`{"reason": "..."}`, reason required)
- `POST /api/documents/{id}/blacklist` (`{"reason": "...", "flagged_by": "..."}`)
- `GET /api/blacklist` (optional `?resolved=true|false` filter)
- `POST /api/blacklist/{id}/resolve` (`{"resolution": "dismissed"|"document_rejected", "resolved_by": "..."}`)
  — resolving as `document_rejected` internally also calls the reject path
- 35/35 backend tests passing (11 new: reject success/validation/404,
  blacklist create/validation/404, list+filter, resolve both paths +
  invalid-value + 404).

**Verified live end-to-end** (real curl against a running server, not
simulated): uploaded a doc → rejected it with a reason → confirmed
`status: "rejected"` + reason persisted. Separately uploaded another doc →
flagged it → confirmed it appeared in the unresolved blacklist list →
resolved it as `document_rejected` → confirmed the linked document's
status flipped to `rejected` automatically with an audit-trail reason.

## Database

Documents now persist in **SQLite** (`backend/land_records.db`, via
SQLAlchemy — `backend/db.py`) instead of an in-memory dict, so **uploaded
records survive a backend restart**. This was the fix for "there's no
pending document" — that was never a bug, it was in-memory state getting
wiped on restart with no seed data.

- One table (`documents`): `document_id`, `filename`, `processed_at`,
  `fields_json`, `overall_confidence`, `review_required`, `status`,
  `boundary_json`. `fields`/`boundary` are stored as JSON text columns —
  deliberately simple for a demo, not a normalized schema.
- `backend/land_records.db` is gitignored (runtime data, not source) —
  everyone who clones this gets a fresh empty DB; upload a few scans after
  first start.
- 15/15 backend tests passing (`backend/test_db.py` + updated
  `test_main.py`, both run against a throwaway SQLite file per test via
  `backend/conftest.py`, never touching the real demo DB).
- **Verified live**: uploaded a low-confidence doc, restarted the uvicorn
  process, called `/api/documents` again — the document was still there
  with the correct status.

## Uploader accounts — "My Documents"

Separate from the Gov Employee Portal, the **person uploading scans** can
now create a real account and come back later to see the status of
everything they've submitted, instead of re-uploading every time.

| Route | Purpose |
|---|---|
| `/account/login` | Sign up or log in (toggle link switches mode) |
| `/account` | "My Documents" — every doc uploaded while signed in, with live status |

**This is real auth, not mocked** (unlike the Gov Employee Portal):
- `POST /api/auth/signup` / `POST /api/auth/login` — passwords are salted +
  SHA-256 hashed and stored in a `users` SQLite table (demo-grade hashing,
  not bcrypt/argon2 — fine for a hackathon demo, not for production).
- Login returns a bearer-style token stored in `localStorage`; every
  `/api/analyze` and `/api/documents?mine=true` call sends it as an
  `X-Auth-Token` header.
- `documents.owner_username` links each upload to its uploader. Uploading
  while **not** signed in still works exactly as before (`owner_username`
  is null) — accounts are opt-in, not required.
- 24/24 backend tests passing (added `test_signup_then_login_roundtrip`,
  duplicate-username rejection, wrong-password rejection, and the
  upload-with-token-then-`mine=true`-filters-correctly path).

**Verified live end-to-end** (real browser session): signed up as a new
user → redirected to `/account` (empty state) → went to `/` (header now
shows "My Documents (username)") → uploaded a scan → went back to
`/account` → the document appeared with its real status and confidence,
without re-uploading anything.

**Bug caught and fixed during this verification:** the CORS middleware was
restricting `allow_methods` to `["POST", "GET"]`, which blocks the browser's
automatic `OPTIONS` preflight request that carries the custom `X-Auth-Token`
header — every authenticated upload failed with "Failed to fetch" until
this was widened to `allow_methods=["*"]`. Also had to delete a stale
`land_records.db` created before the `users` table existed (SQLAlchemy
`create_all` doesn't migrate existing tables) — a stale local
`land_records.db` created before this change will 500 on any auth-related call until deleted.

## Dummy uploads + AI-vs-government-record accuracy check

The `dummy-land.svg` shown on the reviewer's boundary canvas has 4 distinct
plots (labeled A–D, north-west/north-east/south-west/south-east). Each now
has:
- A **pre-made AI extraction result** (`backend/dummy_plot_fixtures.py`) —
  2 plots (A, B) are clean/high-confidence, 2 plots (C, D) have a
  **deliberate AI mistake** (a digit or status misread) with correspondingly
  lower confidence on that field, so there's something real to catch.
- A matching **official government record** (`backend/government_records.py`)
  — the "ground truth" already on file, independent of whatever the AI
  extracted from a scan.

**How to use it:**
1. On `/`, under "Or try a dummy scan", click Plot A/B/C/D — this calls
   `POST /api/documents/dummy-upload` and creates a document exactly like a
   real upload would (same pending/auto-approved logic).
2. In the Gov Employee Portal (`/review/[id]`), if the document came from a
   dummy plot, a **"🏛 AI vs. Official Government Record"** panel appears
   below the extracted fields — a per-field comparison table showing the
   AI's value, the government's on-file value, and a ✓ match / ✗ mismatch
   flag, so the reviewer can actually verify the AI is working correctly
   instead of taking it on faith.

**Verified live**: dummy-uploaded Plot C (has 2 seeded AI errors) — the
comparison table correctly flagged `khasra_no` (AI said `901/D`, government
record says `901/B`) and `area` (AI said `4.60`, government record says
`4.00`) as `✗ mismatch`, with the other 4 fields correctly `✓ match`.
Separately verified Plot B (clean fixture, no seeded errors) — all 6 fields
showed `✓ match`.

**Follow-up: parallel document view + map** — the review page now leads
with two side-by-side cards (📤 what the user uploaded / AI extracted vs 🏛
the official khata record on file with the government), plus a zoomed
cadastral-map view (cropped `<svg><image>` of `dummy-land.svg`, using
per-plot bounding boxes in `frontend/src/lib/plots.ts`) with the relevant
plot outlined in red. The AI-vs-government match table stays below as the
detailed field-by-field breakdown. Documents not linked to a demo plot
(real uploads) gracefully show "No matching official record on file"
instead of the government card/map. Verified live: Plot C parallel view
correctly showed both documents side-by-side with differing khasra_no/area
values, map zoomed to Plot C's bounding box with red outline; a real
(non-plot) upload correctly fell back to the "no matching record" state.

## Structure

```
2026-09-11_SIH/
  backend/       FastAPI mock API (fixtures.py, main.py, db.py, government_records.py, dummy_plot_fixtures.py, tests) — venv included, gitignored
                 SQLite-backed (land_records.db, gitignored — runtime data) via SQLAlchemy
                 /api/analyze, /api/documents(+approve/boundary/dummy-upload), /api/government-records
  frontend/      Next.js + TypeScript + Tailwind app (App Router)
    src/lib/api.ts          typed fetch client (analyze/list/get/approve/boundary/auth)
    src/lib/useAuth.ts      localStorage-backed auth hook for uploader accounts
    src/app/page.tsx        public upload -> loading -> results UI, shows pending status + account header
    src/app/account/login/  uploader signup/login
    src/app/account/        "My Documents" — uploader's own document history
    src/app/UI1..5/home/    5 mockup design directions (iframe of public/mockups/*.html)
    src/app/review/login/   gov employee demo login
    src/app/review/         review queue dashboard
    src/app/review/[id]/    single-doc review: fields + boundary canvas + approve
  mockups/       original 5 static HTML design comparisons (source of truth; copies live in frontend/public/mockups/)
  IDEA.md        Original one-line idea pointer
  README.md      This file
```

## Contract (frontend <-> backend)

`POST http://localhost:8000/api/analyze` (multipart `file=`) → JSON with
`fields[]` (khata_no, khasra_no, survey_no, owner_name, area, mutation),
`overall_confidence`, `review_required` (true if any field confidence < 0.7).
Simulated latency 1.2–2.5s so the UI shows a real loading state.
Full contract details in the plan doc above.

## Running locally

```bash
# backend (port 8067)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8067

# run backend tests
pytest -v

# frontend (port 3067)
cd frontend
npm install
npm run build && npm run start -- -H 0.0.0.0 -p 3067
```

Open `http://localhost:3067`, upload any image file, watch the ~1.2–2.5s
processing state, then see 6 extracted fields with confidence badges.

## What's deliberately NOT built (out of scope for this tier)

- Real OCR/NER — `backend/fixtures.py` hashes the filename to deterministically
  pick one of 3 canned field-sets. Same filename = same result every time.
- Database, auth, GIS/map layer, review-correction workflow.
- The 5 alternate UI mockup directions from the original plan — one clean
  default UI was built directly instead to get to a working demo fastest.

See `.hermes/plans/2026-09-11_land-record-digitization-timeline.md` for what
a real functional-prototype build (real OCR+NER, Postgres+PostGIS, auth,
GIS) would actually take (~27–44 hrs across 1.5–3 weeks, gated on you
supplying real sample scans and picking a target script/language).

## Next steps (your call)

1. Demo this as-is for SIH pitch/round 1 — it's fully functional right now.
2. If you want the 5 UI mockup directions to choose a different visual
   style, say so and I'll generate them.
3. If SIH wants a real pipeline next round, we scope Phase 0 (sample scans +
   target script) from the timeline plan.

# ClaimIQ security and reliability patch notes

This patch addresses the P0/P1 findings from the SRS review. It is a source-code patch, not a claim that staging, production security, performance, or all tests have already passed.

## Changes made

### P0 — Security and business rules

- `app/api/routes/claims.py`
  - Applies row-level claim filtering to Support Agents by region; Adjusters remain limited to assigned claims or their region; Managers/Admins retain cross-region access.
  - Uses the same scoped query for claim detail, updates, status changes, and notes, so an inaccessible claim appears as 404.
  - Validates that claims use active policies within their effective dates and that the claim region matches the policy region.
  - Validates adjuster assignments and region compatibility.
  - Prevents Adjusters from changing claim assignment, claim amount, or region.
  - Requires a non-blank, meaningful justification for a manager/admin override and records the justification in status history.
  - Archives submitted claims instead of physically deleting them; status history and notes remain in the database.
- `app/db/models.py`, `app/schemas/claim.py`
  - Adds `Claim.archived_at`; removes ORM delete-orphan behavior for status history; exposes archive time in the claim response.
  - Rejects null/blank values for required claim update fields and blank notes/AI questions.
- `migrations/versions/0004_claim_archive_and_history_retention.py`
  - Adds the archive column and changes the status-history FK to `RESTRICT` for PostgreSQL migrations.
- `app/api/routes/policies.py`
  - Scopes policy list/detail reads for non-privileged users to their region and GLOBAL policies.
- `docker-compose.yml`, `.env.example`
  - Removes the hardcoded database password from Compose configuration and requires a local `POSTGRES_PASSWORD` value.
  - The deliverable ZIP intentionally excludes `.env` and `.git`.

### P1 — RAG, analytics, and operational safety

- `app/rag/service.py`
  - Validates model citation markers against the source markers actually provided to the model.
  - Fails closed with the no-match response when citations are absent or fabricated.
  - Logs only cited source records; redacts email, phone, long numeric identifiers, Aadhaar-like numbers, and PAN-like identifiers in persisted text.
  - Captures prompt/completion token counts when the LLM SDK provides usage metadata; provider usage may be unavailable and remain null.
  - Configures a maximum generated response length (`RAG_MAX_RESPONSE_TOKENS`, default 512) in the LLM client.
  - Returns a generic provider failure message to clients and records a failure event without returning raw provider exceptions.
- `app/core/redaction.py` centralizes PII redaction for persisted text; manager override justifications and document audit metadata use the redaction policy.
- `app/rag/vector_store.py`, `app/rag/retriever.py`, `app/rag/ingestion.py`
  - Removes debug output containing raw questions and full ChromaDB document contents.
  - Uses structured server logging and avoids exposing raw ingestion exception text in API-visible document status.
- `app/api/routes/documents.py`
  - Validates the PDF signature as well as content type.
  - Commits the inactive document state before vector cleanup. Retrieval checks the database status, so leftover vectors are not retrievable after deactivation.
  - Returns generic indexing/re-indexing failures to clients and logs the document ID internally.
- `app/api/routes/ai.py`
  - Adds a basic per-user AI query rate limit (20 requests per 60 seconds per process).
  - Enforces policy-region access and avoids exposing raw internal exceptions to API clients.
- `app/api/routes/analytics.py`
  - Applies date, region, claim-type and archived-record filters in PostgreSQL before building the Pandas DataFrame.
  - Loads claim history efficiently and counts closed claims' original approved/rejected decision in the approval/rejection metrics.
  - Counts AI queries using a database-side filtered query.
- `migrations/versions/0005_ai_token_usage.py`
  - Adds nullable prompt/completion token count columns to AI query logs.
- `tests/test_claim_visibility.py`, `tests/test_analytics.py`, `tests/test_ai_logging.py`
  - Adds regression tests for region scoping, archive filtering, closed-claim decisions, and identity-number redaction.

## Important deployment notes

1. If the `.env` in the original archive contains real credentials, rotate them. The `.env` file is intentionally not included in this ZIP.
2. Copy `.env.example` to `.env` and set unique local-development secrets before running Compose.
3. Apply migrations before testing: `alembic upgrade head`.
4. The new migrations are intended for the project's PostgreSQL deployment. Back up the database before applying them to an existing environment.
5. The AI rate limiter is process-local and resets on restart. For multiple workers or production, enforce limits at Azure API Management or with a shared Redis-backed limiter.
6. Audit/status history has no application edit endpoint and physical claim deletion is blocked by the migration. Strict tamper-evidence against database administrators would additionally require database permissions and/or cryptographic audit-chain storage.
7. A document's database status is authoritative during retrieval. If vector deletion fails after deactivation, the API reports cleanup failure; rerun cleanup/reindex maintenance, but the inactive document should not be retrieved.

## Verification commands

Run from the `ClaimsIQ` directory after setting up Python 3.11 and installing dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows; use `cp .env.example .env` on macOS/Linux
# Set DATABASE_URL and JWT_SECRET_KEY in .env for your chosen environment
python -m compileall -q app migrations scripts tests
pytest -q
```

For Docker Compose, set `POSTGRES_PASSWORD` in `.env`, then run:

```bash
docker compose up --build
```

Compose runs Alembic migrations before starting FastAPI. Verify `/health` (if enabled by the current health route), `/docs`, and the manual acceptance scenarios below.

## Manual regression scenarios

- A Support Agent in Region A cannot list or retrieve a Region B claim or policy.
- An Adjuster cannot update a claim outside their permitted scope or change assignment, amount, or region.
- A manager override with blank/whitespace justification is rejected; a justified override creates a status-history row.
- Archiving a submitted claim removes it from normal list/detail results but preserves its status history and notes in the database.
- An inactive document cannot supply an answer after deactivation, even if stale vector records remain.
- A generated AI answer with no citation or an unknown `[S99]` citation returns the no-match response; valid markers map only to retrieved source metadata.
- A completed claim contributes to turnaround time and its prior approved/rejected decision is counted in decision-rate metrics.
- Failed login, AI failure, and document-processing errors do not expose credentials, raw provider errors, or raw document contents to API clients/log fields.

## Verification status for this patch artifact

- Python syntax compilation: passed in the packaging environment.
- `pytest -q`: **not executed successfully** because this environment does not have all project dependencies installed (including `langchain_core`, `pwdlib`, and `langchain_text_splitters`). Install `requirements.txt` in a supported Python 3.11 environment and rerun the suite before merging/deploying.
- PostgreSQL migrations, live LLM calls, Docker startup, Azure deployment, concurrency and latency targets: not verified in this environment.

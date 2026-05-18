# Outbound AI Outreach System: End-to-End Flow

This document explains how the system really works in production terms, not just the marketing version.

## What the system does

The application takes a search query or a direct domain, discovers candidate companies, crawls public web pages, extracts decision-maker and company data, enriches email information, validates confidence thresholds, generates personalization, drafts a 3-email sequence, and persists every step in PostgreSQL.

The delivery step is intentionally gated. The pipeline stops at `READY_TO_SEND` and does not send live email.

## Runtime entry points

- Frontend dashboard: `frontend/src/app/(workspace)/dashboard/page.tsx`
- Search API: `POST /api/search` in `backend/main.py`
- Direct-domain API: `POST /api/process-domain` in `backend/main.py`
- Workflow graph: `backend/graph.py`
- State model: `backend/state.py`
- Persistence: `backend/db/models.py`

## Real end-to-end flow

### 1. User starts a run

The frontend submits either:

- a search query to `/api/search`
- a direct domain to `/api/process-domain`

The backend creates a `search_runs` row immediately so the run is durable before work starts.

### 2. Search discovery

`backend/nodes/search.py` expands the query into variants and calls Tavily.

Output:

- candidate company URLs
- normalized domain
- inferred company name when available

Duplicate filtering happens before enqueueing new leads.

### 3. Lead creation and persistence

Each discovered company becomes a `LeadState` object and is saved to PostgreSQL.

Important fields:

- `lead_id`
- `run_id`
- `search_query`
- `company_name`
- `domain`
- `source_url`
- `source_type`
- `status`

This means the system is crash-recoverable from the database, not from memory.

### 4. Crawling

`backend/nodes/crawl.py` uses Crawl4AI to fetch the company site and selected internal pages.

The crawler:

- normalizes the seed URL
- checks robots/sitemaps when available
- crawls a bounded number of pages
- collects markdown text

If crawl fails completely, the lead is marked dead.

### 5. Extraction

`backend/graph.py` now runs a single extraction step that gathers:

- founder data
- services
- signals

That step calls:

- `backend/nodes/extract.py`

Extraction uses:

- LLM structured output when an API key is available
- heuristics fallback for obvious founder patterns

This is the first place where the system can become sparse if the site has little public information.

### 6. LinkedIn lookup

If the founder confidence is high enough, the graph continues to:

- `backend/nodes/linkedin_lookup.py`

This is a conservative lookup. It only keeps person-profile style LinkedIn URLs.

### 7. Email enrichment

`backend/nodes/enrich.py` calls Hunter when configured.

If Hunter cannot find a verified email, the pipeline can fall back to:

- `backend/nodes/enrich.py::pattern_guess_node`

This is a best-effort guess, not verification.

### 8. Validation

`backend/nodes/validate.py` applies confidence and completeness checks.

Current thresholds:

- founder confidence >= 0.75
- email confidence >= 0.70

If the lead does not meet the threshold, it is marked `DEAD_LEAD`.

### 9. Company profile synthesis

`backend/nodes/profile.py` synthesizes a compact company profile from:

- crawled markdown
- founder name and LinkedIn
- services
- signals
- email

This node has a fallback path when OpenAI is unavailable or the model call fails.

That fallback is not fake data, but it can be generic if the source evidence is sparse.

What this means in practice:

- if the crawl/extraction stage found strong evidence, the profile is specific
- if the site has little useful public content, the profile is conservative and generic

### 10. Personalization

`backend/nodes/personalize.py` picks one signal or the synthesized outreach angle.

This becomes the hook for the first email.

### 11. Drafting

`backend/nodes/draft.py` builds a 3-email sequence.

Output:

- Email 1
- Email 2
- Email 3

If the LLM call fails, a deterministic fallback sequence is used.

### 12. Review gate

`backend/nodes/outreach.py` does not send email.

It returns:

- `READY_TO_SEND`

This is deliberate. The system is review-first until a live delivery channel is explicitly enabled.

## Persistence model

PostgreSQL stores:

- runs
- leads
- settings

The workflow updates the database after each meaningful state transition so the system can resume from the last persisted state.

## Failure handling

The system currently handles failures by:

- retrying the workflow a bounded number of times
- marking the lead `RETRY_PENDING`
- falling back to `DEAD_LEAD` when retries are exhausted

Known caveat:

- fallback paths are conservative, not magical
- no external API means no external intelligence

## What is real versus fallback

Real:

- Tavily search
- Crawl4AI crawling
- PostgreSQL persistence
- Hunter enrichment when configured
- OpenAI extraction/personalization/drafting when configured

Fallback:

- heuristics founder detection
- guessed email patterns
- generic company profile synthesis
- deterministic draft sequences

## Questions a senior developer will likely ask

### How does a query turn into a lead?

The frontend posts a query or domain, the backend creates a run, search discovers URLs, each domain becomes a `LeadState`, and the graph processes each lead independently.

### How do you avoid duplicates?

At enqueue time the backend normalizes the domain and checks PostgreSQL for an existing lead. The leads table also has a unique index on domain.

### What happens on crash or restart?

Because every lead and run transition is persisted, the system resumes from the last known database state instead of a volatile in-memory queue.

### What happens if OpenAI is unavailable?

The extraction/profile/drafting stages fall back to heuristics or deterministic text so the system still completes, but with reduced quality.

### Why does profile output sometimes look generic?

Because the site evidence is sparse or the LLM path is unavailable. The profile node intentionally refuses to invent rich company facts from thin evidence.

### Why does the pipeline stop before sending?

The product is intentionally review-first. It is designed to produce human-reviewable drafts, not autonomous outreach.

### What are the main external dependencies?

- Tavily
- Crawl4AI
- Hunter
- OpenAI
- PostgreSQL

### Where do configuration values live?

Environment variables and database-backed settings. The draft prompt and search tuning values are stored in PostgreSQL.

## Operational commands

- Backend compile check: `python -m compileall backend`
- Backend tests: `python -m unittest backend.tests.test_pipeline`
- Frontend lint: `npm run lint`
- Frontend build: `npm run build`

## Current working state

The local codebase currently passes:

- backend compile
- backend tests
- frontend lint
- frontend build

Live smoke tests verified:

- health endpoint
- settings endpoint
- summary endpoint
- run creation
- run polling to terminal state
- run deletion for completed runs
- frontend route rendering


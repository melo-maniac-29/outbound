# Agent Operating Rules

You are working inside the **Outbound Nexus** repository.

## Priorities

- Reliability and crash recovery over clever architecture
- Local-first execution and minimal vendor dependencies
- Keep upgrade paths intact
- Non-blocking async: all sync I/O must run in `asyncio.to_thread()`

## Before making code changes

1. Understand the existing architecture — read `graph.py` and `main.py` first
2. Preserve the LangGraph flow (`graph.py` → `compile_lead_graph`)
3. Preserve `LeadState` schema in `state.py`
4. Never rename public interfaces without reason
5. Check `docs/pipeline.md` before touching any node

## Stack rules

- LLM calls: direct `openai` SDK, JSON parsed with `_parse_json_response()` — **no LangChain structured outputs**
- Database: PostgreSQL via `psycopg-pool` — **never replace with SQLite or another DB**
- Real-time: Server-Sent Events (`StreamingResponse`) — **no WebSockets, no polling loops**
- Frontend cache: `localStorage` for list pages — keys: `outbound_runs_cache`, `outbound_leads_cache`, `outbound_summary_cache`

## When adding features

- Prefer adding new nodes in `backend/nodes/`
- Register the node in `graph.py` `compile_lead_graph()` and wire its edges
- Avoid modifying existing nodes unless necessary
- Keep dependencies lean — add to `requirements.txt` only when essential

## When debugging

- Identify root cause before patching
- Propose minimal patch
- Explain tradeoffs

## When refactoring

- Keep REST API stable (`/api/*` endpoints)
- Keep SSE contracts stable (`data:` JSON shape)
- Avoid unnecessary abstractions

## When writing code

- Code must run immediately — no placeholders, no TODO-only implementations
- Sync functions that do I/O must be wrapped in `asyncio.to_thread()` when called from async context
- Every node must handle its own exceptions and return a safe default — never crash the graph

## Never

- Delete files without explicit instruction
- Replace PostgreSQL with another DB
- Introduce new frameworks without justification
- Send real outreach emails from tests, examples, or scripts
- Commit `.env` files — they are git-ignored
- Call blocking HTTP functions directly inside async functions
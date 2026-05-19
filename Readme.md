# Outbound Nexus

Automated lead discovery and personalized email drafting pipeline. Finds companies, crawls their websites, extracts founders, verifies emails, builds company profiles, and writes 3-email outreach sequences — all without human input until the draft is ready for review.

**Nothing sends automatically.** Every lead stops at `READY_TO_SEND` for human approval before any email goes out.

---

## How it works

1. Enter a search query (`"boutique B2B email marketing agencies"`) or paste a direct domain
2. Tavily discovers matching company websites
3. Pipeline crawls each site, extracts founder data, finds/guesses email addresses, builds a profile, writes 3 emails
4. Dashboard shows real-time progress via Server-Sent Events — no refresh needed
5. Open any lead, review signals and email drafts, then decide to send

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| Search / discovery | Tavily | Built for agents, returns clean URLs with context |
| Website crawling | Crawl4AI + Playwright | Local, JS rendering, anti-bot, no API key or cost |
| LLM | OpenAI-compatible API | Direct JSON parsing, no LangChain structured output fragility |
| Email lookup | Hunter.io | Domain → verified email + confidence score |
| Workflow | LangGraph | Typed state machine with conditional branching |
| Database | PostgreSQL + psycopg-pool | Relational, crash recovery, connection pooling |
| Backend API | FastAPI | Async, SSE streaming, background tasks |
| Frontend | Next.js 15 | App Router, client-side localStorage cache |
| Real-time | Server-Sent Events | Push-only, no WebSocket overhead, auto-reconnect |
| Deployment | Docker Compose | Single command, isolated services |

---

## Pipeline — node by node

```
START
  ↓
crawl_node              Playwright crawls ≤8 pages → single markdown blob
  ↓
extract_all_node        3 parallel GPT calls: founder + services + signals
  ↓
merge_extractions       Writes extracted data into LeadState
  ↓
◆ founder_confidence ≥ 0.75?
  ├─ NO  → dead_lead_node → END
  └─ YES → linkedin_lookup_node   Tavily → founder LinkedIn /in/ URL
               ↓
            enrich_node           Hunter.io email (skipped if site email ≥ 0.80)
               ↓
            build_profile_node    GPT → summary, positioning, outreach_angle
               ↓
            ◆ email_confidence ≥ 0.70?
               ├─ NO  → pattern_guess_node   first.last@domain (conf 0.72)
               └─ YES ↓
                    validate_node    Final gate: founder ≥ 0.75 AND email ≥ 0.70
                       ↓
                    ◆ status == VALIDATED?
                       ├─ NO  → END (dead lead)
                       └─ YES → personalize_node   Picks best signal as hook
                                    ↓
                                 draft_node         GPT writes 3-email sequence
                                    ↓
                                 outreach_node      Sets READY_TO_SEND
                                    ↓
                                   END
```

For full node-by-node breakdown see [`docs/pipeline.md`](docs/pipeline.md).

---

## Multi-wave search

A single run targets N ready leads. The orchestrator runs in waves:

- Wave 1: search → crawl all discovered URLs in parallel → count how many hit `READY_TO_SEND`
- If target not reached → search with a new query variant → repeat
- Stops when: target hit (`COMPLETED`), search stalls 3 waves in a row (`EXHAUSTED`), or user clicks Stop

---

## Lead status flow

```
SEARCHED → CRAWLED → EXTRACTED → ENRICHED → VALIDATED → PERSONALIZED → READY_TO_SEND
                                                                        ↘
                                                                      DEAD_LEAD (any gate)
                                                                      RETRY_PENDING (on error)
```

---

## Project structure

```
outbound/
├── AGENTS.md                   Agent operating rules
├── docker-compose.yml
├── backend/
│   ├── main.py                 FastAPI app — REST + SSE endpoints + orchestration
│   ├── graph.py                LangGraph state machine (nodes + edges)
│   ├── state.py                LeadState schema + LeadStatus enum
│   ├── requirements.txt
│   ├── .env.example
│   ├── db/
│   │   └── models.py           PostgreSQL connection pool + all DB functions
│   └── nodes/
│       ├── search.py           Tavily discovery + URL filtering
│       ├── crawl.py            Playwright multi-page crawler → markdown
│       ├── extract.py          GPT extraction (founder, services, signals, emails)
│       ├── linkedin_lookup.py  Tavily → LinkedIn /in/ URL
│       ├── enrich.py           Hunter.io email lookup + pattern guesser
│       ├── profile.py          GPT company profile synthesis
│       ├── validate.py         Confidence gate
│       ├── personalize.py      Signal picker
│       ├── draft.py            GPT 3-email sequence writer
│       └── outreach.py         Terminal step → READY_TO_SEND
├── frontend/
│   └── src/app/
│       ├── (workspace)/
│       │   ├── dashboard/      Run launcher + SSE live stats
│       │   ├── runs/           Run history (SSE auto-refresh + localStorage cache)
│       │   ├── runs/[runId]/   Run detail with live SSE lead tracking
│       │   ├── leads/          Lead directory (SSE auto-refresh + localStorage cache)
│       │   ├── leads/[leadId]/ Lead detail — signals, profile, email drafts, copy
│       │   └── settings/       System prompt + search config
│       └── page.tsx            Landing page
├── docs/
│   ├── pipeline.md             Full pipeline explanation
│   └── pipeline.excalidraw.json  Visual diagram (generate with scripts/gen_diagram.py)
└── scripts/
    ├── e2e_search_run.py       End-to-end smoke test
    └── gen_diagram.py          Generates pipeline.excalidraw.json
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/search` | Start a search run (`query`, `max_companies`) |
| `POST` | `/api/process-domain` | Start a single-domain run |
| `GET` | `/api/runs` | List all runs (paginated) |
| `GET` | `/api/runs/{id}` | Run detail with all leads |
| `POST` | `/api/runs/{id}/stop` | Request run stop |
| `DELETE` | `/api/runs/{id}` | Delete run and its leads |
| `GET` | `/api/runs/{id}/stream` | **SSE** — live run + leads updates |
| `GET` | `/api/leads` | List all leads (paginated) |
| `GET` | `/api/leads/{id}` | Lead detail |
| `DELETE` | `/api/leads/{id}` | Delete a terminal lead |
| `GET` | `/api/summary` | Dashboard stats |
| `GET` | `/api/stream/summary` | **SSE** — live dashboard stats + recent runs |
| `GET` | `/api/settings` | Get system settings |
| `PUT` | `/api/settings` | Update system prompt / search config |

---

## Real-time updates (SSE)

The frontend uses `EventSource` — a persistent HTTP connection that receives pushed JSON when anything changes. No polling, no WebSockets.

- **Dashboard** → `/api/stream/summary` → auto-updates stats and recent runs
- **Run detail** → `/api/runs/{id}/stream` → auto-updates lead statuses as pipeline runs
- **Runs list** → subscribes to `/api/stream/summary`, re-fetches full list on any change
- **Leads list** → same as runs list

All list pages cache their last data in `localStorage` — navigating back shows instant data before the next fetch completes.

---

## Setup

### Prerequisites

- Docker + Docker Compose
- A local OpenAI-compatible proxy or OpenAI API key
- Tavily API key (free tier: [tavily.com](https://tavily.com))

### 1. Clone and configure

```bash
git clone https://github.com/melo-maniac-29/outbound.git
cd outbound
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```env
TAVILY_API_KEY=tvly-...
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=http://host.docker.internal:5005/v1   # if using local proxy
OPENAI_MODEL_NAME=gpt-4
HUNTER_API_KEY=                                        # optional, leave blank to skip
DATABASE_URL=postgresql://outbound:outbound@postgres:5432/outbound
```

### 2. Start

```bash
docker compose up -d
```

Backend: `http://localhost:8000`  
Frontend: `http://localhost:3000` (run separately, see below)

### 3. Run frontend locally

```bash
cd frontend
npm install
npm run dev
```

### 4. Smoke test

```bash
python scripts/e2e_search_run.py --query "B2B SaaS email marketing agency" --max 3
```

---

## Design principles

- **Reliability over cleverness** — direct OpenAI JSON parsing, no LangChain structured outputs
- **Local-first** — Crawl4AI runs locally, no cloud crawl API
- **Non-blocking** — all sync I/O runs in `asyncio.to_thread()` so FastAPI stays responsive
- **Human review gate** — nothing sends until a human approves
- **Minimal deps** — no Redis, no Celery, no message queue; PostgreSQL + asyncio is enough

---

## Upgrade path

All upgrades are isolated to one node or config:

| Current | Upgrade to | Change |
|---|---|---|
| Tavily | SearXNG (self-hosted) | `nodes/search.py` only |
| Hunter.io | Apollo.io / Clearbit | `nodes/enrich.py` only |
| `READY_TO_SEND` gate | Gmail SMTP / SendGrid | `nodes/outreach.py` only |
| Console logs | LangSmith | `graph.py` lifespan only |
| Single server | Multi-worker | Add Redis for SSE fan-out |

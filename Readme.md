# Outbound AI Outreach System
**Architecture & Technical Documentation**  
Assessment Submission · Allen Bobby

---

# 1. Overview

This system takes Google-style search strings as input and produces personalized 3-email outreach sequences for qualified leads.

The system performs:

- Agency discovery
- Website crawling
- Founder / decision-maker extraction
- Email enrichment
- Lead validation
- Personalized outreach generation
- Scheduled follow-ups
- State persistence with crash recovery

Every lead maintains a persisted state throughout its lifecycle.

---

# 2. Design Philosophy

This system intentionally prioritizes:

- Reliability over visual complexity
- Local-first execution where possible
- Minimal vendor dependency
- Explicit upgrade paths
- Production-inspired fault tolerance

Every tool is chosen for a specific engineering reason.

No tool exists purely for "stack impressiveness."

---

# 3. Final Stack

| Tool | Purpose | Why | Cost |
|---|---|---|---|
| Tavily | Search / discovery | Native LangGraph integration, built for agents | Free tier |
| Crawl4AI | Website crawling | Local, anti-bot, crash recovery, no API key | Free |
| ScrapeGraphAI | Structured extraction | Prompt-based extraction using existing OpenAI key | OpenAI usage |
| Hunter.io | Email enrichment | Domain → verified email + confidence | Free tier |
| OpenAI GPT-4o | Personalization + drafting | Structured reasoning + JSON outputs | Existing key |
| LangGraph | Workflow orchestration | Stateful graphs, branching, checkpointing | Free |
| SQLite | State persistence | Lightweight relational storage | Free |
| Gmail SMTP | Email delivery | Zero setup overhead for demo | Free |

---

# 4. Architecture

The system is implemented as a directed state graph using LangGraph.

Each node is:

- Pure
- Async
- Independently testable
- Writes only to shared LeadState

---

# 5. LeadState Schema

```python
class LeadState(BaseModel):
    lead_id: str

    search_query: str
    company_name: str | None
    domain: str | None

    founder_name: str | None
    founder_linkedin: str | None
    founder_confidence: float = 0.0

    email: str | None
    email_confidence: float = 0.0

    services: list[str] = []
    signals: list[str] = []

    source_url: str | None
    source_type: str | None
    extraction_timestamp: datetime | None

    email_sequence: list[str] = []

    retry_count: int = 0

    status: LeadStatus
```

---

# 6. LangGraph Node Architecture

## search_node

Tool: Tavily

Input:

- search strings

Output:

- company URLs

Example:

"email marketing agency founder linkedin"

Responsibilities:

- Search discovery
- URL normalization
- Duplicate filtering

---

## crawl_node

Tool: Crawl4AI

Input:

- company URL

Output:

- clean markdown

Responsibilities:

- Page fetching
- JS rendering
- Anti-bot handling
- Resume on crash

---

## extract_node

Tool: ScrapeGraphAI

Input:

- crawled markdown

Prompt:

"Extract founder name, linkedin, services, recent signals"

Output:

Structured JSON:

```json
{
  "founder_name": "John Doe",
  "linkedin": "...",
  "services": [],
  "signals": [],
  "confidence": 0.84
}
```

Responsibilities:

- Founder extraction
- Signal extraction
- Confidence scoring
- Provenance capture

---

## enrich_node

Tool: Hunter.io

Input:

- domain

Output:

- verified emails
- confidence scores

Responsibilities:

- Email enrichment
- Pattern detection

---

## pattern_guess_node

Tool: Pure Python

Runs only when Hunter confidence is insufficient.

Patterns:

- firstname@
- firstname.lastname@
- firstinitiallastname@

---

## validate_node

Tool: Pure Python

Responsibilities:

- Deduplication
- Confidence threshold filtering
- Completeness checks

Thresholds:

Founder:

>= 0.75

Email:

>= 0.70

---

## personalize_node

Tool: GPT-4o

Responsibilities:

Select one relevant signal:

Examples:

- Recent hiring
- New case study
- Client announcement
- Service expansion

Returns:

One personalization hook.

---

## draft_node

Tool: GPT-4o

Responsibilities:

Generate:

- Email 1
- Email 2
- Email 3

Constraints:

- Under 100 words
- No generic openings
- Peer-to-peer tone
- Specific signal in first email

---

## outreach_node

Tool: Gmail SMTP

Responsibilities:

- Send Email 1
- Schedule follow-ups

Schedule:

Day 0

Day 3

Day 10

---

# 7. Parallel Extraction

To reduce latency, extraction tasks run in parallel.

```text
crawl_node
    ↓
extract_node
    ↓
 ┌──────────────┬──────────────┬──────────────┐
 ↓              ↓              ↓
 founder        services       signals
 ↓              ↓              ↓
 └──────────────merge──────────┘
```

LangGraph merges outputs into LeadState.

---

# 8. Conditional Edges

```text
extract_node
    ↓
founder_confidence >= 0.75 ?

YES → enrich_node
NO  → DEAD_LEAD


enrich_node
    ↓
email_confidence >= 0.70 ?

YES → validate_node
NO  → pattern_guess_node


validate_node
    ↓
complete data ?

YES → personalize_node
NO  → DEAD_LEAD
```

---

# 9. Lead State Machine

Every lead state is persisted.

Crash recovery resumes from last checkpoint.

```text
NEW
↓
SEARCHED
↓
CRAWLED
↓
EXTRACTED
↓
ENRICHED
↓
VALIDATED
↓
PERSONALIZED
↓
READY_TO_SEND
↓
SENT
↓
FOLLOWUP_1
↓
FOLLOWUP_2
↓
RESPONDED

OR

DEAD_LEAD

OR

RETRY_PENDING
```

---

# 10. Retry Strategy

External APIs may rate limit.

Retry policy:

- Exponential backoff
- Max retries: 3

Backoff:

1 sec

2 sec

4 sec

On failure:

Lead enters:

RETRY_PENDING

After retry exhaustion:

DEAD_LEAD

---

# 11. Observability

Each node emits structured logs.

Example:

```json
{
  "lead_id": "...",
  "node": "extract_node",
  "latency_ms": 842,
  "status": "success"
}
```

Every lead has:

- correlation ID
- timestamps
- retry counters

Production upgrade:

LangSmith can be added without graph redesign.

---

# 12. Email Sequence

## Email 1 — Day 0

Subject:

Based on extracted signal.

Template:

Hi {first_name},

Came across {company} and noticed {signal}.

I'm building {product} and think it could create real value for your clients.

Worth a 10-minute conversation this week?

{sender}

---

## Email 2 — Day 3

Subject:

Re: original subject

Template:

Hi {first_name},

Wanted to follow up with something specific:

{new insight}

Happy to share more if useful.

{sender}

---

## Email 3 — Day 10

Subject:

Closing the loop

Template:

Hi {first_name},

Just closing the loop.

Still think there's a strong fit around {specific angle}.

Open to a quick chat?

{sender}

---

# 13. Project Structure

```text
outbound_agent/
├── main.py
├── graph.py
├── state.py
├── nodes/
│   ├── search.py
│   ├── crawl.py
│   ├── extract.py
│   ├── enrich.py
│   ├── validate.py
│   ├── personalize.py
│   ├── draft.py
│   ├── outreach.py
├── db/
│   ├── models.py
├── prompts/
│   ├── email_system.txt
└── requirements.txt
```

---

# 14. Intentional Exclusions

## CrewAI

Reason:

Role-based agent conversations are unnecessary.

This is a workflow graph.

---

## Vector Database

Reason:

Data is relational.

No semantic retrieval needed.

---

## LangSmith

Reason:

Observability is useful but not essential for demo scope.

Can be added later.

---

## Firecrawl

Reason:

Cloud pricing and vendor dependency.

Crawl4AI provides equivalent outputs locally.

---

## SearXNG

Reason:

Better for production.

Docker setup adds demo overhead.

---

# 15. Upgrade Path

The architecture supports zero-redesign upgrades.

Examples:

SQLite → PostgreSQL

Tavily → SearXNG

Gmail SMTP → SendGrid

Structured logs → LangSmith

All upgrades require changes in a single node or config file.

---

# 16. Final Design Principle

This system is intentionally designed as:

"Simple enough to demo. Strong enough to scale."
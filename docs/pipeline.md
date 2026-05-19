# Outbound Nexus — Full Pipeline Breakdown

## What Is LangGraph and Why We Use It

LangGraph is a state machine framework built on top of LangChain. It lets you define a **graph of nodes** where each node is a Python function, and **edges** define the flow between them. It handles state passing, async execution, and conditional branching.

**Why not just write sequential Python?**  
Because leads can fail at any step. A state machine makes it explicit — each node reads from a typed state, updates it, and the graph decides what runs next based on the result. Crash recovery, retries, and routing are all built into the graph structure rather than scattered across try/except blocks.

---

## The State Object — `LeadState`

Every lead flowing through the pipeline is a single `LeadState` Pydantic model. Every node reads from it and writes back to it. It gets persisted to PostgreSQL after each node completes.

```python
class LeadState:
    lead_id: str            # UUID, unique per lead
    run_id: str             # which batch this came from
    domain: str             # e.g. "klientboost.com"
    company_name: str       # extracted or from search
    founder_name: str       # extracted by LLM
    founder_linkedin: str   # found by Tavily search
    founder_confidence: float   # 0.0 – 1.0
    email: str              # found on site or guessed
    email_confidence: float # 0.0 – 1.0
    services: list[str]     # extracted by LLM
    signals: list[str]      # extracted by LLM
    company_profile: dict   # built by GPT
    email_sequence: list[str]   # 3 drafted emails
    status: LeadStatus      # current pipeline stage
    retry_count: int        # how many times retried
```

**LeadStatus** values (in order):  
`SEARCHED → CRAWLED → EXTRACTED → ENRICHED → VALIDATED → PERSONALIZED → READY_TO_SEND`  
or `DEAD_LEAD` at any point if a gate fails.

---

## The Graph — Node by Node

### `START → crawl_node`

**What it does:** Uses Playwright (headless browser) + Crawl4AI to:
1. Fetch the homepage as rendered HTML
2. Find internal links (from sitemap.xml, robots.txt, and inline `<a>` tags)
3. Score and prioritize pages: `/about`, `/team`, `/services`, `/contact`, `/founders` rank highest
4. Fetch up to 8 pages in parallel
5. Concatenate all page content into one large markdown string (~20k chars)

**Why markdown?** LLMs work best on clean text. Converting HTML → markdown strips nav, ads, scripts, and keeps headings, paragraphs, and lists which are where the useful data lives.

**On failure:** Sets `status = DEAD_LEAD`, short-circuits to END. This catches parked domains, 404s, login walls.

**State after:** `lead.markdown` populated, `lead.status = CRAWLED`

---

### `crawl_node → extract_all_node`

**What it does:** Runs **3 GPT calls in parallel** using `asyncio.gather()`:

#### 1. `extract_founder_node`
- First tries a regex heuristic — searches the markdown for patterns like `"Jason B.\nFounder & CEO"` 
- If heuristic finds nothing, sends the full markdown to GPT with prompt: *"Find the most senior decision-maker. Return JSON: {founder_name, linkedin, confidence}"*
- Returns confidence 0.9 if found by heuristic, LLM sets its own 0.0–1.0

#### 2. `extract_services_node`
- Sends markdown to GPT: *"List every distinct service offering. Look for headings, nav items, bullet lists, pricing pages. Return JSON: {services: [...]}"*
- Strips markdown code fences from response, parses JSON manually (proxy resilience)
- Example output: `["Email Marketing", "SMS Marketing", "CRO", "B2B Sales Engine Setup"]`

#### 3. `extract_signals_node`
- Sends markdown to GPT: *"Find 5–10 specific credibility signals — real numbers, named clients, awards, certifications. Return JSON: {signals: [...]}"*
- Example output: `["$400M+ revenue generated", "Top Agency Partner by Instantly.ai", "4.9 on Clutch", "Worked with Caraway, Glossier, Allbirds"]`

Also runs inline (no GPT, pure regex): `extract_emails_from_content` — finds any `@domain.com` emails directly in the markdown.

**State after:** `ext_founder`, `ext_services`, `ext_signals`, `ext_emails` all populated in graph state

---

### `extract_all_node → merge_extractions`

**What it does:** Pure Python — takes the 4 extracted payloads and writes them onto the `LeadState` object:
- `lead.founder_name`, `lead.founder_linkedin`, `lead.founder_confidence`
- `lead.services`, `lead.signals`
- `lead.email`, `lead.email_confidence` (if found directly on site)
- `lead.status = EXTRACTED`

Saves to DB.

---

### `merge_extractions → ◆ check_founder_confidence`

**Decision gate:** `lead.founder_confidence >= 0.75?`

- **YES → `linkedin_lookup_node`** (continues)
- **NO → `dead_lead_node`** → END

**Why 0.75?** Below that threshold, the LLM wasn't confident enough that the person is actually a decision-maker. Emailing a random employee wastes the outreach slot.

---

### `linkedin_lookup_node`

**What it does:** If we don't already have a LinkedIn URL from the crawl, uses Tavily to search:  
`"[Founder Name] [Company Name] [Domain] LinkedIn"`  
Filters results to only `linkedin.com/in/` URLs (personal profiles, not company pages), and only if the founder's first name appears in the title/content.

**Why Tavily not the LinkedIn API?** LinkedIn's API requires approval. Tavily's search gives enough signal to confirm and link to the profile.

**State after:** `lead.founder_linkedin` set if found

---

### `linkedin_lookup_node → enrich_node`

**What it does:** Calls Hunter.io API with the domain.  
- If we already found a high-confidence email directly on the site (`email_confidence >= 0.80`), this step is **skipped entirely** (guard in code)
- Otherwise Hunter.io returns emails found on that domain with confidence scores
- If Hunter finds something better than what we have, it replaces it

**Fallback:** If no Hunter API key is set (or response is empty), returns `{email: None, confidence: 0.0}` — never crashes the pipeline.

---

### `enrich_node → build_profile_node`

**What it does:** GPT synthesizes everything into a structured company profile:

```json
{
  "summary": "KlientBoost is a performance marketing agency...",
  "positioning": "Award-winning, results-driven...",
  "audience": "B2B SaaS startups, IT firms, consulting companies",
  "key_services": ["Paid Advertising", "SEO", "CRO", ...],
  "credibility_signals": ["88% goal achievement rate Q1 2026", ...],
  "outreach_angle": "Reference their 88% goal rate and offer..."
}
```

The `outreach_angle` is the most critical output — it's the single most relevant hook that makes the email feel researched, not templated.

Prompt includes: company name, domain, founder, extracted services, signals, and first 18,000 chars of site markdown.

**State after:** `lead.company_profile` set

---

### `build_profile_node → ◆ check_email_confidence`

**Decision gate:** `lead.email_confidence >= 0.70?`

- **YES → `validate_node`** (we have a usable email)
- **NO → `pattern_guess_node`** (try to construct one)

---

### `pattern_guess_node`

**What it does:** Uses the founder name + domain to guess the most likely email format:
- `first.last@domain.com` (most common, confidence 0.72)
- Single name only: `firstname@domain.com` (confidence 0.55)

Then flows into `validate_node`.

---

### `validate_node`

**What it does:** Final gate before drafting. Checks:
- `founder_confidence >= 0.75` AND
- `email_confidence >= 0.70` AND
- `founder_name` is not None AND
- `email` is not None

If all pass: `status = VALIDATED`  
Otherwise: `status = DEAD_LEAD`

---

### `validate_node → ◆ check_validation`

**Decision gate:** `lead.status == VALIDATED?`

- **YES → `personalize_node`**
- **NO → END** (dead lead, don't draft)

---

### `personalize_node`

**What it does:** Picks the single best signal to use as the email hook. Priority order:
1. A signal containing a specific number (`$`, `%`, `+`, numeric)
2. A signal mentioning a named client or award
3. First signal from the list
4. Falls back to the outreach angle from the company profile

Filters out generic filler strings like "noticed your recent growth".

**State after:** `personalization_hook` — a single string, e.g.:  
`"Generated $100k LTV for Rio ESG and $68k for IT Now"`

---

### `draft_node`

**What it does:** Sends everything to GPT to write 3 cold emails:

- **Email 1 (Day 0):** Opens with the specific signal/hook. One-paragraph, direct ask.
- **Email 2 (Day 3):** New angle — focuses on a different aspect (integration, time-saving, process fit)
- **Email 3 (Day 10):** Short close — references company name, one sentence value prop, asks for 15-min call

Prompt enforces: 60–100 words per email, peer-to-peer tone, specific CTA, no generic praise, founder's first name as salutation.

`max_tokens=1200` to ensure all 3 emails fit without truncation.

**State after:** `lead.email_sequence = [email1, email2, email3]`

---

### `outreach_node`

**What it does:** Terminal step. Checks that email and sequence exist, then:
- Sets `lead.status = READY_TO_SEND`

**Nothing is sent.** This is the human review gate. The system stops here and waits.

---

## The Full Graph as Code

```
START
  ↓
crawl_node              [Playwright, up to 8 pages → markdown]
  ↓
extract_all_node        [3 parallel GPT calls: founder + services + signals]
  ↓
merge_extractions       [Write extracted data to LeadState]
  ↓
◆ founder_confidence ≥ 0.75?
  ├─ NO  → dead_lead_node → END
  └─ YES → linkedin_lookup_node   [Tavily → LinkedIn profile URL]
              ↓
           enrich_node             [Hunter.io email lookup]
              ↓
           build_profile_node      [GPT → summary, positioning, outreach angle]
              ↓
           ◆ email_confidence ≥ 0.70?
              ├─ NO  → pattern_guess_node  [first.last@domain.com guess]
              │           ↓
              └─ YES → validate_node       [Final confidence gate]
                           ↓
                        ◆ status == VALIDATED?
                           ├─ NO  → END (dead lead)
                           └─ YES → personalize_node   [Pick best signal as hook]
                                       ↓
                                    draft_node          [GPT writes 3-email sequence]
                                       ↓
                                    outreach_node       [Sets READY_TO_SEND]
                                       ↓
                                      END
```

---

## Multi-Wave Search (Outside the Graph)

The graph processes **one lead**. The orchestrator in `main.py → process_lead()` runs many leads to fill a target count.

```
User sets target = 5 ready leads

Wave 1: Tavily search → 5 URLs discovered
        → Run graph on all 5 in parallel (asyncio.gather)
        → 3 become READY_TO_SEND, 2 become DEAD_LEAD

Wave 2: Still need 2 more. New Tavily query variant → 3 new URLs
        → 1 becomes READY_TO_SEND, 2 become DEAD_LEAD

Wave 3: Still need 1 more. Another query variant → 2 new URLs
        → 1 becomes READY_TO_SEND

Done. Target hit. Run status → COMPLETED
```

Stops early if:
- Target reached → `COMPLETED`
- 3 consecutive waves find nothing new → `EXHAUSTED` (search stalled)
- Max lead attempts hit (350) → `EXHAUSTED`
- User clicks Stop → `STOPPED`

---

## Real-Time Updates — SSE

While the graph runs in a background task, the frontend subscribes to:

- `GET /api/runs/{id}/stream` — pushes full run+leads JSON every time DB state changes
- `GET /api/stream/summary` — pushes dashboard stats every time they change

Backend checks DB every 3s, diffs against last sent payload, only pushes if something changed. No polling from the browser — one persistent HTTP connection per open page.

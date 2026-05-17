import uuid
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI(title="Outbound AI Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    from db.models import init_db

    init_db()


class SearchRequest(BaseModel):
    query: str
    max_companies: int = Field(default=5, ge=1, le=25)


class DomainRequest(BaseModel):
    domain: str
    label: str | None = None


class SettingsRequest(BaseModel):
    draft_system_prompt: str
    search_dedupe_across_db: str | None = None
    search_bucket_rounds: str | None = None
    search_variant_limit: str | None = None


async def process_lead(query: str, max_companies: int, run_id: str):
    from db.models import finalize_run, fetch_run, find_existing_lead, get_bool_setting, get_int_setting
    from graph import compile_lead_graph
    from nodes.search import search_node

    try:
        workflow = compile_lead_graph()
        dedupe_across_db = get_bool_setting("search_dedupe_across_db", True)
        bucket_rounds = max(1, get_int_setting("search_bucket_rounds", 6))
        variant_limit = max(1, get_int_setting("search_variant_limit", 4))
        search_target = min(max(max_companies * 4, 10), 25)
        seen_domains: set[str] = set()
        good_count = 0
        bucket_queries = build_bucket_queries(query, bucket_rounds)

        for bucket_query in bucket_queries:
            run_snapshot = fetch_run(run_id)
            if not run_snapshot or run_snapshot.get("stop_requested") or run_snapshot.get("status") == "STOPPED":
                finalize_run(run_id, "STOPPED", "Run stopped by user.")
                return
            if good_count >= max_companies:
                break

            remaining = max_companies - good_count
            results = search_node(
                bucket_query,
                max_companies=min(max(remaining * 4, 10), search_target),
                max_attempts=variant_limit,
                exclude_domains=seen_domains,
            )
            discovered = results.get("discovered_urls", [])
            if not discovered:
                continue

            import asyncio
            tasks = []
            for target in discovered:
                domain = target["domain"]
                if domain in seen_domains:
                    continue
                
                # Check DB in a thread
                existing = await asyncio.to_thread(find_existing_lead, domain)
                if dedupe_across_db and existing:
                    seen_domains.add(domain)
                    continue
                seen_domains.add(domain)
                
                def _enqueue():
                    return enqueue_lead(
                        workflow=workflow,
                        run_id=run_id,
                        search_query=query,
                        company_name=target.get("company_name"),
                        domain=domain,
                        source_url=target["source_url"],
                        source_type="tavily_search",
                    )
                lead_payload = await asyncio.to_thread(_enqueue)
                if not lead_payload:
                    continue
                    
                tasks.append(run_workflow_for_lead(workflow, lead_payload))
                
            if tasks:
                completed_leads = await asyncio.gather(*tasks, return_exceptions=True)
                for completed_lead in completed_leads:
                    if isinstance(completed_lead, Exception):
                        continue
                    item_status = getattr(completed_lead.status, "value", completed_lead.status)
                    if item_status == "READY_TO_SEND":
                        good_count += 1
                        
            run_snapshot = await asyncio.to_thread(fetch_run, run_id)
            if not run_snapshot or run_snapshot.get("stop_requested") or run_snapshot.get("status") == "STOPPED":
                await asyncio.to_thread(finalize_run, run_id, "STOPPED", "Run stopped by user.")
                return

        await asyncio.to_thread(finalize_run, run_id, "COMPLETED" if good_count >= max_companies else "EXHAUSTED")
    except Exception as exc:
        await asyncio.to_thread(finalize_run, run_id, "FAILED", str(exc))
        print(f"Run {run_id} failed: {exc}")


async def process_domain(domain: str, label: str | None, run_id: str):
    from db.models import finalize_run
    from graph import compile_lead_graph
    import asyncio

    try:
        workflow = compile_lead_graph()
        normalized = normalize_domain(domain)
        def _enqueue():
            return enqueue_lead(
                workflow=workflow,
                run_id=run_id,
                search_query=label or normalized,
                company_name=label or normalized,
                domain=normalized,
                source_url=f"https://{normalized}",
                source_type="manual_domain",
            )
        lead_payload = await asyncio.to_thread(_enqueue)
        if not lead_payload:
            await asyncio.to_thread(finalize_run, run_id, "EXHAUSTED", "Domain already exists in the lead database.")
            return
        await run_workflow_for_lead(workflow, lead_payload)
        await asyncio.to_thread(finalize_run, run_id, "COMPLETED")
    except Exception as exc:
        await asyncio.to_thread(finalize_run, run_id, "FAILED", str(exc))
        print(f"Run {run_id} failed: {exc}")


def normalize_domain(domain_or_url: str) -> str:
    value = domain_or_url.strip()
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return parsed.netloc or parsed.path


def enqueue_lead(
    workflow,
    run_id: str,
    search_query: str,
    company_name: str | None,
    domain: str,
    source_url: str,
    source_type: str,
):
    from db.models import find_existing_lead, save_lead_to_db
    from state import LeadState, LeadStatus

    existing = find_existing_lead(domain)
    if existing:
        return None

    initial_lead = LeadState(
        lead_id=str(uuid.uuid4()),
        run_id=run_id,
        search_query=search_query,
        company_name=company_name,
        domain=domain,
        source_url=source_url,
        source_type=source_type,
        status=LeadStatus.SEARCHED,
    )
    save_lead_to_db(initial_lead)
    return initial_lead


async def run_workflow_for_lead(workflow, initial_lead):
    from db.models import save_lead_to_db
    from state import LeadStatus

    try:
        await workflow.ainvoke({"lead": initial_lead, "markdown": None, "personalization_hook": None, "company_profile": None})
    except Exception as exc:
        initial_lead.status = LeadStatus.RETRY_PENDING if initial_lead.retry_count < 3 else LeadStatus.DEAD_LEAD
        initial_lead.retry_count += 1
        import asyncio
        await asyncio.to_thread(save_lead_to_db, initial_lead)
        print(f"Workflow failed for {initial_lead.domain}: {exc}")
    return initial_lead


def build_bucket_queries(query: str, bucket_rounds: int) -> list[str]:
    normalized = query.strip()
    if is_brand_query(normalized):
        return build_brand_queries(normalized, bucket_rounds)

    suffixes = [
        "",
        " company",
        " official site",
        " contact",
        " team",
        " about",
    ]
    buckets = []
    for index in range(bucket_rounds):
        suffix = suffixes[index % len(suffixes)]
        bucket_query = f"{normalized}{suffix}".strip()
        if bucket_query not in buckets:
            buckets.append(bucket_query)
    return buckets


def build_brand_queries(query: str, bucket_rounds: int) -> list[str]:
    suffixes = [
        "",
        " official site",
        " company",
        " contact",
        " team",
        " about",
    ]
    buckets = []
    for index in range(bucket_rounds):
        suffix = suffixes[index % len(suffixes)]
        bucket_query = f'"{query}"{suffix}'.strip()
        if bucket_query not in buckets:
            buckets.append(bucket_query)
    return buckets


def is_brand_query(query: str) -> bool:
    tokens = [token for token in query.split() if token]
    return len(tokens) == 1 and len(query) <= 24 and not query.startswith("http")


@app.post("/api/search")
async def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    from db.models import create_run

    run_id = str(uuid.uuid4())
    create_run(run_id, req.query, req.max_companies, "tavily_search")
    background_tasks.add_task(process_lead, req.query, req.max_companies, run_id)
    return {
        "status": "success",
        "message": "Outreach pipeline triggered.",
        "max_companies": req.max_companies,
        "run_id": run_id,
    }


@app.post("/api/process-domain")
async def start_domain(req: DomainRequest, background_tasks: BackgroundTasks):
    from db.models import create_run

    normalized = normalize_domain(req.domain)
    run_id = str(uuid.uuid4())
    create_run(run_id, req.label or normalized, 1, "manual_domain")
    background_tasks.add_task(process_domain, req.domain, req.label, run_id)
    return {"status": "success", "message": "Direct domain pipeline triggered.", "run_id": run_id}


@app.get("/api/leads")
def get_leads(limit: int = 50, offset: int = 0):
    from db.models import fetch_all_leads

    try:
        return {"leads": fetch_all_leads(limit=limit, offset=offset)}
    except Exception as e:
        return {"leads": [], "error": str(e)}


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str):
    from db.models import fetch_lead

    lead = fetch_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.delete("/api/leads/{lead_id}")
def remove_lead(lead_id: str):
    from db.models import delete_lead, fetch_lead

    lead = fetch_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.get("status") in {"SEARCHED", "CRAWLED", "EXTRACTED", "ENRICHED", "VALIDATED", "PERSONALIZED"}:
        raise HTTPException(
            status_code=409,
            detail="Lead is still active. Stop the parent run or wait for completion before deleting it.",
        )
    deleted = delete_lead(lead_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "deleted", "lead_id": lead_id}


@app.get("/api/runs")
def get_runs(limit: int = 20, offset: int = 0):
    from db.models import fetch_runs

    return {"runs": fetch_runs(limit=limit, offset=offset)}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    from db.models import fetch_run

    run = fetch_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str):
    from db.models import fetch_run, request_run_stop

    run = fetch_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") in {"COMPLETED", "EXHAUSTED", "FAILED", "STOPPED"}:
        return run
    updated = request_run_stop(run_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Run not found")
    return updated


@app.delete("/api/runs/{run_id}")
def remove_run(run_id: str, purge_leads: bool = True):
    from db.models import delete_run, fetch_run

    run = fetch_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") == "RUNNING" and not purge_leads:
        raise HTTPException(status_code=409, detail="Stop the run before deleting it.")
    deleted = delete_run(run_id, purge_leads=purge_leads)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "deleted", "run_id": run_id, "purge_leads": purge_leads}


@app.get("/api/summary")
def get_summary():
    from db.models import fetch_summary

    try:
        return fetch_summary()
    except Exception as e:
        return {
            "total_leads": 0,
            "sent_leads": 0,
            "ready_to_send": 0,
            "dead_leads": 0,
            "active_leads": 0,
            "total_runs": 0,
            "status_counts": [],
            "error": str(e),
        }


@app.get("/api/settings")
def get_settings():
    from db.models import get_settings

    return get_settings()


@app.put("/api/settings")
def update_settings(req: SettingsRequest):
    from db.models import get_settings, update_setting

    update_setting("draft_system_prompt", req.draft_system_prompt)
    if req.search_dedupe_across_db is not None:
        update_setting("search_dedupe_across_db", req.search_dedupe_across_db)
    if req.search_bucket_rounds is not None:
        update_setting("search_bucket_rounds", req.search_bucket_rounds)
    if req.search_variant_limit is not None:
        update_setting("search_variant_limit", req.search_variant_limit)
    return get_settings()


@app.get("/api/health")
def healthcheck():
    from db.models import init_db

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

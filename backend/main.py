import asyncio
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


async def process_lead(query: str, max_companies: int, run_id: str):
    from db.models import finalize_run
    from graph import compile_lead_graph
    from nodes.search import search_node

    try:
        results = search_node(query, max_companies=max_companies)
        discovered = results.get("discovered_urls", [])
        if not discovered:
            finalize_run(run_id, "EXHAUSTED", "No valid company domains discovered.")
            return

        workflow = compile_lead_graph()
        tasks = []
        for target in discovered:
            lead_payload = enqueue_lead(
                workflow=workflow,
                run_id=run_id,
                search_query=query,
                company_name=target.get("company_name"),
                domain=target["domain"],
                source_url=target["source_url"],
                source_type="tavily_search",
            )
            if lead_payload:
                tasks.append(asyncio.create_task(run_workflow_for_lead(workflow, lead_payload)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        finalize_run(run_id, "COMPLETED" if len(discovered) >= max_companies else "EXHAUSTED")
    except Exception as exc:
        finalize_run(run_id, "FAILED", str(exc))
        print(f"Run {run_id} failed: {exc}")


async def process_domain(domain: str, label: str | None, run_id: str):
    from db.models import finalize_run
    from graph import compile_lead_graph

    try:
        workflow = compile_lead_graph()
        normalized = normalize_domain(domain)
        lead_payload = enqueue_lead(
            workflow=workflow,
            run_id=run_id,
            search_query=label or normalized,
            company_name=label or normalized,
            domain=normalized,
            source_url=f"https://{normalized}",
            source_type="manual_domain",
        )
        if not lead_payload:
            finalize_run(run_id, "EXHAUSTED", "Domain already exists in the lead database.")
            return
        await run_workflow_for_lead(workflow, lead_payload)
        finalize_run(run_id, "COMPLETED")
    except Exception as exc:
        finalize_run(run_id, "FAILED", str(exc))
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
        await workflow.ainvoke({"lead": initial_lead, "markdown": None, "personalization_hook": None})
    except Exception as exc:
        initial_lead.status = LeadStatus.RETRY_PENDING if initial_lead.retry_count < 3 else LeadStatus.DEAD_LEAD
        initial_lead.retry_count += 1
        save_lead_to_db(initial_lead)
        print(f"Workflow failed for {initial_lead.domain}: {exc}")


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
def get_leads():
    from db.models import fetch_all_leads

    try:
        return {"leads": fetch_all_leads()}
    except Exception as e:
        return {"leads": [], "error": str(e)}


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str):
    from db.models import fetch_lead

    lead = fetch_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.get("/api/runs")
def get_runs():
    from db.models import fetch_runs

    return {"runs": fetch_runs()}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    from db.models import fetch_run

    run = fetch_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


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
    return get_settings()


@app.get("/api/health")
def healthcheck():
    from db.models import init_db

    init_db()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

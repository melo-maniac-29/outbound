import asyncio
from urllib.parse import urlparse
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

app = FastAPI(title="Outbound AI Agent API")

# Allow frontend to communicate with backend
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

async def process_lead(query: str, max_companies: int):
    from nodes.search import search_node
    from graph import compile_lead_graph
    from db.models import init_db

    init_db()

    results = search_node(query, max_companies=max_companies)
    discovered = results.get("discovered_urls", [])
    if not discovered:
        return
        
    workflow = compile_lead_graph()
    
    for target in discovered:
        enqueue_lead(
            workflow=workflow,
            search_query=query,
            company_name=target.get("company_name"),
            domain=target["domain"],
            source_url=target["source_url"],
            source_type="tavily_search",
        )


async def process_domain(domain: str, label: str | None = None):
    from graph import compile_lead_graph
    from db.models import init_db

    init_db()
    workflow = compile_lead_graph()
    normalized = normalize_domain(domain)
    enqueue_lead(
        workflow=workflow,
        search_query=label or normalized,
        company_name=label or normalized,
        domain=normalized,
        source_url=f"https://{normalized}",
        source_type="manual_domain",
    )


def normalize_domain(domain_or_url: str) -> str:
    value = domain_or_url.strip()
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return parsed.netloc or parsed.path


def enqueue_lead(workflow, search_query: str, company_name: str | None, domain: str, source_url: str, source_type: str):
    from state import LeadState, LeadStatus
    from db.models import find_existing_lead, save_lead_to_db

    initial_lead = LeadState(
        lead_id=str(uuid.uuid4()),
        search_query=search_query,
        company_name=company_name,
        domain=domain,
        source_url=source_url,
        source_type=source_type,
        status=LeadStatus.SEARCHED,
    )
    existing = find_existing_lead(domain)
    if existing:
        return existing

    save_lead_to_db(initial_lead)
    asyncio.create_task(run_workflow_for_lead(workflow, initial_lead))
    return initial_lead.model_dump()

async def run_workflow_for_lead(workflow, initial_lead):
    from state import LeadStatus
    from db.models import save_lead_to_db

    try:
        await workflow.ainvoke({"lead": initial_lead, "markdown": None, "personalization_hook": None})
    except Exception as exc:
        initial_lead.status = LeadStatus.RETRY_PENDING if initial_lead.retry_count < 3 else LeadStatus.DEAD_LEAD
        initial_lead.retry_count += 1
        save_lead_to_db(initial_lead)
        print(f"Workflow failed for {initial_lead.domain}: {exc}")

@app.post("/api/search")
async def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    """Starts the LangGraph pipeline in the background."""
    background_tasks.add_task(process_lead, req.query, req.max_companies)
    return {"status": "success", "message": "Outreach pipeline triggered.", "max_companies": req.max_companies}

@app.post("/api/process-domain")
async def start_domain(req: DomainRequest, background_tasks: BackgroundTasks):
    """Runs the pipeline for a direct company domain."""
    background_tasks.add_task(process_domain, req.domain, req.label)
    return {"status": "success", "message": "Direct domain pipeline triggered."}

@app.get("/api/leads")
def get_leads():
    """Fetches all leads and their status/emails from PostgreSQL."""
    from db.models import fetch_all_leads
    try:
        return {"leads": fetch_all_leads()}
    except Exception as e:
        return {"leads": [], "error": str(e)}

@app.get("/api/summary")
def get_summary():
    from db.models import fetch_summary

    try:
        return fetch_summary()
    except Exception as e:
        return {"total_leads": 0, "sent_leads": 0, "ready_to_send": 0, "dead_leads": 0, "active_leads": 0, "status_counts": [], "error": str(e)}

@app.get("/api/health")
def healthcheck():
    from db.models import init_db

    init_db()
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

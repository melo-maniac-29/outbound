import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

async def process_lead(query: str):
    from nodes.search import search_node
    from state import LeadState, LeadStatus
    from graph import compile_lead_graph
    
    # 1. Search for leads
    results = search_node(query)
    discovered = results.get("discovered_urls", [])
    if not discovered:
        return
        
    workflow = compile_lead_graph()
    
    # 2. Iterate through ALL discovered targets and process them
    for target in discovered:
        initial_lead = LeadState(
            lead_id=str(uuid.uuid4()),
            search_query=query,
            domain=target['domain'],
            source_url=target['source_url'],
            status=LeadStatus.NEW
        )
        
        # 3. Fire into LangGraph asynchronously
        asyncio.create_task(
            workflow.ainvoke({"lead": initial_lead, "markdown": None, "personalization_hook": None})
        )

@app.post("/api/search")
async def start_search(req: SearchRequest, background_tasks: BackgroundTasks):
    """Starts the LangGraph pipeline in the background."""
    background_tasks.add_task(process_lead, req.query)
    return {"status": "success", "message": "Outreach pipeline triggered."}

@app.get("/api/leads")
def get_leads():
    """Fetches all leads and their status/emails from SQLite."""
    import sqlite3
    import json
    try:
        with sqlite3.connect("outbound_leads.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            
        leads = []
        for r in rows:
            lead = dict(r)
            if lead.get("services"): lead["services"] = json.loads(lead["services"])
            if lead.get("signals"): lead["signals"] = json.loads(lead["signals"])
            if lead.get("email_sequence"): lead["email_sequence"] = json.loads(lead["email_sequence"])
            leads.append(lead)
        return {"leads": leads}
    except Exception as e:
        return {"leads": [], "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

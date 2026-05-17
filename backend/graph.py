from datetime import datetime
from typing import Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from state import LeadState, LeadStatus
from db.models import save_lead_to_db

from nodes.crawl import crawl_node
from nodes.extract import extract_founder_node, extract_services_node, extract_signals_node
from nodes.enrich import enrich_node, pattern_guess_node
from nodes.validate import validate_node
from nodes.personalize import personalize_node
from nodes.draft import draft_node
from nodes.outreach import outreach_node
class GraphState(TypedDict):
    lead: LeadState
    markdown: Optional[str]
    personalization_hook: Optional[str]
    
    # Temporary fields for parallel extraction
    ext_founder: Optional[dict]
    ext_services: Optional[list]
    ext_signals: Optional[list]

async def crawl_step(state: GraphState):
    lead = state["lead"]
    url = lead.domain or lead.source_url
    if url:
        if not url.startswith("http"):
            url = "https://" + url
        try:
            md = await crawl_node(url)
            lead.status = LeadStatus.CRAWLED
            lead.source_url = url
            save_lead_to_db(lead)
            return {"markdown": md, "lead": lead}
        except Exception as e:
            print(f"Crawl error: {e}")
            
    lead.status = LeadStatus.DEAD_LEAD
    save_lead_to_db(lead)
    return {"lead": lead, "markdown": None}

async def extract_founder_step(state: GraphState):
    md = state.get("markdown")
    if md:
        data = await extract_founder_node(md)
        return {"ext_founder": data}
    return {"ext_founder": {}}

async def extract_services_step(state: GraphState):
    md = state.get("markdown")
    if md:
        data = await extract_services_node(md)
        return {"ext_services": data.get("services", [])}
    return {"ext_services": []}

async def extract_signals_step(state: GraphState):
    md = state.get("markdown")
    if md:
        data = await extract_signals_node(md)
        return {"ext_signals": data.get("signals", [])}
    return {"ext_signals": []}

def merge_extractions_step(state: GraphState):
    lead = state["lead"]
    founder_data = state.get("ext_founder", {})
    
    lead.founder_name = founder_data.get("founder_name")
    lead.founder_linkedin = founder_data.get("linkedin")
    lead.founder_confidence = founder_data.get("confidence", 0.0)
    
    lead.services = state.get("ext_services", [])
    lead.signals = state.get("ext_signals", [])
    lead.extraction_timestamp = datetime.utcnow()
    
    lead.status = LeadStatus.EXTRACTED
    save_lead_to_db(lead)
    return {"lead": lead}

def dead_lead_step(state: GraphState):
    lead = state["lead"]
    lead.status = LeadStatus.DEAD_LEAD
    save_lead_to_db(lead)
    return {"lead": lead}

def enrich_step(state: GraphState):
    lead = state["lead"]
    data = enrich_node(lead.domain)
    lead.email = data.get("email")
    lead.email_confidence = data.get("email_confidence", 0.0)
    lead.status = LeadStatus.ENRICHED
    save_lead_to_db(lead)
    return {"lead": lead}

def pattern_guess_step(state: GraphState):
    lead = state["lead"]
    data = pattern_guess_node(lead.founder_name, lead.domain)
    lead.email = data.get("email")
    lead.email_confidence = data.get("email_confidence", 0.0)
    lead.status = LeadStatus.ENRICHED
    save_lead_to_db(lead)
    return {"lead": lead}

def validate_step(state: GraphState):
    lead = state["lead"]
    is_valid = validate_node(
        founder_confidence=lead.founder_confidence,
        email_confidence=lead.email_confidence,
        founder_name=lead.founder_name,
        email=lead.email
    )
    if is_valid:
        lead.status = LeadStatus.VALIDATED
    else:
        lead.status = LeadStatus.DEAD_LEAD
    save_lead_to_db(lead)
    return {"lead": lead}

def personalize_step(state: GraphState):
    lead = state["lead"]
    data = personalize_node(lead.signals)
    lead.status = LeadStatus.PERSONALIZED
    save_lead_to_db(lead)
    return {"personalization_hook": data["personalization_hook"], "lead": lead}

def draft_step(state: GraphState):
    lead = state["lead"]
    hook = state.get("personalization_hook", "Noticed your recent updates.")
    data = draft_node(
        founder_name=lead.founder_name,
        company=lead.company_name or lead.domain,
        signal=hook
    )
    lead.email_sequence = data.get("email_sequence", [])
    lead.status = data.get("status", LeadStatus.DEAD_LEAD)
    save_lead_to_db(lead)
    return {"lead": lead}

def outreach_step(state: GraphState):
    lead = state["lead"]
    # Only execute if drafting didn't kill the lead
    if lead.status != LeadStatus.DEAD_LEAD:
        data = outreach_node(email=lead.email, sequence=lead.email_sequence)
        lead.status = data.get("status", LeadStatus.SENT)
        save_lead_to_db(lead)
    return {"lead": lead}

# --- Conditional Edges ---
def check_founder_confidence(state: GraphState):
    if state["lead"].founder_confidence >= 0.75:
        return "enrich_node"
    return "dead_lead_node"

def check_email_confidence(state: GraphState):
    if state["lead"].email_confidence >= 0.70:
        return "validate_node"
    return "pattern_guess_node"

def check_validation(state: GraphState):
    if state["lead"].status == LeadStatus.VALIDATED:
        return "personalize_node"
    return END

def compile_lead_graph():
    """
    Compiles the full LangGraph state machine based on the conditional 
    edges defined in the architecture Readme.
    """
    workflow = StateGraph(GraphState)
    
    workflow.add_node("crawl_node", crawl_step)
    workflow.add_node("extract_founder", extract_founder_step)
    workflow.add_node("extract_services", extract_services_step)
    workflow.add_node("extract_signals", extract_signals_step)
    workflow.add_node("merge_extractions", merge_extractions_step)
    workflow.add_node("dead_lead_node", dead_lead_step)
    
    workflow.add_node("enrich_node", enrich_step)
    workflow.add_node("pattern_guess_node", pattern_guess_step)
    workflow.add_node("validate_node", validate_step)
    workflow.add_node("personalize_node", personalize_step)
    workflow.add_node("draft_node", draft_step)
    workflow.add_node("outreach_node", outreach_step)
    
    workflow.add_edge(START, "crawl_node")
    
    # Fan out
    workflow.add_edge("crawl_node", "extract_founder")
    workflow.add_edge("crawl_node", "extract_services")
    workflow.add_edge("crawl_node", "extract_signals")
    
    # Fan in
    workflow.add_edge("extract_founder", "merge_extractions")
    workflow.add_edge("extract_services", "merge_extractions")
    workflow.add_edge("extract_signals", "merge_extractions")
    
    # Conditional branch after merging extraction
    workflow.add_conditional_edges("merge_extractions", check_founder_confidence)
    workflow.add_edge("dead_lead_node", END)
    
    # Conditional branch after enrichment
    workflow.add_conditional_edges("enrich_node", check_email_confidence)
    
    # Pattern guess merges back into validation
    workflow.add_edge("pattern_guess_node", "validate_node")
    
    # Conditional branch after validation
    workflow.add_conditional_edges("validate_node", check_validation)
    
    # Linear path to the end
    workflow.add_edge("personalize_node", "draft_node")
    workflow.add_edge("draft_node", "outreach_node")
    workflow.add_edge("outreach_node", END)
    
    return workflow.compile()

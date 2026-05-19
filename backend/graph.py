import asyncio
from datetime import datetime, timezone
from typing import Optional, TypedDict
from langgraph.graph import StateGraph, START, END
from state import LeadState, LeadStatus
from db.models import save_lead_to_db

from nodes.crawl import crawl_node
from nodes.extract import extract_founder_node, extract_services_node, extract_signals_node, extract_emails_from_content
from nodes.linkedin_lookup import linkedin_lookup_node
from nodes.profile import build_profile_node
from nodes.enrich import enrich_node, pattern_guess_node
from nodes.validate import validate_node
from nodes.personalize import personalize_node
from nodes.draft import draft_node
from nodes.outreach import outreach_node


class GraphState(TypedDict):
    lead: LeadState
    markdown: Optional[str]
    personalization_hook: Optional[str]
    company_profile: Optional[dict]

    # Temporary fields for parallel extraction
    ext_founder: Optional[dict]
    ext_services: Optional[list]
    ext_signals: Optional[list]
    ext_emails: Optional[list]

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
            await asyncio.to_thread(save_lead_to_db, lead)
            return {"markdown": md, "lead": lead}
        except Exception as e:
            print(f"Crawl error: {e}")

    lead.status = LeadStatus.DEAD_LEAD
    await asyncio.to_thread(save_lead_to_db, lead)
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


async def extract_all_step(state: GraphState):
    md = state.get("markdown")
    if not md:
        return {"ext_founder": {}, "ext_services": [], "ext_signals": [], "ext_emails": []}

    # Email extraction is pure regex — runs instantly, no async needed
    crawled_emails = extract_emails_from_content(md)

    founder_data, services_data, signals_data = await asyncio.gather(
        extract_founder_node(md),
        extract_services_node(md),
        extract_signals_node(md),
    )
    return {
        "ext_founder": founder_data or {},
        "ext_services": (services_data or {}).get("services", []),
        "ext_signals": (signals_data or {}).get("signals", []),
        "ext_emails": crawled_emails,
    }


def merge_extractions_step(state: GraphState):
    lead = state["lead"]
    founder_data = state.get("ext_founder", {})

    lead.founder_name = founder_data.get("founder_name")
    lead.founder_linkedin = founder_data.get("linkedin")
    lead.founder_confidence = founder_data.get("confidence", 0.0)

    lead.services = state.get("ext_services", [])
    lead.signals = state.get("ext_signals", [])
    lead.extraction_timestamp = datetime.now(timezone.utc)

    # Use emails found directly on the company website (free, no API)
    crawled_emails = state.get("ext_emails", [])
    if crawled_emails:
        best = max(crawled_emails, key=lambda e: e.get("confidence", 0))
        lead.email = best["email"]
        lead.email_confidence = best["confidence"]

    lead.status = LeadStatus.EXTRACTED
    save_lead_to_db(lead)
    return {"lead": lead}

def linkedin_lookup_step(state: GraphState):
    lead = state["lead"]
    data = linkedin_lookup_node(
        founder_name=lead.founder_name,
        company_name=lead.company_name,
        domain=lead.domain,
        existing_linkedin=lead.founder_linkedin,
    )
    lead.founder_linkedin = data.get("founder_linkedin") or lead.founder_linkedin
    save_lead_to_db(lead)
    return {"lead": lead}

def dead_lead_step(state: GraphState):
    lead = state["lead"]
    lead.status = LeadStatus.DEAD_LEAD
    save_lead_to_db(lead)
    return {"lead": lead}

def enrich_step(state: GraphState):
    lead = state["lead"]
    # Skip Hunter.io if we already found a good email from the crawled content
    if lead.email and lead.email_confidence >= 0.80:
        lead.status = LeadStatus.ENRICHED
        save_lead_to_db(lead)
        return {"lead": lead}
    data = enrich_node(lead.domain)
    hunter_email = data.get("email")
    hunter_conf = data.get("email_confidence", 0.0)
    # Only replace if Hunter found something better
    if hunter_email and hunter_conf > lead.email_confidence:
        lead.email = hunter_email
        lead.email_confidence = hunter_conf
    lead.status = LeadStatus.ENRICHED
    save_lead_to_db(lead)
    return {"lead": lead}

async def build_profile_step(state: GraphState):
    lead = state["lead"]
    markdown = state.get("markdown") or ""
    data = await build_profile_node(
        markdown_content=markdown,
        company_name=lead.company_name,
        domain=lead.domain,
        founder_name=lead.founder_name,
        founder_linkedin=lead.founder_linkedin,
        services=lead.services,
        signals=lead.signals,
        email=lead.email,
    )
    lead.company_profile = data
    await asyncio.to_thread(save_lead_to_db, lead)
    return {"lead": lead, "company_profile": data}

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
    data = personalize_node(lead.signals, lead.company_profile)
    lead.status = LeadStatus.PERSONALIZED
    save_lead_to_db(lead)
    return {"personalization_hook": data["personalization_hook"], "lead": lead}

def draft_step(state: GraphState):
    lead = state["lead"]
    hook = state.get("personalization_hook", "Noticed your recent updates.")
    data = draft_node(
        founder_name=lead.founder_name,
        company=lead.company_name or lead.domain,
        signal=hook,
        company_profile=lead.company_profile,
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
        return "linkedin_lookup_node"
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
    workflow.add_node("extract_all_node", extract_all_step)
    workflow.add_node("extract_founder", extract_founder_step)
    workflow.add_node("extract_services", extract_services_step)
    workflow.add_node("extract_signals", extract_signals_step)
    workflow.add_node("merge_extractions", merge_extractions_step)
    workflow.add_node("linkedin_lookup_node", linkedin_lookup_step)
    workflow.add_node("dead_lead_node", dead_lead_step)

    workflow.add_node("enrich_node", enrich_step)
    workflow.add_node("build_profile_node", build_profile_step)
    workflow.add_node("pattern_guess_node", pattern_guess_step)
    workflow.add_node("validate_node", validate_step)
    workflow.add_node("personalize_node", personalize_step)
    workflow.add_node("draft_node", draft_step)
    workflow.add_node("outreach_node", outreach_step)

    workflow.add_edge(START, "crawl_node")

    workflow.add_edge("crawl_node", "extract_all_node")
    workflow.add_edge("extract_all_node", "merge_extractions")

    workflow.add_conditional_edges("merge_extractions", check_founder_confidence)
    workflow.add_edge("dead_lead_node", END)

    workflow.add_conditional_edges("build_profile_node", check_email_confidence)
    workflow.add_edge("enrich_node", "build_profile_node")
    workflow.add_edge("linkedin_lookup_node", "enrich_node")

    workflow.add_edge("pattern_guess_node", "validate_node")

    workflow.add_conditional_edges("validate_node", check_validation)

    workflow.add_edge("personalize_node", "draft_node")
    workflow.add_edge("draft_node", "outreach_node")
    workflow.add_edge("outreach_node", END)

    return workflow.compile()

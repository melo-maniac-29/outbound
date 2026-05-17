from state import LeadStatus

def outreach_node(email: str, sequence: list) -> dict:
    """
    Draft-only terminal node.
    We stop at READY_TO_SEND so human review can happen before any delivery.
    """
    if not email or not sequence:
        return {"status": LeadStatus.DEAD_LEAD}

    return {"status": LeadStatus.READY_TO_SEND}

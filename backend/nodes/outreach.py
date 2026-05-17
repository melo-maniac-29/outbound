from state import LeadStatus

def outreach_node(email: str, sequence: list) -> dict:
    """
    Tool: Gmail SMTP
    For testing purposes, this node MOCKS the email sending to strictly adhere
    to the rule: "Never send real outreach emails from tests or examples".
    """
    if not email or not sequence:
        return {"status": LeadStatus.DEAD_LEAD}
        
    print("\n" + "="*50)
    print("🚨 MOCK EMAIL DISPATCH 🚨")
    print(f"To: {email}")
    print(f"Subject: Based on recent signal")
    print("-" * 50)
    print(sequence[0])
    print("="*50 + "\n")
    
    # We pretend the email was sent successfully and followups are scheduled.
    return {"status": LeadStatus.SENT}

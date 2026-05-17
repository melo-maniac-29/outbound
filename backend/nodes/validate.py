def validate_node(founder_confidence: float, email_confidence: float, founder_name: str, email: str) -> bool:
    """
    Tool: Pure Python
    Responsibilities: Deduplication, Confidence threshold filtering, Completeness checks.
    Returns True if valid, False if it should be DEAD_LEAD.
    """
    # Thresholds defined in Readme:
    # Founder >= 0.75
    # Email >= 0.70
    
    if not founder_name or not email:
        return False
        
    if founder_confidence < 0.75:
        print("Validation Failed: Founder confidence too low.")
        return False
        
    if email_confidence < 0.70:
        print("Validation Failed: Email confidence too low.")
        return False
        
    return True

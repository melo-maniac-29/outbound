import os
import requests

def enrich_node(domain: str) -> dict:
    """
    Tool: Hunter.io
    Input: domain
    Output: verified emails and confidence scores
    """
    api_key = os.getenv("HUNTER_API_KEY")
    
    if not api_key or not domain or api_key == "dummy":
        return {"email": None, "email_confidence": 0.0}
        
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        
        emails = data.get("data", {}).get("emails", [])
        
        best_email = None
        best_confidence = 0.0
        
        for e in emails:
            # Hunter returns confidence out of 100, we normalize to 0.0 - 1.0
            conf = float(e.get("confidence", 0)) / 100.0
            if conf > best_confidence:
                best_confidence = conf
                best_email = e.get("value")
                
        return {
            "email": best_email,
            "email_confidence": best_confidence
        }
    except Exception as e:
        print(f"Hunter.io Error: {e}")
        return {"email": None, "email_confidence": 0.0}

def pattern_guess_node(founder_name: str, domain: str) -> dict:
    """
    Runs only when Hunter confidence is insufficient.
    Guesses email patterns based on name and domain.
    """
    if not founder_name or not domain:
        return {"email": None, "email_confidence": 0.0}
        
    parts = founder_name.lower().split()
    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        guessed_email = f"{first}.{last}@{domain}"
        return {"email": guessed_email, "email_confidence": 0.72}
        
    return {"email": None, "email_confidence": 0.0}

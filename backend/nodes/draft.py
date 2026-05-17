import os
import json
from openai import OpenAI
from state import LeadStatus
from db.models import get_setting

def _fallback_sequence(founder_name: str, company: str, signal: str, sender: str) -> list[str]:
    first_name = founder_name or "there"
    company_name = company or "your company"
    hook = signal or "a recent update on your team"
    return [
        (
            f"Hi {first_name},\n\n"
            f"Came across {company_name} and noticed {hook}.\n\n"
            "I'm building an AI outreach system that helps agencies turn relevant signals into targeted outbound faster.\n\n"
            "Worth a 10-minute conversation this week?\n\n"
            f"{sender}"
        ),
        (
            f"Hi {first_name},\n\n"
            f"Wanted to follow up on {hook}.\n\n"
            "I think there is a practical fit for tightening prospect research and getting sharper first-touch emails out the door.\n\n"
            f"Happy to share examples if useful.\n\n{sender}"
        ),
        (
            f"Hi {first_name},\n\n"
            "Just closing the loop.\n\n"
            f"Still think there is a strong fit for {company_name} around signal-based outbound and faster sequence drafting.\n\n"
            f"Open to a quick chat?\n\n{sender}"
        ),
    ]


def draft_node(founder_name: str, company: str, signal: str, product: str = "our AI outreach system", sender: str = "Allen") -> dict:
    """
    Tool: GPT-4o
    Generates the 3-email sequence based on constraints.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/email_system.txt")
    with open(prompt_path, "r") as f:
        file_prompt = f.read()
    system_prompt = get_setting("draft_system_prompt", file_prompt) or file_prompt

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return {
            "email_sequence": _fallback_sequence(founder_name, company, signal, sender),
            "status": LeadStatus.READY_TO_SEND,
        }

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_API_BASE"))
        
    user_prompt = f"""
    Generate a 3-email sequence.
    Variables:
    - first_name: {founder_name or "Founder"}
    - company: {company or "your company"}
    - signal: {signal or "your recent updates"}
    - product: {product}
    - sender: {sender}
    
    Return a JSON array of exactly 3 strings representing the body of email 1, 2, and 3.
    """
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        sequence = json.loads(content)
        return {
            "email_sequence": sequence,
            "status": LeadStatus.READY_TO_SEND
        }
    except Exception as e:
        print(f"Draft Node Error: {e}")
        return {
            "email_sequence": _fallback_sequence(founder_name, company, signal, sender),
            "status": LeadStatus.READY_TO_SEND,
        }

import os
import json
from openai import OpenAI
from state import LeadStatus

def draft_node(founder_name: str, company: str, signal: str, product: str = "our AI outreach system", sender: str = "Allen") -> dict:
    """
    Tool: GPT-4o
    Generates the 3-email sequence based on constraints.
    """
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        base_url=os.getenv("OPENAI_API_BASE")
    )
    
    prompt_path = os.path.join(os.path.dirname(__file__), "../prompts/email_system.txt")
    with open(prompt_path, "r") as f:
        system_prompt = f.read()
        
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
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4"),
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
        return {"email_sequence": [], "status": LeadStatus.DEAD_LEAD}

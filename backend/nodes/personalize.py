import os
from openai import OpenAI

def personalize_node(signals: list, company_profile: dict | None = None) -> dict:
    """
    Tool: GPT-4o
    Selects one relevant signal from the extracted list for personalization.
    """
    profile_angle = (company_profile or {}).get("outreach_angle")
    if profile_angle:
        return {"personalization_hook": profile_angle}

    if not signals:
        profile_summary = (company_profile or {}).get("summary")
        return {"personalization_hook": profile_summary or "Noticed your recent growth."}

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return {"personalization_hook": signals[0]}

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_API_BASE"))
    
    prompt = f"Select the single most relevant and impactful business signal from the following list to use as a personalization hook in a cold email. Return ONLY the chosen signal text.\n\nSignals:\n{signals}"
    
    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50
        )
        hook = response.choices[0].message.content.strip()
        return {"personalization_hook": hook}
    except Exception as e:
        print(f"Personalize Node Error: {e}")
        return {"personalization_hook": signals[0]}

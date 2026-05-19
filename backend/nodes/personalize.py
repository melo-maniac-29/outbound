import os
from openai import OpenAI

_GENERIC_PHRASES = (
    "reach out with a concise note",
    "noticed your recent growth",
    "concise note about how you can help",
    "no detailed profile",
)

def _is_generic(text: str | None) -> bool:
    if not text:
        return True
    lowered = text.lower()
    return any(phrase in lowered for phrase in _GENERIC_PHRASES)


def personalize_node(signals: list, company_profile: dict | None = None) -> dict:
    """
    Selects the best personalization hook from signals or profile data.
    Falls back gracefully without using generic placeholders.
    """
    p = company_profile or {}

    # If we have real signals, use GPT to pick the best one
    if signals:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "dummy":
            client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_API_BASE"))
            prompt = (
                "Select the single most relevant business signal from this list to use as a "
                "personalization hook in a cold email. Return ONLY the chosen signal text, nothing else.\n\n"
                f"Signals:\n{chr(10).join(f'- {s}' for s in signals)}"
            )
            try:
                resp = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=80,
                )
                hook = resp.choices[0].message.content.strip()
                if hook:
                    return {"personalization_hook": hook}
            except Exception as e:
                print(f"Personalize Node Error: {e}")
        return {"personalization_hook": signals[0]}

    # No signals — try to build a hook from profile data
    angle = p.get("outreach_angle")
    if angle and not _is_generic(angle):
        return {"personalization_hook": angle}

    # Build hook from key_services
    services = p.get("key_services") or []
    if isinstance(services, list) and services:
        return {"personalization_hook": f"their work in {services[0]}"}

    # Build hook from summary
    summary = p.get("summary")
    if summary and not _is_generic(summary) and len(summary) > 30:
        return {"personalization_hook": summary[:120]}

    # True last resort — don't use a placeholder, just leave it thin
    return {"personalization_hook": None}

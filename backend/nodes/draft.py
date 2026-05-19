import os
import re
import json
from openai import OpenAI
from state import LeadStatus
from db.models import get_setting


def _format_profile_brief(company_profile: dict | None, company: str | None) -> str:
    """
    Convert the raw company profile dict into a natural language brief
    that the LLM can actually use to write better emails.
    """
    p = company_profile or {}
    company_name = company or "the company"
    lines = []

    summary = p.get("summary")
    if summary:
        lines.append(f"About: {summary}")

    positioning = p.get("positioning")
    if positioning:
        lines.append(f"Positioning: {positioning}")

    audience = p.get("audience")
    if audience:
        lines.append(f"Target audience: {audience}")

    key_services = p.get("key_services", [])
    if key_services:
        lines.append(f"Core services: {', '.join(key_services[:5])}")

    credibility = p.get("credibility_signals", [])
    if credibility:
        lines.append(f"Recent activity: {', '.join(credibility[:4])}")

    angle = p.get("outreach_angle")
    if angle:
        lines.append(f"Best outreach angle: {angle}")

    if not lines:
        return f"{company_name} — no detailed profile available."

    return "\n".join(lines)


def _fallback_sequence(founder_name: str, company: str, signal: str, sender: str, company_profile: dict | None = None) -> list[str]:
    first_name = founder_name or "there"
    company_name = company or "your company"
    p = company_profile or {}
    hook = signal or p.get("outreach_angle") or p.get("summary") or "a recent update on your team"
    services_mention = ""
    key_services = p.get("key_services", [])
    if key_services:
        services_mention = f" around {key_services[0]}"

    return [
        (
            f"Hi {first_name},\n\n"
            f"Came across {company_name} and noticed {hook}.\n\n"
            f"I'm building an AI outreach system that helps agencies turn relevant signals "
            f"into targeted outbound faster{services_mention}.\n\n"
            f"Worth a 10-minute conversation this week?\n\n"
            f"{sender}"
        ),
        (
            f"Hi {first_name},\n\n"
            f"Wanted to follow up — I think there's a practical fit for tightening "
            f"prospect research and getting sharper first-touch emails out the door"
            f"{' for ' + company_name if company_name != 'your company' else ''}.\n\n"
            f"Happy to share examples if useful.\n\n{sender}"
        ),
        (
            f"Hi {first_name},\n\n"
            f"Just closing the loop.\n\n"
            f"Still think there's a strong fit for {company_name}"
            f"{services_mention} around signal-based outbound and faster sequence drafting.\n\n"
            f"Open to a quick chat?\n\n{sender}"
        ),
    ]


def draft_node(founder_name: str, company: str, signal: str, company_profile: dict | None = None, product: str = "our AI outreach system", sender: str = "Allen") -> dict:
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
            "email_sequence": _fallback_sequence(founder_name, company, signal, sender, company_profile=company_profile),
            "status": LeadStatus.READY_TO_SEND,
        }

    client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_API_BASE"))

    # Format the profile as a readable brief instead of raw JSON
    profile_brief = _format_profile_brief(company_profile, company)

    user_prompt = f"""Generate a 3-email cold outreach sequence for this lead.

TARGET PERSON: {founder_name or "Founder"}
COMPANY: {company or "their company"}
PERSONALIZATION SIGNAL: {signal or "their recent updates"}

COMPANY BRIEF:
{profile_brief}

PRODUCT WE ARE OFFERING: {product}
SENDER NAME: {sender}

RULES:
- Each email must be under 100 words
- No generic openings like "Hope this finds you well"
- Peer-to-peer tone, direct and confident
- Email 1 MUST reference the specific signal above
- Email 2 should add a new angle or insight
- Email 3 is a short closing-the-loop message
- Use the company brief to make emails specific, not generic

Return in EXACTLY this format:
EMAIL_1:
<body>

EMAIL_2:
<body>

EMAIL_3:
<body>"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()

        # More robust parsing — handle variations in LLM output format
        parts = re.split(r"EMAIL_[123]\s*:", content)
        sequence = [part.strip() for part in parts if part.strip()]

        if len(sequence) < 3:
            # Try alternative split patterns the LLM might use
            parts = re.split(r"(?:Email\s+[123]|#\s*Email\s+[123]|---)\s*:?\s*\n", content, flags=re.IGNORECASE)
            sequence = [part.strip() for part in parts if part.strip()]

        if len(sequence) >= 3:
            return {
                "email_sequence": sequence[:3],
                "status": LeadStatus.READY_TO_SEND
            }
        else:
            print(f"Draft parsing got {len(sequence)} parts instead of 3, using fallback.")
            return {
                "email_sequence": _fallback_sequence(founder_name, company, signal, sender, company_profile=company_profile),
                "status": LeadStatus.READY_TO_SEND,
            }
    except Exception as e:
        print(f"Draft Node Error: {e}")
        return {
            "email_sequence": _fallback_sequence(founder_name, company, signal, sender, company_profile=company_profile),
            "status": LeadStatus.READY_TO_SEND,
        }

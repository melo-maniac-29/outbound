import os
import re
import json
from openai import OpenAI
from state import LeadStatus
from db.models import get_setting


DEFAULT_SYSTEM_PROMPT = (
    "You are an expert sales representative writing cold outreach emails.\n"
    "Your goal is to write a concise, peer-to-peer cold email based on the company brief and signals provided.\n\n"
    "Constraints:\n"
    "- Under 100 words per email.\n"
    "- No generic openings like 'Hope this finds you well' or 'I came across your company'.\n"
    "- Tone: Peer-to-peer, confident, direct — like messaging a colleague, not pitching a stranger.\n"
    "- Must reference the specific signal or company insight provided.\n"
    "- Each email in the sequence should have a different angle, not repeat the same pitch."
)


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
    system_prompt = get_setting("draft_system_prompt", DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT

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
PERSONALIZATION SIGNAL: {signal or "their positioning in the market"}

COMPANY BRIEF:
{profile_brief}

PRODUCT WE ARE OFFERING: {product}
SENDER NAME: {sender}

RULES:
- Each email must be 60-100 words (not shorter, not longer)
- Write the FULL email body: greeting line, 2-3 sentences of body, closing question, sender sign-off
- No generic openings like "Hope this finds you well" or "I came across your company"
- Peer-to-peer tone — write like you already know the industry
- Email 1: Lead with the personalization signal
- Email 2: New angle — add a different value insight
- Email 3: Short closing-the-loop message
- Use specific details from the company brief, not vague generalities
- Always end with a soft CTA question (not "Let me know if you're interested")

Return in EXACTLY this format with no extra text before EMAIL_1:
EMAIL_1:
<full email body>

EMAIL_2:
<full email body>

EMAIL_3:
<full email body>"""

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1200,
        )
        content = response.choices[0].message.content.strip()
        print(f"[DRAFT] raw output ({len(content)} chars): {content[:300]}...")

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

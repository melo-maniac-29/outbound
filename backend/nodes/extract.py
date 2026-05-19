import os
import re
from pydantic import BaseModel, Field


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4o")


def get_llm():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        model=_model_name(),
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=0,
    )


def _to_payload(result, defaults: dict) -> dict:
    if result is None:
        return defaults
    if isinstance(result, dict):
        return {**defaults, **result}
    if hasattr(result, "model_dump"):
        return {**defaults, **result.model_dump()}
    if hasattr(result, "dict"):
        return {**defaults, **result.dict()}
    return defaults


def _extract_linkedin(markdown_content: str) -> str | None:
    match = re.search(r"https?://[^\s)]+linkedin\.com/[^\s)]+", markdown_content, re.IGNORECASE)
    return match.group(0) if match else None


def _heuristic_founder(markdown_content: str) -> dict | None:
    explicit_patterns = [
        r"## Meet the Founder.*?###\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.'-]+)+)\s*\nFounder(?:\s*&\s*CEO)?",
        r"###\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.'-]+)+)\s*\nFounder(?:\s*&\s*CEO)?",
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.'-]+)+)\s*\n(?:Founder|Co-Founder|Founder & CEO|CEO|Managing Director|Principal)",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, markdown_content, re.IGNORECASE | re.DOTALL)
        if match:
            return {
                "founder_name": match.group(1).strip(),
                "linkedin": _extract_linkedin(markdown_content),
                "confidence": 0.9,
            }
    return None


class FounderExtraction(BaseModel):
    founder_name: str | None = Field(description="Name of the founder or CEO")
    linkedin: str | None = Field(description="LinkedIn URL of the founder")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")


class ServicesExtraction(BaseModel):
    services: list[str] = Field(description="List of services provided by the company")


class SignalsExtraction(BaseModel):
    signals: list[str] = Field(description="List of recent news, signals, or client case studies")


async def extract_founder_node(markdown_content: str) -> dict:
    """Extract founder details with structured LLM output and heuristics fallback."""
    heuristic = _heuristic_founder(markdown_content)
    if heuristic:
        return heuristic

    llm = get_llm().with_structured_output(FounderExtraction, method="function_calling")
    prompt = (
        "Extract the most senior real decision-maker mentioned in this company content. "
        "Prefer founder, co-founder, CEO, owner, managing director, or principal. "
        "Return linkedin only when an actual profile URL is present. "
        "Set confidence above 0.75 only when the role and name are explicit.\n\n"
        f"{markdown_content[:22000]}"
    )
    try:
        res = await llm.ainvoke(prompt)
        return _to_payload(res, {"founder_name": None, "linkedin": None, "confidence": 0.0})
    except Exception as e:
        print(f"Founder extraction failed: {e}")
        return {"founder_name": None, "linkedin": None, "confidence": 0.0}


async def extract_services_node(markdown_content: str) -> dict:
    """Extract company services with structured output."""
    llm = get_llm().with_structured_output(ServicesExtraction, method="function_calling")
    prompt = f"Extract a concise list of services provided by the company from the following markdown.\n\n{markdown_content[:22000]}"
    try:
        res = await llm.ainvoke(prompt)
        return _to_payload(res, {"services": []})
    except Exception as e:
        print(f"Services extraction failed: {e}")
        return {"services": []}


async def extract_signals_node(markdown_content: str) -> dict:
    """Extract recent signals and news with structured output."""
    llm = get_llm().with_structured_output(SignalsExtraction, method="function_calling")
    prompt = (
        "Extract recent signals, news, client wins, case studies, launches, or hiring indicators "
        "that could support outreach personalization.\n\n"
        f"{markdown_content[:22000]}"
    )
    try:
        res = await llm.ainvoke(prompt)
        return _to_payload(res, {"signals": []})
    except Exception as e:
        print(f"Signals extraction failed: {e}")
        return {"signals": []}


def extract_emails_from_content(markdown_content: str) -> list[dict]:
    """
    Extract email addresses directly from crawled website content.
    This is a free alternative to Hunter.io — emails found on the company's
    own website are high-confidence since the company published them.
    """
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    found = re.findall(email_pattern, markdown_content)

    # Generic role-based emails are useless for cold outreach to a founder
    blocked_prefixes = {
        'info@', 'support@', 'hello@', 'contact@', 'admin@', 'sales@',
        'help@', 'noreply@', 'no-reply@', 'team@', 'press@', 'media@',
        'privacy@', 'legal@', 'billing@', 'careers@', 'jobs@', 'hr@',
        'webmaster@', 'postmaster@', 'abuse@', 'newsletter@', 'office@',
        'general@', 'enquiries@', 'feedback@', 'marketing@',
    }

    results = []
    seen: set[str] = set()
    for email in found:
        normalized = email.lower().strip()
        if normalized in seen:
            continue
        seen.add(normalized)

        if any(normalized.startswith(prefix) for prefix in blocked_prefixes):
            continue

        # Skip file-like references that regex might catch
        if normalized.endswith(('.png', '.jpg', '.gif', '.svg', '.webp', '.css', '.js')):
            continue

        # Skip example/placeholder emails
        if 'example.com' in normalized or 'test.' in normalized or 'placeholder' in normalized:
            continue

        results.append({
            'email': normalized,
            'confidence': 0.85,
            'source': 'website_content',
        })

    return results

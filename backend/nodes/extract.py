import os
import re
import json
from openai import OpenAI


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4o")


def _parse_json_response(content: str, key: str, default):
    """Parse JSON from LLM output, handling markdown code fences."""
    # Strip markdown code fences
    content = re.sub(r"```(?:json)?\s*", "", content).strip(" `")
    try:
        parsed = json.loads(content)
        return parsed.get(key, default)
    except Exception:
        # Try to find JSON object in the text
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed.get(key, default)
            except Exception:
                pass
    return default


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
    match = re.search(r"https?://[^\s)]+linkedin\.com/in/[^\s)]+", markdown_content, re.IGNORECASE)
    return match.group(0).rstrip(")") if match else None


def _heuristic_founder(markdown_content: str) -> dict | None:
    patterns = [
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.']+)+)\s*\n(?:Founder|Co-Founder|Founder & CEO|CEO|Managing Director|Principal|Owner)",
        r"###\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z.']+)+)\s*\n(?:Founder|CEO)",
    ]
    for p in patterns:
        m = re.search(p, markdown_content, re.IGNORECASE | re.DOTALL)
        if m:
            return {"founder_name": m.group(1).strip(), "linkedin": _extract_linkedin(markdown_content), "confidence": 0.9}
    return None



async def extract_founder_node(markdown_content: str) -> dict:
    """Extract founder details. Uses heuristic first, then LLM."""
    heuristic = _heuristic_founder(markdown_content)
    if heuristic:
        return heuristic


    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return {"founder_name": None, "linkedin": None, "confidence": 0.0}

    client = _get_client()
    prompt = (
        "Extract the most senior decision-maker from this company website content. "
        "Prefer founder, co-founder, CEO, owner, managing director, or principal.\n"
        "Return ONLY valid JSON in this exact format (no markdown, no extra text):\n"
        '{"founder_name": "Full Name or null", "linkedin": "URL or null", "confidence": 0.0}\n\n'
        f"{markdown_content[:22000]}"
    )
    try:
        resp = client.chat.completions.create(
            model=_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        content = resp.choices[0].message.content.strip()
        name = _parse_json_response(content, "founder_name", None)
        linkedin = _parse_json_response(content, "linkedin", None) or _extract_linkedin(markdown_content)
        confidence = _parse_json_response(content, "confidence", 0.0)
        result = {"founder_name": name, "linkedin": linkedin, "confidence": float(confidence or 0)}
        print(f"[EXTRACT] founder={result}")
        return result
    except Exception as e:
        print(f"Founder extraction failed: {e}")
        return {"founder_name": None, "linkedin": None, "confidence": 0.0}




async def extract_services_node(markdown_content: str) -> dict:
    """Extract company services — aggressive extraction, never returns empty if site has content."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return {"services": []}
    client = _get_client()
    prompt = (
        "Extract services from this B2B company website. Be thorough — check headings, nav URLs, "
        "bullet lists, service page URLs like /services/X, and any phrases describing offerings.\n"
        "Return ONLY valid JSON (no markdown, no extra text):\n"
        '{"services": ["service1", "service2", "service3"]}\n\n'
        f"{markdown_content[:22000]}"
    )
    try:
        resp = client.chat.completions.create(
            model=_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
        )
        content = resp.choices[0].message.content.strip()
        services = _parse_json_response(content, "services", [])
        if not isinstance(services, list):
            services = []
        print(f"[EXTRACT] services={services}")
        return {"services": services}
    except Exception as e:
        print(f"Services extraction failed: {e}")
        return {"services": []}


async def extract_signals_node(markdown_content: str) -> dict:
    """Extract outreach signals — aggressive extraction from any available clues."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return {"signals": []}
    client = _get_client()
    prompt = (
        "Extract personalization signals for cold outreach from this company website.\n"
        "Look for: client logos, testimonials, case study titles, blog topics, specific industries served, "
        "notable results, integrations mentioned, awards, and growth indicators.\n"
        "If explicit signals are sparse, derive implied signals from the company's focus and client type.\n"
        "Return ONLY valid JSON (no markdown, no extra text):\n"
        '{"signals": ["signal 1 sentence", "signal 2 sentence"]}\n\n'
        f"{markdown_content[:22000]}"
    )
    try:
        resp = client.chat.completions.create(
            model=_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=600,
        )
        content = resp.choices[0].message.content.strip()
        signals = _parse_json_response(content, "signals", [])
        if not isinstance(signals, list):
            signals = []
        print(f"[EXTRACT] signals={signals}")
        return {"signals": signals}
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

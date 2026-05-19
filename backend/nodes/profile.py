import json
import os
import re
from openai import OpenAI
from typing import Any


def _model_name() -> str:
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4o")


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )


def _parse_json(content: str) -> dict:
    """Parse JSON from LLM output, handling markdown code fences."""
    content = re.sub(r"```(?:json)?\s*", "", content).strip(" `")
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}


def _fallback_profile(
    company_name: str | None,
    domain: str | None,
    founder_name: str | None,
    services: list[str] | None,
    signals: list[str] | None,
) -> dict[str, Any]:
    company_label = company_name or domain or "the company"
    parts = [company_label]
    if services:
        parts.append(f"offers {', '.join(services[:3])}")
    if founder_name:
        parts.append(f"led by {founder_name}")
    summary = " — ".join(parts) + "."

    outreach_angle = None
    if signals:
        outreach_angle = signals[0]
    elif services:
        outreach_angle = f"Their focus on {services[0]} is a strong entry point for outreach."

    return {
        "summary": summary,
        "positioning": f"{company_label} serves a specialized niche.",
        "audience": f"Companies needing {services[0].lower()}" if services else None,
        "key_services": (services or [])[:5],
        "credibility_signals": (signals or [])[:5],
        "outreach_angle": outreach_angle,
    }


async def build_profile_node(
    markdown_content: str,
    company_name: str | None,
    domain: str | None,
    founder_name: str | None = None,
    founder_linkedin: str | None = None,
    services: list[str] | None = None,
    signals: list[str] | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    """Build a company profile using direct OpenAI client + JSON output."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return _fallback_profile(company_name, domain, founder_name, services, signals)

    client = _get_client()
    prompt = (
        "Synthesize a B2B company profile for cold outreach. Use ONLY evidence from the input.\n\n"
        "Return ONLY valid JSON (no markdown, no extra text) in this exact format:\n"
        '{"summary": "...", "positioning": "...", "audience": "...", '
        '"key_services": ["svc1","svc2"], "credibility_signals": ["sig1","sig2"], "outreach_angle": "..."}\n\n'
        "Rules for outreach_angle: must be specific and actionable, referencing a real signal, "
        "service, or client type from the site. Never write 'Reach out with a concise note'.\n\n"
        f"Company: {company_name or 'Unknown'}\n"
        f"Domain: {domain or 'Unknown'}\n"
        f"Founder: {founder_name or 'Unknown'}\n"
        f"Services extracted: {json.dumps(services or [])}\n"
        f"Signals extracted: {json.dumps(signals or [])}\n\n"
        "SITE CONTENT:\n"
        f"{markdown_content[:18000]}"
    )
    try:
        resp = client.chat.completions.create(
            model=_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=800,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = _parse_json(raw)
        print(f"[PROFILE] angle={str(parsed.get('outreach_angle', ''))[:80]}")
        fallback = _fallback_profile(company_name, domain, founder_name, services, signals)
        return {**fallback, **{k: v for k, v in parsed.items() if v}}
    except Exception as exc:
        print(f"[PROFILE] build failed: {exc}")
        return _fallback_profile(company_name, domain, founder_name, services, signals)

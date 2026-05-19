import json
import os
from typing import Any

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


def _to_payload(result, defaults: dict[str, Any]) -> dict[str, Any]:
    if result is None:
        return defaults
    if isinstance(result, dict):
        return {**defaults, **result}
    if hasattr(result, "model_dump"):
        return {**defaults, **result.model_dump()}
    if hasattr(result, "dict"):
        return {**defaults, **result.dict()}
    return defaults


class CompanyProfile(BaseModel):
    summary: str | None = Field(description="Short plain-English company summary")
    positioning: str | None = Field(description="How the company positions itself in the market")
    audience: str | None = Field(description="Who the company appears to serve")
    key_services: list[str] = Field(default_factory=list, description="Main services or offerings")
    credibility_signals: list[str] = Field(default_factory=list, description="Signals that can support outreach personalization")
    outreach_angle: str | None = Field(description="The best outreach angle based on the available evidence")


def _fallback_profile(
    company_name: str | None,
    domain: str | None,
    founder_name: str | None,
    founder_linkedin: str | None,
    services: list[str] | None,
    signals: list[str] | None,
) -> dict[str, Any]:
    company_label = company_name or domain or "the company"

    # Build a real summary from available data
    summary_parts = [f"{company_label}"]
    if services:
        summary_parts.append(f"offers {', '.join(services[:3])}")
    if founder_name:
        summary_parts.append(f"led by {founder_name}")
    summary = " — ".join(summary_parts) + "." if len(summary_parts) > 1 else f"{company_label}."

    # Build a useful outreach angle from signals
    outreach_angle = None
    if signals:
        outreach_angle = signals[0]
    elif services:
        outreach_angle = f"Their focus on {services[0]} suggests a fit for signal-based outreach tooling."
    else:
        outreach_angle = f"Reach out with a concise note about how you can help {company_label}."

    # Infer audience from services if possible
    audience = None
    if services:
        audience = f"Companies needing {services[0].lower()}"

    return {
        "summary": summary,
        "positioning": f"{company_label} operates in a specialized niche based on their public site content.",
        "audience": audience,
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
    """
    Build a concise company profile from the crawled site and extracted facts.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "dummy":
        return _fallback_profile(company_name, domain, founder_name, founder_linkedin, services, signals)

    llm = get_llm().with_structured_output(CompanyProfile, method="function_calling")
    prompt = (
        "You are synthesizing a B2B company profile for cold outreach preparation.\n\n"
        "INSTRUCTIONS:\n"
        "- Use ONLY evidence present in the input. Do not speculate.\n"
        "- Write the summary as a clear, plain-English description of what the company does.\n"
        "- The outreach_angle should be a specific, actionable suggestion for the first email hook.\n"
        "  It should reference a real signal, achievement, or service — NOT a generic placeholder.\n"
        "- If evidence is thin, be honest. A short factual profile is better than a fabricated one.\n"
        "- The audience field should describe WHO the company serves.\n\n"
        f"Company name: {company_name or 'Unknown'}\n"
        f"Domain: {domain or 'Unknown'}\n"
        f"Founder: {founder_name or 'Unknown'}\n"
        f"Founder LinkedIn: {founder_linkedin or 'Not found'}\n"
        f"Email: {email or 'Not found'}\n"
        f"Extracted services: {json.dumps(services or [])}\n"
        f"Extracted signals: {json.dumps(signals or [])}\n\n"
        "CRAWLED SITE CONTENT:\n"
        f"{markdown_content[:22000]}"
    )
    try:
        res = await llm.ainvoke(prompt)
        return _to_payload(
            res,
            _fallback_profile(company_name, domain, founder_name, founder_linkedin, services, signals),
        )
    except Exception as exc:
        print(f"Profile build failed: {exc}")
        return _fallback_profile(company_name, domain, founder_name, founder_linkedin, services, signals)

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
    summary_bits = [f"{company_label}."]
    if services:
        summary_bits.append(f"Services: {', '.join(services[:4])}.")
    if signals:
        summary_bits.append(f"Signals: {signals[0]}.")
    if founder_name:
        summary_bits.append(f"Founder: {founder_name}.")
    if founder_linkedin:
        summary_bits.append("Founder LinkedIn confirmed.")

    return {
        "summary": " ".join(summary_bits).strip(),
        "positioning": f"{company_label} appears to be positioning itself through its public site content.",
        "audience": None,
        "key_services": (services or [])[:5],
        "credibility_signals": (signals or [])[:5],
        "outreach_angle": signals[0] if signals else f"Lead with a concise note about {company_label}.",
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
        "Synthesize a concise B2B company profile from the provided site content and extracted facts.\n"
        "Use only the evidence in the input. Avoid speculation.\n"
        "Return a practical profile that can be used to draft a relevant cold email.\n\n"
        f"Company name: {company_name or ''}\n"
        f"Domain: {domain or ''}\n"
        f"Founder: {founder_name or ''}\n"
        f"Founder LinkedIn: {founder_linkedin or ''}\n"
        f"Email: {email or ''}\n"
        f"Services: {json.dumps(services or [])}\n"
        f"Signals: {json.dumps(signals or [])}\n\n"
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

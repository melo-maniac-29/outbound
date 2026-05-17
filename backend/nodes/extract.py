import os
import re
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

def _model_name() -> str:
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4o")


def get_llm():
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        model=_model_name(),
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=0
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
    """Extracts founder details in parallel using native Langchain."""
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
    """Extracts company services in parallel."""
    llm = get_llm().with_structured_output(ServicesExtraction, method="function_calling")
    prompt = f"Extract a concise list of services provided by the company from the following markdown.\n\n{markdown_content[:22000]}"
    try:
        res = await llm.ainvoke(prompt)
        return _to_payload(res, {"services": []})
    except Exception as e:
        print(f"Services extraction failed: {e}")
        return {"services": []}

async def extract_signals_node(markdown_content: str) -> dict:
    """Extracts recent signals and news in parallel."""
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

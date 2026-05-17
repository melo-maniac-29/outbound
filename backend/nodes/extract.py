import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

def get_llm():
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        model="gpt-4",
        base_url=os.getenv("OPENAI_API_BASE"),
        temperature=0
    )

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
    llm = get_llm().with_structured_output(FounderExtraction)
    prompt = f"Extract the founder/CEO and their LinkedIn URL from the following markdown. If not found, return None and 0.0 confidence.\n\n{markdown_content[:8000]}"
    try:
        res = await llm.ainvoke(prompt)
        return res.dict()
    except Exception as e:
        print(f"Founder extraction failed: {e}")
        return {"founder_name": None, "linkedin": None, "confidence": 0.0}

async def extract_services_node(markdown_content: str) -> dict:
    """Extracts company services in parallel."""
    llm = get_llm().with_structured_output(ServicesExtraction)
    prompt = f"Extract a list of services provided by the company from the following markdown.\n\n{markdown_content[:8000]}"
    try:
        res = await llm.ainvoke(prompt)
        return res.dict()
    except Exception as e:
        print(f"Services extraction failed: {e}")
        return {"services": []}

async def extract_signals_node(markdown_content: str) -> dict:
    """Extracts recent signals and news in parallel."""
    llm = get_llm().with_structured_output(SignalsExtraction)
    prompt = f"Extract a list of recent signals, news, case studies, or client announcements.\n\n{markdown_content[:8000]}"
    try:
        res = await llm.ainvoke(prompt)
        return res.dict()
    except Exception as e:
        print(f"Signals extraction failed: {e}")
        return {"signals": []}

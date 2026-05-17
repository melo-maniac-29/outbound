from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class LeadStatus(str, Enum):
    NEW = "NEW"
    SEARCHED = "SEARCHED"
    CRAWLED = "CRAWLED"
    EXTRACTED = "EXTRACTED"
    ENRICHED = "ENRICHED"
    VALIDATED = "VALIDATED"
    PERSONALIZED = "PERSONALIZED"
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    FOLLOWUP_1 = "FOLLOWUP_1"
    FOLLOWUP_2 = "FOLLOWUP_2"
    RESPONDED = "RESPONDED"
    DEAD_LEAD = "DEAD_LEAD"
    RETRY_PENDING = "RETRY_PENDING"

class LeadState(BaseModel):
    lead_id: str

    search_query: str
    company_name: Optional[str] = None
    domain: Optional[str] = None

    founder_name: Optional[str] = None
    founder_linkedin: Optional[str] = None
    founder_confidence: float = 0.0

    email: Optional[str] = None
    email_confidence: float = 0.0

    services: List[str] = Field(default_factory=list)
    signals: List[str] = Field(default_factory=list)

    source_url: Optional[str] = None
    source_type: Optional[str] = None
    extraction_timestamp: Optional[datetime] = None

    email_sequence: List[str] = Field(default_factory=list)

    retry_count: int = 0

    status: LeadStatus

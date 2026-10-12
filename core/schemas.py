from typing import Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    document_id: str
    document_type: str
    title: str
    language: str = "en"
    source: Optional[str] = None
    text: str


class Requirement(BaseModel):
    requirement_id: str
    source_document_id: str

    # Core semantic fields
    actor: Optional[str] = None
    action: Optional[str] = None
    object: Optional[str] = None
    recipient: Optional[str] = None

    # Obligation / permission
    obligation_type: Optional[str] = None
    authorization: Optional[str] = None

    # Conditions and exceptions
    condition: Optional[str] = None
    exception: Optional[str] = None
    eligibility_logic: Optional[str] = None

    # Numeric / temporal constraints
    operator: Optional[str] = None
    threshold: Optional[float] = None
    unit: Optional[str] = None
    deadline: Optional[str] = None

    # Regulatory metadata
    benefit: Optional[str] = None
    page_number: Optional[int] = None
    source_url: Optional[str] = None

    # Original evidence
    source_text: str


class MatchResult(BaseModel):
    contract_text: str
    policy_text: str
    similarity_score: float
    matched: bool


class ConflictResult(BaseModel):
    conflict: bool
    severity: str
    reason: str

    contract_evidence: str
    policy_evidence: str

    similarity_score: float
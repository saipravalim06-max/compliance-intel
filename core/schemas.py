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

    actor: Optional[str] = None
    action: Optional[str] = None
    object: Optional[str] = None
    recipient: Optional[str] = None

    obligation_type: Optional[str] = None
    authorization: Optional[str] = None

    condition: Optional[str] = None
    threshold: Optional[str] = None
    deadline: Optional[str] = None
    exception: Optional[str] = None

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
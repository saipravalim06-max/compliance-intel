from typing import List, Optional

from pydantic import BaseModel

from core.normalize import normalize_threshold
from core.taxonomy import (
    OPERATOR_MAP,
    STATE_DOMAIN_MAP,
    STATE_TYPE_MAP,
    FitVerdict,
    SourceType,
)


class Document(BaseModel):
    document_id: str
    document_type: str
    title: str
    language: str = "en"
    source: Optional[str] = None
    text: str


class Requirement(BaseModel):
    """
    ONE requirement model for contract clauses, company policies AND state
    regulations. Fields from the original engine come first (unchanged, so
    extraction.py / conflict.py keep working). Everything below the divider is
    optional and used mainly by state-regulation rows (Sreeja's 21-column
    schema maps onto these 1:1 — see Requirement.from_state_row).
    """
    requirement_id: str
    source_document_id: str

    actor: Optional[str] = None
    action: Optional[str] = None
    object: Optional[str] = None
    recipient: Optional[str] = None

    obligation_type: Optional[str] = None
    authorization: Optional[str] = None

    condition: Optional[str] = None
    threshold: Optional[str] = None      # original text, kept for explanations
    deadline: Optional[str] = None
    exception: Optional[str] = None

    source_text: str

    # ---- shared-schema extensions (all optional) ---------------------------
    source_type: Optional[SourceType] = None
    language: Optional[str] = None
    jurisdiction: Optional[str] = None        # e.g. "Tamil Nadu"
    policy_name: Optional[str] = None
    domain: Optional[str] = None              # taxonomy.StateDomain value
    requirement_name: Optional[str] = None
    requirement_type: Optional[str] = None    # taxonomy.RequirementType value

    operator: Optional[str] = None            # taxonomy.Operator value
    threshold_value: Optional[float] = None   # numeric: INR in absolute rupees
    unit: Optional[str] = None                # taxonomy.Unit value
    bound: Optional[str] = None               # UPPER | LOWER, from wording ("up to", "at least")
    benefit: Optional[str] = None
    eligibility_logic: Optional[str] = None   # AND | OR

    # ---- Step 2 additions (all optional) ------------------------------------
    quantity_kind: Optional[str] = None       # what the primary number measures, e.g. TERMINATION_NOTICE
    per: Optional[str] = None                 # 'month' | 'year' | 'occurrence' ... for rates and limits
    applies_to: Optional[str] = None          # scope qualifier, e.g. 'vendors classified as "critical"'
    quantities: Optional[List[dict]] = None   # every quantity found: value, unit, bound, per, kind, raw, inferred

    page_number: Optional[int] = None
    source_url: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    notes: Optional[str] = None

    @classmethod
    def from_state_row(cls, row: dict) -> "Requirement":
        """Build a Requirement from one row of a state workbook (dict keyed by
        the 21 schema columns). Raw values are mapped through the taxonomy
        crosswalks; missing/NaN stays None — nothing is invented."""

        def clean(v):
            if v is None:
                return None
            s = str(v).strip()
            return None if s == "" or s.lower() in ("nan", "none", "null", "nat") else s

        def key(v):
            c = clean(v)
            return c.lower() if c else None

        op_raw = key(row.get("operator"))
        dom_raw = key(row.get("domain"))
        typ_raw = key(row.get("requirement_type"))
        thr_text = clean(row.get("threshold"))
        norm = normalize_threshold(thr_text, clean(row.get("unit"))) if thr_text else None
        page = clean(row.get("page_number"))
        try:
            page = int(float(page)) if page else None
        except ValueError:
            page = None

        return cls(
            requirement_id=clean(row.get("requirement_id")) or "",
            source_document_id=clean(row.get("policy_name")) or "",
            actor=clean(row.get("actor")),
            action=clean(row.get("action")),
            condition=clean(row.get("condition")),
            threshold=thr_text,
            deadline=clean(row.get("deadline")),
            source_text=clean(row.get("evidence_text")) or "",
            source_type=SourceType.STATE_REGULATION,
            language="en",
            jurisdiction=clean(row.get("state")),
            policy_name=clean(row.get("policy_name")),
            domain=STATE_DOMAIN_MAP[dom_raw].value if dom_raw in STATE_DOMAIN_MAP else None,
            requirement_name=clean(row.get("requirement_name")),
            requirement_type=STATE_TYPE_MAP[typ_raw].value if typ_raw in STATE_TYPE_MAP else None,
            operator=OPERATOR_MAP[op_raw].value if op_raw in OPERATOR_MAP else None,
            threshold_value=norm["value"] if norm else None,
            unit=norm["unit"] if norm else None,
            bound=norm["bound"] if norm else None,
            benefit=clean(row.get("benefit")),
            eligibility_logic=clean(row.get("eligibility_logic")),
            page_number=page,
            source_url=clean(row.get("source_url")),
            effective_from=clean(row.get("effective_from")),
            effective_to=clean(row.get("effective_to")),
            notes=clean(row.get("notes")),
        )


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
    label: Optional[str] = None   # taxonomy.ConflictLabel value (CONFLICT / NO_CONFLICT / ...)


class ProfileCheck(BaseModel):
    """Module 1 output: one state requirement evaluated against a company profile."""
    requirement_id: str
    jurisdiction: str
    verdict: FitVerdict
    company_value: Optional[str] = None   # the profile fact that was compared
    rule: Optional[str] = None            # e.g. "annual_turnover <= 50 crore"
    reasoning: Optional[str] = None
    evidence_text: Optional[str] = None
    page_number: Optional[int] = None
    source_url: Optional[str] = None

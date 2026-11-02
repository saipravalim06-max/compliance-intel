"""
core/extraction.py — rule-based requirement extraction (baseline).

Turns one contract / policy sentence into a structured Requirement:
modality (permission / obligation / prohibition / restricted permission),
action, object, recipient, authorization, quantities (value, unit, direction,
kind), deadline, condition, scope qualifier and exception.

This is the transparent baseline. A learned extractor should be evaluated
against it on the same labelled set (see scripts/evaluate.py).
"""
import re
from typing import Optional

from core.quantities import Quantity, detect_kind, find_quantities, preprocess
from core.schemas import Requirement
from core.taxonomy import ObligationType, Operator, Unit

# ----------------------------------------------------------------- modality
_NOT_REQUIRED = re.compile(r"\bnot\s+(?:be\s+)?required\b|\bneed\s+not\b")
_PROHIBITION = re.compile(
    r"\b(?:must|shall|will|may|can|should|is|are|be|do|does)\s+not\b|\bcannot\b|\bcan\s+not\b|"
    r"\bnot\s+(?:be\s+)?(?:permitted|allowed|entitled)\b|\bprohibit\w*\b|\bforbid\w*\b|"
    r"\bno\s+(?:\w+\s+){1,2}(?:shall|may|will|can)\b|\bneither\b[^.;]{0,60}\b(?:may|shall|will|can)\b|"
    r"\b(?:agrees?|covenants?|undertakes?|promises?)\s+not\s+to\b|\b(?:not\s+acceptable|unacceptable)\b"
)
_VOID = re.compile(r"\b(?:void|invalid|null|of no (?:force|effect)|not (?:be )?valid)\b")
_RESTRICTED = re.compile(
    r"\bmay\s+only\b|\bonly\b[^.;]{0,40}\bmay\b|\bonly\s+(?:be\s+)?(?:shared|disclosed|provided|transferred|used)\b|"
    r"\bmay\b[^.;]{0,100}\bonly\s+(?:if|with|after|when|upon|to)\b"
)
_OBLIGATION = re.compile(r"\b(?:must|shall|required|requires?|needs?\s+to|is\s+responsible\s+for|agrees?\s+to|will)\b")
_PERMISSION = re.compile(r"\b(?:may|can|permitted|allowed|entitled|right\s+to)\b")


def detect_modality(lower: str) -> Optional[ObligationType]:
    if _NOT_REQUIRED.search(lower):
        return ObligationType.PERMISSION
    if _PROHIBITION.search(lower):
        return ObligationType.PROHIBITION
    if _RESTRICTED.search(lower):
        return ObligationType.RESTRICTED_PERMISSION
    ob, pe = _OBLIGATION.search(lower), _PERMISSION.search(lower)
    if ob and pe:
        return ObligationType.OBLIGATION if ob.start() < pe.start() else ObligationType.PERMISSION
    if ob:
        return ObligationType.OBLIGATION
    if pe:
        return ObligationType.PERMISSION
    return None


# ------------------------------------------------------------ authorization
_AUTH_WORD = r"(?:approval|authori[sz]ation|consent|permission)"
_WITHOUT_AUTH = re.compile(rf"\bwithout\s+(?:the\s+|any\s+)?(?:[\w'’-]+\s+){{0,3}}?(?:prior\s+)?(?:written\s+)?{_AUTH_WORD}\b")
_REQUIRES_AUTH = re.compile(
    rf"\b(?:prior\s+(?:written\s+)?{_AUTH_WORD}|{_AUTH_WORD}\s+(?:is|are)\s+required|"
    rf"(?:requires?|subject\s+to|only\s+with|upon|with\s+the)\s+(?:the\s+)?(?:[\w'’-]+\s+){{0,3}}?(?:prior\s+)?(?:written\s+)?{_AUTH_WORD})\b"
)
_APPROVED_IN_WRITING = re.compile(
    r"\b(?:approved|authorized|consented|permitted)\b[^.;]{0,40}\b(?:in writing|beforehand|prior|advance)\b|"
    r"\b(?:prior|advance|beforehand)\b[^.;]{0,40}\b(?:in writing\s+)?(?:approval|consent|permission|authori[sz]ation)\b|"
    r"\b(?:in writing)\b[^.;]{0,30}\b(?:beforehand|prior|advance)\b",
    re.IGNORECASE,
)

# approvals by the COMPANY's own functions are internal governance, not consent from the counterparty
_INTERNAL_APPROVER = re.compile(
    r"\b(?:general counsel|director[- ]level|finance (?:department|review)|legal (?:department|review)|executive committee|"
    r"chief financial officer|cfo|by legal|by finance)\b"
)

# ------------------------------------------------------------------- action
_ACTIONS = [
    ("share", r"shar\w*"), ("disclose", r"disclos\w*"),
    ("provide", r"provid(?:e|es|ed|ing)\b(?!\s+that\b)"),
    ("transfer", r"transfer\w*"),
    ("collect", r"collect\w*"), ("store", r"stor(?:e|es|ed|ing|age)|host\w*"), ("retain", r"retain\w*|retention"),
    ("delete", r"delet\w*|destr(?:oy|uction)\w*|purg\w*"), ("pay", r"pay\w*"), ("terminate", r"terminat\w*"),
    ("assign", r"assign\w*|novat\w*"), ("audit", r"audit\w*"), ("notify", r"notif\w*|notice"), ("report", r"report\w*"),
    ("maintain", r"maintain\w*"), ("submit", r"submit\w*"), ("renew", r"renew\w*"), ("indemnify", r"indemnif\w*"),
    ("insure", r"insur\w*"), ("warrant", r"warrant\w*"), ("compete", r"compet\w*"), ("solicit", r"solicit\w*"),
    ("remediate", r"remediat\w*"),("engage", r"engag\w*"),("engage", r"sub[- ]?process(?:ing|ors?)"),
    ("subcontract", r"sub[- ]?contract\w*"), ("govern", r"govern\w*"),
    ("publicize", r"publici\w*|marketing\b|use\b[^.;]{0,35}\b(?:name|logo)"),
    ]
_ACTION_RES = [(name, re.compile(rf"\b(?:{rx})\b")) for name, rx in _ACTIONS]
_RECIPIENT_ACTIONS = {"share", "disclose", "provide", "transfer", "submit"}

_OBJECTS = [
    "customer or confidential data",
    "company or customer data",
    "customer data",
    "confidential data",
    "personal data",
    "patient data",
    "clinical data",
    "health data",
    "customer information",
    "company information",
    "confidential information",
    "intellectual property",
    "sub-processors",
    "subprocessors",
    "subcontractors",
    "core services",
    "company's name or logo",
    "company name or logo",
    "name or logo",
    "marketing material",
    "publicity",
    "payments",
    "payment",
    "services",
    "liability",
    "insurance",
    "warranty",
    "fees",
    "agreement",
    "contract",
]
_APPLIES_TO = re.compile(
    r"^\s*(?:\d+\.\d+\s+)?((?:vendors?|suppliers?|contractors?|contracts?|agreements?|third parties)\s+"
    r"(?:classified|designated|categori[sz]ed|deemed)\s+as\s+[^,]*?)(?=\s+(?:must|shall|should|are\s+required|will)\b)"
)


def _fmt(q: Quantity) -> str:
    unit = q.unit.value.lower().replace("_", " ")
    return f"{q.value:g} {unit}"


def extract_requirement(
    text: str,
    requirement_id: str = "REQ-001",
    source_document_id: str = "DOC-001",
) -> Requirement:
    lower = text.lower().replace("’", "'")

    modality = detect_modality(lower)

    # authorization (context-aware: "must not share ... without approval" means approval IS required)
    authorization: Optional[str] = None
    if _WITHOUT_AUTH.search(lower):
        # "must not X without consent" / "X without consent is void"  => consent IS required
        restrictive = modality == ObligationType.PROHIBITION or bool(_VOID.search(lower))
        authorization = "REQUIRED" if restrictive else "NOT_REQUIRED"
    elif _REQUIRES_AUTH.search(lower):
        authorization = "REQUIRED"
    elif _APPROVED_IN_WRITING.search(lower):
        authorization = "REQUIRED"
    elif re.search(
    r"\b(?:shall|must|will)\b.{0,100}"
    r"\b(?:first\s+)?(?:have\s+been\s+)?obtained\b.{0,50}"
    r"\b(?:written\s+)?(?:consent|approval|authorization|authorisation|permission)\b",
    lower,
    ):
        authorization = "REQUIRED"

    if authorization and _INTERNAL_APPROVER.search(lower) and not re.search(r"\b(?:counterparty|vendor|supplier|customer|other party|licensor|licensee)'?s?\s+(?:prior\s+)?(?:written\s+)?(?:consent|approval)", lower):
        authorization = None

    # action = whichever action word appears first in the operative sentence.
    # If the clause begins with a section heading (e.g., "6.3 Transfer. Either party may novate..."),
    # prefer the action from the body sentence over a heading verb.
    heading_match = re.match(r"^\s*(?:\d+(?:\.\d+)*\s+)?([A-Za-z\s]{1,30}\.)\s+(.+)$", lower, re.DOTALL)
    search_target = heading_match.group(2) if heading_match else lower

    action, best = None, None
    for name, rx in _ACTION_RES:
        m = rx.search(search_target)
        if m and (best is None or m.start() < best):
            action, best = name, m.start()

    if not action:
        for name, rx in _ACTION_RES:
            m = rx.search(lower)
            if m and (best is None or m.start() < best):
                action, best = name, m.start()

    
    # recipient (only meaningful for disclosure-type actions)
    recipient = None
    if action in _RECIPIENT_ACTIONS:
        m = re.search(
            r"\b(?:to|with)\s+(?:the\s+|its\s+|any\s+)?([a-z][a-z\s-]*?)"
            r"(?=\s+(?:without|with|if|when|unless|provided that|after|only|before|for|by|upon|in|on|during|within|that|which)\b|[.,;]|$)",
            text, re.IGNORECASE,
        )
        if m:
            recipient = m.group(1).strip()

    # Object extraction must run for every action, not only recipient actions.
    if action == "engage":
        obj = next(
            (
                o for o in (
                    "sub-processors",
                    "subprocessors",
                    "subcontractors",
                )
                if o in lower
            ),
            None,
        )
    elif action == "govern":
        m_gov = re.search(r"\bgoverned\s+by\s+(?:the\s+)?(laws\s+of\s+[^.,;\n]+|[a-z\s]+jurisdiction|[a-z\s]+law)", lower)
        if m_gov:
            obj = m_gov.group(1).strip()
        else:
            obj = next((o for o in _OBJECTS if o in lower), None)
    else:
        obj = next((o for o in _OBJECTS if o in lower), None)

    if action == "assign" and obj is None and ("agreement" in lower or "contract" in lower):
        obj = "agreement"


    # quantities
    prohibition = modality == ObligationType.PROHIBITION
    quantities = find_quantities(text, prohibition=prohibition)
    if not any(detect_kind(text, q) == "TERMINATION_NOTICE" for q in quantities):
        # immediate termination counts as "0 days notice" only when it is not for cause / insolvency / pay in lieu
        if re.search(r"\b(?:terminat\w*|cancel\w*)\b", lower) and re.search(
            r"\b(?:immediately|forthwith|with immediate effect|without (?:any |prior )?notice)\b", lower
        ) and not re.search(
            r"\b(?:cause|breach|default|insolven\w*|bankrupt\w*|violat\w*|misconduct|fail\w*|in lieu|notice period|"
            r"convicted|fraud|negligence|non-?payment)\b", lower
        ):
            quantities.append(Quantity(0.0, Unit.DAYS, kind="TERMINATION_NOTICE", raw="immediate termination", inferred=True))
    for q in quantities:
        q.kind = q.kind or detect_kind(text, q)
    primary = next((q for q in quantities if q.kind), quantities[0] if quantities else None)

    threshold = threshold_value = unit = bound = per = kind = operator = None
    if primary:
        threshold, threshold_value, unit, bound = _fmt(primary), primary.value, primary.unit.value, primary.bound
        per, kind = primary.per, primary.kind
        operator = {"UPPER": Operator.LTE.value, "LOWER": Operator.GTE.value}.get(bound or "")

    deadline = None
    m = re.search(r"\b(?:within|no later than|not later than|after)\s+(?:the\s+)?(\d+(?:\.\d+)?)\s*(?:business\s+|calendar\s+)?(hours?|days?|weeks?|months?|years?)\b", preprocess(text))
    if m:
        deadline = f"{m.group(1)} {m.group(2)}"

    cond = re.search(r"\b(?:if|when|unless|provided that)\b(.+?)(?:\.|$)", text, re.IGNORECASE)
    exc = re.search(r"\b(?:except|unless)\b(.+?)(?:\.|$)", text, re.IGNORECASE)
    scope = _APPLIES_TO.search(lower)

    return Requirement(
        requirement_id=requirement_id,
        source_document_id=source_document_id,
        action=action,
        object=obj,
        recipient=recipient,
        obligation_type=modality.value if modality else None,
        authorization=authorization,
        condition=cond.group(1).strip() if cond else None,
        threshold=threshold,
        deadline=deadline,
        exception=exc.group(1).strip() if exc else None,
        source_text=text,
        threshold_value=threshold_value,
        unit=unit,
        bound=bound,
        operator=operator,
        quantity_kind=kind,
        per=per,
        applies_to=scope.group(1).strip() if scope else None,
        quantities=[
            {"value": q.value, "unit": q.unit.value, "bound": q.bound, "per": q.per, "kind": q.kind,
             "raw": q.raw, "inferred": q.inferred}
            for q in quantities
        ] or None,
    )

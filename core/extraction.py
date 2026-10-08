import re
from typing import Optional

from core.schemas import Requirement


def extract_requirement(
    text: str,
    requirement_id: str = "REQ-001",
    source_document_id: str = "DOC-001",
) -> Requirement:
    """
    Extract a lightweight structured requirement from a contract/policy sentence.

    This is the first rule-based baseline for the project.
    Later, we will replace/extend these rules with an NLP model.
    """

    lower = text.lower()

    actor: Optional[str] = None
    action: Optional[str] = None
    obj: Optional[str] = None
    recipient: Optional[str] = None
    authorization: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[str] = None
    deadline: Optional[str] = None
    obligation_type: Optional[str] = None
    exception: Optional[str] = None

    # ---------------------------------------------------------
    # Authorization
    # ---------------------------------------------------------

    no_authorization_patterns = [
        "without prior approval",
        "without prior written approval",
        "without approval",
        "without prior authorization",
        "without prior written authorization",
        "without authorization",
    ]

    authorization_required_patterns = [
        "prior approval",
        "prior written approval",
        "prior authorization",
        "prior written authorization",
        "approval is required",
        "authorization is required",
    ]

    if any(pattern in lower for pattern in no_authorization_patterns):
        authorization = "NOT_REQUIRED"

    elif any(pattern in lower for pattern in authorization_required_patterns):
        authorization = "REQUIRED"

    # ---------------------------------------------------------
    # Action
    # ---------------------------------------------------------

    action_patterns = [
        "share",
        "disclose",
        "provide",
        "transfer",
        "collect",
        "store",
        "retain",
        "pay",
        "terminate",
        "assign",
        "audit",
        "notify",
        "maintain",
        "submit",
    ]

    for candidate in action_patterns:
        if re.search(rf"\b{candidate}\w*\b", lower):
            action = candidate
            break

    # ---------------------------------------------------------
    # Recipient
    # ---------------------------------------------------------

    recipient_match = re.search(
        r"\b(?:to|with)\s+(?:the\s+)?([a-zA-Z][a-zA-Z\s-]*?)(?=\s+(?:without|with|if|when|unless|provided that)\b|[.,;]|$)",
        text,
        re.IGNORECASE,
    )

    if recipient_match:
        recipient = recipient_match.group(1).strip()

    # ---------------------------------------------------------
    # Object
    # ---------------------------------------------------------

    object_patterns = [
        "customer data",
        "personal data",
        "confidential information",
        "customer information",
        "company information",
        "intellectual property",
        "payment",
        "payments",
        "services",
    ]

    for candidate in object_patterns:
        if candidate in lower:
            obj = candidate
            break

    # ---------------------------------------------------------
    # Deadline
    # ---------------------------------------------------------

    deadline_match = re.search(
        r"\b(?:within|after)\s+(\d+(?:\.\d+)?)\s+(day|days|month|months|year|years)\b",
        lower,
    )

    if deadline_match:
        deadline = f"{deadline_match.group(1)} {deadline_match.group(2)}"

    # ---------------------------------------------------------
    # Numeric threshold
    # ---------------------------------------------------------

    threshold_match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*(%|percent|employees?|days?|months?|years?)\b",
        lower,
    )

    if threshold_match:
        threshold = (
            f"{threshold_match.group(1)} {threshold_match.group(2)}"
        )

    # ---------------------------------------------------------
    # Obligation type
    # ---------------------------------------------------------

    if any(word in lower for word in ["may", "can", "permitted", "allowed"]):
        obligation_type = "PERMISSION"

    elif any(word in lower for word in ["must", "shall", "required"]):
        obligation_type = "OBLIGATION"

    # ---------------------------------------------------------
    # Condition
    # ---------------------------------------------------------

    condition_match = re.search(
        r"\b(?:if|when|unless|provided that)\b(.+?)(?:\.|$)",
        text,
        re.IGNORECASE,
    )

    if condition_match:
        condition = condition_match.group(1).strip()

    # ---------------------------------------------------------
    # Exception
    # ---------------------------------------------------------

    exception_match = re.search(
        r"\b(?:except|unless)\b(.+?)(?:\.|$)",
        text,
        re.IGNORECASE,
    )

    if exception_match:
        exception = exception_match.group(1).strip()

    return Requirement(
        requirement_id=requirement_id,
        source_document_id=source_document_id,
        actor=actor,
        action=action,
        object=obj,
        recipient=recipient,
        obligation_type=obligation_type,
        authorization=authorization,
        condition=condition,
        threshold=threshold,
        deadline=deadline,
        exception=exception,
        source_text=text,
    )
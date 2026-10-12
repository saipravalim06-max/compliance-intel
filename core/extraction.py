import re
from typing import Optional

from core.schemas import Requirement


NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _extract_number(text: str) -> Optional[float]:
    """
    Extract a numeric value from either:
      - 30
      - 30.5
      - thirty
      - thirty (30)

    Returns the numeric value only.
    """

    digit_match = re.search(r"\b\d+(?:\.\d+)?\b", text)

    if digit_match:
        return float(digit_match.group())

    lower = text.lower()

    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", lower):
            return float(value)

    return None


def _extract_unit(text: str) -> Optional[str]:
    """
    Extract the unit associated with a numeric value.
    """

    unit_match = re.search(
        r"\b(days?|weeks?|months?|years?|employees?|percent|%)\b",
        text.lower(),
    )

    if unit_match:
        unit = unit_match.group(1).lower()

        if unit == "%":
            return "percent"

        if unit.endswith("s"):
            return unit[:-1]

        return unit

    return None


def _extract_operator(text: str) -> Optional[str]:
    """
    Extract a comparison operator from phrases such as:
      at least 30 days -> >=
      no less than 30 days -> >=
      at most 30 days -> <=
      no more than 30 days -> <=
      more than 30 days -> >
      fewer than 30 employees -> <
      less than 30 days -> <
    """

    lower = text.lower()

    if re.search(r"\b(at least|no less than|minimum of)\b", lower):
        return ">="

    if re.search(r"\b(at most|no more than|maximum of)\b", lower):
        return "<="

    if re.search(r"\b(more than|greater than|over)\b", lower):
        return ">"

    if re.search(r"\b(less than|fewer than|under)\b", lower):
        return "<"

    return None


def _extract_threshold(text: str):
    """
    Extract threshold and unit while distinguishing phrases such as
    'at least 30 days' from deadline phrases such as 'within 30 days'.
    """

    lower = text.lower()

    # Match phrases containing a number/number word followed by a unit.
    number_pattern = (
        r"(?:\d+(?:\.\d+)?|"
        + "|".join(NUMBER_WORDS.keys())
        + r")"
    )

    threshold_match = re.search(
        rf"\b{number_pattern}\s*(?:\(\s*\d+(?:\.\d+)?\s*\))?"
        rf"\s*(days?|weeks?|months?|years?|employees?|percent|%)\b",
        lower,
    )

    if not threshold_match:
        return None, None

    matched_text = threshold_match.group()

    value = _extract_number(matched_text)
    unit = _extract_unit(matched_text)

    return value, unit


def extract_requirement(
    text: str,
    requirement_id: str = "REQ-001",
    source_document_id: str = "DOC-001",
) -> Requirement:
    """
    Extract a lightweight structured requirement from a contract,
    policy, or regulatory sentence.

    This is the rule-based baseline for the project.
    Later, NLP models can extend these rules.
    """

    lower = text.lower()

    actor: Optional[str] = None
    action: Optional[str] = None
    obj: Optional[str] = None
    recipient: Optional[str] = None
    authorization: Optional[str] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    unit: Optional[str] = None
    operator: Optional[str] = None
    deadline: Optional[str] = None
    obligation_type: Optional[str] = None
    exception: Optional[str] = None
    eligibility_logic: Optional[str] = None

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
        r"\b(?:to|with)\s+(?:the\s+)?"
        r"([a-zA-Z][a-zA-Z\s-]*?)"
        r"(?=\s+(?:without|with|if|when|unless|provided that)\b|[.,;]|$)",
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
        r"\b(?:within|after)\s+"
        r"(\d+(?:\.\d+)?)\s+"
        r"(day|days|month|months|year|years)\b",
        lower,
    )

    if deadline_match:
        deadline = (
            f"{deadline_match.group(1)} "
            f"{deadline_match.group(2)}"
        )

    # ---------------------------------------------------------
    # Threshold + unit + operator
    # ---------------------------------------------------------

    threshold, unit = _extract_threshold(text)

    operator = _extract_operator(text)

    # 'within 30 days' represents a deadline rather than
    # a >= comparison.
    if re.search(r"\bwithin\b", lower):
        operator = "<="

    # ---------------------------------------------------------
    # Obligation type
    # ---------------------------------------------------------

    # Restrictions must be checked before ordinary permission.
    if re.search(r"\b(must not|shall not|may not|cannot|can not)\b", lower):
        obligation_type = "PROHIBITION"

    elif re.search(r"\bmay only\b", lower):
        obligation_type = "RESTRICTED_PERMISSION"

    elif re.search(r"\b(may|can|permitted|allowed)\b", lower):
        obligation_type = "PERMISSION"

    elif re.search(r"\b(must|shall|required)\b", lower):
        obligation_type = "OBLIGATION"

    # ---------------------------------------------------------
    # Condition
    # ---------------------------------------------------------

    condition_match = re.search(
        r"\b(?:if|when|provided that)\b(.+?)(?:\.|$)",
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

    # ---------------------------------------------------------
    # Eligibility logic
    # ---------------------------------------------------------

    if re.search(r"\b(and|both)\b", lower):
        eligibility_logic = "AND"

    elif re.search(r"\b(or|either)\b", lower):
        eligibility_logic = "OR"

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
        exception=exception,
        eligibility_logic=eligibility_logic,
        operator=operator,
        threshold=threshold,
        unit=unit,
        deadline=deadline,
        source_text=text,
    )
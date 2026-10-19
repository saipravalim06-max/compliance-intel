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


def _number_pattern() -> str:
    """Build a regex pattern for supported number words and digits."""
    words = "|".join(
        re.escape(word)
        for word in sorted(NUMBER_WORDS, key=len, reverse=True)
    )
    return rf"(?:\d[\d,]*(?:\.\d+)?|{words})"


def _convert_number(value: str) -> Optional[float]:
    """Convert a numeric string or supported number word into a float."""
    value = value.strip().lower()

    if value in NUMBER_WORDS:
        return float(NUMBER_WORDS[value])

    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _extract_number(text: str) -> Optional[float]:
    """
    Extract a number from text.

    Supports examples such as:
        30
        30.5
        2,000,000
        thirty
        thirty (30)
        USD 2,000,000
    """

    # Prefer the explicit numeric value in expressions such as
    # "thirty (30)".
    parenthetical_match = re.search(
        r"\(\s*(\d[\d,]*(?:\.\d+)?)\s*\)",
        text,
    )

    if parenthetical_match:
        return _convert_number(parenthetical_match.group(1))

    # Prefer currency amounts when present.
    currency_match = re.search(
        r"(?:\bUSD\b|US\$|\$)\s*(\d[\d,]*(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )

    if currency_match:
        return _convert_number(currency_match.group(1))

    # Extract a numeric value, including comma separators.
    digit_match = re.search(r"\b\d[\d,]*(?:\.\d+)?\b", text)

    if digit_match:
        return _convert_number(digit_match.group())

    # Fall back to supported number words.
    lower = text.lower()

    for word in sorted(NUMBER_WORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(word)}\b", lower):
            return float(NUMBER_WORDS[word])

    return None


def _extract_unit(text: str) -> Optional[str]:
    """
    Extract and normalize a measurement unit.

    Examples:
        days -> day
        months -> month
        USD 2,000,000 -> usd
        20% -> percent
    """

    lower = text.lower()

    # Check currency first so an amount such as USD 2,000,000
    # is not confused with another measurement.
    if re.search(r"\b(?:usd|us dollars?)\b|us\$|\$", lower):
        return "usd"

    unit_match = re.search(
        r"\b(days?|weeks?|months?|years?|employees?|percent)\b|%",
        lower,
    )

    if not unit_match:
        return None

    unit = unit_match.group().lower()

    if unit == "%":
        return "percent"

    if unit.endswith("s"):
        return unit[:-1]

    return unit


def _extract_operator(text: str) -> Optional[str]:
    """
    Extract a comparison operator from requirement wording.

    Examples:
        at least 30 days -> >=
        no less than 15 days -> >=
        minimum coverage of USD 2,000,000 -> >=
        not capped below 12 months -> >=
        at most 30 days -> <=
        no more than 10 employees -> <=
        more than 30 days -> >
        less than 15 days -> <
    """

    lower = text.lower()

    # Check lower-bound expressions before generic "less than"
    # expressions so that "no less than" is handled correctly.
    minimum_patterns = [
        r"\bat least\b",
        r"\bno less than\b",
        r"\bnot less than\b",
        r"\bminimum\b",
        r"\bnot below\b",
        r"\b(?:should|must|shall)\s+not\s+(?:be\s+)?capped\s+below\b",
        r"\bnot\s+(?:be\s+)?capped\s+below\b",
    ]

    maximum_patterns = [
        r"\bat most\b",
        r"\bno more than\b",
        r"\bnot more than\b",
        r"\bmaximum\b",
        r"\bup to\b",
        r"\bnot above\b",
    ]

    greater_patterns = [
        r"\bmore than\b",
        r"\bgreater than\b",
        r"\bover\b",
    ]

    less_patterns = [
        r"\bless than\b",
        r"\bfewer than\b",
        r"\bunder\b",
        r"\bbelow\b",
    ]

    if any(re.search(p, lower) for p in minimum_patterns):
        return ">="

    if any(re.search(p, lower) for p in maximum_patterns):
        return "<="

    if any(re.search(p, lower) for p in greater_patterns):
        return ">"

    if any(re.search(p, lower) for p in less_patterns):
        return "<"

    return None


def _extract_threshold(text: str):
    """
    Extract a numeric threshold and its unit.

    Supports:
        thirty (30) calendar days -> (30, day)
        no less than fifteen days -> (15, day)
        twelve (12) months of fees -> (12, month)
        USD 2,000,000 per incident -> (2000000, usd)
        minimum coverage of USD 1,000,000 -> (1000000, usd)
        20 percent -> (20, percent)
        20% -> (20, percent)
    """

    lower = text.lower()

    # Currency amounts must be handled separately because the amount
    # may be followed by "per incident", "per occurrence", etc.
    currency_match = re.search(
        r"(?:\busd\b|us\$|\$)\s*"
        r"(?P<amount>\d[\d,]*(?:\.\d+)?)",
        lower,
    )

    if currency_match:
        amount = _convert_number(currency_match.group("amount"))
        return amount, "usd"

    number_core = _number_pattern()

    # Match durations, counts, and word-plus-parenthetical-number
    # expressions such as "thirty (30) calendar days".
    duration_match = re.search(
        rf"(?P<number>{number_core})"
        rf"(?:\s*\(\s*(?P<paren>\d[\d,]*(?:\.\d+)?)\s*\))?"
        rf"\s*(?:calendar\s+)?"
        rf"(?P<unit>days?|weeks?|months?|years?|employees?|percent)\b",
        lower,
    )

    if duration_match:
        # Prefer the explicit digits when the text contains both
        # a number word and a parenthetical number.
        value_text = (
            duration_match.group("paren")
            or duration_match.group("number")
        )

        value = _convert_number(value_text)
        unit = duration_match.group("unit")

        if unit.endswith("s"):
            unit = unit[:-1]

        return value, unit

    # Percent signs need separate handling because "%" is not a word
    # and should not be followed by a word boundary.
    percent_match = re.search(
        rf"(?P<number>{number_core})"
        rf"(?:\s*\(\s*(?P<paren>\d[\d,]*(?:\.\d+)?)\s*\))?"
        rf"\s*%",
        lower,
    )

    if percent_match:
        value_text = (
            percent_match.group("paren")
            or percent_match.group("number")
        )

        return _convert_number(value_text), "percent"

    return None, None


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
        r"(\d[\d,]*(?:\.\d+)?)\s+"
        r"(day|days|month|months|year|years)\b",
        lower,
    )

    if deadline_match:
        deadline = (
            f"{deadline_match.group(1).replace(',', '')} "
            f"{deadline_match.group(2)}"
        )

    # ---------------------------------------------------------
    # Threshold + unit + operator
    # ---------------------------------------------------------

    threshold, unit = _extract_threshold(text)
    operator = _extract_operator(text)

    # "Within 30 days" is generally a deadline, not a minimum.
    # Do not overwrite a deadline's comparison if a different
    # explicit comparison phrase is present.
    if re.search(r"\bwithin\b", lower):
        operator = "<="

    # ---------------------------------------------------------
    # Obligation type
    # ---------------------------------------------------------

    if re.search(
        r"\b(must not|shall not|may not|cannot|can not)\b",
        lower,
    ):
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
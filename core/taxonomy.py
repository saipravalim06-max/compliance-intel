"""
core/taxonomy.py — the ONE shared vocabulary.

Everything that flows through the engine (contract clauses, company policies,
state regulations, company profiles) is described with these enums. Teammates'
raw values (e.g. Karnataka's "=" operator, Tamil Nadu's "Startup eligibility"
domain) are mapped to these through the crosswalk dicts at the bottom, so no
module ever compares free-text categories.
"""
from enum import Enum


class SourceType(str, Enum):
    CONTRACT = "CONTRACT"
    COMPANY_POLICY = "COMPANY_POLICY"
    STATE_REGULATION = "STATE_REGULATION"


# ---- Labels -----------------------------------------------------------------
class ConflictLabel(str, Enum):
    """Module 2: contract clause vs company policy."""
    CONFLICT = "CONFLICT"
    NO_CONFLICT = "NO_CONFLICT"
    PARTIAL_CONFLICT = "PARTIAL_CONFLICT"
    UNCERTAIN = "UNCERTAIN"


class FitVerdict(str, Enum):
    """Module 1: one state requirement evaluated against a company profile.
    UNKNOWN means the profile lacks a needed fact — it is NOT a failure and
    must never be counted against a state."""
    APPLIES = "APPLIES"
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    POTENTIAL = "POTENTIAL"
    UNKNOWN = "UNKNOWN"
    INFO = "INFO"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


# ---- Requirement vocabulary -------------------------------------------------
class Operator(str, Enum):
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"          # "at most", "within", "not exceed", "<="
    GT = "GT"
    GTE = "GTE"          # "at least", "no less than", "minimum", ">="
    IN = "IN"
    REQUIRED = "REQUIRED"
    NOT_ALLOWED = "NOT_ALLOWED"
    CONDITIONAL = "CONDITIONAL"


class Unit(str, Enum):
    INR = "INR"          # always stored in absolute rupees (1 crore = 10,000,000)
    USD = "USD"
    PERCENT = "PERCENT"
    HOURS = "HOURS"
    DAYS = "DAYS"
    BUSINESS_DAYS = "BUSINESS_DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    MONTHS_OF_FEES = "MONTHS_OF_FEES"   # liability caps expressed as "12 months of fees"
    YEARS = "YEARS"
    EMPLOYEES = "EMPLOYEES"
    COUNT = "COUNT"


class ObligationType(str, Enum):
    """Modality of a clause. Order of precedence when several words appear:
    PROHIBITION > RESTRICTED_PERMISSION > OBLIGATION > PERMISSION."""
    PROHIBITION = "PROHIBITION"                    # must not / shall not / may not
    RESTRICTED_PERMISSION = "RESTRICTED_PERMISSION"  # may only / only ... may
    OBLIGATION = "OBLIGATION"                      # must / shall / required
    PERMISSION = "PERMISSION"                      # may / can / entitled to


class RequirementType(str, Enum):
    ELIGIBILITY = "ELIGIBILITY"
    BENEFIT = "BENEFIT"
    OBLIGATION = "OBLIGATION"
    RESTRICTION = "RESTRICTION"
    EXEMPTION = "EXEMPTION"
    SUPPORT = "SUPPORT"
    RECOGNITION = "RECOGNITION"
    ALLOCATION = "ALLOCATION"
    METADATA = "METADATA"


class StateDomain(str, Enum):
    ELIGIBILITY = "ELIGIBILITY"
    FUNDING = "FUNDING"
    TAX_INCENTIVE = "TAX_INCENTIVE"
    IP = "IP"
    PROCUREMENT = "PROCUREMENT"
    INCLUSION = "INCLUSION"                    # women, SC/ST, rural, social
    INFRASTRUCTURE = "INFRASTRUCTURE"
    OPERATING_SUPPORT = "OPERATING_SUPPORT"    # mentoring, marketing, quality, recognition
    MANUFACTURING = "MANUFACTURING"
    REGULATORY_COMPLIANCE = "REGULATORY_COMPLIANCE"  # labour, approvals, sandbox  <- friction side
    SECTOR_FOCUS = "SECTOR_FOCUS"              # circular economy, societal impact
    METADATA = "METADATA"


# ---- Crosswalks from teammates' raw values (keys are lower-case) ------------
STATE_DOMAIN_MAP = {
    # Tamil Nadu
    "startup eligibility": StateDomain.ELIGIBILITY, "startup recognition": StateDomain.OPERATING_SUPPORT,
    "funding": StateDomain.FUNDING, "inclusion": StateDomain.INCLUSION,
    "women entrepreneurship": StateDomain.INCLUSION, "government procurement": StateDomain.PROCUREMENT,
    "manufacturing": StateDomain.MANUFACTURING, "intellectual property": StateDomain.IP,
    "compliance": StateDomain.REGULATORY_COMPLIANCE, "startup support": StateDomain.OPERATING_SUPPORT,
    "infrastructure": StateDomain.INFRASTRUCTURE, "policy metadata": StateDomain.METADATA,
    # Karnataka
    "eligibility": StateDomain.ELIGIBILITY, "restriction": StateDomain.ELIGIBILITY,
    "definition": StateDomain.METADATA, "ip": StateDomain.IP, "procurement": StateDomain.PROCUREMENT,
    "rural": StateDomain.INCLUSION, "societal impact": StateDomain.SECTOR_FOCUS,
    "circular economy": StateDomain.SECTOR_FOCUS, "tax incentive": StateDomain.TAX_INCENTIVE,
    "quality": StateDomain.OPERATING_SUPPORT, "marketing": StateDomain.OPERATING_SUPPORT,
    "regulatory sandbox": StateDomain.REGULATORY_COMPLIANCE,
}

STATE_TYPE_MAP = {
    "eligibility": RequirementType.ELIGIBILITY, "benefit": RequirementType.BENEFIT,
    "support": RequirementType.SUPPORT, "infrastructure support": RequirementType.SUPPORT,
    "procurement": RequirementType.OBLIGATION, "procurement benefit": RequirementType.BENEFIT,
    "allocation": RequirementType.ALLOCATION, "target": RequirementType.ALLOCATION,
    "budget": RequirementType.METADATA, "programme limit": RequirementType.RESTRICTION,
    "funding condition": RequirementType.OBLIGATION, "recognition": RequirementType.RECOGNITION,
    "exemption": RequirementType.EXEMPTION, "policy metadata": RequirementType.METADATA,
}

OPERATOR_MAP = {
    "<=": Operator.LTE, "<": Operator.LT, ">=": Operator.GTE, ">": Operator.GT,
    "=": Operator.EQ, "==": Operator.EQ, "!=": Operator.NE, "in": Operator.IN,
    "required": Operator.REQUIRED, "not_allowed": Operator.NOT_ALLOWED,
    "conditional": Operator.CONDITIONAL,
    # KA-ELIG-001 has a registration requirement typed into the operator cell
    "karnataka startup cell registration": Operator.REQUIRED,
}

UNIT_MAP = {
    "inr": Unit.INR, "lakh": Unit.INR, "crore": Unit.INR, "rs": Unit.INR,
    "%": Unit.PERCENT, "percent": Unit.PERCENT,
    "days": Unit.DAYS, "day": Unit.DAYS, "months": Unit.MONTHS, "month": Unit.MONTHS,
    "years": Unit.YEARS, "year": Unit.YEARS,
    "employees": Unit.EMPLOYEES, "interns": Unit.COUNT,
}

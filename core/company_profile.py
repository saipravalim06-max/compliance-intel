"""
core/company_profile.py

The ONE company profile used by every module. It is the union of the facts in
Sreeja's Tamil Nadu and Karnataka profile sheets plus the original engine fields,
so every state's rules are evaluated against the SAME set of facts.

Tri-state facts: True / False / None.  None means UNKNOWN (not supplied) and
must produce an UNKNOWN verdict, never a FAIL, in Module 1.
"""
import json
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from typing import Dict, List, Optional


class Industry(str, Enum):
    SOFTWARE_SAAS = "software_saas"
    FINTECH = "fintech"
    HEALTHTECH = "healthtech"
    ECOMMERCE = "ecommerce"
    MANUFACTURING = "manufacturing"
    EDTECH = "edtech"
    GREENTECH = "greentech"
    AGRITECH = "agritech"
    FOOD_PROCESSING = "food_processing"
    AUTO_COMPONENTS = "auto_components"
    OTHER = "other"


class DataSensitivity(str, Enum):
    NONE = "none"
    BASIC_PII = "basic_pii"
    FINANCIAL = "financial"
    HEALTH = "health"
    CHILDREN = "children"


@dataclass
class CompanyProfile:
    # --- identity ---
    company_name: str
    industry: Industry = Industry.OTHER
    sector_description: Optional[str] = None      # e.g. "AI + Agriculture"
    legal_form: Optional[str] = None              # "Private Limited", "LLP", ...
    founded_year: Optional[int] = None
    age_years: Optional[float] = None

    # --- size ---
    annual_turnover_inr: Optional[float] = None   # absolute rupees (4 crore = 40_000_000)
    employee_count: Optional[int] = None

    # --- eligibility facts used by state rules (None = UNKNOWN) ---
    is_women_led: Optional[bool] = None
    women_ownership_pct: Optional[float] = None
    has_rural_impact: Optional[bool] = None
    is_manufacturing: Optional[bool] = None
    is_sc_st_led: Optional[bool] = None
    is_trans_or_differently_abled_led: Optional[bool] = None
    has_patent: Optional[bool] = None
    patent_details: Optional[str] = None
    has_innovation: Optional[bool] = None
    has_scalable_model: Optional[bool] = None
    formed_by_split_or_reconstruction: Optional[bool] = None
    is_social_entrepreneur: Optional[bool] = None
    grand_challenge_winner: Optional[bool] = None
    located_beyond_bengaluru_urban: Optional[bool] = None
    incubated_in_govt_supported_incubator: Optional[bool] = None
    intl_marketing_spend_inr: Optional[float] = None
    has_quality_certifications: Optional[bool] = None
    is_green_tech: Optional[bool] = None
    is_first_time_founder: Optional[bool] = None

    # --- operations / data (Modules 2 & 3) ---
    is_remote_first: Optional[bool] = None
    handles_cross_border_data: Optional[bool] = None
    data_sensitivity: Optional[DataSensitivity] = None
    environmental_footprint_notes: str = ""

    # --- facts that only make sense per state, e.g.
    # {"Karnataka": {"incorporated_in_state": True, "recognized_by_state_startup_agency": True}}
    state_context: Dict[str, Dict[str, Optional[bool]]] = field(default_factory=dict)

    # --- documents / free text ---
    internal_policy_doc_paths: List[str] = field(default_factory=list)
    operating_in_states: List[str] = field(default_factory=list)
    self_description: str = ""

    # --- provenance: be explicit about anything assumed or fictional ---
    is_demo_profile: bool = False
    assumptions: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ helpers
    def unknown_fields(self) -> List[str]:
        skip = {"company_name", "state_context", "internal_policy_doc_paths", "operating_in_states",
                "self_description", "assumptions", "is_demo_profile", "environmental_footprint_notes"}
        return [f.name for f in fields(self) if f.name not in skip and getattr(self, f.name) is None]

    def to_matching_text(self) -> str:
        """Flatten known facts into text for semantic matching. Unknowns are skipped."""
        pairs = [
            ("Industry", self.industry.value if self.industry else None),
            ("Sector", self.sector_description), ("Legal form", self.legal_form),
            ("Age (years)", self.age_years), ("Employees", self.employee_count),
            ("Annual turnover (INR)", self.annual_turnover_inr),
            ("Women-led", self.is_women_led), ("Rural impact", self.has_rural_impact),
            ("Manufacturing", self.is_manufacturing), ("Holds patent", self.has_patent),
            ("Data sensitivity", self.data_sensitivity.value if self.data_sensitivity else None),
            ("Cross-border data", self.handles_cross_border_data),
        ]
        lines = [f"{k}: {v}" for k, v in pairs if v is not None]
        if self.self_description:
            lines.append(self.self_description)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["industry"] = self.industry.value if self.industry else None
        d["data_sensitivity"] = self.data_sensitivity.value if self.data_sensitivity else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CompanyProfile":
        d = dict(d)
        if d.get("industry"):
            d["industry"] = Industry(d["industry"])
        if d.get("data_sensitivity"):
            d["data_sensitivity"] = DataSensitivity(d["data_sensitivity"])
        known = {f.name for f in fields(cls)}
        unexpected = set(d) - known
        if unexpected:
            raise ValueError(f"Unknown profile fields: {sorted(unexpected)}")
        return cls(**d)

    @classmethod
    def load(cls, path: str) -> "CompanyProfile":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

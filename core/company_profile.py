"""
core/company_profile.py

The Company Profile is the single data model that every module (state-fit
recommender, contract checker, drift monitor) reads from. Build this first
and get its shape right before building anything else — it's the thing that
makes the three modules feel like one product instead of three tools.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class Industry(str, Enum):
    SOFTWARE_SAAS = "software_saas"
    FINTECH = "fintech"
    HEALTHTECH = "healthtech"
    ECOMMERCE = "ecommerce"
    MANUFACTURING = "manufacturing"
    EDTECH = "edtech"
    GREENTECH = "greentech"
    OTHER = "other"


class DataSensitivity(str, Enum):
    """How sensitive the data this company handles is — drives which
    regulatory clauses (data privacy, breach notification, etc.) matter most
    when matching against state/jurisdiction regulations."""
    NONE = "none"
    BASIC_PII = "basic_pii"            # names, emails, addresses
    FINANCIAL = "financial"             # payment data, bank details
    HEALTH = "health"                   # medical/health records
    CHILDREN = "children"               # data belonging to minors


@dataclass
class CompanyProfile:
    # --- Identity ---
    company_name: str
    industry: Industry
    founded_year: Optional[int] = None

    # --- Operational footprint (drives which regulatory clauses are relevant) ---
    employee_count: int = 0
    is_remote_first: bool = False
    data_sensitivity: DataSensitivity = DataSensitivity.BASIC_PII
    handles_cross_border_data: bool = False
    environmental_footprint_notes: str = ""  # e.g. "manufacturing, heavy water use"

    # --- Category flags that matter for STATE INCENTIVE matching ---
    is_women_led: bool = False
    is_green_tech: bool = False
    is_first_time_founder: bool = False

    # --- Document references (paths to uploaded files, not raw text) ---
    internal_policy_doc_paths: List[str] = field(default_factory=list)
    operating_in_states: List[str] = field(default_factory=list)  # once chosen

    # --- Free-text self-description (fed into semantic matching directly) ---
    self_description: str = ""  # e.g. "We process customer payment data and
                                 # employ 40 people, 10 remote across states."

    def to_matching_text(self) -> str:
        """
        Flattens the structured profile into a single text blob for semantic
        embedding against regulatory/policy text. Keep this function as the
        ONE place that defines how structured fields become matchable text —
        every module should call this rather than rolling its own version.
        """
        parts = [
            f"Industry: {self.industry.value}",
            f"Employee count: {self.employee_count}",
            f"Data sensitivity: {self.data_sensitivity.value}",
            f"Cross-border data handling: {self.handles_cross_border_data}",
            f"Women-led: {self.is_women_led}",
            f"Green/sustainability focused: {self.is_green_tech}",
            self.self_description,
        ]
        return "\n".join(p for p in parts if p)


if __name__ == "__main__":
    example = CompanyProfile(
        company_name="Acme Analytics Pvt Ltd",
        industry=Industry.SOFTWARE_SAAS,
        employee_count=40,
        data_sensitivity=DataSensitivity.FINANCIAL,
        handles_cross_border_data=True,
        is_women_led=True,
        self_description=(
            "We build analytics software for e-commerce clients and process "
            "customer payment data. Most of our team works remotely."
        ),
    )
    print(example.to_matching_text())

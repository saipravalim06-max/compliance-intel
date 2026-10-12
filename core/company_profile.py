"""
core/company_profile.py

The Company Profile is the shared company context used by:
- state-fit analysis
- contract checking
- regulatory drift monitoring

The profile should contain structured facts that can be evaluated
against regulatory requirements, plus a free-text description for
semantic matching.
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
    NONE = "none"
    BASIC_PII = "basic_pii"
    FINANCIAL = "financial"
    HEALTH = "health"
    CHILDREN = "children"


@dataclass
class CompanyProfile:
    # ---------------------------------------------------------
    # Identity
    # ---------------------------------------------------------
    company_name: str
    industry: Industry
    founded_year: Optional[int] = None

    # ---------------------------------------------------------
    # Operational footprint
    # ---------------------------------------------------------
    employee_count: int = 0
    is_remote_first: bool = False
    data_sensitivity: DataSensitivity = DataSensitivity.BASIC_PII
    handles_cross_border_data: bool = False
    environmental_footprint_notes: str = ""

    # ---------------------------------------------------------
    # Category / eligibility flags
    # ---------------------------------------------------------
    is_women_led: bool = False
    is_green_tech: bool = False
    is_first_time_founder: bool = False

    # ---------------------------------------------------------
    # Regulatory / business facts
    #
    # These fields allow deterministic evaluation of requirements
    # instead of relying only on semantic similarity.
    # ---------------------------------------------------------
    annual_revenue: Optional[float] = None
    annual_revenue_unit: Optional[str] = None

    annual_investment: Optional[float] = None
    annual_investment_unit: Optional[str] = None

    registered_capital: Optional[float] = None
    registered_capital_unit: Optional[str] = None

    startup_status: Optional[bool] = None
    startup_registration_status: Optional[str] = None

    business_age_years: Optional[float] = None

    has_manufacturing_operations: bool = False
    has_export_operations: bool = False
    has_import_operations: bool = False

    # ---------------------------------------------------------
    # Location / jurisdiction
    # ---------------------------------------------------------
    operating_states: List[str] = field(default_factory=list)

    registered_state: Optional[str] = None

    # ---------------------------------------------------------
    # Document references
    # ---------------------------------------------------------
    internal_policy_doc_paths: List[str] = field(default_factory=list)

    # ---------------------------------------------------------
    # Free-text company description
    # ---------------------------------------------------------
    self_description: str = ""

    def to_matching_text(self) -> str:
        """
        Convert structured company information into text for
        semantic matching against regulatory and policy text.

        Deterministic eligibility checks should use the structured
        fields directly rather than relying only on this text.
        """

        parts = [
            f"Company: {self.company_name}",
            f"Industry: {self.industry.value}",
            f"Employee count: {self.employee_count}",
            f"Data sensitivity: {self.data_sensitivity.value}",
            f"Cross-border data handling: {self.handles_cross_border_data}",
            f"Women-led: {self.is_women_led}",
            f"Green/sustainability focused: {self.is_green_tech}",
            f"First-time founder: {self.is_first_time_founder}",
            f"Startup status: {self.startup_status}",
            f"Manufacturing operations: {self.has_manufacturing_operations}",
            f"Export operations: {self.has_export_operations}",
            f"Import operations: {self.has_import_operations}",
        ]

        if self.annual_revenue is not None:
            parts.append(
                f"Annual revenue: {self.annual_revenue} "
                f"{self.annual_revenue_unit or ''}".strip()
            )

        if self.annual_investment is not None:
            parts.append(
                f"Annual investment: {self.annual_investment} "
                f"{self.annual_investment_unit or ''}".strip()
            )

        if self.registered_capital is not None:
            parts.append(
                f"Registered capital: {self.registered_capital} "
                f"{self.registered_capital_unit or ''}".strip()
            )

        if self.business_age_years is not None:
            parts.append(
                f"Business age: {self.business_age_years} years"
            )

        if self.operating_states:
            parts.append(
                f"Operating states: {', '.join(self.operating_states)}"
            )

        if self.registered_state:
            parts.append(
                f"Registered state: {self.registered_state}"
            )

        if self.environmental_footprint_notes:
            parts.append(
                f"Environmental footprint: "
                f"{self.environmental_footprint_notes}"
            )

        if self.self_description:
            parts.append(self.self_description)

        return "\n".join(parts)


if __name__ == "__main__":
    example = CompanyProfile(
        company_name="AgriVision Technologies Pvt Ltd",
        industry=Industry.SOFTWARE_SAAS,
        founded_year=2022,
        employee_count=40,
        is_remote_first=True,
        data_sensitivity=DataSensitivity.FINANCIAL,
        handles_cross_border_data=True,
        is_women_led=True,
        is_green_tech=False,
        is_first_time_founder=True,
        annual_revenue=2.5,
        annual_revenue_unit="crore",
        annual_investment=1.2,
        annual_investment_unit="crore",
        startup_status=True,
        startup_registration_status="registered",
        business_age_years=4,
        has_manufacturing_operations=False,
        has_export_operations=True,
        has_import_operations=False,
        operating_states=["Tamil Nadu", "Karnataka"],
        registered_state="Tamil Nadu",
        self_description=(
            "We build agricultural analytics software for farms and "
            "agribusinesses. We process customer payment data and "
            "export software services."
        ),
    )

    print(example.to_matching_text())
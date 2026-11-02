import unittest

from core.schemas import Requirement
from core.conflict import detect_conflict
from core.quantities import find_quantities, detect_kind




def make_requirement(
    requirement_id,
    text,
    threshold=None,
    unit=None,
    operator=None,
):
    quantities = []

    for q in find_quantities(text):
        kind = detect_kind(text, q)
        if kind:
            quantities.append({
                "value": q.value,
                "unit": q.unit.value,
                "bound": q.bound,
                "per": q.per,
                "kind": kind,
                "raw": q.raw,
                "inferred": q.inferred,
            })

    return Requirement(
        requirement_id=requirement_id,
        source_document_id=requirement_id,
        source_text=text,
        threshold=str(threshold) if threshold is not None else None,
        unit=unit,
        operator=operator,
        quantities=quantities,
    )




class TestConflictRules(unittest.TestCase):

    def test_short_termination_notice_is_conflict(self):
        contract = make_requirement(
            "CON-001",
            "Either party may terminate for convenience with 7 days notice.",
            threshold=7,
            unit="day",
        )
        policy = make_requirement(
            "POL-05-001",
            "Termination for convenience requires at least 30 days notice.",
            threshold=30,
            unit="day",
            operator=">=",
        )

        result = detect_conflict(contract, policy)
        self.assertTrue(result["conflict"])
        self.assertEqual(result["severity"], "HIGH")

    def test_thirty_day_notice_is_compatible(self):
        contract = make_requirement(
            "CON-002",
            "Either party may terminate for convenience with 30 days notice.",
            threshold=30,
            unit="day",
        )
        policy = make_requirement(
            "POL-05-001",
            "Termination for convenience requires at least 30 days notice.",
            threshold=30,
            unit="day",
            operator=">=",
        )

        result = detect_conflict(contract, policy)
        self.assertFalse(result["conflict"])

    def test_short_liability_cap_is_conflict(self):
        contract = make_requirement(
            "CON-003",
            "Liability is capped at an amount equal to 6 months of fees.",
            threshold=6,
            unit="month",
        )
        policy = make_requirement(
            "POL-06-001",
            "Liability must not be capped below 12 months of fees.",
            threshold=12,
            unit="month",
            operator=">=",
        )

        result = detect_conflict(contract, policy)
        self.assertTrue(result["conflict"])

    def test_twelve_month_liability_cap_is_compatible(self):
        contract = make_requirement(
            "CON-004",
            "Liability is capped at an amount equal to 12 months of fees.",
            threshold=12,
            unit="month",
        )
        policy = make_requirement(
            "POL-06-001",
            "Liability must not be capped below 12 months of fees.",
            threshold=12,
            unit="month",
            operator=">=",
        )

        result = detect_conflict(contract, policy)
        self.assertFalse(result["conflict"])

    def test_insufficient_cyber_insurance_is_conflict(self):
        contract = make_requirement(
            "CON-005",
            "Vendor maintains cyber insurance of USD 1000000 per incident.",
            threshold=1_000_000,
            unit="usd",
        )
        policy = make_requirement(
            "POL-10-001",
            "Vendors processing company data need cyber insurance coverage of USD 2000000.",
            threshold=2_000_000,
            unit="usd",
            operator=">=",
        )

        result = detect_conflict(contract, policy)
        self.assertTrue(result["conflict"])

    def test_sufficient_cyber_insurance_is_compatible(self):
        contract = make_requirement(
            "CON-006",
            "Vendor maintains cyber insurance of USD 2000000 per incident.",
            threshold=2_000_000,
            unit="usd",
        )
        policy = make_requirement(
            "POL-10-001",
            "Vendors processing company data need USD 2000000 cyber coverage.",
            threshold=2_000_000,
            unit="usd",
            operator=">=",
        )

        result = detect_conflict(contract, policy)
        self.assertFalse(result["conflict"])

    
    def test_policy_prohibition_conflicts_with_contract_permission(self):
        contract = Requirement(
            requirement_id="CON-MOD-001",
            source_document_id="CON-MOD-001",
            source_text="The vendor may disclose customer data to third parties.",
            action="disclose",
            object="customer data",
            obligation_type="PERMISSION",
        )

        policy = Requirement(
            requirement_id="POL-MOD-001",
            source_document_id="POL-MOD-001",
            source_text=(
                "The vendor must not disclose customer data to third parties "
                "without prior written authorization."
            ),
            action="disclose",
            object="customer data",
            obligation_type="PROHIBITION",
            authorization="REQUIRED",
        )

        result = detect_conflict(contract, policy)

        self.assertTrue(result["conflict"])
        self.assertEqual(result["label"], "CONFLICT")
        self.assertIn("MODALITY", result["rules"])



if __name__ == "__main__":
    unittest.main(verbosity=2)
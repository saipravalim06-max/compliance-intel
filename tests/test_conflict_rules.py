import unittest

from core.schemas import Requirement
from core.conflict import detect_conflict


def make_requirement(
    requirement_id,
    text,
    threshold=None,
    unit=None,
    operator=None,
):
    return Requirement(
        requirement_id=requirement_id,
        source_document_id=requirement_id,
        source_text=text,
        threshold=threshold,
        unit=unit,
        operator=operator,
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
            "Vendors processing company data need USD 2000000 cyber coverage.",
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
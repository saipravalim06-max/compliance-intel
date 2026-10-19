from core.extraction import extract_requirement

examples = [
    (
        "Termination for convenience requires a minimum notice period "
        "of thirty (30) calendar days.",
        "30-day notice requirement",
    ),
    (
        "A counterparty's total liability should not be capped below "
        "an amount equal to twelve (12) months of fees.",
        "12-month liability benchmark",
    ),
    (
        "Vendors processing company data must maintain cyber liability "
        "insurance with a minimum coverage of USD 2,000,000 per incident.",
        "Cyber insurance minimum",
    ),
    (
        "The breaching party has a cure period of no less than "
        "fifteen (15) calendar days.",
        "15-day cure period",
    ),
]

for text, label in examples:
    result = extract_requirement(text)

    print(f"\n--- {label} ---")
    print("Text:", text)
    print("Threshold:", result.threshold)
    print("Unit:", result.unit)
    print("Operator:", result.operator)
    print("Deadline:", result.deadline)


import unittest

from core.extraction import extract_requirement


class TestPolicyRequirementExtraction(unittest.TestCase):

    def test_termination_minimum(self):
        result = extract_requirement(
            "Termination for convenience requires a minimum notice "
            "period of thirty (30) calendar days."
        )
        self.assertEqual(result.threshold, 30.0)
        self.assertEqual(result.unit, "day")
        self.assertEqual(result.operator, ">=")

    def test_liability_minimum(self):
        result = extract_requirement(
            "A counterparty's total liability should not be capped below "
            "an amount equal to twelve (12) months of fees."
        )
        self.assertEqual(result.threshold, 12.0)
        self.assertEqual(result.unit, "month")
        self.assertEqual(result.operator, ">=")

    def test_cyber_insurance_minimum(self):
        result = extract_requirement(
            "Vendors processing company data must maintain cyber liability "
            "insurance with a minimum coverage of USD 2,000,000 per incident."
        )
        self.assertEqual(result.threshold, 2_000_000.0)
        self.assertEqual(result.unit, "usd")
        self.assertEqual(result.operator, ">=")

    def test_cure_period_minimum(self):
        result = extract_requirement(
            "The breaching party has a cure period of no less than "
            "fifteen (15) calendar days."
        )
        self.assertEqual(result.threshold, 15.0)
        self.assertEqual(result.unit, "day")
        self.assertEqual(result.operator, ">=")


if __name__ == "__main__":
    unittest.main(verbosity=2)
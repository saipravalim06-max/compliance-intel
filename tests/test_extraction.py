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
        self.assertEqual(result.threshold_value, 30.0)
        self.assertEqual(result.unit, "DAYS")
        self.assertEqual(result.operator, "GTE")

    def test_liability_minimum(self):
        result = extract_requirement(
            "A counterparty's total liability should not be capped below "
            "an amount equal to twelve (12) months of fees."
        )
        self.assertEqual(result.threshold_value, 12.0)
        self.assertEqual(result.unit, "MONTHS_OF_FEES")
        self.assertEqual(result.operator, "GTE")

    def test_cyber_insurance_minimum(self):
        result = extract_requirement(
            "Vendors processing company data must maintain cyber liability "
            "insurance with a minimum coverage of USD 2,000,000 per incident."
        )
        self.assertEqual(result.threshold_value, 2_000_000.0)
        self.assertEqual(result.unit, "USD")
        self.assertEqual(result.operator, "GTE")

    def test_cure_period_minimum(self):
        result = extract_requirement(
            "The breaching party has a cure period of no less than "
            "fifteen (15) calendar days."
        )
        self.assertEqual(result.threshold_value, 15.0)
        self.assertEqual(result.unit, "DAYS")
        self.assertEqual(result.operator, "GTE")

    
    def test_prior_written_notice_is_termination_notice(self):
        result = extract_requirement(
            "Either party may terminate for convenience with "
            "30 days prior written notice."
        )

        self.assertEqual(result.quantities[0]["value"], 30.0)
        self.assertEqual(
            result.quantities[0]["kind"], "TERMINATION_NOTICE"
        )

    def test_cure_duration_is_cure_period(self):
        result = extract_requirement(
            "The breaching party has 15 calendar days to cure the breach."
        )

        self.assertEqual(result.quantities[0]["value"], 15.0)
        self.assertEqual(result.quantities[0]["kind"], "CURE_PERIOD")

    def test_notice_and_cure_durations_are_classified_separately(self):
        result = extract_requirement(
            "Either party may terminate with 30 days prior written notice, "
            "but the breaching party must be given 15 calendar days to "
            "cure the breach before termination for cause."
        )

        by_value = {
            item["value"]: item["kind"]
            for item in result.quantities
        }

        self.assertEqual(by_value[30.0], "TERMINATION_NOTICE")
        self.assertEqual(by_value[15.0], "CURE_PERIOD")

    def test_prior_written_notice_is_termination_notice(self):
        result = extract_requirement(
            "Either party may terminate for convenience with "
            "30 days prior written notice."
        )
        self.assertEqual(
            result.quantities[0]["kind"], "TERMINATION_NOTICE"
        )

    def test_cure_duration_is_cure_period(self):
        result = extract_requirement(
            "The breaching party has 15 calendar days to cure the breach."
        )
        self.assertEqual(
            result.quantities[0]["kind"], "CURE_PERIOD"
        )

    def test_notice_and_cure_durations_are_classified_separately(self):
        result = extract_requirement(
            "Either party may terminate with 30 days prior written notice, "
            "but the breaching party must be given 15 calendar days to "
            "cure the breach before termination for cause."
        )
        by_value = {
            item["value"]: item["kind"]
            for item in result.quantities
        }
        self.assertEqual(by_value[30.0], "TERMINATION_NOTICE")
        self.assertEqual(by_value[15.0], "CURE_PERIOD")

    def test_authorization_required_when_consent_must_be_obtained_first(self):
        result = extract_requirement(
            "Operator shall not make any assignment of this Agreement "
            "unless there first shall have been obtained the written "
            "consent of Owner."
        )

        self.assertEqual(result.action, "assign")
        self.assertEqual(result.authorization, "REQUIRED")

if __name__ == "__main__":
    unittest.main(verbosity=2)
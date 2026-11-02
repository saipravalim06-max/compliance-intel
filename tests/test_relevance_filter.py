
from core.extraction import extract_requirement
from modules.contract_checker import _is_relevant_pair


def _pair(contract: str, policy: str) -> bool:
    return _is_relevant_pair(
        extract_requirement(contract),
        extract_requirement(policy),
    )


def test_termination_matches_termination():
    assert _pair(
        "The supplier may terminate this agreement with 7 days written notice.",
        "Suppliers must give at least 30 days written notice before terminating an agreement.",
    )


def test_disclosure_matches_disclosure():
    assert _pair(
        "The supplier may disclose customer data to third parties without prior written approval.",
        "Suppliers must obtain prior written approval before disclosing customer data to third parties.",
    )


def test_assignment_matches_assignment():
    assert _pair(
        "Neither party may assign this agreement without the other party's prior written consent.",
        "A party must obtain prior written consent before assigning an agreement.",
    )


def test_disclosure_does_not_match_assignment():
    assert not _pair(
        "The supplier may disclose customer data to third parties without prior written approval.",
        "A party must obtain prior written consent before assigning an agreement.",
    )


def test_assignment_does_not_match_disclosure():
    assert not _pair(
        "Neither party may assign this agreement without the other party's prior written consent.",
        "Suppliers must obtain prior written approval before disclosing customer data to third parties.",
    )


def test_payment_does_not_match_termination():
    assert not _pair(
        "The customer must pay valid invoices within 30 days.",
        "Suppliers must give at least 30 days written notice before terminating an agreement.",
    )


def test_missing_action_is_not_rejected_automatically():
    assert _pair(
        "The supplier must comply with all applicable requirements.",
        "Suppliers must obtain prior written approval before disclosing customer data to third parties.",
    )

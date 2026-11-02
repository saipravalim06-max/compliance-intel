
import pandas as pd
import pytest

from core.engine import Segment
from modules.contract_checker import check_clause_against_state_requirements


class FakeMatcher:
    """Deterministic matcher for unit tests."""

    def __init__(self, score=0.95):
        self.score = score

    def match(self, contract_segment, policy_segments, top_k=5):
        return [
            (segment, self.score)
            for segment in policy_segments[:top_k]
        ]


def write_state_csv(tmp_path, evidence, page_number="18-19"):
    path = tmp_path / "state_requirements.csv"
    pd.DataFrame([{
        "requirement_id": "TN-TEST-001",
        "source_document_id": "TEST-SOURCE",
        "actor": "",
        "action": "",
        "object": "",
        "recipient": "",
        "obligation_type": "",
        "authorization": "",
        "condition": "",
        "threshold": "",
        "deadline": "",
        "exception": "",
        "source_text": evidence,
        "evidence_text": evidence,
        "source_type": "STATE_REGULATION",
        "language": "en",
        "jurisdiction": "Tamil Nadu",
        "policy_name": "Test policy",
        "domain": "PROCUREMENT",
        "requirement_name": "Test requirement",
        "requirement_type": "OBLIGATION",
        "operator": "",
        "threshold_value": "",
        "unit": "",
        "bound": "",
        "benefit": "",
        "eligibility_logic": "",
        "page_number": page_number,
        "source_url": "https://example.org/source.pdf",
        "effective_from": "",
        "effective_to": "",
        "notes": "",
    }]).to_csv(path, index=False)
    return str(path)


def test_state_checker_detects_numeric_conflict_and_preserves_evidence(tmp_path):
    path = write_state_csv(
        tmp_path,
        "Termination for convenience requires at least 30 days notice.",
    )

    results = check_clause_against_state_requirements(
        "Either party may terminate for convenience with 7 days notice.",
        jurisdiction="Tamil Nadu",
        matcher=FakeMatcher(),
        state_requirements_path=path,
    )

    assert len(results) == 1
    result = results[0]
    assert result["label"] == "CONFLICT"
    assert result["conflict"] is True
    assert result["requirement_id"] == "TN-TEST-001"
    assert result["jurisdiction"] == "Tamil Nadu"
    assert result["source_url"] == "https://example.org/source.pdf"
    assert str(result["page_number"]) == "18-19"
    assert result["legal_status"] == "UNVERIFIED"
    assert result["applicability_status"] == "REVIEW_REQUIRED"


def test_state_checker_reports_compatible_numeric_requirement(tmp_path):
    path = write_state_csv(
        tmp_path,
        "Termination for convenience requires at least 30 days notice.",
        page_number="21",
    )

    results = check_clause_against_state_requirements(
        "Either party may terminate for convenience with 30 days notice.",
        jurisdiction="Tamil Nadu",
        matcher=FakeMatcher(),
        state_requirements_path=path,
    )

    assert len(results) == 1
    assert results[0]["label"] == "NO_CONFLICT"
    assert results[0]["conflict"] is False


def test_state_checker_marks_uncomparable_text_uncertain(tmp_path):
    path = write_state_csv(
        tmp_path,
        "A programme supports eligible startups in selected sectors.",
    )

    results = check_clause_against_state_requirements(
        "Either party may terminate this agreement.",
        jurisdiction="Tamil Nadu",
        matcher=FakeMatcher(),
        state_requirements_path=path,
    )

    assert len(results) == 1
    assert results[0]["label"] == "UNCERTAIN"
    assert results[0]["conflict"] is False


def test_state_checker_rejects_missing_jurisdiction():
    with pytest.raises(ValueError, match="jurisdiction"):
        check_clause_against_state_requirements(
            "Either party may terminate this agreement.",
            jurisdiction="",
            matcher=FakeMatcher(),
        )


def test_state_checker_rejects_empty_contract():
    with pytest.raises(ValueError, match="contract_text"):
        check_clause_against_state_requirements(
            "",
            jurisdiction="Tamil Nadu",
            matcher=FakeMatcher(),
        )

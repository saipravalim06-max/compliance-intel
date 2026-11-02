
import pandas as pd
import pytest

from core.state_law import load_state_law_candidates


@pytest.fixture
def state_csv(tmp_path):
    path = tmp_path / "state_requirements.csv"

    pd.DataFrame([
        {
            "requirement_id": "TN-001",
            "jurisdiction": "Tamil Nadu",
            "requirement_type": "OBLIGATION",
            "source_text": "Maintain the required records.",
            "source_url": "https://example.org/source.pdf",
            "page_number": "18-19",
        },
        {
            "requirement_id": "TN-002",
            "jurisdiction": "Tamil Nadu",
            "requirement_type": "ELIGIBILITY",
            "source_text": "The startup must meet the eligibility criteria.",
            "source_url": "https://example.org/startup.pdf",
            "page_number": "5",
        },
        {
            "requirement_id": "KA-001",
            "jurisdiction": "Karnataka",
            "requirement_type": "RESTRICTION",
            "source_text": "A restriction applies under the stated programme.",
            "source_url": "https://example.org/karnataka.pdf",
            "page_number": "20",
        },
        {
            "requirement_id": "TN-003",
            "jurisdiction": "Tamil Nadu",
            "requirement_type": "SUPPORT",
            "source_text": "Support is available to eligible startups.",
            "source_url": "https://example.org/support.pdf",
            "page_number": "7",
        },
    ]).to_csv(path, index=False)

    return path


def test_filters_by_jurisdiction_and_candidate_type(state_csv):
    rows = load_state_law_candidates("Tamil Nadu", str(state_csv))

    assert [row["requirement_id"] for row in rows] == ["TN-001"]


def test_jurisdiction_matching_is_case_insensitive(state_csv):
    rows = load_state_law_candidates("tAmIl NaDu", str(state_csv))

    assert [row["requirement_id"] for row in rows] == ["TN-001"]


def test_preserves_source_evidence_and_page_range(state_csv):
    rows = load_state_law_candidates("Tamil Nadu", str(state_csv))

    assert rows[0]["source_text"] == "Maintain the required records."
    assert rows[0]["source_url"] == "https://example.org/source.pdf"
    assert rows[0]["page_number"] == "18-19"


def test_missing_jurisdiction_is_rejected(state_csv):
    with pytest.raises(ValueError, match="jurisdiction"):
        load_state_law_candidates("", str(state_csv))


def test_does_not_treat_candidate_as_proven_law(state_csv):
    rows = load_state_law_candidates("Tamil Nadu", str(state_csv))

    # The loader returns source records; it does not assert legal applicability.
    assert rows[0]["requirement_type"] == "OBLIGATION"
    assert "legal_status" not in rows[0]

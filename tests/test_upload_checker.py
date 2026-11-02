
from modules.upload_checker import split_document_text


def test_numbered_clause_survives_wrapped_lines():
    text = """
    6.1 Assignment. No assignment of this Agreement or any right
    accruing hereunder shall be made by the Distributor without
    the prior written consent of the Company, which consent shall
    not be unreasonably withheld.
    """
    segments = split_document_text(text)

    assert len(segments) == 1
    assert segments[0].startswith("6.1 Assignment.")
    assert "prior written consent of the Company" in segments[0]
    assert "not be unreasonably withheld" in segments[0]


def test_multiple_numbered_clauses_remain_separate():
    text = """
    4.1 Duration. The Agreement starts on the commencement date.

    4.2 Termination for Cause. Either party may terminate upon
    thirty days written notice.

    4.3 Accrued Obligations. Accrued obligations survive termination.
    """
    segments = split_document_text(text)

    assert len(segments) == 3
    assert segments[0].startswith("4.1 Duration.")
    assert segments[1].startswith("4.2 Termination for Cause.")
    assert segments[2].startswith("4.3 Accrued Obligations.")


def test_clause_does_not_end_at_a_wrapped_line():
    text = """
    4.2 Termination for Cause. Either party may terminate this
    Agreement upon thirty (30) days written notice of a breach.
    The notice must describe the breach and allow an opportunity
    to cure it before termination becomes effective.
    """
    segments = split_document_text(text)

    assert len(segments) == 1
    assert "describe the breach" in segments[0]
    assert "before termination becomes effective" in segments[0]


def test_single_letter_marker_is_not_a_standalone_clause():
    text = """
    A.

    The Company's Business. The Company sells energy efficiency devices.
    """
    segments = split_document_text(text)

    assert all(segment.strip() != "A." for segment in segments)
    assert any("energy efficiency devices" in segment for segment in segments)


def test_empty_input_returns_no_segments():
    assert split_document_text("") == []
    assert split_document_text("  \n\n  ") == []


def test_duplicate_segments_are_removed_in_order():
    text = """
    1.1 Scope. The policy applies to vendors.

    1.2 Notice. Notices must be in writing.

    1.2 Notice. Notices must be in writing.
    """
    segments = split_document_text(text)

    assert len(segments) == 2
    assert segments[0].startswith("1.1 Scope.")
    assert segments[1].startswith("1.2 Notice.")


def test_numbered_clause_continues_across_page_marker():
    text = """
    4.2 Termination for Cause. Either party may terminate this
    Agreement upon 30 days

    Page -8-

    prior written notice to the other upon the occurrence of
    any of the following events: default or failure to pay.

    4.3 Accrued Obligations. Accrued obligations survive termination.
    """

    segments = split_document_text(text)

    termination = [
        segment for segment in segments
        if "Termination for Cause" in segment
    ]

    assert len(termination) == 1
    assert "upon 30 days" in termination[0]
    assert "prior written notice" in termination[0]
    assert "occurrence of" in termination[0]
    assert "Page -8-" not in termination[0]

    assert any(
        segment.startswith("4.3 Accrued Obligations.")
        for segment in segments
    )

def test_policy_extraction_keeps_numbered_requirements_only():
    from modules.upload_checker import extract_policy_requirements

    text = """
POLICY ID: POL-05
TITLE: Contract Termination and Notice Policy
CATEGORY: Termination
EFFECTIVE DATE: 2024-01-01
1. PURPOSE
This policy defines minimum notice periods.
2. REQUIREMENTS
2.1 Termination without cause requires at least 30 days.
2.2 Termination for cause requires at least 15 days to cure.
3. APPLICABILITY
Applies to all commercial contracts.
"""

    assert extract_policy_requirements(text) == [
        "2.1 Termination without cause requires at least 30 days.",
        "2.2 Termination for cause requires at least 15 days to cure.",
    ]


def test_policy_extraction_handles_windows_line_endings():
    from modules.upload_checker import extract_policy_requirements

    text = (
        "TITLE: Example Policy\r\n"
        "2.1 Written notice is required.\r\n"
        "2.2 A cure period of 15 days is required.\r\n"
    )

    assert extract_policy_requirements(text) == [
        "2.1 Written notice is required.",
        "2.2 A cure period of 15 days is required.",
    ]



def test_policy_extraction_fallback_bulleted_and_normative():
    from modules.upload_checker import extract_policy_requirements

    bullet_text = """
    Vendor Code of Conduct
    - All vendors must provide 30 days prior notice before service termination.
    - Vendor liability must not exceed two times the annual fee paid.
    """
    bullet_reqs = extract_policy_requirements(bullet_text)
    assert len(bullet_reqs) == 2
    assert "30 days prior notice" in bullet_reqs[0]

    unformatted_text = """
    Data Privacy Standard.
    The contractor shall maintain confidentiality of all customer information.
    Payment terms shall be strictly within 45 days of valid invoice receipt.
    """
    unformatted_reqs = extract_policy_requirements(unformatted_text)
    assert len(unformatted_reqs) >= 2


def test_subcontracting_and_governing_law_evaluation():
    from core.extraction import extract_requirement
    from core.conflict import detect_conflict

    c_sub = extract_requirement(
        "6.4 Subcontracting. The Supplier may subcontract core services to third parties without prior written approval from the Company."
    )
    p_sub = extract_requirement(
        "4.4 The supplier must not subcontract core services without prior written approval from the Company."
    )
    res_sub = detect_conflict(c_sub, p_sub)
    assert res_sub["label"] == "CONFLICT"
    assert "AUTH" in res_sub["rules"]
    assert "MODALITY" in res_sub["rules"]

    c_gov = extract_requirement("6.3 Governing Law. This agreement must be governed by the laws of India.")
    p_gov = extract_requirement("4.3 Vendor agreements must be governed by the laws of India.")
    res_gov = detect_conflict(c_gov, p_gov)
    assert res_gov["label"] == "NO_CONFLICT"
    assert "laws of india" in res_gov["reason"].lower()


def test_compare_uploaded_documents_prunes_uncertain_noise(tmp_path):
    from modules.upload_checker import compare_uploaded_documents

    policy_content = """Northwind Technologies Policy
1.1 Payment within 60 days of receipt.
1.2 Notice of at least 90 days before termination.
1.3 Vendor agreements must not renew automatically unless the Company receives at least 60 days written notice of renewal.
4.3 Vendor agreements must be governed by the laws of India.
4.4 The supplier must not subcontract core services without prior written approval from the Company.
"""
    contract_content = """2.1 Payment. The Company must pay valid supplier invoices within 20 days.
3.1 Renewal. This Agreement renews automatically unless either party gives 15 days written notice of non-renewal.
6.3 Governing Law. This agreement must be governed by the laws of India.
6.4 Subcontracting. The Supplier may subcontract core services without prior written approval.
"""
    p_file = tmp_path / "pol.txt"
    c_file = tmp_path / "con.txt"
    p_file.write_text(policy_content, encoding="utf-8")
    c_file.write_text(contract_content, encoding="utf-8")

    res = compare_uploaded_documents(str(c_file), [str(p_file)], backend="hashing")
    labels = {f["clause_number"]: f["label"] for f in res["findings"]}

    # Clause 1 (2.1 Payment): 20 days <= 60 days -> NO_CONFLICT
    assert labels[1] == "NO_CONFLICT"
    # Clause 2 (3.1 Renewal): 15 days vs 60 days -> CONFLICT
    assert labels[2] == "CONFLICT"
    # Clause 3 (6.3 Governing Law): both laws of India -> NO_CONFLICT
    assert labels[3] == "NO_CONFLICT"
    # Clause 4 (6.4 Subcontracting): permits vs requires approval -> CONFLICT
    assert labels[4] == "CONFLICT"
    # No spurious UNCERTAIN rows returned
    assert not any(f["label"] == "UNCERTAIN" for f in res["findings"])

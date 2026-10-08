"""
Module 2: Contract -> Company Policy Compliance Checker.

This module connects the shared NLP components:

    contract clause
        ↓
    requirement extraction
        ↓
    semantic policy matching
        ↓
    policy requirement extraction
        ↓
    structured conflict reasoning
        ↓
    evidence + explanation
"""

from typing import List, Dict

from core.engine import Segment
from core.extraction import extract_requirement
from core.matching import PolicyMatcher
from core.conflict import detect_conflict


def check_clause_against_policies(
    contract_text: str,
    policy_texts: List[str],
) -> List[Dict]:
    """
    Check one contract clause against a list of company policy requirements.

    Returns the most relevant policy matches together with their
    structured conflict analysis.
    """

    # ---------------------------------------------------------
    # 1. Create a contract Segment
    # ---------------------------------------------------------

    contract_segment = Segment(
        source_doc_id="CONTRACT-001",
        segment_id="CONTRACT-001-1",
        original_text=contract_text,
        original_language="en",
    )

    # ---------------------------------------------------------
    # 2. Create policy Segments
    # ---------------------------------------------------------

    policy_segments = []

    for index, policy_text in enumerate(policy_texts):
        policy_segments.append(
            Segment(
                source_doc_id=f"POLICY-{index + 1:03d}",
                segment_id=f"POLICY-{index + 1:03d}-1",
                original_text=policy_text,
                original_language="en",
            )
        )

    # ---------------------------------------------------------
    # 3. Find semantically relevant policies
    # ---------------------------------------------------------

    matcher = PolicyMatcher()

    matches = matcher.match(
        contract_segment,
        policy_segments,
        top_k=3,
    )

    results = []

    # ---------------------------------------------------------
    # 4. Extract contract requirement once
    # ---------------------------------------------------------

    contract_requirement = extract_requirement(
        contract_text,
        requirement_id="CONTRACT-REQ-001",
        source_document_id="CONTRACT-001",
    )

    # ---------------------------------------------------------
    # 5. Extract + compare each relevant policy
    # ---------------------------------------------------------

    for policy_segment, similarity_score in matches:

        policy_requirement = extract_requirement(
            policy_segment.original_text,
            requirement_id=policy_segment.segment_id,
            source_document_id=policy_segment.source_doc_id,
        )

        conflict_result = detect_conflict(
            contract_requirement,
            policy_requirement,
        )

        results.append(
            {
                "contract_text": contract_text,
                "policy_text": policy_segment.original_text,
                "similarity_score": round(similarity_score, 3),
                **conflict_result,
            }
        )

    return results


if __name__ == "__main__":

    contract = (
        "The vendor may share customer data with subcontractors "
        "without prior approval."
    )

    policies = [
        (
            "Customer data may only be shared with approved third "
            "parties after prior authorization."
        ),
        (
            "Invoices must be paid within 30 days."
        ),
    ]

    results = check_clause_against_policies(
        contract,
        policies,
    )

    for result in results:
        print("\n--- RESULT ---")

        for key, value in result.items():
            print(f"{key}: {value}")
"""
Module 2: Contract -> Company Policy Compliance Checker.

    contract clause
        -> requirement extraction
        -> semantic retrieval of relevant policy lines (embeddings: relevance only)
        -> policy requirement extraction
        -> structured conflict reasoning (core.conflict)
        -> evidence + explanation

Two entry points:
    check_clause_against_policies(clause, [policy text, ...])   original API, kept
    check_clause_against_corpus(clause, corpus_dir)             the real 21-policy corpus
    check_clause_against_state_requirements(...)                check clause against state statutory rules
    check_contract_document_against_state_requirements(...)     full contract audit against state laws
"""
from typing import Any, Dict, List, Optional

from core.conflict import detect_conflict
from core.engine import Segment
from core.extraction import extract_requirement
from core.matching import PolicyMatcher
from core.policy_corpus import load_policy_lines
from core.schemas import Requirement
from core.state_law import load_state_law_candidates

_ORDER = {"CONFLICT": 0, "PARTIAL_CONFLICT": 1, "NO_CONFLICT": 2, "UNCERTAIN": 3}
_policy_req_cache: Dict[str, object] = {}


def _policy_requirement(text: str, req_id: str, doc_id: str):
    """Extract each policy line once and reuse it for every clause."""
    key = f"{doc_id}|{req_id}|{text}"
    if key not in _policy_req_cache:
        _policy_req_cache[key] = extract_requirement(text, requirement_id=req_id, source_document_id=doc_id)
    return _policy_req_cache[key]

def _is_relevant_pair(contract_req, policy_req) -> bool:
    """Reject only clearly unrelated action/object pairs."""
    contract_action = contract_req.action
    policy_action = policy_req.action

    # Missing action information is insufficient to reject a candidate.
    if not contract_action or not policy_action:
        return True

    # Equivalent actions across related operational / legal concepts.
    equivalent_actions = {
        frozenset(("share", "disclose")),
        frozenset(("assign", "novate")),
        frozenset(("store", "transfer")),
    }
    same_action = contract_action == policy_action or (
        frozenset((contract_action, policy_action)) in equivalent_actions
    )

    # Different known actions are not automatically irrelevant:
    # a clause may describe a related obligation using different wording.
    if not same_action:
        # Different verbs can express the same numeric requirement.
        contract_kind = contract_req.quantity_kind
        policy_kind = policy_req.quantity_kind

        same_requirement_kind = (
            contract_kind is not None
            and contract_kind == policy_kind
        )

        if not same_requirement_kind:
            return False

    contract_object = (contract_req.object or "").lower().strip()
    policy_object = (policy_req.object or "").lower().strip()

    # Missing object information alone is not enough to reject a match.
    if not contract_object or not policy_object:
        return True

    object_aliases = {
        "sub-processors": "subcontractors",
        "subprocessors": "subcontractors",
        "customer or confidential data": "customer data",
        "company or customer data": "customer data",
        "confidential data": "customer data",
        "confidential information": "customer data",
        "customer information": "customer data",
        "company information": "customer data",
        "patient data": "customer data",
        "clinical data": "customer data",
        "health data": "customer data",
        "name or logo": "publicity",
        "company name or logo": "publicity",
        "company's name or logo": "publicity",
        "marketing material": "publicity",
        "this agreement": "agreement",
        "the agreement": "agreement",
        "contract": "agreement",
    }

    contract_object = object_aliases.get(contract_object, contract_object)
    policy_object = object_aliases.get(policy_object, policy_object)

    return contract_object == policy_object


def _run(contract_text: str, policy_segments: List[Segment], matcher: PolicyMatcher, top_k: int, meta: Optional[Dict] = None) -> List[Dict]:
    contract_segment = Segment(source_doc_id="CONTRACT-001", segment_id="CONTRACT-001-1",
                               original_text=contract_text, original_language="en")
    contract_req = extract_requirement(contract_text, requirement_id="CONTRACT-REQ-001", source_document_id="CONTRACT-001")
    results = []
    for seg, score in matcher.match(contract_segment, policy_segments, top_k=top_k):
        policy_req = _policy_requirement(seg.original_text,seg.segment_id,seg.source_doc_id,)
        if not _is_relevant_pair(contract_req, policy_req):
            continue

        result = detect_conflict(contract_req, policy_req)
        results.append({"contract_text": contract_text,"policy_text": seg.original_text,
                        "policy_line_id": seg.segment_id, "similarity_score": round(score, 3),
                        **((meta or {}).get(seg.segment_id, {})), **result})
    return results


def check_clause_against_policies(
    contract_text: str,
    policy_texts: List[str],
    matcher: Optional[PolicyMatcher] = None,
    top_k: int = 3,
) -> List[Dict]:
    """Original API: check one clause against a list of policy requirement sentences."""
    matcher = matcher or PolicyMatcher()
    segs = [Segment(source_doc_id=f"POLICY-{i + 1:03d}", segment_id=f"POLICY-{i + 1:03d}-1",
                    original_text=t, original_language="en") for i, t in enumerate(policy_texts)]
    return _run(contract_text, segs, matcher, top_k)


def check_clause_against_corpus(
    contract_text: str,
    corpus_dir: str = "data/policy_corpus",
    matcher: Optional[PolicyMatcher] = None,
    top_k: int = 5,
) -> List[Dict]:
    """Check one clause against every numbered requirement line in the canonical corpus.
    Results are sorted: conflicts first, then by similarity."""
    matcher = matcher or PolicyMatcher()
    lines = load_policy_lines(corpus_dir)
    segs = [Segment(source_doc_id=ln["policy_id"], segment_id=ln["line_id"],
                    original_text=ln["text"], original_language="en") for ln in lines]
    meta = {ln["line_id"]: {"policy_id": ln["policy_id"], "policy_name": ln["policy_name"]} for ln in lines}
    results = _run(contract_text, segs, matcher, top_k, meta)
    results.sort(key=lambda r: (_ORDER[r["label"]], -r["similarity_score"]))
    return results


def get_statutory_redline_advice(finding: Dict[str, Any]) -> str:
    """Provide practical contract drafting redlines for detected statutory conflicts."""
    req_id = str(finding.get("requirement_id") or "")
    reason = str(finding.get("reason") or "").lower()

    if "PAY" in req_id or "payment term" in reason:
        return (
            "Suggested Redline: Amend payment term to: 'The Buyer shall pay all valid undisputed invoices "
            "within forty-five (45) days of receipt, in compliance with Section 15 of the MSMED Act, 2006.'"
        )
    if "NOC" in req_id or "competing" in reason or "compete" in reason:
        return (
            "Suggested Redline: Delete post-termination non-compete covenant (void ab initio under Section 27 "
            "of the Indian Contract Act). Replace with: 'The Service Provider covenants to protect Confidential Information "
            "and refrain from soliciting client personnel for twelve (12) months following termination.'"
        )
    if "NOT" in req_id or "notice" in reason:
        return (
            "Suggested Redline: Amend termination notice to: 'Either party may terminate this agreement for convenience "
            "by providing at least thirty (30) days prior written notice to the other party.'"
        )
    if "DATA" in req_id or "breach" in reason or "cybersecurity" in reason:
        return (
            "Suggested Redline: Amend incident timeline to: 'The Contractor shall report confirmed cybersecurity incidents "
            "and customer data breaches within six (6) hours of discovery to align with statutory CERT-In directions.'"
        )
    if "STAMP" in req_id or "stamp" in reason:
        return (
            "Statutory Formality: Ensure this agreement is executed with appropriate state e-stamp duty under the "
            "relevant State Stamp Act prior to signature to ensure legal admissibility in arbitration or court."
        )
    if "PROC" in req_id or "turnover" in reason:
        return (
            "Suggested Proviso: Add: 'Provided that registered startups shall be exempt from prior turnover and "
            "prior experience criteria in accordance with the applicable State Startup Public Procurement Policy.'"
        )
    return "Action Required: Review clause with legal counsel to harmonize with state statutory guidelines."


def check_clause_against_state_requirements(
    contract_text: str,
    jurisdiction: str,
    matcher: Optional[PolicyMatcher] = None,
    top_k: int = 5,
    state_requirements_path: Optional[str] = None,
) -> List[Dict]:
    """Compare a contract clause with sourced state-policy candidates.

    A detected conflict is a potential contradiction with a dataset record,
    not a legal conclusion. Legal status and applicability require review.
    """
    if not contract_text or not contract_text.strip():
        raise ValueError("contract_text must not be empty")

    if not jurisdiction or not jurisdiction.strip():
        raise ValueError("jurisdiction must be provided")

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    rows = load_state_law_candidates(
        jurisdiction=jurisdiction,
        path=state_requirements_path,
    )

    # Keep only rows that contain evidence text to compare.
    usable_rows = []
    for row in rows:
        evidence = row.get("evidence_text") or row.get("source_text")
        if evidence and str(evidence).strip():
            usable_rows.append((row, str(evidence).strip()))

    if not usable_rows:
        return []

    # Use a conservative threshold suitable for cross-domain statutory matching
    matcher = matcher or PolicyMatcher(backend="hashing", similarity_threshold=0.08)

    contract_segment = Segment(
        source_doc_id="CONTRACT-001",
        segment_id="CONTRACT-001-1",
        original_text=contract_text.strip(),
        original_language="en",
    )

    contract_req = extract_requirement(
        contract_text.strip(),
        requirement_id="CONTRACT-REQ-001",
        source_document_id="CONTRACT-001",
    )

    state_segments = [
        Segment(
            source_doc_id=str(row.get("policy_name") or row.get("requirement_id")),
            segment_id=str(row.get("requirement_id")),
            original_text=evidence,
            original_language="en",
        )
        for row, evidence in usable_rows
    ]

    row_by_id = {
        str(row.get("requirement_id")): (row, evidence)
        for row, evidence in usable_rows
    }

    results = []

    for segment, score in matcher.match(
        contract_segment,
        state_segments,
        top_k=top_k,
    ):
        row, evidence = row_by_id[segment.segment_id]

        try:
            # Extract structured fields from the original source wording.
            state_req = extract_requirement(
                evidence,
                requirement_id=str(row.get("requirement_id")),
                source_document_id=str(
                    row.get("policy_name") or row.get("requirement_id")
                ),
            )

            # Prefer explicit structured values from the dataset when present.
            for field in (
                "actor",
                "action",
                "object",
                "recipient",
                "obligation_type",
                "authorization",
                "condition",
                "threshold",
                "deadline",
                "exception",
                "bound",
                "threshold_value",
                "unit",
            ):
                value = row.get(field)
                if value is not None and str(value).strip().lower() not in {
                    "", "nan", "none", "null"
                }:
                    setattr(state_req, field, str(value).strip())

            # Propagate explicit UPPER/LOWER bound to extracted quantities
            explicit_bound = row.get("bound")
            if explicit_bound and str(explicit_bound).strip().upper() in ("UPPER", "LOWER"):
                bound_val = str(explicit_bound).strip().upper()
                state_req.bound = bound_val
                for q in state_req.quantities or []:
                    q["bound"] = bound_val

        except (TypeError, ValueError):
            # Preserve the finding as uncertain if the row cannot be mapped.
            finding = {
                "contract_text": contract_text,
                "state_requirement_text": evidence,
                "requirement_id": row.get("requirement_id"),
                "policy_name": row.get("policy_name"),
                "jurisdiction": row.get("jurisdiction") or row.get("state"),
                "similarity_score": round(score, 3),
                "label": "UNCERTAIN",
                "conflict": False,
                "severity": "UNKNOWN",
                "reason": (
                    "A relevant state-policy record was retrieved, but its "
                    "structured fields could not be mapped for comparison."
                ),
                "contract_evidence": contract_text,
                "policy_evidence": evidence,
                "source_url": row.get("source_url"),
                "page_number": row.get("page_number"),
                "legal_status": "UNVERIFIED",
                "applicability_status": "REVIEW_REQUIRED",
            }
            finding["redline_advice"] = get_statutory_redline_advice(finding)
            results.append(finding)
            continue

        comparison = detect_conflict(contract_req, state_req)

        finding = {
            "contract_text": contract_text,
            "state_requirement_text": evidence,
            "requirement_id": row.get("requirement_id"),
            "policy_name": row.get("policy_name"),
            "jurisdiction": row.get("jurisdiction") or row.get("state"),
            "requirement_type": row.get("requirement_type"),
            "similarity_score": round(score, 3),
            **comparison,
            "source_url": row.get("source_url"),
            "page_number": row.get("page_number"),
            "effective_from": row.get("effective_from"),
            "effective_to": row.get("effective_to"),
            "legal_status": "UNVERIFIED",
            "applicability_status": "REVIEW_REQUIRED",
        }
        finding["redline_advice"] = get_statutory_redline_advice(finding)
        results.append(finding)

    results.sort(
        key=lambda item: (
            _ORDER.get(item.get("label"), 4),
            -item.get("similarity_score", 0),
        )
    )
    return results


def check_contract_document_against_state_requirements(
    contract_text: str,
    jurisdiction: str,
    matcher: Optional[PolicyMatcher] = None,
    top_k: int = 3,
    state_requirements_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate an entire multi-clause contract document against
    sourced state statutory regulations and policies.
    """
    from modules.upload_checker import split_document_text

    clauses = split_document_text(contract_text)
    matcher = matcher or PolicyMatcher(backend="hashing", similarity_threshold=0.08)

    findings = []
    seen_pairs = set()

    for idx, clause in enumerate(clauses, start=1):
        clause_results = check_clause_against_state_requirements(
            contract_text=clause,
            jurisdiction=jurisdiction,
            matcher=matcher,
            top_k=top_k,
            state_requirements_path=state_requirements_path,
        )

        # Filter out noisy UNCERTAIN rows when decisive findings exist
        decisive = [r for r in clause_results if r.get("label") in ("CONFLICT", "PARTIAL_CONFLICT", "NO_CONFLICT")]
        selected_results = decisive if decisive else clause_results[:1]

        for res in selected_results:
            # Deduplicate multiple identical matches for the same clause
            pair_key = (idx, res.get("requirement_id"))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            findings.append({
                "clause_number": idx,
                "contract_clause": clause,
                **res,
            })

    conflicts = [f for f in findings if f.get("label") == "CONFLICT"]
    partial = [f for f in findings if f.get("label") == "PARTIAL_CONFLICT"]
    compatible = [f for f in findings if f.get("label") == "NO_CONFLICT"]

    return {
        "jurisdiction": jurisdiction,
        "clause_count": len(clauses),
        "total_findings": len(findings),
        "conflict_count": len(conflicts),
        "partial_count": len(partial),
        "compatible_count": len(compatible),
        "findings": findings,
    }


if __name__ == "__main__":
    import sys

    backend = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers"
    matcher = PolicyMatcher(backend=backend, similarity_threshold=0.0 if backend == "hashing" else 0.35)
    clause = "Either party may terminate this agreement by giving 7 days written notice."
    for r in check_clause_against_corpus(clause, matcher=matcher, top_k=5):
        print(f"\n[{r['label']}] {r['policy_line_id']} (similarity {r['similarity_score']})")
        print("  policy:", r["policy_text"][:110])
        print("  why:   ", r["reason"][:160])

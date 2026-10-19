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
"""
from typing import Dict, List, Optional

from core.conflict import detect_conflict
from core.engine import Segment
from core.extraction import extract_requirement
from core.matching import PolicyMatcher
from core.policy_corpus import load_policy_lines

_ORDER = {"CONFLICT": 0, "PARTIAL_CONFLICT": 1, "NO_CONFLICT": 2, "UNCERTAIN": 3}
_policy_req_cache: Dict[str, object] = {}


def _policy_requirement(text: str, req_id: str, doc_id: str):
    """Extract each policy line once and reuse it for every clause."""
    key = f"{doc_id}|{req_id}|{text}"
    if key not in _policy_req_cache:
        _policy_req_cache[key] = extract_requirement(text, requirement_id=req_id, source_document_id=doc_id)
    return _policy_req_cache[key]


def _run(contract_text: str, policy_segments: List[Segment], matcher: PolicyMatcher, top_k: int, meta: Optional[Dict] = None) -> List[Dict]:
    contract_segment = Segment(source_doc_id="CONTRACT-001", segment_id="CONTRACT-001-1",
                               original_text=contract_text, original_language="en")
    contract_req = extract_requirement(contract_text, requirement_id="CONTRACT-REQ-001", source_document_id="CONTRACT-001")
    results = []
    for seg, score in matcher.match(contract_segment, policy_segments, top_k=top_k):
        policy_req = _policy_requirement(seg.original_text, seg.segment_id, seg.source_doc_id)
        result = detect_conflict(contract_req, policy_req)
        results.append({"contract_text": contract_text, "policy_text": seg.original_text,
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


if __name__ == "__main__":
    import sys

    backend = sys.argv[1] if len(sys.argv) > 1 else "sentence-transformers"
    matcher = PolicyMatcher(backend=backend, similarity_threshold=0.0 if backend == "hashing" else 0.35)
    clause = "Either party may terminate this agreement by giving 7 days written notice."
    for r in check_clause_against_corpus(clause, matcher=matcher, top_k=5):
        print(f"\n[{r['label']}] {r['policy_line_id']} (similarity {r['similarity_score']})")
        print("  policy:", r["policy_text"][:110])
        print("  why:   ", r["reason"][:160])

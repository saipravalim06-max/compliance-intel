"""
tests/test_engine.py — guards the Step-2 engine behaviour.
Run:  python -m pytest tests/test_engine.py -q     (or: python tests/test_engine.py)
Needs no model download: retrieval tests use the offline hashing backend.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.conflict import detect_conflict  # noqa: E402
from core.embeddings import EmbeddingModel  # noqa: E402
from core.extraction import extract_requirement as ex  # noqa: E402
from core.matching import PolicyMatcher  # noqa: E402
from core.policy_corpus import get_line, load_policy_lines  # noqa: E402
from core.quantities import find_quantities  # noqa: E402

CORPUS = os.path.join(ROOT, "data", "policy_corpus")


def _label(clause, policy):
    return detect_conflict(ex(clause), ex(policy))["label"]


# ---- the five extractor bugs found in the first review ------------------------
def test_word_boundary_cancellation_is_not_a_permission():
    r = ex("Fees are payable upon cancellation of the order.")
    assert r.obligation_type is None


def test_negation_is_a_prohibition():
    assert ex("The vendor must not disclose confidential information to third parties.").obligation_type == "PROHIBITION"
    assert ex("Neither party may assign its rights without consent.").obligation_type == "PROHIBITION"
    assert ex("You agree not to make a transfer without our prior written consent.").obligation_type == "PROHIBITION"


def test_may_only_is_a_restricted_permission_and_recipient_is_clean():
    r = ex("Customer data may only be shared with approved third parties after prior authorization.")
    assert r.obligation_type == "RESTRICTED_PERMISSION" and r.authorization == "REQUIRED"
    assert r.recipient == "approved third parties"


def test_number_words_and_calendar_day_phrasing():
    r = ex("All vendor contracts must include a minimum thirty (30) calendar day written termination notice period.")
    assert r.action == "terminate" and r.threshold_value == 30 and r.unit == "DAYS" and r.bound == "LOWER"


def test_without_approval_inside_a_prohibition_means_approval_required():
    assert ex("Customer data must not be shared without prior written authorization.").authorization == "REQUIRED"
    assert ex("The vendor may share customer data without prior approval.").authorization == "NOT_REQUIRED"
    assert ex("Any assignment without such consent will be void.").authorization == "REQUIRED"


# ---- numeric reasoning ------------------------------------------------------------
NOTICE = "Termination for convenience requires a minimum notice period of thirty (30) calendar days."


def test_headline_7_vs_30_days():
    r = detect_conflict(ex("Either party may terminate this agreement by giving 7 days written notice."), ex(NOTICE))
    assert r["label"] == "CONFLICT" and r["severity"] == "HIGH"
    assert "7 days" in r["reason"] and "30 days" in r["reason"]


def test_boundary_equal_value_is_not_a_conflict():
    assert _label("Either party may terminate upon thirty (30) days written notice.", NOTICE) == "NO_CONFLICT"


def test_direction_matters_floor_vs_ceiling():
    floor = "Warranty period must be a minimum of ninety (90) days."
    ceiling = "Non-compete provisions must not exceed twelve (12) months."
    assert _label("Supplier warrants the goods for thirty (30) days.", floor) == "CONFLICT"
    assert _label("Supplier warrants the goods for one (1) year.", floor) == "NO_CONFLICT"
    assert _label("Vendor shall not compete for three (3) years after termination.", ceiling) == "CONFLICT"
    assert _label("Vendor shall not compete for six (6) months after termination.", ceiling) == "NO_CONFLICT"


def test_unit_conversion_hours_days():
    pol = "Any data breach must be reported within twenty-four (24) hours of discovery."
    assert _label("Processor shall notify Controller of any data breach within three (3) days of discovery.", pol) == "CONFLICT"


def test_not_comparable_is_uncertain_not_a_guess():
    assert _label("Interest accrues at 12% per annum on overdue amounts.",
                  "Late payment interest in excess of 1.5% per month requires approval.") == "UNCERTAIN"
    assert _label("Liability shall not exceed USD 50,000.",
                  "Liability should not be capped below an amount equal to twelve (12) months of fees.") == "UNCERTAIN"


def test_a_term_length_is_not_a_notice_period():
    r = ex("The Agreement renews for successive five (5)-year terms unless either party gives notice at least ninety (90) days prior to expiry.")
    kinds = [(q["value"], q["kind"]) for q in r.quantities]
    assert (90.0, "RENEWAL_NOTICE") in kinds and not any(v == 5.0 and k == "RENEWAL_NOTICE" for v, k in kinds)


def test_internal_approval_is_not_counterparty_consent():
    r = ex("Non-compete clauses that restrict the company are not acceptable without General Counsel approval.")
    assert r.authorization is None


def test_scope_qualifier_gives_partial_conflict():
    pol = 'Vendors classified as "critical" must provide a minimum sixty (60) day termination notice period.'
    assert _label("Either party may terminate upon forty-five (45) days written notice.", pol) == "PARTIAL_CONFLICT"


def test_find_quantities_directions():
    q = find_quantities("with less than fifteen (15) days notice", prohibition=True)[0]
    assert (q.value, q.bound) == (15.0, "LOWER")
    assert find_quantities("no less than 30 days")[0].bound == "LOWER"
    assert find_quantities("not to exceed 5% annually")[0].bound == "UPPER"


# ---- the labelled set -----------------------------------------------------------------
def test_gold_set_regression():
    cases = json.load(open(os.path.join(ROOT, "tests/datasets/evaluation_set.json"), encoding="utf-8"))["cases"]
    lines = load_policy_lines(CORPUS)
    wrong = []
    for c in cases:
        pol = get_line(lines, c["policy_line"])
        got = detect_conflict(ex(c["clause"]), ex(pol["text"]))["label"]
        if got != c["expected"]:
            wrong.append((c["id"], c["expected"], got))
    assert len(cases) >= 80
    assert len(wrong) / len(cases) <= 0.03, wrong   # synthetic suite: expect (near) perfect


# ---- retrieval / caching (offline backend) ------------------------------------------
def test_embedding_cache_encodes_each_text_once():
    class Counting:
        def __init__(self):
            self.n = 0

        def encode(self, texts, normalize_embeddings=True):
            self.n += len(texts)
            import numpy as np
            return np.ones((len(texts), 4), dtype="float32") / 2

    m = EmbeddingModel(backend="hashing")
    m.model = Counting()
    m.encode(["a", "b", "a"]); m.encode(["a", "b", "c"])
    assert m.model.n == 3


def test_pipeline_end_to_end_offline():
    from modules.contract_checker import check_clause_against_corpus
    matcher = PolicyMatcher(backend="hashing", similarity_threshold=0.0)
    res = check_clause_against_corpus("Either party may terminate this agreement by giving 7 days written notice.",
                                      corpus_dir=CORPUS, matcher=matcher, top_k=8)
    assert any(r["label"] == "CONFLICT" and r["policy_line_id"].startswith("POL-0") for r in res)
    assert all(r["label"] in {"CONFLICT", "PARTIAL_CONFLICT", "NO_CONFLICT", "UNCERTAIN"} for r in res)


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\n{len(tests)} engine checks passed")

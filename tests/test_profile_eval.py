"""
tests/test_profile_eval.py — guards Module 1 (state requirements vs company profile).
Run:  python -m pytest tests/test_profile_eval.py -q     (or: python tests/test_profile_eval.py)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pandas as pd  # noqa: E402

from core.company_profile import CompanyProfile  # noqa: E402
from core.profile_eval import evaluate_profile, load_rules, load_state_requirements, summarize  # noqa: E402
from core.taxonomy import FitVerdict  # noqa: E402
from modules.state_fit import compare_states, evaluate_for_state  # noqa: E402

P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
REQS = load_state_requirements(P("data/state_policies/state_requirements_canonical.csv"))
RULES = load_rules(P("data/state_policies/profile_rules.json"))
AGRI = CompanyProfile.load(P("data/profiles/agrivision_ai.json"))
STEEL = CompanyProfile.load(P("data/profiles/steelforge_components.json"))
NIRMAAN = CompanyProfile.load(P("data/profiles/nirmaan_rural_foods.json"))


def _by_id(checks):
    return {c.requirement_id: c for c in checks}


def test_every_requirement_has_a_rule_and_no_rule_is_orphaned():
    ids = {r["requirement_id"] for r in REQS}
    assert ids == set(RULES), (ids ^ set(RULES))
    assert len(ids) == 93


def test_missing_facts_never_become_fail():
    empty = CompanyProfile(company_name="Nothing Known Ltd")
    checks = evaluate_profile(empty, REQS, RULES)
    assert not [c.requirement_id for c in checks if c.verdict == FitVerdict.FAIL]
    assert any(c.verdict == FitVerdict.UNKNOWN for c in checks)


def test_numeric_eligibility_uses_the_right_limits_per_state():
    tn = _by_id(evaluate_profile(AGRI, [r for r in REQS if r["jurisdiction"] == "Tamil Nadu"], RULES))
    assert tn["TN-ELIG-002"].verdict == FitVerdict.PASS and tn["TN-ELIG-003"].verdict == FitVerdict.PASS
    mid = CompanyProfile(company_name="Mid Ltd", legal_form="Private Limited", age_years=5, annual_turnover_inr=7.5e8)  # ₹75 crore
    tn = _by_id(evaluate_profile(mid, [r for r in REQS if r["jurisdiction"] == "Tamil Nadu"], RULES))
    ka = _by_id(evaluate_profile(mid, [r for r in REQS if r["jurisdiction"] == "Karnataka"], RULES))
    assert tn["TN-ELIG-003"].verdict == FitVerdict.FAIL        # ₹75 crore > ₹50 crore (Tamil Nadu)
    assert ka["KA-ELIG-003"].verdict == FitVerdict.PASS        # ₹75 crore <= ₹100 crore (Karnataka)


def test_a_definite_failure_is_reported_even_when_other_facts_are_unknown():
    ka = _by_id(evaluate_profile(AGRI, [r for r in REQS if r["jurisdiction"] == "Karnataka"], RULES))
    assert ka["KA-SGST-002"].verdict == FitVerdict.FAIL        # ₹4 crore > ₹1 crore cap
    assert "40,000,000" in ka["KA-SGST-002"].reasoning


def test_non_startup_fails_eligibility_and_gets_no_benefits():
    for state in ("Tamil Nadu", "Karnataka"):
        r = evaluate_for_state(STEEL, state)
        s = r["summary"]
        assert not s["eligible_as_startup"]
        assert any(i.endswith("ELIG-002") or i.endswith("ELIG-004") for i in s["eligibility_failures"])   # age
        assert s["benefits_confirmed"] <= 2                                                             # no benefits flow through


def test_registration_is_a_step_to_take_not_a_failure():
    r = evaluate_for_state(NIRMAAN, "Tamil Nadu", if_registered=True)
    assert r["summary"]["eligible_as_startup"]
    assert r["summary"]["actions_required"] == ["TN-ELIG-007"]
    stated = evaluate_for_state(NIRMAAN, "Tamil Nadu", if_registered=False)
    assert stated["summary"]["benefits_confirmed"] < r["summary"]["benefits_confirmed"]


def test_inclusion_rules_follow_the_profile():
    tn = _by_id(evaluate_profile(AGRI, [r for r in REQS if r["jurisdiction"] == "Tamil Nadu"], RULES))
    assert tn["TN-SCST-001"].verdict == FitVerdict.NOT_APPLICABLE
    assert tn["TN-WOM-001"].verdict == FitVerdict.PASS
    nir = _by_id(evaluate_profile(_registered(NIRMAAN, "Tamil Nadu"), [r for r in REQS if r["jurisdiction"] == "Tamil Nadu"], RULES))
    assert nir["TN-SCST-001"].verdict == FitVerdict.PASS        # SC/ST-led
    assert nir["TN-MFG-003"].verdict == FitVerdict.NOT_APPLICABLE   # manufacturing but only 8 employees (needs > 20)


def _registered(profile, state):
    from core.profile_eval import assume_registered
    return assume_registered(profile, state)


def test_mirror_rows_are_not_counted_twice():
    ka = [r for r in REQS if r["jurisdiction"] == "Karnataka"]
    checks = evaluate_profile(AGRI, ka, RULES)
    s = summarize(checks, RULES)
    assert sum(s["counts"].values()) == len(ka) - 2


def test_every_verdict_carries_its_evidence():
    checks = evaluate_profile(AGRI, REQS, RULES)
    assert all(c.evidence_text and c.reasoning and c.source_url for c in checks)
    missing_page = [c.requirement_id for c in checks if c.page_number is None]
    assert missing_page == [], missing_page
    ka_market = next(c for c in checks if c.requirement_id == "KA-MKT-002")
    assert str(ka_market.page_number) == "18-19"   # known data gap, logged in docs/MODULE1.md


def test_compare_states_returns_both_states_without_a_single_score():
    res = compare_states(AGRI)
    assert {r["state"] for r in res} == {"Tamil Nadu", "Karnataka"}
    assert all("score" not in r["summary"] for r in res)


def test_agreement_with_hand_labels_does_not_regress():
    gold, n, agree = [], 0, 0
    for state, (path, sheet) in {"Tamil Nadu": ("data/state_policies/tamil_nadu_state_fit.xlsx", "TN Evaluation"),
                                 "Karnataka": ("data/state_policies/karnataka_state_fit.xlsx", "KA Evaluation")}.items():
        if not os.path.exists(P(path)):
            return
        g = pd.read_excel(P(path), sheet_name=sheet).set_index("requirement_id")["result"]
        for c in evaluate_profile(AGRI, [r for r in REQS if r["jurisdiction"] == state], RULES):
            if c.requirement_id in g.index:
                n += 1
                agree += str(g[c.requirement_id]).strip() == c.verdict.value
    assert n == 86 and agree / n >= 0.85, f"{agree}/{n}"


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\n{len(tests)} profile-evaluation checks passed")

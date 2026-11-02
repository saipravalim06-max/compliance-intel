"""
tests/test_foundation.py — guards the Step-1 decisions (one corpus, one schema,
one taxonomy, one profile). Run:  python -m pytest tests/test_foundation.py -q
(or simply: python tests/test_foundation.py)
"""
import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.company_profile import CompanyProfile  # noqa: E402
from core.normalize import normalize_threshold as nt  # noqa: E402
from core.schemas import Requirement  # noqa: E402
from core.taxonomy import OPERATOR_MAP, STATE_DOMAIN_MAP, STATE_TYPE_MAP  # noqa: E402

P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
STATE_FILES = [("data/state_policies/tamil_nadu_state_fit.xlsx", "TN_Regulatory_Data"),
               ("data/state_policies/karnataka_state_fit.xlsx", "KA_Regulatory_Data")]


def test_policy_corpus_is_single_and_consistent():
    idx = pd.read_csv(P("data/policy_corpus/policy_index.csv"))
    assert idx.policy_id.is_unique, "duplicate policy IDs"
    files_on_disk = {f for f in os.listdir(P("data/policy_corpus")) if f.startswith("POL-") and f.endswith(".txt")}
    assert files_on_disk == set(idx.file_name), f"index/files mismatch: {files_on_disk ^ set(idx.file_name)}"
    for r in idx.itertuples():
        text = open(P("data/policy_corpus", r.file_name), encoding="utf-8").read()
        assert f"POLICY ID: {r.policy_id}" in text, f"{r.file_name} header ID mismatch"
        lines = [l for l in text.splitlines() if re.match(r"^\d+\.\d+\s", l.strip())]
        assert len(lines) >= 3, f"{r.policy_id}: too few numbered requirement lines"
        assert any(re.search(r"\d", l) for l in lines), f"{r.policy_id}: no numeric threshold in any requirement"


def test_mapping_points_at_real_policies():
    idx = set(pd.read_csv(P("data/policy_corpus/policy_index.csv")).policy_id)
    m = pd.read_csv(P("data/processed/cuad_policy_mapping.csv"))
    assert set(m.policy_id) <= idx
    assert m.cuad_category.is_unique
    assert set(m.mapping_strength) <= {"strong", "moderate", "weak"}


def test_taxonomy_covers_every_raw_value_in_state_workbooks():
    for path, sheet in STATE_FILES:
        if not os.path.exists(P(path)):
            continue
        df = pd.read_excel(P(path), sheet_name=sheet)
        for col, mp in [("domain", STATE_DOMAIN_MAP), ("requirement_type", STATE_TYPE_MAP), ("operator", OPERATOR_MAP)]:
            vals = {str(v).strip().lower() for v in df[col].dropna()}
            assert vals <= set(mp), f"{sheet}.{col} unmapped: {sorted(vals - set(mp))}"


def test_every_state_row_converts_and_numeric_thresholds_parse():
    n = 0
    for path, sheet in STATE_FILES:
        if not os.path.exists(P(path)):
            continue
        for rec in pd.read_excel(P(path), sheet_name=sheet).to_dict("records"):
            r = Requirement.from_state_row(rec)
            n += 1
            assert r.requirement_id and r.source_text, "missing id/evidence"
            if r.threshold and re.search(r"\d", r.threshold):
                assert r.threshold_value is not None and r.unit is not None, r.requirement_id
    assert n == 0 or n == 93


def test_turnover_ceilings_are_comparable_across_states():
    got = {}
    for path, sheet in STATE_FILES:
        if not os.path.exists(P(path)):
            continue
        for rec in pd.read_excel(P(path), sheet_name=sheet).to_dict("records"):
            r = Requirement.from_state_row(rec)
            if r.unit == "INR" and r.threshold and "turnover" in (r.requirement_name or "").lower() + (r.condition or "").lower() \
                    and r.requirement_type == "ELIGIBILITY" and r.jurisdiction:
                got.setdefault(r.jurisdiction, set()).add(r.threshold_value)
    if got:
        assert 5e8 in got.get("Tamil Nadu", set()), got
        assert 1e9 in got.get("Karnataka", set()), got


def test_normalizer():
    assert nt("₹50 crore in any financial year")["value"] == 5e8
    assert nt("Up to ₹15", "lakh")["value"] == 1.5e6
    assert nt("10 years from incorporation")["unit"] == "YEARS"
    d = nt("a minimum thirty (30) calendar day written notice")
    assert (d["value"], d["unit"], d["bound"]) == (30.0, "DAYS", "LOWER")
    assert nt("Registered") is None


def test_profiles_load_and_unknown_stays_unknown():
    for fn in os.listdir(P("data/profiles")):
        p = CompanyProfile.load(P("data/profiles", fn))
        assert p.company_name and p.is_demo_profile
    agri = CompanyProfile.load(P("data/profiles/agrivision_ai.json"))
    assert agri.annual_turnover_inr == 4e7
    assert agri.has_scalable_model is None and "has_scalable_model" in agri.unknown_fields()


def test_existing_extractor_still_imports_and_runs():
    from core.extraction import extract_requirement
    assert extract_requirement("The vendor may share customer data without prior approval.").action == "share"


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("PASS", t.__name__)
    print(f"\n{len(tests)} foundation checks passed")

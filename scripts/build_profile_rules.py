"""
scripts/build_profile_rules.py — the evaluation rules for every state requirement.

Edit THIS file (not the JSON), then run:   python scripts/build_profile_rules.py

Each rule says, for one requirement:
    gates   facts that decide whether the requirement concerns the company at all
    checks  conditions the company must satisfy (False -> FAIL)
    needs   extra evidence before an award can be claimed (unknown -> POTENTIAL)
    kind    eligibility | benefit | applies | discretionary | info
Rules are written from the policy wording (evidence_text), not from anyone's labels.
Verdict logic is documented in core/profile_eval.py.

Label conventions (so the two states are judged the same way):
    allocation / earmark / reservation  -> kind "applies"      (a policy-level provision that covers the company)
    competitive or discretionary award  -> kind "discretionary"(category fits, award is not automatic)
    programme target, budget, institution funding, platform -> kind "info"
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def P(fact, op, value=None, label=None):
    d = {"fact": fact, "op": op}
    if value is not None:
        d["value"] = value
    if label:
        d["label"] = label
    return d


def ANY(*ps, label=None):
    return {"any_of": list(ps), **({"label": label} if label else {})}


def NONE(*ps, label=None):
    return {"none_of": list(ps), **({"label": label} if label else {})}


def ALL(*ps, label):
    return {"all_of": list(ps), "label": label}


def R(kind, gates=(), checks=(), needs=(), note=None, duplicate_of=None):
    r = {"kind": kind}
    for k, v in (("gates", gates), ("checks", checks), ("needs", needs)):
        if v:
            r[k] = list(v)
    if note:
        r["note"] = note
    if duplicate_of:
        r["duplicate_of"] = duplicate_of
    return r


# ---------------------------------------------------------------- shared facts
# actionable = a step the company can simply take (register, incorporate), not an intrinsic fact about it
RECOG = {**P("state.recognized_by_state_startup_agency", "==", True, "recognised by the state startup agency"), "actionable": True}
INCORP = {**P("state.incorporated_in_state", "==", True, "incorporated in the state"), "actionable": True}
LEGAL = P("legal_form", "in", ["private limited", "llp", "limited liability partnership", "partnership",
                               "registered partnership", "partnership firm"], "legal form is private limited / partnership / LLP")
AGE10 = P("age_years", "<=", 10, "age ≤ 10 years from incorporation")
TO50 = P("annual_turnover_inr", "<=", 5e8, "turnover ≤ ₹50 crore")
TO100 = P("annual_turnover_inr", "<=", 1e9, "turnover ≤ ₹100 crore")
SPLIT = P("formed_by_split_or_reconstruction", "==", False, "not formed by splitting / reconstructing an existing business")
INNOV = P("has_innovation", "==", True, "works on innovation / improvement of products, services or processes")
SCALE = P("has_scalable_model", "==", True, "scalable model with employment / wealth potential")
WOMEN = P("is_women_led", "==", True, "women-led")
RURAL = P("has_rural_impact", "==", True, "rural impact")
GREEN = P("is_green_tech", "==", True, "climate-action / green-tech")
SCST = P("is_sc_st_led", "==", True, "SC/ST-led")
TRANS = P("is_trans_or_differently_abled_led", "==", True, "trans / differently-abled-led")
OBCMIN = P("is_obc_or_minority_led", "==", True, "OBC / minority-led")
MANUF = P("is_manufacturing", "==", True, "manufacturing startup")
PATENT = P("has_patent", "==", True, "holds a patent")
BEYOND = P("located_beyond_bengaluru_urban", "==", True, "located beyond Bengaluru Urban")
INCUB = P("incubated_in_govt_supported_incubator", "==", True, "incubated in a government-supported incubator")
EARLY = P("is_early_stage", "==", True, "early-stage / proof-of-concept stage")
GROWTH = P("is_growth_stage", "==", True, "growth-stage startup")
DEEPTECH = ["ai", "artificial intelligence", "ml", "machine learning", "robotics", "drones", "medtech",
            "electric vehicles", "deep tech", "quantum", "blockchain", "iot", "assistive technology"]
DEEP = P("technology_areas", "any_in", DEEPTECH, "works in a deep-tech / emerging-technology area")
SDGI = P("impact_areas", "any_in", ["sdg", "sustainable development", "circular economy", "assistive technology"],
         "works on SDG / sustainability areas")

BASE_KA = ALL(RECOG, AGE10, TO100, label="meets the Karnataka startup definition and is registered with the Startup Cell")
BASE_TN = ALL(RECOG, LEGAL, AGE10, TO50, label="meets the Tamil Nadu startup definition and is StartupTN-recognised")

# ----------------------------------------------------------------------- rules
RULES = {}

# ---- Tamil Nadu
RULES.update({
    "TN-ELIG-001": R("eligibility", checks=[LEGAL]),
    "TN-ELIG-002": R("eligibility", checks=[AGE10]),
    "TN-ELIG-003": R("eligibility", checks=[TO50]),
    "TN-ELIG-004": R("eligibility", checks=[SPLIT]),
    "TN-ELIG-005": R("eligibility", checks=[INNOV]),
    "TN-ELIG-006": R("eligibility", checks=[SCALE]),
    "TN-ELIG-007": R("eligibility", checks=[RECOG]),
    "TN-FUND-001": R("benefit", gates=[BASE_TN, ANY(WOMEN, RURAL, GREEN, label="enhanced-support category")], needs=[EARLY]),
    "TN-FUND-002": R("benefit", gates=[BASE_TN, NONE(WOMEN, RURAL, GREEN, label="not in an enhanced-support category")], needs=[EARLY]),
    "TN-FUND-003": R("applies", gates=[BASE_TN], note="If TANSEED is received, the state takes a 3% support stake."),
    "TN-FUND-004": R("applies", gates=[BASE_TN], note="Applies if the company becomes a TANSEED beneficiary."),
    "TN-FUND-005": R("applies", gates=[BASE_TN, WOMEN], note="25% of TANSEED assistance is earmarked for women-led startups."),
    "TN-FUND-006": R("applies", gates=[BASE_TN, RURAL], note="10% of TANSEED assistance is earmarked for rural-impact startups."),
    "TN-FUND-007": R("discretionary", gates=[BASE_TN], needs=[GROWTH], note="TANSCALE investment is selective."),
    "TN-FUND-008": R("info", note="Programme size (10 growth-stage startups a year), not a company test."),
    "TN-FUND-009": R("info", note="Programme budget, not a company test."),
    "TN-SCST-001": R("benefit", gates=[BASE_TN, SCST]),
    "TN-SCST-002": R("info", note="Programme target (200 supported startups), not a benefit to a single company."),
    "TN-SCST-003": R("benefit", gates=[BASE_TN, SCST]),
    "TN-WOM-001": R("benefit", gates=[BASE_TN, WOMEN]),
    "TN-WOM-002": R("benefit", gates=[BASE_TN, WOMEN], needs=[P("incubated_in_govt_supported_incubator", "==", True, "uses a state-supported incubation centre")]),
    "TN-WOM-003": R("benefit", gates=[BASE_TN, WOMEN]),
    "TN-INCL-001": R("benefit", gates=[BASE_TN, TRANS]),
    "TN-INCL-002": R("benefit", gates=[BASE_TN, TRANS]),
    "TN-PROC-001": R("benefit", gates=[BASE_TN]),
    "TN-PROC-002": R("benefit", gates=[BASE_TN]),
    "TN-PROC-003": R("benefit", gates=[BASE_TN]),
    "TN-PROC-004": R("benefit", gates=[BASE_TN]),
    "TN-PROC-005": R("benefit", gates=[BASE_TN, MANUF]),
    "TN-IP-001": R("benefit", gates=[BASE_TN, PATENT], needs=[P("patent_stage", "known", label="patent filing / registration details")]),
    "TN-IP-002": R("benefit", gates=[BASE_TN, P("has_trademark", "==", True, "has a trademark filing / registration")]),
    "TN-COMP-001": R("benefit", gates=[BASE_TN]),
    "TN-COMP-002": R("benefit", gates=[BASE_TN]),
    "TN-COMP-003": R("benefit", gates=[BASE_TN], checks=[P("startup_recognition_age_years", "<=", 3, "within 3 years of state recognition")]),
    "TN-COMP-004": R("benefit", gates=[BASE_TN], checks=[P("startup_recognition_age_years", "<=", 3, "within the 3-year booster-kit period")]),
    "TN-MFG-001": R("benefit", gates=[BASE_TN, MANUF]),
    "TN-MFG-002": R("benefit", gates=[BASE_TN, MANUF]),
    "TN-MFG-003": R("benefit", gates=[BASE_TN, MANUF, P("employee_count", ">", 20, "more than 20 employees")]),
    "TN-MFG-004": R("benefit", gates=[BASE_TN, MANUF]),
    "TN-MFG-005": R("discretionary", gates=[BASE_TN], needs=[P("is_msme", "==", True, "MSME / SME-exchange listing eligibility")]),
    "TN-INFRA-001": R("discretionary", gates=[BASE_TN], note="Subsidised facilities; no automatic entitlement to a specific facility."),
    "TN-INFRA-002": R("discretionary", gates=[BASE_TN], note="Innovation infrastructure; facility-specific eligibility is not automatic."),
    "TN-POL-001": R("info", note="Policy validity period."),
})

# ---- Karnataka
RULES.update({
    "KA-ELIG-001": R("eligibility", checks=[RECOG]),
    "KA-ELIG-002": R("eligibility", checks=[LEGAL, INCORP]),
    "KA-ELIG-003": R("eligibility", checks=[TO100]),
    "KA-ELIG-004": R("eligibility", checks=[AGE10]),
    "KA-ELIG-005": R("eligibility", checks=[INNOV]),
    "KA-ELIG-006": R("eligibility", checks=[SPLIT]),
    "KA-ELIG-007": R("eligibility", checks=[AGE10], duplicate_of="KA-ELIG-004"),
    "KA-ELIG-008": R("eligibility", checks=[TO100], duplicate_of="KA-ELIG-003"),
    "KA-FUND-001": R("benefit", gates=[BASE_KA], needs=[EARLY]),
    "KA-FUND-002": R("applies", gates=[BASE_KA, ANY(DEEP, SDGI, label="deep-tech / assistive / SDG area")],
                     note="10% of the Idea2PoC fund is earmarked for these areas."),
    "KA-FUND-003": R("benefit", gates=[BASE_KA], needs=[P("state.elevate_programme_recognised", "==", True, "recognised under the ELEVATE programme")]),
    "KA-FUND-004": R("discretionary", gates=[BASE_KA, DEEP], note="Venture-capital funding is competitive."),
    "KA-FUND-005": R("benefit", gates=[BASE_KA, BEYOND], needs=[GROWTH]),
    "KA-FUND-006": R("info", note="Platform the government will create; not a company test."),
    "KA-WOM-001": R("benefit", gates=[BASE_KA, WOMEN, BEYOND]),
    "KA-WOM-002": R("applies", gates=[BASE_KA, WOMEN], note="25% of the venture-capital fund is earmarked for women startups."),
    "KA-WOM-003": R("benefit", gates=[BASE_KA, WOMEN]),
    "KA-WOM-004": R("applies", gates=[BASE_KA, WOMEN], note="20% of seats at supported incubators are reserved for women startups."),
    "KA-WOM-005": R("benefit", gates=[BASE_KA, WOMEN]),
    "KA-SOC-001": R("benefit", gates=[BASE_KA, SCST]),
    "KA-SOC-002": R("benefit", gates=[BASE_KA, OBCMIN]),
    "KA-RURAL-001": R("info", note="Funding for a Rural Innovation Centre at an institution; not an individual company benefit."),
    "KA-RURAL-002": R("benefit", gates=[BASE_KA, P("hires_interns_from_beyond_bengaluru", "==", True, "hires interns from Beyond Bengaluru")]),
    "KA-RURAL-003": R("benefit", gates=[BASE_KA, P("hires_interns_from_beyond_bengaluru", "==", True, "hires interns from Beyond Bengaluru")],
                      checks=[P("intern_duration_months", ">=", 6, "internship of at least 6 months")]),
    "KA-RURAL-004": R("benefit", gates=[BASE_KA, P("hires_interns_from_beyond_bengaluru", "==", True, "hires interns from Beyond Bengaluru")],
                      checks=[P("has_availed_rural_internship_subsidy", "==", False, "has not already used the internship subsidy")]),
    "KA-GCK-001": R("info", note="Challenge opportunity; participation is not automatic eligibility."),
    "KA-GCK-002": R("benefit", gates=[BASE_KA, P("grand_challenge_winner", "==", True, "won a Grand Challenge")]),
    "KA-GCK-003": R("benefit", gates=[BASE_KA, P("grand_challenge_winner", "==", True, "won a Grand Challenge")]),
    "KA-CIRC-001": R("benefit", gates=[BASE_KA, P("has_circular_economy_focus", "==", True, "works on circular economy")]),
    "KA-CIRC-002": R("benefit", gates=[BASE_KA, P("has_circular_economy_focus", "==", True, "works on circular economy")]),
    "KA-CIRC-003": R("discretionary", gates=[BASE_KA, SDGI], note="Acceleration-programme places are competitive."),
    "KA-EODB-001": R("benefit", gates=[BASE_KA]),
    "KA-EODB-002": R("benefit", gates=[BASE_KA, P("has_women_night_shift_operations", "==", True, "runs 3-shift operations with women at night")]),
    "KA-PROC-001": R("benefit", gates=[BASE_KA]),
    "KA-SAND-001": R("benefit", gates=[BASE_KA, P("is_sandbox_operator", "==", True, "is a regulatory-sandbox operator")]),
    "KA-SAND-002": R("benefit", gates=[BASE_KA, P("is_sandbox_participant", "==", True, "participates in a regulatory sandbox")]),
    "KA-SGST-001": R("benefit", gates=[BASE_KA, BEYOND, INCUB]),
    "KA-SGST-002": R("benefit", gates=[BASE_KA], checks=[P("annual_turnover_inr", "<=", 1e7, "annual turnover ≤ ₹1 crore (SGST reimbursement cap)")]),
    "KA-SGST-003": R("benefit", gates=[BASE_KA], checks=[P("incubation_age_years", "<=", 3, "within the first 3 years of being incubated")]),
    "KA-MKT-001": R("benefit", gates=[BASE_KA, P("intl_marketing_spend_inr", ">", 0, "has international marketing spend")]),
    "KA-MKT-002": R("benefit", gates=[BASE_KA, P("intl_marketing_spend_inr", ">", 0, "has international marketing spend")]),
    "KA-IP-001": R("benefit", gates=[BASE_KA, PATENT], checks=[INCUB]),
    "KA-IP-002": R("benefit", gates=[BASE_KA, P("has_foreign_patent", "==", True, "holds a foreign patent")]),
    "KA-IP-003": R("benefit", gates=[BASE_KA, PATENT], checks=[P("patent_stage", "known", label="patent filing stage")]),
    "KA-IP-004": R("benefit", gates=[BASE_KA, PATENT], checks=[P("patent_stage", "==", "granted", "patent has been granted")]),
    "KA-QC-001": R("benefit", gates=[BASE_KA, BEYOND]),
    "KA-QC-002": R("benefit", gates=[BASE_KA], checks=[P("quality_certification_spend_inr", "known", label="has certification expenses")]),
    "KA-QC-003": R("benefit", gates=[BASE_KA], checks=[P("quality_certification_count", "<=", 3, "at most 3 quality certifications")]),
    "KA-WOM-006": R("benefit", gates=[BASE_KA], checks=[P("women_ownership_pct", ">=", 51, "women hold at least 51% stake")]),
    "KA-WOM-007": R("benefit", gates=[BASE_KA, P("women_ownership_pct", "<", 51, "women stake below 51%")],
                    needs=[P("women_employment_pct", ">=", 51, "at least 51% of jobs go to women")]),
})

if __name__ == "__main__":
    import pandas as pd

    ids = set(pd.read_csv("data/state_policies/state_requirements_canonical.csv").requirement_id)
    missing, extra = sorted(ids - set(RULES)), sorted(set(RULES) - ids)
    if missing or extra:
        raise SystemExit(f"rules out of sync with requirements: missing={missing} extra={extra}")
    with open("data/state_policies/profile_rules.json", "w", encoding="utf-8") as f:
        json.dump(RULES, f, indent=1, ensure_ascii=False)
    print(f"{len(RULES)} rules written to data/state_policies/profile_rules.json")

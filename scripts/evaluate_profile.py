"""
scripts/evaluate_profile.py — Module 1 report.

    python scripts/evaluate_profile.py                       # all demo profiles + agreement with the hand labels
    python scripts/evaluate_profile.py --profile data/profiles/steelforge_components.json --details
    python scripts/evaluate_profile.py --report results/profile_eval_report.md

Part 1  Agreement with Sreeja's hand labels (AgriVision, the profile she evaluated).
        Disagreements are REVIEW ITEMS, not errors: they are either a rule to fix, a profile fact the label assumed
        but never stated, or a label to reconsider.
Part 2  Per-state summary for every demo profile. Eligibility failures, confirmed benefits and missing information
        are reported separately — there is deliberately no single "best state" number.
"""
import argparse
import glob
import os
import sys
from collections import Counter

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.company_profile import CompanyProfile  # noqa: E402
from core.profile_eval import evaluate_profile, load_rules, load_state_requirements, summarize  # noqa: E402

VERDICTS = ["PASS", "APPLIES", "POTENTIAL", "UNKNOWN", "NOT_APPLICABLE", "INFO", "FAIL"]
GOLD = {"Tamil Nadu": ("data/state_policies/tamil_nadu_state_fit.xlsx", "TN Evaluation", "result", "reasoning"),
        "Karnataka": ("data/state_policies/karnataka_state_fit.xlsx", "KA Evaluation", "result", "reason")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=None, help="evaluate one profile JSON instead of all")
    ap.add_argument("--details", action="store_true", help="print every verdict with its reasoning")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    reqs = load_state_requirements()
    rules = load_rules()
    by_state = {}
    for r in reqs:
        by_state.setdefault(r["jurisdiction"], []).append(r)
    paths = [a.profile] if a.profile else sorted(glob.glob("data/profiles/*.json"))
    out = ["# Module 1 report — state requirements vs company profile\n"]

    # ---------------- Part 1: agreement with the hand labels
    agri = CompanyProfile.load("data/profiles/agrivision_ai.json")
    if not a.profile or "agrivision" in a.profile:
        out.append("## Part 1 — agreement with Sreeja's hand labels (AgriVision AI)\n")
        out.append("Rules were written from the policy wording, not from these labels. Differences are review items.\n")
        allrows, conf = [], Counter()
        for state, items in by_state.items():
            path, sheet, rcol, wcol = GOLD[state]
            if not os.path.exists(path):
                continue
            gold = pd.read_excel(path, sheet_name=sheet).set_index("requirement_id")
            for c in evaluate_profile(agri, items, rules):
                if c.requirement_id in gold.index:
                    g = str(gold.loc[c.requirement_id, rcol]).strip()
                    allrows.append((state, c.requirement_id, g, c.verdict.value, str(gold.loc[c.requirement_id, wcol]), c.reasoning))
                    conf[(g, c.verdict.value)] += 1
        n = len(allrows)
        agree = sum(g == p for _, _, g, p, _, _ in allrows)
        out.append(f"Overall: **{agree}/{n} = {agree / n:.1%}** requirements get the same verdict.\n")
        for state in by_state:
            rows = [r for r in allrows if r[0] == state]
            if rows:
                out.append(f"- {state}: {sum(r[2] == r[3] for r in rows)}/{len(rows)}")
        out.append("\n### Confusion (rows = hand label, columns = engine)\n")
        out.append("| hand \\ engine | " + " | ".join(VERDICTS) + " |\n|---|" + "---|" * len(VERDICTS))
        for g in VERDICTS:
            if any(conf[(g, p)] for p in VERDICTS):
                out.append(f"| {g} | " + " | ".join(str(conf[(g, p)]) or "0" for p in VERDICTS) + " |")
        diff = [r for r in allrows if r[2] != r[3]]
        out.append(f"\n### Disagreements ({len(diff)})\n")
        out.append("| requirement | hand label | engine | hand reasoning | engine reasoning |\n|---|---|---|---|---|")
        for state, rid, g, p, gr, pr in diff:
            out.append(f"| {rid} | {g} | {p} | {gr[:110]} | {pr[:140]} |")
        out.append("")

    # ---------------- Part 2: per-state summary for every profile
    from modules.state_fit import evaluate_for_state

    out.append("## Part 2 — per-state summary for each demo profile\n")
    out.append("Evaluated as if the company registers and incorporates in each state (registration is a step to take, "
               "not a reason a state is unsuitable). Mirror rows are excluded. `needs info` = a fact the rules depend on is "
               "missing; it is never counted against a state. There is deliberately no single score.\n")
    out.append("| profile | state | intrinsic eligibility failures | steps to take | confirmed (PASS) | policy-level (APPLIES) | POTENTIAL | needs info | N/A | FAIL |\n|---|---|---|---|---|---|---|---|---|---|")
    detail = []
    for path in paths:
        prof = CompanyProfile.load(path)
        for state in by_state:
            res = evaluate_for_state(prof, state, reqs, if_registered=True)
            sm, c = res["summary"], res["summary"]["counts"]
            out.append(f"| {prof.company_name} | {state} | {', '.join(sm['eligibility_failures']) or 'none'} | {', '.join(sm['actions_required']) or 'none'} | "
                       f"{c['PASS']} | {c['APPLIES']} | {c['POTENTIAL']} | {c['UNKNOWN']} | {c['NOT_APPLICABLE']} | {c['FAIL']} |")
            if a.details:
                detail.append(f"\n### {prof.company_name} — {state}\n")
                for ck in res["checks"]:
                    detail.append(f"- **{ck.requirement_id}** {ck.verdict.value}: {ck.reasoning} (p.{ck.page_number})")
    out.extend(detail)

    out.append("\n## Part 3 — facts that would settle the most open requirements\n")
    out.append("Each fact below is missing from the profile and would resolve the listed number of UNKNOWN / POTENTIAL requirements. "
               "This is the questionnaire to give the company.\n")
    for path in paths:
        prof = CompanyProfile.load(path)
        out.append(f"**{prof.company_name}**\n")
        for state in by_state:
            res = evaluate_for_state(prof, state, reqs, if_registered=True)
            top = res["summary"]["facts_to_provide"][:8]
            out.append(f"- {state}: " + (", ".join(f"`{t['fact']}` ({t['would_help']})" for t in top) or "nothing missing"))
        out.append("")
    text = "\n".join(out)
    print(text)
    if a.report:
        os.makedirs(os.path.dirname(a.report) or ".", exist_ok=True)
        open(a.report, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()

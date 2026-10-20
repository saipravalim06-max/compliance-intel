"""
Module 1: State Fit — which state's startup policy suits this company?

    company profile  +  state requirements (data/state_policies)  +  rules (profile_rules.json)
        -> one verdict per requirement, with the profile facts used, the policy evidence and page number

The question here is "where should we START", so registering with the state startup agency and incorporating
there are treated as STEPS TO TAKE (reported as `actions_required`), not as reasons a state is unsuitable.
`if_registered=True` (default) evaluates the company as if it had taken those steps; pass False to evaluate
the company exactly as stated.

There is deliberately no single "best state" score. A state is described by:
    intrinsic eligibility failures  (age, turnover, legal form ... — cannot be fixed by a form)
    actions required                (register / incorporate)
    benefits confirmed, benefits potential
    information still needed        (facts missing from the profile; never counted against the state)
`rank_states` orders by those in that priority, as an aid to reading — not as a score.
"""
from typing import Dict, List, Optional

from core.company_profile import CompanyProfile
from core.profile_eval import (assume_registered, evaluate_profile, load_rules, load_state_requirements,
                               summarize)


def evaluate_for_state(profile: CompanyProfile, state: str, requirements: Optional[List[dict]] = None,
                       if_registered: bool = True) -> Dict:
    requirements = requirements or load_state_requirements()
    items = [r for r in requirements if r["jurisdiction"] == state]
    if not items:
        raise ValueError(f"no requirements for state: {state}")
    rules = load_rules()
    as_stated = summarize(evaluate_profile(profile, items, rules), rules)
    used = assume_registered(profile, state) if if_registered else profile
    checks = evaluate_profile(used, items, rules)
    summary = summarize(checks, rules)
    summary["actions_required"] = as_stated["actions_required"]
    return {"state": state, "if_registered": if_registered, "summary": summary, "checks": checks}


def compare_states(profile: CompanyProfile, states: Optional[List[str]] = None,
                   if_registered: bool = True) -> List[Dict]:
    requirements = load_state_requirements()
    states = states or sorted({r["jurisdiction"] for r in requirements})
    return [evaluate_for_state(profile, s, requirements, if_registered) for s in states]


def rank_states(results: List[Dict]) -> List[Dict]:
    """Reading order, not a score: fewer intrinsic failures, then more confirmed benefits, then more
    potential benefits, then fewer missing facts."""
    def key(r):
        s = r["summary"]
        return (len(s["eligibility_failures"]), -s["benefits_confirmed"], -s["benefits_potential"], len(s["needs_information"]))
    return sorted(results, key=key)


def describe(results: List[Dict]) -> str:
    lines = []
    for r in rank_states(results):
        s, c = r["summary"], r["summary"]["counts"]
        lines.append(f"{r['state']}: " + ("eligible as a startup" if s["eligible_as_startup"]
                                           else "NOT eligible (" + ", ".join(s["eligibility_failures"]) + ")"))
        if s["actions_required"]:
            lines.append(f"  steps to take: {', '.join(s['actions_required'])} (register / incorporate)")
        lines.append(f"  benefits confirmed: {s['benefits_confirmed']} | potential: {s['benefits_potential']} | "
                     f"policy-level allocations: {c['APPLIES']} | needs information: {len(s['needs_information'])} | FAIL: {c['FAIL']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "data/profiles/agrivision_ai.json"
    profile = CompanyProfile.load(path)
    print(f"{profile.company_name}  (assuming it registers in each state)\n")
    print(describe(compare_states(profile)))

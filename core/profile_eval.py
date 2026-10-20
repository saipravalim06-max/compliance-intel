"""
core/profile_eval.py — Module 1: evaluate state requirements against a company profile.

Each requirement has a declarative rule (data/state_policies/profile_rules.json):

    kind     eligibility | benefit | applies | discretionary | info
    gates    "does this requirement concern this company at all?"
    checks   "does the company satisfy the condition?"
    needs    "extra evidence before an award can be claimed"
    duplicate_of   a mirror row of another requirement (not counted twice)

Verdict logic (first match wins) — the one rule that matters: a MISSING FACT NEVER BECOMES FAIL.

    info                                   -> INFO
    any gate False                         -> NOT_APPLICABLE
    any check False                        -> FAIL
    any gate or check unknown (None)       -> UNKNOWN      (a fact the rule depends on is missing)
    any need False                         -> NOT_APPLICABLE
    any need unknown (None)                -> POTENTIAL    (eligible so far, more evidence needed)
    kind discretionary                     -> POTENTIAL    (award is competitive / not automatic)
    kind applies                           -> APPLIES      (a policy-level allocation or programme feature)
    otherwise                              -> PASS

A predicate is {"fact", "op", "value", "label"} or a group: {"all_of": [...]}, {"any_of": [...]}, {"none_of": [...]}.
Facts are CompanyProfile fields, or "state.<name>" for per-state facts.
"""
import json
import os
from typing import Dict, List, Optional, Tuple

from core.company_profile import CompanyProfile
from core.schemas import ProfileCheck
from core.taxonomy import FitVerdict

RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "state_policies", "profile_rules.json")


# ------------------------------------------------------------------ predicates
def _fact(profile: CompanyProfile, name: str, state: str):
    if name.startswith("state."):
        return (profile.state_context.get(state) or {}).get(name[6:])
    return getattr(profile, name, None)


def _fmt(v) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) >= 1000:
        return f"{v:,}"
    return str(v)


def _missing(pred: dict, profile: CompanyProfile, state: str) -> List[str]:
    """Names of the profile facts that could still change this predicate's outcome (stated facts and
    sub-conditions that are already decisive are not reported)."""
    for key in ("all_of", "any_of", "none_of"):
        if key in pred:
            vals = [eval_pred(p, profile, state)[0] for p in pred[key]]
            decided = (key == "all_of" and False in vals) or (key != "all_of" and True in vals)
            return [] if decided else [f for p in pred[key] for f in _missing(p, profile, state)]
    return [pred["fact"]] if _fact(profile, pred["fact"], state) is None else []


def eval_pred(pred: dict, profile: CompanyProfile, state: str) -> Tuple[Optional[bool], str]:
    """Return (True | False | None for unknown, human-readable explanation)."""
    if "all_of" in pred:
        subs = [eval_pred(p, profile, state) for p in pred["all_of"]]
        vals = [v for v, _ in subs]
        res = False if any(v is False for v in vals) else (None if any(v is None for v in vals) else True)
        label = pred.get("label") or "all of the following"
        detail = "; ".join(t for v, t in subs if v is not True)
        return res, label + (" ✓" if res is True else f" — {detail}")
    if "any_of" in pred or "none_of" in pred:
        key = "any_of" if "any_of" in pred else "none_of"
        subs = [eval_pred(p, profile, state) for p in pred[key]]
        vals = [v for v, _ in subs]
        if key == "any_of":
            res = True if any(v is True for v in vals) else (None if any(v is None for v in vals) else False)
        else:
            res = False if any(v is True for v in vals) else (None if any(v is None for v in vals) else True)
        word = "any of" if key == "any_of" else "none of"
        return res, f"{word}: " + "; ".join(t for _, t in subs)

    fact, op, want = pred["fact"], pred["op"], pred.get("value")
    have = _fact(profile, fact, state)
    label = pred.get("label") or f"{fact} {op} {_fmt(want)}"
    if have is None:
        return None, f"{label} — not stated in the profile"
    if op == "known":
        return True, f"{label} (value: {_fmt(have)})"
    try:
        if op == "==":
            ok = have == want
        elif op == "!=":
            ok = have != want
        elif op == "<=":
            ok = have <= want
        elif op == ">=":
            ok = have >= want
        elif op == "<":
            ok = have < want
        elif op == ">":
            ok = have > want
        elif op == "in":
            ok = str(have).lower() in [str(w).lower() for w in want]
        elif op == "any_in":
            ok = bool({str(h).lower() for h in have} & {str(w).lower() for w in want})
        else:
            raise ValueError(f"unknown op {op}")
    except TypeError:
        return None, f"{label} — value not comparable"
    shown = _fmt(have) if not isinstance(have, list) else ", ".join(map(str, have))
    return ok, f"{label} (company: {shown}) → {'met' if ok else 'not met'}"


# ------------------------------------------------------------------- verdicts
_RULES: Optional[Dict] = None


def load_rules(path: Optional[str] = None) -> Dict:
    """Load the rule table (cached for the default path)."""
    global _RULES
    if path is not None:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    if _RULES is None:
        with open(RULES_PATH, encoding="utf-8") as f:
            _RULES = json.load(f)
    return _RULES


def evaluate_requirement(req: dict, profile: CompanyProfile, rule: dict) -> ProfileCheck:
    state = req["jurisdiction"]
    kind = rule.get("kind", "benefit")
    groups = {g: [eval_pred(p, profile, state) for p in rule.get(g, [])] for g in ("gates", "checks", "needs")}
    rule_text = " AND ".join(p.get("label") or p.get("fact", "condition") for g in ("gates", "checks", "needs") for p in rule.get(g, [])) or None
    facts = "; ".join(t for g in ("gates", "checks", "needs") for _, t in groups[g])

    def result(verdict: FitVerdict, why: str, actionable: Optional[bool] = None) -> ProfileCheck:
        miss = sorted({f for g in ("gates", "checks", "needs") for p in rule.get(g, []) for f in _missing(p, profile, state)})
        return ProfileCheck(
            missing_facts=miss if verdict in (FitVerdict.UNKNOWN, FitVerdict.POTENTIAL) and miss else None,
            requirement_id=req["requirement_id"], jurisdiction=state, verdict=verdict, actionable=actionable,
            company_value=facts or None, rule=rule_text,
            reasoning=(why + (" Duplicate of " + rule["duplicate_of"] + "." if rule.get("duplicate_of") else "")).strip(),
            evidence_text=req.get("source_text"), page_number=req.get("page_number"), source_url=req.get("source_url"),
        )

    vals = lambda g: [v for v, _ in groups[g]]  # noqa: E731
    texts = lambda g, want: "; ".join(t for v, t in groups[g] if v is want)  # noqa: E731

    if kind == "info":
        return result(FitVerdict.INFO, rule.get("note") or "Informational provision, not a company pass/fail test.")
    if False in vals("gates"):
        return result(FitVerdict.NOT_APPLICABLE, "Does not apply: " + texts("gates", False) + ".")
    if False in vals("checks"):
        failing = [p for p, (v, _) in zip(rule.get("checks", []), groups["checks"]) if v is False]
        only_actions = bool(failing) and all(p.get("actionable") for p in failing)
        return result(FitVerdict.FAIL, "Condition not satisfied: " + texts("checks", False) + ".", only_actions)
    if None in vals("gates") or None in vals("checks"):
        missing = texts("gates", None) + ("; " if None in vals("gates") and None in vals("checks") else "") + texts("checks", None)
        return result(FitVerdict.UNKNOWN, "Cannot conclude: " + missing + ".")
    if False in vals("needs"):
        return result(FitVerdict.NOT_APPLICABLE, "Does not apply: " + texts("needs", False) + ".")
    if None in vals("needs"):
        return result(FitVerdict.POTENTIAL, "Eligible so far, but more evidence is needed: " + texts("needs", None) + ".")
    if kind == "discretionary":
        return result(FitVerdict.POTENTIAL, rule.get("note") or "Category fits, but the award is competitive / not automatic.")
    if kind == "applies":
        return result(FitVerdict.APPLIES, rule.get("note") or "Applies to this company; the conditions are met or are policy-level.")
    return result(FitVerdict.PASS, "All stated conditions are met.")


def load_state_requirements(path: Optional[str] = None) -> List[dict]:
    """Read data/state_policies/state_requirements_canonical.csv as clean dicts (NaN -> None, page -> int)."""
    import math
    import pandas as pd

    path = path or os.path.join(os.path.dirname(RULES_PATH), "state_requirements_canonical.csv")
    rows = []
    for rec in pd.read_csv(path).to_dict("records"):
        rec = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in rec.items()}
        if rec.get("page_number") is not None:
            rec["page_number"] = int(rec["page_number"])
        rows.append(rec)
    return rows


def evaluate_profile(profile: CompanyProfile, requirements: List[dict], rules: Optional[Dict] = None) -> List[ProfileCheck]:
    """Evaluate every requirement (dicts with the canonical-CSV columns). A requirement with no rule is
    reported UNKNOWN with an explicit 'no rule written' reason instead of being silently skipped."""
    rules = rules or load_rules()
    out = []
    for req in requirements:
        rule = rules.get(req["requirement_id"])
        if rule is None:
            out.append(ProfileCheck(requirement_id=req["requirement_id"], jurisdiction=req["jurisdiction"],
                                    verdict=FitVerdict.UNKNOWN, reasoning="No evaluation rule has been written for this requirement.",
                                    evidence_text=req.get("source_text"), page_number=req.get("page_number"),
                                    source_url=req.get("source_url")))
        else:
            out.append(evaluate_requirement(req, profile, rule))
    return out


def assume_registered(profile: CompanyProfile, state: str) -> CompanyProfile:
    """What-if copy of the profile: the company registers with the state startup agency and incorporates there.
    Use it for 'where should we START', where registration is a step to take, not a reason a state is unsuitable."""
    import copy
    p = copy.deepcopy(profile)
    ctx = dict(p.state_context.get(state) or {})
    ctx["recognized_by_state_startup_agency"] = True
    ctx["incorporated_in_state"] = True
    p.state_context = {**p.state_context, state: ctx}
    return p


def summarize(checks: List[ProfileCheck], rules: Optional[Dict] = None) -> Dict:
    """Counts per verdict (mirror rows excluded) plus the failing and information-needed requirements.
    Deliberately NOT a single 'best state' number: eligibility failures, matched benefits and missing
    information are different things and are reported separately."""
    rules = rules or load_rules()
    counted = [c for c in checks if not rules.get(c.requirement_id, {}).get("duplicate_of")]
    by = {v.value: 0 for v in FitVerdict}
    for c in counted:
        by[c.verdict.value] += 1
    kinds = {c.requirement_id: rules.get(c.requirement_id, {}).get("kind") for c in counted}
    elig = [c for c in counted if c.verdict == FitVerdict.FAIL and kinds[c.requirement_id] == "eligibility"]
    intrinsic = [c.requirement_id for c in elig if not c.actionable]
    actions = [c.requirement_id for c in elig if c.actionable]
    from collections import Counter
    need = Counter(f for c in counted for f in (c.missing_facts or []))
    return {
        "counts": by,
        "facts_to_provide": [{"fact": f, "would_help": n} for f, n in need.most_common()],
        "eligible_as_startup": not intrinsic,          # no intrinsic eligibility failure (age, turnover, legal form, ...)
        "eligibility_failures": intrinsic,
        "actions_required": actions,                   # e.g. register with the state startup agency
        "eligible_as_startup_if_registered": not intrinsic,
        "benefits_confirmed": sum(1 for c in counted if c.verdict == FitVerdict.PASS and kinds[c.requirement_id] == "benefit"),
        "benefits_potential": sum(1 for c in counted if c.verdict == FitVerdict.POTENTIAL),
        "needs_information": [c.requirement_id for c in counted if c.verdict == FitVerdict.UNKNOWN],
        "failures": [c.requirement_id for c in counted if c.verdict == FitVerdict.FAIL],
    }

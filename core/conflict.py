"""
core/conflict.py — structured conflict reasoning (contract requirement vs policy requirement).

Embedding similarity only says two texts are about the same topic. Whether they
conflict is decided here, over structured fields, with an explanation that points
at the exact numbers / words involved.

detect_conflict() returns a dict (old keys kept: conflict, severity, reason,
contract_evidence, policy_evidence) plus:
    label        CONFLICT | NO_CONFLICT | PARTIAL_CONFLICT | UNCERTAIN
    rules        which rules fired, e.g. ["NUMERIC:TERMINATION_NOTICE"]
    comparisons  one entry per numeric/authorization comparison made

Rules
    AUTH        contract allows without authorization, policy requires it (or reverse)
    NUMERIC     same kind of quantity (notice period, liability cap, ...), compared
                in the direction the policy sets (floor or ceiling) after unit conversion
    MODALITY    policy prohibits what the contract permits (same action AND object)
UNCERTAIN is returned, never a guess, when the two sides are not comparable
(different units such as months-of-fees vs a fixed amount, different rate periods,
no number on one side) or when business-day vs calendar-day results are borderline.
"""
from typing import List, Optional

from core.quantities import KIND_DEFAULT_BOUND, compare_values
from core.schemas import Requirement
from core.taxonomy import Unit

_EVENT_PER = {"occurrence": "event", "incident": "event", "claim": "event"}
_PER_IGNORED_KINDS = {"INSURANCE_GENERAL", "INSURANCE_CYBER", "INSURANCE_PROFESSIONAL",
                      "LIABILITY_CAP", "LIABILITY_CAP_AMOUNT"}


_DISPOSAL = {"share", "disclose", "provide", "transfer", "assign", "submit"}


def _same_action(a: Optional[str], b: Optional[str]) -> bool:
    """Authorization rules are only comparable when both sides are about the same kind of act."""
    return a is None or b is None or a == b or (a in _DISPOSAL and b in _DISPOSAL)


def _norm_per(p: Optional[str]) -> Optional[str]:
    return _EVENT_PER.get(p, p)


def _severity(gap: float, inferred: bool) -> str:
    if inferred or gap >= 0.5:
        return "HIGH"
    return "MEDIUM" if gap >= 0.2 else "LOW"


def _fmt(v: float, unit: str, per: Optional[str]) -> str:
    num = f"{v:,.0f}" if abs(v) >= 1000 and float(v).is_integer() else f"{v:g}"
    name = {"USD": "USD", "INR": "INR"}.get(unit, unit.lower().replace("_", " "))
    return f"{num} {name}" + (f" per {per}" if per else "")


def _compare_quantities(contract: Requirement, policy: Requirement) -> List[dict]:
    out = []
    for cq in contract.quantities or []:
        for pq in policy.quantities or []:
            kind = pq.get("kind")
            if not kind or cq.get("kind") != kind:
                continue
            c_unit, p_unit = Unit(cq["unit"]), Unit(pq["unit"])
            entry = {"kind": kind, "contract": _fmt(cq["value"], cq["unit"], cq.get("per")),
                     "policy": _fmt(pq["value"], pq["unit"], pq.get("per"))}

            if kind not in _PER_IGNORED_KINDS and _norm_per(cq.get("per")) != _norm_per(pq.get("per")):
                out.append({**entry, "result": "INCOMPARABLE",
                            "why": f"the figures are measured per different periods "
                                   f"({cq.get('per') or 'unspecified'} vs {pq.get('per') or 'unspecified'})"})
                continue
            c_val, status = compare_values(cq["value"], c_unit, pq["value"], p_unit)
            if status == "INCOMPARABLE":
                out.append({**entry, "result": "INCOMPARABLE",
                            "why": f"the units cannot be compared ({cq['unit'].lower()} vs {pq['unit'].lower()})"})
                continue
            bound = pq.get("bound") or KIND_DEFAULT_BOUND.get(kind)
            if bound is None:
                out.append({**entry, "result": "INCOMPARABLE", "why": "the policy does not state whether its figure is a minimum or a maximum"})
                continue

            p_val = pq["value"]
            if status == "APPROX":                       # business days <-> calendar days
                ratio = (c_val / p_val) if p_val else 0
                violated = ratio > 1.5 if bound == "UPPER" else ratio < 0.67
                satisfied = ratio < 0.67 if bound == "UPPER" else ratio > 1.5
                if not violated and not satisfied:
                    out.append({**entry, "result": "INCOMPARABLE",
                                "why": "business days and calendar days differ and the figures are too close to call"})
                    continue
            else:
                violated = c_val > p_val + 1e-9 if bound == "UPPER" else c_val < p_val - 1e-9

            gap = abs(c_val - p_val) / p_val if p_val else 1.0
            word = "no more than" if bound == "UPPER" else "at least"
            if violated:
                what = " (inferred from immediate termination)" if cq.get("inferred") else ""
                out.append({**entry, "result": "VIOLATION", "bound": bound, "severity": _severity(gap, bool(cq.get("inferred"))),
                            "why": f"{kind.replace('_', ' ').lower()}: the contract gives {entry['contract']}{what}, "
                                   f"but the policy requires {word} {entry['policy']}"})
            else:
                out.append({**entry, "result": "SATISFIED", "bound": bound,
                            "why": f"{kind.replace('_', ' ').lower()}: {entry['contract']} meets the policy's {word} {entry['policy']}"})
    return out


def detect_conflict(contract: Requirement, policy: Requirement) -> dict:
    reasons: List[str] = []
    rules: List[str] = []
    comparisons: List[dict] = []
    severities: List[str] = []
    violations = satisfied = 0
    partial_scope = None
    stricter_only = False

    # ---- AUTH ------------------------------------------------------------
    auth_ok = _same_action(contract.action, policy.action)
    if not auth_ok:
        pass
    elif contract.authorization == "NOT_REQUIRED" and policy.authorization == "REQUIRED":
        reasons.append("The contract permits the action without prior authorization, while the company policy requires prior authorization.")
        rules.append("AUTH")
        severities.append("HIGH")
        violations += 1
        comparisons.append({"kind": "AUTHORIZATION", "contract": "not required", "policy": "required", "result": "VIOLATION"})
    elif contract.authorization == "REQUIRED" and policy.authorization == "NOT_REQUIRED":
        reasons.append("The contract requires prior authorization, while the company policy permits the action without it; "
                       "this is stricter than the policy and is a conflict only if it restricts the company's own freedom.")
        rules.append("AUTH_STRICTER")
        severities.append("LOW")
        violations += 1
        stricter_only = True
        comparisons.append({"kind": "AUTHORIZATION", "contract": "required", "policy": "not required", "result": "VIOLATION"})
    elif contract.authorization and contract.authorization == policy.authorization:
        satisfied += 1
        comparisons.append({"kind": "AUTHORIZATION", "contract": contract.authorization.lower().replace("_", " "),
                            "policy": policy.authorization.lower().replace("_", " "), "result": "SATISFIED"})

    # ---- MODALITY (same action AND same object only) -----------------------------
    same_topic = contract.action and contract.action == policy.action and contract.object and contract.object == policy.object
    if same_topic and not policy.authorization and not contract.authorization:
        if policy.obligation_type == "PROHIBITION" and contract.obligation_type == "PERMISSION":
            reasons.append(f"The policy prohibits '{policy.action}' of {policy.object}, but the contract permits it.")
            rules.append("MODALITY")
            severities.append("MEDIUM")
            violations += 1

    # ---- NUMERIC -----------------------------------------------------------
    seen, numeric = set(), []
    for c in _compare_quantities(contract, policy):
        key = (c["kind"], c["contract"], c["policy"], c["result"], c.get("why"))
        if key not in seen:
            seen.add(key)
            numeric.append(c)
    incomparable = [c for c in numeric if c["result"] == "INCOMPARABLE"]
    for c in numeric:
        comparisons.append(c)
        if c["result"] == "VIOLATION":
            reasons.append(c["why"][0].upper() + c["why"][1:] + ".")
            rules.append(f"NUMERIC:{c['kind']}")
            severities.append(c["severity"])
            violations += 1
        elif c["result"] == "SATISFIED":
            satisfied += 1
    if policy.applies_to and any(c["result"] == "VIOLATION" for c in numeric):
        partial_scope = policy.applies_to

    # ---- verdict ---------------------------------------------------------------
    order = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    severity = max(severities, key=order.get) if severities else "NONE"
    base = {"contract_evidence": contract.source_text, "policy_evidence": policy.source_text,
            "rules": rules, "comparisons": comparisons}

    if violations:
        if stricter_only and all(r == "AUTH_STRICTER" for r in rules):
            label = "PARTIAL_CONFLICT"
        elif partial_scope and not any(r in ("AUTH", "MODALITY") for r in rules):
            label = "PARTIAL_CONFLICT"
            reasons.append(f"This policy line only applies to {partial_scope}; the clause does not say whether that applies.")
        else:
            label = "CONFLICT"
        return {"conflict": True, "severity": severity, "reason": " ".join(reasons), "label": label, **base}

    if satisfied:
        return {"conflict": False, "severity": "NONE", "label": "NO_CONFLICT", **base,
                "reason": " ".join(c["why"][0].upper() + c["why"][1:] + "." for c in numeric if c["result"] == "SATISFIED")
                          or "The contract and the policy agree on the authorization requirement."}

    if incomparable:
        return {"conflict": False, "severity": "NONE", "label": "UNCERTAIN", **base,
                "reason": "Not comparable: " + "; ".join(c["why"] for c in incomparable) + "."}

    return {"conflict": False, "severity": "NONE", "label": "UNCERTAIN", **base,
            "reason": "No structured conflict was detected, and no comparable figure or authorization rule was found on both sides."}

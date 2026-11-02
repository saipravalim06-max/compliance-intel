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
import re
from typing import List, Optional

from core.quantities import KIND_DEFAULT_BOUND, compare_values
from core.schemas import Requirement
from core.taxonomy import Unit

_EVENT_PER = {"occurrence": "event", "incident": "event", "claim": "event"}
_PER_IGNORED_KINDS = {"INSURANCE_GENERAL", "INSURANCE_CYBER", "INSURANCE_PROFESSIONAL",
                      "LIABILITY_CAP", "LIABILITY_CAP_AMOUNT"}


_DISPOSAL = {"share", "disclose", "provide", "transfer", "assign", "submit"}

def _same_action(a: Optional[str], b: Optional[str]) -> bool:
    """Compare actions only when they are known and equivalent."""
    if not a or not b:
        return False

    if a == b:
        return True

    # Sharing and disclosing can describe the same data-handling action;
    # assigning and novating are interchangeable transfer concepts for contracts.
    pair = {a, b}
    if pair in ({"share", "disclose"}, {"assign", "novate"}, {"store", "transfer"}):
        return True
    return False

def _same_object(a: Optional[str], b: Optional[str]) -> bool:
    """Match known equivalent objects, including two unspecified objects."""
    if a is None or b is None:
        return a is None and b is None

    def normalize(value: str) -> str:
        value = value.lower().strip()
        value = value.replace("sub-processors", "subcontractors")
        value = value.replace("subprocessors", "subcontractors")
        value = re.sub(r"\bthe\s+", "", value)
        if "india" in value:
            return "laws of india"
        return value

    a_norm = normalize(a)
    b_norm = normalize(b)

    if a_norm == b_norm:
        return True

    data_objects = {
        "customer data",
        "confidential data",
        "customer or confidential data",
        "company or customer data",
        "personal data",
        "patient data",
        "clinical data",
        "health data",
        "customer information",
        "company information",
        "confidential information",
    }

    if a_norm in data_objects and b_norm in data_objects:
        return True

    publicity_objects = {
        "name or logo",
        "company name or logo",
        "company's name or logo",
        "marketing material",
        "publicity",
    }
    if a_norm in publicity_objects and b_norm in publicity_objects:
        return True

    if {a_norm, b_norm} <= {"agreement", "contract", "this agreement", "the agreement"}:
        return True

    if {a_norm, b_norm} <= {"services", "core services"}:
        return True

    return False

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
                # 1 business day ~ 1.4 calendar days (7/5).
                # Mark satisfied when converted value safely complies with the bound.
                # Mark violation when clearly exceeding the threshold.
                if bound == "UPPER":
                    if c_val <= p_val:
                        violated = False
                    elif c_val > p_val * 1.15:
                        violated = True
                    else:
                        out.append({**entry, "result": "INCOMPARABLE",
                                    "why": "business days and calendar days differ and the figures are too close to call"})
                        continue
                else: # bound == "LOWER"
                    if c_val >= p_val:
                        violated = False
                    elif c_val < p_val * 0.85:
                        violated = True
                    else:
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
    auth_ok = (
        _same_action(contract.action, policy.action)
        and _same_object(contract.object, policy.object)
        )
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
    comparable_numeric_kind = any(
        cq.get("kind")
        and cq.get("kind") == pq.get("kind")
        for cq in (contract.quantities or [])
        for pq in (policy.quantities or [])
        )
    same_topic = (
        contract.action
        and policy.action
        and _same_action(contract.action, policy.action)
        and _same_object(contract.object, policy.object)
        and not comparable_numeric_kind
        )

    if same_topic:
        # A policy prohibition can conflict with an explicit contract
        # permission even when the policy also requires authorization.
        if (
            policy.obligation_type == "PROHIBITION"
            and contract.obligation_type == "PERMISSION"
            and contract.authorization != "REQUIRED"
        ):
            act = "assignment or novation" if policy.action in ("assign", "novate") else policy.action
            obj_phrase = f" of {policy.object}" if policy.object and str(policy.object).lower() != "none" else ""
            reasons.append(
                f"The policy prohibits '{act}'{obj_phrase} "
                "without the required authorization, but the contract permits it."
            )
            rules.append("MODALITY")
            severities.append("MEDIUM")
            violations += 1


    # ---- GOVERNING LAW ----------------------------------------------------
    if contract.action == "govern" and policy.action == "govern":
        c_law = contract.object or "unspecified"
        p_law = policy.object or "unspecified"
        if _same_object(contract.object, policy.object):
            satisfied += 1
            comparisons.append({
                "kind": "GOVERNING_LAW",
                "contract": c_law,
                "policy": p_law,
                "result": "SATISFIED",
                "why": f"governing law: both contract and policy require {p_law}",
            })
        else:
            reasons.append(
                f"Governing law mismatch: the contract specifies {c_law}, "
                f"but the company policy requires {p_law}."
            )
            rules.append("GOVERNING_LAW")
            severities.append("HIGH")
            violations += 1
            comparisons.append({
                "kind": "GOVERNING_LAW",
                "contract": c_law,
                "policy": p_law,
                "result": "VIOLATION",
                "why": f"governing law: the contract specifies {c_law}, but the policy requires {p_law}",
            })

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
        sat_numeric = [c["why"][0].upper() + c["why"][1:] + "." for c in numeric if c.get("result") == "SATISFIED" and c.get("why")]
        sat_other = [c["why"][0].upper() + c["why"][1:] + "." for c in comparisons if c.get("result") == "SATISFIED" and c.get("why") and c not in numeric]
        reason_text = " ".join(sat_numeric + sat_other)
        if not reason_text:
            reason_text = "The contract and the policy agree on the authorization requirement."
        return {"conflict": False, "severity": "NONE", "label": "NO_CONFLICT", **base, "reason": reason_text}

    if incomparable:
        return {"conflict": False, "severity": "NONE", "label": "UNCERTAIN", **base,
                "reason": "Not comparable: " + "; ".join(c["why"] for c in incomparable) + "."}

    return {"conflict": False, "severity": "NONE", "label": "UNCERTAIN", **base,
            "reason": "No structured conflict was detected, and no comparable figure or authorization rule was found on both sides."}

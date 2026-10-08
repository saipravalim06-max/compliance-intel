from core.schemas import Requirement


def detect_conflict(
    contract: Requirement,
    policy: Requirement,
) -> dict:
    """
    Compare a contract requirement against a company policy requirement.

    This is the first rule-based conflict reasoning baseline.
    It deliberately reasons over structured fields instead of treating
    embedding similarity as proof of a conflict.
    """

    reasons = []
    severity = "NONE"

    # ---------------------------------------------------------
    # Rule 1: Authorization conflict
    # ---------------------------------------------------------

    if (
        contract.authorization == "NOT_REQUIRED"
        and policy.authorization == "REQUIRED"
    ):
        reasons.append(
            "The contract permits the action without prior authorization, "
            "while the company policy requires prior authorization."
        )
        severity = "HIGH"

    # ---------------------------------------------------------
    # Rule 2: Reverse authorization conflict
    # ---------------------------------------------------------

    elif (
        contract.authorization == "REQUIRED"
        and policy.authorization == "NOT_REQUIRED"
    ):
        reasons.append(
            "The contract requires prior authorization, while the company "
            "policy permits the action without prior authorization."
        )
        severity = "MEDIUM"

    # ---------------------------------------------------------
    # No conflict detected
    # ---------------------------------------------------------

    if not reasons:
        return {
            "conflict": False,
            "severity": "NONE",
            "reason": "No structured conflict was detected.",
            "contract_evidence": contract.source_text,
            "policy_evidence": policy.source_text,
        }

    return {
        "conflict": True,
        "severity": severity,
        "reason": " ".join(reasons),
        "contract_evidence": contract.source_text,
        "policy_evidence": policy.source_text,
    }
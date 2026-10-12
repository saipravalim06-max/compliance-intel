from core.schemas import Requirement


def _same_unit(contract: Requirement, policy: Requirement) -> bool:
    """
    Check whether both requirements use the same measurable unit.
    """
    if contract.unit is None or policy.unit is None:
        return False

    return contract.unit.lower() == policy.unit.lower()


def _numeric_conflict(
    contract: Requirement,
    policy: Requirement,
):
    """
    Detect conflicts between numeric contract and policy requirements.

    The policy requirement is treated as the governing constraint.

    Example:

        Contract: 7 days
        Policy:   >= 30 days

        7 < 30 -> conflict
    """

    if contract.threshold is None or policy.threshold is None:
        return None

    if not _same_unit(contract, policy):
        return None

    # ---------------------------------------------------------
    # Policy minimum requirement
    # ---------------------------------------------------------

    if policy.operator == ">=":
        if contract.threshold < policy.threshold:
            return (
                True,
                "HIGH",
                (
                    f"The contract specifies {contract.threshold:g} "
                    f"{contract.unit}, while the company policy requires "
                    f"at least {policy.threshold:g} {policy.unit}."
                ),
            )

    # ---------------------------------------------------------
    # Policy maximum requirement
    # ---------------------------------------------------------

    if policy.operator == "<=":
        if contract.threshold > policy.threshold:
            return (
                True,
                "HIGH",
                (
                    f"The contract specifies {contract.threshold:g} "
                    f"{contract.unit}, while the company policy allows "
                    f"at most {policy.threshold:g} {policy.unit}."
                ),
            )

    # ---------------------------------------------------------
    # Policy strict lower bound
    # ---------------------------------------------------------

    if policy.operator == ">":
        if contract.threshold <= policy.threshold:
            return (
                True,
                "HIGH",
                (
                    f"The contract specifies {contract.threshold:g} "
                    f"{contract.unit}, while the company policy requires "
                    f"more than {policy.threshold:g} {policy.unit}."
                ),
            )

    # ---------------------------------------------------------
    # Policy strict upper bound
    # ---------------------------------------------------------

    if policy.operator == "<":
        if contract.threshold >= policy.threshold:
            return (
                True,
                "HIGH",
                (
                    f"The contract specifies {contract.threshold:g} "
                    f"{contract.unit}, while the company policy requires "
                    f"less than {policy.threshold:g} {policy.unit}."
                ),
            )

    return None


def detect_conflict(
    contract: Requirement,
    policy: Requirement,
) -> dict:

    reasons = []
    severity = "NONE"

    # ---------------------------------------------------------
    # Authorization conflict
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
    # Numeric conflict
    # ---------------------------------------------------------

    numeric_result = _numeric_conflict(contract, policy)

    if numeric_result is not None:
        numeric_conflict, numeric_severity, numeric_reason = numeric_result

        if numeric_conflict:
            reasons.append(numeric_reason)

            if numeric_severity == "HIGH":
                severity = "HIGH"
            elif severity == "NONE":
                severity = numeric_severity

    # ---------------------------------------------------------
    # Final result
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
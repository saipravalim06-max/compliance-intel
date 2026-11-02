"""Compare an uploaded contract against uploaded company policies."""

import re
from pathlib import Path
from typing import Any, Optional

from core.engine import ingest_document
from core.matching import PolicyMatcher
from modules.contract_checker import check_clause_against_policies

def split_document_text(text: str) -> list[str]:
    """
    Split extracted documents into candidate clauses.

    Remove standalone page markers, join wrapped lines and page-break
    continuations, and preserve numbered clause boundaries.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove standalone page markers before splitting into paragraphs.
    text = re.sub(
        r"(?im)^[ \t]*Page[ \t]+-?\d+-?[ \t]*$",
        "",
        text,
    )

    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n+", text)
        if p.strip()
    ]

    # Join a paragraph to the next one when it appears to continue a
    # sentence, rather than starting a new numbered section or heading.
    joined: list[str] = []
    for paragraph in paragraphs:
        if not joined:
            joined.append(paragraph)
            continue

        previous = joined[-1]

        starts_new_section = bool(
            re.match(r"^\d+(?:\.\d+)+\s+", paragraph)
            or re.match(r"^\d+\.\s+", paragraph)
        )

        # Page-break continuations often start lowercase, or with
        # words such as "prior written notice".
        looks_like_continuation = bool(
            re.match(r"^[a-z]", paragraph)
            or re.match(
                r"^(prior|upon|within|after|before|and|or|to|of|by|"
                r"which|that|such|any|the other)\b",
                paragraph,
                re.IGNORECASE,
            )
        )

        previous_ends_sentence = bool(
            re.search(r'[.!?]["\')\]]?\s*$', previous)
        )

        if not starts_new_section and (
            looks_like_continuation or not previous_ends_sentence
        ):
            joined[-1] = previous + " " + paragraph
        else:
            joined.append(paragraph)

    units: list[str] = []

    for paragraph in joined:
        # Split multiple numbered clauses embedded in one paragraph.
        numbered = re.split(
            r"(?<!\w)(?=\d+(?:\.\d+)+\s+)",
            paragraph,
        )

        for part in numbered:
            part = part.strip()
            if not part:
                continue

            # Preserve numbered clauses as complete units.
            if re.match(r"^\d+(?:\.\d+)+\s+", part):
                units.append(part)
                continue

            # Discard isolated alphabetic outline markers.
            if re.fullmatch(r"[A-Za-z]\.", part):
                continue

            sentences = re.split(
                r"(?<!\d\.)(?<=[.!?])\s+(?=[A-Z0-9\"'])",
                part,
            )

            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and not re.fullmatch(r"[A-Za-z]\.", sentence):
                    units.append(sentence)

    return list(dict.fromkeys(units))


def extract_policy_requirements(text: str) -> list[str]:
    """
    Extract substantive numbered requirements or clauses from an uploaded policy.

    1. Checks if the document contains standard numbered lines such as 2.1, 2.2, etc.
    2. Checks if the document contains bulleted list items (- / * / •).
    3. If neither, uses split_document_text to group sections with their body text.
    4. Filters out pure headers/titles without substantive content.
    """
    cleaned_lines = [l.strip() for l in text.replace("\r\n", "\n").replace("\r", "\n").splitlines() if l.strip()]

    # 1. Standard numbered clauses (e.g. 2.1 ...)
    numbered_lines = []
    for line in cleaned_lines:
        match = re.match(r"^(\d+\.\d+)\s+(.+)$", line)
        if match:
            numbered_lines.append(f"{match.group(1)} {match.group(2).strip()}")
    if numbered_lines:
        return numbered_lines

    # 2. Bulleted items (- / * / •)
    bullet_items = [line for line in cleaned_lines if re.match(r"^[-*•]\s+", line) and len(line) > 15]
    if len(bullet_items) >= 2:
        return bullet_items

    # 3. Document clause segmentation (handles sections + body text)
    candidates = split_document_text(text)
    requirements = []
    for candidate in candidates:
        cleaned = candidate.strip()
        if len(cleaned) < 15:
            continue
        # Skip pure short headings (e.g. "1. PURPOSE", "SECTION 2")
        if re.fullmatch(r"^\d+[\.\)]\s+[A-Za-z\s]+$", cleaned) and len(cleaned.split()) <= 4:
            continue
        requirements.append(cleaned)

    return requirements or candidates


def evaluate_manual_review_needed(clause: str, label: str) -> tuple[bool, Optional[str]]:
    """
    Check if an UNCERTAIN or NO_MATCH_FOUND clause contains operative obligations
    or numeric figures that warrant manual human legal review.
    """
    if label not in ("UNCERTAIN", "NO_MATCH_FOUND"):
        return False, None

    lower = clause.lower()

    modals = []
    for m, desc in [
        (r"\bshall\b", "shall"),
        (r"\bmust\b", "must"),
        (r"\bmay\b", "may"),
        (r"\bwill\b", "will"),
        (r"\bagrees?\s+to\b", "agrees to"),
        (r"\brequired\b", "required"),
        (r"\bcovenants?\b", "covenants"),
    ]:
        if re.search(m, lower):
            modals.append(desc)

    has_numbers = bool(
        re.search(r"\b\d+(?:\.\d+)?\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty|forty|fifty|sixty|ninety)\b", lower)
        and re.search(r"\b(?:days?|months?|years?|weeks?|hours?|percent|%|inr|usd|lakh|crore|fees?)\b", lower)
    )

    if modals and has_numbers:
        return True, f"Contains operative legal term ('{modals[0]}') and quantitative metrics with no confirmed policy rule."
    elif modals:
        return True, f"Contains operative legal duty ('{modals[0]}') with no confirmed policy rule."
    elif has_numbers:
        return True, "Contains unverified numeric metrics or duration."
    return False, None


def compare_uploaded_documents(
    contract_path: str,
    policy_paths: list[str],
    backend: str = "sentence-transformers",
    similarity_threshold: float = 0.10,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Extract and compare one contract with one or more uploaded policy files.

    Returns a report dictionary; it does not modify the uploaded files.
    """
    if not policy_paths:
        raise ValueError("Upload at least one company policy document.")

    contract_file = Path(contract_path)
    if not contract_file.is_file():
        raise FileNotFoundError(f"Contract not found: {contract_path}")

    for policy_path in policy_paths:
        if not Path(policy_path).is_file():
            raise FileNotFoundError(f"Policy not found: {policy_path}")

    contract_text = ingest_document(str(contract_file))
    contract_clauses = split_document_text(contract_text)

    policy_requirements: list[str] = []
    policy_sources: list[str] = []

    for policy_path in policy_paths:
        policy_text = ingest_document(policy_path)
        requirements = extract_policy_requirements(policy_text)

        policy_requirements.extend(requirements)
        policy_sources.extend([Path(policy_path).name] * len(requirements))

    if not contract_clauses:
        raise ValueError("No candidate clauses were extracted from the contract.")

    if not policy_requirements:
        raise ValueError("No candidate requirements were extracted from the policies.")

    # Reuse the project's existing semantic matcher and conflict rules.
    matcher = PolicyMatcher(
        backend=backend,
        similarity_threshold=similarity_threshold,
    )

    findings = []

    for clause_number, clause in enumerate(contract_clauses, start=1):
        matches = check_clause_against_policies(
            contract_text=clause,
            policy_texts=policy_requirements,
            matcher=matcher,
            top_k=top_k,
        )

        if not matches:
            needs_review, review_note = evaluate_manual_review_needed(clause, "NO_MATCH_FOUND")
            findings.append({
                "clause_number": clause_number,
                "contract_clause": clause,
                "policy_source": None,
                "policy_requirement": None,
                "similarity_score": None,
                "label": "NO_MATCH_FOUND",
                "severity": "NONE",
                "reason": (
                    "No policy requirement met the semantic similarity "
                    "threshold. This does not prove compliance."
                ),
                "needs_manual_review": needs_review,
                "review_reason": review_note,
            })
            continue

        # Post-process matches to eliminate noisy UNCERTAIN clutter:
        # If any decisive match (CONFLICT, PARTIAL_CONFLICT, NO_CONFLICT) exists,
        # drop lower-ranked UNCERTAIN noise for this clause.
        decisive = [m for m in matches if m["label"] in ("CONFLICT", "PARTIAL_CONFLICT", "NO_CONFLICT")]
        selected_matches = decisive if decisive else matches[:1]

        for match in selected_matches:
            # The checker creates policy IDs in the same order as the
            # supplied policy_requirements list.
            policy_index = int(match["policy_line_id"].removeprefix("POLICY-").split("-")[0]) - 1
            source_name = (
                policy_sources[policy_index]
                if 0 <= policy_index < len(policy_sources)
                else None
                )

            label = match["label"]
            needs_review, review_note = evaluate_manual_review_needed(clause, label)

            findings.append({
                "clause_number": clause_number,
                "contract_clause": clause,
                "policy_source": source_name,
                "policy_requirement": match["policy_text"],
                "similarity_score": match["similarity_score"],
                "label": label,
                "severity": match["severity"],
                "reason": match["reason"],
                "rules": match.get("rules", []),
                "contract_evidence": match.get("contract_evidence", clause),
                "policy_evidence": match.get(
                    "policy_evidence", match["policy_text"]
                ),
                "needs_manual_review": needs_review,
                "review_reason": review_note,
            })

    return {
        "contract_file": contract_file.name,
        "policy_files": [Path(p).name for p in policy_paths],
        "contract_clause_count": len(contract_clauses),
        "policy_requirement_count": len(policy_requirements),
        "finding_count": len(findings),
        "findings": findings,
    }

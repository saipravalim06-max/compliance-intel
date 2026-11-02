"""Load state requirements that may be relevant to contract compliance.

This module filters existing state-policy records conservatively.
It does not claim that every returned record is an enforceable law.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional

from core.profile_eval import load_state_requirements


# These types are candidates for review, not proof of legal applicability.
_CANDIDATE_TYPES = {"OBLIGATION", "RESTRICTION", "EXEMPTION"}


def load_state_law_candidates(
    jurisdiction: str,
    path: Optional[str] = None,
) -> List[Dict]:
    """Return sourced state-policy records for review in one jurisdiction.

    Benefits, startup eligibility, and programme support are excluded.
    Records retain their original evidence and source metadata.
    """
    if not jurisdiction or not jurisdiction.strip():
        raise ValueError("jurisdiction must be provided")

    requested = jurisdiction.strip().casefold()
    rows = list(load_state_requirements(path))

    # When path is not explicitly overridden by test fixtures, also include
    # the dedicated state statutory contract regulations dataset.
    if path is None:
        extra_path = Path(__file__).resolve().parents[1] / "data" / "state_policies" / "state_contract_regulations.csv"
        if extra_path.is_file():
            with extra_path.open("r", encoding="utf-8-sig") as f:
                extra_rows = list(csv.DictReader(f))
                rows.extend(extra_rows)

    candidates = []
    for row in rows:
        row_jurisdiction = str(row.get("jurisdiction") or "").strip()
        row_type = str(row.get("requirement_type") or "").strip().upper()

        if row_jurisdiction.casefold() != requested:
            continue
        if row_type not in _CANDIDATE_TYPES:
            continue

        candidates.append(dict(row))

    return candidates

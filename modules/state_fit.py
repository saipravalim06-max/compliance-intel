"""
modules/state_fit.py — MODULE 1

Build this SECOND, only after modules/contract_checker.py works end-to-end.
Same engine, same pattern — the only thing that changes is what sits on
each side of the comparison: a CompanyProfile instead of a contract, and a
state's startup-policy corpus instead of your internal policy corpus.

Start with just 2 states (Gujarat, Karnataka). Don't add more until this
works cleanly — adding states is just adding directories, it will not
teach you anything new about the pipeline.
"""

import os
from core.company_profile import CompanyProfile
from core.engine import (
    ingest_document,
    segment_policy_text,
    embed_segments,
    match_segments,
    Segment,
)


def profile_to_segment(profile: CompanyProfile) -> Segment:
    """Wraps the company profile's matching text as a single Segment so it
    can flow through the same embed/match machinery as everything else."""
    return Segment(
        source_doc_id=profile.company_name,
        segment_id=f"{profile.company_name}-profile",
        original_text=profile.to_matching_text(),
        original_language="en",
    )


def score_state_fit(profile: CompanyProfile, state_policy_dir: str) -> dict:
    """
    Returns a dict: {
        "state": <dir name>,
        "matches": [MatchResult, ...],
        "conflict_count": int,
        "high_severity_count": int,
    }
    Call this once per state, then rank states by whatever combination of
    conflict_count / high_severity_count / (later) incentive-match score
    you decide on.
    """
    profile_segment = embed_segments([profile_to_segment(profile)])

    policy_segments = []
    for fname in os.listdir(state_policy_dir):
        if not fname.endswith(".txt"):
            continue
        text = ingest_document(os.path.join(state_policy_dir, fname))
        policy_segments.extend(segment_policy_text(doc_id=fname, text=text))
    policy_segments = embed_segments(policy_segments)

    matches = match_segments(profile_segment, policy_segments)

    return {
        "state": os.path.basename(state_policy_dir.rstrip("/")),
        "matches": matches,
        "conflict_count": sum(1 for m in matches if m.numeric_conflict),
        "high_severity_count": sum(1 for m in matches if m.severity == "high"),
    }


def rank_states(profile: CompanyProfile, states_root_dir: str) -> list:
    """
    states_root_dir should contain one subdirectory per state, e.g.:
        data/state_policies/gujarat/
        data/state_policies/karnataka/
    each holding that state's policy text files (same .txt format as the
    internal policy corpus, for now).
    """
    results = []
    for state_dir in sorted(os.listdir(states_root_dir)):
        full_path = os.path.join(states_root_dir, state_dir)
        if os.path.isdir(full_path):
            results.append(score_state_fit(profile, full_path))

    # Lower conflict/severity = better fit. Replace with your real scoring
    # formula once you add the positive incentive-matching side (see
    # overview notes: State Fit Score = incentive alignment - friction).
    results.sort(key=lambda r: (r["high_severity_count"], r["conflict_count"]))
    return results


if __name__ == "__main__":
    print(
        "Fill in core/engine.py's TODOs and add state policy .txt files "
        "under data/state_policies/<state>/ before running this."
    )

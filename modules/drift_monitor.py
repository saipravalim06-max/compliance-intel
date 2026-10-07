"""
modules/drift_monitor.py — MODULE 3 (build LAST)

Don't start this until Module 1 and Module 2 both work. This needs a
"before" and "after" version of a regulation to compare against an existing
contract/policy — early on, simulate this with synthetic before/after
regulation pairs (write two versions of a POL-style file by hand) since
real amendment history is sparse and hard to source for a working demo.

The core question this module answers: "A regulation we previously matched
against has changed — does our existing contract/policy still comply?"
Same engine again: segment the OLD regulation text, segment the NEW
regulation text, segment the existing contract/policy clause that was
originally matched to the OLD version, and re-run match_segments() against
the NEW version to see if the match/conflict verdict changed.
"""

from core.engine import segment_policy_text, embed_segments, match_segments


def check_drift(existing_clause_segment, old_regulation_text: str, new_regulation_text: str):
    """
    Returns whether a previously-compliant clause has drifted out of
    compliance because the regulation it was checked against has changed.

    TODO once Modules 1 & 2 are solid:
    1. Segment old_regulation_text and new_regulation_text.
    2. Re-run match_segments() for existing_clause_segment against each.
    3. Compare the two MatchResult sets — if the NEW version produces a
       conflict that the OLD version didn't, that's drift. Flag it.
    """
    raise NotImplementedError(
        "Build this after modules/contract_checker.py and "
        "modules/state_fit.py are both working end-to-end."
    )

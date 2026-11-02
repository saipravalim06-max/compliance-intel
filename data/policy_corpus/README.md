# Canonical Company Policy Corpus (synthetic)

21 synthetic internal policies. **This is the one corpus** — `policy_index.csv`
is the only index; every `policy_id` is unique and maps to exactly one file.

Synthetic by design (real internal policies are confidential). Disclose this in
the report: *"Policies were constructed for this project, modelled on common
corporate standards."*

## Format rule (important)
Each policy has numbered requirement lines (`2.1 ...`) with **explicit numeric
thresholds** (days, %, amounts). Conflict detection compares these numbers to
contract clauses, so vague wording ("reasonable", "appropriate") is avoided on
purpose. New policies must follow the same format.

## CUAD coverage (`cuad_coverage` column)
CUAD has 41 clause categories. It has **no** categories for confidentiality,
indemnification, data privacy, data retention, information security,
environmental, third-party data sharing, force majeure or vendor management.
Policies marked `none` have no real CUAD clauses to draw on — evaluate them with
synthetic clauses (see tests/ and docs/DECISIONS.md).

## Relationship labels (Module 2)
CONFLICT, NO_CONFLICT, PARTIAL_CONFLICT, UNCERTAIN

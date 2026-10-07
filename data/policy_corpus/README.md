# Synthetic Company Policy Corpus

This corpus contains 17 synthetic internal company policies created for the NLP project.

Purpose:
- Provide a company-policy side for contract-vs-policy compliance analysis.
- Support semantic matching, obligation extraction, conflict detection, and evaluation.
- Serve as a prototype dataset; these are not real legal/company policies.

The policy_index.csv file maps each policy ID to its name, domain, and text file.

Initial workflow:
CUAD contract clause -> relevant company policy -> relationship label -> explanation.

Suggested relationship labels:
- CONFLICT
- NO_CONFLICT
- PARTIAL_CONFLICT
- UNCERTAIN

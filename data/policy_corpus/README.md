# Synthetic Company Policy Corpus

This is a synthetic corpus of 17 internal company policy documents, built to stand in
for a real organization's policy library. Since real internal company policies are
confidential and not publicly available, this corpus was constructed for use in an
academic NLP project (contract clause vs. policy semantic conflict detection).

## Why synthetic data is appropriate here

Real internal company policies are not published anywhere — using synthetic policies
is the standard, accepted approach for this kind of coursework, as long as it's
disclosed transparently in your report. State clearly in your methodology section:
*"Company policy documents were synthetically constructed for this project, modeled
on common real-world corporate policy standards, since real internal policies are
confidential and unavailable for academic use."*

## Design principle

Each policy contains explicit, **quantifiable requirements** (specific day counts,
percentages, dollar amounts, durations) rather than vague language. This is
intentional: your semantic conflict detector needs concrete numeric anchors to
compare against contract clause language — e.g., a contract clause saying "7 days
notice" can be meaningfully compared against a policy requiring "30 days notice"
to produce a clear, explainable conflict.

## Files

| File | Category | Maps to CUAD label(s) |
|---|---|---|
| POL-01_vendor_management.txt | Vendor mgmt / termination | Termination for Convenience |
| POL-02_data_privacy_protection.txt | Data privacy | (no direct CUAD label — cross-reference with GDPR/DPDP text) |
| POL-03_payment_terms.txt | Payment | Payment terms / price restriction |
| POL-04_confidentiality_nda.txt | Confidentiality | Confidentiality clauses |
| POL-05_termination_notice.txt | Termination | Termination for Convenience / Notice Period |
| POL-06_limitation_of_liability.txt | Liability | Cap on Liability |
| POL-07_indemnification.txt | Indemnification | Third Party Beneficiary / IP Indemnification |
| POL-08_ip_assignment.txt | IP | IP Ownership Assignment |
| POL-09_noncompete_nonsolicit.txt | Non-compete | Non-Compete / Non-Solicit |
| POL-10_insurance_requirements.txt | Insurance | Insurance |
| POL-11_audit_rights.txt | Audit | Audit Rights |
| POL-12_dispute_resolution_governing_law.txt | Dispute resolution | Governing Law |
| POL-13_force_majeure.txt | Force majeure | (no direct CUAD label — general clause) |
| POL-14_autorenewal.txt | Renewal | Renewal Term |
| POL-15_assignment_change_of_control.txt | Assignment | Anti-Assignment / Change of Control |
| POL-16_exclusivity_mfn.txt | Exclusivity | Exclusivity / Most Favored Nation |
| POL-17_warranty.txt | Warranty | Warranty Duration |

`policy_index.csv` gives you a machine-readable index with each policy's key
quantifiable requirements pre-extracted, so you don't have to re-parse the full
text just to get the headline numbers.

## Using this with CUAD

1. Load CUAD contract clauses (see `theatticusproject/cuad-qa` on Hugging Face).
2. Load this policy corpus with `load_policies.py`.
3. Embed both sides with a sentence-transformer model (e.g., `all-MiniLM-L6-v2`
   for a fast baseline, or a larger legal-domain model if you want stronger
   results).
4. For each contract clause, retrieve the top-k most similar policy requirement
   lines (use `get_requirement_sections()` in `load_policies.py` to split
   policies into individual numbered requirement lines — this gives you
   finer-grained matches than comparing against a whole policy document).
5. Where similarity is high AND the extracted numeric values differ (e.g.,
   clause says "7 days," policy requires "30 days"), flag as a conflict.
   This numeric-comparison step is what makes your conflict detection
   explainable rather than just a similarity score.

## Extending the corpus

If you want more coverage or a larger corpus for training/evaluation splits,
follow the same format (numbered policy ID, title, category, purpose,
numbered requirements with explicit numeric standards, applicability) and
add new files + a corresponding row in `policy_index.csv`.

# Module 1 report — state requirements vs company profile

## Part 1 — agreement with Sreeja's hand labels (AgriVision AI)

Rules were written from the policy wording, not from these labels. Differences are review items.

Overall: **77/86 = 89.5%** requirements get the same verdict.

- Tamil Nadu: 38/40
- Karnataka: 39/46

### Confusion (rows = hand label, columns = engine)

| hand \ engine | PASS | APPLIES | POTENTIAL | UNKNOWN | NOT_APPLICABLE | INFO | FAIL |
|---|---|---|---|---|---|---|---|
| PASS | 25 | 3 | 1 | 0 | 0 | 0 | 0 |
| APPLIES | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| POTENTIAL | 0 | 0 | 9 | 2 | 0 | 0 | 0 |
| UNKNOWN | 0 | 0 | 0 | 22 | 0 | 0 | 1 |
| NOT_APPLICABLE | 0 | 0 | 0 | 1 | 14 | 1 | 0 |
| INFO | 0 | 0 | 0 | 0 | 0 | 3 | 0 |

### Disagreements (9)

| requirement | hand label | engine | hand reasoning | engine reasoning |
|---|---|---|---|---|
| TN-FUND-001 | PASS | POTENTIAL | Company matches two listed enhanced-support categories: Women-led and Rural Impact. | Eligible so far, but more evidence is needed: early-stage / proof-of-concept stage — not stated in the profile. |
| TN-SCST-002 | NOT_APPLICABLE | INFO | This is a programme target, not a benefit applicable to this company. | Programme target (200 supported startups), not a benefit to a single company. |
| KA-FUND-002 | PASS | APPLIES | AI is explicitly a deep-tech area; SDG/rural impact stated | 10% of the Idea2PoC fund is earmarked for these areas. |
| KA-WOM-002 | PASS | APPLIES | Women-led profile; allocation is policy-level | 25% of the venture-capital fund is earmarked for women startups. |
| KA-WOM-004 | PASS | APPLIES | Women-led profile | 20% of seats at supported incubators are reserved for women startups. |
| KA-CIRC-001 | POTENTIAL | UNKNOWN | Rural/AI profile may align, but circular economy status is not established | Cannot conclude: works on circular economy — not stated in the profile. |
| KA-CIRC-002 | POTENTIAL | UNKNOWN | Circular economy innovation status not established | Cannot conclude: works on circular economy — not stated in the profile. |
| KA-SAND-001 | NOT_APPLICABLE | UNKNOWN | Company is not a sandbox operator | Cannot conclude: is a regulatory-sandbox operator — not stated in the profile. |
| KA-SGST-002 | UNKNOWN | FAIL | Turnover passes INR 1 crore cap, but other conditions unknown | Condition not satisfied: annual turnover ≤ ₹1 crore (SGST reimbursement cap) (company: 40,000,000) → not met. |

## Part 2 — per-state summary for each demo profile

Evaluated as if the company registers and incorporates in each state (registration is a step to take, not a reason a state is unsuitable). Mirror rows are excluded. `needs info` = a fact the rules depend on is missing; it is never counted against a state. There is deliberately no single score.

| profile | state | intrinsic eligibility failures | steps to take | confirmed (PASS) | policy-level (APPLIES) | POTENTIAL | needs info | N/A | FAIL |
|---|---|---|---|---|---|---|---|---|---|
| AgriVision AI Pvt Ltd | Tamil Nadu | none | none | 14 | 4 | 7 | 4 | 10 | 0 |
| AgriVision AI Pvt Ltd | Karnataka | none | none | 11 | 3 | 4 | 22 | 4 | 1 |
| Nirmaan Rural Foods LLP | Tamil Nadu | none | TN-ELIG-007 | 22 | 4 | 4 | 3 | 6 | 0 |
| Nirmaan Rural Foods LLP | Karnataka | none | KA-ELIG-001, KA-ELIG-002 | 16 | 3 | 3 | 15 | 8 | 0 |
| SteelForge Components Ltd | Tamil Nadu | TN-ELIG-001, TN-ELIG-002, TN-ELIG-003, TN-ELIG-005 | TN-ELIG-007 | 2 | 0 | 0 | 1 | 32 | 4 |
| SteelForge Components Ltd | Karnataka | KA-ELIG-002, KA-ELIG-003, KA-ELIG-004, KA-ELIG-005 | KA-ELIG-001 | 2 | 0 | 0 | 0 | 39 | 4 |

## Part 3 — facts that would settle the most open requirements

Each fact below is missing from the profile and would resolve the listed number of UNKNOWN / POTENTIAL requirements. This is the questionnaire to give the company.

**AgriVision AI Pvt Ltd**

- Tamil Nadu: `startup_recognition_age_years` (2), `has_scalable_model` (1), `is_early_stage` (1), `is_growth_stage` (1), `incubated_in_govt_supported_incubator` (1), `patent_stage` (1), `has_trademark` (1), `is_msme` (1)
- Karnataka: `located_beyond_bengaluru_urban` (4), `hires_interns_from_beyond_bengaluru` (3), `has_circular_economy_focus` (2), `incubated_in_govt_supported_incubator` (2), `intl_marketing_spend_inr` (2), `patent_stage` (2), `is_early_stage` (1), `state.elevate_programme_recognised` (1)

**Nirmaan Rural Foods LLP**

- Tamil Nadu: `startup_recognition_age_years` (2), `is_growth_stage` (1), `has_trademark` (1), `is_msme` (1)
- Karnataka: `hires_interns_from_beyond_bengaluru` (3), `has_circular_economy_focus` (2), `intl_marketing_spend_inr` (2), `state.elevate_programme_recognised` (1), `is_growth_stage` (1), `is_obc_or_minority_led` (1), `intern_duration_months` (1), `has_availed_rural_internship_subsidy` (1)

**SteelForge Components Ltd**

- Tamil Nadu: `has_scalable_model` (1)
- Karnataka: nothing missing


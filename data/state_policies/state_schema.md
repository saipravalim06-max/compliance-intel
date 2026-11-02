# State Fit Regulatory Dataset Schema

Tamil Nadu and Karnataka use the same 21-column regulatory schema so the shared NLP engine can map both datasets to one common Requirement model.

| Column | Description |
|---|---|
| `state` | State to which the requirement belongs. |
| `requirement_id` | Stable unique identifier for the requirement, such as `TN-ELIG-001` or `KA-ELIG-001`. |
| `policy_name` | Full name of the policy document containing the requirement. |
| `domain` | Policy area such as Eligibility, Funding, IP, Procurement, Inclusion, or Facilitation. |
| `requirement_name` | Short name describing the specific rule, benefit, restriction, or provision. |
| `actor` | Entity to which the provision applies, such as Startup, Government, or Startup Cell. |
| `action` | What the actor must do, receives, is eligible for, or is otherwise subject to. |
| `condition` | Circumstance or attribute that determines when the provision applies. |
| `operator` | Explicit comparison/logical operator, such as `<=`, `IN`, `REQUIRED`, or `NOT_ALLOWED`. |
| `threshold` | Numeric, categorical, or other limit/value used by the provision. Blank when none is supported. |
| `unit` | Unit associated with a threshold, such as `INR`, `years`, `employees`, or `%`. |
| `deadline` | Explicit deadline or claim/application time limit when stated by the source. |
| `benefit` | Funding, reimbursement, concession, support, exemption, or other positive outcome. |
| `requirement_type` | Classification such as Eligibility, Benefit, Obligation, Exemption, Restriction, Support, Recognition, or Policy Metadata. |
| `eligibility_logic` | Explicit relationship between conditions, such as `AND` or `OR`. |
| `evidence_text` | Exact source wording supporting the structured requirement. |
| `page_number` | Page number in the source policy PDF where the evidence appears. |
| `source_url` | Official source URL for the policy document or official policy page. |
| `effective_from` | Concrete policy start/effective date only when explicitly supported by the source; otherwise blank. |
| `effective_to` | Concrete policy end/expiry date only when explicitly supported by the source; otherwise blank. |
| `notes` | Additional source-grounded context that does not fit the standardized fields. |

## Evaluation labels

Both State Evaluation sheets use only:

`APPLIES`, `PASS`, `FAIL`, `NOT_APPLICABLE`, `POTENTIAL`, `UNKNOWN`, `INFO`.

- `APPLIES` — the provision is applicable, without claiming every condition has passed.
- `PASS` — the provision applies and the company profile satisfies the supported condition.
- `FAIL` — the provision applies and the company profile does not satisfy the supported condition.
- `NOT_APPLICABLE` — the provision does not apply to the company/profile.
- `POTENTIAL` — the provision may apply, but additional conditions or evidence are needed.
- `UNKNOWN` — the available profile/source information is insufficient to determine the result.
- `INFO` — informational content that is not a company pass/fail test.

## Evidence and missing values

Do not invent missing values. Preserve `evidence_text`, `page_number`, `source_url`, and any explicitly supported effective dates. If the source does not support a field, leave it blank/NULL.

The state datasets are regulatory inputs only. They do not calculate a universal "best state" score.

# Module 1 — State Fit (state requirements vs company profile)

```
profile (data/profiles/*.json)  ─┐
state requirements (CSV, 93)     ├─► core/profile_eval.py ─► verdict per requirement + evidence + page + missing facts
rules (profile_rules.json, 93)  ─┘            └─► modules/state_fit.py ─► per-state summary (no single score)
```
Rules are authored in `scripts/build_profile_rules.py` (edit that, then run it). Run:

    python scripts/evaluate_profile.py --report results/profile_eval_report.md
    python -m modules.state_fit data/profiles/nirmaan_rural_foods.json
    python tests/test_profile_eval.py

## Verdict logic (core/profile_eval.py) — the rule that matters: a missing fact never becomes FAIL
info → INFO · a gate is False → NOT_APPLICABLE · a check is False → FAIL · a gate/check fact is missing → UNKNOWN ·
a "need" is False → NOT_APPLICABLE · a "need" is missing → POTENTIAL · discretionary award → POTENTIAL ·
policy-level allocation → APPLIES · otherwise PASS.

## "Where should we START" vs "are we already there"
Registering with the state startup agency and incorporating there are **steps to take**, not reasons a state is
unsuitable. `evaluate_for_state(..., if_registered=True)` (default) evaluates the company as if it had taken them and
lists them under `actions_required`. Intrinsic failures (age, turnover, legal form, innovation) are separate.
There is deliberately **no single best-state score**: failures, confirmed benefits, potential benefits and missing
information are different things (Sreeja's schema also says the datasets must not compute one).

## Measured: agreement with Sreeja's hand labels (AgriVision) — 77/86 = 89.5%
Rules were written from the policy wording, not from her labels. The 9 differences are review items:

| requirement | hand | engine | what it is | suggested resolution |
|---|---|---|---|---|
| KA-SGST-002 | UNKNOWN | FAIL | **label error**: reason says turnover "passes the INR 1 crore cap", but AgriVision's turnover is INR 4 crore | change the label to FAIL |
| TN-FUND-001 | PASS | POTENTIAL | policy requires "early-stage"; the profile never states stage | add `is_early_stage` to the profile, or accept POTENTIAL |
| KA-SAND-001 | NOT_APPLICABLE | UNKNOWN | label assumed "not a sandbox operator", never stated | add `is_sandbox_operator: false` to AgriVision, or accept UNKNOWN |
| KA-FUND-002, KA-WOM-002, KA-WOM-004 | PASS | APPLIES | allocations / earmarks / reservations are APPLIES in Tamil Nadu but PASS in Karnataka | pick one convention for both states (engine uses APPLIES) |
| TN-SCST-002 | NOT_APPLICABLE | INFO | programme target is N/A in TN but INFO in KA (KA-RURAL-001) | pick one convention (engine uses INFO) |
| KA-CIRC-001, KA-CIRC-002 | POTENTIAL | UNKNOWN | a missing eligibility fact is UNKNOWN for "Beyond Bengaluru" but POTENTIAL for "circular economy" | pick one convention (engine: missing eligibility fact = UNKNOWN; POTENTIAL = eligible so far, more evidence or an award decision needed) |

## Open data items
**Page-reference correction:** The canonical dataset now preserves the source workbook's page range for `KA-MKT-002` as `18-19`. The earlier missing-page data-gap note is resolved. This confirms consistency with the workbook reference; it does not independently establish the legal status or current applicability of the underlying requirement.
- 3 Tamil Nadu and 4 Karnataka requirements (TANSCALE rows, KA-ELIG-007/008 mirrors, KA-FUND-006, KA-SOC-002) have no hand label; the engine evaluates them.
- Regulatory friction (labour, approvals) is thin: 6 of 93 requirements. Module 1 currently measures **incentive and eligibility fit**.

## Limits — be honest about these in the report
- Rules were authored by one person (me, from the policy text) and checked against labels written by another; only AgriVision has gold labels. SteelForge and Nirmaan outputs are plausible but unlabelled.
- The three profiles are fictional.
- Rules encode **one reading** of the policy text. A real product needs the rule table reviewed by someone who knows the policies.
- The evaluator reads structured facts; it does not read the policy PDFs. Adding a state means writing its requirement rows and rules.

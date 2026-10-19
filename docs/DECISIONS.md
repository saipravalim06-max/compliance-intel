# Foundation decisions (Step 1)

Four decisions that every module, dataset and test now depends on. Change one
only by changing it here, in the code, and in `tests/test_foundation.py` together.

## D1. One policy corpus — `data/policy_corpus/` (21 policies)
- `policy_index.csv` is the only index. `policy_id` is unique and maps to one file.
- **Format rule:** numbered requirement lines (`2.1 ...`) with explicit numeric
  thresholds. Reason: conflict detection compares numbers (7 days vs 30 days).
  Vague policies ("reasonable", "appropriate") cannot be labelled objectively.
- Teammate's earlier vague 1–3 sentence versions were **replaced, not merged**.
  Her topics that were missing from the original set (information security, data
  retention, environmental, third-party sharing) were kept and rewritten with
  thresholds as POL-18, 19, 20, 21.
- Old-ID → canonical-ID table: `data/processed/policy_id_translation.csv`
  (any labels written against the old numbering must be translated with it).
- `cuad_coverage` column: CUAD has **no** categories for confidentiality,
  indemnification, data privacy/retention, info security, environmental,
  third-party sharing, force majeure or vendor management. Those 9 policies need
  **synthetic** test clauses; do not expect real CUAD clauses for them.

## D2. One requirement schema — `core/schemas.py`
- `Requirement` is a backward-compatible superset: the engine's original fields
  plus the state-dataset fields (operator, threshold_value, unit, bound, benefit,
  eligibility_logic, page_number, source_url, effective_from/to, ...).
- `Requirement.from_state_row()` converts a workbook row. All 93 rows convert.
- Numbers are numeric: `threshold_value` + `unit`. **INR is always absolute rupees**
  (₹50 crore = 500,000,000). `bound` = UPPER/LOWER from wording ("up to", "at least").
- Vocabulary lives in `core/taxonomy.py` (Operator, Unit, RequirementType,
  StateDomain). Raw teammate values are mapped by the crosswalk dicts; a test
  fails if a new raw value appears that is not mapped.
- Two label sets, deliberately separate:
  - Module 2 (contract vs policy): CONFLICT, NO_CONFLICT, PARTIAL_CONFLICT, UNCERTAIN
  - Module 1 (state rule vs profile): APPLIES, PASS, FAIL, NOT_APPLICABLE, POTENTIAL, UNKNOWN, INFO

## D3. One company profile — `core/company_profile.py`, `data/profiles/*.json`
- Union of the facts in both state profile sheets, so both states are evaluated
  against the **same** facts.
- Facts are tri-state: True / False / **None = UNKNOWN**. Unknown must give an
  UNKNOWN verdict, never FAIL. A state whose rules ask for more facts will show
  more UNKNOWN — report "needs more information" separately; do not penalise it.
- Three demo profiles (all fictional, flagged `is_demo_profile`):
  AgriVision (near-ideal fit), SteelForge (fails age/turnover caps),
  Nirmaan (inclusion rules; fails employee thresholds). Without the last two
  there would be no FAIL cases to test.
- State-specific facts (recognised by the state startup agency, incorporated in
  the state) live in `state_context`, because they depend on which state is asked.

## D4. Contract ↔ policy bridge — `data/processed/cuad_policy_mapping.csv`
- CUAD spells categories in title case ("Cap On Liability", "Ip Ownership
  Assignment"). The first mapping used other spellings and silently returned zero
  clauses for 8 categories. The script now matches case-insensitively and
  **fails loudly** on a mapped category that does not exist in CUAD.
- Each mapping has a `mapping_strength` (strong / moderate / weak). The
  evaluation sample uses `strong` only by default.

## D5. Engine behaviour (Step 2) — see `docs/ENGINE.md`
- `UNCERTAIN` is a first-class answer. The engine never guesses across different units, periods or quantity kinds.
- Two policy lines were reworded because their direction was ambiguous: POL-11#2.1 (audit notice is now a ceiling the
  counterparty may require) and POL-14#2.1 (non-renewal notice may not be required earlier than 60 days).
- Authorization means consent from the **counterparty**. Approvals by the company's own functions (General Counsel,
  Finance, Director) are internal governance and are ignored by the authorization rule.
- `core/schemas.py` gained `quantity_kind`, `per`, `applies_to`, `quantities` (all optional).

## Known open items (not decided here)
- Mirror rows in the Karnataka data (e.g. KA-ELIG-003 "turnover <= 100 crore" and
  KA-ELIG-008 "turnover > 100 crore" come from one sentence). Do not count both.
- Regulatory *friction* is thin: only 6 of 93 state requirements are in
  REGULATORY_COMPLIANCE. Labour and approvals documents are still needed.
- `effective_from/to` is blank for all 93 rows (Karnataka's policy period 2022–2027
  is stated in the workbook's Policy Metadata sheet and can be filled in).
- `core/engine.py` still contains old stubs and its own `MatchResult` dataclass
  that duplicate `core/matching.py` / `core/schemas.py`. Clean up in Step 2.

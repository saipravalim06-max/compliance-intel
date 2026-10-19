# Engine (Step 2): what it does, what it does not

Pipeline: `extract_requirement` → (policy line retrieval) → `detect_conflict` → label + evidence.

```
clause ──► core/extraction.py ──► Requirement {modality, action, authorization, quantities[kind,unit,bound]}
policy line ─► (same extractor) ─┘
                       core/conflict.py ──► CONFLICT | PARTIAL_CONFLICT | NO_CONFLICT | UNCERTAIN  + exact reason
retrieval (embeddings) only picks WHICH policy lines to compare; it never decides a conflict.
```

## Rules in `core/conflict.py`
| rule | fires when |
|---|---|
| NUMERIC | same *kind* of quantity (notice period, liability cap, ...), compared in the direction the policy sets (floor or ceiling) after unit conversion |
| AUTH | contract allows an act without consent where policy requires consent |
| AUTH_STRICTER | contract requires consent where the policy does not → PARTIAL_CONFLICT, low severity |
| MODALITY | policy prohibits an act (same action AND object) that the contract permits |
| scope | policy line applies only to e.g. "vendors classified as critical" → PARTIAL_CONFLICT |

UNCERTAIN is returned, not a guess, when: no comparable number on both sides; different units (months-of-fees vs fixed
amount); different rate periods (per month vs per annum); business-vs-calendar days that are too close to call.

## Design choices worth defending in the report
- Similarity ≠ conflict. Embeddings choose candidates; structured fields decide.
- A number is only compared with a number of the same *kind* (cure period ≠ notice period; term length ≠ notice period).
- Direction comes from the wording ("at least", "within", "not exceed") with per-kind defaults.
- Policy lines were reworded where direction was ambiguous (POL-11#2.1, POL-14#2.1).

## Measured so far (see `results/eval_report.md`, `python scripts/evaluate.py`)
| set | result | how far to trust it |
|---|---|---|
| 81 synthetic gold cases | 81/81 | **regression suite only** — authored together with the rules |
| 64 real CUAD pairs (pool) | 52 UNCERTAIN, 12 decided | the real limitation: **coverage is ~19%** on mixed categories |
| 4,908 real strong-mapped clauses | a number is found in 25% | most categories are textual, not numeric |
| author's read of 30 real predictions | ~16–17/18 conflicts and 11/12 no-conflicts looked right | one reader, small sample — NOT ground truth |
| retrieval, offline hashing baseline | gold line in top-5 for 66.7% | sentence-transformer retrieval not yet measured (no model download in the build sandbox) |

## Known limits
- Textual categories (governing law, IP ownership, MFN, liability carve-outs) have no rule yet → UNCERTAIN.
- Clauses with several figures are compared figure by figure; who the notice is *from* is not modelled.
- "Termination for convenience" clauses that mention renewals can be mis-kinded as renewal notice.
- Sentence-transformer retrieval and the translation layer are untested in the build environment.

## Next
1. Human-label `data/processed/evaluation_sample_predicted.csv` (suggestions are pre-filled; `label` stays blank).
2. Rules for the textual categories (governing-law match, consent/carve-out checks) or an NLI/LLM comparator, evaluated against the rule baseline.
3. Run `python scripts/evaluate.py --retrieval sentence-transformers` locally and record the number.
4. Translation layer (IndicTrans2 / NLLB) with the Hindi/Tamil round trip.

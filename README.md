# Compliance Intelligence Platform

One shared engine (ingest → translate → segment → extract → embed → match →
conflict → explain) behind three modules:

| Module | Compares | Status |
|---|---|---|
| 2. Contract checker | contract clause ⟷ company policy | engine in progress |
| 1. State fit | company profile ⟷ state startup policy | data ready (TN, KA) |
| 3. Drift monitor | contract/policy ⟷ changed regulation | not started |

## Foundation (agreed — see `docs/DECISIONS.md`)
- `data/policy_corpus/` — 21 synthetic policies, numeric thresholds, one index
- `core/schemas.py` + `core/taxonomy.py` — one `Requirement`, one vocabulary
- `core/company_profile.py` + `data/profiles/` — one tri-state profile (None = UNKNOWN)
- `data/processed/` — CUAD ⟷ policy mapping, candidates, labelling pool
- `data/state_policies/` — Tamil Nadu + Karnataka workbooks and canonical CSV

## Run the checks
```
pip install -r requirements.txt
python tests/test_foundation.py
```

## Step 2 — engine (done; see `docs/ENGINE.md`)
Extractor fixes, numeric/authorization conflict rules, cached batch embeddings, evaluation script
(`python scripts/evaluate.py`), 81 gold cases, suggested labels for the 64 real CUAD pairs.

## Module 1 — state fit (done; see `docs/MODULE1.md`)
`python scripts/evaluate_profile.py` · `python -m modules.state_fit data/profiles/nirmaan_rural_foods.json` ·
93 rules, 89.5% agreement with the hand labels, disagreements listed for review.

## Next
1. Human-label `data/processed/evaluation_sample_predicted.csv`
2. Rules / comparator for the textual categories (coverage on real clauses is ~19%)
3. Measure sentence-transformer retrieval locally
4. Translation layer (IndicTrans2 / NLLB) with Hindi/Tamil round trip

See `docs/MERGE_GUIDE.md` for applying this to an existing repo.

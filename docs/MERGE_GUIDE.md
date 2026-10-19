# How to apply this overlay to your repo (Steps 1 + 2, cumulative)

Copy the files into your repo root keeping paths. It is cumulative: it works on top of your original repo OR on top of
the earlier foundation overlay.

## 0. Before you copy — these are YOUR files and they are replaced
Step 2 rewrites these (same function names/signatures, results are a superset). Run `git diff` after copying and keep
any local edits you made:
- `core/extraction.py`, `core/conflict.py`, `core/embeddings.py`, `core/matching.py`, `modules/contract_checker.py`
- `core/schemas.py`, `core/company_profile.py` (Step 1)
Not touched: `core/engine.py`, `modules/state_fit.py`, `modules/drift_monitor.py`, `.gitignore`.

## 1. Branch
    git checkout -b engine-step-2

## 2. Copy the overlay over the repo root, then (if you merged Varsha's branch) delete her old policy files
    git rm data/policy_corpus/*_policy.txt        # her old vague files; canonical files do not end in _policy.txt
Do not commit `data/cuad/*` (keep it gitignored).

## 3. Install and verify
    pip install -r requirements.txt
    python tests/test_foundation.py        # 8 checks
    python tests/test_engine.py            # 17 checks, no model download needed
    python scripts/evaluate.py             # 81 gold cases -> accuracy, confusion matrix, per-category
    python -m modules.contract_checker hashing     # offline demo of the whole pipeline

## 4. On YOUR machine (the sandbox could not download the model)
    python -m modules.contract_checker                          # real sentence-transformer retrieval
    python scripts/evaluate.py --retrieval sentence-transformers --top-k 5
Record the retrieval number; it is the one measurement not yet taken.

## 5. Regenerate data (needs data/cuad/data.zip)
    python scripts/extract_mapped_candidates.py
    python scripts/create_evaluation_sample.py
    python scripts/predict_sample.py       # adds SUGGESTED labels for humans to confirm
    python scripts/build_state_requirements.py

## 6. Commit
    git add -A && git commit -m "Engine: extractor, numeric conflict rules, cached embeddings, evaluation"

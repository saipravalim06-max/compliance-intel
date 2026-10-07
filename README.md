# Compliance Intelligence Platform — Starter Repo

One shared NLP engine, three product modules, built on the same
ingest → translate → segment → embed → match → explain pipeline.

```
core/
  company_profile.py   # the data model every module reads from — build/read this first
  engine.py             # the shared pipeline — fill in the TODOs here, don't duplicate logic in modules/
modules/
  contract_checker.py   # MODULE 2 — build & validate THIS FIRST (you have the data for it already)
  state_fit.py           # MODULE 1 — build SECOND, same engine, different corpus
  drift_monitor.py       # MODULE 3 — build LAST, needs Module 1 & 2 working first
data/
  policy_corpus/         # your synthetic company policy corpus (copy in from policy_corpus.zip)
  state_policies/         # one subdirectory per state, e.g. gujarat/, karnataka/
  cuad/                   # CUAD contract clauses (download from Hugging Face)
app/                       # dashboard — build LAST, after all 3 modules work via script/notebook
tests/
```

## Build order (do not skip ahead)

1. **`core/company_profile.py`** — already has a working example at the
   bottom. Run it (`python core/company_profile.py`) to sanity-check the
   schema makes sense for your use case before building anything else.

2. **`core/engine.py`** — fill in the TODOs in this order:
   - `detect_language()` → wire up `langdetect`
   - `translate_to_english()` → wire up IndicTrans2 or NLLB-200
   - `embed_segments()` → wire up `sentence-transformers` (`all-MiniLM-L6-v2` to start)
   - `match_segments()` → cosine similarity + the numeric-conflict check
   - `generate_explanation()` → grounded explanation from the matched spans

3. **`modules/contract_checker.py`** — once `core/engine.py` is filled in,
   run this against your policy corpus + a CUAD contract. This is your
   first working demo. Get this right before touching anything else.

4. **`modules/state_fit.py`** — add `data/state_policies/gujarat/` and
   `data/state_policies/karnataka/` (just .txt files in the same numbered-
   requirement format as the policy corpus — see README in that folder's
   zip for the format). Run `rank_states()` and sanity-check the output
   makes sense.

5. **`modules/drift_monitor.py`** — leave this alone until 3 and 4 both work.

6. **`app/`** — build a Streamlit dashboard last, once all three modules
   work from a script/notebook. Don't build UI before the logic works —
   it slows down iteration on the part that actually matters.

## Getting your data into this repo

- **Policy corpus**: unzip your existing `policy_corpus.zip` into
  `data/policy_corpus/` (should give you 17 `.txt` files + `policy_index.csv`).
- **CUAD**: `pip install datasets` then
  `from datasets import load_dataset; ds = load_dataset("theatticusproject/cuad-qa")`
  — pull out a handful of contracts to start, save as `.txt` under `data/cuad/`.
- **State policies**: source Gujarat's and Karnataka's official startup
  policy PDFs (search "Gujarat Startup Policy PDF" / "Karnataka Startup
  Policy PDF" on the respective state government / Startup India sites),
  extract text, and reformat into the same numbered-requirement `.txt`
  style as the policy corpus so `segment_policy_text()` can parse them
  without changes.

## Why this structure

Every module is a thin wrapper that calls `core/engine.py` with a
different pair of documents. If you ever find yourself writing matching,
embedding, or explanation logic inside a `modules/*.py` file, stop — that
logic belongs in `core/engine.py` so all three modules stay provably
built on the exact same mechanism. That shared-engine property is also
the core of your patent claim, so keeping it structurally true (not just
true in your head) matters.

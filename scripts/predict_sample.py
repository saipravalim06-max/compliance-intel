"""
scripts/predict_sample.py — pre-fill SUGGESTED labels for the real-CUAD labelling pool.

Reads  data/processed/evaluation_sample.csv   (label column empty: for humans)
Writes data/processed/evaluation_sample_predicted.csv   (adds suggested_* columns)

The human `label` column is never filled in. The suggestions only save time: a
reviewer confirms or corrects them, and only then do they count as ground truth.
Each clause is checked against every numbered line of its mapped policy; the
strongest result is reported (any conflict > any satisfied check > uncertain).
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conflict import detect_conflict  # noqa: E402
from core.extraction import extract_requirement  # noqa: E402
from core.policy_corpus import load_policy_lines  # noqa: E402

RANK = {"CONFLICT": 0, "PARTIAL_CONFLICT": 1, "NO_CONFLICT": 2, "UNCERTAIN": 3}

df = pd.read_csv("data/processed/evaluation_sample.csv")
lines = load_policy_lines("data/policy_corpus")
by_pol = {}
for ln in lines:
    by_pol.setdefault(ln["policy_id"], []).append((ln, extract_requirement(ln["text"], ln["line_id"])))

sug_label, sug_line, sug_reason = [], [], []
for r in df.itertuples():
    creq = extract_requirement(r.clause_text, r.pair_id)
    best = None
    for ln, preq in by_pol[r.policy_id]:
        res = detect_conflict(creq, preq)
        if best is None or RANK[res["label"]] < RANK[best[0]["label"]]:
            best = (res, ln)
    sug_label.append(best[0]["label"])
    sug_line.append(best[1]["line_id"] if best[0]["label"] != "UNCERTAIN" else "")
    sug_reason.append(best[0]["reason"])

df["suggested_label"], df["suggested_policy_line"], df["suggested_reason"] = sug_label, sug_line, sug_reason
df.to_csv("data/processed/evaluation_sample_predicted.csv", index=False)
print(df.suggested_label.value_counts().to_string())
print("\nhuman `label` column left empty:", int(df.label.isna().sum()), "of", len(df))

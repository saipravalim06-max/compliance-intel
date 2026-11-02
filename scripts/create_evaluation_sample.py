"""
scripts/create_evaluation_sample.py

Creates data/processed/evaluation_sample.csv — the pool to be hand-labelled.

Improvements over head(3)-per-category:
  * reproducible random sample (fixed seed), not "first rows in file order"
  * only 'strong' mappings by default (weak ones dominate by volume otherwise)
  * drops redacted ([***]) and very short/long clauses
  * half of each category's picks must contain a number, because numeric
    thresholds are what the conflict detector is meant to test
  * at most 1 clause per contract per category (no single-contract bias)

Labels to fill in: CONFLICT | NO_CONFLICT | PARTIAL_CONFLICT | UNCERTAIN
"""
import argparse
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--per-category", type=int, default=4)
ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--strengths", default="strong")
ap.add_argument("--inp", default="data/processed/final_candidate_clauses.csv")
ap.add_argument("--out", default="data/processed/evaluation_sample.csv")
a = ap.parse_args()

df = pd.read_csv(a.inp)
df = df[df.mapping_strength.isin(a.strengths.split(","))]
df = df[(~df.has_redaction) & df.n_chars.between(40, 700)]
df = df.sample(frac=1, random_state=a.seed).drop_duplicates(["cuad_category", "contract_id"])

picked = []
for cat, g in df.groupby("cuad_category"):
    half = a.per_category // 2
    with_num = g[g.has_number].head(half)
    rest = g.drop(with_num.index).head(a.per_category - len(with_num))
    picked.append(pd.concat([with_num, rest]))
out = pd.concat(picked).reset_index(drop=True)
out.insert(0, "pair_id", [f"CP-{i+1:03d}" for i in range(len(out))])
out["label"] = ""
out["reason"] = ""
out["notes"] = ""
out = out.drop(columns=["answer_start"])
idx = pd.read_csv("data/policy_corpus/policy_index.csv")
texts = {r.policy_id: open("data/policy_corpus/" + r.file_name, encoding="utf-8").read().strip() for r in idx.itertuples()}
out.insert(out.columns.get_loc("policy_name") + 1, "policy_text", out.policy_id.map(texts))
out.to_csv(a.out, index=False)
print(f"{len(out)} pairs -> {a.out}")
print(out.groupby("cuad_category").size().to_string())
print("with a number:", int(out.has_number.sum()), "of", len(out))

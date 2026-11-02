"""
scripts/extract_mapped_candidates.py

Builds data/processed/final_candidate_clauses.csv: real CUAD clause spans paired
with the policy they map to.

Changes vs the first version:
  * category matching is case/space-insensitive (CUAD uses 'Cap On Liability',
    'Ip Ownership Assignment', ... which silently failed before)
  * a mapped category that does not exist in CUAD is a hard error, not a silent skip
  * policy text comes from policy_index.csv (no glob guessing)
  * adds mapping_strength, has_number, has_redaction, n_chars for filtering

Run from the repo root:
    python scripts/extract_mapped_candidates.py [--cuad-zip data/cuad/data.zip]
"""
import argparse
import csv
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

CATEGORY_RE = re.compile(r'related to "([^"]+)"')


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cuad-zip", default="data/cuad/data.zip")
    ap.add_argument("--mapping", default="data/processed/cuad_policy_mapping.csv")
    ap.add_argument("--policy-dir", default="data/policy_corpus")
    ap.add_argument("--out", default="data/processed/final_candidate_clauses.csv")
    args = ap.parse_args()

    mapping = pd.read_csv(args.mapping)
    index = pd.read_csv(Path(args.policy_dir) / "policy_index.csv")
    policy_text = {
        r.policy_id: (Path(args.policy_dir) / r.file_name).read_text(encoding="utf-8").strip()
        for r in index.itertuples()
    }
    unknown = set(mapping.policy_id) - set(policy_text)
    if unknown:
        raise SystemExit(f"Mapping references policy IDs not in policy_index.csv: {sorted(unknown)}")

    by_key = {norm(r.cuad_category): r for r in mapping.itertuples()}

    with zipfile.ZipFile(args.cuad_zip) as z, z.open("CUADv1.json") as f:
        articles = json.load(f)["data"]

    rows, seen_keys, cuad_names = [], set(), set()
    for art in articles:
        for para in art.get("paragraphs", []):
            for qa in para.get("qas", []):
                m = CATEGORY_RE.search(qa.get("question", ""))
                if not m:
                    continue
                cuad_names.add(m.group(1))
                key = norm(m.group(1))
                if key not in by_key:
                    continue
                seen_keys.add(key)
                r = by_key[key]
                for ans in qa.get("answers", []):
                    text = ans.get("text", "").strip()
                    if not text:
                        continue
                    rows.append({
                        "contract_id": art.get("title", ""),
                        "cuad_category": m.group(1),
                        "clause_text": text,
                        "answer_start": ans.get("answer_start"),
                        "policy_id": r.policy_id,
                        "policy_name": r.policy_name,
                        "mapping_strength": r.mapping_strength,
                    })

    missing = [r.cuad_category for r in mapping.itertuples() if norm(r.cuad_category) not in {norm(n) for n in cuad_names}]
    if missing:
        raise SystemExit(f"Mapped categories that do not exist in CUAD: {missing}")
    empty = [r.cuad_category for r in mapping.itertuples() if norm(r.cuad_category) not in seen_keys]
    if empty:
        print("WARNING: categories exist in CUAD but returned no annotated clauses:", empty)

    df = pd.DataFrame(rows)
    df["n_chars"] = df.clause_text.str.len()
    df["has_number"] = df.clause_text.str.contains(r"\d")
    df["has_redaction"] = df.clause_text.str.contains(r"\[\s*\*+\s*\]|\*{3,}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, quoting=csv.QUOTE_NONNUMERIC)

    print(f"{len(df)} candidate clauses from {df.contract_id.nunique()} contracts -> {args.out}")
    print(df.groupby(["mapping_strength", "cuad_category"]).size().to_string())


if __name__ == "__main__":
    main()

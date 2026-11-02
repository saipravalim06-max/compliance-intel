"""
load_policies.py — loads the canonical policy corpus.

policy_index.csv is the single source of truth (unique policy_id per file).
Columns: policy_id, policy_name, domain, file_name,
         key_quantifiable_requirements, cuad_coverage

Usage:
    from data.policy_corpus.load_policies import load_policy_corpus, get_requirement_lines
    corpus = load_policy_corpus("data/policy_corpus")
"""
import csv
import os
import re

_REQ = re.compile(r"^\d+\.\d+\s")


def load_policy_corpus(corpus_dir: str):
    """Return a list of dicts: index columns + full_text. Fails loudly on
    missing files or duplicate policy IDs (no silent glob guessing)."""
    records, seen = [], set()
    with open(os.path.join(corpus_dir, "policy_index.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["policy_id"]
            if pid in seen:
                raise ValueError(f"Duplicate policy_id in policy_index.csv: {pid}")
            seen.add(pid)
            path = os.path.join(corpus_dir, row["file_name"])
            with open(path, encoding="utf-8") as pf:
                row["full_text"] = pf.read()
            records.append(row)
    return records


def get_requirement_lines(full_text: str):
    """Numbered requirement lines ('2.1 ...') — the unit used for matching."""
    return [ln.strip() for ln in full_text.splitlines() if _REQ.match(ln.strip())]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    corpus = load_policy_corpus(here)
    total = 0
    for p in corpus:
        n = len(get_requirement_lines(p["full_text"]))
        total += n
        print(f"{p['policy_id']}  {p['policy_name']:<45} {n} requirement lines")
    print(f"\n{len(corpus)} policies, {total} requirement lines")

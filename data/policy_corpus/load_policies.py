"""
load_policies.py

Utility to load the synthetic company policy corpus into a pandas DataFrame,
ready for embedding and semantic matching against CUAD contract clauses.

Usage:
    from load_policies import load_policy_corpus
    df = load_policy_corpus("policy_corpus")
    print(df.head())
"""

import os
import csv


def load_policy_corpus(corpus_dir: str):
    """
    Loads policy_index.csv + the full text of each policy file.

    Returns a list of dicts, one per policy, with keys:
        policy_id, title, category, file_name, key_quantifiable_requirements, full_text
    (Convert to a pandas DataFrame yourself if you have pandas installed:
        import pandas as pd
        df = pd.DataFrame(load_policy_corpus("policy_corpus"))
    )
    """
    index_path = os.path.join(corpus_dir, "policy_index.csv")
    records = []

    with open(index_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_path = os.path.join(corpus_dir, row["file_name"])
            with open(file_path, encoding="utf-8") as pf:
                full_text = pf.read()
            row["full_text"] = full_text
            records.append(row)

    return records


def get_requirement_sections(full_text: str):
    """
    Splits a policy's full text into individual numbered requirement lines
    (e.g. '2.1 ...', '2.2 ...') for finer-grained embedding/matching than
    whole-document comparison. Useful because a contract clause usually
    maps to ONE specific requirement line, not an entire policy document.
    """
    lines = full_text.splitlines()
    requirements = []
    for line in lines:
        stripped = line.strip()
        # crude heuristic: requirement lines start with "N.N " (e.g. "2.3 ")
        if len(stripped) > 4 and stripped[0].isdigit() and "." in stripped[:4]:
            requirements.append(stripped)
    return requirements


if __name__ == "__main__":
    corpus = load_policy_corpus(os.path.dirname(__file__) or ".")
    print(f"Loaded {len(corpus)} policy documents.\n")
    for policy in corpus:
        reqs = get_requirement_sections(policy["full_text"])
        print(f"{policy['policy_id']} — {policy['title']} ({len(reqs)} requirement lines)")

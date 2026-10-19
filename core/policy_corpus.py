"""core/policy_corpus.py — load the canonical policy corpus as individual requirement lines."""
import csv
import os
import re
from typing import Dict, List

_REQ = re.compile(r"^(\d+\.\d+)\s+(.*)$")


def load_policy_lines(corpus_dir: str = "data/policy_corpus") -> List[Dict]:
    """One dict per numbered requirement line: policy_id, policy_name, line_no, text, line_id.
    line_id looks like 'POL-05#2.1'."""
    lines = []
    with open(os.path.join(corpus_dir, "policy_index.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            with open(os.path.join(corpus_dir, row["file_name"]), encoding="utf-8") as pf:
                for raw in pf.read().splitlines():
                    m = _REQ.match(raw.strip())
                    if m:
                        lines.append({"policy_id": row["policy_id"], "policy_name": row["policy_name"],
                                      "line_no": m.group(1), "text": m.group(2).strip(),
                                      "line_id": f"{row['policy_id']}#{m.group(1)}"})
    return lines


def get_line(lines: List[Dict], line_id: str) -> Dict:
    for ln in lines:
        if ln["line_id"] == line_id:
            return ln
    raise KeyError(f"policy line not found: {line_id}")

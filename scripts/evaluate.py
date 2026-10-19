"""
scripts/evaluate.py — measure the conflict engine against a labelled set.

    python scripts/evaluate.py                         # conflict logic, gold policy line supplied
    python scripts/evaluate.py --retrieval hashing     # + can retrieval find the gold line? (offline baseline)
    python scripts/evaluate.py --retrieval sentence-transformers --top-k 5
    python scripts/evaluate.py --report results/eval_report.md

Two things are measured separately on purpose:
  1. LABEL QUALITY  extraction + conflict rules, with the correct policy line handed over
  2. RETRIEVAL      does the matcher put the correct policy line in the top-k?
so a retrieval miss is never confused with a reasoning error.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conflict import detect_conflict  # noqa: E402
from core.extraction import extract_requirement  # noqa: E402
from core.policy_corpus import get_line, load_policy_lines  # noqa: E402

LABELS = ["CONFLICT", "PARTIAL_CONFLICT", "NO_CONFLICT", "UNCERTAIN"]


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="tests/datasets/evaluation_set.json")
    ap.add_argument("--corpus", default="data/policy_corpus")
    ap.add_argument("--retrieval", choices=["hashing", "sentence-transformers"], default=None)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    cases = json.load(open(a.data, encoding="utf-8"))["cases"]
    lines = load_policy_lines(a.corpus)

    rows, conf = [], Counter()
    for c in cases:
        pol = get_line(lines, c["policy_line"])
        res = detect_conflict(extract_requirement(c["clause"], "C"), extract_requirement(pol["text"], pol["line_id"]))
        rows.append({**c, "predicted": res["label"], "reason": res["reason"]})
        conf[(c["expected"], res["label"])] += 1

    n = len(rows)
    correct = sum(r["expected"] == r["predicted"] for r in rows)
    out = [f"# Evaluation report\n", f"Cases: {n} (all synthetic) | accuracy: {correct}/{n} = {correct / n:.1%}\n"]

    out.append("## Per-label precision / recall / F1\n")
    out.append("| label | support | precision | recall | F1 |\n|---|---|---|---|---|")
    for lab in LABELS:
        tp = conf[(lab, lab)]
        fp = sum(conf[(o, lab)] for o in LABELS if o != lab)
        fn = sum(conf[(lab, o)] for o in LABELS if o != lab)
        p, r, f = prf(tp, fp, fn)
        out.append(f"| {lab} | {tp + fn} | {p:.2f} | {r:.2f} | {f:.2f} |")

    out.append("\n## Confusion matrix (rows = gold, columns = predicted)\n")
    out.append("| gold \\ predicted | " + " | ".join(LABELS) + " |\n|---|" + "---|" * len(LABELS))
    for g in LABELS:
        out.append(f"| {g} | " + " | ".join(str(conf[(g, p)]) for p in LABELS) + " |")

    by_cat = defaultdict(lambda: [0, 0])
    for r in rows:
        by_cat[r["category"]][1] += 1
        by_cat[r["category"]][0] += r["expected"] == r["predicted"]
    out.append("\n## Accuracy by category\n")
    out.append("| category | correct / total |\n|---|---|")
    for cat, (ok, tot) in sorted(by_cat.items()):
        out.append(f"| {cat} | {ok}/{tot} |")

    fails = [r for r in rows if r["expected"] != r["predicted"]]
    out.append(f"\n## Failures ({len(fails)})\n")
    for r in fails:
        out.append(f"- **{r['id']}** gold={r['expected']} predicted={r['predicted']} vs {r['policy_line']}\n  clause: {r['clause']}\n  reason: {r['reason']}")
    if not fails:
        out.append("None.")

    if a.retrieval:
        from core.engine import Segment
        from core.matching import PolicyMatcher
        matcher = PolicyMatcher(backend=a.retrieval, similarity_threshold=-1.0)
        segs = [Segment(ln["policy_id"], ln["line_id"], ln["text"], "en") for ln in lines]
        hits, rr = 0, 0.0
        for c in cases:
            ranked = matcher.match(Segment("C", "C-1", c["clause"], "en"), segs, top_k=len(segs))
            ids = [s.segment_id for s, _ in ranked]
            rank = ids.index(c["policy_line"]) + 1
            hits += rank <= a.top_k
            rr += 1 / rank
        out.append(f"\n## Retrieval ({a.retrieval}, {len(lines)} policy lines)\n")
        out.append(f"- gold line in top-{a.top_k}: {hits}/{n} = {hits / n:.1%}\n- mean reciprocal rank: {rr / n:.3f}")

    text = "\n".join(out)
    print(text)
    if a.report:
        os.makedirs(os.path.dirname(a.report) or ".", exist_ok=True)
        open(a.report, "w", encoding="utf-8").write(text + "\n")


if __name__ == "__main__":
    main()

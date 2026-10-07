"""
modules/contract_checker.py — MODULE 2

Build and validate this module FIRST. You already have the data for it
(CUAD contract clauses + the synthetic policy corpus), so it's your fastest
path to a working, demoable result — and it proves out the shared engine
before you point it at anything else.

This module contains almost no logic of its own — it just calls the shared
engine with (contract clauses) as source and (company's own policy corpus)
as target. If you find yourself writing matching logic here, move it to
core/engine.py instead.
"""

import os
from core.engine import (
    ingest_document,
    detect_language,
    translate_to_english,
    segment_policy_text,
    segment_contract_text,
    embed_segments,
    match_segments,
    generate_explanation,
)


def check_contract_against_policies(contract_path: str, policy_corpus_dir: str):
    """
    End-to-end: one contract file -> list of MatchResult flagged conflicts
    against every policy in the corpus directory.
    """
    # 1. Ingest + detect language + translate the contract
    raw_text = ingest_document(contract_path)
    lang = detect_language(raw_text)
    english_text = translate_to_english(raw_text, lang)

    # 2. Segment the contract into clauses
    contract_segments = segment_contract_text(
        doc_id=os.path.basename(contract_path),
        text=english_text,
        language=lang,
    )

    # 3. Load + segment every policy in the corpus
    policy_segments = []
    for fname in os.listdir(policy_corpus_dir):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(policy_corpus_dir, fname)
        text = ingest_document(path)
        policy_segments.extend(segment_policy_text(doc_id=fname, text=text))

    # 4. Embed both sides
    contract_segments = embed_segments(contract_segments)
    policy_segments = embed_segments(policy_segments)

    # 5. Match + score
    matches = match_segments(contract_segments, policy_segments)

    # 6. Explain, back in the original language if the contract wasn't English
    for match in matches:
        match.explanation = generate_explanation(
            match, target_language=lang if lang != "en" else None
        )

    return matches


if __name__ == "__main__":
    # Example run once the TODOs in core/engine.py are filled in:
    #
    # results = check_contract_against_policies(
    #     contract_path="data/cuad/sample_contract.txt",
    #     policy_corpus_dir="data/policy_corpus",
    # )
    # for r in results:
    #     if r.numeric_conflict:
    #         print(r.explanation)
    print("Fill in core/engine.py's TODOs, then uncomment the example above.")

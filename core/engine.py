"""
core/engine.py

THE shared engine. Modules 1, 2, and 3 all call into this — none of them
should contain their own embedding/matching/explanation logic. If you find
yourself writing matching logic inside a module file, it belongs here instead.

Pipeline: ingest -> (translate) -> segment -> embed -> match -> explain

This file is intentionally a skeleton with clear TODOs — fill in the model
calls, don't restructure the flow. The flow IS your architecture.
"""

from dataclasses import dataclass
from typing import List, Optional
import re


# ---------------------------------------------------------------------------
# Data structures passed between pipeline stages
# ---------------------------------------------------------------------------

@dataclass
class Segment:
    """One clause or policy requirement line, after segmentation."""
    source_doc_id: str
    segment_id: str
    original_text: str
    original_language: str
    translated_text: Optional[str] = None  # English, for matching
    embedding: Optional[list] = None


@dataclass
class MatchResult:
    """One semantic match between a contract/profile segment and a
    policy/regulation segment, with a conflict verdict."""
    source_segment: Segment
    target_segment: Segment
    similarity_score: float
    numeric_conflict: bool
    severity: str  # "high" | "medium" | "low" | "none"
    explanation: str  # grounded in the actual overlapping text, not generated freely


# ---------------------------------------------------------------------------
# Stage 1: Ingestion
# ---------------------------------------------------------------------------

def ingest_document(file_path: str) -> str:
    """
    Extract raw text from a PDF/DOCX/TXT file.
    TODO: wire up PyMuPDF (fitz) for PDF, python-docx for DOCX.
    For .txt files (like the policy corpus), just read directly.
    """
    if file_path.endswith(".txt"):
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    raise NotImplementedError(
        f"Wire up a PDF/DOCX extractor for: {file_path}. "
        "Use PyMuPDF for PDF, python-docx for DOCX."
    )


# ---------------------------------------------------------------------------
# Stage 2: Language detection + translation
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str:
    """
    TODO: wire up langdetect or fastText lang-id.
    Return an ISO code, e.g. 'en', 'hi', 'ta'.
    """
    return "en"  # stub default — replace with real detection


def translate_to_english(text: str, source_lang: str) -> str:
    """
    TODO: wire up IndicTrans2 (Indian languages) or NLLB-200 (broader).
    IMPORTANT: this is only used to produce the text you embed/match on.
    Keep the untranslated `original_text` on the Segment so explanations
    can be reconstructed in the original language later — that alignment
    is the whole point of the cross-lingual explainability claim.
    """
    if source_lang == "en":
        return text
    raise NotImplementedError("Wire up IndicTrans2 / NLLB-200 here.")


# ---------------------------------------------------------------------------
# Stage 3: Segmentation
# ---------------------------------------------------------------------------

REQUIREMENT_LINE_PATTERN = re.compile(r"^\d+\.\d+\s")


def segment_policy_text(doc_id: str, text: str, language: str = "en") -> List[Segment]:
    """
    Splits a policy document into individual numbered requirement lines
    (the "2.1 ...", "2.2 ..." pattern used in the policy corpus). This gives
    finer-grained matching than comparing a clause against a whole document.
    """
    segments = []
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if REQUIREMENT_LINE_PATTERN.match(stripped):
            segments.append(Segment(
                source_doc_id=doc_id,
                segment_id=f"{doc_id}-req-{i}",
                original_text=stripped,
                original_language=language,
            ))
    return segments


def segment_contract_text(doc_id: str, text: str, language: str = "en") -> List[Segment]:
    """
    TODO: real clause segmentation. Start simple — split on paragraph breaks
    or numbered clause headers — then upgrade to a sentence-transformer-based
    boundary detector if the simple version isn't accurate enough. Don't
    over-engineer this early; CUAD's own clause boundaries are a good
    reference/validation set once you're using real CUAD data.
    """
    raise NotImplementedError("Implement clause segmentation for contract text.")


# ---------------------------------------------------------------------------
# Stage 4: Embedding
# ---------------------------------------------------------------------------

def embed_segments(segments: List[Segment]) -> List[Segment]:
    """
    TODO: wire up sentence-transformers (start with 'all-MiniLM-L6-v2' for a
    fast baseline). Embed `translated_text` if present, else `original_text`.
    Mutates and returns the same list with `.embedding` filled in.
    """
    raise NotImplementedError("Wire up sentence-transformers here.")


# ---------------------------------------------------------------------------
# Stage 5: Matching + numeric conflict detection
# ---------------------------------------------------------------------------

NUMBER_PATTERN = re.compile(r"\d+(\.\d+)?")


def extract_numbers(text: str) -> List[float]:
    return [float(n) for n in NUMBER_PATTERN.findall(text) if n]


def match_segments(
    source_segments: List[Segment],
    target_segments: List[Segment],
    similarity_threshold: float = 0.6,
    top_k: int = 3,
) -> List[MatchResult]:
    """
    For each source segment (a contract clause or company-profile chunk),
    find the top-k most similar target segments (policy/regulation
    requirement lines), then check for a numeric mismatch to decide
    conflict severity.

    TODO: replace the cosine-similarity stub with real vector comparison
    (e.g. using numpy or sentence-transformers' util.cos_sim).
    """
    raise NotImplementedError(
        "1. Compute cosine similarity between source and target embeddings.\n"
        "2. Keep matches above similarity_threshold.\n"
        "3. For each kept match, extract_numbers() from both texts.\n"
        "4. If numbers differ meaningfully (e.g. clause says 7, policy says "
        "30), mark numeric_conflict=True and set severity accordingly.\n"
        "5. Build the MatchResult with an explanation grounded in the "
        "actual overlapping text span — not a freely generated sentence."
    )


# ---------------------------------------------------------------------------
# Stage 6: Explanation (grounded, cross-lingual)
# ---------------------------------------------------------------------------

def generate_explanation(match: MatchResult, target_language: Optional[str] = None) -> str:
    """
    Builds a human-readable explanation grounded in the matched text spans
    (not a free-form LLM summary). If target_language is set and differs
    from English, translate the explanation back using the SAME sentence
    alignment captured during ingestion — this alignment-preserving
    reverse-explanation step is your strongest novelty claim, so don't
    shortcut it by just re-translating from scratch.
    """
    base = (
        f"Clause: \"{match.source_segment.original_text}\" "
        f"may conflict with requirement \"{match.target_segment.original_text}\" "
        f"(similarity: {match.similarity_score:.2f})."
    )
    if target_language and target_language != "en":
        raise NotImplementedError(
            "Translate `base` back into target_language using the "
            "sentence-level alignment preserved from ingestion, not a "
            "fresh translation of the English explanation."
        )
    return base

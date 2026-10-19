from typing import List, Optional, Tuple

from core.embeddings import EmbeddingModel, get_model
from core.engine import Segment


def _text(seg: Segment) -> str:
    return seg.translated_text if seg.translated_text else seg.original_text


class PolicyMatcher:
    """
    Finds the company-policy requirements that are semantically relevant to a
    contract clause.

    Matching answers: "Which policy requirements are about the same topic?"
    It does NOT answer: "Do they conflict?" — that is core.conflict's job.

    The embedding model is shared and caches every text, so policy lines are
    encoded once and each additional clause costs one encode + one matrix product.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.50,
        backend: str = "sentence-transformers",
        model: Optional[EmbeddingModel] = None,
    ):
        self.embedding_model = model or get_model(model_name, backend)
        self.similarity_threshold = similarity_threshold

    def match(
        self,
        contract_segment: Segment,
        policy_segments: List[Segment],
        top_k: int = 3,
    ) -> List[Tuple[Segment, float]]:
        """Top-k policy segments above similarity_threshold, most similar first."""
        if not policy_segments:
            return []
        sims = self.embedding_model.similarity_matrix(
            [_text(contract_segment)], [_text(p) for p in policy_segments]
        )[0]
        ranked = sorted(zip(policy_segments, sims.tolist()), key=lambda x: x[1], reverse=True)
        return [(p, s) for p, s in ranked if s >= self.similarity_threshold][:top_k]

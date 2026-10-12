from typing import List, Tuple

from core.embeddings import EmbeddingModel
from core.engine import Segment


class PolicyMatcher:
    """
    Finds the company-policy requirements that are semantically
    relevant to a contract clause.

    Matching answers:
        "Which policy requirements are about the same topic?"

    It does NOT answer:
        "Do they conflict?"

    Conflict reasoning is handled separately by core.conflict.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.50,
    ):
        self.embedding_model = EmbeddingModel(model_name)
        self.similarity_threshold = similarity_threshold

    def match(
        self,
        contract_segment: Segment,
        policy_segments: List[Segment],
        top_k: int = 3,
    ) -> List[Tuple[Segment, float]]:
        """
        Return the top-k policy segments most semantically similar
        to the contract segment.

        Only candidates above similarity_threshold are returned.
        """

        contract_text = (
            contract_segment.translated_text
            if contract_segment.translated_text
            else contract_segment.original_text
        )

        results = []

        for policy_segment in policy_segments:
            policy_text = (
                policy_segment.translated_text
                if policy_segment.translated_text
                else policy_segment.original_text
            )

            score = self.embedding_model.similarity(
                contract_text,
                policy_text,
            )

            if score >= self.similarity_threshold:
                results.append((policy_segment, score))

        results.sort(key=lambda item: item[1], reverse=True)

        return results[:top_k]
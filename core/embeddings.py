from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from core.engine import Segment


class EmbeddingModel:
    """
    Shared sentence-transformer embedding model.

    We use embeddings to determine which contract clauses and
    company-policy requirements are semantically related.

    IMPORTANT:
    Similarity indicates relevance, not conflict.
    Conflict is decided separately by core.conflict.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Convert a list of texts into normalized embeddings.
        """
        return self.model.encode(
            texts,
            normalize_embeddings=True,
        )

    def similarity(self, text_a: str, text_b: str) -> float:
        """
        Calculate cosine similarity between two pieces of text.
        Because embeddings are normalized, their dot product is
        equivalent to cosine similarity.
        """
        embeddings = self.encode([text_a, text_b])

        return float(np.dot(embeddings[0], embeddings[1]))


def embed_segments(segments: List[Segment]) -> List[Segment]:
    """
    Add embeddings to Segment objects.

    If translated_text exists, use it for matching.
    Otherwise use the original text.
    """

    model = EmbeddingModel()

    texts = [
        segment.translated_text
        if segment.translated_text
        else segment.original_text
        for segment in segments
    ]

    embeddings = model.encode(texts)

    for segment, embedding in zip(segments, embeddings):
        segment.embedding = embedding.tolist()

    return segments
from typing import Dict, List, Optional
import re
import zlib

import numpy as np

from core.engine import Segment


class HashingEncoder:
    """Deterministic, dependency-free bag-of-words encoder (unigrams + bigrams hashed to
    `dim` buckets). It is NOT a semantic model — it exists so retrieval and the whole
    pipeline can be tested offline, and as a lexical baseline to compare the sentence
    transformer against in the report."""

    _STOP = set("a an the of and or to in on for by with is are be shall must may will this that any all".split())

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def encode(self, texts: List[str], normalize_embeddings: bool = True) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            toks = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in self._STOP]
            grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
            for g in grams:
                out[i, zlib.crc32(g.encode()) % self.dim] += 1.0
        if normalize_embeddings:
            norms = np.linalg.norm(out, axis=1, keepdims=True)
            out = out / np.where(norms == 0, 1, norms)
        return out


class EmbeddingModel:
    """
    Shared embedding model with an in-memory cache, so every distinct text is
    encoded once no matter how many clauses are checked against it.

    backend="sentence-transformers" (default) loads the real model lazily;
    backend="hashing" uses the offline HashingEncoder.

    IMPORTANT: similarity indicates relevance, not conflict. Conflict is decided
    by core.conflict.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", backend: str = "sentence-transformers"):
        self.model_name, self.backend = model_name, backend
        if backend == "hashing":
            self.model = HashingEncoder()
        elif backend == "sentence-transformers":
            from sentence_transformers import SentenceTransformer  # imported lazily
            self.model = SentenceTransformer(model_name)
        else:
            raise ValueError(f"unknown backend: {backend}")
        self._cache: Dict[str, np.ndarray] = {}

    def encode(self, texts: List[str]) -> np.ndarray:
        """Normalized embeddings, batch-encoding only the texts not seen before."""
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            vecs = self.model.encode(missing, normalize_embeddings=True)
            for t, v in zip(missing, vecs):
                self._cache[t] = np.asarray(v)
        return np.vstack([self._cache[t] for t in texts]) if texts else np.zeros((0, 1))

    def similarity(self, text_a: str, text_b: str) -> float:
        e = self.encode([text_a, text_b])
        return float(np.dot(e[0], e[1]))

    def similarity_matrix(self, queries: List[str], docs: List[str]) -> np.ndarray:
        """(len(queries) x len(docs)) cosine similarities in one matrix product."""
        return self.encode(queries) @ self.encode(docs).T


_MODELS: Dict[tuple, EmbeddingModel] = {}


def get_model(model_name: str = "all-MiniLM-L6-v2", backend: str = "sentence-transformers") -> EmbeddingModel:
    """One shared model per (name, backend) for the whole process."""
    key = (model_name, backend)
    if key not in _MODELS:
        _MODELS[key] = EmbeddingModel(model_name, backend)
    return _MODELS[key]


def embed_segments(segments: List[Segment], model: Optional[EmbeddingModel] = None) -> List[Segment]:
    """Add embeddings to Segment objects (uses translated_text when present)."""
    model = model or get_model()
    texts = [s.translated_text if s.translated_text else s.original_text for s in segments]
    for segment, vec in zip(segments, model.encode(texts)):
        segment.embedding = vec.tolist()
    return segments

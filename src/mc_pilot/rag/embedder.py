"""Embedding adapter for BAAI/bge-small-zh-v1.5."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "BAAI/bge-small-zh-v1.5"
DEFAULT_DIMENSION = 512
CHUNKER_VERSION = "1.0.0"


class Embedder:
    """Generates dense vectors using sentence-transformers."""

    _model_id: str
    _model: Any
    _dimension: int

    def __init__(self, model_id: str = DEFAULT_MODEL_ID) -> None:
        self._model_id = model_id
        logger.info("Loading embedding model", extra={"model": model_id})
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_id)
        dim: int | None = self._model.get_sentence_embedding_dimension()
        self._dimension = DEFAULT_DIMENSION if dim is None else dim

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return [v.tolist() for v in vectors]

    def encode_single(self, text: str) -> list[float]:
        return self.encode([text])[0]

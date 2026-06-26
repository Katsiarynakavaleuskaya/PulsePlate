"""Embedding provider for RAG vector retrieval.

Thin adapter around FastEmbed/ONNX following the existing ProviderBase pattern.
Model is loaded lazily on the first ``.encode()`` call to avoid import-time
side effects (OpenAPI generation safety, feature-flag gating).

Usage::

    from providers.embeddings import FastEmbedTextEmbeddings

    provider = FastEmbedTextEmbeddings()        # no model load yet
    vectors = provider.encode(["hello world"])   # loads model on first call

Feature-gated via ``FEATURE_RAG_VECTOR``; callers should check the flag
before instantiating.
"""

from __future__ import annotations

import logging
import math
import threading
from typing import Any, Protocol, runtime_checkable

from core.rag.rag_constants import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers (structural typing)."""

    model_name: str
    dimensions: int

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts into dense vectors.

        Returns a list of float vectors, one per input text.
        Each vector has length ``self.dimensions``.
        """
        ...  # pragma: no cover


class FastEmbedTextEmbeddings:
    """Thin adapter around FastEmbed's ONNX text embedding runtime.

    Thread-safe: model loading is guarded by a lock.
    Lazy: model is not loaded until the first ``.encode()`` call.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL_NAME,
        dimensions: int = EMBEDDING_DIMENSIONS,
    ) -> None:
        self.model_name = model_name
        self.dimensions = dimensions
        self._model: Any | None = None
        self._lock = threading.Lock()

    def _load_model(self) -> Any:
        """Lazy-load the FastEmbed text embedding model (thread-safe)."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(model_name=self.model_name)
                    logger.info(
                        "Loaded embedding model %s (dim=%d)",
                        self.model_name,
                        self.dimensions,
                    )
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts into dense float vectors.

        Args:
            texts: list of strings to encode.

        Returns:
            List of float vectors, each of length ``self.dimensions``.
        """
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.embed(texts)
        return [self._normalize_embedding_row(row) for row in embeddings]

    def _normalize_embedding_row(self, row: Any) -> list[float]:
        """Return a finite Python float vector with the configured dimensions."""
        values = row.tolist() if hasattr(row, "tolist") else list(row)
        vector = [float(value) for value in values]
        if len(vector) != self.dimensions:
            raise ValueError(
                f"embedding dimension mismatch: got {len(vector)}, expected {self.dimensions}"
            )
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("embedding contains non-finite values")
        return vector


__all__ = ["EmbeddingProvider", "FastEmbedTextEmbeddings"]

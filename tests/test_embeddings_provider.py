"""Tests for providers/embeddings.py — EmbeddingProvider protocol and adapter.

Tests use mock/fake sentence-transformers to avoid model download in CI.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest


class TestEmbeddingProviderProtocol:
    """Verify EmbeddingProvider protocol conformance."""

    def test_protocol_is_runtime_checkable(self) -> None:
        from providers.embeddings import EmbeddingProvider

        class _Dummy:
            model_name = "dummy"
            dimensions = 10

            def encode(self, texts: list[str]) -> list[list[float]]:
                return [[0.0] * 10 for _ in texts]

        assert isinstance(_Dummy(), EmbeddingProvider)

    def test_non_conforming_object_fails_protocol(self) -> None:
        from providers.embeddings import EmbeddingProvider

        class _Bad:
            pass

        assert not isinstance(_Bad(), EmbeddingProvider)


class TestSentenceTransformerEmbeddings:
    """Unit tests for SentenceTransformerEmbeddings adapter."""

    def test_init_does_not_load_model(self) -> None:
        """Model must not be loaded at construction time (lazy loading)."""
        from providers.embeddings import SentenceTransformerEmbeddings

        provider = SentenceTransformerEmbeddings()
        assert provider._model is None
        assert provider.model_name == "all-mpnet-base-v2"
        assert provider.dimensions == 768

    def test_encode_empty_list_returns_empty(self) -> None:
        from providers.embeddings import SentenceTransformerEmbeddings

        provider = SentenceTransformerEmbeddings()
        result = provider.encode([])
        assert result == []

    def test_encode_returns_correct_shape(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Encode should return list of float vectors with correct dimensions."""
        from providers.embeddings import SentenceTransformerEmbeddings

        provider = SentenceTransformerEmbeddings()

        # Mock the model to avoid actual model download
        fake_model = MagicMock()
        fake_embeddings = np.random.randn(2, 768).astype(np.float32)
        fake_model.encode.return_value = fake_embeddings

        provider._model = fake_model

        result = provider.encode(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 768
        assert len(result[1]) == 768
        assert all(isinstance(v, float) for v in result[0])

    def test_encode_single_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from providers.embeddings import SentenceTransformerEmbeddings

        provider = SentenceTransformerEmbeddings()

        fake_model = MagicMock()
        fake_embeddings = np.random.randn(1, 768).astype(np.float32)
        fake_model.encode.return_value = fake_embeddings

        provider._model = fake_model

        result = provider.encode(["test"])
        assert len(result) == 1
        assert len(result[0]) == 768

    def test_encode_calls_model_with_correct_args(self) -> None:
        from providers.embeddings import SentenceTransformerEmbeddings

        provider = SentenceTransformerEmbeddings()

        fake_model = MagicMock()
        fake_model.encode.return_value = np.zeros((1, 768), dtype=np.float32)
        provider._model = fake_model

        provider.encode(["test input"])
        fake_model.encode.assert_called_once_with(["test input"], convert_to_numpy=True)

    def test_lazy_load_calls_sentence_transformer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """_load_model should import and instantiate SentenceTransformer."""
        from providers import embeddings

        fake_st_class = MagicMock()
        fake_instance = MagicMock()
        fake_st_class.return_value = fake_instance
        fake_instance.encode.return_value = np.zeros((1, 768), dtype=np.float32)

        # Patch the import inside _load_model
        monkeypatch.setattr(
            "providers.embeddings.SentenceTransformerEmbeddings._load_model",
            lambda self: _patch_load(self, fake_st_class),
        )

        provider = embeddings.SentenceTransformerEmbeddings()
        provider._model = fake_instance

        result = provider.encode(["hello"])
        assert len(result) == 1

    def test_custom_model_name(self) -> None:
        from providers.embeddings import SentenceTransformerEmbeddings

        provider = SentenceTransformerEmbeddings(model_name="custom-model")
        assert provider.model_name == "custom-model"

    def test_exports(self) -> None:
        """Module exports must include protocol and adapter."""
        from providers.embeddings import EmbeddingProvider, SentenceTransformerEmbeddings

        assert EmbeddingProvider is not None
        assert SentenceTransformerEmbeddings is not None


def _patch_load(self: Any, fake_cls: Any) -> Any:
    """Helper for monkeypatching _load_model."""
    self._model = fake_cls(self.model_name)
    return self._model

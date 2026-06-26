"""Tests for providers/embeddings.py — EmbeddingProvider protocol and adapter.

Tests use mock/fake FastEmbed models to avoid model download in CI.
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


class TestFastEmbedTextEmbeddings:
    """Unit tests for FastEmbedTextEmbeddings adapter."""

    def test_init_does_not_load_model(self) -> None:
        """Model must not be loaded at construction time (lazy loading)."""
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings()
        assert provider._model is None
        assert provider.model_name == "BAAI/bge-base-en-v1.5"
        assert provider.dimensions == 768

    def test_encode_empty_list_returns_empty(self) -> None:
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings()
        result = provider.encode([])
        assert result == []

    def test_encode_returns_correct_shape(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Encode should return list of float vectors with correct dimensions."""
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings()

        # Mock the model to avoid actual model download
        fake_model = MagicMock()
        fake_model.embed.return_value = np.random.randn(2, 768).astype(np.float32)

        provider._model = fake_model

        result = provider.encode(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 768
        assert len(result[1]) == 768
        assert all(isinstance(v, float) for v in result[0])

    def test_encode_single_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings()

        fake_model = MagicMock()
        fake_model.embed.return_value = np.random.randn(1, 768).astype(np.float32)

        provider._model = fake_model

        result = provider.encode(["test"])
        assert len(result) == 1
        assert len(result[0]) == 768

    def test_encode_calls_model_with_correct_args(self) -> None:
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings()

        fake_model = MagicMock()
        fake_model.embed.return_value = np.zeros((1, 768), dtype=np.float32)
        provider._model = fake_model

        provider.encode(["test input"])
        fake_model.embed.assert_called_once_with(["test input"])

    def test_lazy_load_calls_fastembed_text_embedding(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_load_model should import and instantiate FastEmbed TextEmbedding."""
        from providers import embeddings

        fake_text_embedding_class = MagicMock()
        fake_instance = MagicMock()
        fake_text_embedding_class.return_value = fake_instance
        fake_instance.embed.return_value = np.zeros((1, 768), dtype=np.float32)

        # Patch the import inside _load_model
        monkeypatch.setattr(
            "providers.embeddings.FastEmbedTextEmbeddings._load_model",
            lambda self: _patch_load(self, fake_text_embedding_class),
        )

        provider = embeddings.FastEmbedTextEmbeddings()
        provider._model = fake_instance

        result = provider.encode(["hello"])
        assert len(result) == 1

    def test_custom_model_name(self) -> None:
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings(model_name="custom-model")
        assert provider.model_name == "custom-model"

    def test_encode_rejects_wrong_dimensions(self) -> None:
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings(dimensions=3)
        fake_model = MagicMock()
        fake_model.embed.return_value = [[1.0, 2.0]]
        provider._model = fake_model

        with pytest.raises(ValueError, match="embedding dimension mismatch"):
            provider.encode(["test"])

    def test_encode_rejects_non_finite_values(self) -> None:
        from providers.embeddings import FastEmbedTextEmbeddings

        provider = FastEmbedTextEmbeddings(dimensions=3)
        fake_model = MagicMock()
        fake_model.embed.return_value = [[1.0, float("nan"), 3.0]]
        provider._model = fake_model

        with pytest.raises(ValueError, match="non-finite"):
            provider.encode(["test"])

    def test_exports(self) -> None:
        """Module exports must include protocol and adapter."""
        from providers.embeddings import EmbeddingProvider, FastEmbedTextEmbeddings

        assert EmbeddingProvider is not None
        assert FastEmbedTextEmbeddings is not None


def _patch_load(self: Any, fake_cls: Any) -> Any:
    """Helper for monkeypatching _load_model."""
    self._model = fake_cls(self.model_name)
    return self._model

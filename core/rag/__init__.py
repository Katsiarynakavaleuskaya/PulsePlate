"""RAG (Retrieval-Augmented Generation) module per RAG_CONTRACT.md."""

from core.rag import simple_rag
from core.rag.contracts import RAGChunk, RAGContext
from core.rag.rag_constants import (
    MAX_CHUNK_SIZE_CHARS,
    MAX_CHUNKS_PER_HOP,
    MAX_RAG_HOPS,
    MAX_SOURCES_IN_RESPONSE,
    MIN_CHUNK_SCORE,
    RAG_PIPELINE_TIMEOUT_SEC,
)

__all__ = [
    "RAGChunk",
    "RAGContext",
    "MAX_CHUNK_SIZE_CHARS",
    "MAX_CHUNKS_PER_HOP",
    "MAX_RAG_HOPS",
    "MAX_SOURCES_IN_RESPONSE",
    "MIN_CHUNK_SCORE",
    "RAG_PIPELINE_TIMEOUT_SEC",
    "simple_rag",
]

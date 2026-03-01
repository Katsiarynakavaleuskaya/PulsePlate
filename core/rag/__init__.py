"""RAG (Retrieval-Augmented Generation) module per RAG_CONTRACT.md."""

from core.rag import simple_rag
from core.rag.contracts import (
    AGENT_CORPUS_MAP,
    CorpusNotIndexedError,
    RAGChunk,
    RAGContext,
)
from core.rag.rag_constants import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_NAME,
    MAX_CHUNK_SIZE_CHARS,
    MAX_CHUNKS_PER_HOP,
    MAX_RAG_HOPS,
    MAX_SOURCES_IN_RESPONSE,
    MIN_CHUNK_SCORE,
    MIN_VECTOR_SCORE,
    RAG_PIPELINE_TIMEOUT_SEC,
)

__all__ = [
    "AGENT_CORPUS_MAP",
    "CorpusNotIndexedError",
    "RAGChunk",
    "RAGContext",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_MODEL_NAME",
    "MAX_CHUNK_SIZE_CHARS",
    "MAX_CHUNKS_PER_HOP",
    "MAX_RAG_HOPS",
    "MAX_SOURCES_IN_RESPONSE",
    "MIN_CHUNK_SCORE",
    "MIN_VECTOR_SCORE",
    "RAG_PIPELINE_TIMEOUT_SEC",
    "simple_rag",
]

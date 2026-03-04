"""RAG (Retrieval-Augmented Generation) module per RAG_CONTRACT.md."""

from core.rag import simple_rag
from core.rag.contracts import (
    AGENT_CORPUS_MAP,
    CorpusNotIndexedError,
    RAGChunk,
    RAGContext,
)
from core.rag.orchestration import (
    RAGOrchestrationResult,
    retrieve_and_validate_rag,
)
from core.rag.philosophy_pipeline import (
    PipelineResult,
    run_pipeline,
)
from core.rag.rag_constants import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL_NAME,
    MAX_CHUNK_SIZE_CHARS,
    MAX_CHUNKS_PER_HOP,
    MAX_RAG_HOPS,
    MAX_REFINEMENT_PASSES,
    MAX_SOURCES_IN_RESPONSE,
    MAX_VERIFICATION_QUERIES,
    MIN_CHUNK_SCORE,
    MIN_CONFIDENCE_GAIN_PER_HOP,
    MIN_VECTOR_SCORE,
    RAG_PIPELINE_TIMEOUT_SEC,
)

__all__ = [
    "AGENT_CORPUS_MAP",
    "CorpusNotIndexedError",
    "RAGChunk",
    "RAGContext",
    "RAGOrchestrationResult",
    "retrieve_and_validate_rag",
    "PipelineResult",
    "run_pipeline",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_MODEL_NAME",
    "MAX_CHUNK_SIZE_CHARS",
    "MAX_CHUNKS_PER_HOP",
    "MAX_RAG_HOPS",
    "MAX_REFINEMENT_PASSES",
    "MAX_SOURCES_IN_RESPONSE",
    "MAX_VERIFICATION_QUERIES",
    "MIN_CHUNK_SCORE",
    "MIN_CONFIDENCE_GAIN_PER_HOP",
    "MIN_VECTOR_SCORE",
    "RAG_PIPELINE_TIMEOUT_SEC",
    "simple_rag",
]

"""
RAG budget and pipeline constants per docs/contracts/RAG_CONTRACT.md §4.

Used by retrieval pipeline, response shaping (max sources), and timeouts.
"""

MAX_RAG_HOPS: int = 3
MAX_CHUNKS_PER_HOP: int = 5
MAX_SOURCES_IN_RESPONSE: int = 5
RAG_PIPELINE_TIMEOUT_SEC: int = 10
MIN_CHUNK_SCORE: float = 0.1
MAX_CHUNK_SIZE_CHARS: int = 800
MAX_REFINEMENT_PASSES: int = 2
MAX_VERIFICATION_QUERIES: int = 2
MIN_CONFIDENCE_GAIN_PER_HOP: float = 0.02

# Vector retrieval constants (P2)
EMBEDDING_MODEL_NAME: str = "all-mpnet-base-v2"
EMBEDDING_DIMENSIONS: int = 768
MIN_VECTOR_SCORE: float = 0.3  # cosine similarity threshold (higher bar than Jaccard's 0.1)

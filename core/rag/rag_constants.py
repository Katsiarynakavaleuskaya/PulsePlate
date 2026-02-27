"""
RAG budget and pipeline constants (per docs/contracts/RAG_CONTRACT.md §4).

RU: Константы бюджета рекурсии и латентности для RAG-пайплайна.
"""

MAX_RAG_HOPS: int = 3
MAX_CHUNKS_PER_HOP: int = 5
MAX_SOURCES_IN_RESPONSE: int = 5
RAG_PIPELINE_TIMEOUT_SEC: int = 10
MIN_CHUNK_SCORE: float = 0.1
MAX_CHUNK_SIZE_CHARS: int = 800

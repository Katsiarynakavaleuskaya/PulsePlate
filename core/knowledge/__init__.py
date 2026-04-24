"""Knowledge bounded-context exports.

RU: Экспорт внутреннего bounded-context для knowledge promotion.
EN: Internal bounded-context exports for knowledge promotion.
"""

from core.knowledge.contracts import (
    KnowledgeEvidenceRef,
    KnowledgeFactCandidate,
    KnowledgeRecord,
)
from core.knowledge.policy import KnowledgePolicy
from core.knowledge.promotion import build_knowledge_promotion_candidates
from core.knowledge.store import KnowledgeStore, NoOpKnowledgeStore

__all__ = [
    "KnowledgeEvidenceRef",
    "KnowledgeFactCandidate",
    "KnowledgePolicy",
    "KnowledgeRecord",
    "KnowledgeStore",
    "NoOpKnowledgeStore",
    "build_knowledge_promotion_candidates",
]

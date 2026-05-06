"""Evidence asset registry contracts.

RU: Канонические контракты evidence asset registry.
EN: Canonical evidence asset registry contracts.
"""

from core.evidence.assets import (
    AssetType,
    EvidenceAssetRef,
    Rail,
    create_evidence_asset_ref,
)
from core.evidence.fingerprints import (
    build_asset_id,
    build_idempotency_key,
    fingerprint_payload,
)
from core.evidence.events import (
    EvidenceEvalEvent,
    EvalEventProducer,
    EvalEventRail,
    EvalEventType,
    ValidationStatus,
    create_eval_event,
)
from core.evidence.promotion_ledger import (
    PromotionDecision,
    PromotionLedgerEntry,
    create_promotion_ledger_entry,
)
from core.evidence.replay import (
    PromotionDiff,
    PromotionReplaySummary,
    dry_run_replay,
)

__all__ = [
    "AssetType",
    "EvidenceAssetRef",
    "EvidenceEvalEvent",
    "EvalEventProducer",
    "EvalEventRail",
    "EvalEventType",
    "PromotionDecision",
    "PromotionDiff",
    "PromotionLedgerEntry",
    "PromotionReplaySummary",
    "Rail",
    "ValidationStatus",
    "build_asset_id",
    "build_idempotency_key",
    "create_evidence_asset_ref",
    "create_eval_event",
    "create_promotion_ledger_entry",
    "dry_run_replay",
    "fingerprint_payload",
]

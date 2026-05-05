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

__all__ = [
    "AssetType",
    "EvidenceAssetRef",
    "EvidenceEvalEvent",
    "EvalEventProducer",
    "EvalEventRail",
    "EvalEventType",
    "Rail",
    "ValidationStatus",
    "build_asset_id",
    "build_idempotency_key",
    "create_evidence_asset_ref",
    "create_eval_event",
    "fingerprint_payload",
]

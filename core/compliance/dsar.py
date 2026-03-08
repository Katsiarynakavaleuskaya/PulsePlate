"""Internal DSAR and deletion/export mapping for PulsePlate artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DSARArtifact:
    """Internal representation of a user-data artifact."""

    artifact_id: str
    label: str
    storage: str
    subject_binding: str
    export_supported: bool
    deletion_supported: bool
    deletion_mode: str
    retention_owner: str
    notes: str


_DSAR_ARTIFACTS: tuple[DSARArtifact, ...] = (
    DSARArtifact(
        artifact_id="account_user_record",
        label="Account and user row",
        storage="SQL table `users`",
        subject_binding="direct user_id",
        export_supported=True,
        deletion_supported=True,
        deletion_mode="direct row deletion",
        retention_owner="account lifecycle",
        notes="Primary account record; public DSAR endpoint still deferred until auth contract is formalized.",
    ),
    DSARArtifact(
        artifact_id="rag_feedback",
        label="RAG feedback entries",
        storage="SQL table `rag_feedback`",
        subject_binding="direct user_id",
        export_supported=True,
        deletion_supported=True,
        deletion_mode="direct row deletion",
        retention_owner="product QA and privacy review",
        notes="Query/preview/response fields are minimized before persistence.",
    ),
    DSARArtifact(
        artifact_id="user_knowledge",
        label="User knowledge corpus",
        storage="SQL table `user_knowledge`",
        subject_binding="direct user_id",
        export_supported=True,
        deletion_supported=True,
        deletion_mode="direct row deletion",
        retention_owner="VIP personalization controls",
        notes="Embedding-backed personalization artifacts remain internal-only.",
    ),
    DSARArtifact(
        artifact_id="pseudonymous_request_fingerprint",
        label="Pseudonymous request fingerprints",
        storage="logs and rate-limit fingerprints",
        subject_binding="indirect by network identifier",
        export_supported=False,
        deletion_supported=False,
        deletion_mode="retention-only cleanup",
        retention_owner="core.log_retention",
        notes="Not directly attributable to an authenticated user without extra evidence.",
    ),
    DSARArtifact(
        artifact_id="vip_llm_monthly_usage",
        label="LLM quota usage fingerprints",
        storage="SQL table `vip_llm_monthly_usage`",
        subject_binding="tier-scoped key fingerprint",
        export_supported=False,
        deletion_supported=False,
        deletion_mode="retention or support-led remediation",
        retention_owner="billing/security controls",
        notes="Bound to key fingerprint rather than a canonical user account id.",
    ),
    DSARArtifact(
        artifact_id="agent_control_audit",
        label="Signed audit envelopes",
        storage="JSONL file `artifacts/orchestration/agent_control_audit.jsonl`",
        subject_binding="event metadata only",
        export_supported=False,
        deletion_supported=False,
        deletion_mode="retention-only cleanup",
        retention_owner="security audit policy",
        notes="Audit logs store hashed/minimized metadata and are not treated as a public self-service artifact.",
    ),
)


def get_dsar_artifact_map() -> list[dict[str, object]]:
    """Return the canonical internal DSAR data map."""

    return [asdict(item) for item in _DSAR_ARTIFACTS]


def summarize_dsar_support() -> dict[str, int]:
    """Return a compact support summary for internal dashboards and `/privacy`."""

    export_supported = sum(1 for item in _DSAR_ARTIFACTS if item.export_supported)
    deletion_supported = sum(1 for item in _DSAR_ARTIFACTS if item.deletion_supported)
    return {
        "artifact_count": len(_DSAR_ARTIFACTS),
        "export_supported_count": export_supported,
        "deletion_supported_count": deletion_supported,
    }


def build_dsar_rights_summary() -> list[dict[str, object]]:
    """Return user-rights disclosures tied to the artifact map."""

    return [
        {
            "right": "access",
            "status": "available_via_support_process",
            "notes": "Internal artifact map exists; public self-service export endpoint is not yet promised.",
        },
        {
            "right": "deletion",
            "status": "available_for_direct-user artifacts",
            "notes": "Direct-user SQL artifacts can be deleted; pseudonymous and audit artifacts follow retention or support-led handling.",
        },
        {
            "right": "rectification",
            "status": "case_by_case",
            "notes": "Derived artifacts are corrected by replacing or deleting the underlying record, not by in-place free-form edits.",
        },
        {
            "right": "object_to_automated_analysis",
            "status": "surface_specific",
            "notes": "Users can stop using AI insight surfaces and request deletion of direct-user feedback/personalization artifacts.",
        },
    ]

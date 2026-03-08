"""Privacy policy control-plane data for runtime and legal docs."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from core.compliance.dsar import build_dsar_rights_summary, summarize_dsar_support
from core.compliance.transparency import get_blocked_regulated_lane, get_transparency_registry
from core.log_retention import get_retention_manager

PRIVACY_POLICY_VERSION = "2026-03-08.eu-first.v1"
PRIVACY_POLICY_LAST_UPDATED = "2026-03-08"


@dataclass(frozen=True)
class ProviderDisclosure:
    """Provider disclosure for privacy notices."""

    provider_id: str
    name: str
    category: str
    role: str
    data_scope: str
    retention: str
    activation: str


@dataclass(frozen=True)
class ProcessingCategory:
    """Canonical processing category disclosure."""

    category_id: str
    title: str
    endpoints: tuple[str, ...]
    purpose: str
    sensitivity: str
    third_party_exposure: str
    retention: str
    deletion_path: str


_PROVIDER_INVENTORY: tuple[ProviderDisclosure, ...] = (
    ProviderDisclosure(
        provider_id="local_runtime",
        name="PulsePlate local/runtime processing",
        category="first_party",
        role="Primary application runtime",
        data_scope="BMI/bodyfat/nutrition calculations, routing, and local formula execution",
        retention="Depends on the artifact type; see /privacy and docs/compliance for details",
        activation="Always active",
    ),
    ProviderDisclosure(
        provider_id="xai_grok",
        name="xAI Grok provider family",
        category="external_processor",
        role="Configured LLM provider for selected AI insight surfaces",
        data_scope="User-submitted text and derived prompts for configured insight endpoints",
        retention="Provider-specific terms apply when enabled",
        activation="Conditional, configuration-based",
    ),
    ProviderDisclosure(
        provider_id="openai_compatible",
        name="OpenAI-compatible provider family",
        category="external_processor",
        role="Configured external LLM endpoint when selected by deployment",
        data_scope="User-submitted text and derived prompts for configured insight endpoints",
        retention="Provider-specific terms apply when enabled",
        activation="Conditional, configuration-based",
    ),
    ProviderDisclosure(
        provider_id="anthropic_compatible",
        name="Anthropic-compatible provider family",
        category="external_processor",
        role="Configured external LLM endpoint when selected by deployment",
        data_scope="User-submitted text and derived prompts for configured insight endpoints",
        retention="Provider-specific terms apply when enabled",
        activation="Conditional, configuration-based",
    ),
    ProviderDisclosure(
        provider_id="ollama_self_hosted",
        name="Ollama or compatible self-hosted provider",
        category="self_hosted_processor",
        role="Self-hosted/local LLM processing",
        data_scope="User-submitted text and derived prompts for configured insight endpoints",
        retention="Deployment-controlled; not assumed to be zero-retention by default",
        activation="Conditional, configuration-based",
    ),
    ProviderDisclosure(
        provider_id="pico",
        name="Pico provider family",
        category="external_processor",
        role="Configured external provider for selected AI insight surfaces",
        data_scope="User-submitted text and derived prompts for configured insight endpoints",
        retention="Provider-specific terms apply when enabled",
        activation="Conditional, configuration-based",
    ),
)

_PROCESSING_CATEGORIES: tuple[ProcessingCategory, ...] = (
    ProcessingCategory(
        category_id="pseudonymous_security_identifiers",
        title="Pseudonymous security and rate-limit identifiers",
        endpoints=("/health", "/metrics", "/api/v1/insight", "/api/v1/pro/cbt/insight"),
        purpose="Abuse prevention, rate limiting, request correlation, and operational security",
        sensitivity="pseudonymous",
        third_party_exposure="No third-party disclosure by default",
        retention="Managed by configured retention windows under core.log_retention",
        deletion_path="Automatic retention cleanup; not directly user-addressable without extra evidence",
    ),
    ProcessingCategory(
        category_id="wellness_profile_inputs",
        title="Wellness profile inputs and formula-driven outputs",
        endpoints=(
            "/bmi",
            "/api/v1/bmi",
            "/api/v1/bodyfat",
            "/api/v1/pro/nutrition/daily",
            "/api/v1/pro/meal/weekly",
            "/api/v1/premium/plate",
        ),
        purpose="Provide deterministic wellness calculations and explanatory guidance",
        sensitivity="health-adjacent",
        third_party_exposure="Processed in application runtime; no automatic third-party sharing",
        retention="Primarily request-scoped unless persisted by a separate feature path",
        deletion_path="Delete or correct any directly persisted derivative artifact via support-led process",
    ),
    ProcessingCategory(
        category_id="ai_generated_wellness_analysis",
        title="AI-generated wellness analysis",
        endpoints=("/insight", "/api/v1/insight", "/api/v1/pro/cbt/insight"),
        purpose="Generate wellness-oriented, automated AI responses and explanations",
        sensitivity="derived sensitive",
        third_party_exposure="May involve configured provider families or self-hosted processors",
        retention="Provider- and deployment-specific; local audit metadata is minimized and signed",
        deletion_path="Direct-user feedback/personalization artifacts can be deleted; provider-side artifacts follow provider policy",
    ),
    ProcessingCategory(
        category_id="feedback_quality_improvement",
        title="Feedback and quality-improvement artifacts",
        endpoints=("/api/v1/feedback/rag",),
        purpose="Collect minimized QA feedback to improve retrieval and response quality",
        sensitivity="derived sensitive",
        third_party_exposure="No automatic third-party disclosure by default",
        retention="Application-controlled until deletion or retention review",
        deletion_path="Direct row deletion for user-bound artifacts",
    ),
    ProcessingCategory(
        category_id="signed_audit_envelopes",
        title="Signed policy and audit envelopes",
        endpoints=("/api/v1/pro/cbt/insight",),
        purpose="Document privileged AI actions with a tamper-evident audit trail",
        sensitivity="minimized security metadata",
        third_party_exposure="No automatic third-party disclosure by default",
        retention="Application-controlled JSONL audit trail with minimized metadata",
        deletion_path="Retention-managed; not exposed as a public self-service artifact",
    ),
)


def get_provider_inventory() -> list[dict[str, object]]:
    """Return provider inventory as serializable dictionaries."""

    return [asdict(item) for item in _PROVIDER_INVENTORY]


def get_processing_categories() -> list[dict[str, object]]:
    """Return processing category disclosures as serializable dictionaries."""

    return [asdict(item) for item in _PROCESSING_CATEGORIES]


def build_privacy_endpoint_payload() -> dict[str, object]:
    """Build the additive `/privacy` payload from the canonical control plane."""

    retention_manager = get_retention_manager()
    pseudonymous_retention_days = getattr(retention_manager, "pseudonymous_retention_days", 0)
    transparency_registry = get_transparency_registry()

    old_payload: dict[str, object] = {
        "privacy_policy": (
            "PulsePlate operates as a consumer wellness product. It processes wellness-profile inputs, "
            "pseudonymous request identifiers, minimized feedback artifacts, and selected AI metadata. "
            "Some surfaces remain request-scoped, while other artifacts are persisted in minimized form "
            "for security, quality, and user-account operations."
        ),
        "data_collection": {
            "pseudonymous_identifiers": {
                "type": "Client fingerprints (hashed and truncated IP addresses)",
                "purpose": "Security monitoring, request correlation, and abuse prevention",
                "retention_period_days": pseudonymous_retention_days,
                "classification": "Pseudonymous data (GDPR Article 4(5))",
                "deletion": "Automatic deletion after retention period expires",
            },
            "feedback_and_quality_artifacts": {
                "type": "Minimized user-bound feedback and QA artifacts",
                "purpose": "Quality improvement for retrieval and AI-generated wellness responses",
                "retention_period_days": None,
                "classification": "Derived sensitive wellness data",
                "deletion": "Direct-user SQL artifacts can be deleted via internal DSAR workflow",
            },
        },
        "llm_processing": {
            "endpoints": ["/insight", "/api/v1/insight", "/api/v1/pro/cbt/insight"],
            "purpose": "Generate wellness-oriented insights using configured AI providers or self-hosted runtimes",
            "data_transmitted": "User-provided text queries and derived prompts for enabled AI surfaces",
            "recipients": "Configured provider families or self-hosted processors listed in provider inventory",
            "retention_by_provider": "Varies by provider and deployment configuration",
            "legal_basis": "Product operation, legitimate interest, and surface-specific user action",
            "opt_out": "Do not use AI insight surfaces if you do not want your text processed by configured providers",
            "feature_flag": "AI processing can be reduced or disabled via deployment configuration",
            "note": "Avoid submitting personally identifiable information, clinical records, or emergency/crisis content",
        },
        "data_retention": (
            f"Pseudonymous request identifiers are retained for {pseudonymous_retention_days} days. "
            "Direct-user SQL artifacts follow feature-specific retention and deletion rules. "
            "Configured provider-side retention follows the provider or self-hosted deployment policy."
        ),
        "data_classification": {
            "pseudonymous_logs": "Logs containing client fingerprints are classified as PSEUDONYMOUS data",
            "access_control": "Access to logs and direct-user artifacts is restricted and audited",
            "salt_rotation": "Fingerprint salt is stored as a secret and can be rotated per documented procedures",
        },
        "contact": "For privacy concerns, please contact the application administrator.",
        "gdpr_compliance": (
            "PulsePlate maintains a wellness-only posture, minimized audit metadata, and direct-user deletion pathways "
            "for eligible artifacts. Additional regulated lanes remain blocked until a separate compliance track is approved."
        ),
    }

    old_payload.update(
        {
            "policy_version": PRIVACY_POLICY_VERSION,
            "last_updated": PRIVACY_POLICY_LAST_UPDATED,
            "processing_categories": get_processing_categories(),
            "providers": get_provider_inventory(),
            "rights": build_dsar_rights_summary(),
            "automated_analysis": list(transparency_registry.values()),
            "retention_summary": {
                "pseudonymous_retention_days": pseudonymous_retention_days,
                "artifact_support": summarize_dsar_support(),
                "regulated_lane": get_blocked_regulated_lane(),
            },
        }
    )
    return old_payload

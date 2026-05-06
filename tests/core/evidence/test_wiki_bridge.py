from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, cast

import pytest

from core.evidence.admission import AdmissionPolicy, decide_allow_serve
from core.evidence.wiki_bridge import (
    AdvisoryWikiArtifactRef,
    WikiEvidenceBridgePolicy,
    create_advisory_wiki_artifact_ref,
    wiki_artifact_to_admission_input,
    wiki_artifact_to_evidence_asset_ref,
)

_MODULE_PATH = Path("core/evidence/wiki_bridge.py")
_HASH = "a" * 64
_PRODUCED_AT = "2026-05-06T12:00:00Z"
_NOW = "2026-05-06T12:01:00Z"


def _artifact(**overrides: object) -> AdvisoryWikiArtifactRef:
    values: dict[str, object] = {
        "corpus": "project_internal",
        "slug": "local-wiki-support-plane",
        "source_rel_path": "docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md",
        "page_path": "artifacts/orchestration/wiki/project_internal/pages/local-wiki-support-plane.md",
        "promoted_path": "artifacts/orchestration/wiki/project_internal/promoted/local-wiki-support-plane.md",
        "content_hash": _HASH,
        "policy_version": "policy-e5",
        "promoted": True,
        "upstream_ids": ["upstream-b", "upstream-a"],
        "metadata": {"advisory_only": True, "note": "operator memory"},
    }
    values.update(overrides)
    return create_advisory_wiki_artifact_ref(
        corpus=cast(str, values["corpus"]),
        slug=cast(str, values["slug"]),
        source_rel_path=cast(str, values["source_rel_path"]),
        page_path=cast(str, values["page_path"]),
        promoted_path=cast(str | None, values["promoted_path"]),
        content_hash=cast(str, values["content_hash"]),
        policy_version=cast(str, values["policy_version"]),
        promoted=cast(bool, values["promoted"]),
        upstream_ids=cast(list[str], values["upstream_ids"]),
        metadata=cast(dict[str, Any], values["metadata"]),
        policy=cast(WikiEvidenceBridgePolicy | None, values.get("policy")),
    )


def test_creates_valid_artifact_ref_from_wiki_page_metadata() -> None:
    artifact = _artifact()

    assert artifact.advisory_only is True
    assert artifact.promoted is True
    assert artifact.content_hash == f"sha256:{_HASH}"
    assert artifact.source_rel_path.startswith("docs/")
    assert artifact.upstream_ids == ("upstream-a", "upstream-b")
    assert artifact.artifact_id.startswith("advisory-wiki:")
    assert artifact.idempotency_key.startswith("idem:advisory-wiki:")


@pytest.mark.parametrize("field", ["corpus", "slug", "source_rel_path", "content_hash"])
def test_rejects_blank_required_identity_fields(field: str) -> None:
    with pytest.raises(ValueError):
        _artifact(**{field: " "})


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../x",
        "/tmp/x",
        "~/x",
        "C:/x",
        "C:relative/path.md",
        "file://tmp/x.md",
        "https://example.com/x.md",
        ".",
        "./",
        "./.",
    ],
)
@pytest.mark.parametrize("field", ["source_rel_path", "page_path", "promoted_path"])
def test_rejects_unsafe_paths(field: str, unsafe_path: str) -> None:
    with pytest.raises(ValueError):
        _artifact(**{field: unsafe_path})


def test_allows_docs_source_path_only_as_provenance() -> None:
    artifact = _artifact(source_rel_path="docs/orchestration/example.md")

    assert artifact.source_rel_path == "docs/orchestration/example.md"


@pytest.mark.parametrize("field", ["page_path", "promoted_path"])
def test_rejects_docs_output_paths_as_canonical_authority(field: str) -> None:
    with pytest.raises(ValueError, match="canonical docs authority"):
        _artifact(**{field: "docs/orchestration/wiki-output.md"})


@pytest.mark.parametrize(
    "metadata",
    [
        {"raw_prompt": "explain the repo"},
        {"response_text": "full answer"},
        {"query": "private wiki query"},
        {"user_health": {"weight": 123}},
        {"sec" + "ret": "redacted credential payload"},
        {"note": "prompt: raw body"},
    ],
)
def test_rejects_raw_prompt_response_query_user_health_secret_metadata(
    metadata: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        _artifact(metadata=metadata)


@pytest.mark.parametrize(
    "metadata",
    [
        {"rail": "runtime"},
        {"canonical": True},
        {"source_of_truth": "runtime"},
        {"product_truth": "authoritative"},
        {"advisory_only": False},
        {"runtime": 1},
        {"canonical": 1.0},
        {"source_of_truth": [0, 1]},
    ],
)
def test_rejects_runtime_or_canonical_authority_claims(metadata: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _artifact(metadata=metadata)


def test_maps_valid_wiki_artifact_to_advisory_evidence_asset() -> None:
    asset = wiki_artifact_to_evidence_asset_ref(_artifact())

    assert asset.rail == "advisory"
    assert asset.asset_type == "knowledge_candidate"
    assert asset.policy_version == "policy-e5"


def test_runtime_rail_mapping_is_not_available() -> None:
    asset = wiki_artifact_to_evidence_asset_ref(_artifact(), asset_type="context_bundle")

    assert asset.rail == "advisory"
    with pytest.raises(ValueError):
        _artifact(metadata={"rail": "runtime"})


def test_rejects_runtime_evidence_upstreams_before_admission_mapping() -> None:
    runtime_upstream = "evidence:knowledge_candidate:runtime:v1:aaaaaaaaaaaaaaaaaaaaaaaa"

    with pytest.raises(ValueError, match="cross-rail"):
        _artifact(upstream_ids=[runtime_upstream])


def test_advisory_only_flag_survives_asset_and_admission_adapter() -> None:
    artifact = _artifact()
    asset = wiki_artifact_to_evidence_asset_ref(artifact)
    admission_input = wiki_artifact_to_admission_input(
        artifact,
        produced_at=_PRODUCED_AT,
        coverage_rate=1.0,
        verification_rate=1.0,
        fallback_rate=0.0,
        metadata={"review_state": "promoted"},
    )

    assert artifact.advisory_only is True
    assert asset.rail == "advisory"
    assert admission_input.metadata["advisory_only"] is True
    assert admission_input.metadata["serve_scope"] == "advisory_review_only"


def test_idempotency_key_artifact_id_and_serialization_are_deterministic() -> None:
    first = _artifact(upstream_ids=["b", "a"], content_hash=f"sha256:{_HASH}")
    second = _artifact(upstream_ids=["a", "b"], content_hash=_HASH.upper())

    assert first.artifact_id == second.artifact_id
    assert first.idempotency_key == second.idempotency_key
    assert first.to_json() == second.to_json()


def test_metadata_and_upstream_ids_are_defensively_copied() -> None:
    metadata: dict[str, Any] = {"advisory_only": True, "labels": ["one"]}
    upstream_ids = ["z", "a"]
    artifact = _artifact(metadata=metadata, upstream_ids=upstream_ids)

    cast(list[str], metadata["labels"]).append("two")
    upstream_ids.append("later")
    returned_metadata = artifact.metadata
    cast(list[str], returned_metadata["labels"]).append("three")

    assert artifact.metadata == {"advisory_only": True, "labels": ["one"]}
    assert artifact.upstream_ids == ("a", "z")


@pytest.mark.parametrize(
    "payload",
    [
        b"redacted credential payload",
        bytearray(b"redacted credential payload"),
        memoryview(b"redacted"),
    ],
)
def test_rejects_byte_like_metadata_payloads(payload: object) -> None:
    with pytest.raises(ValueError, match="JSON-compatible"):
        _artifact(metadata={"advisory_only": True, "note": payload})

    with pytest.raises(ValueError, match="JSON-compatible"):
        wiki_artifact_to_admission_input(
            _artifact(),
            produced_at=_PRODUCED_AT,
            coverage_rate=1.0,
            verification_rate=1.0,
            fallback_rate=0.0,
            metadata=cast(dict[str, Any], {"review_state": payload}),
        )


def test_admission_adapter_does_not_imply_product_runtime_serve() -> None:
    admission_input = wiki_artifact_to_admission_input(
        _artifact(),
        produced_at=_PRODUCED_AT,
        coverage_rate=1.0,
        verification_rate=1.0,
        fallback_rate=0.0,
    )
    decision = decide_allow_serve(
        admission_input=admission_input,
        policy=AdmissionPolicy(policy_version="policy-e5"),
        now=_NOW,
    )

    assert decision.allowed is True
    input_payload = cast(dict[str, Any], decision.metadata["input"])
    input_metadata = cast(dict[str, Any], input_payload["metadata"])
    assert input_metadata["advisory_only"] is True
    assert input_metadata["serve_scope"] == "advisory_review_only"


@pytest.mark.parametrize(
    "value", [".", "./", "./.", "docs/path.md", "core/evidence/wiki_bridge.py"]
)
def test_rejects_path_like_metadata_values(value: str) -> None:
    with pytest.raises(ValueError):
        _artifact(metadata={"advisory_only": True, "note": value})


def test_policy_blocks_unapproved_corpus_and_asset_type() -> None:
    policy = WikiEvidenceBridgePolicy(policy_version="policy-e5", allowed_corpora=("ops",))

    with pytest.raises(ValueError, match="corpus"):
        _artifact(policy=policy)

    artifact = _artifact()
    restricted = WikiEvidenceBridgePolicy(
        policy_version="policy-e5",
        allowed_corpora=("project_internal",),
        allowed_asset_types=("verification_bundle",),
    )
    with pytest.raises(ValueError, match="asset_type"):
        wiki_artifact_to_evidence_asset_ref(
            artifact, asset_type="knowledge_candidate", policy=restricted
        )


def test_admission_adapter_requires_explicit_allowed_status() -> None:
    artifact = _artifact()

    with pytest.raises(ValueError, match="not admitted"):
        wiki_artifact_to_admission_input(
            artifact,
            produced_at=_PRODUCED_AT,
            coverage_rate=1.0,
            verification_rate=1.0,
            fallback_rate=0.0,
            validation_status="degraded",
        )


def test_import_guard_blocks_runtime_compiler_cache_and_eval_imports() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_fragments = (
        "app",
        "db",
        "evals",
        "fastapi",
        "graphrag",
        "legacy_app",
        "llm",
        "local_support_plane",
        "providers",
        "redis",
        "scripts.orchestration",
        "semantic_cache",
        "session",
        "sqlalchemy",
        "wiki_ingest",
        "wiki_lint",
        "wiki_promote",
        "wiki_query",
    )
    violations = sorted(
        module
        for module in imported_modules
        if any(fragment in module.lower() for fragment in forbidden_fragments)
    )

    assert violations == []

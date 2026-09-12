"""Original native build identity and finite material admission regressions."""

from __future__ import annotations

import copy
import base64
import json
import hashlib
from pathlib import Path
import subprocess

import pytest

from scripts.ci import check_pgvector_attestations as verifier

REPO = "Katsiarynakavaleuskaya/PulsePlate"
WORKFLOW = REPO + "/.github/workflows/cd.yml"
REF = "refs/heads/main"
SHA = "5b384c91708f774c025b0b19edc1c8c83d11266b"
INVOCATION = "https://github.com/" + REPO + "/actions/runs/34700002576/attempts/1"


def packet() -> tuple[dict, dict]:
    manifest = json.loads(Path("deploy/postgres-pgvector/image-manifest.json").read_text())
    identity = {
        "repository": REPO,
        "source_sha": SHA,
        "source_ref": REF,
        "signer_workflow": WORKFLOW,
        "run_invocation_uri": INVOCATION,
    }
    # Observed gh verificationResult.signature.certificate shape, not an invented receipt.
    certificate = {
        "sourceRepositoryDigest": SHA,
        "sourceRepositoryRef": REF,
        "sourceRepositoryURI": "https://github.com/" + REPO,
        "buildSignerURI": "https://github.com/" + WORKFLOW + "@" + REF,
        "runInvocationURI": INVOCATION,
        "runnerEnvironment": "github-hosted",
    }
    provenance = {
        "buildDefinition": {
            "buildType": "https://actions.github.io/buildtypes/workflow/v1",
            "externalParameters": {
                "workflow": {
                    "path": ".github/workflows/cd.yml",
                    "ref": REF,
                    "repository": "https://github.com/" + REPO,
                }
            },
            "resolvedDependencies": [
                {"digest": {"gitCommit": SHA}, "uri": "git+https://github.com/" + REPO + "@" + REF}
            ],
        },
        "runDetails": {
            "builder": {"id": "https://github.com/" + WORKFLOW + "@" + REF},
            "metadata": {"invocationId": INVOCATION},
        },
    }
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "name": "image",
        "documentNamespace": "https://example/image",
        "creationInfo": {"created": "2026-09-12T00:00:00Z", "creators": ["Tool: trivy-0.74.0"]},
        "packages": [{"name": "postgresql", "versionInfo": "15.19"}],
        "relationships": [],
    }
    payloads = {}
    for kind, predicate in zip(
        verifier.TYPES,
        (
            provenance,
            verifier.materials_predicate(manifest, identity, verifier.spdx_hash(sbom)),
            sbom,
        ),
    ):
        payloads[kind] = [
            {
                "verificationResult": {
                    "signature": {"certificate": copy.deepcopy(certificate)},
                    "statement": {
                        "_type": "https://in-toto.io/Statement/v1",
                        "predicateType": kind,
                        "subject": [
                            {
                                "name": manifest["repository"],
                                "digest": {"sha256": manifest["platform_manifest_digest"][7:]},
                            }
                        ],
                        "predicate": copy.deepcopy(predicate),
                    },
                }
            }
        ]
    return manifest, payloads


def test_native_triple_reuse_retains_original_execution() -> None:
    manifest, payloads = packet()
    result = verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)
    assert result["passed"] is True
    assert result["original_build"]["source_sha"] == SHA
    assert result["original_build"]["run_invocation_uri"] == INVOCATION
    assert result["predicate_types"] == list(verifier.TYPES)


@pytest.mark.parametrize(
    "field,value",
    [
        ("sourceRepositoryDigest", "a" * 40),
        ("sourceRepositoryRef", "refs/tags/v1.0"),
        ("sourceRepositoryURI", "https://github.com/other/repo"),
        ("runInvocationURI", INVOCATION[:-1] + "2"),
        ("buildSignerURI", "https://github.com/other/repo/.github/workflows/cd.yml@" + REF),
        ("runnerEnvironment", "self-hosted"),
    ],
)
def test_cross_predicate_certificate_mismatch_fails(field: str, value: str) -> None:
    manifest, payloads = packet()
    payloads[verifier.MATERIALS_TYPE][0]["verificationResult"]["signature"]["certificate"][
        field
    ] = value
    with pytest.raises(ValueError):
        verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)


@pytest.mark.parametrize("kind", verifier.TYPES)
def test_missing_duplicate_and_subject_mismatch_rejected(kind: str) -> None:
    manifest, payloads = packet()
    broken = copy.deepcopy(payloads)
    broken[kind] = []
    with pytest.raises(ValueError, match="HOLD"):
        verifier.validate_triple(broken, manifest, REPO, WORKFLOW, REF)
    broken = copy.deepcopy(payloads)
    broken[kind].append(copy.deepcopy(broken[kind][0]))
    assert verifier.validate_triple(broken, manifest, REPO, WORKFLOW, REF)["passed"]
    broken[kind][1]["verificationResult"]["statement"]["predicate"]["conflict"] = True
    with pytest.raises(ValueError, match="Conflicting predicate"):
        verifier.validate_triple(broken, manifest, REPO, WORKFLOW, REF)
    payloads[kind][0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = (
        "b" * 64
    )
    with pytest.raises(ValueError, match="subject"):
        verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)


def test_material_recipe_and_native_statement_are_substantively_checked() -> None:
    manifest, payloads = packet()
    payloads[verifier.MATERIALS_TYPE][0]["verificationResult"]["statement"]["predicate"]["recipe"][
        "make_jobs"
    ] = "2"
    with pytest.raises(ValueError, match="recipe"):
        verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)
    manifest, payloads = packet()
    payloads[verifier.TYPES[0]][0]["verificationResult"]["statement"]["predicate"]["runDetails"][
        "metadata"
    ]["invocationId"] = (INVOCATION[:-1] + "2")
    with pytest.raises(ValueError, match="invocation"):
        verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)


def test_entire_spdx_hash_rejects_every_predicate_content_mutation() -> None:
    manifest, payloads = packet()
    sbom = copy.deepcopy(
        payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"]
    )
    assert verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF, sbom=sbom)["passed"]
    for field in (
        "name",
        "documentNamespace",
        "packages",
        "relationships",
        "creationInfo",
        "unknown",
    ):
        broken = copy.deepcopy(sbom)
        broken[field] = [{"changed": True}]
        with pytest.raises(ValueError):
            verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF, sbom=broken)


def test_spdx_full_encoding_preserves_unknown_fields_arrays_unicode_and_types() -> None:
    original = {
        "spdxVersion": "SPDX-2.3",
        "packages": [{"name": "é", "annotations": [{"annotationDate": "one"}]}],
        "relationships": [{"spdxElementId": "A", "relatedSpdxElement": "B"}],
        "unknown": [True, 1, 1.0, None],
    }
    expected = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                original, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode("utf-8")
        ).hexdigest()
    )
    assert verifier.spdx_hash(original) == expected
    assert verifier.spdx_hash(dict(reversed(list(original.items())))) == expected
    for field in ("packages", "relationships", "unknown"):
        changed = copy.deepcopy(original)
        changed[field].append({"unknown-change": True})
        assert verifier.spdx_hash(changed) != expected
    changed = copy.deepcopy(original)
    changed["packages"][0]["annotations"][0]["annotationDate"] = "two"
    assert verifier.spdx_hash(changed) != expected
    changed = copy.deepcopy(original)
    changed["unknown"].reverse()
    assert verifier.spdx_hash(changed) != expected
    for value in (float("nan"), float("inf"), "\ud800"):
        with pytest.raises(ValueError):
            verifier.spdx_hash({"spdxVersion": "SPDX-2.3", "value": value})
    for raw in ('{"spdxVersion":"SPDX-2.3","nested":{"a":1,"a":2}}', '{"value":NaN}'):
        with pytest.raises(ValueError):
            verifier.loads(raw)


def test_signed_spdx_or_encoding_mutation_rejects_without_optional_regeneration() -> None:
    manifest, payloads = packet()
    payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"][
        "name"
    ] = "changed"
    with pytest.raises(ValueError, match="SPDX"):
        verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)


def test_material_generation_requires_one_complete_spdx_before_signing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, payloads = packet()
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "34700002576")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    output = tmp_path / "materials.json"
    args = ["generate", "--json-out", str(output)]
    assert verifier.main(args) == 1
    assert not output.exists()
    document = payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"]
    sbom = tmp_path / "original.spdx.json"
    sbom.write_text(json.dumps(document))
    assert verifier.main(args + ["--sbom", str(sbom)]) == 0
    material = json.loads(output.read_text())
    assert material["spdx_sha256"] == verifier.spdx_hash(document)
    assert material["spdx_hash_encoding"] == verifier.SPDX_HASH_ENCODING


def test_distinct_real_build_tuples_keep_distinct_full_spdx_hashes() -> None:
    manifest, original = packet()
    later = copy.deepcopy(original)
    invocation = INVOCATION[:-1] + "2"
    for kind in verifier.TYPES:
        result = later[kind][0]["verificationResult"]
        result["signature"]["certificate"]["runInvocationURI"] = invocation
        predicate = result["statement"]["predicate"]
        if kind == verifier.TYPES[0]:
            predicate["runDetails"]["metadata"]["invocationId"] = invocation
        elif kind == verifier.MATERIALS_TYPE:
            predicate["source"]["run_invocation_uri"] = invocation
    document = later[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"]
    document["creationInfo"]["created"] = "2026-09-13T00:00:00Z"
    later[verifier.MATERIALS_TYPE][0]["verificationResult"]["statement"]["predicate"][
        "spdx_sha256"
    ] = verifier.spdx_hash(document)
    all_records = {kind: original[kind] + later[kind] for kind in verifier.TYPES}
    reused = verifier.validate_triple(all_records, manifest, REPO, WORKFLOW, REF)
    assert reused["original_build"]["run_invocation_uri"] == INVOCATION
    assert reused["spdx_sha256"] != verifier.spdx_hash(document)
    created = verifier.validate_triple(
        all_records, manifest, REPO, WORKFLOW, REF, run_invocation_uri=invocation, sbom=document
    )
    assert created["spdx_sha256"] == verifier.spdx_hash(document)
    manifest, payloads = packet()
    payloads[verifier.MATERIALS_TYPE][0]["verificationResult"]["statement"]["predicate"][
        "spdx_hash_encoding"
    ] = "unsupported"
    with pytest.raises(ValueError):
        verifier.validate_triple(payloads, manifest, REPO, WORKFLOW, REF)


def test_official_cli_verifies_all_three_before_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, payloads = packet()
    calls = []

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        kind = args[args.index("--predicate-type") + 1]
        return subprocess.CompletedProcess(args, 0, json.dumps(payloads[kind]), "")

    monkeypatch.setattr(verifier.native, "_run_gh", run)
    assert verifier.verify(manifest, REPO, WORKFLOW, REF, source_sha=SHA)["passed"]
    assert len(calls) == 3
    assert all(
        "--bundle-from-oci" in call and "--deny-self-hosted-runners" in call for call in calls
    )
    with pytest.raises(ValueError, match="source SHA"):
        verifier.verify(manifest, REPO, WORKFLOW, REF, source_sha="0" * 40)


def test_shared_material_rules_cover_recursive_added_deleted_owners() -> None:
    rules = verifier.material_rules("HEAD")
    assert verifier.selected("app/models/new/descendant.py", rules)
    assert verifier.selected("alembic/versions/new_revision.py", rules)
    assert verifier.selected("deploy/postgres-pgvector/new/material", rules)
    assert verifier.selected("core/db.py", rules)
    assert verifier.selected("scripts/ci/check_pgvector_attestations.py", rules)
    assert not verifier.selected("frontend/irrelevant.ts", rules)


@pytest.mark.parametrize("existing", [False, True])
def test_inventory_uses_official_triple_before_reuse_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool
) -> None:
    manifest, payloads = packet()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    sbom_path = tmp_path / "sbom.json"
    sbom_path.write_text(
        json.dumps(payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"])
    )
    records = []
    if existing:
        records = [
            {
                "bundle": {
                    "dsseEnvelope": {
                        "payload": base64.b64encode(
                            json.dumps(
                                payloads[kind][0]["verificationResult"]["statement"]
                            ).encode()
                        ).decode()
                    }
                }
            }
            for kind in verifier.TYPES
        ]
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"attestations": records}))
    calls = []

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        kind = args[args.index("--predicate-type") + 1]
        return subprocess.CompletedProcess(args, 0, json.dumps(payloads[kind]), "")

    monkeypatch.setattr(verifier.native, "_run_gh", run)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "34700002576")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    result = tmp_path / "result.json"
    assert (
        verifier.main(
            [
                "inventory",
                "--manifest",
                str(manifest_path),
                "--inventory",
                str(inventory),
                "--json-out",
                str(result),
                "--current-build",
                "--sbom",
                str(sbom_path),
                "--source-sha",
                SHA,
                "--run-invocation-uri",
                INVOCATION,
            ]
        )
        == 0
    )
    assert json.loads(result.read_text())["mode"] == ("reuse" if existing else "create")
    assert len(calls) == (3 if existing else 0)
    if existing:
        payloads[verifier.MATERIALS_TYPE] = []
        assert (
            verifier.main(
                ["inventory", "--manifest", str(manifest_path), "--inventory", str(inventory)]
            )
            == 1
        )


def test_material_changes_union_includes_added_and_deleted_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(verifier, "material_rules", lambda ref: ("app/models/**",))

    def git(args: list[str]) -> bytes:
        if args[0] == "ls-tree":
            return (
                b"app/models/old/nested.py\0docs/note.md\0"
                if args[-1] == "base"
                else b"app/models/new/nested.py\0docs/note.md\0"
            )
        return b"app/models/old/nested.py\0app/models/new/nested.py\0docs/note.md\0"

    monkeypatch.setattr(verifier, "git_output", git)
    assert verifier.material_changes("base", "head") == [
        "app/models/new/nested.py",
        "app/models/old/nested.py",
    ]


@pytest.mark.parametrize("present", [(), (0,), (0, 1), (0, 2)])
def test_interrupted_current_actual_build_resumes_only_its_missing_predicates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, present: tuple[int, ...]
) -> None:
    manifest, payloads = packet()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    sbom_path = tmp_path / "sbom.json"
    sbom_path.write_text(
        json.dumps(payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"])
    )
    records = [
        {
            "bundle": {
                "dsseEnvelope": {
                    "payload": base64.b64encode(
                        json.dumps(
                            payloads[verifier.TYPES[index]][0]["verificationResult"]["statement"]
                        ).encode()
                    ).decode()
                }
            }
        }
        for index in present
    ]
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"attestations": records}))

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        kind = args[args.index("--predicate-type") + 1]
        return subprocess.CompletedProcess(args, 0, json.dumps(payloads[kind]), "")

    monkeypatch.setattr(verifier.native, "_run_gh", run)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "34700002576")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    arguments = [
        "inventory",
        "--manifest",
        str(manifest_path),
        "--inventory",
        str(inventory),
        "--sbom",
        str(sbom_path),
    ]
    assert verifier.main(arguments) == 1
    output = tmp_path / "result.json"
    assert (
        verifier.main(
            arguments
            + [
                "--current-build",
                "--source-sha",
                SHA,
                "--run-invocation-uri",
                INVOCATION,
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    result = json.loads(output.read_text())
    for index, field in enumerate(("provenance_mode", "materials_mode", "sbom_mode")):
        assert result[field] == ("reuse" if index in present else "create")
    assert result["run_invocation_uri"] == INVOCATION
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    new_invocation = INVOCATION[:-1] + "2"
    assert (
        verifier.main(
            arguments
            + [
                "--current-build",
                "--source-sha",
                SHA,
                "--run-invocation-uri",
                new_invocation,
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    result = json.loads(output.read_text())
    assert all(
        result[field] == "create" for field in ("provenance_mode", "materials_mode", "sbom_mode")
    )


def test_repeated_actual_build_digest_selects_complete_original_execution() -> None:
    manifest, original = packet()
    later = copy.deepcopy(original)
    invocation = "https://github.com/" + REPO + "/actions/runs/34700002577/attempts/2"
    for kind in verifier.TYPES:
        result = later[kind][0]["verificationResult"]
        result["signature"]["certificate"]["runInvocationURI"] = invocation
        if kind == verifier.TYPES[0]:
            result["statement"]["predicate"]["runDetails"]["metadata"]["invocationId"] = invocation
        elif kind == verifier.MATERIALS_TYPE:
            result["statement"]["predicate"]["source"]["run_invocation_uri"] = invocation
    all_records = {kind: later[kind] + original[kind] for kind in verifier.TYPES}
    assert (
        verifier.validate_triple(all_records, manifest, REPO, WORKFLOW, REF)["original_build"][
            "run_invocation_uri"
        ]
        == INVOCATION
    )
    assert (
        verifier.validate_triple(
            all_records,
            manifest,
            REPO,
            WORKFLOW,
            REF,
            source_sha=SHA,
            run_invocation_uri=invocation,
        )["original_build"]["run_invocation_uri"]
        == invocation
    )
    all_records[verifier.MATERIALS_TYPE] = original[verifier.MATERIALS_TYPE]
    assert (
        verifier.validate_triple(all_records, manifest, REPO, WORKFLOW, REF)["original_build"][
            "run_invocation_uri"
        ]
        == INVOCATION
    )
    with pytest.raises(ValueError, match="HOLD"):
        verifier.validate_triple(
            all_records, manifest, REPO, WORKFLOW, REF, run_invocation_uri=invocation
        )


@pytest.mark.parametrize(
    "path",
    [
        "scripts/ops/postgres_backup.sh",
        "scripts/ops/postgres_restore.sh",
        "tests/test_staging_security.py",
    ],
)
def test_storage_mutation_and_validation_owners_are_finite_material_paths(path: str) -> None:
    assert verifier.selected(path, verifier.material_rules("HEAD"))


def test_historical_custom_slsa_is_retained_without_counting_as_native_evidence() -> None:
    manifest, current = packet()
    historical = copy.deepcopy(current[verifier.TYPES[0]][0])
    historical["verificationResult"]["statement"]["predicate"]["buildDefinition"][
        "buildType"
    ] = "https://pulseplate.app/buildtypes/postgres-pgvector/v1"
    incomplete = {
        verifier.TYPES[0]: [historical],
        verifier.TYPES[1]: [],
        verifier.TYPES[2]: copy.deepcopy(current[verifier.TYPES[2]]),
    }
    with pytest.raises(ValueError, match="HOLD"):
        verifier.validate_triple(incomplete, manifest, REPO, WORKFLOW, REF)
    current[verifier.TYPES[0]].append(historical)
    assert verifier.validate_triple(current, manifest, REPO, WORKFLOW, REF)["passed"]
    assert len(current[verifier.TYPES[0]]) == 2
    historical["verificationResult"]["statement"]["predicate"]["buildDefinition"][
        "buildType"
    ] = "https://unknown.example/build"
    with pytest.raises(ValueError, match="Unrecognized"):
        verifier.validate_triple(current, manifest, REPO, WORKFLOW, REF)

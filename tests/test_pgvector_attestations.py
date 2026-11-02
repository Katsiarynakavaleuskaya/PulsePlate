"""Original native build identity and finite material admission regressions."""

from __future__ import annotations

import ast
import copy
import base64
import json
import hashlib
import os
import shutil
import stat
from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

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


@pytest.mark.parametrize("existing,status", [(False, "200"), (False, "404"), (True, "200")])
def test_inventory_uses_official_triple_before_reuse_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool, status: str
) -> None:
    manifest, payloads = packet()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    sbom_path = tmp_path / "sbom.json"
    sbom_path.write_text(
        json.dumps(payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"])
    )
    if existing:
        regenerated = json.loads(sbom_path.read_text())
        regenerated["creationInfo"]["created"] = "2026-09-14T00:00:00Z"
        sbom_path.write_text(json.dumps(regenerated))
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
    inventory.write_text(
        json.dumps(
            {"attestations": [{"bundle_url": "https://example.invalid/native"} for _ in records]}
        )
    )
    calls = []

    def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[1] == "download":
            assert cwd is not None
            (cwd / (manifest["platform_manifest_digest"] + ".jsonl")).write_text(
                "\n".join(json.dumps(record["bundle"]) for record in records)
            )
            return subprocess.CompletedProcess(
                args, 0, "native CLI output is not a path contract", ""
            )
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
                "--inventory-http-status",
                status,
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
    assert len(calls) == (4 if existing else 0)
    if existing:
        readonly = [
            "inventory",
            "--manifest",
            str(manifest_path),
            "--inventory",
            str(inventory),
            "--json-out",
            str(result),
        ]
        assert verifier.main(readonly) == 0
        assert json.loads(result.read_text())["source_sha"] == SHA
        monkeypatch.setenv("GITHUB_SHA", "b" * 40)
        monkeypatch.setenv("GITHUB_RUN_ID", "34700002577")
        assert (
            verifier.main(
                readonly
                + [
                    "--current-build",
                    "--sbom",
                    str(sbom_path),
                    "--source-sha",
                    "b" * 40,
                    "--run-invocation-uri",
                    "https://github.com/" + REPO + "/actions/runs/34700002577/attempts/1",
                ]
            )
            == 0
        )
        assert json.loads(result.read_text())["run_invocation_uri"] == INVOCATION
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
                if args[-1] == "a" * 40
                else b"app/models/new/nested.py\0docs/note.md\0"
            )
        return b"app/models/old/nested.py\0app/models/new/nested.py\0docs/note.md\0"

    monkeypatch.setattr(verifier, "git_output", git)
    assert verifier.material_changes("a" * 40, "b" * 40) == [
        "app/models/new/nested.py",
        "app/models/old/nested.py",
    ]


@pytest.mark.parametrize("present", [(), (0,), (1,), (2,), (0, 1), (0, 2), (1, 2)])
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
    inventory.write_text(
        json.dumps(
            {"attestations": [{"bundle_url": "https://example.invalid/native"} for _ in records]}
        )
    )

    def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        if args[1] == "download":
            assert cwd is not None
            (cwd / (manifest["platform_manifest_digest"] + ".jsonl")).write_text(
                "\n".join(json.dumps(record["bundle"]) for record in records)
            )
            return subprocess.CompletedProcess(args, 0, "", "")
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
    if 1 in present or 2 in present:
        original_document = sbom_path.read_text()
        changed_document = json.loads(original_document)
        changed_document["creationInfo"]["created"] = "2026-09-14T00:00:00Z"
        sbom_path.write_text(json.dumps(changed_document))
        assert (
            verifier.main(
                arguments
                + ["--current-build", "--source-sha", SHA, "--run-invocation-uri", INVOCATION]
            )
            == 1
        )
        sbom_path.write_text(original_document)
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
        "deploy/systemd/pulseplate-postgres-backup.service.example",
        "deploy/systemd/pulseplate-staging-postgres-backup.service.example",
        "deploy/systemd/pulseplate-postgres-backup.timer.example",
        "deploy/systemd/pulseplate-staging-storage.conf",
    ],
)
def test_storage_mutation_and_validation_owners_are_finite_material_paths(path: str) -> None:
    assert verifier.selected(path, verifier.material_rules("HEAD"))


def test_timer_only_change_is_material_in_native_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = Path(".github/workflows/ci.yml").read_bytes()
    timer_path = "deploy/systemd/pulseplate-postgres-backup.timer.example"
    steps = yaml.safe_load(workflow)["jobs"]["changes"]["steps"]
    filters = next(step for step in steps if step.get("id") == "filter")["with"]["filters"]
    assert timer_path in yaml.safe_load(filters)["pgvector_compat"]
    timer_content = Path(timer_path).read_text()
    for name in verifier.git_output(["rev-parse", "--local-env-vars"]).decode().splitlines():
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    verifier.git_output(["init", "--initial-branch=main"])
    workflow_path = tmp_path / ".github/workflows/ci.yml"
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_bytes(workflow)
    timer = tmp_path / timer_path
    timer.parent.mkdir(parents=True)
    timer.write_text(timer_content)
    commit = [
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.org",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "fixture",
    ]
    verifier.git_output(["add", "."])
    verifier.git_output(commit)
    base = verifier.git_output(["rev-parse", "HEAD"]).decode().strip()
    timer.write_text(timer_content.replace("02:15:00", "03:15:00"))
    verifier.git_output(["add", timer_path])
    verifier.git_output(commit)
    head = verifier.git_output(["rev-parse", "HEAD"]).decode().strip()
    assert verifier.material_changes(base, head) == [timer_path]


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


@pytest.mark.parametrize(
    "arguments",
    [
        ["inventory"],
        ["changes"],
        ["changes", "--base", "a" * 40],
        ["unchanged", "--head", "a" * 40],
    ],
)
def test_mode_specific_missing_arguments_reject_before_input_use(
    arguments: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert verifier.main(arguments) == 1
    assert "requires" in capsys.readouterr().err


def test_official_verifier_fetch_limit_matches_complete_bounded_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest, payloads = packet()
    calls = []

    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        assert args[args.index("--limit") + 1] == "100"
        kind = args[args.index("--predicate-type") + 1]
        return subprocess.CompletedProcess(args, 0, json.dumps(payloads[kind] * 100), "")

    monkeypatch.setattr(verifier.native, "_run_gh", run)
    with pytest.raises(ValueError, match="limit exhausted"):
        verifier.verify(manifest, REPO, WORKFLOW, REF)


def test_first_creation_base_is_changed_only_after_addressable_full_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def git(args: list[str]) -> bytes:
        calls.append(args)
        return b"core/db.py\0" if args[0] == "ls-tree" else b""

    monkeypatch.setattr(verifier, "git_output", git)
    monkeypatch.setattr(verifier, "material_rules", lambda ref: ("core/db.py",))
    assert verifier.material_changes("0" * 40, "a" * 40) == ["core/db.py"]
    assert calls[0] == ["cat-file", "-e", "a" * 40 + "^{commit}"]
    with pytest.raises(ValueError, match="full SHA"):
        verifier.material_changes("0" * 40, "malformed")


@pytest.mark.parametrize(
    "failure",
    [
        "missing",
        "empty",
        "symlink",
        "directory",
        "failed",
        "malformed",
        "duplicate",
        "nonobject",
        "base64",
        "cap",
    ],
)
def test_native_download_failures_never_become_empty_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    manifest, _ = packet()
    metadata = tmp_path / "presence.json"
    metadata.write_text('{"attestations":[{"bundle_url":"opaque"}]}')
    roots = []

    def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert args == [
            "attestation",
            "download",
            verifier.native.build_artifact_uri(
                manifest["repository"], manifest["platform_manifest_digest"]
            ),
            "--repo",
            REPO,
            "--limit",
            "100",
        ]
        assert cwd is not None and not list(cwd.iterdir())
        roots.append(cwd)
        output = cwd / (manifest["platform_manifest_digest"] + ".jsonl")
        if failure == "symlink":
            output.symlink_to(metadata)
        elif failure == "directory":
            output.mkdir()
        elif failure != "missing":
            values = {
                "empty": "\n",
                "malformed": "{",
                "duplicate": '{"dsseEnvelope":{},"dsseEnvelope":{}}',
                "nonobject": "[]",
                "base64": '{"dsseEnvelope":{"payload":"!"}}',
                "cap": "{}\n" * 100,
                "failed": "{}",
            }
            output.write_text(values[failure])
        if failure == "failed":
            raise RuntimeError("native download failed")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(verifier.native, "_run_gh", run)
    with pytest.raises((ValueError, RuntimeError)):
        verifier.inventory_kinds(manifest, REPO, metadata, "200")
    assert roots and all(not root.exists() for root in roots)


@pytest.mark.parametrize("count", [1, 99, 100])
def test_native_inventory_counts_before_foreign_subject_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    manifest, _ = packet()
    metadata = tmp_path / "presence.json"
    metadata.write_text('{"attestations":[{}]}')
    record = {
        "dsseEnvelope": {
            "payload": base64.b64encode(
                json.dumps(
                    {"subject": [], "predicateType": "https://example.invalid/unrelated"}
                ).encode()
            ).decode()
        }
    }

    def run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd is not None
        (cwd / (manifest["platform_manifest_digest"] + ".jsonl")).write_text(
            "\n".join(json.dumps(record) for _ in range(count))
        )
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(verifier.native, "_run_gh", run)
    if count == 100:
        with pytest.raises(ValueError, match="limit"):
            verifier.inventory_kinds(manifest, REPO, metadata, "200")
    else:
        assert verifier.inventory_kinds(manifest, REPO, metadata, "200") == ()


@pytest.mark.parametrize("status", ["200", "404", "401", "403", "429", "500"])
def test_presence_status_is_not_readonly_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    manifest, _ = packet()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    metadata = tmp_path / "presence.json"
    metadata.write_text('{"attestations":[]}')

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Empty/error presence must not download or verify")

    monkeypatch.setattr(verifier.native, "_run_gh", forbidden)
    assert (
        verifier.main(
            [
                "inventory",
                "--manifest",
                str(manifest_path),
                "--inventory",
                str(metadata),
                "--inventory-http-status",
                status,
            ]
        )
        == 1
    )


@pytest.mark.parametrize("status", ["200", "404"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "unsupported"),
        ("repository", None),
        ("repository", "not-a-registry"),
        ("platform_manifest_digest", None),
        ("platform_manifest_digest", "sha256:invalid"),
    ],
)
def test_empty_inventory_rejects_invalid_subject_before_create_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    field: str,
    value: str | None,
) -> None:
    manifest, payloads = packet()
    manifest[field] = value
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    inventory = tmp_path / "inventory.json"
    inventory.write_text('{"attestations":[]}')
    sbom = tmp_path / "sbom.json"
    sbom.write_text(
        json.dumps(payloads[verifier.TYPES[2]][0]["verificationResult"]["statement"]["predicate"])
    )
    result = tmp_path / "decision.json"
    output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "34700002576")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid subject must be rejected before native calls")

    monkeypatch.setattr(verifier.native, "_run_gh", forbidden)
    assert (
        verifier.main(
            [
                "inventory",
                "--manifest",
                str(manifest_path),
                "--inventory",
                str(inventory),
                "--inventory-http-status",
                status,
                "--current-build",
                "--source-sha",
                SHA,
                "--run-invocation-uri",
                INVOCATION,
                "--sbom",
                str(sbom),
                "--json-out",
                str(result),
            ]
        )
        == 1
    )
    assert not result.exists()
    assert not output.exists()


def _pg_scan_program() -> tuple[dict[str, Any], dict[str, Any], str]:
    workflow = yaml.safe_load(Path(".github/workflows/cd.yml").read_text())
    job = workflow["jobs"]["postgres-pgvector-publish"]
    step = next(
        item
        for item in job["steps"]
        if item.get("name")
        == "Scan exact bases, post-APK builder, and final image without suppressions"
    )
    source = step["run"].split("python3 - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    return job, step, source


@pytest.mark.parametrize(
    "case",
    ["safe-hc", "secret", "null-secret", "malformed", "wrong-image", "native-error", "oci-private"],
)
def test_pg_scan_publication_keeps_unsafe_native_reports_private(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    from scripts.ci import check_docker_runtime_dependency_surface as surface

    job, _step, source = _pg_scan_program()
    tree = ast.parse(source)
    nodes = [
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name in {"file_facts", "publish_pg_report"}
    ]
    image = "sha256:" + "a" * 64
    monkeypatch.setattr(
        surface, "_run_docker", lambda argv: subprocess.CompletedProcess(argv, 0, image + "\n", "")
    )
    report: dict[str, Any] = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "ArtifactName": image,
        "Metadata": {"ImageID": image},
        "Results": [
            {
                "Target": "alpine",
                "Class": "os-pkgs",
                "Type": "alpine",
                "Vulnerabilities": [{"Severity": "HIGH", "VulnerabilityID": "synthetic"}],
            }
        ],
    }
    if case == "secret":
        report["Results"][0]["Secrets"] = [{"Match": "synthetic-private-secret"}]
    elif case == "null-secret":
        report["Results"][0]["Secrets"] = None
    elif case == "wrong-image":
        report["Metadata"]["ImageID"] = "sha256:" + "b" * 64
    raw = tmp_path / "private.json"
    raw.write_bytes(
        b"malformed synthetic private" if case == "malformed" else json.dumps(report).encode()
    )
    before = raw.read_bytes()
    public = tmp_path / "public"
    public.mkdir()
    namespace: dict[str, Any] = {
        "Path": Path,
        "os": os,
        "stat": stat,
        "hashlib": hashlib,
        "json": json,
        "subprocess": subprocess,
        "validate_trivy_image_report": surface.validate_trivy_image_report,
    }
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), "<PG-publication-helper>", "exec"),
        namespace,
    )
    accepted = namespace["publish_pg_report"](
        None if case == "oci-private" else image, raw, public, 1, 2 if case == "native-error" else 0
    )
    assert accepted is (case == "safe-hc")
    assert raw.read_bytes() == before
    if accepted:
        assert (public / "1.full.json").read_bytes() == before
    else:
        assert list(public.iterdir()) == []
    upload = next(
        item
        for item in job["steps"]
        if item.get("name") == "Upload PostgreSQL pgvector admission evidence"
    )
    assert upload["if"] == "${{ always() }}"
    assert "pulseplate-pg-scan-public/" in upload["with"]["path"]
    assert "private" not in upload["with"]["path"]


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "finding",
        "full-timeout",
        "full-error",
        "missing",
        "malformed",
        "secret",
        "null-secret",
        "wrong-image",
        "validation-error",
        "oci-malformed",
        "pull-error",
        "inspect-error",
        "db-drift",
    ],
)
def test_pg_scan_loop_retains_later_available_subjects_and_rejects_aggregate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: str | None,
) -> None:
    """Execute the actual whole workflow program with synthetic native boundaries and real files."""
    from scripts.ci import check_docker_runtime_dependency_surface as surface

    _job, step, source = _pg_scan_program()
    trivy = tmp_path / "trivy"
    trivy.write_bytes(b"synthetic pinned scanner")
    trivy.chmod(0o700)
    ignore = tmp_path / "empty-ignore"
    ignore.write_bytes(b"")
    docker_config = tmp_path / "docker-config"
    docker_config.mkdir()
    oci = tmp_path / "oci"
    (oci / "oci-1").mkdir(parents=True)
    final_digest = "sha256:" + "f" * 64
    for name, value in step["env"].items():
        if name.startswith("PGVECTOR_") and name.endswith("SECONDS"):
            monkeypatch.setenv(name, value)
    for name, value in {
        "RUNNER_TEMP": str(tmp_path),
        "TRIVY_BIN": str(trivy),
        "TRIVY_IGNORE_FILE": str(ignore),
        "TRIVY_DB_REPOSITORY": "ghcr.io/aquasecurity/trivy-db",
        "PGVECTOR_BUILDER_LOCAL_TAG": "synthetic-builder",
        "PGVECTOR_DOCKER_CONFIG": str(docker_config),
        "PGVECTOR_OCI_OUTPUT_DIR": str(oci),
        "PGVECTOR_EXPECTED_PLATFORM_DIGEST": final_digest,
        "TRIVY_IGNORE_POLICY": "synthetic-forbidden-policy",
        "GH_TOKEN": "synthetic-forbidden-token",
    }.items():
        monkeypatch.setenv(name, value)
    original_which = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: "/absolute/docker" if name == "docker" else original_which(name),
    )
    inspected_public: list[str] = []

    def inspect_image(argv: list[str]) -> subprocess.CompletedProcess[str]:
        assert argv[-1].startswith("sha256:")  # The OCI directory never enters this owner.
        inspected_public.append(argv[-1])
        if fault == "validation-error" and argv[-1] == "sha256:" + "1" * 64:
            raise RuntimeError("synthetic-private-native-diagnostic")
        return subprocess.CompletedProcess(argv, 0, argv[-1] + "\n", "")

    monkeypatch.setattr(surface, "_run_docker", inspect_image)
    calls: list[tuple[str, list[str]]] = []
    originals: dict[int, bytes] = {}
    private_marker = b"synthetic-private-native-diagnostic"

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        label = Path(kwargs["stdout"].name).name.removesuffix(".stdout")
        calls.append((label, argv))
        environment = kwargs["env"]
        assert "GH_TOKEN" not in environment and "TRIVY_IGNORE_POLICY" not in environment
        assert environment["DOCKER_CONFIG"] == str(docker_config)
        assert environment["HOME"] != os.environ.get("HOME")
        assert kwargs["stdin"] == subprocess.DEVNULL
        assert kwargs["check"] is False
        kwargs["stderr"].write(private_marker)
        if label == "database":
            cache = Path(argv[argv.index("--cache-dir") + 1])
            (cache / "db").mkdir(parents=True)
            (cache / "db/trivy.db").write_bytes(b"one frozen synthetic DB")
            (cache / "db/metadata.json").write_text('{"Version":2}')
            return subprocess.CompletedProcess(argv, 0)
        ordinal = int(label.split(".", 1)[0])
        if label.endswith(".pull"):
            assert kwargs["timeout"] == int(step["env"]["PGVECTOR_PULL_PROCESS_SECONDS"])
            return subprocess.CompletedProcess(
                argv, 7 if fault == "pull-error" and ordinal == 1 else 0
            )
        if label.endswith(".inspect"):
            assert kwargs["timeout"] == int(step["env"]["PGVECTOR_INSPECT_PROCESS_SECONDS"])
            kwargs["stdout"].write(("sha256:" + str(ordinal) * 64 + "\n").encode())
            return subprocess.CompletedProcess(
                argv, 7 if fault == "inspect-error" and ordinal == 1 else 0
            )
        assert kwargs["timeout"] == int(step["env"]["PGVECTOR_SCAN_PROCESS_SECONDS"])
        assert argv[argv.index("--timeout") + 1] == step["env"]["PGVECTOR_SCAN_SECONDS"] + "s"
        assert "--skip-db-update" in argv and "--skip-java-db-update" in argv
        assert argv[argv.index("--scanners") + 1] == "vuln,secret"
        if ordinal == 4:
            assert argv[-2:] == ["--input", str(oci / "oci-1")]
        else:
            assert argv[-1] == "sha256:" + str(ordinal) * 64
        if label.endswith(".hc"):
            assert argv[argv.index("--severity") + 1] == "CRITICAL,HIGH"
            assert argv[argv.index("--exit-code") + 1] == "1"
            assert argv[argv.index("--format") + 1] == "table"
            kwargs["stdout"].write(private_marker)
            return subprocess.CompletedProcess(
                argv, 1 if fault == "finding" and ordinal == 1 else 0
            )
        assert argv[argv.index("--severity") + 1] == "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL"
        assert argv[argv.index("--exit-code") + 1] == "0" and "--list-all-pkgs" in argv
        report_path = Path(argv[argv.index("--output") + 1])
        image = argv[-1]
        report: dict[str, Any] = {
            "SchemaVersion": 2,
            "ArtifactType": "container_image",
            "ArtifactName": image,
            "Metadata": {"ImageID": image},
            "Results": [
                {"Target": "alpine", "Class": "os-pkgs", "Type": "alpine", "Vulnerabilities": []}
            ],
        }
        if ordinal == 1:
            if fault == "finding":
                report["Results"][0]["Vulnerabilities"] = [
                    {"Severity": "HIGH", "VulnerabilityID": "synthetic"}
                ]
            elif fault == "secret":
                report["Results"][0]["Secrets"] = [{"Match": private_marker.decode()}]
            elif fault == "null-secret":
                report["Results"][0]["Secrets"] = None
            elif fault == "wrong-image":
                report["Metadata"]["ImageID"] = final_digest
            elif fault == "db-drift":
                cache = Path(argv[argv.index("--cache-dir") + 1])
                (cache / "db/trivy.db").write_bytes(b"changed DB")
        body = json.dumps(report).encode()
        if fault == "malformed" and ordinal == 1 or fault == "oci-malformed" and ordinal == 4:
            body = b"{" + private_marker
        if not (fault == "missing" and ordinal == 1):
            report_path.write_bytes(body)
            originals[ordinal] = body
        if fault == "full-timeout" and ordinal == 1:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], stderr=private_marker)
        return subprocess.CompletedProcess(argv, 2 if fault == "full-error" and ordinal == 1 else 0)

    monkeypatch.setattr(subprocess, "run", run)
    previous_umask = os.umask(0o077)
    try:
        if fault is None:
            exec(compile(source, "<cd.yml:pgvector-scan-loop>", "exec"), {})
        else:
            with pytest.raises(SystemExit, match="pg_scan_failed_private_diagnostics"):
                exec(compile(source, "<cd.yml:pgvector-scan-loop>", "exec"), {})
    finally:
        os.umask(previous_umask)
    output = capsys.readouterr()
    assert private_marker.decode() not in output.out + output.err
    public = tmp_path / "pulseplate-pg-scan-public"
    statuses = {n: json.loads((public / f"{n}.status.json").read_text()) for n in range(1, 5)}
    assert statuses[4].get("public_full_report") is False
    assert not (public / "4.full.json").exists()
    if fault != "db-drift":
        for ordinal in (2, 3, 4):
            assert any(label == f"{ordinal}.full" for label, _ in calls)
            assert any(label == f"{ordinal}.hc" for label, _ in calls)
        assert statuses[4]["subject"] == final_digest
        assert statuses[4]["raw"]["sha256"] == hashlib.sha256(originals[4]).hexdigest()
    else:
        assert not any(label == "1.hc" for label, _ in calls)
        assert all(statuses[n]["failure"] == "frozen_input_drift" for n in range(1, 5))
    private_dirs = list(tmp_path.glob("pulseplate-pg-scan-private-*"))
    assert len(private_dirs) == 1
    private = private_dirs[0]
    assert stat.S_IMODE(private.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o600 for path in private.rglob("*") if path.is_file()
    )
    assert final_digest not in inspected_public
    for ordinal, body in originals.items():
        assert (private / f"{ordinal}.full.json").read_bytes() == body
    for path in public.iterdir():
        assert private_marker not in path.read_bytes()
        if path.name.endswith(".full.json"):
            assert path.read_bytes() == originals[int(path.name.split(".", 1)[0])]
    if fault == "full-timeout":
        assert statuses[1]["full_native_exit"] == 124
    if fault == "finding":
        assert statuses[1]["hc_native_exit"] == 1
        assert statuses[1]["public_full_report"] is True


def test_pg_scan_job_budget_covers_dual_scans_and_remaining_native_work() -> None:
    from scripts.ci.check_docker_runtime_dependency_surface import DOCKER_TIMEOUT_SECONDS

    job, step, source = _pg_scan_program()
    budgets = {name: int(value) for name, value in step["env"].items() if name.endswith("SECONDS")}
    assert job["timeout-minutes"] == 240
    assert 0 < budgets["PGVECTOR_SCAN_SECONDS"] < budgets["PGVECTOR_SCAN_PROCESS_SECONDS"]
    # One DB acquisition, four full and four HC scans, two pulls, three direct
    # inspections and three existing structural-owner Docker inspections.
    scan_envelope = (
        9 * budgets["PGVECTOR_SCAN_PROCESS_SECONDS"]
        + 2 * budgets["PGVECTOR_PULL_PROCESS_SECONDS"]
        + 3 * budgets["PGVECTOR_INSPECT_PROCESS_SECONDS"]
        + 3 * DOCKER_TIMEOUT_SECONDS
    )
    assert job["timeout-minutes"] * 60 - scan_envelope >= 90 * 60
    assert "continue-on-error" not in step
    assert "--download-db-only" in source
    assert source.count('"--download-db-only"') == 1
    assert "print(" not in source and "tee " not in source

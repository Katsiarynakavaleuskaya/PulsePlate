#!/usr/bin/env python3
"""Bounded PostgreSQL materials and officially verified original-build admission."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404: native Git owns tracked-tree semantics; no safer bounded replacement (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci import check_docker_provenance_attestation as native

MATERIALS_TYPE = "https://pulseplate.app/attestations/postgres-pgvector-materials/v1"
SPDX_HASH_ENCODING = "python-json-sortkeys-compact-utf8-no-ascii-escape-no-nonfinite-v1"
TYPES = (native.PROVENANCE_PREDICATE_TYPE, MATERIALS_TYPE, native.SBOM_PREDICATE_TYPE)
MANIFEST = Path("deploy/postgres-pgvector/image-manifest.json")
HELPER_PATHS = (
    ".github/workflows/cd.yml",
    "scripts/ci/check_pgvector_attestations.py",
    "scripts/ci/check_docker_provenance_attestation.py",
    "tests/test_pgvector_attestations.py",
    "tests/test_cd_attestation_workflow_contract.py",
    "tests/test_check_docker_provenance_attestation.py",
    "scripts/ops/check_staging_security.py",
    "deploy/systemd/pulseplate-staging-storage.conf",
    "deploy/systemd/pulseplate-postgres-backup.service.example",
    "scripts/ops/postgres_backup.sh",
    "scripts/ops/postgres_restore.sh",
    "tests/test_staging_security.py",
    "scripts/ci/check_staging_postgres_runtime.py",
    "tests/test_staging_postgres_runtime.py",
)


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def loads(raw: str | bytes) -> object:
    return json.loads(
        raw,
        object_pairs_hook=reject_duplicates,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected regular JSON file")
    result = loads(path.read_bytes())
    if not isinstance(result, dict):
        raise ValueError("Expected JSON object")
    return result


def material_dependencies(manifest: dict) -> list[dict]:
    if manifest.get("schema") == "pulseplate.synthetic_attestation_probe.v1":
        if set(manifest) != {"schema", "repository", "platform_manifest_digest", "recipe"}:
            raise ValueError("Synthetic probe manifest shape drifted")
        if manifest["recipe"] != {"base": "scratch", "payload": "synthetic-attestation-probe-v1"}:
            raise ValueError("Synthetic probe recipe drifted")
        return []
    materials = [
        ("dhi.io/postgres:runtime-index", manifest["runtime_base_index_digest"]),
        ("dhi.io/postgres:runtime-platform", manifest["runtime_base_platform_manifest_digest"]),
        ("dhi.io/postgres:runtime-config", manifest["runtime_base_config_digest"]),
        ("dhi.io/postgres:builder-index", manifest["builder_base_index_digest"]),
        ("dhi.io/postgres:builder-platform", manifest["builder_base_platform_manifest_digest"]),
        ("dhi.io/postgres:builder-config", manifest["builder_base_config_digest"]),
        (manifest["pgvector_source_url"], manifest["pgvector_source_sha256"]),
        (
            "git+https://github.com/pgvector/pgvector",
            "sha1:" + manifest["pgvector_source_commit"],
        ),
        (
            "git+https://github.com/Katsiarynakavaleuskaya/PulsePlate#deploy/postgres-pgvector/Containerfile",
            manifest["containerfile_sha256"],
        ),
        ("pulseplate:builder-apk-closure", manifest["builder_apk_closure_sha256"]),
        ("pulseplate:builder-apk-inputs", manifest["builder_apk_inputs_sha256"]),
        ("pulseplate:builder-apk-signed-index", manifest["builder_apk_index_sha256"]),
        ("docker.io/moby/buildkit", manifest["buildkit_platform_manifest_digest"]),
        (
            "https://github.com/docker/buildx/releases/download/"
            f"v{manifest['buildx_version']}/buildx-v{manifest['buildx_version']}.linux-amd64",
            manifest["buildx_linux_amd64_sha256"],
        ),
        (
            "pulseplate:runtime-artifact-inventory",
            manifest["runtime_artifact_inventory_sha256"],
        ),
        ("pulseplate:mountpoint-layer", manifest["mountpoint_layer_digest"]),
        ("pulseplate:mountpoint-layer-diff-id", manifest["mountpoint_layer_diff_id"]),
    ]
    resolved_dependencies = []
    for uri, digest in materials:
        algorithm, value = digest.split(":", 1)
        resolved_dependencies.append({"uri": uri, "digest": {algorithm: value}})

    return resolved_dependencies


def materials_predicate(manifest: dict, identity: dict, spdx_sha256: str) -> dict:
    return {
        "schema": "pulseplate.postgres_pgvector_materials.v1",
        "spdx_sha256": spdx_sha256,
        "spdx_hash_encoding": SPDX_HASH_ENCODING,
        "source": identity,
        "recipe": copy.deepcopy(manifest),
        "resolvedDependencies": material_dependencies(manifest),
    }


def identity_from_certificate(result: dict, repo: str, workflow: str, ref: str) -> dict:
    signature = result.get("signature")
    certificate = signature.get("certificate") if isinstance(signature, dict) else None
    if not isinstance(certificate, dict):
        raise ValueError("Missing native signature certificate")
    sha = certificate.get("sourceRepositoryDigest")
    invocation = certificate.get("runInvocationURI")
    signer = "https://github.com/" + workflow + "@" + ref
    if (
        not isinstance(sha, str)
        or re.fullmatch(r"[0-9a-f]{40}", sha) is None
        or certificate.get("sourceRepositoryURI") != "https://github.com/" + repo
        or certificate.get("sourceRepositoryRef") != ref
        or certificate.get("buildSignerURI") != signer
        or certificate.get("runnerEnvironment") != "github-hosted"
        or not isinstance(invocation, str)
        or re.fullmatch(
            re.escape("https://github.com/" + repo)
            + r"/actions/runs/[1-9][0-9]*/attempts/[1-9][0-9]*",
            invocation,
        )
        is None
    ):
        raise ValueError("Original build certificate identity mismatch")
    return {
        "repository": repo,
        "source_sha": sha,
        "source_ref": ref,
        "signer_workflow": workflow,
        "run_invocation_uri": invocation,
    }


def spdx_hash(document: dict) -> str:
    """Bind every native SPDX field and array position without normalization."""
    if not isinstance(document, dict) or document.get("spdxVersion") != "SPDX-2.3":
        raise ValueError("Native SPDX predicate must be an SPDX-2.3 object")
    encoded = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def verified_statement(
    payload: object, predicate_type: str, subject: list, repo: str, workflow: str, ref: str
) -> tuple[dict, dict]:
    if not isinstance(payload, list) or len(payload) != 1:
        raise ValueError("Expected exactly one original-build attestation per predicate")
    item = payload[0]
    result = item.get("verificationResult") if isinstance(item, dict) else None
    if not isinstance(result, dict):
        raise ValueError("Missing native verificationResult")
    statement = result.get("statement")
    if (
        not isinstance(statement, dict)
        or statement.get("_type") != "https://in-toto.io/Statement/v1"
        or statement.get("predicateType") != predicate_type
        or statement.get("subject") != subject
        or not isinstance(statement.get("predicate"), dict)
    ):
        raise ValueError("Verified statement subject/type/predicate mismatch")
    return statement["predicate"], identity_from_certificate(result, repo, workflow, ref)


def validate_one_triple(
    payloads: dict,
    manifest: dict,
    repo: str,
    workflow: str,
    ref: str,
    source_sha: str | None = None,
    sbom: dict | None = None,
) -> dict:
    if manifest.get("schema") not in (
        "pulseplate.postgres_pgvector_image_manifest.v1",
        "pulseplate.synthetic_attestation_probe.v1",
    ):
        raise ValueError("Unsupported material manifest schema")
    if (
        not isinstance(manifest.get("repository"), str)
        or re.fullmatch(r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+", manifest["repository"]) is None
        or not isinstance(manifest.get("platform_manifest_digest"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", manifest["platform_manifest_digest"]) is None
    ):
        raise ValueError("Material subject identity malformed")
    subject = [
        {
            "name": manifest["repository"],
            "digest": {"sha256": manifest["platform_manifest_digest"].removeprefix("sha256:")},
        }
    ]
    records = [
        verified_statement(payloads[kind], kind, subject, repo, workflow, ref) for kind in TYPES
    ]
    identity = records[0][1]
    if any(record[1] != identity for record in records):
        raise ValueError("Attestation original source/run/attempt identities differ")
    if source_sha is not None and identity["source_sha"] != source_sha:
        raise ValueError("Original source SHA mismatch")
    provenance, materials, document = (record[0] for record in records)
    definition = provenance.get("buildDefinition")
    if not isinstance(definition, dict):
        raise ValueError("Native SLSA buildDefinition missing")
    expected_workflow = {
        "path": workflow.split("/.github/", 1)[-1],
        "ref": ref,
        "repository": "https://github.com/" + repo,
    }
    expected_workflow["path"] = ".github/" + expected_workflow["path"]
    dependencies = [
        {
            "digest": {"gitCommit": identity["source_sha"]},
            "uri": "git+https://github.com/" + repo + "@" + ref,
        }
    ]
    external = definition.get("externalParameters")
    run_details = provenance.get("runDetails")
    if not isinstance(external, dict) or not isinstance(run_details, dict):
        raise ValueError("Native SLSA workflow/run details malformed")
    metadata = run_details.get("metadata")
    builder = run_details.get("builder")
    if not isinstance(metadata, dict) or not isinstance(builder, dict):
        raise ValueError("Native SLSA invocation/builder malformed")
    if (
        definition.get("buildType") != "https://actions.github.io/buildtypes/workflow/v1"
        or external.get("workflow") != expected_workflow
        or definition.get("resolvedDependencies") != dependencies
        or metadata.get("invocationId") != identity["run_invocation_uri"]
        or builder.get("id") != "https://github.com/" + workflow + "@" + ref
    ):
        raise ValueError("Native SLSA original workflow/source/invocation mismatch")
    document_hash = spdx_hash(document)
    if materials != materials_predicate(manifest, identity, document_hash):
        raise ValueError("Exact material recipe/dependency/source/SPDX hash mismatch")
    if sbom is not None and document_hash != spdx_hash(sbom):
        raise ValueError("Entire SPDX predicate hash mismatch")
    return {
        "passed": True,
        "schema": "pulseplate.pgvector_attestation_admission.v1",
        "artifact_uri": native.build_artifact_uri(
            manifest["repository"], manifest["platform_manifest_digest"]
        ),
        "original_build": identity,
        "predicate_types": list(TYPES),
        "materials_sha256": native._canonical_json_sha256(materials),
        "spdx_sha256": document_hash,
    }


def tuple_records(payloads: dict, manifest: dict, repo: str, workflow: str, ref: str) -> dict:
    """Group official verified records by exact original execution, never by type alone."""
    subject = [
        {
            "name": manifest["repository"],
            "digest": {"sha256": manifest["platform_manifest_digest"].removeprefix("sha256:")},
        }
    ]
    groups: dict[str, dict] = {}
    for kind in TYPES:
        items = payloads.get(kind)
        if not isinstance(items, list):
            raise ValueError("Verified predicate inventory malformed")
        for item in items:
            predicate, identity = verified_statement([item], kind, subject, repo, workflow, ref)
            definition = predicate.get("buildDefinition")
            if kind == TYPES[0] and (
                not isinstance(definition, dict)
                or definition.get("buildType") != "https://actions.github.io/buildtypes/workflow/v1"
            ):
                # Historical custom SLSA proofs are retained, but are not native build evidence.
                if isinstance(definition, dict) and definition.get("buildType") == (
                    "https://pulseplate.app/buildtypes/postgres-pgvector/v1"
                ):
                    continue
                raise ValueError("Unrecognized native provenance build type")
            key = json.dumps(identity, sort_keys=True)
            if any(
                group["identity"]["run_invocation_uri"] == identity["run_invocation_uri"]
                and group["identity"] != identity
                for group in groups.values()
            ):
                raise ValueError("One original execution has conflicting certificate identities")
            group = groups.setdefault(key, {"identity": identity, "records": {}})
            records = group["records"]
            if kind in records:
                old_predicate = records[kind][0]["verificationResult"]["statement"]["predicate"]
                equivalent = (
                    spdx_hash(old_predicate) == spdx_hash(predicate)
                    if kind == TYPES[2]
                    else old_predicate == predicate
                )
                if not equivalent:
                    raise ValueError("Conflicting predicate records for one original execution")
            else:
                records[kind] = [item]
    return groups


def validate_triple(
    payloads: dict,
    manifest: dict,
    repo: str,
    workflow: str,
    ref: str,
    source_sha: str | None = None,
    sbom: dict | None = None,
    run_invocation_uri: str | None = None,
) -> dict:
    groups = tuple_records(payloads, manifest, repo, workflow, ref)
    eligible = []
    last_error = None
    for group in groups.values():
        identity = group["identity"]
        if source_sha is not None and identity["source_sha"] != source_sha:
            continue
        if run_invocation_uri is not None and identity["run_invocation_uri"] != run_invocation_uri:
            continue
        if set(group["records"]) != set(TYPES):
            continue
        try:
            result = validate_one_triple(
                group["records"], manifest, repo, workflow, ref, source_sha, sbom
            )
        except ValueError as exc:
            last_error = exc
            if run_invocation_uri is not None:
                raise
            continue
        run, attempt = (
            identity["run_invocation_uri"].rsplit("/actions/runs/", 1)[1].split("/attempts/")
        )
        eligible.append(((int(run), int(attempt), identity["source_sha"]), result))
    if not eligible:
        if last_error is not None:
            raise last_error
        raise ValueError(
            "No complete eligible original-build tuple; source SHA/content/inventory HOLD"
        )
    # Closed stable selection, not a claim about build chronology or current reuse execution.
    eligible.sort(key=lambda member: member[0])
    return eligible[0][1]


def verified_payloads(
    manifest: dict,
    repo: str,
    workflow: str,
    ref: str,
    present: tuple[str, ...] = TYPES,
) -> dict:
    payloads: dict[str, object] = {kind: [] for kind in TYPES}
    uri = native.build_artifact_uri(manifest["repository"], manifest["platform_manifest_digest"])
    for kind in TYPES:
        if kind not in present:
            continue
        completed = native._run_gh(
            [
                "attestation",
                "verify",
                uri,
                "--repo",
                repo,
                "--signer-workflow",
                workflow,
                "--source-ref",
                ref,
                "--predicate-type",
                kind,
                "--bundle-from-oci",
                "--deny-self-hosted-runners",
                "--format",
                "json",
            ]
        )
        payloads[kind] = loads(completed.stdout)
    return payloads


def verify(
    manifest: dict,
    repo: str,
    workflow: str,
    ref: str,
    source_sha: str | None = None,
    sbom: dict | None = None,
    run_invocation_uri: str | None = None,
) -> dict:
    payloads = verified_payloads(manifest, repo, workflow, ref)
    return validate_triple(
        payloads, manifest, repo, workflow, ref, source_sha, sbom, run_invocation_uri
    )


def git_output(args: list[str]) -> bytes:
    binary = shutil.which("git")
    if binary is None:
        raise ValueError("Git required")
    return subprocess.run(  # nosec B603: absolute Git argv, disabled replacement objects, no shell and bounded timeout (remove-by: 2026-10-12, ref: ledger-p1-native-cli-subprocess-review)
        [binary, "--no-replace-objects", *args], check=True, capture_output=True, timeout=120
    ).stdout


def material_rules(ref: str) -> tuple[str, ...]:
    text = git_output(["show", ref + ":.github/workflows/ci.yml"]).decode()
    rows = re.findall(r"^ {12}pgvector_compat: (\[[^\n]+\])$", text, re.MULTILINE)
    if len(rows) != 1:
        raise ValueError("Expected one complete CI pgvector_compat rule universe")
    # This is the existing finite literal filter, not a YAML/runtime policy parser.
    rules = loads(rows[0].replace("'", '"'))
    if not isinstance(rules, list) or any(not isinstance(rule, str) for rule in rules):
        raise ValueError("Malformed CI material rule set")
    if any("*" in rule and not rule.endswith("/**") for rule in rules):
        raise ValueError("Unsupported CI material rule")
    return tuple(rules) + HELPER_PATHS


def selected(path: str, rules: tuple[str, ...]) -> bool:
    return any(
        path == rule or (rule.endswith("/**") and path.startswith(rule[:-2])) for rule in rules
    )


def material_changes(base: str, head: str) -> list[str]:
    rules = tuple(dict.fromkeys(material_rules(base) + material_rules(head)))
    # Independently enumerate both tracked trees: additions/deletions are admitted.
    universe: set[str] = set()
    for ref in (base, head):
        universe.update(
            p.decode()
            for p in git_output(["ls-tree", "-r", "--name-only", "-z", ref]).split(b"\0")
            if p
        )
    changed = {
        p.decode()
        for p in git_output(["diff", "--name-only", "-z", "--no-renames", base, head]).split(b"\0")
        if p
    }
    return sorted(path for path in universe & changed if selected(path, rules))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "verify", "inventory", "changes", "unchanged"))
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--repo", default="Katsiarynakavaleuskaya/PulsePlate")
    parser.add_argument(
        "--signer-workflow", default="Katsiarynakavaleuskaya/PulsePlate/.github/workflows/cd.yml"
    )
    parser.add_argument("--source-ref", default="refs/heads/main")
    parser.add_argument("--source-sha")
    parser.add_argument("--run-invocation-uri")
    parser.add_argument(
        "--current-build",
        action="store_true",
        help="Publisher-only: actual exact image was rebuilt by this execution",
    )
    parser.add_argument("--sbom", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--head")
    args = parser.parse_args(argv)
    try:
        if args.mode in ("changes", "unchanged"):
            changes = material_changes(args.base, args.head)
            if args.mode == "unchanged" and changes:
                raise ValueError(
                    "Current main PostgreSQL material superseded run: " + ",".join(changes)
                )
            result = {"changed": bool(changes), "paths": changes}
        else:
            manifest = read_json(args.manifest)
            if args.mode == "generate":
                identity = {
                    "repository": args.repo,
                    "source_sha": os.environ["GITHUB_SHA"],
                    "source_ref": args.source_ref,
                    "signer_workflow": args.signer_workflow,
                    "run_invocation_uri": "https://github.com/"
                    + args.repo
                    + "/actions/runs/"
                    + os.environ["GITHUB_RUN_ID"]
                    + "/attempts/"
                    + os.environ["GITHUB_RUN_ATTEMPT"],
                }
                if args.sbom is None:
                    raise ValueError(
                        "Materials generation requires --sbom from the one native SPDX generation"
                    )
                result = materials_predicate(manifest, identity, spdx_hash(read_json(args.sbom)))
            elif args.mode == "inventory":
                current_sbom = read_json(args.sbom) if args.sbom is not None else None
                if args.current_build and current_sbom is None:
                    raise ValueError(
                        "Current actual-build inventory requires its one generated --sbom"
                    )
                inventory = read_json(args.inventory).get("attestations")
                if not isinstance(inventory, list) or len(inventory) >= 100:
                    raise ValueError("Attestation inventory malformed/pagination ambiguous")
                kinds = []
                for record in inventory:
                    statement = loads(
                        base64.b64decode(record["bundle"]["dsseEnvelope"]["payload"], validate=True)
                    )
                    if not isinstance(statement, dict):
                        raise ValueError("Inventory statement malformed")
                    if statement.get("subject") == [
                        {
                            "name": manifest["repository"],
                            "digest": {
                                "sha256": manifest["platform_manifest_digest"].removeprefix(
                                    "sha256:"
                                )
                            },
                        }
                    ]:
                        kinds.append(statement.get("predicateType"))
                payloads = verified_payloads(
                    manifest,
                    args.repo,
                    args.signer_workflow,
                    args.source_ref,
                    tuple(kind for kind in TYPES if kind in kinds),
                )
                groups = tuple_records(
                    payloads, manifest, args.repo, args.signer_workflow, args.source_ref
                )
                try:
                    admitted = validate_triple(
                        payloads,
                        manifest,
                        args.repo,
                        args.signer_workflow,
                        args.source_ref,
                        sbom=current_sbom,
                    )
                except ValueError:
                    admitted = None
                if admitted is not None:
                    identity = admitted["original_build"]
                    modes = {kind: "reuse" for kind in TYPES}
                else:
                    if not args.current_build:
                        raise ValueError(
                            "No complete existing tuple; read-only reuse cannot author build evidence"
                        )
                    expected_invocation = (
                        "https://github.com/"
                        + args.repo
                        + "/actions/runs/"
                        + os.environ["GITHUB_RUN_ID"]
                        + "/attempts/"
                        + os.environ["GITHUB_RUN_ATTEMPT"]
                    )
                    if (
                        args.source_sha != os.environ["GITHUB_SHA"]
                        or args.run_invocation_uri != expected_invocation
                    ):
                        raise ValueError("Current actual-build source/run binding mismatch")
                    identity = {
                        "repository": args.repo,
                        "source_sha": args.source_sha,
                        "source_ref": args.source_ref,
                        "signer_workflow": args.signer_workflow,
                        "run_invocation_uri": expected_invocation,
                    }
                    current = groups.get(json.dumps(identity, sort_keys=True), {"records": {}})
                    if current_sbom is None:
                        raise ValueError("Current actual-build inventory lacks its generated SPDX")
                    current_hash = spdx_hash(current_sbom)
                    existing_materials = current["records"].get(MATERIALS_TYPE)
                    if existing_materials is not None and existing_materials[0][
                        "verificationResult"
                    ]["statement"]["predicate"] != materials_predicate(
                        manifest, identity, current_hash
                    ):
                        raise ValueError(
                            "Current execution materials conflict with generated SPDX; rebuild in a new execution"
                        )
                    existing_spdx = current["records"].get(TYPES[2])
                    if (
                        existing_spdx is not None
                        and spdx_hash(
                            existing_spdx[0]["verificationResult"]["statement"]["predicate"]
                        )
                        != current_hash
                    ):
                        raise ValueError(
                            "Current execution SPDX conflicts with generated SPDX; rebuild in a new execution"
                        )
                    modes = {
                        kind: "reuse" if kind in current["records"] else "create" for kind in TYPES
                    }
                result = {
                    "mode": (
                        "reuse" if all(mode == "reuse" for mode in modes.values()) else "create"
                    ),
                    "provenance_mode": modes[TYPES[0]],
                    "materials_mode": modes[TYPES[1]],
                    "sbom_mode": modes[TYPES[2]],
                    "source_sha": identity["source_sha"],
                    "run_invocation_uri": identity["run_invocation_uri"],
                }
                if os.getenv("GITHUB_OUTPUT"):
                    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                        for key, value in result.items():
                            output.write(key + "=" + str(value) + "\n")
            else:
                result = verify(
                    manifest,
                    args.repo,
                    args.signer_workflow,
                    args.source_ref,
                    args.source_sha,
                    read_json(args.sbom) if args.sbom else None,
                    args.run_invocation_uri,
                )
        if args.json_out:
            native._write_json(args.json_out, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (
        ValueError,
        RuntimeError,
        OSError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        print(native._redact_sensitive_text(str(exc)), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

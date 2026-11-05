"""Adapter/ownership regressions for the separate real Linux runtime experiment."""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

from scripts.ci import check_staging_postgres_runtime as runtime

ROOT = Path(__file__).resolve().parents[1]


def selected_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads((ROOT / "deploy/postgres-pgvector/image-manifest.json").read_text())
    # This is a renderer adapter fixture, not native integration success evidence.
    source = yaml.safe_load((ROOT / "deploy/docker-compose.staging.yaml").read_text())["services"][
        "postgres"
    ]
    rendered = {
        "services": {
            "postgres": {
                "image": source["image"],
                "platform": source["platform"],
                "command": source["command"],
                "environment": {"PGDATA": manifest["compose_pgdata"]},
                "volumes": [
                    {"type": "volume", "target": manifest["compose_volume_target"]},
                    {
                        "type": "bind",
                        "read_only": True,
                        "target": "/etc/postgresql/pg_hba.conf",
                        "source": str(ROOT / "deploy/postgres-pgvector/pg_hba.conf"),
                    },
                ],
            }
        }
    }
    return rendered, manifest


def _bind_identity_raw(
    contract: dict[str, Any],
    manifest: dict[str, Any],
    envelope: dict[str, Any],
    local: list[dict[str, Any]],
    raw: bytes,
    projection: object,
) -> None:
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    subject = manifest["repository"] + "@" + digest
    manifest["platform_manifest_digest"] = digest
    contract["image"] = subject
    envelope.update(
        {
            "Ref": subject,
            "Raw": base64.b64encode(raw).decode("ascii"),
            "Descriptor": {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": digest,
                "size": len(raw),
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            "OCIManifest": deepcopy(projection),
        }
    )
    local[0].update({"RepoDigests": [subject], "Id": manifest["config_digest"]})


def _identity_fixture(
    seed: str = "first",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    rendered, manifest = selected_fixture()
    config = ("synthetic-config-" + seed).encode()
    manifest["config_digest"] = "sha256:" + hashlib.sha256(config).hexdigest()
    document = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": manifest["config_digest"],
            "size": len(config),
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": "sha256:" + hashlib.sha256((seed + suffix).encode()).hexdigest(),
                "size": size,
                "annotations": {"synthetic": suffix},
            }
            for suffix, size in (("one", 1), ("two", 2))
        ],
    }
    contract: dict[str, Any] = {}
    envelope: dict[str, Any] = {}
    local = [{"Os": "linux", "Architecture": "amd64"}]
    _bind_identity_raw(contract, manifest, envelope, local, json.dumps(document).encode(), document)
    manifest["runtime_ref"] = (
        manifest["repository"] + ":synthetic@" + manifest["platform_manifest_digest"]
    )
    rendered["services"]["postgres"]["image"] = manifest["runtime_ref"]
    return runtime.selected_contract(rendered, manifest), manifest, envelope, local


def _identity_reader(
    monkeypatch: pytest.MonkeyPatch, subject: str, registry: bytes, local: bytes
) -> list[list[str]]:
    calls: list[list[str]] = []

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        if args == ["docker", "manifest", "inspect", "--verbose", subject]:
            output = registry
        else:
            assert args == ["docker", "image", "inspect", subject]
            output = local
        return subprocess.CompletedProcess(args, 0, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    return calls


@pytest.mark.parametrize("id_form", ["config_digest", "platform_manifest_digest"])
def test_selected_identity_requires_the_complete_witness_for_both_id_forms(
    monkeypatch: pytest.MonkeyPatch, id_form: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    local[0]["Id"] = manifest[id_form]
    # Object order is immaterial; Raw bytes and layer array order remain unchanged.
    envelope["OCIManifest"] = dict(reversed(list(envelope["OCIManifest"].items())))
    calls = _identity_reader(
        monkeypatch, contract["image"], json.dumps(envelope).encode(), json.dumps(local).encode()
    )
    subject = runtime._selected_image_subject(contract, manifest)
    runtime._admit_selected_image(subject, manifest)
    assert calls == [
        ["docker", "manifest", "inspect", "--verbose", subject],
        ["docker", "image", "inspect", subject],
    ]
    del envelope["Raw"]
    calls = _identity_reader(
        monkeypatch, subject, json.dumps(envelope).encode(), json.dumps(local).encode()
    )
    with pytest.raises(runtime.ProbeError, match="supported single OCI envelope"):
        runtime._admit_selected_image(subject, manifest)
    assert len(calls) == 1  # No config-form shortcut or local-inspect fallback.


@pytest.mark.parametrize(
    "owner,field,value",
    [
        ("manifest", "repository", None),
        ("manifest", "repository", ""),
        ("manifest", "repository", "https://ghcr.io/owner/image"),
        ("manifest", "repository", "user:password@ghcr.io/owner/image"),
        ("manifest", "repository", "ghcr.io/owner/image:tag"),
        ("manifest", "platform_manifest_digest", None),
        ("manifest", "platform_manifest_digest", "sha256:short"),
        ("manifest", "platform_manifest_digest", "sha256:" + "A" * 64),
        ("manifest", "config_digest", []),
        ("manifest", "config_digest", "sha256:short"),
        ("manifest", "platform", "linux/arm64"),
        ("contract", "platform", None),
        ("contract", "image", "ghcr.io/owner/image:tag"),
        ("contract", "image", []),
    ],
)
def test_selected_identity_rejects_consumed_tuple_fields_before_image_operations(
    monkeypatch: pytest.MonkeyPatch, owner: str, field: str, value: object
) -> None:
    contract, manifest, _, _ = _identity_fixture()
    (manifest if owner == "manifest" else contract)[field] = value
    calls: list[list[str]] = []
    monkeypatch.setattr(runtime, "native", lambda args, **kwargs: calls.append(args))
    with pytest.raises(runtime.ProbeError, match="Native selected image"):
        runtime._selected_image_subject(contract, manifest)
    assert calls == []
    if owner == "manifest":
        rendered, selected = selected_fixture()
        selected[field] = value
        with pytest.raises(runtime.ProbeError):
            runtime.selected_contract(rendered, selected)


@pytest.mark.parametrize(
    "fault,message",
    [
        ("array", "supported single OCI envelope"),
        ("extra", "supported single OCI envelope"),
        ("missing", "supported single OCI envelope"),
        ("ref", "reference or Raw field"),
        ("raw_type", "reference or Raw field"),
        ("base64", "malformed or non-finite"),
        ("base64_nonascii", "malformed or non-finite"),
        ("hash", "Raw identity or Descriptor"),
        ("descriptor_type", "Raw identity or Descriptor"),
        ("descriptor_extra", "Raw identity or Descriptor"),
        ("descriptor_missing", "Raw identity or Descriptor"),
        ("descriptor_digest", "Raw identity or Descriptor"),
        ("descriptor_size", "Raw identity or Descriptor"),
        ("descriptor_bool", "Raw identity or Descriptor"),
        ("descriptor_float", "Raw identity or Descriptor"),
        ("descriptor_zero", "Raw identity or Descriptor"),
        ("descriptor_media", "Raw identity or Descriptor"),
        ("descriptor_platform", "Raw identity or Descriptor"),
        ("descriptor_platform_extra", "Raw identity or Descriptor"),
    ],
)
def test_registry_envelope_rejects_independent_binding_faults(
    monkeypatch: pytest.MonkeyPatch, fault: str, message: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    observation: object = envelope
    if fault == "array":
        observation = [envelope]
    elif fault == "extra":
        envelope["unknown"] = "synthetic-marker"
    elif fault == "missing":
        del envelope["Raw"]
    elif fault == "ref":
        envelope["Ref"] += "suffix"
    elif fault == "raw_type":
        envelope["Raw"] = []
    elif fault == "base64":
        envelope["Raw"] += "!"
    elif fault == "base64_nonascii":
        envelope["Raw"] = "é"
    elif fault == "hash":
        raw = base64.b64decode(envelope["Raw"])
        changed = raw.replace(b'"schemaVersion": 2', b'"schemaVersion": 3')
        assert changed != raw and len(changed) == len(raw)
        envelope["Raw"] = base64.b64encode(changed).decode()
    elif fault == "descriptor_type":
        envelope["Descriptor"] = []
    elif fault == "descriptor_extra":
        envelope["Descriptor"]["unknown"] = True
    elif fault == "descriptor_missing":
        del envelope["Descriptor"]["size"]
    elif fault == "descriptor_platform_extra":
        envelope["Descriptor"]["platform"]["variant"] = "unknown"
    else:
        field, value = {
            "descriptor_digest": ("digest", "sha256:" + "0" * 64),
            "descriptor_size": ("size", envelope["Descriptor"]["size"] + 1),
            "descriptor_bool": ("size", True),
            "descriptor_float": ("size", float(envelope["Descriptor"]["size"])),
            "descriptor_zero": ("size", 0),
            "descriptor_media": (
                "mediaType",
                "application/vnd.docker.distribution.manifest.v2+json",
            ),
            "descriptor_platform": ("platform", {"os": "linux", "architecture": "arm64"}),
        }[fault]
        envelope["Descriptor"][field] = value
    calls = _identity_reader(
        monkeypatch, contract["image"], json.dumps(observation).encode(), json.dumps(local).encode()
    )
    with pytest.raises(runtime.ProbeError, match=message):
        runtime._admit_selected_image(contract["image"], manifest)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("schemaVersion", True, "supported OCI image manifest"),
        ("schemaVersion", 2.0, "supported OCI image manifest"),
        ("schemaVersion", "2", "supported OCI image manifest"),
        ("mediaType", "application/vnd.oci.image.index.v1+json", "supported OCI image manifest"),
        (
            "mediaType",
            "application/vnd.docker.distribution.manifest.v2+json",
            "supported OCI image manifest",
        ),
        ("layers", {}, "supported OCI image manifest"),
        ("manifests", [], "supported OCI image manifest"),
        ("config", [], "config descriptor"),
        ("__root__", [], "supported OCI image manifest"),
        ("__missing_layers__", None, "supported OCI image manifest"),
    ],
)
def test_raw_manifest_shape_is_checked_after_recomputed_hash_binding(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object, message: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    document = deepcopy(envelope["OCIManifest"])
    if field == "__root__":
        document = value
    elif field == "__missing_layers__":
        del document["layers"]
    else:
        document[field] = value
    _bind_identity_raw(contract, manifest, envelope, local, json.dumps(document).encode(), document)
    _identity_reader(
        monkeypatch, contract["image"], json.dumps(envelope).encode(), json.dumps(local).encode()
    )
    with pytest.raises(runtime.ProbeError, match=message):
        runtime._admit_selected_image(contract["image"], manifest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("digest", "sha256:" + "0" * 64),
        ("mediaType", "application/vnd.docker.container.image.v1+json"),
        ("size", True),
        ("size", 1.0),
        ("size", 0),
        ("size", -1),
        ("size", "1"),
        ("size", None),
        ("extra", "unsupported"),
        ("missing", None),
        ("cross_pair", None),
    ],
)
def test_config_descriptor_requires_its_own_exact_witness(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    document = deepcopy(envelope["OCIManifest"])
    if field == "missing":
        del document["config"]["digest"]
    elif field == "cross_pair":
        _, other, _, _ = _identity_fixture("second")
        document["config"]["digest"] = other["config_digest"]
    else:
        document["config"][field] = value
    # Rebind all upstream bytes/hash/Ref/Descriptor prerequisites to target this check.
    _bind_identity_raw(contract, manifest, envelope, local, json.dumps(document).encode(), document)
    calls = _identity_reader(
        monkeypatch, contract["image"], json.dumps(envelope).encode(), json.dumps(local).encode()
    )
    with pytest.raises(runtime.ProbeError, match="config descriptor"):
        runtime._admit_selected_image(contract["image"], manifest)
    assert len(calls) == 1


@pytest.mark.parametrize("fault", ["bool", "float", "missing", "extra", "order", "value"])
def test_oci_projection_preserves_complete_values_array_order_and_json_types(
    monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    projection = envelope["OCIManifest"]
    if fault == "bool":
        projection["layers"][0]["size"] = True  # Python equality would equate this with 1.
    elif fault == "float":
        projection["schemaVersion"] = 2.0  # Python equality would equate this with 2.
    elif fault == "missing":
        del projection["layers"][0]["annotations"]
    elif fault == "extra":
        projection["extra"] = None
    elif fault == "order":
        projection["layers"].reverse()
    else:
        projection["layers"][0]["annotations"]["synthetic"] = "changed"
    _identity_reader(
        monkeypatch, contract["image"], json.dumps(envelope).encode(), json.dumps(local).encode()
    )
    with pytest.raises(runtime.ProbeError, match="OCI projection differs"):
        runtime._admit_selected_image(contract["image"], manifest)


@pytest.mark.parametrize("location", ["envelope", "raw", "local"])
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b'{"marker":"synthetic-private-marker",', id="malformed-json"),
        pytest.param(b'{"duplicate":1,"duplicate":2}', id="duplicate-keys"),
        pytest.param(b'{"value":NaN}', id="nan"),
        pytest.param(b'{"value":Infinity}', id="positive-infinity"),
        pytest.param(b'{"value":-Infinity}', id="negative-infinity"),
        pytest.param(b'{"value":1e999}', id="exponent-overflow"),
        pytest.param(b"\xffsynthetic-private-marker", id="invalid-utf8"),
    ],
)
def test_new_observations_contain_decode_and_nonfinite_failures(
    monkeypatch: pytest.MonkeyPatch, location: str, payload: bytes
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    registry = json.dumps(envelope).encode()
    inspected = json.dumps(local).encode()
    if location == "envelope":
        registry = payload
    elif location == "local":
        inspected = payload
    else:
        _bind_identity_raw(contract, manifest, envelope, local, payload, envelope["OCIManifest"])
        registry, inspected = json.dumps(envelope).encode(), json.dumps(local).encode()
    _identity_reader(monkeypatch, contract["image"], registry, inspected)
    with pytest.raises(runtime.ProbeError) as observed:
        runtime._admit_selected_image(contract["image"], manifest)
    assert str(observed.value) == "Native image identity observation is malformed or non-finite"
    assert "synthetic-private-marker" not in str(observed.value)


@pytest.mark.parametrize(
    "location,shape_error",
    [
        pytest.param(
            "envelope",
            "Native registry observation is not the supported single OCI envelope",
            id="envelope",
        ),
        pytest.param(
            "raw",
            "Native registry Raw is not the supported OCI image manifest",
            id="raw",
        ),
        pytest.param("local", "Native pulled image inspection is ambiguous", id="local"),
    ],
)
def test_real_deep_unsupported_json_has_a_constant_location_specific_hold(
    monkeypatch: pytest.MonkeyPatch, location: str, shape_error: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    payload = b'{"synthetic-private-marker":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"
    registry, inspected = json.dumps(envelope).encode(), json.dumps(local).encode()
    if location == "envelope":
        registry = payload
    elif location == "local":
        inspected = payload
    else:
        _bind_identity_raw(contract, manifest, envelope, local, payload, envelope["OCIManifest"])
        registry, inspected = json.dumps(envelope).encode(), json.dumps(local).encode()
    calls = _identity_reader(monkeypatch, contract["image"], registry, inspected)
    with pytest.raises(runtime.ProbeError) as observed:
        runtime._admit_selected_image(contract["image"], manifest)
    # A finite depth does not promise an interpreter-specific RecursionError.
    assert str(observed.value) in {
        shape_error,
        "Native image identity observation is malformed or non-finite",
    }
    assert "synthetic-private-marker" not in str(observed.value)
    assert len(calls) == (2 if location == "local" else 1)


@pytest.mark.parametrize(
    "observation_number",
    [pytest.param(1, id="envelope"), pytest.param(2, id="raw"), pytest.param(3, id="local")],
)
def test_decoder_recursion_error_has_only_the_constant_hold_diagnostic(
    monkeypatch: pytest.MonkeyPatch, observation_number: int
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    calls = _identity_reader(
        monkeypatch, contract["image"], json.dumps(envelope).encode(), json.dumps(local).encode()
    )
    real_decoder = runtime.source._read_json
    decoded = 0

    def decode(value: str) -> object:
        nonlocal decoded
        decoded += 1
        if decoded == observation_number:
            raise RecursionError("synthetic-private-marker")
        return real_decoder(value)

    monkeypatch.setattr(runtime.source, "_read_json", decode)
    with pytest.raises(runtime.ProbeError) as observed:
        runtime._admit_selected_image(contract["image"], manifest)
    assert str(observed.value) == "Native image identity observation is malformed or non-finite"
    assert "synthetic-private-marker" not in str(observed.value)
    assert decoded == observation_number
    assert len(calls) == (2 if observation_number == 3 else 1)


@pytest.mark.parametrize("location", ["envelope", "raw", "local"])
def test_exponent_overflow_in_otherwise_accepted_observation_fields_is_rejected(
    monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    if location == "envelope":
        envelope["OCIManifest"]["layers"][0]["annotations"]["overflow"] = float("inf")
    elif location == "local":
        local[0]["unconsumed"] = float("inf")
    else:
        document = deepcopy(envelope["OCIManifest"])
        document["layers"][0]["annotations"]["overflow"] = float("inf")
        raw = json.dumps(document).encode().replace(b"Infinity", b"1e999")
        _bind_identity_raw(contract, manifest, envelope, local, raw, envelope["OCIManifest"])
    registry = json.dumps(envelope).encode().replace(b"Infinity", b"1e999")
    inspected = json.dumps(local).encode().replace(b"Infinity", b"1e999")
    _identity_reader(monkeypatch, contract["image"], registry, inspected)
    with pytest.raises(runtime.ProbeError, match="malformed or non-finite"):
        runtime._admit_selected_image(contract["image"], manifest)


@pytest.mark.parametrize("location", ["envelope", "raw", "local"])
def test_image_observation_parser_admission_has_explicit_byte_bounds(
    monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    registry, inspected = json.dumps(envelope).encode(), json.dumps(local).encode()
    if location == "envelope":
        registry = b" " * (runtime.IMAGE_OBSERVATION_LIMIT + 1)
    elif location == "local":
        inspected = b" " * (runtime.IMAGE_OBSERVATION_LIMIT + 1)
    else:
        raw = b" " * (runtime.IMAGE_OBSERVATION_LIMIT // 2 + 1)
        _bind_identity_raw(contract, manifest, envelope, local, raw, envelope["OCIManifest"])
        registry, inspected = json.dumps(envelope).encode(), json.dumps(local).encode()
        assert len(registry) <= runtime.IMAGE_OBSERVATION_LIMIT
    _identity_reader(monkeypatch, contract["image"], registry, inspected)
    with pytest.raises(runtime.ProbeError, match="exceeds parser bounds"):
        runtime._admit_selected_image(contract["image"], manifest)


@pytest.mark.parametrize(
    "fault,message",
    [
        ("empty", "inspection is ambiguous"),
        ("multiple", "inspection is ambiguous"),
        ("object", "inspection is ambiguous"),
        ("member", "inspection is ambiguous"),
        ("digest_missing", "subject or platform"),
        ("digest_type", "subject or platform"),
        ("digest_member", "subject or platform"),
        ("foreign_repository", "subject or platform"),
        ("suffix", "subject or platform"),
        ("os", "subject or platform"),
        ("architecture", "subject or platform"),
        ("id_type", "Id differs"),
        ("cross_config", "Id differs"),
        ("cross_platform", "Id differs"),
    ],
)
def test_local_image_requires_the_same_canonical_subject_platform_and_pair(
    monkeypatch: pytest.MonkeyPatch, fault: str, message: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    observation: object = local
    if fault == "empty":
        observation = []
    elif fault == "multiple":
        observation = local * 2
    elif fault == "object":
        observation = local[0]
    elif fault == "member":
        observation = [None]
    elif fault == "digest_missing":
        del local[0]["RepoDigests"]
    elif fault == "digest_type":
        local[0]["RepoDigests"] = contract["image"]
    elif fault == "digest_member":
        local[0]["RepoDigests"].append(1)
    elif fault == "foreign_repository":
        local[0]["RepoDigests"] = ["ghcr.io/foreign/image@" + manifest["platform_manifest_digest"]]
    elif fault == "suffix":
        local[0]["RepoDigests"] = [contract["image"] + "suffix"]
    elif fault == "os":
        local[0]["Os"] = "windows"
    elif fault == "architecture":
        local[0]["Architecture"] = "arm64"
    elif fault == "id_type":
        local[0]["Id"] = []
    else:
        _, other, _, _ = _identity_fixture("second")
        local[0]["Id"] = other[
            "config_digest" if fault == "cross_config" else "platform_manifest_digest"
        ]
    _identity_reader(
        monkeypatch,
        contract["image"],
        json.dumps(envelope).encode(),
        json.dumps(observation).encode(),
    )
    with pytest.raises(runtime.ProbeError, match=message):
        runtime._admit_selected_image(contract["image"], manifest)


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "unavailable"])
def test_registry_observation_preserves_real_native_failure_despite_plausible_stdout(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    contract, manifest, envelope, _ = _identity_fixture()
    calls: list[list[str]] = []
    monkeypatch.setattr(
        runtime.shutil,
        "which",
        lambda name: None if failure == "unavailable" else "/resolved/docker",
    )

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        assert kwargs["timeout"] == 60 and kwargs["check"] is False
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 60)
        return subprocess.CompletedProcess(
            args, 23, json.dumps(envelope).encode(), b"reader failed"
        )

    monkeypatch.setattr(runtime.subprocess, "run", run)
    expected = subprocess.TimeoutExpired if failure == "timeout" else runtime.ProbeError
    with pytest.raises(expected):
        runtime._admit_selected_image(contract["image"], manifest)
    assert len(calls) == (0 if failure == "unavailable" else 1)
    if calls:
        assert calls[0] == [
            "/resolved/docker",
            "manifest",
            "inspect",
            "--verbose",
            contract["image"],
        ]


@pytest.mark.parametrize("fault", ["selection", "registry", "local", "registry_cleanup"])
def test_cli_identity_hold_precedes_native_resources_and_leaves_no_success_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fault: str
) -> None:
    contract, manifest, envelope, local = _identity_fixture()
    if fault == "selection":
        contract["image"] = "ghcr.io/owner/image:unselected"
    elif fault.startswith("registry"):
        del envelope["Raw"]
    else:
        local[0]["RepoDigests"] = []
    root = tmp_path / "source"
    selected = root / "deploy/postgres-pgvector/image-manifest.json"
    selected.parent.mkdir(parents=True)
    selected.write_text(json.dumps(manifest))
    output = tmp_path / "native-result.json"
    calls: list[list[str]] = []
    cleanups: list[str] = []

    def pki(directory: Path) -> Path:
        secrets = directory / "secrets"
        secrets.mkdir()
        (secrets / "postgres_password").write_text("synthetic-private-marker")
        return secrets

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        if args[:2] == ["openssl", "x509"]:
            data = b"synthetic-public-fingerprint"
        elif args[:2] == ["docker", "pull"]:
            assert args[-1] == contract["image"] and kwargs["timeout"] == 180
            data = b""
        elif args == ["docker", "manifest", "inspect", "--verbose", contract["image"]]:
            data = json.dumps(envelope).encode()
        else:
            assert args == ["docker", "image", "inspect", contract["image"]]
            data = json.dumps(local).encode()
        return subprocess.CompletedProcess(args, 0, data, b"")

    def cleanup(resources: dict[str, list[str]], owner: str) -> None:
        cleanups.append(owner)
        if fault == "registry_cleanup":
            raise runtime.ProbeError("secondary cleanup must not replace identity failure")

    monkeypatch.setattr(runtime, "create_pki", pki)
    monkeypatch.setattr(runtime, "native", native)
    monkeypatch.setattr(runtime, "cleanup", cleanup)
    monkeypatch.setattr(runtime, "render_contract", lambda root, selected: contract)
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    monkeypatch.setattr(
        runtime.sys,
        "argv",
        ["probe", "--repo-root", str(root), "--json-out", str(output)],
    )
    assert runtime.main() == 1
    assert not output.exists() and len(cleanups) == 1
    error = capsys.readouterr().err
    expected = (
        "selected image subject differs"
        if fault == "selection"
        else (
            "supported single OCI envelope"
            if fault.startswith("registry")
            else "local image subject or platform differs"
        )
    )
    assert "Native staging experiment HOLD:" in error and expected in error
    assert "synthetic-private-marker" not in error
    assert "secondary cleanup must not replace" not in error
    # No network/volume create, helper, Compose up, query or restore command is admitted.
    assert all(
        args[:2] in (["openssl", "x509"], ["docker", "pull"])
        or args[:4] == ["docker", "manifest", "inspect", "--verbose"]
        or args[:3] == ["docker", "image", "inspect"]
        for args in calls
    )
    image_calls = [args for args in calls if args[0] == "docker"]
    assert len(image_calls) == (0 if fault == "selection" else 3 if fault == "local" else 2)


def test_native_adapter_retains_real_command_image_hba_and_pgdata() -> None:
    rendered, manifest = selected_fixture()
    selected = runtime.selected_contract(rendered, manifest)
    assert selected["command"] == rendered["services"]["postgres"]["command"]
    # The selected image's native entrypoint owns exec postgres "$@".
    assert selected["command"][0] == "-c" and "postgres" not in selected["command"]
    assert selected["image"] == manifest["repository"] + "@" + manifest["platform_manifest_digest"]
    assert selected["compose_runtime_ref"] == manifest["runtime_ref"]
    assert selected["hba"] == str(ROOT / "deploy/postgres-pgvector/pg_hba.conf")
    assert selected["pgdata"] == rendered["services"]["postgres"]["environment"]["PGDATA"]


def test_digest_execution_does_not_relax_the_rendered_canonical_reference_contract() -> None:
    rendered, manifest = selected_fixture()
    digest_only = manifest["repository"] + "@" + manifest["platform_manifest_digest"]
    assert runtime.selected_contract(rendered, manifest)["image"] == digest_only
    rendered["services"]["postgres"]["image"] = digest_only
    with pytest.raises(runtime.ProbeError, match="selected immutable manifest"):
        runtime.selected_contract(rendered, manifest)


def test_native_entrypoint_rejects_a_second_postgres_executable() -> None:
    rendered, manifest = selected_fixture()
    rendered["services"]["postgres"]["command"].insert(0, "postgres")
    with pytest.raises(runtime.ProbeError, match="admitted TLS arguments"):
        runtime.selected_contract(rendered, manifest)


@pytest.mark.parametrize(
    "field,value",
    [
        ("image", "postgres:15-alpine"),
        ("platform", "linux/arm64"),
        ("command", []),
        ("command", ["postgres", 1]),
        ("volumes", []),
        ("volumes", None),
    ],
)
def test_native_adapter_rejects_unbound_or_malformed_source(field: str, value: object) -> None:
    rendered, manifest = selected_fixture()
    rendered["services"]["postgres"][field] = value
    with pytest.raises(ValueError):
        runtime.selected_contract(rendered, manifest)


@pytest.mark.parametrize("fault", ["data_mount", "pgdata"])
def test_native_adapter_denies_divergent_runtime_storage_contract(fault: str) -> None:
    rendered, manifest = selected_fixture()
    postgres = rendered["services"]["postgres"]
    if fault == "data_mount":
        postgres["volumes"][0]["target"] = "/wrong/data"
    else:
        postgres["environment"]["PGDATA"] = "/wrong/data"
    with pytest.raises(runtime.ProbeError):
        runtime.selected_contract(rendered, manifest)


def test_crash_waits_on_observed_transaction_before_kill_and_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    observations = iter(("0", "1"))

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, b"", b"")

    def query(container: str, sql: str, conn: str) -> subprocess.CompletedProcess[bytes]:
        assert "pg_stat_activity" in sql and "wait_event='PgSleep'" in sql
        assert "application_name=pulseplate_crash_" in conn
        return subprocess.CompletedProcess([], 0, next(observations).encode(), b"")

    monkeypatch.setattr(runtime, "native", native)
    monkeypatch.setattr(runtime, "query", query)
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(runtime, "wait_database", lambda container: calls.append(["ready"]))
    runtime.crash_at_transaction_barrier("owned-db", "a" * 32)
    assert "BEGIN; INSERT" in calls[0][-1] and "pg_sleep(120); COMMIT" in calls[0][-1]
    assert calls[1] == ["docker", "kill", "--signal", "KILL", "owned-db"]
    assert calls[2] == ["docker", "start", "owned-db"]


def test_cleanup_includes_stopped_owned_containers_and_rejects_unknown_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        output = b"unknown-container\n" if args[1:3] == ["container", "ls"] else b""
        return subprocess.CompletedProcess(args, 0, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    with pytest.raises(ValueError, match="ownership"):
        runtime.cleanup({"container": ["owned-db"], "volume": [], "network": []}, "owner")
    assert "--all" in calls[0] and "{{.Names}}" in calls[0]
    assert not any("rm" in args for args in calls)


def test_primary_failure_is_preserved_when_cleanup_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = runtime.ProbeError("primary native experiment")

    def pki(root: Path) -> Path:
        raise failure

    def cleanup(resources: dict, owner: str) -> None:
        raise runtime.ProbeError("secondary cleanup")

    monkeypatch.setattr(runtime, "create_pki", pki)
    monkeypatch.setattr(runtime, "cleanup", cleanup)
    with pytest.raises(runtime.ProbeError, match="primary native experiment") as observed:
        runtime.experiment(ROOT, {}, {})
    assert observed.value is failure


def test_configuration_precedes_publication_and_full_native_proof_precedes_promotion() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/cd.yml").read_text())
    job = workflow["jobs"]["staging-postgres-native-integration"]
    assert job["name"] == "PostgreSQL configuration admission"
    assert job["if"] == (
        "github.event_name == 'pull_request' || "
        "(github.event_name == 'push' && github.ref == 'refs/heads/main')"
    )
    assert job["permissions"] == {"contents": "read"}
    assert "environment" not in job
    assert job["needs"] == "postgres-pgvector-contract"
    text = json.dumps(job)
    for forbidden in (
        "DHI_",
        "SSH_",
        "secrets.",
        "GHCR_READ_TOKEN",
        "docker login",
        "manifest inspect",
        "docker pull",
        "continue-on-error",
        "--publish",
    ):
        assert forbidden not in text
    assert "scripts.ci.check_pgvector_attestations changes" in text
    config = next(step for step in job["steps"] if "--configure-only" in step.get("run", ""))
    assert config["if"] == "steps.native-material.outputs.changed == 'true'"
    assert "scripts.ci.check_staging_postgres_runtime --configure-only" in config["run"]
    artifact = next(step for step in job["steps"] if "with" in step and "path" in step["with"])
    assert artifact["with"]["path"] == "staging-postgres-configuration-result.json"
    publisher = workflow["jobs"]["postgres-pgvector-publish"]
    assert "staging-postgres-native-integration" in publisher["needs"]
    assert "needs.staging-postgres-native-integration.result == 'success'" in publisher["if"]
    steps = publisher["steps"]
    names = [step["name"] for step in steps]
    proof = "Execute real isolated PostgreSQL TLS crash restart and restore checks"
    assert (
        names.index("Verify candidate pullback, material provenance, SBOM, and runtime identity")
        < names.index(proof)
        < names.index("Promote verified candidate digest to canonical tag without rebuild")
    )
    native = steps[names.index(proof)]
    assert "if" not in native and "continue-on-error" not in native and "env" not in native
    assert "--configure-only" not in native["run"]
    assert "scripts.ci.check_staging_postgres_runtime" in native["run"]
    assert "--json-out staging-postgres-native-result.json" in native["run"]
    evidence = next(
        step for step in steps if step["name"] == "Upload PostgreSQL pgvector admission evidence"
    )
    assert "staging-postgres-native-result.json" in evidence["with"]["path"].splitlines()


def test_external_current_incomplete_tuple_control_precedes_spdx_and_complete_probe() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/cd.yml").read_text())
    steps = workflow["jobs"]["postgres-synthetic-attestation-probe"]["steps"]
    names = [step["name"] for step in steps]
    incomplete = names.index(
        "Reject the exact current incomplete native and materials tuple before SPDX"
    )
    assert (
        names.index("Attest synthetic exact materials")
        < incomplete
        < names.index("Attest synthetic SPDX")
    )
    assert names.index("Attest synthetic SPDX") < names.index(
        "Fresh-process external pullback repeat and source-rejection probe"
    )
    control = steps[incomplete]["run"]
    assert "--run-invocation-uri" in control and "if python3" in control and "exit 1" in control
    assert "continue-on-error" not in steps[incomplete]
    build = next(
        step["run"] for step in steps if step.get("name") == "Build and push tiny synthetic image"
    )
    assert 'export DOCKER_CONFIG="$config_dir"' in build
    assert 'printf \'DOCKER_CONFIG=%s\\n\' "$config_dir" >> "$GITHUB_ENV"' in build
    cleanup = steps[-1]["run"]
    assert 'docker --config "$DOCKER_CONFIG" logout ghcr.io' in cleanup
    assert 'scripts.ci.ghcr_attestation_credentials cleanup --directory "$DOCKER_CONFIG"' in cleanup
    assert 'success) exit "$cleanup_failed"' in cleanup
    assert "continue-on-error" not in steps[-1]


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "accept_corrupt",
        "accept_plaintext",
        "lose_committed",
        "wrong_version",
        "missing_archive_table",
        "bad_tls",
        "bad_cast",
        "bad_vector_version",
        "source_missing",
        "restart_missing",
        "restore_missing",
        "bad_dump_size",
        "negative_healthy_lost",
        "expired_accepted",
        "inspect_malformed",
        "inspect_wrong_config",
        "cleanup_pki",
        "wrapper_failure",
    ],
)
def test_driver_protocol_rejects_bad_outcomes_and_cleans_owned_resources(
    monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    contract, manifest, envelope, inspected = _identity_fixture()
    state: dict[str, Any] = {
        "container": None,
        "volume": None,
        "network": None,
        "sentinel": None,
        "expired": False,
        "crashed": False,
        "restarts": 0,
        "selects": 0,
        "negative_seen": False,
        "dump": b"PGDMP-disposable-native-oracle-archive",
    }
    calls = []
    if fault == "bad_dump_size":
        state["dump"] = b""

    def native(
        args: list[str], data: bytes | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        output, code = b"", 0
        if args[0] == "openssl":
            for flag in ("-keyout", "-out"):
                if flag in args:
                    Path(args[args.index(flag) + 1]).write_text("disposable-crypto-oracle")
            if "-fingerprint" in args:
                output = b"SHA256 Fingerprint=disposable-public-oracle"
        elif args[1:4] == ["manifest", "inspect", "--verbose"]:
            output = json.dumps(envelope).encode()
        elif args[1:3] == ["image", "inspect"]:
            local = deepcopy(inspected)
            if fault == "inspect_wrong_config":
                local[0]["Id"] = "wrong"
            output = json.dumps([] if fault == "inspect_malformed" else local).encode()
        elif args[1] in ("network", "volume") and args[2] == "create":
            state[args[1]] = args[-1]
        elif args[1] == "compose":
            assert args[-5:] == ["up", "--detach", "--pull", "never", "postgres"]
            state["compose"] = json.loads(Path(args[args.index("-f") + 1]).read_text())
            state["container"] = state["compose"]["services"]["postgres"]["container_name"]
        elif args[1] == "run":
            if fault == "cleanup_pki" and any("-ownership-restore" in value for value in args):
                raise runtime.ProbeError("Native private PKI cleanup denied")
            if "--detach" in args:
                state["container"] = args[args.index("--name") + 1]
            if "-ec" in args and "expired_server_crt /k/postgres_server_crt" in args[-1]:
                state["expired"] = True
        elif args[1] in ("container", "volume", "network") and args[2] == "ls":
            output = ((state[args[1]] + "\n") if state[args[1]] else "").encode()
        elif args[1] in ("container", "volume", "network") and args[2] == "rm":
            assert args[-1] == state[args[1]]
            state[args[1]] = None
        elif args[1] == "kill":
            state["crashed"] = True
        elif args[1] == "restart":
            state["restarts"] += 1
        elif args[1] == "exec" and "pg_dump" in args:
            output = state["dump"]
        elif args[1] == "exec" and "pg_restore" in args:
            if "--list" in args:
                output = (
                    b"214; 1259 16387 TABLE public staging_probe pulseplate_probe\n"
                    if fault != "missing_archive_table"
                    else b""
                )
            elif "--file=/dev/null" in args and data != state["dump"]:
                code = 0 if fault == "accept_corrupt" else 1
        elif args[1] == "exec" and "psql" in args:
            if "--command" in args:
                output = b""  # Detached open transaction starts; SQL barrier is observed below.
            else:
                sql = (data or b"").decode()
                conn = args[args.index("--dbname") + 1]
                if "sslmode=disable" in conn:
                    code = 0 if fault == "accept_plaintext" else 1
                    state["negative_seen"] = True
                elif "wrong_ca" in conn or "host=wrong.invalid" in conn or state["expired"]:
                    code = 0 if state["expired"] and fault == "expired_accepted" else 1
                elif "pg_stat_activity" in sql:
                    output = b"1\n"
                elif "pg_stat_ssl" in sql:
                    output = b"false:TLSv1.0" if fault == "bad_tls" else b"true:TLSv1.3\n"
                elif "SHOW server_version" in sql:
                    output = (
                        b"99.0\n"
                        if fault == "wrong_version"
                        else manifest["postgres_version"].encode()
                    )
                elif "SELECT extversion" in sql:
                    output = (
                        b"99.0"
                        if fault == "bad_vector_version"
                        else manifest["pgvector_version"].encode()
                    )
                elif "CREATE EXTENSION" in sql:
                    output = b"bad cast" if fault == "bad_cast" else b"[1,2,3]\n"
                elif "CREATE TABLE staging_probe" in sql:
                    value = args[args.index("--set") + 1]
                    assert value.startswith("sentinel=") and ":'sentinel'" in sql
                    state["sentinel"] = value.split("=", 1)[1]
                elif "FROM staging_probe" in sql:
                    state["selects"] += 1
                    output = (
                        "0:lost"
                        if (
                            (state["crashed"] and fault == "lose_committed")
                            or (fault == "source_missing" and state["selects"] == 1)
                            or (fault == "restart_missing" and state["restarts"] == 1)
                            or (
                                fault == "restore_missing"
                                and "dbname=pulseplate_restore_check_" in conn
                            )
                        )
                        else "1:" + state["sentinel"]
                    ).encode()
                else:
                    output = (
                        b"0"
                        if fault == "negative_healthy_lost" and state["negative_seen"]
                        else b"1\n"
                    )
        return subprocess.CompletedProcess(args, code, output, b"")

    def wrapper_checks(*args: Any) -> dict[str, bool]:
        calls.append(["wrapper-checks"])
        if fault == "wrapper_failure":
            raise runtime.ProbeError("Native wrapper controls rejected")
        return {"adapter_only": True}

    monkeypatch.setattr(runtime, "wrapper_restore_checks", wrapper_checks)
    monkeypatch.setattr(runtime, "native", native)
    if fault is None:
        result = runtime.experiment(ROOT, contract, manifest)
        assert result["live_deployment_sessions_and_do_encryption_claim"] is False
        assert result["process_crash_committed_survives_uncommitted_rolls_back"] is True
        assert result["isolated_restore_sentinel_count_equal"] is True
        assert len(result["fingerprint"]) == 64
    else:
        expected_error = {
            "accept_corrupt": "Native corrupted custom archive unexpectedly accepted",
            "accept_plaintext": "Native plaintext rejection unexpectedly succeeded",
            "lose_committed": "Process crash lost committed sentinel",
            "wrong_version": "Actual PostgreSQL binary version differs",
            "missing_archive_table": "Native custom dump does not contain",
            "bad_tls": "Actual TCP PostgreSQL session did not use required TLS",
            "bad_cast": "Native pgvector extension/cast failed",
            "bad_vector_version": "Actual pgvector extension version differs",
            "source_missing": "Synthetic source sentinel mismatch",
            "restart_missing": "Same-volume restart lost synthetic sentinel",
            "restore_missing": "Isolated native restore sentinel/count differs",
            "bad_dump_size": "Native custom dump size is outside",
            "negative_healthy_lost": (
                "Native TLS negative control lost its healthy positive baseline"
            ),
            "expired_accepted": "Expired native server certificate unexpectedly accepted",
            "inspect_malformed": "Native pulled image inspection is ambiguous",
            "inspect_wrong_config": (
                "Native local image Id differs from the witnessed selected tuple"
            ),
            "cleanup_pki": "Native private PKI cleanup denied",
            "wrapper_failure": "Native wrapper controls rejected",
        }[fault]
        with pytest.raises(runtime.ProbeError, match=expected_error):
            runtime.experiment(ROOT, contract, manifest)
    assert not state["container"] and not state["volume"] and not state["network"]
    assert not any("--publish" in args or "--privileged" in args for args in calls)
    expected_image = manifest["repository"] + "@" + manifest["platform_manifest_digest"]
    for args in calls:
        if (
            args[:2] == ["docker", "pull"]
            or args[:3] == ["docker", "image", "inspect"]
            or args[:4] == ["docker", "manifest", "inspect", "--verbose"]
        ):
            assert args[-1] == expected_image
        if args[:2] == ["docker", "run"]:
            assert args[args.index("-ec") - 1] == expected_image
    if "compose" in state:
        registry_call = ["docker", "manifest", "inspect", "--verbose", expected_image]
        assert calls.index(registry_call) < next(
            i for i, args in enumerate(calls) if args[1:3] == ["network", "create"]
        )
        service = state["compose"]["services"]["postgres"]
        assert service["image"] == expected_image
        assert service["command"] == contract["command"]
        assert "ports" not in service and "entrypoint" not in service
        assert "PGHOST" not in service["environment"]  # Native init uses its socket-only server.
        assert runtime.USER != runtime.DATABASE
        if fault is not None and fault != "cleanup_pki":
            diagnostics = next(
                i for i, args in enumerate(calls) if args[1:3] == ["container", "inspect"]
            )
            removal = next(i for i, args in enumerate(calls) if args[1:3] == ["container", "ls"])
            assert diagnostics < removal


def test_native_command_adapter_requires_resolved_binary_and_preserves_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    with pytest.raises(runtime.ProbeError, match="unavailable"):
        runtime.native(["docker", "info"])
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/resolved/docker")

    def run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert args[0] == "/resolved/docker" and kwargs["timeout"] == 60
        return subprocess.CompletedProcess(args, 23, b"", b"private output not logged")

    monkeypatch.setattr(runtime.subprocess, "run", run)
    assert runtime.native(["docker", "info"], required=False).returncode == 23
    with pytest.raises(runtime.ProbeError, match="exit 23"):
        runtime.native(["docker", "info"])


def test_render_uses_native_compose_with_synthetic_variables_and_real_source_asset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered, manifest = selected_fixture()
    monkeypatch.setenv("PROMETHEUS_RUNTIME_REF", "parent-conflicting-prometheus-ref")

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert "compose" in args and "--no-env-resolution" in args
        assert kwargs["environment"]["POSTGRES_USER"] == runtime.USER
        assert kwargs["environment"]["STAGING_ENV_FILE"] == "/dev/null"
        assert kwargs["environment"]["PROMETHEUS_RUNTIME_REF"] == manifest["runtime_ref"]
        return subprocess.CompletedProcess(args, 0, json.dumps(rendered).encode(), b"")

    monkeypatch.setattr(runtime, "native", native)
    assert (
        runtime.render_contract(ROOT, manifest)["command"]
        == rendered["services"]["postgres"]["command"]
    )
    rendered["services"]["postgres"]["volumes"][1]["source"] = "/untrusted/hba"
    with pytest.raises(runtime.ProbeError, match="real regular"):
        runtime.render_contract(ROOT, manifest)


@pytest.mark.parametrize("barrier", [False, True])
def test_readiness_and_transaction_barrier_expire_without_faulting_unobserved_state(
    monkeypatch: pytest.MonkeyPatch, barrier: bool
) -> None:
    clock = iter((0.0, 1.0, 100.0))
    calls = []
    monkeypatch.setattr(runtime.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        runtime, "query", lambda *args, **kwargs: subprocess.CompletedProcess([], 1, b"0", b"")
    )
    monkeypatch.setattr(runtime, "native", lambda args, **kwargs: calls.append(args))
    with pytest.raises(runtime.ProbeError):
        if barrier:
            runtime.crash_at_transaction_barrier("owned", "a" * 32)
        else:
            runtime.wait_database("owned")
    assert not any("kill" in args for args in calls)


@pytest.mark.parametrize("fault", ["census", "remove"])
def test_native_cleanup_failures_are_blocking(monkeypatch: pytest.MonkeyPatch, fault: str) -> None:
    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        output = b"owned\n" if args[1:3] == ["container", "ls"] and fault == "remove" else b""
        code = 1 if (args[2] == "ls" and fault == "census") or args[2] == "rm" else 0
        return subprocess.CompletedProcess(args, code, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    with pytest.raises(runtime.ProbeError):
        runtime.cleanup({"container": ["owned"], "volume": [], "network": []}, "owner")


@pytest.mark.parametrize("mode", ["configure", "linux", "nonlinux", "error"])
def test_cli_keeps_configuration_and_native_execution_claims_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    rendered, manifest = selected_fixture()
    monkeypatch.setattr(
        runtime,
        "render_contract",
        lambda root, selected: runtime.selected_contract(rendered, selected),
    )
    output = tmp_path / "result.json"
    arguments = ["probe", "--repo-root", str(ROOT), "--json-out", str(output)] + (
        ["--configure-only"] if mode == "configure" else []
    )
    monkeypatch.setattr(runtime.sys, "argv", arguments)
    monkeypatch.setattr(
        runtime.sys, "platform", "linux" if mode in ("linux", "error") else "darwin"
    )
    experiment_calls: list[str] = []

    def forbidden_native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise AssertionError("CLI must not add image operations outside the native experiment")

    def experiment(root: Path, contract: dict, selected: dict) -> dict:
        experiment_calls.append("experiment")
        if mode == "error":
            raise runtime.ProbeError("native rejected")
        return {"native_execution": True}

    monkeypatch.setattr(runtime, "experiment", experiment)
    monkeypatch.setattr(runtime, "native", forbidden_native)
    assert runtime.main() == (1 if mode in ("nonlinux", "error") else 0)
    assert experiment_calls == ([] if mode in ("configure", "nonlinux") else ["experiment"])
    if mode in ("nonlinux", "error"):
        assert not output.exists()
    else:
        record = json.loads(output.read_text())
        assert record.get("configure_only", False) is (mode == "configure")


def test_native_diagnostics_are_bounded_redacted_and_omit_stdout_argv_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/resolved/docker")
    secret = "opaque" + "_native" + "_diagnostic"
    stderr = (
        "TLS certificate verification failed GH_TOKEN="
        + secret
        + " https://user:"
        + secret
        + "@registry.invalid Bearer "
        + secret
        + " -----BEGIN PRIVATE KEY-----\n"
        + secret
        + "\n-----END PRIVATE KEY----- "
        + "x" * 1000
    )
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 7, b"binary-stdout-private-data", stderr.encode()
        ),
    )
    with pytest.raises(runtime.ProbeError) as failure:
        runtime.native(["docker", "exec", "private-container-identifier", "private-argument"])
    message = str(failure.value)
    assert "Native docker exec" in message and "TLS certificate verification failed" in message
    assert len(message) < 600
    for value in (
        secret,
        "binary-stdout-private-data",
        "private-container-identifier",
        "private-argument",
    ):
        assert value not in message


@pytest.mark.parametrize("owned", [True, False])
def test_failure_diagnostics_read_only_owned_state_and_bounded_redacted_logs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], owned: bool
) -> None:
    calls = []
    probe_value = "ephemeral-diagnostic-control"

    def native(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        assert kwargs == {"required": False, "timeout": 10}
        if "--format" in args and ".Config.Labels" in args[-2]:
            output = json.dumps("owner" if owned else "someone-else").encode()
        elif "--format" in args:
            assert all(
                field in args[-2]
                for field in (".State.Status", ".State.OOMKilled", ".State.ExitCode")
            )
            assert ".Config.Env" not in args[-2] and ".State.Health" not in args[-2]
            output = b'{"status":"exited","oom_killed":false,"exit_code":1}'
        else:
            assert args == ["docker", "logs", "--tail", "64", "owned-db"]
            output = (
                "ENTRYPOINT startup failed "
                + probe_value
                + " GH_TOKEN="
                + probe_value
                + "\n-----BEGIN PRIVATE KEY-----\nprivate-key-data\n-----END PRIVATE KEY-----\n"
                + "x" * 20_000
            ).encode()
        return subprocess.CompletedProcess(args, 0, output, b"")

    monkeypatch.setattr(runtime, "native", native)
    runtime.diagnose_container("owned-db", "owner", (probe_value,))
    captured = capsys.readouterr().err
    assert len(captured) < 10_000
    assert probe_value not in captured and "private-key-data" not in captured
    if owned:
        assert len(calls) == 3 and "ENTRYPOINT startup failed" in captured
        assert '"exit_code":1' in captured.replace('\\"', '"')
    else:
        assert len(calls) == 1 and "ownership unconfirmed" in captured


def test_readiness_failure_retains_last_query_exit_and_redacted_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((0.0, 1.0, 100.0))
    monkeypatch.setattr(runtime.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runtime.time, "sleep", lambda _: None)
    monkeypatch.setattr(
        runtime,
        "query",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 7, b"do-not-publish-query-data", b"could not connect GH_TOKEN=opaque-test-token"
        ),
    )
    with pytest.raises(runtime.ProbeError) as failed:
        runtime.wait_database("owned-db")
    assert "exit=7" in str(failed.value) and "could not connect" in str(failed.value)
    assert "opaque-test-token" not in str(failed.value)
    assert "do-not-publish-query-data" not in str(failed.value)


@pytest.fixture
def wrapper_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Finite command outputs test helper decisions, never native DB execution."""
    compose_file = tmp_path / "compose.native.json"
    compose_file.write_text("{}")
    state: dict[str, Any] = {
        "fault": None,
        "cleanup_fault": None,
        "owner": "a" * 32,
        "source_owner": "default",
        "bad_sql": False,
        "private_source": False,
        "targets": {},
        "calls": [],
        "backups": 0,
        "decoded": [],
        "primary": runtime.ProbeError("Original wrapper command error"),
    }
    monkeypatch.setattr(runtime.shutil, "which", lambda name: "/resolved/" + name)

    def completed(
        args: list[str], output: bytes = b"", code: int = 0, error: bytes = b""
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args, code, output, error)

    def native(
        args: list[str], data: bytes | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        state["calls"].append((args, kwargs))
        fault = state["fault"]
        if args[0] == "bash":
            env = kwargs["environment"]
            assert Path(args[1]).is_absolute()
            assert env["PROJECT_DIR"] == str(tmp_path) and env["COMPOSE_FILE"] == str(compose_file)
            assert env["POSTGRES_USER"] == runtime.USER and env["POSTGRES_DB"] == runtime.DATABASE
            assert env["ENV_FILE"] == "/dev/null" and env["DOCKER_BIN"] == "/resolved/docker"
            assert env["PROMETHEUS_IMAGE_MANIFEST"] == str(
                Path(args[1]).parents[2] / "deploy/prometheus/image-manifest.json"
            )
            assert kwargs["timeout"] == 120
            assert not any(key.startswith("PG") for key in env)
            assert "COMPOSE_PROJECT_NAME" not in env
            if args[1].endswith("postgres_backup.sh"):
                if fault == "backup-error":
                    raise state["primary"]
                state["backups"] += 1
                tag = (
                    "nonpublic"
                    if state["private_source"]
                    else "failing" if state["bad_sql"] else state["source_owner"]
                )
                backup_dir = Path(env["BACKUP_DIR"])
                path = backup_dir / f"pulseplate_{state['backups']}.dump"
                if fault != "backup-absent":
                    path.write_bytes(tag.encode())
                    path.chmod(0o600)
                if fault == "backup-multiple":
                    (backup_dir / "pulseplate_extra.dump").write_bytes(b"default")
                elif fault == "backup-mode":
                    path.chmod(0o644)
                elif fault == "backup-empty":
                    path.write_bytes(b"")
                elif fault == "backup-large":
                    with path.open("r+b") as stream:
                        stream.truncate(64 * 1024**2 + 1)
                elif fault == "backup-link":
                    os.link(path, backup_dir / "extra-link")
                elif fault == "backup-symlink":
                    real = backup_dir / "real-dump"
                    path.rename(real)
                    path.symlink_to(real)
                elif fault == "backup-residue":
                    (backup_dir / ".pulseplate-backup.residue").mkdir()
                output = "Backup created: " + str(path)
                if fault == "backup-receipt":
                    output += " extra output"
                return completed(args, (output + "\n").encode())
            assert args[1].endswith("postgres_restore.sh")
            mode, target, archive = args[2], args[3], Path(args[4]).read_bytes()
            assert mode == "--verify-into" and target.startswith("pulseplate_restore_check_")
            if target in state["targets"]:
                if fault == "verify-mutates-existing":
                    state["targets"][target]["mutated"] = True
                kind = next(
                    (
                        kind
                        for kind in ("ordinary", "publication", "nonpublic", "global")
                        if "occupied_" + kind in target
                    ),
                    None,
                )
                if kind and fault == "occupied-" + kind + "-mutates":
                    state["targets"][target]["mutated"] = True
                return completed(
                    args,
                    b"Restore completed" if fault == "occupied-success-output" and kind else b"",
                    (
                        0
                        if fault == "verify-accepts-existing"
                        or fault == "occupied-" + str(kind) + "-accepts"
                        else 1
                    ),
                    (
                        b"connection failed"
                        if fault == "occupied-other-rejection" and kind
                        else b"database already exists"
                    ),
                )
            database = {
                "old": False,
                "private": archive == b"nonpublic",
                "mutated": False,
                "archive": archive,
            }
            state["targets"][target] = database
            if archive == b"failing":
                database["empty"] = fault != "rollback-partial-target"
                if fault == "rollback-original-mutates":
                    original = next(name for name in state["targets"] if "check_original_" in name)
                    state["targets"][original]["mutated"] = True
                if fault == "rollback-source-mutates":
                    state["source_mutated"] = True
                if fault == "rollback-source-layout-mutates":
                    state["source_layout_mutated"] = True
                return completed(
                    args,
                    b"Restore completed" if fault == "rollback-success-output" else b"",
                    0 if fault == "rollback-accepts" else 3,
                    (
                        b"authentication failed"
                        if fault == "rollback-other-rejection"
                        else b"synthetic restore index failure"
                    ),
                )
            return completed(args)
        assert args[:2] == ["docker", "exec"]
        if "createdb" in args:
            assert args[args.index("--maintenance-db") + 1] == runtime.DATABASE
            assert args[args.index("-U") + 1] == runtime.USER
            state["targets"][args[-1]] = {"old": True, "private": False, "mutated": False}
            return completed(args)
        if "pg_dump" in args:
            assert "--schema=public" in args
            return completed(args, b"definition")
        assert "pg_restore" in args
        if "--file=/dev/null" in args:
            if fault == "backup-decode":
                raise runtime.ProbeError("Native archive decoder rejected")
            state["decoded"].append(data)
            return completed(args)
        tag = (data or b"").decode()
        has_record = tag != "default"
        if fault == "shape-omitted" and tag == "default":
            has_record = True
        if fault == "shape-metadata-only" and tag == "metadata":
            has_record = False
        if "--list" in args:
            output = "214; 1259 16387 TABLE public staging_probe pulseplate_probe\n"
            if has_record:
                output = "5; 2615 2200 SCHEMA - public pulseplate_probe\n" + output
            return completed(args, output.encode())
        assert "--clean" in args and "--if-exists" in args and "--file=-" in args
        sql = (
            "CREATE SCHEMA public;\n"
            if tag == "definition" and fault != "shape-definition"
            else "-- no schema CREATE\n"
        )
        return completed(args, sql.encode())

    def query(
        container: str, sql: str, conn: str | None = None, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        state["calls"].append((["query", sql, conn or "source"], kwargs))
        fault = state["fault"]
        database_name = (
            runtime.DATABASE
            if conn is None
            else next(
                token.removeprefix("dbname=")
                for token in conn.split()
                if token.startswith("dbname=")
            )
        )
        if sql.startswith("DROP INDEX IF EXISTS"):
            state["cleaned"] = True
            if state["cleanup_fault"] == "exception":
                raise runtime.ProbeError("Cleanup adapter raised")
            return completed([], code=7 if state["cleanup_fault"] == "exit" else 0)
        if database_name == "template1":
            if sql.startswith("CREATE TABLE public.wrapper_template1_only"):
                state["template1_contaminated"] = True
            elif sql.startswith("DROP TABLE IF EXISTS public.wrapper_template1_only"):
                state["template1_cleaned"] = True
            else:
                raise AssertionError(sql)
            return completed([])
        if database_name == runtime.DATABASE:
            if "SELECT coalesce(obj_description" in sql:
                return completed([], b"native public comment")
            if "SELECT tablename" in sql:
                return completed(
                    [],
                    (
                        b"staging_probe\nt|t"
                        if not state.get("source_layout_mutated")
                        else b"extra\nstaging_probe\nf|t"
                    ),
                )
            if "FROM public.staging_probe" in sql:
                return completed(
                    [], b"0:missing" if state.get("source_mutated") else b"1:source-sentinel"
                )
            if "FROM pg_database" in sql:
                assert "datname=:'role'" in sql
                assert kwargs["variables"] == {"role": runtime.USER}
                return completed([], b"1" if fault == "role-database-exists" else b"0")
            if sql == "ALTER SCHEMA public OWNER TO " + runtime.USER + ";":
                state["source_owner"] = "metadata"
            elif sql == "ALTER SCHEMA public OWNER TO pg_database_owner;":
                state["source_owner"] = "default"
            elif sql.startswith("CREATE FUNCTION public.wrapper_restore_key"):
                state["bad_sql"] = True
            elif sql.startswith("DROP INDEX public.wrapper_restore_failure_idx"):
                state["bad_sql"] = False
            elif sql.startswith("CREATE SCHEMA private_wrapper"):
                state["private_source"] = True
            elif sql == "SELECT id FROM private_wrapper.hidden;":
                return completed([], b"9" if state["private_source"] else b"lost")
            elif "WHERE pubname='wrapper_source_all'" in sql:
                return completed([], b"t" if state["private_source"] else b"f")
            return completed([])
        database = state["targets"][database_name]
        if sql.startswith("CREATE TABLE public.wrapper_original"):
            assert "VALUES(1,:'old_payload')" in sql
            assert kwargs["variables"] == {"old_payload": "old_" + "a" * 16}
            return completed([])
        if sql.startswith("CREATE SCHEMA private_wrapper"):
            database["private"] = True
            return completed([])
        if sql.startswith("CREATE PUBLICATION"):
            database["publication"] = True
            return completed([])
        if sql.startswith("CREATE FOREIGN DATA WRAPPER"):
            database["global"] = True
            return completed([])
        if sql == "SELECT 1;":
            return completed([], b"1")
        if "SELECT nspname FROM" in sql:
            return completed(
                [],
                str(
                    (database.get("private"), database.get("publication"), database.get("global"))
                ).encode(),
            )
        if "SELECT id FROM private_wrapper.hidden" in sql:
            return completed(
                [],
                (
                    b"9"
                    if database["private"]
                    and (fault != "full-private-lost" or "occupied" in database_name)
                    else b"lost"
                ),
            )
        if "WHERE pubname='wrapper_source_all'" in sql:
            return completed([], b"f" if fault == "full-publication-lost" else b"t")
        if "FROM public.wrapper_original" in sql:
            return completed(
                [], b"original-data-and-objects" if not database["mutated"] else b"mutated-data"
            )
        if "FROM public.staging_probe" in sql:
            if database["mutated"] or fault == "verification-missing":
                return completed([], b"0:missing")
            return completed([], b"1:source-sentinel")
        if "SELECT count(*) FROM pg_catalog.pg_tables" in sql:
            if fault == "rollback-function-retained":
                return completed([], b"0\nf|t")
            return completed([], b"0\nt|t" if database.get("empty") else b"1\nt|t")
        if "SELECT coalesce(obj_description" in sql:
            return completed(
                [],
                b"wrong metadata" if fault == "verification-metadata" else b"native public comment",
            )
        if "SELECT pg_get_userbyid(nspowner)" in sql:
            owner = "pg_database_owner" if database["archive"] == b"default" else runtime.USER
            return completed(
                [], ("wrong-owner" if fault == "verification-owner" else owner).encode()
            )
        if "wrapper_template1_only" in sql:
            assert state["template1_contaminated"]
            return completed([], b"f" if fault == "template1-inherited" else b"t")
        assert "SELECT tablename" in sql
        tables = {"verification-extra": b"extra\nstaging_probe", "verification-no-tables": b""}
        return completed([], tables.get(fault, b"staging_probe"))

    monkeypatch.setattr(runtime, "native", native)
    monkeypatch.setattr(runtime, "query", query)
    state["run"] = lambda: runtime.wrapper_restore_checks(
        ROOT, tmp_path, "owned-db", state["owner"], compose_file
    )
    return state


def test_wrapper_helper_adapter_accepts_only_complete_observed_controls(
    wrapper_adapter: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PGHOST", "unrelated-host")
    monkeypatch.setenv("COMPOSE_PROJECT_NAME", "unrelated-project")
    results = wrapper_adapter["run"]()
    assert len(results) == 13 and all(value is True for value in results.values())
    assert all(
        results["wrapper_fresh_restore_schema_" + shape]
        for shape in ("omitted", "metadata_only", "definition")
    )
    assert b"failing" in wrapper_adapter["decoded"]
    assert wrapper_adapter["cleaned"]
    restores = [
        args
        for args, _ in wrapper_adapter["calls"]
        if args[0] == "bash" and args[1].endswith("postgres_restore.sh")
    ]
    assert all(args[2] == "--verify-into" for args in restores)
    assert len(restores) == 12
    assert wrapper_adapter["template1_contaminated"] and wrapper_adapter["template1_cleaned"]
    assert runtime.USER != runtime.DATABASE


@pytest.mark.parametrize(
    "fault",
    [
        "backup-absent",
        "backup-multiple",
        "backup-mode",
        "backup-empty",
        "backup-large",
        "backup-link",
        "backup-symlink",
        "backup-residue",
        "backup-receipt",
        "backup-decode",
    ],
)
def test_wrapper_helper_rejects_invalid_actual_wrapper_publication_outputs(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="backup|decoder"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]
    assert not any(
        args[0] == "bash" and args[1].endswith("postgres_restore.sh")
        for args, _ in wrapper_adapter["calls"]
    )


@pytest.mark.parametrize("shape", ["omitted", "metadata-only", "definition"])
def test_wrapper_helper_rejects_misclassified_native_schema_shapes(
    wrapper_adapter: dict[str, Any], shape: str
) -> None:
    wrapper_adapter["fault"] = "shape-" + shape
    with pytest.raises(runtime.ProbeError, match="schema shape"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize(
    "fault",
    [
        "rollback-accepts",
        "rollback-other-rejection",
        "rollback-partial-target",
        "rollback-original-mutates",
        "rollback-source-mutates",
        "rollback-source-layout-mutates",
        "rollback-function-retained",
        "rollback-success-output",
    ],
)
def test_wrapper_helper_requires_expected_late_sql_failure_and_exact_retention(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="late SQL failure"):
        wrapper_adapter["run"]()
    assert b"failing" in wrapper_adapter["decoded"]
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize(
    "fault",
    [
        *[
            "occupied-" + kind + "-" + action
            for kind in ("ordinary", "publication", "nonpublic", "global")
            for action in ("accepts", "mutates")
        ],
        "occupied-other-rejection",
        "occupied-success-output",
    ],
)
def test_wrapper_helper_requires_occupied_target_refusal_and_preservation(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="occupied"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize("fault", ["full-private-lost", "full-publication-lost"])
def test_wrapper_helper_requires_full_archive_represented_objects(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError, match="full archive"):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize(
    "fault",
    [
        "role-database-exists",
        "verify-accepts-existing",
        "verify-mutates-existing",
        "verification-missing",
        "verification-extra",
        "verification-no-tables",
        "verification-owner",
        "verification-metadata",
        "template1-inherited",
    ],
)
def test_wrapper_helper_rejects_missing_maintenance_or_fresh_restore_evidence(
    wrapper_adapter: dict[str, Any], fault: str
) -> None:
    wrapper_adapter["fault"] = fault
    with pytest.raises(runtime.ProbeError):
        wrapper_adapter["run"]()
    assert wrapper_adapter["cleaned"]


@pytest.mark.parametrize("cleanup_fault", ["exit", "exception"])
def test_wrapper_helper_cleanup_failure_preserves_original_command_error(
    wrapper_adapter: dict[str, Any], capsys: pytest.CaptureFixture[str], cleanup_fault: str
) -> None:
    wrapper_adapter["fault"], wrapper_adapter["cleanup_fault"] = "backup-error", cleanup_fault
    with pytest.raises(runtime.ProbeError) as failed:
        wrapper_adapter["run"]()
    assert failed.value is wrapper_adapter["primary"]
    assert "cleanup also failed; primary failure preserved" in capsys.readouterr().err


@pytest.mark.parametrize("cleanup_fault", ["exit", "exception"])
def test_wrapper_helper_cleanup_failure_without_prior_error_remains_blocking(
    wrapper_adapter: dict[str, Any], cleanup_fault: str
) -> None:
    wrapper_adapter["cleanup_fault"] = cleanup_fault
    with pytest.raises(runtime.ProbeError, match="cleanup|Cleanup"):
        wrapper_adapter["run"]()


@pytest.mark.parametrize("fault", ["same-role-database", "invalid-owner", "missing-docker"])
def test_wrapper_helper_start_boundaries_precede_native_operations(
    wrapper_adapter: dict[str, Any], monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    if fault == "same-role-database":
        monkeypatch.setattr(runtime, "DATABASE", runtime.USER)
    elif fault == "invalid-owner":
        wrapper_adapter["owner"] = "untrusted-owner"
    else:
        monkeypatch.setattr(runtime.shutil, "which", lambda name: None)
    with pytest.raises(runtime.ProbeError):
        wrapper_adapter["run"]()
    assert wrapper_adapter["calls"] == []

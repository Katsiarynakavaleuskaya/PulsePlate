"""Offline security contracts for the hosted metadata-only source qualifier."""

from __future__ import annotations

from dataclasses import replace
import copy
from email.message import Message
import gzip
import io
import json
from pathlib import Path
import signal
import tarfile
from typing import Any
from urllib.request import HTTPSHandler, ProxyHandler, build_opener
from urllib.response import addinfourl

import pytest

from scripts.ci import prometheus_source_image as source


def _finite_vendor_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, wrong_diff: bool = False
) -> Path:
    """Synthetic graph data only; no native format, origin or build-success fixture."""
    layout = tmp_path / "vendor"
    (layout / "blobs/sha256").mkdir(parents=True)
    contracts = []
    for index in range(13):
        stream = io.BytesIO()
        rows = []
        with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            names = ("usr", "usr/bin", "etc", "bin") if index == 0 else (f"vendor-{index}",)
            for name in names:
                member = tarfile.TarInfo(name)
                data = ("synthetic vendor " + str(index)).encode()
                if index == 0:
                    member.type = tarfile.SYMTYPE if name == "bin" else tarfile.DIRTYPE
                    member.linkname = "usr/bin" if name == "bin" else ""
                    member.mode = 0o777 if name == "bin" else 0o755
                    data = b""
                else:
                    member.mode, member.size = 0o644, len(data)
                archive.addfile(member, io.BytesIO(data) if member.isreg() else None)
                row = {
                    "name": name,
                    "type": member.type.decode(),
                    "size": member.size,
                    "mode": member.mode,
                    "linkname": member.linkname,
                }
                if member.isreg():
                    row["sha256"] = source.sha(data)
                rows.append(row)
        raw = stream.getvalue()
        compressed = gzip.compress(raw, mtime=0)
        descriptor = {
            "mediaType": source.OCI_LAYER,
            "digest": "sha256:" + source.sha(compressed),
            "size": len(compressed),
        }
        (layout / "blobs/sha256" / descriptor["digest"][7:]).write_bytes(compressed)
        contracts.append(
            {
                "descriptor": descriptor,
                "diff_id": "sha256:" + source.sha(raw),
                "expanded": len(raw),
                "members": len(rows),
                "inventory_sha256": source.sha(
                    json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
                ),
            }
        )
    if wrong_diff:
        contracts[0]["diff_id"] = "sha256:" + "f" * 64
    config = {
        "architecture": "amd64",
        "os": "linux",
        "created": "1970-01-01T00:00:00Z",
        "config": {"User": "65532", "WorkingDir": "/home/nonroot", "Env": ["PATH=/usr/bin:/bin"]},
        "rootfs": {"type": "layers", "diff_ids": [row["diff_id"] for row in contracts]},
        "history": [
            {"created": "1970-01-01T00:00:00Z", "created_by": f"vendor {i}"} for i in range(13)
        ],
    }
    config_raw = json.dumps(config).encode()
    assert len(config_raw) < 2938
    config_raw += b" " * (2938 - len(config_raw))
    config_digest = "sha256:" + source.sha(config_raw)
    (layout / "blobs/sha256" / config_digest[7:]).write_bytes(config_raw)
    manifest = {
        "schemaVersion": 2,
        "mediaType": source.OCI_MANIFEST,
        "config": {"mediaType": source.OCI_CONFIG, "size": 2938, "digest": config_digest},
        "layers": [row["descriptor"] for row in contracts],
        "annotations": {"org.opencontainers.image.source": "synthetic"},
    }
    raw = json.dumps(manifest).encode()
    digest = "sha256:" + source.sha(raw)
    (layout / "blobs/sha256" / digest[7:]).write_bytes(raw)
    (layout / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}')
    (layout / "index.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.index.v1+json",
                "manifests": [
                    {"mediaType": source.OCI_MANIFEST, "size": len(raw), "digest": digest}
                ],
            }
        )
    )
    monkeypatch.setattr(source, "BASE", "gcr.io/distroless/static-debian13@" + digest)
    monkeypatch.setattr(source, "BASE_CONFIG", config_digest)
    monkeypatch.setattr(source, "BASE_LAYER_CONTRACTS", contracts)
    return layout


def _finite_constructed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    vendor = _finite_vendor_input(tmp_path, monkeypatch)
    base = source.base_graph(vendor)
    files = {
        name: ("synthetic-format-only " + name).encode()
        for name in ("prometheus", "promtool", "prometheus.yml", "LICENSE", "NOTICE")
    }
    layout, docker = tmp_path / "candidate", tmp_path / "candidate.docker.tar"
    result = source.construct_image(base, files, layout, docker, synthetic=True)
    return base, layout, docker, result


def test_finite_vendor_keeps_known_alias_and_never_extracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _finite_vendor_input(tmp_path, monkeypatch)
    result = source.base_graph(layout)
    assert len(result["layers"]) == 13
    assert not (layout / "bin").exists() and not (layout / "usr").exists()
    (layout / "blobs/sha256" / ("e" * 64)).write_bytes(b"extra")
    with pytest.raises(source.QualificationError, match="layout_closed_inventory"):
        source.base_graph(layout)


def test_finite_vendor_recomputes_diffID_instead_of_trusting_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _finite_vendor_input(tmp_path, monkeypatch, wrong_diff=True)
    with pytest.raises(source.QualificationError, match="vendor_independent_diffID"):
        source.base_graph(layout)


def test_finite_constructor_has_one_payload_and_distinct_transport_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, layout, docker, result = _finite_constructed(tmp_path, monkeypatch)
    graph = source.validate_oci_graph(layout, base, synthetic=True)
    source.validate_docker_archive(docker, graph)
    assert len(graph["layers"]) == len(graph["diff_ids"]) == 14
    assert result["synthetic_format_only"] is True
    assert graph["manifest_digest"] != graph["config_digest"]
    assert result["docker_archive_sha256"] != graph["manifest_digest"][7:]
    with tarfile.open(fileobj=io.BytesIO(graph["expanded_layers"][-1]), mode="r:") as archive:
        names = [member.name for member in archive.getmembers()]
        assert names == [
            "etc/prometheus",
            "prometheus",
            "LICENSE",
            "NOTICE",
            "etc/prometheus/prometheus.yml",
            "usr/bin/prometheus",
            "usr/bin/promtool",
        ]
        assert not {"bin", "usr", "usr/bin", "etc"}.intersection(names)


@pytest.mark.parametrize(
    "fault",
    ["extra_blob", "extra_directory", "changed_blob", "duplicate_index", "multiple_descriptors"],
)
def test_finite_graph_rejects_unreachable_or_conflicting_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    base, layout, _docker, result = _finite_constructed(tmp_path, monkeypatch)
    if fault == "extra_blob":
        (layout / "blobs/sha256" / ("a" * 64)).write_bytes(b"extra")
    elif fault == "extra_directory":
        (layout / "extra").mkdir()
    elif fault == "changed_blob":
        (layout / "blobs/sha256" / result["config_digest"][7:]).write_bytes(b"corrupt")
    elif fault == "duplicate_index":
        (layout / "index.json").write_text('{"schemaVersion":2,"schemaVersion":2}')
    else:
        index = json.loads((layout / "index.json").read_bytes())
        index["manifests"].append(copy.deepcopy(index["manifests"][0]))
        (layout / "index.json").write_text(json.dumps(index))
    with pytest.raises(source.QualificationError):
        source.validate_oci_graph(layout, base, synthetic=True)


@pytest.mark.parametrize(
    "fault", ["link", "traversal", "duplicate", "owner", "mode", "mtime", "special"]
)
def test_finite_payload_rejects_type_alias_and_header_drift(fault: str) -> None:
    files = {
        name: b"synthetic"
        for name in ("prometheus", "promtool", "prometheus.yml", "LICENSE", "NOTICE")
    }
    raw, _compressed = source.payload_layer(files, synthetic=True)
    result = io.BytesIO()
    with (
        tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as original,
        tarfile.open(fileobj=result, mode="w", format=tarfile.USTAR_FORMAT) as changed,
    ):
        members = original.getmembers()
        target = members[-1]
        if fault == "link":
            target.type, target.linkname, target.size = tarfile.SYMTYPE, "/etc/passwd", 0
        elif fault == "special":
            target.type, target.size = tarfile.FIFOTYPE, 0
        elif fault == "traversal":
            target.name = "../promtool"
        elif fault == "owner":
            target.uid = 65532
        elif fault == "mode":
            target.mode = 0o777
        elif fault == "mtime":
            target.mtime += 1
        elif fault == "duplicate":
            members.append(copy.copy(target))
        for member in members:
            changed.addfile(member, io.BytesIO(b"synthetic") if member.isreg() else None)
    with pytest.raises(source.QualificationError):
        source._payload_files(result.getvalue())


def test_finite_synthetic_conformance_never_passes_real_binary_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, layout, _docker, _result = _finite_constructed(tmp_path, monkeypatch)
    with pytest.raises(source.QualificationError, match="payload_amd64_ELF"):
        source.validate_oci_graph(layout, base)


def test_finite_source_prepared_is_explicitly_not_a_normal_consumer(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    data = {
        "schema": source.IMAGE_SCHEMA,
        "phase": "source_prepared",
        "inputs": source.declared_inputs(),
        "selection": None,
        "candidate": None,
    }
    manifest.write_text(json.dumps(data))
    assert source.read_image_manifest(manifest, preparation=True)["selection"] is None
    with pytest.raises(source.QualificationError, match="source_prepared_not_consumable"):
        source.read_image_manifest(manifest)
    data["inputs"]["source"]["epoch"] = True
    manifest.write_text(json.dumps(data))
    with pytest.raises(source.QualificationError, match="declared_data_type"):
        source.read_image_manifest(manifest, preparation=True)


def _tool_scan_data(subject: str = "/synthetic/tool-rootfs") -> dict[str, Any]:
    return {
        "SchemaVersion": 2,
        "Trivy": {"Version": "0.74.0"},
        "ArtifactName": subject,
        "ArtifactType": "filesystem",
        "Results": [
            {
                "Target": "usr/bin/oras",
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [
                    {"Name": "stdlib", "Version": "v1.27.2"},
                    {"Name": "golang.org/x/crypto", "Version": "v0.52.0"},
                ],
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2026-56854",
                        "PkgName": "golang.org/x/crypto",
                        "InstalledVersion": "v0.52.0",
                        "Severity": "HIGH",
                        "Description": "Synthetic module observation; no applicability disposition.",
                    }
                ],
            }
        ],
    }


def test_tool_observation_retains_module_high_without_security_claim() -> None:
    data = _tool_scan_data()
    observed = source.tool_scan_inventory(source.canonical_data(data), data["ArtifactName"])
    assert observed == {
        "all_findings": data["Results"][0]["Vulnerabilities"],
        "Secrets_fields_absent": 1,
    }
    assert "Secrets" not in data["Results"][0]
    graph = [
        {
            "ImportPath": source.ORAS_COMMAND,
            "Name": "main",
            "Imports": ["golang.org/x/crypto/blake2b"],
        },
        {"ImportPath": "golang.org/x/crypto/blake2b", "Imports": []},
    ]
    actual = source.tool_packages(b"\n".join(source.canonical_data(row) for row in graph))
    assert actual["SSH_OpenPGP_paths"] == []
    # This exercises parser/graph boundaries only; neither object is native admission.
    assert observed["all_findings"][0]["Severity"] == "HIGH"


@pytest.mark.parametrize(
    "fault",
    [
        "subject",
        "scanner",
        "empty",
        "alias",
        "packages",
        "stdlib",
        "package-type",
        "finding-type",
        "unlisted-finding",
        "severity",
        "secret",
        "secret-null",
        "secret-false",
        "duplicate-target",
    ],
)
def test_tool_scan_rejects_incomplete_subject_coverage_types_and_actual_secrets(fault: str) -> None:
    data = _tool_scan_data()
    row = data["Results"][0]
    if fault == "subject":
        data["ArtifactName"] = "/different/root"
    elif fault == "scanner":
        data["Trivy"]["Version"] = "0.73.0"
    elif fault == "empty":
        data["Results"] = []
    elif fault == "alias":
        row["Target"] = "./usr/bin/oras"
    elif fault == "packages":
        row.pop("Packages")
    elif fault == "stdlib":
        row["Packages"][0]["Version"] = "v1.25.14"
    elif fault == "package-type":
        row["Packages"][0]["Version"] = True
    elif fault == "finding-type":
        row["Vulnerabilities"][0]["InstalledVersion"] = 52
    elif fault == "unlisted-finding":
        row["Vulnerabilities"][0]["PkgName"] = "unlisted/module"
    elif fault == "severity":
        row["Vulnerabilities"][0]["Severity"] = "NOT-CLASSIFIED"
    elif fault.startswith("secret"):
        row["Secrets"] = {
            "secret": [{"Match": "synthetic-only"}],
            "secret-null": None,
            "secret-false": False,
        }[fault]
    elif fault == "duplicate-target":
        data["Results"].append(copy.deepcopy(row))
    with pytest.raises(source.QualificationError):
        source.tool_scan_inventory(source.canonical_data(data), "/synthetic/tool-rootfs")


@pytest.mark.parametrize(
    "path",
    [
        "golang.org/x/crypto/ssh",
        "golang.org/x/crypto/ssh/terminal",
        "golang.org/x/crypto/openpgp",
        "golang.org/x/crypto/openpgp/packet",
    ],
)
def test_oras_affected_package_absence_is_checked_from_full_graph(path: str) -> None:
    rows = [
        {"ImportPath": source.ORAS_COMMAND, "Name": "main", "Imports": [path]},
        {"ImportPath": path, "Imports": []},
    ]
    with pytest.raises(source.QualificationError, match="ORAS_SSH_OpenPGP_imports_HOLD"):
        source.tool_packages(b"\n".join(source.canonical_data(row) for row in rows))


def test_finite_layout_transport_roundtrips_raw_bytes_and_rejects_extra_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, layout, _docker, _result = _finite_constructed(tmp_path, monkeypatch)
    archive = tmp_path / "image.oci.tar"
    source.pack_layout(layout, archive)
    copied = tmp_path / "copied"
    source.unpack_layout(archive.read_bytes(), copied)
    source.compare_pair(
        source.validate_oci_graph(layout, base, synthetic=True),
        source.validate_oci_graph(copied, base, synthetic=True),
    )
    bad = io.BytesIO()
    with tarfile.open(fileobj=bad, mode="w", format=tarfile.USTAR_FORMAT) as output:
        member = tarfile.TarInfo("../outside")
        member.size, member.mode, member.mtime = 1, 0o644, source.SOURCE_DATE_EPOCH
        output.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(source.QualificationError, match="layout_transport_path"):
        source.unpack_layout(bad.getvalue(), tmp_path / "bad")


@pytest.mark.parametrize(
    "path", ["../escape", "/absolute", "nested/../alias", "nested\\alias", "a//b"]
)
def test_finite_actions_zip_rejects_unsafe_names(tmp_path: Path, path: str) -> None:
    import zipfile

    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(path, b"synthetic")
    with pytest.raises(source.QualificationError, match="artifact_member_path_or_alias"):
        source._zip_members(archive)


def test_finite_actions_zip_keeps_4096_member_limit(tmp_path: Path) -> None:
    import zipfile

    archive = tmp_path / "input.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for index in range(4097):
            output.writestr(str(index), b"x")
    with pytest.raises(source.QualificationError, match="artifact_member_count"):
        source._zip_members(archive)


def test_PR_source_ancestry_is_within_PR_and_does_not_require_squash_ancestry() -> None:
    first, final, base = "1" * 40, "2" * 40, "3" * 40
    pr = {
        "number": 2477,
        "head": {"sha": final, "ref": "codex/source", "repo": {"id": 1043311030}},
        "base": {"ref": "main", "repo": {"id": 1043311030}},
        "commits": 2,
    }
    graph = [
        {"sha": first, "parents": [{"sha": base}]},
        {"sha": final, "parents": [{"sha": first}]},
    ]

    class FixtureAPI:
        def json(self, endpoint: str) -> dict[str, Any]:
            assert endpoint.endswith("/pulls/2477")
            return pr

        def pages(self, endpoint: str, key: None, count: int) -> list[dict[str, Any]]:
            assert endpoint.endswith("/pulls/2477/commits") and key is None and count == 2
            return graph

    api = FixtureAPI()
    assert source.authenticate_pr_source(api, 2477, first, final, "refs/heads/codex/source") == pr
    graph[1]["parents"] = [{"sha": base}]
    with pytest.raises(source.QualificationError, match="producer_ancestor_within_PR"):
        source.authenticate_pr_source(api, 2477, first, final, "refs/heads/codex/source")


def test_immutable_promotion_tag_cannot_overwrite_other_subject() -> None:
    digest = "sha256:" + "a" * 64
    versions = [{"id": 1, "name": digest, "metadata": {"container": {"tags": ["selected"]}}}]
    assert source.immutable_tag_state(versions, "selected", digest)
    assert not source.immutable_tag_state(versions, "new", digest)
    with pytest.raises(
        source.QualificationError, match="immutable_tag_existing_other_subject_HOLD"
    ):
        source.immutable_tag_state(versions, "selected", "sha256:" + "b" * 64)


@pytest.mark.parametrize("conclusion", ["success", "failure", None])
def test_unchanged_publication_requires_successful_native_publisher_job(
    conclusion: str | None,
) -> None:
    head = "1" * 40
    run = {
        "id": 12,
        "run_attempt": 1,
        "head_sha": head,
        "head_branch": "main",
        "repository": {"id": 1043311030},
        "head_repository": {"id": 1043311030},
        "event": "push",
        "status": "completed",
        "conclusion": "success",
    }
    job = {
        "name": "prometheus-publish",
        "status": "completed",
        "conclusion": conclusion,
        "head_sha": head,
    }

    class FixtureAPI:
        def json(self, endpoint: str) -> dict[str, int]:
            return {"total_count": 1}

        def pages(self, endpoint: str, key: str, count: int) -> list[dict[str, Any]]:
            assert count == 1
            return [run] if key == "workflow_runs" else [job]

    if conclusion == "success":
        assert source.require_publication_predecessor(FixtureAPI(), head) == {
            "run": run,
            "job": job,
        }
    else:
        with pytest.raises(
            source.QualificationError, match="positive_publication_predecessor_pending_or_missing"
        ):
            source.require_publication_predecessor(FixtureAPI(), head)


def _projection_case(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    root = tmp_path / "repo"
    for name, raw in (
        ("scripts/ci/prometheus_source_image.py", b"synthetic helper"),
        (".github/workflows/build.yml", b"synthetic workflow"),
        ("deploy/prometheus/Containerfile", source.finite_recipe()),
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    manifest = _synthetic_prometheus_manifest()
    manifest["phase"], manifest["selection"], manifest["candidate"] = "source_prepared", None, None
    (root / source.MANIFEST_PATH).write_text(json.dumps(manifest))
    acquired = {
        "source": "a" * 64,
        "go": source.GO.digest,
        "modules": "b" * 64,
        "UI_transform": {
            "generated_paths": [name + ".gz" for name in sorted(source.UI_FILES)],
            "embed_sha256": "c" * 64,
            "python": "synthetic Python",
            "gzip_source_sha256": "d" * 64,
            "zlib_build": "1.3.1",
            "zlib_runtime": "1.3.1",
            "algorithm": "Python GzipFile filename-empty mtime0 level6 OS255; not GNU gzip byte equality",
        },
        "tool_implementations": {
            "oras_sha256": manifest["inputs"]["oras"]["retained"]["binary_sha256"],
            "python_executable_sha256": "e" * 64,
            "python_version": "synthetic Python",
            "zlib": "1.3.1",
        },
    }
    return root, manifest, acquired


@pytest.mark.parametrize(
    "fault",
    [
        "output-cycle",
        "source-bool",
        "go",
        "modules",
        "ui-extra",
        "ui-missing",
        "tool-binary",
        "version-mismatch",
    ],
)
def test_producer_input_projection_rejects_untyped_or_unbound_inputs(
    tmp_path: Path, fault: str
) -> None:
    root, _manifest, acquired = _projection_case(tmp_path)
    assert source.producer_projection(root, acquired)["acquired"] == acquired
    if fault == "output-cycle":
        acquired["selected_digest"] = "a" * 64
    elif fault == "source-bool":
        acquired["source"] = True
    elif fault == "go":
        acquired["go"] = "a" * 64
    elif fault == "modules":
        acquired["modules"] = None
    elif fault == "ui-extra":
        acquired["UI_transform"]["artifact_id"] = 1
    elif fault == "ui-missing":
        acquired["UI_transform"]["generated_paths"].pop()
    elif fault == "tool-binary":
        acquired["tool_implementations"]["oras_sha256"] = "0" * 64
    elif fault == "version-mismatch":
        acquired["tool_implementations"]["python_version"] = "different"
    with pytest.raises(source.QualificationError):
        source.producer_projection(root, acquired)


def test_tool_projection_excludes_own_outputs_but_prom_input_keeps_acquired_tool(
    tmp_path: Path,
) -> None:
    root, manifest, acquired = _projection_case(tmp_path)
    tool_before = source.tool_input_projection(root)
    prom_before = source.producer_projection(root, acquired)
    manifest["inputs"]["oras"]["retained"]["artifact_id"] += 1
    (root / source.MANIFEST_PATH).write_text(json.dumps(manifest))
    assert source.tool_input_projection(root) == tool_before
    assert source.producer_projection(root, acquired) != prom_before
    assert tool_before["inputs"]["oras"]["retained"] is None


def test_native_image_contract_rejects_config_layer_and_user_drift() -> None:
    from tests.test_deploy_contract_scripts import (
        _synthetic_prometheus_manifest,
        FAKE_PROMETHEUS_IMAGE_INSPECT_JSON,
    )

    selection = _synthetic_prometheus_manifest()["selection"]
    image = json.loads(FAKE_PROMETHEUS_IMAGE_INSPECT_JSON)[0]
    source.native_image_contract(image, selection)
    for fault in ("config", "layer", "user", "repository"):
        altered = copy.deepcopy(image)
        if fault == "config":
            altered["Id"] = "sha256:" + "f" * 64
        elif fault == "layer":
            altered["RootFS"]["Layers"][-1] = "sha256:" + "f" * 64
        elif fault == "user":
            altered["Config"]["User"] = "0"
        else:
            altered["RepoDigests"] = []
        with pytest.raises(source.QualificationError):
            source.native_image_contract(altered, selection)


@pytest.mark.parametrize(
    "mode", ["changed_pr_candidate", "new_main_selection", "unchanged_published"]
)
@pytest.mark.parametrize("admission", ["success", "skipped", "failure", "cancelled", "unknown"])
@pytest.mark.parametrize("promotion", ["success", "skipped", "failure", "cancelled", "unknown"])
def test_finite_consumer_result_table_has_only_three_positive_transitions(
    mode: str, admission: str, promotion: str
) -> None:
    expected = {
        ("changed_pr_candidate", "success", "skipped"): "local",
        ("new_main_selection", "success", "success"): "published",
        ("unchanged_published", "skipped", "skipped"): "published",
    }
    if (mode, admission, promotion) in expected:
        assert (
            source.consumer_result(mode, admission, promotion)
            == expected[(mode, admission, promotion)]
        )
    else:
        with pytest.raises(source.QualificationError, match="consumer_predecessors"):
            source.consumer_result(mode, admission, promotion)


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_CONFIG_DIR",
        "GH_HOST",
        "GH_DEBUG",
        "GIT_TRACE",
        "GIT_CURL_VERBOSE",
        "DEVPI_CI_USER",
        "DEVPI_CI_PASSWORD",
        "PULSEPLATE_PYTHON_INDEX_URL",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(name, raising=False)


def package_stream(command: str, *, http2: bool = False) -> bytes:
    root = {"ImportPath": source.ROOT_MODULE + "/cmd/" + command, "Name": "main", "Imports": []}
    objects: list[dict[str, Any]] = []
    if command == "prometheus":
        ui = {
            "ImportPath": source.ROOT_MODULE + "/web/ui",
            "Name": "ui",
            "Imports": [],
            "EmbedFiles": [p + ".gz" for p in source.UI_FILES],
        }
        root["Imports"].append(ui["ImportPath"])
        objects.append(ui)
    if http2:
        root["Imports"].append("golang.org/x/net/http2")
        objects.append(
            {
                "ImportPath": "golang.org/x/net/http2",
                "Name": "http2",
                "Imports": [],
                "Module": {"Path": "golang.org/x/net", "Version": "v0.58.0"},
            }
        )
    objects.append(root)
    return b"\n".join(json.dumps(obj).encode() for obj in objects)


@pytest.mark.parametrize("command", ["prometheus", "promtool"])
def test_complete_graph_preserves_observation_without_disposition(command: str) -> None:
    result = source.decode_packages(package_stream(command, http2=True), command)
    assert result["affected_package_path_observations"]["golang.org/x/net/http2"] is True
    assert len(result["affected_package_path_observations"]) == 8
    assert "pending" in result["advisory_disposition"]
    assert set(source.ADVISORIES) == {
        "GO-2026-6603",
        "GO-2026-6610",
        "GO-2026-6611",
        "GO-2026-6612",
        "GO-2026-6617",
        "GO-2026-5932",
    }
    assert not any("openpgp" in p for p in result["package_paths"])


@pytest.mark.parametrize(
    "change",
    [
        "Error",
        "DepsErrors",
        "Incomplete",
        "missing_dependency",
        "missing_root",
        "duplicate",
        "missing_UI",
        "bad_Incomplete_type",
    ],
)
def test_graph_rejects_incomplete_or_conflicting_native_output(change: str) -> None:
    objects = [json.loads(line) for line in package_stream("prometheus").splitlines()]
    if change == "Error":
        objects[-1]["Error"] = {"Err": "synthetic native error"}
    elif change == "DepsErrors":
        objects[-1]["DepsErrors"] = [{"Err": "synthetic missing module"}]
    elif change == "Incomplete":
        objects[-1]["Incomplete"] = True
    elif change == "bad_Incomplete_type":
        objects[-1]["Incomplete"] = 0
    elif change == "missing_dependency":
        objects[-1]["Imports"].append("golang.org/x/net/http2")
    elif change == "missing_root":
        objects.pop()
    elif change == "duplicate":
        objects.append(dict(objects[-1], Name="different"))
    elif change == "missing_UI":
        objects[0]["EmbedFiles"].pop()
    with pytest.raises(source.QualificationError):
        source.decode_packages(
            b"\n".join(json.dumps(obj).encode() for obj in objects), "prometheus"
        )


@pytest.mark.parametrize(
    "tail",
    [b"{", b"trailing", b'{"ImportPath":"x","ImportPath":"y"}', b'{"ImportPath":"x","Value":NaN}'],
)
def test_json_stream_rejects_truncation_duplicates_and_nonfinite(tail: bytes) -> None:
    with pytest.raises((source.QualificationError, json.JSONDecodeError)):
        source.decode_packages(package_stream("prometheus") + b"\n" + tail, "prometheus")


class SyntheticHTTPS(HTTPSHandler):
    def __init__(self, replies: list[tuple[int, bytes, str | None]]) -> None:
        super().__init__()
        self.replies = list(replies)
        self.requests: list[Any] = []

    def https_open(self, request: Any) -> Any:
        self.requests.append(request)
        code, body, location = self.replies.pop(0)
        headers = Message()
        if location is not None:
            headers["Location"] = location
        if code == 200:
            headers["Content-Length"] = str(len(body))
        response = addinfourl(io.BytesIO(body), headers, request.full_url, code)
        response.msg = "synthetic response"
        return response


def install_transport(
    monkeypatch: pytest.MonkeyPatch, replies: list[tuple[int, bytes, str | None]]
) -> SyntheticHTTPS:
    handler = SyntheticHTTPS(replies)
    transport = build_opener(ProxyHandler({}), source.NoRedirect(), handler)
    monkeypatch.setattr(source, "opener", lambda: transport)
    return handler


FINAL = "https://release-assets.githubusercontent.com/github-production-release-asset/6838921/45b9efd2-fa57-4f55-951b-67f2ea9abb5d?sig=synthetic-query-do-not-log"


def test_direct_acquisition_uses_verified_bytes_and_rejects_redirect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = replace(source.GO, size=3, digest=source.sha(b"abc"))
    handler = install_transport(monkeypatch, [(200, b"abc", None)])
    result = source.acquire(artifact, tmp_path / "go")
    assert result["sha256"] == source.sha(b"abc")
    assert handler.requests[0].get_header("Authorization") is None
    install_transport(monkeypatch, [(302, b"", FINAL)])
    with pytest.raises(source.QualificationError, match="source_transport_failed"):
        source.acquire(artifact, tmp_path / "redirect")


def test_release_accepts_one_finite_handoff_then_no_redirect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = replace(source.UI, size=3, digest=source.sha(b"abc"))
    handler = install_transport(monkeypatch, [(302, b"", FINAL), (200, b"abc", None)])
    result = source.acquire(artifact, tmp_path / "ui")
    assert result["explicit_release_handoff"] is True and len(handler.requests) == 2
    assert "sig=" not in json.dumps(result)
    install_transport(monkeypatch, [(302, b"", FINAL), (302, b"", FINAL)])
    with pytest.raises(source.QualificationError, match="source_transport_failed"):
        source.acquire(artifact, tmp_path / "second-hop")


@pytest.mark.parametrize(
    "url",
    [
        "http://release-assets.githubusercontent.com/github-production-release-asset/6838921/45b9efd2-fa57-4f55-951b-67f2ea9abb5d?x=1",
        FINAL.replace("6838921", "9999999"),
        FINAL.replace("release-assets.githubusercontent.com", "evil.example"),
        FINAL.replace("https://", "https://user:password@"),
        FINAL + "#fragment",
    ],
)
def test_release_handoff_rejects_wrong_authority_path_or_credentials(url: str) -> None:
    with pytest.raises(source.QualificationError):
        source.validate_release_handoff(url, "ui")


def test_digest_failure_does_not_become_cache_or_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = replace(source.GO, size=3, digest=source.sha(b"abc"))
    handler = install_transport(monkeypatch, [(200, b"bad", None)])
    with pytest.raises(source.QualificationError, match="download_integrity"):
        source.acquire(artifact, tmp_path / "go")
    assert len(handler.requests) == 1
    with pytest.raises(source.QualificationError, match="download_cache_collision"):
        source.acquire(artifact, tmp_path / "go")


def make_archive(path: Path, entries: list[tuple[str, bytes | None, bytes]]) -> source.Artifact:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.mode = 0o644
            if payload is not None:
                member.size = len(payload)
            if kind == tarfile.SYMTYPE:
                member.linkname = "../outside"
            archive.addfile(member, io.BytesIO(payload) if payload is not None else None)
    return source.Artifact(
        "fixture",
        source.GO.url,
        path.stat().st_size,
        source.file_hash(path),
        "",
        len(entries),
        sum(kind == tarfile.REGTYPE for _, _, kind in entries),
        1024,
    )


def test_safe_archive_checks_every_member_before_extraction(tmp_path: Path) -> None:
    path = tmp_path / "archive.tar.gz"
    artifact = make_archive(path, [("a/b", b"content", tarfile.REGTYPE)])
    rows = source.extract(artifact, path, tmp_path / "result")
    assert rows[0]["sha256"] == source.sha(b"content")
    assert (tmp_path / "result/a/b").read_bytes() == b"content"


@pytest.mark.parametrize(
    "entries",
    [
        [("../escape", b"x", tarfile.REGTYPE)],
        [("a//b", b"x", tarfile.REGTYPE)],
        [("/absolute", b"x", tarfile.REGTYPE)],
        [("a", None, tarfile.SYMTYPE)],
        [("fifo", None, tarfile.FIFOTYPE)],
        [("a", b"1", tarfile.REGTYPE), ("a", b"2", tarfile.REGTYPE)],
        [("a", b"1", tarfile.REGTYPE), ("a/b", b"2", tarfile.REGTYPE)],
    ],
)
def test_archive_rejects_escapes_links_specials_and_collisions(
    tmp_path: Path, entries: list[tuple[str, bytes | None, bytes]]
) -> None:
    path = tmp_path / "archive.tar.gz"
    artifact = make_archive(path, entries)
    with pytest.raises(source.QualificationError):
        source.extract(artifact, path, tmp_path / "result")
    assert not (tmp_path / "result").exists()


def test_fresh_owned_directories_reject_symlink_and_existing_cache(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(source.QualificationError, match="output_not_fresh"):
        source.fresh_directory(existing)
    alias = tmp_path / "alias"
    alias.symlink_to(existing, target_is_directory=True)
    with pytest.raises(source.QualificationError):
        source.fresh_directory(alias / "child")
    assert not (existing / "child").exists()


def test_ui_staging_discloses_transform_and_keeps_licenses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, ui = tmp_path / "source", tmp_path / "ui"
    (root / "web/ui").mkdir(parents=True)
    (ui / "static").mkdir(parents=True)
    template = b'package ui\nimport "embed"\n'
    (root / "web/ui/embed.go.tmpl").write_bytes(template)
    monkeypatch.setattr(source, "EMBED_TEMPLATE", source.sha(template))
    files = {}
    for name in ["static/index.html", "static/third-party-licenses.txt"]:
        data = name.encode()
        (ui / name).write_bytes(data)
        files[name] = {"size": len(data), "sha256": source.sha(data)}
    monkeypatch.setattr(source, "UI_FILES", files)
    result = source.stage_ui(root, ui)
    assert len(result["generated_paths"]) == 2
    assert "not GNU" in result["algorithm"]
    for name in files:
        payload = (root / "web/ui" / (name + ".gz")).read_bytes()
        assert payload[9] == 255 and gzip.decompress(payload) == (ui / name).read_bytes()
    assert "third-party-licenses.txt.gz" in (root / "web/ui/embed.go").read_text()


def test_sandbox_is_fixed_rootless_readonly_and_credential_free(tmp_path: Path) -> None:
    roots = [tmp_path / name for name in ["source", "go", "modules"]]
    for path in roots:
        path.mkdir()
    argv = source.sandbox_arguments(
        "/usr/bin/docker", tmp_path, "sha256:" + "1" * 64, "owned", "owner", *roots
    )
    assert argv[argv.index("--user") + 1] == "65532:65532"
    assert argv[argv.index("--network") + 1] == "none"
    assert argv[argv.index("--memory") + 1] == "4g"
    assert argv.count("--mount") == 3 and "--read-only" in argv
    assert argv[argv.index("--tmpfs") + 1] == (
        "/qualification:rw,nosuid,nodev,noexec,size=1g,mode=1777"
    )
    assert "HOME=/qualification" in argv and "TMPDIR=/qualification" in argv
    assert "GOCACHE=/qualification/gocache" in argv
    assert all(argv[i + 1].endswith(",readonly") for i, v in enumerate(argv) if v == "--mount")
    env = source.clean_environment(tmp_path, tmp_path, tmp_path, tmp_path, offline=True)
    assert env["GOPROXY"] == env["GOSUMDB"] == "off"
    assert env["GOTOOLCHAIN"] == "local" and env["CGO_ENABLED"] == "0"
    assert not {"GITHUB_TOKEN", "GH_TOKEN", "NETRC", "PIP_INDEX_URL"}.intersection(env)


def test_local_Mac_is_rejected_before_network_or_native_operations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(source.platform, "system", lambda: "Darwin")
    with pytest.raises(source.QualificationError, match="hosted_linux_only"):
        source.qualify(tmp_path / "not-created", 900, 120)
    assert not (tmp_path / "not-created").exists()


def test_valid_wrong_release_asset_is_rejected_before_final_fetch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wrong = FINAL.replace(
        "45b9efd2-fa57-4f55-951b-67f2ea9abb5d", "01234567-89ab-cdef-0123-456789abcdef"
    )
    handler = install_transport(monkeypatch, [(302, b"", wrong)])
    with pytest.raises(source.QualificationError, match="release_handoff_path"):
        source.acquire(replace(source.UI, size=3, digest=source.sha(b"abc")), tmp_path / "ui")
    assert len(handler.requests) == 1


def test_producer_binding_is_absolute_and_independent_of_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = source.producer_paths()
    assert all(path.is_absolute() and path.is_file() for path in paths)
    assert paths[1].name == "build.yml"
    assert all(len(source.file_hash(path)) == 64 for path in paths)


def test_hash_rejects_single_leaf_aliases_and_special_nodes(tmp_path: Path) -> None:
    path = tmp_path / "regular"
    path.write_bytes(b"safe")
    link = tmp_path / "hardlink"
    link.hardlink_to(path)
    with pytest.raises(source.QualificationError, match="multilink"):
        source.file_hash(path)
    fifo = tmp_path / "fifo"
    import os

    os.mkfifo(fifo)
    with pytest.raises(source.QualificationError, match="nonregular"):
        source.file_hash(fifo)


def test_create_timeout_retains_ownership_and_raw_status_for_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    owned: dict[str, dict[str, Any]] = {}
    expected = {"owner": "synthetic"}
    calls: list[list[str]] = []
    state = {"exists": False}

    class FakeNative:
        def __init__(self) -> None:
            self.records: list[dict[str, Any]] = []

        def run(self, argv: list[str], label: str, env: dict[str, str], **kwargs: Any) -> bytes:
            calls.append(argv)
            if "create" in argv:
                assert owned["owned"] == expected
                state["exists"] = True
                self.records.append(
                    {
                        "exit": None,
                        "failure": "TimeoutExpired",
                        "stderr": "retained-raw-create.stderr",
                    }
                )
                raise TimeoutError("synthetic create timeout")
            if "ps" in argv:
                return b"owned\n" if state["exists"] else b""
            if "inspect" in argv:
                return b"[{}]"
            if "rm" in argv:
                state["exists"] = False
                return b"owned\n"
            raise AssertionError(argv)

    fake = FakeNative()
    with pytest.raises(TimeoutError):
        source.create_owned(
            fake, ["/usr/bin/docker", "create"], "owned", expected, owned, "probe", {}, tmp_path
        )
    monkeypatch.setattr(source, "validate_container", lambda actual, name, record: None)
    result = source.cleanup_owned(fake, "/usr/bin/docker", tmp_path, owned, {}, tmp_path)
    assert result == [{"name": "owned", "native_absent": True}]
    assert fake.records[0]["failure"] == "TimeoutExpired"
    assert any("rm" in argv for argv in calls)


def test_never_created_resource_needs_positive_inventory_without_delete(tmp_path: Path) -> None:
    class FakeNative:
        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            assert "ps" in argv
            return b""

    result = source.cleanup_owned(
        FakeNative(), "/usr/bin/docker", tmp_path, {"owned": {}}, {}, tmp_path
    )
    assert result[0]["native_absent"] is True


def test_diagnostics_retain_constant_code_without_remote_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        source.diagnostic_code(source.QualificationError("source_lock_changed"))
        == "source_lock_changed"
    )
    assert source.diagnostic_code(RuntimeError(FINAL)) is None
    assert source.diagnostic_code(source.QualificationError(FINAL)) is None

    def fail(*args: Any) -> None:
        raise source.QualificationError("source_lock_changed")

    monkeypatch.setattr(source, "qualify", fail)
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--work-dir",
            str(tmp_path),
            "--timeout-seconds",
            "900",
            "--cleanup-seconds",
            "120",
        ],
    )
    previous_handlers = {
        signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        assert source.main() == 1
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    assert all(signal.getsignal(signum) == handler for signum, handler in previous_handlers.items())
    stderr = capsys.readouterr().err
    assert "source_lock_changed" in stderr and "sig=" not in stderr


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b'{"Path":"x","Version":"v1.0.0","Error":"failed"}',
        b'{"Path":"x"}',
        b'{"Path":"x","Version":"v1.0.0"}\n{"Path":"x","Version":"v1.0.0"}',
    ],
)
def test_native_module_stream_errors_cannot_be_success(payload: bytes) -> None:
    with pytest.raises(source.QualificationError):
        source.decode_modules(payload)


def test_native_module_semantics_are_retained_not_reimplemented() -> None:
    payload = {
        "Path": "example.org/module",
        "Version": "v1.0.0",
        "Sum": "h1:synthetic",
        "GoModSum": "h1:synthetic",
    }
    assert source.decode_modules(json.dumps(payload).encode()) == [payload]


def test_deadline_and_signal_preserve_failure_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(source.QualificationError, match="qualification_deadline"):
        source.check_deadline(0)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    monkeypatch.setattr(source, "CLEANING", False)
    with pytest.raises(KeyboardInterrupt):
        source.interrupt(15, None)
    assert source.INTERRUPTIONS == [15]
    monkeypatch.setattr(source, "CLEANING", True)
    source.interrupt(15, None)
    assert source.INTERRUPTIONS == [15, 15]


@pytest.mark.parametrize(
    "state",
    [
        {"Running": False, "ExitCode": 1, "OOMKilled": False},
        {"Running": False, "ExitCode": 0, "OOMKilled": True},
        {"Running": True, "ExitCode": 0, "OOMKilled": False},
        {"Running": False, "ExitCode": False, "OOMKilled": False},
    ],
)
def test_attached_CLI_success_requires_native_container_completion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, state: dict[str, Any]
) -> None:
    checked = []

    class FakeNative:
        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            if "start" in argv:
                return b"native metadata"
            assert "inspect" in argv
            return json.dumps([{"State": state}]).encode()

    monkeypatch.setattr(
        source, "validate_container", lambda actual, name, expected: checked.append(name)
    )
    with pytest.raises(source.QualificationError, match="container_native_completion"):
        source.start_owned(
            FakeNative(), "/usr/bin/docker", tmp_path, "owned", {}, "case", {}, tmp_path
        )
    assert checked == ["owned"]


def test_completed_container_inspection_retains_actual_native_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state = {"Running": False, "ExitCode": 0, "OOMKilled": False, "FinishedAt": "native-time"}
    operations = []

    class FakeNative:
        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            operations.append(argv)
            if "start" in argv:
                return b"native metadata"
            return json.dumps([{"State": state}]).encode()

    monkeypatch.setattr(source, "validate_container", lambda actual, name, expected: None)
    raw, observed = source.start_owned(
        FakeNative(), "/usr/bin/docker", tmp_path, "owned", {}, "case", {}, tmp_path
    )
    assert raw == b"native metadata" and observed == state
    assert "start" in operations[0] and "inspect" in operations[1]


def test_early_cleanup_has_one_shared_window_without_later_native_launch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    clock = {"now": 10.0}
    launched: list[list[str]] = []
    monkeypatch.setattr(source.time, "monotonic", lambda: clock["now"])

    class CompletedProcess:
        returncode = 0

        def poll(self) -> int:
            return self.returncode

    def completed(argv: list[str], **kwargs: Any) -> CompletedProcess:
        launched.append(argv)
        return CompletedProcess()

    monkeypatch.setattr(source.subprocess, "Popen", completed)
    native = source.Native(tmp_path, deadline=900.0, cleanup=120)
    native.begin_cleanup()
    assert native.cleanup_deadline == 130.0
    native.run(["/usr/bin/docker", "ps"], "first-cleanup", {}, cwd=tmp_path, cleaning=True)
    clock["now"] = 131.0
    with pytest.raises(source.QualificationError, match="qualification_deadline"):
        native.run(
            ["/usr/bin/docker", "inspect", "owned"],
            "second-cleanup",
            {},
            cwd=tmp_path,
            cleaning=True,
        )
    assert launched == [["/usr/bin/docker", "ps"]]
    with pytest.raises(source.QualificationError, match="cleanup_deadline_already_started"):
        native.begin_cleanup()


@pytest.mark.parametrize("missing_read", (1, 2))
def test_missing_archive_stream_preserves_failure_before_output_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing_read: int
) -> None:
    path = tmp_path / "archive.tar.gz"
    artifact = make_archive(path, [("a/b", b"content", tarfile.REGTYPE)])
    original = tarfile.TarFile.extractfile
    calls = 0

    def missing_stream(archive: tarfile.TarFile, member: tarfile.TarInfo) -> Any:
        nonlocal calls
        calls += 1
        return None if calls == missing_read else original(archive, member)

    monkeypatch.setattr(source.tarfile.TarFile, "extractfile", missing_stream)
    code = "archive_member_missing" if missing_read == 1 else "extract_member_missing"
    destination = tmp_path / "result"
    with pytest.raises(source.QualificationError, match=code):
        source.extract(artifact, path, destination)
    assert calls == missing_read
    assert not (destination / "a/b").exists()
    if missing_read == 1:
        assert not destination.exists()


@pytest.mark.parametrize("path", (None, 0, False, "", []))
def test_native_package_identity_rejects_nonstring_or_empty_path(path: Any) -> None:
    objects = [json.loads(line) for line in package_stream("prometheus").splitlines()]
    objects[-1]["ImportPath"] = path
    with pytest.raises(source.QualificationError, match="package_identity"):
        source.decode_packages(
            b"\n".join(json.dumps(obj).encode() for obj in objects), "prometheus"
        )


def test_missing_native_docker_stops_before_acquisition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setattr(source.shutil, "which", lambda name: None)

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Missing native Docker must stop before any source acquisition")

    monkeypatch.setattr(source, "acquire", forbidden)
    work = tmp_path / "qualification"
    with pytest.raises(source.QualificationError, match="native_Docker_missing"):
        source.qualify(work, 900, 120)
    assert not (work / "docker-config").exists()


@pytest.mark.parametrize("changed_lock", (None, "go.mod", "go.sum"))
def test_main_prefetch_uses_no_explicit_module_args_and_rejects_lock_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    changed_lock: str | None,
) -> None:
    """Exercise the real main/qualify flow through prefetch with synthetic native I/O.

    This proves argv and the real post-download lock guard, not native Go closure.
    No Docker or Go process is launched; the unchanged case stops at mod verify.
    """
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setattr(source.shutil, "which", lambda name: "/usr/bin/docker")
    locks = {"go.mod": b"synthetic module lock\n", "go.sum": b"synthetic sums\n"}
    monkeypatch.setattr(source, "LOCKS", {name: source.sha(data) for name, data in locks.items()})
    monkeypatch.setattr(source, "GO_LICENSE", source.sha(b"synthetic license"))
    monkeypatch.setattr(source, "SOURCE_LICENSES", {"LICENSE": source.sha(b"synthetic license")})

    def acquire_fixture(artifact: source.Artifact, target: Path, deadline: float) -> dict[str, Any]:
        target.write_text(
            source.UI.digest + "  prometheus-web-ui-3.15.0.tar.gz\n"
            if artifact.name == "checksums"
            else "synthetic archive"
        )
        return {"synthetic": True}

    def extract_fixture(
        artifact: source.Artifact, archive: Path, target: Path, deadline: float
    ) -> list[dict[str, Any]]:
        target.mkdir()
        if artifact.name in ("source", "go"):
            (target / "LICENSE").write_bytes(b"synthetic license")
            (target / "VERSION").write_bytes(
                b"3.15.0\n"
                if artifact.name == "source"
                else b"go1.27.2\ntime 2026-10-02T20:28:03Z\n"
            )
        if artifact.name == "source":
            for name, data in locks.items():
                (target / name).write_bytes(data)
        return []

    calls: list[tuple[list[str], str]] = []

    def native_fixture(
        native: source.Native,
        argv: list[str],
        name: str,
        env: dict[str, str],
        *,
        cwd: Path,
        cleaning: bool = False,
    ) -> bytes:
        calls.append((argv, name))
        assert not cleaning
        assert env["GOTOOLCHAIN"] == "local" and env["GOFLAGS"] == "-mod=readonly"
        if name == "online-go-version":
            return source.GO_VERSION.encode()
        if name == "public-module-download":
            if changed_lock is not None:
                (cwd / changed_lock).write_bytes(b"unexpected native lock mutation\n")
            return b'{"Path":"example.org/synthetic-module","Version":"v1.0.0"}'
        assert name == "online-module-verify"
        raise source.QualificationError("synthetic_stop_before_Docker")

    monkeypatch.setattr(source, "acquire", acquire_fixture)
    monkeypatch.setattr(source, "extract", extract_fixture)
    monkeypatch.setattr(source, "stage_ui", lambda *args: {"synthetic": True})
    monkeypatch.setattr(source.Native, "run", native_fixture)
    work = tmp_path / "qualification"
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--work-dir",
            str(work),
            "--timeout-seconds",
            "900",
            "--cleanup-seconds",
            "120",
        ],
    )
    previous = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}
    try:
        assert source.main() == 1
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    assert calls[1] == (
        [str(work / "go/bin/go"), "mod", "download", "-json"],
        "public-module-download",
    )
    report = json.loads((work / "evidence/qualification.json").read_text())
    expected = "source_lock_changed" if changed_lock else "synthetic_stop_before_Docker"
    assert report["failure"] == {
        "class": "QualificationError",
        "code": expected,
        "stage": "public_native_Go_prefetch",
    }
    assert expected in capsys.readouterr().err
    assert report["status"] == "failed_or_unknown" and report["cleanup"] == []
    assert [name for _, name in calls] == (
        ["online-go-version", "public-module-download"]
        if changed_lock
        else ["online-go-version", "public-module-download", "online-module-verify"]
    )
    if changed_lock:
        assert (work / "source" / changed_lock).read_bytes() == b"unexpected native lock mutation\n"


def ghcr_synthetic_responses() -> tuple[dict[str, Any], dict[str, Any]]:
    """Synthetic fields; delimiter shape matches host observation f1459cf, not hosted parity."""
    repository = {
        "id": 123,
        "full_name": source.GHCR_REPOSITORY,
        "owner": {"id": 456, "login": source.GHCR_OWNER},
    }
    package = {
        "id": 789,
        "name": "pulseplate",
        "package_type": "container",
        "visibility": "public",
        "owner": {"id": 456, "login": source.GHCR_OWNER},
        "repository": {"id": 123, "full_name": source.GHCR_REPOSITORY},
    }
    return repository, package


def ghcr_synthetic_HTTP(value: Any) -> bytes:
    return b"HTTP/2.0 200 OK\nContent-Type: application/json\r\n\r\n" + json.dumps(value).encode()


def test_ghcr_typed_projection_does_not_copy_unused_fields() -> None:
    repository, package = ghcr_synthetic_responses()
    repository["description"] = "synthetic private unused field"
    package["url"] = "https://synthetic.invalid/unused"
    projection = source.ghcr_identity(repository, package)
    assert projection == {
        "repository": {"id": 123, "full_name": source.GHCR_REPOSITORY},
        "owner": {"id": 456, "login": source.GHCR_OWNER},
        "package": {
            "id": 789,
            "name": "pulseplate",
            "package_type": "container",
            "visibility": "public",
            "source_repository_id": 123,
        },
    }
    assert source.ghcr_response(ghcr_synthetic_HTTP(repository)) == (200, repository)
    assert "synthetic" not in json.dumps(projection)


@pytest.mark.parametrize("value", [True, False, 0, -1, "123", None, 1.25])
@pytest.mark.parametrize(
    "location", ["repository", "owner", "package", "package_owner", "linked_repository"]
)
def test_ghcr_IDs_are_positive_JSON_integers(value: Any, location: str) -> None:
    repository, package = ghcr_synthetic_responses()
    targets = {
        "repository": repository,
        "owner": repository["owner"],
        "package": package,
        "package_owner": package["owner"],
        "linked_repository": package["repository"],
    }
    targets[location]["id"] = value
    with pytest.raises(source.QualificationError, match="GHCR_positive_ID"):
        source.ghcr_identity(repository, package)


@pytest.mark.parametrize(
    "location,field,value",
    [
        ("package", "visibility", "private"),
        ("package", "package_type", "npm"),
        ("package", "name", "pulseplate-other"),
        ("package_owner", "id", 457),
        ("linked_repository", "id", 124),
        ("repository", "full_name", "other/PulsePlate"),
        ("owner", "login", "Katsiarynakavaleuskayа"),
    ],
)
def test_ghcr_cross_identity_and_public_conditions_fail_closed(
    location: str, field: str, value: Any
) -> None:
    repository, package = ghcr_synthetic_responses()
    targets = {
        "repository": repository,
        "owner": repository["owner"],
        "package": package,
        "package_owner": package["owner"],
        "linked_repository": package["repository"],
    }
    targets[location][field] = value
    with pytest.raises(source.QualificationError):
        source.ghcr_identity(repository, package)


@pytest.mark.parametrize("body", [b'{"id":1,"id":2}', b'{"id":NaN}', b"{}{}", b"[]", b"{", b""])
def test_ghcr_requires_one_complete_unique_finite_JSON_object(body: bytes) -> None:
    with pytest.raises((source.QualificationError, ValueError)):
        source.ghcr_response(b"HTTP/2.0 200 OK\nContent-Type: application/json\r\n\r\n" + body)


@pytest.mark.parametrize(
    "raw,diagnostic",
    [
        (b"{}", "GHCR_HTTP_header"),
        (
            b"HTTP/2.0 403 Forbidden\nContent-Type: application/json\r\n\r\n{}",
            "GHCR_HTTP_status_403",
        ),
        (b"HTTP/2.0 302 Found\nContent-Type: application/json\r\n\r\n{}", "GHCR_HTTP_status_302"),
        (b"HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n{}", "GHCR_HTTP_status"),
        (b"HTTP/2.0 200 OK\n\nContent-Type: application/json\r\n\r\n{}", "GHCR_HTTP_header"),
        (
            b"HTTP/2.0 200 OK\nContent-Type: application/json\nX-Test: value\r\n\r\n{}",
            "GHCR_HTTP_header",
        ),
        (
            b"HTTP/2.0 200 OK\nContent-Type: application/json\rX-Test: value\r\n\r\n{}",
            "GHCR_HTTP_header",
        ),
        (b"HTTP/2.0 200 OK\nContent-Type: application/json\r\n\n{}", "GHCR_HTTP_header"),
        (
            b"HTTP/2.0 200 OK trailing\x00\nContent-Type: application/json\r\n\r\n{}",
            "GHCR_HTTP_status",
        ),
    ],
)
def test_ghcr_requires_observed_native_delimiters_and_success(raw: bytes, diagnostic: str) -> None:
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.ghcr_response(raw)


def test_ghcr_host_observed_status_LF_and_strict_header_CRLF_shape() -> None:
    repository, _ = ghcr_synthetic_responses()
    status = bytes.fromhex("485454502f322e3020323030204f4b0a")
    raw = (
        status
        + b"Content-Type: application/json\r\nX-Synthetic: unused\r\n\r\n"
        + json.dumps(repository).encode()
    )
    assert source.ghcr_response(raw) == (200, repository)
    # Only status/delimiter shape is native-observed; body/headers are synthetic.
    with pytest.raises(source.QualificationError, match="GHCR_HTTP_header"):
        source.ghcr_response(status + b"X-Synthetic: " + b"x" * 32768 + b"\r\n\r\n{}")


def test_ghcr_mode_cannot_fall_through_to_source_qualify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    called: list[str] = []
    monkeypatch.setattr(source, "qualify", lambda *args: called.append("source"))
    monkeypatch.setattr(
        source, "qualify_existing_ghcr_package", lambda *args: called.append("GHCR")
    )
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--qualify-existing-ghcr-package",
            "--public-output",
            str(tmp_path / "public.json"),
            "--work-dir",
            str(tmp_path / "private"),
            "--timeout-seconds",
            "90",
            "--cleanup-seconds",
            "30",
        ],
    )
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        assert source.main() == 0
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    assert called == ["GHCR"]


@pytest.mark.parametrize("selector", [[], ["--qualify-existing-ghcr-package"]])
def test_ghcr_mixed_flags_reject_before_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, selector: list[str]
) -> None:
    monkeypatch.setattr(source, "qualify", lambda *args: pytest.fail("source operation"))
    monkeypatch.setattr(
        source,
        "qualify_existing_ghcr_package",
        lambda *args: pytest.fail("authenticated operation"),
    )
    args = [
        "qualifier",
        "--work-dir",
        str(tmp_path / "private"),
        "--timeout-seconds",
        "90",
        "--cleanup-seconds",
        "30",
        *selector,
    ]
    if not selector:
        args += ["--public-output", str(tmp_path / "public.json")]
    monkeypatch.setattr(source.sys, "argv", args)
    with pytest.raises(SystemExit) as error:
        source.main()
    assert error.value.code == 2


def _fixed_native_capture_fixture(
    tmp_path: Path, mode: str, adapter: str = "GHCR"
) -> tuple[Path, Path, Path]:
    """One existing synthetic native fixture for both consumers of the canonical group boundary."""
    runner = tmp_path.resolve()
    repository, package = ghcr_synthetic_responses()
    trace = runner / "synthetic-command-trace.jsonl"
    gh = runner / "synthetic-gh"
    child_code = (
        "import os,signal,time\nfrom pathlib import Path\n"
        + "marker=Path("
        + repr(str(trace.with_suffix(".child-signal")))
        + ")\n"
        + "ready=Path("
        + repr(str(trace.with_suffix(".child-ready")))
        + ")\n"
        + "def terminate(signum, frame):\n marker.write_text('SIGTERM\\n')\n"
        + (
            " os.execv('/bin/sleep', ['/bin/sleep', '0.2'])\n"
            if mode == "owned_residual_exec_exit"
            else " raise SystemExit(128+signum)\n"
        )
        + "signal.signal(signal.SIGTERM, terminate)\nready.write_text('ready')\ntime.sleep(5)\n"
    )
    gh.write_text(
        "#!"
        + source.sys.executable
        + "\n"
        + "import os,sys,json,time,subprocess\nfrom pathlib import Path\n"
        + "mode="
        + repr(mode)
        + "\nadapter="
        + repr(adapter)
        + "\nrepository="
        + repr(repository)
        + "\npackage="
        + repr(package)
        + "\n"
        + "trace=Path("
        + repr(str(trace))
        + ")\n"
        + "child_code="
        + repr(child_code)
        + "\n"
        + "with trace.open('a') as output: output.write(json.dumps({'argv':sys.argv[1:],'environment_keys':sorted(os.environ)})+'\\n')\n"
        + "token=os.environ['GH_TOKEN']\n"
        + "if sys.argv[1:]==['auth','status','--hostname','github.com']:\n"
        + " if mode in ('owned_residual','owned_residual_exec_exit','owned_held_pipes'):\n"
        + "  child=subprocess.Popen([sys.executable,'-c',child_code],stdin=subprocess.DEVNULL,stdout=None if mode=='owned_held_pipes' else subprocess.DEVNULL,stderr=None if mode=='owned_held_pipes' else subprocess.DEVNULL)\n"
        + "  trace.with_suffix('.child-pid').write_text(str(child.pid))\n"
        + "  ready=trace.with_suffix('.child-ready'); ready_deadline=time.monotonic()+1\n"
        + "  while not ready.exists():\n"
        + "   assert time.monotonic()<ready_deadline\n"
        + "   time.sleep(0.01)\n"
        + "  time.sleep(0.5)\n"
        + " if mode=='deadline': time.sleep(3)\n"
        + " if mode=='output_bound': sys.stdout.write('x'*(1024**2+1))\n"
        + " elif mode=='auth_reflection': sys.stdout.write(token)\n"
        + " else: sys.stdout.write('synthetic auth status')\n"
        + " sys.exit(1 if mode=='auth_nonzero' else 0)\n"
        + "if adapter=='GitHubRead':\n"
        + " if sys.argv[1:] == ['stdin']:\n"
        + "  sys.stderr.write('x'*131072); sys.stderr.flush()\n"
        + "  received=sys.stdin.buffer.read(); assert received == ('synthetic.'+'q'*160000+'.opaque\\n').encode()\n"
        + "  sys.stdout.write('accepted'); sys.exit(0)\n"
        + " endpoint=sys.argv[-1]; value=repository if endpoint=='/repos/Katsiarynakavaleuskaya/PulsePlate' else package\n"
        + " if mode=='unused_body_reflection': value['unused']=token\n"
        + " if mode=='API_403': value={'message':'synthetic forbidden'}\n"
        + " if mode=='cleanup_failure' and not (Path.cwd()/'home'/'unexpected').is_symlink(): os.symlink('../config',Path.cwd()/'home'/'unexpected')\n"
        + " sys.stdout.write(json.dumps(value))\n"
        + " if mode=='stderr_reflection': sys.stderr.write(token)\n"
        + " sys.exit(1 if mode in ('API_nonzero','API_403') else 0)\n"
        + "assert sys.argv[1:9]==['api','--hostname','github.com','--method','GET','--include','-H','Accept:application/vnd.github+json']\n"
        + "endpoint=sys.argv[9]\nvalue=repository if endpoint=='/repos/Katsiarynakavaleuskaya/PulsePlate' else package\n"
        + "if mode=='unused_body_reflection': value['unused']=token\n"
        + "header='HTTP/2.0 200 OK\\nContent-Type: application/json\\r\\n'\n"
        + "if mode=='header_reflection': header+='X-Synthetic: '+token+'\\r\\n'\n"
        + "if mode=='API_403': header='HTTP/2.0 403 Forbidden\\nContent-Type: application/json\\r\\n'; value={'message':'synthetic forbidden'}\n"
        + "sys.stdout.write(header+'\\r\\n'+json.dumps(value))\n"
        + "if mode=='stderr_reflection': sys.stderr.write(token)\n"
        + "if mode=='cleanup_failure': (Path.cwd()/'home'/'unexpected').write_text('synthetic empty-state violation')\n"
        + "sys.exit(1 if mode in ('API_nonzero','API_403') else 0)\n"
    )
    gh.chmod(0o700)
    return runner, trace, gh


@pytest.mark.parametrize(
    "mode",
    [
        "immediate_exit",
        "auth_nonzero",
        "API_nonzero",
        "API_403",
        "auth_reflection",
        "header_reflection",
        "unused_body_reflection",
        "stderr_reflection",
        "output_bound",
        "deadline",
        "cleanup_failure",
        "owned_residual",
        "owned_residual_exec_exit",
    ],
)
def test_ghcr_fixed_native_capture_and_hygiene(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    """Real child pipes/processes, synthetic GH program; not an authenticated API proof."""
    runner, trace, gh = _fixed_native_capture_fixture(tmp_path, mode)
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    credential = "synthetic.opaque.step.credential.without.length.assumptions"
    for key, value in {
        "GITHUB_ACTIONS": "true",
        "RUNNER_OS": "Linux",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_JOB": "prometheus-ghcr-package-qualification",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "RUNNER_TEMP": str(runner),
        "GH_TOKEN": credential,
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    monkeypatch.setattr(
        source.Native, "run", lambda *args, **kwargs: pytest.fail("credential-bearing Native.run")
    )
    work, public = (
        runner / "ghcr-private-123-1",
        runner / "ghcr-public-123-1" / "qualification.json",
    )
    real_popen = source.subprocess.Popen
    declared_environment_keys: list[set[str]] = []
    declared_commands: list[list[str]] = []

    def observe_environment(argv: list[str], *args: Any, **kwargs: Any) -> Any:
        if argv and argv[0] == str(gh):
            environment = kwargs["env"]
            declared_environment_keys.append(set(environment))
            declared_commands.append(argv[1:])
            assert environment["GH_TOKEN"] == credential  # Explicit synthetic fixture only.
            assert environment["HOME"] == str(work / "home")
            assert environment["GH_CONFIG_DIR"] == str(work / "config")
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(source.subprocess, "Popen", observe_environment)
    if mode == "immediate_exit":
        result = source.qualify_existing_ghcr_package(work, public, 8, 2)
        assert result == json.loads(public.read_bytes()) and result["qualified"] is True
        assert result["package"]["id"] == 789
        assert credential.encode() not in public.read_bytes()
    else:
        errors = (source.QualificationError, TimeoutError)
        if mode == "deadline":
            errors += (source.subprocess.TimeoutExpired,)
        with pytest.raises(errors) as failure:
            source.qualify_existing_ghcr_package(work, public, 1 if mode == "deadline" else 8, 2)
        assert not public.exists() and not public.parent.exists()
        if mode == "deadline":
            if isinstance(failure.value, source.subprocess.TimeoutExpired):
                assert failure.value.cmd == [
                    "/bin/ps",
                    "-axo",
                    "pid,ppid,pgid,uid,lstart,state,comm",
                ]
                assert 0 < failure.value.timeout <= 1
            else:
                assert isinstance(failure.value, source.QualificationError)
                assert str(failure.value) == "qualification_deadline"
        if mode == "API_403":
            assert isinstance(failure.value, source.QualificationError)
            assert str(failure.value) == "GHCR_native_exit_1_GHCR_HTTP_status_403"
        if mode in {"owned_residual", "owned_residual_exec_exit"}:
            assert isinstance(failure.value, source.QualificationError)
            assert str(failure.value) == "GHCR_owned_group_survived"
            assert trace.with_suffix(".child-signal").read_bytes() == b"SIGTERM\n"
    assert trace.exists() or mode == "deadline"
    commands = (
        [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    )
    if mode == "deadline":
        # A real deadline may kill the child before its first Python trace write.
        assert len(commands) in {0, 1}
        assert declared_commands in ([], [["auth", "status", "--hostname", "github.com"]])
    else:
        assert len(commands) == (
            3
            if mode in {"immediate_exit", "cleanup_failure"}
            else (
                2
                if mode
                in {
                    "API_nonzero",
                    "API_403",
                    "header_reflection",
                    "unused_body_reflection",
                    "stderr_reflection",
                }
                else 1
            )
        )
    if commands:
        assert commands[0]["argv"] == ["auth", "status", "--hostname", "github.com"]
    assert [command["argv"] for command in commands] == declared_commands[: len(commands)]
    expected_environment_keys = {
        "PATH",
        "LANG",
        "LC_ALL",
        "GH_HOST",
        "GH_TOKEN",
        "GH_PROMPT_DISABLED",
        "GH_PAGER",
        "PAGER",
        "GH_NO_UPDATE_NOTIFIER",
        "GH_NO_EXTENSION_UPDATE_NOTIFIER",
        "GH_TELEMETRY",
        "DO_NOT_TRACK",
        "HOME",
        "GH_CONFIG_DIR",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "TMPDIR",
    }
    assert len(declared_environment_keys) == len(declared_commands)
    if mode != "deadline":
        assert len(declared_commands) == len(commands)
    assert all(keys == expected_environment_keys for keys in declared_environment_keys)
    # The OS/runtime can inject non-selected metadata (observed macOS CF key).
    # Check credential/config selectors in the real child without authorizing an OS-key allowlist.
    selectors = {
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "DEBUG",
        "GIT_TRACE",
        "GIT_CURL_VERBOSE",
        "PYTHONPATH",
        "PYTHONHOME",
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
        "BASH_ENV",
        "ENV",
        "SSH_ASKPASS",
        "GIT_ASKPASS",
    }
    for command in commands:
        selected = {
            key
            for key in command["environment_keys"]
            if key.startswith(("GH_", "GITHUB_")) or key in selectors
        }
        assert selected == {key for key in expected_environment_keys if key.startswith("GH_")}
    assert not any("GITHUB_TOKEN" in command["environment_keys"] for command in commands)
    assert not work.exists() if mode != "cleanup_failure" else work.exists()
    assert not list(runner.glob("**/*.stdout")) and not list(runner.glob("**/*.stderr"))
    if mode in {"owned_residual", "owned_residual_exec_exit"}:
        child_pid = int(trace.with_suffix(".child-pid").read_text())
        with pytest.raises(ProcessLookupError):
            source.os.kill(child_pid, 0)


@pytest.mark.parametrize(
    "mode",
    [
        "immediate_exit",
        "auth_nonzero",
        "API_nonzero",
        "API_403",
        "auth_reflection",
        "unused_body_reflection",
        "stderr_reflection",
        "output_bound",
        "deadline",
        "cleanup_failure",
        "owned_residual",
        "owned_residual_exec_exit",
        "owned_held_pipes",
    ],
)
def test_github_fixed_native_capture_and_hygiene(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    """Same native child fixture/canonical recognizer, synthetic auth only."""
    runner, trace, gh = _fixed_native_capture_fixture(tmp_path, mode, "GitHubRead")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    credential = "synthetic.opaque." + "a." * 260
    monkeypatch.setenv("GH_TOKEN", credential)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic.other.opaque.writer")
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    monkeypatch.setattr(
        source.Native, "run", lambda *args, **kwargs: pytest.fail("credential-bearing Native.run")
    )
    evidence = runner / "evidence"
    evidence.mkdir()
    private = runner / "private"
    adapter = source.GitHubRead.__new__(source.GitHubRead)

    def observe() -> None:
        source.GitHubRead.__init__(
            adapter,
            private,
            evidence,
            source.time.monotonic() + (1 if mode in {"deadline", "owned_held_pipes"} else 8),
            2,
        )
        adapter.json("/repos/" + source.GHCR_REPOSITORY)
        adapter.json("/repos/" + source.GHCR_REPOSITORY + "/synthetic-package")

    if mode == "immediate_exit":
        observe()
        assert adapter.cleanup_deadline is None
        adapter.close()
        assert not private.exists()
    else:
        with pytest.raises(
            (source.QualificationError, TimeoutError, source.subprocess.TimeoutExpired)
        ) as failure:
            try:
                observe()
            finally:
                if private.exists():
                    adapter.close()
        if mode in {"API_nonzero", "API_403"}:
            assert str(failure.value) == "GitHub_native_failed"
        elif mode in {"unused_body_reflection", "stderr_reflection"}:
            assert str(failure.value) == "GitHub_credential_reflection_HOLD"
        elif mode == "cleanup_failure":
            assert str(failure.value) == "GitHub_private_member"
        if mode in {"owned_residual", "owned_residual_exec_exit"}:
            assert str(failure.value) == "GHCR_owned_group_survived"
        if mode in {"owned_residual", "owned_residual_exec_exit", "owned_held_pipes"}:
            assert trace.with_suffix(".child-signal").read_bytes() == b"SIGTERM\n"
            child = int(trace.with_suffix(".child-pid").read_text())
            with pytest.raises(ProcessLookupError):
                source.os.kill(child, 0)
        assert private.exists() is (mode == "cleanup_failure")
    for path in evidence.iterdir():
        assert credential.encode() not in path.read_bytes()
        assert b"synthetic.other.opaque.writer" not in path.read_bytes()
    assert adapter.process is None


@pytest.mark.parametrize("uncertainty", ["reused_identity", "census_failure"])
def test_github_fixed_native_capture_retains_private_on_identity_uncertainty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    uncertainty: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner, _trace, gh = _fixed_native_capture_fixture(tmp_path, "deadline", "GitHubRead")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GH_TOKEN", "synthetic.opaque.identity.control")
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    evidence = runner / "evidence"
    evidence.mkdir()
    private = runner / "private"
    real_census = source.process_census
    real_popen = source.subprocess.Popen
    children: list[Any] = []
    calls = 0

    def start(argv: list[str], *args: Any, **kwargs: Any) -> Any:
        process = real_popen(argv, *args, **kwargs)
        if argv[0] == str(gh):
            children.append(process)
        return process

    def uncertain(cap: float, known: tuple[bytes, ...]) -> dict[int, dict[str, Any]]:
        nonlocal calls
        calls += 1
        rows = real_census(cap, known)
        if calls > 1:
            if uncertainty == "census_failure":
                raise source.QualificationError("GHCR_process_census")
            row = rows.get(children[-1].pid)
            if row is not None:
                row["uid"] += 1
        return rows

    with monkeypatch.context() as context:
        context.setattr(source.subprocess, "Popen", start)
        context.setattr(source, "process_census", uncertain)
        context.setattr(source.os, "killpg", lambda *args: pytest.fail("uncertain identity signal"))
        with pytest.raises(source.QualificationError) as failure:
            source.GitHubRead(private, evidence, source.time.monotonic() + 8, 2)
        assert str(failure.value) == (
            "GHCR_process_census"
            if uncertainty == "census_failure"
            else "GHCR_unknown_or_reused_group_member"
        )
        assert private.is_dir()
    # The fixture's exact own child expires naturally; no uncertainty-based signal.
    for child in children:
        child.wait(timeout=5)
        assert not any(
            row["pgid"] == child.pid
            for row in real_census(source.time.monotonic() + 1, ()).values()
        )
    assert "GitHub cleanup also failed:" in capsys.readouterr().err


def test_github_fixed_native_capture_drains_output_while_writing_opaque_stdin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner, _trace, gh = _fixed_native_capture_fixture(tmp_path, "immediate_exit", "GitHubRead")
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GH_TOKEN", "synthetic.opaque." + "x." * 260)
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    evidence = runner / "evidence"
    evidence.mkdir()
    adapter = source.GitHubRead(runner / "private", evidence, source.time.monotonic() + 8, 2)
    opaque = ("synthetic." + "q" * 160000 + ".opaque\n").encode()
    try:
        assert (
            adapter._capture(
                [str(gh), "stdin"],
                2 * 1024**2,
                environment={"PATH": "/usr/bin:/bin", "GH_TOKEN": "synthetic.readonly.native"},
                input_data=opaque,
            )
            == b"accepted"
        )
    finally:
        adapter.close()
    assert not (runner / "private").exists()
    assert all(opaque not in path.read_bytes() for path in evidence.iterdir())


@pytest.mark.parametrize(
    "endpoint,accepted",
    [
        ("/repos/" + source.GHCR_REPOSITORY, True),
        ("/repos/" + source.GHCR_REPOSITORY + "/commits/" + "a" * 40, True),
        ("/repos/foreign/PulsePlate", False),
        ("/repos/Katsiarynakavaleuskaya/foreign", False),
        ("/repos/" + source.GHCR_REPOSITORY + "-extra", False),
        ("/repos/" + source.GHCR_REPOSITORY + "-extra/commits", False),
        ("/repos/" + source.GHCR_REPOSITORY + "child", False),
        ("/repos/" + source.GHCR_REPOSITORY + "?ref=main", False),
        ("/repos/" + source.GHCR_REPOSITORY + "#fragment", False),
        ("/repos/" + source.GHCR_REPOSITORY + "/../foreign", False),
        ("/repos/" + source.GHCR_REPOSITORY + "/\n", False),
        ("/repos/" + source.GHCR_REPOSITORY + "/\x7f", False),
        ("https://api.github.com/repos/" + source.GHCR_REPOSITORY, False),
    ],
)
def test_github_native_namespace_exact_root_and_existing_children_only(
    monkeypatch: pytest.MonkeyPatch, endpoint: str, accepted: bool
) -> None:
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    adapter = source.GitHubRead.__new__(source.GitHubRead)
    adapter.gh = "/synthetic/gh"
    observed: list[list[str]] = []

    def capture(argv: list[str], maximum: int) -> bytes:
        observed.append(argv)
        return b"{}"

    monkeypatch.setattr(adapter, "_capture", capture)
    if accepted:
        assert adapter.raw(endpoint) == b"{}"
        assert observed == [
            [adapter.gh, "api", "--hostname", "github.com", "--method", "GET", endpoint]
        ]
    else:
        with pytest.raises(source.QualificationError, match="GitHub_same_repository_endpoint"):
            adapter.raw(endpoint)
        assert observed == []


def _promotion_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rejection: str | None = None,
    *,
    unchanged: bool = False,
    cleanup_hold: bool = False,
    already_present: bool = False,
) -> tuple[Path, Path, Path, list[str], dict[str, Any]]:
    """Synthetic sequencing data only; no native origin, artifact or registry proof."""
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    root = tmp_path / "source"
    target = root / source.MANIFEST_PATH
    target.parent.mkdir(parents=True)
    manifest = _synthetic_prometheus_manifest()
    raw_root = source.canonical_data(
        {
            "schemaVersion": 2,
            "mediaType": source.OCI_MANIFEST,
            "layers": manifest["selection"]["layers"],
        }
    )
    if unchanged:
        manifest["selection"]["manifest_digest"] = "sha256:" + source.sha(raw_root)
        manifest["selection"]["runtime_ref"] = (
            source.IMAGE_REPOSITORY + "@" + manifest["selection"]["manifest_digest"]
        )
    if rejection == "prepared":
        manifest.update(phase="source_prepared", selection=None, candidate=None)
    target.write_bytes(source.canonical_data(manifest))
    work = tmp_path / "publication"
    config = tmp_path / "prometheus-publisher-auth-123-1"
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"ref": "refs/heads/main", "before": "b" * 40}))
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN", "DOCKER_CONFIG"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_REPOSITORY_OWNER": source.GHCR_OWNER,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_EVENT_PATH": str(event_path),
        "RUNNER_TEMP": str(tmp_path),
        "GH_TOKEN": "synthetic.readonly.token",
        "GITHUB_TOKEN": "synthetic.writer." + "z." * 260,
    }.items():
        monkeypatch.setenv(key, value)
    trace: list[str] = []
    payload = tmp_path / "payload"
    payload.mkdir()
    for filename in ("sbom.spdx.json", "provenance-bundle.jsonl", "sbom-bundle.jsonl"):
        (payload / filename).write_text("synthetic signed-bundle transport fixture\n")
    tool = tmp_path / "retained-tool"
    tool.write_bytes(b"nonexecuted synthetic tool")
    candidate = {
        "tool": tool,
        "tool_record": {"coordinates": {"binary_sha256": source.file_hash(tool)}, "base": {}},
        "layout": tmp_path / "layout",
        "graph": {"synthetic": True},
        "payload": payload,
    }
    if rejection == "tool":
        candidate["tool_record"]["coordinates"]["binary_sha256"] = "0" * 64

    def candidate_input(*args: Any) -> dict[str, Any]:
        trace.append("candidate")
        assert not config.exists()
        if rejection in {"input", "artifact", "native", "scanner"}:
            raise source.QualificationError("synthetic_reject_" + rejection)
        return candidate

    def admission(*args: Any) -> dict[str, Any]:
        trace.append("event")
        assert not config.exists()
        if rejection == "event":
            raise source.QualificationError("synthetic_reject_event")
        return {"mode": "unchanged_published" if unchanged else "new_main_selection"}

    identity = {
        "repository": {"id": 1043311030},
        "owner": {"id": 169792616},
        "package": {"id": 9374404},
    }

    def package(api: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        trace.append("package")
        if rejection == "package":
            raise source.QualificationError("synthetic_reject_package")
        selection = manifest["selection"]
        tag = "prometheus-3.15.0-" + selection["manifest_digest"][7:]
        visible = unchanged or already_present or "copy" in trace or rejection == "tag"
        digest = "sha256:" + "f" * 64 if rejection == "tag" else selection["manifest_digest"]
        return identity, [
            {"id": 1, "name": digest, "metadata": {"container": {"tags": [tag] if visible else []}}}
        ]

    def predecessor(*args: Any) -> dict[str, str]:
        trace.append("predecessor")
        assert not config.exists()
        if rejection == "predecessor":
            raise source.QualificationError("synthetic_reject_predecessor")
        return {"synthetic": "positive predecessor"}

    class FixtureAPI:
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            self.private, self.evidence, self.deadline = private, evidence, deadline
            private.mkdir()
            (private / "home").mkdir()
            self.gh = "/synthetic/gh"
            self.environment = {"PATH": "/usr/bin:/bin", "GH_TOKEN": "synthetic.readonly.token"}
            self.cleanup_deadline: float | None = None
            self.main_reads = 0

        def json(self, endpoint: str) -> dict[str, Any]:
            if "/jobs?" in endpoint:
                return {"total_count": 2}
            assert endpoint.endswith("/git/ref/heads/main")
            self.main_reads += 1
            bad = rejection == "main-before-credentials" or (
                rejection == "main-before-write" and self.main_reads == 2
            )
            return {"object": {"sha": "c" * 40 if bad else "a" * 40}}

        def pages(self, *args: Any) -> list[dict[str, str]]:
            return [
                {"name": name, "head_sha": "a" * 40, "conclusion": "success", "status": "completed"}
                for name in ("build", "security-scan")
            ]

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            if "login" in argv:
                trace.append("login")
                assert trace[:2] == ["event", "predecessor" if unchanged else "candidate"]
                assert "package" in trace and config.is_dir()
                assert kwargs["input_data"] == source.os.environ["GITHUB_TOKEN"].encode() + b"\n"
                assert not {"GH_TOKEN", "GITHUB_TOKEN"}.intersection(kwargs["environment"])
                assert source.os.environ["GITHUB_TOKEN"] not in " ".join(argv)
                (config / "config.json").write_text(
                    '{"auths":{"ghcr.io":{"auth":"synthetic-private"}}}'
                )
                (config / "config.json").chmod(0o600)
                if rejection == "login":
                    raise source.QualificationError("synthetic_login_failed")
            elif "attestation" in argv:
                trace.append("verify")
                assert "pullback" in trace and config.is_dir()
                assert argv[argv.index("--bundle") + 1].startswith(str(work / "evidence"))
                assert (
                    argv[argv.index("--source-digest") + 1]
                    == manifest["candidate"]["producer"]["source_head"]
                )
                assert (
                    argv[argv.index("--source-ref") + 1]
                    == manifest["candidate"]["producer"]["source_ref"]
                )
                assert (
                    argv[argv.index("--signer-workflow") + 1]
                    == source.GHCR_REPOSITORY + "/.github/workflows/build.yml"
                )
                assert argv[argv.index("--repo") + 1] == source.GHCR_REPOSITORY
                if argv[argv.index("--bundle") + 1].endswith("sbom-bundle.jsonl"):
                    assert (
                        argv[argv.index("--predicate-type") + 1] == "https://spdx.dev/Document/v2.3"
                    )
                else:
                    assert "--predicate-type" not in argv
                assert "--deny-self-hosted-runners" in argv and argv[-2:] == ["--format", "json"]
                if rejection == "verification":
                    raise source.QualificationError("synthetic_verification_failed")
                return b"[]\n"
            elif "--from-oci-layout" in argv:
                trace.append("copy")
            elif "--to-oci-layout" in argv:
                trace.append("pullback")
            else:
                assert unchanged and "imagetools" in argv
                trace.append("manifest-pullback")
                return raw_root
            return b""

        def begin_cleanup(self) -> float:
            if self.cleanup_deadline is None:
                self.cleanup_deadline = source.time.monotonic() + 2
            return self.cleanup_deadline

        def close(self) -> None:
            trace.append("owned-cleanup")
            self.begin_cleanup()
            if cleanup_hold:
                raise source.QualificationError("GHCR_unknown_or_reused_group_member")
            source.shutil.rmtree(self.private)

    monkeypatch.setattr(source, "GitHubRead", FixtureAPI)
    monkeypatch.setattr(source, "event_admission", admission)
    monkeypatch.setattr(source, "candidate_payload", candidate_input)
    monkeypatch.setattr(source, "existing_public_package", package)
    monkeypatch.setattr(source, "require_publication_predecessor", predecessor)
    monkeypatch.setattr(
        source.shutil, "which", lambda name: "/synthetic/docker" if name == "docker" else None
    )
    monkeypatch.setattr(source, "validate_oci_graph", lambda *args: candidate["graph"])
    monkeypatch.setattr(
        source,
        "compare_pair",
        lambda a, b: None if a == b else pytest.fail("pullback bytes changed"),
    )
    monkeypatch.setattr(
        source,
        "pack_layout",
        lambda layout, path: path.write_bytes(b"synthetic retained exact bytes"),
    )
    return root, work, config, trace, manifest


@pytest.mark.parametrize(
    "rejection",
    [
        "event",
        "prepared",
        "input",
        "artifact",
        "tool",
        "native",
        "scanner",
        "package",
        "tag",
        "main-before-credentials",
        "predecessor",
    ],
)
def test_promote_rejection_precedes_registry_directory_and_login(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rejection: str
) -> None:
    root, work, config, trace, _manifest = _promotion_fixture(
        monkeypatch, tmp_path, rejection, unchanged=rejection == "predecessor"
    )
    with pytest.raises(source.QualificationError):
        source.promote_image(work, root, 30, 2)
    assert "login" not in trace and "copy" not in trace
    assert not config.exists()
    assert not (work / "evidence/publication.json").exists()


@pytest.mark.parametrize("unchanged,already_present", [(False, False), (False, True), (True, True)])
def test_promote_exact_pullback_and_original_bundles_precede_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, unchanged: bool, already_present: bool
) -> None:
    root, work, config, trace, _manifest = _promotion_fixture(
        monkeypatch, tmp_path, unchanged=unchanged, already_present=already_present
    )
    result = source.promote_image(work, root, 30, 2)
    assert result["status"] == "observed_published_exact_immutable_subject"
    assert not config.exists()
    if unchanged:
        assert "candidate" not in trace and "verify" not in trace and "copy" not in trace
        assert (
            trace.index("predecessor")
            < trace.index("login")
            < trace.index("manifest-pullback")
            < trace.index("owned-cleanup")
        )
    else:
        assert ("copy" in trace) is (not already_present)
        if not already_present:
            assert trace.index("login") < trace.index("copy") < trace.index("pullback")
        assert (
            trace.index("candidate")
            < trace.index("package")
            < trace.index("login")
            < trace.index("pullback")
            < trace.index("verify")
            < trace.index("owned-cleanup")
        )
        assert trace.count("verify") == 2
        assert (work / "evidence/original-provenance-verification.json").read_bytes() == b"[]\n"
        assert (work / "evidence/original-sbom-verification.json").read_bytes() == b"[]\n"


@pytest.mark.parametrize("failure", ["login", "main-before-write", "verification"])
def test_promote_operation_failure_cleans_credentials_without_success_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str
) -> None:
    root, work, config, trace, _manifest = _promotion_fixture(monkeypatch, tmp_path, failure)
    with pytest.raises(source.QualificationError):
        source.promote_image(work, root, 30, 2)
    assert not config.exists() and "owned-cleanup" in trace
    assert not (work / "evidence/publication.json").exists()
    assert ("copy" in trace) is (failure == "verification")


def test_promote_primary_failure_and_uncertain_cleanup_retain_private_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, work, config, _trace, _manifest = _promotion_fixture(
        monkeypatch, tmp_path, "verification", cleanup_hold=True
    )
    with pytest.raises(source.QualificationError, match="synthetic_verification_failed"):
        source.promote_image(work, root, 30, 2)
    assert config.is_dir() and (work / "GitHub-private").is_dir()
    assert not (work / "evidence/publication.json").exists()
    assert (
        "Publisher cleanup also failed:GHCR_unknown_or_reused_group_member"
        in capsys.readouterr().err
    )


def test_GHCR_observation_job_has_only_read_permission_and_exact_public_artifact() -> None:
    import yaml

    workflow = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".github/workflows/build.yml").read_text()
    )
    job = workflow["jobs"]["prometheus-ghcr-package-qualification"]
    assert (
        job["if"]
        == "github.event_name == 'workflow_dispatch' && inputs.mode == 'prometheus-source-qualify' && github.repository == 'Katsiarynakavaleuskaya/PulsePlate'"
    )
    assert job["permissions"] == {"contents": "read", "packages": "read"}
    assert (
        job["timeout-minutes"]
        == "${{ fromJSON(vars.PROMETHEUS_GHCR_QUALIFICATION_TIMEOUT_MINUTES || '3') }}"
    )
    assert job["env"] == {
        "PROMETHEUS_GHCR_QUALIFICATION_SECONDS": "90",
        "PROMETHEUS_GHCR_CLEANUP_SECONDS": "30",
    }
    steps = job["steps"]
    assert steps[1]["with"] == {"persist-credentials": False, "ref": "${{ github.sha }}"}
    assert "\"$GITHUB_RUN_ATTEMPT\" != '1'" in steps[0]["run"]
    assert [step.get("env") for step in steps if "env" in step] == [
        {"GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}"}
    ]
    observe, retain = steps[3], steps[4]
    assert observe["id"] == "package" and "--qualify-existing-ghcr-package" in observe["run"]
    assert '--timeout-seconds "$PROMETHEUS_GHCR_QUALIFICATION_SECONDS"' in observe["run"]
    assert '--cleanup-seconds "$PROMETHEUS_GHCR_CLEANUP_SECONDS"' in observe["run"]
    assert retain["if"] == "${{ success() && steps.package.outputs.qualified == 'true' }}"
    assert (
        retain["with"]["path"]
        == "${{ runner.temp }}/ghcr-public-${{ github.run_id }}-${{ github.run_attempt }}/qualification.json"
    )
    assert retain["with"]["if-no-files-found"] == "error"
    assert job["outputs"] == {"qualified": "${{ steps.package.outputs.qualified }}"}
    serialized = json.dumps(job)
    for forbidden in (
        "packages: write",
        "docker login",
        "docker build",
        "go build",
        "GHCR_READ_TOKEN",
        "DHI",
        "GITHUB_ENV",
        "always()",
        "*.stdout",
        "*.stderr",
    ):
        assert forbidden not in serialized
    # Real heavy jobs are absent at this stage; this test makes no heavy dependency claim.


def test_selected_Main_object_is_distinct_from_download_identity() -> None:
    objects = [
        {"Path": source.ROOT_MODULE, "Main": True, "UnknownNativeField": {"retained": 1}},
        {"Path": "golang.org/x/net", "Version": "v0.60.0", "GoModSum": "h1:synthetic"},
    ]
    raw = b"\n".join(json.dumps(value).encode() for value in objects)
    assert source.decode_selected_modules(raw) == {value["Path"]: value for value in objects}
    with pytest.raises(source.QualificationError):
        source.decode_modules(raw)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-root",
        "wrong-root",
        "duplicate-path",
        "Main-int",
        "dependency-no-version",
        "Path-none",
        "Path-int",
        "Replace-error",
    ],
)
def test_selected_modules_reject_incomplete_or_conflicting_native_identity(fault: str) -> None:
    values = [{"Path": source.ROOT_MODULE, "Main": True}, {"Path": "x", "Version": "v1.0.0"}]
    if fault == "missing-root":
        values.pop(0)
    elif fault == "wrong-root":
        values[0]["Path"] = "other/root"
    elif fault == "duplicate-path":
        values.append({"Path": "x", "Version": "v2.0.0"})
    elif fault == "Main-int":
        values[0]["Main"] = 1
    elif fault == "dependency-no-version":
        values[1].pop("Version")
    elif fault == "Path-none":
        values[1]["Path"] = None
    elif fault == "Path-int":
        values[1]["Path"] = 1
    else:
        values[1]["Replace"] = {"Path": "replacement", "Error": {"Err": "synthetic"}}
    with pytest.raises(source.QualificationError):
        source.decode_selected_modules(b"\n".join(json.dumps(value).encode() for value in values))


def test_replay_coordinate_correspondence_retains_every_other_native_field(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    left = {
        "Path": "x",
        "Version": "v1",
        "Dir": str(a / "modules/x"),
        "GoMod": str(a / "modules/x/go.mod"),
        "Origin": {"URL": "https://example.invalid/x"},
        "Replace": {"Path": "replacement", "Dir": str(a / "source/local")},
        "Unknown": [1, 2],
    }
    right = json.loads(json.dumps(left).replace(str(a), str(b)))
    observed = source.replay_coordinates(left, a / "source", a / "modules", download=False)
    assert observed == source.replay_coordinates(right, b / "source", b / "modules", download=False)
    assert observed["Origin"] == left["Origin"] and observed["Unknown"] == [1, 2]
    assert left["Dir"] == str(a / "modules/x")
    right["Unknown"] = [2, 1]
    assert observed != source.replay_coordinates(right, b / "source", b / "modules", download=False)
    left["Unknown"] = "arbitrary text containing " + str(a / "source")
    right["Unknown"] = "arbitrary text containing " + str(b / "source")
    assert source.replay_coordinates(
        left, a / "source", a / "modules", download=False
    ) != source.replay_coordinates(right, b / "source", b / "modules", download=False)
    for path in (str(a / "modules") + "/../escape", str(a / "modules") + "-alias/x", "/unbound/x"):
        with pytest.raises(source.QualificationError):
            source.replay_coordinates({"Dir": path}, a / "source", a / "modules", download=False)


@pytest.mark.parametrize(
    "extra",
    [
        ["--qualify-existing-ghcr-package", "--public-output", "public.json"],
        ["--public-output", "public.json"],
        ["--derive-xnet06"],
    ],
)
def test_fixed_derivation_selector_rejects_mixed_or_abbreviated_modes_before_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra: list[str]
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Selector rejected after protected effect")

    monkeypatch.setattr(source, "qualify", forbidden)
    monkeypatch.setattr(source, "qualify_existing_ghcr_package", forbidden)
    monkeypatch.setattr(source.signal, "signal", forbidden)
    args = [
        "qualifier",
        "--work-dir",
        str(tmp_path / "uncreated"),
        "--timeout-seconds",
        "900",
        "--cleanup-seconds",
        "120",
    ]
    if extra != ["--derive-xnet06"]:
        args.append("--derive-xnet060")
    monkeypatch.setattr(source.sys, "argv", args + extra)
    with pytest.raises(SystemExit) as error:
        source.main()
    assert error.value.code == 2
    assert not (tmp_path / "uncreated").exists()


@pytest.mark.parametrize(
    "fault",
    ["none", "base-lock", "get-error", "derived-download-sum", "b-lock-mismatch", "get-nonlock"],
)
def test_derivation_controller_uses_two_clean_original_fixed_get_replays_or_stops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    """Synthetic native transcript only; it cannot qualify Go, source or closure."""
    work = tmp_path / "work"
    work.mkdir()
    evidence = work / "evidence"
    evidence.mkdir()
    original = {"go.mod": b"original module\n", "go.sum": b"original sums\n"}
    derived = {"go.mod": b"derived module\n", "go.sum": b"derived sums\n"}
    monkeypatch.setattr(source, "LOCKS", {name: source.sha(raw) for name, raw in original.items()})
    go = work / "go"
    (go / "bin").mkdir(parents=True)
    (go / "bin/go").write_bytes(b"inert Go fixture")
    ui = work / "ui"
    ui.mkdir()
    downloads = work / "downloads"
    downloads.mkdir()
    a = work / "source"
    a.mkdir()

    def populate(target: Path) -> None:
        for name, raw in original.items():
            (target / name).write_bytes(raw)
        (target / "retained.go").write_bytes(b"inert source\n")

    populate(a)

    def extracted(
        artifact: source.Artifact, archive: Path, target: Path, deadline: float
    ) -> list[dict[str, Any]]:
        assert not target.exists()
        target.mkdir()
        populate(target)
        return []

    monkeypatch.setattr(source, "extract", extracted)
    monkeypatch.setattr(source, "stage_ui", lambda *args: {"synthetic": True})
    transcript: list[tuple[list[str], dict[str, str], Path]] = []

    class FakeNative:
        deadline = source.time.monotonic() + 900

        def __init__(self) -> None:
            self.evidence = evidence

        def run(
            self, argv: list[str], name: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            transcript.append((argv, dict(env), cwd))
            if argv[0] == "/usr/bin/docker":
                if "ps" in argv:
                    return b""
                if "pull" in argv:
                    return b""
                return json.dumps(
                    [
                        {
                            "Id": source.BASE_CONFIG,
                            "Os": "linux",
                            "Architecture": "amd64",
                            "RepoDigests": [source.BASE],
                            "Config": {"Env": []},
                        }
                    ]
                ).encode()
            command = argv[1:]
            changed = (cwd / "go.mod").read_bytes() != original["go.mod"]
            version = "v0.60.0" if changed else "v0.58.0"
            if command == ["get", "golang.org/x/net@v0.60.0"]:
                assert env["GOFLAGS"] == "" and not changed
                if fault == "get-error":
                    raise source.QualificationError("synthetic_get_failure")
                for file, raw in derived.items():
                    (cwd / file).write_bytes(
                        raw
                        + (
                            b"different\n"
                            if fault == "b-lock-mismatch"
                            and cwd.name == "source-b"
                            and file == "go.sum"
                            else b""
                        )
                    )
                if fault == "get-nonlock":
                    (cwd / "retained.go").write_bytes(b"unexpected source")
                return b""
            assert env["GOFLAGS"] == "-mod=readonly"
            if command == ["version"]:
                return source.GO_VERSION.encode()
            if command == ["mod", "edit", "-json"]:
                if fault == "base-lock" and not changed:
                    (cwd / "go.sum").write_bytes(b"unexpected sum")
                return json.dumps(
                    {
                        "Module": {"Path": source.ROOT_MODULE},
                        "Go": "1.26.0",
                        "Unknown": {"retain": True},
                    }
                ).encode()
            if command == ["mod", "download", "-json"]:
                directory = Path(env["GOMODCACHE"]) / ("xnet@" + version)
                directory.mkdir(exist_ok=True)
                (directory / "go.mod").write_bytes(b"inert cache")
                if changed and fault == "derived-download-sum":
                    (cwd / "go.sum").write_bytes(b"late sum write")
                return json.dumps(
                    {
                        "Path": "golang.org/x/net",
                        "Version": version,
                        "Dir": str(directory),
                        "GoMod": str(directory / "go.mod"),
                    }
                ).encode()
            if command == ["mod", "verify"]:
                return b"all modules verified\n"
            if command == ["list", "-m", "-json", "all"]:
                values = [
                    {
                        "Path": source.ROOT_MODULE,
                        "Main": True,
                        "Dir": str(cwd),
                        "GoMod": str(cwd / "go.mod"),
                    },
                    {
                        "Path": "golang.org/x/net",
                        "Version": version,
                        "Dir": str(Path(env["GOMODCACHE"]) / ("xnet@" + version)),
                    },
                ]
                return b"\n".join(json.dumps(value).encode() for value in values)
            if command == ["mod", "graph"]:
                return (source.ROOT_MODULE + " golang.org/x/net@" + version + "\n").encode()
            raise AssertionError(command)

    offline: list[tuple[str, Path]] = []

    def observed(
        native: Any, root: Path, tool: Path, modules: Path, expected: dict[str, bytes], *args: Any
    ) -> dict[str, Any]:
        assert source._derivation_locks(root) == expected
        offline.append((root.name, modules))
        return {
            "full_native_package_objects": {
                "prometheus": {"p": {"ImportPath": "p"}},
                "promtool": {"t": {"ImportPath": "t"}},
            }
        }

    monkeypatch.setattr(source, "_derivation_offline", observed)
    report: dict[str, Any] = {"UI_transform": {"synthetic": True}}
    native = FakeNative()
    if fault == "none":
        source.derive_xnet060_observe(
            native, work, downloads, a, go, ui, {}, "/usr/bin/docker", work, {}, report
        )
        assert len(report["module_derivation"]["replays"]) == 2
        assert len(offline) == 2 and offline[0][1] != offline[1][1]
        assert (evidence / "a-module-derivation.patch").read_bytes() == (
            evidence / "b-module-derivation.patch"
        ).read_bytes()
    else:
        with pytest.raises(source.QualificationError):
            source.derive_xnet060_observe(
                native, work, downloads, a, go, ui, {}, "/usr/bin/docker", work, {}, report
            )
    gets = [(argv, env, cwd) for argv, env, cwd in transcript if argv[1:2] == ["get"]]
    assert len(gets) == (
        2 if fault in ("none", "b-lock-mismatch") else 0 if fault == "base-lock" else 1
    )
    for argv, env, cwd in gets:
        assert argv[1:] == ["get", "golang.org/x/net@v0.60.0"] and env["GOFLAGS"] == ""
    for argv, env, cwd in transcript:
        if argv[0] != "/usr/bin/docker" and argv[1:2] != ["get"]:
            assert env["GOFLAGS"] == "-mod=readonly"
        if argv[1:3] == ["mod", "download"]:
            assert argv[1:] == ["mod", "download", "-json"]


@pytest.mark.parametrize("missing", [False, True])
def test_derivation_offline_keeps_both_production_graphs_and_existing_sandbox_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, missing: bool
) -> None:
    """Synthetic owned-container outcomes; no native executable is started."""
    root, go, modules, evidence = [
        tmp_path / name for name in ("source", "go", "modules", "evidence")
    ]
    for path in (root, go / "bin", modules, evidence):
        path.mkdir(parents=True)
    (root / "go.mod").write_bytes(b"frozen mod")
    (root / "go.sum").write_bytes(b"frozen sum")
    (go / "bin/go").write_bytes(b"inert tool")
    (modules / "cache").write_bytes(b"inert cache")
    frozen = source._derivation_locks(root)
    remainder = source._derivation_nonlocks(root, source.time.monotonic() + 900)
    created: list[list[str]] = []

    class FakeNative:
        deadline = source.time.monotonic() + 900

        def __init__(self) -> None:
            self.evidence = evidence

        def run(self, argv: list[str], *args: Any, **kwargs: Any) -> bytes:
            if "create" in argv:
                created.append(argv)
                return b"owned"
            return b"[{}]"

    monkeypatch.setattr(source, "validate_container", lambda *args: None)

    def completed(
        native: Any,
        docker: str,
        config: Path,
        name: str,
        expected: dict[str, Any],
        label: str,
        *args: Any,
    ) -> tuple[bytes, dict[str, Any]]:
        command = expected["command"]
        if command == ["version"]:
            raw = source.GO_VERSION.encode()
        elif command == ["mod", "verify"]:
            raw = b"all modules verified"
        else:
            selected = command[-1].rsplit("/", 1)[-1]
            raw = package_stream("prometheus" if missing and selected == "promtool" else selected)
        return raw, {"Running": False, "ExitCode": 0, "OOMKilled": False}

    monkeypatch.setattr(source, "start_owned", completed)
    arguments = (
        FakeNative(),
        root,
        go,
        modules,
        frozen,
        remainder,
        source.file_hash(go / "bin/go"),
        "a",
        "/usr/bin/docker",
        tmp_path,
        {"Id": source.BASE_CONFIG, "Config": {"Env": []}},
        "synthetic-owner",
        [],
        {},
        {},
        tmp_path,
    )
    if missing:
        with pytest.raises(source.QualificationError):
            source._derivation_offline(*arguments)
    else:
        result = source._derivation_offline(*arguments)
        assert set(result["command_observations"]) == {"prometheus", "promtool"}
        assert set(result["full_native_package_objects"]) == {"prometheus", "promtool"}
        assert len(result["container_completion"]) == 4
    assert len(created) == 4
    for argv in created:
        assert argv[argv.index("--network") + 1] == "none"
        assert argv[argv.index("--user") + 1] == "65532:65532"
        assert "--read-only" in argv
        assert all(
            value.endswith(",readonly")
            for index, value in enumerate(argv)
            if index and argv[index - 1] == "--mount"
        )


def _consumer_fixture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, published: bool, fault: str | None = None
) -> tuple[Path, Path, Path, list[str]]:
    """Synthetic admission ordering only, not authentic artifact/native evidence."""
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    root = tmp_path / "source"
    path = root / source.MANIFEST_PATH
    path.parent.mkdir(parents=True)
    manifest = _synthetic_prometheus_manifest()
    selection = manifest["selection"]
    raw = source.canonical_data(
        {
            "schemaVersion": 2,
            "mediaType": source.OCI_MANIFEST,
            "config": {
                "mediaType": source.OCI_CONFIG,
                "size": 1,
                "digest": selection["config_digest"],
            },
            "layers": selection["layers"],
        }
    )
    selection["manifest_digest"] = "sha256:" + source.sha(raw)
    selection["runtime_ref"] = source.IMAGE_REPOSITORY + "@" + selection["manifest_digest"]
    path.write_bytes(source.canonical_data(manifest))
    source.read_image_manifest(path)
    image = {
        "Id": selection["config_digest"],
        "Os": "linux",
        "Architecture": "amd64",
        "RootFS": {"Layers": selection["diff_ids"]},
        "Config": {
            "User": "65532:65532",
            "Entrypoint": ["/bin/prometheus"],
            "WorkingDir": "/prometheus",
            "Volumes": None,
            "Cmd": [
                "--config.file=/etc/prometheus/prometheus.yml",
                "--storage.tsdb.path=/prometheus",
            ],
        },
        "RepoDigests": [selection["runtime_ref"]],
    }
    source.native_image_contract(image, selection, local=not published)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"head": {"sha": "a" * 40}}}))
    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_READ_TOKEN",
        "GHCR_TOKEN",
        "DOCKER_CONFIG",
        "DOCKER_AUTH_CONFIG",
        "NETRC",
        "DEVPI_CI_USER",
        "DEVPI_CI_PASSWORD",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    token = "synthetic.reader." + "r." * 260
    for key, value in {
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_EVENT_PATH": str(event),
        "GITHUB_REPOSITORY_OWNER": source.GHCR_OWNER,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "RUNNER_TEMP": str(tmp_path),
        "GH_TOKEN": "synthetic.api",
        "GITHUB_TOKEN": "synthetic.api",
    }.items():
        monkeypatch.setenv(key, value)
    if fault != "missing-token":
        monkeypatch.setenv("GHCR_READ_TOKEN", token)
    if fault == "owner":
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "foreign")
    trace: list[str] = []
    work = tmp_path / "consumer"
    reader = tmp_path / "prometheus-consumer-auth-123-1"
    clock = [100.0]
    monkeypatch.setattr(source.time, "monotonic", lambda: clock[0])

    class Native:
        def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
            self.deadline = deadline
            self.records: list[dict[str, Any]] = []

        def run(self, argv: list[str], label: str, env: dict[str, str], **kwargs: Any) -> bytes:
            assert not reader.exists()
            assert not any(key in env for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN"))
            trace.append("load" if "load" in argv else "inspect")
            return source.canonical_data(image)

    class API:
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            self.private = private
            private.mkdir(mode=0o700)
            (private / "home").mkdir(mode=0o700)

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            assert published
            if "login" in argv:
                trace.append("login")
                assert kwargs["input_data"] == token.encode() + b"\n"
                assert token not in " ".join(argv)
                leaf = reader / "config.json"
                leaf.write_bytes(b"synthetic configuration fixture")
                leaf.chmod(0o600)
                if fault in {"login", "login-cleanup"}:
                    raise source.QualificationError("GitHub_native_failed")
            elif "pull" in argv:
                trace.append("pull")
            else:
                trace.append("raw")
                return raw
            return b""

        def begin_cleanup(self) -> float:
            return clock[0] + 2

        def close(self) -> None:
            trace.append("cleanup")
            if fault in {"cleanup", "login-cleanup"}:
                raise source.QualificationError("GHCR_unknown_or_reused_group_member")
            source.shutil.rmtree(self.private)

    def admission(*args: Any) -> dict[str, Any]:
        trace.append("event")
        if fault == "event":
            raise source.QualificationError("consumer_actual_open_PR")
        return {
            "mode": "unchanged_published" if published else "changed_pr_candidate",
            "head": "a" * 40,
            "publisher_head": "b" * 40,
        }

    def candidate(*args: Any) -> dict[str, Any]:
        trace.append("candidate")
        assert not reader.exists()
        if fault == "candidate":
            raise source.QualificationError("artifact_identity_expiry_size")
        return {"docker_archive": tmp_path / "synthetic-image.docker.tar"}

    def predecessor(*args: Any) -> dict[str, str]:
        trace.append("predecessor")
        if fault == "predecessor":
            clock[0] += 100
            raise source.QualificationError("positive_publication_predecessor_pending_or_missing")
        return {
            "run": {
                "id": 1,
                "head_sha": "b" * 40,
                "head_branch": "main",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
            },
            "job": {
                "id": 1,
                "head_sha": "b" * 40,
                "name": "prometheus-publish",
                "status": "completed",
                "conclusion": "success",
            },
        }

    def package(*args: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        trace.append("public-package")
        repository = {
            "id": 1043311030,
            "full_name": source.GHCR_REPOSITORY,
            "owner": {"id": 169792616, "login": source.GHCR_OWNER},
        }
        package_data = {
            "id": 9374404,
            "name": source.GHCR_PACKAGE,
            "package_type": "container",
            "visibility": "public",
            "owner": repository["owner"],
            "repository": repository,
        }
        if fault == "package":
            package_data["visibility"] = "private"
        if fault == "foreign-repo":
            package_data["repository"] = {"id": 1043311030, "full_name": "foreign/PulsePlate"}
        identity = source.ghcr_identity(repository, package_data)
        if fault == "subject":
            return identity, []
        return identity, [
            {
                "id": 1,
                "name": selection["manifest_digest"],
                "metadata": {
                    "container": {"tags": ["prometheus-3.15.0-" + selection["manifest_digest"][7:]]}
                },
            }
        ]

    monkeypatch.setattr(source, "Native", Native)
    monkeypatch.setattr(source, "GitHubRead", API)
    monkeypatch.setattr(source, "event_admission", admission)
    monkeypatch.setattr(source, "candidate_payload", candidate)
    monkeypatch.setattr(source, "require_publication_predecessor", predecessor)
    monkeypatch.setattr(source, "existing_public_package", package)
    monkeypatch.setattr(source.shutil, "which", lambda name: "/synthetic/docker")
    return root, work, reader, trace


@pytest.mark.parametrize("published", [False, True])
def test_consumer_owns_admitted_reader_cleanup_before_local_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, published: bool
) -> None:
    root, work, reader, trace = _consumer_fixture(monkeypatch, tmp_path, published=published)
    result = source.consume_image(work, root, 30, 2)
    assert not reader.exists() and not (work / "GitHub-private").exists()
    if published:
        assert trace == [
            "event",
            "predecessor",
            "public-package",
            "login",
            "pull",
            "raw",
            "cleanup",
            "inspect",
        ]
    else:
        assert trace == ["event", "candidate", "cleanup", "load", "inspect"]
        assert result["runtime_ref"] == result["selection"]["config_digest"]


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("event", "consumer_actual_open_PR"),
        ("candidate", "artifact_identity_expiry_size"),
        ("predecessor", "qualification_deadline"),
        ("package", "GHCR_package_properties"),
        ("missing-token", "consumer_registry_token_missing"),
        ("login", "GitHub_native_failed"),
        ("cleanup", "GHCR_unknown_or_reused_group_member"),
        ("subject", "consumer_published_subject_missing"),
        ("foreign-repo", "GHCR_expected_identity"),
        ("login-cleanup", "GitHub_native_failed"),
        ("owner", "consumer_registry_owner"),
    ],
)
def test_consumer_rejects_at_intended_admission_and_retains_uncertain_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str, diagnostic: str
) -> None:
    root, work, reader, trace = _consumer_fixture(
        monkeypatch, tmp_path, published=fault != "candidate", fault=fault
    )
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.consume_image(work, root, 30, 2)
    assert "load" not in trace and "inspect" not in trace
    assert reader.exists() is (fault in {"cleanup", "login-cleanup"})
    if fault not in {"login", "cleanup", "login-cleanup"}:
        assert "login" not in trace
    assert not (work / "evidence/consumer.json").exists()

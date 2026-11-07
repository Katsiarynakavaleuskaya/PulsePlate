"""Offline security contracts for the hosted metadata-only source qualifier."""

from __future__ import annotations

from dataclasses import replace
import base64
import hashlib
import copy
from email.message import Message
import gzip
import io
import json
from pathlib import Path
import re
import signal
import stat
import tarfile
import time
from typing import Any, cast
from urllib.request import HTTPSHandler, ProxyHandler, build_opener
from urllib.response import addinfourl
import zipfile

import pytest

from scripts.ci import prometheus_source_image as source


@pytest.mark.parametrize("purpose", ["tool", "pair"])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing",
        "extra",
        "duplicate",
        "source",
        "attempt",
        "active",
        "job-source",
        "branch",
        "foreign-PR",
        "current-job",
        "retry-selector",
    ],
)
def test_stabilization_manual_budget_preserves_complete_spent_history(
    monkeypatch: pytest.MonkeyPatch, purpose: str, fault: str | None
) -> None:
    """Synthetic API responses retain the observed historical identities; no build is run."""
    tool_rows = [
        (
            38170923494,
            114563178711,
            "5de54811121079eadbd3f5d8dbbb8720f712530a",
            "codex/dependency-native-runtime-remediation",
            "failure",
        ),
        (
            38192419687,
            114627819440,
            "15097adaa871a900370f6c57a512fe862dddb041",
            "codex/dependency-native-runtime-remediation",
            "failure",
        ),
        (
            38239428418,
            114778090287,
            "f632572057453d57975a397a5b2db64894204be0",
            "codex/dependency-native-runtime-remediation",
            "failure",
        ),
        (
            38269614712,
            114880342307,
            "a18d636138bbab67e96c902b1c61f690263c8b55",
            "codex/dependency-native-runtime-remediation",
            "success",
        ),
        (
            39020247533,
            117360452632,
            "9c1b48f8b3a63bf827543cf69090505c1f157fc6",
            "codex/consolidate-legacy-ownership-guard",
            "success",
        ),
    ]
    tool_rows.append(
        (
            40188825249,
            121155232821,
            "c22d641bc0d4dce56925114c827be6d712db7070",
            "codex/python-setup-security-stabilization",
            "success",
        )
    )
    pair_rows = [
        (
            38291450453,
            114952275845,
            "b732222719f70fa592218d2255324850843e9eea",
            "codex/dependency-native-runtime-remediation",
            "success",
        ),
        (
            39033193167,
            117397709770,
            "e2b86644a9a0264098f57f1bbca5914a3438fbe6",
            "codex/consolidate-legacy-ownership-guard",
            "success",
        ),
    ]
    pair_rows.append(
        (
            40222244853,
            121256136190,
            "7e275934593fa83749c5d89054c019fd4f7c6e89",
            "codex/python-setup-security-stabilization",
            "success",
        )
    )
    branch = "codex/python-setup-security-stabilization"
    head = "a" * 40
    job_name = (
        "prometheus-oras-qualification" if purpose == "tool" else "prometheus-source-build-pair"
    )
    rows = tool_rows if purpose == "tool" else pair_rows
    runs = [
        {
            "id": run,
            "head_sha": revision,
            "head_branch": ref,
            "run_attempt": 1,
            "event": "workflow_dispatch",
            "workflow_id": 99,
            "status": "completed",
            "conclusion": outcome,
            "repository": {"id": 1043311030},
            "head_repository": {"id": 1043311030},
        }
        for run, _, revision, ref, outcome in rows
    ]
    jobs = {
        run: [
            {
                "id": job,
                "run_id": run,
                "head_sha": revision,
                "name": job_name,
                "status": "completed",
                "conclusion": outcome,
            }
        ]
        for run, job, revision, _, outcome in rows
    }
    current = {
        "id": 999,
        "head_sha": head,
        "head_branch": branch,
        "run_attempt": 1,
        "event": "workflow_dispatch",
        "workflow_id": 99,
        "repository": {"id": 1043311030},
        "head_repository": {"id": 1043311030},
    }
    pr = {
        "number": 2497,
        "state": "open",
        "head": {"ref": branch, "sha": head, "repo": {"id": 1043311030}},
        "base": {"ref": "main", "repo": {"id": 1043311030}},
    }
    jobs[999] = [
        {"id": 1999, "run_id": 999, "head_sha": head, "name": job_name, "status": "in_progress"}
    ]
    if fault == "missing":
        runs.pop()
    elif fault == "extra":
        extra = {**runs[-1], "id": 888}
        runs.append(extra)
        jobs[888] = [{**jobs[rows[-1][0]][0], "run_id": 888, "id": 1888}]
    elif fault == "duplicate":
        jobs[rows[0][0]].append(dict(jobs[rows[0][0]][0]))
    elif fault == "source":
        runs[0]["head_sha"] = "b" * 40
    elif fault == "attempt":
        runs[0]["run_attempt"] = 2
    elif fault == "active":
        runs[0]["status"] = "in_progress"
    elif fault == "job-source":
        jobs[rows[0][0]][0]["head_sha"] = "b" * 40
    elif fault == "branch":
        runs[0]["head_branch"] = "unrelated"
    elif fault == "foreign-PR":
        pr["head"]["repo"]["id"] = 1
    elif fault == "current-job":
        jobs[999][0]["status"] = "completed"

    class API:
        def json(self, endpoint: str) -> dict[str, Any]:
            if endpoint.endswith("/runs/999"):
                return current
            if endpoint.endswith("/workflows/build.yml"):
                return {"id": 99, "path": ".github/workflows/build.yml"}
            if endpoint.endswith("/pulls/2497"):
                return pr
            return {"total_count": len(runs) + 1 if "/workflows/" in endpoint else 1}

        def pages(self, endpoint: str, key: str, count: int) -> list[dict[str, Any]]:
            if key == "workflow_runs":
                return [*runs, current]
            return jobs[int(endpoint.split("/runs/")[1].split("/")[0])]

    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    for key, value in {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "999",
        "GITHUB_SHA": head,
        "GITHUB_REF": "refs/heads/" + branch,
    }.items():
        monkeypatch.setenv(key, value)
    selector = source.TOOL_THREE_PREDECESSORS if fault == "retry-selector" else None
    if fault is None:
        result = source.manual_hosted_admission(API(), purpose, prefetch_predecessor=selector)
        assert result["budget"] == (1 if purpose == "tool" else 2)
        assert len(result["actual_prior_invocations"]) == (6 if purpose == "tool" else 3)
    else:
        with pytest.raises(source.QualificationError):
            source.manual_hosted_admission(API(), purpose, prefetch_predecessor=selector)


def _synthetic_ca_bundle(monkeypatch: pytest.MonkeyPatch) -> bytes:
    """Mock the X509 transport only for graph units; actual bundle/TLS proof stays native."""
    import ssl

    data = b"synthetic admitted bundle for graph unit tests\n"
    certificates = [f"synthetic DER {number}".encode() for number in range(148)]

    class Context:
        def load_verify_locations(self, *, cadata: str) -> None:
            assert cadata == data.decode("ascii")

        def get_ca_certs(self, *, binary_form: bool) -> list[bytes]:
            assert binary_form is True
            return certificates

    def context(protocol: int) -> Context:
        assert protocol == ssl.PROTOCOL_TLS_CLIENT
        return Context()

    monkeypatch.setattr(ssl, "SSLContext", context)
    monkeypatch.setattr(source, "BASE_CA_SHA256", source.sha(data))
    monkeypatch.setattr(source, "BASE_CA_BYTES", len(data))
    return data


def _finite_vendor_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, wrong_diff: bool = False
) -> Path:
    """Synthetic graph data only; no native format, origin or build-success fixture."""
    ca = _synthetic_ca_bundle(monkeypatch)
    layout = tmp_path / "vendor"
    (layout / "blobs/sha256").mkdir(parents=True)
    contracts = []
    for index in range(13):
        stream = io.BytesIO()
        rows = []
        with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            names = (
                ("usr", "usr/bin", "etc", "bin")
                if index == 0
                else (
                    ("etc/ssl/certs/ca-certificates.crt",) if index == 12 else (f"vendor-{index}",)
                )
            )
            for name in names:
                member = tarfile.TarInfo(name)
                data = ca if index == 12 else ("synthetic vendor " + str(index)).encode()
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


@pytest.mark.parametrize("ingest", [False, True])
def test_finite_oras_readonly_blobs_keep_one_graph_and_canonical_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ingest: bool
) -> None:
    base, layout, _docker, _result = _finite_constructed(tmp_path, monkeypatch)
    vendor = tmp_path / "vendor"
    for tree in (vendor, layout):
        for path in (tree / "blobs/sha256").iterdir():
            path.chmod(0o444)
        if ingest:
            (tree / "ingest").mkdir()
    source.base_graph(vendor)
    expected = source.validate_oci_graph(layout, base, synthetic=True)
    archive = tmp_path / "readonly.oci.tar"
    source.pack_layout(layout, archive)
    with tarfile.open(archive) as packed:
        members = packed.getmembers()
        assert all(member.isreg() and member.mode == 0o644 for member in members)
        assert not any(
            member.name == "ingest" or member.name.startswith("ingest/") for member in members
        )
    copied = tmp_path / "unpacked"
    source.unpack_layout(archive.read_bytes(), copied)
    source.compare_pair(expected, source.validate_oci_graph(copied, base, synthetic=True))


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("metadata", "layout_regular_leaf"),
        ("unknown", "layout_regular_leaf"),
        ("hardlink", "layout_regular_leaf"),
        ("symlink", "layout_regular_leaf"),
        ("fifo", "layout_regular_leaf"),
        ("foreign", "layout_owner_count"),
        ("ingest-file", "layout_closed_inventory"),
        ("ingest-link", "layout_regular_leaf"),
        ("ingest-foreign", "layout_owner_count"),
        ("ingest-child", "layout_closed_inventory"),
        ("ingest-nested", "layout_closed_inventory"),
        ("count", "layout_owner_count"),
    ],
)
def test_finite_layout_inventory_rejects_unselected_or_nonempty_ingest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    import os

    layout = _finite_vendor_input(tmp_path, monkeypatch)
    expected = {"sha256:" + path.name for path in (layout / "blobs/sha256").iterdir()}
    leaf = next((layout / "blobs/sha256").iterdir())
    if fault == "metadata":
        (layout / "index.json").chmod(0o444)
    elif fault == "unknown":
        p = layout / "blobs/sha256" / ("e" * 64)
        p.write_bytes(b"unknown")
        p.chmod(0o444)
    elif fault == "hardlink":
        os.link(leaf, tmp_path / "second-link")
    elif fault == "symlink":
        leaf.unlink()
        leaf.symlink_to(tmp_path / "not-followed")
    elif fault == "fifo":
        leaf.unlink()
        os.mkfifo(leaf)
    elif fault == "ingest-file":
        (layout / "ingest").write_bytes(b"not a directory")
    elif fault == "ingest-link":
        (layout / "ingest").symlink_to(tmp_path, target_is_directory=True)
    elif fault.startswith("ingest"):
        (layout / "ingest").mkdir()
        if fault == "ingest-child":
            (layout / "ingest/item").write_bytes(b"unadmitted")
        elif fault == "ingest-nested":
            (layout / "ingest/nested").mkdir()
    if fault in ("foreign", "ingest-foreign"):
        target = layout / "ingest" if fault == "ingest-foreign" else leaf
        original = Path.lstat

        def foreign(path: Path) -> os.stat_result:
            value = original(path)
            if path == target:
                fields = list(value)
                fields[4] = os.getuid() + 1
                return os.stat_result(fields)
            return value

        monkeypatch.setattr(Path, "lstat", foreign)
    elif fault == "count":
        for index in range(70):
            digest = source.sha(str(index).encode())
            expected.add("sha256:" + digest)
            (layout / "blobs/sha256" / digest).write_bytes(b"x")
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$") as caught:
        source._layout_inventory(layout, expected)
    facts = caught.value.layout_rejection
    assert facts["predicate"] == diagnostic and facts["observation_error"] is None
    assert len(facts["relative"]) <= 512 and str(tmp_path) not in facts["relative"]
    assert type(facts["uid"]) is int and type(facts["nlink"]) is int
    if fault == "metadata":
        assert facts["mode"] == "0o444" and facts["type"] == "regular"


@pytest.mark.parametrize("fault", ["escaped", "lstat", "diagnostic"])
def test_layout_rejection_retains_bounded_facts_without_replacing_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    import os

    layout = tmp_path / "layout"
    layout.mkdir()
    (layout / "blobs/sha256").mkdir(parents=True)
    leaf = layout / ("\n\t" + ("\x01" * 120))
    leaf.write_bytes(b"unselected")
    leaf.chmod(0o444)
    if fault == "lstat":
        original = Path.lstat

        def uncertain(path: Path) -> os.stat_result:
            if path == leaf:
                raise PermissionError("synthetic observation uncertainty")
            return original(path)

        monkeypatch.setattr(Path, "lstat", uncertain)
    elif fault == "diagnostic":
        original_dump = source.json.dumps

        def failed_description(value: Any, *args: Any, **kwargs: Any) -> str:
            if type(value) is str:
                raise RuntimeError("synthetic optional diagnostic failure")
            return original_dump(value, *args, **kwargs)

        monkeypatch.setattr(source.json, "dumps", failed_description)
    exception = PermissionError if fault == "lstat" else source.QualificationError
    with pytest.raises(exception) as caught:
        source._layout_inventory(layout, set())
    facts = caught.value.layout_rejection
    if fault == "lstat":
        assert facts["observation_error"] == "PermissionError"
    elif fault == "diagnostic":
        assert str(caught.value) == "layout_regular_leaf"
        assert facts == {"predicate": "layout_regular_leaf", "observation_error": "RuntimeError"}
    else:
        assert "\\n" in facts["relative"] and "\\t" in facts["relative"]
        assert len(facts["relative"]) == 512 and facts["relative_truncated"] is True
        assert "\n" not in facts["relative"] and "\t" not in facts["relative"]


def test_actual_layout_rejection_reaches_tool_report_and_keeps_cleanup_separate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = _finite_vendor_input(tmp_path, monkeypatch)
    (tree / "index.json").chmod(0o444)
    locks = {"go.mod": b"original", "go.sum": b"sums"}
    monkeypatch.setattr(source, "ORAS_LOCKS", {key: source.sha(raw) for key, raw in locks.items()})
    monkeypatch.setattr(source, "ORAS_LICENSE", source.sha(b"license"))

    class API:
        def __init__(self, *args: Any) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(source, "GitHubRead", API)
    monkeypatch.setattr(
        source,
        "manual_hosted_admission",
        lambda *args, **kwargs: {
            "head": "synthetic",
            "ref": "refs/heads/codex/python-setup-security-stabilization",
        },
    )
    monkeypatch.setattr(source, "authenticate_producer_inputs", lambda *args, **kwargs: None)
    monkeypatch.setattr(source, "tool_input_projection", lambda root: {"synthetic": True})
    monkeypatch.setattr(source.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(source, "acquire", lambda *args, **kwargs: None)

    def extract(
        artifact: Any, archive: Path, destination: Path, deadline: float | None
    ) -> list[dict[str, Any]]:
        destination.mkdir()
        if artifact == source.ORAS_SOURCE:
            for name, raw in {**locks, "LICENSE": b"license"}.items():
                (destination / name).write_bytes(raw)
        return []

    monkeypatch.setattr(source, "extract", extract)

    def rejected(*args: Any, **kwargs: Any) -> None:
        return source._layout_inventory(
            tree, {"sha256:" + p.name for p in (tree / "blobs/sha256").iterdir()}
        )

    monkeypatch.setattr(source, "prefetch_modules", rejected)
    monkeypatch.setattr(
        source, "cleanup_owned", lambda *args, **kwargs: [{"failure": "synthetic_cleanup"}]
    )
    work = tmp_path / "tool"
    with pytest.raises(source.QualificationError, match="^layout_regular_leaf$"):
        source.qualify_tool(work, tmp_path, 30, 2)
    report = source.one_object((work / "evidence/tool.json").read_bytes())
    assert report["failure"]["code"] == "layout_regular_leaf"
    assert report["failure"]["layout_rejection"]["relative"] == "index.json"
    assert report["failure"]["layout_rejection"]["mode"] == "0o444"
    assert report["cleanup"] == [{"failure": "synthetic_cleanup"}]


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
                    {"Name": "stdlib", "Version": "v1.27.3"},
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


def _publication_run(
    run_id: int = 12,
    *,
    attempt: int = 1,
    status: str = "completed",
    conclusion: str | None = "success",
) -> dict[str, Any]:
    return {
        "id": run_id,
        "run_attempt": attempt,
        "workflow_id": 1234,
        "path": ".github/workflows/build.yml",
        "head_sha": "1" * 40,
        "head_branch": "main",
        "event": "push",
        "repository": {"id": 1043311030},
        "head_repository": {"id": 1043311030},
        "status": status,
        "conclusion": conclusion,
    }


def _publication_job(
    run_id: int = 12,
    *,
    attempt: int = 1,
    status: str = "completed",
    conclusion: str | None = "success",
) -> dict[str, Any]:
    return {
        "id": run_id * 10,
        "run_id": run_id,
        "run_attempt": attempt,
        "name": "prometheus-publish",
        "head_sha": "1" * 40,
        "status": status,
        "conclusion": conclusion,
    }


class _PublicationPredecessorAPI(source.GitHubRead):
    """Native-shaped observations through the real bounded pages reader; no external API."""

    def __init__(
        self,
        runs: list[dict[str, Any]] | None = None,
        jobs: dict[int, list[dict[str, Any]]] | None = None,
        *,
        snapshots: list[tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]] | None = None,
    ) -> None:
        self.snapshots = (
            copy.deepcopy(snapshots)
            if snapshots is not None
            else [
                (
                    [_publication_run()] if runs is None else copy.deepcopy(runs),
                    {12: [_publication_job()]} if jobs is None else copy.deepcopy(jobs),
                )
            ]
        )
        self.observation = 0
        self.current = self.snapshots[0]
        self.requests: list[str] = []
        self.overrides: dict[str, Any] = {}

    def json(self, endpoint: str) -> Any:
        self.requests.append(endpoint)
        if endpoint in self.overrides:
            value = self.overrides[endpoint]
            if isinstance(value, BaseException):
                raise value
            return copy.deepcopy(value)
        prefix = f"/repos/{source.GHCR_REPOSITORY}/actions/"
        if endpoint.startswith(prefix + "workflows/build.yml/runs?"):
            runs, _jobs = self.snapshots[min(self.observation, len(self.snapshots) - 1)]
            return {"total_count": len(runs), "workflow_runs": copy.deepcopy(runs)}
        match = re.fullmatch(
            re.escape(prefix) + r"runs/(\d+)/attempts/(\d+)/jobs\?per_page=100&page=1", endpoint
        )
        if match:
            run_id, attempt = map(int, match.groups())
            assert any(
                row["id"] == run_id and row["run_attempt"] == attempt for row in self.current[0]
            )
            jobs = self.current[1].get(run_id, [])
            return {"total_count": len(jobs), "jobs": copy.deepcopy(jobs)}
        match = re.fullmatch(re.escape(prefix) + r"runs/(\d+)", endpoint)
        assert match is not None, endpoint
        return copy.deepcopy(next(row for row in self.current[0] if row["id"] == int(match[1])))

    def pages(self, endpoint: str, key: str | None, count: int) -> list[dict[str, Any]]:
        if key == "workflow_runs":
            self.current = self.snapshots[min(self.observation, len(self.snapshots) - 1)]
        values = super().pages(endpoint, key, count)
        if key == "workflow_runs":
            self.observation += 1
        return values


def _publication_wait_observations(
    case: str,
) -> tuple[list[tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]], str | None, int]:
    """One finite caller-regression table, shared by the workflow and internal consumer."""
    active = ([_publication_run(status="in_progress", conclusion=None)], {12: []})
    success = ([_publication_run()], {12: [_publication_job()]})
    terminal = (
        [_publication_run(status="in_progress", conclusion=None)],
        {12: [_publication_job(conclusion="failure")]},
    )
    if case == "missing-active-success":
        return [([], {}), active, success], None, 2
    if case == "new-attempt-success":
        return (
            [active, ([_publication_run(attempt=2)], {12: [_publication_job(attempt=2)]})],
            None,
            1,
        )
    if case == "pending-terminal":
        return [active, terminal], "publication_predecessor_failed", 1
    if case == "missing-timeout":
        return [([], {})], "qualification_deadline", -1
    if case == "active-timeout":
        return [active], "qualification_deadline", -1
    if case == "missing-job":
        return [([_publication_run()], {12: []})], "publication_predecessor_not_published", 0
    if case == "skipped-job":
        return (
            [(active[0], {12: [_publication_job(conclusion="skipped")]})],
            "publication_predecessor_not_published",
            0,
        )
    if case == "malformed":
        return (
            [([_publication_run()], {12: [_publication_job(attempt=2)]})],
            "publication_predecessor_job_identity",
            0,
        )
    if case == "api-error":
        return [success], "GitHub_native_failed", 0
    job_failure = case.startswith("job-")
    conclusion = case.removeprefix("job-")
    diagnostics = {
        "failure": "publication_predecessor_failed",
        "cancelled": "publication_predecessor_cancelled",
        "timed_out": "publication_predecessor_timed_out",
    }
    assert conclusion in diagnostics
    run = (
        _publication_run(status="in_progress", conclusion=None)
        if job_failure
        else _publication_run(conclusion=conclusion)
    )
    job = _publication_job(conclusion=conclusion if job_failure else "success")
    return [([run], {12: [job]})], diagnostics[conclusion], 0


@pytest.mark.parametrize(
    "run_status,run_conclusion,job_status,job_conclusion,diagnostic",
    [
        ("completed", "success", "completed", "success", None),
        ("in_progress", None, "in_progress", None, "positive_publication_predecessor_active"),
        ("queued", None, None, None, "positive_publication_predecessor_active"),
        ("waiting", None, "queued", None, "positive_publication_predecessor_active"),
        ("pending", None, "queued", None, "positive_publication_predecessor_active"),
        ("requested", None, "queued", None, "positive_publication_predecessor_active"),
        ("in_progress", None, "completed", "success", "positive_publication_predecessor_active"),
        ("in_progress", None, "completed", "failure", "publication_predecessor_failed"),
        ("in_progress", None, "completed", "cancelled", "publication_predecessor_cancelled"),
        ("in_progress", None, "completed", "timed_out", "publication_predecessor_timed_out"),
        ("completed", "failure", "completed", "success", "publication_predecessor_failed"),
        ("completed", "cancelled", None, None, "publication_predecessor_cancelled"),
        ("completed", "timed_out", None, None, "publication_predecessor_timed_out"),
        ("completed", "neutral", None, None, "publication_predecessor_not_published"),
        ("completed", "skipped", None, None, "publication_predecessor_not_published"),
        ("completed", "action_required", None, None, "publication_predecessor_not_published"),
        ("completed", "stale", None, None, "publication_predecessor_not_published"),
        ("completed", "startup_failure", None, None, "publication_predecessor_not_published"),
        ("completed", "success", None, None, "publication_predecessor_not_published"),
        ("in_progress", None, "completed", "skipped", "publication_predecessor_not_published"),
        ("in_progress", None, "completed", "neutral", "publication_predecessor_not_published"),
        (
            "completed",
            "success",
            "completed",
            "failure",
            "publication_predecessor_run_job_contradiction",
        ),
        (
            "completed",
            "success",
            "in_progress",
            None,
            "publication_predecessor_run_job_contradiction",
        ),
        ("completed", "success", "completed", None, "publication_predecessor_state"),
        ("in_progress", None, "future-status", None, "publication_predecessor_state"),
        ("completed", None, None, None, "publication_predecessor_state"),
        ("in_progress", "failure", None, None, "publication_predecessor_state"),
        ("future-status", None, None, None, "publication_predecessor_state"),
        ("completed", "future-conclusion", None, None, "publication_predecessor_state"),
    ],
)
@pytest.mark.parametrize("observer", [False, True])
def test_publication_predecessor_recognizes_bound_native_state(
    observer: bool,
    run_status: str,
    run_conclusion: str | None,
    job_status: str | None,
    job_conclusion: str | None,
    diagnostic: str | None,
) -> None:
    run = _publication_run(status=run_status, conclusion=run_conclusion)
    jobs = (
        []
        if job_status is None
        else [_publication_job(status=job_status, conclusion=job_conclusion)]
    )
    api = _PublicationPredecessorAPI([run], {12: jobs})
    known = {
        "positive_publication_predecessor_active",
        "publication_predecessor_failed",
        "publication_predecessor_cancelled",
        "publication_predecessor_timed_out",
        "publication_predecessor_not_published",
    }
    if observer:
        if diagnostic is None:
            assert source.observe_publication_predecessor(api, "1" * 40) == (
                {"run": run, "job": jobs[0]},
                None,
            )
        elif diagnostic in known:
            assert source.observe_publication_predecessor(api, "1" * 40) == (None, diagnostic)
        else:
            with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
                source.observe_publication_predecessor(api, "1" * 40)
        return
    if diagnostic is None:
        assert source.require_publication_predecessor(api, "1" * 40) == {"run": run, "job": jobs[0]}
    else:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.require_publication_predecessor(api, "1" * 40)


def test_publication_predecessor_missing_is_not_an_api_error() -> None:
    api = _PublicationPredecessorAPI([], {})
    with pytest.raises(
        source.QualificationError, match="^positive_publication_predecessor_missing$"
    ):
        source.require_publication_predecessor(api, "1" * 40)
    assert len(api.requests) == 2 and api.observation == 1


@pytest.mark.parametrize("head", [None, True, "1" * 39, "../main", "A" * 40])
def test_publication_predecessor_rejects_malformed_head_before_api(head: object) -> None:
    api = _PublicationPredecessorAPI()
    with pytest.raises(source.QualificationError, match="^publication_predecessor_head$"):
        source.require_publication_predecessor(api, cast(str, head))
    assert api.requests == []


def test_publication_predecessor_other_jobs_cannot_substitute_required_publication() -> None:
    job = {**_publication_job(), "name": "build"}
    api = _PublicationPredecessorAPI([_publication_run()], {12: [job]})
    with pytest.raises(source.QualificationError, match="^publication_predecessor_not_published$"):
        source.require_publication_predecessor(api, "1" * 40)


def test_publication_predecessor_keeps_real_page_count_drift_rejection() -> None:
    class API(_PublicationPredecessorAPI):
        def json(self, endpoint: str) -> Any:
            result = super().json(endpoint)
            if "/workflows/build.yml/runs?" in endpoint and len(self.requests) > 1:
                result["total_count"] = 2
            return result

    api = API()
    with pytest.raises(source.QualificationError, match="^GitHub_page_count_drift$"):
        source.require_publication_predecessor(api, "1" * 40)
    assert len(api.requests) == 2


@pytest.mark.parametrize(
    "foreign", ["head_sha", "head_branch", "event", "repository", "head_repository"]
)
def test_publication_predecessor_preserves_positive_precedence(foreign: str) -> None:
    unrelated = _publication_run(40, conclusion="failure")
    unrelated[foreign] = (
        {"id": 123}
        if foreign.endswith("repository")
        else ("2" * 40 if foreign == "head_sha" else "foreign")
    )
    runs = [
        _publication_run(30, conclusion="failure"),
        _publication_run(10),
        unrelated,
        _publication_run(20),
    ]
    jobs = {n: [_publication_job(n)] for n in (10, 20, 30)}
    api = _PublicationPredecessorAPI(runs, jobs)
    assert source.require_publication_predecessor(api, "1" * 40) == {
        "run": runs[3],
        "job": jobs[20][0],
    }
    assert not any(
        "/runs/40/" in endpoint or endpoint.endswith("/runs/40") for endpoint in api.requests
    )


@pytest.mark.parametrize("conclusion", ["success", "failure"])
@pytest.mark.parametrize("eligible", [False, True])
def test_publication_predecessor_binds_exact_native_workflow_path(
    conclusion: str,
    eligible: bool,
) -> None:
    foreign = {**_publication_run(40, conclusion=conclusion), "path": ".github/workflows/ci.yml"}
    runs = [_publication_run(10), foreign, _publication_run(20)] if eligible else [foreign]
    jobs = {n: [_publication_job(n)] for n in (10, 20, 40)}
    api = _PublicationPredecessorAPI(runs, jobs)
    if eligible:
        assert source.require_publication_predecessor(api, "1" * 40) == {
            "run": runs[2],
            "job": jobs[20][0],
        }
    else:
        with pytest.raises(
            source.QualificationError, match="^positive_publication_predecessor_missing$"
        ):
            source.require_publication_predecessor(api, "1" * 40)
    assert not any(
        "/runs/40/" in endpoint or endpoint.endswith("/runs/40") for endpoint in api.requests
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_publication_predecessor_does_not_rescue_latest_failure_with_older_active_run(
    reverse: bool,
) -> None:
    runs = [
        _publication_run(11, status="in_progress", conclusion=None),
        _publication_run(12, conclusion="failure"),
    ]
    if reverse:
        runs.reverse()
    api = _PublicationPredecessorAPI(runs, {11: [], 12: [_publication_job(conclusion="failure")]})
    with pytest.raises(source.QualificationError, match="^publication_predecessor_failed$"):
        source.require_publication_predecessor(api, "1" * 40)
    assert api.observation == 1


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("run-bool", "publication_predecessor_run_identity"),
        ("attempt-zero", "publication_predecessor_run_identity"),
        ("repository-shape", "publication_predecessor_run_identity"),
        ("path-empty", "publication_predecessor_run_identity"),
        ("path-missing", "publication_predecessor_run_identity"),
        ("path-type", "publication_predecessor_run_identity"),
        ("job-bool", "publication_predecessor_job_identity"),
        ("job-run", "publication_predecessor_job_identity"),
        ("job-attempt", "publication_predecessor_job_identity"),
        ("job-head", "publication_predecessor_job_identity"),
        ("duplicate-publisher", "publication_predecessor_publisher_ambiguous"),
        ("attempt-drift", "publication_predecessor_run_drift"),
        ("head-drift", "publication_predecessor_run_drift"),
        ("path-drift", "publication_predecessor_run_drift"),
        ("terminal-regression", "publication_predecessor_run_drift"),
        ("run-count", "GitHub_complete_distinct_pages"),
        ("run-count-type", "GitHub_finite_page_count"),
        ("run-missing-count", "publication_predecessor_run_inventory"),
        ("job-missing-count", "publication_predecessor_job_inventory"),
        ("duplicate-run", "GitHub_complete_distinct_pages"),
        ("malformed-page", "GitHub_page_shape"),
        ("api-error", "GitHub_native_failed"),
    ],
)
@pytest.mark.parametrize("observer", [False, True])
def test_publication_predecessor_uncertainty_never_becomes_pending(
    observer: bool,
    fault: str,
    diagnostic: str,
) -> None:
    run, job = _publication_run(), _publication_job()
    if fault == "run-bool":
        run["id"] = True
    elif fault == "attempt-zero":
        run["run_attempt"] = 0
    elif fault == "repository-shape":
        run["repository"] = None
    elif fault == "path-empty":
        run["path"] = ""
    elif fault == "path-missing":
        run.pop("path")
    elif fault == "path-type":
        run["path"] = True
    elif fault == "job-bool":
        job["id"] = True
    elif fault == "job-run":
        job["run_id"] = 13
    elif fault == "job-attempt":
        job["run_attempt"] = 2
    elif fault == "job-head":
        job["head_sha"] = "2" * 40
    jobs = [job, {**job, "id": 121}] if fault == "duplicate-publisher" else [job]
    api = _PublicationPredecessorAPI([run, run] if fault == "duplicate-run" else [run], {12: jobs})
    endpoint = f"/repos/{source.GHCR_REPOSITORY}/actions/workflows/build.yml/runs?event=push&head_sha={'1' * 40}&per_page=100&page=1"
    if fault.startswith("run-") and fault in {"run-count", "run-count-type", "run-missing-count"}:
        api.overrides[endpoint] = {"workflow_runs": [run]}
        if fault != "run-missing-count":
            api.overrides[endpoint]["total_count"] = True if fault == "run-count-type" else 2
    elif fault == "malformed-page":
        api.overrides[endpoint] = {"total_count": 1, "workflow_runs": [None]}
    elif fault == "job-missing-count":
        api.overrides[
            f"/repos/{source.GHCR_REPOSITORY}/actions/runs/12/attempts/1/jobs?per_page=100&page=1"
        ] = {}
    elif fault == "api-error":
        api.overrides[endpoint] = source.QualificationError("GitHub_native_failed")
    elif fault in {"attempt-drift", "head-drift", "path-drift", "terminal-regression"}:
        changed = dict(run)
        changed[
            {
                "attempt-drift": "run_attempt",
                "head-drift": "head_sha",
                "path-drift": "path",
                "terminal-regression": "conclusion",
            }[fault]
        ] = {
            "attempt-drift": 2,
            "head-drift": "2" * 40,
            "path-drift": ".github/workflows/ci.yml",
            "terminal-regression": "failure",
        }[
            fault
        ]
        api.overrides[f"/repos/{source.GHCR_REPOSITORY}/actions/runs/12"] = changed
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        if observer:
            source.observe_publication_predecessor(api, "1" * 40)
        else:
            source.require_publication_predecessor(api, "1" * 40)


def test_publication_predecessor_uses_terminal_detail_observed_during_active_run() -> None:
    api = _PublicationPredecessorAPI(
        [_publication_run(status="in_progress", conclusion=None)],
        {12: [_publication_job(status="in_progress", conclusion=None)]},
    )
    api.overrides[f"/repos/{source.GHCR_REPOSITORY}/actions/runs/12"] = _publication_run(
        conclusion="failure"
    )
    with pytest.raises(source.QualificationError, match="^publication_predecessor_failed$"):
        source.require_publication_predecessor(api, "1" * 40)


def test_publication_predecessor_accepts_coherent_completion_during_observation() -> None:
    api = _PublicationPredecessorAPI(
        [_publication_run(status="in_progress", conclusion=None)],
        {12: [_publication_job()]},
    )
    current = _publication_run()
    api.overrides[f"/repos/{source.GHCR_REPOSITORY}/actions/runs/12"] = current
    assert source.require_publication_predecessor(api, "1" * 40) == {
        "run": current,
        "job": _publication_job(),
    }


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
        "go": source.CURRENT_GO.digest,
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
    """Remove the finite declared credential and configuration sources before synthetic tests."""
    for name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GHCR_READ_TOKEN",
        "GHCR_TOKEN",
        "DOCKER_CONFIG",
        "DOCKER_AUTH_CONFIG",
        "PROMETHEUS_CREDENTIAL_ROUTE",
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


def _xnet062_report_fixture(
    work: Path,
    lanes: tuple[str, ...] = ("a", "b"),
) -> tuple[dict[str, Any], source.Native, dict[str, dict[str, Any]], Path]:
    """Real offline collectors with synthetic Docker transcripts, never native proof."""
    evidence, config, go = work / "evidence", work / "docker-config", work / "go"
    for directory in (evidence, config, go / "bin"):
        directory.mkdir(parents=True, exist_ok=True)
    (go / "bin/go").write_bytes(b"inert compiler fixture")
    image = _native_fixed_base_image()
    owned: dict[str, dict[str, Any]] = {}

    class Transcript(source.Native):
        def run(
            self, argv: list[str], name: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            if argv[3] == "create":
                raw = hashlib.sha256(name.encode()).hexdigest().encode() + b"\n"
            else:
                selected = next(
                    (key, value)
                    for key, value in owned.items()
                    if key == argv[-1] or value.get("container_id") == argv[-1]
                )
                container_name, expected = selected
                if argv[3] == "start":
                    command = expected["command"]
                    raw = (
                        source.CURRENT_GO_VERSION.encode()
                        if command == ["version"]
                        else (
                            b"all modules verified\n"
                            if command == ["mod", "verify"]
                            else package_stream(command[-1].rsplit("/", 1)[-1])
                        )
                    )
                else:
                    assert argv[3] == "inspect"
                    actual = {
                        "Id": expected["container_id"],
                        "Name": "/" + container_name,
                        "Image": image["Id"],
                        "Config": {
                            "Image": image["Id"],
                            "Labels": {source.LABEL: expected["owner"]},
                            "User": "65532:65532",
                            "WorkingDir": "/src",
                            "Entrypoint": ["/usr/local/go/bin/go"],
                            "Cmd": expected["command"],
                            "Env": [
                                key + "=" + value for key, value in expected["environment"].items()
                            ],
                        },
                        "HostConfig": {
                            "NetworkMode": "none",
                            "ReadonlyRootfs": True,
                            "Privileged": False,
                            "NanoCpus": 2000000000,
                            "Memory": 4294967296,
                            "PidsLimit": 128,
                            "CapDrop": ["ALL"],
                            "CapAdd": None,
                            "SecurityOpt": ["no-new-privileges"],
                            "Tmpfs": {str(source.GUEST_TMP): source.GUEST_TMPFS},
                        },
                        "Mounts": [
                            {"Type": "bind", "RW": False, "Destination": key, "Source": value}
                            for key, value in expected["mounts"].items()
                        ],
                        "State": {
                            "Running": False,
                            "ExitCode": 0,
                            "OOMKilled": False,
                            "FinishedAt": "synthetic-time",
                        },
                    }
                    raw = json.dumps([actual]).encode()
            (evidence / (name + ".stdout")).write_bytes(raw)
            (evidence / (name + ".stderr")).write_bytes(b"")
            self.records.append(
                {
                    "argv": list(argv),
                    "environment": dict(env),
                    "cwd": str(cwd),
                    "exit": 0,
                    "failure": None,
                    "stdout": str(evidence / (name + ".stdout")),
                    "stderr": str(evidence / (name + ".stderr")),
                    "stdout_sha256": source.sha(raw),
                    "stderr_sha256": source.sha(b""),
                }
            )
            return raw

    native = Transcript(evidence, time.monotonic() + 900, 120)
    report: dict[str, Any] = {
        "purpose": "synthetic serialization only",
        "module_action": "xnet062-replay",
        "module_derivation": {"authored_action": "golang.org/x/net@v0.62.0", "replays": []},
        "failure": None,
        "interruptions": [],
        "retained_unknown": {"value": [True, 1, "α"]},
        "heavy_build_invocations": 0,
    }
    for lane in lanes:
        root, modules = work / ("source-" + lane), work / ("modules-" + lane)
        root.mkdir()
        modules.mkdir()
        (modules / "cache").write_bytes(b"original cached bytes")
        (modules / "empty-directory").mkdir(mode=0o750)
        for name, raw in {"go.mod": b"frozen mod", "go.sum": b"frozen sums"}.items():
            (root / name).write_bytes(raw)
        locks = source._derivation_locks(root)
        remainder = source._derivation_nonlocks(root, native.deadline)
        arguments = (
            native,
            root,
            go,
            modules,
            locks,
            remainder,
            source.file_hash(go / "bin/go"),
            lane,
            "/usr/bin/docker",
            config,
            image,
            "synthetic-owner",
            [],
            owned,
            {},
            work,
        )
        incumbent = source._derivation_offline(
            *arguments[:7], lane + "-incumbent", *arguments[8:], restore_cache_modes=True
        )
        source._retain_xnet062_arrays(native, lane, incumbent)
        final = source._derivation_offline(*arguments)
        report["module_derivation"]["replays"].append(
            {
                "replay": lane,
                "offline": final,
                "incumbent_reconstruction": {"offline": incumbent, "preserve": ["unchanged"]},
                "complete_module_transitions": [
                    {"Path": "synthetic", "before": None, "after": {"x": 1}}
                ],
            }
        )
    report["native_operations"] = native.records
    report["cleanup"] = [{"name": name, "native_absent": True} for name in owned]
    native.begin_cleanup()
    return report, native, owned, config


def test_xnet062_report_finalizer_preserves_every_value_and_archive_roundtrip(
    tmp_path: Path,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    report["status"] = "failed_or_unknown"
    before = copy.deepcopy(report)
    view = source._finalize_xnet062_report(
        report, native, owned, "/usr/bin/docker", config, derive_completed=True
    )
    assert report == before
    assert view["status"] == "observed_package_metadata_only"
    raw = (native.evidence / "qualification.json").read_bytes()
    assert len(raw) < source.MAX_NATIVE_OUTPUT and source.one_object(raw) == view
    assert not (native.evidence / ".qualification.json.pending").exists()
    references = []
    for lane in view["module_derivation"]["replays"]:
        for offline in (lane["offline"], lane["incumbent_reconstruction"]["offline"]):
            references.extend(offline["full_native_package_members"].values())
            references.append(offline["module_inventory_member"])
            if "cache_mode_restoration" in offline:
                restoration = offline["cache_mode_restoration"]
                references.extend(
                    restoration[key]
                    for key in (
                        "files_before_member",
                        "files_restored_member",
                        "physical_members_member",
                    )
                )
                assert "files_frozen" not in restoration
    assert len(references) == len({value["member"] for value in references}) == 18
    assert len(list(native.evidence.glob("*-incumbent-cache-*.json"))) == 6
    archive = tmp_path / "transport.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        for member in native.evidence.iterdir():
            stream.write(member, member.name)
    files = source._zip_members(archive)
    # Status records finalization; the transport check compares the original
    # pre-publication view, without treating either fixture as native evidence.
    transported = source.one_object(files["qualification.json"])
    transported["status"] = before["status"]
    source._check_xnet062_report(
        before, transported, native, owned, "/usr/bin/docker", config, complete=True, files=files
    )
    assert source.DERIVED_LOCKS != source.XNET060_INCUMBENT_LOCKS


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("missing-b", "xnet062_replay_slots"),
        ("duplicate-a", "xnet062_replay_slots"),
        ("action", "xnet062_report_action"),
        ("target", "xnet062_report_action"),
        ("native-duplicate", "xnet062_native_record_cardinality"),
        ("native-exit-bool", "xnet062_native_terminal"),
        ("native-create-argv", "declared_data_value"),
        ("native-start-ID", "declared_data_value"),
        ("native-path", "xnet062_native_record_cardinality"),
        ("native-hash", "xnet062_native_raw_binding"),
        ("binding-alias", "declared_data_value"),
        ("binding-size-bool", "declared_data_type"),
        ("binding-extra", "declared_data_keys"),
        ("unknown-field-lost", "declared_data_keys"),
    ],
)
def test_xnet062_report_rejects_exact_binding_and_record_faults(
    tmp_path: Path,
    fault: str,
    diagnostic: str,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    view = source._xnet062_report_view(
        report, native, owned, "/usr/bin/docker", config, complete=True
    )
    if fault == "missing-b":
        report["module_derivation"]["replays"].pop()
    elif fault == "duplicate-a":
        report["module_derivation"]["replays"][1]["replay"] = "a"
    elif fault == "action":
        report["module_action"] = "xnet060-replay"
    elif fault == "target":
        report["module_derivation"]["authored_action"] = "golang.org/x/net@v0.60.0"
    elif fault.startswith("native-"):
        stage = "a-offline-prometheus-" + ("create" if fault == "native-create-argv" else "native")
        record = next(row for row in native.records if row["stdout"].endswith(stage + ".stdout"))
        if fault == "native-duplicate":
            native.records.append(copy.deepcopy(record))
        elif fault == "native-exit-bool":
            record["exit"] = False
        elif fault in ("native-create-argv", "native-start-ID"):
            record["argv"][-1] = "wrong"
        elif fault == "native-path":
            record["stdout"] = str(tmp_path / "foreign.stdout")
        else:
            record["stdout_sha256"] = "0" * 64
    elif fault == "unknown-field-lost":
        del view["retained_unknown"]
    else:
        binding = view["module_derivation"]["replays"][0]["offline"]["full_native_package_members"][
            "prometheus"
        ]
        if fault == "binding-alias":
            binding["member"] = "./" + binding["member"]
        elif fault == "binding-size-bool":
            binding["bytes"] = True
        else:
            binding["extra"] = "unbound"
    with pytest.raises(source.QualificationError, match=diagnostic):
        source._check_xnet062_report(
            report, view, native, owned, "/usr/bin/docker", config, complete=True
        )


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("root-object", "xnet062_array_root"),
        ("NaN", "nonfinite_JSON"),
        ("duplicate-key", "duplicate_JSON_key"),
        ("missing-LF", "xnet062_array_encoding"),
        ("bool-mode", "declared_data_type"),
        ("missing-empty-directory", "declared_data_length"),
        ("missing-root", "declared_data_length"),
        ("duplicate-root", "declared_data_length"),
        ("identity-key", "declared_data_keys"),
        ("parent-file", "declared_data_value"),
        ("order", "declared_data_value"),
        ("mode", "declared_data_value"),
        ("frozen-content", "xnet062_frozen_semantic_hash"),
    ],
)
def test_xnet062_report_array_roundtrip_rejects_loss_even_with_rebound_raw_hash(
    tmp_path: Path,
    fault: str,
    diagnostic: str,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    view = source._xnet062_report_view(
        report, native, owned, "/usr/bin/docker", config, complete=True
    )
    offline = view["module_derivation"]["replays"][0]["incumbent_reconstruction"]["offline"]
    restoration = offline["cache_mode_restoration"]
    binding = (
        offline["module_inventory_member"]
        if fault == "frozen-content"
        else (
            restoration["files_before_member"]
            if fault in ("bool-mode", "mode")
            else restoration["physical_members_member"]
        )
    )
    path = native.evidence / binding["member"]
    value = json.loads(path.read_bytes())
    if fault == "root-object":
        raw = b"{}\n"
    elif fault == "NaN":
        raw = b"[NaN]\n"
    elif fault == "duplicate-key":
        raw = b'[{"path":".","path":"."}]\n'
    elif fault == "missing-LF":
        raw = path.read_bytes()[:-1]
    else:
        if fault == "bool-mode":
            value[0]["mode"] = True
        elif fault == "missing-empty-directory":
            value = [row for row in value if row["path"] != "empty-directory"]
        elif fault == "missing-root":
            value.pop(0)
        elif fault == "duplicate-root":
            value.append(value[0])
        elif fault == "identity-key":
            del value[0]["identity"]["st_ino"]
        elif fault == "parent-file":
            value[-1]["path"] = "cache/child"
        elif fault == "order":
            value.reverse()
        elif fault == "mode":
            value[0]["mode"] += 1
        else:
            value[0]["sha256"] = "0" * 64
        raw = (
            (json.dumps(value, sort_keys=True) + "\n").encode()
            if fault == "frozen-content"
            else source._xnet062_json_bytes(value, native.cleanup_deadline)
        )
    path.write_bytes(raw)
    binding.update(bytes=len(raw), sha256=source.sha(raw))
    with pytest.raises(source.QualificationError, match=diagnostic):
        source._check_xnet062_report(
            report, view, native, owned, "/usr/bin/docker", config, complete=True
        )


@pytest.mark.parametrize("fault", ["missing", "symlink", "hardlink", "directory", "oversize"])
def test_xnet062_report_member_read_is_bounded_and_nofollow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    member = tmp_path / "a-incumbent-cache-before.json"
    if fault == "symlink":
        target = tmp_path / "target"
        target.write_bytes(b"[]\n")
        member.symlink_to(target)
    elif fault == "hardlink":
        target = tmp_path / "target"
        target.write_bytes(b"[]\n")
        member.hardlink_to(target)
    elif fault == "directory":
        member.mkdir()
    elif fault == "oversize":
        member.write_bytes(b"12345")
        monkeypatch.setattr(source, "MAX_NATIVE_OUTPUT", 4)
    with pytest.raises(
        (source.QualificationError, FileNotFoundError), match="xnet062_member_|No such file"
    ):
        source._xnet062_member(tmp_path, member.name, time.monotonic() + 30)


def test_xnet062_report_write_collision_and_size_preserve_existing_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "a-incumbent-cache-before.json"
    path.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        source._xnet062_write(tmp_path, path.name, b"[]\n", time.monotonic() + 30)
    assert path.read_bytes() == b"original"
    monkeypatch.setattr(source, "MAX_NATIVE_OUTPUT", 8)
    with pytest.raises(source.QualificationError, match="xnet062_report_size"):
        source._xnet062_json_bytes({"large": "123456789"}, time.monotonic() + 30)
    assert not (tmp_path / "qualification.json").exists()


@pytest.mark.parametrize(
    "completed,failure,cleanup,interrupted",
    [
        (False, None, False, False),
        (True, {"class": "TimeoutError"}, False, False),
        (True, None, True, False),
        (True, None, False, True),
    ],
)
def test_xnet062_report_cannot_publish_success_from_partial_or_failed_outcome(
    tmp_path: Path,
    completed: bool,
    failure: Any,
    cleanup: bool,
    interrupted: bool,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    report["failure"] = failure
    if cleanup:
        report["cleanup"][0]["failure"] = "TimeoutError"
    if interrupted:
        report["interruptions"] = [15]
    view = source._finalize_xnet062_report(
        report, native, owned, "/usr/bin/docker", config, derive_completed=completed
    )
    assert view["status"] == "failed_or_unknown"
    assert (
        source.one_object((native.evidence / "qualification.json").read_bytes())["status"]
        == "failed_or_unknown"
    )


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("command", "container_command"),
        ("entrypoint", "container_command"),
        ("image", "native_container"),
        ("terminal", "declared_data_value"),
        ("package-field", "declared_data_value"),
    ],
)
def test_xnet062_report_rejects_rebound_native_data_using_existing_owners(
    tmp_path: Path,
    fault: str,
    diagnostic: str,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    view = source._xnet062_report_view(
        report, native, owned, "/usr/bin/docker", config, complete=True
    )
    stage = "a-offline-prometheus-" + (
        "native" if fault == "package-field" else "completed-inspect"
    )
    record = next(row for row in native.records if row["stdout"].endswith(stage + ".stdout"))
    path = native.evidence / (stage + ".stdout")
    if fault == "package-field":
        values = source.decode_objects(path.read_bytes())
        values[0]["Name"] = "changed_name_same_count"
        raw = b"\n".join(json.dumps(value).encode() for value in values)
        binding = view["module_derivation"]["replays"][0]["offline"]["full_native_package_members"][
            "prometheus"
        ]
        binding.update(bytes=len(raw), sha256=source.sha(raw))
    else:
        value = json.loads(path.read_bytes())
        actual = value[0]
        if fault == "command":
            actual["Config"]["Cmd"] = ["version"]
        elif fault == "entrypoint":
            actual["Config"]["Entrypoint"] = ["/unexpected"]
        elif fault == "image":
            actual["Config"]["Image"] = "sha256:" + "0" * 64
        else:
            actual["State"]["ExitCode"] = 1
        raw = json.dumps(value).encode()
    path.write_bytes(raw)
    record["stdout_sha256"] = source.sha(raw)
    with pytest.raises(source.QualificationError, match=diagnostic):
        source._check_xnet062_report(
            report, view, native, owned, "/usr/bin/docker", config, complete=True
        )


def test_xnet062_report_invalid_utf8_and_member_change_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    view = source._xnet062_report_view(
        report, native, owned, "/usr/bin/docker", config, complete=True
    )
    binding = view["module_derivation"]["replays"][0]["offline"]["module_inventory_member"]
    path = native.evidence / binding["member"]
    path.write_bytes(b"[\xff]\n")
    binding.update(bytes=4, sha256=source.sha(b"[\xff]\n"))
    with pytest.raises(UnicodeDecodeError):
        source._check_xnet062_report(
            report, view, native, owned, "/usr/bin/docker", config, complete=True
        )
    stat_fd = source.os.fstat
    calls = 0

    def changed(descriptor: int) -> Any:
        nonlocal calls
        calls += 1
        if calls == 2:
            path.write_bytes(b"changed while open")
        return stat_fd(descriptor)

    monkeypatch.setattr(source.os, "fstat", changed)
    with pytest.raises(source.QualificationError, match="xnet062_member_changed"):
        source._xnet062_member(native.evidence, path.name, native.cleanup_deadline)


def test_xnet062_report_failed_partial_incumbent_is_visible_without_complete_replay(
    tmp_path: Path,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path, ("a",))
    report["module_derivation"]["replays"] = []
    report["failure"] = {"class": "QualificationError", "code": "synthetic_get_failure"}
    view = source._finalize_xnet062_report(
        report, native, owned, "/usr/bin/docker", config, derive_completed=False
    )
    assert view["status"] == "failed_or_unknown"
    assert set(view["partial_incumbent_members"]) == {
        "a-incumbent-cache-" + suffix + ".json"
        for suffix in ("before", "restored", "physical-members")
    }
    assert view["module_derivation"]["replays"] == []


def test_xnet062_report_preservation_does_not_recheck_historical_filesystem(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report, native, owned, config = _xnet062_report_fixture(tmp_path)
    replays = report["module_derivation"]["replays"]
    identities = [
        row["incumbent_reconstruction"]["offline"]["cache_mode_restoration"]["members"][0][
            "identity"
        ]
        for row in replays
    ]
    assert identities[0]["st_ino"] != identities[1]["st_ino"]
    # A subsequent get legitimately changes source/cache; preserved original
    # observations, not these later paths, are the serialization oracle.
    (tmp_path / "source-a/go.mod").write_bytes(b"later authored get")

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("historical live state was revalidated")

    monkeypatch.setattr(source, "sandbox_arguments", forbidden)
    monkeypatch.setattr(source, "_derivation_guard", forbidden)
    monkeypatch.setattr(source, "tree_inventory", forbidden)
    view = source._finalize_xnet062_report(
        report, native, owned, "/usr/bin/docker", config, derive_completed=True
    )
    assert view["status"] == "observed_package_metadata_only"


def _xnet062_qualify_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace acquisition only; the real qualifier/finalizer remains under test."""
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.setattr(source.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(
        source,
        "LOCKS",
        {
            key: source.sha(raw)
            for key, raw in {"go.mod": b"frozen mod", "go.sum": b"frozen sums"}.items()
        },
    )
    monkeypatch.setattr(source, "GO_LICENSE", source.sha(b"fixture license"))
    monkeypatch.setattr(source, "SOURCE_LICENSES", {"LICENSE": source.sha(b"fixture license")})

    def acquire(artifact: source.Artifact, target: Path, deadline: float) -> dict[str, Any]:
        target.write_text(source.UI.digest + "  prometheus-web-ui-3.15.0.tar.gz\n")
        return {"synthetic": artifact.name}

    def extract(
        artifact: source.Artifact, archive: Path, target: Path, deadline: float
    ) -> list[dict[str, Any]]:
        target.mkdir()
        (target / "LICENSE").write_bytes(b"fixture license")
        (target / "VERSION").write_bytes(
            source.CURRENT_GO_VERSION_FILE if artifact == source.CURRENT_GO else b"3.15.0\n"
        )
        if artifact == source.SOURCE:
            (target / "go.mod").write_bytes(b"frozen mod")
            (target / "go.sum").write_bytes(b"frozen sums")
        return []

    monkeypatch.setattr(source, "acquire", acquire)
    monkeypatch.setattr(source, "extract", extract)
    monkeypatch.setattr(source, "stage_ui", lambda *args: {"synthetic": True})


@pytest.mark.parametrize(
    "fault",
    [None, "before-b", "secondary-encode", "secondary-write", "expired-cleanup", "cleanup", "view"],
)
def test_xnet062_report_actual_qualify_finalization_and_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
) -> None:
    _xnet062_qualify_inputs(monkeypatch)
    primary = source.QualificationError("synthetic_primary_deadline")
    saved: dict[str, Any] = {}

    def derive(
        native: source.Native,
        work: Path,
        downloads: Path,
        original_source: Path,
        go: Path,
        ui: Path,
        owned: dict[str, dict[str, Any]],
        *args: Any,
        target_version: str,
    ) -> None:
        assert target_version == "v0.62.0"
        original_report = args[-1]
        fixture, transcript, expected, _ = _xnet062_report_fixture(
            work,
            (
                ("a",)
                if fault in ("before-b", "secondary-encode", "secondary-write", "expired-cleanup")
                else ("a", "b")
            ),
        )
        native.records.extend(transcript.records)
        owned.update(expected)
        original_report.update(
            {
                key: value
                for key, value in fixture.items()
                if key not in ("native_operations", "cleanup")
            }
        )
        saved["original"] = original_report
        saved["derivation"] = copy.deepcopy(original_report["module_derivation"])
        if fault == "secondary-encode":

            def failed_encode(*args: Any, **kwargs: Any) -> bytes:
                raise source.QualificationError("synthetic_secondary_encode")

            monkeypatch.setattr(source, "_xnet062_json_bytes", failed_encode)
        if fault == "secondary-write":

            def failed_write(*args: Any, **kwargs: Any) -> None:
                raise OSError("synthetic storage failure")

            monkeypatch.setattr(source, "_xnet062_write", failed_write)
        if fault == "expired-cleanup":
            begin = source.Native.begin_cleanup

            def expired_cleanup(instance: source.Native) -> None:
                begin(instance)
                instance.cleanup_deadline = 0

            monkeypatch.setattr(source.Native, "begin_cleanup", expired_cleanup)
        if fault == "view":
            (native.evidence / "b-offline-promtool-native.stdout").unlink()
        if fault in ("before-b", "secondary-encode", "secondary-write", "expired-cleanup"):
            raise primary

    def cleanup(
        native: source.Native,
        docker: str,
        config: Path,
        owned: dict[str, dict[str, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return (
            [{"failure": "synthetic cleanup failure"}]
            if fault == "cleanup"
            else [{"name": name, "native_absent": True} for name in owned]
        )

    monkeypatch.setattr(source, "derive_xnet_observe", derive)
    monkeypatch.setattr(source, "cleanup_owned", cleanup)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    work = tmp_path / "qualify"
    if fault is None:
        result = source.qualify(work, 1800, 120, derive_xnet062=True)
        assert result["status"] == "observed_package_metadata_only"
        assert "full_native_package_members" in result["module_derivation"]["replays"][0]["offline"]
    elif fault in ("before-b", "secondary-encode", "secondary-write", "expired-cleanup"):
        with pytest.raises(source.QualificationError, match="synthetic_primary_deadline") as caught:
            source.qualify(work, 1800, 120, derive_xnet062=True)
        assert caught.value is primary
        assert (work / "evidence/a-incumbent-cache-physical-members.json").is_file()
        assert not (work / "evidence/b-incumbent-cache-physical-members.json").exists()
    elif fault == "cleanup":
        with pytest.raises(source.QualificationError, match="qualification_or_cleanup_failed"):
            source.qualify(work, 1800, 120, derive_xnet062=True)
    else:
        with pytest.raises(FileNotFoundError):
            source.qualify(work, 1800, 120, derive_xnet062=True)
        diagnostic = source.one_object((work / "evidence/qualification.json").read_bytes())
        assert diagnostic["incomplete_diagnostic"] is True
        assert diagnostic["status"] == "failed_or_unknown"
        assert diagnostic["report_failure"]["class"] == "FileNotFoundError"
    assert source.CLEANING is False
    assert saved["original"]["module_derivation"] == saved["derivation"]
    assert (work / "evidence/a-offline-prometheus-native.stdout").is_file()


def test_xnet062_report_keeps_060_serialization_and_return_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _xnet062_qualify_inputs(monkeypatch)

    def observed(*args: Any, target_version: str) -> None:
        assert target_version == "v0.60.0"
        args[-1]["module_action"] = "xnet060-replay"
        args[-1]["module_derivation"] = {"original_field": [1, "legacy"]}

    monkeypatch.setattr(source, "derive_xnet_observe", observed)
    monkeypatch.setattr(source, "cleanup_owned", lambda *args: [])
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    work = tmp_path / "qualify"
    report = source.qualify(work, 900, 120, derive_xnet060=True)
    assert (work / "evidence/qualification.json").read_bytes() == (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    ).encode()
    assert report["module_derivation"] == {"original_field": [1, "legacy"]}
    assert not list((work / "evidence").glob("*-incumbent-cache-*.json"))


@pytest.mark.parametrize(
    "mode,seconds,cleanup,allowed",
    [
        (mode, seconds, cleanup, allowed)
        for mode in ("unchanged", "060", "062")
        for seconds, cleanup, allowed in (
            (900, 120, True),
            (901, 120, mode == "062"),
            (1800, 120, mode == "062"),
            (1801, 120, False),
            (0, 120, False),
            (-1, 120, False),
            (True, 120, False),
            (900.0, 120, False),
            ("900", 120, False),
            (900, 121, False),
            (900, True, False),
        )
    ],
)
def test_xnet062_report_budget_is_mode_specific_before_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    seconds: Any,
    cleanup: Any,
    allowed: bool,
) -> None:
    _xnet062_qualify_inputs(monkeypatch)
    effects = []

    def first_effect(path: Path, *args: Any) -> None:
        effects.append(path)
        raise RuntimeError("budget admitted before first effect")

    monkeypatch.setattr(source, "fresh_directory", first_effect)
    selectors = {"derive_xnet060": mode == "060", "derive_xnet062": mode == "062"}
    with pytest.raises(
        RuntimeError if allowed else source.QualificationError,
        match="budget admitted" if allowed else "qualification_budget",
    ):
        source.qualify(tmp_path / "uncreated", seconds, cleanup, **selectors)
    assert bool(effects) is allowed


@pytest.mark.parametrize("value", [1, 0, None, "true", [], {}])
def test_xnet062_report_rejects_nonboolean_selectors(tmp_path: Path, value: Any) -> None:
    with pytest.raises(source.QualificationError, match="xnet_derivation_selector_type"):
        source.qualify(tmp_path / "uncreated", 900, 120, derive_xnet062=value)
    assert not (tmp_path / "uncreated").exists()


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
    assert result[0]["name"] == "owned" and result[0].get("failure")
    assert fake.records[0]["failure"] == "TimeoutExpired"
    # A timed-out create supplied no full ID: do not delete a name-only candidate.
    assert not any("rm" in argv for argv in calls)
    assert state["exists"] is True


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
            FakeNative(),
            "/usr/bin/docker",
            tmp_path,
            "owned",
            {"container_id": "a" * 64},
            "case",
            {},
            tmp_path,
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
        FakeNative(),
        "/usr/bin/docker",
        tmp_path,
        "owned",
        {"container_id": "a" * 64},
        "case",
        {},
        tmp_path,
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
                b"3.15.0\n" if artifact.name == "source" else source.CURRENT_GO_VERSION_FILE
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
            return source.CURRENT_GO_VERSION.encode()
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


class _PublicPackageInventoryAPI:
    """Synthetic transport data only; no auth, native-capacity or atomicity evidence."""

    gh = "/synthetic/gh"

    def __init__(self, count: Any) -> None:
        self.repository, self.package = ghcr_synthetic_responses()
        self.repository["id"] = self.package["repository"]["id"] = 1043311030
        self.repository["owner"]["id"] = self.package["owner"]["id"] = 169792616
        self.package["id"] = 9374404
        self.package["version_count"] = count
        self.after_repository: dict[str, Any] | None = None
        self.after_package: dict[str, Any] | None = None
        self.pages: dict[int, bytes] = {}
        self.repository_reads = 0
        self.package_reads = 0
        self.version_requests: list[tuple[int, int]] = []
        self.enforce_capture_bound = True

    def json(self, endpoint: str) -> dict[str, Any]:
        assert endpoint == "/repos/" + source.GHCR_REPOSITORY
        self.repository_reads += 1
        value = self.after_repository if self.repository_reads == 2 else None
        return copy.deepcopy(self.repository if value is None else value)

    def _capture(self, argv: list[str], maximum: int) -> bytes:
        assert argv[:6] == [self.gh, "api", "--hostname", "github.com", "--method", "GET"]
        assert len(argv) == 7 and 0 < maximum <= 16 * 1024**2
        endpoint = source.GHCR_REQUESTS[1]
        if argv[6] == endpoint:
            self.package_reads += 1
            value = self.after_package if self.package_reads == 2 else None
            raw = source.canonical_data(self.package if value is None else value)
        else:
            prefix = endpoint + "/versions?per_page=100&page="
            assert argv[6].startswith(prefix)
            page = int(argv[6].removeprefix(prefix))
            self.version_requests.append((page, maximum))
            count = self.package["version_count"]
            rows = [
                {"id": number, "metadata": {"container": {"tags": []}}}
                for number in range((page - 1) * 100 + 1, min(page * 100, count) + 1)
            ]
            raw = self.pages.get(page, source.canonical_data(rows))
        if self.enforce_capture_bound and len(raw) > maximum:
            raise source.QualificationError("GitHub_native_output_bound")
        return raw


@pytest.mark.parametrize("count", [0, 99, 100, 9999, 10000, 16557, 16575, 20000])
def test_public_package_inventory_count_derived_terminal_and_full_rows(count: int) -> None:
    api = _PublicPackageInventoryAPI(count)
    identity, rows = source.existing_public_package(api)
    assert identity["package"]["id"] == 9374404
    assert [row["id"] for row in rows] == list(range(1, count + 1))
    assert api.version_requests == [(page, 1024**2) for page in range(1, count // 100 + 2)]
    assert api.package_reads == api.repository_reads == 2


@pytest.mark.parametrize("count", [None, True, False, -1, 20001, "16557", 1.5, "missing"])
def test_public_package_inventory_rejects_invalid_count_before_pages(count: Any) -> None:
    api = _PublicPackageInventoryAPI(count)
    if count == "missing":
        del api.package["version_count"]
    with pytest.raises(source.QualificationError, match="package_version_count"):
        source.existing_public_package(api)
    assert api.version_requests == []
    assert api.package_reads == api.repository_reads == 1


@pytest.mark.parametrize(
    "raw,diagnostic",
    [
        (b"{}", "package_native_versions"),
        (b"null", "package_native_versions"),
        (b"[true]", "package_native_versions"),
        (b'[{"id":true}]', "package_native_versions"),
        (b'[{"id":0}]', "package_native_versions"),
        (b'[{"id":-1}]', "package_native_versions"),
        (b'[{"id":"1"}]', "package_native_versions"),
        (b'[{"id":1,"id":2}]', "duplicate_JSON_key"),
        (b'[{"id":NaN}]', "nonfinite_JSON"),
    ],
)
def test_public_package_inventory_rejects_malformed_rows(raw: bytes, diagnostic: str) -> None:
    api = _PublicPackageInventoryAPI(1)
    api.pages[1] = raw
    with pytest.raises(source.QualificationError, match=diagnostic):
        source.existing_public_package(api)
    assert api.package_reads == api.repository_reads == 1


@pytest.mark.parametrize(
    "count,page,ids,diagnostic",
    [
        (101, 1, list(range(1, 100)), "package_complete_inventory_count"),
        (100, 2, [101], "package_complete_inventory_count"),
        (101, 1, list(range(1, 102)), "package_native_versions"),
        (2, 1, [1, 1], "package_pagination_distinct"),
        (101, 2, [1], "package_pagination_distinct"),
    ],
)
def test_public_package_inventory_rejects_partial_extra_or_repeated_pages(
    count: int, page: int, ids: list[int], diagnostic: str
) -> None:
    api = _PublicPackageInventoryAPI(count)
    api.pages[page] = source.canonical_data([{"id": value} for value in ids])
    with pytest.raises(source.QualificationError, match=diagnostic):
        source.existing_public_package(api)
    assert api.package_reads == api.repository_reads == 1


@pytest.mark.parametrize("fault", ["count", "bool_count", "package_id", "repository_id"])
def test_public_package_inventory_rejects_identity_or_count_readback_drift(fault: str) -> None:
    api = _PublicPackageInventoryAPI(1)
    api.after_package = copy.deepcopy(api.package)
    api.after_repository = copy.deepcopy(api.repository)
    if fault == "count":
        api.after_package["version_count"] = 2
    elif fault == "bool_count":
        api.after_package["version_count"] = True
    elif fault == "package_id":
        api.after_package["id"] += 1
    else:
        api.after_repository["id"] += 1
        api.after_package["repository"]["id"] = api.after_repository["id"]
    with pytest.raises(
        source.QualificationError, match="package_inventory_identity_or_count_drift"
    ):
        source.existing_public_package(api)
    assert api.package_reads == api.repository_reads == 2


@pytest.mark.parametrize("extra", [0, 1])
def test_public_package_inventory_obeys_native_page_capture_ceiling(extra: int) -> None:
    api = _PublicPackageInventoryAPI(0)
    api.pages[1] = b"[]" + b" " * (1024**2 - 2 + extra)
    if extra:
        with pytest.raises(source.QualificationError, match="GitHub_native_output_bound"):
            source.existing_public_package(api)
    else:
        assert source.existing_public_package(api)[1] == []
    assert api.version_requests == [(1, 1024**2)]


def test_public_package_inventory_aggregate_refusal_precedes_json_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _PublicPackageInventoryAPI(1)
    api.pages[1] = b"not JSON"
    api.enforce_capture_bound = False  # A faulty fake return must not bypass the aggregate guard.
    monkeypatch.setattr(source, "PACKAGE_VERSION_STDOUT_BYTES_MAX", 3)
    with pytest.raises(source.QualificationError, match="package_inventory_stdout_bound"):
        source.existing_public_package(api)
    assert api.version_requests == [(1, 3)]
    assert api.package_reads == api.repository_reads == 1


def test_public_package_inventory_exhaustion_stops_before_next_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _PublicPackageInventoryAPI(101)
    first = source.canonical_data([{"id": value} for value in range(1, 101)])
    api.pages[1] = first
    monkeypatch.setattr(source, "PACKAGE_VERSION_STDOUT_BYTES_MAX", len(first))
    with pytest.raises(source.QualificationError, match="package_inventory_stdout_bound"):
        source.existing_public_package(api)
    assert api.version_requests == [(1, len(first))]
    assert api.package_reads == api.repository_reads == 1


def test_public_package_inventory_preserves_collision_after_page_100() -> None:
    api = _PublicPackageInventoryAPI(10001)
    api.pages[101] = source.canonical_data(
        [
            {
                "id": 10001,
                "name": "sha256:" + "b" * 64,
                "metadata": {"container": {"tags": ["selected"]}},
            }
        ]
    )
    _identity, rows = source.existing_public_package(api)
    with pytest.raises(
        source.QualificationError, match="immutable_tag_existing_other_subject_HOLD"
    ):
        source.immutable_tag_state(rows, "selected", "sha256:" + "a" * 64)
    assert api.version_requests[-1][0] == 101


def test_public_package_inventory_accepts_exact_aggregate_stdout_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _PublicPackageInventoryAPI(1)
    raw = source.canonical_data([{"id": 1}])
    api.pages[1] = raw
    monkeypatch.setattr(source, "PACKAGE_VERSION_STDOUT_BYTES_MAX", len(raw))
    assert source.existing_public_package(api)[1] == [{"id": 1}]
    assert api.version_requests == [(1, len(raw))]


@pytest.mark.parametrize("diagnostic", ["deadline", "GitHub_native_failed"])
def test_public_package_inventory_propagates_terminal_native_failure(
    monkeypatch: pytest.MonkeyPatch, diagnostic: str
) -> None:
    api = _PublicPackageInventoryAPI(100)
    capture = api._capture

    def fail_terminal(argv: list[str], maximum: int) -> bytes:
        if argv[-1].endswith("/versions?per_page=100&page=2"):
            raise source.QualificationError(diagnostic)
        return capture(argv, maximum)

    monkeypatch.setattr(api, "_capture", fail_terminal)
    with pytest.raises(source.QualificationError, match=diagnostic):
        source.existing_public_package(api)
    assert api.package_reads == api.repository_reads == 1


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
        + (
            "release=Path("
            + repr(str(trace.with_suffix(".child-release")))
            + ")\nlifetime_end=time.monotonic()+5\n"
            if mode == "owned_residual"
            else ""
        )
        + "def terminate(signum, frame):\n marker.write_text('SIGTERM\\n')\n"
        + (
            " os.execv('/bin/sleep', ['/bin/sleep', '0.2'])\n"
            if mode == "owned_residual_exec_exit"
            else (
                " while not release.exists():\n"
                "  assert time.monotonic()<lifetime_end\n"
                "  time.sleep(0.01)\n"
                " raise SystemExit(128+signum)\n"
                if mode == "owned_residual"
                else " raise SystemExit(128+signum)\n"
            )
        )
        + "signal.signal(signal.SIGTERM, terminate)\nready.write_text('ready')\n"
        + (
            "time.sleep(max(0,lifetime_end-time.monotonic()))\n"
            if mode == "owned_residual"
            else "time.sleep(5)\n"
        )
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
        + "  trace.with_suffix('.child-group').write_text(str(os.getpgid(child.pid)))\n"
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
        + " if sys.argv[1:] == ['combined-output']:\n"
        + "  assert mode in ('combined_balanced_exact','combined_balanced_over','combined_stderr_exact','combined_stderr_over')\n"
        + "  out_size=131072 if mode.startswith('combined_stderr') else 524288\n"
        + "  err_size=1048576-out_size+(1 if mode.endswith('_over') else 0)\n"
        + "  trace.with_suffix('.capture-pid').write_text(str(os.getpid()))\n"
        + "  trace.with_suffix('.capture-group').write_text(str(os.getpgid(0)))\n"
        + "  sys.stdout.buffer.write(b'o'*out_size); sys.stdout.buffer.flush()\n"
        + "  sys.stderr.buffer.write(b'e'*err_size); sys.stderr.buffer.flush()\n"
        + "  sys.exit(0)\n"
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


def _coordinate_residual_fixture_exit(
    monkeypatch: pytest.MonkeyPatch, trace: Path
) -> list[dict[str, Any]]:
    """Coordinate one ordinary fixture exit using only genuine bounded native censuses.

    Production identity uncertainty remains terminal. The fixture holds its
    unchanged child in its handler until this observer witnesses the owned
    identity and releases it, then returns only the actually inactive snapshot.
    No native row is added, removed, rewritten or declared absent synthetically.
    """
    real_census = source.process_census
    known_identity: tuple[Any, ...] | None = None
    observations: list[dict[str, Any]] = []

    def census(cap: float, known: tuple[bytes, ...]) -> dict[int, dict[str, Any]]:
        """Keep the original cap while separating stable ownership from actual exit."""
        nonlocal known_identity
        rows = real_census(cap, known)
        pid_file, group_file = trace.with_suffix(".child-pid"), trace.with_suffix(".child-group")
        if (
            observations
            or not pid_file.exists()
            or not group_file.exists()
            or not trace.with_suffix(".child-ready").exists()
        ):
            return rows
        child, group = int(pid_file.read_text()), int(group_file.read_text())
        row = rows.get(child)
        if row is not None and not row["state"].startswith("Z"):
            assert row["pid"] == child and row["pgid"] == group
            assert row["uid"] == source.os.getuid()
            identity = source.process_identity(row)
            if known_identity is None:
                known_identity = identity
            assert identity == known_identity
        if not trace.with_suffix(".child-signal").exists():
            return rows
        assert trace.with_suffix(".child-signal").read_bytes() == b"SIGTERM\n"
        assert known_identity is not None and row is not None
        assert not row["state"].startswith("Z")
        assert source.process_identity(row) == known_identity
        trace.with_suffix(".child-release").write_text("release witnessed fixture exit\n")
        while True:
            # This is a fresh real snapshot, not the earlier ownership witness.
            rows = real_census(cap, known)
            child_row = rows.get(child)
            active = [
                current
                for current in rows.values()
                if current["pgid"] == group and not current["state"].startswith("Z")
            ]
            if (child_row is None or child_row["state"].startswith("Z")) and not active:
                observations.append(
                    {
                        "child_pid": child,
                        "pgid": group,
                        "stable_owned_identity_before_release": known_identity,
                        "observed_child_state": (
                            "absent" if child_row is None else child_row["state"]
                        ),
                        "active_group_pids": [],
                        "original_cap": cap,
                    }
                )
                return rows
            source.check_deadline(cap)
            source.time.sleep(min(0.01, max(0, cap - source.time.monotonic())))

    monkeypatch.setattr(source, "process_census", census)
    return observations


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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Real child pipes/processes, synthetic GH program; not an authenticated API proof."""
    runner, trace, gh = _fixed_native_capture_fixture(tmp_path, mode)
    exit_observations = (
        _coordinate_residual_fixture_exit(monkeypatch, trace) if mode == "owned_residual" else []
    )
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
    if mode == "owned_residual":
        assert len(exit_observations) == 1
        assert exit_observations[0]["active_group_pids"] == []
        assert exit_observations[0]["child_pid"] == int(trace.with_suffix(".child-pid").read_text())
        assert exit_observations[0]["pgid"] == int(trace.with_suffix(".child-group").read_text())
        assert trace.with_suffix(".child-release").is_file()
    assert work.exists() is (mode in {"cleanup_failure", "owned_residual_exec_exit"})
    if mode == "owned_residual_exec_exit":
        assert str(failure.value) == "GHCR_owned_group_survived"
        assert (
            "GHCR cleanup also failed:GHCR_unknown_or_reused_group_member"
            in capsys.readouterr().err
        )
    assert not list(runner.glob("**/*.stdout")) and not list(runner.glob("**/*.stderr"))
    if mode in {"owned_residual", "owned_residual_exec_exit"}:
        child_pid = int(trace.with_suffix(".child-pid").read_text())
        group = int(trace.with_suffix(".child-group").read_text())
        # No further signal: observe only this fixture's child and captured group.
        deadline = source.time.monotonic() + 5
        while True:
            rows = source.process_census(deadline, ())
            child_row = rows.get(child_pid)
            active_group = [
                row
                for row in rows.values()
                if row["pgid"] == group and not row["state"].startswith("Z")
            ]
            if (child_row is None or child_row["state"].startswith("Z")) and not active_group:
                break
            assert source.time.monotonic() < deadline
            source.time.sleep(0.01)
        assert child_row is None or child_row["state"].startswith("Z")
        assert not active_group
        trace.with_suffix(".child-inactive").write_text(
            json.dumps(
                {
                    "child_pid": child_pid,
                    "pgid": group,
                    "observed_child_state": "absent" if child_row is None else child_row["state"],
                    "active_group_pids": [],
                }
            )
        )


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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mode: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Same native child fixture/canonical recognizer, synthetic auth only."""
    runner, trace, gh = _fixed_native_capture_fixture(tmp_path, mode, "GitHubRead")
    exit_observations = (
        _coordinate_residual_fixture_exit(monkeypatch, trace) if mode == "owned_residual" else []
    )
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
    deadline_witnesses: list[tuple[float, float, int, tuple[int, ...]]] = []
    if mode == "owned_held_pipes":
        real_owned_members = source.owned_members

        def observe_ready_members(
            process: Any,
            seen: dict[int, tuple[Any, ...]],
            cap: float,
            known: tuple[bytes, ...],
        ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
            members = real_owned_members(process, seen, cap, known)
            if (
                not source.CLEANING
                and process is adapter.process
                and not deadline_witnesses
                and trace.with_suffix(".child-ready").exists()
                and trace.with_suffix(".child-pid").exists()
            ):
                child_pid = int(trace.with_suffix(".child-pid").read_text())
                active_pids = tuple(row["pid"] for row in members[1])
                if child_pid in active_pids:
                    previous = adapter.deadline
                    adapter.deadline = min(previous, source.time.monotonic() + 1)
                    deadline_witnesses.append((previous, adapter.deadline, child_pid, active_pids))
            return members

        monkeypatch.setattr(source, "owned_members", observe_ready_members)

    def observe() -> None:
        source.GitHubRead.__init__(
            adapter,
            private,
            evidence,
            source.time.monotonic() + (1 if mode == "deadline" else 8),
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
            if mode == "owned_held_pipes":
                assert len(deadline_witnesses) == 1
                previous, tightened, witnessed_child, active_pids = deadline_witnesses[0]
                assert tightened <= previous
                assert witnessed_child == child and child in active_pids
            if mode == "owned_residual_exec_exit":
                assert private.is_dir()
                assert (
                    "GitHub cleanup also failed:GHCR_unknown_or_reused_group_member"
                    in capsys.readouterr().err
                )
            group = int(trace.with_suffix(".child-group").read_text())
            cleanup_deadline = adapter.cleanup_deadline
            deadline = source.time.monotonic() + 5
            while True:
                rows = source.process_census(deadline, ())
                child_row = rows.get(child)
                active_group = [
                    row
                    for row in rows.values()
                    if row["pgid"] == group and not row["state"].startswith("Z")
                ]
                if (child_row is None or child_row["state"].startswith("Z")) and not active_group:
                    break
                assert source.time.monotonic() < deadline
                source.time.sleep(0.01)
            assert child_row is None or child_row["state"].startswith("Z")
            assert not active_group
            trace.with_suffix(".child-inactive").write_text(
                json.dumps(
                    {
                        "child_pid": child,
                        "pgid": group,
                        "observed_child_state": (
                            "absent" if child_row is None else child_row["state"]
                        ),
                        "active_group_pids": [],
                    }
                )
            )
            if mode == "owned_residual_exec_exit":
                # Only observed inactivity now permits existing cleanup; its cap is unchanged.
                adapter.close()
                assert adapter.cleanup_deadline == cleanup_deadline
        if mode == "owned_residual":
            assert len(exit_observations) == 1
            assert exit_observations[0]["active_group_pids"] == []
            assert exit_observations[0]["child_pid"] == int(
                trace.with_suffix(".child-pid").read_text()
            )
            assert exit_observations[0]["pgid"] == int(
                trace.with_suffix(".child-group").read_text()
            )
            assert trace.with_suffix(".child-release").is_file()
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

    try:
        with monkeypatch.context() as context:
            context.setattr(source.subprocess, "Popen", start)
            context.setattr(source, "process_census", uncertain)
            context.setattr(
                source.os, "killpg", lambda *args: pytest.fail("uncertain identity signal")
            )
            with pytest.raises(source.QualificationError) as failure:
                source.GitHubRead(private, evidence, source.time.monotonic() + 8, 2)
            assert str(failure.value) == (
                "GHCR_process_census"
                if uncertainty == "census_failure"
                else "GHCR_unknown_or_reused_group_member"
            )
            assert private.is_dir()
        assert "GitHub cleanup also failed:" in capsys.readouterr().err
    finally:
        # Fixture-owned cleanup begins after the production context has been restored.
        for child in children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=5)
            assert not any(
                row["pgid"] == child.pid
                for row in real_census(source.time.monotonic() + 1, ()).values()
            )


@pytest.mark.parametrize("initial_live", [False, True])
def test_owned_cleanup_uses_canonical_active_members_without_signalling_zombies(
    monkeypatch: pytest.MonkeyPatch, initial_live: bool
) -> None:
    import io
    from types import SimpleNamespace

    uid = source.os.getuid()
    leader = {
        "pid": 17001,
        "ppid": 1,
        "pgid": 17001,
        "uid": uid,
        "start": "synthetic leader",
        "state": "Z",
        "comm": "synthetic",
    }
    child = {
        "pid": 17002,
        "ppid": 17001,
        "pgid": 17001,
        "uid": uid,
        "start": "synthetic child",
        "state": "S" if initial_live else "Z",
        "comm": "synthetic",
    }
    seen = {leader["pid"]: source.process_identity(leader)}
    signals: list[tuple[int, int]] = []

    def census(*args: Any) -> dict[int, dict[str, Any]]:
        return {leader["pid"]: dict(leader), child["pid"]: dict(child)}

    def signal_owned(pgid: int, signum: int) -> None:
        assert initial_live and child["state"] == "S"
        signals.append((pgid, signum))
        child["state"] = "Z"

    process = SimpleNamespace(
        pid=leader["pid"],
        poll=lambda: 0,
        stdin=io.BytesIO(),
        stdout=io.BytesIO(),
        stderr=io.BytesIO(),
    )
    monkeypatch.setattr(source, "process_census", census)
    monkeypatch.setattr(source.os, "killpg", signal_owned)
    source.cleanup_process(process, seen, source.time.monotonic() + 1, ())
    assert signals == ([(leader["pid"], source.signal.SIGTERM)] if initial_live else [])
    assert not source.owned_members(process, seen, source.time.monotonic() + 1, ())[1]
    assert all(stream.closed for stream in (process.stdin, process.stdout, process.stderr))


@pytest.mark.parametrize("adapter_name", ["GHCR", "GitHubRead"])
def test_fixed_native_capture_zombie_tail_does_not_block_terminal_admission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, adapter_name: str
) -> None:
    runner, _trace, gh = _fixed_native_capture_fixture(tmp_path, "immediate_exit", adapter_name)
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "GH_TOKEN": "synthetic.opaque.zombie.control",
        "GITHUB_ACTIONS": "true",
        "RUNNER_OS": "Linux",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_JOB": "prometheus-ghcr-package-qualification",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "RUNNER_TEMP": str(runner),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    real_popen, real_census = source.subprocess.Popen, source.process_census
    children: list[Any] = []
    witnessed: set[int] = set()
    zombie_observations: list[int] = []

    def start(argv: list[str], *args: Any, **kwargs: Any) -> Any:
        process = real_popen(argv, *args, **kwargs)
        if argv[0] == str(gh):
            children.append(process)
        return process

    def census(cap: float, known: tuple[bytes, ...]) -> dict[int, dict[str, Any]]:
        rows = real_census(cap, known)
        if children:
            process = children[-1]
            if process.pid in rows:
                witnessed.add(process.pid)
            if process.pid in witnessed and process.poll() is not None:
                pid = process.pid + 1000000000
                rows[pid] = {
                    "pid": pid,
                    "ppid": 1,
                    "pgid": process.pid,
                    "uid": -1,
                    "start": "synthetic zombie",
                    "state": "Z",
                    "comm": "synthetic",
                }
                zombie_observations.append(process.pid)
        return rows

    monkeypatch.setattr(source.subprocess, "Popen", start)
    monkeypatch.setattr(source, "process_census", census)
    monkeypatch.setattr(source.os, "killpg", lambda *args: pytest.fail("zombie-only signal"))
    try:
        if adapter_name == "GHCR":
            private = runner / "ghcr-private-123-1"
            result = source.qualify_existing_ghcr_package(
                private, runner / "ghcr-public-123-1" / "qualification.json", 8, 2
            )
            assert result["qualified"] is True
        else:
            evidence = runner / "evidence"
            evidence.mkdir()
            private = runner / "private"
            adapter = source.GitHubRead(private, evidence, source.time.monotonic() + 8, 2)
            adapter.json("/repos/" + source.GHCR_REPOSITORY)
            adapter.close()
        assert zombie_observations
        assert not private.exists()
    finally:
        for child in children:
            child.wait(timeout=5)


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


def _publisher_job_rows(
    status: str = "completed", conclusion: str | None = "success"
) -> list[dict[str, Any]]:
    """Exact synthetic native job fields for the three current-run predecessors."""
    return [
        {
            "id": index,
            "name": name,
            "run_id": 123,
            "run_attempt": 1,
            "head_sha": "a" * 40,
            "head_branch": "main",
            "run_url": "https://api.github.com/repos/"
            + source.GHCR_REPOSITORY
            + "/actions/runs/123",
            "status": status if name == "publish" else "completed",
            "conclusion": conclusion if name == "publish" else "success",
        }
        for index, name in enumerate(("build", "security-scan", "publish"), 101)
    ]


def _writer_ordering_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    snapshots: list[list[dict[str, Any]] | BaseException],
    *,
    fault: str | None = None,
    cleanup_hold: bool = False,
) -> tuple[Path, Path, Path, list[str], dict[str, Any]]:
    """Real promotion, page reader and inventory; synthetic transport and clock only."""
    real_pages = source.GitHubRead.pages
    real_inventory = source.existing_public_package
    root, work, config, trace, manifest = _promotion_fixture(
        monkeypatch, tmp_path, cleanup_hold=cleanup_hold
    )
    parent = source.GitHubRead
    clock = [100.0]
    state: dict[str, Any] = {
        "reads": 0,
        "sleeps": [],
        "deadlines": [],
        "inventory": [],
        "read_effects": [],
    }
    inventory = _PublicPackageInventoryAPI(101 if fault == "overlap" else 1)
    expected_jobs = "/repos/" + source.GHCR_REPOSITORY + "/actions/runs/123/attempts/1/jobs"

    class API(parent):
        pages = real_pages

        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            super().__init__(private, evidence, deadline, cleanup)
            state["deadlines"].append(deadline)
            if fault == "expired":
                clock[0] = deadline

        def json(self, endpoint: str) -> dict[str, Any]:
            if endpoint == expected_jobs + "?per_page=100&page=1":
                state["deadlines"].append(self.deadline)
                index = state["reads"]
                state["reads"] += 1
                if fault == "page-native" and index == 3:
                    raise source.QualificationError("GitHub_native_failed")
                observation = snapshots[min(index // 2, len(snapshots) - 1)]
                state["read_effects"].append(tuple(trace))
                assert not config.exists() and "candidate" not in trace and "package" not in trace
                if isinstance(observation, BaseException):
                    raise observation
                count: Any = len(observation)
                if fault == "count-drift" and index == 1:
                    count += 1
                elif fault == "count-bool":
                    count = True
                elif fault == "count-string":
                    count = "3"
                elif fault == "count-large":
                    count = 101
                elif fault == "count-negative":
                    count = -1
                if fault == "count-missing":
                    return {"jobs": observation}
                rows = copy.deepcopy(observation)
                if fault == "metadata-pending" and index == 0:
                    rows[-1].update(status="queued", conclusion=None)
                if fault == "bad-page" and index == 1:
                    return {"total_count": count, "jobs": None}
                return {"total_count": count, "jobs": rows}
            if endpoint == "/repos/" + source.GHCR_REPOSITORY:
                return inventory.json(endpoint)
            if fault == "main-after-wait" and endpoint.endswith("/git/ref/heads/main"):
                return {"object": {"sha": "b" * 40}}
            return super().json(endpoint)

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            if argv[-1].startswith(source.GHCR_REQUESTS[1]):
                if argv[-1] == source.GHCR_REQUESTS[1] and inventory.package_reads % 2 == 0:
                    trace.append("package")
                state["inventory"].append(argv[-1])
                selection = manifest["selection"]
                tag = "prometheus-3.15.0-" + selection["manifest_digest"][7:]
                inventory.pages[1] = source.canonical_data(
                    [
                        {
                            "id": 1,
                            "name": selection["manifest_digest"],
                            "metadata": {"container": {"tags": [tag] if "copy" in trace else []}},
                        }
                    ]
                )
                if fault == "overlap":
                    inventory.pages[1] = source.canonical_data([{"id": i} for i in range(1, 101)])
                    inventory.pages[2] = source.canonical_data([{"id": 100}])
                elif fault == "inventory-count":
                    inventory.package["version_count"] = 2
                elif fault == "inventory-tag":
                    inventory.pages[1] = source.canonical_data(
                        [
                            {
                                "id": 1,
                                "name": "sha256:" + "f" * 64,
                                "metadata": {"container": {"tags": [tag]}},
                            }
                        ]
                    )
                elif fault == "post-copy-count" and "copy" in trace:
                    inventory.package["version_count"] = 2
                return inventory._capture(argv, maximum)
            return super()._capture(argv, maximum, **kwargs)

    def sleep(seconds: float) -> None:
        state["sleeps"].append(seconds)
        assert "candidate" not in trace and "package" not in trace and not config.exists()
        if fault == "interrupt":
            raise KeyboardInterrupt("synthetic publisher interruption")
        clock[0] += seconds

    monkeypatch.setattr(source, "GitHubRead", API)
    monkeypatch.setattr(source, "existing_public_package", real_inventory)
    monkeypatch.setattr(source.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(source.time, "sleep", sleep)
    return root, work, config, trace, state


@pytest.mark.parametrize("pending", [False, True])
@pytest.mark.parametrize("metadata_progress", [False, True])
def test_promote_waits_for_same_run_writer_before_real_inventory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pending: bool, metadata_progress: bool
) -> None:
    snapshots = (
        [_publisher_job_rows("queued", None), _publisher_job_rows("in_progress", None)]
        if pending
        else []
    ) + [_publisher_job_rows()]
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, snapshots, fault="metadata-pending" if metadata_progress else None
    )
    result = source.promote_image(work, root, 1800, 120)
    assert result["copy_invocations"] == 1
    assert state["reads"] == 2 * len(snapshots)
    assert state["sleeps"] == ([60, 60] if pending else [])
    assert set(state["deadlines"]) == {1900.0}
    assert state["read_effects"] == [("event",)] * state["reads"]
    assert trace.index("candidate") < trace.index("package") < trace.index("login")
    assert sum("versions?" in endpoint for endpoint in state["inventory"]) == 2
    assert trace[-1] == "owned-cleanup" and not config.exists()


@pytest.mark.parametrize("name", ["build", "security-scan", "publish"])
@pytest.mark.parametrize(
    "field,bad",
    [
        ("id", True),
        ("id", 0),
        ("id", -1),
        ("id", "3"),
        ("run_id", True),
        ("run_id", 124),
        ("run_attempt", True),
        ("run_attempt", 2),
        ("head_sha", "b" * 40),
        ("head_branch", "other"),
        ("run_url", "https://api.github.com/repos/foreign/repo/actions/runs/123"),
        ("run_url", "https://api.github.com/repos/" + source.GHCR_REPOSITORY + "/actions/runs/124"),
    ],
)
def test_promote_writer_rejects_wrong_native_job_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, field: str, bad: Any
) -> None:
    rows = _publisher_job_rows()
    next(row for row in rows if row["name"] == name)[field] = bad
    root, work, config, trace, state = _writer_ordering_fixture(monkeypatch, tmp_path, [rows])
    with pytest.raises(source.QualificationError, match="^publisher_selected_job_identity$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == 2 and not state["sleeps"]
    assert "candidate" not in trace and not state["inventory"] and not config.exists()
    assert trace[-1] == "owned-cleanup"


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("missing", "publisher_selected_job_cardinality"),
        ("duplicate", "publisher_selected_job_cardinality"),
        ("own-job", "publisher_selected_job_cardinality"),
        ("id-missing", "publisher_selected_job_identity"),
        ("status-missing", "publisher_backend_publish_state"),
        ("conclusion-missing", "publisher_backend_publish_state"),
        ("unknown-status", "publisher_backend_publish_state"),
        ("pending-success", "publisher_backend_publish_state"),
        ("build-pending", "publisher_positive_build_security_predecessors"),
        ("security-failed", "publisher_positive_build_security_predecessors"),
    ],
)
def test_promote_writer_rejects_incomplete_or_ambiguous_jobs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str, diagnostic: str
) -> None:
    rows = _publisher_job_rows()
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows.append({**rows[-1], "id": 4})
    elif fault == "own-job":
        rows[-1]["name"] = "prometheus-publish"
    elif fault.endswith("-missing"):
        del rows[-1][fault.removesuffix("-missing")]
    elif fault == "unknown-status":
        rows[-1]["status"] = "waiting"
    elif fault == "pending-success":
        rows[-1]["status"] = "in_progress"
    elif fault == "build-pending":
        rows[0].update(status="in_progress", conclusion=None)
    else:
        rows[1]["conclusion"] = "failure"
    root, work, config, trace, state = _writer_ordering_fixture(monkeypatch, tmp_path, [rows])
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.promote_image(work, root, 1800, 120)
    assert "candidate" not in trace and not state["inventory"] and not config.exists()


@pytest.mark.parametrize(
    "conclusion",
    [None, "failure", "cancelled", "skipped", "neutral", "timed_out", "action_required", "unknown"],
)
def test_promote_writer_requires_positive_completion(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, conclusion: str | None
) -> None:
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, [_publisher_job_rows("completed", conclusion)]
    )
    with pytest.raises(source.QualificationError, match="^publisher_backend_publish_success$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == 2 and not state["sleeps"]
    assert "candidate" not in trace and not config.exists()


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("count-drift", "GitHub_page_count_drift"),
        ("bad-page", "GitHub_page_shape"),
        ("count-bool", "publisher_jobs_count"),
        ("count-string", "publisher_jobs_count"),
        ("count-large", "publisher_jobs_count"),
        ("count-negative", "publisher_jobs_count"),
        ("count-missing", "publisher_jobs_count"),
    ],
)
def test_promote_writer_rejects_native_count_and_page_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str, diagnostic: str
) -> None:
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, [_publisher_job_rows()], fault=fault
    )
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == (2 if fault in {"count-drift", "bad-page"} else 1)
    assert not state["sleeps"] and not state["inventory"] and "candidate" not in trace
    assert not config.exists()


@pytest.mark.parametrize("fault", ["regression", "build-id", "security-id", "publish-id"])
def test_promote_writer_rejects_observed_state_or_identity_regression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    rows = _publisher_job_rows("queued", None) if fault == "regression" else _publisher_job_rows()
    if fault != "regression":
        rows[{"build-id": 0, "security-id": 1, "publish-id": 2}[fault]]["id"] += 10
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, [_publisher_job_rows("in_progress", None), rows]
    )
    diagnostic = (
        "publisher_backend_publish_regression"
        if fault == "regression"
        else "publisher_selected_job_identity_drift"
    )
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == 4 and state["sleeps"] == [60]
    assert not state["inventory"] and "candidate" not in trace and not config.exists()


@pytest.mark.parametrize(
    "fault,seconds,reads,sleeps,diagnostic",
    [
        (None, 1800, 32, [60] * 15, "publisher_backend_publish_wait_bound"),
        (None, 61, 4, [60, 1], "qualification_deadline"),
        ("expired", 60, 0, [], "qualification_deadline"),
        ("interrupt", 1800, 2, [60], "synthetic publisher interruption"),
    ],
)
def test_promote_writer_wait_shares_original_deadline_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fault: str | None,
    seconds: int,
    reads: int,
    sleeps: list[int],
    diagnostic: str,
) -> None:
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, [_publisher_job_rows("in_progress", None)], fault=fault
    )
    error = KeyboardInterrupt if fault == "interrupt" else source.QualificationError
    with pytest.raises(error, match="^" + diagnostic + "$"):
        source.promote_image(work, root, seconds, 120)
    assert state["reads"] == reads and state["sleeps"] == sleeps
    assert set(state["deadlines"]) == {100.0 + seconds}
    assert trace[-1] == "owned-cleanup" and not config.exists()
    assert "candidate" not in trace and not state["inventory"]


@pytest.mark.parametrize(
    "diagnostic", ["GitHub_native_failed", "GitHub_page_shape", "duplicate_JSON_key"]
)
@pytest.mark.parametrize("cleanup_hold", [False, True])
def test_promote_writer_failed_read_is_terminal_and_keeps_primary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    diagnostic: str,
    cleanup_hold: bool,
) -> None:
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch,
        tmp_path,
        [_publisher_job_rows("queued", None), source.QualificationError(diagnostic)],
        cleanup_hold=cleanup_hold,
    )
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == 3 and state["sleeps"] == [60]
    assert "candidate" not in trace and not config.exists() and not state["inventory"]
    assert (work / "GitHub-private").exists() is cleanup_hold
    assert ("Publisher cleanup also failed:" in capsys.readouterr().err) is cleanup_hold


@pytest.mark.parametrize("field", ["GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"])
@pytest.mark.parametrize("value", ["", "0", "01", "-1", "1.0", " 1", "1\n", "١"])
def test_promote_writer_coordinates_are_canonical_positive_decimal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, value: str
) -> None:
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, [_publisher_job_rows()]
    )
    monkeypatch.setenv(field, value)
    with pytest.raises(source.QualificationError, match="^publisher_run_attempt_coordinates$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == 0 and not state["inventory"] and "candidate" not in trace
    assert not config.exists()


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("main-after-wait", "publisher_main_before_inventory"),
        ("overlap", "package_pagination_distinct"),
        ("inventory-count", "package_complete_inventory_count"),
        ("inventory-tag", "immutable_tag_existing_other_subject_HOLD"),
        ("post-copy-count", "package_complete_inventory_count"),
    ],
)
def test_promote_writer_success_does_not_bypass_main_or_package_guards(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str, diagnostic: str
) -> None:
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch,
        tmp_path,
        [_publisher_job_rows("in_progress", None), _publisher_job_rows()],
        fault=fault,
    )
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.promote_image(work, root, 1800, 120)
    assert state["reads"] == 4 and state["sleeps"] == [60]
    assert ("copy" in trace) is (fault == "post-copy-count")
    assert not config.exists() and not (work / "evidence/publication.json").exists()
    if fault == "main-after-wait":
        assert not state["inventory"]


def test_promote_known_writer_order_has_frozen_acyclic_workflow() -> None:
    import yaml

    raw = (Path(__file__).resolve().parents[1] / ".github/workflows/build.yml").read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        # Public frozen build workflow digest
        == "17deb9c904594c23ca20ecc88fc917c51bcb392aca108fff08358910e148bdf8"
    )
    jobs = yaml.safe_load(raw)["jobs"]
    assert jobs["publish"]["needs"] == ["build", "security-scan"]
    assert jobs["prometheus-publish"]["needs"] == ["build", "security-scan"]


@pytest.mark.parametrize("variant", ["equal-boundary", "changed-boundary", "within", "nonadjacent"])
def test_public_package_inventory_retains_observed_overlap_rejection(variant: str) -> None:
    """Replay the retained page5/page6 ID boundary with deterministic transport rows."""
    api = _PublicPackageInventoryAPI(16575)
    row = {"id": 1306109302, "metadata": {"container": {"tags": []}}}
    fifth = [{"id": value} for value in range(401, 500)] + [row]
    sixth = [copy.deepcopy(row)] + [{"id": value} for value in range(502, 601)]
    expected_page = 6
    if variant == "changed-boundary":
        sixth[0]["metadata"]["container"]["tags"] = ["changed"]
    elif variant == "within":
        fifth[-2] = copy.deepcopy(row)
        expected_page = 5
    elif variant == "nonadjacent":
        api.pages[3] = source.canonical_data([{"id": value} for value in range(201, 300)] + [row])
        fifth[-1] = {"id": 500}
    api.pages[5] = source.canonical_data(fifth)
    api.pages[6] = source.canonical_data(sixth)
    with pytest.raises(source.QualificationError, match="^package_pagination_distinct$"):
        source.existing_public_package(api)
    assert [page for page, _ in api.version_requests] == list(range(1, expected_page + 1))
    assert api.repository_reads == api.package_reads == 1


@pytest.mark.parametrize(
    "fault", ["100-jobs", "queued-again", "page-native", "duplicate-native-id"]
)
def test_promote_writer_polling_obeys_complete_native_snapshot_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    complete = _publisher_job_rows()
    if fault == "100-jobs":
        complete += [{"id": value, "name": "other"} for value in range(200, 297)]
        snapshots = [complete]
    elif fault == "duplicate-native-id":
        complete[-1]["id"] = complete[0]["id"]
        snapshots = [complete]
    else:
        snapshots = [
            _publisher_job_rows("queued", None),
            _publisher_job_rows("queued", None),
            complete,
        ]
    root, work, config, trace, state = _writer_ordering_fixture(
        monkeypatch, tmp_path, snapshots, fault=fault
    )
    if fault in {"page-native", "duplicate-native-id"}:
        diagnostic = (
            "GitHub_native_failed" if fault == "page-native" else "GitHub_complete_distinct_pages"
        )
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.promote_image(work, root, 1800, 120)
        assert state["reads"] == (4 if fault == "page-native" else 2)
        assert not state["inventory"] and "candidate" not in trace
    else:
        assert source.promote_image(work, root, 1800, 120)["copy_invocations"] == 1
        assert state["reads"] == (2 if fault == "100-jobs" else 6)
        assert state["sleeps"] == ([] if fault == "100-jobs" else [60, 60])
    assert trace[-1] == "owned-cleanup" and not config.exists()


def _promotion_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rejection: str | None = None,
    *,
    unchanged: bool = False,
    cleanup_hold: bool = False,
    already_present: bool = False,
    historical: bool = False,
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
        assert args[1] == (selected_root if historical else root)
        if rejection in {"input", "artifact", "native", "scanner"}:
            raise source.QualificationError("synthetic_reject_" + rejection)
        return candidate

    def admission(*args: Any) -> dict[str, Any]:
        trace.append("event")
        assert not config.exists()
        if rejection == "event":
            raise source.QualificationError("synthetic_reject_event")
        return {
            "mode": (
                "unchanged_published"
                if unchanged
                else "historical_main_recovery" if historical else "new_main_selection"
            ),
            "head": "a" * 40,
            "publisher_head": "a" * 40,
            "historical_source_head": "3" * 40 if historical else None,
        }

    selected_root = tmp_path / "historical-data"
    selected_root.mkdir()

    def candidate_root(api: Any, material: Path, work_dir: Path, event: dict[str, Any]) -> Path:
        assert material == root and work_dir == work and not config.exists()
        if historical:
            assert event["mode"] == "historical_main_recovery"
            trace.append("source-root")
            return selected_root
        return material

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
                return {"total_count": 3}
            assert endpoint.endswith("/git/ref/heads/main")
            self.main_reads += 1
            bad = (rejection == "main-before-credentials" and self.main_reads == 2) or (
                rejection == "main-before-write" and self.main_reads == 3
            )
            return {"object": {"sha": "c" * 40 if bad else "a" * 40}}

        def pages(self, *args: Any) -> list[dict[str, Any]]:
            return _publisher_job_rows()

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            if "login" in argv:
                trace.append("login")
                expected_prefix = (
                    ["event", "predecessor"]
                    if unchanged
                    else (
                        ["event", "source-root", "candidate"]
                        if historical
                        else ["event", "candidate"]
                    )
                )
                assert trace[: len(expected_prefix)] == expected_prefix
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
    # A data-root seam spy only; separate semantic tests exercise its real native proof.
    monkeypatch.setattr(source, "candidate_source_root", candidate_root, raising=False)
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
    "rejection,diagnostic",
    [
        pytest.param("event", "synthetic_reject_event", id="event"),
        pytest.param("prepared", "source_prepared_not_consumable", id="prepared"),
        pytest.param("input", "synthetic_reject_input", id="input"),
        pytest.param("artifact", "synthetic_reject_artifact", id="artifact"),
        pytest.param("tool", "publisher_retained_tool_changed", id="tool"),
        pytest.param("native", "synthetic_reject_native", id="native"),
        pytest.param("scanner", "synthetic_reject_scanner", id="scanner"),
        pytest.param("package", "synthetic_reject_package", id="package"),
        pytest.param("tag", "immutable_tag_existing_other_subject_HOLD", id="tag"),
        pytest.param(
            "main-before-credentials",
            "publisher_main_before_credentials",
            id="main-before-credentials",
        ),
        pytest.param("predecessor", "synthetic_reject_predecessor", id="predecessor"),
    ],
)
def test_promote_rejection_precedes_registry_directory_and_login(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, rejection: str, diagnostic: str
) -> None:
    """Prove the named original rejection is reached before registry activation."""
    root, work, config, trace, _manifest = _promotion_fixture(
        monkeypatch, tmp_path, rejection, unchanged=rejection == "predecessor"
    )
    with pytest.raises(source.QualificationError, match="^" + re.escape(diagnostic) + "$"):
        source.promote_image(work, root, 30, 2)
    expected_seam = (
        "predecessor"
        if rejection == "predecessor"
        else (
            "candidate"
            if rejection in {"input", "artifact", "tool", "native", "scanner"}
            else (
                "package" if rejection in {"package", "tag", "main-before-credentials"} else "event"
            )
        )
    )
    assert expected_seam in trace
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


@pytest.mark.parametrize(
    "failure,diagnostic",
    [
        pytest.param("login", "synthetic_login_failed", id="login"),
        pytest.param("main-before-write", "publisher_main_before_write", id="main-before-write"),
        pytest.param("verification", "synthetic_verification_failed", id="verification"),
    ],
)
def test_promote_operation_failure_cleans_credentials_without_success_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure: str, diagnostic: str
) -> None:
    """Preserve each exact original native failure and owned credential cleanup."""
    root, work, config, trace, _manifest = _promotion_fixture(monkeypatch, tmp_path, failure)
    with pytest.raises(source.QualificationError, match="^" + re.escape(diagnostic) + "$"):
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


@pytest.mark.parametrize("selector", ["--derive-xnet060", "--derive-xnet062"])
@pytest.mark.parametrize(
    "extra",
    [
        ["--qualify-existing-ghcr-package", "--public-output", "public.json"],
        ["--public-output", "public.json"],
        ["--derive-xnet06"],
        ["--derive-xnet060", "--derive-xnet062"],
        ["--operation", "pair"],
    ],
)
def test_fixed_derivation_selector_rejects_mixed_or_abbreviated_modes_before_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra: list[str], selector: str
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
        args.append(selector)
    monkeypatch.setattr(source.sys, "argv", args + extra)
    with pytest.raises(SystemExit) as error:
        source.main()
    assert error.value.code == 2
    assert not (tmp_path / "uncreated").exists()


@pytest.mark.parametrize("selector", ["xnet060", "xnet062"])
def test_derivation_selector_dispatches_only_the_selected_metadata_action(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, selector: str
) -> None:
    calls: list[dict[str, Any]] = []

    def observed(work: Path, seconds: int, cleanup: int, **kwargs: Any) -> None:
        assert work == tmp_path / "uncreated" and (seconds, cleanup) == (900, 120)
        calls.append(kwargs)

    monkeypatch.setattr(source, "qualify", observed)
    monkeypatch.setattr(source.signal, "signal", lambda *args: None)
    monkeypatch.setattr(
        source.sys,
        "argv",
        [
            "qualifier",
            "--derive-" + selector,
            "--work-dir",
            str(tmp_path / "uncreated"),
            "--timeout-seconds",
            "900",
            "--cleanup-seconds",
            "120",
        ],
    )
    assert source.main() == 0
    assert calls == [{"derive_" + selector: True}]
    assert not (tmp_path / "uncreated").exists()


def test_derivation_rejects_unbound_or_conflicting_targets_before_effects(tmp_path: Path) -> None:
    with pytest.raises(source.QualificationError, match="conflicting_xnet_derivation_targets"):
        source.qualify(tmp_path / "uncreated", 900, 120, derive_xnet060=True, derive_xnet062=True)
    with pytest.raises(source.QualificationError, match="unsupported_xnet_derivation_target"):
        source.derive_xnet_observe(
            cast(Any, None),
            tmp_path,
            tmp_path,
            tmp_path,
            tmp_path,
            tmp_path,
            {},
            "/usr/bin/docker",
            tmp_path,
            {},
            {},
            target_version="v0.63.0",
        )
    assert not (tmp_path / "uncreated").exists()


@pytest.mark.parametrize(
    "target_version,fault",
    [
        (target, fault)
        for target in ("v0.60.0", "v0.62.0")
        for fault in (
            "none",
            "base-lock",
            "get-error",
            "derived-download-sum",
            "b-lock-mismatch",
            "get-nonlock",
        )
    ]
    + [("v0.62.0", "incumbent-lock"), ("v0.62.0", "incumbent-get-error")],
)
def test_derivation_controller_uses_two_clean_original_fixed_get_replays_or_stops(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str, target_version: str
) -> None:
    """Synthetic native transcript only; it cannot qualify Go, source or closure."""
    work = tmp_path / "work"
    work.mkdir()
    evidence = work / "evidence"
    evidence.mkdir()
    original = {"go.mod": b"original module\n", "go.sum": b"original sums\n"}
    derived = {"go.mod": b"derived module\n", "go.sum": b"derived sums\n"}
    incumbent = {"go.mod": b"incumbent module\n", "go.sum": b"incumbent sums\n"}
    monkeypatch.setattr(
        source,
        "XNET060_INCUMBENT_LOCKS",
        {name: source.sha(raw) for name, raw in incumbent.items()},
    )
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
                return json.dumps([_native_fixed_base_image()]).encode()
            command = argv[1:]
            changed = (cwd / "go.mod").read_bytes() != original["go.mod"]
            current_mod = (cwd / "go.mod").read_bytes()
            version = (
                target_version
                if current_mod == derived["go.mod"]
                else "v0.60.0" if changed else "v0.58.0"
            )
            if target_version == "v0.62.0" and command == ["get", "golang.org/x/net@v0.60.0"]:
                assert env["GOFLAGS"] == "" and not changed
                for file, raw in incumbent.items():
                    (cwd / file).write_bytes(
                        raw + (b"wrong" if fault == "incumbent-lock" and file == "go.sum" else b"")
                    )
                if fault == "incumbent-get-error":
                    raise source.QualificationError("synthetic_incumbent_get_failure")
                return b""
            if command == ["get", "golang.org/x/net@" + target_version]:
                assert env["GOFLAGS"] == ""
                if target_version == "v0.62.0":
                    lane = "b" if cwd.name == "source-b" else "a"
                    for suffix in ("before", "restored", "physical-members"):
                        assert (
                            evidence / (lane + "-incumbent-cache-" + suffix + ".json")
                        ).is_file()
                assert current_mod == (
                    incumbent["go.mod"] if target_version == "v0.62.0" else original["go.mod"]
                )
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
                return source.CURRENT_GO_VERSION.encode()
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
                if version == target_version and fault == "derived-download-sum":
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
        native: Any,
        root: Path,
        tool: Path,
        modules: Path,
        expected: dict[str, bytes],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        assert source._derivation_locks(root) == expected
        if kwargs.get("restore_cache_modes"):
            assert target_version == "v0.62.0" and expected == incumbent
        else:
            assert expected == derived or fault == "b-lock-mismatch"
        offline.append((root.name, modules))
        return {
            "full_native_package_objects": {
                "prometheus": {"p": {"ImportPath": "p"}},
                "promtool": {"t": {"ImportPath": "t"}},
            },
            # This controller stub exercises early retention, not cache validity.
            "cache_mode_restoration": {"files_before": [], "files_restored": [], "members": []},
        }

    monkeypatch.setattr(source, "_derivation_offline", observed)
    report: dict[str, Any] = {"UI_transform": {"synthetic": True}}
    native = FakeNative()
    if fault == "none":
        source.derive_xnet_observe(
            native,
            work,
            downloads,
            a,
            go,
            ui,
            {},
            "/usr/bin/docker",
            work,
            {},
            report,
            target_version=target_version,
        )
        assert len(report["module_derivation"]["replays"]) == 2
        assert len(offline) == (4 if target_version == "v0.62.0" else 2)
        assert offline[0][1] != offline[-1][1]
        assert report["module_action"] == (
            "xnet062-replay" if target_version == "v0.62.0" else "xnet060-replay"
        )
        for replay in report["module_derivation"]["replays"]:
            assert replay["before"]["selected"]["golang.org/x/net"]["Version"] == (
                "v0.60.0" if target_version == "v0.62.0" else "v0.58.0"
            )
            assert replay["after"]["selected"]["golang.org/x/net"]["Version"] == target_version
            if target_version == "v0.62.0":
                assert (
                    replay["incumbent_reconstruction"]["original_before"]["selected"][
                        "golang.org/x/net"
                    ]["Version"]
                    == "v0.58.0"
                )
                assert replay["incumbent_reconstruction"]["locks"] == source.XNET060_INCUMBENT_LOCKS
        assert (evidence / "a-module-derivation.patch").read_bytes() == (
            evidence / "b-module-derivation.patch"
        ).read_bytes()
    else:
        with pytest.raises(source.QualificationError):
            source.derive_xnet_observe(
                native,
                work,
                downloads,
                a,
                go,
                ui,
                {},
                "/usr/bin/docker",
                work,
                {},
                report,
                target_version=target_version,
            )
    if fault == "incumbent-get-error":
        for name, raw in incumbent.items():
            assert (evidence / ("a-failed-incumbent-" + name)).read_bytes() == raw
    gets = [(argv, env, cwd) for argv, env, cwd in transcript if argv[1:2] == ["get"]]
    final_gets = [
        (argv, env, cwd)
        for argv, env, cwd in gets
        if argv[2] == "golang.org/x/net@" + target_version
    ]
    assert len(final_gets) == (
        2
        if fault in ("none", "b-lock-mismatch")
        else 0 if fault in ("base-lock", "incumbent-lock", "incumbent-get-error") else 1
    )
    for argv, env, cwd in gets:
        assert argv[1] == "get" and env["GOFLAGS"] == ""
        assert argv[2] in ("golang.org/x/net@v0.60.0", "golang.org/x/net@" + target_version)
    if target_version == "v0.62.0":
        assert len(gets) - len(final_gets) == (
            2 if fault in ("none", "b-lock-mismatch") else 0 if fault == "base-lock" else 1
        )
    for argv, env, cwd in transcript:
        if argv[0] != "/usr/bin/docker" and argv[1:2] != ["get"]:
            assert env["GOFLAGS"] == "-mod=readonly"
        if argv[1:3] == ["mod", "download"]:
            assert argv[1:] == ["mod", "download", "-json"]


@pytest.mark.parametrize(
    "missing,restore_cache_modes,cache_fault",
    [
        (False, False, None),
        (True, False, None),
        (False, True, None),
        (True, True, None),
        (False, True, "new-directory"),
        (False, True, "replacement"),
        (False, True, "changed-bytes"),
    ],
)
def test_derivation_offline_keeps_both_production_graphs_and_existing_sandbox_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing: bool,
    restore_cache_modes: bool,
    cache_fault: str | None,
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
    (modules / "empty-directory").mkdir(mode=0o750)
    modes_before = {path: path.stat().st_mode for path in (modules, *modules.rglob("*"))}
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
                return b"a" * 64 + b"\n"
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
            raw = source.CURRENT_GO_VERSION.encode()
        elif command == ["mod", "verify"]:
            raw = b"all modules verified"
        else:
            selected = command[-1].rsplit("/", 1)[-1]
            raw = package_stream("prometheus" if missing and selected == "promtool" else selected)
            if selected == "promtool" and cache_fault:
                modules.chmod(0o755)
                if cache_fault == "new-directory":
                    (modules / "unexpected-empty").mkdir()
                elif cache_fault == "replacement":
                    (modules / "cache").rename(modules / "old-cache")
                    (modules / "cache").write_bytes(b"inert cache")
                    (modules / "old-cache").unlink()
                else:
                    (modules / "cache").chmod(0o644)
                    (modules / "cache").write_bytes(b"changed bytes")
                (modules / "cache").chmod(0o444)
                modules.chmod(0o555)
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
        _native_fixed_base_image(),
        "synthetic-owner",
        [],
        {},
        {},
        tmp_path,
    )
    if missing or cache_fault:
        with pytest.raises(source.QualificationError):
            source._derivation_offline(*arguments, restore_cache_modes=restore_cache_modes)
        assert stat.S_IMODE(modules.stat().st_mode) == 0o555
    else:
        result = source._derivation_offline(*arguments, restore_cache_modes=restore_cache_modes)
        assert set(result["command_observations"]) == {"prometheus", "promtool"}
        assert set(result["full_native_package_objects"]) == {"prometheus", "promtool"}
        assert len(result["container_completion"]) == 4
        if restore_cache_modes:
            assert {path: path.stat().st_mode for path in modes_before} == modes_before
            assert (
                result["cache_mode_restoration"]["files_before"]
                == result["cache_mode_restoration"]["files_restored"]
            )
            assert {row["path"] for row in result["cache_mode_restoration"]["members"]} == {
                ".",
                "cache",
                "empty-directory",
            }
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
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    published: bool,
    fault: str | None = None,
    mode: str | None = None,
    event_name: str = "pull_request",
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
    selected_mode = mode or ("unchanged_published" if published else "changed_pr_candidate")
    publisher_head = "a" * 40 if event_name == "push" else "b" * 40
    route = (
        "trusted_published"
        if event_name == "push"
        else "unchanged_pr_published" if published else selected_mode
    )
    event = tmp_path / "event.json"
    event_data: dict[str, Any] = {"number": 2493, "ref": "refs/heads/main", "before": "b" * 40}
    if event_name == "pull_request":
        event_data["pull_request"] = {"head": {"sha": "a" * 40}, "base": {"sha": "b" * 40}}
    event.write_text(json.dumps(event_data))
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
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_REF": "refs/heads/main" if event_name == "push" else "refs/pull/2493/merge",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_EVENT_PATH": str(event),
        "PROMETHEUS_CREDENTIAL_ROUTE": route,
        "GITHUB_REPOSITORY_OWNER": source.GHCR_OWNER,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "RUNNER_TEMP": str(tmp_path),
        "GH_TOKEN": "synthetic.api",
        "GITHUB_TOKEN": "synthetic.api",
    }.items():
        monkeypatch.setenv(key, value)
    if published and fault != "missing-token":
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

        def json(self, endpoint: str) -> dict[str, Any]:
            """Return only synthetic live coordinates for the before-use freshness check."""
            if endpoint.endswith("/git/ref/heads/main"):
                return {"object": {"sha": "a" * 40}}
            assert endpoint.endswith("/pulls/2493")
            return {
                "state": "open",
                "head": {"sha": "a" * 40, "repo": {"id": 1043311030}},
                "base": {"ref": "main", "sha": "b" * 40, "repo": {"id": 1043311030}},
            }

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
        if fault == "restore-bound-manifest":
            path.write_bytes(source.canonical_data(manifest))
        return {
            "mode": selected_mode,
            "head": "c" * 40 if fault == "head-binding" else "a" * 40,
            "publisher_head": (
                "c" * 40 if fault == "publisher-binding" else publisher_head if published else None
            ),
            "historical_source_head": "3" * 40 if selected_mode.startswith("historical_") else None,
        }

    selected_root = tmp_path / "historical-data"
    selected_root.mkdir()

    def candidate_root(api: Any, material: Path, work_dir: Path, event: dict[str, Any]) -> Path:
        assert material == root and work_dir == work and not reader.exists()
        if selected_mode == "historical_pr_candidate":
            trace.append("source-root")
            return selected_root
        return material

    def candidate(*args: Any) -> dict[str, Any]:
        trace.append("candidate")
        assert not reader.exists()
        assert args[1] == (selected_root if selected_mode == "historical_pr_candidate" else root)
        if fault == "candidate":
            raise source.QualificationError("artifact_identity_expiry_size")
        return {"docker_archive": tmp_path / "synthetic-image.docker.tar"}

    def predecessor(*args: Any) -> dict[str, Any]:
        trace.append("predecessor")
        assert args[1] == publisher_head
        if fault == "predecessor":
            clock[0] += 100
            raise source.QualificationError("positive_publication_predecessor_active")
        return {
            "run": {
                "id": 1,
                "head_sha": publisher_head,
                "head_branch": "main",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
            },
            "job": {
                "id": 1,
                "head_sha": publisher_head,
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
    # This spy checks flow only; real historical-data admission has separate native fixtures.
    monkeypatch.setattr(source, "candidate_source_root", candidate_root, raising=False)
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


@pytest.mark.parametrize(
    "case,cleanup_failure",
    [
        (case, False)
        for case in (
            "failure",
            "cancelled",
            "timed_out",
            "job-failure",
            "job-cancelled",
            "job-timed_out",
            "missing-job",
            "skipped-job",
            "malformed",
            "api-error",
            "pending-terminal",
            "missing-active-success",
            "new-attempt-success",
            "missing-timeout",
            "active-timeout",
        )
    ]
    + [("job-failure", True), ("api-error", True)],
)
def test_consumer_publication_wait_uses_real_recognizer_without_terminal_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: str,
    cleanup_failure: bool,
) -> None:
    real_predecessor = source.require_publication_predecessor
    root, work, reader, trace = _consumer_fixture(
        monkeypatch,
        tmp_path,
        published=True,
        fault="cleanup" if cleanup_failure else None,
        event_name="push",
    )
    base_api = source.GitHubRead
    snapshots, diagnostic, expected_sleeps = _publication_wait_observations(case)
    observed: list[_PublicationPredecessorAPI] = []
    clock = [100.0]
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    class API(base_api):
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            super().__init__(private, evidence, deadline, cleanup)
            assert deadline == 130 and cleanup == 2
            self.publication = _PublicationPredecessorAPI(snapshots=snapshots)
            if case == "api-error":
                endpoint = f"/repos/{source.GHCR_REPOSITORY}/actions/workflows/build.yml/runs?event=push&head_sha={'a' * 40}&per_page=100&page=1"
                self.publication.overrides[endpoint] = source.QualificationError(
                    "GitHub_native_failed"
                )
            observed.append(self.publication)

        def json(self, endpoint: str) -> dict[str, Any]:
            if "/actions/" in endpoint:
                return self.publication.json(endpoint)
            return super().json(endpoint)

        def pages(self, endpoint: str, key: str | None, count: int) -> list[dict[str, Any]]:
            return self.publication.pages(endpoint, key, count)

        def begin_cleanup(self) -> float:
            return clock[0] + 2

    # The consumer fixture's event/publisher head is a; bind the synthetic native
    # observations to that same head rather than bypassing the real recognizer.
    for runs, jobs in snapshots:
        for row in runs:
            row["head_sha"] = "a" * 40
        for rows in jobs.values():
            for row in rows:
                row["head_sha"] = "a" * 40
    monkeypatch.setattr(source, "GitHubRead", API)
    monkeypatch.setattr(source, "require_publication_predecessor", real_predecessor)
    monkeypatch.setattr(source.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(source.time, "sleep", sleep)
    if diagnostic is None:
        source.consume_image(work, root, 30, 2)
        assert "public-package" in trace and "login" in trace and "inspect" in trace
    else:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.consume_image(work, root, 30, 2)
        assert not {"public-package", "login", "pull", "raw", "load", "inspect"}.intersection(trace)
        assert not reader.exists() and not (work / "evidence/consumer.json").exists()
    if expected_sleeps >= 0:
        assert len(sleeps) == expected_sleeps
        assert observed[0].observation == (0 if case == "api-error" else expected_sleeps + 1)
    else:
        assert clock[0] == 130 and sum(sleeps) == 30 and observed[0].observation == 6
    if case == "new-attempt-success":
        assert any("/attempts/2/jobs" in endpoint for endpoint in observed[0].requests)
    if cleanup_failure:
        assert (
            "Consumer cleanup also failed:GHCR_unknown_or_reused_group_member"
            in capsys.readouterr().err
        )


@pytest.mark.parametrize("case", ["success", "failure", "job-timed_out", "missing", "active"])
def test_nonpolling_promoter_keeps_native_predecessor_admission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    real_predecessor = source.require_publication_predecessor
    root, work, config, trace, _manifest = _promotion_fixture(monkeypatch, tmp_path, unchanged=True)
    base_api = source.GitHubRead
    if case == "success":
        snapshots, diagnostic = [([_publication_run()], {12: [_publication_job()]})], None
    elif case == "missing":
        snapshots, diagnostic = [([], {})], "positive_publication_predecessor_missing"
    elif case == "active":
        snapshots, diagnostic = [
            ([_publication_run(status="in_progress", conclusion=None)], {12: []})
        ], "positive_publication_predecessor_active"
    else:
        snapshots, diagnostic, _sleeps = _publication_wait_observations(case)
    for runs, jobs in snapshots:
        for row in runs:
            row["head_sha"] = "b" * 40
        for rows in jobs.values():
            for row in rows:
                row["head_sha"] = "b" * 40
    observed: list[_PublicationPredecessorAPI] = []

    class API(base_api):
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            super().__init__(private, evidence, deadline, cleanup)
            self.publication = _PublicationPredecessorAPI(snapshots=snapshots)
            observed.append(self.publication)

        def json(self, endpoint: str) -> dict[str, Any]:
            if (
                "/workflows/build.yml/runs?" in endpoint
                or "/actions/runs/12/" in endpoint
                or endpoint.endswith("/actions/runs/12")
            ):
                return self.publication.json(endpoint)
            return super().json(endpoint)

        def pages(self, endpoint: str, key: str | None, count: int) -> list[dict[str, Any]]:
            if key == "workflow_runs" or "/actions/runs/12/" in endpoint:
                if key == "workflow_runs":
                    trace.append("predecessor")
                return self.publication.pages(endpoint, key, count)
            return super().pages(endpoint, key, count)

    monkeypatch.setattr(source, "GitHubRead", API)
    monkeypatch.setattr(source, "require_publication_predecessor", real_predecessor)
    monkeypatch.setattr(
        source.time, "sleep", lambda _seconds: pytest.fail("nonpolling predecessor slept")
    )
    if diagnostic is None:
        assert source.promote_image(work, root, 30, 2)["copy_invocations"] == 0
        assert "package" in trace and "login" in trace
    else:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.promote_image(work, root, 30, 2)
        assert not {"package", "login", "copy", "candidate"}.intersection(trace)
    assert observed[0].observation == 1 and not config.exists()


@pytest.mark.parametrize("root_module", (source.ROOT_MODULE, "oras.land/oras"))
@pytest.mark.parametrize(
    "variant", ("unchanged", "lock", "source", "Go", "verify", "snapshot", "root", "graph")
)
def test_tool_prefetch_retains_before_after_and_preserves_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str, root_module: str
) -> None:
    """Synthetic native I/O only; actual missing post-state stays an explicit error."""
    work, tree, go = tmp_path / "work", tmp_path / "source", tmp_path / "go"
    for path in (work, tree, go, work / "evidence"):
        path.mkdir()
    (go / "bin").mkdir()
    (go / "bin/go").write_bytes(b"synthetic compiler identity, never executed")
    original = {"go.mod": b"synthetic original module\n", "go.sum": b"synthetic original sums\n"}
    for name, raw in original.items():
        (tree / name).write_bytes(raw)
    (tree / "kept.go").write_bytes(b"package synthetic\n")
    native = source.Native(work / "evidence", time.monotonic() + 60, 2)
    calls: list[list[str]] = []

    def run(argv: list[str], name: str, env: dict[str, str], *, cwd: Path) -> bytes:
        calls.append(argv)
        assert cwd == tree and env["GOTOOLCHAIN"] == "local" and env["GOWORK"] == "off"
        if name.endswith("-version"):
            return source.CURRENT_GO_VERSION.encode()
        if name.endswith("-download"):
            if variant == "lock":
                (tree / "go.sum").write_bytes(b"actual synthetic lock drift\n")
            if variant == "source":
                (tree / "kept.go").write_bytes(b"package changed\n")
            if variant == "Go":
                (go / "bin/go").write_bytes(b"changed compiler identity")
            (work / "tool-modules/cached.mod").write_bytes(b"synthetic cached module")
            return b'{"Path":"example.invalid/synthetic","Version":"v1.0.0"}'
        if name.endswith("-selected"):
            return source.canonical_data(
                {"Path": "wrong" if variant == "root" else root_module, "Main": True}
            )
        if name.endswith("-graph"):
            return (
                b""
                if variant == "graph"
                else (root_module + " example.invalid/synthetic@v1.0.0\n").encode()
            )
        assert name.endswith("-verify")
        if variant in ("verify", "snapshot"):
            if variant == "snapshot":
                (tree / "go.sum").unlink()
            raise source.QualificationError("synthetic_primary_verify_failure")
        return b"all modules verified\n"

    monkeypatch.setattr(native, "run", run)
    if variant == "unchanged":
        source.prefetch_modules(
            native,
            work,
            tree,
            go,
            "tool",
            {n: source.sha(v) for n, v in original.items()},
            root_module=root_module,
        )
    else:
        expected = (
            "prefetch_original_locks_source"
            if variant in ("lock", "source", "Go")
            else (
                "selected_module_root"
                if variant == "root"
                else (
                    "empty_native_module_graph"
                    if variant == "graph"
                    else "synthetic_primary_verify_failure"
                )
            )
        )
        with pytest.raises(source.QualificationError, match="^" + expected + "(?:\n|$)"):
            source.prefetch_modules(
                native,
                work,
                tree,
                go,
                "tool",
                {n: source.sha(v) for n, v in original.items()},
                root_module=root_module,
            )
    assert calls[1] == [str(go / "bin/go"), "mod", "download", "-json"]
    report = source.one_object((native.evidence / "tool-prefetch.json").read_bytes())
    for name, raw in original.items():
        assert (native.evidence / ("tool-prefetch-before-" + name)).read_bytes() == raw
        assert report["before"]["locks"][name]["mode"] == (tree / "go.mod").stat().st_mode & 0o777
    if variant == "snapshot":
        assert report["failure"]["code"] == "synthetic_primary_verify_failure"
        assert report["snapshot_errors"][0]["phase"] == "verify-after"
        assert report["snapshot_errors"][0]["class"] == "FileNotFoundError"
        assert report["after"]["source_inventory"] is None
    else:
        assert report["after"]["source_inventory"] is not None
        assert bool(report["snapshot_errors"]) is (variant in ("lock", "source", "Go"))
        if variant == "unchanged":
            assert [row["name"] for row in report["commands"]] == [
                "version",
                "download",
                "verify",
                "selected",
                "graph",
            ]
            before_cache = json.loads(
                (native.evidence / "tool-prefetch-cache-before-freeze.json").read_bytes()
            )
            frozen = json.loads((native.evidence / "tool-prefetch-cache-frozen.json").read_bytes())
            assert before_cache == [
                {
                    "path": "cached.mod",
                    "mode": 0o644,
                    "size": 23,
                    "sha256": source.sha(b"synthetic cached module"),
                }
            ]
            assert frozen == [dict(before_cache[0], mode=0o444)]
            for row in report["commands"]:
                assert (
                    report[row["name"] + "-before"]
                    == report[row["name"] + "-after"]
                    == report["before"]
                )
        if variant == "lock":
            assert (
                native.evidence / "tool-prefetch-after-go.sum"
            ).read_bytes() == b"actual synthetic lock drift\n"
        if variant == "source":
            assert report["before"]["source_inventory"] != report["after"]["source_inventory"]


def _tool_prefetch_recovery_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> Any:
    """Complete synthetic failed transport; no historical proof, API or native execution."""
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN", "DOCKER_CONFIG"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "999",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_REF": "refs/heads/codex/dependency-native-runtime-remediation",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(source, "GO", replace(source.GO, files=1))
    ref = "refs/heads/codex/dependency-native-runtime-remediation"
    head = "5de54811121079eadbd3f5d8dbbb8720f712530a"
    workflow = {"id": 199904435, "path": ".github/workflows/build.yml"}
    run = {
        "id": 38170923494,
        "head_sha": head,
        "head_branch": ref[11:],
        "repository": {"id": 1043311030},
        "head_repository": {"id": 1043311030},
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "failure",
        "workflow_id": workflow["id"],
    }
    job = {
        "id": 114563178711,
        "name": "prometheus-oras-qualification",
        "run_id": run["id"],
        "head_sha": head,
        "status": "completed",
        "conclusion": "failure",
    }
    inventory = source.canonical_data(
        [{"path": "synthetic.go", "git_mode": "100644", "size": 1, "sha256": "b" * 64}]
    )
    inputs = {"oras": {"retained": None, "canonical_inventory_sha256": source.sha(inventory)}}
    old_files = {name: ("synthetic historical " + name).encode() for name in source.PRODUCER_FILES}
    old_files[source.MANIFEST_PATH] = source.canonical_data(
        {"schema": source.IMAGE_SCHEMA, "inputs": inputs}
    )
    projection = {
        "inputs": inputs,
        "raw_producer": {
            n: {"bytes": len(old_files[n]), "sha256": source.sha(old_files[n])}
            for n in source.PRODUCER_FILES
        },
    }
    digest = "sha256:" + source.sha(source.canonical_data(projection))
    monkeypatch.setattr(source, "TOOL_PREFETCH_INPUT_DIGEST", digest)
    report = {
        "identity": "PulsePlate-rebuilt ORAS 1.3.4",
        "source_revision": source.ORAS_REVISION,
        "source_tree": source.ORAS_TREE,
        "original_locks": source.ORAS_LOCKS,
        "input_projection": projection,
        "input_digest": digest,
        "admission": {
            "actual_prior_invocations": [],
            "budget": 1,
            "head": head,
            "job": job["name"],
            "ref": ref,
            "run_id": run["id"],
            "workflow_id": workflow["id"],
        },
        "tool_compile_invocations": 0,
        "Prometheus_compile_invocations": 0,
        "failure": {"class": "QualificationError", "code": "prefetch_original_locks_source"},
        "cleanup": [],
        "native_commands": [],
    }
    files = {"go-members.json": inventory, "oras-source-members.json": inventory}
    prior_work = Path("/home/runner/work/_temp/prometheus-oras-38170923494-1")
    environment = source.clean_environment(
        prior_work / "tool-home",
        prior_work / "tool-tmp",
        prior_work / "tool-cache",
        prior_work / "tool-modules",
        offline=False,
    )
    for name, command, stdout in (
        ("version", ["version"], source.GO_VERSION.encode()),
        (
            "download",
            ["mod", "download", "-json", "all"],
            b'{"Path":"example.invalid/synthetic","Version":"v1.0.0"}',
        ),
        ("verify", ["mod", "verify"], b"all modules verified\n"),
    ):
        row = {
            "argv": [str(prior_work / "go/bin/go"), *command],
            "cwd": str(prior_work / "source"),
            "environment": environment,
            "exit": 0,
            "failure": None,
        }
        for suffix, raw in (("stdout", stdout), ("stderr", b"")):
            member = f"tool-{name}.{suffix}"
            files[member] = raw
            row[suffix], row[suffix + "_sha256"] = str(
                prior_work / "evidence" / member
            ), source.sha(raw)
        report["native_commands"].append(row)
    for number in range(1, 36):
        prefix = f"GitHub-{number}"
        argv = (
            ["/usr/bin/gh", "auth", "status", "--hostname", "github.com"]
            if number == 1
            else [
                "/usr/bin/gh",
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                "/repos/" + source.GHCR_REPOSITORY + "/synthetic",
            ]
        )
        files[prefix + ".stdout"], files[prefix + ".stderr"] = b"{}", b""
        files[prefix + ".json"] = source.canonical_data(
            {
                "argv": argv,
                "exit": 0,
                "stdout_bytes": 2,
                "stdout_sha256": source.sha(b"{}"),
                "stderr_sha256": source.sha(b""),
            }
        )
    if variant == "false-counter":
        report["tool_compile_invocations"] = False
    elif variant == "missing-counter":
        del report["tool_compile_invocations"]
    elif variant == "compiled":
        report["tool_compile_invocations"] = 1
    elif variant == "extra-command":
        report["native_commands"].append(copy.deepcopy(report["native_commands"][0]))
    elif variant == "argv":
        report["native_commands"][1]["argv"][-1] = "different"
    elif variant == "native-exit":
        report["native_commands"][1]["exit"] = False
    elif variant == "output-mismatch":
        files["tool-download.stdout"] += b"\n"
    elif variant == "extra-marker":
        files["invocation-start.json"] = b"{}"
    elif variant == "binary":
        files["oras"] = b"synthetic binary data, never executed"
    elif variant == "incomplete":
        del files["tool-verify.stderr"]
    elif variant == "source-mismatch":
        old_files[source.PRODUCER_FILES[0]] += b"changed historical source"
    elif variant == "failure-code":
        report["failure"]["code"] = "different_failure"
    elif variant == "status":
        run["status"] = "in_progress"
    elif variant == "attempt":
        run["run_attempt"] = 2
    elif variant == "ref":
        run["head_branch"] = "foreign"
    elif variant == "wrong-job":
        job["id"] += 1
    elif variant == "successful":
        job["conclusion"] = run["conclusion"] = "success"
    files["tool.json"] = source.canonical_data(report)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    raw_archive = stream.getvalue()
    monkeypatch.setattr(
        source,
        "TOOL_PREFETCH_ARCHIVE",
        {"bytes": len(raw_archive), "sha256": source.sha(raw_archive)},
    )
    artifact = {
        "id": 11713828762,
        "expired": variant == "expired",
        "size_in_bytes": len(raw_archive),
        "expires_at": "2099-01-01T00:00:00Z",
        "name": "prometheus-oras-38170923494-1",
        "digest": "sha256:" + source.sha(raw_archive),
        "workflow_run": {
            "id": run["id"],
            "repository_id": 1043311030,
            "head_repository_id": 1043311030,
            "head_sha": head,
        },
    }
    current = dict(
        run,
        id=999,
        head_sha="a" * 40,
        status="in_progress",
        conclusion=None,
        run_attempt=1,
        head_branch=ref[11:],
    )
    if variant == "digest":
        artifact["digest"] = "sha256:" + "d" * 64

    class API:
        evidence = tmp_path

        def json(self, endpoint: str) -> dict[str, Any]:
            if "/actions/artifacts/" in endpoint:
                return copy.deepcopy(artifact)
            if endpoint.endswith("/actions/workflows/build.yml"):
                return copy.deepcopy(workflow)
            if endpoint.endswith("/actions/runs/999"):
                return copy.deepcopy(current)
            if endpoint.endswith("/actions/runs/38170923494"):
                return copy.deepcopy(run)
            if "workflows/build.yml/runs" in endpoint:
                return {"total_count": 3 if variant == "second-failed-job" else 2}
            return {"total_count": 2 if variant == "extra-job" else 1}

        def pages(self, endpoint: str, field: str, count: int) -> list[dict[str, Any]]:
            if variant == "history-unknown":
                raise source.QualificationError("synthetic_complete_history_unavailable")
            if "workflows/build.yml/runs" in endpoint:
                rows = [copy.deepcopy(current), copy.deepcopy(run)]
                if variant == "second-failed-job":
                    rows.append(dict(run, id=38170923495))
                assert len(rows) == count
                return rows
            jobs = [copy.deepcopy(job)]
            if variant == "extra-job" and "filter=all" in endpoint:
                jobs.append(dict(job, id=114563178712))
            assert len(jobs) == count
            return jobs

        def raw(self, endpoint: str, *, maximum: int) -> bytes:
            assert endpoint.endswith("/11713828762/zip")
            return raw_archive

        def source_files(self, revision: str, paths: tuple[str, ...]) -> dict[str, bytes]:
            assert revision == head and set(paths) == set(old_files)
            return old_files

    return API()


@pytest.mark.parametrize(
    "variant,diagnostic",
    (
        ("valid", None),
        ("false-counter", "tool_prefetch_failed_before_compile"),
        ("missing-counter", "tool_prefetch_failed_before_compile"),
        ("compiled", "tool_prefetch_failed_before_compile"),
        ("extra-command", "tool_prefetch_exact_native_prefix"),
        ("argv", "tool_prefetch_exact_native_prefix"),
        ("native-exit", "tool_prefetch_exact_native_prefix"),
        ("output-mismatch", "tool_prefetch_native_output_binding"),
        ("extra-marker", "tool_prefetch_complete_failed_inventory"),
        ("binary", "tool_prefetch_complete_failed_inventory"),
        ("incomplete", "tool_prefetch_complete_failed_inventory"),
        ("source-mismatch", "declared_data_value"),
        ("failure-code", "declared_data_value"),
        ("status", "artifact_completed_workflow"),
        ("attempt", "artifact_completed_workflow"),
        ("ref", "tool_prefetch_authenticated_predecessor"),
        ("wrong-job", "tool_prefetch_complete_singleton_history"),
        ("successful", "tool_prefetch_complete_singleton_history"),
        ("extra-job", "tool_prefetch_complete_singleton_history"),
        ("history-unknown", "synthetic_complete_history_unavailable"),
        ("second-failed-job", "tool_prefetch_complete_singleton_history"),
        ("expired", "artifact_identity_expiry_size"),
        ("digest", "artifact_native_download_digest"),
    ),
)
def test_tool_prefetch_recovery_is_one_closed_failed_precompile_predecessor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str, diagnostic: str | None
) -> None:
    api = _tool_prefetch_recovery_fixture(tmp_path, monkeypatch, variant)
    if diagnostic is None:
        admitted = source.manual_hosted_admission(
            api, "tool", prefetch_predecessor=source.TOOL_PREFETCH_PREDECESSOR
        )
        assert admitted["budget"] == 1 and len(admitted["actual_prior_invocations"]) == 1
        assert admitted["actual_prior_invocations"][0]["conclusion"] == "failure"
        assert (
            "historical post-lock bytes unknown"
            in admitted["actual_prior_invocations"][0]["precompile_disposition"]
        )
    else:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.manual_hosted_admission(
                api, "tool", prefetch_predecessor=source.TOOL_PREFETCH_PREDECESSOR
            )


def _two_tool_prefetch_recovery_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> Any:
    """The same closed recovery family with two independent synthetic archives."""
    locks = {"go.mod": b"synthetic original mod", "go.sum": b"synthetic original sum"}
    monkeypatch.setattr(source, "ORAS_LOCKS", {key: source.sha(raw) for key, raw in locks.items()})
    monkeypatch.setattr(source, "ORAS_SOURCE", replace(source.ORAS_SOURCE, files=1))
    first = _tool_prefetch_recovery_fixture(tmp_path, monkeypatch, "valid")
    raw_first = first.raw("/11713828762/zip", maximum=10**7)
    old_head = "5de54811121079eadbd3f5d8dbbb8720f712530a"
    head = "15097adaa871a900370f6c57a512fe862dddb041"
    ref = "refs/heads/codex/dependency-native-runtime-remediation"
    old_files = first.source_files(old_head, (*source.PRODUCER_FILES, source.MANIFEST_PATH))
    historical = {key: raw + b" second producer" for key, raw in old_files.items()}
    historical[source.MANIFEST_PATH] = old_files[source.MANIFEST_PATH]
    inputs = source.one_object(historical[source.MANIFEST_PATH])["inputs"]
    projection = {
        "inputs": inputs,
        "raw_producer": {
            name: {"bytes": len(historical[name]), "sha256": source.sha(historical[name])}
            for name in source.PRODUCER_FILES
        },
    }
    digest = "sha256:" + source.sha(source.canonical_data(projection))
    monkeypatch.setattr(source, "TOOL_PREFETCH_SECOND_INPUT_DIGEST", digest)
    with zipfile.ZipFile(io.BytesIO(raw_first)) as archive:
        first_report = source.one_object(archive.read("tool.json"))
        members = archive.read("oras-source-members.json")
        files = {
            name: archive.read(name) for name in archive.namelist() if name.startswith("GitHub-")
        }
    for number in range(36, 50):
        for suffix in ("json", "stdout", "stderr"):
            files[f"GitHub-{number}.{suffix}"] = files[f"GitHub-35.{suffix}"]
    files.update(
        {
            "go-members.json": members,
            "oras-source-members.json": members,
            "tool-prefetch-predecessor.zip": raw_first,
        }
    )
    state = {
        "locks": {
            name: {"bytes": len(raw), "sha256": source.sha(raw), "mode": 0o644}
            for name, raw in locks.items()
        },
        "source_inventory": [
            {"path": "synthetic.go", "mode": 0o644, "size": 1, "sha256": "b" * 64}
        ],
    }
    files["tool-prefetch.json"] = source.canonical_data(
        {"before": state, "after": state, "failure": None, "snapshot_errors": []}
    )
    for name, raw in locks.items():
        for phase in ("before", "after"):
            files[f"tool-prefetch-{phase}-{name}"] = raw
    work = Path("/home/runner/work/_temp/prometheus-oras-38192419687-1")
    online = source.clean_environment(
        work / "tool-home",
        work / "tool-tmp",
        work / "tool-cache",
        work / "tool-modules",
        offline=False,
    )
    host_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "LANG": "C.UTF-8",
        "DOCKER_CONFIG": str(work / "docker-config"),
    }
    offline = source.clean_environment(
        source.GUEST_TMP,
        source.GUEST_TMP,
        source.GUEST_TMP / "gocache",
        Path("/modules"),
        offline=True,
    )
    docker = ["/usr/bin/docker", "--config", str(work / "docker-config")]
    records: list[dict[str, Any]] = []

    def native(
        name: str,
        argv: list[str],
        stdout: bytes = b"",
        stderr: bytes = b"",
        status: int = 0,
        *,
        online_go: bool = False,
    ) -> None:
        row: dict[str, Any] = {
            "argv": argv,
            "cwd": str(work / "source" if online_go else work),
            "environment": online if online_go else host_env,
            "exit": status,
            "failure": None,
        }
        for suffix, raw in (("stdout", stdout), ("stderr", stderr)):
            member = name + "." + suffix
            files[member] = raw
            row[suffix], row[suffix + "_sha256"] = str(work / "evidence" / member), source.sha(raw)
        records.append(row)

    native(
        "tool-version",
        [str(work / "go/bin/go"), "version"],
        source.GO_VERSION.encode(),
        online_go=True,
    )
    download = b'{"Path":"example.invalid/synthetic","Version":"v1.0.0"}'
    native(
        "tool-download",
        [str(work / "go/bin/go"), "mod", "download", "-json"],
        download,
        online_go=True,
    )
    native(
        "tool-verify",
        [str(work / "go/bin/go"), "mod", "verify"],
        b"all modules verified\n",
        online_go=True,
    )
    native("vendor-pull", [*docker, "pull", "--platform", "linux/amd64", source.HISTORICAL_BASE])
    containers = []
    for index, (kind, command) in enumerate(
        (
            ("version", ["version"]),
            ("verify", ["mod", "verify"]),
            ("modules", ["list", "-mod=readonly", "-m", "-json", "all"]),
        )
    ):
        name, owner = "synthetic-owned-" + kind, "synthetic-owner-" + kind
        image = _native_fixed_base_image(current=False)
        if variant == "base-relation" and index == 0:
            image["RootFS"]["Layers"] = []
        native(
            f"tool-{kind}-base",
            [*docker, "image", "inspect", source.HISTORICAL_BASE],
            source.canonical_data(image),
        )
        # Historical argv is opaque data; no current-host directory constructor is invoked.
        create = [
            *docker,
            "create",
            "--name",
            name,
            "--label",
            source.LABEL + "=" + owner,
            source.HISTORICAL_BASE_CONFIG,
            *command,
        ]
        identifier = source.sha(name.encode())
        create_output = identifier.encode()
        if index == 0 and variant in ("create-short-ID", "create-empty-ID"):
            create_output = name.encode() if variant == "create-short-ID" else b""
        native(
            f"tool-{kind}-create",
            create,
            create_output,
        )
        environment = dict(value.split("=", 1) for value in image["Config"]["Env"])
        environment.update(offline)
        container = {
            "Id": "e" * 64 if variant == "container-ID" and index == 0 else identifier,
            "Name": "/" + name,
            "Image": source.HISTORICAL_BASE_CONFIG,
            "Config": {
                "Image": source.HISTORICAL_BASE_CONFIG,
                "Labels": {source.LABEL: owner},
                "User": "65532:65532",
                "WorkingDir": "/src",
                "Entrypoint": ["/usr/local/go/bin/go"],
                "Cmd": command,
                "Env": [key + "=" + value for key, value in environment.items()],
            },
            "HostConfig": {
                "NetworkMode": "none",
                "ReadonlyRootfs": True,
                "Privileged": False,
                "NanoCpus": 2000000000,
                "Memory": 4294967296,
                "PidsLimit": 128,
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges"],
                "Tmpfs": {str(source.GUEST_TMP): source.GUEST_TMPFS},
            },
            "Mounts": [
                {"Type": "bind", "RW": False, "Destination": guest, "Source": str(work / local)}
                for guest, local in (
                    ("/src", "source"),
                    ("/usr/local/go", "go"),
                    ("/modules", "tool-modules"),
                )
            ],
            "State": {"Running": False, "ExitCode": 1 if index == 2 else 0, "OOMKilled": False},
        }
        native(
            f"tool-{kind}-before", [*docker, "inspect", name], source.canonical_data([container])
        )
        stdout = (
            source.GO_VERSION.encode()
            if kind == "version"
            else b"all modules verified\n" if kind == "verify" else b""
        )
        native(
            f"tool-{kind}-native",
            [*docker, "start", "--attach", name],
            stdout,
            b"synthetic module lookup disabled by GOPROXY=off\n" if kind == "modules" else b"",
            1 if kind == "modules" else 0,
        )
        if kind != "modules":
            native(
                f"tool-{kind}-terminal",
                [*docker, "inspect", name],
                source.canonical_data([container]),
            )
        containers.append((name, container))
    for name, container in containers:
        inventory = [*docker, "ps", "--all", "--format", "{{.Names}}"]
        native(name + "-cleanup-inventory", inventory, name.encode())
        native(
            name + "-cleanup-inspect",
            [*docker, "inspect", name],
            source.canonical_data([container]),
        )
        native(name + "-cleanup-remove", [*docker, "rm", "--force", name], name.encode())
        native(name + "-cleanup-absence", inventory)
    assert len(records) == 30 and records[17]["exit"] == 1
    monkeypatch.setattr(
        source, "TOOL_PREFETCH_SECOND_NATIVE_DIGEST", source.sha(source.canonical_data(records))
    )
    monkeypatch.setattr(
        source,
        "TOOL_PREFETCH_SECOND_STDERR_DIGEST",
        source.sha(files["tool-modules-native.stderr"]),
    )
    prior = {
        "run_id": 38170923494,
        "job_id": 114563178711,
        "status": "completed",
        "conclusion": "failure",
        "precompile_disposition": "selected_known_prefetch_failure; no qualified output; historical post-lock bytes unknown",
    }
    report = dict(
        first_report,
        admission={
            "run_id": 38192419687,
            "head": head,
            "ref": ref,
            "workflow_id": 199904435,
            "job": "prometheus-oras-qualification",
            "actual_prior_invocations": [prior],
            "budget": 1,
        },
        input_projection=projection,
        input_digest=digest,
        failure={"class": "QualificationError", "code": "native_failed"},
        native_commands=records,
        cleanup=[{"name": name, "native_absent": True} for name, _ in containers],
        public_modules={"files": 1, "download_stdout_sha256": source.sha(download)},
    )
    if variant == "false-counter":
        report["tool_compile_invocations"] = False
    elif variant == "compiled":
        report["tool_compile_invocations"] = 1
    elif variant == "extra-command":
        records.append(copy.deepcopy(records[0]))
    elif variant == "native-exit":
        records[17]["exit"] = 0
    elif variant == "argv":
        records[1]["argv"].append("all")
    elif variant == "output-mismatch":
        files["tool-modules-native.stderr"] += b"changed"
    elif variant == "extra-marker":
        files["invocation-start.json"] = b"{}"
    elif variant == "binary":
        files["oras"] = b"never executed"
    elif variant == "incomplete":
        del files["tool-modules-native.stderr"]
    elif variant == "source-mismatch":
        historical[source.PRODUCER_FILES[0]] += b"changed"
    elif variant == "lock":
        files["tool-prefetch-after-go.sum"] += b"changed"
    elif variant == "cleanup":
        report["cleanup"][2]["native_absent"] = False
    elif variant == "failure-code":
        report["failure"]["code"] = "another_failure"
    files["tool.json"] = source.canonical_data(report)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    raw_archive = stream.getvalue()
    monkeypatch.setattr(
        source,
        "TOOL_PREFETCH_SECOND_ARCHIVE",
        {"bytes": len(raw_archive), "sha256": source.sha(raw_archive)},
    )
    first_run = first.json("/actions/runs/38170923494")
    run = dict(first_run, id=38192419687, head_sha=head)
    job = {
        "id": 114627819440,
        "name": "prometheus-oras-qualification",
        "run_id": run["id"],
        "head_sha": head,
        "status": "completed",
        "conclusion": "failure",
    }
    artifact = {
        "id": 11722041486,
        "expired": False,
        "size_in_bytes": len(raw_archive),
        "expires_at": "2099-01-01T00:00:00Z",
        "name": "prometheus-oras-38192419687-1",
        "digest": "sha256:" + source.sha(raw_archive),
        "workflow_run": {
            "id": run["id"],
            "repository_id": 1043311030,
            "head_repository_id": 1043311030,
            "head_sha": head,
        },
    }
    if variant == "attempt":
        run["run_attempt"] = 2
    if variant == "status":
        run["status"] = "in_progress"
    if variant == "job2-failure":
        job["conclusion"] = "success"

    class API:
        evidence = tmp_path

        def json(self, endpoint: str) -> dict[str, Any]:
            if endpoint.endswith("/actions/artifacts/11722041486"):
                return copy.deepcopy(artifact)
            if endpoint.endswith("/actions/runs/38192419687"):
                return copy.deepcopy(run)
            if "workflows/build.yml/runs" in endpoint:
                return {"total_count": 3}
            return first.json(endpoint)

        def pages(self, endpoint: str, field: str, count: int) -> list[dict[str, Any]]:
            if variant == "history-unknown":
                raise source.QualificationError("synthetic_complete_history_unavailable")
            if "workflows/build.yml/runs" in endpoint:
                return [
                    first.json("/actions/runs/999"),
                    copy.deepcopy(run),
                    copy.deepcopy(first_run),
                ]
            if "/runs/38192419687/" in endpoint:
                return [copy.deepcopy(job)]
            return first.pages(endpoint, field, count)

        def raw(self, endpoint: str, *, maximum: int) -> bytes:
            return (
                raw_archive
                if endpoint.endswith("/11722041486/zip")
                else first.raw(endpoint, maximum=maximum)
            )

        def source_files(self, revision: str, paths: tuple[str, ...]) -> dict[str, bytes]:
            return historical if revision == head else first.source_files(revision, paths)

    return API()


@pytest.mark.parametrize(
    "variant,diagnostic",
    (
        ("valid", None),
        ("false-counter", "tool_prefetch_second_before_compile"),
        ("create-short-ID", "tool_prefetch_second_create_ID"),
        ("create-empty-ID", "tool_prefetch_second_create_ID"),
        ("container-ID", "container_full_identity"),
        ("base-relation", "declared_data_length"),
        ("compiled", "tool_prefetch_second_before_compile"),
        ("extra-command", "tool_prefetch_second_native_records"),
        ("native-exit", "tool_prefetch_second_native_records"),
        ("argv", "tool_prefetch_second_native_records"),
        ("output-mismatch", "tool_prefetch_second_native_output_binding"),
        ("extra-marker", "tool_prefetch_second_complete_inventory"),
        ("binary", "tool_prefetch_second_complete_inventory"),
        ("incomplete", "tool_prefetch_second_native_output_binding"),
        ("source-mismatch", "declared_data_value"),
        ("lock", "tool_prefetch_second_original_lock_bytes"),
        ("cleanup", "declared_data_value"),
        ("failure-code", "declared_data_value"),
        ("attempt", "artifact_completed_workflow"),
        ("status", "artifact_completed_workflow"),
        ("job2-failure", "tool_prefetch_complete_two_history"),
        ("history-unknown", "synthetic_complete_history_unavailable"),
    ),
)
def test_tool_prefetch_recovery_requires_both_complete_failed_histories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str, diagnostic: str | None
) -> None:
    api = _two_tool_prefetch_recovery_fixture(tmp_path, monkeypatch, variant)
    if diagnostic is not None:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.manual_hosted_admission(
                api, "tool", prefetch_predecessor=source.TOOL_PREFETCH_TWO_PREDECESSORS
            )
        return
    result = source.manual_hosted_admission(
        api, "tool", prefetch_predecessor=source.TOOL_PREFETCH_TWO_PREDECESSORS
    )
    assert result["budget"] == 1 and len(result["actual_prior_invocations"]) == 2
    assert all(row["conclusion"] == "failure" for row in result["actual_prior_invocations"])
    assert "FAILED/SPENT" in result["actual_prior_invocations"][1]["precompile_disposition"]
    for selector in (None, source.TOOL_PREFETCH_PREDECESSOR):
        with pytest.raises(
            source.QualificationError,
            match="^"
            + (
                "nonrenewable_hosted_invocation_budget_spent_or_unknown"
                if selector is None
                else "tool_prefetch_complete_singleton_history"
            )
            + "$",
        ):
            source.manual_hosted_admission(api, "tool", prefetch_predecessor=selector)
    with pytest.raises(source.QualificationError, match="^artifact_completed_workflow$"):
        source.authenticated_artifact(
            api,
            11722041486,
            tmp_path / "never-success.zip",
            expected_run=38192419687,
            expected_job="prometheus-oras-qualification",
            expected_head="15097adaa871a900370f6c57a512fe862dddb041",
        )


def _three_tool_failure_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str) -> Any:
    """Complete synthetic historical data; no executable, API or native operation."""
    previous = _two_tool_prefetch_recovery_fixture(tmp_path, monkeypatch, "valid")
    raw_second = previous.raw("/11722041486/zip", maximum=10**7)
    with zipfile.ZipFile(io.BytesIO(raw_second)) as archive:
        old = {name: archive.read(name) for name in archive.namelist()}
    second = source.one_object(old["tool.json"])
    head = "f632572057453d57975a397a5b2db64894204be0"
    historical = {
        key: raw + b" third source"
        for key, raw in previous.source_files(
            "15097adaa871a900370f6c57a512fe862dddb041",
            (*source.PRODUCER_FILES, source.MANIFEST_PATH),
        ).items()
    }
    historical[source.MANIFEST_PATH] = source.canonical_data(
        {"schema": source.IMAGE_SCHEMA, "inputs": second["input_projection"]["inputs"]}
    )
    projection = {
        "inputs": second["input_projection"]["inputs"],
        "raw_producer": {
            key: {"bytes": len(historical[key]), "sha256": source.sha(historical[key])}
            for key in source.PRODUCER_FILES
        },
    }
    digest = "sha256:" + source.sha(source.canonical_data(projection))
    monkeypatch.setattr(source, "TOOL_THIRD_INPUT_DIGEST", digest)
    members = json.loads(old["oras-source-members.json"])
    files = {
        "oras-source-members.json": old["oras-source-members.json"],
        "go-members.json": source.canonical_data(
            [{"path": "bin/go", "git_mode": "100755", "size": 1, "sha256": "c" * 64}]
        ),
        "tool-prefetch-predecessor.zip": old["tool-prefetch-predecessor.zip"],
        "tool-prefetch-second-predecessor.zip": raw_second,
    }
    for number in range(1, 64):
        for suffix in ("json", "stdout", "stderr"):
            files[f"GitHub-{number}.{suffix}"] = old[f"GitHub-{min(number, 49)}.{suffix}"]
    before = {
        "locks": source.one_object(old["tool-prefetch.json"])["before"]["locks"],
        "source_inventory": [
            {"path": row["path"], "size": row["size"], "sha256": row["sha256"], "mode": 0o644}
            for row in members
        ],
        "Go_binary_sha256": "c" * 64,
    }
    prefix = (
        ("version", ["version"]),
        ("download", ["mod", "download", "-json"]),
        ("verify", ["mod", "verify"]),
        ("selected", ["list", "-mod=readonly", "-m", "-json", "all"]),
        ("graph", ["mod", "graph"]),
    )
    phases = (
        "before",
        "after",
        *(name + "-" + phase for name, _ in prefix for phase in ("before", "after")),
    )
    prefetch = {phase: copy.deepcopy(before) for phase in phases}
    prefetch.update(failure=None, snapshot_errors=[], commands=[])
    for phase in phases:
        for lock in source.ORAS_LOCKS:
            files["tool-prefetch-" + phase + "-" + lock] = old["tool-prefetch-before-" + lock]
    work = Path("/home/runner/work/_temp/prometheus-oras-38239428418-1")
    online = source.clean_environment(
        work / "tool-home",
        work / "tool-tmp",
        work / "tool-cache",
        work / "tool-modules",
        offline=False,
    )
    host = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "LANG": "C.UTF-8",
        "DOCKER_CONFIG": str(work / "docker-config"),
    }
    docker = ["/usr/bin/docker", "--config", str(work / "docker-config")]
    records: list[dict[str, Any]] = []

    def native(name: str, argv: list[str], raw: bytes = b"", *, go: bool = False) -> None:
        row: dict[str, Any] = {
            "argv": argv,
            "cwd": str(work / "source" if go else work),
            "environment": online if go else host,
            "exit": 0,
            "failure": None,
        }
        for suffix, value in (("stdout", raw), ("stderr", b"")):
            key = name + "." + suffix
            files[key] = value
            row[suffix], row[suffix + "_sha256"] = str(work / "evidence" / key), source.sha(value)
        records.append(row)

    selected = source.canonical_data({"Path": "oras.land/oras", "Main": True})
    package = source.canonical_data(
        {"ImportPath": source.ORAS_COMMAND, "Name": "main", "Imports": []}
    )
    graph = b"oras.land/oras example.invalid/synthetic@v1.0.0\n"
    online_outputs = (
        source.GO_VERSION.encode(),
        old["tool-download.stdout"],
        b"all modules verified\n",
        selected,
        graph,
    )
    for (name, command), raw in zip(prefix, online_outputs):
        native("tool-" + name, [str(work / "go/bin/go"), *command], raw, go=True)
        prefetch["commands"].append(
            {"name": name, "argv": command, "stdout_sha256": source.sha(raw)}
        )
    files["tool-prefetch.json"] = source.canonical_data(prefetch)
    cache = [{"path": "cache.mod", "mode": 0o644, "size": 1, "sha256": "d" * 64}]
    frozen = [dict(cache[0], mode=0o444)]
    files["tool-prefetch-cache-before-freeze.json"] = source.canonical_data(cache)
    files["tool-prefetch-cache-frozen.json"] = source.canonical_data(frozen)
    native("tool-base-pull", [*docker, "pull", "--platform", "linux/amd64", source.HISTORICAL_BASE])
    commands = (
        ("version", ["version"], source.GO_VERSION.encode()),
        ("verify", ["mod", "verify"], b"all modules verified\n"),
        ("modules", ["list", "-mod=readonly", "-m", "-json", "all"], selected),
        ("graph", ["mod", "graph"], graph),
        ("packages", ["list", "-mod=readonly", "-deps", "-json", source.ORAS_COMMAND], package),
        (
            "compile",
            [
                "build",
                "-mod=readonly",
                "-trimpath",
                "-buildvcs=false",
                "-p=1",
                "-ldflags=" + source.ORAS_METADATA,
                "-o",
                "/output/oras",
                source.ORAS_COMMAND,
            ],
            b"",
        ),
        ("buildinfo", ["version", "-m", "/output/oras"], b"go1.27.2 synthetic buildinfo"),
    )
    containers = []
    for number, (name, command, raw) in enumerate(commands):
        container, owner = "synthetic-third-" + name, "synthetic-owner-" + name
        image = _native_fixed_base_image(current=False)
        if fault == "base-relation" and number == 0:
            image["RootFS"]["Layers"] = []
        native(
            "tool-" + name + "-base",
            [*docker, "image", "inspect", source.HISTORICAL_BASE],
            source.canonical_data(image),
        )
        create = [
            *docker,
            "create",
            "--name",
            container,
            "--label",
            source.LABEL + "=" + owner,
            source.HISTORICAL_BASE_CONFIG,
            *command,
        ]
        identifier = source.sha(container.encode())
        create_output = identifier.encode()
        if number == 0 and fault in ("create-short-ID", "create-empty-ID"):
            create_output = container.encode() if fault == "create-short-ID" else b""
        native(
            "tool-" + name + "-create",
            create,
            create_output,
        )
        environment = dict(value.split("=", 1) for value in image["Config"]["Env"])
        environment.update(
            source.clean_environment(
                source.GUEST_TMP,
                source.GUEST_TMP,
                source.GUEST_TMP / "gocache",
                Path("/modules"),
                offline=True,
            )
        )
        mounts = [
            {"Type": "bind", "RW": False, "Destination": guest, "Source": str(work / local)}
            for guest, local in (
                ("/src", "source"),
                ("/usr/local/go", "go"),
                ("/modules", "tool-modules"),
            )
        ]
        if number >= 5:
            environment.update(TMPDIR="/output/tmp", GOCACHE="/output/cache")
            mounts.append(
                {
                    "Type": "bind",
                    "RW": True,
                    "Destination": "/output",
                    "Source": str(work / "compiled"),
                }
            )
        value = {
            "Id": "e" * 64 if fault == "container-ID" and number == 0 else identifier,
            "Name": "/" + container,
            "Image": source.HISTORICAL_BASE_CONFIG,
            "Config": {
                "Image": source.HISTORICAL_BASE_CONFIG,
                "Labels": {source.LABEL: owner},
                "User": "65532:65532",
                "WorkingDir": "/src",
                "Entrypoint": ["/usr/local/go/bin/go"],
                "Cmd": command,
                "Env": [key + "=" + val for key, val in environment.items()],
            },
            "HostConfig": {
                "NetworkMode": "none",
                "ReadonlyRootfs": True,
                "Privileged": False,
                "NanoCpus": 2000000000,
                "Memory": 4294967296,
                "PidsLimit": 128,
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges"],
                "Tmpfs": {str(source.GUEST_TMP): source.GUEST_TMPFS},
            },
            "Mounts": mounts,
            "State": {"Running": False, "ExitCode": 0, "OOMKilled": False},
        }
        native(
            "tool-" + name + "-before",
            [*docker, "inspect", container],
            source.canonical_data([value]),
        )
        native("tool-" + name + "-native", [*docker, "start", "--attach", container], raw)
        native(
            "tool-" + name + "-terminal",
            [*docker, "inspect", container],
            source.canonical_data([value]),
        )
        containers.append((container, value))
    binary = str(work / "compiled/oras")
    native("ORAS-version", [binary, "version"], b"synthetic rebuilt ORAS1.3.4")
    native("ORAS-help", [binary, "cp", "--help"], b"synthetic help")
    native(
        "ORAS-authenticated-base",
        [binary, "cp", "--to-oci-layout", source.HISTORICAL_BASE, str(work / "vendor") + ":base"],
    )
    for container, value in containers:
        argv = [*docker, "ps", "--all", "--format", "{{.Names}}"]
        native(container + "-cleanup-inventory", argv, container.encode())
        native(
            container + "-cleanup-inspect",
            [*docker, "inspect", container],
            source.canonical_data([value]),
        )
        native(
            container + "-cleanup-remove", [*docker, "rm", "--force", container], container.encode()
        )
        native(container + "-cleanup-absence", argv)
    assert len(records) == 72
    monkeypatch.setattr(
        source, "TOOL_THIRD_NATIVE_DIGEST", source.sha(source.canonical_data(records))
    )
    first_prior = copy.deepcopy(second["admission"]["actual_prior_invocations"])
    first_prior.append(
        {
            "run_id": 38192419687,
            "job_id": 114627819440,
            "status": "completed",
            "conclusion": "failure",
            "precompile_disposition": "selected_known_offline_metadata_failure; FAILED/SPENT; no compiler or qualified output",
        }
    )
    start = {
        key: copy.deepcopy(second[key])
        for key in ("identity", "source_revision", "source_tree", "original_locks")
    }
    start.update(
        admission={
            "run_id": 38239428418,
            "head": head,
            "ref": "refs/heads/codex/dependency-native-runtime-remediation",
            "workflow_id": 199904435,
            "job": "prometheus-oras-qualification",
            "actual_prior_invocations": first_prior,
            "budget": 1,
        },
        input_projection=projection,
        input_digest=digest,
        tool_compile_invocations=1,
        Prometheus_compile_invocations=0,
        failure=None,
        public_modules={
            "files": 1,
            "inventory_sha256": source.sha(source.canonical_data(frozen)),
            "download_stdout_sha256": source.sha(old["tool-download.stdout"]),
        },
        full_modules={"oras.land/oras": {"Path": "oras.land/oras", "Main": True}},
        command_graph={
            "command": source.ORAS_COMMAND,
            "packages": 1,
            "package_paths": [source.ORAS_COMMAND],
            "SSH_OpenPGP_paths": [],
            "scope": "exact Linux amd64 CGO0 command graph",
        },
    )
    final = copy.deepcopy(start)
    final.update(
        failure={"class": "QualificationError", "code": "layout_regular_leaf"},
        binary=source.TOOL_THIRD_BINARY_OBSERVATION,
        cleanup=[{"name": name, "native_absent": True} for name, _ in containers],
        native_commands=records,
    )
    if fault == "false-counter":
        final["tool_compile_invocations"] = False
    elif fault == "zero-counter":
        final["tool_compile_invocations"] = 0
    elif fault == "start-zero":
        start["tool_compile_invocations"] = 0
    elif fault == "historical-budget":
        final["admission"]["budget"] = 2
    elif fault == "phase":
        final["failure"]["code"] = "native_failed"
    elif fault == "native-status":
        records[34]["exit"] = False
    elif fault == "native-argv":
        records[34]["argv"].append("unexpected")
    elif fault == "native-output":
        files["tool-compile-native.stdout"] = b"changed"
    elif fault == "missing-output":
        del files["tool-compile-native.stderr"]
    elif fault == "cleanup":
        final["cleanup"][0]["native_absent"] = False
    elif fault == "source":
        historical[source.PRODUCER_FILES[0]] += b"changed"
    elif fault == "extra-binary":
        files["oras"] = b"not a retained executable"
    elif fault == "Go":
        changed = copy.deepcopy(prefetch)
        for phase in phases:
            changed[phase]["Go_binary_sha256"] = "e" * 64
        files["tool-prefetch.json"] = source.canonical_data(changed)
    files["tool.json"] = source.canonical_data(final)
    if fault != "missing-start":
        files["invocation-start.json"] = source.canonical_data(start)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    raw_archive = stream.getvalue()
    monkeypatch.setattr(
        source, "TOOL_THIRD_ARCHIVE", {"bytes": len(raw_archive), "sha256": source.sha(raw_archive)}
    )
    run = dict(previous.json("/actions/runs/38192419687"), id=38239428418, head_sha=head)
    job = {
        "id": 114778090287,
        "name": "prometheus-oras-qualification",
        "run_id": run["id"],
        "head_sha": head,
        "status": "completed",
        "conclusion": "failure",
    }
    artifact = {
        "id": 11742856046,
        "expired": False,
        "size_in_bytes": len(raw_archive),
        "expires_at": "2099-01-01T00:00:00Z",
        "name": "prometheus-oras-38239428418-1",
        "digest": "sha256:" + source.sha(raw_archive),
        "workflow_run": {
            "id": run["id"],
            "repository_id": 1043311030,
            "head_repository_id": 1043311030,
            "head_sha": head,
        },
    }
    if fault == "attempt":
        run["run_attempt"] = 2
    if fault == "pending":
        job["status"] = "in_progress"

    class API:
        evidence = tmp_path

        def json(self, endpoint: str) -> dict[str, Any]:
            if endpoint.endswith("/actions/artifacts/11742856046"):
                return copy.deepcopy(artifact)
            if endpoint.endswith("/actions/runs/38239428418"):
                return copy.deepcopy(run)
            if "workflows/build.yml/runs" in endpoint:
                return {"total_count": 5 if fault == "fourth-history" else 4}
            return previous.json(endpoint)

        def pages(self, endpoint: str, field: str, count: int) -> list[dict[str, Any]]:
            if fault == "history-unknown":
                raise source.QualificationError("synthetic_complete_history_unavailable")
            if "workflows/build.yml/runs" in endpoint:
                rows = [
                    previous.json("/actions/runs/999"),
                    copy.deepcopy(run),
                    previous.json("/actions/runs/38192419687"),
                    previous.json("/actions/runs/38170923494"),
                ]
                if fault == "fourth-history":
                    rows.append(dict(run, id=38239428419))
                return rows
            if "/runs/38239428418/" in endpoint or "/runs/38239428419/" in endpoint:
                return [copy.deepcopy(job)]
            return previous.pages(endpoint, field, count)

        def raw(self, endpoint: str, *, maximum: int) -> bytes:
            return (
                raw_archive
                if endpoint.endswith("/11742856046/zip")
                else previous.raw(endpoint, maximum=maximum)
            )

        def source_files(self, revision: str, paths: tuple[str, ...]) -> dict[str, bytes]:
            return historical if revision == head else previous.source_files(revision, paths)

    return API()


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("valid", None),
        ("false-counter", "tool_third_actual_compiler_consumed"),
        ("create-short-ID", "tool_third_create_ID"),
        ("create-empty-ID", "tool_third_create_ID"),
        ("container-ID", "container_full_identity"),
        ("base-relation", "declared_data_length"),
        ("zero-counter", "tool_third_actual_compiler_consumed"),
        ("start-zero", "tool_third_actual_compiler_consumed"),
        ("historical-budget", "declared_data_value"),
        ("phase", "declared_data_value"),
        ("missing-start", "tool_third_report_keys"),
        ("native-status", "tool_third_native_status"),
        ("native-argv", "tool_third_native_records"),
        ("native-output", "tool_third_native_output_binding"),
        ("missing-output", "tool_third_native_output_binding"),
        ("cleanup", "declared_data_value"),
        ("source", "declared_data_value"),
        ("extra-binary", "tool_third_complete_failed_inventory"),
        ("Go", "tool_third_qualified_Go_identity"),
        ("attempt", "artifact_completed_workflow"),
        ("pending", "tool_complete_three_history"),
        ("fourth-history", "tool_complete_three_history"),
        ("history-unknown", "synthetic_complete_history_unavailable"),
    ],
)
def test_exact_third_postcompile_history_preserves_consumption_and_failed_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str | None
) -> None:
    api = _three_tool_failure_fixture(tmp_path, monkeypatch, fault)
    if diagnostic:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.manual_hosted_admission(
                api, "tool", prefetch_predecessor=source.TOOL_THREE_PREDECESSORS
            )
        return
    result = source.manual_hosted_admission(
        api, "tool", prefetch_predecessor=source.TOOL_THREE_PREDECESSORS
    )
    assert result["budget"] == 2 and len(result["actual_prior_invocations"]) == 3
    assert all(row["conclusion"] == "failure" for row in result["actual_prior_invocations"])
    assert (
        "actual Tool compiler1" in result["actual_prior_invocations"][2]["postcompile_disposition"]
    )
    for selector, expected in (
        (None, "nonrenewable_hosted_invocation_budget_spent_or_unknown"),
        (source.TOOL_PREFETCH_PREDECESSOR, "tool_prefetch_complete_singleton_history"),
        (source.TOOL_PREFETCH_TWO_PREDECESSORS, "tool_prefetch_complete_two_history"),
    ):
        with pytest.raises(source.QualificationError, match="^" + expected + "$"):
            source.manual_hosted_admission(api, "tool", prefetch_predecessor=selector)
    with pytest.raises(source.QualificationError, match="^artifact_completed_workflow$"):
        source.authenticated_artifact(
            api,
            11742856046,
            tmp_path / "no-qualified.zip",
            expected_run=38239428418,
            expected_job="prometheus-oras-qualification",
            expected_head="f632572057453d57975a397a5b2db64894204be0",
        )
    with pytest.raises(source.QualificationError, match="^artifact_closed_purpose$"):
        source.authenticated_artifact(
            api,
            11742856046,
            tmp_path / "no-precompile.zip",
            expected_run=38239428418,
            expected_job="prometheus-oras-qualification",
            expected_head="f632572057453d57975a397a5b2db64894204be0",
            purpose="tool_prefetch_precompile_failure",
        )
    with pytest.raises(source.QualificationError, match="^tool_prefetch_explicit_predecessor$"):
        source.manual_hosted_admission(
            api, "pair", prefetch_predecessor=source.TOOL_THREE_PREDECESSORS
        )


def test_failed_prefetch_purpose_cannot_enter_success_readers_or_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    api = _tool_prefetch_recovery_fixture(tmp_path, monkeypatch, "valid")
    with pytest.raises(source.QualificationError, match="^artifact_completed_workflow$"):
        source.authenticated_artifact(
            api,
            11713828762,
            tmp_path / "success.zip",
            expected_run=38170923494,
            expected_job="prometheus-oras-qualification",
            expected_head="5de54811121079eadbd3f5d8dbbb8720f712530a",
        )
    assert not (tmp_path / "success.zip").exists()
    with pytest.raises(
        source.QualificationError, match="^nonrenewable_hosted_invocation_budget_spent_or_unknown$"
    ):
        source.manual_hosted_admission(api, "tool")
    with pytest.raises(source.QualificationError, match="^tool_prefetch_explicit_predecessor$"):
        source.manual_hosted_admission(
            api, "pair", prefetch_predecessor=source.TOOL_PREFETCH_PREDECESSOR
        )
    with pytest.raises(source.QualificationError, match="^tool_prefetch_explicit_predecessor$"):
        source.manual_hosted_admission(api, "tool", prefetch_predecessor="38170923494:11713828763")


# These fixed data fixtures exercise admission; they are not native build/publication receipts.
_HISTORICAL_SOURCE_PATHS = (
    "scripts/ci/prometheus_source_image.py",
    ".github/workflows/build.yml",
    "deploy/prometheus/Containerfile",
    "deploy/prometheus/image-manifest.json",
)


@pytest.mark.parametrize(
    "delta,expected",
    [
        ("0000", "unchanged_published"),
        ("0001", "unchanged_published"),
        ("0010", "unchanged_published"),
        ("0011", "unchanged_published"),
        ("0100", "historical_helper_change"),
        ("0101", "source_change_recipe_drift"),
        ("0110", "source_change_recipe_drift"),
        ("0111", "source_change_recipe_drift"),
        ("1000", "manifest_changed"),
        ("1001", "manifest_changed"),
        ("1010", "manifest_changed"),
        ("1011", "manifest_changed"),
        ("1100", "manifest_changed"),
        ("1101", "manifest_changed"),
        ("1110", "manifest_changed"),
        ("1111", "manifest_changed"),
    ],
)
def test_historical_source_change_has_manifest_first_closed_table(
    delta: str, expected: str
) -> None:
    """Independent16-row source-case oracle; no result confers image validity."""
    before = {name: ("original " + name).encode() for name in _HISTORICAL_SOURCE_PATHS}
    after = dict(before)
    order = (_HISTORICAL_SOURCE_PATHS[3], *_HISTORICAL_SOURCE_PATHS[:3])
    for bit, name in zip(delta, order, strict=True):
        if bit == "1":
            after[name] += b" changed"
    if expected == "source_change_recipe_drift":
        with pytest.raises(source.QualificationError, match="^source_change_recipe_drift$"):
            source.classify_source_change(before, after)
    else:
        assert source.classify_source_change(before, after) == expected


@pytest.mark.parametrize("fault", ["missing", "extra", "nonbytes"])
def test_historical_source_classifier_rejects_incomplete_data(fault: str) -> None:
    """Require the complete fixed raw-source universe before source-case selection."""
    before = {name: name.encode() for name in _HISTORICAL_SOURCE_PATHS}
    assert source.classify_source_change(before, dict(before)) == "unchanged_published"
    after: dict[str, Any] = dict(before)
    if fault == "missing":
        after.pop(_HISTORICAL_SOURCE_PATHS[0])
    elif fault == "extra":
        after["unselected.py"] = b"extra"
    else:
        after[_HISTORICAL_SOURCE_PATHS[0]] = True
    with pytest.raises(source.QualificationError, match="^source_change_inventory$"):
        source.classify_source_change(before, after)


@pytest.mark.parametrize(
    "suffix,accepted",
    [
        ("a" * 40 + "..." + "b" * 40, True),
        ("a" * 40 + "%2e%2e%2e" + "b" * 40, False),
        ("a" * 40 + "...refs/heads/main", False),
        ("A" * 40 + "..." + "b" * 40, False),
        ("a" * 39 + "..." + "b" * 40, False),
        ("a" * 40 + "..." + "b" * 40 + "?per_page=250", False),
        ("a" * 40 + "..." + "b" * 40 + "#fragment", False),
        ("a" * 40 + "..." + "b" * 40 + "/extra", False),
        ("../foreign", False),
    ],
)
def test_historical_compare_namespace_is_exclusive(
    monkeypatch: pytest.MonkeyPatch, suffix: str, accepted: bool
) -> None:
    """Reject encoded or alternate comparison forms before native capture."""
    adapter = source.GitHubRead.__new__(source.GitHubRead)
    adapter.gh = "/synthetic/gh"
    calls: list[list[str]] = []

    def capture(argv: list[str], maximum: int) -> bytes:
        calls.append(argv)
        return b"{}"

    monkeypatch.setattr(adapter, "_capture", capture)
    endpoint = "/repos/" + source.GHCR_REPOSITORY + "/compare/" + suffix
    if accepted:
        assert adapter.raw(endpoint) == b"{}"
        assert calls == [
            [adapter.gh, "api", "--hostname", "github.com", "--method", "GET", endpoint]
        ]
    else:
        with pytest.raises(source.QualificationError, match="^GitHub_same_repository_endpoint$"):
            adapter.raw(endpoint)
        assert calls == []


class _HistoricalAPI:
    """Typed native-shaped data only; transport, token auth and image proof are separate."""

    def __init__(self, files: dict[str, dict[str, bytes]], private: Path) -> None:
        """Prepare immutable-shaped synthetic native records without performing transport."""
        self.files = files
        self.private = private
        self.deadline = time.monotonic() + 30
        self.calls: list[str] = []
        run, job = _publication_run(), _publication_job()
        run["head_sha"] = job["head_sha"] = "4" * 40
        self.publication = _PublicationPredecessorAPI([run], {12: [job]})
        self.current: dict[str, Any] = {
            "number": 2493,
            "state": "open",
            "head": {"sha": "5" * 40, "repo": {"id": 1043311030}},
            "base": {"sha": "4" * 40, "ref": "main", "repo": {"id": 1043311030}},
        }
        self.original: dict[str, Any] = {
            "number": 2477,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "3" * 40,
            "head": {
                "sha": "2" * 40,
                "ref": "synthetic-parser-fixture",
                "repo": {"id": 1043311030},
            },
            "base": {"ref": "main", "repo": {"id": 1043311030}},
            "commits": 2,
        }
        self.graph: list[dict[str, Any]] = [
            {"sha": "1" * 40, "parents": [{"sha": "0" * 40}]},
            {"sha": "2" * 40, "parents": [{"sha": "1" * 40}]},
        ]
        self.comparisons = {
            ("3" * 40, "4" * 40): _historical_comparison("3" * 40, "4" * 40),
            ("4" * 40, "5" * 40): _historical_comparison("4" * 40, "5" * 40),
        }

    def json(self, endpoint: str) -> dict[str, Any]:
        """Return one declared synthetic native response, never make an HTTP request."""
        self.calls.append(endpoint)
        prefix = "/repos/" + source.GHCR_REPOSITORY
        if endpoint.startswith(prefix + "/actions/"):
            return cast(dict[str, Any], self.publication.json(endpoint))
        if endpoint == prefix + "/pulls/2493":
            return self.current
        if endpoint == prefix + "/pulls/2477":
            return self.original
        if endpoint == prefix + "/git/ref/heads/main":
            return {"object": {"sha": "5" * 40}}
        if endpoint.startswith(prefix + "/git/commits/"):
            revision = endpoint.rsplit("/", 1)[1]
            return {"sha": revision, "tree": {"sha": "f" * 40}, "parents": []}
        if endpoint.startswith(prefix + "/compare/"):
            pair = tuple(endpoint.rsplit("/", 1)[1].split("..."))
            assert len(pair) == 2
            return self.comparisons[(pair[0], pair[1])]
        raise AssertionError("Unexpected synthetic native endpoint: " + endpoint)

    def pages(self, endpoint: str, key: str | None, count: int) -> list[dict[str, Any]]:
        """Use real bounded publication pages or the declared original PR graph."""
        if key is not None:
            return self.publication.pages(endpoint, key, count)
        assert endpoint == "/repos/" + source.GHCR_REPOSITORY + "/pulls/2477/commits"
        assert key is None and count == 2
        self.calls.append(endpoint)
        return self.graph

    def source_files(self, revision: str, paths: tuple[str, ...]) -> dict[str, bytes]:
        """Return raw data from one declared synthetic source revision."""
        assert set(paths) <= set(_HISTORICAL_SOURCE_PATHS)
        self.calls.append("files:" + revision + ":" + ",".join(paths))
        return {name: self.files[revision][name] for name in paths}


def _historical_comparison(ancestor: str, target: str) -> dict[str, Any]:
    """Finite observed compare shape; no inferred edge through a squash."""
    return {
        "base_commit": {"sha": ancestor},
        "merge_base_commit": {"sha": ancestor},
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
        "total_commits": 1,
        "commits": [{"sha": target, "parents": [{"sha": ancestor}]}],
    }


def _historical_fixture(tmp_path: Path) -> tuple[Path, _HistoricalAPI, dict[str, Any]]:
    """Complete synthetic H/B/S/P data, not an authenticated candidate artifact."""
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    marker = tmp_path / "historical-executed"
    historical_helper = (
        "from pathlib import Path\n"
        + "Path("
        + repr(str(marker))
        + ").write_text('must never execute')\n"
        + "raise AssertionError('historical source is data only')\n"
    ).encode()
    old = {
        _HISTORICAL_SOURCE_PATHS[0]: historical_helper,
        _HISTORICAL_SOURCE_PATHS[1]: b"synthetic producer workflow data\n",
        _HISTORICAL_SOURCE_PATHS[2]: source.finite_recipe(),
    }
    manifest = cast(dict[str, Any], _synthetic_prometheus_manifest())
    manifest["inputs"]["source"]["derived_locks"] = dict(source.XNET060_INCUMBENT_LOCKS)
    manifest["candidate"]["producer"]["raw_producer"] = {
        name: {"bytes": len(raw), "sha256": source.sha(raw)} for name, raw in old.items()
    }
    old[_HISTORICAL_SOURCE_PATHS[3]] = source.canonical_data(manifest)
    current = dict(old)
    current[_HISTORICAL_SOURCE_PATHS[0]] = b"# synthetic proposed consumer data\n"
    root = tmp_path / "material"
    root.mkdir()
    for name, raw in current.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o644)
    source.read_image_manifest(root / source.MANIFEST_PATH)
    files = {revision * 40: dict(old) for revision in ("1", "2", "3", "4")}
    files["5" * 40] = current
    api = _HistoricalAPI(files, tmp_path / "GitHub-private")
    event = {
        "number": 2493,
        "ref": "refs/heads/main",
        "before": "4" * 40,
        "pull_request": copy.deepcopy(api.current),
    }
    return root, api, event


@pytest.mark.parametrize("event_name", ["pull_request", "push"])
def test_historical_event_binds_merged_squash_and_both_native_relations(
    tmp_path: Path, event_name: str
) -> None:
    """Keep original PR ancestry and receiving squash lineage independent for both events."""
    root, api, event = _historical_fixture(tmp_path)
    result = source.event_admission(api, root, event, event_name, "5" * 40)
    expected_mode = (
        "historical_pr_candidate" if event_name == "pull_request" else "historical_main_recovery"
    )
    assert result["mode"] == expected_mode
    assert result["head"] == "5" * 40 and result["historical_source_head"] == "3" * 40
    assert result["publisher_head"] == (None if event_name == "pull_request" else "5" * 40)
    prefix = "/repos/" + source.GHCR_REPOSITORY
    assert prefix + "/pulls/2477/commits" in api.calls
    assert prefix + "/compare/" + "3" * 40 + "..." + "4" * 40 in api.calls
    assert prefix + "/compare/" + "4" * 40 + "..." + "5" * 40 in api.calls
    assert not any("/compare/" + "1" * 40 + "..." + "3" * 40 in item for item in api.calls)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("unmerged", "historical_original_merged_PR"),
        ("open-original", "historical_original_merged_PR"),
        ("missing-squash", "historical_original_merged_PR"),
        ("squash-outside-base", "native_ancestor_relation"),
        ("foreign-original", "candidate_same_repository_PR"),
        ("wrong-ref", "candidate_same_repository_PR"),
        ("missing-producer", "producer_and_final_within_PR"),
        ("disconnected-producer", "producer_ancestor_within_PR"),
        ("selected-manifest", "historical_selected_manifest"),
        ("historical-recipe", "historical_recipe_drift"),
    ],
)
def test_historical_event_rejects_at_its_actual_original_source_boundary(
    tmp_path: Path, fault: str, diagnostic: str
) -> None:
    """Reach each named original-source rejection from a valid historical baseline."""
    root, api, event = _historical_fixture(tmp_path)
    baseline = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert baseline["mode"] == "historical_pr_candidate"
    if fault == "unmerged":
        api.original["merged"] = False
    elif fault == "open-original":
        api.original["state"] = "open"
    elif fault == "missing-squash":
        api.original["merge_commit_sha"] = None
    elif fault == "squash-outside-base":
        api.original["merge_commit_sha"] = "6" * 40
        api.files["6" * 40] = dict(api.files["3" * 40])
        comparison = _historical_comparison("6" * 40, "4" * 40)
        comparison["merge_base_commit"]["sha"] = "9" * 40
        api.comparisons[("6" * 40, "4" * 40)] = comparison
    elif fault == "foreign-original":
        api.original["head"]["repo"]["id"] = 999
    elif fault == "wrong-ref":
        api.original["head"]["ref"] = "foreign"
    elif fault == "missing-producer":
        api.graph[0]["sha"] = "0" * 40
    elif fault == "disconnected-producer":
        api.graph[1]["parents"] = [{"sha": "0" * 40}]
    elif fault == "selected-manifest":
        api.files["3" * 40][source.MANIFEST_PATH] += b" "
    else:
        api.files["3" * 40][_HISTORICAL_SOURCE_PATHS[2]] += b"changed"
    with pytest.raises(source.QualificationError, match="^" + re.escape(diagnostic) + "$"):
        source.event_admission(api, root, event, "pull_request", "5" * 40)


def test_historical_helper_change_does_not_rescue_changed_manifest_wrong_producer(
    tmp_path: Path,
) -> None:
    """A helper delta cannot rescue a manifest change by a nonproducer PR."""
    root, api, event = _historical_fixture(tmp_path)
    path = root / source.MANIFEST_PATH
    raw = path.read_bytes() + b" "
    path.write_bytes(raw)
    api.files["5" * 40][source.MANIFEST_PATH] = raw
    with pytest.raises(source.QualificationError, match="^changed_PR_original_producer$"):
        source.event_admission(api, root, event, "pull_request", "5" * 40)


def test_historical_no_helper_delta_still_requires_real_published_predecessor(
    tmp_path: Path,
) -> None:
    """Keep the old published branch when no helper delta selects historical admission."""
    root, api, event = _historical_fixture(tmp_path)
    same = api.files["4" * 40][_HISTORICAL_SOURCE_PATHS[0]]
    api.files["5" * 40][_HISTORICAL_SOURCE_PATHS[0]] = same
    (root / _HISTORICAL_SOURCE_PATHS[0]).write_bytes(same)
    result = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert result == {"mode": "unchanged_published", "head": "5" * 40, "publisher_head": "4" * 40}
    assert not any("/compare/" in item for item in api.calls)
    # The existing native predecessor test independently covers success/failure/pending.


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("status", "native_ancestor_relation"),
        ("base", "native_ancestor_relation"),
        ("merge-base", "native_ancestor_relation"),
        ("behind", "native_ancestor_relation"),
        ("bool", "native_ancestor_inventory"),
        ("oversized", "native_ancestor_inventory"),
        ("partial", "native_ancestor_inventory"),
        ("duplicate", "native_ancestor_inventory"),
        ("target", "native_ancestor_inventory"),
        ("parents", "native_ancestor_inventory"),
        ("duplicate-parent", "native_ancestor_inventory"),
    ],
)
def test_historical_native_ancestry_rejects_incomplete_or_wrong_relation(
    tmp_path: Path, fault: str, diagnostic: str
) -> None:
    """Reject the intended native relation or inventory defect after its valid control."""
    _root, api, _event = _historical_fixture(tmp_path)
    ancestor, head = "3" * 40, "4" * 40
    source.require_native_ancestor(api, ancestor, head)
    value = api.comparisons[(ancestor, head)]
    if fault == "status":
        value["status"] = "diverged"
    elif fault == "base":
        value["base_commit"]["sha"] = "9" * 40
    elif fault == "merge-base":
        value["merge_base_commit"]["sha"] = "9" * 40
    elif fault == "behind":
        value["behind_by"] = 1
    elif fault == "bool":
        value["total_commits"] = True
    elif fault == "oversized":
        value["ahead_by"] = value["total_commits"] = 251
    elif fault == "partial":
        value["commits"] = []
    elif fault == "duplicate":
        value["ahead_by"] = value["total_commits"] = 2
        value["commits"] *= 2
    elif fault == "target":
        value["commits"][0]["sha"] = "9" * 40
    elif fault == "parents":
        value["commits"][0]["parents"] = None
    else:
        value["commits"][0]["parents"] *= 2
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.require_native_ancestor(api, ancestor, head)


def test_historical_native_ancestry_identity_uses_native_commit_not_a_synthetic_edge(
    tmp_path: Path,
) -> None:
    """Authenticate an identical commit without manufacturing a comparison edge."""
    _root, api, _event = _historical_fixture(tmp_path)
    source.require_native_ancestor(api, "3" * 40, "3" * 40)
    assert api.calls == ["/repos/" + source.GHCR_REPOSITORY + "/git/commits/" + "3" * 40]


@pytest.mark.parametrize("path", _HISTORICAL_SOURCE_PATHS)
@pytest.mark.parametrize("fault", ["bytes", "size", "mode", "symlink", "hardlink"])
def test_historical_material_binding_rejects_dirty_files_with_unchanged_head(
    tmp_path: Path, path: str, fault: str
) -> None:
    """Native head labels cannot conceal dirty bytes, executable modes or aliased leaves."""
    root, api, _event = _historical_fixture(tmp_path)
    expected = api.files["5" * 40]
    source.authenticate_material_files(root, expected, api.deadline)
    target = root / path
    if fault == "bytes":
        raw = target.read_bytes()
        target.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    elif fault == "size":
        target.write_bytes(target.read_bytes() + b" ")
    elif fault == "mode":
        target.chmod(0o755)
    else:
        saved = tmp_path / "saved-source"
        target.rename(saved)
        if fault == "symlink":
            target.symlink_to(saved)
        else:
            target.hardlink_to(saved)
    with pytest.raises(source.QualificationError, match="^material_source_binding$"):
        source.authenticate_material_files(root, expected, api.deadline)


@pytest.mark.parametrize("prefix", [".github", "scripts", "deploy"])
def test_historical_material_binding_keeps_lexical_intermediate_prefixes(
    tmp_path: Path, prefix: str
) -> None:
    """Retain lexical directory prefixes so real outside children cannot hide a symlink."""
    root, api, _event = _historical_fixture(tmp_path)
    source.authenticate_material_files(root, api.files["5" * 40], api.deadline)
    outside = tmp_path / "outside"
    (root / prefix).rename(outside)
    (root / prefix).symlink_to(outside, target_is_directory=True)
    with pytest.raises(source.QualificationError, match="^nonreal_directory_chain$"):
        source.authenticate_material_files(root, api.files["5" * 40], api.deadline)


def test_historical_candidate_root_is_one_authenticated_data_snapshot(tmp_path: Path) -> None:
    """Keep all selected squash bytes as data and retain literal original-producer equality."""
    root, api, event = _historical_fixture(tmp_path)
    admission = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert admission["mode"] == "historical_pr_candidate"
    work = tmp_path / "consumer-work"
    work.mkdir()
    selected = source.candidate_source_root(api, root, work, admission)
    assert selected != root and selected.is_relative_to(work)
    assert not selected.is_relative_to(api.private)
    for name in _HISTORICAL_SOURCE_PATHS:
        assert (selected / name).read_bytes() == api.files["3" * 40][name]
    assert not (tmp_path / "historical-executed").exists()
    raw = source.authenticate_producer_inputs(api, selected, "1" * 40)
    assert set(raw) == set(_HISTORICAL_SOURCE_PATHS[:3])
    api.files["1" * 40][_HISTORICAL_SOURCE_PATHS[0]] += b"changed original raw source"
    with pytest.raises(source.QualificationError, match="^full_raw_producer_input_drift$"):
        source.authenticate_producer_inputs(api, selected, "1" * 40)


@pytest.mark.parametrize("mode", ["historical_pr_candidate", "historical_main_recovery"])
@pytest.mark.parametrize("admission", ["success", "skipped", "failure", "cancelled", "unknown"])
@pytest.mark.parametrize("promotion", ["success", "skipped", "failure", "cancelled", "unknown"])
def test_historical_consumer_result_table_has_only_two_additional_transitions(
    mode: str, admission: str, promotion: str
) -> None:
    """The two historical modes add exactly one local and one published result."""
    expected = {
        ("historical_pr_candidate", "success", "skipped"): "local",
        ("historical_main_recovery", "success", "success"): "published",
    }
    if (mode, admission, promotion) in expected:
        assert (
            source.consumer_result(mode, admission, promotion)
            == expected[(mode, admission, promotion)]
        )
    else:
        with pytest.raises(source.QualificationError, match="^consumer_predecessors$"):
            source.consumer_result(mode, admission, promotion)


@pytest.mark.parametrize("mode", ["changed_pr_candidate", "historical_pr_candidate"])
def test_historical_and_original_local_consumers_reject_dedicated_registry_token(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    """Neither local candidate branch may activate registry credentials or native load."""
    root, work, reader, trace = _consumer_fixture(monkeypatch, tmp_path, published=False, mode=mode)
    monkeypatch.setenv("GHCR_READ_TOKEN", "synthetic.registry.forbidden")
    with pytest.raises(source.QualificationError, match="^consumer_candidate_registry_token$"):
        source.consume_image(work, root, 30, 2)
    assert not reader.exists() and "login" not in trace and "load" not in trace
    assert "candidate" not in trace and not (work / "evidence/consumer.json").exists()


def test_historical_pr_consumer_uses_data_root_and_cleans_before_native_load(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Local historical admission delegates to its data root before credential-free native use."""
    root, work, reader, trace = _consumer_fixture(
        monkeypatch, tmp_path, published=False, mode="historical_pr_candidate"
    )
    result = source.consume_image(work, root, 30, 2)
    assert trace == ["event", "source-root", "candidate", "cleanup", "load", "inspect"]
    assert result["component_consumption"] == "local" and not reader.exists()
    assert result["runtime_ref"] == result["selection"]["config_digest"]


@pytest.mark.parametrize(
    "fault,route,diagnostic",
    [
        (None, "unknown", "consumer_credential_route"),
        (None, "historical_pr_candidate", "consumer_route_binding"),
        ("head-binding", "unchanged_pr_published", "consumer_route_binding"),
        ("publisher-binding", "unchanged_pr_published", "consumer_route_binding"),
    ],
)
def test_historical_fresh_consumer_binding_rejects_route_head_or_publisher_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str | None, route: str, diagnostic: str
) -> None:
    """Reauthenticate the exact route and coordinates before creating registry auth state."""
    root, work, reader, trace = _consumer_fixture(
        monkeypatch, tmp_path, published=True, fault=fault
    )
    monkeypatch.setenv("PROMETHEUS_CREDENTIAL_ROUTE", route)
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.consume_image(work, root, 30, 2)
    assert not reader.exists() and "login" not in trace and "pull" not in trace
    assert not (work / "evidence/consumer.json").exists()


def test_historical_main_consumer_requires_positive_publisher_and_uses_registry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Main consumers await actual publication rather than loading retained local bytes."""
    root, work, reader, trace = _consumer_fixture(
        monkeypatch, tmp_path, published=True, mode="historical_main_recovery", event_name="push"
    )
    result = source.consume_image(work, root, 30, 2)
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
    assert result["component_consumption"] == "published" and not reader.exists()
    assert "candidate" not in trace and "load" not in trace


@pytest.mark.parametrize("already_present", [False, True])
def test_historical_main_publisher_admits_full_data_before_credentials_and_original_bundles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, already_present: bool
) -> None:
    """Main promotion keeps retained proof, immutable copy and original verification ordering."""
    root, work, config, trace, _manifest = _promotion_fixture(
        monkeypatch, tmp_path, historical=True, already_present=already_present
    )
    result = source.promote_image(work, root, 30, 2)
    assert trace.index("source-root") < trace.index("candidate") < trace.index("login")
    assert (
        trace.index("login")
        < trace.index("pullback")
        < trace.index("verify")
        < trace.index("owned-cleanup")
    )
    assert trace.count("verify") == 2 and not config.exists()
    assert result["compile_invocations"] == 0
    assert result["copy_invocations"] == (0 if already_present else 1)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [("input", "synthetic_reject_input"), ("tool", "publisher_retained_tool_changed")],
)
def test_historical_main_publisher_rejection_precedes_writer_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str, diagnostic: str
) -> None:
    """A historical input or tool rejection stops before writer credentials exist."""
    root, work, config, trace, _manifest = _promotion_fixture(
        monkeypatch, tmp_path, fault, historical=True
    )
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.promote_image(work, root, 30, 2)
    assert "source-root" in trace and "candidate" in trace and "login" not in trace
    assert not config.exists() and not (work / "evidence/publication.json").exists()


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("truncated", "GitHub_complete_source_tree"),
        ("missing", "GitHub_regular_source_blob"),
        ("duplicate", "GitHub_regular_source_blob"),
        ("symlink", "GitHub_regular_source_blob"),
        ("executable", "GitHub_regular_source_blob"),
        ("encoding", "GitHub_blob_encoding"),
        ("size", "GitHub_blob_native_identity"),
        ("identity", "GitHub_blob_native_identity"),
    ],
)
def test_historical_native_four_blob_reader_retains_actual_rejection_causes(
    monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    """Exercise the real existing native reader from a complete valid four-blob baseline."""
    revision, tree_id = "a" * 40, "b" * 40
    files = {name: ("synthetic native blob " + name).encode() for name in _HISTORICAL_SOURCE_PATHS}
    blobs: dict[str, dict[str, Any]] = {}
    rows = []
    for name, raw in files.items():
        oid = hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
        ).hexdigest()
        rows.append({"path": name, "mode": "100644", "type": "blob", "sha": oid})
        blobs[oid] = {
            "encoding": "base64",
            "content": base64.b64encode(raw).decode(),
            "size": len(raw),
            "sha": oid,
        }
    tree: dict[str, Any] = {"sha": tree_id, "truncated": False, "tree": rows}
    adapter = source.GitHubRead.__new__(source.GitHubRead)

    def native_json(endpoint: str) -> dict[str, Any]:
        prefix = "/repos/" + source.GHCR_REPOSITORY
        if endpoint == prefix + "/git/commits/" + revision:
            return {"sha": revision, "tree": {"sha": tree_id}}
        if endpoint == prefix + "/git/trees/" + tree_id + "?recursive=1":
            return tree
        assert endpoint.startswith(prefix + "/git/blobs/")
        return blobs[endpoint.rsplit("/", 1)[1]]

    monkeypatch.setattr(adapter, "json", native_json)
    assert adapter.source_files(revision, _HISTORICAL_SOURCE_PATHS) == files
    first = blobs[rows[0]["sha"]]
    if fault == "truncated":
        tree["truncated"] = True
    elif fault == "missing":
        rows.pop(0)
    elif fault == "duplicate":
        rows.append(dict(rows[0]))
    elif fault in {"symlink", "executable"}:
        rows[0]["mode"] = "120000" if fault == "symlink" else "100755"
    elif fault == "encoding":
        first["encoding"] = "utf-8"
    elif fault == "size":
        first["size"] = True
    else:
        first["sha"] = "f" * 40
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        adapter.source_files(revision, _HISTORICAL_SOURCE_PATHS)


def test_historical_event_rejects_dirty_local_selection_even_with_valid_native_blobs(
    tmp_path: Path,
) -> None:
    """A valid typed local selection still must equal authenticated current-head bytes."""
    root, api, event = _historical_fixture(tmp_path)
    baseline = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert baseline["mode"] == "historical_pr_candidate"
    manifest = source.read_image_manifest(root / source.MANIFEST_PATH)
    manifest["selection"]["config_digest"] = "sha256:" + "e" * 64
    (root / source.MANIFEST_PATH).write_bytes(source.canonical_data(manifest))
    source.read_image_manifest(root / source.MANIFEST_PATH)
    with pytest.raises(source.QualificationError, match="^material_source_binding$"):
        source.event_admission(api, root, event, "pull_request", "5" * 40)


def test_historical_consumer_uses_manifest_bound_by_admission_not_stale_prebinding_selection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Synthetic admission sequencing only; the semantic H binding has separate real tests."""
    root, work, _reader, trace = _consumer_fixture(
        monkeypatch,
        tmp_path,
        published=False,
        mode="historical_pr_candidate",
        fault="restore-bound-manifest",
    )
    path = root / source.MANIFEST_PATH
    bound = source.read_image_manifest(path)["selection"]
    stale = source.read_image_manifest(path)
    stale["selection"]["config_digest"] = "sha256:" + "e" * 64
    path.write_bytes(source.canonical_data(stale))
    source.read_image_manifest(path)
    result = source.consume_image(work, root, 30, 2)
    assert result["selection"] == bound
    assert trace == ["event", "source-root", "candidate", "cleanup", "load", "inspect"]


@pytest.mark.parametrize(
    "event_name,mode,published,route",
    [
        ("pull_request", "historical_main_recovery", True, "unchanged_pr_published"),
        ("pull_request", "new_main_selection", True, "unchanged_pr_published"),
        ("push", "changed_pr_candidate", False, "trusted_published"),
        ("push", "historical_pr_candidate", False, "trusted_published"),
    ],
)
def test_historical_consumer_rejects_wrong_event_and_admission_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    event_name: str,
    mode: str,
    published: bool,
    route: str,
) -> None:
    """A mode valid for another event cannot cross the closed credential route relation."""
    root, work, reader, trace = _consumer_fixture(
        monkeypatch, tmp_path, published=published, mode=mode, event_name=event_name
    )
    monkeypatch.setenv("PROMETHEUS_CREDENTIAL_ROUTE", route)
    with pytest.raises(source.QualificationError, match="^consumer_route_binding$"):
        source.consume_image(work, root, 30, 2)
    assert not reader.exists() and "login" not in trace and "candidate" not in trace
    assert "load" not in trace and not (work / "evidence/consumer.json").exists()


@pytest.mark.parametrize("tool", [False, True])
@pytest.mark.parametrize(
    "changed", ["scripts/ci/prometheus_source_image.py", ".github/workflows/build.yml"]
)
def test_public_package_inventory_change_keeps_full_raw_tool_and_pair_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: bool, changed: str
) -> None:
    manifest = {"schema": source.IMAGE_SCHEMA, "inputs": {"oras": {"retained": None}}}
    files = {name: b"synthetic frozen producer bytes" for name in source.PRODUCER_FILES}
    files[source.MANIFEST_PATH] = source.canonical_data(manifest)
    for name, raw in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    class FrozenSourceAPI:
        def source_files(self, revision: str, names: tuple[str, ...]) -> dict[str, bytes]:
            assert revision == "1" * 40
            assert names == (*source.PRODUCER_FILES, source.MANIFEST_PATH)
            return dict(files)

    monkeypatch.setattr(
        source, "read_image_manifest", lambda *args, **kwargs: copy.deepcopy(manifest)
    )
    api = FrozenSourceAPI()
    assert source.authenticate_producer_inputs(api, tmp_path, "1" * 40, tool=tool)
    files[changed] += b" changed"
    with pytest.raises(source.QualificationError, match="full_raw_producer_input_drift"):
        source.authenticate_producer_inputs(api, tmp_path, "1" * 40, tool=tool)


@pytest.mark.parametrize("stdout_bytes", [512 * 1024, 128 * 1024])
@pytest.mark.parametrize("extra", [0, 1])
def test_public_package_inventory_real_capture_combined_stream_bound_and_cleanup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout_bytes: int, extra: int
) -> None:
    """Real owned pipes/process; synthetic CLI data, no provider or native-capacity claim."""
    shape = "stderr" if stdout_bytes == 128 * 1024 else "balanced"
    outcome = "over" if extra else "exact"
    runner, trace, gh = _fixed_native_capture_fixture(
        tmp_path, f"combined_{shape}_{outcome}", "GitHubRead"
    )
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "GHCR_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    credential = "synthetic.capture." + "opaque." * 80
    monkeypatch.setenv("GH_TOKEN", credential)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic.capture.writer")
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    monkeypatch.setattr(source.shutil, "which", lambda name: str(gh) if name == "gh" else None)
    monkeypatch.setattr(
        source.Native, "run", lambda *args, **kwargs: pytest.fail("credential-bearing Native.run")
    )
    evidence = runner / "evidence"
    evidence.mkdir()
    private = runner / "private"
    adapter = source.GitHubRead(private, evidence, source.time.monotonic() + 8, 2)
    try:
        if extra:
            with pytest.raises(source.QualificationError, match="^GitHub_native_output_bound$"):
                adapter._capture([str(gh), "combined-output"], 1024**2)
            assert adapter.cleanup_deadline is not None
            assert not any(
                (evidence / f"GitHub-2.{suffix}").exists()
                for suffix in ("json", "stdout", "stderr")
            )
        else:
            raw = adapter._capture([str(gh), "combined-output"], 1024**2)
            stderr = (evidence / "GitHub-2.stderr").read_bytes()
            assert raw == b"o" * stdout_bytes
            assert stderr == b"e" * (1024**2 - stdout_bytes)
            assert len(raw) + len(stderr) == 1024**2
            assert adapter.cleanup_deadline is None
        assert adapter.process is None
        assert adapter.seen == {}
    finally:
        adapter.close()
    assert not private.exists()
    assert adapter.process is None and adapter.seen == {}
    commands = [json.loads(line)["argv"] for line in trace.read_text().splitlines()]
    assert commands == [["auth", "status", "--hostname", "github.com"], ["combined-output"]]
    pid = int(trace.with_suffix(".capture-pid").read_text())
    group = int(trace.with_suffix(".capture-group").read_text())
    rows = source.process_census(source.time.monotonic() + 2, ())
    assert pid not in rows
    assert not any(row["pgid"] == group for row in rows.values())
    for path in evidence.iterdir():
        raw = path.read_bytes()
        assert credential.encode() not in raw and b"synthetic.capture.writer" not in raw


@pytest.mark.parametrize(
    "fault", [None, "bytes", "length", "parse", "count", "removed-emsign", "removed-aaa"]
)
def test_current_default_CA_recognizer_binds_bytes_and_closed_DER_inventory(
    monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    import ssl

    assert (
        source.BASE_CA_SHA256 == "e9c7b63ee2623386e9b0a3ee32f499d01a8ea23dc83b8383ddff9f8e749543b7"
    )
    assert source.BASE_CA_BYTES == 222073
    assert source.REMOVED_CA_DER_SHA256 == {
        "86a1ecba089c4a8d3bbe2734c612ba341d813e043cf9e8a862cd5c57a36bbe6b",
        "d7a7a0fb5d7e2731d771e9484ebcdef71d5f0c3e0a2948782bc83ee0ea699ef4",
    }
    raw = b"synthetic exact bundle\n"
    certificates = [f"synthetic DER {i}".encode() for i in range(148)]
    monkeypatch.setattr(source, "BASE_CA_BYTES", len(raw))
    monkeypatch.setattr(source, "BASE_CA_SHA256", source.sha(raw))
    calls: list[str] = []

    class Context:
        def load_verify_locations(self, *, cadata: str) -> None:
            calls.append("explicit-cadata")
            assert cadata == raw.decode("ascii")
            if fault == "parse":
                raise ssl.SSLError("synthetic parse rejection")

        def get_ca_certs(self, *, binary_form: bool) -> list[bytes]:
            calls.append("DER")
            assert binary_form is True
            return certificates[:-1] if fault == "count" else certificates

    def context(protocol: int) -> Context:
        calls.append("new-context")
        assert protocol == ssl.PROTOCOL_TLS_CLIENT
        return Context()

    monkeypatch.setattr(ssl, "SSLContext", context)
    if fault in ("removed-emsign", "removed-aaa"):
        # Controlled fingerprints test both positions without fabricating native roots.
        index = 0 if fault == "removed-emsign" else 1
        monkeypatch.setattr(
            source, "REMOVED_CA_DER_SHA256", frozenset({source.sha(certificates[index])})
        )
    candidate = raw + b"x" if fault == "length" else (b"X" + raw[1:] if fault == "bytes" else raw)
    if fault is None:
        source.validate_default_ca(candidate)
        assert calls == ["new-context", "explicit-cadata", "DER"]
    else:
        with pytest.raises(source.QualificationError):
            source.validate_default_ca(candidate)
        if fault in ("bytes", "length"):
            assert calls == []


def _unchanged_pr_fixture(tmp_path: Path) -> tuple[Path, _HistoricalAPI, dict[str, Any]]:
    """Make all four B/H blobs equal while retaining real historical-source checks."""
    root, api, event = _historical_fixture(tmp_path)
    same = api.files["4" * 40][_HISTORICAL_SOURCE_PATHS[0]]
    api.files["5" * 40][_HISTORICAL_SOURCE_PATHS[0]] = same
    (root / _HISTORICAL_SOURCE_PATHS[0]).write_bytes(same)
    return root, api, event


@pytest.mark.parametrize(
    "state,diagnostic",
    [
        ("missing", "positive_publication_predecessor_missing"),
        ("active", "positive_publication_predecessor_active"),
        ("failure", "publication_predecessor_failed"),
        ("cancelled", "publication_predecessor_cancelled"),
        ("timed_out", "publication_predecessor_timed_out"),
        ("neutral", "publication_predecessor_not_published"),
        ("success", None),
    ],
)
def test_unchanged_pr_evidence_uses_complete_publication_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, diagnostic: str | None
) -> None:
    """Known nonpositive publication selects independent candidate proof, never success."""
    root, api, event = _unchanged_pr_fixture(tmp_path)
    for name in ("GHCR_READ_TOKEN", "GHCR_TOKEN", "DOCKER_CONFIG", "DOCKER_AUTH_CONFIG"):
        monkeypatch.delenv(name, raising=False)
    run = _publication_run(
        status="in_progress" if state == "active" else "completed",
        conclusion=None if state == "active" else state,
    )
    job = _publication_job(
        status="in_progress" if state == "active" else "completed",
        conclusion=None if state == "active" else state,
    )
    run["head_sha"] = job["head_sha"] = "4" * 40
    api.publication = _PublicationPredecessorAPI(
        [] if state == "missing" else [run], {} if state == "missing" else {12: [job]}
    )
    predecessor, observed = source.observe_publication_predecessor(api, "4" * 40)
    assert observed == diagnostic
    assert (predecessor is None) == (diagnostic is not None)
    expected = "unchanged_pr_published" if state == "success" else "historical_pr_candidate"
    assert source.select_pr_evidence_route(api, root, event, "5" * 40) == expected
    admission = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert admission["mode"] == (
        "unchanged_published" if state == "success" else "historical_pr_candidate"
    )
    if diagnostic is not None:
        with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
            source.require_publication_predecessor(api, "4" * 40)
        assert admission["publisher_head"] is None
        assert admission["historical_source_head"] == "3" * 40
    else:
        assert admission["publisher_head"] == "4" * 40
        assert not any("/compare/" in call for call in api.calls)


@pytest.mark.parametrize("path", _HISTORICAL_SOURCE_PATHS[1:3])
def test_unchanged_label_with_recipe_delta_keeps_strict_published_mode(
    tmp_path: Path, path: str
) -> None:
    """Legacy source classification is not four-blob equality or candidate permission."""
    root, api, event = _unchanged_pr_fixture(tmp_path)
    api.publication = _PublicationPredecessorAPI([], {})
    api.files["5" * 40][path] += b"changed recipe"
    (root / path).write_bytes(api.files["5" * 40][path])
    assert source.classify_source_change(api.files["4" * 40], api.files["5" * 40]) == (
        "unchanged_published"
    )
    admission = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert admission["mode"] == "unchanged_published"
    assert api.publication.requests == []


@pytest.mark.parametrize(
    "failure", ["transport", "malformed", "drift", "ambiguous", "contradiction"]
)
def test_unchanged_pr_publication_uncertainty_cannot_select_candidate(
    tmp_path: Path, failure: str
) -> None:
    """The same complete success baseline reaches each independent evidence failure."""
    root, api, event = _unchanged_pr_fixture(tmp_path)
    assert source.event_admission(api, root, event, "pull_request", "5" * 40)["mode"] == (
        "unchanged_published"
    )
    run = {**_publication_run(), "head_sha": "4" * 40}
    job = {**_publication_job(), "head_sha": "4" * 40}
    api.publication = _PublicationPredecessorAPI([run], {12: [job]})
    prefix = "/repos/" + source.GHCR_REPOSITORY + "/actions/"
    endpoint = prefix + "workflows/build.yml/runs?event=push&head_sha=" + "4" * 40
    if failure == "transport":
        api.publication.overrides[endpoint + "&per_page=100&page=1"] = source.QualificationError(
            "GitHub_native_failed"
        )
        diagnostic = "GitHub_native_failed"
    elif failure == "malformed":
        api.publication.overrides[endpoint + "&per_page=100&page=1"] = {}
        diagnostic = "publication_predecessor_run_inventory"
    elif failure == "drift":
        api.publication.overrides[prefix + "runs/12"] = {**run, "run_attempt": 2}
        diagnostic = "publication_predecessor_run_drift"
    elif failure == "ambiguous":
        api.publication = _PublicationPredecessorAPI([run], {12: [job, {**job, "id": 121}]})
        diagnostic = "publication_predecessor_publisher_ambiguous"
    else:
        api.publication = _PublicationPredecessorAPI(
            [run], {12: [{**job, "conclusion": "failure"}]}
        )
        diagnostic = "publication_predecessor_run_job_contradiction"
    api.calls.clear()
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert not any("/pulls/2477" in call or "/compare/" in call for call in api.calls)


def test_unchanged_pr_healthy_publication_ignores_expired_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expired retained artifact cannot block an independently published subject."""
    root, api, event = _unchanged_pr_fixture(tmp_path)
    manifest = source.read_image_manifest(root / source.MANIFEST_PATH)
    manifest["candidate"]["artifact"]["expires_at"] = "2000-01-01T00:00:00Z"
    raw = source.canonical_data(manifest)
    (root / source.MANIFEST_PATH).write_bytes(raw)
    for files in api.files.values():
        files[source.MANIFEST_PATH] = raw
    admission = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert admission["mode"] == "unchanged_published"
    assert not any("/artifacts/" in call or "/pulls/2477" in call for call in api.calls)
    # The actual consumer likewise must not acquire a candidate in published mode.
    material, work, _reader, trace = _consumer_fixture(
        monkeypatch, tmp_path / "consume", published=True
    )
    assert source.consume_image(work, material, 30, 2)["component_consumption"] == "published"
    assert "candidate" not in trace and "load" not in trace


@pytest.mark.parametrize(
    "credential", ["GHCR_READ_TOKEN", "GHCR_TOKEN", "DOCKER_CONFIG", "DOCKER_AUTH_CONFIG"]
)
def test_pr_evidence_selection_rejects_registry_environment_before_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credential: str
) -> None:
    root, api, event = _unchanged_pr_fixture(tmp_path)
    for name in ("GHCR_READ_TOKEN", "GHCR_TOKEN", "DOCKER_CONFIG", "DOCKER_AUTH_CONFIG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(credential, "synthetic-forbidden")
    with pytest.raises(
        source.QualificationError, match="^consumer_selection_registry_credentials$"
    ):
        source.select_pr_evidence_route(api, root, event, "5" * 40)
    assert api.calls == [] and api.publication.requests == []


@pytest.mark.parametrize("fault", ["head", "base", "state"])
def test_candidate_acquisition_rechecks_current_pr_before_native_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    root, work, reader, trace = _consumer_fixture(
        monkeypatch, tmp_path, published=False, mode="historical_pr_candidate"
    )
    original = source.candidate_payload

    def acquire(api: Any, selected: Path, destination: Path) -> dict[str, Any]:
        result = original(api, selected, destination)
        native_json = api.json

        def changed(endpoint: str) -> dict[str, Any]:
            value = native_json(endpoint)
            if fault == "state":
                value["state"] = "closed"
            else:
                value[fault]["sha"] = "f" * 40
            return value

        api.json = changed
        return result

    monkeypatch.setattr(source, "candidate_payload", acquire)
    with pytest.raises(source.QualificationError, match="^consumer_route_binding$"):
        source.consume_image(work, root, 30, 2)
    assert trace == ["event", "source-root", "candidate", "cleanup"]
    assert not reader.exists() and not (work / "evidence/consumer.json").exists()


@pytest.mark.parametrize("published", [False, True])
@pytest.mark.parametrize("retarget", [False, True])
def test_consumer_rechecks_main_base_ref_after_acquisition_before_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, published: bool, retarget: bool
) -> None:
    root, work, reader, trace = _consumer_fixture(
        monkeypatch,
        tmp_path,
        published=published,
        mode="unchanged_published" if published else "historical_pr_candidate",
    )
    original_json = source.GitHubRead.json
    boundary = "public-package" if published else "candidate"
    observed: list[str] = []

    def live_pr(api: Any, endpoint: str) -> dict[str, Any]:
        value = original_json(api, endpoint)
        assert endpoint.endswith("/pulls/2493")
        if boundary in trace:
            assert value["base"]["sha"] == "b" * 40 and value["base"]["ref"] == "main"
            if retarget:
                value["base"]["ref"] = "release"
            observed.append(value["base"]["ref"])
        return value

    monkeypatch.setattr(source.GitHubRead, "json", live_pr)
    before_effect = (
        ["event", "predecessor", "public-package"]
        if published
        else ["event", "source-root", "candidate"]
    )
    if retarget:
        with pytest.raises(source.QualificationError, match="^consumer_route_binding$"):
            source.consume_image(work, root, 30, 2)
        assert observed == ["release"] and trace == [*before_effect, "cleanup"]
        assert not (work / "evidence/consumer.json").exists()
    else:
        source.consume_image(work, root, 30, 2)
        effects = (
            ["login", "pull", "raw", "cleanup", "inspect"]
            if published
            else ["cleanup", "load", "inspect"]
        )
        assert observed == ["main"] and trace == [*before_effect, *effects]
    assert not reader.exists() and not (work / "GitHub-private").exists()


def test_pr_selection_change_before_consumption_rejects_expected_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A positive publisher arriving between observations cannot silently change classes."""
    root, api, event = _unchanged_pr_fixture(tmp_path)
    for name in ("GHCR_READ_TOKEN", "GHCR_TOKEN", "DOCKER_CONFIG", "DOCKER_AUTH_CONFIG"):
        monkeypatch.delenv(name, raising=False)
    success = api.publication
    api.publication = _PublicationPredecessorAPI([], {})
    selected = source.select_pr_evidence_route(api, root, event, "5" * 40)
    assert selected == "historical_pr_candidate"
    api.publication = success
    fresh = source.event_admission(api, root, event, "pull_request", "5" * 40)
    assert fresh["mode"] == "unchanged_published"
    monkeypatch.setenv("PROMETHEUS_CREDENTIAL_ROUTE", selected)
    with pytest.raises(source.QualificationError, match="^consumer_route_binding$"):
        source._bind_consumer_route(event, "pull_request", "5" * 40, fresh)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("original-unmerged", "historical_original_merged_PR"),
        ("selected-manifest", "historical_selected_manifest"),
        ("selected-recipe", "historical_recipe_drift"),
    ],
)
def test_unchanged_nonpositive_publication_still_requires_original_source(
    tmp_path: Path, fault: str, diagnostic: str
) -> None:
    root, api, event = _unchanged_pr_fixture(tmp_path)
    api.publication = _PublicationPredecessorAPI([], {})
    assert source.event_admission(api, root, event, "pull_request", "5" * 40)["mode"] == (
        "historical_pr_candidate"
    )
    if fault == "original-unmerged":
        api.original["merged"] = False
    elif fault == "selected-manifest":
        api.files["3" * 40][source.MANIFEST_PATH] += b" "
    else:
        api.files["3" * 40][_HISTORICAL_SOURCE_PATHS[2]] += b"drift"
    with pytest.raises(source.QualificationError, match="^" + diagnostic + "$"):
        source.event_admission(api, root, event, "pull_request", "5" * 40)


def _native_fixed_base_image(*, modern: bool = False, current: bool = True) -> dict[str, Any]:
    assert current or not modern
    base = source.BASE if current else source.HISTORICAL_BASE
    config = source.BASE_CONFIG if current else source.HISTORICAL_BASE_CONFIG
    diff_ids = (
        [r["diff_id"] for r in source.BASE_LAYER_CONTRACTS]
        if current
        else source._NATIVE_HISTORICAL_BASE_DIFF_IDS
    )
    image: dict[str, Any] = {
        "Id": base.split("@", 1)[1] if modern else config,
        "Os": "linux",
        "Architecture": "amd64",
        "RepoDigests": [base],
        "RootFS": {"Type": "layers", "Layers": diff_ids},
        "Config": {
            "User": "65532",
            "WorkingDir": "/home/nonroot",
            "Env": [
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
            ],
        },
    }
    if modern:
        image["Descriptor"] = {
            "mediaType": source.OCI_MANIFEST,
            "digest": source.BASE.split("@", 1)[1],
            "size": 2864,
        }
    return image


@pytest.mark.parametrize("modern", [False, True])
def test_native_base_identity_keeps_config_and_engine_roles(modern: bool) -> None:
    image = _native_fixed_base_image(modern=modern)
    relation = source.native_base_identity(image)
    assert relation["config_digest"] == source.BASE_CONFIG
    assert relation["operand"] == relation["engine_id"] == image["Id"]
    actual = {"Image": image["Id"], "Config": {"Image": image["Id"]}}
    if modern:
        actual["ImageManifestDescriptor"] = {
            **image["Descriptor"],
            "platform": {"architecture": "amd64", "os": "linux"},
        }
    source.native_container_image_identity(actual, relation)


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-id",
        "rootfs-order",
        "repo",
        "volumes",
        "onbuild",
        "descriptor-size-bool",
        "descriptor-extra",
        "descriptor-platform",
    ],
)
def test_native_base_identity_rejects_cross_field_contradictions(fault: str) -> None:
    image = _native_fixed_base_image(modern=True)
    if fault == "wrong-id":
        image["Id"] = "sha256:" + "f" * 64
    elif fault == "rootfs-order":
        image["RootFS"]["Layers"].reverse()
    elif fault == "repo":
        image["RepoDigests"] = []
    elif fault == "volumes":
        image["Config"]["Volumes"] = {"/unexpected": {}}
    elif fault == "onbuild":
        image["Config"]["OnBuild"] = ["RUN false"]
    elif fault == "descriptor-size-bool":
        image["Descriptor"]["size"] = True
    elif fault == "descriptor-extra":
        image["Descriptor"]["extra"] = "ignored?"
    else:
        image["Descriptor"]["platform"] = {"os": "linux", "architecture": "amd64"}
    with pytest.raises(source.QualificationError):
        source.native_base_identity(image)


@pytest.mark.parametrize("fault", ["K", "Q", "missing-D", "platform", "extra-D", "annotations"])
def test_native_base_container_descriptor_is_role_specific_and_fail_closed(fault: str) -> None:
    image = _native_fixed_base_image(modern=True)
    relation = source.native_base_identity(image)
    actual = {
        "Image": image["Id"],
        "Config": {"Image": image["Id"]},
        "ImageManifestDescriptor": {
            **image["Descriptor"],
            "platform": {"architecture": "amd64", "os": "linux"},
        },
    }
    if fault == "K":
        actual["Image"] = source.BASE_CONFIG
    elif fault == "Q":
        actual["Config"]["Image"] = source.BASE
    elif fault == "missing-D":
        del actual["ImageManifestDescriptor"]
    elif fault == "platform":
        actual["ImageManifestDescriptor"]["platform"]["architecture"] = "arm64"
    elif fault == "extra-D":
        actual["ImageManifestDescriptor"]["urls"] = []
    else:
        actual["ImageManifestDescriptor"]["annotations"] = {}
    with pytest.raises(source.QualificationError):
        source.native_container_image_identity(actual, relation)


@pytest.mark.parametrize(
    "raw", [b"[]", b"[{},{}]", b"{}", b'[{"Id":"a","Id":"b"}]', b'[{"size":NaN}]', b"[{}] {}"]
)
def test_native_one_image_rejects_nonunique_or_incomplete_carriers(raw: bytes) -> None:
    with pytest.raises((ValueError, source.QualificationError)):
        source.native_one_image(raw)


def test_native_BASE20_uses_shared_content_without_weakening_canonical_grammar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = _finite_vendor_input(tmp_path, monkeypatch)
    root_digest = source.BASE.split("@", 1)[1]
    root_size = (layout / "blobs/sha256" / root_digest[7:]).stat().st_size
    monkeypatch.setattr(source, "_NATIVE_BASE_MANIFEST_SIZE", root_size)
    index = json.loads((layout / "index.json").read_bytes())
    index["manifests"][0]["annotations"] = {
        "containerd.io/distribution.source.gcr.io": "distroless/static-debian13"
    }
    (layout / "index.json").write_text(json.dumps(index))
    (layout / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "Config": "blobs/sha256/" + source.BASE_CONFIG[7:],
                    "RepoTags": None,
                    "Layers": [
                        "blobs/sha256/" + row["descriptor"]["digest"][7:]
                        for row in source.BASE_LAYER_CONTRACTS
                    ],
                }
            ]
        )
    )
    assert source.native_base_export_graph(layout) == {
        "mediaType": source.OCI_MANIFEST,
        "digest": root_digest,
        "size": root_size,
    }
    with pytest.raises(source.QualificationError, match="layout_transport_annotation"):
        source._layout_root(layout)
    (layout / "extra").write_bytes(b"unaccounted")
    with pytest.raises(source.QualificationError):
        source.native_base_export_graph(layout)


def _native_go_inputs(
    monkeypatch: pytest.MonkeyPatch, *, indexed: bool
) -> tuple[dict[str, Any], bytes, bytes]:
    manifest = {
        "schemaVersion": 2,
        "mediaType": source.OCI_MANIFEST,
        "config": {"mediaType": source.OCI_CONFIG, "size": 10, "digest": source._NATIVE_GO_CONFIG},
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 10,
                "digest": "sha256:" + str(i) * 64,
            }
            for i in range(5)
        ],
    }
    manifest_raw = json.dumps(manifest).encode()
    manifest_raw += b" " * (1922 - len(manifest_raw))
    assert len(manifest_raw) == 1922
    digest = "sha256:" + source.sha(manifest_raw)
    monkeypatch.setattr(source, "_NATIVE_GO_MANIFEST", digest)
    descriptor = {
        "mediaType": source.OCI_MANIFEST,
        "digest": digest,
        "size": 1922,
        "platform": {"architecture": "amd64", "os": "linux"},
        "annotations": dict(source._NATIVE_GO_ANNOTATIONS),
    }
    index_raw = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [descriptor],
        }
    ).encode()
    monkeypatch.setattr(source, "_NATIVE_GO_INDEX", "sha256:" + source.sha(index_raw))
    image = {
        "Id": digest,
        "Os": "linux",
        "Architecture": "amd64",
        "Descriptor": (
            descriptor if indexed else {k: descriptor[k] for k in ("mediaType", "digest", "size")}
        ),
        "RepoDigests": ["golang@" + (source._NATIVE_GO_INDEX if indexed else digest)],
        "RootFS": {"Type": "layers", "Layers": list(source._NATIVE_GO_DIFF_IDS)},
        "Config": {
            "WorkingDir": "/go",
            "Cmd": ["/bin/sh"],
            "Env": [
                "PATH=/go/bin:/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "GOLANG_VERSION=1.26.10",
                "GOTOOLCHAIN=local",
                "GOPATH=/go",
            ],
        },
    }
    return image, index_raw, manifest_raw


@pytest.mark.parametrize("indexed", [False, True])
def test_native_go_profile_binds_actual_index_or_manifest_operand(
    monkeypatch: pytest.MonkeyPatch, indexed: bool
) -> None:
    image, index, manifest = _native_go_inputs(monkeypatch, indexed=indexed)
    relation = source.native_go_identity(image, index, manifest, indexed=indexed)
    descriptor = {**relation["manifest"], "platform": {"architecture": "amd64", "os": "linux"}}
    if indexed:
        descriptor["annotations"] = dict(source._NATIVE_GO_ANNOTATIONS)
    actual = {
        "Image": source._NATIVE_GO_INDEX if indexed else source._NATIVE_GO_MANIFEST,
        "Config": {"Image": relation["operand"]},
        "ImageManifestDescriptor": descriptor,
    }
    source.native_container_image_identity(actual, relation)
    actual["Config"]["Image"] = source._NATIVE_GO_CONFIG
    with pytest.raises(source.QualificationError):
        source.native_container_image_identity(actual, relation)


@pytest.mark.parametrize("annotations", [None, {}, {"unexpected": "value"}])
def test_native_go_present_descriptor_annotations_cannot_be_ignored(
    monkeypatch: pytest.MonkeyPatch, annotations: object
) -> None:
    image, index, manifest = _native_go_inputs(monkeypatch, indexed=False)
    relation = source.native_go_identity(image, index, manifest)
    actual = {
        "Image": relation["operand"],
        "Config": {"Image": relation["operand"]},
        "ImageManifestDescriptor": {
            **relation["manifest"],
            "platform": {"architecture": "amd64", "os": "linux"},
            "annotations": annotations,
        },
    }
    with pytest.raises(source.QualificationError):
        source.native_container_image_identity(actual, relation)


@pytest.mark.parametrize(
    "fault", [None, "ID", "command-null", "operand", "descriptor", "owner", "network"]
)
def test_native_metadata_custody_keeps_explicit_command_and_full_ID(fault: str | None) -> None:
    image = _native_fixed_base_image(modern=True)
    relation = source.native_base_identity(image)
    environment = source.clean_environment(
        source.GUEST_TMP,
        source.GUEST_TMP,
        source.GUEST_TMP / "gocache",
        Path("/modules"),
        offline=True,
    )
    mounts = {"/src": "/owned/source", "/usr/local/go": "/owned/go", "/modules": "/owned/modules"}
    expected = {
        "container_id": "a" * 64,
        "image": image["Id"],
        "image_relation": relation,
        "owner": "synthetic-owner",
        "command": ["version"],
        "environment": environment,
        "mounts": mounts,
    }
    actual = {
        "Id": "a" * 64,
        "Name": "/synthetic",
        "Image": image["Id"],
        "ImageManifestDescriptor": {
            **relation["manifest"],
            "platform": {"architecture": "amd64", "os": "linux"},
        },
        "Config": {
            "Image": image["Id"],
            "Labels": {source.LABEL: "synthetic-owner"},
            "User": "65532:65532",
            "WorkingDir": "/src",
            "Entrypoint": ["/usr/local/go/bin/go"],
            "Cmd": ["version"],
            "Env": [key + "=" + value for key, value in environment.items()],
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "NanoCpus": 2000000000,
            "Memory": 4294967296,
            "PidsLimit": 128,
            "CapDrop": ["ALL"],
            "CapAdd": None,
            "SecurityOpt": ["no-new-privileges"],
            "Tmpfs": {str(source.GUEST_TMP): source.GUEST_TMPFS},
        },
        "Mounts": [
            {"Type": "bind", "RW": False, "Destination": key, "Source": value}
            for key, value in mounts.items()
        ],
    }
    if fault == "ID":
        actual["Id"] = "b" * 64
    elif fault == "command-null":
        actual["Config"]["Cmd"] = None
    elif fault == "operand":
        actual["Config"]["Image"] = source.BASE_CONFIG
    elif fault == "descriptor":
        actual["ImageManifestDescriptor"]["platform"]["os"] = "other"
    elif fault == "owner":
        actual["Config"]["Labels"][source.LABEL] = "foreign"
    elif fault == "network":
        actual["HostConfig"]["NetworkMode"] = "bridge"
    if fault is None:
        source.validate_container(actual, "synthetic", expected)
    else:
        with pytest.raises(source.QualificationError):
            source.validate_container(actual, "synthetic", expected)


def test_native_BASE20_reaches_F_current_support_without_relabeling_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts.ci import fetch_docker_source_artifacts as fetcher

    layout = _finite_vendor_input(tmp_path, monkeypatch)
    destination = tmp_path / "support"
    destination.mkdir()
    layout.rename(destination / "base-layout")
    layout = destination / "base-layout"
    core = {
        "mediaType": source.OCI_MANIFEST,
        "digest": source.BASE.split("@", 1)[1],
        "size": (layout / "blobs/sha256" / source.BASE.split(":")[-1]).stat().st_size,
    }
    monkeypatch.setattr(source, "_NATIVE_BASE_MANIFEST_SIZE", core["size"])
    (layout / "index.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.index.v1+json",
                "manifests": [
                    {
                        **core,
                        "annotations": {
                            "containerd.io/distribution.source.gcr.io": "distroless/static-debian13"
                        },
                    }
                ],
            }
        )
    )
    (layout / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "Config": "blobs/sha256/" + source.BASE_CONFIG[7:],
                    "RepoTags": None,
                    "Layers": [
                        "blobs/sha256/" + row["descriptor"]["digest"][7:]
                        for row in source.BASE_LAYER_CONTRACTS
                    ],
                }
            ]
        )
    )
    for path in layout.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
    archive = destination / "base-image.tar"
    with tarfile.open(archive, "w") as saved:
        for path in sorted(layout.rglob("*")):
            info = tarfile.TarInfo(path.relative_to(layout).as_posix())
            info.mode = 0o700 if path.is_dir() else 0o600
            if path.is_dir():
                info.type = tarfile.DIRTYPE
                saved.addfile(info)
            else:
                raw = path.read_bytes()
                info.size = len(raw)
                saved.addfile(info, io.BytesIO(raw))
    rows, _ = fetcher._alertmanager_base_export_inventory(archive)
    rootfs = {"Type": "layers", "Layers": [r["diff_id"] for r in source.BASE_LAYER_CONTRACTS]}
    report = {
        "base": {
            "archive_sha256": source.file_hash(archive),
            "config": source.BASE_CONFIG,
            "RootFS": rootfs,
            "actual_local_OCI_descriptor": core,
            "complete_export_file_inventory": rows,
        }
    }
    qualification = {
        "root_inputs": {"base-image.tar": source.file_hash(archive)},
        "loaded_base": {"RootFS": rootfs},
    }
    assert len(rows) == 18  # 20 total members including the two directories.
    assert fetcher._alertmanager_current_base_graph(layout) == core
    fetcher._alertmanager_current_support_base(destination, report, qualification)
    report["base"]["config"] = core["digest"]
    with pytest.raises(source.QualificationError):
        fetcher._alertmanager_current_support_base(destination, report, qualification)


class _ProductImportNative(source.Native):
    """Offline transport shaped by retained Docker product create/save observations."""

    def __init__(self, tmp_path: Path, graph: dict[str, Any], modern: bool) -> None:
        evidence = tmp_path / "native-evidence"
        evidence.mkdir()
        super().__init__(evidence, time.monotonic() + 600, 45)
        self.graph = graph
        self.calls: list[tuple[list[str], str, dict[str, Any]]] = []
        self.loaded = False
        self.preexisting = False
        self.tag_collision = False
        self.fail_label = ""
        self.fail_after_effect = False
        self.error = TimeoutError("synthetic operation timeout")
        self.cleanup_error = False
        self.survive = False
        self.bad_id = False
        self.bad_version = False
        self.bad_terminal = False
        self.custody_fault = ""
        self.archive_fault = ""
        self.extra_tag = False
        self.inventory_fault = ""
        self.image_inventory_prefix = b""
        self.container_inventory_prefix = b""
        self.save_file_fault = ""
        self.start_running_timeout = False
        self.containers: dict[str, dict[str, Any]] = {}
        self.created_count = 0
        self.cleanup_starts = 0
        self.manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "digest": graph["config_digest"],
                "size": len(graph["config_raw"]),
            },
            "layers": [
                {
                    "mediaType": "application/vnd.docker.image.rootfs.diff.tar",
                    "digest": digest,
                    "size": len(raw),
                }
                for digest, raw in zip(graph["diff_ids"], graph["expanded_layers"], strict=True)
            ],
        }
        self.manifest_raw = json.dumps(self.manifest, separators=(",", ":")).encode()
        self.engine = (
            "sha256:" + source.sha(self.manifest_raw) if modern else graph["config_digest"]
        )
        self.descriptor = {
            "mediaType": self.manifest["mediaType"],
            "digest": self.engine,
            "size": len(self.manifest_raw),
            "annotations": {
                "io.containerd.image.name": "docker.io/library/pulseplate-prometheus:candidate",
                "org.opencontainers.image.ref.name": "candidate",
            },
        }
        self.image = {
            "Id": self.engine,
            "Os": "linux",
            "Architecture": "amd64",
            "RootFS": {"Type": "layers", "Layers": graph["diff_ids"]},
            "Config": json.loads(graph["config_raw"])["config"],
            "RepoTags": ["pulseplate-prometheus:candidate"],
            "RepoDigests": ["pulseplate-prometheus@" + self.engine] if modern else [],
        }
        if modern:
            self.image["Descriptor"] = self.descriptor
        self.modern = modern

    def begin_cleanup(self) -> None:
        self.cleanup_starts += 1
        super().begin_cleanup()

    def archive_bytes(self) -> bytes:
        content = {"blobs/sha256/" + self.graph["config_digest"][7:]: self.graph["config_raw"]}
        content.update(
            ("blobs/sha256/" + digest[7:], raw)
            for digest, raw in zip(
                self.graph["diff_ids"], self.graph["expanded_layers"], strict=True
            )
        )
        native_manifest = copy.deepcopy(self.manifest)
        if self.archive_fault == "layer-order":
            native_manifest["layers"].reverse()
        raw = json.dumps(native_manifest, separators=(",", ":")).encode()
        content["blobs/sha256/" + self.engine[7:]] = raw
        index = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [{key: self.descriptor[key] for key in ("mediaType", "digest", "size")}],
        }
        if self.archive_fault == "index-bool":
            index["schemaVersion"] = True
        elif self.archive_fault == "tagged-index":
            index["manifests"] = [self.descriptor]
        elif self.archive_fault == "empty-index-annotations":
            index["manifests"][0]["annotations"] = {}
        compatibility = [
            {
                "Config": "blobs/sha256/" + self.graph["config_digest"][7:],
                "RepoTags": None,
                "Layers": ["blobs/sha256/" + d[7:] for d in self.graph["diff_ids"]],
            }
        ]
        if self.archive_fault == "compat-tag":
            compatibility[0]["RepoTags"] = ["foreign:tag"]
        elif self.archive_fault == "compat-empty-tags":
            compatibility[0]["RepoTags"] = []
        elif self.archive_fault == "compat-candidate":
            compatibility[0]["RepoTags"] = ["pulseplate-prometheus:candidate"]
        content.update(
            {
                "index.json": json.dumps(index).encode(),
                "manifest.json": json.dumps(compatibility).encode(),
                "oci-layout": b'{"imageLayoutVersion":"1.0.0"}',
            }
        )
        if self.archive_fault == "duplicate-json":
            content["oci-layout"] = b'{"imageLayoutVersion":"1.0.0","imageLayoutVersion":"1.0.0"}'
        if self.archive_fault == "layer-bytes":
            key = "blobs/sha256/" + self.graph["diff_ids"][0][7:]
            content[key] = b"x" + content[key][1:]
        if self.archive_fault == "config-bytes":
            key = "blobs/sha256/" + self.graph["config_digest"][7:]
            content[key] = b"x" + content[key][1:]
        if self.archive_fault == "extra":
            content["foreign"] = b"x"
        if self.archive_fault == "missing":
            del content["oci-layout"]
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name in ("blobs", "blobs/sha256"):
                member = tarfile.TarInfo(name)
                member.type, member.mode = tarfile.DIRTYPE, 0o755
                archive.addfile(member)
            for name, data in sorted(content.items()):
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = 0o644 if name in ("index.json", "manifest.json") else 0o444
                if name == "oci-layout":
                    if self.archive_fault == "mode":
                        member.mode = 0o777
                    if self.archive_fault == "pax":
                        member.pax_headers = {"comment": "unqualified"}
                    if self.archive_fault == "symlink":
                        member.type, member.linkname, member.size = tarfile.SYMTYPE, "index.json", 0
                archive.addfile(member, io.BytesIO(data))
                if self.archive_fault == "duplicate" and name == "oci-layout":
                    archive.addfile(member, io.BytesIO(data))
        raw = stream.getvalue()
        if self.archive_fault == "trailer":
            raw = raw[:-1] + b"x"
        return raw

    def run(self, argv: list[str], name: str, env: dict[str, str], **kwargs: Any) -> bytes:
        self.calls.append((argv, name, kwargs))
        assert argv[:3] == ["/usr/bin/docker", "--config", str(self.evidence.parent / "config")]
        if kwargs.get("cleaning"):
            assert self.cleanup_deadline is not None
        if name == self.fail_label and not self.fail_after_effect:
            raise self.error
        args = argv[3:]
        raw = b""
        if args[:2] == ["image", "ls"]:
            assert args[2:] == [
                "--all",
                "--no-trunc",
                "--format",
                "{{.ID}}\t{{.Repository}}:{{.Tag}}",
            ]
            rows = []
            if self.preexisting:
                rows.append(self.engine + "\t<none>:<none>")
            if self.loaded or self.tag_collision:
                rows.append(self.engine + "\tpulseplate-prometheus:candidate")
            if self.extra_tag and self.loaded:
                rows.append(self.engine + "\tforeign:tag")
            raw = ("\n".join(rows) + ("\n" if rows else "")).encode()
            raw = self.image_inventory_prefix + raw
            if self.inventory_fault and name == self.inventory_fault:
                raw = b"incomplete"
        elif args[0] == "load":
            self.loaded = True
        elif args[:2] == ["image", "inspect"]:
            raw = json.dumps(self.image).encode()
        elif args[:2] == ["image", "save"]:
            assert args[2] == "--output" and args[-1] == self.engine
            target = Path(args[3])
            assert kwargs["watched_output"] == target.parent
            target.write_bytes(self.archive_bytes())
            if self.save_file_fault == "symlink":
                other = target.parent.parent / "untrusted-native.tar"
                target.rename(other)
                target.symlink_to(other)
            elif self.save_file_fault == "extra":
                (target.parent / "unexpected").write_bytes(b"extra")
        elif args[0] == "ps":
            assert args[1:] == ["--all", "--no-trunc", "--format", "{{.ID}}\t{{.Names}}"]
            raw = "".join(
                k + "\t" + v["Name"][1:] + "\n" for k, v in self.containers.items()
            ).encode()
            raw = self.container_inventory_prefix + raw
        elif args[0] == "create":
            assert all(
                flag in args for flag in ("--pull", "--read-only", "--cap-drop", "--security-opt")
            )
            for flag, value in (
                ("--pull", "never"),
                ("--user", "65532:65532"),
                ("--network", "none"),
                ("--cap-drop", "ALL"),
                ("--cpus", "2"),
                ("--memory", "4g"),
                ("--pids-limit", "128"),
            ):
                assert args[args.index(flag) + 1] == value
            self.created_count += 1
            identifier = f"{self.created_count:064x}"
            config = copy.deepcopy(self.image["Config"])
            label_key, label_value = args[args.index("--label") + 1].split("=", 1)
            config["Labels"][label_key] = label_value
            config["Image"] = self.engine
            config["Volumes"] = None
            if "--entrypoint" in args:
                config["Entrypoint"] = [args[args.index("--entrypoint") + 1]]
                config["Cmd"] = ["--version"]
                assert args[-2:] == [self.engine, "--version"]
            else:
                assert args[-1] == self.engine
            actual = {
                "Id": identifier,
                "Name": "/" + args[args.index("--name") + 1],
                "Image": self.engine,
                "Config": config,
                "Path": config["Entrypoint"][0],
                "Args": config["Cmd"],
                "Mounts": [],
                "State": {
                    "Status": "created",
                    "Running": False,
                    "Paused": False,
                    "Restarting": False,
                    "OOMKilled": False,
                    "Dead": False,
                    "Pid": 0,
                    "ExitCode": 0,
                    "Error": "",
                    "StartedAt": "0001-01-01T00:00:00Z",
                },
                "HostConfig": {
                    "NetworkMode": "none",
                    "ReadonlyRootfs": True,
                    "Privileged": False,
                    "NanoCpus": 2000000000,
                    "Memory": 4294967296,
                    "PidsLimit": 128,
                    "CapDrop": ["ALL"],
                    "CapAdd": None,
                    "SecurityOpt": ["no-new-privileges"],
                    "AutoRemove": False,
                    "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
                    "Binds": None,
                    "VolumesFrom": None,
                    "Tmpfs": None,
                    "Devices": [],
                    "DeviceRequests": None,
                    "PidMode": "",
                    "UTSMode": "",
                    "IpcMode": "private",
                },
            }
            if self.modern:
                actual["ImageManifestDescriptor"] = {
                    **self.descriptor,
                    "platform": {"os": "linux", "architecture": "amd64"},
                }
            self.containers[identifier] = actual
            raw = ("short" if self.bad_id else identifier).encode() + b"\n"
        elif args[0] == "inspect":
            assert re.fullmatch(r"[0-9a-f]{64}", args[-1])
            actual = copy.deepcopy(self.containers[args[-1]])
            if self.custody_fault:
                if self.custody_fault == "ID":
                    actual["Id"] = "f" * 64
                elif self.custody_fault == "operand":
                    actual["Config"]["Image"] = "sha256:" + "f" * 64
                elif self.custody_fault == "owner":
                    actual["Config"]["Labels"][source.LABEL] = "foreign"
                elif self.custody_fault == "mount":
                    actual["Mounts"] = [{"Destination": "/host"}]
                elif self.custody_fault == "network":
                    actual["HostConfig"]["NetworkMode"] = "host"
                elif self.custody_fault == "descriptor":
                    actual["ImageManifestDescriptor"]["platform"]["os"] = "foreign"
                elif self.custody_fault == "command":
                    actual["Config"]["Cmd"] = ["foreign"]
            raw = json.dumps(actual).encode()
        elif args[0] == "cp":
            identifier, path = args[1].split(":", 1)
            assert identifier in self.containers and args[2] == "-"
            filename = Path(path).name
            data = self.graph["files"][filename]
            member = tarfile.TarInfo(filename)
            member.size = len(data)
            member.mode = 0o755 if filename in ("prometheus", "promtool") else 0o644
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w") as archive:
                archive.addfile(member, io.BytesIO(data))
            raw = stream.getvalue()
        elif args[0] == "start":
            assert args[1] == "--attach" and args[2] in self.containers
            actual = self.containers[args[2]]
            actual["State"].update(
                Status="exited",
                Running=False,
                OOMKilled=self.bad_terminal,
                StartedAt="2026-11-07T00:00:00Z",
            )
            raw = ("version 3.15.0 " + source.REVISION + " go1.27.3").encode()
            if self.bad_version:
                raw = b"wrong version"
            if self.start_running_timeout:
                actual["State"].update(Status="running", Running=True, Pid=123)
                raise self.error
        elif args[0] == "rm":
            assert args[-1] in self.containers
            if self.cleanup_error:
                raise RuntimeError("synthetic cleanup failure")
            if not self.survive:
                del self.containers[args[-1]]
        elif args[:2] == ["image", "rm"]:
            assert args[2:] == [self.engine] and not self.containers and not self.preexisting
            self.loaded = False
        else:
            raise AssertionError(argv)
        stdout = self.evidence / (name + ".stdout")
        stdout.write_bytes(raw)
        self.records.append({"argv": argv, "stdout": str(stdout), "exit": 0})
        if name == self.fail_label:
            raise self.error
        return raw


def _product_import_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modern: bool = True
) -> tuple[_ProductImportNative, Path, dict[str, Any]]:
    base, layout, archive, _ = _finite_constructed(tmp_path, monkeypatch)
    graph = source.validate_oci_graph(layout, base, synthetic=True)
    return _ProductImportNative(tmp_path, graph, modern), archive, graph


def _run_product_import(
    native: _ProductImportNative, archive: Path, graph: dict[str, Any], *, synthetic: bool = True
) -> dict[str, Any]:
    return source.native_import(
        native,
        native.evidence.parent,
        "/usr/bin/docker",
        native.evidence.parent / "config",
        {},
        archive,
        graph,
        synthetic=synthetic,
    )


@pytest.mark.parametrize("modern", [False, True])
@pytest.mark.parametrize("synthetic", [False, True])
def test_native_import_complete_product_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modern: bool, synthetic: bool
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch, modern)
    result = _run_product_import(native, archive, graph, synthetic=synthetic)
    assert result["image_config_id"] == graph["config_digest"]
    assert result["status"] == (
        "observed_synthetic_format_only" if synthetic else "observed_real_native_import"
    )
    assert result["synthetic_executed"] is False and len(result["copies"]) == 7
    assert native.created_count == (1 if synthetic else 3)
    starts = [argv for argv, _, _ in native.calls if argv[3] == "start"]
    assert len(starts) == (0 if synthetic else 2)
    assert not native.containers and not native.loaded and native.cleanup_starts == 1
    assert not any(argv[3] == "run" for argv, _, _ in native.calls)
    assert len([argv for argv, _, _ in native.calls if argv[3:5] == ["image", "save"]]) == int(
        modern
    )
    for capture in result["copies"].values():
        assert "retained_tar_gzip_sha256" in capture


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("layer-bytes", "product_save_content_bytes"),
        ("config-bytes", "product_save_content_bytes"),
        ("layer-order", "product_save_manifest_digest"),
        ("index-bool", "declared_data_type"),
        ("compat-tag", "declared_data_type"),
        ("duplicate-json", "duplicate_JSON_key"),
        ("extra", "product_save_inventory"),
        ("missing", "product_save_inventory"),
        ("duplicate", "product_save_inventory"),
        ("mode", "product_save_regular"),
        ("pax", "product_save_header"),
        ("symlink", "product_save_header"),
        ("trailer", "product_save_trailer"),
    ],
)
def test_native_import_rejects_saved_graph_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.archive_fault = fault
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0 and native.loaded
    assert not any(argv[3:5] == ["image", "rm"] for argv, _, _ in native.calls)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("ID", "product_container_identity"),
        ("operand", "product_container_operand_mounts"),
        ("owner", "declared_data_value"),
        ("mount", "product_container_operand_mounts"),
        ("network", "declared_data_value"),
        ("descriptor", "declared_data_value"),
        ("command", "declared_data_length"),
    ],
)
def test_native_import_rejects_container_custody_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.custody_fault = fault
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert not any(argv[3] in ("cp", "start", "rm") for argv, _, _ in native.calls)
    assert native.containers and native.loaded


@pytest.mark.parametrize(
    "label,after",
    [
        ("import-load", True),
        ("import-image", False),
        ("import-save", False),
        ("import-copy-create", True),
        ("import-copy-0", False),
        ("import-prometheus-version", True),
        ("import-promtool-version", True),
    ],
)
def test_native_import_preserves_primary_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str, after: bool
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.fail_label, native.fail_after_effect = label, after
    with pytest.raises(TimeoutError) as caught:
        _run_product_import(native, archive, graph, synthetic=False)
    assert caught.value is native.error and native.cleanup_starts == 1
    assert getattr(caught.value, "native_import_cleanup")
    if label in {"import-load", "import-image", "import-save", "import-copy-create"}:
        assert native.loaded
        assert not any(argv[3:5] == ["image", "rm"] for argv, _, _ in native.calls)
    else:
        assert not native.containers and not native.loaded


@pytest.mark.parametrize("primary", [False, True])
def test_native_import_cleanup_error_never_creates_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, primary: bool
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.cleanup_error = True
    if primary:
        native.fail_label = "import-copy-0"
        with pytest.raises(TimeoutError) as caught:
            _run_product_import(native, archive, graph)
        assert caught.value is native.error
        assert any("failure" in row for row in caught.value.native_import_cleanup)
    else:
        with pytest.raises(source.QualificationError, match="product_import_cleanup_failed"):
            _run_product_import(native, archive, graph)
    assert native.containers and native.loaded


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("preexisting", "product_preexisting_image_HOLD"),
        ("tag_collision", "native_import_tag_collision"),
        ("bad_id", "owned_create_full_ID"),
        ("bad_version", "native_candidate_version_revision_compiler"),
        ("bad_terminal", "product_container_completion"),
        ("survive", "product_import_cleanup_failed"),
        ("extra_tag", "product_import_cleanup_failed"),
    ],
)
def test_native_import_failed_lifecycle_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    setattr(native, fault, True)
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph, synthetic=False)
    if fault in {"preexisting", "tag_collision", "bad_id", "survive", "extra_tag"}:
        assert not any(argv[3:5] == ["image", "rm"] for argv, _, _ in native.calls)


@pytest.mark.parametrize("maximum", [0, -1, True, 4 * 1024**3 + 1])
def test_product_file_hash_rejects_invalid_explicit_maximum(tmp_path: Path, maximum: int) -> None:
    with pytest.raises(source.QualificationError, match="file_maximum_bound"):
        source.file_hash(tmp_path / "absent", maximum_bytes=maximum)


def test_product_file_hash_retains_default_bound_and_streams_explicit_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "saved"
    path.write_bytes(b"12345678")
    monkeypatch.setattr(source, "MAX_CACHE_BYTES", 4)
    with pytest.raises(source.QualificationError, match="file_byte_bound"):
        source.file_hash(path)
    assert source.file_hash(path, maximum_bytes=8) == source.sha(b"12345678")


@pytest.mark.parametrize(
    "label", ["import-inventory", "import-image-cleanup-inventory", "import-image-absence"]
)
def test_native_import_incomplete_inventory_is_not_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, label: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.inventory_fault = label
    diagnostic = (
        "product_inventory_terminal"
        if label == "import-inventory"
        else "product_import_cleanup_failed"
    )
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    if label == "import-inventory":
        assert not native.loaded and native.created_count == 0


@pytest.mark.parametrize(
    "fault,diagnostic",
    [("symlink", "nonregular_or_multilink_file"), ("extra", "product_save_output_inventory")],
)
def test_native_import_private_save_file_cannot_be_substituted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.save_file_fault = fault
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0 and native.loaded


def test_native_import_save_is_streamed_not_returned_as_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    original = Path.read_bytes

    def bounded_read(path: Path) -> bytes:
        assert path.name != "native.tar", "native save must not be read as a whole-image buffer"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", bounded_read)
    _run_product_import(native, archive, graph)
    save_call = next(row for row in native.calls if row[1] == "import-save")
    assert "watched_output" in save_call[2] and "output_bound" not in save_call[2]
    assert (native.evidence / "import-save.stdout").stat().st_size == 0
    assert (native.evidence / "import-save/native.tar").stat().st_size > 0


def test_native_import_running_version_timeout_removes_only_proven_full_ID(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.start_running_timeout = True
    with pytest.raises(TimeoutError) as caught:
        _run_product_import(native, archive, graph, synthetic=False)
    assert caught.value is native.error and not native.containers and not native.loaded
    forced = [argv for argv, _, _ in native.calls if argv[3:5] == ["rm", "--force"]]
    assert len(forced) == 1 and re.fullmatch(r"[0-9a-f]{64}", forced[0][-1])


def test_native_import_free_space_failure_precedes_save_and_create(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    observed = source.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(source.shutil, "disk_usage", lambda path: observed._replace(free=0))
    with pytest.raises(source.QualificationError, match="product_save_free_space_HOLD"):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0
    assert not any(argv[3:5] == ["image", "save"] for argv, _, _ in native.calls)


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("config", "declared_data_value"),
        ("layer-order", "declared_data_value"),
        ("layer-size", "declared_data_value"),
        ("bool-size", "declared_data_type"),
        ("layer-count", "declared_data_length"),
        ("media", "declared_data_value"),
        ("extra-key", "declared_data_keys"),
    ],
)
def test_native_import_hash_correct_manifest_must_still_bind_source_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    if fault == "config":
        native.manifest["config"]["digest"] = "sha256:" + "f" * 64
    elif fault == "layer-order":
        native.manifest["layers"].reverse()
    elif fault == "layer-size":
        native.manifest["layers"][0]["size"] += 1
    elif fault == "bool-size":
        native.manifest["config"]["size"] = True
    elif fault == "layer-count":
        native.manifest["layers"].pop()
    elif fault == "media":
        native.manifest["mediaType"] = source.OCI_MANIFEST
    else:
        native.manifest["unknown"] = "not admitted"
    native.manifest_raw = json.dumps(native.manifest, separators=(",", ":")).encode()
    native.engine = "sha256:" + source.sha(native.manifest_raw)
    native.descriptor.update(digest=native.engine, size=len(native.manifest_raw))
    native.image.update(Id=native.engine, RepoDigests=["pulseplate-prometheus@" + native.engine])
    # The raw manifest hashes to the observed engine and descriptor; source relation alone rejects.
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0 and native.loaded


@pytest.mark.parametrize("field", ["RootFS", "Descriptor"])
def test_native_import_inspect_cross_links_cannot_be_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    if field == "RootFS":
        native.image[field] = {"Type": "layers", "Layers": []}
        diagnostic = "declared_data_length"
    else:
        native.descriptor["annotations"]["org.opencontainers.image.ref.name"] = "foreign"
        diagnostic = "declared_data_value"
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0


@pytest.mark.parametrize("repository", ["caddy", "registry.invalid:5000/caddy", "<none>"])
@pytest.mark.parametrize("modern", [False, True])
def test_native_import_image_census_keeps_untagged_repository_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repository: str, modern: bool
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch, modern)
    # Docker29 emits repo:<none> for distinct IDs; the last field is its display sentinel.
    prefix = (
        "sha256:"
        + "c" * 64
        + "\t"
        + repository
        + ":<none>\n"
        + "sha256:"
        + "d" * 64
        + "\t"
        + repository
        + ":<none>\n"
    ).encode()
    native.image_inventory_prefix = prefix
    result = _run_product_import(native, archive, graph)
    assert result["image_config_id"] == graph["config_digest"]
    assert native.image_inventory_prefix == prefix and not native.loaded
    removals = [argv for argv, _, _ in native.calls if argv[3:5] == ["image", "rm"]]
    assert removals == [
        ["/usr/bin/docker", "--config", str(tmp_path / "config"), "image", "rm", native.engine]
    ]


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("named-tag", "product_inventory_ambiguous_names"),
        ("sentinel-lookalike", "product_inventory_ambiguous_names"),
        ("duplicate-row", "product_inventory_rows"),
        ("short-id", "product_inventory_rows"),
    ],
)
def test_native_import_image_census_still_rejects_ambiguous_or_incomplete_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    tag = (
        "latest"
        if fault == "named-tag"
        else "<none>-other" if fault == "sentinel-lookalike" else "<none>"
    )
    first = "sha256:" + "c" * 64 + "\tcaddy:" + tag + "\n"
    second = "sha256:" + "d" * 64 + "\tcaddy:" + tag + "\n"
    if fault == "duplicate-row":
        second = first
    elif fault == "short-id":
        second = "sha256:short\tcaddy:<none>\n"
    native.image_inventory_prefix = (first + second).encode()
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert not any(
        argv[3] in ("load", "create", "cp", "start", "rm") for argv, _, _ in native.calls
    )


def test_native_import_image_census_retains_exact_candidate_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.image_inventory_prefix = (
        "sha256:"
        + "c" * 64
        + "\tpulseplate-prometheus:<none>\n"
        + "sha256:"
        + "d" * 64
        + "\tpulseplate-prometheus:<none>\n"
        + "sha256:"
        + "e" * 64
        + "\tpulseplate-prometheus:candidate\n"
    ).encode()
    with pytest.raises(source.QualificationError, match="native_import_tag_collision"):
        _run_product_import(native, archive, graph)
    assert not native.loaded and native.created_count == 0


def test_native_import_image_census_untagged_ID_remains_preexisting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.image_inventory_prefix = (
        native.engine + "\tcaddy:<none>\n" + "sha256:" + "d" * 64 + "\tcaddy:<none>\n"
    ).encode()
    with pytest.raises(source.QualificationError, match="product_preexisting_image_HOLD"):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0 and native.loaded
    assert not any(argv[3:5] == ["image", "rm"] for argv, _, _ in native.calls)


def test_native_import_image_census_does_not_relax_container_name_uniqueness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.container_inventory_prefix = (
        "c" * 64 + "\tforeign-container\n" + "d" * 64 + "\tforeign-container\n"
    ).encode()
    with pytest.raises(source.QualificationError, match="product_inventory_ambiguous_names"):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0


def test_native_import_full_ID_export_separates_tagged_live_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    with tarfile.open(fileobj=io.BytesIO(native.archive_bytes()), mode="r:") as exported:
        index_file = exported.extractfile("index.json")
        manifest_file = exported.extractfile("manifest.json")
        assert index_file is not None and manifest_file is not None
        index = json.loads(index_file.read())
        compatibility = json.loads(manifest_file.read())
        assert index["manifests"] == [
            {key: native.descriptor[key] for key in ("mediaType", "digest", "size")}
        ]
        assert compatibility[0]["RepoTags"] is None
    result = _run_product_import(native, archive, graph, synthetic=False)
    assert result["image_config_id"] == graph["config_digest"]
    for role in ("copy", "prometheus", "promtool"):
        actual = json.loads(
            (native.evidence / ("import-" + role + "-prestart.stdout")).read_bytes()
        )
        assert actual["ImageManifestDescriptor"] == {
            **native.descriptor,
            "platform": {"architecture": "amd64", "os": "linux"},
        }
        assert actual["Image"] == actual["Config"]["Image"] == native.engine
    saves = [argv for argv, _, _ in native.calls if argv[3:5] == ["image", "save"]]
    assert len(saves) == 1 and saves[0][-1] == native.engine


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        ("tagged-index", "declared_data_keys"),
        ("empty-index-annotations", "declared_data_keys"),
        ("compat-empty-tags", "declared_data_type"),
        ("compat-candidate", "declared_data_type"),
    ],
)
def test_native_import_full_ID_export_rejects_tagged_or_mixed_shapes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, diagnostic: str
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.archive_fault = fault
    with pytest.raises(source.QualificationError, match=diagnostic):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0 and native.loaded


def test_native_import_full_ID_export_does_not_relax_tagged_live_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    native, archive, graph = _product_import_fixture(tmp_path, monkeypatch)
    native.image["Descriptor"] = {
        key: native.descriptor[key] for key in ("mediaType", "digest", "size")
    }
    with pytest.raises(source.QualificationError, match="declared_data_keys"):
        _run_product_import(native, archive, graph)
    assert native.created_count == 0 and native.loaded


def _p062_retained_q_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, bytes], Path, dict[str, Any], Path, dict[str, Any]]:
    """Exercise the real two-replay producer with inert native transport, then its reader.

    The independent reader never receives this producer's in-memory report or
    owned-container mapping. Small fixture locks replace content parameters only.
    """
    import difflib

    root, work = tmp_path / "checkout", tmp_path / "prometheus-source-502-1"
    root.mkdir()
    work.mkdir()
    evidence, go, config = work / "evidence", work / "go", work / "docker-config"
    for path in (evidence, go / "bin", config):
        path.mkdir(parents=True)
    (go / "bin/go").write_bytes(b"inert compiler")
    epochs = {
        version: {name: (version + " " + name + "\n").encode() for name in ("go.mod", "go.sum")}
        for version in ("v0.58.0", "v0.60.0", "v0.62.0")
    }
    for constant, version in (
        ("LOCKS", "v0.58.0"),
        ("XNET060_INCUMBENT_LOCKS", "v0.60.0"),
        ("DERIVED_LOCKS", "v0.62.0"),
    ):
        monkeypatch.setattr(
            source, constant, {key: source.sha(raw) for key, raw in epochs[version].items()}
        )
    patch = b"".join(
        b"".join(
            difflib.diff_bytes(
                difflib.unified_diff,
                epochs["v0.58.0"][name].splitlines(keepends=True),
                epochs["v0.62.0"][name].splitlines(keepends=True),
                fromfile=("a/" + name).encode(),
                tofile=("b/" + name).encode(),
            )
        )
        for name in ("go.mod", "go.sum")
    )
    monkeypatch.setattr(source, "XNET062_PATCH_SHA256", source.sha(patch))
    coordinates = {
        "source_head": "a" * 40,
        "run_id": 501,
        "artifact_id": 601,
        "artifact_name": "prometheus-oras-501-1",
        "artifact_digest": "sha256:" + "1" * 64,
        "binary_sha256": "2" * 64,
        "binary_bytes": 10,
        "input_digest": "sha256:" + "3" * 64,
    }
    manifest = {
        "schema": source.IMAGE_SCHEMA,
        "phase": "source_prepared",
        "inputs": source.declared_inputs(),
        "selection": None,
        "candidate": None,
    }
    manifest["inputs"]["oras"]["retained"] = coordinates
    for name in source.PRODUCER_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            source.finite_recipe() if name.endswith("Containerfile") else b"inert producer bytes"
        )
    (root / source.MANIFEST_PATH).write_bytes(source.canonical_data(manifest))
    ui = {
        "generated_paths": [name + ".gz" for name in sorted(source.UI_FILES)],
        "embed_sha256": "e" * 64,
        "gzip_source_sha256": "f" * 64,
        "python": "synthetic interpreter",
        "zlib_build": "synthetic",
        "zlib_runtime": "synthetic",
        "algorithm": "Python GzipFile filename-empty mtime0 level6 OS255; not GNU gzip byte equality",
    }

    def populate(path: Path) -> None:
        path.mkdir()
        for name, raw in epochs["v0.58.0"].items():
            (path / name).write_bytes(raw)
        (path / "fixed.go").write_bytes(b"inert source\n")

    def extract(artifact: Any, archive: Path, target: Path, deadline: float) -> list[Any]:
        populate(target)
        return []

    monkeypatch.setattr(source, "extract", extract)
    monkeypatch.setattr(source, "stage_ui", lambda *args: copy.deepcopy(ui))
    populate(work / "source")
    owned: dict[str, dict[str, Any]] = {}
    removed: set[str] = set()
    image = _native_fixed_base_image()

    class Transcript(source.Native):
        def run(
            self, argv: list[str], name: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            if argv[0] == "/usr/bin/docker":
                command = argv[3]
                if command == "ps":
                    raw = "".join(n + "\n" for n in owned if n not in removed).encode()
                elif command == "pull":
                    raw = b"synthetic pull\n"
                elif command == "image":
                    raw = json.dumps([image]).encode()
                elif command == "create":
                    raw = source.sha(name.encode()).encode() + b"\n"
                else:
                    container_name, expected = next(
                        (n, v)
                        for n, v in owned.items()
                        if n == argv[-1] or v.get("container_id") == argv[-1]
                    )
                    if command == "rm":
                        removed.add(container_name)
                        raw = expected["container_id"].encode() + b"\n"
                    elif command == "start":
                        guest = expected["command"]
                        raw = (
                            source.CURRENT_GO_VERSION.encode()
                            if guest == ["version"]
                            else (
                                b"all modules verified\n"
                                if guest == ["mod", "verify"]
                                else package_stream(guest[-1].split("/")[-1])
                            )
                        )
                    else:
                        assert command == "inspect"
                        actual = {
                            "Id": expected["container_id"],
                            "Name": "/" + container_name,
                            "Image": image["Id"],
                            "Config": {
                                "Image": image["Id"],
                                "Labels": {source.LABEL: expected["owner"]},
                                "User": "65532:65532",
                                "WorkingDir": "/src",
                                "Entrypoint": ["/usr/local/go/bin/go"],
                                "Cmd": expected["command"],
                                "Env": [k + "=" + v for k, v in expected["environment"].items()],
                            },
                            "HostConfig": {
                                "NetworkMode": "none",
                                "ReadonlyRootfs": True,
                                "Privileged": False,
                                "NanoCpus": 2000000000,
                                "Memory": 4294967296,
                                "PidsLimit": 128,
                                "CapDrop": ["ALL"],
                                "CapAdd": None,
                                "SecurityOpt": ["no-new-privileges"],
                                "Tmpfs": {str(source.GUEST_TMP): source.GUEST_TMPFS},
                            },
                            "Mounts": [
                                {"Type": "bind", "RW": False, "Destination": k, "Source": v}
                                for k, v in expected["mounts"].items()
                            ],
                            "State": {"Running": False, "ExitCode": 0, "OOMKilled": False},
                        }
                        raw = json.dumps([actual]).encode()
            else:
                command = argv[1:]
                version = (cwd / "go.mod").read_text().split()[0]
                modules = Path(env["GOMODCACHE"])
                directory = modules / ("xnet@" + version)
                if command[0] == "get":
                    version = command[-1].split("@")[-1]
                    for key, data in epochs[version].items():
                        (cwd / key).write_bytes(data)
                    raw = b""
                elif command == ["version"]:
                    raw = source.CURRENT_GO_VERSION.encode()
                elif command == ["mod", "edit", "-json"]:
                    raw = json.dumps(
                        {"Module": {"Path": source.ROOT_MODULE}, "Go": "1.26.0"}
                    ).encode()
                elif command == ["mod", "download", "-json"]:
                    directory.mkdir(exist_ok=True)
                    (directory / "go.mod").write_bytes(b"inert cache")
                    raw = json.dumps(
                        {
                            "Path": "golang.org/x/net",
                            "Version": version,
                            "Dir": str(directory),
                            "GoMod": str(directory / "go.mod"),
                        }
                    ).encode()
                elif command == ["mod", "verify"]:
                    raw = b"all modules verified\n"
                elif command == ["list", "-m", "-json", "all"]:
                    values = [
                        {
                            "Path": source.ROOT_MODULE,
                            "Main": True,
                            "Dir": str(cwd),
                            "GoMod": str(cwd / "go.mod"),
                        },
                        {"Path": "golang.org/x/net", "Version": version, "Dir": str(directory)},
                    ]
                    raw = b"\n".join(json.dumps(v).encode() for v in values)
                else:
                    assert command == ["mod", "graph"]
                    raw = (source.ROOT_MODULE + " golang.org/x/net@" + version + "\n").encode()
            (evidence / (name + ".stdout")).write_bytes(raw)
            (evidence / (name + ".stderr")).write_bytes(b"")
            self.records.append(
                {
                    "argv": list(argv),
                    "environment": dict(env),
                    "cwd": str(cwd),
                    "exit": 0,
                    "failure": None,
                    "stdout": str(evidence / (name + ".stdout")),
                    "stderr": str(evidence / (name + ".stderr")),
                    "stdout_sha256": source.sha(raw),
                    "stderr_sha256": source.sha(b""),
                }
            )
            return raw

    native = Transcript(evidence, time.monotonic() + 900, 120)
    docker_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "DOCKER_CONFIG": str(config),
        "LANG": "C.UTF-8",
    }
    qualified = {
        "run": {
            "id": 502,
            "head_sha": "b" * 40,
            "head_branch": source.P062_REF[11:],
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
        },
        "job": {"id": 702},
    }
    report = {
        "source_revision": source.REVISION,
        "source_tree": source.TREE,
        "UI_transform": ui,
        "heavy_build_invocations": 0,
        "publication_commands": 0,
        "automatic_retries": 0,
        "failure": None,
        "interruptions": [],
        "retained_tool": coordinates,
        "admission": {
            "run_id": 502,
            "head": "b" * 40,
            "ref": source.P062_REF,
            "workflow_id": 199904435,
            "job": "prometheus-source-qualification",
            "job_id": 702,
            "pr_number": 2494,
            "producer_epoch": "xnet062",
        },
        "producer": {
            str(root / n): source.file_hash(root / n)
            for n in (source.PRODUCER_FILES[0], source.PRODUCER_FILES[1])
        },
        "acquisition": [
            {
                "artifact": v.name,
                "public_source": v.url,
                "bytes": v.size,
                "sha256": v.digest,
                "explicit_release_handoff": v.release,
                "final_redirects": 0,
            }
            for v in (source.SOURCE, source.CURRENT_GO, source.UI, source.CHECKSUMS)
        ],
    }
    source.derive_xnet_observe(
        native,
        work,
        work / "downloads",
        work / "source",
        go,
        work / "ui",
        owned,
        "/usr/bin/docker",
        config,
        docker_env,
        report,
        target_version="v0.62.0",
    )
    native.begin_cleanup()
    report["cleanup"] = source.cleanup_owned(
        native, "/usr/bin/docker", config, owned, docker_env, work
    )
    report["native_operations"] = native.records
    source._finalize_xnet062_report(
        report, native, owned, "/usr/bin/docker", config, derive_completed=True
    )
    return (
        {p.name: p.read_bytes() for p in evidence.iterdir()},
        root,
        qualified,
        work,
        {"config": {"config": image["Config"]}},
    )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "fullF",
        "job",
        "retained",
        "producer",
        "native-secret",
        "mount",
        "resource",
        "full-ID",
        "raw-rehash",
        "cache-mode",
        "missing-slot",
        "cleanup",
        "extra-command",
        "path",
    ],
)
def test_p062_independent_retained_reader_rejects_rebound_false_native_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    files, root, qualified, work, vendor = _p062_retained_q_fixture(tmp_path, monkeypatch)
    report = source.one_object(files["qualification.json"])
    if fault == "fullF":
        report["module_derivation"]["closure_disposition"] = "remediated"
    elif fault == "job":
        report["admission"]["job_id"] += 1
    elif fault == "retained":
        report["retained_tool"]["run_id"] += 1
    elif fault == "producer":
        report["producer"][str(root / source.PRODUCER_FILES[0])] = "e" * 64
    elif fault == "native-secret":
        report["native_operations"][0]["environment"]["GH_TOKEN"] = "synthetic-secret"
    elif fault == "path":
        work = work.parent / "prometheus-source-999-1"
    elif fault == "extra-command":
        report["native_operations"].append(copy.deepcopy(report["native_operations"][-1]))
    elif fault == "cleanup":
        report["cleanup"][-1]["native_absent"] = False
    elif fault == "missing-slot":
        report["module_derivation"]["replays"][1]["offline"]["full_native_package_members"].pop(
            "promtool"
        )
    elif fault == "cache-mode":
        binding = report["module_derivation"]["replays"][0]["incumbent_reconstruction"]["offline"][
            "cache_mode_restoration"
        ]["files_restored_member"]
        rows = json.loads(files[binding["member"]])
        rows[0]["mode"] ^= 0o200
        raw = source.canonical_data(rows) + b"\n"
        files[binding["member"]] = raw
        binding.update(bytes=len(raw), sha256=source.sha(raw))
    elif fault in ("mount", "resource", "full-ID", "raw-rehash"):
        name = (
            "a-incumbent-offline-prometheus-inspect.stdout"
            if fault != "raw-rehash"
            else "a-derived-selected.stdout"
        )
        objects = (
            source.decode_objects(files[name]) if fault == "raw-rehash" else json.loads(files[name])
        )
        if fault == "mount":
            objects[0]["Mounts"][0]["Source"] = "/foreign"
        elif fault == "resource":
            objects[0]["HostConfig"]["Memory"] = 0
        elif fault == "full-ID":
            objects[0]["Id"] = objects[0]["Id"][:12]
        else:
            objects[1]["Version"] = "v0.60.0"
        raw = (
            json.dumps(objects).encode()
            if fault != "raw-rehash"
            else b"\n".join(json.dumps(v).encode() for v in objects)
        )
        files[name] = raw
        next(r for r in report["native_operations"] if r["stdout"].endswith("/" + name))[
            "stdout_sha256"
        ] = source.sha(raw)
    files["qualification.json"] = source.canonical_data(report)
    archive = tmp_path / "Q.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for name, raw in files.items():
            output.writestr(name, raw)
    # Deliberately replace the serializer checker with a trap: it cannot supply admission.
    monkeypatch.setattr(
        source, "_check_xnet062_report", lambda *args, **kwargs: pytest.fail("circular reader")
    )
    args = {
        "producer_root": root,
        "artifact_digest": "sha256:" + source.file_hash(archive),
        "qualified": qualified,
        "qualification_root": work,
        "vendor_base": vendor,
    }
    if fault is None:
        locks = source.qualification_locks(archive, **args)
        assert locks == {n: ("v0.62.0 " + n + "\n").encode() for n in ("go.mod", "go.sum")}
        assert len(report["native_operations"]) == 171
    else:
        with pytest.raises(source.QualificationError):
            source.qualification_locks(archive, **args)


def _p062_stage_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, purpose: str
) -> tuple[Any, Path]:
    """API-only native boundary fixtures; no actual GitHub call or producer action."""
    root = tmp_path / "checkout"
    root.mkdir()
    head = ("a" if purpose == "tool" else "b") * 40
    current_id = {"tool": 501, "qualification": 502, "pair": 503}[purpose]
    for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": source.GHCR_REPOSITORY,
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": str(current_id),
        "GITHUB_REF": source.P062_REF,
        "GITHUB_SHA": head,
        "RUNNER_OS": "Linux",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(source.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source.platform, "machine", lambda: "x86_64")
    manifest = {
        "schema": source.IMAGE_SCHEMA,
        "phase": "source_prepared",
        "inputs": source.declared_inputs(),
        "selection": None,
        "candidate": None,
    }
    p0 = source.canonical_data(manifest)
    if purpose != "tool":
        manifest["inputs"]["oras"]["retained"] = {
            "source_head": "a" * 40,
            "run_id": 501,
            "artifact_id": 601,
            "artifact_name": "prometheus-oras-501-1",
            "artifact_digest": "sha256:" + "1" * 64,
            "binary_sha256": "2" * 64,
            "binary_bytes": 10,
            "input_digest": "sha256:" + "3" * 64,
        }
    files = {
        name: source.finite_recipe() if name.endswith("Containerfile") else b"inert exact source\n"
        for name in source.PRODUCER_FILES
    }
    files[source.MANIFEST_PATH] = source.canonical_data(manifest)
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    originals = dict(files, **{source.MANIFEST_PATH: p0})
    runs, jobs = {}, {}
    for row in source.P062_SPENT_HISTORY:
        (
            rid,
            jid,
            name,
            revision,
            branch,
            attempt,
            run_status,
            run_end,
            job_status,
            job_end,
            start,
            end,
        ) = row
        runs[rid] = {
            "id": rid,
            "head_sha": revision,
            "head_branch": branch,
            "run_attempt": attempt,
            "status": run_status,
            "conclusion": run_end,
            "event": "workflow_dispatch",
            "workflow_id": 199904435,
            "repository": {"id": 1043311030},
            "head_repository": {"id": 1043311030},
        }
        jobs.setdefault(rid, []).append(
            {
                "id": jid,
                "name": name,
                "head_sha": revision,
                "run_attempt": attempt,
                "run_id": rid,
                "status": job_status,
                "conclusion": job_end,
                "started_at": start,
                "completed_at": end,
            }
        )
    for selected in ("tool", "qualification", "pair"):
        rid = {"tool": 501, "qualification": 502, "pair": 503}[selected]
        if rid > current_id:
            continue
        revision = ("a" if selected == "tool" else "b") * 40
        live = rid == current_id
        runs[rid] = {
            "id": rid,
            "head_sha": revision,
            "head_branch": source.P062_REF[11:],
            "run_attempt": 1,
            "status": "in_progress" if live else "completed",
            "conclusion": None if live else "success",
            "event": "workflow_dispatch",
            "workflow_id": 199904435,
            "repository": {"id": 1043311030},
            "head_repository": {"id": 1043311030},
        }
        jobs[rid] = [
            {
                "id": rid + 200,
                "run_id": rid,
                "head_sha": revision,
                "name": source.P062_JOB_NAMES[selected],
                "run_attempt": 1,
                "status": "in_progress" if live else "completed",
                "conclusion": None if live else "success",
                "started_at": f"2026-11-07T0{rid - 500}:00:00Z",
                "completed_at": None if live else f"2026-11-07T0{rid - 500}:01:00Z",
            }
        ]
        if selected == "qualification":
            jobs[rid].append({**jobs[rid][0], "id": 799, "name": source.P062_COMPANION})

    class API:
        deadline = time.monotonic() + 60

        def __init__(self) -> None:
            self.runs, self.jobs, self.files, self.originals = runs, jobs, files, originals
            self.pr = {
                "number": 2494,
                "state": "open",
                "merged": False,
                "commits": 2,
                "head": {"sha": head, "ref": source.P062_REF[11:], "repo": {"id": 1043311030}},
                "base": {"sha": "c" * 40, "ref": "main", "repo": {"id": 1043311030}},
            }
            self.graph = [
                {"sha": "a" * 40, "parents": []},
                {"sha": "b" * 40, "parents": [{"sha": "a" * 40}]},
            ]

        def source_files(self, revision: str, names: tuple[str, ...]) -> dict[str, bytes]:
            return dict(
                self.originals if revision == "a" * 40 and purpose != "tool" else self.files
            )

        def json(self, endpoint: str) -> dict[str, Any]:
            if endpoint.endswith("/pulls/2494"):
                return copy.deepcopy(self.pr)
            if "/compare/" in endpoint:
                return {
                    "base_commit": {"sha": "a" * 40},
                    "merge_base_commit": {"sha": "a" * 40},
                    "status": "ahead",
                    "behind_by": 0,
                    "total_commits": 1,
                    "ahead_by": 1,
                    "commits": [self.graph[1]],
                }
            if endpoint.endswith("/actions/workflows/build.yml"):
                return {"id": 199904435, "path": ".github/workflows/build.yml"}
            if "/jobs?" in endpoint:
                return {
                    "total_count": len(self.jobs[int(endpoint.split("/runs/")[1].split("/")[0])])
                }
            if "workflow_dispatch" in endpoint:
                return {"total_count": len(self.runs)}
            return copy.deepcopy(self.runs[int(endpoint.rsplit("/", 1)[-1])])

        def pages(self, endpoint: str, key: str | None, total: int) -> list[dict[str, Any]]:
            if endpoint.endswith("/commits"):
                rows = self.graph
            elif key == "workflow_runs":
                rows = list(self.runs.values())
            else:
                rows = self.jobs[int(endpoint.split("/runs/")[1].split("/")[0])]
            assert len(rows) == total
            return copy.deepcopy(rows)

    return API(), root


@pytest.mark.parametrize("purpose", ["tool", "qualification", "pair"])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing-history",
        "changed-history",
        "duplicate-job",
        "extra-spent",
        "retry",
        "foreign",
        "source-drift",
        "phase",
        "prior-output",
        "same-P0",
        "graph",
        "raw-P0",
        "inputs-P0",
        "chronology",
        "failed-companion",
    ],
)
def test_p062_stage_prefix_is_finite_authenticated_and_nonrenewable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, purpose: str, fault: str | None
) -> None:
    api, root = _p062_stage_fixture(tmp_path, monkeypatch, purpose)
    current_id = int(source.os.environ["GITHUB_RUN_ID"])
    if fault == "missing-history":
        api.jobs[38170923494].clear()
    elif fault == "changed-history":
        api.jobs[38170923494][0]["conclusion"] = "success"
    elif fault == "duplicate-job":
        api.jobs[current_id].append(copy.deepcopy(api.jobs[current_id][0]))
    elif fault == "extra-spent":
        api.runs[600] = {
            **api.runs[current_id],
            "id": 600,
            "status": "completed",
            "conclusion": "success",
        }
        api.jobs[600] = [
            {
                **api.jobs[current_id][0],
                "id": 900,
                "run_id": 600,
                "status": "completed",
                "conclusion": "success",
            }
        ]
    elif fault == "retry":
        monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    elif fault == "foreign":
        api.pr["head"]["repo"]["id"] = 1
    elif fault == "source-drift":
        api.files[source.PRODUCER_FILES[0]] += b" drift"
    elif fault == "phase":
        value = json.loads(api.files[source.MANIFEST_PATH])
        value["phase"] = "candidate_selected"
        api.files[source.MANIFEST_PATH] = source.canonical_data(value)
        (root / source.MANIFEST_PATH).write_bytes(api.files[source.MANIFEST_PATH])
    elif fault == "prior-output":
        value = json.loads(api.files[source.MANIFEST_PATH])
        value["selection"] = {"guessed": True}
        api.files[source.MANIFEST_PATH] = source.canonical_data(value)
        (root / source.MANIFEST_PATH).write_bytes(api.files[source.MANIFEST_PATH])
    elif fault in ("same-P0", "graph", "raw-P0", "inputs-P0", "chronology") and purpose != "tool":
        if fault == "same-P0":
            api.runs[501]["head_sha"] = "b" * 40
            api.jobs[501][0]["head_sha"] = "b" * 40
        elif fault == "graph":
            api.graph[1]["parents"] = []
        elif fault == "raw-P0":
            api.originals[source.PRODUCER_FILES[1]] += b" changed"
        elif fault == "inputs-P0":
            value = json.loads(api.originals[source.MANIFEST_PATH])
            value["inputs"]["source"]["version"] = "other"
            api.originals[source.MANIFEST_PATH] = source.canonical_data(value)
        else:
            api.jobs[501][0]["completed_at"] = "2027-11-07T01:01:00Z"
    elif fault == "failed-companion" and purpose == "pair":
        api.jobs[502][1]["conclusion"] = "failure"
    elif fault is not None:
        # These are meaningful predecessor checks only after the first T stage.
        with pytest.raises(
            source.QualificationError, match="p062_explicit_owner_no_retry_selector"
        ):
            source.manual_hosted_admission(
                api, purpose, producer_root=root, prefetch_predecessor="spent"
            )
        return
    if fault is None:
        result = source.manual_hosted_admission(api, purpose, producer_root=root)
        assert result["run_id"] == current_id and result["producer_epoch"] == "xnet062"
        assert result["pr_number"] == 2494 and result["budget"] == (2 if purpose == "pair" else 1)
    else:
        with pytest.raises(source.QualificationError):
            source.manual_hosted_admission(api, purpose, producer_root=root)


@pytest.mark.parametrize(
    "fault", ["stop-after-close", "admission", "retained", "close", "primary-and-close"]
)
def test_p062_qualification_authentication_finishes_before_native_or_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    api, root = _p062_stage_fixture(tmp_path, monkeypatch, "qualification")
    work = tmp_path / "Q"
    trace: list[str] = []
    monkeypatch.setattr(
        source,
        "producer_paths",
        lambda: (root / source.PRODUCER_FILES[0], root / source.PRODUCER_FILES[1]),
    )
    monkeypatch.setattr(source.shutil, "which", lambda name: "/usr/bin/docker")
    if fault == "admission":
        api.jobs[38170923494].clear()

    class PrivateAPI:
        def __init__(self, private: Path, evidence: Path, deadline: float, cleanup: int) -> None:
            trace.append("open")
            private.mkdir()
            self.private = private
            self.deadline = deadline

        def json(self, path: str) -> dict[str, Any]:
            return api.json(path)

        def pages(self, path: str, key: str | None, count: int) -> list[dict[str, Any]]:
            return api.pages(path, key, count)

        def source_files(self, revision: str, names: tuple[str, ...]) -> dict[str, bytes]:
            return api.source_files(revision, names)

        def close(self) -> None:
            trace.append("close")
            self.private.rmdir()
            if fault in ("close", "primary-and-close"):
                raise source.QualificationError("synthetic_cleanup_error")

    def retained(reader: Any, producer: Path, destination: Path) -> tuple[Path, dict[str, Any]]:
        trace.append("retained")
        assert reader.private.is_dir() and producer == root and destination == work
        if fault in ("retained", "primary-and-close"):
            raise source.QualificationError("synthetic_retained_error")
        return work / "oras", {
            "coordinates": source.read_image_manifest(
                root / source.MANIFEST_PATH, preparation=True
            )["inputs"]["oras"]["retained"]
        }

    def acquire(*args: Any, **kwargs: Any) -> None:
        trace.append("acquire")
        assert trace == ["open", "retained", "close", "acquire"]
        assert not (work / "GitHub-private").exists()
        raise source.QualificationError("synthetic_post_auth_stop")

    monkeypatch.setattr(source, "GitHubRead", PrivateAPI)
    monkeypatch.setattr(source, "retained_tool", retained)
    monkeypatch.setattr(source, "acquire", acquire)
    monkeypatch.setattr(source, "CLEANING", False)
    monkeypatch.setattr(source, "INTERRUPTIONS", [])
    expected = {
        "stop-after-close": "synthetic_post_auth_stop",
        "admission": "declared_data_length",
        "retained": "synthetic_retained_error",
        "close": "synthetic_cleanup_error",
        "primary-and-close": "synthetic_retained_error",
    }[fault]
    with pytest.raises(source.QualificationError, match=expected):
        source.qualify(work, 1800, 120, derive_xnet062=True)
    assert "close" in trace and ("acquire" in trace) == (fault == "stop-after-close")
    assert not (work / "GitHub-private").exists()
    report = source.one_object((work / "evidence/qualification.json").read_bytes())
    assert report["failure"]["code"] == expected
    assert report["native_operations"] == [] and report["heavy_build_invocations"] == 0
    if fault in ("close", "primary-and-close"):
        assert report["authentication_cleanup_failure"]["code"] == "synthetic_cleanup_error"


def test_p062_epochs_and_prepared_manifest_have_no_future_outputs(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    # The checked-out manifest may later be the valid P1 or P2 successor.
    source.read_image_manifest(root / source.MANIFEST_PATH, preparation=True)
    p0 = tmp_path / "manifest.json"
    p0.write_bytes(
        source.canonical_data(
            {
                "schema": source.IMAGE_SCHEMA,
                "phase": "source_prepared",
                "inputs": source.declared_inputs(),
                "selection": None,
                "candidate": None,
            }
        )
    )
    manifest = source.read_image_manifest(p0, preparation=True)
    assert manifest["phase"] == "source_prepared"
    assert manifest["selection"] is None and manifest["candidate"] is None
    assert manifest["inputs"]["oras"]["retained"] is None
    assert manifest["inputs"]["source"]["derived_locks"] == {
        "go.mod": "6e2dfa8d25b5cd3da5513334134e63549aff7e70915958f98893893c825d609e",
        "go.sum": "673bf9d73e667b94aa125f5ac3987bfb4a26b7ccbe1b0e51e7de030bc45fcce5",
    }
    assert source.declared_inputs(historical_xnet060=True)["source"]["derived_locks"] == {
        "go.mod": "d85af091d5bf9ba19f98e4d92e24b368d3e5537af086521ef10c7dd669695fd7",
        "go.sum": "eaeb5e4f16a9edcab1aeeb2b1a90a0f85decbd0065b3bf63e03729d324f7fc1f",
    }
    assert len(source.P062_SPENT_HISTORY) == 19
    assert {
        name: sum(row[2] == name for row in source.P062_SPENT_HISTORY)
        for name in (
            "prometheus-oras-qualification",
            "prometheus-source-qualification",
            "prometheus-source-build-pair",
            source.P062_COMPANION,
        )
    } == {
        "prometheus-oras-qualification": 7,
        "prometheus-source-qualification": 5,
        "prometheus-source-build-pair": 4,
        source.P062_COMPANION: 3,
    }
    assert source.P062_SPENT_HISTORY[-1][:2] == (40384356149, 121788589461)


@pytest.mark.parametrize(
    "fault", [None, "failed-run", "duplicate-Q", "wrong-head", "expired-context"]
)
def test_p062_pair_resolves_exact_successful_Q_on_same_P1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    api, root = _p062_stage_fixture(tmp_path, monkeypatch, "pair")
    original_json, original_pages = api.json, api.pages
    calls: list[int] = []
    if fault == "failed-run":
        api.runs[502]["conclusion"] = "failure"
    elif fault == "duplicate-Q":
        api.runs[504] = {**api.runs[502], "id": 504}
        api.jobs[504] = [{**api.jobs[502][0], "id": 704, "run_id": 504}]
    elif fault == "wrong-head":
        api.runs[502]["head_sha"] = "c" * 40
    elif fault == "expired-context":
        api.runs[502]["status"] = "in_progress"
    artifacts = {
        502: [{"id": 602, "name": "prometheus-source-qualification-502-1"}],
        504: [{"id": 604, "name": "prometheus-source-qualification-504-1"}],
    }

    def json_api(endpoint: str) -> dict[str, Any]:
        if endpoint.split("?", 1)[0].endswith("/artifacts"):
            return {"total_count": 1}
        return original_json(endpoint)

    def pages(endpoint: str, key: str | None, count: int) -> list[dict[str, Any]]:
        if key == "artifacts":
            return artifacts[int(endpoint.split("/runs/")[1].split("/")[0])]
        return original_pages(endpoint, key, count)

    def acquire(reader: Any, artifact: int, destination: Path, **kwargs: Any) -> dict[str, Any]:
        assert reader is api and artifact == 602
        assert kwargs == {
            "expected_run": 502,
            "expected_job": "prometheus-source-qualification",
            "expected_head": "b" * 40,
        }
        calls.append(artifact)
        return {"run": api.runs[502], "artifact": artifacts[502][0], "job": api.jobs[502][0]}

    api.json, api.pages = json_api, pages
    monkeypatch.setattr(source, "authenticated_artifact", acquire)
    admission = {
        "ref": source.P062_REF,
        "head": "b" * 40,
        "run_id": 503,
        "producer_epoch": "xnet062",
    }
    if fault is None:
        assert (
            source._current_qualification_artifact(api, root, admission, tmp_path / "q.zip")["run"][
                "id"
            ]
            == 502
        )
        assert calls == [602]
    else:
        with pytest.raises(source.QualificationError):
            source._current_qualification_artifact(api, root, admission, tmp_path / "q.zip")
        assert not calls


@pytest.mark.parametrize(
    "fault", [None, "source-selected", "source-output", "source-input", "raw-workflow"]
)
def test_p062_output_receiver_requires_prepared_P1_and_equal_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from tests.test_deploy_contract_scripts import _synthetic_prometheus_manifest

    api, root = _p062_stage_fixture(tmp_path, monkeypatch, "qualification")
    prepared = json.loads(api.files[source.MANIFEST_PATH])
    selected = _synthetic_prometheus_manifest()
    selected["inputs"] = copy.deepcopy(prepared["inputs"])
    selected["candidate"]["producer"]["pr_number"] = 2494
    selected["candidate"]["producer"]["source_ref"] = source.P062_REF
    selected["candidate"]["producer"]["source_head"] = "b" * 40
    (root / source.MANIFEST_PATH).write_bytes(source.canonical_data(selected))
    if fault == "source-selected":
        prepared["phase"] = "candidate_selected"
    elif fault == "source-output":
        prepared["selection"] = {"unproved": True}
    elif fault == "source-input":
        prepared["inputs"]["source"]["derived_locks"] = dict(source.XNET060_INCUMBENT_LOCKS)
    elif fault == "raw-workflow":
        api.files[source.PRODUCER_FILES[1]] += b" drift"
    api.files[source.MANIFEST_PATH] = source.canonical_data(prepared)
    if fault is None:
        assert source.authenticate_producer_inputs(api, root, "b" * 40)
    else:
        with pytest.raises(source.QualificationError):
            source.authenticate_producer_inputs(api, root, "b" * 40)

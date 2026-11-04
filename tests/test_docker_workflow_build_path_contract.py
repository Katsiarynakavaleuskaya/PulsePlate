"""Regression guards for the Docker workflow build-path consolidation contract."""

from __future__ import annotations

import ast
from copy import deepcopy
from datetime import date
from dataclasses import replace
from email.message import Message
from hashlib import sha256, sha3_256
from io import BytesIO
import json
import os
import shlex
import shutil
import stat
from ssl import SSLCertVerificationError
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import HTTPHandler, HTTPSHandler, Request
from urllib.response import addinfourl

from fastapi.testclient import TestClient
import pytest
import yaml

from scripts.ci import fetch_docker_source_artifacts as docker_sources

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
BACKEND_PYTHON_BASE_IMAGE = (
    "python:3.13.14-slim-bookworm"
    "@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64"
)
EXPECTED_BACKEND_PYTHON_FROM_LINES = (
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS builder",
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS sqlite-builder",
    f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
)
EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS = {
    ("build.yml", "build", "Build Docker image (local, for tests)"),
    ("build.yml", "publish", "Build Docker image for publish scan"),
    ("trivy.yml", "build", "Build Docker image (production target)"),
    ("cd.yml", "build", "Build & Push backend image (staging)"),
    ("cd.yml", "build-production", "Build & Push image (production)"),
}


@pytest.fixture(autouse=True)
def historical_alertmanager_selection(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from tests.test_deploy_contract_scripts import _historical_AM_scan_oracle

    current = json.loads(json.dumps(docker_sources._ALERT_ACCEPTED_CANDIDATE))
    assert current is None or isinstance(current, dict)
    current_oracle = json.loads(json.dumps(docker_sources._ALERT_CURRENT_SCAN_ORACLE))
    monkeypatch.setattr(
        docker_sources,
        "_ALERT_ACCEPTED_CANDIDATE",
        json.loads(json.dumps(docker_sources._ALERT_HISTORICAL_C10)),
    )
    monkeypatch.setattr(docker_sources, "_ALERT_CURRENT_SCAN_ORACLE", _historical_AM_scan_oracle())
    return {"accepted": current, "scan": current_oracle}


def test_current_selected_images_match_live_identity_consumers(
    historical_alertmanager_selection: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cross-bind actual selected data before any historical fixture substitution."""
    from tests import test_notify_premium_alias_checkpoint_failure as native

    selected = historical_alertmanager_selection["accepted"]
    oracle = historical_alertmanager_selection["scan"]
    with monkeypatch.context() as current:
        current.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", selected)
        current.setattr(docker_sources, "_ALERT_CURRENT_SCAN_ORACLE", oracle)
        if selected is None:
            from scripts.ci.prometheus_source_image import QualificationError, read_image_manifest

            with pytest.raises(QualificationError, match="UNCONFIGURED_HOLD"):
                docker_sources._alertmanager_accepted_producer()
            manifest_path = REPO_ROOT / "deploy/prometheus/image-manifest.json"
            manifest = read_image_manifest(manifest_path, preparation=True)
            assert manifest["phase"] == "source_prepared"
            assert manifest["selection"] is manifest["candidate"] is None
            with pytest.raises(QualificationError, match="^source_prepared_not_consumable$"):
                read_image_manifest(manifest_path)
            return
        assert docker_sources._alertmanager_accepted_producer() == selected
        runtime_ref, config_id = docker_sources._alertmanager_contract_subject()
        assert native.ALERTMANAGER_IMAGE == runtime_ref
        assert native._ACCEPTED_AM_BINARIES == oracle["subject"]["binary_sha256"]
        assert config_id == selected["graph"]["config"]["digest"] == oracle["subject"]["config"]
        assert Path(native.__file__).read_text().count(config_id) == 1
        for path in docker_sources._ALERT_SELECTION_FILES[:3]:
            model = yaml.safe_load((REPO_ROOT / path).read_text())
            assert model["services"]["alertmanager"]["image"] == runtime_ref
        cd = _load_workflow(WORKFLOWS_DIR / "cd.yml")
        jobs = cd["jobs"]
        assert isinstance(jobs, dict)
        candidate_env = jobs["alertmanager-retained-candidate"]["env"]
        assert {
            name: candidate_env[name]
            for name in ("AM_CANDIDATE_RUN", "AM_CANDIDATE_ARTIFACT", "AM_CANDIDATE_SOURCE")
        } == {
            "AM_CANDIDATE_RUN": str(selected["run"]),
            "AM_CANDIDATE_ARTIFACT": str(selected["artifact"]),
            "AM_CANDIDATE_SOURCE": selected["source"],
        }
        tuple_text = (
            f"--alertmanager-candidate-run {selected['run']} "
            f"--alertmanager-candidate-artifact {selected['artifact']}"
        )
        source_text = f"--alertmanager-candidate-source {selected['source']}"
        for workflow, expected_count in (("ci.yml", 1), ("cd.yml", 3)):
            raw = (WORKFLOWS_DIR / workflow).read_text()
            assert raw.count(tuple_text) == raw.count(source_text) == expected_count
            for kind, run_id, artifact_id in (
                ("qualification", 40379971373, 12677328773),
                ("support", 40383803043, 12679243318),
            ):
                selector = (
                    f"--alertmanager-{kind}-run {run_id} "
                    f"--alertmanager-{kind}-artifact {artifact_id}"
                )
                assert raw.count(selector) == expected_count
                assert (
                    raw.count(f"--alertmanager-{kind}-source {selected['source']}")
                    == expected_count
                )
        for name in ("alertmanager", "amtool"):
            assert oracle["expected_modules"][name]["stdlib"] == "v1.27.3"


@pytest.mark.parametrize("tool_selected", [False, True], ids=["without-tool", "with-tool"])
def test_source_prepared_tool_selection_preserves_image_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool_selected: bool
) -> None:
    """Real preparation parsing accepts tool metadata without claiming artifact or image admission."""
    from scripts.ci import prometheus_source_image as source

    manifest = json.loads((REPO_ROOT / source.MANIFEST_PATH).read_text())
    manifest.update(phase="source_prepared", selection=None, candidate=None)
    coordinates = {
        "source_head": "1" * 40,
        "run_id": 1,
        "artifact_id": 2,
        "artifact_name": "prometheus-oras-1-1",
        "artifact_digest": "sha256:" + "2" * 64,
        "binary_sha256": "3" * 64,
        "binary_bytes": 1,
        "input_digest": "sha256:" + "4" * 64,
    }
    manifest["inputs"]["oras"]["retained"] = coordinates if tool_selected else None
    path = tmp_path / "image-manifest.json"
    path.write_text(json.dumps(manifest))

    assert source.read_image_manifest(path, preparation=True) == manifest
    with pytest.raises(source.QualificationError, match="^source_prepared_not_consumable$"):
        source.read_image_manifest(path)
    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", None)
    with pytest.raises(source.QualificationError, match="^AM_accepted_producer_UNCONFIGURED_HOLD$"):
        docker_sources._alertmanager_accepted_producer()

    if tool_selected:
        malformed = deepcopy(manifest)
        malformed["inputs"]["oras"]["retained"]["run_id"] = True
        path.write_text(json.dumps(malformed))
        with pytest.raises(source.QualificationError, match="^tool_retained_positive_integer$"):
            source.read_image_manifest(path, preparation=True)


def test_historical_AM_fixture_copy_does_not_change_current_selection(
    historical_alertmanager_selection: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.test_deploy_contract_scripts import (
        _historical_AM_scan_oracle,
        _historical_AM_source,
        _historical_AM_template,
    )

    selected = historical_alertmanager_selection["accepted"]
    oracle = historical_alertmanager_selection["scan"]
    with monkeypatch.context() as current:
        current.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", selected)
        current.setattr(docker_sources, "_ALERT_CURRENT_SCAN_ORACLE", oracle)
        original = Path(docker_sources.__file__).read_bytes()
        copied = _historical_AM_source()
        main_guard = b'\nif __name__ == "__main__":\n'
        prefix, suffix = original.split(main_guard)
        assert copied.startswith(prefix)
        assert copied.endswith(main_guard + suffix)
        fixture = copied[len(prefix) : -len(main_guard + suffix)]
        assert b"_ALERT_ACCEPTED_CANDIDATE = _ALERT_HISTORICAL_C10" in fixture
        historical = _historical_AM_scan_oracle()
        assert (
            historical["subject"]["config"]
            == docker_sources._ALERT_HISTORICAL_C10["graph"]["config"]["digest"]
        )
        assert historical["expected_OS"]["OS"] == oracle["expected_OS"]["OS"]
        historical_os = {row[3]: row for row in historical["expected_OS"]["packages"]}
        current_os = {row[3]: row for row in oracle["expected_OS"]["packages"]}
        assert set(historical_os) == set(current_os)
        assert {name for name in historical_os if historical_os[name] != current_os[name]} == {
            "ca-certificates",
            "tzdata",
            "tzdata-legacy",
        }
        assert historical_os["ca-certificates"][4] == "20250419"
        assert current_os["ca-certificates"][4] == "20250419+deb13u1"
        for name in ("tzdata", "tzdata-legacy"):
            assert historical_os[name][4] == "2026c"
            assert current_os[name][4] == "2026e"
        for name in ("alertmanager", "amtool"):
            assert historical["expected_modules"][name]["stdlib"] == "v1.27.2"
            assert {
                key: value
                for key, value in historical["expected_modules"][name].items()
                if key != "stdlib"
            } == {
                key: value
                for key, value in oracle["expected_modules"][name].items()
                if key != "stdlib"
            }
        old_ref = (
            "ghcr.io/katsiarynakavaleuskaya/pulseplate@"
            + docker_sources._ALERT_HISTORICAL_C10["graph"]["manifest"]["digest"]
        ).encode()
        from tests import test_notify_premium_alias_checkpoint_failure as native

        current_ref = native.ALERTMANAGER_IMAGE.encode()
        for path in docker_sources._ALERT_SELECTION_FILES[:3]:
            actual = (REPO_ROOT / path).read_bytes()
            assert actual.count(current_ref) == 1
            assert _historical_AM_template(REPO_ROOT / path) == actual.replace(
                current_ref, old_ref, 1
            )
        assert Path(docker_sources.__file__).read_bytes() == original
        assert docker_sources._ALERT_ACCEPTED_CANDIDATE == selected
        assert docker_sources._ALERT_CURRENT_SCAN_ORACLE == oracle


@pytest.mark.parametrize("support_only", [False, True])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing-history",
        "extra-history",
        "duplicate-job",
        "prior-source",
        "prior-attempt",
        "prior-active",
        "foreign-PR",
        "current-job",
        "current-ref",
    ],
)
def test_current_alertmanager_manual_admission_preserves_history_and_owner(
    monkeypatch: pytest.MonkeyPatch, support_only: bool, fault: str | None
) -> None:
    """Native totals are deliberately not inferred from these synthetic API job rows."""
    records = [
        (39048899349, 117443160727, "6c9f537e89d38f82f8d685150a32e25aee14c6c7", "failure"),
        (39052648330, 117454182747, "2e28d62f4311930f1caeabb5378af3e1d3c1e1a1", "failure"),
        (39059505765, 117474381581, "917854fb7832d7a980c8e6a8ee85940fd2e7724f", "failure"),
        (39067589451, 117498357173, "45409a39ce06804d4cbb5dce6c7dbb61a85167c8", "failure"),
        (39072367157, 117512436494, "bf5b6a9053c9b42727834ffd6966f45e4a493062", "failure"),
        (39077538191, 117527703920, "9d849ab2128aa0a2ff7c065fcc47fdc36a771b1d", "failure"),
        (39084669786, 117548630619, "557b66bf9287feadc68b9916f41f1f471bee9e49", "failure"),
        (39093991413, 117576475833, "91bf3744fcc5f5bbdfdd6e08699d703db46a491f", "failure"),
        (39099358458, 117592265589, "8a00dc7fe7c754c6801dc5c19f1772546ed8696e", "failure"),
        (39143039135, 117721196331, "63455b8a750ef07a1e525078b4e3ce2089eecdde", "success"),
        (40237598500, 121302388554, "04b76f42c09854405df00328ead16b30d701a24f", "success"),
    ]
    branch, head = "codex/python-setup-security-stabilization", "a" * 40
    runs = [
        {
            "id": run,
            "head_sha": source,
            "head_branch": (
                branch if run == 40237598500 else "codex/dependency-alertmanager-remediation"
            ),
            "run_attempt": 1,
            "status": "completed",
            "conclusion": outcome,
            "event": "workflow_dispatch",
            "workflow_id": 99,
            "repository": {"id": 1043311030},
            "head_repository": {"id": 1043311030},
        }
        for run, _, source, outcome in records
    ]
    jobs = {
        run: [
            {
                "id": job,
                "run_id": run,
                "head_sha": source,
                "name": "alertmanager-candidate-build",
                "status": "completed",
                "conclusion": outcome,
            }
        ]
        for run, job, source, outcome in records
    }
    current = {
        "id": 999,
        "head_sha": head,
        "head_branch": branch,
        "workflow_id": 99,
        "event": "workflow_dispatch",
        "run_attempt": 1,
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
        {
            "id": 1999,
            "run_id": 999,
            "head_sha": head,
            "status": "in_progress",
            "name": (
                "alertmanager-input-inspection" if support_only else "alertmanager-candidate-build"
            ),
        }
    ]
    if fault == "missing-history":
        runs.pop()
    elif fault == "extra-history":
        runs.append({**runs[-1], "id": 888})
        jobs[888] = [{**jobs[records[-1][0]][0], "run_id": 888, "id": 1888}]
    elif fault == "duplicate-job":
        jobs[records[0][0]].append(dict(jobs[records[0][0]][0]))
    elif fault == "prior-source":
        runs[0]["head_sha"] = "b" * 40
    elif fault == "prior-attempt":
        runs[0]["run_attempt"] = 2
    elif fault == "prior-active":
        runs[0]["status"] = "in_progress"
    elif fault == "foreign-PR":
        pr["head"]["repo"]["id"] = 1
    elif fault == "current-job":
        jobs[999][0]["head_sha"] = "b" * 40

    class API:
        calls: list[str] = []

        def json(self, endpoint: str) -> dict[str, Any]:
            self.calls.append(endpoint)
            if endpoint.endswith("/workflows/cd.yml"):
                return {"id": 99, "path": ".github/workflows/cd.yml"}
            if endpoint.endswith("/runs/999"):
                return current
            if endpoint.endswith("/pulls/2497"):
                return pr
            return {"total_count": len(runs) + 1 if "/workflows/" in endpoint else 1}

        def pages(self, endpoint: str, key: str, count: int) -> list[dict[str, Any]]:
            self.calls.append(endpoint)
            if key == "workflow_runs":
                return [*runs, current]
            return jobs[int(endpoint.split("/runs/")[1].split("/")[0])]

    for key, value in {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "999",
        "GITHUB_SHA": head,
        "GITHUB_REF": "refs/heads/" + ("unrelated" if fault == "current-ref" else branch),
    }.items():
        monkeypatch.setenv(key, value)
    api = API()
    relevant = fault in {"foreign-PR", "current-job", "current-ref"} or (
        fault is not None and not support_only
    )
    if relevant:
        with pytest.raises(RuntimeError, match="AM_current_build"):
            docker_sources._alertmanager_current_manual_admission(
                api, head, support_only=support_only
            )
    else:
        docker_sources._alertmanager_current_manual_admission(api, head, support_only=support_only)
    if support_only:
        assert not any("runs?event=" in path for path in api.calls)


@pytest.mark.parametrize("fault", [None, "credentials", "qualification", "pair", "security"])
def test_current_alertmanager_build_orders_real_input_seams_and_retains_spent_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alertmanager_proposal_environment: None,
    fault: str | None,
) -> None:
    """Synthetic adapters exercise order/retention only; no compiler or native acceptance claim."""
    from scripts.ci import prometheus_source_image as transport

    head = "a" * 40
    monkeypatch.setenv("GITHUB_SHA", head)
    events: list[str] = []
    sources = {
        path: (REPO_ROOT / path).read_bytes()
        for path in (
            *docker_sources._ALERT_Q_SOURCE_FILES,
            "tests/test_notify_premium_alias_checkpoint_failure.py",
        )
    }

    class API:
        def __init__(self, private: Path, *args: Any) -> None:
            self.private = private
            private.mkdir()

        def _capture(self, *args: Any, **kwargs: Any) -> bytes:
            return (head + "\n").encode()

        def close(self) -> None:
            events.append("credentials-closed")
            if fault != "credentials":
                self.private.rmdir()

    monkeypatch.setattr(transport, "GitHubRead", API)
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_current_manual_admission",
        lambda *a: events.append("admission"),
    )
    monkeypatch.setattr(docker_sources, "_alertmanager_source_snapshot", lambda *a: sources)

    def inputs(
        api: API, source: str, target: Path, *, kind: str, source_files: dict[str, str]
    ) -> dict[str, Any]:
        assert source == head and source_files == {
            key: sha256(sources[key]).hexdigest() for key in docker_sources._ALERT_Q_SOURCE_FILES
        }
        events.append(kind)
        target.write_bytes(b"synthetic archive")
        return {
            "source": source,
            "run": 1,
            "artifact": 2,
            "zip_sha256": "b" * 64,
            "source_files": source_files,
        }

    monkeypatch.setattr(docker_sources, "_alertmanager_current_inputs", inputs)
    monkeypatch.setattr(docker_sources, "_alertmanager_package_read", lambda *a: {})

    def qualification(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert events[-1] == "credentials-closed" and kwargs["current"] is True
        if fault == "qualification":
            raise RuntimeError("synthetic-qualified-input-rejection")
        return {
            "plan": {
                "UI_file_hashes": {"synthetic": "c" * 64},
                "assembly_argv": [
                    "--build-context",
                    transport.BASE
                    + "=oci-layout:///inputs/base-layout@<UNOBSERVED_CURRENT_EXPORT>",
                ],
            }
        }

    monkeypatch.setattr(docker_sources, "_alertmanager_qualified_payload", qualification)
    support = {
        "probe": {},
        "base": {"actual_local_OCI_descriptor": {"digest": "sha256:" + "b" * 64}},
        "scanner": {"DB": {"synthetic": "d" * 64}},
        "base_scan": {},
        "probe_scan": {},
    }
    monkeypatch.setattr(docker_sources, "_alertmanager_support_payload", lambda *a, **k: support)
    monkeypatch.setattr(
        docker_sources, "_alertmanager_materialize", lambda *a: events.append("materialized")
    )

    def pair(
        inputs: Path,
        supported: Path,
        plan: dict[str, Any],
        work: Path,
        result: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        assert events[-1] == "materialized"
        assert kwargs["base_descriptor"] == support["base"]["actual_local_OCI_descriptor"]
        assert plan["assembly_argv"] == [
            "--build-context",
            transport.BASE + "=oci-layout:///inputs/base-layout@sha256:" + "b" * 64,
        ]
        events.append("one-pair")
        result.update(
            compiler_starts=1 if fault == "pair" else 2,
            logical_build_starts=1,
            graph={},
            build_information={},
        )
        if fault == "pair":
            raise RuntimeError("synthetic-partial-compiler-failure")
        work.mkdir()
        (work / "candidate.oci.tar").write_bytes(b"synthetic OCI")

    def security(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["support_report"] is support
        events.append("security")
        if fault == "security":
            raise RuntimeError("synthetic-security-failure")
        return {"synthetic_control_only": True}

    monkeypatch.setattr(docker_sources, "_alertmanager_pair", pair)
    monkeypatch.setattr(docker_sources, "_alertmanager_final_security", security)

    def native(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs == {"producer_image": True}
        events.append("native")
        return {"synthetic_control_only": True}

    monkeypatch.setattr(docker_sources, "_alertmanager_native_candidate", native)
    monkeypatch.setattr(
        docker_sources, "_alertmanager_retain_execution", lambda *a: events.append("retained")
    )
    monkeypatch.setattr(
        docker_sources, "_alertmanager_finalize_payload", lambda *a: events.append("footer")
    )
    output = tmp_path / "current-build"
    args = docker_sources.parse_args(
        [
            "--artifact",
            "alertmanager",
            "--alertmanager-stage",
            "build",
            "--source-sha",
            head,
            "--output-dir",
            str(output),
        ]
    )
    if fault is None:
        docker_sources._alertmanager_current_build(args)
    else:
        with pytest.raises(RuntimeError):
            docker_sources._alertmanager_current_build(args)
    observed = json.loads((output / "retained/candidate-observation.json").read_text())
    assert events[-2:] == ["retained", "footer"]
    assert events.count("one-pair") == (0 if fault in {"credentials", "qualification"} else 1)
    assert observed["compiler_starts"] == (
        0 if fault in {"credentials", "qualification"} else 1 if fault == "pair" else 2
    )
    assert ("failure" in observed) is (fault is not None)
    assert ("native" in events) is (fault is None)
    if fault is None:
        assert observed["status"] == "OBSERVED_PRODUCER_IMAGE_SECURITY"


@pytest.mark.parametrize("producer_image", [False, True])
@pytest.mark.parametrize("fault", [None, "opposite", "mixed", "missing", "duplicate"])
def test_alertmanager_native_bridge_keeps_producer_and_consumer_proof_disjoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alertmanager_proposal_environment: None,
    producer_image: bool,
    fault: str | None,
) -> None:
    """Mock process output tests marker binding, never execution or acceptance authority."""
    from scripts.ci import prometheus_source_image as transport

    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", None)
    image = "sha256:" + "a" * 64
    marker = (
        b"native_AM_producer_image_controls=pass"
        if producer_image
        else b"native_AM_full_candidate_controls=pass"
    )
    opposite = (
        b"native_AM_full_candidate_controls=pass"
        if producer_image
        else b"native_AM_producer_image_controls=pass"
    )
    raw = marker
    if fault == "opposite":
        raw = opposite
    elif fault == "mixed":
        raw += b"\n" + opposite
    elif fault == "missing":
        raw = b"no terminal result"
    elif fault == "duplicate":
        raw += b"\n" + marker

    class Native:
        def __init__(self, *args: Any) -> None:
            self.records: list[dict[str, Any]] = []

        def run(self, argv: list[str], label: str, *args: Any, **kwargs: Any) -> bytes:
            if label == "native-load-retained-OCI":
                return b""
            if label == "native-retained-image":
                return json.dumps({"Id": image, "RootFS": {"Layers": []}}).encode()
            assert label == "full-AM-native"
            assert ("--alertmanager-producer-image" in argv) is producer_image
            return raw

    monkeypatch.setattr(transport, "Native", Native)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_docker_load_transport",
        lambda *a: {"load_input": str(tmp_path / "synthetic.tar")},
    )
    observation = tmp_path / "candidate-observation.json"
    observation.write_text("{}")
    work = tmp_path / "native"
    candidate = {"graph": {"config": {"digest": image}, "diff_ids": []}}
    arguments = {"producer_image": producer_image}
    if fault is None:
        result = docker_sources._alertmanager_native_candidate(
            candidate, observation, work, docker_sources._alertmanager_limits(), **arguments
        )
        assert result["validation_scope"] == (
            "producer_image" if producer_image else "selected_consumer"
        )
    else:
        with pytest.raises(RuntimeError, match="AM_native_full_terminal_missing"):
            docker_sources._alertmanager_native_candidate(
                candidate, observation, work, docker_sources._alertmanager_limits(), **arguments
            )
    assert docker_sources._ALERT_ACCEPTED_CANDIDATE is None
    with pytest.raises(RuntimeError, match="AM_accepted_producer_UNCONFIGURED_HOLD"):
        docker_sources._alertmanager_accepted_producer()


def test_finite_backend_exports_follow_credential_cleanup_and_do_not_publish() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    job = workflow["jobs"]["build"]
    assert job["permissions"] == {"actions": "read", "contents": "read"}
    production = _step_by_name(job, "Build Docker image (local, for tests)")
    staging = _step_by_name(job, "Build staging image from the same qualified backend inputs")
    assert production["with"]["target"] == "production"
    assert staging["with"]["target"] == "staging"
    for step in (production, staging):
        assert step["with"]["push"] is False and step["with"]["load"] is True
        assert step["with"]["platforms"] == "linux/amd64"
        assert (
            step["with"]["build-args"]
            == "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt\n"
        )
        assert "pp_netrc=${{ runner.temp }}/pulseplate-docker-netrc" in step["with"]["secret-files"]
    export_name = "Retain exact production and staging native image bytes"
    assert (
        _step_index(job, production["name"])
        < _step_index(job, staging["name"])
        < _step_index(job, "Remove private Python index Docker authentication")
        < _step_index(job, export_name)
    )
    exported = _step_by_name(job, export_name)
    run = exported["run"]
    assert 'test ! -e "$RUNNER_TEMP/pulseplate-docker-netrc"' in run
    assert '[docker, "image", "save", "--output", str(archive), tag]' in run
    assert "again != observed" in run and '"archive_sha256": digest(archive)' in run
    assert "No registry publication or guest execution in this export step" in run
    assert "docker login" not in run and '"push"' not in run
    python_source = run.split("python3 - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    ast.parse(python_source)
    uploaded = _step_by_name(job, "Preserve exact backend native images for pullback qualification")
    assert (
        uploaded["if"]
        == "${{ always() && steps.backend-native-export.outputs.complete == 'true' }}"
    )


def test_finite_arm_sdk_origin_is_manual_canonical_static_and_not_tool_trust() -> None:
    from scripts.ci.install_locked_python_requirements import PSYCOPG_SDK_TARGETS

    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    job = workflow["jobs"]["backend-arm-sdk-qualification"]
    assert job["runs-on"] == "ubuntu-24.04-arm"
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    assert job["if"] == (
        "github.event_name == 'workflow_dispatch' && inputs.mode == 'backend-sdk-qualify' && "
        "github.repository == 'Katsiarynakavaleuskaya/PulsePlate' && github.repository_id == '1043311030'"
    )
    targets = [
        target
        for target in PSYCOPG_SDK_TARGETS
        if (target.machine, target.minor) == ("aarch64", 13)
    ]
    assert len(targets) == 1 and job["env"]["SDK_SOURCE_IMAGE"] == targets[0].source_image
    guard = _step_by_name(job, "Require one explicit genuine ARM SDK producer attempt")["run"]
    assert "test \"$GITHUB_RUN_ATTEMPT\" = '1'" in guard
    assert "test \"$GITHUB_REPOSITORY_ID\" = '1043311030'" in guard
    assert 'test "$(uname -m)" = aarch64' in guard
    acquisition = _step_by_name(job, "Prepare existing private acquisition credentials")
    assert acquisition["env"] == {
        "DEVPI_CI_USER": "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && secrets.DEVPI_CI_USER || '' }}",
        "DEVPI_CI_PASSWORD": "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && secrets.DEVPI_CI_PASSWORD || '' }}",
    }
    assert (
        'if [[ -z "${DEVPI_CI_USER:-}" && -z "${DEVPI_CI_PASSWORD:-}" ]]; then exit 0; fi'
        in acquisition["run"]
    )
    built = _step_by_name(job, "Build genuine ARM cp313 SDK using its existing target")
    assert built["with"]["target"] == "psycopg-sdk"
    assert built["with"]["platforms"] == "linux/arm64"
    assert built["with"]["push"] is False
    name = "Bind genuine SDK origin, image and exported payload bytes"
    assert (
        _step_index(job, built["name"])
        < _step_index(job, "Remove acquisition credentials before static SDK validation")
        < _step_index(job, name)
    )
    origin = _step_by_name(job, name)
    assert origin["env"] == {"SDK_BUILD_METADATA": "${{ steps.sdk-build.outputs.metadata }}"}
    run = origin["run"]
    assert 'read_psycopg_c_sdk(sdk / "psycopg-sdk", native_root=sdk)' in run
    assert "SDK image and local exporter bytes differ" in run
    assert "External clean supporting-tool-root admission" in run
    assert "# Static wheel/receipt/DSO recognition only. No supplied SDK library," in run
    assert '"--entrypoint", "/not-executed", image_id' in run
    python_source = run.split("python3 - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    ast.parse(python_source)
    assert python_source.count('json.loads(os.environ["SDK_BUILD_METADATA"])') == 1
    assert '"build_metadata": build_metadata' in python_source
    start = python_source.index('build_metadata = json.loads(os.environ["SDK_BUILD_METADATA"])')
    binding = python_source[start : python_source.index('name = "pp-sdk-export-', start)]
    child_source = (
        "import json, os, re\n"
        'docker = "/qualified/docker"\n'
        "def run(argv: list[str], name: str) -> bytes:\n"
        '    assert argv == [docker, "image", "inspect", "pulseplate-sdk:arm-cp313"]\n'
        '    assert name == "sdk-image"\n'
        '    return os.environ["NATIVE_SDK_INSPECT"].encode()\n'
        + binding
        + '\nprint("SDK binding complete")\n'
    )
    config = "sha256:" + "a" * 64
    manifest = "sha256:" + "b" * 64
    metadata: dict[str, object] = {
        "containerimage.config.digest": config,
        "containerimage.digest": manifest,
    }
    inspected = [{"Id": config, "Os": "linux", "Architecture": "arm64"}]
    cases: list[tuple[dict[str, object], list[dict[str, str]], str | None]] = [
        (metadata, inspected, None),
        (
            {"containerimage.digest": manifest},
            inspected,
            "SDK build metadata config digest missing or malformed",
        ),
        (
            metadata,
            [{**inspected[0], "Id": manifest}],
            "SDK image/config/platform mismatch",
        ),
    ]
    cases.extend(
        (
            {**metadata, "containerimage.config.digest": malformed},
            inspected,
            "SDK build metadata config digest missing or malformed",
        )
        for malformed in (None, "", "sha256:" + "a" * 63, "sha256:" + "A" * 64, 42)
    )
    for current_metadata, current_inspected, expected_error in cases:
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-c", child_source],
            env={
                "SDK_IMAGE_ID": "",
                "SDK_BUILD_METADATA": json.dumps(current_metadata),
                "NATIVE_SDK_INSPECT": json.dumps(current_inspected),
            },
            capture_output=True,
            timeout=10,
            check=False,
        )
        if expected_error is None:
            assert result.returncode == 0, result.stderr
            assert result.stdout == b"SDK binding complete\n"
        else:
            assert result.returncode != 0
            assert result.stderr.decode().strip() == expected_error


def _load_workflow(path: Path) -> dict[str, object]:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(workflow, dict)
    return workflow


def _step_names(job: dict[str, object]) -> list[str]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    names: list[str] = []
    for step in steps:
        assert isinstance(step, dict)
        name = step.get("name")
        if isinstance(name, str):
            names.append(name)
    return names


def _step_by_name(job: dict[str, object], step_name: str) -> dict[str, object]:
    steps = job.get("steps")
    assert isinstance(steps, list)
    for step in steps:
        assert isinstance(step, dict)
        if step.get("name") == step_name:
            return step
    raise AssertionError(f"missing step {step_name!r}")


def _step_index(job: dict[str, object], step_name: str) -> int:
    return _step_names(job).index(step_name)


def _root_context_docker_build_steps(
    workflow: dict[str, object],
) -> list[tuple[str, dict[str, object], str]]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_steps: list[tuple[str, dict[str, object], str]] = []
    for job_name, job in jobs.items():
        assert isinstance(job_name, str)
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            assert isinstance(step, dict)
            uses = step.get("uses")
            if not (isinstance(uses, str) and uses.startswith("docker/build-push-action@")):
                continue
            step_with = step.get("with")
            assert isinstance(
                step_with,
                dict,
            ), f"{job_name}/{step.get('name')} must define docker build inputs"
            context = step_with.get("context")
            if context != ".":
                # Frontend/Caddy builds do not consume the backend SQLite source bundle.
                continue
            step_name = step.get("name")
            assert isinstance(step_name, str)
            build_steps.append((job_name, job, step_name))
    return build_steps


def _docker_source_manifest(
    *,
    payload: bytes = b"sqlite source",
    review_by: str = "2026-06-28",
    filename: str = "sqlite-autoconf-3530200.tar.gz",
    url: str = "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
) -> dict[str, object]:
    digest = sha3_256(payload).hexdigest()
    return {
        "schema_version": 1,
        "generated_at": "2026-06-14",
        "review_by": review_by,
        "artifacts": [
            {
                "name": "sqlite-autoconf",
                "version": "3530200",
                "filename": filename,
                "url": url,
                "sha3_256_parts": [digest[index : index + 8] for index in range(0, len(digest), 8)],
            }
        ],
    }


def _write_docker_source_manifest(tmp_path: Path, manifest: dict[str, object]) -> Path:
    manifest_path = tmp_path / "docker_source_artifacts.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_removed_duplicate_docker_pr_workflows() -> None:
    """PR-time production image validation stays in the canonical Docker workflow."""
    assert not (WORKFLOWS_DIR / "docker-image.yml").exists()
    assert not (WORKFLOWS_DIR / "docker-openapi-smoke.yml").exists()


def test_build_workflow_owns_docker_validation_contract() -> None:
    """Build workflow keeps runtime, telemetry, budget, and OpenAPI smoke checks together."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    step_names = _step_names(build_job)

    assert "Build Docker image (local, for tests)" in step_names
    assert "Check Docker runtime dependency surface" in step_names
    assert "Collect Docker image telemetry" in step_names
    assert "Enforce Docker image budget" in step_names
    assert "Test Docker image" in step_names

    test_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Test Docker image"
    )
    build_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Build Docker image (local, for tests)"
    )
    build_step_with = build_step["with"]
    assert isinstance(build_step_with, dict)
    assert build_step_with["target"] == "production"
    assert build_step_with["load"] is True
    assert build_step_with["push"] is False
    assert build_step_with["provenance"] is False

    run_script = test_step["run"]
    assert isinstance(run_script, str)
    assert "openapi.json" in run_script
    assert "/api/v1/bmi" in run_script
    assert (
        'assert "/api/v1/bodyfat" not in paths, '
        '"/api/v1/bodyfat must not leak into canonical OpenAPI"'
    ) in run_script


def test_build_workflow_does_not_expose_github_token_to_pr_baseline_script() -> None:
    """PR builds must not pass workflow tokens to checked-out baseline code."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    steps = build_job["steps"]
    assert isinstance(steps, list)

    fallback_step = next(
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("name") == "Use checked-in Docker image telemetry baseline on pull requests"
    )
    assert fallback_step["if"] == "github.event_name == 'pull_request'"
    fallback_run = fallback_step["run"]
    assert isinstance(fallback_run, str)
    assert "fetch_docker_image_baseline.py" not in fallback_run
    assert "GH_TOKEN" not in fallback_step.get("env", {})
    assert "GITHUB_TOKEN" not in fallback_step.get("env", {})

    resolve_step = next(
        step
        for step in steps
        if isinstance(step, dict) and step.get("name") == "Resolve Docker image telemetry baseline"
    )
    assert resolve_step["if"] == "github.event_name != 'pull_request'"
    resolve_env = resolve_step["env"]
    assert isinstance(resolve_env, dict)
    assert resolve_env["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
    assert resolve_env["GITHUB_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"


def test_production_dockerfile_prunes_package_manager_surface() -> None:
    """Production target removes package-manager, gzip, ACL/attr, and Perl runtime packages."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    production_section = dockerfile.split("FROM runtime-base AS production", 1)[1]
    production_section = production_section.split("FROM production AS staging", 1)[0]
    pruning_block = production_section.split(
        "# SECURITY: production-package-pruning-start",
        1,
    )[
        1
    ].split("# SECURITY: production-package-pruning-end", 1)[0]

    assert "dpkg --purge --force-depends --force-remove-essential" in pruning_block
    assert "perl_module_packages=" in pruning_block
    assert "'perl-modules-*'" in pruning_block
    assert (
        "for package in apt gzip gpgv libacl1 libattr1 libgnutls30 "
        "libsqlite3-0 libpcre2-8-0 perl-base ${perl_module_packages} bsdutils libblkid1 libmount1 "
        "libsmartcols1 libuuid1 mount util-linux util-linux-extra libsystemd0 libudev1; do"
    ) in pruning_block
    for package in (
        "apt",
        "gzip",
        "gpgv",
        "libacl1",
        "libattr1",
        "libgnutls30",
        "libsqlite3-0",
        "libpcre2-8-0",
        "perl-base",
    ):
        assert f"        {package} \\" in pruning_block
        assert f" {package} " in pruning_block
    assert "dpkg-query -W -f='${db:Status-Abbrev}'" in pruning_block
    assert "for binary in gzip gunzip zcat" in pruning_block
    assert 'command -v "${binary}"' in pruning_block
    assert "import gzip" in pruning_block
    assert "gzip.compress(payload, mtime=0)" in pruning_block
    assert "import ssl" in pruning_block
    assert "import sqlite3" in pruning_block
    assert "expected >= 3.53.2" in pruning_block


def test_build_workflow_blocks_removed_acl_attr_runtime_packages() -> None:
    """Docker runtime surface guard fails if removed packages return."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)

    surface_step = _step_by_name(build_job, "Check Docker runtime dependency surface")
    run_script = surface_step["run"]
    assert isinstance(run_script, str)

    for package in ("gzip", "libacl1", "libattr1"):
        assert f"--blocked-debian-package {package}" in run_script


def test_dockerfile_pins_all_backend_python_stages_to_one_oci_index() -> None:
    """Runtime bases stay fixed; only the exact isolated SDK family varies."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    trivyignore = (REPO_ROOT / ".trivyignore").read_text(encoding="utf-8")
    python_from_lines = tuple(
        line.strip()
        for line in dockerfile.splitlines()
        if line.lstrip().casefold().startswith("from ") and "python" in line.casefold()
    )

    sdk_from_lines = (
        "FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS native-builder",
        "FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS psycopg-inputs",
        "FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS dev-bootstrap-inputs",
    )
    assert len(python_from_lines) == 6
    assert (
        tuple(line for line in python_from_lines if line not in sdk_from_lines)
        == EXPECTED_BACKEND_PYTHON_FROM_LINES
    )
    assert tuple(line for line in python_from_lines if line in sdk_from_lines) == sdk_from_lines
    assert "3.13.13" not in dockerfile
    assert f"FROM {BACKEND_PYTHON_BASE_IMAGE.partition('@')[0]} AS" not in dockerfile
    assert BACKEND_PYTHON_BASE_IMAGE.partition("@")[0] in trivyignore
    assert "3.13.13" not in trivyignore


@pytest.mark.parametrize(
    ("stage", "helpers"),
    (
        ("native-builder", ("fetch_docker_source_artifacts.py",)),
        (
            "psycopg-inputs",
            ("install_locked_python_requirements.py", "check_private_python_proxy_health.py"),
        ),
        ("psycopg-wheel-builder", ("install_locked_python_requirements.py",)),
        (
            "dev-bootstrap-inputs",
            ("install_locked_python_requirements.py", "check_private_python_proxy_health.py"),
        ),
        (
            "development",
            ("install_locked_python_requirements.py", "check_python_startup_hooks.py"),
        ),
    ),
)
def test_native_helper_stage_layout_executes_real_cli(
    tmp_path: Path, stage: str, helpers: tuple[str, ...]
) -> None:
    """Actual COPY layouts preserve helper roots and parse operations without acquisition."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    section = dockerfile.split(f" AS {stage}\n", 1)[1].split("\nFROM ", 1)[0]
    if stage == "psycopg-wheel-builder":
        assert "FROM native-builder AS psycopg-wheel-builder" in dockerfile
        parent = dockerfile.split(" AS native-builder\n", 1)[1].split("\nFROM ", 1)[0]
        section = parent + "\n" + section
    stage_root = tmp_path / stage
    staged: dict[str, Path] = {}
    for line in section.splitlines():
        if not line.startswith("COPY scripts/ci/"):
            continue
        tokens = shlex.split(line)
        destination = PurePosixPath(tokens[-1])
        for source in tokens[1:-1]:
            source_path = REPO_ROOT / source
            target = destination / source_path.name if tokens[-1].endswith("/") else destination
            assert target.parents[2] == PurePosixPath(
                "/tooling"
            ), "Native helper COPY lost the repository-root depth required by the real CLI"
            materialized = stage_root / target.relative_to("/")
            materialized.parent.mkdir(parents=True, exist_ok=True)
            materialized.write_bytes(source_path.read_bytes())
            staged[source_path.name] = materialized
    home = tmp_path / "empty-home"
    home.mkdir()
    environment = {"PATH": os.defpath, "HOME": str(home), "LANG": "C.UTF-8"}
    for name in helpers:
        result = subprocess.run(
            [sys.executable, str(staged[name]), "--help"],
            cwd=stage_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout
    installer = staged.get("install_locked_python_requirements.py")
    if installer is not None:
        operations = (
            (["--build-psycopg-c"], "Exact Psycopg build requires all four explicit inputs"),
            (
                ["--prefetch-psycopg-source", str(tmp_path / "source"), "--prefetch-only"],
                "Locked installer operation selectors are mutually exclusive.",
            ),
            (
                ["--prefetch-psycopg-build-wheels", str(tmp_path / "wheels"), "--prefetch-only"],
                "Locked installer operation selectors are mutually exclusive.",
            ),
        )
        for flags, expected_error in operations:
            result = subprocess.run(
                [
                    sys.executable,
                    str(installer),
                    "--index-url",
                    "https://packages.pulseplate.app/root/pulseplate/+simple/",
                    *flags,
                ],
                cwd=stage_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            assert result.returncode == 1
            assert expected_error in result.stdout, result.stdout + result.stderr
        assert not (tmp_path / "source").exists()
        assert not (tmp_path / "wheels").exists()


def test_ncurses_replacement_preserves_debian_versioned_consumers() -> None:
    """ABI6 keeps its symbol namespaces and checks actual consumers after pruning."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    configuration = dockerfile.split("cd /build/source/ncurses-6.6", 1)[1].split("make -j2", 1)[0]
    for option in ("--with-versioned-syms", "--with-abi-version=6", "--enable-widec"):
        assert option in configuration
    assert "--with-termlib=tinfo" in configuration
    source = dockerfile.split("<<'PY_NATIVE_TERMINAL'\n", 1)[1].split("\nPY_NATIVE_TERMINAL", 1)[0]
    assert dockerfile.index(
        "USER pulseplate", dockerfile.index("production-package-pruning-end")
    ) < (dockerfile.index("<<'PY_NATIVE_TERMINAL'"))
    assert 'run_checked_consumer(["/bin/bash", "--noprofile", "--norc"' in source
    assert 'for interpreter in ("/usr/local/bin/python", "/opt/venv/bin/python"):' in source
    assert "run_checked_consumer([interpreter" in source
    assert "curses.setupterm" in source and "import curses.panel" in source
    assert 'check_native_empty_panel_stack(ctypes.CDLL("libpanelw.so.6"))' in source
    assert "curses.panel.bottom_panel" not in source
    assert "readline.get_current_history_length" in source
    assert "actual_ncurses = ncurses.curses_version()" in source
    assert "linker.dlvsym(handle._handle, symbol, version)" in source
    for version in (
        "NCURSES6_TINFO_5.0.19991023",
        "NCURSESW6_5.1.20000708",
        "NCURSESW6_5.3.20021019",
    ):
        assert version in source
    assert 'Path("/proc/self/maps")' in source and "hashlib.sha256" in source
    assert "LD_LIBRARY_PATH" not in source and "LD_PRELOAD" not in source


@pytest.mark.parametrize(
    ("producer", "expected_exit", "diagnostic"),
    (
        ("print('ordinary terminal consumer')", 0, ""),
        (
            "import sys; sys.stderr.write('no version information available\\n')",
            1,
            "no version information available",
        ),
        (
            "import sys; sys.stderr.write('version NCURSES6_TINFO not found\\n')",
            1,
            "version NCURSES6_TINFO not found",
        ),
        ("raise SystemExit(2)", 1, "Native terminal consumer returned an error"),
        (
            "import sys; print('ordinary output'); sys.stderr.write('other diagnostic\\n')",
            1,
            "other diagnostic",
        ),
    ),
)
def test_real_terminal_consumer_adapter_rejects_diagnostics(
    tmp_path: Path, producer: str, expected_exit: int, diagnostic: str
) -> None:
    """Execute the shipped adapter with real child exits and stdout/stderr streams."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_TERMINAL'\n", 1)[1].split("\nPY_NATIVE_TERMINAL", 1)[0]
    parsed = ast.parse(source)
    declarations = ast.Module(
        body=[node for node in parsed.body if isinstance(node, (ast.Import, ast.FunctionDef))],
        type_ignores=[],
    )
    command = [sys.executable, "-c", producer]
    program = ast.unparse(declarations) + f"\nrun_checked_consumer({command!r})\n"
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    if diagnostic:
        assert diagnostic in result.stderr
    else:
        assert result.stdout == "ordinary terminal consumer\n"
        assert not result.stderr


@pytest.mark.parametrize("above,below,expected_exit", ((None, None, 0), (1, None, 1), (None, 1, 1)))
def test_native_panel_null_boundary_rejects_nonempty_results(
    tmp_path: Path, above: int | None, below: int | None, expected_exit: int
) -> None:
    """The shipped NULL-result checker rejects either unexpected panel pointer."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    wrapper = dockerfile.split("<<'PY_NATIVE_TERMINAL'\n", 1)[1].split("\nPY_NATIVE_TERMINAL", 1)[0]
    assignment = next(
        node
        for node in ast.parse(wrapper).body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "consumer_source"
            for target in node.targets
        )
    )
    assert isinstance(assignment.value, ast.Constant) and isinstance(assignment.value.value, str)
    helper = next(
        node
        for node in ast.parse(assignment.value.value).body
        if isinstance(node, ast.FunctionDef) and node.name == "check_native_empty_panel_stack"
    )
    source = "import ctypes\nimport types\n" + ast.unparse(helper)
    source += f"""
class SyntheticPanelOperation:
    def __init__(self, value):
        self.value = value
    def __call__(self, pointer):
        assert pointer is None
        assert self.argtypes == [ctypes.c_void_p] and self.restype is ctypes.c_void_p
        return self.value
panel = types.SimpleNamespace(panel_above=SyntheticPanelOperation({above!r}),
                              panel_below=SyntheticPanelOperation({below!r}))
check_native_empty_panel_stack(panel)
"""
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    if expected_exit:
        assert "Native panel empty-stack boundary returned a non-NULL panel" in result.stderr
    else:
        assert not result.stdout and not result.stderr


def test_native_shared_export_preserves_source_aliases_and_excludes_static_inputs(
    tmp_path: Path,
) -> None:
    """Real cp -a preserves the source SDK topology before directory-content COPY."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    section = dockerfile.split(" AS native-shared-runtime\n", 1)[1].split("\nFROM ", 1)[0]
    assert "RUN --network=none mkdir -p /native-shared-libraries" in section
    assert "cp -a /native/usr/local/lib/*.so* /native-shared-libraries/" in section
    assert (
        dockerfile.count(
            "COPY --from=native-shared-runtime /native-shared-libraries/ /usr/local/lib/"
        )
        == 2
    )
    assert "COPY --from=native-builder /native/usr/local/lib/*.so*" not in dockerfile
    source = tmp_path / "source"
    export = tmp_path / "export"
    source.mkdir()
    export.mkdir()
    payload = b"synthetic canonical shared DSO bytes"
    (source / "libpq.so.5.18").write_bytes(payload)
    for name in ("libpq.so", "libpq.so.5"):
        (source / name).symlink_to("libpq.so.5.18")
    (source / "libpq.a").write_bytes(b"static archive excluded")
    (source / "pkgconfig").mkdir()
    (source / "pkgconfig/libpq.pc").write_text("excluded package configuration")
    copy_binary = shutil.which("cp")
    assert copy_binary is not None
    result = subprocess.run(
        [copy_binary, "-a", *(str(path) for path in sorted(source.glob("*.so*"))), str(export)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert {path.name for path in export.iterdir()} == {"libpq.so", "libpq.so.5", "libpq.so.5.18"}
    assert (export / "libpq.so.5.18").is_file() and not (export / "libpq.so.5.18").is_symlink()
    for name in ("libpq.so", "libpq.so.5"):
        assert (export / name).is_symlink()
        assert (export / name).readlink() == Path("libpq.so.5.18")
        assert (export / name).read_bytes() == payload


@pytest.mark.parametrize(
    "scenario",
    ("canonical", "wrong_path", "extra_path", "flattened_alias", "absolute_alias", "wrong_hash"),
)
def test_libpq_lineage_guard_requires_exact_source_topology_and_bytes(
    tmp_path: Path, scenario: str
) -> None:
    """The shipped guard rejects valid-version libraries with the wrong source identity."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    assert 'psycopg.__version__ != "3.3.4"' in source
    assert 'pq.__impl__ != "c" or pq.version() != 180006' in source
    assert "OpenSSL 4.0.3" in source
    assert "Psycopg actual mapped libpq paths" in source
    assert "Psycopg source DSO hash" in source
    helper = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "check_libpq_lineage"
    )
    root = tmp_path / "native-lib"
    root.mkdir()
    canonical = root / "libpq.so.5.18"
    payload = b"synthetic reviewed canonical DSO"
    canonical.write_bytes(payload)
    for name in ("libpq.so", "libpq.so.5"):
        (root / name).symlink_to("libpq.so.5.18")
    loaded = [canonical]
    if scenario == "wrong_path":
        loaded = [tmp_path / "wrong-lib/libpq.so.5.18"]
    elif scenario == "extra_path":
        loaded.append(tmp_path / "extra-lib/libpq.so.5")
    elif scenario == "flattened_alias":
        (root / "libpq.so.5").unlink()
        (root / "libpq.so.5").write_bytes(payload)
    elif scenario == "absolute_alias":
        (root / "libpq.so.5").unlink()
        (root / "libpq.so.5").symlink_to(canonical)
    receipt = tmp_path / "sdk.json"
    receipt.write_text(
        json.dumps(
            {
                "native_libraries": {
                    "libpq.so.5": sha256(
                        b"different bytes" if scenario == "wrong_hash" else payload
                    ).hexdigest()
                }
            }
        )
    )
    program = "import hashlib, json\nfrom pathlib import Path\n" + ast.unparse(helper)
    program += (
        f"\ncheck_libpq_lineage({{Path(name) for name in {[str(path) for path in loaded]!r}}}, "
        f"Path({str(root)!r}), Path({str(receipt)!r}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == (0 if scenario == "canonical" else 1), result.stdout + result.stderr
    assert "Psycopg actual mapped libpq paths" in result.stdout
    if scenario in ("canonical", "wrong_hash"):
        assert "Psycopg source DSO hash" in result.stdout
    if scenario != "canonical":
        assert "Psycopg" in result.stderr


@pytest.mark.parametrize(
    "version_info,expected_exit",
    (
        ((3, 5, 0, 9, 0), 0),
        ((3, 5, 0, 8, 0), 1),
        ((3, 6, 0, 9, 0), 1),
        ((4, 0, 0, 9, 0), 1),
        ((3, 5, 9, 0, 0), 1),
        ((3, 5, 0, 9, 15), 1),
    ),
)
def test_runtime_openssl_guard_uses_openssl3_patch_field_and_release_status(
    tmp_path: Path, version_info: tuple[int, ...], expected_exit: int
) -> None:
    """Execute the shipped version guard against the public OpenSSL 3 tuple shape."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
            and node.value.args[0].value == "Loaded shared OpenSSL"
        )
        or (
            isinstance(node, ast.If)
            and "Psycopg runtime shared OpenSSL mismatch" in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    assert isinstance(statements[0], ast.Expr) and isinstance(statements[1], ast.If)
    program = (
        "import types\n"
        f"ssl = types.SimpleNamespace(OPENSSL_VERSION_INFO={version_info!r}, "
        "OPENSSL_VERSION='synthetic OpenSSL observation', OPENSSL_VERSION_NUMBER=0x30500090)\n"
        + "\n".join(ast.unparse(node) for node in statements)
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert repr(version_info) in result.stdout
    assert "synthetic OpenSSL observation" in result.stdout and "0x30500090" in result.stdout
    if expected_exit:
        assert "Psycopg runtime shared OpenSSL mismatch" in result.stderr
    else:
        assert not result.stderr


def test_dockerfile_builds_verified_sqlite_runtime_library() -> None:
    """Dockerfile builds pre-fetched SQLite 3.53.2 before removing Debian SQLite."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    sqlite_builder_section = dockerfile.split("AS sqlite-builder", 1)[1]
    sqlite_builder_section = sqlite_builder_section.split("FROM python", 1)[0]
    runtime_base_section = dockerfile.split(
        f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
        1,
    )[1]
    runtime_base_section = runtime_base_section.split("COPY --from=builder", 1)[0]

    assert 'ARG SQLITE_AUTOCONF_VERSION="3530200"' in dockerfile
    assert "SQLite source pins are intentionally mirrored" in dockerfile
    assert "Docker COPY source paths are literal" in dockerfile
    checksum_parts = (
        "025328da",
        "165109f4",
        "8abccc6e",
        "74785080",
        "60804412",
        "bed2bd81",
        "d47e98ba",
        "1b72983b",
    )
    for index, checksum_part in enumerate(checksum_parts, start=1):
        assert f'ARG SQLITE_AUTOCONF_SHA3_256_PART_{index}="{checksum_part}"' in dockerfile
    assert len("".join(checksum_parts)) == 64
    assert 'os.environ[f"SQLITE_AUTOCONF_SHA3_256_PART_{index}"]' in sqlite_builder_section
    assert "urlopen" not in sqlite_builder_section
    assert "urllib" not in sqlite_builder_section
    assert "https://sqlite.org" not in sqlite_builder_section
    assert "COPY build/docker-sources/sqlite-autoconf-3530200.tar.gz" in sqlite_builder_section
    assert "!build/docker-sources/sqlite-autoconf-*.tar.gz" in dockerignore
    assert "sha3_256(payload).hexdigest()" in sqlite_builder_section
    assert "SQLite source SHA3 mismatch" in sqlite_builder_section
    assert "./configure --prefix=/usr/local --disable-static --enable-shared" in dockerfile
    assert "COPY --from=sqlite-builder /usr/local/lib/libsqlite3.so*" in runtime_base_section
    assert "/etc/ld.so.conf.d/00-pulseplate-local-sqlite.conf" in runtime_base_section
    assert "ldconfig" in runtime_base_section
    assert "import sqlite3" in runtime_base_section
    assert "expected >= 3.53.2" in runtime_base_section


def test_docker_source_artifact_manifest_pins_sqlite_source() -> None:
    """Docker source-artifact manifest pins approved SQLite source with SHA3 parts."""
    manifest = json.loads(
        (REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text(encoding="utf-8")
    )
    artifacts = manifest["artifacts"]
    assert manifest["schema_version"] == 1
    assert manifest["generated_at"] == "2026-10-04"
    assert manifest["review_by"] == "2026-10-30"
    assert len(artifacts) == 17
    assert [row["name"] for row in artifacts[-2:]] == ["alertmanager-source", "alertmanager-ui"]
    assert [row["name"] for row in artifacts[:4]] == [
        "sqlite-autoconf",
        "util-linux",
        "pcre2",
        "sljit",
    ]
    for name in ("SQLite", "util-linux", "PCRE2", "SLJIT"):
        assert name in manifest["reason"]

    artifact = artifacts[0]
    parsed_url = urlparse(artifact["url"])
    assert artifact["name"] == "sqlite-autoconf"
    assert artifact["version"] == "3530200"
    assert artifact["filename"] == "sqlite-autoconf-3530200.tar.gz"
    assert parsed_url.scheme == "https"
    assert parsed_url.hostname == "sqlite.org"
    assert parsed_url.path == "/2026/sqlite-autoconf-3530200.tar.gz"
    assert artifact["sha3_256_parts"] == [
        "025328da",
        "165109f4",
        "8abccc6e",
        "74785080",
        "60804412",
        "bed2bd81",
        "d47e98ba",
        "1b72983b",
    ]
    assert len("".join(artifact["sha3_256_parts"])) == 64


def test_docker_source_artifact_manifest_review_window_is_inclusive(tmp_path: Path) -> None:
    """Keep historical review cutoffs and prove current October 30/31 admission."""
    manifest_path = REPO_ROOT / "scripts/ci/docker_source_artifacts.json"
    historical = json.loads(manifest_path.read_text())
    historical["generated_at"] = "2026-09-28"
    historical["review_by"] = "2026-10-05"
    old_path = _write_docker_source_manifest(tmp_path, historical)
    assert len(docker_sources.load_manifest(old_path, today=date(2026, 10, 5))) == 15
    with pytest.raises(RuntimeError, match="review_by is stale: 2026-10-05"):
        docker_sources.load_manifest(old_path, today=date(2026, 10, 6))
    previous = json.loads(manifest_path.read_text())
    previous["review_by"] = "2026-10-21"
    previous_path = _write_docker_source_manifest(tmp_path, previous)
    assert len(docker_sources.load_manifest(previous_path, today=date(2026, 10, 21))) == 15
    with pytest.raises(RuntimeError, match="review_by is stale: 2026-10-21"):
        docker_sources.load_manifest(previous_path, today=date(2026, 10, 22))
    for day in (6, 8, 21, 30):
        assert len(docker_sources.load_manifest(manifest_path, today=date(2026, 10, day))) == 15
    alertmanager = docker_sources.load_manifest(
        manifest_path, today=date(2026, 10, 30), artifact="alertmanager"
    )
    assert len(alertmanager) == 2
    for artifact in (None, "alertmanager"):
        with pytest.raises(RuntimeError, match="review_by is stale: 2026-10-30"):
            docker_sources.load_manifest(manifest_path, today=date(2026, 10, 31), artifact=artifact)


def _forecast_workflow_step() -> tuple[dict[str, object], str]:
    workflow = _load_workflow(WORKFLOWS_DIR / "nightly.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    job = jobs["review-deadline-forecast"]
    assert isinstance(job, dict)
    step = _step_by_name(job, "Forecast source and suppression review deadlines")
    run = step["run"]
    assert isinstance(run, str)
    return job, run


def _run_forecast_workflow(
    tmp_path: Path, *, today: date, review_by: str = "2026-10-05", policy: str | None = None
) -> tuple[subprocess.CompletedProcess[str], str]:
    manifest_dir = tmp_path / "scripts" / "ci"
    policy_dir = tmp_path / "trivy"
    manifest_dir.mkdir(parents=True)
    policy_dir.mkdir()
    (manifest_dir / "docker_source_artifacts.json").write_text(
        json.dumps(_docker_source_manifest(review_by=review_by)), encoding="utf-8"
    )
    (policy_dir / "ignore-policy.rego").write_text(
        (
            policy
            if policy is not None
            else (REPO_ROOT / "trivy" / "ignore-policy.rego").read_text(encoding="utf-8")
        ),
        encoding="utf-8",
    )

    _, run = _forecast_workflow_step()
    marker = "python3 - <<'PY'\n"
    assert run.startswith("set -euo pipefail\n" + marker)
    source = run.split(marker, 1)[1].rsplit("\nPY", 1)[0]
    assert "datetime.now(UTC).date()" in source
    functions = source.split('if __name__ == "__main__":', 1)[0]
    guard = (
        "import urllib.request\n"
        "def reject_network(*args, **kwargs):\n"
        "    raise AssertionError('forecast must not use network')\n"
        "urllib.request.urlopen = reject_network\n"
    )
    invocation = f"\nraise SystemExit(main(date.fromisoformat({today.isoformat()!r}), Path({str(tmp_path)!r})))\n"
    summary = tmp_path / "summary.md"
    result = subprocess.run(
        [sys.executable, "-c", guard + functions + invocation],
        cwd=REPO_ROOT,
        env={**os.environ, "GITHUB_STEP_SUMMARY": str(summary)},
        capture_output=True,
        text=True,
        check=False,
    )
    return result, summary.read_text(encoding="utf-8") if summary.exists() else ""


def test_nightly_forecast_job_is_main_only_private_free_and_independent() -> None:
    job, run = _forecast_workflow_step()
    workflow = _load_workflow(WORKFLOWS_DIR / "nightly.yml")

    assert workflow["jobs"]["test"] != job
    assert job["if"] == (
        "${{ github.ref == 'refs/heads/main' && "
        "(github.event_name == 'schedule' || github.event_name == 'workflow_dispatch') }}"
    )
    assert job["timeout-minutes"] == 2
    assert job["permissions"] == {"contents": "read"}
    assert job["env"] == {
        "PULSEPLATE_PYTHON_INDEX_URL": "",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": "",
    }
    checkout = _step_by_name(job, "Checkout code")
    assert checkout["with"] == {"persist-credentials": False}
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" == checkout["uses"]
    assert "load_manifest" in run and "evaluate_policy_file" in run
    assert "urlopen" not in run and "--ignore-policy" not in run
    assert "GITHUB_STEP_SUMMARY" in run


@pytest.mark.parametrize(
    ("today", "expected_exit", "current_finding", "forecast_finding"),
    [
        (date(2026, 9, 30), 0, False, False),
        (date(2026, 10, 2), 1, False, True),
        (date(2026, 10, 4), 1, False, True),
        (date(2026, 10, 6), 1, True, True),
    ],
)
def test_nightly_forecast_executes_utc_date_boundaries_and_labels(
    tmp_path: Path,
    today: date,
    expected_exit: int,
    current_finding: bool,
    forecast_finding: bool,
) -> None:
    historical = (
        "package trivy\n\nimport rego.v1\n"
        "# Suppression expires: 2026-10-07 (manual removal)\n"
        "# Review-by: 2026-10-05 (manual removal)\n"
        "# Review-by: 2026-10-07 (manual removal)\n"
        'default ignore := false\nignore if {\n\tinput.VulnerabilityID == "CVE-0000-0000"\n}\n'
    )
    result, summary = _run_forecast_workflow(tmp_path, today=today, policy=historical)

    assert result.returncode == expected_exit, result.stderr
    assert (
        f"UTC today: {today}; UTC forecast date: {date.fromordinal(today.toordinal() + 4)}"
        in summary
    )
    assert f"### CURRENT: {'attention required' if current_finding else 'no finding'}" in summary
    assert f"### FORECAST: {'attention required' if forecast_finding else 'no finding'}" in summary
    if today == date(2026, 10, 2):
        assert "review-by 2026-10-05" in summary
        assert "review-by 2026-10-07" not in summary
    if today == date(2026, 10, 4):
        assert "review-by 2026-10-07" in summary
        assert "Expired Trivy ignore policy" in summary


@pytest.mark.parametrize(
    ("review_by", "policy"),
    [
        ("bad-date", None),
        ("2026-10-05", "package trivy\nnot a valid policy"),
    ],
)
def test_nightly_forecast_malformed_inputs_fail_closed(
    tmp_path: Path, review_by: str, policy: str | None
) -> None:
    result, summary = _run_forecast_workflow(
        tmp_path, today=date(2026, 9, 28), review_by=review_by, policy=policy
    )

    assert result.returncode == 1, result.stderr
    assert "### CURRENT: attention required" in summary
    assert "### FORECAST: attention required" in summary


def test_libuuid_source_and_production_native_linkage_contract() -> None:
    manifest = json.loads((REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text())
    record = next(row for row in manifest["artifacts"] if row["name"] == "util-linux")
    assert record["version"] == "2.42.3"
    assert "".join(record["sha3_256_parts"]) == (
        "3edc35e7d261478bf9910ec87b70ae0c2be133e8ab523e2683ccfc0704d51652"  # pragma: allowlist secret
    )
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    assert "FROM sqlite-builder AS uuid-builder" in dockerfile
    assert "--disable-all-programs --enable-libuuid --disable-static" in dockerfile
    assert "make -j2 libuuid.la" in dockerfile
    production = dockerfile.split("FROM runtime-base AS production", 1)[1].split(
        "FROM production AS staging", 1
    )[0]
    assert "COPY --from=uuid-builder /opt/libuuid/libuuid.so.1.3.0" in production
    assert "import _uuid" in production and "_uuid.generate_time_safe()" in production
    assert 'Path("/proc/self/maps")' in production and "loaded != {expected}" in production
    assert "sha256sum --check" in production
    assert "/opt/libuuid/COPYING" in production
    assert "for interpreter in /usr/local/bin/python /opt/venv/bin/python" in production
    assert production.index("USER pulseplate") < production.index("import _uuid")


@pytest.mark.parametrize("corrupt_digest", [None, "sha256", "sha3"])
def test_libuuid_build_executes_both_source_digest_checks(
    tmp_path: Path, corrupt_digest: str | None
) -> None:
    """Execute the actual builder verifier with independently corrupted expected hashes."""
    payload = b"bounded util-linux source fixture"
    record = {
        "name": "util-linux",
        "version": "2.42.3",
        "sha256_parts": [sha256(payload).hexdigest()],
        "sha3_256_parts": [sha3_256(payload).hexdigest()],
    }
    if corrupt_digest == "sha256":
        record["sha256_parts"] = ["0" * 64]
    elif corrupt_digest == "sha3":
        record["sha3_256_parts"] = ["0" * 64]
    manifest_path = _write_docker_source_manifest(tmp_path, {"artifacts": [record]})
    archive_path = tmp_path / "util-linux.tar.gz"
    archive_path.write_bytes(payload)
    builder = (
        (REPO_ROOT / "Dockerfile").read_text().split("FROM sqlite-builder AS uuid-builder", 1)[1]
    )
    verifier = builder.split("RUN python - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    verifier = verifier.replace(
        '"/opt/libuuid/docker_source_artifacts.json"', repr(str(manifest_path))
    ).replace('"/tmp/util-linux.tar.gz"', repr(str(archive_path)))
    result = subprocess.run(
        [sys.executable, "-c", verifier], capture_output=True, text=True, check=False
    )
    if corrupt_digest is None:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert f"{corrupt_digest.upper()} mismatch" in result.stderr


def test_pr_build_runs_native_suppression_contract_after_pinned_scan() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build = jobs["build"]
    assert isinstance(build, dict)
    names = _step_names(build)
    assert names.count("Validate native Trivy suppression semantics") == 1
    assert names.index("Scan production image before publication eligibility") + 1 == names.index(
        "Validate native Trivy suppression semantics"
    )
    assert names.index("Validate native Trivy suppression semantics") + 1 == names.index(
        "Validate production image report and render SARIF"
    )
    scan = _step_by_name(build, "Scan production image before publication eligibility")
    assert scan["uses"] == ("aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25")
    assert scan["with"]["version"] == "v0.74.0"
    assert scan["with"]["ignore-policy"] == ".trivy-ignore-policy.rego"
    native = _step_by_name(build, "Validate native Trivy suppression semantics")
    assert native == {
        "name": "Validate native Trivy suppression semantics",
        "if": "github.event_name == 'pull_request'",
        "run": "set -euo pipefail\npython3 scripts/ci/check_trivy_ignore_policy_native.py\n",
    }
    assert "continue-on-error" not in native
    assert "Validate native Trivy suppression semantics" not in _step_names(jobs["publish"])


def test_pr_and_publish_share_strict_native_image_scan_predicates() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    build = jobs["build"]
    publish = jobs["publish"]
    first = _step_by_name(build, "Scan production image before publication eligibility")
    second = _step_by_name(publish, "Run Trivy vulnerability scanner (image scan, fail-closed)")
    assert first.get("env", {}).get("TRIVY_DB_REPOSITORY") == second["env"]["TRIVY_DB_REPOSITORY"]
    for key in (
        "version",
        "scan-type",
        "scanners",
        "severity",
        "exit-code",
        "format",
        "trivyignores",
        "ignore-policy",
    ):
        assert first["with"][key] == second["with"][key]
    for step in (first, second):
        assert step["with"]["version"] == "v0.74.0"
        assert step["with"].get("ignore-unfixed", False) is False
        assert "continue-on-error" not in step
    assert first["with"]["image-ref"] == "pulseplate:test"
    assert "if" not in first, "the production scan must not be a main-only step"
    for job, name in (
        (build, "Validate production image report and render SARIF"),
        (publish, "Fail when Trivy image SARIF is missing"),
    ):
        validator = _step_by_name(job, name)
        assert validator["if"] == "${{ always() }}"
        assert "--trivy-report" in validator["run"]
        assert "trivy convert --format sarif" in validator["run"]
    assert "github.event_name != 'pull_request'" in publish["if"]
    blocked = (
        "bsdutils",
        "libblkid1",
        "libmount1",
        "libsmartcols1",
        "libuuid1",
        "mount",
        "util-linux",
        "util-linux-extra",
        "libsystemd0",
        "libudev1",
        "libpcre2-8-0",
    )
    for job, name in (
        (build, "Check Docker runtime dependency surface"),
        (publish, "Check Docker publish runtime dependency surface"),
    ):
        run = _step_by_name(job, name)["run"]
        for package in blocked:
            assert f"--blocked-debian-package {package} \\" in run


def test_docker_source_artifact_loader_rejects_stale_review_dates(tmp_path: Path) -> None:
    manifest_path = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(review_by="2026-06-13"),
    )

    with pytest.raises(RuntimeError, match="review_by is stale"):
        docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))


def test_docker_source_artifact_loader_rejects_unsafe_source_metadata(tmp_path: Path) -> None:
    bad_host_manifest = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(url="https://example.com/sqlite-autoconf-3530200.tar.gz"),
    )
    with pytest.raises(RuntimeError, match="source URL must use https"):
        docker_sources.load_manifest(bad_host_manifest, today=date(2026, 6, 14))

    bad_filename_manifest = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(filename="../sqlite-autoconf-3530200.tar.gz"),
    )
    with pytest.raises(RuntimeError, match="safe basename"):
        docker_sources.load_manifest(bad_filename_manifest, today=date(2026, 6, 14))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("duplicate", "Duplicate"),
        ("version", "identity/version"),
        ("basename", "URL filename"),
        ("query", "overrides"),
        ("credentials", "overrides"),
        ("port", "overrides"),
        ("wrong-owner", "approved host"),
    ],
)
def test_source_manifest_rejects_ambiguous_identity_and_url_overrides(
    tmp_path: Path, mutation: str, message: str
) -> None:
    manifest = _docker_source_manifest()
    rows = manifest["artifacts"]
    row = rows[0]
    if mutation == "duplicate":
        rows.append(dict(row))
    elif mutation == "version":
        row["version"] = "another"
    elif mutation == "basename":
        row["url"] = "https://sqlite.org/2026/different.tar.gz"
    elif mutation == "query":
        row["url"] += "?override=1"
    elif mutation == "credentials":
        row["url"] = row["url"].replace("https://", "https://user@")
    elif mutation == "port":
        row["url"] = row["url"].replace("sqlite.org/", "sqlite.org:443/")
    else:
        row["url"] = row["url"].replace("sqlite.org", "www.kernel.org")
    path = _write_docker_source_manifest(tmp_path, manifest)
    with pytest.raises(RuntimeError, match=message):
        docker_sources.load_manifest(path, today=date(2026, 6, 14))


def _stub_source_transport(
    monkeypatch: pytest.MonkeyPatch,
    *,
    payload: bytes,
    code: int = 200,
    location: str | None = None,
    response_codes: tuple[int, ...] | None = None,
    response_headers: dict[str, str] | None = None,
    request_headers: list[dict[str, str]] | None = None,
) -> list[tuple[str, int]]:
    """Keep the actual opener/redirect dispatch and replace only HTTP transport."""
    calls: list[tuple[str, int]] = []

    def respond(_handler: object, request: Request) -> addinfourl:
        calls.append((request.full_url, request.timeout))
        if request_headers is not None:
            request_headers.append(dict(request.header_items()))
        headers = Message()
        for name, value in (response_headers or {}).items():
            headers[name] = value
        if location is not None:
            headers["Location"] = location
        status = code
        if response_codes is not None:
            if len(calls) > len(response_codes):
                pytest.fail("source transport exceeded its finite response inventory")
            status = response_codes[len(calls) - 1]
        response = addinfourl(BytesIO(payload), headers, request.full_url, status)
        response.msg = "synthetic source response"
        return response

    monkeypatch.setattr(HTTPSHandler, "https_open", respond)
    monkeypatch.setattr(HTTPHandler, "http_open", respond)
    return calls


@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
@pytest.mark.parametrize(
    "location",
    [
        "/2026/another.tar.gz",
        "https://www.sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://www.kernel.org/another.tar.gz",
        "https://unapproved.example/another.tar.gz",
        "http://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "file:///tmp/another.tar.gz",
    ],
)
def test_source_fetch_rejects_real_opener_redirects_without_second_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: int, location: str
) -> None:
    payload = b"verified source"
    path = _write_docker_source_manifest(tmp_path, _docker_source_manifest(payload=payload))
    artifact = docker_sources.load_manifest(path, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=payload, code=code, location=location)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError):
        docker_sources._write_verified_artifact(artifact, output)

    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize(
    "url",
    [
        "http://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://unapproved.example/sqlite-autoconf-3530200.tar.gz",
        "https://www.kernel.org/sqlite-autoconf-3530200.tar.gz",
        "https://@sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://sqlite.org:0/2026/sqlite-autoconf-3530200.tar.gz",
        "https://reader@sqlite.org/2026/sqlite-autoconf-3530200.tar.gz",
        "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz?override=1",
        "https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz#override",
    ],
)
def test_source_fetch_revalidates_direct_artifact_before_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    path = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = replace(docker_sources.load_manifest(path, today=date(2026, 6, 14))[0], url=url)
    calls = _stub_source_transport(monkeypatch, payload=b"unused")

    with pytest.raises(RuntimeError):
        docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert calls == []


@pytest.mark.parametrize("status", (502, 503, 504))
def test_source_fetch_retries_gateway_error_then_verifies_same_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: int,
) -> None:
    payload = b"verified sqlite source artifact"
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest(payload=payload))
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=payload, response_codes=(status, 200))
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)

    output = docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert output.read_bytes() == payload
    assert output.stat().st_mode & 0o777 == 0o644
    assert calls == [(artifact.url, 60)] * 2
    assert waits == [1]
    assert capsys.readouterr().err == f"sqlite-autoconf: source HTTP {status} on attempt 1/3\n"


def test_source_fetch_gateway_exhaustion_preserves_first_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(
        monkeypatch, payload=b"untrusted gateway body", response_codes=(502, 503, 504)
    )
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, output)

    assert raised.value.code == 502
    assert raised.value.fp.closed
    assert calls == [(artifact.url, 60)] * 3
    assert waits == [1, 2]
    assert list(output.iterdir()) == []
    assert capsys.readouterr().err.splitlines() == [
        "sqlite-autoconf: source HTTP 502 on attempt 1/3",
        "sqlite-autoconf: source HTTP 503 on attempt 2/3",
        "sqlite-autoconf: source HTTP 504 on attempt 3/3",
    ]


@pytest.mark.parametrize("status", (400, 401, 403, 404, 429, 500, 501, 505))
def test_source_fetch_permanent_http_error_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=b"permanent failure", code=status)
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, output)

    assert raised.value.code == status
    assert calls == [(artifact.url, 60)]
    assert waits == []
    assert list(output.iterdir()) == []


def test_source_fetch_gateway_then_redirect_still_fails_without_following(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(
        monkeypatch, payload=b"redirected source", location=artifact.url, response_codes=(504, 302)
    )
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, output)

    assert raised.value.code == 302
    assert calls == [(artifact.url, 60)] * 2
    assert waits == [1]
    assert list(output.iterdir()) == []


def test_source_fetch_gateway_then_bad_digest_is_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = _write_docker_source_manifest(
        tmp_path, _docker_source_manifest(payload=b"verified source")
    )
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls = _stub_source_transport(monkeypatch, payload=b"bad source", response_codes=(503, 200))
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)
    output = tmp_path / "sources"

    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, output)

    assert calls == [(artifact.url, 60)] * 2
    assert waits == [1]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("code", (504.0, "504", None, True))
def test_source_fetch_malformed_http_status_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, code: object
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    failure = HTTPError(artifact.url, 504, "synthetic malformed status", Message(), BytesIO())
    setattr(failure, "code", code)
    calls: list[str] = []

    def reject(_handler: object, request: Request) -> addinfourl:
        calls.append(request.full_url)
        raise failure

    monkeypatch.setattr(HTTPSHandler, "https_open", reject)
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)

    with pytest.raises(HTTPError) as raised:
        docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert raised.value is failure
    assert calls == [artifact.url]
    assert waits == []


@pytest.mark.parametrize(
    "failure",
    (
        SSLCertVerificationError("synthetic TLS verification failure"),
        URLError("synthetic connection failure"),
        TypeError("synthetic malformed response"),
    ),
)
def test_source_fetch_non_http_failure_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    calls: list[str] = []

    def reject(_handler: object, request: Request) -> addinfourl:
        calls.append(request.full_url)
        raise failure

    monkeypatch.setattr(HTTPSHandler, "https_open", reject)
    waits: list[int] = []
    monkeypatch.setattr(docker_sources.time, "sleep", waits.append)

    with pytest.raises(type(failure)) as raised:
        docker_sources._write_verified_artifact(artifact, tmp_path / "sources")

    assert raised.value is failure
    assert calls == [artifact.url]
    assert waits == []


def test_docker_source_artifact_fetcher_verifies_sha3_and_reuses_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"verified sqlite source artifact"
    manifest_path = _write_docker_source_manifest(
        tmp_path, _docker_source_manifest(payload=payload)
    )
    artifact = docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))[0]
    output_dir = tmp_path / "docker-sources"
    calls = _stub_source_transport(monkeypatch, payload=payload)
    output_path = docker_sources._write_verified_artifact(artifact, output_dir)

    assert output_path == output_dir / "sqlite-autoconf-3530200.tar.gz"
    assert output_path.read_bytes() == payload
    assert output_path.stat().st_mode & 0o777 == 0o644
    assert calls == [("https://sqlite.org/2026/sqlite-autoconf-3530200.tar.gz", 60)]

    reused_path = docker_sources._write_verified_artifact(artifact, output_dir)

    assert reused_path == output_path
    assert output_path.read_bytes() == payload
    assert calls == [(artifact.url, 60)]


def test_docker_source_artifact_fetcher_rejects_digest_mismatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_docker_source_manifest(
        tmp_path,
        _docker_source_manifest(payload=b"expected sqlite source artifact"),
    )
    artifact = docker_sources.load_manifest(manifest_path, today=date(2026, 6, 14))[0]

    _stub_source_transport(monkeypatch, payload=b"tampered sqlite source artifact")

    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, tmp_path / "docker-sources")

    assert not (tmp_path / "docker-sources" / "sqlite-autoconf-3530200.tar.gz").exists()


@pytest.fixture
def zlib_rejection_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    context = tmp_path / "synthetic-build-context"
    context.mkdir()
    monkeypatch.setattr(docker_sources, "REPO_ROOT", context)
    return context


def test_zlib_rejection_retains_private_opaque_response_without_authentication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    zlib_rejection_context: Path,
) -> None:
    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_TOKEN",
        "GHCR_READ_TOKEN",
        "DEVPI_CI_USER",
        "DEVPI_CI_PASSWORD",
        "PULSEPLATE_PYTHON_INDEX_URL",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
    ):
        (
            monkeypatch.setenv(key, "synthetic")
            if "proxy" not in key.lower()
            else monkeypatch.delenv(key, raising=False)
        )
    monkeypatch.setenv("no_proxy", "*")
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".netrc").write_text("machine zlib.net login synthetic password synthetic\n")
    (tmp_path / ".netrc").chmod(0o600)
    artifact = next(
        row
        for row in docker_sources.load_manifest(
            docker_sources.DEFAULT_MANIFEST, today=date(2026, 10, 9)
        )
        if row.name == "zlib"
    )
    payload = b"untrusted-response-body-marker"
    requests: list[dict[str, str]] = []
    headers = {
        "Content-Type": "text/html",
        "Content-Length": str(len(payload)),
        "Content-Encoding": "identity",
        "Date": "Mon, 12 Oct 2026 00:00:00 GMT",
        "Last-Modified": "x" * 513,
        "Set-Cookie": "synthetic",
        "Authorization": "synthetic",
        "Proxy-Authorization": "synthetic",
        "WWW-Authenticate": "synthetic",
        "Proxy-Authenticate": "synthetic",
        "Location": "https://example.invalid/never-followed",
        "X-Unselected": "synthetic",
    }
    calls = _stub_source_transport(
        monkeypatch, payload=payload, response_headers=headers, request_headers=requests
    )
    output, quarantine = tmp_path / "verified", tmp_path / "quarantine"
    assert not quarantine.is_relative_to(zlib_rejection_context)
    with pytest.raises(RuntimeError) as raised:
        docker_sources._write_verified_artifact(
            artifact, output, integrity_rejection_dir=quarantine
        )
    assert raised.value.args == (
        f"zlib SHA3 mismatch: expected {artifact.sha3_256}, got {sha3_256(payload).hexdigest()}",
    )
    assert calls == [(artifact.url, 60)]
    assert not {"authorization", "proxy-authorization", "cookie"}.intersection(
        key.lower() for key in requests[0]
    )
    assert list(output.iterdir()) == []
    assert {p.name for p in quarantine.iterdir()} == {"response.bin", "metadata.json"}
    assert (quarantine / "response.bin").read_bytes() == payload
    assert quarantine.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in quarantine.iterdir())
    metadata = json.loads((quarantine / "metadata.json").read_bytes())
    assert metadata["request_url"] == artifact.url and metadata["status"] == 200
    assert metadata["headers"] == {
        name: headers[name][:512]
        for name in ("Content-Type", "Content-Length", "Content-Encoding", "Date", "Last-Modified")
    }
    assert metadata["truncated_headers"] == ["Last-Modified"]
    assert metadata["retained_bytes"] == len(payload) and metadata["body_scope"] == "received_bytes"
    assert metadata["expected_sha3_256"] == artifact.sha3_256
    assert metadata["expected_sha256"] == artifact.sha256
    assert metadata["actual_sha3_256"] == sha3_256(payload).hexdigest()
    assert metadata["actual_sha256"] == sha256(payload).hexdigest()
    captured = capsys.readouterr()
    assert "untrusted-response-body-marker" not in captured.out + captured.err
    assert "synthetic" not in captured.out + captured.err


@pytest.mark.parametrize(
    "kind", ("existing", "symlink", "parent-symlink", "parent-traversal", "context", "cache")
)
def test_zlib_capture_path_failure_preserves_integrity_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, zlib_rejection_context: Path
) -> None:
    artifact = next(
        row
        for row in docker_sources.load_manifest(
            docker_sources.DEFAULT_MANIFEST, today=date(2026, 10, 9)
        )
        if row.name == "zlib"
    )
    payload = b"bad-response"
    _stub_source_transport(monkeypatch, payload=payload)
    output, quarantine = tmp_path / "verified", tmp_path / "quarantine"
    output.mkdir()
    if kind == "existing":
        quarantine.mkdir(mode=0o700)
    elif kind == "symlink":
        quarantine.symlink_to(tmp_path / "never-created")
    elif kind == "parent-symlink":
        (tmp_path / "alias").symlink_to(tmp_path)
        quarantine = tmp_path / "alias/quarantine"
    elif kind == "parent-traversal":
        quarantine = tmp_path / "unused/../quarantine"
    elif kind == "context":
        quarantine = zlib_rejection_context / "never-created-rejection"
    else:
        quarantine = output / "quarantine"
    if kind in ("existing", "symlink"):
        with pytest.raises(FileExistsError):
            docker_sources._retain_rejected_zlib_response(
                artifact, payload, 200, Message(), quarantine, output
            )
    else:
        with pytest.raises(RuntimeError) as secondary:
            docker_sources._retain_rejected_zlib_response(
                artifact, payload, 200, Message(), quarantine, output
            )
        expected_message = (
            "Rejected-response quarantine requires real existing parents."
            if kind == "parent-symlink"
            else "Rejected-response quarantine must be outside the build context/cache."
        )
        assert secondary.value.args == (expected_message,)
    with pytest.raises(RuntimeError) as raised:
        docker_sources._write_verified_artifact(
            artifact, output, integrity_rejection_dir=quarantine
        )
    assert raised.value.args == (
        f"zlib SHA3 mismatch: expected {artifact.sha3_256}, got {sha3_256(payload).hexdigest()}",
    )
    expected = "FileExistsError" if kind in ("existing", "symlink") else "RuntimeError"
    assert raised.value.__notes__ == [f"zlib: rejected-response capture failed: {expected}"]
    assert list(output.iterdir()) == []
    assert not (tmp_path / "never-created").exists()


def test_zlib_rejection_retains_only_original_bounded_read_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, zlib_rejection_context: Path
) -> None:
    artifact = next(
        row
        for row in docker_sources.load_manifest(
            docker_sources.DEFAULT_MANIFEST, today=date(2026, 10, 9)
        )
        if row.name == "zlib"
    )
    assert docker_sources._NATIVE_ARCHIVE_MAX_BYTES == 64 * 1024 * 1024
    payload = b"x" * (64 * 1024 * 1024 + 2)
    _stub_source_transport(monkeypatch, payload=payload)
    output, quarantine = tmp_path / "verified", tmp_path / "quarantine"
    assert not quarantine.is_relative_to(zlib_rejection_context)
    with pytest.raises(RuntimeError, match="^zlib SHA3 mismatch: expected "):
        docker_sources._write_verified_artifact(
            artifact, output, integrity_rejection_dir=quarantine
        )
    retained = (quarantine / "response.bin").read_bytes()
    metadata = json.loads((quarantine / "metadata.json").read_bytes())
    assert retained == payload[:-1]
    assert (
        len(retained)
        == metadata["retained_bytes"]
        == metadata["read_limit_bytes"]
        == 64 * 1024 * 1024 + 1
    )
    assert metadata["body_scope"] == "bounded_prefix"
    assert metadata["actual_sha3_256"] == sha3_256(retained).hexdigest()
    assert metadata["actual_sha256"] == sha256(retained).hexdigest()
    assert list(output.iterdir()) == []


def test_zlib_capture_write_failure_keeps_primary_error_and_closes_owned_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    zlib_rejection_context: Path,
) -> None:
    artifact = next(
        row
        for row in docker_sources.load_manifest(
            docker_sources.DEFAULT_MANIFEST, today=date(2026, 10, 9)
        )
        if row.name == "zlib"
    )
    payload = b"bad-response"
    assert not (tmp_path / "quarantine").is_relative_to(zlib_rejection_context)
    _stub_source_transport(monkeypatch, payload=payload)
    real_close = os.close
    failed: list[int] = []
    closed: list[int] = []

    def fail_write(fd: int, *_args: object, **_kwargs: object) -> None:
        failed.append(fd)
        raise OSError("synthetic-private-write-detail")

    def close_owned(fd: int) -> None:
        real_close(fd)
        closed.append(fd)

    with monkeypatch.context() as local:
        local.setattr(docker_sources.os, "fdopen", fail_write)
        local.setattr(docker_sources.os, "close", close_owned)
        with pytest.raises(RuntimeError) as raised:
            docker_sources._write_verified_artifact(
                artifact, tmp_path / "verified", integrity_rejection_dir=tmp_path / "quarantine"
            )
    assert raised.value.args == (
        f"zlib SHA3 mismatch: expected {artifact.sha3_256}, got {sha3_256(payload).hexdigest()}",
    )
    assert raised.value.__notes__ == ["zlib: rejected-response capture failed: OSError"]
    assert len(failed) == 1 and failed[0] in closed
    assert not (tmp_path / "quarantine/metadata.json").exists()
    assert list((tmp_path / "verified").iterdir()) == []
    captured = capsys.readouterr()
    assert "synthetic-private-write-detail" not in captured.out + captured.err
    assert captured.err == "zlib: rejected-response capture failed: OSError\n"


@pytest.mark.parametrize("kind", ("symlink", "dangling", "directory", "fifo", "hardlink"))
def test_source_cache_rejects_nonregular_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    payload = b"reviewed source"
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest(payload=payload))
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    output = tmp_path / "sources"
    output.mkdir()
    referent = tmp_path / "outside"
    referent.write_bytes(payload)
    referent.chmod(0o600)
    cached = output / artifact.filename
    if kind == "symlink":
        cached.symlink_to(referent)
    elif kind == "dangling":
        cached.symlink_to(tmp_path / "missing")
    elif kind == "directory":
        cached.mkdir()
    elif kind == "hardlink":
        cached.hardlink_to(referent)
    else:
        os.mkfifo(cached)

    def no_network(*args: object, **kwargs: object) -> None:
        pytest.fail("unsafe cache entry must be rejected before network access")

    monkeypatch.setattr(docker_sources, "build_opener", no_network)
    with pytest.raises(RuntimeError, match="regular|symlink"):
        docker_sources._write_verified_artifact(artifact, output)
    assert referent.read_bytes() == payload
    assert referent.stat().st_mode & 0o777 == 0o600


def test_source_cache_rejects_symlinked_output_parent(tmp_path: Path) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlink"):
        docker_sources._write_verified_artifact(artifact, alias / "sources")
    assert list(actual.iterdir()) == []


def test_source_cache_rejects_parent_traversal(tmp_path: Path) -> None:
    manifest = _write_docker_source_manifest(tmp_path, _docker_source_manifest())
    artifact = docker_sources.load_manifest(manifest, today=date(2026, 6, 14))[0]
    with pytest.raises(RuntimeError, match="traverse parent"):
        docker_sources._write_verified_artifact(artifact, tmp_path / "nested" / ".." / "sources")
    assert not (tmp_path / "nested").exists()


def test_docker_build_workflows_prefetch_source_artifacts_before_build() -> None:
    """Docker workflows prepare source artifacts explicitly before image build actions."""
    checked_steps: set[tuple[str, str, str]] = set()

    for workflow_name in ("build.yml", "trivy.yml", "cd.yml"):
        workflow = _load_workflow(WORKFLOWS_DIR / workflow_name)
        for job_name, job, build_step_name in _root_context_docker_build_steps(workflow):
            prepare_step = _step_by_name(job, "Prepare Docker source artifacts")
            prepare_run = prepare_step["run"]
            assert isinstance(prepare_run, str)
            assert "set -euo pipefail" in prepare_run
            assert "python3 scripts/ci/fetch_docker_source_artifacts.py" in prepare_run
            assert _step_index(job, "Prepare Docker source artifacts") < _step_index(
                job,
                build_step_name,
            )
            checked_steps.add((workflow_name, job_name, build_step_name))

    assert EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS <= checked_steps


def test_makefile_docker_build_targets_prefetch_source_artifacts() -> None:
    """Local Docker Make targets prepare source artifacts before Docker builds."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "docker-source-artifacts: ## Prepare verified Docker source artifacts" in makefile
    assert "$(DEV_PYTHON) scripts/ci/fetch_docker_source_artifacts.py" in makefile
    assert (
        "docker-build: ensure-python-proxy docker-source-artifacts ## Build production Docker image"
        in makefile
    )
    assert (
        "docker-build-dev: ensure-python-proxy docker-source-artifacts ## Build development Docker image"
        in makefile
    )


def test_runtime_base_requires_fixed_bookworm_glibc_line() -> None:
    """Runtime base fails closed if libc stays below the CVE-2025-8058 fix."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime_base_section = dockerfile.split(
        f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base",
        1,
    )[1]
    runtime_base_section = runtime_base_section.split("COPY --from=builder", 1)[0]

    assert "libc-bin" in runtime_base_section
    assert "libc6" in runtime_base_section
    assert 'dpkg --compare-versions "${version}" ge "2.36-9+deb12u13"' in runtime_base_section
    assert "below fixed glibc line 2.36-9+deb12u13" in runtime_base_section


def test_runtime_base_requires_fixed_bookworm_pcre2_line() -> None:
    """Refresh inherited PCRE2 and reject packages below both Debian CVE fixes."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    runtime = dockerfile.split(f"FROM {BACKEND_PYTHON_BASE_IMAGE} AS runtime-base", 1)[1]
    runtime = runtime.split("COPY --from=builder", 1)[0]
    assert "        libpcre2-8-0 \\" in runtime
    pcre2_guard = runtime.split("&& pcre2_version=", 1)[1].split(
        "&& rm -rf /var/lib/apt/lists/*", 1
    )[0]
    assert (
        'if ! dpkg --compare-versions "${pcre2_version}" ge "10.42-1+deb12u1"; then' in pcre2_guard
    )
    assert "exit 1;" in pcre2_guard
    assert "below fixed PCRE2 line 10.42-1+deb12u1" in runtime


def test_docker_runtime_surface_guard_blocks_perl_runtime_packages() -> None:
    """Docker workflows fail if production keeps Perl runtime packages."""
    for workflow_name, image_ref in (
        ("build.yml", "pulseplate:test"),
        ("trivy.yml", "pulseplate:trivy-scan-${{ github.sha }}"),
    ):
        workflow = _load_workflow(WORKFLOWS_DIR / workflow_name)
        jobs = workflow["jobs"]
        assert isinstance(jobs, dict)
        build_job = jobs["build"]
        assert isinstance(build_job, dict)
        step = _step_by_name(build_job, "Check Docker runtime dependency surface")
        run_script = step["run"]
        assert isinstance(run_script, str)

        assert f"--image {image_ref}" in run_script
        assert "--blocked-debian-package apt" in run_script
        assert "--blocked-debian-package gzip" in run_script
        assert "--blocked-debian-package gpgv" in run_script
        assert "--blocked-debian-package libacl1" in run_script
        assert "--blocked-debian-package libattr1" in run_script
        assert "--blocked-debian-package libgnutls30" in run_script
        assert "--blocked-debian-package libsqlite3-0" in run_script
        assert "--blocked-debian-package libpcre2-8-0" in run_script
        assert "--blocked-debian-package perl-base" in run_script
        assert "--blocked-debian-prefix perl-modules-" in run_script


def test_docker_entrypoint_keeps_bodyfat_hidden_but_routable() -> None:
    """Docker entrypoint serves app.main while preserving bodyfat compatibility."""
    from app.main import app

    client = TestClient(app)
    openapi_response = client.get("/openapi.json")
    assert openapi_response.headers.get("content-type", "").startswith("application/json")
    openapi_paths = openapi_response.json()["paths"]

    assert "/api/v1/bodyfat" not in openapi_paths
    response = client.post(
        "/api/v1/bodyfat",
        json={
            "gender": "male",
            "age": 30,
            "waist_cm": 80.0,
            "neck_cm": 38.0,
            "height_m": 1.75,
            "weight_kg": 75.0,
        },
    )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert {"labels", "lang", "median", "methods"} <= response.json().keys()


def test_trivy_workflow_is_main_push_image_security_lane() -> None:
    """Trivy scans production images on main pushes, schedule, and manual dispatch."""
    workflow = _load_workflow(WORKFLOWS_DIR / "trivy.yml")
    on_section = workflow.get("on", workflow.get(True))
    assert isinstance(on_section, dict)
    push = on_section["push"]
    assert isinstance(push, dict)
    assert push["branches"] == ["main"]
    assert "pull_request" not in on_section
    assert "pull_request_target" not in on_section
    assert "schedule" in on_section
    assert "workflow_dispatch" in on_section

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    build_job = jobs["build"]
    assert isinstance(build_job, dict)
    scan_step = next(
        step
        for step in build_job["steps"]
        if isinstance(step, dict) and step.get("name") == "Run Trivy vulnerability scanner"
    )
    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["exit-code"] == "1"
    assert scan_step_with["severity"] == "CRITICAL,HIGH"
    assert scan_step_with["limit-severities-for-sarif"] is True
    assert scan_step_with["ignore-unfixed"] is True
    assert scan_step_with["trivyignores"] == ".trivyignore"
    assert scan_step_with["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan_step
    assert "Fail when Trivy SARIF is missing" in _step_names(build_job)


def test_publish_image_scan_fails_closed() -> None:
    """Publish path image scan blocks HIGH/CRITICAL findings and missing SARIF."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    publish_job = jobs["publish"]
    assert isinstance(publish_job, dict)
    publish_steps = publish_job["steps"]
    assert isinstance(publish_steps, list)
    build_scan_step = _step_by_name(publish_job, "Build Docker image for publish scan")
    image_ref_step = _step_by_name(publish_job, "Set image ref for SBOM and image scan")
    publish_surface_step = _step_by_name(
        publish_job, "Check Docker publish runtime dependency surface"
    )
    scan_step = _step_by_name(
        publish_job,
        "Run Trivy vulnerability scanner (image scan, fail-closed)",
    )
    fail_sarif_step = _step_by_name(publish_job, "Fail when Trivy image SARIF is missing")
    upload_sarif_step = _step_by_name(publish_job, "Upload Trivy image scan results")
    login_step = _step_by_name(publish_job, "Log in to GHCR")
    push_step = _step_by_name(publish_job, "Push scanned Docker image")
    sbom_step = _step_by_name(publish_job, "Generate SBOM")
    provenance_step = _step_by_name(publish_job, "Attest Docker image provenance")
    attestation_step = _step_by_name(publish_job, "Attest Docker image SBOM")

    assert _step_index(publish_job, "Build Docker image for publish scan") < _step_index(
        publish_job, "Set image ref for SBOM and image scan"
    )
    assert _step_index(publish_job, "Set image ref for SBOM and image scan") < _step_index(
        publish_job, "Check Docker publish runtime dependency surface"
    )
    assert _step_index(
        publish_job, "Check Docker publish runtime dependency surface"
    ) < _step_index(publish_job, "Run Trivy vulnerability scanner (image scan, fail-closed)")
    assert _step_index(
        publish_job, "Run Trivy vulnerability scanner (image scan, fail-closed)"
    ) < _step_index(publish_job, "Fail when Trivy image SARIF is missing")
    assert _step_index(publish_job, "Fail when Trivy image SARIF is missing") < _step_index(
        publish_job, "Upload Trivy image scan results"
    )
    assert _step_index(publish_job, "Upload Trivy image scan results") < _step_index(
        publish_job, "Log in to GHCR"
    )
    assert _step_index(publish_job, "Log in to GHCR") < _step_index(
        publish_job, "Push scanned Docker image"
    )
    assert _step_index(publish_job, "Push scanned Docker image") < _step_index(
        publish_job, "Generate SBOM"
    )

    build_scan_with = build_scan_step["with"]
    assert isinstance(build_scan_with, dict)
    assert build_scan_step["id"] == "docker-build-scan"
    assert build_scan_with["target"] == "production"
    assert build_scan_with["platforms"] == "linux/amd64"
    assert build_scan_with["push"] is False
    assert build_scan_with["load"] is True
    assert build_scan_with["provenance"] is False
    assert "sbom" not in build_scan_with
    assert build_scan_with["tags"] == "${{ steps.meta.outputs.tags }}"
    assert build_scan_with["labels"] == "${{ steps.meta.outputs.labels }}"
    assert (
        "PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt"
        in build_scan_with["build-args"]
    )
    assert "pp_py_index=PULSEPLATE_PYTHON_INDEX_URL" in build_scan_with["secret-envs"]
    assert "pp_py_host=PULSEPLATE_PYTHON_TRUSTED_HOST" in build_scan_with["secret-envs"]

    for step in publish_steps[: _step_index(publish_job, "Fail when Trivy image SARIF is missing")]:
        assert isinstance(step, dict)
        if step.get("uses") == "docker/build-push-action@d08e5c354a6adb9ed34480a06d141179aa583294":
            step_with = step.get("with")
            assert isinstance(step_with, dict)
            assert step_with["push"] is False

    assert "GITHUB_TOKEN" not in build_scan_step.get("env", {})
    assert "GITHUB_TOKEN" not in publish_surface_step.get("env", {})
    assert "GITHUB_TOKEN" not in scan_step.get("env", {})
    assert login_step["uses"].startswith("docker/login-action@")
    assert _step_index(publish_job, "Log in to GHCR") > _step_index(
        publish_job, "Fail when Trivy image SARIF is missing"
    )

    image_ref_run = image_ref_step["run"]
    assert isinstance(image_ref_run, str)
    assert "sha-${{ github.sha }}" in image_ref_run

    publish_surface_run = publish_surface_step["run"]
    assert isinstance(publish_surface_run, str)
    assert "check_docker_runtime_dependency_surface.py" in publish_surface_run
    assert publish_surface_step["env"] == {"IMAGE_REF": "${{ steps.image-ref.outputs.ref }}"}
    assert '--image "${IMAGE_REF}"' in publish_surface_run
    assert "steps.image-ref.outputs.ref" not in publish_surface_run
    assert "--blocked-debian-package gzip" in publish_surface_run
    for package in (
        "apt",
        "gpgv",
        "libacl1",
        "libattr1",
        "libgnutls30",
        "libsqlite3-0",
        "perl-base",
    ):
        assert f"--blocked-debian-package {package}" in publish_surface_run
    assert "--blocked-debian-prefix perl-modules-" in publish_surface_run
    assert "docker-publish-runtime-dependency-surface.json" in publish_surface_run

    scan_step_with = scan_step["with"]
    assert isinstance(scan_step_with, dict)
    assert scan_step_with["scan-type"] == "image"
    assert scan_step_with["image-ref"] == "${{ steps.image-ref.outputs.ref }}"
    assert scan_step_with["exit-code"] == "1"
    assert scan_step_with["severity"] == "CRITICAL,HIGH"
    assert scan_step_with["format"] == "json"
    assert scan_step_with["output"] == "trivy-image.json"
    assert scan_step_with["trivyignores"] == ".trivyignore"
    assert scan_step_with["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan_step
    assert fail_sarif_step["if"] == "${{ always() }}"

    assert upload_sarif_step["if"] == "${{ always() && hashFiles('trivy-image.sarif') != '' }}"
    assert push_step["id"] == "docker-build-push"
    push_run = push_step["run"]
    assert isinstance(push_run, str)
    assert "docker image push" in push_run
    assert "steps.meta.outputs.tags" in push_run
    assert "steps.image-ref.outputs.ref" in push_run
    assert "grep -F -m1" in push_run
    assert "GITHUB_OUTPUT" in push_run
    assert "digest=${digest}" in push_run

    assert sbom_step["with"]["image"] == "${{ steps.image-ref.outputs.ref }}"
    assert (
        provenance_step["with"]["subject-digest"] == "${{ steps.docker-build-push.outputs.digest }}"
    )
    assert (
        attestation_step["with"]["subject-digest"]
        == "${{ steps.docker-build-push.outputs.digest }}"
    )


@pytest.mark.parametrize(
    "name,version,url,digest",
    [
        (
            "pcre2",
            "10.49",
            "https://codeload.github.com/PCRE2Project/pcre2/legacy.tar.gz/refs/tags/pcre2-10.49",
            "6510970e92ea9410b44f85c606c389c3473ba05d2d6338f0ce763cc4ccaa382c",
        ),
        (
            "sljit",
            "de0259c7aaf36aa40cba8014f3fad3edde9307f9",
            "https://codeload.github.com/zherczeg/sljit/legacy.tar.gz/"
            "de0259c7aaf36aa40cba8014f3fad3edde9307f9",
            "7ad006814d4d9c698832b14541634b9cc12039bae7b3bb547909fda51ee11a80",
        ),
    ],
)
def test_pcre2_source_records_bind_exact_reviewed_closure(
    name: str, version: str, url: str, digest: str
) -> None:
    artifacts = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
    )
    assert len(artifacts) == 15
    matches = [artifact for artifact in artifacts if artifact.name == name]
    assert len(matches) == 1
    artifact = matches[0]
    assert (artifact.version, artifact.filename, artifact.url, artifact.sha3_256) == (
        version,
        f"{name}-{version}.tar.gz",
        url,
        digest,
    )


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
@pytest.mark.parametrize(
    "mutation",
    [
        "repo",
        "ref",
        "path",
        "version",
        "filename",
        "digest",
        "cross_pair",
        "http",
        "credentials",
        "empty_userinfo",
        "port",
        "query",
        "fragment",
        "unknown_name",
        "malformed_version",
        "malformed_digest",
    ],
)
def test_pcre2_source_manifest_rejects_identity_and_metadata_cross_pairs(
    tmp_path: Path, name: str, mutation: str
) -> None:
    manifest = json.loads((REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text())
    row = next(record for record in manifest["artifacts"] if record["name"] == name)
    if mutation == "repo":
        row["url"] = row["url"].replace("/legacy.tar.gz/", "-other/legacy.tar.gz/")
    elif mutation == "ref":
        row["url"] += "-other"
    elif mutation == "path":
        row["url"] = row["url"].replace("/legacy.tar.gz/", "/tar.gz/")
    elif mutation == "version":
        row["version"] += "-other"
        row["filename"] = f"{name}-{row['version']}.tar.gz"
    elif mutation == "filename":
        row["filename"] = "different.tar.gz"
    elif mutation == "digest":
        row["sha3_256_parts"] = ["0" * 64]
    elif mutation == "cross_pair":
        other = next(
            record
            for record in manifest["artifacts"]
            if record["name"] != name and record["name"] in ("pcre2", "sljit")
        )
        row["url"] = other["url"]
        row["sha3_256_parts"] = other["sha3_256_parts"]
    elif mutation == "http":
        row["url"] = row["url"].replace("https:", "http:")
    elif mutation == "credentials":
        row["url"] = row["url"].replace("https://", "https://reader@")
    elif mutation == "empty_userinfo":
        row["url"] = row["url"].replace("https://", "https://@")
    elif mutation == "port":
        row["url"] = row["url"].replace("github.com/", "github.com:443/")
    elif mutation == "query":
        row["url"] += "?override=1"
    elif mutation == "fragment":
        row["url"] += "#override"
    elif mutation == "unknown_name":
        row["name"] = "other"
        row["filename"] = f"other-{row['version']}.tar.gz"
    elif mutation == "malformed_version":
        row["version"] = 10
    else:
        row["sha3_256_parts"] = [None]
    path = _write_docker_source_manifest(tmp_path, manifest)
    with pytest.raises(RuntimeError):
        docker_sources.load_manifest(path, today=date(2026, 10, 2))


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_pcre2_source_redirects_use_real_rejecting_handler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, code: int
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
        )
        if item.name == name
    )
    calls = _stub_source_transport(
        monkeypatch, payload=b"redirected source", code=code, location=artifact.url
    )
    output = tmp_path / "sources"
    with pytest.raises(HTTPError):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
@pytest.mark.parametrize("field", ["url", "version", "filename", "sha3_256"])
def test_pcre2_direct_source_revalidates_identity_before_cache_or_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, field: str
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
        )
        if item.name == name
    )
    corrupted = replace(artifact, **{field: getattr(artifact, field) + "other"})
    calls = _stub_source_transport(monkeypatch, payload=b"unused")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="exact reviewed identity"):
        docker_sources._write_verified_artifact(corrupted, output)
    assert calls == []
    assert not output.exists()


@pytest.mark.parametrize("name", ["pcre2", "sljit"])
def test_pcre2_source_download_rejects_wrong_actual_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 2)
        )
        if item.name == name
    )
    calls = _stub_source_transport(monkeypatch, payload=b"wrong actual source bytes")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="SHA3"):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


def test_pcre2_production_build_preserves_native_features_and_consumers() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    dockerignore = (REPO_ROOT / ".dockerignore").read_text()
    builder = dockerfile.split("FROM sqlite-builder AS pcre2-builder", 1)[1].split(
        "# Stage 2: Runtime base stage", 1
    )[0]
    for filename in ("pcre2-10.49.tar.gz", "sljit-de0259c7aaf36aa40cba8014f3fad3edde9307f9.tar.gz"):
        assert f"COPY build/docker-sources/{filename}" in builder
        assert f"!build/docker-sources/{filename}" in dockerignore
    assert 'sha3_256(payload).hexdigest() != "".join(records[0]["sha3_256_parts"])' in builder
    assert "RUN --network=none" in builder
    assert "--strip-components=1 -C /tmp/pcre2-source/deps/sljit" in builder
    for flag in (
        "--enable-shared",
        "--disable-static",
        "--enable-jit",
        "--enable-unicode",
        "--enable-pcre2-8",
        "--disable-pcre2-16",
        "--disable-pcre2-32",
        "--disable-pcre2grep-libz",
        "--disable-pcre2grep-libbz2",
        "--disable-pcre2test-libreadline",
    ):
        assert flag in builder
    assert "make -j2 libpcre2-8.la" in builder
    for source in ("LICENCE.md", "COPYING", "deps/sljit/LICENSE"):
        assert f"install -m 0644 {source}" in builder
    production = dockerfile.split("FROM runtime-base AS production", 1)[1].split(
        "FROM runtime-base AS development", 1
    )[0]
    replacement = production.index("COPY --from=pcre2-builder")
    pruning = production.index("# SECURITY: production-package-pruning-start")
    nonroot = production.index("USER pulseplate")
    smoke = production.index("# Exercise the actual replacement")
    assert replacement < pruning < nonroot < smoke
    assert "ln -s libpcre2-8.so.0.16.1 /usr/local/lib/libpcre2-8.so.0 && ldconfig" in production
    assert "        libpcre2-8-0 \\" in production
    assert "sha256sum --check /usr/local/share/doc/pulseplate-pcre2/SHA256SUMS" in production
    for native_call in (
        "pcre2_config_8",
        "pcre2_compile_8",
        "pcre2_jit_compile_8",
        "pcre2_jit_match_8",
        "pcre2_jit_stack_assign_8",
        "selabel_open",
        "selabel_lookup_raw",
        "freecon",
        "selabel_close",
    ):
        assert native_call in production[smoke:]
    assert 'version.value.startswith(b"10.49 ")' in production[smoke:]
    assert "if loaded != {expected}:" in production[smoke:]
    assert "finally:" in production[smoke:]
    assert "grep -P" in production[smoke:]
    assert "dpkg --version" in production[smoke:]
    assert 'mkdir "${consumer_directory}/child"' in production[smoke:]


@pytest.mark.parametrize(
    "today,expected_exit,forecast_finding",
    [
        (date(2026, 10, 6), 0, False),
        (date(2026, 10, 8), 0, False),
        (date(2026, 10, 17), 0, False),
        (date(2026, 10, 18), 1, True),
    ],
)
def test_candidate_nightly_forecast_preserves_current_and_plus_four(
    tmp_path: Path, today: date, expected_exit: int, forecast_finding: bool
) -> None:
    result, summary = _run_forecast_workflow(tmp_path, today=today, review_by="2026-10-21")
    assert result.returncode == expected_exit, result.stderr
    assert (
        f"UTC today: {today}; UTC forecast date: {date.fromordinal(today.toordinal() + 4)}"
        in summary
    )
    assert "### CURRENT: no finding" in summary
    assert f"### FORECAST: {'attention required' if forecast_finding else 'no finding'}" in summary
    if forecast_finding:
        assert (
            "Docker sources: Docker source artifact manifest review_by is stale: 2026-10-21"
            in summary
        )
        assert "Expired Trivy ignore policy" not in summary
    assert "Trivy policy:" not in summary


def test_native_client_omits_unused_gss_closure_and_separates_pg_build() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    native = dockerfile.split(" AS native-builder\n", 1)[1].split("\nFROM ", 1)[0]
    assert "libkrb5-dev" not in dockerfile and "libgssapi-krb5-2 \\\n" not in dockerfile
    assert "--without-gssapi --without-ldap" in native and "--with-gssapi" not in native
    split = "ldconfig\nSH\n\n# PostgreSQL client flags have a separate cache boundary from Z/N/OpenSSL.\nRUN --network=none <<'SH'\nset -eu\ncd /build/source/postgresql-18.6"
    assert split in native
    prefix, client = native.split(split, 1)
    assert "cd /build/source/zlib-1.3.2" in prefix
    assert "--with-versioned-syms" in prefix and "make -j2 build_sw" in prefix
    assert "make -j2 -C src/interfaces/libpq all" in client
    for package in ("libgssapi-krb5-2", "libk5crypto3", "libkrb5-3", "libkrb5support0"):
        assert package in dockerfile.split("retired = ", 1)[1].split("\nfor row", 1)[0]
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    assert "gssencmode=require" in source and "not compiled in" in source
    assert (
        "gss_probe.finish()" in source and "Unused Kerberos native runtime remains loaded" in source
    )


@pytest.mark.parametrize(
    "status,error_message,expected_exit",
    (
        (1, b'gssencmode value "require" invalid when GSSAPI support is not compiled in', 0),
        (1, b"GSSAPI encryption required but no credential cache", 1),
        (0, b"not compiled in", 1),
        (0, b"GSSAPI enabled", 1),
    ),
)
def test_shipped_libpq_gss_feature_probe_rejects_enabled_client_and_always_finishes(
    tmp_path: Path, status: int, error_message: bytes, expected_exit: int
) -> None:
    """Execute the exact shipped public API probe, including cleanup on rejection."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "gss_probe" for target in node.targets
            )
        )
        or (
            isinstance(node, ast.Try)
            and "Unused libpq GSSAPI feature remains enabled" in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    program = f"""import atexit, json, types
observed = {{"finish_calls": 0, "connect_arguments": []}}
class SyntheticConnection:
    status = {status!r}
    error_message = {error_message!r}
    def finish(self):
        observed["finish_calls"] += 1
def connect_start(conninfo):
    observed["connect_arguments"].append(conninfo.decode("ascii"))
    return SyntheticConnection()
pq = types.SimpleNamespace(PGconn=types.SimpleNamespace(connect_start=connect_start))
psycopg = types.SimpleNamespace(pq=types.SimpleNamespace(ConnStatus=types.SimpleNamespace(BAD=1)))
atexit.register(lambda: print(json.dumps(observed)))
""" + "\n".join(ast.unparse(node) for node in statements)
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        "finish_calls": 1,
        "connect_arguments": ["host=/tmp gssencmode=require"],
    }
    if expected_exit:
        assert "Unused libpq GSSAPI feature remains enabled" in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    "library,expected_exit",
    (
        ("libpq.so.5.18", 0),
        ("libkrb5support-helper.so.1", 0),
        ("libgssapi_krb5.so.2.2", 1),
        ("libk5crypto.so.3.1", 1),
        ("libkrb5.so.3.3", 1),
        ("libkrb5support.so.0.1", 1),
    ),
)
def test_shipped_loaded_native_guard_rejects_each_unused_gss_family(
    tmp_path: Path, library: str, expected_exit: int
) -> None:
    """Real fixture map data exercises the shipped family guard without host maps."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "gss_families"
                for target in node.targets
            )
        )
        or (
            isinstance(node, ast.If)
            and "Unused Kerberos native runtime remains loaded" in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    fixture = tmp_path / "synthetic-maps.txt"
    fixture.write_text(f"1000-2000 r--p 00000000 00:00 0 /usr/local/lib/{library}\n")
    program = "from pathlib import Path\n" + "\n".join(ast.unparse(node) for node in statements)
    program = program.replace("'/proc/self/maps'", repr(str(fixture)))
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_exit, result.stdout + result.stderr
    if expected_exit:
        assert "Unused Kerberos native runtime remains loaded" in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    "scenario,library,expected_message",
    (
        ("empty", "unrelated.so.1", None),
        ("present", "libgssapi_krb5.so.2.2", "Unused Kerberos library remains"),
        ("present", "libk5crypto.so.3.1", "Unused Kerberos library remains"),
        ("present", "libkrb5.so.3.3", "Unused Kerberos library remains"),
        ("present", "libkrb5support.so.0.1", "Unused Kerberos library remains"),
        ("missing_directory", "unrelated.so.1", "FileNotFoundError"),
        ("non_directory", "unrelated.so.1", "NotADirectoryError"),
    ),
)
def test_shipped_physical_gss_guard_rejects_files_and_required_directory_errors(
    tmp_path: Path, scenario: str, library: str, expected_message: str | None
) -> None:
    """Real scandir input cannot turn an unavailable mandatory directory into absence."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split("<<'PY_NATIVE_PSYCOPG'\n", 1)[1].split("\nPY_NATIVE_PSYCOPG", 1)[0]
    statements = [
        node
        for node in ast.parse(source).body
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "gss_families"
                for target in node.targets
            )
        )
        or (
            isinstance(node, ast.For)
            and "Unused Kerberos library remains in a required native directory"
            in ast.unparse(node)
        )
    ]
    assert len(statements) == 2
    native = tmp_path / "native-library-directory"
    system = tmp_path / "system-library-directory"
    native.mkdir()
    if scenario == "non_directory":
        system.write_text("synthetic non-directory")
    elif scenario != "missing_directory":
        system.mkdir()
        (system / library).write_bytes(b"synthetic physical native bytes")
    program = "import os\n" + "\n".join(ast.unparse(node) for node in statements)
    program = program.replace("'/usr/local/lib'", repr(str(native)))
    program = program.replace("'/usr/lib/x86_64-linux-gnu'", repr(str(system)))
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == (1 if expected_message else 0), result.stdout + result.stderr
    if expected_message:
        assert expected_message in result.stderr
    else:
        assert not result.stderr


@pytest.mark.parametrize(
    "inventory,expected_message",
    (
        (["ii libgssapi-krb5-2"], "An original native package remains installed"),
        (["ii libk5crypto3"], "An original native package remains installed"),
        (["ii libkrb5-3:amd64"], "An original native package remains installed"),
        (["ii libkrb5support0"], "An original native package remains installed"),
        (["rc libkrb5-3", "ii libkrb5-helper"], None),
        ([""], "Package inventory is malformed after native replacement"),
        (["ii"], "Package inventory is malformed after native replacement"),
        (["ii libkrb5-3 extra"], "Package inventory is malformed after native replacement"),
    ),
)
def test_existing_package_guard_rejects_kerberos_and_preserves_typed_inventory_errors(
    tmp_path: Path, inventory: list[str], expected_message: str | None
) -> None:
    """Execute the existing retirement loop, preserving exact package membership."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    source = dockerfile.split('retired = {"zlib1g"', 1)[1].split("\nssl_root", 1)[0]
    source = 'retired = {"zlib1g"' + source
    program = f"rows = {inventory!r}\n" + source
    result = subprocess.run(
        [sys.executable, "-c", program],
        cwd=tmp_path,
        env={"PATH": os.defpath, "HOME": str(tmp_path), "LANG": "C.UTF-8"},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == (1 if expected_message else 0), result.stdout + result.stderr
    if expected_message:
        assert expected_message in result.stderr
    else:
        assert not result.stderr


_ZLIB_MAINTENANCE_PATCHES = (
    (
        "zlib-gzwrite-null-fix",
        ("e3dc0a85" "b7032e98" "380dec01" "1bc8f2c2" "ee0d8fca"),
        ("2d97c97e" "020dfe05" "9b8b1981" "95a8fe42" "197f88b1" "184bb9ef" "0292a8af" "a535aa26"),
        ("8be18219" "a658f1dd" "fa83d4e8" "f778d2c3" "be1ade11" "3863f166" "3929c399" "02e001cc"),
    ),
    (
        "zlib-gzvprintf-return-fix",
        ("bbc2ccf3" "d0de2675" "76b524b8" "75c769a7" "24a513b0"),
        ("28af72a5" "d4d20648" "1956ab11" "ab164090" "7577bc0c" "021ef3b5" "8344ea64" "f00c764c"),
        ("96bd1c24" "2f09b244" "430bfe78" "54a9bb57" "a6e24a1e" "38e93bce" "f8ba946d" "22ecaf16"),
    ),
    (
        "zlib-gzprintf-return-fix",
        ("7235b0a5" "81227c56" "a79a43ff" "828f8ef6" "794194c8"),
        ("84bd6874" "0f1bf101" "fa85d3dd" "726a9c9b" "ec84c216" "3adf5b7b" "5c004bba" "62db6d5d"),
        ("c5eff1cc" "8dd1997b" "16e0918e" "bf6074b9" "9bd38b2c" "244fb2bf" "2b697e74" "541a0987"),
    ),
    (
        "zlib-blocked-errno-fix",
        ("813dac5d" "cb5902ed" "241e9b0d" "38abd2d8" "47a335a9"),
        ("d4fbd685" "ed4c2ec2" "d5e4962f" "0f6d5a98" "5ab1f542" "0bc1224d" "d262b419" "e7c26ab5"),
        ("b1fcf877" "5123d729" "0a11e952" "21632fca" "7406cce1" "73820a09" "392c659e" "adb0ba0a"),
    ),
    (
        "zlib-gzprintf-contract-fix",
        ("d81c2d7e" "b705c622" "94ba0329" "92556720" "78e89115"),
        ("e9216856" "034689c7" "1656fb32" "dd1b25d3" "2304baf4" "42b7e9b8" "d454c732" "187b0bcf"),
        ("22adf550" "e344229d" "f577ce66" "fddfce16" "451eb605" "20e8f68e" "5cae2192" "1b9bc0ea"),
    ),
    (
        "zlib-errno-order-fix",
        ("a82e0db3" "92178a3e" "05fb27bf" "551a6ce7" "57a47898"),
        ("33b8bc65" "706a2b85" "2e4b7ede" "ce112f13" "59078b3c" "8e475079" "d7b8d92d" "d4931d47"),
        ("c12fbe1d" "d31e27c3" "90d4552c" "3862fe6b" "c50169c7" "3ab97a74" "e81682b6" "a713f1f9"),
    ),
)


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
def test_zlib_maintenance_manifest_keeps_exact_official_patch_identities(
    name: str, commit: str, sha3: str, sha2: str
) -> None:
    artifacts = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 9)
    )
    matches = [artifact for artifact in artifacts if artifact.name == name]
    assert len(matches) == 1
    artifact = matches[0]
    assert (
        artifact.version,
        artifact.url,
        artifact.filename,
        artifact.sha3_256,
        artifact.sha256,
    ) == (
        commit,
        f"https://github.com/madler/zlib/commit/{commit}.patch?full_index=1",
        f"{name}-{commit}.patch",
        sha3,
        sha2,
    )


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
@pytest.mark.parametrize("field", ["version", "url", "filename", "sha3_256", "sha256"])
def test_zlib_maintenance_identity_drift_rejected_before_cache_or_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    commit: str,
    sha3: str,
    sha2: str,
    field: str,
) -> None:
    artifact = docker_sources.DockerSourceArtifact(
        name=name,
        version=commit,
        filename=f"{name}-{commit}.patch",
        url=f"https://github.com/madler/zlib/commit/{commit}.patch?full_index=1",
        sha3_256=sha3,
        sha256=sha2,
    )
    value = getattr(artifact, field)
    assert isinstance(value, str)
    corrupted = replace(artifact, **{field: value + "other"})
    calls = _stub_source_transport(monkeypatch, payload=b"unused")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="reviewed identity"):
        docker_sources._write_verified_artifact(corrupted, output)
    assert calls == []
    assert not output.exists()


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
@pytest.mark.parametrize("code", [301, 302, 303, 307, 308])
def test_zlib_maintenance_redirects_use_real_rejecting_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    commit: str,
    sha3: str,
    sha2: str,
    code: int,
) -> None:
    artifact = docker_sources.DockerSourceArtifact(
        name=name,
        version=commit,
        filename=f"{name}-{commit}.patch",
        url=f"https://github.com/madler/zlib/commit/{commit}.patch?full_index=1",
        sha3_256=sha3,
        sha256=sha2,
    )
    calls = _stub_source_transport(
        monkeypatch, payload=b"redirected patch", code=code, location=artifact.url
    )
    output = tmp_path / "sources"
    with pytest.raises(HTTPError):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("name,commit,sha3,sha2", _ZLIB_MAINTENANCE_PATCHES)
def test_zlib_maintenance_payload_rejects_wrong_actual_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, commit: str, sha3: str, sha2: str
) -> None:
    artifact = docker_sources.DockerSourceArtifact(
        name=name,
        version=commit,
        filename=f"{name}-{commit}.patch",
        url=f"https://github.com/madler/zlib/commit/{commit}.patch?full_index=1",
        sha3_256=sha3,
        sha256=sha2,
    )
    calls = _stub_source_transport(monkeypatch, payload=b"different actual patch bytes")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


def test_zlib_maintenance_docker_recipe_binds_exact_order_and_source_fingerprints() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    native = dockerfile.split(" AS native-builder\n", 1)[1].split("\nFROM ", 1)[0]
    prefix = native.split("./configure --prefix=/usr/local --libdir=/usr/local/lib --shared", 1)[0]
    commits = [record[1] for record in _ZLIB_MAINTENANCE_PATCHES]
    names = [record[0] for record in _ZLIB_MAINTENANCE_PATCHES]
    names.insert(2, "zlib-gzwrite-fix")
    commits.insert(2, ("df84af25" "dc194249" "0e1d1c89" "9a076191" "52a46148"))
    expected = [
        f"patch --batch --forward --fuzz=0 --no-backup-if-mismatch -p1 --input /input/native/{name}-{commit}.patch"
        for name, commit in zip(names, commits)
    ]
    assert [line for line in prefix.splitlines() if line.startswith("patch ")] == expected
    dockerignore = (REPO_ROOT / ".dockerignore").read_text()
    for name, commit in zip(names, commits):
        filename = f"{name}-{commit}.patch"
        assert f"build/docker-sources/{filename}" in prefix
        assert f"!build/docker-sources/{filename}" in dockerignore
    assert "set(before) != set(after)" in prefix
    assert "len(before) != 254" in prefix
    assert "!= set(expected)" in prefix
    for name, digest in (
        (
            "gzguts.h",
            (
                "6c366344"
                "bc1f1e25"
                "3892a33e"
                "06a01e97"
                "005c9340"
                "f9a44f93"
                "1e6cec8c"
                "b9878ffc"
            ),
        ),
        (
            "gzread.c",
            (
                "22178dd5"
                "092c89bc"
                "46e0a3eb"
                "bcd808f0"
                "3e8aafa3"
                "15c2a452"
                "4a6a0a2f"
                "f7c65038"
            ),
        ),
        (
            "gzwrite.c",
            (
                "548eb543"
                "23313b70"
                "b74a5564"
                "a61ccd4b"
                "968200ef"
                "89cbb70a"
                "6152d50b"
                "373515c5"
            ),
        ),
        (
            "zlib.h",
            (
                "648069fd"
                "ae548705"
                "c3a1c02d"
                "ac97a1dd"
                "7794e9e0"
                "bd32b46f"
                "b2afb357"
                "164b8037"
            ),
        ),
    ):
        assert name in prefix
        assert all(part in prefix for part in [digest[i : i + 8] for i in range(0, 64, 8)])


@pytest.mark.parametrize("bad_name", [[], {}])
def test_zlib_maintenance_manifest_refuses_unhashable_names(
    tmp_path: Path, bad_name: object
) -> None:
    manifest = json.loads((REPO_ROOT / "scripts/ci/docker_source_artifacts.json").read_text())
    row = next(
        record for record in manifest["artifacts"] if record["name"] == "zlib-gzwrite-null-fix"
    )
    row["name"] = bad_name
    path = _write_docker_source_manifest(tmp_path, manifest)
    with pytest.raises(RuntimeError, match="Only exact reviewed zlib patches"):
        docker_sources.load_manifest(path, today=date(2026, 10, 9))


def test_prometheus_metadata_mode_is_explicit_and_independent() -> None:
    """The qualifier cannot select or publish a Prometheus runtime."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    events = workflow.get("on", workflow.get(True))
    assert events["workflow_dispatch"]["inputs"]["mode"]["options"] == [
        "disabled",
        "normal",
        "prometheus-source-qualify",
        "backend-sdk-qualify",
        "prometheus-oras-qualify",
        "prometheus-source-pair",
    ]
    assert events["workflow_dispatch"]["inputs"]["prometheus_module_action"] == {
        "description": "Explicit Prometheus metadata module action; unchanged retains original locks",
        "type": "choice",
        "required": True,
        "default": "unchanged",
        "options": ["unchanged", "xnet060-replay"],
    }
    jobs = workflow["jobs"]
    qualification = jobs["prometheus-source-qualification"]
    assert "needs" not in qualification
    assert qualification["permissions"] == {"contents": "read"}
    assert qualification["timeout-minutes"] == (
        "${{ fromJSON(vars.PROMETHEUS_SOURCE_QUALIFICATION_TIMEOUT_MINUTES || '20') }}"
    )
    assert qualification["if"] == (
        "github.event_name == 'workflow_dispatch' && "
        "inputs.mode == 'prometheus-source-qualify' && "
        "github.repository == 'Katsiarynakavaleuskaya/PulsePlate'"
    )
    assert jobs["build"]["if"] == (
        "github.event_name != 'workflow_dispatch' || inputs.mode == 'normal'"
    )
    assert jobs["publish"]["needs"] == ["build", "security-scan"]
    command = _step_by_name(qualification, "Qualify Prometheus package metadata only")["run"]
    assert "-m scripts.ci.prometheus_source_image" in command
    assert "$PROMETHEUS_QUALIFICATION_SECONDS" in command
    assert "$PROMETHEUS_CLEANUP_SECONDS" in command
    step = _step_by_name(qualification, "Qualify Prometheus package metadata only")
    assert step["env"] == {"PROMETHEUS_MODULE_ACTION": "${{ inputs.prometheus_module_action }}"}
    assert 'case "$PROMETHEUS_MODULE_ACTION" in' in command
    assert "xnet060-replay) module_args+=(--derive-xnet060)" in command
    assert '"${module_args[@]}"' in command
    assert "${{ inputs.prometheus_module_action }}" not in command
    assert "buildx" not in command and "secrets." not in command
    assert not any("secrets." in str(step) for step in qualification["steps"])
    checkout = _step_by_name(qualification, "Checkout qualification source")
    assert checkout["with"]["persist-credentials"] is False


def test_prometheus_publisher_verifies_retained_original_signed_bundles() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    jobs = workflow["jobs"]
    pair = jobs["prometheus-source-build-pair"]
    attestations = [
        step for step in pair["steps"] if step.get("uses", "").startswith("actions/attest@")
    ]
    assert len(attestations) == 2
    for step in attestations:
        assert step["with"]["push-to-registry"] is False
        assert step["with"]["create-storage-record"] is False
    publisher = jobs["prometheus-publish"]
    assert [step["name"] for step in publisher["steps"]] == [
        "Checkout exact main producer",
        "Promote precise retained bytes and pull them back",
        "Retain main publication and pullback",
    ]
    promote = _step_by_name(publisher, "Promote precise retained bytes and pull them back")
    assert promote["id"] == "published"
    assert promote["env"] == {
        "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
    }
    assert "--operation promote" in promote["run"]
    assert '--cleanup-seconds "$PROMETHEUS_CLEANUP_SECONDS"' in promote["run"]
    assert "DOCKER_CONFIG" not in str(publisher)
    assert not any(
        step.get("uses", "").startswith("docker/login-action@") for step in publisher["steps"]
    )


def test_security_scan_excludes_pr_registry_credentials_even_when_token_available() -> None:
    """Exact event guards exclude PR credentials while retaining non-PR DB behavior."""
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    job = workflow["jobs"]["security-scan"]
    assert job["env"] == {"GHCR_READ_TOKEN_AVAILABLE": "${{ secrets.GHCR_READ_TOKEN != '' }}"}
    login = _step_by_name(job, "Log in to GHCR (Trivy DB)")
    assert login["if"] == (
        "${{ github.event_name != 'pull_request' && env.GHCR_READ_TOKEN_AVAILABLE == 'true' }}"
    )
    assert login["env"] == {
        "GHCR_READ_TOKEN": (
            "${{ github.event_name != 'pull_request' && secrets.GHCR_READ_TOKEN || '' }}"
        )
    }
    assert (
        'docker login ghcr.io -u "${{ github.repository_owner }}" --password-stdin' in login["run"]
    )
    assert "continuing without registry auth" in login["run"]
    scan = _step_by_name(job, "Run Trivy vulnerability scanner (filesystem scan)")
    assert scan["with"]["version"] == "v0.74.0"
    assert scan["with"]["severity"] == "CRITICAL,HIGH"
    assert scan["with"]["exit-code"] == "1"
    assert scan["with"]["scanners"] == "vuln"
    assert scan["with"]["ignore-policy"] == ".trivy-ignore-policy.rego"
    assert "continue-on-error" not in scan
    sarif = _step_by_name(job, "Check Trivy filesystem SARIF output")
    assert sarif["if"] == "${{ always() }}"
    assert 'echo "present=false"' in sarif["run"]
    upload = _step_by_name(job, "Upload Trivy scan results to GitHub Security tab")
    assert upload["if"] == "${{ always() && steps.trivy_fs_sarif.outputs.present == 'true' }}"
    assert upload["continue-on-error"] is True


def test_manual_oras_prefetch_selector_is_data_and_preserves_compile_budget() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "build.yml")
    inputs = workflow.get("on", workflow.get(True))["workflow_dispatch"]["inputs"]
    assert inputs["tool_prefetch_predecessor"] == {
        "description": "Exact failed precompile run:artifact evidence selector; no dispatch authorization",
        "type": "string",
        "required": False,
        "default": "",
    }
    job = workflow["jobs"]["prometheus-oras-qualification"]
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    assert job["env"]["PROMETHEUS_TOOL_SECONDS"] == "1800"
    assert job["env"]["PROMETHEUS_CLEANUP_SECONDS"] == "120"
    step = _step_by_name(job, "Compile one ORAS tool and qualify native format")
    assert step["env"] == {
        "GH_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
        "TOOL_PREFETCH_PREDECESSOR": "${{ inputs.tool_prefetch_predecessor }}",
    }
    assert "predecessor=()" in step["run"]
    assert 'predecessor=(--tool-prefetch-predecessor "$TOOL_PREFETCH_PREDECESSOR")' in step["run"]
    assert '"${predecessor[@]}"' in step["run"]
    assert step["run"].count("--operation tool") == 1
    pair = workflow["jobs"]["prometheus-source-build-pair"]
    assert "tool_prefetch_predecessor" not in str(pair)
    assert not any("continue-on-error" in value for value in job["steps"])


def test_alertmanager_catalog_selector_preserves_incumbent_default_inputs() -> None:
    manifest = REPO_ROOT / "scripts/ci/docker_source_artifacts.json"
    incumbent = docker_sources.load_manifest(manifest)
    selected = docker_sources.load_manifest(manifest, artifact="alertmanager")
    assert len(incumbent) == 15
    assert not any(item.name.startswith("alertmanager-") for item in incumbent)
    assert {item.name for item in selected} == {"alertmanager-source", "alertmanager-ui"}
    assert {item.sha256 for item in selected} == {
        "5c5c72ec6b4c4746d523f2ed1994dfec4b94f7457e530ee6fb16cfec158e545e",
        "881fe0f7beb9573f35be47dd233af6220e72c8db72c03bcd1780402eb8dc1307",
    }
    with pytest.raises(RuntimeError, match="finite Alertmanager selector"):
        docker_sources.load_manifest(manifest, artifact="fetch-all")


@pytest.mark.parametrize("name", ["alertmanager-source", "alertmanager-ui"])
def test_alertmanager_archive_rejects_changed_bytes_before_member_admission(name: str) -> None:
    selected = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
    )
    artifact = next(item for item in selected if item.name == name)
    with pytest.raises(RuntimeError, match="SHA3 mismatch"):
        docker_sources.validate_source_payload(artifact, b"unqualified source or UI")


def test_alertmanager_transport_does_not_retry_source_service_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from email.message import Message
    from urllib.error import HTTPError
    from scripts.ci import prometheus_source_image as transport
    import io
    import time

    selected = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
    )
    artifact = next(item for item in selected if item.name == "alertmanager-source")
    calls: list[str] = []

    class FailedTransport:
        def open(self, request: object, *, timeout: float) -> object:
            calls.append(request.full_url)
            raise HTTPError(
                artifact.url,
                503,
                "synthetic unavailable",
                Message(),
                io.BytesIO(b"synthetic failure"),
            )

    monkeypatch.setattr(transport, "opener", lambda: FailedTransport())
    with pytest.raises(RuntimeError, match="initial HTTP status 503"):
        docker_sources._download_alertmanager(
            artifact, deadline=time.monotonic() + 5, private=tmp_path
        )
    assert calls == [artifact.url]
    assert (tmp_path / "alertmanager-source-initial.http-body").read_bytes() == b"synthetic failure"
    assert (
        json.loads((tmp_path / "alertmanager-source-http.json").read_text())[0][
            "actual_http_status"
        ]
        == 503
    )


@pytest.mark.parametrize(
    "location",
    [
        "https://unapproved.invalid/private?synthetic=only",
        "https://release-assets.githubusercontent.com/github-production-release-asset/11434314/12345678-1234-1234-1234-123456789abc?synthetic=only\n",
    ],
)
def test_alertmanager_transport_rejects_unapproved_handoff_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
) -> None:
    from email.message import Message
    from urllib.error import HTTPError
    from scripts.ci import prometheus_source_image as transport
    import io
    import time

    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
        )
        if item.name == "alertmanager-ui"
    )
    headers = Message()
    headers["Location"] = location
    calls: list[str] = []

    class WrongHandoff:
        def open(self, request: object, *, timeout: float) -> object:
            calls.append(request.full_url)
            raise HTTPError(artifact.url, 302, "synthetic handoff", headers, io.BytesIO(b""))

    monkeypatch.setattr(transport, "opener", lambda: WrongHandoff())
    with pytest.raises(RuntimeError, match="handoff authority"):
        docker_sources._download_alertmanager(
            artifact, deadline=time.monotonic() + 5, private=tmp_path
        )
    assert calls == [artifact.url]


def test_alertmanager_bootstrap_skip_covers_every_shared_install_effect() -> None:
    action = _load_workflow(REPO_ROOT / ".github/actions/python-setup/action.yml")
    steps = {step["name"]: step for step in action["runs"]["steps"]}
    for name in (
        "Configure private Python index authentication",
        "Build exact Psycopg C client SDK",
        "Install base dependencies",
        "Observe installed native Python consumers",
    ):
        assert steps[name]["if"] == "${{ inputs.skip-base-install != 'true' }}"
    assert steps["Retain untrusted rejected zlib response"]["if"] == (
        "${{ failure() && steps.psycopg_sdk.outcome == 'failure' "
        "&& steps.psycopg_sdk.outputs.rejection_dir != '' }}"
    )
    assert steps["Remove private Python index authentication"]["if"] == "${{ always() }}"


def test_alertmanager_bootstrap_delegates_binary_only_two_pass_startup_guards() -> None:
    import inspect
    from scripts.ci import install_locked_python_requirements as installer

    command = installer.build_pip_proxy_install_command(
        python_executable="/absolute/owned-AM/bin/python",
        requirement_file=REPO_ROOT / "requirements-dev.txt",
        constraints_file=REPO_ROOT / "constraints.txt",
        index_url="https://synthetic.invalid/simple",
        trusted_host=None,
        allow_pip_download_cache=False,
    )
    assert command[:4] == ["/absolute/owned-AM/bin/python", "-m", "pip", "install"]
    assert "--no-deps" in command and command[command.index("--only-binary") + 1] == ":all:"
    assert command[command.index("--requirement") + 1] == str(REPO_ROOT / "requirements-dev.txt")
    assert command[command.index("--constraint") + 1] == str(REPO_ROOT / "constraints.txt")
    source = inspect.getsource(installer.install_with_guard_from_proxy)
    normal = source.split(
        "with staged_python_environment(python_executable) as staging_python:", 1
    )[1]
    assert normal.count("install_from_proxy_with_emergency_fallback(") == 2
    assert normal.count("collect_startup_hook_failure_lines(") == 2
    assert (
        normal.index("python_executable=staging_python")
        < normal.index("collect_startup_hook_failure_lines(")
        < normal.index("python_executable=python_executable")
        < normal.rindex("collect_startup_hook_failure_lines(")
    )
    assert "if failure_lines:" in normal and "return 1" in normal
    transport = inspect.getsource(installer.run_command)
    assert "PIP_CHILD_SELECTOR" in transport
    assert "_install_pip_transport_guard()" in inspect.getsource(installer._run_owned_pip_child)


@pytest.mark.parametrize(
    "job_name",
    [
        "alertmanager-retained-candidate",
        "alertmanager-main-publication",
    ],
)
def test_alertmanager_bootstrap_is_isolated_guarded_and_precedes_all_host_effects(
    job_name: str,
) -> None:
    from scripts.ci import install_locked_python_requirements as installer

    job = _load_workflow(WORKFLOWS_DIR / "cd.yml")["jobs"][job_name]
    if job_name == "alertmanager-main-publication":
        assert _step_by_name(job, "Checkout exact AM executable proposal")["with"] == {
            "ref": "${{ github.sha }}",
            "persist-credentials": False,
            "fetch-depth": 0,
        }
    setup = next(
        step for step in job["steps"] if step.get("uses") == "./.github/actions/python-setup"
    )
    assert setup["with"] == {"python-version": "3.13.14", "skip-base-install": "true"}
    install = _step_by_name(job, "Install isolated AM host tools through the locked owner")
    smoke = _step_by_name(job, "Verify isolated AM host import capability before effects")
    driver = (
        _step_by_name(job, "Run full accepted AM native controls on this runner")
        if job_name == "alertmanager-retained-candidate"
        else next(
            step
            for step in job["steps"]
            if "--artifact alertmanager --alertmanager-stage" in step.get("run", "")
        )
    )
    if job_name == "alertmanager-retained-candidate":
        preparation = _step_by_name(job, "Prepare exact AM subject before material execution")
        assert _step_index(job, preparation["name"]) < _step_index(job, setup["name"])
        assert "python3 -E -s -S -m" in preparation["run"]
        assert "--alertmanager-prepare-only" in preparation["run"]
    assert (
        _step_index(job, "Validate existing credential-free AM native Python proxy")
        < _step_index(job, setup["name"])
        < _step_index(job, install["name"])
        < _step_index(job, smoke["name"])
        < _step_index(job, driver["name"])
    )
    assert smoke["id"] == "am-python"
    assert "GITHUB_OUTPUT" not in install["run"]
    if job_name == "alertmanager-retained-candidate":
        assert 'native_python="${{ steps.am-python.outputs.python }}"' in driver["run"]
        assert "/usr/bin/env -i" in driver["run"]
    else:
        assert driver["env"]["AM_HOST_PYTHON"] == "${{ steps.am-python.outputs.python }}"
    for step in (setup, install):
        assert step["env"]["PULSEPLATE_PYTHON_INDEX_URL"] == (
            "${{ vars.PULSEPLATE_PYTHON_INDEX_URL }}"
        )
        assert step["env"]["PULSEPLATE_PYTHON_TRUSTED_HOST"] == (
            "${{ vars.PULSEPLATE_PYTHON_TRUSTED_HOST }}"
        )
        assert step["env"]["DEVPI_CI_USER"] == step["env"]["DEVPI_CI_PASSWORD"] == ""
    for step in (
        (install, smoke)
        if job_name == "alertmanager-retained-candidate"
        else (install, smoke, driver)
    ):
        assert step["env"]["PYTHONHOME"] == step["env"]["PYTHONPATH"] == ""
        assert step["env"]["PYTHONNOUSERSITE"] == "1"
        assert "HOME" not in step["env"] and "PATH" not in step["env"]
    for key in (
        "PULSEPLATE_PSYCOPG_C_SDK",
        "PULSEPLATE_DOCKER_SINGLE_PASS_LOCKED_INSTALL",
        "PULSEPLATE_DOCKER_PIP_LAYER_CACHE",
    ):
        assert install["env"][key] == ""
    run = install["run"]
    root = 'am_root="$RUNNER_TEMP/pulseplate-am-python-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT"'
    assert root in run and root in smoke["run"]
    assert (
        run.index('test ! -e "$am_root"')
        < run.index('test ! -L "$am_root"')
        < run.index('python -I -m venv "$am_root"')
        < run.index('mkdir "$am_root/installer-home"')
    )
    assert "umask 077" in run and "--system-site-packages" not in run
    assert 'am_python="$am_root/bin/python"' in run
    installer_call = (
        'HOME="$am_root/installer-home" "$am_python" -I '
        '"$GITHUB_WORKSPACE/scripts/ci/install_locked_python_requirements.py"'
    )
    assert run.count(installer_call) == 3
    upgrade = "--upgrade-pip-only --upgrade-pip-spec 'pip==26.2.2'"
    observation = "import pip._vendor.certifi"
    preflight = '"${install_args[@]}" --preflight-only'
    final_install = run.rindex(installer_call)
    assert run.index(upgrade) < run.index(observation) < run.index(preflight) < final_install
    assert 'version != "26.2.2"' in run
    assert 'trust != "50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785"' in run
    block = run.split("install_args=(\n", 1)[1].split("\n)", 1)[0]
    flags = shlex.split(block)
    args = installer.parse_args(flags)
    assert args.python_executable == "$am_python"
    assert args.requirements_file == Path("$GITHUB_WORKSPACE/requirements-dev.txt")
    assert args.constraints_file == Path("$GITHUB_WORKSPACE/constraints.txt")
    assert args.emergency_wheel_manifest == Path(
        "$GITHUB_WORKSPACE/scripts/ci/emergency_python_wheels.json"
    )
    assert args.require_virtualenv is True and args.install_mode == "direct-proxy"
    assert args.index_url == "$PULSEPLATE_PYTHON_INDEX_URL"
    assert args.requirements_profile is None and not args.install_dev and not args.install_test
    assert args.psycopg_sdk is None and not args.build_psycopg_c
    assert not args.upgrade_pip and not args.prefetch_only and not args.consume_only
    assert 'install_args+=(--trusted-host "$PULSEPLATE_PYTHON_TRUSTED_HOST")' in run
    assert "--no-deps" not in flags and "--only-binary" not in flags
    pins = installer._collect_unmarked_exact_requirement_pin_versions(
        (REPO_ROOT / "requirements-dev.txt").read_text().splitlines()
    )
    assert "pytest" in pins and "pyyaml" in pins
    assert "psycopg" not in pins and "psycopg-c" not in pins
    source = smoke["run"].split("\"$am_python\" - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    tree = ast.parse(source)
    assert {node.names[0].name for node in tree.body if isinstance(node, ast.Import)} == {
        "json",
        "site",
        "sys",
        "pytest",
        "yaml",
        *({"os", "shutil", "subprocess"} if job_name == "alertmanager-candidate-build" else set()),
    }
    for statement in (
        "from scripts.ci import fetch_docker_source_artifacts, prometheus_source_image",
        "from scripts.ops import notify_premium_alias_checkpoint_failure",
        "from tests import test_notify_premium_alias_checkpoint_failure as native",
        "assert sys.version_info[:3] == (3, 13, 14)",
        "assert sys.prefix != sys.base_prefix and sys.base_prefix not in site.PREFIXES",
        "assert site.ENABLE_USER_SITE is False",
        "with pytest.MonkeyPatch.context():",
        'assert yaml.safe_load("probe: true\\n") == {"probe": True}',
        "assert callable(native.native_alertmanager_main)",
    ):
        assert statement in source
    for package in ("pytest", "pyyaml"):
        assert (
            'version("'
            + ("PyYAML" if package == "pyyaml" else package)
            + '") == "'
            + (next(iter(pins[package])))
            + '"'
            in source
        )
    assert "metadata.distributions()" in source and 'metadata.version("pip")' in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "native_alertmanager_main"
        for node in ast.walk(tree)
    )
    help_call = '"$am_python" -m tests.test_notify_premium_alias_checkpoint_failure --help'
    assert help_call in smoke["run"]
    assert smoke["run"].index(help_call) < smoke["run"].index(
        'printf \'python=%s\\n\' "$am_python" >> "$GITHUB_OUTPUT"'
    )
    if job_name != "alertmanager-retained-candidate":
        assert '"$AM_HOST_PYTHON" -m scripts.ci.fetch_docker_source_artifacts' in driver["run"]
    else:
        assert (
            '"$native_python" -m tests.test_notify_premium_alias_checkpoint_failure --native-alertmanager'
            in driver["run"]
        )
    assert '"$AM_HOST_PYTHON" -I' not in driver["run"]
    for step in (install, smoke):
        for forbidden in (
            "GITHUB_ENV",
            "GITHUB_PATH",
            "--build-psycopg",
            "docker build",
            ".netrc",
            "--requirements-profile",
            "--install-dev",
            "--install-test",
        ):
            assert forbidden not in step["run"]


def test_alertmanager_bootstrap_has_one_aggregate_setup_budget() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "cd.yml")
    env = workflow["env"]
    parts = {
        "Select AM Python without dependency or SDK installation": "ALERTMANAGER_PYTHON_SETUP_MINUTES",
        "Install isolated AM host tools through the locked owner": "ALERTMANAGER_PYTHON_INSTALL_MINUTES",
        "Verify isolated AM host import capability before effects": "ALERTMANAGER_PYTHON_SMOKE_MINUTES",
    }
    assert [int(env[key]) for key in parts.values()] == [3, 6, 1]
    assert (
        sum(int(env[key]) for key in parts.values()) == int(env["ALERTMANAGER_SETUP_MINUTES"]) == 10
    )
    for restored in ("alertmanager-candidate-build", "alertmanager-input-inspection"):
        job = workflow["jobs"][restored]
        assert "github.event_name == 'workflow_dispatch'" in job["if"]
        assert "github.run_attempt == 1" in job["if"]
        assert "refs/heads/codex/python-setup-security-stabilization" in job["if"]
        assert job["permissions"] == {"contents": "read", "actions": "read", "packages": "read"}
    for name, cap in (
        ("alertmanager-retained-candidate", 80),
        ("alertmanager-main-publication", 110),
    ):
        job = workflow["jobs"][name]
        assert job["timeout-minutes"] == cap
        for step_name, key in parts.items():
            assert _step_by_name(job, step_name)["timeout-minutes"] == (
                "${{ fromJSON(env." + key + ") }}"
            )
    assert env["ALERTMANAGER_PREP_SECONDS"] == "600"
    assert env["ALERTMANAGER_NATIVE_SECONDS"] == "2400"
    assert env["ALERTMANAGER_CLEANUP_SECONDS"] == "45"
    assert env["ALERTMANAGER_NATIVE_CLEANUP_SECONDS"] == "120"
    assert env["ALERTMANAGER_UPLOAD_MINUTES"] == "5"


def test_alertmanager_module_mode_is_manual_first_attempt_and_build_is_held() -> None:
    workflow = _load_workflow(WORKFLOWS_DIR / "cd.yml")
    job = workflow["jobs"]["alertmanager-module-qualification"]
    admission = job["if"]
    assert "github.event_name == 'workflow_dispatch'" in admission
    assert "github.run_attempt == 1" in admission
    assert "github.repository == 'Katsiarynakavaleuskaya/PulsePlate'" in admission
    assert "inputs.alertmanager_mode == 'module-qualify'" in admission
    assert "inputs.alertmanager_mode == 'build'" not in admission
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    assert job["env"]["ALERTMANAGER_QUALIFY_SECONDS"] == "825"
    first = job["steps"][0]["run"]
    assert 'test "$ALERTMANAGER_MODE" = module-qualify' in first
    assert 'test "$SOURCE_SHA" = "$GITHUB_SHA"' in first
    checkout = _step_by_name(job, "Checkout authenticated Alertmanager preparation")
    assert checkout["with"] == {"ref": "${{ github.sha }}", "persist-credentials": False}
    qualification = _step_by_name(
        job, "Qualify exact inputs and modules under one metadata-only clock"
    )
    assert (
        _step_index(job, job["steps"][0]["name"])
        < _step_index(job, checkout["name"])
        < _step_index(job, qualification["name"])
    )
    assert qualification["run"].index('checkout_sha="$(git rev-parse HEAD)"') < (
        qualification["run"].index('test "$checkout_sha" = "$GITHUB_SHA"')
    )
    assert qualification["run"].index('test "$checkout_sha" = "$GITHUB_SHA"') < (
        qualification["run"].index("python3 -m scripts.ci.fetch_docker_source_artifacts")
    )
    runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert "docker login" not in runs and "docker push" not in runs
    assert "--artifact alertmanager --alertmanager-module-qualify" in runs


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "malformed_source",
        "different_source",
        "different_repository",
        "repeat_attempt",
        "build_mode",
        "different_api_revision",
        "api_failure",
        "different_checkout",
        "checkout_failure",
    ],
)
def test_alertmanager_module_mode_checks_exact_revision_before_qualification(
    tmp_path: Path, fault: str | None
) -> None:
    job = _load_workflow(WORKFLOWS_DIR / "cd.yml")["jobs"]["alertmanager-module-qualification"]
    qualification = _step_by_name(
        job, "Qualify exact inputs and modules under one metadata-only clock"
    )
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    marker = tmp_path / "qualified"
    scripts = {
        "gh": '#!/bin/sh\nprintf "%s\\n" "$SYNTHETIC_API_SHA"\nexit "$SYNTHETIC_API_EXIT"\n',
        "git": (
            '#!/bin/sh\n[ "$*" = "rev-parse HEAD" ] || exit 64\n'
            'printf "%s\\n" "$SYNTHETIC_CHECKOUT_SHA"\nexit "$SYNTHETIC_GIT_EXIT"\n'
        ),
        "python3": (
            '#!/bin/sh\n[ "$*" = "-m scripts.ci.fetch_docker_source_artifacts '
            '--artifact alertmanager --alertmanager-module-qualify" ] || exit 64\n'
            'printf "qualified\\n" > "$QUALIFICATION_MARKER"\n'
        ),
    }
    for name, body in scripts.items():
        executable = binary_dir / name
        executable.write_text(body)
        executable.chmod(0o755)
    revision = "a" * 40
    # An explicit environment excludes every host credential source, even for stubs.
    env = {
        "PATH": str(binary_dir),
        "HOME": str(tmp_path),
        "GH_CONFIG_DIR": str(tmp_path / "gh-config"),
        "GH_TOKEN": "synthetic-test-token",
        "GITHUB_TOKEN": "synthetic-test-token",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_RUN_ATTEMPT": "1",
        "SOURCE_SHA": revision,
        "GITHUB_SHA": revision,
        "ALERTMANAGER_MODE": "module-qualify",
        "SYNTHETIC_API_SHA": revision,
        "SYNTHETIC_API_EXIT": "0",
        "SYNTHETIC_CHECKOUT_SHA": revision,
        "SYNTHETIC_GIT_EXIT": "0",
        "QUALIFICATION_MARKER": str(marker),
    }
    mutations = {
        "malformed_source": ("SOURCE_SHA", "invalid"),
        "different_source": ("SOURCE_SHA", "b" * 40),
        "different_repository": ("GITHUB_REPOSITORY", "other/repository"),
        "repeat_attempt": ("GITHUB_RUN_ATTEMPT", "2"),
        "build_mode": ("ALERTMANAGER_MODE", "build"),
        "different_api_revision": ("SYNTHETIC_API_SHA", "b" * 40),
        "api_failure": ("SYNTHETIC_API_EXIT", "1"),
        "different_checkout": ("SYNTHETIC_CHECKOUT_SHA", "b" * 40),
        "checkout_failure": ("SYNTHETIC_GIT_EXIT", "1"),
    }
    if fault is not None:
        key, value = mutations[fault]
        env[key] = value
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", job["steps"][0]["run"] + "\n" + qualification["run"]],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert (result.returncode == 0) is (fault is None), result.stderr
    assert marker.exists() is (fault is None)


def test_alertmanager_literal_recipe_has_only_selected_payload_and_private_defaults() -> None:
    recipe = (REPO_ROOT / "deploy/alertmanager/Containerfile").read_text()
    assert "RUN " not in recipe and "ADD " not in recipe
    assert "COPY probe-bin-bracket /usr/bin/wget" in recipe
    assert "COPY probe-bin-bracket /usr/bin/httpd" in recipe
    assert "COPY alertmanager /usr/bin/alertmanager" in recipe
    assert "COPY amtool /usr/bin/amtool" in recipe
    assert "USER 65534:65534" in recipe
    assert "COPY --chown=65534:65534 --chmod=0700 storage-dir /alertmanager" in recipe
    assert len(recipe.encode()) == 908
    assert (
        sha256(recipe.encode()).hexdigest()
        == docker_sources._ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
        == "2c70a5f492866c30e2c7db69be001003c674ef0f16b336f94a8a23be2777de13"
    )
    assert (
        docker_sources._ALERT_Q_SOURCE_FILES["deploy/alertmanager/Containerfile"]
        == docker_sources._ALERT_S_SOURCE_FILES["deploy/alertmanager/Containerfile"]
        == "69af6364f15e3e5b9a4662a5919ff7f3b0209da0461cd7a85e01e21022abdb78"
    )
    assert '"--cluster.listen-address="' in recipe


@pytest.mark.parametrize("final_status", [200, 403])
def test_alertmanager_one_handoff_has_no_final_retry_and_retains_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_status: int,
) -> None:
    from email.message import Message
    from urllib.error import HTTPError
    from scripts.ci import prometheus_source_image as transport
    import io
    import time

    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
        )
        if item.name == "alertmanager-ui"
    )
    handoff = "https://release-assets.githubusercontent.com/github-production-release-asset/11434314/12345678-1234-1234-1234-123456789abc?synthetic=only"
    headers = Message()
    headers["Location"] = handoff
    calls: list[str] = []

    class Response(io.BytesIO):
        status = 200

        def geturl(self) -> str:
            return handoff

    class HandoffTransport:
        def open(self, request: object, *, timeout: float) -> object:
            calls.append(request.full_url)
            if len(calls) == 1:
                raise HTTPError(artifact.url, 302, "synthetic handoff", headers, io.BytesIO(b""))
            if final_status == 403:
                raise HTTPError(
                    handoff,
                    403,
                    "synthetic final rejection",
                    Message(),
                    io.BytesIO(b"private synthetic rejection"),
                )
            return Response(b"synthetic successful transport")

    monkeypatch.setattr(transport, "opener", lambda: HandoffTransport())
    if final_status == 403:
        with pytest.raises(RuntimeError, match="handoff HTTP status 403"):
            docker_sources._download_alertmanager(
                artifact, deadline=time.monotonic() + 5, private=tmp_path
            )
        records = json.loads((tmp_path / "alertmanager-ui-http.json").read_text())
        assert records[-1]["actual_http_status"] == 403
        assert records[-1]["diagnostic_read_error"] is None
        assert (
            tmp_path / "alertmanager-ui-handoff-final.http-body"
        ).stat().st_mode & 0o777 == 0o600
        assert handoff not in (tmp_path / "alertmanager-ui-http.json").read_text()
    else:
        assert (
            docker_sources._download_alertmanager(
                artifact, deadline=time.monotonic() + 5, private=tmp_path
            )
            == b"synthetic successful transport"
        )
    assert calls == [artifact.url, handoff]


def test_alertmanager_http_body_diagnostic_failure_preserves_primary_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from email.message import Message
    from urllib.error import HTTPError
    from scripts.ci import prometheus_source_image as transport
    import io
    import time

    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
        )
        if item.name == "alertmanager-source"
    )

    class BrokenBody(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            raise OSError("synthetic diagnostic read failure")

    class FailedTransport:
        def open(self, request: object, *, timeout: float) -> object:
            raise HTTPError(
                artifact.url, 503, "synthetic primary rejection", Message(), BrokenBody()
            )

    monkeypatch.setattr(transport, "opener", lambda: FailedTransport())
    with pytest.raises(RuntimeError, match="initial HTTP status 503"):
        docker_sources._download_alertmanager(
            artifact, deadline=time.monotonic() + 5, private=tmp_path
        )
    records = json.loads((tmp_path / "alertmanager-source-http.json").read_text())
    assert records[0]["actual_http_status"] == 503
    assert records[0]["diagnostic_read_error"] == "OSError"
    assert (tmp_path / "alertmanager-source-http.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("exit_code", [0, 17])
def test_alertmanager_native_attach_success_does_not_admit_failed_go_exit(exit_code: int) -> None:
    identifier, name, token = "a" * 64, "pulseplate-alert-module-synthetic", "synthetic"
    observed = {
        "Id": identifier,
        "Name": "/" + name,
        "Config": {"Labels": {"pulseplate.alertmanager-module": token}},
        "State": {
            "Status": "exited",
            "Running": False,
            "Restarting": False,
            "Dead": False,
            "OOMKilled": False,
            "Error": "",
            "ExitCode": exit_code,
        },
    }
    # Docker attach itself can return 0; the native wait/state remains independent truth.
    if exit_code:
        with pytest.raises(RuntimeError, match="Actual Alertmanager container command exit"):
            docker_sources._alertmanager_command_exit(observed, identifier, name, token, b"17\n")
    else:
        docker_sources._alertmanager_command_exit(observed, identifier, name, token, b"0\n")


def test_alertmanager_oversized_cache_is_rejected_before_read_or_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
        )
        if item.name == "alertmanager-source"
    )
    cached = tmp_path / artifact.filename
    with cached.open("wb") as stream:
        stream.truncate(docker_sources._ALERT_SIZES[artifact.name] + 1)
    original_read = Path.read_bytes

    def trapped_read(path: Path) -> bytes:
        if path == cached:
            raise AssertionError("oversized cache must never be read")
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", trapped_read)
    monkeypatch.setattr(
        docker_sources,
        "_download_alertmanager",
        lambda *args, **kwargs: pytest.fail("bad cache must not be replaced"),
    )
    with pytest.raises(RuntimeError, match="cached exact size"):
        docker_sources._write_verified_artifact(artifact, tmp_path)
    assert cached.stat().st_size == docker_sources._ALERT_SIZES[artifact.name] + 1


@pytest.mark.parametrize("foreign", [False, True])
def test_alertmanager_cleanup_requires_actual_create_id_before_any_remove(
    tmp_path: Path,
    foreign: bool,
) -> None:
    owned, identifier = "a" * 64, ("b" if foreign else "a") * 64
    calls: list[list[str]] = []

    class SyntheticNative:
        def run(self, argv: list[str], *args: object, **kwargs: object) -> bytes:
            calls.append(argv)
            if "inspect" in argv:
                return json.dumps(
                    {
                        "Id": identifier,
                        "Name": "/owned",
                        "Config": {"Labels": {"pulseplate.alertmanager-module": "token"}},
                    }
                ).encode()
            return b""

    if foreign:
        with pytest.raises(RuntimeError, match="actual retained create identity"):
            docker_sources._alertmanager_cleanup_member(
                SyntheticNative(),
                "/absolute/docker",
                identifier,
                {owned},
                {"owned"},
                "token",
                {},
                tmp_path,
                0,
                tmp_path,
            )
        assert calls == []
    else:
        docker_sources._alertmanager_cleanup_member(
            SyntheticNative(),
            "/absolute/docker",
            identifier,
            {owned},
            {"owned"},
            "token",
            {},
            tmp_path,
            0,
            tmp_path,
        )
        assert calls[-1] == ["/absolute/docker", "--config", str(tmp_path), "rm", "--force", owned]


def _alertmanager_cache_row(path: str, body: bytes, mode: int = 0o444) -> dict[str, object]:
    return {"path": path, "size": len(body), "mode": mode, "sha256": sha256(body).hexdigest()}


@pytest.fixture
def alertmanager_replays() -> list[dict[str, Any]]:
    first = {
        "original": {"go.mod": b"module example.org/main\n", "go.sum": b"original sums\n"},
        "derived": {"go.mod": b"module example.org/main\n", "go.sum": b"derived sums\n"},
        "modules": [{"Path": "example.org/dependency", "Version": "v1.2.3"}],
        "graph": [b"example.org/main example.org/dependency@v1.2.3"],
        "packages": {
            "alertmanager": [{"ImportPath": "example.org/main/cmd/alertmanager"}],
            "amtool": [{"ImportPath": "example.org/main/cmd/amtool"}],
        },
        "delta": [{"path": "example.org/dependency", "before": "v1.2.2", "after": "v1.2.3"}],
        "source": [_alertmanager_cache_row("go.mod", b"module example.org/main\n")],
        "version": b"go version go1.27.2 linux/amd64\n",
        "module_cache": [
            _alertmanager_cache_row("cache/download/example.org/dependency/@v/v1.2.3.mod", b"mod"),
            _alertmanager_cache_row("cache/download/example.org/dependency/@v/v1.2.3.zip", b"zip"),
            _alertmanager_cache_row(
                "cache/download/sumdb/sum.golang.org/lookup/module@v1.2.3", b"first lookup", 0o600
            ),
            _alertmanager_cache_row(
                "cache/download/sumdb/sum.golang.org/tile/8/0/001.p/2", b"first tile", 0o600
            ),
            _alertmanager_cache_row(
                "example.org/dependency@v1.2.3/main.go", b"package dependency\n"
            ),
        ],
    }
    second = deepcopy(first)
    second["module_cache"][2] = _alertmanager_cache_row(
        "cache/download/sumdb/sum.golang.org/lookup/module@v1.2.3", b"second lookup", 0o600
    )
    second["module_cache"][3] = _alertmanager_cache_row(
        "cache/download/sumdb/sum.golang.org/tile/8/0/001", b"second full tile", 0o600
    )
    return [first, second]


def test_alertmanager_replay_partitions_only_native_sumdb_state_without_mutating_raw_records(
    alertmanager_replays: list[dict[str, Any]],
) -> None:
    original = deepcopy(alertmanager_replays)
    assert alertmanager_replays[0]["module_cache"] != alertmanager_replays[1]["module_cache"]
    docker_sources._alertmanager_compare_replays(alertmanager_replays)
    assert alertmanager_replays == original


@pytest.mark.parametrize("module_changed", [False, True])
def test_alertmanager_replay_compares_complete_module_payload_not_go_index_cache(
    alertmanager_replays: list[dict[str, Any]],
    module_changed: bool,
) -> None:
    first, second = alertmanager_replays
    first["whole_GOCACHE"] = [_alertmanager_cache_row("index-first-root", b"first root index")]
    second["whole_GOCACHE"] = [_alertmanager_cache_row("index-second-root", b"second root index")]
    if module_changed:
        second["module_cache"][-1] = _alertmanager_cache_row(
            "example.org/dependency@v1.2.3/main.go", b"changed module payload\n"
        )
        with pytest.raises(RuntimeError, match="module_cache"):
            docker_sources._alertmanager_compare_replays(alertmanager_replays)
    else:
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize(
    "path",
    [
        "cache/download/sumdbx/lookup/module",
        "cache/download/sumdb-old/lookup/module",
        "cache/download/sumdb",
        "cache/download/SUMDB/lookup/module",
        "Cache/download/sumdb/lookup/module",
        "prefix/cache/download/sumdb/lookup/module",
        "cache/download/sumdb.json",
    ],
)
def test_alertmanager_sumdb_lookalikes_and_root_file_remain_strict(
    alertmanager_replays: list[dict[str, Any]], path: str
) -> None:
    alertmanager_replays[0]["module_cache"].append(_alertmanager_cache_row(path, b"first"))
    alertmanager_replays[1]["module_cache"].append(_alertmanager_cache_row(path, b"second"))
    with pytest.raises(RuntimeError, match="replay differs: module_cache"):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize(
    "path",
    [
        "",
        "/cache/download/sumdb/lookup/module",
        "./cache/download/sumdb/lookup/module",
        "cache/download/sumdb/../module",
        "cache/download/sumdb/./module",
        "cache/download/sumdb//module",
        "cache/download//sumdb/module",
        "cache/download/sumdb/module/",
        "cache\\download\\sumdb\\module",
        "cache/download/sumdb/module\x00suffix",
    ],
)
def test_alertmanager_sumdb_aliases_reject_before_partition(
    alertmanager_replays: list[dict[str, Any]], path: str
) -> None:
    alertmanager_replays[1]["module_cache"].append(_alertmanager_cache_row(path, b"opaque cache"))
    with pytest.raises(RuntimeError, match="path is unsafe or noncanonical"):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize("inventory", [None, {}, (), "cache inventory", True])
def test_alertmanager_replay_rejects_nonlist_cache_inventory(
    alertmanager_replays: list[dict[str, Any]], inventory: object
) -> None:
    alertmanager_replays[1]["module_cache"] = inventory
    with pytest.raises(RuntimeError, match="inventory shape or bound"):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize("field", ["path", "size", "mode", "sha256", "unknown"])
def test_alertmanager_replay_rejects_missing_or_unknown_checksum_row_fields(
    alertmanager_replays: list[dict[str, Any]], field: str
) -> None:
    row = alertmanager_replays[1]["module_cache"][2]
    if field == "unknown":
        row["type"] = "file"
    else:
        row.pop(field)
    # Every raw row is validated before even another ordinary mismatch can mask it.
    alertmanager_replays[1]["modules"] = []
    with pytest.raises(RuntimeError, match="row shape differs"):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize("row", [None, [], "cache row", True])
def test_alertmanager_replay_rejects_nonobject_row(
    alertmanager_replays: list[dict[str, Any]], row: object
) -> None:
    alertmanager_replays[1]["module_cache"].append(row)
    with pytest.raises(RuntimeError, match="row shape differs"):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", None),
        ("path", True),
        ("size", True),
        ("size", -1),
        ("size", 1.5),
        ("size", 2 * 1024**3 + 1),
        ("mode", True),
        ("mode", -1),
        ("mode", "0600"),
        ("mode", 0o100600),
        ("sha256", None),
        ("sha256", "A" * 64),
        ("sha256", "a" * 63),
        ("sha256", "g" * 64),
        ("sha256", "a" * 64 + "\n"),
    ],
)
def test_alertmanager_replay_rejects_invalid_values_inside_checksum_namespace(
    alertmanager_replays: list[dict[str, Any]], field: str, value: object
) -> None:
    alertmanager_replays[1]["module_cache"][2][field] = value
    diagnostic = "path is unsafe" if field == "path" else "row values differ"
    with pytest.raises(RuntimeError, match=diagnostic):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize("fault", ["duplicate", "count", "total", "missing_inventory"])
def test_alertmanager_replay_validates_complete_cache_before_partition(
    alertmanager_replays: list[dict[str, Any]], fault: str
) -> None:
    inventory = alertmanager_replays[1]["module_cache"]
    if fault == "duplicate":
        inventory.append(deepcopy(inventory[2]))
        diagnostic = "duplicate path"
    elif fault == "count":
        alertmanager_replays[1]["module_cache"] = [inventory[2]] * 250001
        diagnostic = "inventory shape or bound"
    elif fault == "total":
        inventory[2]["size"] = 2 * 1024**3
        diagnostic = "aggregate byte bound"
    else:
        alertmanager_replays[1].pop("module_cache")
        diagnostic = "inventory shape or bound"
    with pytest.raises(RuntimeError, match=diagnostic):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize(
    "member", [0, 1, 4], ids=["module-metadata", "module-archive", "module-source"]
)
@pytest.mark.parametrize("fault", ["missing", "extra", "path", "size", "mode", "sha256", "order"])
def test_alertmanager_every_nonchecksum_member_remains_exact(
    alertmanager_replays: list[dict[str, Any]], member: int, fault: str
) -> None:
    inventory = alertmanager_replays[1]["module_cache"]
    if fault == "missing":
        inventory.pop(member)
    elif fault == "extra":
        row = deepcopy(inventory[member])
        row["path"] += ".additional"
        inventory.append(row)
    elif fault == "order":
        inventory.insert(0, inventory.pop(member if member else 1))
    else:
        row = inventory[member]
        row[fault] = {
            "path": str(row["path"]) + ".changed",
            "size": int(row["size"]) + 1,
            "mode": 0o600,
            "sha256": sha256(b"changed member body").hexdigest(),
        }[fault]
    with pytest.raises(RuntimeError, match="replay differs: module_cache"):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize(
    "key,part",
    [
        ("original", "go.mod"),
        ("original", "go.sum"),
        ("derived", "go.mod"),
        ("derived", "go.sum"),
        ("modules", None),
        ("graph", None),
        ("packages", "alertmanager"),
        ("packages", "amtool"),
        ("delta", None),
        ("source", None),
        ("version", None),
    ],
)
def test_alertmanager_checksum_partition_cannot_mask_another_replay_mismatch(
    alertmanager_replays: list[dict[str, Any]], key: str, part: str | None
) -> None:
    if part is None:
        alertmanager_replays[1][key] = b"changed ordinary predicate"
    else:
        alertmanager_replays[1][key][part] = b"changed lock or command graph"
    with pytest.raises(RuntimeError, match="replay differs: " + key):
        docker_sources._alertmanager_compare_replays(alertmanager_replays)


@pytest.mark.parametrize("replays", [None, [], [{}], [None, None], ({}, {})])
def test_alertmanager_replay_requires_exact_pair_container(replays: object) -> None:
    with pytest.raises(RuntimeError, match="requires two replay records"):
        docker_sources._alertmanager_compare_replays(replays)


@pytest.fixture
def alertmanager_api_epoch(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    import base64

    for name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_READ_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_HOST",
        "GH_CONFIG_DIR",
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "DOCKER_AUTH_CONFIG",
        "DOCKER_CONFIG",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GH_TOKEN", "synthetic-AM-token")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-AM-token")
    zip_bytes = b"synthetic immutable Actions ZIP transport"
    monkeypatch.setattr(docker_sources, "_ALERT_Q_ZIP_SHA256", sha256(zip_bytes).hexdigest())
    source_files = {
        path: ("synthetic source bytes: " + path).encode()
        for path in docker_sources._ALERT_Q_SOURCE_FILES
    }
    source_files["deploy/alertmanager/Containerfile"] = _historical_alertmanager_recipe().replace(
        b" --chmod=0700", b""
    )
    assert len(source_files["deploy/alertmanager/Containerfile"]) == 895
    assert (
        sha256(source_files["deploy/alertmanager/Containerfile"]).hexdigest()
        == "69af6364f15e3e5b9a4662a5919ff7f3b0209da0461cd7a85e01e21022abdb78"
    )
    monkeypatch.setattr(
        docker_sources,
        "_ALERT_Q_SOURCE_FILES",
        {path: sha256(raw).hexdigest() for path, raw in source_files.items()},
    )
    monkeypatch.setattr(
        docker_sources,
        "_ALERT_S_SOURCE_FILES",
        {path: sha256(raw).hexdigest() for path, raw in source_files.items()},
    )
    monkeypatch.setattr(docker_sources, "_ALERT_S_ZIP_SHA256", sha256(zip_bytes).hexdigest())
    repository = {"id": 1043311030, "full_name": "Katsiarynakavaleuskaya/PulsePlate"}
    run = {
        "id": docker_sources._ALERT_Q_RUN,
        "head_sha": docker_sources._ALERT_Q_SOURCE,
        "head_branch": docker_sources._ALERT_Q_BRANCH,
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
        "workflow_id": 123,
        "repository": repository,
        "head_repository": repository,
    }
    workflow = {"id": 123, "path": ".github/workflows/cd.yml"}
    jobs = [
        {
            "id": docker_sources._ALERT_Q_JOB,
            "name": "alertmanager-module-qualification",
            "status": "completed",
            "conclusion": "success",
            "run_id": docker_sources._ALERT_Q_RUN,
            "head_sha": docker_sources._ALERT_Q_SOURCE,
        }
    ]
    artifact = {
        "id": docker_sources._ALERT_Q_ARTIFACT,
        "expired": False,
        "name": f"alertmanager-module-qualification-{docker_sources._ALERT_Q_RUN}-1",
        "size_in_bytes": len(zip_bytes),
        "digest": "sha256:" + sha256(zip_bytes).hexdigest(),
        "expires_at": "2099-01-01T00:00:00Z",
        "workflow_run": {
            "id": docker_sources._ALERT_Q_RUN,
            "head_sha": docker_sources._ALERT_Q_SOURCE,
            "repository_id": 1043311030,
            "head_repository_id": 1043311030,
        },
    }
    calls: list[str] = []
    data = {
        "repository": repository,
        "workflow": workflow,
        "run": run,
        "jobs": jobs,
        "artifact": artifact,
        "zip": zip_bytes,
        "calls": calls,
        "source_files": source_files,
    }

    class API:
        gh = "/absolute/gh"

        def json(self, endpoint: str) -> dict[str, Any]:
            calls.append(endpoint)
            if "/contents/" in endpoint:
                path = endpoint.split("/contents/", 1)[1].split("?", 1)[0]
                raw = source_files[path]
                return {
                    "type": "file",
                    "path": path,
                    "encoding": "base64",
                    "size": len(raw),
                    "content": base64.b64encode(raw).decode(),
                }
            if "/actions/workflows/" in endpoint:
                return data["workflow"]
            if "/actions/artifacts/" in endpoint:
                return data["artifact"]
            if "/jobs?" in endpoint:
                return {"total_count": len(data["jobs"])}
            if "/actions/runs/" in endpoint:
                return data["run"]
            return data["repository"]

        def pages(self, endpoint: str, key: str, count: int) -> list[dict[str, Any]]:
            calls.append(endpoint)
            assert key == "jobs" and count == len(data["jobs"])
            return data["jobs"]

        def raw(self, endpoint: str, *, maximum: int) -> bytes:
            calls.append(endpoint)
            assert maximum == 1024**3
            return data["zip"]

        def _capture(self, argv: list[str], maximum: int) -> bytes:
            calls.append(" ".join(argv))
            assert argv == [
                "/absolute/gh",
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                "/users/Katsiarynakavaleuskaya/packages/container/pulseplate",
            ]
            assert maximum == 1024**2
            return data["package"]

    data["api"] = API()
    data["package"] = json.dumps(
        {
            "name": "pulseplate",
            "package_type": "container",
            "visibility": "public",
            "repository": repository,
        }
    ).encode()
    return data


def _historical_alertmanager_recipe() -> bytes:
    from scripts.ci.prometheus_source_image import BASE, HISTORICAL_BASE

    raw = (REPO_ROOT / "deploy/alertmanager/Containerfile").read_bytes()
    historical = raw.replace(BASE.encode(), HISTORICAL_BASE.encode(), 1)
    assert sha256(historical).hexdigest() == docker_sources._ALERT_ASSEMBLY_RECIPE_SHA256
    return historical


@pytest.fixture
def alertmanager_retained_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, bytes]:
    import time
    from types import SimpleNamespace
    from scripts.ci import prometheus_source_image as transport

    original = {"go.mod": b"original mod\n", "go.sum": b"original sums\n"}
    derived = {"go.mod": b"derived mod\n", "go.sum": b"derived sums\n"}
    roots = {
        "go-toolchain.tar.gz": b"synthetic qualified Go archive",
        "base-image.tar": b"synthetic observed base export",
        "source.tar.gz": b"synthetic upstream source",
        "ui.tar.gz": b"synthetic matching UI",
    }
    monkeypatch.setattr(
        transport, "GO", SimpleNamespace(digest=sha256(roots["go-toolchain.tar.gz"]).hexdigest())
    )
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_loaded_base",
        lambda objects, *, current=False: "sha256:" + "1" * 64,
    )
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_input_plan",
        lambda *args, **kwargs: {"state": "DECLARED_ONLY_COMPILER_HOLD"},
    )
    source_before = [
        _alertmanager_cache_row(path, raw, 0o644) for path, raw in sorted(original.items())
    ]
    source_after = [
        _alertmanager_cache_row(path, raw, 0o644) for path, raw in sorted(derived.items())
    ]
    module_bodies = {
        "cache/download/example.org/dependency/@v/v1.2.3.mod": b"module dependency",
        "cache/download/sumdb/sum.golang.org/tile/8/0/001": b"retained opaque checksum state",
        "example.org/dependency@v1.2.3/main.go": b"package dependency\n",
        "cache/download/example.org/module-with-a-long-native-directory-component/"
        "nested-package-component-extending-the-native-PAX-path/@v/v1.2.3.mod": b"long-directory descendant",
    }
    module_rows = [
        _alertmanager_cache_row(path, raw, 0o600) for path, raw in sorted(module_bodies.items())
    ]

    def readonly(value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [dict(row, mode=0o555 if row["mode"] & 0o111 else 0o444) for row in value]

    gocache = [_alertmanager_cache_row("index", b"owned index", 0o600)]
    gopath = [_alertmanager_cache_row("build/index", b"owned index", 0o600)] + [
        dict(row, path="pkg/mod/" + row["path"]) for row in module_rows
    ]
    inventories = {
        "original_source": source_before,
        "derived_source": source_after,
        "complete_GOMODCACHE": module_rows,
        "whole_GOPATH": gopath,
        "whole_GOCACHE": gocache,
        "readonly_source": readonly(source_after),
        "readonly_GOPATH": readonly(gopath),
    }
    stability = {
        "source_before": readonly(source_after),
        "source_after": readonly(source_after),
        "whole_GOPATH_before": readonly(gopath),
        "whole_GOPATH_after": readonly(gopath),
        "whole_GOCACHE_after": readonly(gocache),
    }
    delta = [
        {"path": name, "before": before, "after": after, "class": "authored"}
        for name, before, after in (
            ("golang.org/x/net", "v0.58.0", "v0.60.0"),
            ("google.golang.org/grpc", "v1.83.1", "v1.83.2"),
        )
    ]
    projection = {
        "selected_modules": [{"Path": "github.com/prometheus/alertmanager", "Main": True}],
        "package_graphs": {
            name: [{"ImportPath": "github.com/prometheus/alertmanager/cmd/" + name}]
            for name in ("alertmanager", "amtool")
        },
        "module_edges": ["github.com/prometheus/alertmanager golang.org/x/net@v0.60.0"],
        "delta": delta,
    }
    go_before = [_alertmanager_cache_row("bin/go", b"qualified go bytes", 0o755)]
    go_binding = {
        "before_files": go_before,
        "after_files": readonly(go_before),
        "before_directories": [{"path": ".", "mode": 0o700}, {"path": "bin", "mode": 0o755}],
        "after_directories": [{"path": ".", "mode": 0o555}, {"path": "bin", "mode": 0o555}],
    }
    files = {
        "base-retention/base-image.tar": roots["base-image.tar"],
        "go-readonly-input-binding.json": json.dumps(go_binding).encode(),
    }
    bodies = {"source/" + path: raw for path, raw in derived.items()}
    bodies.update({"modules/" + path: raw for path, raw in module_bodies.items()})
    bodies.update(roots)
    directories = {"source", "modules"} | {
        "/".join(path.split("/")[:index])
        for path in bodies
        for index in range(1, len(path.split("/")))
    }
    stage, evidence = tmp_path / "retention-stage", tmp_path / "retention-evidence"
    stage.mkdir()
    evidence.mkdir()
    for path, raw in bodies.items():
        target = stage / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(0o444 if path.startswith(("source/", "modules/")) else 0o644)
    for path in directories:
        (stage / path).chmod(0o555)
    try:
        # Use the actual producer and native serializer, including the long
        # directory's PAX path and its descendant's distinct FILE representation.
        frozen = docker_sources._retain_alertmanager_inputs(
            evidence,
            stage / "source",
            stage / "modules",
            *(stage / path for path in roots),
            time.monotonic() + 10,
        )
    finally:
        for path in directories:
            (stage / path).chmod(0o700)
    files["frozen-inputs.tar"] = (evidence / "frozen-inputs.tar").read_bytes()
    files["frozen-inputs-inventory.json"] = json.dumps(frozen).encode()
    for number in (1, 2):
        prefix = "replay" + str(number)
        files[prefix + "-inventories.json"] = json.dumps(inventories).encode()
        files[prefix + "-offline-stability.json"] = json.dumps(stability).encode()
        files[prefix + "-projections.json"] = json.dumps(projection).encode()
        for lock, raw in original.items():
            files[prefix + "-original-" + lock] = raw
        for lock, raw in derived.items():
            files[prefix + "-derived-" + lock] = raw
    labels = ["public-base-pull", "public-base-inspect", "retain-physical-base"]
    ids, names = [], []
    token = "a" * 32
    for number in (1, 2):
        prefix = "replay" + str(number)
        labels += [
            prefix + "-" + label
            for label in (
                "version",
                "baseline-download",
                "baseline-modules",
                "two-authored-replacements",
                "derived-download",
                "online-verify",
                "online-modules",
                "online-graph",
                "online-alertmanager",
                "online-amtool",
            )
        ]
        for command in ("version", "verify", "modules", "graph", "alertmanager", "amtool"):
            identifier = f"{len(ids) + 1:064x}"
            name = f"pulseplate-alert-module-{token}-{number}-{command}"
            ids.append(identifier)
            names.append(name)
            labels += [
                prefix + "-" + stage + "-" + command
                for stage in ("create", "offline", "wait", "terminal")
            ]
            files[prefix + "-create-" + command + ".stdout"] = (identifier + "\n").encode()
            files[prefix + "-wait-" + command + ".stdout"] = b"0\n"
            files[prefix + "-terminal-" + command + ".stdout"] = json.dumps(
                {
                    "Id": identifier,
                    "Name": "/" + name,
                    "Config": {"Labels": {"pulseplate.alertmanager-module": token}},
                    "State": {
                        "Status": "exited",
                        "Running": False,
                        "Restarting": False,
                        "Dead": False,
                        "OOMKilled": False,
                        "Error": "",
                        "ExitCode": 0,
                    },
                }
            ).encode()
    labels += (
        ["cleanup-census"]
        + [f"cleanup-{stage}-{index}" for index in range(12) for stage in ("inspect", "remove")]
        + ["cleanup-absence"]
    )
    files["public-base-inspect.stdout"] = b"{}"
    native = []
    for label in labels:
        stdout = label + ".stdout"
        stderr = label + ".stderr"
        files.setdefault(
            stdout, b"go version go1.27.2 linux/amd64\n" if label.endswith("-version") else b""
        )
        files[stderr] = b""
        native.append(
            {
                "argv": ["/usr/bin/docker", "synthetic-" + label],
                "environment": {"PATH": "/usr/bin:/bin", "HOME": "/owned"},
                "cwd": "/owned",
                "exit": 0,
                "failure": None,
                "stdout": "/owned/alertmanager-module-evidence/" + stdout,
                "stderr": "/owned/alertmanager-module-evidence/" + stderr,
                "stdout_sha256": sha256(files[stdout]).hexdigest(),
                "stderr_sha256": sha256(files[stderr]).hexdigest(),
            }
        )
    report = {
        "metadata_only": True,
        "compiler_starts": 0,
        "compiler_counter_meaning": "procedural fixed commands only",
        "owned_container_names": sorted(names),
        "owned_container_ids": sorted(ids),
        "owned_container_absence_observed": True,
        "logical_build_starts": 0,
        "frozen_input_payload": frozen,
        "loaded_base_ID": "sha256:" + "1" * 64,
        "base_export_representation": "derived Docker save",
        "whole_GOPATH_GOCACHE_individually_retained": True,
        "delta": delta,
        "native_records": native,
        "elapsed_limit_seconds": 825,
        "qualification_requires_separate_fullF_and_build_admission": True,
    }
    files["module-qualification.json"] = json.dumps(report).encode()
    return files


def _alertmanager_payload_zip(
    directory: Path, files: dict[str, bytes], fault: str | None = None
) -> Path:
    import stat
    import zipfile

    rows = [_alertmanager_cache_row(path, raw, 0o600) for path, raw in sorted(files.items())]
    if fault == "hash":
        rows[0]["sha256"] = "f" * 64
    elif fault == "mode":
        rows[0]["mode"] = 0o644
    elif fault == "unknown":
        rows[0]["unexpected"] = True
    elif fault == "duplicate":
        rows.append(deepcopy(rows[0]))
    footer = {
        "files": rows,
        "directories": [{"path": "base-retention", "type": "directory", "mode": 0o700}],
        "inventory_carrier_exception": "Exactly artifact-payload-members.json is bound by external artifact bytes; its own hash is not recursively embedded.",
    }
    payload = dict(files)
    if fault != "missing-footer":
        payload["artifact-payload-members.json"] = json.dumps(footer).encode()
    path = directory / "qualification.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name, raw in payload.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(info, raw)
    return path


@pytest.mark.parametrize("fault", [None, "hash", "mode", "unknown", "duplicate", "missing-footer"])
def test_alertmanager_retained_payload_validates_complete_native_transport(
    tmp_path: Path, alertmanager_retained_files: dict[str, bytes], fault: str | None
) -> None:
    archive = _alertmanager_payload_zip(tmp_path, alertmanager_retained_files, fault)
    if fault:
        with pytest.raises((RuntimeError, KeyError)):
            docker_sources._alertmanager_qualified_payload(
                archive, producer_recipe=_historical_alertmanager_recipe()
            )
    else:
        result = docker_sources._alertmanager_qualified_payload(
            archive, producer_recipe=_historical_alertmanager_recipe()
        )
        assert (
            result["compiler_starts"] == 0
            and result["build_admission"] == "HOLD_SEPARATE_HUMAN_DECISION"
        )
        assert result["artifact_files"] == len(alertmanager_retained_files)


@pytest.mark.parametrize(
    "fault",
    [
        "native",
        "canonical-directory",
        "double-slash",
        "alias",
        "traversal",
        "file-slash",
        "unknown-PAX",
        "type",
        "link",
        "mode",
        "size",
        "uid",
        "gid",
        "mtime",
    ],
)
def test_alertmanager_frozen_PAX_directory_preserves_typed_native_relationship(
    tmp_path: Path, alertmanager_retained_files: dict[str, bytes], fault: str
) -> None:
    import tarfile

    files = alertmanager_retained_files
    original = files["frozen-inputs.tar"]
    with tarfile.open(fileobj=BytesIO(original), mode="r:") as archive:
        members = archive.getmembers()
        directory = next(
            member for member in members if member.isdir() and "path" in member.pax_headers
        )
        descendant = next(
            member
            for member in members
            if member.isfile() and member.name.startswith(directory.name + "/")
        )
        assert directory.pax_headers == {"path": directory.name + "/"}
        assert descendant.pax_headers == {"path": descendant.name}
        assert archive.extractfile(descendant).read() == b"long-directory descendant"
        assert directory.mode == 0o555 and descendant.mode == 0o444
        if fault != "native":
            target = descendant.name if fault == "file-slash" else directory.name
            output = BytesIO()
            with tarfile.open(fileobj=output, mode="w", format=tarfile.PAX_FORMAT) as rewritten:
                for member in members:
                    changed = deepcopy(member)
                    if (
                        fault == "canonical-directory"
                        and member.isdir()
                        and "path" in changed.pax_headers
                    ):
                        changed.pax_headers["path"] = member.name
                    if member.name == target:
                        if fault in ("canonical-directory", "type", "link"):
                            changed.pax_headers["path"] = directory.name
                        elif fault == "double-slash":
                            changed.pax_headers["path"] = directory.name + "//"
                        elif fault == "alias":
                            changed.pax_headers["path"] = (
                                directory.name.replace("modules/", "modules//", 1) + "/"
                            )
                        elif fault == "traversal":
                            changed.pax_headers["path"] = directory.name + "/../other/"
                        elif fault == "file-slash":
                            changed.pax_headers["path"] = descendant.name + "/"
                        elif fault == "unknown-PAX":
                            changed.pax_headers["comment"] = "unadmitted native key"
                        if fault == "type":
                            changed.type = tarfile.REGTYPE
                        elif fault == "link":
                            changed.type, changed.linkname = tarfile.SYMTYPE, "../outside"
                        elif fault == "mode":
                            changed.mode = 0o755
                        elif fault == "size":
                            changed.size = 1
                        elif fault in ("uid", "gid", "mtime"):
                            setattr(changed, fault, 1)
                    rewritten.addfile(
                        changed, archive.extractfile(member) if member.isfile() else None
                    )
            files["frozen-inputs.tar"] = output.getvalue()
            frozen = json.loads(files["frozen-inputs-inventory.json"])
            declared_members = deepcopy(frozen["members"])
            frozen.update(
                bytes=len(output.getvalue()), sha256=sha256(output.getvalue()).hexdigest()
            )
            assert frozen["members"] == declared_members
            files["frozen-inputs-inventory.json"] = json.dumps(frozen).encode()
            report = json.loads(files["module-qualification.json"])
            report["frozen_input_payload"] = frozen
            files["module-qualification.json"] = json.dumps(report).encode()
    archive_path = _alertmanager_payload_zip(tmp_path, files)
    raw_before = archive_path.read_bytes()
    if fault in ("native", "canonical-directory"):
        observed = docker_sources._alertmanager_qualified_payload(
            archive_path, producer_recipe=_historical_alertmanager_recipe()
        )
        assert observed["build_admission"] == "HOLD_SEPARATE_HUMAN_DECISION"
    else:
        with pytest.raises(RuntimeError, match="AM_"):
            docker_sources._alertmanager_qualified_payload(
                archive_path, producer_recipe=_historical_alertmanager_recipe()
            )
    assert archive_path.read_bytes() == raw_before
    if fault == "native":
        assert files["frozen-inputs.tar"] == original


@pytest.mark.parametrize(
    "fault",
    [
        "compiler-bool",
        "cleanup",
        "native-exit",
        "lock",
        "graph",
        "mode-transition",
        "offline-checksum",
    ],
)
def test_alertmanager_retained_success_requires_locks_graphs_modes_and_raw_offline_stability(
    tmp_path: Path, alertmanager_retained_files: dict[str, bytes], fault: str
) -> None:
    files = alertmanager_retained_files
    if fault in ("compiler-bool", "cleanup", "native-exit"):
        report = json.loads(files["module-qualification.json"])
        if fault == "compiler-bool":
            report["compiler_starts"] = False
        elif fault == "cleanup":
            report["owned_container_absence_observed"] = False
        else:
            report["native_records"][0]["exit"] = 1
        files["module-qualification.json"] = json.dumps(report).encode()
    elif fault == "lock":
        files["replay2-derived-go.sum"] += b"changed"
    elif fault == "graph":
        projection = json.loads(files["replay2-projections.json"])
        projection["package_graphs"]["amtool"] = []
        files["replay2-projections.json"] = json.dumps(projection).encode()
    elif fault == "mode-transition":
        inventory = json.loads(files["replay1-inventories.json"])
        inventory["readonly_source"][0]["mode"] = 0o600
        files["replay1-inventories.json"] = json.dumps(inventory).encode()
    else:
        stability = json.loads(files["replay1-offline-stability.json"])
        checksum = next(row for row in stability["whole_GOPATH_after"] if "/sumdb/" in row["path"])
        checksum["sha256"] = "f" * 64
        files["replay1-offline-stability.json"] = json.dumps(stability).encode()
    with pytest.raises(RuntimeError, match="AM_"):
        docker_sources._alertmanager_qualified_payload(
            _alertmanager_payload_zip(tmp_path, files),
            producer_recipe=_historical_alertmanager_recipe(),
        )


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "run",
        "main-branch",
        "attempt",
        "workflow",
        "job",
        "duplicate-job",
        "artifact",
        "expired",
        "name",
        "digest",
        "bytes",
    ],
)
def test_alertmanager_retained_Q_requires_exact_authenticated_successful_CD_epoch(
    tmp_path: Path, alertmanager_api_epoch: dict[str, Any], fault: str | None
) -> None:
    data = alertmanager_api_epoch
    if fault == "run":
        data["run"]["head_sha"] = "f" * 40
    elif fault == "main-branch":
        data["run"]["head_branch"] = "main"
    elif fault == "attempt":
        data["run"]["run_attempt"] = True
    elif fault == "workflow":
        data["workflow"]["path"] = ".github/workflows/build.yml"
    elif fault == "job":
        data["jobs"][0]["conclusion"] = "failure"
    elif fault == "duplicate-job":
        data["jobs"].append(deepcopy(data["jobs"][0]))
    elif fault == "artifact":
        data["artifact"]["workflow_run"]["repository_id"] = 1
    elif fault == "expired":
        data["artifact"]["expires_at"] = "2020-01-01T00:00:00Z"
    elif fault == "name":
        data["artifact"]["name"] = "latest-qualification"
    elif fault == "digest":
        data["artifact"]["digest"] = "sha256:" + "f" * 64
    elif fault == "bytes":
        data["zip"] += b"drift"
    destination = tmp_path / "qualification.zip"
    if fault is None:
        result = docker_sources._alertmanager_authenticated_inputs(
            data["api"],
            docker_sources._ALERT_Q_RUN,
            docker_sources._ALERT_Q_ARTIFACT,
            docker_sources._ALERT_Q_SOURCE,
            destination,
        )
        assert (
            result["source"] == docker_sources._ALERT_Q_SOURCE
            and destination.read_bytes() == data["zip"]
        )
    else:
        with pytest.raises(RuntimeError, match="AM_qualification_"):
            docker_sources._alertmanager_authenticated_inputs(
                data["api"],
                docker_sources._ALERT_Q_RUN,
                docker_sources._ALERT_Q_ARTIFACT,
                docker_sources._ALERT_Q_SOURCE,
                destination,
            )
        assert not destination.exists()


@pytest.mark.parametrize("kind", ["qualification", "support", "candidate"])
@pytest.mark.parametrize(
    "fault", [None, "other-epoch", "changed", "missing", "mixed", "config", "run", "job"]
)
def test_alertmanager_source_recipe_binds_historical_QS_and_current_candidate_separately(
    tmp_path: Path,
    alertmanager_api_epoch: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    fault: str | None,
) -> None:
    data = alertmanager_api_epoch
    recipe_path = "deploy/alertmanager/Containerfile"
    historical = data["source_files"][recipe_path]
    current = (REPO_ROOT / recipe_path).read_bytes()
    assert len(historical) == 895 and len(current) == 908
    assert (
        docker_sources._ALERT_Q_SOURCE_FILES[recipe_path]
        == docker_sources._ALERT_S_SOURCE_FILES[recipe_path]
        == sha256(historical).hexdigest()
        == "69af6364f15e3e5b9a4662a5919ff7f3b0209da0461cd7a85e01e21022abdb78"
    )
    assert sha256(current).hexdigest() == docker_sources._ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
    run, artifact, source, job = (
        (
            docker_sources._ALERT_Q_RUN,
            docker_sources._ALERT_Q_ARTIFACT,
            docker_sources._ALERT_Q_SOURCE,
            docker_sources._ALERT_Q_JOB,
        )
        if kind == "qualification"
        else (
            (
                docker_sources._ALERT_S_RUN,
                docker_sources._ALERT_S_ARTIFACT,
                docker_sources._ALERT_S_SOURCE,
                docker_sources._ALERT_S_JOB,
            )
            if kind == "support"
            else (1234, 5678, "a" * 40, 9876)
        )
    )
    name = {
        "qualification": "alertmanager-module-qualification",
        "support": "alertmanager-input-inspection",
        "candidate": "alertmanager-candidate",
    }[kind]
    data["run"].update(id=run, head_sha=source)
    data["jobs"][0].update(
        id=job,
        run_id=run,
        head_sha=source,
        name="alertmanager-candidate-build" if kind == "candidate" else name,
    )
    data["artifact"].update(id=artifact, name=f"{name}-{run}-1")
    data["artifact"]["workflow_run"].update(id=run, head_sha=source)
    expected = current if kind == "candidate" else historical
    data["source_files"][recipe_path] = expected
    if kind == "candidate":
        data["run"]["head_branch"] = docker_sources._ALERT_RECEIVER_BRANCH
        native_path = "tests/test_notify_premium_alias_checkpoint_failure.py"
        data["source_files"][native_path] = b"synthetic independently accepted native owner"
        monkeypatch.setattr(
            docker_sources,
            "_ALERT_ACCEPTED_CANDIDATE",
            {
                "run": run,
                "attempt": 1,
                "artifact": artifact,
                "source": source,
                "job": job,
                "zip_sha256": sha256(data["zip"]).hexdigest(),
                "source_files": {
                    path: sha256(raw).hexdigest() for path, raw in data["source_files"].items()
                },
                "graph": {"synthetic_known_graph": True},
                "OCI_archive_sha256": "e" * 64,
            },
        )
    if fault == "other-epoch":
        data["source_files"][recipe_path] = historical if kind == "candidate" else current
    elif fault == "changed":
        data["source_files"][recipe_path] += b"# unreviewed recipe\n"
    elif fault == "missing":
        data["source_files"][recipe_path] = b""
    elif fault == "mixed":
        data["source_files"][recipe_path] = expected.replace(
            b"--chown=65534:65534", b"--chown=0:65534"
        )
    elif fault == "config":
        data["source_files"]["deploy/alertmanager/alertmanager.yml"] += b"# changed config\n"
    elif fault == "run":
        data["run"]["conclusion"] = "failure"
    elif fault == "job":
        data["jobs"][0]["conclusion"] = "failure"
    destination = tmp_path / (kind + ".zip")
    if fault is None:
        result = docker_sources._alertmanager_authenticated_inputs(
            data["api"], run, artifact, source, destination, kind=kind
        )
        assert result["source_files"][recipe_path] == sha256(expected).hexdigest()
        assert destination.read_bytes() == data["zip"]
        if kind != "qualification":
            assert (tmp_path / (kind + "-producer-source") / recipe_path).read_bytes() == expected
    else:
        diagnostic = {
            "missing": "AM_qualification_source_blob",
            "run": "AM_qualification_successful_CD_source",
            "job": "AM_qualification_successful_unique_job",
        }.get(fault, "AM_qualification_source_bytes")
        with pytest.raises(RuntimeError, match="^" + diagnostic + "$"):
            docker_sources._alertmanager_authenticated_inputs(
                data["api"], run, artifact, source, destination, kind=kind
            )
        assert not destination.exists()
        assert not any(call.endswith("/zip") for call in data["calls"])


def test_alertmanager_unknown_selector_rejects_before_auth_or_download(
    tmp_path: Path, alertmanager_api_epoch: dict[str, Any]
) -> None:
    with pytest.raises(RuntimeError, match="AM_qualification_exact_selectors"):
        docker_sources._alertmanager_authenticated_inputs(
            alertmanager_api_epoch["api"],
            True,
            docker_sources._ALERT_Q_ARTIFACT,
            docker_sources._ALERT_Q_SOURCE,
            tmp_path / "out.zip",
        )
    assert alertmanager_api_epoch["calls"] == []


@pytest.mark.parametrize("fault", [None, "identity", "403"])
def test_alertmanager_existing_package_check_is_finite_read_only(
    alertmanager_api_epoch: dict[str, Any], fault: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = alertmanager_api_epoch
    if fault == "403":

        def denied(*args: object) -> bytes:
            raise RuntimeError("GitHub_native_failed403")

        monkeypatch.setattr(data["api"], "_capture", denied)
    elif fault == "identity":
        package = json.loads(data["package"])
        package["visibility"] = "private"
        data["package"] = json.dumps(package).encode()
    if fault:
        with pytest.raises(RuntimeError):
            docker_sources._alertmanager_package_read(data["api"])
    else:
        observed = docker_sources._alertmanager_package_read(data["api"])
        assert observed["metadata_read"] is True and observed["publication_write_proved"] is False
        assert len(data["calls"]) == 1 and "GET" in data["calls"][0]


@pytest.mark.parametrize("stage", ["build", "publish"])
def test_alertmanager_unadmitted_stages_cannot_activate_compiler_or_publication(
    stage: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Held stage reached input acquisition")

    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", None)
    monkeypatch.setattr(docker_sources, "load_manifest", forbidden)
    monkeypatch.delenv("ALERTMANAGER_PREP_SECONDS", raising=False)
    expected = (
        "AM_accepted_producer_UNCONFIGURED_HOLD" if stage == "publish" else "AM_current_build_cli"
    )
    with pytest.raises(RuntimeError, match=expected):
        docker_sources.main(["--artifact", "alertmanager", "--alertmanager-stage", stage])
    assert docker_sources.parse_args([]).alertmanager_stage == "disabled"


@pytest.mark.parametrize(
    "payload", [b"synthetic current Go\n", b"different current Go bytes\n"], ids=["first", "second"]
)
@pytest.mark.parametrize(
    "case", ["fresh", "retained", "size", "digest", "symlink", "directory", "hardlink"]
)
def test_alertmanager_current_go_archive_guard_uses_acquired_owner_before_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes, case: str
) -> None:
    """Exercise the real guard with synthetic artifact bytes; never qualify or execute Go."""
    from scripts.ci import prometheus_source_image as source

    current = replace(source.CURRENT_GO, size=len(payload), digest=sha256(payload).hexdigest())
    legacy = source.GO
    archive = tmp_path / "go1.27.3.linux-amd64.tar.gz"
    acquisitions: list[Path] = []
    extractions: list[Path] = []
    if case == "symlink":
        archive.symlink_to(tmp_path / "absent-target")
    elif case == "directory":
        archive.mkdir()
    elif case != "fresh":
        archive.write_bytes(
            payload + b"extra"
            if case == "size"
            else bytes([payload[0] ^ 1]) + payload[1:] if case == "digest" else payload
        )
        if case == "hardlink":
            (tmp_path / "second-link").hardlink_to(archive)

    def acquire(artifact: source.Artifact, destination: Path, deadline: float) -> None:
        assert artifact is current and destination == archive and deadline > 0
        assert case == "fresh"
        acquisitions.append(destination)
        destination.write_bytes(payload)

    def extract(artifact: source.Artifact, path: Path, target: Path, deadline: float) -> None:
        assert artifact is current and path == archive and deadline > 0
        assert target == tmp_path / "alertmanager-go" and path.read_bytes() == payload
        extractions.append(path)
        raise RuntimeError("synthetic_current_go_extract_boundary")

    def no_native(*args: Any, **kwargs: Any) -> None:
        pytest.fail("archive validation must precede every native command")

    monkeypatch.setenv("ALERTMANAGER_QUALIFY_SECONDS", "825")
    monkeypatch.setattr(source, "CURRENT_GO", current)
    monkeypatch.setattr(source, "acquire", acquire)
    monkeypatch.setattr(source, "extract", extract)
    monkeypatch.setattr(source.Native, "run", no_native)
    monkeypatch.setattr(docker_sources, "load_manifest", lambda *a, **k: [])
    monkeypatch.setattr(docker_sources, "_fetch_alertmanager_pair", lambda *a, **k: None)
    valid = case in {"fresh", "retained"}
    diagnostic = (
        "^synthetic_current_go_extract_boundary$"
        if valid
        else "^Exact Go input changed; no overwrite, replacement or retry\\.$"
    )
    with pytest.raises(RuntimeError, match=diagnostic):
        docker_sources._qualify_alertmanager_modules(tmp_path)
    assert acquisitions == ([archive] if case == "fresh" else [])
    assert extractions == ([archive] if valid else [])
    assert source.GO is legacy
    assert not (tmp_path / "alertmanager-module-evidence/module-qualification.json").exists()


@pytest.mark.parametrize(
    "relative",
    [
        "pkg/mod/cache/download/sumdb/sum.golang.org/lookup/module@v1.2.3",
        "pkg/mod/example.org/dependency@v1.2.3/main.go",
        "build/index",
    ],
    ids=["checksum-state", "module-payload", "build-cache"],
)
def test_alertmanager_offline_stability_still_uses_complete_raw_cache(
    tmp_path: Path, relative: str
) -> None:
    import inspect
    from scripts.ci.prometheus_source_image import tree_inventory

    # Physical inventory still observes checksum state, even though cross-replay
    # payload comparison delegates that exact namespace to the qualified Go owner.
    cache = tmp_path / "cache"
    member = cache / relative
    member.parent.mkdir(parents=True)
    member.write_bytes(b"before offline command")
    before = tree_inventory(cache)
    member.write_bytes(b"after offline command")
    after = tree_inventory(cache)
    assert before != after
    assert before[0]["path"] == after[0]["path"] == relative

    phase = ast.parse(inspect.getsource(docker_sources._alertmanager_module_phase))
    guard = next(
        node
        for node in ast.walk(phase)
        if isinstance(node, ast.If)
        and any(
            isinstance(statement, ast.Raise)
            and isinstance(statement.exc, ast.Call)
            and statement.exc.args
            and isinstance(statement.exc.args[0], ast.Constant)
            and statement.exc.args[0].value == "Readonly offline source/cache changed."
            for statement in node.body
        )
    )
    # This existing admission guard must compare both full raw observations,
    # without the comparator's transient cross-replay partition.
    assert ast.unparse(guard.test) == (
        "tree_inventory(source, deadline=deadline) != readonly_source or "
        "tree_inventory(cache, deadline=deadline) != readonly_cache"
    )


def test_alertmanager_matching_verify_stdout_cannot_mask_native_failure(tmp_path: Path) -> None:
    import time
    from scripts.ci.prometheus_source_image import Native, QualificationError

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    native = Native(evidence, time.monotonic() + 10, 45)
    with pytest.raises(QualificationError, match="native_failed"):
        native.run(
            [sys.executable, "-I", "-c", "print('all modules verified'); raise SystemExit(1)"],
            "synthetic-online-verify",
            {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
            cwd=tmp_path,
        )
    assert (evidence / "synthetic-online-verify.stdout").read_bytes() == b"all modules verified\n"
    assert native.records[0]["exit"] == 1


def test_alertmanager_frozen_input_artifact_includes_required_bytes_and_excludes_private_home(
    tmp_path: Path,
) -> None:
    import time
    import tarfile

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    source, modules = tmp_path / "source", tmp_path / "modules"
    source.mkdir()
    modules.mkdir()
    (source / "go.mod").write_bytes(b"derived exact lock")
    (modules / "module").write_bytes(b"frozen exact module")
    long_module = modules / ("module-cache-" + "x" * 151)
    long_module.write_bytes(b"exact long-name module bytes")
    long_module.chmod(0o444)
    checksum = modules / "cache/download/sumdb/sum.golang.org/lookup/module@v1.2.3"
    checksum.parent.mkdir(parents=True)
    checksum.write_bytes(b"complete retained checksum state")
    checksum.chmod(0o600)
    files = []
    for name in ("go", "base", "original", "ui"):
        path = tmp_path / name
        path.write_bytes(name.encode())
        files.append(path)
    (tmp_path / "HOME-private").write_bytes(b"must stay excluded")
    (tmp_path / "private-http-capture").write_bytes(b"must stay excluded")
    result = docker_sources._retain_alertmanager_inputs(
        evidence, source, modules, *files, time.monotonic() + 10
    )
    with tarfile.open(evidence / "frozen-inputs.tar") as archive:
        names = archive.getnames()
        assert "source/go.mod" in names and "modules/module" in names
        assert {"go-toolchain.tar.gz", "base-image.tar", "source.tar.gz", "ui.tar.gz"} <= set(names)
        assert not any("private" in name or "HOME" in name for name in names)
        assert archive.extractfile("source/go.mod").read() == b"derived exact lock"
        long_name = "modules/" + long_module.name
        assert archive.extractfile(long_name).read() == long_module.read_bytes()
        assert archive.getmember(long_name).mode == 0o444
        checksum_name = "modules/" + checksum.relative_to(modules).as_posix()
        assert archive.extractfile(checksum_name).read() == checksum.read_bytes()
        assert archive.getmember(checksum_name).mode == 0o600
        observed = []
        for member in archive.getmembers():
            row = {
                "path": member.name,
                "mode": member.mode,
                "bytes": member.size,
                "type": "directory" if member.isdir() else "file",
            }
            assert member.uid == member.gid == member.mtime == 0
            if member.isfile():
                row["sha256"] = sha256(archive.extractfile(member).read()).hexdigest()
            observed.append(row)
        assert observed == result["members"]
    assert result["private_HTTP_and_HOME_excluded"] is True
    assert sha256((evidence / "frozen-inputs.tar").read_bytes()).hexdigest() == result["sha256"]
    repeated = tmp_path / "repeated-evidence"
    repeated.mkdir()
    repeated_result = docker_sources._retain_alertmanager_inputs(
        repeated, source, modules, *files, time.monotonic() + 10
    )
    assert repeated_result == result
    assert (repeated / "frozen-inputs.tar").read_bytes() == (
        evidence / "frozen-inputs.tar"
    ).read_bytes()
    files[0].unlink()
    other = tmp_path / "other-evidence"
    other.mkdir()
    with pytest.raises(RuntimeError, match="required Alertmanager input missing"):
        docker_sources._retain_alertmanager_inputs(
            other, source, modules, *files, time.monotonic() + 10
        )


def test_alertmanager_hosted_transport_shares_clock_and_empty_docker_config() -> None:
    import inspect

    source = (
        inspect.getsource(docker_sources._qualify_alertmanager_modules)
        + "\n"
        + inspect.getsource(docker_sources._alertmanager_module_phase)
    )
    assert (
        source.index("deadline =")
        < source.index("_fetch_alertmanager_pair")
        < source.index("acquire(GO")
    )
    assert "operation_deadline=deadline" in source
    assert 'docker_prefix = [docker, "--config", str(docker_config)]' in source
    assert "base_id = _alertmanager_loaded_base(base_objects, current=True)" in source
    assert '"--pull=never"' in source
    assert (
        "/run/alertmanager-metadata:size=64m,noexec,nosuid,uid=65534,gid=65534,mode=0700" in source
    )
    assert '"HOME": "/run/alertmanager-metadata"' in source
    assert '"GOCACHE": "/run/alertmanager-metadata/cache"' in source
    assert '"TMPDIR": "/run/alertmanager-metadata"' in source
    assert '"--network=none"' in source and '"--read-only"' in source
    assert '"GOSUMDB": "sum.golang.org"' in source
    assert '"GOTOOLCHAIN": "local"' in source
    assert '["get", "golang.org/x/net@v0.60.0", "google.golang.org/grpc@v1.83.2"]' in source
    assert '"--cap-drop=ALL"' in source and '"--security-opt=no-new-privileges"' in source
    assert '"loaded_base_ID": base_id' in source
    assert "native_import(" not in source and '"login"' not in source
    workflow = _load_workflow(WORKFLOWS_DIR / "cd.yml")
    steps = workflow["jobs"]["alertmanager-module-qualification"]["steps"]
    calls = [
        step.get("run", "")
        for step in steps
        if "fetch_docker_source_artifacts" in step.get("run", "")
    ]
    assert len(calls) == 1 and "--alertmanager-module-qualify" in calls[0]


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "config",
        "platform",
        "digest",
        "layer",
        "digests-string",
        "duplicate-digest",
        "rootfs-list",
        "rootfs-type",
        "layers-string",
    ],
)
def test_alertmanager_public_base_native_binding_precedes_offline_use(fault: str) -> None:
    image = {
        "Id": "sha256:55a757dc8ab862a4eb634c434261dcd26f17c186b54f7bce845404a335456110",
        "Os": "linux",
        "Architecture": "amd64",
        "RepoDigests": [
            "gcr.io/distroless/static-debian13@sha256:2293b36c7c9082bf4115aab724b4d2cddec82c8eba39bf27ac0517e159acf150"
        ],
        "RootFS": {
            "Type": "layers",
            "Layers": [
                "sha256:9486261b5a13f63ca6904b36721527ac8f19df53d300560138d69ae9b4c203de",
                "sha256:621c35e751a51a9a9dc3e80aa0b7fe8be2a93402ea6ccd307d30852cd7776cda",
                "sha256:763a77745f27b86cf26b97887b6842d83720e63b1c48848c0ba9ee54e351d63a",
                "sha256:f0d0eff4c2312a7bd6e21797bdfea5eb35f60e76b555ce2b22794424af2cad36",
                "sha256:275a30dd8ce958b21daa9ad962c6fbc09f98306ee2f486b65c9075dc257b1412",
                "sha256:4d049f83d9cf21d1f5cc0e11deaf36df02790d0e60c1a3829538fb4b61685368",
                "sha256:af5aa97ebe6ce1604747ec1e21af7136ded391bcabe4acef882e718a87c86bcc",
                "sha256:6f1cdceb6a3146f0ccb986521156bef8a422cdbb0863396f7f751f575ba308f4",
                "sha256:bd3cdfae1d3fdd83a2231d608969b38b82349777c2fff9a7c12d54f8ac5c9b38",
                "sha256:4cde6b0bb6f50a5f255eef7b2a42162c661cf776b803225dcac9a659e396bb6b",
                "sha256:ad51d0769d16ba578106a177987dfe3d2e02c1668c852b795b2f6b024068242a",
                "sha256:187cfc6d1e3e8a40a5e64653bcd3239c140807dcf1c09e48021178705a5a6139",
                "sha256:f2392a9484bf6b18f06beaf705b994e31dbb2716c99cf7d03c9c495cd107f364",
            ],
        },
    }
    if fault == "config":
        image["Id"] = "sha256:" + "0" * 64
    elif fault == "platform":
        image["Architecture"] = "arm64"
    elif fault == "digest":
        image["RepoDigests"] = []
    elif fault == "layer":
        image["RootFS"]["Layers"] = image["RootFS"]["Layers"][:-1]
    elif fault == "digests-string":
        image["RepoDigests"] = image["RepoDigests"][0]
    elif fault == "duplicate-digest":
        image["RepoDigests"] *= 2
    elif fault == "rootfs-list":
        image["RootFS"] = []
    elif fault == "rootfs-type":
        image["RootFS"]["Type"] = "unknown"
    elif fault == "layers-string":
        image["RootFS"]["Layers"] = "not a layer inventory"
    if fault == "none":
        assert docker_sources._alertmanager_loaded_base([image]) == image["Id"]
    else:
        with pytest.raises(RuntimeError, match="Exact public base"):
            docker_sources._alertmanager_loaded_base([image])


def test_alertmanager_qualification_timer_restores_remaining_caller_without_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import signal

    now = [0.0]
    timers: list[tuple[float, float]] = []
    handlers: list[object] = []

    def prior_handler(*args: object) -> None:
        pass

    monkeypatch.setenv("ALERTMANAGER_QUALIFY_SECONDS", "825")
    monkeypatch.setattr(docker_sources.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(signal, "getitimer", lambda which: (1200.0, 0.0))
    monkeypatch.setattr(signal, "getsignal", lambda which: prior_handler)
    monkeypatch.setattr(signal, "signal", lambda which, handler: handlers.append(handler))
    monkeypatch.setattr(
        signal, "setitimer", lambda which, value, interval=0.0: timers.append((value, interval))
    )

    def synthetic_phase(output: Path, deadline: float, seconds: int) -> None:
        assert deadline == 825 and seconds == 825
        now[0] = 7.0

    monkeypatch.setattr(docker_sources, "_alertmanager_module_phase", synthetic_phase)
    docker_sources._qualify_alertmanager_modules(tmp_path)
    assert timers == [(825, 0.0), (0, 0.0), (1193.0, 0.0)]
    assert handlers[-1] is prior_handler


def test_alertmanager_source_timer_restores_same_remaining_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import signal

    now = [0.0]
    timers: list[tuple[float, float]] = []

    def parent_handler(*args: object) -> None:
        pass

    handlers: list[object] = []
    artifacts = docker_sources.load_manifest(
        REPO_ROOT / "scripts/ci/docker_source_artifacts.json", artifact="alertmanager"
    )
    monkeypatch.setattr(docker_sources.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(signal, "getitimer", lambda which: (900.0, 0.0))
    monkeypatch.setattr(signal, "getsignal", lambda which: parent_handler)
    monkeypatch.setattr(signal, "signal", lambda which, handler: handlers.append(handler))
    monkeypatch.setattr(
        signal, "setitimer", lambda which, value, interval=0.0: timers.append((value, interval))
    )

    def synthetic_input(*args: object, **kwargs: object) -> None:
        now[0] += 2.5

    monkeypatch.setattr(docker_sources, "_write_verified_artifact", synthetic_input)
    docker_sources._fetch_alertmanager_pair(artifacts, tmp_path, operation_deadline=900)
    assert timers == [(300.0, 0.0), (0, 0.0), (895.0, 0.0)]
    assert handlers[-1] is parent_handler


def test_alertmanager_owned_go_tree_is_searchable_under_umask077_without_execution(
    tmp_path: Path,
) -> None:
    import os
    import time

    toolchain = tmp_path / "alertmanager-go"
    old_mask = os.umask(0o077)
    try:
        (toolchain / "bin").mkdir(parents=True, mode=0o755)
        binary = toolchain / "bin/go"
        binary.write_bytes(b"synthetic non-executed Go bytes")
        binary.chmod(0o755)
        (toolchain / "VERSION").write_bytes(b"synthetic")
    finally:
        os.umask(old_mask)
    assert (toolchain / "bin").stat().st_mode & 0o777 == 0o700
    binding = docker_sources._alertmanager_readonly_go(toolchain, time.monotonic() + 10)
    assert all(row["mode"] == 0o555 for row in binding["after_directories"])
    assert binary.stat().st_mode & 0o777 == 0o555
    assert (toolchain / "VERSION").stat().st_mode & 0o777 == 0o444
    assert binary.read_bytes() == b"synthetic non-executed Go bytes"


def test_alertmanager_complete_artifact_inventory_includes_own_bytes_and_bounds(
    tmp_path: Path,
) -> None:
    import time
    from scripts.ci.prometheus_source_image import MAX_CACHE_BYTES

    evidence = tmp_path / "small"
    evidence.mkdir()
    (evidence / "payload").write_bytes(b"bound actual evidence")
    docker_sources._alertmanager_finalize_payload(evidence, time.monotonic() + 10)
    inventory = json.loads((evidence / "artifact-payload-members.json").read_text())
    assert inventory["files"][0]["path"] == "payload"
    assert "Exactly artifact-payload-members.json" in inventory["inventory_carrier_exception"]
    oversized = tmp_path / "oversized"
    oversized.mkdir()
    with (oversized / "payload").open("wb") as stream:
        stream.truncate(MAX_CACHE_BYTES + 1)
    with pytest.raises(RuntimeError, match="tree_size_bound"):
        docker_sources._alertmanager_finalize_payload(oversized, time.monotonic() + 10)
    assert not (oversized / "artifact-payload-members.json").exists()


@pytest.mark.parametrize("fault", ["valid", "old-url", "query", "port"])
def test_zlib_release_keeps_exact_bytes_at_reviewed_www_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 16)
        )
        if item.name == "zlib"
    )
    assert (artifact.version, artifact.filename, artifact.url) == (
        "1.3.2",
        "zlib-1.3.2.tar.gz",
        "https://www.zlib.net/fossils/zlib-1.3.2.tar.gz",
    )
    assert artifact.sha3_256 == (
        "451bedbd" "cd78dec3" "704df673" "c976fab2" "5beaef6a" "db9433fe" "84665e7b" "f946e325"
    )
    assert artifact.sha256 == (
        "bb329a0a" "2cd0274d" "05519d61" "c667c062" "e06990d7" "2e125ee2" "dfa8de64" "f0119d16"
    )
    if fault == "valid":
        return
    url = {
        "old-url": artifact.url.replace("www.", ""),
        "query": artifact.url + "?x=1",
        "port": artifact.url.replace("www.zlib.net", "www.zlib.net:443"),
    }[fault]
    calls = _stub_source_transport(monkeypatch, payload=b"unused")
    output = tmp_path / "sources"
    with pytest.raises(RuntimeError, match="exact reviewed identity"):
        docker_sources._write_verified_artifact(replace(artifact, url=url), output)
    assert calls == [] and not output.exists()


@pytest.mark.parametrize("status", [200, 301, 302, 303, 307, 308])
def test_zlib_www_challenge_and_redirect_never_admit_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    artifact = next(
        item
        for item in docker_sources.load_manifest(
            REPO_ROOT / "scripts/ci/docker_source_artifacts.json", today=date(2026, 10, 16)
        )
        if item.name == "zlib"
    )
    calls = _stub_source_transport(
        monkeypatch,
        payload=b"<html>challenge</html>",
        code=status,
        location=artifact.url if status != 200 else None,
    )
    output = tmp_path / "sources"
    if status == 200:
        with pytest.raises(RuntimeError, match="zlib SHA3 mismatch"):
            docker_sources._write_verified_artifact(artifact, output)
    else:
        with pytest.raises(HTTPError):
            docker_sources._write_verified_artifact(artifact, output)
    assert calls == [(artifact.url, 60)]
    assert list(output.iterdir()) == []


@pytest.fixture
def alertmanager_proposal_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_READ_TOKEN",
        "GH_ENTERPRISE_TOKEN",
        "GITHUB_ENTERPRISE_TOKEN",
        "GH_HOST",
        "GH_CONFIG_DIR",
        "DOCKER_CONFIG",
        "DOCKER_AUTH_CONFIG",
        "NETRC",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "DEVPI_CI_USER",
        "DEVPI_CI_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in _load_workflow(WORKFLOWS_DIR / "cd.yml")["env"].items():
        if name.startswith("ALERTMANAGER_"):
            monkeypatch.setenv(name, value)
    for name, value in {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": "Katsiarynakavaleuskaya/PulsePlate",
        "GITHUB_REPOSITORY_ID": "1043311030",
        "GITHUB_REF": "refs/heads/codex/dependency-alertmanager-remediation",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": "a" * 40,
        "GH_TOKEN": "synthetic-proposal-credential",
        "GITHUB_TOKEN": "synthetic-proposal-credential",
        "GITHUB_REPOSITORY_OWNER": "Katsiarynakavaleuskaya",
    }.items():
        monkeypatch.setenv(name, value)


def _alertmanager_proposal_arguments(output: Path) -> list[str]:
    return [
        "--artifact",
        "alertmanager",
        "--alertmanager-stage",
        "build",
        "--source-sha",
        "a" * 40,
        "--alertmanager-qualification-run",
        str(docker_sources._ALERT_Q_RUN),
        "--alertmanager-qualification-artifact",
        str(docker_sources._ALERT_Q_ARTIFACT),
        "--alertmanager-qualification-source",
        docker_sources._ALERT_Q_SOURCE,
        "--alertmanager-support-run",
        str(docker_sources._ALERT_S_RUN),
        "--alertmanager-support-artifact",
        str(docker_sources._ALERT_S_ARTIFACT),
        "--alertmanager-support-source",
        docker_sources._ALERT_S_SOURCE,
        "--output-dir",
        str(output),
    ]


def _alertmanager_buildinfo(binary: str) -> bytes:
    # Native Go with -trimpath omits -ldflags; the actual --version owns stamps.
    return (
        "/out/" + binary + ": go1.27.2\n"
        "\tpath\tgithub.com/prometheus/alertmanager/cmd/" + binary + "\n"
        "\tmod\tgithub.com/prometheus/alertmanager\t(devel)\n"
        "\tdep\tgolang.org/x/net\tv0.60.0\th1:synthetic\n"
        "\tdep\tgoogle.golang.org/grpc\tv1.83.2\th1:synthetic\n"
        "\tdep\texample.invalid/" + binary + "\tv1.2.3\th1:synthetic\n"
        "\tbuild\tCGO_ENABLED=0\n\tbuild\tGOOS=linux\n\tbuild\tGOARCH=amd64\n"
        "\tbuild\t-tags=netgo\n\tbuild\t-trimpath=true\n"
    ).encode()


@pytest.mark.parametrize("binary", ["alertmanager", "amtool"])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "Go",
        "module",
        "platform",
        "CGO",
        "tags",
        "duplicate",
        "replacement",
        "fictional-ldflags",
        "main",
        "command",
    ],
)
def test_alertmanager_actual_buildinfo_rejects_stale_second_binary_or_recipe(
    binary: str, fault: str | None
) -> None:
    raw = _alertmanager_buildinfo(binary)
    if fault == "Go":
        raw = raw.replace(b"go1.27.2", b"go1.26.8")
    elif fault == "module":
        raw = raw.replace(b"v1.83.2", b"v1.83.1")
    elif fault == "platform":
        raw = raw.replace(b"GOARCH=amd64", b"GOARCH=arm64")
    elif fault == "CGO":
        raw = raw.replace(b"CGO_ENABLED=0", b"CGO_ENABLED=1")
    elif fault == "tags":
        raw = raw.replace(b"-tags=netgo", b"-tags=other")
    elif fault == "duplicate":
        raw += b"\tbuild\tGOARCH=amd64\n"
    elif fault == "replacement":
        raw += b"\t=>\tunreviewed.example/module\tv1.0.0\n"
    elif fault == "fictional-ldflags":
        raw += ("\tbuild\t-ldflags=" + docker_sources._ALERT_BUILD_METADATA + "\n").encode()
    elif fault == "main":
        raw = raw.replace(b"\t(devel)", b"\tv0.34.0")
    elif fault == "command":
        raw = raw.replace(b"/cmd/" + binary.encode(), b"/cmd/foreign")
    if fault:
        with pytest.raises(RuntimeError, match="AM_"):
            docker_sources._alertmanager_build_information(raw, binary)
    else:
        assert docker_sources._alertmanager_build_information(raw, binary)["Go"] == "go1.27.2"


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "second-binary",
        "stale-module",
        "CVE-low",
        "new-blocker",
        "secret",
        "null-results",
        "missing-package",
        "duplicate-target",
        "wrong-subject",
        "missing-OS",
        "extra-OS",
        "duplicate-OS",
        "version-OS",
        "PURL-OS",
        "source-OS",
        "arch-OS",
        "malformed-OS",
        "OS-family",
        "encoding-only",
        "changed-reference",
    ],
)
def test_alertmanager_candidate_scan_requires_real_complete_pair_and_unsuppressed_inventory(
    fault: str | None,
) -> None:
    build_information = {
        name: docker_sources._alertmanager_build_information(_alertmanager_buildinfo(name), name)
        for name in ("alertmanager", "amtool")
    }
    image_id = "sha256:" + "1" * 64
    packages = [
        {
            "ID": name + "@1.0",
            "Name": name,
            "Version": "1.0",
            "Arch": "all",
            "SrcName": "synthetic-source",
            "SrcVersion": "1.0",
            "Identifier": {
                "PURL": "pkg:deb/debian/" + name + "@1.0?arch=all",
                "UID": "synthetic-opaque",
            },
            "Layer": {"DiffID": "sha256:" + "3" * 64},
        }
        for name in ("synthetic-base-one", "synthetic-base-two")
    ]
    os_row = {
        "Target": "retained-base-export (debian synthetic)",
        "Class": "os-pkgs",
        "Type": "debian",
        "Packages": packages,
    }
    base: dict[str, Any] = {
        "ArtifactType": "container_image",
        "Metadata": {
            "ImageID": docker_sources._ALERT_BASE_CONFIG,
            "OS": {"Family": "debian", "Name": "synthetic"},
        },
        "Results": [deepcopy(os_row)],
    }
    rows = [deepcopy(os_row)]
    for binary in ("alertmanager", "amtool"):
        rows.append(
            {
                "Target": "usr/bin/" + binary,
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [
                    {"Name": name, "Version": version}
                    for name, version in (
                        ("stdlib", "v1.27.2"),
                        ("golang.org/x/net", "v0.60.0"),
                        ("google.golang.org/grpc", "v1.83.2"),
                        ("example.invalid/" + binary, "v1.2.3"),
                        ("github.com/prometheus/alertmanager", "v0.34.1"),
                    )
                ],
            }
        )
    report: dict[str, Any] = {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "Metadata": {"ImageID": image_id, "OS": {"Family": "debian", "Name": "synthetic"}},
        "Results": rows,
    }
    if fault == "second-binary":
        rows.pop()
    elif fault == "stale-module":
        rows[-1]["Packages"][-1]["Version"] = "v1.83.1"
    elif fault in ("CVE-low", "new-blocker"):
        rows[-1]["Vulnerabilities"] = [
            {
                "VulnerabilityID": "CVE-2026-97031" if fault == "CVE-low" else "CVE-SYNTHETIC-NEW",
                "PkgName": "stdlib",
                "InstalledVersion": "v1.27.2",
                "Severity": "LOW" if fault == "CVE-low" else "HIGH",
            }
        ]
    elif fault == "secret":
        rows[0]["Secrets"] = [{"RuleID": "synthetic"}]
    elif fault == "null-results":
        report["Results"] = None
    elif fault == "missing-package":
        rows[-1]["Packages"].pop()
    elif fault == "duplicate-target":
        rows.append(deepcopy(rows[-1]))
    elif fault == "wrong-subject":
        report["Metadata"]["ImageID"] = "sha256:" + "2" * 64
    elif fault == "missing-OS":
        rows[0]["Packages"].pop()
    elif fault == "extra-OS":
        extra = deepcopy(packages[0])
        extra["Name"] = "extra-package"
        extra["ID"] = "extra-package@1.0"
        rows[0]["Packages"].append(extra)
    elif fault == "duplicate-OS":
        rows[0]["Packages"].append(deepcopy(rows[0]["Packages"][0]))
    elif fault == "version-OS":
        rows[0]["Packages"][0]["Version"] = "2.0"
    elif fault == "PURL-OS":
        rows[0]["Packages"][0]["Identifier"]["PURL"] += "&unapproved=true"
    elif fault == "source-OS":
        rows[0]["Packages"][0]["SrcName"] = "changed-source"
    elif fault == "arch-OS":
        rows[0]["Packages"][0]["Arch"] = "arm64"
    elif fault == "malformed-OS":
        rows[0]["Packages"][0]["ID"] = None
    elif fault == "OS-family":
        report["Metadata"]["OS"]["Family"] = "unrecognized"
    elif fault == "encoding-only":
        rows[0]["Target"] = "candidate.oci.tar (debian synthetic)"
        rows[0]["Packages"][0]["Layer"] = {
            "Digest": "sha256:" + "4" * 64,
            "DiffID": "sha256:" + "3" * 64,
        }
        rows[0]["Packages"][0]["Identifier"]["UID"] = "new-native-opaque-UID"
    elif fault == "changed-reference":
        for selected in (rows[0], base["Results"][0]):
            selected["Packages"].pop()
            selected["Packages"][0]["Version"] = "authorized-future-version"
            selected["Packages"][0]["SrcVersion"] = "authorized-future-version"
            selected["Packages"][0]["ID"] = "synthetic-base-one@authorized-future-version"
            selected["Packages"][0]["Identifier"][
                "PURL"
            ] = "pkg:deb/debian/synthetic-base-one@authorized-future-version?arch=all"
    if fault not in (None, "encoding-only", "changed-reference"):
        with pytest.raises(RuntimeError, match="AM_"):
            docker_sources._alertmanager_candidate_inventory(
                report, image_id, base, build_information
            )
    else:
        actual = docker_sources._alertmanager_candidate_inventory(
            report, image_id, base, build_information
        )
        assert (
            len(actual["packages"]) == (11 if fault == "changed-reference" else 12)
            and actual["findings"] == []
        )


@pytest.fixture
def alertmanager_proposal_graph(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> dict[str, Any]:
    import gzip
    import tarfile

    compressed = getattr(request, "param", None) == "gzip"
    support = tmp_path / "support"
    base = support / "base-layout"
    seed = tmp_path / "candidate-seed"
    for layout in (base, seed):
        (layout / "blobs/sha256").mkdir(parents=True)

    def blob(layout: Path, body: bytes, media: str) -> dict[str, Any]:
        digest = sha256(body).hexdigest()
        (layout / "blobs/sha256" / digest).write_bytes(body)
        return {"mediaType": media, "digest": "sha256:" + digest, "size": len(body)}

    def tar(rows: list[tuple[str, bytes | None, int, int, int]]) -> bytes:
        output = BytesIO()
        with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, raw, mode, uid, gid in rows:
                info = tarfile.TarInfo(name)
                info.mode, info.uid, info.gid = mode, uid, gid
                info.type = tarfile.DIRTYPE if raw is None else tarfile.REGTYPE
                info.size = 0 if raw is None else len(raw)
                archive.addfile(info, None if raw is None else BytesIO(raw))
        return output.getvalue()

    layers = []
    diff_ids = []
    for index in range(13):
        rows = [
            (
                "etc/ssl/certs/ca-certificates.crt" if index == 0 else "base-" + str(index),
                b"synthetic CA" if index == 0 else str(index).encode(),
                0o444,
                0,
                0,
            )
        ]
        raw = tar(rows)
        diff_ids.append("sha256:" + sha256(raw).hexdigest())
        layers.append(
            blob(
                base,
                gzip.compress(raw, mtime=0) if compressed else raw,
                "application/vnd.oci.image.layer.v1.tar" + ("+gzip" if compressed else ""),
            )
        )
    base_config = {
        "os": "linux",
        "architecture": "amd64",
        "config": {"Env": ["PATH=/usr/bin"]},
        "rootfs": {"type": "layers", "diff_ids": diff_ids},
    }
    config = blob(
        base, json.dumps(base_config).encode(), "application/vnd.oci.image.config.v1+json"
    )
    manifest = blob(
        base,
        json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "config": config,
                "layers": layers,
            }
        ).encode(),
        "application/vnd.oci.image.manifest.v1+json",
    )
    (base / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}')
    (base / "index.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.index.v1+json",
                "manifests": [manifest],
            }
        )
    )
    for path in (base / "blobs/sha256").iterdir():
        shutil.copyfile(path, seed / "blobs/sha256" / path.name)
    binaries = {
        name: ("synthetic produced " + name).encode() for name in ("alertmanager", "amtool")
    }
    inputs = tmp_path / "inputs"
    for name in ("source", "modules", "alertmanager-go"):
        (inputs / name).mkdir(parents=True)
    for name in ("LICENSE", "NOTICE"):
        (inputs / "source" / name).write_bytes(("synthetic " + name).encode())
    (inputs / "source/main.go").write_bytes(b"package main")
    probe = b"synthetic original multicall probe"
    plugin = b"synthetic qualified Buildx"
    (support / "empty-docker-config/cli-plugins").mkdir(parents=True)
    (support / "empty-docker-config/cli-plugins/docker-buildx").write_bytes(plugin)
    (support / "probe-bin-bracket").write_bytes(probe)
    (support / "base-image.tar").write_bytes(b"synthetic base transport")
    monkeypatch.setattr(docker_sources, "_ALERT_BASE_CONFIG", config["digest"])
    monkeypatch.setattr(docker_sources, "_ALERT_BASE_MANIFEST", manifest["digest"])
    monkeypatch.setattr(docker_sources, "_ALERT_PROBE_SHA256", sha256(probe).hexdigest())
    monkeypatch.setattr(docker_sources, "_ALERT_BUILDX_SHA256", sha256(plugin).hexdigest())
    values = {"usr/bin/" + name: raw for name, raw in binaries.items()}
    values.update(
        {
            "usr/bin/wget": probe,
            "usr/bin/httpd": probe,
            "etc/alertmanager/alertmanager.yml": (
                REPO_ROOT / "deploy/alertmanager/alertmanager.yml"
            ).read_bytes(),
            "LICENSE": (inputs / "source/LICENSE").read_bytes(),
            "NOTICE": (inputs / "source/NOTICE").read_bytes(),
        }
    )
    rows = [("alertmanager", None, 0o700, 65534, 65534)] + [
        (name, raw, 0o555 if name.startswith("usr/bin/") else 0o444, 0, 0)
        for name, raw in values.items()
    ]
    actual_config = deepcopy(base_config)
    actual_config["config"].update(
        {
            "User": "65534:65534",
            "Entrypoint": ["/bin/alertmanager"],
            "Cmd": [
                "--config.file=/etc/alertmanager/alertmanager.yml",
                "--storage.path=/alertmanager",
                "--cluster.listen-address=",
            ],
            "WorkingDir": "/alertmanager",
            "Volumes": {"/alertmanager": {}},
            "ExposedPorts": {"9093/tcp": {}},
        }
    )
    data = {
        "support": support,
        "base": base,
        "seed": seed,
        "inputs": inputs,
        "rows": rows,
        "values": values,
        "binaries": binaries,
        "expected": {k: sha256(v).hexdigest() for k, v in values.items()},
        "config": actual_config,
    }

    def write() -> None:
        raw = tar(data["rows"])
        payload = blob(
            seed,
            gzip.compress(raw, mtime=0) if compressed else raw,
            "application/vnd.oci.image.layer.v1.tar" + ("+gzip" if compressed else ""),
        )
        configuration = deepcopy(data["config"])
        configuration["rootfs"]["diff_ids"] = diff_ids + ["sha256:" + sha256(raw).hexdigest()]
        config_row = blob(
            seed, json.dumps(configuration).encode(), "application/vnd.oci.image.config.v1+json"
        )
        descriptor = blob(
            seed,
            json.dumps(
                {
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.oci.image.manifest.v1+json",
                    "config": config_row,
                    "layers": [*layers, payload],
                }
            ).encode(),
            "application/vnd.oci.image.manifest.v1+json",
        )
        (seed / "oci-layout").write_text('{"imageLayoutVersion":"1.0.0"}')
        (seed / "index.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 2,
                    "mediaType": "application/vnd.oci.image.index.v1+json",
                    "manifests": [descriptor],
                }
            )
        )
        keep = {v["digest"][7:] for v in [*layers, payload, config_row, descriptor]}
        for path in (seed / "blobs/sha256").iterdir():
            if path.name not in keep:
                path.unlink()

    data["write"] = write
    write()
    return data


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing-amtool",
        "mode",
        "owner",
        "storage-uid",
        "storage-gid",
        "storage-mode",
        "extra",
        "alias",
        "bytes",
        "platform",
        "environment",
        "attestation",
    ],
)
@pytest.mark.parametrize("alertmanager_proposal_graph", [None, "gzip"], indirect=True)
def test_alertmanager_COPY_graph_rejects_real_subject_or_payload_drift(
    alertmanager_proposal_graph: dict[str, Any],
    fault: str | None,
) -> None:
    d = alertmanager_proposal_graph
    if fault == "missing-amtool":
        d["rows"] = [row for row in d["rows"] if row[0] != "usr/bin/amtool"]
    elif fault in ("mode", "owner", "alias", "bytes"):
        d["rows"] = [
            (
                "../usr/bin/amtool" if fault == "alias" and name == "usr/bin/amtool" else name,
                raw + b"changed" if fault == "bytes" and name == "usr/bin/amtool" else raw,
                0o644 if fault == "mode" and name == "usr/bin/amtool" else mode,
                1 if fault == "owner" and name == "usr/bin/amtool" else uid,
                gid,
            )
            for name, raw, mode, uid, gid in d["rows"]
        ]
    elif fault in ("storage-uid", "storage-gid", "storage-mode"):
        d["rows"][0] = (
            "alertmanager",
            None,
            0o755 if fault == "storage-mode" else 0o700,
            0 if fault == "storage-uid" else 65534,
            0 if fault == "storage-gid" else 65534,
        )
    elif fault == "extra":
        d["rows"].append(("usr/bin/unapproved", b"unexpected", 0o555, 0, 0))
    elif fault == "platform":
        d["config"]["architecture"] = "arm64"
    elif fault == "environment":
        d["config"]["config"]["Env"].append("HTTPS_PROXY=unreviewed.invalid")
    d["write"]()
    if fault == "attestation":
        path = d["seed"] / "index.json"
        index = json.loads(path.read_text())
        index["manifests"].append(deepcopy(index["manifests"][0]))
        path.write_text(json.dumps(index))
    if fault:
        with pytest.raises(
            RuntimeError,
            match=(
                "^AM_storage_directory_owner_mode$"
                if fault in ("storage-uid", "storage-gid", "storage-mode")
                else None
            ),
        ):
            docker_sources._alertmanager_candidate_graph(d["seed"], d["support"], d["expected"])
    else:
        graph = docker_sources._alertmanager_candidate_graph(d["seed"], d["support"], d["expected"])
        assert graph["files"] == d["expected"] and len(graph["layers"]) == 14
        assert graph["default_CA_sha256"] == sha256(b"synthetic CA").hexdigest()


@pytest.mark.parametrize(
    "current_epoch,caller,omit_base_member",
    [
        (epoch, caller, omitted)
        for epoch in (False, True)
        for caller in ("retained-candidate", "retained-failed-candidate")
        for omitted in (False, True)
    ]
    + [
        (True, "producer-" + fault, False)
        for fault in ("missing", "unknown", "mixed", "old-marker", "old-status")
    ],
)
def test_alertmanager_both_security_callers_use_actual_authenticated_support_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alertmanager_proposal_environment: None,
    alertmanager_proposal_graph: dict[str, Any],
    caller: str,
    omit_base_member: bool,
    current_epoch: bool,
) -> None:
    """Bind both callers to the base; a failed build never reaches reconciliation."""
    import zipfile
    from scripts.ci import prometheus_source_image as transport

    source_sha = "a" * 40 if current_epoch else docker_sources._ALERT_HISTORICAL_C10["source"]

    def build_raw(name: str) -> bytes:
        raw = _alertmanager_buildinfo(name)
        return raw.replace(b"go1.27.2", b"go1.27.3") if current_epoch else raw

    build_information = {
        name: docker_sources._alertmanager_build_information(
            build_raw(name), name, current=current_epoch
        )
        for name in ("alertmanager", "amtool")
    }
    d = alertmanager_proposal_graph
    graph = docker_sources._alertmanager_candidate_graph(d["seed"], d["support"], d["expected"])
    image_id = graph["config"]["digest"]
    packages = [
        {
            "ID": name + "@2",
            "Name": name,
            "Version": "2",
            "Arch": "all",
            "SrcName": name,
            "SrcVersion": "2",
            "Identifier": {"PURL": "pkg:deb/debian/" + name + "@2?arch=all"},
        }
        for name in ("future-one", "future-two")
    ]
    base: dict[str, Any] = {
        "ArtifactType": "container_image",
        "Metadata": {
            "ImageID": (
                transport.BASE_CONFIG if current_epoch else docker_sources._ALERT_BASE_CONFIG
            ),
            "OS": {"Family": "debian", "Name": "future"},
        },
        "Results": [
            {"Target": "base export", "Class": "os-pkgs", "Type": "debian", "Packages": packages}
        ],
    }
    full = deepcopy(base)
    full["SchemaVersion"] = 2
    full["Metadata"]["ImageID"] = image_id
    if omit_base_member:
        full["Results"][0]["Packages"].pop()
    for binary in ("alertmanager", "amtool"):
        full["Results"].append(
            {
                "Target": "usr/bin/" + binary,
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": [
                    {"Name": name, "Version": version}
                    for name, version in (
                        ("stdlib", "v1.27.3" if current_epoch else "v1.27.2"),
                        ("golang.org/x/net", "v0.60.0"),
                        ("google.golang.org/grpc", "v1.83.2"),
                        ("example.invalid/" + binary, "v1.2.3"),
                        ("github.com/prometheus/alertmanager", "0.34.1"),
                    )
                ],
            }
        )
    support = d["support"]
    (support / "evidence").mkdir(parents=True)
    (support / "evidence/base-full-supported-scan.private.json").write_text(json.dumps(base))
    (support / "trivy").write_bytes(b"synthetic scanner bytes")
    (support / "trivy-cache/db").mkdir(parents=True)
    (support / "trivy-cache/db/trivy.db").write_bytes(b"synthetic frozen DB")
    (support / "trivy-cache/db/metadata.json").write_text('{"Version":2}')
    monkeypatch.setattr(
        docker_sources, "_ALERT_TRIVY_SHA256", sha256((support / "trivy").read_bytes()).hexdigest()
    )
    monkeypatch.setattr(
        docker_sources,
        "_ALERT_DB",
        {
            "db/" + p.name: sha256(p.read_bytes()).hexdigest()
            for p in (support / "trivy-cache/db").iterdir()
        },
    )
    original = docker_sources._alertmanager_candidate_inventory
    bound: list[dict[str, Any]] = []

    def consume(
        report: dict[str, Any],
        subject: str,
        actual_base: dict[str, Any],
        actual_information: dict[str, Any],
        *,
        current: bool = False,
    ) -> dict[str, Any]:
        assert actual_base == base
        bound.append(actual_base)
        assert actual_information == build_information
        assert current is current_epoch
        original(report, subject, actual_base, actual_information, current=current)
        raise RuntimeError("synthetic-stop-after-actual-OS-reconciliation")

    monkeypatch.setattr(docker_sources, "_alertmanager_candidate_inventory", consume)
    plan = {"UI_file_hashes": {"index.html.gz": "f" * 64}}
    source = {
        path: (REPO_ROOT / path).read_bytes()
        for path in (
            *docker_sources._ALERT_Q_SOURCE_FILES,
            "tests/test_notify_premium_alias_checkpoint_failure.py",
        )
    }
    if not current_epoch:
        source["deploy/alertmanager/Containerfile"] = _historical_alertmanager_recipe()
    files = {"producer-source/" + path: raw for path, raw in source.items()}
    files["security-evidence/candidate-full-supported.private.json"] = json.dumps(full).encode()
    phase_records = {}
    for phase in ("pair", "security", "native"):
        label = "full-AM-native" if phase == "native" else "synthetic-" + phase
        raw = (
            (
                b"native_AM_producer_image_controls=pass"
                if current_epoch
                else b"native_AM_full_candidate_controls=pass"
            )
            if phase == "native"
            else b"synthetic raw terminal"
        )
        if phase == "native" and caller == "producer-mixed":
            raw += b"\nnative_AM_full_candidate_controls=pass"
        elif phase == "native" and caller == "producer-old-marker":
            raw = b"native_AM_full_candidate_controls=pass"
        files[phase + "-evidence/" + label + ".stdout"] = raw
        files[phase + "-evidence/" + label + ".stderr"] = b""
        phase_records[phase] = [
            {
                "exit": 0,
                "failure": None,
                "stdout": "/original/" + label + ".stdout",
                "stderr": "/original/" + label + ".stderr",
                "stdout_sha256": sha256(raw).hexdigest(),
                "stderr_sha256": sha256(b"").hexdigest(),
            }
        ]
    observed = {
        "source": source_sha,
        "OCI_archive_sha256": "e" * 64,
        "status": (
            "OBSERVED_PRODUCER_IMAGE_SECURITY"
            if current_epoch
            else "OBSERVED_NATIVE_SECURITY_ACCEPTED"
        ),
        "failure": None,
        "cleanup_failure": None,
        "compiler_starts": 2,
        "logical_build_starts": 1,
        "automatic_retries": 0,
        "owned_absence_observed": True,
        "plan": plan,
        "UI_file_hashes": plan["UI_file_hashes"],
        "producer_source_files": {k: sha256(v).hexdigest() for k, v in source.items()},
        "upstream": {
            "qualification": {"zip_sha256": docker_sources._ALERT_Q_ZIP_SHA256},
            "support": {"zip_sha256": docker_sources._ALERT_S_ZIP_SHA256},
        },
        "native_records": phase_records["pair"],
        "native": {"native_records": phase_records["native"]},
        "security": {
            "native_records": phase_records["security"],
            "scanner": {
                "sha256": docker_sources._ALERT_TRIVY_SHA256,
                "DB": docker_sources._ALERT_DB,
            },
        },
        "graph": {"config": {"digest": image_id}},
    }
    if current_epoch and caller != "producer-missing":
        observed["native"]["validation_scope"] = (
            "unknown" if caller == "producer-unknown" else "producer_image"
        )
    observed["build_information"] = build_information
    observed["output_hashes"] = {
        name: sha256(name.encode()).hexdigest() for name in ("alertmanager", "amtool")
    }
    observed["graph"]["files"] = {
        "usr/bin/" + name: digest for name, digest in observed["output_hashes"].items()
    }
    for binary in ("alertmanager", "amtool"):
        raw = build_raw(binary)
        files["pair-evidence/" + binary + "-buildinfo-attach.stdout"] = raw
        files["pair-evidence/" + binary + "-buildinfo-attach.stderr"] = b""
        observed["native_records"].append(
            {
                "exit": 0,
                "failure": None,
                "stdout": "/original/" + binary + "-buildinfo-attach.stdout",
                "stderr": "/original/" + binary + "-buildinfo-attach.stderr",
                "stdout_sha256": sha256(raw).hexdigest(),
                "stderr_sha256": sha256(b"").hexdigest(),
            }
        )
    if caller == "producer-old-status":
        observed["status"] = "OBSERVED_NATIVE_SECURITY_ACCEPTED"
    if caller == "retained-failed-candidate":
        observed["status"] = "HOLD_NO_EXECUTION_OUTCOME"
        observed["failure"] = "QualificationError:layout_transport_annotation"
    qualification = {
        "source": source_sha,
        "zip_sha256": "1" * 64,
        "source_files": {
            key: sha256(source[key]).hexdigest() for key in docker_sources._ALERT_Q_SOURCE_FILES
        },
    }
    support_binding = {**qualification, "zip_sha256": "2" * 64}
    support_report = {"scanner": {"DB": dict(docker_sources._ALERT_DB)}}
    if current_epoch:
        observed["upstream"] = {"qualification": qualification, "support": support_binding}
        # Current S owns the actual DB; the old retained DB cannot substitute.
        monkeypatch.setattr(
            docker_sources, "_ALERT_DB", {key: "0" * 64 for key in docker_sources._ALERT_DB}
        )
    files["candidate-observation.json"] = json.dumps(observed).encode()
    directories = sorted(
        {
            str(parent)
            for name in files
            for parent in PurePosixPath(name).parents
            if str(parent) != "."
        }
    )
    files["artifact-payload-members.json"] = json.dumps(
        {
            "files": [
                {
                    "path": name,
                    "size": len(raw),
                    "mode": 0o600,
                    "sha256": sha256(raw).hexdigest(),
                }
                for name, raw in files.items()
            ],
            "directories": [
                {"path": name, "type": "directory", "mode": 0o700} for name in directories
            ],
            "inventory_carrier_exception": "Exactly artifact-payload-members.json is bound by external artifact bytes; its own hash is not recursively embedded.",
        }
    ).encode()
    archive = tmp_path / "candidate.zip"
    with zipfile.ZipFile(archive, "w") as retained:
        for name, raw in files.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            retained.writestr(info, raw)

    monkeypatch.setattr(
        docker_sources,
        "_ALERT_ACCEPTED_CANDIDATE",
        {
            "run": 101,
            "attempt": 1,
            "artifact": 102,
            "source": source_sha,
            "job": 103,
            "zip_sha256": sha256(archive.read_bytes()).hexdigest(),
            "source_files": {path: sha256(raw).hexdigest() for path, raw in source.items()},
            "graph": deepcopy(observed["graph"]),
            "OCI_archive_sha256": "e" * 64,
        },
    )

    if not current_epoch:
        # This generated transport has its own exact synthetic historical tuple.
        monkeypatch.setattr(
            docker_sources,
            "_ALERT_HISTORICAL_C10",
            deepcopy(docker_sources._ALERT_ACCEPTED_CANDIDATE),
        )

    def invoke() -> None:
        docker_sources._alertmanager_candidate_payload(
            archive,
            tmp_path / "candidate",
            source,
            {"plan": plan},
            support,
            qualification=qualification if current_epoch else None,
            support_binding=support_binding if current_epoch else None,
            support_report=support_report if current_epoch else None,
        )

    with pytest.raises(
        RuntimeError,
        match=(
            "AM_candidate_positive_predecessors_and_finite_recipe"
            if caller == "producer-old-status"
            else (
                "AM_candidate_native_terminal"
                if caller.startswith("producer-")
                else (
                    "AM_candidate_positive_predecessors_and_finite_recipe"
                    if caller == "retained-failed-candidate"
                    else (
                        "AM_candidate_all_and_only_authenticated_base_packages"
                        if omit_base_member
                        else "synthetic-stop-after-actual-OS-reconciliation"
                    )
                )
            )
        ),
    ):
        invoke()
    assert bound == ([base] if caller == "retained-candidate" else [])


@pytest.mark.parametrize("binary", ["alertmanager", "amtool"])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing-dependency",
        "extra-dependency",
        "duplicate-dependency",
        "version-drift",
        "other-binary-union",
        "missing-main",
        "wrong-main",
        "empty-expected",
        "versioned-main",
    ],
)
def test_alertmanager_candidate_go_inventory_matches_each_actual_compiled_dependency(
    binary: str,
    fault: str | None,
) -> None:
    information = {
        name: docker_sources._alertmanager_build_information(
            (
                _alertmanager_buildinfo(name).replace(b"\t(devel)", b"\tv0.34.1")
                if fault == "versioned-main"
                else _alertmanager_buildinfo(name)
            ),
            name,
        )
        for name in ("alertmanager", "amtool")
    }
    package = {
        "ID": "synthetic-base@1",
        "Name": "synthetic-base",
        "Version": "1",
        "Arch": "all",
        "SrcName": "synthetic-base",
        "SrcVersion": "1",
        "Identifier": {"PURL": "pkg:deb/debian/synthetic-base@1?arch=all"},
    }
    base: dict[str, Any] = {
        "ArtifactType": "container_image",
        "Metadata": {
            "ImageID": docker_sources._ALERT_BASE_CONFIG,
            "OS": {"Family": "debian", "Name": "synthetic"},
        },
        "Results": [
            {
                "Target": "synthetic base",
                "Class": "os-pkgs",
                "Type": "debian",
                "Packages": [package],
            }
        ],
    }
    report = deepcopy(base)
    report["SchemaVersion"] = 2
    image_id = report["Metadata"]["ImageID"] = "sha256:" + "7" * 64
    selected = None
    for name in ("alertmanager", "amtool"):
        # Independent native scanner shape: root resolution is delegated to Trivy.
        packages = [
            {"Name": dependency, "Version": version}
            for dependency, version in (
                ("stdlib", "v1.27.2"),
                ("golang.org/x/net", "v0.60.0"),
                ("google.golang.org/grpc", "v1.83.2"),
                ("example.invalid/" + name, "v1.2.3"),
                ("github.com/prometheus/alertmanager", "v0.34.1"),
            )
        ]
        report["Results"].append(
            {
                "Target": "usr/bin/" + name,
                "Class": "lang-pkgs",
                "Type": "gobinary",
                "Packages": packages,
            }
        )
        if name == binary:
            selected = packages
    assert selected is not None
    if fault == "missing-dependency":
        selected.pop(3)
    elif fault == "extra-dependency":
        selected.append({"Name": "unrelated.invalid/module", "Version": "v1.0.0"})
    elif fault == "duplicate-dependency":
        selected.append(deepcopy(selected[3]))
    elif fault == "version-drift":
        selected[3]["Version"] = "v1.2.4"
    elif fault == "other-binary-union":
        selected.append(
            {
                "Name": "example.invalid/"
                + ("amtool" if binary == "alertmanager" else "alertmanager"),
                "Version": "v1.2.3",
            }
        )
    elif fault == "missing-main":
        selected.pop()
    elif fault == "wrong-main":
        selected[-1]["Version"] = "v0.34.0"
    elif fault == "empty-expected":
        information[binary]["dependencies"]["uncomparable.invalid/module"] = ""
    if fault in (None, "versioned-main"):
        assert (
            docker_sources._alertmanager_candidate_inventory(report, image_id, base, information)[
                "findings"
            ]
            == []
        )
    else:
        with pytest.raises(RuntimeError, match="AM_candidate_"):
            docker_sources._alertmanager_candidate_inventory(report, image_id, base, information)


@pytest.mark.parametrize("alertmanager_proposal_graph", ["gzip"], indirect=True)
@pytest.mark.parametrize(
    ("phase", "fault"),
    [
        (phase, fault)
        for phase in ("native",)
        for fault in (
            None,
            "tamper",
            "missing",
            "extra",
            "alias",
            "duplicate",
            "header",
            "truncated",
            "graph",
            "source-drift",
            "source-drift-observation",
            "destination",
            "loaded-ID",
            "loaded-diffID",
            "space-initial",
            "space-drop",
        )
    ],
)
def test_alertmanager_real_phase_renders_private_Docker_transport_without_changing_OCI(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alertmanager_proposal_environment: None,
    alertmanager_proposal_graph: dict[str, Any],
    phase: str,
    fault: str | None,
) -> None:
    import tarfile
    from scripts.ci import prometheus_source_image as transport

    d = alertmanager_proposal_graph
    graph = docker_sources._alertmanager_candidate_graph(d["seed"], d["support"], d["expected"])
    source = tmp_path / "candidate.oci.tar"
    transport.pack_layout(d["seed"], source)
    original = source.read_bytes()
    with tarfile.open(fileobj=BytesIO(original), mode="r:") as archive:
        canonical = {
            member.name: archive.extractfile(member).read() for member in archive.getmembers()
        }
    layer_paths = ["blobs/sha256/" + row["digest"][7:] for row in graph["layers"]]
    assert all(canonical[name].startswith(b"\x1f\x8b") for name in layer_paths)
    assert "manifest.json" not in canonical
    graph_checks: list[Path] = []
    unpack_calls: list[Path] = []
    load_calls: list[Path] = []
    inventory_calls: list[Any] = []
    original_graph = docker_sources._alertmanager_candidate_graph
    original_gunzip, original_unpack = transport._gunzip, transport.unpack_layout
    original_load = docker_sources._alertmanager_docker_load_transport
    recognizing_graph = False

    def recognize(layout: Path, support: Path, files: dict[str, str]) -> dict[str, Any]:
        nonlocal recognizing_graph
        assert layout == work / "docker-load-layout" and files == graph["files"]
        graph_checks.append(layout)
        recognizing_graph = True
        try:
            return original_graph(layout, support, files)
        finally:
            recognizing_graph = False

    def gunzip(*args: Any, **kwargs: Any) -> bytes:
        assert recognizing_graph, "private load rendering transformed a layer"
        return original_gunzip(*args, **kwargs)

    def unpack(payload: bytes, destination: Path) -> None:
        unpack_calls.append(destination)
        original_unpack(payload, destination)

    def load(selected: Path, *args: Any) -> dict[str, Any]:
        load_calls.append(selected)
        return original_load(selected, *args)

    monkeypatch.setattr(docker_sources, "_alertmanager_candidate_graph", recognize)
    monkeypatch.setattr(docker_sources, "_alertmanager_docker_load_transport", load)
    monkeypatch.setattr(transport, "_gunzip", gunzip)
    monkeypatch.setattr(transport, "unpack_layout", unpack)
    if fault in ("tamper", "missing", "extra", "alias", "duplicate", "header"):
        with tarfile.open(source, "w", format=tarfile.USTAR_FORMAT) as archive:
            for name, raw in canonical.items():
                if fault == "missing" and name == layer_paths[-1]:
                    continue
                if fault == "tamper" and name == layer_paths[-1]:
                    raw = raw[:-1] + bytes([raw[-1] ^ 1])
                name = "./index.json" if fault == "alias" and name == "index.json" else name
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = (
                    len(raw),
                    0o600 if fault == "header" else 0o644,
                    transport.SOURCE_DATE_EPOCH,
                )
                archive.addfile(info, BytesIO(raw))
            if fault in ("extra", "duplicate"):
                name = "unapproved" if fault == "extra" else "index.json"
                raw = b"unapproved" if fault == "extra" else canonical[name]
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(raw), 0o644, transport.SOURCE_DATE_EPOCH
                archive.addfile(info, BytesIO(raw))
    elif fault == "truncated":
        with tarfile.open(fileobj=BytesIO(original), mode="r:") as archive:
            member = archive.getmember(layer_paths[-1])
            source.write_bytes(original[: member.offset_data + member.size - 1])
    elif fault == "graph":
        graph = deepcopy(graph)
        graph["manifest"]["digest"] = "sha256:" + "9" * 64
    entered = source.read_bytes()
    if fault in ("source-drift", "source-drift-observation"):
        original_blob = transport._blob
        drifted = False

        def blob(layout: Path, descriptor: dict[str, Any]) -> bytes:
            nonlocal drifted
            raw = original_blob(layout, descriptor)
            if not drifted:
                source.write_bytes(entered + b"synthetic source drift")
                drifted = True
            return raw

        monkeypatch.setattr(transport, "_blob", blob)
    work = tmp_path / phase
    layout = work / "docker-load-layout"
    scan_fault = (fault or "").removesuffix("-observation")
    scan_failure = scan_fault.startswith("scan-")
    scan_error = RuntimeError("synthetic actual scanner initialization failure")

    def mutate_scan_input() -> None:
        kind = scan_fault.rsplit("-", 1)[-1]
        if kind == "source" or scan_fault == "scan-error":
            source.write_bytes(original + b"synthetic scan-time source drift")
        if scan_fault == "scan-error":
            (layout / "unapproved").write_bytes(b"must not mask native error")
        elif kind == "alias":
            (layout / "alias-index").symlink_to(layout / "index.json")
        elif kind == "missing":
            (layout / layer_paths[-1]).unlink()
        elif kind == "extra":
            (layout / "unapproved").write_bytes(b"unexpected closed-namespace member")
        elif kind == "tamper":
            path = layout / layer_paths[-1]
            raw = path.read_bytes()
            path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))

    original_disk_usage = shutil.disk_usage
    usage_type = type(original_disk_usage(tmp_path))
    resource_observations: list[Any] = []
    delegated_resources: list[tuple[Any, tuple[Any, ...], dict[str, Any]]] = []

    def disk_usage(path: Any, *args: Any, **kwargs: Any) -> Any:
        if path != work or args or kwargs:
            delegated_resources.append((path, args, kwargs))
            return original_disk_usage(path, *args, **kwargs)
        total, free = 128 * 1024**3, 96 * 1024**3
        if fault == "space-initial":
            free = 2 * len(entered) + 64 * 1024 + 512 * 1024**2 - 1
        elif fault == "space-drop" and resource_observations:
            free = 512 * 1024**2 - 1
        observed = usage_type(total=total, used=total - free, free=free)
        resource_observations.append(observed)
        return observed

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    unrelated = shutil.disk_usage(tmp_path)
    assert delegated_resources == [(tmp_path, (), {})]
    assert tuple(unrelated) == (unrelated.total, unrelated.used, unrelated.free)
    original_write = Path.write_text
    if fault == "source-drift-observation" or (scan_failure and fault.endswith("-observation")):

        def write(path: Path, data: str, *args: Any, **kwargs: Any) -> int:
            if path == work / (phase + "-observation.json"):
                raise OSError("synthetic secondary observation write")
            return original_write(path, data, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", write)
    loaded: list[Path] = []
    scanned: list[Path] = []

    class Native:
        def __init__(self, evidence: Path, deadline: float, cleanup: int) -> None:
            del deadline, cleanup
            self.evidence = evidence
            self.records: list[dict[str, Any]] = []
            if fault == "destination":
                (work / "docker-load.tar").write_bytes(b"pre-existing destination")

        def run(self, argv: list[str], name: str, env: dict[str, str], **kwargs: Any) -> bytes:
            expected_env = {"PATH", "HOME", "DOCKER_CONFIG", "LANG"}
            if phase == "native":
                expected_env |= {
                    "COMPOSE_PROFILES",
                    "PYTHONUNBUFFERED",
                    "ALERTMANAGER_NATIVE_SECONDS",
                    "ALERTMANAGER_NATIVE_CLEANUP_SECONDS",
                }
                assert env["COMPOSE_PROFILES"] == "" and env["PYTHONUNBUFFERED"] == "1"
                limits = docker_sources._alertmanager_limits()
                assert 0 < int(env["ALERTMANAGER_NATIVE_SECONDS"]) <= limits["NATIVE_SECONDS"]
                assert (
                    int(env["ALERTMANAGER_NATIVE_CLEANUP_SECONDS"])
                    == limits["NATIVE_CLEANUP_SECONDS"]
                )
            assert set(env) == expected_env
            assert not set(env) & {"GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "HTTPS_PROXY"}
            raw = b""
            failed_scan = name == "candidate-full-supported" and scan_fault == "scan-error"
            if name in ("candidate-load-same-OCI", "native-load-retained-OCI"):
                actual = Path(argv[argv.index("--input") + 1])
                loaded.append(actual)
                assert actual == work / "docker-load.tar" and actual != source
                assert actual.stat().st_mode & 0o777 == 0o600 and actual.stat().st_nlink == 1
                with tarfile.open(actual, "r:") as archive:
                    members = archive.getmembers()
                    assert [m.name for m in members] == [*canonical, "manifest.json"]
                    assert len([m for m in members if m.name == "manifest.json"]) == 1
                    for member in members:
                        assert member.isreg() and not member.pax_headers and not member.linkname
                        assert member.mode == 0o644 and member.uid == member.gid == 0
                        assert member.mtime == transport.SOURCE_DATE_EPOCH
                        value = archive.extractfile(member).read()
                        if member.name != "manifest.json":
                            assert value == canonical[member.name]
                        else:
                            assert json.loads(value) == [
                                {
                                    "Config": "blobs/sha256/" + graph["config"]["digest"][7:],
                                    "RepoTags": [],
                                    "Layers": layer_paths,
                                }
                            ]
                assert source.read_bytes() == original
            elif name in ("candidate-loaded-config", "native-retained-image"):
                raw = json.dumps(
                    {
                        "Id": (
                            "sha256:" + "8" * 64
                            if fault == "loaded-ID"
                            else graph["config"]["digest"]
                        ),
                        "Os": "linux",
                        "Architecture": "amd64",
                        "RootFS": {"Layers": [] if fault == "loaded-diffID" else graph["diff_ids"]},
                    }
                ).encode()
            elif name == "full-AM-native":
                raw = b"native_AM_full_candidate_controls=pass"
            elif "--output" in argv:
                assert (
                    kwargs["maximum_seconds"]
                    == docker_sources._alertmanager_limits()["SCAN_PROCESS_SECONDS"]
                )
                assert argv[argv.index("--scanners") + 1] == "vuln,secret"
                assert argv[argv.index("--pkg-types") + 1] == "os,library"
                assert argv[argv.index("--severity") + 1] == "UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL"
                assert argv[argv.index("--exit-code") + 1] == "0"
                assert all(
                    flag in argv
                    for flag in (
                        "--skip-db-update",
                        "--skip-java-db-update",
                        "--skip-vex-repo-update",
                        "--offline-scan",
                        "--skip-version-check",
                        "--disable-telemetry",
                        "--list-all-pkgs",
                        "--ignore-unfixed=false",
                    )
                )
                assert Path(argv[argv.index("--config") + 1]).read_bytes() == b"{}\n"
                assert Path(argv[argv.index("--ignorefile") + 1]).read_bytes() == b""
                if name == "candidate-known-vulnerable-control" and scan_fault.startswith(
                    "scan-before-"
                ):
                    mutate_scan_input()
                if name == "candidate-full-supported":
                    actual = Path(argv[argv.index("--input") + 1])
                    scanned.append(actual)
                    assert actual == layout and actual.is_dir() and actual != source
                    assert len(graph_checks) == 1
                    assert {
                        str(path.relative_to(actual)): path.read_bytes()
                        for path in actual.rglob("*")
                        if path.is_file()
                    } == canonical
                    assert not (actual / "manifest.json").exists()
                    assert source.read_bytes() == original
                    if scan_fault.startswith("scan-after-") or failed_scan:
                        mutate_scan_input()
                if not failed_scan:
                    Path(argv[argv.index("--output") + 1]).write_text('{"SchemaVersion":2}')
            stdout, stderr = self.evidence / (name + ".stdout"), self.evidence / (name + ".stderr")
            stdout.write_bytes(raw)
            stderr.write_bytes(b"synthetic actual scanner stderr" if failed_scan else b"")
            self.records.append(
                {
                    "argv": argv,
                    "environment": env,
                    "exit": 1 if failed_scan else 0,
                    "failure": "RuntimeError" if failed_scan else None,
                    "stdout": str(stdout),
                    "stderr": str(stderr),
                    "stdout_sha256": sha256(raw).hexdigest(),
                    "stderr_sha256": sha256(stderr.read_bytes()).hexdigest(),
                }
            )
            if failed_scan:
                raise scan_error
            return raw

    monkeypatch.setattr(transport, "Native", Native)
    monkeypatch.setattr(shutil, "which", lambda name: "/absolute/" + name)
    observation = tmp_path / "candidate-observation.json"
    observation.write_text("{}")

    def invoke() -> dict[str, Any]:
        return docker_sources._alertmanager_native_candidate(
            {"graph": graph}, observation, work, docker_sources._alertmanager_limits()
        )

    if fault is None:
        result = invoke()
        record = result["docker_load_transport"]
        assert record == json.loads((work / "evidence/docker-load-transport.json").read_text())
        assert record["source_OCI_sha256"] == sha256(original).hexdigest()
        assert record["load_archive_sha256"] == sha256(loaded[0].read_bytes()).hexdigest()
        assert len((work / "evidence/docker-load-transport.json").read_bytes()) < 32 * 1024
        assert scanned == ([layout] if phase == "security" else [])
        assert len(graph_checks) == (2 if phase == "security" else 0)
        assert len(inventory_calls) == (1 if phase == "security" else 0)
    else:
        expected_error = (
            RuntimeError if scan_fault == "scan-error" else transport.QualificationError
        )
        with pytest.raises((expected_error, tarfile.ReadError, FileNotFoundError)) as caught:
            invoke()
        if fault == "source-drift-observation" or (scan_failure and fault.endswith("-observation")):
            assert (
                "AM " + phase + " observation write also failed: OSError" in caught.value.__notes__
            )
        if fault in ("space-initial", "space-drop"):
            expected_guard = (
                "AM_load_transport_byte_space_bound"
                if fault == "space-initial"
                else "AM_load_transport_free_reserve"
            )
            assert isinstance(caught.value, transport.QualificationError)
            assert str(caught.value) == expected_guard
            assert len(resource_observations) == (1 if fault == "space-initial" else 2)
            if fault == "space-drop":
                assert resource_observations[0].free > 2 * len(entered) + 64 * 1024 + 512 * 1024**2
        assert len(loaded) == (1 if scan_failure or fault in ("loaded-ID", "loaded-diffID") else 0)
        assert scanned == (
            [layout] if scan_fault.startswith("scan-after-") or scan_fault == "scan-error" else []
        )
        if scan_failure:
            assert not inventory_calls
            report = (
                json.loads((work / "security-observation.json").read_text())
                if not fault.endswith("-observation")
                else None
            )
            assert report is None or "candidate" not in report
            assert len(graph_checks) == (2 if scan_fault.startswith("scan-after-") else 1)
            if scan_fault == "scan-error":
                assert caught.value is scan_error
                assert report is None or report["native_records"][-1]["exit"] == 1
                assert (work / "evidence/candidate-full-supported.stderr").read_bytes() == (
                    b"synthetic actual scanner stderr"
                )
            else:
                assert isinstance(caught.value, (transport.QualificationError, FileNotFoundError))
                if scan_fault.endswith("-source"):
                    assert str(caught.value) == (
                        "AM_final_candidate_scan_post_identity"
                        if scan_fault.startswith("scan-after-")
                        else "AM_final_candidate_scan_identity"
                    )
    assert load_calls == [source]
    assert len(unpack_calls) == (0 if fault in ("space-initial", "destination") else 1)
    assert resource_observations
    assert all(row.total == row.used + row.free and len(row) == 3 for row in resource_observations)
    if fault not in ("source-drift", "source-drift-observation") and not (
        scan_fault.endswith("-source") or scan_fault == "scan-error"
    ):
        assert source.read_bytes() == entered
    if fault is None or fault in ("space-initial", "space-drop"):
        retained = tmp_path / "retained"
        retained.mkdir()
        docker_sources._alertmanager_retain_execution(tmp_path, retained)
        if fault is None:
            assert (retained / (phase + "-evidence/docker-load-transport.json")).is_file()
        else:
            report = json.loads(
                (retained / (phase + "-" + phase + "-observation.json")).read_text()
            )
            assert report["native_records"] == []
            if phase == "native":
                assert report["failure"] == "QualificationError:" + expected_guard
        assert not list(retained.rglob("docker-load.tar"))


@pytest.fixture
def accepted_alertmanager_artifact_io(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, Any], dict[str, bytes], Any]:
    """Synthetic independent A drives the existing exact three-kind transport."""
    import base64
    from hashlib import sha1

    source = {
        path: (REPO_ROOT / path).read_bytes()
        for path in (
            *docker_sources._ALERT_Q_SOURCE_FILES,
            "tests/test_notify_premium_alias_checkpoint_failure.py",
        )
    }
    archive = b"synthetic accepted artifact transport"
    selected: dict[str, Any] = {
        "run": 101,
        "attempt": 1,
        "artifact": 102,
        "source": "a" * 40,
        "job": 103,
        "zip_sha256": sha256(archive).hexdigest(),
        "source_files": {path: sha256(raw).hexdigest() for path, raw in source.items()},
        "graph": {"manifest": {"digest": "sha256:" + "b" * 64}},
        "OCI_archive_sha256": "c" * 64,
    }
    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", selected)

    class API:
        calls: list[str]
        fault: str | None = None

        def __init__(self) -> None:
            self.calls = []

        def json(self, endpoint: str) -> dict[str, Any]:
            self.calls.append(endpoint)
            if endpoint.endswith("/PulsePlate"):
                return {"id": 1043311030, "full_name": "Katsiarynakavaleuskaya/PulsePlate"}
            if endpoint.endswith("/actions/workflows/cd.yml"):
                return {"id": 88, "path": ".github/workflows/cd.yml"}
            if endpoint.endswith("/actions/runs/101"):
                return {
                    "id": 101,
                    "head_sha": "a" * 40,
                    "head_branch": docker_sources._ALERT_RECEIVER_BRANCH,
                    "event": "workflow_dispatch",
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "success",
                    "workflow_id": 88,
                    "repository": {"id": 1043311030},
                    "head_repository": {"id": 1043311030},
                }
            if "/jobs?" in endpoint:
                return {"total_count": 1}
            if "/contents/" in endpoint:
                path = endpoint.split("/contents/", 1)[1].split("?ref=", 1)[0]
                raw = source[path] + (b"mixed unreviewed source" if self.fault == path else b"")
                return {
                    "path": path,
                    "type": "file",
                    "encoding": "base64",
                    "size": len(raw),
                    "content": base64.b64encode(raw).decode(),
                    "sha": sha1(
                        b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
                    ).hexdigest(),
                }
            assert endpoint.endswith("/actions/artifacts/102")
            return {
                "id": 102,
                "expired": False,
                "name": "alertmanager-candidate-101-1",
                "size_in_bytes": len(archive),
                "digest": "sha256:"
                + ("d" * 64 if self.fault == "archive" else sha256(archive).hexdigest()),
                "workflow_run": {
                    "id": 101,
                    "head_sha": "a" * 40,
                    "repository_id": 1043311030,
                    "head_repository_id": 1043311030,
                },
                "expires_at": "2099-01-01T00:00:00Z",
            }

        def pages(self, endpoint: str, key: str, count: int) -> list[dict[str, Any]]:
            assert (
                endpoint.endswith("/actions/runs/101/attempts/1/jobs")
                and key == "jobs"
                and count == 1
            )
            return [
                {
                    "id": 104 if self.fault == "job" else 103,
                    "name": "alertmanager-candidate-build",
                    "run_id": 101,
                    "head_sha": "a" * 40,
                    "status": "completed",
                    "conclusion": "success",
                }
            ]

        def raw(self, endpoint: str, maximum: int) -> bytes:
            self.calls.append(endpoint)
            assert endpoint.endswith("/actions/artifacts/102/zip") and maximum == 1024**3
            return archive

    return selected, source, API()


@pytest.mark.parametrize(
    "entry", ["consume", "publish", "execution", "authenticated", "snapshot", "payload"]
)
def test_alertmanager_unconfigured_accepted_producer_holds_before_credentials_or_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
) -> None:
    from argparse import Namespace
    from scripts.ci import prometheus_source_image as transport

    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", None)
    monkeypatch.setattr(
        transport,
        "GitHubRead",
        lambda *a, **k: pytest.fail("unconfigured producer acquired credentials"),
    )

    class API:
        def json(self, *args: Any) -> Any:
            pytest.fail("unconfigured producer reached authenticated API")

    args = Namespace(
        alertmanager_stage="publish",
        alertmanager_candidate_run=101,
        alertmanager_candidate_artifact=102,
        alertmanager_candidate_source="a" * 40,
    )
    with pytest.raises(RuntimeError, match="AM_accepted_producer_UNCONFIGURED_HOLD"):
        if entry == "consume":
            docker_sources._alertmanager_consume(args)
        elif entry == "publish":
            docker_sources._alertmanager_publish(args, API(), tmp_path, tmp_path, {}, {})
        elif entry == "execution":
            docker_sources._alertmanager_execution(args)
        elif entry == "authenticated":
            docker_sources._alertmanager_authenticated_inputs(
                API(), 101, 102, "a" * 40, tmp_path / "candidate.zip", kind="candidate"
            )
        elif entry == "snapshot":
            docker_sources._alertmanager_source_snapshot(API(), "a" * 40, accepted=True)
        else:
            docker_sources._alertmanager_candidate_payload(
                tmp_path / "absent.zip", tmp_path / "payload", {}, {}, tmp_path
            )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "early-ancestor",
        "run",
        "artifact",
        "job",
        "archive",
        "scripts/ci/fetch_docker_source_artifacts.py",
        ".github/workflows/cd.yml",
        "tests/test_notify_premium_alias_checkpoint_failure.py",
        "deploy/alertmanager/Containerfile",
    ],
)
def test_alertmanager_accepted_producer_identity_precedes_retained_download(
    tmp_path: Path,
    accepted_alertmanager_artifact_io: tuple[dict[str, Any], dict[str, bytes], Any],
    fault: str | None,
) -> None:
    selected, source, api = accepted_alertmanager_artifact_io
    api.fault = fault
    run, artifact, revision = selected["run"], selected["artifact"], selected["source"]
    if fault == "early-ancestor":
        revision = "1" * 40
    elif fault == "run":
        run += 1
    elif fault == "artifact":
        artifact += 1
    target = tmp_path / "candidate.zip"
    if fault is None:
        result = docker_sources._alertmanager_authenticated_inputs(
            api, run, artifact, revision, target, kind="candidate"
        )
        assert result["source_files"] == selected["source_files"]
        assert target.read_bytes() == b"synthetic accepted artifact transport"
        # A later consumer's local fetcher can differ; only immutable A source is compared.
        snapshot = docker_sources._alertmanager_source_snapshot(api, revision, accepted=True)
        assert snapshot == source
    else:
        expected = (
            "AM_accepted_producer_exact_selectors"
            if fault in {"early-ancestor", "run", "artifact"}
            else (
                "AM_qualification_successful_unique_job"
                if fault == "job"
                else (
                    "AM_qualification_artifact_identity"
                    if fault == "archive"
                    else "AM_qualification_source_bytes"
                )
            )
        )
        with pytest.raises(RuntimeError, match=expected):
            docker_sources._alertmanager_authenticated_inputs(
                api, run, artifact, revision, target, kind="candidate"
            )
        assert not target.exists() and not any(call.endswith("/zip") for call in api.calls)
        if fault in {"early-ancestor", "run", "artifact"}:
            assert api.calls == []


@pytest.mark.parametrize(
    "fault", ["native-source", "recipe", "subject", "graph", "archive", "consumer"]
)
def test_alertmanager_payload_independent_A_binds_source_recipe_and_full_subject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    accepted_alertmanager_artifact_io: tuple[dict[str, Any], dict[str, bytes], Any],
    fault: str,
) -> None:
    selected, source, api = accepted_alertmanager_artifact_io
    qualification = {
        "source": selected["source"],
        "zip_sha256": "1" * 64,
        "source_files": {
            key: selected["source_files"][key] for key in docker_sources._ALERT_Q_SOURCE_FILES
        },
    }
    upstream = {
        "qualification": qualification,
        "support_binding": {**qualification, "zip_sha256": "2" * 64},
        "support_report": {"scanner": {"DB": docker_sources._ALERT_DB}},
    }
    del api
    archive = tmp_path / "candidate.zip"
    archive.write_bytes(b"synthetic accepted artifact transport")
    if fault == "native-source":
        source = {**source, "tests/test_notify_premium_alias_checkpoint_failure.py": b"mixed"}
    elif fault == "recipe":
        source = {**source, "deploy/alertmanager/Containerfile": b"mixed"}
    elif fault == "archive":
        archive.write_bytes(b"mixed archive")
    elif fault == "consumer":
        # Current consumer identity is deliberately independent of the selected A bytes.
        monkeypatch.setattr(docker_sources, "REPO_ROOT", tmp_path / "later-consumer")
    from scripts.ci import prometheus_source_image as transport

    if fault in {"subject", "graph"}:
        import zipfile

        observed = {
            "source": "f" * 40 if fault == "subject" else selected["source"],
            "graph": (
                {"manifest": {"digest": "sha256:" + "e" * 64}}
                if fault == "graph"
                else selected["graph"]
            ),
            "OCI_archive_sha256": selected["OCI_archive_sha256"],
        }
        raw = json.dumps(observed).encode()
        footer = {
            "files": [
                {
                    "path": "candidate-observation.json",
                    "size": len(raw),
                    "mode": 0o600,
                    "sha256": sha256(raw).hexdigest(),
                }
            ],
            "directories": [],
            "inventory_carrier_exception": "Exactly artifact-payload-members.json is bound by external artifact bytes; its own hash is not recursively embedded.",
        }
        with zipfile.ZipFile(archive, "w") as retained:
            for name, value in (
                ("candidate-observation.json", raw),
                ("artifact-payload-members.json", json.dumps(footer).encode()),
            ):
                info = zipfile.ZipInfo(name)
                info.external_attr = (stat.S_IFREG | 0o600) << 16
                retained.writestr(info, value)
        selected["zip_sha256"] = sha256(archive.read_bytes()).hexdigest()
        with pytest.raises(RuntimeError, match="AM_accepted_producer_subject_graph"):
            docker_sources._alertmanager_candidate_payload(
                archive, tmp_path / "payload", source, {}, tmp_path, **upstream
            )
        assert not (tmp_path / "payload").exists()
        return

    def members(path: Path) -> dict[str, bytes]:
        assert path == archive
        raise RuntimeError("reached-original-payload-reader")

    monkeypatch.setattr(transport, "_zip_members", members)
    expected = (
        "AM_accepted_producer_source_bytes"
        if fault in {"native-source", "recipe"}
        else (
            "AM_accepted_producer_archive_bytes"
            if fault == "archive"
            else "reached-original-payload-reader"
        )
    )
    with pytest.raises(RuntimeError, match=expected):
        docker_sources._alertmanager_candidate_payload(
            archive, tmp_path / "payload", source, {}, tmp_path, **upstream
        )
    assert not (tmp_path / "payload").exists()


def test_alertmanager_complete_preparation_preempts_blocking_pure_work_and_restores_timer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import signal
    import time
    from argparse import Namespace

    previous = signal.getsignal(signal.SIGALRM)
    monkeypatch.setattr(docker_sources, "_alertmanager_controller_binding", lambda args: None)

    def blocked(args: Namespace, limits: dict[str, int], deadline: float) -> None:
        del args, limits, deadline
        time.sleep(3)
        pytest.fail("pure work escaped total preparation clock")

    monkeypatch.setattr(docker_sources, "_alertmanager_prepare_candidate_body", blocked)
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="complete preparation600"):
        docker_sources._alertmanager_prepare_candidate(Namespace(), {"PREP_SECONDS": 1})
    assert time.monotonic() - started < 2
    assert signal.getsignal(signal.SIGALRM) is previous
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_alertmanager_preparation_cleanup_keeps_actual_primary_without_refilling_main() -> None:
    import time
    import signal

    class API:
        def close(self) -> None:
            raise OSError("synthetic owned cleanup failure")

    primary = ValueError("synthetic original failure")
    try:
        try:
            raise primary
        except ValueError:
            with pytest.raises(ValueError, match="synthetic original failure") as observed:
                docker_sources._alertmanager_close_preparation_api(API(), time.monotonic() - 1)
        assert observed.value is primary
        assert "AM API cleanup also failed: OSError" in primary.__notes__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


@pytest.fixture
def alertmanager_published_reader_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Provide native publication metadata and registry bytes through existing transport seams."""
    from argparse import Namespace
    from scripts.ci import prometheus_source_image as transport
    import time

    for key in (
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GHCR_READ_TOKEN",
        "DOCKER_CONFIG",
        "DOCKER_AUTH_CONFIG",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "Katsiarynakavaleuskaya")
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-reader")
    monkeypatch.setenv("ALERTMANAGER_CONTROLLER_SOURCE", "c" * 40)
    graph = deepcopy(docker_sources._ALERT_ACCEPTED_CANDIDATE["graph"])
    manifest = json.dumps(
        {"schemaVersion": 2, "config": graph["config"], "layers": graph["layers"]}
    ).encode()
    graph["manifest"]["digest"] = "sha256:" + sha256(manifest).hexdigest()
    graph["manifest"]["size"] = len(manifest)
    accepted = deepcopy(docker_sources._ALERT_ACCEPTED_CANDIDATE)
    accepted["graph"] = graph
    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", accepted)
    monkeypatch.setattr(docker_sources, "_ALERT_HISTORICAL_C10", deepcopy(accepted))
    repo = {"id": 1043311030}
    data: dict[str, Any] = {
        "calls": [],
        "merge": "a" * 40,
        "pr": {
            "number": 2497,
            "merged": True,
            "state": "closed",
            "merge_commit_sha": "a" * 40,
            "base": {"repo": repo, "ref": "main"},
            "head": {"repo": repo, "ref": docker_sources._ALERT_RECEIVER_BRANCH},
        },
        "workflow": {"id": 55, "path": ".github/workflows/cd.yml"},
        "runs": [
            {
                "id": 66,
                "run_attempt": 1,
                "head_sha": "a" * 40,
                "head_branch": "main",
                "event": "workflow_dispatch",
                "workflow_id": 55,
                "repository": repo,
                "head_repository": repo,
                "status": "completed",
                "conclusion": "success",
            }
        ],
        "jobs": [
            {
                "id": 77,
                "run_id": 66,
                "head_sha": "a" * 40,
                "name": "alertmanager-main-publication",
                "status": "completed",
                "conclusion": "success",
            }
        ],
        "manifest": manifest,
        "count_drift": False,
    }
    (tmp_path / "github-read-evidence").mkdir()
    private = tmp_path / "private"
    for name in ("home", "config", "cache", "tmp"):
        (private / name).mkdir(parents=True)

    class API:
        def __init__(self) -> None:
            self.private = private
            self.gh = "/synthetic/gh"

        def json(self, endpoint: str) -> Any:
            data["calls"].append(endpoint)
            if endpoint.endswith("/pulls/2497"):
                return data["pr"]
            if endpoint.endswith("/actions/workflows/cd.yml"):
                return data["workflow"]
            if "/actions/workflows/cd.yml/runs?" in endpoint:
                assert "branch=main&event=workflow_dispatch&status=success" in endpoint
                assert "head_sha=" not in endpoint
                page = int(endpoint.rsplit("page=", 1)[1])
                return {
                    "total_count": data.get("count", len(data["runs"])),
                    "workflow_runs": data["runs"][(page - 1) * 100 : page * 100],
                }
            if "/actions/runs/66/attempts/1/jobs?" in endpoint:
                return {
                    "total_count": len(data["jobs"])
                    + int(data["count_drift"] and data["calls"].count(endpoint) > 1),
                    "jobs": data["jobs"],
                }
            pytest.fail(
                "ordinary route requested an unrecognized API or expired archive: " + endpoint
            )

        def pages(self, endpoint: str, key: str, count: int) -> Any:
            return transport.GitHubRead.pages(self, endpoint, key, count)

        def _capture(self, argv: list[str], maximum: int, **kwargs: Any) -> bytes:
            del maximum
            data["calls"].append(argv)
            if "login" in argv:
                assert kwargs["input_data"] == b"synthetic-reader\n"
                credential = Path(argv[2]) / "config.json"
                credential.write_bytes(b"{}")
                credential.chmod(0o600)
                return b"Login Succeeded\n"
            if "imagetools" in argv:
                return data["manifest"]
            if "pull" in argv:
                return b"saved immutable image pulled\n"
            if "inspect" in argv:
                return json.dumps(
                    {
                        "Id": graph["config"]["digest"],
                        "Os": "linux",
                        "Architecture": "amd64",
                        "RepoDigests": [
                            "ghcr.io/katsiarynakavaleuskaya/pulseplate@"
                            + graph["manifest"]["digest"]
                        ],
                        "RootFS": {"Layers": graph["diff_ids"]},
                    }
                ).encode()
            pytest.fail("unrecognized registry action")

    class Native:
        def __init__(self, *args: Any) -> None:
            self.records: list[dict[str, Any]] = []

        def run(self, argv: list[str], *args: Any, cwd: Path, **kwargs: Any) -> bytes:
            assert cwd == tmp_path and "--no-replace-objects" in argv
            if argv[-2:] == ["rev-parse", "--is-shallow-repository"]:
                return b"true\n" if data.get("shallow") else b"false\n"
            assert argv[-4:-2] == ["merge-base", "--is-ancestor"]
            assert tuple(argv[-2:]) in {
                (data["merge"], data["runs"][0]["head_sha"]),
                (data["runs"][0]["head_sha"], data["route"]["base"]),
            }
            if data.get("ancestry-failure"):
                raise RuntimeError("synthetic native ancestry failure")
            data["calls"].append("native merged selection ancestry")
            return b""

    sources = {name: b"synthetic reviewed source" for name in docker_sources._ALERT_SELECTION_FILES}
    sources["scripts/ci/fetch_docker_source_artifacts.py"] = Path(
        docker_sources.__file__
    ).read_bytes()
    monkeypatch.setattr(transport, "Native", Native)
    monkeypatch.setattr(shutil, "which", lambda name: "/synthetic/" + name)

    def regular(root: Path, revision: str, work: Path, deadline: float) -> dict[str, bytes]:
        del work, deadline
        assert root == tmp_path
        historical = data.get("historical", sources)
        if revision == data["route"]["base"]:
            return sources
        if revision == data["merge"]:
            return historical
        return data.get("published", historical)

    monkeypatch.setattr(docker_sources, "_alertmanager_regular_sources", regular)

    def templates(api: Any, source: str, *, controller_templates: bool) -> dict[str, bytes]:
        assert source == "c" * 40 and controller_templates is True
        data["calls"].append("read separate C templates")
        return {path: sources[path] for path in docker_sources._ALERT_SELECTION_FILES[:5]}

    monkeypatch.setattr(docker_sources, "_alertmanager_source_snapshot", templates)
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_render_source_contract",
        lambda *args, **kwargs: data["calls"].append("validated BASE first"),
    )
    data["versions"] = [
        {
            "id": 1,
            "name": graph["manifest"]["digest"],
            "metadata": {
                "container": {"tags": ["alertmanager-0.34.1-" + graph["manifest"]["digest"][7:]]}
            },
        }
    ]
    monkeypatch.setattr(
        transport, "existing_public_package", lambda api: ({"exact": "synthetic"}, data["versions"])
    )
    data.update(
        {
            "api": API(),
            "sources": sources,
            "output": tmp_path,
            "deadline": time.monotonic() + 60,
            "args": Namespace(material_root=tmp_path),
            "route": {"base": "b" * 40},
        }
    )
    return data


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "unmerged",
        "wrong-PR",
        "merge",
        "workflow",
        "branch",
        "event",
        "attempt",
        "repository",
        "head-repository",
        "workflow-ID",
        "run-head",
        "pending",
        "run-failure",
        "job-name",
        "job-run",
        "job-head",
        "job-pending",
        "job-failure",
        "duplicate-job",
        "count-drift",
        "missing-tag",
        "tag-conflict",
        "source-drift",
        "manifest-drift",
    ],
)
def test_alertmanager_published_route_requires_native_predecessor_before_login(
    alertmanager_published_reader_io: dict[str, Any],
    fault: str | None,
) -> None:
    data = alertmanager_published_reader_io
    if fault == "unmerged":
        data["pr"]["merged"] = False
    elif fault == "wrong-PR":
        data["pr"]["number"] = 2477
    elif fault == "merge":
        data["pr"]["merge_commit_sha"] = "unknown"
    elif fault == "workflow":
        data["workflow"]["path"] = ".github/workflows/build.yml"
    elif fault in {
        "branch",
        "event",
        "attempt",
        "workflow-ID",
        "run-head",
        "pending",
        "run-failure",
    }:
        key, value = {
            "branch": ("head_branch", "other"),
            "event": ("event", "push"),
            "attempt": ("run_attempt", True),
            "workflow-ID": ("workflow_id", 99),
            "run-head": ("head_sha", "unknown"),
            "pending": ("status", "queued"),
            "run-failure": ("conclusion", "failure"),
        }[fault]
        data["runs"][0][key] = value
    elif fault in {"repository", "head-repository"}:
        data["runs"][0][fault.replace("-", "_")] = {"id": 1}
    elif fault in {"job-name", "job-run", "job-head", "job-pending", "job-failure"}:
        key, value = {
            "job-name": ("name", "prometheus-publish"),
            "job-run": ("run_id", 99),
            "job-head": ("head_sha", "c" * 40),
            "job-pending": ("status", "in_progress"),
            "job-failure": ("conclusion", "failure"),
        }[fault]
        data["jobs"][0][key] = value
    elif fault == "duplicate-job":
        data["jobs"].append({**data["jobs"][0], "id": 78})
    elif fault == "count-drift":
        data["count_drift"] = True
    elif fault == "missing-tag":
        data["versions"].clear()
    elif fault == "tag-conflict":
        data["versions"][0]["name"] = "sha256:" + "c" * 64
    elif fault == "source-drift":
        data["sources"] = {**data["sources"], "deploy/alertmanager/alertmanager.yml": b"drift"}
    elif fault == "manifest-drift":
        data["manifest"] += b"\n"

    def invoke() -> dict[str, Any]:
        return docker_sources._alertmanager_pull_published(
            data["api"],
            data["args"],
            data["route"],
            data["sources"],
            data["output"],
            data["deadline"],
        )

    if fault is None:
        result = invoke()
        assert result["registry_login"] is True
        assert result["publication_predecessor"]["job"]["id"] == 77
        assert result["docker_load_transport"] is None
        assert not any(
            "/artifacts/" in entry or "/zip" in entry
            for entry in data["calls"]
            if isinstance(entry, str)
        )
    else:
        with pytest.raises(RuntimeError):
            invoke()
        login = [entry for entry in data["calls"] if isinstance(entry, list) and "login" in entry]
        assert bool(login) is (fault == "manifest-drift")
    assert data["calls"][:2] == ["read separate C templates", "validated BASE first"]


def test_alertmanager_preparation_shorter_parent_preempts_before_own_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nested preparation may not postpone an already armed caller deadline."""
    import signal
    import time
    from argparse import Namespace

    previous = signal.getsignal(signal.SIGALRM)
    original_timer = signal.getitimer(signal.ITIMER_REAL)
    monkeypatch.setattr(docker_sources, "_alertmanager_controller_binding", lambda args: None)

    def blocked(*args: Any) -> None:
        time.sleep(3)
        pytest.fail("shorter parent clock was replaced")

    monkeypatch.setattr(docker_sources, "_alertmanager_prepare_candidate_body", blocked)
    started = time.monotonic()
    signal.setitimer(signal.ITIMER_REAL, 0.2)
    try:
        with pytest.raises(TimeoutError, match="complete preparation600"):
            docker_sources._alertmanager_prepare_candidate(Namespace(), {"PREP_SECONDS": 600})
        assert time.monotonic() - started < 1
        assert signal.getsignal(signal.SIGALRM) is previous
    finally:
        signal.setitimer(signal.ITIMER_REAL, *original_timer)


def _alertmanager_current_scan_report() -> dict[str, Any]:
    """Complete synthetic scanner carrier using the separately retained immutable inventory oracle."""
    oracle = docker_sources._ALERT_CURRENT_SCAN_ORACLE
    os_packages = []
    for row in oracle["expected_OS"]["packages"]:
        os_packages.append(
            {
                **dict(zip(("ID", "Name", "Version", "Arch", "SrcName", "SrcVersion"), row[2:8])),
                "Identifier": {"PURL": row[8]},
            }
        )
    return {
        "SchemaVersion": 2,
        "ArtifactType": "container_image",
        "Metadata": {
            "ImageID": oracle["subject"]["config"],
            "OS": deepcopy(oracle["expected_OS"]["OS"]),
        },
        "Results": [
            {
                "Target": "current immutable S",
                "Class": "os-pkgs",
                "Type": "debian",
                "Packages": os_packages,
            },
            *[
                {
                    "Target": "usr/bin/" + binary,
                    "Class": "lang-pkgs",
                    "Type": "gobinary",
                    "Packages": [
                        {"Name": name, "Version": version} for name, version in modules.items()
                    ],
                }
                for binary, modules in oracle["expected_modules"].items()
            ],
        ],
    }


@pytest.mark.parametrize("target", (0, 1, 2))
@pytest.mark.parametrize(
    "fault",
    (
        None,
        "remove",
        "alter",
        "add",
        "duplicate",
        "missing-target",
        "wrong-subject",
        "secret",
        "new-HIGH",
        "target-CVE-LOW",
        "mixed-proof",
        "mixed-binary",
    ),
)
def test_alertmanager_current_scan_requires_complete_accepted_OS_and_both_native_module_sets(
    target: int,
    fault: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _alertmanager_current_scan_report()
    assert [len(row["Packages"]) for row in report["Results"]] == [6, 117, 112]
    row = report["Results"][target]
    if fault == "remove":
        row["Packages"].pop()
    elif fault == "alter":
        row["Packages"][0]["Version"] = "unreviewed"
    elif fault == "add":
        row["Packages"].append({**row["Packages"][0], "Name": "unreviewed", "ID": "unreviewed@1"})
    elif fault == "duplicate":
        row["Packages"].append(deepcopy(row["Packages"][0]))
    elif fault == "missing-target":
        report["Results"].pop(target)
    elif fault == "wrong-subject":
        report["Metadata"]["ImageID"] = "sha256:" + "0" * 64
    elif fault == "secret":
        row["Secrets"] = [{"RuleID": "synthetic", "Severity": "CRITICAL"}]
    elif fault in ("new-HIGH", "target-CVE-LOW"):
        row["Vulnerabilities"] = [
            {
                "VulnerabilityID": "CVE-new" if fault == "new-HIGH" else "CVE-2026-97031",
                "Severity": "HIGH" if fault == "new-HIGH" else "LOW",
                "PkgName": "synthetic",
                "InstalledVersion": "1",
            }
        ]
    elif fault == "mixed-binary":
        changed = deepcopy(docker_sources._ALERT_ACCEPTED_CANDIDATE)
        changed["graph"]["files"]["usr/bin/amtool"] = "0" * 64
        monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", changed)
    args = (
        report,
        docker_sources._ALERT_CURRENT_SCAN_ORACLE["subject"]["config"],
        None,
        {} if fault == "mixed-proof" else None,
    )
    if fault is None:
        assert len(docker_sources._alertmanager_candidate_inventory(*args)["packages"]) == 235
    else:
        with pytest.raises(RuntimeError, match="AM_"):
            docker_sources._alertmanager_candidate_inventory(*args)


@pytest.mark.parametrize("current_epoch", [False, True])
@pytest.mark.parametrize("severity", ["UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"])
@pytest.mark.parametrize("target", [0, 1, 2])
@pytest.mark.parametrize("identifier", ["CVE-2026-111943", "CVE-synthetic-unrelated"])
def test_alertmanager_target_CVE_postcondition_is_severity_independent_in_current_epoch(
    current_epoch: bool, severity: str, target: int, identifier: str
) -> None:
    """The finite target-ID predicate is independent of the existing generic severity gate."""
    report = _alertmanager_current_scan_report()
    finding = {
        "VulnerabilityID": identifier,
        "Severity": severity,
        "PkgName": "synthetic",
        "InstalledVersion": "1",
    }
    report["Results"][target]["Vulnerabilities"] = [finding]
    arguments = (report, docker_sources._ALERT_CURRENT_SCAN_ORACLE["subject"]["config"], None, None)
    if severity in ("HIGH", "CRITICAL"):
        with pytest.raises(RuntimeError, match="^AM_new_blocking_support_finding_HOLD$"):
            docker_sources._alertmanager_candidate_inventory(*arguments, current=current_epoch)
    elif current_epoch and identifier == "CVE-2026-111943":
        with pytest.raises(RuntimeError, match="^AM_current_Go_CVE_still_present$"):
            docker_sources._alertmanager_candidate_inventory(*arguments, current=True)
    else:
        observed = docker_sources._alertmanager_candidate_inventory(
            *arguments, current=current_epoch
        )
        assert observed["findings"] == [finding]


@pytest.mark.parametrize(
    "kind,job",
    [
        ("ci-lint", 190),
        ("shared-pr", 170),
        ("shared-main", 290),
        ("standalone", 80),
        ("third-main", 110),
    ],
)
@pytest.mark.parametrize(
    "fault",
    (
        None,
        "too-small",
        "too-large",
        "malformed",
        "unknown-route",
        "native-override",
        "reservation-drift",
    ),
)
def test_alertmanager_caller_budgets_reject_unadmitted_effective_overrides(
    alertmanager_proposal_environment: None,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    job: int,
    fault: str | None,
) -> None:
    for key, value in {
        "ALERTMANAGER_CALLER_KIND": kind,
        "ALERTMANAGER_JOB_TIMEOUT_MINUTES": str(job),
        "ALERTMANAGER_GENERIC_NATIVE_MINUTES": "40",
        "ALERTMANAGER_LINT_CHECK_MINUTES": "60",
        "PROMETHEUS_PUBLICATION_WAIT_SECONDS": "10800",
        "PROMETHEUS_CONSUME_SECONDS": "900",
        "PROMETHEUS_CLEANUP_SECONDS": "120",
        "PROMETHEUS_SECURITY_RESERVE_SECONDS": "2400",
    }.items():
        monkeypatch.setenv(key, value)
    if fault == "too-small":
        monkeypatch.setenv("ALERTMANAGER_JOB_TIMEOUT_MINUTES", str(job - 1))
    elif fault == "too-large":
        monkeypatch.setenv("ALERTMANAGER_JOB_TIMEOUT_MINUTES", "361")
    elif fault == "malformed":
        monkeypatch.setenv("ALERTMANAGER_JOB_TIMEOUT_MINUTES", " 170 ")
    elif fault == "unknown-route":
        monkeypatch.setenv("ALERTMANAGER_CALLER_KIND", "caller-claims-budget")
    elif fault == "native-override":
        monkeypatch.setenv("ALERTMANAGER_GENERIC_NATIVE_MINUTES", "39")
    elif fault == "reservation-drift":
        monkeypatch.setenv("PROMETHEUS_PUBLICATION_WAIT_SECONDS", "10799")
    rejects = (
        fault in {"too-small", "too-large", "malformed", "unknown-route"}
        or (fault == "native-override" and kind in {"ci-lint", "third-main"})
        or (fault == "reservation-drift" and kind == "shared-main")
    )
    if rejects:
        with pytest.raises(RuntimeError, match="AM_"):
            docker_sources._alertmanager_limits(caller=True)
    else:
        assert docker_sources._alertmanager_limits(caller=True)["PREP_SECONDS"] == 600


@pytest.mark.parametrize(
    "class_name,type_name", [("lang-pkgs", "npm"), ("unknown", "gobinary"), ("os-pkgs", "unknown")]
)
def test_alertmanager_current_inventory_rejects_extra_unclassified_package_carrier(
    class_name: str,
    type_name: str,
) -> None:
    report = _alertmanager_current_scan_report()
    report["Results"].append(
        {
            "Target": "unexpected/package-lock.json",
            "Class": class_name,
            "Type": type_name,
            "Packages": [{"Name": "synthetic-unknown-payload", "Version": "1.0.0"}],
        }
    )
    with pytest.raises(
        RuntimeError, match="AM_(unclassified_package_bearing_target|candidate_OS_classifier)"
    ):
        docker_sources._alertmanager_candidate_inventory(
            report, report["Metadata"]["ImageID"], None, None
        )


@pytest.mark.parametrize(
    "route",
    (
        "own-pr",
        "ordinary-pr",
        "first-main-squash",
        "first-main-merge",
        "later-main",
        "tag",
        "schedule",
    ),
)
@pytest.mark.parametrize(
    "fault",
    (
        None,
        "event-repository",
        "event-head-repository",
        "current-main",
        "unknown-before",
        "wrong-parents",
        "PR-graph",
        "receiver-number",
    ),
)
def test_alertmanager_three_positive_routes_bind_native_event_and_keep_first_main_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    route: str,
    fault: str | None,
) -> None:
    from argparse import Namespace
    from scripts.ci import prometheus_source_image as transport
    import time

    repo = {"id": 1043311030, "full_name": "Katsiarynakavaleuskaya/PulsePlate"}
    before, head, merge = "a" * 40, "b" * 40, "c" * 40
    is_pr = route.endswith("pr")
    first = route.startswith("first-main")
    source = head if is_pr else merge
    number = 2497 if route != "ordinary-pr" else 2500
    pr = {
        "number": number,
        "state": "open" if is_pr else "closed",
        "merged": not is_pr,
        "merge_commit_sha": merge if first else "d" * 40,
        "commits": 2,
        "head": {
            "repo": repo,
            "ref": docker_sources._ALERT_RECEIVER_BRANCH if number == 2497 else "ordinary",
            "sha": head,
        },
        "base": {"repo": repo, "ref": "main", "sha": before if is_pr else merge},
    }
    event = {
        "repository": repo,
        "number": number,
        "pull_request": deepcopy(pr),
        "ref": "refs/heads/main",
        "deleted": False,
        "after": merge,
        "before": before,
    }
    name = "pull_request" if is_pr else "schedule" if route == "schedule" else "push"
    ref = (
        "refs/pull/2497/merge"
        if is_pr
        else "refs/tags/v1.0.0" if route == "tag" else "refs/heads/main"
    )
    if route == "tag":
        event["ref"] = ref
    for key, value in {
        "GITHUB_EVENT_NAME": name,
        "GITHUB_REF": ref,
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_SHA": source,
    }.items():
        monkeypatch.setenv(key, value)
    current = before if is_pr else merge
    if fault == "event-repository":
        event["repository"] = {"id": 1, "full_name": "elsewhere/project"}
    if fault == "event-head-repository":
        event["pull_request"]["head"]["repo"] = {"id": 1}
    if fault == "current-main":
        current = "f" * 40
    if fault == "unknown-before":
        event["before"] = "unknown"
    expected_parent = [merge, before, head] if route == "first-main-merge" else [merge, before]
    if fault == "wrong-parents":
        expected_parent = [merge, "f" * 40]
    if fault == "receiver-number":
        pr["number"] = 2494
    calls = []

    class API:
        def json(self, endpoint: str) -> Any:
            calls.append(endpoint)
            if endpoint.endswith("/git/ref/heads/main"):
                return {"object": {"sha": current}}
            if endpoint.endswith("/pulls/" + str(number)):
                return pr
            if endpoint.endswith("/pulls/2494"):
                return {
                    "number": 2494,
                    "commits": 2,
                    "head": {
                        "repo": repo,
                        "ref": docker_sources._ALERT_Q_BRANCH,
                        "sha": docker_sources._ALERT_DONOR_SOURCE,
                    },
                    "base": {"repo": repo, "ref": "main"},
                }
            pytest.fail(
                "route consulted registry/history instead of its positive native case:" + endpoint
            )

        def pages(self, endpoint: str, key: Any, count: int) -> Any:
            assert endpoint.endswith("/commits") and count == 2
            accepted_source = docker_sources._ALERT_ACCEPTED_CANDIDATE["source"]
            return [
                {"sha": accepted_source, "parents": []},
                {
                    "sha": docker_sources._ALERT_DONOR_SOURCE,
                    "parents": [] if fault == "PR-graph" else [{"sha": accepted_source}],
                },
            ]

    class Native:
        def __init__(self, *args: Any) -> None:
            pass

        def run(self, argv: list[str], *args: Any, cwd: Path, **kwargs: Any) -> bytes:
            assert cwd == tmp_path
            assert argv[-5:] == ["rev-list", "--parents", "-n", "1", merge]
            return (" ".join(expected_parent) + "\n").encode()

    monkeypatch.setattr(transport, "Native", Native)
    monkeypatch.setattr(shutil, "which", lambda name: "/synthetic/" + name)
    reject = (
        fault in {"event-repository", "current-main"}
        or (fault == "event-head-repository" and is_pr)
        or (fault in {"unknown-before", "wrong-parents"} and first)
        or (fault == "PR-graph" and (first or route == "own-pr"))
        or (fault == "receiver-number" and (is_pr or first))
    )

    def invoke() -> dict[str, Any]:
        return docker_sources._alertmanager_reader_route(
            API(),
            Namespace(source_sha=source, material_root=tmp_path),
            event,
            tmp_path,
            time.monotonic() + 60,
        )

    if reject:
        with pytest.raises(RuntimeError):
            invoke()
    else:
        observed = invoke()
        assert observed["mode"] == (
            "initial_own_PR_retained"
            if route == "own-pr"
            else (
                "ordinary_published_PR"
                if is_pr
                else "genuine_first_main_retained" if first else "ordinary_published_main"
            )
        )
        if first:
            assert observed["base"] == before and pr["base"]["sha"] == merge
    assert all("/packages/" not in endpoint and "/artifacts/" not in endpoint for endpoint in calls)


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "unset-C",
        "wrong-C",
        "commit",
        "tree-record",
        "truncated",
        "duplicate",
        "missing",
        "directory-mode",
        "leaf-mode",
        "leaf-type",
        "leaf-sha",
        "contents-sha",
        "contents-size",
        "contents-type",
        "mixed-case",
    ],
)
def test_alertmanager_controller_templates_use_native_regular_git_objects(
    monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    """A source ref alone cannot authorize symlinks or incomplete native Git tree metadata."""
    import base64
    from hashlib import sha1

    revision = "c" * 40
    monkeypatch.setenv("ALERTMANAGER_CONTROLLER_SOURCE", revision)
    raw = {
        path: (REPO_ROOT / path).read_bytes() for path in docker_sources._ALERT_SELECTION_FILES[:5]
    }
    directory_ids = {"": "1" * 40, "deploy": "2" * 40, "deploy/alertmanager": "3" * 40}
    blobs = {
        path: sha1(
            b"blob " + str(len(value)).encode() + b"\0" + value, usedforsecurity=False
        ).hexdigest()
        for path, value in raw.items()
    }
    trees: dict[str, Any] = {
        sha: {"sha": sha, "truncated": False, "tree": []} for sha in directory_ids.values()
    }
    for path, sha in directory_ids.items():
        if path:
            parent, _, leaf = path.rpartition("/")
            trees[directory_ids[parent]]["tree"].append(
                {"path": leaf, "mode": "040000", "type": "tree", "sha": sha}
            )
    for path, sha in blobs.items():
        parent, _, leaf = path.rpartition("/")
        trees[directory_ids[parent]]["tree"].append(
            {"path": leaf, "mode": "100644", "type": "blob", "sha": sha}
        )
    first = trees["2" * 40]["tree"][1]
    assert first["path"] == "docker-compose.staging.yaml"
    if fault == "unset-C":
        monkeypatch.delenv("ALERTMANAGER_CONTROLLER_SOURCE")
    elif fault == "wrong-C":
        monkeypatch.setenv("ALERTMANAGER_CONTROLLER_SOURCE", "d" * 40)
    elif fault == "truncated":
        trees["2" * 40]["truncated"] = True
    elif fault == "duplicate":
        trees["2" * 40]["tree"].append(deepcopy(first))
    elif fault == "missing":
        trees["2" * 40]["tree"].remove(first)
    elif fault == "directory-mode":
        trees["1" * 40]["tree"][0]["mode"] = "100644"
    elif fault == "leaf-mode":
        first["mode"] = "120000"
    elif fault == "leaf-type":
        first["type"] = "commit"
    elif fault == "leaf-sha":
        first["sha"] = "e" * 40

    class API:
        def json(self, endpoint: str) -> Any:
            if "/git/commits/" in endpoint:
                return {
                    "sha": "a" * 40 if fault == "commit" else revision,
                    "tree": [] if fault == "tree-record" else {"sha": "1" * 40},
                }
            if "/git/trees/" in endpoint:
                return trees[endpoint.rsplit("/", 1)[-1]]
            assert "/contents/" in endpoint and endpoint.endswith("?ref=" + revision)
            path = endpoint.split("/contents/", 1)[1].split("?", 1)[0]
            return {
                "path": path,
                "type": "symlink" if fault == "contents-type" else "file",
                "encoding": "base64",
                "size": len(raw[path]) + int(fault == "contents-size"),
                "content": base64.b64encode(raw[path]).decode(),
                "sha": "a" * 40 if fault == "contents-sha" else blobs[path],
            }

    if fault is None:
        assert (
            docker_sources._alertmanager_source_snapshot(API(), revision, controller_templates=True)
            == raw
        )
    else:
        diagnostic = {
            "unset-C": "AM_designated_controller_data_source",
            "wrong-C": "AM_designated_controller_data_source",
            "commit": "AM_controller_data_commit_tree",
            "tree-record": "AM_controller_data_commit_tree",
            "truncated": "AM_controller_data_complete_distinct_tree",
            "duplicate": "AM_controller_data_complete_distinct_tree",
            "missing": "AM_controller_data_regular_git_path",
            "directory-mode": "AM_controller_data_regular_git_path",
            "leaf-mode": "AM_controller_data_regular_git_path",
            "leaf-type": "AM_controller_data_regular_git_path",
            "leaf-sha": "AM_controller_data_leaf_cross_binding",
            "contents-sha": "AM_producer_raw_Git_blob",
            "contents-size": "AM_producer_raw_Git_blob",
            "contents-type": "AM_producer_finite_source_blob",
            "mixed-case": "AM_source_cases_are_disjoint",
        }[fault]
        with pytest.raises(RuntimeError, match=diagnostic):
            docker_sources._alertmanager_source_snapshot(
                API(), revision, controller_templates=True, accepted=fault == "mixed-case"
            )


@pytest.mark.parametrize("case", ["accepted", "old"])
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "include",
        "extends",
        "external-env",
        "config",
        "policy",
        "missing-template",
        "second-subject",
    ],
)
def test_alertmanager_render_binds_reviewed_data_before_native_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str, fault: str | None
) -> None:
    """Exercise actual reviewed template bytes, the old transition and required synthetic input."""
    import time
    from scripts.ci import prometheus_source_image as transport
    from tests.test_deploy_contract_scripts import (
        FAKE_PROMETHEUS_COMPOSE_JSON,
        _historical_AM_template,
        _staging_compose_fixture_json,
    )

    templates = {
        path: (
            _historical_AM_template(REPO_ROOT / path)
            if path in docker_sources._ALERT_SELECTION_FILES[:3]
            else (REPO_ROOT / path).read_bytes()
        )
        for path in docker_sources._ALERT_SELECTION_FILES[:5]
    }
    sources = {
        **templates,
        docker_sources._ALERT_SELECTION_FILES[-1]: Path(docker_sources.__file__).read_bytes(),
    }
    if case == "old":
        for path in docker_sources._ALERT_SELECTION_FILES[:3]:
            sources[path] = sources[path].replace(
                docker_sources._alertmanager_contract_subject()[0].encode(),
                docker_sources._ALERT_OLD_RUNTIME_REF.encode(),
            )
        # Exact retired policy fixture remains independent of current Git HEAD.
        sources["deploy/alertmanager/trivy-ignore.yaml"] = (
            b"vulnerabilities:\n"
            b"  - id: CVE-2026-84445\n"
            b"    purls:\n"
            b"      - pkg:golang/google.golang.org/grpc@v1.83.1\n"
            b"    expired_at: 2026-10-21\n"
            b"    statement: >-\n"
            b"      Seven-day exception for the exact official Alertmanager v0.34.1 linux/amd64\n"
            b"      image. The verified release list on 2026-10-14 has no newer release.\n"
            b"      Component fixes exist; qualification of a replacement covering all admitted\n"
            b"      findings is carryover to the next substantive PR. See\n"
            b"      docs/security/CVE-2026-84445-alertmanager.md. Remove after all admitted\n"
            b"      findings are remediated and the replacement passes native/security acceptance.\n"
            b"  - id: CVE-2026-78669\n"
            b"    purls:\n"
            b"      - pkg:golang/golang.org/x/net@v0.58.0\n"
            b"      - pkg:golang/stdlib@v1.26.8\n"
            b"    expired_at: 2026-10-21\n"
            b"    statement: >-\n"
            b"      Seven-day exception for the exact official Alertmanager v0.34.1 linux/amd64\n"
            b"      image. The verified release list on 2026-10-14 has no newer release.\n"
            b"      Component fixes exist; qualification of a replacement covering all admitted\n"
            b"      findings is carryover to the next substantive PR. See\n"
            b"      docs/security/CVE-2026-84445-alertmanager.md. Remove after all admitted\n"
            b"      findings are remediated and the replacement passes native/security acceptance.\n"
            b"  - id: CVE-2026-78667\n"
            b"    purls:\n"
            b"      - pkg:golang/stdlib@v1.26.8\n"
            b"    expired_at: 2026-10-21\n"
            b"    statement: >-\n"
            b"      Seven-day exception for the exact official Alertmanager v0.34.1 linux/amd64\n"
            b"      image. The verified release list on 2026-10-14 has no newer release.\n"
            b"      Component fixes exist; qualification of a replacement covering all admitted\n"
            b"      findings is carryover to the next substantive PR. See\n"
            b"      docs/security/CVE-2026-84445-alertmanager.md. Remove after all admitted\n"
            b"      findings are remediated and the replacement passes native/security acceptance.\n"
            b"  - id: CVE-2026-97031\n"
            b"    purls:\n"
            b"      - pkg:golang/stdlib@v1.26.8\n"
            b"    expired_at: 2026-10-21\n"
            b"    statement: >-\n"
            b"      Seven-day exception for the exact official Alertmanager v0.34.1 linux/amd64\n"
            b"      image. The verified release list on 2026-10-14 has no newer release.\n"
            b"      Component fixes exist; qualification of a replacement covering all admitted\n"
            b"      findings is carryover to the next substantive PR. See\n"
            b"      docs/security/CVE-2026-84445-alertmanager.md. Remove after all admitted\n"
            b"      findings are remediated and the replacement passes native/security acceptance.\n"
        )
    if fault in ("include", "extends", "external-env"):
        injected = {
            "include": b"\ninclude: ../outside.yaml\n",
            "extends": b"\nextends: ../outside.yaml\n",
            "external-env": b"\nenv_file: ../private.env\n",
        }[fault]
        sources[docker_sources._ALERT_SELECTION_FILES[0]] += injected
    elif fault == "config":
        sources["deploy/alertmanager/alertmanager.yml"] += b"# changed\n"
    elif fault == "policy":
        sources["deploy/alertmanager/trivy-ignore.yaml"] += b"\n"
    elif fault == "missing-template":
        templates.pop(docker_sources._ALERT_SELECTION_FILES[0])
    elif fault == "second-subject":
        templates[
            docker_sources._ALERT_SELECTION_FILES[0]
        ] += docker_sources._alertmanager_contract_subject()[0].encode()
    calls: list[str] = []

    class Native:
        def __init__(self, *args: Any) -> None:
            assert fault is None, "unreviewed source reached native setup"
            self.records: list[dict[str, Any]] = []

        def run(
            self, argv: list[str], label: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            assert argv[:3] == ["/synthetic/docker", "compose", "--env-file"]
            assert argv[4] == "--project-directory" and argv[6] == "-f"
            assert argv[8:] == ["--profile", "*", "config", "--format", "json"]
            assert (
                Path(argv[3]).read_bytes() == b""
                and Path(env["STAGING_ENV_FILE"]).read_bytes() == b""
            )
            compose = Path(argv[7])
            assert Path(argv[5]) == cwd == compose.parent
            assert kwargs["maximum_seconds"] == 8 and kwargs["output_bound"] == 1048576
            if compose.name.endswith("selfhosted.yaml"):
                assert "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" in compose.read_text()
                assert env["POSTGRES_PASSWORD"] == "synthetic"
            assert set(env) == {
                "PATH",
                "HOME",
                "COMPOSE_PROFILES",
                "STAGING_IMAGE_REF",
                "STAGING_CADDY_IMAGE_REF",
                "PROMETHEUS_RUNTIME_REF",
                "IMAGE_REF",
                "STAGING_ENV_FILE",
                "POSTGRES_USER",
                "POSTGRES_DB",
                "POSTGRES_PASSWORD",
                "DATABASE_URL",
                "STAGING_DOMAIN",
                "PRODUCTION_DOMAIN",
                "STAGING_FALLBACK_DOMAIN",
            }
            model = json.loads(
                _staging_compose_fixture_json(compose.parent)
                if "staging" in compose.name
                else FAKE_PROMETHEUS_COMPOSE_JSON
            )
            model["services"]["alertmanager"]["image"] = (
                docker_sources._ALERT_OLD_RUNTIME_REF
                if case == "old"
                else docker_sources._alertmanager_contract_subject()[0]
            )
            model["services"]["alertmanager"]["volumes"] = [
                {
                    "type": "bind",
                    "source": str(compose.parent / "alertmanager/alertmanager.yml"),
                    "target": "/etc/alertmanager/alertmanager.yml",
                    "read_only": True,
                }
            ]
            model["secrets"]["alertmanager_smtp_key"]["file"] = str(
                compose.parent / "secrets/alertmanager_smtp_key"
            )
            calls.append(label)
            return json.dumps(model).encode()

    monkeypatch.setattr(transport, "Native", Native)
    monkeypatch.setattr(shutil, "which", lambda command: "/synthetic/" + command)
    work = tmp_path / "native"
    if fault:
        with pytest.raises(RuntimeError, match="AM_"):
            docker_sources._alertmanager_render_source_contract(
                sources,
                work,
                time.monotonic() + 30,
                expected_case=case,
                controller_templates=templates,
            )
        assert not work.exists() and not calls
    else:
        docker_sources._alertmanager_render_source_contract(
            sources, work, time.monotonic() + 30, expected_case=case, controller_templates=templates
        )
        assert calls == ["BASE-all-profile-0", "BASE-all-profile-1", "BASE-all-profile-2"]


@pytest.mark.parametrize("drift", [False, True])
def test_alertmanager_initial_pr_binds_current_data_before_acquisition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: bool
) -> None:
    """Initial retained acquisition cannot authorize changed data after C designation."""
    from argparse import Namespace
    from scripts.ci import prometheus_source_image as transport
    import time

    accepted = docker_sources._alertmanager_accepted_producer()
    templates = {
        path: (REPO_ROOT / path).read_bytes() for path in docker_sources._ALERT_SELECTION_FILES[:5]
    }
    material = {
        **templates,
        docker_sources._ALERT_SELECTION_FILES[-1]: Path(docker_sources.__file__).read_bytes(),
    }
    if drift:
        material[docker_sources._ALERT_SELECTION_FILES[0]] += b"\ninclude: ../external.yaml\n"
    event = tmp_path / "event.json"
    event.write_text("{}")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_REPOSITORY", "Katsiarynakavaleuskaya/PulsePlate")
    monkeypatch.setenv("ALERTMANAGER_CONTROLLER_SOURCE", "c" * 40)
    calls: list[str] = []

    class API:
        def __init__(self, private: Path, *args: Any) -> None:
            self.private = private
            private.mkdir()

    def snapshot(api: Any, source: str, *, controller_templates: bool) -> dict[str, bytes]:
        assert source == "c" * 40 and controller_templates is True
        calls.append("templates")
        return templates

    def acquisition(*args: Any, **kwargs: Any) -> Any:
        calls.append("acquisition")
        raise RuntimeError("synthetic acquisition reached")

    monkeypatch.setattr(transport, "GitHubRead", API)
    monkeypatch.setattr(
        docker_sources, "_alertmanager_reader_route", lambda *a: {"mode": "own_PR_retained"}
    )
    monkeypatch.setattr(docker_sources, "_alertmanager_bind_material", lambda *a: material)
    monkeypatch.setattr(docker_sources, "_alertmanager_source_snapshot", snapshot)
    monkeypatch.setattr(docker_sources, "_alertmanager_authenticated_inputs", acquisition)
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_close_preparation_api",
        lambda api, deadline: api.private.rmdir(),
    )
    args = Namespace(
        output_dir=tmp_path / "output",
        material_root=tmp_path,
        source_sha="d" * 40,
        alertmanager_candidate_run=accepted["run"],
        alertmanager_candidate_artifact=accepted["artifact"],
        alertmanager_candidate_source=accepted["source"],
        alertmanager_qualification_run=1,
        alertmanager_qualification_artifact=2,
        alertmanager_qualification_source="e" * 40,
    )
    with pytest.raises(
        RuntimeError,
        match="AM_reviewed_controller_data_closure" if drift else "synthetic acquisition reached",
    ):
        docker_sources._alertmanager_prepare_candidate_body(
            args, {"CLEANUP_SECONDS": 45}, time.monotonic() + 30
        )
    assert calls == (["templates"] if drift else ["templates", "acquisition"])
    assert not (args.output_dir / "private").exists()


def test_alertmanager_actual_preparation_observation_is_retained_by_every_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bind the actual producer's written filename to each existing workflow artifact selector."""
    from argparse import Namespace

    selected = docker_sources._alertmanager_accepted_producer()
    output = tmp_path / "consumer"
    output.mkdir()
    payload = output / "candidate"
    payload.mkdir()
    prepared = {
        "image_id": selected["graph"]["config"]["digest"],
        "config_sha256": sha256(
            (REPO_ROOT / "deploy/alertmanager/alertmanager.yml").read_bytes()
        ).hexdigest(),
    }
    monkeypatch.setattr(docker_sources, "_alertmanager_limits", lambda **kwargs: {})
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_prepare_candidate",
        lambda *args: ({"graph": selected["graph"]}, payload, output, prepared),
    )
    monkeypatch.setattr(
        docker_sources,
        "_alertmanager_native_candidate",
        lambda *args, **kwargs: pytest.fail("prepare-only executed full native fixtures"),
    )
    args = Namespace(
        alertmanager_candidate_run=selected["run"],
        alertmanager_candidate_artifact=selected["artifact"],
        alertmanager_candidate_source=selected["source"],
        alertmanager_prepare_only=True,
        source_sha="a" * 40,
        material_root=REPO_ROOT,
    )
    docker_sources._alertmanager_consume(args)
    written = [path for path in output.iterdir() if path.is_file()]
    assert len(written) == 1
    observation = json.loads(written[0].read_text())
    assert observation["compiler_starts"] == 0 and observation["registry_login"] is False
    assert observation["original_producer"] == selected and "native" not in observation
    assert dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines()) == {
        "image_id": prepared["image_id"],
        "config_sha256": prepared["config_sha256"],
        "observation": str(payload / "candidate-observation.json"),
    }
    consumers = (
        ("ci.yml", "lint"),
        ("cd.yml", "alertmanager-retained-candidate"),
        ("cd.yml", "prometheus-image-security-pr"),
        ("cd.yml", "prometheus-image-security-trusted"),
        ("cd.yml", "obs2a-checkpoint-native"),
    )
    prepare_name = "Prepare exact AM subject before material execution"
    discovered = {
        (workflow, name)
        for workflow in ("ci.yml", "cd.yml")
        for name, job in _load_workflow(WORKFLOWS_DIR / workflow)["jobs"].items()
        if any(step.get("name") == prepare_name for step in job.get("steps", []))
    }
    assert discovered == set(consumers)
    for workflow, job_name in consumers:
        job = _load_workflow(WORKFLOWS_DIR / workflow)["jobs"][job_name]
        assert job["runs-on"] == "ubuntu-24.04", (workflow, job_name)
        metadata_name = (
            "Admit retained PR candidate or published immutable subject"
            if job_name.startswith("prometheus-image-security-")
            else prepare_name
        )
        prepare = _step_by_name(job, metadata_name)["run"]
        version = "docker version --format 'client={{json .Client.Version}} server={{json .Server.Version}}'"
        store = (
            "docker info --format 'driver={{json .Driver}} driver_status={{json .DriverStatus}} "
            "os={{json .OSType}} arch={{json .Architecture}}'"
        )
        assert version in prepare and store in prepare
        assert prepare.index(version) < prepare.index(store) < prepare.index("python3 ")
        steps = job["steps"]
        uploads = [
            step["with"]["path"]
            for step in steps
            if str(step.get("uses", "")).startswith("actions/upload-artifact@")
        ]
        matches = [paths for paths in uploads if "/" + written[0].name in paths]
        assert len(matches) == 1, (workflow, job_name, written[0].name)
        assert "/github-read-evidence/" in matches[0] and "/preparation/evidence/" in matches[0]
        assert "/candidate.zip" not in matches[0] and "/private/" not in matches[0]


@pytest.mark.parametrize("later_change", [None, "fetcher", "non-AM-compose"])
def test_alertmanager_descendant_witness_keeps_current_consumer_material_independent(
    alertmanager_published_reader_io: dict[str, Any], later_change: str | None
) -> None:
    """Historical Q/P closure cannot freeze later reviewed BASE/HEAD/controller bytes."""
    data = alertmanager_published_reader_io
    data["runs"][0]["head_sha"] = data["jobs"][0]["head_sha"] = "d" * 40
    data["historical"] = dict(data["sources"])
    if later_change == "fetcher":
        data["historical"]["scripts/ci/fetch_docker_source_artifacts.py"] = b"historical F"
    elif later_change == "non-AM-compose":
        data["historical"]["deploy/docker-compose.production.yaml"] = b"earlier backend data"
    result = docker_sources._alertmanager_pull_published(
        data["api"], data["args"], data["route"], data["sources"], data["output"], data["deadline"]
    )
    assert result["registry_login"] is True
    assert result["publication_predecessor"]["merge"] == "a" * 40
    assert result["publication_predecessor"]["run"]["head_sha"] == "d" * 40
    assert not any(
        "/artifacts/" in call or "/zip" in call for call in data["calls"] if isinstance(call, str)
    )


@pytest.mark.parametrize("member", docker_sources._ALERT_SELECTION_FILES)
def test_alertmanager_predecessor_rejects_each_historical_source_drift_before_login(
    alertmanager_published_reader_io: dict[str, Any], member: str
) -> None:
    data = alertmanager_published_reader_io
    data["runs"][0]["head_sha"] = data["jobs"][0]["head_sha"] = "d" * 40
    data["published"] = {**data["sources"], member: b"unreviewed historical change"}
    with pytest.raises(RuntimeError, match="AM_publication_historical_six_source_drift"):
        docker_sources._alertmanager_pull_published(
            data["api"],
            data["args"],
            data["route"],
            data["sources"],
            data["output"],
            data["deadline"],
        )
    assert not any(isinstance(call, list) and "login" in call for call in data["calls"])


@pytest.mark.parametrize(
    "case",
    [
        "zero",
        "999",
        "1000",
        "bool",
        "string",
        "negative",
        "duplicate",
        "malformed",
        "shallow",
        "ancestry",
    ],
)
def test_alertmanager_predecessor_keeps_bounded_complete_query_and_native_history(
    alertmanager_published_reader_io: dict[str, Any], case: str
) -> None:
    data = alertmanager_published_reader_io
    if case == "zero":
        data["runs"] = []
    elif case == "999":
        data["runs"] += [{**data["runs"][0], "id": n + 100, "event": "push"} for n in range(998)]
    elif case in {"1000", "bool", "string", "negative"}:
        data["count"] = {"1000": 1000, "bool": True, "string": "1", "negative": -1}[case]
    elif case == "duplicate":
        data["runs"] *= 2
    elif case == "malformed":
        data["runs"] = [None]
    elif case == "shallow":
        data["shallow"] = True
    else:
        data["ancestry-failure"] = True

    def invoke() -> dict[str, Any]:
        return docker_sources._alertmanager_publication_predecessor(
            data["api"],
            data["args"].material_root,
            data["route"]["base"],
            data["output"] / "witness",
            data["deadline"],
        )

    if case == "999":
        assert invoke()["run"]["id"] == 66
    else:
        with pytest.raises(RuntimeError):
            invoke()
    assert not any(isinstance(call, list) and "login" in call for call in data["calls"])


@pytest.fixture
def alertmanager_temporary_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """Real local Git objects with synthetic identity; no shared refs, hooks or network."""
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path.resolve()))
    git = shutil.which("git")
    assert git is not None
    root = tmp_path / "repository"
    root.mkdir()
    for key in tuple(os.environ):
        if (
            key.startswith(("GH", "GITHUB", "GIT_", "DEVPI_", "DOCKER_"))
            or key.upper().endswith("PROXY")
            or key in {"NETRC", "PYTHONPATH", "PYTHONHOME"}
        ):
            monkeypatch.delenv(key, raising=False)
    environment = {
        "PATH": os.defpath,
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }

    def command(*argv: str) -> str:
        result = subprocess.run(
            [
                git,
                "--no-replace-objects",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=AM synthetic fixture",
                "-c",
                "user.email=am-fixture@example.invalid",
                "-C",
                str(root),
                *argv,
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip()

    command("init", "--initial-branch=main")
    for name in docker_sources._ALERT_SELECTION_FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPO_ROOT / name).read_bytes())
    command("add", ".")
    command("commit", "-m", "Synthetic merged AM material")
    merged = command("rev-parse", "HEAD")
    (root / "unrelated.txt").write_text("synthetic unrelated change\n")
    command("add", ".")
    command("commit", "-m", "Synthetic descendant publisher")
    publisher = command("rev-parse", "HEAD")
    return {"root": root, "command": command, "Q": merged, "P": publisher, "work": tmp_path}


@pytest.mark.parametrize(
    "fault", [None, "wrong-controller", "wrong-controller-data", "changed-worktree-F"]
)
def test_alertmanager_actual_controller_and_regular_source_interface_uses_required_cwd(
    alertmanager_temporary_history: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    fault: str | None,
) -> None:
    import time
    from argparse import Namespace

    data = alertmanager_temporary_history
    root = data["root"]
    monkeypatch.setattr(docker_sources, "REPO_ROOT", root)
    monkeypatch.setenv(
        "ALERTMANAGER_CONTROLLER_SOURCE", "f" * 40 if fault == "wrong-controller" else data["P"]
    )
    args = Namespace(
        material_root=root,
        alertmanager_controller_source=(
            "f" * 40 if fault in {"wrong-controller", "wrong-controller-data"} else data["P"]
        ),
    )
    if fault == "wrong-controller-data":
        with pytest.raises(RuntimeError, match="AM_controller_UNCONFIGURED_HOLD"):
            docker_sources._alertmanager_controller_binding(args)
        return
    if fault == "wrong-controller":
        with pytest.raises(RuntimeError, match="AM_controller_actual_checkout"):
            docker_sources._alertmanager_controller_binding(args)
        return
    docker_sources._alertmanager_controller_binding(args)
    if fault == "changed-worktree-F":
        (root / "scripts/ci/fetch_docker_source_artifacts.py").write_bytes(b"changed worktree F")
        with pytest.raises(RuntimeError, match="AM_actual_material_not_admitted_HEAD"):
            docker_sources._alertmanager_bind_material(
                root, data["P"], data["work"] / "material", time.monotonic() + 30
            )
    else:
        sources = docker_sources._alertmanager_bind_material(
            root, data["P"], data["work"] / "material", time.monotonic() + 30
        )
        assert set(sources) == set(docker_sources._ALERT_SELECTION_FILES)
        assert sources == docker_sources._alertmanager_regular_sources(
            root, data["Q"], data["work"] / "original", time.monotonic() + 30
        )
        observation = json.loads((data["work"] / "original/native-observation.json").read_text())
        assert len(observation["native_records"]) == 12
        assert all(
            row["exit"] == 0 and row["cwd"] == str(root) for row in observation["native_records"]
        )


@pytest.mark.parametrize("member", docker_sources._ALERT_SELECTION_FILES)
@pytest.mark.parametrize("mode", ["executable", "symlink", "missing"])
def test_alertmanager_actual_historical_regular_sources_reject_nonregular_members(
    alertmanager_temporary_history: dict[str, Any], member: str, mode: str
) -> None:
    import time

    data = alertmanager_temporary_history
    path = data["root"] / member
    if mode == "executable":
        path.chmod(0o755)
    else:
        path.unlink()
        if mode == "symlink":
            path.symlink_to("/absent-synthetic-input")
    data["command"]("add", "--all")
    data["command"]("commit", "-m", "Synthetic invalid historical member")
    changed = data["command"]("rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="AM_selection_regular100644_blob"):
        docker_sources._alertmanager_regular_sources(
            data["root"], changed, data["work"] / "read", time.monotonic() + 30
        )


@pytest.mark.parametrize(
    "case",
    [
        "equal",
        "descendant",
        "later-consumer",
        "unrelated",
        "shallow",
        "missing-Q",
        "missing-P",
        "missing-B",
        "publisher-after-base",
        "historical-content",
    ],
)
def test_alertmanager_actual_native_predecessor_binds_Q_P_B_without_archive_or_registry(
    alertmanager_temporary_history: dict[str, Any], case: str
) -> None:
    import time
    from scripts.ci import prometheus_source_image as transport

    data = alertmanager_temporary_history
    merged = data["Q"]
    publisher = merged if case == "equal" else data["P"]
    revision = data["P"]
    if case == "later-consumer":
        (data["root"] / "scripts/ci/fetch_docker_source_artifacts.py").write_bytes(
            b"later reviewed F"
        )
        (data["root"] / "deploy/docker-compose.production.yaml").write_text(
            "later reviewed backend material\n"
        )
        data["command"]("add", ".")
        data["command"]("commit", "-m", "Synthetic later reviewed consumer")
        revision = data["command"]("rev-parse", "HEAD")
    elif case == "unrelated":
        data["command"]("checkout", "--orphan", "unrelated")
        data["command"]("commit", "-m", "Synthetic unrelated publisher")
        publisher = revision = data["command"]("rev-parse", "HEAD")
    elif case == "shallow":
        (data["root"] / ".git/shallow").write_text(merged + "\n")
    elif case == "missing-Q":
        merged = "f" * 40
    elif case == "missing-P":
        publisher = "f" * 40
    elif case == "missing-B":
        revision = "f" * 40
    elif case == "publisher-after-base":
        revision = merged
    elif case == "historical-content":
        (data["root"] / "deploy/alertmanager/trivy-ignore.yaml").write_text(
            "changed historical policy\n"
        )
        data["command"]("add", ".")
        data["command"]("commit", "-m", "Synthetic incompatible publisher")
        publisher = revision = data["command"]("rev-parse", "HEAD")
    repo = {"id": 1043311030}
    run = {
        "id": 66,
        "head_sha": publisher,
        "head_branch": "main",
        "event": "workflow_dispatch",
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
        "workflow_id": 55,
        "repository": repo,
        "head_repository": repo,
    }
    job = {
        "id": 77,
        "run_id": 66,
        "head_sha": publisher,
        "name": "alertmanager-main-publication",
        "status": "completed",
        "conclusion": "success",
    }
    calls: list[str] = []

    class API:
        def json(self, endpoint: str) -> dict[str, Any]:
            calls.append(endpoint)
            if endpoint.endswith("/pulls/2497"):
                return {
                    "number": 2497,
                    "merged": True,
                    "state": "closed",
                    "merge_commit_sha": merged,
                    "base": {"ref": "main", "repo": repo},
                    "head": {"ref": docker_sources._ALERT_RECEIVER_BRANCH, "repo": repo},
                }
            if endpoint.endswith("/actions/workflows/cd.yml"):
                return {"id": 55, "path": ".github/workflows/cd.yml"}
            if "/actions/workflows/cd.yml/runs?" in endpoint:
                assert "branch=main&event=workflow_dispatch&status=success" in endpoint
                return {"total_count": 1, "workflow_runs": [run]}
            assert "/actions/runs/66/attempts/1/jobs?" in endpoint
            return {"total_count": 1, "jobs": [job]}

        def pages(self, endpoint: str, key: str, count: int) -> list[dict[str, Any]]:
            return transport.GitHubRead.pages(self, endpoint, key, count)

    def invoke() -> dict[str, Any]:
        return docker_sources._alertmanager_publication_predecessor(
            API(), data["root"], revision, data["work"] / "predecessor", time.monotonic() + 60
        )

    if case in {"equal", "descendant", "later-consumer"}:
        result = invoke()
        assert (
            result["merge"] == merged
            and result["run"]["head_sha"] == result["job"]["head_sha"] == publisher
        )
    else:
        with pytest.raises(RuntimeError):
            invoke()
    assert all(
        "/artifacts/" not in call and "/zip" not in call and "packages" not in call
        for call in calls
    )


@pytest.mark.parametrize("owner", ["regular", "predecessor", "render"])
@pytest.mark.parametrize("primary_failure", [False, True])
def test_alertmanager_proof_retention_failure_preserves_native_primary_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, owner: str, primary_failure: bool
) -> None:
    """Diagnostic retention cannot turn a failed native proof into success or erase its cause."""
    import time
    from scripts.ci import prometheus_source_image as transport
    from tests.test_deploy_contract_scripts import (
        _historical_AM_template,
        _staging_compose_fixture_json,
    )

    for key in tuple(os.environ):
        if key.startswith(("GH", "GITHUB", "DEVPI_", "DOCKER_")) or key.upper().endswith("PROXY"):
            monkeypatch.delenv(key, raising=False)
    sources = {
        name: (
            _historical_AM_template(REPO_ROOT / name)
            if name in docker_sources._ALERT_SELECTION_FILES[:3]
            else (REPO_ROOT / name).read_bytes()
        )
        for name in docker_sources._ALERT_SELECTION_FILES
    }
    work = tmp_path / "proof"
    expected_error = RuntimeError("synthetic original native failure")
    real_write = Path.write_text

    def write(path: Path, *args: Any, **kwargs: Any) -> int:
        if path.name == "native-observation.json":
            raise OSError("synthetic retained write failure")
        return real_write(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write)
    monkeypatch.setattr(shutil, "which", lambda name: "/synthetic/" + name)

    class Native:
        def __init__(self, *args: Any) -> None:
            self.records: list[dict[str, Any]] = []

        def run(
            self, argv: list[str], name: str, env: dict[str, str], *, cwd: Path, **kwargs: Any
        ) -> bytes:
            self.records.append(
                {"argv": argv, "cwd": str(cwd), "exit": 1 if primary_failure else 0}
            )
            if primary_failure:
                raise expected_error
            if "--is-shallow-repository" in argv:
                return b"false\n"
            if "ls-tree" in argv:
                member = argv[-1]
                raw = sources[member]
                import hashlib

                digest = hashlib.sha1(
                    b"blob " + str(len(raw)).encode() + b"\0" + raw, usedforsecurity=False
                ).hexdigest()
                return b"100644 blob " + digest.encode() + b"\t" + member.encode() + b"\0"
            if "cat-file" in argv:
                return sources[argv[-1].split(":", 1)[1]]
            assert owner == "render"
            compose = Path(argv[argv.index("-f") + 1])
            model = json.loads(_staging_compose_fixture_json(compose.parent))
            if "staging" not in compose.name:
                model["services"]["prometheus"]["environment"][
                    "PULSEPLATE_ENVIRONMENT"
                ] = "production"
                model["services"]["app"]["networks"] = {"web": {}, "observability": {}}
            return json.dumps(model).encode()

    monkeypatch.setattr(transport, "Native", Native)

    class API:
        def json(self, endpoint: str) -> dict[str, Any]:
            if endpoint.endswith("/pulls/2497"):
                repo = {"id": 1043311030}
                return {
                    "number": 2497,
                    "merged": True,
                    "state": "closed",
                    "merge_commit_sha": "a" * 40,
                    "base": {"ref": "main", "repo": repo},
                    "head": {"ref": docker_sources._ALERT_RECEIVER_BRANCH, "repo": repo},
                }
            if endpoint.endswith("/cd.yml"):
                return {"id": 55, "path": ".github/workflows/cd.yml"}
            return {"total_count": 0, "workflow_runs": []}

        def pages(self, *args: Any) -> list[dict[str, Any]]:
            return []

    if owner == "predecessor" and not primary_failure:
        # No witness is itself the primary admission failure; retention must preserve it.
        match = "AM_positive_publication_predecessor_missing"
        expected_type: type[BaseException] = RuntimeError
    else:
        match = (
            "synthetic original native failure"
            if primary_failure
            else "synthetic retained write failure"
        )
        expected_type = RuntimeError if primary_failure else OSError
    with pytest.raises(expected_type, match=match) as raised:
        if owner == "regular":
            docker_sources._alertmanager_regular_sources(
                tmp_path, "a" * 40, work, time.monotonic() + 30
            )
        elif owner == "predecessor":
            docker_sources._alertmanager_publication_predecessor(
                API(), tmp_path, "b" * 40, work, time.monotonic() + 30
            )
        else:
            docker_sources._alertmanager_render_source_contract(
                sources,
                work,
                time.monotonic() + 30,
                expected_case="accepted",
                controller_templates={
                    p: sources[p] for p in docker_sources._ALERT_SELECTION_FILES[:5]
                },
            )
    if primary_failure:
        assert raised.value is expected_error
    if primary_failure or owner == "predecessor":
        assert "AM native proof retention failed: OSError" in raised.value.__notes__


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "advanced-head",
        "wrong-pr",
        "wrong-repo",
        "wrong-ref",
        "bool-count",
        "missing-source",
        "missing-donor",
        "duplicate",
        "wrong-parent",
        "unreachable-donor",
        "malformed-parent",
        "count-drift",
    ],
)
def test_alertmanager_original_lineage_is_independent_of_receiver_history(
    fault: str | None,
) -> None:
    """Only the original complete PR graph can establish C10-to-donor ancestry."""
    from copy import deepcopy

    source = docker_sources._alertmanager_accepted_producer()["source"]
    donor = docker_sources._ALERT_DONOR_SOURCE
    head = "e" * 40 if fault in {"advanced-head", "unreachable-donor"} else donor
    rows = [{"sha": source, "parents": []}, {"sha": donor, "parents": [{"sha": source}]}]
    if head != donor:
        rows.append(
            {"sha": head, "parents": [{"sha": source if fault == "unreachable-donor" else donor}]}
        )
    pr = {
        "number": 2497 if fault == "wrong-pr" else 2494,
        "commits": len(rows),
        "head": {"sha": head, "ref": docker_sources._ALERT_Q_BRANCH, "repo": {"id": 1043311030}},
        "base": {"ref": "main", "repo": {"id": 1043311030}},
    }
    if fault == "wrong-repo":
        pr["head"]["repo"]["id"] = 1
    elif fault == "wrong-ref":
        pr["head"]["ref"] = docker_sources._ALERT_RECEIVER_BRANCH
    elif fault == "bool-count":
        pr["commits"] = True
    elif fault == "missing-source":
        rows[0]["sha"] = "f" * 40
    elif fault == "missing-donor":
        rows[1]["sha"] = "f" * 40
    elif fault == "duplicate":
        rows[1] = deepcopy(rows[0])
    elif fault == "wrong-parent":
        rows[1]["parents"] = []
    elif fault == "malformed-parent":
        rows[1]["parents"] = [{"sha": "short"}]
    elif fault == "count-drift":
        pr["commits"] += 1

    class API:
        def json(self, endpoint: str) -> dict[str, Any]:
            assert endpoint == "/repos/Katsiarynakavaleuskaya/PulsePlate/pulls/2494"
            return deepcopy(pr)

        def pages(self, endpoint: str, key: object, count: int) -> list[dict[str, Any]]:
            assert endpoint.endswith("/pulls/2494/commits") and key is None
            assert count == pr["commits"]
            return deepcopy(rows)

    if fault in (None, "advanced-head"):
        docker_sources._alertmanager_original_lineage(API())
    else:
        with pytest.raises(RuntimeError, match="AM_original_"):
            docker_sources._alertmanager_original_lineage(API())


@pytest.mark.parametrize(
    "fault", [None, "missing-current", "duplicate", "unreachable", "foreign", "ref"]
)
def test_alertmanager_new_producer_has_own_receiver_ancestry_without_relabeling_C10(
    monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    historical = docker_sources._ALERT_HISTORICAL_C10["source"]
    donor = docker_sources._ALERT_DONOR_SOURCE
    selected = deepcopy(docker_sources._ALERT_HISTORICAL_C10)
    selected["source"] = "a" * 40
    selected["source_files"][
        "deploy/alertmanager/Containerfile"
    ] = docker_sources._ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", selected)
    prior_rows = [
        {"sha": historical, "parents": []},
        {"sha": donor, "parents": [{"sha": historical}]},
    ]
    current_rows = [
        {"sha": selected["source"], "parents": []},
        {"sha": "b" * 40, "parents": [{"sha": selected["source"]}]},
    ]
    if fault == "missing-current":
        current_rows[0]["sha"] = "c" * 40
    elif fault == "duplicate":
        current_rows[1] = deepcopy(current_rows[0])
    elif fault == "unreachable":
        current_rows[1]["parents"] = []
    called: list[int] = []

    class API:
        def json(self, endpoint: str) -> dict[str, Any]:
            number = int(endpoint.rsplit("/", 1)[1])
            called.append(number)
            assert number in (2494, 2497)
            return {
                "number": number,
                "commits": 2,
                "head": {
                    "sha": donor if number == 2494 else "b" * 40,
                    "ref": (
                        docker_sources._ALERT_Q_BRANCH
                        if number == 2494 or fault == "ref"
                        else docker_sources._ALERT_RECEIVER_BRANCH
                    ),
                    "repo": {"id": 1 if number == 2497 and fault == "foreign" else 1043311030},
                },
                "base": {"ref": "main", "repo": {"id": 1043311030}},
            }

        def pages(self, endpoint: str, key: object, count: int) -> list[dict[str, Any]]:
            assert key is None and count == 2
            return deepcopy(prior_rows if "/2494/" in endpoint else current_rows)

    if fault is None:
        docker_sources._alertmanager_original_lineage(API())
    else:
        with pytest.raises(RuntimeError, match="AM_original_"):
            docker_sources._alertmanager_original_lineage(API())
    assert called == [2494, 2497]


@pytest.mark.parametrize(
    "job_name",
    [
        "alertmanager-retained-candidate",
        "alertmanager-main-publication",
        "prometheus-image-security-pr",
        "obs2a-checkpoint-native",
    ],
)
@pytest.mark.parametrize(
    "fault", ["corrected", "upgrade-failure", "old-seed", "bad-CA", "parent-child"]
)
@pytest.mark.parametrize("trusted_host", [False, True])
def test_am_host_bootstrap_shell_rejects_unrepaired_child_before_profile(
    tmp_path: Path,
    job_name: str,
    fault: str,
    trusted_host: bool,
) -> None:
    """Execute the real shell/inline guard; synthetic transports do not qualify a real pip wheel."""
    from scripts.ci import install_locked_python_requirements as installer

    workflow = _load_workflow(WORKFLOWS_DIR / "cd.yml")
    step = _step_by_name(
        workflow["jobs"][job_name], "Install isolated AM host tools through the locked owner"
    )
    script = step["run"]
    commands = tmp_path / "commands"
    commands.mkdir()
    trace = tmp_path / "trace.jsonl"
    stub = commands / "python"
    stub.write_text(f"#!{sys.executable}\n" + r"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

def record(step, **fields):
    with Path(os.environ["CONTROL_TRACE"]).open("a") as output:
        output.write(json.dumps({"step": step, **fields}) + "\n")

arguments = sys.argv[1:]
if arguments[:3] == ["-I", "-m", "venv"]:
    assert len(arguments) == 4
    root = Path(arguments[3])
    root.mkdir()
    (root / "bin").mkdir()
    child = root / "bin/python"
    child.write_bytes(Path(__file__).read_bytes())
    child.chmod(0o700)
    record("venv", child=str(child))
    raise SystemExit(0)

root = Path(sys.argv[0]).parent.parent
assert os.environ["HOME"] == str(root / "installer-home")
assert not any(os.environ.get(key) for key in (
    "GH_TOKEN", "GITHUB_TOKEN", "GHCR_READ_TOKEN", "DEVPI_CI_USER", "DEVPI_CI_PASSWORD",
    "PULSEPLATE_PSYCOPG_C_SDK", "PULSEPLATE_DOCKER_SINGLE_PASS_LOCKED_INSTALL",
    "PULSEPLATE_DOCKER_PIP_LAYER_CACHE", "PYTHONHOME", "PYTHONPATH",
))
fault = os.environ["CONTROL_FAULT"]
if arguments == ["-I", "-"]:
    record("observation")
    source = sys.stdin.read()
    ca = root / "synthetic-ca"
    raw = b"synthetic-bad-CA" if fault == "bad-CA" else b"synthetic-corrected-CA"
    ca.write_bytes(raw)
    def version(name):
        assert name == "pip"
        return (root / "pip-version").read_text()
    def digest(value):
        assert value == raw
        record("CA-read")
        target = "0" * 64 if fault == "bad-CA" else "50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785"
        return type("ObservedDigest", (), {"hexdigest": lambda self: target})()
    # Identity and metadata are controlled child collaborators, never a native environment claim.
    sys.prefix = sys.base_prefix if fault == "parent-child" else str(root)
    sys.executable = str(root / "bin/python")
    with patch("importlib.metadata.version", version), patch("pip._vendor.certifi.where", lambda: str(ca)), patch("hashlib.sha256", digest):
        exec(compile(source, "<cd.yml:AM-child-pip-observation>", "exec"), {"__name__": "__main__"})
    raise SystemExit(0)
assert arguments[0] == "-I"
assert arguments[1] == os.environ["GITHUB_WORKSPACE"] + "/scripts/ci/install_locked_python_requirements.py"
flags = arguments[2:]
assert flags[flags.index("--python-executable") + 1] == str(root / "bin/python")
assert "--require-virtualenv" in flags
assert flags[flags.index("--index-url") + 1] == os.environ["PULSEPLATE_PYTHON_INDEX_URL"]
if "--upgrade-pip-only" in flags:
    record("upgrade", flags=flags)
    assert flags[flags.index("--upgrade-pip-spec") + 1] == "pip==26.2.2"
    if fault == "upgrade-failure":
        raise SystemExit(7)
    (root / "pip-version").write_text("26.2.1" if fault == "old-seed" else "26.2.2")
else:
    record("preflight" if "--preflight-only" in flags else "profile", flags=flags)
""")
    stub.chmod(0o700)
    environment = {
        "PATH": str(commands) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "LANG": "C.UTF-8",
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_RUN_ID": "101",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKSPACE": str(REPO_ROOT),
        "PULSEPLATE_PYTHON_INDEX_URL": "https://packages.pulseplate.app/root/pulseplate/+simple/",
        "PULSEPLATE_PYTHON_TRUSTED_HOST": "packages.pulseplate.app" if trusted_host else "",
        "CONTROL_TRACE": str(trace),
        "CONTROL_FAULT": fault,
    }
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", script],
        env=environment,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    steps = [row["step"] for row in records]
    assert steps[:2] == ["venv", "upgrade"]
    upgrade = records[1]["flags"]
    parsed = installer.parse_args(upgrade)
    assert parsed.upgrade_pip_only and not parsed.upgrade_pip and parsed.require_virtualenv
    assert parsed.upgrade_pip_spec == "pip==26.2.2"
    assert parsed.trusted_host == ("packages.pulseplate.app" if trusted_host else None)
    if fault == "corrected":
        assert result.returncode == 0, result.stdout + result.stderr
        assert steps == ["venv", "upgrade", "observation", "CA-read", "preflight", "profile"]
        observed = json.loads(result.stdout)
        assert observed["pip"] == "26.2.2"
        assert observed["python"] == str(tmp_path / "pulseplate-am-python-101-1/bin/python")
    else:
        assert result.returncode != 0
        assert "preflight" not in steps and "profile" not in steps
        assert result.returncode == (7 if fault == "upgrade-failure" else 1)
        if fault != "upgrade-failure":
            assert steps == ["venv", "upgrade", "observation", "CA-read"]
            assert "AM " in result.stderr
    assert "GITHUB_OUTPUT" not in script


@pytest.mark.parametrize(
    "job_name,case",
    [
        (job, case)
        for job in ("prometheus-image-security-pr", "obs2a-checkpoint-native")
        for case in ("main", "wrong-main", "wrong-checkout", "wrong-child-env")
    ]
    + [("prometheus-image-security-pr", "PR")],
)
def test_am_workflow_shell_propagates_authenticated_controller_to_actual_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    alertmanager_temporary_history: dict[str, Any],
    job_name: str,
    case: str,
) -> None:
    """Real shell/CLI/Git binding, with synthetic API transport and no image admission."""
    data = alertmanager_temporary_history
    repository = data["root"]
    fixed, main = data["Q"], data["P"]
    assert fixed != main
    controller = repository / "artifacts/orchestration/alertmanager-control"
    if case == "PR":
        data["command"]("worktree", "add", "--detach", str(controller), fixed)
    elif case == "wrong-checkout":
        data["command"]("checkout", "--detach", fixed)
    workflow = _load_workflow(WORKFLOWS_DIR / "cd.yml")
    step = _step_by_name(
        workflow["jobs"][job_name], "Prepare exact AM subject before material execution"
    )
    script = step["run"]
    commands = tmp_path / "caller-bin"
    commands.mkdir()
    trace = tmp_path / "caller-trace.jsonl"
    output = tmp_path / "step-output"
    output.write_text("")
    program = r"""
import json
import os
from pathlib import Path
import sys
from scripts.ci import fetch_docker_source_artifacts as source

def record(step, **fields):
    with Path(os.environ["CONTROL_TRACE"]).open("a") as stream:
        stream.write(json.dumps({"step": step, **fields}) + "\n")
args = source.parse_args(sys.argv[1:])
record("CLI", argument=args.alertmanager_controller_source,
       received=os.environ["ALERTMANAGER_CONTROLLER_SOURCE"])
source.REPO_ROOT = Path(os.environ["CONTROL_CHECKOUT"])
if os.environ["CONTROL_CASE"] == "wrong-child-env":
    os.environ["ALERTMANAGER_CONTROLLER_SOURCE"] = os.environ["CONTROL_FIXED_C"]
source._alertmanager_controller_binding(args)
class TemplateBoundary(RuntimeError):
    pass
class API:
    def json(self, endpoint):
        assert endpoint == "/repos/Katsiarynakavaleuskaya/PulsePlate/git/commits/" + args.alertmanager_controller_source
        record("template-source", source=args.alertmanager_controller_source)
        raise TemplateBoundary()
try:
    source._alertmanager_source_snapshot(API(), os.environ["ALERTMANAGER_CONTROLLER_SOURCE"], controller_templates=True)
except TemplateBoundary:
    pass
else:
    raise AssertionError("Expected bounded synthetic API boundary")
record("binding-admitted", source=args.alertmanager_controller_source)
print("image_id=sha256:" + "1" * 64)
print("config_sha256=" + "2" * 64)
print("observation=synthetic-observation")
"""
    shim = commands / "python3"
    shim.write_text(
        f"#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n"
        "assert sys.argv[1:6] == ['-E','-s','-S','-m','scripts.ci.fetch_docker_source_artifacts']\n"
        "env=dict(os.environ); env['CONTROL_CHECKOUT']=str(Path.cwd())\n"
        "os.chdir(env['CONTROL_REPO_ROOT'])\n"
        f"os.execve(sys.executable,[sys.executable,'-E','-s','-S','-c',{program!r},*sys.argv[6:]],env)\n"
    )
    shim.chmod(0o700)
    gh = commands / "gh"
    gh.write_text(
        f"#!{sys.executable}\nimport os,sys,json\nfrom pathlib import Path\n"
        "args=sys.argv[1:]\n"
        "assert args in (['auth','status','--hostname','github.com'],['api','--method','GET','repos/Katsiarynakavaleuskaya/PulsePlate/git/ref/heads/main','--jq','.object.sha'])\n"
        "with Path(os.environ['CONTROL_TRACE']).open('a') as f:f.write(json.dumps({'step':'gh-'+args[0]})+'\\n')\n"
        "if args[0]=='api':print(os.environ['CONTROL_API_MAIN'])\n"
    )
    gh.chmod(0o700)
    timeout = commands / "timeout"
    timeout.write_text(
        f"#!{sys.executable}\nimport os,sys\nfrom pathlib import Path\n"
        "assert sys.argv[1:4]==['--signal=TERM','--kill-after=2s','15s']\n"
        "assert sys.argv[4]=='gh'\n"
        "command=str(Path(__file__).with_name('gh'))\n"
        "os.execve(command,[command,*sys.argv[5:]],os.environ)\n"
    )
    timeout.chmod(0o700)
    docker = commands / "docker"
    docker.write_text(
        f"#!{sys.executable}\nimport sys\n"
        "assert sys.argv[1] in ('version','info') and sys.argv[2]=='--format' and len(sys.argv)==4\n"
        "print('synthetic Docker metadata')\n"
    )
    docker.chmod(0o700)
    environment = {
        "PATH": str(commands) + os.pathsep + os.defpath,
        "HOME": str(tmp_path),
        "LANG": "C",
        "GITHUB_WORKSPACE": str(repository),
        "RUNNER_TEMP": str(tmp_path),
        "GITHUB_EVENT_NAME": "pull_request" if case == "PR" else "push",
        "GITHUB_SHA": main,
        "SOURCE_SHA": main,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ID": "102",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_OUTPUT": str(output),
        "GH_TOKEN": "synthetic-caller",
        "GITHUB_TOKEN": "synthetic-caller",
        "ALERTMANAGER_CONTROLLER_SOURCE": fixed,
        "CONTROL_TRACE": str(trace),
        "CONTROL_REPO_ROOT": str(REPO_ROOT),
        "CONTROL_FIXED_C": fixed,
        "CONTROL_CASE": case,
        "CONTROL_API_MAIN": "f" * 40 if case == "wrong-main" else main,
        "TMPDIR": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    bash = shutil.which("bash")
    assert bash is not None
    result = subprocess.run(
        [bash, "-c", script],
        cwd=repository,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    records = (
        [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    )
    steps = [row["step"] for row in records]
    if case in {"main", "PR"}:
        assert result.returncode == 0, result.stdout + result.stderr
        expected = fixed if case == "PR" else main
        cli = next(row for row in records if row["step"] == "CLI")
        assert cli["argument"] == cli["received"] == expected
        assert records[-2:] == [
            {"step": "template-source", "source": expected},
            {"step": "binding-admitted", "source": expected},
        ]
        assert f"controller_source={expected}\n" in output.read_text()
        assert ("gh-auth" in steps) is (case != "PR")
    else:
        assert result.returncode != 0
        assert "binding-admitted" not in steps and "template-source" not in steps
        assert "controller_source=" not in output.read_text()
        if case == "wrong-child-env":
            assert next(row for row in records if row["step"] == "CLI")["received"] == main
            assert "AM_controller_UNCONFIGURED_HOLD" in result.stderr
        else:
            assert "CLI" not in steps
    scan = _step_by_name(
        workflow["jobs"]["prometheus-image-security-pr"],
        "Scan accepted AM and execute all four current controls",
    )
    assert (
        scan["env"]["ALERTMANAGER_CONTROLLER_SOURCE"]
        == "${{ steps.alertmanager-image.outputs.controller_source }}"
    )
    assert environment["ALERTMANAGER_CONTROLLER_SOURCE"] == fixed


@pytest.mark.parametrize(
    "job_name",
    [
        "alertmanager-module-qualification",
        "alertmanager-input-inspection",
        "alertmanager-candidate-build",
        "alertmanager-main-publication",
    ],
)
def test_alertmanager_native_producers_keep_qualified_runner(job_name: str) -> None:
    """Keep native config-ID consumers on their qualified Docker runner environment."""
    workflow = _load_workflow(WORKFLOWS_DIR / "cd.yml")
    assert workflow["jobs"][job_name]["runs-on"] == "ubuntu-24.04"


@pytest.fixture
def current_AM_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Complete synthetic Q/S byte transport; no native supplier/build proof is claimed."""
    import tarfile
    from scripts.ci import prometheus_source_image as transport

    root = tmp_path / "current-export"
    root.mkdir()
    files: dict[str, bytes] = {}

    def blob(raw: bytes, media: str) -> dict[str, Any]:
        digest = sha256(raw).hexdigest()
        files["blobs/sha256/" + digest] = raw
        return {"digest": "sha256:" + digest, "size": len(raw), "mediaType": media}

    layers = [
        blob(f"synthetic expanded layer {i}".encode(), "application/vnd.oci.image.layer.v1.tar")
        for i in range(13)
    ]
    config = {
        "os": "linux",
        "architecture": "amd64",
        "rootfs": {"type": "layers", "diff_ids": [x["digest"] for x in layers]},
    }
    raw_config = json.dumps(config).encode().ljust(2938, b" ")
    config_descriptor = blob(raw_config, transport.OCI_CONFIG)
    descriptor = blob(
        json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": transport.OCI_MANIFEST,
                "config": config_descriptor,
                "layers": layers,
            }
        ).encode(),
        transport.OCI_MANIFEST,
    )
    for number in range(13):
        blob(f"synthetic Docker compatibility metadata {number}".encode(), "unused")
    files["oci-layout"] = b'{"imageLayoutVersion":"1.0.0"}'
    files["index.json"] = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [descriptor],
        }
    ).encode()
    files["manifest.json"] = b"[]"
    assert len(files) == 31
    archive = root / "base-image.tar"
    with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as output:
        for name in ("blobs", "blobs/sha256"):
            entry = tarfile.TarInfo(name)
            entry.type = tarfile.DIRTYPE
            output.addfile(entry)
        for name, raw in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(raw)
            output.addfile(entry, BytesIO(raw))
    archive.chmod(0o600)
    layout = root / "base-layout"
    layout.mkdir(mode=0o700)
    rows, directories = docker_sources._alertmanager_base_export_inventory(
        archive, destination=layout
    )
    monkeypatch.setattr(transport, "BASE_CONFIG", config_descriptor["digest"])
    monkeypatch.setattr(
        transport,
        "BASE_LAYER_CONTRACTS",
        [{"diff_id": row["digest"], "expanded": row["size"]} for row in layers],
    )
    q = {
        "root_inputs": {"base-image.tar": sha256(archive.read_bytes()).hexdigest()},
        "loaded_base": {"RootFS": {"Type": "layers", "Layers": config["rootfs"]["diff_ids"]}},
    }
    report = {
        "base": {
            "archive_sha256": q["root_inputs"]["base-image.tar"],
            "complete_export_file_inventory": rows,
            "actual_local_OCI_descriptor": descriptor,
            "config": config_descriptor["digest"],
            "RootFS": q["loaded_base"]["RootFS"],
        }
    }
    return {
        "root": root,
        "files": files,
        "report": report,
        "q": q,
        "descriptor": descriptor,
        "directories": directories,
        "layers": layers,
    }


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "compatibility",
        "extra",
        "missing",
        "replaced",
        "index",
        "directory",
        "symlink",
        "hardlink",
        "mode",
        "Q-hash",
        "report-hash",
        "report-descriptor",
        "report-config",
        "report-rootfs",
        "pinned-size",
        "pinned-order",
    ],
)
def test_current_AM_export_binds_every_Q_byte_before_report_or_graph(
    current_AM_export: dict[str, Any], monkeypatch: pytest.MonkeyPatch, fault: str | None
) -> None:
    from scripts.ci import prometheus_source_image as transport

    item = current_AM_export
    root, report, q = item["root"], item["report"], item["q"]
    docker_sources._alertmanager_current_support_base(root, report, q)
    layout = root / "base-layout"
    compatibility = next(name for name, raw in item["files"].items() if b"compatibility" in raw)
    target = layout / compatibility
    if fault == "compatibility":
        target.write_bytes(b"changed but report and footer can agree")
    elif fault == "extra":
        (layout / "extra").write_bytes(b"extra")
        (layout / "extra").chmod(0o600)
    elif fault == "missing":
        target.unlink()
    elif fault == "replaced":
        target.rename(layout / "replacement")
    elif fault == "index":
        (layout / "index.json").write_text("{}")
    elif fault == "directory":
        (layout / "extra-directory").mkdir(mode=0o700)
    elif fault in ("symlink", "hardlink"):
        target.unlink()
        other = layout / "manifest.json"
        target.symlink_to(other) if fault == "symlink" else os.link(other, target)
    elif fault == "mode":
        target.chmod(0o644)
    elif fault == "Q-hash":
        q["root_inputs"]["base-image.tar"] = "f" * 64
    elif fault == "report-hash":
        report["base"]["archive_sha256"] = "f" * 64
    elif fault == "report-descriptor":
        report["base"]["actual_local_OCI_descriptor"] = {**item["descriptor"], "size": 1}
    elif fault == "report-config":
        report["base"]["config"] = "sha256:" + "f" * 64
    elif fault == "report-rootfs":
        report["base"]["RootFS"] = {"Type": "layers", "Layers": []}
    elif fault in ("pinned-size", "pinned-order"):
        contracts = deepcopy(transport.BASE_LAYER_CONTRACTS)
        if fault == "pinned-size":
            contracts[0]["expanded"] += 1
        else:
            contracts.reverse()
        monkeypatch.setattr(transport, "BASE_LAYER_CONTRACTS", contracts)
    if fault in {"compatibility", "extra", "missing", "replaced", "index"}:
        # An internally consistent S report cannot override the independent Q tar.
        report["base"]["complete_export_file_inventory"] = [
            {"path": row["path"], "bytes": row["size"], "sha256": row["sha256"]}
            for row in transport.tree_inventory(layout)
        ]
    if fault is None:
        assert docker_sources._alertmanager_current_base_graph(layout) == item["descriptor"]
        assert (
            docker_sources._alertmanager_base_export_inventory(root / "base-image.tar")[1]
            == item["directories"]
        )
    else:
        with pytest.raises(transport.QualificationError):
            docker_sources._alertmanager_current_support_base(root, report, q)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate",
        "dot",
        "parent",
        "absolute",
        "backslash",
        "symlink",
        "hardlink",
        "special",
        "file-parent",
        "directory-as-file",
        "count",
        "oversized",
    ],
)
def test_current_AM_export_tar_rules_reject_unsafe_private_materialization(
    tmp_path: Path, fault: str
) -> None:
    import tarfile
    from scripts.ci.prometheus_source_image import QualificationError

    archive = tmp_path / "invalid.tar"
    with tarfile.open(archive, "w", format=tarfile.USTAR_FORMAT) as output:
        first = tarfile.TarInfo("safe")
        first.size = 1
        output.addfile(first, BytesIO(b"x"))
        entry = tarfile.TarInfo(
            {
                "duplicate": "safe",
                "dot": "./bad",
                "parent": "../bad",
                "absolute": "/bad",
                "backslash": "bad\\path",
                "file-parent": "safe/child",
            }.get(fault, "bad")
        )
        if fault in ("symlink", "hardlink", "special"):
            entry.type = {
                "symlink": tarfile.SYMTYPE,
                "hardlink": tarfile.LNKTYPE,
                "special": tarfile.FIFOTYPE,
            }[fault]
            entry.linkname = "safe"
        if fault == "directory-as-file":
            directory = tarfile.TarInfo("bad/child")
            directory.type = tarfile.DIRTYPE
            output.addfile(directory)
        if fault == "count":
            for number in range(33):
                output.addfile(tarfile.TarInfo(f"extra-{number}"))
        output.addfile(entry)
    archive.chmod(0o600)
    if fault == "oversized":
        with archive.open("ab") as output:
            output.truncate(16 * 1024**2 + 1)
    destination = tmp_path / "layout"
    destination.mkdir(mode=0o700)
    with pytest.raises(QualificationError):
        docker_sources._alertmanager_base_export_inventory(archive, destination=destination)


@pytest.mark.parametrize("current", [False, True])
@pytest.mark.parametrize(
    "fault", [None, "crossed-recipe", "mixed-source", "selector", "unconfigured"]
)
def test_AM11_accepted_recipe_is_disjoint_and_bound_to_configured_selection(
    monkeypatch: pytest.MonkeyPatch, current: bool, fault: str | None
) -> None:
    from scripts.ci.prometheus_source_image import QualificationError

    selected = deepcopy(docker_sources._ALERT_HISTORICAL_C10)
    if current:
        selected.update(source="a" * 40, run=101, artifact=102, job=103)
        selected["source_files"][
            "deploy/alertmanager/Containerfile"
        ] = docker_sources._ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
    monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", selected)
    assert (
        docker_sources._alertmanager_accepted_producer(
            selected["run"], selected["artifact"], selected["source"]
        )
        == selected
    )
    if fault == "crossed-recipe":
        selected["source_files"]["deploy/alertmanager/Containerfile"] = (
            docker_sources._ALERT_ASSEMBLY_RECIPE_SHA256
            if current
            else docker_sources._ALERT_CURRENT_ASSEMBLY_RECIPE_SHA256
        )
    elif fault == "mixed-source":
        selected["source"] = docker_sources._ALERT_HISTORICAL_C10["source"] if current else "a" * 40
    elif fault == "unconfigured":
        monkeypatch.setattr(docker_sources, "_ALERT_ACCEPTED_CANDIDATE", None)
    if fault is not None:
        with pytest.raises(QualificationError):
            docker_sources._alertmanager_accepted_producer(
                selected["run"] + (1 if fault == "selector" else 0),
                selected["artifact"],
                selected["source"],
            )

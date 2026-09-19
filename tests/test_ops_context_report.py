"""Offline operational evidence contracts; identifiers and packets are synthetic."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.ops import ops_context_report as ops

SHA = "a" * 40
NOW = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    sources = []
    for environment in ("production", "staging"):
        for service in ("app", "database", "prometheus", "packages"):
            path = f"docs/{environment}-{service}.md"
            target = tmp_path / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"synthetic {environment} {service}\n", encoding="utf-8")
            sources.append(
                {
                    "environment": environment,
                    "service": service,
                    "configuration": (
                        "managed_default" if environment == "production" else "staging"
                    ),
                    "path": path,
                }
            )
    for service in ("app", "database", "prometheus"):
        sources.append(
            {
                "environment": "production",
                "service": service,
                "configuration": "selfhosted_alternative",
                "path": f"docs/production-{service}.md",
            }
        )
    index = tmp_path / "docs/deploy/OPS_CONTEXT_SOURCES.json"
    index.parent.mkdir(parents=True)
    index.write_text(
        json.dumps({"schema_version": "ops-context-sources.v1", "sources": sources}),
        encoding="utf-8",
    )
    return tmp_path


def observation(**changes: object) -> dict[str, object]:
    record: dict[str, object] = {
        "environment": "production",
        "service": "database",
        "resource_id": "synthetic-db-1",
        "provenance": "provider_export",
        "observed_at": "2026-09-14T12:00:00Z",
        "repo_sha": SHA,
        "selected_config": "managed_default",
    }
    record.update(changes)
    return record


def write_observed(root: Path, records: list[dict[str, object]]) -> str:
    path = "artifacts/observed.json"
    target = root / path
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        json.dumps({"schema_version": "ops-observed.v1", "observations": records}), encoding="utf-8"
    )
    return path


def report(root: Path, **kwargs: object) -> dict:
    return ops.build_report(root, environment="production", repo_sha=SHA, now=NOW, **kwargs)


def test_no_observations_preserves_unknowns_and_selection(repository: Path) -> None:
    result = report(repository)
    assert result["schema_version"] == "ops-context-report.v1"
    assert {item["service"] for item in result["surfaces"]} == set(ops.SERVICES)
    assert all(item["live_identity"] == "unknown" for item in result["surfaces"])
    assert all("staging" not in source["path"] for source in result["sources"])
    assert result["observations"] == []
    assert result["authority"] == "none"


@pytest.mark.parametrize("selector", ["PRODUCTION", "invalid-secret-marker", "", None])
def test_invalid_environment_rejected(repository: Path, selector: object) -> None:
    with pytest.raises(ops.ReportError):
        ops.build_report(repository, environment=selector, repo_sha=SHA, now=NOW)


@pytest.mark.parametrize("age,freshness", [(0, "fresh"), (60, "fresh"), (61, "stale")])
def test_freshness_boundary(repository: Path, age: int, freshness: str) -> None:
    from datetime import timedelta

    observed_at = (NOW - timedelta(seconds=age)).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = write_observed(repository, [observation(observed_at=observed_at)])
    result = report(repository, observed=path, max_age_seconds=60)
    assert result["observations"][0]["freshness"] == freshness
    assert result["observations"][0]["revision_match"] is True
    assert result["provider_authentication"] == "not_assessed"
    assert result["surfaces"][1]["live_identity"] == "unknown"


def test_conflicts_cross_alternatives_and_are_order_independent(repository: Path) -> None:
    records = [
        observation(),
        observation(
            resource_id="synthetic-db-2",
            selected_config="selfhosted_alternative",
            observed_at="2026-09-14T11:00:00Z",
            repo_sha="b" * 40,
        ),
    ]
    path = write_observed(repository, records)
    first = report(repository, observed=path, max_age_seconds=60)
    write_observed(repository, list(reversed(records)))
    second = report(repository, observed=path, max_age_seconds=60)
    assert first["observations"] == second["observations"]
    assert first["surfaces"] == second["surfaces"]
    surface = next(item for item in first["surfaces"] if item["service"] == "database")
    assert surface["conflicts"] == ["resource_id", "selected_config"]
    assert surface["live_identity"] == "unknown"


@pytest.mark.parametrize(
    "field,value",
    [
        ("environment", "unknown"),
        ("service", "bad"),
        ("resource_id", "https://secret-marker"),
        ("observed_at", "2026-09-14T12:00:01Z"),
        ("observed_at", "2026-09-14T12:00:00"),
        ("repo_sha", "bad"),
        ("provenance", "verified"),
        ("unexpected", "secret-marker"),
    ],
)
def test_whole_observed_input_validated(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: object,
) -> None:
    baseline = observation(environment="staging", selected_config="staging")
    path = write_observed(repository, [observation(), baseline])
    positive = report(repository, observed=path, max_age_seconds=60)
    assert len(positive["observations"]) == 1
    assert positive["observations"][0]["environment"] == "production"
    changed = {**baseline, field: value}
    assert {key for key in changed if changed[key] != baseline.get(key)} == {field}
    write_observed(repository, [observation(), changed])
    with pytest.raises(ops.ReportError):
        report(repository, observed=path, max_age_seconds=60)
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    original = ops.build_report

    def fixed_clock(root: Path, **kwargs: object) -> dict:
        return original(root, now=NOW, **kwargs)

    monkeypatch.setattr(ops, "build_report", fixed_clock)
    assert (
        ops.main(
            [
                "--environment",
                "production",
                "--observed",
                path,
                "--max-observation-age-seconds",
                "60",
                "--format",
                "json",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


@pytest.mark.parametrize("window", [None, 0, -1, True, float("inf")])
def test_observed_requires_positive_integer_window(repository: Path, window: object) -> None:
    path = write_observed(repository, [observation()])
    with pytest.raises(ops.ReportError):
        report(repository, observed=path, max_age_seconds=window)


@pytest.mark.parametrize("option", ["sources", "observed"])
@pytest.mark.parametrize(
    "path",
    [
        "/outside/secret-marker.json",
        "../secret-marker.json",
        "docs//secret-marker.json",
        "./docs/secret-marker.json",
        "docs\\secret-marker.json",
    ],
)
def test_input_paths_require_canonical_relative(repository: Path, option: str, path: str) -> None:
    with pytest.raises(ops.ReportError):
        report(repository, **{option: path}, max_age_seconds=60)


def test_alternate_index_and_absolute_inside(repository: Path) -> None:
    original = repository / ops.DEFAULT_SOURCES
    alternate = repository / "docs/alternate.json"
    alternate.write_bytes(original.read_bytes())
    assert report(repository, sources="docs/alternate.json")["surfaces"]
    for option, path in [
        ("sources", str(original)),
        ("observed", str(repository / write_observed(repository, []))),
    ]:
        with pytest.raises(ops.ReportError):
            report(repository, **{option: path}, max_age_seconds=60)


@pytest.mark.parametrize(
    "args",
    [
        ["--environment", "secret-marker"],
        ["--secret-marker"],
        ["--environment", "production", "--observed", "../secret-marker"],
    ],
)
def test_cli_errors_do_not_echo_input(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    assert ops.main(args + ["--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "secret-marker" not in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("environment", ["production", "staging"])
@pytest.mark.parametrize("service", [None, "app", "database", "prometheus", "packages"])
def test_exact_accepted_cli_success(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    environment: str,
    service: str | None,
) -> None:
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    args = [
        "--environment",
        environment,
        "--format",
        "json",
        "--sources",
        ops.DEFAULT_SOURCES,
        "--observed",
        write_observed(repository, []),
        "--max-observation-age-seconds",
        "60",
    ]
    if service is not None:
        args.extend(["--service", service])
    assert ops.main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result["environment"] == environment
    assert {item["service"] for item in result["surfaces"]} == (
        {service} if service else set(ops.SERVICES)
    )
    assert all(
        item["unknowns"]
        == [
            "live_identity_unverified",
            "selected_configuration_unverified",
            "no_supplied_observations",
        ]
        for item in result["surfaces"]
    )


@pytest.mark.parametrize("option", ["sources", "observed"])
@pytest.mark.parametrize("path", [".env", "docs/config.yaml", "artifacts/file.txt"])
def test_inputs_must_be_json(repository: Path, option: str, path: str) -> None:
    with pytest.raises(ops.ReportError):
        report(repository, **{option: path}, max_age_seconds=60)


@pytest.mark.parametrize(
    "kind", ["symlink", "ancestor", "hardlink", "fifo", "directory", "oversize", "missing", "utf8"]
)
def test_dynamic_filesystem_admission(repository: Path, kind: str) -> None:
    import os

    target = repository / "observed.json"
    if kind == "symlink":
        target.symlink_to(repository / ops.DEFAULT_SOURCES)
    elif kind == "ancestor":
        (repository / "alias").symlink_to(repository / "docs", target_is_directory=True)
        target = repository / "alias/deploy/OPS_CONTEXT_SOURCES.json"
    elif kind == "hardlink":
        os.link(repository / ops.DEFAULT_SOURCES, target)
    elif kind == "fifo":
        os.mkfifo(target)
    elif kind == "directory":
        target.mkdir()
    elif kind == "oversize":
        target.write_bytes(b" " * (ops.MAX_JSON_BYTES + 1))
    elif kind == "utf8":
        target.write_bytes(b"\xffsecret-marker")
    with pytest.raises(ops.ReportError):
        report(repository, observed=target.relative_to(repository).as_posix(), max_age_seconds=60)


@pytest.mark.parametrize(
    "path",
    [
        ".env.json",
        "artifacts/private.json",
        "docs/secret.key",
        "../private.json",
        "/private.json",
        "docs/*.md",
    ],
)
def test_static_policy_rejects_before_read(
    repository: Path, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    index = repository / ops.DEFAULT_SOURCES
    payload = json.loads(index.read_text())
    payload["sources"][0]["path"] = path
    index.write_text(json.dumps(payload))
    reads: list[str] = []
    original = ops.reader.read_repo_source

    def record_read(root: Path, raw_path: str, **kwargs: object) -> object:
        reads.append(raw_path)
        return original(root, raw_path, **kwargs)

    monkeypatch.setattr(ops.reader, "read_repo_source", record_read)
    with pytest.raises(ops.ReportError):
        report(repository)
    assert reads == [ops.DEFAULT_SOURCES]


def test_missing_selected_source_fatal_unselected_source_not_read(repository: Path) -> None:
    (repository / "docs/staging-app.md").unlink()
    assert report(repository)["surfaces"]
    (repository / "docs/production-app.md").unlink()
    with pytest.raises(ops.ReportError):
        report(repository)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":-Infinity}',
        b"{",
        b"[]",
        b'{"x":"\\ud800"}',
        b'{"x":"secret-marker\\n"}',
        b"[" * 1000 + b"]" * 1000,
        json.dumps({"x": "x" * 513}).encode(),
        json.dumps(
            {"schema_version": "ops-observed.v1", "observations": [observation()] * 129}
        ).encode(),
    ],
)
def test_bad_json_never_leaks(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    raw: bytes,
) -> None:
    (repository / "bad.json").write_bytes(raw)
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    assert (
        ops.main(
            [
                "--environment",
                "production",
                "--observed",
                "bad.json",
                "--max-observation-age-seconds",
                "60",
                "--format",
                "json",
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


@pytest.mark.parametrize("duplicate_scope", ["root", "record"])
def test_duplicate_keys_only_rejected_with_valid_controls(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    duplicate_scope: str,
) -> None:
    record = json.dumps(observation(resource_id="synthetic-secret-marker"))
    raw = '{"schema_version":"ops-observed.v1","observations":[' + record + "]}"
    target = repository / "observed.json"
    target.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    original = ops.build_report

    def fixed_clock(root: Path, **kwargs: object) -> dict:
        return original(root, now=NOW, **kwargs)

    monkeypatch.setattr(ops, "build_report", fixed_clock)
    args = [
        "--environment",
        "production",
        "--observed",
        "observed.json",
        "--max-observation-age-seconds",
        "60",
        "--format",
        "json",
    ]
    assert ops.main(args) == 0
    positive = capsys.readouterr()
    assert positive.err == ""
    assert len(json.loads(positive.out)["observations"]) == 1
    duplicate = (
        '"schema_version":"ops-observed.v1"'
        if duplicate_scope == "root"
        else '"resource_id": "synthetic-secret-marker"'
    )
    assert raw.count(duplicate) == 1
    target.write_text(raw.replace(duplicate, duplicate + "," + duplicate), encoding="utf-8")
    assert ops.main(args) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


def test_duplicate_claims_not_corroboration_and_same_id_config_conflict(repository: Path) -> None:
    path = write_observed(repository, [observation(), observation()])
    result = report(repository, observed=path, max_age_seconds=60)
    surface = next(item for item in result["surfaces"] if item["service"] == "database")
    assert surface["conflicts"] == []
    assert surface["live_identity"] == "unknown"
    assert len(result["observations"]) == 2
    write_observed(
        repository, [observation(), observation(selected_config="selfhosted_alternative")]
    )
    result = report(repository, observed=path, max_age_seconds=60)
    assert result["surfaces"][1]["conflicts"] == ["selected_config"]


def test_revision_claim_and_dirty_byte_fingerprint(repository: Path) -> None:
    import hashlib

    path = write_observed(repository, [observation()])
    before = report(repository, observed=path, max_age_seconds=60)
    source = repository / "docs/production-database.md"
    source.write_bytes(b"changed synthetic config\r\n")
    after = report(repository, observed=path, max_age_seconds=60)
    assert before["repo_sha"] == after["repo_sha"]
    assert after["observations"][0]["revision_match"] is True
    assert before["sources"] != after["sources"]
    assert (
        next(
            item["sha256"]
            for item in after["sources"]
            if item["path"] == "docs/production-database.md"
        )
        == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    assert after["configuration_verification"] == "not_assessed"


def test_mismatch_and_stale_unknown_reasons(repository: Path) -> None:
    record = observation(repo_sha="b" * 40, observed_at="2026-09-14T11:00:00Z")
    record.pop("selected_config")
    path = write_observed(
        repository,
        [
            record,
            observation(
                environment="staging", selected_config="staging", resource_id="synthetic-staging"
            ),
        ],
    )
    result = report(repository, observed=path, max_age_seconds=60)
    assert len(result["observations"]) == 1
    assert result["observations"][0]["revision_match"] is False
    assert result["surfaces"][1]["unknowns"] == [
        "live_identity_unverified",
        "selected_configuration_unverified",
        "stale_observation",
        "revision_mismatch",
        "selected_configuration_not_supplied",
    ]
    assert result["surfaces"][1]["conflicts"] == []


@pytest.mark.parametrize("mode", [None, "self-hosted", "managed", "secret-marker"])
def test_deploy_transport_never_selects_topology(
    repository: Path, monkeypatch: pytest.MonkeyPatch, mode: str | None
) -> None:
    if mode is None:
        monkeypatch.delenv("PROD_DEPLOY_MODE", raising=False)
    else:
        monkeypatch.setenv("PROD_DEPLOY_MODE", mode)
    assert report(repository)["surfaces"][1]["selected_configuration"] == "unknown"


def test_git_fixed_absolute_read_only_query(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    monkeypatch.setenv("GIT_DIR", "secret-marker")
    monkeypatch.setenv("GIT_WORK_TREE", "secret-marker")
    lookups = []

    def system_lookup(name: str, *, path: str) -> str:
        lookups.append((name, path))
        return "/synthetic/git"

    monkeypatch.setattr(ops.shutil, "which", system_lookup)
    calls = []

    def run(args: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=(SHA + "\n").encode(), stderr=b"secret-marker")

    monkeypatch.setattr(ops.subprocess, "run", run)
    assert ops.git_revision(repository) == SHA
    assert lookups == [("git", "/usr/bin:/bin")]
    assert calls == [
        (
            ["/synthetic/git", "--no-replace-objects", "rev-parse", "--verify", "HEAD^{commit}"],
            {
                "cwd": repository,
                "env": {
                    "PATH": "/usr/bin:/bin",
                    "LC_ALL": "C",
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": "/dev/null",
                },
                "capture_output": True,
                "timeout": 5,
                "check": False,
            },
        )
    ]


@pytest.mark.parametrize(
    "failure", ["missing", "relative", "timeout", "oserror", "exit", "bad", "utf8"]
)
def test_git_failure_sanitized(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    import subprocess
    from types import SimpleNamespace

    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(
        ops.shutil,
        "which",
        lambda name, *, path: (
            None
            if failure == "missing"
            else "relative/git" if failure == "relative" else "/synthetic/git"
        ),
    )

    def run(*args: object, **kwargs: object) -> SimpleNamespace:
        if failure == "timeout":
            raise subprocess.TimeoutExpired("secret-marker", 5)
        if failure == "oserror":
            raise OSError("secret-marker")
        return SimpleNamespace(
            returncode=1 if failure == "exit" else 0,
            stdout=b"\xff" if failure == "utf8" else b"secret-marker",
            stderr=b"secret-marker",
        )

    monkeypatch.setattr(ops.subprocess, "run", run)
    assert ops.main(["--environment", "production", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


def test_ambient_git_override_cannot_select_second_repo(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil
    import subprocess

    git = shutil.which("git", path="/usr/bin:/bin")
    assert git is not None
    # Native hooks export repository/index/config state before invoking pytest.
    # Exercise that setup boundary using only disposable paths.
    hook_git = tmp_path / "hook.git"
    hook_git.mkdir()
    hook_config = hook_git / "config"
    hook_config.write_bytes(b"[core]\n\tbare = true\n")
    hook_index = tmp_path / "hook-index"
    hook_index.write_bytes(b"synthetic-index-sentinel")
    original_config = hook_config.read_bytes()
    original_index = hook_index.read_bytes()
    monkeypatch.setenv("GIT_DIR", str(hook_git))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "hook-worktree"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(hook_index))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false")
    second = tmp_path / "second"
    second.mkdir()
    env = {
        "PATH": str(Path(git).parent),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_AUTHOR_NAME": "Synthetic",
        "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic",
        "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
    }
    for directory in (repository, second):
        subprocess.run(
            [git, "-c", "init.templateDir=", "init", "--quiet", str(directory)],
            env=env,
            check=True,
            capture_output=True,
            timeout=5,
        )
    for directory, message in ((repository, "first"), (second, "second")):
        subprocess.run(
            [
                git,
                "-C",
                str(directory),
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "--allow-empty",
                "--quiet",
                "-m",
                message,
            ],
            env=env,
            check=True,
            capture_output=True,
            timeout=5,
        )
    assert hook_config.read_bytes() == original_config
    assert hook_index.read_bytes() == original_index
    assert sorted(path.name for path in hook_git.iterdir()) == ["config"]
    assert not (tmp_path / "hook-worktree").exists()
    expected = ops.git_revision(repository)
    assert ops.git_revision(second) != expected
    monkeypatch.setenv("GIT_DIR", str(second / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(second))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.worktree")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(second))
    assert ops.git_revision(repository) == expected


@pytest.fixture
def native_commit(repository: Path) -> tuple[str, dict[str, str], str]:
    import shutil
    import subprocess

    git = shutil.which("git", path="/usr/bin:/bin")
    assert git is not None
    env = {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_AUTHOR_NAME": "Synthetic",
        "GIT_AUTHOR_EMAIL": "synthetic@example.invalid",
        "GIT_COMMITTER_NAME": "Synthetic",
        "GIT_COMMITTER_EMAIL": "synthetic@example.invalid",
    }
    prefix = [
        git,
        "-c",
        "init.templateDir=",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
    ]
    for args in (["init", "--quiet"], ["commit", "--allow-empty", "--quiet", "-m", "synthetic"]):
        subprocess.run(
            prefix + args, cwd=repository, env=env, check=True, capture_output=True, timeout=5
        )
    result = subprocess.run(
        prefix + ["rev-parse", "--verify", "HEAD^{commit}"],
        cwd=repository,
        env=env,
        check=True,
        capture_output=True,
        timeout=5,
    )
    return git, env, result.stdout.decode("ascii").strip()


@pytest.mark.parametrize(
    "head_kind", ["attached", "detached", "blob", "tree", "unborn", "missing", "dangling"]
)
def test_native_git_requires_commit_head(
    repository: Path,
    native_commit: tuple[str, dict[str, str], str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    head_kind: str,
) -> None:
    import subprocess

    git, env, commit = native_commit
    head = repository / ".git/HEAD"
    if head_kind in {"blob", "tree"}:
        args = ["hash-object", "-w", "--stdin"] if head_kind == "blob" else ["mktree"]
        result = subprocess.run(
            [git, "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"] + args,
            input=b"synthetic\n" if head_kind == "blob" else b"",
            cwd=repository,
            env=env,
            check=True,
            capture_output=True,
            timeout=5,
        )
        head.write_bytes(result.stdout)
    elif head_kind == "detached":
        head.write_text(commit + "\n", encoding="ascii")
    elif head_kind == "unborn":
        head.write_text("ref: refs/heads/unborn\n", encoding="ascii")
    elif head_kind == "missing":
        head.unlink()
    elif head_kind == "dangling":
        head.write_text("b" * 40 + "\n", encoding="ascii")
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    result_code = ops.main(["--environment", "production", "--format", "json"])
    captured = capsys.readouterr()
    if head_kind in {"attached", "detached"}:
        assert result_code == 0
        assert captured.err == ""
        assert json.loads(captured.out)["repo_sha"] == commit
    else:
        assert result_code == 2
        assert captured.out == ""
        assert captured.err == "ops-context-report: INVALID_REQUEST\n"


def test_caller_path_cannot_supply_git(
    repository: Path,
    native_commit: tuple[str, dict[str, str], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shlex

    _, _, commit = native_commit
    fake_bin = repository / "fake-bin"
    fake_bin.mkdir()
    marker = fake_bin / "executed"
    fake = fake_bin / "git"
    fake.write_text(
        "#!/bin/sh\n: > " + shlex.quote(str(marker)) + "\nprintf '%s\\n' " + "b" * 40 + "\n",
        encoding="ascii",
    )
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(fake_bin))
    assert ops.git_revision(repository) == commit
    assert not marker.exists()


def test_missing_system_git_never_falls_back(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lookups = []

    def missing(name: str, *, path: str) -> None:
        lookups.append((name, path))

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("missing system Git must not execute a subprocess")

    monkeypatch.setenv("PATH", str(repository / "caller-secret-marker"))
    monkeypatch.setattr(ops.shutil, "which", missing)
    monkeypatch.setattr(ops.subprocess, "run", forbidden)
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    assert ops.main(["--environment", "production", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert lookups == [("git", "/usr/bin:/bin")]
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_real_catalogue_caddy_policy_selection_and_fingerprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    environment: str,
) -> None:
    import hashlib

    root = Path(__file__).resolve().parents[1]
    caddy = "deploy/Caddyfile.production" if environment == "production" else "deploy/Caddyfile"
    expected = {ops.DEFAULT_SOURCES, "docs/deploy/OPERATIONAL_SIGNALS.md", caddy}
    expected |= (
        {
            "deploy/PRODUCTION.md",
            "deploy/docker-compose.production.yaml",
            "deploy/docker-compose.production.selfhosted.yaml",
        }
        if environment == "production"
        else {"docs/deploy/STAGING.md", "deploy/docker-compose.staging.yaml"}
    )
    before = ops.build_report(root, environment=environment, service="app", repo_sha=SHA, now=NOW)
    fingerprints = {row["path"]: row["sha256"] for row in before["sources"]}
    assert set(fingerprints) == expected
    assert fingerprints[caddy] == hashlib.sha256((root / caddy).read_bytes()).hexdigest()
    assert [
        row["configuration"] for row in before["surfaces"][0]["references"] if row["path"] == caddy
    ] == ["shared" if environment == "production" else "staging"]
    for path in expected:
        copied = tmp_path / path
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes((root / path).read_bytes())
    policy = tmp_path / caddy
    policy.write_bytes(policy.read_bytes() + b"\n# synthetic policy revision\n")
    after = ops.build_report(
        tmp_path, environment=environment, service="app", repo_sha=SHA, now=NOW
    )
    assert before["repo_sha"] == after["repo_sha"] == SHA
    assert {
        row["path"] for row in after["sources"] if row["sha256"] != fingerprints[row["path"]]
    } == {caddy}
    policy.unlink()
    monkeypatch.setattr(ops, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    assert ops.main(["--environment", environment, "--service", "app", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


@pytest.mark.parametrize("service", ["app", "database", "prometheus"])
@pytest.mark.parametrize("configuration", ["managed_default", "selfhosted_alternative"])
def test_alternate_index_requires_each_production_configuration(
    repository: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    service: str,
    configuration: str,
) -> None:
    data = json.loads((repository / ops.DEFAULT_SOURCES).read_text())
    data["sources"].extend(
        {
            "environment": "production",
            "service": name,
            "configuration": "shared",
            "path": f"docs/production-{name}.md",
        }
        for name in ("app", "database", "prometheus")
    )
    alternate = repository / "docs/alternate.json"
    alternate.write_text(json.dumps(data))
    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    selections = [("production", service), ("production", "packages"), ("staging", "packages")]
    for environment, selected in selections:
        assert (
            ops.main(
                [
                    "--sources",
                    "docs/alternate.json",
                    "--environment",
                    environment,
                    "--service",
                    selected,
                    "--format",
                    "json",
                ]
            )
            == 0
        )
        captured = capsys.readouterr()
        assert captured.err == ""
        assert json.loads(captured.out)["surfaces"][0]["selected_configuration"] == "unknown"
    before = {(row["environment"], row["service"], row["configuration"]) for row in data["sources"]}
    removed = ("production", service, configuration)
    data["sources"] = [
        row
        for row in data["sources"]
        if (row["environment"], row["service"], row["configuration"]) != removed
    ]
    after = {(row["environment"], row["service"], row["configuration"]) for row in data["sources"]}
    assert before - after == {removed}
    assert {(row["environment"], row["service"]) for row in data["sources"]} == {
        (env, name) for env in ops.ENVIRONMENTS for name in ops.SERVICES
    }
    assert ("production", service, "shared") in after
    alternate.write_text(json.dumps(data))
    for environment, selected in selections:
        assert (
            ops.main(
                [
                    "--sources",
                    "docs/alternate.json",
                    "--environment",
                    environment,
                    "--service",
                    selected,
                    "--format",
                    "json",
                ]
            )
            == 2
        )
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == "ops-context-report: INVALID_REQUEST\n"


def test_real_catalogue_finite_production_alternatives() -> None:
    root = Path(__file__).resolve().parents[1]
    required = {
        ("production", name, config)
        for name in ("app", "database", "prometheus")
        for config in ("managed_default", "selfhosted_alternative")
    }
    data = json.loads((root / ops.DEFAULT_SOURCES).read_text())
    triples = {
        (row["environment"], row["service"], row["configuration"]) for row in data["sources"]
    }
    assert required <= triples
    assert ("production", "packages", "selfhosted_alternative") not in triples
    assert not any(
        env == "staging" and config in {"managed_default", "selfhosted_alternative"}
        for env, _, config in triples
    )
    for environment in ops.ENVIRONMENTS:
        result = ops.build_report(root, environment=environment, repo_sha=SHA, now=NOW)
        assert {surface["service"] for surface in result["surfaces"]} == set(ops.SERVICES)
        assert all(surface["selected_configuration"] == "unknown" for surface in result["surfaces"])


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_real_catalogue_prometheus_compose_owners(environment: str) -> None:
    root = Path(__file__).resolve().parents[1]
    result = ops.build_report(
        root, environment=environment, service="prometheus", repo_sha=SHA, now=NOW
    )
    assert {item["path"] for item in result["sources"] if "docker-compose" in item["path"]} == (
        {
            "deploy/docker-compose.production.yaml",
            "deploy/docker-compose.production.selfhosted.yaml",
        }
        if environment == "production"
        else {"deploy/docker-compose.staging.yaml"}
    )


def test_real_catalogue_staging_access_policy_fingerprint(tmp_path: Path) -> None:
    import hashlib

    root = Path(__file__).resolve().parents[1]
    hba = "deploy/postgres-pgvector/pg_hba.conf"
    before = ops.build_report(
        root, environment="staging", service="database", repo_sha=SHA, now=NOW
    )
    fingerprints = {item["path"]: item["sha256"] for item in before["sources"]}
    assert fingerprints[hba] == hashlib.sha256((root / hba).read_bytes()).hexdigest()
    assert {
        row["configuration"] for row in before["surfaces"][0]["references"] if row["path"] == hba
    } == {"staging"}
    production = report(root)
    assert hba not in {item["path"] for item in production["sources"]}
    for path in fingerprints:
        copied = tmp_path / path
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes((root / path).read_bytes())
    (tmp_path / hba).write_bytes((tmp_path / hba).read_bytes() + b"# synthetic policy revision\n")
    after = ops.build_report(
        tmp_path, environment="staging", service="database", repo_sha=SHA, now=NOW
    )
    changed = {item["path"]: item["sha256"] for item in after["sources"]}
    assert before["repo_sha"] == after["repo_sha"] == SHA
    assert {path for path in changed if changed[path] != fingerprints[path]} == {hba}
    assert before["surfaces"] == after["surfaces"]


def test_real_catalogue_production_image_only_selfhosted() -> None:
    root = Path(__file__).resolve().parents[1]
    result = report(root, service="database")
    surface = result["surfaces"][0]
    assert [
        row
        for row in surface["references"]
        if row["path"] == "deploy/postgres-pgvector/image-manifest.json"
    ] == [
        {
            "environment": "production",
            "service": "database",
            "configuration": "selfhosted_alternative",
            "path": "deploy/postgres-pgvector/image-manifest.json",
        }
    ]
    assert {"managed_default", "selfhosted_alternative"} <= {
        row["configuration"] for row in surface["references"]
    }
    assert surface["selected_configuration"] == "unknown"


def test_synthetic_packet_delivers_finite_ops_catalogue_bytes(
    repository: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from types import SimpleNamespace

    from scripts.orchestration import qoder_dispatch_bridge as bridge
    from scripts.orchestration import role_dispatch_bridge

    roles = [
        "agent-coordinator",
        "logic-agent",
        "philosophy-agent",
        "dev-operator",
        "architecture-specialist",
        "security-auditor",
    ]
    definitions = repository / ".cursor/agents"
    definitions.mkdir(parents=True)
    for role in roles:
        (definitions / f"{role}.md").write_text(
            f"---\nname: {role}\nreadonly: true\n---\nSynthetic {role} instructions.\n"
        )
    docs = repository / "docs/orchestration"
    docs.mkdir()
    paths = [ops.DEFAULT_SOURCES] + sorted(
        {
            row["path"]
            for row in json.loads((repository / ops.DEFAULT_SOURCES).read_text())["sources"]
        }
    )
    (docs / "AGENT_CONTEXT_MAP.md").write_text(
        "### Dev Operator (`dev-operator`)\n" + "\n".join(f"- `{path}`" for path in paths) + "\n"
    )
    (docs / "AGENT_ROUTING_GRAPH.md").write_text("# Synthetic routing\n")
    instruction = "tools/codex_skills/pulseplate-workflow/SKILL.md"
    (repository / instruction).parent.mkdir(parents=True)
    (repository / instruction).write_bytes(b"Explicit synthetic instruction\r\n")
    packet = {
        "native_subagent_bridge": {
            "primary": {"repo_agent_slug": "agent-coordinator"},
            "secondary": [
                {
                    "repo_agent_slug": role,
                    "execution_mode": (
                        "read_write" if role == "dev-operator" else "read_only_analysis"
                    ),
                }
                for role in roles[1:-1]
            ],
            "advisory": [],
            "reviewer": {"repo_agent_slug": "security-auditor"},
        },
        "required_context": [],
        "role_agent_dispatch_contract": {"runtime_implementation_owners": ["dev-operator"]},
        "task_packet_id": "synthetic-ops-not-an-authority-receipt",
    }
    packet_path = repository / "packet.json"
    packet_path.write_text(json.dumps(packet))
    monkeypatch.setattr(bridge, "REPO_ROOT", repository)
    monkeypatch.setattr(bridge, "_routing_graph", None)
    monkeypatch.setattr(
        bridge,
        "load_routing_graph",
        lambda path: {
            "ops": SimpleNamespace(
                cluster="ops",
                primary="dev-operator",
                secondary="architecture-specialist",
                reviewer="security-auditor",
            )
        },
    )
    assert (
        role_dispatch_bridge.main(
            [
                "--packet",
                str(packet_path),
                "--mode",
                "runtime",
                "--implementation-owner",
                "dev-operator",
                "--role-context-order",
                "4",
                "--instruction-file",
                instruction,
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_dispatch"]["role_slug"] == "dev-operator"
    assert payload["selected_dispatch"]["readonly"] is False
    context = payload["role_context"]
    assert context["complete"] is True
    delivered = {item["path"]: item["content"].encode("utf-8") for item in context["sources"]}
    for path in paths + [instruction]:
        assert delivered[path] == (repository / path).read_bytes()
    assert "packet.json" not in delivered
    assert context["dynamic_packet"]["content"].encode("utf-8") == packet_path.read_bytes()


def test_whole_report_offline_deterministic(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import socket
    from types import SimpleNamespace

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Network access forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(ops.shutil, "which", lambda name, *, path: "/synthetic/git")
    calls = []

    def run(args: list[str], **kwargs: object) -> SimpleNamespace:
        assert args == [
            "/synthetic/git",
            "--no-replace-objects",
            "rev-parse",
            "--verify",
            "HEAD^{commit}",
        ]
        assert kwargs["cwd"] == repository
        assert kwargs["timeout"] == 5
        assert "shell" not in kwargs
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=(SHA + "\n").encode(), stderr=b"")

    monkeypatch.setattr(ops.subprocess, "run", run)
    first = ops.build_report(repository, environment="production", now=NOW)
    assert len(calls) == 1
    second = ops.build_report(repository, environment="production", now=NOW)
    assert len(calls) == 2
    assert first == second


def test_runbook_cli_examples(
    repository: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import shlex

    monkeypatch.setattr(ops, "REPO_ROOT", repository)
    monkeypatch.setattr(ops, "git_revision", lambda root: SHA)
    (repository / "artifacts").mkdir()
    (repository / "artifacts/ops-observed.json").write_text(
        json.dumps({"schema_version": "ops-observed.v1", "observations": []})
    )
    text = (Path(__file__).resolve().parents[1] / "docs/deploy/OPERATIONAL_SIGNALS.md").read_text()
    examples = [
        shlex.split(line)[2:]
        for line in text.splitlines()
        if line.startswith("python scripts/ops/ops_context_report.py ")
    ]
    assert len(examples) == 3
    for args in examples:
        assert "--format" in args
        assert ops.main(args) == 0
        assert json.loads(capsys.readouterr().out)["authority"] == "none"


@pytest.mark.parametrize("change", ["duplicate", "missing_binding", "extra", "bad_schema"])
def test_invalid_index_grammar(repository: Path, change: str) -> None:
    path = repository / ops.DEFAULT_SOURCES
    data = json.loads(path.read_text())
    if change == "duplicate":
        data["sources"].append(data["sources"][0])
    elif change == "missing_binding":
        data["sources"] = [item for item in data["sources"] if item["service"] != "app"]
    elif change == "extra":
        data["sources"][0]["secret-marker"] = "secret-marker"
    else:
        data["schema_version"] = "unknown"
    path.write_text(json.dumps(data))
    with pytest.raises(ops.ReportError):
        report(repository)


def test_null_revision_and_impossible_calendar_date(repository: Path) -> None:
    path = write_observed(repository, [observation(repo_sha=None)])
    result = report(repository, observed=path, max_age_seconds=10**12)
    assert result["observations"][0]["revision_match"] is None
    assert "revision_not_supplied" in result["surfaces"][1]["unknowns"]
    write_observed(repository, [observation(observed_at="2026-02-30T12:00:00Z")])
    with pytest.raises(ops.ReportError):
        report(repository, observed=path, max_age_seconds=60)


def test_reader_exception_is_not_exposed(
    repository: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(ops, "REPO_ROOT", repository)

    def changed(*args: object, **kwargs: object) -> None:
        raise ops.reader.ContextBundleError("SOURCE_CHANGED", "secret-marker")

    monkeypatch.setattr(ops.reader, "read_repo_source", changed)
    assert ops.main(["--environment", "production", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "ops-context-report: INVALID_REQUEST\n"


def test_file_changed_during_read_fails_closed(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    path = write_observed(repository, [observation()])
    target = repository / path
    target_inode = target.stat().st_ino
    original = ops.reader.os.read
    mutated = False

    def read_then_change(descriptor: int, length: int) -> bytes:
        nonlocal mutated
        raw = original(descriptor, length)
        if not mutated and os.fstat(descriptor).st_ino == target_inode:
            mutated = True
            target.write_bytes(b" ")
        return raw

    monkeypatch.setattr(ops.reader.os, "read", read_then_change)
    with pytest.raises(ops.ReportError):
        report(repository, observed=path, max_age_seconds=60)
    assert mutated

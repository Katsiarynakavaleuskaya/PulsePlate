#!/usr/bin/env python3
"""Build local, offline operational reference reports without action authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess  # nosec B404: # native Git identity has no safer bounded stdlib replacement (remove-by: 2026-10-14, ref: PR-2397)
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Standalone entrypoint; ordinary package imports remain the only loading mechanism.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.orchestration import context_bundle as reader

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES = "docs/deploy/OPS_CONTEXT_SOURCES.json"
ENVIRONMENTS = ("production", "staging")
SERVICES = ("app", "database", "prometheus", "packages")
CONFIGURATIONS = ("managed_default", "selfhosted_alternative", "staging", "shared")
MAX_JSON_BYTES = 65536
MAX_RECORDS = 128
SYSTEM_GIT_PATH = "/usr/bin:/bin"
_SHA = re.compile(r"[0-9a-f]{40}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class ReportError(ValueError):
    """One bounded diagnostic, deliberately independent of supplied values."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ReportError("INVALID_ARGUMENTS")


def _require(condition: bool, code: str = "INVALID_INPUT") -> None:
    if not condition:
        raise ReportError(code)


def _keys(value: object, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReportError("INVALID_INPUT")
    _require(required <= value.keys() <= required | (optional or set()))
    return value


def _choice(value: object, choices: tuple[str, ...]) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ReportError("INVALID_INPUT")
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ReportError("INVALID_JSON")


def _json(raw: bytes) -> object:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            _require(depth <= 6)
            if isinstance(item, dict):
                pending.extend((key, depth + 1) for key in item)
                pending.extend((entry, depth + 1) for entry in item.values())
            elif isinstance(item, list):
                _require(len(item) <= MAX_RECORDS)
                pending.extend((entry, depth + 1) for entry in item)
            elif isinstance(item, str):
                _require(len(item) <= 512 and all(32 <= ord(char) <= 126 for char in item))
        return value
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ReportError("INVALID_JSON") from exc


def _read(
    root: Path,
    path: str,
    *,
    static: bool,
    metrics: reader.ContextIOMetrics,
    limit: int = MAX_JSON_BYTES,
) -> reader.SourceSnapshot:
    try:
        # canonical_repo_path intentionally rejects even an absolute path inside root.
        admitted = reader.canonical_repo_path(path)
        if static:
            reader.validate_static_source_path(admitted)
        return reader.read_repo_source(root, admitted, metrics=metrics, limit=limit)
    except reader.ContextBundleError as exc:
        raise ReportError("SOURCE_UNAVAILABLE") from exc


def _index(raw: bytes) -> list[dict[str, str]]:
    index = _keys(_json(raw), {"schema_version", "sources"})
    _require(index["schema_version"] == "ops-context-sources.v1")
    rows = index["sources"]
    _require(isinstance(rows, list) and 0 < len(rows) <= MAX_RECORDS)
    validated: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    bindings: set[tuple[str, str]] = set()
    for row in rows:
        item = _keys(row, {"environment", "service", "configuration", "path"})
        environment = _choice(item["environment"], ENVIRONMENTS)
        service = _choice(item["service"], SERVICES)
        configuration = _choice(item["configuration"], CONFIGURATIONS)
        _require(
            configuration
            in (
                ("managed_default", "selfhosted_alternative", "shared")
                if environment == "production"
                else ("staging", "shared")
            )
        )
        try:
            path = reader.canonical_repo_path(item["path"])
            reader.validate_static_source_path(path)
        except reader.ContextBundleError as exc:
            raise ReportError("INVALID_INDEX") from exc
        identity = (environment, service, configuration, path)
        _require(identity not in seen)
        seen.add(identity)
        bindings.add((environment, service))
        validated.append(
            {
                "environment": environment,
                "service": service,
                "configuration": configuration,
                "path": path,
            }
        )
    _require(bindings == {(env, service) for env in ENVIRONMENTS for service in SERVICES})
    _require(
        {"managed_default", "selfhosted_alternative"}
        <= {
            row["configuration"]
            for row in rows
            if row["environment"] == "production" and row["service"] == "database"
        }
    )
    return validated


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ReportError("INVALID_INPUT")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ReportError("INVALID_TIMESTAMP") from exc


def _observations(raw: bytes, now: datetime, window: int, repo_sha: str) -> list[dict[str, Any]]:
    payload = _keys(_json(raw), {"schema_version", "observations"})
    _require(payload["schema_version"] == "ops-observed.v1")
    rows = payload["observations"]
    _require(isinstance(rows, list) and len(rows) <= MAX_RECORDS)
    result = []
    for row in rows:
        item = _keys(
            row,
            {"environment", "service", "resource_id", "provenance", "observed_at", "repo_sha"},
            {"selected_config"},
        )
        environment = _choice(item["environment"], ENVIRONMENTS)
        _choice(item["service"], SERVICES)
        _choice(item["provenance"], ("operator_entry", "provider_export"))
        _require(
            isinstance(item["resource_id"], str)
            and bool(_IDENTIFIER.fullmatch(item["resource_id"]))
        )
        revision = item["repo_sha"]
        _require(revision is None or isinstance(revision, str) and bool(_SHA.fullmatch(revision)))
        if "selected_config" in item:
            _choice(
                item["selected_config"],
                (
                    ("managed_default", "selfhosted_alternative")
                    if environment == "production"
                    else ("staging",)
                ),
            )
        age = (now - _timestamp(item["observed_at"])).total_seconds()
        _require(age >= 0, "FUTURE_OBSERVATION")
        result.append(
            {
                **item,
                "age_seconds": age,
                "freshness": "fresh" if age <= window else "stale",
                "revision_match": None if revision is None else revision == repo_sha,
            }
        )
    return sorted(result, key=lambda item: json.dumps(item, sort_keys=True))


def git_revision(root: Path) -> str:
    """Resolve a commit using OS-managed Git, excluding caller PATH and Git overrides."""
    binary = shutil.which("git", path=SYSTEM_GIT_PATH)
    if binary is None or not Path(binary).is_absolute():
        raise ReportError("GIT_UNAVAILABLE")
    try:
        result = subprocess.run(  # nosec B603: # resolved fixed Git argv, explicit cwd/env, no shell, 5s bound and SHA validation (remove-by: 2026-10-14, ref: PR-2397)
            [binary, "--no-replace-objects", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=root,
            env={
                "PATH": SYSTEM_GIT_PATH,
                "LC_ALL": "C",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
            },
            capture_output=True,
            timeout=5,
            check=False,
        )
        revision = result.stdout.decode("ascii").removesuffix("\n")
        _require(result.returncode == 0 and bool(_SHA.fullmatch(revision)), "GIT_UNAVAILABLE")
        return revision
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise ReportError("GIT_UNAVAILABLE") from exc


def build_report(
    root: Path,
    *,
    environment: str,
    service: str | None = None,
    sources: str = DEFAULT_SOURCES,
    observed: str | None = None,
    max_age_seconds: int | None = None,
    now: datetime | None = None,
    repo_sha: str | None = None,
) -> dict[str, Any]:
    """Project selected references and supplied claims; never choose a live resource."""
    _choice(environment, ENVIRONMENTS)
    selected_services = SERVICES if service is None else (_choice(service, SERVICES),)
    _require(max_age_seconds is None or type(max_age_seconds) is int and 0 < max_age_seconds)
    _require(observed is None or max_age_seconds is not None)
    clock = now if now is not None else datetime.now(timezone.utc)
    _require(isinstance(clock, datetime) and clock.utcoffset() is not None, "INVALID_CLOCK")
    clock = clock.astimezone(timezone.utc)
    _require(isinstance(sources, str) and sources.endswith(".json"), "INVALID_INPUT_PATH")
    _require(
        observed is None or isinstance(observed, str) and observed.endswith(".json"),
        "INVALID_INPUT_PATH",
    )
    metrics = reader.ContextIOMetrics()
    index_snapshot = _read(root, sources, static=True, metrics=metrics)
    rows = _index(index_snapshot.raw)
    selected = [
        row
        for row in rows
        if row["environment"] == environment and row["service"] in selected_services
    ]
    selected.sort(
        key=lambda row: (SERVICES.index(row["service"]), row["configuration"], row["path"])
    )
    snapshots = {index_snapshot.path: index_snapshot}
    for path in sorted({row["path"] for row in selected}):
        if path not in snapshots:
            snapshots[path] = _read(
                root, path, static=True, metrics=metrics, limit=reader.MAX_SOURCE_BYTES
            )
        _require(
            sum(len(item.raw) for item in snapshots.values()) <= reader.MAX_TOTAL_SOURCE_BYTES,
            "SOURCE_LIMIT",
        )
    _require(len(snapshots) <= reader.MAX_SOURCES, "SOURCE_LIMIT")
    observed_snapshot = (
        None if observed is None else _read(root, observed, static=False, metrics=metrics)
    )
    revision = git_revision(root) if repo_sha is None else repo_sha
    _require(isinstance(revision, str) and bool(_SHA.fullmatch(revision)), "INVALID_REVISION")
    observations = []
    if observed_snapshot is not None:
        if max_age_seconds is None:
            raise ReportError("INVALID_INPUT")
        observations = _observations(observed_snapshot.raw, clock, max_age_seconds, revision)
    observations = [
        item
        for item in observations
        if item["environment"] == environment and item["service"] in selected_services
    ]
    surfaces = []
    for selected_service in selected_services:
        claims = [item for item in observations if item["service"] == selected_service]
        conflicts = [
            field
            for field in ("resource_id", "selected_config")
            if len({item[field] for item in claims if field in item}) > 1
        ]
        unknowns = ["live_identity_unverified", "selected_configuration_unverified"]
        if not claims:
            unknowns.append("no_supplied_observations")
        if any(item["freshness"] == "stale" for item in claims):
            unknowns.append("stale_observation")
        if any(item["revision_match"] is False for item in claims):
            unknowns.append("revision_mismatch")
        if any(item["revision_match"] is None for item in claims):
            unknowns.append("revision_not_supplied")
        if any("selected_config" not in item for item in claims):
            unknowns.append("selected_configuration_not_supplied")
        surfaces.append(
            {
                "service": selected_service,
                "references": [row for row in selected if row["service"] == selected_service],
                "live_identity": "unknown",
                "selected_configuration": "unknown",
                "unknowns": unknowns,
                "conflicts": conflicts,
            }
        )
    return {
        "schema_version": "ops-context-report.v1",
        "environment": environment,
        "repo_sha": revision,
        "reference_time": clock.isoformat().replace("+00:00", "Z"),
        "max_age_seconds": max_age_seconds,
        "authority": "none",
        "provider_authentication": "not_assessed",
        "configuration_verification": "not_assessed",
        "source_snapshot_scope": "per_file_acquired_bytes",
        "sources": [
            {"path": path, "sha256": hashlib.sha256(snapshot.raw).hexdigest()}
            for path, snapshot in sorted(snapshots.items())
        ],
        "observed_input": (
            None
            if observed_snapshot is None
            else {
                "path": observed_snapshot.path,
                "sha256": hashlib.sha256(observed_snapshot.raw).hexdigest(),
            }
        ),
        "observations": observations,
        "surfaces": surfaces,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    parser.add_argument("--service", choices=SERVICES)
    parser.add_argument("--sources", default=DEFAULT_SOURCES)
    parser.add_argument("--observed")
    parser.add_argument("--max-observation-age-seconds", dest="max_age_seconds", type=int)
    parser.add_argument("--format", choices=("json",), required=True)
    try:
        args = parser.parse_args(argv)
        options = vars(args)
        options.pop("format")
        result = build_report(REPO_ROOT, **options)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except ReportError:
        print("ops-context-report: INVALID_REQUEST", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

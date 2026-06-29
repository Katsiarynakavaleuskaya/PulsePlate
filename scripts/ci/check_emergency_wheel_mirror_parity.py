#!/usr/bin/env python3
"""Validate emergency wheel manifest parity against the approved private proxy."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import socket
import ssl
import sys
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse

try:
    from scripts.ci import check_private_python_proxy_health as proxy_health
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    import check_private_python_proxy_health as proxy_health

INDEX_ENV_VAR = proxy_health.INDEX_ENV_VAR
DEFAULT_MANIFEST = Path(__file__).with_name("emergency_python_wheels.json")
RETIRED_MARKER_GENERATED_AT = "2026-06-29"
ALLOWED_ARTIFACT_HOSTS = frozenset({"files.pythonhosted.org"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+!~-]*$")
ProjectPageCache = dict[str, tuple[int, bytes] | Exception]


class SimplePageValidationError(ValueError):
    """Validation failure with a stable parity reason code."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason


class _SimplePageHrefParser(HTMLParser):
    """Collect anchor hrefs from a Python Simple API project page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)


@dataclass(frozen=True)
class EmergencyWheelArtifact:
    package: str
    normalized_package: str
    version: str
    filename: str
    url: str
    sha256: str
    expires_at: date

    def safe_dict(self) -> dict[str, object]:
        return {
            "package": self.package,
            "normalized_package": self.normalized_package,
            "version": self.version,
            "filename": self.filename,
            "url": proxy_health.redact_url_credentials(self.url),
            "sha256": self.sha256,
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass(frozen=True)
class ArtifactResult:
    artifact: EmergencyWheelArtifact
    project_url: str
    ok: bool
    reason: str
    status: int | None = None
    bytes_read: int = 0
    detail: str = ""

    def safe_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "artifact": self.artifact.safe_dict(),
            "project_url": proxy_health.redact_url_credentials(self.project_url),
            "ok": self.ok,
            "reason": self.reason,
            "status": self.status,
            "bytes_read": self.bytes_read,
        }
        if self.detail:
            payload["detail"] = proxy_health.redact_text(self.detail)
        return payload


@dataclass(frozen=True)
class ParitySummary:
    ok: bool
    retired: bool
    manifest: str
    index_url: str
    host: str
    results: tuple[ArtifactResult, ...]
    errors: tuple[str, ...] = ()

    def safe_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "retired": self.retired,
            "manifest": self.manifest,
            "index_url": proxy_health.redact_url_credentials(self.index_url),
            "host": self.host,
            "artifact_count": len(self.results),
            "missing_count": sum(not result.ok for result in self.results),
            "error_count": len(self.errors),
            "results": [result.safe_dict() for result in self.results],
            "errors": [proxy_health.redact_text(error) for error in self.errors],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Emergency wheel manifest JSON file.",
    )
    parser.add_argument(
        "--index-url",
        default=os.environ.get(INDEX_ENV_VAR, ""),
        help=f"Private proxy simple-index root. Defaults to ${INDEX_ENV_VAR}.",
    )
    parser.add_argument(
        "--python-version",
        action="append",
        default=[],
        help="GitHub Ubuntu Python target version for wheel tag parity. Repeatable.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=4_000_000,
        help="Maximum private project page bytes to inspect.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser


def _parse_iso_date(value: object, *, field_name: str) -> date:
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise ValueError(f"{field_name} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD") from exc


def _normalize_sha256(artifact: dict[str, object], *, filename: str) -> str:
    direct_digest = artifact.get("sha256")
    digest_parts = artifact.get("sha256_parts")
    if isinstance(direct_digest, str) and direct_digest.strip():
        digest = direct_digest.strip().lower()
    elif (
        isinstance(digest_parts, list)
        and digest_parts
        and all(isinstance(part, str) and part.strip() for part in digest_parts)
    ):
        digest = "".join(digest_parts).strip().lower()
    else:
        raise ValueError(f"{filename}: missing sha256 or sha256_parts")
    if SHA256_RE.fullmatch(digest) is None:
        raise ValueError(f"{filename}: invalid sha256 digest")
    return digest


def _validate_artifact_url(url: str, *, filename: str) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if parsed.scheme != "https" or hostname not in ALLOWED_ARTIFACT_HOSTS:
        raise ValueError(f"{filename}: artifact URL host is not approved")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{filename}: inline artifact URL credentials are forbidden")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{filename}: artifact URL query and fragment are forbidden")
    if unquote(Path(parsed.path).name) != filename:
        raise ValueError(f"{filename}: artifact URL basename must match filename")


def _sha256_from_fragment(fragment: str) -> str | None:
    for field in fragment.split("&"):
        name, separator, value = field.partition("=")
        if separator != "=" or name.lower() != "sha256":
            continue
        digest = unquote(value).strip().lower()
        if SHA256_RE.fullmatch(digest) is None:
            raise SimplePageValidationError(
                "simple_page_sha256_invalid",
                "invalid sha256 fragment",
            )
        return digest
    return None


def _href_uses_private_proxy(*, href: str, project_url: str) -> bool:
    parsed_href = urlparse(href)
    if not parsed_href.scheme and not parsed_href.netloc:
        return True

    parsed_project = urlparse(project_url)
    if parsed_href.username is not None or parsed_href.password is not None:
        return False
    return (
        parsed_href.scheme == parsed_project.scheme
        and (parsed_href.hostname or "").rstrip(".").lower()
        == (parsed_project.hostname or "").rstrip(".").lower()
    )


def _exact_pin_wheel_sha256s(
    *,
    body: bytes,
    normalized_project: str,
    expected_version: str,
    project_url: str,
) -> dict[str, str | None]:
    """Return exact-version wheel filename -> advertised Simple API sha256."""

    parser = _SimplePageHrefParser()
    parser.feed(body.decode("utf-8", errors="ignore"))
    parser.close()
    expected_prefixes = (
        f"{normalized_project}-{expected_version}-".lower(),
        f"{normalized_project.replace('-', '_')}-{expected_version}-".lower(),
    )
    wheel_hashes: dict[str, str | None] = {}
    for href in parser.hrefs:
        parsed = urlparse(href)
        filename = unquote(Path(parsed.path).name).lower()
        if not filename.endswith(".whl") or not filename.startswith(expected_prefixes):
            continue
        if not _href_uses_private_proxy(href=href, project_url=project_url):
            raise SimplePageValidationError(
                "simple_page_artifact_host_unapproved",
                f"{filename}: Simple API href must be relative or same-host private proxy link",
            )
        digest = _sha256_from_fragment(parsed.fragment)
        if filename in wheel_hashes and wheel_hashes[filename] != digest:
            raise SimplePageValidationError(
                "simple_page_sha256_invalid",
                f"{filename}: conflicting sha256 fragments",
            )
        wheel_hashes[filename] = digest
    return wheel_hashes


def _target_python_coverage_errors(
    *,
    artifacts: Sequence[EmergencyWheelArtifact],
    target_python_versions: Sequence[str],
) -> tuple[str, ...]:
    target_tags = proxy_health.normalize_target_python_versions(target_python_versions)
    artifacts_by_pin: dict[tuple[str, str], list[EmergencyWheelArtifact]] = {}
    for artifact in artifacts:
        artifacts_by_pin.setdefault((artifact.normalized_package, artifact.version), []).append(
            artifact
        )

    errors: list[str] = []
    for (normalized_package, version), pinned_artifacts in sorted(artifacts_by_pin.items()):
        missing_targets = [
            target_tag
            for target_tag in target_tags
            if not any(
                proxy_health.wheel_is_compatible_with_targets(
                    artifact.filename,
                    target_python_versions=(target_tag,),
                )
                for artifact in pinned_artifacts
            )
        ]
        if missing_targets:
            errors.append(
                "python_target_coverage_missing: "
                f"{normalized_package}=={version} missing {','.join(missing_targets)}"
            )
    return tuple(errors)


def _manifest_is_retired_marker(payload: dict[str, object]) -> bool:
    reason = payload.get("reason")
    return (
        payload.get("artifacts") == []
        and payload.get("generated_at") == RETIRED_MARKER_GENERATED_AT
        and isinstance(reason, str)
        and reason.strip().lower().startswith("retired:")
    )


def load_manifest_artifacts(manifest: Path) -> tuple[bool, tuple[EmergencyWheelArtifact, ...]]:
    if not manifest.exists():
        raise FileNotFoundError(f"Emergency wheel manifest not found: {manifest}")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Emergency wheel manifest is not valid JSON: {manifest}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Emergency wheel manifest root must be a JSON object.")
    if payload.get("schema_version") != 1:
        raise ValueError("Emergency wheel manifest schema_version must equal 1.")

    artifacts = payload.get("artifacts")
    if artifacts == []:
        if _manifest_is_retired_marker(payload):
            return True, ()
        raise ValueError("Empty emergency wheel manifest is allowed only for the retired marker.")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Emergency wheel manifest must define an artifacts list.")

    default_expires_at = _parse_iso_date(payload.get("expires_at"), field_name="expires_at")
    normalized: list[EmergencyWheelArtifact] = []
    seen_filename_digests: dict[str, str] = {}
    today = date.today()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ValueError(f"artifacts[{index}] must be an object.")
        package = artifact.get("package")
        version = artifact.get("version")
        filename = artifact.get("filename")
        url = artifact.get("url")
        if not all(
            isinstance(value, str) and value.strip() for value in (package, version, filename, url)
        ):
            raise ValueError(
                f"artifacts[{index}] requires non-empty package, version, filename, and url"
            )
        package_text = str(package).strip()
        version_text = str(version).strip()
        filename_text = str(filename).strip()
        url_text = str(url).strip()
        if VERSION_RE.fullmatch(version_text) is None:
            raise ValueError(f"{filename_text}: invalid package version")
        if "/" in filename_text or "\\" in filename_text or not filename_text.endswith(".whl"):
            raise ValueError(f"{filename_text}: filename must be a wheel basename")
        normalized_package = proxy_health.normalize_project_name(package_text)
        sha256 = _normalize_sha256(artifact, filename=filename_text)
        _validate_artifact_url(url_text, filename=filename_text)
        expires_at_value = artifact.get("expires_at")
        expires_at = (
            default_expires_at
            if expires_at_value is None
            else _parse_iso_date(expires_at_value, field_name=f"artifacts[{index}].expires_at")
        )
        if expires_at < today:
            raise ValueError(f"{filename_text}: active emergency artifact is expired")
        previous_digest = seen_filename_digests.get(filename_text)
        if previous_digest is not None and previous_digest != sha256:
            raise ValueError(f"{filename_text}: conflicting sha256 digests")
        seen_filename_digests[filename_text] = sha256
        normalized.append(
            EmergencyWheelArtifact(
                package=package_text,
                normalized_package=normalized_package,
                version=version_text,
                filename=filename_text,
                url=url_text,
                sha256=sha256,
                expires_at=expires_at,
            )
        )
    return False, tuple(normalized)


def _result_from_error(
    *,
    artifact: EmergencyWheelArtifact,
    project_url: str,
    reason: str,
    detail: str,
    status: int | None = None,
) -> ArtifactResult:
    return ArtifactResult(
        artifact=artifact,
        project_url=project_url,
        ok=False,
        reason=reason,
        status=status,
        detail=detail,
    )


def probe_artifact(
    *,
    artifact: EmergencyWheelArtifact,
    index_url: str,
    timeout_seconds: float,
    max_bytes: int,
    authorization_header: str | None,
    target_python_versions: Sequence[str],
    page_cache: ProjectPageCache,
) -> ArtifactResult:
    project_url = proxy_health.project_page_url(index_url, artifact.normalized_package)
    try:
        cached_page = page_cache[project_url]
    except KeyError:
        try:
            cached_page = proxy_health.fetch_project_page(
                project_url,
                timeout_seconds=timeout_seconds,
                max_bytes=max_bytes,
                authorization_header=authorization_header,
            )
        except (HTTPError, TimeoutError, socket.timeout, URLError, ssl.SSLError, OSError) as exc:
            cached_page = exc
        page_cache[project_url] = cached_page

    try:
        if isinstance(cached_page, Exception):
            raise cached_page
        status, body = cached_page
    except HTTPError as exc:
        return _result_from_error(
            artifact=artifact,
            project_url=project_url,
            reason=proxy_health.classify_http_error(exc),
            status=exc.code,
            detail=f"HTTP {exc.code}",
        )
    except (TimeoutError, socket.timeout) as exc:
        return _result_from_error(
            artifact=artifact,
            project_url=project_url,
            reason="tls_or_connect_timeout",
            detail=str(exc),
        )
    except (URLError, ssl.SSLError, OSError) as exc:
        reason = (
            "tls_or_connect_timeout"
            if proxy_health._looks_like_timeout(exc)  # noqa: SLF001 - reuse stable helper.
            else "origin_unhealthy"
        )
        return _result_from_error(
            artifact=artifact,
            project_url=project_url,
            reason=reason,
            detail=str(exc),
        )

    if status in proxy_health.ORIGIN_UNHEALTHY_STATUSES:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="origin_unhealthy",
            status=status,
            bytes_read=len(body),
        )
    if status < 200 or status >= 300:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="http_error",
            status=status,
            bytes_read=len(body),
        )
    if len(body) > max_bytes:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="simple_page_truncated",
            status=status,
            bytes_read=len(body),
        )
    if proxy_health.body_has_cloudflare_origin_error(body):
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="origin_unhealthy",
            status=status,
            bytes_read=len(body),
            detail="Cloudflare origin-error marker found in body",
        )
    if not proxy_health.simple_page_has_project_link(
        body=body,
        normalized_project=artifact.normalized_package,
    ):
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="simple_page_malformed",
            status=status,
            bytes_read=len(body),
        )

    exact_wheels = proxy_health.exact_pin_wheel_filenames(
        body=body,
        normalized_project=artifact.normalized_package,
        expected_version=artifact.version,
    )
    if artifact.filename.lower() not in {filename.lower() for filename in exact_wheels}:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="mirror_lag_exact_filename_missing",
            status=status,
            bytes_read=len(body),
        )
    try:
        exact_wheel_hashes = _exact_pin_wheel_sha256s(
            body=body,
            normalized_project=artifact.normalized_package,
            expected_version=artifact.version,
            project_url=project_url,
        )
    except SimplePageValidationError as exc:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason=exc.reason,
            status=status,
            bytes_read=len(body),
            detail=str(exc),
        )
    mirrored_sha256 = exact_wheel_hashes.get(artifact.filename.lower())
    if mirrored_sha256 is None:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="simple_page_sha256_missing",
            status=status,
            bytes_read=len(body),
        )
    if mirrored_sha256 != artifact.sha256:
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="mirror_sha256_mismatch",
            status=status,
            bytes_read=len(body),
        )
    if not proxy_health.wheel_is_compatible_with_targets(
        artifact.filename,
        target_python_versions=target_python_versions,
    ):
        targets = ",".join(proxy_health.normalize_target_python_versions(target_python_versions))
        return ArtifactResult(
            artifact=artifact,
            project_url=project_url,
            ok=False,
            reason="incompatible_wheel",
            status=status,
            bytes_read=len(body),
            detail=f"not compatible with {targets}",
        )
    return ArtifactResult(
        artifact=artifact,
        project_url=project_url,
        ok=True,
        reason="ok",
        status=status,
        bytes_read=len(body),
    )


def check_parity(
    *,
    manifest: Path,
    index_url: str,
    timeout_seconds: float,
    max_bytes: int,
    target_python_versions: Sequence[str],
) -> ParitySummary:
    validated_index = proxy_health.validate_index_url(index_url)
    parsed_index = urlparse(validated_index)
    host = (parsed_index.hostname or "").rstrip(".").lower()
    retired, artifacts = load_manifest_artifacts(manifest)
    if retired:
        return ParitySummary(
            ok=True,
            retired=True,
            manifest=str(manifest),
            index_url=validated_index,
            host=host,
            results=(),
        )
    authorization_header = proxy_health.basic_auth_from_netrc(host)
    page_cache: ProjectPageCache = {}
    results = tuple(
        probe_artifact(
            artifact=artifact,
            index_url=validated_index,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
            authorization_header=authorization_header,
            target_python_versions=target_python_versions,
            page_cache=page_cache,
        )
        for artifact in artifacts
    )
    errors = _target_python_coverage_errors(
        artifacts=artifacts,
        target_python_versions=target_python_versions,
    )
    return ParitySummary(
        ok=all(result.ok for result in results) and not errors,
        retired=False,
        manifest=str(manifest),
        index_url=validated_index,
        host=host,
        results=results,
        errors=errors,
    )


def emit_text(summary: ParitySummary) -> None:
    print(
        "emergency_wheel_mirror_parity "
        f"ok={str(summary.ok).lower()} retired={str(summary.retired).lower()} "
        f"host={summary.host} artifacts={len(summary.results)} "
        f"missing={sum(not result.ok for result in summary.results)} "
        f"errors={len(summary.errors)} "
        f"index={proxy_health.redact_url_credentials(summary.index_url)}"
    )
    for result in summary.results:
        status = result.status if result.status is not None else "-"
        detail = f" detail={proxy_health.redact_text(result.detail)}" if result.detail else ""
        print(
            "artifact "
            f"package={result.artifact.normalized_package} version={result.artifact.version} "
            f"filename={result.artifact.filename} status={status} "
            f"bytes={result.bytes_read} reason={result.reason}{detail}"
        )
    for error in summary.errors:
        print(f"error {proxy_health.redact_text(error)}", file=sys.stderr)


def _error_summary(
    *,
    manifest: Path,
    index_url: str,
    error: str,
) -> ParitySummary:
    return ParitySummary(
        ok=False,
        retired=False,
        manifest=str(manifest),
        index_url=index_url,
        host=(urlparse(index_url).hostname or "").rstrip(".").lower(),
        results=(),
        errors=(error,),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        target_python_versions = proxy_health.normalize_target_python_versions(args.python_version)
        summary = check_parity(
            manifest=args.manifest,
            index_url=args.index_url,
            timeout_seconds=args.timeout_seconds,
            max_bytes=args.max_bytes,
            target_python_versions=target_python_versions,
        )
    except Exception as exc:  # noqa: BLE001 - CLI must return redacted diagnostics.
        summary = _error_summary(
            manifest=args.manifest,
            index_url=args.index_url,
            error=f"{type(exc).__name__}: {exc}",
        )
    if args.format == "json":
        print(json.dumps(summary.safe_dict(), sort_keys=True))
    else:
        emit_text(summary)
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

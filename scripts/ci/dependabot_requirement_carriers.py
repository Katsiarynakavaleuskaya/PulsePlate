#!/usr/bin/env python3
"""Canonical path and content class for Dependabot Python requirement carriers.

The repository config fixes the Dependabot update directory at ``/``.  The
pinned upstream Python fetcher snapshot declared below inspects ``.txt`` and
``.in`` files at the repository root and one directory below it.  This module
freezes that snapshot's path and content grammar so discovery is neither a
basename allowlist nor a prose-matching approximation.

Newer upstream revisions are outside this snapshot claim.  Path or content
grammar drift requires a separate reviewed revalidation and contract-version
bump, not another carrier exception or fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePath, PurePosixPath
import re
import shutil
import stat
import subprocess  # nosec B404: read-only Git index query has no safe in-process API (remove-by: 2026-10-31, ref: PR-2181)

DEPENDABOT_REQUIREMENT_SUFFIXES = frozenset({".in", ".txt"})
DEPENDABOT_REQUIREMENT_MAX_DEPTH = 1
DEPENDABOT_REQUIREMENT_MAX_BYTES = 500_000
DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS = 4096
DEPENDABOT_REQUIREMENTS_NAME_FRAGMENT = "requirements"
DEPENDABOT_REQUIREMENT_DIRECTIVE_PREFIXES = ("-r ", "-c ", "-e ", "--")
GIT_BINARY = shutil.which("git")
GIT_SOURCE_SET_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class DependabotRequirementCarrierUpstreamSnapshot:
    """Immutable identity for the validated upstream carrier snapshot."""

    contract_version: str
    upstream_repository_url: str
    upstream_commit_sha: str
    shared_file_fetcher_source_path: str
    requirement_parser_source_path: str


DEPENDABOT_REQUIREMENT_CARRIER_UPSTREAM_SNAPSHOT = DependabotRequirementCarrierUpstreamSnapshot(
    contract_version="dependabot-python-requirement-carriers/v1",
    upstream_repository_url="https://github.com/dependabot/dependabot-core",
    upstream_commit_sha="7936a8ab913935a937365279b3f44a1740117929",  # pragma: allowlist secret
    shared_file_fetcher_source_path=("python/lib/dependabot/python/shared_file_fetcher.rb"),
    requirement_parser_source_path=("python/lib/dependabot/python/requirement_parser.rb"),
)

_REQUIREMENTS_MANIFEST_BASENAME_RE = re.compile(
    r"^requirements(?:-[a-z0-9][a-z0-9-]*)?\.(?:in|txt)$"
)
# Frozen translation of RequirementParser::VALID_REQ_TXT_REQUIREMENT from
# DEPENDABOT_REQUIREMENT_CARRIER_UPSTREAM_SNAPSHOT.
_UPSTREAM_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?"
_UPSTREAM_EXTRA = r"[A-Za-z0-9_.-]+"
_UPSTREAM_COMPARISON = r"(?:===|==|>=|<=|<|>|~=|!=)"
_UPSTREAM_VERSION = (
    r"(?:[1-9][0-9]*!)?[0-9]+[A-Za-z0-9_.*-]*" r"(?:\+[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)?"
)
_UPSTREAM_REQUIREMENT = rf"{_UPSTREAM_COMPARISON}\s*\\?\s*v?{_UPSTREAM_VERSION}"
_UPSTREAM_REQUIREMENTS = rf"{_UPSTREAM_REQUIREMENT}" rf"(?:\s*,\s*\\?\s*{_UPSTREAM_REQUIREMENT})*"
_UPSTREAM_HASH = r"--hash=(?:.*?):(?:.*?)(?=\s|\\|$)"
_UPSTREAM_HASHES = rf"{_UPSTREAM_HASH}(?:\s*\\?\s*{_UPSTREAM_HASH})*"
_UPSTREAM_PYTHON_STRING_CHARACTER = r"[A-Za-z0-9\s().{}\-_*\#:;/\?\[\]!~`@\$%\^&=\+|<>]"
_UPSTREAM_PYTHON_STRING = (
    rf"(?:'(?:{_UPSTREAM_PYTHON_STRING_CHARACTER}|\")*'"
    rf'|"(?:{_UPSTREAM_PYTHON_STRING_CHARACTER}|\')*")'
)
_UPSTREAM_MARKER_ENVIRONMENT_VARIABLE = (
    r"(?:python_version|python_full_version|os_name|sys_platform|"
    r"platform_release|platform_system|platform_version|platform_machine|"
    r"platform_python_implementation|implementation_name|"
    r"implementation_version)"
)
_UPSTREAM_MARKER_OPERATOR = rf"\s*(?:{_UPSTREAM_COMPARISON}|\s*in|\s*not\s*in)"
_UPSTREAM_MARKER_VARIABLE = (
    rf"\s*(?:{_UPSTREAM_MARKER_ENVIRONMENT_VARIABLE}|" rf"{_UPSTREAM_PYTHON_STRING})"
)
_UPSTREAM_MARKER_EXPRESSION_ONE = (
    rf"{_UPSTREAM_MARKER_VARIABLE}" rf"{_UPSTREAM_MARKER_OPERATOR}" rf"{_UPSTREAM_MARKER_VARIABLE}"
)
_UPSTREAM_MARKER_EXPRESSION = (
    rf"(?:{_UPSTREAM_MARKER_EXPRESSION_ONE}|\(\s*|\s*\)|" rf"\s+and\s+|\s+or\s+)+"
)
_UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN = (
    rf"^\s*\\?\s*{_UPSTREAM_NAME}"
    rf"\s*\\?\s*(?:\[\s*{_UPSTREAM_EXTRA}"
    rf"(?:\s*,\s*{_UPSTREAM_EXTRA})*\s*\])?"
    rf"\s*\\?\s*\(?(?:{_UPSTREAM_REQUIREMENTS})?\)?"
    rf"\s*\\?\s*"
)
_UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN = (
    _UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN + rf"(?:;\s*{_UPSTREAM_MARKER_EXPRESSION})?"
    rf"\s*\\?\s*(?:{_UPSTREAM_HASHES})?"
    r"\s*(?:#+\s*.*)?$"
)
# The release prefix and its following version class both accept digits, while
# whitespace repetitions throughout the grammar overlap adjacent components.
# Make every whitespace repetition possessive so an invalid candidate cannot
# trigger exponential redistribution inside the repeated marker expression.
# Counts pin the exact frozen translation locations: grammar drift must fail
# closed instead of silently hardening a different language.
_HARDENING_TRANSFORMATIONS = (
    (r"[0-9]+[A-Za-z0-9_.*-]*", r"[0-9]++[A-Za-z0-9_.*-]*"),
    (r"\s*", r"\s*+"),
    (r"\s+", r"\s++"),
)
_UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN_SHA256 = (
    "d6c2ad19356670da7befa66ae40913b500c811b748c8227f156ca69ac6ed90f6"  # pragma: allowlist secret
)
_UPSTREAM_VALID_REQUIREMENT_LINE_HARDENING_COUNTS = (2, 34, 4)
_UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN_SHA256 = (
    "ec2bb91014b6a206a143f5a81242c4a78effc5bac962e47e3517d43cfb124112"  # pragma: allowlist secret
)
_UPSTREAM_REQUIREMENT_BEFORE_MARKER_HARDENING_COUNTS = (2, 19, 0)


def _harden_upstream_requirement_pattern(
    pattern: str,
    *,
    expected_sha256: str,
    expected_counts: tuple[int, int, int],
) -> str:
    """Apply the frozen bounded-time rewrites or reject grammar drift."""

    observed_counts = tuple(
        pattern.count(source) for source, _replacement in _HARDENING_TRANSFORMATIONS
    )
    if observed_counts != expected_counts:
        raise RuntimeError("pinned requirement grammar hardening locations drifted")
    pattern_digest = hashlib.sha256(pattern.encode("ascii")).hexdigest()
    if pattern_digest != expected_sha256:
        raise RuntimeError("pinned requirement grammar identity drifted")
    hardened = pattern
    for source, replacement in _HARDENING_TRANSFORMATIONS:
        hardened = hardened.replace(source, replacement)
    return hardened


_UPSTREAM_VALID_REQUIREMENT_LINE_RE = re.compile(
    _harden_upstream_requirement_pattern(
        _UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN,
        expected_sha256=_UPSTREAM_VALID_REQUIREMENT_LINE_PATTERN_SHA256,
        expected_counts=_UPSTREAM_VALID_REQUIREMENT_LINE_HARDENING_COUNTS,
    ),
    flags=re.ASCII,
)
_UPSTREAM_REQUIREMENT_BEFORE_MARKER_RE = re.compile(
    _harden_upstream_requirement_pattern(
        _UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN,
        expected_sha256=_UPSTREAM_REQUIREMENT_BEFORE_MARKER_PATTERN_SHA256,
        expected_counts=_UPSTREAM_REQUIREMENT_BEFORE_MARKER_HARDENING_COUNTS,
    ),
    flags=re.ASCII,
)
_MARKER_VARIABLE_LINEAR = rf"(?:{_UPSTREAM_MARKER_ENVIRONMENT_VARIABLE}|{_UPSTREAM_PYTHON_STRING})"
_MARKER_EXPRESSION_ONE_LINEAR_RE = re.compile(
    rf"{_MARKER_VARIABLE_LINEAR}\s*+"
    rf"(?:{_UPSTREAM_COMPARISON}|in|not\s*+in)\s*+"
    rf"{_MARKER_VARIABLE_LINEAR}",
    flags=re.ASCII,
)
_ASCII_WHITESPACE = " \t\r\n\v\f"


def _scan_pinned_marker_family(marker: str) -> int | None:
    """Return the continuation offset for one bounded marker atom sequence."""

    cursor = 0
    atom_count = 0
    preceding_atom: str | None = None
    # The caller enforces the 4096-character line budget. Every accepted atom
    # advances ``cursor`` and the first rejected atom breaks, so this scan is
    # linear in the already-bounded marker length and never calls the raw regex.
    while cursor < len(marker):
        whitespace_start = cursor
        while cursor < len(marker) and marker[cursor] in _ASCII_WHITESPACE:
            cursor += 1
        expression = _MARKER_EXPRESSION_ONE_LINEAR_RE.match(marker, cursor)
        if expression is not None:
            cursor = expression.end()
            atom_count += 1
            preceding_atom = "expression"
            continue
        if cursor < len(marker) and marker[cursor] in "()":
            parenthesis = marker[cursor]
            if (
                parenthesis == "("
                and whitespace_start < cursor
                and preceding_atom not in (None, "open-parenthesis", "boolean")
            ):
                cursor = whitespace_start
                break
            cursor += 1
            atom_count += 1
            preceding_atom = "open-parenthesis" if parenthesis == "(" else "close-parenthesis"
            continue
        if preceding_atom == "boolean" and cursor - whitespace_start == 1:
            for boolean_operator in ("and", "or"):
                operator_end = cursor + len(boolean_operator)
                if (
                    marker.startswith(boolean_operator, cursor)
                    and operator_end < len(marker)
                    and marker[operator_end] in _ASCII_WHITESPACE
                ):
                    return None
        for boolean_operator in ("and", "or"):
            operator_end = cursor + len(boolean_operator)
            if (
                whitespace_start < cursor
                and not (preceding_atom == "boolean" and cursor - whitespace_start < 2)
                and marker.startswith(boolean_operator, cursor)
                and operator_end < len(marker)
                and marker[operator_end] in _ASCII_WHITESPACE
            ):
                cursor = operator_end
                atom_count += 1
                preceding_atom = "boolean"
                break
        else:
            cursor = whitespace_start
            break

    if atom_count == 0:
        return None
    return cursor


def _matches_pinned_marker_ambiguity(raw_line: str) -> bool:
    """Recognize the bounded raw marker family without whitespace backtracking."""

    marker_delimiter = raw_line.find(";")
    if marker_delimiter < 0:
        return False
    if _UPSTREAM_REQUIREMENT_BEFORE_MARKER_RE.fullmatch(raw_line[:marker_delimiter]) is None:
        return False

    marker = raw_line[marker_delimiter + 1 :]
    continuation_offset = _scan_pinned_marker_family(marker)
    if continuation_offset is None:
        return False
    continuation_probe = (
        raw_line[: marker_delimiter + 1] + ' python_version == "3"' + marker[continuation_offset:]
    )
    return _UPSTREAM_VALID_REQUIREMENT_LINE_RE.fullmatch(continuation_probe) is not None


RepoPath = str | PurePath


class DependabotRequirementDiscoveryError(RuntimeError):
    """Fail-closed signal for an unclassifiable repository tree."""

    def __init__(self, relative_path: RepoPath) -> None:
        self.relative_path = normalize_repo_relative_path(relative_path)
        super().__init__(
            "Dependabot requirement carrier discovery could not inspect " "the repository tree"
        )


def normalize_repo_relative_path(path: RepoPath) -> PurePosixPath:
    """Return a stable repository-relative POSIX path."""

    normalized = str(path).removeprefix("./")
    return PurePosixPath(normalized)


def is_dependabot_requirement_candidate_path(path: RepoPath) -> bool:
    """Return whether the configured updater can discover ``path`` by shape."""

    normalized = normalize_repo_relative_path(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        return False
    if not normalized.parts:
        return False
    return (
        len(normalized.parts) <= DEPENDABOT_REQUIREMENT_MAX_DEPTH + 1
        and normalized.suffix in DEPENDABOT_REQUIREMENT_SUFFIXES
    )


def is_protected_python_dependency_text_path(path: RepoPath) -> bool:
    """Preserve broad requirements protection plus exact carrier discovery."""

    normalized = normalize_repo_relative_path(path)
    return _REQUIREMENTS_MANIFEST_BASENAME_RE.fullmatch(
        normalized.name
    ) is not None or is_dependabot_requirement_candidate_path(normalized)


def is_dependabot_requirement_carrier_text(
    path: RepoPath,
    text: str,
) -> bool:
    """Recognize the exact content class accepted by the pinned snapshot.

    Before classification, every newline-delimited record must fit the shared
    line budget; over-bound input is unclassifiable and fails closed. The pinned
    shared-file-fetcher snapshot accepts any remaining valid-encoding candidate
    with ``requirements`` in its name. For other candidates, every line must be
    blank, a comment, a supported pip directive, or match the pinned
    requirement-parser snapshot.
    """

    normalized = normalize_repo_relative_path(path)
    # Ruby String#lines uses the newline record separator. Python splitlines()
    # also splits on vertical-tab and Unicode separators, which would widen the
    # accepted class by turning one invalid upstream line into multiple lines.
    raw_lines = text.split("\n")
    if any(len(raw_line) > DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS for raw_line in raw_lines):
        raise DependabotRequirementDiscoveryError(normalized)
    if DEPENDABOT_REQUIREMENTS_NAME_FRAGMENT in normalized.as_posix():
        return True
    for raw_line in raw_lines:
        stripped = raw_line.strip(" \t\r\n\v\f\0")
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(DEPENDABOT_REQUIREMENT_DIRECTIVE_PREFIXES):
            continue
        if _UPSTREAM_VALID_REQUIREMENT_LINE_RE.fullmatch(
            raw_line
        ) or _matches_pinned_marker_ambiguity(raw_line):
            continue
        return False
    return True


def _open_directory_descriptor(
    path: str | Path,
    *,
    relative_path: str | Path,
    dir_fd: int | None = None,
    expected_identity: tuple[int, int] | None = None,
) -> int:
    """Open one directory without following its final path component."""

    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags, dir_fd=dir_fd)
    except OSError as exc:
        raise DependabotRequirementDiscoveryError(relative_path) from exc
    try:
        opened_stat = os.fstat(descriptor)
    except OSError as exc:
        os.close(descriptor)
        raise DependabotRequirementDiscoveryError(relative_path) from exc
    opened_identity = (opened_stat.st_dev, opened_stat.st_ino)
    if not stat.S_ISDIR(opened_stat.st_mode) or (
        expected_identity is not None and opened_identity != expected_identity
    ):
        os.close(descriptor)
        raise DependabotRequirementDiscoveryError(relative_path)
    return descriptor


def _entry_stat(
    descriptor: int,
    name: str,
    *,
    relative_path: str | Path,
) -> os.stat_result:
    """Stat one descriptor-anchored entry without following symlinks."""

    try:
        return os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except OSError as exc:
        raise DependabotRequirementDiscoveryError(relative_path) from exc


def _read_regular_utf8_candidate_at(
    parent_descriptor: int,
    name: str,
    relative_path: Path,
    expected_stat: os.stat_result,
) -> str | None:
    """Read one bounded at-rest candidate through its pinned parent."""

    normalized = normalize_repo_relative_path(relative_path)
    if not is_dependabot_requirement_candidate_path(normalized) or normalized.name != name:
        return None
    if not stat.S_ISREG(expected_stat.st_mode):
        return None
    if expected_stat.st_size > DEPENDABOT_REQUIREMENT_MAX_BYTES:
        return None

    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError:
        return None
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            return None
        if (opened_stat.st_dev, opened_stat.st_ino) != (
            expected_stat.st_dev,
            expected_stat.st_ino,
        ):
            return None
        if opened_stat.st_size > DEPENDABOT_REQUIREMENT_MAX_BYTES:
            return None
        with os.fdopen(descriptor, "rb", closefd=False) as candidate_file:
            payload = candidate_file.read(DEPENDABOT_REQUIREMENT_MAX_BYTES + 1)
    except OSError:
        return None
    finally:
        os.close(descriptor)
    if len(payload) > DEPENDABOT_REQUIREMENT_MAX_BYTES:
        return None
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _record_candidate(
    carriers: set[str],
    *,
    parent_descriptor: int,
    name: str,
    relative_path: Path,
    expected_stat: os.stat_result,
) -> None:
    """Classify one candidate while its parent descriptor remains pinned."""

    text = _read_regular_utf8_candidate_at(
        parent_descriptor,
        name,
        relative_path,
        expected_stat,
    )
    normalized = normalize_repo_relative_path(relative_path).as_posix()
    if text is None or is_dependabot_requirement_carrier_text(relative_path, text):
        carriers.add(normalized)


def _run_git_bytes(repo_root: Path, *args: str) -> bytes:
    """Run one fixed Git query with an absolute executable and bytes output."""

    if GIT_BINARY is None:
        raise DependabotRequirementDiscoveryError(".")
    git_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        result = subprocess.run(  # nosec B603: resolved Git binary with fixed read-only argv (remove-by: 2026-10-31, ref: PR-2181)
            [GIT_BINARY, "-C", os.fspath(repo_root), *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            env=git_env,
            text=False,
            timeout=GIT_SOURCE_SET_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise DependabotRequirementDiscoveryError(".") from exc
    if not isinstance(result.stdout, bytes):
        raise DependabotRequirementDiscoveryError(".")
    return result.stdout


def _git_index_source_paths(repo_root: Path) -> tuple[PurePosixPath, ...]:
    """Return the exact Git-index path set for one repository top level."""

    try:
        resolved_repo_root = repo_root.resolve(strict=True)
    except OSError as exc:
        raise DependabotRequirementDiscoveryError(".") from exc

    top_level_payload = _run_git_bytes(repo_root, "rev-parse", "--show-toplevel")
    if (
        not top_level_payload.endswith(b"\n")
        or b"\0" in top_level_payload
        or b"\n" in top_level_payload[:-1]
    ):
        raise DependabotRequirementDiscoveryError(".")
    try:
        reported_top_level = Path(os.fsdecode(top_level_payload[:-1])).resolve(strict=True)
    except OSError as exc:
        raise DependabotRequirementDiscoveryError(".") from exc
    if reported_top_level != resolved_repo_root:
        raise DependabotRequirementDiscoveryError(".")

    index_payload = _run_git_bytes(
        repo_root,
        "ls-files",
        "--cached",
        "--full-name",
        "-z",
    )
    if index_payload and not index_payload.endswith(b"\0"):
        raise DependabotRequirementDiscoveryError(".")

    source_paths: set[PurePosixPath] = set()
    raw_paths = index_payload.split(b"\0")
    for raw_path in raw_paths[:-1] if index_payload else ():
        if not raw_path:
            raise DependabotRequirementDiscoveryError(".")
        normalized = normalize_repo_relative_path(os.fsdecode(raw_path))
        if normalized.is_absolute() or not normalized.parts or ".." in normalized.parts:
            raise DependabotRequirementDiscoveryError(normalized)
        source_paths.add(normalized)
    return tuple(sorted(source_paths, key=PurePosixPath.as_posix))


def _record_git_index_candidate(
    carriers: set[str],
    *,
    root_descriptor: int,
    relative_path: PurePosixPath,
) -> None:
    """Classify one indexed candidate through descriptor-anchored path lookup."""

    parent_descriptor = root_descriptor
    child_descriptor: int | None = None
    try:
        if len(relative_path.parts) == 2:
            directory_name = relative_path.parts[0]
            directory_stat = _entry_stat(
                root_descriptor,
                directory_name,
                relative_path=directory_name,
            )
            child_descriptor = _open_directory_descriptor(
                directory_name,
                relative_path=directory_name,
                dir_fd=root_descriptor,
                expected_identity=(directory_stat.st_dev, directory_stat.st_ino),
            )
            parent_descriptor = child_descriptor

        filesystem_path = Path(*relative_path.parts)
        candidate_name = relative_path.parts[-1]
        candidate_stat = _entry_stat(
            parent_descriptor,
            candidate_name,
            relative_path=filesystem_path,
        )
        _record_candidate(
            carriers,
            parent_descriptor=parent_descriptor,
            name=candidate_name,
            relative_path=filesystem_path,
            expected_stat=candidate_stat,
        )
    finally:
        if child_descriptor is not None:
            os.close(child_descriptor)


def discover_dependabot_requirement_carriers(
    repo_root: Path,
) -> set[str]:
    """Return carriers from the Git-index source set and pinned content class."""

    carriers: set[str] = set()
    candidate_paths = tuple(
        path
        for path in _git_index_source_paths(repo_root)
        if is_dependabot_requirement_candidate_path(path)
    )
    root_descriptor = _open_directory_descriptor(repo_root, relative_path=".")
    try:
        for relative_path in candidate_paths:
            _record_git_index_candidate(
                carriers,
                root_descriptor=root_descriptor,
                relative_path=relative_path,
            )
    finally:
        os.close(root_descriptor)
    return carriers

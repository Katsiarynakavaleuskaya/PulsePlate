#!/usr/bin/env python3
"""Validate the production-governed Dependabot intake policy."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
import fnmatch
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, NoReturn

from packaging.requirements import InvalidRequirement, Requirement
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_python_dependency_surfaces import (
    DEPENDENCY_SURFACES,
    registered_dependabot_requirement_carriers,
)
from scripts.ci.dependabot_requirement_carriers import (
    DEPENDABOT_REQUIREMENT_MAX_LINE_CHARS as MAX_REQUIREMENT_LINE_CHARS,
    DependabotRequirementDiscoveryError,
    discover_dependabot_requirement_carriers,
)

CONFIG_PATH = Path(".github/dependabot.yml")
SHADOW_CONFIG_PATH = Path(".github/dependabot.yaml")
CONSTRAINTS_PATH = Path("constraints.txt")
REGISTRY_NAME = "python-index"
REGISTRY_AUTH_KEYS = ("username", "pass" + "word")
REGISTRY_CONFIG = {
    "type": "python-index",
    "url": "https://packages.pulseplate.app/root/pulseplate/+simple/",
    REGISTRY_AUTH_KEYS[0]: "${{secrets.DEVPI_DEPENDABOT_USER}}",
    REGISTRY_AUTH_KEYS[1]: "${{secrets.DEVPI_DEPENDABOT_PASSWORD}}",
    "replaces-base": True,
}
EXPECTED_COOLDOWN = {
    "default-days": 7,
    "semver-major-days": 30,
    "semver-minor-days": 7,
    "semver-patch-days": 3,
}
EXPECTED_GITHUB_ACTIONS_COOLDOWN = {"default-days": 7}
EXPECTED_GROUPS: dict[str, dict[str, tuple[str, ...] | str]] = {
    "runtime-security-sensitive": {
        "patterns": (
            "cryptography",
            "requests",
            "urllib3",
            "certifi",
            "pillow",
            "python-multipart",
            "mako",
            "setuptools",
        ),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "runtime-web": {
        "patterns": (
            "fastapi",
            "starlette",
            "uvicorn",
            "pydantic*",
            "httpx",
            "openai",
            "python-dotenv",
            "slowapi",
            "tenacity",
            "click",
            "email-validator",
            "nh3",
        ),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "runtime-database": {
        "patterns": ("sqlalchemy", "alembic", "psycopg*", "aiosqlite", "greenlet"),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "runtime-observability": {
        "patterns": ("opentelemetry-*", "prometheus-client"),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "runtime-rendering": {
        "patterns": ("reportlab", "matplotlib", "numpy", "pygments"),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "test-quality": {
        "patterns": (
            "pytest*",
            "coverage",
            "hypothesis",
            "faker",
            "httpx2",
            "diff-cover",
            "flake8",
            "marshmallow",
            "msgpack",
            "mypy",
            "ruff",
            "black",
            "types-pyyaml",
            "yamllint",
            "sourcery",
        ),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "supply-chain-tools": {
        "patterns": (
            "pip-tools",
            "pip-audit",
            "pre-commit",
            "bandit",
            "detect-secrets",
            "distlib",
            "cyclonedx-python-lib",
        ),
        "update-types": ("minor", "patch"),
        "applies-to": "version-updates",
    },
    "optional-rag-patches": {
        "patterns": ("pgvector", "fastembed"),
        "update-types": ("patch",),
        "applies-to": "version-updates",
    },
    "offline-data-patches": {
        "patterns": ("pandas", "pyarrow"),
        "update-types": ("patch",),
        "applies-to": "version-updates",
    },
}
FORBIDDEN_UPDATE_KEYS = {
    "allow",
    "ignore",
    "exclude-paths",
    "target-branch",
    "multi-ecosystem-group",
}
NON_PYTHON_FORBIDDEN_AUTHORITY_KEYS = FORBIDDEN_UPDATE_KEYS | {
    "groups",
    "registries",
    "labels",
    "assignees",
    "reviewers",
    "milestone",
    "auto-merge",
    "automerge",
    "approve",
    "auto-approve",
    "approvers",
}
EXTERNAL_CODE_EXECUTION_KEY = "insecure-external-code-execution"
EXPECTED_UPDATE_EXACT_VALUES: dict[str, object] = {
    "package-ecosystem": "pip",
    "directory": "/",
    "registries": [REGISTRY_NAME],
    "schedule": {"interval": "weekly"},
    "open-pull-requests-limit": 4,
    "commit-message": {"prefix": "deps", "include": "scope"},
}
EXPECTED_UPDATE_KEYS = set(EXPECTED_UPDATE_EXACT_VALUES) | {"cooldown", "groups"}
EXPECTED_COMMON_UPDATE_EXACT_VALUES: dict[str, object] = {
    "schedule": {"interval": "weekly"},
    "open-pull-requests-limit": 1,
    "commit-message": {"prefix": "deps", "include": "scope"},
}


@dataclass(frozen=True)
class UpdaterContract:
    """One statically typed closed-world updater contract."""

    scope_key: str
    scope_paths: tuple[str, ...]
    exact_values: Mapping[str, object]
    keys: frozenset[str]
    cooldown: Mapping[str, object]


EXPECTED_UPDATE_CONTRACTS: dict[str, UpdaterContract] = {
    "pip": UpdaterContract(
        scope_key="directory",
        scope_paths=("/",),
        exact_values=EXPECTED_UPDATE_EXACT_VALUES,
        keys=frozenset(EXPECTED_UPDATE_KEYS),
        cooldown=EXPECTED_COOLDOWN,
    ),
    "npm": UpdaterContract(
        scope_key="directories",
        scope_paths=("/", "/frontend"),
        exact_values={
            "package-ecosystem": "npm",
            **EXPECTED_COMMON_UPDATE_EXACT_VALUES,
        },
        keys=frozenset(
            {
                "package-ecosystem",
                "directories",
                *EXPECTED_COMMON_UPDATE_EXACT_VALUES,
                "cooldown",
            }
        ),
        cooldown=EXPECTED_COOLDOWN,
    ),
    "bundler": UpdaterContract(
        scope_key="directory",
        scope_paths=("/ios",),
        exact_values={
            "package-ecosystem": "bundler",
            **EXPECTED_COMMON_UPDATE_EXACT_VALUES,
        },
        keys=frozenset(
            {
                "package-ecosystem",
                "directory",
                *EXPECTED_COMMON_UPDATE_EXACT_VALUES,
                "cooldown",
            }
        ),
        cooldown=EXPECTED_COOLDOWN,
    ),
    "github-actions": UpdaterContract(
        scope_key="directories",
        scope_paths=("/", "/.github/actions/*"),
        exact_values={
            "package-ecosystem": "github-actions",
            **EXPECTED_COMMON_UPDATE_EXACT_VALUES,
        },
        keys=frozenset(
            {
                "package-ecosystem",
                "directories",
                *EXPECTED_COMMON_UPDATE_EXACT_VALUES,
                "cooldown",
            }
        ),
        cooldown=EXPECTED_GITHUB_ACTIONS_COOLDOWN,
    ),
}
EXPECTED_UPDATER_ECOSYSTEMS = frozenset(EXPECTED_UPDATE_CONTRACTS)
ALL_EXPECTED_UPDATE_KEYS = frozenset(
    key for contract in EXPECTED_UPDATE_CONTRACTS.values() for key in contract.keys
)
SCOPE_KEYS = frozenset({"directory", "directories"})
BUSINESS_COLLATERAL_PACKAGE_PATH = Path("scripts/business_collateral/package.json")
BUSINESS_COLLATERAL_DEPENDENCY_KEYS = frozenset(
    {"dependencies", "devDependencies", "optionalDependencies", "peerDependencies"}
)
BUSINESS_COLLATERAL_LOCK_PATHS = (
    Path("scripts/business_collateral/package-lock.json"),
    Path("scripts/business_collateral/npm-shrinkwrap.json"),
    Path("scripts/business_collateral/yarn.lock"),
    Path("scripts/business_collateral/pnpm-lock.yaml"),
    Path("scripts/business_collateral/pnpm-lock.yml"),
    Path("scripts/business_collateral/bun.lock"),
    Path("scripts/business_collateral/bun.lockb"),
)
MAX_CONFIG_BYTES = 64 * 1024
MAX_BUSINESS_PACKAGE_BYTES = 16 * 1024
MAX_BUSINESS_JSON_INTEGER_DIGITS = 4300
MAX_YAML_TOKENS = 4096
MAX_YAML_NESTING = 32
MAX_REQUIREMENT_SOURCE_BYTES = 64 * 1024
MAX_REQUIREMENT_SOURCE_LINES = 4096
ALLOWED_REQUIREMENT_DIRECTIVES = {"-c requirements.txt"}
ALLOWED_LOCK_DIRECTIVES = {"requirements-all.txt": {"-r requirements.txt"}}
INPUT_UNREADABLE = "unreadable"
INPUT_NON_REGULAR = "non_regular"
INPUT_OVERSIZED = "oversized"
INPUT_INVALID_UTF8 = "invalid_utf8"
_YAML_CONTAINER_START_TOKENS = (
    yaml.tokens.FlowSequenceStartToken,
    yaml.tokens.FlowMappingStartToken,
    yaml.tokens.BlockSequenceStartToken,
    yaml.tokens.BlockMappingStartToken,
)
_YAML_CONTAINER_END_TOKENS = (
    yaml.tokens.FlowSequenceEndToken,
    yaml.tokens.FlowMappingEndToken,
    yaml.tokens.BlockEndToken,
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _error(key_path: str, message: str) -> str:
    return f"{CONFIG_PATH.as_posix()}:{key_path}:{message}"


def _sorted_keys(keys: Iterable[object]) -> list[object]:
    """Return heterogeneous YAML keys in a deterministic printable order."""

    return sorted(keys, key=lambda key: (type(key).__name__, repr(key)))


def _value_shape(value: object) -> str:
    """Describe untrusted YAML structurally without rendering its content."""

    if isinstance(value, Mapping):
        return f"mapping(len={len(value)})"
    if isinstance(value, list):
        return f"list(len={len(value)})"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def _exact_value_matches(actual: object, expected: object) -> bool:
    """Compare governed YAML values without Python's cross-type equality."""

    if type(actual) is not type(expected):
        return False
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping) or set(actual) != set(expected):
            return False
        return all(_exact_value_matches(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return False
        return all(
            _exact_value_matches(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    return actual == expected


def _safe_yaml_error_message(exc: yaml.YAMLError) -> str:
    """Describe YAML failures without rendering source buffers or scalar values."""

    problem = getattr(exc, "problem", None)
    if isinstance(exc, yaml.constructor.ConstructorError) and isinstance(problem, str):
        category = "duplicate key" if problem.startswith("duplicate key:") else "constructor error"
    else:
        category = exc.__class__.__name__
    mark = getattr(exc, "problem_mark", None)
    line = getattr(mark, "line", None)
    column = getattr(mark, "column", None)
    if isinstance(line, int) and isinstance(column, int):
        return f"{category} at line {line + 1}, column {column + 1}"
    return category


def _walk_mapping(
    value: object,
    path: str,
) -> Iterator[tuple[str, Mapping[object, object]]]:
    if isinstance(value, Mapping):
        yield path, value
        safe_keys = (
            set(ALL_EXPECTED_UPDATE_KEYS)
            | set(EXPECTED_GROUPS)
            | {
                "version",
                "registries",
                "updates",
                REGISTRY_NAME,
                *REGISTRY_CONFIG,
                "applies-to",
                "patterns",
                "update-types",
            }
            | NON_PYTHON_FORBIDDEN_AUTHORITY_KEYS
        )
        for key, child in value.items():
            key_component = key if isinstance(key, str) and key in safe_keys else "<mapping-value>"
            child_path = f"{path}.{key_component}" if path else key_component
            yield from _walk_mapping(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_mapping(child, f"{path}[{index}]")


def _yaml_structure_violation(text: str) -> str | None:
    """Return a bounded structural violation before constructing YAML objects."""

    nesting = 0
    for token_count, token in enumerate(
        yaml.scan(text, Loader=yaml.SafeLoader),
        start=1,
    ):
        if token_count > MAX_YAML_TOKENS:
            return f"YAML token count exceeds limit {MAX_YAML_TOKENS}"
        if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken)):
            return "YAML anchors and aliases are forbidden"
        if isinstance(token, _YAML_CONTAINER_START_TOKENS):
            nesting += 1
            if nesting > MAX_YAML_NESTING:
                return f"YAML nesting exceeds limit {MAX_YAML_NESTING}"
        elif isinstance(token, _YAML_CONTAINER_END_TOKENS):
            nesting -= 1
    return None


def _normalized_pattern(pattern: str) -> str:
    return re.sub(r"[-_.]+", "-", pattern.lower())


def _matches(package: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(package, _normalized_pattern(pattern))


def _source_error(relative_path: str | Path, location: str, message: str) -> str:
    return f"{Path(relative_path).as_posix()}:{location}:{message}"


def _read_bounded_regular_utf8(
    repo_root: Path,
    relative_path: str | Path,
    *,
    max_bytes: int,
) -> tuple[str | None, str | None]:
    """Read one immutable regular policy input through a bounded descriptor."""

    path = repo_root / relative_path
    try:
        path_stat = path.lstat()
    except OSError:
        return None, INPUT_UNREADABLE
    if not stat.S_ISREG(path_stat.st_mode):
        return None, INPUT_NON_REGULAR
    open_flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        file_descriptor = os.open(path, open_flags)
    except OSError:
        return None, INPUT_UNREADABLE
    try:
        descriptor_stat = os.fstat(file_descriptor)
        if not stat.S_ISREG(descriptor_stat.st_mode) or (
            descriptor_stat.st_dev,
            descriptor_stat.st_ino,
        ) != (path_stat.st_dev, path_stat.st_ino):
            return None, INPUT_NON_REGULAR
        if descriptor_stat.st_size > max_bytes:
            return None, INPUT_OVERSIZED
        with os.fdopen(file_descriptor, "rb", closefd=False) as policy_input:
            input_bytes = policy_input.read(max_bytes + 1)
    except OSError:
        return None, INPUT_UNREADABLE
    finally:
        os.close(file_descriptor)

    if len(input_bytes) > max_bytes:
        return None, INPUT_OVERSIZED
    try:
        return input_bytes.decode("utf-8"), None
    except UnicodeError:
        return None, INPUT_INVALID_UTF8


def _policy_input_error(
    relative_path: str | Path,
    failure: str,
    *,
    max_bytes: int,
) -> str:
    messages = {
        INPUT_UNREADABLE: "policy input could not be read",
        INPUT_NON_REGULAR: "policy input must be a regular non-symlink file",
        INPUT_OVERSIZED: f"policy input size exceeds limit {max_bytes} bytes",
        INPUT_INVALID_UTF8: "policy input must be UTF-8",
    }
    return _source_error(relative_path, "$", messages[failure])


def _strict_requirement_names_from_text(
    text: str,
    *,
    relative_path: str | Path,
    allowed_directives: set[str],
    direct_source: bool,
) -> tuple[set[str], list[str]]:
    """Parse one closed requirements grammar without silently skipped carriers."""

    lines = text.splitlines()
    if len(lines) > MAX_REQUIREMENT_SOURCE_LINES:
        return set(), [
            _source_error(
                relative_path,
                "$",
                f"line count exceeds limit {MAX_REQUIREMENT_SOURCE_LINES}",
            )
        ]

    names: set[str] = set()
    errors: list[str] = []
    for line_number, raw_line in enumerate(lines, start=1):
        if len(raw_line) > MAX_REQUIREMENT_LINE_CHARS:
            errors.append(
                _source_error(
                    relative_path,
                    str(line_number),
                    f"line length exceeds limit {MAX_REQUIREMENT_LINE_CHARS}",
                )
            )
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in allowed_directives:
            continue
        if stripped.startswith(("-", "--")):
            directive_message = (
                "unsupported requirement directive; only the canonical constraint is allowed"
                if direct_source
                else "unsupported lock directive"
            )
            errors.append(
                _source_error(
                    relative_path,
                    str(line_number),
                    directive_message,
                )
            )
            continue
        requirement_text = re.sub(r"\s+#.*$", "", stripped).rstrip()
        if requirement_text.endswith("\\"):
            errors.append(
                _source_error(
                    relative_path,
                    str(line_number),
                    "line continuations are forbidden; use one PEP 508 declaration per line",
                )
            )
            continue
        try:
            requirement = Requirement(requirement_text)
        except InvalidRequirement:
            errors.append(
                _source_error(
                    relative_path,
                    str(line_number),
                    "invalid single-line PEP 508 requirement declaration",
                )
            )
            continue
        if requirement.url is not None:
            errors.append(
                _source_error(
                    relative_path,
                    str(line_number),
                    "direct URL requirements are forbidden",
                )
            )
            continue
        names.add(_normalized_pattern(requirement.name))
    return names, errors


def _strict_requirement_names(
    repo_root: Path,
    relative_path: str | Path,
    *,
    allowed_directives: set[str],
    direct_source: bool,
) -> tuple[set[str], list[str]]:
    text, failure = _read_bounded_regular_utf8(
        repo_root,
        relative_path,
        max_bytes=MAX_REQUIREMENT_SOURCE_BYTES,
    )
    if failure is not None:
        return set(), [
            _policy_input_error(
                relative_path,
                failure,
                max_bytes=MAX_REQUIREMENT_SOURCE_BYTES,
            )
        ]
    if text is None:
        return set(), [
            _policy_input_error(
                relative_path,
                INPUT_UNREADABLE,
                max_bytes=MAX_REQUIREMENT_SOURCE_BYTES,
            )
        ]
    return _strict_requirement_names_from_text(
        text,
        relative_path=relative_path,
        allowed_directives=allowed_directives,
        direct_source=direct_source,
    )


def _known_packages(repo_root: Path) -> tuple[set[str], set[str], list[str]]:
    direct: set[str] = set()
    known: set[str] = set()
    errors: list[str] = []
    for surface in DEPENDENCY_SURFACES:
        if surface.source_file is not None:
            source_packages, source_errors = _strict_requirement_names(
                repo_root,
                surface.source_file,
                allowed_directives=ALLOWED_REQUIREMENT_DIRECTIVES,
                direct_source=True,
            )
            direct.update(source_packages)
            known.update(source_packages)
            errors.extend(source_errors)
        lock_packages, lock_errors = _strict_requirement_names(
            repo_root,
            surface.lockfile,
            allowed_directives=ALLOWED_LOCK_DIRECTIVES.get(surface.lockfile, set()),
            direct_source=False,
        )
        known.update(lock_packages)
        errors.extend(lock_errors)
    constraint_packages, constraint_errors = _strict_requirement_names(
        repo_root,
        CONSTRAINTS_PATH,
        allowed_directives=set(),
        direct_source=True,
    )
    direct.update(constraint_packages)
    known.update(constraint_packages)
    errors.extend(constraint_errors)
    return direct, known, errors


def _unknown_dependabot_requirement_carriers(repo_root: Path) -> list[str]:
    """Return accepted Dependabot carriers outside the closed ownership registry."""

    discovered = discover_dependabot_requirement_carriers(repo_root)
    return sorted(discovered - registered_dependabot_requirement_carriers())


def _validate_exact_mapping(
    *,
    actual: object,
    expected: Mapping[str, object],
    key_path: str,
    errors: list[str],
) -> None:
    if not isinstance(actual, Mapping):
        errors.append(_error(key_path, "must be a mapping"))
        return
    actual_keys = set(actual)
    expected_keys = set(expected)
    if actual_keys != expected_keys:
        errors.append(
            _error(
                key_path,
                f"keys must be exactly {_sorted_keys(expected_keys)!r}; "
                f"got key_count={len(actual_keys)}",
            )
        )
    for key, expected_value in expected.items():
        if key in actual and not _exact_value_matches(actual[key], expected_value):
            expected_description = (
                "configured secret reference"
                if key_path == f"registries.{REGISTRY_NAME}" and key in {"username", "password"}
                else repr(expected_value)
            )
            errors.append(
                _error(
                    f"{key_path}.{key}",
                    f"must be {expected_description}; got {_value_shape(actual[key])}",
                )
            )


def _validate_business_collateral_marker(repo_root: Path, errors: list[str]) -> None:
    """Require an explicit ownership decision before collateral becomes an npm surface."""

    package_text, failure = _read_bounded_regular_utf8(
        repo_root,
        BUSINESS_COLLATERAL_PACKAGE_PATH,
        max_bytes=MAX_BUSINESS_PACKAGE_BYTES,
    )
    if failure is not None:
        errors.append(
            _policy_input_error(
                BUSINESS_COLLATERAL_PACKAGE_PATH,
                failure,
                max_bytes=MAX_BUSINESS_PACKAGE_BYTES,
            )
        )
    elif package_text is None:
        errors.append(
            _policy_input_error(
                BUSINESS_COLLATERAL_PACKAGE_PATH,
                INPUT_UNREADABLE,
                max_bytes=MAX_BUSINESS_PACKAGE_BYTES,
            )
        )
    else:
        try:
            package_manifest = json.loads(
                package_text,
                parse_constant=_reject_nonstandard_json_constant,
                parse_int=_parse_bounded_json_integer,
            )
        except (json.JSONDecodeError, ValueError, RecursionError):
            errors.append(
                _source_error(
                    BUSINESS_COLLATERAL_PACKAGE_PATH,
                    "$",
                    "must be valid bounded JSON",
                )
            )
        else:
            if not isinstance(package_manifest, Mapping):
                errors.append(
                    _source_error(
                        BUSINESS_COLLATERAL_PACKAGE_PATH,
                        "$",
                        "dependency-free marker must be a mapping",
                    )
                )
            else:
                if not _exact_value_matches(package_manifest.get("type"), "commonjs"):
                    errors.append(
                        _source_error(
                            BUSINESS_COLLATERAL_PACKAGE_PATH,
                            "type",
                            "dependency-free marker must declare exact string 'commonjs'",
                        )
                    )
                for dependency_key in sorted(
                    BUSINESS_COLLATERAL_DEPENDENCY_KEYS.intersection(package_manifest)
                ):
                    errors.append(
                        _source_error(
                            BUSINESS_COLLATERAL_PACKAGE_PATH,
                            dependency_key,
                            "dependency ownership is not admitted for this marker",
                        )
                    )

    for lock_path in BUSINESS_COLLATERAL_LOCK_PATHS:
        candidate = repo_root / lock_path
        if candidate.exists() or candidate.is_symlink():
            errors.append(
                _source_error(
                    lock_path,
                    "$",
                    "adjacent lock requires a separate explicit updater ownership decision",
                )
            )


def _reject_nonstandard_json_constant(_constant: str) -> NoReturn:
    """Reject NaN and infinities without reflecting their untrusted spelling."""

    raise ValueError


def _parse_bounded_json_integer(raw_integer: str) -> int:
    """Parse one JSON integer within an explicit non-reflecting digit budget."""

    digits = raw_integer[1:] if raw_integer.startswith("-") else raw_integer
    if len(digits) > MAX_BUSINESS_JSON_INTEGER_DIGITS:
        raise ValueError
    return int(raw_integer)


def _scope_paths(
    *,
    update: Mapping[object, object],
    update_path: str,
    ecosystem: str,
    present_scope_keys: frozenset[str],
    errors: list[str],
) -> tuple[str, ...] | None:
    """Return one validated canonical scope without rendering untrusted values."""

    if len(present_scope_keys) != 1:
        errors.append(
            _error(
                update_path,
                "must define exactly one of 'directory' or 'directories'",
            )
        )
        return None

    scope_key = next(iter(present_scope_keys))
    raw_scope = update[scope_key]
    if scope_key == "directory":
        if not isinstance(raw_scope, str):
            errors.append(_error(f"{update_path}.directory", "must be a string"))
            return None
        paths = (raw_scope,)
    else:
        if not isinstance(raw_scope, list) or not raw_scope:
            errors.append(
                _error(
                    f"{update_path}.directories",
                    "must be a non-empty list of strings",
                )
            )
            return None
        if not all(isinstance(path, str) for path in raw_scope):
            errors.append(
                _error(
                    f"{update_path}.directories",
                    "must be a non-empty list of strings",
                )
            )
            return None
        paths = tuple(raw_scope)

    if len(set(paths)) != len(paths):
        errors.append(_error(f"{update_path}.{scope_key}", "duplicate paths are forbidden"))

    paths_are_canonical = True
    for index, path in enumerate(paths):
        path_location = (
            f"{update_path}.directory"
            if scope_key == "directory"
            else f"{update_path}.directories[{index}]"
        )
        has_wildcard = any(character in path for character in "*?[")
        path_parts = path[1:].split("/") if path.startswith("/") else []
        is_canonical = (
            bool(path)
            and path.startswith("/")
            and "\\" not in path
            and (path == "/" or not path.endswith("/"))
            and "//" not in path
            and (path == "/" or all(part not in {"", ".", ".."} for part in path_parts))
            and not any(character.isspace() or ord(character) < 32 for character in path)
        )
        if not is_canonical:
            errors.append(
                _error(
                    path_location,
                    "must be a canonical absolute repository directory",
                )
            )
            paths_are_canonical = False
        if has_wildcard and not (ecosystem == "github-actions" and path == "/.github/actions/*"):
            errors.append(
                _error(
                    path_location,
                    "wildcards are forbidden except the exact composite-action token",
                )
            )
            paths_are_canonical = False

    return paths if paths_are_canonical else None


def _validate_update_contract(
    *,
    repo_root: Path,
    update: Mapping[object, object],
    update_index: int,
    ecosystem: str,
    errors: list[str],
) -> tuple[str, ...] | None:
    """Validate one recognized updater against its finite local contract."""

    update_path = f"updates[{update_index}]"
    contract = EXPECTED_UPDATE_CONTRACTS[ecosystem]
    expected_keys = contract.keys
    if set(update) != expected_keys:
        errors.append(
            _error(
                update_path,
                f"keys must be exactly {_sorted_keys(expected_keys)!r}; "
                f"got key_count={len(update)}",
            )
        )

    for key, expected_value in contract.exact_values.items():
        if key in SCOPE_KEYS:
            continue
        actual_value = update.get(key)
        if not _exact_value_matches(actual_value, expected_value):
            errors.append(
                _error(
                    f"{update_path}.{key}",
                    f"must be exactly {expected_value!r}; got {_value_shape(actual_value)}",
                )
            )

    present_scope_keys = SCOPE_KEYS.intersection(update)
    paths = _scope_paths(
        update=update,
        update_path=update_path,
        ecosystem=ecosystem,
        present_scope_keys=present_scope_keys,
        errors=errors,
    )
    expected_scope_key = contract.scope_key
    expected_scope_paths = contract.scope_paths
    actual_scope_key = next(iter(present_scope_keys)) if len(present_scope_keys) == 1 else None
    if actual_scope_key != expected_scope_key:
        errors.append(
            _error(
                update_path,
                f"scope key must be exactly {expected_scope_key!r}",
            )
        )
    if paths is not None and (
        len(paths) != len(expected_scope_paths) or set(paths) != set(expected_scope_paths)
    ):
        errors.append(
            _error(
                f"{update_path}.{expected_scope_key}",
                f"scope must be exactly {sorted(expected_scope_paths)!r}",
            )
        )

    _validate_exact_mapping(
        actual=update.get("cooldown"),
        expected=contract.cooldown,
        key_path=f"{update_path}.cooldown",
        errors=errors,
    )

    if ecosystem == "pip":
        _validate_groups(
            repo_root=repo_root,
            groups=update.get("groups"),
            errors=errors,
            update_path=update_path,
        )
    return paths


def _validate_groups(
    *,
    repo_root: Path,
    groups: object,
    errors: list[str],
    update_path: str = "updates[0]",
) -> None:
    if not isinstance(groups, Mapping):
        errors.append(_error(f"{update_path}.groups", "must be a mapping"))
        return
    expected_names = set(EXPECTED_GROUPS)
    actual_names = set(groups)
    if actual_names != expected_names:
        errors.append(
            _error(
                f"{update_path}.groups",
                f"group names must be exactly {_sorted_keys(expected_names)!r}; "
                f"got group_count={len(actual_names)}",
            )
        )

    usable_groups: dict[str, tuple[str, ...]] = {}
    for group_name, expected in EXPECTED_GROUPS.items():
        key_path = f"{update_path}.groups.{group_name}"
        group = groups.get(group_name)
        if not isinstance(group, Mapping):
            errors.append(_error(key_path, "must be a mapping"))
            continue
        expected_keys = {"applies-to", "patterns", "update-types"}
        if set(group) != expected_keys:
            errors.append(
                _error(
                    key_path,
                    f"keys must be exactly {_sorted_keys(expected_keys)!r}; "
                    f"got key_count={len(group)}",
                )
            )
        for scalar_key in ("applies-to",):
            if not _exact_value_matches(group.get(scalar_key), expected[scalar_key]):
                errors.append(
                    _error(
                        f"{key_path}.{scalar_key}",
                        f"must be {expected[scalar_key]!r}; "
                        f"got {_value_shape(group.get(scalar_key))}",
                    )
                )
        for list_key in ("patterns", "update-types"):
            actual = group.get(list_key)
            expected_list = list(expected[list_key])
            if not _exact_value_matches(actual, expected_list):
                errors.append(
                    _error(
                        f"{key_path}.{list_key}",
                        f"must be {expected_list!r}; got {_value_shape(actual)}",
                    )
                )
        patterns = group.get("patterns")
        if (
            isinstance(patterns, list)
            and all(isinstance(pattern, str) for pattern in patterns)
            and _exact_value_matches(patterns, list(expected["patterns"]))
        ):
            usable_groups[group_name] = tuple(patterns)

    direct_packages, known_packages, source_errors = _known_packages(repo_root)
    errors.extend(source_errors)
    if source_errors:
        return
    for group_name, patterns in usable_groups.items():
        for pattern_index, pattern in enumerate(patterns):
            if pattern in {"*", "**"}:
                errors.append(
                    _error(
                        f"{update_path}.groups.{group_name}.patterns[{pattern_index}]",
                        "catch-all patterns are forbidden",
                    )
                )
            if not any(_matches(package, pattern) for package in known_packages):
                errors.append(
                    _error(
                        f"{update_path}.groups.{group_name}.patterns[{pattern_index}]",
                        f"pattern {pattern!r} matches no known source or lock package",
                    )
                )

    for package in sorted(known_packages):
        owners = [
            group_name
            for group_name, patterns in usable_groups.items()
            if any(_matches(package, pattern) for pattern in patterns)
        ]
        if len(owners) > 1:
            errors.append(
                _error(
                    f"groups.package-owner.{package}",
                    f"known package matches multiple groups: {owners!r}",
                )
            )
        if package in direct_packages and len(owners) != 1:
            errors.append(
                _error(
                    f"groups.package-owner.{package}",
                    f"direct package must match exactly one group; got {owners!r}",
                )
            )


def validate_repo(repo_root: Path) -> list[str]:
    """Return deterministic policy violations for ``repo_root``."""
    errors: list[str] = []
    config_path = repo_root / CONFIG_PATH
    shadow_path = repo_root / SHADOW_CONFIG_PATH
    if shadow_path.exists() or shadow_path.is_symlink():
        errors.append(f"{SHADOW_CONFIG_PATH.as_posix()}:$:shadow Dependabot config is forbidden")

    config_text, input_failure = _read_bounded_regular_utf8(
        repo_root,
        CONFIG_PATH,
        max_bytes=MAX_CONFIG_BYTES,
    )
    if input_failure is not None:
        failure_messages = {
            INPUT_UNREADABLE: "required config could not be read",
            INPUT_NON_REGULAR: "required config must be a regular non-symlink file",
            INPUT_OVERSIZED: f"config size exceeds limit {MAX_CONFIG_BYTES} bytes",
            INPUT_INVALID_UTF8: "invalid YAML: config must be UTF-8",
        }
        errors.append(_error("$", failure_messages[input_failure]))
        return errors
    if config_text is None:
        errors.append(_error("$", "required config could not be read"))
        return errors

    try:
        structure_violation = _yaml_structure_violation(config_text)
        if structure_violation is not None:
            errors.append(_error("$", structure_violation))
            return errors
        loader = UniqueKeyLoader(config_text)
        try:
            config = loader.get_single_data()
        finally:
            loader.dispose()
    except yaml.YAMLError as exc:
        errors.append(_error("$", f"invalid YAML: {_safe_yaml_error_message(exc)}"))
        return errors
    except RecursionError:
        errors.append(_error("$", "invalid YAML: recursion limit exceeded"))
        return errors
    if not isinstance(config, Mapping):
        errors.append(_error("$", "root must be a mapping"))
        return errors

    _validate_business_collateral_marker(repo_root, errors)

    for mapping_path, mapping in _walk_mapping(config, "$"):
        if EXTERNAL_CODE_EXECUTION_KEY in mapping:
            errors.append(
                _error(
                    f"{mapping_path}.{EXTERNAL_CODE_EXECUTION_KEY}",
                    "key is forbidden because external code must not receive "
                    "private registry credentials",
                )
            )

    try:
        unknown_carriers = _unknown_dependabot_requirement_carriers(repo_root)
    except DependabotRequirementDiscoveryError:
        errors.append(
            "dependabot.requirement-carriers:$:"
            "candidate discovery could not inspect the repository tree"
        )
        unknown_carriers = []
    if unknown_carriers:
        errors.append(
            "dependabot.requirement-carriers:$:"
            f"unregistered candidate carriers are forbidden: {unknown_carriers!r}"
        )

    if not _exact_value_matches(config.get("version"), 2):
        errors.append(
            _error(
                "version",
                f"must be 2; got {_value_shape(config.get('version'))}",
            )
        )
    if set(config) != {"version", "registries", "updates"}:
        errors.append(
            _error(
                "$",
                "root keys must be exactly ['registries', 'updates', 'version']; "
                f"got key_count={len(config)}",
            )
        )

    registries = config.get("registries")
    if not isinstance(registries, Mapping) or set(registries) != {REGISTRY_NAME}:
        errors.append(
            _error(
                "registries",
                f"must contain only {REGISTRY_NAME!r}; got {_value_shape(registries)}",
            )
        )
    else:
        _validate_exact_mapping(
            actual=registries[REGISTRY_NAME],
            expected=REGISTRY_CONFIG,
            key_path=f"registries.{REGISTRY_NAME}",
            errors=errors,
        )

    updates = config.get("updates")
    if not isinstance(updates, list):
        errors.append(_error("updates", "must be a list"))
        return errors
    if len(updates) != len(EXPECTED_UPDATER_ECOSYSTEMS):
        errors.append(
            _error(
                "updates",
                "must contain exactly four governed update blocks; " f"got {len(updates)}",
            )
        )

    observed: dict[str, list[tuple[int, tuple[str, ...] | None]]] = {}
    for update_index, update in enumerate(updates):
        update_path = f"updates[{update_index}]"
        if not isinstance(update, Mapping):
            errors.append(_error(update_path, "must be a mapping"))
            continue

        ecosystem_value = update.get("package-ecosystem")
        ecosystem = ecosystem_value if isinstance(ecosystem_value, str) else ""

        for mapping_path, mapping in _walk_mapping(update, update_path):
            for forbidden_key in sorted(FORBIDDEN_UPDATE_KEYS.intersection(mapping)):
                errors.append(
                    _error(
                        f"{mapping_path}.{forbidden_key}",
                        "key is forbidden by Mode A intake policy",
                    )
                )
            if ecosystem != "pip":
                for forbidden_key in sorted(
                    NON_PYTHON_FORBIDDEN_AUTHORITY_KEYS.intersection(mapping)
                    - FORBIDDEN_UPDATE_KEYS
                ):
                    errors.append(
                        _error(
                            f"{mapping_path}.{forbidden_key}",
                            "key is forbidden for bounded non-Python updater authority",
                        )
                    )

        if ecosystem not in EXPECTED_UPDATER_ECOSYSTEMS:
            errors.append(
                _error(
                    f"{update_path}.package-ecosystem",
                    "must be one of the four exact governed ecosystems; "
                    f"got {_value_shape(ecosystem_value)}",
                )
            )
            continue

        paths = _validate_update_contract(
            repo_root=repo_root,
            update=update,
            update_index=update_index,
            ecosystem=ecosystem,
            errors=errors,
        )
        observed.setdefault(ecosystem, []).append((update_index, paths))

    for ecosystem in sorted(EXPECTED_UPDATER_ECOSYSTEMS):
        occurrences = observed.get(ecosystem, [])
        if not occurrences:
            errors.append(
                _error(
                    "updates",
                    f"missing required {ecosystem!r} updater identity",
                )
            )
            continue
        if len(occurrences) > 1:
            errors.append(
                _error(
                    "updates",
                    f"duplicate {ecosystem!r} updater identity is forbidden",
                )
            )
            valid_path_sets = [set(paths) for _, paths in occurrences if paths is not None]
            if any(
                left.intersection(right)
                for left_index, left in enumerate(valid_path_sets)
                for right in valid_path_sets[left_index + 1 :]
            ):
                errors.append(
                    _error(
                        "updates",
                        f"overlapping {ecosystem!r} updater scopes are forbidden",
                    )
                )
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors = validate_repo(args.repo_root.resolve())
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"{CONFIG_PATH.as_posix()}:$:PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate the production-governed Python Dependabot intake policy."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator, Mapping
import fnmatch
from pathlib import Path
import re
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_python_dependency_surfaces import (
    DEPENDENCY_SURFACES,
    _requirement_package_names,
)

CONFIG_PATH = Path(".github/dependabot.yml")
SHADOW_CONFIG_PATH = Path(".github/dependabot.yaml")
REGISTRY_NAME = "python-index"
REGISTRY_CONFIG = {
    "type": "python-index",
    "url": "https://packages.pulseplate.app/root/pulseplate/+simple/",
    "username": "${{secrets.DEVPI_DEPENDABOT_USER}}",
    "password": "${{secrets.DEVPI_DEPENDABOT_PASSWORD}}",
    "replaces-base": True,
}
EXPECTED_COOLDOWN = {
    "default-days": 7,
    "semver-major-days": 30,
    "semver-minor-days": 7,
    "semver-patch-days": 3,
}
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
        "patterns": ("opentelemetry-*", "prometheus-client", "zipp"),
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
    "insecure-external-code-execution",
}
EXPECTED_UPDATE_EXACT_VALUES: dict[str, object] = {
    "package-ecosystem": "pip",
    "directory": "/",
    "registries": [REGISTRY_NAME],
    "schedule": {"interval": "weekly"},
    "open-pull-requests-limit": 4,
    "commit-message": {"prefix": "deps", "include": "scope"},
}
EXPECTED_UPDATE_KEYS = set(EXPECTED_UPDATE_EXACT_VALUES) | {"cooldown", "groups"}
MAX_CONFIG_BYTES = 64 * 1024
MAX_YAML_TOKENS = 4096
MAX_YAML_NESTING = 32
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
            EXPECTED_UPDATE_KEYS
            | set(EXPECTED_GROUPS)
            | {"applies-to", "patterns", "update-types"}
            | FORBIDDEN_UPDATE_KEYS
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


def _known_packages(repo_root: Path) -> tuple[set[str], set[str]]:
    direct: set[str] = set()
    known: set[str] = set()
    for surface in DEPENDENCY_SURFACES:
        if surface.source_file is not None:
            source_path = repo_root / surface.source_file
            if source_path.is_file():
                source_packages = _requirement_package_names(
                    repo_root,
                    surface.source_file,
                )
                direct.update(source_packages)
                known.update(source_packages)
        lock_path = repo_root / surface.lockfile
        if lock_path.is_file():
            known.update(_requirement_package_names(repo_root, surface.lockfile))
    return direct, known


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
        if key in actual and actual[key] != expected_value:
            errors.append(
                _error(
                    f"{key_path}.{key}",
                    f"must be {expected_value!r}; got {_value_shape(actual[key])}",
                )
            )


def _validate_groups(
    *,
    repo_root: Path,
    groups: object,
    errors: list[str],
) -> None:
    if not isinstance(groups, Mapping):
        errors.append(_error("updates[0].groups", "must be a mapping"))
        return
    expected_names = set(EXPECTED_GROUPS)
    actual_names = set(groups)
    if actual_names != expected_names:
        errors.append(
            _error(
                "updates[0].groups",
                f"group names must be exactly {_sorted_keys(expected_names)!r}; "
                f"got group_count={len(actual_names)}",
            )
        )

    usable_groups: dict[str, tuple[str, ...]] = {}
    for group_name, expected in EXPECTED_GROUPS.items():
        key_path = f"updates[0].groups.{group_name}"
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
            if group.get(scalar_key) != expected[scalar_key]:
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
            if actual != expected_list:
                errors.append(
                    _error(
                        f"{key_path}.{list_key}",
                        f"must be {expected_list!r}; got {_value_shape(actual)}",
                    )
                )
        patterns = group.get("patterns")
        if patterns == list(expected["patterns"]):
            usable_groups[group_name] = tuple(patterns)

    direct_packages, known_packages = _known_packages(repo_root)
    for group_name, patterns in usable_groups.items():
        for pattern_index, pattern in enumerate(patterns):
            if pattern in {"*", "**"}:
                errors.append(
                    _error(
                        f"updates[0].groups.{group_name}.patterns[{pattern_index}]",
                        "catch-all patterns are forbidden",
                    )
                )
            if not any(_matches(package, pattern) for package in known_packages):
                errors.append(
                    _error(
                        f"updates[0].groups.{group_name}.patterns[{pattern_index}]",
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
    if config_path.is_symlink():
        errors.append(_error("$", "required config must be a regular non-symlink file"))
        return errors
    if not config_path.is_file():
        errors.append(_error("$", "required config is missing"))
        return errors

    try:
        if config_path.stat().st_size > MAX_CONFIG_BYTES:
            errors.append(
                _error(
                    "$",
                    f"config size exceeds limit {MAX_CONFIG_BYTES} bytes",
                )
            )
            return errors
        config_text = config_path.read_text(encoding="utf-8")
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
    except UnicodeError:
        errors.append(_error("$", "invalid YAML: config must be UTF-8"))
        return errors
    except OSError:
        errors.append(_error("$", "invalid YAML: config could not be read"))
        return errors
    if not isinstance(config, Mapping):
        errors.append(_error("$", "root must be a mapping"))
        return errors

    if config.get("version") != 2:
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
    if len(updates) != 1:
        errors.append(
            _error(
                "updates",
                f"must contain exactly one governed update block; got {len(updates)}",
            )
        )
        return errors
    update = updates[0]
    update_path = "updates[0]"
    if not isinstance(update, Mapping):
        errors.append(_error(update_path, "must be a mapping"))
        return errors
    if set(update) != EXPECTED_UPDATE_KEYS:
        errors.append(
            _error(
                update_path,
                f"keys must be exactly {_sorted_keys(EXPECTED_UPDATE_KEYS)!r}; "
                f"got key_count={len(update)}",
            )
        )
    for key, expected_value in EXPECTED_UPDATE_EXACT_VALUES.items():
        actual_value = update.get(key)
        if actual_value != expected_value:
            errors.append(
                _error(
                    f"{update_path}.{key}",
                    f"must be exactly {expected_value!r}; got {_value_shape(actual_value)}",
                )
            )
    _validate_exact_mapping(
        actual=update.get("cooldown"),
        expected=EXPECTED_COOLDOWN,
        key_path=f"{update_path}.cooldown",
        errors=errors,
    )
    for mapping_path, mapping in _walk_mapping(update, update_path):
        for forbidden_key in sorted(FORBIDDEN_UPDATE_KEYS.intersection(mapping)):
            errors.append(
                _error(
                    f"{mapping_path}.{forbidden_key}",
                    "key is forbidden by Mode A intake policy",
                )
            )
    _validate_groups(repo_root=repo_root, groups=update.get("groups"), errors=errors)
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

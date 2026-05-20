"""Fail when the temporary Ruby jwt/Fastlane suppression can be removed.

The tracked Dependabot alert is blocked only while the latest safe Bundler
resolution keeps Fastlane on a `jwt < 3` dependency graph. This guard parses a
fresh `bundle lock --update fastlane jwt googleauth signet --print` result and
fails as soon as that blocker disappears or Bundler resolves the patched jwt
line.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess  # nosec B404: Bundler subprocess is required for fixed local resolver inspection (remove-by: 2026-08-31, ref: ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363)
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IOS_DIR = REPO_ROOT / "ios"
FIXED_JWT_FLOOR = "3.2.0"

_SPEC_RE = re.compile(r"^(?P<indent>\s*)(?P<name>[A-Za-z0-9_.-]+) \((?P<body>[^)]+)\)")
_VERSION_RE = re.compile(r"^\d+(?:\.\d+)*(?:\.[A-Za-z0-9_-]+)?$")
_CONSTRAINT_RE = re.compile(r"(?P<operator><=|>=|!=|=|~>|<|>)\s*(?P<version>[0-9][A-Za-z0-9_.-]*)")


@dataclass(frozen=True)
class BundlerEvidence:
    """Relevant pieces from Bundler's printed lockfile output."""

    versions: dict[str, str] = field(default_factory=dict)
    jwt_constraints: dict[str, str] = field(default_factory=dict)


def _version_key(version: str) -> tuple[tuple[int, ...], int]:
    """Return comparable numeric version plus prerelease rank.

    Prereleases sort below their corresponding final release. This is enough for
    the `jwt 3.2.0` floor this guard enforces and avoids a runtime dependency on
    packaging libraries in a CI bootstrap script.
    """
    numeric_parts: list[int] = []
    prerelease = False
    for item in re.split(r"[._-]", version):
        if item.isdigit():
            numeric_parts.append(int(item))
            continue
        prerelease = True
        break
    while len(numeric_parts) < 3:
        numeric_parts.append(0)
    return tuple(numeric_parts), 0 if prerelease else 1


def _version_at_least(version: str, floor: str) -> bool:
    return _version_key(version) >= _version_key(floor)


def _numeric_parts(version: str) -> list[int]:
    parts: list[int] = []
    for item in re.split(r"[._-]", version):
        if not item.isdigit():
            break
        parts.append(int(item))
    return parts or [0]


def _pessimistic_upper_bound(version: str) -> tuple[tuple[int, ...], int]:
    parts = _numeric_parts(version)
    if len(parts) <= 2:
        upper = [parts[0] + 1, 0, 0]
    else:
        upper = [parts[0], parts[1] + 1, 0]
    return tuple(upper), 1


def _constraint_blocks_fixed_jwt_floor(constraint: str, fixed_jwt_floor: str) -> bool:
    fixed_key = _version_key(fixed_jwt_floor)
    for match in _CONSTRAINT_RE.finditer(constraint):
        operator = match.group("operator")
        version = match.group("version")
        version_key = _version_key(version)
        if operator == "<" and not fixed_key < version_key:
            return True
        if operator == "<=" and not fixed_key <= version_key:
            return True
        if operator == "=" and fixed_key != version_key:
            return True
        if operator == "~>":
            lower_key = version_key
            upper_key = _pessimistic_upper_bound(version)
            if not (lower_key <= fixed_key < upper_key):
                return True
    return False


def parse_bundler_evidence(output: str) -> BundlerEvidence:
    """Parse package versions and direct jwt constraints from Bundler output."""
    target_packages = {"fastlane", "googleauth", "signet", "jwt"}
    versions: dict[str, str] = {}
    jwt_constraints: dict[str, str] = {}
    current_spec: str | None = None

    for raw_line in output.splitlines():
        match = _SPEC_RE.match(raw_line)
        if not match:
            continue

        indent = len(match.group("indent"))
        name = match.group("name")
        body = match.group("body")

        if indent == 4:
            current_spec = name
            if name in target_packages:
                first_token = body.split(",", 1)[0].strip()
                if _VERSION_RE.match(first_token):
                    versions[name] = first_token
            continue

        if indent == 6 and current_spec in {"fastlane", "googleauth", "signet"}:
            if name == "jwt":
                jwt_constraints[current_spec] = body.strip()

    return BundlerEvidence(versions=versions, jwt_constraints=jwt_constraints)


def evaluate_bundler_evidence(
    evidence: BundlerEvidence,
    *,
    fixed_jwt_floor: str = FIXED_JWT_FLOOR,
) -> list[str]:
    """Return errors when the suppression should no longer remain in place."""
    errors: list[str] = []

    jwt_version = evidence.versions.get("jwt")
    if jwt_version is None:
        errors.append("Bundler output did not include a resolved jwt version.")
    elif _version_at_least(jwt_version, fixed_jwt_floor):
        errors.append(
            f"Bundler now resolves jwt {jwt_version}, which is at or above "
            f"the patched floor {fixed_jwt_floor}; remove the Trivy suppression."
        )

    fastlane_version = evidence.versions.get("fastlane")
    fastlane_constraint = evidence.jwt_constraints.get("fastlane")
    if fastlane_version is None:
        errors.append("Bundler output did not include fastlane.")
    elif fastlane_constraint is None:
        errors.append(
            f"Fastlane {fastlane_version} no longer reports a direct jwt constraint; "
            "re-evaluate the lockfile and remove or update the suppression."
        )
    elif not _constraint_blocks_fixed_jwt_floor(fastlane_constraint, fixed_jwt_floor):
        errors.append(
            f"Fastlane {fastlane_version} no longer blocks jwt {fixed_jwt_floor} "
            f"({fastlane_constraint}); try resolving jwt >= {fixed_jwt_floor}."
        )

    return errors


def _run_bundler(ios_dir: Path) -> str:
    bundle_path = shutil.which("bundle")
    if bundle_path is None:
        raise RuntimeError("Bundler executable `bundle` was not found on PATH.")

    result = subprocess.run(  # nosec B603: argv uses resolved Bundler path and fixed lockfile inspection args only (remove-by: 2026-08-31, ref: ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363)
        [
            bundle_path,
            "lock",
            "--update",
            "fastlane",
            "jwt",
            "googleauth",
            "signet",
            "--print",
        ],
        cwd=ios_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Bundler resolver check failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resolver-output",
        type=Path,
        help="Path to captured `bundle lock --update fastlane jwt googleauth signet --print` output.",
    )
    parser.add_argument(
        "--ios-dir",
        type=Path,
        default=DEFAULT_IOS_DIR,
        help="iOS directory used when running Bundler directly.",
    )
    parser.add_argument(
        "--fixed-jwt-floor",
        default=FIXED_JWT_FLOOR,
        help="Patched jwt floor reported by GitHub/Trivy.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.resolver_output:
            output = args.resolver_output.read_text(encoding="utf-8")
        else:
            output = _run_bundler(args.ios_dir)
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    evidence = parse_bundler_evidence(output)
    errors = evaluate_bundler_evidence(evidence, fixed_jwt_floor=args.fixed_jwt_floor)
    if errors:
        print("ERROR: Ruby jwt/Fastlane unblock guard failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "OK: Ruby jwt remains blocked by Fastlane's jwt < 3 resolver graph; "
        "temporary suppression still requires monitoring."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

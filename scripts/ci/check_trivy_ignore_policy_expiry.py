from __future__ import annotations

import os
import re
from datetime import UTC, datetime, date
from pathlib import Path


# Allow trailing content after the date (e.g. "(manual removal)").
_EXPIRY_RE = re.compile(r"Suppression expires:\s*(\d{4}-\d{2}-\d{2})(?:\s|$)")


def _parse_expiry(path: Path) -> date:
    matches: list[date] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        found = _EXPIRY_RE.search(line)
        if found:
            matches.append(date.fromisoformat(found.group(1)))
    if not matches:
        raise ValueError(f"Missing 'Suppression expires: YYYY-MM-DD' in {path}")
    if len(matches) > 1:
        raise ValueError(
            f"Multiple 'Suppression expires: YYYY-MM-DD' entries found in {path}; "
            "expected exactly one expiry per policy file"
        )
    return matches[0]


def _resolve_policy_files(repo_root: Path) -> list[Path]:
    env_path = os.environ.get("TRIVY_IGNORE_POLICY_PATH", "").strip()
    if env_path:
        # Allow comma-separated list (mirrors trivy-action inputs style).
        paths = [p.strip() for p in env_path.split(",") if p.strip()]
        resolved: list[Path] = []
        for raw in paths:
            candidate = (repo_root / raw).resolve()
            if "*" in raw:
                resolved.extend(sorted(repo_root.glob(raw)))
            else:
                resolved.append(candidate)
        return resolved

    trivy_dir = repo_root / "trivy"
    return sorted(trivy_dir.glob("ignore-policy*.rego"))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    policy_files = _resolve_policy_files(repo_root)

    missing_files = [p for p in policy_files if not p.exists()]
    if missing_files:
        print("ERROR: Trivy ignore policy file(s) not found:")
        for p in missing_files:
            print(f"- {p}")
        return 1

    if not policy_files:
        print(
            "ERROR: No Trivy ignore policy files found. "
            "Set TRIVY_IGNORE_POLICY_PATH or add trivy/ignore-policy*.rego."
        )
        return 1

    today = datetime.now(UTC).date()
    failures: list[str] = []

    for policy_file in policy_files:
        try:
            expiry = _parse_expiry(policy_file)
        except ValueError as exc:
            failures.append(str(exc))
            continue

        if today > expiry:
            failures.append(
                f"Expired Trivy ignore policy: {policy_file} (expired {expiry}, today {today})"
            )

    if failures:
        print("ERROR: Trivy ignore policy expiry check failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

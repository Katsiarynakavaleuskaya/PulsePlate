from __future__ import annotations

import re
from datetime import UTC, datetime, date
from pathlib import Path


_EXPIRY_RE = re.compile(r"Suppression expires:\s*(\d{4}-\d{2}-\d{2})\s*$")


def _parse_expiry(path: Path) -> date:
    expiry: date | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _EXPIRY_RE.search(line)
        if match:
            expiry = date.fromisoformat(match.group(1))
            break
    if expiry is None:
        raise ValueError(f"Missing 'Suppression expires: YYYY-MM-DD' in {path}")
    return expiry


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    trivy_dir = repo_root / "trivy"

    if not trivy_dir.exists():
        return 0

    policy_files = sorted(trivy_dir.glob("ignore-policy*.rego"))
    if not policy_files:
        return 0

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

from __future__ import annotations

from datetime import date
from pathlib import Path
import re

from scripts.ci.check_trivy_ignore_policy_expiry import evaluate_policy_file

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "trivy" / "ignore-policy.rego"
TRIVYIGNORE_PATH = REPO_ROOT / ".trivyignore"
SECURITY_DOC_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-48962-perl-base.md"
BACKLOG_PATH = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"


def _policy_text() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def _cve_2026_48962_policy_block() -> str:
    text = _policy_text()
    match = re.search(
        r"# CVE-2026-48962 \(perl-base / IO::Compress\).*?(?=\n# CVE-|\Z)",
        text,
        flags=re.DOTALL,
    )
    assert match is not None, "missing CVE-2026-48962 perl-base Rego block"
    return match.group(0)


def test_trivy_policy_guard_accepts_unexpired_policy_and_review_dates(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        "\n".join(
            [
                "package trivy",
                "# Suppression expires: 2026-05-27 (manual removal)",
                "# Review-by: 2026-05-27 (manual removal)",
                "default ignore := false",
            ]
        ),
        encoding="utf-8",
    )

    assert evaluate_policy_file(policy, today=date(2026, 5, 19)) == []


def test_trivy_policy_guard_fails_stale_review_by_dates(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        "\n".join(
            [
                "package trivy",
                "# Suppression expires: 2026-05-27 (manual removal)",
                "# Review-by: 2026-05-18 (manual removal)",
                "default ignore := false",
            ]
        ),
        encoding="utf-8",
    )

    failures = evaluate_policy_file(policy, today=date(2026, 5, 19))

    assert failures == [
        f"Stale Trivy suppression review date: {policy}:3 "
        "(review-by 2026-05-18, today 2026-05-19)"
    ]


def test_trivy_policy_guard_still_rejects_multiple_file_expiry_markers(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        "\n".join(
            [
                "package trivy",
                "# Suppression expires: 2026-05-27 (manual removal)",
                "# Suppression expires: 2026-06-27 (manual removal)",
                "# Review-by: 2026-05-27 (manual removal)",
                "default ignore := false",
            ]
        ),
        encoding="utf-8",
    )

    failures = evaluate_policy_file(policy, today=date(2026, 5, 19))

    assert failures == [
        f"Multiple 'Suppression expires: YYYY-MM-DD' entries found in {policy}; "
        "expected exactly one expiry per policy file"
    ]


def test_trivy_policy_guard_reports_invalid_review_by_dates(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        "\n".join(
            [
                "package trivy",
                "# Suppression expires: 2026-05-27 (manual removal)",
                "# Review-by: 2026-13-99 (manual removal)",
                "default ignore := false",
            ]
        ),
        encoding="utf-8",
    )

    failures = evaluate_policy_file(policy, today=date(2026, 5, 19))

    assert failures == [
        f"Invalid 'Review-by' date in {policy}:3: 2026-13-99 (month must be in 1..12)"
    ]


def test_trivy_policy_guard_reports_invalid_file_expiry_dates(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        "\n".join(
            [
                "package trivy",
                "# Suppression expires: 2026-13-99 (manual removal)",
                "# Review-by: 2026-05-27 (manual removal)",
                "default ignore := false",
            ]
        ),
        encoding="utf-8",
    )

    failures = evaluate_policy_file(policy, today=date(2026, 5, 19))

    assert failures == [
        f"Invalid 'Suppression expires' date in {policy}:2: 2026-13-99 " "(month must be in 1..12)"
    ]


def test_cve_2026_48962_policy_is_exact_and_timeboxed() -> None:
    block = _cve_2026_48962_policy_block()

    assert "# Review-by: 2026-06-27 (manual removal)" in block
    assert 'input.VulnerabilityID == "CVE-2026-48962"' in block
    assert 'input.PkgName == "perl-base"' in block
    assert 'input.InstalledVersion == "5.36.0-7+deb12u3"' in block
    assert 'startswith(input.PkgID, "perl-base@5.36.0-7+deb12u3")' in block
    assert "contains(input.PkgID" not in block

    policy = _policy_text()
    assert len(re.findall(r"^# Suppression expires:", policy, flags=re.MULTILINE)) == 1


def test_cve_2026_48962_is_not_broadly_ignored_in_trivyignore() -> None:
    trivyignore = TRIVYIGNORE_PATH.read_text(encoding="utf-8")

    assert "CVE-2026-48962" not in trivyignore


def test_cve_2026_48962_doc_and_backlog_coupling() -> None:
    doc_text = SECURITY_DOC_PATH.read_text(encoding="utf-8")
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")

    assert "CVE-2026-48962" in doc_text
    assert "alert `#602`" in doc_text
    assert "policy disposition" in doc_text
    assert "Dockerfile:9" in doc_text
    assert ".github/workflows/build.yml:422" in doc_text

    ledger_start = backlog_text.index('<a id="ledger-p1-container-perl-cve-remediation"></a>')
    next_anchor = backlog_text.find("<a id=", ledger_start + 1)
    ledger_end = next_anchor if next_anchor != -1 else len(backlog_text)
    ledger_entry = backlog_text[ledger_start:ledger_end]

    assert "CVE-2026-48962" in ledger_entry
    assert "alert #602" in ledger_entry
    assert "trivy/ignore-policy.rego" in ledger_entry
    assert "docs/security/CVE-2026-48962-perl-base.md" in ledger_entry

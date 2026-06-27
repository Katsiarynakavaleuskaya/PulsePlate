from __future__ import annotations

from datetime import date
from pathlib import Path
import re

from scripts.ci.check_trivy_ignore_policy_expiry import evaluate_policy_file

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "trivy" / "ignore-policy.rego"
TRIVYIGNORE_PATH = REPO_ROOT / ".trivyignore"
SECURITY_DOC_48959_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-48959-perl-base.md"
SECURITY_DOC_48962_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-48962-perl-base.md"
SECURITY_DOC_8058_PATH = REPO_ROOT / "docs" / "security" / "CVE-2025-8058-glibc.md"
SECURITY_DOC_ARCHIVE_TAR_PATH = (
    REPO_ROOT / "docs" / "security" / "CVE-2026-archive-tar-perl-runtime-removal.md"
)
SECURITY_DOC_SQLITE_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-sqlite-runtime-removal.md"
SECURITY_DOC_GPGV_24882_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-24882-gpgv.md"
SECURITY_DOC_GPGV_24883_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-24883-gpgv.md"
SECURITY_DOC_FARADAY_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-54297-faraday-fastlane.md"
BACKLOG_PATH = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"

REMOVED_PERL_RUNTIME_CVES = (
    "CVE-2023-31484",
    "CVE-2023-31486",
    "CVE-2025-40909",
    "CVE-2026-48959",
    "CVE-2026-48962",
    "CVE-2026-9538",
    "CVE-2026-42497",
    "CVE-2026-8376",
    "CVE-2026-42496",
)
REMEDIATED_SQLITE_CVES = (
    "CVE-2025-7458",
    "CVE-2025-6965",
    "CVE-2025-29088",
    "CVE-2026-11822",
    "CVE-2026-11824",
)
REMOVED_PRODUCTION_TOOLING_CVES = (
    "CVE-2022-3219",
    "CVE-2026-24882",
    "CVE-2026-24883",
    "CVE-2025-68972",
    "CVE-2025-68973",
    "CVE-2025-9820",
    "CVE-2025-30258",
)


def _policy_text() -> str:
    return POLICY_PATH.read_text(encoding="utf-8")


def _ledger_perl_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index('<a id="ledger-p1-container-perl-cve-remediation"></a>')
    next_anchor = backlog_text.find("<a id=", ledger_start + 1)
    ledger_end = next_anchor if next_anchor != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


def _ledger_gpgv_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index(
        "- [x] Remove Trivy suppression for gpgv CVE (CVE-2026-24883)"
    )
    next_item = backlog_text.find("\n- [", ledger_start + 1)
    ledger_end = next_item if next_item != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


def _ledger_faraday_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index(
        '<a id="ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297"></a>'
    )
    next_anchor = backlog_text.find("<a id=", ledger_start + 1)
    ledger_end = next_anchor if next_anchor != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


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


def test_removed_perl_runtime_cves_are_not_suppressed_in_rego_policy() -> None:
    policy = _policy_text()

    assert len(re.findall(r"^# Suppression expires:", policy, flags=re.MULTILINE)) == 1
    for cve in REMOVED_PERL_RUNTIME_CVES + REMEDIATED_SQLITE_CVES + REMOVED_PRODUCTION_TOOLING_CVES:
        assert cve not in policy
    assert "perl-base" not in policy
    assert "perl-modules" not in policy
    assert "libsqlite3-0" not in policy


def test_remediated_container_cves_are_not_broadly_ignored_in_trivyignore() -> None:
    trivyignore = TRIVYIGNORE_PATH.read_text(encoding="utf-8")

    assert "CVE-2025-8058" not in trivyignore
    for cve in REMOVED_PERL_RUNTIME_CVES + REMEDIATED_SQLITE_CVES + REMOVED_PRODUCTION_TOOLING_CVES:
        assert cve not in trivyignore
    assert "SQLite" not in trivyignore
    assert "libsqlite3-0" not in trivyignore
    assert "gpgv retained as Debian system dependency" not in trivyignore
    assert "libgnutls30 is installed in the Debian production image" not in trivyignore


def test_perl_runtime_removal_docs_and_backlog_coupling() -> None:
    doc_48959 = SECURITY_DOC_48959_PATH.read_text(encoding="utf-8")
    doc_48962 = SECURITY_DOC_48962_PATH.read_text(encoding="utf-8")
    archive_doc = SECURITY_DOC_ARCHIVE_TAR_PATH.read_text(encoding="utf-8")
    ledger_entry = _ledger_perl_entry()

    for doc_text in (doc_48959, doc_48962, archive_doc):
        assert "fixed by production package removal" in doc_text
        assert "perl-base" in doc_text
        assert "perl-modules-5.36" in doc_text
        assert "trivy/ignore-policy.rego" in doc_text
        assert "removed" in doc_text
        assert "temporary, exact Trivy Rego policy suppression" not in doc_text
        assert "fixed version remains unavailable" not in doc_text

    for cve in ("CVE-2026-48959", "CVE-2026-48962"):
        assert cve in doc_48959 + doc_48962
    for cve in ("CVE-2026-9538", "CVE-2026-42497", "CVE-2026-8376", "CVE-2026-42496"):
        assert cve in archive_doc
        assert cve in ledger_entry

    assert "Status: In progress" in ledger_entry
    assert "package removal from the production target" in ledger_entry
    assert ".trivyignore" in ledger_entry
    assert "trivy/ignore-policy.rego" in ledger_entry


def test_glibc_cve_2025_8058_doc_records_package_update_not_ignore() -> None:
    doc_text = SECURITY_DOC_8058_PATH.read_text(encoding="utf-8")

    assert "CVE-2025-8058" in doc_text
    assert "fixed by package update" in doc_text
    assert "2.36-9+deb12u13" in doc_text
    assert "Dockerfile" in doc_text
    assert ".trivyignore" in doc_text
    assert "removed" in doc_text


def test_sqlite_runtime_doc_records_source_update_and_package_removal() -> None:
    doc_text = SECURITY_DOC_SQLITE_PATH.read_text(encoding="utf-8")

    for cve in ("CVE-2026-11822", "CVE-2026-11824"):
        assert cve in doc_text
    for prior_cve in ("CVE-2025-7458", "CVE-2025-6965", "CVE-2025-29088"):
        assert prior_cve in doc_text
    assert "fixed by source update and production package removal" in doc_text
    assert "sqlite-autoconf-3530200.tar.gz" in doc_text
    sqlite_sha3 = "".join(
        (
            "025328da",
            "165109f4",
            "8abccc6e",
            "74785080",
            "60804412",
            "bed2bd81",
            "d47e98ba",
            "1b72983b",
        )
    )
    assert sqlite_sha3 in doc_text
    assert "libsqlite3-0" in doc_text
    assert ".trivyignore" in doc_text
    assert "removed" in doc_text


def test_gpgv_docs_and_backlog_record_production_package_removal() -> None:
    docs_text = "\n".join(
        (
            SECURITY_DOC_GPGV_24882_PATH.read_text(encoding="utf-8"),
            SECURITY_DOC_GPGV_24883_PATH.read_text(encoding="utf-8"),
        )
    )
    ledger_entry = _ledger_gpgv_entry()

    for cve in ("CVE-2026-24882", "CVE-2026-24883"):
        assert cve in docs_text
    assert "RESOLVED for the production Docker target by package removal" in docs_text
    assert "The final `production` Docker target no longer retains `gpgv`" in docs_text
    assert "old waiver posture" in docs_text
    assert "Removing `gpgv` would break the base system" not in docs_text
    assert "Why This CVE is Suppressed" not in docs_text

    assert "Status: Closed by production package removal" in ledger_entry
    assert "codex/fix-main-trivy-container-cves" in ledger_entry
    assert "Final production image removes `gpgv`" in ledger_entry
    assert "do not suppress CVE-2026-24883" in ledger_entry


def test_faraday_fastlane_suppression_tracks_1_10_6_scanner_lag() -> None:
    policy = _policy_text()
    faraday_policy = policy[policy.index("# CVE-2026-54297") :]
    doc_text = SECURITY_DOC_FARADAY_PATH.read_text(encoding="utf-8")
    ledger_entry = _ledger_faraday_entry()

    assert 'input.VulnerabilityID == "CVE-2026-54297"' in faraday_policy
    assert "input.Fingerprint" not in faraday_policy
    assert "faraday@1.10.5" not in faraday_policy
    assert 'input.PkgIdentifier.PURL == "pkg:gem/faraday@1.10.6"' in faraday_policy
    assert 'input.FixedVersion == ">= 2.14.3"' in faraday_policy
    assert 'input.FixedVersion == "2.14.3"' not in faraday_policy
    assert 'input.PrimaryURL == "https://avd.aquasec.com/nvd/cve-2026-54297"' in faraday_policy
    assert 'input.Severity == "HIGH"' in faraday_policy
    assert 'input.Status == "fixed"' in faraday_policy
    assert 'input.DataSource.ID == "ghsa"' not in faraday_policy
    assert 'input.PkgName == "faraday"' in faraday_policy
    assert 'input.InstalledVersion == "1.10.6"' in faraday_policy
    assert 'input.PkgID == "faraday@1.10.6"' in faraday_policy
    assert "docs/security/CVE-2026-54297-faraday-fastlane.md" in faraday_policy
    assert "# Review-by: 2026-07-04 (manual removal)" in faraday_policy

    assert "scanner-lag suppression" in doc_text
    assert "faraday@1.10.6" in doc_text
    assert "old vulnerable `1.10.5` lock" in doc_text
    assert "fastlane (2.235.0)" in doc_text
    assert "fixed in 1.10.6 and 2.14.3" in doc_text
    assert "ruby-advisory-db" in doc_text
    assert 'input.FixedVersion == ">= 2.14.3"' in doc_text
    assert "`DataSource.ID` can vary by advisory feed" in doc_text
    assert "Trivy's ignore-policy Rego input" in doc_text
    assert "Trivy `Fingerprint`\nchanges between synthetic PR merge refs" in doc_text
    assert "skip-dirs: trivy" in doc_text
    assert "transient upstream `trivy/go.mod`" in doc_text
    assert "`trivy/ignore-policy.rego`" in doc_text
    assert (
        "`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297`"
        in doc_text
    )

    assert "Remove Trivy suppression for Ruby Faraday CVE-2026-54297" in ledger_entry
    assert "codex/dependency-cleanup-faraday-runtime-drift" in ledger_entry
    assert "faraday@1.10.6" in ledger_entry
    assert "old `faraday 1.10.5` lock" in ledger_entry
    assert "faraday >= 2.14.3" in ledger_entry
    assert "scanner-lag suppression" in ledger_entry


def test_faraday_1_10_6_is_only_locked_in_ios_fastlane_lockfile() -> None:
    ignored_dirs = {".git", ".venv", "node_modules", "worktrees"}
    matching_lockfiles = []

    for lockfile in REPO_ROOT.rglob("Gemfile.lock"):
        relative = lockfile.relative_to(REPO_ROOT)
        if ignored_dirs.intersection(relative.parts):
            continue
        lockfile_text = lockfile.read_text(encoding="utf-8")
        assert "    faraday (1.10.5)" not in lockfile_text
        if "    faraday (1.10.6)" in lockfile_text:
            matching_lockfiles.append(relative.as_posix())

    assert matching_lockfiles == ["ios/Gemfile.lock"]

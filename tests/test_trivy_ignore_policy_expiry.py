from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

from scripts.ci import check_trivy_ignore_policy_expiry as expiry_guard
from scripts.ci import check_trivy_ignore_policy_native as native_policy
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
SECURITY_DOC_GZIP_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-41992-gzip.md"
SECURITY_DOC_FARADAY_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-54297-faraday-fastlane.md"
SECURITY_DOC_REACT_ROUTER_RSC_PATH = (
    REPO_ROOT / "docs" / "security" / "GHSA-qwww-vcr4-c8h2-react-router.md"
)
SECURITY_DOC_OPENSSL_14456_PATH = REPO_ROOT / "docs" / "security" / "CVE-2026-14456-openssl.md"
BACKLOG_PATH = REPO_ROOT / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
LOCAL_ONLY_SCAN_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "artifacts",
    "build",
    "dist",
    "node_modules",
    "worktrees",
}

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
REMOVED_ACL_ATTR_CVES = (
    "CVE-2026-54369",
    "CVE-2026-54371",
)
REMOVED_GZIP_CVES = ("CVE-2026-41992",)
REMOVED_ACL_ATTR_PACKAGES = (
    "libacl1",
    "libattr1",
)
_CANONICAL_RSC_RULE_BODY = "\n".join(
    (
        '\tinput.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
        '\tinput.PkgName == "react-router"',
        '\tinput.InstalledVersion == "7.18.1"',
        '\tinput.PkgID == "react-router@7.18.1"',
        '\tinput.FixedVersion == "8.3.0"',
    )
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


def _ledger_gzip_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index('<a id="ledger-p1-container-gzip-cve-remediation"></a>')
    next_anchor = backlog_text.find("<a id=", ledger_start + 1)
    ledger_end = next_anchor if next_anchor != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


def _ledger_faraday_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index(
        '<a id="ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297"></a>'
    )
    next_anchor = backlog_text.find("<a id=", ledger_start + 1)
    ledger_end = next_anchor if next_anchor != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


def _ledger_react_router_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index('<a id="ledger-p1-react-router-rsc-advisory-monitor"></a>')
    next_anchor = backlog_text.find("<a id=", ledger_start + 1)
    ledger_end = next_anchor if next_anchor != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


def _ledger_openssl_14456_entry() -> str:
    backlog_text = BACKLOG_PATH.read_text(encoding="utf-8")
    ledger_start = backlog_text.index(
        '<a id="ledger-p1-remove-trivy-suppression-openssl-cve-2026-14456"></a>'
    )
    current_item = backlog_text.index("\n- [", ledger_start + 1)
    next_item = backlog_text.find("\n- [", current_item + 1)
    ledger_end = next_item if next_item != -1 else len(backlog_text)
    return backlog_text[ledger_start:ledger_end]


def _repository_gemfile_locks(repo_root: Path) -> list[Path]:
    """Return repository lockfiles without descending into local-only trees."""

    lockfiles: list[Path] = []

    def raise_traversal_error(error: OSError) -> None:
        raise error

    for root, dirnames, filenames in os.walk(repo_root, onerror=raise_traversal_error):
        dirnames[:] = sorted(dirname for dirname in dirnames if dirname not in LOCAL_ONLY_SCAN_DIRS)
        if "Gemfile.lock" in filenames:
            lockfiles.append(Path(root) / "Gemfile.lock")
    return sorted(lockfiles)


@pytest.mark.parametrize("today", [date(2026, 9, 28), date(2026, 10, 5), date(2026, 10, 6)])
def test_current_policy_review_deadline_is_inclusive_and_distinct_from_expiry(today: date) -> None:
    """The approved review boundary expires the records, not the whole October policy."""
    policy_lines = POLICY_PATH.read_text().splitlines()
    assert [line for line in policy_lines if line.startswith("# Review-by:")] == [
        "# Review-by: 2026-10-05 (manual removal)",
        "# Review-by: 2026-10-07 (manual removal)",
        "# Review-by: 2026-10-05 (manual removal)",
        "# Review-by: 2026-10-05 (manual removal)",
    ]
    review_lines = [
        number
        for number, line in enumerate(policy_lines, start=1)
        if line.startswith("# Review-by: 2026-10-05 ")
    ]
    assert len(review_lines) == 3, "two retained records and new OpenSSL review are required"
    expected = (
        [
            f"Stale Trivy suppression review date: {POLICY_PATH}:{number} "
            f"(review-by 2026-10-05, today {today})"
            for number in review_lines
        ]
        if today == date(2026, 10, 6)
        else []
    )
    assert evaluate_policy_file(POLICY_PATH, today=today) == expected


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


@pytest.mark.parametrize(
    "decoy",
    (
        "\n".join(
            (
                "decoy := `",
                "# Suppression expires: 2000-01-01 decoy",
                "# Review-by: 2000-01-01 decoy",
                "`",
            )
        ),
        "\n".join(
            (
                'expiry_decoy := "# Suppression expires: 2000-01-01 decoy"',
                'review_decoy := "# Review-by: 2000-01-01 decoy"',
            )
        ),
    ),
)
def test_trivy_policy_dates_ignore_raw_and_quoted_string_decoys(
    tmp_path: Path,
    decoy: str,
) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        "\n".join(
            (
                "package trivy",
                decoy,
                "# Suppression expires: 2099-01-01 (manual removal)",
                "# Review-by: 2099-01-01 (manual removal)",
                "default ignore := false",
            )
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
    for cve in (
        REMOVED_PERL_RUNTIME_CVES
        + REMEDIATED_SQLITE_CVES
        + REMOVED_PRODUCTION_TOOLING_CVES
        + REMOVED_ACL_ATTR_CVES
        + REMOVED_GZIP_CVES
    ):
        assert cve not in policy
    assert "perl-base" not in policy
    assert "perl-modules" not in policy
    assert "libsqlite3-0" not in policy
    for package in REMOVED_ACL_ATTR_PACKAGES:
        assert package not in policy
    assert "gzip" not in policy


def test_remediated_container_cves_are_not_broadly_ignored_in_trivyignore() -> None:
    trivyignore = TRIVYIGNORE_PATH.read_text(encoding="utf-8")

    assert "CVE-2025-8058" not in trivyignore
    assert "CVE-2025-8869" not in trivyignore
    for cve in (
        REMOVED_PERL_RUNTIME_CVES
        + REMEDIATED_SQLITE_CVES
        + REMOVED_PRODUCTION_TOOLING_CVES
        + REMOVED_ACL_ATTR_CVES
        + REMOVED_GZIP_CVES
    ):
        assert cve not in trivyignore
    assert "SQLite" not in trivyignore
    assert "libsqlite3-0" not in trivyignore
    for package in REMOVED_ACL_ATTR_PACKAGES:
        assert package not in trivyignore
    assert "gzip" not in trivyignore
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


def test_gzip_docs_and_backlog_record_production_package_removal() -> None:
    doc_text = SECURITY_DOC_GZIP_PATH.read_text(encoding="utf-8")
    ledger_entry = _ledger_gzip_entry()

    assert "CVE-2026-41992" in doc_text
    assert "RESOLVED for the production Docker target by package removal" in doc_text
    assert "The final `production` Docker target no longer retains `gzip`" in doc_text
    assert "`gzip`, `gunzip`, and `zcat`" in doc_text
    assert "Python stdlib `gzip`" in doc_text
    assert "old waiver posture" in doc_text
    assert "Why This CVE is Suppressed" not in doc_text
    assert "temporary, exact Trivy Rego policy suppression" not in doc_text

    assert "Container image gzip CVE remediation (CVE-2026-41992)" in ledger_entry
    assert "codex/fix-main-docker-publish-" in ledger_entry
    assert "gzip-cve-2026-41992" in ledger_entry
    assert "Production image removes `gzip`" in ledger_entry
    assert "do not suppress CVE-2026-41992" in ledger_entry


def test_faraday_fastlane_suppression_removed_after_scanner_lag_resolved() -> None:
    policy = _policy_text()
    trivyignore = TRIVYIGNORE_PATH.read_text(encoding="utf-8")
    ledger_entry = _ledger_faraday_entry()

    for suppressed_text in (policy, trivyignore):
        assert "CVE-2026-54297" not in suppressed_text
        assert "GHSA-98m9-hrrm-r99r" not in suppressed_text
        assert "faraday@1.10.5" not in suppressed_text
        assert "faraday@1.10.6" not in suppressed_text
        assert "pkg:gem/faraday" not in suppressed_text

    assert "Remove Trivy suppression for Ruby Faraday CVE-2026-54297" in ledger_entry
    assert "- [x] P1: Remove Trivy suppression for Ruby Faraday CVE-2026-54297" in ledger_entry
    assert "codex/dependency-cleanup-faraday-runtime-drift" in ledger_entry
    assert "codex/fix-trivy-ignore-policy-expiry" in ledger_entry
    assert "faraday@1.10.6" in ledger_entry
    assert "temporary scanner-lag suppression was removed" in ledger_entry


def test_faraday_fastlane_doc_records_scanner_lag_removal() -> None:
    doc_text = SECURITY_DOC_FARADAY_PATH.read_text(encoding="utf-8")

    assert "temporary Trivy scanner-lag" in doc_text
    assert "suppression for `faraday@1.10.6` was removed" in doc_text
    assert "faraday@1.10.6" in doc_text
    assert "fastlane (2.237.0)" in doc_text
    assert "Fixed versions per advisory: `1.10.6` and `2.14.3`" in doc_text
    assert "2026-07-05 recheck" in doc_text
    assert "no longer reported any HIGH/CRITICAL finding" in doc_text
    assert "skip-dirs: trivy" in doc_text
    assert "transient upstream `trivy/go.mod`" in doc_text
    assert "`trivy/ignore-policy.rego`" in doc_text
    assert (
        "`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-faraday-cve-2026-54297`"
        in doc_text
    )


def test_faraday_1_10_6_is_only_locked_in_ios_fastlane_lockfile() -> None:
    matching_lockfiles: list[str] = []

    # Prune volatile dependency trees before descent. Python 3.11's ``Path.rglob``
    # can raise FileNotFoundError when a parallel OpenAPI test replaces
    # ``frontend/node_modules`` with ``npm ci``.
    for lockfile in _repository_gemfile_locks(REPO_ROOT):
        relative = lockfile.relative_to(REPO_ROOT)
        lockfile_text = lockfile.read_text(encoding="utf-8")
        assert "    faraday (1.10.5)" not in lockfile_text
        if "    faraday (1.10.6)" in lockfile_text:
            matching_lockfiles.append(relative.as_posix())

    assert sorted(matching_lockfiles) == ["ios/Gemfile.lock"]


def test_gemfile_scan_preserves_retained_local_artifacts(tmp_path: Path) -> None:
    ios_lock = tmp_path / "ios" / "Gemfile.lock"
    ios_lock.parent.mkdir()
    ios_lock.write_text("    faraday (1.10.6)\n", encoding="utf-8")
    retained_lock = (
        tmp_path / "artifacts" / "orchestration" / "experiments" / "retained" / "Gemfile.lock"
    )
    retained_lock.parent.mkdir(parents=True)
    retained_lock.write_text("creative evidence\n", encoding="utf-8")

    lockfiles = _repository_gemfile_locks(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in lockfiles] == ["ios/Gemfile.lock"]


def test_gemfile_scan_fails_closed_on_traversal_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def deny_traversal(_path: object) -> None:
        raise PermissionError("lockfile traversal denied")

    monkeypatch.setattr(os, "scandir", deny_traversal)

    with pytest.raises(PermissionError, match="lockfile traversal denied"):
        _repository_gemfile_locks(tmp_path)


def test_zlib_suppression_requires_exact_pkgid_scope() -> None:
    """Retain CVE/name/version scope and lexical contains; no exact-ID claim."""
    policy = _policy_text()
    start = policy.index('ignore if {\n\tinput.VulnerabilityID == "CVE-2026-27171"')
    zlib_ignore_rule = policy[start : policy.index("\n}", start) + 2]

    assert 'input.InstalledVersion == "1:1.2.13.dfsg-1"' in policy
    assert 'contains(input.PkgID, "zlib1g@1:1.2.13.dfsg-1")' in policy
    assert 'input.PkgName == "zlib1g"' in zlib_ignore_rule
    assert "cve_2026_27171_version_match" in zlib_ignore_rule
    assert "cve_2026_27171_pkgid_match" in zlib_ignore_rule
    assert zlib_ignore_rule.count('object.get(input, "FixedVersion", "") == ""') == 1


def test_ncurses_suppression_requires_fixed_version_and_exact_tuple_scope() -> None:
    """Retain family/name/version scope; prefixes do not prove paired equality."""
    policy = _policy_text()
    start = policy.index('ignore if {\n\tinput.VulnerabilityID == "CVE-2025-69720"')
    ncurses_ignore_rule = policy[start : policy.index("\n}", start) + 2]
    helper_region = policy[policy.index("cve_2025_69720_pkg_match if {") : start]

    assert 'input.VulnerabilityID == "CVE-2025-69720"' in ncurses_ignore_rule
    assert "cve_2025_69720_pkg_match" in ncurses_ignore_rule
    assert "cve_2025_69720_version_match" in ncurses_ignore_rule
    assert "cve_2025_69720_pkgid_match" in ncurses_ignore_rule
    assert ncurses_ignore_rule.count('object.get(input, "FixedVersion", "") == ""') == 1
    assert 'input.InstalledVersion == "6.4-4"' in helper_region
    for package in ("libncursesw6", "libtinfo6", "ncurses-base", "ncurses-bin"):
        assert f'startswith(input.PkgID, "{package}@6.4-4")' in helper_region


def _native_report_output(finding: dict[str, object], count: int) -> bytes:
    report = json.loads(native_policy._report_bytes(finding))
    if count == 0:
        del report["Results"][0]["Vulnerabilities"]
    return json.dumps(report).encode()


def test_native_trivy_case_inventory_is_exact_and_bounded() -> None:
    cases = native_policy._cases()

    assert len(native_policy.TUPLES) == 5
    assert len(cases) == 45
    assert len({case_id for case_id, _, _ in cases}) == 45
    assert {case_id.rsplit("/", 1)[1] for case_id, _, _ in cases} == {
        "missing",
        "empty",
        "null",
        "nonempty",
        "wrong-cve",
        "wrong-package",
        "wrong-version",
        "wrong-pkgid",
        "integer",
    }
    assert [finding["PkgName"] for _, finding, _ in cases[::9]] == [
        "zlib1g",
        "libncursesw6",
        "libtinfo6",
        "ncurses-base",
        "ncurses-bin",
    ]
    assert all(expected is None for _, _, expected in cases[8::9])


def test_native_trivy_policy_copy_rejects_symlink_hardlink_and_drift(tmp_path: Path) -> None:
    source = tmp_path / "source.rego"
    scan_copy = tmp_path / "scan.rego"
    source.write_bytes(b"package trivy\n")
    scan_copy.write_bytes(source.read_bytes())
    native_policy._verify_policy_copy(source, scan_copy)

    scan_copy.write_bytes(b"different")
    with pytest.raises(ValueError, match="differs"):
        native_policy._verify_policy_copy(source, scan_copy)
    scan_copy.unlink()
    scan_copy.symlink_to(source)
    with pytest.raises(ValueError, match="real single-link"):
        native_policy._verify_policy_copy(source, scan_copy)
    scan_copy.unlink()
    os.link(source, scan_copy)
    with pytest.raises(ValueError, match="real single-link"):
        native_policy._verify_policy_copy(source, scan_copy)
    scan_copy.unlink()
    with pytest.raises(ValueError, match="Unable to read"):
        native_policy._verify_policy_copy(source, scan_copy)


def test_native_trivy_binary_requires_real_absolute_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_policy.shutil, "which", lambda _name: None)
    with pytest.raises(ValueError, match="missing"):
        native_policy._trivy_binary()

    binary = tmp_path / "trivy"
    binary.write_bytes(b"synthetic executable")
    monkeypatch.setattr(native_policy.shutil, "which", lambda _name: str(binary))
    with pytest.raises(ValueError, match="not an executable"):
        native_policy._trivy_binary()
    binary.chmod(0o700)
    assert native_policy._trivy_binary() == str(binary.resolve())
    binary.unlink()
    with pytest.raises(ValueError, match="Unable to resolve"):
        native_policy._trivy_binary()


def test_native_trivy_runner_distinguishes_timeout_and_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*_args: object, **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="trivy", timeout=10)

    monkeypatch.setattr(native_policy.subprocess, "run", timeout)
    with pytest.raises(ValueError, match="timed out"):
        native_policy._invoke(["/usr/bin/trivy", "convert"])

    def cannot_start(*_args: object, **_kwargs: object) -> None:
        raise OSError("synthetic failure")

    monkeypatch.setattr(native_policy.subprocess, "run", cannot_start)
    with pytest.raises(ValueError, match="could not start"):
        native_policy._invoke(["/usr/bin/trivy", "convert"])


def test_native_trivy_runner_uses_fixed_local_subprocess_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        captured.update({"argv": argv, **kwargs})
        return subprocess.CompletedProcess(argv, 0, b"{}", b"")

    monkeypatch.setattr(native_policy.subprocess, "run", run)
    payload = b"synthetic"
    result = native_policy._invoke(["/usr/bin/trivy", "convert"], payload=payload)

    assert result.returncode == 0
    assert captured["argv"] == ["/usr/bin/trivy", "convert"]
    assert captured["input"] == payload
    assert captured["cwd"] == native_policy.REPO_ROOT
    assert captured["timeout"] == native_policy.TIMEOUT_SECONDS
    assert captured["check"] is False
    assert "shell" not in captured


def test_native_trivy_version_requires_exact_pinned_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    for returncode, stdout in (
        (0, b"Version: 0.74.0\n"),
        (1, b"Version: 0.74.0\n"),
        (0, b"Version: 0.75.0\n"),
    ):
        monkeypatch.setattr(
            native_policy,
            "_invoke",
            lambda _argv, *, payload=None: subprocess.CompletedProcess(
                args=[], returncode=returncode, stdout=stdout, stderr=b""
            ),
        )
        if returncode == 0 and stdout == b"Version: 0.74.0\n":
            native_policy._require_version("/usr/bin/trivy")
        else:
            with pytest.raises(ValueError, match="exactly version 0.74.0"):
                native_policy._require_version("/usr/bin/trivy")


def test_native_trivy_output_requires_exact_schema_identity_count_and_finding() -> None:
    finding = native_policy._cases()[3][1]
    visible = json.loads(_native_report_output(finding, 1))
    native_policy._validate_output(_native_report_output(finding, 0), finding, 0)
    native_policy._validate_output(_native_report_output(finding, 1), finding, 1)

    bad_reports: list[tuple[object, str]] = [(b"not-json", "invalid JSON")]
    for edit, expected in (
        (lambda report: report.update({"Extra": True}), "unexpected report shape"),
        (lambda report: report.update({"SchemaVersion": "2"}), "different report identity"),
        (lambda report: report["Results"].append({}), "different report identity"),
        (
            lambda report: report["Results"][0].update({"Target": "other"}),
            "different result identity",
        ),
        (lambda report: report["Results"][0].update({"Extra": True}), "different result identity"),
        (lambda report: report["Results"][0].update({"Vulnerabilities": {}}), "finding count"),
        (lambda report: report["Results"][0]["Vulnerabilities"].append(finding), "finding count"),
        (
            lambda report: report["Results"][0]["Vulnerabilities"][0].update({"PkgID": "other"}),
            "different finding identity",
        ),
    ):
        mutated = json.loads(json.dumps(visible))
        edit(mutated)
        bad_reports.append((json.dumps(mutated).encode(), expected))
    for raw, expected in bad_reports:
        with pytest.raises(ValueError, match=expected):
            native_policy._validate_output(raw, finding, 1)


def test_native_trivy_contract_runs_each_case_with_fixed_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = native_policy._cases() + native_policy._openssl_cases()
    calls: list[list[str]] = []

    def convert(
        argv: list[str], *, payload: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        case_id, finding, expected = cases[len(calls)]
        calls.append(argv)
        assert json.loads(payload or b"")["Results"][0]["Vulnerabilities"] == [finding]
        if expected is None:
            return subprocess.CompletedProcess(
                argv, 1, b"", b"json decode error FixedVersion of type string"
            )
        return subprocess.CompletedProcess(argv, 0, _native_report_output(finding, expected), b"")

    monkeypatch.setattr(native_policy, "_invoke", convert)
    assert native_policy._run_contract("/usr/bin/trivy", Path("/tmp/policy.rego")) == 85
    assert len(calls) == 85
    assert all(
        call
        == [
            "/usr/bin/trivy",
            "convert",
            "--quiet",
            "--format",
            "json",
            "--ignore-policy",
            "/tmp/policy.rego",
            "--ignorefile",
            "/dev/null",
            "/dev/stdin",
        ]
        for call in calls
    )


def test_native_trivy_contract_rejects_other_errors_and_wrong_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_id, finding, _ = native_policy._cases()[0]

    def failure(
        argv: list[str], *, payload: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 1, b"", b"network error")

    monkeypatch.setattr(native_policy, "_invoke", failure)
    with pytest.raises(ValueError, match="conversion failed"):
        native_policy._run_contract("/usr/bin/trivy", Path("/tmp/policy.rego"))

    def wrong_count(
        argv: list[str], *, payload: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(argv, 0, _native_report_output(finding, 1), b"")

    monkeypatch.setattr(native_policy, "_invoke", wrong_count)
    with pytest.raises(ValueError, match="finding count"):
        native_policy._run_contract("/usr/bin/trivy", Path("/tmp/policy.rego"))


def test_native_trivy_integer_case_rejects_unrelated_process_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = native_policy._cases()
    calls = 0

    def convert(
        argv: list[str], *, payload: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        _, finding, expected = cases[calls]
        calls += 1
        if expected is None:
            return subprocess.CompletedProcess(argv, 1, b"", b"network error")
        return subprocess.CompletedProcess(argv, 0, _native_report_output(finding, expected), b"")

    monkeypatch.setattr(native_policy, "_invoke", convert)
    with pytest.raises(ValueError, match="expected native FixedVersion type rejection"):
        native_policy._run_contract("/usr/bin/trivy", Path("/tmp/policy.rego"))
    assert calls == 9


def test_native_trivy_main_fails_closed_and_passes_bound_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "tracked.rego"
    scan_copy = tmp_path / "copy.rego"
    source.write_bytes(b"package trivy\n")
    scan_copy.write_bytes(source.read_bytes())
    monkeypatch.setattr(native_policy, "SOURCE_POLICY", source)
    monkeypatch.setattr(native_policy, "SCAN_POLICY", scan_copy)
    monkeypatch.setattr(native_policy, "_trivy_binary", lambda: "/usr/bin/trivy")
    monkeypatch.setattr(native_policy, "_require_version", lambda _binary: None)
    monkeypatch.setattr(native_policy, "_run_contract", lambda _binary, _policy: 45)
    assert native_policy.main() == 0
    assert "passed: 45 cases" in capsys.readouterr().out
    scan_copy.write_bytes(b"drift")
    assert native_policy.main() == 1
    assert "differs" in capsys.readouterr().err


def test_retired_util_linux_3184_suppression_stays_absent() -> None:
    policy = _policy_text()
    assert 'input.VulnerabilityID == "CVE-2026-3184"' not in policy
    assert "cve_2026_3184_pkgid_match" not in policy
    assert "util_linux_bookworm_pkg_match" in policy
    assert "util_linux_bookworm_version_match" in policy


def _fixed_version_clause_treats_finding_as_unfixed(finding: dict[str, str]) -> bool:
    """Mirror the Rego object.get default used for FixedVersion."""
    return finding.get("FixedVersion", "") == ""


def test_util_linux_cve_2026_53615_fixed_version_predicate_semantics() -> None:
    assert _fixed_version_clause_treats_finding_as_unfixed({})
    assert _fixed_version_clause_treats_finding_as_unfixed({"FixedVersion": ""})
    assert not _fixed_version_clause_treats_finding_as_unfixed({"FixedVersion": "2.42-1"})


def test_util_linux_cve_2026_53615_suppression_requires_exact_pkgid_scope() -> None:
    policy = _policy_text()

    assert "cve_2026_53615_pkgid_match" in policy
    start = policy.index('ignore if {\n\tinput.VulnerabilityID == "CVE-2026-53615"')
    # Bound the CVE-2026-53615 ignore rule before any later ignore block.
    next_ignore = policy.find("\nignore if {", start + 1)
    util_linux_ignore_rule = policy[start:] if next_ignore < 0 else policy[start:next_ignore]

    assert 'input.VulnerabilityID == "CVE-2026-53615"' in util_linux_ignore_rule
    assert "util_linux_bookworm_pkg_match" in util_linux_ignore_rule
    assert "util_linux_bookworm_version_match" in util_linux_ignore_rule
    assert "cve_2026_53615_pkgid_match" in util_linux_ignore_rule
    assert (
        "# Trivy omits empty FixedVersion (omitempty); missing/empty means unfixed."
        in util_linux_ignore_rule
    )
    # Trivy v0.71.2 omits empty FixedVersion, so the policy must default a missing key.
    assert 'object.get(input, "FixedVersion", "") == ""' in util_linux_ignore_rule
    assert "cve_2026_3184_pkgid_match" not in util_linux_ignore_rule

    helper_region = policy[policy.index("cve_2026_53615_pkgid_match if {") : start]
    assert "startswith(input.PkgID" not in helper_region

    for package, version in (
        ("bsdutils", "1:2.38.1-5+deb12u3"),
        ("libblkid1", "2.38.1-5+deb12u3"),
        ("libmount1", "2.38.1-5+deb12u3"),
        ("libsmartcols1", "2.38.1-5+deb12u3"),
        ("libuuid1", "2.38.1-5+deb12u3"),
        ("mount", "2.38.1-5+deb12u3"),
        ("util-linux", "2.38.1-5+deb12u3"),
        ("util-linux-extra", "2.38.1-5+deb12u3"),
    ):
        pkgid_rule = (
            f'cve_2026_53615_pkgid_match if {{\n\tinput.PkgName == "{package}"'
            f'\n\tinput.PkgID == "{package}@{version}"\n}}'
        )
        assert pkgid_rule in helper_region

    # Negative mismatches: prefix/wildcard forms must not appear for this CVE.
    assert 'input.PkgID == "util-linux@2.38.1-5+deb12u30"' not in helper_region
    assert 'startswith(input.PkgID, "util-linux@2.38.1-5+deb12u3")' not in helper_region


@pytest.mark.parametrize(
    "cve,helper",
    [
        ("CVE-2026-53613", "cve_2026_53613_pkgid_match"),
        ("CVE-2026-14456", "cve_2026_14456_pkgid_match"),
    ],
)
def test_retired_util_linux_and_openssl_rules_have_no_policy_or_fallback(
    cve: str, helper: str
) -> None:
    policy = _policy_text()
    assert cve not in policy
    assert helper not in policy
    assert cve not in TRIVYIGNORE_PATH.read_text(encoding="utf-8")
    assert "default ignore := false" in policy
    assert "cve_2026_53615_pkgid_match" in policy
    assert "util_linux_bookworm_pkg_match" in policy
    assert "util_linux_bookworm_version_match" in policy


def test_openssl_cve_2026_14456_document_and_removal_ledger_are_coupled() -> None:
    policy = _policy_text()
    security_doc = SECURITY_DOC_OPENSSL_14456_PATH.read_text(encoding="utf-8")
    ledger_entry = _ledger_openssl_14456_entry()

    for evidence in (
        "32368859081",
        "96424514194",
        "32368859126",
        "96424915657",
        "sha256:bb92cf07ffbdb41bb3ec05dc5014dd5280798cf2a3c01f5119847277a8611298",
        "https://openssl-library.org/news/secadv/20260813.txt",
        "https://security-tracker.debian.org/tracker/CVE-2026-14456",
        "metadata-correction retirement",
        "Shared policy expiry:** 2026-10-07",
        "scanner false-positive disposition",
        "not remediation",
    ):
        assert evidence in security_doc

    assert "CVE-2026-14456" not in policy
    assert policy.count("Suppression expires: 2026-10-07") == 1
    assert "Owner: @katsiaryna_kavaleuskaya (Security/SRE)" in ledger_entry
    assert "Priority: P1" in ledger_entry
    assert "Target PR: PR #2400" in ledger_entry
    assert "docs/security/CVE-2026-14456-openssl.md" in ledger_entry
    assert "Remove only the exact CVE-2026-14456 Rego rule" in ledger_entry
    assert "package tuple changes" in ledger_entry
    assert "finding disappears" in ledger_entry


def test_react_router_rsc_suppression_is_absent_and_guarded_against_reintroduction() -> None:
    policy = _policy_text()
    trivyignore = TRIVYIGNORE_PATH.read_text(encoding="utf-8")

    assert "GHSA-qwww-vcr4-c8h2" not in policy
    assert (
        expiry_guard._validate_react_router_rsc_trivyignore_absent(
            TRIVYIGNORE_PATH,
            text=trivyignore,
        )
        == []
    )
    assert expiry_guard._RETIRED_REACT_ROUTER_RSC_ADVISORY == "GHSA-qwww-vcr4-c8h2"


def test_react_router_rsc_trivyignore_reintroduction_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_expiry_wrapper_policy(tmp_path)
    (tmp_path / ".trivyignore").write_text(
        "# unrelated comment\nGHSA-qwww-vcr4-c8h2 exp:2099-01-01\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)

    assert expiry_guard.main() == 1
    output = capsys.readouterr().out
    assert "Retired React Router suppression must remain absent" in output
    assert "GHSA-qwww-vcr4-c8h2" in output


def test_react_router_rsc_trivyignore_comment_is_not_active(tmp_path: Path) -> None:
    ignore_file = tmp_path / ".trivyignore"
    text = "# retired: GHSA-qwww-vcr4-c8h2\nCVE-2023-45853\n"

    assert (
        expiry_guard._validate_react_router_rsc_trivyignore_absent(
            ignore_file,
            text=text,
        )
        == []
    )


def test_rego_os_read_error_returns_stable_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy_path = tmp_path / "trivy" / "ignore-policy.rego"
    policy_path.parent.mkdir()
    policy_path.write_text("package trivy\n", encoding="utf-8")
    original_read_text = Path.read_text

    def deny_policy_read(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        if path == policy_path:
            raise PermissionError("test denial")
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", deny_policy_read)

    assert evaluate_policy_file(policy_path, today=date(2026, 7, 27)) == [
        f"Unable to read Trivy ignore policy {policy_path}: test denial"
    ]
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)

    assert expiry_guard.main() == 1
    assert (
        f"- Unable to read Trivy ignore policy {policy_path}: test denial"
        in capsys.readouterr().out
    )


def test_rego_unicode_read_error_returns_stable_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy_path = tmp_path / "trivy" / "ignore-policy.rego"
    policy_path.parent.mkdir()
    policy_path.write_bytes(b"\xff")

    failures = evaluate_policy_file(policy_path, today=date(2026, 7, 27))

    assert len(failures) == 1
    assert failures[0].startswith(f"Unable to read Trivy ignore policy {policy_path}: ")
    assert "can't decode byte 0xff" in failures[0]
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)

    assert expiry_guard.main() == 1
    assert f"- Unable to read Trivy ignore policy {policy_path}: " in capsys.readouterr().out


def test_trivy_main_reuses_one_rego_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_expiry_wrapper_policy(tmp_path)
    policy_path = tmp_path / "trivy" / "ignore-policy.rego"
    original_read_text = Path.read_text
    read_count = 0

    def read_policy_once(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        nonlocal read_count
        if path == policy_path:
            read_count += 1
            if read_count > 1:
                raise PermissionError("second read must not occur")
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(Path, "read_text", read_policy_once)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)

    assert expiry_guard.main() == 0
    assert read_count == 1


@pytest.mark.parametrize(
    "body",
    (
        _CANONICAL_RSC_RULE_BODY,
        '\tinput.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
        '\tinput.PkgName == "react-router"',
        "\ttrue",
    ),
)
def test_react_router_rsc_suppression_rejects_any_target_capable_rule(
    tmp_path: Path,
    body: str,
) -> None:
    policy_path = _write_expiry_wrapper_policy_with_body(tmp_path, body)
    failures = expiry_guard.evaluate_policy_file(policy_path, today=date(2026, 7, 27))

    assert any("Retired React Router suppression must remain absent" in item for item in failures)


def test_react_router_rsc_remediation_policy_doc_and_backlog_are_coupled() -> None:
    policy = _policy_text()
    security_doc = SECURITY_DOC_REACT_ROUTER_RSC_PATH.read_text(encoding="utf-8")
    ledger_entry = _ledger_react_router_entry()

    assert "GHSA-qwww-vcr4-c8h2" not in policy
    assert "GHSA-qwww-vcr4-c8h2" in security_doc
    assert "Base installed version: `7.18.1`" in security_doc
    assert "Selected fixed version: `7.18.2`" in security_doc
    assert "exact suppression was deleted" in security_doc
    assert "scripts/ci/check_react_router_rsc_premise.py" not in security_doc
    assert "scripts/ci/check_trivy_ignore_policy_expiry.py" in security_doc
    assert "tests/test_trivy_ignore_policy_expiry.py" in security_doc
    assert '<a id="ledger-p1-react-router-rsc-advisory-monitor"></a>' in ledger_entry
    assert "- [ ] P1: Remove React Router unstable RSC advisory suppression" in ledger_entry
    assert "Target PR: PR #2247" in ledger_entry
    assert "suppression is deleted" in ledger_entry
    assert "exact-head Trivy confirmation is pending" in ledger_entry
    assert "scripts/ci/check_react_router_rsc_premise.py" not in ledger_entry
    assert "scripts/ci/check_trivy_ignore_policy_expiry.py" in ledger_entry
    assert "tests/test_trivy_ignore_policy_expiry.py" in ledger_entry


def _write_expiry_wrapper_policy(repo_root: Path) -> None:
    policy_dir = repo_root / "trivy"
    policy_dir.mkdir(parents=True)
    (repo_root / ".trivyignore").write_text("", encoding="utf-8")
    lines = [
        "package trivy",
        "# Suppression expires: 2099-01-01 (manual removal)",
        "default ignore := false",
        "# Review-by: 2099-01-01 (manual removal)",
        "ignore if {",
        '\tinput.VulnerabilityID == "CVE-2026-27171"',
        '\tinput.PkgName == "zlib1g"',
        "}",
    ]
    (policy_dir / "ignore-policy.rego").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _write_expiry_wrapper_policy_with_rule(repo_root: Path, rule: str) -> Path:
    policy_dir = repo_root / "trivy"
    policy_dir.mkdir(parents=True)
    policy_path = policy_dir / "ignore-policy.rego"
    policy_path.write_text(
        "\n".join(
            (
                "package trivy",
                "# Suppression expires: 2099-01-01 (manual removal)",
                "default ignore := false",
                "# Review-by: 2099-01-01 (manual removal)",
                rule,
                "",
            )
        ),
        encoding="utf-8",
    )
    return policy_path


def _write_expiry_wrapper_policy_with_body(repo_root: Path, body: str) -> Path:
    return _write_expiry_wrapper_policy_with_rule(
        repo_root,
        "\n".join(("ignore if {", body, "}")),
    )


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(
            "\n".join(
                (
                    '\tinput.VulnerabilityID=="GHSA-qwww-vcr4-c8h2"',
                    '\tinput.PkgName == "react-router"',
                    '\tinput.InstalledVersion == "7.18.1"',
                    '\tinput.PkgID == "react-router@7.18.1"',
                    '\tinput.FixedVersion == "8.3.0"',
                )
            ),
            id="no-space-target-equality",
        ),
        pytest.param(
            "\n".join(
                (
                    '\t"GHSA-qwww-vcr4-c8h2" == input.VulnerabilityID',
                    '\tinput.PkgName == "react-router"',
                    '\tinput.InstalledVersion == "7.18.1"',
                    '\tinput.PkgID == "react-router@7.18.1"',
                    '\tinput.FixedVersion == "8.3.0"',
                )
            ),
            id="reversed-target-equality",
        ),
        pytest.param(
            '\tinput.VulnerabilityID == "\\u0047HSA-qwww-vcr4-c8h2"',
            id="escaped-target-literal",
        ),
        pytest.param(
            "\treact_router_rsc_target_match",
            id="opaque-helper-predicate",
        ),
        pytest.param(
            "\n".join(
                (
                    '\ttarget_vulnerabilities := {"GHSA-qwww-vcr4-c8h2"}',
                    "\ttarget_vulnerabilities[input.VulnerabilityID]",
                )
            ),
            id="set-member-expression",
        ),
        pytest.param(
            "\n".join(
                (
                    "\tdecoy := `payload",
                    '\tinput.VulnerabilityID == "CVE-NOT-THE-TARGET"',
                    "\t`",
                    "\ttrue",
                )
            ),
            id="raw-string-conflicting-decoy",
        ),
        pytest.param(
            "\n".join(
                (
                    '\tinput.VulnerabilityID == "CVE-2026-27171"',
                    "\t# The modifier is part of the equality expression despite the newline.",
                    '\twith input.VulnerabilityID as "GHSA-qwww-vcr4-c8h2"',
                )
            ),
            id="following-with-overrides-same-input-field",
        ),
        pytest.param(
            "\n".join(
                (
                    '\t"CVE-2026-27171" == input.VulnerabilityID',
                    '\twith input as {"VulnerabilityID": "GHSA-qwww-vcr4-c8h2"}',
                )
            ),
            id="following-with-overrides-input-root",
        ),
        pytest.param(
            "\n".join(
                (
                    '\tinput.VulnerabilityID == "CVE-2026-27171"',
                    '\twith input["VulnerabilityID"] as "GHSA-qwww-vcr4-c8h2"',
                )
            ),
            id="following-with-overrides-bracket-input-field",
        ),
        pytest.param(
            "\n".join(
                (
                    '\tinput.VulnerabilityID == "CVE-2026-27171"',
                    '\twith input.PkgName as "react-router" with input.VulnerabilityID as "GHSA-qwww-vcr4-c8h2"',
                )
            ),
            id="chained-with-second-modifier-overrides-input-field",
        ),
        pytest.param(
            "\n".join(
                (
                    '\tinput.VulnerabilityID == "CVE-2026-27171"',
                    '\twith data.PkgName as "react-router" with input["VulnerabilityID"] as "GHSA-qwww-vcr4-c8h2"',
                )
            ),
            id="chained-with-second-bracket-modifier-overrides-input-field",
        ),
        pytest.param(
            "\n".join(
                (
                    '\tinput.VulnerabilityID == "CVE-2026-27171"',
                    "\twith",
                    '\tinput.VulnerabilityID as "GHSA-qwww-vcr4-c8h2"',
                )
            ),
            id="split-following-with-fails-closed",
        ),
        pytest.param(
            "\n".join(
                (
                    "\tdecoy := (",
                    '\t\tinput.VulnerabilityID == "CVE-2026-27171"',
                    "\t)",
                    "\ttrue",
                )
            ),
            id="wrapped-assignment-is-not-a-conflicting-predicate",
        ),
    ],
)
def test_noncanonical_target_capable_rule_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str,
) -> None:
    _write_expiry_wrapper_policy_with_body(tmp_path, body)
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)

    assert expiry_guard.main() == 1
    assert "Retired React Router suppression must remain absent" in capsys.readouterr().out


@pytest.mark.parametrize(
    "vulnerability_predicate",
    [
        'input.VulnerabilityID=="CVE-2026-27171"',
        '"CVE-2026-27171" == input.VulnerabilityID',
        '(\n\tinput.VulnerabilityID == "CVE-2026-27171"\n)',
    ],
)
def test_unrelated_rule_with_explicit_conflicting_vulnerability_stays_valid(
    tmp_path: Path,
    vulnerability_predicate: str,
) -> None:
    policy_path = _write_expiry_wrapper_policy_with_body(
        tmp_path,
        "\n".join(
            (
                f"\t{vulnerability_predicate}",
                '\taffected_packages := {"react-router", "zlib1g"}',
                "\taffected_packages[input.PkgName]",
            )
        ),
    )
    assert evaluate_policy_file(policy_path, today=date(2026, 7, 27)) == []


@pytest.mark.parametrize(
    "modifier",
    [
        pytest.param(
            'with input.PkgName as "react-router"',
            id="different-input-field",
        ),
        pytest.param(
            'with input["PkgName"] as "react-router"',
            id="different-bracket-input-field",
        ),
        pytest.param(
            'with input.VulnerabilityIDExtra as "GHSA-qwww-vcr4-c8h2"',
            id="input-field-prefix-near-miss",
        ),
        pytest.param(
            'with data.VulnerabilityID as "GHSA-qwww-vcr4-c8h2"',
            id="data-document-near-miss",
        ),
        pytest.param(
            'with input.PkgName as "react-router" with data.VulnerabilityID as "GHSA-qwww-vcr4-c8h2"',
            id="chained-non-overlapping-modifiers",
        ),
    ],
)
def test_unrelated_rule_with_non_overlapping_modifier_stays_valid(
    tmp_path: Path,
    modifier: str,
) -> None:
    policy_path = _write_expiry_wrapper_policy_with_body(
        tmp_path,
        "\n".join(
            (
                '\tinput.VulnerabilityID == "CVE-2026-27171"',
                f"\t{modifier}",
                "\ttrue",
            )
        ),
    )
    assert evaluate_policy_file(policy_path, today=date(2026, 7, 27)) == []


@pytest.mark.parametrize(
    "rule",
    [
        pytest.param(
            "\n".join(("ignore := true if {", _CANONICAL_RSC_RULE_BODY, "}")),
            id="assignment-colon-equals",
        ),
        pytest.param(
            "\n".join(("ignore = true if {", _CANONICAL_RSC_RULE_BODY, "}")),
            id="assignment-equals",
        ),
        pytest.param(
            'ignore := input.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
            id="direct-boolean-expression",
        ),
        pytest.param(
            "\n".join(("ignore {", _CANONICAL_RSC_RULE_BODY, "}")),
            id="legacy-unsupported-head",
        ),
        pytest.param(
            "\n".join(("ignore", "if {", "true", "}")),
            id="newline-between-head",
        ),
        pytest.param(
            "\n".join(("ignore # comment between head tokens", "if {", "true", "}")),
            id="comment-between-head",
        ),
        pytest.param(
            "\n".join(
                (
                    "rsc_target if {",
                    _CANONICAL_RSC_RULE_BODY,
                    "}",
                    "ignore if rsc_target",
                )
            ),
            id="helper-expression-head",
        ),
        pytest.param(
            "\n".join(
                (
                    "ignore if {",
                    '\tinput.VulnerabilityID == "CVE-2026-27171"',
                    "} else if {",
                    _CANONICAL_RSC_RULE_BODY,
                    "}",
                )
            ),
            id="else-chain-target",
        ),
        pytest.param(
            "\n".join(
                (
                    "decoy := `ignore if {",
                    _CANONICAL_RSC_RULE_BODY,
                    "}`",
                    "ignore := true if {",
                    "\ttrue",
                    "}",
                )
            ),
            id="raw-canonical-decoy-plus-alternate-head",
        ),
    ],
)
def test_unsupported_top_level_ignore_head_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    rule: str,
) -> None:
    _write_expiry_wrapper_policy_with_rule(tmp_path, rule)
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)

    assert expiry_guard.main() == 1
    assert "unsupported top-level ignore rule" in capsys.readouterr().out


def test_ignore_text_in_comments_does_not_create_suppression_rule(
    tmp_path: Path,
) -> None:
    policy_path = _write_expiry_wrapper_policy_with_rule(
        tmp_path,
        "\n".join(
            (
                "# ignore := true if {",
                "# ignore = true if {",
                "# ignore if {",
                "# }",
            )
        ),
    )
    assert evaluate_policy_file(policy_path, today=date(2026, 7, 27)) == []


def test_current_policy_uses_only_supported_ignore_rule_heads() -> None:
    assert evaluate_policy_file(POLICY_PATH, today=date(2026, 7, 27)) == []


def test_openssl_suppression_requires_paired_high_unfixed_scope() -> None:
    policy = _policy_text()
    start = policy.index("cve_2026_84782_pkgid_match if {")
    openssl_region = policy[start:]
    helpers = re.findall(r"cve_2026_84782_pkgid_match if \{(.*?)\n\}", openssl_region, re.S)
    assert len(helpers) == 2
    assert {block.strip() for block in helpers} == {
        'input.PkgName == "libssl3"\n\tinput.PkgID == "libssl3@3.0.22-1~deb12u1"',
        'input.PkgName == "openssl"\n\tinput.PkgID == "openssl@3.0.22-1~deb12u1"',
    }
    rule = openssl_region[openssl_region.index("ignore if {") :]
    assert 'input.VulnerabilityID == "CVE-2026-84782"' in rule
    assert 'input.Severity == "HIGH"' in rule
    assert 'input.InstalledVersion == "3.0.22-1~deb12u1"' in rule
    assert "cve_2026_84782_pkgid_match" in rule
    assert rule.count('object.get(input, "FixedVersion", "") == ""') == 1
    assert "contains(" not in openssl_region
    assert "startswith(" not in openssl_region
    assert "== null" not in openssl_region
    assert policy.count("Suppression expires: 2026-10-07") == 1


def test_openssl_native_cases_keep_distinct_members_and_adversarial_inputs() -> None:
    cases = native_policy._openssl_cases()
    assert native_policy.OPENSSL_TUPLES == (
        ("libssl3", "libssl3@3.0.22-1~deb12u1"),
        ("openssl", "openssl@3.0.22-1~deb12u1"),
    )
    assert len(cases) == len({case_id for case_id, _, _ in cases}) == 40
    kinds = {
        "missing",
        "empty",
        "null",
        "wrong-cve",
        "wrong-package",
        "wrong-version",
        "wrong-pkgid",
        "cross-pair",
        "pkgid-prefix",
        "pkgid-suffix",
        "pkgid-lookalike",
        "nonempty",
        "fixed-text",
        "fixed-whitespace",
        "critical",
        "integer",
        "float",
        "bool",
        "array",
        "object",
    }
    assert {case_id.rsplit("/", 1)[1] for case_id, _, _ in cases} == kinds
    for package, pkgid in native_policy.OPENSSL_TUPLES:
        group = {
            case_id.rsplit("/", 1)[1]: (finding, expected)
            for case_id, finding, expected in cases
            if case_id.split("/")[1] == package
        }
        assert set(group) == kinds
        baseline = group["missing"][0]
        assert baseline["PkgName"] == package
        assert baseline["PkgID"] == pkgid
        assert baseline["InstalledVersion"] == "3.0.22-1~deb12u1"
        assert baseline["Severity"] == "HIGH"
        assert "FixedVersion" not in baseline
        assert group["empty"][0]["FixedVersion"] == ""
        assert group["null"][0]["FixedVersion"] is None
        assert group["cross-pair"][0]["PkgID"] in {
            value for name, value in native_policy.OPENSSL_TUPLES if name != package
        }
        assert group["pkgid-prefix"][0]["PkgID"] == f"prefix/{pkgid}"
        assert group["pkgid-suffix"][0]["PkgID"] == f"{pkgid}:suffix"
        assert group["pkgid-lookalike"][0]["PkgID"] == f"{pkgid}0"
        assert group["critical"][0]["Severity"] == "CRITICAL"
        assert group["fixed-whitespace"][0]["FixedVersion"] == " "
        assert {kind for kind, (_, expected) in group.items() if expected == 0} == {
            "missing",
            "empty",
            "null",
        }
        assert {kind for kind, (_, expected) in group.items() if expected is None} == {
            "integer",
            "float",
            "bool",
            "array",
            "object",
        }
        assert {
            type(group[kind][0]["FixedVersion"])
            for kind in ("integer", "float", "bool", "array", "object")
        } == {int, float, bool, list, dict}
        assert sum(expected == 1 for _, expected in group.values()) == 12


@pytest.mark.parametrize("kind", ("integer", "float", "bool", "array", "object"))
@pytest.mark.parametrize("fault", ("success", "stdout", "decoder", "field", "type"))
def test_openssl_native_type_controls_require_actual_decode_rejection(
    kind: str, fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    cases = native_policy._cases() + native_policy._openssl_cases()
    target = f"CVE-2026-84782/libssl3/{kind}"
    calls = 0

    def convert(
        argv: list[str], *, payload: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        case_id, finding, expected = cases[calls]
        calls += 1
        assert json.loads(payload or b"")["Results"][0]["Vulnerabilities"] == [finding]
        if case_id == target:
            result = {
                "success": (0, b"", b"json decode error FixedVersion of type string"),
                "stdout": (1, b"{}", b"json decode error FixedVersion of type string"),
                "decoder": (1, b"", b"unrelated error FixedVersion of type string"),
                "field": (1, b"", b"json decode error OtherField of type string"),
                "type": (1, b"", b"json decode error FixedVersion of type number"),
            }[fault]
            return subprocess.CompletedProcess(argv, *result)
        if expected is None:
            return subprocess.CompletedProcess(
                argv, 1, b"", b"json decode error FixedVersion of type string"
            )
        return subprocess.CompletedProcess(argv, 0, _native_report_output(finding, expected), b"")

    monkeypatch.setattr(native_policy, "_invoke", convert)
    with pytest.raises(ValueError, match="expected native FixedVersion type rejection"):
        native_policy._run_contract("/usr/bin/trivy", Path("/tmp/policy.rego"))
    assert cases[calls - 1][0] == target


@pytest.mark.parametrize("package", ("libssl3", "openssl"))
@pytest.mark.parametrize(
    "kind",
    (
        "cross-pair",
        "pkgid-prefix",
        "pkgid-suffix",
        "critical",
        "nonempty",
        "fixed-text",
        "fixed-whitespace",
    ),
)
def test_openssl_native_negatives_require_retained_finding_identity(
    package: str, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    cases = native_policy._cases() + native_policy._openssl_cases()
    target = f"CVE-2026-84782/{package}/{kind}"
    calls = 0

    def convert(
        argv: list[str], *, payload: bytes | None = None
    ) -> subprocess.CompletedProcess[bytes]:
        nonlocal calls
        case_id, finding, expected = cases[calls]
        calls += 1
        if case_id == target:
            assert expected == 1
            changed = {**finding, "PkgID": "other@0"}
            return subprocess.CompletedProcess(argv, 0, _native_report_output(changed, 1), b"")
        if expected is None:
            return subprocess.CompletedProcess(
                argv, 1, b"", b"json decode error FixedVersion of type string"
            )
        return subprocess.CompletedProcess(argv, 0, _native_report_output(finding, expected), b"")

    monkeypatch.setattr(native_policy, "_invoke", convert)
    with pytest.raises(ValueError, match="different finding identity"):
        native_policy._run_contract("/usr/bin/trivy", Path("/tmp/policy.rego"))
    assert cases[calls - 1][0] == target

from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import re

import pytest

from scripts.ci import check_trivy_ignore_policy_expiry as expiry_guard
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
    policy = _policy_text()

    zlib_ignore_rule = policy[
        policy.index('ignore if {\n\tinput.VulnerabilityID == "CVE-2026-27171"') :
    ]

    assert 'input.InstalledVersion == "1:1.2.13.dfsg-1"' in policy
    assert 'contains(input.PkgID, "zlib1g@1:1.2.13.dfsg-1")' in policy
    assert 'input.PkgName == "zlib1g"' in zlib_ignore_rule
    assert "cve_2026_27171_version_match" in zlib_ignore_rule
    assert "cve_2026_27171_pkgid_match" in zlib_ignore_rule


def test_util_linux_suppression_requires_exact_pkgid_scope() -> None:
    policy = _policy_text()

    assert "cve_2026_3184_pkgid_match" in policy
    start = policy.index('ignore if {\n\tinput.VulnerabilityID == "CVE-2026-3184"')
    next_ignore = policy.find("\nignore if {", start + 1)
    util_linux_ignore_rule = policy[start:] if next_ignore < 0 else policy[start:next_ignore]
    assert "util_linux_bookworm_pkg_match" in util_linux_ignore_rule
    assert "util_linux_bookworm_version_match" in util_linux_ignore_rule
    assert "cve_2026_3184_pkgid_match" in util_linux_ignore_rule

    helper_start = policy.index("cve_2026_3184_pkgid_match if {")
    helper_region = policy[helper_start:start]
    assert "startswith(input.PkgID" not in helper_region

    expected_tuples = (
        ("bsdutils", "1:2.38.1-5+deb12u3"),
        ("libblkid1", "2.38.1-5+deb12u3"),
        ("libmount1", "2.38.1-5+deb12u3"),
        ("libsmartcols1", "2.38.1-5+deb12u3"),
        ("libuuid1", "2.38.1-5+deb12u3"),
        ("mount", "2.38.1-5+deb12u3"),
        ("util-linux", "2.38.1-5+deb12u3"),
        ("util-linux-extra", "2.38.1-5+deb12u3"),
    )
    assert helper_region.count("cve_2026_3184_pkgid_match if {") == len(expected_tuples)

    for package, version in expected_tuples:
        exact_rule = (
            f'cve_2026_3184_pkgid_match if {{\n\tinput.PkgName == "{package}"'
            f'\n\tinput.PkgID == "{package}@{version}"\n}}'
        )
        suffix_rule = exact_rule.replace(
            f'input.PkgID == "{package}@{version}"',
            f'input.PkgID == "{package}@{version}-unexpected-suffix"',
        )
        prefix_rule = exact_rule.replace(
            f'input.PkgID == "{package}@{version}"',
            f'startswith(input.PkgID, "{package}@{version}")',
        )

        assert exact_rule in helper_region
        assert suffix_rule not in helper_region
        assert prefix_rule not in helper_region


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
    assert "Target PR: PR #2246" in ledger_entry
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
        "# Suppression expires: 2026-10-07 (manual removal)",
        "default ignore := false",
        "# Review-by: 2026-08-24 (manual removal)",
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

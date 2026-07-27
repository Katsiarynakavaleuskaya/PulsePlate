from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re

import pytest

from scripts.ci import check_react_router_rsc_premise as guard
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
        assert f'input.PkgName == "{package}"' in policy
        assert f'startswith(input.PkgID, "{package}@{version}")' in policy


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


def _write_frontend(
    tmp_path: Path,
    *,
    package_json: object | None = None,
    package_lock: object | None = None,
) -> Path:
    frontend_root = tmp_path / "frontend"
    frontend_root.mkdir()
    package_value = (
        {"dependencies": {}, "devDependencies": {}, "optionalDependencies": {}, "scripts": {}}
        if package_json is None
        else package_json
    )
    (frontend_root / "package.json").write_text(
        json.dumps(package_value),
        encoding="utf-8",
    )
    lock_value = {} if package_lock is None else package_lock
    (frontend_root / "package-lock.json").write_text(
        json.dumps(lock_value),
        encoding="utf-8",
    )
    return frontend_root


def _write_source(frontend_root: Path, relative_path: str, text: str) -> Path:
    source_path = frontend_root / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(text, encoding="utf-8")
    return source_path


def test_default_cli_scans_canonical_frontend_root(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scanned_roots: list[Path] = []
    monkeypatch.setattr(
        guard,
        "scan_repository",
        lambda root: scanned_roots.append(root) or [],
    )

    assert guard.main([]) == 0
    assert scanned_roots == [guard.DEFAULT_FRONTEND_ROOT]
    assert capsys.readouterr().out == "PASS: React Router RSC suppression premise holds\n"


@pytest.mark.parametrize(
    ("package_json", "package_lock", "expected"),
    [
        (
            {"dependencies": {"@vitejs/plugin-rsc": "0.4.0"}},
            None,
            "package.json:dependencies.@vitejs/plugin-rsc:@vitejs/plugin-rsc",
        ),
        (
            {"devDependencies": {"react-server-dom-webpack": "19.1.0"}},
            None,
            "package.json:devDependencies.react-server-dom-webpack:react-server-dom-*",
        ),
        (
            {"optionalDependencies": {"rsc-runtime": "npm:react-server-dom-webpack@19.1.0"}},
            None,
            "package.json:optionalDependencies.rsc-runtime:react-server-dom-*",
        ),
        (
            {},
            {
                "packages": {
                    "node_modules/rsc-bridge": {
                        "resolved": (
                            "https://registry.npmjs.org/react-server-dom-webpack/"
                            "-/react-server-dom-webpack-19.1.0.tgz"
                        )
                    }
                }
            },
            ("package-lock.json:packages.node_modules/rsc-bridge.resolved:" "react-server-dom-*"),
        ),
        (
            {},
            {
                "packages": {
                    "node_modules/rsc-bridge": {
                        "dependencies": {"rsc-runtime": "npm:react-server-dom-webpack@19.1.0"}
                    }
                }
            },
            (
                "package-lock.json:packages.node_modules/rsc-bridge.dependencies."
                "rsc-runtime:react-server-dom-*"
            ),
        ),
    ],
)
def test_package_metadata_markers_fail_closed(
    tmp_path: Path,
    package_json: object,
    package_lock: object | None,
    expected: str,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json=package_json,
        package_lock=package_lock,
    )

    assert expected in guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    ("imports", "expected"),
    (
        (
            {"#router": "react-router"},
            "package.json:imports.#router:react-router package target",
        ),
        (
            {"#router": {"node": "react-router/server"}},
            "package.json:imports.#router.node:react-router package target",
        ),
        (
            {
                "#router": [
                    "./fallback.js",
                    {"default": "react-router/internal/react-server"},
                ]
            },
            "package.json:imports.#router.1.default:react-router package target",
        ),
    ),
)
def test_package_import_alias_targets_to_react_router_fail_closed(
    tmp_path: Path,
    imports: object,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path, package_json={"imports": imports})

    assert guard.scan_repository(frontend_root) == [expected]


def test_package_import_alias_near_matches_are_ignored(tmp_path: Path) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={
            "imports": {
                "#react-router": "./react-router",
                "#router-dom": "react-router-dom",
                "#scoped-router": "@example/react-router",
            }
        },
    )

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize(
    ("package_json", "package_lock", "expected"),
    (
        (
            {"dependencies": {"rr-rsc": "npm:react-router@7.18.1"}},
            None,
            "package.json:dependencies.rr-rsc:react-router npm alias",
        ),
        (
            {},
            {
                "packages": {
                    "": {
                        "dependencies": {
                            "rr-rsc": "npm:react-router@7.18.1",
                        }
                    }
                }
            },
            ("package-lock.json:packages..dependencies.rr-rsc:" "react-router npm alias"),
        ),
        (
            {},
            {
                "packages": {
                    "node_modules/rr-rsc": {
                        "name": "react-router",
                        "version": "7.18.1",
                    }
                }
            },
            ("package-lock.json:packages.node_modules/rr-rsc.name:" "react-router npm alias"),
        ),
    ),
)
def test_npm_alias_dependencies_targeting_react_router_fail_closed(
    tmp_path: Path,
    package_json: object,
    package_lock: object | None,
    expected: str,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json=package_json,
        package_lock=package_lock,
    )

    assert guard.scan_repository(frontend_root) == [expected]


def test_react_router_npm_alias_near_matches_are_ignored(tmp_path: Path) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={
            "dependencies": {
                "router-dom": "npm:react-router-dom@7.18.1",
                "scoped-router": "npm:@example/react-router@7.18.1",
            }
        },
        package_lock={
            "packages": {
                "": {
                    "dependencies": {
                        "router-dom": "npm:react-router-dom@7.18.1",
                    }
                },
                "node_modules/react-router": {
                    "name": "react-router",
                    "version": "7.18.1",
                },
                "workspace/react-router-source": {
                    "name": "react-router",
                    "version": "7.18.1",
                },
            }
        },
    )

    assert guard.scan_repository(frontend_root) == []


def test_npmrc_node_options_react_server_condition_fails_closed(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    (frontend_root / ".npmrc").write_text(
        "node-options=--conditions=react-server\n",
        encoding="utf-8",
    )

    assert guard.scan_repository(frontend_root) == [".npmrc:node-options:react-server condition"]


@pytest.mark.parametrize(
    "npmrc",
    (
        "# node-options=--conditions=react-server\n",
        "; node-options=--conditions=react-server\n",
        "node-options=--require react-server\n",
        "other-key=--conditions=react-server\n",
        "node-options=--conditions=react-serverish\n",
    ),
)
def test_npmrc_non_condition_decoys_are_ignored(tmp_path: Path, npmrc: str) -> None:
    frontend_root = _write_frontend(tmp_path)
    (frontend_root / ".npmrc").write_text(npmrc, encoding="utf-8")

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize(
    ("relative_path", "source_text", "expected"),
    [
        (
            "src/server.ts",
            'import { unstable_matchRSCServerRequest } from "react-router-dom";\n',
            "src/server.ts:unstable_matchRSCServerRequest",
        ),
        (
            "src/server.tsx",
            'import { unstable_routeRSCServerRequest } from "react-router";\n',
            "src/server.tsx:unstable_routeRSCServerRequest",
        ),
        (
            "src/server.mts",
            'import handler from "react-router/internal/react-server";\n',
            "src/server.mts:react-router/internal/react-server",
        ),
        (
            "src/plugin.cts",
            'import plugin from "@vitejs/plugin-rsc";\n',
            "src/plugin.cts:@vitejs/plugin-rsc",
        ),
        (
            "src/runtime.mjs",
            'import runtime from "react-server-dom-webpack";\n',
            "src/runtime.mjs:react-server-dom-",
        ),
    ],
)
def test_existing_runtime_markers_fail_closed(
    tmp_path: Path,
    relative_path: str,
    source_text: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, relative_path, source_text)

    assert expected in guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    "source_text",
    (
        'import * as router from "react-router";\n'
        'router["unstable_" + "routeRSCServerRequest"];\n',
        "import * as rr from 'react-router';\n" 'rr["unstable_" + "matchRSCServerRequest"];\n',
        'import/* owner */*/* runtime */as $router\nfrom\n"react-router";\n',
    ),
)
def test_react_router_namespace_import_is_rejected_before_computed_export_access(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/computed.mjs", source_text)

    expected = ["src/computed.mjs:react-router namespace import"]
    if "matchRSCServerRequest" in source_text:
        expected.append("src/computed.mjs:unstable_matchRSCServerRequest")
    elif "routeRSCServerRequest" in source_text:
        expected.append("src/computed.mjs:unstable_routeRSCServerRequest")
    assert guard.scan_repository(frontend_root) == expected


@pytest.mark.parametrize(
    "source_text",
    (
        'import * as r\\u006futer from "react-router";\n'
        'r\\u006futer["unstable_" + "routeRSCServerRequest"];\n',
        'import * as Роутер from "react-router";\n'
        'Роутер["unstable_" + "routeRSCServerRequest"];\n',
        'import * as \\u0420\\u043e\\u0443\\u0442\\u0435\\u0440 from "react-router";\n'
        '\\u0420\\u043e\\u0443\\u0442\\u0435\\u0440["unstable_" + "routeRSCServerRequest"];\n',
        'import * as router from "react\\u002drouter";\n'
        'router["unstable_" + "routeRSCServerRequest"];\n',
    ),
)
def test_escaped_static_namespace_imports_are_rejected(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/escaped.mjs", source_text)

    assert guard.scan_repository(frontend_root) == [
        "src/escaped.mjs:react-router namespace import",
        "src/escaped.mjs:unstable_routeRSCServerRequest",
    ]


@pytest.mark.parametrize(
    ("source_text", "expected"),
    (
        (
            'const router = await import("react-router");\n'
            'router["unstable_" + "routeRSCServerRequest"];\n',
            (
                "src/bypass.mjs:react-router dynamic import",
                "src/bypass.mjs:unstable_routeRSCServerRequest",
            ),
        ),
        (
            'const router = require("react-router");\n'
            'router["unstable_" + "matchRSCServerRequest"];\n',
            (
                "src/bypass.mjs:react-router require",
                "src/bypass.mjs:unstable_matchRSCServerRequest",
            ),
        ),
        (
            'const router = module.require("react-router");\n'
            'router["unstable_" + "matchRSCServerRequest"];\n',
            (
                "src/bypass.mjs:react-router require",
                "src/bypass.mjs:unstable_matchRSCServerRequest",
            ),
        ),
        (
            'export * as router from "react-router";\n',
            ("src/bypass.mjs:react-router re-export",),
        ),
        (
            'export { createBrowserRouter as router } from "react\\u002drouter";\n',
            ("src/bypass.mjs:react-router re-export",),
        ),
        (
            'const router = import("react\\u002drouter");\n'
            'router["unstable_" + "routeRSCServerRequest"];\n',
            (
                "src/bypass.mjs:react-router dynamic import",
                "src/bypass.mjs:unstable_routeRSCServerRequest",
            ),
        ),
        (
            'const router = require("react-router/server");\n',
            ("src/bypass.mjs:react-router require",),
        ),
        (
            'const router = await vi.importActual<typeof import("react-router")>'
            '("react-router");\n',
            ("src/bypass.mjs:react-router dynamic import",),
        ),
    ),
)
def test_namespace_producing_react_router_bypasses_are_rejected(
    tmp_path: Path,
    source_text: str,
    expected: tuple[str, ...],
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/bypass.mjs", source_text)

    assert guard.scan_repository(frontend_root) == list(expected)


@pytest.mark.parametrize(
    ("source_text", "expected"),
    (
        (
            'const router = import("react-" + "router");\n',
            "src/nonliteral.mjs:dynamic import requires a single string literal",
        ),
        (
            "const router = import(moduleName);\n",
            "src/nonliteral.mjs:dynamic import requires a single string literal",
        ),
        (
            "const router = import(`react-router`);\n",
            "src/nonliteral.mjs:dynamic import requires a single string literal",
        ),
        (
            "const router = require(moduleName);\n",
            "src/nonliteral.mjs:require requires a single string literal",
        ),
        (
            'const router = require("react-router", options);\n',
            "src/nonliteral.mjs:require requires a single string literal",
        ),
        (
            "const router = module.require(moduleName);\n",
            "src/nonliteral.mjs:require requires a single string literal",
        ),
    ),
)
def test_bare_dynamic_module_calls_require_one_string_literal(
    tmp_path: Path,
    source_text: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/nonliteral.mjs", source_text)

    assert guard.scan_repository(frontend_root) == [expected]


@pytest.mark.parametrize(
    "source_text",
    (
        'const router = await vi.importActual("react-router");\n',
        'const router = loader.require("react-router");\n',
        'const router = foo.module.require("react-router");\n',
    ),
)
def test_member_module_calls_are_not_misclassified_as_bare_calls(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/member-call.mjs", source_text)

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize(
    ("source_text", "expected"),
    (
        (
            'const path = "react-router/internal/react-" + "server";\n',
            (
                "src/composed.mjs:react-router/internal/react-server",
                "src/composed.mjs:react-server condition",
            ),
        ),
        (
            'const api = "unstable_" + "matchRSCServerRequest";\n',
            ("src/composed.mjs:unstable_matchRSCServerRequest",),
        ),
        (
            'const api = "unstable_" + "routeRSC" + "ServerRequest";\n',
            ("src/composed.mjs:unstable_routeRSCServerRequest",),
        ),
    ),
)
def test_composed_static_string_markers_fail_closed(
    tmp_path: Path,
    source_text: str,
    expected: tuple[str, ...],
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/composed.mjs", source_text)

    assert guard.scan_repository(frontend_root) == list(expected)


@pytest.mark.parametrize(
    ("source_text", "expected"),
    (
        (
            'const router = requ\\u0069re("react-router");\n',
            "src/escaped-bypass.mjs:react-router require",
        ),
        (
            'const router = import("r\\u{65}act-router");\n',
            "src/escaped-bypass.mjs:react-router dynamic import",
        ),
        (
            'const router = import("react\\x2drouter");\n',
            "src/escaped-bypass.mjs:react-router dynamic import",
        ),
        (
            'export const condition = "react\\u002dserver";\n',
            "src/escaped-bypass.mjs:react-server condition",
        ),
        (
            "export const marker = " '"unstable_routeRSCServerRequ\\x65st";\n',
            "src/escaped-bypass.mjs:unstable_routeRSCServerRequest",
        ),
    ),
)
def test_javascript_escape_bypasses_are_decoded_before_comparison(
    tmp_path: Path,
    source_text: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/escaped-bypass.mjs", source_text)

    assert guard.scan_repository(frontend_root) == [expected]


@pytest.mark.parametrize("suffix", (".js", ".cjs", ".mjs", ".ts"))
@pytest.mark.parametrize("line_ending", ("\n", "\r", "\r\n"))
def test_javascript_line_continuations_are_decoded_before_module_and_api_comparisons(
    tmp_path: Path,
    suffix: str,
    line_ending: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    source_text = (
        'import * as router from "react-'
        + "\\"
        + line_ending
        + 'router";\nrouter["unstable_matchRSCServer'
        + "\\"
        + line_ending
        + 'Request"];\n'
    )
    _write_source(frontend_root, f"src/continued{suffix}", source_text)

    assert guard.scan_repository(frontend_root) == [
        f"src/continued{suffix}:react-router namespace import",
        f"src/continued{suffix}:unstable_matchRSCServerRequest",
    ]


def test_identity_escapes_are_decoded_but_simple_escapes_preserve_runtime_value(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/identity.mjs",
        'import * as router from "react\\-router";\n'
        'router["unstable_matchRSCServer\\Request"];\n',
    )
    _write_source(
        frontend_root,
        "src/simple.mjs",
        'const marker = "unstable_matchRSCServer\\nRequest";\n',
    )

    assert guard.scan_repository(frontend_root) == [
        "src/identity.mjs:react-router namespace import",
        "src/identity.mjs:unstable_matchRSCServerRequest",
    ]


@pytest.mark.parametrize("decimal_escape", ("\\1", "\\08", "\\9"))
def test_legacy_decimal_escapes_fail_closed(
    tmp_path: Path,
    decimal_escape: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/legacy-escape.js",
        f'const value = "{decimal_escape}";\n',
    )

    with pytest.raises(guard.PremiseScanError, match="legacy decimal escape"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    "source_text",
    (
        '// import * as router from "react-router";\n',
        '/* import * as router from "react-router"; */\n',
        'const example = "import * as router from \\"react-router\\";";\n',
        'const example = `import * as router from "react-router";`;\n',
    ),
)
def test_namespace_import_like_comments_and_string_literals_are_ignored(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/example.ts", source_text)

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize(
    "source_text",
    (
        'import * as router from "react-router-dom";\n',
        'import type * as router from "react-router";\n',
        'import { createBrowserRouter } from "react-router";\n',
        'import router from "react-router";\n',
        'import "react-router";\n',
    ),
)
def test_safe_or_out_of_scope_react_router_import_shapes_remain_allowed(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/safe.ts", source_text)

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize("quote", ["'", '"', "`"])
def test_exact_react_server_condition_is_found_in_imported_source(
    tmp_path: Path,
    quote: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "config/rsc-conditions.ts",
        f"export const conditions = [{quote}react-server{quote}];\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "config/rsc-conditions.ts:react-server condition"
    ]


@pytest.mark.parametrize(
    "condition_literal",
    ("--conditions=react-server", "react-server:custom"),
)
def test_bounded_react_server_condition_is_found_inside_source_literal(
    tmp_path: Path,
    condition_literal: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "config/rsc-conditions.ts",
        f'export const condition = "{condition_literal}";\n',
    )

    assert guard.scan_repository(frontend_root) == [
        "config/rsc-conditions.ts:react-server condition"
    ]


@pytest.mark.parametrize(
    "near_match",
    ("pre-react-server", "react-serverish"),
)
def test_react_server_condition_near_matches_inside_source_literals_are_ignored(
    tmp_path: Path,
    near_match: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "config/rsc-conditions.ts",
        f'export const condition = "{near_match}";\n',
    )

    assert guard.scan_repository(frontend_root) == []


def test_all_supported_source_suffixes_are_scanned(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    for suffix in sorted(guard.SOURCE_SUFFIXES):
        _write_source(
            frontend_root,
            f"src/condition{suffix}",
            'export const condition = "react-server";\n',
        )

    assert guard.scan_repository(frontend_root) == [
        f"src/condition{suffix}:react-server condition" for suffix in sorted(guard.SOURCE_SUFFIXES)
    ]


def test_inline_module_scripts_in_html_are_scanned(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "index.html",
        "\n".join(
            (
                "<!doctype html>",
                '<script type="application/javascript">',
                '  const ignored = "unstable_matchRSCServerRequest";',
                "</script>",
                '<script type="module" src="/src/entry.ts">',
                '  const ignoredSourceBody = "unstable_matchRSCServerRequest";',
                "</script>",
                '<script TYPE=" module ">',
                '  import * as router from "react-router";',
                '  router["unstable_" + "routeRSCServerRequest"];',
                "</script>",
            )
        ),
    )

    assert guard.scan_repository(frontend_root) == [
        "index.html:inline-classic-script[1]:unstable_matchRSCServerRequest",
        "index.html:inline-module-script[1]:react-router namespace import",
        "index.html:inline-module-script[1]:unstable_routeRSCServerRequest",
    ]


def test_storybook_mdx_is_scanned(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/stories/rsc.mdx",
        'import { unstable_routeRSCServerRequest } from "react-router";\n'
        "{unstable_routeRSCServerRequest(request, routes)}\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "src/stories/rsc.mdx:unstable_routeRSCServerRequest",
    ]


def test_executable_classic_inline_script_is_scanned_but_data_scripts_are_not(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "index.html",
        "\n".join(
            (
                "<script>",
                '  import("react-router").then('
                "(router) => router.unstable_routeRSCServerRequest());",
                "</script>",
                '<script type="importmap">',
                '  {"imports": {"router": "react-router/internal/react-server"}}',
                "</script>",
                '<script type="application/json">',
                '  {"api": "unstable_matchRSCServerRequest"}',
                "</script>",
            )
        ),
    )

    assert guard.scan_repository(frontend_root) == [
        "index.html:inline-classic-script[1]:react-router dynamic import",
        "index.html:inline-classic-script[1]:unstable_routeRSCServerRequest",
    ]


def test_html_self_closing_syntax_does_not_hide_inline_module_body(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "index.html",
        '<script type="module"/>import("react-router");</script>',
    )

    assert guard.scan_repository(frontend_root) == [
        "index.html:inline-module-script[1]:react-router dynamic import"
    ]


def test_unterminated_inline_module_script_fails_closed(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "index.html",
        '<script type="module">const marker = "react-server";',
    )

    with pytest.raises(guard.PremiseScanError, match="unterminated script element"):
        guard.scan_repository(frontend_root)


def test_comments_near_misses_escapes_and_unsupported_files_are_ignored(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/clean.ts",
        "\n".join(
            (
                "// unstable_routeRSCServerRequest and 'react-server'",
                "/* @vitejs/plugin-rsc and react-server-dom-webpack */",
                'const suffix = "react-serverish";',
                'const prefix = "pre-react-server";',
                'const caseVariant = "React-Server";',
                'const escaped = "react\\nserver";',
            )
        ),
    )
    _write_source(
        frontend_root,
        "src/ignored.txt",
        'const condition = "react-server";\n',
    )

    assert guard.scan_repository(frontend_root) == []


def test_javascript_regex_literals_do_not_confuse_quote_scanning(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/regex.ts",
        "\n".join(
            (
                r"""const threshold = /(?<!['"`/])\b18\.5\b(?!['"`])/;""",
                r"""const normalized = value.replace(/\\/g, "/");""",
                'export const condition = "react-server";',
            )
        ),
    )

    assert guard.scan_repository(frontend_root) == ["src/regex.ts:react-server condition"]


@pytest.mark.parametrize(
    ("source_text", "expected"),
    (
        (
            'let count = 0;\ncount++ / import("react-router").then('
            "(router) => router.unstable_routeRSCServerRequest()) / 2;\n",
            (
                "src/postfix.mjs:react-router dynamic import",
                "src/postfix.mjs:unstable_routeRSCServerRequest",
            ),
        ),
        (
            'let count = 1;\ncount-- / require("react-router").'
            "unstable_matchRSCServerRequest() / 2;\n",
            (
                "src/postfix.mjs:react-router require",
                "src/postfix.mjs:unstable_matchRSCServerRequest",
            ),
        ),
    ),
)
def test_postfix_update_before_division_does_not_hide_runtime_surfaces(
    tmp_path: Path,
    source_text: str,
    expected: tuple[str, ...],
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/postfix.mjs", source_text)

    assert guard.scan_repository(frontend_root) == list(expected)


@pytest.mark.parametrize("property_name", ("await", "return"))
def test_keyword_named_property_before_division_does_not_hide_runtime_surfaces(
    tmp_path: Path,
    property_name: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/property.mjs",
        f'const ratio = obj.{property_name} / import("react-router").then('
        "(router) => router.unstable_routeRSCServerRequest()) / 2;\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "src/property.mjs:react-router dynamic import",
        "src/property.mjs:unstable_routeRSCServerRequest",
    ]


def test_rsc_template_interpolation_fails_closed(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/interpolation.mjs",
        "const result = "
        '`${import("react-router").then((router) => '
        'router["unstable_" + "routeRSCServerRequest"]())}`;\n',
    )

    with pytest.raises(guard.PremiseScanError, match="RSC template interpolation"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    "source_text",
    (
        r'++ /import\("react-router"\).*unstable_routeRSCServerRequest/.lastIndex;',
        r'-- /require\("react-router"\).*unstable_matchRSCServerRequest/.lastIndex;',
    ),
)
def test_prefix_update_operators_preserve_real_regex_literals(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/prefix.mjs", source_text)

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize(
    ("line_terminator", "operator"),
    (("\n", "++"), ("\r", "--"), ("\u2028", "++"), ("\u2029", "--")),
)
def test_line_terminator_forces_prefix_update_before_real_regex(
    tmp_path: Path,
    line_terminator: str,
    operator: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/newline-prefix.mjs",
        "let count = 0;\n"
        f'count{line_terminator}{operator} /import\\("react-router"\\).*'
        "unstable_routeRSCServerRequest/.lastIndex;\n",
    )

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize("line_terminator", ("\r", "\n", "\u2028", "\u2029"))
def test_line_terminator_inside_comment_preserves_javascript_semantics(
    tmp_path: Path,
    line_terminator: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/comment-lines.mjs",
        f"// comment{line_terminator}"
        'import("react-router").then('
        "(router) => router.unstable_routeRSCServerRequest());\n",
    )
    _write_source(
        frontend_root,
        "src/comment-prefix.mjs",
        "let count = 0;\n"
        f'count/*{line_terminator}*/++ /import\\("react-router"\\).*'
        "unstable_routeRSCServerRequest/.lastIndex;\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "src/comment-lines.mjs:react-router dynamic import",
        "src/comment-lines.mjs:unstable_routeRSCServerRequest",
    ]


@pytest.mark.parametrize("line_terminator", ("\r", "\n", "\u2028", "\u2029"))
def test_escaped_regex_line_terminator_fails_closed(
    tmp_path: Path,
    line_terminator: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/invalid-regex.mjs",
        f'/prefix\\{line_terminator}import("react-router").' "unstable_routeRSCServerRequest/;\n",
    )

    with pytest.raises(guard.PremiseScanError, match="unterminated regular expression literal"):
        guard.scan_repository(frontend_root)


def test_jsx_text_apostrophes_do_not_start_string_literals(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/Message.tsx",
        "<p>Users' pages aren't here. Let's go back.</p>\n",
    )

    assert guard.scan_repository(frontend_root) == []


def test_bounded_regex_context_preserves_prefix_characters_and_keywords() -> None:
    regex_prefixes = (
        "",
        *sorted(guard._REGEX_PREFIX_CHARACTERS),
        *guard._REGEX_PREFIX_KEYWORDS,
    )
    for prefix in regex_prefixes:
        visible = guard._VisibleCharacters()
        visible.extend(prefix)
        visible.extend(" " * 10_000)
        assert guard._starts_regex_literal(visible), prefix

    for prefix in ("identifier", "returnValue"):
        visible = guard._VisibleCharacters()
        visible.extend(prefix)
        visible.extend(" " * 10_000)
        assert not guard._starts_regex_literal(visible), prefix


def test_long_slash_and_apostrophe_prefixes_use_bounded_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_prefix_lengths: list[int] = []
    original = guard._ends_with_regex_prefix_keyword

    def record_prefix_length(prefix: str) -> bool:
        observed_prefix_lengths.append(len(prefix))
        return original(prefix)

    monkeypatch.setattr(guard, "_ends_with_regex_prefix_keyword", record_prefix_length)
    long_identifier = "x" * 100_000
    source = "\n".join(
        (
            f"{long_identifier} / divisor;",
            f"<p>{long_identifier}' pages</p>",
            "export const condition = 'react-server';",
        )
    )

    literals, _visible = guard._source_literals_and_visible_text(source, label="long-prefix.tsx")

    assert "react-server" in literals
    assert observed_prefix_lengths
    assert max(observed_prefix_lengths) <= guard._REGEX_PREFIX_CONTEXT_LIMIT


def test_script_condition_requires_exact_token_boundaries(tmp_path: Path) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={
            "scripts": {
                "build": "NODE_OPTIONS=--conditions=react-server vite build",
                "near": "echo react-serverish pre-react-server",
            }
        },
    )

    assert guard.scan_repository(frontend_root) == [
        "package.json:scripts.build:react-server condition"
    ]


@pytest.mark.parametrize("script_name", ("build.sh", "build"))
def test_delegated_shell_build_script_condition_fails_closed(
    tmp_path: Path,
    script_name: str,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": f"bash -e scripts/{script_name}"}},
    )
    _write_source(
        frontend_root,
        f"scripts/{script_name}",
        "#!/usr/bin/env bash\n" "export NODE_OPTIONS=--conditions=react-server\n" "vite build\n",
    )

    assert guard.scan_repository(frontend_root) == [f"scripts/{script_name}:react-server condition"]


def test_delegated_shell_build_script_ignores_comment_only_condition(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": "bash scripts/build.sh"}},
    )
    _write_source(
        frontend_root,
        "scripts/build.sh",
        "# NODE_OPTIONS=--conditions=react-server\nvite build\n",
    )

    assert guard.scan_repository(frontend_root) == []


def test_delegated_python_build_script_condition_fails_closed(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": "python3 scripts/build.py"}},
    )
    _write_source(
        frontend_root,
        "scripts/build.py",
        'import os\nos.environ["NODE_OPTIONS"] = "--conditions=react-server"\n',
    )

    assert guard.scan_repository(frontend_root) == ["scripts/build.py:react-server condition"]


@pytest.mark.parametrize(
    "build_command",
    (
        "bash -euo pipefail scripts/build",
        "./scripts/build",
        "source scripts/build",
    ),
)
def test_delegated_shell_command_forms_scan_the_local_script(
    tmp_path: Path,
    build_command: str,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": build_command}},
    )
    _write_source(
        frontend_root,
        "scripts/build",
        "export NODE_OPTIONS=--conditions=react-server\nvite build\n",
    )

    assert guard.scan_repository(frontend_root) == ["scripts/build:react-server condition"]


def test_delegated_shell_command_rejects_cwd_change(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": "cd scripts && bash build"}},
    )

    with pytest.raises(guard.PremiseScanError, match="unsupported compound shell command"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    "build_command",
    (
        "echo setup\nbash scripts/build",
        "bash -c 'bash scripts/build'",
        "bash -lc 'source scripts/build'",
        "! bash scripts/build",
        "command bash scripts/build",
        "env NODE_ENV=production bash scripts/build",
        "exec bash scripts/build",
        "{ bash scripts/build; }",
        "if true; then bash scripts/build; fi",
    ),
)
def test_unverified_shell_compound_forms_fail_closed(
    tmp_path: Path,
    build_command: str,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": build_command}},
    )

    with pytest.raises(guard.PremiseScanError, match="unsupported"):
        guard.scan_repository(frontend_root)


def test_shell_interpreter_argument_is_not_treated_as_an_executed_command(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": "echo bash scripts/build"}},
    )
    _write_source(
        frontend_root,
        "scripts/build",
        "export NODE_OPTIONS=--conditions=react-server\nvite build\n",
    )

    assert guard.scan_repository(frontend_root) == []


def test_direct_javascript_build_script_uses_source_scanner(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": "./scripts/build.mjs"}},
    )
    _write_source(frontend_root, "scripts/build.mjs", "const pattern = /don't/;\n")

    assert guard.scan_repository(frontend_root) == []


def test_dynamic_node_options_join_fails_closed(tmp_path: Path) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={"scripts": {"build": "./scripts/build.mjs"}},
    )
    _write_source(
        frontend_root,
        "scripts/build.mjs",
        "\n".join(
            (
                'const nodeOptions = ["--conditions=", "react", "-", "server"].join("");',
                "process.env.NODE_OPTIONS = nodeOptions;",
                'spawnSync("vite", ["build"], {env: process.env});',
            )
        ),
    )

    with pytest.raises(
        guard.PremiseScanError,
        match="NODE_OPTIONS value cannot be statically verified",
    ):
        guard.scan_repository(frontend_root)


def test_dynamic_node_condition_argument_fails_closed(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "scripts/build.mjs",
        'spawnSync("node", ["--conditions", condition, "server.mjs"]);\n',
    )

    with pytest.raises(
        guard.PremiseScanError,
        match="Node condition value cannot be statically verified",
    ):
        guard.scan_repository(frontend_root)


def test_static_safe_node_conditions_and_unrelated_node_options_reads_are_allowed(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "scripts/build.mjs",
        "\n".join(
            (
                'process.env.NODE_OPTIONS = "--conditions=" + "browser";',
                "const inheritedOptions = process.env.NODE_OPTIONS;",
                'const labels = ["NODE_OPTIONS", "conditions"];',
                'spawnSync("node", ["--conditions", "browser", "server.mjs"]);',
            )
        ),
    )

    assert guard.scan_repository(frontend_root) == []


def test_root_outputs_are_pruned_but_nested_build_and_dist_are_scanned(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    for root_output in ("build", "dist"):
        _write_source(
            frontend_root,
            f"{root_output}/ignored.ts",
            'export const condition = "react-server";\n',
        )
        _write_source(
            frontend_root,
            f"src/{root_output}/checked.ts",
            'export const condition = "react-server";\n',
        )

    assert guard.scan_repository(frontend_root) == [
        "src/build/checked.ts:react-server condition",
        "src/dist/checked.ts:react-server condition",
    ]


def test_global_generated_directories_are_pruned_at_every_depth(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    for relative_directory in (
        "node_modules",
        "src/node_modules",
        ".pytest_cache",
        "src/.ruff_cache",
    ):
        _write_source(
            frontend_root,
            f"{relative_directory}/ignored.ts",
            'export const condition = "react-server";\n',
        )

    assert guard.scan_repository(frontend_root) == []


def test_excluded_directory_symlinks_are_pruned_before_validation(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    _write_source(
        external_directory,
        "marker.ts",
        'export const condition = "react-server";\n',
    )
    (frontend_root / "dist").symlink_to(external_directory, target_is_directory=True)
    source_directory = frontend_root / "src"
    source_directory.mkdir()
    (source_directory / "node_modules").symlink_to(
        external_directory,
        target_is_directory=True,
    )

    assert guard.scan_repository(frontend_root) == []


def test_violations_are_sorted_and_deduplicated(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/z.ts",
        "unstable_routeRSCServerRequest(); unstable_routeRSCServerRequest();\n",
    )
    _write_source(
        frontend_root,
        "src/a.ts",
        "unstable_matchRSCServerRequest();\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "src/a.ts:unstable_matchRSCServerRequest",
        "src/z.ts:unstable_routeRSCServerRequest",
    ]


@pytest.mark.parametrize(
    ("filename", "payload", "expected"),
    [
        ("package.json", "{", "invalid JSON in package.json"),
        ("package.json", "[]", "expected a JSON object in package.json"),
        ("package.json", '{"dependencies": []}', "package.json:dependencies"),
        (
            "package.json",
            '{"dependencies": {"react-router": 7}}',
            "package.json:dependencies.react-router",
        ),
        ("package.json", '{"scripts": []}', "package.json:scripts"),
        ("package.json", '{"scripts": {"build": 1}}', "package.json:scripts.build"),
        ("package-lock.json", "[]", "expected a JSON object in package-lock.json"),
        (
            "package-lock.json",
            '{"packages": []}',
            "package-lock.json:packages",
        ),
    ],
)
def test_malformed_metadata_fails_closed(
    tmp_path: Path,
    filename: str,
    payload: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    (frontend_root / filename).write_text(payload, encoding="utf-8")

    with pytest.raises(guard.PremiseScanError, match=expected):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize("filename", ["package.json", "package-lock.json"])
def test_missing_package_metadata_fails_closed(tmp_path: Path, filename: str) -> None:
    frontend_root = _write_frontend(tmp_path)
    (frontend_root / filename).unlink()

    with pytest.raises(guard.PremiseScanError, match="required metadata file is missing"):
        guard.scan_repository(frontend_root)


def test_unreadable_candidate_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    package_path = frontend_root / "package.json"
    original_read_text = Path.read_text

    def deny_package_read(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        if path == package_path:
            raise PermissionError("test denial")
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", deny_package_read)

    with pytest.raises(guard.PremiseScanError, match="unable to read package.json"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize("target_outside_root", [False, True])
def test_candidate_file_symlinks_fail_closed(
    tmp_path: Path,
    target_outside_root: bool,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    target_parent = tmp_path if target_outside_root else frontend_root
    target = _write_source(
        target_parent,
        "target.ts",
        'export const condition = "react-server";\n',
    )
    linked_source = frontend_root / "src" / "linked.ts"
    linked_source.parent.mkdir()
    linked_source.symlink_to(target)

    with pytest.raises(guard.PremiseScanError, match="candidate path must not be a symlink"):
        guard.scan_repository(frontend_root)


def test_directory_symlink_fails_closed_without_following_target(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    _write_source(
        external_directory,
        "marker.ts",
        'export const condition = "react-server";\n',
    )
    (frontend_root / "linked").symlink_to(external_directory, target_is_directory=True)

    with pytest.raises(guard.PremiseScanError, match="directory must not be a symlink"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    ("source_text", "expected"),
    [
        ('const value = "react-server', "unterminated string literal"),
        ("/* react-server", "unterminated block comment"),
    ],
)
def test_incomplete_source_syntax_fails_closed(
    tmp_path: Path,
    source_text: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/incomplete.ts", source_text)

    with pytest.raises(guard.PremiseScanError, match=expected):
        guard.scan_repository(frontend_root)


def test_traversal_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_root = _write_frontend(tmp_path)

    def fail_walk(
        *args: object,
        onerror: object,
        **kwargs: object,
    ) -> list[tuple[str, list[str], list[str]]]:
        assert callable(onerror)
        onerror(PermissionError("test traversal denial"))
        return []

    monkeypatch.setattr(guard.os, "walk", fail_walk)

    with pytest.raises(guard.PremiseScanError, match="unable to traverse frontend root"):
        guard.scan_repository(frontend_root)


def test_cli_reports_clean_findings_and_incomplete_scan(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    frontend_root = _write_frontend(tmp_path)

    assert guard.main(["--frontend-root", str(frontend_root)]) == 0
    assert capsys.readouterr().out == "PASS: React Router RSC suppression premise holds\n"

    _write_source(
        frontend_root,
        "src/marker.ts",
        'export const condition = "react-server";\n',
    )
    assert guard.main(["--frontend-root", str(frontend_root)]) == 1
    assert capsys.readouterr().out == (
        "ERROR: React Router RSC suppression premise violated:\n"
        "- src/marker.ts:react-server condition\n"
    )

    assert guard.main(["--frontend-root", str(tmp_path / "missing")]) == 1
    assert "premise scan was incomplete" in capsys.readouterr().out


def test_cli_rejects_unknown_arguments() -> None:
    with pytest.raises(SystemExit) as exc_info:
        guard.main(["--unknown"])

    assert exc_info.value.code == 2


def test_react_router_rsc_suppression_requires_exact_scanner_tuple() -> None:
    policy = _policy_text()
    start = policy.index('ignore if {\n\tinput.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"')
    next_ignore = policy.find("\nignore if {", start + 1)
    rule = policy[start:] if next_ignore < 0 else policy[start:next_ignore]

    assert 'input.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"' in rule
    assert 'input.PkgName == "react-router"' in rule
    assert 'input.InstalledVersion == "7.18.1"' in rule
    assert 'input.PkgID == "react-router@7.18.1"' in rule
    assert 'input.FixedVersion == "8.3.0"' in rule
    assert "startswith(" not in rule
    assert "contains(" not in rule


def test_rego_os_read_error_returns_stable_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    policy_path = tmp_path / "trivy" / "ignore-policy.rego"
    policy_path.parent.mkdir()
    policy_path.write_text("package trivy\n", encoding="utf-8")
    (tmp_path / "frontend").mkdir()
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
    assert expiry_guard._contains_react_router_rsc_suppression(policy_path)
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(expiry_guard, "scan_react_router_rsc_premise", lambda _root: [])

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
    (tmp_path / "frontend").mkdir()

    failures = evaluate_policy_file(policy_path, today=date(2026, 7, 27))

    assert len(failures) == 1
    assert failures[0].startswith(f"Unable to read Trivy ignore policy {policy_path}: ")
    assert "can't decode byte 0xff" in failures[0]
    assert expiry_guard._contains_react_router_rsc_suppression(policy_path)
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(expiry_guard, "scan_react_router_rsc_premise", lambda _root: [])

    assert expiry_guard.main() == 1
    assert f"- Unable to read Trivy ignore policy {policy_path}: " in capsys.readouterr().out


def test_trivy_main_reuses_one_rego_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_expiry_wrapper_policy(tmp_path, include_rsc_rule=True)
    (tmp_path / "frontend").mkdir()
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
    monkeypatch.setattr(expiry_guard, "scan_react_router_rsc_premise", lambda _root: [])

    assert expiry_guard.main() == 0
    assert read_count == 1


def test_react_router_rsc_suppression_rejects_duplicate_or_broader_rule(
    tmp_path: Path,
) -> None:
    policy_path = tmp_path / "ignore-policy.rego"
    canonical = "\n".join(
        (
            "ignore if {",
            '\tinput.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
            '\tinput.PkgName == "react-router"',
            '\tinput.InstalledVersion == "7.18.1"',
            '\tinput.PkgID == "react-router@7.18.1"',
            '\tinput.FixedVersion == "8.3.0"',
            "}",
        )
    )
    policy_path.write_text(
        "# Suppression expires: 2099-01-01\n" + canonical + "\n" + canonical + "\n",
        encoding="utf-8",
    )
    assert any(
        "exactly one GHSA ignore block" in failure
        for failure in expiry_guard.evaluate_policy_file(
            policy_path,
            today=date(2026, 7, 27),
        )
    )

    broader = canonical.replace(
        '\tinput.FixedVersion == "8.3.0"',
        '\tinput.FixedVersion == "8.3.0"\n\tstartswith(input.PkgID, "react-router")',
    )
    policy_path.write_text(
        "# Suppression expires: 2099-01-01\n" + broader + "\n",
        encoding="utf-8",
    )
    assert any(
        "canonical five predicates" in failure
        for failure in expiry_guard.evaluate_policy_file(
            policy_path,
            today=date(2026, 7, 27),
        )
    )

    policy_path.write_text(
        "# Suppression expires: 2099-01-01\n"
        + canonical
        + "\nignore if {\n"
        + '\tinput.PkgName == "react-router"\n'
        + "}\n",
        encoding="utf-8",
    )
    assert any(
        "additional ignore block capable of matching" in failure
        for failure in expiry_guard.evaluate_policy_file(
            policy_path,
            today=date(2026, 7, 27),
        )
    )


def test_react_router_rsc_suppression_policy_doc_and_backlog_are_coupled() -> None:
    policy = _policy_text()
    security_doc = SECURITY_DOC_REACT_ROUTER_RSC_PATH.read_text(encoding="utf-8")
    backlog = BACKLOG_PATH.read_text(encoding="utf-8")

    assert "# Monitor: https://github.com/advisories/GHSA-qwww-vcr4-c8h2" in policy
    assert "# Documented in: docs/security/GHSA-qwww-vcr4-c8h2-react-router.md" in policy
    assert "GHSA-qwww-vcr4-c8h2" in security_doc
    assert "Installed version: `7.18.1`" in security_doc
    assert "Trivy fixed version: `8.3.0`" in security_doc
    assert "Review the GitHub advisory and Dependabot alert #241 weekly" in security_doc
    assert "scripts/ci/check_react_router_rsc_premise.py" in security_doc
    assert "scripts/ci/check_trivy_ignore_policy_expiry.py" in security_doc
    assert "tests/test_trivy_ignore_policy_expiry.py" in security_doc
    assert '<a id="ledger-p1-react-router-rsc-advisory-monitor"></a>' in backlog
    assert (
        "Target PR: this combined bootstrap PR (carryover from closed PRs #2184 and\n" "    #2187)"
    ) in backlog
    assert "Remove the suppression if an affected RSC marker is introduced" in backlog
    assert "scripts/ci/check_react_router_rsc_premise.py" in backlog
    assert "scripts/ci/check_trivy_ignore_policy_expiry.py" in backlog
    assert "tests/test_trivy_ignore_policy_expiry.py" in backlog


def _write_expiry_wrapper_policy(repo_root: Path, *, include_rsc_rule: bool) -> None:
    policy_dir = repo_root / "trivy"
    policy_dir.mkdir(parents=True)
    lines = [
        "package trivy",
        "# Suppression expires: 2026-10-07 (manual removal)",
        "# Review-by: 2026-08-24 (manual removal)",
        "default ignore := false",
    ]
    if include_rsc_rule:
        lines.extend(
            [
                "ignore if {",
                '\tinput.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
                '\tinput.PkgName == "react-router"',
                '\tinput.InstalledVersion == "7.18.1"',
                '\tinput.PkgID == "react-router@7.18.1"',
                '\tinput.FixedVersion == "8.3.0"',
                "}",
            ]
        )
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
                "# Review-by: 2099-01-01 (manual removal)",
                "default ignore := false",
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


_CANONICAL_RSC_RULE_BODY = "\n".join(
    (
        '\tinput.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
        '\tinput.PkgName == "react-router"',
        '\tinput.InstalledVersion == "7.18.1"',
        '\tinput.PkgID == "react-router@7.18.1"',
        '\tinput.FixedVersion == "8.3.0"',
    )
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
    ],
)
def test_noncanonical_target_capable_rule_rejected_and_activates_premise_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    body: str,
) -> None:
    policy_path = _write_expiry_wrapper_policy_with_body(tmp_path, body)
    calls: list[Path] = []
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda root: calls.append(root) or [],
    )

    assert expiry_guard._contains_react_router_rsc_suppression(policy_path)
    assert expiry_guard.main() == 1
    assert calls == [tmp_path / "frontend"]
    assert "must contain exactly the canonical five predicates" in capsys.readouterr().out


@pytest.mark.parametrize(
    "vulnerability_predicate",
    [
        'input.VulnerabilityID=="CVE-2026-27171"',
        '"CVE-2026-27171" == input.VulnerabilityID',
    ],
)
def test_unrelated_rule_with_explicit_conflicting_vulnerability_stays_valid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda _root: pytest.fail("explicitly unrelated rule must not activate RSC scan"),
    )

    assert not expiry_guard._contains_react_router_rsc_suppression(policy_path)
    assert expiry_guard.main() == 0


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
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda _root: pytest.fail("non-overlapping modifier must preserve conflict proof"),
    )

    assert not expiry_guard._contains_react_router_rsc_suppression(policy_path)
    assert expiry_guard.main() == 0


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
def test_unsupported_top_level_ignore_head_fails_closed_and_activates_premise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    rule: str,
) -> None:
    policy_path = _write_expiry_wrapper_policy_with_rule(tmp_path, rule)
    calls: list[Path] = []
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda root: calls.append(root) or [],
    )

    assert expiry_guard._contains_react_router_rsc_suppression(policy_path)
    assert expiry_guard.main() == 1
    assert calls == [tmp_path / "frontend"]
    assert "unsupported top-level ignore rule" in capsys.readouterr().out


def test_ignore_text_in_comments_does_not_activate_premise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda _root: pytest.fail("comments and the default rule must not activate RSC scan"),
    )

    assert not expiry_guard._contains_react_router_rsc_suppression(policy_path)
    assert expiry_guard.main() == 0


def test_current_policy_uses_only_supported_ignore_rule_heads() -> None:
    assert evaluate_policy_file(POLICY_PATH, today=date(2026, 7, 27)) == []
    assert expiry_guard._contains_react_router_rsc_suppression(POLICY_PATH)


def test_trivy_expiry_wrapper_runs_rsc_premise_once_when_suppression_is_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_expiry_wrapper_policy(tmp_path, include_rsc_rule=True)
    (tmp_path / "frontend").mkdir()
    calls: list[Path] = []
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda root: calls.append(root) or [],
    )

    assert expiry_guard.main() == 0
    assert calls == [tmp_path / "frontend"]


def test_trivy_expiry_wrapper_does_not_run_rsc_premise_without_suppression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_expiry_wrapper_policy(tmp_path, include_rsc_rule=False)
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        expiry_guard,
        "scan_react_router_rsc_premise",
        lambda _root: pytest.fail("RSC premise scan must be suppression-coupled"),
    )

    assert expiry_guard.main() == 0


@pytest.mark.parametrize("result", ["violation", "incomplete"])
def test_trivy_expiry_wrapper_fails_closed_for_rsc_premise_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    result: str,
) -> None:
    _write_expiry_wrapper_policy(tmp_path, include_rsc_rule=True)
    (tmp_path / "frontend").mkdir()
    monkeypatch.delenv("TRIVY_IGNORE_POLICY_PATH", raising=False)
    monkeypatch.setattr(expiry_guard, "REPO_ROOT", tmp_path)
    if result == "violation":
        monkeypatch.setattr(
            expiry_guard,
            "scan_react_router_rsc_premise",
            lambda _root: ["src/server.ts:unstable_routeRSCServerRequest"],
        )
    else:
        monkeypatch.setattr(
            expiry_guard,
            "scan_react_router_rsc_premise",
            lambda _root: (_ for _ in ()).throw(
                guard.PremiseScanError("unable to read package-lock.json")
            ),
        )

    assert expiry_guard.main() == 1
    output = capsys.readouterr().out
    if result == "violation":
        assert (
            "React Router RSC suppression premise violated: "
            "src/server.ts:unstable_routeRSCServerRequest"
        ) in output
    else:
        assert (
            "React Router RSC premise scan was incomplete: " "unable to read package-lock.json"
        ) in output

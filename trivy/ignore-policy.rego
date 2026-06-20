package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed at time of suppression
# - Limit to the installed versions reported at time of suppression
# - CI enforces a single file-level expiry (exactly one "Suppression expires: YYYY-MM-DD" per policy file)
#
# Suppression expires: 2026-06-27 (manual removal)
# Last reviewed: 2026-06-14
# Documented in: docs/security/CVE-2026-27171-zlib1g.md, docs/security/CVE-2026-3184-util-linux.md, docs/security/CVE-2025-69720-ncurses.md, docs/security/CVE-2026-54297-faraday-fastlane.md

# CVE-2026-27171 (zlib1g) - no fixed release for Debian bookworm at review time
# Review-by: 2026-06-27 (manual removal)
# Rationale: Debian bookworm has no fixed zlib1g package for this CVE at review time; no repository-level remediation is available until Debian publishes a fixed package or Trivy metadata gains a Fixed Version.
# Note: CI expiry is enforced once per policy file (see header); do not add another "Suppression expires:" line.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-27171
# Documented in: docs/security/CVE-2026-27171-zlib1g.md
# Removal condition: Remove when Debian bookworm publishes a fixed zlib1g package or Trivy metadata includes Fixed Version

cve_2026_27171_version_match if {
	input.InstalledVersion == "1:1.2.13.dfsg-1"
}

cve_2026_27171_pkgid_match if {
	contains(input.PkgID, "zlib1g@1:1.2.13.dfsg-1")
}

ignore if {
	input.VulnerabilityID == "CVE-2026-27171"
	input.PkgName == "zlib1g"
	cve_2026_27171_version_match
	cve_2026_27171_pkgid_match
}

# CVE-2026-3184 (util-linux family) - Debian bookworm no-dsa / not applicable to login in this release context at review time
# Review-by: 2026-06-27 (manual removal)
# Rationale: Debian bookworm marks this LOW-severity util-linux issue as no-dsa/non-applicable for the login binary context; keep exact package/version scope while monitoring Debian/Trivy metadata.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-3184
# Documented in: docs/security/CVE-2026-3184-util-linux.md
# Removal condition: Remove when Debian bookworm publishes a fixed util-linux package or Trivy metadata includes Fixed Version

cve_2026_3184_pkg_match if {
	util_linux_pkgs := {
		"bsdutils", "libblkid1", "libmount1", "libsmartcols1",
		"libuuid1", "mount", "util-linux", "util-linux-extra",
	}
	util_linux_pkgs[input.PkgName]
}

cve_2026_3184_version_match if {
	affected_versions := {"2.38.1-5+deb12u3", "1:2.38.1-5+deb12u3"}
	affected_versions[input.InstalledVersion]
}

ignore if {
	input.VulnerabilityID == "CVE-2026-3184"
	cve_2026_3184_pkg_match
	cve_2026_3184_version_match
}

# CVE-2025-69720 (ncurses family) - no fixed release for Debian bookworm at review time
# Review-by: 2026-06-27 (manual removal)
# Rationale: Debian bookworm remains no-dsa/minor for ncurses packages at review time; keep exact package/version scope while monitoring Debian/Trivy metadata.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2025-69720
# Documented in: docs/security/CVE-2025-69720-ncurses.md
# Removal condition: Remove when Debian bookworm publishes a fixed ncurses package or Trivy metadata includes Fixed Version

cve_2025_69720_pkg_match if {
	ncurses_pkgs := {"libncursesw6", "libtinfo6", "ncurses-base", "ncurses-bin"}
	ncurses_pkgs[input.PkgName]
}

cve_2025_69720_version_match if {
	input.InstalledVersion == "6.4-4"
}

cve_2025_69720_pkgid_match if {
	startswith(input.PkgID, "libncursesw6@6.4-4")
}

cve_2025_69720_pkgid_match if {
	startswith(input.PkgID, "libtinfo6@6.4-4")
}

cve_2025_69720_pkgid_match if {
	startswith(input.PkgID, "ncurses-base@6.4-4")
}

cve_2025_69720_pkgid_match if {
	startswith(input.PkgID, "ncurses-bin@6.4-4")
}

ignore if {
	input.VulnerabilityID == "CVE-2025-69720"
	cve_2025_69720_pkg_match
	cve_2025_69720_version_match
	cve_2025_69720_pkgid_match
}

# CVE-2026-54297 (Faraday / Fastlane release tooling) - Fastlane still constrains Faraday 1.x at review time
# Review-by: 2026-06-27 (manual removal)
# Rationale: Trivy v0.71.2 reports faraday@1.10.5 in ios/Gemfile.lock with fixed version 2.14.3, but Fastlane 2.236.1 still depends on faraday (~> 1.0). This lockfile is privileged iOS release tooling, not backend/container runtime or the iOS app binary, so keep an exact temporary suppression while monitoring upstream Fastlane. Trivy ignore-policy input does not expose the result Target, and Fingerprint changes between synthetic PR merge refs, so this rule is scoped to stable advisory/package identity fields and guarded by a repo test that Faraday 1.10.5 exists only in ios/Gemfile.lock.
# Monitor: https://avd.aquasec.com/nvd/cve-2026-54297
# Documented in: docs/security/CVE-2026-54297-faraday-fastlane.md
# Removal condition: Remove when Fastlane publishes a compatible release that permits Faraday >= 2.14.3, or iOS release tooling no longer depends on Fastlane's Faraday 1.x graph.

cve_2026_54297_identifier_match if {
	input.PkgIdentifier.PURL == "pkg:gem/faraday@1.10.5"
}

cve_2026_54297_advisory_match if {
	input.FixedVersion == "2.14.3"
	input.PrimaryURL == "https://avd.aquasec.com/nvd/cve-2026-54297"
	input.Severity == "HIGH"
	input.Status == "fixed"
	input.DataSource.ID == "ghsa"
}

cve_2026_54297_pkgid_match if {
	input.PkgID == "faraday@1.10.5"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-54297"
	cve_2026_54297_identifier_match
	cve_2026_54297_advisory_match
	input.PkgName == "faraday"
	input.InstalledVersion == "1.10.5"
	cve_2026_54297_pkgid_match
}

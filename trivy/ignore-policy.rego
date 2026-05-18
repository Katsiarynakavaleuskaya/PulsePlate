package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed at time of suppression
# - Limit to the installed versions reported at time of suppression
# - CI enforces a single file-level expiry (exactly one "Suppression expires: YYYY-MM-DD" per policy file)
#
# Suppression expires: 2026-05-27 (manual removal)
# Last reviewed: 2026-04-02
# Documented in: docs/security/CVE-2026-0915-glibc.md, docs/security/CVE-2026-4046-glibc.md, docs/security/CVE-2025-15281-glibc.md, docs/security/CVE-2026-27171-zlib1g.md, docs/security/CVE-2026-3184-util-linux.md, docs/security/CVE-2025-14831-gnutls.md, docs/security/CVE-2026-33845-gnutls.md, docs/security/CVE-2026-33846-gnutls.md, docs/security/CVE-2025-69720-ncurses.md, docs/security/CVE-2026-29111-systemd.md, docs/security/CVE-2026-4878-libcap2.md, docs/security/CVE-2026-45363-jwt-fastlane.md

ignore if {
	input.VulnerabilityID == "CVE-2026-0915"
	input.PkgName == "libc6"
	input.InstalledVersion == "2.36-9+deb12u13"
	startswith(input.PkgID, "libc6@2.36-9+deb12u13")
}

ignore if {
	input.VulnerabilityID == "CVE-2026-0915"
	input.PkgName == "libc-bin"
	input.InstalledVersion == "2.36-9+deb12u13"
	startswith(input.PkgID, "libc-bin@2.36-9+deb12u13")
}

# CVE-2026-4046 (glibc) - upstream unfixed in Debian bookworm at triage time
# Review-by: 2026-05-27 (manual removal)
# Rationale: Trivy code-scanning alerts on main report empty Fixed Version for libc6/libc-bin in the
#   Debian bookworm base image; repo code cannot patch glibc in the upstream image layer
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-4046
# Documented in: docs/security/CVE-2026-4046-glibc.md
# Removal condition: Remove when Debian bookworm publishes a fixed glibc package line or Trivy metadata includes Fixed Version

cve_2026_4046_version := "2.36-9+deb12u13"

cve_2026_4046_pkg_match if {
	glibc_pkgs := {"libc6", "libc-bin"}
	glibc_pkgs[input.PkgName]
}

cve_2026_4046_version_match if {
	input.InstalledVersion == cve_2026_4046_version
}

cve_2026_4046_pkgid_match if {
	startswith(input.PkgID, sprintf("libc6@%s", [cve_2026_4046_version]))
}

cve_2026_4046_pkgid_match if {
	startswith(input.PkgID, sprintf("libc-bin@%s", [cve_2026_4046_version]))
}

ignore if {
	input.VulnerabilityID == "CVE-2026-4046"
	cve_2026_4046_pkg_match
	cve_2026_4046_version_match
	cve_2026_4046_pkgid_match
}

# CVE-2025-15281 (glibc) - upstream unfixed in GitHub runner base image
# Review-by: 2026-05-27 (manual removal)
# Rationale: Upstream unfixed; GitHub runner base image (deb12u10/deb12u13); no actionable remediation in repo
# Monitor: https://security-tracker.debian.org/tracker/CVE-2025-15281
# Documented in: docs/security/CVE-2025-15281-glibc.md

# Helper rule: check if InstalledVersion matches observed runner versions
cve_2025_15281_version_match if {
	input.InstalledVersion == "2.36-9+deb12u10"
}

cve_2025_15281_version_match if {
	input.InstalledVersion == "2.36-9+deb12u13"
}

# Helper rule: check if PkgID matches allowed glibc packages (both u10 and u13)
cve_2025_15281_pkgid_match if {
	startswith(input.PkgID, "libc6@2.36-9+deb12u10")
}

cve_2025_15281_pkgid_match if {
	startswith(input.PkgID, "libc6@2.36-9+deb12u13")
}

cve_2025_15281_pkgid_match if {
	startswith(input.PkgID, "libc-bin@2.36-9+deb12u10")
}

cve_2025_15281_pkgid_match if {
	startswith(input.PkgID, "libc-bin@2.36-9+deb12u13")
}

ignore if {
	input.VulnerabilityID == "CVE-2025-15281"
	allowed_packages := {"libc6", "libc-bin"}
	allowed_packages[input.PkgName]
	cve_2025_15281_version_match
	cve_2025_15281_pkgid_match
}

# CVE-2026-27171 (zlib1g) - upstream unfixed in Debian bookworm
# Review-by: 2026-05-27 (manual removal)
# Rationale: Unfixed distro CVE; no fixed version reported in Trivy metadata for bookworm at time of triage
# Note: CI expiry is enforced once per policy file (see header); do not add another "Suppression expires:" line.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-27171
# Documented in: docs/security/CVE-2026-27171-zlib1g.md
# Removal condition: Remove when Debian bookworm publishes a fixed zlib1g package or Trivy metadata includes Fixed Version

# Helper rule: check if InstalledVersion matches observed version
cve_2026_27171_version_match if {
	input.InstalledVersion == "1:1.2.13.dfsg-1"
}

# Helper rule: check if PkgID matches observed zlib1g package
cve_2026_27171_pkgid_match if {
	contains(input.PkgID, "zlib1g@1:1.2.13.dfsg-1")
}

ignore if {
	input.VulnerabilityID == "CVE-2026-27171"
	input.PkgName == "zlib1g"
	cve_2026_27171_version_match
	cve_2026_27171_pkgid_match
}

# CVE-2026-41989 (libgcrypt20) - no fixed release for observed Debian package at triage time
# Review-by: 2026-05-27 (manual removal)
# Rationale: Trivy security scan reports libgcrypt20 fixed-version unknown for `1.10.1-3` in base image; no repository-level remediation path exists right now.
# Monitor: https://avd.aquasec.com/nvd/cve-2026-41989
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-41989
# Documented in: docs/security/CVE-2026-41989-libgcrypt20.md
# Removal condition: Remove when Debian publishes fixed libgcrypt20 package / Trivy metadata gains fixed version for this package context

cve_2026_41989_libgcrypt20_version := "1.10.1-3"

cve_2026_41989_image_reference_match if {
	# Scope by image reference when available in Trivy input.
	# Fallback remains broad when the field is absent.
	startswith(input.Image, "ghcr.io/katsiarynakavaleuskaya/pulseplate")
}

cve_2026_41989_image_reference_match if {
	not input.Image
}

cve_2026_41989_distro_match if {
	# Scope by distro when available in Trivy input.
	# Fallback remains broad when distro field is absent.
	input.Distro == "debian"
}

cve_2026_41989_distro_match if {
	not input.Distro
}

ignore if {
	input.VulnerabilityID == "CVE-2026-41989"
	input.PkgName == "libgcrypt20"
	input.InstalledVersion == cve_2026_41989_libgcrypt20_version
	cve_2026_41989_image_reference_match
	cve_2026_41989_distro_match
	startswith(input.PkgID, sprintf("libgcrypt20@%s", [cve_2026_41989_libgcrypt20_version]))
}

# CVE-2025-14831 (gnutls) - base image not yet updated to fixed version
# Review-by: 2026-05-27 (check if base image updated to deb12u6)
# Rationale: Fix available in 3.7.9-2+deb12u6 but base image still has deb12u5
# Monitor: https://security-tracker.debian.org/tracker/CVE-2025-14831
# Documented in: docs/security/CVE-2025-14831-gnutls.md
# Removal condition: Remove when base image updated to include libgnutls30 >= 3.7.9-2+deb12u6

ignore if {
	input.VulnerabilityID == "CVE-2025-14831"
	input.PkgName == "libgnutls30"
	input.InstalledVersion == "3.7.9-2+deb12u5"
}

# anchor:cve-2026-33845-gnutls-suppression
# CVE-2026-33845 (GnuTLS) - no fixed release for Debian bookworm at triage time
# Review-by: 2026-05-27 (manual removal)
# Rationale: Trivy code-scanning alert #589 reports libgnutls30 fixed-version unknown
#   in the production image. The Dockerfile now explicitly installs libgnutls30
#   from bookworm-security so the image does not retain stale `3.7.9-2+deb12u5`,
#   but Debian still marks bookworm-security `3.7.9-2+deb12u6` vulnerable.
#   Fixed version is only published for unstable (`3.8.13-1`) at triage time.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-33845
# Documented in: docs/security/CVE-2026-33845-gnutls.md
# Removal condition: Remove when Debian publishes fixed libgnutls30 package / Trivy metadata gains fixed version for this package context

cve_2026_33845_libgnutls30_version := "3.7.9-2+deb12u6"

cve_2026_33845_image_reference_match if {
	startswith(input.Image, "ghcr.io/katsiarynakavaleuskaya/pulseplate")
}

cve_2026_33845_image_reference_match if {
	startswith(input.Image, "katsiarynakavaleuskaya/pulseplate")
}

cve_2026_33845_image_reference_match if {
	# Fallback: Trivy sometimes omits the Image field in certain scan contexts;
	# suppression still requires exact CVE + package + version + pkgID prefix match.
	not input.Image
}

cve_2026_33845_distro_match if {
	input.Distro == "debian"
}

cve_2026_33845_distro_match if {
	# Fallback: Trivy sometimes omits the Distro field;
	# suppression still requires exact CVE + package + version + pkgID prefix match.
	not input.Distro
}

ignore if {
	input.VulnerabilityID == "CVE-2026-33845"
	input.PkgName == "libgnutls30"
	input.InstalledVersion == cve_2026_33845_libgnutls30_version
	cve_2026_33845_image_reference_match
	cve_2026_33845_distro_match
	startswith(input.PkgID, sprintf("libgnutls30@%s", [cve_2026_33845_libgnutls30_version]))
}

# anchor:cve-2026-33846-gnutls-suppression
# CVE-2026-33846 (GnuTLS) - no fixed release for Debian bookworm at triage time
# Review-by: 2026-05-27 (manual removal)
# Rationale: GitHub Code Scanning alert #590 reports libgnutls30 CVE-2026-33846
#   in the production image. The Dockerfile now explicitly installs libgnutls30
#   from bookworm-security so the image does not retain stale `3.7.9-2+deb12u5`,
#   but Debian still marks bookworm-security `3.7.9-2+deb12u6` vulnerable.
#   Fixed version is only published for unstable (`3.8.13-1`) at triage time.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-33846
# Documented in: docs/security/CVE-2026-33846-gnutls.md
# Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-gnutls-cve-2026-33846
# Removal condition: Remove when Debian bookworm publishes fixed libgnutls30 package / Trivy metadata gains fixed version for this package context

cve_2026_33846_libgnutls30_version := "3.7.9-2+deb12u6"

cve_2026_33846_image_reference_match if {
	startswith(input.Image, "ghcr.io/katsiarynakavaleuskaya/pulseplate")
}

cve_2026_33846_image_reference_match if {
	startswith(input.Image, "katsiarynakavaleuskaya/pulseplate")
}

cve_2026_33846_image_reference_match if {
	# Fallback: Trivy sometimes omits the Image field in certain scan contexts;
	# suppression still requires exact CVE + package + version + pkgID prefix match.
	not input.Image
}

cve_2026_33846_distro_match if {
	input.Distro == "debian"
}

cve_2026_33846_distro_match if {
	# Fallback: Trivy sometimes omits the Distro field;
	# suppression still requires exact CVE + package + version + pkgID prefix match.
	not input.Distro
}

ignore if {
	input.VulnerabilityID == "CVE-2026-33846"
	input.PkgName == "libgnutls30"
	input.InstalledVersion == cve_2026_33846_libgnutls30_version
	cve_2026_33846_image_reference_match
	cve_2026_33846_distro_match
	startswith(input.PkgID, sprintf("libgnutls30@%s", [cve_2026_33846_libgnutls30_version]))
}

# CVE-2026-3184 (util-linux family) - upstream unfixed in Debian bookworm
# Review-by: 2026-05-27 (manual removal)
# Rationale: Unfixed distro CVE; access control bypass via hostname canonicalization; LOW severity
# Affects all binary packages from util-linux source: bsdutils, libblkid1, libmount1,
#   libsmartcols1, libuuid1, mount, util-linux, util-linux-extra
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-3184
# Documented in: docs/security/CVE-2026-3184-util-linux.md
# Removal condition: Remove when Debian bookworm publishes a fixed util-linux package or Trivy metadata includes Fixed Version

# Helper rule: all util-linux family packages affected by CVE-2026-3184
cve_2026_3184_pkg_match if {
	util_linux_pkgs := {
		"bsdutils", "libblkid1", "libmount1", "libsmartcols1",
		"libuuid1", "mount", "util-linux", "util-linux-extra"
	}
	util_linux_pkgs[input.PkgName]
}

# Helper rule: check if InstalledVersion matches observed versions (with/without epoch)
cve_2026_3184_version_match if {
	affected_versions := {"2.38.1-5+deb12u3", "1:2.38.1-5+deb12u3"}
	affected_versions[input.InstalledVersion]
}

ignore if {
	input.VulnerabilityID == "CVE-2026-3184"
	cve_2026_3184_pkg_match
	cve_2026_3184_version_match
}

# CVE-2026-29111 (systemd family) - upstream unfixed in Debian bookworm
# Review-by: 2026-05-27 (manual removal)
# Rationale: Debian bookworm remains vulnerable; fix is published only in forky/sid at triage time
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-29111
# Documented in: docs/security/CVE-2026-29111-systemd.md
# Removal condition: Remove when Debian bookworm publishes a fixed systemd package line or Trivy metadata includes Fixed Version

cve_2026_29111_version := "252.38-1~deb12u1"

cve_2026_29111_pkg_match if {
	systemd_pkgs := {"libsystemd0", "libudev1"}
	systemd_pkgs[input.PkgName]
}

cve_2026_29111_version_match if {
	input.InstalledVersion == cve_2026_29111_version
}

cve_2026_29111_pkgid_match if {
	startswith(input.PkgID, sprintf("libsystemd0@%s", [cve_2026_29111_version]))
}

cve_2026_29111_pkgid_match if {
	startswith(input.PkgID, sprintf("libudev1@%s", [cve_2026_29111_version]))
}

ignore if {
	input.VulnerabilityID == "CVE-2026-29111"
	cve_2026_29111_pkg_match
	cve_2026_29111_version_match
	cve_2026_29111_pkgid_match
}

# CVE-2025-69720 (ncurses family) - upstream unfixed in Debian bookworm
# Review-by: 2026-05-27 (manual removal)
# Rationale: Debian bookworm remains vulnerable; fix is published only in forky/sid at triage time
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

# CVE-2026-4878 (libcap2) - no fixed release for observed Debian package at triage time
# Review-by: 2026-05-27 (manual removal)
# Rationale: Trivy code-scanning alert #588 reports libcap2 fixed-version unknown
#   for `1:2.66-4+deb12u1` in the production image. No repository-level
#   remediation path exists until Debian publishes a fixed package line or
#   Trivy metadata reports a Fixed Version.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-4878
# Documented in: docs/security/CVE-2026-4878-libcap2.md
# Removal condition: Remove when Debian publishes fixed libcap2 package / Trivy metadata gains fixed version for this package context

cve_2026_4878_libcap2_version := "1:2.66-4+deb12u1"

cve_2026_4878_image_reference_match if {
	startswith(input.Image, "ghcr.io/katsiarynakavaleuskaya/pulseplate")
}

cve_2026_4878_image_reference_match if {
	startswith(input.Image, "katsiarynakavaleuskaya/pulseplate")
}

cve_2026_4878_image_reference_match if {
	not input.Image
}

cve_2026_4878_distro_match if {
	input.Distro == "debian"
}

cve_2026_4878_distro_match if {
	not input.Distro
}

ignore if {
	input.VulnerabilityID == "CVE-2026-4878"
	input.PkgName == "libcap2"
	input.InstalledVersion == cve_2026_4878_libcap2_version
	cve_2026_4878_image_reference_match
	cve_2026_4878_distro_match
	startswith(input.PkgID, sprintf("libcap2@%s", [cve_2026_4878_libcap2_version]))
}

# anchor:cve-2026-45363-jwt-fastlane-suppression
# CVE-2026-45363 (Ruby jwt) - fixed version blocked by Fastlane dependency constraint
# Review-by: 2026-05-27 (manual removal)
# Rationale: GitHub Code Scanning alert #594 reports Ruby gem `jwt` 2.10.2
#   from ios/Gemfile.lock with fixed version 3.2.0. Bundler resolves latest
#   Fastlane 2.234.0 with `jwt >= 2.1.0, < 3`, so the fixed jwt 3.x line is
#   not reachable through a safe lockfile update. Trivy's Rego input for
#   Bundler findings does not expose the target path, so this rule uses exact
#   package, version, PURL, and advisory URL fields instead of a global CVE-only
#   suppression. This is release tooling only, not an iOS app binary runtime
#   dependency.
# Monitor: https://rubygems.org/gems/fastlane/versions/2.234.0
# Monitor: https://rubygems.org/gems/jwt/versions/3.2.0
# Monitor: https://avd.aquasec.com/nvd/cve-2026-45363
# Monitor: https://github.com/advisories/GHSA-c32j-vqhx-rx3x
# Documented in: docs/security/CVE-2026-45363-jwt-fastlane.md
# Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363
# Expiry is governed by the single file-level marker at the top of this policy.
# Removal condition: Remove when Fastlane permits jwt >= 3.2.0 or the iOS
#   release tooling no longer depends on Fastlane's jwt 2.x graph

cve_2026_45363_jwt_version := "2.10.2"

ignore if {
	input.VulnerabilityID == "CVE-2026-45363"
	input.PkgName == "jwt"
	input.InstalledVersion == cve_2026_45363_jwt_version
	input.FixedVersion == "3.2.0"
	input.PkgID == sprintf("jwt@%s", [cve_2026_45363_jwt_version])
	input.PkgIdentifier.PURL == sprintf("pkg:gem/jwt@%s", [cve_2026_45363_jwt_version])
	input.PrimaryURL == "https://avd.aquasec.com/nvd/cve-2026-45363"
}

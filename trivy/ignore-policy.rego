package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed at time of suppression
# - Limit to the installed versions reported at time of suppression
# - CI enforces a single file-level expiry (exactly one "Suppression expires: YYYY-MM-DD" per policy file)
#
# Suppression expires: 2026-10-07 (manual removal)
# Last reviewed: 2026-08-20
# CVE-2026-14456 was added with an exact two-tuple OpenSSL 3.0 scanner-disposition scope and a 2026-09-19 Review-by date; the earlier rule bodies are unchanged, and the shared file expiry remains 2026-10-07.
# Documented in: docs/security/CVE-2026-27171-zlib1g.md, docs/security/CVE-2026-3184-util-linux.md, docs/security/CVE-2025-69720-ncurses.md, docs/security/CVE-2026-53615-util-linux.md, docs/security/CVE-2026-53613-util-linux.md, docs/security/CVE-2026-14456-openssl.md

# CVE-2026-27171 (zlib1g) - no fixed release for Debian bookworm at review time
# Review-by: 2026-09-08 (manual removal)
# Rationale: Debian bookworm still lists zlib 1:1.2.13.dfsg-1 as vulnerable/no-dsa at the 2026-08-09 review; no repository-level remediation is available until Debian publishes a fixed package or Trivy metadata gains a Fixed Version.
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

# CVE-2026-3184 (util-linux family) - Debian bookworm not applicable to login in this release context at review time
# Review-by: 2026-09-08 (manual removal)
# Rationale: Debian still lists bookworm util-linux 2.38.1-5+deb12u3 as vulnerable but marks it ignored because login is not built from src:util-linux there at the 2026-08-09 review; keep exact package/version/PkgID scope while monitoring Debian/Trivy metadata.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-3184
# Documented in: docs/security/CVE-2026-3184-util-linux.md
# Removal condition: Remove when Debian bookworm publishes a fixed util-linux package or Trivy metadata includes Fixed Version

util_linux_bookworm_pkg_match if {
	util_linux_pkgs := {
		"bsdutils", "libblkid1", "libmount1", "libsmartcols1",
		"libuuid1", "mount", "util-linux", "util-linux-extra",
	}
	util_linux_pkgs[input.PkgName]
}

util_linux_bookworm_version_match if {
	affected_versions := {"2.38.1-5+deb12u3", "1:2.38.1-5+deb12u3"}
	affected_versions[input.InstalledVersion]
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "bsdutils"
	input.PkgID == "bsdutils@1:2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "libblkid1"
	input.PkgID == "libblkid1@2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "libmount1"
	input.PkgID == "libmount1@2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "libsmartcols1"
	input.PkgID == "libsmartcols1@2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "libuuid1"
	input.PkgID == "libuuid1@2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "mount"
	input.PkgID == "mount@2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "util-linux"
	input.PkgID == "util-linux@2.38.1-5+deb12u3"
}

cve_2026_3184_pkgid_match if {
	input.PkgName == "util-linux-extra"
	input.PkgID == "util-linux-extra@2.38.1-5+deb12u3"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-3184"
	util_linux_bookworm_pkg_match
	util_linux_bookworm_version_match
	cve_2026_3184_pkgid_match
}

# CVE-2026-53615 (util-linux family) - Debian bookworm no fixed release at review time
# Review-by: 2026-10-07 (manual removal)
# Rationale: Trivy reports this util-linux issue as HIGH on the fail-closed publish scan, while Debian bookworm has no fixed util-linux package for this CVE at the 2026-07-09 review; keep exact package/version/PkgID scope while monitoring Debian/Trivy metadata and the util-linux GHSA advisory.
# Note: CI expiry is enforced once per policy file (see header); do not add another "Suppression expires:" line.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-53615
# Documented in: docs/security/CVE-2026-53615-util-linux.md
# Removal condition: Remove when Debian bookworm publishes a fixed util-linux package or Trivy metadata includes Fixed Version

cve_2026_53615_pkgid_match if {
	input.PkgName == "bsdutils"
	input.PkgID == "bsdutils@1:2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "libblkid1"
	input.PkgID == "libblkid1@2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "libmount1"
	input.PkgID == "libmount1@2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "libsmartcols1"
	input.PkgID == "libsmartcols1@2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "libuuid1"
	input.PkgID == "libuuid1@2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "mount"
	input.PkgID == "mount@2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "util-linux"
	input.PkgID == "util-linux@2.38.1-5+deb12u3"
}

cve_2026_53615_pkgid_match if {
	input.PkgName == "util-linux-extra"
	input.PkgID == "util-linux-extra@2.38.1-5+deb12u3"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-53615"
	util_linux_bookworm_pkg_match
	util_linux_bookworm_version_match
	cve_2026_53615_pkgid_match
	# Trivy omits empty FixedVersion (omitempty); missing/empty means unfixed.
	object.get(input, "FixedVersion", "") == ""
}

# CVE-2026-53613 (util-linux family) - Debian bookworm has no fixed release at review time
# Review-by: 2026-09-19 (manual removal)
# Rationale: Exact-main CD run 32355502655 reports this util-linux TOCTOU issue as HIGH across eight Debian bookworm package tuples with no FixedVersion; Debian fixes trixie-security at 2.41.5-0+deb13u1 while bookworm 2.38.1-5+deb12u3 remains vulnerable at the 2026-08-20 review.
# Note: CI expiry is enforced once per policy file (see header); do not add another "Suppression expires:" line.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-53613
# Documented in: docs/security/CVE-2026-53613-util-linux.md
# Removal condition: Remove when Debian bookworm publishes a fixed util-linux package, the base image moves to a fixed release, or Trivy reports a non-empty FixedVersion

cve_2026_53613_pkgid_match if {
	input.PkgName == "bsdutils"
	input.InstalledVersion == "1:2.38.1-5+deb12u3"
	input.PkgID == "bsdutils@1:2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "libblkid1"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "libblkid1@2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "libmount1"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "libmount1@2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "libsmartcols1"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "libsmartcols1@2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "libuuid1"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "libuuid1@2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "mount"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "mount@2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "util-linux"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "util-linux@2.38.1-5+deb12u3"
}

cve_2026_53613_pkgid_match if {
	input.PkgName == "util-linux-extra"
	input.InstalledVersion == "2.38.1-5+deb12u3"
	input.PkgID == "util-linux-extra@2.38.1-5+deb12u3"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-53613"
	util_linux_bookworm_pkg_match
	util_linux_bookworm_version_match
	cve_2026_53613_pkgid_match
	# Trivy omits empty FixedVersion (omitempty); missing/empty means unfixed.
	object.get(input, "FixedVersion", "") == ""
}

# CVE-2026-14456 (OpenSSL) - upstream classifies the shipped 3.0 branch as unaffected
# Review-by: 2026-09-19 (manual removal)
# Rationale: Exact-main CD run 32368859081 and Docker Build and Push run 32368859126 report two HIGH findings for Debian bookworm OpenSSL 3.0.20-1~deb12u2 with no FixedVersion, while the upstream OpenSSL advisory assigns Low severity and marks the 3.0 branch unaffected because the vulnerable QUIC server implementation begins in OpenSSL 3.5.
# Note: This is a scanner false-positive disposition, not package remediation. CI expiry is enforced once per policy file (see header); do not add another "Suppression expires:" line.
# Monitor: https://openssl-library.org/news/secadv/20260813.txt and https://security-tracker.debian.org/tracker/CVE-2026-14456
# Documented in: docs/security/CVE-2026-14456-openssl.md
# Removal condition: Remove when scanner or Debian metadata is corrected, the installed package tuple changes, the finding disappears, or upstream evidence expands affected branches to OpenSSL 3.0

cve_2026_14456_pkgid_match if {
	input.PkgName == "libssl3"
	input.InstalledVersion == "3.0.20-1~deb12u2"
	input.PkgID == "libssl3@3.0.20-1~deb12u2"
}

cve_2026_14456_pkgid_match if {
	input.PkgName == "openssl"
	input.InstalledVersion == "3.0.20-1~deb12u2"
	input.PkgID == "openssl@3.0.20-1~deb12u2"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-14456"
	cve_2026_14456_pkgid_match
	# Trivy omits empty FixedVersion (omitempty); missing/empty means unfixed.
	object.get(input, "FixedVersion", "") == ""
}


# CVE-2025-69720 (ncurses family) - no fixed release for Debian bookworm at review time
# Review-by: 2026-09-08 (manual removal)
# Rationale: Debian bookworm still lists ncurses 6.4-4 as vulnerable/no-dsa at the 2026-08-09 review; keep exact package/version scope while monitoring Debian/Trivy metadata.
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

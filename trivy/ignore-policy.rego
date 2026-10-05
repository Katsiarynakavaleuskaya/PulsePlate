package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed at time of suppression
# - Limit to the installed versions reported at time of suppression
# - CI enforces a single file-level expiry (exactly one "Suppression expires: YYYY-MM-DD" per policy file)
#
# Suppression expires: 2026-10-30 (manual removal)
# Last reviewed: 2026-10-04 (zlib/ncurses/OpenSSL; util-linux53615 retired)
# Documented in: docs/security/CVE-2026-27171-zlib1g.md, docs/security/CVE-2025-69720-ncurses.md, docs/security/CVE-2026-84782-openssl.md

# CVE-2026-27171 (zlib1g) - no fixed release for Debian bookworm at review time
# Review-by: 2026-10-21 (manual removal)
# Rationale: Debian bookworm still lists zlib 1:1.2.13.dfsg-1 as vulnerable/no-dsa at the 2026-10-04 review, with no fixed Bookworm package currently; any source/backport/base migration requires separate reviewed evidence.
# Note: CI expiry is enforced once per policy file (see header); do not add another "Suppression expires:" line.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-27171
# Documented in: docs/security/CVE-2026-27171-zlib1g.md
# Removal condition: Remove when Debian bookworm publishes a fixed zlib1g package or Trivy metadata includes Fixed Version

cve_2026_27171_version_match if {
	input.InstalledVersion == "1:1.2.13.dfsg-1"
}

cve_2026_27171_pkgid_match if {
	input.PkgID == "zlib1g@1:1.2.13.dfsg-1"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-27171"
	input.PkgName == "zlib1g"
	cve_2026_27171_version_match
	cve_2026_27171_pkgid_match
	object.get(input, "FixedVersion", "") == ""
}

# CVE-2025-69720 (ncurses family) - no fixed release for Debian bookworm at review time
# Review-by: 2026-10-21 (manual removal)
# Rationale: Debian bookworm still lists ncurses 6.4-4 as vulnerable/no-dsa at the 2026-10-04 review; keep exact package/version scope while monitoring Debian/Trivy metadata.
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
	input.PkgName == "libncursesw6"
	input.PkgID == "libncursesw6@6.4-4"
}

cve_2025_69720_pkgid_match if {
	input.PkgName == "libtinfo6"
	input.PkgID == "libtinfo6@6.4-4"
}

cve_2025_69720_pkgid_match if {
	input.PkgName == "ncurses-base"
	input.PkgID == "ncurses-base@6.4-4"
}

cve_2025_69720_pkgid_match if {
	input.PkgName == "ncurses-bin"
	input.PkgID == "ncurses-bin@6.4-4"
}

ignore if {
	input.VulnerabilityID == "CVE-2025-69720"
	cve_2025_69720_pkg_match
	cve_2025_69720_version_match
	cve_2025_69720_pkgid_match
	object.get(input, "FixedVersion", "") == ""
}

# CVE-2026-84782 (OpenSSL) - no fixed Debian bookworm package at review time
# Review-by: 2026-10-21 (manual removal)
# Rationale: Bookworm 3.0.22-1~deb12u1 remains affected at the 2026-10-04 review; this HIGH-only exception retains affected-package risk and requires separate exact-head human acceptance.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-84782
# Documented in: docs/security/CVE-2026-84782-openssl.md
# Removal condition: Remove when a fixed Bookworm package is available or native Trivy reports a nonempty FixedVersion; do not extend deadlines automatically.

cve_2026_84782_pkgid_match if {
	input.PkgName == "libssl3"
	input.PkgID == "libssl3@3.0.22-1~deb12u1"
}

cve_2026_84782_pkgid_match if {
	input.PkgName == "openssl"
	input.PkgID == "openssl@3.0.22-1~deb12u1"
}

ignore if {
	input.VulnerabilityID == "CVE-2026-84782"
	input.Severity == "HIGH"
	input.InstalledVersion == "3.0.22-1~deb12u1"
	cve_2026_84782_pkgid_match
	# Native Trivy owns string decoding; raw Rego null does not equal empty.
	object.get(input, "FixedVersion", "") == ""
}

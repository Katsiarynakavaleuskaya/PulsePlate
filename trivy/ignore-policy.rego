package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed at time of suppression
# - Limit to the installed versions reported at time of suppression
# - CI enforces a single file-level expiry (exactly one "Suppression expires: YYYY-MM-DD" per policy file)
#
# Suppression expires: 2026-05-27 (manual removal)
# Documented in: docs/security/CVE-2026-0915-glibc.md, docs/security/CVE-2025-15281-glibc.md, docs/security/CVE-2026-27171-zlib1g.md, docs/security/CVE-2026-3184-util-linux.md

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

# CVE-2025-15281 (glibc) - upstream unfixed in GitHub runner base image
# Review-by: 2026-03-01 (manual removal)
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
# Review-by: 2026-05-10 (manual removal)
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

# CVE-2026-3184 (util-linux) - upstream unfixed in Debian bookworm
# Review-by: 2026-05-27 (manual removal)
# Rationale: Unfixed distro CVE; access control bypass via hostname canonicalization; LOW severity
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-3184
# Documented in: docs/security/CVE-2026-3184-util-linux.md
# Removal condition: Remove when Debian bookworm publishes a fixed util-linux package or Trivy metadata includes Fixed Version

# Helper rule: check if InstalledVersion matches observed version
cve_2026_3184_version_match if {
	input.InstalledVersion == "2.38.1-5+deb12u3"
}

# Helper rule: check if PkgID matches observed util-linux-extra package
cve_2026_3184_pkgid_match if {
	contains(input.PkgID, "util-linux-extra@2.38.1-5+deb12u3")
}

ignore if {
	input.VulnerabilityID == "CVE-2026-3184"
	input.PkgName == "util-linux-extra"
	cve_2026_3184_version_match
	cve_2026_3184_pkgid_match
}

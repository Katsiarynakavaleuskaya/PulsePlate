package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed (libc6 + libc-bin)
# - Limit to the installed versions reported at time of suppression
#
# Suppression expires: 2026-03-01 (manual removal)
# Documented in: docs/security/CVE-2026-0915-glibc.md, docs/security/CVE-2025-15281-glibc.md

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
# Rationale: Upstream unfixed; GitHub runner base image (deb12u13); no actionable remediation in repo
# Monitor: https://security-tracker.debian.org/tracker/CVE-2025-15281
# Documented in: docs/security/CVE-2025-15281-glibc.md

# Helper rule: check if PkgID matches allowed glibc packages
cve_2025_15281_pkgid_match if {
	startswith(input.PkgID, "libc6@2.36-9+deb12u13")
}

cve_2025_15281_pkgid_match if {
	startswith(input.PkgID, "libc-bin@2.36-9+deb12u13")
}

ignore if {
	input.VulnerabilityID == "CVE-2025-15281"
	allowed_packages := {"libc6", "libc-bin"}
	allowed_packages[input.PkgName]
	input.InstalledVersion == "2.36-9+deb12u13"
	cve_2025_15281_pkgid_match
}

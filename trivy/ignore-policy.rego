package trivy

default ignore = false

# Narrow suppression for CVE-2026-0915:
# - Limit to the specific OS packages observed in Trivy code-scanning alerts (#507/#508): libc6 + libc-bin
# - Limit to the exact installed version reported by Trivy at time of suppression
#
# Suppression expires: 2026-03-01 (manual removal)
# Documented in: docs/security/CVE-2026-0915-glibc.md

ignore {
	input.VulnerabilityID == "CVE-2026-0915"
	input.PkgName == "libc6"
	input.InstalledVersion == "2.36-9+deb12u13"
}

ignore {
	input.VulnerabilityID == "CVE-2026-0915"
	input.PkgName == "libc-bin"
	input.InstalledVersion == "2.36-9+deb12u13"
}

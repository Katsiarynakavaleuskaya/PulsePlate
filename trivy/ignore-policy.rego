package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed (libc6 + libc-bin)
# - Limit to the installed versions reported at time of suppression
#
# Suppression expires: 2026-03-01 (manual removal)
# Documented in:
# - docs/security/CVE-2026-0861-glibc.md
# - docs/security/CVE-2026-0915-glibc.md

ignore if {
	input.VulnerabilityID == "CVE-2026-0861"
	input.PkgName == "libc6"
	startswith(input.PkgID, "libc6@2.36-9+deb12u")
	# Allow current known bookworm patch levels for python:3.13.6-slim (documented elsewhere).
	regex.match("^2\\.36-9\\+deb12u(10|13)$", input.InstalledVersion)
}

ignore if {
	input.VulnerabilityID == "CVE-2026-0861"
	input.PkgName == "libc-bin"
	startswith(input.PkgID, "libc-bin@2.36-9+deb12u")
	regex.match("^2\\.36-9\\+deb12u(10|13)$", input.InstalledVersion)
}

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

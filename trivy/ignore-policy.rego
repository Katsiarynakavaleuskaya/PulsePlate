package trivy

import rego.v1

default ignore := false

# Suppression expires: 2026-12-26
# Review-by: 2026-12-26
# Trivy's Debian 12 advisory lacks the fix carried by this qualified backport.
# https://security-tracker.debian.org/tracker/CVE-2026-124851
# See docs/security/CVE-2026-124851-libzstd.md. Retire on a supported official
# Bookworm fix or scanner recognition of the qualified backport.
ignore if {
	input.VulnerabilityID == "CVE-2026-124851"
	input.PkgName == "libzstd1"
	input.PkgID == "libzstd1@1.5.7+dfsg-1+deb13u1~pulseplate12+1"
	input.InstalledVersion == "1.5.7+dfsg-1+deb13u1~pulseplate12+1"
	input.PkgIdentifier.PURL == "pkg:deb/debian/libzstd1@1.5.7%2Bdfsg-1%2Bdeb13u1~pulseplate12%2B1?arch=amd64&distro=debian-12.15"
	input.DataSource.ID == "debian"
	input.DataSource.Name == "Debian Security Tracker"
	input.DataSource.URL == "https://salsa.debian.org/security-tracker-team/security-tracker"
	input.Severity == "HIGH"
	input.Status == "affected"
	object.get(input, "FixedVersion", "") == ""
	time.now_ns() < time.parse_rfc3339_ns("2026-12-27T00:00:00Z")
}

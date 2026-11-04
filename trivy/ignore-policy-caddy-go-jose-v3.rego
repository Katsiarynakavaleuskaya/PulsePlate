package trivy

import rego.v1

# CVE-2026-116587 / GHSA-mgcc-cww5-fp2q; PR #2497, accepted 2026-10-28.
# Owner: @katsiaryna_kavaleuskaya (Security/SRE). Permanent exit: PR #2494.
# Review-by: 2026-10-30
# Suppression expires: 2026-11-04
# Only the explicit frontend Caddy CI caller may select this policy after binding
# the original image, actual binary, loaded synthetic configuration and full report.
# Trivy's input is one DetectedVulnerability, NOT the image/result envelope.
# Target/Class/Type/image/config scope is enforced by that existing report owner.
# https://github.com/advisories/GHSA-mgcc-cww5-fp2q
# docs/security/CVE-2026-116587-caddy-go-jose.md

default ignore := false

ignore if {
	input.VulnerabilityID == "CVE-2026-116587"
	input.PkgName == "github.com/go-jose/go-jose/v3"
	input.PkgID == "github.com/go-jose/go-jose/v3@v3.0.5"
	input.PkgIdentifier.PURL == "pkg:golang/github.com/go-jose/go-jose/v3@v3.0.5"
	input.InstalledVersion == "v3.0.5"
	input.Severity == "HIGH"
	input.Status == "affected"
	object.get(input, "FixedVersion", "") == ""
	time.now_ns() >= time.parse_rfc3339_ns("2026-10-28T00:00:00Z")
	time.now_ns() < time.parse_rfc3339_ns("2026-10-31T00:00:00Z")
	time.now_ns() < time.parse_rfc3339_ns("2026-11-05T00:00:00Z")
}

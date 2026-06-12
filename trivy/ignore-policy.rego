package trivy

import rego.v1

default ignore := false

# Narrow suppressions for Trivy code-scanning alerts:
# - Limit to the specific OS packages observed at time of suppression
# - Limit to the installed versions reported at time of suppression
# - CI enforces a single file-level expiry (exactly one "Suppression expires: YYYY-MM-DD" per policy file)
#
# Suppression expires: 2026-06-27 (manual removal)
# Last reviewed: 2026-05-28
# Documented in: docs/security/CVE-2026-27171-zlib1g.md, docs/security/CVE-2026-3184-util-linux.md, docs/security/CVE-2025-69720-ncurses.md, docs/security/CVE-2026-48959-perl-base.md, docs/security/CVE-2026-48962-perl-base.md

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

# CVE-2026-48962 (perl-base / IO::Compress) - no fixed Debian bookworm perl source at review time
# Review-by: 2026-06-27 (manual removal)
# Rationale: Debian bookworm perl-base remains vulnerable with no actionable fixed version in this image context; Python runtime does not execute Perl IO::Compress/File::GlobMapper on attacker-controlled output globs.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-48962
# Documented in: docs/security/CVE-2026-48962-perl-base.md
# Removal condition: Remove when Debian bookworm publishes a fixed perl/perl-base package, Trivy reports a fixed version for alert #602, or production removes perl-base with passing Docker/Trivy evidence.

cve_2026_48962_perl_base_version_match if {
	input.InstalledVersion == "5.36.0-7+deb12u3"
}

cve_2026_48962_perl_base_pkgid_match if {
	startswith(input.PkgID, "perl-base@5.36.0-7+deb12u3")
}

cve_2026_48962_perl_base_fixed_version_unavailable if {
	not input.FixedVersion
}

cve_2026_48962_perl_base_fixed_version_unavailable if {
	input.FixedVersion == ""
}

cve_2026_48962_perl_base_fixed_version_unavailable if {
	input.FixedVersion == null
}

ignore if {
	input.VulnerabilityID == "CVE-2026-48962"
	input.PkgName == "perl-base"
	cve_2026_48962_perl_base_version_match
	cve_2026_48962_perl_base_pkgid_match
	cve_2026_48962_perl_base_fixed_version_unavailable
}

# CVE-2026-48959 (perl-base / IO::Uncompress::Unzip) - no fixed Debian bookworm perl source at review time
# Review-by: 2026-06-27 (manual removal)
# Rationale: Debian bookworm perl-base remains vulnerable with no actionable fixed version in this image context; PulsePlate's Python runtime does not execute Perl IO::Uncompress::Unzip on attacker-controlled ZIP entries.
# Monitor: https://security-tracker.debian.org/tracker/CVE-2026-48959
# Documented in: docs/security/CVE-2026-48959-perl-base.md
# Removal condition: Remove when Debian bookworm publishes a fixed perl/perl-base package, Trivy reports a fixed version for alert #610, or production removes perl-base with passing Docker/Trivy evidence.

cve_2026_48959_perl_base_version_match if {
	input.InstalledVersion == "5.36.0-7+deb12u3"
}

cve_2026_48959_perl_base_pkgid_match if {
	startswith(input.PkgID, "perl-base@5.36.0-7+deb12u3")
}

cve_2026_48959_perl_base_fixed_version_unavailable if {
	not input.FixedVersion
}

cve_2026_48959_perl_base_fixed_version_unavailable if {
	input.FixedVersion == ""
}

cve_2026_48959_perl_base_fixed_version_unavailable if {
	input.FixedVersion == null
}

ignore if {
	input.VulnerabilityID == "CVE-2026-48959"
	input.PkgName == "perl-base"
	cve_2026_48959_perl_base_version_match
	cve_2026_48959_perl_base_pkgid_match
	cve_2026_48959_perl_base_fixed_version_unavailable
}

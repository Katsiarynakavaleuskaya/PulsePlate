#!/bin/bash
# Build the independently checked Debian security source with Bookworm tooling.
set -Eeuo pipefail
umask 022

donor=1.5.7+dfsg-1+deb13u1
backport="$donor~pulseplate12+1"
work=/tmp/pulseplate-libzstd
output=/opt/pulseplate-libzstd
builder=pulseplate-zstd-build
apt_secure=(
    -o Acquire::Check-Valid-Until=true
    -o Acquire::AllowInsecureRepositories=false
    -o APT::Get::AllowUnauthenticated=false
)

verify_source() {
    sha256sum -c <<'HASH'
32f2d49685864a4f03f639ac59cfd19674b650e1f2b007705b01342cb0fd5cc3  libzstd_1.5.7+dfsg-1+deb13u1.dsc
0c092ef267edce57ba7f3f2645c861f72eaf5e76273c6c3632869423464b90a5  libzstd_1.5.7+dfsg.orig.tar.xz
adc44c628b74a7a4eff4fbed4681e8fdc8ffe8e4bc31aa9ea6a41a07a2281d23  libzstd_1.5.7+dfsg-1+deb13u1.debian.tar.xz
HASH
}

prepare() {
    test "$(id -u)" = 0
    grep -Fxq ID=debian /etc/os-release
    grep -Fxq VERSION_CODENAME=bookworm /etc/os-release
    test "$(dpkg --print-architecture)" = amd64
    export DEBIAN_FRONTEND=noninteractive
    # Only source records from the donor suite are visible to APT.
    cat > /etc/apt/sources.list.d/pulseplate-libzstd-donor.sources <<'APT'
Types: deb-src
URIs: https://security.debian.org/debian-security
Suites: trixie-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
APT
    apt-get "${apt_secure[@]}" -o APT::Update::Error-Mode=any update
    apt-get "${apt_secure[@]}" install -y --no-install-recommends \
        build-essential cmake debhelper dpkg-dev help2man less liblz4-dev liblzma-dev patch python3 zlib1g-dev
    useradd --system --user-group --create-home --home-dir "/home/$builder" --shell /usr/sbin/nologin "$builder"
    chmod 0700 "/home/$builder"
    install -d -m 0700 -o "$builder" -g "$builder" "$work" "$output"
    cd "$work"
    apt-get "${apt_secure[@]}" source --download-only --only-source "libzstd=$donor"
    verify_source
    chown "$builder:$builder" "libzstd_$donor.dsc" libzstd_1.5.7+dfsg.orig.tar.xz "libzstd_$donor.debian.tar.xz"
    cp /var/lib/apt/lists/*trixie-security*InRelease "$output/donor.InRelease"
    apt-cache showsrc libzstd > "$output/donor.Sources.txt"
    rm -rf /var/lib/apt/lists/*
}

build() {
    test "$(id -un)" = "$builder"
    test "$(id -u)" -ne 0
    test "$HOME" = "/home/$builder"
    test -w "$HOME"
    test -w "$work"
    test -w "$output"
    cd "$work"
    verify_source
    test "$(dpkg --print-architecture)" = amd64
    dpkg --compare-versions "$backport" gt '1.5.4+dfsg2-5'
    dpkg --compare-versions "$backport" lt "$donor"
    dpkg-source -x "libzstd_$donor.dsc" source
    cd source
    printf '%s\n' '6093ac3e24ef7e08c8b669736137502ff12209a857af6ada3795d8c978a64edd  debian/patches/CVE-2026-124851.patch' | sha256sum -c
    grep -Fx 'CVE-2026-124851.patch' .pc/applied-patches
    patch --dry-run --batch --fuzz=0 -R -p1 < debian/patches/CVE-2026-124851.patch

    # Bookworm has debhelper 13 and the Debian 12 dpkg build API.
    python -I - "$backport" <<'PY'
from pathlib import Path
import sys

control = Path("debian/control")
source_control = control.read_text()
changes = (
    (" debhelper (>> 13.15.2~),\n dh-package-notes,\n dpkg-build-api (= 1),", " debhelper-compat (= 13),"),
    ("X-DH-Compat: 14\n", "Rules-Requires-Root: no\n"),
    ("Section: libs\nDescription:", "Section: libs\nDepends: ${misc:Depends}, ${shlibs:Depends}\nDescription:"),
    ("Section: utils\nDescription:", "Section: utils\nDepends: ${misc:Depends}, ${shlibs:Depends}\nDescription:"),
    ("Package-Type: udeb\n", "Package-Type: udeb\nDepends: ${misc:Depends}, ${shlibs:Depends}\n"),
)
for observed, updated in changes:
    if source_control.count(observed) != 1:
        raise SystemExit("Debian donor packaging differs")
    source_control = source_control.replace(observed, updated, 1)
control.write_text(source_control)
rules = Path("debian/rules")
content = rules.read_text()
package_notes = "include /usr/share/debhelper/dh_package_notes/package-notes.mk\n"
if content.count(package_notes) != 1:
    raise SystemExit("Debian donor rules differ")
rules.write_text(content.replace(package_notes, "", 1))
changelog = Path("debian/changelog")
changelog.write_text(
    f"libzstd ({sys.argv[1]}) bookworm; urgency=medium\n\n"
    "  * Rebuild the Debian security source on Bookworm for PulsePlate.\n"
    "  * Retain Debian's CVE-2026-124851 correction and Bookworm build tools.\n\n"
    " -- PulsePlate Build <pulseplate@pm.me>  Thu, 26 Nov 2026 11:00:00 +0000\n\n"
    + changelog.read_text()
)
PY
    DEB_BUILD_OPTIONS=parallel=2 dpkg-buildpackage -b -uc -us
    package="../libzstd1_${backport}_amd64.deb"
    test "$(dpkg-deb -f "$package" Package)" = libzstd1
    test "$(dpkg-deb -f "$package" Source)" = libzstd
    test "$(dpkg-deb -f "$package" Version)" = "$backport"
    test "$(dpkg-deb -f "$package" Architecture)" = amd64
    test "$(dpkg-deb -f "$package" Multi-Arch)" = same
    test -n "$(dpkg-deb -f "$package" Depends)"
    dpkg-deb --fsys-tarfile "$package" | tar --numeric-owner -tvf - > "$output/package-data.txt"
    awk '
        { sub(/^\.\//, "", $6) }
        $6 == "usr/lib/x86_64-linux-gnu/libzstd.so.1" { alias_owned = ($2 == "0/0") }
        $6 == "usr/lib/x86_64-linux-gnu/libzstd.so.1.5.7" { library_owned = ($2 == "0/0") }
        END { if (!alias_owned || !library_owned) exit 1 }
    ' "$output/package-data.txt"
    install -m 0644 "$package" "$output/libzstd1.deb"
    (cd "$output" && sha256sum libzstd1.deb > SHA256SUMS)
}

case "${1:-}" in
    prepare) prepare ;;
    build) build ;;
    *) printf '%s\n' 'Expected prepare or build' >&2; exit 2 ;;
esac

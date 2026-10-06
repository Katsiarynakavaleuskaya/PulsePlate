# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for PulsePlate
# Optimized for production with minimal image size and security

# Centralize pip upgrade range (SoT) to avoid drift across stages.
ARG PIP_VERSION_RANGE="pip>=26.0,<27.0"
# SQLite source pins are intentionally mirrored in scripts/ci/docker_source_artifacts.json.
# Docker COPY source paths are literal, so a SQLite bump must update the manifest,
# the COPY filename below, and these SHA3 parts together.
ARG SQLITE_AUTOCONF_VERSION="3530200"
ARG SQLITE_AUTOCONF_SHA3_256_PART_1="025328da"
ARG SQLITE_AUTOCONF_SHA3_256_PART_2="165109f4"
ARG SQLITE_AUTOCONF_SHA3_256_PART_3="8abccc6e"
ARG SQLITE_AUTOCONF_SHA3_256_PART_4="74785080"
ARG SQLITE_AUTOCONF_SHA3_256_PART_5="60804412"
ARG SQLITE_AUTOCONF_SHA3_256_PART_6="bed2bd81"
ARG SQLITE_AUTOCONF_SHA3_256_PART_7="d47e98ba"
ARG SQLITE_AUTOCONF_SHA3_256_PART_8="1b72983b"

# Exact Linux/amd64 SDK interpreter family; runtime Python keeps its existing pin.
ARG PSYCOPG_SDK_PYTHON_IMAGE="python@sha256:7a6b87c02e1f4d6bb572e379235cbbdd7892add0572442c9b0b860a3f5aa9857"

FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS native-builder
ARG PSYCOPG_SDK_PYTHON_IMAGE
RUN case "${PSYCOPG_SDK_PYTHON_IMAGE}" in \
      python@sha256:9fd630803ec3446920ed6b64d20150bd724c1751e71817293a4230522c1a384a|python@sha256:a594f7e9df8a4c431265125b5f5d90cd1b81c8a8797fefee69d5b3544be11111|python@sha256:7a6b87c02e1f4d6bb572e379235cbbdd7892add0572442c9b0b860a3f5aa9857) ;; \
      *) echo "Unsupported Psycopg SDK interpreter image" >&2; exit 1 ;; \
    esac \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential bison flex libkrb5-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY scripts/ci/docker_source_artifacts.json scripts/ci/fetch_docker_source_artifacts.py /tooling/scripts/ci/
COPY build/docker-sources/zlib-1.3.2.tar.gz build/docker-sources/ncurses-6.6.tar.gz build/docker-sources/openssl-3.5.9.tar.gz build/docker-sources/postgresql-18.6.tar.gz build/docker-sources/zlib-gzwrite-fix-df84af25dc1942490e1d1c899a07619152a46148.patch /input/native/
RUN --network=none python - <<'PY'
import sys
sys.path.insert(0, "/tooling/scripts/ci")
from pathlib import Path
import tarfile
from fetch_docker_source_artifacts import load_manifest, validate_source_payload

records = load_manifest(Path("/tooling/scripts/ci/docker_source_artifacts.json"))
for name in ("zlib", "ncurses", "openssl", "postgresql", "zlib-gzwrite-fix"):
    matches = [record for record in records if record.name == name]
    if len(matches) != 1:
        raise SystemExit("Native source identity is missing or duplicated")
    record = matches[0]
    payload = Path("/input/native", record.filename).read_bytes()
    validate_source_payload(record, payload)
    if name != "zlib-gzwrite-fix":
        with tarfile.open(Path("/input/native", record.filename), "r:gz") as archive:
            archive.extractall("/build/source", filter="data")
PY
RUN --network=none <<'SH'
set -eu
cd /build/source/zlib-1.3.2
python - <<'PY'
from hashlib import sha256
from pathlib import Path
import json
rows = {p.as_posix(): sha256(p.read_bytes()).hexdigest() for p in Path(".").rglob("*") if p.is_file() and not p.is_symlink()}
Path("/tmp/zlib-original-members.json").write_text(json.dumps(rows))
PY
patch --batch --forward -p1 --input /input/native/zlib-gzwrite-fix-df84af25dc1942490e1d1c899a07619152a46148.patch
python - <<'PY'
from hashlib import sha256
from pathlib import Path
import json
before = json.loads(Path("/tmp/zlib-original-members.json").read_text())
after = {p.as_posix(): sha256(p.read_bytes()).hexdigest() for p in Path(".").rglob("*") if p.is_file() and not p.is_symlink()}
if set(before) != set(after) or {name for name in before if before[name] != after[name]} != {"gzwrite.c"}:
    raise SystemExit("zlib patch changed another source member or failed to apply")
if len(before) != 254 or after["gzwrite.c"] != ('31d0da14' '0edf382b' '82b13e2d' '87a22f59' 'e158d901' '4ee02645' '9e01cf43' '7d0ab07d'):
    raise SystemExit("zlib patched source fingerprint mismatch")
PY
./configure --prefix=/usr/local --libdir=/usr/local/lib --shared
make -j2
make DESTDIR=/native install
cp -a /native/usr/local/. /usr/local/
cd /build/source/ncurses-6.6
./configure --prefix=/usr/local --with-shared --without-debug --without-ada \
    --enable-widec --with-abi-version=6 --with-termlib=tinfo --with-versioned-syms --enable-pc-files \
    --with-pkg-config-libdir=/usr/local/lib/pkgconfig
make -j2
make DESTDIR=/native install
cp -a /native/usr/local/. /usr/local/
ldconfig
python - <<'PY'
import subprocess
import sys

result = subprocess.run(
    ["/bin/bash", "--noprofile", "--norc", "-c", "printf 'pulseplate terminal ABI\\n'"],
    capture_output=True, text=True, check=False,
)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
if result.returncode != 0 or result.stderr or result.stdout != "pulseplate terminal ABI\n":
    raise SystemExit("Debian bash rejected the replacement terminal ABI")
PY
cd /build/source/openssl-openssl-45e844f
perl ./Configure linux-x86_64 shared --prefix=/usr/local --libdir=lib --openssldir=/usr/lib/ssl
make -j2 build_sw
make DESTDIR=/native install_sw
cp -a /native/usr/local/. /usr/local/
ldconfig
cd /build/source/postgresql-18.6
CPPFLAGS=-I/usr/local/include LDFLAGS='-L/usr/local/lib -Wl,-rpath,/usr/local/lib' \
    ./configure --prefix=/usr/local --libdir=/usr/local/lib --with-ssl=openssl \
    --with-gssapi --without-ldap --without-icu --without-readline
make -j2 -C src/include all
make -j2 -C src/interfaces/libpq all
make -j2 -C src/bin/pg_config all
make -C src/interfaces/libpq DESTDIR=/native install
make -C src/bin/pg_config DESTDIR=/native install
install -d /native/usr/local/include/libpq
install -m 644 src/include/postgres_ext.h src/include/pg_config.h src/include/pg_config_os.h src/include/pg_config_manual.h /native/usr/local/include/
install -m 644 src/include/libpq/libpq-fs.h /native/usr/local/include/libpq/
cp -a /native/usr/local/. /usr/local/
ldconfig
install -d /native/usr/local/share/doc/pulseplate-native
install -m 644 /build/source/zlib-1.3.2/LICENSE /native/usr/local/share/doc/pulseplate-native/ZLIB-LICENSE
install -m 644 /build/source/ncurses-6.6/COPYING /native/usr/local/share/doc/pulseplate-native/NCURSES-COPYING
install -m 644 /build/source/openssl-openssl-45e844f/LICENSE.txt /native/usr/local/share/doc/pulseplate-native/OPENSSL-LICENSE
install -m 644 /build/source/openssl-openssl-45e844f/apps/openssl.cnf /native/usr/local/share/doc/pulseplate-native/openssl.cnf
install -m 644 /build/source/postgresql-18.6/COPYRIGHT /native/usr/local/share/doc/pulseplate-native/LIBPQ-COPYRIGHT
install -m 644 /tooling/scripts/ci/docker_source_artifacts.json /native/usr/local/share/doc/pulseplate-native/docker_source_artifacts.json
SH

# Archive and binary build inputs are acquired without running source metadata.
FROM ${PSYCOPG_SDK_PYTHON_IMAGE} AS psycopg-inputs
ARG PULSEPLATE_PYTHON_INDEX_URL
COPY scripts/ci/install_locked_python_requirements.py scripts/ci/check_private_python_proxy_health.py /tooling/scripts/ci/
RUN --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_netrc,required=false <<'SH'
set -eu
index="${PULSEPLATE_PYTHON_INDEX_URL:-}"
if [ -f /run/secrets/pp_py_index ]; then index="$(cat /run/secrets/pp_py_index)"; fi
if [ -f /run/secrets/pp_netrc ]; then
    test ! -e /root/.netrc
    cp /run/secrets/pp_netrc /root/.netrc
    chmod 600 /root/.netrc
fi
trap 'rm -f /root/.netrc' EXIT
test -n "$index"
python /tooling/scripts/ci/install_locked_python_requirements.py --index-url "$index" --prefetch-psycopg-source /input/source
python /tooling/scripts/ci/install_locked_python_requirements.py --index-url "$index" --prefetch-psycopg-build-wheels /input/build-wheels
SH

# No credentialed HOME, configuration, cache or environment crosses into this build.
FROM native-builder AS psycopg-wheel-builder
COPY --from=psycopg-inputs /input/ /input/psycopg/
COPY scripts/ci/install_locked_python_requirements.py /tooling/scripts/ci/install_locked_python_requirements.py
RUN --network=none /usr/bin/env -i HOME=/tmp PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 TMPDIR=/tmp \
    /usr/local/bin/python /tooling/scripts/ci/install_locked_python_requirements.py --build-psycopg-c \
    --psycopg-source-archive /input/psycopg/source/psycopg_c-3.3.4.tar.gz \
    --psycopg-build-wheels /input/psycopg/build-wheels --psycopg-native-root / \
    --psycopg-wheel-output /output/psycopg-sdk

FROM scratch AS psycopg-sdk
COPY --from=native-builder /native/ /
COPY --from=psycopg-wheel-builder /output/psycopg-sdk/ /psycopg-sdk/

# Preserve the source-built relative SONAME aliases without exporting static archives.
FROM native-builder AS native-shared-runtime
RUN --network=none mkdir -p /native-shared-libraries \
    && cp -a /native/usr/local/lib/*.so* /native-shared-libraries/

# Stage 1: Build stage
FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG PULSEPLATE_PYTHON_INDEX_URL
ARG PULSEPLATE_PYTHON_TRUSTED_HOST=""
ARG PULSEPLATE_REQUIREMENTS_FILE="requirements-docker-runtime.txt"

# Install system dependencies for building (curl removed - not needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    ca-certificates \
    libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_PYTHON_VERSION_WARNING=1 \
    PULSEPLATE_DOCKER_SINGLE_PASS_LOCKED_INSTALL=1 \
    PULSEPLATE_DOCKER_PIP_LAYER_CACHE=1

# Centralize pip version range (SoT) for CVE fixes.
ARG PIP_VERSION_RANGE
COPY scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/

# SECURITY (CVE-2026-1703):
# Ensure pip is upgraded in the venv before installing dependencies.
# We must upgrade pip inside the image (system + venv) because scanners flag installed pip dist-info.
# requirements.in cannot affect pip shipped in the base image.
# Policy: do not pin exact pip in Dockerfile; use a safe version range instead.
# Mirror-lag fallback is governed by install_locked_python_requirements.py and the sha256 manifest.
# BuildKit cache mount speeds rebuilds; omit --no-cache-dir so pip can use the mounted HTTP cache.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi && \
    rm -rf /tmp/pulseplate-ci

COPY --from=native-shared-runtime /native-shared-libraries/ /usr/local/lib/
COPY --from=psycopg-wheel-builder /output/psycopg-sdk/ /opt/psycopg-sdk/
RUN ldconfig

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-ci-lite.txt requirements-docker-runtime.txt constraints.txt ./
COPY scripts/ci/check_python_startup_hooks.py scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json scripts/ci/check_private_python_proxy_health.py /tmp/pulseplate-ci/
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    case "${PULSEPLATE_REQUIREMENTS_FILE}" in \
      requirements.txt|requirements-ci-lite.txt|requirements-docker-runtime.txt) ;; \
      *) \
        echo "Unsupported Docker requirements profile: ${PULSEPLATE_REQUIREMENTS_FILE}" >&2; \
        exit 1; \
        ;; \
    esac; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}" \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-mode direct-proxy \
        --prefetch-only --wheelhouse-dir /opt/runtime-wheelhouse --psycopg-sdk /opt/psycopg-sdk \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable /opt/venv/bin/python \
        --requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}" \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-mode direct-proxy \
        --prefetch-only --wheelhouse-dir /opt/runtime-wheelhouse --psycopg-sdk /opt/psycopg-sdk \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi
RUN --network=none /opt/venv/bin/python /tmp/pulseplate-ci/install_locked_python_requirements.py \
    --python-executable /opt/venv/bin/python --consume-only \
    --wheelhouse-dir /opt/runtime-wheelhouse --psycopg-sdk /opt/psycopg-sdk \
    --requirements-file "${PULSEPLATE_REQUIREMENTS_FILE}" --constraints-file constraints.txt \
    --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py && \
    # Remove setuptools from runtime image to fix GHSA-58pv-8j8x-9vj2 (jaraco.context vulnerability)
    # setuptools is only needed for build-time (pip install), not runtime
    /opt/venv/bin/pip uninstall -y setuptools wheel && \
    /opt/venv/bin/python - <<'PY'
import importlib.util, sys
if importlib.util.find_spec("setuptools") is not None:
    sys.stderr.write("setuptools leaked into runtime venv\n")
    sys.exit(1)
PY

# Stage 1b: SQLite runtime library stage
# SECURITY (CVE-2026-11822, CVE-2026-11824):
# Debian bookworm libsqlite3-0 is currently flagged by Trivy with no fixed
# package metadata. Build SQLite 3.53.2 from a pre-fetched official autoconf
# source tarball with SHA3 verification, then copy only the shared runtime
# library into runtime-base. The tarball is prepared outside Docker by
# scripts/ci/fetch_docker_source_artifacts.py so Docker builds do not perform
# hidden live upstream downloads.
FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS sqlite-builder

ARG SQLITE_AUTOCONF_VERSION
ARG SQLITE_AUTOCONF_SHA3_256_PART_1
ARG SQLITE_AUTOCONF_SHA3_256_PART_2
ARG SQLITE_AUTOCONF_SHA3_256_PART_3
ARG SQLITE_AUTOCONF_SHA3_256_PART_4
ARG SQLITE_AUTOCONF_SHA3_256_PART_5
ARG SQLITE_AUTOCONF_SHA3_256_PART_6
ARG SQLITE_AUTOCONF_SHA3_256_PART_7
ARG SQLITE_AUTOCONF_SHA3_256_PART_8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY build/docker-sources/sqlite-autoconf-3530200.tar.gz /tmp/sqlite-autoconf.tar.gz

RUN python - <<'PY'
from hashlib import sha3_256
from pathlib import Path
import os
import sys

expected = "".join(
    os.environ[f"SQLITE_AUTOCONF_SHA3_256_PART_{index}"] for index in range(1, 9)
)
payload = Path("/tmp/sqlite-autoconf.tar.gz").read_bytes()
actual = sha3_256(payload).hexdigest()
if actual != expected:
    sys.stderr.write(f"SQLite source SHA3 mismatch: expected {expected}, got {actual}\n")
    sys.exit(1)
PY

RUN tar -xzf /tmp/sqlite-autoconf.tar.gz -C /tmp \
    && cd "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}" \
    && ./configure --prefix=/usr/local --disable-static --enable-shared \
    && make -j"$(nproc)" \
    && make install \
    && /usr/local/bin/sqlite3 -version | grep '^3\.53\.2 ' \
    && rm -rf "/tmp/sqlite-autoconf-${SQLITE_AUTOCONF_VERSION}" /tmp/sqlite-autoconf.tar.gz

# Build only the reviewed shared UUID library; reuse the existing Bookworm toolchain.
FROM sqlite-builder AS uuid-builder
COPY build/docker-sources/util-linux-2.42.3.tar.gz /tmp/util-linux.tar.gz
COPY scripts/ci/docker_source_artifacts.json /opt/libuuid/docker_source_artifacts.json
RUN python - <<'PY'
from hashlib import sha256, sha3_256
import json
from pathlib import Path

manifest = json.loads(Path("/opt/libuuid/docker_source_artifacts.json").read_text())
records = [record for record in manifest["artifacts"] if record["name"] == "util-linux"]
if len(records) != 1 or records[0]["version"] != "2.42.3":
    raise SystemExit("Expected one reviewed util-linux 2.42.3 source")
payload = Path("/tmp/util-linux.tar.gz").read_bytes()
if sha3_256(payload).hexdigest() != "".join(records[0]["sha3_256_parts"]):
    raise SystemExit("util-linux source SHA3 mismatch")
if sha256(payload).hexdigest() != "".join(records[0]["sha256_parts"]):
    raise SystemExit("util-linux source SHA256 mismatch")
print("util-linux source SHA256:", sha256(payload).hexdigest())
PY
RUN tar -xzf /tmp/util-linux.tar.gz -C /tmp \
    && cd /tmp/util-linux-2.42.3 \
    && ./configure --disable-all-programs --enable-libuuid --disable-static \
        --enable-shared --disable-nls --without-systemd --without-udev --disable-asciidoc \
    && make -j2 libuuid.la \
    && install -m 0644 .libs/libuuid.so.1.3.0 /opt/libuuid/libuuid.so.1.3.0 \
    && install -m 0644 libuuid/COPYING /opt/libuuid/COPYING \
    && (cd /opt/libuuid && sha256sum libuuid.so.1.3.0 > SHA256SUMS)

# CVE-2026-103111: production-only PCRE2 replacement using reviewed source closure.
FROM sqlite-builder AS pcre2-builder
COPY build/docker-sources/pcre2-10.49.tar.gz /tmp/pcre2.tar.gz
COPY build/docker-sources/sljit-de0259c7aaf36aa40cba8014f3fad3edde9307f9.tar.gz /tmp/sljit.tar.gz
COPY scripts/ci/docker_source_artifacts.json /opt/pcre2/docker_source_artifacts.json
RUN --network=none python - <<'PYCODE'
from hashlib import sha3_256
import json
from pathlib import Path

manifest = json.loads(Path("/opt/pcre2/docker_source_artifacts.json").read_text())
for name, version in (
    ("pcre2", "10.49"),
    ("sljit", "de0259c7aaf36aa40cba8014f3fad3edde9307f9"),
):
    records = [record for record in manifest["artifacts"] if record["name"] == name]
    if len(records) != 1 or records[0]["version"] != version:
        raise SystemExit(f"Expected one reviewed {name} {version} source")
    payload = Path(f"/tmp/{name}.tar.gz").read_bytes()
    if sha3_256(payload).hexdigest() != "".join(records[0]["sha3_256_parts"]):
        raise SystemExit(f"{name} source SHA3 mismatch")
    print(name, "source SHA3:", sha3_256(payload).hexdigest())
PYCODE
RUN --network=none mkdir -p /tmp/pcre2-source /opt/pcre2 \
    && tar -xzf /tmp/pcre2.tar.gz --strip-components=1 -C /tmp/pcre2-source \
    && tar -xzf /tmp/sljit.tar.gz --strip-components=1 -C /tmp/pcre2-source/deps/sljit \
    && cd /tmp/pcre2-source \
    && ./configure --prefix=/usr/local --enable-shared --disable-static \
        --enable-jit --enable-unicode --enable-pcre2-8 --disable-pcre2-16 \
        --disable-pcre2-32 --disable-pcre2grep-libz --disable-pcre2grep-libbz2 \
        --disable-pcre2test-libreadline \
    && make -j2 libpcre2-8.la \
    && install -m 0644 .libs/libpcre2-8.so.0.16.1 /opt/pcre2/libpcre2-8.so.0.16.1 \
    && install -m 0644 LICENCE.md /opt/pcre2/PCRE2-LICENCE.md \
    && install -m 0644 COPYING /opt/pcre2/PCRE2-COPYING \
    && install -m 0644 deps/sljit/LICENSE /opt/pcre2/SLJIT-LICENSE \
    && (cd /opt/pcre2 && sha256sum libpcre2-8.so.0.16.1 > SHA256SUMS)

# Stage 2: Runtime base stage
# NOTE: Keep system package manager tools here so the development stage can install tools via apt.
FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64 AS runtime-base

# Re-declare build arg in this stage.
ARG PIP_VERSION_RANGE
ARG PULSEPLATE_PYTHON_INDEX_URL
ARG PULSEPLATE_PYTHON_TRUSTED_HOST=""

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# SECURITY (CVE-2026-1703):
# The base image may ship with an affected pip (e.g., 25.2) in system site-packages.
# Upgrade it so scanners do not detect pip 25.2 at /usr/local/lib/... in the runtime image.
# We must upgrade pip inside the image (system + venv) because scanners flag installed pip dist-info.
# requirements.in cannot affect pip shipped in the base image.
# Policy: do not pin exact pip in Dockerfile; use a safe version range instead.
COPY scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --upgrade-pip-only \
        --upgrade-pip-spec "${PIP_VERSION_RANGE}" \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi && \
    rm -rf /tmp/pulseplate-ci

# Install runtime dependencies only (curl removed - using Python for healthcheck)
# NOTE: libtasn1-6 comes transitively via libgnutls30 (required for TLS/HTTPS).
# CVE-2025-13151 is NOT fixed in Debian bookworm as of 2026-01 (no patched version available).
# Tracking: https://security-tracker.debian.org/tracker/CVE-2025-13151
# Revisit when bookworm publishes a fixed package.
#
# Security hardening:
# Explicitly install libc6/libc-bin from the current bookworm repositories and
# fail the build unless the image reaches Debian's fixed line for CVE-2025-8058.
# Explicitly install libgnutls30, alongside the existing OpenSSL packages, so
# runtime-base/development layers take Debian's latest available bookworm-security
# package instead of a stale base-layer copy. The final production target then
# prunes apt/gpgv/libgnutls30 and the CI runtime surface guard fails closed if
# that package-manager/GnuTLS surface returns.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libc-bin \
        libc6 \
        libgnutls30 \
        libpcre2-8-0 \
        libgssapi-krb5-2 \
        libssl3 \
        openssl \
    && for package in libc6 libc-bin; do \
        version="$(dpkg-query -W -f='${Version}' "${package}")"; \
        if ! dpkg --compare-versions "${version}" ge "2.36-9+deb12u13"; then \
            echo "${package} ${version} is below fixed glibc line 2.36-9+deb12u13" >&2; \
            exit 1; \
        fi; \
    done \
    && pcre2_version="$(dpkg-query -W -f='${Version}' libpcre2-8-0)" \
    && if ! dpkg --compare-versions "${pcre2_version}" ge "10.42-1+deb12u1"; then \
        echo "libpcre2-8-0 ${pcre2_version} is below fixed PCRE2 line 10.42-1+deb12u1" >&2; \
        exit 1; \
    fi \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY --from=sqlite-builder /usr/local/lib/libsqlite3.so* /usr/local/lib/
RUN printf '%s\n' '/usr/local/lib' > /etc/ld.so.conf.d/00-pulseplate-local-sqlite.conf \
    && ldconfig \
    && python - <<'PY'
import sqlite3
import sys

version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
if version < (3, 53, 2):
    sys.stderr.write(
        f"Python sqlite3 loaded SQLite {sqlite3.sqlite_version}, expected >= 3.53.2\n"
    )
    sys.exit(1)
PY

# Shared source builds own the native runtime and matching client linkage.
COPY --from=native-shared-runtime /native-shared-libraries/ /usr/local/lib/
COPY --from=native-builder /native/usr/local/lib/ossl-modules/ /usr/local/lib/ossl-modules/
COPY --from=native-builder /native/usr/local/lib/engines-3/ /usr/local/lib/engines-3/
COPY --from=native-builder /native/usr/local/bin/openssl /native/usr/local/bin/infocmp /usr/local/bin/
COPY --from=native-builder /native/usr/local/share/terminfo/ /usr/local/share/terminfo/
COPY --from=native-builder /native/usr/local/share/doc/pulseplate-native/ /usr/local/share/doc/pulseplate-native/
COPY --from=psycopg-wheel-builder /output/psycopg-sdk/psycopg-c-sdk.json /usr/local/share/doc/pulseplate-native/psycopg-c-sdk.json
RUN ldconfig

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r pulseplate && useradd -r -g pulseplate pulseplate

# Create app directory
WORKDIR /app

# Copy only necessary application files (exclude frontend, tests, docs)
COPY --chown=pulseplate:pulseplate app/ ./app/
COPY --chown=pulseplate:pulseplate core/ ./core/
COPY --chown=pulseplate:pulseplate legacy_app.py main.py settings.py ./
# Copy root-level modules that app.py imports
# Note: bmi_core.py is a legacy compatibility shim (no BMI math, delegates to core/bmi/*)
COPY --chown=pulseplate:pulseplate bmi_core.py bmi_visualization.py nutrition_core.py signed_links.py bodyfat.py ./
COPY --chown=pulseplate:pulseplate alembic/ ./alembic/
COPY --chown=pulseplate:pulseplate alembic.ini ./

# Create necessary directories with proper permissions
# Include home directory for matplotlib config and ensure cache/data/logs are writable
RUN mkdir -p /home/pulseplate/.config/matplotlib /app/cache/matplotlib /app/cache/food_db /app/data /app/logs && \
    chown -R pulseplate:pulseplate /home/pulseplate /app/cache /app/data /app/logs

# Set environment variables for matplotlib only.
# Production/staging must supply DATABASE_URL explicitly at runtime.
ENV MPLCONFIGDIR=/app/cache/matplotlib

# Switch to non-root user
USER pulseplate

# Expose port
EXPOSE 8000

# Health check (using Python instead of curl to avoid CVE vulnerabilities)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5)" || exit 1

# Default command (serve ASGI via app.main:app; legacy_app.py is no longer the entrypoint;
# ensure scripts/CI pass DATABASE_URL/API_KEY envs as needed)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Production stage (hardened)
FROM runtime-base AS production

# RU: Временный возврат к root нужен только для production-only slimming/hardening.
# EN: Temporarily switch back to root only for production-only slimming/hardening.
USER root

# Keep the Python _uuid ABI while retiring the vulnerable Debian package family.
COPY --from=uuid-builder /opt/libuuid/libuuid.so.1.3.0 /usr/local/lib/libuuid.so.1.3.0
COPY --from=uuid-builder /opt/libuuid/COPYING /opt/libuuid/SHA256SUMS /opt/libuuid/docker_source_artifacts.json /usr/local/share/doc/pulseplate-libuuid/
RUN ln -s libuuid.so.1.3.0 /usr/local/lib/libuuid.so.1 && ldconfig

# Preserve retained grep/libselinux consumers with genuinely patched shared PCRE2.
COPY --from=pcre2-builder /opt/pcre2/libpcre2-8.so.0.16.1 /usr/local/lib/libpcre2-8.so.0.16.1
COPY --from=pcre2-builder /opt/pcre2/PCRE2-LICENCE.md /opt/pcre2/PCRE2-COPYING /opt/pcre2/SLJIT-LICENSE /opt/pcre2/SHA256SUMS /opt/pcre2/docker_source_artifacts.json /usr/local/share/doc/pulseplate-pcre2/
RUN ln -s libpcre2-8.so.0.16.1 /usr/local/lib/libpcre2-8.so.0 && ldconfig

# Remove the original package-owned native bytes after the genuine replacements exist.
RUN dpkg --purge --force-depends --force-remove-essential \
        zlib1g libncurses6 libncursesw6 libtinfo6 ncurses-base ncurses-bin libssl3 openssl \
    && ldconfig
RUN python - <<'PY'
from pathlib import Path
import shutil
import subprocess

rows = subprocess.run(
    ["/usr/bin/dpkg-query", "-W", "-f=${db:Status-Abbrev} ${binary:Package}\n"],
    check=True, capture_output=True, text=True,
).stdout.splitlines()
retired = {"zlib1g", "libncurses6", "libncursesw6", "libtinfo6", "ncurses-base", "ncurses-bin", "libssl3", "openssl"}
for row in rows:
    fields = row.split()
    if len(fields) != 2:
        raise SystemExit("Package inventory is malformed after native replacement")
    if fields[0].startswith("ii") and fields[1].split(":", 1)[0] in retired:
        raise SystemExit("An original native package remains installed")
ssl_root = Path("/usr/lib/ssl")
ssl_root.mkdir(parents=True, exist_ok=True)
Path("/etc/ssl/private").mkdir(mode=0o700, exist_ok=True)
shutil.copyfile("/usr/local/share/doc/pulseplate-native/openssl.cnf", "/etc/ssl/openssl.cnf")
for name, target in {
    "cert.pem": "/etc/ssl/certs/ca-certificates.crt",
    "certs": "/etc/ssl/certs", "private": "/etc/ssl/private",
    "openssl.cnf": "/etc/ssl/openssl.cnf",
}.items():
    path = ssl_root / name
    if path.is_symlink():
        path.unlink()
    if path.exists():
        raise SystemExit("Unexpected real entry at an OpenSSL compatibility path")
    path.symlink_to(target)
PY

# RU: Убираем pip из production-stage, но не трогаем runtime-base/development.
# EN: Remove pip from the production stage only so shared runtime/dev topology stays intact.
RUN /opt/venv/bin/python -m pip uninstall -y pip \
    && /usr/local/bin/python -m pip uninstall -y pip \
    && /opt/venv/bin/python - <<'PY'
import importlib.util
import sys

if importlib.util.find_spec("pip") is not None:
    sys.stderr.write("pip leaked into production venv\n")
    sys.exit(1)
PY
RUN /usr/local/bin/python - <<'PY'
import importlib.util
import sys

if importlib.util.find_spec("pip") is not None:
    sys.stderr.write("pip leaked into production system site-packages\n")
    sys.exit(1)
PY

# RU: Убираем package-manager TLS, ACL/attr, Debian SQLite, gzip и Perl runtime surface только из production;
# RU: runtime-base/development остаются с apt для dev/staging workflows. apt/gpgv/perl-base
# RU: essential для Debian, поэтому удаление намеренно ограничено final production stage
# RU: и проверяется fail-closed.
# EN: Remove the package-manager TLS, ACL/attr, Debian SQLite, gzip, and Perl runtime
# EN: surface only from production; runtime-base/development keep apt for dev/staging workflows.
# EN: apt/gpgv/perl-base are Debian-essential, so this removal is intentionally limited
# EN: to the final production stage and checked fail-closed.
# SECURITY: production-package-pruning-start
RUN perl_module_packages="$(dpkg-query -W -f='${Package}\n' 'perl-modules-*' 2>/dev/null || true)" \
    && dpkg --purge --force-depends --force-remove-essential \
        bsdutils libblkid1 libmount1 libsmartcols1 libuuid1 mount util-linux util-linux-extra \
        libsystemd0 libudev1 \
    && dpkg --purge --force-depends --force-remove-essential \
        apt \
        gzip \
        gpgv \
        libacl1 \
        libattr1 \
        libgnutls30 \
        libsqlite3-0 \
        libpcre2-8-0 \
        perl-base \
        ${perl_module_packages} \
    && ldconfig \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* \
    && for package in apt gzip gpgv libacl1 libattr1 libgnutls30 libsqlite3-0 libpcre2-8-0 perl-base ${perl_module_packages} bsdutils libblkid1 libmount1 libsmartcols1 libuuid1 mount util-linux util-linux-extra libsystemd0 libudev1; do \
        status="$(dpkg-query -W -f='${db:Status-Abbrev}' "${package}" 2>/dev/null || true)"; \
        if [ "${status#ii}" != "${status}" ]; then \
            echo "${package} remains installed after production package pruning" >&2; \
            exit 1; \
        fi; \
    done \
    && for binary in gzip gunzip zcat; do \
        if command -v "${binary}" >/dev/null 2>&1; then \
            echo "${binary} binary remains after production package pruning" >&2; \
            exit 1; \
        fi; \
    done \
    && /usr/local/bin/python - <<'PY'
import gzip
import io
import ssl
import sqlite3
import sys

if not ssl.OPENSSL_VERSION:
    sys.stderr.write("Python ssl module is unavailable after production package pruning\n")
    sys.exit(1)
version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
if version < (3, 53, 2):
    sys.stderr.write(
        f"Python sqlite3 loaded SQLite {sqlite3.sqlite_version}, expected >= 3.53.2\n"
    )
    sys.exit(1)
payload = b"pulseplate gzip stdlib smoke"
compressed = gzip.compress(payload, mtime=0)
if gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb").read() != payload:
    sys.stderr.write("Python gzip stdlib smoke failed after production package pruning\n")
    sys.exit(1)
PY
# SECURITY: production-package-pruning-end

# RU: Финальный runtime остаётся non-root как и в runtime-base.
# EN: Final runtime stays non-root, matching the runtime-base contract.
USER pulseplate

# Exercise ordinary native calls and the actual loaded replacement paths after pruning.
RUN --network=none <<'SH'
set -eu
openssl version
openssl list -providers
openssl list -providers -provider legacy
infocmp -V
infocmp xterm >/dev/null
python - <<'PY_NATIVE_TERMINAL'
import subprocess
import sys

consumer_source = r'''
import ctypes
import curses
import curses.panel
import gzip
import hashlib
from pathlib import Path
import readline
import ssl
import zlib

def check_native_empty_panel_stack(panel: ctypes.CDLL) -> None:
    for operation in ("panel_above", "panel_below"):
        function = getattr(panel, operation)
        function.argtypes = [ctypes.c_void_p]
        function.restype = ctypes.c_void_p
        if function(None) is not None:
            raise SystemExit("Native panel empty-stack boundary returned a non-NULL panel")

if zlib.ZLIB_RUNTIME_VERSION != "1.3.2" or not ssl.OPENSSL_VERSION.startswith("OpenSSL 3.5.9 "):
    raise SystemExit("System native replacement version mismatch")
ncurses = ctypes.CDLL("libncursesw.so.6")
ncurses.curses_version.argtypes = []
ncurses.curses_version.restype = ctypes.c_char_p
actual_ncurses = ncurses.curses_version().decode("ascii")
if not actual_ncurses.startswith("ncurses 6.6"):
    raise SystemExit("Ncurses replacement version mismatch")
print("Ncurses runtime", actual_ncurses, "Python metadata", tuple(curses.ncurses_version))
payload = b"pulseplate native compression round trip"
if gzip.decompress(gzip.compress(payload, mtime=0)) != payload:
    raise SystemExit("Native gzip round trip failed")
if zlib.decompress(zlib.compress(payload)) != payload:
    raise SystemExit("Native zlib round trip failed")
curses.setupterm("xterm")
if curses.tigetnum("colors") < 8:
    raise SystemExit("Retained terminal data is unavailable")
readline.get_current_history_length()
check_native_empty_panel_stack(ctypes.CDLL("libpanelw.so.6"))
ssl.create_default_context()
linker = ctypes.CDLL(None)
linker.dlvsym.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
linker.dlvsym.restype = ctypes.c_void_p
for library, symbols in (
    ("libtinfo.so.6", ((b"tgetent", b"NCURSES6_TINFO_5.0.19991023"),
                       (b"tigetstr", b"NCURSES6_TINFO_5.0.19991023"))),
    ("libncursesw.so.6", ((b"initscr", b"NCURSESW6_5.1.20000708"),
                          (b"wadd_wch", b"NCURSESW6_5.3.20021019"))),
    ("libpanelw.so.6", ((b"new_panel", b"NCURSESW6_5.1.20000708"),)),
):
    handle = ctypes.CDLL(library)
    for symbol, version in symbols:
        if not linker.dlvsym(handle._handle, symbol, version):
            raise SystemExit("A required Debian terminal symbol version is missing")
        print(library, symbol.decode(), version.decode())
paths = {Path(line.rsplit(maxsplit=1)[-1]).resolve() for line in Path("/proc/self/maps").read_text().splitlines() if "/" in line}
for family in ("libz.so", "libncursesw.so", "libpanelw.so", "libtinfo.so", "libssl.so", "libcrypto.so"):
    loaded = {path for path in paths if path.name.startswith(family)}
    if not loaded or any(path.parent != Path("/usr/local/lib") for path in loaded):
        raise SystemExit("A retained consumer loaded unexpected native bytes")
    print(family, [(str(path), hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(loaded)])
'''

def run_checked_consumer(command: list[str], source: str | None = None) -> None:
    result = subprocess.run(command, input=source, capture_output=True, text=True, check=False)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0 or result.stderr:
        raise SystemExit("Native terminal consumer returned an error or loader diagnostic")

run_checked_consumer(["/bin/bash", "--noprofile", "--norc", "-c", "printf 'pulseplate terminal ABI\\n'"])
for interpreter in ("/usr/local/bin/python", "/opt/venv/bin/python"):
    run_checked_consumer([interpreter, "-"], consumer_source)
PY_NATIVE_TERMINAL
/opt/venv/bin/python - <<'PY_NATIVE_PSYCOPG'
import importlib.metadata as metadata
import hashlib
import json
from pathlib import Path
import ssl
import cryptography
from cryptography.hazmat.backends.openssl.backend import backend
from PIL import Image
import psycopg
from psycopg import pq

def check_libpq_lineage(loaded: set[Path], library_root: Path, sdk_receipt: Path) -> None:
    expected_hash = json.loads(sdk_receipt.read_text())["native_libraries"]["libpq.so.5"]
    expected = library_root / "libpq.so.5.18"
    print("Psycopg actual mapped libpq paths", sorted(str(path) for path in loaded), "Psycopg source DSO hash", expected_hash)
    if loaded != {expected} or not expected.is_file() or expected.is_symlink():
        raise SystemExit("Psycopg loaded an unexpected canonical libpq path")
    for name in ("libpq.so", "libpq.so.5"):
        alias = library_root / name
        if not alias.is_symlink() or alias.readlink() != Path("libpq.so.5.18"):
            raise SystemExit("Psycopg source-built libpq relative alias was not preserved")
    actual_hash = hashlib.sha256(expected.read_bytes()).hexdigest()
    print("Psycopg source DSO hash", expected_hash, "loaded DSO hash", actual_hash)
    if not isinstance(expected_hash, str) or actual_hash != expected_hash:
        raise SystemExit("Psycopg loaded libpq bytes differ from the native source SDK")

if cryptography.__version__ != "50.0.2" or not backend.openssl_version_text().startswith("OpenSSL 4.0.3 "):
    raise SystemExit("Cryptography bundled OpenSSL mismatch")
if psycopg.__version__ != "3.3.4" or pq.__impl__ != "c" or pq.version() != 180006:
    raise SystemExit("Psycopg C/system client mismatch")
if ssl.OPENSSL_VERSION_INFO[:3] != (3, 5, 9):
    raise SystemExit("Psycopg runtime shared OpenSSL mismatch")
if any(distribution.metadata["Name"].lower() == "psycopg-binary" for distribution in metadata.distributions()):
    raise SystemExit("The binary Psycopg carrier remains installed")
import io
image = Image.new("RGB", (2, 2), color=(1, 2, 3))
data = io.BytesIO()
image.save(data, format="PNG")
data.seek(0)
if Image.open(data).getpixel((0, 0)) != (1, 2, 3):
    raise SystemExit("Pillow native PNG round trip failed")
loaded = {Path(line.rsplit(maxsplit=1)[-1]).resolve() for line in Path("/proc/self/maps").read_text().splitlines() if "libpq.so" in line}
check_libpq_lineage(loaded, Path("/usr/local/lib"), Path("/usr/local/share/doc/pulseplate-native/psycopg-c-sdk.json"))
print("Psycopg C", pq.version(), "Cryptography bundled", backend.openssl_version_text())
PY_NATIVE_PSYCOPG
SH

RUN <<'SH'
set -eu
(cd /usr/local/lib && sha256sum --check /usr/local/share/doc/pulseplate-libuuid/SHA256SUMS)
for interpreter in /usr/local/bin/python /opt/venv/bin/python; do
    "$interpreter" - <<'PY'
import _uuid
from pathlib import Path
import uuid

native_bytes, native_status = _uuid.generate_time_safe()
if len(native_bytes) != 16 or uuid.UUID(bytes=native_bytes).version != 1:
    raise SystemExit("Native UUID generation failed")
expected = Path("/usr/local/lib/libuuid.so.1.3.0").resolve()
loaded = {
    Path(line.rsplit(maxsplit=1)[-1]).resolve()
    for line in Path("/proc/self/maps").read_text().splitlines()
    if "libuuid.so" in line
}
if loaded != {expected}:
    raise SystemExit(f"Unexpected native UUID library: {loaded}")
if uuid.UUID(str(uuid.uuid4())).version != 4:
    raise SystemExit("UUID round-trip failed")
print("Native UUID library:", expected, "coordination status:", native_status)
PY
done
SH

# Exercise the actual replacement and retained native consumers after package pruning.
RUN <<'SH'
set -eu
(cd /usr/local/lib && sha256sum --check /usr/local/share/doc/pulseplate-pcre2/SHA256SUMS)
for interpreter in /usr/local/bin/python /opt/venv/bin/python; do
    "$interpreter" - <<'PYCODE'
import ctypes as c
from pathlib import Path
import stat
import tempfile

lib = c.CDLL("libpcre2-8.so.0")
lib.pcre2_config_8.argtypes = [c.c_uint32, c.c_void_p]
lib.pcre2_config_8.restype = c.c_int
version = c.create_string_buffer(64)
if lib.pcre2_config_8(11, version) <= 0 or not version.value.startswith(b"10.49 "):
    raise SystemExit("PCRE2 replacement version mismatch")
for key in (1, 9):  # Native PCRE2_CONFIG_JIT and PCRE2_CONFIG_UNICODE.
    enabled = c.c_uint32()
    if lib.pcre2_config_8(key, c.byref(enabled)) != 0 or enabled.value != 1:
        raise SystemExit("PCRE2 required JIT/Unicode feature is disabled")
lib.pcre2_compile_8.argtypes = [
    c.c_char_p, c.c_size_t, c.c_uint32, c.POINTER(c.c_int), c.POINTER(c.c_size_t), c.c_void_p
]
lib.pcre2_compile_8.restype = c.c_void_p
lib.pcre2_jit_compile_8.argtypes = [c.c_void_p, c.c_uint32]
lib.pcre2_jit_compile_8.restype = c.c_int
lib.pcre2_match_data_create_from_pattern_8.argtypes = [c.c_void_p, c.c_void_p]
lib.pcre2_match_data_create_from_pattern_8.restype = c.c_void_p
lib.pcre2_match_context_create_8.argtypes = [c.c_void_p]
lib.pcre2_match_context_create_8.restype = c.c_void_p
lib.pcre2_jit_stack_create_8.argtypes = [c.c_size_t, c.c_size_t, c.c_void_p]
lib.pcre2_jit_stack_create_8.restype = c.c_void_p
lib.pcre2_jit_stack_assign_8.argtypes = [c.c_void_p, c.c_void_p, c.c_void_p]
lib.pcre2_jit_stack_assign_8.restype = None
lib.pcre2_jit_match_8.argtypes = [
    c.c_void_p, c.c_char_p, c.c_size_t, c.c_size_t, c.c_uint32, c.c_void_p, c.c_void_p
]
lib.pcre2_jit_match_8.restype = c.c_int
for name in (
    "pcre2_jit_stack_free_8", "pcre2_match_context_free_8",
    "pcre2_match_data_free_8", "pcre2_code_free_8",
):
    function = getattr(lib, name)
    function.argtypes = [c.c_void_p]
    function.restype = None
code = match = context = stack = None
try:
    pattern = rb"^(?:\p{L}+)$"
    error = c.c_int()
    offset = c.c_size_t()
    code = lib.pcre2_compile_8(
        pattern, len(pattern), 0x00080000 | 0x00020000, c.byref(error), c.byref(offset), None
    )  # Native PCRE2_UTF | PCRE2_UCP.
    if not code or lib.pcre2_jit_compile_8(code, 1) != 0:
        raise SystemExit("PCRE2 UTF/UCP compile or JIT compile failed")
    match = lib.pcre2_match_data_create_from_pattern_8(code, None)
    context = lib.pcre2_match_context_create_8(None)
    stack = lib.pcre2_jit_stack_create_8(32768, 524288, None)
    if not match or not context or not stack:
        raise SystemExit("PCRE2 native allocation failed")
    lib.pcre2_jit_stack_assign_8(context, None, stack)
    for subject, expected_result in (("Привет".encode(), 1), (b"123", -1)):
        if lib.pcre2_jit_match_8(
            code, subject, len(subject), 0, 0, match, context
        ) != expected_result:
            raise SystemExit("PCRE2 UTF/UCP JIT match with assigned stack failed")
finally:
    for name, pointer in (
        ("pcre2_jit_stack_free_8", stack), ("pcre2_match_context_free_8", context),
        ("pcre2_match_data_free_8", match), ("pcre2_code_free_8", code),
    ):
        if pointer:
            getattr(lib, name)(pointer)

class SelabelOpt(c.Structure):
    _fields_ = [("type", c.c_int), ("value", c.c_char_p)]

selinux = c.CDLL("libselinux.so.1", use_errno=True)
selinux.selabel_open.argtypes = [c.c_uint, c.POINTER(SelabelOpt), c.c_uint]
selinux.selabel_open.restype = c.c_void_p
selinux.selabel_lookup_raw.argtypes = [c.c_void_p, c.POINTER(c.c_char_p), c.c_char_p, c.c_int]
selinux.selabel_lookup_raw.restype = c.c_int
selinux.freecon.argtypes = [c.c_void_p]
selinux.freecon.restype = None
selinux.selabel_close.argtypes = [c.c_void_p]
selinux.selabel_close.restype = None
with tempfile.TemporaryDirectory() as directory:
    contexts = Path(directory) / "file_contexts"
    contexts.write_text(
        "/tmp/pulseplate-pcre2-check(/.*)? system_u:object_r:tmp_t:s0\n", encoding="utf-8"
    )
    options = (SelabelOpt * 1)(SelabelOpt(3, str(contexts).encode()))  # SELABEL_OPT_PATH.
    handle = selinux.selabel_open(0, options, 1)  # SELABEL_CTX_FILE backend.
    if not handle:
        raise SystemExit("libselinux native regex backend open failed")
    label = c.c_char_p()
    try:
        if selinux.selabel_lookup_raw(
            handle, c.byref(label), b"/tmp/pulseplate-pcre2-check/child", stat.S_IFREG
        ) != 0 or label.value != b"system_u:object_r:tmp_t:s0":
            raise SystemExit("libselinux native regex lookup failed")
    finally:
        if label.value is not None:
            selinux.freecon(c.cast(label, c.c_void_p))
        selinux.selabel_close(handle)
expected = Path("/usr/local/lib/libpcre2-8.so.0.16.1").resolve()
loaded = {
    Path(line.rsplit(maxsplit=1)[-1]).resolve()
    for line in Path("/proc/self/maps").read_text().splitlines()
    if "libpcre2-8.so" in line
}
if loaded != {expected}:
    raise SystemExit(f"Unexpected native PCRE2 library: {loaded}")
print("PCRE2", version.value.decode(), "UTF/UCP/JIT and libselinux regex passed:", expected)
PYCODE
done
printf 'abc\n' | grep -P '^\p{L}+$'
dpkg --version
ls /usr/local/lib/libpcre2-8.so.0
consumer_directory="$(mktemp -d)"
mkdir "${consumer_directory}/child"
rmdir "${consumer_directory}/child" "${consumer_directory}"
SH

# ALEMBIC-FILESYSTEM-CARRIER-PRECHECK-START
RUN /opt/venv/bin/python - <<'PY'
from pathlib import Path
import sys

literal_app_root = Path("/app")
literal_migration_root = Path("/app/alembic")
for path in (literal_app_root, literal_migration_root):
    if path.is_symlink() or not path.is_dir():
        sys.stderr.write(f"Required repository directory is not a real directory: {path}\n")
        raise SystemExit(1)
app_root = literal_app_root.resolve()
migration_root = literal_migration_root.resolve()
if app_root != literal_app_root:
    sys.stderr.write(f"Repository root must resolve exactly to /app, got {app_root}\n")
    raise SystemExit(1)
if migration_root != literal_migration_root or not migration_root.is_relative_to(app_root):
    sys.stderr.write(
        f"Migration root must resolve exactly to /app/alembic under /app, got {migration_root}\n"
    )
    raise SystemExit(1)
symlink_paths = [path for path in migration_root.rglob("*") if path.is_symlink()]
if symlink_paths:
    rendered = ", ".join(str(path) for path in symlink_paths[:5])
    sys.stderr.write(f"Repository migration tree contains symlink carriers: {rendered}\n")
    raise SystemExit(1)
forbidden_paths = []
package_carrier = migration_root / "__init__.py"
if package_carrier.exists() or package_carrier.is_symlink():
    forbidden_paths.append(package_carrier)
forbidden_paths.extend(migration_root.rglob("__pycache__"))
forbidden_paths.extend(migration_root.rglob("*.pyc"))
forbidden_paths.extend(migration_root.rglob("*.pyo"))
if forbidden_paths:
    rendered = ", ".join(str(path) for path in forbidden_paths[:5])
    sys.stderr.write(f"Repository Alembic package/bytecode carrier detected: {rendered}\n")
    raise SystemExit(1)
PY
# ALEMBIC-FILESYSTEM-CARRIER-PRECHECK-END

# ALEMBIC-INSTALLED-OWNERSHIP-GUARD-START
RUN /opt/venv/bin/python - <<'PY'
import importlib
import importlib.metadata
import importlib.util
from pathlib import Path
import sys
import sysconfig

from alembic.config import Config
from alembic.script import ScriptDirectory

app_root = Path("/app").resolve()
migration_root = Path("/app/alembic").resolve()
venv_root = Path(sys.prefix).resolve()
if venv_root != Path("/opt/venv"):
    sys.stderr.write(f"Production interpreter prefix mismatch: {venv_root}\n")
    raise SystemExit(1)
purelib_root = Path(sysconfig.get_path("purelib")).resolve()
if not purelib_root.is_relative_to(venv_root):
    sys.stderr.write(f"Production purelib is outside /opt/venv: {purelib_root}\n")
    raise SystemExit(1)
distribution = importlib.metadata.distribution("alembic")
distribution_root = Path(distribution.locate_file("")).resolve()
installed_alembic_root = Path(distribution.locate_file("alembic")).resolve()
if distribution_root != purelib_root or not installed_alembic_root.is_relative_to(purelib_root):
    sys.stderr.write("Installed Alembic distribution is outside the production venv purelib\n")
    raise SystemExit(1)
print(f"Alembic distribution root: {distribution_root}")

for module_name in ("alembic", "alembic.config", "alembic.context", "alembic.op"):
    module = importlib.import_module(module_name)
    origin_path = Path(module.__file__ or "")
    if not origin_path.is_file() or origin_path.is_symlink():
        sys.stderr.write(f"{module_name} is not a regular installed module: {origin_path}\n")
        raise SystemExit(1)
    origin = origin_path.resolve()
    if not origin.is_relative_to(installed_alembic_root):
        sys.stderr.write(f"{module_name} resolved outside installed Alembic: {origin}\n")
        raise SystemExit(1)
    if origin.is_relative_to(migration_root):
        sys.stderr.write(f"{module_name} resolved from repository migration data: {origin}\n")
        raise SystemExit(1)

expected_repo_origins = {
    "app": app_root / "app" / "__init__.py",
    "core": app_root / "core" / "__init__.py",
    "settings": app_root / "settings.py",
}
for module_name, expected_origin in expected_repo_origins.items():
    if not expected_origin.is_file() or expected_origin.is_symlink():
        sys.stderr.write(f"{module_name} repository carrier is not a regular file: {expected_origin}\n")
        raise SystemExit(1)
    if not expected_origin.resolve().is_relative_to(app_root):
        sys.stderr.write(f"{module_name} repository carrier escaped /app: {expected_origin}\n")
        raise SystemExit(1)
    spec = importlib.util.find_spec(module_name)
    origin_path = Path(spec.origin or "") if spec is not None else None
    origin = origin_path.resolve() if origin_path is not None else None
    if origin_path != expected_origin or origin != expected_origin.resolve():
        sys.stderr.write(
            f"{module_name} repository ownership mismatch: expected {expected_origin}, got {origin}\n"
        )
        raise SystemExit(1)

config = Config("/app/alembic.ini")
scripts = ScriptDirectory.from_config(config)
if Path(scripts.dir).resolve() != migration_root:
    sys.stderr.write(f"Alembic script directory mismatch: {scripts.dir}\n")
    raise SystemExit(1)
heads = scripts.get_heads()
if len(heads) != 1 or not heads[0].strip():
    sys.stderr.write(f"Alembic migration graph must have one non-empty head, got {heads!r}\n")
    raise SystemExit(1)
PY
# ALEMBIC-INSTALLED-OWNERSHIP-GUARD-END

# ALEMBIC-CLI-HEADS-GUARD-START
RUN /opt/venv/bin/alembic -c /app/alembic.ini heads
# ALEMBIC-CLI-HEADS-GUARD-END

# Stage 4: Staging stage
# Extends production with staging-specific configurations
# Can be customized for staging needs (e.g., debug logging, extended health checks)
#
# HOW TO BUILD FOR STAGING:
#   docker build --target=staging -t myapp:staging .
#   docker build --target=staging --build-arg LOG_LEVEL=INFO -t myapp:staging .
#
# HOW TO RUN STAGING CONTAINER:
#   docker run -e LOG_LEVEL=INFO -e DATABASE_URL=staging_db_url myapp:staging
#
FROM production AS staging

# COMMON STAGING ENV VARS (uncomment/modify as needed):
#
# Logging and debugging:
# ENV LOG_LEVEL=INFO                    # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
# ENV ENABLE_DEBUG_FEATURES=true        # Enable debug endpoints/features
# ENV ENABLE_PROFILING=true             # Enable performance profiling
# ENV SENTRY_ENVIRONMENT=staging        # Sentry error tracking environment
#
# API and feature flags:
# ENV API_RATE_LIMIT=1000               # Higher rate limits for testing
# ENV ENABLE_BETA_FEATURES=true         # Enable beta/experimental features
# ENV MOCK_EXTERNAL_APIS=false          # Use real APIs but with test credentials
#
# Database and caching:
# ENV DATABASE_POOL_SIZE=10             # Smaller pool for staging resources
# ENV REDIS_CACHE_TTL=300               # Shorter cache TTL for testing
#
# Security and monitoring:
# ENV CORS_ALLOWED_ORIGINS="*"          # More permissive CORS for testing
# ENV ENABLE_METRICS_EXPORT=true        # Export metrics to monitoring service
#
# HOW TO SET ENV VARS:
# 1. Build-time (baked into image): Use ENV directive above or --build-arg
# 2. Run-time (flexible): Use -e flag with docker run or docker-compose.yaml
# 3. From file: Use --env-file staging.env with docker run
#
# CI/CD USAGE:
# - In GitHub Actions: Set target in docker/build-push-action@v2 with 'target: staging'
# - In GitLab CI: Add --target=staging to docker build command in .gitlab-ci.yml
# - With docker-compose: Set 'target: staging' in docker-compose.staging.yaml
#
# For detailed staging setup and deployment instructions, see:
# - STAGING_SETUP.md - Complete staging environment configuration
# - DEPLOYMENT_FULL_GUIDE.md - Production and staging deployment workflows
# - .github/workflows/ - CI/CD pipeline examples with staging targets

# Stage 5: Development stage
FROM runtime-base AS development
COPY --from=psycopg-wheel-builder /output/psycopg-sdk/ /opt/psycopg-sdk/

ARG PULSEPLATE_PYTHON_INDEX_URL
ARG PULSEPLATE_PYTHON_TRUSTED_HOST=""

# Switch back to root for development tools
USER root

# Install development dependencies
# Copy both requirements files as requirements-dev.txt includes requirements.txt via -r
COPY requirements.txt requirements-dev.txt constraints.txt ./
COPY scripts/ci/check_python_startup_hooks.py scripts/ci/install_locked_python_requirements.py scripts/ci/emergency_python_wheels.json /tmp/pulseplate-ci/
# SECURITY NOTE: Do NOT uninstall setuptools/wheel in development stage.
# They are required runtime dependencies of pip-tools for lockfile generation (pip-compile).
# Security mitigation (GHSA-58pv-8j8x-9vj2) applies to runtime/production images only.
RUN --mount=type=secret,id=pp_py_index,required=false \
    --mount=type=secret,id=pp_py_host,required=false \
    --mount=type=secret,id=pp_netrc,required=false \
    PULSEPLATE_PYTHON_INDEX_URL="$(cat /run/secrets/pp_py_index 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_INDEX_URL:-}")"; \
    PULSEPLATE_PYTHON_TRUSTED_HOST="$(cat /run/secrets/pp_py_host 2>/dev/null || printf '%s' "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}")"; \
    if [ -f /run/secrets/pp_netrc ]; then \
      if [ -e /root/.netrc ]; then \
        echo "Refusing to overwrite an existing /root/.netrc." >&2; \
        exit 1; \
      fi; \
      cp /run/secrets/pp_netrc /root/.netrc; \
      chmod 600 /root/.netrc; \
    fi; \
    trap 'rm -f /root/.netrc' EXIT; \
    if [ -z "${PULSEPLATE_PYTHON_INDEX_URL:-}" ]; then \
      echo "PULSEPLATE_PYTHON_INDEX_URL is required for Docker builds." >&2; \
      exit 1; \
    fi; \
    if [ -n "${PULSEPLATE_PYTHON_TRUSTED_HOST:-}" ]; then \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --requirements-file requirements.txt \
        --dev-requirements-file requirements-dev.txt \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-dev \
        --psycopg-sdk /opt/psycopg-sdk \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" \
        --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}"; \
    else \
      python /tmp/pulseplate-ci/install_locked_python_requirements.py \
        --python-executable python \
        --requirements-file requirements.txt \
        --dev-requirements-file requirements-dev.txt \
        --guard-script /tmp/pulseplate-ci/check_python_startup_hooks.py \
        --constraints-file constraints.txt \
        --install-dev \
        --psycopg-sdk /opt/psycopg-sdk \
        --emergency-wheel-manifest /tmp/pulseplate-ci/emergency_python_wheels.json \
        --index-url "${PULSEPLATE_PYTHON_INDEX_URL}"; \
    fi

# Install additional development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER pulseplate

# Override command for development (serve ASGI via app.main:app; legacy_app.py is no longer
# the entrypoint; ensure scripts/CI pass DATABASE_URL/API_KEY envs as needed)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

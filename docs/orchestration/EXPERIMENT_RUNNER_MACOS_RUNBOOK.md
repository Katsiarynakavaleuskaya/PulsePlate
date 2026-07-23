# Experiment Runner strict macOS backend

Status: local development evidence only. This backend does not grant PR,
promotion, merge, release, GitHub App, or Slack authority.

## Purpose

The macOS dispatcher preserves the canonical `network_budget=0` contract by
running the existing Linux Experiment Runner in an isolated OCI guest. For
general probe and candidate execution, backend selection happens once before
the experiment:

1. Apple `container` on Apple silicon;
2. Docker with `--network none` when the Apple probe is not strict;
3. `capability_mismatch` when neither backend proves the required controls.

There is no mid-run fallback and no retry with a weaker network mode. The
strict dispatcher accepts only packets whose `network_budget` is exactly zero;
a non-zero value produces `capability_mismatch` before any runtime probe.

For `oracle_only_governance_reviewer` on macOS, do not use that automatic
fallback order. `run` accepts only explicit `--backend apple-container` and
rejects `auto`, `docker`, and `native-linux` before runtime probing or result
creation. Apple capability loss is terminal `capability_mismatch`; it never
falls back to Docker.

## Host prerequisites

- Apple silicon and supported macOS for Apple Container 1.1.0;
- official signed Apple package installed;
- `container system start` completed;
- recommended kernel configured when requested by the runtime;
- Docker Desktop is an optional general candidate/negative-control fallback,
  not a macOS Oracle runtime or co-required runtime;
- approved private Python proxy is available only during image build.

Do not add `CAP_SYS_ADMIN`, mount a runtime socket, or change
`network_budget` to a non-zero value to make a probe pass.

## Build the immutable runner image

The admitted source recipe starts from the pinned official UBI 10 minimal
multi-architecture digest
`registry.access.redhat.com/ubi10/ubi-minimal@sha256:04140c8d78c6c6915b5c1fdad2f16d10eac3630c3339999ccdf659d8c903be50`.
It verifies the official EPEL 10 key and release RPM, installs exact Python
3.13.14 packages, and overlays the checksum-pinned official CPython 3.13
backport for `CVE-2026-15308`. The final image keeps the locked `runtime-dev`
environment and non-root UID/GID 65532. Proxy values enter BuildKit as secrets
and are not build arguments or runtime environment variables. A source pin is
not reusable admission evidence; every material rebuild needs a new exact
image digest and the complete sequence below.

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend apple-container \
  --tag pulseplate/experiment-runner:mac-local
```

The command returns a sanitized `name@sha256:<digest>` reference. Preserve that
exact reference for `probe` and `run`; mutable tags are rejected by `run`.

Docker fallback build:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend docker \
  --tag pulseplate/experiment-runner:docker-local
```

## Probe

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py probe \
  --backend auto \
  --image pulseplate/experiment-runner:mac-local@sha256:<digest> \
  --output mac-strict-capability.json
```

The local artifact is written under
`artifacts/orchestration/experiments/capabilities/` and is gitignored. It
contains coarse platform/runtime classes, the image digest, boolean probes,
deterministic blocker codes, and `authority: evidence_only`. It never contains
hostnames, usernames, home paths, tokens, or raw subprocess output.

Strict Apple execution requires all of the following:

- an internal Apple network and `--no-dns`;
- guest `unshare --net --map-root-user` without added capabilities;
- the IPv4 subnet inspected from Apple Container's persistent built-in
  `default` network, used only to exclude runtime-owned host candidates;
- a real host TCP listener that is reachable in the outer Apple guest as a
  positive control, bound to the one safe, locally bindable AF_INET/SOCK_STREAM
  address returned for the local hostname while DNS and direct-IP outbound are
  blocked;
- a separate inner-namespace canary proving that the same host listener, DNS,
  and direct-IP outbound are all blocked by guest `unshare`;
- repository, packet, patch, and root filesystem read-only;
- no host-writable result bind: the untrusted runner writes only to a private
  named result volume;
- private bounded tmpfs mounted with
  `type=tmpfs,destination=/tmp,size=1G,mode=1777`; the current PulsePlate Git
  object store is larger than 600 MiB, so smaller tmpfs profiles cannot hold
  the Runner's required no-hardlinks temporary clone;
- forced deletion of uniquely named runner/canary containers before volume and
  network cleanup.

The positive-control identity comes only from hostname AF_INET/SOCK_STREAM
resolution. Before creating the temporary canary network, the dispatcher
deduplicates those addresses and removes loopback, unspecified, multicast,
link-local, reserved, Apple-runtime-subnet, and locally unbindable candidates.
Exactly one candidate must remain. It is bound by the listener and targeted by
both canaries, but is never written to capability or result artifacts. Multiple
eligible candidates, no eligible candidate, hostname resolution failure, or a
bind race fails closed as `host_listener_unavailable`; there is no ordering,
interface heuristic, wildcard bind, hard-coded address, fallback, or retry.
Canary containers still run on one unique internal `--no-dns` network. Missing
or malformed persistent `default` IPv4 subnet metadata retains the existing
`network_gateway_unavailable` compatibility blocker. Every encountered
`ipv4Subnet` value is parsed as a strict IPv4 network: identical values
deduplicate, exactly one distinct network must remain, and IPv6, host-bit-set,
malformed, or multiple distinct values fail closed under the same compatibility
blocker.

Docker requires the same guest and mount controls, with whole-container
`--network none` and a bounded `/tmp` tmpfs. Its outer and inner canaries both
must fail to reach the real listener, DNS, and direct IP. The listener is
separately proven reachable from the host so a closed local port cannot create
a false positive.

The untrusted runner never mounts the runtime socket. After its PID 1 exits, a
separate trusted collector mounts the private result volume read-only inside a
fresh network namespace. The collector opens only the canonical result with
`O_NOFOLLOW`, verifies a regular bounded file via `fstat`, and emits base64 to
the dispatcher. The volume is then deleted.

## Run

Oracle-only governance evidence:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py run \
  --backend apple-container \
  --packet artifacts/orchestration/experiments/packets/<packet>.json \
  --image pulseplate/experiment-runner:mac-local@sha256:<digest> \
  --output <result>.json
```

When an oracle-only review is intended to materially shape the engineering
decision if accepted, pass the complete attribution triple. The reason remains
one literal argv value, including when it contains spaces:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py run \
  --backend apple-container \
  --packet artifacts/orchestration/experiments/packets/<packet>.json \
  --image pulseplate/experiment-runner:mac-local@sha256:<digest> \
  --output <result>.json \
  --contribution-kind oracle_review \
  --coauthor-required \
  --coauthor-reason "Material oracle review shaped the engineering decision."
```

Omit all three attribution flags when the Runner contribution is not material.
The dispatcher validates the tuple before backend selection and accepts a
material tuple only for oracle-only governance review. Candidate-patch mode
rejects material/non-default attribution. The same validated tuple is forwarded
as exact inner-runner argv; on macOS the material Oracle path is Apple Container
only, while default candidate tuples retain Apple/Docker parity and add no inner
argv. After collection and redaction, the host dispatcher requires an
accepted result's attribution tuple to equal the requested normalized tuple
exactly; a rejected result must use canonical `contribution_kind: none`,
`coauthor_required: false`, and `coauthor_reason: ""`. Any mismatch fails as
`result_validation_failed` without exposing raw metadata. If an accepted
attributed artifact is later unused,
governed identity policy determines that no Experiment Runner trailer is
required. Attribution metadata records material evidence use only. It does not
start a container, approve promotion, open or merge a PR, or grant runtime
authority.

Candidate mode additionally passes a repository-local patch:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py run \
  --backend auto \
  --packet <packet>.json \
  --candidate-patch <candidate>.patch \
  --image pulseplate/experiment-runner:mac-local@sha256:<digest> \
  --output <result>.json
```

The dispatcher creates a self-contained temporary clone, applies the tracked
working-tree diff for oracle-only freshness, and mounts that snapshot read-only.
It never exposes a host worktree `.git/worktrees/...` path to the guest. New
results contain optional `execution_backend` provenance; old v1 results remain
valid without it.

Apple Container is invoked with the already inspected exact
`name@sha256:<digest>` reference. Docker is invoked with the inspected local
digest identity and `--pull never`; the dispatcher re-inspects the original
name-to-digest binding immediately before execution. Neither backend may pull
or substitute an image after preflight.

## Failure handling

`capability_mismatch` is non-retryable environment evidence. Common blockers:

- `runtime_cli_missing`, `runtime_stopped`, `runtime_not_ready`;
- `apple_kernel_not_configured`;
- `image_missing`, `image_digest_drift`;
- `guest_unshare_unavailable`, `guest_platform_mismatch`;
- `strict_network_budget_required`, `filesystem_isolation_unavailable`;
- `host_listener_unavailable`, `network_gateway_unavailable`,
  `network_isolation_failed`,
  `mount_contract_failed`;
- `result_volume_failed`, `container_cleanup_failed`;
- `probe_execution_failed`.

For general probe/candidate execution, automatic Apple-to-Docker fallback is
allowed only after Apple preflight cleanup completes. It is never allowed for
macOS Oracle-only governance review. `container_cleanup_failed` is terminal
because residual resources may remain; `auto` must not probe or start another
backend.

After the experiment starts, any runtime failure remains on the selected
backend and is reported without trying Docker, Apple Container, or a networked
mode. `infra_flake` remains reserved for genuinely transient execution errors.
Loss of `unshare` after a passed preflight is still a non-retryable
`capability_mismatch`.

## Validation and rollback

The prior slim-trixie candidate built as Apple image index
`sha256:ee233e13a3663e86bcf8922fe0944e183c9220e600e2f33447e8acf483fa8940`.
Its exact exported OCI chain was the top index above, one `linux/arm64`
manifest
`sha256:734c8152bd362380066ac82ac04b8289f52ee16cf4a87cf7eec9a39bc0cb81dd`,
and config/history
`sha256:ba1205a81ca4e89dff7e2ba168458b94f5c8466739bb7611e485ae22383231dc`.
The manifest-bound config/history inspection found no configured proxy-secret
name or current value, but the unsuppressed official Trivy 0.72.0 scan failed:
Debian 13.6 reported 60 HIGH/CRITICAL occurrences (44 HIGH, 16 CRITICAL)
across 25 unique CVEs. That exact image is not admitted.

The Alpine candidate was also rejected before admission. The locked installer
correctly required binary wheels, while `matplotlib==3.10.8` had no compatible
Linux ARM64 musllinux wheel. The diagnostic build used the approved private
index secret and did not fall back to public PyPI. Weakening the lock,
`--only-binary` policy, or index boundary was not authorized.

The current UBI recipe built through the canonical Apple dispatcher as image
index
`sha256:5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70`.
Its exact `linux/arm64` manifest is
`sha256:c46d2bd8a174b6b10b9ed06c1c145eeb1ca131d326c67b4c72589ea84e6d1750`,
and its manifest-bound config/history is
`sha256:b96621e97fd78527a93f9853970d1f17baffa46e8d188e5341899fc6a1efaa1d`.
The scan must consume the exact OCI layout cryptographically traversed from
that Apple image digest; a mutable tag, bare repository-context scan, or
unverified PATH Trivy binary is not evidence. Download the official Trivy
0.72.0 macOS ARM64 asset and its official release checksums, verify the asset
before execution, refresh its vulnerability database, and run:

```bash
set -euo pipefail

RUNNER_IMAGE_REF='pulseplate/experiment-runner:mac-local@sha256:<digest>'
RUNNER_IMAGE_DIGEST="${RUNNER_IMAGE_REF##*@}"
RUNNER_EVIDENCE_PARENT='artifacts/orchestration/security'
RUNNER_EVIDENCE_DIR="${RUNNER_EVIDENCE_PARENT}/runner-${RUNNER_IMAGE_DIGEST#sha256:}"
RUNNER_INSPECT_JSON="${RUNNER_EVIDENCE_DIR}/apple-image-inspect.json"
RUNNER_OCI_ARCHIVE="${RUNNER_EVIDENCE_DIR}/runner.oci.tar"
RUNNER_OCI_LAYOUT="${RUNNER_EVIDENCE_DIR}/oci-layout"
RUNNER_TRIVY_REPORT="${RUNNER_EVIDENCE_DIR}/trivy-0.72.0.json"
RUNNER_TRIVY_DIR="${RUNNER_EVIDENCE_DIR}/trivy-0.72.0"
RUNNER_RUNTIME_REPORT="${RUNNER_EVIDENCE_DIR}/runtime-contract.stdout"
RUNNER_PROBE_STDOUT="${RUNNER_EVIDENCE_DIR}/apple-probe.stdout"
RUNNER_STATUS_REPORT="${RUNNER_EVIDENCE_DIR}/admission-exit-statuses.txt"
RUNNER_PROBE_ARTIFACT="mac-strict-capability-${RUNNER_IMAGE_DIGEST#sha256:}.json"
TRIVY_VERSION='0.72.0'
TRIVY_ASSET="trivy_${TRIVY_VERSION}_macOS-ARM64.tar.gz"
TRIVY_CHECKSUMS="trivy_${TRIVY_VERSION}_checksums.txt"
TRIVY_RELEASE_BASE="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}"

AWK_BIN="$(command -v awk)"
CONTAINER_BIN="$(command -v container)"
CURL_BIN="$(command -v curl)"
GREP_BIN="$(command -v grep)"
JQ_BIN="$(command -v jq)"
SHASUM_BIN="$(command -v shasum)"
TAR_BIN="$(command -v tar)"
TEE_BIN="$(command -v tee)"
WC_BIN="$(command -v wc)"
RUNNER_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
test -x "${AWK_BIN}"
test -x "${CONTAINER_BIN}"
test -x "${CURL_BIN}"
test -x "${GREP_BIN}"
test -x "${JQ_BIN}"
test -x "${SHASUM_BIN}"
test -x "${TAR_BIN}"
test -x "${TEE_BIN}"
test -x "${WC_BIN}"
test -x "${RUNNER_PYTHON}"
printf '%s\n' "${RUNNER_IMAGE_DIGEST}" | \
  "${GREP_BIN}" -Eq '^sha256:[0-9a-f]{64}$'
mkdir -p "${RUNNER_EVIDENCE_PARENT}"
mkdir "${RUNNER_EVIDENCE_DIR}"
mkdir "${RUNNER_OCI_LAYOUT}"
mkdir "${RUNNER_TRIVY_DIR}"

"${CURL_BIN}" --fail --location --silent --show-error \
  "${TRIVY_RELEASE_BASE}/${TRIVY_ASSET}" \
  --output "${RUNNER_TRIVY_DIR}/${TRIVY_ASSET}"
"${CURL_BIN}" --fail --location --silent --show-error \
  "${TRIVY_RELEASE_BASE}/${TRIVY_CHECKSUMS}" \
  --output "${RUNNER_TRIVY_DIR}/${TRIVY_CHECKSUMS}"
TRIVY_EXPECTED_SHA="$("${AWK_BIN}" -v asset="${TRIVY_ASSET}" \
  '$2 == asset {count += 1; digest = $1} END {if (count == 1) print digest}' \
  "${RUNNER_TRIVY_DIR}/${TRIVY_CHECKSUMS}")"
printf '%s\n' "${TRIVY_EXPECTED_SHA}" | "${GREP_BIN}" -Eq '^[0-9a-f]{64}$'
printf '%s  %s\n' "${TRIVY_EXPECTED_SHA}" "${TRIVY_ASSET}" \
  >"${RUNNER_TRIVY_DIR}/selected-checksum.txt"
(
  cd "${RUNNER_TRIVY_DIR}"
  "${SHASUM_BIN}" -a 256 -c selected-checksum.txt
)
"${TAR_BIN}" -xzf "${RUNNER_TRIVY_DIR}/${TRIVY_ASSET}" \
  -C "${RUNNER_TRIVY_DIR}" trivy
TRIVY_BIN="${RUNNER_TRIVY_DIR}/trivy"
test -x "${TRIVY_BIN}"
"${TRIVY_BIN}" --version | "${GREP_BIN}" -Fx 'Version: 0.72.0'

"${CONTAINER_BIN}" image inspect "${RUNNER_IMAGE_REF}" >"${RUNNER_INSPECT_JSON}"
"${JQ_BIN}" -e --arg digest "${RUNNER_IMAGE_DIGEST}" \
  'length == 1 and .[0].configuration.descriptor.digest == $digest' \
  "${RUNNER_INSPECT_JSON}" >/dev/null

"${CONTAINER_BIN}" image save --output "${RUNNER_OCI_ARCHIVE}" \
  "${RUNNER_IMAGE_REF}"
"${TAR_BIN}" -xf "${RUNNER_OCI_ARCHIVE}" -C "${RUNNER_OCI_LAYOUT}"
RUNNER_TOP_INDEX_DIGEST="$("${JQ_BIN}" -er \
  'if (.manifests | length) == 1 and
      .manifests[0].mediaType == "application/vnd.oci.image.index.v1+json"
   then .manifests[0].digest else error("expected one OCI index") end' \
  "${RUNNER_OCI_LAYOUT}/index.json")"
RUNNER_TOP_INDEX_SIZE="$("${JQ_BIN}" -er \
  'if (.manifests | length) == 1 and
      .manifests[0].mediaType == "application/vnd.oci.image.index.v1+json"
   then .manifests[0].size else error("expected one OCI index") end' \
  "${RUNNER_OCI_LAYOUT}/index.json")"
printf '%s\n' "${RUNNER_TOP_INDEX_DIGEST}" | \
  "${GREP_BIN}" -Eq '^sha256:[0-9a-f]{64}$'
test "${RUNNER_TOP_INDEX_DIGEST}" = "${RUNNER_IMAGE_DIGEST}"
RUNNER_TOP_INDEX_BLOB="${RUNNER_OCI_LAYOUT}/blobs/sha256/${RUNNER_TOP_INDEX_DIGEST#sha256:}"
test -f "${RUNNER_TOP_INDEX_BLOB}"
RUNNER_TOP_INDEX_ACTUAL_SIZE="$("${WC_BIN}" -c \
  <"${RUNNER_TOP_INDEX_BLOB}" | "${AWK_BIN}" '{print $1}')"
test "${RUNNER_TOP_INDEX_ACTUAL_SIZE}" = "${RUNNER_TOP_INDEX_SIZE}"
RUNNER_TOP_INDEX_SHA="sha256:$("${SHASUM_BIN}" -a 256 \
  "${RUNNER_TOP_INDEX_BLOB}" | "${AWK_BIN}" '{print $1}')"
test "${RUNNER_TOP_INDEX_SHA}" = "${RUNNER_TOP_INDEX_DIGEST}"

RUNNER_PLATFORM_MANIFEST_DIGEST="$("${JQ_BIN}" -er \
  'if (.manifests | length) == 1 and
      .manifests[0].mediaType == "application/vnd.oci.image.manifest.v1+json" and
      .manifests[0].platform.os == "linux" and
      .manifests[0].platform.architecture == "arm64"
   then .manifests[0].digest else error("expected one linux/arm64 manifest") end' \
  "${RUNNER_TOP_INDEX_BLOB}")"
RUNNER_PLATFORM_MANIFEST_SIZE="$("${JQ_BIN}" -er \
  'if (.manifests | length) == 1 and
      .manifests[0].mediaType == "application/vnd.oci.image.manifest.v1+json" and
      .manifests[0].platform.os == "linux" and
      .manifests[0].platform.architecture == "arm64"
   then .manifests[0].size else error("expected one linux/arm64 manifest") end' \
  "${RUNNER_TOP_INDEX_BLOB}")"
printf '%s\n' "${RUNNER_PLATFORM_MANIFEST_DIGEST}" | \
  "${GREP_BIN}" -Eq '^sha256:[0-9a-f]{64}$'
RUNNER_PLATFORM_MANIFEST_BLOB="${RUNNER_OCI_LAYOUT}/blobs/sha256/${RUNNER_PLATFORM_MANIFEST_DIGEST#sha256:}"
test -f "${RUNNER_PLATFORM_MANIFEST_BLOB}"
RUNNER_PLATFORM_MANIFEST_ACTUAL_SIZE="$("${WC_BIN}" -c \
  <"${RUNNER_PLATFORM_MANIFEST_BLOB}" | "${AWK_BIN}" '{print $1}')"
test "${RUNNER_PLATFORM_MANIFEST_ACTUAL_SIZE}" = \
  "${RUNNER_PLATFORM_MANIFEST_SIZE}"
RUNNER_PLATFORM_MANIFEST_SHA="sha256:$("${SHASUM_BIN}" -a 256 \
  "${RUNNER_PLATFORM_MANIFEST_BLOB}" | "${AWK_BIN}" '{print $1}')"
test "${RUNNER_PLATFORM_MANIFEST_SHA}" = "${RUNNER_PLATFORM_MANIFEST_DIGEST}"

RUNNER_CONFIG_DIGEST="$("${JQ_BIN}" -er \
  'if .schemaVersion == 2 and
      .config.mediaType == "application/vnd.oci.image.config.v1+json"
   then .config.digest else error("expected OCI config") end' \
  "${RUNNER_PLATFORM_MANIFEST_BLOB}")"
RUNNER_CONFIG_SIZE="$("${JQ_BIN}" -er \
  'if .schemaVersion == 2 and
      .config.mediaType == "application/vnd.oci.image.config.v1+json"
   then .config.size else error("expected OCI config") end' \
  "${RUNNER_PLATFORM_MANIFEST_BLOB}")"
printf '%s\n' "${RUNNER_CONFIG_DIGEST}" | \
  "${GREP_BIN}" -Eq '^sha256:[0-9a-f]{64}$'
RUNNER_CONFIG_BLOB="${RUNNER_OCI_LAYOUT}/blobs/sha256/${RUNNER_CONFIG_DIGEST#sha256:}"
test -f "${RUNNER_CONFIG_BLOB}"
RUNNER_CONFIG_ACTUAL_SIZE="$("${WC_BIN}" -c \
  <"${RUNNER_CONFIG_BLOB}" | "${AWK_BIN}" '{print $1}')"
test "${RUNNER_CONFIG_ACTUAL_SIZE}" = "${RUNNER_CONFIG_SIZE}"
RUNNER_CONFIG_SHA="sha256:$("${SHASUM_BIN}" -a 256 \
  "${RUNNER_CONFIG_BLOB}" | "${AWK_BIN}" '{print $1}')"
test "${RUNNER_CONFIG_SHA}" = "${RUNNER_CONFIG_DIGEST}"

"${RUNNER_PYTHON}" - "${RUNNER_CONFIG_BLOB}" <<'PY'
import json
import os
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
config = payload.get("config")
history = payload.get("history")
if not isinstance(config, dict) or not isinstance(history, list):
    raise SystemExit("manifest_bound_config_history_invalid")
if config.get("User") != "65532:65532":
    raise SystemExit("manifest_bound_non_root_user_invalid")
if config.get("Cmd") != ["/opt/venv/bin/python", "--version"]:
    raise SystemExit("manifest_bound_entrypoint_invalid")
if config.get("WorkingDir") != "/repo":
    raise SystemExit("manifest_bound_workdir_invalid")


def string_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from string_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from string_values(child)


fields = tuple(string_values(config)) + tuple(string_values(history))
secret_env_names = (
    "PULSEPLATE_PYTHON_INDEX_URL",
    "PULSEPLATE_PYTHON_TRUSTED_HOST",
    "PULSEPLATE_PYTHON_NETRC",
    "PIP_INDEX_URL",
    "PIP_TRUSTED_HOST",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
)
folded_fields = tuple(field.casefold() for field in fields)
if any(name.casefold() in field for name in secret_env_names for field in folded_fields):
    raise SystemExit("proxy_secret_material_present")
for name in secret_env_names:
    secret_value = os.environ.get(name, "")
    if secret_value and any(secret_value in field for field in fields):
        raise SystemExit("proxy_secret_material_present")
PY

"${CONTAINER_BIN}" run --rm --read-only --no-dns "${RUNNER_IMAGE_REF}" \
  /bin/sh -eu -c '
test "$(id -u):$(id -g)" = "65532:65532"
test "$(/opt/venv/bin/python -c "import platform; print(platform.python_version())")" = \
  "3.13.14"
EXPECTED_HTML_PARSER_SHA256='4274e911:2adf3fa5:7c7f9afa:7c9b5c63:1456b18b:7403cc62:7cc5027d:02cdd2ae'
EXPECTED_HTML_PARSER_SHA256="$(printf '%s' "${EXPECTED_HTML_PARSER_SHA256}" | tr -d ':')"
test "$(sha256sum /usr/lib64/python3.13/html/parser.py | cut -d " " -f 1)" = \
  "${EXPECTED_HTML_PARSER_SHA256}"
/opt/venv/bin/python -c "from html.parser import HTMLParser; parser = HTMLParser(); assert parser._pending == []; assert parser._pending_len == 0; assert parser._parse_threshold == 1"
test "$(rpm -q python3.13)" = "python3.13-3.13.14-1.el10_2.aarch64"
test "$(rpm -q git-core)" = "git-core-2.52.0-1.el10.aarch64"
test "$(rpm -q make)" = "make-4.4.1-9.el10.aarch64"
test "$(rpm -q shadow-utils)" = "shadow-utils-4.15.0-11.el10.aarch64"
test "$(rpm -q util-linux-core)" = "util-linux-core-2.40.2-18.el10.aarch64"
expected_rpm_package_count="129"
expected_rpm_inventory_sha256="bf2426b1:94df76bf:c9f26642:a23b7b94:f208ee11:69251070:7d737476:368a34b2"
expected_rpm_inventory_sha256="$(printf "%s" "${expected_rpm_inventory_sha256}" | tr -d ":")"
rpm_inventory="$(rpm -qa --qf "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH} %{SHA256HEADER} %{PAYLOADDIGEST} %{PAYLOADDIGESTALGO}\n" | LC_ALL=C sort)"
test "$(printf "%s\n" "${rpm_inventory}" | wc -l | tr -d " ")" = \
  "${expected_rpm_package_count}"
test "$(printf "%s\n" "${rpm_inventory}" | sha256sum | cut -d " " -f 1)" = \
  "${expected_rpm_inventory_sha256}"
test -x /usr/bin/git
test -x /usr/bin/make
test -x /usr/bin/unshare
printf "%s\n" \
  "uid_gid=65532:65532" \
  "python_version=3.13.14" \
  "rpm_package_count=${expected_rpm_package_count}" \
  "rpm_inventory_sha256=${expected_rpm_inventory_sha256}" \
  "runtime_contract=passed"
' | "${TEE_BIN}" "${RUNNER_RUNTIME_REPORT}"

"${TRIVY_BIN}" image --download-db-only --no-progress
"${TRIVY_BIN}" image --input "${RUNNER_OCI_LAYOUT}" \
  --scanners vuln \
  --severity HIGH,CRITICAL \
  --ignorefile /dev/null \
  --ignore-unfixed=false \
  --exit-code 1 \
  --format json \
  --output "${RUNNER_TRIVY_REPORT}"
TRIVY_COVERAGE_RECEIPT="$(
  "${RUNNER_PYTHON}" - "${RUNNER_TRIVY_REPORT}" <<'PY'
import json
from pathlib import Path
import sys


def fail(reason):
    raise SystemExit(f"trivy_admission_report_invalid:{reason}")


def package_count(result):
    packages = result.get("Packages")
    if not isinstance(packages, list) or not packages:
        fail("packages")
    identities = set()
    for package in packages:
        if not isinstance(package, dict):
            fail("package_shape")
        name = package.get("Name")
        version = package.get("Version")
        if not isinstance(name, str) or not name:
            fail("package_identity")
        if not isinstance(version, str) or not version:
            fail("package_identity")
        identity = (name, version)
        if identity in identities:
            fail("duplicate_package")
        identities.add(identity)
    return len(packages)


if len(sys.argv) != 2:
    fail("arguments")
try:
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    fail("json")
if not isinstance(report, dict):
    fail("report_shape")
if report.get("SchemaVersion") != 2:
    fail("schema_version")
if report.get("ArtifactType") != "container_image":
    fail("artifact_type")
metadata = report.get("Metadata")
if not isinstance(metadata, dict):
    fail("metadata")
operating_system = metadata.get("OS")
if not isinstance(operating_system, dict):
    fail("os_metadata")
if operating_system.get("Family") != "redhat" or operating_system.get("Name") != "10.2":
    fail("os_identity")
results = report.get("Results")
if not isinstance(results, list) or not results:
    fail("results")

os_package_counts = []
python_package_counts = []
finding_count = 0
for result in results:
    if not isinstance(result, dict):
        fail("result_shape")
    target = result.get("Target")
    result_class = result.get("Class")
    result_type = result.get("Type")
    if not all(
        isinstance(value, str) and value
        for value in (target, result_class, result_type)
    ):
        fail("result_identity")
    current_package_count = package_count(result)
    if "Vulnerabilities" in result:
        vulnerabilities = result["Vulnerabilities"]
        if not isinstance(vulnerabilities, list):
            fail("vulnerabilities")
        if any(not isinstance(vulnerability, dict) for vulnerability in vulnerabilities):
            fail("vulnerability_shape")
        finding_count += len(vulnerabilities)
    if result_class == "os-pkgs" and result_type == "redhat":
        os_package_counts.append(current_package_count)
    if (
        result_class == "lang-pkgs"
        and result_type == "python-pkg"
        and target == "Python"
    ):
        python_package_counts.append(current_package_count)

if len(os_package_counts) != 1:
    fail("os_coverage")
if len(python_package_counts) != 1:
    fail("python_coverage")
if os_package_counts[0] != 129:
    fail("os_package_count")
if python_package_counts[0] != 136:
    fail("python_package_count")
if finding_count:
    fail("selected_findings")

print(
    "\n".join(
        (
            "trivy_artifact_type=container_image",
            "trivy_os_family=redhat",
            "trivy_os_version=10.2",
            "trivy_os_package_count=129",
            "trivy_python_package_count=136",
            "trivy_high_critical_findings=0",
        )
    )
)
PY
)"
"${RUNNER_PYTHON}" scripts/orchestration/experiment_runner_dispatch.py probe \
  --backend apple-container \
  --image "${RUNNER_IMAGE_REF}" \
  --output "${RUNNER_PROBE_ARTIFACT}" | \
  "${TEE_BIN}" "${RUNNER_PROBE_STDOUT}"
printf '%s\n' \
  'trivy_checksum_exit=0' \
  'image_inspect_exit=0' \
  'oci_descriptor_validation_exit=0' \
  'config_history_validation_exit=0' \
  'runtime_contract_exit=0' \
  'trivy_exit=0' \
  "${TRIVY_COVERAGE_RECEIPT}" \
  'apple_probe_exit=0' \
  >"${RUNNER_STATUS_REPORT}"
```

The inspection and export must agree on the Apple-returned top index digest.
Admission then hashes that top-index blob, requires and hashes exactly one
`linux/arm64` manifest, resolves and hashes its config blob, and inspects only
that manifest-bound config/history for configured proxy-secret names and every
non-empty current secret value without printing those values. Runtime checks
bind UID/GID 65532, Python 3.13.14, the exact CPython patch content, exact RPM
versions, and required executables to the same digest. The downloaded official
Trivy asset must pass its official release checksum before it scans the exact
OCI layout. The self-contained Python coverage guard then requires Trivy schema
v2, a `container_image` artifact, exact Red Hat 10.2 metadata, exactly one
129-package OS result, and exactly one 136-package Python result before it
accepts the absence of selected findings. The command writes sanitized runtime
output, probe output, scanner JSON, and one success-only exit-status receipt
beneath the digest-bound local evidence directory. Because `set -euo pipefail`
is active, a failed producer or coverage guard cannot be hidden, and the
all-zero status receipt is never written after a failed admission step.

The admitted UBI image reported Red Hat 10.2 with 129 OS packages and 136
packages in one Python dependency manifest. The unfiltered OS-and-language scan
reported zero HIGH/CRITICAL findings under the explicit `/dev/null` ignore
policy with unfixed findings included. The strict Apple 1.1.0 probe passed
every required network, mount, digest, cleanup, and non-root control for the
same digest. The sanitized build, runtime, scanner, and probe receipts are
recorded in
`docs/security/EXPERIMENT_RUNNER_CONTAINER_CVE_REMEDIATION.md`. Run the final
immutable-oracle review only after material freeze and do not edit tracked
material afterward. A failed inspection, digest check, checksum, scan, or
probe blocks oracle execution; do not weaken the package, network, or
suppression policy to force admission.

Rollback this candidate only by preserving any failed UBI admission evidence,
deleting the candidate image by its exact digest, and reverting the UBI
base/package/CPython patch pin plus its image-specific tests and evidence
documentation. The fail-closed Trivy coverage guard must remain in the
admission path; a guard regression keeps the runner blocked and requires a
fix-forward. The runner result contract and capability schema are unchanged.
Neither the failed slim-trixie image, incompatible Alpine recipe, nor blocked
bookworm baseline becomes a fallback; only a separately and explicitly
admitted immutable runner is eligible, and a mutable tag is never eligible.

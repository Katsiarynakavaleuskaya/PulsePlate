# Experiment Runner strict macOS backend

Status: local development evidence only. This backend does not grant PR,
promotion, merge, release, GitHub App, or Slack authority.

## Current local qualification boundary

`LOCAL-ORACLE-RUNNER-QUALIFICATION-1/v2` is in progress. The source recipe now
preserves the original builder and uses ordinary runtime-preparation for exact
pip, pip-api, pip-tools, pip-audit, virtualenv and pre-commit retirement, with pip
last. Its final venv excludes those tools and eight launchers; the final system
retires the positively guarded inherited pip seed and full ensurepip tree.
Healthy build and all other distribution payload/default plugins stay required.
The expected seed pin is historical source evidence, not a fresh observation.

The exact owner-approved preservation exceptions are ast-serialize 0.6.0 to
0.7.0, Pydantic 2.13.4 to 2.14.1, pydantic-core 2.46.4 to 2.50.1,
typing-extensions 4.15.0 to 4.16.0 and typing-inspection 0.4.2 to 0.4.4.
The genuine runtime-first commit and all six constrained canonical Make outputs
have been retained; every other dependency tuple is unchanged. These selected
Python floors do not invent advisory ranges from the wheels' Cargo components.
Ast remains owned by dev/aggregate, with no pure runtime/Docker/CI-lite addition.
Every unaffected native payload and all original twelve outcomes remain required.

Before any actual pruning build, the operator must capture the original builder's
selected AND every retained native RECORD/payload/version/type/mode/link/cache,
shared owners and actual sole system seed source/RPM/type/bytes/hash. Selected-only
RECORDs and subtraction of historical counts are insufficient. Preserve SDK,
proxy/default CA/locks and acquisition-cleanup/quarantine/network-none validation/
activation/offline-consume/native-COPY ordering. No seventh distribution or
orphan sweep is admitted.

The image-specific admission pins in the historical example below have NOT
been updated to a qualified successor. They remain hard
checks, not parameters to bypass. A successor needs observed full native final
RPM/Python/vendor/lineage and current OCI descriptors before these pins can be
reconciled. Actual failed179 and four-HIGH222 remain failed/unqualified; the
separate222 secret output contained OS130/Python152 Packages and no Secrets.
Source tests and an empty Secrets field never promote those histories.
The obsolete pip capture and its root/18-vendor checks have been removed. The
same consumer rejects admission with `vendor_producer_evidence_pending` until
all eight actual retained source artifacts and their genuine native producer
statuses/reports have independent physical-profile bindings. Until those
operands and new subject pins exist,
the historical command block cannot admit the successor. Do not delete that
requirement, substitute an empty BOM or infer replacement counts from source.

Native qualification must independently prove ordinary-site original system AND
venv module/metadata/physical/launcher/seed absence, usable `venv --without-pip`,
and default CLI venv (or explicit `with_pip=True`) failing at genuine ensurepip
bootstrap before installation. `EnvBuilder()` defaults to bare behavior and is
not that negative. Retained build1.5 default isolation needs a real valid writable
project and backend declaration, reaching the intended bootstrap failure before
install; a fake backend or permission/project error is not proof. Keep the real
process census at its existing one-second bound and qualify complete SDK/SSL/CA/
DSO/HTTP/TLS/PostgreSQL and strict Apple behavior on the successor.

This lane keeps Docker closed. Independently reviewed immutable control, distinct
material, actual source/SDK/image/argv/output/redaction/cleanup admission precedes
native work; source hashes cannot self-admit it. Qualify the image first, then
one admitted original-three-command Apple Oracle may evidence default plugins
and the Oracle outcome separately. Its original commands/order and600/test3/
network0/provider0 stay unchanged; the candidate path cap does not truncate the
complete actual review context. All twelve accepted outcomes remain pending.

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

First qualify the genuine Linux aarch64 CPython 3.13 SDK from its matching
immutable source image. Bind the actual producer operation, exported complete
payload and private owned `0700` root before any secret-bearing Runner build.
The required `--psycopg-sdk-root` directory carries the receipt and one opaque
wheel under `psycopg-sdk/`, the declared libpq/OpenSSL files and internal libpq
alias, and native licenses/configuration under `usr/local/`. The dispatcher
rejects additional members and rechecks the actual private staged context
before proxy-secret lookup. Directory names and self-hashes do not prove origin;
the canonical installer inside UBI performs SDK, source and ABI admission.

Both backend build commands below use that same admitted root. Preserve the
original UBI default CA bundle when connecting the custom OpenSSL defaults.
Observe final system `_ssl` and HTTP default trust, provider behavior, actual
loaded DSO hashes, Psycopg/database calls, full native inventory and strict
Apple isolation before selecting a successor image. Historical image evidence remains retained; it does not admit the successor
or authorize a fresh mandatory Oracle before complete qualification passes.

The admitted source recipe starts from the pinned official UBI 10 minimal
multi-architecture digest
`registry.access.redhat.com/ubi10/ubi-minimal@sha256:04140c8d78c6c6915b5c1fdad2f16d10eac3630c3339999ccdf659d8c903be50`.
It verifies the official EPEL 10 key and release RPM, installs exact Python
3.13.16 packages, and overlays the checksum-pinned official CPython 3.13
backport for `CVE-2026-15308`. The final image keeps the locked `runtime-dev`
environment and non-root UID/GID 65532. Proxy values enter BuildKit as secrets
and are not build arguments or runtime environment variables. A source pin is
not reusable admission evidence; every material rebuild needs a new exact
image digest and the complete sequence below.

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend apple-container \
  --psycopg-sdk-root /absolute/private/qualified-arm-sdk \
  --tag pulseplate/experiment-runner:mac-local
```

The command returns a sanitized `name@sha256:<digest>` reference. Preserve that
exact reference for `probe` and `run`; mutable tags are rejected by `run`.

Docker fallback build:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py build-image \
  --backend docker \
  --psycopg-sdk-root /absolute/private/qualified-arm-sdk \
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

The historical UBI recipe built through the canonical Apple dispatcher as image
index
`sha256:5b3abbad998dc1b23f9d99e72a8fde931558401b81a2aec8c5eeeff90b128a70`.
Its exact `linux/arm64` manifest is
`sha256:c46d2bd8a174b6b10b9ed06c1c145eeb1ca131d326c67b4c72589ea84e6d1750`,
and its manifest-bound config/history is
`sha256:b96621e97fd78527a93f9853970d1f17baffa46e8d188e5341899fc6a1efaa1d`.
These coordinates describe the historical image. The current SDK candidate has
eight layers and requires its own observed immutable reference and all current
admission checks below; it is not selected by the historical receipt.
The scan must consume the exact OCI layout cryptographically traversed from
that Apple image digest; a mutable tag, bare repository-context scan, or
unverified PATH Trivy binary is not evidence. Download the official Trivy
0.74.0 macOS ARM64 asset and its official release checksums, verify the asset
before execution, refresh its vulnerability database, and run:

```bash
set -euo pipefail
umask 077

RUNNER_IMAGE_REF='pulseplate/experiment-runner:mac-local@sha256:<digest>'
RUNNER_IMAGE_DIGEST="${RUNNER_IMAGE_REF##*@}"
RUNNER_EVIDENCE_PARENT='artifacts/orchestration/security'
RUNNER_EVIDENCE_DIR="${RUNNER_EVIDENCE_PARENT}/runner-${RUNNER_IMAGE_DIGEST#sha256:}"
RUNNER_INSPECT_JSON="${RUNNER_EVIDENCE_DIR}/apple-image-inspect.json"
RUNNER_OCI_ARCHIVE="${RUNNER_EVIDENCE_DIR}/runner.oci.tar"
RUNNER_OCI_LAYOUT="${RUNNER_EVIDENCE_DIR}/oci-layout"
RUNNER_TRIVY_REPORT="${RUNNER_EVIDENCE_DIR}/trivy-0.74.0.json"
RUNNER_TRIVY_DIR="${RUNNER_EVIDENCE_DIR}/trivy-0.74.0"
RUNNER_RUNTIME_REPORT="${RUNNER_EVIDENCE_DIR}/runtime-contract.stdout"
RUNNER_PROBE_STDOUT="${RUNNER_EVIDENCE_DIR}/apple-probe.stdout"
RUNNER_STATUS_REPORT="${RUNNER_EVIDENCE_DIR}/admission-exit-statuses.txt"
RUNNER_PROBE_ARTIFACT="mac-strict-capability-${RUNNER_IMAGE_DIGEST#sha256:}.json"
TRIVY_VERSION='0.74.0'
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
# All scanner processes use fresh private state, never ambient host configuration.
RUNNER_SCAN_ROOT="$("${RUNNER_PYTHON}" -I -c 'import os, sys; print(os.path.abspath(sys.argv[1]))' "${RUNNER_TRIVY_DIR}")"
RUNNER_SCAN_HOME="${RUNNER_SCAN_ROOT}/home"
RUNNER_SCAN_CACHE="${RUNNER_SCAN_ROOT}/cache"
RUNNER_SCAN_TMP="${RUNNER_SCAN_ROOT}/tmp"
mkdir -m 700 "${RUNNER_SCAN_HOME}" "${RUNNER_SCAN_CACHE}" "${RUNNER_SCAN_TMP}"
/usr/bin/env -i HOME="${RUNNER_SCAN_HOME}" TMPDIR="${RUNNER_SCAN_TMP}" \
  XDG_CACHE_HOME="${RUNNER_SCAN_CACHE}" PATH=/usr/bin:/bin LANG=C LC_ALL=C \
  "${TRIVY_BIN}" --config /dev/null --cache-dir "${RUNNER_SCAN_CACHE}" --version | "${GREP_BIN}" -Fx 'Version: 0.74.0'

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

test "${RUNNER_TOP_INDEX_DIGEST}" = "sha256:df9285934fe1ecd12e4c5317ddceae874a77270730afe58f9eca38f983bd69b4"
"${JQ_BIN}" -e '. == {
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.index.v1+json",
  "manifests": [
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "digest": "sha256:a9f97d6eeee4ada7952d927c44527363c6d1f2a55515dfef9bcef007437633e3",
      "size": 1819,
      "platform": {
        "architecture": "arm64",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "digest": "sha256:1f748a696b62f940dc2e1703d5ecd5a0d0e2c67dc3ab792a779f45e80e1823eb",
      "size": 837,
      "annotations": {
        "vnd.docker.reference.digest": "sha256:a9f97d6eeee4ada7952d927c44527363c6d1f2a55515dfef9bcef007437633e3",
        "vnd.docker.reference.type": "attestation-manifest"
      },
      "platform": {
        "architecture": "unknown",
        "os": "unknown"
      }
    }
  ]
}' "${RUNNER_TOP_INDEX_BLOB}" >/dev/null
RUNNER_PLATFORM_MANIFEST_DIGEST="$("${JQ_BIN}" -er '.manifests[0].digest' "${RUNNER_TOP_INDEX_BLOB}")"
RUNNER_PLATFORM_MANIFEST_SIZE="$("${JQ_BIN}" -er '.manifests[0].size' "${RUNNER_TOP_INDEX_BLOB}")"
while read -r expected_digest expected_size; do
  attestation_blob="${RUNNER_OCI_LAYOUT}/blobs/sha256/${expected_digest#sha256:}"
  test ! -L "${attestation_blob}"
  test -f "${attestation_blob}"
  test "$("${WC_BIN}" -c <"${attestation_blob}" | "${AWK_BIN}" '{print $1}')" = "${expected_size}"
  test "sha256:$("${SHASUM_BIN}" -a 256 "${attestation_blob}" | "${AWK_BIN}" '{print $1}')" = "${expected_digest}"
done <<'EXPECTED_CURRENT_ATTESTATION'
sha256:1f748a696b62f940dc2e1703d5ecd5a0d0e2c67dc3ab792a779f45e80e1823eb 837
sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a 2
sha256:f60c3efc8677b9bf81b2781c33df8614195e9461096bb4a3fa4e06df8c491df8 3202
EXPECTED_CURRENT_ATTESTATION
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

OCI_LAYER_RECEIPT="$(
  "${RUNNER_PYTHON}" - \
    "${RUNNER_PLATFORM_MANIFEST_BLOB}" "${RUNNER_OCI_LAYOUT}" <<'PY'
import hashlib
import json
from pathlib import Path
import re
import stat
import sys


def fail(reason):
    raise SystemExit(f"oci_layer_validation_invalid:{reason}")


if len(sys.argv) != 3:
    fail("arguments")
manifest_path = Path(sys.argv[1])
layout_path = Path(sys.argv[2])
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError):
    fail("manifest_json")
if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 2:
    fail("manifest_shape")
layers = manifest.get("layers")
if not isinstance(layers, list) or len(layers) != 8:
    fail("layer_count")

seen_digests = set()
for descriptor in layers:
    if not isinstance(descriptor, dict):
        fail("descriptor_shape")
    if descriptor.get("mediaType") != "application/vnd.oci.image.layer.v1.tar+gzip":
        fail("media_type")
    digest = descriptor.get("digest")
    size = descriptor.get("size")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        fail("digest")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        fail("size")
    if digest in seen_digests:
        fail("duplicate_digest")
    seen_digests.add(digest)

    blob_path = layout_path / "blobs" / "sha256" / digest.removeprefix("sha256:")
    try:
        blob_stat = blob_path.lstat()
    except OSError:
        fail("blob_missing")
    if not stat.S_ISREG(blob_stat.st_mode):
        fail("blob_not_regular")
    if blob_stat.st_size != size:
        fail("blob_size")
    actual_digest = hashlib.sha256()
    try:
        with blob_path.open("rb") as blob:
            for chunk in iter(lambda: blob.read(1024 * 1024), b""):
                actual_digest.update(chunk)
    except OSError:
        fail("blob_read")
    if actual_digest.hexdigest() != digest.removeprefix("sha256:"):
        fail("blob_digest")

print(f"oci_layer_count={len(layers)}")
PY
)"

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
  "3.13.16"
EXPECTED_HTML_PARSER_SHA256='4274e911:2adf3fa5:7c7f9afa:7c9b5c63:1456b18b:7403cc62:7cc5027d:02cdd2ae'
EXPECTED_HTML_PARSER_SHA256="$(printf '%s' "${EXPECTED_HTML_PARSER_SHA256}" | tr -d ':')"
test "$(sha256sum /usr/lib64/python3.13/html/parser.py | cut -d " " -f 1)" = \
  "${EXPECTED_HTML_PARSER_SHA256}"
/opt/venv/bin/python -c "from html.parser import HTMLParser; parser = HTMLParser(); assert parser._pending == []; assert parser._pending_len == 0; assert parser._parse_threshold == 1"
rpm_query_output="$(rpm -q python3.13)"
test "${rpm_query_output}" = "python3.13-3.13.16-1.el10_2.aarch64"
rpm_query_output="$(rpm -q git-core)"
test "${rpm_query_output}" = "git-core-2.52.0-1.el10.aarch64"
rpm_query_output="$(rpm -q make)"
test "${rpm_query_output}" = "make-4.4.1-9.el10.aarch64"
rpm_query_output="$(rpm -q shadow-utils)"
test "${rpm_query_output}" = "shadow-utils-4.15.0-11.el10.aarch64"
rpm_query_output="$(rpm -q util-linux-core)"
test "${rpm_query_output}" = "util-linux-core-2.40.2-18.el10.aarch64"
expected_rpm_package_count="129"
expected_rpm_inventory_sha256="4a9eb99a:ba1b6a59:9fccd7ef:6d32a3b6:cbed8b47:4e89de93:6697a78b:370494a8"
expected_rpm_inventory_sha256="$(printf "%s" "${expected_rpm_inventory_sha256}" | tr -d ":")"
rpm_inventory="$(rpm -qa --qf "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH} %{SHA256HEADER} %{PAYLOADDIGEST} %{PAYLOADDIGESTALGO}\n")"
rpm_inventory="$(printf "%s\n" "$rpm_inventory" | LC_ALL=C sort)"
test "$(printf "%s\n" "${rpm_inventory}" | wc -l | tr -d " ")" = \
  "${expected_rpm_package_count}"
test "$(printf "%s\n" "${rpm_inventory}" | sha256sum | cut -d " " -f 1)" = \
  "${expected_rpm_inventory_sha256}"
test -x /usr/bin/git
test -x /usr/bin/make
test -x /usr/bin/unshare
printf "%s\n" \
  "uid_gid=65532:65532" \
  "python_version=3.13.16" \
  "rpm_package_count=${expected_rpm_package_count}" \
  "rpm_inventory_sha256=${expected_rpm_inventory_sha256}" \
  "runtime_contract=passed"
' | "${TEE_BIN}" "${RUNNER_RUNTIME_REPORT}"

/usr/bin/env -i HOME="${RUNNER_SCAN_HOME}" TMPDIR="${RUNNER_SCAN_TMP}" \
  XDG_CACHE_HOME="${RUNNER_SCAN_CACHE}" PATH=/usr/bin:/bin LANG=C LC_ALL=C \
  "${TRIVY_BIN}" --config /dev/null --cache-dir "${RUNNER_SCAN_CACHE}" image --download-db-only --no-progress --secret-config=
# Fresh output paths plus both native statuses are required, even on rejection.
RUNNER_SECRET_REPORT="${RUNNER_EVIDENCE_DIR}/trivy-secrets.json"
for output in "${RUNNER_TRIVY_REPORT}" "${RUNNER_SECRET_REPORT}" \
  "${RUNNER_EVIDENCE_DIR}/trivy-vuln.stdout" "${RUNNER_EVIDENCE_DIR}/trivy-vuln.stderr" \
  "${RUNNER_EVIDENCE_DIR}/trivy-secret.stdout" "${RUNNER_EVIDENCE_DIR}/trivy-secret.stderr"; do
  test ! -e "$output"; test ! -L "$output"
done
RUNNER_TRIVY_STARTED_NS="$("${RUNNER_PYTHON}" -c 'import time; print(time.time_ns())')"
if /usr/bin/env -i HOME="${RUNNER_SCAN_HOME}" TMPDIR="${RUNNER_SCAN_TMP}" \
  XDG_CACHE_HOME="${RUNNER_SCAN_CACHE}" PATH=/usr/bin:/bin LANG=C LC_ALL=C \
  "${TRIVY_BIN}" --config /dev/null --cache-dir "${RUNNER_SCAN_CACHE}" image --input "${RUNNER_OCI_LAYOUT}" \
  --secret-config= \
  --skip-db-update --scanners vuln --severity HIGH,CRITICAL \
  --ignorefile /dev/null --ignore-policy= --ignore-status= \
  --ignore-unfixed=false --vex= --exit-code 1 --format json \
  --output "${RUNNER_TRIVY_REPORT}" \
  >"${RUNNER_EVIDENCE_DIR}/trivy-vuln.stdout" \
  2>"${RUNNER_EVIDENCE_DIR}/trivy-vuln.stderr"; then
  RUNNER_VULN_STATUS=0
else
  RUNNER_VULN_STATUS=$?
fi
if /usr/bin/env -i HOME="${RUNNER_SCAN_HOME}" TMPDIR="${RUNNER_SCAN_TMP}" \
  XDG_CACHE_HOME="${RUNNER_SCAN_CACHE}" PATH=/usr/bin:/bin LANG=C LC_ALL=C \
  "${TRIVY_BIN}" --config /dev/null --cache-dir "${RUNNER_SCAN_CACHE}" image --input "${RUNNER_OCI_LAYOUT}" \
  --secret-config= \
  --skip-db-update --scanners secret --image-config-scanners secret \
  --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
  --ignorefile /dev/null --ignore-policy= --ignore-status= \
  --ignore-unfixed=false --vex= --exit-code 1 --format json \
  --output "${RUNNER_SECRET_REPORT}" \
  >"${RUNNER_EVIDENCE_DIR}/trivy-secret.stdout" \
  2>"${RUNNER_EVIDENCE_DIR}/trivy-secret.stderr"; then
  RUNNER_SECRET_STATUS=0
else
  RUNNER_SECRET_STATUS=$?
fi
printf 'trivy_vuln_exit=%s\ntrivy_secret_exit=%s\n' \
  "${RUNNER_VULN_STATUS}" "${RUNNER_SECRET_STATUS}" >"${RUNNER_STATUS_REPORT}"
TRIVY_COVERAGE_RECEIPT="$(
  "${RUNNER_PYTHON}" - "${RUNNER_TRIVY_REPORT}" "${RUNNER_SECRET_REPORT}" "${RUNNER_OCI_LAYOUT}" "${RUNNER_TOP_INDEX_DIGEST}" "${RUNNER_VULN_STATUS}" "${RUNNER_SECRET_STATUS}" "${RUNNER_TRIVY_STARTED_NS}" <<'PY'
import hashlib
import json
import os
import re
import stat
from pathlib import Path
import sys


def fail(reason):
    raise SystemExit(f"trivy_admission_report_invalid:{reason}")


def read_report(path, label, started_ns):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 64 * 1024**2:
                fail(label + "_read")
            if before.st_mtime_ns < started_ns:
                fail(label + "_freshness")
            raw = stream.read(64 * 1024**2 + 1)
            after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            fail(label + "_read")
        return json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        fail(label + "_read")


# Recheck the current exported chain after BOTH producers, not just their pair.
def oci_blob(descriptor):
    if not isinstance(descriptor, dict):
        fail("oci_blob")
    digest, size = descriptor.get("digest"), descriptor.get("size")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or type(size) is not int or size <= 0:
        fail("oci_blob")
    path = layout / "blobs" / "sha256" / digest.removeprefix("sha256:")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size != size:
                fail("oci_blob")
            actual = hashlib.sha256()
            raw = bytearray()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                actual.update(chunk)
                if descriptor.get("mediaType") != "application/vnd.oci.image.layer.v1.tar+gzip":
                    raw.extend(chunk)
                    if len(raw) > 16 * 1024**2:
                        fail("oci_blob")
            after = os.fstat(stream.fileno())
        if actual.hexdigest() != digest.removeprefix("sha256:") or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            fail("oci_blob")
        return bytes(raw)
    except OSError:
        fail("oci_blob")


def current_subject(report):
    if not isinstance(report, dict) or report.get("SchemaVersion") != 2 or report.get("ArtifactType") != "container_image":
        fail("current_subject")
    metadata = report.get("Metadata")
    if not isinstance(metadata, dict) or report.get("ArtifactID") != config_digest or metadata.get("ImageID") != config_digest or metadata.get("DiffIDs") != diff_ids or report.get("ArtifactName") != str(layout) or report.get("Trivy") != {"Version": "0.74.0"}:
        fail("current_subject")


def package_count(result):
    packages = result.get("Packages")
    if not isinstance(packages, list) or not packages:
        fail("packages")
    python_result = (result.get("Class"), result.get("Type"), result.get("Target")) == ("lang-pkgs", "python-pkg", "Python")
    identities, top_names, top_paths = set(), set(), set()
    physical_records = set()
    for package in packages:
        if not isinstance(package, dict):
            fail("package_shape")
        name, version = package.get("Name"), package.get("Version")
        if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
            fail("package_identity")
        if not python_result:
            if (name, version) in identities:
                fail("duplicate_package")
            identities.add((name, version))
            continue
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        identifier = package.get("Identifier")
        expected_purl = "pkg:pypi/" + normalized + "@" + version
        if not isinstance(identifier, dict) or identifier.get("PURL") != expected_purl or package.get("Layer") != EXPECTED_PYTHON_LAYER:
            fail("python_package_lineage")
        if package.get("AnalyzedBy") == "python-pkg":
            path = package.get("FilePath")
            match = re.fullmatch(r"opt/venv/lib/python3[.]13/site-packages/([A-Za-z0-9._-]+)[.]dist-info/METADATA", path) if isinstance(path, str) else None
            if match is None:
                fail("python_metadata_origin")
            directory_name, separator, directory_version = match.group(1).rpartition("-")
            if not separator or re.sub(r"[-_.]+", "-", directory_name).lower() != normalized or directory_version != version:
                fail("python_metadata_identity")
            if normalized in top_names or path in top_paths or (normalized, version) in identities:
                fail("duplicate_package")
            top_names.add(normalized)
            top_paths.add(path)
            physical_records.add((normalized, version, path))
            identities.add((normalized, version))
        else:
            fail("python_unknown_origin")
    if python_result:
        if len(top_names) != 134 or len(top_paths) != 134 or len(identities) != 134:
            fail("python_package_count")
        inventory_bytes = json.dumps(sorted(physical_records), separators=(",", ":"), ensure_ascii=True).encode("ascii")
        if hashlib.sha256(inventory_bytes).hexdigest() != '15b8a47e4a9978b9efc73e395bcc691246594d2a987f792dbdfc338bc827437e':
            fail("python_physical_inventory")
        return len(identities)
    return len(packages)


EXPECTED_PYTHON_LAYER = {'Digest': 'sha256:1fb871361e453637230e1d88374621b44811cd6c365ecda7acb229ed5646c346', 'DiffID': 'sha256:e27988ccf24b562c671d682a9f091034066e843c6646e33bbd6eb5b2494eecec'}

if len(sys.argv) != 8:
    fail("arguments")
if sys.argv[5] not in {"0", "1"} or sys.argv[6] not in {"0", "1"}:
    fail("producer_status")
if not re.fullmatch(r"[1-9][0-9]*", sys.argv[7]):
    fail("producer_start")
started_ns = int(sys.argv[7])
layout = Path(sys.argv[3])
try:
    index = read_report(layout / "index.json", "oci_index", 0)
    roots = index.get("manifests") if isinstance(index, dict) else None
    if not isinstance(index, dict) or index.get("schemaVersion") != 2 or not isinstance(roots, list) or len(roots) != 1 or roots[0].get("digest") != sys.argv[4] or roots[0].get("mediaType") != "application/vnd.oci.image.index.v1+json":
        fail("current_subject")
    top = json.loads(oci_blob(roots[0]))
    if not isinstance(top, dict) or top.get("schemaVersion") != 2:
        fail("current_subject")
    platforms = [d for d in top.get("manifests", []) if isinstance(d, dict) and d.get("platform") == {"architecture": "arm64", "os": "linux"}]
    if len(platforms) != 1 or platforms[0].get("mediaType") != "application/vnd.oci.image.manifest.v1+json":
        fail("current_subject")
    manifest = json.loads(oci_blob(platforms[0]))
    if not isinstance(manifest, dict) or manifest.get("schemaVersion") != 2:
        fail("current_subject")
    config_descriptor = manifest.get("config")
    if not isinstance(config_descriptor, dict) or config_descriptor.get("mediaType") != "application/vnd.oci.image.config.v1+json":
        fail("current_subject")
    config = json.loads(oci_blob(config_descriptor))
    config_digest = config_descriptor["digest"]
    rootfs = config.get("rootfs")
    diff_ids = rootfs.get("diff_ids") if isinstance(rootfs, dict) else None
    layers = manifest.get("layers")
    if config.get("architecture") != "arm64" or config.get("os") != "linux" or not isinstance(layers, list) or not layers or not isinstance(diff_ids, list) or len(layers) != len(diff_ids) or any(not isinstance(d, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", d) for d in diff_ids):
        fail("current_subject")
    for layer in layers:
        if not isinstance(layer, dict) or layer.get("mediaType") != "application/vnd.oci.image.layer.v1.tar+gzip":
            fail("oci_blob")
        oci_blob(layer)
    if EXPECTED_PYTHON_LAYER not in [{"Digest": layer["digest"], "DiffID": diff_id} for layer, diff_id in zip(layers, diff_ids)]:
        fail("python_package_lineage")
except (KeyError, TypeError, AttributeError, UnicodeDecodeError, json.JSONDecodeError):
    fail("current_subject")
secret_report = read_report(sys.argv[2], "secret", started_ns)
current_subject(secret_report)
secret_results = secret_report.get("Results")
if not isinstance(secret_results, list) or not secret_results:
    fail("secret_shape")
secret_identities = set()
for result in secret_results:
    if not isinstance(result, dict):
        fail("secret_shape")
    if "Secrets" in result:
        if not isinstance(result["Secrets"], list) or any(not isinstance(finding, dict) for finding in result["Secrets"]):
            fail("secret_shape")
        if result["Secrets"]:
            fail("secret_findings")
    # Native empty0.74 reports retain OS/Python Packages with no Secrets.
    # Positive file/config rows reject above; no invented positive schema here.
    if (result.get("Class"), result.get("Type")) not in {("os-pkgs", "redhat"), ("lang-pkgs", "python-pkg")} or not isinstance(result.get("Target"), str) or not result["Target"] or not isinstance(result.get("Packages"), list) or not result["Packages"]:
        fail("secret_shape")
    identity = (result["Class"], result["Type"])
    if identity in secret_identities:
        fail("secret_shape")
    secret_identities.add(identity)
    for package in result["Packages"]:
        if not isinstance(package, dict) or any(not isinstance(package.get(key), str) or not package[key] for key in ("Name", "Version")):
            fail("secret_shape")
if secret_identities != {("os-pkgs", "redhat"), ("lang-pkgs", "python-pkg")}:
    fail("secret_shape")
# Apply the physical/origin baseline to the secret producer independently.
# Merely matching the vulnerability producer (or retaining nonempty names)
# does not establish the actual inventory. This baseline remains historical
# until successor native operands are measured and rebound above.
secret_counts = {}
for result in secret_results:
    identity = (result["Class"], result["Type"], result["Target"])
    if identity in secret_counts:
        fail("secret_shape")
    secret_counts[identity] = package_count(result)
if sorted(secret_counts.values()) != [129, 134]:
    fail("secret_package_count")
if not any(identity[:2] == ("os-pkgs", "redhat") and count == 129 for identity, count in secret_counts.items()) or secret_counts.get(("lang-pkgs", "python-pkg", "Python")) != 134:
    fail("secret_package_count")

report = read_report(sys.argv[1], "vuln", started_ns)
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
    if "Secrets" in result:
        secrets = result["Secrets"]
        if not isinstance(secrets, list) or secrets:
            fail("secrets")
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
if python_package_counts[0] != 134:
    fail("python_package_count")
if finding_count:
    fail("selected_findings")
current_subject(report)
if sys.argv[5:7] != ["0", "0"]:
    fail("producer_status")

# The eight retained source/native-report/status bindings have not yet been
# rebound to a measured successor. Removing the retired pip operand supplies
# no replacement vendor evidence and cannot authorize image admission.
fail("vendor_producer_evidence_pending")
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
  "${OCI_LAYER_RECEIPT}" \
  'config_history_validation_exit=0' \
  'runtime_contract_exit=0' \
  "trivy_vuln_exit=${RUNNER_VULN_STATUS}" \
  "trivy_secret_exit=${RUNNER_SECRET_STATUS}" \
  "${TRIVY_COVERAGE_RECEIPT}" \
  'apple_probe_exit=0' \
  >>"${RUNNER_STATUS_REPORT}"
```

The inspection and export must agree on the Apple-returned top index digest.
Admission then hashes that top-index blob, requires the exact current runtime
and linked metadata descriptors, hashes the metadata blobs, and hashes the one
`linux/arm64` runtime manifest, verifies every one of its eight referenced layer blobs
as a regular file with the descriptor's exact byte length and SHA-256, resolves
and hashes its config blob, and inspects only that manifest-bound
config/history for configured proxy-secret names and every non-empty current
secret value without printing those values. Runtime checks bind UID/GID 65532,
Python 3.13.16, the exact CPython patch content, exact RPM versions, and
required executables to the same digest. The downloaded official Trivy asset
must pass its official release checksum before it scans the exact OCI layout.
Database acquisition and both separate image producers run with an allowlisted
empty environment, private HOME/cache/TMP and an explicit cache directory shared
only by these operations. Version inspection uses the same private environment.
`--config /dev/null` excludes the main config; separate `--secret-config=` selects
Trivy0.74.0's empty-path built-in rule branch, excluding ambient/default
`trivy-secret.yaml`. This retains upstream built-in allow rules and default skip
patterns; it is not a claim to scan every possible file. See pinned
[environment binding](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/flag/options.go#L348-L366),
[secret-config default](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/flag/secret_flags.go#L3-L8)
and [empty-path loader](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/fanal/secret/scanner.go#L331-L350).
The vulnerability scan selects HIGH/CRITICAL and the secret scan
explicitly selects all five severities and image-config scanning. Both clear external ignore-policy,
ignore-status, and VEX inputs. The self-contained Python coverage guard then
requires Trivy schema v2, a `container_image` artifact, exact Red Hat 10.2
metadata, exactly one 129-package OS result, and exactly one 134-package Python
result before it accepts the absence of selected findings. The commands preserve separate raw scanner stdout/stderr/JSON and native exit
statuses even on rejection. The SAME coverage consumer rechecks the current
exported index/ARM manifest/config/every layer after both producers and binds
each report ImageID/ArtifactID/DiffIDs to that chain. New regular output files
must be created after the producer start; stale, missing, malformed or failed
inputs cannot mean zero. Genuine native file/config canaries still must prove
actual finding inventories and intended rejection; synthetic test shapes are
not those observations. A successful probe then appends the final admission
receipt; a failed producer or consumer cannot write an all-zero admission.

The admitted UBI image reported Red Hat 10.2 with 129 OS packages and 136
packages in one Python dependency manifest. The unfiltered OS-and-language scan
reported zero HIGH/CRITICAL findings with ambient Trivy configuration disabled,
all external suppression inputs explicitly empty, `/dev/null` as the ignore
file, and unfixed findings included. The strict Apple 1.1.0 probe passed every
required network, mount, digest, cleanup, and non-root control for the same
digest. The sanitized build, runtime, scanner, and probe receipts are recorded
in
`docs/security/EXPERIMENT_RUNNER_CONTAINER_CVE_REMEDIATION.md`. Run the final
immutable-oracle review only after material freeze and do not edit tracked
material afterward. A failed inspection, digest check, checksum, scan, or
probe blocks oracle execution; do not weaken the package, network, or
suppression policy to force admission.

Rollback this candidate only by preserving any failed UBI admission evidence,
deleting the candidate image by its exact digest, and reverting the UBI
base/package/CPython patch pin plus its image-specific tests and evidence
documentation. The fail-closed OCI layer, isolated Trivy invocation, and Trivy
coverage guards must remain in the admission path; a guard regression keeps the
runner blocked and requires a fix-forward. The runner result contract and
capability schema are unchanged.
Neither the failed slim-trixie image, incompatible Alpine recipe, nor blocked
bookworm baseline becomes a fallback; only a separately and explicitly
admitted immutable runner is eligible, and a mutable tag is never eligible.

# Experiment Runner strict macOS backend

Status: local development evidence only. This backend does not grant PR,
promotion, merge, release, GitHub App, or Slack authority.

## Purpose

The macOS dispatcher preserves the canonical `network_budget=0` contract by
running the existing Linux Experiment Runner in an isolated OCI guest. Backend
selection happens once, before the experiment:

1. Apple `container` on Apple silicon;
2. Docker with `--network none` when the Apple probe is not strict;
3. `capability_mismatch` when neither backend proves the required controls.

There is no mid-run fallback and no retry with a weaker network mode. The
strict dispatcher accepts only packets whose `network_budget` is exactly zero;
a non-zero value produces `capability_mismatch` before any runtime probe.

## Host prerequisites

- Apple silicon and supported macOS for Apple Container 1.1.0;
- official signed Apple package installed;
- `container system start` completed;
- recommended kernel configured when requested by the runtime;
- Docker Desktop is an optional fallback, not a co-required runtime;
- approved private Python proxy is available only during image build.

Do not add `CAP_SYS_ADMIN`, mount a runtime socket, or change
`network_budget` to a non-zero value to make a probe pass.

## Build the immutable runner image

The dedicated image uses the pinned multi-architecture digest for
`python:3.13.13-slim-bookworm`, a locked `runtime-dev` environment, and a
non-root final user. Proxy values enter BuildKit as secrets and are not build
arguments or runtime environment variables.

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
  --backend auto \
  --packet artifacts/orchestration/experiments/packets/<packet>.json \
  --image pulseplate/experiment-runner:mac-local@sha256:<digest> \
  --output <result>.json
```

When an oracle-only review is intended to materially shape the engineering
decision if accepted, pass the complete attribution triple. The reason remains
one literal argv value, including when it contains spaces:

```bash
python3 scripts/orchestration/experiment_runner_dispatch.py run \
  --backend auto \
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
as exact inner-runner argv on Apple Container and Docker; default tuples add no
inner argv. After collection and redaction, the host dispatcher requires an
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

After the experiment starts, any runtime failure remains on the selected
backend and is reported without trying Docker, Apple Container, or a networked
mode. `infra_flake` remains reserved for genuinely transient execution errors.
Loss of `unshare` after a passed preflight is still a non-retryable
`capability_mismatch`.

## Validation and rollback

Before using local evidence in a PR lane, verify image history/config contains
no proxy credential and scan the immutable image with Trivy. A successful run
must show `network_budget=0`, `shared_tree_untouched: true`, populated backend
provenance, and no host path or secret.

Rollback is a revert of the dispatcher, result-contract extension, capability
schema, and dedicated Containerfile, followed by deleting the local OCI image.
The existing direct native Linux Runner path remains unchanged. The strict
dispatcher can report its network capability, but does not admit native Linux
execution until an equivalent read-only filesystem/private-temp containment
contract exists; it returns `filesystem_isolation_unavailable` instead.

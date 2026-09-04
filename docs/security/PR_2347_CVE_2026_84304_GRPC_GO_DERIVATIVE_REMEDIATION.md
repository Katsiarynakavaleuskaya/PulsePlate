# PR #2347 CVE-2026-84304 Go gRPC derivative remediation

## Summary

This document is the single security owner for the bounded
`google.golang.org/grpc` remediation in PR #2347. Caddy and the candidate-only
Prometheus derivative select `v1.83.1`; CVE-2026-16742 remains outside this
PR. The source change does not itself claim a successfully built, scanned,
published, selected, deployed, or activated candidate image.

Stage-1 postcondition remains **`P=false`**. The selected Prometheus runtime is
still the exact official record at `deploy/prometheus/image-manifest.json:1`.
Candidate evidence and a final receipt would not change that selector.

## Current truth

- The official selected Prometheus linux/amd64 image embeds gRPC `v1.83.0`;
  CVE-2026-84304 is fixed in `v1.83.1`.
- Caddy's exact module graph and binary metadata now select `v1.83.1` at
  `frontend/Dockerfile.caddy-spa:21`.
- The subordinate derivative recipe is
  `deploy/prometheus/Containerfile:1`.
- The sole policy and state-machine owner is
  `scripts/ci/prometheus_derivative_candidate.py:1`.
- Private mechanics are isolated in
  `scripts/ci/_prometheus_derivative_transport.py:1`.
- The rejected CD `workflow_dispatch` publisher is not an authority or
  compatibility surface.

## Closed pre-build identity

Before receipt `00-spec`, the controller resolves and binds:

1. the full repository Git HEAD and tree through an absolute resolved Git
   executable;
2. the controller and private transport paths and bytes, plus the exact Python
   interpreter path, bytes, and version;
3. the exact Containerfile path, size, and SHA-256;
4. the unchanged runtime-selector path, size, and SHA-256;
5. the absolute Apple Container executable, bytes, version `1.1.0`, release
   channel, full system/apiserver identity, and commit `5973b9c`; a non-empty
   `CONTAINER_HOST` is rejected rather than inherited;
6. the absolute Trivy executable, bytes, and version `0.74.0`;
7. all three canonical Compose Prometheus consumers, source revision/archive,
   gRPC transition, platform, destination, and the fixed single-write ceiling.

The candidate ID is the SHA-256 of that canonical pre-build specification. It
is not the post-verification publication identity.

## Local verification and authorization tuple

Two isolated Apple Container builds use distinct controller-created private
contexts containing only the verified Containerfile. Before and after each
build, the controller requires and binds a live builder with exactly four CPUs
and 6 GiB memory; an underprovisioned builder is `HOLD` before build execution.
Each exact absolute argv uses linux/amd64, the same resource values, no cache,
plain progress, and a private OCI output. Build, scan, and registry plans
receive a controller-owned private `HOME`/configuration root rather than the
operator's ambient credential context. Trivy uses a fresh private cache, an
explicit empty ignore input, and `--config /dev/null`; ambient VEX,
ignore-policy, ignore-status, and credential environment are not inherited.

The controller—not the transport—accepts and compares:

- OCI manifest, config, platform, and layer digests;
- Prometheus and promtool hashes;
- source archive and installed pnpm executable hashes;
- transformed `go.mod` and `go.sum`;
- module graph digest/count;
- UI file count/bytes/path/content inventories;
- gzip content-tree evidence and EmbedFS hash;
- exact Apple builder image digest and normalized pre/post builder status,
  including four CPUs and 6 GiB memory;
- exact Trivy executable/version/fresh database identity and normalized report
  digest after scanning the validated, privately extracted OCI layout;
- positive OS, `/bin/prometheus`, and `/bin/promtool` package coverage, with
  zero HIGH/CRITICAL findings.

Receipt `30-local-verification` owns the path-independent equality result and
the complete authorization tuple. The tuple binds repository, Git HEAD/tree,
controller, private transport, Python, Containerfile, selector, three Compose
consumers, Apple Container system/builder, OCI, binaries,
source/module/UI/EmbedFS, Trivy, destination, the receipt-chain head entering
30, `single_write_limit=1`, and the derived runtime/deploy observation.

The tuple SHA-256—not the candidate ID—derives the candidate tag and
idempotency key. `show-publication-tuple` reports the tuple, derived reference,
digest/key, and this exact expected line:

`AUTHORIZE_PROMETHEUS_CANDIDATE_PUSH <64-lowercase-hex-tuple-sha256> <derived-candidate-ref>`

## Append-only state machine

The fixed private root is:

`artifacts/security_lab/prometheus_derivative_candidate/v1/<candidate-id>`

Directories are mode `0700`; receipts are mode `0600`, single-link,
canonical JSON, published through kernel atomic no-replace rename, hash-linked,
and valid only as this complete prefix. Staging lives outside the inventoried
candidate directory, so interruption yields either the old prefix or the new
receipt rather than a two-hardlink intermediate:

1. `00-spec`
2. `10-build-one`
3. `20-build-two`
4. `30-local-verification`
5. `40-publication-authorization`
6. `50-write-intent`
7. `60-push-result`
8. `70-remote-verification`
9. `80-final-receipt`

Exact replay performs no receipt rewrite. Divergence, gaps, unknown files,
duplicate JSON keys, unsafe modes, symlinks, hardlinks, changed bindings, or
unsupported observations return `HOLD`.

`authorize` reads exactly one newline-terminated UTF-8 line from stdin and
atomically records receipt 40 only when it equals the tuple-derived line.
`publish-or-reconcile` accepts no confirmation input and requires valid 40.

## Publication boundary

Before 50, the controller may perform only credential-free build/scan
revalidation and anonymous bearer-token tag census. A tag present before
intent is `HOLD`, even when its bytes appear to match.

Only the invocation that atomically creates `50-write-intent` may read the
fixed opaque runtime token and make the controller's one direct call to the
private login/push/logout primitive. The token is stdin-only for login and is
never argv, receipt, log, or error data. Logout runs on every post-login
success, failure, or interruption path. There is no push retry.

An invocation observing an existing 50 performs anonymous reconciliation only:
zero token read, zero login, and zero push. A push process result at 60 is not
remote truth. Receipt 70 requires anonymous remote
manifest/config/platform/layer equality with receipt 30.

Immediately before receipts 50 and 80, the controller recomputes the complete
execution identity, selector, and three Compose bindings. Receipt 80 derives:

- `candidate_selected=false`;
- `runtime_selector_updated=false`;
- `deployment_performed=false`;
- `t0_activated=false`.

## Validation and evidence limits

Behavioral tests live in existing files:

- `tests/test_deploy_contract_scripts.py:365` covers canonical identity,
  immutable receipts, stage semantics, creator dominance, reconciliation,
  credential containment, OCI structure, registry status, and module
  boundaries.
- `tests/test_cd_workflow_production_deploy_gate.py:310` proves the rejected
  CD publisher is absent.
- `tests/test_caddy_deploy_provenance.py:384` keeps the Caddy and subordinate
  Containerfile surface bounded.

Adapter tests are mocked and non-network. Source implementation does not itself
prove a successful Apple build, Trivy scan, anonymous GHCR observation,
registry login, push, or receipt 70. Those claims require their separate
operator-authorized execution and canonical local receipt evidence.

## Rollback

Rollback is a normal revert of the Caddy gRPC selection, subordinate
Containerfile, two Python modules, bounded tests, and these instruction/docs
updates. The selected Prometheus selector and all Compose/deploy consumers are
unchanged, so no runtime rollback action exists for this Stage-1 source change.

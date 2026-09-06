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

- Run `34047493123` on head `cfe313c3a7413b201000d953a4dcd9716df5c4fd`
  completed both build calls and their input/parser/identity checks, then
  stopped at `HOLD:path_independent_build_mismatch` before scanning. This is
  two completed builds, not a reproducible, scanned or admitted candidate.
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

## Operator-authorized execution transfer

The operator explicitly approved moving only candidate build and verification
to GitHub Actions in the existing PR, after the local Apple builder exhausted
disk space during image unpack. That approval did not authorize publication,
Droplet execution, deployment, runtime selection, or `T0`. The separate exact
publication line remains mandatory. A subsequent direct approval permits the
existing controller to contain at most 2400 normally Black-formatted physical
lines; the private transport remains below 1400 and there are still exactly
two Python modules, one already-existing workflow, and no new publication
backend.

The first real cloud attempt for head
`80fb75e29d87aabe7552380077831ae7999ad203`, run `34039556026` / job
`101503713637`, stopped before compilation with `tool_observation_invalid`.
Pinned Buildx 0.37 has no `inspect --format` flag. The collector now bootstraps
with supported `inspect`, then asks `ls --format` for the single exact named
Builder JSON and checks the real node `Version` field, before the unchanged
Docker image/config/resource checks. No text parser, version widening or
profile change is used. [Pinned inspect flags](https://github.com/docker/buildx/blob/v0.37.0/commands/inspect.go#L182),
[canonical JSON formatter](https://github.com/docker/buildx/blob/v0.37.0/commands/ls.go#L206),
[node JSON fields](https://github.com/docker/buildx/blob/v0.37.0/builder/node.go#L197).
The failed run and receipt 00 remain retained, not reset or counted as image
evidence; the corrected material requires a fresh head-bound candidate.

The second cloud attempt, head
`5cf70a19a880082e6baf0bc2f060e31d5a417e6c`, run `34042515054` / job
`101511716740`, passed that observation and failed at
`deploy/prometheus/Containerfile:3`: the pinned official builder manifest
`sha256:cdcb06bf0bc5401d4fbf8a71706bb8f74d69276427a1b368a065af53a254bc7f`
returned `404 MANIFEST_UNKNOWN`. Its receipt 00 is also preserved as failed.

On 2026-09-06, independent registry reads of the official `1.27-base` tag and
the exact replacement digest returned byte-identical manifests:

- Manifest: `sha256:7eeded2a35a4ce199f4e108cf81f1b89b5a0df1366233da673a36f12b436f95b`.
- Config: `sha256:fd24ead1d7b2b586c49bf15d11fcaba118f0f16f9cbe8f182da9c104abbe9a5a`.
- Platform: `linux/amd64`; upstream creation: 2026-09-03.
- Go archive checksum agrees with the official Go download inventory for
  `go1.27.1.linux-amd64.tar.gz`:
  `63d339f0da5ab53635a56f2490a7984dfe12dfcff22ad749f63edaf590168445`.
- The hash-verified system layer records Node `22.23.2-1nodesource1` as
  installed. The hash-verified pnpm layer's actual executable retains
  `e5e29eb103e73729ed4115f0e939fb376386dd0d76db56b12459524041f922a0`.

The bounded repair refreshes only the immutable builder pin, the exact Go
assertion to `1.27.1`, and the controller's recipe hash. Node, pnpm, source,
UI/Go locks, runtime base and all verification/publication gates are unchanged.
Registry metadata and extracted package/executable bytes are input evidence,
not a successful execution or reproducibility result. The real build must
still pass every executable assertion and compare two freshly measured binary
and image identities. [Official builder](https://github.com/prometheus/golang-builder),
[Go 1.27.1 patch release](https://go.dev/doc/devel/release#go1.27.1).

The implementation below is not evidence that a new cloud candidate has been
successfully built or published. Stage-1 `P=false` remains unchanged.

## First-use and subprocess review corrections

Two review findings exposed defects in the existing mechanics, not authority
to expand the candidate lane. First freeze now creates the missing fixed
`artifacts/` root before validating it, at
`scripts/ci/prometheus_derivative_candidate.py:256`. The test fixture no longer
pre-creates that root. Clean/partial/replayed state, every fixed path component,
creation races and unsafe existing modes are exercised without a permission
repair or alternate output root.

The private process primitive at
`scripts/ci/_prometheus_derivative_transport.py:223` now checks its existing
per-stream byte limit during simultaneous output collection and stdin delivery,
instead of buffering an entire command before checking. Real subprocess tests
exercise live stdout/stderr/mixed floods, exact limits, input/output pipe
pressure, EOF, nonzero exits, timeout and isolated-group termination/reaping.
The public plan/result and stable error contracts remain unchanged; no spill
file, provider, generic executor or extra module is introduced. Operational
rules remain in `scripts/AGENTS.md:40`.

The separate dispatch-option finding is **NOT-A-BUG** for the selected API.
The existing request explicitly sends `X-GitHub-Api-Version: 2026-03-10` at
`scripts/ci/prometheus_derivative_candidate.py:1074`. That version returns
HTTP 200 with run identity by default; `return_run_details` belongs to the
older version's opt-in contract. The cited CLI implementation itself notes
the new-version distinction. Exact-header and empty-response/no-retry tests
retain the current request rather than adding an unnecessary compatibility
option. [Current versioned REST contract](https://docs.github.com/en/rest/actions/workflows?apiVersion=2026-03-10#create-a-workflow-dispatch-event),
[older opt-in contract](https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28#create-a-workflow-dispatch-event),
[CLI version distinction](https://github.com/cli/cli/blob/v2.96.0/pkg/cmd/workflow/run/run.go#L306).

These corrections and the request-contract disposition do not supply the
outstanding cloud build, scan, publication or selector evidence.

## Reproducibility export and bounded failure evidence

The failed equality run did not retain differing field values before its
normal temporary-archive cleanup. It cannot establish whether binary, UI or
OCI metadata differed; its receipt 00 remains failed and is not reused.

The pinned upstream compression script uses gzip `-n`, so no gzip-option
change is justified. Pinned BuildKit 0.33.0 separately requires
`rewrite-timestamp=true` to apply `SOURCE_DATE_EPOCH` to image-layer file
timestamps. The existing OCI exporter omitted that option; touching only the
two binaries did not prove normalization of every emitted entry. The common
build path now supplies the documented option for both builds and subsequent
fresh pre-publication verification, while preserving the recipe, sources,
locks, base, resources and full equality predicate.
[Pinned gzip implementation](https://github.com/prometheus/prometheus/blob/09fdfcd2659dd9c816e9e23c992fc161c0091757/scripts/compress_assets.sh#L16),
[pinned BuildKit timestamp contract](https://github.com/moby/buildkit/blob/v0.33.0/docs/build-repro.md#source_date_epoch),
[exporter option](https://github.com/moby/buildkit/blob/v0.33.0/exporter/containerimage/opts.go#L57).

Before the unchanged mismatch HOLD, the controller reports only differing
validated evidence fields, digest values and bounded counts. Layer lists are
represented by count and canonical digest, not dumped; oversized numeric
diagnostics are explicitly marked. Invalid or unknown evidence is rejected
before logging. No scan or success artifact follows a mismatch. This is
stderr diagnostics, not a new receipt or authority surface. The relevant
implementation remains `scripts/ci/prometheus_derivative_candidate.py:567`.

The missing exporter normalization is a supported contract correction, not
proof that timestamps were the sole cause of the observed mismatch. Only a
fresh exact-head run can establish equality and then the unchanged scanner
postcondition. Expected content hashes are not rewritten to accept drift.

## Closed pre-build identity

Before receipt `00-spec`, the controller binds exact repository/head/tree,
controller and private transport bytes, the exact local Python and Git
executables, resolved GitHub CLI, Apple image-publication CLI/system identity,
Containerfile, selector, all three Compose consumers, source/locks, destination,
and the single-write limit. Apple compilation and local Trivy are no longer
requirements of that publication executor. `CONTAINER_HOST` remains forbidden.

The same spec freezes `.github/workflows/build.yml` bytes and one cloud
profile: Ubuntu 24.04, Python 3.13.14, the existing pinned checkout/Python/upload
actions, Buildx 0.37.0, immutable linux/amd64 BuildKit 0.33.0, Trivy 0.74.0,
two isolated no-cache builds, and explicit
`SOURCE_DATE_EPOCH=1788079847`. Expected public binary/archive checksums and
the BuildKit manifest/config digests live in the controller's `CLOUD_PROFILE`.
Remote executable observations are collected during execution, not invented
during freeze.

Primary pinned inputs:

- [Buildx 0.37.0 release](https://github.com/docker/buildx/releases/tag/v0.37.0)
- [BuildKit 0.33.0 release](https://github.com/moby/buildkit/releases/tag/v0.33.0)
- [Trivy 0.74.0 checksums](https://github.com/aquasecurity/trivy/releases/download/v0.74.0/trivy_0.74.0_checksums.txt)

The candidate ID hashes this pre-build spec; it is not the publication tuple.

## Cloud verification and authenticated admission

The existing `build.yml` has one independent read-only
`prometheus-candidate` job. Candidate mode skips the complete ordinary
build/security-scan/publish topology. Manual dispatch defaults to `disabled`;
ordinary manual runs now require explicit `normal` mode and empty candidate
inputs. Push, PR and tag semantics remain unchanged. The rejected CD publisher
stays absent; the existing CD-Test listener still admits only successful
push-to-main builds.

Candidate checkout takes `github.sha` directly; the dispatch head is only an
equality assertion against the run and checked-out Git identity, never the
authority selecting code to execute. This removes the input-driven checkout
reported by CodeQL without changing candidate admission or publication gates.

Python dependencies use the existing canonical
`scripts/ci/install_locked_python_requirements.py:1` installer with the locked
`ci-lite` profile and direct-proxy mode. Only the credential-free repository
variable `PULSEPLATE_PYTHON_INDEX_URL` enters its sanitized `env -i` environment
alongside the private `HOME`, `PATH`, and disabled ambient pip configuration.
URL/floor validation and startup-hook inspection remain owned by that
installer. Proxy failure stops the job; this transfer grants no public-index
fallback, direct package-install bypass, `.netrc`, or private-index secret.

The new `cloud-execute` subcommand does not instantiate the Mac publication
executor or local receipt store. It downloads only checksum-verified public
Buildx/Trivy tools, constructs two isolated builders with no shared build cache,
and verifies their exact BuildKit identity and four-CPU/6-GiB limits before and
after each build. The unchanged recipe retains its source/archive, pnpm, locked
module graph, UI/gzip/EmbedFS and binary checks, Node 2048-MiB heap cap and Go
`GOMAXPROCS=2`/`GOMEMLIMIT=3GiB`/`-p=1` controls. These are not a total-host
memory guarantee. Provenance/SBOM attestations are disabled to retain the
existing single-image OCI recognizer, not to claim signed provenance.

Both OCI archives are parsed and compared in cloud before one candidate
archive is exported alongside two complete build observations, bounded
material/tool/run observations, and the full Trivy report. Trivy scans the
validated extracted OCI layout with a fresh private cache, explicit empty
ignore input, `--config /dev/null`, positive package coverage for OS,
Prometheus and promtool, and zero HIGH/CRITICAL findings. GitHub platform
checkout/artifact authentication exists, but no operator/project/registry/
private-index/deploy secrets enter candidate build/scan plans.

Local `verify-local` retains its name but dispatches this cloud execution once
through the resolved authenticated GitHub CLI. The direct REST dispatch run ID
is required; an uncertain response is `HOLD`, never a blind POST retry.
Admission requires exact repository/head/workflow/run/attempt bindings, the
complete attempt-scoped four-job census, candidate success and ordinary-job
skips, and one non-expired artifact with exact ID/name/digest. Artifact API
metadata does not contain a producer job ID: producer binding is derived from
the frozen sole-uploader workflow, complete job census, name containing
run/attempt/job, and artifact creation within the successful job interval.
This is not cryptographic producer attestation. The echoed spec digest is
correlation only and cannot authenticate its own producer.

The ZIP is streamed to adjacent private local support storage with a bounded
byte count and exact API digest, never buffered as a multi-GiB subprocess
result. Duplicate, extra, traversal, link, encrypted, oversized and truncated
members fail closed. The existing OCI parser remains the only admitted shape
recognizer. Local admission independently compares material, pinned tools,
both build observations, OCI digests and the complete normalized scan report.

Database identity remains SHA-256 of the complete regular, single-link private
`db/trivy.db` consumed by the scanner, capped at 2 GiB. `UpdatedAt` owns
freshness. `DownloadedAt` is local operational metadata, not database identity.
Changed/stale/missing DB evidence is `HOLD`, with no automatic refresh or
reseal. [Trivy DB implementation](https://github.com/aquasecurity/trivy/blob/v0.74.0/pkg/db/db.go).

Receipt `30-local-verification` binds initial authenticated cloud provenance
into the exact publication tuple alongside all stable material/build/scan and
local executor identity. Its SHA-256 derives the candidate tag/idempotency key.
`show-publication-tuple` reports, but cannot authorize, the required line:

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

After valid 40 and before 50, the controller initiates and admits a new cloud
two-build/scan proof. It compares stable content, tools and DB-byte identity
with 30; ephemeral run/job/artifact provenance must be fresh rather than equal.
An old run or a rescan alone is insufficient. Receipt 50 records that fresh
provenance. No local compilation fallback exists.

The verified OCI is then loaded locally only after exact source/candidate tag
absence. Its outer descriptor must bind the expected fully qualified
containerd image name with no Apple name override. JSON image inventory uses
`configuration.name`, not denormalized quiet display strings. The controller
tags the loaded image, saves/reparses exactly linux/amd64, and compares
manifest/config/layers before anonymous destination census and final material
checks. Owned names are cleaned even on post-load failure. A tag present before
intent is `HOLD`, even when its bytes appear to match.

Only the invocation that atomically creates `50-write-intent` may read the
fixed opaque runtime token and make the controller's one direct call to the
private login/push/logout primitive. The token is stdin-only for login and is
never argv, receipt, log, or error data. Logout runs on every post-login
success, failure, or interruption path. There is no push retry.

An invocation observing an existing 50 performs anonymous reconciliation only:
zero cloud build, zero local compilation, zero token read, zero login, and zero
push. A push process result at 60 is not
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
prove a successful cloud build, Trivy scan, anonymous GHCR observation,
registry login, push, or receipt 70. Those claims require their separate
operator-authorized execution and canonical local receipt evidence.

## Rollback

Rollback is a normal revert of the Caddy gRPC selection, subordinate
Containerfile, the existing workflow's candidate-only additions, two Python
modules, bounded tests, and these instruction/docs
updates. The selected Prometheus selector and all Compose/deploy consumers are
unchanged, so no runtime rollback action exists for this Stage-1 source change.

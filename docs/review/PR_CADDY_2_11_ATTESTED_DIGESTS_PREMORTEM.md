# PR-D1 Caddy 2.11.4 Attested Digests Premortem

Mode: `pr-premortem`
Phase: pre-open, actual diff
Decision: `proceed with changes`

## Frame

It is six months from now. The hardened Caddy and attested staging deployment
failed: staging either served an unverified image, stopped deploying after a
server drift, or exposed a route/certificate regression. This premortem works
backward from the actual deploy, workflow, Dockerfile, tests, and runbook diff.

Success means that Caddy reports `v2.11.4` built by Go `1.26.5`, the final image
has no HIGH/CRITICAL Trivy findings without suppressions, CD attests and scans
the exact backend and Caddy digests produced by the same job, and no deployment
can start until the server-local contract is synchronized.

## Most likely failure

The server still contains an older Compose file or deploy script after merge.
The new workflow sends two digest references, but the old server-local script
accepts a tag or ignores the Caddy reference. The early warning is a contract
hash mismatch. Containment is to keep `STAGING_ATTESTED_DIGEST_READY=false`,
synchronize the server-local Compose file, Caddyfile, deploy script, and
Postgres backup helper; create the reviewed root-owned contract marker; and
verify every file against the current commit's SHA-256 hashes. All listed
artifacts must be synchronized before readiness and the no-secret remote
preflight can pass.

Disposition: **FIXED** by the default-false rollout gate, root-owned marker,
current-commit SHA-256 checks, `STAGING_DEPLOY_CONTRACT_VERSION="2"`, and
`--preflight-only` execution before GHCR credentials are transmitted.

## Most dangerous failure

CD verifies one artifact but deploys a mutable or parallel-workflow tag. A tag
is repointed after verification, so the server pulls bytes that were never
covered by the successful provenance, SBOM, or vulnerability result.

Disposition: **FIXED**. Backend and Caddy are built in the same CD job, their
BuildKit digest outputs are validated as distinct lowercase SHA-256 values,
each digest gets provenance plus SBOM attestation and verification, both exact
references are scanned, and only those two `name@sha256` values reach SSH.

## Hidden assumption

Building `github.com/caddyserver/caddy/v2/cmd/caddy@v2.11.4` was assumed to
preserve `caddy version`. The first real build disproved this: the module was
v2.11.4 but the command reported `unknown` without upstream version metadata.

Disposition: **FIXED** with the upstream `CustomVersion=v2.11.4` linker value,
plus independent checks of command version, Go build information, main module
version, standard module parity, and file capability.

## Failure-mode closure

| ID | Failure mode | Early warning | Enforceable closure |
|---|---|---|---|
| PM-01 | Rebuilt binary reports `unknown` or wrong Caddy release | `caddy version` differs from v2.11.4 | Docker build fails unless linker version, Go metadata, and module version match |
| PM-02 | Module comparison false-reds or misses a plugin drift | Official binary prints package columns differently | Compare normalized module-name column; require exact sorted set parity |
| PM-03 | Capability validation cannot execute the binary | `operation not permitted` under `--cap-drop ALL` | Validation adds only `NET_BIND_SERVICE`; runtime file capability remains asserted |
| PM-04 | Server-local deploy contract is stale | Marker, contract version, or one of four reviewed-file hashes differs | Preflight fails before registry token/deploy; gate remains default-false |
| PM-05 | Required staging deploy silently skips incomplete credentials | readiness step emits `skip=1` while required mode is true | Readiness exits non-zero when `STAGING_DEPLOY_REQUIRED=true` |
| PM-06 | Caddy or backend scan is advisory or scans a tag | scan input lacks same-job digest | Both Trivy steps consume validated digest outputs and use exit code 1 |
| PM-07 | A suppression hides the original Caddy findings | ignore input or policy appears | Tests reject ignore inputs; no `.trivyignore` or Rego change is in scope |
| PM-08 | Route/header behavior changes in Caddy 2.11 | Caddy validation or ordering assertion fails | Both Caddyfiles validate; route order and security-header contracts run in CI |
| PM-09 | Image rollback is mistaken for database rollback | migration succeeded before a later edge failure | Pre-migration backup remains mandatory; runbook separates digest rollback from DB restore |
| PM-10 | A newer main run cancels an in-flight stateful deploy | workflow cancellation during backup/migration | Staging concurrency uses `cancel-in-progress: false` |

## Pre-open checklist

- [x] Actual hardened image reports Caddy v2.11.4 and Go 1.26.5.
- [x] Official and rebuilt standard module names match.
- [x] Both current Caddyfiles pass `caddy validate` under the hardened image.
- [x] Synthetic staging Compose renders with two distinct digest references.
- [x] Local Trivy 0.71.2 reports zero HIGH/CRITICAL findings for OS and Go binary.
- [x] Focused deploy/provenance/workflow tests pass.
- [ ] Required narrow repo gates and current-head CI remain outstanding until run/open.

## Revised plan

The original version-pin plan is retained only as a supply-chain input. The
shipping contract is the rebuilt, scanned PulsePlate image plus two same-job
attested deployment digests. The server-local marker/hash preflight and the
default-false activation variable are mandatory prerequisites; merge performs
no live deployment and production rollout remains a separate human decision.

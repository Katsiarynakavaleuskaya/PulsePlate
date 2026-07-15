# PR #2117 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117

Branch: `codex/caddy-2-11-attested-digests`

## Summary

This PR builds a hardened Caddy v2.11.4 binary with Go 1.26.5, upgrades the
runtime `c-ares`, `curl`, and `libcurl` packages, and makes staging consume the
exact backend and Caddy digests produced, attested, verified, and scanned by
the same CD job. It does not deploy or change backend, OpenAPI, client, or
Caddy route behavior.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed
- [x] Codex Security exact-material-head diff scan completed
- [x] `pulseplate-pr-review` completed
- [x] Post-rebase packet role refresh completed
- [x] Bounded supplemental Codex Security delta scan completed
- [x] Current-head `pulseplate-pr-review` completed
- [ ] Current-head CI completed
- [ ] Mandatory review wait-window and strict merge-readiness completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: All CodeRabbit actionables and review-level findings were fixed by the mapped commits; focused Caddy, workflow, deploy, and supply-chain contract tests pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923686 -> bd6116803
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923694 -> bd6116803
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923702 -> bfa216247
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923708 -> 690a8d07d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923714 -> bd6116803
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923719 -> 690a8d07d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923722 -> bd6116803
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4689618115 -> 690a8d07d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4689852435 -> 4f44d1ab1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3576902700 -> 31d7aeb01
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4691892060 -> 31d7aeb01
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3576961278 -> 9d227a08b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4691964978 -> 9d227a08b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3585346559 -> 18f0468ce
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3585346574 -> 18f0468ce
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4701934244 -> 18f0468ce

### Final post-rebase CodeRabbit review

Disposition: FIXED
Commit: 18f0468ce
Evidence: The frontend workflow self-trigger was already present and is now
covered explicitly. Staging Compose/Caddy inputs reject symlinks, the backup
helper rejects group/world-writable modes, each in-container readiness request
has a five-second timeout, and staging attestation verification passes GitHub
context through named environment variables. Focused deploy/attestation tests,
`make validate-changed`, and full pre-commit pass.
Reason: Both inline findings and the bounded actionable items in the review
summary were verified against current code. The duplicated remote marker/hash
block remains intentional: two independent SSH sessions must each recheck the
same server-local state immediately before use, without introducing another
remote helper authority.

## Intermediate Codex Security Review Evidence

- The Codex Security scan for `95325b12f5a664a131ce79543f6a963c06f4de0a..2d4e03b48a2877f6da9e5994e3b3bfc0165cf151` completed with zero reportable findings.
- It identified one operator-only stale-build correctness gap in `scripts/QUICK_FIX_PRODUCTION.sh`; attack-path analysis rejected it as a security finding because no attacker-controlled entrypoint or lower-privileged boundary exists.
- Rebased commit `4f44d1ab1` still closes that bounded correctness gap by
  rebuilding Caddy fail closed and verifying the running Caddy/Go identity
  before the success claim.

This receipt predates the final review-hardening commits and is not used as the
exact-head Codex Security merge gate. A new sealed scan is still required after
the final governance commit.

## Final Codex Security Evidence

Disposition: NOT-A-BUG
Evidence: Codex Security scan `fd6c509c-806d-4aa8-b407-44b68084b82e`
sealed the exact material range
`95325b12f5a664a131ce79543f6a963c06f4de0a..0ff3de9780e8dddeb90baf0c51e2899989182163`
with eight of eight source-like rows closed and zero reportable findings. The
review included the two workflows and hardened Dockerfile in addition to all
five runtime/deploy scripts selected by the deterministic diff worklist.
Reason: No attacker-controlled source crossed the digest, credential, SSH,
environment, database, or edge-runtime controls. Rejected hypotheses required
already root/Docker-equivalent operator authority or described operational
availability behavior without a new lower-privileged attack path. The sealed
report is local-only at the scan workspace path and no live deployment occurred.

### Supplemental Docker Source Review Scan

Disposition: NOT-A-BUG
Evidence: Codex Security scan `5d1ee294-2b0e-4294-850d-005a60691b68`
sealed the exact follow-up range
`3b264f6ac644e9b104eb944b4f29290f0a9fcd7a..dfd91f432d348d9c2b7aaf7780ef129ed6263cc8`
with three of three explicitly seeded JSON, test, and governance rows closed
and zero reportable findings. The immutable SQLite version, authoritative HTTPS
URL, safe filename, and SHA3-256 remained unchanged; the review window moved
from the expired `2026-07-13` date to the bounded `2026-07-28` date after an
independent upstream archive verification.
Reason: The earlier sealed full material scan and this sealed exact-delta scan
together cover all material PR changes through `dfd91f432`. No suppressions,
new permissions, deployment authority, or live rollout were introduced.

### Supplemental Production Environment Guard Scan

Disposition: NOT-A-BUG
Evidence: Codex Security scan `d36b998f-652b-40de-b008-06a421a67728`
sealed the exact follow-up range
`0a05abeb6164e6e92c85fa56247ccf9c808bd6e8..0a3a4325530c2969aa38f288566c497a621e2548`
with two of two script/test worklist rows closed and zero reportable findings.
The review covered Docker Compose normalization for leading whitespace,
optional `export`, whitespace before `=`, tabs, and CRLF; secret redaction;
managed production flag replacement; validation-before-mutation ordering; and
atomic environment replacement.
Reason: QA, bug-hunter, security-auditor, live Compose parser probes, and the
sealed diff scan all confirm that the two review-discovered parser mismatches
are fixed without introducing shell evaluation, secret output, deployment
authority, or a lower-privileged TOCTOU path. No live deployment occurred.

## PulsePlate PR Review Evidence

Disposition: NOT-A-BUG
Evidence: `pulseplate-pr-review` ran against remote head `0ff3de978` with all
three review sources available and no blocking finding. GitHub reports the
actual PR surface as 19 files, 2,293 additions, and 210 deletions; `gh pr diff
2117 --name-only` matches the bounded Caddy/deploy/provenance file inventory.
Reason: The review tool's only advisory was the generic large-diff threshold.
The size is justified by one indivisible producer-to-consumer provenance chain,
deterministic negative/positive deploy tests, and parser-safe governance
evidence. The focused five-file suite, local narrow bundle, container identity,
module parity, Caddyfile validation, Compose rendering, and Trivy checks all
passed. The report's larger 31-file two-dot inventory includes main-only
Experiment Runner changes and is not the GitHub PR changed-file truth.

## Pre-open Role and Premortem Evidence

### Agent Coordinator

Disposition: NOT-A-BUG
Evidence: The coordinator classified the lane as Release/control-plane work
and required the exact ordered pre-open role path recorded in the local packet.
Reason: The hardened artifact and its two-digest consumer form one bounded,
rollback-safe provenance chain without runtime product expansion.

### Architecture Specialist

Disposition: FIXED
Commit: 03c87f9a9
Evidence: CD now creates, attests, verifies, scans, and passes both image
digests from their own build steps; staging Compose and deploy accept the same
two immutable identities.
Reason: The implementation removes the previous producer/consumer identity
split while preserving Caddy topology and persistent volumes.

### Security Auditor

Disposition: FIXED
Commit: 03c87f9a9
Evidence: Required deployments fail closed on contract readiness, credentials,
server marker, input hashes, attestations, scans, and exact canonical digest
shape; no new secret, permission, suppression, or PR deployment authority was
added.
Reason: The bounded controls close both the vulnerable Caddy artifact and
mutable/cross-workflow staging handoff risks.

### Dev Operator

Disposition: FIXED
Commit: 03c87f9a9
Evidence: `scripts/deploy.sh` provides a credential-free preflight, validates
the root-owned migration marker and server-local file hashes before secrets,
then performs the existing backup/migration/readiness sequence with two pulled
digest references.
Reason: Server-local migration is explicit and backup-protected; no live
deployment is performed by this PR.

### QA Engineer Agent

Disposition: FIXED
Commit: 03c87f9a9
Evidence: Focused tests cover exact versions/digests, two-image workflow order,
negative and positive deploy CLI cases, persistent volumes, route topology,
headers, attestations, and scans. Local container evidence validates version,
Go build info, 132-module parity, both Caddyfiles, Compose, and zero
HIGH/CRITICAL findings.
Reason: Deterministic acceptance evidence exists for the complete bounded
change while heavy current-head CI remains a separate pending gate.

### Actual-diff Premortem

Disposition: FIXED
Commit: 03c87f9a9
Evidence: `docs/review/PR_CADDY_2_11_ATTESTED_DIGESTS_PREMORTEM.md` records the
actual diff risks and the implementation contains their required mitigations,
including default-false readiness, marker/hash preflight, same-job digests,
module parity, capability restoration, and no suppression.
Reason: No high-probability/high-impact premortem risk remained unmitigated
before PR open.

## Post-open Role Pass Evidence

### QA Engineer Agent

Disposition: FIXED
Commit: c40bfb8cd
Evidence: `.github/workflows/cd.yml` groups all contract-hash outputs under one
redirect, satisfying Actionlint/ShellCheck SC2129; the canonical mapping uses
the parser-safe no-actionables marker; the PR body now carries trusted-label
backed operator and privileged-scope approvals and accurately describes the
inherited optional-deploy `continue-on-error` policy.
Reason: The post-open QA pass found no further runtime/deploy-contract defect;
all three P1 gate findings and the P2 wording inconsistency were corrected
before the next role pass.

### Bug Hunter

Disposition: FIXED
Commit: 43878b634
Evidence: The credentialed deploy SSH step receives the three expected hashes,
revalidates the root-owned marker, contract version, deploy script, Compose,
and Caddyfile immediately before invoking `deploy.sh`, and a focused regression
test enforces this ordering and identity binding.
Reason: The second SSH session can no longer consume changed server-local files
after only relying on the earlier credential-free preflight result.

### Security Auditor

Disposition: FIXED
Commit: 933d308ff
Evidence: An unconditional policy step makes `STAGING_DEPLOY_REQUIRED=true`
fail unless all three rollout gates are explicitly true, and the staging
healthcheck receives `STAGING_DOMAIN` through a step environment variable
rather than embedding a secret expression in shell source. Focused tests and
Actionlint pass.
Reason: Required deployment can no longer silently skip behind a disabled gate,
and the healthcheck no longer creates a secret-to-shell-source injection seam.

### Final QA Engineer Agent

Disposition: FIXED
Commit: 690a8d07d
Evidence: the premortem now records four reviewed-file hashes, the Docker build
fails unless Go metadata reports Caddy main module v2.11.4, and header assertions
are bound to every active global header block. The focused suite passes.
Reason: All three bounded P2 findings from the review-fix diff were corrected
before the subsequent role passes.

### Final Bug Hunter

Disposition: NOT-A-BUG
Evidence: Exact review range `ca8b4f025..f1cde4cd9`; 95 focused
deploy/provenance/supply-chain tests and `git diff --check` passed, with no
bounded P0-P2 correctness defect found.
Reason: Current-head workflow CI remains authoritative for Actionlint, which was
not available in the local worktree.

### Final Security Auditor

Disposition: NOT-A-BUG
Evidence: Exact review range `ca8b4f025..f1cde4cd9`; no P0-P2 finding across
checkout credential persistence, pinned build inputs, module/version proof,
header scope, attestation/SBOM dependencies, scan ordering, or token guidance.
Reason: The final material diff preserves fail-closed artifact and deployment
identity without adding secret, permission, publish, or deploy authority.

### Current-head Closure QA Engineer Agent

Disposition: NOT-A-BUG
Evidence: Exact material head `b7d08050f`; the five focused Caddy, deploy,
attestation, workflow, and supply-chain suites, shell syntax checks, and
`git diff --check` passed. The final production helper tests prove secret
redaction, readiness failure, exact Caddy/Go identity, same-directory temporary
state, preserved mode, complete pre-rename flags, and no temporary residue.
Reason: No P0-P2 defect remained after the final atomic environment fix.

### Current-head Closure Bug Hunter

Disposition: NOT-A-BUG
Evidence: Exact material head `b7d08050f`; the complete `.env` content is built
in the same-directory metadata-preserving temporary file before the sole atomic
rename, and the focused five-file suite, `bash -n`, and `git diff --check`
passed.
Reason: No remaining P0-P2 correctness defect was found in the full
`origin/main...HEAD` Caddy/deploy/provenance path.

### Current-head Closure Security Auditor

Disposition: FIXED
Commit: 0547227d9
Evidence: Duplicate `.env` diagnostics expose keys only, all production flags
are finalized before the atomic rename, and credential lifecycle, exact distinct
digests, same-job attestations and scans, SSH fingerprint/contract checks,
Caddy runtime identity, modules, capabilities, volumes, routes, headers, and
readiness paths passed the final security audit.
Reason: The P2 secret-output and non-atomic environment replacement findings
were fixed before the definitive security pass.

### Docker Source Review Remediation QA Engineer Agent

Disposition: FIXED
Commit: c45f98eb0
Evidence: Exact range `3b264f6ac..dfd91f432`; the unchanged SQLite 3.53.2
archive URL and SHA3-256 were independently revalidated, the review window is
fourteen days, the complete Docker workflow contract suite passed 18 tests,
and preflight, consistency, and `git diff --check` passed.
Reason: The required Docker build gate exposed a genuinely stale review window;
the bounded remediation renews review ownership without changing source identity
or weakening the loader.

### Docker Source Review Remediation Bug Hunter

Disposition: NOT-A-BUG
Evidence: Exact range `3b264f6ac..dfd91f432`; the loader accepts the review
window through `2026-07-28` and rejects `2026-07-29`, while unsafe hosts,
filenames, and tampered payloads still fail closed.
Reason: No P0-P2 correctness defect remained in the three-file remediation.

### Docker Source Review Remediation Security Auditor

Disposition: NOT-A-BUG
Evidence: Exact range `3b264f6ac..dfd91f432`; SQLite stays at `3530200`, the
HTTPS `sqlite.org` URL and SHA3-256 are unchanged, the review window is bounded,
focused tests passed, and Caddy/Go inputs, Trivy policy, and deployment authority
were untouched.
Reason: The supply-chain control remains fail closed and no suppression or
privileged-boundary expansion was introduced.

### Production Environment Guard QA Engineer Agent

Disposition: FIXED
Commit: 31d7aeb01
Evidence: Exact range `0a05abeb..0a3a43255`; 11 quick-fix tests and 70 bounded
deploy/provenance tests passed. Compose-normalized required-key duplicates fail
before backup, mutation, or Docker operations beyond the read-only version
probe; managed `APP_ENV` and `ALLOW_DEV_API_KEY` variants are removed and
replaced exactly once with canonical secure assignments.
Reason: Both review-discovered P1 parser mismatches are covered by deterministic
positive and negative regression tests.

### Production Environment Guard Bug Hunter

Disposition: NOT-A-BUG
Evidence: Exact range `0a05abeb..0a3a43255`; leading spaces, tabs, optional
`export`, whitespace around `=`, and CRLF were exercised adversarially. Duplicate
values remained redacted, `.env` stayed unchanged on failures, no backup or
deploy operation ran, the atomic replacement preserved mode, and no temporary
file remained.
Reason: No P0-P2 correctness defect remained after the normalized parser and
managed-flag cleanup fixes.

### Production Environment Guard Security Auditor

Disposition: FIXED
Commit: 31d7aeb01
Evidence: Exact range `0a05abeb..0a3a43255`; live Docker Compose probes confirmed
that every accepted space/export/tab/CRLF variant is recognized by the guard.
Diagnostics expose only line number, allowlisted key, and `<redacted>`; no value
is sourced, evaluated, or interpolated into a command.
Reason: The earlier validation/runtime parser split and surviving development
flag path are closed without introducing shell injection, secret disclosure,
or a relevant lower-privileged TOCTOU boundary.

### Post-rebase Curl/Libcurl Remediation

Disposition: FIXED
Commit: 1a85e24cf
Evidence: A refreshed Trivy 0.71.2 database identified four fixed HIGH findings
in inherited Alpine `curl`/`libcurl` 8.19.0-r0. The final stage now requires
`curl>=8.20.0-r0` and `libcurl>=8.20.0-r0`; the rebuilt image reports Caddy
v2.11.4 on Go 1.26.5, preserves 132-module parity and bind capability, validates
both Caddyfiles, and the repeated no-suppression image scan reports zero
HIGH/CRITICAL findings for Alpine and the Go binary. The focused deploy,
attestation, workflow, and Python supply-chain suite plus `make
validate-changed` and `pre-commit run --all-files` pass.
Reason: The refreshed vulnerability database exposed a bounded current-PR
final-image defect. It was remediated without changing Node, Postgres, Python
locks, application behavior, permissions, secrets, or deployment authority.

### Post-rebase Packet Role Refresh

Disposition: FIXED
Commits: `91682df26`, `cdc5d761b`, `c220a1274`
Evidence: The ordered packet roles ran sequentially. QA found no P0-P2 defects.
Bug Hunter identified that the new app could become ready before migration and
that the staging runbook omitted an activation gate; `91682df26` now stops app
and Caddy, runs Alembic in a one-shot container before app start, leaves both
stopped on migration failure, and aligns the runbook. Security Auditor found no
remaining P0-P2 issue. App Store Release Agent identified an unsupported
per-run human-approval claim; `cdc5d761b` documents the actual automatic-main
behavior once all gates are enabled. Marketing Strategist identified an
overbroad automatic-maintenance claim; `c220a1274` restores operator ownership
for host, backup, volume, DNS/TLS, and server-local contract maintenance. Every
finding was re-reviewed by its originating role and received PASS.
Reason: Current-PR defects and messaging overclaims were fixed before security
finalization, without widening deploy authority or changing product behavior.

### Bounded Supplemental Codex Security Delta Scan

Disposition: NOT-A-BUG
Evidence: Scan `896592f6-c277-4a23-91bb-71ee20649406` covered exact range
`1764016a92a6ae1f68b175b5f5d7579452048a85..8455d4856d96407744d93e5995e4b508d01fc9c2`.
Both canonical worklist rows (`scripts/deploy.sh` and supporting
`frontend/Dockerfile.caddy-spa`) received full-file receipts. The sealed report
contains zero reportable findings and complete coverage. This was the single
bounded supplemental scan; no broad restart or repeated plugin iteration ran.
Reason: The package-floor and migration-sequencing delta strengthens existing
controls and introduces no plausible attacker-controlled source-to-sink path.

### Current-head PulsePlate PR Review

Disposition: NOT-A-BUG
Evidence: The repo-native `pulseplate-pr-review` ran after publishing rebased
head `0e587ea1c`. GitHub PR metadata, the local Git diff, and the canonical
fixed-mapping artifact were all available with no source degradation. The
report emitted no correctness, security, architecture, release, or governance
finding. Its only advisory is the deterministic large-diff threshold.
Reason: The PR body contains the operator-approved privileged-scope and
frontend/backend split justifications. The Caddy producer, two-image
attestation/scan chain, and two-digest staging consumer form one fail-closed
provenance contract; splitting them would leave a broken or mutable deployment
state. Targeted role review, focused tests, container validation, no-suppression
Trivy evidence, `make validate-changed`, and full pre-commit provide the
required narrow evidence. The final mapping-only head receives the same
read-only review after publication.

The mandatory role chain and Codex Security material scans are complete.
The final remote-head PulsePlate PR review, current-head CI, review wait window,
discussion disposition checks, and strict authenticated merge-readiness gate
remain pending.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-d1eccd832832.json`
(local-only, gitignored)

- Accepted oracle result with no failure class.
- Shared tree and source diff checks passed.
- Contribution kind `commit_decision`; material commits contain the canonical
  Experiment Runner co-author trailer.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/65070079a095.json`
(local-only, gitignored)

The packet routed mandatory ordered roles and did not execute them implicitly.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: the five focused deploy/provenance/workflow/supply-chain suites after
  every material review fix, including the final atomic-environment regressions.
- PASS: branch-scoped `make validate-changed` after implementation commits.
- PASS: `pre-commit run --all-files` and pre-push hooks.
- PASS: hardened image reports Caddy v2.11.4 and Go 1.26.5, matches 132
  standard modules, and retains the expected bind capability.
- PASS: both Caddyfiles validate; staging Compose renders with two synthetic
  digest references.
- PASS: Trivy 0.71.2 reports zero HIGH/CRITICAL findings for Alpine packages
  and the rebuilt Caddy binary.
- Not run: local `make verify`, per repository machine-budget policy.
- PASS (historical pre-rebase evidence): exact-material-head Codex Security scan
  and PulsePlate PR review.
- PASS: supplemental exact-delta Codex Security scan for the Docker source
  review-window remediation.
- PASS: supplemental exact-delta Codex Security scan for the production
  environment parser and managed-flag remediation.
- PASS: one bounded supplemental Codex Security scan for post-rebase exact
  range `1764016a9..8455d4856`; zero reportable findings, complete coverage,
  and no broad scan restart.
- Pending: current-head GitHub CI and review governance.

## Merge Readiness

Not claimed. Exact-head Codex Security, PulsePlate PR review, bot/thread
dispositions, current-head CI, the wait window, and strict authenticated merge
readiness remain required.

## Deferred / Follow-ups

- Live staging canary and production rollout remain separate operator
  decisions. The current GitHub `staging` environment does not enforce a
  per-run required reviewer; once all three rollout gates are enabled,
  successful `main` pushes may deploy automatically.
- The existing staging TLS fallback seam remains separately tracked.
- Coverage 7.15.1, PyArrow 25, pgvector 0.5, and the BOLA matrix remain separate
  epic lanes.

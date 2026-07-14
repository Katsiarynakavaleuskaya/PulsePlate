# PR #2117 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117

Branch: `codex/caddy-2-11-attested-digests`

## Summary

This PR builds a hardened Caddy v2.11.4 binary with Go 1.26.5, upgrades the
runtime c-ares package, and makes staging consume the exact backend and Caddy
digests produced, attested, verified, and scanned by the same CD job. It does
not deploy or change backend, OpenAPI, client, or Caddy route behavior.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed
- [ ] Codex Security exact-head diff scan completed
- [ ] `pulseplate-pr-review` completed
- [ ] Current-head CI completed
- [ ] Mandatory review wait-window and strict merge-readiness completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: All CodeRabbit actionables and review-level findings were fixed by the mapped commits; focused Caddy, workflow, deploy, and supply-chain contract tests pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923686 -> bb58dab7f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923694 -> bb58dab7f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923702 -> d3a4d893a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923708 -> f1cde4cd9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923714 -> bb58dab7f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923719 -> f1cde4cd9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#discussion_r3574923722 -> bb58dab7f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4689618115 -> f1cde4cd9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117#pullrequestreview-4689852435 -> 7c7414266

## Exact-head Security Review Evidence

- The Codex Security scan for `95325b12f5a664a131ce79543f6a963c06f4de0a..2d4e03b48a2877f6da9e5994e3b3bfc0165cf151` completed with zero reportable findings.
- It identified one operator-only stale-build correctness gap in `scripts/QUICK_FIX_PRODUCTION.sh`; attack-path analysis rejected it as a security finding because no attacker-controlled entrypoint or lower-privileged boundary exists.
- Commit `7c7414266` still closes that bounded correctness gap by rebuilding Caddy fail closed and verifying the running Caddy/Go identity before the success claim.

## Pre-open Role and Premortem Evidence

### Agent Coordinator

Disposition: NOT-A-BUG
Evidence: The coordinator classified the lane as Release/control-plane work
and required the exact ordered pre-open role path recorded in the local packet.
Reason: The hardened artifact and its two-digest consumer form one bounded,
rollback-safe provenance chain without runtime product expansion.

### Architecture Specialist

Disposition: FIXED
Commit: b7e574bfd
Evidence: CD now creates, attests, verifies, scans, and passes both image
digests from their own build steps; staging Compose and deploy accept the same
two immutable identities.
Reason: The implementation removes the previous producer/consumer identity
split while preserving Caddy topology and persistent volumes.

### Security Auditor

Disposition: FIXED
Commit: b7e574bfd
Evidence: Required deployments fail closed on contract readiness, credentials,
server marker, input hashes, attestations, scans, and exact canonical digest
shape; no new secret, permission, suppression, or PR deployment authority was
added.
Reason: The bounded controls close both the vulnerable Caddy artifact and
mutable/cross-workflow staging handoff risks.

### Dev Operator

Disposition: FIXED
Commit: b7e574bfd
Evidence: `scripts/deploy.sh` provides a credential-free preflight, validates
the root-owned migration marker and server-local file hashes before secrets,
then performs the existing backup/migration/readiness sequence with two pulled
digest references.
Reason: Server-local migration is explicit and reversible; no live deployment
is performed by this PR.

### QA Engineer Agent

Disposition: FIXED
Commit: b7e574bfd
Evidence: Focused tests cover exact versions/digests, two-image workflow order,
negative and positive deploy CLI cases, persistent volumes, route topology,
headers, attestations, and scans. Local container evidence validates version,
Go build info, 132-module parity, both Caddyfiles, Compose, and zero
HIGH/CRITICAL findings.
Reason: Deterministic acceptance evidence exists for the complete bounded
change while heavy current-head CI remains a separate pending gate.

### Actual-diff Premortem

Disposition: FIXED
Commit: b7e574bfd
Evidence: `docs/review/PR_CADDY_2_11_ATTESTED_DIGESTS_PREMORTEM.md` records the
actual diff risks and the implementation contains their required mitigations,
including default-false readiness, marker/hash preflight, same-job digests,
module parity, capability restoration, and no suppression.
Reason: No high-probability/high-impact premortem risk remained unmitigated
before PR open.

## Post-open Role Pass Evidence

### QA Engineer Agent

Disposition: FIXED
Commit: 1902cc5c7
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
Commit: 312877b8e
Evidence: The credentialed deploy SSH step receives the three expected hashes,
revalidates the root-owned marker, contract version, deploy script, Compose,
and Caddyfile immediately before invoking `deploy.sh`, and a focused regression
test enforces this ordering and identity binding.
Reason: The second SSH session can no longer consume changed server-local files
after only relying on the earlier credential-free preflight result.

### Security Auditor

Disposition: FIXED
Commit: bed97b521
Evidence: An unconditional policy step makes `STAGING_DEPLOY_REQUIRED=true`
fail unless all three rollout gates are explicitly true, and the staging
healthcheck receives `STAGING_DOMAIN` through a step environment variable
rather than embedding a secret expression in shell source. Focused tests and
Actionlint pass.
Reason: Required deployment can no longer silently skip behind a disabled gate,
and the healthcheck no longer creates a secret-to-shell-source injection seam.

### Final QA Engineer Agent

Disposition: FIXED
Commit: f1cde4cd9
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

The remaining mandatory Codex Security and PulsePlate PR review passes are
pending.

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
- PASS: focused deploy/provenance/workflow/supply-chain suites after every
  material review fix; the final bug-hunter subset contains 95 tests.
- PASS: branch-scoped `make validate-changed` after implementation commits.
- PASS: `pre-commit run --all-files` and pre-push hooks.
- PASS: hardened image reports Caddy v2.11.4 and Go 1.26.5, matches 132
  standard modules, and retains the expected bind capability.
- PASS: both Caddyfiles validate; staging Compose renders with two synthetic
  digest references.
- PASS: Trivy 0.71.2 reports zero HIGH/CRITICAL findings for Alpine packages
  and the rebuilt Caddy binary.
- Not run: local `make verify`, per repository machine-budget policy.
- Pending: current-head GitHub CI and review governance.

## Merge Readiness

Not claimed. Post-open roles, Codex Security, PulsePlate PR review, bot/thread
dispositions, current-head CI, the wait window, and strict authenticated merge
readiness remain required.

## Deferred / Follow-ups

- Live staging canary and production rollout require separate human approval.
- The existing staging TLS fallback seam remains separately tracked.
- Coverage 7.15.1, PyArrow 25, pgvector 0.5, and the BOLA matrix remain separate
  epic lanes.

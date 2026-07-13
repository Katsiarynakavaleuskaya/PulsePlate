# PR #2117 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2117

Branch: `codex/caddy-2-11-attested-digests`

## Summary

This PR builds a hardened Caddy v2.11.4 binary with Go 1.26.5, upgrades the
runtime c-ares package, and makes staging consume the exact backend and Caddy
digests produced, attested, verified, and scanned by the same CD job. It does
not deploy or change backend, OpenAPI, client, or Caddy route behavior.

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass completed
- [ ] Codex Security exact-head diff scan completed
- [ ] `pulseplate-pr-review` completed
- [ ] Current-head CI completed
- [ ] Mandatory review wait-window and strict merge-readiness completed

## Fixed in Commit Mapping

- No actionable review comments

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

The remaining mandatory post-open roles are pending.

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
- PASS: 187 focused deploy/provenance/workflow/supply-chain tests.
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

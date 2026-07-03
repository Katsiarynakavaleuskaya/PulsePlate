# PR #2067 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067

Branch: `codex/harden-privileged-surface-review-routing`

## Summary

This PR centralizes privileged-surface review matching in
`scripts/orchestration/bootstrap_sync_policy.py` and makes bootstrap, skill
routing, docs, and tests consume that shared contract.

## Scope

- Privileged prefixes and exact/root-style manifest patterns.
- Shared matcher for `task_bootstrap.py` security review and `skill_router.py`
  security skill reasons.
- Agent-facing docs and deterministic parity tests.
- Backlog closeout for the privileged workflow security-review requirement.

## Out Of Scope

No product runtime, OpenAPI, route registration, Docker remediation behavior,
BOLA, dependency upgrades, or GitHub workflow edits are included.

## Implementation Commit

- `b09ea4d9d` - centralizes the privileged-surface matcher, keeps
  `security-auditor` executable for matched surfaces, adds slash-boundary
  negative tests, and syncs agent-facing docs.
- `100b1ac42` - fixes post-open QA findings by adding deploy Compose/Caddy
  Dockerfile and Dependabot `.yaml` privileged surfaces, making glob matching
  segment-aware for all patterns, and restoring canonical mapping syntax.
- `6d3a83a54` - fixes the second post-open QA/control-surface review by adding
  bounded devcontainer, deploy Caddy, GitHub governance, npm, and iOS Gemfile
  manifest coverage with positive and nested/lookalike negative tests.
- `21e64df95` - addresses AGENTS review comments by reducing the root/runbook
  sync note to a policy pointer while preserving the shared-matcher and
  executable `security-auditor` invariants.
- `849c06cf1` - fixes the post-open bug-hunter finding by adding bounded root
  CI/security/deploy helper-script and root quality-gate config coverage.
- `95b04a9d` - fixes the post-open security-auditor SwiftPM finding by adding
  iOS SwiftPM manifest coverage with positive and nested negative tests.
- `e36f556e6` - fixes the second post-open security-auditor pass by adding
  bounded root security/gate/governance control surfaces and reopening the
  backlog item until PR merge or explicit closeout.
- `9e4ce2fa2` - fixes the third post-open security-auditor pass by adding
  bounded review-bot, MCP control-plane, secret-baseline, policy-guard-test,
  and Cloudflare edge deploy control surfaces.
- `c76ab28de` - fixes live review findings by adding bounded coverage for
  canonical role definitions, Node runtime baseline, frontend Caddy build
  context, Xcode SwiftPM and iOS privacy manifests, and live deploy/backup
  shell entrypoints.
- `3ff73044a` - fixes the coordinator premortem risk that the Xcode project
  package-reference file could bypass privileged review routing even though it
  can carry SwiftPM dependency references.
- `067ff4dca` - normalizes bounded dot-segment
  paths before privileged matching and adds coverage-governance files
  `.coveragerc` / `codecov.*` to the privileged matcher.
- `7005eb031` - fixes the latest review-control findings by adding bounded
  privileged coverage for yamllint config, submodule metadata, repo-local hook
  scripts, Python/Ruby toolchain pins, and the CI environment validation helper.
- `b6fa2dbae` - fixes the latest agent/control-plane review findings by adding
  bounded privileged coverage for GitHub helper scripts, scoped AGENTS files,
  authz contract tests, skill installer/source surfaces, cybersecurity skill
  bundle content, and Cursor control-plane configs.
- `3f39887e5` - fixes the latest lab/release/scanner findings by adding bounded
  privileged coverage for METATRON lab compose/guard files, iOS entitlement and
  release plist/string controls, the AgentGuard scanner, and backup systemd
  unit examples.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/7e4027b0a5dc.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/harden-privileged-surface-review-routing`
- Pre-open role order executed:
  `agent-coordinator -> security-auditor -> qa-engineer-agent -> bug-hunter ->
  cursor-specialist-agent -> architecture-specialist`

## Premortem Closure

Disposition: FIXED
Reason: Root-style glob semantics could have made the new matcher both too
broad and too narrow, so the production-risk closure needed executable matcher
logic and negative tests rather than documentation-only wording.
Evidence: `scripts/orchestration/bootstrap_sync_policy.py` now prevents
root-style manifest globs from crossing `/`, and
`tests/test_bootstrap_sync_policy.py` plus `tests/test_skill_router.py` cover
nested/lookalike negative controls.

Disposition: FIXED
Reason: Agent-facing docs are part of the routing contract; if they drift from
the executable matcher, future agents can route privileged changes differently
from bootstrap.
Evidence: `AGENTS.md`, `RUNBOOK_AGENT.md`,
`docs/orchestration/AGENT_ROUTING_GRAPH.md`, and
`docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` now point agent-facing
guidance at the shared matcher; `tests/test_skill_router.py` locks the
AGENTS/RUNBOOK sync note.

Disposition: FIXED
Commit: 067ff4dca
Reason: Current-head Codex Security file review found that bounded dot-segment
candidate paths such as `docs/../.github/workflows/ci.yml` could bypass the
standalone matcher even though they resolve to a privileged surface. The fix
must be executable, not documentation-only, because skill routing consumes the
matcher before adding `privileged-surface:*` reasons.
Evidence: `scripts/orchestration/bootstrap_sync_policy.py` now normalizes POSIX
dot segments before prefix/pattern matching. `tests/test_bootstrap_sync_policy.py`
and `tests/test_skill_router.py` cover bounded dot-segment positives, while
`tests/test_task_bootstrap.py` asserts parent-traversal candidate paths fail
closed before packet construction.

Disposition: FIXED
Commit: 067ff4dca
Reason: Current-head Codex Security file review found `.coveragerc` and
`codecov.*` are coverage-governance controls that can affect local/CI coverage
truth and should not route as ordinary config when this PR is explicitly
centralizing privileged review surfaces.
Evidence: `scripts/orchestration/bootstrap_sync_policy.py` now covers
`.coveragerc`, `codecov.yml`, and `codecov.yaml`; focused bootstrap,
skill-router, and task-bootstrap tests cover positive root paths and nested
lookalike negatives.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-b1cddccd9543.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-b1cddccd9543.json`
- Runner mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Oracles: focused pytest, ruff check, and `git diff --check`
- Contribution: material oracle review for PR-open/commit decision; commit
  includes `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Superseded local infra attempt:
  `artifacts/orchestration/experiments/results/exp-9a5a64cf0a45.json`
  rejected before oracle execution because this macOS host lacks Linux
  `unshare` for network-disabled sandboxing.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2067`.
- [x] Initial PR open: no GitHub review comments were resolved before mapping.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit actionable review comments checked and dispositioned after bot
  review completes.
- [x] Sourcery actionable review comments checked and dispositioned after bot
  review completes.
- [x] Cubic actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#pullrequestreview-4621382055 -> 21e64df95
Disposition: FIXED
Commit: 21e64df95
Reason: The Sourcery review contained one actionable typo/clarity finding on root privileged-surface wording; the root note now avoids the duplicate matcher list and points to the canonical workflows/actions policy.
Evidence: `AGENTS.md` points to `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`, and the inline Sourcery discussion URL is mapped below with the same commit proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#pullrequestreview-4621396806 -> 21e64df95
Disposition: FIXED
Commit: 21e64df95
Reason: The CodeRabbit review contained one actionable root-AGENTS duplication finding; the fix reduced the root note to a scoped policy pointer rather than a second matcher list.
Evidence: `AGENTS.md` and `RUNBOOK_AGENT.md` now keep only the shared matcher pointer plus executable `security-auditor` invariant, and the inline CodeRabbit discussion URL is mapped below with the same commit proof.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516291986 -> 21e64df95
Disposition: FIXED
Commit: 21e64df95
Reason: Sourcery correctly noted that the root AGENTS wording said `workflow/actions` while the actual GitHub surfaces are `.github/workflows/**` and `.github/actions/**`; the root note now avoids the duplicate list and uses `workflows/actions` in the canonical policy pointer.
Evidence: `AGENTS.md` now points to `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` for the canonical workflows/actions matched-surface list.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516306795 -> 21e64df95
Disposition: FIXED
Commit: 21e64df95
Reason: CodeRabbit was right that root `AGENTS.md` should not duplicate the full matcher list because the canonical list already lives in the scoped policy and duplication would create another drift surface.
Evidence: `AGENTS.md` and `RUNBOOK_AGENT.md` now keep only the shared matcher pointer plus the `security-auditor` executable invariant.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516308979 -> 100b1ac42
Disposition: FIXED
Commit: 100b1ac42
Reason: Production deploy Compose files are privileged deploy controls named by `deploy/AGENTS.md`, so a docs/release task touching them must not bypass `security_review_required` or the executable security reviewer.
Evidence: The matcher covers `deploy/docker-compose.production*.yaml` and `deploy/docker-compose.staging.yaml`; focused bootstrap/skill/task tests cover positive production/staging paths and nested/lookalike negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516308984 -> 100b1ac42
Disposition: FIXED
Commit: 100b1ac42
Reason: Dependabot accepts both `.yml` and `.yaml` config filenames, so covering only `.github/dependabot.yml` left a plausible dependency-automation control bypass.
Evidence: The matcher now includes `.github/dependabot.yaml`, and `tests/test_skill_router.py` asserts stable `privileged-surface:` metadata for that path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516308990 -> 6d3a83a54
Disposition: FIXED
Commit: 6d3a83a54
Reason: The original root-only Dockerfile pattern did not cover repo-owned Dockerfile variants that control production/frontend or devcontainer build surfaces; those are supply-chain control files, not ordinary nested docs.
Evidence: The matcher covers `frontend/Dockerfile.caddy-spa` and `.devcontainer/Dockerfile`, while negative tests keep unrelated nested Dockerfile lookalikes non-privileged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516412113 -> 6d3a83a54
Disposition: FIXED
Commit: 6d3a83a54
Reason: `deploy/Caddyfile` and `deploy/Caddyfile.production` control production proxy/routing behavior, so they belong in the privileged deploy surface rather than only the Compose subset.
Evidence: The matcher now includes `deploy/Caddyfile*`, with positive tests for both deploy Caddyfiles and a nested Caddyfile negative control.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516412116 -> 6d3a83a54
Disposition: FIXED
Commit: 6d3a83a54
Reason: Devcontainer Docker/Compose/devcontainer config forwards package-proxy and build-environment controls, so changes there can affect the developer supply-chain path and should route through security review.
Evidence: The matcher covers `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, and `.devcontainer/docker-compose*.yml` / `.yaml`; tests cover matched devcontainer paths and nested negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516412120 -> 6d3a83a54
Disposition: FIXED
Commit: 6d3a83a54
Reason: The initial manifest list was Python-only, but this repo also has npm and iOS dependency-lock surfaces that can carry supply-chain remediation or dependency submission behavior.
Evidence: The matcher covers root/frontend `package*.json` and `ios/Gemfile*`, with task-bootstrap and skill-router tests proving they force the privileged security-review path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516412122 -> 6d3a83a54
Disposition: FIXED
Commit: 6d3a83a54
Reason: `.github/CODEOWNERS` and `.github/actionlint.yaml` govern review ownership and workflow lint policy, so leaving them outside the matcher would allow governance changes to bypass executable security review.
Evidence: The matcher includes `.github/CODEOWNERS`, `.github/actionlint.yml`, and `.github/actionlint.yaml`; focused tests cover positive and nested lookalike negative cases.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516486804
Disposition: NOT-A-BUG
Reason: This stale-state review comment was based on a transient single-commit head; the mapped SHAs are current PR ancestors on the actual head.
Evidence: `git merge-base --is-ancestor 21e64df95 HEAD`, `100b1ac42`, and `6d3a83a54` returned 0 on the local PR head, and `check_pr_body_phase2_gates --pr-number 2067` passes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516486807
Disposition: NOT-A-BUG
Reason: This stale-state review comment checked a transient head that lacked the Experiment Runner trailer; the actual branch still contains the material Experiment Runner co-author trailer on the implementation commit.
Evidence: `git show -s --format=full b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and the Phase2 gate passes on the current branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516486812 -> 849c06cf1
Disposition: FIXED
Commit: 849c06cf1
Reason: Root quality-gate configs can weaken pre-commit, ruff, pytest, or shared tooling behavior, so they must route through privileged security review.
Evidence: The matcher covers `.pre-commit-config.yaml`, `.pre-commit-config.yml`, and `pyproject.toml`; focused bootstrap, skill-router, and task-bootstrap tests cover positives and lookalike negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3516486816 -> 849c06cf1
Disposition: FIXED
Commit: 849c06cf1
Reason: Workflow-called root CI/security/deploy helper scripts can change gate or deploy behavior while sitting outside `scripts/ci/` and `scripts/release/` directory prefixes.
Evidence: The matcher covers `scripts/ci_*.sh` and `scripts/deploy_*.sh`; focused tests cover `scripts/ci_bandit.sh`, `scripts/ci_pip_audit.sh`, `scripts/deploy_production.sh`, and lookalike negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518035727 -> e36f556e6
Disposition: FIXED
Commit: e36f556e6
Reason: Bandit configuration controls the security-scan exclusion policy, so `.bandit.yaml` and the repo's Makefile-used `.bandit` must not route as ordinary docs or config.
Evidence: The matcher now covers `.bandit` and `.bandit.yaml`; focused bootstrap, skill-router, and task-bootstrap tests prove both paths force privileged security review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518035736 -> e36f556e6
Disposition: FIXED
Commit: e36f556e6
Reason: `scripts/run-backend-tests-pre-commit.sh` and `scripts/hooks/repo_python.sh` decide changed-test selection and repo interpreter resolution for mandatory local gates, so helper-only changes need the same privileged review path as hook config changes.
Evidence: The matcher now covers both helper paths with negative controls for nested lookalikes; focused bootstrap, skill-router, and task-bootstrap tests prove security review is required.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518035740 -> e36f556e6
Disposition: FIXED
Commit: e36f556e6
Reason: Root `AGENTS.md` and `RUNBOOK_AGENT.md` own mandatory gate and reviewer policy, so changing them can weaken merge governance even when no code file changes.
Evidence: The matcher now covers `AGENTS.md` and `RUNBOOK_AGENT.md`; focused bootstrap, skill-router, and task-bootstrap tests prove they keep `security-auditor` executable.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518035746 -> e36f556e6
Disposition: FIXED
Commit: e36f556e6
Reason: `Makefile` owns required local targets such as `validate-changed` and `bandit-full`, so Makefile-only gate changes must not bypass privileged routing.
Evidence: The matcher now covers `Makefile`; focused bootstrap, skill-router, and task-bootstrap tests prove it triggers `security_review_required=true`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518035750 -> e36f556e6
Disposition: FIXED
Commit: e36f556e6
Reason: PR templates shape merge-readiness evidence and reviewer checklists, so root and typed PR-template changes are merge-governance control changes rather than ordinary markdown.
Evidence: The matcher now covers `.github/pull_request_template.md` and `.github/PULL_REQUEST_TEMPLATE/*.md`, with nested-template negative controls and task-bootstrap parity coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518035754 -> e36f556e6
Disposition: FIXED
Commit: e36f556e6
Reason: The backlog item should track PR #2067 as the active target while the PR is still open; closing the checkbox before merge would hide unresolved review/CI disposition work.
Evidence: `docs/roadmap/BACKLOG_LEDGER.md` now leaves the item unchecked and adds a DoD line requiring PR #2067 merge or explicit won't-do closeout before the checkbox is closed.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105300
Disposition: NOT-A-BUG
Reason: This stale-state review comment is anchored to `cd18de8650108aeb6cce48b4b192e687b5cbabd4`, which is not a valid commit in the current PR history; the current branch head contains the mapped fix commits as ancestors.
Evidence: `git cat-file -t cd18de8650108aeb6cce48b4b192e687b5cbabd4` reports an invalid object locally, while `git merge-base --is-ancestor b09ea4d9d HEAD`, `21e64df95`, `100b1ac42`, `6d3a83a54`, `849c06cf1`, `95b04a9d`, `e36f556e6`, and `9e4ce2fa2` return current-branch ancestry for their mapped fixes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105307
Disposition: NOT-A-BUG
Reason: This stale-state attribution comment checks the same non-current `cd18de8650108aeb6cce48b4b192e687b5cbabd4` object; the actual implementation commit that used Experiment Runner evidence is still in the PR history with the required trailer.
Evidence: `git show -s --format=full b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `git merge-base --is-ancestor b09ea4d9d HEAD` returns 0.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518181507
Disposition: NOT-A-BUG
Reason: This stale-state review comment is anchored to `9b2a6cc2e483d5d92977ae7c436a48d5cf3a09f0`, which is not a valid object in the current PR history; remapping valid ancestor fix commits to that invalid object would make the artifact less accurate.
Evidence: `git cat-file -t 9b2a6cc2e483d5d92977ae7c436a48d5cf3a09f0` exits 128 locally, and the current PR head is `99fced9d7e1419c0688fd6ca3700c5bfa4f1bc7f`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518181513
Disposition: NOT-A-BUG
Reason: This stale-state attribution comment checks the same invalid `9b2a6cc2e483d5d92977ae7c436a48d5cf3a09f0` object; the actual implementation commit that used Experiment Runner evidence is still in the current PR history with the required trailer.
Evidence: `git show -s --format=full b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `git merge-base --is-ancestor b09ea4d9d HEAD` returns 0.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105311 -> 9e4ce2fa2
Disposition: FIXED
Commit: 9e4ce2fa2
Reason: CodeRabbit and Sourcery config files control merge-blocking review-bot behavior, so changes to `.coderabbit.yaml` or `.sourcery.yaml` must not route as ordinary config.
Evidence: The matcher now covers `.coderabbit.yaml` and `.sourcery.yaml`; focused bootstrap, skill-router, and task-bootstrap tests prove both paths force privileged security review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105314 -> 9e4ce2fa2
Disposition: FIXED
Commit: 9e4ce2fa2
Reason: `opencode.json` and `mcp-config.json` define governed MCP command/package and env wiring examples, so control-plane tool changes need executable security review.
Evidence: The matcher now covers `opencode.json` and `mcp-config.json`; focused bootstrap, skill-router, and task-bootstrap tests cover both positive paths.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105315 -> 9e4ce2fa2
Disposition: FIXED
Commit: 9e4ce2fa2
Reason: `.secrets.baseline` is the detect-secrets suppression baseline, so baseline-only changes can hide secret fingerprints unless they route through privileged security review.
Evidence: The matcher now covers `.secrets.baseline`; focused bootstrap, skill-router, and task-bootstrap tests prove it sets `security_review_required=true`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105321 -> 9e4ce2fa2
Disposition: FIXED
Commit: 9e4ce2fa2
Reason: Repo policy guard tests enforce nosec/subprocess/sys.modules and other hard-gate rules, so guard-weakening test-only PRs need privileged governance review.
Evidence: The matcher now covers `tests/test_repo_policy_guards.py` and the bounded `tests/guards/` prefix, with negative controls for non-guard test lookalikes and task-bootstrap parity coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518105324 -> 9e4ce2fa2
Disposition: FIXED
Commit: 9e4ce2fa2
Reason: `worker.js`, `wrangler.toml`, and `frontend/wrangler.toml` control first-party Cloudflare proxy/edge deploy behavior, so edge routing changes belong in the privileged deploy surface.
Evidence: The matcher now covers `worker.js`, `wrangler.toml`, and `frontend/wrangler.toml`, with negative controls for nested lookalikes and task-bootstrap parity coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518310113
Disposition: NOT-A-BUG
Reason: The comment asked to remap FIXED proofs to dropped target `81d7bbdd72dd4ba6cae4c68f290081fb0cfd916c`, but that object is not present in the current PR history. Mapping valid fix commits to a non-current object would make the artifact less accurate, not more accurate.
Evidence: `git cat-file -t 81d7bbdd72dd4ba6cae4c68f290081fb0cfd916c` returns missing locally, while the mapped fix commits remain ancestors of the current PR head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518310119
Disposition: NOT-A-BUG
Reason: The attribution comment checked the same dropped `81d7bbdd72dd4ba6cae4c68f290081fb0cfd916c` object. The actual implementation commit that used Experiment Runner evidence is still in the current PR history and carries the required trailer.
Evidence: `git show -s --format=full b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `git merge-base --is-ancestor b09ea4d9d HEAD` returns 0.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518310125 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: Xcode-managed SwiftPM locks are live iOS dependency-control files and are used by CI cache keys, so they must not bypass privileged review routing just because the root `ios/Package.resolved` path is already covered.
Evidence: The matcher now covers `ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved`, with focused bootstrap, skill-router, and task-bootstrap tests proving it requires security review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518310131 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: `scripts/diagnose_web.sh` and `scripts/redeploy_caddy.sh` are bundled into the production deploy path, so helper-only changes can alter production diagnostics/redeploy behavior without matching `scripts/deploy_*.sh`.
Evidence: The matcher now covers both exact helper paths, and focused bootstrap, skill-router, and task-bootstrap tests prove they force the privileged security-review path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518310139 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: `.cursor/agents/**` is the canonical role-definition source reused by native subagent transports, so coordinator/security-auditor instruction changes can weaken review authority and must require executable security review.
Evidence: The matcher now includes the bounded `.cursor/agents/` prefix, with positive and lookalike negative coverage in bootstrap/skill-router tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518310148 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: Root `.nvmrc` pins the Node runtime baseline used by frontend CI and guard tests, so runtime-baseline changes belong with the privileged dependency/tooling control files.
Evidence: The matcher now covers root `.nvmrc`; focused bootstrap, skill-router, and task-bootstrap tests cover the positive path and keep `frontend/.nvmrc` as a negative lookalike.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518426345
Disposition: NOT-A-BUG
Reason: The comment asked to remap FIXED proofs to dropped target `157c228476e75ba45975badb6a3d6e7e3b8b48aa`, but that object is not present in the current PR history. The correct mapping must name commits that actually exist on the current branch and contain each fix.
Evidence: `git cat-file -t 157c228476e75ba45975badb6a3d6e7e3b8b48aa` returns missing locally, while the mapped fix commits are current-branch ancestors.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518426354
Disposition: NOT-A-BUG
Reason: The attribution comment checked the same dropped `157c228476e75ba45975badb6a3d6e7e3b8b48aa` object. The actual implementation commit that used Experiment Runner evidence is still in the current PR history and carries the required trailer.
Evidence: `git show -s --format=full b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `git merge-base --is-ancestor b09ea4d9d HEAD` returns 0.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518426358 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: The workspace SwiftPM manifest is a live Xcode dependency-control file for the iOS workspace, so it belongs in the privileged SwiftPM surface beside the root manifests and Xcode lockfile.
Evidence: The matcher now covers `ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift`, with focused bootstrap, skill-router, and task-bootstrap parity tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518426362 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: `ios/PulsePlate/PrivacyInfo.xcprivacy` is an App Store release readiness and privacy-disclosure gate, so disclosure-affecting changes must not route as ordinary iOS files.
Evidence: The matcher now covers `ios/PulsePlate/PrivacyInfo.xcprivacy`, with focused bootstrap, skill-router, and task-bootstrap tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518426367 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: `frontend/.dockerignore` controls what enters the frontend/Caddy image build context, so it is a deploy/supply-chain control file like `frontend/Dockerfile.caddy-spa`.
Evidence: The matcher now covers `frontend/.dockerignore`; tests cover the positive path and keep `frontend/nested/.dockerignore` as a negative lookalike.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3518426372 -> c76ab28de
Disposition: FIXED
Commit: c76ab28de
Reason: `scripts/deploy.sh` and the ops backup/restore helpers are live deploy and database-safety entrypoints, so they need exact privileged routing instead of relying only on underscore-prefixed deploy helpers.
Evidence: The matcher now covers `scripts/deploy.sh`, `scripts/ops/postgres_backup.sh`, and `scripts/ops/postgres_restore.sh`, with focused bootstrap, skill-router, and task-bootstrap tests.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520300541 -> 7005eb031
Disposition: FIXED
Commit: 7005eb031
Reason: `.yamllint` config controls the repo yamllint hook invoked by pre-commit, so changing it can weaken mandatory YAML lint behavior without touching `.pre-commit-config.yaml`.
Evidence: The matcher now covers root `.yamllint`; focused bootstrap, skill-router, and task-bootstrap tests prove it routes through `security_review_required=true`, and negative tests keep `docs/.yamllint` non-privileged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520300553 -> 7005eb031
Disposition: FIXED
Commit: 7005eb031
Reason: `.gitmodules` controls checked-in submodule source metadata, including the security-skills submodule path used by operator install flows, so submodule URL/path edits must not bypass executable security review.
Evidence: The matcher now covers root `.gitmodules`; focused bootstrap, skill-router, and task-bootstrap tests prove the positive path and keep `docs/.gitmodules` as a nested lookalike negative.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520300561 -> 7005eb031
Disposition: FIXED
Commit: 7005eb031
Reason: Repo-local hook scripts under `.githooks/**` can weaken local push and safety checks even when the pre-commit config is unchanged, so they belong in the privileged local-hook surface.
Evidence: The matcher now covers the bounded `.githooks/` prefix; focused bootstrap, skill-router, and task-bootstrap tests cover `.githooks/pre-push`, while `.githooks-notes/pre-push` remains a negative control.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520300567 -> 7005eb031
Disposition: FIXED
Commit: 7005eb031
Reason: Python/Ruby runtime pin files define local and release toolchain baselines, and this matcher already protected the adjacent Node pin `.nvmrc`; leaving `.python-version`, `.tool-versions`, and `.ruby-version` out created inconsistent toolchain governance.
Evidence: The matcher now covers `.python-version`, `.tool-versions`, and `.ruby-version`; focused bootstrap, skill-router, and task-bootstrap tests prove all three route through privileged review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520300573 -> 7005eb031
Disposition: FIXED
Commit: 7005eb031
Reason: `scripts/validate-ci-environment.sh` is a workflow-called CI/CD environment validation helper, so helper-only edits can weaken deploy-environment validation without matching the existing `scripts/ci/` or `scripts/deploy_*.sh` surfaces.
Evidence: The matcher now covers exact `scripts/validate-ci-environment.sh`; focused bootstrap, skill-router, and task-bootstrap tests prove the positive path and keep `scripts/validate-ci-environment/archive.sh` as a nested negative control.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520535964
Disposition: NOT-A-BUG
Reason: The review comment validates against synthetic target commit `7a1145d18df7c1333947c166af583ec7b066b839`, which is not present in the local or pushed PR branch history. Repo merge-readiness disposition proof is based on real branch commits and commit-after-comment ancestry on the PR head, not on a transient review-only synthetic object.
Evidence: `git cat-file -t 7a1145d18df7c1333947c166af583ec7b066b839` fails locally, while `git merge-base --is-ancestor 21e64df95 HEAD` and `git merge-base --is-ancestor 7005eb031 HEAD` both return 0. The strict disposition guard reports all resolved threads have disposition proof and commit-after-comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520535970
Disposition: NOT-A-BUG
Reason: Experiment Runner attribution is required on commits where Experiment Runner materially contributed. The material oracle evidence shaped the original implementation commit, and that commit carries the required trailer. Later review-fix commits and GitHub synthetic review commits did not use Experiment Runner output as material contribution, so adding the trailer there would be inaccurate.
Evidence: `git show -s --format=%B b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `git merge-base --is-ancestor b09ea4d9d HEAD` returns 0.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520535977 -> b6fa2dbae
Disposition: FIXED
Commit: b6fa2dbae
Reason: GitHub helper scripts under `.github/scripts/**` are workflow-adjacent privileged controls already treated as workflow risk by CI risk profiling, so helper-only changes must not bypass executable security review.
Evidence: The matcher now covers `.github/scripts/`; focused bootstrap, skill-router, and task-bootstrap tests cover `.github/scripts/parse-safety-report.py`, while `.github/script/` and `.github/scripts-notes/` remain negative controls.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520535982 -> b6fa2dbae
Disposition: FIXED
Commit: b6fa2dbae
Reason: Scoped `AGENTS.md` files define mandatory local policy for their subtrees, so scoped policy changes are governance changes rather than ordinary docs.
Evidence: The matcher now supports the bounded `**/AGENTS.md` pattern; focused bootstrap, skill-router, and task-bootstrap tests cover `scripts/AGENTS.md` and `tests/AGENTS.md`, while `AGENTS.md.backup` lookalikes stay non-privileged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520535991 -> b6fa2dbae
Disposition: FIXED
Commit: b6fa2dbae
Reason: `tests/security/_api_authz_contracts.py` is the required auth/tier/ownership route registry, and its static contract test guards that registry; changing either can weaken authorization coverage without touching production routes.
Evidence: The matcher now covers `tests/security/_api_authz_contracts.py` and `tests/security/test_api_authz_contract_static.py`; focused tests cover both positives and nested/lookalike negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520535997 -> b6fa2dbae
Disposition: FIXED
Commit: b6fa2dbae
Reason: `scripts/install_codex_skills.sh` controls official/compat skill installation targets and cybersecurity bundle handling, so installer-only changes can alter agent skill sources or destinations.
Evidence: The matcher now covers exact `scripts/install_codex_skills.sh`; focused tests prove the positive path and keep `scripts/install_codex_skills/archive.sh` non-privileged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520536004 -> b6fa2dbae
Disposition: FIXED
Commit: b6fa2dbae
Reason: Repo skill sources, discovery mirror entries, and the cybersecurity skill bundle are agent behavior/control-plane inputs; skill-only changes can weaken gate, review, or security instructions.
Evidence: The matcher now covers `.agents/skills/`, `tools/codex_skills/`, and `tools/cybersecurity_skills/`; focused bootstrap, skill-router, and task-bootstrap tests cover representative positive paths and lookalike negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520536010 -> b6fa2dbae
Disposition: FIXED
Commit: b6fa2dbae
Reason: Cursor command/rule/MCP example files shape cold-start behavior, security-skill discovery, and local MCP wiring, so they are control-plane surfaces like `.cursor/agents/**`.
Evidence: The matcher now covers `.cursor/commands/`, `.cursor/rules/`, and `.cursor/mcp.json.example`; focused tests cover representative positives and keep `.cursor/command/`, `.cursor/rules-notes/`, and `.cursor/mcp.json` as negative controls.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520884314
Disposition: NOT-A-BUG
Reason: The comment validates FIXED proof against synthetic reviewed commit `a6f61af64cde8d7cd546c601cdc13ecc49e39aa9`, which is not present in the local or pushed PR branch history. Remapping real fix commits to a non-branch object would make the artifact less accurate; repository disposition proof is based on real PR commits that contain the fixes and satisfy commit-after-comment.
Evidence: `git cat-file -t a6f61af64cde8d7cd546c601cdc13ecc49e39aa9` fails locally, while real mapped fix commits are branch commits. The new code-fix commit for current actionable findings is `3f39887e5`, made after this comment.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520884318
Disposition: NOT-A-BUG
Reason: Experiment Runner attribution is required on commits materially shaped by Experiment Runner evidence. That material oracle evidence shaped the original implementation commit, which carries the required trailer; the synthetic reviewed commit `a6f61af64cde8d7cd546c601cdc13ecc49e39aa9` is not a branch commit, and later review-fix commits did not use new Experiment Runner output as material contribution.
Evidence: `git show -s --format=%B b09ea4d9d` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`, and `git merge-base --is-ancestor b09ea4d9d HEAD` returns 0.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520884326 -> 3f39887e5
Disposition: FIXED
Commit: 3f39887e5
Reason: `deploy/metatron-lab/docker-compose.yaml` and `scripts/metatron_lab/compose_guard.py` control the isolated security-lab network and its fixed-path guard, so lab isolation changes must not bypass executable security review.
Evidence: The matcher now covers `deploy/metatron-lab/` and `scripts/metatron_lab/`; focused bootstrap, skill-router, and task-bootstrap tests cover representative positive paths and lookalike negatives such as `deploy/metatron_lab/` and `scripts/metatron_lab_notes/`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520884329 -> 3f39887e5
Disposition: FIXED
Commit: 3f39887e5
Reason: iOS entitlements, release plist, and localized `InfoPlist.strings` files control HealthKit/release permission posture and App Store privacy copy, so they belong with the existing iOS privacy-manifest release controls.
Evidence: The matcher now covers `ios/PulsePlate/PulsePlate.entitlements`, `ios/PulsePlate/Info-Release.plist`, and `ios/PulsePlate/*/InfoPlist.strings`; focused tests cover the positives and nested/archive lookalike negatives.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520884334 -> 3f39887e5
Disposition: FIXED
Commit: 3f39887e5
Reason: `tools/agentguard/scan_text.mjs` is invoked by the local AgentGuard bridge for shared AI-input scanning, so scanner-only changes can weaken prompt-injection or shell-exec detection without touching Python guard code.
Evidence: The matcher now covers `tools/agentguard/`; focused bootstrap, skill-router, and task-bootstrap tests cover `tools/agentguard/scan_text.mjs` and keep `tools/agentguard-notes/scan_text.mjs` non-privileged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2067#discussion_r3520884340 -> 3f39887e5
Disposition: FIXED
Commit: 3f39887e5
Reason: Backup systemd service/timer examples schedule `scripts/ops/postgres_backup.sh` for self-hosted installs, so unit-only changes can alter backup cadence, user, or target without touching the backup helper itself.
Evidence: The matcher now covers `deploy/systemd/pulseplate-postgres-backup.*`; focused tests cover service/timer positives and nested/lookalike negatives such as `deploy/systemd/archive/` and `pulseplate-postgres-backup-notes.md`.

## Role-Agent / Premortem Closeout

- Coordinator finding: Xcode project SwiftPM package references could bypass
  privileged review routing via `ios/PulsePlate.xcodeproj/project.pbxproj`.
Disposition: FIXED
Commit: 3ff73044a
Reason: The project file is a live dependency-control surface for Xcode package
references and CI-visible iOS build state, so it belongs in the same canonical
privileged matcher as the root SwiftPM manifests and Xcode SwiftPM lockfile.
Evidence: `scripts/orchestration/bootstrap_sync_policy.py` now covers
`ios/PulsePlate.xcodeproj/project.pbxproj`; focused bootstrap, skill-router,
and task-bootstrap tests include positive coverage plus an archive-path
negative control.

## Mapping Notes

Future actionable human, bot, role-agent, premortem, Experiment Runner, Codex
Security, or external-review findings must be added with disposition evidence
before merge-readiness claims.

## Post-Open Role Findings

Role: `qa-engineer-agent`

Disposition: FIXED

Commit: `100b1ac42`

Reason: QA identified the same root-cause as the review comments: the canonical
matcher needed to cover repo-owned deploy control files, not just root Compose
globs.

Evidence: Post-open QA found that the privileged matcher missed production
deploy control surfaces named by `deploy/AGENTS.md`. Commit `100b1ac42` adds
`deploy/docker-compose.production*.yaml`, `deploy/docker-compose.staging.yaml`,
and `frontend/Dockerfile.caddy-spa` to the canonical matcher, and focused tests
cover both matched production/staging paths and nested/lookalike negative
controls.

Disposition: FIXED

Commit: `100b1ac42`

Reason: `.github/dependabot.yaml` is an alternate filename for the same
dependency-automation control, so treating it differently from `.yml` would
create a needless bypass.

Evidence: Post-open QA found that `.github/dependabot.yaml` was not covered
beside `.github/dependabot.yml`. Commit `100b1ac42` adds the YAML variant to
the canonical matcher and asserts stable `privileged-surface:` metadata in
`tests/test_skill_router.py`.

Disposition: FIXED

Commit: `100b1ac42`

Reason: The Phase2 gate consumes this artifact mechanically; prose inside the
canonical mapping section creates false governance evidence and must be moved
outside that section.

Evidence: Post-open QA found that this artifact failed Phase2 validation
because `## Fixed in Commit Mapping` mixed prose with non-canonical mapping
lines. Commit `100b1ac42` restores the parser-required checkbox labels and
canonical `- No actionable review comments` line; local validation passed via
`python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 2067`.

Disposition: FIXED

Commit: `6d3a83a54`

Reason: The second QA pass found additional repo-owned privileged control
surfaces under the same matcher-root cause; closing them in code/tests is
stronger than documenting a narrower list as intentional.

Evidence: Commit `6d3a83a54` adds bounded devcontainer, deploy Caddy, GitHub
governance, npm, and iOS Gemfile patterns, and focused bootstrap/skill-router/
task-bootstrap tests cover positive and nested/lookalike negative paths.

Disposition: NOT-A-BUG

Reason: The local `PULSEPLATE_PYTHON_INDEX_URL` warning is operator environment
state, not a repository regression in this PR. The repo canonical URL is already
documented as `https://packages.pulseplate.app/root/pulseplate/+simple/`; the
observed local value was `https://packages.pulseplate.app/root/pypi/+simple/`.

Evidence: `RUNBOOK_AGENT.md` and `docs/DEPENDENCY_MANAGEMENT.md` already point
to the canonical `root/pulseplate/+simple/` URL. No secret or local shell
configuration is committed by this PR.

Role: `bug-hunter`

Disposition: FIXED

Commit: `849c06cf1`

Reason: Bug-hunter correctly found that root workflow-called helper scripts and
root quality-gate configs can weaken CI/security/deploy behavior while sitting
outside the original `scripts/ci/` prefix and manifest patterns.

Evidence: Commit `849c06cf1` adds bounded `.pre-commit-config.y*ml`,
`pyproject.toml`, `scripts/ci_*.sh`, and `scripts/deploy_*.sh` patterns.
Focused bootstrap, skill-router, and task-bootstrap tests cover
`scripts/ci_bandit.sh`, `scripts/ci_pip_audit.sh`, `scripts/deploy_production.sh`,
`.pre-commit-config.yaml`, and `pyproject.toml`, plus lookalike negatives.

Role: `security-auditor`

Disposition: FIXED

Commit: `95b04a9d`

Reason: Security-auditor correctly found that iOS SwiftPM manifests are
dependency supply-chain control files like `ios/Gemfile*`, so they should not
bypass privileged review routing.

Evidence: Commit `95b04a9d` adds `ios/Package.swift` and
`ios/Package.resolved` patterns. Focused bootstrap, skill-router, and
task-bootstrap tests cover both SwiftPM manifest positives and nested
`ios/vendor/Package.resolved` as a negative.

Disposition: FIXED

Commit: `e36f556e6`

Reason: The second security-auditor pass found live review-governance and
gate-control files still outside the canonical matcher; these are credible
fail-open paths because they can alter mandatory gates, reviewer policy, or PR
evidence without touching workflow YAML.

Evidence: Commit `e36f556e6` adds bounded matcher coverage for Bandit config,
root AGENTS/RUNBOOK/Makefile policy entrypoints, PR templates, and backend-test
hook helpers. Focused bootstrap, skill-router, and task-bootstrap tests cover
the new positive paths plus nested/lookalike negative controls, and the backlog
item is reopened until PR merge or explicit closeout.

Disposition: FIXED

Commit: `9e4ce2fa2`

Reason: The third security-auditor pass found additional live control surfaces
that can alter merge-blocking bot review, MCP tool command wiring, secret-scan
suppression, hard-gate guard tests, or Cloudflare edge deploy behavior without
touching workflow YAML.

Evidence: Commit `9e4ce2fa2` adds bounded matcher coverage for `.coderabbit.yaml`,
`.sourcery.yaml`, `.secrets.baseline`, `opencode.json`, `mcp-config.json`,
`tests/test_repo_policy_guards.py`, `tests/guards/**`, `worker.js`,
`wrangler.toml`, and `frontend/wrangler.toml`. Focused bootstrap, skill-router,
and task-bootstrap tests cover the new positives plus nested/lookalike negatives.

Disposition: NOT-A-BUG

Reason: The earlier security-auditor pass checked the then-current PR head and found
that all live review-thread URLs were represented in this mapping, every
`FIXED`/`NOT-A-BUG` block included a `Reason:`, stale-state comments pointed at
invalid or non-current commits, and the code-side matcher/test coverage closed
the then-known privileged-surface routing risks. Later current-head scan findings
are recorded in separate entries above rather than treating this older pass as
current-head proof.

Evidence: Post-open security-auditor PASS on
`cfedd6a4a013e883c0a0aef2c8f0af020ea72773` confirmed zero unmapped live review
thread URLs, `MISSING_REASON: none`, valid mapped ancestor commits for live
fixes, and no new secret/subprocess/nosec/type-ignore/runtime/OpenAPI/BOLA/
route-registration risk in the material diff.

Role: `codex-security`

Disposition: NOT-A-BUG

Reason: The earlier Codex Security diff scan found no reportable candidate for
the then-current material diff. It is historical evidence only; the active
current-head Codex Security scan is tracked separately and must provide the
current-head result after the follow-up matcher fixes are finalized.

Evidence: Scan `f855c09e-b874-45c7-89b1-1bb2bc1efa92` finalized successfully
with 0 findings and complete coverage over 11 changed surfaces. Report:
`/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-mNIoGV/harden-privileged-surface-review-routing/cfedd6a4a013e883c0a0aef2c8f0af020ea72773_20260703T074800Z_8ze5fph6/report.md`.

Role: `codex-security-current-head`

Disposition: FIXED
Commit: 067ff4dca

Reason: Current-head Codex Security scan `bce4adbf-5ab0-4801-b495-256425cf57d4`
found two actionable matcher-governance candidates: bounded dot-segment path
normalization and missing coverage-governance files. Both candidates were
closed by code/tests/docs before scan finalization, so the final report has 0
outstanding findings rather than a bare `not a bug` classification.

Evidence: Scan `bce4adbf-5ab0-4801-b495-256425cf57d4` finalized with 0
outstanding findings after in-scan fixes. Report:
`/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-mNIoGV/harden-privileged-surface-review-routing/86ee4ceb2b9da213261371697165690c5e053c74_20260703T131924Z_pd3xbv2g/report.md`.

Role: `pulseplate-pr-review`

Disposition: NOT-A-BUG

Reason: The dry-run PR review emitted only an advisory `NEEDS-HUMAN` note for
diff size, not a code defect. The larger diff is still one coherent root-cause
slice: one canonical privileged-surface matcher shared by bootstrap, skill
routing, docs, and tests. Splitting after the post-open role fixes would create
more governance churn without reducing the reviewed security risk.

Evidence: `python3 scripts/orchestration/pr_review_context.py --pr 2067
--output /tmp/pulseplate_pr_2067_review_context.json` succeeded, and
`python3 scripts/orchestration/pr_review_report.py --context
/tmp/pulseplate_pr_2067_review_context.json --format json` reported
`findings_count: 1` with severity `note`, category `tests`, disposition
candidate `NEEDS-HUMAN`, and gate `make validate-changed`; `make
validate-changed` already passed on this branch.

## Local Validation Evidence

- `PULSEPLATE_PYTHON_INDEX_URL=https://packages.pulseplate.app/root/pulseplate/+simple/ python3 scripts/orchestration/check_preflight.py`
  passed with canonical private-index shape.
- `python3 scripts/orchestration/check_agent_consistency.py` passed.
- Focused pytest passed with the repo-resolved interpreter:
  `. scripts/hooks/repo_python.sh; VENV_PYTHON="$(resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_bootstrap_sync_policy.py tests/test_task_bootstrap.py tests/test_skill_router.py`.
- Focused ruff passed with the repo-resolved interpreter:
  `. scripts/hooks/repo_python.sh; VENV_PYTHON="$(resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m ruff check scripts/orchestration/bootstrap_sync_policy.py scripts/orchestration/skill_router.py tests/test_bootstrap_sync_policy.py tests/test_task_bootstrap.py tests/test_skill_router.py`.
- Phase2 artifact validation passed after the post-open QA fix:
  `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 2067`.
- `make validate-changed` passed after commit and selected the three changed
  test files.
- `pre-commit run --all-files` passed.
- Push pre-push hooks passed, including mypy changed files, pip-audit, backend
  tests, full-repo bandit, and docker build test.
- Historical Codex Security diff scan finalized with 0 findings for an earlier
  PR head; the current-head scan is recorded separately after finalization.
  Historical report path:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-mNIoGV/harden-privileged-surface-review-routing/cfedd6a4a013e883c0a0aef2c8f0af020ea72773_20260703T074800Z_8ze5fph6/report.md`.
- Current-head Codex Security scan `bce4adbf-5ab0-4801-b495-256425cf57d4`
  finalized with 0 outstanding findings after fixing two matcher-governance
  candidates in code/tests/docs; report path:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-mNIoGV/harden-privileged-surface-review-routing/86ee4ceb2b9da213261371697165690c5e053c74_20260703T131924Z_pd3xbv2g/report.md`.
- `pulseplate-pr-review` dry-run report completed; its only finding was the
  advisory diff-size `NEEDS-HUMAN` note dispositioned above with rationale.

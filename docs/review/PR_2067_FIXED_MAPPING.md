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
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Sourcery actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Cubic actionable review comments checked and dispositioned after bot
  review completes.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

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

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py` passed with the existing
  private-index shape warning only.
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

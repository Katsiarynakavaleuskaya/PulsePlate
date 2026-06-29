# PR #2050 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2050

Branch: `codex/deps-ruff-0-15-20-refresh`

## Summary

This PR supersedes closed Dependabot PR #2019 with a human-owned Ruff
quality-tooling dependency refresh from `0.15.19` to `0.15.20`.

The PR also carries the narrow merge-governance repair discovered during PR
closeout: fallback current-head checks must keep skipped canonical/proxy checks
blocking, but must not block ordinary PR merge readiness on the release-only
Docker `publish` job that is intentionally skipped for `pull_request` events.

## Scope

- `constraints.txt`: raise Ruff floor to `>=0.15.20`.
- `requirements-all.txt`: raise Ruff quality-tooling floor to `>=0.15.20`.
- `requirements-dev.in`: raise direct Ruff dev constraint to `~=0.15.20`.
- `requirements-dev.txt`: lock Ruff to `0.15.20`.
- `requirements-lock.txt`: lock Ruff to `0.15.20`.
- `scripts/ci/check_current_head_pr_checks.py`: keep skipped Docker `publish`
  advisory in fallback mode while preserving skipped canonical/proxy blocking.
- `tests/test_current_head_pr_checks.py`: cover the release-only skipped
  `publish` fallback and preserve blocking semantics for skipped canonical
  checks and failed Docker publish checks.

## Out Of Scope

No `requirements.txt`, runtime dependency, OpenAPI, backend route, web, iOS,
macOS, private-proxy, emergency-wheel, workflow, installer, or pre-commit hook
configuration change is included. `.pre-commit-config.yaml` remains pinned to
`astral-sh/ruff-pre-commit` `v0.14.10` by design for this lane.

The governance repair does not weaken skipped-check handling globally: skipped
canonical CI checks and skipped proxy-gated checks still fail closed.

## Implementation Commits

- `f31e5e642` - bump Ruff quality-tooling dependency surfaces to `0.15.20`.
- `df09f0381` - keep release-only skipped Docker `publish` advisory for
  ordinary PR fallback merge-readiness checks.

## Lane Start Provenance

Base branch: `main`

Branch: `codex/deps-ruff-0-15-20-refresh`

Packet: artifacts/orchestration/task_packets/505b1519b2ff.json

Starter: scripts/orchestration/start_pr_lane.sh

Current `main` CI run `28386708528` completed successfully before edits.

Pre-implementation role order executed:
  `agent-coordinator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent`

Packet creation was routing/provenance only; role passes were executed
  explicitly before implementation.

## Premortem Evidence

Artifact: `artifacts/orchestration/premortem/pr-ruff-0-15-20-replacement-premortem.md`

Decision: `proceed with changes`. The accepted changes are the five-line
Ruff-only diff plus explicit private-proxy/index and local Ruff-version
validation notes.

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/ruff-0-15-20-replacement-oracle-result.json

Packet: `artifacts/orchestration/experiments/artifacts/orchestration/experiments/ruff-0-15-20-replacement-oracle-packet.json`

Status: accepted.

Contribution: `oracle_review`; commit `f31e5e642` includes
`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] CodeRabbit actionable review comments dispositioned.
- [x] Codex Security diff scan / finding discovery completed or explicitly
  dispositioned.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] `pulseplate-pr-review` completed.
- [x] Current-head CI inspected before readiness language.
- [x] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Review Evidence

- PASS: `qa-engineer-agent` post-open pass found no changed-file QA findings.
  Current-head readiness is blocked by infrastructure failures in the GitHub
  `Private Python proxy health` job, not by the Ruff diff.
- PASS: `bug-hunter` post-open pass found no actionable bug and flagged the
  false-green risk that `Merge readiness gate` can pass while upstream CI jobs
  are skipped after private-proxy failure.
- PASS: `security-auditor` post-open pass found no actionable security issue in
  the dependency-only diff.
- PASS: `cursor-specialist-agent` post-open consistency review found no
  workflow/scope issue.
- PASS: `web-research-agent` verified Ruff `0.15.20` availability and found no
  package-vulnerability signal for the requested version.
- PASS: Codex Security diff scan `8f08d653-ae42-442c-bb6a-204f8a1763f6`
  completed with `findingCount=0`.
  Report: `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-8FeNb2/deps-ruff-0-15-20-refresh/679f988d344d524fc6f3d77965a99581530be284_20260629T183911Z_y_ulc81d/report.md`
- PASS: `pulseplate-pr-review` dry-run report found zero deterministic
  findings for PR #2050.
  Context: `/tmp/pulseplate_pr_2050_review_context.json`
  Report: `/tmp/pulseplate_pr_2050_review_report.md`

## External Review / Thread Status

- CodeRabbit status is `SUCCESS`; its walkthrough/pre-merge comment contains no
  actionable code-change request.
- Sourcery submitted a `COMMENTED` review saying the changes look good and
  posted only a reviewer guide; no actionable code-change request.
- Cubic status is advisory/neutral; no actionable thread is present.
- GitHub review-thread GraphQL query returned zero review threads for PR #2050.
- ChatGPT Codex connector posted a usage-limit notice only; no actionable code
  or governance finding.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path constraints.txt --path requirements-all.txt --path requirements-dev.in --path requirements-dev.txt --path requirements-lock.txt`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --path docs/review/PR_2050_FIXED_MAPPING.md --path constraints.txt --path requirements-all.txt --path requirements-dev.in --path requirements-dev.txt --path requirements-lock.txt`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python verify_requirements.py`
- PASS: `python scripts/ci/check_python_dependency_surfaces.py`
- PASS: canonical-index private proxy health for `ruff==0.15.20` in
  `requirements-dev.txt`
- PASS: canonical-index private proxy health for `ruff==0.15.20` in
  `requirements-lock.txt`
- PASS: `python scripts/ci/install_locked_python_requirements.py --requirements-file requirements-dev.txt --constraints-file constraints.txt --install-dev --preflight-only`
- PASS: `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_dependency_security_guard.py tests/guards/test_security_devtooling_regression_guards.py`
- PASS: `python -m pytest -q tests/test_python_dependency_surfaces.py tests/test_verify_requirements.py`
- PASS: `python -m ruff --version` reported `ruff 0.15.20`
- PASS: `python -m ruff check .`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: `git diff --check`
- PASS: no `pip==` unsafe pins in `requirements-dev.txt` or
  `requirements-lock.txt`
- PASS: `python3 scripts/orchestration/pr_review_context.py --pr 2050 --repo Katsiarynakavaleuskaya/PulsePlate --base 71af9d208b26435352fc821b79a2d78cebb319f5 --head 679f988d344d524fc6f3d77965a99581530be284 --repo-root /Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/deps-ruff-0-15-20-refresh --output /tmp/pulseplate_pr_2050_review_context.json`
- PASS: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_2050_review_context.json --format markdown --packet-id 505b1519b2ff --packet-path artifacts/orchestration/task_packets/505b1519b2ff.json --output /tmp/pulseplate_pr_2050_review_report.md`
- PASS: `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" "$VENV_PYTHON" -m pytest -q tests/test_current_head_pr_checks.py tests/test_orchestration_merge_ready.py tests/test_pr_merge_readiness_gate.py`
- PASS: `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" "$VENV_PYTHON" -m ruff check scripts/ci/check_current_head_pr_checks.py tests/test_current_head_pr_checks.py`
- PASS: `GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) python3 scripts/ci/check_current_head_pr_checks.py --pr-number 2050 --repo Katsiarynakavaleuskaya/PulsePlate`
  now reports `publish: skipped [Docker Build and Push]` as advisory and exits
  `0` while retaining failed/pending canonical fallback blocking.
- PASS: `GH_TOKEN=$(gh auth token) GITHUB_TOKEN=$(gh auth token) python3 scripts/orchestration/check_merge_ready.py --pr-number 2050 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
  passed Phase2, review-governance, current-head fallback checks, and
  review-thread disposition after the skipped Docker `publish` fallback repair.
- PASS: `gh pr checks 2050` returned exit 0 after current-head CI settled;
  current-head `lint`, `security`, `test-pr (3.13)`, `diff-coverage`,
  `Private Python proxy health`, `OpenAPI sync`, `PR Body Phase2 gates`,
  `RAG Release Gates Smoke`, `build`, `build-and-test`, `CodeQL`, CodeRabbit,
  and Sourcery were passing. The command still displayed stale superseded
  failures from a cancelled overlapping run.
- PASS: `gh api repos/Katsiarynakavaleuskaya/PulsePlate/actions/jobs/84132972883`
  showed Docker `publish` job conclusion `skipped` with no steps.

## Current Review-State Notes

Local focused validation, post-open role review, Codex Security, and
`pulseplate-pr-review` are complete with no actionable findings. The expanded
governance repair resolves the local strict merge-readiness false block around
release-only skipped Docker `publish`. After the final push, use only the new
current-head CI snapshot plus strict `check_merge_ready.py --require-auth`
evidence for merge.

# PR 1978 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1978>

## Summary

This follow-up lane fixes the post-merge CD fallout from the Docker source
artifact remediation. The CD staging and production image builds now run the
existing verified Docker source artifact fetcher before Buildx, registry auth,
and Docker build/push. The workflow guard now checks `build.yml`, `trivy.yml`,
and `cd.yml` so future root-context Docker builds must prepare source artifacts
first and must keep explicit `context: .`.

No Dockerfile, Trivy policy, GHCR push, private Python index secret, SBOM,
provenance, or attestation semantics are changed.

## Lane Start Provenance

- Branch: `codex/fix-cd-docker-source-artifact-prep`
- Base at PR open: `84f3fa02e15ef61a6847aa5a4c2941d4ac7d957a`
- Initial implementation commit: `0936fbe946c5b522af1cafa3698faf5741fa4607`
- Implementation head before mapping artifact:
  `c27f7a6ee3681702df5e32694f3e8584dd515003`
- Packet: `artifacts/orchestration/task_packets/2ed6a60cee46.json`
- Premortem artifact:
  `artifacts/orchestration/premortem/cd-docker-source-artifact-prep-premortem.md`
- Experiment Runner accepted result:
  `artifacts/orchestration/experiments/results/cd-docker-source-artifact-prep-oracle-result-v2.json`
- Machine-heavy exception: full local `make verify` is intentionally deferred
  under the operator-approved emergency CI/CD scope. Focused local gates and
  current-head CI remain required.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Initial GitHub review/comment scan completed.
- [x] CodeRabbit issue comment `4703324821` is rate-limit metadata, not
  actionable code review feedback. Disposition: NOT-A-BUG.
  Evidence: the comment says CodeRabbit could not start the review due to rate
  limits and lists only selected files.
- [x] Sourcery issue comment `4703325041` is reviewer-guide metadata, not an
  actionable review thread. Disposition: NOT-A-BUG.
  Evidence: the comment summarizes the PR and provides bot usage instructions.
- [x] Post-open role loop completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan and finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [x] GitHub review comments and bot actionables checked for the current head.

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1978#pullrequestreview-4493732314
Disposition: NOT-A-BUG
Evidence: `tests/test_docker_workflow_build_path_contract.py:78` requires Docker build inputs, and `tests/test_docker_workflow_build_path_contract.py:83` through `tests/test_docker_workflow_build_path_contract.py:86` require explicit `context: .`.
Reason: Sourcery's proposed `continue` for missing Docker build inputs would weaken the reviewed fail-closed contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1978#discussion_r3410388443
Disposition: FIXED
Commit: 50a41bced2985f0facad77dd05aba9555d734d98
Evidence: `tests/test_docker_workflow_build_path_contract.py:83` gets `context`; `tests/test_docker_workflow_build_path_contract.py:84` asserts `context == "."`; focused pytest passed with `17 passed`.
Reason: the guard no longer treats missing `with.context` as root path context, so a future switch to Docker Git context fails before CD can regress.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1978#pullrequestreview-4493732314
Disposition: FIXED
Commit: c27f7a6ee3681702df5e32694f3e8584dd515003
Evidence: `tests/test_docker_workflow_build_path_contract.py:19` defines `EXPECTED_DOCKER_SOURCE_PREP_BUILD_STEPS`; `tests/test_docker_workflow_build_path_contract.py:408` asserts that the discovered workflow build steps cover that named contract.
Reason: Sourcery's maintainability suggestion to stop hardcoding the expected workflow tuples inline was implemented.

## Role Dispatch Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: role dispatch manifest from packet
  `artifacts/orchestration/task_packets/2ed6a60cee46.json`
- Pre-open role order completed before PR open:
  `agent-coordinator -> dev-operator -> security-auditor -> qa-engineer-agent -> bug-hunter -> cursor-specialist-agent -> web-research-agent`.
- `agent-coordinator`: accepted narrow CD workflow fallout scope.
- `dev-operator`: confirmed CD staging and production missed Docker source
  artifact preparation.
- `security-auditor`: required no weakening to secrets, SBOM, provenance,
  attestation, or Trivy behavior.
- `qa-engineer-agent`: accepted focused Docker workflow guard coverage.
- `bug-hunter`: required generic coverage across build, Trivy, and CD workflow
  build actions.
- `cursor-specialist-agent`: confirmed prep ordering before Buildx/login/build.
- `web-research-agent`: no external web evidence required for the local CD
  workflow regression.

## Post-Open Role Finding Closure

- `qa-engineer-agent` read-only pass:
Disposition: NOT-A-BUG
Evidence: QA found no implementation blocker after the implementation diff and
identified the missing fixed-mapping/current-head checks as governance
blockers.
Reason: the code path was accepted; mapping and current-head CI remained.

- `bug-hunter` read-only pass:
Disposition: FIXED
Commit: `50a41bced2985f0facad77dd05aba9555d734d98`
Evidence: bug-hunter found the same false-green `context` gap as the Codex
inline review. `tests/test_docker_workflow_build_path_contract.py:83` through
`tests/test_docker_workflow_build_path_contract.py:86` now fail closed on
missing or non-`.` Docker path context.

- `security-auditor` read-only pass:
Disposition: NOT-A-BUG
Evidence: security-auditor confirmed staging prep at `.github/workflows/cd.yml:75`,
production prep at `.github/workflows/cd.yml:468`, registry auth after prep at
`.github/workflows/cd.yml:88` and `.github/workflows/cd.yml:481`, and build/push
after prep at `.github/workflows/cd.yml:95` and `.github/workflows/cd.yml:488`.
Reason: no security/deploy supply-chain blocker remained in the reviewed diff.

- Codex Security diff scan / finding discovery:
Disposition: NOT-A-BUG
Evidence: final-head scan directory
`/tmp/codex-security-scans/fix-cd-docker-source-artifact-prep/c27f7a6ee_20260614T230408Z`
validated `report.md` and rendered `report.html`; final result was 0
reportable findings with 2/2 diff-scoped files reviewed.
Reason: the automatic rank generator produced 0 rows for YAML/test governance
changes, so the scan used an explicit manual diff-file worklist and closed both
files with evidence.

- `pulseplate-pr-review` dry-run:
Disposition: NOT-A-BUG
Evidence: local report generation completed and
`/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_pr_review_report.py`
passed with `9 passed`.
Reason: the review reported the expected missing mapping artifact before this
file was created and did not identify a code blocker.

## Premortem Finding Closure

- `F1` CD misses another Docker build path.
Disposition: FIXED
Commit: `0936fbe946c5b522af1cafa3698faf5741fa4607`
Evidence: `tests/test_docker_workflow_build_path_contract.py:390` iterates
`build.yml`, `trivy.yml`, and `cd.yml`; `tests/test_docker_workflow_build_path_contract.py:408`
asserts expected Docker build coverage.

- `F2` source fetch happens after privileged auth.
Disposition: FIXED
Commit: `0936fbe946c5b522af1cafa3698faf5741fa4607`
Evidence: staging prep runs at `.github/workflows/cd.yml:75` before registry
login at `.github/workflows/cd.yml:88`; production prep runs at
`.github/workflows/cd.yml:468` before registry login at
`.github/workflows/cd.yml:481`.

- `F3` security weakening during hotfix.
Disposition: FIXED
Commit: `0936fbe946c5b522af1cafa3698faf5741fa4607`
Evidence: the diff is limited to `.github/workflows/cd.yml` and
`tests/test_docker_workflow_build_path_contract.py`; Dockerfile, Trivy policy,
secret-envs, SBOM, provenance, and attestation semantics are unchanged.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/cd-docker-source-artifact-prep-oracle-result-v2.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Contribution: `commit_decision`
- Co-author required: true; implementation commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Accepted oracle commands:
  - `git diff --check`
  - `python3 -m py_compile tests/test_docker_workflow_build_path_contract.py`
  - dependency-free CD prep ordering assertion

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_docker_workflow_build_path_contract.py`
  (`17 passed`)
- PASS: `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
- PASS: `PRE_COMMIT_HOME=/tmp/pre-commit-cd-docker-source-artifact-prep pre-commit run --all-files`
- PASS during commit/push hooks: commit hooks, `pip-audit`, backend pre-push
  pytest, full-repo Bandit.
- PASS: Codex Security final-head report validation and HTML rendering:
  `/tmp/codex-security-scans/fix-cd-docker-source-artifact-prep/c27f7a6ee_20260614T230408Z/report.md`
  and
  `/tmp/codex-security-scans/fix-cd-docker-source-artifact-prep/c27f7a6ee_20260614T230408Z/report.html`
- PASS: `pulseplate-pr-review` dry-run tooling and
  `tests/test_pr_review_report.py` (`9 passed`)

## Merge Readiness

Merge readiness is not claimed by this artifact alone. Required remaining proof:

- current-head PR CI for the latest pushed head;
- PR-body Phase2 and mapping guards after this artifact is committed and the PR
  body mirror is refreshed;
- strict merge-readiness wrapper with GitHub auth;
- post-merge `main` CD run, because this PR fixes a push-only CD workflow path.

## Risks / Rollback

- Risk: CD source artifact preparation may still fail at runtime due external
  source availability. Existing manifest/SHA3 verification remains fail-closed.
- Risk: CD itself is push-only, so final runtime proof requires post-merge main
  CD.
- Rollback: revert this PR. It changes workflow ordering and tests only; runtime
  app code and Dockerfile semantics are unchanged.

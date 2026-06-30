# PR #2055 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2055

Branch: `codex/fix-main-docker-trivy-acl-attr`

## Summary

This PR fixes the live `main` Docker Build and Push / publish Trivy image scan
blocker before PR #2054 can merge. It removes base-image `libacl1` and
`libattr1` from the final production image layer through the existing
production-only pruning block, then extends the Docker runtime dependency
surface guard so those packages fail closed if they return.

## Scope

- Add `libacl1` and `libattr1` to final production package pruning.
- Add both packages to the Docker runtime dependency surface guard.
- Keep the Docker Build and Push runtime-surface guard and scheduled `trivy`
  workflow runtime-surface guard aligned.
- Add tests that prevent broad Trivy suppression for the two CVEs/packages.
- Add PR-scoped premortem, Experiment Runner, post-open role-review, Codex
  Security, and fixed-mapping evidence.

## Out Of Scope

No PR #2054 creative-code changes, GitHub App permission changes, broad base
image migration, `.trivyignore` entries, or fail-open Trivy behavior are
included.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/a877862dd62a.json

Post-open packet: artifacts/orchestration/task_packets/8391d9018c5d.json

Closeout packet: artifacts/orchestration/task_packets/acba65b177db.json

Starter: raw Codex session using repo `check_preflight.py` and
`task_bootstrap.py`; no `start_pr_lane.sh` worktree was created because this was
opened as an urgent `main` stabilization branch from the already synced root
checkout.

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/pr2055-docker-trivy-acl-attr-oracle-result-network1.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Experiment ID: `exp-b3113fa85180`
- Shared tree untouched: `true`
- Mutated paths: `[]`
- Contribution kind: `fixed_mapping_review`
- Co-author required: `true`
- Evidence mirror: `docs/review/PR_2055_EXPERIMENT_RUNNER_EVIDENCE.md`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: The scheduled/manual Trivy lane now mirrors the ACL/attr blocklist and the focused workflow test checks both image refs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2055#discussion_r3501752437 -> 3b8089b7c263951c0834a175da771ee189fdee3c

Disposition: FIXED
Commit: 75c4d3eb9bb834523a6fec63cc447565820bc8b9
Evidence: docs/review/PR_2055_PREMORTEM.md records the actual Docker/Trivy diff premortem and closed findings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2055#discussion_r3501792733

Disposition: FIXED
Commit: 75c4d3eb9bb834523a6fec63cc447565820bc8b9
Evidence: docs/review/PR_2055_EXPERIMENT_RUNNER_EVIDENCE.md records the accepted oracle-only runner artifact and commands.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2055#discussion_r3501792740

Disposition: NOT-A-BUG
Evidence: Dockerfile, build.yml, trivy.yml, and tests/test_docker_workflow_build_path_contract.py keep the ACL/attr literals aligned across executable pruning, both workflow guards, and focused tests.
Reason: Sourcery centralization feedback is maintainability guidance; centralizing package lists would broaden this urgent Docker/Trivy hotfix without fixing a current security defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2055#pullrequestreview-4603955142

## Post-Open Review Evidence

- PASS: `qa-engineer-agent` post-open pass found no actionable test gap; it
  correctly kept merge acceptance blocked pending pushed mapping/current-head
  CI.
- PASS: `bug-hunter` post-open pass found no Docker/workflow mismatch after the
  Trivy-lane parity fix and no Trivy suppression bypass. It kept merge blocked
  on mapping, the false no-actionable sentinel, and stale evidence.
- PASS: `security-auditor` post-open pass found no Docker/Trivy security blocker
  in the `c2d9bd45` diff.
- PASS: `architecture-specialist` found no PR #2053/#2054 contamination and no
  need to centralize Docker package literals in this urgent PR.
- PASS: Codex Security scan `3b9010f8-1944-456f-97d5-2933df29534e` completed as
  `branch_diff` with 0 reportable findings and 6/6 diff-scoped surfaces closed.
- PASS: `pulseplate-pr-review` dry-run report returned no deterministic
  findings; all review sources were available.
- Evidence mirror: `docs/review/PR_2055_POST_OPEN_REVIEW_EVIDENCE.md`.

## Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --path Dockerfile --path .github/workflows/build.yml --path tests/test_docker_workflow_build_path_contract.py --path tests/test_trivy_ignore_policy_expiry.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `. .venv/bin/activate && pytest -q tests/test_docker_workflow_build_path_contract.py tests/test_trivy_ignore_policy_expiry.py`
- PASS: `make validate-changed` (selected no Python/cross-surface tests, so the
  focused pytest above is the changed-surface evidence)
- PASS: `pre-commit run --all-files`
- PASS: `python3 scripts/ci/fetch_docker_source_artifacts.py && docker build --platform linux/amd64 --target production --build-arg PULSEPLATE_REQUIREMENTS_FILE=requirements-docker-runtime.txt --secret id=pp_py_index,env=PULSEPLATE_PYTHON_INDEX_URL --secret id=pp_py_host,env=PULSEPLATE_PYTHON_TRUSTED_HOST -t pulseplate:acl-attr-prune-test .`
- PASS: `python3 scripts/ci/check_docker_runtime_dependency_surface.py --image pulseplate:acl-attr-prune-test --blocked-debian-package apt --blocked-debian-package gpgv --blocked-debian-package libacl1 --blocked-debian-package libattr1 --blocked-debian-package libgnutls30 --blocked-debian-package libsqlite3-0 --blocked-debian-package perl-base --blocked-debian-prefix perl-modules- --output-json /tmp/docker-runtime-dependency-surface-acl-attr.json`
- PASS: `docker run --rm -i --platform linux/amd64 --entrypoint python pulseplate:acl-attr-prune-test -` smoke for `ssl`, SQLite 3.53.2, and `/bin/sh`
- PASS: `trivy image --ignore-policy trivy/ignore-policy.rego --severity CRITICAL,HIGH --exit-code 1 --scanners vuln pulseplate:acl-attr-prune-test`

Not run locally:

- Full `make verify`, per repo local machine budget rule.

## Current Review-State Notes

This artifact replaces the stale no-actionable sentinel. Review threads remain
unresolved until the final pushed mapping and strict merge-readiness checks pass.

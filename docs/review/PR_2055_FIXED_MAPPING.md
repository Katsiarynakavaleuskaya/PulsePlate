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

## Out Of Scope

No PR #2054 creative-code changes, GitHub App permission changes, broad base
image migration, `.trivyignore` entries, or fail-open Trivy behavior are
included.

## Lane Start Provenance

Packet: artifacts/orchestration/task_packets/a877862dd62a.json

Post-open packet: artifacts/orchestration/task_packets/8391d9018c5d.json

Starter: raw Codex session using repo `check_preflight.py` and
`task_bootstrap.py`; no `start_pr_lane.sh` worktree was created because this was
opened as an urgent `main` stabilization branch from the already synced root
checkout.

## Experiment Runner Evidence

Not applicable: this is a Docker image security remediation PR; Experiment
Runner did not provide mutation, oracle, admission, or commit-decision evidence.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Review Evidence

- PASS: `qa-engineer-agent` post-open pass found no actionable test gap; it
  correctly kept merge acceptance blocked pending pushed mapping/current-head
  CI.
- FIXED: `bug-hunter` post-open pass found that scheduled/main `trivy.yml`
  runtime-surface guard did not yet block `libacl1`/`libattr1` like
  `build.yml`; fixed by extending the workflow guard and two-workflow test
  assertion in commit `3b8089b7c1c8c73af61d2c0af07d638077ac5911`.
- Pending: `security-auditor` post-open pass.
- Pending: Codex Security diff scan / finding discovery if available.
- Pending: `pulseplate-pr-review`.

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

This artifact records the current no-actionable review mapping state for PR
#2055. If review threads or actionable bot comments appear, this file must be
updated with FIXED, NOT-A-BUG, or DEFERRED disposition evidence before thread
resolution or merge-readiness claims.

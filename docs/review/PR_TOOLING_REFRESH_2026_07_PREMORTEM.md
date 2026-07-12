# PR Tooling Refresh 2026-07 Premortem

Scope: controlled replacement for Dependabot PRs #2103 and #2104, updating
Hypothesis, mypy, Ruff, and the mypy-owned transitive pins in dev/test tooling
surfaces only.

## Summary

It is 48 hours after this tooling refresh merged, and the dependency lane made
CI worse instead of reducing Dependabot noise. The actual diff is small, but it
touches privileged lock surfaces, so the failure modes are resolver drift,
private-proxy gaps, and false confidence from a green narrow test set.

## Most Likely Failure

Disposition: FIXED

Failure story: lock regeneration silently accepts unrelated resolver churn or
the same `pip==...` unsafe pin that made #2103/#2104 unsafe. Reviewers focus on
the three direct dependency names and miss aggregate-lock collapse or public
index leakage.

Underlying assumption: a targeted `pip-compile` command will naturally preserve
the existing aggregate graph.

Early warning signs: `requirements-lock.txt` line count drops sharply, `pip==`
appears in any `requirements*.txt`, or generated headers contain local/index
metadata.

Containment action: stop the lane and regenerate from current `origin/main`
using existing output files as seeds. Do not merge bot-generated lock collapse.

Evidence: `requirements-lock.txt` remains 528 lines, `rg '^pip=='
requirements*.txt` returned no matches, and the generated headers retain the
canonical no-index command shape.

## Most Dangerous Failure

Disposition: FIXED

Failure story: the private package proxy has exact Hypothesis wheels but is
missing a mypy, Ruff, `librt`, or `ast-serialize` artifact. CI health appears
green because the default probe covers test/runtime representatives, but the
dev install fails later in lint/pre-commit or on another runner.

Underlying assumption: the canonical representative proxy check covers every
new dev-tool artifact in this PR.

Early warning signs: `check_private_python_proxy_health.py` passes for
`requirements-test.txt` but `--install-dev` fails, or the Simple API project
page lacks one of the exact new dev pins.

Containment action: add an exact temporary requirements probe for all five Lane
A pins and run the locked dev install before PR open.

Evidence: exact private-proxy probe passed for `hypothesis==6.156.6`,
`mypy==2.2.0`, `ruff==0.15.21`, `librt==0.13.0`, and
`ast-serialize==0.6.0`; the default CI health gate now includes
`requirements-dev.txt` and the same five Lane A pins. The locked dev install
smoke completed successfully.

## Hidden Assumption

Disposition: NOT-A-BUG

Failure story: a reviewer expects `ruff check .` with the newly installed Ruff
to be a PR gate and asks for a broad autofix of unrelated tool fixtures. That
would turn a dependency refresh into a large formatting/lint remediation PR.

Underlying assumption: every locally useful lint command is a merge gate for
this lane.

Evidence: PR CI lint uses `pre-commit run --all-files`, while the full
repository `ruff check .` reports broad unrelated findings in non-product
tooling paths. The plan explicitly forbids Ruff autofix sweeps, and
`pre-commit run --all-files` passed.

## Revised Plan

- Keep the diff to dependency inputs, compiled locks, constraint surfaces, and
  version-sensitive guard tests.
- Preserve runtime, Docker, CI-lite, and application code surfaces unchanged.
- Use exact private-proxy probes for direct and transitive Lane A pins.
- Treat full-repo Ruff findings as out of scope unless current-head PR CI
  exposes a required failure.

## Pre-Merge Checklist

- [x] Coordinator and role-agent passes completed for Lane A scope.
- [x] Private proxy exact pins verified for direct and transitive updates.
- [x] `pip==...` hard stop checked after regeneration.
- [x] Focused supply-chain tests passed.
- [x] `make validate-changed`, `pre-commit run --all-files`, and
  `git diff --check` passed.
- [ ] Current-head GitHub CI and review bots pass after PR open.
- [ ] #2103 and #2104 closed only after the replacement PR exists.

## Decision

Proceed with changes. No premortem finding remains open before PR open; the
remaining unchecked item is current-head CI/review evidence, which can only be
collected after the PR is opened.

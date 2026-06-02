# Dependabot Alert #153 Graph Refresh Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/85771c03a883.json`
Branch: `codex/frontend-dependency-graph-alert-153`

It is 48 hours after merge. The PR landed, but Dependabot alert `#153` stayed
open or reviewers lost confidence because the graph-refresh lane submitted the
wrong manifest path or mixed unrelated ledger governance into the security
workflow fix. This premortem records the failure modes found against the actual
scoped diff before PR open and the post-open closure for review-validated risks.

## Summary

The plan adds frontend npm dependency submission for `/frontend` and documents
`CVE-2026-47429` / `GHSA-5xrq-8626-4rwp` graph drift. Success means GitHub can
ingest `frontend/package-lock.json` truth from `main` while repo docs make clear
that `vitest@4.1.8` is already patched.

## Failure Modes

### PM-153-001: Alert `#153` still does not close after merge

Failure story: The workflow lands, but `NPM Dependency Submission` does not run
for frontend lockfile changes or the frontend snapshot is correlated with the
wrong package root. GitHub dependency graph keeps reporting `vitest@3.2.4`, so
reviewers conclude the repo still depends on vulnerable Vitest even though the
lockfile is already patched.

Underlying assumption: Root npm dependency submission is enough for a nested
frontend lockfile.

Early warning signs: `.github/workflows/npm-dependency-submission.yml` omits
`frontend/package-lock.json` from triggers, the frontend job scans directly from
`filePath: frontend`, or the submitted graph root cannot preserve
`frontend/package-lock.json` as a repo-relative manifest path.

Closure: FIXED. The workflow now triggers on `frontend/package.json` and
`frontend/package-lock.json`, adds a frontend job with
`correlator: npm-dependency-submission-frontend`, prepares a temporary graph
root containing `frontend/package.json` and `frontend/package-lock.json`, and
uses that graph root as the action `filePath` so the submitted manifest path
stays `frontend/package-lock.json`. Guard coverage in
`tests/guards/test_security_devtooling_regression_guards.py` asserts these
properties.

### PM-153-002: The security PR widens dependency or permission scope

Failure story: While trying to close the alert, the PR starts changing
`frontend/package-lock.json`, `dependabot.yml`, Python dependency setup, or
workflow permissions. That creates review noise, private-index drift risk, or
new CI privilege surface unrelated to the stale GitHub graph state.

Underlying assumption: Any dependency-security PR should update all adjacent
dependency tooling.

Early warning signs: The diff touches `frontend/package-lock.json`,
`frontend/package.json`, `.github/dependabot.yml`, requirements files, or adds
permissions beyond `contents: write`.

Closure: FIXED. The diff is limited to the npm submission workflow,
deterministic guards, security/audit docs, and review evidence. No
Python/private-index, package-lock, backend, OpenAPI, Docker, Trivy, frontend
runtime, ledger, or semantic-cache runtime files are changed.

### PM-153-003: The bundled Philosophy PR-5 closeout violates ledger closeout policy

Failure story: The PR tries to close an already-merged Philosophy PR-5 ledger
row in the same branch as the security workflow fix. Reviewers reject the mixed
scope under the backlog ledger policy that completed ledger items require a
separate docs-only closeout PR.

Underlying assumption: A small status-only ledger carryover is harmless inside a
security workflow PR.

Early warning signs: CodeRabbit or repo governance asks to remove the ledger
closeout from the security PR; `AGENTS.md` points to the docs-only closeout
requirement.

Closure: FIXED. The Philosophy PR-5 ledger change and its guard were removed
from PR #1868. The ledger closeout remains a separate docs-only governance
follow-up and is not used as part of the Dependabot alert #153 graph fix.

### PM-153-004: Audit evidence is misread as a full frontend security clean bill

Failure story: Reviewers see `npm audit` output and either miss the Vitest graph
drift or require unrelated moderate transitive fixes in the same PR. The branch
then grows package-lock churn, violating the dependency-graph-only scope.

Underlying assumption: `npm audit --json` must be fully clean for a graph-refresh
workflow PR.

Early warning signs: The PR body claims all frontend audit findings are closed,
or starts remediating unrelated `brace-expansion` / `ws` moderate findings.

Closure: NOT-A-BUG. The focused security signal for this lane is that
`npm audit --audit-level=high --json` reports zero high/critical findings, while
full `npm audit --json` still reports two pre-existing moderate transitive
findings unrelated to Vitest. Those are out of scope because this PR must not
change package manifests or lockfiles.

## Decision

Proceed with changes. All premortem findings are fixed or dispositioned by the
current diff and validation plan. Merge readiness still requires post-open role
passes, Codex Security diff scan / finding discovery, `pulseplate-pr-review`,
current-head CI, fixed mapping, PR-body mirror, and strict merge-readiness gates.

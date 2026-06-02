# Dependabot Alert #153 Graph Refresh Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Packet: `artifacts/orchestration/task_packets/85771c03a883.json`
Branch: `codex/frontend-dependency-graph-alert-153`

It is 48 hours after merge. The PR landed, but Dependabot alert `#153` stayed
open or reviewers lost confidence because the graph-refresh lane mixed a
security workflow fix with a small backlog ledger closeout. This premortem
records the failure modes found against the actual scoped diff before PR open.

## Summary

The plan adds frontend npm dependency submission for `/frontend`, documents
`CVE-2026-47429` / `GHSA-5xrq-8626-4rwp` graph drift, and marks the already
merged Philosophy PR-5 source-corpus ledger row complete. Success means GitHub
can ingest `frontend/package-lock.json` truth from `main` while repo docs make
clear that `vitest@4.1.8` is already patched and semantic-cache/runtime gates
remain closed.

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
`frontend/package-lock.json` from triggers, the frontend job lacks
`filePath: frontend`, or the frontend job excludes `frontend`.

Closure: FIXED. The workflow now triggers on `frontend/package.json` and
`frontend/package-lock.json`, adds a frontend job with
`correlator: npm-dependency-submission-frontend`, and uses `filePath:
frontend`. Guard coverage in
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

Closure: FIXED. The diff is limited to the npm submission workflow, deterministic
guards, security/audit docs, one premortem artifact, and the Philosophy PR-5
ledger row. No Python/private-index, package-lock, backend, OpenAPI, Docker,
Trivy, frontend runtime, or semantic-cache runtime files are changed.

### PM-153-003: The bundled Philosophy PR-5 closeout reopens a closed gate

Failure story: The backlog ledger checkbox is flipped, but the status text drops
the semantic-cache safeguards. A later agent reads the completed row as a signal
that runtime semantic-cache work is now allowed.

Underlying assumption: A docs-only closeout cannot affect runtime governance.

Early warning signs: The row loses `Semantic-cache runtime handoff remains
blocked`, loses `all machine markers stay closed/false`, or no guard checks the
PR #1822 merge evidence.

Closure: FIXED. The ledger row keeps the semantic-cache/runtime blockers and
adds PR #1822 merge evidence (`2026-05-26`,
`740a64fb7d87d404076117698bee5d4bee71f390`). Guard coverage asserts the row is
complete, cites PR #1822, omits stale `Active branch` wording, and preserves the
closed runtime markers.

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

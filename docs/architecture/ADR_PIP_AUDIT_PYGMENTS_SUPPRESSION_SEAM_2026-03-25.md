# ADR: pip-audit Pygments Suppression Seam (2026-03-25)

- Status: Accepted (temporary seam)
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-pygments-pip-audit-ignore`

## Context

`pip-audit` is a blocking pre-push gate in this repository. During PR `#1236`,
the repo baseline on `origin/main` still carried `Pygments==2.19.2` while
`GHSA-5239-wwwm-4pmq` had no patched upstream release available yet.

That created a temporary governance seam:

- the `requests` advisory could be remediated immediately by upgrading to
  `2.33.0`;
- the `Pygments` advisory could not be remediated yet because no safe release
  existed to pin in tracked lock surfaces;
- the pre-push gate still needed to be restored so unrelated narrow PRs were
  not blocked by a no-fix repository baseline.

Implementation anchors:

- `.pre-commit-config.yaml:126`
- `docs/security/GHSA-5239-wwwm-4pmq-pygments.md:1`
- `docs/roadmap/BACKLOG_LEDGER.md:7539`

## Decision

Keep a temporary `pip-audit --ignore-vuln GHSA-5239-wwwm-4pmq` exception in the
pre-push hook until a patched `Pygments` release exists.

This seam is allowed only because all of the following are true:

1. the advisory currently has no patched upstream version available;
2. the exception is scoped to a single GHSA identifier;
3. the exception is documented in repo-tracked security notes;
4. the removal path is tracked in the canonical backlog ledger.

## Exit criteria

Retire this seam only when all are true:

1. a patched `Pygments` release exists for `GHSA-5239-wwwm-4pmq`;
2. tracked dependency surfaces can pin that safe release, including
   `requirements.txt`, `requirements-dev.txt`, and `requirements-lock.txt`;
3. `.pre-commit-config.yaml` no longer carries
   `--ignore-vuln GHSA-5239-wwwm-4pmq`;
4. `pre-commit run --hook-stage pre-push pip-audit --all-files` passes without
   the temporary exception;
5. the linked ledger item is closed with final remediation evidence.

## Consequences

- Positive: repository-wide pre-push security gates remain usable while the
  no-fix advisory is still upstream-blocked.
- Positive: the exception is auditable through a single ADR plus a single ledger
  item.
- Negative: until upstream publishes a fix, the repo accepts a temporary
  advisory-specific suppression seam in local security tooling.

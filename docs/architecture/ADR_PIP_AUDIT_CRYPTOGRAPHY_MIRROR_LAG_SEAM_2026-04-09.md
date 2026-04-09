# ADR: pip-audit cryptography mirror-lag seam (2026-04-09)

- Status: Accepted (temporary seam)
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-bump`

## Context

`pip-audit` is a blocking pre-push gate in this repository. On `9 April 2026`,
the remediation branch for PR `#1379` hit a supply-chain mismatch:

- `pip-audit` flagged `cryptography==46.0.6` for `GHSA-p423-j2cm-9vmq`
  / `CVE-2026-39892`, with fix version `46.0.7`;
- bumping tracked requirement surfaces to `46.0.7` restored the local
  pre-push gate but broke shared CI and Docker locked installs because the
  approved private package proxy did not resolve `46.0.7`.

That produced a governance conflict where the patched version existed upstream,
but the approved internal distribution path lagged behind.

## Decision

Keep a temporary `pip-audit --ignore-vuln GHSA-p423-j2cm-9vmq` exception in the
pre-push hook while tracked pins stay on `cryptography==46.0.6` until the
approved private proxy resolves `46.0.7`.

This seam is allowed only because:

1. the exception is limited to one GHSA identifier;
2. the install-path blocker is documented through shared CI/Docker evidence;
3. the removal path is tracked in repo docs and backlog;
4. the repo remains fail-closed on the approved proxy contract rather than
   bypassing it with public-index installs.

## Exit Criteria

Retire this seam only when:

1. the approved private proxy resolves `cryptography==46.0.7` (or later safe
   version) for shared CI and Docker installs;
2. tracked requirement surfaces are bumped to the safe version;
3. `.pre-commit-config.yaml` no longer carries the ignore;
4. `pre-commit` and canonical CI pass without the temporary exception.

## Consequences

- Positive: PR flow remains usable while the approved mirror catches up.
- Positive: the repo preserves the fail-closed private-proxy contract.
- Negative: a known advisory remains temporarily suppressed in the local
  pre-push gate until mirror sync completes.

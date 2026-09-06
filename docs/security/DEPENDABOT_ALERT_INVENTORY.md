<!-- markdownlint-disable MD013 MD031 MD032 -->

# Dependabot open alert inventory - 2026-09-06

## Snapshot boundary

This is the complete authenticated open-alert census observed at
`2026-09-06T17:45:46Z` using all REST pagination:

```text
GET /repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts
    ?state=open&per_page=100
pagination: --paginate --slurp
```

The census contains exactly one open alert. It is the npm `browserslist` alert
from `frontend/package-lock.json`. No authenticated alert currently projects
`npm:qs`; this provider-projection gap does not override the terminal scanner
and GAD evidence that admitted `qs` into the exact repository batch.

## Authenticated open alerts

| Alert | Ecosystem | Package | Advisory / CVE | Manifest | Current lane |
| --- | --- | --- | --- | --- | --- |
| `#273` | npm | `browserslist` | `GHSA-73wf-gq98-2v4g` / `CVE-2026-73088` | `frontend/package-lock.json` | `codex/frontend-browserslist-cves-2026-73088-73089` |

The alert payload reports development scope, severity HIGH, affected range
`<=4.28.6`, first patched version `4.28.7`, state `open`, and no fixed or
dismissed timestamp. The complete two-identity scanner and Advisory Database
receipt is owned by
`docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:63`. It contains all
three Browserslist records and all ten qs records / twenty-one qs range rows,
including the retained withdrawn `GHSA-crvj-3gj9-gm2p` record.

## Repository remediation versus provider closure

The candidate dependency transaction is owned by
`docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:1`. Its npm-generated
lock resolves `browserslist 4.28.8` at `frontend/package-lock.json:4743` and
`qs 6.16.0` at `frontend/package-lock.json:8938`, while
`frontend/package.json` remains byte-identical. The exact two-target permanent
all-occurrence guard is `tests/test_frontend_dependency_guards.py:1644`.

That candidate repository evidence does not close Dependabot alert `#273` and
does not invent a provider closure event for the not-projected `qs` identity.
GitHub can update the provider state only after merged material is ingested by
the dependency graph. Until a post-merge authenticated lookup returns terminal
provider state, report repository remediation and provider closure separately.

## Closed alert reconciliation

The open census intentionally excludes historical pip alert `#225` for
`msgpack` / `GHSA-6v7p-g79w-8964`. Its separately authenticated exact-alert
lookup was rechecked with the current census and remains:

```text
alert_number=225
ecosystem=pip
package=msgpack
advisory=GHSA-6v7p-g79w-8964
state=fixed
fixed_at=2026-06-22T22:34:21Z
dismissed_at=null
auto_dismissed_at=null
manifest=requirements-ci-lite.txt
```

The corresponding item is closed at
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-msgpack-ci-lite-alert-recheck`.
This is provider-state reconciliation only: no pip dependency material is
changed by the exact frontend npm batch. The existing parity guard at
`tests/test_dependency_security_guard.py:314` binds this historical tuple to
the unchanged ledger. New closed alerts must not replace this evidence.

## Closed RubyGems alert reconciliation

The open census intentionally excludes the now-fixed RubyGems alert `#239` for
`json` / `GHSA-x2f5-4prf-w687`. Its separately authenticated exact-alert lookup
was rechecked with the current census and is:

```text
alert_number=239
ecosystem=rubygems
package=json
advisory=GHSA-x2f5-4prf-w687
state=fixed
fixed_at=2026-08-22T11:43:56Z
dismissed_at=null
auto_dismissed_at=null
manifest=ios/Gemfile.lock
```

This is provider-state reconciliation only: no Ruby dependency material is
changed by the exact frontend npm batch.

## Final pre-closeout open-alert refresh

```text
exit: 0
open_count: 1
alert: 273
package: npm:browserslist
state: open
fixed_at: null
dismissed_at: null
```

## Refresh rule

After merge, repeat the complete authenticated census and perform a separate
exact lookup for alert `#273`. Until exact-main CI, the merged lock, the focused
npm audit, and the provider refresh are each terminally observed, report
`MERGED_PENDING_POST_MERGE_PROOF`; do not translate one signal into another.

<!-- markdownlint-enable MD013 MD031 MD032 -->

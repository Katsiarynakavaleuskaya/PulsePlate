<!-- markdownlint-disable MD013 MD031 MD032 -->

# Dependabot open alert inventory - 2026-09-02

## Snapshot boundary

This is the complete authenticated open-alert census observed at
`2026-09-02T10:19:40Z` using all REST pagination:

```text
GET /repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts
    ?state=open&per_page=100
pagination: --paginate --slurp
```

The census contains exactly one open alert. It is the npm `browserslist` alert
from `frontend/package-lock.json`; no RubyGems or pip alert was open at this
snapshot.

## Authenticated open alerts

| Alert | Ecosystem | Package | Advisory / CVE | Manifest | Current lane |
| --- | --- | --- | --- | --- | --- |
| `#273` | npm | `browserslist` | `GHSA-73wf-gq98-2v4g` / `CVE-2026-73088` | `frontend/package-lock.json` | `codex/frontend-browserslist-cves-2026-73088-73089` |

The alert payload reports development scope, severity HIGH, affected range
`<=4.28.6`, first patched version `4.28.7`, state `open`, and no fixed or
dismissed timestamp. The complete package-wide Advisory Database census is
owned by `docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:63`; it also
contains current `GHSA-c83g-rgw3-j3cx` / `CVE-2026-73089` and historical
`GHSA-w8qv-6jwh-64r5` / `CVE-2021-23364`.

## Repository remediation versus provider closure

The candidate dependency transaction is owned by
`docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:1`. Its npm-generated
lock resolves `browserslist 4.28.8` at `frontend/package-lock.json:4743`, while
`frontend/package.json` remains byte-identical. The permanent all-occurrence
guard is `tests/test_frontend_dependency_guards.py:1572`.

That candidate repository evidence does not close Dependabot alert `#273`.
GitHub can update the provider state only after merged material is ingested by
the dependency graph. Until a post-merge authenticated lookup returns terminal
provider state, report repository remediation and provider closure separately.

## Closed alert reconciliation

The open census intentionally excludes the now-fixed RubyGems alert `#239` for
`json` / `GHSA-x2f5-4prf-w687`. Its separately authenticated exact-alert lookup
is:

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
changed by the Browserslist lane.

## Refresh rule

After merge, repeat the complete authenticated census and perform a separate
exact lookup for alert `#273`. Until exact-main CI, the merged lock, the focused
npm audit, and the provider refresh are each terminally observed, report
`MERGED_PENDING_POST_MERGE_PROOF`; do not translate one signal into another.

<!-- markdownlint-enable MD013 MD031 MD032 -->

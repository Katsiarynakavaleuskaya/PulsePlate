<!-- markdownlint-disable MD013 MD031 MD032 -->

# Dependabot open alert inventory - 2026-08-22

## Snapshot boundary

This is the complete authenticated open-alert census observed at
`2026-08-22T07:49:57Z` using all REST pagination:

```text
GET /repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts
    ?state=open&per_page=100
pagination: --paginate --slurp
```

The census contains exactly one open alert. It is the RubyGems `json` alert
from `ios/Gemfile.lock`; no npm or pip alert was open at this snapshot.

## Authenticated open alerts

| Alert | Ecosystem | Package | Advisory / CVE | Manifest | Current lane |
| --- | --- | --- | --- | --- | --- |
| `#239` | RubyGems | `json` | `GHSA-x2f5-4prf-w687` / `CVE-2026-54696` | `ios/Gemfile.lock` | `codex/ios-ruby-json-security-remediation` |

The alert payload reports severity LOW, affected range `>= 2.9.0, < 2.19.9`,
first patched version `2.19.9`, state `open`, and no fixed, dismissed, or
auto-dismissed timestamp. The CVE alias is independently cross-checked through
the authenticated GitHub Advisory Database endpoint because the repository
alert payload did not populate its advisory `cves` array.

## Repository remediation versus provider closure

The candidate dependency transaction is owned by
`docs/security/CVE-2026-54696-json-fastlane.md` and tracked at
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ruby-json-cve-2026-54696-release-tooling`.
Its Bundler-generated lock resolves `json 2.19.9`, and its all-severity Trivy
0.72.0 filesystem scan reports zero vulnerabilities.
The exact candidate carrier is `ios/Gemfile.lock:176`.

That candidate repository evidence does not close Dependabot alert `#239`.
GitHub can update the provider state only after merged material is ingested by
the dependency graph. Until a post-merge authenticated lookup returns terminal
provider state, report repository remediation and provider closure separately.

## Closed alert reconciliation

The open census intentionally excludes historical pip alert `#225` for
`msgpack` / `GHSA-6v7p-g79w-8964`. Its separately authenticated exact-alert
lookup remains:

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
changed by the Ruby `json` lane.

## Refresh rule

After merge, repeat the complete authenticated census and perform a separate
exact lookup for alert `#239`. Until exact-main CI, the merged lock, the
all-severity scanner result, and the provider refresh are each terminally
observed, report `MERGED_PENDING_POST_MERGE_PROOF`; do not translate one signal
into another.

<!-- markdownlint-enable MD013 MD031 MD032 -->

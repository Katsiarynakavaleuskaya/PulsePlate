<!-- markdownlint-disable MD013 MD031 MD032 -->

# Dependabot open alert inventory — 2026-08-21

## Snapshot boundary

This is the complete authenticated open-alert census observed at
`2026-08-21T06:47:21Z` using all REST pagination:

```text
GET /repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts
    ?state=open&per_page=100
pagination: --paginate --slurp
```

The census contains 13 open alerts: 12 npm alerts from
`frontend/package-lock.json` and one RubyGems alert from `ios/Gemfile.lock`.
The current npm dependency transaction is anchored at
`frontend/package.json:77`; the separate Ruby material is not changed here.

## Authenticated open alerts

| Alert | Ecosystem | Package | Advisory / CVE | Manifest | Current lane |
| --- | --- | --- | --- | --- | --- |
| `#234` | npm | `js-yaml` | `GHSA-52cp-r559-cp3m` / `CVE-2026-59869` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#235` | npm | `dompurify` | `GHSA-c2j3-45gr-mqc4` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#239` | RubyGems | `json` | `GHSA-x2f5-4prf-w687` / `CVE-2026-54696` | `ios/Gemfile.lock` | separate `deps(ios)` release-tooling lane |
| `#240` | npm | `postcss` | `GHSA-r28c-9q8g-f849` / `CVE-2026-73646` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#243` | npm | `style-dictionary` | `GHSA-vj5c-m527-mpff` / `CVE-2026-54639` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#246` | npm | `undici` | `GHSA-8xcm-r25x-g524` / `CVE-2026-16728` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#247` | npm | `undici` | `GHSA-4cwx-7wf7-3272` / `CVE-2026-13697` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#248` | npm | `undici` | `GHSA-jr45-8vmc-qm54` / `CVE-2026-14643` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#249` | npm | `undici` | `GHSA-v3r7-h72x-cjcm` / `CVE-2026-16729` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#250` | npm | `undici` | `GHSA-m8rv-5g2x-5cg5` / `CVE-2026-15157` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#252` | npm | `postcss` | `GHSA-fxqj-rqcc-2cmp` / `CVE-2026-69153` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#263` | npm | `dompurify` | `GHSA-55q2-fjhq-7xh7` | `frontend/package-lock.json` | seven-identity frontend batch |
| `#266` | npm | `js-yaml` | `GHSA-5p4m-2wfm-xmqj` | `frontend/package-lock.json` | seven-identity frontend batch |

## Trivy and Advisory Database-only lag

The immutable all-severity Trivy snapshot also reports:

- `brace-expansion@2.1.3` and `brace-expansion@5.0.8` for
  `GHSA-rgw5-rvv9-x895` / `CVE-2026-69152`;
- `nanoid@3.3.17` for `GHSA-2v37-7h3g-55p8` /
  `CVE-2026-67213`.

Those identities are also present in npm audit and the GitHub Advisory
Database, but no open repository Dependabot alert represented them in this
authenticated census. They remain members of the exact frozen scanner batch;
provider lag cannot remove them or manufacture a provider-closure claim.

The batch owner is
`docs/security/FRONTEND_NPM_SECURITY_BATCH_REMEDIATION_CLASS.md`. Repository
version remediation, final scanner observations, and provider alert refresh are
three separate propositions.

## Separate Ruby `json` lane

Alert `#239` remains open for RubyGems `json` in iOS/Fastlane release tooling.
This npm PR does not alter `ios/Gemfile` or `ios/Gemfile.lock` and does not claim
that `json` is remediated. The follow-up is tracked at
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ruby-json-cve-2026-54696-release-tooling`
with target `json >=2.19.9`, canonical Bundler replay, classified closure,
Fastlane compatibility, and release-tooling security gates.

## Refresh rule

After merge, repeat the complete authenticated census. Until GitHub refreshes
its dependency graph, report `MERGED_PENDING_POST_MERGE_PROOF`; do not translate
a remediated lock, npm-audit result, or zero-row Trivy observation into “all
Dependabot alerts closed.”

<!-- markdownlint-enable MD013 MD031 MD032 -->

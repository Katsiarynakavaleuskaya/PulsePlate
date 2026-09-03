<!-- markdownlint-disable MD013 MD031 MD032 -->

# Frontend npm Browserslist and qs finite security batch

## Authority and bounded claim

The historical Browserslist filename is retained to preserve the existing PR
and review carrier. This file is the sole transition-evidence owner for the
operator-authorized exact finite batch:

```text
B = {npm:browserslist, npm:qs}
P_batch = P_browserslist AND P_qs
```

The operator directly confirmed this exact two-identity expansion on 3 September
2026 after a terminal full-repository npm scanner snapshot derived the same
all-and-only set. That confirmation grants no third identity, future batch,
suppression, override, direct pin, alert dismissal, force push, provider claim,
or merge authority. Canonical admission policy is the
`dependency-remediation-admission:v2` block at `AGENTS.md:2324`.

For each `D` in `B`, this owner records an independent `S_base`, `S_head`,
`F_cutoff`, non-empty `A`, authored `I_R`, replay-proven `C_R`, and universal
`P`. The permanent data-driven guard is
`tests/test_frontend_dependency_guards.py:1609`.

## Exact base, material head, and governed surfaces

The exact authorized base and merge-base are:

```text
2bfb7ff96dfcc98a806de9c113eff5242bfbe479
```

The dependency/guard material head preceding this complete batch-evidence
refresh is:

```text
c6ae3eddb41b6663719b84126a8f8fae05701263
```

This anchor is updated to the coherent batch implementation commit before the
branch is pushed. The tracked surface enumerator at
`tests/test_frontend_dependency_guards.py:1097` discovers exactly five base/head
npm surfaces:

| Surface | Base SHA-256 | Candidate SHA-256 | Reconciliation |
| --- | --- | --- | --- |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | same | executable absence; unchanged |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | same | executable absence; unchanged |
| `frontend/package.json` | `234beaabd47ec019090e28a26cc4e56fdda4b745d5d75c89c12ec958a03eed5d` | same | no direct batch owner; unchanged |
| `frontend/package-lock.json` | `3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae` | `155f75cf12988ded917d7c4a36b36da2b06c3b9d4bd5870811d5067ef718e5c0` | two `I_R` plus Browserslist `C_R` |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | same | executable absence; unchanged |

Base occurrences are `browserslist@4.28.2` and `qs@6.15.2`, both in
`frontend/package-lock.json`. Candidate occurrences are `browserslist@4.28.8`
at `frontend/package-lock.json:4743` and `qs@6.16.0` at
`frontend/package-lock.json:8938`. All manifest and root npm bytes are
unchanged from the exact base.

## Terminal scanner snapshot and complete GAD receipt

At `2026-09-03T03:39:19Z`, authenticated GAD pagination returned 3 Browserslist
records / 3 range rows and 10 qs records / 21 range rows. The terminal
full-repository npm audit snapshot returned a clean root lock and exactly two
vulnerable frontend identities. Its canonical SHA-256 is:

```text
c3aec6d46c57b693d2a9860838921fd51a16644dd76f32507a2aa3d8852419d4
```

Canonical batch receipt SHA-256:

```text
1b23fd6cbd3e491a719dae2016d52851738c5e991f9ca88c1093ae15a9e095f2
```

The retained normalized batch receipt is:

```json
{
  "authorized_dependency_identities": [
    "npm:browserslist",
    "npm:qs"
  ],
  "operator_authorization": "exact_finite_batch_confirmed_2026-09-03",
  "scanner_snapshot": {
    "base_sha": "2bfb7ff96dfcc98a806de9c113eff5242bfbe479",
    "observed_at": "2026-09-03T03:39:19Z",
    "roots": [
      {
        "command": "npm audit --package-lock-only --json",
        "exit_code": 0,
        "lock": "package-lock.json",
        "project": ".",
        "severity_counts": {
          "critical": 0,
          "high": 0,
          "info": 0,
          "low": 0,
          "moderate": 0,
          "total": 0
        },
        "vulnerability_keys": []
      },
      {
        "command": "npm audit --package-lock-only --json",
        "exit_code": 1,
        "lock": "frontend/package-lock.json",
        "project": "frontend",
        "severity_counts": {
          "critical": 0,
          "high": 1,
          "info": 0,
          "low": 0,
          "moderate": 1,
          "total": 2
        },
        "vulnerability_keys": [
          "browserslist",
          "qs"
        ]
      }
    ],
    "terminal": true,
    "vulnerable_dependency_identities": [
      "npm:browserslist",
      "npm:qs"
    ]
  },
  "scanner_snapshot_sha256": "c3aec6d46c57b693d2a9860838921fd51a16644dd76f32507a2aa3d8852419d4",
  "schema": "pulseplate.frontend-npm-security-batch-gad-receipt/v1",
  "targets": {
    "browserslist": {
      "next_page": null,
      "observed_at": "2026-09-03T03:39:19Z",
      "page_count": 1,
      "query": "GET /advisories?ecosystem=npm&affects=browserslist&per_page=100",
      "range_count": 3,
      "record_count": 3,
      "records": [
        {
          "cve_id": "CVE-2026-73088",
          "ghsa_id": "GHSA-73wf-gq98-2v4g",
          "published_at": "2026-09-01T16:41:54Z",
          "severity": "high",
          "updated_at": "2026-09-01T16:41:55Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "4.28.7",
              "package": "browserslist",
              "vulnerable_version_range": "<=4.28.6"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-73089",
          "ghsa_id": "GHSA-c83g-rgw3-j3cx",
          "published_at": "2026-09-01T16:42:13Z",
          "severity": "high",
          "updated_at": "2026-09-01T16:42:15Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "4.28.7",
              "package": "browserslist",
              "vulnerable_version_range": "<=4.28.6"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2021-23364",
          "ghsa_id": "GHSA-w8qv-6jwh-64r5",
          "published_at": "2021-05-24T19:52:40Z",
          "severity": "medium",
          "updated_at": "2023-08-17T05:02:30Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "4.16.5",
              "package": "browserslist",
              "vulnerable_version_range": ">=4.0.0,<4.16.5"
            }
          ],
          "withdrawn_at": null
        }
      ]
    },
    "qs": {
      "next_page": null,
      "observed_at": "2026-09-03T03:39:19Z",
      "page_count": 1,
      "query": "GET /advisories?ecosystem=npm&affects=qs&per_page=100",
      "range_count": 21,
      "record_count": 10,
      "records": [
        {
          "cve_id": "CVE-2026-82417",
          "ghsa_id": "GHSA-4mjr-xmp4-gh2g",
          "published_at": "2026-09-02T14:45:13Z",
          "severity": "medium",
          "updated_at": "2026-09-02T14:45:15Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.16.0",
              "package": "qs",
              "vulnerable_version_range": ">=2.2.5,<6.16.0"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2025-15284",
          "ghsa_id": "GHSA-6rw7-vpxm-498p",
          "published_at": "2025-12-30T21:02:54Z",
          "severity": "medium",
          "updated_at": "2026-03-02T22:05:33Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.14.1",
              "package": "qs",
              "vulnerable_version_range": "<6.14.1"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": null,
          "ghsa_id": "GHSA-crvj-3gj9-gm2p",
          "published_at": "2018-10-09T00:44:29Z",
          "severity": "high",
          "updated_at": "2023-01-09T05:02:51Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "1.0.0",
              "package": "qs",
              "vulnerable_version_range": "<1.0.0"
            }
          ],
          "withdrawn_at": "2020-06-16T21:32:53Z"
        },
        {
          "cve_id": "CVE-2014-10064",
          "ghsa_id": "GHSA-f9cm-p3w6-xvr3",
          "published_at": "2018-10-09T00:38:48Z",
          "severity": "high",
          "updated_at": "2023-01-09T05:02:52Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "1.0.0",
              "package": "qs",
              "vulnerable_version_range": "<1.0.0"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2017-1000048",
          "ghsa_id": "GHSA-gqgv-6jq5-jjj9",
          "published_at": "2020-04-30T17:16:47Z",
          "severity": "high",
          "updated_at": "2023-01-09T05:02:30Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.0.4",
              "package": "qs",
              "vulnerable_version_range": "<6.0.4"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.1.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.1.0,<6.1.2"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.2.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.2.0,<6.2.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.3.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.3.0,<6.3.2"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2022-24999",
          "ghsa_id": "GHSA-hrpp-h998-j3pp",
          "published_at": "2022-11-27T00:30:50Z",
          "severity": "high",
          "updated_at": "2025-04-29T15:41:45Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.2.4",
              "package": "qs",
              "vulnerable_version_range": "<6.2.4"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.10.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.10.0,<6.10.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.3.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.3.0,<6.3.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.4.1",
              "package": "qs",
              "vulnerable_version_range": ">=6.4.0,<6.4.1"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.5.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.5.0,<6.5.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.6.1",
              "package": "qs",
              "vulnerable_version_range": ">=6.6.0,<6.6.1"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.7.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.7.0,<6.7.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.8.3",
              "package": "qs",
              "vulnerable_version_range": ">=6.8.0,<6.8.3"
            },
            {
              "ecosystem": "npm",
              "first_patched_version": "6.9.7",
              "package": "qs",
              "vulnerable_version_range": ">=6.9.0,<6.9.7"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2014-7191",
          "ghsa_id": "GHSA-jjv7-qpx3-h62q",
          "published_at": "2017-10-24T18:33:36Z",
          "severity": "high",
          "updated_at": "2023-04-11T00:27:35Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "1.0.0",
              "package": "qs",
              "vulnerable_version_range": "<1.0.0"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-8723",
          "ghsa_id": "GHSA-q8mj-m7cp-5q26",
          "published_at": "2026-05-22T17:27:19Z",
          "severity": "medium",
          "updated_at": "2026-05-22T17:27:20Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.15.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.11.1,<=6.15.1"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-2391",
          "ghsa_id": "GHSA-w7fw-mjwx-w883",
          "published_at": "2026-02-12T17:04:39Z",
          "severity": "low",
          "updated_at": "2026-02-12T20:08:00Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.14.2",
              "package": "qs",
              "vulnerable_version_range": ">=6.7.0,<=6.14.1"
            }
          ],
          "withdrawn_at": null
        },
        {
          "cve_id": "CVE-2026-82562",
          "ghsa_id": "GHSA-x5fp-wj9c-mxmx",
          "published_at": "2026-09-02T14:46:57Z",
          "severity": "medium",
          "updated_at": "2026-09-02T14:46:58Z",
          "vulnerabilities": [
            {
              "ecosystem": "npm",
              "first_patched_version": "6.16.0",
              "package": "qs",
              "vulnerable_version_range": ">=6.14.2,<=6.15.3"
            }
          ],
          "withdrawn_at": null
        }
      ]
    }
  }
}
```

The authenticated query inputs were:

```text
GET /advisories?ecosystem=npm&affects=browserslist&per_page=100
GET /advisories?ecosystem=npm&affects=qs&per_page=100
pages: 1 per target
next_page: null per target
exit: 0 per query
```

The content-binding guard at
`tests/test_frontend_dependency_guards.py:3186` rejects duplicate JSON keys,
wrong batch/scanner identities, record/range omissions, changed package or
ecosystem projections, first-patched drift, and withdrawal drift.

## Per-identity applicability

### npm:browserslist

`D = npm:browserslist`; `S_base` contains one comparable `4.28.2` occurrence.
`F_cutoff` contains three records. Derived `A` is exactly:

```text
GHSA-73wf-gq98-2v4g / CVE-2026-73088
GHSA-c83g-rgw3-j3cx / CVE-2026-73089
```

`GHSA-w8qv-6jwh-64r5` is non-applicable at base because `4.28.2` is above
`>=4.0.0,<4.16.5`, but remains in universal `P_browserslist`.

### npm:qs

`D = npm:qs`; `S_base` contains one comparable `6.15.2` occurrence.
`F_cutoff` contains ten records / twenty-one ranges. Derived `A` is exactly:

```text
GHSA-x5fp-wj9c-mxmx / CVE-2026-82562
GHSA-4mjr-xmp4-gh2g / CVE-2026-82417
```

The other eight records are non-applicable at base because all their affected
ranges end before `6.15.2`. `GHSA-q8mj-m7cp-5q26` ends at `6.15.1`.
`GHSA-crvj-3gj9-gm2p` is retained with `cve_id=null`, affected `<1.0.0`, and
`withdrawn_at=2020-06-16T21:32:53Z`; retention in frozen `F_cutoff` and
universal `P_qs` is not a claim that the withdrawn record is an active current
vulnerability. All twenty-one row boundaries are executable at
`tests/test_frontend_dependency_guards.py:3143`.

## Resolver actions and exact disjoint partition

Runtime and configuration:

```text
base: 2bfb7ff96dfcc98a806de9c113eff5242bfbe479
node: v24.18.1
npm: 11.16.0
registry: https://registry.npmjs.org/
lockfileVersion: 3
flags: --package-lock-only --ignore-scripts --no-audit --no-fund
```

Each fresh external temp directory reconstructed both frontend npm files with
`git show <base>:<path>`. Six commands exited `0`:

```text
B1: npm update browserslist
B2: npm update browserslist
Q1: npm update qs
Q2: npm update qs
BQ1: npm update browserslist; npm update qs
BQ2: npm update qs; npm update browserslist
```

Results:

```text
B1 == B2:  54794b10e610e2decf7d9287f28edb55c5be08827c44caf5de5d0df4de12e244
Q1 == Q2:  5141041123a72476ca429f6de5303a03e7580496727327c5828433a6a82da8c2
BQ1 == BQ2: 155f75cf12988ded917d7c4a36b36da2b06c3b9d4bd5870811d5067ef718e5c0
keys(Delta_B) intersect keys(Delta_Q): empty
Delta_BQ == exact full-record disjoint union: true
tracked_lock_cmp_to_BQ1: 0
frontend_package_json_cmp: 0
packages_root_record_equal: true
top_level_lock_metadata_equal: true
```

Complete delta:

| Class | Identity / record | Base | Candidate | Notes |
| --- | --- | ---: | ---: | --- |
| `I_R[browserslist]` | `browserslist` | `4.28.2` | `4.28.8` | authored target replacement |
| `C_R[browserslist]` | `baseline-browser-mapping` | `2.10.37` | `2.11.20` | resolver closure |
| `C_R[browserslist]` | `caniuse-lite` | `1.0.30001799` | `1.0.30001810` | resolver closure |
| `C_R[browserslist]` | `electron-to-chromium` | `1.5.372` | `1.5.420` | resolver closure |
| `C_R[browserslist]` | `node-releases` | `2.0.47` | `2.0.54` | resolver closure |
| `C_R[browserslist]` | `update-browserslist-db` | `1.2.3` | `1.3.2` | resolver closure |
| `I_R[qs]` | `qs` | `6.15.2` | `6.16.0` | full record also changes `side-channel ^1.1.0 -> ^1.1.1` and adds `es-define-property ^1.0.1` |

`C_R[qs]` is empty: the two dependency-map changes belong to the same authored
`node_modules/qs` record; no child package record moved. Complete before/after
record equality—not versions alone—establishes the partition.

## Audit results

Exact-base terminal frontend audit:

```text
$ npm audit --package-lock-only --json
exit: 1
vulnerability_keys: browserslist, qs
moderate: 1
high: 1
critical: 0
total: 2
```

Candidate audit after the combined transaction:

```text
$ npm audit --package-lock-only --json
exit: 0
vulnerabilities: {}
info: 0
low: 0
moderate: 0
high: 0
critical: 0
total: 0

$ npm audit --package-lock-only --audit-level=moderate
exit: 0
found 0 vulnerabilities

$ npm audit --package-lock-only --audit-level=high
exit: 0
found 0 vulnerabilities
```

`audit-level` changes the exit threshold and does not filter lower-severity
report rows. Batch acceptance therefore depends on the default total-zero JSON
result, not a HIGH-only exit.

## Permanent conjunctive postcondition

The exact authorization literal and data maps are at
`tests/test_frontend_dependency_guards.py:200`. The shared executor at
`tests/test_frontend_dependency_guards.py:1609`:

1. requires exactly the literal targets `browserslist` and `qs`;
2. enumerates each tracked npm surface and rejects duplicate raw JSON members;
3. rejects direct, aliased, override, or bundled ownership for either target;
4. delegates all other source semantics to installed npm's
   `npm-package-arg`/`semver` adapter and rejects opaque sources;
5. requires dependency manifests and root lock records to match exactly and
   admits only lockfile v3;
6. validates every non-root lock record through the existing canonical
   registry-provenance adapter;
7. loads each complete virtual graph through the hermetic repository npm
   wrapper, with ambient graph-shaping configuration removed;
8. independently discovers every raw canonical/nested target occurrence;
9. rejects links, prereleases, malformed versions, identity/path conflicts,
   foreign provenance, and invalid 64-byte SHA-512 SRI metadata;
10. compares each occurrence with every affected range for its target;
11. permits per-target executable absence only after the complete shared
    admission pass.

The permanent guard does not freeze base/candidate hashes, occurrence counts,
or `4.28.8` / `6.16.0` as the only future-safe versions. Passing SRI syntax is
not a cryptographic recomputation of fetched package bytes. Opaque or future npm
semantics stop for rescope instead of creating another carrier parser.

## Provider projection

At `2026-09-03T03:39:19Z`, the complete authenticated open Dependabot census
contained only alert `#273` for Browserslist / `GHSA-73wf-gq98-2v4g`, state
`open`, development scope, `frontend/package-lock.json`, with no fixed or
dismissed timestamp. No authenticated alert currently projects `qs`; this is a
provider-projection gap, not evidence of `qs` closure or non-applicability.

Repository remediation is `P_browserslist AND P_qs`. Provider closure is a
separate post-merge observation. No alert is dismissed.

## Verification, rollback, and stop conditions

Focused verification commands include:

```text
python -m pytest -q tests/test_frontend_dependency_guards.py
python scripts/ci/check_docs_phase1_gates.py --files docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md docs/security/DEPENDABOT_ALERT_INVENTORY.md
npm query '#browserslist' --package-lock-only --json
npm query '#qs' --package-lock-only --json
npm ls browserslist qs --all --package-lock-only --json
npm explain browserslist
npm explain qs
```

Before merge, rollback means abandoning the branch/PR. After merge, never return
either identity to an affected version; use a separate secure roll-forward.

Stop on a third vulnerable identity or authored action, empty `A`, incomplete or
incomparable GAD inventory, replay mismatch, overlapping independent deltas,
combined non-union, manifest/root/unrelated package movement, missing provenance
or integrity, affected head occurrence, nonzero default/MODERATE audit, new npm
grammar branch, second evidence owner, suppression/waiver/dismissal, stale
base/head, or unresolved review/CI evidence.

This document does not claim production exploitability, whole-repository
security, provider review, provider scan, PASS, no findings, approval, merge
readiness, deployment, or release authority.

<!-- markdownlint-enable MD013 MD031 MD032 -->

<!-- markdownlint-disable MD013 MD031 MD032 -->

# Frontend `browserslist` remediation class

## Authority and bounded claim

This document is the sole transition-evidence owner for one application-dependency
remediation class:

- `D`: `npm:browserslist`;
- ecosystem: `npm`;
- `S`: the complete Git-indexed npm manifest/lock surface universe enumerated
  at the exact base and material head;
- `F_cutoff`: the three-record, fully paginated GitHub Advisory Database
  response frozen below;
- `A`: the two candidates whose affected ranges contain the governed base
  occurrence `4.28.2`;
- `I_R`: one targeted lock-only replacement, `4.28.2 -> 4.28.8`;
- `C_R`: exactly five resolver-coupled child transitions;
- `P`: every discovered head occurrence is comparable, provenance-valid,
  integrity-bearing, and outside every `F_cutoff` affected range, or the
  dependency is executably absent.

This is not a claim about future advisories, arbitrary package-manager syntax,
package contents, production exploitability, whole-repository security,
provider closure, review, CI, approval, or merge readiness. Canonical policy is
the `dependency-remediation-admission:v2` block in `AGENTS.md:2324`; the
permanent executable guard is `tests/test_frontend_dependency_guards.py:1413`.

## Exact base, material head, and surface universe

The exact synchronized base and merge-base are:

```text
6327960917e2a04e5fec0d89b358b51781b12f67
```

The immutable dependency/guard material head is:

```text
937db0926f257684cc57ef39b1dcf78589643aeb
```

The current permanent guard enumerates tracked `package.json`,
`package-lock.json`, and `npm-shrinkwrap.json` paths through
`tests/test_frontend_dependency_guards.py:1104`. At this transition, the
complete base/head universe contains exactly five surfaces:

| Surface | Base SHA-256 | Material-head SHA-256 | Reconciliation |
| --- | --- | --- | --- |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | executable absence; unchanged |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | executable absence; unchanged |
| `frontend/package.json` | `7b2b8f3fb4459ff5d42f372daf3a618360d25c07fbbec0f0439b58e2d98c4d6d` | `7b2b8f3fb4459ff5d42f372daf3a618360d25c07fbbec0f0439b58e2d98c4d6d` | no direct or aliased carrier; unchanged |
| `frontend/package-lock.json` | `3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae` | `cca7af82287c809306110702f0b52f34d1a44df05e2b76067d7f529e2d783ab4` | one `I_R` plus five `C_R` records |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | executable absence; unchanged |

The installed material-head occurrence is
`frontend/package-lock.json:4743`. The guard rejects direct and aliased
manifest authority across all enumerated surfaces and checks every canonical
or nested installed occurrence; dependency-edge selectors are not treated as
installed comparable versions.

## Candidate inventory `F_cutoff` and applicable subset `A`

The authoritative input was the fully paginated GitHub Advisory Database REST
query:

```text
GET /advisories?ecosystem=npm&affects=browserslist&per_page=100
Accept: application/vnd.github+json
observed_at: 2026-09-01T21:02:32Z
pages: 1
next_page: null
records: 3
```

The normalized receipt schema is
`pulseplate.browserslist-gad-receipt/v1`. Its canonical sorted JSON SHA-256 is:

```text
b8f1a459b8d0e7cd6e5cd4311ed41b40b57c52ab21cf9b861c12f5bb7770fcdc
```

The retained normalized receipt is:

```json
{
  "accept": "application/vnd.github+json",
  "next_page": null,
  "observed_at": "2026-09-01T21:02:32Z",
  "page_count": 1,
  "query": "GET /advisories?ecosystem=npm&affects=browserslist&per_page=100",
  "record_count": 3,
  "records": [
    {
      "cve_id": "CVE-2026-73088",
      "ghsa_id": "GHSA-73wf-gq98-2v4g",
      "published_at": "2026-09-01T16:41:54Z",
      "severity": "high",
      "summary": "Browserslist: Uncaught crash / prototype write via untrusted browserslist-stats.json custom stats (normalizeStats)",
      "updated_at": "2026-09-01T16:41:55Z",
      "vulnerabilities": [
        {
          "ecosystem": "npm",
          "first_patched_version": "4.28.7",
          "package": "browserslist",
          "vulnerable_version_range": "<= 4.28.6"
        }
      ]
    },
    {
      "cve_id": "CVE-2026-73089",
      "ghsa_id": "GHSA-c83g-rgw3-j3cx",
      "published_at": "2026-09-01T16:42:13Z",
      "severity": "high",
      "summary": "Browserslist: Unbounded memory growth (no cache eviction) via distinct query results, leading to eventual OOM",
      "updated_at": "2026-09-01T16:42:15Z",
      "vulnerabilities": [
        {
          "ecosystem": "npm",
          "first_patched_version": "4.28.7",
          "package": "browserslist",
          "vulnerable_version_range": "<= 4.28.6"
        }
      ]
    },
    {
      "cve_id": "CVE-2021-23364",
      "ghsa_id": "GHSA-w8qv-6jwh-64r5",
      "published_at": "2021-05-24T19:52:40Z",
      "severity": "medium",
      "summary": "Regular Expression Denial of Service in browserslist",
      "updated_at": "2023-08-17T05:02:30Z",
      "vulnerabilities": [
        {
          "ecosystem": "npm",
          "first_patched_version": "4.16.5",
          "package": "browserslist",
          "vulnerable_version_range": ">= 4.0.0, < 4.16.5"
        }
      ]
    }
  ],
  "schema": "pulseplate.browserslist-gad-receipt/v1"
}
```

The complete receipt projection is:

| Advisory / CVE | GitHub severity | Affected range | First patched | Base `4.28.2` | Head `4.28.8` |
| --- | --- | --- | --- | --- | --- |
| `GHSA-73wf-gq98-2v4g` / `CVE-2026-73088` | high | `<=4.28.6` | `4.28.7` | applicable | outside range |
| `GHSA-c83g-rgw3-j3cx` / `CVE-2026-73089` | high | `<=4.28.6` | `4.28.7` | applicable | outside range |
| `GHSA-w8qv-6jwh-64r5` / `CVE-2021-23364` | medium | `>=4.0.0,<4.16.5` | `4.16.5` | non-applicable: `4.28.2` is above the range | outside range |

Therefore:

```text
A = {
  GHSA-73wf-gq98-2v4g,
  GHSA-c83g-rgw3-j3cx
}
```

The historical candidate remains inside the universal `P` check even though it
creates no remediation claim. The executable boundary controls at
`tests/test_frontend_dependency_guards.py:2576` require `4.16.4`, `4.16.5`,
`4.28.2`, and `4.28.6` to fail, while `4.28.7` and `4.28.8` pass all three
recorded ranges.

## Registry admission and resolver environment

The resolver environment was:

```text
node: v24.18.1
npm: 11.16.0
registry: https://registry.npmjs.org/
lockfileVersion: 3
```

Registry metadata for `browserslist@4.28.8` returned:

```text
version: 4.28.8
deprecated: absent
engines.node: ^6 || ^7 || ^8 || ^9 || ^10 || ^11 || ^12 || >=13.7
tarball: https://registry.npmjs.org/browserslist/-/browserslist-4.28.8.tgz
integrity: sha512-V2NpofLblG64mfOtSgDhOJESZEGogzDMBv/q+W6oc4LXWP/q75eOXoOaaOu1EOadB9U4Bwx/e0yzbvwKH8zalA==
```

The exact accepted transaction was run from each temporary project directory
through the repository wrapper:

```bash
task_repo_root="$(git rev-parse --show-toplevel)"
task_replay_dir="$(mktemp -d)"
task_base_sha="6327960917e2a04e5fec0d89b358b51781b12f67" # pragma: allowlist secret
git show "${task_base_sha}:frontend/package.json" > "$task_replay_dir/package.json"
git show "${task_base_sha}:frontend/package-lock.json" > "$task_replay_dir/package-lock.json"
(
  cd "$task_replay_dir"
  "$task_repo_root/scripts/frontend_npm.sh" update browserslist \
    --package-lock-only --ignore-scripts --no-audit --no-fund
)
```

Two independent exact-base replays exited `0` and produced identical bytes:

```text
replay_lock_cmp=0
cca7af82287c809306110702f0b52f34d1a44df05e2b76067d7f529e2d783ab4  replay-1/package-lock.json
cca7af82287c809306110702f0b52f34d1a44df05e2b76067d7f529e2d783ab4  replay-2/package-lock.json
package_json_cmp=0
```

An earlier planning probe using `--prefix <absolute-temp-directory>` was
rejected: npm serialized temp-relative package keys, the two lock hashes
diverged, and the delta exceeded this class. None of those bytes entered the
repository. The successful cwd-bound replay above is the frozen resolver
boundary.

## Operator intent `I_R` and deterministic closure `C_R`

`I_R` contains exactly one authored replacement operation:

| Class | Package | Base | Head |
| --- | --- | ---: | ---: |
| `I_R` | `browserslist` | `4.28.2` | `4.28.8` |

The complete mechanically coupled closure is:

| Class | Package | Base | Head | Relationship |
| --- | --- | ---: | ---: | --- |
| `C_R` | `baseline-browser-mapping` | `2.10.37` | `2.11.20` | satisfies the selected Browserslist `^2.11.12` edge |
| `C_R` | `caniuse-lite` | `1.0.30001799` | `1.0.30001810` | satisfies `^1.0.30001809` |
| `C_R` | `electron-to-chromium` | `1.5.372` | `1.5.419` | satisfies `^1.5.402` |
| `C_R` | `node-releases` | `2.0.47` | `2.0.54` | satisfies `^2.0.53` |
| `C_R` | `update-browserslist-db` | `1.2.3` | `1.3.2` | satisfies `^1.3.0` |

The selected package dependency edges are visible at
`frontend/package-lock.json:4763`. No package was added or removed; no direct
manifest, root lock, registry, lock-schema, suppression, waiver, or unrelated
dependency changed. Every material dependency record belongs exactly once to
`I_R` or `C_R`.

## Base and head audit observations

The exact-base command was:

```bash
scripts/frontend_npm.sh audit --package-lock-only --json
```

It exited `1` with the following bounded result:

```text
high: 1
critical: 0
total: 1
package: browserslist
range: <=4.28.6
via: GHSA-c83g-rgw3-j3cx, GHSA-73wf-gq98-2v4g
node: node_modules/browserslist
```

At material head, the same command exited `0`:

```text
info: 0
low: 0
moderate: 0
high: 0
critical: 0
total: 0
vulnerabilities: {}
```

This audit observation corroborates the package-class postcondition. It is not
provider closure, review, approval, CI, or merge-readiness evidence.

## Permanent postcondition `P`

The executable guard at `tests/test_frontend_dependency_guards.py:1413`:

1. mechanically enumerates the current tracked npm surface universe;
2. rejects every direct, optional, peer, override, bundled, npm-alias, tarball,
   or tracked-local manifest carrier;
3. discovers each installed lock candidate by canonical path, explicit name,
   or tarball identity before validation and closes dependency demand per lock
   surface, so one safe graph cannot mask a demand-only sibling graph;
4. validates every non-optional demand selector against an installed version
   in that lock and excludes a peer only when `peerDependenciesMeta` contains
   the exact boolean marker `optional: true`;
5. rejects unsupported lock schemas, malformed or prerelease versions,
   noncanonical paths, conflicting names, provenance mismatches, and any
   integrity value that is not a valid 64-byte `sha512` SRI digest;
6. binds the exact three advisory identities and exact two-member `A`, then
   compares every discovered stable version with every recorded affected range;
7. permits executable absence only after the complete discovery pass finds no
   manifest carrier, required lock dependency demand, or installed record.

The guard deliberately does not freeze `4.28.8`, the historical occurrence
count, this base, or this transition delta. A later authorized safe patch or
complete removal remains possible.

Focused verification completed with exit `0`:

```text
$ VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
$ "$VENV_PYTHON" -m pytest -q tests/test_frontend_dependency_guards.py
........................................................................ [ 41%]
........................................................................ [ 83%]
.............................                                            [100%]
```

The repository-wide pre-commit hook also exited `0` after Black's first-pass
format update was applied and the focused suite was rerun. Current-head GitHub
CI, review dispositions, mapping, and the mandatory wait window remain pending.

## Provider state and alert inventory

At `2026-09-01T21:02:32Z`, the complete authenticated open Dependabot census
contained exactly repository alert `#273` for
`GHSA-73wf-gq98-2v4g`, manifest `frontend/package-lock.json`, development
scope, state `open`, with no `fixed_at` or `dismissed_at`. The provider currently
projects only that advisory; the fully reconciled package-class evidence also
contains `GHSA-c83g-rgw3-j3cx` and the historical non-applicable candidate.

Repository remediation and provider ingestion are separate rails. Until an
authenticated post-merge lookup reports terminal provider state, the correct
status is `REPOSITORY_REMEDIATED_PROVIDER_OPEN`, not `CLOSED`.

## Residual risk, rollback, and stop conditions

Residual risk remains for future or corrected advisories, future npm carrier or
lock schemas, malicious package contents, build-tool behavior changes, provider
lag, unrelated dependency findings, CI failures, and review findings.

Before merge, rollback means abandoning the complete branch/PR transaction.
After merge, reverting to vulnerable `4.28.2` is forbidden; regressions require
a secure roll-forward to another compatible version outside every frozen range.

Stop and rescope if:

- the fully paginated cutoff no longer reconciles to these three records;
- another applicable advisory or governed occurrence appears;
- any surface, occurrence, provenance, integrity, or dependency delta is
  ambiguous or unclassified;
- a manifest pin, override, suppression, waiver, registry change, unsupported
  lock schema, second authored action, second dependency identity, or second
  evidence owner becomes necessary;
- replay no longer yields the exact one-`I_R` plus five-`C_R` partition.

<!-- markdownlint-enable MD013 MD031 MD032 -->

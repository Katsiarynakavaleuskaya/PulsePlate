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
permanent executable guard is `tests/test_frontend_dependency_guards.py:1486`.

## Exact base, material head, and surface universe

The exact synchronized base and merge-base are:

```text
2bfb7ff96dfcc98a806de9c113eff5242bfbe479
```

The dependency/guard material head preceding this evidence refresh is:

```text
c39ab21fb98495fc5a24bda87fbf2992795615cb
```

The delegated-recognizer mechanism was introduced by reachable commit
`a51a14f9f5c986f8e9a676f5d1add97746252a39` and its final structural admission
controls were added by the material head above. Base synchronization entered
through `be39aa939486e55d1eeab52712c0bf6f37befbb5`, whose parents are
`7bcc55f9d14d771b4b17cc3881e303afc9b0e9d3` and
`2bfb7ff96dfcc98a806de9c113eff5242bfbe479`; its merge-base with current
`origin/main` is the latter.

The current permanent guard enumerates tracked `package.json`,
`package-lock.json`, and `npm-shrinkwrap.json` paths through
`tests/test_frontend_dependency_guards.py:1014`. At this transition, the
complete base/head universe contains exactly five surfaces:

| Surface | Base SHA-256 | Material-head SHA-256 | Reconciliation |
| --- | --- | --- | --- |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | executable absence; unchanged |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | executable absence; unchanged |
| `frontend/package.json` | `234beaabd47ec019090e28a26cc4e56fdda4b745d5d75c89c12ec958a03eed5d` | `234beaabd47ec019090e28a26cc4e56fdda4b745d5d75c89c12ec958a03eed5d` | no direct or aliased carrier; unchanged from synchronized base |
| `frontend/package-lock.json` | `3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae` | `54794b10e610e2decf7d9287f28edb55c5be08827c44caf5de5d0df4de12e244` | one `I_R` plus five `C_R` records |
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
observed_at: 2026-09-02T10:19:40Z
pages: 1
next_page: null
records: 3
```

The normalized receipt schema is
`pulseplate.browserslist-gad-receipt/v1`. Its canonical sorted JSON SHA-256 is:

```text
4a0b408d1e570f005e871a9f96236c8250542e86eb01bc89137ffc8cd9d6756f
```

The retained normalized receipt is:

```json
{
  "accept": "application/vnd.github+json",
  "next_page": null,
  "observed_at": "2026-09-02T10:19:40Z",
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

The deterministic binding at `tests/test_frontend_dependency_guards.py:2847`
parses this retained JSON with duplicate-key rejection at
`tests/test_frontend_dependency_guards.py:1527`, canonicalizes it with sorted
compact keys, verifies the displayed SHA-256, and requires the exact three
advisory identities.

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
`tests/test_frontend_dependency_guards.py:2834` require `4.16.4`, `4.16.5`,
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
task_base_sha="2bfb7ff96dfcc98a806de9c113eff5242bfbe479" # pragma: allowlist secret
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
54794b10e610e2decf7d9287f28edb55c5be08827c44caf5de5d0df4de12e244  replay-1/package-lock.json
54794b10e610e2decf7d9287f28edb55c5be08827c44caf5de5d0df4de12e244  replay-2/package-lock.json
package_json_cmp=0
```

The registry observation cutoff for this one-time replay pair is
`2026-09-02T10:19:40Z`. The retained lock bytes and their SHA-256 are the
immutable transition receipt; the public npm registry is mutable and does not
provide time-travel resolution. Therefore this command is a contemporaneous
two-run solver witness, not a promise that rerunning it after the cutoff will
select the same compatible child patches. Any later resolver output, including
a newer safe Browserslist or child patch, requires a fresh bounded admission
and must not overwrite this historical receipt. The permanent guard owns
future head safety independently of the one-time resolver receipt.

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
| `C_R` | `electron-to-chromium` | `1.5.372` | `1.5.420` | satisfies `^1.5.402` |
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

At the synchronized material head, the same command exited `0` under the
repository HIGH threshold and reported no remaining Browserslist finding:

```text
info: 0
low: 0
moderate: 1
high: 0
critical: 0
total: 1
package: qs@6.15.2
via: GHSA-x5fp-wj9c-mxmx, GHSA-4mjr-xmp4-gh2g
browserslist: absent from vulnerabilities
```

This audit observation corroborates the package-class postcondition. It is not
provider closure, review, approval, CI, or merge-readiness evidence. The two
`qs` advisories were published after this class's frozen Browserslist cutoff,
belong to a second dependency identity, and are therefore tracked without lock
mutation at
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-frontend-qs-2026-moderate-advisories`.

## Permanent postcondition `P`

The executable guard at `tests/test_frontend_dependency_guards.py:1523` uses a
delegated recognizer boundary instead of a Browserslist-specific npm parser:

1. it mechanically enumerates the current tracked npm surface universe at
   `tests/test_frontend_dependency_guards.py:1015` and loads each raw surface
   with duplicate-member rejection at
   `tests/test_frontend_dependency_guards.py:1362`;
2. it validates only local JSON container shape at
   `tests/test_frontend_dependency_guards.py:1338`, rejects direct target keys,
   aliases, overrides, and bundle ownership, and delegates every other manifest
   source to the existing root npm adapter imported at
   `tests/test_frontend_dependency_guards.py:29`;
3. that adapter resolves `npm-package-arg` and `semver` from the active installed
   npm tree and admits only registry `version` or `range` selectors; Git, local,
   tarball, workspace, tag, malformed, and unknown sources are opaque and fail
   closed rather than being interpreted by package-specific string branches;
4. dependency-bearing manifest roots must have exactly one same-root lock
   authority, every lock root must have a tracked manifest, and each root
   dependency container must exactly equal its manifest counterpart; the class
   accepts only `lockfileVersion: 3` and therefore does not partially interpret
   the separate v2 compatibility tree. These boundaries are enforced at
   `tests/test_frontend_dependency_guards.py:1385`;
5. each lock-bearing project is loaded through the repository wrapper with
   `npm ls --all --package-lock-only --json`. The invocation removes ambient
   Node/npm graph controls, uses empty temporary user/global configs, explicitly
   disables global/workspace/link filtering, includes dev/optional/peer edges,
   and requires exit `0`, object JSON, no `error`, and no `problems`; the exact
   policy is bound at `tests/test_frontend_dependency_guards.py:136` and its
   adversarial control is `tests/test_frontend_dependency_guards.py:2717`;
6. canonical registry provenance for every non-root lock record and raw target
   discovery by path, explicit name, or canonical tarball identity reuse the
   existing root dependency-guard adapter; nested raw target records are not
   replaced by npm's rendered or deduplicated display tree;
7. only the target-specific layer at
   `tests/test_frontend_dependency_guards.py:1503` requires a canonical
   Browserslist installed path, rejects links and prereleases, compares the
   stable exact version with all three `F_cutoff` ranges, requires the exact npm
   registry tarball URL, and validates a syntactic 64-byte `sha512` SRI value;
8. the exact applicable set `A` is recomputed from base `4.28.2` against every
   reconciled advisory range at `tests/test_frontend_dependency_guards.py:2921`;
9. executable absence is permitted only after raw JSON, manifest-source,
   manifest/lock topology admission, successful complete virtual-graph loading,
   and raw target occurrence discovery all complete without ambiguity.

The active PATH-resolved Node/npm toolchain is the semantic witness for selector
and virtual-tree behavior. The current admitted runtime is Node `24.18.1` with
npm `11.16.0`; npm itself is not repository-version-pinned, so the adversarial
tests are the fail-closed drift detector. The guard does not fetch packages or
cryptographically recompute tarball contents: it validates recorded canonical
provenance and SRI syntax only. It makes no universal claim across future npm
versions, arbitrary package contents, untracked installs, or new lock schemas.

The guard deliberately does not freeze `4.28.8`, the historical occurrence
count, this base, or this transition delta. A later authorized safe patch or
complete removal remains possible.

Focused verification completed with exit `0`:

```text
$ VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
$ "$VENV_PYTHON" -m pytest -q tests/test_frontend_dependency_guards.py
........................................................................ [ 40%]
........................................................................ [ 80%]
....................................                                     [100%]
```

The focused file collected 180 tests, including 42 Browserslist controls. The
repository-wide pre-commit hook must be rerun on the final material state.
Current-head GitHub CI, review dispositions, mapping, and the mandatory wait
window remain pending.

## Provider state and alert inventory

At `2026-09-02T10:19:40Z`, the complete authenticated open Dependabot census
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

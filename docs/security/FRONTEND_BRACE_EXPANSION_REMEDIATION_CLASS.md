# Frontend `brace-expansion` remediation class

## Authority and bounded claim

This document is the sole current evidence owner for one application-dependency
remediation class:

- `D`: `npm:brace-expansion`;
- ecosystem: `npm`;
- `S`: the complete repository npm manifest/lock surface universe reconciled
  below, with the governed occurrences confined to the frontend graph;
- `R`: one authored scoped-replacement operation and semantic intent;
- `P`: every governed head occurrence is comparable with and outside every
  affected range in the finite `F_cutoff` inventory.

The 2.x and 5.x outputs are parameters and occurrence variants of this one
class. They are not separate classes. Advisory IDs are candidates evaluated by
the class; they are not class boundaries either.

The historical combined npm remediation document and the historical root
AgentGuard removal document remain supporting point-in-time evidence only:

- `docs/security/CVE-2026-4926-path-to-regexp-and-CVE-2026-33750-brace-expansion.md`;
- `docs/security/GHSA-f886-m6hf-6m8v-brace-expansion.md`.

Neither historical document owns this current frontend class. In particular,
`path-to-regexp`, the removed root AgentGuard graph, and the frontend graph have
different `D`, `S`, or `R` boundaries and cannot be batched by this owner.

## Frozen material and surface reconciliation

The exact base is commit
`906049a03d26dcba05d69f46e0eec85861f3ba70`. The base artifacts are bound by:

- `frontend/package.json` SHA-256
  `17235b55570d8137d35b54a6d6a7a605cb7eea23f1acf684f842baf06f85c05b`;
- `frontend/package-lock.json` SHA-256
  `059def600151a44cc1feacc40cb2638df23140c6e0de62f8d26291a47f697300`.

The proposed head dependency artifacts are bound independently of the eventual
Git commit by:

- `frontend/package.json` SHA-256
  `97bd09c0eec4fd15a582dd6a3fc96f02b29610e7955166796421f3cea703f309`;
- `frontend/package-lock.json` SHA-256
  `41d793fe5905be75656cffc03fd03f9c8371ecf1f8f60aa8ee979e789efe5885`.

The repository npm-surface sweep enumerates exactly:

1. `package.json`;
2. `package-lock.json`;
3. `frontend/package.json`;
4. `frontend/package-lock.json`;
5. `scripts/business_collateral/package.json`.

The root manifest/lock pair and the business-collateral manifest contain no
`brace-expansion` occurrence. They are unchanged by this PR, so their
base/head reconciliation is executable absence. The two non-empty governed
surfaces are therefore the same at base and head:

| Surface | Occurrence | Base | Head |
| --- | --- | ---: | ---: |
| `frontend/package.json` | `/overrides/minimatch@3/brace-expansion` | `2.0.3` | `2.1.3` |
| `frontend/package.json` | `/overrides/minimatch@10/brace-expansion` | `5.0.6` | `5.0.8` |
| `frontend/package-lock.json` | `/packages/node_modules/brace-expansion` | `2.0.3` | `2.1.3` |
| `frontend/package-lock.json` | `/packages/node_modules/glob/node_modules/brace-expansion` | `5.0.6` | `5.0.8` |

There is no surface addition or removal. Dependency-edge semver strings inside
the lockfile are resolver inputs, not installed comparable values, and are not
misclassified as additional occurrences.

Exact head evidence anchors are `frontend/package.json:86`,
`frontend/package-lock.json:4720`, and `frontend/package-lock.json:6355`.

## Candidate inventory `F_cutoff` and applicable subset `A`

The authoritative candidate input is the paginated GitHub Advisory Database
REST query:

```text
GET /advisories?ecosystem=npm&affects=brace-expansion&per_page=100
Accept: application/vnd.github+json
```

Cutoff: `2026-08-01T05:41:33Z`. The response contained exactly six records and
no next page. After retaining the advisory identity, publication/update state,
severity, summary, and npm `brace-expansion` ranges and sorting by GHSA ID, the
canonical JSON response SHA-256 was
`07cf9e303aac2c81ac5072d5c0ff1a7e1fd8ec76cdb3af07242db0ac06e38311`.

That finite reconciled response is `F_cutoff`:

| Advisory | Affected ranges relevant to the database record | Base disposition | Universal head evidence |
| --- | --- | --- | --- |
| [`GHSA-3jxr-9vmj-r5cp`](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp) / `CVE-2026-13149` | `<1.1.16`; `>=2.0.0,<2.1.2`; `>=3.0.0,<5.0.7` | **Applicable**: both `2.0.3` and `5.0.6` are affected | `2.1.3` and `5.0.8` are outside every affected range |
| [`GHSA-mh99-v99m-4gvg`](https://github.com/advisories/GHSA-mh99-v99m-4gvg) / `CVE-2026-14257` | `<1.1.17`; `>=2.0.0,<2.1.3`; `>=3.0.0,<3.0.3`; `>=4.0.0,<5.0.8` | **Applicable**: both `2.0.3` and `5.0.6` are affected | `2.1.3` and `5.0.8` equal their relevant first-patched versions |
| [`GHSA-jxxr-4gwj-5jf2`](https://github.com/advisories/GHSA-jxxr-4gwj-5jf2) / `CVE-2026-45149` | `>=5.0.0,<5.0.6` | Non-applicable: `5.0.6` equals the first-patched version; 2.x has no affected range | `5.0.8` remains above the fixed boundary; 2.x remains outside the advisory domain |
| [`GHSA-f886-m6hf-6m8v`](https://github.com/advisories/GHSA-f886-m6hf-6m8v) / `CVE-2026-33750` | `<1.1.13`; `>=2.0.0,<2.0.3`; `>=3.0.0,<3.0.2`; `>=4.0.0,<5.0.5` | Non-applicable: `2.0.3` equals its first-patched version and `5.0.6` is above `5.0.5` | both head outputs remain outside every affected range |
| [`GHSA-v6h2-p8h4-qcjw`](https://github.com/advisories/GHSA-v6h2-p8h4-qcjw) / `CVE-2025-5889` | `>=1.0.0,<=1.1.11`; `>=2.0.0,<=2.0.1`; `==3.0.0`; `==4.0.0` | Non-applicable: `2.0.3` is above the affected 2.x interval and there is no 5.x range | both head outputs remain outside every affected range |
| [`GHSA-832h-xg76-4gv6`](https://github.com/advisories/GHSA-832h-xg76-4gv6) / `CVE-2017-18077` | `<1.1.7` | Non-applicable: neither base major is in the advisory domain | neither head major is in the advisory domain |

The exact non-empty applicable subset derived from comparable affected base
witnesses is:

```text
A = {
  GHSA-3jxr-9vmj-r5cp,
  GHSA-mh99-v99m-4gvg
}
```

Only these two candidates receive a remediation attribution. The other four
remain in `P`; their non-applicability at base is not permission for an affected
or unresolved head occurrence.

As secondary reconciliation evidence, exact-base
`npm audit --package-lock-only --json` exited `1`, reported 12 total findings,
and reported `brace-expansion` through `GHSA-3jxr-9vmj-r5cp` and
`GHSA-mh99-v99m-4gvg`. The proposed-head command also exited `1`, reported nine
unrelated findings, and returned no `brace-expansion` vulnerability key. That
bounded absence is not an overall audit PASS and does not claim zero
vulnerabilities.

## Operator intent `I_R` and deterministic closure `C_R`

`I_R` contains exactly two non-identity manifest transitions:

```text
/overrides/minimatch@3/brace-expansion: 2.0.3 -> 2.1.3
/overrides/minimatch@10/brace-expansion: 5.0.6 -> 5.0.8
```

Both are one equivalence class: the authored operation is a parent-scoped npm
override replacement and the semantic intent is to move every frontend
`brace-expansion` variant beyond all applicable known ranges without collapsing
incompatible majors. The literal targets are parameters of that operation.
A blanket override is forbidden.

`C_R` is the mechanically coupled npm lock closure produced from the exact base
using:

```text
working directory: frontend/
Node: v24.16.0
npm: 11.13.0
lockfileVersion: 3
registry: https://registry.npmjs.org/
command: npm install --package-lock-only --ignore-scripts
```

The complete closure is limited to `version`, exact HTTPS `resolved`, and
`integrity` replacement for both installed lock records, plus the npm-published
`engines.node` metadata transition from `18 || 20 || >=22` to `20 || >=22` for
the nested 5.x record. Dependency edges, license/dev flags, and all unrelated
dependency identities remain unchanged. A replay producing any additional
dependency transition is not this `C_R` and must fail the lane; manual lock
editing carries no remediation authority.

## Postcondition `P` and executable guard

For every candidate in all of `F_cutoff`, every installed occurrence on every
head surface must be parseable and outside every affected range, or the surface
must prove executable absence. The deterministic guard derives `A` from exact
base witnesses, verifies the four non-applicable dispositions, and then checks
both `2.1.3` and `5.0.8` against all six candidates.

Candidate discovery is deliberately separate from provenance validity. Within
the finite lockfile-v3 `packages` map, an entry is considered a potential
`brace-expansion` occurrence when any of these bounded identity signals exists:

1. a canonical terminal installed path `node_modules/brace-expansion`;
2. an explicit package `name` equal to `brace-expansion`;
3. a parsed/raw tarball pathname in the `brace-expansion` package namespace.

Only after discovery may validation require the canonical relative POSIX path,
the exact `https://registry.npmjs.org` origin, the version-derived tarball path,
empty URL params/query/fragment, a consistent optional name, and non-empty
integrity. Thus a foreign-host, query-decorated, or fragment-decorated alias is
rejected rather than disappearing from the quantified candidate universe.

This is a finite closed-world claim over the manifest override tree and
lockfile-v3 `packages` map. It does not claim recognition of arbitrary mirrors,
renamed packages, publisher behavior, future advisories, future lockfile
schemas, or artifacts with none of the three bounded identity signals.

## Residual risks, rollback, and stop conditions

The head audit's unrelated residual inventory remains separate:
`@eslint/eslintrc`, `@redocly/openapi-core`, `dompurify`, `js-yaml`, `jspdf`,
`postcss`, `react-router`, `react-router-dom`, and `style-dictionary`. This PR
does not mutate or disposition those classes, `path-to-regexp`, or the root npm
graph.

Stop and rescope rather than widening this PR if:

- the frozen advisory response is not reproducible or contains a seventh
  candidate at the recorded cutoff;
- a new base/head surface, unresolved occurrence, or unreconciled surface delta
  appears;
- deterministic resolver replay changes another dependency identity or cannot
  reproduce the closure above;
- a second authored operation or dependency objective is required;
- a materially novel carrier outside the three bounded identity signals exposes
  the same open-world assumption;
- preserving the invariant would require changing either historical evidence
  document or the root admission authority.

Rollback must revert both scoped override parameters and the complete generated
lock closure together. It must not introduce a blanket override, suppress npm
audit, weaken the guard, or rewrite the historical evidence owners.

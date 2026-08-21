<!-- markdownlint-disable MD013 MD024 MD031 MD032 -->

# Frontend npm security batch remediation class

## Authority and bounded claim

The operator directly authorized this exact finite same-ecosystem batch on
2026-08-21, outside the candidate diff. The scanner derives the cardinality;
it does not create authority. The exact identity set is:

```text
D_batch = {
  npm:brace-expansion,
  npm:dompurify,
  npm:js-yaml,
  npm:nanoid,
  npm:postcss,
  npm:style-dictionary,
  npm:undici
}
```

This document is the sole transition-evidence owner for that seven-identity
batch. Its claim is limited to governed repository versions at the recorded
base, cutoff, resolver transaction, and head content hashes. It does not prove
historical exploitability absence, benign package contents, deployment,
whole-frontend or whole-repository security, future advisory absence, or
Dependabot graph refresh.

The exact base is
`e2be23492a5266116109f4908f5ee33bd05711e0`. At synchronization time,
exact-main canonical CI run `32453370862` was still nonterminal; the operator
explicitly directed this security-stabilization lane to continue without
waiting for that run. This is not a healthy-main or terminal-CI claim, and the
PR's own exact-current-head CI remains mandatory. Current manifest intent is anchored at
`frontend/package.json:77` and the first affected lock witness at
`frontend/package-lock.json:4720`.

## Immutable admission snapshot

Snapshot identifier:
`frontend-npm-security-batch/20260821T064721Z-e2be2349`.

The gitignored local evidence directory is
`artifacts/security_lab/frontend-npm-security-batch/20260821T064721Z-e2be2349/`.
Raw provider payloads remain local and are not committed. The committed
projection records only finite identifiers, commands, timestamps, counts, and
hashes.

Admission inputs:

- Trivy `0.72.0`;
- vulnerability DB schema `2`;
- DB `UpdatedAt`: `2026-08-20T13:14:11.601761173Z`;
- DB `DownloadedAt`: `2026-08-20T18:17:04.657176Z`;
- scan timestamp: `2026-08-21T06:47:21Z`;
- Node `v24.18.1`;
- npm `11.16.0`;
- registry: `https://registry.npmjs.org/`;
- lockfile version `3`;
- no tracked `.npmrc`, registry change, suppression, waiver, or ignore policy.

Exact scanner command:

```bash
trivy fs frontend \
  --scanners vuln \
  --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
  --include-dev-deps \
  --skip-dirs frontend/node_modules \
  --skip-version-check \
  --format json \
  --exit-code 0
```

The normalized sorted projection contains package identity, installed version,
scanner vulnerability ID, fixed-version text, and severity for every row.
Its SHA-256 is
`ead66dea10631006f0ed8ddc97f6eb5285da5106b27c873af0954613f01ce53f`.
The result is exactly seven identities, eight distinct affected installed lock
records, 15 `(installed occurrence × advisory)` finding rows, and 14 unique
advisories. “15 rows” does not mean 15 distinct package nodes.

Authenticated Dependabot pagination used:

```text
GET /repos/Katsiarynakavaleuskaya/PulsePlate/dependabot/alerts
    ?state=open&per_page=100
pagination: --paginate --slurp
```

It returned 13 open alerts: 12 npm alerts for five batch identities and one
RubyGems `json` alert. `brace-expansion` and `nanoid` are absent from that
provider census but present in Trivy, npm audit, and the GitHub Advisory
Database. That is recorded provider lag, not an identity omission.

## Exact tracked surface universe

Git-index enumeration at both base and head must equal exactly these five
surfaces:

1. `package.json`;
2. `package-lock.json`;
3. `frontend/package.json`;
4. `frontend/package-lock.json`;
5. `scripts/business_collateral/package.json`.

| Surface | Exact-base SHA-256 | Intended-head SHA-256 | Batch material |
| --- | --- | --- | --- |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | same | none |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | same | none; retains safe `nanoid@5.1.16` |
| `frontend/package.json` | `681130ffb4dcf434b3d35f9ba84de41c13771de99f411b016e73c31b3f682698` | `7b2b8f3fb4459ff5d42f372daf3a618360d25c07fbbec0f0439b58e2d98c4d6d` | seven authored declaration/override projections |
| `frontend/package-lock.json` | `2dc7084e209ab24b824f64fee88e63abc09e8abeb58301148405bd2fd4300aa9` | `3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae` | npm-generated target records and closure |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | same | none |

Every surface participates for every identity. A surface with no occurrence is
an explicit empty projection, not an omitted surface. The only additional
same-identity head witness outside the frontend lock is the unchanged safe root
`package-lock.json` record `nanoid@5.1.16`.

## Per-identity `F_cutoff`, applicability, action, and postcondition

For each identity below, `A = F_cutoff` is non-empty because every advisory has
an affected comparable base witness. Every head occurrence must be stable,
advisory-comparable, canonically registry-resolved with non-empty integrity,
and outside every affected range, or the identity must be executably absent.

| Identity | Affected base witness | Exact `F_cutoff` | One authored `I_R` | Head target |
| --- | --- | --- | --- | --- |
| `brace-expansion` | `2.1.3`, `5.0.8` | `GHSA-rgw5-rvv9-x895` | replace both existing major-specific override outputs | `2.1.4`, `5.0.9` |
| `dompurify` | `3.4.11` | `GHSA-c2j3-45gr-mqc4`; `GHSA-55q2-fjhq-7xh7` | replace existing override | `3.4.13` |
| `js-yaml` | `4.2.0` | `GHSA-52cp-r559-cp3m`; `GHSA-5p4m-2wfm-xmqj` | replace existing override | `4.3.1` |
| `nanoid` | `3.3.17` | `GHSA-2v37-7h3g-55p8` | exact temporary npm seed/unseed, with no final manifest carrier | `3.3.18`; unchanged root `5.1.16` remains safe |
| `postcss` | `8.5.15` | `GHSA-r28c-9q8g-f849`; `GHSA-fxqj-rqcc-2cmp` | raise existing direct dev declaration | security floor `8.5.23`; selected `8.5.26` |
| `style-dictionary` | `5.3.3` | `GHSA-vj5c-m527-mpff` | replace existing direct dev declaration | `5.4.4` |
| `undici` | `7.28.0` | `GHSA-8xcm-r25x-g524`; `GHSA-4cwx-7wf7-3272`; `GHSA-jr45-8vmc-qm54`; `GHSA-v3r7-h72x-cjcm`; `GHSA-m8rv-5g2x-5cg5` | replace existing override | `7.29.0` |

Canonical GitHub Advisory Database records:

- <https://github.com/advisories/GHSA-rgw5-rvv9-x895>;
- <https://github.com/advisories/GHSA-c2j3-45gr-mqc4>;
- <https://github.com/advisories/GHSA-55q2-fjhq-7xh7>;
- <https://github.com/advisories/GHSA-52cp-r559-cp3m>;
- <https://github.com/advisories/GHSA-5p4m-2wfm-xmqj>;
- <https://github.com/advisories/GHSA-2v37-7h3g-55p8>;
- <https://github.com/advisories/GHSA-r28c-9q8g-f849>;
- <https://github.com/advisories/GHSA-fxqj-rqcc-2cmp>;
- <https://github.com/advisories/GHSA-vj5c-m527-mpff>;
- <https://github.com/advisories/GHSA-8xcm-r25x-g524>;
- <https://github.com/advisories/GHSA-4cwx-7wf7-3272>;
- <https://github.com/advisories/GHSA-jr45-8vmc-qm54>;
- <https://github.com/advisories/GHSA-v3r7-h72x-cjcm>;
- <https://github.com/advisories/GHSA-m8rv-5g2x-5cg5>.

The same cutoff also records the Trivy CVE aliases:
`CVE-2026-69152`, `CVE-2026-59869`, `CVE-2026-67213`,
`CVE-2026-73646`, `CVE-2026-69153`, `CVE-2026-54639`,
`CVE-2026-16728`, `CVE-2026-13697`, `CVE-2026-14643`,
`CVE-2026-16729`, and `CVE-2026-15157`.

## Registry and target admission

`npm view` was recorded for every exact target. All eight outputs exist, are
stable, have no deprecation metadata, provide canonical npm HTTPS tarballs and
SRI integrity, and admit Node `24.18.1`:

| Exact output | Engine admission |
| --- | --- |
| `brace-expansion@2.1.4` | no restrictive engine metadata |
| `brace-expansion@5.0.9` | `20 || >=22` |
| `dompurify@3.4.13` | no restrictive engine metadata |
| `js-yaml@4.3.1` | no restrictive engine metadata |
| `nanoid@3.3.18` | `^10 || ^12 || ^13.7 || ^14 || >=15.0.1` |
| `postcss@8.5.26` | `^10 || ^12 || >=14` |
| `style-dictionary@5.4.4` | `>=22.0.0` |
| `undici@7.29.0` | `>=20.18.1` |

PostCSS `8.5.26` is deliberately above the security floor `8.5.23`; the
selected release also carries the upstream `list.split()` regression fix and
source-map path-protection follow-up.

## Material transaction and complete JSON delta partition

The exact resolver sequence is:

```bash
./scripts/frontend_npm.sh --prefix frontend install \
  --package-lock-only --ignore-scripts --no-audit --no-fund \
  --save-dev --save-exact nanoid@3.3.18
./scripts/frontend_npm.sh --prefix frontend uninstall \
  --package-lock-only --ignore-scripts --no-audit --no-fund \
  --save-dev nanoid
./scripts/frontend_npm.sh --prefix frontend install \
  --package-lock-only --ignore-scripts --no-audit --no-fund
```

The final manifest contains no `nanoid` carrier. npm generated the lock; no
manual lock edit, `npm update`, `npm audit fix`, force flag, legacy peer mode,
or registry change occurred.

Every changed JSON pointer belongs exactly once to this partition:

| Classification | JSON pointers |
| --- | --- |
| `I_R(brace-expansion)` projection | `/overrides/minimatch@3/brace-expansion`; `/overrides/minimatch@10/brace-expansion`; both corresponding lock records' `version`, `resolved`, and `integrity` |
| `I_R(dompurify)` projection | `/overrides/dompurify`; `node_modules/dompurify/{version,resolved,integrity}` |
| `I_R(js-yaml)` projection | `/overrides/js-yaml`; `node_modules/js-yaml/{version,resolved,integrity}` |
| `I_R(nanoid)` projection | `node_modules/nanoid/{version,resolved,integrity}`; no final manifest pointer |
| `I_R(postcss)` projection | `/devDependencies/postcss` in manifest and lock root; `node_modules/postcss/{version,resolved,integrity}` |
| `I_R(style-dictionary)` projection | `/devDependencies/style-dictionary` in manifest and lock root; `node_modules/style-dictionary/{version,resolved,integrity}` |
| `I_R(undici)` projection | `/overrides/undici`; `node_modules/undici/{version,resolved,integrity}` |
| deterministic npm `C_R` | `node_modules/postcss/dependencies/nanoid: ^3.3.12 -> ^3.3.17`; `node_modules/style-dictionary/dependencies/@bundled-es-modules/deepmerge: ^4.3.1 -> ^4.3.2` |

There are no package additions or removals. React, React DOM, React Router,
Vite, Vitest, Storybook, TypeScript, Playwright, Node, scripts, registry,
remaining overrides, and `lockfileVersion` do not move.

## Independent exact-base replays

Two disposable workspaces began with exact-base
`frontend/package-lock.json` SHA-256
`2dc7084e209ab24b824f64fee88e63abc09e8abeb58301148405bd2fd4300aa9`
and the same intended final manifest. Each ran the exact seed, unseed, and final
install sequence above with Node `v24.18.1`, npm `11.16.0`, and the canonical
registry.

Replay A, replay B, and the working lock are byte-identical. Each has SHA-256:

```text
3584251c809e21a7d2606cbce3d904c8b90e591bb87818d744c5262ce017daae
```

This proves deterministic resolver closure for the recorded inputs. It does
not grant authority to future npm versions, registries, targets, or advisory
inventories.

## Permanent executable postconditions

The permanent tests do not freeze this historical base-to-head delta. They
independently enumerate current tracked npm surfaces, validate exact stable npm
SemVer, reject opaque manifest carriers, require canonical registry tarballs and
non-empty integrity for every non-root lock record, and apply every current
affected range to every governed head occurrence.

Primary anchors:

- `tests/test_root_npm_dependency_guards.py:31` — NanoID range families;
- `tests/test_root_npm_dependency_guards.py:897` — universal NanoID occurrence guard;
- `tests/test_root_npm_dependency_guards.py:867` — all-lock canonical provenance owner;
- `tests/test_frontend_dependency_guards.py:44` — current Brace Expansion outputs;
- `tests/test_frontend_dependency_guards.py:188` — five non-brace target table;
- `tests/test_frontend_dependency_guards.py:1250` — stable target postcondition helper.

Every boundary has an executable immediately-below `FAIL`, exact-floor `PASS`,
and selected-target `PASS`. PostCSS separately proves `8.5.22` fails,
`8.5.23` passes the advisory floor, and `8.5.26` passes the selected target.

## Conjunctive batch postcondition

```text
P_batch :=
  exact(scanner identity set) = D_batch
  AND exact(unique advisory set) = the 14 recorded GHSAs
  AND exact(tracked npm surface set) = the five recorded surfaces
  AND for every D in D_batch:
        A_D = F_cutoff(D) != empty
        AND exactly one authored I_R(D)
        AND every dependency delta is classified exactly once
        AND every governed head occurrence is comparable and outside every
            affected range, or D is executably absent
  AND both exact-base replays equal the working lock byte-for-byte
  AND no unapproved dependency, API, workflow, product, registry, or
      suppression movement exists
```

Partial success is forbidden. A zero-row final Trivy observation and npm audit
exit `0` corroborate this conjunction; neither scanner alone proves the surface
universe, causal delta partition, provenance, or merge readiness.

## Final local material observations

The following observations were taken after the byte-identical replay and clean
install, before the material commit:

- `npm ls` resolved exactly `brace-expansion@2.1.4` and `5.0.9`,
  `dompurify@3.4.13`, `js-yaml@4.3.1`, `nanoid@3.3.18`,
  `postcss@8.5.26`, `style-dictionary@5.4.4`, and `undici@7.29.0`;
- all seven `npm explain` paths remained inside their recorded current graph;
- `npm audit --json` exited `0` with zero info, low, moderate, high, or critical
  vulnerability keys;
- at `2026-08-21T06:52:15Z`, the recorded all-severity Trivy command exited `0`
  with zero finding rows and no suppression; its raw JSON SHA-256 is
  `8656d62130f03a6ae60141dea9b982497697c89e5c304b0a02dee2dbe03b6d7b`;
- frontend `test:ci` passed 765 tests with one intentional existing skip;
- the accessibility lane passed 41 tests with one intentional existing skip;
- Vite build, CSS smoke, Storybook build, and token parity passed;
- OpenAPI generation remained byte-identical at
  `8249a536f2ba4daab8570d37559a21476d2bfb391aeb9fceea736401653a9d78`
  for `frontend/src/api/openapi.json` and
  `808dd7a29df3e6b8e8ff98c684a82693cc9447c85b0c98af37dc854949048bfa`
  for `frontend/src/api/schema.ts`;
- the exact frontend container build passed on Node `24.18.1`; the exported
  manifest-list digest was
  `sha256:293e51b104385cf6f5ab391fdf355ccdfd84bb0ddf026721f529a1a7bfac2964`.

These are bounded local observations, not current-head GitHub CI or merge
readiness. Docker Desktop was stopped after the container gate to release local
resources.

## Validation contract and claim limits

Required final observations include:

- exact resolved outputs from `npm ls` and `npm explain`;
- `npm audit --json` exit `0`;
- the same all-severity Trivy command with exit `0` and zero rows, without
  `.trivyignore`, Rego waiver, or other suppression;
- focused guard tests, frontend tests, accessibility, build, CSS smoke,
  Storybook, token parity, Docker build, and byte-identical OpenAPI artifacts;
- repository narrow gates, all-files pre-commit, current-head CI, review
  disposition, mapping/seal, and freshness wait-window evidence.

Permissible conclusion after those gates pass:

> At the exact material head, the governed repository occurrences of the exact
> seven npm identities are outside the exact 14-advisory cutoff across the exact
> five tracked npm surfaces, and the recorded resolver transaction is
> deterministic.

This must not be shortened to “all vulnerabilities fixed,” “frontend safe,”
“repository secure,” “zero vulnerabilities,” or “Dependabot closed.” A final
Trivy zero-row result is only a zero-row observation under the recorded command,
tool, DB, time, and head. Provider refresh is reported separately after merge.

## Rollback and stop conditions

Before merge, rollback restores the exact-base manifest, lock, guards, and
evidence together and reruns `npm ci`. After merge, rollback requires a normal
revert PR for the complete conjunctive transaction; partial identity rollback
is forbidden because it destroys `P_batch`.

Stop and request a new operator decision if the scanner identity set or target
advisory truth changes, a selected release becomes missing/deprecated/noncanonical,
Node or registry configuration drifts, npm adds/removes a package or produces an
unclassified delta, either replay differs, a new parser/carrier mechanism is
needed, a suppression becomes necessary, or OpenAPI-generated bytes change.

<!-- markdownlint-enable MD013 MD024 MD031 MD032 -->

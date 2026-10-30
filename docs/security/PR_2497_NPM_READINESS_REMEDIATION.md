# PR #2497: bounded NPM readiness remediation

## Authority and outcome boundary

This is the single NPM evidence owner for the two-identity readiness correction in
PR #2497. The operator's direct request to finish this PR completely and the
coordinator's accepted eight-path handoff authorize this bounded implementation.
Candidate policy text, this document, scanners and role reports do not create
that authority. The Python seven-package unit and Alertmanager/Prometheus unit
retain their separate owners. There is no npm-wide update or suppression change.

The immutable CI Trivy cohort contains DOMPurify advisories
GHSA-cg2g-xh64-v4q7 and GHSA-mrv2-3pqr-j5jr, and Zod
CVE-2023-54404 / GHSA-mrhx-c7xc-m3w5: three findings, two identities.
The broader npm audit below is a separate diagnostic inventory.

The retained Trivy 0.74.0 SARIF is code-scanning analysis `2018346343`, created
2026-10-24 07:54:35 UTC, with SHA-256
`01c7ed50794dbec8bf87a5fc62365780d0d753b836b5a2eab47a6035e3da34aa`.
Its analysis commit `88f97255637129b667e800144b817dffe951dd89` is the synthetic
PR merge, not the authored head. The authenticated
[security-scan job](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/40075354543/job/120819237277)
binds the run to authored head `87c1d0930158c24d57b6d8d70df44fa90db1a677`.
The original SARIF reports exactly the three findings above at the original
frontend lock's DOMPurify 3.4.13 and Zod 3.25.76 occurrences. Candidate source
hashes below describe different, locally validated material.

| Identity/action | Owning source change | Resolved change | Classification |
| --- | --- | --- | --- |
| `npm:dompurify` | exact override `3.4.13` → `3.4.17` | `3.4.13` → `3.4.17` | Authored security replacement |
| `npm:zod` | dependency `^3.23.8` → `^4.6.7` | `3.25.76` → `4.6.7` | Authored security replacement |
| `@hookform/resolvers` | dependency `^3.9.0` → `^5.2.2` | `3.10.0` → `5.2.2` | Separately authored compatibility companion |

Resolver 5.2.1 is the corrected minimum for the non-raw input/output flow used
here. Selected 5.2.2 also corrects the `raw: true` declaration; runtime JavaScript
matches 5.2.1. The application keeps the default parsed-output path. Its peer
requirement `react-hook-form ^7.55.0` is satisfied by unchanged 7.79.0.
This companion is not a third security identity or an inferred solver action.

Local target postconditions and focused validation passed on the material
recorded below. Complete current-head CI, coverage, review, whole-PR narrow gates,
seal and merge readiness remain coordinator-owned and are not asserted here.
The candidate frontend npm audit still exits **1** with ten other rows.

## Exact source universe and material

Base: `48d36c220ff58dec82450da66ef0599c6da71787`.
Published head before these uncommitted changes:
`87c1d0930158c24d57b6d8d70df44fa90db1a677`.
Both revisions have the same original NPM surfaces. Independent tracked-path
enumeration found the following complete five-source universe at base and
candidate; no source was added or removed. This count describes this snapshot,
not a permanent limit on future repository surfaces.

| Source | Base SHA-256 | Candidate SHA-256 |
| --- | --- | --- |
| `frontend/package-lock.json` | `6227a413247ffb9d38491c64ee270de18f44bfebc1bd0d4d91dc37da24278645` | `c473f85f249c93345e2b2ad2b606d488ffc658e6a74ccab1c2bd83f01c201ad7` |
| `frontend/package.json` | `c52c2d3870db4787d27abff663fd46e48a12f9922390825c5ed25916acbd7bba` | `376169b41d908889510f419b622d99e188f571eba8ee78a67af227f5e078ddd9` |
| `package-lock.json` | `9fe0630047798a9947926f903b2b4114f5b0ccc188880dbb2c9463ea28723419` | `9fe0630047798a9947926f903b2b4114f5b0ccc188880dbb2c9463ea28723419` |
| `package.json` | `8181e4f5b7a68c0d1219c1875a616c57ba516ac67fa272b9c01d2d1e1cbbbcbe` | `8181e4f5b7a68c0d1219c1875a616c57ba516ac67fa272b9c01d2d1e1cbbbcbe` |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` |

DOMPurify has one exact frontend manifest override and one frontend lock node
`node_modules/dompurify`; Zod has one frontend dependency and one frontend lock
node `node_modules/zod`. The other three sources have no occurrence of either.
All direct, nested and cross-lock occurrences remain in the discovery contract.
The transition document and independent resolver replay own historical equality;
permanent tests do not freeze the selected version for future authorized updates.

Evidence: `frontend/package.json:54`, `frontend/package.json:97`,
`tests/test_frontend_dependency_guards.py:2086`.
The guard independently discovers tracked surfaces, validates every lock record
against the existing opaque-inner-graph rules, canonical source/SRI and duplicate
JSON rules, then validates the complete native npm virtual graph. A DOM exact
owner and Zod stable caret/root-lock membership are separate from universal
advisory safety. A safe nested or other-root transitive occurrence may have its
own version and parent constraint. Missing owners, opaque/aliased carriers,
unsafe occurrences, unsupported provenance and peer conflicts fail closed.

## Finite advisory inventory and per-advisory postcondition

Cutoff: **2026-10-24 09:39:11 UTC**. Named primary inputs are the complete
GitHub reviewed-advisory API queries for npm DOMPurify and Zod, plus their linked
upstream releases/source. The two successful queries had no pagination Link:
DOMPurify at 09:34:02 UTC returned 34 records; Zod at 09:34:01 returned two.
Raw response SHA-256 values:

- DOMPurify: `3a3afcc9bc17c4aea25cd8f44e4099c248dafdedc059ca7c7b2cce085c35723e`.
- Zod: `d429f298b4688c906f4aed420e790ebf03517d1806e5c960299828c4c827b487`.

`F_cutoff` is **36 advisory identities / 40 intervals**. The non-empty applicable
subset `A` is exactly six: five DOMPurify findings at 3.4.13 and one Zod finding
at 3.25.76. Each other row is non-applicable at base because that comparable
base version lies outside every listed interval; it stays in the universal
candidate postcondition. “Outside all” below means every actual candidate
occurrence is comparable and outside every interval of that row, including
withdrawn and base-non-applicable rows. It does not mean future or all possible
vulnerabilities are absent.

| Identity | Primary advisory | Alias | Raw affected interval(s) | Base disposition | Candidate |
| --- | --- | --- | --- | --- | --- |
| dompurify | [GHSA-cg2g-xh64-v4q7](https://github.com/advisories/GHSA-cg2g-xh64-v4q7) | None recorded | `>= 3.4.4, <= 3.4.16` | Affected | Outside all |
| dompurify | [GHSA-mrv2-3pqr-j5jr](https://github.com/advisories/GHSA-mrv2-3pqr-j5jr) | None recorded | `<= 3.4.16` | Affected | Outside all |
| dompurify | [GHSA-c6gr-qvv4-5v3f](https://github.com/advisories/GHSA-c6gr-qvv4-5v3f) | None recorded | `<= 3.4.16` | Affected | Outside all |
| dompurify | [GHSA-6688-9rhm-gjv2](https://github.com/advisories/GHSA-6688-9rhm-gjv2) | None recorded | `<= 3.4.15` | Affected | Outside all |
| dompurify | [GHSA-p98j-92pf-mc4p](https://github.com/advisories/GHSA-p98j-92pf-mc4p) | None recorded | `>= 3.4.13, <= 3.4.15` | Affected | Outside all |
| dompurify | [GHSA-55q2-fjhq-7xh7](https://github.com/advisories/GHSA-55q2-fjhq-7xh7) | None recorded | `<= 3.4.12` | Outside every listed interval | Outside all |
| dompurify | [GHSA-jxrp-r7gx-q4j8](https://github.com/advisories/GHSA-jxrp-r7gx-q4j8) | None recorded | `<= 3.4.11` | Outside every listed interval; withdrawn 2026-10-02T22:43:11Z | Outside all |
| dompurify | [GHSA-c2j3-45gr-mqc4](https://github.com/advisories/GHSA-c2j3-45gr-mqc4) | CVE-2026-66010 | `<= 3.4.11` | Outside every listed interval | Outside all |
| dompurify | [GHSA-cmwh-pvxp-8882](https://github.com/advisories/GHSA-cmwh-pvxp-8882) | CVE-2026-65898 | `<= 3.4.10` | Outside every listed interval | Outside all |
| dompurify | [GHSA-vxr8-fq34-vvx9](https://github.com/advisories/GHSA-vxr8-fq34-vvx9) | CVE-2026-65899 | `< 3.4.9` | Outside every listed interval | Outside all |
| dompurify | [GHSA-gvmj-g25r-r7wr](https://github.com/advisories/GHSA-gvmj-g25r-r7wr) | CVE-2026-65900 | `>= 3.0.0, <= 3.4.7` | Outside every listed interval | Outside all |
| dompurify | [GHSA-rp9w-3fw7-7cwq](https://github.com/advisories/GHSA-rp9w-3fw7-7cwq) | CVE-2026-49978 | `<= 3.4.6` | Outside every listed interval | Outside all |
| dompurify | [GHSA-x4vx-rjvf-j5p4](https://github.com/advisories/GHSA-x4vx-rjvf-j5p4) | CVE-2026-65901 | `<= 3.4.6` | Outside every listed interval | Outside all |
| dompurify | [GHSA-76mc-f452-cxcm](https://github.com/advisories/GHSA-76mc-f452-cxcm) | CVE-2026-65902 | `< 3.4.7` | Outside every listed interval | Outside all |
| dompurify | [GHSA-hpcv-96wg-7vj8](https://github.com/advisories/GHSA-hpcv-96wg-7vj8) | CVE-2026-49458 | `<= 3.4.5` | Outside every listed interval | Outside all |
| dompurify | [GHSA-r47g-fvhr-h676](https://github.com/advisories/GHSA-r47g-fvhr-h676) | CVE-2026-49459 | `<= 3.4.5` | Outside every listed interval | Outside all |
| dompurify | [GHSA-87xg-pxx2-7hvx](https://github.com/advisories/GHSA-87xg-pxx2-7hvx) | CVE-2026-47423 | `= 3.4.4` | Outside every listed interval | Outside all |
| dompurify | [GHSA-h7mw-gpvr-xq4m](https://github.com/advisories/GHSA-h7mw-gpvr-xq4m) | CVE-2026-41240 | `< 3.4.0` | Outside every listed interval | Outside all |
| dompurify | [GHSA-crv5-9vww-q3g8](https://github.com/advisories/GHSA-crv5-9vww-q3g8) | CVE-2026-41239 | `>= 1.0.10, < 3.4.0` | Outside every listed interval | Outside all |
| dompurify | [GHSA-v9jr-rg53-9pgp](https://github.com/advisories/GHSA-v9jr-rg53-9pgp) | CVE-2026-41238 | `>= 3.0.1, < 3.4.0` | Outside every listed interval | Outside all |
| dompurify | [GHSA-39q2-94rc-95cp](https://github.com/advisories/GHSA-39q2-94rc-95cp) | CVE-2026-65903 | `<= 3.3.3` | Outside every listed interval | Outside all |
| dompurify | [GHSA-cjmm-f4jc-qw8r](https://github.com/advisories/GHSA-cjmm-f4jc-qw8r) | CVE-2026-65912 | `<= 3.3.1` | Outside every listed interval | Outside all |
| dompurify | [GHSA-cj63-jhhr-wcxv](https://github.com/advisories/GHSA-cj63-jhhr-wcxv) | CVE-2026-65913 | `<= 3.3.1` | Outside every listed interval | Outside all |
| dompurify | [GHSA-h8r8-wccr-v5f2](https://github.com/advisories/GHSA-h8r8-wccr-v5f2) | CVE-2026-65914 | `< 3.3.2` | Outside every listed interval | Outside all |
| dompurify | [GHSA-v2wj-7wpq-c8vv](https://github.com/advisories/GHSA-v2wj-7wpq-c8vv) | CVE-2026-0540 | `>= 3.1.3, <= 3.3.1`; `>= 2.5.3, <= 2.5.8` | Outside every listed interval | Outside all |
| dompurify | [GHSA-v8jm-5vwx-cfxm](https://github.com/advisories/GHSA-v8jm-5vwx-cfxm) | CVE-2025-15599 | `>= 3.1.3, < 3.2.7`; `>= 2.5.3, <= 2.5.8` | Outside every listed interval | Outside all |
| dompurify | [GHSA-vhxf-7vqr-mrjg](https://github.com/advisories/GHSA-vhxf-7vqr-mrjg) | CVE-2025-26791 | `< 3.2.4` | Outside every listed interval | Outside all |
| dompurify | [GHSA-p3vf-v8qc-cwcr](https://github.com/advisories/GHSA-p3vf-v8qc-cwcr) | CVE-2024-48910 | `< 2.4.2` | Outside every listed interval | Outside all |
| dompurify | [GHSA-gx9m-whjm-85jf](https://github.com/advisories/GHSA-gx9m-whjm-85jf) | CVE-2024-47875 | `< 2.5.0`; `>= 3.0.0, < 3.1.3` | Outside every listed interval | Outside all |
| dompurify | [GHSA-mmhx-hmjr-r674](https://github.com/advisories/GHSA-mmhx-hmjr-r674) | CVE-2024-45801 | `< 2.5.4`; `>= 3.0.0, < 3.1.3` | Outside every listed interval | Outside all |
| dompurify | [GHSA-8hgg-xxm5-3873](https://github.com/advisories/GHSA-8hgg-xxm5-3873) | CVE-2019-25155 | `< 1.0.11` | Outside every listed interval | Outside all |
| dompurify | [GHSA-63q7-h895-m982](https://github.com/advisories/GHSA-63q7-h895-m982) | CVE-2020-26870 | `< 2.0.17` | Outside every listed interval | Outside all |
| dompurify | [GHSA-mjjq-c88q-qhr6](https://github.com/advisories/GHSA-mjjq-c88q-qhr6) | None recorded | `< 2.0.7` | Outside every listed interval | Outside all |
| dompurify | [GHSA-chqj-j4fh-rw7m](https://github.com/advisories/GHSA-chqj-j4fh-rw7m) | CVE-2019-16728 | `< 2.0.3` | Outside every listed interval | Outside all |
| zod | [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) | CVE-2023-54404 | `< 4.6.6` | Affected | Outside all |
| zod | [GHSA-m95q-7qp3-xv42](https://github.com/advisories/GHSA-m95q-7qp3-xv42) | CVE-2023-4316 | `<= 3.22.2` | Outside every listed interval | Outside all |

Native npm-semver 7.8.1 evaluates these retained ranges. Raw `= 3.4.4` is exact
npm equality; the existing finite guard representation `==3.4.4` has explicit
native below/equal/above witnesses 3.4.3, 3.4.4 and 3.4.5. This adds no generic
npm-to-PEP440 converter. All 40 intervals have independent affected/unaffected
controls that exercise the interval without the current security floor masking
it. Omission controls include disjoint, withdrawn and base-non-applicable rows.
Evidence: `tests/test_frontend_dependency_guards.py:348`,
`tests/test_frontend_dependency_guards.py:388`,
`tests/test_frontend_dependency_guards.py:4670`.

Some advisory descriptions retain historical “unfixed/latest 3.4.16” wording;
current structured ranges and 3.4.17 fixes are corroborated by the
[DOMPurify release](https://github.com/cure53/DOMPurify/releases/tag/3.4.17) and matching published `purify.ts` bytes.
Different scanner severities do not change affected-range membership.
The [Zod release](https://github.com/colinhacks/zod/releases/tag/v4.6.7) and published schema source retain the bounded-array
fix. Its actual array limit is necessary: updating an unbounded schema alone
does not enable early rejection.

## Published package provenance and compatibility

Registry SHA-512 values match each selected lock entry and the independently
fetched tarball bytes. Tarball SHA-256 values are:

- DOMPurify 3.4.17: `056cbdae276897208b88c21d1d779adfa09ad7be488a2f510a28e900d3bbffe7`.
- Zod 4.6.7: `84efd155bed93270286e793fc951be270b536cbd5b0eeb111f0fa3967201d698`.
- Resolver 5.2.2: `f4c24c8d78c4e62c9b7e17599f1ac01f48419c16f9921dc62324e2a79c440a00`.

Zod 4.6.7 npm gitHead and official release both identify
`b500a2ee95134f81d74da7911d7378dd2853d042`. The original and rewritten 4.6.6
commit observations both returned HTTP 200 and the same Git tree; neither is
reported unavailable. Comparing published 4.6.6/4.6.7 archives found 836 of 840
members equal and only four version/package metadata files changed. Choosing
4.6.7 records clearer release continuity, not evidence of a compromised 4.6.6
npm artifact. The [resolver 5.2.1 release](https://github.com/react-hook-form/resolvers/releases/tag/v5.2.1) documents its corrected
input/output handling; 5.2.2 is the selected patch-complete companion.

After normal installation, all regular files of the three selected packages
matched the fetched archives: DOMPurify 24, Zod 840, resolver 399. Package source
continuity, registry integrity and installed-payload equality do not claim
signature/attestation validation, an independently reproducible upstream build,
or absence of malicious code.

## Canonical independent resolution and complete delta

Two independent copies, A and B, started from the exact five base sources,
without `node_modules`. Each had its own empty HOME, cache and npm user/global
configuration. Only the three owning inputs above were authored. Actual tools:
Node **24.18.1**, npm **11.16.0**. The canonical repository wrapper was used;
its name alone is not tool-version proof. No host credentials/configuration
were copied into these environments.

The following command was executed once per copy; paths here are deliberately
normalized to repository-relative owned artifacts. The local receipts retain
the exact absolute argv, sanitized environment, timestamps, exit status and logs.
`<copy>` is independently `A` or `B`; `$W` is the lane repository path.

```bash
scripts/frontend_npm.sh --prefix "$W/artifacts/orchestration/stabilization/npm2497-implementation/replay-<copy>/source/frontend" install --package-lock-only --ignore-scripts --strict-peer-deps --no-audit --no-fund --save-prefix=^ zod@4.6.7 @hookform/resolvers@5.2.2 --registry=https://registry.npmjs.org/ --userconfig="$W/artifacts/orchestration/stabilization/npm2497-implementation/replay-<copy>/config/user.npmrc" --globalconfig="$W/artifacts/orchestration/stabilization/npm2497-implementation/replay-<copy>/config/global.npmrc"
```

Both commands exited 0 (A 5.005 s; B 3.741 s), with raw stdout:

```text
up to date in 4s
up to date in 4s
```

The complete five-source outputs are byte-identical, including entire manifest
and lock bytes. The adopted files are those exact outputs. There are exactly
four changed lock records: root input projection and the three selected nodes.
The JSON below is the complete changed-field projection: omitted keys/records
are unchanged, no node is added/removed, and all non-`packages` lock fields are
unchanged. `/` paths are JSON-pointer field paths within the named record.
The DOMPurify override lives only in the owning package manifest, which npm
does not duplicate into the root lock record.

```json
[
  {
    "record": "",
    "classification": "owning_input_projection",
    "changes": [
      {
        "path": "/dependencies/@hookform~1resolvers",
        "operation": "replace",
        "before": "^3.9.0",
        "after": "^5.2.2"
      },
      {
        "path": "/dependencies/zod",
        "operation": "replace",
        "before": "^3.23.8",
        "after": "^4.6.7"
      }
    ]
  },
  {
    "record": "node_modules/@hookform/resolvers",
    "classification": "I_compatibility",
    "changes": [
      {
        "path": "/dependencies",
        "operation": "add",
        "after": {
          "@standard-schema/utils": "^0.3.0"
        }
      },
      {
        "path": "/integrity",
        "operation": "replace",
        "before": "sha512-79Dv+3mDF7i+2ajj7SkypSKHhl1cbln1OGavqrsF7p6mbUv11xpqpacPsGDCTRvCSjEEIez2ef1NveSVL3b0Ag==",
        "after": "sha512-A/IxlMLShx3KjV/HeTcTfaMxdwy690+L/ZADoeaTltLx+CVuzkeVIPuybK3jrRfw7YZnmdKsVVHAlEPIAEUNlA=="
      },
      {
        "path": "/peerDependencies/react-hook-form",
        "operation": "replace",
        "before": "^7.0.0",
        "after": "^7.55.0"
      },
      {
        "path": "/resolved",
        "operation": "replace",
        "before": "https://registry.npmjs.org/@hookform/resolvers/-/resolvers-3.10.0.tgz",
        "after": "https://registry.npmjs.org/@hookform/resolvers/-/resolvers-5.2.2.tgz"
      },
      {
        "path": "/version",
        "operation": "replace",
        "before": "3.10.0",
        "after": "5.2.2"
      }
    ]
  },
  {
    "record": "node_modules/dompurify",
    "classification": "I_R_security",
    "changes": [
      {
        "path": "/integrity",
        "operation": "replace",
        "before": "sha512-2vmYIoqjze2d+kakP8S/nS5shfsl587kzwEjcGlTdiksUVgFHnFCsLYDVj/JNqJVOQZGSYBTmuycv0PodwmnMQ==",
        "after": "sha512-B/pSlYVHQ58kqISD/yDjuJ1yfzI34m1gF4lAod2bwSRhiN4K5Cl3H8Af7hqB2PmTL911tdEudnnXn5FnhRoz0w=="
      },
      {
        "path": "/resolved",
        "operation": "replace",
        "before": "https://registry.npmjs.org/dompurify/-/dompurify-3.4.13.tgz",
        "after": "https://registry.npmjs.org/dompurify/-/dompurify-3.4.17.tgz"
      },
      {
        "path": "/version",
        "operation": "replace",
        "before": "3.4.13",
        "after": "3.4.17"
      }
    ]
  },
  {
    "record": "node_modules/zod",
    "classification": "I_R_security",
    "changes": [
      {
        "path": "/integrity",
        "operation": "replace",
        "before": "sha512-gzUt/qt81nXsFGKIFcC3YnfEAx5NkunCfnDlvuBSSFS02bcXu4Lmea0AFIUwbLWxWPx3d9p8S5QoaujKcNQxcQ==",
        "after": "sha512-g8W2D2kU6a8untc053fX1uVBKzM7yqAxW/3zwk83+6RyF2+SKOuV+c0wBDhUwzV1PaGapmZH+rmcUzPf+3CGwg=="
      },
      {
        "path": "/resolved",
        "operation": "replace",
        "before": "https://registry.npmjs.org/zod/-/zod-3.25.76.tgz",
        "after": "https://registry.npmjs.org/zod/-/zod-4.6.7.tgz"
      },
      {
        "path": "/version",
        "operation": "replace",
        "before": "3.25.76",
        "after": "4.6.7"
      }
    ]
  }
]
```

Thus the two security node replacements belong to `I_R`; the resolver node is
explicit `I_compatibility`; root changes project those inputs. There are no
additional `C_R` node transitions. The resolver's added dependency edge to
already-existing `@standard-schema/utils 0.3.0` and strengthened RHF peer edge
are included above, not hidden upgrades. No manual lock edits or peer bypasses
were used. Replay receipt SHA-256: `4fac65f0375bd45c53aedd9ddf77af7787ce954b9e86512d3284bb391bf98ed6`.

## Consumer behavior and native proof

`frontend/src/pages/NutritionSetup/schema.ts:23` retains existing numeric bounds
and field-local visible error messages. `diet_flags` now uses the unchanged
choice list's length as its maximum, then defaults to `[]`. This is the existing
ten-checkbox input shape, not backend nutrition/entitlement truth. Empty,
omitted, all-ten and valid arrays of at most ten entries remain accepted,
including duplicates that the old schema permitted. Checkbox uniqueness remains
its existing separate UI behavior. No DTO/OpenAPI, visual flow or calculation
rule changes.

`frontend/src/pages/NutritionSetup/schema.ts:39` separates `z.input` and `z.output`.
Its single helper returns actual parsed data or undefined.
`frontend/src/pages/NutritionSetup/SetupForm.tsx:42` uses
`useForm<Input, unknown, Output>` with the real non-raw resolver.
`frontend/src/pages/NutritionSetup/index.tsx:82` consumes parsed saved values.
The removed boolean predicate incorrectly narrowed unchanged raw data to output
when `.default([])` had normalized a separate parsed object.

A real page-restoration test proves normalized `diet_flags: []` reaches both
ResultView hooks, the original saved object retains its omitted field and unknown
keys, and invalid saved data returns to the form. A separate submission test
caught a newly introduced parse-clone identity change (two hook input identities
instead of one). The functional state setter now reuses only output already
held from the parser/resolver when it is the same object as saved settings;
first raw restoration still parses. The test now observes one parsed-output
identity, avoiding duplicate identity-triggered requests without a new effect
dependency or a production cast. Evidence:
`frontend/src/pages/NutritionSetup/__tests__/SetupForm.test.tsx:188`.

The real installed Zod path rejects an eleven-entry invalid array with `too_big`
and **zero element reads**. A one-entry invalid enum control is read and rejected.
This is a bounded native witness, not an unbounded exhaustion test or universal
resource-safety promise. Form checks retain comma/dot decimal parsing,
fractional-age message `Expected integer, received float`, valid/default submits,
checkbox behavior, and empty/malformed/non-finite/out-of-range rejection.

The installed DOMPurify package was exercised with the same jsdom 29.1.1 and
Node runtime as a separately integrity-verified 3.4.13 baseline. Three inert
baseline-sensitive witnesses changed from vulnerable behavior to rejection:
attached shadow/template expression, detached IN_PLACE subtree attribute, and
XHTML SMIL `attributeName`. Exact benign HTML survives in both. Package JavaScript
runs, but attacker handlers/scripts are not executed; intercepted network
transports observed zero calls. This is not kernel network isolation. No direct
application DOMPurify/jsPDF/html2canvas consumer was found, so these results are
package-level proof, not application-wide XSS or PDF coverage.

## Validation and retained diagnostics

All local commands ran sequentially on the authorized Mac fallback after memory
and disk checks, with owned configuration and a 2048 MiB Node heap cap. Vitest
used one worker and no file parallelism. No other lane's processes or files were
modified. The controller records source hashes before/after each gate; later
UI-only repairs do not relabel earlier lock/guard evidence as a new whole-tree
run. Adding this evidence document does not change native inputs. Final whole-PR
local/current-head gates remain separate.

| Command (paths normalized as described above) | Exit | Observed result |
| --- | --- | --- |
| `scripts/frontend_npm.sh --prefix frontend ci --strict-peer-deps --no-audit --no-fund` with owned empty configs/registry | 0 | Normal installation, 27.17 s; lifecycle enabled |
| `scripts/frontend_npm.sh --prefix frontend ls --all --json --include=prod --include=dev --include=optional --include=peer --legacy-peer-deps=false --strict-peer-deps=true` | 0 | Actual installed graph, no problems; DOM 3.4.17, Zod 4.6.7, resolver 5.2.2, RHF 7.79.0 |
| Repo Python `-m pytest -q tests/test_frontend_dependency_guards.py --maxfail=20 --junitxml=<owned-report>` | 0 | 461 tests, zero failures/errors/skips; full native owning module |
| `scripts/frontend_npm.sh --prefix frontend run typecheck` | 0 | TypeScript check |
| `scripts/frontend_npm.sh --prefix frontend run test:precommit -- --maxWorkers=1 --no-file-parallelism src/pages/NutritionSetup/__tests__/SetupForm.test.tsx src/pages/NutritionSetup/__tests__/NutritionSetupPage.test.tsx src/pages/NutritionSetup/__tests__/hooks.test.tsx src/api/__tests__/thin-client-guards.test.ts` | 0 | 4 files / 33 tests passed after final identity repair |
| `scripts/frontend_npm.sh --prefix frontend run build` | 0 | Final TypeScript + Vite build, 3.65 s |
| Native Node `artifacts/orchestration/stabilization/npm2497-implementation/native-probes/dompurify.cjs` | 0 | Three baseline-sensitive inert checks plus benign control |

The selected Python guard also passed Black with the current approved hook
source, Ruff, and `git diff --check`. The owner document passed
`scripts/ci/check_docs_phase1_gates.py --files docs/security/PR_2497_NPM_READINESS_REMEDIATION.md`.
These focused formatting/document checks do not substitute for the coordinator's
terminal all-files pre-commit pass.

Raw failures remain in local evidence: initial test TypeScript syntax/lib
mismatch; a shared-guard diagnostic mismatch repaired by preserving the existing
malformed-record message; an over-strong DOM probe assertion about text adjacent
to a removed template expression (corrected while retaining an independent benign
control); and the genuine duplicate submission identity regression, red before
the runtime fix and green after it. No production invariant, test skip,
security suppression or global threshold was weakened to obtain these results.

The final build retains `INEFFECTIVE_DYNAMIC_IMPORT` for `src/api/client.ts`
and the >500 kB chunk warning. Both warning families appear in the successful
[existing same-head Frontend CI job](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/40075354518/job/120817407225).
The retained baseline log is truncated but contains both raw warning lines.
This proves earlier presence of those warning classes, not identical bundle size.
No threshold or import-flow change suppresses them.

Complete audits were repeated at 2026-10-24 12:26 UTC using canonical wrapper,
owned empty configs and `audit --json --package-lock-only --ignore-scripts`.
Root exits 0 with zero rows. Frontend exits 1 with six moderate, three high and
one critical row. The earlier full diagnostic at 08:59 UTC had twelve rows and
30 unique advisory IDs; the complete original report is retained, not filtered.

| Original package/effect row | Original severity | Candidate diagnostic |
| --- | --- | --- |
| `@vitest/coverage-v8` | moderate | Remains: moderate |
| `@vitest/mocker` | moderate | Remains: moderate |
| `dompurify` | critical | Absent from candidate report |
| `postcss-nested` | moderate | Remains: moderate |
| `postcss-selector-parser` | moderate | Remains: moderate |
| `source-map-js` | high | Remains: high |
| `storybook` | critical | Remains: critical |
| `tailwindcss` | moderate | Remains: moderate |
| `undici` | high | Remains: high |
| `vite` | high | Remains: high |
| `vitest` | moderate | Remains: moderate |
| `zod` | high | Absent from candidate report |

Neither absence of the two targets nor the narrower original Trivy cohort
accepts, suppresses, remediates or declares non-applicable the other ten rows.
The coordinator must assess any remaining required-gate failure under its actual
owner; this unit does not claim full npm-audit PASS or whole-PR readiness.
Candidate frontend raw report SHA-256:
`7e939fffe78ba8be220c767621b22315b0bf996996d27f3b9d2d525454f9a349`.

Ignored local evidence is retained under
`artifacts/orchestration/stabilization/npm2497-implementation/`: replay A/B,
complete original/resolved graph delta, normal install/payload comparison,
material-bound gate logs, native probes, baseline warnings and full audit JSON.
These artifacts are not committed or runtime authority. Exact local source
hashes and command receipts support handoff; current published-head CI must
still be obtained after integration.

## Risks and rollback

The focused native checks cover this flow and finite advisory snapshot. They
do not prove all Zod APIs, every browser engine, product-wide sanitization or
future advisories. Follow-up findings inside the active dependency/consumer
surface must be addressed before readiness. There is no new permanent exception,
registry, provider, suppression, bypass or production deployment in this unit.

Rollback is a reviewed revert of the coherent dependency and consumer correction.
Returning old package versions restores known findings and requires an explicit
owner decision. Do not automatically downgrade dependencies, rewrite history or
deploy production. The final PR review and merge process remain unchanged.

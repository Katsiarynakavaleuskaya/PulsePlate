<!-- markdownlint-disable MD013 MD024 MD031 MD032 -->

# `image-size`, `nanoid`, and React Router atomic Trivy remediation class

## Authority boundary and bounded claim

The runtime packet records a direct operator instruction on 2026-08-08 to
handle this exact same-PR npm batch. The instruction was issued outside the
candidate diff and authorizes this exact policy transition and bounded material;
it grants no general or future batch authority. This document memorializes
receipt of that instruction; it does not authenticate the sender or infer
authority from Git, Trivy, CI, a test, an agent, or the candidate policy text.
The `dependency-remediation-admission:v2` policy added by this candidate has
prospective repository effect only after merge and cannot self-authorize this
batch.

This is one npm-ecosystem batch with the exact finite identity set:

```text
D_batch = {
  npm:image-size,
  npm:nanoid,
  npm:react-router
}
```

The bounded claim is only that the declared material transitions establish the
conjunction of the three postconditions below over the exact five governed npm
surfaces. It is not a full repository vulnerability audit, a current-head
scanner result, or a readiness claim.

## Immutable scanner snapshot and identity derivation

The one immutable scanner snapshot that derives the whole batch is Docker Build
and Push run `31258531222`, failed `security-scan` job `93106014446`, and Trivy
code-scanning analysis `1589834230`. The terminal analysis was created
`2026-08-08T13:04:44Z` by Trivy `0.72.0`, category
`.github/workflows/build.yml:security-scan`, with no analysis error or warning.
It is bound to pull-request merge commit
`0090859bf3a2c58ac8683cd807ebe98cdbb00a8e`, whose parents are the exact base
`ad179450108ab352fe31e6687a33185b99b52127` and PR head
`a2ba1867a829cd6159e2e4683f790b4f89ee666d`. All five governed npm surface
blobs are byte-identical between those parents. The GitHub SARIF response has
SHA-256 (eight groups, concatenated)
`8c2546c9 8ceacacb 6e88759f facf418b d260e48c 2d0e2291 cd0ace35 bd5e72b4`.
The SARIF reports exactly four HIGH results and exactly these three npm
identities:

| Identity | Exact result | Selected target |
| --- | --- | --- |
| `npm:image-size` | `CVE-2025-71329` and `CVE-2025-71330`, HIGH, `package-lock.json`, installed `1.2.1`, no fixed release in the SARIF | remove the unused `pptxgenjs` carrier and the executable identity |
| `npm:nanoid` | `CVE-2026-67214`, HIGH, `package-lock.json`, installed `5.1.7`, fixed `3.3.16, 5.1.16` | root `5.1.16`; reconcile the governed frontend occurrence against its complete same-identity inventory at `3.3.17` |
| `npm:react-router` | `GHSA-qwww-vcr4-c8h2`, HIGH, `frontend/package-lock.json`, installed `7.18.1`, fixed `7.18.2, 8.3.0` | `react-router` and its direct carrier `react-router-dom` at `7.18.2` |

The `npm:image-size` subordinate evidence owner is
`docs/security/IMAGE_SIZE_TRANSITIVE_REMOVAL_REMEDIATION_CLASS.md`. The exact
scanner-derived identity set is therefore all-and-only
`{npm:image-size, npm:nanoid, npm:react-router}`; no identity was selected from a
second scan or added manually.

## Per-identity advisory inventories

Each identity keeps its own finite `F_cutoff`; the scanner-derived identity set
does not collapse advisory variants into separate dependency identities:

- `npm:image-size`: `CVE-2025-71329` and `CVE-2025-71330`, both reported by the
  immutable Trivy SARIF against base `1.2.1`, with affected releases through
  `2.0.2` and no patched release in that snapshot. Both are in `A`.
- `npm:nanoid`: `CVE-2026-67214` / `GHSA-28wg-ghj8-5hjv` affects `<3.3.16` and
  `>=4,<5.1.16`; `CVE-2026-67213` / `GHSA-2v37-7h3g-55p8` affects `<3.3.17`
  and `>=4,<5.1.6`. The first is the triggering Trivy result; the second is a
  same-identity current GitHub/npm advisory reconciled at the same cutoff.
  Governed base occurrences `5.1.7` and `3.3.12` provide affected comparable
  witnesses, so both candidates are in `A`. Targets `5.1.16` and `3.3.17` are
  outside both affected range families.
- `npm:react-router`: `GHSA-qwww-vcr4-c8h2` affects `>=7.12,<7.18.2` and
  `>=8,<8.3.0`. Governed base `7.18.1` is the affected witness; head target
  `7.18.2` is outside both ranges.

No candidate in these inventories is dispositioned as base-non-applicable. The
long-lived guard nevertheless evaluates every installed head occurrence against
every reconciled affected range so a later head cannot move from one known
range into another and create a false remediation claim.

## Exact surface universe

The exact base is
`ad179450108ab352fe31e6687a33185b99b52127`. Tracked/index enumeration must
equal this five-surface set at base and head:

1. `package.json`;
2. `package-lock.json`;
3. `frontend/package.json`;
4. `frontend/package-lock.json`;
5. `scripts/business_collateral/package.json`.

| Surface | Exact-base SHA-256 | Integrated-head SHA-256 |
| --- | --- | --- |
| `package.json` | `1da85e56a5cdcc39fdf1136548aa2815b357bed5f9ccd85399e42c9cbd867ca5` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` |
| `package-lock.json` | `6828456d38086a1924cc0e3c54b4a6d1b001acc686c4cfb07691319ee3759759` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` |
| `frontend/package.json` | `97bd09c0eec4fd15a582dd6a3fc96f02b29610e7955166796421f3cea703f309` | `681130ffb4dcf434b3d35f9ba84de41c13771de99f411b016e73c31b3f682698` |
| `frontend/package-lock.json` | `41d793fe5905be75656cffc03fd03f9c8371ecf1f8f60aa8ee979e789efe5885` | `2dc7084e209ab24b824f64fee88e63abc09e8abeb58301148405bd2fd4300aa9` |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` |

The complete allowed dependency JSON delta partition is:

- `package.json`: remove `dependencies/pptxgenjs` and
  `scripts/build:b2b-pitch-deck`; change the aggregate command to the retained
  DOCX-only proposal command;
- `package-lock.json`: remove the exact seven replay-proven
  `pptxgenjs`/`image-size` closure paths and change only `version`, `resolved`,
  and `integrity` under `node_modules/nanoid`;
- `frontend/package.json`: change only `dependencies/react-router-dom`;
- `frontend/package-lock.json`: change only the root `react-router-dom` edge,
  the three `version`/`resolved`/`integrity` fields for each of `nanoid`,
  `react-router`, and `react-router-dom`, and the nested
  `react-router-dom -> react-router` edge;
- `scripts/business_collateral/package.json`: no JSON delta.

Any omitted, additional, aliased, malformed, manual, or unclassified
dependency delta fails closed.

## Per-identity authored actions and resolver evidence

### `npm:image-size`: removal

The authored action removes the unused root `pptxgenjs` carrier. Node
`v24.18.1` and npm `11.16.0` replayed the exact-base action twice with identical
lock output:

```text
npm uninstall pptxgenjs --package-lock-only --ignore-scripts --no-audit --no-fund
```

The subordinate image owner records the seven-path solver closure and the
retained DOCX/PPTX content boundary. The head must contain no executable
`image-size` occurrence on any governed surface.

### `npm:nanoid`: replacement

The root lock-only replacement was selected and applied with Node `v24.18.1`
and npm `11.16.0`. The recorded resolver cutoff is a separate reproducibility
input; it is later than and does not redefine the immutable scanner timestamp:

```text
npm update nanoid --package-lock-only --ignore-scripts --no-audit --no-fund --before=2026-08-08T16:58:11Z
```

A disposable replay from the exact material changed only the root nanoid
`version`, `resolved`, and `integrity` fields. Root `package.json` gains no
direct dependency, dev dependency, npm alias, target-shaped tarball carrier, or
override for `nanoid`, regardless of tarball origin.

The frontend owner ran this canonical exact-target seed/unseed sequence from
`frontend/` with the same Node/npm versions:

```text
npm install --package-lock-only --ignore-scripts --no-audit --no-fund --save-dev --save-exact nanoid@3.3.17
npm uninstall --package-lock-only --ignore-scripts --no-audit --no-fund --save-dev nanoid
npm install --package-lock-only --ignore-scripts --no-audit --no-fund --save-exact react-router-dom@7.18.2
npm install --package-lock-only --ignore-scripts --no-audit --no-fund
```

The seed/unseed keeps nanoid transitive through the existing frontend graph;
the final manifest must not contain `nanoid`. A separate dev-operator
reproduction used `npm update nanoid --before=2026-08-07T00:00:00Z`; it is
corroborating evidence, not the selected frontend mutation command.

### `npm:react-router`: replacement and obsolete suppression deletion

The one authored dependency action changes the direct carrier
`react-router-dom` from `7.18.1` to `7.18.2`; canonical npm closure aligns the
installed `react-router` entry and carrier edge at `7.18.2`. The exact former
`GHSA-qwww-vcr4-c8h2` Rego rule and its header reference are deleted because
that target-specific suppression becomes obsolete. No suppression is added,
broadened, replaced, or otherwise deleted.

## Conjunctive postcondition and executable evidence

`P_batch` is one conjunction, never three optional results:

```text
P_batch =
  image-size absent on every governed head surface
  AND the root lockfile nanoid occurrence == 5.1.16
  AND every frontend lockfile nanoid occurrence == 3.3.17
  AND every tracked package.json nanoid carrier is an exact stable selector
      outside every reconciled affected range; only the exact nanoid key in the
      dependency/dev/optional/peer maps may use an identity-bound npm:nanoid
      alias, while override aliases, renamed aliases, target-shaped tarballs,
      and local-package carriers fail closed
  AND every tracked package.json react-router carrier under the exact
      react-router key is an exact stable direct selector outside every
      reconciled affected range; aliases, target-shaped tarballs, and renamed
      local-package carriers fail closed
  AND every tracked package.json react-router-dom carrier is exact npm SemVer,
      applies Node-semver's raw 256-character bound to direct/lock values and
      to the extracted alias/tarball version token, stays within its numeric-component bound,
      has no prerelease component, and is outside the affected ranges
  AND every react-router-dom lock artifact declares an exact stable react-router
      dependency equal to its own version and resolves it to the corresponding
      package-local occurrence first, then the nearest progressively hoisted
      validated Router occurrence; independent safe Router occurrences are
      allowed and do not freeze the lockfile topology
  AND every retained nanoid/react-router occurrence is a stable version whose
      origin-neutral target identity is discovered before its canonical registry
      tarball version is required to match `version` with non-empty integrity;
      WHATWG-style special-scheme backslashes are normalized before URL parsing
  AND every dependency/dev/optional/peer or nested override leaf is a non-empty
      ASCII selector whose identity remains explicit in its package key and
      whose registry version/range classification is delegated in one batch to
      `npm-package-arg` plus strict `semver.validRange` from the physically
      active npm tree; the stricter target rules above own the exact-key NanoID
      alias exception, while tags, renamed aliases, Git, hosted shorthand,
      remote/local paths, workspaces, unknown transports, Unicode, and malformed
      leaves fail closed for separate provenance review instead of growing a
      second npm parser
  AND lock-path identity is the complete unscoped name or @scope/name after the
      final node_modules segment, never the terminal basename alone
  AND GHSA-qwww-vcr4-c8h2 is not suppressible by the Rego policy or .trivyignore
```

Executable evidence anchors for the stable postconditions are:

- tracked/index surface enumeration and fail-closed Git environment:
  `tests/test_root_npm_dependency_guards.py::_git_stdout` and
  `tests/test_root_npm_dependency_guards.py::_load_tracked_npm_surfaces`;
- retired `pptxgenjs`/`image-size` graph absence:
  `tests/test_root_npm_dependency_guards.py::test_retired_pptx_graph_stays_absent_from_all_tracked_npm_surfaces`;
- direct, npm-aliased, target-shaped tarball, tracked local-package, bundled,
  and version-qualified override discovery:
  `tests/test_root_npm_dependency_guards.py::_tarball_identity_matches`,
  `tests/test_root_npm_dependency_guards.py::_find_manifest_occurrences`,
  `tests/test_root_npm_dependency_guards.py::_find_tracked_local_manifest_occurrences`,
  `tests/test_root_npm_dependency_guards.py::test_retired_graph_guard_rejects_repository_relative_target_tarball`, and
  `tests/test_root_npm_dependency_guards.py::test_manifest_discovery_rejects_version_qualified_override_keys`;
- transparent-registry selector admission in named manifest fields:
  `tests/test_root_npm_dependency_guards.py::_classify_current_npm_registry_specs`,
  `tests/test_root_npm_dependency_guards.py::_find_opaque_npm_dependency_source_occurrences`,
  and `tests/test_root_npm_dependency_guards.py::test_tracked_npm_manifests_reject_opaque_dependency_sources`;
  the generic owner admits a non-empty ASCII leaf only when the physically
  active npm installation classifies it as a registry `version` or `range` and
  its strict bundled `semver.validRange` accepts it; tags, aliases, transports,
  workspaces, Unicode, and malformed values remain opaque, while NanoID and
  React Router declarations still pass through the separate exact
  advisory-comparison owner below;
- complete scoped/unscoped lock-path identity:
  `tests/test_root_npm_dependency_guards.py::_lock_path_package_identity` and
  `tests/test_root_npm_dependency_guards.py::test_nanoid_owner_allows_unrelated_scoped_package_with_same_basename`;
- universal nanoid and React Router affected-range, Node-semver length/numeric,
  origin-neutral lock discovery, canonical-tarball provenance, integrity, and
  stable-release, Router/DOM artifact resolution, and exact dependency-edge postconditions:
  `tests/test_root_npm_dependency_guards.py::_parse_exact_npm_semver`,
  `tests/test_root_npm_dependency_guards.py::_exact_manifest_version`,
  `tests/test_root_npm_dependency_guards.py::_assert_manifest_occurrences_outside_ranges`,
  `tests/test_root_npm_dependency_guards.py::_assert_occurrences_outside_ranges`,
  `tests/test_root_npm_dependency_guards.py::_assert_react_router_dom_dependency_edges`,
  `tests/test_root_npm_dependency_guards.py::test_nanoid_occurrences_stay_outside_all_reconciled_affected_ranges`,
  and `tests/test_root_npm_dependency_guards.py::test_react_router_occurrences_stay_outside_all_reconciled_affected_ranges`;
- target-capable React Router suppression denial across both active ignore
  inputs:
  `scripts/ci/check_trivy_ignore_policy_expiry.py::_ignore_block_can_match_react_router_target`,
  `scripts/ci/check_trivy_ignore_policy_expiry.py::_validate_react_router_rsc_trivyignore_absent`,
  `tests/test_trivy_ignore_policy_expiry.py::test_react_router_rsc_suppression_is_absent_and_guarded_against_reintroduction`,
  and `tests/test_trivy_ignore_policy_expiry.py::test_react_router_rsc_trivyignore_reintroduction_fails_closed`;
- exact policy deletion surface: `trivy/ignore-policy.rego:1`;
- retained DOCX builder and retired local PPTX execution boundary:
  `tests/test_business_collateral_builders.py:90` and
  `tests/test_business_collateral_builders.py:131`.

The complete one-time base-to-head JSON delta and resolver replays remain
immutable evidence in this document; they are deliberately not encoded as a
permanent exact-base test that would block future authorized npm changes. The
anchors prove deterministic guard coverage of the stable postconditions. They
do not substitute for a terminal exact-head Trivy run or the repository's
separate merge-readiness gates.

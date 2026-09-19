# js-yaml security remediation — DEP-SEC-01 and historical GHSA-h67p-54hq-rp68

## Accepted scope and dated pre-open checkpoint

DEP-SEC-01 replaces the existing `npm:js-yaml` frontend override **4.3.1 → 4.3.2**
and requires every governed installed occurrence to resolve to 4.3.2. This existing
document is the evidence owner for this single-identity transition. The original
h67p fix and August batch remain historical evidence below.

The owner accepted this bounded implementation and explicitly authorized its start
while a colleague owns CD recovery. That decision does not claim healthy CD or
supply merge approval. The five material files are the frontend manifest/lock,
existing frontend dependency guard, this document and the existing backlog ledger.
No other dependency intent, runtime/API/DTO/route change, suppression or CD edit is
part of DEP-SEC-01. At the pre-open checkpoint on 2026-09-14, before 11:34 UTC,
the PR had not yet opened. The separate current checkpoint below records later progress.

The original accepted DEP-SEC-01 plan v1 and separate owner amendment govern all
acceptance items. Repository documentation belongs in this substantive PR;
unavoidable post-merge reconciliation is Carryover into the next substantive PR.
No standalone docs-only closeout PR is authorized for this dependency lane.

## D and S — identity and independently enumerated surfaces

- D: `npm:js-yaml`.
- Exact base B: `b89e833af752d2b68f8d8b0fa99ab18b59e856e9`.
- Candidate dependency material: the complete base/head hashes below; the eventual
  PR material-head SHA will be bound by its ordinary exact-head review/seal.
- Base census command: `git ls-tree -r --name-only -z b89e833af752d2b68f8d8b0fa99ab18b59e856e9`.
- Head census command: `git ls-files --cached -z`.
- Both independent NUL-safe censuses select every tracked basename `package.json`,
  `package-lock.json` and `npm-shrinkwrap.json`. Each present surface must be a
  regular non-symlink file. S_base = S_head is the five surfaces recorded below;
  no surface was added or removed.
- Actual base occurrences: `frontend/package.json` `/overrides/js-yaml = 4.3.1`
  and `frontend/package-lock.json` `/packages/node_modules~1js-yaml/version = 4.3.1`.
  At head both are 4.3.2; the other three surfaces have no governed js-yaml carrier.
- Dependent edge requirements (`^4.1.1`, `4.1.1`) and the js-yaml executable mapping
  are not additional installed versions. The existing delegated npm graph checks
  resolve edges; literal string search alone is not an identity/absence proof.

Permanent guards independently discover current tracked surfaces and enforce
current head policy; they do not freeze B, this five-surface count or historical
delta. Evidence: `tests/test_frontend_dependency_guards.py:1120`,
`tests/test_frontend_dependency_guards.py:1777`, `frontend/package.json:95`,
`frontend/package-lock.json:7346`.

The retained base/head/replay SHA-256 inventory is:

| Surface | Base SHA-256 | Head and replay SHA-256 (byte-equal) |
| --- | --- | --- |
| `frontend/package-lock.json` | `4b6649721614c6a937d3d1dd445301d1e905700df814a63ea5d6e8fa28bfb615` | `218ce00de53a874d486dd9fbbc275b9f00445435283c93acd1963a9569810423` |
| `frontend/package.json` | `234beaabd47ec019090e28a26cc4e56fdda4b745d5d75c89c12ec958a03eed5d` | `7d38cb173973ea0cab7ff49b1d2c7af37d6a1bc482b85a4e4c419245b3faba10` |
| `package-lock.json` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` | `a1c5411b103a80fc78b293c628d0fd8d6f47de065d2c75a208d06e40c683d9e8` |
| `package.json` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` | `9bcbc2307471c1eb4be4c87cffeb88587339e911e6a4898d5c9234fff7b0766c` |
| `scripts/business_collateral/package.json` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` | `8005a3491db7d92f36ac66369861589f9c47123d3a7c71e643fc2c06168cd45a` |

## F_cutoff and A — complete retained advisory inventory

Snapshot interval: **2026-09-14T10:30:36Z–2026-09-14T10:30:42Z**.
Authoritative inputs were the fully paginated GitHub Advisory Database npm/js-yaml
query, the authenticated full repository open Dependabot-alert census, and the npm
registry metadata for the selected version. GAD query parameters were
`ecosystem=npm`, `affects=js-yaml`, `per_page=100`; all returned pages were retained.
The complete snapshot contains **11 non-withdrawn advisory records / 16 ranges**.
The current repository alert is
[Dependabot #291](https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/291),
bound to [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh).

The new advisory describes CPU denial of service through repeated empty merge
mappings that bypass the merge-key work limit. Version 4.3.2 counts merge-source
work. No denial-of-service workload or production exploitation claim is part of
this version remediation.

Retained full raw input SHA-256 values (local files stay untracked and are archived
with the lane evidence):

- `js-yaml-advisories-pages.json`: `99ae30ba90e358ee7fa57ab8536ee062675e69ca6c840af4e1fa264af05fcbaa`.
- `dependabot-open-pages.json`: `500122c41845e6628c216e1f0d5c32e34344f554727dc4f242efce6e1a6973dc`.
- `registry-js-yaml-4.3.2.json`: `e96013c33e40d4140b113285a695ba1940373239763065427dfcf687e9427f9e`.

A is exactly `{GHSA-2883-xcg3-v3hh}`: comparable governed base occurrence 4.3.1
is within that advisory's `>=4.0.0,<4.3.2` range. Every other candidate is outside
its complete affected ranges at base 4.3.1, as shown below. Inapplicability at base
never removes a record from the universal head condition. Every range was compared
with base 4.3.1 and head 4.3.2 using the existing stable-version/SpecifierSet path;
all head comparisons are outside. The following normalized receipt retains each
record's revision metadata, all ranges, first patched versions and result:

```json
[
  {
    "ghsa_id": "GHSA-2883-xcg3-v3hh",
    "published_at": "2026-09-08T21:24:51Z",
    "updated_at": "2026-09-08T21:24:52Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 4.0.0, < 4.3.2",
        "first_patched": "4.3.2"
      },
      {
        "affected": ">= 3.0.0, < 3.15.2",
        "first_patched": "3.15.2"
      }
    ],
    "base_4_3_1_affected": true,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-5p4m-2wfm-xmqj",
    "published_at": "2026-08-06T20:27:32Z",
    "updated_at": "2026-08-06T20:27:32Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 4.0.0, < 4.3.1",
        "first_patched": "4.3.1"
      },
      {
        "affected": ">= 3.0.0, < 3.15.1",
        "first_patched": "3.15.1"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-pm4m-ph32-ghv5",
    "published_at": "2026-07-24T16:47:36Z",
    "updated_at": "2026-08-13T17:47:37Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 5.0.0, <= 5.2.1",
        "first_patched": "5.2.2"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-g796-fgmg-93mv",
    "published_at": "2026-07-20T21:19:27Z",
    "updated_at": "2026-07-20T21:19:29Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 5.0.0, <= 5.1.0",
        "first_patched": "5.2.0"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-52cp-r559-cp3m",
    "published_at": "2026-07-20T21:19:09Z",
    "updated_at": "2026-07-20T21:19:10Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 3.0.0, < 3.15.0",
        "first_patched": "3.15.0"
      },
      {
        "affected": ">= 4.0.0, < 4.3.0",
        "first_patched": "4.3.0"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-724g-mxrg-4qvm",
    "published_at": "2026-07-20T21:18:51Z",
    "updated_at": "2026-07-20T21:18:53Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 5.0.0, <= 5.2.0",
        "first_patched": "5.2.1"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-h67p-54hq-rp68",
    "published_at": "2026-06-15T17:15:07Z",
    "updated_at": "2026-06-29T15:06:00Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 4.0.0, <= 4.1.1",
        "first_patched": "4.2.0"
      },
      {
        "affected": "< 3.15.0",
        "first_patched": "3.15.0"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-mh29-5h37-fv8m",
    "published_at": "2025-11-14T14:29:48Z",
    "updated_at": "2026-01-31T03:32:45Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": ">= 4.0.0, < 4.1.1",
        "first_patched": "4.1.1"
      },
      {
        "affected": "< 3.14.2",
        "first_patched": "3.14.2"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-2pr6-76vf-7546",
    "published_at": "2019-06-05T14:35:29Z",
    "updated_at": "2023-01-09T05:01:39Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": "< 3.13.0",
        "first_patched": "3.13.0"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-8j8c-7jfh-h6hx",
    "published_at": "2019-06-04T20:14:07Z",
    "updated_at": "2023-11-29T20:43:52Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": "< 3.13.1",
        "first_patched": "3.13.1"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  },
  {
    "ghsa_id": "GHSA-xxvw-45rp-3mj2",
    "published_at": "2017-10-24T18:33:37Z",
    "updated_at": "2023-01-09T05:03:30Z",
    "withdrawn_at": null,
    "ranges": [
      {
        "affected": "< 2.0.5",
        "first_patched": "2.0.5"
      }
    ],
    "base_4_3_1_affected": false,
    "head_4_3_2_outside_all": true
  }
]
```

## R — authored intent and reproducible native solver closure

I_R is the single nonempty authored replacement at `/overrides/js-yaml`.
The lockfile was generated through the repository wrapper, then the same action
and command were replayed from a second isolated detached worktree at exact B:

```bash
scripts/frontend_npm.sh --prefix frontend install --package-lock-only --ignore-scripts --no-audit --no-fund
```

Both native runs exited 0. Retained raw stdout was respectively:

```text
up to date in 1s
up to date in 404ms
```

Node was `v24.18.1`, npm `11.16.0`, matching the retained pre-resolution baseline
and the post-resolution configuration in both worktrees. Registry was
`https://registry.npmjs.org/`; legacy-peer-deps, strict-peer-deps and install-links
were false; package-lock true; lockfile-version null; omit/include empty. The
ambient ignore-scripts value was false; the identical command explicitly enabled
ignore-scripts and disabled audit/funding in both runs.

Comparison covers complete parsed JSON over all independently enumerated npm
surfaces, plus byte equality of every candidate/replay surface. It found exactly
four changed JSON fields: one I_R field and three C_R fields in one installed
js-yaml record. No other record, edge, dependency identity or manifest changed.
Every field appears exactly once in the complete delta below; the two native
results are byte-identical. No manual lock edit, audit fix or broad package update
was used. The detached replay is evidence computation, not a second PR lane.

| Surface | JSON pointer | Before | After | Class |
| --- | --- | --- | --- | --- |
| `frontend/package-lock.json` | `/packages/node_modules~1js-yaml/integrity` | `sha512-CY6crGq313MX8GkwvB7tzgp99vjQxY1++5y10/BKN/GUfHqWaOGQMNZkBvqSzsZKWk/ijwHlWzzkLulsGHhjWQ==` | `sha512-SFNOvSJ+Dgf/9An904Yx+CgSlIPCkIpao4qo51lpee25TIRejdH3rhR4EZMGoNx3/TP3O+wzWuiTFl4sqbltzA==` | `C_R` |
| `frontend/package-lock.json` | `/packages/node_modules~1js-yaml/resolved` | `https://registry.npmjs.org/js-yaml/-/js-yaml-4.3.1.tgz` | `https://registry.npmjs.org/js-yaml/-/js-yaml-4.3.2.tgz` | `C_R` |
| `frontend/package-lock.json` | `/packages/node_modules~1js-yaml/version` | `4.3.1` | `4.3.2` | `C_R` |
| `frontend/package.json` | `/overrides/js-yaml` | `4.3.1` | `4.3.2` | `I_R` |

The root manifest, root lock and business-collateral manifest have empty JSON deltas.
The retained replay receipt contains the complete machine-readable JSON delta;
this table renders every nonempty field without changing its value.

The complete local replay receipt `resolver-replay.json` has SHA-256
`526c525c01b1dfdf489be6d2297b1f6a933c7ef15e4ccac0ec74994c5083450e`.
The selected registry metadata and native lock output agree on the canonical
4.3.2 tarball and SHA-512 SRI; `argparse: ^2.0.1` remains unchanged. Integrity syntax
alone does not authenticate tarball contents; clean npm ci provides the separate
fetched-byte integrity check.

## P — head postcondition and validation

All admitted js-yaml occurrences must remain comparable, exactly 4.3.2, from the
canonical npm source, consistent with manifest authority, and outside **every**
range in F_cutoff. A later-looking prerelease, alias, unexpected owner surface,
malformed entry or source cannot count as absent/safe. This finite cutoff claim
never means immunity to unknown/future advisories or proof of production exposure.

Executable changes in `tests/test_frontend_dependency_guards.py:328` and
`tests/test_frontend_dependency_guards.py:1777` retain the ordinary guard path and
reuse its existing strict JSON, container, provenance and SHA-512 helpers.
Independent expected inventory/range witnesses include every 3.x/4.x/5.x boundary;
range checks run separately from the project floor so a below-floor failure cannot
mask a missing advisory predicate. Whole-guard controls cover vulnerable nested and
top-level versions, safe-but-unselected drift, aliases, malformed entries/versions,
duplicate JSON keys, wrong source, link/bundle state, invalid SRI, manifest/lock
mismatch, additional tracked manifests/locks/shrinkwraps and missing/symlinked files.

Validation commands retained from the 2026-09-14 pre-open checkpoint:

```bash
python -m pytest -q tests/test_frontend_dependency_guards.py tests/test_root_npm_dependency_guards.py
python scripts/ci/check_docs_phase1_gates.py --files docs/security/GHSA-h67p-54hq-rp68-js-yaml.md
```

The full focused frontend/root dependency guard suites exited 0. Initial retained
failures were an expected-message mismatch in the malformed-packages fixture and
an unintended census replacement in an existing brace-expansion test; both were
corrected before the passing full rerun, without weakening any guard. Raw failures
and rerun output remain in the local lane evidence.

Coordinator-observed compatibility results: clean npm ci installed 693 packages;
make openapi and make openapi-check passed without generated drift; frontend build
(including typecheck), tokens check and CSS smoke passed. Vitest reported 93 files,
888 passing tests and one existing color-contrast skip: JSDOM cannot compute those
styles (`frontend/src/components/__tests__/Accessibility.test.tsx:229`), and the
browser axe lane owns that check (`frontend/tests/accessibility.spec.ts:1`). No skip
was added. Aggregate frontend coverage was statements 73.6%, branches 71.45%,
functions 73.07%, lines 74.3%; these are not the current-PR diff-coverage ≥97% gate.
An initial concurrent coverage/tokens run raced make openapi's npm ci; the
coordinator retained failures and reran after installation completed. Build emits
existing dynamic-import/chunk-size warnings on unchanged frontend source.

At that pre-open evidence checkpoint, preflight/consistency, inspected
make validate-changed and all-file pre-commit remained required.
Full local make verify is not authorized.
Premortem/Runner, post-open role review, current-head canonical CI/security/coverage,
strict seal/readiness/wait, human merge decision and post-merge proof were pending
at that checkpoint. It did not claim PR or Dependency Epic completion.

## Current PR checkpoint — 2026-09-14

[PR #2396](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2396) opened
non-draft at 11:34 UTC on `codex/dep-sec-js-yaml-floor`. The reviewed implementation
head was `6fd99b402cea2ae653dc9ed9dd024a235fbca3ce`; the canonical mapping will bind
the final material head after these review corrections.

The full focused suites, analytical preflight, agent consistency and all-file
pre-commit passed. `make validate-changed` selected and passed 829 tests across
the frontend/root dependency guards, CI scope contract and Python supply-chain
controls. Canonical `make tokens-check` passed all 37 controls. No full local
`make verify` was run.

Actual-diff premortem has no open finding. Accepted Experiment Runner
`exp-626de9290a4b` ran two oracle-only checks (75 selected guard cases and Docs
Phase 1), both exit 0, one attempt, zero retries and no tracked mutations.
Its accepted result materially informed the commit decision and both initial
commits carry the canonical Runner co-author trailer. The single required
post-open QA → bug-hunter → security-auditor chain completed on the reviewed
implementation head without additional executable defects.

Sourcery identified an inaccurate fixed target count in the helper docstring;
the correction names the declared target set without freezing its cardinality.
Five new negative-test docstrings now describe their distinct failure modes.
CodeRabbit's checkpoint finding is addressed by retaining the dated pre-open
evidence above and recording observed progress separately here.
Evidence: `tests/test_frontend_dependency_guards.py:1778`,
`tests/test_frontend_dependency_guards.py:4314`.

The PR scope classifier initially rejected security-document plus frontend paths.
The owner's already accepted five-file scope was recorded through the existing
operator/client-mix approval metadata; the next current-head scope check passed.
No classifier, gate or scope rule was weakened. The existing Phase 2 pending
literal was corrected separately; its local pre-closeout body check passed.
Final current-head CI, numeric diff coverage ≥97%, review dispositions,
self-review/seal, strict readiness/wait, human merge authorization and post-merge
proof remain pending at this documentation checkpoint.

All four existing Drive documents have verified same-ID plan-start and PR-open
readbacks, including both tabs of the native Dependency Epic plan. Previous
content was preserved exactly; the Markdown files received new versions.
Terminal/post-merge Drive checkpoints, alert #291 observation, archive and owned
cleanup are still required. These statements do not close the Dependency Epic.

## Remaining debt and rollback

The retained repository census has 16 open alerts over six identities. This PR
addresses js-yaml only; smol-toml, Vitest/@vitest/mocker, httpx2 and httpcore2 remain
separate sequential work. PYDEP-1A remains deferred after the security sequence.
See [dependency checkpoint](../roadmap/BACKLOG_LEDGER.md#ledger-p1-dependency-alerts-after-main-recovery)
and [Dependency Epic](../roadmap/BACKLOG_LEDGER.md#ledger-p1-depsec2-multi-ecosystem-dependency-closure).

Before merge, stop advancement and fix any regression in this PR. After merge,
rollback is a human-authorized governed revert that explicitly restores the security
risk to tracking. Alert #291 must be observed after merge; indexing delay is a
separate pending result and must not be hidden by dismissal. The four same-ID Drive
checkpoints, archive and owned-resource cleanup remain required. Unavoidable later
repository reconciliation is carried into the next substantive PR under the owner's
explicit decision; the epic stays open.

## Historical remediation chronology

GitHub Dependabot alert #164 reported `js-yaml <=4.1.1` under
`frontend/package-lock.json` for GHSA-h67p-54hq-rp68 / CVE-2026-53550 (medium).
A safe top-level 4.2.0 coexisted with a vulnerable nested
`node_modules/@redocly/openapi-core/node_modules/js-yaml@4.1.1`. The original lane
added the manifest-backed override and regenerated all installed occurrences to
4.2.0. Its historical commands were `npm --prefix frontend install --package-lock-only
--ignore-scripts`, `npm --prefix frontend ls dompurify js-yaml --package-lock-only
--all`, and the focused frontend dependency guard suite.

The 2026-08-21 seven-identity successor raised that same carrier to 4.3.1 for
GHSA-52cp-r559-cp3m and GHSA-5p4m-2wfm-xmqj. Its transition remains owned by
[the historical frontend batch document](FRONTEND_NPM_SECURITY_BATCH_REMEDIATION_CLASS.md).
DEP-SEC-01 supersedes the current selected-version/floor projection here, preserving
both historical corrections and their evidence owners. The original nested entry
remains absent, although Redocly's dependency edge still declares 4.1.1 and is
resolved through the override. This does not declare the whole frontend secure.

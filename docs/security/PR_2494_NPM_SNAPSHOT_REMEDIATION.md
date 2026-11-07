# PR 2494: exact npm snapshot remediation


## Current audit03 accepted extension (2026-10-31)

Direct external owner instruction `5c3bccdffbbc9446976d585b26550ef8b02f8229e5eed9fe208f83b13c531a53`
accepts the complete original-base audit03 snapshot
`97c17f997b90aae7b2e2458f3b2bb1c3165c4283f751f7add2df9484320bc1be`.
The original-base root audit returned 0; frontend returned 1 with all30 rows:
2 LOW,24 MODERATE,3 HIGH,1 CRITICAL. The immutable cutoff completed at
2026-10-31T12:24:08.666886+00:00 with Node24.22.1/npm11.19.1. These
are actual historical observations, not a fresh candidate audit.

The all-and-only primary identity set is @vitest/mocker, deepmerge, glob,
minimatch, postcss-selector-parser, qs, source-map-js, storybook, undici and vite.
Prior eight authored targets remain unchanged. New authored I_R is glob14.0.2,
minimatch11.0.1 replacing both old minimatch@3/@10 override objects, and the
explicit checked Redocly1.34.15 source adaptation. The former brace-expansion
parameters are superseded; universal current-occurrence advisory floors remain.
The Redocly adaptation is authored intent, not solver closure or an extra
advisory identity. No lifecycle hook, other dependency target, token/golden
rewrite, suppression or future cohort authority follows.

S_base and S_head remain the root and frontend manifests/locks enumerated below;
root material is unchanged. Current frontend manifest and the exact canonical
combined A/B lock are now imported. The complete transition partition is
reconciled as recorded below. At the October 31 lock-import checkpoint, installed versions and executable absence still required native verification. The material 24 result below supersedes that pending status. Earlier audit02 evidence remains dated history.

New cutoff members: glob GHSA-3g3m-2fjr-6pw4 affects `>=9.0.0 <=14.0.1`,
selected14.0.2; minimatch GHSA-g3hv-75wg-m249 affects `<11.0.1`, selected11.0.1.
Both are applicable at the original governed base according to actual audit03
occurrences. All previously reconciled advisory members below remain in the
universal head check, including non-applicable-at-base records. Installed comparability and executable absence were subsequently checked on material 24.

### Observed canonical replays and imported lock

The four original-base canonical replays returned native exit0: glob-only,
minimatch-only, combined-A and independent combined-B. They used the qualified
Node24.22.1/npm11.19.1 lock-only/ignore-scripts command and recorded registry
configuration. Combined A/B bytes and complete delta were equal. A separate
original-base other-nine/minus-glob diagnostic also returned exit0; it was not
seeded from a previous replay. No install or lifecycle execution is inferred.

| Graph | Exact frontend lock SHA-256 | Observation |
| --- | --- | --- |
| B original base | c473f85f249c93345e2b2ad2b606d488ffc658e6a74ccab1c2bd83f01c201ad7 | Common immutable starting lock |
| G glob-only | cf179c96de7f5f23ab1ab686786884f566672836369f90613169fa6ec57612d5 | Independent single-action exit0 |
| Minimatch-only | 64b67a53eee025bb67d6b1a66ef59448b7a6b1059eab351d4ffdae75feea3e8a | Independent single-action exit0 |
| N other-nine diagnostic | b56b198237f5d1737b2e655f45041fc0282b28a11f162dde8e2043713306a71a | Conditional-placement corroboration only |
| F combined A and B | 05c0fd820e1e1954ab117d00a4e4edcd5c4dc0fa33236afaf83c6a23ffe1e45c | Byte-identical native outputs; imported unchanged |

The current authored manifest SHA256 is
d934bbe972efa9022cd404968e8cb0026a10584c59e5edb54a83d970ef0b7a30.
ROOT independently reconciled and imported the exact349819-byte F lock,
replacing the earlier76ca536c003860b573aab1e1ecbbf1c7361ddb512da2d216e287d71ed01d6217
candidate by compare-and-swap. It was not manually edited. Current anchors:
`frontend/package.json:90`, `frontend/package-lock.json:1643` and
`frontend/package-lock.json:1661`.

Full B→F accounting is **181 physical rows = 1 root authored union +14 I_R
rows +166 C_R rows**, exactly one class per row, zero unclassified, no omitted
or extra physical paths. ROOT rechecked164 ordinary C_R whole-row witnesses,
1007 declared/resolved edge checks including repeated chains, all10 base/head
identity censuses and the finite pair conditions. The two additional C_R rows
are the explicit path-scurry deletion/addition pair below. Prior eight action
witnesses remain separately bound; a shared @isaacs/nonrecursive-glob-match
closure retains glob-first accounting with both individual witnesses, without
claiming unique global causality. The generate-types verify prefix and Redocly
source adaptation remain authored I_R, never solver closure.

### Exact four-row placement adjudication

All four physical transitions remain visible:

| Physical path | Transition | Accounting |
| --- | --- | --- |
| node_modules/glob | Delete13.0.6 | One glob I_R action, first physical row |
| node_modules/@joshwooding/vite-plugin-react-docgen-typescript/node_modules/glob | Add14.0.2 | Same glob I_R action, second physical row |
| node_modules/path-scurry | Delete2.0.2 | Glob-owned C_R, first physical row |
| node_modules/@joshwooding/vite-plugin-react-docgen-typescript/node_modules/path-scurry | Add3.0.0 | Same finite C_R pair, second physical row |

The explicit coordinator adjudication applies only to these exact B/G/N/F
operands. Every graph contains exactly one glob and one path-scurry occurrence;
complete B/N before objects and complete G/F after objects match. Full N→F has
exactly these four package-record changes, with every other package record and
non-packages top-level field equal. All addresses remain recorded, not normalized
away. No path-scurry parameter was authored in any of the four manifests.

**B→G supplies the required original-base single-action proof**, including the
actual path-scurry2→3 artifact and incoming glob requirement change. N→F only
corroborates its final placement under the fixed other-nine intents; neither the
diagnostic nor joint A/B determinism replaces G. Path-scurry's G/F outgoing
lru-cache/minipass edges retain identical physical targets and complete objects.
The surviving docgen declaration remains `^13.0.1`, controlled by the explicitly
authorized glob14.0.2 override;14 is not claimed to satisfy13 normally. The old
bundled wrapper disappears under the separately accepted deepmerge/Style Dictionary
action. This is no generic hoisting exception or future classification rule.

Whole-graph equivalence is explicitly false: G's glob resolves nested
minimatch11.0.3; F resolves root minimatch11.0.1 under its separate authored
replacement and individual witness. G11.0.3 is nonretained and is not relabeled
as11.0.1 or hidden inside the path-scurry classification. Any changed operand,
cardinality, object, edge or intent invalidates this finite adjudication.

### Bound evidence and remaining postconditions

Evidence hashes identify the retained procedural records, without replacing
tracked source anchors or asserting native behavior from a hash:

- Four-replay ROOT receipt:63bc31f2926c360e82e697b7325e6074fa7deb0faa4bdb1413680203908e9afa.
- Diagnostic ROOT receipt:de830db3d5fadb5c6eafd616c3f88db8541d373a36f93fba3fd113cc7e395aa3.
- Complete four-graph evidence:33f5f176d859548b8b86547b0d52e0519ead32d17a16124b486581a446caa1fe.
- Prior explicit finite adjudication:b464c9ce454916bab6e37dffbe4e90df5e70f247bd67062f8f78a53ff6a04b8c.
- Complete classification v2:4a0855d011c9f559cc7ced7e62db48af05b91fb6a6374aa7df69edc0af703a8b.
- ROOT reconciliation/import:abfc1a4316372228f598906b59dc218478321b828beb8938768d77796b9deede.
- Original four-unclassified HOLD:12df223188385ea5bf2922ba5d7f3c09ada8c2659ab0f9be8decf59f9fddff0e remains immutable history, not erased by v2.

Present head lock candidates are undici7.30.1, storybook10.6.2, vite8.1.6,
@vitest/mocker4.1.12, postcss-selector-parser6.1.5, source-map-js1.2.2,
glob14.0.2 and minimatch11.0.1. qs and deepmerge have zero lock occurrences;
the executable absence checks are recorded below. All30 original scanner rows and every
per-identity F/A remain, including non-applicable-at-base advisories in the
universal head condition. Root2, Zod's complete row and Redocly1.34.15's original
whole lock row/URL/SRI are preserved. Existing failures, old-eight observations,
all39/N7, owners, missed deadlines and post-merge obligations remain history and
independent requirements.

### Material 24 qualification

All ten scoped P postconditions are achieved for tree `c488c4e848cb3835439116cdbc119735f2711d21` against the immutable audit03 cutoff `97c17f997b90aae7b2e2458f3b2bb1c3165c4283f751f7add2df9484320bc1be`. The evidence combines the per-advisory base applicability and head range checks, the classified canonical replays, fresh root/frontend installations and a separate installed-tree readback. The base and head enumeration covers five tracked carriers: root and frontend package manifests and locks, plus the dependency-free collateral manifest `scripts/business_collateral/package.json`. The two compositions were audited independently. The accepted transition remains 181 physical rows: one root authored union, 14 authored-action rows and 166 solver-closure rows, zero unclassified. The final frontend lock is `05c0fd820e1e1954ab117d00a4e4edcd5c4dc0fa33236afaf83c6a23ffe1e45c`.

| Exact identity | A / F and governed base witness | Actual governed head result |
| --- | --- | --- |
| @vitest/mocker | 2 / 3 at 4.1.11 | One frontend occurrence at 4.1.12, outside all three candidates including the base-nonapplicable range. |
| deepmerge | 1 / 1 at 4.3.1 | No occurrence. Both root and frontend resolution returned MODULE_NOT_FOUND. The accepted loader replacement removes its parent dependency. |
| glob | 1 / 1 at 13.0.6 | One nested frontend occurrence at 14.0.2. The actual docgen parent resolved that occurrence and exercised globSync. The original-base glob-only replay owns the replacement and the precise path-scurry closure. |
| minimatch | 1 / 1 for the original governed versions below 11.0.1 | One frontend occurrence at 11.0.1, at the fixed boundary. Redocly, ESLint and TypeScript-ESLint resolved the actual package. Glob-only replay’s 11.0.3 remains diagnostic history. |
| postcss-selector-parser | 1 / 1 at 6.1.4 | One frontend occurrence at 6.1.5, outside the affected range. |
| qs | 1 / 1 at 6.16.0 | No occurrence. Both root and frontend resolution returned MODULE_NOT_FOUND. The manifest retains the authored 6.16.1 override. Physical absence belongs to classified solver closure. |
| source-map-js | 1 / 1 at 1.2.1 | One frontend occurrence at 1.2.2, outside the affected range. |
| storybook | 2 / 2 at 10.4.4 | One frontend occurrence at 10.6.2, outside both candidates. The Storybook build completed. |
| undici | 18 / 18 at 7.29.0 | One frontend occurrence at 7.30.1, outside each of the 18 candidates and their recorded intervals. |
| vite | 5 / 5 at 8.0.16 | One frontend occurrence at 8.1.6, outside all five candidates. Typecheck and build completed. |

All ten identities had zero installed occurrences at root. The separate recovery inspected 1,211 installed package.json observations. The retired wrapper and Style Dictionary also failed resolution in both compositions. They remain consequences of the admitted remediation. The two native unignored audits on material 24 reported zero vulnerability keys and zero total findings (root 135 reported dependencies, frontend 709). The installed results and range/absence checks establish the ten-identity conjunction. Source anchors: `tests/test_frontend_dependency_guards.py:5604`, `tests/test_frontend_dependency_guards.py:5624`, `frontend/package.json:90`, `frontend/package-lock.json:1643`, `frontend/scripts/check-redocly-compat.mjs:256`.

Run 05 installed both compositions and completed the real Redocly controls (687 original and 687 after members, 17 commands), the full audits, and all 854 owning Python test cases with zero skips. All eleven token JSONs remained unchanged from D209 to material 24, and the old, new and tracked CSS, TypeScript and Swift outputs were byte-equal. The run subsequently exited 1 during the private parent API probe with `TypeError: match is not a function`. Later phases did not execute in that run.

Run 06 re-read the retained installed trees and completed 12 phases. It exercised four actual Redocly URL match cases, two each for the ESLint and TypeScript-ESLint parent-resolved minimatch APIs, and one nested docgen globSync case. Both lints, the frontend and Storybook builds, token generation/check, typecheck and canonical OpenAPI completed. Vitest reported 929 cases: 928 passed and one existing JSDOM color-contrast check skipped. Browser color-contrast execution is still open under the [tracked P1 Toggle follow-up](../roadmap/BACKLOG_LEDGER.md#ledger-p1-web-color-contrast-browser-coverage). The two readbacks establish scoped results on the bound source tree. Continuous installed-tree history, any presently unexecuted color-contrast behavior, current-head CI, PR-wide security, review, merge and post-merge outcomes remain outside this P decision.

Original execution receipt `9ed3c2ad244616c4477c21ca4d159ff621c62b538846f5356e7010073f153319`. Recovery receipt `5263698d3550ece121d9b7cbc06f27470bfebcf42ba028dc12d4e76de7cb674c`.

### Complete audit03 row inventory

Each direct advisory identity retains its own postcondition; induced rows retain
their exact upstream dependency relationships. None is dropped because its
parent no longer appears in a later candidate. At the October 31 import checkpoint each row awaited a fresh head audit. The material 24 audits and per-identity results are recorded above.

| Row | Snapshot via identities/advisories | Role |
| --- | --- | --- |
| @bundled-es-modules/deepmerge | deepmerge | induced dependency row |
| @bundled-es-modules/glob | glob | induced dependency row |
| @eslint-community/eslint-utils | eslint | induced dependency row |
| @eslint/config-array | minimatch | induced dependency row |
| @eslint/eslintrc | minimatch | induced dependency row |
| @joshwooding/vite-plugin-react-docgen-typescript | glob | induced dependency row |
| @redocly/openapi-core | minimatch | induced dependency row |
| @storybook/react-vite | @joshwooding/vite-plugin-react-docgen-typescript | induced dependency row |
| @typescript-eslint/eslint-plugin | @typescript-eslint/parser, @typescript-eslint/type-utils, @typescript-eslint/utils, eslint | induced dependency row |
| @typescript-eslint/parser | @typescript-eslint/typescript-estree, eslint | induced dependency row |
| @typescript-eslint/type-utils | @typescript-eslint/typescript-estree, @typescript-eslint/utils, eslint | induced dependency row |
| @typescript-eslint/typescript-estree | minimatch | induced dependency row |
| @typescript-eslint/utils | @eslint-community/eslint-utils, @typescript-eslint/typescript-estree, eslint | induced dependency row |
| @vitest/coverage-v8 | vitest | induced dependency row |
| @vitest/mocker | GHSA-qxg6-89mg-rqv8, GHSA-xp26-3454-mjgp | primary identity |
| deepmerge | GHSA-gcqx-w48m-w2h4 | primary identity |
| eslint | @eslint-community/eslint-utils, @eslint/config-array, @eslint/eslintrc, minimatch | induced dependency row |
| eslint-plugin-react-refresh | eslint | induced dependency row |
| glob | GHSA-3g3m-2fjr-6pw4, minimatch | primary identity |
| minimatch | GHSA-g3hv-75wg-m249 | primary identity |
| openapi-typescript | @redocly/openapi-core | induced dependency row |
| postcss-selector-parser | GHSA-rj75-hqrm-r3gf | primary identity |
| qs | GHSA-6pq8-jhm2-2vcw | primary identity |
| source-map-js | GHSA-68fv-2mgg-jv7q | primary identity |
| storybook | GHSA-f2ph-cmg5-wxc8, GHSA-px85-f4q5-jh77 | primary identity |
| style-dictionary | @bundled-es-modules/deepmerge, @bundled-es-modules/glob | induced dependency row |
| typescript-eslint | @typescript-eslint/eslint-plugin, @typescript-eslint/parser, @typescript-eslint/typescript-estree, @typescript-eslint/utils, eslint | induced dependency row |
| undici | GHSA-3wwx-pv8p-q78v, GHSA-pmjh-fq2x-6v4x, GHSA-r53p-7pc4-xj5r, GHSA-rfgv-xxqx-mfg5, GHSA-3xpg-4rpp-hhhm, GHSA-2jfj-6hjv-fm6j, GHSA-2gqq-gqf2-x968, GHSA-w293-vg96-wgc3, GHSA-8436-99hf-9mmv, GHSA-rx4f-c7p8-82vq, GHSA-4qv8-2p9j-2685, GHSA-f72v-6w45-q472, GHSA-xjj6-f33q-929c, GHSA-4w7w-5xrc-9h26, GHSA-2m5v-pch6-74hx, GHSA-qrxm-fqhp-jwvm, GHSA-9fm3-97px-rjf6, GHSA-55wc-3pg8-jfw6 | primary identity |
| vite | GHSA-698v-4r3x-3vcv, GHSA-r825-w8mm-5pxw, GHSA-587h-7wmj-h5pm, GHSA-9jrq-w75r-8gcw, GHSA-rq7h-c2jc-7f22 | primary identity |
| vitest | @vitest/coverage-v8, @vitest/mocker | induced dependency row |

### Finite Redocly source and caller contract

`frontend/scripts/check-redocly-compat.mjs:1` owns exactly the fixed parent at
frontend/node_modules/@redocly/openapi-core1.34.15. Acquired original SRI remains
`sha512-HAwCnNyKcs5XGQqms+9t7OdAPM/5TDstmhF+0i7tdCFato2QKuYIlyWETwkXd8c5zbltr1oB+6y9NTeQLr2d6Q==`;
the derived installed tree is not pristine upstream and never substitutes its
hash into lock integrity. Original archive SHA256d07f7d934e6b18c41beafac967ab0fca567da9f878a0b03bcf285103f9ee1ea2
and exact patchcb808b31c5dc55edd2d86485f4298b0f2b5dcaacf2f69803c71966be1c842804
bind the source transition. All687 payload files,680 mode0644 and7 mode0755,
come from the qualified original installed readback. Only lib/utils.js changes;
checked target mode is preserved. These original observations do not prove a
future installed minimatch11 graph.

Apply admits full ORIGINAL or an idempotent full AFTER; verify admits AFTER only.
The actual parent's Node resolution, lock acquisition tuple, nested dependency
subtree and minimatch11.0.1 named callable export are checked separately. Payload
completeness excludes only the package-root dependency subtree; it does not
claim full file hashes for every dependency. Symlink/hardlink/mode/member drift,
unknown partial states and transaction residues reject. One owned same-filesystem
atomic replacement and full reread do not promise global concurrent filesystem
atomicity. No consumer follows a failed check and no automatic reinstall repairs it.

Named callers are successful canonical frontend ci through scripts/frontend_npm.sh,
the existing retry composite after its successful npm loop, fresh/cached Make
frontend-install, direct generate-types verify-before-CLI, and Docker's exact
three copied helper/data prerequisites before ci/apply. Root/audit/lock-only and
unknown/subdirectory wrapper forms do not receive automatic patching. The exact
run-ci-local ci-to-install fallback is removed. Caddy source context changes
invalidate old material qualification for these new inputs.

At the October 31 lock-import checkpoint, normal install, ORIGINAL→AFTER→verify,
negative filesystem/graph controls, parent API compatibility, builds, OpenAPI,
token parity and both audits still awaited execution. Material 24 supplies the
scoped results above. The original 39 criteria, N7 and final CI, review, merge
and post-merge outcomes retain their separate evidence requirements.

## Historical audit02 implementation and evidence


## Audit02 status and authority at the October 31 checkpoint

At that checkpoint, the implemented audit02 candidate awaited native qualification.
Direct external operator instruction d633310b23da700478ab5f1e99e93de93a72e1e757f07cea467027cc9ff4e9b5
admits the exact immutable audit02 cohort (archive SHA-256
d30afa38781ac4fb70c7cd34d53eed9e3bff8a276319a7618baa72740d74397d).
The candidate does not authorize itself. No future batch, suppression, risk acceptance,
publication or merge authority follows. Original 39 criteria, N7, missed deadlines
and post-merge gates remain independent and open until individually evidenced.

The snapshot has eight advisory-bearing identities and four induced scanner rows.
The extra authored Vitest parent/coverage/expect parameters and removal of the
Style Dictionary loader were explicitly included in that instruction.
Current baseline is actual merged main d20922f741f431b6eb3e47386ae944ca441a971e
integrated into the existing PR; audit02 material tree was
a82fd09fd0247baeae59119abf4c9342f408ca6b. This is not a claim that the live PR API base
has advanced from its separately retained 48d36c220ff58dec82450da66ef0599c6da71787.

## D and complete S

Independent tracked discovery at the frozen base and candidate finds five npm
carriers: `package.json`, `package-lock.json`, `frontend/package.json`,
`frontend/package-lock.json`, and `scripts/business_collateral/package.json`.
The collateral marker declares no dependencies; root and frontend are the two
independent lock compositions. No surface was added or removed. Root package/lock
and collateral bytes remain unchanged. Root/frontend complete nested occurrences
and aliases remain governed by the existing dependency guards.

## F_cutoff, A and universal candidate P

F_cutoff is immutable audit02 plus its retained primary GitHub advisory responses
and the three retained Vitest policy candidates, individually timestamped in the
source intake. There are 31 base-applicable GHSAs, 32 candidates across the eight
identities and 34 across all twelve rows. All 18 undici advisories remain present.
The table includes every primary interval, including non-base major branches;
base non-applicable candidates remain subject to universal head checks.
Static version comparison is not a native scanner or executable absence result.

| Identity / scanner row | Base | Candidate | A / F | Current evidence boundary |
| --- | --- | --- | --- | --- |
| @bundled-es-modules/deepmerge | 4.3.2 | no lock occurrence | 0 / 0 | Native P pending |
| @vitest/coverage-v8 | 4.1.11 | 4.1.12 | 0 / 0 | Native P pending |
| @vitest/mocker | 4.1.11 | 4.1.12 | 2 / 3 | Native P pending |
| deepmerge | 4.3.1 | no lock occurrence | 1 / 1 | Native P pending |
| postcss-selector-parser | 6.1.4 | 6.1.5 | 1 / 1 | Native P pending |
| qs | 6.16.0 | no lock occurrence; override 6.16.1 | 1 / 1 | Native P pending |
| source-map-js | 1.2.1 | 1.2.2 | 1 / 1 | Native P pending |
| storybook | 10.4.4 | 10.6.2 | 2 / 2 | Native P pending |
| style-dictionary | 5.4.4 | no lock occurrence | 0 / 0 | Native P pending |
| undici | 7.29.0 | 7.30.1 | 18 / 18 | Native P pending |
| vite | 8.0.16 | 8.1.6 | 5 / 5 | Native P pending |
| vitest | 4.1.11 | 4.1.12 | 0 / 3 | Native P pending |

| Identity | Advisory | All primary affected ranges | Base disposition |
| --- | --- | --- | --- |
| @vitest/mocker | [GHSA-qxg6-89mg-rqv8](https://github.com/advisories/GHSA-qxg6-89mg-rqv8) | `>= 2.1.0-beta.7, < 4.1.12`; `>= 5.0.0-beta.1, < 5.0.3` | Applicable: exact base occurrence in range |
| @vitest/mocker | [GHSA-xp26-3454-mjgp](https://github.com/advisories/GHSA-xp26-3454-mjgp) | `>= 4.1.11, < 4.1.12`; `>= 5.0.0-rc.2, < 5.0.3` | Applicable: exact base occurrence in range |
| @vitest/mocker | [GHSA-82fw-gwwq-j7x9](https://github.com/advisories/GHSA-82fw-gwwq-j7x9) | `>= 2.1.0, < 4.1.11`; `>= 5.0.0-beta.1, < 5.0.0-rc.2` | Non-applicable at base: every recorded base occurrence outside ranges |
| deepmerge | [GHSA-gcqx-w48m-w2h4](https://github.com/advisories/GHSA-gcqx-w48m-w2h4) | `>= 4.2.0, <= 4.3.1` | Applicable: exact base occurrence in range |
| postcss-selector-parser | [GHSA-rj75-hqrm-r3gf](https://github.com/advisories/GHSA-rj75-hqrm-r3gf) | `>= 7.0.0, < 7.1.6`; `< 6.1.5` | Applicable: exact base occurrence in range |
| qs | [GHSA-6pq8-jhm2-2vcw](https://github.com/advisories/GHSA-6pq8-jhm2-2vcw) | `>= 6.7.0, <= 6.16.0` | Applicable: exact base occurrence in range |
| source-map-js | [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) | `>= 1.0.0, < 1.2.2` | Applicable: exact base occurrence in range |
| storybook | [GHSA-px85-f4q5-jh77](https://github.com/advisories/GHSA-px85-f4q5-jh77) | `>= 8.0.0, < 8.6.19`; `>= 9.0.0, < 9.1.21`; `>= 10.0.0, < 10.6.2`; `>= 11.0.0-alpha.0, < 11.0.0-alpha.6` | Applicable: exact base occurrence in range |
| storybook | [GHSA-f2ph-cmg5-wxc8](https://github.com/advisories/GHSA-f2ph-cmg5-wxc8) | `>= 8.0.0, < 8.6.19`; `>= 9.0.0, < 9.1.21`; `>= 10.0.0, < 10.6.2`; `>= 11.0.0-alpha.0, < 11.0.0-alpha.6` | Applicable: exact base occurrence in range |
| undici | [GHSA-4w7w-5xrc-9h26](https://github.com/advisories/GHSA-4w7w-5xrc-9h26) | `>= 7.0.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-2gqq-gqf2-x968](https://github.com/advisories/GHSA-2gqq-gqf2-x968) | `>= 7.1.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-4qv8-2p9j-2685](https://github.com/advisories/GHSA-4qv8-2p9j-2685) | `>= 6.5.0, < 6.29.1`; `>= 7.0.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-w293-vg96-wgc3](https://github.com/advisories/GHSA-w293-vg96-wgc3) | `>= 7.24.1, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-8436-99hf-9mmv](https://github.com/advisories/GHSA-8436-99hf-9mmv) | `>= 7.0.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-r53p-7pc4-xj5r](https://github.com/advisories/GHSA-r53p-7pc4-xj5r) | `< 6.28.1`; `>= 7.0.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-3wwx-pv8p-q78v](https://github.com/advisories/GHSA-3wwx-pv8p-q78v) | `>= 6.25.0, < 6.28.1`; `>= 7.28.0, < 7.29.1`; `>= 8.1.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-pmjh-fq2x-6v4x](https://github.com/advisories/GHSA-pmjh-fq2x-6v4x) | `>= 7.11.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-3xpg-4rpp-hhhm](https://github.com/advisories/GHSA-3xpg-4rpp-hhhm) | `>= 7.15.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-rx4f-c7p8-82vq](https://github.com/advisories/GHSA-rx4f-c7p8-82vq) | `>= 7.0.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-9fm3-97px-rjf6](https://github.com/advisories/GHSA-9fm3-97px-rjf6) | `>= 5.15.0, < 6.29.1`; `>= 7.0.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-2m5v-pch6-74hx](https://github.com/advisories/GHSA-2m5v-pch6-74hx) | `>= 4.0.0, < 6.29.1`; `>= 7.0.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-qrxm-fqhp-jwvm](https://github.com/advisories/GHSA-qrxm-fqhp-jwvm) | `>= 4.2.1, < 6.29.1`; `>= 7.0.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-55wc-3pg8-jfw6](https://github.com/advisories/GHSA-55wc-3pg8-jfw6) | `>= 7.15.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-2jfj-6hjv-fm6j](https://github.com/advisories/GHSA-2jfj-6hjv-fm6j) | `>= 7.0.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-f72v-6w45-q472](https://github.com/advisories/GHSA-f72v-6w45-q472) | `>= 7.15.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-rfgv-xxqx-mfg5](https://github.com/advisories/GHSA-rfgv-xxqx-mfg5) | `>= 6.7.0, < 6.28.1`; `>= 7.0.0, < 7.29.1`; `>= 8.0.0, < 8.10.2` | Applicable: exact base occurrence in range |
| undici | [GHSA-xjj6-f33q-929c](https://github.com/advisories/GHSA-xjj6-f33q-929c) | `>= 6.23.0, < 6.29.1`; `>= 7.18.0, < 7.30.1`; `>= 8.0.0, < 8.12.2` | Applicable: exact base occurrence in range |
| vite | [GHSA-rq7h-c2jc-7f22](https://github.com/advisories/GHSA-rq7h-c2jc-7f22) | `>= 8.3.0, <= 8.3.2`; `>= 8.2.0, <= 8.2.3`; `>= 8.0.0, <= 8.1.5`; `>= 7.0.0, <= 7.3.6`; `<= 6.4.3` | Applicable: exact base occurrence in range |
| vite | [GHSA-698v-4r3x-3vcv](https://github.com/advisories/GHSA-698v-4r3x-3vcv) | `>= 8.3.0, <= 8.3.2`; `>= 8.2.0, <= 8.2.3`; `>= 8.0.0, <= 8.1.5`; `>= 7.0.0, <= 7.3.6`; `<= 6.4.3` | Applicable: exact base occurrence in range |
| vite | [GHSA-9jrq-w75r-8gcw](https://github.com/advisories/GHSA-9jrq-w75r-8gcw) | `>= 8.3.0, <= 8.3.2`; `>= 8.2.0, <= 8.2.3`; `>= 8.0.0, <= 8.1.5`; `>= 7.0.0, <= 7.3.6`; `<= 6.4.3` | Applicable: exact base occurrence in range |
| vite | [GHSA-r825-w8mm-5pxw](https://github.com/advisories/GHSA-r825-w8mm-5pxw) | `>= 8.3.0, <= 8.3.2`; `>= 8.2.0, <= 8.2.3`; `>= 8.0.0, <= 8.1.5`; `>= 7.0.0, <= 7.3.6`; `<= 6.4.3` | Applicable: exact base occurrence in range |
| vite | [GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm) | `>= 8.3.0, <= 8.3.2`; `>= 8.2.0, <= 8.2.3`; `>= 8.0.0, <= 8.1.5`; `>= 7.0.0, <= 7.3.6`; `<= 6.4.3` | Applicable: exact base occurrence in range |
| vitest | [GHSA-5xrq-8626-4rwp](https://github.com/advisories/GHSA-5xrq-8626-4rwp) | `>= 4.0.0, < 4.1.0`; `< 3.2.6` | Non-applicable at base: every recorded base occurrence outside ranges |
| vitest | [GHSA-82fw-gwwq-j7x9](https://github.com/advisories/GHSA-82fw-gwwq-j7x9) | `>= 2.1.0, < 4.1.11`; `>= 5.0.0-beta.1, < 5.0.0-rc.2` | Non-applicable at base: every recorded base occurrence outside ranges |
| vitest | [GHSA-9crc-q9x8-hgqq](https://github.com/advisories/GHSA-9crc-q9x8-hgqq) | `>= 1.0.0, < 1.6.1`; `>= 2.0.0, < 2.1.9`; `>= 3.0.0, < 3.0.5`; `<= 0.0.125` | Non-applicable at base: every recorded base occurrence outside ranges |

## R: exact authored intent and solver closure

Authored parameters: undici 7.30.1; storybook 10.6.2; vite 8.1.6;
@vitest/mocker 4.1.12 through vitest, @vitest/coverage-v8 and @vitest/expect
4.1.12; postcss-selector-parser 6.1.5; source-map-js 1.2.2; qs override
6.16.1; deepmerge removal through explicit retirement of Style Dictionary.
No Storybook addon/react-vite upgrade was authored: both remain 10.4.4.
Zod remains 4.6.7 and ws remains 8.21.0. No SDK transition is included.

The qualified Node 24.22.1 / npm 11.19.1 procedure used the same exact frozen base,
explicit registry/config and empty owned HOME for each individual intent and
combined A/B. The native terminal receipt
4a32583ab8b7c848539ade5be6ec97a1613dcbd8b806fa2bc23d070c312b87b5
retains all ten successful resolver runs and full 91-member output. Each used
`npm install --package-lock-only --ignore-scripts --include=dev --include=optional --include=peer`
with its recorded explicit registry/config environment; no force, legacy peer
mode, audit-fix or handwritten lock edit was used. Config bytes and full actual
argv remain in the receipt; this abbreviated command is not a fresh execution.

Classification cabdc237406895f9945fbf83b789da8df1d4a7581dc2196980557b689f68565c
recomputed all ten complete delta arrays. All 166 combined whole-record changes
are partitioned: 11 I_R package rows, 154 individual-replay-witnessed C_R rows,
and one root I_R union. ROOT independently verified 165 whole-record matches,
547 dependency-chain edges and ten manifest edits, with zero unclassified rows.
The combined root record is the authored union, not falsely assigned to one
individual replay. Both combined locks are byte-equal. Imported frontend manifest
SHA-256 is 6ef0942b9126d88cb977ab1d2716902597030423e38d2de2528caf424fc63c52;
lock SHA-256 is 76ca536c003860b573aab1e1ecbbf1c7361ddb512da2d216e287d71ed01d6217.

The qs-only replay selected 6.16.1. The combined graph instead removes qs through
the independently witnessed Style Dictionary/deepmerge removal closure. Its
authored override remains; **installed qs 6.16.1 is not claimed**. Every transition
has its complete before/after record and concrete dependency chain retained,
not merely a matching version. Resolver success does not establish compatibility.

PR 2473 provenance is retained for selector-parser/source-map-js intent:
head dac384c19395ab29e1144779e4edcbdc204fffad, lock blob
79b718ab42380dd6cea88abe5b59f0919c30a8ae. These intents were canonically replayed;
no foreign branch was imported or closed. PR 2499's unrelated root major is excluded.

## Loader and qualification boundary

Evidence: `frontend/style-dictionary.config.mjs:1` owns the bounded eleven-source
reader; `frontend/scripts/build-tokens.mjs:1` retains all existing formatters;
`tests/test_design_token_parity.py:1` owns the independent Python oracle;
`tests/test_frontend_dependency_guards.py:1` enforces current head inventory.
The replacement rejects duplicate decoded keys, aliases/symlinks, unsupported
shapes, conflicting groups and unsafe reference segments. It preserves the
existing typography objects, numeric/insertion order and raw CSS aliases.
All three strings are rendered before any write; IO atomicity is not claimed.
Existing --check behavior still builds then checks drift.

All eleven token source bytes and all three generated CSS/TS/Swift mirrors are
read-only in this transition. Old native baseline is retained and matches them.
New loader byte parity, clean install/executable absence, two full native audits,
frontend typecheck/build/tests/Storybook and final conjunctive P remain UNKNOWN.
The normal install must also qualify the unchanged ws override against current
Storybook requirements; no speculative override update or waiver is permitted.

Run in ROOT's qualified isolated environment: `npm ci`, `npm run tokens:build`,
`npm run tokens:check`, `npm run typecheck`, `npm run test:ci`, `npm run build`,
`npm run build-storybook`; run both owning Python modules with qualified Node
available. Re-run the exact full root/frontend audit02 commands with all includes
and retain all results, new findings and all twelve original-row dispositions.
No token/golden rewrite may hide output drift. Original local narrow gates,
current-head CI, >=97% applicable coverage, reviewer dispositions and merge gates
remain required. No native qualification was executed by this writer.

## Rollback

Reject the candidate on unresolved parity, compatibility, new findings or missing
proof. Restore the coherent manifest/lock/loader/tests together through the owning
ordinary Git process; do not retain a loader importing a removed package or undo
other security work. Historical receipts and all prior failures remain preserved.

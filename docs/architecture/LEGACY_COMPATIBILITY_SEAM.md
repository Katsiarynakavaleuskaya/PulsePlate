# Legacy Compatibility Seam

Status: Accepted guardrail

<!-- LEGACY_SEAM_STATUS: accepted_guardrail -->
<!-- LEGACY_SEAM_RUNTIME_BEHAVIOR_CHANGED: false -->
<!-- LEGACY_SEAM_OPENAPI_CHANGED: false -->
<!-- LEGACY_SEAM_SEMANTIC_CACHE_SERVING: false -->
<!-- LEGACY_SEAM_FOODDB_CUTOVER: false -->
<!-- LEGACY_SEAM_BROAD_REFACTOR: false -->

The runtime-behavior marker above records that this compatibility seam does not
authorize a route/lifecycle/runtime expansion. It does not conceal the separately
reviewed, bounded sanitization of hidden admin error envelopes and the legacy
weekly-plan downstream error boundary documented below.

## Context

`app/bootstrap/application.py` constructs the sole production FastAPI singleton.
`app/main.py` imports it directly and owns additive composition; deployment
remains `app.main:app`. `legacy_app.py` is a transitional compatibility facade
that re-exports the same app, runtime environment, metadata, and lifespan.
Normal imports therefore share one app. The finite package facade resolves
`app.app` directly from `app.main.app` (`app/__init__.py:58-59`); a deliberate
test-only reassignment of `legacy_app.app` cannot rebind package, bootstrap, or
`app.main` authority. Plain `import app`, `dir(app)`, and unknown-name lookup do
not import `legacy_app`. Resolving `app.app` imports `app.main` without loading
`legacy_app`; the canonical bootstrap no longer reverse-imports the compatibility
facade. The eight former paid/BMI registration mirrors are absent from `app`,
`app.main`, and `legacy_app.py`. Twelve bounded Python-binding retirements remove
only the exact 99 `legacy_app.py` Python bindings enumerated below; they do not
remove or redirect any HTTP path, change auth, alter OpenAPI, or change FastAPI
object identity. Repository census found no tracked supported production
consumer of the second ten-name, third eleven-name, fourth eight-name, fifth
twelve-name, sixth seven-name, seventh three-name, eighth seven-name, ninth
fifteen-name, tenth four-name, eleventh four-name, or twelfth eight-name cohort;
it does not prove that no external or dynamic Python consumer exists.

Application startup/shutdown behavior is canonically owned by
`app/bootstrap/lifespan.py`. `app/bootstrap/application.py` passes that exact
context manager to its constructor and `legacy_app.py` only re-exports it.
Food-search clients and the process-wide strategy adapter are acquired and
released inside that lifespan; additive route bootstrap must not create shared
runtime resources or wrap `app.router.lifespan_context`.

App-client API-key extraction and validation dependencies are canonically owned
by `app/routers/api_key.py`. Canonical routers and bootstrap code import those
callables directly. `legacy_app.py` may only re-export the exact same callable
objects while compatibility imports remain; wrappers or mutable legacy-owned
warning state would break FastAPI dependency identity.

Application metadata is canonically owned by
`app/application_metadata.py:56` and constructed through the environment-aware
factory at `app/application_metadata.py:113`. The application bootstrap builds
one immutable value and `legacy_app.py` aliases it for compatibility.

Public OpenAPI visibility, component pruning, builder ownership, and cache
reconciliation are canonically owned by `app/bootstrap/openapi.py:32` and its
validation/install/policy seams at `app/bootstrap/openapi.py:285`,
`app/bootstrap/openapi.py:310`, and `app/bootstrap/openapi.py:343`.
`app/main.py:1097` validates builder ownership before mutation, completes
additive route registration, then applies policy and installs the builder at
`app/main.py:1208-1209`. This order prevents an early partial schema while preserving
an equal cached schema object on a no-op bootstrap.
The seven former legacy Python re-exports `_OPENAPI_ALLOWED_PREFIXES`,
`_OPENAPI_ALLOWED_EXACT`, `_is_openapi_public_path`, `_collect_schema_refs`,
`_prune_unreferenced_schema_components`, `_build_canonical_openapi`, and
`_install_openapi_builder` are retired from `legacy_app.py`. Their exact
canonical objects remain in `app/bootstrap/openapi.py:51-79`,
`app/bootstrap/openapi.py:228`, and `app/bootstrap/openapi.py:375`.
The two policy collections and five callables are available through that
module; the installer alias remains identical to
`install_canonical_openapi_builder`. This retirement changes Python imports
of those legacy names only. The HTTP route table, public schema, builder/cache
policy, and FastAPI app identity remain unchanged. Unknown external or
computed importers must migrate to `app.bootstrap.openapi`.

PR #2412 merged on 2026-09-24T20:13:33Z as
`156bed4034c8de9daded0e5a91014e700563f1d7`, retiring the seven OpenAPI
helper projections and extending the exact-name guard from 61 to 68.
[PR #2419](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2419)
merged on 2026-09-25T04:43:11Z as
`dc24f2f6e4a90d1736c4bf9d2c36d6b8c0609e17`, retiring only the fifteen
BMR/PRO nutrition contract projections:
`BMRRequest`, `BMRRequestLegacy`, `BMRResponse`, `NutrientGapsRequest`,
`NutrientGapsResponse`, `PlateRequest`, `PlateResponse`, `VisualShape`,
`WHOTargetsRequest`, `WHOTargetsResponse`, `Activity`, `DietFlag`, `Goal`, `Sex`,
and `build_who_targets_ui_labels`. The three BMR models remain at
`app/schemas/bmr.py:56-64`; the four `Literal` aliases at
`app/schemas/premium_contracts.py:21-24`; the seven PRO nutrition models at
`app/schemas/premium_contracts.py:39`, `app/schemas/premium_contracts.py:71`,
`app/schemas/premium_contracts.py:80`, `app/schemas/premium_contracts.py:90`,
`app/schemas/premium_contracts.py:143`, `app/schemas/premium_contracts.py:216`,
and `app/schemas/premium_contracts.py:243`; and the labels helper at
`app/schemas/premium_contracts.py:203`. `BMRRequest` and `BMRRequestLegacy`
remain distinct models with the same validation contract. That PR removed
only Python import paths, extended the finite guard from 68 to 83, and left
retained HTTP routes, response models, OpenAPI, and the FastAPI app identity
unchanged. Unknown external or reflective Python importers remain a residual
compatibility risk.

The tenth bounded retirement removes only `DataClass`,
`get_retention_manager`, `LogRetentionManager`, and the unused
`_log_retention_manager` from `legacy_app.py`. The first three remain canonical
in `core/log_retention.py:18`, `core/log_retention.py:196`, and
`core/log_retention.py:33`; the fourth was a facade-local `None` placeholder,
not the core singleton. The live admin service consumes the first two directly
at `app/services/admin_operations.py:21`; privacy cleanup imports the getter
at `core/compliance/privacy.py:10`. This retires only four Python bindings
and extends the exact-name guard from 83 to 87. It does not alter log cleanup,
HTTP routes, auth, OpenAPI, or FastAPI object identity. Unknown external or
computed imports remain a compatibility risk and must migrate to the core owner.

## Planning-schema Python export retirement

The eleventh cohort retires exactly `TargetsIn`, `CanonicalTargetsIn`,
`LegacyWeekPlanRequest`, and `WeeklyMenuResponse` from `legacy_app.py`. Both
former TargetsIn paths identify the one canonical class at
`app/schemas/nutrition_targets.py:41`; the other two classes remain at
`app/schemas/legacy_premium_weekly_plan.py:14` and
`app/schemas/legacy_premium_weekly_plan.py:83`. The canonical schema files and
their validation rules remain unchanged. The independently declared retired
inventory is the original 87 plus these four names, exactly 91. The guard's
recognizer is unchanged; only its four protected-name literals are added.

At admitted base `4ec4a8c3a15cb0bd925d919800840bbe12cdc6d4`, the bounded census
identified 17 selected-name sites in three test files and no recognized
production consumer. Rechecking those three files after canonical-import
migration finds zero selected legacy-name sites: `tests/test_targets_in_parity.py`,
`tests/test_legacy_weekly_plan_alias_api.py`, and
`tests/test_legacy_app_diff_coverage.py`. The static module-symbol count shrinks
from 56 to 52. This cohort check does not establish a complete Python consumer
inventory or authorize another retirement.

The existing retirement probe in `tests/test_legacy_bmi_shims.py` covers both
fresh import orders, ordinary attributes, `vars`, and from-import failures;
it retains network denial and its credential-excluding child environment.
Canonical validation, weekly request modes/goal normalization, response
serialization, and retained HTTP/auth/OpenAPI/app identity contracts remain
required. Unknown external or computed callers must migrate to the canonical
schema modules; these fresh-import checks make no hot-reload guarantee.

Carryover: [PR #2457](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2457)
merged on 2026-09-30T10:35:36Z as
`6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e`. Its malformed-Mapping and overflow
validation correction remains in the canonical TargetsIn validator, with its
regressions preserved during this import migration.
[PR #2466](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2466)
(`codex/retire-legacy-planning-schema-exports`) merged on
2026-10-06T10:47:48Z from approved final head
`96a73949f107ac77ddb507e47520da925e74efda`, with squash
`0b4afbf32a6d1d177c7d4f2e3abb0f9be08b1d1a`. Its directly approved
18-path concurrency repair is inherited material; it supplies no approval to
expand this utility child. Historical R29 remains **PARTIAL / UNWAIVED**, with
no retrospective execution claim.

The predecessor's post-merge receipt records clean main at that squash,
0 ahead / 0 behind, complete tree equality with its approved R4 state, and
focused sanity across eight test families with exit 0. Canonical main
[CI run 37452144570](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/37452144570)
finished SUCCESS: 14 successful jobs, 12 intentional conditional skips,
0 failures, and 0 cancellations. Python 3.11 / 3.12 / 3.13 total coverage was
97.63% / 97.66% / 97.65%, recorded at raw log lines 1857 / 2012 / 1972.
[CD run 37452144603](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/37452144603)
finished SUCCESS with production jobs intentionally SKIPPED; this establishes
no production deployment or global health claim. No own-caused R39 fallout was
observed within those CI, sanity, and CD boundaries. Separate dependency-updater
`unexpected_external_code` and undici `security_update_not_possible` diagnostics
retain their dependency owners and unchanged manifest/lock/configuration proof.

The verified predecessor archive is
[folder 1ndorbw9PcjdFOjG2wFpyqZQP0Ztlgvk2](https://drive.google.com/drive/folders/1ndorbw9PcjdFOjG2wFpyqZQP0Ztlgvk2):

- Git bundle `1gI3o_yyoWclmkpURYB3m9Ib2C8a7kzB-`: 69,702,946 downloaded bytes;
  SHA-256 `deb3bc74f5845e25b34ed950fcea9838c8464e413ca1046a68ab4bd39c115828`;
  native verification exited 0 and restoration recovered the exact R4 head/tree.
- Implementation archive `1Rqx4-8vxuyj6ZNNbT_UbvGepSFicugKT`: 545,235 bytes;
  SHA-256 `688886ceaa3891175bb9af08fa7fd52f21186948bec3012c68077a1fb068e26a`;
  88 regular members / 87 manifest members, with complete downloaded/extracted
  byte and hash equivalence.
- Terminal supplement `1oCzydUZzMfFlz_1vfUXG8JDCZ-ZXYYX4`: 135,093 bytes;
  SHA-256 `e44d9eebccfc61901894fafa6e7fd34106524d2312a68ded6631df7b71a1201e`;
  29 regular members / 28 manifest members, with complete downloaded/extracted
  byte and hash equivalence. It carries actual main CI and owned cleanup receipts.
- Final outcome/continuity package `1pD8CAhQP3boW0Zbpc5154ppnuaRhzGNr`:
  46,175 bytes;
  SHA-256 `4edbea75bb408dff3f79bb66a1cf339ae68655f0cf8d93317818b459851fdb12`;
  12 regular members / 11 manifest members. The historical native
  `postmerge_cloud_outcome_archive_receipt.json`, observed at
  2026-10-06T12:34:00.166117Z, records download/upload equality and every extracted
  member's exact raw bytes and hash, preserving final QA and terminal continuity.
  This is retained predecessor evidence, not a new verification of its archive.

Predecessor owned M/T7 checkouts and local/remote branches are absent. Guarded
local-ref deletion followed native branch-deletion refusal after squash and
verified tree/recovery equivalence. Exact owned temporary resources and stale
Git registrations were removed; foreign worktrees/caches were preserved, with
no global worktree prune. Private preservation of 1,971 files / 359,779,942 bytes
was verified before cleanup. The exact terminal receipts are
`postmerge_owned_cleanup_receipt.json` and `cleanup_owned_stale_metadata_receipt.json`;
foreign master contents and private observer data remain local.

These completed-child receipts are carried in this next substantive utility
child, [PR #2475](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2475)
(`codex/retire-legacy-core-utility-exports`). `PROJECT_LEGACY` remains OPEN. There is no standalone
docs-only closeout PR and no additional cohort authority.
Rollback is a reviewed revert of the whole planning-schema retirement PR,
including its facade, inventories, tests, documentation, and directly approved
concurrency repair.

## Core/utility Python export retirement

The twelfth cohort removes exactly `get_session`, `Language`, `normalize_lang`,
`t`, `FIBER_MIN_G`, `_short_git_sha`, `_is_truthy`, and
`_LEGACY_IMPORT_COMPAT_REEXPORTS` from `legacy_app.py`. The tuple was facade-only
and has no replacement. The first seven objects retain these canonical owners:

| Retired legacy binding | Canonical owner and defining source |
| --- | --- |
| `get_session` | `core.db.get_session`, `core/db.py:961` |
| `Language` | `core.i18n.Language`, `core/i18n.py:415` |
| `normalize_lang` | `core.i18n.normalize_lang`, `core/i18n.py:522` |
| `t` | `core.i18n.t`, `core/i18n.py:481` |
| `FIBER_MIN_G` | `core.targets.FIBER_MIN_G`, `core/targets.py:486` |
| `_short_git_sha` | `app.utils.helpers._short_git_sha`, `app/utils/helpers.py:15` |
| `_is_truthy` | `app.utils.feature_flags._is_truthy`, `app/utils/feature_flags.py:15` |

`Language` remains `Literal["ru", "en", "es"]`, checked through its origin and
arguments. Fiber remains the existing float from `core.targets`; an equal value
in another constants module does not establish owner identity. The package
`app._is_truthy` export remains the exact feature-flags callable. Health retains
the canonical `get_session` dependency key and `_short_git_sha` helper imports
(`app/routers/health.py:13`, `app/routers/health.py:14`); import availability does
not require calling the DB. Canonical implementations and generated clients
remain unchanged.

At admitted base `0b4afbf32a6d1d177c7d4f2e3abb0f9be08b1d1a`, the bounded
tracked-Python census has 1,807 files and two recognized selected consumers:
`tests/test_legacy_app_git_sha.py:11` and
`tests/test_legacy_app_diff_coverage.py:808`. The SHA suite imports the canonical
helper and preserves every digest, whitespace, case, invalid, and short-input
assertion. The fiber assertion resolves `core.targets` at use time and keeps
`int(round(...))` plus its result check. Rechecking tracked imports, aliases,
attributes, literal lookups, and literal patch targets finds no remaining
selected direct consumer or parse error. The discovered computed lookups in
`tests/test_legacy_bmi_shims.py` are explicit absence assertions; the existing
`tests/test_app_public_surface.py:96` loop covers the prior OpenAPI cohort.
Negative fixture strings and historical documentation are preserved. This
bounded census does not prove absence of unknown external or arbitrary
computed callers. The static module-symbol count shrinks from 52 to 44;
that count includes scaffolding and is not a supported public export inventory.

The independent test inventory preserves the previous 91-name prefix and every
historical cohort assertion, then appends exactly these eight unique names for
99. Only eight protected-name literals change in
`scripts/ci/check_legacy_growth_guard.py:133`; its recognition algorithm and
separately owned PR #2433 / #2434 hunks are unchanged. Existing supported binding
forms and exact canonical imports have negative controls. The existing fresh
process probe extends both actual import-order strings while retaining planning
imports, scenario IDs, network denial, credential exclusion, interpreter,
timeout, and diagnostics. It checks namespace absence, `AttributeError`, direct
`ImportError`, canonical Literal/float/function owners, and retained package and
health identities.

The current utility child is [PR #2475](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2475)
(`codex/retire-legacy-core-utility-exports`). Parent `PROJECT_LEGACY` remains OPEN.
Callers of `_LEGACY_IMPORT_COMPAT_REEXPORTS` must remove that dependency; it
has no canonical replacement. Callers of the other seven names must migrate
to their listed canonical owners. These fresh imports make no hot-reload
guarantee. Rollback is a reviewed whole-material
revert of this utility PR, excluding the inherited #2466 workflow repair.

The utility child PR #2475 is CLOSED / MERGED: reviewed head
`d5caf6dee5feddd01014443d373a63cde4e1fc20`, actual squash
`483fc220a18d5a413dc355b2cd5441d667bd2ddc`, merged at
`2026-10-06T23:36:51Z`. Its own local narrow gates, exact-head canonical
CI/security, provider-neutral seal, dispositions, strict wrapper and review
window preceded the approved race-protected squash. Merged-main focused sanity
passed; main CI37547524358 and all seven selected specialized runs succeeded.
Full-main native TOTAL coverage for Python3.11/3.12/3.13 was
97.62%/97.65%/97.65%; numeric diff coverage was N/A from an independently
proven empty eligible-line inventory. Deployment jobs were skipped.
Verified recovery, final same-ID continuity and later owned cleanup receipts
are retained in archive folder `1viMSIUDcDmizMEKUIDOtkofEMe5o7SKi`.
All accepted D1-D8 outcomes require the retained individual 41-item final QA
receipt. PROJECT_LEGACY remains OPEN; R29 remains PARTIAL / UNWAIVED and
the shared-runtime fail-fast learning follow-up remains OPEN. Unknown external
and computed callers remain a bounded residual risk. No standalone docs-only
closeout PR or new cohort authority follows.

## Legacy BMI alias validation prerequisite

The bounded prerequisite `LEGACY-BMI-ALIAS-VALIDATION-1/v1`, branch
`codex/fix-legacy-bmi-alias-overflow`
([PR #2478](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2478)),
adds `OverflowError`
only to the two existing conversion catches in
`app/schemas/bmi_compat.py:43` and `app/schemas/bmi_compat.py:50`.
Failed `weight`, `height`, and `height_cm` conversion still leaves the canonical
field absent for ordinary Pydantic validation; retained `/bmi` and `/plan`
reject the admitted integer-overflow cases with JSON HTTP 422 before service,
calculation consumer, or visualization entry. Valid canonical `weight_kg` and
`height_m` retain priority over unused overflowing aliases. This is bounded
conversion containment, not a universal numeric or external-import safety claim.

Regression evidence belongs to the existing `tests/test_bmi_compat_router.py`
model and HTTP cases, including exact missing-field errors, current registered
route/service binding, zero calls and awaits, and real canonical-precedence
success controls. This prerequisite preserves the distinct `BMIRequest` and
`BMIRequestV1` models, aliases, height units, defaults, route/auth/OpenAPI and
app identities, all seven selected BMI bindings, and both independent 99-name
retired inventories. Its own current-head gates, review, separately approved
merge, post-merge proof, archive, final same-ID continuity, and cleanup remain
pending; the utility child's historical receipts supply no new PASS.

This substantive child carries the completed #2475 utility receipt once.
It does not reclose #2466 or change the independent #2476 guard repair.
`PROJECT_LEGACY` remains OPEN, R29 PARTIAL / UNWAIVED, historical O1
NOT_ADMITTED, and the shared-runtime P1 follow-up OPEN. Shared-document edits
stay within these utility/prerequisite anchors and require a fresh live #2476
comparison before edit, push, and freeze. Actual overlap requires scoped handoff.
Rollback is a reviewed revert of the prerequisite material; the future removal
has a separate rollback boundary.

After this prerequisite's complete lifecycle, the retained removal successor
`LEGACY-BMI-PYTHON-EXPORT-RETIREMENT-1/v1` requires fresh consumer census and
ownership admission, with no predetermined wait for #2476. It removes exactly
`BMIRequest`, `BMIRequestV1`, `MATPLOTLIB_AVAILABLE`,
`generate_bmi_visualization`, `add_visualization_if_requested`,
`_BMI_COMPAT_REEXPORTS`, and `_BMI_SCHEMA_COMPAT_REEXPORTS` from `legacy_app.py`,
for 99 to 106 retired names while preserving canonical models, rendering,
package exports and HTTP contracts. Original successor D1-D8 remain required;
removal is not implemented or admitted by this prerequisite. The successor does
not repeat #2475 reconciliation or import #2476's algorithmic repair.

## Residual Python facade census (log-retention child)

This section preserves the historical log-retention child's census and exact
56-name result. Its tables are historical evidence, not the historical 52-name
planning-schema retirement projection or the current utility projection.

The exact base is `0dccc2ee18d5f88d0753a5cdff384838bd080af7` (`origin/main`
at lane admission). Python's `symtable.symtable(..., "exec")` counted names with
`is_assigned() or is_imported()` in that base's `legacy_app.py`: **60**. The
candidate file after the four-name removal has **56**. This is a static module
symbol inventory, not a supported export list: it includes private names,
typing imports, local scaffolding, conditional imports, and `annotations`.
The exact residual 56-name partition is:

| Classification / canonical owner | Residual names |
| --- | --- |
| Python/typing imports | `annotations`, `logging`, `TYPE_CHECKING`, `Any`, `Callable`, `Optional`, `cast` |
| App construction and metadata: `app/bootstrap/*`, `app/application_metadata.py` | `build_application_metadata`, `APPLICATION_METADATA`, `RUNTIME_ENV`, `_canonical_app`, `lifespan`, `app`, `_app_env`, `_application_metadata`, `tags_metadata`, `_api_description`, `logger`, `bmi_logger` |
| Error details and API-key dependency: `app/http_error_details.py`, `app/routers/api_key.py` | `ENHANCED_PLATE_GENERATION_FAILED_DETAIL`, `INVALID_PREMIUM_PLATE_INPUT_DETAIL`, `_get_api_key_dynamic`, `get_api_key` |
| Schemas: `app/schemas/*` | `BMIRequest`, `BMIRequestV1`, `CanonicalTargetsIn`, `TargetsIn`, `LegacyWeekPlanRequest`, `WeeklyMenuResponse` |
| BMI rendering adapter: `app/services/bmi_compat.py` | `MATPLOTLIB_AVAILABLE`, `add_visualization_if_requested`, `generate_bmi_visualization`, `_BMI_COMPAT_REEXPORTS`, `_BMI_SCHEMA_COMPAT_REEXPORTS` |
| Scheduler, core utilities and compatibility tuple | `get_update_scheduler`, `get_session`, `Language`, `normalize_lang`, `t`, `FIBER_MIN_G`, `_short_git_sha`, `_is_truthy`, `_LEGACY_IMPORT_COMPAT_REEXPORTS` |
| Rate limiting and optional SlowAPI scaffolding: `app/security/rate_limit.py`, `slowapi`, `typing` | `RATE_LIMIT_429_RESPONSES`, `RATE_LIMIT_EXPORTS`, `RATE_LIMIT_INSIGHT`, `_RATE_LIMIT_429_RESPONSES`, `limiter`, `limit_if_available`, `Limiter`, `LimiterType`, `_Limiter`, `slowapi_available`, `_TypeVar`, `_F`, `_LimitValue` |

The tracked direct-consumer scan parsed 89 Python files containing the literal
`legacy_app` out of 1,797 tracked `*.py` files. It recognized explicit
`from legacy_app import name`, `import legacy_app [as alias]` followed by
`alias.name`, and constant-string `getattr(alias, "name")`. The same 16 of the
residual names had 27 name/file pairs at both base and candidate. All 27 pairs
are in tests; there is no recognized production direct consumer. Exact test
consumers are:

| Tracked file | Direct residual names |
| --- | --- |
| `tests/test_api_key_dependency_ownership.py` | `_get_api_key_dynamic`, `get_api_key` |
| `tests/test_app_missing_lines_extra.py` | `get_update_scheduler` |
| `tests/test_app_public_surface.py` | `app`, `get_update_scheduler`, `lifespan` |
| `tests/test_application_instance_ownership.py` | `app` |
| `tests/test_application_metadata.py` | `_api_description`, `_app_env`, `tags_metadata` |
| `tests/test_canonical_application_lifespan.py` | `app`, `lifespan` |
| `tests/test_env_guards.py` | `app` |
| `tests/test_final_coverage_97_boost.py` | `app` |
| `tests/test_health_db.py` | `app` |
| `tests/test_legacy_app_diff_coverage.py` | `BMIRequest`, `FIBER_MIN_G`, `LegacyWeekPlanRequest`, `add_visualization_if_requested`, `app`, `get_update_scheduler` |
| `tests/test_legacy_app_git_sha.py` | `_short_git_sha` |
| `tests/test_legacy_bmi_shims.py` | `BMIRequest`, `BMIRequestV1` |
| `tests/test_legacy_weekly_plan_alias_api.py` | `LegacyWeekPlanRequest`, `WeeklyMenuResponse` |
| `tests/test_targets_in_parity.py` | `TargetsIn` |

Reproduce the census from the repository root with the following read-only
stdlib script. `base` reads committed Git blobs; `candidate` reads the current
checkout. After the material commit, rerun `base` with that commit SHA to check
the committed 56-name projection. `git grep` only narrows the Python parse
candidate list; the AST, not text matches, decides direct uses.

```bash
python3 - <<'PY'
import ast
from collections import defaultdict
from pathlib import Path
import shutil
import subprocess
import symtable

git_bin = shutil.which("git")
assert git_bin is not None
# Public Git commit SHA fixing the census base; it is not a credential.
base = "0dccc2ee18d5f88d0753a5cdff384838bd080af7"  # pragma: allowlist secret

def git(*args):
    return subprocess.check_output([git_bin, *args])

for rev in (base, None):
    source = git("show", f"{rev}:legacy_app.py").decode() if rev else Path("legacy_app.py").read_text()
    symbols = symtable.symtable(source, "legacy_app.py", "exec").get_symbols()
    names = {s.get_name() for s in symbols if s.is_assigned() or s.is_imported()}
    argv = ("grep", "-l", "-z", "legacy_app", rev, "--", "*.py") if rev else (
        "grep", "-l", "-z", "legacy_app", "--", "*.py"
    )
    paths = [p.decode().removeprefix(rev + ":") if rev else p.decode()
             for p in git(*argv).split(b"\0") if p]
    uses = defaultdict(set)
    for path in paths:
        code = git("show", f"{rev}:{path}").decode() if rev else Path(path).read_text()
        tree = ast.parse(code)
        aliases = {a.asname or a.name for n in ast.walk(tree)
                   if isinstance(n, ast.Import) for a in n.names if a.name == "legacy_app"}
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module == "legacy_app":
                for a in n.names:
                    if a.name in names:
                        uses[a.name].add(path)
            elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                if n.value.id in aliases and n.attr in names:
                    uses[n.attr].add(path)
            elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                args = n.args
                if (n.func.id == "getattr" and len(args) >= 2
                    and isinstance(args[0], ast.Name) and args[0].id in aliases
                    and isinstance(args[1], ast.Constant)
                    and isinstance(args[1].value, str) and args[1].value in names):
                    uses[args[1].value].add(path)
    pairs = sum(len(files) for files in uses.values())
    production_pairs = sum(not path.startswith("tests/")
                           for files in uses.values() for path in files)
    print(rev or "candidate", len(names), len(paths), len(uses), pairs, production_pairs)
PY
```

This scan does not resolve arbitrary alias flow, indirect or computed lookups,
import hooks, runtime mutation, generated/untracked files, shell/Markdown
consumers, or external Python packages. It does not justify retiring any of
the other 56 names. The four selected log-retention names had zero recognized
tracked direct consumers at base; their canonical owners and the supported
admin/privacy direct imports are stated above.

Admin scheduler access is canonically exposed by
`app/services/scheduler_access.py` as a lazy typed delegator. The core scheduler
module remains the only singleton and lifecycle owner, while `app` and
`legacy_app.py` expose the exact service callable for compatibility. Admin
operations consume that binding directly; compatibility resolver state and
module-table lookup are forbidden. This access cutover does not change routes,
auth, methods, OpenAPI, scheduler lifecycle, or worker topology. Operational
database-status, force-update, and update-check failures use stable generic 500
details while technical exceptions remain server-log-only.

The following direct-call Python bindings are retired from `legacy_app.py`:
`admin_status`, `cleanup_expired_logs`, `debug_env`, `get_database_status`,
`force_database_update`, `check_for_updates`, `rollback_database`,
`bmi_endpoint`, `plan_endpoint`, and `bmi_endpoint_v1`. Their canonical
implementations remain callable in `app/services/admin_operations.py:27` and
`app/services/bmi_compat.py:138`; HTTP ownership remains in
`app/routers/admin_operations.py:34` and `app/routers/bmi_compat.py:21`.
The `BMIRequest` / `BMIRequestV1` schema compatibility exports and BMI
visualization exports remain explicit in `legacy_app.py:28` and
`legacy_app.py:55`. Unknown external or reflective callers remain residual
compatibility risk; this lane makes no telemetry or consumer-census claim for
them and grants no authority to retire HTTP aliases. Runtime-absence tests prove
only the imported module state produced by the current checked source and test
environment; they do not prove absence under external monkeypatching, import
hooks, or another runtime environment.

The following PRO nutrition direct-call Python bindings are also retired from
`legacy_app.py`: `_resolve_build_targets_callable`, `PlateDependencies`,
`_compute_premium_plate`, `api_premium_plate`, `build_fallback_plate`,
`align_macros_with_targets`, `aggregate_day_micros`,
`premium_targets_legacy`, `api_who_targets`, and `api_nutrient_gaps`.
Canonical Plate direct callers use the typed dependency contract at
`app/services/pro_nutrition_plate.py:257` and the operations at
`app/services/pro_nutrition_plate.py:582`,
`app/services/pro_nutrition_plate.py:768`,
`app/services/pro_nutrition_plate.py:911`, and
`app/services/pro_nutrition_plate.py:927`. Canonical targets/gaps direct callers
use `app/services/pro_nutrition_targets.py:248` and
`app/services/pro_nutrition_targets.py:360`. Retained HTTP aliases remain owned
by the handlers at `app/routers/legacy_premium_nutrition.py:55`,
`app/routers/legacy_premium_nutrition.py:86`,
`app/routers/legacy_premium_nutrition.py:99`, and
`app/routers/legacy_premium_nutrition.py:113`. Existing request/response schemas,
auth, routes, and OpenAPI remain unchanged. The separate Plate helper retirement
below narrows only the Python facade. Unknown external direct imports are an explicit
residual compatibility risk.

The following twelve Plate helper bindings are also retired from `legacy_app.py`:
`DB_TO_ALIAS_NUTRIENT_MAP`, `PlateServiceDependencies`,
`_convert_db_nutrients_to_alias_format`, `_aggregate_meal_micronutrients`,
`_get_recipe_ingredients_for_meal`, `_aggregate_day_micronutrients`,
`_macros_to_kcal`, `sanitize_plate_data`, `_iter_exception_chain`,
`_is_missing_nh3_error`, `_raise_missing_nh3_http_error`, and
`calculate_heuristic_macros`. Their existing canonical objects remain owned by
`app/services/pro_nutrition_plate.py:257`, including the nutrient map constant
at `app/services/pro_nutrition_plate.py:287` and the helper implementations from
`app/services/pro_nutrition_plate.py:299`. Canonical calculation, aggregation,
dependency-injection, sanitization, and error behavior stay unchanged. The
separate supported package export `app._macros_to_kcal` remains the exact
canonical callable (`app/__init__.py:49`). Fresh-process retirement tests in
`tests/test_legacy_bmi_shims.py` cover namespace, attribute, and from-import
absence plus canonical availability; they do not establish absence of unknown
external or computed importers.

The following seven nutrition utility projections are also retired from
`legacy_app.py`: `MANDATORY_MICRO_DEFAULTS`, `MAX_DAILY_KCAL`,
`MICRO_ALIAS_MAP`, `MIN_DAILY_KCAL`, `_alias_micros`, `_clamp_daily_kcal`,
and `_ensure_priority_micros`. Direct callers import the four constants and
three functions from `core/nutrition_utils.py:25-81`; targets/gaps service
tests verify the three function identities at
`app/services/pro_nutrition_targets.py:25`. The canonical calculations and
mutable micronutrient inputs are unchanged. Repository census found no tracked
supported production consumer of these seven legacy names, but unknown
external or dynamic Python imports remain a bounded compatibility risk;
those callers must migrate to `core.nutrition_utils`. This retirement makes no
claim about HTTP aliases, DTOs, OpenAPI, or `app._macros_to_kcal`.

The three targets/gaps service re-exports `_generate_who_targets_response`,
`_fallback_targets_response`, and `analyze_nutrient_gaps_response` are also
retired from `legacy_app.py`. Their canonical callables remain at
`app/services/pro_nutrition_targets.py:248`,
`app/services/pro_nutrition_targets.py:118`, and
`app/services/pro_nutrition_targets.py:360`. Repository-owned behavior tests
call the canonical service with the existing request schema, inputs, patches,
and assertions. The retained HTTP aliases, DTOs, OpenAPI, and FastAPI app
identity are unchanged. Unknown external or dynamic importers of these three
legacy names must migrate to the canonical service.

The following planning/export direct-call Python bindings are also retired from
`legacy_app.py`: `analyze_nutrient_gaps`, `make_daily_menu`,
`make_weekly_menu`, `repair_week_plan`, `make_plate`,
`build_nutrition_targets`, `to_csv_day`, `to_pdf_day`, `to_csv_week`,
`to_pdf_week`, and `WeeklyPlanFlexibleRequest`. Planning implementations remain
owned by `core/menu_engine.py:114`, `core/menu_engine.py:179`,
`core/menu_engine.py:562`, and `core/menu_engine.py:589`; Plate and target
implementations remain owned by `core/plate.py:268` and
`core/recommendations.py:39`. All four byte-returning export implementations
remain owned by `core/exports.py:54`, `core/exports.py:104`,
`core/exports.py:170`, and `core/exports.py:263`.
`WeeklyPlanFlexibleRequest` is removed without substituting the distinct
`LegacyWeekPlanRequest` or `WeeklyMenuResponse` contracts in
`app/schemas/legacy_premium_weekly_plan.py:14` and
`app/schemas/legacy_premium_weekly_plan.py:83`. The exact synthetic
`legacy_app.routers.plan_export` namespace is retired separately from those
eleven ordinary bindings; `app/routers/plan_export.py:61` and
`app/routers/plan_export.py:62` remain the canonical module/router owners.
These removals do not change the sign, weekly CSV, weekly PDF, or retained
premium weekly-plan HTTP paths; their auth, signed-token, rate-limit, response,
OpenAPI, and FastAPI-identity contracts remain unchanged. Unknown external
direct imports remain an explicit residual compatibility risk.

The former synchronous `legacy_app.start_background_updates` /
`legacy_app.stop_background_updates` wrappers, their private scheduler bindings,
the `app.scheduler_helpers` resolver module, and the implicit `app_module`
module-table alias are retired. Canonical startup and shutdown continue to use
direct typed hooks in `app/bootstrap/lifespan.py`; scheduler mode, ordering,
timeouts, cleanup, and worker topology are unchanged. Retained package and
legacy `get_update_scheduler` exports remain the exact callable owned by
`app/services/scheduler_access.py`.

The canonical weekly-menu builder remains owned by
`core/menu_engine.py`. The hidden legacy premium weekly-plan route obtains the
exact callable through the lazy, uncached access seam in
`app/services/legacy_premium_weekly_plan.py`; it no longer selects mutable
`app`/`legacy_app` facade state or reads the module table. The service also owns
legacy response normalization, while `app/routers/legacy_premium_weekly_plan.py`
owns the hidden HTTP compatibility boundary. Public `app.make_weekly_menu` and
`app.build_nutrition_targets` remain exact package compatibility exports; the
`legacy_app.make_weekly_menu` and `legacy_app.build_nutrition_targets` bindings
are retired and must not be recreated. Exact canonical-module absence retains
the existing unavailable `503`; broken imports and unknown downstream errors
are logged server-side and exposed only through the stable generic `500`
envelope. Route auth, VIP/FitChef execution, OpenAPI, and application identity
remain unchanged.

Legacy matplotlib/base64 BMI rendering remains owned by
`bmi_visualization.py`. `app/services/bmi_compat.py` is the sole runtime
consumer for the hidden `/bmi` compatibility route and owns the legacy response
normalization around that renderer. Public `app` and `legacy_app.py`
visualization symbols remain import compatibility only; rebinding either
facade must not influence runtime renderer selection. The structured
`BMIScaleV1Spec` path in `app/services/bmi_visualization.py` is a separate
canonical contract and is not part of this compatibility seam.

Insight request/response schema ownership is canonical in
`app/schemas/insight.py`. The thin adapter in
`app/services/insight_compat.py` owns retained direct-call behavior, provider
and transparency adapters, quota enforcement, and sanitized failure envelopes;
it delegates orchestration to `app/services/insight_application_service.py`.
The hidden router in `app/routers/legacy_insight.py` imports canonical schemas,
security, and rate-limit policy and resolves adapter callables from
`app.services.insight_compat` at request time. The following ordinary
`legacy_app.py` bindings are retired: `INSIGHT_TEXT_MAX_LENGTH`,
`InsightRequest`, `RAGSourceItem`, `InsightResponse`,
`INSIGHT_TEMP_UNAVAILABLE_MESSAGE`, `_execute_insight_request`, `insight_v1`,
and `insight`. Their canonical schema/service owners remain callable, while
both retained routes stay hidden from OpenAPI and `/insight` remains deprecated.
Canonical router, schema, adapter, and service modules must never import or
dynamically look up the legacy facade. Unknown external direct importers remain
an explicit residual compatibility risk.

PR #2343 merged the bounded fourth eight-name Insight retirement at
`8243c30e7989713cc9c2d3d77ed5dd5ec389144b`. Before another legacy-retirement
child, the operator selected canonical mapped-model registration as a separate
prerequisite: `core/db.py:730` explicitly registers the current packet-bound
mapped set for named schema-creation consumers, `core/db_fallback.py:93` reuses
that action for fallback initialization, and `tests/test_db_model_registry.py:14`
freezes the exact current class/table identities and import-order behavior. This
prerequisite does not change model definitions, migration files, or schema
declarations. It does change schema-creation output for fresh standalone
`create_tables()` and local/dev/test fallback paths whose former independent
imports exposed empty or core-only metadata: those paths now materialize the
existing exact 16 mapped tables. It makes no Alembic revision/autogenerate
parity, migration-only table, or OpenAPI completeness claim.
The loader also rejects any missing or extra mapped class/table and completes
SQLAlchemy mapper configuration before a named consumer initiates new
engine/file/table schema work or calls `create_all`; registry and configuration
failures propagate without partial schema creation from that consumer action.
Pre-existing long-lived sync or async engine state may already exist and is not
retroactively covered by this ordering claim.

The current policy is compatibility first:

- keep existing legacy routes callable when current clients still depend on
  them;
- hide or internalize legacy surfaces from public OpenAPI when the canonical
  route family owns the public contract;
- put new canonical route growth in `app/routers/` and `app/bootstrap/`, then
  register it through `app/main.py`;
- keep product truth, entitlement truth, AI runtime truth, FoodDB authority, and
  OpenAPI contract truth out of `legacy_app.py`.

## Decision

Freeze `legacy_app.py` as a compatibility seam. It may shrink or delegate more
thinly over time, but it must not grow new product behavior.

PR #2294 completed canonical FastAPI construction ownership. The bounded
`codex/retire-legacy-scheduler-app-module-compat` successor removed only the
package module alias and legacy synchronous scheduler compatibility rail. The
next bounded lane landed as PR #2309 at
`f561d37b2f0ad70b9d5ada9251572b0c9e033aac`, retiring the eight paid/BMI
registration mirrors and the canonical reverse import without changing route
registration. PR #2314 then merged at
`827f8ea0ba5bf0432e011241d08553b01fa471b1`, adding canonical PRO BMR and
nutrient-gap routes and moving the repository-owned Web Nutrition Setup BMR
consumer to the canonical namespace. The bounded
PR #2317 removed only the first ten direct-call Python bindings enumerated
above and added a closed, exact-name regression guard. PR #2322 merged at
`d96314454935862bc2a694c1e594648c011081ba`, removing only the second ten-name
PRO nutrition cohort and extending that exact-name set without changing the
recognizer. PR #2336 merged at
`ece5250305d3d65f47fa75c64bf9b55b5e5158de`, removing only the third
eleven-name planning/export cohort plus the exact synthetic
`legacy_app.routers.plan_export` namespace and extending the same recognizer to
31 names. PR #2343 merged at
`8243c30e7989713cc9c2d3d77ed5dd5ec389144b`, removing only the fourth
eight-name Insight Python projection and extending the same exact-name data to
39 without changing recognizer semantics. PR #2349 merged canonical ORM model
registration at `942cc0f10995d89be74f5ffc7ab9329809865e0b`, and PR #2355 merged the bounded PostgreSQL
ORM/Alembic drift reconciliation at
`a157d445c98c3e4bea76bd95c2a8d333c99725c1`.
[PR #2365](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2365)
(`codex/alembic-autogenerate-completeness`) merged at
`9cf03aba9aa127b3d5f4bbd790c51458721cc202`. Its positive claim remains only
`bounded_exact_head_autogenerate_admission=PASS`, with physical PostgreSQL
descriptor evidence and CI routing; it does not change runtime behavior,
register or access a FoodData database, or retire a legacy surface. The next
bounded child, [PR #2388](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2388)
(`codex/retire-legacy-plate-helper-exports`), merged on 2026-09-10 at
13:11:06 UTC as `c845a7e5e6a8af4c0678608c8d3996dafe1ae323`. It retired
exactly the twelve Plate helper bindings above, extended the retired-name
data from 39 to 51, and included the merged #2365 ledger reconciliation.
[PR #2402](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2402)
(`codex/retire-legacy-nutrition-utils-exports`),
merged on 2026-09-23 at 14:32:10 UTC as
`ab7da79ce12cbd25537df57551b57b31e69409d0`. It retired only the seven
`core.nutrition_utils` projections above and extended the same name set from
51 to 58 without changing its recognizer. The later bounded child,
[PR #2407](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2407)
(`codex/retire-legacy-targets-gaps-service-exports`) retired only the three
targets/gaps service projections above, extending the exact-name set from 58 to
61 without changing its recognizer. PR #2412 then merged the seven OpenAPI
helper projections above as `156bed4034c8de9daded0e5a91014e700563f1d7`,
and PR #2419 merged the fifteen BMR/PRO nutrition projections as
`dc24f2f6e4a90d1736c4bf9d2c36d6b8c0609e17`.
[PR #2449](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2449)
merged on 2026-09-28T20:49:16Z as
`0151b9416804b36fd80834a76989965eb958c03c`, completing the four-name
log-retention retirement and census above. The parent Legacy epic remains open.
All retained Insight HTTP routes, all four versioned nutrition aliases, and
both root aliases remain callable. Versioned-alias retirement, root-alias
auth/sunset, retained Insight HTTP-alias retirement, and final legacy deletion
remain separate ordered
lanes behind their own evidence
(canonical route evidence: `app/routers/pro_nutrition_contracts.py:61` and
`app/routers/pro_nutrition_contracts.py:72`; bounded registrar evidence:
`app/bootstrap/pro_contracts.py:246`; Web consumer evidence:
`frontend/src/api/premium/bmr.ts:4`).

Allowed in `legacy_app.py`:

- existing compatibility aliases and response shaping;
- removal or narrowing of legacy surface;
- thin delegation to canonical routers, services, or core helpers;
- comments or markers that document the seam.

Forbidden in `legacy_app.py`:

- new `@app.*` routes;
- new `app.include_router(...)` or `app.add_api_route(...)` registrations;
- new `app.routers.*` imports for product route growth;
- new provider or LLM calls;
- new billing, entitlement, subscription, receipt, quota, or API-key behavior;
- new OpenAPI-visible public surface;
- semantic-cache serving, FoodDB cutover, DB writes, or broad refactors.

## Ownership Map

| Surface | Owner | Rule |
| --- | --- | --- |
| Existing legacy compatibility aliases | `legacy_app.py` | Runtime compatibility only; no growth; paid/BMI registration mirrors are retired. |
| FastAPI construction | `app/bootstrap/application.py` | Sole production constructor; no routes, middleware, OpenAPI, or resources. |
| Canonical app composition | `app/main.py` | Additive, idempotent registration on the supplied app; never rebind the singleton. |
| Package app facade | `app/__init__.py` | Finite lazy exports; `app.app` resolves only from `app.main.app`; no `app_module` alias. |
| New route implementations | `app/routers/` | Canonical route families own new behavior. |
| Operational health/readiness routes | `app/routers/health.py` + `app/main.py` | Runtime paths unchanged; no legacy decorator ownership. |
| Infra and observability bootstrap | `app/bootstrap/` | Register from canonical entrypoint, not from `legacy_app.py`. |
| Application lifecycle and shared resources | `app/bootstrap/lifespan.py` | One explicit startup/shutdown owner; deterministic reverse-order cleanup. |
| App-client API-key dependencies | `app/routers/api_key.py` | Canonical owner; legacy compatibility is identity-preserving re-export only. |
| Application metadata | `app/application_metadata.py` | Immutable source; every FastAPI projection receives fresh nested mutable inputs. |
| Public OpenAPI policy and builder | `app/bootstrap/openapi.py` | Validate before mutation; install after complete route bootstrap; stale/foreign state fails closed. |
| Hidden admin/debug routes | `app/routers/admin_operations.py` | Canonical HTTP owner; route methods, auth, hidden OpenAPI posture, and response contracts remain unchanged. |
| Admin/debug operations | `app/services/admin_operations.py` | Canonical direct-call owner; the seven former `legacy_app.py` bindings are retired. |
| Admin scheduler access | `app/services/scheduler_access.py` | Lazy typed delegation only; core owns singleton/lifecycle and compatibility exports preserve service-callable identity. |
| Scheduler startup/shutdown | `app/bootstrap/lifespan.py` + `core/food_apis/scheduler.py` | Direct typed hooks only; no legacy sync wrappers, helper resolver, module-table lookup, or caller-frame precedence. |
| Legacy weekly-menu builder access | `core/menu_engine.py` + `app/services/legacy_premium_weekly_plan.py` | Core owns the builder; the service provides lazy exact-callable access and response normalization; facade exports are compatibility only. |
| Planning direct-call runtime | `core/menu_engine.py` + `core/plate.py` + `core/recommendations.py` | Canonical implementations remain callable; the eleven-name planning/export cohort stays absent from `legacy_app.py`, while the finite `app` package facade retains only its reviewed exports. |
| Export direct-call runtime | `core/exports.py` | All four byte-returning CSV/PDF implementations remain canonical; no `legacy_app.py` placeholders or aliases. |
| Plan-export HTTP routes | `app/routers/plan_export.py` + `app/main.py` | Canonical routers retain exact endpoint, auth, signed-token, rate-limit, response, operation-identity, and public-OpenAPI behavior; no synthetic `legacy_app.routers.plan_export` namespace. |
| Legacy BMI visualization access | `bmi_visualization.py` + `app/services/bmi_compat.py` | The renderer owns chart generation; the service consumes local bindings and normalizes compatibility responses; facade exports are compatibility only. |
| Legacy BMI routes and direct-call runtime | `app/routers/bmi_compat.py` + `app/services/bmi_compat.py` | HTTP routes remain unchanged; the three former `legacy_app.py` endpoint bindings are retired while schemas and visualization exports remain. |
| Insight API contract | `app/schemas/insight.py` | Canonical request/response ownership and wire shape remain; the four former schema/constants projections are retired from `legacy_app.py`. |
| Insight compatibility routes | `app/routers/legacy_insight.py` | The two hidden VIP routes own route-level guards and consume canonical adapter attributes at request time; the legacy facade is not a runtime dependency. |
| Insight compatibility runtime | `app/services/insight_compat.py` + `app/services/insight_application_service.py` | The adapter owns retained callables and HTTP/error seams; the application service and `core/ai` retain orchestration truth. The four former callable/message projections stay absent from `legacy_app.py`; facade rebinding and reverse imports are forbidden. |
| PRO targets/gaps API contracts | `app/schemas/premium_contracts.py` | Canonical request/response ownership and wire shapes; the former `legacy_app.py` schema and alias projections are retired. |
| PRO targets/gaps runtime | `app/services/pro_nutrition_targets.py` + `core/nutrition_utils.py` | The service owns typed targets/gaps orchestration and stable error envelopes; core owns shared kcal/micronutrient helpers; retired facade callables and seven nutrition utility projections stay absent while service imports retain exact core function identity. |
| PRO targets/gaps routes | `app/routers/pro_nutrition_contracts.py` + `app/routers/legacy_premium_nutrition.py` | Canonical targets/gaps and retained compatibility routes call the service directly; the canonical family uses `require_pro_tier`, while legacy API-key behavior remains unchanged. |
| PRO Plate API contract | `app/schemas/premium_contracts.py` | The existing `PlateRequest` / `PlateResponse` wire shapes remain shared by canonical and retained routes. |
| PRO Plate runtime | `app/services/pro_nutrition_plate.py` + `core/` nutrition modules | The service owns typed Plate orchestration, bounded fallbacks, required sanitization, and stable error envelopes through direct core dependencies resolved per call; facade lookup, module-table lookup, mutable dependency registries, and import-time callable caches are forbidden. Retired direct-call and twelve helper bindings stay absent from `legacy_app.py`; the separate package export `app._macros_to_kcal` remains the exact service callable. |
| PRO Plate routes | `app/routers/pro_nutrition_contracts.py` + `app/routers/legacy_premium_nutrition.py` | Canonical and retained Plate handlers call the canonical service directly. Existing PRO-tier/API-key divergence, deprecation metadata, response models, and OpenAPI visibility remain unchanged. |
| Premium BMR API contract | `app/schemas/bmr.py` | Both retained request DTOs enforce the same finite core boundaries; the existing `BMRResponse` wire shape remains shared. |
| Premium BMR runtime | `app/services/pro_nutrition_bmr.py` + `core/bmr.py` | The service owns request-time feature gating, defensive dependency validation, localization, response assembly, and stable fail-closed errors through direct core callables resolved per call. Dynamic facade/module lookup, synthetic success stubs, and fallback TDEE values are forbidden. |
| PRO and retained BMR routes | `app/routers/pro_nutrition_contracts.py` + `app/routers/legacy_premium_nutrition.py` | `/api/v1/pro/nutrition/bmr` is the public PRO contract and Web consumer target. `/api/v1/premium/bmr` retains the app-client API-key dependency, `/premium_bmr` remains the historical public exception, and all three delegate directly to the same feature-gated service. |
| Domain logic | `core/` and `app/services/` | Backend truth stays outside route shims. |
| Public API contract | Backend OpenAPI gates | Legacy aliases must not become client contract truth. |

## Guard Contract

`scripts/ci/check_legacy_growth_guard.py` enforces this seam with static source
analysis. It parses `legacy_app.py` and the canonical lifecycle/food-search
bootstrap modules without importing application modules. It compares route,
router-import, and sensitive-call facts against the frozen baseline and rejects
legacy lifecycle implementations, startup/shutdown event registration, or
hidden `lifespan_context` mutation. It also rejects legacy API-key dependency
implementations and canonical `app/**` reverse imports or dynamic lookups for
those callables. Current facts may disappear as the seam shrinks; new facts fail
closed with repo-relative diagnostics.

For the 99 retired Python bindings, the guard has a deliberately bounded
finite mechanical claim over the exact repo-relative `legacy_app.py` source
only. It freezes the exact 99-name set, uses the existing `_assigned_names`
collector for statically visible ordinary module-scope `Name` Store/Del
bindings, rejects explicit `global` declarations for a protected name, rejects
all star imports, and rejects a statically bound module-level `__getattr__`.
Unreadable source and `SyntaxError` fail closed. Comments, strings, function or
class locals without `global`, foreign object attributes, underscore/different
names, and canonical owner modules outside `legacy_app.py` are outside this
finite binding set.

The containing `legacy_app.py` module is parsed into an AST, but the
retired-binding rule does not recognize or interpret dynamic carrier families:
`globals()` / `locals()` / `vars()`, `sys.modules`, module `__dict__`, `setattr`
/ `delattr` in bare, imported, qualified, aliased, destructured, chained, or
bound forms, mapping `update` / `__setitem__` / `__ior__`, `eval` / `exec`,
import hooks, reflection, arbitrary helpers, and external monkeypatching. The
rule neither accepts nor certifies those families and makes no completeness
claim about them. Any new or changed dynamic namespace carrier in
`legacy_app.py`, and any dynamic carrier intended to bind or rebind one of the
99 protected names, requires manual STOP and review. The existing router-import
recognizer separately rejects reintroduction of the former exact dynamic
`app.routers.plan_export -> _plan_mod` fact; this does not widen the ordinary
binding rule or certify arbitrary namespace mutation.

The same guard now verifies application-metadata/OpenAPI ownership: extracted
functions cannot be redefined or rebound in legacy, `app/main.py` must import
the canonical OpenAPI lifecycle directly, the package facade cannot install OpenAPI,
and canonical modules cannot reverse-import the compatibility app. The check is
bounded AST analysis and intentionally does not interpret arbitrary Python.

The guard does not authorize runtime behavior. It only prevents unreviewed seam
growth while later extraction PRs move routes behind canonical routers.

## Static Guard Threat Model

The legacy growth guard is an architectural regression detector for trusted,
reviewed repository source. It detects explicit ownership violations, direct
reverse imports and lookups, and the finite ordinary module bindings described
above.

It is not a Python sandbox, abstract interpreter, or proof against intentionally
obfuscated source. Descriptor, metaclass, closure, arbitrary container or
data-flow, `eval` / `exec`, dynamic import consumers, and equivalent reflective
constructions remain residual risk subject to human review and repository
security tooling. The exact-name binding guard must not be widened to imply a
complete census of open-world namespace mutation or runtime consumers.

Runtime contract tests, callable-identity tests, code review, targeted security
review, and current-head CI remain authoritative.

## Exit Criteria

Retire this seam only when all are true:

1. `app/main.py` no longer depends on `legacy_app.app` as the runtime base.
2. Remaining compatibility aliases are either removed or implemented as bounded
   canonical router shims.
3. OpenAPI namespace guards stay deterministic after removal.
4. Auth, billing, export, insight, food-data, and websocket contracts have route
   parity coverage for any moved surface.
5. Backlog or PR governance records the final compatibility retirement evidence.

## Validation

Use:

```bash
python3 scripts/ci/check_legacy_growth_guard.py
pytest -q tests/test_legacy_growth_guard.py
```

This guard does not open runtime behavior, OpenAPI, semantic-cache serving,
FoodDB cutover, or broad refactor scope.

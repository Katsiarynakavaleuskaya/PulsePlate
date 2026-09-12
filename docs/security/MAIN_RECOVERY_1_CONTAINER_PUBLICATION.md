# MAIN-RECOVERY-1: image security and publication recovery

## Current continuation: original-build admission and protected staging

The owner accepted one new implementation carrier,
`codex/main-recovery-secure-staging`, from main
`5b384c91708f774c025b0b19edc1c8c83d11266b`. It retains PostgreSQL 15.19,
pgvector 0.8.6 and the frozen Alpine image. The target is the existing staging
Droplet `594869239`, not production; the accepted storage budget is one 50 GiB
DigitalOcean Volume at $5/month. Actual host access, provisioning and activation
remain unproved until their operational receipts exist.

Exact-main CD run
[34700002720](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/34700002720)
reached the derived attestation action and failed with:

```text
Failed to persist attestation: Invalid Argument - unsupported build type:
https://pulseplate.app/buildtypes/postgres-pgvector/v1
```

Custom SLSA build types are not intrinsically invalid. This failure establishes
an incompatibility with GitHub persistence for this exact type, not a general
SLSA prohibition or an inability to build PostgreSQL. The remediation delegates
native SLSA production to the pinned GitHub action and preserves the exact
PulsePlate recipe/material assertions under a distinct custom predicate URI.

Native GitHub SLSA, PulsePlate materials/v1 and SPDX are verified conjunctively
against one subject and original certificate source/workflow/run/attempt. The
shared bounded helper compares exact material records before redaction. Actual
build executions may complete their own missing tuple members; historical
proofs are retained. Read-only reuse selects an existing complete compatible
tuple and cannot author a new-build claim. Actual native Trivy documents exposed 246 changed scalar fields, including
package identities, relationships and package annotation dates. The prior
three-field normalization was stopped. Materials now bind the entire original
parsed SPDX predicate using sorted compact UTF-8 JSON (ensure_ascii=False,
allow_nan=False) and SHA-256, retaining array order and every content field.
This is parsed-document identity, not raw-file byte identity or semantic
equivalence of regenerated documents. Reuse retains that original signed
document/hash; the independently blocking fresh image scan remains required. Classifier and terminal
checks compare the same finite compatibility rules over both Git trees.
Evidence anchors: `scripts/ci/check_pgvector_attestations.py:1`,
`tests/test_pgvector_attestations.py:1`, `.github/workflows/cd.yml:1`.

The premerge integration transport uses an explicit same-repository push to
`codex/attestation-probe/<exact-full-sha>` because a new `workflow_dispatch`
trigger is not dispatchable before it exists on the default branch. This is a
temporary synthetic-only branch, not another PR or a direct push to main.
The checked-out SHA and ref suffix must equal the event SHA. The job receives
no DHI credentials and cannot promote a runtime tag or enter a deploy job.
The resulting native signer/ref identity stays literal; it is not rewritten as
main. The probe exercises external persistence and OCI verification only;
actual merged-main PostgreSQL publication/reuse remains independently required.

The ready-made DHI pgvector alternative was examined independently. Native
Trivy 0.74.0 with database updated `2026-09-12T13:01:09Z` reported three CRITICAL
and eighteen HIGH entries on linux/amd64 digest
`sha256:6483fa1212f6d5962cb00d6677a6b0b00ff0cb0ecc50afd3856c063aa016bb45`.
That reporting invocation exited zero because it did not use `--exit-code 1`;
zero is not a security admission. The candidate also changes Debian/PGDATA
contracts, so this continuation does not replace the selected Alpine image.

Staging v5 explicitly requires TLS-only PostgreSQL network authentication,
verify-full libpq clients, file-backed database credentials and protected
certificate mounts. A root-owned local storage receipt is bound to actual
DigitalOcean device name, filesystem UUID, exact writable mount and capacity.
Named PostgreSQL/Prometheus volumes and local backups must use that mount;
credential files are bind-mounted from its protected secrets directory.
The Docker service's systemd mount dependencies and disabled live restore
extend the boundary to daemon restart/mount loss, while backups independently
check the mount before writing. Existing mismatched volumes fail closed and
remain preserved. Configuration, provider encryption statements and actual
runtime observations remain separate evidence.
Evidence anchors: `scripts/ops/check_staging_security.py:1`,
`deploy/systemd/pulseplate-staging-storage.conf:1`, `scripts/deploy.sh:1`.

Premortem exposed partial-attestation recovery, selected-Compose versus ambient
DB identity, omitted backup material owners and premerge trigger eligibility.
Their closure is executable in this same diff. Euler uses prospective local
family/episode evidence; Telos preserves each original MAIN-RECOVERY-1 criterion
and the owner-added staging criteria; the zero-network Apple Container Runner
provides oracle-only review. No experiment or role report grants merge,
production, crypto-provider success or operational-completion authority.

Current validation and future native receipts must remain distinguished in
closeout. Full local make verify is not part of this lane. The final outcome
still requires exact-head PR gates, separately authorized merge, actual new-main
CD and repeat/reuse, trusted staging deployment, TLS negative controls,
backup/restore and Prometheus persistence, plus same-ID readback of the four
existing Drive continuity records. No main/staging completion is claimed here.

## Native command security dispositions

The complete pre-commit hook checks low-severity findings as well as higher
severities. It reported six generic B404/B603 import/call alerts at
`scripts/ci/check_pgvector_attestations.py:15`,
`scripts/ci/check_pgvector_attestations.py:426`,
`scripts/ci/check_staging_postgres_runtime.py:17`,
`scripts/ci/check_staging_postgres_runtime.py:46`,
`scripts/ops/check_staging_security.py:17` and
`scripts/ops/check_staging_security.py:104`.
The coordinator reviewed the security role's caller assessment and found no
safer bounded replacement: these paths deliberately delegate tracked Git
trees, Docker/PostgreSQL protocols and native mount/TLS/daemon recognition.
Each uses an absolute resolved executable, argv without shell interpretation
and a bounded timeout; the Git path disables replacement objects, while native
runtime errors redact sensitive diagnostics.

Exactly these six sites have rule-specific inline dispositions through
2026-10-12 under the existing no-safe-code-fix policy. No scanner configuration,
severity or path allowlist changes. Native executable and caller argument trust
remain review obligations; shell avoidance does not establish tool semantics
or signature validity. The
[bounded follow-up](../roadmap/BACKLOG_LEDGER.md#ledger-p1-native-cli-subprocess-review)
requires reassessment before expiry. Actual all-files hook and nosec/absolute
binary guards remain required evidence.

## Outcome and authority

The operator accepted one bounded recovery carrier on 2026-09-09:
`codex/main-ci-image-security-recovery`. Its outcome is successful applicable
CI/CD on the final merged main, followed by local sanity and retained evidence.
This document records implementation evidence; it grants no merge, deployment,
credential, production-database, or volume authority.

Baseline: `e5d162168a866b64f1750f396e6034643f210cca`, the squash merge of
PR #2347. PR #2371 previously merged as
`87feb5272ca81aa698416c5ed999d26e79f21b2a`. Both repository deliveries remain
completed; the post-merge operational failure is owned by this recovery.

The explicit scope joins Docker/Scout execution context and cleanup, the frozen
backend-image findings, one Caddy gRPC replacement, three expired review
decisions, and pre-publication image-scan parity. Separate Dependabot updater
failures and new npm/pip alerts are retained in the dependency queue and do not
become hidden dependency changes in this carrier.

## Post-merge Statement consumer recovery

PR #2387 was squash-merged as `28f518b1e44715c28597f51d9ded78346abaa824`.
On that SHA, canonical CI `34403818879` (including all three main Python
versions and coverage-main), Frontend/Caddy, Docker Build and Push, CD-Test,
Trivy, CodeQL, Actionlint and accessibility passed. CD was the sole failing
pipeline in that nine-workflow push/workflow-run snapshot; the separately
queued dependency updater is outside the accepted CI/CD recovery DoD.
Backend publish-image-scan artifact `10124716347` from run `34403818939`
reports Trivy 0.74.0, zero blocking findings and all ten blocked Debian packages
absent. Its image config ID is
`sha256:58a5add42b39572462426b9788cff5bc32c7ad9ff2abd905a9a609b12bc81150`.
This supports backend image closure, independently of PostgreSQL CD below.
[CD run 34403818948, job 102643305050](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/34403818948/job/102643305050)
authenticated both Scout calls, verified their signatures and wrote both source
files. Owned builder cleanup succeeded. The subsequent Python consumer failed:
`dhi-postgres-runtime-provenance.json is not one in-toto v1 statement`.

Both native outputs use `https://in-toto.io/Statement/v0.1` with the independent
`https://slsa.dev/provenance/v1` predicate type and the exact expected singleton
platform subjects. The [historical in-toto Statement specification](https://github.com/in-toto/attestation/blob/2ec5785b36ec5e1ac12730356f8634bf889cc688/spec/README.md#statement)
and [SLSA predicate schema](https://slsa.dev/spec/v1.0/provenance#schema) define
these separate schema identifiers. SLSA v1 does not imply Statement v1.

The retained GitHub artifact `10124696818` has archive SHA-256
`3de673f7eaeba259c62a199b55163b7bedf1e6dccd77f3ed986702a5dc1f2074`.
Runtime JSON SHA-256 is
`5529e7493da37ca65008896f69a21ec65017d9aa658a6dc1e38fb24f7605236d`;
builder JSON SHA-256 is
`ebe248f585f0594558da328625fc30d2cb4de7ca33e10a08de5e6b60d72a04ed`.
Executing the unchanged workflow consumer against those original files returned
exit 1; the corrected consumer returned exit 0 for both unchanged files.

The correction recognizes only this pinned Statement/v0.1 profile, explicitly
requires an object root and nonempty object predicate, and retains exact subject
equality and SLSA predicate v1. This establishes source binding and structural
presence, not complete SLSA semantic validity. Other Statement versions are
unsupported by this pinned consumer, not inherently invalid. Scout 1.24.0,
`--verify`, `--skip-tlog`, source digests, credentials and trusted event admission
are unchanged. Signature verification remains delegated to Scout; a test stub
does not prove it. Evidence anchors: `.github/workflows/cd.yml:1014` and
`tests/test_deploy_contract_scripts.py:1916`.

The regression executes the actual complete step with independently varied
runtime/builder outputs, checks both exact Scout invocations and rejects wrong
schema/subject/digest, missing or extra subjects, malformed/empty predicates,
non-object or invalid JSON, missing/empty/symlink files and either verifier
failure even when valid-looking files were written. The original positive
cases failed on the baseline. Their corrected suite and the original native
file replay pass. Later build, publication, pullback, admission and Prometheus
steps were not reached in this failed main run and remain required. This
continuation is implementation recovery, not a standalone bookkeeping PR.

## Post-merge APK input and base-image recovery

PR #2389 was squash-merged as `48b416ac9f6723c540a85ea1139e2c996a7dbb0c`.
Its exact-main CD run `34469999154` passed the DHI Statement/v0.1 consumer
that had blocked PR #2387, then failed in PostgreSQL job `102850332413` before
publication. The live Alpine resolver selected transitive `libcurl` 8.22.0-r0
instead of the closure-recorded 8.21.0-r0. This proves that an
installed-package checksum detects resolver drift but does not freeze the
resolver inputs.

The bounded continuation tracks a seven-field SHA-256/size/file/package/version/
architecture/HTTPS acquisition record for all 41 builder APK archives and the
supplier's unchanged signed `APKINDEX.tar.gz`. CI downloads only those exact
bytes, then native APK verifies and installs the signed local repository with
network and cache access disabled. The build-stage `RUN` also has no network.
No unsigned subset, replacement key, public mirror fallback, package-manager
upgrade, `--allow-untrusted`, or vulnerability suppression is accepted. Buildx
0.37.0 is checksum-bound and BuildKit v0.32.2 is selected by exact linux/amd64
platform-manifest digest plus the closed manifest `buildkit_version`; both
identities enter the generated and reused provenance material sets.

The first fully frozen candidate retained the old DHI runtime base and exposed
six HIGH findings in `libuuid` 2.41.4-r0: CVE-2026-53612,
CVE-2026-53613, CVE-2026-53614, CVE-2026-76642, CVE-2026-78408 and
CVE-2026-78410. The finding was not ignored. The same PostgreSQL 15.19 Alpine
3.23 runtime/dev tags were refreshed to new immutable DHI digests containing
`libuuid` 2.41.6-r1. Trivy 0.74.0 scans of the refreshed runtime base, builder
base and exact final OCI layout report zero HIGH/CRITICAL findings with no
ignore entries. Trivy consumes the verified OCI layout directory; an OCI tar
is retained for reproducibility evidence but is not treated as a Docker-archive
scanner input.

Two clean-cache linux/amd64 builds produced the same platform digest
`sha256:06c914735c70f82424a2a9b1e57790590a21d0fbfe250504ff79a1cca2559380`,
config digest
`sha256:c822c68e22d0358e66cee17e06f7b3ece5d1538cb8b607c1376b59620866ceff`
and byte-identical OCI archive SHA-256
`c8557b99c6fbcee628472dc0cecb869562aab2e848b5ce5f896f1b4141a0a415`.
Publication, exact-main admission and merge evidence remain required.

The resumed review on 2026-09-12 found missing execution evidence despite the
published mapping. The actual premortem and ordered post-open QA, bug-hunter and
security passes were recovered before merge; their execution is not backdated
to PR opening. The premortem restored the ordinary 500 KB file-size check and
scoped the 2048 KB exception to the single supplier-signed APK index. The source
fixture documentation now separates its historical observed output shape from
synthetic current-digest substitutions.

The dedicated index hook also checks modified tracked files via `--enforce-all`.
The ordinary size limit is unchanged. The existing detect-secrets hook runs
serially because its file batches update one shared baseline; parallel batches
can overwrite each other's metadata updates. This serializes one hook invocation,
not independent operator processes or other worktrees.

The missing post-APK builder scan was executed against a newly reproduced
current-recipe OCI image. Trivy 0.74.0 reported zero HIGH/CRITICAL and secret
findings across its 94-package inventory. The final 49-package runtime layout
also passed with the same fresh database. Scout 1.24.0 authenticated both new
DHI source subjects with `--verify --skip-tlog`, and the unchanged workflow
consumer accepted both actual outputs. This is source-signature evidence,
without transparency-log proof or derived-publication authority.

The first resumed Experiment Runner packet executed the 42 governance tests
successfully but was rejected because its second oracle required an absent
Python pgvector binding. That rejected result remains retained. The corrected
governance-only packet passed both immutable oracles in strict Apple Container
isolation; Python binding and PostgreSQL compatibility remain separate required
CI/native checks. These procedural corrections grant no merge authority and do
not close the original final-main or documentation criteria.

The full native runtime replay exposed an initialization race in the inherited
`pg_isready` probe: the temporary Unix server accepted connections before the
requested database existed. The startup loop now requires both a successful
TCP `psql` command against that database and its exact `SELECT 1` result.
The same bounded loop rejects a never-ready database and output `1` paired
with a nonzero process exit. Native fresh-volume, same-volume restart and
legacy-image transition replay then passed with preserved database OIDs,
sentinels, PostgreSQL 15.19 and pgvector 0.8.6. Disposable test resources were
removed and Docker Desktop was stopped; no production volume was involved.

Evidence anchors: `.pre-commit-config.yaml:12`,
`tests/test_deploy_contract_scripts.py:8511`, and
`.github/workflows/cd.yml:1011`.

## Newly observed backend PCRE2 findings

Docker run `34686508035` reported two HIGH findings in Debian
`libpcre2-8-0 10.42-1`: CVE-2026-86145 and CVE-2026-89161. This was an
image vulnerability failure, not an expired review date. The same affected
package is independently present in this recovery PR's own production scan
from run `34677565852`, image
`sha256:f4e36161c7dcbc2c7299146a6d889076bc0f6e31dcde4b14a5850e8fd5014545`.

The Debian trackers for [CVE-2026-86145](https://security-tracker.debian.org/tracker/CVE-2026-86145)
and [CVE-2026-89161](https://security-tracker.debian.org/tracker/CVE-2026-89161)
identify Bookworm security package `10.42-1+deb12u1` as fixed. The existing
runtime-base installation now explicitly refreshes only this additional
package and rejects any installed version below that native Debian floor.
The Python/base-image pins, requirements and security suppressions are
unchanged. No blanket `apt upgrade` or new waiver is introduced.

The full rebuilt production image must pass its existing strict PR scan,
including unfixed findings, before merge. Compare complete package inventories
and preserve the current runtime smoke/UUID/TLS/gzip/SQLite/Alembic guards;
the successful earlier image scan is historical evidence only.
Evidence anchors: `Dockerfile:323` and
`tests/test_docker_workflow_build_path_contract.py:731`.

Docker's warning that credentials are stored in `config.json` is expected when
a credential helper is not configured; it is not evidence that the temporary
credentials survive the job. This lane keeps a dedicated mode-0700
`DOCKER_CONFIG`, uses `--password-stdin`, logs out of both registries, validates
the owned path and removes it from the always-run cleanup. Cleanup failures
remain fail-closed without replacing the primary job result.

## Frozen baseline failures

| Workflow / job | Primary evidence | Recovery owner |
| --- | --- | --- |
| CI 34310992480 / 102337448004 | Three individual review dates expired on 2026-09-08 | Existing Trivy policy/CVE documents |
| CD 34310992482 / 102338426980 | Docker credentials written to default config; Scout authentication unavailable; cleanup loses builder and rejects Scout directory | Existing CD steps and deploy contract tests |
| Frontend CI 34310992523 / 102337496366 | gRPC 1.83.1, CVE-2026-84445; implicit Trivy 0.70.0 | Existing Caddy recipe and scan step |
| Docker Build and Push 34310992504 / 102337942372 | Trivy 0.74.0 reports 34 HIGH findings before registry push | Production image composition |

The complete canonical CI Python 3.11/3.12/3.13 matrix, security, coverage-main,
lint, OpenAPI and iOS jobs succeeded on that baseline. An older DB/FOOD snapshot
is not evidence for changing current ORM, migrations or test backend selection.

The backend inventory is finite: CVE-2026-76642, CVE-2026-78408,
CVE-2026-78409 and CVE-2026-78410 each occur on eight Debian packages:
`bsdutils`, `libblkid1`, `libmount1`, `libsmartcols1`, `libuuid1`, `mount`,
`util-linux`, `util-linux-extra`. CVE-2026-16742 occurs on `libsystemd0` and
`libudev1`. Code-scanning records 652 through 685 bind these findings to the
baseline head. The frozen set is not a claim about all future vulnerabilities.

## Docker context and cleanup

The setup exports the dedicated Docker configuration before the first login
and Buildx call, then carries it through `GITHUB_ENV` to subsequent processes.
Scout 1.24.0 receives supported Hub credentials only in its verification step.
Registry login alone is not Scout authentication evidence. Both DHI subjects,
signature verification and existing attestation checks remain enforced.

Cleanup uses successful native inventory for absence recognition, matches
resource names to the current run/attempt, and validates each temporary path
against its specific direct-child slot. Scout uses the matching
`pulseplate-pgvector-scout.*` name. A failed inventory query is not absence;
cleanup cannot fall through to the default Docker configuration. The primary
failed job remains failed while secondary cleanup errors remain visible.

Evidence anchors: `.github/workflows/cd.yml:923`,
`tests/test_deploy_contract_scripts.py:1813`.

## Native backend remediation

The Python 3.13.14 Bookworm base and application install profiles are unchanged.
Only production removes the ten frozen Debian packages. Removal precedes the
existing Perl pruning because util-linux post-removal scripts need that
interpreter; the first local build exposed and retained this ordering failure.

Python's `_uuid` extension requires `libuuid.so.1`. The existing SQLite builder
ancestry compiles only shared libuuid from official util-linux 2.42.3; the final
image receives the exact library, SONAME link, upstream license, source manifest
and binary checksum. Headers, utilities, source trees and static libraries are
not copied from that builder. Both system and venv interpreters exercise native
UUID generation and inspect the actual loaded library under the non-root user.
The native coordination status is recorded, not forced to imply a uuidd service.

The frozen Debian tracker snapshots identify util-linux 2.42.3-1 as fixed for
[CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642),
[CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408),
[CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) and
[CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410).
Their affected mount/nsenter utilities are removed, and only the pinned upstream
2.42.3 shared UUID library is copied into production. This combines source-version
evidence with removal of the affected utility paths and actual native linkage.

Source: <https://www.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.3.tar.gz>

```text
SHA-256  2f4c3484f67c79688a50974b9e0ae52d089fe07a63d2dbb59b20e50ed26fe89f
SHA3-256 3edc35e7d261478bf9910ec87b70ae0c2be133e8ab523e2683ccfc0704d51652
```

The existing source fetcher now rejects cached links/nonregular objects and
symlinked output directories before cache reads or mutation. Its claim is the
bounded cooperative build cache, not hostile same-user race exclusion.

Evidence anchors: `Dockerfile:205`,
`scripts/ci/fetch_docker_source_artifacts.py:132`,
`scripts/ci/check_docker_runtime_dependency_surface.py:184`.

## Caddy: one Go identity

Authored action: replace `google.golang.org/grpc` 1.83.1 with 1.83.2 in the
existing Caddy recipe. Complete native module graphs, go.mod/go.sum and repeated
resolver output are retained separately from the recipe's selected metadata
assertions. The repeated native Go 1.26.6 replay contains 549 modules at base and head.
Its only two transitions are gRPC 1.83.1 to 1.83.2 (authored) and
`golang.org/x/net` 0.57.0 to 0.58.0 (solver closure). Two executions from the
exact baseline produce identical go.mod, go.sum and full module graphs.
Caddy capabilities, routes, headers and configuration remain unchanged.

The 2026-09-09 GitHub advisory inventory contains seven records. Only
GHSA-2v4p-qf9q-27wj applies at the Caddy base version; its 1.83 branch is affected
below 1.83.2. The candidate 1.83.2 is outside every listed range:

| Advisory | Base applicability / candidate postcondition |
| --- | --- |
| GHSA-2v4p-qf9q-27wj | 1.83.1 affected; 1.83.2 is the fixed 1.83 branch boundary |
| GHSA-qc2q-p7wx-3px3 | Base above affected <=1.83.0; candidate also outside |
| GHSA-vp52-pcj8-j9qc | Base above affected <=1.83.0; candidate also outside |
| GHSA-hrxh-6v49-42gf | Base/candidate above affected <1.82.1 |
| GHSA-p77j-4mvh-x3m3 | Base/candidate above affected <1.79.3 |
| GHSA-xr7q-jx4m-x55m | Base/candidate outside [1.64.0,1.64.1) |
| GHSA-m425-mq94-257g | Base/candidate outside the affected 1.56, 1.57 and 1.58 ranges |

The existing selected Prometheus/promtool subject remains unchanged and embeds
gRPC 1.83.2; its current-head CD scan remains independently required. No direct
Go manifest, alternate image selector or replacement-module mechanism is added.

Evidence anchor: `frontend/Dockerfile.caddy-spa:22`.

## Scanner parity and review decisions

Backend PR and publication both scan the actual production image with Trivy
0.74.0, vulnerability scanning, HIGH/CRITICAL, existing policy/ignore inputs and
exit 1 on findings. Neither enables `ignore-unfixed`. Native JSON is bound to
the selected image and inspected Docker image ID through the existing runtime
surface checker, then converted to SARIF by Trivy. The checker validates only
its explicit report projection, not an invented universal scanner schema.
The scanner's original failure is preserved even when report retention succeeds.
PR jobs gain no publication or DHI credential authority.

The Caddy scanner now selects 0.74.0 explicitly. Its existing secret/vulnerability
scan semantics remain distinct from the backend vulnerability-only contour.

CVE-2026-3184 is removed from candidate policy after exact local image absence
proof. Shared util-linux helpers remain for other existing rules. Fresh Debian
evidence still marks Bookworm zlib and ncurses vulnerable/no-dsa; their exact
predicates remain unchanged and the approved review date is 2026-09-19. The
single overall expiry remains 2026-10-07. Renewed review is not remediation.

Evidence anchors: `.github/workflows/build.yml:165`,
`trivy/ignore-policy.rego:17`.

## Validation and remaining delivery proof

The final-head Python 3.12 run `34376019383` exposed a cleanup-retry test that
also depended on a real Python oracle completing within a five-second packet
budget. Its hosted log reports `rejected` versus `accepted`; the exact hosted
rejection subtype was not captured. JUnit records 0.371 seconds, which argues
against the multi-second process-timeout hypothesis for that hosted failure.
Twenty local Python 3.12.7 replays of the original test and three immediate
predecessors passed; these are not the hosted Linux 3.12.14 shard. A controlled
slow-oracle replay reproduced
the same assertion with `failure_class: timeout` after both attempts. The test
now supplies a deterministic successful oracle while retaining real temporary
checkouts, the injected first cleanup error, and assertions for both cleanup
calls and both oracle invocations. The 100-test Runner module passes, including
its separate timeout cases. This closes the demonstrated fixture coupling;
it does not assert that the historical hosted failure was proven to be a timeout.
Runtime retry and timeout enforcement remain unchanged. Evidence anchor:
`tests/test_experiment_runner.py:1626`.

Observed baseline regressions failed for current-step Docker context, Scout
directory naming, cached source symlinks, and the missing SHA-256 comparison.
The actual Dockerfile verifier now independently rejects either mismatched
expected digest; all four source-integrity checks pass. Patched lifecycle/source checks
passed (28 tests); the initial Docker/Caddy/report focused bundle passed
(100 tests). A local linux/amd64 production candidate completed native UUID,
TLS/gzip/SQLite and Alembic build checks, HTTP health/OpenAPI smoke, and the
ten-package inventory with `passed: true`. Its fresh policy-bound Trivy scan
reported zero blocking HIGH/CRITICAL findings.

These local results are not committed-head or merged-main readiness. Final
material validation, the full current-head CI/review/strict sequence, human
exact-head merge authorization, actual Scout provenance/publication/pullback and
all applicable merged-main pipelines remain required. Source-built library
provenance and native linkage evidence remain necessary even when package
scanning reports no findings. Docker Desktop is stopped after local Docker work;
native archive scans and cloud CI do not require retaining its VM in memory.

The ignored lane archive retains raw failures, vendor and advisory snapshots,
input/report hashes, image identity, native evidence and exact command receipts.
Before completion it also retains the merge receipt, clean main `0 0`, sanity,
review evidence, verified Git bundle and same-ID readback of the four approved
Drive records. No standalone bookkeeping PR or automatic prevention PR is opened.

# MAIN-RECOVERY-1: image security and publication recovery

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

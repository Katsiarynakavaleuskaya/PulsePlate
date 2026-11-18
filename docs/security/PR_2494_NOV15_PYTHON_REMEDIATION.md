# PR 2494 Python dependency findings on November 15, 2026

The ordinary push from `203fe93cf06e5344d3e32b2e22e3258ec4edd122` stopped at
the runtime pip-audit hook. A subsequent full audit of that same commit found
two affected PyPI packages. The owner approved both replacements in PR #2494
and the minimum OpenTelemetry compatibility changes established by solver
replay. Earlier remediation decisions retain their original inputs and dates.

## Scope and evidence

The scan used pip-audit 2.10.1 and all ten registered compiled locks. Starting
at 01:10 UTC on November 15, it completed in 95 seconds. The strict inventory
check accounted for 561 package occurrences with zero skipped and zero
incomplete profiles. Runtime, Docker runtime, CI-lite and aggregate each
contained both findings. Test, dev, both vector profiles, data and the empty
evals profile had zero reported findings. The two vector profiles used the
existing verified FastEmbed wheel comparison. The aggregate lock is a reference
for dependency reconciliation. Its rows contribute to the audit counts.

The ten outcome records hash to
`119d8c0455677017c015c4173ceeeb0d8c9d8c67f5d7c13ab8d24586aa3c91b0`.
The archive of 254 original records hashes to
`7f3bb47c8d3a4348749777eb88f3a01c4f10e465ae08ca2d0e1d3f5da034091b`.
The original pre-push runtime audit and this full audit both returned finding
exit 1. The pre-push branch tests had 15,339 passes and 15 skips. The remote
branch stayed at `762eed8694bc95384c821b773273fb275cca3981` during that push.

For the PR base `d20922f741f431b6eb3e47386ae944ca441a971e` and the
pre-repair commit `203fe93cf06e5344d3e32b2e22e3258ec4edd122`, separate
Git-tree inventories matched all 21 members of the requirements registry.
Both versions had the same six dnspython carriers and seven OpenTelemetry
API carriers. For each package, the four affected lockfiles were
`requirements.txt`, `requirements-docker-runtime.txt`,
`requirements-ci-lite.txt` and `requirements-lock.txt`. The additional
dnspython source declarations were `requirements.in` and `constraints.txt`.
OpenTelemetry API had direct declarations in `requirements.in`,
`requirements-docker-runtime.in` and `requirements-ci-lite.in`.
The registered lock and source owners are documented in
[Python dependency surfaces](../contracts/PYTHON_DEPENDENCY_SURFACES.md).
The canonical Git candidate classifier is at
`scripts/ci/dependabot_requirement_carriers.py:305`.

## Reconciled advisory inventory

The terminal GitHub reviewed-advisory queries at 00:48 UTC returned three
dnspython records and two OpenTelemetry API records. Each affected base
witness below occurred in all four locks. The named package versions are
evaluated across every range in the table, including the ranges that exclude
the base. Targets in the last column are the approved resolver parameters.

| Package | Advisory | Affected range | Base witness | Target |
| --- | --- | --- | --- | --- |
| dnspython | [GHSA-vvf4-9x63-8xvv / CVE-2026-128089](https://github.com/rthalley/dnspython/security/advisories/GHSA-vvf4-9x63-8xvv) | <2.9.2 | 2.9.0 affected | 2.9.2 |
| dnspython | [GHSA-45c3-73f7-pv4m / CVE-2026-114605](https://github.com/advisories/GHSA-45c3-73f7-pv4m) | <2.9.0 | 2.9.0 outside | 2.9.2 |
| dnspython | [GHSA-3rq5-2g8h-59hc / CVE-2023-29483](https://github.com/advisories/GHSA-3rq5-2g8h-59hc) | <2.6.1 | 2.9.0 outside | 2.9.2 |
| opentelemetry-api | [GHSA-mf5v-w3w3-f6cg / CVE-2026-126360](https://github.com/open-telemetry/opentelemetry-python/security/advisories/GHSA-mf5v-w3w3-f6cg) | <=1.45.1 | 1.45.1 affected | 1.45.2 |
| opentelemetry-api | [GHSA-xcq7-p3pf-p88h / CVE-2026-114603](https://github.com/advisories/GHSA-xcq7-p3pf-p88h) | <=1.45.0 | 1.45.1 outside | 1.45.2 |

## dnspython replacement and replay

The source floor advanced to `>=2.9.2,<3.0.0` in the two existing
declarations. The first runtime Make invocation stopped before resolution
because the historical Psycopg SDK supplied two different hashes for derived
source material. The existing SDK produced for setuptools 84 matched the
current installer bindings and the retained original wheel and manifest.

Both native runtime compiles used the same original seed, the approved private
index, Linux x86_64 CPython 3.13.5, pip 26.2.2 and pip-tools 7.6.1. Each used
`make requirements-locks` with `LOCK_PROFILES=runtime` and
`UPGRADE_PACKAGES=dnspython==2.9.2`. Their outputs were byte-identical.
Among 70 entries, only the dnspython pin advanced. The ordinary checkpoint
`0f80a98b9bac9494ced9b4d230c2da176d2d3a85` contains both source changes
and the generated runtime lock.

The dependent command used `LOCK_PROFILES="docker-runtime ci-lite aggregate"`
with the same Make target and upgrade parameter. Two independent runs from
that checkpoint matched byte-for-byte. Docker runtime, CI-lite and aggregate
retained 61, 106 and 137 entries respectively. Each diff changed only the
literal dnspython pin. The complete dependency delta therefore consists of
one authored replacement and zero additional solver-driven coordinates. The
dependent checkpoint is `56749eaf015cd120fde36f49bb9bd8cdbfda61f7`.
Its Git tree retains all six original carriers. The other six registered
compiled locks contain no occurrence of this package.

## OpenTelemetry API replacement and required companion versions

The source floor advanced to `>=1.45.2,<2.0.0` in the three existing API
declarations. The fully committed dnspython state at `56749eaf` supplied the
seed for each runtime replay. The locked SDK 1.45.1 and semantic conventions
0.66b1 both require API 1.45.1 exactly. Their original requirements therefore
exclude the patched API. The SDK 1.45.2 wheel requires API 1.45.2 and semantic
conventions 0.66b2 exactly. The latter independently requires API 1.45.2.
The original exporters accept these versions through their existing API and SDK
ranges. Their locked protobuf transport dependencies also remained compatible.
The optional file-configuration extra was inactive.

Both runtime compiles used the canonical `make requirements-locks` with
`LOCK_PROFILES=runtime` and exact upgrade parameters
`opentelemetry-api==1.45.2 opentelemetry-sdk==1.45.2 opentelemetry-semantic-conventions==0.66b2`.
The verified private wheels and their dependency metadata identify the API as
the single authored replacement and the SDK and semantic conventions as its
two required companion transitions. Each independent run retained the same 70
runtime coordinates and changed exactly those three versions. The complete
result hashes to
`0259c31274fcc0f38d7cca9976a9accdf2396f67c9a74a268365e6dc714fa25c`.

| Distribution | Version | Private wheel SHA-256 | METADATA SHA-256 |
| --- | --- | --- | --- |
| opentelemetry-api | 1.45.2 | 2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34 | aa93f63be0d6d1f662966e67b22a77c0d9966752e3a32ad87c1347f595cea7cb |
| opentelemetry-sdk | 1.45.2 | ff974ea70ee4f1d51e2ec152db37c2b626c7bf82bb3f7d86114fd8704e7199c6 | 97f0b558caae567c607dc5b53fc755deb2d0e305fe08093bb8d6c59ed55aa3e4 |
| opentelemetry-semantic-conventions | 0.66b2 | 4cbe61e5f9275d57ab31708446e7938ef4291ebbe6a7fca6f7a629c5acae87d8 | 7e443b23ebb345b06a7be96db4803ae81ac7ec8995e37f6814d0f2006b8e6447 |

The ordinary runtime checkpoint was `5f568d6ac090a8ac5a28af0c9655ac8ec66c6e23`.
Two dependent-profile runs from this commit produced identical results for
Docker runtime, CI-lite and aggregate. Each retained its complete set of
package names, extras, markers, URLs and versions apart from the three
selected version transitions. The dependent commit was
`a90d31b57cc150f2b92715fc35776b8cb011828b`.

## Result across all ten locks

The complete dependency commit has the same 21 registry members, six
dnspython carriers and seven OpenTelemetry API carriers as the original
inventories. All locked occurrences and source-floor witnesses for dnspython
are 2.9.2 and lie outside all three reconciled advisory ranges. All API
occurrences and source-floor witnesses are 1.45.2 and lie outside both API
ranges. Both authored fixes occur together in the four affected locks; the two
solver-required companion transitions are the only additional version changes.
Every other byte in those locks and all bytes in the other six locks matched
the original seed, except for those version substitutions.

On November 15 the full post-fix audit at `a90d31b5` completed in 109 seconds
with exit 0. The scanner reported zero findings in 561 package occurrences,
with all ten inputs accounted for and zero skipped or incomplete profiles.
Both vector profiles repeated the same verified upstream-wheel comparison.
The raw archive SHA-256 is
`8118fc10cab87ec6c0d0ee8db8916e427d4fdb193b4cb65ccad9b21ba35ccea4`.

| Compile profile | Scanned occurrences | Findings before | Findings after |
| --- | ---: | ---: | ---: |
| runtime | 70 | 2 | 0 |
| docker-runtime | 61 | 2 | 0 |
| ci-lite | 106 | 2 | 0 |
| test | 23 | 0 | 0 |
| dev | 89 | 0 | 0 |
| rag-vector | 35 | 0 | 0 |
| rag-vector-cpu | 35 | 0 | 0 |
| data | 5 | 0 | 0 |
| evals | 0 | 0 | 0 |
| aggregate | 137 | 2 | 0 |

The existing dependency guard now checks both affected versions explicitly.
On the updated guard material, all 81 selected tests passed, including the
actual carrier inventory and the two advisory-specific negative witnesses.
The original October cutoffs remain separately identifiable in
`tests/test_dependency_security_guard.py:246`. The current combined blocked
ranges for the two packages are in
`tests/fixtures/dependency_security_schema.json:25` and
`tests/fixtures/dependency_security_schema.json:57`.

## Installed compatibility

The qualified Linux amd64 CPython 3.13.14 image installed the corrected locks
from commit `a90d31b57cc150f2b92715fc35776b8cb011828b` in nine fresh virtual
environments. The canonical installer obtained four maximal wheel sets through
the approved package proxy and consumed each profile's exact wheels with the
container network disabled. Each installed inventory matched its lock inputs,
plus the separately verified pip 26.2.2. Every `pip check` exited zero.

| Installation | Locked packages |
| --- | ---: |
| Runtime | 70 |
| Docker runtime | 61 |
| CI lite | 106 |
| Runtime plus dev | 137 |
| Runtime plus test | 87 |
| CI test | 118 |
| Runtime plus RAG | 88 |
| Aggregate | 137 |
| Runtime plus test and dev | 138 |

Each profile loaded dnspython 2.9.2, OpenTelemetry API and SDK 1.45.2, and
semantic conventions 0.66b2 from its own virtual environment. A DNS message
with an ordinary A record survived a wire round trip. The user schema accepted
a synthetic email address. The in-memory SDK exporter received one completed
span and the OTLP HTTP exporter successfully initialized and shut down. These
observations cover offline behavior and exporter lifecycle. External OTLP
delivery was outside the check. The real app test in the CI-test environment
passed once. See `app/schemas/users.py:19` and `tests/test_genai_tracing.py:591`.

The 89-package dev-only lock contains none of these four dependencies. The
CPU and default RAG lockfiles have different generated comments and identical
requirement rows, versions and extras. The RAG installation supplies the
observed execution for that shared composition.

The first CI-test prefetch returned 1 when the installer attempted to create
effective constraints next to the read-only source copy. The corrected run
used identical constraint bytes in a private writable directory. Installation
and behavior checks then passed. Docker returned 125 before starting the
one app test because the read-only source clone lacked a cache mountpoint.
Creating that empty mountpoint in the disposable clone allowed the test to
run in the same installed environment. The previous native failures and their
logs were retained. The installation evidence summary SHA-256 is
`70757eaa5aaea268e6668a8c162350c5179ac3271654450d19e1ca9ab341c641`.

## Rollback

A compatibility regression in an installed profile requires a reviewed
follow-up against that profile's retained lock and native evidence. To revert
this dependency transaction, revert the four linked source and lock commits
in reverse order and reconcile the guard, owner document and ledger in the
same review. Restoring either affected version reopens its advisory and
requires a fresh ten-lock audit before publication. The validated execution
here covers Linux amd64 CPython 3.13.14; other platforms and deployed images
require their own release evidence.

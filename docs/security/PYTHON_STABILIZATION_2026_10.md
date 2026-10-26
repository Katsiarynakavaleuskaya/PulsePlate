# Python setup and security stabilization — October 2026

## Status and external instruction

This is the single owner document for the in-progress
`codex/python-setup-security-stabilization` prerequisite, based on
`48d36c220ff58dec82450da66ef0599c6da71787`. The operator accepted the original
five-identity batch and separately authorized FastEmbed compatibility, pip tooling
and the source-review window. On October 24 the operator explicitly amended
this same PR to seven security identities: add setuptools 84.1.0 and filelock
4.2.1, and advance virtualenv to 21.14.10. The other four security targets and
the FastEmbed/pip-tools companions remain unchanged. This document records
external instructions; it cannot create or broaden them.

The operator has also given advance conditional permission to merge this one
prerequisite after every required current-material validation, CI, review,
closeout and wait-window gate passes. There is no deployment authority.

**AM03 component checkpoint — 2026-10-24 03:26 UTC:** both independent
canonical replays are complete and
their verified locks are adopted. All ten locks passed the strict audit, all 53
primary postconditions passed, and four adopted-material guards passed. The
amended native matrix also completed all ten steps, covering eight product
profiles and one reference-only baseline. Publication and closeout independently
require the final local gates, current Oracle/role review and hosted CI; their
live outcomes belong to the PR, canonical mapping and exact-material receipts. Earlier
successful generation/install/audit results below retain their original
material and advisory cutoff. The ordinary pre-push of the earlier c981
candidate failed after its prior successful audit; a complete rescan confirmed
five advisory IDs in three packages;
those failures are not suppressed or replaced by the earlier successful scan.
The published internal FastEmbed wheel and its verified bytes remain unchanged.

## October 24 governing advisory inventory and authored correction

A new terminal pip-audit 2.10.1 scan of all ten original-base locks ran from
`2026-10-24T02:15:37.407738Z` to `2026-10-24T02:17:44.748688Z`. It observed
553 package occurrences, seven affected identities, 52 distinct advisory IDs,
316 finding occurrences and no skipped packages. The separate scan of
`c98177bf123a59dc6b46cd487f00d644c53e542b` observed 561 package occurrences,
five advisory IDs and 23 finding occurrences across filelock, setuptools and
virtualenv. Both complete scans exited 1 because of retained findings.
The immutable combined analysis SHA-256 is
`8c5df2d89275ca9081e7c33473ab22c39f246068cb8dc8657f70f8f0569e1f1e`.

Primary reconciliation retains 53 `F_cutoff` entries: the 52 base-applicable
entries plus `GHSA-4f8h-vr72-p32c`, which applies to the previous virtualenv
21.14.9 candidate. The complete primary-payload index SHA-256 is
`f0538c40f2c0946ac7b01b355d61e90d98186d5624159284cc2173faa7d99e20`.
Seven security identities, nine authored package coordinates (including the two
compatibility companions), 53 reconciled advisories and 52 base-applicable
advisories are distinct counts. Every governed head occurrence must satisfy
all corresponding retained ranges; a clean subset does not establish final P.

| Identity | Authored carriers | Selected replacement |
| --- | --- | --- |
| black | Existing dev/convenience/constraint/hook owners | 26.10.1 |
| certifi | Existing runtime/constraint owners | 2026.10.19 |
| filelock | CI-lite, dev, both RAG inputs and constraints | 4.2.1 |
| opentelemetry-api | Existing runtime, Docker and CI-lite inputs | 1.45.1 |
| pillow | Existing runtime, Docker, CI-lite, dev and constraint owners | 13.0.0 |
| setuptools | Runtime, Docker, CI-lite, dev and constraints | 84.1.0 |
| virtualenv | Existing CI-lite and dev inputs | 21.14.10 |

FastEmbed `0.8.0+pulseplate.1` and pip-tools `7.6.1` remain separately authorized
compatibility actions. Pip remains outside application locks with its unchanged
26.2.2 minimum. No unrelated dependency intent, suppression or new registry is
included. The same canonical runtime-then-seven-dependent transaction is replayed
from the original base twice before adoption; current commands are in
[the runbook](../../RUNBOOK_AGENT.md#native-python-client-build-and-lock-refresh).

The existing finite admission now represents filelock's actual before values
per profile: ci-lite/dev 3.24.3, aggregate 3.29.1 and both RAG profiles 3.29.4.
Every value must match a hash-verified original seed; missing/extra profiles,
wrong-profile substitutions and source drift reject before acquisition. The
existing `exact_profile_deltas` remains the single projection. The admission
remains within its existing 32768-byte cap, and legacy records and original-base
hashes are preserved. Evidence anchors:
`scripts/ci/compile_locked_python_requirements.py:1177` and
`tests/test_python_dependency_surfaces.py:4771`.

The direct filelock floor also requires exactly one existing Dependabot owner.
The necessary two-line companion adds `filelock` to `supply-chain-tools` in
`.github/dependabot.yml:119` and its existing closed validator mirror at
`scripts/ci/check_dependabot_python_policy.py:131`. It changes no schedules,
registries, credentials, update types or ownership algorithm. The concrete
implementation now has 43 material paths; the sole numbered mapping brings the
final footprint to 44. This companion adds no dependency identity or target and
requires the same concrete scope justification and publication gates.

Permanent security floors, affected ranges and required carrier presence remain
owned by `tests/test_dependency_security_guard.py`, including Pillow in both
RAG locks (`tests/test_dependency_security_guard.py:3907`). Black consumer tests
compare the live hook and lock versions and require membership in owning input
specifiers; a compatible-release lower bound is not another selected-version
constant (`tests/test_python_supply_chain_controls.py:1873`,
`tests/test_install_locked_python_requirements.py:2960`). These continuing
consumer contracts do not relax the exact one-time compiler transition.

### Primary advisory reconciliation

Each row's selected target is outside its primary structured range. This is
range comparison, not proof of installation or absence of unknown defects.

| Identity | Primary advisory / scanner ID | Primary affected range | Base witness or disposition | Selected target |
| --- | --- | --- | --- | --- |
| black | [GHSA-cg8m-r9f2-5wm2](https://github.com/advisories/GHSA-cg8m-r9f2-5wm2) / CVE-2026-114134 | `<26.10.1` | 26.5.1: affected | 26.10.1 |
| certifi | [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) / PYSEC-2026-4320 | `<2026.10.19,>=2019.03.09` | 2026.1.4: affected | 2026.10.19 |
| filelock | [GHSA-567q-5qvw-pf92](https://github.com/advisories/GHSA-567q-5qvw-pf92) / CVE-2026-112907 | `<=4.2.0,>=3.22.0` | 3.24.3, 3.29.1, 3.29.4: affected | 4.2.1 |
| filelock | [GHSA-9vhv-jxww-xfm5](https://github.com/advisories/GHSA-9vhv-jxww-xfm5) / CVE-2026-112913 | `<=4.2.0,>=3.20.4` | 3.24.3, 3.29.1, 3.29.4: affected | 4.2.1 |
| filelock | [GHSA-v4x8-3wr5-3wq8](https://github.com/advisories/GHSA-v4x8-3wr5-3wq8) / CVE-2026-112940 | `<=4.2.0,>=3.20.4` | 3.24.3, 3.29.1, 3.29.4: affected | 4.2.1 |
| opentelemetry-api | [GHSA-xcq7-p3pf-p88h](https://github.com/advisories/GHSA-xcq7-p3pf-p88h) / CVE-2026-114603 | `<=1.45.0` | 1.44.0: affected | 1.45.1 |
| pillow | [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9) / CVE-2026-112390 | `<13.0.0,>=7.2.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-24rc-8hj2-v98c](https://github.com/advisories/GHSA-24rc-8hj2-v98c) / CVE-2026-96638 | `<13.0.0,>=9.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-254f-3936-288h](https://github.com/advisories/GHSA-254f-3936-288h) / CVE-2026-112391 | `<13.0.0,>=5.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-27h8-gf7j-v5hc](https://github.com/advisories/GHSA-27h8-gf7j-v5hc) / CVE-2026-112392 | `<=12.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-332p-7hrc-92wf](https://github.com/advisories/GHSA-332p-7hrc-92wf) / CVE-2026-112393 | `<13.0.0,>=2.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-3j72-p6qg-6xp7](https://github.com/advisories/GHSA-3j72-p6qg-6xp7) / CVE-2026-96642 | `<13.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-462x-pgg6-55fp](https://github.com/advisories/GHSA-462x-pgg6-55fp) / CVE-2026-112395 | `<13.0.0,>=8.2.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-4rm8-3hmm-39fg](https://github.com/advisories/GHSA-4rm8-3hmm-39fg) / CVE-2026-96641 | `<13.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-4rr5-89j8-mwwm](https://github.com/advisories/GHSA-4rr5-89j8-mwwm) / CVE-2026-112396 | `<13.0.0,>=11.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-58r4-6rv3-gfh8](https://github.com/advisories/GHSA-58r4-6rv3-gfh8) / CVE-2026-112397 | `<=12.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-5x8w-8jj5-q52h](https://github.com/advisories/GHSA-5x8w-8jj5-q52h) / CVE-2026-112398 | `<=12.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-5xm2-6676-qcp9](https://github.com/advisories/GHSA-5xm2-6676-qcp9) / CVE-2026-112399 | `<13.0.0,>=8.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-654x-cwwv-5j9c](https://github.com/advisories/GHSA-654x-cwwv-5j9c) / CVE-2026-114501 | `<13.0.0,>=11.2.1` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-65qm-jvmh-6pqg](https://github.com/advisories/GHSA-65qm-jvmh-6pqg) / CVE-2026-112400 | `<13.0.0,>=9.2.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-74r2-7ff9-mjj2](https://github.com/advisories/GHSA-74r2-7ff9-mjj2) / CVE-2026-112401 | `<13.0.0,>=5.4.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-78g4-xqwv-q3g8](https://github.com/advisories/GHSA-78g4-xqwv-q3g8) | `<13.0.0,>=11.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-7mwm-ghpf-9vrm](https://github.com/advisories/GHSA-7mwm-ghpf-9vrm) / CVE-2026-112402 | `<=12.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-9v9v-9qvf-h2hj](https://github.com/advisories/GHSA-9v9v-9qvf-h2hj) / CVE-2026-96644 | `<13.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-c6hw-5grf-ff96](https://github.com/advisories/GHSA-c6hw-5grf-ff96) / CVE-2026-112404 | `<13.0.0,>=8.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-cp9v-662q-vvx9](https://github.com/advisories/GHSA-cp9v-662q-vvx9) / CVE-2026-112405 | `<13.0.0,>=12.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-f2g6-542v-9j58](https://github.com/advisories/GHSA-f2g6-542v-9j58) / CVE-2026-112406 | `<13.0.0,>=5.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-fc9g-5qg7-mf45](https://github.com/advisories/GHSA-fc9g-5qg7-mf45) / CVE-2026-112891 | `<13.0.0,>=9.2.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-g4qv-2jxx-769h](https://github.com/advisories/GHSA-g4qv-2jxx-769h) / CVE-2026-96643 | `<13.0.0,>=11.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-g7cr-3p24-7wf7](https://github.com/advisories/GHSA-g7cr-3p24-7wf7) / CVE-2026-96778 | `<13.0.0,>=9.4.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-g842-9rc4-69pw](https://github.com/advisories/GHSA-g842-9rc4-69pw) / CVE-2026-96637 | `<13.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-gg2r-wvfm-q9rx](https://github.com/advisories/GHSA-gg2r-wvfm-q9rx) / CVE-2026-112892 | `<13.0.0,>=4.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-j4m9-6w36-pw47](https://github.com/advisories/GHSA-j4m9-6w36-pw47) / CVE-2026-112893 | `<13.0.0,>=10.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-jg86-v3jv-hrpm](https://github.com/advisories/GHSA-jg86-v3jv-hrpm) / CVE-2026-112894 | `<13.0.0,>=5.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-mrfp-p49p-3hf2](https://github.com/advisories/GHSA-mrfp-p49p-3hf2) / CVE-2026-96640 | `<13.0.0,>=5.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-p4wg-p73j-c528](https://github.com/advisories/GHSA-p4wg-p73j-c528) / CVE-2026-112895 | `<13.0.0,>=5.1.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-p8hx-v2p6-rp84](https://github.com/advisories/GHSA-p8hx-v2p6-rp84) / CVE-2026-96636 | `<13.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-pchr-8j38-3x4p](https://github.com/advisories/GHSA-pchr-8j38-3x4p) / CVE-2026-112896 | `<=12.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-q45j-58j2-45rg](https://github.com/advisories/GHSA-q45j-58j2-45rg) / CVE-2026-112897 | `<13.0.0,>=5.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-v9pv-5gc8-w2m6](https://github.com/advisories/GHSA-v9pv-5gc8-w2m6) / CVE-2026-96639 | `<13.0.0,>=11.0.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-vx6w-vv9f-6gvg](https://github.com/advisories/GHSA-vx6w-vv9f-6gvg) / CVE-2026-112899 | `<=12.3.0,>=2.3.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-w889-685w-c8fh](https://github.com/advisories/GHSA-w889-685w-c8fh) / CVE-2026-112900 | `<13.0.0,>=2.6.0` | 12.3.0: affected | 13.0.0 |
| pillow | [GHSA-xgh8-jp6q-p5x8](https://github.com/advisories/GHSA-xgh8-jp6q-p5x8) / CVE-2026-112901 | `<=12.3.0` | 12.3.0: affected | 13.0.0 |
| setuptools | [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w) | `<84.1.0,>=38.2.2` | 83.0.0: affected | 84.1.0 |
| virtualenv | [GHSA-394h-qwmc-48pf](https://github.com/advisories/GHSA-394h-qwmc-48pf) / CVE-2026-113718 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-494p-63j8-28p3](https://github.com/advisories/GHSA-494p-63j8-28p3) / CVE-2026-113714 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-4f8h-vr72-p32c](https://github.com/advisories/GHSA-4f8h-vr72-p32c) / CVE-2026-113713 | `<21.14.10,>=21.14.8` | 21.14.5: outside structured range; 21.14.9 candidate affected | 21.14.10 |
| virtualenv | [GHSA-6w3r-xr62-4xcp](https://github.com/advisories/GHSA-6w3r-xr62-4xcp) / CVE-2026-113723 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-c978-59m8-c77v](https://github.com/advisories/GHSA-c978-59m8-c77v) / CVE-2026-113722 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-cx28-75q4-x26q](https://github.com/advisories/GHSA-cx28-75q4-x26q) / CVE-2026-113717 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-fc2g-4w5p-6whm](https://github.com/advisories/GHSA-fc2g-4w5p-6whm) / CVE-2026-113720 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-qmx5-4p3x-wvqf](https://github.com/advisories/GHSA-qmx5-4p3x-wvqf) / CVE-2026-113715 | `<21.14.9` | 21.14.5: affected | 21.14.10 |
| virtualenv | [GHSA-vxj4-q4g9-crj7](https://github.com/advisories/GHSA-vxj4-q4g9-crj7) / CVE-2026-113725 | `<=21.14.6` | 21.14.5: affected | 21.14.10 |

`GHSA-4f8h-vr72-p32c` needs a narrow disposition: base virtualenv 21.14.5 is
outside the current structured primary range `>=21.14.8,<21.14.10`; this does
not demonstrate that the underlying bug was absent from that older release.
The advisory prose still discusses an unavailable fix and an unverified earlier
20.0.6 boundary, while its structured record identifies 21.14.10 as fixed.
The verified 21.14.10 wheel independently contains the seeder correction:
`options.symlink_app_data and not self.app_data.transient`. Source comparison
corroborates the selected fix; actual execution remains a separate test.
The universal head guard retains this advisory and uses 21.14.9 as its affected
witness (`tests/test_dependency_security_guard.py:3961`).

All three corrected artifacts were obtained through the existing private index
and matched primary PyPI sizes/hashes before ZIP metadata inspection:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `setuptools==84.1.0` | 819380 | `5231689c6ac8156cd155cfb98c3fd6fb252c3e7e9bd3d78b64d3c55f132624c9` |
| `filelock==4.2.1` | 162455 | `7be2662e9e826b9bba28afc0f843a123280d799a2ea44bb5d35ccec67905ae44` |
| `virtualenv==21.14.10` | 5494519 | `bf4a0f9671731d097e017e41280aa05e1e1adcd536b0e804fceb3179947ad50e` |

The 125-case synthetic admission/advisory/schema selection exited 0 in 11.02s;
the canonical isolated pre-push mypy hook and targeted Ruff checks also passed.
A direct unconfigured mypy invocation first reported duplicate module discovery;
the canonical hook then exposed two typing errors, which were fixed and rerun.
Those raw failures remain retained. Synthetic tests are not canonical resolver,
installation, final audit or current-head CI evidence.

### AM03 canonical replay, complete delta and audit

Four canonical Make transactions completed in the qualified owned Linux amd64
CPython 3.13.14 environment: A runtime 142.77s and dependents 507.44s;
B runtime 116.77s and dependents 501.22s. All four exited 0, with no yanked
warnings. Compiler pip 26.2.2 and pip-tools 7.6.1 stayed fixed; its setuptools
was updated to 84.1.0. Each independent export started from the same immutable
original-base seeds. All ten output files matched byte-for-byte across A/B;
the existing exact-pin reader accepted all eight installation compositions.
Replay proof SHA-256:
`2d6f44730d89baa0509c4c4f6261234a220df1ab703bb6a69218d6037f2d3ced`.

The generated outputs were adopted without hand edits. Eight locks differ from
the original base; seven changed from the previous c981 candidate because its
test lock already matched the independently reproduced result. Data and eval
remain unchanged and stay inside the audit inventory. Four adopted-material
checks (complete advisory surfaces, virtualenv, schema and setuptools floor)
exited 0: `4 passed in 1.50s`.

The complete dependency delta has 17 identities: seven authored security
replacements, the two separately authorized compatibility companions and eight
independently reproduced solver-closure transitions. No transition is omitted;
filelock's different original versions are retained per profile. Requirement
strings preserve extras and contain no markers or URLs.

```json
{
  "black": {"before":"black==26.5.1","after":"black==26.10.1","profiles":["dev","aggregate"],"class":"authored_security_replacement"},
  "certifi": {"before":"certifi==2026.1.4","after":"certifi==2026.10.19","profiles":["runtime","docker-runtime","ci-lite","dev","rag-vector","rag-vector-cpu","aggregate"],"class":"authored_security_replacement"},
  "fastembed": {"before":"fastembed==0.8.0","after":"fastembed==0.8.0+pulseplate.1","profiles":["rag-vector","rag-vector-cpu"],"class":"separately_authorized_compatibility_companion"},
  "filelock": {"before_by_profile":{"ci-lite":"filelock==3.24.3","dev":"filelock==3.24.3","rag-vector":"filelock==3.29.4","rag-vector-cpu":"filelock==3.29.4","aggregate":"filelock==3.29.1"},"after":"filelock==4.2.1","class":"authored_security_replacement"},
  "opentelemetry-api": {"before":"opentelemetry-api==1.44.0","after":"opentelemetry-api==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"authored_security_replacement"},
  "opentelemetry-exporter-http-transport": {"before":null,"after":"opentelemetry-exporter-http-transport[requests]==0.66b1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "opentelemetry-exporter-otlp-common": {"before":null,"after":"opentelemetry-exporter-otlp-common==0.66b1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "opentelemetry-exporter-otlp-proto-common": {"before":"opentelemetry-exporter-otlp-proto-common==1.44.0","after":"opentelemetry-exporter-otlp-proto-common==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "opentelemetry-exporter-otlp-proto-http": {"before":"opentelemetry-exporter-otlp-proto-http==1.44.0","after":"opentelemetry-exporter-otlp-proto-http==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "opentelemetry-proto": {"before":"opentelemetry-proto==1.44.0","after":"opentelemetry-proto==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "opentelemetry-sdk": {"before":"opentelemetry-sdk==1.44.0","after":"opentelemetry-sdk==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "opentelemetry-semantic-conventions": {"before":"opentelemetry-semantic-conventions==0.65b0","after":"opentelemetry-semantic-conventions==0.66b1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"independently_reproduced_solver_closure"},
  "packaging": {"before":"packaging==25.0","after":"packaging==26.3","profiles":["runtime","docker-runtime","ci-lite","test","dev","rag-vector","rag-vector-cpu","aggregate"],"class":"independently_reproduced_solver_closure"},
  "pillow": {"before":"pillow==12.3.0","after":"pillow==13.0.0","profiles":["runtime","docker-runtime","ci-lite","dev","rag-vector","rag-vector-cpu","aggregate"],"class":"authored_security_replacement"},
  "pip-tools": {"before":"pip-tools==7.6.0","after":"pip-tools==7.6.1","profiles":["dev","aggregate"],"class":"separately_authorized_compatibility_companion"},
  "setuptools": {"before":"setuptools==83.0.0","after":"setuptools==84.1.0","profiles":["runtime","docker-runtime","ci-lite","dev","aggregate"],"class":"authored_security_replacement"},
  "virtualenv": {"before":"virtualenv==21.14.5","after":"virtualenv==21.14.10","profiles":["ci-lite","dev","aggregate"],"class":"authored_security_replacement"}
}
```

The final candidate-A audit ran from `2026-10-24T02:58:20.557568Z` through
`2026-10-24T03:01:14.462470Z`. Every scanner and adapter validation returned 0:
ten locks, 561 package occurrences, zero findings, zero skips and no inventory
errors. The later binding verified that every audited input equals both replay
outputs and the adopted lock bytes. All 53 primary head postconditions passed.
The two private FastEmbed occurrences retain the explicit byte-proven upstream
comparison; no direct PyPI audit of the private version is claimed. Audit proof
SHA-256:
`984355915034a47d778aa569c423240e6c2b73e3d9d1243dd287bfb464119dbb`.

| Adopted lock | Packages | Findings | Exit | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `requirements-ci-lite.txt` | 106 | 0 | 0 | `535374684bf646b5ebfc4622d566bbc9325189c5e1f82efeba5fc3ac0c408709` |
| `requirements-data.txt` | 5 | 0 | 0 | `1d6ccad5c345d99ef0e67fc85c6eea5350a1e4aed839e0aeb132beb393712792` |
| `requirements-dev.txt` | 89 | 0 | 0 | `44b1c1c0c79ceed5a7ac64886b40a0314e80268d3b9e8bdf53b93fbcc39992e0` |
| `requirements-docker-runtime.txt` | 61 | 0 | 0 | `946244b2713e43f8fc42066eac794e47ce23d19e259bc5592925f58be72b2d96` |
| `requirements-evals.txt` | 0 | 0 | 0 | `e67fe66dfd94ccda260fee2fbaf6da25ae28262753e849b454b1f26baad8c206` |
| `requirements-lock.txt` | 137 | 0 | 0 | `4d015a1be44a183e84eabe07f41c5611f4eff83fc498c1cb854b03ea8f666106` |
| `requirements-rag-vector-cpu.txt` | 35 | 0 | 0 | `05f64424ae0779765239e9e5cc73362f07828808db046efcf3a260bdfb99eaaf` |
| `requirements-rag-vector.txt` | 35 | 0 | 0 | `9de7f03220711fa24b6291a7889bdf12ddf7e989502b5b1ac4c41051165bcfd2` |
| `requirements-test.txt` | 23 | 0 | 0 | `5d0c7403d86c48cea7b500328de68fce74e76b5eaa5419f592c7710c89fd103e` |
| `requirements.txt` | 70 | 0 | 0 | `a6abdaa0af537fd519950127707ebf5f4cb1774db84935e1bf609c44274600f5` |

The eight exact installation selections contain runtime 70, runtime-dev 137,
runtime-test 87, CI-lite 106, CI-test 118, runtime+RAG 88, Docker runtime 61
and manual CPU 35 artifacts, excluding bootstrap pip. Composition agreement is
not installation or runtime execution proof; the separately observed native
matrix below supplies those bounded execution results. Final narrow gates,
hosted current-head CI and review remain independent publication requirements.

### AM03 native profile and consumer evidence

The fresh amended matrix ran from `2026-10-24T03:10:34.566872Z` to
`2026-10-24T03:24:43.356467Z`, taking 848.752s. Preparation, one reference-only
baseline and all eight product profiles exited 0. The owned emulated Linux
amd64 CPython 3.13.14 guest used two CPUs and two GiB; installation consumed the
canonical exact profile selections, and native probes used the existing clean,
offline namespace boundary. Each actual installed inventory matched its exact
selection; startup guards and `pip check` passed. The guest was stopped normally
after its owned work completed.

This run remains bound to its actual frozen 5722-path source snapshot:
`41330f91574c8edc5148052ee5fe0b7b6aa4925176f170151990d53062237c31`.
The snapshot bytes stayed unchanged. At 03:26 UTC the recorded working-tree
comparison differed only in this owner document and the ledger; executable and
dependency bytes then matched. Subsequent fixture-serialization and Dependabot
owner corrections have their own focused validation and do not change native
consumer, compiler or lock inputs. This is component continuity, not retroactive
execution of later documentation, control-plane changes or a final Git head. Native matrix proof SHA-256:
`1f6b03c4f4c1882ae25b98ad14f5fe57b1564fbae70ecfdf0a1048f56f90097f`;
observed summary SHA-256:
`4cdf8e21c94a64995cdf88663230d5b481022d73aa0ecefa5db80c2c118c7418`.

All eight product environments observed pip 26.2.2 and the fixed CA payload
`50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`.
Applicable profiles observed setuptools 84.1.0, filelock 4.2.1 and virtualenv
21.14.10. Runtime-dev also executed pip-tools 7.6.1, Black 26.10.1 and a fresh
offline virtualenv child. The seven SDK-bearing profiles loaded Psycopg C 3.3.4,
libpq 180006 and OpenSSL 3.5.9 with the same qualified native library hashes.
A real database connection was not exercised. Existing OpenTelemetry and
TestClient probes retain their recorded local/offline scope.

Both runtime+RAG and manual CPU executed the real offline embedding comparison
against the unchanged reference model `BAAI/bge-base-en-v1.5`, revision
`199291fdd1aa89faf9c20b722dc72ad5e17aa0d0`, tokenizer 0.23.1 and ONNXRuntime
1.27.0. They produced finite `[13, 768]` arrays with maximum absolute delta
`0.0`, within `rtol=1e-5` and `atol=1e-6`; query rankings were identical and
retrieval against persisted baseline BGE vectors succeeded. Each observed only
loopback and external-connect errno 101. Candidate-result hashes are
`df5901cea3b7dc9d7a6011745d0b5042023d9fee8827596d4ef5baec45605ffa`
(runtime+RAG) and
`f8120bffbde18a003000f7f34ba8dfe06b316e26d6b35138438ddd11797ffe7c`
(manual CPU).

Exactly four shared package versions differ from the reference: FastEmbed,
Pillow, packaging 25.0 to 26.3 and filelock 3.29.4 to 4.2.1. Runtime+RAG also
contains 53 additional packages; manual CPU has no additions. The reference's
older Pillow/filelock versions are retained only for the isolated comparison,
not as product locks or an audit PASS. These observations establish the named
graph/corpus compatibility, not isolated two-package causality or historical
MPNet compatibility.

The seven export-bearing product profiles produced and decoded real
PNG/JPEG/WEBP files and canonical CSV/PDF/image-PDF outputs. Six profiles also
executed the existing Matplotlib chart; Docker's profile intentionally has no
Matplotlib and uses a real Pillow image. All fourteen PDFs independently parsed
as one page. Both Docker PDFs rendered successfully and were visually inspected:
the meal table/totals were readable and the embedded image appeared correctly.
Parser proof SHA-256:
`138f6cff0e4d69d58fd450ac6aaa8f4414adeae42ef92350b325a670b95aacc3`;
visual-observation proof SHA-256:
`dcfb3ec74ff38170b785066b35030040d6e2cf335944d85725d6569424571769`.

This owned Linux consumer matrix does not establish a final Docker image build,
real database connectivity, hosted workflow success, review completion or merge
readiness. Those applicable final gates remain independently required.

## Historical October 23 advisory and surface inventory

The following subsection preserves the original five-identity snapshot and its
then-selected targets. It is not the governing AM03 inventory or current success.

Pip-audit 2.10.1 observed all ten registered compiled locks from
`2026-10-23T10:19:10.624000Z` through `2026-10-23T10:19:14.400522Z`:
five affected identities, forty distinct advisory identities, 264 occurrences
and zero skipped dependencies. The empty eval lock is a registered observed
surface. These counts do not describe all security defects or future advisories.
The exact compact serialization SHA-256 is
`7efe1e22f40e515df0e01571b44233a5e54af80cc3a3a7e59c1a29abf7ff66f4`;
formatted snapshot bytes separately hash to
`47bf161d4c6b8460efca78f0f893c06c0c158121a08cdfd6d3238e965bbdd0bf`.
Per-report original raw stdout digests were matched by retained reacquisitions;
the later acquisition time does not replace the original snapshot interval.

| Compiled surface | Packages | Findings | Exit | Base lock SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `requirements.txt` | 68 | 37 | 1 | `45856873613fa43e5ac34c2673ecd3cb29e97aecf33b91dedcefcf7aee56d054` |
| `requirements-docker-runtime.txt` | 59 | 37 | 1 | `158d23745f9c8b3160bedf080a5d0853e3328300b05b3fe9015182f306389a75` |
| `requirements-ci-lite.txt` | 104 | 39 | 1 | `771b48e95e960af8c0b43142b9bdf3fab493b5fb26884d0e1b262988bd04fa0c` |
| `requirements-test.txt` | 23 | 0 | 0 | `8f463b624999802c8f61a85e11ccc1c19b4581a5d0dbe7a89d9dbb313938d195` |
| `requirements-dev.txt` | 89 | 39 | 1 | `173aaf867f1654dd36cda34151f78db8e64cf19210ae301c32b7234d5f8a86e8` |
| `requirements-rag-vector.txt` | 35 | 36 | 1 | `1eb69b82d5389fdcd6697c6988a4cae81b8c405e455a51cf53f7c81d1a29fc4f` |
| `requirements-rag-vector-cpu.txt` | 35 | 36 | 1 | `530fc49cd17c7c491ff37c35dfeb265ff6fb263506aa901e4b5b2e01f8568fe7` |
| `requirements-data.txt` | 5 | 0 | 0 | `1d6ccad5c345d99ef0e67fc85c6eea5350a1e4aed839e0aeb132beb393712792` |
| `requirements-evals.txt` | 0 | 0 | 0 | `e67fe66dfd94ccda260fee2fbaf6da25ae28262753e849b454b1f26baad8c206` |
| `requirements-lock.txt` | 135 | 40 | 1 | `c31f9168bba70db0f9eb3d8f27dab65ed2da9b4cfbedaf611de60086ab8912fe` |

Tracked source/constraint discovery uses the existing owner
`scripts/ci/dependabot_requirement_carriers.py:573`; compiled profile ownership
is defined in `docs/contracts/PYTHON_DEPENDENCY_SURFACES.md`.

| Identity | Base/head authored carriers | Replacement intent and selected target |
| --- | --- | --- |
| certifi | No explicit base source; new `requirements.in` and `constraints.txt` floors | `>=2026.10.19`; target 2026.10.19 |
| opentelemetry-api | Runtime, Docker-runtime and CI-lite `.in` files | `>=1.45.1,<2.0.0`; target 1.45.1 |
| pillow | The three runtime inputs above, dev `.in`, `constraints.txt` | `>=13.0.0,<14.0.0`; existing exact constraint advances to 13.0.0 |
| virtualenv | CI-lite and dev `.in` files | `>=21.14.9`; target 21.14.9 |
| black | Dev `.in`, `constraints.txt`, convenience-only `requirements-all.txt`; separate Black hook | Compatible/floor inputs and hook advance to 26.10.1 |

The aggregate lock contains all five affected base witnesses. Runtime, Docker
and CI-lite also contain certifi/API/Pillow; dev contains
Black/certifi/Pillow/virtualenv; both vector locks contain certifi/Pillow.
Every base witness listed below is affected by its primary range. A equals
F_cutoff for each identity and is nonempty; no non-applicable-at-base row is
omitted. The retained forty-primary-payload index SHA-256 is
`c9f12715521e7f42dfb85ff315cfff7663099e0ee82a06cb8f7ee6ac29a27169`.
Primary ranges, including the two different virtualenv floors, govern this
reconciliation. Scanner identifiers and GHSA aliases refer to the same
corresponding row, not additional findings.

Each row was independently checked with `packaging.specifiers.SpecifierSet`:
its exact base witness is affected and its selected candidate is outside the
range. The current working-material guard now checks all forty ranges over
every present occurrence discovered in the 21 registered tracked carriers.
The census contains Black 5, certifi 9, API 7, Pillow 12 and virtualenv 5
occurrences; the separate Black hook also matches the dev/aggregate locks.
Census SHA-256: `f1be0b095cd58abd9741e58a43c39f7ce4da7068ff2dbbe2eb0200fbc96eba28`.
This component result does not replace final current-head CI or runtime proof.

| Identity | Primary advisory / scanner identifier | Affected range | Base witness | Selected candidate |
| --- | --- | --- | --- | --- |
| pillow | [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9) / CVE-2026-112390 | `>= 7.2.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-24rc-8hj2-v98c](https://github.com/advisories/GHSA-24rc-8hj2-v98c) / CVE-2026-96638 | `>= 9.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-254f-3936-288h](https://github.com/advisories/GHSA-254f-3936-288h) / CVE-2026-112391 | `>= 5.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-27h8-gf7j-v5hc](https://github.com/advisories/GHSA-27h8-gf7j-v5hc) / CVE-2026-112392 | `<= 12.3.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-332p-7hrc-92wf](https://github.com/advisories/GHSA-332p-7hrc-92wf) / CVE-2026-112393 | `>= 2.0.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-3j72-p6qg-6xp7](https://github.com/advisories/GHSA-3j72-p6qg-6xp7) / CVE-2026-96642 | `< 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-462x-pgg6-55fp](https://github.com/advisories/GHSA-462x-pgg6-55fp) / CVE-2026-112395 | `>= 8.2.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-4rm8-3hmm-39fg](https://github.com/advisories/GHSA-4rm8-3hmm-39fg) / CVE-2026-96641 | `< 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-4rr5-89j8-mwwm](https://github.com/advisories/GHSA-4rr5-89j8-mwwm) / CVE-2026-112396 | `>= 11.3.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-58r4-6rv3-gfh8](https://github.com/advisories/GHSA-58r4-6rv3-gfh8) / CVE-2026-112397 | `<= 12.3.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-5xm2-6676-qcp9](https://github.com/advisories/GHSA-5xm2-6676-qcp9) / CVE-2026-112399 | `>= 8.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-65qm-jvmh-6pqg](https://github.com/advisories/GHSA-65qm-jvmh-6pqg) / CVE-2026-112400 | `>= 9.2.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| certifi | [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) / PYSEC-2026-4320 | `>= 2019.03.09, < 2026.10.19` | `2026.1.4`: affected | `2026.10.19`: outside |
| pillow | [GHSA-74r2-7ff9-mjj2](https://github.com/advisories/GHSA-74r2-7ff9-mjj2) / CVE-2026-112401 | `>= 5.4.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-78g4-xqwv-q3g8](https://github.com/advisories/GHSA-78g4-xqwv-q3g8) / GHSA-78g4-xqwv-q3g8 | `>= 11.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-7mwm-ghpf-9vrm](https://github.com/advisories/GHSA-7mwm-ghpf-9vrm) / CVE-2026-112402 | `<= 12.3.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-9v9v-9qvf-h2hj](https://github.com/advisories/GHSA-9v9v-9qvf-h2hj) / CVE-2026-96644 | `< 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-c6hw-5grf-ff96](https://github.com/advisories/GHSA-c6hw-5grf-ff96) / CVE-2026-112404 | `>= 8.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| virtualenv | [GHSA-c978-59m8-c77v](https://github.com/advisories/GHSA-c978-59m8-c77v) / CVE-2026-113722 | `< 21.14.9` | `21.14.5`: affected | `21.14.9`: outside |
| black | [GHSA-cg8m-r9f2-5wm2](https://github.com/advisories/GHSA-cg8m-r9f2-5wm2) / CVE-2026-114134 | `< 26.10.1` | `26.5.1`: affected | `26.10.1`: outside |
| pillow | [GHSA-cp9v-662q-vvx9](https://github.com/advisories/GHSA-cp9v-662q-vvx9) / CVE-2026-112405 | `>= 12.0.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-f2g6-542v-9j58](https://github.com/advisories/GHSA-f2g6-542v-9j58) / CVE-2026-112406 | `>= 5.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-fc9g-5qg7-mf45](https://github.com/advisories/GHSA-fc9g-5qg7-mf45) / CVE-2026-112891 | `>= 9.2.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-g4qv-2jxx-769h](https://github.com/advisories/GHSA-g4qv-2jxx-769h) / CVE-2026-96643 | `>= 11.0.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-g7cr-3p24-7wf7](https://github.com/advisories/GHSA-g7cr-3p24-7wf7) / CVE-2026-96778 | `>= 9.4.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-g842-9rc4-69pw](https://github.com/advisories/GHSA-g842-9rc4-69pw) / CVE-2026-96637 | `< 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-gg2r-wvfm-q9rx](https://github.com/advisories/GHSA-gg2r-wvfm-q9rx) / CVE-2026-112892 | `>= 4.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-j4m9-6w36-pw47](https://github.com/advisories/GHSA-j4m9-6w36-pw47) / CVE-2026-112893 | `>= 10.0.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-jg86-v3jv-hrpm](https://github.com/advisories/GHSA-jg86-v3jv-hrpm) / CVE-2026-112894 | `>= 5.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-mrfp-p49p-3hf2](https://github.com/advisories/GHSA-mrfp-p49p-3hf2) / CVE-2026-96640 | `>= 5.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-p4wg-p73j-c528](https://github.com/advisories/GHSA-p4wg-p73j-c528) / CVE-2026-112895 | `>= 5.1.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-p8hx-v2p6-rp84](https://github.com/advisories/GHSA-p8hx-v2p6-rp84) / CVE-2026-96636 | `< 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-pchr-8j38-3x4p](https://github.com/advisories/GHSA-pchr-8j38-3x4p) / CVE-2026-112896 | `<= 12.3.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-q45j-58j2-45rg](https://github.com/advisories/GHSA-q45j-58j2-45rg) / CVE-2026-112897 | `>= 5.3.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-v9pv-5gc8-w2m6](https://github.com/advisories/GHSA-v9pv-5gc8-w2m6) / CVE-2026-96639 | `>= 11.0.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| pillow | [GHSA-vx6w-vv9f-6gvg](https://github.com/advisories/GHSA-vx6w-vv9f-6gvg) / CVE-2026-112899 | `>= 2.3.0, <= 12.3.0` | `12.3.0`: affected | `13.0.0`: outside |
| virtualenv | [GHSA-vxj4-q4g9-crj7](https://github.com/advisories/GHSA-vxj4-q4g9-crj7) / CVE-2026-113725 | `<= 21.14.6` | `21.14.5`: affected | `21.14.9`: outside |
| pillow | [GHSA-w889-685w-c8fh](https://github.com/advisories/GHSA-w889-685w-c8fh) / CVE-2026-112900 | `>= 2.6.0, < 13.0.0` | `12.3.0`: affected | `13.0.0`: outside |
| opentelemetry-api | [GHSA-xcq7-p3pf-p88h](https://github.com/advisories/GHSA-xcq7-p3pf-p88h) / CVE-2026-114603 | `<= 1.45.0` | `1.44.0`: affected | `1.45.1`: outside |
| pillow | [GHSA-xgh8-jp6q-p5x8](https://github.com/advisories/GHSA-xgh8-jp6q-p5x8) / CVE-2026-112901 | `<= 12.3.0` | `12.3.0`: affected | `13.0.0`: outside |

## Historical October 23 authored actions and resolver closure

Security I_R contains exactly the five replacements above. FastEmbed, pip and
the explicitly approved pip-tools compatibility amendment are separate
companion actions. Certifi has explicit runtime
ownership at `requirements.in:17`; the global constraint retains its floor.
No packaging direct dependency or unrelated source floor is authored.

Canonical generation and independent replay reproduced OTel family 1.45.1,
semantic conventions 0.66b1, the two additional exporter identities and
packaging 26.3. The transport retains its `requests` extra. Virtualenv's new
packaging floor propagates through runtime-constrained profiles, including
test. The existing finite admission retains complete source/seed/artifact/profile
bindings and default/legacy rejection. The terminal native runs and replay,
rather than admission metadata alone, establish the recorded solver closure.

The owner explicitly approved pip-tools 7.6.1 on October 23 after canonical
Make failed with pip-tools 7.6.0 and mandatory pip 26.2.2 at the import of
`pip._internal.utils.compat.stdlib_pkgs`. The authored change at
`requirements-dev.in:37` applies only to dev and aggregate locks; it is not
C_R or another security-batch identity. The existing admission binds the
74661-byte `pip_tools-7.6.1-py3-none-any.whl`, SHA-256
`6111c8b4b07fd14b7223ca921485b0e96cf66e20bf94da95eeed9845f510cb8f`,
verified against primary metadata and the approved proxy. A separate owned
Linux amd64 CPython 3.13.14 probe with pip 26.2.2/pip-tools 7.6.1 passed
`pip check` and a real offline single-package compile. Application lock
generation/replay and installed dev-profile execution subsequently completed as
recorded below; hosted checks remain separate.

Use canonical `make requirements-locks`, runtime first, then constrained
profiles. Retain every actual command, resolver version, original-base replay
and complete classified dependency delta before claiming C_R. Never hand-edit
locks/seeds, rotate baselines, bypass conflicts or accept unexplained changes.
Pip remains outside application locks. Final P is the conjunction of all five
universal F_cutoff postconditions; partial success is insufficient. The two
unchanged data/eval locks stay in the ten-lock final audit inventory.

The initial candidate exposed a packaging conflict in the existing runtime-test
and ci-test installation compositions: runtime/CI-lite selected 26.3 while the
test lock retained 25.0. The unchanged `requirements-test.in:1` already constrains
the test resolver through runtime. The same finite admission therefore includes
the original test seed and that unchanged source, with only packaging 25.0 to
26.3 expected in the test lock. This adds no authored target or security identity.
Canonical generation and original-base replay produced that exact test delta,
and composition checks now pass; advisory audits still do not prove installation
or execution of the composed environments.

The permanent guard reuses canonical tracked-carrier discovery and the
existing requirement parser for every present occurrence of the five
identities, retaining all 40 primary advisory ranges and earlier virtualenv
advisories (`tests/test_dependency_security_guard.py:3880`). Its synthetic
controls accept later safe versions and reject incomplete inventories,
symlinks, malformed carriers and unsafe aliases. The real adopted-material
postcondition and Black hook parity checks returned `4 passed in 1.55s`, exit 0.
The initial parity check exposed a stale 26.5.1 test expectation; it was corrected
to the already adopted Black 26.10.1 without changing the hook or admission.

## Historical October 23 generation, delta, audit and native evidence

The exact base remained `48d36c220ff58dec82450da66ef0599c6da71787`.
Execution used owned Linux amd64 CPython 3.13.14 under Mac emulation, pip 26.2.2,
pip-tools 7.6.1, the approved private index and the genuine source-built SDK.
Independent original runtime runs produced the same bytes. Scope06's native
current-admission checks accepted both retained runtime checkpoints after proving
unchanged runtime code projection, sources, artifacts, tool inventory and SDK.
Those original receipts keep their original material identity; runtime was not
retroactively relabeled or re-executed.

Fresh dependent A2 and B2 used original dependent seeds, including test, and
both exited 0 (538.165s and 524.452s). Their ten outputs matched byte-for-byte;
the runtime checkpoint stayed unchanged. Eight locks changed and data/eval
stayed unchanged. The complete replay proof SHA-256 is
`f3c4aee0b5fb4e951ed600148d6bfbf7fde5caa78b63bece4a9a1104e98b0428`;
A2/B2 terminal receipt hashes are
`98500e6282602932b25921c550c0deca39e1a60bb2c7cb6a7d1c6f3898866e18`
and `b52024524a3f0229a0a2b7c8450f54cef7535fecdeeeeb8275848cc429476478`.

The historical run used its then-authorized seven-target request. AM03 uses
the revised nine-target request in [the runbook commands](../../RUNBOOK_AGENT.md),
with the qualified owned
interpreter, approved index and SDK selected explicitly:

```bash
make requirements-locks VENV_PYTHON="$STABILIZATION_PYTHON" \
  LOCK_PROFILES='runtime' UPGRADE_PACKAGES="$STABILIZATION_UPGRADES" \
  GRAPH_CHANGE_PACKAGES="$STABILIZATION_GRAPH" \
  GRAPH_CHANGE_ADMISSION='python-stabilization-2026-10-23'
make requirements-locks VENV_PYTHON="$STABILIZATION_PYTHON" \
  LOCK_PROFILES='docker-runtime ci-lite dev test rag-vector rag-vector-cpu aggregate' \
  UPGRADE_PACKAGES="$STABILIZATION_UPGRADES" \
  GRAPH_CHANGE_PACKAGES="$STABILIZATION_GRAPH" \
  GRAPH_CHANGE_ADMISSION='python-stabilization-2026-10-23'
```

Three raw lines present in both dependent logs, terminal exit 0 for each:

```text
Updated governed lock profile docker-runtime: requirements-docker-runtime.txt
Updated governed lock profile test: requirements-test.txt
Updated governed lock profile aggregate: requirements-lock.txt
```

The following JSON accounts for all 15 changed dependency identities across
all eight changed locks. Requirement strings retain exact extras; all markers
and URLs are absent. The two added identities are solver closure. FastEmbed and
pip-tools remain separately authorized authored companions, outside the five
security-identity batch. No transition or suppression is omitted.

```json
{
  "black": {"before":"black==26.5.1","after":"black==26.10.1","profiles":["dev","aggregate"],"class":"authored_security_replacement"},
  "certifi": {"before":"certifi==2026.1.4","after":"certifi==2026.10.19","profiles":["runtime","docker-runtime","ci-lite","dev","rag-vector","rag-vector-cpu","aggregate"],"class":"authored_security_replacement"},
  "fastembed": {"before":"fastembed==0.8.0","after":"fastembed==0.8.0+pulseplate.1","profiles":["rag-vector","rag-vector-cpu"],"class":"separately_authorized_compatibility_companion"},
  "opentelemetry-api": {"before":"opentelemetry-api==1.44.0","after":"opentelemetry-api==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"authored_security_replacement"},
  "opentelemetry-exporter-http-transport": {"before":null,"after":"opentelemetry-exporter-http-transport[requests]==0.66b1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "opentelemetry-exporter-otlp-common": {"before":null,"after":"opentelemetry-exporter-otlp-common==0.66b1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "opentelemetry-exporter-otlp-proto-common": {"before":"opentelemetry-exporter-otlp-proto-common==1.44.0","after":"opentelemetry-exporter-otlp-proto-common==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "opentelemetry-exporter-otlp-proto-http": {"before":"opentelemetry-exporter-otlp-proto-http==1.44.0","after":"opentelemetry-exporter-otlp-proto-http==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "opentelemetry-proto": {"before":"opentelemetry-proto==1.44.0","after":"opentelemetry-proto==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "opentelemetry-sdk": {"before":"opentelemetry-sdk==1.44.0","after":"opentelemetry-sdk==1.45.1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "opentelemetry-semantic-conventions": {"before":"opentelemetry-semantic-conventions==0.65b0","after":"opentelemetry-semantic-conventions==0.66b1","profiles":["runtime","docker-runtime","ci-lite","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "packaging": {"before":"packaging==25.0","after":"packaging==26.3","profiles":["runtime","docker-runtime","ci-lite","test","dev","rag-vector","rag-vector-cpu","aggregate"],"class":"solver_closure_reproduced_from_original_dependent_seed"},
  "pillow": {"before":"pillow==12.3.0","after":"pillow==13.0.0","profiles":["runtime","docker-runtime","ci-lite","dev","rag-vector","rag-vector-cpu","aggregate"],"class":"authored_security_replacement"},
  "pip-tools": {"before":"pip-tools==7.6.0","after":"pip-tools==7.6.1","profiles":["dev","aggregate"],"class":"separately_authorized_compatibility_companion"},
  "virtualenv": {"before":"virtualenv==21.14.5","after":"virtualenv==21.14.9","profiles":["ci-lite","dev","aggregate"],"class":"authored_security_replacement"}
}
```

A fresh pip-audit 2.10.1 pass ran from `2026-10-23T21:09:47.827280Z` to
`2026-10-23T21:12:17.187662Z`. All ten scanner and adapter-validation commands
exited 0, with zero findings, no skips or inventory errors, and 561 total package
occurrences. Both FastEmbed rows use the explicit byte-proven upstream comparand,
not a claim that PyPI directly audited the private version. Raw reports and
sidecars bind the exact lock hashes below; summary SHA-256 is
`0ff86a642f435ad888e2b669fb7dc8ec95edd71aa91c8b70b4fde24c57270d96`.

| Candidate lock | Packages | Findings | Exit | Lock SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `requirements.txt` | 70 | 0 | 0 | `8248d549c174823e08251e34ae8e15cb78320e613bbeddafae7baa822a8d682a` |
| `requirements-docker-runtime.txt` | 61 | 0 | 0 | `0d3a0f7dda8efa490217dee902c47a5940cf1f9096ee2cda5d65e0184c09be9b` |
| `requirements-ci-lite.txt` | 106 | 0 | 0 | `cb8f2344a3777ff218d96d055f54f0e82311e917627312f6bda27e0b50f5d09d` |
| `requirements-test.txt` | 23 | 0 | 0 | `5d0c7403d86c48cea7b500328de68fce74e76b5eaa5419f592c7710c89fd103e` |
| `requirements-dev.txt` | 89 | 0 | 0 | `6e2e89281c21b024faac6ba6ed4042e1c39f1c9badc0c060d22895981bf6daba` |
| `requirements-rag-vector.txt` | 35 | 0 | 0 | `cfc54845436be1dfa4763af7d76054d016e6222c848e0b965de34cdd476b78e6` |
| `requirements-rag-vector-cpu.txt` | 35 | 0 | 0 | `c3d3d096333a89c78174f0ea876c5347ae552a10c245a59caa0c2618701e6697` |
| `requirements-data.txt` | 5 | 0 | 0 | `1d6ccad5c345d99ef0e67fc85c6eea5350a1e4aed839e0aeb132beb393712792` |
| `requirements-evals.txt` | 0 | 0 | 0 | `e67fe66dfd94ccda260fee2fbaf6da25ae28262753e849b454b1f26baad8c206` |
| `requirements-lock.txt` | 137 | 0 | 0 | `80d0458f20fc3e42d834f95a764d363807a89f8abc816523cdc0496a8902dad1` |

The canonical exact-pin reader accepted runtime (70), runtime-dev (137),
runtime-test (87), CI-lite (106), CI-test (118), runtime+RAG (88), explicit
Docker runtime (61) and explicit manual CPU (35) artifact selections. All eight
then installed into separate fresh venvs through the canonical installer, with
exact wheel views, startup guards, pip 26.2.2 and successful `pip check`.
The counts exclude bootstrap pip. Aggregate remains audit-only.

The native matrix ran from `2026-10-23T21:51:07.134979Z` through
`2026-10-23T22:02:19.214778Z`: prepare, one reference-only baseline and eight
product cases all exited 0. It used the owned two-CPU/two-GiB Linux amd64
CPython 3.13.14 guest; consume/probes ran in an isolated network/user namespace
with clean HOME, outer UID 501 and namespace UID 0. Source material digest:
`6aecdbeb1b02a3ead967119e0d027222f78a0c3075901ff7811be8250aedc61b`.
The exported tracked bytes stayed unchanged. A separate comparison confirms
the 21 recorded dependency/installer/runtime component files still match the
working tree; this does not relabel the native run as execution of later CI
caller changes or of the final full material. Matrix receipt SHA-256:
`d404a93e292101b8f4de754a37ad699e430af72ef452787e66e75d849f5d3979`;
component comparison SHA-256:
`3e1d9f6cfb54725fd7d9ec627e6c8954a31affebd875aa0e0d959cbbbc432237`.

All seven SDK-bearing cases loaded Psycopg C 3.3.4, libpq 180006 and OpenSSL
3.5.9 with mapped-library hashes matching the genuine SDK. No database
connection was exercised. Each recorded one valid in-memory OpenTelemetry
span and imported the actual OTLP HTTP exporter without network export or
global product-provider mutation. Both test compositions exercised real
TestClient health/BMI responses and invalid-input 422; runtime-dev executed
pip-tools, Black and creation of a fresh offline virtualenv child. The manual
CPU and reference baseline used no SDK. Complete per-case inventories, command
environments, exits and log/output hashes are retained; observed-summary SHA-256:
`0864f8cb412542215052039a4c8e163caa32c9ff88437408f47302895a5a3baf`.

The first preparation correctly rejected five uncovered CI-lite version tuples;
adding the existing CI-lite acquisition selection fixed the exact pool coverage.
The second completed all three product acquisitions but rejected private
FastEmbed selected by `==0.8.0` for the reference fixture. The successful attempt
revalidated those cached pools and used the retained hash-proved upstream wheel,
acquiring only missing reference Pillow/packaging wheels. Both failures and
their original logs remain retained; no lock, parser or dependency-resolution
check was weakened.

## FastEmbed compatibility evidence

The approved-index upstream wheel is 116572 bytes, SHA-256
`40bee672657574a1009e35ec50030a55f2b426842cb011845379817641bbbbd0`,
checked before ZIP interpretation. The offline transformer
`scripts/ci/build_fastembed_compat_wheel.py:210` and adjacent recipe change only
distribution Version, the three Pillow `<13.0` upper bounds to `<14.0`,
matching dist-info coordinates and RECORD. Python markers, lower bounds,
Requires-Python, license/notice and executable bytes remain intact.

Two independent builds produced identical 116726-byte wheels, SHA-256
`3dd7642eb4d7ceecf208df4c9e290b08f14f28007b056ff81488810b9a366a45`.
Independent inspection checked all 64 members/modes and complete RECORD:
62 payloads identical; only METADATA and RECORD payloads changed. The retained
build-proof JSON SHA-256 is
`d739daebcb5040bd8c47e5a28d6415353287e62eae2bc267eff39f60d40f2b72`.
The builder neither executes package code nor publishes a package.

The earlier compatibility experiment used an owned Apple Container guest running
Linux/aarch64 CPython 3.13.14 from the
immutable Python image index
`sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64`.
Two independently installed 35-package compatibility fixtures shared
ONNXRuntime 1.27.0, NumPy 2.4.6, tokenizers 0.23.1, certifi 2026.10.19 and
pip 26.2.2. Only FastEmbed/Pillow differed: 0.8.0/12.3.0 versus
0.8.0+pulseplate.1/13.0.0. These fixtures are not canonical profile installs.
Embedding execution used guest UID 0; separate readable-package/trust-payload
observation used final UID 501.

The model remains `BAAI/bge-base-en-v1.5`, 768 dimensions
(`core/rag/rag_constants.py:21`). Qdrant ONNX model/tokenizer revision:
`199291fdd1aa89faf9c20b722dc72ad5e17aa0d0`; model SHA-256:
`4e556722bc4f65716c544c8a931f1e90fb3f866e5741fd93a96f051d673339c7`;
tokenizer SHA-256:
`d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`.
All nine retained model files were checked. The thirteen-text corpus contains
six documents, three queries and four empty/whitespace/non-ASCII controls;
corpus SHA-256:
`d8b944920c2ab261251f48a42a0cd1ae5ae78760b8ade9ee84de6f9b4d92c498`.

Observed offline outputs were `[13, 768]`, all finite, maximum absolute delta
`0.0` under `rtol=1e-5`, `atol=1e-6`, identical query rankings and compatible
retrieval against persisted baseline BGE vectors. Native observations found
only DOWN loopback, empty route inventories and external-connect errno 101.
An initial sysfs-observer failure is retained separately; corrected native
interface observation does not erase that failed attempt. The existing model
acknowledgement (`core/rag/vector_rag.py:123`) remains unchanged; historical
MPNet compatibility is explicitly not claimed. This proof is bounded to the
specified corpus, model and Linux ARM environment.
Candidate embedding-result JSON SHA-256:
`580f26af41e6a75a57cf8dc2cd65cb5a3b1ff5398e302c2c715f7e18b9abba8b`.

The earlier October 23 Linux amd64 matrix independently installed the unchanged 35-package
reference fixture, then actually executed both canonical runtime+RAG and manual
CPU selections with the same model, tokenizer, corpus and ONNXRuntime 1.27.0.
Each produced finite `[13, 768]` vectors, maximum absolute delta `0.0` within
`rtol=1e-5`, `atol=1e-6`, identical rankings and successful retrieval against
persisted reference BGE vectors. Candidate-result SHA-256 values are
`27140a1d4ef96bd6a1e99bbfa9c7fa03e94bc02bb2504ea14fffc7e7b663f0dd`
(runtime+RAG) and
`4f54dccbcd85ddb598f256186a550e4b54ebf3d176c72bc42c09a8b40bf9da67`
(manual CPU). The reference fixture uses known-vulnerable Pillow only for the
offline synthetic comparison; it is not a product lock or an audit PASS.
Shared-package changes are FastEmbed, Pillow and packaging 25.0 to 26.3;
runtime+RAG additionally contains 53 packages absent from the reference, while
manual CPU has no additions. Full inventories and every addition are retained.
This is graph compatibility evidence, not isolated two-package causality or
historical MPNet compatibility.

The seven earlier export-bearing product environments produced and decoded real
PNG/JPEG/WEBP files and exercised canonical PDF/CSV and image-PDF
exports; the six containing matplotlib 3.10.8 also executed the canonical BMI
chart. Docker intentionally has no Matplotlib and embeds a real Pillow image.
All fourteen PDFs independently parsed as one page, and both Docker PDFs were
rendered successfully; the meal export's displayed table and totals were also
visually checked. PDF parser/render receipt SHA-256:
`ea9b319fc522d3b13e1873cf164b6200134e96ea61311a54cb0b448bca1d5582`.
The earlier ARM pinned-consumer result remains separate, SHA-256
`f94d90bb7dc7c1b2c3f4f2a2090c337e9e0305773de2c2730f84d82bbac6aeae`;
the original unpinned attempt is retained and does not supply final-profile proof.

The first private-index upload POST was attempted by `pulseplate-upload` at
`https://packages.pulseplate.app/root/pulseplate/` from
`2026-10-23T11:50:34.343033Z` through `2026-10-23T11:50:38.401232Z` and
returned **HTTP 403**. The retained result records `upload_attempted=true`,
`readback_verified=false` and wheel SHA-256
`3dd7642eb4d7ceecf208df4c9e290b08f14f28007b056ff81488810b9a366a45`.
A later authenticated Cloudflare request observation
binds Ray `a4f086783d09ec9c` to the Twine POST at 14:50:38 GMT+3: edge 403,
HTML response, no origin status, and `Block by Managed rules`. The exact managed
rule remains unknown because the sampled security event is unavailable. The
original POST response headers/body were not retained; the separate GET's
Cloudflare challenge is not that POST's rule evidence or proof of a password,
devpi ACL or simple-index failure. The earlier administrative GET is not a
Twine prerequisite. That diagnosis supplied no upload exemption. A separately
authorized publication through the existing SSH account and loopback-only devpi
returned HTTP 200 during `2026-10-23T12:42:49.615175Z` through
`2026-10-23T12:43:17.330432Z`, with verified readback. An independent
credential-free public HTTPS read at `2026-10-23T12:44:11.006735Z` returned
200, `application/octet-stream`, 116726 bytes and the exact derived wheel
SHA-256 above. This establishes delivery of that package, not canonical lock
resolution, profile installation or remediation. The initial 403 remains
retained historical evidence. The [retirement obligation](../roadmap/BACKLOG_LEDGER.md#ledger-p1-fastembed-pillow13-compat-retirement)
requires a tested compatible upstream replacement.

The separately authorized October 23 Cloudflare tightening removed only
`All managed rules` skip from exactly the owner, health and discovery custom
rules; saved comparisons retain their other fields and the maintenance
predicate/action/order. Seven PHP CVE-2026-109618/109619 rules are enabled with
Block and the bypass warning is absent. The response UI changed from implicit
default `0/3` to explicit default `1/3`, all incoming / First / Active; historical
equivalence is not claimed. Benign package status/simple/wheel GET and HEAD
returned 200; the original wheel remains 116572 bytes with the upstream hash
above. Apex GET remains 302 to Cloudflare Access and www remains 308 to apex;
pre-existing health 302 and healthz 403 are unchanged. The broad packages
exception remains last after OWASP and was not moved earlier. These observations
establish neither universal WAF protection nor internal-wheel publication.

## Exact private-version advisory comparison

PyPI's strict audit of `fastembed==0.8.0+pulseplate.1` returned a collection
failure rather than direct private-version advisory coverage; the original
empty JSON and strict stderr remain failed evidence. The narrow adapter in
`scripts/ci/audit_fastembed_compat.py` prepares only an explicit upstream
`fastembed==0.8.0` comparand after acquiring and byte-checking the exact
upstream and published private wheels through the approved index and proving
their relation with the existing builder/recipe. It does not add a ZIP parser,
advisory alias registry, suppression, OSV fallback or installed-metadata edit.

`scripts/ci_pip_audit.sh` still owns actual scanner invocation, its default
PyPI service/socket timeout, six-manifest selection, raw report filenames and
aggregate failure behavior. Every scanner call is strict. Scanner processes
receive a private empty HOME and a minimal environment without host credentials.
Raw JSON and stderr are retained unchanged; the final evidence sidecar records
original/query coordinates and input digests, wheel/recipe provenance, tool
version/argv, shell-reported exit, report/stderr digests and inventory validation.
It is procedural evidence, not an independent execution attestation.

Validation re-reads original/comparand/provenance bytes after the scanner and
requires exact report-coordinate set equality. Pillow 13 and all other actual
pins remain unchanged. Unknown/skipped, missing, extra, duplicated, malformed
or stale reports and nonzero scanner exits fail closed. All upstream findings
remain visible and blocking; byte provenance does not dismiss them. The sidecar
explicitly denies direct auditing of the private version. Another private
version, a lookalike carrier or an executable patch requires rescope.
These six CI profiles do not replace the final required ten-lock audit or
the independent resolver, installation, RAG and Pillow observations.

## Source deadline and pip toolchain

Only `review_by` advances to October 30 inclusive; October 31 rejects. Raw
comparison against the base preserves `generated_at=2026-10-04` and all
seventeen source records (`scripts/ci/docker_source_artifacts.json:4`).
Default selection stays fifteen; explicit Alertmanager selection stays two.
Historical October 5/6 and 21/22 tests remain. This is a temporary authorized
admission window, not source qualification or another exception renewal.
The [source reassessment](../roadmap/BACKLOG_LEDGER.md#ledger-p1-python-stabilization-source-review)
remains due before expiry.

`Dockerfile:6` and `scripts/ci/install_locked_python_requirements.py:1291`
select `pip>=26.2.2,<27.0` for Docker/default upgrade paths; explicit specs,
selectors and proxy controls remain. The sandbox's final UID 501 could read
pip 26.2.2/certifi 2026.10.19. Pip's vendored CA payload matched its verified
wheel; vendored/application CA SHA-256 both equal
`50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`.
No enumerated trust override keys were present. Trust-payload JSON SHA-256:
`8a7197492756c78b6d4b467253e1c8468ff5fec2d0c7fe5427db1b7a8a3141d2`.
The subsequent eight fresh amd64 product profiles and reference baseline each
observed pip 26.2.2 and this same fixed CA payload. This proves the recorded
versions and readable payloads. Final project-image contents and effective
trust under each applicable hosted caller require independent evidence.

A separate fresh Mac arm64 virtualenv 21.14.9 probe exposed default pip 26.2.1
seeding, with embedded CA SHA-256
`bbc7e9c01d7551bb8a159b5dedd989b8ee3ce105aff522b68eb1b01bf854cab0`.
The same native creation with explicit pip 26.2.2 and a verified local wheel
produced the corrected `50f79f...` payload above. Both commands exited 0 without
child network acquisition. This observation is bounded to the recorded Mac
environment; it is not a hosted CI result. Eleven actual fresh owned Mac Python
hook environments subsequently reported pip 26.2.2 and the fixed CA hash, each
with exit 0; observation receipt SHA-256:
`1a661e72b63e4cff00426ead776167aa963303d297ac488dc8a22e0286e1f31a`.
Hook-environment creation and inspection are not terminal all-files execution.

The shared setup now calls the canonical installer with `--upgrade-pip-only`
and `pip==26.2.2` after private-index authentication and before SDK/profile
acquisition, then checks the actual parent version and embedded CA payload
(`.github/actions/python-setup/action.yml:104`). The existing skip-base predicate,
approved-index/trusted-host handling, exact emergency-manifest path and always
cleanup remain. The initial trusted upgrade is bootstrap; it does not establish
that the preceding interpreter was already patched.

The existing pre-commit step acquires and validates the exact 1819850-byte
`pip-26.2.2-py3-none-any.whl`, SHA-256
`fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70`,
through the installer owner (`.github/workflows/ci.yml:1034`). Primary PyPI
metadata independently confirms those bytes and non-yanked status. SDK selection
is cleared only for that seed-only acquisition. Explicit virtualenv version,
local search, no-download and no-periodic-update controls use owned app-data;
`PRE_COMMIT_HOME` is fresh. A native seed probe precedes the unchanged command,
and every actually created Python hook interpreter is checked for its virtual
environment, pip version and CA payload afterwards. Original pre-commit failure
status takes precedence over observation failures. Existing timeout, SKIP and
workflow selectors remain unchanged. Hosted parent/hook observations and final
all-files execution remain required; caller wiring and mock regressions do not
supply those results.

### Reviewed detect-secrets baseline additions

Security review classified exactly eleven cumulative scanner findings: nine
public integrity-hash occurrences and two synthetic negative-test fixtures.
The existing pinned command `detect-secrets scan --baseline .secrets.baseline`
authored the exact path/type/fingerprint tuples below in two separately admitted
runs, each exit 0: 367 to 376 records (nine additions), then 376 to 378 (two
additions in the finite CI-step expectation). Both increments removed zero
records and preserved prior fields apart from ordinary line-number relocation.
Plugin/filter configuration is unchanged. Failing hooks and every before/after
baseline are retained.
This bounded false-positive handling accepts no real credential and grants no
vulnerability exception; source literals remain visible without new pragmas or
obfuscation.

| Source occurrence | Detector type | Native `hashed_secret` fingerprint | Nonsecret evidence |
| --- | --- | --- | --- |
| `scripts/ci/audit_fastembed_compat.py:40` | Hex High Entropy String | `e3b8047b507f8be27ec8b8dabb28832ce539b6fd` | Official upstream wheel SHA-256 `40bee672657574a1009e35ec50030a55f2b426842cb011845379817641bbbbd0`; 116572 bytes verified. |
| `scripts/ci/audit_fastembed_compat.py:41` | Hex High Entropy String | `d2115b8456dff51f0fac9d9ee678aa6af9a8c4a4` | Reproducible published wheel SHA-256 `3dd7642eb4d7ceecf208df4c9e290b08f14f28007b056ff81488810b9a366a45`; 116726 bytes verified. |
| `scripts/ci/audit_fastembed_compat.py:42` | Hex High Entropy String | `5ac05aeed9526377ba065a10ab4ac25e6ff58a9a` | Tracked recipe SHA-256 `d8c1f34ee1097236614913442b51156926d1bb6c15f854d429f95d72c94c8d41`; 1035 bytes verified. |
| `scripts/ci/fastembed_compat_build.json:4` | Hex High Entropy String | `e3b8047b507f8be27ec8b8dabb28832ce539b6fd` | Same verified upstream wheel SHA-256, stored as the recipe input digest. |
| `tests/test_ci_workflow_pr_size_governance_contract.py:6535` | Hex High Entropy String | `02e6795dbb3ddbeafcb6b3d94a5704f6030592ca` | Same verified official pip26.2.2 wheel SHA-256 and 1819850-byte artifact, repeated in the exact CI-step expectation. |
| `tests/test_ci_workflow_pr_size_governance_contract.py:6557` | Hex High Entropy String | `5dea9dea65238a640165a7ceb3990edee64837d0` | Same verified 238856-byte fixed CA payload SHA-256, repeated in the exact CI-step expectation. |
| `tests/test_fastembed_compat_wheel.py:129` | Hex High Entropy String | `e3b8047b507f8be27ec8b8dabb28832ce539b6fd` | Assertion of that same public upstream wheel SHA-256. |
| `tests/test_python_dependency_surfaces.py:1414` | Basic Auth Credentials | `789cbe0407840b1c2041cb33452ff60f19bf58cc` | Synthetic credentials on reserved `packages.example.test` exercise diagnostic redaction; no account credential. |
| `tests/test_python_supply_chain_controls.py:672` | Hex High Entropy String | `02e6795dbb3ddbeafcb6b3d94a5704f6030592ca` | Official pip wheel SHA-256 `fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70`; 1819850 bytes verified. |
| `tests/test_python_supply_chain_controls.py:736` | Hex High Entropy String | `5dea9dea65238a640165a7ceb3990edee64837d0` | Embedded CA content SHA-256 `50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`; 238856 bytes verified. |
| `tests/test_python_supply_chain_controls.py:2607` | Secret Keyword | `572662ff4bbac5d8fbe3fd244a4b0d7c44f517fa` | Synthetic `TWINE_PASSWORD` canary exercises child-environment isolation and must not be forwarded. |

Earlier reviewed baseline SHA-256 (before later native line-number refreshes):
`18414c32780f253e4f606276893fb9399d58f28235e83fb61a4df85f614e7aa0`.
The first native exact-set admission receipt SHA-256 is
`edb644ba5df7ec9d0b0612e4d46176fff88199e0052f285b6c0b2f0d2f7d704e`;
the second is
`4b332e011fabde8dba0b4fdb8a44097b8b88b54899fa1f7ec4d5195205089279`.
The final all-files gate must still pass after this factual documentation update.

## Validation, remaining evidence and rollback

Focused builder results: `38 passed in 2.10s`, exit 0; Ruff, Black check and
focused mypy passed. An optional isort invocation failed with
`No module named isort`; the shared environment was not changed.
Focused source/pip/selector results: `57 passed in 3.84s`, exit 0;
Black/Ruff/diff checks passed. These results precede final dependency
compilation. Raw scripts, terminal logs, result JSON, model bindings and output
files remain in the owned gitignored stabilization evidence directory.

Publication and closeout require the final material's complete local narrow bundle including
`make validate-changed` and terminal all-files hooks, premortem/Runner,
post-open roles, current-head CI/security/coverage, exact-material self-review,
provider-neutral seal, dispositions, strict wrapper and wait window before the
already conditionally authorized merge. The generation/replay, full classified delta, working-material
carrier postconditions, exact ten-lock audit and native final-profile checks
above retain their bounded component meaning; later input changes require
corresponding revalidation. Consult the canonical PR/mapping and exact-material
receipts for current gate outcomes; missing evidence stays unproven. Native profile
success does not establish final-image, hosted workflow or merge readiness.

The October 24 AM04 decision transfers only the necessary retained Alertmanager
receiver and P01 package-inventory/publication-order code from exact #2494
source into #2497. The original producer identity and other owners remain
unchanged. Actual AM publication still requires its separately authorized manual
main dispatch; current native checks, immutable pullback and downstream CD are
independent outcomes. Code adoption/merge cannot establish a working ordinary
published base while its positive publication predecessor is absent. The AM
owner is `docs/security/CVE-2026-84445-alertmanager.md`. Rollback uses a normal
reviewed revert; restoring vulnerable pins reintroduces known findings and
requires explicit decision. No automatic downgrade, history rewrite, merge or
production action follows from this document.


## Exact nine-site Bandit decision AM05

On October 24 the human owner explicitly accepted only nine existing annotations
from the reviewed finite report SHA-256
`12c7f2674a8b83bd0a73c67dc49c7fb7fbca70b612c3be6698831ffd1a33ed2e`:
four B404 imports, four B603 fixed subprocess calls and one B105 synthetic
configuration value. This is a separate residual-risk decision from the seven
Python dependency remediations and the four-CVE AM replacement. It adds no
application-dependency CVE exception, scanner setting or static allowlist.

| Existing source | Cases | Retained boundary |
| --- | --- | --- |
| `scripts/ops/notify_premium_alias_checkpoint_failure.py:11` | B404, B603 | Fixed canonical manifest reader, minimal environment, ten-second timeout, validated output, no Compose send after failure |
| `scripts/verify_premium_alias_telemetry.py:16` | B404, B603 | Same bounded manifest authority before telemetry operations |
| `scripts/ops/ops_context_report.py:11` | B404, B603 | Absolute native Git, fixed argv/cwd/minimal environment, five-second timeout and sanitized commit identity errors |
| `scripts/ci/fetch_docker_source_artifacts.py:8426`, `:10762`, `:10824` | B105, B404, B603 | Synthetic Compose config only; fixed read-only held-FD collector with bounded captures and owned process-group cleanup |

Owner: security-auditor / dev-operator. Mandatory manual reassessment is due
**2026-10-30**. The unchanged calendar-date guard accepts **2026-10-31
inclusive** and rejects **2026-11-01**. The decision permits no automatic renewal
or tenth annotation. Previous assessment dates and original producer hashes
remain historical evidence.

Within the NOSEC-only delta, the complete executable AST is unchanged. Any
approved embedded collector source must also retain its decoded AST; arbitrary
string changes cannot be hidden by an AST comparison. AM04 receiver logic is a
separate executable delta. Current notifier/verifier/AM helper deployment pins
must be recomputed from actual bytes, together with the independently designated
controller. Original Q/S/C10 source/ZIP/OCI/graph/tool/DB hashes are immutable.

Required evidence comprises ordinary and ignore-nosec scans of exactly these
four files, nine expected unsuppressed finding identities and zero parse errors,
the existing expiry/absolute-binary/process/reader/deploy checks and all final
local/current-head gates. Ordinary suppressed output is not a global no-findings
claim. Actual results live in exact-material receipts and the PR; this scope
record does not mark future checks passed.

Remove the annotations when the operation is retired or a reviewed smaller
implementation preserves every process/identity/error boundary. Reassess on any
changed interpreter/helper/binary/argv/environment/timeout/output contract or
new finding/failing control. Rollback reverts the comments and coupled current
pins together and restores the blocking warning/expiry condition; it never
weakens a scanner or authorizes production action. Tracking remains in the
existing checkpoint/OPS and AM ledger entries.

Actual AM11 CA-qualified producer outputs are now selected as receiver data.
Final C/H consumer admission, current-head gates and merged-main outcomes remain. See [AM11 vendor CA source preparation](CVE-2026-111943-go-trust-store.md#am11-vendor-ca-source-preparation)
for the exact vendor delta, Q/S byte binding and remaining native proof.

The actual AM11 build job `121800078082` at producer `a8c9b361` observed pip
26.2.2 and embedded CA SHA-256
`50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785`
before locked-profile installation. Its later native-host snapshot records pip
26.2.2 and ninety packages. This is the isolated build profile, not every
application environment, a second CA-hash observation or a fresh audit.

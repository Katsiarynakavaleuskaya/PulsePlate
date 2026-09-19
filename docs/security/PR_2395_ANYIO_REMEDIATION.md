# PR #2395 Python dependency remediation

This single owner document preserves two separately authorized transitions:
AnyIO first, then the exact HTTPX2/HTTPCore2 scanner batch. The latter batch and
its necessary idna resolver closure have eight matching replay locks and clean
audits across all ten Python profiles. Compatibility checks and the final expanded local bundle passed; current-head
CI and review/merge gates remain pending.
The current path count and owner-approved privileged-scope justification are
recorded in [PR #2395](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2395)
and checked by the existing PR size governance. No merge-readiness claim is made.

## AnyIO transition — retained historical proof

The following AnyIO evidence binds its completed dependency stage at
`d55cc76f1043f32aac718ec77fe7dfa5118b360c`. References to head/current hashes
in this historical section refer to that stage. The later idna closure changes
lock bytes and receives its own table below; it does not rewrite the AnyIO
receipt or turn HTTPX2/HTTPCore2 into AnyIO resolver closure. Earlier pending
audit/scope observations are retained as history and superseded by the explicit
batch admission below where stated.

### Scope and current stage

The operator explicitly authorized fixing the current AnyIO pip-audit blocker
inside [PR #2395](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2395).
This adds one dependency identity to the existing Euler outcome. Main/CD repair,
other dependency upgrades, suppressions and a new prerequisite PR are outside
this authorization. This document owns the dependency transition evidence.

Status: all eight locks were compiled and independently replayed with identical
bytes; the only changed dependency identity is AnyIO. Runtime pip-audit and
35 compatibility cases passed. The owning test bundle exited 0. Separate
dev/test/aggregate audits found four vulnerabilities in two other packages;
their disposition and current-head CI remain pending. No merge-readiness claim.

### D / S — identity and governed surfaces

`D = pypi:anyio`. Dependency base:
`6ed1d6625ef9a38d507426e77ed171159e93609f`; recorded PR base:
`b89e833af752d2b68f8d8b0fa99ab18b59e856e9`. All 21 registered/discovered
requirement carriers, including source inputs and original lock seeds, were
asserted byte-equivalent between these revisions before transition comparison.

The base observation at `2026-09-19T08:45:12.110048+00:00` found exactly one
`anyio==4.12.0` occurrence in each of the eight locks listed in the replay table
below. Complete discovery examined 21 carriers: `S_base` has those eight locks;
`S_head` has the same locks at 4.14.2 plus `requirements.in`. There are no removed
AnyIO surfaces. The other 12 current carriers contain no AnyIO declaration.

The authored head adds the direct floor at `requirements.in:5`.
The live direct-package ownership guard initially rejected the new source with
`.github/dependabot.yml:groups.package-owner.anyio: direct package must match
exactly one group; got []`. The same-identity repair registers `anyio` in the
existing `runtime-web` group at `.github/dependabot.yml:47` and synchronizes
the existing closed pattern registry at
`scripts/ci/check_dependabot_python_policy.py:73`. The YAML-only attempt failed
the exact-pattern guard before this synchronization. These are two additional
material paths in the same-identity scope count; no classifier logic, scheduling
or broader update-policy rule is changed. Flake8 also exposed an unused
`config_path` local in that touched validator; removing the dead assignment
closed F841 without altering validation behavior.
The reconciled surface delta is one direct source occurrence. Profile sources
that consume the runtime constraint acquire no independent authored floor;
data/evals profiles acquire no new dependency. Same-carrier scope contains
22 material paths plus the canonical review mapping (23 total).

### F / A — finite advisory inventory and base applicability

The retained primary GitHub advisory snapshot SHA-256 is
`781d3116f329a1f0484054d810467ad6594ad49db541c0cab35028bad8e17895`,
recorded with the observation cutoff above. `F_cutoff` contains all three
candidates below; `A` contains the two candidates with affected base witnesses.

| Advisory | Reconciled affected range | Base 4.12.0 | Head obligation |
| --- | --- | --- | --- |
| [GHSA-82r6-8w77-94w6 / CVE-2026-63374](https://github.com/agronholm/anyio/security/advisories/GHSA-82r6-8w77-94w6), TLS hostname encoding | `<4.14.2` | Affected in all eight locks; member of A | Every occurrence outside range |
| [GHSA-5p39-cfhj-2xmp / CVE-2026-64847](https://github.com/agronholm/anyio/security/advisories/GHSA-5p39-cfhj-2xmp), undrained process-pool stderr | `<4.14.2` | Affected in all eight locks; member of A | Every occurrence outside range |
| [GHSA-3w57-8xmc-8v26 / CVE-2026-63349](https://github.com/agronholm/anyio/security/advisories/GHSA-3w57-8xmc-8v26), POSIX extra_groups | `>=4.14.0,<4.14.2` | Not applicable: 4.12.0 predates the affected range | Retained in universal head check |

The extra_groups vendor description identifies version 4.14.0; the reviewed
[GitHub advisory range](https://github.com/advisories/GHSA-3w57-8xmc-8v26)
includes 4.14.0 through versions below 4.14.2. The conservative union is
`>=4.14.0,<4.14.2`; this difference does not make base 4.12.0 affected.
All three records name 4.14.2 as first patched. Safety here means outside this
finite reconciled inventory, not absence of all possible vulnerabilities.

### R — one authored action and deterministic resolver closure

`I_R` is the single replacement action `anyio>=4.14.2,<5.0.0` in
`requirements.in`. `C_R` contains only transitions reproduced by the canonical
compiler from identical base inputs and original seeds. The selected resolver
upgrade is `UPGRADE_PACKAGES="anyio==4.14.2"`; this parameter is not a second
identity or action class.

The owning entrypoint is `make requirements-locks` (`Makefile:93`), using the
approved private proxy, Python 3.13.14 and pip-tools 7.6.0. The commands use
`$VENV_PYTHON`, resolved to the approved repository interpreter; its full host
path is retained only in the local validation-command artifact.
Runtime compiled first and was committed as
`fa6507c3b758a34021d45c58348c98ee56509618` before dependent profiles consumed it,
as required by `scripts/ci/compile_locked_python_requirements.py:2019`.

With that interpreter selected, the profile commands were:

```bash
LOCK_PROFILES="runtime" UPGRADE_PACKAGES="anyio==4.14.2" make requirements-locks
LOCK_PROFILES="docker-runtime ci-lite test dev rag-vector rag-vector-cpu aggregate" UPGRADE_PACKAGES="anyio==4.14.2" make requirements-locks
```

Both compilation phases and their independent replays exited 0. Raw excerpts:

```text
Updated governed lock profile runtime: requirements.txt
Updated governed lock profile aggregate: requirements-lock.txt
```

Replay used identical original-base inputs/seeds and the same admitted source
action/compiler in an isolated local copy. Every resulting lock matches its
replay byte-for-byte. The complete semantic delta contains only the source
floor addition and these eight AnyIO version changes; no other package was
added, removed or changed. Thus the source action is `I_R`, each generated lock
transition is replay-proven `C_R`, and there is no unclassified transition.
No graph-admission override or registry fallback was used.

| Lock | Only package-version delta | Head and replay SHA-256 |
| --- | --- | --- |
| `requirements-ci-lite.txt` | `4.12.0 -> 4.14.2` | `0eff94f871e5a54475312a2c8c72f7f6df505591984b9ab709b6c820568b1c1b` |
| `requirements-dev.txt` | `4.12.0 -> 4.14.2` | `42a07bed8942c76f5c25f900a33563275a095919d93e8fd2db2155cdc3c67bd3` |
| `requirements-docker-runtime.txt` | `4.12.0 -> 4.14.2` | `8db6d4a061d0021865585acafc001daa45a52501c5eaf07c85c80aa58204f32c` |
| `requirements-lock.txt` | `4.12.0 -> 4.14.2` | `2a92f48bfef2ee6330c9bab10fe2d1c5f9bf026cd7b2f1c4f39a2b037db8ab42` |
| `requirements-rag-vector-cpu.txt` | `4.12.0 -> 4.14.2` | `14cb12be17be11e5133dac624c475c0c699244ffd1991a1ab58911ca3de4cdcb` |
| `requirements-rag-vector.txt` | `4.12.0 -> 4.14.2` | `d899c60a77430f4653aa5bc6b83b249255d5945840b3ef4c5584f95be90959af` |
| `requirements-test.txt` | `4.12.0 -> 4.14.2` | `f195521fd6fb7656271d88f24b2c20b9b4e8fd69afa131d694147a5230fd5146` |
| `requirements.txt` | `4.12.0 -> 4.14.2` | `9b8c7ac3e2d6d2f833ca2b8bf688cfcf3fc01eedd5b5af31c3455608e3e6dc8c` |

The local transition verifier command, run from the owning worktree, was:

```bash
PYTHONPATH="$PWD" "$VENV_PYTHON" artifacts/orchestration/euler-ops2/verify-anyio-transition.py
```

Exit 0; raw output (`anyio-transition-verification.log`):

```text
21 carriers examined; S_base=8; S_head=9; eight byte-identical replays; zero non-AnyIO transitions; head clears all three advisories
```

`anyio-transition-proof.json` retains the complete carrier inventory, per-file
semantic delta and replay hashes; `anyio-base-evidence.json` retains original
lock hashes. These local records are gitignored evidence, not new instruction
or dependency authority. This checked-in document records their result.

### P — permanent current-head postcondition

The existing dependency schema blocks `anyio<4.14.2` and the owning guard uses
the canonical registry/discovery plus existing requirement parsing. It checks
current registered manifests and locks, requires AnyIO in the eight current
consuming locks and its source, and checks every additional discovered AnyIO
occurrence. Duplicate, missing required, malformed, URL, extras, conditional,
uncomparable and affected carriers fail. Safe later pins remain allowed.
The wider `<4.14.2` block covers the union of all three candidate ranges.
An explicit ordered-version floor comparison also rejects `4.14.2rc1` and
`4.14.2.dev1`: PEP 440 exclusive ranges alone exclude these prereleases from
the blocked set even with prerelease matching enabled. Both regression cases
reproduced acceptance before the fix; all 22 isolated AnyIO cases then passed,
including acceptance of a later stable `4.15.0` pin.

This permanent check carries no historical base, resolver or immutable
admission snapshot. The transition proof remains in this document.

### Validation and rollback

The isolated AnyIO guard command was:

```bash
"$VENV_PYTHON" -m pytest -q tests/test_dependency_security_guard.py -k 'anyio and not current_governed'
```

Exit 0, 22 cases; raw output:

```text
......................                                                   [100%]
```

The full owning test command was:

```bash
"$VENV_PYTHON" -m pytest -q tests/test_dependency_security_guard.py tests/test_check_dependabot_python_policy.py tests/test_python_dependency_surfaces.py
```

It exited 0: 601 collected cases,
586 passed and 15 existing intentional skips, recorded in
`anyio-owning-full.log`. No skip was added by this remediation. Final raw
progress line:

```text
.........................                                                [100%]
```

The compatibility command was:

```bash
PYTHONPATH="$PWD/artifacts/orchestration/euler-ops2-smoke:$PWD" "$VENV_PYTHON" -m pytest -q tests/test_health_db.py tests/test_rate_limit_client_key_api.py
```

Compatibility smoke used an isolated AnyIO 4.14.2 installation with the shared
approved interpreter. `anyio-smoke-version.log` proves the loaded module was
under the owning worktree's `artifacts/orchestration/euler-ops2-smoke/anyio/`
and reported `4.14.2`; the primary environment was not mutated. The focused
`tests/test_health_db.py` and `tests/test_rate_limit_client_key_api.py` bundle
passed 35 cases, exit 0. Raw output (`anyio-compatibility-smoke-retry.log`):

```text
...................................                                      [100%]
```

Each lock was audited independently using the same arguments, with its own
input/output path. The exact dev-profile command was:

```bash
"$VENV_PYTHON" -m pip_audit -r requirements-dev.txt --no-deps --disable-pip -f json -o artifacts/orchestration/euler-ops2/audit-requirements-dev.txt.json
```

Audit results are per lock. The runtime, Docker-runtime, CI-lite, RAG-vector and
RAG-vector-CPU profiles exited 0. Their raw audit result was:

```text
No known vulnerabilities found
```

Dev, test and aggregate profiles exited 1, each reporting:

```text
Found 4 known vulnerabilities in 2 packages
```

These remaining findings are `httpcore2==2.3.0` (`PYSEC-2026-3844`) and
`httpx2==2.3.0` (`PYSEC-2026-3849`, `PYSEC-2026-3848`, `PYSEC-2026-3846`).
`httpx2` is declared by dev/test sources; `httpcore2` is its transitive dependency
(`requirements-dev.txt:82`, `requirements-test.txt:25`,
`requirements-lock.txt:154`). They were not changed by the AnyIO action.
At this historical stage, their disposition awaited coordinator scope/authority
review; the explicit owner approval in the batch section below supersedes that
admission hold. This historical audit does not claim all profiles were clean.

The initial attempt to combine all locks into one audit was an invalid tool
invocation: independently owned profiles carry distinct Chardet pins, and the
auditor rejected duplicate requirements. It supplied no vulnerability result.
The separate profile runs above replaced that failed invocation; its raw log
is retained as `anyio-all-lock-audit.log`.

AnyIO clears the reconciled three-advisory inventory across all eight locks.
The retained per-profile audit summary is separate from the full local narrow
bundle, current-head CI and final material review. Current-head CI and
remaining review/readiness gates are pending.

A reviewed rollback must preserve the security block: an affected old AnyIO pin
cannot be restored as a passing release state. No advisory suppression or
bypass is authorized. Any compatibility failure requires a supported safe
replacement and a new verified resolver result in this same governed process.

## Scanner batch — HTTPX2 and HTTPCore2

### External authority and exact identity set

The owner explicitly approved both dependencies inside PR #2395 on 2026-09-19
in response to the complete ten-profile scanner snapshot SHA-256
`9bc543ee97f7db8bec7fed13bfe685962fdd9e93980dfc0ca8d4ce1abf40464d`.
The all-and-only authored identity set is `{pypi:httpx2, pypi:httpcore2}`.
This is the existing finite scanner-batch exception, not authority for another
package, ecosystem, suppression, prerequisite PR or main/CD work. The earlier
unresolved audit observation is now admitted for same-carrier remediation;
that admission is not a completion or audit-PASS result.

### D / S / F / A — independently reconciled identities

Batch base is `d55cc76f1043f32aac718ec77fe7dfa5118b360c`, after the AnyIO stage.
The base inventory examined all 21 canonical carriers. HTTPX2 occurs in
`requirements-dev.in`, `requirements-test.in`, `requirements-dev.txt`,
`requirements-test.txt` and `requirements-lock.txt` (five surfaces), with base
floor/pins 2.3.0. HTTPCore2 occurs in the same three locks at 2.3.0; the head
adds explicit floors to the two dev/test sources, for five intended surfaces.
Independent final discovery confirms HTTPX2 `S5 -> S5` and HTTPCore2
`S3 -> S5`, with all and only the source/lock members above. Runtime, Docker,
CI-lite, data/evals and vector profiles acquired neither HTTPX2 nor HTTPCore2.

The immutable primary advisory snapshots are:

- `httpx2-advisories-snapshot.json`: `41a539ffb0fef4b3cf8002241dc63135f425b23df6e6a4e52008c9d479bd0776`.
- `httpcore2-advisories-snapshot.json`: `39c9b7fc2feb929e683078765335bad76b7276d3bed7135f150ad42b973f961e`.

| Identity | Candidate advisory | Affected range | Base 2.3.0 disposition |
| --- | --- | --- | --- |
| `httpx2` | [GHSA-8xx6-hgc6-gc2m](https://github.com/advisories/GHSA-8xx6-hgc6-gc2m) / CVE-2026-84382 | `< 2.12.0` | Affected: member of A |
| `httpx2` | [GHSA-pf96-p4fj-6566](https://github.com/advisories/GHSA-pf96-p4fj-6566) / CVE-2026-84380 | `< 2.11.0` | Affected: member of A |
| `httpx2` | [GHSA-h4x7-gw46-3wm6](https://github.com/advisories/GHSA-h4x7-gw46-3wm6) / CVE-2026-84379 | `< 2.11.0` | Affected: member of A |
| `httpx2` | [GHSA-f2fp-rgf2-35cp](https://github.com/advisories/GHSA-f2fp-rgf2-35cp) / CVE-2026-84378 | `>= 2.5.0, < 2.10.0` | Not applicable: 2.3.0 predates range; retained in P |
| `httpx2` | [GHSA-7mj9-2mp8-4m2p](https://github.com/advisories/GHSA-7mj9-2mp8-4m2p) / CVE-2026-84381 | `>= 2.6.0, < 2.10.0` | Not applicable: 2.3.0 predates range; retained in P |
| `httpcore2` | [GHSA-7mj9-2mp8-4m2p](https://github.com/advisories/GHSA-7mj9-2mp8-4m2p) / CVE-2026-84381 | `< 2.10.0` | Affected: member of A |

HTTPX2's `A` contains three advisories; its two newer-feature advisories remain
non-applicable at base but mandatory in the universal head safety condition.
HTTPCore2's `A` contains the TLS advisory. The shared GHSA has distinct ranges
for the two packages; a non-applicable HTTPX2 range does not excuse the affected
HTTPCore2 occurrence. Batch P requires the conjunction of both complete
per-identity postconditions, with no omitted candidate or surface.

### R — two authored actions and necessary idna closure

Each admitted identity has one explicit replacement action: declare
`>=2.12.0,<3.0.0` in both existing dev/test sources. HTTPCore2's direct owner is
registered in the existing `test-quality` Dependabot group and canonical
pattern registry; no scheduling or classifier logic changes are made.

The selected HTTPX2 2.12.0 wheel metadata requires `httpcore2==2.12.0` and
`idna>=3.18`. The batch-base runtime constraint pinned idna 3.15, so leaving
idna unchanged could not satisfy the admitted pair. The independently replayed
idna 3.18 move is proven `C_R`, not a third authored remediation identity or
source floor.
Truststore 0.10.4 is already present in the three consumer locks. The metadata
proof and exact canonical replay must justify every resulting transition;
no broader upgrade set is inferred.

Runtime idna was compiled/committed first at
`6017aa5465e49603098ca9c8001c51d7f8a36ba4`, then the seven dependent locks were
compiled using B_batch original seeds. The exact canonical commands were:

```bash
LOCK_PROFILES=runtime UPGRADE_PACKAGES=idna==3.18 make requirements-locks
LOCK_PROFILES="dev test aggregate" UPGRADE_PACKAGES="httpx2==2.12.0 httpcore2==2.12.0 idna==3.18" make requirements-locks
LOCK_PROFILES="docker-runtime ci-lite rag-vector rag-vector-cpu" UPGRADE_PACKAGES=idna==3.18 make requirements-locks
```

All three compilation groups and their independent replays exited 0, using
`$VENV_PYTHON` resolved to the approved repository interpreter, Python 3.13.14,
pip-tools 7.6.0 and the canonical private proxy. Replay used byte-equivalent
base-governed tooling and original seeds, the same two source actions and the
same runtime-first sequence. Final four-profile compile/replay raw excerpts:

```text
Updated governed lock profile docker-runtime: requirements-docker-runtime.txt
Updated governed lock profile rag-vector-cpu: requirements-rag-vector-cpu.txt
```

Every lock below matches its independent replay byte-for-byte. Here **pair**
means both authored `httpx2` and `httpcore2` replacements `2.3.0 -> 2.12.0`
(`I_R`); **idna** means the metadata-required `3.15 -> 3.18` closure (`C_R`).
The only source changes are the two identities' dev/test floors. The complete
21-carrier semantic comparison found zero other or unclassified transitions.
No manual lock edit, registry fallback or graph-admission bypass was used.

| Final lock | Complete package-version delta | Head and replay SHA-256 |
| --- | --- | --- |
| `requirements-ci-lite.txt` | idna only | `ad5c1421e6c9f6aaaa23534d7f1b7d719b6d3878247f523362dc9203437d3505` |
| `requirements-dev.txt` | pair + idna | `28ba07dbd5a5efb6a037dfbc4f5aa40d2bce405ac0d3e709dec66e66fdce07f1` |
| `requirements-docker-runtime.txt` | idna only | `23b730831c4dfad8a8d7b2eec8fe38c610a51fae5bcea321f5c25d5848ee13b4` |
| `requirements-lock.txt` | pair + idna | `19c24064c634169bd9db10c4ee3c77d01cf32afce0a8bf44c22a55fdd890bd06` |
| `requirements-rag-vector-cpu.txt` | idna only | `c0e62496c6a33a234412d06e6cb9c321d7e72f92ac12957cd0cb7bd28f06edf8` |
| `requirements-rag-vector.txt` | idna only | `96d8b54a12bd5b5e603bdad1b7d9b59e6312041eb8f088e1a975bc8b5ab41ff5` |
| `requirements-test.txt` | pair + idna | `8f463b624999802c8f61a85e11ccc1c19b4581a5d0dbe7a89d9dbb313938d195` |
| `requirements.txt` | idna only | `cafe8d1cadaa49b066acf1f6a25b13316c55fa2a91fdf035a537a2c3d364a197` |

The independent transition check was:

```bash
PYTHONPATH="$PWD" "$VENV_PYTHON" artifacts/orchestration/euler-ops2/verify-http-transition.py
```

Exit 0; raw output from `http-transition-verification.log`:

```text
21 carriers; HTTPX2 S5->5, HTTPCore2 S3->5; eight identical replay locks; only admitted pair plus metadata-required idna closure
```

`http-transition-proof.json` retains the complete semantic partition and
surface inventory. `http-batch-base-evidence.json` retains all original input
hashes and target metadata. These local records preserve evidence without
becoming another dependency registry or authorizing further upgrades.

### P — current-head guard and acceptance stage

The existing parser/helper is parameterized for the finite admitted identities.
HTTPX2/HTTPCore2 must occur exactly once in each intended source/lock and be
absent outside those owners. Fixed-floor comparison rejects pre-fixed rc/dev
versions as well as affected stable versions. Current registry/discovery and
required-profile/source checks retain missing-inventory rejection.

Both packages use the conservative policy floor 2.12.0: HTTPX2 needs it for its
latest candidate advisory; HTTPCore2's advisory alone is fixed at 2.10.0, but
HTTPX2's exact metadata requirement selects the tested 2.12.0 pair. This is a
compatibility/security floor, not a claim that all HTTPCore2 versions below
2.12.0 share the same advisory. A separate exact-pin compatibility check requires
idna >=3.18 in all eight runtime-constrained locks without adding an idna
remediation identity to the schema.

### Observed batch validation and remaining delivery gates

The isolated parameterized guard bundle passed 40 cases, exit 0:

```bash
"$VENV_PYTHON" -m pytest -q tests/test_dependency_security_guard.py -k '(anyio or http_client) and not current_governed and not runtime_constraints'
```

```text
........................................                                 [100%]
```

Native compatibility used the isolated new package set, confirmed in
`http-smoke-version.log`: HTTPX2 2.12.0, HTTPCore2 2.12.0, idna 3.18 and AnyIO
4.14.2. Both commands below exited 0, with 35 and one passed cases respectively:

```bash
PYTHONPATH="$PWD/artifacts/orchestration/euler-ops2-smoke:$PWD" "$VENV_PYTHON" -m pytest -q tests/test_health_db.py tests/test_rate_limit_client_key_api.py
PYTHONPATH="$PWD/artifacts/orchestration/euler-ops2-smoke:$PWD" "$VENV_PYTHON" -m pytest -q tests/compat/test_starlette_httpx2_testclient_compat.py
```

```text
...................................                                      [100%]
.                                                                        [100%]
```

All ten Python profiles have clean per-profile audit results. The eight changed
locks were individually re-audited with exit 0; unchanged data/evals locks retain
their earlier exit-0 audits because their bytes are unchanged. The exact
final dev-profile command was:

```bash
"$VENV_PYTHON" -m pip_audit -r requirements-dev.txt --no-deps --disable-pip -f json -o artifacts/orchestration/euler-ops2/http-final-audit-requirements-dev.txt.json
```

The same arguments were used independently for each changed lock/output.
`http-final-dev-audit-summary.json` covers dev/test/aggregate and
`http-final-runtime-audit-summary.json` covers the other five changed locks.
Each raw result reports:

```text
No known vulnerabilities found
```

These results supersede the four historical HTTPX2/HTTPCore2 audit findings in
the AnyIO section. Both per-identity universal head postconditions hold for the
full candidate inventories, including the two HTTPX2 base-nonapplicable
candidates. No alert was suppressed or dismissed to obtain this result.

The local index-docs guard also passed all 63 owning cases under `PRE_COMMIT=1`;
its separate Git-index repair preserves ordinary/CI committed-HEAD checks.
The expanded final local command exited 0: 775 passed and 15 existing skips
(790 collected), with no new skip introduced:

```bash
"$VENV_PYTHON" -m pytest -q tests/test_dependency_security_guard.py tests/test_check_dependabot_python_policy.py tests/test_python_dependency_surfaces.py tests/test_render_codex_start_prompt.py tests/test_start_pr_lane.py tests/guards/test_security_devtooling_regression_guards.py
```

Final raw progress line from `final-expanded-focused.log`:

```text
......................................................................   [100%]
```
Current-head CI, final material review, same-ID external closeout and explicit
merge authority remain pending. Earlier AnyIO results are not substituted for
this batch's new evidence. Reviewed rollback must not restore affected pins as
a passing state or bypass security controls.

# PR #2395 AnyIO dependency remediation

## Scope and current stage

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

## D / S — identity and governed surfaces

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

## F / A — finite advisory inventory and base applicability

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

## R — one authored action and deterministic resolver closure

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

## P — permanent current-head postcondition

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

## Validation and rollback

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
Their disposition is pending coordinator scope/authority review; this document
does not classify them as deferred or claim all profiles are clean.

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

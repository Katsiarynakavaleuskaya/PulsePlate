# PR #2455: finite virtualenv dependency remediation evidence

## Summary

This is the single evidence owner for `pip:virtualenv` in the operator-admitted
PR #2455 expansion. The authored replacement is virtualenv21.14.5 through the
owning sources and canonical Make compiler. The finite source reconciliation
contains F10 advisories, A7 base-applicable advisories and three independently
base-inapplicable candidates. All ten remain in the head postcondition.

Observed local results: canonical Make and independent original-base replay
both exited0, with three byte-identical complete locks and all other dependency
pins/metadata unchanged. The complete current21-carrier census has five
virtualenv occurrences, each outside every F10 range. An isolated owned canonical
venv sync and pip-check exited0. Actual stock pre-commit created eleven cold
Python environments and eleven fresh environments using the warmed app-data;
selected embedded/cached pip26.2.1 bytes match the recorded verified wheel.

These are bounded local results for the recorded uncommitted material and
configuration. Final material gates, current-head CI, review/closeout, strict
readiness, protected exact-head merge and post-delivery outcomes remain pending.
No overall-ready, provider/scan/no-findings, downloaded-seed verification,
compromise, general cache integrity or future-advisory claim is made.

## Current truth and external instruction boundary

D is exactly the ecosystem-qualified identity `pip:virtualenv`. The direct human
same-PR instructions, "в рамках этого пиара" and "Расширить скол, я имею в виду.",
selected #2455 as the carrier. The preserved criteria amendment, packet
`356d2576f243` and completed Coordinator/Logic/Philosophy/Security/Architecture
preparation retain that external instruction. Candidate code, this document,
scanners, labels, records and role outputs cannot authenticate or enlarge it.
The existing root D/S/F_cutoff/A/I_R/C_R/P contract remains unchanged, with one
identity and one authored action; no application batch or policy transition.

The latest conditional human #2455 merge direction is separately bound by the
parent to actual strict readiness and the exact head. It is not supplied by
this evidence document. All original24 criteria, 33 requirements, 18 proposals,
C25/C26/C27 and C28 remain retained. Completed ORCH/PG roles and their qualified
local proof remain separate; C28 Cloud/environment proof is still unknown.

## S: complete independently enumerated base and head carriers

The exact original base is
`16874a7c4d991673f849e17d45e3e3da51dd5e59`. The pre-action f7 material had
identical carrier bytes. Existing registered and Git-index-discovered inventories
independently agree on the complete21-carrier universe at base and current head.
Their union is21, nonempty. All surface deltas are exactly the two owning .in
sources and three compiled locks below. No base-only or unreconciled carrier.
The full before/after per-carrier byte hashes are retained in the hashed census
and head-P receipts in the evidence inventory.

| Carrier | Base virtualenv | Current occurrence | Byte relation |
| --- | --- | --- | --- |
| constraints.txt | absent | absent | unchanged |
| requirements-all.txt | absent | absent | unchanged |
| requirements-ci-lite.in | absent | virtualenv>=21.14.5 | changed |
| requirements-ci-lite.txt | 21.2.0 | virtualenv==21.14.5 | changed |
| requirements-data.in | absent | absent | unchanged |
| requirements-data.txt | absent | absent | unchanged |
| requirements-dev.in | absent | virtualenv>=21.14.5 | changed |
| requirements-dev.txt | 20.36.1 | virtualenv==21.14.5 | changed |
| requirements-docker-runtime.in | absent | absent | unchanged |
| requirements-docker-runtime.txt | absent | absent | unchanged |
| requirements-evals.in | absent | absent | unchanged |
| requirements-evals.txt | absent | absent | unchanged |
| requirements-lock.txt | 21.4.2 | virtualenv==21.14.5 | changed |
| requirements-rag-vector-cpu.in | absent | absent | unchanged |
| requirements-rag-vector-cpu.txt | absent | absent | unchanged |
| requirements-rag-vector.in | absent | absent | unchanged |
| requirements-rag-vector.txt | absent | absent | unchanged |
| requirements-test.in | absent | absent | unchanged |
| requirements-test.txt | absent | absent | unchanged |
| requirements.in | absent | absent | unchanged |
| requirements.txt | absent | absent | unchanged |

The two authored sources add the same security comment and
`virtualenv>=21.14.5` immediately after pre-commit~=4.6.1. Their complete current
SHA256 values are
`06968656ca62789f78899d952233afe71070bcf8291fc2eaaa8d3419d8c4a80c` and
`66f96297c792deacf29201ee6a39931dd22d1211ab827239e13cfbbb22acddd3`.
They consume requirements.txt; aggregate additionally consumes requirements.in.
constraints.txt was independently censused and unchanged; it is not a consumed
input of these three compile plans. Virtualenv is tooling-owned; this change
adds no runtime/Docker virtualenv presence requirement.

## F_cutoff and A: finite primary-source reconciliation

The immutable snapshot is the exact saved vendor8/GitHub Advisory Database7
source pair, with complete union F10, no withdrawn member, and reconciliation
SHA256 `a391fbb14b0c25b25aeba29d9a8590c668ab1ec3a884694bc9f1fb69479a500b`.
Vendor input SHA256:
`8bfceb94b324ebf7dd7cf51b4d776c13cf8bc80466aad4fad093a208bf054d64`.
GAD input SHA256:
`1886058aae626ec27940a250eee02ca50a40dbc6d9f6e06d263375b5b8e53608`.
Named-source publication/update times and full conflicting prose remain in those
raw inputs. This snapshot does not claim a newer or future advisory inventory.

| Advisory / primary source | Reconciled affected range | Structured patched version | Base applicability | Head21.14.5 |
| --- | --- | --- | --- | --- |
| [GHSA-3jhc-wjqf-5f2c](https://github.com/advisories/GHSA-3jhc-wjqf-5f2c) | <1.5 | 1.5 | none; retained disposition | outside every range |
| [GHSA-597g-3phw-6986](https://github.com/pypa/virtualenv/security/advisories/GHSA-597g-3phw-6986) | <20.36.1 | 20.36.1 | none; retained disposition | outside every range |
| [GHSA-5vjq-rrrf-7h2q](https://github.com/pypa/virtualenv/security/advisories/GHSA-5vjq-rrrf-7h2q) | <=21.14.3 | 21.14.4 | all three base locks affected | outside every range |
| [GHSA-8rjx-v5ww-45pp](https://github.com/pypa/virtualenv/security/advisories/GHSA-8rjx-v5ww-45pp) | <=21.14.1,>=20.26.6 | 21.14.2 | all three base locks affected | outside every range |
| [GHSA-94p9-xgh2-xp45](https://github.com/pypa/virtualenv/security/advisories/GHSA-94p9-xgh2-xp45) | <=21.7.11 | 21.7.12 | all three base locks affected | outside every range |
| [GHSA-9h9j-4vrj-gf7g](https://github.com/pypa/virtualenv/security/advisories/GHSA-9h9j-4vrj-gf7g) | <=21.7.10 | 21.7.11 | all three base locks affected | outside every range |
| [GHSA-c947-3pg5-gm8q](https://github.com/pypa/virtualenv/security/advisories/GHSA-c947-3pg5-gm8q) | <=21.14.1 | 21.14.2 | all three base locks affected | outside every range |
| [GHSA-p58f-9548-mpm2](https://github.com/pypa/virtualenv/security/advisories/GHSA-p58f-9548-mpm2) | <=21.7.12 | 21.7.13 | all three base locks affected | outside every range |
| [GHSA-rqc4-2hc7-8c8v](https://github.com/advisories/GHSA-rqc4-2hc7-8c8v) | <20.26.6 | 20.26.6 | none; retained disposition | outside every range |
| [GHSA-x78j-v8h9-3j2q](https://github.com/pypa/virtualenv/security/advisories/GHSA-x78j-v8h9-3j2q) | <=21.7.11 | 21.7.12 | all three base locks affected | outside every range |

Every A7 row has affected comparable witnesses in all three original locks:
ci-lite21.2.0, dev20.36.1 and aggregate21.4.2. Each is remedied by the same authored
whole-identity replacement. The three candidates outside A remain inside P;
none is removed from the universal head check.

### GHSA-597g source conflict and individual non-applicability

Vendor and GAD structured ranges say <20.36.1, patched20.36.1; the retained
vendor description instead says through20.36.1 and fixed20.36.2. This disagreement
is preserved. The exact official20.36.1 wheel, SHA256
`575a8d6b124ef88f6f51d56d656132389f961062a9177016a50e4f507bbcc19f`,
contains the two PR3013 source corrections, including atomic directory creation
in app_data and lock-parent paths. Official20.36.1 release history records
[PR3013](https://github.com/pypa/virtualenv/pull/3013). The narrow source
reconciliation supports the structured boundary and the base-inapplicable
assessment for dev20.36.1; the other two base versions are higher. It does not
establish general filesystem or cache safety.

GHSA-rqc4 (<20.26.6) and GHSA-3jhc (<1.5) each have all three comparable base
occurrences above their affected ranges. These individually evidenced
non-applicability decisions do not exempt any head occurrence. The earlier
21.7.13 target would still be affected by the newer <=21.14.1 and <=21.14.3
members, so the old alert-only subset was insufficient.

## R: sole authored action and exact deterministic closure

I_R is virtualenv==21.14.5. The compiler's selected fixed alternative is
`virtualenv-2455-21.14.5`, ordered ci-lite/dev/aggregate, with only
python-discovery graph selection. The existing admission's fixed virtualenv_2455
slot binds exact original seeds, prospective source bytes, two artifact and
METADATA proposals, and each profile's before/after relation. Original
observability and default rejection remain disjoint. There is no discovery
source pin, second authored upgrade, raw resolver, manual lock/seed or reusable
future-baseline permission.

The actual canonical invocation for both recorded runs was:

```bash
LOCK_PROFILES="ci-lite dev aggregate" UPGRADE_PACKAGES="virtualenv==21.14.5" GRAPH_CHANGE_PACKAGES="python-discovery" GRAPH_CHANGE_ADMISSION="virtualenv-2455-21.14.5" make requirements-locks
```

Both used the reviewed compiler SHA256
`06d2d173ed5c1cab06295d4ab43f6f75b369fb9df0871c2b6ac4b5815c3edc0f`,
existing admission file SHA256
`ff20a05fd74db4aec1a8310574e8664305abed01b3e3aacbef2a63261861c4d5`,
Python3.13.14, pip26.1.2, pip-tools7.6.0 and packaging25.0. The original compiler
interpreter/environment remained unchanged through both runs. Original16874
seeds were independently materialized in a detached replay checkout, with the
same compiler/admission and same two-source action. Replay did not use generated
candidate seeds. Existing no-config/backtracking/profile-view options and the
approved proxy were retained.

Raw producer stdout for each run:

```text
Updated governed lock profile ci-lite: requirements-ci-lite.txt
Updated governed lock profile dev: requirements-dev.txt
Updated governed lock profile aggregate: requirements-lock.txt
```

Each retained .exit is0. Complete lock bytes, including headers and annotations,
match across both runs:

| Lock | Package count before -> after | Bytes | Current/replay SHA256 |
| --- | --- | ---: | --- |
| requirements-ci-lite.txt |104 ->104 |8863 |12b9638eef1412c283c2ca2b2919c189b1dbefc3ac44f8f73f0219f193cbc9b4 |
| requirements-dev.txt |88 ->89 |5827 |ffd70839ef810ca7eb37bd76041e9f7258910e0f25d61400f570c4d54ff7aea5 |
| requirements-lock.txt |135 ->135 |10970 |e4f239aad39bf5d954adb567ccda4a4f3c37234b6e378d1819e2650fc0b80629 |

The target's verified native METADATA requires python-discovery>=1.6, excluding
both old versions and dev absence. Discovery1.6.1 requires Python>=3.8 and
filelock>=3.15.4; virtualenv requires Python>=3.9. Exact canonical resolution and
independent original-base replay now establish those three discovery transitions
as necessary C_R for this action. Filelock3.24.3/3.24.3/3.29.1 and every other pin,
extra, marker and URL remain unchanged. Each observed transition belongs exactly
once to I_R or C_R; no omitted or unclassified transition.

Complete native JSON dependency delta from the retained producer:

```json
{
  "requirements-ci-lite.txt": {
    "before_sha256": "65aa21256de611ca98069ff713c60edef60006d5db9d5d6d03b64384f53e082f",
    "after_sha256": "12b9638eef1412c283c2ca2b2919c189b1dbefc3ac44f8f73f0219f193cbc9b4",
    "before_package_count": 104,
    "after_package_count": 104,
    "full_transition_inventory": [
      {
        "package": "python-discovery",
        "before": {
          "version": "1.2.1",
          "extras": [],
          "marker": null,
          "url": null
        },
        "after": {
          "version": "1.6.1",
          "extras": [],
          "marker": null,
          "url": null
        },
        "class": "C_R: exactcanonicalnative/originalbase byte replay plus necessary target METADATA"
      },
      {
        "package": "virtualenv",
        "before": {
          "version": "21.2.0",
          "extras": [],
          "marker": null,
          "url": null
        },
        "after": {
          "version": "21.14.5",
          "extras": [],
          "marker": null,
          "url": null
        },
        "class": "I_R"
      }
    ],
    "every_other_pin_and_metadata_unchanged": true
  },
  "requirements-dev.txt": {
    "before_sha256": "3f400a3adeaf63cbac868e35d30ff538ee9d82ccfe3b52296981b91231797952",
    "after_sha256": "ffd70839ef810ca7eb37bd76041e9f7258910e0f25d61400f570c4d54ff7aea5",
    "before_package_count": 88,
    "after_package_count": 89,
    "full_transition_inventory": [
      {
        "package": "python-discovery",
        "before": null,
        "after": {
          "version": "1.6.1",
          "extras": [],
          "marker": null,
          "url": null
        },
        "class": "C_R: exactcanonicalnative/originalbase byte replay plus necessary target METADATA"
      },
      {
        "package": "virtualenv",
        "before": {
          "version": "20.36.1",
          "extras": [],
          "marker": null,
          "url": null
        },
        "after": {
          "version": "21.14.5",
          "extras": [],
          "marker": null,
          "url": null
        },
        "class": "I_R"
      }
    ],
    "every_other_pin_and_metadata_unchanged": true
  },
  "requirements-lock.txt": {
    "before_sha256": "b9d7192fcbc4cb1b283766fe68f4533b684151ac205992b05338aa3ae7d77316",
    "after_sha256": "e4f239aad39bf5d954adb567ccda4a4f3c37234b6e378d1819e2650fc0b80629",
    "before_package_count": 135,
    "after_package_count": 135,
    "full_transition_inventory": [
      {
        "package": "python-discovery",
        "before": {
          "version": "1.4.0",
          "extras": [],
          "marker": null,
          "url": null
        },
        "after": {
          "version": "1.6.1",
          "extras": [],
          "marker": null,
          "url": null
        },
        "class": "C_R: exactcanonicalnative/originalbase byte replay plus necessary target METADATA"
      },
      {
        "package": "virtualenv",
        "before": {
          "version": "21.4.2",
          "extras": [],
          "marker": null,
          "url": null
        },
        "after": {
          "version": "21.14.5",
          "extras": [],
          "marker": null,
          "url": null
        },
        "class": "I_R"
      }
    ],
    "every_other_pin_and_metadata_unchanged": true
  }
}
```

## P: universal current version postcondition and permanent guard

The current uncommitted head universe is complete21. Its only five occurrences
are the two21.14.5 source floors and three21.14.5 locks. All five were compared
to every F10 range, including the three base-inapplicable candidates, with no
unparseable/unresolved occurrence. This establishes the bounded version P for
that local snapshot; it is not committed/published/final-head evidence.

The permanent guard extends the existing native Requirement/Version/SpecifierSet
parser, existing remediated-surface helper, security schema and registry/discovery
consumer. It requires the two tooling sources and three profiles, checks every
optional-present carrier, rejects omitted/malformed/URL/extras/marker/duplicate/
non-comparable state and punctuation aliases such as virtual_env. The safe final
floor21.14.4 closes native exclusive-boundary rc/dev gaps. It accepts safe later
authorized versions, rather than freezing the incident's exact target or base
hash/delta in a permanent test. Full ten advisory range members remain in the
existing blocked_versions data; virtualenv is absent from global min_versions.
This guard's new tests still require the parent's actual execution.

Implementation evidence anchors:
`scripts/ci/compile_locked_python_requirements.py:434` selects the complete
closed alternative; `:1304` enforces the complete candidate delta; `:1957` binds
the exact artifacts. `tests/test_dependency_security_guard.py:2813` owns native
surface validation; `:3471` independently checks the current full universe.
Historical transition truth belongs here and in the hashed native receipts,
not a new guard or policy carrier.

## Approved supplier bytes and private install compatibility

Approved-proxy native HTTP200 and exact primary parity were observed for:

| Artifact | Bytes | Wheel SHA256 | METADATA SHA256 |
| --- | ---: | --- | --- |
| virtualenv21.14.5 |5487482 |b0651e0174982bba17cc6f0aaa2ef496730cb85a3f35eb5d1119d1c904f7d1da |b0fde245e322f834e437172f784cebb039bf1c657c30a79b7aa488085c2e92fc |
| python-discovery1.6.1 |38664 |d43fcdef879fe795352bd13ccf8d185ba5a9f86f36cfcd00529f596e737442b3 |fd4e94258896c927fd6e5354988c7b307a0f16b6a25abd5d0b646fcf5cc9fea8 |

Canonical artifact acquisition remained exact/no-deps/binary-only, with trusted
proxy hash admission, destroyed credentialed HOME before static wheel validation,
separate credential-free/index-free profile resolution, original captures and
all-candidate preparation/atomic-per-file/caught-failure rollback. Candidate code
was not imported during acquisition/static validation. This is neither arbitrary
same-UID isolation nor crash-atomic multi-lock publication.

After replay, an owned isolated checkout venv was created and synchronized
through the existing canonical installer (exit0). Native pip-check exited0,
with raw stdout `No broken requirements found.`. Observed installed versions:
virtualenv21.14.5, python-discovery1.6.1, filelock3.24.3, pre-commit4.6.1,
pip26.1.2, pip-tools7.6.0, Python3.13.14. The original compiler environment was
not updated. These results establish this local installed profile compatibility,
not every OS/interpreter, Cloud bootstrap or complete all-files hook success.

## Actual benign cold/warm hook seed and effective configuration

Using stock .pre-commit-config.yaml, real pre-commit4.6.1 created eleven cold
Python hook environments (exit0). A fresh PRE_COMMIT_HOME then created eleven new
hook environments using the same warmed owned app-data (exit0); this was actual
new environment creation, rather than only reuse of already-created hook venvs.
A separate warm reuse invocation also exited0. The receipts retain each real
pyvenv.cfg, installed hook package inventory and selected Python/pip version.
All observed created environments identify virtualenv21.14.5 and CPython3.13.14,
include-system-site-packages=false, with installed hook pip26.2.1.

The actual stock creator command is pre-commit's
`[sys.executable, -m virtualenv, envdir]`, with no extra creator/seeder/download
flags. Effective native pip configuration observation has only environment
configuration, no existing global/user/site/env config file or virtualenv config
path, explicit per-process PIP_INDEX_URL at https://packages.pulseplate.app and
no other ambient index override. Credential values are not recorded here.

Selected pip-26.2.1-py3-none-any.whl is1,816,632 bytes, SHA256
`71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e`.
Observed owned app-data cache wheel bytes equal the verified embedded wheel;
the cold and fresh-warm environments both install that pip version. This binds
the observed selected bundle/cache seam for this actual configuration.

The source's `_uses_default_index` heuristic returns false when explicit
PIP_INDEX_URL is present. Therefore this proof does
not claim downloaded-seed public-hash verification under a custom index, all
pip.conf configurations, every cache/extra-dir content, continuous cache
integrity or future seed behavior. Embedded verification's per-process memo is
not continuous copied/cache verification. Actual install-hooks environment
creation is distinct from running every hook over final material; the required
sequential all-files gate remains pending.

## Files, retained evidence and claim limits

Raw and structured local receipts live under ignored
artifacts/orchestration/consol-orch-recovery/virtualenv2455 and are never tracked.
The document includes the substantive finite inventories/delta and these exact
receipt identities; later sanitized archive/readback remains separately required.

- `surface-base-preaction-census.json`: SHA256 `4420f5d4da81776b489f74cf2ab6d22aa56be383799589c339f6a846d888403c`.
- `advisory-cutoff-reconciled.json`: SHA256 `a391fbb14b0c25b25aeba29d9a8590c668ab1ec3a884694bc9f1fb69479a500b`.
- `ghsa-597g-base-source-reconciliation.json`: SHA256 `cb6b02f45b54b1d4f1f0bde04451621f2d683abf0b19461041438be779351d92`.
- `approved-proxy-artifact-parity.json`: SHA256 `d4ea0c80a4ab175a6ff45d301d99dfe71a76f66d72a88329049066d06a826cd0`.
- `native-original-base-replay-proof.json`: SHA256 `3ebf97d2ae5eab5129dba3323b75018c58ad96c392d74dd428099057bc714126`.
- `current-head-surface-P-observation.json`: SHA256 `515ae2f73e9a4b08e7884b2a01bd0d8130136e5eaca67f78ceb3da72c41af48b`.
- `owned-venv-installed-state.json`: SHA256 `2eefc292df8a3d839405a27b78381ce13d5c9ac6bde0645d0a8ac5e0dd9d6088`.
- `real-hook-cold-observation.json`: SHA256 `a5841637463175e8b4edaddea59da0e5990218f70ecf9f7611be29af4ce72fd3`.
- `real-hook-cold-warm-proof.json`: SHA256 `608c548bb2fbb08102057a0c9fefffc67d36dd2f3a219b1b56f7737ba369e67b`.
- `real-hook-effective-config-observation.json`: SHA256 `9053d49554bf1a588e140454123a68ac18e4b945a5c2da2079c21d4150f0929e`.

Raw native Make candidate/replay logs and their exit0 receipts, owned venv-sync/
pip-check logs, cold-install/warm-create/warm-reuse logs and producer observations
remain preserved. Earlier Black check1 and corrected rerun0 remain historical
formatting evidence; source correction did not become a waiver. Initial pending
fields inside older P/install/cold snapshots retain their own timestamps and are
superseded only by the later named replay/install/warm receipts. A role, UI,
record or digest by itself does not supply native PASS or protected authority.

Remaining required outcome proof includes new guard/focused tests, narrow local
bundle, sequential all-files, premortem/Oracle/scoped supplemental roles,
current-material/current-head CI and applicable >=97% producers/security,
exact-material self-review/dispositions, provider-neutral one-successor
closeout/review cycle/strict readiness and protected exact-head merge. PG/backend
Docker publisher/hosted/post-merge proof and C28 DO/Cloud/runtime outcomes remain
separate. No full local make verify, suppression, registry/secret setting,
Cloud bootstrap fix, production deployment or new role framework was introduced.

## Risks/Rollback, decision log and next action

A reviewed revert of the coherent compiler/source/lock/guard change is the
rollback; restoring vulnerable locks reopens the known validation defect and
requires a new remediation decision. No live rollback, cache deletion or
production operation was performed by this evidence stage.

The one identity and one authored replacement were retained. Native replay
converted only the observed necessary discovery relations from proposal to C_R;
no other identity intent or generalized future baseline followed. Version P,
private installed compatibility and this real hook seed/config observation are
separate qualified results. The parent now validates the final seven-file stage
and remaining exact-material gates; this document cannot mark #2455 ready or
close the ledger or accepted overall goal.

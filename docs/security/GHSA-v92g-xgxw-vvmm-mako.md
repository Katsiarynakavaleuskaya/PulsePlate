# Mako remediation owner — current 1.4.2 resolver proof and retained history

## Current scope and status — 2026-10-31

PR: [#2494](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2494).
Owner: dev-operator (Dependency Epic); security-auditor review.
This is the existing Mako evidence owner, now recording the directly authorized
single-identity correction. The only authored application dependency transition
is PyPI `mako` from 1.3.12 to 1.4.2. The five source/constraint floors and five affected locks now select1.4.2.
Canonical runtime/dependent transactions and their independent replays completed
with native exit0. The live schema and finite F5 guard are updated in this candidate.
Current remediation P remains unachieved: installed compositions, real consumer
behavior, complete audits, current-head CI and final outcome remain UNKNOWN.

The frozen integrated input baseline is candidate3 Git index tree
`fa9336e4c2a05fb00fa2c9a2044008174aaa9d0c`, with published branch HEAD
`9d330b739b0059432f46475f3bc3f807315d0a66` and incoming main
`d20922f741f431b6eb3e47386ae944ca441a971e`. The index tree is a material snapshot,
not a new published commit or merge/readiness receipt. ROOT must retain actual
per-file base/head hashes and resolver evidence before final claims.

## D and complete governed S

D is one ecosystem-qualified identity, `PyPI:mako`; spelling normalization does
not create another identity. Independent tracked-path discovery and the existing
registry `scripts/ci/check_python_dependency_surfaces.py:189` identify 21
requirements/constraint carriers, including ten compiled lock profiles. Inspect
all of them at both frozen base and final head, plus candidate packaging metadata;
alert paths alone are not the surface universe. Current Mako-bearing subset:

| Carrier | Frozen base | Prepared source / final output target |
| --- | --- | --- |
| `requirements.in` | `>=1.3.12,<2.0.0` | `>=1.4.2,<2.0.0` |
| `requirements-docker-runtime.in` | `>=1.3.12,<2.0.0` | `>=1.4.2,<2.0.0` |
| `requirements-ci-lite.in` | `>=1.3.12,<2.0.0` | `>=1.4.2,<2.0.0` |
| `requirements-dev.in` | `>=1.3.12,<2.0.0` | `>=1.4.2,<2.0.0` |
| `constraints.txt` | `>=1.3.12` | `>=1.4.2` |
| `requirements.txt` | `==1.3.12` | `==1.4.2`, generated and replay-equal |
| `requirements-docker-runtime.txt` | `==1.3.12` | `==1.4.2`, generated and replay-equal |
| `requirements-ci-lite.txt` | `==1.3.12` | `==1.4.2`, generated and replay-equal |
| `requirements-dev.txt` | `==1.3.12` | `==1.4.2`, generated and replay-equal |
| `requirements-lock.txt` | `==1.3.12` | `==1.4.2`, generated and replay-equal |

The other eleven carriers have no direct Mako occurrence: test, RAG-vector,
RAG-vector-CPU, data and evals source/lock pairs, plus the noncompiled
`requirements-all.txt` reference. Their includes/compositions still consume
runtime truth and must be reconciled; absence is not omission from S. Current
`pyproject.toml` has no application dependency declaration and
`app/telemetry/setup.py` is application code, not a packaging setup invocation.
Repeat tracked discovery at final material to detect any added or removed carrier.

Evidence anchors: `requirements.in:45`, `requirements-docker-runtime.in:41`,
`requirements-ci-lite.in:38`, `requirements-dev.in:31`, `constraints.txt:55`;
`scripts/ci/compile_locked_python_requirements.py:1830` rejects an upgrade absent
from a seed, and `:2742` owns mixed-transaction rejection. Therefore the second
transaction selects docker-runtime, ci-lite, dev and aggregate, not the
historical October23 seven-profile list. Any unexpected actual dependency delta
or additional affected composition stops for owner reconciliation.

## Finite primary F_cutoff and nonempty A

Cutoff: authenticated complete GitHub global package-advisory observation at
2026-10-31T00:50:22.694018Z, reconciled with the retained maintainer and PyPI
observations. The `ecosystem=pip&affects=mako&per_page=100` response contains
five active, nonwithdrawn records and no next page; raw response SHA256
`3c93efa8c8f8306d3b3fb64ee40d61546a3dec93dc0492c39eb525624c2f7884`.
This corrects the earlier three-row preparation inventory. All five remain in
F_cutoff; the PyPI version endpoint is an independent input, not authority to
remove an advisory.

| Advisory | Primary affected range | First fixed version | Base1.3.12 disposition |
| --- | --- | --- | --- |
| [GHSA-v92g-xgxw-vvmm / CVE-2026-41205](https://github.com/advisories/GHSA-v92g-xgxw-vvmm) | `<=1.3.10` | `1.3.11` | Non-applicable at this base; already outside range |
| [GHSA-2h4p-vjrc-8xpq / CVE-2026-44307](https://github.com/advisories/GHSA-2h4p-vjrc-8xpq) | `<=1.3.11` | `1.3.12` | Non-applicable at this base; already outside range |
| [GHSA-5639-2j2p-m4mx / CVE-2026-102991](https://github.com/sqlalchemy/mako/security/advisories/GHSA-5639-2j2p-m4mx) | `<=1.4.1` | `1.4.2` | Applicable affected coordinate in all five base locks |
| [GHSA-v973-fxgf-6xhp / CVE-2022-40023](https://github.com/advisories/GHSA-v973-fxgf-6xhp) | `<1.2.2` | `1.2.2` | Non-applicable at this base: 1.3.12 is outside range; candidate 1.4.2 is also outside |
| [GHSA-7q8x-38mc-p84f / CVE-2010-2480](https://github.com/advisories/GHSA-7q8x-38mc-p84f) | `<0.3.4` | `0.3.4` | Non-applicable at this base: 1.3.12 is outside range; candidate 1.4.2 is also outside |

F_cutoff has five members; A is the single drive-letter URI advisory above,
with five comparable base witnesses and four independently non-applicable
advisories at base1.3.12. Its Windows TemplateLookup condition is distinct from package-version
remediation. Historical Linux/amd64 non-reachability evidence is retained below/
in the ledger; it neither removes the vulnerable coordinate nor proves every
supported platform safe. The four base-non-applicable advisories remain in the universal head
postcondition. Selected1.4.2 is outside all five named ranges; every actual
final governed occurrence still needs proof against each of those five members.

ROOT's retained public PyPI1.3.12 and1.4.2 responses both have an empty
`vulnerabilities` array. Their SHA256 values are respectively
`8af0a67f6e8ea054efc3d32d6f4313c2402406132a4e088189ae9fe7d0359a41` and
`ea1630832738679168c0412482341cc26c7820c7ee56a75add28315f30d75ae2`.
The active Windows advisory predates the reported earlier audit-zero result;
that feed discrepancy is unresolved, not cancellation or successful remediation.
Retain both raw observations and use the primary advisory in final proof.

## Replacement R and compatibility inputs

I_R is exactly Mako replacement to1.4.2 across all governed occurrences. Preserve
existing `<2.0.0` bounds. C_R is empty: complete canonical runtime and dependent original-seed replays
show only Mako1.3.12 ->1.4.2 in five locks, with no other package transition.
No unrelated manually selected package transition is authorized as closure. No application pip, packaging,
pip-tools or SDK upgrade is authored by this source change.

[Public1.4.2 metadata](https://pypi.org/pypi/Mako/1.4.2/json) reports non-yanked
`mako-1.4.2-py3-none-any.whl`, 80163 bytes, SHA256
`e70a2a4308952b33a21208bfd6725da79fae5a8c224578f8cfdeb60e5ace03df`.
This is metadata, not actual private-index artifact acquisition proof. Python
requirement rises to>=3.10 and MarkupSafe to>=2.0; current Python3.11–3.13 and
existing MarkupSafe3.0.3 satisfy those declared bounds. Optional Babel/testing/
lingua extras are not newly selected. Actual Alembic rendering, relevant
platform behavior, private-proxy bytes, startup hooks, composed installs and
native runtime compatibility remain to be observed.

ROOT qualified an isolated compiler with pip26.2.2, pip-tools7.6.1 and
packaging26.3 using canonical acquisition/consumption. The first read-only
constraints tempfile failure is retained; a second qualified attempt used an
exact constraints copy in its owned writable directory without repeating
successful venv/pip steps. Receipt consumption SHA256
`a40c9025abbb840abefcccf81dec4e60b32d237043a8927f955a2a1479869bff`
is tool qualification only. It grants no application install, new dependency
intent or native SDK security result. The retained matching SDK input must be
rebound before compilation.

## Procedure and P boundary

Use only [the current Mako checkpoint procedure](../../RUNBOOK_AGENT.md#current-mako-only-checkpoint--pr-2494-2026-10-31):
canonical runtime Make transaction, immutable successful runtime checkpoint and
independent original-input replay, then four dependent profiles under that exact
checkpoint with full replay. No intermediate runtime commit is required for this
specific correction; no historical October23 graph grant, weakened guard, hook
skip, fallback or source-floor rollback follows.

Final P requires every discovered governed Mako occurrence to be comparable and
outside every F_cutoff range, with all base/head surface deltas reconciled.
Raise live schema/tests only after all five generated target locks agree. Retain
actual commands/tool identities, complete distributions and classified deltas,
all input/output hashes, replay equality, private-index acquisition, applicable
runtime/platform tests, strict audits and current-head CI/review. An audit
provider's omission does not replace this per-advisory postcondition.

Current post-resolver status: five floors and five generated locks select1.4.2;
four successful native transactions/replays are retained below. Schema floor and
all five finite blocked ranges are now enforced by the unchanged per-identity
recognizer. Installed Mako/Alembic behavior and full audit/P remain pending.
Emergency wheel records are unchanged. The historical1.3.12 fallback
cannot satisfy the new1.4.2 intent; a private-index failure must fail closed,
not select the old wheel or add a new fallback. The separate historical
`MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md` is not rewritten.

## Observed canonical resolver and replay evidence — 2026-10-31

The actual compiler transactions used frozen input tree
`eacb4155335ad1ac9d60e88d284cb7eb22cde219` (candidate4), derived from the integrated
baseline above with only the authored Mako floors. Branch HEAD remained9d330b7;
this is staged material identity, not a published commit. Qualified compiler:
pip26.2.2 / pip-tools7.6.1 / packaging26.3, approved private proxy, retained matching
psycopg SDK input; container image
`sha256:4dacf887f001d20d6cbd453037201df331f2e7719b6077e68cda027712f1ed31`.
The exact qualified interpreter argument remains in the private transaction receipt.
This public record redacts only its task-local location:
`VENV_PYTHON=<redacted-qualified-interpreter>`.
Each command used canonical `make requirements-locks`, `UPGRADE_PACKAGES=mako==1.4.2`,
empty `GRAPH_CHANGE_PACKAGES=` and `GRAPH_CHANGE_ADMISSION=`, under a900-second
outer timeout with30-second termination grace. Runtime selected `LOCK_PROFILES=runtime`;
dependent selected `LOCK_PROFILES="docker-runtime ci-lite dev aggregate"`.
No resolver or replay was rerun by this documentation writer.

| Actual phase | Native exit | Duration | Observed result |
| --- | --- | --- | --- |
| Runtime A02 | 0 | 54.362s | requirements.txt only, same70 normalized packages |
| Runtime independent B02 | 0 | 62.649s | original seed replay equals A02 bytes |
| Dependent A01 | 0 | 209.117s | four locks only; runtime checkpoint unchanged |
| Dependent independent B01 | 0 | 179.346s | all four outputs byte-equal; runtime unchanged |

Runtime A01 failure native2/1.550s and the separate B01 wrapper/prologue failure
remain retained history; neither counts as a successful compile. Successful replay
used original transaction seeds, not the successful output as its own seed. The
runtime checkpoint is SHA256
`06833a3a071ea408235482d31956828eb563b7055f2f91c4c17bd1b0c1490668`.
Both dependent transactions consumed that immutable checkpoint and preserved it.

Complete changed-lock identity table (every delta is solely Mako1.3.12 ->1.4.2):

| Lock | Base SHA256 | Generated/replayed SHA256 |
| --- | --- | --- |
| `requirements.txt` | `82f147c28b29cbfcc8babf6090140acac048cbe0d6a9e76bfd1399c2d711e18b` | `06833a3a071ea408235482d31956828eb563b7055f2f91c4c17bd1b0c1490668` |
| `requirements-docker-runtime.txt` | `3c4ea9d51e70095ffbe093069f4e657d1c21d110e7e8f31e7b9a5087dd63f1cc` | `461a16074b2780b9725c805706d234b6b44780a42205c39a83cd1c466d289e76` |
| `requirements-ci-lite.txt` | `6472606da9d141d90774a6f0a2fb939e14be1d4e52e5bcc4c077c21d7dbaf078` | `082f673372f527c64ba4f8334f55a1faa193914dce75ad182e5e66b6baafdb0c` |
| `requirements-dev.txt` | `807d98929385ec3b41a8a69a065f673df773c9faae4c15668aca6a224207f967` | `f00d82de21f50e6ffb977f69738bdd15bbc5f41ccff65702b81681d845bea2e4` |
| `requirements-lock.txt` | `31b355109b80329bcc3fbd97856fe80b0ed603c2545b58423078ad0472923859` | `4914573e1a51387509cb3c037fe12aeaf5780a66e81be47e7c78668c8eaea1d6` |

Complete extras-aware normalized counts are runtime70, docker-runtime61,
ci-lite106, dev89 and aggregate137, unchanged between each original seed and
its generated/replayed output. The earlier68/59/103/87/133 observations were
plain-name projections that omitted extras-bearing declarations such as
`opentelemetry-exporter-http-transport[requests]`, `psycopg[c]`,
`cachecontrol[filecache]` and `coverage[toml]`; they remain historical projection
counts, not complete package inventories. Full before/after maps retaining
version, extras, marker and URL still show only Mako1.3.12 ->1.4.2, so C_R remains
empty and all lock bytes/replay equality are unchanged. The complete four-archive
reconciliation SHA256 is
`19ebce67f348419843b1e06a4631b2a6304196ee5b3e636453e99ec86801e9f7`.
Every other distribution/pin and all other governed carrier bytes remained
unchanged within these resolver transactions. Independent current worktree
readback matches all five returned output hashes. The authored transition is
I_R={PyPI:mako replacement}; deterministic C_R is empty. These are transition
facts, not installed/runtime or universal P claims.

ROOT consumption receipt SHA256 identities:

- `mako-runtime-A-ROOT-consumption.json`: `d576d96efa739ce1779cbfb2410565fc6c813fd829d2d8dc7df92d08e8980305`.
- `mako-runtime-B-ROOT-consumption.json`: `522649b3e8ed1ca554bb3dc51ed2b7a239485d1a22aa20544e333f02b2097c9f`.
- `mako-dependent-A-ROOT-consumption.json`: `4140502373253aaf1b359ca46d78fead06e6a8cebcd38786f0cde9629195dd9d`.
- `mako-dependent-B-ROOT-consumption.json`: `165fd0d22ee60982225aab792220552af2ea5e1691ceffb43219bc0bbca10215`.

Evidence owners: `scripts/ci/compile_locked_python_requirements.py:1830`,
`tests/fixtures/dependency_security_schema.json:5`, and
`tests/test_dependency_security_guard.py:3036`. The permanent guard enumerates
current registered/discovered carriers and uses the existing per-identity parser;
it does not freeze these historical hashes or resolver output bytes.

Final frontier: all21 carriers/ten locks and packaging candidates must reconcile;
all installed compositions need actual Mako metadata, pip-check and template/Alembic
consumer proof in qualified fresh environments. Complete ten-lock audit and the
ordinary owning audit retain full raw results/private-wheel comparands. PyPI-empty
advisory metadata does not cancel the five primary advisories. New guard tests,
installed/runtime/audit/P and CI remain pending until their native observations.
Original39/N7 and historical deadlines are unchanged.

## Historical 1.3.12 remediation record

The following prior owner text is retained as historical evidence. Its commands,
line numbers, floor, severity and earlier lane scope describe that older record,
not completed current1.4.2 proof or present fallback authority.

### Summary

- Package: `Mako`
- GHSA: `GHSA-v92g-xgxw-vvmm`
- Severity: `medium`
- Fixed version: `1.3.12`

This lane remediates the `Mako` advisory by raising the repo-managed security
floor to `1.3.12` across the governed Python source, dev, pinned, and CI-lite
requirement surfaces.

### Repo Evidence

- `requirements.in:39` - runtime source floor is `mako>=1.3.12,<2.0.0`
- `requirements-ci-lite.in:36` - CI-lite source floor is `mako>=1.3.12,<2.0.0`
- `requirements-dev.in:25` - dev tooling surface now carries `mako>=1.3.12,<2.0.0`
- `constraints.txt:51` - constraints floor is `mako>=1.3.12`
- `requirements.txt:103` - runtime lock pins `mako==1.3.12`
- `requirements-dev.txt:87` - dev lock pins `mako==1.3.12`
- `requirements-lock.txt:213` - full lock pins `mako==1.3.12`
- `requirements-ci-lite.txt:152` - CI-lite lock pins `mako==1.3.12`
- `scripts/ci/emergency_python_wheels.json:85-90` - exact wheel fallback records
  `mako==1.3.12` with artifact-scoped expiry and pinned `sha256`
- `tests/fixtures/dependency_security_schema.json:4` - dependency security schema
  records minimum safe version `1.3.12`

### Validation

```bash
.venv/bin/python -m pytest -q tests/test_dependency_security_guard.py
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
rg -n "mako|Mako" requirements.in requirements-ci-lite.in requirements-dev.in requirements.txt requirements-dev.txt requirements-lock.txt requirements-ci-lite.txt constraints.txt tests/fixtures/dependency_security_schema.json scripts/ci/emergency_python_wheels.json
python3 scripts/ci/install_locked_python_requirements.py --index-url "${PULSEPLATE_PYTHON_INDEX_URL}" --trusted-host "${PULSEPLATE_PYTHON_TRUSTED_HOST}" --preflight-only
```

### Notes

- The repo uses a schema-driven dependency guard, so the remediation must be
  reflected in both source manifests and the pinned lock surfaces.
- The floor is enforced explicitly rather than relying on the current Alembic
  transitive resolution, so future lock regeneration cannot drift back to the
  vulnerable `1.3.10` release.
- Current-head dependency-install evidence for the private-proxy lag and the
  exact-wheel fallback governance lives in
  `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md:5-18` and
  `docs/security/MAKO_1_3_11_PRIVATE_INDEX_ADVISORY.md:31-38`.
- This lane stays dependency-only; runtime and frontend behavior remain out of
  scope per
  `docs/orchestration/DEPENDABOT_ALERTS_114_116_REMEDIATION_TASK_PACKET_2026-04-17.md:101-106`.

### Temporary Seam Governance

- ADR: `docs/architecture/ADR_WAVE6_SECURITY_FLOOR_UNBLOCK_SEAM_2026-04-17.md:1-79`
- Seam backlog / DoD / blockers:
  `docs/roadmap/BACKLOG_LEDGER.md:1678-1699`
- Emergency-manifest retirement backlog:
  `docs/roadmap/BACKLOG_LEDGER.md:445-474`

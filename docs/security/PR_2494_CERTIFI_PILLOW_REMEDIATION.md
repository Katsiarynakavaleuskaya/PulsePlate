# PR #2494: certifi remediation and temporary retained Pillow risk

PR: #2494
Owner: dependency/security; ROOT executes this PR; the human repository owner accepts the bounded temporary risk.

## Authority, scope and current truth

On 2026-10-21 the human repository owner directly authorized the necessary audit and correction processes, conditional merge after fresh readiness, and temporary ignores when a compatible solution cannot be qualified. The owner reaffirmed that instruction after the FastEmbed conflict and requested one coherent source/tests/docs package. These external instructions are the authority; this document, dates, hashes, tests and scanner output cannot create permission.

The achievable route is **certifi-only remediation to 2026.10.19 plus a separate temporary Pillow 12.3.0 risk disposition**. The former two-identity remediation attempt did not satisfy its conjunction and remains unsuccessful. Pillow universal P is false. No FastEmbed upgrade, replacement library, SDK change, feature removal or hand-edited generated lock is included. All seven generated locks and the source/schema/test changes must agree before final-material claims.

The original 2026-10-21T00:00:00Z deadline was missed and remains UNACHIEVED. The owner permits revising future timing but supplied no replacement timestamp. The review/expiry dates below are prospective ROOT-selected bounds under that instruction, not literal human timestamps, a rewritten AM deadline or a renewal of expired AM admission. Current production incident/exposure is not established by these CI findings.

The exact writer handoff covers 17 admitted source/test/config/document paths; ROOT alone owns seven generated locks and remote execution. Final path inventory, generated dependency delta and trusted scope admission remain ROOT's publication prerequisites. This document does not turn the old 30+1 scope or any future unrelated dependency into permission.

## Immutable full scanner snapshot and native format observations

- Existing qualified pip-audit 2.10.1, strict/no-deps/disable-pip, serial all 10 registry compiled locks on be27b919396d9c1885b1c1d89e62ab9a9e32c613, base/merge-base 48d36c220ff58dec82450da66ef0599c6da71787.
- Observation 2026-10-21T06:25:54.499810Z through 06:26:15.046844Z: all 10 terminal JSON reports; seven contain 9 reported IDs across certifi/Pillow, three have none. Evals is positively comment/blank-only. No omitted input, dependency skip, scanner timeout or parse error was observed. This is a finite observation, not atomic or universal advisory history.
- Native aggregate exit 1 means findings. Complete 128-member secret-free archive 1,637,701 bytes SHA-256 `9726c03e751761e5c04c8f7cda6346b7f3fbb782a7c6f810fd80908271cedc1b`; ROOT consumption SHA-256 `f8bde7e62fd0470e618d0afb92e8874842ecdfd42ccfe0cfa886402d53c13511`.

```text
Found 9 known vulnerabilities in 2 packages
```

PYSEC-2026-4320/GHSA-6q48-6c7w-9gw2 are one certifi finding. Eight native Pillow IDs are the exact exception cohort below; their count does not replace the 61-row primary inventory.

Native 2.10.1 qualification on the identical 89-dependency dev input proved that ignored JSON has `dependencies`/`fixes`, resolved rows have `name`/`version`/`vulns`, and ignored Pillow rows have `vulns: []` with **no ignored-details field**. The ignored diagnostic exited 1 because certifi remained active; stderr reported 1 active and 8 ignored. A fresh unsuppressed counterpart exited 1 and retained all 9 finding details. Both observations had identical dependency names/versions and exact input SHA-256 `173aaf867f1654dd36cda34151f78db8e64cf19210ae301c32b7234d5f8a86e8`. Exactly eight removed tuples bind Pillow 12.3.0 and the cohort below. This is format/negative-control evidence, not a passing security gate.

Raw report SHA-256 `d71eb671ce0ef53ec290e5ec92c85afde6c55285046a318186034a190064666d`; ignored report SHA-256 `e7f5b6eeb2f309b77ba4d379bae4928667a9dafe7d866921fcfb5289b16ab55f`; paired ROOT receipt SHA-256 `d758ada44451fbb3489d12e8bf0b9dc0cd6f8dc3727bbb199ab91ea244f6a6a2`.

## Governed surfaces and selected action

The existing executable registry and independent tracked discovery at scripts/ci/check_python_dependency_surfaces.py:189 enumerate 21 carriers. Independent Git discovery examined 28 potential base/head carriers; selected bytes were equal before correction. Counts are dated observations; current registry/discovery reconciliation remains mandatory at every exception use.

Pillow occurs in seven locks (`requirements.txt`, `requirements-docker-runtime.txt`, `requirements-ci-lite.txt`, `requirements-dev.txt`, `requirements-rag-vector.txt`, `requirements-rag-vector-cpu.txt`, `requirements-lock.txt`), four sources (`requirements.in`, `requirements-docker-runtime.in`, `requirements-ci-lite.in`, `requirements-dev.in`) and `constraints.txt`. Retain exact 12.3.0 locks/constraint and genuine source ranges `>=12.3.0,<13.0.0`. No-Pillow data/test/evals inputs remain separately scoped; a valid empty evals input is not global no-findings proof.

certifi has seven base lock occurrences. Its authored replacement is 2026.1.4 → 2026.10.19, with explicit floors in all four runtime/development sources and an exact constraint. ROOT must generate all seven locks via the canonical target; no other dependency transition is intended. Every extra transition requires its existing deterministic solver-closure proof, never manual classification as convenient cleanup.

The superseded Pillow 13/runtime transaction succeeded, but the dependent transaction failed and rolled back: FastEmbed 0.8.0 requires Pillow <13. Checked public 0.8.1/0.9 metadata also retain that cap. The transient runtime 13 / dependent 12 state is failed historical evidence, not the final graph. Forty affected source rows name 13.0 fixes; they are currently incompatible with this checked graph, **not all unfixed upstream**. No compatibility claim about every possible future release follows.

Canonical certifi-only commands, no intermediate source commits:

```bash
LOCK_PROFILES="runtime" UPGRADE_PACKAGES="certifi==2026.10.19 pillow==12.3.0" make requirements-locks
LOCK_PROFILES="docker-runtime ci-lite dev rag-vector rag-vector-cpu aggregate" UPGRADE_PACKAGES="certifi==2026.10.19 pillow==12.3.0" make requirements-locks
```

The explicit Pillow 12.3.0 argument normalizes the abandoned uncommitted runtime 13 proposal and is identical in the independent exact-base replay. Net be27-to-final dependency intent remains certifi-only; unchanged baseline Pillow is not a remediation transition.

Use the existing approved proxy, matching Psycopg-C SDK, Python 3.13.5 / pip-tools 7.6.0 / pip 25.1.1. Preserve native generation, exact source/seed/output hashes, whole dependency delta and independent exact-base replay before claiming certifi C_R/P. No compiler/image/SDK substitution is admitted by this route.

## Frozen primary inventory and applicability

Named primary input bytes frozen during 2026-10-21 03:36 reconciliation, plus the terminal all 10 observation, form the finite F_cutoff. The complete published inventories have 61 Pillow rows and 4 certifi rows, no next page. Row counts are not distinct flaws or exploitability judgments.

| Frozen primary input | SHA-256 |
| --- | --- |
| `pillow-upstream-advisories.json` | `40b2a0a8ffe540ed2772a1d402d09de8c74b5874cc55267c81fa0947fb69e6d5` |
| `certifi-upstream-advisories.json` | `412288148097767310453949773f7819ae3903179d47c2df272b2ebf04925c3b` |
| `PYSEC-2026-4320.yaml` | `6b150bc853575a0675446a62e959b10c7df1ac4685120fe8c7966e62fbcdb783` |

### certifi: four candidates, one applicable at base

Newest upstream raw affected `>=2019.03.09`, patched 2026.10.18; PyPA alias fixed 2026.10.19 and includes 18 as affected. Conservatively reconcile `>=2019.3.9,<2026.10.19`: 18 removed all emSign roots, 19 restored unaffected roots. Selected 19 is outside that interval and all three older intervals. Retain the raw source disagreement instead of treating unbounded GHSA prose as overriding its patched field.

| Advisory | Raw affected range | Base 2026.1.4 | Generated candidate 2026.10.19 |
| --- | --- | --- | --- |
| [GHSA-6q48-6c7w-9gw2](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) | `>=2019.03.09` | Affected | Outside reconciled interval |
| [GHSA-248v-346w-9cwc](https://github.com/certifi/python-certifi/security/advisories/GHSA-248v-346w-9cwc) | `>=2021.05.30,<2024.07.04` | Not applicable at base; retained | Outside reconciled interval |
| [GHSA-xqr8-7jwr-rhp7](https://github.com/certifi/python-certifi/security/advisories/GHSA-xqr8-7jwr-rhp7) | `>=2015.04.28,<2023.07.22` | Not applicable at base; retained | Outside reconciled interval |
| [GHSA-43fp-rhv2-5gv8](https://github.com/certifi/python-certifi/security/advisories/GHSA-43fp-rhv2-5gv8) | `>= 2017.11.05, <2022.12.07` | Not applicable at base; retained | Outside reconciled interval |

### Pillow: all 61 retained primary rows

| Advisory / CVE | Raw affected range | Base 12.3.0 | Retained head 12.3.0 |
| --- | --- | --- | --- |
| [GHSA-78g4-xqwv-q3g8](https://github.com/python-pillow/Pillow/security/advisories/GHSA-78g4-xqwv-q3g8) | `11.1.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-fc9g-5qg7-mf45 / CVE-2026-112891](https://github.com/python-pillow/Pillow/security/advisories/GHSA-fc9g-5qg7-mf45) | `9.2.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-654x-cwwv-5j9c](https://github.com/python-pillow/Pillow/security/advisories/GHSA-654x-cwwv-5j9c) | `11.2.1 - 13.0.0` | Affected | Affected; temporarily retained |
| [GHSA-65qm-jvmh-6pqg / CVE-2026-112400](https://github.com/python-pillow/Pillow/security/advisories/GHSA-65qm-jvmh-6pqg) | `<= 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-vx6w-vv9f-6gvg / CVE-2026-112899](https://github.com/python-pillow/Pillow/security/advisories/GHSA-vx6w-vv9f-6gvg) | `2.3.0 - 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-xgh8-jp6q-p5x8 / CVE-2026-112901](https://github.com/python-pillow/Pillow/security/advisories/GHSA-xgh8-jp6q-p5x8) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-jg86-v3jv-hrpm / CVE-2026-112894](https://github.com/python-pillow/Pillow/security/advisories/GHSA-jg86-v3jv-hrpm) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-74r2-7ff9-mjj2 / CVE-2026-112401](https://github.com/python-pillow/Pillow/security/advisories/GHSA-74r2-7ff9-mjj2) | `5.4.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-27h8-gf7j-v5hc / CVE-2026-112392](https://github.com/python-pillow/Pillow/security/advisories/GHSA-27h8-gf7j-v5hc) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-f2g6-542v-9j58 / CVE-2026-112406](https://github.com/python-pillow/Pillow/security/advisories/GHSA-f2g6-542v-9j58) | `5.1.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-22hg-r758-rrw9 / CVE-2026-112390](https://github.com/python-pillow/Pillow/security/advisories/GHSA-22hg-r758-rrw9) | `7.2.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-rfgq-q3w2-pmv2 / CVE-2026-112898](https://github.com/python-pillow/Pillow/security/advisories/GHSA-rfgq-q3w2-pmv2) | `9.1.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-7mwm-ghpf-9vrm / CVE-2026-112402](https://github.com/python-pillow/Pillow/security/advisories/GHSA-7mwm-ghpf-9vrm) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-5xm2-6676-qcp9 / CVE-2026-112399](https://github.com/python-pillow/Pillow/security/advisories/GHSA-5xm2-6676-qcp9) | `8.1.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-xvh5-g6gv-559v / CVE-2026-112902](https://github.com/python-pillow/Pillow/security/advisories/GHSA-xvh5-g6gv-559v) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-q45j-58j2-45rg / CVE-2026-112897](https://github.com/python-pillow/Pillow/security/advisories/GHSA-q45j-58j2-45rg) | `<= 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-c6hw-5grf-ff96 / CVE-2026-112404](https://github.com/python-pillow/Pillow/security/advisories/GHSA-c6hw-5grf-ff96) | `<= 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-g7cr-3p24-7wf7 / CVE-2026-96778](https://github.com/python-pillow/Pillow/security/advisories/GHSA-g7cr-3p24-7wf7) | `9.4.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-332p-7hrc-92wf / CVE-2026-112393](https://github.com/python-pillow/Pillow/security/advisories/GHSA-332p-7hrc-92wf) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-4558-3h8r-v8xp / CVE-2026-112394](https://github.com/python-pillow/Pillow/security/advisories/GHSA-4558-3h8r-v8xp) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-pchr-8j38-3x4p / CVE-2026-112896](https://github.com/python-pillow/Pillow/security/advisories/GHSA-pchr-8j38-3x4p) | `<= 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-8g5g-8vmr-9782 / CVE-2026-112403](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8g5g-8vmr-9782) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-w889-685w-c8fh / CVE-2026-112900](https://github.com/python-pillow/Pillow/security/advisories/GHSA-w889-685w-c8fh) | `2.6.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-254f-3936-288h / CVE-2026-112391](https://github.com/python-pillow/Pillow/security/advisories/GHSA-254f-3936-288h) | `5.1.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-g4qv-2jxx-769h / CVE-2026-96643](https://github.com/python-pillow/Pillow/security/advisories/GHSA-g4qv-2jxx-769h) | `11.0.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-3j72-p6qg-6xp7 / CVE-2026-96642](https://github.com/python-pillow/Pillow/security/advisories/GHSA-3j72-p6qg-6xp7) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-p4wg-p73j-c528 / CVE-2026-112895](https://github.com/python-pillow/Pillow/security/advisories/GHSA-p4wg-p73j-c528) | `5.1.0 - 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-gg2r-wvfm-q9rx / CVE-2026-112892](https://github.com/python-pillow/Pillow/security/advisories/GHSA-gg2r-wvfm-q9rx) | `4.1.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-9v9v-9qvf-h2hj / CVE-2026-96644](https://github.com/python-pillow/Pillow/security/advisories/GHSA-9v9v-9qvf-h2hj) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-j4m9-6w36-pw47 / CVE-2026-112893](https://github.com/python-pillow/Pillow/security/advisories/GHSA-j4m9-6w36-pw47) | `10.0.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-58r4-6rv3-gfh8 / CVE-2026-112397](https://github.com/python-pillow/Pillow/security/advisories/GHSA-58r4-6rv3-gfh8) | `<= 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-cp9v-662q-vvx9 / CVE-2026-112405](https://github.com/python-pillow/Pillow/security/advisories/GHSA-cp9v-662q-vvx9) | `12.0.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-4rr5-89j8-mwwm / CVE-2026-112396](https://github.com/python-pillow/Pillow/security/advisories/GHSA-4rr5-89j8-mwwm) | `11.3.0 - 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-v9pv-5gc8-w2m6 / CVE-2026-96639](https://github.com/python-pillow/Pillow/security/advisories/GHSA-v9pv-5gc8-w2m6) | `>= 11.0.0, <= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-4rm8-3hmm-39fg / CVE-2026-96641](https://github.com/python-pillow/Pillow/security/advisories/GHSA-4rm8-3hmm-39fg) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-24rc-8hj2-v98c / CVE-2026-96638](https://github.com/python-pillow/Pillow/security/advisories/GHSA-24rc-8hj2-v98c) | `>= 9.1.0, <= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-g842-9rc4-69pw / CVE-2026-96637](https://github.com/python-pillow/Pillow/security/advisories/GHSA-g842-9rc4-69pw) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-p8hx-v2p6-rp84 / CVE-2026-96636](https://github.com/python-pillow/Pillow/security/advisories/GHSA-p8hx-v2p6-rp84) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-mrfp-p49p-3hf2 / CVE-2026-96640](https://github.com/python-pillow/Pillow/security/advisories/GHSA-mrfp-p49p-3hf2) | `>= 5.1.0, <= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-9hw9-ch79-4vh6 / CVE-2026-59205](https://github.com/python-pillow/Pillow/security/advisories/GHSA-9hw9-ch79-4vh6) | `<=12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-6r8x-57c9-28j4 / CVE-2026-59199](https://github.com/python-pillow/Pillow/security/advisories/GHSA-6r8x-57c9-28j4) | `<= 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-phj9-mv4w-65pm / CVE-2026-55380](https://github.com/python-pillow/Pillow/security/advisories/GHSA-phj9-mv4w-65pm) | `≤ 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-5x94-69rx-g8h2 / CVE-2026-54060](https://github.com/python-pillow/Pillow/security/advisories/GHSA-5x94-69rx-g8h2) | `≤ 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-8v84-f9pq-wr9x / CVE-2026-54059](https://github.com/python-pillow/Pillow/security/advisories/GHSA-8v84-f9pq-wr9x) | `≤ 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-45hq-cxwh-f6vc / CVE-2026-55379](https://github.com/python-pillow/Pillow/security/advisories/GHSA-45hq-cxwh-f6vc) | `≤ 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-fj7v-r99m-22gq / CVE-2026-59198](https://github.com/python-pillow/Pillow/security/advisories/GHSA-fj7v-r99m-22gq) | `5.2.0 - 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-xj96-63gp-2gmr / CVE-2026-59197](https://github.com/python-pillow/Pillow/security/advisories/GHSA-xj96-63gp-2gmr) | `<= 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-5x8w-8jj5-q52h / CVE-2026-112398](https://github.com/python-pillow/Pillow/security/advisories/GHSA-5x8w-8jj5-q52h) | `<= 12.3.0` | Affected | Affected; temporarily retained |
| [GHSA-62p4-gmf7-7g93 / CVE-2026-54058](https://github.com/python-pillow/Pillow/security/advisories/GHSA-62p4-gmf7-7g93) | `<= 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-vjc4-5qp5-m44j / CVE-2026-59204](https://github.com/python-pillow/Pillow/security/advisories/GHSA-vjc4-5qp5-m44j) | `8.2.0 - 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-pg7v-jwj7-p798 / CVE-2026-59203](https://github.com/python-pillow/Pillow/security/advisories/GHSA-pg7v-jwj7-p798) | `12.0.0 - 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-4x4j-2g7c-83w6 / CVE-2026-55798](https://github.com/python-pillow/Pillow/security/advisories/GHSA-4x4j-2g7c-83w6) | `<= 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-462x-pgg6-55fp / CVE-2026-112395](https://github.com/python-pillow/Pillow/security/advisories/GHSA-462x-pgg6-55fp) | `8.2.0 - 12.3.0` | Affected / reported | Affected; temporarily retained |
| [GHSA-5xmw-vc9v-4wf2 / CVE-2026-42309](https://github.com/python-pillow/Pillow/security/advisories/GHSA-5xmw-vc9v-4wf2) | `>= 11.2.1, < 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-wjx4-4jcj-g98j / CVE-2026-42308](https://github.com/python-pillow/Pillow/security/advisories/GHSA-wjx4-4jcj-g98j) | `< 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-r73j-pqj5-w3x7 / CVE-2026-42310](https://github.com/python-pillow/Pillow/security/advisories/GHSA-r73j-pqj5-w3x7) | `>= 5.1.0, < 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-pwv6-vv43-88gr / CVE-2026-42311](https://github.com/python-pillow/Pillow/security/advisories/GHSA-pwv6-vv43-88gr) | `>= 10.3.0, < 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-whj4-6x5x-4v2j / CVE-2026-40192](https://github.com/python-pillow/Pillow/security/advisories/GHSA-whj4-6x5x-4v2j) | `>= 10.3.0, < 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-jjj6-mw9f-p565 / CVE-2026-59200](https://github.com/python-pillow/Pillow/security/advisories/GHSA-jjj6-mw9f-p565) | `5.1.0 - 12.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-cfh3-3jmp-rvhc / CVE-2026-25990](https://github.com/python-pillow/Pillow/security/advisories/GHSA-cfh3-3jmp-rvhc) | `>= 10.3.0, < 12.1.1` | Not applicable at base; retained | Outside affected range; retained NAB |
| [GHSA-xg8h-j46f-w952 / CVE-2025-48379](https://github.com/python-pillow/Pillow/security/advisories/GHSA-xg8h-j46f-w952) | `11.2.0` | Not applicable at base; retained | Outside affected range; retained NAB |


The CNA HTTP 404 for CVE-2026-112899 remains an unavailable source, not NOT-A-BUG; GHSA-vx6w-vv9f-6gvg positively binds its alias.

## Temporary retained Pillow 12.3.0 exception

All 41 base-applicable source rows remain affected at retained 12.3.0: 8 native reported rows plus 33 additional affected rows. Source-row severities are 13 HIGH / 2 CRITICAL / 23 MEDIUM / 3 LOW, not distinct flaws or deployed exploitability counts. All 20 base-NAB rows remain in the head inventory. GHSA-654x-cwwv-5j9c separately affects 11.2.1–13.0.0 inclusive; Arrow export with PILLOW_ALIGNMENT>1 may expose stale heap bytes and the retained advisory names no patched version. Deployed configuration, indirect paths and exploitability remain UNKNOWN. Tracked absence of direct Arrow calls does not prove no exposure.

Only the following closed native cohort on PyPI:pillow==12.3.0 is eligible:

| Native ID | Bound upstream alias |
| --- | --- |
| CVE-2026-112395 | GHSA-462x-pgg6-55fp |
| CVE-2026-112397 | GHSA-58r4-6rv3-gfh8 |
| CVE-2026-112400 | GHSA-65qm-jvmh-6pqg |
| CVE-2026-112404 | GHSA-c6hw-5grf-ff96 |
| CVE-2026-112895 | GHSA-p4wg-p73j-c528 |
| CVE-2026-112896 | GHSA-pchr-8j38-3x4p |
| CVE-2026-112897 | GHSA-q45j-58j2-45rg |
| CVE-2026-112899 | GHSA-vx6w-vv9f-6gvg |

Owner: dependency/security. Review reminder 2026-10-23T00:00:00Z; hard expiry 2026-10-28T00:00:00Z. At `now>=expiry` the actual helper rejects before every ignored invocation and before promotion; the reminder is not an earlier hidden expiry. There is no user-set clock override, package/severity ignore or global bypass.

The existing `scripts/ci_pip_audit.sh` owns no-args CI mode (six declared manifests, not all 10 coverage) and the exact `--pre-push` selector (requirements.txt only). The remote pre-commit hook retains pip-audit 2.10.1 and delegates to that helper. `scripts/ci/check_python_dependency_surfaces.py` owns one literal predicate/cohort. CI now also uses `--strict` alongside retained `--no-deps --disable-pip`; this is explicit strengthening.

Each current invocation retains an unsuppressed JSON report first. Only a complete exact dependency/version inventory with admitted Pillow tuples may reach the ignored invocation. Both current reports must bind the same unchanged input/carriers; their exact removed finding subset must be admitted and the ignored native exit must be 0 with no active findings. A raw native 1 is recorded as findings, never native PASS. Native errors/nonexpected exits, skips, unknown IDs/aliases, wrong package/version, stale/missing/malformed reports, carrier drift or expiry block acceptance. The native ignored format removes details, so ignored JSON alone never proves eligibility. No-Pillow/no-findings inputs do not need eight finding rows and must not invoke ignores.

Unique raw/native/stdout/stderr evidence is retained under `artifacts/security_lab/pip-audit/`; CI also exposes canonical `pip-audit-*.json` copies including unsuppressed/native counterparts for existing artifact retention. Pre-push keeps its reports in that ignored evidence directory. Historical evidence is not deleted or reused. The exact retired PyTorch CVE-2025-3000/GHSA-rrmf-rvhw-rf47 exception remains absent.

This is policy acceptance of known retained risk, **not Pillow remediation, FIXED, NOT-A-BUG, no findings, security-safe status or successful former two-identity P**. The other 33 applicable primary rows remain documented risk; their absence from native output does not ignore their identifiers. Any newly emitted finding outside the exact eight blocks the actual audit. Four original AM exception retirements are a separate subject and do not mean all repository security exceptions disappeared.

## Follow-up, removal and rollback

Track the complete retained risk at [the canonical ledger](../roadmap/BACKLOG_LEDGER.md#ledger-p1-pillow-arrow-residual-2494). Qualify a compatible applicable fix against the full retained inventory as soon as available; regenerate all affected locks and remove the exact obsolete ignores plus temporary 12.3 equality branch. Preserve ordinary future schema-driven floors rather than permanently freezing 12.3. Pillow removal/replacement feasibility is a future dependency decision covering ReportLab/PDF, Matplotlib visualization, FastEmbed and tooling consumers; no migration is implemented here.

Rollback the coherent correction on compatibility regression, preserve known vulnerable baseline/failure evidence and stop readiness. Do not silently broaden ignores, change SDK/features or extend expiry. At hard expiry, an unresolved case remains blocked absent a new explicit owner decision.

## Validation status and outcome boundary

Implementation references: scripts/ci/check_python_dependency_surfaces.py:1142; scripts/ci_pip_audit.sh:1; .pre-commit-config.yaml:126; tests/test_dependency_security_guard.py:124; tests/fixtures/dependency_security_schema.json:1. Canonical generation remains Makefile:106 and scripts/ci/compile_locked_python_requirements.py:1498.

First generation, before the later three source-floor additions, observed on 2026-10-21: canonical generation and its independent exact-be27 replay completed with all four Make transactions exit 0, native total 679.083773 seconds, no timeout and empty stderr for all four commands. All seven output blobs are byte-identical to their independent replay. ROOT verified full 5,718 typed source/index/hook parity, original process absence, and all 131 evidence archive members by type/mode/size/SHA-256/readback before transferring the exact generated blobs to Mac. The raw index remains unchanged; no source commit or publication follows from that transfer.

| Governed lock | Complete distribution count (unchanged) | Complete version delta | Retained Pillow |
| --- | --- | --- | --- |
| `requirements.txt` | 68 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |
| `requirements-docker-runtime.txt` | 59 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |
| `requirements-ci-lite.txt` | 104 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |
| `requirements-dev.txt` | 89 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |
| `requirements-rag-vector.txt` | 35 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |
| `requirements-rag-vector-cpu.txt` | 35 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |
| `requirements-lock.txt` | 135 | `2026.1.4 -> 2026.10.19` | `12.3.0 -> 12.3.0` |

The complete JSON dependency relation has SHA-256 `bf718f5325ea3396c59b6a3c0df3fd70612ce0d857878b08f7136692e5a0d58e`. For every lock, base/head distribution names and extras/markers/URLs are equal; all-and-only certifi changed, and `C_R=[]`. Both full maps and native commands are retained in the 131-member secret-free raw archive, 38,409,297 bytes, SHA-256 `35cf6738459cd24b27f9bf2e455adec447390f78025898c3e66612934d2032d2`. This establishes the generated candidate relation; it does not remediate retained Pillow or establish final-head readiness.

The subsequent current-floor guard exposed missing explicit certifi declarations in `requirements-docker-runtime.in`, `requirements-ci-lite.in` and `requirements-dev.in`. Those owning sources now declare `certifi>=2026.10.19`; the unchanged guard passes all 10 current-surface cases. Canonical captured source closure identifies only Docker-runtime, CI-lite, dev and aggregate locks as affected by these additions. The final four-profile annotation regeneration and independent exact-base-seed replay both completed exit 0, native 407.238297 seconds / host 414.839271 seconds, no timeout. All four output blobs match the new replay byte-for-byte. Runtime and both RAG source/output bindings remain unchanged and reuse only their observed canonical prefix; they were not executed again. The composed seven-lock relation still changes only certifi, with empty solver closure. All 106 returned files were verified by type/mode/size/SHA-256/readback in the 2,608,322-byte archive SHA-256 `7419f5770975191bb8e3683eab18ec7c34f18a234131a54938ef147cb7c0eef3`, before exact four-blob Mac transfer. The certifi governed candidate universe is seven locks, four sources and the constraint, all under the same selected replacement.

The final focused run on this compatible graph completed native exit 0 in 465.037276 seconds, host exit 0: 1,033 complete JUnit cases, 1,028 passed, no failures/errors, and five unchanged intentional skips. The five source/constraint-style blocked-range cases apply only to pinned surfaces; their function AST equals the existing base, while current source floors, universal certifi witnesses and the on-by-default repo policy guard executed. Full 5,718 typed source/index/hook parity and original process absence were independently checked before all 36 raw members were returned and verified: 2,000,964-byte archive SHA-256 `8597245f8851c57161af94d6d72ccb7db3814b22d006f66341c80ad46a7742c3`.

The actual existing pre-push helper also completed policy exit 0 using the qualified installed pip-audit 2.10.1 on the 68-distribution runtime input. Its fresh unsuppressed native exit 1 retained all eight admitted Pillow findings; the separate ignored invocation exited 0. Certifi 2026.10.19 had no reported finding in that input. All 21 carrier hashes were bound before each invocation and promotion. The full raw/native pair and evidence were preserved in the verified 80-member, 2,479,377-byte archive SHA-256 `35ff1250e1402aee10d111c382cbc49a99765bf9264dc85507a966e5312b8beb`. This is the runtime helper result, not Git publication, complete CI, no-findings or Pillow remediation.

The remaining narrow final gates, actual publication, current-head hosted CI/security and numeric coverage >=97% remain PENDING until observed. Earlier failed preparations and focused runs remain preserved; no historical run is relabeled as current-head evidence.

The existing human conditional merge instruction persists only after fresh exact-head review/dispositions/mapping/seal/wait/strict readiness. No temporary exception grants merge/release/production authority, completes original 20+P01 or repairs the historical deadline miss.

ROOT must rerun the closed audit/eligibility predicate immediately before exact-head promotion/merge; older CI alone cannot establish that the wall-clock exception is still unexpired. No separate merge-wrapper mechanism is introduced.

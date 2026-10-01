# PR 2447 urllib3 remediation evidence owner

Status: repository candidate remediation evidence. Both native compiler stages,
committed runtime binding and independent exact-base replays are observed. The
current 21-carrier projection excludes every captured affected range at all eight
urllib3 occurrences. Focused validation results are recorded below; current PR-head
CI, image publication, merge and host outcomes remain separate pending rails.

## Authority and one-identity scope

The direct receiving-chat owner instruction consolidates all blocking CVEs in the
existing PR #2447 and explicitly retains urllib3 ownership here. The canonical
application dependency-remediation v2 remains unchanged (`AGENTS.md:2361`). This
continuation has one PyPI identity, `urllib3`, and one authored replacement action.
CVE count is not dependency identity count. The same replacement fixes the Medium
finding without admitting general Medium-severity remediation.

All original PR2-C01 through C20, transferred OpenSSL-C1 through C8 and additive
C21 through C25 remain individually required in criteria version
`OBS2A-combined-security-v9`. The complete PR has 37 paths including its canonical
mapping. The 11 urllib3 paths are the sole source, seven existing locks, existing
schema/guard and this security evidence owner. Candidate text, packet metadata,
scanner output and scope labels create no authority.

## Exact base and governed surfaces

Action base is `556ff01058950eb4627e742692d3c65108094eac`; PR merge-base is
`6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e`. The ordinary unpublished runtime intermediate commit is
`9b4095c7351cc067e07ad7db13c4d3acb179d28a`, whose sole parent is the action base.
Root observed native commit hooks exit 0 and a clean checkout. Its runtime blob
was independently extracted and compared byte-for-byte to actual and replay
constraints. Compiler transaction separation does not itself prove that Git commit
(`scripts/ci/compile_locked_python_requirements.py:1981`).

The exact-base registry and independent discovery both contain 21 carriers under
the supported Git-index requirement grammar. Base urllib3 is 2.7.0 in
`requirements.txt:201`, `requirements-docker-runtime.txt:269`,
`requirements-ci-lite.txt:401`, `requirements-dev.txt:275`,
`requirements-lock.txt:509`, `requirements-rag-vector.txt:118` and
`requirements-rag-vector-cpu.txt:118`. No direct source declaration exists at base.
The test, data and eval profiles positively lack urllib3; a missing, unreadable or
malformed file is not this absence observation.

The authored source floor is only `requirements.in:19`. Do not add gratuitous
source rows, constraints or dependencies to absent profiles. Independent current candidate discovery equals the canonical registry at all
21 carriers. The base/candidate carrier union remains 21, with no added or removed
carrier paths. The one new direct occurrence is the authored source floor; seven
existing lock occurrences are replaced. Every present occurrence is validated,
and all test/data/evals source and lock carriers positively remain absent. The
existing executable owners are
`scripts/ci/check_python_dependency_surfaces.py:386` and
`scripts/ci/dependabot_requirement_carriers.py:573`.

## Frozen acquisition and advisory reconciliation

The frozen reconciliation receipt was recorded at 2026-09-30 20:21:53 UTC. It binds
15 complete captured published vendor records, 18 affected intervals, the full
runtime audit with 68 dependency records and its three findings. No withheld or
future advisory completeness claim follows. Hashes identify retained bytes; they
do not execute commands, authenticate the human instruction or prove an outcome.
The acquisition receipt names the real parent tool calls and observed exits:

```text
gh api --paginate --slurp 'repos/urllib3/urllib3/security-advisories?per_page=100'
```

Observed exit: 0. The native paginated response retains one page and all 15
records. There is no separately captured HTTP-header proof claim. File write
observations in the receipt are explicitly filesystem observations, not independent
acquisition timestamps. Vendor publication/update dates remain distinct from the
reconciliation cutoff.

```text
python3 -m pip_audit --requirement requirements.txt --no-deps --disable-pip --strict --timeout 60 --format json --output artifacts/orchestration/urllib3_pr2447_20260930/runtime_audit_full_before.json
```

This ran through the activated approved primary interpreter, Python 3.13.14,
with pip-audit 2.10.1. Observed exit: 1. Raw summary:

```text
Found 3 known vulnerabilities in 1 package
```

The runtime input is the requirements lock, not the installed host environment.
The native required pre-push hook has the same audit semantics
(`.pre-commit-config.yaml:126`). Exactly three members are applicable at 2.7.0:
CVE-2026-97687 (HIGH), CVE-2026-97688 (MEDIUM), CVE-2026-97689 (HIGH). Each has
seven affected comparable base witnesses. Every other captured record excludes
2.7.0 and remains inside the universal head postcondition.

| Primary vendor record | Severity | Published / updated UTC | Complete affected ranges | Patched versions | Base applicability or disposition | Head range result |
| --- | --- | --- | --- | --- | --- | --- |
| [GHSA-2xpw-w6gg-jr37](https://github.com/urllib3/urllib3/security/advisories/GHSA-2xpw-w6gg-jr37) / CVE-2025-66471 | HIGH | 2025-12-05T15:26:59Z / 2025-12-05T15:27:00Z | `>=1.0,<2.6.0` | 2.6.0 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-34jh-p97f-mpxf](https://github.com/urllib3/urllib3/security/advisories/GHSA-34jh-p97f-mpxf) / CVE-2024-37891 | MEDIUM | 2024-06-17T17:21:51Z / 2024-06-17T17:21:51Z | `<=1.26.18`; `<=2.2.1` | 1.26.19; 2.2.2 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-38jv-5279-wg99](https://github.com/urllib3/urllib3/security/advisories/GHSA-38jv-5279-wg99) / CVE-2026-21441 | HIGH | 2026-01-07T16:30:42Z / 2026-01-07T16:30:42Z | `>=1.22,<2.6.3` | 2.6.3 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-48p4-8xcf-vxj5](https://github.com/urllib3/urllib3/security/advisories/GHSA-48p4-8xcf-vxj5) / CVE-2025-50182 | MEDIUM | 2025-06-18T14:11:14Z / 2025-06-18T14:11:15Z | `>=2.2.0,<2.5.0` | 2.5.0 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-5phf-pp7p-vc2r](https://github.com/urllib3/urllib3/security/advisories/GHSA-5phf-pp7p-vc2r) / CVE-2021-28363 | HIGH | 2021-03-15T15:07:32Z / 2021-03-15T15:45:11Z | `>=1.26.0,<=1.26.3` | >=1.26.4 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-8988-9cw3-xx77](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77) / CVE-2026-97687 | HIGH | 2026-09-15T19:42:08Z / 2026-09-29T15:29:27Z | `>=1.26.0, <2.8.0` | 2.8.0 | Affected: seven exact 2.7.0 pins | All eight candidate occurrences exclude every range |
| [GHSA-g4mx-q9vg-27p4](https://github.com/urllib3/urllib3/security/advisories/GHSA-g4mx-q9vg-27p4) / CVE-2023-45803 | MEDIUM | 2023-10-17T17:47:46Z / 2023-10-17T17:47:46Z | `>=2, <=2.0.6`; `<=1.26.17` | 2.0.7; 1.26.18 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-gh4c-6fx4-qh6g](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g) / CVE-2026-97688 | MEDIUM | 2026-09-15T19:42:59Z / 2026-09-29T15:31:39Z | `>=2.6.2, <2.8.0` | 2.8.0 | Affected: seven exact 2.7.0 pins | All eight candidate occurrences exclude every range |
| [GHSA-gm62-xv2j-4w53](https://github.com/urllib3/urllib3/security/advisories/GHSA-gm62-xv2j-4w53) / CVE-2025-66418 | HIGH | 2025-12-05T15:27:41Z / 2025-12-05T15:27:42Z | `>=1.24,<2.6.0` | 2.6.0 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-mf9v-mfxr-j63j](https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j) / CVE-2026-44432 | HIGH | 2026-05-07T16:34:01Z / 2026-05-07T16:34:02Z | `>=2.6.0, <2.7.0` | 2.7.0 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-pq67-6m6q-mj2v](https://github.com/urllib3/urllib3/security/advisories/GHSA-pq67-6m6q-mj2v) / CVE-2025-50181 | MEDIUM | 2025-06-18T14:10:47Z / 2025-06-18T14:10:47Z | `<2.5.0` | not stated | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-q2q7-5pp4-w6pg](https://github.com/urllib3/urllib3/security/advisories/GHSA-q2q7-5pp4-w6pg) / CVE-2021-33503 | MEDIUM | 2021-05-26T17:08:18Z / 2021-06-26T18:16:23Z | `<1.26.5` | >=1.26.5 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-qccp-gfcp-xxvc](https://github.com/urllib3/urllib3/security/advisories/GHSA-qccp-gfcp-xxvc) / CVE-2026-44431 | HIGH | 2026-05-07T16:33:54Z / 2026-05-07T16:33:54Z | `>=1.23, <2.7.0` | 2.7.0 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-v845-jxx5-vc9f](https://github.com/urllib3/urllib3/security/advisories/GHSA-v845-jxx5-vc9f) / CVE-2023-43804 | MEDIUM | 2023-10-02T17:25:14Z / 2023-10-02T17:25:14Z | `<=2.0.5,>2`; `<=1.26.16` | 2.0.6; 1.26.17 | Non-applicable: 2.7.0 above every affected upper boundary | All eight candidate occurrences exclude every range |
| [GHSA-vxq7-64xx-v4gw](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw) / CVE-2026-97689 | HIGH | 2026-09-15T19:42:30Z / 2026-09-29T15:34:16Z | `>=1.10.3, <2.8.0` | 2.8.0 | Affected: seven exact 2.7.0 pins | All eight candidate occurrences exclude every range |

No captured record is withdrawn. The three applicable records were published
2026-09-15 and updated 2026-09-29; older record dates and all complete source fields
remain in the unchanged raw vendor response and acquisition receipt. The empty
patched-version field for CVE-2025-50181 does not erase its `<2.5.0` interval.
Multi-range records retain every interval rather than choosing one convenient
upper boundary. Current deterministic guard data uses all 15 identifiers and
18 intervals, without freezing the historical lock graph.

Supporting authenticated CI run 36734183242, job 109953943533, head
`08b9b1b0641ee9064c4132e9b7f2467b1475b7d2`, reports the same three urllib3
findings on its owned runtime, Docker-runtime and vector locks. Its eight copied
JSON files and copy manifest retain source hashes; the foreign NOSEC worktree
was unchanged. This is supporting evidence from a different head and supplies
neither ownership nor current PR #2447 CI proof.

## Native replacement and independent replay

The exact authored action adds `urllib3>=2.8.0,<3.0.0` and selects
`UPGRADE_PACKAGES=urllib3==2.8.0`. Canonical compiler configuration is Python
3.13.14, pip 26.1.2, pip-tools 7.6.0 and packaging 25.0. No tooling or installed
environment update was performed. The credential-free package index is
`https://packages.pulseplate.app/root/pulseplate/+simple/`.

Resolve the approved interpreter in this owned linked worktree first. The worktree
has no local `.venv`; this resolver selects the validated approved primary
interpreter without installing or changing an environment:

```bash
TASK_2447_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
```

The following commands use that quoted absolute executable variable. Exact actual
argv, including the resolved interpreter path, is retained in the ignored native
command receipts; machine-local paths are not rendered in this tracked document.

```text
LOCK_PROFILES="runtime" UPGRADE_PACKAGES="urllib3==2.8.0" make VENV_PYTHON="$TASK_2447_PYTHON" requirements-locks
```

The shell command above shows the canonical operation. `TASK_2447_PYTHON` is the
absolute approved executable resolved by `scripts/hooks/repo_python.sh`; the exact
actual argv is retained locally in both native command receipts. Actual compilation exit: 0; independent exact-base export replay exit: 0.
Raw native output in both runs:

```text
Updated governed lock profile runtime: requirements.txt
```

Both complete runtime files are byte-identical. The full before/after JSON maps
contain 68 dependency records, 67 unchanged and exactly one semantic transition:

```json
{
  "added": [],
  "removed": [],
  "changed": {
    "urllib3": {
      "before": {"version": "2.7.0", "extras": [], "marker": null, "url": null},
      "after": {"version": "2.8.0", "extras": [], "marker": null, "url": null}
    }
  },
  "other_dependency_transitions": []
}
```

Every source/lock carrier other than the authored source and runtime output remains
byte-identical at this phase. The generated annotation now records the direct
security-floor owner. This nonsemantic annotation delta is recorded alongside the
complete file diff. No independently authored other-package action or solver
closure is admitted; the observed non-urllib3 semantic closure is empty.

The independent export starts from the action-base tree and original runtime
seed, with only the authored source bytes changed. It contains no `.git`, shares
no Git index/config/refs and removes all `GIT_*` variables from command-local
execution. Initial safe extraction rejected an unrelated agent-discovery symlink
before tracked edits, exit 1. The bounded export then retained all regular tracked
base files and explicitly recorded the 16 omitted discovery symlinks. Every native
compiler/input file was byte-bound; this is a regular-file compiler replay, not a
claim that every original pathname was reproduced.

The six constrained profiles were compiled only after that ordinary unpublished
runtime commit and independently extracted blob were bound. Both actual and
independent replay selected exactly `docker-runtime ci-lite dev aggregate
rag-vector rag-vector-cpu`, with the same upgrade target and interpreter. The
fresh exact-base regular-file replay export consumed the real committed runtime
constraint and all six original action-base output seeds. Both native transactions
exited 0 and every complete output file is byte-identical. No partial remediation
was pushed.

```text
LOCK_PROFILES="docker-runtime ci-lite dev aggregate rag-vector rag-vector-cpu" UPGRADE_PACKAGES="urllib3==2.8.0" make VENV_PYTHON="$TASK_2447_PYTHON" requirements-locks
```

Raw terminal lines from both transactions include:

```text
Updated governed lock profile docker-runtime: requirements-docker-runtime.txt
Updated governed lock profile aggregate: requirements-lock.txt
Updated governed lock profile rag-vector-cpu: requirements-rag-vector-cpu.txt
```

The full raw logs retain successful updates for all six profiles. Each complete
JSON before/after pin map has exactly one urllib3 transition and no other version,
extras, marker, URL or package-membership movement:

| Lock profile | Complete package records | Unchanged records | Sole transition | Replay bytes |
| --- | ---: | ---: | --- | --- |
| requirements-docker-runtime.txt | 59 | 58 | urllib3 2.7.0 to 2.8.0 | identical |
| requirements-ci-lite.txt | 104 | 103 | urllib3 2.7.0 to 2.8.0 | identical |
| requirements-dev.txt | 88 | 87 | urllib3 2.7.0 to 2.8.0 | identical |
| requirements-lock.txt | 135 | 134 | urllib3 2.7.0 to 2.8.0 | identical |
| requirements-rag-vector.txt | 35 | 34 | urllib3 2.7.0 to 2.8.0 | identical |
| requirements-rag-vector-cpu.txt | 35 | 34 | urllib3 2.7.0 to 2.8.0 | identical |

Across both stages there are seven generated pin replacements and the one authored
source-floor addition. The sole authored replacement intent is that source floor
and exact target; every generated lock delta is canonical replay-proven closure
of that intent. Other identity transitions are empty. The runtime source and
committed lock remained byte-identical throughout phase two.

## Postcondition and compatibility limits

Root reran the failing runtime audit with its original native flags after phase one.
Observed exit: 0; full JSON contains 68 dependency records and no known findings.
Raw summary:

```text
No known vulnerabilities found
```

This audit observation applies to the runtime lock only. Separately, independent
current discovery and native packaging comparison observed all eight source/pin
occurrences outside each of the 18 affected intervals, 144 comparisons total.
Focused guard results are recorded below. Ordinary final narrow/all-files hooks,
actual pre-push audit, current-head technical/security/image CI and complete
criterion review remain pending.
It does not prove installed-host remediation or a clean unsuppressed Docker scan.

The native package-index probe returned HTTP 200 and observed exact 2.8.0 artifacts
for requested 3.13/3.14 wheel-tag targets; it does not prove two interpreter tests.
The compiler independently validated artifact admissions and resolved offline.
The package index is distinct from an HTTPS forwarding proxy. The retained primary
TLS advisory describes corrected separation of explicit proxy TLS context and
identity settings from target-server settings. The documented legacy forwarding
configuration without `proxy_ssl_context` warns in 2.8; the `<3` source cap avoids
its documented 3.0 error boundary. Do not disable verification or add a public
index, trusted-host override, alternate resolver or another upgrade to obtain a pass.

The guard adds only existing blocked-range/fixed-floor data and current discovery.
It explicitly rejects 2.8 prereleases with the fixed stable floor: PEP 440 exclusive
`<2.8.0` alone does not reject `2.8.0rc1`. Optional present carriers retain strict
validation. The thin urllib3 wrapper rejects mixed source `===` operators; this is
an explicit bounded rule and does not claim the generic helper already rejected
that mixed form. Future authorized versions outside the captured affected ranges remain permitted;
this finite postcondition is not a global future-version safety claim.

## Focused local validation

```text
"$TASK_2447_PYTHON" -m pytest -q tests/test_dependency_security_guard.py
```

The approved resolved primary interpreter ran the same focused module. Initial
exit: 1. Two new nonregular-carrier controls exposed an overly strong discovery
assumption; their raw failure is retained:

```text
E   Failed: DID NOT RAISE RuntimeError
E   IsADirectoryError: [Errno 21] Is a directory
```

Familiar root carrier names are admitted by discovery without proving the current
file type. The thin urllib3 wrapper now explicitly rejects present symlink or
non-file carriers before calling the existing parser. The new controls assert
that exact `regular non-symlink` rejection rather than accepting broad exceptions.
The mitigation is at `tests/test_dependency_security_guard.py:3237`.
All 21 actual candidate carriers were positively rechecked as regular, nonsymlink
and readable, with identical bound bytes. This is a supported checkout observation,
not an atomic-read or hostile-concurrent-filesystem guarantee.

After the bounded fix and Black formatting, the same focused module exited 0.
Raw terminal progress includes:

```text
...ssss.....s........................................................... [ 70%]
........................................................................ [ 94%]
..................                                                       [100%]
```

Existing intentional skips remain unchanged; no new skip, xfail or hook bypass
was introduced. The original failed log and succeeding rerun are both retained.

```text
"$TASK_2447_PYTHON" scripts/ci/check_python_dependency_surfaces.py
```

Observed exit: 0. Raw result:

```text
PASS: Python dependency surfaces match the canonical contract.
```

The checker retains its documented warning-only matplotlib legacy-transition and
numpy transitive-owner observations. No ownership contract error was reported;
this change neither suppresses those observations nor authors another dependency
remediation action.

```text
"$TASK_2447_PYTHON" scripts/ci/check_docs_phase1_gates.py --files docs/security/PR_2447_URLLIB3_REMEDIATION.md
```

Observed initial exit: 0, `phase1-docs-gates: passed.` The final updated document is
rechecked by the same command; its terminal result is retained in the local
phase-two evidence. Final broad local/current-head/PR/image/host rails remain
separately pending as stated above.

## Retained evidence and remaining decisions

Local, ignored evidence under
`artifacts/orchestration/urllib3_pr2447_20260930/` retains
`source_acquisition_receipt.json`, `immutable_source_snapshot.json`, full vendor
and runtime audit JSON/logs, copied supporting CI, phase-one complete semantic
maps/diffs/native logs `phase1_result.json` and phase-two full semantic maps, seed binding, native logs,
byte comparisons and current carrier/advisory projection. References do not replace the
meaningful per-advisory and complete transition proof recorded above.

Original OpenSSL/Alertmanager precise temporary exceptions, review/expiry dates,
OPS dedicated coverage/selection, the existing 97% threshold and every original
monitoring requirement remain separate. This dependency work supplies no temporary
residual-risk acceptance, exact-head merge, Resend/secret/account action, host
activation, two received emails, scheduled checkpoint, Drive readback or production
T0 approval. Monitoring-only activation must preserve app, DB and TSDB identities.

The observed candidate-file postcondition is limited to this captured advisory
inventory and current governed regular carriers. Current PR-head CI, publication
and deployed-host claims require their own later evidence. A failure or unrelated
semantic transition stops the dependent claim; no skip,
suppression, tool/compiler/hook change or weakened gate is allowed. Unmerged owned
material can be abandoned through the ordinary branch workflow; vulnerable 2.7.0
must not be republished merely to manufacture a passing gate.

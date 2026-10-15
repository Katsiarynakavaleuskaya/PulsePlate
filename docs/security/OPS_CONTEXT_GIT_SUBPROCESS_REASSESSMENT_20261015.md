# OPS native Git subprocess reassessment — 2026-10-15

Criteria: `OPS-CONTEXT-NOSEC-REASSESSMENT-20261015/v1`, F1–F8.
Owner: security-auditor / dev-operator.
Receiver: PR [#2477](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2477),
branch `codex/dependency-native-runtime-remediation`.
The unpublished source commit is `33d6fe162e0bb4754eb262e5268a9f415095e710`.
Its focused receipts below remain source-lane observations; they are not integrated-head CI or readiness proof.
PR [#2397](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397)
is introduction provenance only; it does not authorize this reassessment or renewal.

## Observed failure and bounded repair

Canonical main CI [38718879738](https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/38718879738)
completed with `FAILURE` on main
`ea40bc78a433c4e0ab4333b4fbffa41b79349659`. The retained logs for Python
3.11/3.12/3.13 contain the same NoSec policy assertion at the two OPS sites.
The separate main qualification records this cause as an expired annotation
failure, not a job timeout; sibling cancellation does not waive the assertion.
Representative raw lines:

```text
E   - scripts/ops/ops_context_report.py:11: remove-by date is expired; extend only if no safe code fix exists
E   - scripts/ops/ops_context_report.py:229: remove-by date is expired; extend only if no safe code fix exists
FAILED tests/guards/test_nosec_policy_guard.py::test_nosec_policy_guard
```

The retained initial local red guard exited 1: three fixture controls passed and
the real repository assertion rejected exactly those two `2026-10-14` dates.
This document consumes those retained observations; the writer did not rerun
them during preparation. Source at the admitted base has SHA-256
`8868232d8b69267eaa44c5431bab0a7ff4da48de0b036fbf2da4814f6e6b2832`.

The repair changes only the two existing inline comments. The B404 explanation
now describes native commit delegation rather than claiming that no conceivable
safer implementation exists. Both annotations have hard remove-by `2026-10-21`.
The repair references are `PR-2477`; PR #2397 remains historical introduction
provenance in this document. No new suppressed site, rule or file is admitted.
Post-fix static comparison against the admitted base now establishes complete
executable AST equality, including location attributes, with only source lines
11 and 229 changed. The unchanged guards, allowlist and scanner settings were
also checked. Observed focused execution follows below; remaining PR lifecycle
and current-head evidence are still pending.

## Each retained site and the finite alternatives

| Site | Current individual justification | Required boundary |
| --- | --- | --- |
| B404, `scripts/ops/ops_context_report.py:11` | The standalone stdlib CLI imports subprocess to delegate commit recognition to its one native Git seam. | The only production call remains the bounded call at line 229; importing subprocess is not itself a no-risk guarantee. |
| B603, `scripts/ops/ops_context_report.py:229` | The call uses OS-managed absolute Git, fixed argv, explicit owning cwd and minimal environment, no shell, five-second timeout and exact SHA validation. | Preserve the concrete controls and constant public failure projection; no caller command or extra process seam is admitted. |

Removing annotations alone leaves the two observed native Bandit findings.
The existing safe context reader has no Git helper. Requiring a caller-supplied
SHA would replace native checkout identity with a caller claim. A private Git
reader would acquire symbolic/packed-ref, worktree and commit-object semantics
currently delegated to Git. A broader process/Git framework expands this stdlib
tool's dependencies and trust boundary; relocating the same call moves the
finding. None of these inspected alternatives establishes a smaller equivalent
safe replacement within this repair. This finite comparison is not a universal
claim that no safer design could exist.

## Threat assumptions and preserved controls

This is local operational reference tooling, not an exposed product endpoint
or host activation path. The relevant assets are checkout commit identity,
process integrity and public diagnostic confidentiality. Source and observation
files remain subject to the existing bounded readers and closed schemas;
this annotation reassessment does not change those recognizers.

`scripts/ops/ops_context_report.py:223` resolves Git through the fixed
`/usr/bin:/bin` search and rejects missing/nonabsolute results. The fixed query
is `--no-replace-objects rev-parse --verify HEAD^{commit}`; native Git owns commit
recognition. Its process receives the owning cwd and exactly `PATH`, `LC_ALL`,
`GIT_CONFIG_NOSYSTEM` and `GIT_CONFIG_GLOBAL`, not inherited credential/Git
override variables. The call uses no shell, captures output, has a five-second
timeout and accepts only successful ASCII lowercase 40-hex output. Failure
becomes `GIT_UNAVAILABLE`; `scripts/ops/ops_context_report.py:381` projects the
public CLI failure to empty stdout, constant stderr and exit 2.

Existing controls address caller fake PATH and missing-system fallback
(`tests/test_ops_context_report.py:779`, `:801`); hostile ambient Git state and
preservation of a separate disposable parent's config/index (`:612`); attached
and detached commit HEAD versus blob/tree/unborn/missing/dangling HEAD (`:735`);
exact process parameters (`:529`) and sanitized failures (`:574`). The observed
665-test four-tool producer below includes the complete owning OPS suite and
these behavioral/native controls; it is not a full application suite.

OS-managed directories, platform-managed symlink targets, native Git and the
owning local checkout remain trusted assumptions. An absolute path is not
binary authenticity proof; no shell is not universal process containment.
A commit SHA does not prove authorship, worktree cleanliness, deployed revision,
provider authentication or live service health. The timeout bounds this selected
call; it does not certify arbitrary hostile OS/Git behavior. The operational
contract remains `docs/deploy/OPERATIONAL_SIGNALS.md:574`.

## Current native scanner observations

Coordinator captures at `2026-10-15T11:43:57Z` scanned exactly
`./scripts/ops/ops_context_report.py`, 345 LOC, with no JSON errors:

| Native mode | Exit | Results | Skipped tests |
| --- | --- | --- | --- |
| Ordinary Bandit | 0 | `[]` | 2 |
| `--ignore-nosec` | 1 | Exactly B404:11 and B603:229; both LOW severity, HIGH confidence | 0 |

These are same-source baseline observations, not post-fix observations.
Ordinary silence means two named checks were suppressed, not no findings.
The unsuppressed exit 1 is expected only when the exact two identities, source
inventory and empty error set are present; another finding, omitted source or
scan/parse error fails reassessment. Native Bandit and the unchanged NoSec guard
retain their separate responsibilities. No guard, allowlist, Bandit setting,
dependency, workflow or application policy changes are proposed.

## Review window, removal and rollback

Manual review-by: **2026-10-20**; hard remove-by: **2026-10-21**, inclusive
under the unchanged guard's local `date.today()` semantics; October 22 rejects
the annotations. The receiver shortened the source proposal to respect the
operator's one-week limit. Manual review is tracked separately and is not
enforced by the date predicate. This calendar deadline is not a UTC instant
and grants no automatic renewal or permanent risk acceptance.

Remove or explicitly reassess both dispositions when the CLI/native identity
need is retired, a reviewed smaller helper establishes equivalent native
semantics and controls, process parameters/trust assumptions change, or new
scanner findings/failed owning controls invalidate this assessment. Expiry must
continue to fail closed. The existing follow-up owner remains
`docs/roadmap/BACKLOG_LEDGER.md:80`; its parent OPS item stays open.

Rollback is a normal bounded revert of this repair and its coupled documentation.
It restores the expired guard failure, which blocks readiness until corrected;
it never introduces an unchecked fallback, automatic renewal or ignored failure.
Separate human approval is still required for the concrete exact-head squash.

## Observed post-fix focused evidence

The source-lane Root inspected the actual three-path material before executing the focused
checks. The writer subsequently read their retained native JSON, logs and JUnit
and parsed the existing XML; this document update ran no suites or scans.
The positive NoSec/absolute-binary/repository-policy bundle exited 0 with
85 tests, zero failures, errors or skips. Its raw final stdout lines are:

```text
........................................................................ [ 84%]
.............                                                            [100%]
```

The native post-fix scan again selected exactly the one OPS source, 345 LOC,
with errors `[]`. Ordinary Bandit exited 0 with results `[]` and two skipped
tests; unsuppressed Bandit exited 1 with exactly LOW/HIGH B404:11 and B603:229
and no skipped tests. Captured JSON SHA-256 values respectively are
`374cd6c5cc13e5d171805742b2e6d0062b572f10d817c64c14abbec7b365d394`
and `2b6e3ea95f7981edcabc48a5dcd3ea73bc648507eb6f0c47f1427edbee07fac2`.
Source/cardinality/error checks bind this expected unsuppressed exit to those
two findings; it is not an ignored unexpected scanner failure or no-findings claim.
Noncontiguous raw JSON lines from the ordinary capture:

```text
  "errors": [],
      "skipped_tests": 2
  "results": []
```

The unsuppressed capture retains the two native identities (noncontiguous lines):

```text
  "errors": [],
      "test_id": "B404",
      "test_id": "B603",
```

The existing four-tool focused coverage producer exited 0 with 665 tests and
zero failures, errors or skips. XML contains exactly these four intended source
classes with nonempty executable-line inventories:

- `scripts/ops/ops_context_report.py`: 209 executable lines.
- `scripts/ops/resource_cost_report.py`: 434 executable lines.
- `scripts/ops/resource_evidence_report.py`: 588 executable lines.
- `scripts/ops/staging_runtime_diagnostics.py`: 215 executable lines.

The resulting XML SHA-256 is
`78f2cceffc765a14a41a0699225e2316c6d632c5e40ebef3721ed3e493fb78e1`.
OPS changed lines 11 and 229 each have one recorded hit. Native XML stdout:

```text
Wrote XML report to artifacts/orchestration/ops-context-nosec/coverage-ops-context.xml
```

The corrected native diff-cover invocation exited 0 using that same XML and the
unchanged 97% threshold. Its JSON establishes exactly two eligible changed
executable lines, zero missing lines and 100% eligible diff coverage; raw stdout:

```text
Total:   2 lines
Missing: 0 lines
Coverage: 100%
```

This is measured nonempty local diff coverage, not numeric N/A, a per-file
readiness threshold or application full-suite total coverage. The initial
`--json-report` invocation emitted a deprecation warning; its raw output was
retained. Replacing that CLI spelling with native `--format json:...` produced
the clean successful result using the same XML, without rerunning a suite.

Agent consistency and the initial docs Phase 1 invocation each exited 0:

```text
OK: agent docs and files are consistent.
phase1-docs-gates: passed.
```

These initial documentation checks predate this evidence update; dependent
checks must be refreshed as applicable. No backend-hook, Make, all-files,
premortem, Runner, PR/CI/review or merge success is inferred from focused proof.

The following are root's observed post-fix command arguments with one explicit
privacy substitution: `$VENV_PYTHON` replaces the actual private absolute
repo-approved interpreter path, and commands run from the owning repository
checkout. Other argument spellings/order are preserved. The resolver line
documents how to obtain that approved interpreter; it is not a claim about the
historical coordinator baseline invocation. Each command's observed exit is
listed immediately below; stdout/stderr capture redirects are outside argv.

```bash
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"
"$VENV_PYTHON" -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_repo_policy_guards.py --junitxml=artifacts/orchestration/ops-context-nosec/positive-guards.xml
export PYTHONPATH="$PWD:$PWD/tests"
"$VENV_PYTHON" -m coverage run --rcfile=/dev/null --branch --include=scripts/ops/ops_context_report.py,scripts/ops/staging_runtime_diagnostics.py,scripts/ops/resource_cost_report.py,scripts/ops/resource_evidence_report.py --data-file=artifacts/orchestration/ops-context-nosec/.coverage.ops-context -m pytest -q -p no:xdist tests/test_ops_context_report.py tests/test_staging_runtime_diagnostics.py tests/test_resource_cost_report.py tests/test_resource_evidence_report.py --junitxml=artifacts/orchestration/ops-context-nosec/focused-ops.xml
"$VENV_PYTHON" -m coverage xml --rcfile=/dev/null --data-file=artifacts/orchestration/ops-context-nosec/.coverage.ops-context -o artifacts/orchestration/ops-context-nosec/coverage-ops-context.xml
"$VENV_PYTHON" -m bandit -f json scripts/ops/ops_context_report.py
"$VENV_PYTHON" -m bandit --ignore-nosec -f json scripts/ops/ops_context_report.py
"$VENV_PYTHON" -m diff_cover.diff_cover_tool artifacts/orchestration/ops-context-nosec/coverage-ops-context.xml --compare-branch=origin/main --fail-under=97 --format json:artifacts/orchestration/ops-context-nosec/local-diff-coverage.json
```

Observed exits in command order after setup: guards 0; four-tool coverage run 0;
XML emission 0; ordinary Bandit 0; exact-inventory unsuppressed Bandit 1;
corrected diff-cover 0. The two test invocations are the observed 85-test guard
and 665-test focused tooling bundles; they are not a full application suite.

## Remaining evidence and authority

At the source-lane handoff, the applicable `make validate-changed`, all-files pre-commit,
actual-diff premortem, admitted oracle-only review, authenticated non-draft PR,
one post-open QA/Bug/Security pass, own current-head CI/security/governance,
native self-review, dispositions/seal, strict readiness and review wait window
were not established by that unpublished lane. The receiver verifies the
applicable integrated-head requirements through its existing PR #2477
workflow without restarting already completed roles. No full local verify is admitted.

Focused tooling coverage is not application full-suite total coverage. Local or
fix-PR success cannot establish healthy main: that requires a separately
authorized actual merge and its own observed current-main outcome. Legacy
reconciliation, dependency/CD recovery, host activation and operational
follow-ups retain their separate owners and are not closed by this repair.

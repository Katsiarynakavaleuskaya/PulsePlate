# Philosophy Epic V2 PR-3 Admission Dry-Run Packet

Date: 2026-05-21

Branch: `codex/philosophy-epic-v2-pr3-admission-dry-run`

Worktree: `worktrees/philosophy-epic-v2-pr3-admission-dry-run`

Base: `origin/main` at `101a6d2e6461cb86f23ff79458b9f0b36c4032ff`

## Goal

Create the Philosophy Epic V2 PR-3 admission oracle dry-run report and
verification-bundle adapter. This PR is governance and test infrastructure only:
it connects the PR-2 policy/oracle to a deterministic dry-run report that models
verification-bundle states without opening the semantic-cache gate.

## Scope

In scope:

- Canonical generated dry-run report:
  `docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json`
- Report schema:
  `docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.schema.json`
- Deterministic checker:
  `scripts/ci/check_philosophy_admission_dry_run.py`
- Focused tests for report determinism, schema guards, and Phase 1 docs routing
- Ledger, roadmap, and narrow agent guidance updates that require future
  Philosophy semantic-cache runtime work to cite PR-2 policy/oracle and the
  PR-3 dry-run report

Out of scope:

- No semantic-cache gate opening
- No runtime activation
- No Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI,
  frontend, iOS, `/insight`, connection-string, or cache-adapter changes
- No cache read, cache write, or serving decision
- No promotion of PDFs, design input, browser evidence, Experiment Runner output,
  or research output into runtime truth

## Coordinator Role Order

Pre-open role order:

1. `agent-coordinator`
2. `architecture-specialist`
3. `philosophy-agent`
4. `qa-engineer-agent`
5. `security-auditor`
6. `bug-hunter`

Post-open mandatory lane:

1. `qa-engineer-agent`
2. `bug-hunter`
3. `security-auditor` / `codex-security` style diff scan

No role may be skipped unless the coordinator updates this packet.

## Research Basis

External sources are reference-only and untrusted until translated into repo
contracts and tests. PR-3 uses them as design rationale, not runtime truth.

| Source | Design use in PR-3 |
| --- | --- |
| W3C PROV-DM: <https://www.w3.org/TR/prov-dm/> | Treat policy, oracle fixture, and dry-run report as traceable provenance entities derived from structured inputs. |
| Open Policy Agent decision logs: <https://www.openpolicyagent.org/docs/management-decision-logs> | Keep dry-run decisions auditable, structured, and reproducible from policy inputs. |
| NIST AI 600-1 Generative AI Profile: <https://doi.org/10.6028/NIST.AI.600-1> | Treat red-team and adversarial brainstorming as governance evidence, not shipped behavior. |
| Barr et al., "The Oracle Problem in Software Testing: A Survey": <https://discovery.ucl.ac.uk/id/eprint/1471263/> | Use specification and metamorphic-style controls to reduce oracle-gap false greens. |

## Dry-Run Decision Contract

The report must keep these invariants:

- `gate_status` remains `closed`
- `runtime_allowed` remains `false`
- `implementation_allowed` remains `false`
- every dry-run row has `cache_read_allowed=false`,
  `cache_write_allowed=false`, and `serving_allowed=false`
- a passed verification bundle is necessary for future semantic-cache
  consideration, but never sufficient while the semantic-cache gate remains
  closed; the dry-run decision stays `gate_closed_deferred`
- missing, failed, and warning verification bundles remain denied in the dry-run
  adapter

The dry-run adapter may cite `core/verification/contracts.py` as the canonical
VerificationBundle shape, but it must not import runtime cache code, providers,
network clients, DB, OpenAPI, frontend, iOS, or `/insight`.

## Red-Team / Brainstorming Protocol

Reviewers should test whether the report can be misread as runtime approval:

- Does any row imply that cache reads, writes, or serving are allowed?
- Does a passed verification bundle bypass the closed gate?
- Does the report make Redis, GPTCache, embeddings, vector search, provider
  clients, or cache adapters look selected?
- Can missing or warning verification bundles appear accepted?
- Can research, PDFs, design input, or Experiment Runner artifacts override repo
  policy, oracle, and verification-bundle truth?

If a same-class review wave appears, fix the dry-run report schema, checker, or
policy/oracle relation first. Do not patch a one-off sentence without updating
the deterministic source of the failure.

## Experiment Runner Evidence

PR-3 uses the governed `oracle_only_governance_reviewer` mode only. The runner is
advisory and may not mutate candidates, update fixed mappings, resolve threads,
or claim readiness. If its local result artifact shapes validation, mapping,
review disposition, or commit decisions, the commit must use:

```text
Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>
```

The immutable oracles for this lane are the dry-run checker, PR-2 policy/oracle
drift check, focused pytest bundle, agent consistency check, `make
validate-changed`, and `pre-commit run --all-files`.

## Premortem Closure Contract

`pulseplate-premortem-risk-review` is mandatory before readiness. Every finding
must close as:

- `FIXED`: real code, docs, tests, scripts, or governance fix with evidence
- `NOT-A-BUG`: repo evidence proving no change is needed
- `DEFERRED`: backlog link plus PR-body follow-up

No advisory-only finding may be silently ignored. Runtime/code findings from
premortem, QA, bug-hunter, security-auditor, CodeRabbit, Cubic, Sourcery, or
`codex-security` style review must be fixed in code/tests before fixed mapping
or thread resolution.

## Premortem Findings And Closure

- `FIXED` - The dry-run report could be mistaken for gate-open runtime approval.
  Evidence: the report schema and checker require `gate_status: closed`,
  `runtime_allowed: false`, `implementation_allowed: false`, and every dry-run
  decision keeps cache read/write/serving permissions false.
- `FIXED` - A passed verification bundle could be treated as sufficient for
  cache admission. Evidence: the generated report and tests force the passed
  bundle decision to remain `gate_closed_deferred`.
- `FIXED` - PR-2 policy/oracle and PR-3 report could drift independently.
  Evidence: `check_philosophy_admission_dry_run.py --check` validates the PR-2
  policy, policy schema, oracle fixture, report schema, and generated report
  together.
- `FIXED` - CI docs routing could miss report/schema edits. Evidence: Phase 1
  docs gates include the dry-run report path and schema glob, and workflow
  regression tests guard that routing.
- `FIXED` - Future runtime Philosophy semantic-cache PRs could cite PR-2 but
  bypass the verification-bundle adapter. Evidence: the roadmap, ledger, and
  role-agent notes require future runtime work to cite both PR-2 policy/oracle
  and PR-3 dry-run report before any gate-open proposal.

## Validation Plan

Focused gates:

```bash
python3 scripts/ci/check_semantic_cache_gate.py --check-philosophy-admission-oracle-drift
python3 scripts/ci/check_philosophy_admission_dry_run.py --check
../../.venv/bin/python -m pytest -q tests/test_philosophy_admission_dry_run_report.py tests/test_philosophy_admission_policy_oracle.py tests/test_philosophy_semantic_cache_admission_contract.py tests/test_semantic_cache_gate.py tests/core/evidence/test_admission.py
python3 scripts/orchestration/check_agent_consistency.py
DEV_PYTHON=../../.venv/bin/python VENV_PYTHON=../../.venv/bin/python make validate-changed
pre-commit run --all-files
```

GraphMap:

```bash
python tools/graphmap/build_graph.py --out docs/graph/graph.json
python tools/graphmap/build_graph.py --out /tmp/graph_tmp.json
shasum -a 256 docs/graph/graph.json /tmp/graph_tmp.json
```

Post-open gates:

- `task_bootstrap.py --pr-phase post_open_review`
- mandatory `qa-engineer-agent -> bug-hunter`
- security / `codex-security` style scan of `origin/main...HEAD`
- fixed mapping only after underlying fixes/dispositions are complete

## Definition Of Done

- Dry-run report and schema validate fail-closed
- Dry-run report is byte-stable from PR-2 policy/oracle inputs
- Missing, failed, warning, and passed verification-bundle states have explicit
  dry-run decisions
- Passed bundle remains `gate_closed_deferred`
- Every row keeps cache read/write/serving false
- Semantic-cache gate remains closed and runtime/implementation false
- No runtime/cache/provider/client/OpenAPI/DB/frontend/iOS surfaces are touched
- Premortem and role-agent findings are fixed or formally dispositioned before
  readiness claims

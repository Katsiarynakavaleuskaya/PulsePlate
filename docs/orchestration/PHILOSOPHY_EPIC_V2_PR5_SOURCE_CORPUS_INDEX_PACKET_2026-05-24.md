# Philosophy Epic V2 PR-5 Source Corpus Index Packet

**Date:** 2026-05-24
**Branch:** `codex/philosophy-epic-v2-pr5-source-corpus-index`
**Worktree:** `worktrees/philosophy-epic-v2-pr5-source-corpus-index`
**Task packet:** `artifacts/orchestration/task_packets/9883839145a4.json`
**Scope:** docs/governance/test-only source corpus index

## Goal

Create the Philosophy Epic V2 source-corpus index that preserves the six
operator-provided philosophy PDFs as design evidence and maps them to existing
repo contracts, research anchors, and future handoff candidates.

PR-5 is not PR-A2 and does not start AI/runtime prerequisite work. It does not
change product runtime behavior, OpenAPI, DB, frontend, iOS, providers,
`/insight`, cache I/O, Redis, GPTCache, embeddings, vector search, or
semantic-cache machine markers.

## Source Truth

The committed source index is:

- `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json`
- `docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json`

The operator-provided PDFs are local evidence inputs only. The committed index
uses sanitized titles, page counts, SHA-256 fingerprints, paraphrased summaries,
and repo links. It must not commit PDF full text, absolute local paths, or
credential-like URLs.

| Source id | Pages | Focus |
| --- | ---: | --- |
| `analytic_linguistic_audit` | 22 | Analytical and linguistic philosophy audit, falsification, speech acts, meaning-as-use |
| `leibniz_information_theory` | 12 | Leibniz, information theory, temporal semantics, uncertainty |
| `philosophy_cbt_correlation_matrix` | 13 | Philosophy systems mapped to CBT-style wellness coaching affordances |
| `philosophy_cbt_plan_adaptation_epic` | 24 | Philosophy-to-CBT-to-plan-adaptation design evidence |
| `philosophy_full_roadmap` | 19 | Full philosophy-line map and extended roadmap |
| `socratic_method_rag_llm_semantic_cache_cbt` | 12 | Socratic questioning, RAG/LLM reliability, CBT reflection |

## Repo Truth And Handoff

Repo truth overrides the PDFs when there is a conflict:

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/orchestration/PHILOSOPHY_EPIC_V2_PR0_PACKET_2026-05-13.md`
- `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md`
- `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`
- `docs/orchestration/contracts/PHILOSOPHY_ADMISSION_DRY_RUN_REPORT.json`
- `docs/orchestration/contracts/PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT.json`
- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- `docs/roadmap/BACKLOG_LEDGER.md`

PR-5 hands off a governed source index to later philosophy packets. Later
runtime or semantic-cache work must still cite PR-2 policy oracle, PR-3 dry-run
report, PR-4 precondition report, PR #1789 alignment-rule schema, and the
runtime prerequisite train before any separate gate-open review can be
considered.

## Coordinator Start

Startup follows repo canon:

1. `check_preflight.py --mode analyze`
2. `start_pr_lane.sh`
3. `task_bootstrap.py --pr-phase pre_open`
4. `agent-coordinator`
5. `qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/9883839145a4.json --pretty`
6. explicit role-agent dispatch in the order below

Current main CI was in progress when the lane started. The operator explicitly
approved opening work while monitoring main. This is a start-timing exception
only and is not merge-readiness evidence.

## Coordinator Role Order

The packet exposes the full coordinator-declared role order so orchestration
dispatch can parse it. Agents provide read-only review, routing, and findings;
they do not replace coordinator-owned implementation.

1. `agent-coordinator` - scope lock, role assignment, synthesis, and DoD.
2. `philosophy-agent` - source taxonomy, claim semantics, and philosophy-lane boundary review.
3. `web-research-agent` - bounded research register and external-source caveats.
4. `architecture-specialist` - ownership, schema, guard, and no-runtime boundary review.
5. `qa-engineer-agent` - deterministic guard, tests, and validation evidence review.
6. `security-auditor` - local path, credential-like URL, runtime/cache drift review.
7. `bug-hunter` - false-green, source omission, and marker-drift review.
8. `cursor-specialist-agent` - coordinator/dispatch evidence and agent workflow review.

## Role-Agent Execution Evidence

Bootstrap packet creation and the Qoder dispatch manifest are routing evidence
only; they do not count as role-agent execution. For this PR-5 lane, role
subagents were explicitly launched after dispatch:

| Role | Subagent id | Result | Closure |
| --- | --- | --- | --- |
| `agent-coordinator` | `019e5b71-1f9d-7482-8423-4c154c797a41` | start gate and route ownership | Packet records the coordinator-defined role order, scope, risks, validation, and DoD. |
| `philosophy-agent` | `019e5b82-3c45-78c0-9a1f-9f9c256e4d50` | `ISSUES` | `FIXED`: source rows now require source-specific interdisciplinary theme and discipline rails plus wellness-only boundary checks. |
| `web-research-agent` | `019e5b82-5e1b-7f31-8cdc-c60b82df5d96` | `ISSUES` | `FIXED`: `research_basis` is now an exact allowlisted evidence register with access date, verification status, and boundary notes; PubMed CBT is clinical-context caution only. |
| `architecture-specialist` | `019e5b82-82ea-7140-8022-683445c0ef2e` | `ISSUES` | `FIXED`: CI docs Phase1 routing now runs the PR-5 source-corpus checker for PR-5 file changes; schema shape is fail-closed. |
| `qa-engineer-agent` | `019e5b82-bdf8-75f1-9226-e42f7567813e` | `ISSUES` | `FIXED`: touched-file content scanning, docs Phase1 regression, source-order, hash, schema-drift, and research-basis negative tests were added. |
| `security-auditor` | `019e5b82-ee00-7542-a0d2-05f12e38ee1e` | `ISSUES` | `FIXED`: the checker no longer relies on `assert` for runtime validation and scans every passed PR-5 artifact for local paths and credential-like tokens. |
| `bug-hunter` | `019e5b83-06ca-7642-a917-83575adb02fd` | `ISSUES` | `FIXED`: schema/runtime flag drift, source order drift, SHA drift, and CI false-green gaps are covered by deterministic tests. |
| `cursor-specialist-agent` | `019e5b83-26a2-76f2-8642-2a9171f015ef` | `ISSUES` | `FIXED`: this packet now records explicit role execution, bootstrap-vs-execution separation, and Experiment Runner evidence rules. |

## Post-Open Role Order

After the ready-for-review PR opens, run:

1. `task_bootstrap.py --pr-phase post_open_review`
2. `qa-engineer-agent`
3. `bug-hunter`
4. `security-auditor`
5. codex-security-style diff scan

Fix real docs/code/tests first. Only then update
`docs/review/PR_<N>_FIXED_MAPPING.md` and the PR body mirror.

Post-open execution evidence for PR #1822:

- Post-open task packet: `artifacts/orchestration/task_packets/e1615fc0a12d.json`
- Dispatch manifest:
  `qoder_dispatch_bridge.py --packet artifacts/orchestration/task_packets/e1615fc0a12d.json --pretty`
- Mandatory post-open sequence returned by dispatch:
  `qa-engineer-agent -> bug-hunter -> security-auditor`
- Coordinator disposition: post-open route is correct and PR #1822 is
  ready-for-review, not draft; the first post-open fix is governance-only
  mapping/body synchronization after the CodeRabbit capacity-skip comment.

## Research Basis

External sources are rationale-only and do not override repo truth:

- Stanford Encyclopedia of Philosophy, Socrates:
  https://plato.stanford.edu/entries/socrates/
- Stanford Encyclopedia of Philosophy, Leibniz:
  https://plato.stanford.edu/entries/leibniz/
- Stanford Encyclopedia of Philosophy, Wittgenstein:
  https://plato.stanford.edu/entries/wittgenstein/
- Stanford Encyclopedia of Philosophy, Semantic Conceptions of Information:
  https://plato.stanford.edu/entries/information-semantic/
- NIST AI 600-1:
  https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- PubMed Socratic questioning CBT context:
  https://pubmed.ncbi.nlm.nih.gov/32755910/

The canonical JSON records each external source as an evidence-register row
with `source_kind=external_research_reference`, `accessed_on=2026-05-24`,
`verification_status=verified_stable_public_reference`, and
`use=rationale_only_not_runtime_truth`. The PubMed CBT row is explicitly
clinical-context caution only; it is not product efficacy, therapy, diagnosis,
treatment, or runtime authority.

## Oracle Requirement

PR-5 readiness requires:

```bash
python3 scripts/ci/check_philosophy_source_corpus_index.py --check \
  --files docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json \
  docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json \
  docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md \
  docs/roadmap/BACKLOG_LEDGER.md \
  docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md \
  scripts/ci/check_philosophy_source_corpus_index.py \
  scripts/ci/check_docs_phase1_gates.py \
  tests/test_philosophy_source_corpus_index.py \
  .github/workflows/ci.yml \
  tests/test_ci_workflow_pr_size_governance_contract.py
```

The oracle proves:

- all six PDFs are represented with stable IDs, page counts, and SHA-256
  fingerprints;
- committed artifacts contain no absolute local paths or credential-like URLs;
- semantic-cache roadmap markers remain closed/false;
- PR-4 precondition report still blocks runtime handoff;
- every source row keeps cache read, cache write, serving, runtime activation,
  provider call, and `/insight` route-change flags false;
- PR-5 touched paths stay out of runtime, provider, DB, OpenAPI, frontend, iOS,
  and cache I/O surfaces.
- research-basis rows are exact allowlisted rationale-only references, not
  arbitrary HTTPS links.

## Premortem Closure Contract

`pulseplate-premortem-risk-review` is mandatory before readiness. Every finding
must close as `FIXED`, `NOT-A-BUG`, or `DEFERRED`.

Premortem frame:

> It is 6 months from now. PR-5 failed because the source corpus looked
> canonical but either leaked evidence, weakened semantic-cache closure, or let
> arbitrary research references masquerade as repo truth.

Initial premortem findings:

- `FIXED`: PDF intake could leak local paths or credential-like extraction
  artifacts. Evidence: `check_philosophy_source_corpus_index.py` rejects local
  paths and credential-like tokens, with focused tests.
- `FIXED`: the corpus index could be misread as runtime truth. Evidence: source
  policy marks PDFs as design evidence, and every source keeps runtime/cache
  flags false.
- `FIXED`: later agents could omit one of the six PDFs. Evidence: the checker
  requires exact source IDs, stable page counts, hashes, and total page count.
- `FIXED`: PR-5 could drift from the closed semantic-cache roadmap. Evidence:
  the checker validates roadmap markers and the PR-4 precondition report.
- `FIXED`: arbitrary external references could be added as generic HTTPS
  sources. Evidence: the checker enforces exact `research_basis` ids, URLs,
  rails, access dates, verification status, boundary notes, and rationale-only
  use.
- `FIXED`: schema drift could weaken runtime false flags without changing the
  index. Evidence: schema exact-shape checks require every runtime flag property
  to remain `const: false`.
- `FIXED`: raw PDF fingerprints could be mistaken for secrets by pre-commit and
  CI scanners. Evidence: source fingerprints use grouped SHA-256 form, and
  `detect-secrets` passes without adding new high-entropy findings for the
  source-corpus artifacts.

Decision: `proceed with changes`. The changes above are implemented in the
guard, schema, CI routing, tests, packet, and fixed-mapping artifact. This is
not a runtime/gate-open PR.

Pre-merge checklist:

1. Source corpus oracle passes on all PR-5 touched files.
2. Docs Phase1 gates pass on corpus, packet, ledger, and roadmap changes.
3. Semantic-cache gate and PR-4 precondition report remain closed/false.
4. `pre-commit run --all-files` passes without new secret findings.
5. Post-open QA, bug-hunter, security-auditor, and codex-security-style scan
   have no unresolved actionables.

## Oracle Recommendation Closure

The web-research, architecture, QA, security, and bug-hunter review wave
produced the following oracle-hardening recommendations. Each is closed in real
code, docs, tests, or CI routing:

- `FIXED`: credibility/stability of external research basis was documented but
  not guarded. Evidence: `research_basis` is now an exact allowlisted register
  with stable ids, labels, URLs, rails, source kind, access date, verification
  status, boundary note, and rationale-only use.
- `FIXED`: PubMed CBT evidence could be read as product efficacy or therapy
  authority. Evidence: its boundary note is clinical-context caution only and
  explicitly excludes product efficacy, therapy, diagnosis, treatment, and
  runtime authority.
- `FIXED`: CI could miss PR-5 oracle checks. Evidence: `.github/workflows/ci.yml`
  sets `PR5_SOURCE_CORPUS_CHANGED=1` for source-corpus-specific contract,
  packet, guard, and test surfaces, then runs
  `check_philosophy_source_corpus_index.py` against all touched files.
- `FIXED`: schema drift could produce a false green. Evidence: the checker
  validates exact top-level schema keys, source fields, source-policy fields,
  runtime flag `const: false` properties, semantic-cache marker properties, and
  research-basis fields.
- `FIXED`: artifact leakage could hide outside JSON/schema. Evidence:
  `validate_file_contents()` scans every existing file passed via `--files`.
- `FIXED`: type and assertion issues could be missed. Evidence: the checker no
  longer relies on `assert` in validation paths, and pre-push mypy changed-file
  hooks passed.
- `FIXED`: PR-5 CI routing could trigger on unrelated backlog/runtime PRs.
  Evidence: `PR5_SOURCE_CORPUS_CHANGED` is limited to source-corpus-specific
  contract, packet, guard, and test surfaces.
- `FIXED`: source taxonomy and locale drift could pass. Evidence: the checker
  validates per-source `source_family` and `language` values.
- `FIXED`: binary docs artifacts could make leakage scanning brittle. Evidence:
  the touched-file scanner skips binary/non-UTF-8 files while continuing to scan
  text artifacts.
- `FIXED`: repo truth and no-runtime scope arrays could drift. Evidence:
  `repo_truth_links` and `out_of_scope_paths` now have exact deterministic
  checks and regression coverage.
- `FIXED`: final QA/bug-hunter refresh found schema-type false-greens for
  source arrays, source scalar fields, runtime flag object shape, and runtime
  flag boolean properties. Evidence: `check_philosophy_source_corpus_index.py`
  now validates those schema types and `tests/test_philosophy_source_corpus_index.py`
  carries targeted regressions.

## Experiment Runner

Use Experiment Runner only as `oracle_only_governance_reviewer`. If the runner
materially shapes the checker, tests, packet, mapping, or readiness decision,
the commit must include:

`Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

PR-5 Experiment Runner readiness evidence:

- Result artifact: `artifacts/orchestration/experiments/results/exp-16755634fdf6.json`
- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Contribution kind: `oracle_review`
- Co-author required: `true`
- Source diff applied: `false` because the implementation was already committed
  before the oracle review, keeping the runner within its `max_changed_files`
  policy while validating committed repo truth.
- Oracle commands executed: 3 / 3, all return code `0`
  - `check_philosophy_source_corpus_index.py --check`
  - `check_docs_phase1_gates.py --files ...`
  - focused pytest for source-corpus, docs Phase1, and CI workflow routing tests

Earlier local artifact `exp-c195db826c77` was rejected because the oracle-only
context surface omitted several PR-5 changed files. It is not readiness
evidence; the accepted artifact above is the canonical PR-5 runner evidence.

## Validation

Focused gates:

```bash
python3 scripts/ci/check_semantic_cache_gate.py
python3 scripts/ci/check_philosophy_source_corpus_index.py --check
python3 scripts/ci/check_docs_phase1_gates.py --files \
  docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json \
  docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json \
  docs/orchestration/PHILOSOPHY_EPIC_V2_PR5_SOURCE_CORPUS_INDEX_PACKET_2026-05-24.md \
  docs/roadmap/BACKLOG_LEDGER.md \
  docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md
python3 -m pytest -q tests/test_philosophy_source_corpus_index.py tests/test_semantic_cache_gate.py
python3 scripts/orchestration/check_agent_consistency.py
DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed
PATH=.venv/bin:$PATH pre-commit run --all-files
```

Root `AGENTS.md` remains the merge-readiness authority. This lane uses the
operator-approved narrow-gate path instead of a full local `make verify`;
readiness still requires documented local narrow gates, current-head CI,
review-thread disposition, and strict merge-readiness checks.

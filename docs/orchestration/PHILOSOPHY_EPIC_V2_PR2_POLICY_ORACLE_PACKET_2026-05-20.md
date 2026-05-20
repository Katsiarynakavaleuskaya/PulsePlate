# Philosophy Epic V2 PR-2 Policy Oracle Packet

Date: 2026-05-20

Branch: `codex/philosophy-epic-v2-pr2-policy-oracle`

Worktree: `worktrees/philosophy-epic-v2-pr2-policy-oracle`

## Goal

Create the Philosophy Epic V2 PR-2 admission policy spec generator / claim-family
oracle. This PR is governance and test infrastructure only. It makes the PR-1
semantic-cache admission forbidden-claim policy data-driven, generates a
deterministic oracle fixture, and fails closed when policy, schema, checker, or
fixture drift would recreate review loops.

## Scope

In scope:

- Canonical JSON policy:
  `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`
- Policy JSON schema:
  `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json`
- Generated oracle fixture:
  `tests/fixtures/orchestration/philosophy_admission_claim_oracle.json`
- Deterministic generator/check path in `scripts/ci/check_semantic_cache_gate.py`
- Policy/oracle regression tests
- Ledger and narrow role-agent guidance updates needed to prevent repeated
  semantic claim-loop fixes

Out of scope:

- No semantic-cache gate opening
- No runtime activation
- No Redis, GPTCache, embeddings, vector search, provider/client, DB, OpenAPI,
  frontend, iOS, `/insight`, connection-string, or cache-adapter changes
- No promotion of PDFs, design input, browser evidence, or research output into
  runtime truth

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
3. security / `codex-security` style diff scan

No role may be skipped unless the coordinator updates this packet.

## Research Basis

External sources are reference-only and untrusted until translated into repo
contracts and tests. The PR-2 policy uses them as design rationale, not runtime
truth.

| Source | Design use in PR-2 |
| --- | --- |
| Kuhn, "A Survey and Classification of Controlled Natural Languages", ACL Anthology, 2014: <https://aclanthology.org/J14-1005/> | Treat admission claims as controlled language with finite subject, predicate, polarity, modal, and temporal axes. |
| Claessen and Hughes, "QuickCheck: a lightweight tool for random testing of Haskell programs", ICFP 2000: <https://doi.org/10.1145/351240.351266> | Generate deterministic property-style cases from claim-family dimensions instead of adding one-off reviewer phrases. |
| Chen et al., "Metamorphic Testing: A Review of Challenges and Opportunities", ACM Computing Surveys 2018: <https://i.cs.hku.hk/~tse/Papers/2010s/hlmtCSUR.html> | Pair forbidden claims with allowed negative controls to expose oracle-gap regressions. |
| Open Policy Agent policy language docs: <https://www.openpolicyagent.org/docs/policy-language> | Keep policy inputs as structured auditable data, while the repo checker remains Python/stdlib. |
| NIST AI 600-1 Generative AI Profile: <https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf> | Treat red-team brainstorming as adversarial coverage before readiness, not as shipped behavior. |
| Stanford Encyclopedia of Philosophy, "Temporal Logic": <https://plato.stanford.edu/entries/logic-temporal/> and "Modal Logic": <https://plato.stanford.edu/entries/logic-modal/> | Encode temporal/modal drift such as `now`, `still`, `became`, `has been`, `will`, `may`, `must`, and `required to`. |

## Policy Model

The canonical policy data defines:

- claim-family id
- risk rail
- canonical meaning
- forbidden polarity
- detector labels
- controlled subjects
- assertive predicates
- modal predicates
- temporal predicates
- seed regressions from PR-1 review loops
- allowed negative controls

The JSON policy stores no arbitrary regex. The checker compiles exact,
deterministic `re.escape` patterns from generated oracle claims and preserves the
existing PR-1 static detector safety net.

## Oracle Boundary Clarification

PR-2 uses `oracle` in the narrow governance/CI sense: a deterministic generated
fixture plus checker path that adjudicates admission-policy claims. It is not a
new LLM, RAG, semantic-cache, Experiment Runner, or runtime oracle component.

The current oracle analysis reinforces the Experiment Runner invariant
`O intersect M = empty`: immutable oracle surfaces must not become mutable patch
targets. PR-2 keeps that discipline by separating:

1. mutable policy source:
   `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json`
2. generated oracle fixture:
   `tests/fixtures/orchestration/philosophy_admission_claim_oracle.json`
3. deterministic adjudicator:
   `scripts/ci/check_semantic_cache_gate.py`

Philosophical, RAG, or LLM work may generate hypotheses and reviewer wording, but
admission truth is constrained by the policy/spec/generator and the deterministic
checker. This PR does not alter Experiment Runner, immutable experiment oracles,
promotion mechanics, or runtime semantic-cache behavior. Future Experiment Runner
oracle-manifest work belongs in a separate coordinator-owned lane.

## Review-Loop Root Cause Closure

The current oracle analysis treats PR-1761's repeated review waves as a
semantic-detection architecture problem, not as an Experiment Runner problem.
PR-2 closes that failure mode with deterministic governance infrastructure:

| Review-loop root cause | PR-2 countermeasure |
| --- | --- |
| Hand-expanded wording regexes produced new gaps for each tense, modality, subject order, or provider phrase. | Claim families now live in canonical policy JSON, and the oracle generator expands modal, temporal, provider, and polarity dimensions from data. |
| Allowed negative controls could be checked only against the current family and miss false positives from another detector. | Oracle tests now fail any allowed case that triggers any downstream Philosophy admission error. |
| Policy, schema, and oracle fixtures could drift because only some changed paths reached docs gates. | CI/docs wiring passes the policy JSON, schema, and generated oracle fixture together, and workflow-contract tests guard that routing. |
| Oracle regeneration could overwrite fixtures even after policy validation had already failed. | Write mode is fail-closed: it writes only after policy/schema/oracle validation has no errors and only under `tests/fixtures/orchestration`. |
| Review governance could become a separate loop of stale or ambiguous proof. | Findings are fixed in code/tests first, then mapped in `docs/review/PR_1777_FIXED_MAPPING.md`; broader Experiment Runner oracle-manifest and mapping-reachability work stay separate lanes. |

## Red-Team / Brainstorming Protocol

For each claim family, reviewers should ask:

- What sentence would wrongly make the gate open, live, approved, serving, or
  runtime-enabled?
- What modal operator changes the force of the claim: `can`, `may`, `must`,
  `should`, `would`, `required to`, or `has to`?
- What temporal operator changes status: `now`, `still`, `remains`, `became`,
  `has been`, `will`, or `future`?
- What exact negative-control sentence should remain allowed?

If a new review wave finds another same-class phrase, fix the policy family or
generator relation first, then regenerate the oracle fixture and add the
regression there. Do not add another isolated regex branch as the primary fix.

## Premortem Closure Contract

`pulseplate-premortem-risk-review` is mandatory before readiness. Every finding
must close as:

- `FIXED`: real code/docs/tests/governance fix with evidence
- `NOT-A-BUG`: repo evidence proving no change is needed
- `DEFERRED`: backlog link plus PR-body follow-up

No advisory-only finding may be silently ignored. Runtime/code findings from
premortem, QA, bug-hunter, security-auditor, CodeRabbit, Cubic, Sourcery, or
`codex-security` style review must be fixed in code/tests before fixed mapping
or thread resolution.

## Premortem Findings And Closure

- `FIXED` - Same-class review waves could continue if new comments are patched
  with isolated regex branches. Evidence: canonical policy data plus generated
  oracle fixture now own the claim-family dimensions, and philosophy/QA agent
  guidance requires policy-spec-first review before one-off regex changes.
- `FIXED` - Policy, schema, fixture, and downstream docs could drift apart.
  Evidence: `check_semantic_cache_gate.py` validates policy/schema/oracle drift,
  `check_docs_phase1_gates.py` wires the policy artifacts into PR-scoped docs
  gates, and `tests/test_philosophy_admission_policy_oracle.py` rejects fixture
  drift.
- `FIXED` - A governance PR could accidentally imply runtime semantic-cache
  activation. Evidence: the policy requires `gate_status: closed`,
  `runtime_allowed: false`, and `implementation_allowed: false`; the packet keeps
  Redis, GPTCache, embeddings, providers, clients, DB, OpenAPI, frontend, iOS,
  `/insight`, and cache adapters out of scope.
- `FIXED` - Oracle generation could become an unsafe write primitive. Evidence:
  write mode is confined to `tests/fixtures/orchestration`, and the regression
  test rejects writing the oracle fixture outside that root.
- `FIXED` - The term `oracle` could be confused with an Experiment Runner or LLM
  runtime authority. Evidence: the Oracle Boundary Clarification above separates
  mutable policy source, generated fixture, deterministic checker, Experiment
  Runner oracles, and future runtime promotion.

## Validation Plan

Focused gates:

```bash
python3 scripts/ci/check_semantic_cache_gate.py --check-philosophy-admission-oracle-drift
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_philosophy_admission_policy_oracle.py tests/test_philosophy_semantic_cache_admission_contract.py tests/test_semantic_cache_gate.py
python3 scripts/orchestration/check_agent_consistency.py
DEV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed
pre-commit run --all-files
```

Post-open gates:

- `task_bootstrap.py --pr-phase post_open_review`
- mandatory `qa-engineer-agent -> bug-hunter`
- security / `codex-security` style scan of `origin/main...HEAD`
- fixed mapping only after underlying fixes/dispositions are complete

## Definition Of Done

- Policy JSON and schema validate fail-closed
- Generated oracle fixture is byte-stable and checked by CI-local tooling
- Every claim family has forbidden and allowed cases
- Downstream Philosophy docs continue to reject forbidden admission claims
- The semantic-cache gate remains closed and runtime/implementation false
- No runtime/cache/provider/client surfaces are touched
- Premortem and role-agent findings are closed before readiness claims

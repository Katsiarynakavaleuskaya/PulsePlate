# PR #2068 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068

Branch: `codex/experiment-runner-local-active-hypothesis-pr2`

## Scope

PR #2068 adds local active creative-hypothesis intake for the Experiment Runner
creative-context lane.

In scope:

- Sanitized local operator/model hypothesis JSON intake.
- Repo-owned validation, normalization, fingerprinting, and stable hypothesis
  IDs.
- 3-5 bounded hypotheses with concrete targets, tests/oracles, risk notes,
  falsifiers, negative controls, cross-domain analogies, and human approval.
- Coordinator dispatch only, with critique/refine mode and no mutation
  authority.
- Proposal-only learning-loop records with bounded metrics and raw model
  artifact redaction.
- Premortem governance that requires real diff-specific code/schema/test/guard
  closure for production, security, business, user, and project-development
  failure modes.

Out of scope:

- GitHub App workflow dispatch or Actions write permissions.
- Repo-side provider/model calls.
- Patch generation, branch mutation, PR writes, thread resolution authority, or
  merge-readiness claims from creative artifacts.
- Product runtime, OpenAPI, client, DB, semantic-cache, graph-truth, Slack, or
  local HTTP model-adapter changes.

## Lane Start Provenance

- Branch: `codex/experiment-runner-local-active-hypothesis-pr2`
- Base: `main`
- PR: `#2068`
- Experiment Runner artifact:
  `artifacts/orchestration/experiments/results/experiment_runner_local_active_hypothesis_pr2_oracle_result_followup_fixed_head_after_redaction_scan.json`
- Codex Security scan policy: one scan per material diff; the operator launched
  the follow-up scan and no additional scan is run for this body/mapping update.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2068`.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed once for the
  material diff.
- [x] `pulseplate-pr-review` completed.
- [x] CodeRabbit actionable review comments checked and dispositioned.
- [x] Sourcery actionable review comments checked and dispositioned.
- [x] Cubic actionable review comments checked and dispositioned.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: See `Review Comment Dispositions` below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3516531918 -> 33b3a599cf4524c2b35bb6ca4b09afe3e5b5e470
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3516531920 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518307341 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518352549 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518352556 -> 5646787ad2286544d55db08cee8a908c3e17b72a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518352564 -> 5646787ad2286544d55db08cee8a908c3e17b72a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568918 -> 5646787ad2286544d55db08cee8a908c3e17b72a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568921 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568926 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568928 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568929 -> 442b7d81cf5d4ac6fbd5031068b635e2a5627714

Disposition: NOT-A-BUG
Evidence: `tests/test_agent_learning_loop.py` already covered the requested
failure-pattern secondary-metric branch on the current diff before the bot
comment; CodeRabbit also marked the thread addressed in commit `7db17f6`.
Reason: This was stale reviewer feedback against an already-covered branch, so
no new post-comment code change was needed and mapping it to the pre-comment
commit as `FIXED` would violate commit-after-comment governance.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3516541188

Disposition: NOT-A-BUG
Evidence: Sourcery review `4621614380` contains only a weekly diff-character
rate-limit message and no actionable code, test, or docs finding.
Reason: A rate-limit status is external tool availability, not a defect in this
PR diff. There is no Sourcery actionable to fix in the branch.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#pullrequestreview-4621614380

Disposition: NOT-A-BUG
Evidence: Cubic-generated PR body summary contains generated release-note style
content and no inline actionable review thread requiring code or docs changes.
Reason: The generated summary is advisory metadata; actionable review comments
are handled separately in this mapping.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068

## Review Comment Dispositions

### Codex: Spaced Raw-Model Labels

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3516531918
Commit: 33b3a599cf4524c2b35bb6ca4b09afe3e5b5e470
Evidence:

- `scripts/orchestration/agent_learning_loop.py` redacts separator variants
  such as raw prompt/response, provider payload, candidate patch, and patch
  hunks before proposal validation or promotion.
- `tests/test_agent_learning_loop.py` covers marker variants and multiline
  patch-hunk redaction.

### Codex: Exact Runtime / Workflow Root Targets

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3516531920
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- `scripts/orchestration/experiment_runner_pr_creative_context_contract.py`
  rejects exact product/runtime roots and `.github/workflows`.
- `tests/test_experiment_runner_pr_creative_context.py` covers exact root and
  mixed valid+forbidden target rejection.

### CodeRabbit: Failure-Pattern Secondary Metrics

Disposition: NOT-A-BUG
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3516541188
Evidence:

- `tests/test_agent_learning_loop.py` includes failure-pattern metric-shape
  coverage for missing `premortem_code_closure_rate` /
  `review_actionable_escape_reduction`.
- CodeRabbit marked the comment addressed in commit `7db17f6`.

Reason: The current branch already covered the requested failure branch before
the review comment. No post-comment code change was required; the branch is not
missing the requested coverage.

### CodeRabbit: Null Learning Metrics

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518307341
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- `scripts/orchestration/agent_learning_loop.py` now rejects
  `learning_metrics is None`, non-string primary/window fields, and duplicate
  primary metric entries.
- `tests/test_agent_learning_loop.py` covers these validator-integrity cases.

### Codex: Raw Model Payload Labels In Intake

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518352549
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- Runtime leak detection rejects raw model payload text in operator-intake
  fields.
- The operator-intake JSON Schema mirrors the raw model payload deny pattern.
- `tests/test_experiment_runner_pr_creative_context.py` covers runtime and
  schema rejection.

### Codex: Normalized Intake Provenance

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518352556
Commit: 5646787ad2286544d55db08cee8a908c3e17b72a
Evidence:

- `ingest-model-hypotheses --output <path>` now writes validated normalized
  `model_intake.json` beside the packet by default.
- `prepare --context-map ... --model-intake ...` writes normalized
  `model_intake.json` into the prepared local artifact directory.
- CLI tests assert the packet `source_model_intake_fingerprint` matches the
  emitted normalized intake artifact.

### Codex: Missing Dispatch Agent Slug Shape

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518352564
Commit: 5646787ad2286544d55db08cee8a908c3e17b72a
Evidence:

- Runtime routing and coordinator-dispatch validators now require
  `missing_agent_capabilities` entries to match PulsePlate agent-slug shape.
- Routing and dispatch JSON Schemas mirror the stricter slug pattern.
- `tests/test_experiment_runner_pr_creative_context.py` rejects malformed
  missing capability names for both artifacts.

### Codex: Dot-Separated Raw Model Labels

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568918
Commit: 5646787ad2286544d55db08cee8a908c3e17b72a
Evidence:

- Runtime leak detection now treats dots as unsafe separators for raw/provider
  and chain-of-thought marker labels.
- The operator-intake schema mirrors the same dot-separated deny patterns.
- Tests cover `raw.prompt`, `provider.payload`, and `chain.of.thought`.

### Codex: Patch-Hunk Redaction In Intake Schema

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568921
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- The operator-intake schema rejects `@@`, `+++ a/`, `--- a/`,
  `candidate patch`, and `raw model payload` markers.
- Tests assert schema unsafe-text coverage for those patch markers.

### Codex: Repo-Root Hypothesis Targets

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568926
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- Runtime path validation rejects `.`, `*`, and `**`.
- Operator `target_surfaces` must have every entry be a concrete allowed target.
- Tests cover broad root targets mixed with valid targets.

### Codex: Learning Loop On Semantic Triggers

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568928
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- `scripts/orchestration/task_bootstrap.py` now requires the learning-loop gate
  when repeated-pattern semantic trigger evidence exists even outside the
  docs/orchestration lane.
- `tests/test_task_bootstrap.py` covers the non-doc semantic trigger case.

### Codex: Routed Analogy Alternatives

Disposition: FIXED
Comment:
https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2068#discussion_r3518568929
Commit: 442b7d81cf5d4ac6fbd5031068b635e2a5627714
Evidence:

- Cross-domain routing records missing analogy specialists only when no
  candidate for that analogy can be routed.
- Tests assert registered nutrition specialists are routed without reporting
  unregistered alternatives as missing.

## Post-Open Role Findings

### QA Engineer Agent

Disposition: NOT-A-BUG
Evidence: Post-open QA reported prior acceptance findings closed by explicit
tests for PR2 patch eligibility, dispatch negatives, path redaction, and
metrics/schema negatives.
Reason: No remaining QA defect required a new code or docs change after those
closures.

### Bug Hunter

Disposition: NOT-A-BUG
Evidence: Bug-hunter re-check found repo-owned intake identity/count derivation,
redaction, and fingerprint findings closed.
Reason: No escaped regression remained in the local active-intake scope after
the targeted fixes.

### Security Auditor

Disposition: NOT-A-BUG
Evidence: Security-auditor pass found no repo-provider, GitHub-write,
workflow-dispatch, product-runtime, semantic-cache, or mutation-authority path
introduced by this PR.
Reason: The reviewed security boundaries are enforced by contract flags,
validators, schemas, and negative tests.

### Codex Security

Disposition: FIXED
Evidence:

- Codex Security scan `1bc8ca9f-50da-4ea9-b1d6-7e6b8f3bede8` on prior head
  `55834334041dbce54db1af1b5c6d9e599390cb36` found one low learning-loop
  redaction gap.
- Commit `33b3a599cf4524c2b35bb6ca4b09afe3e5b5e470` fixed the gap with code
  and tests.
- Follow-up scan `b9048f29-a60a-4bbe-94d6-f77b2ea85ded` on fixed head
  `33b3a599cf4524c2b35bb6ca4b09afe3e5b5e470` completed with 0 findings and 6/6
  reviewed rows.

## Premortem Findings

- Raw model marker leakage - FIXED by runtime/schema redaction and tests.
- Product/runtime/workflow target smuggling - FIXED by exact-root, descendant,
  repo-root, and every-target validators plus tests.
- Decorative cross-domain analogies - FIXED by specialist routing or missing
  capability recording.
- Context fingerprint drift - FIXED by `prepare --context-map --model-intake`
  and normalized intake sidecar provenance.
- Learning-loop metrics corruption - FIXED by strict metric object/type/shape
  validation and tests.
- Premortem docs-only closure drift - FIXED by skill/router/bootstrap wording
  and learning-loop trigger coverage requiring real code/schema/test/guard
  closure for non-doc risks.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/experiment_runner_local_active_hypothesis_pr2_oracle_result_followup_fixed_head_after_redaction_scan.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Oracle commands: 2
- Oracle command return codes: 0, 0
- Shared tree untouched: true
- Promotion ready: false
- Co-author required: false for this oracle-only follow-up.

## Local Evidence

- PASS:
  `.venv/bin/python -m pytest -q tests/test_experiment_runner_pr_creative_context.py tests/test_agent_learning_loop.py tests/test_task_bootstrap.py tests/test_skill_router.py`
- PASS:
  `python3 -m py_compile scripts/orchestration/experiment_runner_pr_creative_context.py scripts/orchestration/experiment_runner_pr_creative_context_contract.py scripts/orchestration/task_bootstrap.py`
- PASS:
  `python3 -m json.tool docs/orchestration/contracts/creative_hypothesis_operator_model_intake.v1.schema.json`
- PASS:
  `python3 -m json.tool docs/orchestration/contracts/creative_hypothesis_agent_routing.v1.schema.json`
- PASS:
  `python3 -m json.tool docs/orchestration/contracts/creative_hypothesis_coordinator_dispatch.v1.schema.json`
- PASS: commit hook for `5646787ad2286544d55db08cee8a908c3e17b72a`,
  including black, ruff, type-hint check, changed-file Bandit, changed-file
  backend tests, detect-secrets, and commitizen.

Full local `make verify` was intentionally not run under the repository local
budget rule. Current-head CI and strict merge-readiness gates remain required
before readiness.

## Merge Readiness

Not claimed. Current-head CI, final bot/review status, PR body Phase2 gate,
review-thread disposition guard, `make validate-changed`,
`pre-commit run --all-files`, and strict merge-readiness checks still govern
merge.

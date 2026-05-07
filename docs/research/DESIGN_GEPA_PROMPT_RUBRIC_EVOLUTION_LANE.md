<!-- markdownlint-disable MD013 -->
# Design GEPA Prompt/Rubric Evolution Lane

## Summary

This lane defines a bounded, GEPA-compatible research and evaluation process for evolving Design Intelligence prompts and rubrics.

It is process guidance only. It does not implement GEPA runtime behavior, online optimization, production agent self-modification, live product prompt mutation, or design/runtime changes.

## Why PR-8 Exists Now After PR-7

PR-7 added the repeatable design-agent workflow and PR template. PR-8 is the next separate slice because prompt and rubric evolution needs its own safety boundary before any future experimentation can influence design-impacting work.

This sequencing keeps workflow governance first, then research/eval guidance second. It prevents prompt optimization work from being hidden inside web, iOS, token, Figma, Canva, or Storybook changes.

## Scope

- Define how future Design Intelligence prompt and rubric candidates may be evaluated against curated fixtures.
- Define allowed and forbidden mutation units.
- Define candidate, fixture, and trace expectations for later reviewed work.
- Define promotion and rollback rules for any future prompt/rubric changes.
- Keep all outputs non-canonical until a later reviewed PR promotes a concrete change.

## Non-Goals

- No runtime web, iOS, backend, OpenAPI, or product-flow mutation.
- No `/tokens` edits.
- No manual edits to generated mirrors.
- No Figma or Canva writes.
- No Storybook configuration changes.
- No screenshots, videos, runtime/product traces, binary assets, or App Store assets.
- No online prompt optimization against live users.
- No autonomous merge, deployment, or production self-modification.
- No GEPA runtime engine, package dependency, or service integration.

## Source-Of-Truth Hierarchy

Canonical truth remains in the repository:

1. Repo code, docs, tests, root and scoped `AGENTS.md`, and runbooks.
2. `/tokens` as token authoring truth.
3. Generated mirrors as derived artifacts produced by canonical tooling.
4. UI vocabulary, backend/OpenAPI contracts, and runtime code.

Reference and evidence layers remain non-canonical:

- `DESIGN.md`.
- Reference manifests.
- Screen evidence packs.
- Design scorecards.
- Web acceptance briefs.
- iOS audits.
- Prompt outputs, GEPA-inspired eval traces, and generated briefs.

Prompt outputs, evolved rubrics, eval summaries, and GEPA-inspired traces are never runtime or design truth by themselves. They can only inform a later reviewed PR that changes repo-owned docs, tooling, tests, or research/eval fixtures within an explicitly approved non-runtime scope. Any runtime implementation work requires a separate non-PR-8 packet, separate reviewed PR, and explicit files/tests/rollback scope.

## GEPA-Compatible Lane Definition

For PulsePlate, "GEPA-compatible" means an offline research/eval process that can compare prompt and rubric candidates over curated fixtures and produce reviewable evidence.

The lane may:

- propose prompt or rubric candidates;
- run deterministic or recorded eval fixtures;
- compare candidate behavior against repo-owned acceptance criteria;
- emit committed eval trace records for review;
- recommend promotion, rejection, or follow-up work.

The lane may not:

- mutate production prompts automatically;
- write to runtime product flows;
- override repo source truth;
- change design tokens, generated mirrors, Figma, Canva, or Storybook;
- create self-modifying production agents.

## Allowed Mutation Units

Future reviewed PRs may mutate only explicitly scoped research/eval artifacts, such as:

- prompt templates used in offline Design Intelligence experiments;
- rubric criteria, rubric labels, or rubric weights for offline evaluation;
- eval instructions and fixture metadata;
- deterministic docs/tests that validate the research lane boundaries;
- orchestration packets that declare a specific eval run and bounded promotion path.

Each mutation must name the owning file, expected behavior, validation command, reviewer role, rollback path, and reason it does not create runtime truth.

## Forbidden Mutation Units

This lane forbids mutation of:

- runtime web code;
- runtime iOS code;
- backend, OpenAPI, billing, auth, StoreKit, HealthKit, entitlement, nutrition, BMI, or coaching truth;
- `/tokens`;
- generated mirrors, including frontend token mirrors and iOS generated token files;
- Figma and Canva assets or remote designs;
- Storybook configuration;
- screenshots, videos, runtime/product traces, binary assets, release assets, or external infrastructure;
- live product prompts, live agent policies, or online user flows.

## Curated Eval Fixture Policy

Fixtures must be committed, reviewable, deterministic, and small enough to inspect in a PR. Fixture records should describe:

- fixture id;
- source files or evidence layer inputs;
- allowed prompt/rubric candidate ids;
- expected review dimensions;
- disallowed authority claims;
- safety notes;
- owner and rollback path.

Fixtures must not contain secrets, production user data, private health data, or unreviewed external copyrighted payloads. External references remain reference-only and require source metadata if they are used at all.

## Prompt/Rubric Candidate Schema

Candidate records should be explicit enough for deterministic review:

```json
{
  "candidate_id": "design-pr8-example",
  "kind": "prompt_template",
  "owner": "design-intelligence",
  "input_fixtures": ["fixture-design-agent-boundary"],
  "changed_units": ["rubric.criteria.scope_boundary"],
  "repo_truth_statement": "repo code/docs/tests and tokens remain canonical",
  "promotion_target": "none_without_later_reviewed_pr",
  "rollback": "drop candidate and retain current rubric"
}
```

The schema is illustrative for future PRs. It is not a committed runtime contract in this PR.

## Eval Trace Schema

Trace records should make review decisions reproducible without making outputs canonical:

```json
{
  "trace_id": "trace-design-pr8-example",
  "candidate_id": "design-pr8-example",
  "fixture_id": "fixture-design-agent-boundary",
  "result": "review_required",
  "safety_findings": ["no_runtime_mutation"],
  "promotion_recommendation": "do_not_promote_without_reviewed_pr",
  "reviewer_notes": "Evidence remains advisory and does not override repo truth."
}
```

Trace output is evidence only. It cannot update product behavior, design truth, or agent policy without a later reviewed PR.

## Safety Gates

Every future prompt/rubric evolution PR must prove:

- repo truth remains canonical;
- `/tokens` remain token authoring truth;
- generated mirrors remain derived artifacts;
- prompt outputs are evidence only;
- Figma, Canva, Storybook, and external references cannot override repo truth;
- no runtime or product-flow mutation is hidden in research docs;
- no secrets, user data, or production telemetry are introduced;
- premortem reviewed the actual diff and real defects were fixed before mapping;
- bug-hunter reviewed scope creep, runtime drift, and generated mirror drift.

## Promotion Rules

A candidate may be promoted only through a later reviewed PR that:

- names the exact artifact being promoted;
- names the exact files touched;
- proves the change remains within the approved lane;
- includes deterministic tests or docs guards;
- records review dispositions in `docs/review/PR_<N>_FIXED_MAPPING.md`;
- preserves source-of-truth hierarchy;
- includes rollback instructions.

No prompt or rubric candidate can self-promote, auto-merge, or mutate a live product flow.

## Rollback Model

Rollback is file-based:

- revert the research/eval docs or candidate files from the promoting PR;
- remove any associated deterministic docs guard added for that candidate;
- preserve canonical repo truth and runtime behavior;
- document the rollback reason in the follow-up PR or review mapping if review comments required it.

Because this PR adds only research/process guidance and a docs guard, rollback is a docs/test revert with no runtime rollback required.

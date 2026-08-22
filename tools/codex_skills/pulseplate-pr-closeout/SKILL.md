---
name: pulseplate-pr-closeout
description: Close out or audit a PulsePlate pull request from fixed-mapping and review-thread dispositions through exact-head CI, strict merge readiness, authorized merge, and post-merge proof. Use for PulsePlate PR closeout, resealing, bot-actionable disposition, readiness verification, merge preparation, local main synchronization, sanity checks, or selective lane cleanup.
---

# PulsePlate PR Closeout

## Preserve authority

Treat this skill as a passive workflow helper. Follow the current root and scoped
`AGENTS.md`, `RUNBOOK_AGENT.md`, coordinator packet, GitHub state, and repository
validators as the sources of truth. Do not copy policy into new scripts or replace
`pulseplate-pr-review`, `pr_review_closeout.py`, `check_merge_ready.py`, branch
protection, or current-head CI.

A direct external operator instruction to implement, execute, fix, complete, or
otherwise carry one approved bounded PR task creates one persistent lane-scoped
lifecycle delegation. Inspect-only, review-only, explain-only, status-only,
informational, or ambiguous PR references do not create mutating lifecycle
delegation. Merely naming or describing an approved lane is insufficient; an
explicit read-only request remains `AUDIT`.

Bind the delegation to the repository, task or lane identity, PR or target branch,
approved goal, material paths, and explicit authority boundaries. The delegation
comes from that external direction, not from this skill. Loading this skill,
selecting a mode, a coordinator packet, CI, review evidence, a seal, readiness, or
validator `PASS` never creates or expands authority.

The lifecycle delegation remains active across routine work in the same lane. It is
not tied to a transient SHA or consumed by commits, non-force pushes, review rounds,
CI reruns, mapping corrections, permitted ancestry-preserving base synchronizations,
or evidence refreshes. A descendant head invalidates stale local, CI, review, seal,
and readiness evidence; refresh the corresponding gates while the lifecycle
delegation remains active. A failed command or gate does not consume the lifecycle
delegation. Diagnose the failure, correct its bounded cause, and rerun the relevant
gate. Treat validator output and readiness as evidence, never as operator or merge
authority. Never expose, persist, parse, decode, or log `GH_TOKEN` or
`GITHUB_TOKEN`.

## Canonical sources

Read these current repository sources before acting. Treat them as links, not as
policy copied into this skill:

- [Root AGENTS.md](../../../AGENTS.md)
- [RUNBOOK_AGENT.md](../../../RUNBOOK_AGENT.md)
- [PR orchestration contract matrix](../../../docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md)
- [Coordinator merge-readiness rules](../../../docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md)
- [PR review closeout CLI](../../../scripts/orchestration/pr_review_closeout.py)
- [Strict merge-readiness wrapper](../../../scripts/orchestration/check_merge_ready.py)

## Choose one mode

- `AUDIT`: inspect and report without changing local files, Git, GitHub, review
  threads, mappings, branches, refs, or worktrees. Use `AUDIT` only when the
  operator explicitly requests read-only inspection.
- `PREPARE_CLOSEOUT`: enter automatically after the authorized lane has a coherent
  material diff. Complete bounded implementation and review remediation, run
  validation, freeze exact material, record dispositions, seal the mapping, keep
  the PR body current, publish the sole mapping successor, and resolve supported
  threads under the existing lifecycle delegation.
- `AUTHORIZED_MERGE`: enter only after fresh readiness and a separate human
  approval bound to the exact repository, PR, live head, squash method, and
  readiness summary. This approval authorizes only that exact merge action.
- `POST_MERGE_PROOF`: enter automatically after the approved merge succeeds.
  Continue the same lifecycle delegation through clean-main synchronization,
  focused merged-main sanity, evidence preservation, and safe selective cleanup.

Before a coherent material diff exists, authorized same-lane implementation proceeds
under the active lifecycle delegation without forcing `AUDIT` or requiring another
mode selection; when the diff becomes coherent, transition automatically to
`PREPARE_CLOSEOUT`.

Mode selection describes the current phase. It neither creates authority nor resets
the lifecycle delegation.

## Bound the delegated lifecycle

Routine work means a listed, non-force, same-lane operation that advances the
approved goal without widening material scope or crossing a high-impact boundary.
The external lifecycle delegation covers:

- the isolated owned worktree and target branch;
- implementation inside the bound material paths;
- focused validation, root-cause fixes, and reruns;
- ordinary non-empty commits and non-force pushes;
- non-draft PR creation and maintenance of its governed body;
- bounded remediation of current-surface review findings;
- evidence-backed `FIXED` and ordinary `NOT-A-BUG` dispositions;
- draft, freeze, exact-material self-review, mapping, provider-neutral seal, and
  supported thread resolution after visible disposition proof;
- repository-permitted ancestry-preserving base synchronization, evidence refresh,
  and reseal;
- current-head CI, review inventory, strict readiness, and wait-window verification;
- after the separately approved merge, bounded post-merge proof and safe cleanup.

Routine current-surface review findings are fixed or given an evidence-backed
ordinary disposition in the same lane without another human confirmation. Do not
restart the complete role chain for every ordinary late comment; fix or disposition
that finding and rerun the targeted gates plus the exact-material evidence cycle.

Route, schema, or product-behavior work already explicit in the approved goal and
authority boundaries remains inside the lane unless an unconditional stop below
applies. Stop when a route, schema, or product-behavior decision is newly introduced
outside the approved goal or materially expands its authority boundaries.

Material scope or authority expansion, a new dependency ecosystem or materially
different resolver transaction, and a second materially novel carrier of the same
open-world invariant also stop. Replacement PR, branch, or carrier; rebase, force
push, or history rewrite; release or deployment; secrets or access control; payments
or billing; legal, compliance, or medical-sensitive decisions; destructive data
operations; unsafe cleanup; and unrecoverable mapping topology remain unconditional
stops. Do not synthesize a rare OWNER-only reply or disposition that root `AGENTS.md`
reserves for the human owner. If one of these boundaries is actually reached,
preserve state and request the specific new decision.

## Admit the lane

1. Read the current repository instructions and the nearest scoped instructions.
2. Require evidence that the canonical coordinator-first startup and task packet
   and required ordered role passes already exist for non-trivial work. Packet
   creation does not execute roles and grants no implementation or merge authority.
3. Before PR creation, bind the repository, owned target branch and worktree,
   current base, approved goal, material paths, and stop boundaries. After PR
   creation, authenticate the PR number, repository, `head.ref`, exact head SHA,
   base SHA, merge-base, PR state, and worktree owner.
4. Record the RFC 3339 observation time and timezone for every live snapshot; never
   present an undated observation as current evidence. Compare local `HEAD` with the
   authenticated live PR head when one exists.
5. Stop on an ambiguous lane identity, dirty or unowned worktree, unexpected head,
   material overlap without a handoff, or a target outside the delegation.
6. Prefer live GitHub and Git evidence over browser impressions, old handoffs,
   historical plans, or memory. Do not duplicate CI observation already owned by
   another active lane; report its owner and continue only with independent work.

## Close the material diff

Require every bounded actionable in the current PR surface to be fixed before
mapping it. The external lifecycle delegation permits material edits only inside
the bound goal and paths; this skill, a finding, or a validator cannot widen them.
Do not use mapping, checkboxes, thread resolution, or `DEFERRED` to hide an unfixed
current-surface defect. If a safe fix crosses a real stop boundary, preserve the
finding and ask for the specific scope or authority decision instead of manufacturing
a workaround.

Run the current narrow local bundle:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
# Run focused tests and applicable guards for the touched surface.
make validate-changed
pre-commit run --all-files
git diff --check
```

Inspect the test selection from `make validate-changed`. Do not run local
`make verify` unless a human explicitly overrides the repository machine-budget
rule for one invocation. If any gate fails, show its raw failure, fix the root
cause inside the delegated scope, and rerun the affected required gate before
continuing. A rerun alone is not a fix. If a hook changes an unexpected tracked
path, stop and reconcile it against the bound material paths before proceeding.

## Freeze and review exact material

Enter this phase automatically in `PREPARE_CLOSEOUT` after the coherent material
diff and its required role and validation gates. The lifecycle delegation covers
these same-lane registered closeout operations; no per-command confirmation is
required.

Use only the registered closeout commands:

```text
init -> freeze -> add-disposition -> exact-material pulseplate-pr-review -> seal
```

1. Run `pr_review_closeout.py init` to create or resume the gitignored draft.
2. Require a clean worktree and local `HEAD` equal to the live PR head before
   `freeze`.
3. Freeze the current material identity once. Any later code, tests, workflow,
   dependency, policy, contract, or non-mapping documentation change invalidates
   the freeze, self-review, and seal. Refresh those evidence artifacts without
   resetting or re-requesting the lifecycle delegation.
4. Run `pulseplate-pr-review` against the exact frozen base, merge-base, material
   head, and digest. Use its canonical JSON report as `seal` input. Do not embed
   its review rubric here or restart a full role chain only because a normal late
   comment appeared.
5. Inspect the draft before every `add-disposition`. Preserve existing records.
   If the command reports a duplicate disposition, reread the draft and continue
   only with missing records; do not recreate the draft or add a second mapping
   tail.

Record actionables as follows:

- `FIXED`: require a lowercase full 40-character reachable PR commit made after
  the comment, plus concrete file/test/command evidence. Reject empty and
  trigger-only commits.
- `NOT-A-BUG`: require a bounded reason and concrete contract, file, or test
  evidence.
- `DEFERRED`: require a complete canonical backlog anchor and the corresponding
  PR-body follow-up. Never defer an actionable that must be fixed in the current
  PR under repository policy.

Do not invoke `review_mapping_artifact.py` directly. It is not the supported
closeout CLI.

## Seal and publish the sole mapping commit

In `PREPARE_CLOSEOUT`, run `pr_review_closeout.py seal` with the exact-material
self-review JSON. Allow only `seal` to write
`docs/review/PR_<N>_FIXED_MAPPING.md`. The lifecycle delegation covers this bounded
mapping operation, but the seal remains evidence only.

Keep the seal provider-neutral:

- Treat provider absence as neither review, scan, approval, PASS, nor no-findings.
- Do not invoke, restart, retry, poll, wait for, substitute, or override an absent
  provider.
- Keep actual provider findings, trusted security checks, current-head CI,
  mapping, thread, ancestry, and wait-window gates blocking.

Put exactly one rendered same-repository Markdown link to the canonical mapping
on its own bullet line in the live PR body. Bind the URL to the authenticated
exact `head.ref`. Do not duplicate URL-to-SHA mapping blocks in the PR body.

With both opaque tokens exported and the canonical mapping as the only dirty
path, run:

```bash
python3 scripts/orchestration/check_merge_ready.py \
  --pr-number <N> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --pre-closeout \
  --require-auth \
  --experiment-runner-evidence-mode required
```

Interpret a pre-closeout `PASS` as procedural admission evidence only. It is not
lifecycle delegation, merge authorization, or merge-readiness evidence. If strict
authentication is unavailable, stop; do not substitute advisory output, local tests,
or CI impressions.

After `PASS`, create the one direct, non-empty, non-trigger mapping-only successor
and non-force push it under the existing lifecycle delegation. Preserve strict
authentication and the sole-tail constraint. Do not add another mapping tail,
rebase or force-push a governed tail, or manufacture a CI-trigger commit. If current
policy exposes an OWNER-only reply exception, stop for explicit human OWNER
inspection. Do not synthesize the reply, interpret bot prose, or create another
documentation commit.

## Prove current-head readiness

After the mapping push, reacquire the authenticated live head and bind all
evidence to it.

1. Resolve an ordinary review thread only after its disposition and proof are
   visible. The lifecycle delegation covers that supported same-lane resolution.
2. Reinventory actionable bot issue comments, inline comments, top-level reviews,
   and unresolved threads.
3. Treat `gh pr checks` as diagnostic only. Inspect required workflows and jobs by
   exact head SHA and job name.
4. Reject stale, superseded, cancelled, queued, pending, in-progress, and
   cascade-skipped evidence. A completed shell watcher, browser no-conflict state,
   aggregate `UNSTABLE`, one passing readiness job, or an empty thread inventory
   is not terminal readiness proof.
5. Report numeric diff coverage as unknown when the source does not provide a
   number, even if its gate passed.
6. Run the unchanged strict wrapper without `--pre-closeout`:

```bash
python3 scripts/orchestration/check_merge_ready.py \
  --pr-number <N> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth \
  --experiment-runner-evidence-mode required
```

Delegate review quiet-window duration and polling to the current wrapper and
repository policy. Do not hardcode historical timing. Restart the final
verification cycle after new review activity. New review activity refreshes the
inventory, strict result, and wait window; it does not expire the lifecycle
delegation.

When an allowed base advance is required, use only the repository-permitted
ancestry-preserving synchronization. Never rebase or rewrite history. Re-run the
affected local/current-head gates, freeze, self-review, mapping seal, inventory, and
wait cycle against the new evidence epoch. Do not ask for another human confirmation
unless the sync crosses a real stop boundary.

Report `READY_FOR_AUTHORIZED_MERGE` only when the narrow local bundle, every
required current-head job, applicable security/governance checks, numeric
`diff-coverage >= 97%`, complete review and disposition inventory, mapping topology,
seal, full strict wrapper, and review wait window all have current evidence.

## Merge only with exact-head human authority

`READY_FOR_AUTHORIZED_MERGE` is a checkpoint, not the end of the lifecycle
delegation. The exact-head squash merge is the only ordinary human-only checkpoint.
Readiness remains evidence only. Without a separate post-readiness human approval,
stop at `READY_FOR_AUTHORIZED_MERGE` and present a merge packet that binds the
repository, PR, exact live head, squash method, and fresh readiness summary.

In the nominal unchanged-head path, request human merge authorization once.
Immediately before merging, reacquire the live head and the freshness facts required
by repository policy. If they still match the approved exact action, merge with race
protection and without implicit branch deletion:

```bash
gh pr merge <N> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --squash \
  --match-head-commit <exact-live-head-sha>
```

Do not add `--delete-branch`; post-merge cleanup has its own safety predicates. If
the head changes after approval, refresh readiness and request a new exact-head merge
approval because the approved action changed. This is the only ordinary reason for
a repeat merge-approval request. A base, review inventory, required-check, or wait
change before execution also returns to the corresponding evidence phase.

If the merge command fails, first authenticate the PR and merge state. Diagnose a
recoverable failure and retry only when the exact approved head and action remain
unchanged. Never interpret an unknown command result as permission for a second
merge, a replacement carrier, history rewrite, or cleanup.

## Prove the merged result

After GitHub reports `MERGED`, report `MERGED_PENDING_POST_MERGE_PROOF` until all
bounded post-merge proof exists. After the separately approved merge succeeds, the
same lifecycle delegation continues through bounded post-merge proof until
`CLOSED`.

1. Locate the actual `main` worktree with `git worktree list --porcelain`.
2. Require that worktree to be owned, clean, and safe. Never switch or merge in a
   checkout carrying another lane. Stop if no safe `main` worktree exists.
3. In only that named worktree, fetch/prune and fast-forward with
   `git merge --ff-only origin/main`. Do not use `git pull`, rebase, or a history
   rewrite.
4. Prove the exact conditions:

```text
HEAD == origin/main
git rev-list --left-right --count HEAD...origin/main == 0 0
working tree clean
```

5. Run a named focused sanity check against the merged surface on updated
   `main`. Keep any caches or artifacts local and gitignored. A merge receipt alone
   is not product or post-merge proof.
6. Clean only the exact finished or superseded worktree, branch, and temporary
   paths that satisfy the safety predicates below. If a target is dirty, unowned,
   ambiguous, not merged or equivalent, or the sole evidence carrier, leave it in
   place and report the real boundary.

Safe cleanup means one exact target, proven lane ownership, a clean target,
authenticated merge or equivalence proof, preservation of the sole evidence copy,
and no broad glob. Apply those predicates independently to the remote branch, local
branch, worktree, and each temporary path. Never delete an unresolved variable,
wildcard expansion, broad directory, or evidence that has not been preserved.

Report `CLOSED` only after authenticated merge state, the three Git conditions,
the named passing sanity check, and the exact cleanup/preservation inventory are
recorded.

## Report one status

Emit exactly one status:

- `BLOCKED`: a real scope, high-impact, history, replacement, OWNER-only,
  unrecoverable-topology, or unsafe-ownership/cleanup boundary requires a specific
  external decision. Use `BLOCKED` also when a named required external fact cannot
  be restored through bounded in-lane remediation, for example unavailable strict
  GitHub authentication. Do not use `BLOCKED` for recoverable gate failures, bounded
  in-lane remediation, ordinary descendant-head evidence refresh, or pending
  current-head evidence.
- `WAITING_CURRENT_HEAD`: the exact-head required CI or review window is not yet
  terminal. Continue bounded remediation and evidence refresh under the existing
  lifecycle delegation.
- `READY_FOR_AUTHORIZED_MERGE`: readiness is proven, but merge authorization is
  absent. This is a checkpoint; request the one exact-head squash merge approval.
- `MERGED_PENDING_POST_MERGE_PROOF`: GitHub merge is proven, but synchronization,
  sanity, or selective cleanup proof is incomplete.
- `CLOSED`: merge and all bounded post-merge proof are complete.

Include repository and PR identity; head/base/merge-base; material head and
digest; RFC 3339 observation and command-completion times with timezone; local
gate evidence; exact-head run and job IDs; review inventory and
dispositions; mapping, seal, PR-body link, pre-closeout, strict-wrapper, and wait
state; merge authorization and result; post-merge `0 0`, clean-tree, sanity, and
cleanup evidence. Label unknown or unverified values honestly and name the next
blocking action.

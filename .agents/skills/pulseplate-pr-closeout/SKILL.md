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

Default to `AUDIT`. Enter a mutating mode only when the user has authorized that
mode and its exact effects. Treat readiness as evidence, never as merge authority.
Never expose, persist, parse, decode, or log `GH_TOKEN` or `GITHUB_TOKEN`.

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

- `AUDIT`: inspect live state and report blockers without changing Git, GitHub,
  review threads, mappings, branches, or worktrees. Use this by default.
- `PREPARE_CLOSEOUT`: freeze material, record dispositions, seal the mapping,
  update the PR-body link, publish the sole mapping commit, and resolve supported
  threads. Require explicit authorization for each local or GitHub mutation.
- `AUTHORIZED_MERGE`: merge only after a separate explicit user authorization,
  an unchanged exact head, and a fresh strict-readiness result.
- `POST_MERGE_PROOF`: synchronize the real clean `main` worktree, run bounded
  merged-main sanity, and selectively clean the finished lane. Require explicit
  authorization for synchronization or deletion.

If the requested mode is unclear, remain in `AUDIT` and report what authorization
would be needed next.

## Admit the lane

1. Read the current repository instructions and the nearest scoped instructions.
2. Run the canonical coordinator-first startup for non-trivial work. Execute the
   task packet's role sequence and required gates; do not infer that loading this
   skill executed them.
3. Authenticate the live repository and PR identity. Record the PR number,
   repository, `head.ref`, exact head SHA, base SHA, merge-base, PR state, and
   worktree owner. Record the RFC 3339 observation time and timezone for the live
   snapshot; never present an undated observation as current evidence.
4. Compare local `HEAD` with the authenticated live PR head. Stop on a mismatch,
   ambiguous PR, dirty unowned worktree, or overlapping lane without an explicit
   handoff.
5. Prefer live GitHub and Git evidence over browser impressions, old handoffs,
   historical plans, or memory. Do not duplicate CI observation already owned by
   another active lane; report its owner and continue only with independent work.

## Close the material diff

Fix every bounded actionable in the current PR surface before mapping it. Do not
use mapping, checkboxes, thread resolution, or `DEFERRED` to hide an unfixed
current-surface defect.

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
cause, and rerun the affected required gate before continuing.

## Freeze and review exact material

Use only the registered closeout commands:

```text
init -> freeze -> add-disposition -> exact-material pulseplate-pr-review -> seal
```

1. Run `pr_review_closeout.py init` to create or resume the gitignored draft.
2. Require a clean worktree and local `HEAD` equal to the live PR head before
   `freeze`.
3. Freeze the current material identity once. Any later code, tests, workflow,
   dependency, policy, contract, or non-mapping documentation change invalidates
   the freeze, self-review, and seal.
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

## Seal and authorize the sole mapping commit

Run `pr_review_closeout.py seal` with the exact-material self-review JSON. Allow
only `seal` to write `docs/review/PR_<N>_FIXED_MAPPING.md`.

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

Interpret a pre-closeout PASS only as authorization for one mapping-only commit.
It is not merge-readiness evidence. If strict authentication is unavailable,
stop; do not substitute advisory output, local tests, or CI impressions.

After PASS, create and push exactly one direct, non-empty, non-trigger
mapping-only successor. Do not add another mapping tail, rebase or force-push a
governed tail, or manufacture a CI-trigger commit. If current policy exposes a
reply-only exception, stop for explicit human OWNER inspection. Do not synthesize
the reply, interpret bot prose, or create another documentation commit.

## Prove current-head readiness

After the mapping push, reacquire the authenticated live head and bind all
evidence to it.

1. Resolve a review thread only after its disposition and proof are visible.
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
verification cycle after new review activity.

Report `READY_FOR_AUTHORIZED_MERGE` only when the narrow local bundle, every
required current-head job, applicable security/governance checks, numeric
`diff-coverage >= 97%`, complete disposition inventory, mapping topology, seal,
strict wrapper, and review wait window all have current evidence.

## Merge only with explicit authority

Without a separate user authorization, stop at `READY_FOR_AUTHORIZED_MERGE`.
Immediately before an authorized merge, reacquire the live head and rerun any
freshness checks required by current policy. Merge with race protection:

```bash
gh pr merge <N> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --squash \
  --delete-branch \
  --match-head-commit <exact-live-head-sha>
```

Do not retry automatically when the head, base, review inventory, or required
checks change. Return to the corresponding verification phase. Permit at most
the repository-authorized ancestry-preserving base sync and reseal. Use a
replacement carrier only through a separately authorized lane when topology is
provably unrecoverable.

## Prove the merged result

After GitHub reports `MERGED`, report `MERGED_PENDING_POST_MERGE_PROOF` until all
bounded post-merge proof exists.

1. Locate the actual `main` worktree with `git worktree list --porcelain`.
2. Require that worktree to be owned, clean, and safe. Never switch or merge in a
   checkout carrying another lane. Stop if no safe `main` worktree exists.
3. After explicit authorization, fetch/prune and fast-forward only that `main`.
4. Prove the exact conditions:

```text
HEAD == origin/main
git rev-list --left-right --count HEAD...origin/main == 0 0
working tree clean
```

5. Run a named focused sanity check against the merged surface on updated
   `main`. A merge receipt alone is not product or post-merge proof.
6. Clean only the exact finished or superseded worktree, branch, and temporary
   paths after proving ownership, dirt state, and that no sole evidence copy is
   being deleted. Never use broad cleanup globs.

Report `CLOSED` only after authenticated merge state, the three Git conditions,
the named passing sanity check, and the exact cleanup/preservation inventory are
recorded.

## Report one status

Emit exactly one status:

- `BLOCKED`: a required fact, gate, authorization, or safe ownership condition
  is missing or failed.
- `WAITING_CURRENT_HEAD`: the exact-head required CI or review window is not yet
  terminal.
- `READY_FOR_AUTHORIZED_MERGE`: readiness is proven, but merge authorization is
  absent.
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

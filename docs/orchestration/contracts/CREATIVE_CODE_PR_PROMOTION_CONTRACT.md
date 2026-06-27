# CreativeCodePRPromotion Contract

Status: PR-3 human-approved non-draft PR promotion tooling. No product runtime impact.

PR-3 adds a local, fail-closed handoff from one accepted PR-2
`CreativeCodePatchResult` plus exact `candidate.patch` into the normal
PulsePlate pull-request lifecycle. It may create a new `experiment/*` branch,
push that new branch with create-only remote-ref semantics, and open a
non-draft PR only after isolated pre-open validation and explicit TTY human
approval.

It does not authorize draft PRs, branch updates, force push, default-branch
writes, review requests, review submissions, review-thread resolution,
fixed-mapping edits, merge-readiness claims, merge, release, Slack changes,
GitHub App changes, product runtime AI, OpenAPI/client changes, frontend/iOS
changes, DB changes, dependency changes, or public multi-tenant use.

## Artifacts

Strict schemas:

- `creative_code_pr_promotion_plan.v1.schema.json`
- `creative_code_pr_promotion_validation.v1.schema.json`
- `creative_code_pr_promotion_approval.v1.schema.json`
- `creative_code_pr_promotion_receipt.v1.schema.json`

Validator and CLI:

```bash
python -m scripts.orchestration.creative_code_pr_promotion_contract
python -m scripts.orchestration.creative_code_pr_promotion
```

Local receipts stay under:

```text
artifacts/orchestration/creative_code/promotions/<promotion-id>/
```

That directory is local-only and gitignored. It must never be committed.

## Flow

```text
accepted PR-2 patch result
-> promotion plan
-> isolated pre-open validation
-> explicit human approval
-> isolated promotion checkout
-> exact patch application
-> new experiment/* branch
-> one human-authored commit
-> create-only remote branch push
-> gh pr create non-draft
-> readback verification
-> sanitized local receipt
```

CLI:

```bash
python -m scripts.orchestration.creative_code_pr_promotion plan \
  --patch-run <pr2-run-id> \
  --promotion-id <id>

python -m scripts.orchestration.creative_code_pr_promotion validate \
  --promotion-id <id>

python -m scripts.orchestration.creative_code_pr_promotion approve \
  --promotion-id <id> \
  --approved-by-login <github-login>

python -m scripts.orchestration.creative_code_pr_promotion promote \
  --promotion-id <id>
```

`plan` is side-effect-free with respect to GitHub and repository branches. It
reads local PR-2 artifacts, verifies admission, derives the branch, writes the
plan and deterministic PR body, and stops.

`validate` creates an isolated validation checkout at the exact PR-2 base SHA,
applies the exact patch, creates a throwaway local commit so
`make validate-changed` has a meaningful diff, runs fresh candidate oracle
evaluation, runs `pre-commit run --all-files`, runs `make validate-changed`,
and fails if gates mutate the patch.

`approve` requires an interactive TTY, current `gh api user` actor binding, and
the exact phrase:

```text
APPROVE NON-DRAFT PR <plan-fingerprint> <patch-hash-8>
```

There is no `--yes` flag, CI approval mode, or environment bypass.

`promote` rechecks plan, validation, approval, actor, current `origin/main`,
branch absence, and patch fingerprint before creating any remote state.

## Admission

Promotion is allowed only when all PR-2 facts remain true:

- `result.status == accepted`;
- `result.failure_class == null`;
- `runner_summary.status == accepted`;
- `runner_summary.failure_class == null`;
- every configured oracle was executed;
- `runner_summary.shared_tree_untouched == true`;
- `workspace_summary.origin_removed == true`;
- `workspace_summary.checkout_destroyed == true`;
- `workspace_summary.shared_tree_untouched == true`;
- `promotion_ready == false`;
- `sanitized == true`;
- `candidate.patch` fingerprint, byte count, and diff-line count match the
  result;
- changed paths and PR-1 lineage match the request and selected variant;
- `base_commit_sha == current origin/main`.

Reject on base drift, patch drift, branch-name drift, branch existence, dirty
shared worktree, non-TTY approval, GitHub actor mismatch, draft PR request,
pre-commit mutation, validation failure, fresh oracle failure, path traversal,
symlinked artifact paths, or any attempt to use review/merge/thread authority.

## Git and GitHub Boundaries

Subprocess transports must use resolved absolute `git` and `gh` binaries,
fixed argv, `shell=False`, bounded timeouts, and sanitized environments. The
tool must not read token values, call `gh auth token`, mint JWTs, read GitHub App
private keys, or generate installation tokens.

Allowed GitHub mutation:

```bash
gh pr create \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --base main \
  --head experiment/<derived-branch> \
  --title "<deterministic-title>" \
  --body-file "<body-file>"
```

Forbidden command shapes include:

```text
gh pr create --draft
gh pr ready
gh pr review
gh pr merge
gh pr close
gh pr edit --add-reviewer
gh api .../reviews
gh api .../merge
gh auth token
```

Readback must confirm:

- `state == OPEN`;
- `isDraft == false`;
- `baseRefName == main`;
- `headRefName == expected experiment/* branch`;
- `headRefOid == created commit SHA`.

## Branch and Commit

Branches are derived, not user/model supplied:

```text
experiment/<safe-variant-slug>-<patch-hash-8>
```

Rules:

- lowercase ASCII after the `experiment/` prefix;
- maximum length 80;
- existing branch blocks;
- create-only remote-ref lease must fail if the branch appears before push;
- no unconditional force push;
- no update to an existing branch;
- no auto-rebase.

The commit is authored and committed by the local human Git configuration.
Because the Experiment Runner materially contributes to the candidate patch, the
commit message includes:

```text
Creative-Code-Result: <result-id>
Creative-Code-Patch: <sha256>
Human-Promotion-Approval: <approval-id>
Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>
```

The runner must not be author or committer.

## PR Body Safety

The generated body is deterministic and includes:

- Summary;
- Goal;
- Business reason;
- Scope;
- Out of scope;
- Creative Research Origin;
- Alternatives Considered;
- Patch Evidence;
- Oracle Evidence;
- Pre-Open Validation;
- Security Notes;
- Cost;
- Known Limitations;
- Human Approval;
- Tests / Validation;
- Deferred / Follow-ups;
- Experiment Runner Evidence;
- Discussion Thread Pass;
- Fixed in Commit Mapping;
- Merge Readiness.

Required statements:

- Candidate evaluation is not merge-readiness evidence.
- A separate oracle-only governance review of the actual PR diff remains
  required.
- Cost metadata: unavailable.
- Merge readiness is not claimed.
- Generated code may be incorrect.
- No medical or clinical claim is established by this PR.

The body, receipt, and summaries must not include raw patch text, prompts,
reasoning traces, model/provider payloads, runner logs, local absolute paths,
secret-shaped strings, or local Slack/GitHub identifiers beyond public
repository refs.

## Failure Handling

Before push, failure destroys the local checkout and leaves no remote state.

After push but before PR creation, the tool writes a sanitized partial receipt
if it has a commit SHA. It does not delete the remote branch.

After PR creation but failed readback, the tool writes a sanitized partial
receipt. It does not close the PR or delete the branch.

Any destructive cleanup is manual-only.

## Relationship To PR-2

PR-2 remains local-only and unchanged: its `promotion_ready=false` result is the
input to PR-3, not a hidden authorization flag. PR-3 validates the immutable
PR-2 lineage and adds a separate human approval and non-draft PR creation lane.

PR-3 must not call `experiment_pipeline.py`, `experiment_promote.py`,
`experiment_notify.py`, notification wrappers, review-thread tooling, or merge
wrappers. Normal PulsePlate CI, CodeRabbit, security review, QA, bug-hunter,
fixed mapping, and merge-readiness governance start only after the non-draft PR
exists.

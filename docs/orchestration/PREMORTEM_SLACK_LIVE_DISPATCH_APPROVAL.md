# Premortem: Slack Reviewed Live-Dispatch Approval Gate

## Frame

It is 6 months from now. The Slack live-dispatch approval gate failed. We are looking backward to understand why.

## Raw Failure Modes

### 1. Approval SHA256 env var leaked into CI logs or commit
- **Story:** An operator set `EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256`
  or `approval_proof` in a workflow dispatch input for convenience. It was
  echoed in a step summary, captured in a public artifact, and scraped. An
  attacker reused the leaked value to replay a live experiment tuple.
- **Assumption:** The approval digest is treated as a secret.
- **Warning signs:** `::add-mask::` missing for approval ref/proof in workflow;
  approval digest or proof appears in GITHUB_STEP_SUMMARY or workflow artifact.
- **Containment:** Workflow must mask approval_ref and approval_proof inputs;
  audit artifacts must store only a hash prefix or redacted marker and must not
  persist the proof.

### 2. Workflow approval validation is too weak
- **Story:** The `experiment-runner-dispatch.yml` workflow accepted
  `dry_run: false` because `approval_ref` was present and no bridge-signed
  `approval_proof` was validated. Live dispatch ran without proof that the
  Slack bridge had checked the reviewed approval digest.
- **Assumption:** A non-empty string means "approved."
- **Warning signs:** Workflow `if` conditions use loose string checks; no explicit SHA256 hex regex validation.
- **Containment:** Validate lowercase SHA256 shape for `approval_ref` and
  `approval_proof`, then verify `approval_proof` as HMAC-SHA256 over
  `branch_ref + "\0" + hypothesis_sha256 + "\0" + approval_ref` with the
  workflow-dispatch secret.

### 3. Bridge sends `dry_run: false` without approval by code path error
- **Story:** A refactor of `_github_dispatch_inputs` introduced a default parameter or branch where `dry_run` was set to `"false"` when `approval_ref` was `None`. The existing tests only checked execute mode with `dry_run: true`, so the regression reached `main`.
- **Assumption:** Existing tests cover all dispatch paths.
- **Warning signs:** New code path added without corresponding negative test.
- **Containment:** Every code path that sets `dry_run` must have an explicit test proving the value; code review must flag unguarded `"false"` literals.

### 4. Approval replay / reuse across different branch/hypothesis pairs
- **Story:** An operator approved one specific `branch_ref` + `hypothesis` pair. The approval SHA256 was reused for a different pair because the bridge only checked that *some* approval existed, not that it matched the current command.
- **Assumption:** The bridge validates approval against the current command.
- **Warning signs:** Approval check is a global boolean, not a per-command hash comparison.
- **Containment:** Bridge must compute
  `SHA256(branch_ref + "\0" + hypothesis)` and compare with the env var before
  it emits `dry_run: false`; mismatch must reject with a clear error class.
  The workflow must separately validate the HMAC proof for the emitted
  branch/hypothesis-digest/approval tuple.

### 5. Race condition between approval env update and Slack command
- **Story:** An operator updated the GitHub Actions environment secret with a new approval digest. Before the secret propagated, another operator issued a Slack command. The old approval was still active and matched an unintended command.
- **Assumption:** Env updates are atomic and instantaneous.
- **Warning signs:** Multiple workflow dispatches with the same approval digest but different branch/hypothesis pairs succeed.
- **Containment:** Approval digest must include a nonce or timestamp, or be single-use via explicit claim/invalidation. Out of scope for this PR; document in runbook that approval env updates are operator-only and must be validated before dispatch.

### 6. Audit artifact omits approval state, blocking post-incident investigation
- **Story:** After an unauthorized live dispatch, the audit artifact only recorded `status: dispatched` without an `approval_hash` field. Security review could not determine whether approval was present or bypassed.
- **Assumption:** The audit schema is comprehensive.
- **Warning signs:** Audit JSON schema changes without test updates.
- **Containment:** Audit payload must include `approval_hash` (or `"none"`) for every dispatch path; tests must assert its presence.

### 7. Unsafe branch or hypothesis strings bypass validation in live path
- **Story:** The live-dispatch path introduced a new code branch for computing dispatch inputs. This branch accidentally skipped `_is_safe_ref` or `_validate_hypothesis` because the inputs were derived from the approval hash rather than raw command text.
- **Assumption:** Input validation is uniform across all paths.
- **Warning signs:** Live-dispatch tests do not include the same unsafe-input parametrize cases as dry-run tests.
- **Containment:** Live-dispatch tests must reuse the same unsafe branch/hypothesis parameterization; bridge must validate raw inputs before computing any hash.

## Synthesis

### Summary

Add a reviewed live-dispatch approval gate to the Experiment Runner Slack bridge
by introducing an env-var approval digest
(`EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256`) that the bridge matches against
`SHA256(branch_ref + "\0" + hypothesis)`, then requiring the bridge to sign the
workflow inputs with `EXPERIMENT_SLACK_SOCKET_WORKFLOW_DISPATCH_SECRET` before
the workflow accepts `dry_run: false`.

### Most likely failure

**Failure mode #3:** A code-path refactor accidentally sends `dry_run: false` without approval. The existing test suite is strong for dry-run paths but the new live-dispatch path is narrow and easy to regress.

### Most dangerous failure

**Failure mode #1:** Approval digest or proof leaked into logs/artifacts. If
both leaked with the same tuple still valid, they can replay that tuple. The
workflow `::add-mask::` step must cover `approval_ref` and `approval_proof`, and
the bridge must never print the raw env var, proof, branch, or hypothesis.

### Hidden assumption

The approval digest and workflow proof are not nonce-backed single-use tokens.
They bind one tuple, so leaked values require immediate rotation of the approval
digest and suspected secret exposure requires rotation of the workflow-dispatch
HMAC secret.

### Revised plan

1. **Bridge:** Compute `SHA256(branch_ref + "\0" + hypothesis)` and compare with `EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256`. Reject with `SlackSocketDispatchError` on mismatch. Never log the env var or computed hash. See runbook for operator digest generation instructions.
2. **Workflow:** Add `approval_ref` and `approval_proof` inputs with default
   `"none"`. Validate live dispatch via bridge CLI
   `--validate-workflow-dispatch-approval`. Only allow `dry_run: false` when
   the proof matches the branch, hypothesis digest, and approval ref. Mask both
   fields in `::add-mask::`.
3. **Audit:** Add `approval_hash` field to run-experiment dispatch audits only. Store `"none"` when dry-run, a truncated hash prefix when live-approved.
4. **Tests:** Add parameterized unsafe-input tests for the live-dispatch path. Add explicit tests for approval mismatch, approval match, missing approval env, case normalization, and sentinel `"none"`.
5. **Runbook:** Document that approval digests are operator-managed secrets, single-use per dispatch is recommended, and leaked digests must be rotated immediately.

### Pre-merge checklist

- [ ] `::add-mask::` covers `approval_ref` and `approval_proof` in the dispatch workflow.
- [ ] No raw `EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256`, `EXPERIMENT_SLACK_SOCKET_WORKFLOW_DISPATCH_SECRET`, or `approval_proof` appears in stdout, stderr, audit artifacts, or step summaries.
- [ ] Tests prove `dry_run: false` is rejected without approval.
- [ ] Tests prove `dry_run: false` is accepted with matching approval.
- [ ] Audit schema tests include `approval_hash` field.
- [ ] Unsafe branch/hypothesis inputs are rejected in live-dispatch path.
- [ ] Runbook updated with approval-digest rotation instructions.

### Decision

`proceed with changes` — plan is sound after the revised plan items above are implemented.

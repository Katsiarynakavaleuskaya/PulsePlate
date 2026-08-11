# PulsePlate — Agent Runbook (CI + Merge Cycle)

**Last updated:** 2026-06-24 (devpi private index rollout; canonical simple root is `https://packages.pulseplate.app/root/pulseplate/+simple/`; authenticated URLs are secret-only and root credentials are forbidden for CI)

**What this is:** Quick reference for diagnosing CI failures, import hygiene regressions, and current-head merge-cycle state.
**When to use:** CI fails, tests hang, import errors, SQLAlchemy mapper issues, or a PR needs a strict merge-readiness pass.
**Related:** See root `AGENTS.md` for fast triage commands, `tests/test_repo_policy_guards.py` for enforced rules.

## Canonical Policy Links

- **Coordinator-first rule + definition of "task":** see `AGENTS.md` (Agent Coordination section)
- **Quality gates (procedure):** see `RUNBOOK_AGENT.md` (`## Quality Gates (Canonical)`)
- **Quality gate thresholds / policy:** see `AGENTS.md` (Hard Gates / Coverage rule sections)

---

## Agent Coordination (Coordinator-First Policy)

> Note: This section describes **operational** steps only. Policy/definitions live in `AGENTS.md`.
> Automation boundary: repo policy requires coordinator-first behavior, but raw
> start-of-session auto-invocation depends on the local launcher/runtime
> enforcement described in `docs/orchestration/AUTOMATION_READINESS_MATRIX.md`.

**When creating any task, coordinator-first routing is required.**
If launcher/runtime auto-capture is unavailable, manual coordinator invocation is still
required before any non-trivial execution. This is a start gate, not advisory wording.

**Canonical workflow:** See `docs/orchestration/workflow.md`

**Templates (copy-paste ready):**
- Task Analysis: `docs/orchestration/task_analysis.template.md`
- Work Review: `docs/orchestration/work_review.template.md`
- Synthesis: `docs/orchestration/synthesis.template.md`
- DoD: `docs/orchestration/dod.template.md`

The coordinator will:
1. **Analyze the task** and identify the affected domains and risk level.
2. **Route to appropriate agent(s)** using the canonical routing sources:
   - `docs/orchestration/AGENT_ROUTING_GRAPH.md`
   - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
   - nearest scoped `AGENTS.md`
3. **Coordinate multi-agent workflows** when tasks span domains or merge-governance lanes.
4. **Synthesize outputs** from multiple agents into one coherent solution.
5. **Verify quality gates and merge-governance state** before any readiness claim.
6. **Record follow-ups** in `docs/roadmap/BACKLOG_LEDGER.md` when work is deferred.

### Required role-order execution

When a coordinator-owned task packet or runbook declares an explicit role-agent order, execute
the assigned role agents in that order.

Rules:
- Do not skip an assigned role agent without an explicit coordinator update to the packet.
- Do not replace the declared order with an ad-hoc internal stack.
- Missing execution of a bootstrap-assigned role is a hard gate for PR work:
  packet creation is provenance only and never counts as role execution.
- The canonical post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
  role-only lane remains mandatory for PR work.
Source of truth: the active lane packet or runbook at the canonical packet path for the current
lane, which contains the enforced role-agent sequence for that task or PR.

The global final-material Codex Security invariant is defined only in root
`AGENTS.md`. Operationally, this runbook orders current closeout as:
freeze → exact-head `pulseplate-pr-review` self-review → fix and disposition
actual findings → `pr_review_closeout.py seal --self-review-report <report.json>`
without review/security provider flags → strict current-head validation. The seal authors the exact static
review/security no-claim pair and does not invoke, start, restart, retry, poll,
wait for, substitute, or require an operator override for either provider.

Provider absence is not review, scan, approval, PASS, or no-findings evidence.
Provider absence requires no retry.
The trusted current-head security bundle, required CI, actual findings,
canonical mapping, review threads, bot actionables, ancestry, mapping-only
closeout, and wait window remain hard.

Legacy compatibility only: GitHub Codex Connector review and Codex Security
were separate providers. Their embedded receipts remain readable only as
historical data; provider preparation/outcome authoring commands are not
registered and no legacy receipt authorizes a current provider request or
retry.

**Usage:**
```text
Use the agent-coordinator subagent to [task description]
```

When task bootstrap and the host runtime allow it, the coordinator may
automatically delegate to specialized agents and synthesize their work.
If that enforcement layer is absent, manual coordinator-first invocation is the
required fallback.

### Native Runtime Transport Note

PulsePlate agent definitions in `.cursor/agents/` are the single canonical source
for all runtimes. The native subagent bridge supports multiple transports:

- **Kimi Code CLI** — `kimi-native-subagents` bridge; Kimi discovers `.agents/skills/`
  as Project scope automatically. Use `task_bootstrap.py --native-bridge-transport kimi-native-subagents`.
- **Codex** — `codex-native-subagents` bridge; uses `.cursor/agents/` directly.
- **Qoder** — legacy compatibility via `qoder_dispatch_bridge.py`.

Canonical dispatch entrypoint for all transports:
`scripts/orchestration/role_dispatch_bridge.py --packet <packet> --pretty`

### Skill-Router Sync Note

When a PR changes `scripts/orchestration/skill_router.py` or
`docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`, verify the agent-facing
instructions still match the live contract:

- `security-auditor` auto-routes `security-best-practices`,
  `security-threat-model`, and `pulseplate-guards`
- `cybersecurity-skills` stays companion/manual-only and must not appear in
  deterministic `recommended_skills`
- privileged-surface routing is shared by bootstrap and skill routing through
  `scripts/orchestration/bootstrap_sync_policy.py`; see
  `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` for the canonical
  workflows/actions and matched-surface list; must keep `security-auditor` executable

**Starting a new task:**
- See canonical definition: `AGENTS.md` (Agent Coordination section)
- Templates: `docs/orchestration/*.template.md`
- Full workflow: `docs/orchestration/workflow.md`
- If the previous PR in the active train has merged, sync local `main` first and verify
  current-head `main` health before creating the next branch.
- If `main` is red, pending because of merge fallout, or otherwise unstable, stop the next PR
  and stabilize `main` first.
- If the active lane packet or runbook defines an explicit role-agent order, execute the
  assigned role agents in that exact order.
- If a bootstrap packet lists role bindings in the legacy `advisory` collection
  with `required_role_pass: true`, execute them as mandatory custom-role passes;
  the collection name is metadata only, not optional.
- Run `pulseplate-premortem-risk-review` and Experiment Runner oracle evidence for
  every non-trivial PR before opening. Premortem findings must be fixed or
  dispositioned; Experiment Runner artifact load/write failures are infrastructure
  blockers.
- For PR lifecycle packets, bootstrap may now accept `--pr-phase`:
  - `pre_open` for pre-PR scope lock without review-lane synthesis
  - `post_open_review` after PR creation to surface the mandatory
    `qa-engineer-agent -> bug-hunter -> security-auditor` role-only lane plus
    the separate final-material review/security contract
  - `merge_ready` for explicit current-head merge-preparation packets
- `post_open_review` remains deterministic once invoked; it is not a raw-session
  or host-runtime auto-trigger by itself.

**Postponed items:** Always record in `docs/roadmap/BACKLOG_LEDGER.md` immediately.

### Post-merge sync and cleanup before the next PR

Use this sequence after a merge and before opening the next PR in a train:

1. `git checkout main`
2. `git fetch --prune origin`
3. `git merge --ff-only origin/main`
4. verify current-head required-check health for `main`; if `main` is red, pending on merge
   fallout, or otherwise unstable, stop and fix `main`
5. run `gh pr view <N> --json state` and confirm the PR state is `MERGED`; abort cleanup and
   next-PR prep if the PR is not merged yet
6. remove merged local branches only after sync and merge-state verification
7. remove merged remote branches/worktrees only after sync and merge-state verification
8. start the next worktree/branch from synced `origin/main`; do not push more work to the
   already merged PR branch
9. clear only gitignored local artifacts relevant to the finished lane; never commit
   `artifacts/`, `worktrees/`, or host-local wrapper state

This is an operator runbook rule; it does not authorize `git pull` shortcuts or force-pushes.

---

## Agent Orchestration Protocols

**Purpose:** Canonical protocols for multi-agent coordination.

**Location:** `docs/orchestration/`

### Protocol Index

| Protocol | Purpose | When to Use |
|----------|---------|-------------|
| [Task Evaluation Contract](docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md) | Success criteria per task class | Every task (pass/fail criteria) |
| [Context Map](docs/orchestration/AGENT_CONTEXT_MAP.md) | Define which files each agent must load | Every task (Pre-flight Checklist) |
| [Capability Matrix](docs/orchestration/AGENT_CAPABILITY_MATRIX.md) | Agent routing guide (advisory) | Task assignment |
| [Handoff Protocol](docs/orchestration/AGENT_HANDOFF_PROTOCOL.md) | Sequential agent delegation | Multi-agent tasks (A → B → C) |
| [Dialogue Template](docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md) | Multi-agent brainstorming | Multiple valid approaches |
| [Parallel Work Protocol](docs/orchestration/PARALLEL_WORK_PROTOCOL.md) | Parallel agent execution | Independent subtasks |

### Pre-flight Checklist (Canonical)

Canonical Pre-flight Checklist is defined only here:
`docs/orchestration/workflow.md` → “Canonical Pre-flight Checklist (SoT)”

Rule: RUNBOOK does not duplicate checklists; it only links to the canonical source.

---

### E2E Example: Multi-Agent Task

**Task:** “Implement RAG endpoint for VIP tier with frontend UI and tests”

**Execution (high-level):**

1. **Coordinator:** Pre-flight Checklist (load required `AGENTS.md`, contract docs, runbook)
2. **Track 1 (Backend):** Architecture + AI Innovation → endpoint + OpenAPI
3. **Track 2 (Frontend):** Creative Designer → UI component
4. **Track 3 (Tests):** Bug Hunter → contract tests + coverage
5. **Sync Points:** SP1 (OpenAPI ready), SP2 (UI ready), SP3 (tests green)
6. **Post-flight Verification:** all sync points passed; deliverables returned
7. **Synthesis:** coordinator merges tracks into one coherent outcome
8. **DoD:** verify quality gates + record postponements in `BACKLOG_LEDGER.md`

## Quality Gates (Canonical)

**Before merge, verify:**
- Local narrow bundle passes: `check_preflight`, `check_agent_consistency`,
  focused tests for the touched surface, `make validate-changed`, and
  `pre-commit run --all-files`.
- GitHub current-head CI supplies the full heavy signal: lint, typecheck /
  required backend checks, relevant `test-main` matrix, `diff-coverage` at
  ≥97%, applicable security/governance checks, and merge-readiness CI.
- Guard tests pass when they are selected by the touched surface or focused
  validation plan.
- Security scans pass when applicable (see `AGENTS.md` for policy and tools).

**Local full-verify budget rule:** agents must not run full local `make verify`
in this PulsePlate checkout by default. The unsharded full suite exceeds the
operator's acceptable local machine budget. GitHub current-head CI is the
heavy/full-suite signal. Local `make verify` is allowed only when a human
explicitly overrides this rule for one invocation.

**Machine-heavy CI/tooling PRs:** the operator explicitly defers full local
`make verify` by default in this checkout. Agents must use the documented narrow bundle
and wait for canonical current-head CI parity: `lint`,
required/current-head checks, the relevant `test-main` matrix,
`diff-coverage` at ≥97%, security/governance checks, and
`check_merge_ready.py --require-auth`.

**This is the authoritative procedural checklist.** Thresholds/policy live in `AGENTS.md`.

### Merge-Ready Bundle (Blocking vs Advisory)

Use this bundle when you need a strict merge claim:

1. Local blocking bundle:
   - `pre-commit run --all-files`
   - `make validate-changed`
   - `check_preflight`, `check_agent_consistency`, and focused tests for the
     touched surface
   - Full local `make verify` is not a default agent command; GitHub
     current-head CI owns the heavy lint/typecheck/test/diff-coverage signal.
2. PR governance blocking bundle:
   - `python scripts/orchestration/check_merge_ready.py --pr-number <N> --repo <owner/name> --require-auth`
3. Advisory / external signals:
   - Non-required CI jobs
   - Third-party review bots unless branch protection marks them required
4. Release-ops blocking bundle:
   - Fastlane / App Store validation and upload lanes are blocking for publish claims, not automatically for ordinary PR merge claims unless the PR itself changes release surfaces

Canonical SoT for the lane matrix:
- `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md` (`CI Check Classification`)
- `scripts/orchestration/check_merge_ready.py`

For the Tier 1 backend/shared CI consolidation wave, the PR-series operating
contract lives in:
- `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/TIER1_CI_CD_TASK_PACKET_2026-03-26.md`

Operator routing baseline before PR2 workflow consolidation:

- Backend/shared PR: inspect `CI` first; treat it as the canonical lane.
- Frontend/design-token/OpenAPI frontend sync PR: inspect `Frontend CI` first,
  then `Accessibility Tests` when its path filter attaches.
- iOS PR: inspect `CI` iOS jobs first, then `Greenlight iOS Preflight`; treat
  Fastlane/App Store lanes as release-ops, not ordinary PR merge blockers,
  unless the PR explicitly changes release surfaces.
- Workflow-change PR: inspect `CI` first. Current path routing in `CI` also
  attaches iOS jobs for `.github/workflows/**` and `.github/actions/**`, so a
  workflow-only PR can inherit iOS cost until PR2 removes that coupling.
- Release/image PR: inspect `Docker Build and Push` plus any publish lane that
  the PR explicitly changes.

## Guard Coverage Step (EVMbench-inspired)

**Purpose:** Ensure comprehensive coverage — address *all* related violations, not just one.

**When:** Before closing any guard/security PR.

**Steps:**

1. **Run full guard suite:**
   ```bash
   pytest -q tests/test_repo_policy_guards.py
   ```

2. **Confirm no related violations in changed modules:**
   - If PR touches `app/routers/`, verify no BMI math violations
   - If PR touches `core/`, verify no duplicate module patterns
   - If PR touches security config, verify Trivy/bandit pass

3. **Scope check:**
   - All violations of the same class should be fixed in this PR
   - If additional violations exist, either fix them or track in `BACKLOG_LEDGER.md`

4. **Route guard check for tiered surfaces:**
   - When a PR touches canonical `/api/v1/pro/*` or `/api/v1/vip/*` routing,
     run `pytest -q tests/test_pro_vip_route_dependency_guard.py`
   - This guard inspects the live `app.main.app` route table and fails on missing
     `require_pro_tier` / `require_vip_tier` coverage or undocumented alias drift.

**Rationale:** EVMbench scores on comprehensive coverage. Partial fixes (fix one, leave others) result in low scores and technical debt.

## Oracle / Known-Good Gate Behavior (EVMbench-inspired)

**Purpose:** Define expected behavior of quality gates on known-good input for deterministic validation.

**Rationale:** EVMbench uses logic/grading oracles to objectively evaluate
agent success. For PulsePlate, our quality gates (local narrow bundle, GitHub
current-head CI full/heavy signal, guard tests, merge-readiness checks) serve
as oracles. Documenting known-good behavior allows us to:
1. Validate gate implementations (gate passes on valid input)
2. Detect gate drift (gate fails on previously-passing input)
3. Establish baseline for agent evaluation (agent achieves "first-run pass" if gate passes without iteration)

### Known-Good Gate Specifications

| Gate | Known-Good Input | Expected Behavior | Evidence Anchor |
|------|------------------|-------------------|-----------------|
| Local narrow bundle | Clean repo, touched-surface checks passing | Exit 0, no warnings | `AGENTS.md:5` |
| GitHub current-head full CI | Current PR head, required checks passing | Required jobs PASS, no pending required jobs | `.github/workflows/ci.yml:1` |
| `merge_readiness_gate` | PR with all checkboxes checked + valid commit mapping | Exit 0 | `scripts/ci/check_pr_merge_readiness.py:251` |
| `dependency_security_guard` | `requirements.txt` with all deps at floor versions, no blocked packages | Test passes | `tests/test_dependency_security_guard.py:1` |
| `pr_body_phase2_gates` | PR body with `[x]` checkboxes + `- No actionable review comments` | Exit 0 | `scripts/ci/check_pr_body_phase2_gates.py:107` |
| `guard_tests` | Codebase with no policy violations | All guards pass | `tests/test_repo_policy_guards.py:1` |

**Verification commands:**
- Local narrow bundle: `python3 scripts/orchestration/check_preflight.py && python3 scripts/orchestration/check_agent_consistency.py && make validate-changed && pre-commit run --all-files`
- GitHub current-head full CI: use the latest PR head checks and strict merge-readiness wrapper
- `merge_readiness_gate`: `python scripts/ci/check_pr_merge_readiness.py --pr-number <N>`
- `dependency_security_guard`: `pytest -k dependency_security_guard -q`
- `pr_body_phase2_gates`: `python scripts/ci/check_pr_body_phase2_gates.py --body "..."`
- `guard_tests`: `pytest -q tests/test_repo_policy_guards.py`

### Gate Validation Protocol

When modifying a gate or its inputs:

1. **Baseline capture:** Run gate on known-good input, record exit code + output.
2. **Change implementation:** Make modification.
3. **Re-validate:** Run gate on same known-good input; must produce same result.
4. **Negative test:** Run gate on known-bad input; must produce expected failure.

**Known-bad input examples:**
- `merge_readiness_gate`: PR with unchecked boxes, unmapped bot comments
- `dependency_security_guard`: `requirements.txt` with blocked package (`cryptography==41.0.0`)
- `guard_tests`: Code with BMI math outside `core/bmi/`

## Minimal Agent Metrics (EVMbench-inspired)

**Purpose:** Define minimal metrics to evaluate agent task performance objectively.

**Rationale:** EVMbench evaluates agents on objective success rates. For PulsePlate agent workflows, we track:
1. **First-run pass rate** — did the agent get it right on the first attempt?
2. **Iteration count** — how many cycles to achieve green CI?
3. **Gate coverage** — did the agent address all violations or just one?

### Core Metrics

| Metric | Definition | Target | Evidence Anchor |
|--------|------------|--------|-----------------|
| **CI Fix: First-Run Pass** | PR passes GitHub current-head required checks on first push | ≥70% | CI logs: first commit → green |
| **CI Fix: Iteration Limit** | Maximum pushes to achieve green CI | ≤3 | Git log: commit count on PR branch |
| **Merge Readiness: First-Run** | PR passes merge-readiness gate on first attempt | ≥50% | `scripts/ci/check_pr_merge_readiness.py:251` exit 0 |
| **Guard Coverage** | All violations of same class fixed in one PR | 100% | `tests/test_repo_policy_guards.py` after PR |
| **Docs Accuracy** | Documentation updates match code changes | 100% | Manual review + file anchors present |

### Metric Collection (Operational)

Metrics are captured from existing CI artifacts:

1. **First-run pass:** Compare first CI run status vs final merge status
2. **Iteration count:** Count commits on PR branch from open to merge
3. **Guard coverage:** Run guard suite before/after PR; compare violation counts

**Current tracking:** Manual (ledger notes). Future: automated dashboard (P2 backlog).

### Success Criteria per Task Class (Reference)

Full success criteria per task class are defined in:
`docs/orchestration/AGENT_TASK_EVALUATION_CONTRACT.md`

This metrics section provides **quantitative targets**; the evaluation contract provides **qualitative gates**.

## Pre-push hygiene checklist (mandatory)

### Linked-worktree hook Python resolution

Checked-in hooks call `resolve_repo_python <repo_root>` from
`scripts/hooks/repo_python.sh`. Resolution order is exact:

1. a valid absolute regular executable `VENV_PYTHON`, otherwise `DEV_PYTHON`;
   an invalid explicit override is terminal
2. the current checkout `.venv`
3. the primary checkout `.venv`, only after canonical Git common-dir,
   linked-worktree admin backlink, primary top-level, and same-common-dir
   validation
4. system `python3`, then `python`, in CI only
5. local failure when none of the trusted candidates exists

Linked worktrees may be nested, sibling, or outside the primary checkout.
Directory naming is not evidence of ownership; the worktree `.git` pointer and
admin `gitdir` backlink must identify each other. Bare, separate, or decoy
`.git` layouts are rejected. If a commit stops with
`ERROR: no repo/shared .venv Python found for local hook execution`, repeat the
original commit command with an absolute override for that one recovery run.
For example:

```bash
VENV_PYTHON="/absolute/path/to/primary/.venv/bin/python" git commit -m "same commit message"
```

Do not export the override permanently, disable the hook, or skip it. Repair
the checkout/venv binding before the next normal commit.

## GitHub Full-Verify Parity

Agents do not run full local `make verify` by default. If a human explicitly
overrides the local budget rule for one invocation and `make verify` fails
before the real code gates because the clean-clone `.venv` is incomplete, use
the canonical repo recovery path:

```bash
make venv
make verify
```

If `.venv` already exists but drift is suspected, refresh it from the locked
requirements before retrying:

```bash
make venv-sync
make verify
```

`make verify` starts with `verify-env`, a fail-fast preflight that does not
repair the environment. It fails when verify-critical modules such as
`flake8`, `diff_cover.diff_cover_tool` (`diff-cover`), `coverage`, `pytest`, or
`mypy` are missing from `.venv`, when unexpected executable `.pth` startup
hooks are present, or when **present** `.venv/bin` console scripts for those
tools are broken: non-executable, dangling symlink, or an absolute shebang
pointing at a missing or non-executable interpreter (typical after deleting a
worktree or moving the venv). Missing console scripts are allowed—the canonical
`make verify` recipe uses `$(DEV_PYTHON) -m ...` (generic targets) and
`$(VENV_PYTHON)` (verify-env only)—but any installed wrapper must
be consistent so PATH-based tools, shells, and hooks do not fail later with
opaque “bad interpreter” errors. Shebangs using `#!/usr/bin/env ...` are not
validated in v1. Run `make verify` from repo root and do not rely on an
externally activated interpreter: `verify-env` requires the repo `.venv`
interpreter itself. Evidence: `scripts/ci/check_local_verify_environment.py`.

**Host-native binary-wheel recovery boundary (dated 2026-08-04):** use the
host only with an approved compatible binary wheel for the exact locked pin,
interpreter, and platform. Current `cryptography==50.0.0` Intel macOS evidence
lacks `x86_64` and `universal2` artifacts, so use the devcontainer. A
source-build fallback is not supported. This is a dated artifact observation,
not a permanent availability claim.

## Python private index proxy (`PULSEPLATE_PYTHON_INDEX_URL`) triage

**Canonical contract:** see `docs/DEPENDENCY_MANAGEMENT.md` and `scripts/ci/install_locked_python_requirements.py`. Installs must use the approved proxy; public PyPI hosts are blocked for the canonical installer path.

### Symptoms

- `curl` / browser to `…/simple/<package>/` returns **521** (often Cloudflare origin down) or **5xx**.
- `pip` / `make venv-sync` reports *No matching distribution* for a pin that exists on PyPI.
- CI Python setup fails at preflight or locked install.

### Operator checks (dev-operator / SRE)

1. Confirm env is set: `test -n "$PULSEPLATE_PYTHON_INDEX_URL"` and points to the approved devpi simple-index root. Canonical shape: `https://packages.pulseplate.app/root/pulseplate/+simple/`. Keep this URL credential-free; authenticated CI reads use rotated non-root `DEVPI_CI_USER` / `DEVPI_CI_PASSWORD` secrets through the temporary `.netrc` created by `.github/actions/python-setup/action.yml`. Root credentials are forbidden for CI.
2. **HTTP probe** (bounded so a hung origin cannot stall triage): `curl -sS --connect-timeout 5 --max-time 10 -o /dev/null -w '%{http_code}\n' "${PULSEPLATE_PYTHON_INDEX_URL%/}/aiosqlite/"` — expect **200** when healthy. Use the **PEP 503 project page path** under the configured simple-index root (here `aiosqlite`) — probing the bare host or adding another `/simple` does not exercise the same project page that pip consumes and can return misleading results. For authenticated private-read checks, prefer the installer preflight below because it uses `.netrc` and redacts inline URL credentials defensively.
3. **Representative mirror health gate:** from repo root, run the stdlib-only checker before expensive local or CI dependency work:
   `python3 scripts/ci/check_private_python_proxy_health.py --requirements-file requirements.txt --requirements-file requirements-ci-lite.txt --requirements-file requirements-test.txt --requirements-file requirements-dev.txt --project aiosqlite --project cryptography --project requests --project pytest-xdist --project hypothesis --project mypy --project ruff --project librt --project ast-serialize --project pgvector`. It validates the credential-free canonical simple-index root, rejects public, wrong-root, or credentialed indexes, probes canonical project pages, and verifies exact locked pins are present across runtime, CI-lite, test-only `ci-test`, and dev-tool lint/pre-commit surfaces. In protected CI, authenticated project-page reads use `.netrc`; pull-request and non-main branch diagnostics use repository vars only. Failure classes are intentionally distinct:
   - `tls_or_connect_timeout` / `origin_unhealthy` / HTTP 521/522: recover Cloudflare/DigitalOcean/devpi origin first.
   - `empty_project_page` / `simple_page_malformed`: inspect devpi project-page generation or mirror sync.
   - `mirror_lag_exact_pin_missing`: sync the mirror; the emergency wheel manifest is allowed only as a time-boxed exact-pin bridge.
   - `missing_exact_pin_in_requirements`: fix the checker input list or lockfile selection.
   - `auth_or_access_denied`: fix non-root `.netrc`/devpi read credentials; do not embed auth in `PULSEPLATE_PYTHON_INDEX_URL`.
   - `project_page_not_found`: verify the normalized project page and mirror sync for that package.
   - `redirect_not_allowed`: fix DNS/devpi route drift so the canonical simple root is served directly.
   - `http_error`: inspect Cloudflare/origin logs for non-2xx package-host responses not covered above.
   - `simple_page_truncated`: use a smaller representative fast-gate package or investigate oversized mirror pages before raising timeouts.
4. **Emergency manifest all-entry parity:** when validating or changing `scripts/ci/emergency_python_wheels.json`, run:
   `python3 scripts/ci/check_emergency_wheel_mirror_parity.py --manifest scripts/ci/emergency_python_wheels.json --python-version 3.11 --python-version 3.12 --python-version 3.13 --format text`. This is not a replacement for the representative health gate: it validates every active manifest filename against the approved private project pages. `retired=true` means the repo manifest is the empty compatibility marker and no runtime-effective emergency fallback is active.
5. **Preflight without full install:** from repo root with venv active,
   `python3 scripts/ci/install_locked_python_requirements.py --preflight-only`
   (reads the same index + optional `scripts/ci/emergency_python_wheels.json` per policy).
6. **Scope of `scripts/ci/emergency_python_wheels.json`** — this manifest is **not a 521 fallback**. It is currently an empty retired marker. If a future incident reintroduces active entries, they must remain mirror-lag fallback wheels for exact listed filenames only (sha256-only, `files.pythonhosted.org` URLs, TTL `expires_at`) and must pass the all-entry parity checker above before publication. The installer (`install_from_proxy_with_emergency_fallback`) retries with the **same** `--index-url` and only adds `--find-links` for wheels whose exact pins are listed here, so any unlisted dependency in `requirements*.txt` / `requirements-ci-lite.txt` still requires a working `--index-url`. Therefore:
   - When the proxy returns 200 but **lags** for an approved listed pin → an active manifest entry can keep installs going; this is the supported case.
   - When the manifest reports `retired=true` → no emergency wheel is runtime-effective, and mirror lag must be fixed in the private proxy.
   - When the proxy itself is fully unhealthy (true Cloudflare 521 / origin down) → the emergency manifest **cannot keep installs going on its own** for unlisted pins. Do **not** present it as a "521 fallback" to operators. The only correct operator paths in that case are: (a) restore the *packages* origin per the SRE/infra section below, or (b) use an out-of-band complete offline wheelhouse (not part of this PR's scope). This is also the reason `ledger-p1-private-pypi-proxy-mirror-parity` exists — see `docs/roadmap/BACKLOG_LEDGER.md`.
   - Any change to the manifest must pass `tests/test_python_supply_chain_controls.py`, `tests/test_emergency_wheel_mirror_parity.py`, and installer tests; security review applies.

### SRE / infra (scoped fix for 521)

> **Important hostname split.** A 521 on `pulseplate.app` (the public marketing
> site) may be **intentional release gating** — the operator can hold that origin
> down on purpose until the public site is ready. **Do not "revive" the
> marketing origin** as part of CI triage. The only CI-blocking surface is the
> **packages hostname** behind `PULSEPLATE_PYTHON_INDEX_URL` (e.g.
> `packages.pulseplate.app`), which **must** serve PEP 503 project pages under
> the devpi `root/pulseplate/+simple/` root for the locked pins. Treat the two
> hostnames as independent origins behind the same Cloudflare zone. If both
> share one origin today, splitting them is part of the backlog parity work — see
> `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-private-pypi-proxy-mirror-parity`.

- **Root cause (when the packages hostname is the one returning 521):** HTTP **521** means Cloudflare reached the edge but the **origin** did not return a valid HTTP response (origin down, wrong port, TLS mismatch, firewall dropping CF IPs, overload). Fix the **origin** behind the *packages* proxied hostname only; do not touch the marketing origin without explicit operator approval.
- **Cloudflare dashboard** (zone `pulseplate.app`, account-specific) — scope every check to the **packages hostname** record, not the apex marketing record: **DNS** → confirm the packages **A/AAAA/CNAME** points at the live mirror origin; **SSL/TLS** → mode compatible with that origin (often *Full (strict)* if the origin has a valid cert); **Security** → WAF / rate limits / Bot Fight not blocking the packages path; **Analytics** → filter by status 521 **and hostname** so you don't accidentally read the intentional-gate apex traffic; **Load Balancing** (if used): pool health and origin status for the packages pool only.
- **Origin / mirror:** restore Bandersnatch / devpi / Nexus / Artifactory sync, disk, egress for the *packages* origin; ensure **full** PEP 503 simple index for locked pins (including `aiosqlite` and CI manylinux wheels).
- **Repo agents / Cursor:** this assistant has **no** login to your Cloudflare account; use the dashboard or API-token-backed tooling (`curl` / Terraform / WAF API). **Wrangler** can be used when Cloudflare credentials are already configured — it supports both `wrangler login` (browser-based OAuth) and API-token / API-key auth (e.g. `CLOUDFLARE_API_TOKEN`, or `CLOUDFLARE_EMAIL` + `CLOUDFLARE_API_KEY` for legacy global-key flows) — but it does **not** replace zone SSL/DNS/origin fixes for a custom origin, and it must not be used to flip the intentional-gate state of the marketing origin without an explicit operator decision logged in the backlog.

**Leak guard:** GitHub `python-setup` uses `set -euo pipefail` without `xtrace`, rejects credentialed `PULSEPLATE_PYTHON_INDEX_URL` values, writes optional devpi credentials only to a temporary `.netrc`, and removes that file in an `always()` cleanup step.

Run from repo root before any push/PR:

1. `git status --porcelain` → must be empty (or only intentional expected files)
2. `git ls-files worktrees | wc -l` → must be `0`
3. `git check-ignore -v worktrees/` → must show an ignore rule
4. `pre-commit run --all-files`
5. `make validate-changed`

## PR operating lifecycle (mandatory for coordinator-led work)

Use this as the canonical operating loop from branch creation to merge window:

1. **Coordinator start**
   - Run `python3 scripts/orchestration/check_preflight.py`
   - Read `AGENTS.md`, `RUNBOOK_AGENT.md`, and the nearest scoped `AGENTS.md`
   - Decide scope, risk, and which sub-agents or helpers are needed before edits
2. **Open non-draft by default**
   - Provider presence is not an opening prerequisite. Do not invoke, trigger,
     retrigger, or wait for Connector/Codex Security output.
   - Open the PR ready-for-review once scope, artifact strategy, and initial local gates are coherent so bots and current-head checks run
   - Let the configured review bots react automatically to the opened or
     synchronized diff. Do not post manual bot-review commands or disable their
     automatic review setting.
   - Use draft only with an explicit operator exception when review/check suppression is intentional
   - Create or confirm the canonical artifact path `docs/review/PR_<N>_FIXED_MAPPING.md`
3. **Post-open review entry**
   - Once the PR exists, run the mandatory post-open reviewer path declared by the lane packet/runbook before calling the lane stable
   - When the lane declares `qa-engineer-agent -> bug-hunter -> security-auditor`, that pass happens after PR open, not as a substitute for pre-PR local gates
   - Fix every finding, run the required local gates and current-head CI, then
     freeze the material digest with `pr_review_closeout.py freeze`
   - Run the repo-native exact-head `pulseplate-pr-review` as the local
     self-review and disposition every actual finding
   - Run `pr_review_closeout.py seal --repo <owner/name> --pr-number <N>
     --self-review-report <report.json>` without provider-evidence flags. This
     creates the exact static no-claim
     pair; it performs no provider call and requires no retry, substitute,
     operator override, or TTL.
   - Treat current-head CI/security, actual provider findings, mapping,
     unresolved threads, bot actionables, ancestry, and wait-window failures as
     blocking independently of the no-claim pair.
4. **Before each push**
   - Run `pre-commit run --all-files`
   - Run the required local narrow gates for the touched scope:
     `check_preflight`, `check_agent_consistency`, focused tests, and
     `make validate-changed`
   - Do not run full local `make verify` unless a human explicitly overrides
     the local machine-budget rule for one invocation
   - Commit hook changes separately when hooks modify files
5. **After each push**
   - Watch the latest-head CI run, not stale `gh pr checks` history
   - Treat `scripts/orchestration/check_merge_ready.py` as the canonical current-head verdict
6. **After each new review / bot activity**
   - Fix code/docs first when needed
   - If material changed, refreeze, rerun exact-material self-review, and
     revalidate every applicable current-head security/governance gate for the
     new digest
   - Keep dispositions in the gitignored closeout draft; generate the canonical
     mapping/seal once after the final exact-material validation cycle
   - For a validated canonical-record same-digest unavailable-ref duplicate,
     post the structured reply and resolve the thread. The same reply-only path
     covers one first recordless seed only on the exact direct mapping-only
     successor when the trusted root targets that live head and cites one
     reachable non-empty, non-trigger-only FIX mapped from a live resolved
     thread root by a commit pushed strictly after that root comment. Cardinality
     is computed only after full eligibility; if more than one eligible seed with
     the same fingerprint is currently visible, the validator covers none and
     all stay blocking. Rerun merge readiness without a docs commit, Codex
     review, or security scan.
   - When both canonical fingerprint records and FIXED mappings are empty, a
     different owner-only recordless class may cover exactly one resolved
     `chatgpt-codex-connector` root on the canonical current-PR mapping file.
     Confirm first that the root `originalCommit` is the live head, the live
     head is the sole direct mapping-only successor of the sealed material, the
     digest recomputes exactly, and the root names the exact sealed material SHA
     while binding the selected lowercase reviewer ref directly as the object of
     its `not an ancestor of` assertion. Phrase casing may vary, but SHA casing
     may not; labels, URLs, and unrelated SHA mentions are not evidence. A human must
     explicitly confirm the disposition before posting exactly this one line:
     `OWNER NOT-A-BUG: ignore unavailable reviewer ref <full-40-sha>; authenticated live PR graph is authoritative.`
     There must be exactly one later comment whose authenticated GraphQL
     association is exactly `OWNER`, and that sole OWNER comment must equal the
     exact line above. Its selected full lowercase ref must classify as
     `REVIEW_REF_UNAVAILABLE`. `API_UNKNOWN`, a real commit,
     any syntax variation, multiple eligible roots, any fingerprint record, or
     any FIXED mapping leaves the root blocking. Never pass the unavailable ref
     to ancestry. Count eligibility across all live thread roots before URL-only
     disposition filtering, and require the authenticated evidence repository
     to match the snapshot repository case-insensitively. The validator only
     reads this evidence; it never posts it and the line grants no approval or
     merge authority. For a root actually covered by this validator, the exact
     reply plus resolved thread is the disposition evidence; do not add a second
     mapping entry or docs commit. Every non-covered root follows ordinary mapping.
7. **Before merge**
   - Re-run the strict merge wrapper after the latest bot/review activity
   - Confirm no pending required jobs remain
   - Wait one review cycle after the final green state
8. **Post-merge sync / sanity / cleanup**
   - Sync the local clone back to `origin/main`
   - Run the required post-merge sanity checks for the touched lane
   - Remove temporary artifacts, stale worktrees, and merged local branches before declaring the lane closed
   - For a PR series, do not start `PR<N+1>` until `PR<N>` completes this post-merge closure step

If any part of this loop is skipped, the PR must not be described as ready.

For the Tier 1 CI/CD consolidation wave, apply the same loop with the explicit
stacked-PR routing card, mandatory post-open lane, and packet/runbook pair
documented in:
- `docs/orchestration/TIER1_CI_CD_PR_SERIES_RUNBOOK.md`
- `docs/orchestration/TIER1_CI_CD_TASK_PACKET_2026-03-26.md`

## Pre-merge readiness pass (mandatory for non-draft PRs)

Run before merge after latest commit and latest bot/review activity:

1. `python scripts/orchestration/check_merge_ready.py --pr-number <PR_NUMBER> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
2. `gh pr view <PR_NUMBER> --json mergeStateStatus,reviewDecision,isDraft`
3. **Zero bot comments (hard rule):** Merge only when (a) **0 unresolved review threads** and (b) **every actionable bot comment is mapped** in the canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`. PR body is mirror-only when `pr_number` is available. **Do not** report "0 comments" or "ready to merge" based only on unresolved thread count — new bot comments can appear after a check; use the canonical script (below) and re-run after bot activity.
4. Confirm the PR body contains the standard Goal/Scope/Tests/Security/Rollback
   sections, the exact `## Discussion Thread Pass` / `### Fixed in Commit Mapping`
   headings, both checked Phase 2 checklist items, and one link to
   `docs/review/PR_<N>_FIXED_MAPPING.md`; URL→SHA mappings live only in the
   artifact.
5. CI `Merge readiness gate` must be green on latest PR commit.

**Phase2 artifact/body gates (CI):** To pass `check_pr_body_phase2_gates.py` and merge-readiness:
- In the PR description, keep the validator-required discussion/mapping
  headings, both checked checklist items, and one canonical artifact link; do
  not hand-copy URL→SHA/disposition details.
- In the canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`: list each bot comment as `- <comment-url> -> <commit-sha>` or `- <comment-url>` depending on disposition, or use exactly `- No actionable review comments`.
- Local artifact-first check: `python scripts/ci/check_pr_body_phase2_gates.py --pr-number <PR_NUMBER>`
- Local body-only fallback check: `python scripts/ci/check_pr_body_phase2_gates.py --body "$(cat .github/pr_body_*.md)"`

**Canonical verification (required before claiming "0 comments" or "ready to merge"):** Run the orchestration wrapper so Phase 2, merge-readiness, and disposition proof are checked together. Policy: see `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`.

```bash
# Local default: advisory disposition auth, strict PR API auth.
export GITHUB_TOKEN="..."
python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate
```

```bash
# Local strict parity with CI for the disposition guard.
export GITHUB_TOKEN="..."
export GH_TOKEN="${GITHUB_TOKEN}"
python scripts/orchestration/check_merge_ready.py \
  --pr-number <PR_NUMBER> \
  --repo Katsiarynakavaleuskaya/PulsePlate \
  --require-auth
```
Exit 0 = Phase 2 + merge-readiness + disposition proof all pass. Exit 1 = do not merge; fix and re-run.

Raw `gh pr checks <PR_NUMBER>` remains diagnostic only. It can include superseded
historical failures from older runs, so final merge triage must rely on the
filtered current-head view emitted by `check_merge_ready.py`.

Additional live-triage notes:

Implementation provenance: strict current-head triage is enforced by
`scripts/orchestration/check_merge_ready.py` and
`scripts/ci/check_pr_merge_readiness.py`; this runbook wording was refreshed in
PR `#1162` via commits `639aa83f` and `b94d5575`.

- `gh pr checks <PR_NUMBER>` exits non-zero when required jobs are still
  `pending`/`in_progress`. Treat that as "merge window not open yet", not as a
  failed-check verdict.
- When only one current-head job remains live, inspect the exact run/job instead
  of re-reading the whole historical checks table:
  `gh run view <RUN_ID>` or `gh run view --job=<JOB_ID>`.
- Do not report a PR as "green" while `gh pr checks` is non-zero solely because
  of pending jobs. Wait for the last live job to finish, then re-run the strict
  wrapper.

**Optional: unresolved thread count only** (not sufficient alone):

```bash
gh api graphql -f query='
query { repository(owner: "Katsiarynakavaleuskaya", name: "PulsePlate") {
  pullRequest(number: <PR_NUMBER>) {
    reviewThreads(first: 50) { totalCount nodes { id isResolved } }
  }
} }' --jq '.data.repository.pullRequest.reviewThreads | "total: \(.totalCount), unresolved: \([.nodes[] | select(.isResolved == false)] | length)"'
```

Before merge: `unresolved` must be `0`. Resolve all threads in GitHub UI (Conversation → resolve thread) and map any actionable bot comments in the canonical artifact.

**Material-seal closeout cycle:**

1. `pr_review_closeout.py init` creates/resumes the gitignored local draft.
2. Publish the coherent material diff, then run `freeze` to prove local
   HEAD equals the live PR head and record its digest. Do not invoke, trigger,
   restart, retry, poll, or wait for Connector/Codex Security output.
3. Apply actionable fixes and record dispositions. Any material change returns
   to step 2; governance draft/body activity does not.
4. After the final role pass, current-head gates, and material freeze, run the
   repo-native exact-head `pulseplate-pr-review` self-review. Fix or disposition
   every actual finding. Provider absence never resolves an actionable.
5. Run `seal --repo <owner/name> --pr-number <N>
   --self-review-report <report.json>` without
   `--review-ref`, `--review-source-unavailable-ref`, `--scan-manifest`,
   or `--security-outage-override-ref`. The generated v1 seal contains the
   exact symmetric pair:
   - review: `review_claim=none`, `output_required=false`,
     `blocking=false`, exact material head/digest;
   - security: `scan_claim=none`, `no_findings_claim=false`,
     `output_required=false`, `blocking=false`, exact base/head/digest.
   Partial, mixed, arbitrary, or escalating forms fail. The pair is not review,
   scan, approval, PASS, or no findings and never weakens current-head
   CI/security, findings/dispositions, mapping, threads, bot actionables,
   ancestry, mapping-only closeout, or the wait window.
   Historical provider-backed v1 receipts remain readable only. The legacy
   terminal projection `source_degraded=true`, `fallback_required=false`,
   `blocking=false`, `review_claim=none`, `retry_required=false`,
   `substitute_review_required=false`, `prior_review_required=false`,
   `operator_override_required=false`, and `ttl_required=false` remains
   descriptive compatibility data, not current authoring or fallback authority.
   No protected change can use no-claim alone to authorize itself.
6. Update the live PR body with exactly one real same-repository Markdown link
   through
   `https://github.com/<owner>/<repo>/blob/<exact-live-head-ref>/docs/review/PR_<N>_FIXED_MAPPING.md`.
   The path must use the authenticated PR `head.ref` exactly; this supports
   slash-containing branch names without accepting extra file-path segments.
   The link must be a standalone bullet, and the decoded canonical URL may
   occur only once in the body; raw HTML/code examples and a plain repo-relative
   `docs/review/...` href do not count. Then validate the still-uncommitted
   mapping before its sole closeout commit:

   ```bash
   export GH_TOKEN="..."
   export GITHUB_TOKEN="..."
   python scripts/orchestration/check_merge_ready.py \
     --pr-number <PR_NUMBER> \
     --repo Katsiarynakavaleuskaya/PulsePlate \
     --pre-closeout \
     --require-auth
   ```

   The canonical mapping artifact must be the only dirty path. This pass must
   cover every live actionable bot issue comment, bot inline comment, and
   top-level bot review explicitly; a child-comment mapping does not cover its
   actionable top-level review. The validator re-reads the live body,
   content-bound actionable inventory, and local dirty-path set before PASS and
   fails closed if any changes during validation. It intentionally does not require resolved
   threads, current-head CI, or the review wait window and is not
   merge-readiness evidence.
7. Only after that pass, commit the artifact once and push it. Then run the
   unchanged authenticated strict wrapper without `--pre-closeout`; this
   post-push pass owns thread resolution, current-head CI, and the final merge
   verdict.
8. A later validated canonical-record duplicate, the single eligible first
   mapped-FIX recordless seed, or the mutually exclusive empty-mapping
   owner-only class uses only its exact reply contract and an explicit thread
   resolution, followed by one status-check cycle. The owner-only class requires
   an explicit human confirmation before the exact `OWNER NOT-A-BUG` line is
   posted; validators remain read-only. More than one fully eligible visible
   seed in the applicable class leaves all blocking. None may cause another
   synthetic closeout commit.

Do not report "ready to merge" or "0 comments" until the script passes and CI is green.

## Stacked PR replacement flow (mandatory when parent merge closes the child PR)

Implementation provenance: non-history-rewriting replacement flow is governed by
root `AGENTS.md` (`Git workflow (single-developer safe mode)`); this runbook
section was aligned in PR `#1162` via commit `4e2da5ad`.

If a stacked child PR is auto-closed because its parent base branch was merged
and deleted:

1. Verify the parent PR is actually merged:
   `gh pr view <PARENT_PR> --json state,mergeCommit,mergedAt`
2. Create a new branch from `origin/main` in its own worktree.
3. Cherry-pick the child commits onto that new branch.
4. Re-run `pre-commit run --all-files`, `make validate-changed`, and focused
   tests on the replacement branch head before pushing. GitHub current-head CI
   supplies the full heavy signal after the replacement PR opens.
5. Push the replacement branch and open a **replacement PR** on `main`.
6. Create a new canonical artifact path for the replacement PR:
   `docs/review/PR_<NEW_NUMBER>_FIXED_MAPPING.md`
7. Do not continue pushing to the auto-closed PR number as if it were still the
   active review lane.

## Agent Control Plane Security Ops (Wave 1 baseline)

Use this checklist when operating agent automation or closing a token/secrets incident.

**Detailed per-credential rotation protocols:** `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md` section "Credential Rotation Protocols" (R1-R5).

1. **Containment**
   - Stop agent runtime and disable auto-start service.
   - Quarantine local runtime state for forensics.
2. **Secrets rotation** (follow protocol R1-R5 per credential class)
   - R1: HMAC Audit Signing Key (`AGENT_CONTROL_AUDIT_SIGNING_KEY`)
   - R2: HMAC Broker Key (`AGENT_CONTROL_BROKER_HMAC_KEY`)
   - R3: Bot Tokens (GitHub App, Telegram, CI bots)
   - R4: API Provider Keys (LLM, external services)
   - R5: Webhook Secrets
   - For each: generate new → update secret store → restart → verify → revoke old → confirm revoked.
   - Reset webhook endpoints and confirm `getWebhookInfo` reports empty/expected URL.
3. **Verification**
   - Ensure no active runtime process/socket remains for disabled agent service.
   - Confirm privileged automation path is routed through policy gate only.
   - Run canonical security verification (see baseline doc, section "Canonical Security Verification").
4. **Documentation**
   - Record evidence and follow-ups in `docs/roadmap/BACKLOG_LEDGER.md`.
   - Keep controls aligned with `docs/security/AGENT_CONTROL_PLANE_SECURITY_BASELINE.md`.
   - Verify security release gate conditions pass (see baseline doc, section "Security Release Gate").

## METATRON offensive lab (Track A, out-of-band)

Coordinator-first lane only. Product runtime (`app.main`) must not carry METATRON-class
offensive tooling.

- Epic 1 task packet (roster + validation): `docs/orchestration/METATRON_TRACK_A_EPIC1_TASK_PACKET_2026-04-06.md:1`
- ADR: `docs/architecture/ADR_METATRON_OFFENSIVE_LAB_OUT_OF_BAND_2026-04-06.md:1`
- RoE: `docs/security/METATRON_LAB_RULES_OF_ENGAGEMENT.md:1`
- Assessment wave runbook: `docs/orchestration/METATRON_SECURITY_ASSESSMENT_WAVE_RUNBOOK.md:1`
- Ledger: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-metatron-offensive-lab-out-of-band`
- Optional compose stub: `deploy/metatron-lab/README.md:1`

## 0.1) CI: `actions/upload-artifact` fails with `FinalizeArtifact 403 Forbidden`

**Reference:** Documentation: [PR #712](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/712). Fix required a
repo-admin setting change (`default_workflow_permissions=write`; no repo commit).

**Symptom (GitHub Actions logs):**

- `Error: Failed to FinalizeArtifact: ... (403) Forbidden`
- often in steps like “Upload JUnit test report” / “Upload coverage artifact”

**Likely cause:** repository-level **default** workflow token permissions were set to `read`, which can break artifact
finalization even when the byte upload succeeded.

**Check (repo setting):**

```bash
gh api repos/<OWNER>/<REPO>/actions/permissions/workflow
```

Expected (for this repo’s CI, which uploads/downloads artifacts):

```json
{"default_workflow_permissions":"write", ...}
```

**Fix (requires repo admin):**

**Scope note:** changing repository-level `default_workflow_permissions` affects **all workflows** in this repository.
Coordinate with repo owners / security if needed before changing the default.

**Reference docs:** GitHub Actions `GITHUB_TOKEN` permissions:
`https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication`

```bash
gh api -X PUT repos/<OWNER>/<REPO>/actions/permissions/workflow -f default_workflow_permissions=write
```

**Also verify workflow/job permissions:** the job that uploads artifacts should request `actions: write`.
(Example: in CI workflows, see job-level `permissions:` blocks for test jobs.)

**Post-fix:** re-run the failed workflow run (`gh run rerun <RUN_ID> --failed`) and confirm artifact steps pass.

## 0) Golden Rule

Before editing imports / `__init__` / sys.path / sys.modules:
**Run guard checks first.** If guards fail, fix the policy violation before anything else.

## 1) Fast Local Triage (run from repo root)

```bash
make validate-min
make validate-changed
make lint
```

## 2) PR #403 Specific Checks (Import Hygiene)

### 2.0 SQLAlchemy Model Registration (WeeklyPlan/DayPlan not found)

**Problem:** `expression 'WeeklyPlan' failed to locate a name` → model not registered in ORM.

**A. Where classes are declared:**

```bash
rg -n "class WeeklyPlan\b|class DayPlan\b" app/models -S
```

**B. Where DayPlan references WeeklyPlan:**

```bash
rg -n "relationship\(\s*[\"']WeeklyPlan[\"']" app/models -S
rg -n "Mapped\[[\"']WeeklyPlan" app/models -S
```

**C. Model exports (CRITICAL - must export both classes):**

```bash
rg -n "from app\.models\.plans import|from \.plans import" app/models -S
sed -n '1,200p' app/models/__init__.py 2>/dev/null || true
```

**D. Who imports models at startup:**

```bash
rg -n "import app\.models|from app\.models import|import models" app legacy_app.py app/main.py core -S
```

**Fix pattern:**
- Keep `WeeklyPlan` and `DayPlan` in same module with `WeeklyPlan` declared **before** `DayPlan`
- Export both from `app/models/__init__.py`:
  ```python
  from .plans import WeeklyPlan, DayPlan  # noqa: F401
  __all__ = [..., "WeeklyPlan", "DayPlan"]
  ```
- Ensure startup imports `app.models` package (not individual modules)

### 2.1 Import hygiene regressions (dynamic import / exec_module)

**Problem:** `spec_from_file_location / exec_module` returns → Dual Base + Pydantic TypeAdapter issues.

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- app core tests
```

**Offender list (excluding whitelisted script tests):**

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- tests \
  | grep -vE "test_test_pro_access_coverage\.py|test_ensure_database_versions\.py|conftest\.py"
```

### 2.2 sys.path.insert in tests (masks import path bugs)

**Problem:** Breaks xdist isolation, hides real import errors.

```bash
git grep -n "sys\.path\.insert" -- tests
```

**Exclude allowlist (conftest + guards):**

```bash
git grep -n "sys\.path\.insert" -- tests \
  | grep -vE "tests/conftest\.py|tests/test_test_pro_access_coverage\.py|tests/test_import_hygiene_guard\.py|tests/test_repo_policy_guards\.py"
```

### 2.3 sys.modules mutation (main source of Dual Base)

**Problem:** `sys.modules["x"]=...` and `del sys.modules["x"]` create separate namespaces.

```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- .
```

**Only in tests:**

```bash
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- tests
```

### 2.4 Public surface app package (missing attributes)

**Problem:** Tests fail with:
- `module 'app' has no attribute build_nutrition_targets`
- `... get_update_scheduler`
- `... resolve_attr`

**Check what tests expect from app:**

```bash
git grep -nE "from app import |app\.(resolve_attr|build_nutrition_targets|get_update_scheduler|make_weekly_menu)" -- tests
```

**Verify what's actually exported:**

```bash
sed -n '1,200p' app/__init__.py
```

**Run surface guard tests:**

```bash
pytest -q tests/test_app_public_surface.py
pytest -q -k "public_surface or env_guards or import_hygiene"
```

### 2.5 ENV gating / порядок установки TESTING

**Problem:** Retired legacy export carriers can be mistaken for live runtime
configuration, while the canonical signed plan-export security gate has a separate
and still-active meaning.

```bash
git grep -nE "PRIVATE_EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG" -- app legacy_app.py core tests
git grep -nE -w "FEATURE_EXPORTS|EXPORTS_ENABLED" -- app legacy_app.py core
```

- For the retired whole-symbol audit, no output with exit status 1 is expected
  when both symbols are absent.
- The former `FEATURE_EXPORTS` / `EXPORTS_ENABLED` test/demo rail is retired.
  `TESTING=true`, `DEBUG=true`, `FEATURE_EXPORTS=true`, and
  `APP_ENV=test|testing|ci` must not register the old premium export aliases;
  those paths return the ordinary FastAPI 404.
- Both canonical export route families stay registered behind the canonical
  API-key dependency: plan signing and weekly CSV/PDF (`POST
  /api/v1/export/sign`, `GET /api/v1/plan/week/export.{csv,pdf}`), plus shoplist
  JSON/CSV/PDF (`GET /api/v1/shoplist`, `GET
  /api/v1/shoplist/export.{csv,pdf}`).
- `PRIVATE_EXPORTS_ENABLED` additionally controls signed-token enforcement only
  for the weekly plan CSV/PDF routes. It controls neither route-family
  registration nor any shoplist route; production/staging invariants still
  require the private gate enabled.
- Do not use a retired legacy carrier to diagnose canonical route availability
  or signed-token authorization.

**Check pytest_configure:**

```bash
git grep -n "os\.environ\[" -- tests/conftest.py
git grep -n "pytest_configure" -- tests/conftest.py
```

### 2.6 Recipe store tests (_con missing)

**Problem:** `module 'recipe_store' has no attribute '_con'` - symptom of wrong module import path.

**Anti-pattern check:**

```bash
git grep -n "sys\.modules\.get\(\"recipe_store\"\)" tests
git grep -nE "spec_from_file_location\(\"recipe_store\"" tests
```

**Correct pattern:**
- ❌ Don't: `sys.modules.get("recipe_store")`
- ✅ Do: `import app.services.recipe_store as rs`

**Verify import works:**

```bash
python -c "import app.services.recipe_store as rs; print(hasattr(rs,'_con'), rs._con)"
```

### 2.7 VIP router 422 vs 404

**Problem:** Router registered but disabled by logic → 422/401 instead of 404.

```bash
git grep -nE "include_router\(.*vip|VIP|vip_router" app
git grep -nE "VIP_ENABLED|VIP_MODULE_ENABLED|FEATURE_VIP" app core legacy_app.py
```

### 2.8 Docker build (COPY app.py not found / entrypoint drift)

**Problem:** Dockerfile copies `app.py` but file was renamed/moved.

```bash
rg -n "COPY .*app\.py|COPY .*legacy_app\.py" Dockerfile
rg -n "uvicorn\s+app(:|\.main:app)|legacy_app" Dockerfile Makefile docker-compose.yaml -S
```

**Check entrypoint matches canonical:**

```bash
rg -n "app\.main:app" Dockerfile Makefile docker-compose.yaml -S
```

**Expected:** `app.main:app` (current canonical entrypoint, not `legacy_app:app`).

### 2.9 Fast triage - top failure patterns

**When CI shows many failures, extract first 50:**

```bash
pytest -q --maxfail=50
```

**Build error frequency histogram:**

```bash
pytest -q --maxfail=200 2>&1 | rg -o "E\s+[A-Za-z_]+Error|sqlalchemy\.[A-Za-z_]+" | sort | uniq -c | sort -nr | head -30
```

This reveals patterns like:
- `NoForeignKeysError` → model relationship issue
- `InvalidRequestError: Table already defined` → duplicate model registration
- `AttributeError: module 'app' has no attribute` → missing public surface export

---

## 3) If LINT Fails

### 3.1 Ruff / formatting

```bash
ruff check . --fix
black .
```

### 3.2 Explain-only (to see the real errors)

```bash
ruff check . -v
```

## 4) If TESTS Fail

### 4.1 Narrow first

```bash
pytest -q -k "<failing_test_name_or_keyword>"
pytest -q tests/<path_to_file>.py
```

### 4.2 Import hygiene suspects

See section 2 (PR #403 Specific Checks) above for detailed grep commands.

### 4.3 ENV gating suspects (exports/vip)

```bash
git grep -nE "PRIVATE_EXPORTS_ENABLED|VIP_ENABLED|TESTING|DEBUG"
```

Set test environment values before importing `legacy_app`. Confirm that the
canonical API-key dependency protects both registered export families: plan
signing/weekly CSV/PDF and shoplist JSON/CSV/PDF. Use
`PRIVATE_EXPORTS_ENABLED` only to diagnose the additional signed-token check on
weekly plan CSV/PDF; it controls neither registration nor shoplist routes. The
retired legacy carriers no longer control any runtime route. See section 2.5.

## 5) If DOCKER Build Fails

See section 2.8 above for Docker-specific checks.

## 6) If COVERAGE Guard Fails

### 6.1 Identify uncovered lines

```bash
pytest --cov --cov-report=term-missing
```

Then add micro-tests for uncovered branches (avoid flaky tests).

## 7) If xdist Hangs / Mapper / Dual Base Symptoms

### 7.1 Confirm no dynamic loader

```bash
pytest -q tests/test_repo_policy_guards.py
```

### 7.2 Confirm single Base identity (if guard exists)

```bash
pytest -q -k "single_base or import_hygiene"
```

## 8) What NOT to Do (Hard Rules)

- Never mock `builtins.__import__` or `builtins.float`
- Never mutate `sys.modules` in tests
- Never reintroduce `exec_module` / dynamic import patterns
- No network calls in unit tests (use `providers/stub.py`)

## 9) Import Hygiene Checklist (Before Any PR)

See `AGENTS.md` for the full checklist. Quick version:

1. No dynamic imports (except whitelisted test files)
2. No `sys.path.insert` (except whitelisted test files)
3. No `sys.modules` mutations
4. Verify PEP 562 shim in `app/__init__.py`
5. `TESTING=true` set before app import
6. Guard tests pass
7. All retired legacy export aliases remain absent under their former carriers;
   the canonical API-key dependency protects both registered export families
   (plan sign/weekly CSV/PDF and shoplist JSON/CSV/PDF), and
   `PRIVATE_EXPORTS_ENABLED` adds signed-token enforcement only to weekly plan
   CSV/PDF without controlling registration or shoplist routes

## 10) Common CI Failure Patterns

### Pattern: "ModuleNotFoundError: No module named 'app'"

**Cause**: Import path broken, likely due to `sys.path` manipulation or missing `__init__.py`.

**Fix**:
```bash
# Check package structure
find app core -name "__init__.py"

# Verify imports use package paths
git grep -n "from app import" tests
```

### Pattern: "Multiple mapper registry conflicts"

**Cause**: Dual Base - models importing different `Base` instances.

**Fix**:
```bash
# Run Dual Base guard
pytest -q -k "single_base"

# Check all models import from core.db
git grep -n "from core.db import Base" app/models core
```

### Pattern: "pytest hangs on teardown"

**Cause**: Background threads/processes not cleaned up (common in coverage-smoke tests).

**Fix**: Exclude heavy import tests from xdist:
```python
# In conftest.py or pyproject.toml
# Mark tests: @pytest.mark.no_xdist
```

## 11) Emergency: Revert to Known Good State

```bash
# Check last green CI commit
git log --oneline -20

# Soft reset to that commit
git reset --soft <commit-sha>

# Review changes
git diff HEAD
```

# Engineering Lessons — PR-8b (VIP Shoplist PDF)

This document captures **project-level lessons** extracted from PR-8b.
Goal: prevent повторение классов проблем (test nondeterminism, CI portability, contract drift).

---

## 1) `sys.modules` mutations create dual-module state (CRITICAL)

### Problem
Mutating `sys.modules` in tests (e.g. `del sys.modules["app.routers.vip"]`) can create a **dual-module state**:
- imports resolve into different module objects
- `patch("...")` silently patches a different object than the one used by code-under-test

### Symptoms
- Patches "don't work" without obvious error
- flaky behavior depending on import order
- hard-to-debug nondeterminism

### Real incident (PR-8b)
CI flaked because:

`patch("app.routers.vip.get_available_regions", None)` sometimes did **not** affect the реально зарегистрированный handler for `/api/v1/vip/regions`.
In large test runners, this manifested as **success instead of error**.

**Fix (policy-compliant):**
- Find endpoint from `app.routes` by `(path, method)`
- Patch the callable used by the handler via:
  `endpoint.__globals__["get_available_regions"] = None` (via `monkeypatch`)
- No `sys.modules` mutations

### Rule
**Never mutate `sys.modules` in tests.**

**Repo status note:**
- Policy guard `pytest -q tests/test_repo_policy_sys_modules.py` is enforced for `tests/vip/**` only (legacy tests still contain sys.modules mutations).
- Policy uses AST-based detection (not regex) to avoid false positives on comments/strings.
- Policy tracks import aliases (`import sys as s`, `from sys import modules as m`) to catch all mutation patterns.

### Use instead
- `unittest.mock.patch(...)` (but see FAQ below)
- `monkeypatch.setattr(...)`
- `tests/_route_patch.patch_route_dependency(...)` for FastAPI endpoints

---

## FAQ: When `patch("module.symbol")` is not enough?

Sometimes the route handler used at runtime is not the same module object you think you're patching
(e.g., due to import aliasing, reload patterns, or dual-module state from prior tests).

**Robust approach (contract-safe):**
- Identify the actual registered endpoint (`app.routes`) by path+method
- Patch the function reference in `endpoint.__globals__` (or patch attribute on the actual callable)
- Prefer `monkeypatch` to keep test deterministic
- Use `tests/_route_patch.patch_route_dependency()` helper for FastAPI endpoints

---

## 2) Diff-coverage requires targeted tests for error paths

### Problem
Generic tests often don't execute specific branches (e.g. error lines 413/529), so diff-coverage fails.

### Rule
For each uncovered error path, add a **targeted test**.
Preferred pattern: `tests/**/test_*_diff_coverage.py`

---

## 3) Bash scripts must be portable (Bash 3.2+)

### Problem
macOS default Bash is 3.2; Bash-4-only features (e.g. `mapfile`) break local workflow.

### Rule
Scripts in `scripts/` must run on **Bash 3.2+**.
Prefer portable patterns: `while IFS= read -r ...`.

---

## 4) Shallow repos in CI require depth-aware git operations

### Problem
CI often uses shallow clones (`--depth=1`), so commands like `git diff HEAD~10 HEAD` can fail.

### Rule
Before using `HEAD~N`, verify actual depth:
- `git rev-list --count HEAD`
- fallback to merge-base or bounded depth

---

## 5) Always follow AGENTS.md before push

### Rule
Before pushing, follow the repo runbook.

**Quick checklist (example):**
- `pytest -q tests/test_repo_policy_guards.py`
- `make test-fast`
- `make cov-check`
- `make lint && make fmt-check`

---

## 6) PR description structure accelerates review

### Recommended sections
- `Review order (recommended)`
- `Why not split PR?`
- `Scope` split: core vs infrastructure
- `Risks / mitigations`
- `How to test`

---

## 7) Validate full error-envelope in tests

### Rule
Test contract, not just `status == "error"`:
- `status`
- `code`
- `error`
- `detail` (must match expectation)
- required fields present

---

## 7b) Do not paste machine-local absolute paths into review docs

### Problem
CI docs guards reject changed docs that include machine-specific home-directory
paths. This can create a fix-loop when an otherwise narrow CI PR records local
evidence with machine-specific command paths, then pushes a mapping fix that
forces another current-head run.

### Rule
Use repo-relative command evidence in docs and PR bodies:
- `.venv/bin/python -m pytest ...`
- `python3 scripts/...`
- `make validate-changed`

Keep absolute local paths out of `docs/review/**`, backlog evidence, and PR
body mirrors unless a specific policy explicitly requires them.

---

## 8) Keyword-only args in test helpers

### Rule
For helpers with many parameters (5+), enforce keyword-only:

```python
def helper(*, a: int, b: str, c: str) -> None:
    ...
```

This prevents accidental argument-order bugs and improves readability.

---

## 9) Zero-decimal currencies must have explicit scope boundaries

### Rule

Document supported zero-decimal currencies (currently: **JPY/KRW**) and define the path to extend (e.g. VND/CLP/ISK).

---

## 10) Use builtin generics for typing (`tuple[...]` over `Tuple[...]`)

### Rule

Prefer modern typing syntax (Python 3.9+):

- `tuple[int, str]`
- `list[str]`
- `dict[str, int]`

### Type hints for test fixtures

- Prefer explicit typing for fixtures/helpers when patching internals:
  `monkeypatch: pytest.MonkeyPatch`

---

## 11) `@patch` decorator fails with `@contextmanager` under Python 3.12 + xdist (CRITICAL)

### Problem

`unittest.mock.patch` used as a **decorator** (`@patch("module._connect")`) does not
correctly intercept `@contextmanager`-decorated functions when running under
**Python 3.12 with pytest-xdist** (`-n 4 --dist=loadscope`).
The mock is applied but the real function executes, causing tests to hit the
real database and return unexpected results.

### Symptoms

- Tests pass locally (sequential, Python 3.13) but fail in CI (Python 3.12, xdist).
- Assertions like `assert len(result) == 1` fail because the mock was bypassed
  and the real DB returned all rows (e.g., 10 or 15 items).
- Only tests using `@patch` on `@contextmanager` targets are affected; plain
  function patches may still work.

### Real incidents (PR #896, PR #897)

- PR #896: 12 tests in `test_food_store_coverage.py` failed on Python 3.12 CI.
- PR #897: 8 tests in `test_food_store_coverage_boost.py` — same root cause,
  missed in the scope of PR #896.

### Evidence (file:line)

- `tests/test_food_store_coverage_boost.py:126-170` (monkeypatch migration for `_connect` targets)
- `tests/test_food_store_coverage_boost.py:67-72` (autouse `monkeypatch.setenv` isolation)
- `tests/AGENTS.md:21-25` (policy update for `@patch` vs `monkeypatch.setattr`)

### Fix

Replace all `@patch(...)` decorators with `monkeypatch.setattr()`:

```python
# BEFORE (broken on 3.12 + xdist):
@patch("app.services.food_store._connect")
def test_search(self, mock_connect):
    mock_con = MagicMock()
    mock_connect.return_value = mock_con
    ...

# AFTER (works everywhere):
def test_search(self, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_con = _MockConnection(fetchall_result=[...])
    monkeypatch.setattr(food_store, "_connect", lambda: mock_con)
    ...
```

Also replace `os.environ` mutation in `setup_method()` with an autouse
`monkeypatch.setenv()` fixture for proper test isolation.

---

## 12) Bootstrap packets do not execute role agents

### Problem

`task_bootstrap.py` creates the coordinator packet and role metadata, but it does
not launch the role agents. Treating packet creation as execution can leave
requested reviewers, QA, bug-hunter, or security roles skipped while the PR looks
formally bootstrapped.

### Rule

After every non-trivial bootstrap packet is created, generate the dispatch
manifest by running the packet's
`role_agent_dispatch_contract.dispatch_manifest_command` with the actual packet
path, preserving any packet-emitted runtime owner flags, then execute its
`dispatch_sequence` in order.

Assigned role agents are mandatory lane steps unless the coordinator updates the
packet/runbook with an explicit disposition. Do not replace this with skills,
host preflight, Experiment Runner evidence, or PR-body prose.

### Fix pattern

- Packet schemas should expose a machine-readable role dispatch contract.
- Startup prompts should say that packet creation does not execute roles.
- Lane starter output should print the exact dispatch-manifest command.
- Tests should cover requested role order, coordinator-first behavior, and the
  required post-bootstrap dispatch guidance.

---

## 13) Merged AI/RAG ledger items need closeout, not duplicate implementation

### Problem

AI/RAG roadmap and ledger entries can stay open after the actual runtime PR has
already merged. If agents follow the stale open checkbox instead of live
GitHub/repo evidence, they can re-add an already-landed subsystem or widen a
closeout task into a new implementation PR.

### Real incident (PR-V1 closeout)

The verification registry landed via PR #1491 on 2026-04-22, but the ledger and
roadmap still described PR-V1 as active work. The correct follow-up was a
docs/checker/review reconciliation lane, not another `core/verification/*`
implementation.

### Rule

When a RAG/LLM/semantic-cache ledger item appears open but repo/GitHub evidence
proves it already merged, convert the task into a closeout/reconciliation PR.
Update backlog, roadmap, review mapping, and regression guards; do not duplicate
landed code.

---

## 14) Feature-flag backend routing must have explicit priority + lock-safe lazy init

### Problem

When multiple search backends are feature-flagged (e.g., `semantic`, `compat`, `legacy`),
implicit fallback order creates drift and hard-to-reproduce behavior in CI/runtime.
Additionally, lazy backend creation can deadlock if helper code re-enters the same non-reentrant lock.

### Rule

- Declare backend precedence explicitly (example: `semantic > compat > legacy`).
- Keep default path fail-closed (`new feature flag = off` by default).
- In lazy init code guarded by `threading.Lock`, never call helper APIs that re-acquire the same lock.
  Assign guarded globals directly inside the lock section instead.

### Test contract

- Add deterministic tests for:
  - priority selection when multiple flags are on
  - fallback behavior when new adapter is missing
  - env guard parsing for candidate/window limits

### Rule

**Prefer `monkeypatch.setattr()` over `@patch` decorator for all new tests.**
`monkeypatch` is pytest-native, version-safe, and properly scoped per test.

### Prevention

Before merging any PR that touches `food_store` tests (or any test using
`@patch` on `@contextmanager` targets), run:

```bash
# Scan for remaining @patch on food_store targets
git grep -n '@patch("app.services.food_store' -- tests/
```

If any matches remain, convert them to `monkeypatch.setattr()`.

## 15) API schema types must match persisted row types (barcode hit contract)

### Problem
Endpoint handlers that construct `FoodItem(**row)` can fail at runtime if DB columns store
string-encoded payloads for fields typed as structured types (example: `flags` expected as `List[str]`).

### Real incident (W2-C benchmark, 2026-02-25)
During latency benchmark for `/api/v1/foods/barcode/{barcode}`, hit-path requests raised
Pydantic validation errors because `app/schemas/food.py` defines:

- `flags: List[str]` (`app/schemas/food.py:40`)

but seeded DB rows may contain string values (e.g. `"[]"`), and router returns:

- `return FoodItem(**row)` (`app/routers/foods.py:105`)

### Rule
Before exposing DB rows directly through strict Pydantic models:

1. Normalize row payload types in repository/service layer
2. Add deterministic tests for hit/miss/malformed paths
3. Treat benchmark "scenario disabled" as tracked debt in `BACKLOG_LEDGER.md`

### Use instead
- Parse/normalize structured columns (`flags`) before model construction
- Keep migration/seed contracts aligned with API schema types
- Verify with endpoint-level tests, not only unit repository tests

## 15) After merge, never continue work on the same PR branch

### Problem
Continuing commits on a branch after PR merge creates ambiguity:
- new commits are not part of merged `main` state
- bot/check noise appears for already-merged scope
- reviewers see stale comments against a closed delivery

### Rule
Once PR state is `MERGED`:
1. stop edits on that branch immediately
2. create a new worktree + new branch from `origin/main`
3. continue only as a new PR with a new scope

### Verification
- `gh pr view <N> --json state,mergeCommit,mergedAt`
- if `state=MERGED`, do not push further commits to that branch

## 16) Local-first ingest scripts must fail-closed on empty normalized payload

### Problem
CSV ingestion can report "success" even when alias mapping drops required fields,
resulting in zero imported rows and empty API results.

### Rule
For operational import scripts (MenuStat-style and similar):
1. normalize column aliases to canonical contract keys
2. require non-empty mandatory keys (`chain_name`, `item_name`) per row
3. fail with non-zero exit code when no valid rows remain after normalization
4. keep a deterministic sample CSV + end-to-end script test in-repo

## 17) Subprocess-backed determinism tests must expose failure diagnostics

### Problem
When tests call shell pipelines (for example `make openapi`) and fully suppress
`stdout/stderr`, CI failures become opaque (`CalledProcessError` only), which blocks
fast triage and encourages blind reruns.

### Real incident (main CI, 2026-02-25)
`tests/test_openapi_determinism.py` failed in `test-main (3.12)` with
`Command '['make', 'openapi']' returned non-zero exit status 2`, but no actionable
stderr was available in job logs because both streams were redirected to `DEVNULL`.

### Rule
For subprocess-based deterministic tests:
1. capture subprocess output (`capture_output=True`, `text=True`)
2. on failure, emit bounded `stdout/stderr` tails in pytest failure message
3. allow a single retry for transient toolchain/network hiccups, then fail-closed

### Use instead
- helper wrappers that centralize retry + bounded log tail emission
- clear failure messages with command, exit code, and log tails
- deterministic assertions remain strict after command succeeds

## 18) Natural-language AI/RAG/cache governance needs one source of truth

### Problem
Governance PRs for AI, RAG, linguistics, philosophy admission, and semantic-cache
boundaries can drift when the same policy is expressed independently in prose,
machine state, schemas, validator regexes, downstream docs, and fixed-mapping
artifacts. Review waves then find semantically equivalent bypasses, stale
ledger status, orphaned deferred review comments, or wording that implies a
closed gate is active.

### Rule
For natural-language policy or claim guards:

1. Choose one canonical contract or ledger item as the source of truth.
2. Treat regexes as a generated or bounded enforcement layer, not as the policy
   model itself.
3. Add equivalence-class regression tests for actor/action/object, modality,
   tense, polarity, and negative controls when claim wording matters.
4. Keep ledger status, roadmap prose, schemas, validators, downstream docs, and
   fixed-mapping artifacts aligned in the same PR.
5. Do not close a backlog checkbox while a DEFERRED review item still points at
   that same anchor unless the deferred item is fixed or retargeted with evidence.
6. Never let closeout wording imply semantic-cache activation, backend approval,
   serving readiness, or runtime truth when machine-checkable gate markers remain
   closed.

### Use instead
- Structured policy state plus schema validation when a contract has machine state.
- Parsed/section-aware docs checks for downstream claim validation.
- Small closeout tests that assert the ledger, roadmap, gate markers, and review
  artifacts agree.

---

## 19) Verify merged state before cherry-picking long-lived branches (conflict prevention)

### Problem
Cherry-picking older feature branch commits after partial upstream merges can create avoidable
conflicts and duplicate logic.

### Rule
Before cherry-picking:
1. check if commits are already merged via `git log origin/main..feature_branch`
2. inspect file history (`git log -- <file>`) for equivalent merged PRs
3. if upstream already contains the runtime path, continue with the next unimplemented DoD item
   instead of replaying stale commits

### Use instead
- prefer fresh branch from `origin/main`
- implement only remaining acceptance gaps (benchmark/report/tests/rollback notes)
- avoid replaying historical commits that represent already-merged behavior

---

## 20) Enforce kcal upper bounds at API response boundaries (property-test hardening)

### Problem
Hypothesis can discover extreme valid profiles where generated `plate`/`targets`
calories drift slightly above expected contract bounds (for example `5006`),
creating nondeterministic CI failures in full-suite property tests.

### Rule
For nutrition response contracts with explicit kcal ranges:
1. clamp final API response calories at the boundary layer (`min/max`)
2. apply the same bound in fallback and primary paths
3. keep hypothesis/property tests as regression locks for edge profiles

### Use instead
- response-boundary clamps (`max(1200, min(kcal, 5000))`)
- shared bounds for `/premium/plate` and `/premium/targets` compatibility aliases
- deterministic property tests to catch future drift

---

## 20) Experiment Runner attribution follows material evidence contribution, not mutation

### Problem
Oracle-only Experiment Runner artifacts intentionally report `mutated_paths: []`,
but agents can misread that safety invariant as proof that the runner made no
engineering contribution.

### Rule
For Experiment Runner PR evidence:
1. treat `mutated_paths: []` as the mutation boundary only
2. require the canonical co-author trailer when a referenced artifact has
   `coauthor_required: true` because it shaped the plan, validation, admission,
   fixed mapping, review disposition, or commit decision
3. do not add the trailer when the runner only launched, the artifact was
   rejected or unused, or `Not applicable: <reason>` is recorded

### Use instead
- explicit `contribution_kind`, `coauthor_required`, and `coauthor_reason` fields
- review-only diagnostics as supporting evidence, with mandatory execution for
  non-trivial PRs
- the governed trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

---

## 21) Merged AI/RAG lanes become closeout, not duplicate runtime work

### Problem
Backlog or roadmap text can lag live GitHub truth. Reopening the same AI/RAG
runtime scope from stale docs risks duplicate implementation, stale review
mapping, and accidental semantic-cache/runtime widening.

### Rule
When a roadmap lane appears open but repo/GitHub evidence proves its runtime PR
already merged:
1. convert the next PR into closeout/reconciliation
2. record PR number, title, merge timestamp, merge commit, and original branch
3. add a guard/test that prevents stale active/pending wording from returning
4. keep broader parent checklist items open unless the full DoD is separately proven

### Use instead
- landed-symbol evidence plus fixed mapping artifacts
- explicit benchmark-boundary wording for hypothesis targets
- semantic-cache gate markers as machine-checkable invariants

---

## 22) Do not loop on synthetic squash-preview review comments

### Problem
Automated review tools can review a synthetic squash/current-head commit that is
not the live PR branch head. If agents respond by adding another mapping-only
commit for every repeated synthetic hash, the next push can generate a new
synthetic hash and restart the same review loop.

### Real incident pattern
Governance PRs with Experiment Runner attribution and fixed-mapping evidence can
receive repeated comments saying:

- mapped commits are not ancestors of the synthetic squash-preview commit
- the synthetic squash-preview commit message lacks the Experiment Runner
  `Co-authored-by` trailer

The live branch history can still be correct, and the final squash merge message
can still preserve the trailer, while each new mapping commit creates a fresh
review target.

### Rule
When the same synthetic squash-preview concern repeats:

1. Fix real code or workflow defects exactly once.
2. Record one stable disposition with live branch-head evidence.
3. Put the required squash-merge trailer in the PR body as raw trailer text, not
   only inside prose or code fences.
4. Do not keep creating mapping-only commits for each new synthetic hash.
5. If the bot repeats the same already-dispositioned synthetic concern after the
   stable evidence is present, stop and escalate to the operator or repo
   governance owner instead of entering a commit/review loop.

### Use instead
- Live branch ancestry checks against `HEAD`.
- Exact review-thread dispositions for the first occurrence.
- One raw PR-body squash trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`
- A clear PR comment explaining that the synthetic hash is not the canonical
  pre-merge branch-history proof.

## 23) Advisory wording must not make role gates skippable

### Problem
Bootstrap packets can carry readonly/custom-role bindings that older docs called
advisory. Agents then risk treating assigned roles, premortem, Experiment
Runner, or post-open review as optional commentary even though the PR lane
depends on those gates.

### Rule
For non-trivial PRs:
1. execute every bootstrap-requested or coordinator-assigned custom role in the
   declared manifest order through `role_dispatch_bridge.py`
2. do not normalize pre-open requested role order or explicit `--roles` fallback
   dispatch into the post-open `qa-engineer-agent -> bug-hunter -> security-auditor`
   tail
3. scoped `AGENTS.md` files must not narrow the repo-global post-open review
   gate; use a superseding repo-global reference when historical lane bullets
   would otherwise omit `security-auditor`, current-head security checks, or
   `pulseplate-pr-review`
4. run `pulseplate-premortem-risk-review` and Experiment Runner oracle-only
   evidence before PR open
5. after PR open, run `qa-engineer-agent -> bug-hunter -> security-auditor`,
   exact-material `pulseplate-pr-review`, disposition every actual finding, and
   author the provider-neutral no-claim seal without invoking or waiting for
   Connector/Codex Security; independently available provider output stays
   advisory and creates no PASS/no-findings claim
6. when a recurring governance rule emerges, update the smallest authoritative
   instruction surfaces in the same PR: scoped/root `AGENTS.md`, `RUNBOOK_AGENT.md`,
   workflow/contract docs, and this lessons file

### Use instead
- "required readonly/custom-role pass" for mandatory role execution
- explicit `FIXED`, `NOT-A-BUG`, or `DEFERRED` disposition for any finding
- backlog evidence before intentionally deferring a real risk

## 24) Positive enumeration beats stale-SHA-only workflow guards

### Problem
Action-runtime cleanup PRs can enter a fix-commit loop when reviewers find one
more stale workflow pin after each push. A guard that only bans a few known old
SHAs can miss a newly discovered active workflow surface.

### Rule
For GitHub Actions runtime migrations, guard the whole active action surface:

1. enumerate every active `.github/workflows/*.yml` and `*.yaml` workflow
2. assert every matching `uses:` family points at the approved pinned SHA
3. keep old-SHA denylist checks as a backstop, not the only proof
4. exclude disabled/historical workflow templates unless the lane explicitly
   reactivates or scopes them

### Use instead
- positive tests such as "every active `actions/upload-artifact@*` use equals
  the Node 24 SHA"
- targeted old-SHA denylist entries for known regressions
- one coherent guard update before publishing, rather than mapping-only
  follow-up commits after each bot rediscovery

## 25) Pre-commit-selected tests must not rely on async pytest plugin state

### Problem
CI lint runs `pre-commit run --all-files`, and the local `backend-tests` hook
selects changed Python tests through `scripts/run-backend-tests-pre-commit.sh`.
That hook can execute in an environment where `pytest-asyncio` is not installed
or not loaded, even when the developer venv or a broader pytest run has it.

When a changed diff-coverage test uses `pytest.mark.asyncio` or an `async def`
test function, the CI-only lint failure can look like:

- `async def functions are not natively supported`
- `PytestConfigWarning: Unknown config option: asyncio_mode`
- `PytestConfigWarning: Unknown config option: asyncio_default_fixture_loop_scope`

This is an environment/plugin-state drift, not a product bug, but it still
breaks the PR because lint owns the pre-commit backend-tests hook.

### Real incident (PR #2006)

PR #2006 changed `tests/test_diff_coverage_pr339.py`. Local focused tests and
`pre-commit run --all-files` passed in the developer environment, but
current-head CI lint failed when the backend-tests hook selected that file without the
async pytest plugin loaded. The first failure appeared on one parametrized async
test, but the file contained multiple async tests that would have failed next.

### Rule

For tests selected by `scripts/run-backend-tests-pre-commit.sh`, especially
diff-coverage and changed-file tests:

1. Do not add `pytest.mark.asyncio` or `async def` test functions unless the
   hook environment is explicitly proven to load the async plugin.
2. Prefer sync tests that call simple router/service coroutines with
   `asyncio.run(...)`, or exercise route behavior through FastAPI `TestClient`.
3. After fixing the first async-marker failure, scan the entire selected test
   bundle for `pytest.mark.asyncio` and `async def`; do not stop at the first
   failing test.
4. Validate with the exact backend-tests hook path:

```bash
VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" BRANCH_DIFF_MODE=1 bash scripts/run-backend-tests-pre-commit.sh
pre-commit run --all-files
```

### Use instead

- Sync test wrappers around simple coroutine entrypoints:
  `response = asyncio.run(generate_week_plan(request))`.
- `TestClient` for route-level behavior when HTTP semantics matter.
- A full selected-bundle scan before pushing:
  `rg -n "pytest\\.mark\\.asyncio|async def" <selected-test-files>`.

## 26) Duplicate routes are current-PR defects, not inherited debt

### Problem
FastAPI allows registering the same method/path more than once. Runtime dispatch
uses the first matching route, while OpenAPI generation can describe a later
matching route. That creates a security and contract blind spot: tests may hit
one handler while generated clients and reviewers see another.

### Rule
If duplicate method/path routes or a foreign existing paid-tier route surface in
a PR, fix them in that PR before mapping or merge-readiness claims. Do not leave
them as "known inherited" behavior merely because the original task was narrow.

Route-family registrars should fail closed on:

1. duplicate source router method/path entries
2. partial existing route-family registration
3. foreign existing handlers
4. missing required auth/tier dependencies

### Use instead

- One canonical owner per method/path.
- `ensure_route_family_registered(...)` for static route families.
- A focused live route-table test that fails on duplicate paid-tier
  method/path entries.

## 27) Premortem must close production risks in code, not just documents

### Problem
Premortem can drift into a governance artifact: the PR contains a risk document,
the risks have disposition words, and the lane appears compliant, but no new
production invariant, workflow guard, or test was added. That turns premortem
into paperwork instead of a prediction exercise against the actual diff.

### Rule
For non-trivial PRs, premortem starts from "how this exact diff could make
`main` worse in production within 48 hours." Each credible failure story must
end in one of these closures:

1. code, workflow, or test change that makes the failure fail closed
2. explicit stop-condition in the PR evidence when the risk cannot be proven
   pre-merge
3. backlog item only when the risk is genuinely out of scope and safe to defer

Do not count a premortem as complete because the document exists. Count it only
when at least one real production failure mode was actively challenged, and any
credible current-PR risk was fixed or blocked by a guard.

### Use instead

- Diff-first failure stories tied to changed files and CI/runtime behavior.
- Contract tests for every workflow or runtime invariant added by the premortem.
- PR evidence that separates pre-merge proof from post-merge proof when a lane
  such as publish cannot run automatically on pull requests.

## 28) Stop filesystem hardening at the declared transaction boundary

### Problem
Local artifact code can enter an endless sequence of pathname and timestamp
race checks while trying to prove permanent stability against another process
running as the same user. That proof needs a different ownership model, and the
extra code can become riskier than the bounded workflow it protects.

### Rule
For local creative artifacts, use cooperative locking, safe at-rest no-symlink
reads, owned same-parent staging, kernel no-replace publication, parent fsync,
deterministic replay validation, and receipt-last finalization. Preserve partial
evidence and diagnostics. Stop there: do not add directory exchange, canonical
cleanup, hostile syscall-seam tests, or claims of permanent same-UID exclusion.

If stronger exclusivity is required, stop the PR and open a separate threat-
model lane with an explicit ownership boundary instead of extending the race-
checker loop.

## 29) Treat multi-worktree patch containment as a hard safety boundary

### Problem
`apply_patch` does not inherit a shell command's working directory. In a repo
with several worktrees, an unqualified patch path can therefore modify the
primary checkout or a sibling even when inspection commands ran in the assigned
worktree. Trying to compensate with edits in the wrong tree widens the incident.

### Rule
Before patching, verify both `pwd` and `git rev-parse --show-toplevel` against
the assigned worktree. Resolve the worktree and target path canonically, reject
symlink components, and require the target to be the worktree itself or a
descendant at a path-component boundary; a raw string-prefix comparison is not
containment. After patching, inspect `git status --short` in the assigned
worktree, the primary checkout, and any relevant sibling worktree.

If any patch lands in the wrong tree, stop immediately, report the containment
failure, and restore only with explicit ownership evidence. Never compensate by
editing another checkout or sibling worktree.

## 30) Validate the complete live review inventory before the one closeout commit

### Problem
Checking only discussion threads before the final mapping commit misses two
independent contracts: actionable top-level bot reviews also need explicit
mapping, and a plain-text artifact path is not the required Markdown link in the
live PR body. Discovering either omission after push creates an avoidable CI and
bot-review cycle.

### Rule
After the closeout tool writes the local canonical artifact and after the live
PR body is updated, run `python scripts/orchestration/check_merge_ready.py
--pr-number <PR_NUMBER> --repo Katsiarynakavaleuskaya/PulsePlate --pre-closeout
--require-auth` before creating the sole mapping commit. Export both `GH_TOKEN`
and `GITHUB_TOKEN`. The canonical mapping artifact must be the only dirty path.
The pass must compare the uncommitted artifact with all live actionable bot
issue comments, bot inline comments, and top-level bot reviews, and must
find exactly one rendered same-repository
`blob/<exact-live-head-ref>/...` Markdown link to the canonical artifact. The
ref path must equal the authenticated PR `head.ref`, which avoids treating an
extra file-path segment as part of a slash-containing branch name. The link must
be a standalone bullet, and the decoded canonical URL may occur only once; raw
HTML/code examples and repo-relative links do not count. The gate must re-read the body, content-bound
actionable inventory, and local dirty-path set before PASS so async bot activity
or a concurrent local edit cannot create a false-green snapshot. An actionable
review summary needs its own mapping even when all child comments are mapped.

This is a commit-ordering gate, not a merge verdict: unresolved threads,
current-head CI, and the mandatory wait cycle remain for the normal strict
post-push wrapper.

## 31) Close bot fix loops at the invariant boundary

### Problem
Bot findings can have different reproducers yet still form one structural
fix-loop: each push closes one carrier, parser edge, or authority path while
leaving the same underlying invariant incomplete. These are not literal repeats
covered by lesson 22, but fixing each example independently recreates the
enumeration failure from lesson 24.

### Rule
Before changing code, group new reproducers by the invariant they violate:

1. Call a graph finite only when one mechanically closed source of truth
   determines every member. A hand-maintained list is not a completeness proof.
2. Import resolution, implicit tool configuration, plugin discovery,
   executable file formats, and arbitrary build/runtime semantics are
   open-world surfaces. Do not claim they are complete by adding the latest
   carrier to an allowlist or custom parser.
3. Fix one materially novel current-surface P1 at the smallest honest class
   boundary with targeted regression evidence.
4. When a second novel carrier exposes the same open-world assumption, stop the
   example-by-example fixes and reset scope: remove or roll back the unsound
   mechanism, retain only bounded controls whose claims match their proof, and
   record residual risk explicitly.
5. An exact repeat without a new reproducer reuses its existing disposition and
   does not justify another material commit.

Stop when the bounded claim is true, not when the current examples happen to
pass. Broader runtime modeling belongs in a separately scoped lane.

## 32) Restart closeout only after a real material correction

### Problem
A review finding that arrives after the mapping-only closeout can look like a
deadlock: the existing seal names the pre-closeout material head, another docs
commit would no longer be its direct successor, and an operator bypass would
weaken review governance. This becomes a self-created loop when the old
`material_head_sha` is treated as permanent. It also becomes a loop when an
agent tries to reseal the same digest or invents a carrier commit merely to
obtain another mapping-only successor.

### Rule
Classify the new review item before choosing the recovery path:

1. Use the reply-only path only for a validated same-digest duplicate whose
   fingerprint already exists in the canonical mapping artifact.
2. If no matching canonical fingerprint exists, the finding is canonical for
   this closeout state. A same-digest reseal and a second mapping-only commit
   are forbidden.
3. Wait for every current-head CI job to reach a terminal state before
   promoting the review fix.
4. If no mapping-only successor exists yet and the finding exposes a real
   defect in code, tests, policy, or documentation, correct that defect by
   advancing the current material commit. The correction creates the new
   material head and digest; it is not a synthetic carrier.
5. Run the required narrow local bundle, push the material correction, and
   again wait for terminal current-head technical CI. Only then freeze the new
   digest, run exact-material self-review, collect the stable live review
   inventory, author dispositions, and publish exactly one direct mapping-only
   successor.
6. If a mapping-only successor already exists, no real correction may be
   appended on top of it. Keep the finding unresolved and supersede the PR from
   a clean current base through the normal coordinator-owned replacement flow,
   where the correction advances material before that PR's sole mapping-only
   successor.
7. If there is no honest material defect to correct, do not manufacture one.
   Use the validated reply-only path when its fingerprint contract applies;
   otherwise keep the finding unresolved and use the same clean replacement
   flow.
8. Do not wait for an unrelated `main` advance, enumerate reviewer execution
   refs, force-push history, or use generic operator approval to bypass the hard
   disposition gate. The only owner response recognized without a canonical
   fingerprint or FIXED mapping is the closed empty-mapping class: after an
   explicit human decision, one exact GraphQL-`OWNER` reply may say
   `OWNER NOT-A-BUG: ignore unavailable reviewer ref <full-40-sha>; authenticated live PR graph is authoritative.`
   It applies only to one resolved connector root on the canonical mapping file
   whose `originalCommit` is the exact live direct mapping-only successor, whose
   sealed digest recomputes, and whose body names the sealed material SHA while
   binding the selected ref either to `not an ancestor of` or an explicit
   reviewer-ref/unavailable-ref label. An unrelated SHA mention is insufficient.
   The selected ref must be definitively unavailable; unknown
   or real refs and multiple eligible roots remain blocking. Count every live
   thread root before URL-only disposition filtering, and bind authenticated
   evidence to the case-insensitively equal snapshot repository. The validator
   never posts the reply or sends the unavailable ref to ancestry. When it covers
   the root, the exact reply plus resolved thread is the disposition evidence;
   do not add another mapping entry or docs commit. Non-covered roots remain
   subject to ordinary mapping.

The mapping artifact remains excluded from the material digest. Every real
correction must be based on and advance material, invalidate the prior seal,
and be followed by exactly one mapping-only successor. A prior mapping-only
live head must never host the correction. This preserves the one-successor
invariant without freezing an obsolete head or turning every new reviewer ref
into another parser variant.

### Use instead

- Finish current-head CI, then query the live thread and canonical fingerprint
  inventory.
- Re-freeze only after a real material correction and its current-head
  technical CI.
- Reuse a structured reply only when the validator can bind it to an existing
  same-digest fingerprint record.
- For the disjoint empty-mapping owner-only class, obtain explicit human
  confirmation and use only the exact one-line response; do not translate it
  into another mapping, fingerprint, generic approval, or parser variant.
- Treat a strict-wrapper disposition failure as evidence to restart the
  governed recovery, not as grounds for a carrier commit or operator merge
  exception.

## 33) Keep one dependency identity by default; batch only an exact scanner snapshot

### Problem
One dependency can carry several advisory variants, so advisory count is not a
safe PR boundary. Unbounded batching is equally unsafe: it lets a candidate
select convenient findings, omit another identity from the same scanner state,
or treat one repaired member as success. Suppression changes also need their own
fail-closed boundary.

### Rule
The default application-dependency lane defines one identity with `D`, `S`,
`R`, and `P`, evaluated against one finite reconciled candidate inventory
`F_cutoff` whose base-applicable subset `A` is non-empty:

1. **`D` — ecosystem-qualified dependency identity:** exactly one dependency
   identity in exactly one ecosystem by default.
2. **`S` — governed surface universe:** independently enumerate the complete
   governed manifest and lock surfaces for `D` at the exact base (`S_base`) and
   head (`S_head`). Their union `S = S_base ∪ S_head` must be non-empty, and
   every base/head surface delta must be reconciled.
3. **`A` — applicable advisory inventory:** reconcile a finite candidate set
   `F_cutoff` from named authoritative inputs at one recorded snapshot or
   cutoff. `A` is exactly the non-empty subset whose every member has at least
   one comparable governed base occurrence of `D` inside its affected range.
   Every candidate outside `A` requires an independently evidenced
   non-applicable-at-base disposition and remains inside `P`, which must prove
   no affected, unresolved, or incomparable governed head occurrence.
4. **`R` — operator-intent remediation class:** let `I_R` be the non-empty set
   of intent-bearing dependency transitions explicitly authored or authorized
   to remediate `D`. Exactly one non-identity equivalence class is admitted over
   `I_R`: every member has the same authored operation kind and semantic intent.
   Authored replacement and authored removal are different classes; literal
   target versions may be parameters of one replacement class. Let `C_R` be the
   deterministic solver closure produced from the exact base by applying only
   `I_R` with the recorded canonical resolver version, configuration, and
   command. `C_R` may contain mixed occurrence shapes from mechanically coupled
   replacement, addition, hoisting, deduplication, or removal, but carries no
   independent intent or remediation claim. Every material dependency
   transition must belong to exactly one of `I_R` or replay-proven `C_R`; manual,
   unclassified, or unreplayable transitions fail admission. An aggregate goal
   such as "make safe" is `P`, not `R`.
5. **`P` — remediation postcondition:** after reconciling `S_base` and `S_head`,
   for every candidate advisory in `F_cutoff`, the deterministic guard must
   resolve every governed occurrence of `D` on every `S_head` surface to an
   advisory-comparable value outside that candidate's affected range, or prove
   executable absence of `D` for that surface. A candidate outside `A` does not
   gain a remediation claim, but it still cannot become affected at head. Every
   base-only surface must be reconciled under `R`; any unparseable or unresolved
   head occurrence or unreconciled surface delta fails `P`.

The parseable invariant-class relation in the uniquely marked `AGENTS.md` JSON
authority, not sentence variants, is the guard authority. This lesson mirrors
that relation for humans and does not create a second machine-readable
authority.

The v2 exception is deliberately narrow and has prospective repository effect
only after merge. A direct external operator instruction issued outside a
candidate diff may separately authorize the exact transition that changes this
policy together with its exact bounded dependency material; this does not make
candidate text effective early and grants no general or future batch authority.
For current and future batches, the operator names one immutable terminal
full-repository scanner run/analysis and authorizes the complete unresolved
identity set derived from it. The candidate PR, its policy/docs/tests, the
scanner, and agents cannot self-authorize, infer, authenticate, or widen the
instruction. All identities share one ecosystem; each gets exactly one authored
replacement or removal action; the resolver closure is replayed from the exact
base; and `P` is the conjunction across the entire set. Omission, addition,
partial success, or an unclassified delta fails.

Advisories are independently auditable variants within that class, not the
class boundary. Canonical evidence must record the named authoritative input or
inputs and snapshot or cutoff used for `F_cutoff`. Every triggering alert and
every current scanner/audit finding for `D` at that cutoff must be in
`F_cutoff`. A candidate belongs to `A` if and only if at least one comparable
governed base occurrence is inside its affected range; every other candidate is
independently dispositioned as non-applicable at base with evidence and remains
inside the universal head-safety check in `P`. `A` must retain at least one
applicable advisory for a
remediation lane. If reconciliation leaves `A` empty or finds no applicable
affected base occurrence for `D`, use a separate disposition-only lane: it must
not mutate dependency state, claim remediation or `P`, or mix with a
non-empty-`A` lane. The non-empty finite reconciled `A` bounds the remediation
claim; `F_cutoff` bounds `P`. Neither makes a claim about genuinely undisclosed
or future advisories.
Advisory affected ranges and remediation floors may differ. Equality of
advisory remediation floors is not a batching prerequisite.

Exactly one owner document under `docs/security/` must own each `D`/`S`/`R`/`P`
class. Supporting stable in-repo artifacts may exist only when linked from that
owner document. A PR body, issue, or ledger entry alone cannot replace the
owner document. Each candidate in `F_cutoff` retains one independently auditable
record containing its advisory ID, affected range, authoritative source,
governed base/head surfaces, base-applicability proof or
non-applicable-at-base disposition, universal head-safety proof, and
scanner/audit result. Each member of `A` additionally records its remediation
floor, selected target, governed affected base occurrence, and deterministic
proof of `I_R`, `C_R`, and `P`.

Without either the exact external policy-transition instruction for a candidate
changing this rule or, after v2 is effective, a qualifying external
scanner-batch instruction, any difference in `D` requires a separate PR.
Under the exception, the owner document and one-time resolver replay record the
complete derived set, every identity's base/head surfaces and witnesses, and the
complete dependency JSON delta partitioned into authored actions or solver
closure. Permanent guards independently discover current tracked head surfaces
and enforce aliases/malformed-state rejection plus universal `F_cutoff`
postconditions; they must not freeze the incident base/delta and thereby block
future authorized dependency changes. The only suppression mutation allowed in
the batch is deletion of the exact obsolete suppression for an identity
remediated by that same batch. A suppression addition, broadening, replacement,
or unrelated deletion is never closure and remains forbidden.

---

## Repo Commands Reference

```bash
# Import hygiene / repo policy
pytest -q tests/test_repo_policy_guards.py

# VIP-only guard: forbid sys.modules mutations
pytest -q tests/test_repo_policy_sys_modules.py

# Smoke test
make test-fast

# Coverage
make cov-check

# Lint / format
make lint && make fmt-check

# Detect forbidden sys.modules mutations in tests (manual scan)
git grep -nE "sys\.modules\[[^]]+\]\s*=|del\s+sys\.modules\[" -- tests
```

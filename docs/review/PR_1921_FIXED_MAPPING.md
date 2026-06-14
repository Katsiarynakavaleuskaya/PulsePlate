# PR #1921 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921

Branch: `codex/fix-vulnerability-in-mcp-examples`

Primary fix commits: `167a551c524d16c169ceec5555dec27fa06f8755`, `33e1d2222ee6eaf2a88779327bd5c6ace3388c9d`, `9453bbc2db93fd4422ef7952a7a0d78242692343`, `8f5447c6be9f50ce615ab273deaf27017f6a4e0d`, `9a77a2ce364a673eeeb675daa2ecc805758bdeb0`, `24f5ca975902eb9137e195df0d1f6052e026d814`

Scope: MCP example security defaults, root MCP setup/config examples, governed Context7 runbook pinning, guard coverage, and review-governance closeout only. No backend runtime, OpenAPI, frontend runtime, iOS, database, or product behavior changes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3380615348 -> 167a551c524d16c169ceec5555dec27fa06f8755
Disposition: FIXED
Commit: 167a551c524d16c169ceec5555dec27fa06f8755
Evidence: `tests/guards/test_mcp_examples_safe_defaults.py:26` identifies the first non-option `npx` package arg, including unscoped packages; `tests/guards/test_mcp_examples_safe_defaults.py:138` adds an unscoped package regression case.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3380635326 -> 167a551c524d16c169ceec5555dec27fa06f8755
Disposition: FIXED
Commit: 167a551c524d16c169ceec5555dec27fa06f8755
Evidence: `tests/guards/test_mcp_examples_safe_defaults.py:12` defines `PLAYWRIGHT_MCP_ALLOW_UNRESTRICTED_FILE_ACCESS`; `tests/guards/test_mcp_examples_safe_defaults.py:62` rejects truthy Playwright env values; `tests/guards/test_mcp_examples_safe_defaults.py:142` covers truthy regressions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3380635330 -> 167a551c524d16c169ceec5555dec27fa06f8755
Disposition: FIXED
Commit: 167a551c524d16c169ceec5555dec27fa06f8755
Evidence: `tests/guards/test_mcp_examples_safe_defaults.py:35` parses package specs with `rsplit("@", 1)` and exact numeric version regex; `tests/guards/test_mcp_examples_safe_defaults.py:115` rejects missing, tag, range, and malformed package versions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3380635336 -> 167a551c524d16c169ceec5555dec27fa06f8755
Disposition: FIXED
Commit: 167a551c524d16c169ceec5555dec27fa06f8755
Evidence: `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:87`, `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:134`, and `docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md:262` pin governed local Context7 `npx` examples to `@upstash/context7-mcp@3.1.0`; `tests/guards/test_mcp_examples_safe_defaults.py:93` scans the governed runbook.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#pullrequestreview-4458559694 -> 167a551c524d16c169ceec5555dec27fa06f8755
Disposition: FIXED
Commit: 167a551c524d16c169ceec5555dec27fa06f8755
Evidence: Sourcery aggregate feedback about CWD-sensitive pathing and brittle package parsing is covered by `tests/guards/test_mcp_examples_safe_defaults.py:8` repo-root path resolution, `tests/guards/test_mcp_examples_safe_defaults.py:26` package-arg discovery, and the focused `/tmp` CWD pytest run.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409638961 -> 33e1d2222ee6eaf2a88779327bd5c6ace3388c9d
Disposition: FIXED
Commit: 33e1d2222ee6eaf2a88779327bd5c6ace3388c9d
Evidence: `tests/guards/test_mcp_examples_safe_defaults.py:135` now counts governed Context7 matches and `tests/guards/test_mcp_examples_safe_defaults.py:144` fails if the runbook has no governed Context7 examples, preventing vacuous pass.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#pullrequestreview-4493009748 -> 33e1d2222ee6eaf2a88779327bd5c6ace3388c9d
Disposition: FIXED
Commit: 33e1d2222ee6eaf2a88779327bd5c6ace3388c9d
Evidence: CodeRabbit aggregate review `4493009748` reported the same governed Context7 vacuous-pass finding as `#discussion_r3409638961`; `tests/guards/test_mcp_examples_safe_defaults.py:135` counts governed Context7 matches and `tests/guards/test_mcp_examples_safe_defaults.py:144` fails if the runbook has no governed Context7 examples.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409643743 -> 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Disposition: FIXED
Commit: 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Evidence: `mcp-config.json:4` now uses the documented Python-packaged `uvx` invocation and `mcp-config.json:5` pins it to `mcp-server-openai==0.1.4`; `mcp-setup.sh:8` requires `uvx` and `mcp-setup.sh:16` documents the same exact package pin. The earlier unpublished ChatGPT npm example remains removed, and the questionable `mcp-server-openai@0.0.1` npm install/config path is gone.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#pullrequestreview-4493037035 -> 9453bbc2db93fd4422ef7952a7a0d78242692343
Disposition: FIXED
Commit: 9453bbc2db93fd4422ef7952a7a0d78242692343
Evidence: CodeRabbit aggregate review `4493037035` reported that `test_mcp_examples_pin_npx_mcp_packages` could pass vacuously if all governed `npx` examples disappeared; `tests/guards/test_mcp_examples_safe_defaults.py:121` now initializes a match counter, `tests/guards/test_mcp_examples_safe_defaults.py:129` increments it for each governed `npx` server, and `tests/guards/test_mcp_examples_safe_defaults.py:135` fails if no governed `npx` MCP server examples are found.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409723246
Disposition: NOT-A-BUG
Evidence: The review referenced non-current submitted head `bd7de97570cf133ebea802afe4b4e8e4eb48bebf`. At local PR head `8f5447c6be9f50ce615ab273deaf27017f6a4e0d`, `git merge-base --is-ancestor 167a551c524d16c169ceec5555dec27fa06f8755 HEAD`, `git merge-base --is-ancestor 33e1d2222ee6eaf2a88779327bd5c6ace3388c9d HEAD`, and `git merge-base --is-ancestor 9453bbc2db93fd4422ef7952a7a0d78242692343 HEAD` all returned `0`, proving all mapped FIXED proof commits are ancestors of the current PR branch.
Reason: The comment evaluated a stale/non-current submitted commit, not the actual PR branch head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409723248 -> 8f5447c6be9f50ce615ab273deaf27017f6a4e0d
Disposition: FIXED
Commit: 8f5447c6be9f50ce615ab273deaf27017f6a4e0d
Evidence: `opencode.json:25` now pins the checked-in Opencode Cloudflare MCP `npx` command to `@cloudflare/mcp-server-cloudflare@0.2.0` after `npm view @cloudflare/mcp-server-cloudflare version` returned `0.2.0`; `tests/guards/test_mcp_examples_safe_defaults.py:21` registers `opencode.json` as a governed MCP example, `tests/guards/test_mcp_examples_safe_defaults.py:107` parses Opencode `mcp.*.command` arrays, and `tests/guards/test_mcp_examples_safe_defaults.py:153` enforces exact pins for those `npx` package args.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409723249 -> 8f5447c6be9f50ce615ab273deaf27017f6a4e0d
Disposition: FIXED
Commit: 8f5447c6be9f50ce615ab273deaf27017f6a4e0d
Evidence: `git log -1 --pretty=raw 8f5447c6be9f50ce615ab273deaf27017f6a4e0d` shows the required trailer `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on the post-comment commit carrying the latest accepted runner-shaped closeout work.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409745075
Disposition: NOT-A-BUG
Evidence: The review referenced synthetic reviewed/squashed head `a194529962d802c9d2f5f89c6e74a91cf5524d49`, not the GitHub PR branch head. In the local PR branch after `24f5ca975902eb9137e195df0d1f6052e026d814`, every mapped FIXED proof commit listed above remains in first-parent history; the connector's synthetic commit is not the branch commit used by GitHub current-head checks or the strict merge wrapper.
Reason: The comment evaluates a non-branch synthetic review commit. The actual PR branch contains the mapped proof commits.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409745078 -> 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Disposition: FIXED
Commit: 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Evidence: `git log -1 --pretty=raw 9a77a2ce364a673eeeb675daa2ecc805758bdeb0` shows `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on the post-comment implementation commit carrying accepted runner-shaped closeout work.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409745081 -> 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Disposition: FIXED
Commit: 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Evidence: `python3 -m pip download --no-deps mcp-server-openai==0.1.4` showed PyPI metadata for `mcp-server-openai 0.1.4` with console script `mcp-server-openai = mcp_server_openai.server:main`; `mcp-config.json:4` switches the root example to `uvx`, `mcp-config.json:5` pins `mcp-server-openai==0.1.4`, and `mcp-setup.sh:8`/`mcp-setup.sh:16` mirror that Python-package setup instead of `npm install -g mcp-server-openai@0.0.1`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409745083 -> 24f5ca975902eb9137e195df0d1f6052e026d814
Disposition: FIXED
Commit: 24f5ca975902eb9137e195df0d1f6052e026d814
Evidence: `docs/review/PR_1921_FIXED_MAPPING.md` local validation evidence now uses repo-relative commands such as `.venv/bin/python -m pytest ...`; a direct scan of the PR #1921 review artifacts for local home-directory paths returned no matches.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409745084 -> 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Disposition: FIXED
Commit: 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Evidence: `tests/guards/test_mcp_examples_safe_defaults.py:123` parses setup-script command lines, `tests/guards/test_mcp_examples_safe_defaults.py:230` checks every setup-script line for protected env-file reads, and `tests/guards/test_mcp_examples_safe_defaults.py:287` covers equivalent dump commands including `cat "$HOME/.cursor/.env"`, `sed`, `grep`, and `tail`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409745087 -> 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Disposition: FIXED
Commit: 9a77a2ce364a673eeeb675daa2ecc805758bdeb0
Evidence: `tests/guards/test_mcp_examples_safe_defaults.py:13` tokenizes exact Context7 package mentions, `tests/guards/test_mcp_examples_safe_defaults.py:208` validates every token rather than a substring, and `tests/guards/test_mcp_examples_safe_defaults.py:280` covers a mixed pinned-plus-unpinned line.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409643744
Disposition: NOT-A-BUG
Evidence: Local current-head ancestry check returned `ancestor_167_to_head=0` for `git merge-base --is-ancestor 167a551c524d16c169ceec5555dec27fa06f8755 HEAD`, and `HEAD` was `33e1d2222ee6eaf2a88779327bd5c6ace3388c9d`; therefore commit `167a551c524d16c169ceec5555dec27fa06f8755` is present in the current PR branch history.
Reason: The review referenced a stale/non-current reviewed head. The current PR head contains the mapped implementation commit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409674753
Disposition: NOT-A-BUG
Evidence: After `git fetch origin codex/fix-vulnerability-in-mcp-examples`, the remote PR branch head was `89132a0ce71de4e43bff86b337812ef651f8eab6`; `git merge-base --is-ancestor 167a551c524d16c169ceec5555dec27fa06f8755 89132a0ce71de4e43bff86b337812ef651f8eab6` returned `0`, and `git merge-base --is-ancestor 33e1d2222ee6eaf2a88779327bd5c6ace3388c9d 89132a0ce71de4e43bff86b337812ef651f8eab6` returned `0`. GitHub PR API also reported `headRefOid=89132a0ce71de4e43bff86b337812ef651f8eab6`.
Reason: The review referenced `de1ee831e7f6ec9555221ffa20b7a9aa2cb0d566`, which is not the GitHub PR head for PR #1921. The submitted PR branch contains the mapped proof commits.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#discussion_r3409643745
Disposition: NOT-A-BUG
Evidence: The historical CodeRabbit rate-limit issue comment below is not used as CodeRabbit PASS proof. Merge readiness remains blocked until current-head CodeRabbit reports PASS/no-actionables after the latest push; the fresh CodeRabbit actionable finding is mapped separately at `#discussion_r3409638961`.
Reason: A skipped/rate-limited CodeRabbit issue comment is governance noise, not an external-review pass signal. Current-head CodeRabbit status remains a merge-readiness prerequisite.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1921#issuecomment-4659749243
Disposition: NOT-A-BUG
Evidence: CodeRabbit reported a review-skip/rate-limit/credits condition rather than a code finding. This historical issue comment is not counted as CodeRabbit PASS/no-actionables proof; current-head CodeRabbit PASS remains required before merge readiness. The fresh CodeRabbit actionable finding is mapped separately at `#discussion_r3409638961`, and Codex Security local diff scan `/tmp/codex-security-scans/PulsePlate-pr1921-closeout/753508986_20260614T072240Z/report.md` found no reportable security candidates after the patch.
Reason: A skipped external review is governance noise, not a defect in the MCP example hardening diff and not a substitute for current-head CodeRabbit PASS.

## Late Post-Open Premortem

Artifact: `docs/review/PR_1921_PREMORTEM.md`

Decision: proceed with changes. Findings were fixed before this mapping artifact:

- Governed runbook examples could remain unpinned.
- Governed Context7 runbook coverage could pass vacuously if the examples were removed.
- Playwright unrestricted filesystem access could be reintroduced through `env`.
- Scoped-only package parsing could miss unscoped `npx` packages.
- Root MCP config/setup examples could continue to teach unpinned or unpublished packages.
- The setup helper could print an existing local `.env` file while replacing it.

## Role Dispatch Evidence

- Packet: `artifacts/orchestration/task_packets/7386ce628626.json`
- Dispatch bridge: `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/7386ce628626.json --pretty`
- Required role order executed: `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`
- Mandatory post-open role agents executed before implementation: `qa-engineer-agent`, `bug-hunter`, `security-auditor`

## Codex Security Diff Scan

- Local scan report: `/tmp/codex-security-scans/PulsePlate-pr1921-closeout/753508986_20260614T072240Z/report.md`
- Local HTML report: `/tmp/codex-security-scans/PulsePlate-pr1921-closeout/753508986_20260614T072240Z/report.html`
- Result: no reportable security findings remained in the two-file local patch.
- Note: the callable Codex Security MCP diff-scan tool was not exposed by `tool_search`; the installed Codex Security diff-scan skill was applied locally with explicit worklist and ledger receipts.

## PulsePlate PR Review

- Context: `/tmp/pulseplate_pr1921_review_context.json`
- Report: `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr1921_review_context.json --format markdown`
- Finding closure: missing fixed-mapping artifact is resolved by this file. The helper's 11-file diff warning came from comparing the original PR base SHA to head; current GitHub and local truth both show three PR files before this closeout commit via `gh pr diff 1921 --name-only` and `git diff --name-only origin/main...HEAD`.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-ef5d3fd57aeb.json`

Disposition: accepted oracle-only static review. The artifact sets `coauthor_required=true` with `contribution_kind=commit_decision`, and commits `167a551c524d16c169ceec5555dec27fa06f8755`, `33e1d2222ee6eaf2a88779327bd5c6ace3388c9d`, `8f5447c6be9f50ce615ab273deaf27017f6a4e0d`, `9a77a2ce364a673eeeb675daa2ecc805758bdeb0`, and `24f5ca975902eb9137e195df0d1f6052e026d814` include `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

Rejected setup artifacts `exp-12a0b4a5998e` and `exp-885e8677a2c5` were not used as proof; they failed on temporary-checkout venv resolution and shell-quote shape respectively.

## Lane Start Provenance

Packet: `artifacts/orchestration/task_packets/7386ce628626.json`

Starter: `scripts/orchestration/start_pr_lane.sh`

Preflight: `python3 scripts/orchestration/check_preflight.py --mode analyze --path .cursor/mcp.json.example --path .kimi/mcp.json.example --path docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md --path tests/guards/test_mcp_examples_safe_defaults.py` passed.

Follow-up preflight: `python3 scripts/orchestration/check_preflight.py --mode analyze --path mcp-config.json --path mcp-setup.sh --path .cursor/mcp.json.example --path .kimi/mcp.json.example --path docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md --path tests/guards/test_mcp_examples_safe_defaults.py` passed.

Bootstrap: `python3 scripts/orchestration/task_bootstrap.py --goal "Finish PR #1921 MCP example security hardening and review-governance closeout" --task-class Security --path .cursor/mcp.json.example --path .kimi/mcp.json.example --path docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md --path tests/guards/test_mcp_examples_safe_defaults.py --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent qa-engineer-agent --requested-agent bug-hunter --pr-phase post_open_review --native-bridge-transport codex-native-subagents` produced packet `artifacts/orchestration/task_packets/7386ce628626.json`.

## Local Full Verify Deferral

Full local `make verify` was not run. This PR is using the operator-approved machine-heavy exception because the repository has a large test suite and the user explicitly requested `make validate-changed` instead of full main verification.

Required replacement evidence before merge readiness:

- PR-scoped local gates: `check_preflight`, `check_agent_consistency`, focused guard pytest, `make validate-changed`, `pre-commit run --all-files`, and Phase2 body validation.
- Current-head CI: lint, PR Body Phase2 gates, Merge readiness gate, test-pr, coverage-pr, diff-coverage, security, and any branch-protection required checks.
- Strict merge wrapper with auth: `check_merge_ready.py --require-auth`.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path .cursor/mcp.json.example --path .kimi/mcp.json.example --path docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md --path tests/guards/test_mcp_examples_safe_defaults.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path mcp-config.json --path mcp-setup.sh --path .cursor/mcp.json.example --path .kimi/mcp.json.example --path docs/runbooks/OPENAI_EXTERNAL_DOCS_FRESHNESS_PILOT.md --path tests/guards/test_mcp_examples_safe_defaults.py`
- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path opencode.json --path tests/guards/test_mcp_examples_safe_defaults.py --path docs/review/PR_1921_FIXED_MAPPING.md`
- PASS: `.venv/bin/python -m pytest -q tests/guards/test_mcp_examples_safe_defaults.py` (`46 passed`)
- PASS: CWD-independent focused pytest from `/tmp` with repo `PYTHONPATH` and repo-relative test path (`46 passed`)
- PASS: `.venv/bin/python -m black --check tests/guards/test_mcp_examples_safe_defaults.py`
- PASS: `python3 -m json.tool opencode.json >/dev/null`
- PASS: `python3 -m json.tool mcp-config.json >/dev/null`
- PASS: `bash -n mcp-setup.sh`
- PASS: pre-commit hooks during commits `167a551c524d16c169ceec5555dec27fa06f8755` and `33e1d2222ee6eaf2a88779327bd5c6ace3388c9d`, including Black, Ruff, detect-secrets, and changed-file backend tests.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `make validate-changed` (`tests/guards/test_mcp_examples_safe_defaults.py`, `37 passed`)
- PASS: `pre-commit run --all-files`
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1921`

## Merge Readiness

Not claimed by this artifact. Merge readiness requires this artifact plus PR body mirror, current-head CI, disposition/merge wrappers, no unresolved actionable review threads, final bot pass, and the mandatory review wait-window.

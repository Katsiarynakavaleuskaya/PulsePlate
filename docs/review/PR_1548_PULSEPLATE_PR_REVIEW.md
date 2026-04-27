# PR #1548 — PulsePlate PR Review (post-open-review)

**Mode:** `post-open-review`
**Branch:** `feat/tier4-scientific-creative-cell-pr0` vs `origin/main`
**Review date:** 2026-04-28
**Skill:** `.agents/skills/pulseplate-pr-review/SKILL.md`

## Coordinator packet

- **Path:** `docs/orchestration/TIER4_SCIENTIFIC_CREATIVE_CELL_PR0_PACKET_2026-04-27.md`
- **Execution record:** `docs/orchestration/TIER4_PR1548_AGENT_PASS_RECORD_2026-04-27.md`
- **Scoped orchestration SoT:** `docs/orchestration/AGENTS.md` (Tier 4 lane block)
- **Role order used (this review):** Per skill default unless packet narrows compatible sequence — **packet defines phased lanes (A–H)** for Tier 4 work; this advisory review still applies the skill’s **linear review order** for findings: `agent-coordinator` → `architecture-specialist` → `security-auditor` → `backend-engineer` (Python touched) → `qa-engineer-agent` → `bug-hunter` → `data-scientist-agent` (optional). Packet phased table (A scope → B security when scripts change → … → H mandatory `qa-engineer-agent` → `bug-hunter`) is the **lane execution** contract; it does not replace the skill’s review-role checklist.

## Scope reviewed

**Files in `git diff origin/main...HEAD` (9):**

- `docs/orchestration/AGENTS.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/orchestration/PulsePlate_Local_Agent_Workforce_System_Design_Packet_v1_2.md`
- `docs/orchestration/TIER4_PR1548_AGENT_PASS_RECORD_2026-04-27.md`
- `docs/orchestration/TIER4_SCIENTIFIC_CREATIVE_CELL_PR0_PACKET_2026-04-27.md`
- `docs/review/PR_1548_FIXED_MAPPING.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `scripts/orchestration/skill_router.py`
- `tests/test_skill_router.py`

**Deep-read:** `skill_router.py` (Tier 4 constant, `creative_research` rule weights/prefixes/keywords, `_match_path_prefixes` Tier 4 branch), `tests/test_skill_router.py` (new Tier 4 tests), packet + agent pass record + Tier 4 `AGENTS.md` block + routing policy §2a paragraph + `PR_1548_FIXED_MAPPING.md`.

**Explicitly omitted:** GitHub PR checks / CodeRabbit / Sourcery / Cubic live fetch (not invoked in this review); full `make verify` / full suite re-run (not executed in this session); `app/`, `core/`, OpenAPI, frontend/iOS runtime (unchanged in diff — out of scope for PR0).

## Findings

Ordered by severity (highest first).

1. **severity:** `note`
   **role_agent:** `agent-coordinator`
   **category:** `governance`
   **file:** `docs/roadmap/BACKLOG_LEDGER.md`
   **line:** `~3302–3308`
   **evidence:** Ledger entry still states “🟡 In progress — draft PR #1548” while branch carries completed-looking artifacts (`TIER4_PR1548_AGENT_PASS_RECORD`, `PR_1548_FIXED_MAPPING`).
   **suggested_fix:** On merge (or when PR leaves draft), update ledger checkbox/Status per [BACKLOG_LEDGER.md](https://github.com/Katsiarynakavaleuskaya/PulsePlate/blob/main/docs/roadmap/BACKLOG_LEDGER.md) policy (English-first, DoD).
   **gate_to_run:** Manual doc consistency + optional `pytest -q tests/guards/` if ledger format guarded.
   **disposition_candidate:** `DEFERRED` (post-merge ledger hygiene) or `NEEDS-HUMAN` (product owner closes item).

2. **severity:** `note`
   **role_agent:** `data-scientist-agent`
   **category:** `tests`
   **file:** `tests/test_skill_router.py`
   **line:** `872–882`
   **evidence:** Lexeme test uses goal string with “Tier 4”, “falsifiable”, “hypothesis” and `candidate_paths=["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"]` — proves keyword path to `creative_research` without `TIER4_*` file.
   **suggested_fix:** None required; optional future test could assert score margin vs `experiment` when eval keywords co-occur (packet maps eval work to `experiment`).
   **gate_to_run:** `pytest -q tests/test_skill_router.py -k tier4`
   **disposition_candidate:** `NOT-A-BUG`

3. **severity:** `note`
   **role_agent:** `security-auditor`
   **category:** `governance`
   **file:** N/A (command)
   **line:** N/A
   **evidence:** `python3 scripts/orchestration/check_preflight.py` emitted `WARNING: analyze mode without --path skips scoped AGENTS resolution` (exit still 0). Not introduced by PR diff; operator hygiene signal when using analyze mode.
   **suggested_fix:** When triaging orchestration tasks, pass `--path` to preflight analyze or use default mode per `RUNBOOK_AGENT.md`.
   **gate_to_run:** `python3 scripts/orchestration/check_preflight.py`
   **disposition_candidate:** `NOT-A-BUG`

4. **severity:** `note`
   **role_agent:** `qa-engineer-agent`
   **category:** `governance`
   **file:** `docs/review/PR_1548_FIXED_MAPPING.md`
   **line:** `51–57`
   **evidence:** Artifact lists `make verify` (PASS) among initial evidence — this PulsePlate PR Review run **did not** re-execute `make verify`.
   **suggested_fix:** Treat mapping lines as historical operator claims; re-run `make verify` before merge-ready statements per root `AGENTS.md`.
   **gate_to_run:** `make verify`
   **disposition_candidate:** `NEEDS-HUMAN` (merge gate), not a code defect.

**No `critical` or `major` findings** identified on changed surfaces: Tier 4 routing stays within existing `creative_research` / `experiment` labels; `_match_path_prefixes` correctly treats `docs/orchestration/TIER4_*.md` files (prefix without trailing slash); no new subprocess or auth paths in `skill_router.py` diff.

## Role review

- **agent-coordinator:** Packet, ledger anchor, `AGENTS.md` lane, and agent pass record align on “no eighth classifier,” phased execution, and mandatory post-open QA → bug-hunter; scope is docs + deterministic router cues only, consistent with PR0 success criteria.

- **architecture-specialist:** Single SoT string `TIER4_DOC_PREFIX` (`scripts/orchestration/skill_router.py:30`) avoids duplicate literals; `creative_research` rule adds orchestration domain weight + path prefix + keywords without splitting routing into a parallel taxonomy; design packet §8 linkage is minimal (two-line touch) — acceptable coupling.

- **security-auditor:** Changes are pattern/weight/path matching and markdown; `rg` for `subprocess`/`# nosec` on `skill_router.py` per pass record remains appropriate; no broad scraping or plugin execution added.

- **backend-engineer:** `skill_router.py` changes are declarative (constant, rule tuple extensions, `_match_path_prefixes` Tier 4 file-path exception). No API or runtime behavior changes.

- **qa-engineer-agent:** New tests `test_skill_router_tier4_packet_path_classifies_creative_research` and `test_skill_router_tier4_goal_lexemes_classify_creative_research` pin classifier and reasons; targeted pytest pass observed in this review (`pytest -q tests/test_skill_router.py -k "tier4 or Tier4"` exit 0).

- **bug-hunter:** Risk of misclassifying generic orchestration text is partially bounded by existing `test_task_classifier_keeps_generic_market_wellness_language_out_of_creative_research`; Tier 4 keywords could still interact with future rules — monitor classifier precedence/tie-break tests if new keywords land near `creative_research`.

- **data-scientist-agent (optional):** Tier 4 lexemes (“hypothesis”, “falsifiable”) intentionally steer toward `creative_research`; if future tasks mix heavy `experiment` vocabulary with Tier 4 org language, add a focused precedence test rather than widening keywords ad hoc.

## Gate plan

Exact commands (re-run after any fix):

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pytest -q tests/test_skill_router.py
pytest -q tests/test_skill_router.py -k "tier4 or Tier4"
make validate-min
```

Before merge (repo policy — not re-run in this review session):

```bash
pre-commit run --all-files
make verify
```

Optional bootstrap (ran clean this session):

```bash
python3 scripts/orchestration/task_bootstrap.py --goal "PR1548 Tier4 governance review" --task-class Orchestration --pr-phase pre_open
```

## Deferred / Follow-ups

- **Packet:** `docs/orchestration/TIER4_SCIENTIFIC_CREATIVE_CELL_PR0_PACKET_2026-04-27.md` § “Deferred / follow-ups” — Tier 4 PR1+ slices as separate backlog-backed PRs.
- **Ledger:** Close or update `docs/roadmap/BACKLOG_LEDGER.md` Tier 4 PR0 item after merge (see Finding 1).
- **External bots:** Any remaining GitHub review threads — disposition only via `docs/review/PR_1548_FIXED_MAPPING.md` + merge governance (not automated here).

## Decision log

**This review proves:** Local preflight and agent-consistency gates pass on the reviewed tree; `git diff origin/main...HEAD` scope is docs + `skill_router` + tests; Tier 4 routing logic and tests are internally consistent with `AGENT_SKILL_ROUTING_POLICY.md` §2a and the coordinator packet; targeted `pytest` for Tier 4 skill-router cases passes; `task_bootstrap.py` invocation completed exit 0 (JSON packet emitted).

**This review does not prove:** Full `make verify`, full pytest suite, CI green on GitHub, CodeRabbit/Sourcery/Cubic approval, or merge readiness — those require operator/CI execution and `check_merge_ready.py` per root `AGENTS.md`. Mapping artifact claims (e.g. `make verify` in `PR_1548_FIXED_MAPPING.md`) are not independently re-verified here.

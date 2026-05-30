# Premortem: Back /pulseplate-runner mvp-evidence with a durable sanitized ledger snapshot

## Frame

It is 6 months from now. The `/pulseplate-runner mvp-evidence` Slack command returned a snapshot that contained a raw `sessionId` value. A CI artifact tarball shipped the `artifacts/evidence/snapshots/` directory to a public analytics vendor. We are looking backward to understand why.

## Raw Failure Modes

### 1. Snapshot reader crashes before static fallback, breaking the Slack command
- **Story:** A fresh clone or CI runner had no `artifacts/evidence/snapshots/` directory. `render_mvp_evidence_summary()` attempted to read the latest snapshot, raised `FileNotFoundError` or `json.JSONDecodeError`, and the exception propagated out of the renderer. The Slack bridge returned a generic error instead of the static MVP evidence summary. Operators lost visibility and assumed the bridge was down.
- **Assumption:** The snapshot directory always exists and contains valid JSON.
- **Warning signs:** `render_mvp_evidence_summary()` has no try/except around filesystem I/O; tests only mock a happy path.
- **Containment:** Wrap snapshot reading in a bounded exception handler that always falls back to the static summary; log the failure class (not the path) for diagnostics.

### 2. Incomplete sanitization leaks sensitive frontend fields into the snapshot
- **Story:** A new frontend event payload included `analyticsDeviceId`, a field not present in `guidedPlanningObservabilitySensitiveFields`. The snapshot builder used the frontend denylist but not a general heuristic, so `analyticsDeviceId` was treated as safe and stored in `event_aggregates` keys. The leaked key was later correlated with user sessions.
- **Assumption:** The two existing denylists (`frontend/src/lib/mvpObservability.ts` and `core/evidence/events.py`) are jointly exhaustive.
- **Warning signs:** Snapshot tests only assert that known-bad fields are removed; no negative test for unknown fields.
- **Containment:** Fail closed on unrecognized payload keys (drop the event or raise), or maintain an explicit allowlist of safe keys. Do not rely solely on a denylist for cross-domain data.

### 3. `frozen` dataclass is not actually hashable due to a dict field
- **Story:** `MvpEvidenceSnapshot` was declared with `@dataclass(frozen=True)`, but `event_aggregates` was typed as `dict[str, int]`. Python's `frozen=True` does not make unhashable fields hashable, so `__hash__` was silently set to `None`. A downstream bridge helper tried to deduplicate snapshots in a `set()` and lost entries, causing duplicate snapshot writes and unbounded disk growth.
- **Assumption:** `frozen=True` implies hashable.
- **Warning signs:** No test calls `hash(snapshot)` or stores snapshots in a `set`/`dict` key.
- **Containment:** Use `tuple[tuple[str, int], ...]` or a custom frozen mapping type for `event_aggregates`; add a test that asserts `hash(snapshot)` succeeds and is deterministic.

### 4. `artifacts/evidence/snapshots/` is accidentally committed or included in Docker context
- **Story:** The directory was gitignored under a generic `artifacts/` rule, but a teammate added `artifacts/evidence/*.json` to a Docker `COPY` instruction for "debugging convenience." A snapshot containing route and auth-state buckets (while not PII alone) was shipped in a public image, violating the Evidence Graph Runtime rail-separation policy.
- **Assumption:** `artifacts/` is universally treated as local-only and never copied.
- **Warning signs:** Dockerfile gains new `COPY` lines without corresponding `.dockerignore` updates.
- **Containment:** Explicitly add `artifacts/evidence/` to `.gitignore` and `.dockerignore`; add a repo policy guard that fails if any `artifacts/evidence/` path appears in `git ls-files` or Docker context.

### 5. Snapshot lacks schema version, breaking backward compatibility
- **Story:** A follow-up PR added `latency_ms` to `MvpEvidenceSnapshot`. The bridge on an older branch could not read the new field and raised `TypeError` on deserialization. The Slack command failed on half the operator workstations.
- **Assumption:** All consumers update atomously with producers.
- **Warning signs:** Dataclass deserialization uses `**json.load(...)` without a schema version check.
- **Containment:** Include a `snapshot_schema_version: str` field (e.g., `"v1"`) and fail closed on unknown versions.

### 6. `artifact_refs` field stores absolute or forbidden paths
- **Story:** The snapshot builder included an absolute path like `/Users/dev/.ssh/config` in `artifact_refs` because a downstream helper passed `__file__` without normalization. The snapshot was stored and later referenced in a Slack message, leaking local filesystem structure.
- **Assumption:** Callers always pass repo-relative, safe paths.
- **Warning signs:** `artifact_refs` accepts `tuple[str, ...]` without validation.
- **Containment:** Reuse `validate_source_artifact` from `core/evidence/events.py` (or equivalent logic) to reject absolute paths, traversal, and forbidden roots (`artifacts/agent_runs/`, `.venv/`, etc.).

### 7. Snapshot storage path lacks symlink/traversal guards
- **Story:** An attacker with local repo access symlinked `artifacts/evidence/snapshots/` to `/etc`. The bridge wrote a snapshot outside the repo, and a cleanup script later deleted an unintended file.
- **Assumption:** The storage path is safe because it is under the repo root.
- **Warning signs:** No `_reject_symlinked_output_components` equivalent for the snapshot directory.
- **Containment:** Apply the same symlink-rejection and path-traversal guards used for `artifacts/orchestration/experiments/slack_socket_bridge/`.

## Synthesis

### Summary

Add a durable, frozen, hash-safe `MvpEvidenceSnapshot` dataclass in `core/evidence/mvp_snapshot.py` that stores aggregate-only event counts, route/auth-state enum buckets, coverage flags, and validated artifact refs. Sanitize all inputs using a fail-closed union of the frontend and backend denylists. Store append-only JSON lines under `artifacts/evidence/snapshots/` (gitignored). Update the Slack bridge `render_mvp_evidence_summary()` to read the latest snapshot with graceful fallback to the existing static summary. No backend analytics, no DB, no network calls.

### Most likely failure

**Failure mode #1:** `render_mvp_evidence_summary()` crashes on a missing or corrupt snapshot directory before reaching the static fallback. The Slack `mvp-evidence` command becomes a hard error in CI and fresh clones, breaking operator visibility. The existing bridge tests are strong for static rendering but the new filesystem-dependent path is narrow and easy to regress.

### Most dangerous failure

**Failure mode #2:** Incomplete sanitization allows a sensitive field to leak into the snapshot. The snapshot lives in `artifacts/evidence/snapshots/` — while gitignored, it is a local file that can be tarballed, copied into Docker images, or accidentally committed. Because the Evidence Graph Runtime invariant demands strict rail separation, any leak of user-health or session identifiers from the frontend observability stream into a control-plane artifact is a policy violation with potential compliance implications.

### Hidden assumption

The plan assumes that "aggregate-only" (counts and enums) is a self-enforcing property. It is not. Once the snapshot infrastructure exists, the path of least resistance for a future developer who needs "just one more signal" is to add a raw payload field to `event_aggregates`. There is no runtime or type-level guard preventing raw payloads from being stored. The snapshot's `frozen` and `hash-safe` design is a good signal, but without an explicit schema allowlist or a redaction gate that audits every key, the aggregate-only constraint is a convention, not an invariant.

### Revised plan

1. **Dataclass design:** Use `@dataclass(frozen=True)` with only hashable field types. Represent `event_aggregates` as `tuple[tuple[str, int], ...]` (not `dict`). Add `snapshot_schema_version: str = "v1"` for forward compatibility. Add a test that proves `hash(snapshot)` succeeds and is deterministic.
2. **Sanitization:** Build a unified denylist from `guidedPlanningObservabilitySensitiveFields` (camelCase) and `_FORBIDDEN_METADATA_KEY_FRAGMENTS` (snake_case), normalized to lowercase. Fail closed: if an event payload key is not in an explicit allowlist of safe aggregate keys (`surface`, `componentId`, `routePath`, `optionId`, `tierLabel`, `authState`), drop the event or raise. Do not rely on a denylist alone.
3. **Artifact ref validation:** Reuse `validate_source_artifact` logic from `core/evidence/events.py` for every string in `artifact_refs`. Reject absolute paths, traversal, forbidden roots, and paths outside the repo.
4. **Storage guards:** Apply `_reject_symlinked_output_components` equivalent to `artifacts/evidence/snapshots/` before any write. Reject symlinks in the path ancestry.
5. **Bridge renderer:** Wrap snapshot file reading in a bounded `try/except` (catch `OSError`, `json.JSONDecodeError`, `ValueError`). On any failure, emit a `SlackSafeMessage` with `status_line="snapshot_unavailable"` and fall back to the static summary. Never expose the exception message or filesystem path in the Slack payload.
6. **Git / Docker ignore:** Add `artifacts/evidence/` explicitly to `.gitignore` and `.dockerignore`. Add a repo policy guard (or extend an existing one) that fails if `artifacts/evidence/` paths appear in `git ls-files`.
7. **Tests:** Add `tests/test_mvp_evidence_snapshot.py` covering: hashability, schema version mismatch, sanitization of every denied field, artifact ref validation, and symlink guard. Update `tests/test_experiment_slack_socket_bridge.py` to prove static fallback works when the snapshot dir is missing and when JSON is corrupted.

### Pre-merge checklist

- [ ] `MvpEvidenceSnapshot` is frozen and hashable (test calls `hash()` and asserts deterministic result).
- [ ] Sanitization fails closed on unknown keys, not just denied keys (test with a never-before-seen key).
- [ ] `render_mvp_evidence_summary()` never raises on missing/empty/corrupt snapshot dir (static fallback proven in test).
- [ ] Snapshot storage path rejects symlinks and traversal (equivalent guards to bridge audit dir).
- [ ] `artifacts/evidence/` is explicitly listed in `.gitignore` and `.dockerignore`.
- [ ] `artifact_refs` validation rejects absolute paths, traversal, and forbidden roots.
- [ ] No raw event payloads or unlisted metadata keys are stored in the snapshot (only counts, enums, and safe flags).
- [ ] Snapshot schema version field is present and tested for unknown-version rejection.

### Decision

`proceed with changes` — the plan is directionally correct and scoped well, but it must implement the revised plan items above before opening the PR. Without them, the snapshot risks becoming an unguarded local file that violates Evidence Graph Runtime rail separation and breaks operator visibility in CI.

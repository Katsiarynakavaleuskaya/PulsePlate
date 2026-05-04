# PR #1663 Premortem Risk Review

<!-- markdownlint-disable MD013 -->

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1663
Mode: `pr-premortem`
Frame: It is 6 months from now. This PR merged, but OpenCode still reports fewer skills than expected.

## Failure Modes

### 1. Wrong install target not documented clearly enough

**Story:** User installs to `~/.agents/skills/` (official) but OpenCode reads from `~/.config/opencode/skills/` (user-global). Verifier reports all green on official target, but OpenCode session still sees only 2 skills.

**Underlying assumption:** OpenCode's scanner path is `~/.agents/skills/` or `.agents/skills/` (repo-local).

**Early warning signs:** User reports "verifier says all installed, but OpenCode shows only 2 skills."

**Containment:** Runbook documents all known scanner paths including `~/.config/opencode/skills/`. User can re-run verifier with `--dest ~/.config/opencode/skills/`.

### 2. Stale host install not cleaned before fresh install

**Story:** User re-runs installer but old stale copies conflict. Installer exits with "destination already exists as a different symlink."

**Underlying assumption:** Users will read the `--unlink` documentation before re-installing.

**Early warning signs:** Installer error messages in user reports.

**Containment:** Runbook includes explicit "clean stale install" step before reinstall.

### 3. Role/protocol vs skill confusion persists

**Story:** User names `pulseplate-ci-guard-hygiene` in a task prompt expecting it to be loaded. OpenCode reports "skill not found" or silently ignores it.

**Underlying assumption:** Users understand that not all names in task prompts are loadable skills.

**Early warning signs:** Repeated confusion in task prompts.

**Containment:** Runbook includes explicit table distinguishing roles, skills, and prompt protocols.

### 4. Symlink scanner limitations

**Story:** A tool follows symlinks differently or doesn't follow them at all. Skills appear as broken or missing.

**Underlying assumption:** All skill-aware tools follow symlinks correctly.

**Early warning signs:** Tool-specific "skill not found" errors despite correct symlinks.

**Containment:** Installer supports `--copy` mode as a fallback. Documented in existing CODEX_SKILLS.md.

### 5. Tests pass but real scanner behavior differs

**Story:** Verifier tests use `tmp_path` isolation. All pass. But real OpenCode/Codex scanner has undocumented path resolution logic that differs.

**Underlying assumption:** Scanner reads the directory we think it reads.

**Early warning signs:** Tests green, but real tool still shows wrong count.

**Containment:** Documented as known limitation in runbook. Verifier proves repo-to-destination alignment, not scanner behavior.

## Synthesis

**Most likely failure:** Target mismatch (user installs to wrong path for their tool).

**Most dangerous failure:** Tests pass but scanner behavior differs (false confidence).

**Hidden assumption:** We know which directories OpenCode reads, but vendor docs may change.

**Revised plan:** None needed — runbook already documents all known paths and limitations.

## Decision

`proceed` — plan is sound. All identified risks are mitigated through documentation and fallback mechanisms.

## Pre-merge Checklist

- [x] Verifier is read-only (no mutation)
- [x] All known scanner paths documented
- [x] Roles vs skills vs protocols table included
- [x] Restart requirement documented
- [x] Stale install cleanup documented
- [x] Tests cover pass/fail/json/compat/custom/read-only scenarios
- [x] No runtime or provider changes

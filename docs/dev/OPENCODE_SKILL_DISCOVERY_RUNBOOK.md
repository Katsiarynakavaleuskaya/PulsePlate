# OpenCode Skill Discovery Runbook

<!-- markdownlint-disable MD013 -->

## Purpose

Explains why OpenCode, Codex CLI, or other skill-aware agents may report fewer
loaded skills than the repo source of truth contains, and provides a
deterministic diagnosis and remediation flow.

## Repo truth

| Layer | Path | Role |
|-------|------|------|
| Canonical source | `tools/codex_skills/` | Only repo SoT for PulsePlate skills |
| Repo mirror | `.agents/skills/` | Passive discovery mirror (managed links/copies to source) |
| Install contract | `docs/dev/CODEX_SKILLS.md` | Canonical install/discovery documentation |
| Installer | `scripts/install_codex_skills.sh` | Operator-invoked installer |
| Verifier | `scripts/verify_codex_skills_install.py` | Read-only install completeness check |

## Expected PulsePlate skill count

Dynamic command (run from repo root):

```bash
find tools/codex_skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l
```

The expected count must match `tests/test_install_codex_skills.py`
(`test_repo_agents_skills_mirror_points_to_codex_skill_sources`).

## Known scanner paths

Different tools read skills from different directories:

| Tool | Scanner path | Notes |
|------|-------------|-------|
| OpenCode (repo session) | `.agents/skills/` (working directory) | Auto-discovered; all 17 PulsePlate + 3 Vercel skills |
| OpenCode (user global) | `~/.config/opencode/skills/` | User-installed skills only |
| Codex CLI | `$CODEX_HOME/skills` or `~/.codex/skills` | Compat target; requires explicit install |
| Official install | `$AGENTS_HOME/skills` or `~/.agents/skills` | Default installer target |

## Diagnosis flow

1. **List repo source skills:**

   ```bash
   scripts/install_codex_skills.sh --list --no-cybersec
   ```

2. **Check official install target:**

   ```bash
   python3 scripts/verify_codex_skills_install.py --target official
   ```

3. **Check compat install target:**

   ```bash
   python3 scripts/verify_codex_skills_install.py --target compat
   ```

4. **Check custom destination (if applicable):**

   ```bash
   python3 scripts/verify_codex_skills_install.py --dest /path/to/skills
   ```

5. **Identify which target your tool reads** (see Known scanner paths above).

6. **Clean stale install if needed:**

   ```bash
   scripts/install_codex_skills.sh --unlink --no-cybersec
   # or for compat target:
   scripts/install_codex_skills.sh --unlink --target compat --no-cybersec
   ```

7. **Reinstall:**

   ```bash
   scripts/install_codex_skills.sh --no-cybersec
   # or for compat target:
   scripts/install_codex_skills.sh --target compat --no-cybersec
   ```

8. **Restart the tool** (OpenCode, Codex CLI, etc.) so newly installed skills
   are loaded.

9. **Verify after install** (use the same `--target` or `--dest` as the install):

   ```bash
   # official target (default):
   python3 scripts/verify_codex_skills_install.py --strict
   # compat target:
   python3 scripts/verify_codex_skills_install.py --target compat --strict
   # custom destination:
   python3 scripts/verify_codex_skills_install.py --dest /path/to/skills --strict
   ```

## Roles vs skills vs prompt protocols

Not every name that appears in a task prompt is a loadable skill:

| Name | Type | Has SKILL.md? | Loadable? |
|------|------|---------------|-----------|
| `agent-coordinator` | Agent role | No | No (role, not skill) |
| `bug-hunter` | Agent role | No | No (role, not skill) |
| `pulseplate-workflow` | PulsePlate skill | Yes | Yes |
| `pulseplate-gates` | PulsePlate skill | Yes | Yes |
| `pulseplate-premortem-risk-review` | PulsePlate skill | Yes | Yes |
| `code-review-expert` | User-installed skill | Yes | Yes (from `~/.config/opencode/skills/`) |
| `find-skills` | User-installed skill | Yes | Yes (from `~/.config/opencode/skills/`) |
| `bug-triage` | External/plugin skill | Varies | Depends on host install |
| `docs-sync` | External/plugin skill | Varies | Depends on host install |
| `pulseplate-ci-guard-hygiene` | Prompt protocol name | No | No (not materialized as SKILL.md) |
| `pulseplate-pr-governance` | Prompt protocol name | No | No (not materialized as SKILL.md) |
| `pulseplate-cursor-workflow` | Prompt protocol name | No | No (not materialized as SKILL.md) |

**Rule:** If a name does not have a `SKILL.md` in `tools/codex_skills/` or a
host install directory, it cannot be loaded by OpenCode or Codex CLI. Prompt
protocol names represent conceptual workflow steps, not loadable skill packages.

## Common root causes for fewer loaded skills

1. **Target mismatch:** OpenCode reads `~/.config/opencode/skills/` or
   `.agents/skills/` (repo-local), but installer wrote to `~/.agents/skills/`
   or `~/.codex/skills/`.
2. **Stale install:** New skills were added to the repo after the last
   `install_codex_skills.sh` run.
3. **No restart:** Tool was not restarted after install/update.
4. **Wrong filter:** User ran with `--only-cybersec` or a custom destination.
5. **Symlink scanner limitations:** Some tools may not follow symlinks; use
   `--copy` if needed.
6. **Confusing roles/protocols with skills:** Names like `agent-coordinator` or
   `pulseplate-ci-guard-hygiene` are not loadable skill packages.
7. **Repo-local vs host install:** OpenCode in a repo session reads
   `.agents/skills/` from the working directory (all skills present), but a
   standalone session reads only from user-global or host paths.

## Non-goals

- This runbook does not change product runtime behavior.
- This runbook does not create a second source of truth for skills.
- This runbook does not automate install at shell/session start.
- Materializing prompt protocol names as SKILL.md packages is deferred until
  there is a concrete loader need.

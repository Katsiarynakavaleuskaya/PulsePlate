# PulsePlate Skills

<!-- markdownlint-disable MD013 -->

Repo-tracked source for project-specific skills and cybersecurity skills.
**Runtime-agnostic:** used by Codex, Kimi Code CLI, Qoder, and other agentskills.io-compatible runtimes.

- Source of truth: `tools/codex_skills/*`, `tools/cybersecurity_skills/skills/*`
- Repo discovery mirror: `.agents/skills/*` (Kimi, Codex, Qoder all resolve this as Project scope)
- Primary user install target: `$HOME/.agents/skills/*`
- Kimi CLI user target: `$HOME/.kimi/skills/*` (when using `--skills-dir` or `extra_skill_dirs`)
- Compatibility legacy target: `$CODEX_HOME/skills/*` (typically `~/.codex/skills/*`)
- Installer: `scripts/install_codex_skills.sh`

Default install mode uses symlinks so updates in this repo immediately apply to installed skills.
Skills remain passive/discovery-only helpers and do not replace coordinator bootstrap.

> **Kimi CLI note:** Kimi discovers project skills from `.agents/skills/` natively as Project scope.
> No separate `.kimi/skills/` copy is required. User-level skills can also be read from
> `~/.codex/skills/` when `merge_all_available_skills = true` (default).

## PulsePlate skills

- `pulseplate-ai-reports`
- `pulseplate-agent-learning-loop`
- `pulseplate-agent-product`
- `pulseplate-app-store-release`
- `pulseplate-backend-endpoints`
- `pulseplate-design-launch-system`
- `pulseplate-frontend-ui`
- `pulseplate-gates`
- `pulseplate-graphmap`
- `pulseplate-guards`
- `pulseplate-ledger`
- `pulseplate-monetization-gtm`
- `pulseplate-openapi-sync`
- `pulseplate-playwright-e2e`
- `pulseplate-pr-closeout`
- `pulseplate-pr-review`
- `pulseplate-premortem-risk-review`
- `pulseplate-review-pattern-oracles`
- `pulseplate-web-launch-site`
- `pulseplate-workflow`

## Cybersecurity skills (submodule)

734+ skills (approximate; see `tools/cybersecurity_skills/index.json`) from [anthropic-cybersecurity-skills](https://github.com/Katsiarynakavaleuskaya/anthropic-cybersecurity-skills) (agentskills.io format). Keep this bundle opt-in for day-to-day Codex CLI use: broad symlink installs can surface long repo-target skill paths in Codex discovery warnings even when the underlying skill slug is valid.

**First-time setup:**

```bash
git submodule update --init --recursive
scripts/install_codex_skills.sh --no-cybersec
```

If you need the cybersecurity bundle inside Codex CLI, prefer copied installs:

```bash
scripts/install_codex_skills.sh --only-cybersec --copy-cybersec
```

**Update to latest:**

```bash
git submodule update --remote tools/cybersecurity_skills
scripts/install_codex_skills.sh --only-cybersec --copy-cybersec
```

See `docs/dev/CYBERSECURITY_SKILLS.md` for details.

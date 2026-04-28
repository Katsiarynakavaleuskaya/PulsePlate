# PulsePlate Codex Skills

<!-- markdownlint-disable MD013 -->

Repo-tracked source for project-specific Codex skills and cybersecurity skills.

- Source of truth: `tools/codex_skills/*`, `tools/cybersecurity_skills/skills/*`
- Repo discovery mirror: `.agents/skills/*`
- Primary user install target: `$HOME/.agents/skills/*`
- Compatibility-only legacy target: `$CODEX_HOME/skills/*` (typically `~/.codex/skills/*`)
- Installer: `scripts/install_codex_skills.sh`

Default install mode uses symlinks so updates in this repo immediately apply to installed skills.
Skills remain passive/discovery-only helpers and do not replace coordinator bootstrap.

## PulsePlate skills

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-openapi-sync`
- `pulseplate-frontend-ui`
- `pulseplate-ledger`
- `pulseplate-guards`
- `pulseplate-backend-endpoints`
- `pulseplate-ai-reports`
- `pulseplate-app-store-release`
- `pulseplate-graphmap`
- `pulseplate-playwright-e2e`
- `pulseplate-monetization-gtm`
- `pulseplate-design-launch-system`
- `pulseplate-web-launch-site`
- `pulseplate-agent-product`
- `pulseplate-pr-review`

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

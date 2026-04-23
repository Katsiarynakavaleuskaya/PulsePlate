# Cybersecurity Skills for PulsePlate

<!-- markdownlint-disable MD013 -->

734+ cybersecurity skills (approximate; see `tools/cybersecurity_skills/index.json`) from [anthropic-cybersecurity-skills](https://github.com/Katsiarynakavaleuskaya/anthropic-cybersecurity-skills) (agentskills.io format). Keep this bundle explicit for Codex CLI: it is valid by skill slug, but wide symlink installs can produce long repo-target discovery warnings.

## Install

First-time setup (after clone):

```bash
git submodule update --init --recursive
scripts/install_codex_skills.sh --only-cybersec --copy-cybersec
```

Skills are symlinked to the primary user install target `$AGENTS_HOME/skills/`
with `$HOME/.agents/skills/` as the fallback.
Use `scripts/install_codex_skills.sh --target compat` only when a legacy local Codex setup still expects `$CODEX_HOME/skills/`
with `~/.codex/skills/` as the fallback.

For routine PulsePlate work, skip this bundle entirely unless the task actually
needs a cybersecurity playbook:

```bash
scripts/install_codex_skills.sh --no-cybersec
```

For Codex CLI, prefer `--copy-cybersec` so discovery uses short local skill
folder names instead of long repo-target symlink paths.

## Update

To pull latest cybersecurity skills:

```bash
git submodule update --remote tools/cybersecurity_skills
scripts/install_codex_skills.sh --only-cybersec --copy-cybersec
```

## PulsePlate-relevant subdomains

| Subdomain | Skills | Use case |
|-----------|--------|----------|
| api-security | 28 | API auth, BOLA, OWASP, JWT |
| web-application-security | 42 | XSS, XXE, injection, OWASP |
| devsecops | 17 | semgrep, gitleaks, CI pipeline |
| container-security | 30 | Trivy, Falco, Kubernetes |
| vulnerability-management | 25 | CVSS, patch workflow |

## Routing

- **security-auditor** gets access to all ~734 skills (approximate; see index.json) when routed (see `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`)
- **Cursor:** `.cursor/rules/cybersecurity-skills-index.md` provides index and triggers
- **Codex:** Use the canonical path contract from [`docs/dev/CODEX_SKILLS.md`](./CODEX_SKILLS.md); `compat` remains compatibility-only

## Index

Full skill list: `tools/cybersecurity_skills/index.json`

Skill structure: `tools/cybersecurity_skills/skills/{skill-name}/SKILL.md`

## References

- [tools/codex_skills/README.md](../../tools/codex_skills/README.md) — install overview
- [AGENT_SKILL_ROUTING_POLICY.md](../orchestration/AGENT_SKILL_ROUTING_POLICY.md) — skill routing
- [agentskills.io](https://agentskills.io) — skill format standard

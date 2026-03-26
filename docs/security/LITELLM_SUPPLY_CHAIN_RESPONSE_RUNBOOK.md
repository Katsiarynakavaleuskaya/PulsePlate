# LiteLLM Supply-Chain Response Runbook

## Purpose

This runbook captures the repo-local response flow for malicious PyPI release scenarios that abuse Python startup hooks via executable `.pth` files.

Repo evidence anchors:

- `.github/actions/python-setup/action.yml:45`
- `Makefile:73`
- `scripts/ci/check_python_startup_hooks.py:14`
- `scripts/ci/install_locked_python_requirements.py:17`

## Current repo stance

As of **26 March 2026**:

- tracked repo manifests do not reference `litellm`
- local repo `.venv` may still contain historical tooling drift and must be audited separately from the repo lockfiles
- executable `.pth` files are now guarded by `scripts/ci/check_python_startup_hooks.py`
- local bootstrap and CI install surfaces use `scripts/ci/install_locked_python_requirements.py`

## Read-only triage steps

1. Check local versions and site-packages:

```bash
.venv/bin/python -m pip show litellm || true
python3 -m pip show litellm || true
python3 scripts/ci/check_python_startup_hooks.py --python-executable .venv/bin/python
```

1. Search obvious IoCs:

```bash
find "$HOME/.cache/pip" "$HOME/.cache/uv" "$HOME/.config" /tmp \
  \( -name 'litellm_init.pth' -o -name 'sysmon.py' -o -name 'sysmon.service' -o -name 'pglog' \) \
  2>/dev/null
```

1. Review shell/package history for the suspected window:

```bash
rg -n "litellm|pip install|uv pip|python -m pip" ~/.zsh_history ~/.bash_history 2>/dev/null
ls -lt ~/.cache/pip ~/.cache/uv 2>/dev/null
```

1. Review repo install surfaces:

```bash
rg -n "install_locked_python_requirements.py|check_python_startup_hooks.py|python -m pip install" \
  Makefile Dockerfile .github/workflows .github/actions scripts
```

## Escalation criteria

Escalate to incident mode immediately if **any** of the following is true:

- `litellm==1.82.7` or `litellm==1.82.8` appears in any local env or cache
- `litellm_init.pth` or another unexpected executable `.pth` is found
- `~/.config/sysmon/sysmon.py` or `~/.config/systemd/user/sysmon.service` exists
- suspicious outbound traffic to reported attacker infrastructure is confirmed

## Incident-mode actions

1. Rotate all credentials that may have been present on the host:
- SSH keys
- cloud credentials
- database credentials
- API keys
- signing tokens

1. Rebuild local Python environments from scratch:

```bash
rm -rf .venv .venv-ci
make venv
```

1. Review container and Kubernetes access:
- local kubeconfig contexts
- service-account tokens
- mounted secrets in developer clusters

1. Preserve evidence before destructive cleanup:
- shell history
- pip/uv cache timestamps
- workflow run IDs
- Docker build logs

## Prevention controls in this repo

- `scripts/ci/check_python_startup_hooks.py`
- `scripts/ci/install_locked_python_requirements.py`
- `make venv` and `make venv-sync` with `PIP_REQUIRE_VIRTUALENV=1`
- CI composite action and canonical CI lanes using the locked installer

## Deferred control outside repo scope

The repo still needs an **internal mirror / artifact quarantine** path for full supply-chain isolation. That infra dependency is tracked in `docs/roadmap/BACKLOG_LEDGER.md`.

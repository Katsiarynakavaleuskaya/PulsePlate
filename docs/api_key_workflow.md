# API Key Workflow Automation

This guide explains how to exercise the secure configuration helpers end-to-end
using the `scripts/api_key_workflow.py` harness. It automates the sequence of
steps we previously ran manually:

1. ensure encryption support is available;
2. populate the premium/free profiles with encrypted values;
3. write audit metadata and harden file permissions; and
4. run `update_api_key.py verify` to confirm the installation.

The script can run in a throwaway sandbox (default) or against a specific HOME
folder.

## Prerequisites

```bash
python -m pip install --user cryptography
```

(If you plan to experiment with keychain storage, also install
`python -m pip install --user keyring`.)

## Quick smoke test (sandboxed)

```bash
python scripts/api_key_workflow.py
```

What it does:

- Creates a temporary HOME directory.
- Writes demo keys that satisfy validation for both premium & free profiles.
- Runs diagnostics with a 30-day freshness threshold.
- Prints the sandbox path before cleaning it up.

Use `--keep-sandbox` if you want to inspect the generated files afterwards.

## Using real keys

Provide a target directory and pass your actual key material. The script will
refuse to use the built-in demo values when operating on non-temporary homes.

```bash
python scripts/api_key_workflow.py \
  --home "$HOME" \
  --premium "sk-your-premium-key" \
  --free "sk-your-free-key" \
  --source "cli-bootstrap"
```

The command writes encrypted values into `$HOME/.cursor/.env`, updates
`key.meta.json`, and then runs the diagnostics checks. Permission warnings are
addressed automatically (the script issues `chmod 600` on the touched files when
possible).

## Diagnostics-only mode

To run just the verification phase against an existing installation:

```bash
python scripts/api_key_workflow.py --home "$HOME" --verify-only
```

Use `--stale-days 7` (or any integer) to tune the age threshold used for stale
key warnings.

## Advanced flags

- `--skip-premium` / `--skip-free`: omit one of the profiles when writing keys.
- `--premium` / `--free`: explicit key values. When omitted in sandbox mode,
  deterministic demo keys are used.
- `--source`: label stored in the audit log and metadata (defaults to
  `automation-script`).

Refer to `python scripts/api_key_workflow.py --help` for the complete list.

# Tokens Source Of Truth

This document defines the canonical rule for PulsePlate design tokens.

Policy location: `docs/sora/SORA_STYLE_QA_CHECKLIST.md` (section `Web Token Governance`).

### Canonical decision

- `TOKEN_SOT`: `frontend/src/styles/tokens.css`
- `GOLD`: approved as premium/accent semantic token

### Migration policy

- PR-1 (bridge): introduce canonical `--pp-*` brand tokens and keep legacy aliases.
- PR-2 (palette switch): update canonical token values to Guidelines palette.
- PR-3 (guard): ban raw hex in frontend runtime paths with explicit allowlist.

### Canonical brand tokens

- `--pp-navy`
- `--pp-blue`
- `--pp-green`
- `--pp-red`
- `--pp-gold`

### Legacy aliases (temporary)

- `--pp-primary` -> `--pp-blue`
- `--pp-accent` -> `--pp-green`

Legacy aliases are kept only for soft migration and should not be used in new code.

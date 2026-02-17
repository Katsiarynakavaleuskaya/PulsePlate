# Skill Spec: PulsePlate Sora Prompt Engineering

This tracked spec mirrors the local runtime skill content used for Sora prompt
engineering in PulsePlate.

## Trigger Conditions

Use this skill when requests involve:

- Sora prompt creation/refinement for PulsePlate visuals
- Prompt packs for onboarding/paywall/home-card assets
- Anti-drift controls for mascot/icon/background consistency

## Required Outputs

1. Master prompt template (full style lock)
2. Nano prompt template (fast iteration mode)
3. Screen/asset prompt pack with variations
4. Negative prompt blocks
5. QA rubric with pass/fail checks

## Canonical Brand Lock

- Mood: minimalism + cozy + intelligent + luxury-clean
- Palette:
  - Navy `#0F172A`
  - Blue `#339FFF`
  - Accent Green `#20C997`
  - Heart Red `#FF5D5D` (accent only)
- Visual style: flat + soft shadows + subtle gradients
- Mascot policy: FitChef is lifestyle-friendly, never clinical

## Workflow

### Step 1 - Planning

- Lock non-negotiable style invariants
- Define output targets (iOS/Web/Social + ratios)
- Define required variant count

### Step 2 - Audit and Brainstorm

- Build risk table (brand drift, accessibility, policy risk)
- Add negative constraints per prompt family
- Validate external constraints when needed

### Step 3 - Prompt Package

- Master prompt + negative prompt
- 3 controlled variations per asset family
- QA checks and release recommendation

## Anti-Drift Guardrails

- No out-of-palette generation
- No generic AI slop aesthetics
- No diagnosis/cure or medical implication
- No unreadable micro-detail for small-size assets
- Maintain mascot continuity across variants

## References

- Playbook: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- Agent owner: `.cursor/agents/sora-prompt-engineer.md`

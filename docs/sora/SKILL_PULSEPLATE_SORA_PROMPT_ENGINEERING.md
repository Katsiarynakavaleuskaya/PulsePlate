# Skill Spec: PulsePlate Sora Prompt Engineering

This tracked spec mirrors the local runtime skill content used for Sora prompt
engineering in PulsePlate.

## Trigger Conditions

Use this skill when requests involve:

- Sora prompt creation/refinement for PulsePlate visuals
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:49`)
- Prompt packs for onboarding/paywall/home-card assets
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:181`)
- Anti-drift controls for mascot/icon/background consistency
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:275`)

## Required Outputs

1. Master prompt template (full style lock)
   (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:140`)
2. Nano prompt template (fast iteration mode)
   (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:171`)
3. Screen/asset prompt pack with variations
   (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:181`)
4. Negative prompt blocks
   (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:308`)
5. QA rubric with pass/fail checks
   (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:299`)

## Canonical Brand Lock

- Mood: minimalism + cozy + intelligent + luxury-clean
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:23`)
- Palette:
  - Navy `#0F172A`
  - Blue `#339FFF`
  - Accent Green `#20C997`
  - Heart Red `#FF5D5D` (accent only)
- Visual style: flat + soft shadows + subtle gradients
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:29`)
- Mascot policy: FitChef is lifestyle-friendly, never clinical
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:30`)

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
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:277`)
- No generic AI slop aesthetics
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:298`)
- No diagnosis/cure or medical implication
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:262`)
- No unreadable micro-detail for small-size assets
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:116`)
- Maintain mascot continuity across variants
  (`docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:109`)

## References

- Playbook: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- Agent owner: `.cursor/agents/sora-prompt-engineer.md`

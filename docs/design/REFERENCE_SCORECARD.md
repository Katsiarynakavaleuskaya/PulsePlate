<!-- markdownlint-disable MD013 -->
# Reference Scorecard

**Status:** PR-0 design intelligence contract
**Purpose:** Define how PulsePlate evaluates external UI/UX references before any future design brief can use them.

## Summary

This scorecard prevents subjective LLM taste from becoming design authority. It converts reference review into explicit, reviewable axes tied to PulsePlate business value, wellness safety, accessibility, legal safety, implementation cost, token impact, and platform parity.

The scorecard never approves copying. It only approves normalized design direction.

## Required Decisions

Every scored reference must end with one of:

- `adopt`: the abstract pattern already fits PulsePlate vocabulary, tokens, safety, and implementation constraints.
- `adapt`: useful direction, but must be transformed into PulsePlate-specific vocabulary, tokens, copy, and layout.
- `reject`: blocked by brand fit, legal risk, accessibility risk, wellness risk, implementation cost, or copy risk.

Default decision is `adapt` unless a reference is clearly safe and already maps to existing PulsePlate contracts.

## Scoring Scale

Use integers `0` through `3`.

| Score | Meaning |
| --- | --- |
| `0` | Fails or creates material risk |
| `1` | Weak fit; use only as negative example or deferred research |
| `2` | Useful with adaptation and explicit controls |
| `3` | Strong fit as a normalized pattern, still not a copy source |

## Required Scoring Axes

| Axis | Question | Higher score means |
| --- | --- | --- |
| Brand fit | Does the pattern fit PulsePlate's calm premium wellness identity? | It reinforces trust, clarity, and restrained premium perception |
| Trust / wellness-safe tone | Does the reference avoid clinical, diagnostic, treatment, crisis, or pseudoscience claims? | It stays wellness-only and evidence-careful |
| Premium-clean perception | Does it feel polished without decorative excess or fake luxury? | It improves perceived product quality |
| Accessibility risk | Does it preserve contrast, focus, keyboard, motion comfort, touch targets, and readable hierarchy? | Lower a11y risk and clearer remediation path |
| Layout clarity | Is the information hierarchy easy to scan and repeat? | Clear task flow and low cognitive overhead |
| Component reuse potential | Can it map to existing PulsePlate components or vocabulary? | High reuse, low primitive churn |
| Implementation cost | Can it be implemented without broad refactor or runtime logic changes? | Small, bounded frontend/iOS work |
| Token delta size | Does it avoid large token changes? | Existing tokens can carry the direction |
| Business value for conversion / activation | Does it plausibly improve signup, onboarding, activation, premium, or trust? | Clear business reason |
| App Store / legal risk | Does it avoid release, privacy, HealthKit, AI-disclosure, and claim-safety risk? | Low reviewer/legal risk |
| Copy risk | Does it avoid direct copy, unsupported claims, testimonials, rankings, or brand-specific language? | Low copy/legal risk |
| Platform parity potential | Can web and iOS express it without violating platform conventions? | Strong cross-platform translation |

## Decision Thresholds

- `reject` if any of these axes score `0`: trust / wellness-safe tone, accessibility risk, App Store / legal risk, copy risk.
- `reject` if `forbidden_copy_elements` cannot be separated from the useful pattern.
- `adapt` if total score is `18` through `29` and no hard reject axis is `0`.
- `adopt` if total score is `30` or higher, all hard-risk axes are at least `2`, and the pattern maps to existing PulsePlate components/tokens.
- `read_only` remains the status when evidence is incomplete.

## Scorecard Record

```markdown
| Field | Value |
| --- | --- |
| Reference id |  |
| Manifest status | read_only / normalized / rejected / candidate_for_brief |
| Decision | adopt / adapt / reject |
| Total score |  |
| Hard reject axes |  |
| PulsePlate component mapping |  |
| Token delta expectation | none / small / medium / large |
| Required evidence before brief |  |
| Reviewer notes |  |
```

## Deterministic Controls

- Scores require short evidence notes, not only numbers.
- Any `adopt` decision must cite existing PulsePlate component and token mappings.
- Any future LLM-assisted scoring must output this schema and be checked by deterministic validation before use.
- GEPA or similar prompt/rubric evolution may optimize only the scoring rubric over curated fixtures; it must not mutate production UI, tokens, Figma, or runtime code.

## Future Check Plan

PR-4 of this wave should add a deterministic checker that validates:

- required axes are present,
- decision thresholds are followed,
- hard reject axes cannot be bypassed,
- component mappings use PulsePlate vocabulary,
- copy/license risk fields are present before `candidate_for_brief`.

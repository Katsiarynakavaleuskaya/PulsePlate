# CV Photo -> Food Eval Contract

<!-- markdownlint-disable MD013 -->

**Status:** Canonical PR5 contract for offline CV evaluation only.

**Scope:** `photo -> candidate items -> qualitative confidence -> optional portion note -> deterministic nutrition lookup`

**Non-goal:** This file does not define runtime API shapes, upload flows, or client rendering.

---

## 1. Core rules

- Recognition outputs must expose explicit confidence semantics.
- Confidence remains qualitative for this phase:
  - `high`
  - `medium`
  - `low`
  - `unknown`
- Nutrition values must come from deterministic lookup, never from LLM guesses.
- Low-confidence results must degrade deterministically.
- Raw user images are sensitive by default and must not be retained unless a future PR
  explicitly changes that policy.

---

## 2. Canonical evaluation shape

Illustrative offline packet/output shape:

```json
{
  "items": [
    {
      "name": "pasta",
      "confidence_bucket": "medium",
      "portion_estimate": null,
      "nutrition_db_match_id": "fooddb:987"
    }
  ],
  "warnings": ["multiple plausible candidates"],
  "metadata": {
    "dataset": {
      "id": "food-101",
      "version": "1.0"
    },
    "degrade_state": "confirm_top_candidate"
  }
}
```

PR5 contract fields for offline evaluation:

- `items[]`
- per-item confidence bucket
- optional portion estimate note
- deterministic nutrition lookup identifier
- `warnings[]`
- `metadata`

---

## 3. Deterministic degrade states

Future runtime/client surfaces must map from evaluation outcomes into one of these states:

- `show_ranked_candidates`
- `confirm_top_candidate`
- `manual_entry_required`
- `reject_unusable_image`
- `privacy_blocked`

Semantics:

- `show_ranked_candidates`: plausible set is present, but no single item is strong enough
- `confirm_top_candidate`: best candidate is strong enough for confirmation, not silent acceptance
- `manual_entry_required`: recognition signal is too weak; user must enter or search manually
- `reject_unusable_image`: image quality or content is too poor for useful inference
- `privacy_blocked`: policy/consent rules prevent image-derived processing

---

## 4. Offline negative controls

Minimum negative controls:

- non-food image
- empty or invalid image
- ambiguous multi-item image
- low-light / blur / occlusion
- out-of-distribution image

Future deterministic checks should prove:

1. invalid images are rejected cleanly
2. empty recognition returns no silent defaults
3. ambiguous images do not overclaim certainty
4. privacy restrictions can force `privacy_blocked`
5. degrade behavior is stable for repeated identical inputs

---

## 5. Privacy packet minimum

Every CV packet must record:

- `raw_image_retention`
- `logging_policy`
- `consent_policy`
- `deletion_policy`

Default PR5 posture:

- `raw_image_retention = none`
- `logging_policy = no_raw_images`
- `consent_policy = explicit_opt_in`
- `deletion_policy = delete_on_request`

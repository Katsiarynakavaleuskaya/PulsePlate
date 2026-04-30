# Reviewer Packet Hash Contract

**Schema version:** `release-reviewer-packet-hashes.v1`
**Release-control-plane slice:** PR-1, `release/release-control-plane-pr1-reviewer-hash`
**Schema:** [`REVIEWER_PACKET_HASH_CONTRACT.schema.json`](REVIEWER_PACKET_HASH_CONTRACT.schema.json)

## Purpose

This contract defines the reviewer identity portion of the internal release
packet. It consumes landed App Store readiness artifacts from `main` as
upstream evidence and does not own the App Store readiness PR train, Fastlane
upload behavior, App Store Connect credentials, or reviewer copy content.

## Upstream Artifacts

The canonical upstream artifact names are:

- `ios/fastlane/metadata/review_information/notes.txt`
- `ios/fastlane/metadata/en-US/{name,subtitle,description,keywords,promotional_text,release_notes,privacy_url,support_url,marketing_url}.txt`
- `ios/fastlane/metadata/ru-RU/{name,subtitle,description,keywords,promotional_text,release_notes,privacy_url,support_url,marketing_url}.txt`
- `ios/fastlane/metadata/es-ES/{name,subtitle,description,keywords,promotional_text,release_notes,privacy_url,support_url,marketing_url}.txt`
- `ios/fastlane/app_privacy_details.json` as upstream context only.

`ios/fastlane/app_privacy_details.json` is included in `source_artifacts` as
`app_privacy_context` when present, but it is not part of
`appstore_metadata_hash` in PR-1. App Privacy identity can be promoted into the
future release manifest only through a dedicated release-control-plane slice.

## Hash Fields

| Field | Source | Format |
| --- | --- | --- |
| `reviewer_notes_hash` | Canonical bytes for `ios/fastlane/metadata/review_information/notes.txt` | SHA-256 lowercase hex, no prefix |
| `appstore_metadata_hash` | Canonical JSON manifest of per-file hashes for localized Fastlane metadata files | SHA-256 lowercase hex, no prefix |

Every hash uses SHA-256 over canonical UTF-8 bytes and is emitted as lowercase
64-character hexadecimal without a `sha256:` prefix.

## Canonicalization

Text artifacts are canonicalized before hashing:

1. Decode bytes as UTF-8.
2. Normalize `CRLF` and `CR` line endings to `LF`.
3. Ensure exactly one trailing `LF`.
4. Preserve all other whitespace and text.
5. Encode as UTF-8 and hash the resulting bytes.

`appstore_metadata_hash` is computed over a canonical JSON manifest containing
the sorted metadata source entries. JSON is serialized with sorted keys,
compact separators, UTF-8, and exactly one trailing `LF`.

## Contract Payload

The deterministic helper is
`scripts/release/reviewer_packet_hashes.py`. It emits:

```json
{
  "schema_version": "release-reviewer-packet-hashes.v1",
  "hash_algorithm": "sha256",
  "canonicalization": "utf8-lf-single-trailing-newline",
  "reviewer_notes_hash": "<64 lowercase hex>",
  "appstore_metadata_hash": "<64 lowercase hex>",
  "source_artifacts": [
    {
      "kind": "reviewer_notes",
      "path": "ios/fastlane/metadata/review_information/notes.txt",
      "hash": "<64 lowercase hex>"
    }
  ]
}
```

## Boundaries

This PR-1 contract does not:

- modify App Store metadata, reviewer notes, privacy payloads, screenshots, or
  Fastlane upload lanes;
- read App Store Connect credentials, signing material, reviewer credentials,
  or protected GitHub environment secrets;
- generate the final release manifest;
- produce an `ALLOW` / `BLOCK` release decision.

Those behaviors remain scoped to later release-control-plane slices and the
separate App Store readiness train.

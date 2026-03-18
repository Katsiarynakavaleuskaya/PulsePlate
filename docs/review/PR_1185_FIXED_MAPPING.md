# PR 1185 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
Evidence: app/schemas/payments.py, app/services/payments_activation.py, app/routers/billing.py — receipt max_length, activation contract, audit findings addressed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949279076 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#pullrequestreview-3963466028 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949290816 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949290822 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949290825 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949290846 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949290855 -> 26ec3bd0f89f96047d491f4be4db165fbfabbfe3

Disposition: FIXED
Commit: 732b88ef9da6ea20162d9920be965c0d49f0552a
Evidence: app/services/payments_activation.py, app/schemas/payments.py, tests/test_apple_receipt_verify_service_helpers.py, tests/test_subscription_activation_api.py, docs/security/PR_1185_BILLING_ACTIVATION_CONTRACT_AUDIT.md, frontend/src/api/schema.ts
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949590945 -> 732b88ef9da6ea20162d9920be965c0d49f0552a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949590947 -> 732b88ef9da6ea20162d9920be965c0d49f0552a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949590955 -> 732b88ef9da6ea20162d9920be965c0d49f0552a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949590957 -> 732b88ef9da6ea20162d9920be965c0d49f0552a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949590963 -> 732b88ef9da6ea20162d9920be965c0d49f0552a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#pullrequestreview-3963796793 -> 732b88ef9da6ea20162d9920be965c0d49f0552a

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pr1185-cubic-activation-contract
Reason: Cubic review comments (21:02Z) posted after commit 26ec3bd0 (20:52 UTC). Defer to follow-up PR for activation contract refinements.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949556924
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949556932
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949556934
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949556939
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949556942
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2949556947
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#pullrequestreview-3963762156

Disposition: FIXED
Commit: ff8a5de77772b9a490cb3ef2ce8c0c3cf12fe8c5
Evidence: app/services/payments_activation.py, app/schemas/payments.py, tests/test_subscription_activation_api.py, frontend/src/api/openapi.json, frontend/src/api/schema.ts
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2955994946 -> ff8a5de77772b9a490cb3ef2ce8c0c3cf12fe8c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2955994949 -> ff8a5de77772b9a490cb3ef2ce8c0c3cf12fe8c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#discussion_r2955994957 -> ff8a5de77772b9a490cb3ef2ce8c0c3cf12fe8c5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1185#pullrequestreview-3970576952 -> ff8a5de77772b9a490cb3ef2ce8c0c3cf12fe8c5

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] Pre-commit green

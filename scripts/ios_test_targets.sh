#!/usr/bin/env bash
# Canonical -only-testing list for iOS unit tests (AGENTS.md, Makefile, ci.yml)
# Output: comma-separated PulsePlateTests/ClassName entries
# Usage: ./scripts/ios_test_targets.sh
# Consumers: Makefile (ios-test), .github/workflows/ci.yml (ios-tests job)
set -euo pipefail

TESTS=(
  "PulsePlateTests/ThinClientGuardsTests"
  "PulsePlateTests/ProKeyProviderTests"
  "PulsePlateTests/KeychainStoreTests"
  "PulsePlateTests/BMIServiceTests"
  "PulsePlateTests/BMIResponseDecodingTests"
  "PulsePlateTests/BMIRequestEncodingTests"
  "PulsePlateTests/LocaleParsingTests"
  "PulsePlateTests/HTTPClientTests"
  "PulsePlateTests/APIClientTests"
  "PulsePlateTests/BMIServiceThinAdapterTests"
  "PulsePlateTests/SubscriptionBillingServiceTests"
  "PulsePlateTests/SubscriptionManagerTests"
  "PulsePlateTests/StoreKitProductCatalogTests"
  "PulsePlateTests/StoreKitManagerCatalogTests"
)

# Output comma-separated for Makefile IOS_ONLY_TESTING parsing (no trailing newline)
IFS=','; printf '%s' "${TESTS[*]}"; unset IFS

#!/usr/bin/env bash
# Canonical -only-testing selector for iOS unit tests (AGENTS.md, Makefile, ci.yml)
# Output: the complete PulsePlateTests target
# Usage: ./scripts/ios_test_targets.sh
# Consumers: Makefile (ios-test), .github/workflows/ci.yml (ios-tests job)
set -euo pipefail

printf '%s' 'PulsePlateTests'

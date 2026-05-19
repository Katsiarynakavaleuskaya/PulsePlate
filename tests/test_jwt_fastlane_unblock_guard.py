from __future__ import annotations

from scripts.ci.check_jwt_fastlane_unblock import (
    evaluate_bundler_evidence,
    parse_bundler_evidence,
)

BLOCKED_BUNDLER_OUTPUT = """
GEM
  remote: https://rubygems.org/
  specs:
    fastlane (2.234.0)
      jwt (>= 2.1.0, < 3)
    googleauth (1.11.2)
      jwt (>= 1.4, < 3.0)
    jwt (2.10.2)
      base64
    signet (0.21.0)
      jwt (>= 1.5, < 4.0)
"""


UNBLOCKED_BUNDLER_OUTPUT = """
GEM
  remote: https://rubygems.org/
  specs:
    fastlane (2.235.0)
      jwt (>= 3.2.0, < 4)
    googleauth (1.16.2)
      jwt (>= 3.2.0, < 4.0)
    jwt (3.2.0)
    signet (0.21.0)
      jwt (>= 1.5, < 4.0)
"""


def test_jwt_fastlane_guard_accepts_current_blocked_resolver_graph() -> None:
    evidence = parse_bundler_evidence(BLOCKED_BUNDLER_OUTPUT)

    assert evidence.versions["fastlane"] == "2.234.0"
    assert evidence.versions["jwt"] == "2.10.2"
    assert evidence.jwt_constraints["fastlane"] == ">= 2.1.0, < 3"
    assert evaluate_bundler_evidence(evidence) == []


def test_jwt_fastlane_guard_fails_when_resolver_reaches_patched_jwt() -> None:
    errors = evaluate_bundler_evidence(parse_bundler_evidence(UNBLOCKED_BUNDLER_OUTPUT))

    assert any("remove the Trivy suppression" in error for error in errors)


def test_jwt_fastlane_guard_fails_when_fastlane_no_longer_blocks_jwt_3() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (>= 2.1.0, < 3)", "jwt (>= 2.1.0, < 4)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert any("Fastlane 2.234.0 no longer constrains jwt below 3" in error for error in errors)

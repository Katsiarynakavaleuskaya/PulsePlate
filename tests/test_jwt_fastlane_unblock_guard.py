from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.check_jwt_fastlane_unblock import (
    evaluate_bundler_evidence,
    main,
    parse_bundler_evidence,
    patched_jwt_resolved,
    remediation_evidence_complete,
    trivy_suppression_present,
    validate_tracked_lockfile,
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
    evidence = parse_bundler_evidence(UNBLOCKED_BUNDLER_OUTPUT)
    errors = evaluate_bundler_evidence(evidence)

    assert any("remove the Trivy suppression" in error for error in errors)
    assert patched_jwt_resolved(evidence) is True
    assert remediation_evidence_complete(evidence) is True


def test_jwt_fastlane_guard_does_not_accept_malformed_evidence_without_suppression() -> None:
    evidence = parse_bundler_evidence("GEM\n  specs:\n    fastlane (2.235.0)\n")

    assert patched_jwt_resolved(evidence) is False
    assert remediation_evidence_complete(evidence) is False
    assert "Bundler output did not include a resolved jwt version." in evaluate_bundler_evidence(
        evidence
    )


def test_jwt_fastlane_guard_requires_complete_remediation_evidence() -> None:
    evidence = parse_bundler_evidence("GEM\n  specs:\n    jwt (3.2.0)\n")

    assert patched_jwt_resolved(evidence) is True
    assert remediation_evidence_complete(evidence) is False
    assert "Bundler output did not include fastlane." in evaluate_bundler_evidence(evidence)


def test_jwt_fastlane_guard_validates_tracked_lockfile_jwt_floor(tmp_path: Path) -> None:
    lockfile = tmp_path / "Gemfile.lock"
    lockfile.write_text(UNBLOCKED_BUNDLER_OUTPUT, encoding="utf-8")

    assert validate_tracked_lockfile(lockfile) == []


def test_jwt_fastlane_guard_rejects_vulnerable_tracked_lockfile(tmp_path: Path) -> None:
    lockfile = tmp_path / "Gemfile.lock"
    lockfile.write_text(BLOCKED_BUNDLER_OUTPUT, encoding="utf-8")

    assert validate_tracked_lockfile(lockfile) == [
        "Tracked ios/Gemfile.lock resolves jwt 2.10.2, below patched floor 3.2.0."
    ]


def test_jwt_fastlane_guard_rejects_incomplete_patched_lockfile(tmp_path: Path) -> None:
    lockfile = tmp_path / "Gemfile.lock"
    lockfile.write_text("GEM\n  specs:\n    jwt (3.2.0)\n", encoding="utf-8")

    assert validate_tracked_lockfile(lockfile) == [
        "Tracked ios/Gemfile.lock does not include complete Fastlane jwt remediation evidence."
    ]


def test_jwt_fastlane_guard_detects_removed_trivy_suppression(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")

    assert trivy_suppression_present(policy) is False


def test_jwt_fastlane_guard_detects_present_trivy_suppression(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text(
        'package trivy\n\nignore if {\n\tinput.VulnerabilityID == "CVE-2026-45363"\n}\n',
        encoding="utf-8",
    )

    assert trivy_suppression_present(policy) is True


def test_jwt_fastlane_guard_detects_rego_suppression_with_inline_comment(
    tmp_path: Path,
) -> None:
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    policy.write_text(
        'package trivy\n\nignore if {\n\tinput.VulnerabilityID == "CVE-2026-45363" # Ruby jwt\n}\n',
        encoding="utf-8",
    )
    trivyignore.write_text("", encoding="utf-8")

    assert trivy_suppression_present(policy, trivyignore) is True


def test_jwt_fastlane_guard_ignores_rego_comment_only_cve_reference(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    policy.write_text(
        "package trivy\n\n# CVE-2026-45363 removed in PR 1839\n",
        encoding="utf-8",
    )
    trivyignore.write_text("", encoding="utf-8")

    assert trivy_suppression_present(policy, trivyignore) is False


def test_jwt_fastlane_guard_fails_closed_on_unreadable_rego_policy(tmp_path: Path) -> None:
    trivyignore = tmp_path / ".trivyignore"
    trivyignore.write_text("", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Unable to read Trivy policy file"):
        trivy_suppression_present(tmp_path, trivyignore)


def test_jwt_fastlane_guard_detects_legacy_trivyignore_suppression(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")
    trivyignore.write_text("CVE-2026-45363\n", encoding="utf-8")

    assert trivy_suppression_present(policy, trivyignore) is True


def test_jwt_fastlane_guard_detects_annotated_trivyignore_suppression(
    tmp_path: Path,
) -> None:
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")
    trivyignore.write_text(
        "CVE-2026-45363 exp:2026-08-31\nCVE-2026-45363 # Ruby jwt\n",
        encoding="utf-8",
    )

    assert trivy_suppression_present(policy, trivyignore) is True


def test_jwt_fastlane_guard_ignores_trivyignore_comment_only_cve_reference(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")
    trivyignore.write_text("# CVE-2026-45363 removed in PR 1839\n", encoding="utf-8")

    assert trivy_suppression_present(policy, trivyignore) is False


def test_jwt_fastlane_guard_fails_closed_on_unreadable_trivyignore(tmp_path: Path) -> None:
    policy = tmp_path / "ignore-policy.rego"
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match=r"Unable to read \.trivyignore file"):
        trivy_suppression_present(policy, tmp_path)


def test_jwt_fastlane_guard_passes_after_complete_remediation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    resolver_output = tmp_path / "resolver.txt"
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    lockfile = tmp_path / "Gemfile.lock"
    resolver_output.write_text(UNBLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    lockfile.write_text(UNBLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")
    trivyignore.write_text("", encoding="utf-8")

    assert (
        main(
            [
                "--resolver-output",
                str(resolver_output),
                "--trivy-policy",
                str(policy),
                "--trivy-ignore",
                str(trivyignore),
                "--lockfile",
                str(lockfile),
            ]
        )
        == 0
    )
    assert "suppression has been removed" in capsys.readouterr().out


def test_jwt_fastlane_guard_passes_for_blocked_resolver_with_active_suppression(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolver_output = tmp_path / "resolver.txt"
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    lockfile = tmp_path / "Gemfile.lock"
    resolver_output.write_text(BLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    lockfile.write_text(BLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    policy.write_text(
        'package trivy\n\nignore if {\n\tinput.VulnerabilityID == "CVE-2026-45363"\n}\n',
        encoding="utf-8",
    )
    trivyignore.write_text("", encoding="utf-8")

    assert (
        main(
            [
                "--resolver-output",
                str(resolver_output),
                "--trivy-policy",
                str(policy),
                "--trivy-ignore",
                str(trivyignore),
                "--lockfile",
                str(lockfile),
            ]
        )
        == 0
    )
    assert "temporary suppression still requires monitoring" in capsys.readouterr().out


def test_jwt_fastlane_guard_fails_when_suppression_absent_but_resolver_blocked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolver_output = tmp_path / "resolver.txt"
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    lockfile = tmp_path / "Gemfile.lock"
    resolver_output.write_text(BLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    lockfile.write_text(UNBLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")
    trivyignore.write_text("", encoding="utf-8")

    assert (
        main(
            [
                "--resolver-output",
                str(resolver_output),
                "--trivy-policy",
                str(policy),
                "--trivy-ignore",
                str(trivyignore),
                "--lockfile",
                str(lockfile),
            ]
        )
        == 1
    )
    assert "suppression is absent but resolver remains blocked" in capsys.readouterr().out


def test_jwt_fastlane_guard_fails_when_suppression_absent_but_lockfile_incomplete(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolver_output = tmp_path / "resolver.txt"
    policy = tmp_path / "ignore-policy.rego"
    trivyignore = tmp_path / ".trivyignore"
    lockfile = tmp_path / "Gemfile.lock"
    resolver_output.write_text(UNBLOCKED_BUNDLER_OUTPUT, encoding="utf-8")
    lockfile.write_text("GEM\n  specs:\n    jwt (3.2.0)\n", encoding="utf-8")
    policy.write_text("package trivy\n\ndefault ignore := false\n", encoding="utf-8")
    trivyignore.write_text("", encoding="utf-8")

    assert (
        main(
            [
                "--resolver-output",
                str(resolver_output),
                "--trivy-policy",
                str(policy),
                "--trivy-ignore",
                str(trivyignore),
                "--lockfile",
                str(lockfile),
            ]
        )
        == 1
    )
    assert "lockfile remediation is incomplete" in capsys.readouterr().out


def test_jwt_fastlane_guard_fails_when_fastlane_no_longer_blocks_jwt_3() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (>= 2.1.0, < 3)", "jwt (>= 2.1.0, < 4)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert any("Fastlane 2.234.0 no longer blocks jwt 3.2.0" in error for error in errors)


def test_jwt_fastlane_guard_treats_partial_three_x_constraint_as_still_blocked() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (>= 2.1.0, < 3)", "jwt (>= 2.1.0, < 3.2)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert errors == []


def test_jwt_fastlane_guard_treats_three_zero_constraint_as_still_blocked() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (>= 2.1.0, < 3)", "jwt (>= 2.1.0, < 3.0)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert errors == []


def test_jwt_fastlane_guard_treats_pessimistic_two_x_constraint_as_still_blocked() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (>= 2.1.0, < 3)", "jwt (~> 2.1)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert errors == []


def test_jwt_fastlane_guard_treats_exact_two_x_constraint_as_still_blocked() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (>= 2.1.0, < 3)", "jwt (= 2.10.2)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert errors == []


def test_jwt_fastlane_guard_does_not_treat_jwt_prerelease_as_patched() -> None:
    output = BLOCKED_BUNDLER_OUTPUT.replace("jwt (2.10.2)", "jwt (3.2.0.rc1)")

    errors = evaluate_bundler_evidence(parse_bundler_evidence(output))

    assert errors == []

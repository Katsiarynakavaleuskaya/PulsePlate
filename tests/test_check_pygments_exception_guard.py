from __future__ import annotations

from scripts.ci import check_pygments_exception_guard as guard


def _alert(*, first_patched_version: str | None) -> dict[str, object]:
    patched_payload = (
        {"identifier": first_patched_version} if first_patched_version is not None else None
    )
    return {
        "dependency": {"package": {"name": "Pygments"}},
        "security_advisory": {"ghsa_id": guard.ADVISORY_ID},
        "security_vulnerability": {"first_patched_version": patched_payload},
    }


def test_evaluate_guard_state_allows_blocked_upstream_with_exception() -> None:
    pins = {
        "requirements.txt": "2.19.2",
        "requirements-dev.txt": "2.19.2",
        "requirements-lock.txt": "2.19.2",
    }

    errors = guard.evaluate_guard_state(
        alerts=[_alert(first_patched_version=None)],
        pins=pins,
        exception_present=True,
    )

    assert errors == []


def test_evaluate_guard_state_fails_when_patch_exists_and_exception_remains() -> None:
    pins = {
        "requirements.txt": "2.19.2",
        "requirements-dev.txt": "2.19.2",
        "requirements-lock.txt": "2.19.2",
    }

    errors = guard.evaluate_guard_state(
        alerts=[_alert(first_patched_version="2.19.3")],
        pins=pins,
        exception_present=True,
    )

    assert len(errors) == 2
    assert "patched release" in errors[0]
    assert ".pre-commit-config.yaml still ignores" in errors[0]
    assert "requirements.txt=2.19.2" in errors[1]


def test_evaluate_guard_state_fails_when_alerts_disappear_but_exception_remains() -> None:
    pins = {
        "requirements.txt": "2.19.2",
        "requirements-dev.txt": "2.19.2",
        "requirements-lock.txt": "2.19.2",
    }

    errors = guard.evaluate_guard_state(
        alerts=[],
        pins=pins,
        exception_present=True,
    )

    assert errors == [
        "No open Dependabot alerts remain for GHSA-5239-wwwm-4pmq, but the temporary "
        "pip-audit exception seam is still present."
    ]


def test_evaluate_guard_state_ignores_unrelated_alerts() -> None:
    pins = {
        "requirements.txt": "2.19.2",
        "requirements-dev.txt": "2.19.2",
        "requirements-lock.txt": "2.19.2",
    }
    unrelated = {
        "dependency": {"package": {"name": "requests"}},
        "security_advisory": {"ghsa_id": "GHSA-xxxx-yyyy-zzzz"},
        "security_vulnerability": {"first_patched_version": {"identifier": "9.9.9"}},
    }

    errors = guard.evaluate_guard_state(
        alerts=[unrelated],
        pins=pins,
        exception_present=True,
    )

    assert errors == [
        "No open Dependabot alerts remain for GHSA-5239-wwwm-4pmq, but the temporary "
        "pip-audit exception seam is still present."
    ]

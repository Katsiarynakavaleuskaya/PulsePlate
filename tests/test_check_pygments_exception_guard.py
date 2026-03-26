from __future__ import annotations

import urllib.error
from pathlib import Path

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
        advisory_patched_versions=set(),
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
        advisory_patched_versions=set(),
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
        advisory_patched_versions=set(),
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
        advisory_patched_versions=set(),
        pins=pins,
        exception_present=True,
    )

    assert errors == [
        "No open Dependabot alerts remain for GHSA-5239-wwwm-4pmq, but the temporary "
        "pip-audit exception seam is still present."
    ]


def test_evaluate_guard_state_allows_unreadable_alert_endpoint_while_unpatched() -> None:
    pins = {
        "requirements.txt": "2.19.2",
        "requirements-dev.txt": "2.19.2",
        "requirements-lock.txt": "2.19.2",
    }

    errors = guard.evaluate_guard_state(
        alerts=None,
        advisory_patched_versions=set(),
        pins=pins,
        exception_present=True,
    )

    assert errors == []


def test_evaluate_guard_state_fails_when_public_advisory_reports_patch() -> None:
    pins = {
        "requirements.txt": "2.19.2",
        "requirements-dev.txt": "2.19.2",
        "requirements-lock.txt": "2.19.2",
    }

    errors = guard.evaluate_guard_state(
        alerts=None,
        advisory_patched_versions={"2.19.3"},
        pins=pins,
        exception_present=True,
    )

    assert len(errors) == 2
    assert "patched release" in errors[0]
    assert ".pre-commit-config.yaml still ignores" in errors[0]
    assert "requirements.txt=2.19.2" in errors[1]


def test_evaluate_guard_state_flags_versions_below_patched_floor() -> None:
    pins = {
        "requirements.txt": "2.19.1",
        "requirements-dev.txt": "2.19.3",
        "requirements-lock.txt": "2.19.3",
    }

    errors = guard.evaluate_guard_state(
        alerts=None,
        advisory_patched_versions={"2.19.3"},
        pins=pins,
        exception_present=True,
    )

    assert len(errors) == 2
    assert "requirements.txt=2.19.1" in errors[1]
    assert "requirements-dev.txt" not in errors[1]


def test_has_exception_seam_tolerates_yaml_whitespace_changes(tmp_path: Path) -> None:
    pre_commit = tmp_path / guard.PRE_COMMIT_PATH
    pre_commit.write_text(
        "args:\n" "  - --ignore-vuln\n" f"    - {guard.ADVISORY_ID}\n",
        encoding="utf-8",
    )

    assert guard._has_exception_seam(tmp_path) is True


def test_fetch_dependabot_alerts_paginates(monkeypatch) -> None:
    first_page = [
        _alert(first_patched_version=None) for _ in range(guard.DEPENDABOT_ALERTS_PER_PAGE)
    ]
    second_page = [_alert(first_patched_version="2.19.3")]

    def fake_api_request_with_headers(
        url: str,
        token: str | None,
    ) -> tuple[object, dict[str, str]]:
        assert token == "token"
        if "after=cursor-2" in url:
            return second_page, {}
        if "dependabot/alerts?state=open&per_page=100" in url:
            return first_page, {
                "Link": (
                    "<https://api.github.com/repos/owner/repo/dependabot/alerts"
                    '?state=open&per_page=100&after=cursor-2>; rel="next"'
                )
            }
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(guard, "_api_request_with_headers", fake_api_request_with_headers)

    alerts = guard._fetch_dependabot_alerts(repo="owner/repo", token="token")

    assert len(alerts) == guard.DEPENDABOT_ALERTS_PER_PAGE + 1


def test_public_api_request_retries_without_token_on_auth_error(monkeypatch) -> None:
    calls: list[str | None] = []

    def fake_api_request(url: str, token: str | None = None) -> object:
        calls.append(token)
        if token == "token":
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        return {"ok": True}

    monkeypatch.setattr(guard, "_api_request", fake_api_request)

    payload = guard._public_api_request("https://api.github.com/advisories/example", "token")

    assert payload == {"ok": True}
    assert calls == ["token", None]

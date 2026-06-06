"""Tests for the unified App Store submission readiness validator.

Verifies that:
- the validator script exists at the expected path
- the Makefile contains the ``ios-appstore-verify`` target
- the validator script passes on the current repo state
- the validator exposes all required check functions
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any

import pytest
from scripts.release import check_ios_appstore_verify as validator_module

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
VALIDATOR_SCRIPT = REPO_ROOT / "scripts" / "release" / "check_ios_appstore_verify.py"
MAKEFILE = REPO_ROOT / "Makefile"

REQUIRED_CHECKS = [
    "check_release_base_url",
    "check_appicon_marketing",
    "check_privacy_manifest",
    "check_app_privacy_details",
    "check_permission_strings",
    "check_healthkit_readonly",
    "check_ai_wellness_consent",
    "check_reviewer_pack",
    "check_screenshot_policy",
    "check_fitchef_release_readiness_bundle",
    "check_storekit_pricing_truth",
]


def test_validator_script_exists() -> None:
    """Validator script must exist at the canonical path."""
    assert VALIDATOR_SCRIPT.exists(), f"Missing validator script: {VALIDATOR_SCRIPT}"
    assert VALIDATOR_SCRIPT.stat().st_size > 0, "Validator script is empty"


def test_makefile_target_exists() -> None:
    """Makefile must contain the ios-appstore-verify target."""
    content = MAKEFILE.read_text(encoding="utf-8")
    assert "ios-appstore-verify:" in content, "Makefile missing ios-appstore-verify target"
    # Target must also be in .PHONY.
    assert (
        "ios-appstore-verify" in content.split(".PHONY:")[-1]
    ), "ios-appstore-verify not declared in .PHONY"
    target_block = content.split("ios-appstore-verify:", maxsplit=1)[1].split(
        "# --- Dev Container targets",
        maxsplit=1,
    )[0]
    assert "repo-local release gates" in target_block
    assert "tests/test_fitchef_app_store_pack.py" in target_block
    assert "submission readiness" not in target_block.lower()


def test_validator_script_passes() -> None:
    """Validator script must exit 0 on the current repo state."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_SCRIPT)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"Validator failed (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_validator_has_required_checks() -> None:
    """Validator script must define all required check functions."""
    content = VALIDATOR_SCRIPT.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED_CHECKS if f"def {name}(" not in content]
    assert not missing, f"Validator missing check functions: {missing}"
    assert "repo-local release validation" in content
    assert "submission readiness" not in content.lower()


def test_validator_registers_all_checks() -> None:
    """ALL_CHECKS list must reference every required check function."""
    content = VALIDATOR_SCRIPT.read_text(encoding="utf-8")
    # Find the ALL_CHECKS list block.
    assert "ALL_CHECKS" in content, "Validator missing ALL_CHECKS list"
    for name in REQUIRED_CHECKS:
        assert name in content.split("ALL_CHECKS")[1], f"Check {name} not registered in ALL_CHECKS"


def _load_validator_module() -> Any:
    return validator_module


def _prepare_fitchef_bundle_fixture(
    module: Any,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[pathlib.Path, dict[str, Any], str]:
    fitchef_base = tmp_path / "fitchef"
    release_dir = fitchef_base / "release_readiness"
    release_dir.mkdir(parents=True)

    matrix_path = release_dir / "shot_scenario_matrix.json"
    checklist_path = release_dir / "rendered_review_testflight_readiness.md"
    payload = json.loads(module.FITCHEF_SHOT_SCENARIO_MATRIX.read_text(encoding="utf-8"))
    checklist = module.FITCHEF_RENDERED_REVIEW_CHECKLIST.read_text(encoding="utf-8")
    matrix_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    checklist_path.write_text(checklist, encoding="utf-8")

    monkeypatch.setattr(module, "FITCHEF_PACK_BASE", fitchef_base)
    monkeypatch.setattr(module, "FITCHEF_RELEASE_READINESS_DIR", release_dir)
    monkeypatch.setattr(module, "FITCHEF_SHOT_SCENARIO_MATRIX", matrix_path)
    monkeypatch.setattr(module, "FITCHEF_RENDERED_REVIEW_CHECKLIST", checklist_path)
    return release_dir, payload, checklist


def _write_matrix_payload(release_dir: pathlib.Path, payload: dict[str, Any]) -> None:
    (release_dir / "shot_scenario_matrix.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _failed_messages(results: list[tuple[bool, str, str]]) -> str:
    return "\n".join(message for ok, _tag, message in results if not ok)


def test_fitchef_release_readiness_validator_rejects_missing_matrix(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir = tmp_path / "release_readiness"
    release_dir.mkdir()
    checklist_path = release_dir / "rendered_review_testflight_readiness.md"
    checklist_path.write_text("Classification: INTERNAL_REVIEW_ONLY", encoding="utf-8")

    monkeypatch.setattr(module, "FITCHEF_RELEASE_READINESS_DIR", release_dir)
    monkeypatch.setattr(module, "FITCHEF_SHOT_SCENARIO_MATRIX", release_dir / "missing.json")
    monkeypatch.setattr(module, "FITCHEF_RENDERED_REVIEW_CHECKLIST", checklist_path)

    results = module.check_fitchef_release_readiness_bundle()
    assert "File missing" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_submit_ready_overclaim(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["public_submission_allowed"] = True
    (release_dir / "shot_scenario_matrix.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "must not claim public submission allowed" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_secret_or_local_path(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\nGH_TOKEN stored at /Users/example/token\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "gh_token" in messages or "/users/" in messages


@pytest.mark.parametrize(
    "claim",
    [
        "Available on Google Play too.",
        "Android companion app support.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_cross_platform_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\n{claim}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Forbidden release-readiness fragment" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_generic_secret_assignment(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    credential_label = "sec" + "ret"
    dummy_value = "abcd1234" + "efgh5678"
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\n{credential_label}={dummy_value}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "Credential-like release bundle value" in messages
    assert dummy_value not in messages


@pytest.mark.parametrize(
    "label_parts",
    [
        ("api", " key"),
        ("gh", " token"),
        ("sec", "ret key"),
    ],
)
def test_fitchef_release_readiness_validator_rejects_spaced_secret_labels(
    label_parts: tuple[str, str],
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    credential_label = "".join(label_parts)
    dummy_value = "placeholder1234"
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\n{credential_label}: {dummy_value}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "Credential-like release bundle value" in messages
    assert dummy_value not in messages


@pytest.mark.parametrize(
    "token",
    [
        "gh" + "p_" + ("a" * 36),
        "gh" + "s_" + ("a" * 36),
        "gh" + "s_" + ("a" * 24) + "." + ("b" * 24) + "." + ("c" * 24),
        "github" + "_pat_" + ("a" * 36),
        "sk-" + "proj-" + ("a" * 36),
    ],
)
def test_fitchef_release_readiness_validator_rejects_raw_token_strings(
    token: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\nOperator paste: {token}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "Credential-like release bundle value" in messages
    assert token not in messages


def test_fitchef_release_readiness_validator_rejects_protected_json_keys(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["github_token"] = "redacted"
    (release_dir / "shot_scenario_matrix.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Scenario matrix top-level schema key drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_media_file(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "shot-01.png").write_bytes(b"not a real screenshot")

    results = module.check_fitchef_release_readiness_bundle()
    assert "Media file is not allowed" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_media_anywhere_in_pack(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    screenshot_dir = release_dir.parent / "en-US" / "iphone-6.9" / "screenshots"
    screenshot_dir.mkdir(parents=True)
    (screenshot_dir / "01_core-value.png").write_bytes(b"not a real screenshot")

    results = module.check_fitchef_release_readiness_bundle()
    assert "Media file is not allowed in FitChef App Store pack" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_symlinks_in_pack(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    symlink_path = release_dir.parent / "operator_notes.md"
    symlink_path.symlink_to(tmp_path / "local-release-note.md")

    results = module.check_fitchef_release_readiness_bundle()
    assert "Symlink is not allowed" in _failed_messages(results)


@pytest.mark.parametrize("path_part", ["artifacts", ".venv"])
def test_fitchef_release_readiness_validator_rejects_forbidden_pack_path_segments(
    path_part: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    forbidden_dir = release_dir.parent / path_part
    forbidden_dir.mkdir()
    (forbidden_dir / "render_note.md").write_text(
        "Internal rendered-review note only.\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Forbidden FitChef App Store pack path segment" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_extra_release_note_claims(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "operator_notes.md").write_text(
        "GH_TOKEN=not-a-real-token\nFastlane upload completed.\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "gh_token" in messages.lower() or "Protected release action claim" in messages


def test_fitchef_release_readiness_validator_scans_locale_pack_text(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    locale_note = release_dir.parent / "en-US" / "metadata" / "source_of_truth.md"
    locale_note.parent.mkdir(parents=True)
    credential_label = "sec" + "ret"
    dummy_value = "abcd1234" + "efgh5678"
    locale_note.write_text(
        f"Fastlane upload completed.\n{credential_label}={dummy_value}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "Protected release action claim" in messages or "Credential-like" in messages
    assert dummy_value not in messages


def test_fitchef_release_readiness_validator_scans_pack_paths_for_claims(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "cure-notes.md").write_text(
        "Internal rendered-review note only.\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Wellness copy: diagnóstico y tratamiento médico para pacientes.",
        "Recomendado por nutricionistas.",
        "Consejo terapeutico para tu menu.",
        "Текст обещает медицинское лечение для пациентов.",
        "Советы диетолога для меню.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_localized_medical_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Localized medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Ayuda a tratar tus habitos.",
        "Consejos de medico para tu menu.",
        "Prescripcion medica y medicamento para tu menu.",
        "Лекарство и медикамент для плана питания.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_spanish_treatment_role_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Localized medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "FitChef no proporciona diagnostico, tratamiento medico ni terapia.",
        "FitChef не предоставляет диагноз, лечение или терапию.",
    ],
)
def test_fitchef_release_readiness_validator_allows_localized_boundary_disclaimers(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert not _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Sin diagnostico y diagnostico para pacientes.",
        "Без диагноз и диагноз для пациентов.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_repeated_localized_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Localized medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Oferta prueba gratis.",
        "Precio 9,99 €.",
        "Условия подписки остаются за StoreKit.",
        "Пробный период скрыт от скриншота.",
        "Цена 9,99 ₽.",
        "Стоимость 9,99 руб.",
        "€9,99",
        "₽ 999",
        "EUR 9.99",
        "EUR9.99",
        "USD9.99",
        "RUB999",
    ],
)
def test_fitchef_release_readiness_validator_rejects_localized_pricing_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\n{claim}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "Pricing/trial claim" in messages or "Localized pricing/trial claim" in messages


@pytest.mark.parametrize(
    "claim",
    [
        "listo para subir",
        "subida completada",
        "готов к загрузке",
        "готов к релизу",
    ],
)
def test_fitchef_release_readiness_validator_rejects_localized_upload_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\n{claim}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Localized protected release action claim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Guaranteed weight loss results.",
        "Guaranteed adherence with meal plan.",
        "Clinically proven meal plan.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_guaranteed_outcome_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Guaranteed/clinical outcome claim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Cure headaches with this plan.",
        "The app is diagnosing eating patterns.",
        "The app provides treatments for nutrition issues.",
        "Ask a doctor about your menu inside FitChef.",
        "Guidance from a healthcare professional.",
        "Prescription and medication guidance.",
        "Lower cholesterol and blood pressure.",
        "Avoid diabetes with weekly menus.",
        "No diagnosis and treat patients.",
        "Nutritionist-recommended menu.",
        "Dietitian approved plan.",
        "Therapeutic meal plan.",
        "Medical-grade nutrition app.",
        "medical monitoring support.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_expanded_medical_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Instant results for every meal.",
        "Rapid outcomes for busy weeks.",
        "Resultados rapidos para tu cuerpo.",
        "Most accurate nutrition app.",
        "#1 nutrition assistant for families.",
        "Number one wellness planner.",
        "Top-ranked diet app.",
        "Best nutrition plan.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_ranking_and_speed_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Guaranteed/clinical outcome claim" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_scalar_json_pricing_claims(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "pricing_note.json").write_text(
        json.dumps({"price_eur": 9.99, "trial_days": 14}),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Pricing/trial claim" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_json_action_status_claims(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "operator_status.json").write_text(
        json.dumps({"fastlane_upload": True, "app_store_connect_mutation": True}),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Protected release action claim" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_windows_local_path(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\nLocal render output: C:\\\\Users\\\\alice\\\\AppData\\\\Local\\\\Temp\\\\shot.png\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    messages = _failed_messages(results)
    assert "local path" in messages
    assert "alice" not in messages


def test_fitchef_release_readiness_validator_rejects_source_path_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["source_paths"]["ios_context"] = "ios/PulsePlate/AppStore/Missing.swift"
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "source_paths value drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_source_pr_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["source_pr"] = {"number": 0, "merge_commit": ""}
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "source_pr provenance drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_schema_version_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["schema_version"] = "oops"
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "schema_version drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_blocked_action_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["blocked_release_actions"] = []
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "blocked_release_actions drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_requires_protected_export_actions(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["blocked_release_actions"] = [
        action
        for action in payload["blocked_release_actions"]
        if action != "screenshot_binary_export"
    ]
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "blocked_release_actions drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_locale_manifest_mismatch(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["locale_review_matrix"][0][
        "manifest_path"
    ] = "appstore/fitchef/ru-RU/iphone-6.9/screenshots/shot_manifest.json"
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Manifest path must point to governed FitChef pack" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_testflight_completed_claim(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["testflight_smoke_status"] = "passed"
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "TestFlight smoke status must stay not_started" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_medical_matrix_claim(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = "Diagnose diabetes and treat patients."
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize("separator", [":", ".", ";", "!", "?", ",", " - "])
def test_fitchef_release_readiness_validator_rejects_negation_bypass_overclaim(
    separator: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0][
        "privacy_ai_wellness_note"
    ] = f"No wellness issue{separator} Diagnose diabetes and treat patients."
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Medical/wellness overclaim" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_punctuation_only_negation_gap(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = "No, Diagnose patients."
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Medical/wellness overclaim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "No diagnosis and diagnosis patients.",
        "No diagnosis, diagnosis patients.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_later_same_term_overclaim(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = claim
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Medical/wellness overclaim" in _failed_messages(results)


def test_fitchef_release_readiness_validator_allows_boundary_lists(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0][
        "privacy_ai_wellness_note"
    ] = "Wellness-only copy with no diagnosis, treatment, therapy, or clinical nutrition claim."
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert not _failed_messages(results)


def test_fitchef_release_readiness_validator_allows_natural_disclaimer_phrasing(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0][
        "privacy_ai_wellness_note"
    ] = "PulsePlate does not provide medical diagnosis, treatment, or therapy advice."
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert not _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_ios_screenshot_source_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    ios_tests.write_text(
        module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8").replace(
            '"01_core-value"',
            '"99_core-value"',
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert "iOS screenshot test screenshot name drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_ios_screenshot_case_swap(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    ios_test_text = module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8")
    ios_test_text = ios_test_text.replace('"01_core-value"', '"__tmp_core_value__"', 1)
    ios_test_text = ios_test_text.replace('"02_nutrition-analysis"', '"01_core-value"', 1)
    ios_test_text = ios_test_text.replace('"__tmp_core_value__"', '"02_nutrition-analysis"', 1)
    ios_tests.write_text(ios_test_text, encoding="utf-8")
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert "iOS screenshot test screenshot name drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_missing_xctest_capture_method(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    method_block = """    @MainActor
    func testMealPlannerScreenshot() {
        captureScreenshot(for: .mealPlanner)
    }

"""
    ios_tests.write_text(
        module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8").replace(method_block, ""),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert "XCTest method missing for meal_planner" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_wrong_xctest_capture_call(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    ios_tests.write_text(
        module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8").replace(
            "captureScreenshot(for: .mealPlanner)",
            "captureScreenshot(for: .coreValue)",
            1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert "XCTest method drift for meal_planner" in _failed_messages(results)


def test_fitchef_release_readiness_validator_ignores_commented_xctest_capture_call(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    ios_tests.write_text(
        module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8").replace(
            "captureScreenshot(for: .mealPlanner)",
            "// captureScreenshot(for: .mealPlanner)",
            1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert "XCTest method drift for meal_planner" in _failed_messages(results)


@pytest.mark.parametrize(
    ("old", "new", "expected_message"),
    [
        (
            '"-appstore-screenshot-scenario", scenario.rawValue',
            '"-appstore-screenshot-scenario", "core_value"',
            "missing scenario launch argument",
        ),
        (
            "snapshot(scenario.screenshotName, timeWaitingForIdle: 0.3)",
            'snapshot("wrong", timeWaitingForIdle: 0.3)',
            "missing scenario snapshot name",
        ),
    ],
)
def test_fitchef_release_readiness_validator_rejects_capture_helper_drift(
    old: str,
    new: str,
    expected_message: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    ios_tests.write_text(
        module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8").replace(old, new, 1),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert expected_message in _failed_messages(results)


def test_fitchef_release_readiness_validator_ignores_commented_swift_return_literal(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_tests = tmp_path / "AppStoreScreenshotTests.swift"
    ios_tests.write_text(
        module.APPSTORE_SCREENSHOT_TESTS.read_text(encoding="utf-8").replace(
            'return "03_meal-planner"',
            '// return "03_meal-planner"\n                return "03_wrong"',
            1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_TESTS", ios_tests)

    results = module.check_fitchef_release_readiness_bundle()
    assert "screenshot name drift for meal_planner" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_unbound_rendered_scenario_case(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _prepare_fitchef_bundle_fixture(module, tmp_path, monkeypatch)
    ios_context = tmp_path / "AppStoreScreenshotContext.swift"
    ios_context.write_text(
        module.APPSTORE_SCREENSHOT_CONTEXT.read_text(encoding="utf-8").replace(
            ".appStoreScreenshotRoot(scenario.accessibilityIdentifier)",
            ".accessibilityIdentifier(scenario.accessibilityIdentifier)",
            1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "APPSTORE_SCREENSHOT_CONTEXT", ios_context)

    results = module.check_fitchef_release_readiness_bundle()
    assert "rendered scenarioView case drift for core_value" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_blank_privacy_note(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["scenarios"][0]["privacy_ai_wellness_note"] = ""
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "privacy_ai_wellness_note must be non-empty text" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_unsafe_wellness_status(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["locale_review_matrix"][0]["wellness_claim_status"] = "unsafe_status_ok"
    _write_matrix_payload(release_dir, payload)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Unknown wellness-claim status" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_time_range_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["locale_review_matrix"][1]["time_range"] = "3-7s"
    (release_dir / "shot_scenario_matrix.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Time range drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_duplicate_locale_rows(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    payload["locale_review_matrix"].append(payload["locale_review_matrix"][0])
    (release_dir / "shot_scenario_matrix.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Locale review matrix row count drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_reviewer_matrix_drift(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    _release_dir, _payload, _checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    reviewer_matrix = tmp_path / "APPSTORE_REVIEWER_SUBMISSION_MATRIX.md"
    reviewer_text = module.REVIEWER_SUBMISSION_MATRIX.read_text(encoding="utf-8")
    reviewer_text += "\n| `core_value` | `IMPLEMENTATION_REQUIRED` |\n"
    reviewer_matrix.write_text(reviewer_text, encoding="utf-8")
    monkeypatch.setattr(module, "REVIEWER_SUBMISSION_MATRIX", reviewer_matrix)

    results = module.check_fitchef_release_readiness_bundle()
    assert "Reviewer submission matrix classification drift" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_protected_action_claims(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        "\n".join(
            [
                checklist,
                "Fastlane upload completed for all screenshots.",
                "App Store Connect mutation completed for the draft.",
                "Screenshot binary export completed.",
            ]
        ),
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Protected release action claim" in _failed_messages(results)


@pytest.mark.parametrize(
    "claim",
    [
        "Environment activation completed.",
        "Preview video export completed.",
        "Screenshot binary commit completed.",
        "Preview video binary commit completed.",
    ],
)
def test_fitchef_release_readiness_validator_rejects_all_protected_action_claims(
    claim: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\n{claim}\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "Protected release action claim" in _failed_messages(results)


def test_fitchef_release_readiness_validator_rejects_pricing_text(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\nOffer a 14-day free trial in the rendered copy.\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "free trial" in _failed_messages(results).lower()


def test_fitchef_release_readiness_validator_rejects_stale_wellness_promise(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_validator_module()
    release_dir, _payload, checklist = _prepare_fitchef_bundle_fixture(
        module, tmp_path, monkeypatch
    )
    (release_dir / "rendered_review_testflight_readiness.md").write_text(
        f"{checklist}\nRendered copy may improve health.\n",
        encoding="utf-8",
    )

    results = module.check_fitchef_release_readiness_bundle()
    assert "improve health" in _failed_messages(results)

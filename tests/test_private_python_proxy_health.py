from __future__ import annotations

import html
from pathlib import Path
import socket
from urllib.error import HTTPError

import pytest

from scripts.ci import check_private_python_proxy_health as checker

APPROVED_INDEX = "https://packages.pulseplate.app/root/pulseplate/+simple/"


def simple_page(wheel_project: str, version: str) -> bytes:
    return (
        f'<html><body><a href="../../+f/abc/{wheel_project}-{version}-py3-none-any.whl">'
        f"{wheel_project}-{version}-py3-none-any.whl</a></body></html>"
    ).encode()


def source_page(project: str, version: str) -> bytes:
    return (
        f'<html><body><a href="../../+f/abc/{project}-{version}.tar.gz">'
        f"{project}-{version}.tar.gz</a></body></html>"
    ).encode()


def wheel_page(*filenames: str) -> bytes:
    links = "".join(f'<a href="../../+f/abc/{filename}">{filename}</a>' for filename in filenames)
    return f"<html><body>{links}</body></html>".encode()


def wheel_page_with_requires_python(*links: tuple[str, str | None]) -> bytes:
    anchors: list[str] = []
    for filename, requires_python in links:
        requires_python_attr = (
            ""
            if requires_python is None
            else f' data-requires-python="{html.escape(requires_python, quote=True)}"'
        )
        anchors.append(f'<a href="../../+f/abc/{filename}"{requires_python_attr}>wheel</a>')
    return f"<html><body>{''.join(anchors)}</body></html>".encode()


def test_validate_index_url_rejects_unsafe_sources() -> None:
    with pytest.raises(ValueError, match="missing_index_url"):
        checker.validate_index_url("")
    with pytest.raises(ValueError, match="non_https_index_url"):
        checker.validate_index_url("http://packages.pulseplate.app/root/pulseplate/+simple/")
    with pytest.raises(ValueError, match="credentialed_index_url"):
        checker.validate_index_url(
            "https://user:token@packages.pulseplate.app/root/pulseplate/+simple/"  # pragma: allowlist secret
        )
    with pytest.raises(ValueError, match="public_index_url"):
        checker.validate_index_url("https://pypi.org/simple/")
    with pytest.raises(ValueError, match="unexpected_packages_host"):
        checker.validate_index_url("https://pulseplate.app/")
    with pytest.raises(ValueError, match="unexpected_index_path"):
        checker.validate_index_url("https://packages.pulseplate.app/")
    with pytest.raises(ValueError, match="unexpected_index_path"):
        checker.validate_index_url("https://packages.pulseplate.app/simple/")


def test_validate_index_url_normalizes_approved_host() -> None:
    assert checker.validate_index_url(f"  {APPROVED_INDEX.rstrip('/')}  ") == APPROVED_INDEX


def test_validate_index_url_allow_dev_host_still_requires_simple_root() -> None:
    with pytest.raises(ValueError, match="unexpected_index_path"):
        checker.validate_index_url(
            "https://devpi.local/simple/",
            allow_dev_host=True,
        )

    assert (
        checker.validate_index_url(
            "https://devpi.local/root/pulseplate/+simple/",
            allow_dev_host=True,
        )
        == "https://devpi.local/root/pulseplate/+simple/"
    )


def test_project_page_url_uses_normalized_simple_project_page() -> None:
    assert (
        checker.project_page_url(APPROVED_INDEX, "Pydantic_Core")
        == "https://packages.pulseplate.app/root/pulseplate/+simple/pydantic-core/"
    )


def test_wheel_compatibility_accepts_linux_abi3_for_all_github_targets() -> None:
    assert checker.wheel_is_compatible_with_targets(
        "cryptography-48.0.1-cp39-abi3-manylinux_2_28_x86_64.whl",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_wheel_compatibility_rejects_exact_version_for_wrong_platform() -> None:
    assert not checker.wheel_is_compatible_with_targets(
        "cryptography-48.0.1-cp311-abi3-win_amd64.whl",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_wheel_compatibility_rejects_invalid_target_version() -> None:
    with pytest.raises(ValueError, match="invalid_python_version"):
        checker.wheel_is_compatible_with_targets(
            "aiosqlite-0.22.1-py3-none-any.whl",
            target_python_versions=["python-3.11"],
        )


def test_exact_pin_requires_wheel_coverage_for_every_requested_target() -> None:
    assert checker.wheel_is_compatible_with_targets(
        "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl",
        target_python_versions=["3.11", "3.12", "3.13"],
    )
    assert not checker.simple_page_has_exact_pin(
        body=wheel_page("coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl"),
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_exact_pin_accepts_separate_wheel_for_each_requested_target() -> None:
    assert checker.simple_page_has_exact_pin(
        body=wheel_page(
            "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl",
            "coverage-7.15.1-cp312-cp312-manylinux_2_28_x86_64.whl",
            "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl",
        ),
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_exact_pin_wheel_identity_comes_only_from_real_anchor_hrefs() -> None:
    comment_wheel = "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl"
    text_wheel = "coverage-7.15.1-cp312-cp312-manylinux_2_28_x86_64.whl"
    metadata_wheel = "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl"
    real_wheel = "coverage-7.15.1-py3-none-any.whl"
    body = (
        "<html><body>"
        f'<!-- <a href="../../+f/abc/{comment_wheel}">comment</a> -->'
        f"<p>{text_wheel}</p>"
        f'<a data-core-metadata="{metadata_wheel}" '
        f'href="../../+f/abc/{metadata_wheel}.metadata">{metadata_wheel}</a>'
        f'<a href="../../+f/abc/coverage-7.15.0-py3-none-any.whl">{text_wheel}</a>'
        f'<a href="../../+f/abc/{real_wheel}?download=1#sha256={"a" * 64}">opaque</a>'
        "</body></html>"
    ).encode()

    assert checker.exact_pin_wheel_filenames(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
    ) == (real_wheel,)


def test_trusted_exact_pin_hashes_require_proxy_origin_and_sha256() -> None:
    filename = "coverage-7.15.1-py3-none-any.whl"
    digest = "a" * 64
    project_url = f"{APPROVED_INDEX}coverage/"
    body = (f'<a href="../../+f/abc/{filename}#sha256={digest}">{filename}</a>').encode()

    assert checker.trusted_exact_pin_wheel_hashes(
        body=body,
        project_url=project_url,
        normalized_project="coverage",
        expected_version="7.15.1",
    ) == {filename: digest}

    external = (
        f'<a href="https://files.pythonhosted.org/{filename}#sha256={digest}">' f"{filename}</a>"
    ).encode()
    with pytest.raises(ValueError, match="artifact_admission_untrusted_url"):
        checker.trusted_exact_pin_wheel_hashes(
            body=external,
            project_url=project_url,
            normalized_project="coverage",
            expected_version="7.15.1",
        )

    unhashed = f'<a href="../../+f/abc/{filename}">{filename}</a>'.encode()
    with pytest.raises(ValueError, match="artifact_admission_missing_sha256"):
        checker.trusted_exact_pin_wheel_hashes(
            body=unhashed,
            project_url=project_url,
            normalized_project="coverage",
            expected_version="7.15.1",
        )


def test_trusted_exact_pin_hashes_reject_ambiguous_filename() -> None:
    filename = "coverage-7.15.1-py3-none-any.whl"
    project_url = f"{APPROVED_INDEX}coverage/"
    body = (
        f'<a href="../../+f/one/{filename}#sha256={"a" * 64}">one</a>'
        f'<a href="../../+f/two/{filename}#sha256={"b" * 64}">two</a>'
    ).encode()

    with pytest.raises(ValueError, match="artifact_admission_ambiguous_filename"):
        checker.trusted_exact_pin_wheel_hashes(
            body=body,
            project_url=project_url,
            normalized_project="coverage",
            expected_version="7.15.1",
        )


def test_exact_pin_requires_python_is_bound_to_each_wheel_link() -> None:
    body = wheel_page_with_requires_python(
        (
            "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl",
            ">=3.12",
        ),
        (
            "coverage-7.15.1-cp312-cp312-manylinux_2_28_x86_64.whl",
            ">=3.12,<3.13",
        ),
        (
            "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl",
            ">=3.13,<3.14",
        ),
    )

    assert not checker.simple_page_has_exact_pin(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_exact_pin_accepts_missing_and_compound_requires_python_metadata() -> None:
    missing_metadata_body = wheel_page_with_requires_python(
        ("coverage-7.15.1-py3-none-any.whl", None),
    )
    assert checker.simple_page_has_exact_pin(
        body=missing_metadata_body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )

    compound_metadata_body = wheel_page_with_requires_python(
        (
            "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl",
            ">=3.11,<3.12",
        ),
        (
            "coverage-7.15.1-cp312-cp312-manylinux_2_28_x86_64.whl",
            ">=3.12,<3.13",
        ),
        (
            "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl",
            ">=3.13,<3.14",
        ),
    )
    assert checker.simple_page_has_exact_pin(
        body=compound_metadata_body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_exact_pin_accepts_common_compatible_and_wildcard_specifiers() -> None:
    body = wheel_page_with_requires_python(
        (
            "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl",
            "~=3.11",
        ),
        (
            "coverage-7.15.1-cp312-cp312-manylinux_2_28_x86_64.whl",
            "==3.12.*",
        ),
        (
            "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl",
            "!=3.12.*",
        ),
    )

    assert checker.simple_page_has_exact_pin(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_compatible_release_minor_does_not_imply_patch_level_cap() -> None:
    assert checker._requires_python_allows_target(
        "~=3.11",
        target_python_tag="cp313",
    )
    assert not checker._requires_python_allows_target(
        "~=3.11.0",
        target_python_tag="cp313",
    )


def test_exact_pin_rejects_inclusive_requires_python_same_minor_upper_bound() -> None:
    body = wheel_page_with_requires_python(
        (
            "coverage-7.15.1-cp313-cp313-manylinux_2_28_x86_64.whl",
            "<=3.13",
        ),
    )

    assert not checker.simple_page_has_exact_pin(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.13"],
    )
    assert checker._requires_python_allows_target(
        "<=3.14",
        target_python_tag="cp313",
    )
    assert not checker._requires_python_allows_target(
        "<=3.12",
        target_python_tag="cp313",
    )
    assert not checker._requires_python_allows_target(
        "<=3.13.1",
        target_python_tag="cp313",
    )
    assert not checker._requires_python_allows_target(
        "<=3.13",
        target_python_tag="cp313",
    )


def test_requires_python_minor_target_rejects_patch_specific_constraints() -> None:
    assert not checker._requires_python_allows_target(
        "==3.11.0.*",
        target_python_tag="cp311",
    )
    assert not checker._requires_python_allows_target(
        "!=3.11.0.*",
        target_python_tag="cp311",
    )
    assert not checker._requires_python_allows_target(
        "<3.11.1",
        target_python_tag="cp311",
    )
    assert not checker._requires_python_allows_target(
        ">=3.11.1",
        target_python_tag="cp311",
    )


def test_exact_pin_parses_distribution_component_and_rejects_extra_hyphen() -> None:
    valid_legacy = wheel_page("Zope.Interface-7.2-py3-none-any.whl")
    malformed = wheel_page("pytest-xdist-3.8.0-py3-none-any.whl")

    assert checker.exact_pin_wheel_filenames(
        body=valid_legacy,
        normalized_project="zope-interface",
        expected_version="7.2",
    ) == ("zope.interface-7.2-py3-none-any.whl",)
    assert (
        checker.exact_pin_wheel_filenames(
            body=malformed,
            normalized_project="pytest-xdist",
            expected_version="3.8.0",
        )
        == ()
    )


def test_exact_pin_rejects_duplicate_decoded_filename_links() -> None:
    filename = "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl"
    body = wheel_page_with_requires_python(
        (filename, ">=4"),
        (filename, None),
    )

    assert (
        checker.exact_pin_wheel_filenames(
            body=body,
            normalized_project="coverage",
            expected_version="7.15.1",
        )
        == ()
    )
    assert not checker.simple_page_has_exact_pin(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11"],
    )


def test_exact_pin_rejects_external_absolute_or_scheme_relative_wheel_urls() -> None:
    filename = "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl"
    for href in (
        f"https://files.pythonhosted.org/packages/{filename}",
        f"//files.pythonhosted.org/packages/{filename}",
    ):
        body = f'<a href="{href}">wheel</a>'.encode()
        assert not checker.simple_page_has_exact_pin(
            body=body,
            normalized_project="coverage",
            expected_version="7.15.1",
            target_python_versions=["3.11"],
            allowed_netloc="packages.pulseplate.app",
        )

    same_host_body = (
        f'<a href="https://packages.pulseplate.app/root/pulseplate/+f/{filename}">wheel</a>'
    ).encode()
    assert checker.simple_page_has_exact_pin(
        body=same_host_body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11"],
        allowed_netloc="packages.pulseplate.app",
    )


def test_exact_pin_rejects_absolute_scheme_without_authority() -> None:
    filename = "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl"
    body = f'<a href="https:///path/{filename}">wheel</a>'.encode()

    assert not checker.simple_page_has_exact_pin(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11"],
        allowed_netloc="packages.pulseplate.app",
    )


def test_malformed_anchor_poisoning_cannot_be_bypassed_by_later_valid_link() -> None:
    filename = "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl"
    body = (
        f'<a href="../../+f/one/{filename}" '
        f'href="../../+f/two/{filename}">malformed</a>'
        f'<a href="../../+f/three/{filename}">valid</a>'
    ).encode()

    assert (
        checker.exact_pin_wheel_filenames(
            body=body,
            normalized_project="coverage",
            expected_version="7.15.1",
        )
        == ()
    )
    assert not checker.simple_page_has_exact_pin(
        body=body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11"],
    )


def test_exact_pin_rejects_duplicate_anchor_identity_or_python_metadata() -> None:
    filename = "coverage-7.15.1-cp311-cp311-manylinux_2_28_x86_64.whl"
    duplicate_href_body = (
        f'<a href="../../+f/abc/{filename}" ' f'href="../../+f/other/{filename}">wheel</a>'
    ).encode()
    assert (
        checker.exact_pin_wheel_filenames(
            body=duplicate_href_body,
            normalized_project="coverage",
            expected_version="7.15.1",
        )
        == ()
    )

    duplicate_requires_python_body = (
        f'<a href="../../+f/abc/{filename}" '
        'data-requires-python="&gt;=3.11" '
        'data-requires-python="&lt;3.12">wheel</a>'
    ).encode()
    assert (
        checker.exact_pin_wheel_filenames(
            body=duplicate_requires_python_body,
            normalized_project="coverage",
            expected_version="7.15.1",
        )
        == ()
    )
    assert not checker.simple_page_has_exact_pin(
        body=duplicate_requires_python_body,
        normalized_project="coverage",
        expected_version="7.15.1",
        target_python_versions=["3.11"],
    )


@pytest.mark.parametrize(
    "filename",
    (
        "cryptography-48.0.1-cp39-abi3-manylinux_2_28_x86_64.whl",
        "cryptography-48.0.1-py3-none-any.whl",
    ),
)
def test_exact_pin_preserves_abi3_and_universal_wheel_coverage(filename: str) -> None:
    assert checker.simple_page_has_exact_pin(
        body=wheel_page(filename),
        normalized_project="cryptography",
        expected_version="48.0.1",
        target_python_versions=["3.11", "3.12", "3.13"],
    )


def test_parse_exact_pins_normalizes_names(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(
        "\n".join(
            [
                "aiosqlite==0.22.1",
                "pydantic_core==2.41.5 ; python_version >= '3.13'",
                "requests[security]==2.33.0  # comment",
                "cryptography==48.0.1 --hash=sha256:abc123 --hash sha256:def456",
            ]
        ),
        encoding="utf-8",
    )

    assert checker.parse_exact_pins([requirements]) == {
        "aiosqlite": "0.22.1",
        "pydantic-core": "2.41.5",
        "requests": "2.33.0",
        "cryptography": "48.0.1",
    }


def test_parse_exact_pins_rejects_extra_specifiers(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("aiosqlite==0.22.1,<1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non_exact_pin"):
        checker.parse_exact_pins([requirements])


def test_parse_exact_pins_rejects_conflicting_repeated_pins(tmp_path: Path) -> None:
    first = tmp_path / "requirements.txt"
    second = tmp_path / "requirements-test.txt"
    first.write_text("requests==2.33.0\n", encoding="utf-8")
    second.write_text("requests==2.33.1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="conflicting_exact_pins: requests"):
        checker.parse_exact_pins([first, second])


def test_parse_exact_pins_scoped_projects_rejects_selected_conflicts(tmp_path: Path) -> None:
    first = tmp_path / "requirements.txt"
    second = tmp_path / "requirements-dev.txt"
    first.write_text("mypy==2.2.0\n", encoding="utf-8")
    second.write_text("mypy==2.1.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="conflicting_exact_pins: mypy"):
        checker.parse_exact_pins_for_projects([first, second], projects=["mypy"])


def test_parse_exact_pins_scoped_projects_ignores_unselected_conflicts(tmp_path: Path) -> None:
    first = tmp_path / "requirements.txt"
    second = tmp_path / "requirements-dev.txt"
    first.write_text("chardet==5.2.0\nmypy==2.2.0\n", encoding="utf-8")
    second.write_text("chardet==7.4.0.post1\nmypy==2.2.0\n", encoding="utf-8")

    assert checker.parse_exact_pins_for_projects([first, second], projects=["mypy"]) == {
        "mypy": "2.2.0"
    }


def test_main_default_projects_exclude_large_pydantic_core_probe(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_projects: list[str] = []

    def fake_check_health(
        *,
        index_url: str,
        projects: list[str],
        pins: dict[str, str],
        expected_host: str,
        allow_dev_host: bool,
        timeout_seconds: float,
        max_bytes: int,
        retries: int,
        netrc_file: Path | None = None,
        target_python_versions: list[str] | None = None,
    ) -> checker.HealthSummary:
        captured_projects.extend(projects)
        assert target_python_versions == []
        return checker.HealthSummary(
            ok=True,
            index_url=APPROVED_INDEX,
            host="packages.pulseplate.app",
            results=(),
        )

    def fake_parse_exact_pins_for_projects(
        requirements_files: list[Path],
        projects: list[str],
    ) -> dict[str, str]:
        assert requirements_files == [
            Path("requirements.txt"),
            Path("requirements-ci-lite.txt"),
            Path("requirements-test.txt"),
            Path("requirements-dev.txt"),
        ]
        assert projects == [
            "aiosqlite",
            "cryptography",
            "requests",
            "pytest-xdist",
            "hypothesis",
            "mypy",
            "ruff",
            "librt",
            "ast-serialize",
            "pgvector",
        ]
        return {
            "aiosqlite": "0.22.1",
            "cryptography": "48.0.1",
            "requests": "2.33.0",
            "pytest-xdist": "3.8.0",
            "hypothesis": "6.156.6",
            "mypy": "2.2.0",
            "ruff": "0.15.21",
            "librt": "0.13.0",
            "ast-serialize": "0.6.0",
            "pgvector": "0.4.2",
            "pydantic-core": "2.41.5",
        }

    monkeypatch.setattr(
        checker, "parse_exact_pins_for_projects", fake_parse_exact_pins_for_projects
    )
    monkeypatch.setattr(checker, "check_health", fake_check_health)

    assert checker.main(["--index-url", APPROVED_INDEX]) == 0
    assert captured_projects == [
        "aiosqlite",
        "cryptography",
        "requests",
        "pytest-xdist",
        "hypothesis",
        "mypy",
        "ruff",
        "librt",
        "ast-serialize",
        "pgvector",
    ]
    assert "pydantic-core" not in captured_projects
    assert "private_python_proxy_health ok=true" in capsys.readouterr().out


def test_main_failure_path_redacts_credentialed_index_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = checker.main(
        [
            "--index-url",
            "https://root:secret@packages.pulseplate.app/root/pulseplate/+simple/",  # pragma: allowlist secret
        ]
    )

    stderr = capsys.readouterr().err
    assert result == 1
    assert "credentialed_index_url" in stderr
    assert "root:secret" not in stderr


def test_probe_project_passes_when_exact_pin_is_present(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        assert url == f"{APPROVED_INDEX}aiosqlite/"
        assert timeout_seconds == 1
        assert max_bytes == 1000
        assert authorization_header is None
        return 200, simple_page("aiosqlite", "0.22.1")

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="aiosqlite",
        expected_version="0.22.1",
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
    )

    assert result.ok is True
    assert result.reason == "ok"


def test_probe_project_requires_exact_pinned_wheel_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        return 200, source_page("aiosqlite", "0.22.1")

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="aiosqlite",
        expected_version="0.22.1",
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
    )

    assert result.ok is False
    assert result.reason == "mirror_lag_exact_pin_missing"


def test_probe_project_requires_compatible_exact_pinned_wheel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        return 200, wheel_page("cryptography-48.0.1-cp311-abi3-win_amd64.whl")

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="cryptography",
        expected_version="48.0.1",
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
        target_python_versions=["3.11", "3.12", "3.13"],
    )

    assert result.ok is False
    assert result.reason == "mirror_lag_compatible_wheel_missing"
    assert "cp311,cp312,cp313" in result.detail


def test_probe_project_accepts_truncated_page_when_exact_pin_is_already_seen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = simple_page("pydantic_core", "2.41.5") + b"x" * 10

    def fake_fetch_project_page(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        return 200, body

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch_project_page)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="pydantic-core",
        expected_version="2.41.5",
        timeout_seconds=1,
        max_bytes=len(body) - 1,
        retries=0,
    )

    assert result.ok is True
    assert result.reason == "ok"


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (401, "auth_or_access_denied"),
        (403, "auth_or_access_denied"),
        (404, "project_page_not_found"),
        (521, "origin_unhealthy"),
    ],
)
def test_probe_project_classifies_http_errors(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    reason: str,
) -> None:
    def fake_fetch(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        raise HTTPError(url, status, "error", hdrs=None, fp=None)

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="aiosqlite",
        expected_version="0.22.1",
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
    )

    assert result.ok is False
    assert result.reason == reason
    assert result.status == status


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (b"", "empty_project_page"),
        (b"<html><body>no links here</body></html>", "simple_page_malformed"),
        (simple_page("aiosqlite", "0.22.0"), "mirror_lag_exact_pin_missing"),
        (b"<html>Cloudflare Error 521 web server is down</html>", "origin_unhealthy"),
    ],
)
def test_probe_project_classifies_unhealthy_or_non_parity_pages(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
    reason: str,
) -> None:
    def fake_fetch_project_page(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        return 200, body

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch_project_page)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="aiosqlite",
        expected_version="0.22.1",
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
    )

    assert result.ok is False
    assert result.reason == reason


def test_probe_project_classifies_timeouts_after_bounded_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    def fake_fetch(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        nonlocal attempts
        attempts += 1
        raise socket.timeout("timed out")

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch)

    result = checker.probe_project(
        index_url=APPROVED_INDEX,
        project="aiosqlite",
        expected_version="0.22.1",
        timeout_seconds=1,
        max_bytes=1000,
        retries=1,
    )

    assert attempts == 2
    assert result.ok is False
    assert result.reason == "tls_or_connect_timeout"


def test_check_health_fails_when_project_missing_from_requirements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_project_page(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        return 200, simple_page("requests", "2.33.0")

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch_project_page)

    summary = checker.check_health(
        index_url=APPROVED_INDEX,
        projects=["requests"],
        pins={},
        expected_host="packages.pulseplate.app",
        allow_dev_host=False,
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
    )

    assert summary.ok is False
    assert summary.results[0].reason == "missing_exact_pin_in_requirements"


def test_check_health_uses_netrc_for_authenticated_project_pages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text(
        "machine packages.pulseplate.app\n  login pulseplate-ci\n  password read-only-token\n",  # pragma: allowlist secret
        encoding="utf-8",
    )
    seen_headers: list[str | None] = []

    def fake_fetch(
        url: str,
        *,
        timeout_seconds: float,
        max_bytes: int,
        authorization_header: str | None = None,
    ) -> tuple[int, bytes]:
        seen_headers.append(authorization_header)
        return 200, simple_page("aiosqlite", "0.22.1")

    monkeypatch.setattr(checker, "fetch_project_page", fake_fetch)

    summary = checker.check_health(
        index_url=APPROVED_INDEX,
        projects=["aiosqlite"],
        pins={"aiosqlite": "0.22.1"},
        expected_host="packages.pulseplate.app",
        allow_dev_host=False,
        timeout_seconds=1,
        max_bytes=1000,
        retries=0,
        netrc_file=netrc_file,
    )

    assert summary.ok is True
    assert seen_headers == ["Basic cHVsc2VwbGF0ZS1jaTpyZWFkLW9ubHktdG9rZW4="]


def test_netrc_rejects_root_devpi_credentials(tmp_path: Path) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text(
        "machine packages.pulseplate.app\n  login root\n  password not-used\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="root_devpi_credentials"):
        checker.basic_auth_from_netrc("packages.pulseplate.app", netrc_file=netrc_file)


def test_netrc_requires_exact_machine_entry(tmp_path: Path) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text(
        "default login pulseplate-ci password default-token\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    assert checker.basic_auth_from_netrc("packages.pulseplate.app", netrc_file=netrc_file) is None


def test_netrc_parse_errors_do_not_echo_raw_parser_text(tmp_path: Path) -> None:
    netrc_file = tmp_path / ".netrc"
    netrc_file.write_text(
        "machine packages.pulseplate.app login pulseplate-ci password leaked-token extra\n",  # pragma: allowlist secret
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc_info:
        checker.basic_auth_from_netrc("packages.pulseplate.app", netrc_file=netrc_file)

    message = str(exc_info.value)
    assert "netrc_error" in message
    assert "NetrcParseError" in message
    assert "leaked-token" not in message
    assert "extra" not in message


def test_diagnostics_redact_inline_credentials() -> None:
    redacted = checker.redact_text(
        "failed https://root:secret@packages.pulseplate.app/root/pulseplate/+simple/"  # pragma: allowlist secret
        " Authorization=secret-token Authorization: Bearer abc123 token: abc123"  # pragma: allowlist secret
    )

    assert "root:secret" not in redacted
    assert "secret-token" not in redacted
    assert "Bearer" not in redacted
    assert "abc123" not in redacted
    assert "packages.pulseplate.app" in redacted

"""Regression tests for the React Router RSC suppression premise guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import check_react_router_rsc_premise as guard

REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_frontend(
    tmp_path: Path,
    *,
    package_json: object | None = None,
    package_lock: object | None = None,
) -> Path:
    frontend_root = tmp_path / "frontend"
    frontend_root.mkdir()
    package_value = (
        {"dependencies": {}, "devDependencies": {}, "optionalDependencies": {}, "scripts": {}}
        if package_json is None
        else package_json
    )
    (frontend_root / "package.json").write_text(
        json.dumps(package_value),
        encoding="utf-8",
    )
    lock_value = {} if package_lock is None else package_lock
    (frontend_root / "package-lock.json").write_text(
        json.dumps(lock_value),
        encoding="utf-8",
    )
    return frontend_root


def _write_source(frontend_root: Path, relative_path: str, text: str) -> Path:
    source_path = frontend_root / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(text, encoding="utf-8")
    return source_path


def test_repository_frontend_keeps_rsc_premise() -> None:
    assert guard.scan_repository(REPO_ROOT / "frontend") == []


@pytest.mark.parametrize(
    ("package_json", "package_lock", "expected"),
    [
        (
            {"dependencies": {"@vitejs/plugin-rsc": "0.4.0"}},
            None,
            "package.json:dependencies.@vitejs/plugin-rsc:@vitejs/plugin-rsc",
        ),
        (
            {"devDependencies": {"react-server-dom-webpack": "19.1.0"}},
            None,
            "package.json:devDependencies.react-server-dom-webpack:react-server-dom-*",
        ),
        (
            {"optionalDependencies": {"rsc-runtime": "npm:react-server-dom-webpack@19.1.0"}},
            None,
            "package.json:optionalDependencies.rsc-runtime:react-server-dom-*",
        ),
        (
            {},
            {
                "packages": {
                    "node_modules/rsc-bridge": {
                        "resolved": (
                            "https://registry.npmjs.org/react-server-dom-webpack/"
                            "-/react-server-dom-webpack-19.1.0.tgz"
                        )
                    }
                }
            },
            ("package-lock.json:packages.node_modules/rsc-bridge.resolved:" "react-server-dom-*"),
        ),
        (
            {},
            {
                "packages": {
                    "node_modules/rsc-bridge": {
                        "dependencies": {"rsc-runtime": "npm:react-server-dom-webpack@19.1.0"}
                    }
                }
            },
            (
                "package-lock.json:packages.node_modules/rsc-bridge.dependencies."
                "rsc-runtime:react-server-dom-*"
            ),
        ),
    ],
)
def test_package_metadata_markers_fail_closed(
    tmp_path: Path,
    package_json: object,
    package_lock: object | None,
    expected: str,
) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json=package_json,
        package_lock=package_lock,
    )

    assert expected in guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    ("relative_path", "source_text", "expected"),
    [
        (
            "src/server.ts",
            'import { unstable_matchRSCServerRequest } from "react-router-dom";\n',
            "src/server.ts:unstable_matchRSCServerRequest",
        ),
        (
            "src/server.tsx",
            'import { unstable_routeRSCServerRequest } from "react-router";\n',
            "src/server.tsx:unstable_routeRSCServerRequest",
        ),
        (
            "src/server.mts",
            'import handler from "react-router/internal/react-server";\n',
            "src/server.mts:react-router/internal/react-server",
        ),
        (
            "src/plugin.cts",
            'import plugin from "@vitejs/plugin-rsc";\n',
            "src/plugin.cts:@vitejs/plugin-rsc",
        ),
        (
            "src/runtime.mjs",
            'import runtime from "react-server-dom-webpack";\n',
            "src/runtime.mjs:react-server-dom-",
        ),
    ],
)
def test_existing_runtime_markers_fail_closed(
    tmp_path: Path,
    relative_path: str,
    source_text: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, relative_path, source_text)

    assert expected in guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    "source_text",
    (
        'import * as router from "react-router";\n'
        'router["unstable_" + "routeRSCServerRequest"];\n',
        "import * as rr from 'react-router';\n" 'rr["unstable_" + "matchRSCServerRequest"];\n',
        'import/* owner */*/* runtime */as $router\nfrom\n"react-router";\n',
    ),
)
def test_react_router_namespace_import_is_rejected_before_computed_export_access(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/computed.mjs", source_text)

    assert guard.scan_repository(frontend_root) == [
        "src/computed.mjs:react-router namespace import"
    ]


@pytest.mark.parametrize(
    "source_text",
    (
        '// import * as router from "react-router";\n',
        '/* import * as router from "react-router"; */\n',
        'const example = "import * as router from \\"react-router\\";";\n',
        'const example = `import * as router from "react-router";`;\n',
    ),
)
def test_namespace_import_like_comments_and_string_literals_are_ignored(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/example.ts", source_text)

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize(
    "source_text",
    (
        'import * as router from "react-router-dom";\n',
        'import type * as router from "react-router";\n',
        'import { createBrowserRouter } from "react-router";\n',
        'import router from "react-router";\n',
        'import "react-router";\n',
        'const router = import("react-router");\n',
        'const router = require("react-router");\n',
        'export * as router from "react-router";\n',
    ),
)
def test_safe_or_out_of_scope_react_router_import_shapes_remain_allowed(
    tmp_path: Path,
    source_text: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/safe.ts", source_text)

    assert guard.scan_repository(frontend_root) == []


@pytest.mark.parametrize("quote", ["'", '"', "`"])
def test_exact_react_server_condition_is_found_in_imported_source(
    tmp_path: Path,
    quote: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "config/rsc-conditions.ts",
        f"export const conditions = [{quote}react-server{quote}];\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "config/rsc-conditions.ts:react-server condition"
    ]


@pytest.mark.parametrize(
    "condition_literal",
    ("--conditions=react-server", "react-server:custom"),
)
def test_bounded_react_server_condition_is_found_inside_source_literal(
    tmp_path: Path,
    condition_literal: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "config/rsc-conditions.ts",
        f'export const condition = "{condition_literal}";\n',
    )

    assert guard.scan_repository(frontend_root) == [
        "config/rsc-conditions.ts:react-server condition"
    ]


@pytest.mark.parametrize(
    "near_match",
    ("pre-react-server", "react-serverish"),
)
def test_react_server_condition_near_matches_inside_source_literals_are_ignored(
    tmp_path: Path,
    near_match: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "config/rsc-conditions.ts",
        f'export const condition = "{near_match}";\n',
    )

    assert guard.scan_repository(frontend_root) == []


def test_all_supported_source_suffixes_are_scanned(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    for suffix in sorted(guard.SOURCE_SUFFIXES):
        _write_source(
            frontend_root,
            f"src/condition{suffix}",
            'export const condition = "react-server";\n',
        )

    assert guard.scan_repository(frontend_root) == [
        f"src/condition{suffix}:react-server condition" for suffix in sorted(guard.SOURCE_SUFFIXES)
    ]


def test_comments_near_misses_escapes_and_unsupported_files_are_ignored(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/clean.ts",
        "\n".join(
            (
                "// unstable_routeRSCServerRequest and 'react-server'",
                "/* @vitejs/plugin-rsc and react-server-dom-webpack */",
                'const suffix = "react-serverish";',
                'const prefix = "pre-react-server";',
                'const caseVariant = "React-Server";',
                'const escaped = "react\\-server";',
            )
        ),
    )
    _write_source(
        frontend_root,
        "src/ignored.txt",
        'const condition = "react-server";\n',
    )

    assert guard.scan_repository(frontend_root) == []


def test_javascript_regex_literals_do_not_confuse_quote_scanning(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/regex.ts",
        "\n".join(
            (
                r"""const threshold = /(?<!['"`/])\b18\.5\b(?!['"`])/;""",
                r"""const normalized = value.replace(/\\/g, "/");""",
                'export const condition = "react-server";',
            )
        ),
    )

    assert guard.scan_repository(frontend_root) == ["src/regex.ts:react-server condition"]


def test_jsx_text_apostrophes_do_not_start_string_literals(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/Message.tsx",
        "<p>Users' pages aren't here. Let's go back.</p>\n",
    )

    assert guard.scan_repository(frontend_root) == []


def test_bounded_regex_context_preserves_prefix_characters_and_keywords() -> None:
    regex_prefixes = (
        "",
        *sorted(guard._REGEX_PREFIX_CHARACTERS),
        *guard._REGEX_PREFIX_KEYWORDS,
    )
    for prefix in regex_prefixes:
        visible = guard._VisibleCharacters()
        visible.extend(prefix)
        visible.extend(" " * 10_000)
        assert guard._starts_regex_literal(visible), prefix

    for prefix in ("identifier", "returnValue"):
        visible = guard._VisibleCharacters()
        visible.extend(prefix)
        visible.extend(" " * 10_000)
        assert not guard._starts_regex_literal(visible), prefix


def test_long_slash_and_apostrophe_prefixes_use_bounded_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_prefix_lengths: list[int] = []
    original = guard._ends_with_regex_prefix_keyword

    def record_prefix_length(prefix: str) -> bool:
        observed_prefix_lengths.append(len(prefix))
        return original(prefix)

    monkeypatch.setattr(guard, "_ends_with_regex_prefix_keyword", record_prefix_length)
    long_identifier = "x" * 100_000
    source = "\n".join(
        (
            f"{long_identifier} / divisor;",
            f"<p>{long_identifier}' pages</p>",
            "export const condition = 'react-server';",
        )
    )

    literals, _visible = guard._source_literals_and_visible_text(source, label="long-prefix.tsx")

    assert "react-server" in literals
    assert observed_prefix_lengths
    assert max(observed_prefix_lengths) <= guard._REGEX_PREFIX_CONTEXT_LIMIT


def test_script_condition_requires_exact_token_boundaries(tmp_path: Path) -> None:
    frontend_root = _write_frontend(
        tmp_path,
        package_json={
            "scripts": {
                "build": "NODE_OPTIONS=--conditions=react-server vite build",
                "near": "echo react-serverish pre-react-server",
            }
        },
    )

    assert guard.scan_repository(frontend_root) == [
        "package.json:scripts.build:react-server condition"
    ]


def test_root_outputs_are_pruned_but_nested_build_and_dist_are_scanned(
    tmp_path: Path,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    for root_output in ("build", "dist"):
        _write_source(
            frontend_root,
            f"{root_output}/ignored.ts",
            'export const condition = "react-server";\n',
        )
        _write_source(
            frontend_root,
            f"src/{root_output}/checked.ts",
            'export const condition = "react-server";\n',
        )

    assert guard.scan_repository(frontend_root) == [
        "src/build/checked.ts:react-server condition",
        "src/dist/checked.ts:react-server condition",
    ]


def test_global_generated_directories_are_pruned_at_every_depth(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    for relative_directory in (
        "node_modules",
        "src/node_modules",
        ".pytest_cache",
        "src/.ruff_cache",
    ):
        _write_source(
            frontend_root,
            f"{relative_directory}/ignored.ts",
            'export const condition = "react-server";\n',
        )

    assert guard.scan_repository(frontend_root) == []


def test_violations_are_sorted_and_deduplicated(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(
        frontend_root,
        "src/z.ts",
        "unstable_routeRSCServerRequest(); unstable_routeRSCServerRequest();\n",
    )
    _write_source(
        frontend_root,
        "src/a.ts",
        "unstable_matchRSCServerRequest();\n",
    )

    assert guard.scan_repository(frontend_root) == [
        "src/a.ts:unstable_matchRSCServerRequest",
        "src/z.ts:unstable_routeRSCServerRequest",
    ]


@pytest.mark.parametrize(
    ("filename", "payload", "expected"),
    [
        ("package.json", "{", "invalid JSON in package.json"),
        ("package.json", "[]", "expected a JSON object in package.json"),
        ("package.json", '{"dependencies": []}', "package.json:dependencies"),
        (
            "package.json",
            '{"dependencies": {"react-router": 7}}',
            "package.json:dependencies.react-router",
        ),
        ("package.json", '{"scripts": []}', "package.json:scripts"),
        ("package.json", '{"scripts": {"build": 1}}', "package.json:scripts.build"),
        ("package-lock.json", "[]", "expected a JSON object in package-lock.json"),
        (
            "package-lock.json",
            '{"packages": []}',
            "package-lock.json:packages",
        ),
    ],
)
def test_malformed_metadata_fails_closed(
    tmp_path: Path,
    filename: str,
    payload: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    (frontend_root / filename).write_text(payload, encoding="utf-8")

    with pytest.raises(guard.PremiseScanError, match=expected):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize("filename", ["package.json", "package-lock.json"])
def test_missing_package_metadata_fails_closed(tmp_path: Path, filename: str) -> None:
    frontend_root = _write_frontend(tmp_path)
    (frontend_root / filename).unlink()

    with pytest.raises(guard.PremiseScanError, match="required metadata file is missing"):
        guard.scan_repository(frontend_root)


def test_unreadable_candidate_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    package_path = frontend_root / "package.json"
    original_read_text = Path.read_text

    def deny_package_read(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        if path == package_path:
            raise PermissionError("test denial")
        return original_read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", deny_package_read)

    with pytest.raises(guard.PremiseScanError, match="unable to read package.json"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize("target_outside_root", [False, True])
def test_candidate_file_symlinks_fail_closed(
    tmp_path: Path,
    target_outside_root: bool,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    target_parent = tmp_path if target_outside_root else frontend_root
    target = _write_source(
        target_parent,
        "target.ts",
        'export const condition = "react-server";\n',
    )
    linked_source = frontend_root / "src" / "linked.ts"
    linked_source.parent.mkdir()
    linked_source.symlink_to(target)

    with pytest.raises(guard.PremiseScanError, match="candidate path must not be a symlink"):
        guard.scan_repository(frontend_root)


def test_directory_symlink_fails_closed_without_following_target(tmp_path: Path) -> None:
    frontend_root = _write_frontend(tmp_path)
    external_directory = tmp_path / "external"
    external_directory.mkdir()
    _write_source(
        external_directory,
        "marker.ts",
        'export const condition = "react-server";\n',
    )
    (frontend_root / "linked").symlink_to(external_directory, target_is_directory=True)

    with pytest.raises(guard.PremiseScanError, match="directory must not be a symlink"):
        guard.scan_repository(frontend_root)


@pytest.mark.parametrize(
    ("source_text", "expected"),
    [
        ('const value = "react-server', "unterminated string literal"),
        ("/* react-server", "unterminated block comment"),
    ],
)
def test_incomplete_source_syntax_fails_closed(
    tmp_path: Path,
    source_text: str,
    expected: str,
) -> None:
    frontend_root = _write_frontend(tmp_path)
    _write_source(frontend_root, "src/incomplete.ts", source_text)

    with pytest.raises(guard.PremiseScanError, match=expected):
        guard.scan_repository(frontend_root)


def test_traversal_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frontend_root = _write_frontend(tmp_path)

    def fail_walk(
        *args: object,
        onerror: object,
        **kwargs: object,
    ) -> list[tuple[str, list[str], list[str]]]:
        assert callable(onerror)
        onerror(PermissionError("test traversal denial"))
        return []

    monkeypatch.setattr(guard.os, "walk", fail_walk)

    with pytest.raises(guard.PremiseScanError, match="unable to traverse frontend root"):
        guard.scan_repository(frontend_root)


def test_cli_reports_clean_findings_and_incomplete_scan(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    frontend_root = _write_frontend(tmp_path)

    assert guard.main(["--frontend-root", str(frontend_root)]) == 0
    assert capsys.readouterr().out == "PASS: React Router RSC suppression premise holds\n"

    _write_source(
        frontend_root,
        "src/marker.ts",
        'export const condition = "react-server";\n',
    )
    assert guard.main(["--frontend-root", str(frontend_root)]) == 1
    assert capsys.readouterr().out == (
        "ERROR: React Router RSC suppression premise violated:\n"
        "- src/marker.ts:react-server condition\n"
    )

    assert guard.main(["--frontend-root", str(tmp_path / "missing")]) == 1
    assert "premise scan was incomplete" in capsys.readouterr().out


def test_cli_rejects_unknown_arguments() -> None:
    with pytest.raises(SystemExit) as exc_info:
        guard.main(["--unknown"])

    assert exc_info.value.code == 2

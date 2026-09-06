"""Focused tests for exact bounded role-context materialization."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.orchestration import context_bundle


def _write(repo: Path, relative: str, content: str) -> Path:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")
    return path


def _snapshot(repo: Path, path: str) -> tuple[context_bundle.ContextIOMetrics, object]:
    metrics = context_bundle.ContextIOMetrics()
    snapshot = context_bundle.read_repo_source(repo, path, metrics=metrics)
    return metrics, snapshot


def _materialize(
    repo: Path,
    paths: list[str],
    *,
    initial: dict[str, context_bundle.SourceSnapshot] | None = None,
    bracket: list[str] | None = None,
    packet: str | None = None,
) -> tuple[dict[str, object], context_bundle.ContextIOMetrics]:
    metrics = context_bundle.ContextIOMetrics()
    result = context_bundle.materialize_context_bundle(
        repo,
        occurrence=2,
        ordered_source_paths=paths,
        bracket_paths=bracket or paths,
        initial_snapshots=initial,
        dynamic_packet_path=packet,
        metrics=metrics,
    )
    return result, metrics


def test_full_exact_text_preserves_content_beyond_line_200_and_character_500(
    tmp_path: Path,
) -> None:
    content = "".join(f"line-{index:03d}: {'x' * 32}\n" for index in range(240))
    _write(tmp_path, ".cursor/agents/role.md", content)

    result, metrics = _materialize(tmp_path, [".cursor/agents/role.md"])

    assert result["complete"] is True
    sources = result["sources"]
    assert isinstance(sources, list)
    assert sources == [{"path": ".cursor/agents/role.md", "content": content}]
    assert len(content) > 500
    assert "line-200" in sources[0]["content"]
    assert metrics.source_opens == 1
    assert metrics.freshness_opens == 1


def test_first_occurrence_order_deduplicates_without_reordering(tmp_path: Path) -> None:
    _write(tmp_path, "a.md", "alpha\n")
    _write(tmp_path, "b.md", "beta\n")

    result, _metrics = _materialize(tmp_path, ["b.md", "a.md", "b.md"])

    assert [row["path"] for row in result["sources"]] == ["b.md", "a.md"]


@pytest.mark.parametrize(
    "path",
    ["/tmp/outside.md", "../outside.md", "./a.md", "a//b.md", "a\\b.md", "a\x00b.md"],
)
def test_noncanonical_paths_fail_closed(tmp_path: Path, path: str) -> None:
    with pytest.raises(context_bundle.ContextBundleError, match="INVALID_SOURCE_PATH"):
        _materialize(tmp_path, [path])


def test_root_dot_alias_fails_structured_before_source_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[str] = []

    def unexpected_read(
        _repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        del metrics, freshness, limit
        attempted.append(raw_path)
        raise AssertionError("root alias must fail before acquisition")

    monkeypatch.setattr(context_bundle, "read_repo_source", unexpected_read)

    for operation in (
        context_bundle.canonical_repo_path,
        context_bundle.validate_static_source_path,
    ):
        with pytest.raises(
            context_bundle.ContextBundleError,
            match=r"INVALID_SOURCE_PATH: \.",
        ):
            operation(".")
    with pytest.raises(
        context_bundle.ContextBundleError,
        match=r"INVALID_SOURCE_PATH: \.",
    ):
        _materialize(tmp_path, ["."])

    assert attempted == []


@pytest.mark.parametrize("pattern", ["docs/*.md", "docs/?a.md", "docs/[ab].md"])
def test_patterns_return_explicit_manual_incomplete_without_partial_content(
    tmp_path: Path,
    pattern: str,
) -> None:
    result, _metrics = _materialize(tmp_path, [pattern])

    assert result == {
        "schema_version": context_bundle.DELIVERY_SCHEMA_VERSION,
        "complete": False,
        "role_context_order": 2,
        "manual_loading_required": True,
        "reason": "UNSUPPORTED_SOURCE_PATTERN",
        "path": pattern,
    }


def test_directory_returns_explicit_manual_incomplete(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()

    result, _metrics = _materialize(tmp_path, ["docs"])

    assert result["complete"] is False
    assert result["reason"] == "UNSUPPORTED_SOURCE_DIRECTORY"
    assert "sources" not in result


def test_symlink_and_hardlink_sources_fail_closed(tmp_path: Path) -> None:
    source = _write(tmp_path, "source.md", "trusted\n")
    (tmp_path / "alias.md").symlink_to(source)
    os.link(source, tmp_path / "hardlink.md")

    with pytest.raises(context_bundle.ContextBundleError, match="UNSAFE_SOURCE_LINK"):
        _materialize(tmp_path, ["alias.md"])
    with pytest.raises(context_bundle.ContextBundleError, match="UNSAFE_SOURCE_TYPE"):
        _materialize(tmp_path, ["source.md"])


def test_symlinked_parent_component_fails_closed(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    _write(tmp_path, "real/context.md", "trusted\n")
    (tmp_path / "alias").symlink_to(real, target_is_directory=True)

    with pytest.raises(context_bundle.ContextBundleError, match="UNSAFE_SOURCE_READ"):
        _materialize(tmp_path, ["alias/context.md"])


def test_missing_non_utf8_and_oversized_sources_block(tmp_path: Path) -> None:
    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_MISSING"):
        _materialize(tmp_path, ["missing.md"])

    (tmp_path / "binary.md").write_bytes(b"\xff")
    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_NOT_UTF8"):
        _materialize(tmp_path, ["binary.md"])

    (tmp_path / "large.md").write_bytes(b"x" * (context_bundle.MAX_SOURCE_BYTES + 1))
    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_TOO_LARGE"):
        _materialize(tmp_path, ["large.md"])


def test_total_source_and_source_count_bounds_are_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "a.md", "aaaa")
    _write(tmp_path, "b.md", "bbbb")
    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 7)
    with pytest.raises(
        context_bundle.ContextBundleError,
        match="TOTAL_SOURCE_BYTES_EXCEEDED",
    ):
        _materialize(tmp_path, ["a.md", "b.md"])

    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 100)
    monkeypatch.setattr(context_bundle, "MAX_SOURCES", 1)
    with pytest.raises(context_bundle.ContextBundleError, match="TOO_MANY_SOURCES"):
        _materialize(tmp_path, ["a.md", "b.md"])


def test_total_byte_budget_stops_before_later_source_reads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("a.md", "b.md", "c.md"):
        _write(tmp_path, name, "four")
    real_read = context_bundle.read_repo_source
    attempted: list[str] = []

    def observed_read(
        repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        attempted.append(raw_path)
        return real_read(
            repo_root,
            raw_path,
            metrics=metrics,
            freshness=freshness,
            limit=limit,
        )

    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 7)
    monkeypatch.setattr(context_bundle, "read_repo_source", observed_read)
    metrics = context_bundle.ContextIOMetrics()

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="TOTAL_SOURCE_BYTES_EXCEEDED",
    ):
        context_bundle.capture_sources(
            tmp_path,
            ["a.md", "b.md", "c.md"],
            metrics=metrics,
        )

    assert attempted == ["a.md", "b.md"]
    assert metrics.source_bytes_read == 4


def test_existing_snapshots_consume_total_budget_before_new_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "a.md", "four")
    _write(tmp_path, "b.md", "four")
    _write(tmp_path, "c.md", "four")
    seed_metrics = context_bundle.ContextIOMetrics()
    _ordered, existing = context_bundle.capture_sources(
        tmp_path,
        ["a.md", "b.md"],
        metrics=seed_metrics,
    )
    attempted: list[str] = []

    def unexpected_read(
        _repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        del metrics, freshness, limit
        attempted.append(raw_path)
        raise AssertionError("no later source read is allowed")

    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 7)
    monkeypatch.setattr(context_bundle, "read_repo_source", unexpected_read)

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="TOTAL_SOURCE_BYTES_EXCEEDED",
    ):
        context_bundle.capture_sources(
            tmp_path,
            ["a.md", "b.md", "c.md"],
            metrics=context_bundle.ContextIOMetrics(),
            existing=existing,
        )

    assert attempted == []


def test_omitted_existing_bracket_snapshot_limits_new_source_before_content_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "bracket.md", "four")
    _write(tmp_path, "selected.md", "next")
    seed_metrics = context_bundle.ContextIOMetrics()
    bracket = context_bundle.read_repo_source(
        tmp_path,
        "bracket.md",
        metrics=seed_metrics,
    )
    real_read = context_bundle.read_repo_source
    attempted: list[tuple[str, int]] = []

    def observed_read(
        repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        attempted.append((raw_path, limit))
        return real_read(
            repo_root,
            raw_path,
            metrics=metrics,
            freshness=freshness,
            limit=limit,
        )

    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 7)
    monkeypatch.setattr(context_bundle, "read_repo_source", observed_read)
    metrics = context_bundle.ContextIOMetrics()

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="TOTAL_SOURCE_BYTES_EXCEEDED",
    ):
        context_bundle.capture_sources(
            tmp_path,
            ["selected.md"],
            metrics=metrics,
            existing={"bracket.md": bracket},
        )

    assert attempted == [("selected.md", 3)]
    assert metrics.source_bytes_read == 0


def test_complete_snapshot_union_dedupes_at_exact_byte_and_source_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "bracket.md", "four")
    _write(tmp_path, "selected.md", "next")
    seed_metrics = context_bundle.ContextIOMetrics()
    bracket = context_bundle.read_repo_source(
        tmp_path,
        "bracket.md",
        metrics=seed_metrics,
    )
    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 8)
    monkeypatch.setattr(context_bundle, "MAX_SOURCES", 2)
    metrics = context_bundle.ContextIOMetrics()

    ordered, snapshots = context_bundle.capture_sources(
        tmp_path,
        ["selected.md", "bracket.md", "selected.md", "bracket.md"],
        metrics=metrics,
        existing={"bracket.md": bracket},
    )

    assert ordered == ["selected.md", "bracket.md"]
    assert set(snapshots) == {"bracket.md", "selected.md"}
    assert sum(len(snapshot.raw) for snapshot in snapshots.values()) == 8
    assert metrics.source_opens == 1
    assert metrics.source_bytes_read == 4


def test_existing_snapshot_union_owns_source_count_before_new_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "bracket.md", "four")
    _write(tmp_path, "selected.md", "next")
    seed_metrics = context_bundle.ContextIOMetrics()
    bracket = context_bundle.read_repo_source(
        tmp_path,
        "bracket.md",
        metrics=seed_metrics,
    )
    monkeypatch.setattr(context_bundle, "MAX_SOURCES", 1)
    attempted: list[str] = []

    def unexpected_read(
        _repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        del metrics, freshness, limit
        attempted.append(raw_path)
        raise AssertionError("source count must block before read")

    monkeypatch.setattr(context_bundle, "read_repo_source", unexpected_read)

    with pytest.raises(context_bundle.ContextBundleError, match="TOO_MANY_SOURCES"):
        context_bundle.capture_sources(
            tmp_path,
            ["selected.md"],
            metrics=context_bundle.ContextIOMetrics(),
            existing={"bracket.md": bracket},
        )

    assert attempted == []


def test_exactly_exhausted_budget_rejects_before_next_source_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "a.md", "four")
    _write(tmp_path, "b.md", "next")
    real_read = context_bundle.read_repo_source
    attempted: list[str] = []

    def observed_read(
        repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        attempted.append(raw_path)
        return real_read(
            repo_root,
            raw_path,
            metrics=metrics,
            freshness=freshness,
            limit=limit,
        )

    monkeypatch.setattr(context_bundle, "MAX_TOTAL_SOURCE_BYTES", 4)
    monkeypatch.setattr(context_bundle, "read_repo_source", observed_read)

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="TOTAL_SOURCE_BYTES_EXCEEDED",
    ):
        context_bundle.capture_sources(
            tmp_path,
            ["a.md", "b.md"],
            metrics=context_bundle.ContextIOMetrics(),
        )

    assert attempted == ["a.md"]


def test_oversized_existing_snapshot_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "a.md", "four")
    metrics = context_bundle.ContextIOMetrics()
    snapshot = context_bundle.read_repo_source(tmp_path, "a.md", metrics=metrics)
    oversized = context_bundle.SourceSnapshot(
        path=snapshot.path,
        raw=b"12345",
        identity=snapshot.identity,
    )
    monkeypatch.setattr(context_bundle, "MAX_SOURCE_BYTES", 4)

    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_TOO_LARGE"):
        context_bundle.capture_sources(
            tmp_path,
            ["a.md"],
            metrics=context_bundle.ContextIOMetrics(),
            existing={"a.md": oversized},
        )


def test_safe_read_flag_and_absolute_packet_path_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(context_bundle.os, "O_NOFOLLOW")
    with pytest.raises(context_bundle.ContextBundleError, match="SAFE_READ_UNAVAILABLE"):
        context_bundle._required_flag("O_NOFOLLOW")
    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_OUTSIDE_REPOSITORY"):
        context_bundle.repo_relative_input(tmp_path, "/outside/packet.json")


@pytest.mark.parametrize("changed_field", ["links", "size"])
def test_opened_file_is_rechecked_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_field: str,
) -> None:
    _write(tmp_path, "context.md", "trusted")
    real_fstat = context_bundle.os.fstat

    def changed_fstat(descriptor: int) -> SimpleNamespace:
        metadata = real_fstat(descriptor)
        return SimpleNamespace(
            st_mode=metadata.st_mode,
            st_nlink=2 if changed_field == "links" else metadata.st_nlink,
            st_size=(
                (context_bundle.MAX_SOURCE_BYTES + 1)
                if changed_field == "size"
                else metadata.st_size
            ),
        )

    monkeypatch.setattr(context_bundle.os, "fstat", changed_fstat)
    expected = "UNSAFE_SOURCE_TYPE" if changed_field == "links" else "SOURCE_TOO_LARGE"

    with pytest.raises(context_bundle.ContextBundleError, match=expected):
        context_bundle.read_repo_source(
            tmp_path,
            "context.md",
            metrics=context_bundle.ContextIOMetrics(),
        )


def test_in_read_identity_change_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "context.md", "trusted")
    real_fstat = context_bundle.os.fstat
    calls = 0

    def changed_fstat(descriptor: int) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        metadata = real_fstat(descriptor)
        return SimpleNamespace(
            st_dev=metadata.st_dev,
            st_ino=metadata.st_ino,
            st_mode=metadata.st_mode,
            st_nlink=metadata.st_nlink,
            st_size=metadata.st_size,
            st_mtime_ns=metadata.st_mtime_ns + (1 if calls == 2 else 0),
            st_ctime_ns=metadata.st_ctime_ns,
        )

    monkeypatch.setattr(context_bundle.os, "fstat", changed_fstat)

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="SOURCE_CHANGED_DURING_READ",
    ):
        context_bundle.read_repo_source(
            tmp_path,
            "context.md",
            metrics=context_bundle.ContextIOMetrics(),
        )


def test_same_size_same_mtime_edit_is_rejected_by_exact_final_read(tmp_path: Path) -> None:
    path = _write(tmp_path, "context.md", "alpha\n")
    metrics, snapshot = _snapshot(tmp_path, "context.md")
    initial = {"context.md": snapshot}
    original = path.stat()
    path.write_text("omega\n", encoding="utf-8", newline="")
    os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))

    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_CHANGED"):
        context_bundle.materialize_context_bundle(
            tmp_path,
            occurrence=1,
            ordered_source_paths=["context.md"],
            bracket_paths=["context.md"],
            initial_snapshots=initial,
            dynamic_packet_path=None,
            metrics=metrics,
        )


def test_selection_input_change_blocks_complete_output(tmp_path: Path) -> None:
    _write(tmp_path, "role.md", "role\n")
    selector = _write(tmp_path, "selector.md", "one\n")
    metrics = context_bundle.ContextIOMetrics()
    _ordered, initial = context_bundle.capture_sources(
        tmp_path,
        ["role.md", "selector.md"],
        metrics=metrics,
    )
    selector.write_text("two\n", encoding="utf-8", newline="")

    with pytest.raises(context_bundle.ContextBundleError, match="SOURCE_CHANGED"):
        context_bundle.materialize_context_bundle(
            tmp_path,
            occurrence=1,
            ordered_source_paths=["role.md"],
            bracket_paths=["selector.md"],
            initial_snapshots=initial,
            dynamic_packet_path=None,
            metrics=metrics,
        )


def test_dynamic_packet_is_current_but_absent_from_static_sources(tmp_path: Path) -> None:
    _write(tmp_path, "role.md", "definition\n")
    _write(tmp_path, "packet.json", '{"goal":"current"}\n')

    result, _metrics = _materialize(
        tmp_path,
        ["role.md"],
        bracket=["role.md"],
        packet="packet.json",
    )

    assert result["sources"] == [{"path": "role.md", "content": "definition\n"}]
    assert result["dynamic_packet"] == {
        "path": "packet.json",
        "content": '{"goal":"current"}\n',
    }


def test_dynamic_packet_kernel_identity_cannot_enter_static_sources(tmp_path: Path) -> None:
    packet = _write(tmp_path, "packet.json", '{"goal":"current"}\n')
    alias_path = "PACKET.JSON"
    alias = tmp_path / alias_path
    same_object_alias = alias.exists()
    if not same_object_alias:
        alias.write_text("distinct static context\n", encoding="utf-8", newline="")

    if same_object_alias:
        with pytest.raises(
            context_bundle.ContextBundleError,
            match="DYNAMIC_PACKET_SELECTED_AS_STATIC_OBJECT: PACKET.JSON",
        ):
            _materialize(
                tmp_path,
                [alias_path],
                bracket=["packet.json"],
                packet="packet.json",
            )
        assert alias.stat().st_ino == packet.stat().st_ino
    else:
        result, _metrics = _materialize(
            tmp_path,
            [alias_path],
            bracket=["packet.json"],
            packet="packet.json",
        )
        assert alias.stat().st_ino != packet.stat().st_ino
        assert result["complete"] is True
        assert result["sources"] == [{"path": alias_path, "content": "distinct static context\n"}]


def test_materializer_rejects_preacquired_static_alias_of_dynamic_packet(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "packet.json", '{"goal":"current"}\n')
    metrics = context_bundle.ContextIOMetrics()
    dynamic = context_bundle.read_repo_source(tmp_path, "packet.json", metrics=metrics)
    static_alias = context_bundle.SourceSnapshot(
        path="alias.md",
        raw=dynamic.raw,
        identity=dynamic.identity,
    )

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="DYNAMIC_PACKET_SELECTED_AS_STATIC_OBJECT: alias.md",
    ):
        context_bundle.materialize_context_bundle(
            tmp_path,
            occurrence=1,
            ordered_source_paths=["alias.md"],
            bracket_paths=["packet.json"],
            initial_snapshots={"packet.json": dynamic, "alias.md": static_alias},
            dynamic_packet_path="packet.json",
            metrics=metrics,
        )


def test_static_content_change_invalidates_semantic_digest(tmp_path: Path) -> None:
    source = _write(tmp_path, "role.md", "one\n")
    first, _metrics = _materialize(tmp_path, ["role.md"])
    source.write_text("two\n", encoding="utf-8", newline="")
    second, _metrics = _materialize(tmp_path, ["role.md"])

    assert first["semantic_payload_sha256"] != second["semantic_payload_sha256"]
    assert first["sources"] != second["sources"]


def test_instruction_admission_is_explicit_and_bounded() -> None:
    assert (
        context_bundle.validate_instruction_file(
            "tools/codex_skills/pulseplate-workflow/SKILL.md",
            [],
        )
        == "tools/codex_skills/pulseplate-workflow/SKILL.md"
    )
    assert context_bundle.validate_instruction_file("docs/selected.md", ["docs/selected.md"])
    with pytest.raises(context_bundle.ContextBundleError, match="MUST_BE_MARKDOWN"):
        context_bundle.validate_instruction_file("tools/codex_skills/a/skill.txt", [])
    with pytest.raises(context_bundle.ContextBundleError, match="OUTSIDE_DECLARED_ROOTS"):
        context_bundle.validate_instruction_file("docs/unselected.md", [])


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.local",
        "config/credentials",
        "config/credentials.json",
        "config/credentials.yaml",
        "config/credentials.toml",
        "config/credentials.backup.md",
        "config/CREDENTIALS.YML",
        "secrets/id_rsa",
        "config/client.pem",
        "logs/provider.log",
        "providers/logs/provider.md",
        "artifacts/provider/output.md",
        "data/user-health.json",
    ],
)
def test_sensitive_or_dynamic_static_source_classes_are_forbidden(path: str) -> None:
    with pytest.raises(context_bundle.ContextBundleError, match="STATIC_SOURCE_FORBIDDEN"):
        context_bundle.validate_static_source_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "config/credential.yaml",
        "config/mycredentials.yaml",
        "config/credentials_yaml.md",
        "docs/credentials-guide.md",
        "credentials/config.yaml",
        "config/ordinary.yaml",
    ],
)
def test_credential_family_near_misses_remain_admitted(path: str) -> None:
    assert context_bundle.validate_static_source_path(path) == path


def test_materializer_rejects_credential_family_before_source_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "config/credentials.yaml", "api_token: SECRET_SENTINEL\n")
    attempted: list[str] = []

    def unexpected_read(
        _repo_root: Path,
        raw_path: str,
        *,
        metrics: context_bundle.ContextIOMetrics,
        freshness: bool = False,
        limit: int = context_bundle.MAX_SOURCE_BYTES,
    ) -> context_bundle.SourceSnapshot:
        del metrics, freshness, limit
        attempted.append(raw_path)
        raise AssertionError("credential source must be rejected before acquisition")

    monkeypatch.setattr(context_bundle, "read_repo_source", unexpected_read)

    with pytest.raises(
        context_bundle.ContextBundleError,
        match="STATIC_SOURCE_FORBIDDEN: config/credentials.yaml",
    ):
        _materialize(tmp_path, ["config/credentials.yaml"])

    assert attempted == []


def test_ordinary_static_source_still_materializes(tmp_path: Path) -> None:
    _write(tmp_path, "config/ordinary.yaml", "setting: safe\n")

    result, _metrics = _materialize(tmp_path, ["config/ordinary.yaml"])

    assert result["complete"] is True
    assert result["sources"] == [{"path": "config/ordinary.yaml", "content": "setting: safe\n"}]


def test_materializer_has_no_persistence_surface_after_negative_benchmark(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "role.md", "definition\n")

    result, metrics = _materialize(tmp_path, ["role.md"])

    assert "cache" not in result
    assert "bundle_opens" not in metrics.as_dict()
    assert "bundle_bytes_read" not in metrics.as_dict()
    assert "bundle_bytes_written" not in metrics.as_dict()
    assert not hasattr(context_bundle, "CACHE_RELATIVE_ROOT")

"""Closed task-packet candidate-path grammar tests."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from scripts.orchestration.context_pack import (
    REPO_ROOT,
    TaskCandidatePathMode,
    canonical_task_candidate_paths,
    compute_task_packet_id,
)


class _CustomSequence(Sequence[object]):
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def __getitem__(self, index: int) -> object:
        return self._values[index]

    def __len__(self) -> int:
        return len(self._values)


class _ListSubclass(list[object]):
    pass


class _TupleSubclass(tuple[object, ...]):
    pass


class _StringSubclass(str):
    pass


def test_candidate_path_producer_canonicalizes_only_frozen_aliases() -> None:
    repo_root = REPO_ROOT.as_posix()

    assert canonical_task_candidate_paths([], mode="producer") == []
    assert canonical_task_candidate_paths(["."], mode="producer") == ["."]
    assert canonical_task_candidate_paths([repo_root], mode="producer") == ["."]
    assert canonical_task_candidate_paths(
        [f"{repo_root}/future/not-yet-created.py"], mode="producer"
    ) == ["future/not-yet-created.py"]
    assert canonical_task_candidate_paths(["./docs/x.md"], mode="producer") == ["docs/x.md"]
    assert canonical_task_candidate_paths(
        ("scripts/z.py", "README.md", "README.md"), mode="producer"
    ) == ["README.md", "scripts/z.py"]
    assert canonical_task_candidate_paths(["README.md", ".", "scripts/z.py"], mode="producer") == [
        "."
    ]


def test_candidate_path_strict_wire_accepts_only_canonical_fixed_points() -> None:
    assert canonical_task_candidate_paths([], mode="strict_wire") == []
    assert canonical_task_candidate_paths(["."], mode="strict_wire") == ["."]
    assert canonical_task_candidate_paths(["README.md", "scripts/z.py"], mode="strict_wire") == [
        "README.md",
        "scripts/z.py",
    ]


@pytest.mark.parametrize(
    "raw_paths",
    (
        ["./README.md"],
        [REPO_ROOT.as_posix()],
        ["README.md", "README.md"],
        ["scripts/z.py", "README.md"],
        [".", "README.md"],
    ),
)
def test_candidate_path_strict_wire_rejects_noncanonical_collections(
    raw_paths: list[str],
) -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        canonical_task_candidate_paths(raw_paths, mode="strict_wire")


@pytest.mark.parametrize(
    "raw_paths",
    (
        "README.md",
        b"README.md",
        bytearray(b"README.md"),
        {"README.md": True},
        {"README.md"},
        iter(["README.md"]),
        _CustomSequence(["README.md"]),
        _ListSubclass(["README.md"]),
        _TupleSubclass(("README.md",)),
    ),
)
def test_candidate_path_collection_boundary_rejects_ambiguous_containers(
    raw_paths: object,
) -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        canonical_task_candidate_paths(raw_paths, mode="producer")


def test_candidate_path_wire_requires_an_exact_builtin_list() -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        canonical_task_candidate_paths(("README.md",), mode="strict_wire")


@pytest.mark.parametrize(
    "raw_value",
    (
        None,
        0,
        True,
        Path("README.md"),
        b"README.md",
        _StringSubclass("README.md"),
        {"path": "README.md"},
        ["README.md"],
    ),
)
def test_candidate_path_elements_must_be_exact_strings(raw_value: object) -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        canonical_task_candidate_paths([raw_value], mode="producer")


@pytest.mark.parametrize(
    "raw_path",
    (
        "",
        " ",
        " README.md",
        "README.md ",
        "docs/ file.md",
        "docs/dir /file.md",
        "docs/my\u00a0file.md",
        "docs/my\u3000file.md",
        "./",
        "./.",
        "././README.md",
        "docs/./README.md",
        "docs/.",
        "..",
        "docs/../README.md",
        "docs//README.md",
        "docs/README.md/",
        r"docs\README.md",
        "~",
        "~/README.md",
        "C:README.md",
        "C:/README.md",
        "file:README.md",
        "file:///README.md",
        "https:/example/README.md",
        "git+ssh://example/README.md",
        "README.md\x00tail",
        "README.md\n",
        "README.md\r",
        "README.md\t",
        "README.md\x1b",
        "README.md\x7f",
        "README.md\u2028",
        "README.md\u2029",
        "README.md\u202e",
        "README.md\u2066",
        "README.md\ufeff",
        "README.md\ud800",
    ),
)
def test_candidate_path_grammar_rejects_ambiguous_spellings(raw_path: str) -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        canonical_task_candidate_paths([raw_path], mode="producer")


def test_candidate_path_absolute_containment_is_component_aware() -> None:
    repo_root = REPO_ROOT.as_posix()
    parent = REPO_ROOT.parent.as_posix()
    repo_name = REPO_ROOT.name
    outside_paths = (
        f"{repo_root}-evil/x.py",
        f"{repo_root}2/x.py",
        f"{repo_root}_backup/x.py",
        f"{parent}/{repo_name}-shadow/x.py",
        f"{repo_root}/../outside.py",
        f"{repo_root}/./README.md",
        f"{repo_root}/",
        f"{repo_root}/sub/../../outside.py",
    )

    for raw_path in outside_paths:
        with pytest.raises(ValueError, match="canonical task candidate paths"):
            canonical_task_candidate_paths([raw_path], mode="producer")


def test_candidate_path_invalid_member_is_not_hidden_by_dedup_or_root() -> None:
    for raw_paths in (
        [".", None],
        [".", ""],
        ["README.md", "README.md", 1],
        ["README.md", "\n.github/workflows/ci.yml"],
    ):
        with pytest.raises(ValueError, match="canonical task candidate paths"):
            canonical_task_candidate_paths(raw_paths, mode="producer")


def test_candidate_path_identity_preserves_printable_unicode_without_normalization() -> None:
    nfc = "docs/café.md"
    nfd = "docs/cafe\u0301.md"

    assert nfc != nfd
    assert canonical_task_candidate_paths([nfc, nfd], mode="producer") == sorted([nfc, nfd])
    assert canonical_task_candidate_paths(["docs／file.md"], mode="producer") == ["docs／file.md"]


def test_candidate_path_preserves_ordinary_internal_spaces() -> None:
    repo_root = REPO_ROOT.as_posix()
    paths = [
        ".github/Attached HTML and CSS Context",
        "ios/PulsePlate/Preview Content/.gitkeep",
    ]

    assert canonical_task_candidate_paths(paths, mode="producer") == sorted(paths)
    assert canonical_task_candidate_paths(sorted(paths), mode="strict_wire") == sorted(paths)
    assert canonical_task_candidate_paths(
        [f"{repo_root}/ios/PulsePlate/Preview Content/.gitkeep"],
        mode="producer",
    ) == ["ios/PulsePlate/Preview Content/.gitkeep"]
    identities = {
        compute_task_packet_id(
            goal="Bind spaces",
            task_class="Orchestration",
            domain="orchestration",
            candidate_paths=[path],
        )
        for path in ("docs/a b.md", "docs/a  b.md", "docs/a-b.md")
    }
    assert len(identities) == 3


def test_candidate_path_recognizer_has_no_filesystem_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = REPO_ROOT.as_posix()

    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem method must not be used")

    for method in ("resolve", "expanduser", "exists", "is_file", "is_dir", "is_symlink"):
        monkeypatch.setattr(Path, method, fail)

    assert canonical_task_candidate_paths([f"{repo_root}/future/new.py"], mode="producer") == [
        "future/new.py"
    ]
    assert canonical_task_candidate_paths(["future/new.py"], mode="strict_wire") == [
        "future/new.py"
    ]
    assert canonical_task_candidate_paths([f"{repo_root}/future/new file.py"], mode="producer") == [
        "future/new file.py"
    ]


def test_task_packet_identity_uses_the_shared_candidate_path_projection() -> None:
    common = {
        "goal": "Bind candidate paths",
        "task_class": "Orchestration",
        "domain": "orchestration",
    }

    empty_id = compute_task_packet_id(**common, candidate_paths=[])
    root_id = compute_task_packet_id(**common, candidate_paths=["."])
    canonical_id = compute_task_packet_id(**common, candidate_paths=["README.md"])

    assert root_id != empty_id
    assert (
        compute_task_packet_id(
            **common,
            candidate_paths=[REPO_ROOT.as_posix()],
        )
        == root_id
    )
    assert compute_task_packet_id(**common, candidate_paths=["./README.md"]) == canonical_id
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        compute_task_packet_id(**common, candidate_paths=["docs/../README.md"])


@pytest.mark.parametrize("raw_mode", ("unknown", None, []))
def test_candidate_path_mode_is_closed(raw_mode: object) -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        canonical_task_candidate_paths(["README.md"], mode=cast(TaskCandidatePathMode, raw_mode))

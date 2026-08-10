"""Contract tests for the deterministic invariant-family relations sidecar."""

from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import operator
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import cast

import pytest

import scripts.orchestration.review_invariant_family_relations as relations

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "orchestration" / "review_invariant_family_relations.py"
SCHEMA = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "review_invariant_family_relations.v1.schema.json"
)
CONTRACT = (
    REPO_ROOT
    / "docs"
    / "orchestration"
    / "contracts"
    / "REVIEW_INVARIANT_FAMILY_RELATIONS_SHADOW_CONTRACT.md"
)
FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "orchestration"
    / "review_invariant_family_relations_cases.json"
)

POLICY_BEGIN = "<!-- BEGIN REVIEW_INVARIANT_FAMILY_RELATIONS_POLICY_V1 -->"
POLICY_END = "<!-- END REVIEW_INVARIANT_FAMILY_RELATIONS_POLICY_V1 -->"


def _false_authority() -> dict[str, bool]:
    return {field: False for field in relations.AUTHORITY_FIELDS}


def _snapshot(
    universe: list[str],
    families: list[tuple[str, list[str]]],
) -> dict[str, object]:
    return {
        "schema_version": relations.SNAPSHOT_SCHEMA_VERSION,
        "universe_finding_ids": universe,
        "families": [
            {"family_id": family_id, "finding_ids": finding_ids}
            for family_id, finding_ids in families
        ],
        **_false_authority(),
    }


def _compact_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _run_cli(raw: bytes, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=REPO_ROOT,
        input=raw,
        capture_output=True,
        check=False,
    )


def _fixture_snapshot() -> dict[str, object]:
    return cast(dict[str, object], json.loads(FIXTURE.read_text(encoding="utf-8")))


def _fixture_result() -> tuple[bytes, dict[str, object]]:
    completed = _run_cli(FIXTURE.read_bytes())
    assert completed.returncode == 0, completed.stderr.decode("ascii", errors="replace")
    assert completed.stderr == b""
    return completed.stdout, cast(dict[str, object], json.loads(completed.stdout))


def _relation_map(artifact: Mapping[str, object]) -> dict[tuple[str, str], dict[str, object]]:
    raw_relations = cast(list[dict[str, object]], artifact["relations"])
    return {
        (cast(str, item["left_family_id"]), cast(str, item["right_family_id"])): item
        for item in raw_relations
    }


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _contract_policy() -> dict[str, object]:
    text = CONTRACT.read_text(encoding="utf-8")
    assert text.count(POLICY_BEGIN) == 1
    assert text.count(POLICY_END) == 1
    section = text.split(POLICY_BEGIN, 1)[1].split(POLICY_END, 1)[0]
    assert section.count("```json") == 1
    payload = section.split("```json", 1)[1].split("```", 1)[0]
    return cast(dict[str, object], json.loads(payload))


def test_policy_projection_is_recursive_exact_and_immutable() -> None:
    schema = cast(dict[str, object], json.loads(SCHEMA.read_text(encoding="utf-8")))
    contract_policy = _contract_policy()
    script_policy = cast(dict[str, object], _thaw(relations.POLICY_PROJECTION))

    assert schema["x-pulseplate-policy-projection"] == contract_policy == script_policy
    assert isinstance(relations.POLICY_PROJECTION, MappingProxyType)
    with pytest.raises(TypeError):
        operator.setitem(relations.POLICY_PROJECTION, "policy_version", "changed")
    nested = cast(Mapping[str, object], relations.POLICY_PROJECTION["bounds"])
    assert isinstance(nested, MappingProxyType)
    with pytest.raises(TypeError):
        operator.setitem(nested, "max_findings", 1)


def test_schema_is_closed_draft_2020_12_oneof_with_actual_bounds() -> None:
    schema = cast(dict[str, object], json.loads(SCHEMA.read_text(encoding="utf-8")))
    definitions = cast(dict[str, dict[str, object]], schema["$defs"])

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["unevaluatedProperties"] is False
    assert schema["oneOf"] == [
        {"$ref": "#/$defs/snapshot"},
        {"$ref": "#/$defs/artifact"},
    ]
    for definition_name in ("snapshot", "artifact", "family", "relation"):
        assert definitions[definition_name]["additionalProperties"] is False
    assert cast(dict[str, object], definitions["findingIdList"])["maxItems"] == 2048
    assert cast(dict[str, object], definitions["findingIdList"])["uniqueItems"] is True
    snapshot_properties = cast(dict[str, dict[str, object]], definitions["snapshot"]["properties"])
    artifact_properties = cast(dict[str, dict[str, object]], definitions["artifact"]["properties"])
    assert cast(dict[str, object], snapshot_properties["families"])["maxItems"] == 32
    assert cast(dict[str, object], artifact_properties["relations"])["maxItems"] == 496
    assert definitions["falseAuthority"] == {"const": False}
    safe_id = cast(dict[str, object], definitions["safeId"])
    assert (
        cast(dict[str, object], safe_id["not"])["pattern"]
        == _contract_policy()["forbidden_id_pattern"]
    )
    for variant in (definitions["snapshot"], definitions["artifact"]):
        required = cast(list[str], variant["required"])
        properties = cast(dict[str, dict[str, object]], variant["properties"])
        for field in relations.AUTHORITY_FIELDS:
            assert field in required
            assert properties[field] == {"$ref": "#/$defs/falseAuthority"}


def test_fixture_emits_all_relations_partitions_and_unknowns() -> None:
    stdout, artifact = _fixture_result()
    pairs = _relation_map(artifact)

    assert stdout.endswith(b"\n")
    assert not stdout.endswith(b"\n\n")
    stdout.decode("ascii")
    assert stdout == _compact_bytes(artifact) + b"\n"
    assert artifact["unknown_finding_ids"] == ["d", "e", "f"]
    assert len(pairs) == 6
    assert pairs[("A", "B")] == {
        "left_family_id": "A",
        "right_family_id": "B",
        "relation": "left_proper_subset",
        "intersection_finding_ids": ["a"],
        "left_only_finding_ids": [],
        "right_only_finding_ids": ["b"],
    }
    assert pairs[("A", "C")]["relation"] == "equal"
    assert pairs[("A", "D")]["relation"] == "disjoint"
    assert pairs[("B", "C")]["relation"] == "right_proper_subset"
    assert pairs[("B", "D")] == {
        "left_family_id": "B",
        "right_family_id": "D",
        "relation": "partial_overlap",
        "intersection_finding_ids": ["b"],
        "left_only_finding_ids": ["a"],
        "right_only_finding_ids": ["c"],
    }
    assert {cast(str, item["relation"]) for item in pairs.values()} == set(
        relations.RELATION_VALUES
    )


def test_empty_sets_have_equal_and_oriented_subset_semantics() -> None:
    source = _snapshot(
        ["a"],
        [
            ("AEmpty", []),
            ("BFull", ["a"]),
            ("CEmpty", []),
        ],
    )
    artifact = relations.process_document(source)
    pairs = _relation_map(artifact)

    assert pairs[("AEmpty", "BFull")]["relation"] == "left_proper_subset"
    assert pairs[("BFull", "CEmpty")]["relation"] == "right_proper_subset"
    assert pairs[("AEmpty", "CEmpty")] == {
        "left_family_id": "AEmpty",
        "right_family_id": "CEmpty",
        "relation": "equal",
        "intersection_finding_ids": [],
        "left_only_finding_ids": [],
        "right_only_finding_ids": [],
    }


def test_zero_families_leave_the_complete_universe_unknown() -> None:
    artifact = relations.process_document(_snapshot(["b", "a"], []))

    assert artifact["relations"] == []
    assert artifact["unknown_finding_ids"] == ["a", "b"]


def test_snapshot_permutations_produce_byte_identical_artifacts() -> None:
    source = _fixture_snapshot()
    permuted = copy.deepcopy(source)
    cast(list[object], permuted["universe_finding_ids"]).reverse()
    families = cast(list[dict[str, object]], permuted["families"])
    families.reverse()
    for family in families:
        cast(list[object], family["finding_ids"]).reverse()

    first = relations.process_input_bytes(_compact_bytes(source))
    second = relations.process_input_bytes(_compact_bytes(permuted))

    assert first == second


def test_domain_separated_digests_and_full_idempotency_key() -> None:
    _, artifact = _fixture_result()
    snapshot = cast(dict[str, object], artifact["snapshot"])
    expected_snapshot_digest = hashlib.sha256(
        relations.SNAPSHOT_DIGEST_DOMAIN + b"\0" + _compact_bytes(snapshot)
    ).hexdigest()
    artifact_core = {
        key: value
        for key, value in artifact.items()
        if key not in {"artifact_fingerprint", "idempotency_key"}
    }
    expected_artifact_digest = hashlib.sha256(
        relations.ARTIFACT_DIGEST_DOMAIN + b"\0" + _compact_bytes(artifact_core)
    ).hexdigest()

    assert artifact["snapshot_fingerprint"] == f"sha256:{expected_snapshot_digest}"
    assert artifact["artifact_fingerprint"] == f"sha256:{expected_artifact_digest}"
    assert artifact["idempotency_key"] == (
        f"review-invariant-family-relations.v1:{expected_artifact_digest}"
    )
    assert len(cast(str, artifact["idempotency_key"]).rsplit(":", 1)[1]) == 64
    assert expected_snapshot_digest != expected_artifact_digest


def test_valid_relations_replay_emits_the_same_canonical_bytes() -> None:
    canonical, artifact = _fixture_result()
    pretty_replay = json.dumps(artifact, ensure_ascii=True, indent=2).encode("ascii")

    completed = _run_cli(pretty_replay)

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert completed.stdout == canonical


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (
            lambda artifact: cast(list[dict[str, object]], artifact["relations"])[0].update(
                {"right_only_finding_ids": []}
            ),
            b"contract_error:artifact_replay_mismatch\n",
        ),
        (
            lambda artifact: artifact.update({"artifact_fingerprint": "sha256:" + "0" * 64}),
            b"contract_error:artifact_replay_mismatch\n",
        ),
        (
            lambda artifact: cast(list[dict[str, object]], artifact["relations"]).reverse(),
            b"contract_error:artifact_replay_mismatch\n",
        ),
        (
            lambda artifact: artifact.update({"review_authority": True}),
            b"contract_error:authority_boundary_violation\n",
        ),
    ],
)
def test_replay_rejects_partition_digest_order_and_authority_tampering(
    mutator: Callable[[dict[str, object]], object],
    expected_error: bytes,
) -> None:
    _, artifact = _fixture_result()
    mutator(artifact)
    completed = _run_cli(_compact_bytes(artifact))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == expected_error


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    [
        (b"", "stdin_empty"),
        (b"\xef\xbb\xbf{}", "utf8_bom_not_allowed"),
        (b"\xff", "invalid_utf8"),
        (b"{} {}", "invalid_json"),
        (b'{"schema_version":"x","nested":{"a":false,"a":false}}', "duplicate_key"),
        (b'{"schema_version":"x","schema_version":"y"}', "duplicate_key"),
        (b'{"schema_version":1}', "numeric_token_not_allowed"),
        (b'{"schema_version":1.5}', "numeric_token_not_allowed"),
        (b'{"schema_version":1e999}', "numeric_token_not_allowed"),
        (b'{"schema_version":NaN}', "numeric_token_not_allowed"),
        (b'{"schema_version":Infinity}', "numeric_token_not_allowed"),
        (b'{"schema_version":-Infinity}', "numeric_token_not_allowed"),
        (b"[]", "document_not_object"),
        (b'{"schema_version":null}', "schema_branch_not_recognized"),
    ],
)
def test_strict_parser_rejects_ambiguous_or_coerced_json(
    raw: bytes,
    expected_code: str,
) -> None:
    completed = _run_cli(raw)

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == f"contract_error:{expected_code}\n".encode("ascii")


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (lambda source: source.update({"extra": False}), "schema_validation_failed"),
        (lambda source: source.pop("families"), "schema_validation_failed"),
        (lambda source: source.update({"families": None}), "schema_validation_failed"),
        (lambda source: source.update({"families": "[]"}), "schema_validation_failed"),
        (
            lambda source: source.update({"side_effects_allowed": "false"}),
            "authority_boundary_violation",
        ),
        (
            lambda source: cast(list[dict[str, object]], source["families"])[0].update(
                {"extra": False}
            ),
            "schema_validation_failed",
        ),
    ],
)
def test_closed_snapshot_schema_rejects_extra_missing_null_and_coercion(
    mutation: Callable[[dict[str, object]], object],
    expected_code: str,
) -> None:
    source = _fixture_snapshot()
    mutation(source)
    completed = _run_cli(_compact_bytes(source))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == f"contract_error:{expected_code}\n".encode("ascii")


def test_ids_are_ascii_path_and_url_safe_and_errors_never_echo_values() -> None:
    submitted = "https://example.invalid/private?token=SECRET"
    source = _snapshot([submitted], [])

    completed = _run_cli(_compact_bytes(source))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:invalid_id\n"
    assert b"example" not in completed.stderr
    assert b"SECRET" not in completed.stderr
    assert len(completed.stderr) <= relations.MAX_STDERR_BYTES


@pytest.mark.parametrize(
    "submitted",
    [
        "gh" + "p_AbCdEf123",
        "gh" + "o_AbCdEf123",
        "gh" + "u_AbCdEf123",
        "gh" + "s_AbCdEf123",
        "gh" + "r_AbCdEf123",
        "sk" + "_proj_Example123",
        "sk" + "_test_Example123",
        "sk" + "-proj-Example123",
        "gl" + "pat-Example123",
        "AK" + "IA1234567890",
        "AS" + "IA123456789",
        "client" + "-secret-value",
        "bear" + "er_value",
        "private" + "_key_value",
    ],
)
def test_secret_shaped_ids_are_rejected_without_echo(submitted: str) -> None:
    completed = _run_cli(_compact_bytes(_snapshot([submitted], [])))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:invalid_id\n"
    assert submitted.encode("ascii") not in completed.stderr


def test_id_bound_accepts_64_ascii_bytes_and_rejects_65() -> None:
    at_limit = "a" * relations.MAX_ID_ASCII_BYTES
    over_limit = at_limit + "a"

    artifact = relations.process_document(_snapshot([at_limit], [("A", [at_limit])]))
    assert cast(dict[str, object], artifact["snapshot"])["universe_finding_ids"] == [at_limit]
    completed = _run_cli(_compact_bytes(_snapshot([over_limit], [])))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:invalid_id\n"


def test_arguments_are_rejected_without_reading_a_document() -> None:
    completed = _run_cli(FIXTURE.read_bytes(), "unexpected")

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:arguments_not_allowed\n"


def test_stdin_limit_plus_one_fails_without_partial_output() -> None:
    completed = _run_cli(b" " * (relations.MAX_STDIN_BYTES + 1))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:stdin_too_large\n"


def test_finding_bound_accepts_limit_and_rejects_limit_plus_one() -> None:
    at_limit = [f"f{index:04d}" for index in range(relations.MAX_FINDINGS)]
    rendered = relations.process_input_bytes(_compact_bytes(_snapshot(at_limit, [])))
    assert len(cast(list[str], json.loads(rendered)["unknown_finding_ids"])) == 2048

    over_limit = [f"f{index:04d}" for index in range(relations.MAX_FINDINGS + 1)]
    completed = _run_cli(_compact_bytes(_snapshot(over_limit, [])))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:finding_limit_exceeded\n"


def test_family_and_relation_bounds_accept_32_and_reject_33() -> None:
    at_limit = _snapshot(
        [],
        [(f"F{index:02d}", []) for index in range(relations.MAX_FAMILIES)],
    )
    artifact = relations.process_document(at_limit)
    assert len(cast(list[object], artifact["relations"])) == relations.MAX_RELATION_RECORDS

    over_limit = _snapshot(
        [],
        [(f"F{index:02d}", []) for index in range(relations.MAX_FAMILIES + 1)],
    )
    completed = _run_cli(_compact_bytes(over_limit))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:family_limit_exceeded\n"


def test_membership_bound_accepts_4096_and_rejects_4097() -> None:
    universe = [f"f{index:04d}" for index in range(relations.MAX_FINDINGS)]
    at_limit = _snapshot(universe, [("A", universe), ("B", list(reversed(universe)))])
    artifact = relations.process_document(at_limit)
    pair = cast(list[dict[str, object]], artifact["relations"])[0]
    assert len(cast(list[str], pair["intersection_finding_ids"])) == 2048

    over_limit = _snapshot(
        universe,
        [("A", universe), ("B", universe), ("C", [universe[0]])],
    )
    completed = _run_cli(_compact_bytes(over_limit))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:membership_limit_exceeded\n"


def test_derived_partition_ref_preflight_accepts_limit_and_rejects_next_contribution() -> None:
    at_limit_ids = [f"f{index:04d}" for index in range(1024)]
    at_limit = _snapshot(at_limit_ids, [("A", at_limit_ids), ("B", []), ("C", [])])
    artifact = relations.process_document(at_limit)
    assert len(cast(list[object], artifact["relations"])) == 3

    over_limit_ids = [f"f{index:04d}" for index in range(1025)]
    over_limit = _snapshot(over_limit_ids, [("A", over_limit_ids), ("B", []), ("C", [])])
    completed = _run_cli(_compact_bytes(over_limit))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:derived_partition_ref_limit_exceeded\n"


def test_replay_rejects_submitted_partition_reference_limit_plus_one() -> None:
    _, artifact = _fixture_result()
    relation_records = cast(list[dict[str, object]], artifact["relations"])
    relation_records[0]["intersection_finding_ids"] = [
        f"x{index:04d}" for index in range(relations.MAX_DERIVED_PARTITION_REFS)
    ]
    relation_records[0]["left_only_finding_ids"] = ["overflow"]

    completed = _run_cli(_compact_bytes(artifact))

    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:derived_partition_ref_limit_exceeded\n"


def test_membership_outside_finite_universe_and_duplicate_ids_fail_closed() -> None:
    outside = _snapshot(["a"], [("A", ["b"])])
    duplicate_universe = _snapshot(["a", "a"], [])
    duplicate_family = _snapshot(["a"], [("A", []), ("A", ["a"])])

    assert _run_cli(_compact_bytes(outside)).stderr == (
        b"contract_error:membership_outside_universe\n"
    )
    assert _run_cli(_compact_bytes(duplicate_universe)).stderr == (b"contract_error:duplicate_id\n")
    assert _run_cli(_compact_bytes(duplicate_family)).stderr == (b"contract_error:duplicate_id\n")


def test_final_stdout_size_check_occurs_before_transport_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = relations.process_input_bytes(FIXTURE.read_bytes())
    monkeypatch.setattr(relations, "MAX_STDOUT_BYTES", len(expected))
    assert relations.process_input_bytes(FIXTURE.read_bytes()) == expected

    monkeypatch.setattr(relations, "MAX_STDOUT_BYTES", len(expected) - 1)

    with pytest.raises(relations.ContractError, match="stdout_too_large"):
        relations.process_input_bytes(FIXTURE.read_bytes())


def test_main_sanitizes_unexpected_internal_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    monkeypatch.setattr(relations.sys, "argv", [str(SCRIPT)])
    monkeypatch.setattr(
        relations.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(FIXTURE.read_bytes())),
    )
    monkeypatch.setattr(relations.sys, "stdout", SimpleNamespace(buffer=stdout))
    monkeypatch.setattr(relations.sys, "stderr", SimpleNamespace(buffer=stderr))

    def raise_unexpected(_raw: bytes) -> bytes:
        raise RuntimeError("must not escape")

    monkeypatch.setattr(relations, "process_input_bytes", raise_unexpected)

    assert relations.main() == 2
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == b"contract_error:internal_error\n"


def test_main_reports_output_transport_failure_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingBuffer:
        def __init__(self) -> None:
            self.write_attempts = 0

        def write(self, _payload: bytes) -> int:
            self.write_attempts += 1
            raise OSError("sink unavailable")

        def flush(self) -> None:
            return None

    stdout = FailingBuffer()
    stderr = io.BytesIO()
    monkeypatch.setattr(relations.sys, "argv", [str(SCRIPT)])
    monkeypatch.setattr(
        relations.sys,
        "stdin",
        SimpleNamespace(buffer=io.BytesIO(FIXTURE.read_bytes())),
    )
    monkeypatch.setattr(
        relations.sys,
        "stdout",
        SimpleNamespace(buffer=stdout),
    )
    monkeypatch.setattr(relations.sys, "stderr", SimpleNamespace(buffer=stderr))

    assert relations.main() == 2
    assert stdout.write_attempts == 1
    assert stderr.getvalue() == b"contract_error:output_transport_failure\n"


def test_authority_fields_are_required_false_in_source_embedded_snapshot_and_artifact() -> None:
    _, artifact = _fixture_result()
    snapshot = cast(dict[str, object], artifact["snapshot"])

    for field in relations.AUTHORITY_FIELDS:
        assert artifact[field] is False
        assert snapshot[field] is False
    missing = _fixture_snapshot()
    missing.pop("merge_authority")
    completed = _run_cli(_compact_bytes(missing))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b"contract_error:schema_validation_failed\n"


def test_runtime_script_has_only_bounded_stdlib_imports_and_no_authority_calls() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots == {
        "__future__",
        "collections",
        "hashlib",
        "itertools",
        "json",
        "re",
        "sys",
        "types",
        "typing",
    }
    assert imported_roots.isdisjoint(
        {
            "app",
            "core",
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib",
        }
    )

    allowed_call_names = {
        "ContractError",
        "MappingProxyType",
        "SystemExit",
        "_build_artifact",
        "_canonical_json_bytes",
        "_choose_two",
        "_domain_digest",
        "_freeze",
        "_normalize_id_list",
        "_normalize_snapshot",
        "_precompute_partition_reference_count",
        "_relation_name",
        "_require_array",
        "_require_exact_keys",
        "_require_false_authority",
        "_require_id",
        "_require_object",
        "_strict_json_document",
        "_validate_artifact_shape",
        "_write_contract_error",
        "cast",
        "combinations",
        "dict",
        "frozenset",
        "isinstance",
        "len",
        "list",
        "main",
        "process_document",
        "process_input_bytes",
        "set",
        "sorted",
        "super",
        "tuple",
    }
    allowed_call_attributes = {
        "__init__",
        "add",
        "append",
        "compile",
        "decode",
        "difference",
        "dumps",
        "encode",
        "flush",
        "fullmatch",
        "get",
        "hexdigest",
        "intersection",
        "issubset",
        "items",
        "loads",
        "read",
        "search",
        "sha256",
        "sort",
        "startswith",
        "update",
        "values",
        "write",
    }
    actual_call_names: set[str] = set()
    actual_call_attributes: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            actual_call_names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            actual_call_attributes.add(node.func.attr)
        else:
            pytest.fail("sidecar uses a non-name, non-attribute call target")
    assert actual_call_names == allowed_call_names
    assert actual_call_attributes == allowed_call_attributes


def test_sidecar_has_no_runtime_workflow_or_authority_integration_references() -> None:
    forbidden_roots = (
        REPO_ROOT / "app",
        REPO_ROOT / "core",
        REPO_ROOT / ".github" / "workflows",
    )
    needle = "review_invariant_family_relations"
    matches: list[str] = []
    for root in forbidden_roots:
        for candidate in root.rglob("*"):
            if candidate.suffix not in {".py", ".yml", ".yaml", ".json", ".md"}:
                continue
            try:
                text = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if needle in text:
                matches.append(candidate.relative_to(REPO_ROOT).as_posix())
    integration_files = (
        REPO_ROOT / "scripts" / "orchestration" / "task_bootstrap.py",
        REPO_ROOT / "scripts" / "orchestration" / "role_dispatch_bridge.py",
        REPO_ROOT / "scripts" / "orchestration" / "review_pattern_oracles.py",
        REPO_ROOT / "scripts" / "orchestration" / "agent_learning_loop.py",
        REPO_ROOT / "scripts" / "orchestration" / "pr_review_evidence.py",
        REPO_ROOT / "scripts" / "orchestration" / "review_mapping_artifact.py",
    )
    for candidate in integration_files:
        if not candidate.exists():
            continue
        if needle in candidate.read_text(encoding="utf-8"):
            matches.append(candidate.relative_to(REPO_ROOT).as_posix())
    assert matches == []


def test_fixture_is_sanitized_and_contains_only_the_frozen_finite_case() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    lowered = text.casefold()
    for forbidden in (
        "http://",
        "https://",
        "github",
        "pr #",
        "reviewer",
        "severity",
        "provider",
        "savings",
        "revenue",
        "historical",
        "katsiaryna",
        '"roles"',
        '"statuses"',
        '"providers"',
    ):
        assert forbidden not in lowered

    source = _fixture_snapshot()
    assert source["universe_finding_ids"] == ["a", "b", "c", "d", "e", "f"]
    assert source["families"] == [
        {"family_id": "A", "finding_ids": ["a"]},
        {"family_id": "B", "finding_ids": ["a", "b"]},
        {"family_id": "C", "finding_ids": ["a"]},
        {"family_id": "D", "finding_ids": ["b", "c"]},
    ]

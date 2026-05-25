from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.ci.check_docs_phase1_gates as docs_phase1
import scripts.ci.check_philosophy_source_corpus_index as corpus
from scripts.ci.check_philosophy_source_corpus_index import (
    DEFAULT_GATE_REPORT,
    DEFAULT_INDEX,
    DEFAULT_ROADMAP,
    DEFAULT_SCHEMA,
    validate_file_contents,
    validate_philosophy_source_corpus_index,
    validate_touched_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REL_INDEX = "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.json"
REL_SCHEMA = "docs/orchestration/contracts/PHILOSOPHY_SOURCE_CORPUS_INDEX.schema.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _index() -> dict[str, object]:
    loaded = json.loads(_read(DEFAULT_INDEX))
    assert isinstance(loaded, dict)
    return loaded


def _schema() -> dict[str, object]:
    loaded = json.loads(_read(DEFAULT_SCHEMA))
    assert isinstance(loaded, dict)
    return loaded


def _validate(
    index: dict[str, object] | None = None,
    *,
    schema_text: str | None = None,
    roadmap_text: str | None = None,
) -> list[str]:
    index_text = (
        json.dumps(index, ensure_ascii=False, indent=2) + "\n"
        if index is not None
        else _read(DEFAULT_INDEX)
    )
    return validate_philosophy_source_corpus_index(
        index_text=index_text,
        schema_text=schema_text or _read(DEFAULT_SCHEMA),
        roadmap_text=roadmap_text or _read(DEFAULT_ROADMAP),
        gate_report_text=_read(DEFAULT_GATE_REPORT),
    )


def _copy_source_corpus_companions(tmp_path: Path) -> None:
    for relpath in docs_phase1.PHILOSOPHY_SOURCE_CORPUS_INPUTS:
        source = REPO_ROOT / relpath
        destination = tmp_path / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def test_philosophy_source_corpus_index_is_current() -> None:
    assert _validate() == []


def test_philosophy_source_corpus_index_phase1_docs_gate_route() -> None:
    assert docs_phase1.check_docs_phase1_guards(markdown_files=[REL_INDEX, REL_SCHEMA]) == []


def test_philosophy_source_corpus_index_rejects_missing_source() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    index["sources"] = sources[:-1]

    errors = _validate(index)

    assert any("sources must contain 6 entries" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_duplicate_source_id() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    duplicate = dict(sources[1])
    duplicate["source_id"] = sources[0]["source_id"]
    sources[1] = duplicate

    errors = _validate(index)

    assert any("duplicate source_id" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_source_order_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    sources[0], sources[1] = sources[1], sources[0]

    errors = _validate(index)

    assert any("sources must be sorted and complete" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_page_count_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["page_count"] = 23
    sources[0] = first

    errors = _validate(index)

    assert any("analytic_linguistic_audit.page_count must be 22" in error for error in errors)
    assert any("sources page_count sum must be 102" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_sha256_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["sha256"] = "0" * 64
    sources[0] = first

    errors = _validate(index)

    assert any(
        "analytic_linguistic_audit.sha256 must match verified PDF hash" in error for error in errors
    )


def test_philosophy_source_corpus_index_rejects_non_object_source_item() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    sources.append(42)

    errors = _validate(index)

    assert any("sources[6] must be an object" in error for error in errors)
    assert any("sources must contain 6 entries" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_source_family_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["source_family"] = "generic_philosophy"
    sources[0] = first

    errors = _validate(index)

    assert any(
        "analytic_linguistic_audit.source_family must be analytic_linguistic_audit" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_language_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["language"] = "en"
    sources[0] = first

    errors = _validate(index)

    assert any("analytic_linguistic_audit.language must be ru" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_source_scalar_type_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["title"] = 123
    sources[0] = first

    errors = _validate(index)

    assert any("analytic_linguistic_audit.title must be a string" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_source_array_type_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    rails = list(first["discipline_rails"])
    rails.append(123)
    first["discipline_rails"] = rails
    sources[0] = first

    errors = _validate(index)

    assert any(
        "analytic_linguistic_audit.discipline_rails must contain only strings" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_theme_array_type_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    themes = list(first["theme_families"])
    themes.append(123)
    first["theme_families"] = themes
    sources[0] = first

    errors = _validate(index)

    assert any(
        "analytic_linguistic_audit.theme_families must contain only strings" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_linked_anchor_array_type_drift() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    anchors = list(first["linked_repo_anchors"])
    anchors.append({"unexpected": "anchor"})
    first["linked_repo_anchors"] = anchors
    sources[0] = first

    errors = _validate(index)

    assert any(
        "analytic_linguistic_audit.linked_repo_anchors must contain only strings" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_generic_theme_collapse() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["theme_families"] = ["generic"]
    sources[0] = first

    errors = _validate(index)

    assert any(
        "analytic_linguistic_audit.theme_families missing required themes" in error
        for error in errors
    )
    assert any("source corpus missing global theme coverage" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_missing_interdisciplinary_rail() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    leibniz = dict(sources[1])
    leibniz["discipline_rails"] = ["philosophy"]
    sources[1] = leibniz

    errors = _validate(index)

    assert any(
        "leibniz_information_theory.discipline_rails missing required disciplines" in error
        for error in errors
    )
    assert any("source corpus missing global discipline coverage" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_missing_wellness_boundary() -> None:
    index = _index()
    source_policy = index["source_policy"]
    assert isinstance(source_policy, dict)
    policy = dict(source_policy)
    del policy["wellness_boundary"]
    index["source_policy"] = policy

    errors = _validate(index)

    assert any("source_policy.wellness_boundary must be" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_therapy_positioning() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    cbt_row = dict(sources[2])
    cbt_row["future_handoff"] = "Use as therapeutic CBT design evidence after review."
    sources[2] = cbt_row

    errors = _validate(index)

    assert any("forbidden medical/therapy positioning: therapeutic" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_absolute_local_paths() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["summary"] = "/" + "Users/example/Downloads/source.pdf"
    sources[0] = first

    errors = _validate(index)

    assert any("forbidden local path" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_credential_like_urls() -> None:
    index = _index()
    basis = index["research_basis"]
    assert isinstance(basis, list)
    first = dict(basis[0])
    amz_credential = "X-" + "Amz-" + "Credential"
    first["url"] = f"https://example.test/file.pdf?{amz_credential}=abcdefghijklmnop"
    basis[0] = first

    errors = _validate(index)

    assert any("credential-like token" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_arbitrary_research_https_url() -> None:
    index = _index()
    basis = index["research_basis"]
    assert isinstance(basis, list)
    first = dict(basis[0])
    first["url"] = "https://example.test/source"
    basis[0] = first

    errors = _validate(index)

    assert any(
        "sep_socrates.url must be https://plato.stanford.edu/entries/socrates/" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_missing_research_boundary_note() -> None:
    index = _index()
    basis = index["research_basis"]
    assert isinstance(basis, list)
    first = dict(basis[0])
    del first["boundary_note"]
    basis[0] = first

    errors = _validate(index)

    assert any("sep_socrates missing required keys: ['boundary_note']" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_duplicate_research_id() -> None:
    index = _index()
    basis = index["research_basis"]
    assert isinstance(basis, list)
    duplicate = dict(basis[1])
    duplicate["id"] = basis[0]["id"]
    basis[1] = duplicate

    errors = _validate(index)

    assert any("research_basis ids must be unique" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_runtime_flag_activation() -> None:
    index = _index()
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    flags = dict(first["runtime_flags"])
    flags["cache_read_allowed"] = True
    first["runtime_flags"] = flags
    sources[0] = first

    errors = _validate(index)

    assert any("cache_read_allowed must be false" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_runtime_flag_const_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    sources = properties["sources"]
    assert isinstance(sources, dict)
    items = sources["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    runtime_flags = item_properties["runtime_flags"]
    assert isinstance(runtime_flags, dict)
    runtime_properties = runtime_flags["properties"]
    assert isinstance(runtime_properties, dict)
    cache_read = runtime_properties["cache_read_allowed"]
    assert isinstance(cache_read, dict)
    del cache_read["const"]

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.sources.items.properties.runtime_flags.properties."
        "cache_read_allowed.const must be False" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_sources_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    sources = properties["sources"]
    assert isinstance(sources, dict)
    sources["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema sources.type must be array" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_source_scalar_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    sources = properties["sources"]
    assert isinstance(sources, dict)
    items = sources["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    title = item_properties["title"]
    assert isinstance(title, dict)
    title["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.sources.items.properties.title.type must be string" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_runtime_flags_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    sources = properties["sources"]
    assert isinstance(sources, dict)
    items = sources["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    runtime_flags = item_properties["runtime_flags"]
    assert isinstance(runtime_flags, dict)
    runtime_flags["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema runtime_flags.type must be object" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_runtime_flag_boolean_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    sources = properties["sources"]
    assert isinstance(sources, dict)
    items = sources["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    runtime_flags = item_properties["runtime_flags"]
    assert isinstance(runtime_flags, dict)
    runtime_properties = runtime_flags["properties"]
    assert isinstance(runtime_properties, dict)
    cache_read = runtime_properties["cache_read_allowed"]
    assert isinstance(cache_read, dict)
    cache_read["type"] = "string"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.sources.items.properties.runtime_flags.properties."
        "cache_read_allowed.type must be boolean" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_top_level_const_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    runtime_allowed = properties["runtime_allowed"]
    assert isinstance(runtime_allowed, dict)
    runtime_allowed["type"] = "string"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.runtime_allowed.type must be boolean" in error for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_semantic_markers_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    semantic_markers = properties["semantic_cache_markers"]
    assert isinstance(semantic_markers, dict)
    semantic_markers["type"] = "array"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema semantic_cache_markers.type must be object" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_semantic_marker_boolean_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    semantic_markers = properties["semantic_cache_markers"]
    assert isinstance(semantic_markers, dict)
    marker_properties = semantic_markers["properties"]
    assert isinstance(marker_properties, dict)
    runtime_allowed_false = marker_properties["runtime_allowed_false"]
    assert isinstance(runtime_allowed_false, dict)
    runtime_allowed_false["type"] = "string"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.semantic_cache_markers.properties.runtime_allowed_false.type "
        "must be boolean" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_source_policy_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    source_policy = properties["source_policy"]
    assert isinstance(source_policy, dict)
    source_policy["type"] = "array"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema source_policy.type must be object" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_source_policy_value_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    source_policy = properties["source_policy"]
    assert isinstance(source_policy, dict)
    policy_properties = source_policy["properties"]
    assert isinstance(policy_properties, dict)
    authority = policy_properties["authority"]
    assert isinstance(authority, dict)
    authority["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.source_policy.properties.authority.type must be string" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_research_basis_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    research_basis = properties["research_basis"]
    assert isinstance(research_basis, dict)
    research_basis["type"] = "object"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema research_basis.type must be array" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_research_basis_item_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    research_basis = properties["research_basis"]
    assert isinstance(research_basis, dict)
    items = research_basis["items"]
    assert isinstance(items, dict)
    items["type"] = "array"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema research_basis.items.type must be object" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_research_basis_use_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    research_basis = properties["research_basis"]
    assert isinstance(research_basis, dict)
    items = research_basis["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    use = item_properties["use"]
    assert isinstance(use, dict)
    use["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.research_basis.items.properties.use.type must be string" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_research_basis_cardinality_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    research_basis = properties["research_basis"]
    assert isinstance(research_basis, dict)
    del research_basis["maxItems"]

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema research_basis.maxItems must be 6" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_repo_truth_link_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    repo_truth_links = properties["repo_truth_links"]
    assert isinstance(repo_truth_links, dict)
    items = repo_truth_links["items"]
    assert isinstance(items, dict)
    items["type"] = "number"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema repo_truth_links.items.type must be string" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_schema_source_array_item_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    sources = properties["sources"]
    assert isinstance(sources, dict)
    items = sources["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    theme_families = item_properties["theme_families"]
    assert isinstance(theme_families, dict)
    theme_items = theme_families["items"]
    assert isinstance(theme_items, dict)
    theme_items["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema sources.items.properties.theme_families.items.type must be string" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_research_url_type_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    research_basis = properties["research_basis"]
    assert isinstance(research_basis, dict)
    items = research_basis["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    url = item_properties["url"]
    assert isinstance(url, dict)
    url["type"] = "integer"

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema properties.research_basis.items.properties.url.type must be string" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_research_url_format_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    research_basis = properties["research_basis"]
    assert isinstance(research_basis, dict)
    items = research_basis["items"]
    assert isinstance(items, dict)
    item_properties = items["properties"]
    assert isinstance(item_properties, dict)
    url = item_properties["url"]
    assert isinstance(url, dict)
    del url["format"]

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any(
        "schema research_basis.items.properties.url.format must be uri" in error for error in errors
    )


def test_philosophy_source_corpus_index_rejects_schema_out_of_scope_cardinality_drift() -> None:
    schema = _schema()
    properties = schema["properties"]
    assert isinstance(properties, dict)
    out_of_scope_paths = properties["out_of_scope_paths"]
    assert isinstance(out_of_scope_paths, dict)
    out_of_scope_paths["minItems"] = 8

    errors = _validate(schema_text=json.dumps(schema, ensure_ascii=False, indent=2) + "\n")

    assert any("schema out_of_scope_paths.minItems must be 14" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_roadmap_marker_drift() -> None:
    roadmap_text = _read(DEFAULT_ROADMAP).replace(
        "SEMANTIC_CACHE_ALLOWED_RUNTIME: false",
        "SEMANTIC_CACHE_ALLOWED_RUNTIME: true",
    )

    errors = _validate(roadmap_text=roadmap_text)

    assert any("SEMANTIC_CACHE_ALLOWED_RUNTIME must be false" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_runtime_touched_paths() -> None:
    errors = validate_touched_paths(["core/insight/philosophical_runtime.py"])

    assert errors == [
        "core/insight/philosophical_runtime.py: PR-5 is docs/governance/test-only; "
        "forbidden runtime path core/insight/**"
    ]


def test_philosophy_source_corpus_index_accepts_pr5_governance_paths() -> None:
    errors = validate_touched_paths(
        [
            REL_INDEX,
            REL_SCHEMA,
            "scripts/ci/check_philosophy_source_corpus_index.py",
            "tests/test_philosophy_source_corpus_index.py",
        ]
    )

    assert errors == []


def test_philosophy_source_corpus_index_rejects_repo_truth_link_drift() -> None:
    index = _index()
    index["repo_truth_links"] = ["docs/roadmap/BACKLOG_LEDGER.md"]

    errors = _validate(index)

    assert any(
        "repo_truth_links must match the PR-5 canonical repo truth list" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_non_string_repo_truth_link() -> None:
    index = _index()
    links = index["repo_truth_links"]
    assert isinstance(links, list)
    links.append(42)

    errors = _validate(index)

    assert any("repo_truth_links must contain only strings" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_out_of_scope_path_drift() -> None:
    index = _index()
    paths = list(corpus.FORBIDDEN_RUNTIME_PATHS)
    paths.remove("providers/**")
    index["out_of_scope_paths"] = paths

    errors = _validate(index)

    assert any(
        "out_of_scope_paths must match the PR-5 no-runtime path boundary" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_rejects_non_string_out_of_scope_path() -> None:
    index = _index()
    paths = index["out_of_scope_paths"]
    assert isinstance(paths, list)
    paths.append(42)

    errors = _validate(index)

    assert any("out_of_scope_paths must contain only strings" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_non_object_research_basis_item() -> None:
    index = _index()
    basis = index["research_basis"]
    assert isinstance(basis, list)
    basis.append(42)

    errors = _validate(index)

    assert any("research_basis[6] must be an object" in error for error in errors)
    assert any("research_basis must contain 6 sources" in error for error in errors)


def test_philosophy_source_corpus_index_rejects_source_policy_constant_drift() -> None:
    index = _index()
    policy = index["source_policy"]
    assert isinstance(policy, dict)
    policy["authority"] = "pdf_is_runtime_truth"

    errors = _validate(index)

    assert any(
        "source_policy.authority must be operator_pdf_design_evidence_repo_truth_wins" in error
        for error in errors
    )


def test_philosophy_source_corpus_index_scans_touched_artifact_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / REL_INDEX
    artifact.parent.mkdir(parents=True)
    artifact.write_text("leak=" + "/" + "tmp/source.pdf\n", encoding="utf-8")
    monkeypatch.setattr(corpus, "REPO_ROOT", tmp_path)

    errors = validate_file_contents([REL_INDEX])

    assert any("forbidden local path" in error for error in errors)


def test_philosophy_source_corpus_index_skips_binary_touched_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "docs" / "evidence" / "figure.png"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"\x89PNG\r\n\x1a\n\x00binary")
    monkeypatch.setattr(corpus, "REPO_ROOT", tmp_path)

    errors = validate_file_contents(["docs/evidence/figure.png"])

    assert errors == []


def test_philosophy_source_corpus_index_scans_utf16_text_artifact_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / REL_INDEX
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(("leak=" + "/" + "tmp/source.pdf\n").encode("utf-16"))
    monkeypatch.setattr(corpus, "REPO_ROOT", tmp_path)

    errors = validate_file_contents([REL_INDEX])

    assert any("forbidden local path" in error for error in errors)


def test_philosophy_source_corpus_index_phase1_docs_gate_rejects_page_count_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_source_corpus_companions(tmp_path)
    index_path = tmp_path / REL_INDEX
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert isinstance(index, dict)
    sources = index["sources"]
    assert isinstance(sources, list)
    first = dict(sources[0])
    first["page_count"] = 23
    sources[0] = first
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(docs_phase1, "REPO_ROOT", tmp_path)

    errors = docs_phase1.check_docs_phase1_guards(markdown_files=[REL_INDEX])

    assert any(
        error.startswith(f"{REL_INDEX}: analytic_linguistic_audit.page_count must be 22")
        for error in errors
    )

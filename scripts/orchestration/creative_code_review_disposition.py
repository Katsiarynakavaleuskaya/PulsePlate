"""Local PR-5 review-disposition integration for governed creative-code.

The CLI composes sanitized PR review context or read-only fixture payloads into
local advisory artifacts. It never calls GitHub, edits fixed mapping, resolves
threads, creates branches, opens PRs, or claims merge readiness.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, cast

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.creative_code_review_disposition_contract import (
    CreativeCodeReviewDispositionContractError,
    build_creative_code_repair_launch_packet,
    build_creative_code_review_disposition_packet,
    build_creative_code_review_feedback_record,
    read_json_object,
    reject_unsafe_review_value,
    validate_creative_code_repair_launch_packet,
    validate_creative_code_review_disposition_packet,
    validate_creative_code_review_feedback_record,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATIVE_CODE_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code"
REVIEW_DISPOSITION_ROOT = CREATIVE_CODE_ROOT / "review_disposition"

COLLECTION_TYPE = "creative_code_review_feedback_collection"
SUCCESS_OUTPUT = "PASS: creative-code review disposition complete"
RAW_GITHUB_BODY_FIELDS = frozenset({"raw_body", "body", "body_text", "body_html", "body_markdown"})


class CreativeCodeReviewDispositionError(ValueError):
    """Raised when PR-5 review-disposition CLI input is unsafe or malformed."""


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    components: list[Path] = []
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodeReviewDispositionError(f"{label} must not traverse symlinks.")


def _ensure_artifact_root() -> Path:
    _reject_symlink_components(REVIEW_DISPOSITION_ROOT, label="review disposition root")
    REVIEW_DISPOSITION_ROOT.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(REVIEW_DISPOSITION_ROOT, label="review disposition root")
    root = REVIEW_DISPOSITION_ROOT.resolve(strict=True)
    if not root.is_dir():
        raise CreativeCodeReviewDispositionError("review disposition root must be a directory.")
    return root


def _resolve_output_path(raw_path: Path, *, allowed_suffixes: tuple[str, ...] = (".json",)) -> Path:
    root = _ensure_artifact_root()
    path = raw_path if raw_path.is_absolute() else REVIEW_DISPOSITION_ROOT / raw_path
    if path.is_absolute() and not _is_relative_to(path.resolve(strict=False), root):
        raise CreativeCodeReviewDispositionError("output path must stay under review artifacts.")
    _reject_symlink_components(path.parent, label="output parent")
    candidate_parent = path.parent.resolve(strict=False)
    if not _is_relative_to(candidate_parent, root):
        raise CreativeCodeReviewDispositionError("output path must stay under review artifacts.")
    if path.suffix not in allowed_suffixes:
        suffixes = ", ".join(allowed_suffixes)
        raise CreativeCodeReviewDispositionError(f"output path suffix must be one of: {suffixes}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_components(path.parent, label="output parent")
    return path.parent.resolve(strict=True) / path.name


def _write_json(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    output = _resolve_output_path(path)
    reject_unsafe_review_value(payload, label="output")
    if output.is_symlink():
        raise CreativeCodeReviewDispositionError("output path must not be a symlink.")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(payload, temp_file, ensure_ascii=False, indent=2, sort_keys=True)
            temp_file.write("\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _write_text(path: Path, content: str, *, allowed_suffixes: tuple[str, ...]) -> None:
    output = _resolve_output_path(path, allowed_suffixes=allowed_suffixes)
    reject_unsafe_review_value(content, label="output")
    if output.is_symlink():
        raise CreativeCodeReviewDispositionError("output path must not be a symlink.")
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, output)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _safe_source_id(prefix: str, value: Any) -> str:
    raw = str(value if value not in (None, "") else "unknown")
    safe = "".join(
        character if character.isalnum() or character in "._:-" else "-" for character in raw
    )
    safe = safe.strip("-._:") or "unknown"
    return f"{prefix}:{safe}"[:128]


def _context_source(context: dict[str, Any], *, source_kind: str, source_id: str) -> dict[str, Any]:
    raw_query = context.get("query")
    raw_pr = context.get("pr")
    query: dict[str, Any] = raw_query if isinstance(raw_query, dict) else {}
    pr: dict[str, Any] = raw_pr if isinstance(raw_pr, dict) else {}
    repo = str(query.get("repo") or "")
    pr_number = query.get("pr_number") or pr.get("number")
    return {
        "source_kind": source_kind,
        "source_id": source_id,
        "source_fingerprint": cast(str, fingerprint_payload(context)),
        "context_path": None,
        "repository": repo or None,
        "pr_number": pr_number if isinstance(pr_number, int) else None,
    }


def _record_source_fingerprint(payload: dict[str, Any]) -> str:
    return cast(str, fingerprint_payload(payload))


def _safe_head_sha(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 40:
        return None
    if all(character in "0123456789abcdef" for character in value):
        return value
    return None


def records_from_pr_review_context(
    context: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build sanitized feedback records from existing pr_review_context output."""

    source_context = _context_source(
        context,
        source_kind="pr_review_context",
        source_id=_safe_source_id("pr-review-context", context.get("generated_at_utc")),
    )
    raw_query = context.get("query")
    raw_pr = context.get("pr")
    query: dict[str, Any] = raw_query if isinstance(raw_query, dict) else {}
    pr: dict[str, Any] = raw_pr if isinstance(raw_pr, dict) else {}
    repository = source_context["repository"]
    pr_number = source_context["pr_number"]
    head_sha = _safe_head_sha(pr.get("head_sha")) or _safe_head_sha(query.get("head_ref"))
    records: list[dict[str, Any]] = []

    raw_warnings = context.get("warnings")
    warnings: list[Any] = raw_warnings if isinstance(raw_warnings, list) else []
    for index, warning in enumerate(warnings):
        text = str(warning)
        records.append(
            build_creative_code_review_feedback_record(
                source_kind="pr_review_context",
                source_id=_safe_source_id("context-warning", index),
                source_fingerprint=_record_source_fingerprint({"warning": text, "index": index}),
                excerpt=text,
                feedback_kind="context_warning",
                severity="note",
                repository=cast(str | None, repository),
                pr_number=cast(int | None, pr_number),
                head_sha=head_sha,
            )
        )

    statuses = context.get("review_source_status")
    if isinstance(statuses, list):
        for index, status in enumerate(statuses):
            if not isinstance(status, dict):
                continue
            source_name = str(status.get("source") or "unknown")
            status_name = str(status.get("status") or "unknown")
            reason = str(status.get("reason") or "")
            blocking = bool(status.get("blocking"))
            degraded = bool(status.get("source_degraded"))
            if not blocking and not degraded and status_name == "available":
                continue
            excerpt = f"{source_name} {status_name} {reason}".strip()
            records.append(
                build_creative_code_review_feedback_record(
                    source_kind="pr_review_context",
                    source_id=_safe_source_id("review-source", f"{index}-{source_name}"),
                    source_fingerprint=_record_source_fingerprint(
                        {
                            "source": source_name,
                            "status": status_name,
                            "blocking": blocking,
                            "degraded": degraded,
                        }
                    ),
                    excerpt=excerpt,
                    feedback_kind="review_source_status",
                    severity="high" if blocking else "note",
                    repository=cast(str | None, repository),
                    pr_number=cast(int | None, pr_number),
                    head_sha=head_sha,
                )
            )

    return source_context, records


def _github_items(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    groups = (
        ("github_review_comment", "review_comments"),
        ("github_review", "reviews"),
        ("issue_comment", "issue_comments"),
    )
    items: list[tuple[str, dict[str, Any]]] = []
    for source, key in groups:
        raw_items = payload.get(key, [])
        if not isinstance(raw_items, list):
            raise CreativeCodeReviewDispositionError(f"{key} must be an array.")
        for item in raw_items:
            if not isinstance(item, dict):
                raise CreativeCodeReviewDispositionError(f"{key} entries must be objects.")
            if RAW_GITHUB_BODY_FIELDS.intersection(item):
                raise CreativeCodeReviewDispositionError(
                    "raw GitHub body fields are not allowed in fixtures."
                )
            items.append((source, item))
    return items


def _reject_raw_github_body_fields(value: Any, *, label: str) -> None:
    if isinstance(value, dict):
        if RAW_GITHUB_BODY_FIELDS.intersection(value):
            raise CreativeCodeReviewDispositionError(
                f"{label} contains raw GitHub body fields, which are not allowed in fixtures."
            )
        for key, item in value.items():
            _reject_raw_github_body_fields(item, label=f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_raw_github_body_fields(item, label=f"{label}[{index}]")


def records_from_github_fixture(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build sanitized feedback records from a read-only GitHub fixture."""

    _reject_raw_github_body_fields(payload, label="github_fixture")
    repository = payload.get("repository")
    pr_number = payload.get("pr_number")
    head_sha = payload.get("head_sha")
    source_context = {
        "source_kind": "github_fixture",
        "source_id": _safe_source_id("github-fixture", pr_number),
        "source_fingerprint": fingerprint_payload(
            {
                "repository": repository,
                "pr_number": pr_number,
                "head_sha": head_sha,
                "item_count": len(_github_items(payload)),
            }
        ),
        "context_path": None,
        "repository": repository,
        "pr_number": pr_number,
    }
    records: list[dict[str, Any]] = []
    for index, (source, item) in enumerate(_github_items(payload)):
        body = item.get("body_excerpt_sanitized", item.get("summary_sanitized", ""))
        if not isinstance(body, str) or not body.strip():
            raise CreativeCodeReviewDispositionError(
                "GitHub fixture item must include body_excerpt_sanitized or summary_sanitized."
            )
        source_id = _safe_source_id(source, item.get("id", index))
        source_fingerprint = _record_source_fingerprint(
            {
                "source": source,
                "id": item.get("id"),
                "path": item.get("path"),
                "line": item.get("line"),
                "body_fingerprint": fingerprint_payload({"body_excerpt": body}),
            }
        )
        records.append(
            build_creative_code_review_feedback_record(
                source_kind="github_fixture",
                source_id=source_id,
                source_fingerprint=source_fingerprint,
                excerpt=body,
                feedback_kind=str(item.get("feedback_kind") or "review_thread"),
                severity=str(item.get("severity") or "note"),
                source_url=item.get("html_url") if isinstance(item.get("html_url"), str) else None,
                repository=repository if isinstance(repository, str) else None,
                pr_number=pr_number if isinstance(pr_number, int) else None,
                head_sha=head_sha if isinstance(head_sha, str) else None,
                path=item.get("path") if isinstance(item.get("path"), str) else None,
                line=item.get("line") if isinstance(item.get("line"), int) else None,
                side=str(item.get("side") or "unknown").lower(),
            )
        )
    return source_context, records


def build_collection(
    *,
    source_context: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_type": COLLECTION_TYPE,
        "source_context": source_context,
        "feedback_records": [
            validate_creative_code_review_feedback_record(record) for record in records
        ],
        "sanitized": True,
    }


def read_collection(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = read_json_object(path)
    if payload.get("artifact_type") == COLLECTION_TYPE:
        source_context = payload.get("source_context")
        records = payload.get("feedback_records")
        if not isinstance(source_context, dict) or not isinstance(records, list):
            raise CreativeCodeReviewDispositionError("collection shape is invalid.")
        return source_context, [
            validate_creative_code_review_feedback_record(record) for record in records
        ]
    if payload.get("packet_type") == "creative_code_review_disposition_packet":
        packet = validate_creative_code_review_disposition_packet(payload)
        return packet["source_context"], packet["feedback_records"]
    if payload.get("record_type") == "creative_code_review_feedback_record":
        record = validate_creative_code_review_feedback_record(payload)
        return {
            "source_kind": record["source"]["source_kind"],
            "source_id": record["source"]["source_id"],
            "source_fingerprint": record["fingerprints"]["source_fingerprint"],
            "context_path": None,
            "repository": record["source"]["repository"],
            "pr_number": record["source"]["pr_number"],
        }, [record]
    raise CreativeCodeReviewDispositionError("input must be a collection, packet, or record.")


def command_collect(args: argparse.Namespace) -> int:
    if args.review_context:
        context = read_json_object(args.review_context)
        source_context, records = records_from_pr_review_context(context)
    elif args.github_fixture:
        payload = read_json_object(args.github_fixture)
        source_context, records = records_from_github_fixture(payload)
    else:
        raise CreativeCodeReviewDispositionError(
            "collect requires --review-context or --github-fixture."
        )
    collection = build_collection(source_context=source_context, records=records)
    _write_json(Path(args.output) if args.output else None, collection)
    return 0


def command_classify(args: argparse.Namespace) -> int:
    source_context, records = read_collection(Path(args.input))
    packet = build_creative_code_review_disposition_packet(
        feedback_records=records,
        source_context=source_context,
        expected_head_sha=args.expected_head_sha,
        actual_head_sha=args.actual_head_sha,
        classify=True,
    )
    _write_json(Path(args.output) if args.output else None, packet)
    return 0


def command_prepare_launch(args: argparse.Namespace) -> int:
    packet = validate_creative_code_review_disposition_packet(
        read_json_object(args.disposition_packet)
    )
    launch = build_creative_code_repair_launch_packet(packet)
    _write_json(Path(args.output) if args.output else None, launch)
    return 0


def command_summarize(args: argparse.Namespace) -> int:
    packet = validate_creative_code_review_disposition_packet(
        read_json_object(args.disposition_packet)
    )
    summary = packet["summary"]
    lines = [
        "# Creative-Code Review Disposition Summary",
        "",
        "Local-only advisory output. Not fixed-mapping, review-thread, or merge-readiness evidence.",
        "",
        f"- Packet: {packet['packet_id']}",
        f"- Records: {summary['records_total']}",
        f"- Repair candidates: {summary['repair_candidates']}",
        f"- Not-a-bug candidates: {summary['not_actionable']}",
        f"- Deferred candidates: {summary['deferred_candidates']}",
        f"- Head SHA drift blocks: {summary['blocked_by_head_drift']}",
        f"- Highest repair priority: {summary['highest_repair_priority']}",
    ]
    output = "\n".join(lines) + "\n"
    reject_unsafe_review_value(output, label="summary")
    if args.output:
        _write_text(Path(args.output), output, allowed_suffixes=(".md", ".txt"))
    else:
        print(output, end="")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect")
    source_group = collect.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--review-context", type=Path)
    source_group.add_argument("--github-fixture", type=Path)
    collect.add_argument("--output", help="JSON output path under review-disposition artifacts")
    collect.set_defaults(func=command_collect)

    classify = subparsers.add_parser("classify")
    classify.add_argument("--input", required=True)
    classify.add_argument("--output")
    classify.add_argument("--expected-head-sha")
    classify.add_argument("--actual-head-sha")
    classify.set_defaults(func=command_classify)

    prepare = subparsers.add_parser("prepare-launch")
    prepare.add_argument("--disposition-packet", required=True)
    prepare.add_argument("--output")
    prepare.set_defaults(func=command_prepare_launch)

    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--disposition-packet", required=True)
    summarize.add_argument("--output")
    summarize.set_defaults(func=command_summarize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        return cast(int, args.func(args))
    except (
        CreativeCodeReviewDispositionContractError,
        CreativeCodeReviewDispositionError,
    ) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

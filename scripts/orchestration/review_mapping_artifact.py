"""Canonical Fixed in Commit Mapping artifact: repo file as source of truth."""

from __future__ import annotations

import os
import re
import urllib.parse
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from scripts.orchestration.pr_review_evidence import (
    UNAVAILABLE_REVIEW_REF_CAUSE,
    ReviewEvidenceError,
    parse_embedded_review_seal,
    unavailable_review_ref_fingerprint,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "docs" / "review"


def _review_dir() -> Path:
    """Return review dir; override via REVIEW_MAPPING_ARTIFACT_DIR for tests only."""
    override = os.environ.get("REVIEW_MAPPING_ARTIFACT_DIR")
    if not override:
        return REVIEW_DIR
    base = Path(override).resolve()
    if not base.is_dir():
        raise RuntimeError(f"REVIEW_MAPPING_ARTIFACT_DIR must be an existing directory: {base}")
    return base


DISCUSSION_THREAD_PASS_HEADING = "## Discussion Thread Pass"  # nosec B105: doc heading (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
# Canonical artifact uses ##; PR-body mirror/fallback may use ### (AGENTS.md)
FIXED_MAPPING_HEADINGS = ("## Fixed in Commit Mapping", "### Fixed in Commit Mapping")
PRE_CLOSEOUT_MARKER = "phase2-pre-closeout: final-security-pending"

CHECKBOX_DISCUSSION_PASS = "- [x] Discussion-thread pass completed"  # nosec B105: checkbox label (remove-by: 2026-09-30, ref: PR-main-nightly-nosec-ttl)
CHECKBOX_FIXED_MAPPING = "- [x] Fixed in commit mapping completed"

MAPPING_LINE_RE = re.compile(r"^\s*-\s+(https://github\.com/\S+)\s+->\s+([0-9a-f]{7,40})\s*$")
THREAD_LINE_RE = re.compile(r"^\s*-\s+(https://github\.com/\S+)\s*$")
NO_ACTIONABLE_LINE = "- No actionable review comments"
# Disposition/proof lines allowed in section (disposition guard format)
DETAIL_PREFIXES = (
    "Disposition:",
    "Commit:",
    "Evidence:",
    "Backlog:",
    "Reason:",
    "Fingerprint:",
    "Cause:",
    "Material-Digest:",
    "Verified-Fix:",
)
VALID_DISPOSITIONS = frozenset({"FIXED", "NOT-A-BUG", "DEFERRED"})
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
FULL_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REVIEW_SEAL_VERSION_RE = re.compile(r"(?m)^Review-Seal-Version:\s*(\S+)\s*$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MARKDOWN_FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
MARKDOWN_INDENTED_CODE_RE = re.compile(r"^(?: {4}| {0,3}\t)")
MARKDOWN_HEADING_PREFIX_RE = re.compile(r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+|$)")
MARKDOWN_HEADING_RE = re.compile(
    r"^ {0,3}(?P<marks>#{1,6})(?:[ \t]+(?P<title>\S(?:.*\S)?)?[ \t]*|)$"
)
MARKDOWN_RAW_HTML_BLOCK_TAG_RE = re.compile(
    r"^ {0,3}</?(?P<tag>"
    r"address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|"
    r"dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|"
    r"frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|"
    r"nav|noframes|ol|optgroup|option|p|param|pre|script|search|section|style|summary|"
    r"table|tbody|td|textarea|tfoot|th|thead|title|tr|track|ul)(?=[ \t/>]|$)",
    re.IGNORECASE,
)
MARKDOWN_RAW_HTML_STANDALONE_TAG_RE = re.compile(
    r"^ {0,3}(?:"
    r"</[A-Za-z][A-Za-z0-9-]*[ \t]*>"
    r"|<[A-Za-z][A-Za-z0-9-]*(?:[ \t]+[^<>]*)?[ \t]*/?>"
    r")[ \t]*$",
)
MARKDOWN_RAW_HTML_PERSISTENT_TAGS = frozenset({"pre", "script", "style", "textarea"})


@dataclass(frozen=True)
class RenderedMarkdownLine:
    """One source line with Markdown comments and fences classified."""

    source_offset: int
    raw_line: str
    visible_line: str
    starts_in_html_comment: bool
    source_content_starts_visible: bool
    source_heading_level: int | None


def _visible_line_without_html_comments(
    line: str,
    in_html_comment: bool,
) -> tuple[str, bool]:
    """Return rendered line content and the next multiline-comment state."""

    visible_parts: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_html_comment:
            comment_end = line.find("-->", cursor)
            if comment_end < 0:
                return "".join(visible_parts), True
            in_html_comment = False
            cursor = comment_end + 3
            continue
        comment_start = line.find("<!--", cursor)
        if comment_start < 0:
            visible_parts.append(line[cursor:])
            break
        visible_parts.append(line[cursor:comment_start])
        visible_parts.append(" ")
        in_html_comment = True
        cursor = comment_start + 4
    return "".join(visible_parts), in_html_comment


def _raw_html_block_start(line: str) -> tuple[str, bool]:
    """Return the terminator or blank-line mode for a raw HTML block."""

    stripped = line.lstrip(" ")
    if len(line) - len(stripped) > 3 or stripped.startswith("<!--"):
        return "", False
    if match := MARKDOWN_RAW_HTML_BLOCK_TAG_RE.match(line):
        tag = match.group("tag").casefold()
        if not stripped.startswith("</") and tag in MARKDOWN_RAW_HTML_PERSISTENT_TAGS:
            return f"</{tag}>", False
        return "", True
    if MARKDOWN_RAW_HTML_STANDALONE_TAG_RE.fullmatch(line):
        return "", True
    if stripped.startswith("<?"):
        return "?>", False
    if stripped.startswith("<![CDATA["):
        return "]]>", False
    if re.match(r"^<![A-Z]", stripped):
        return ">", False
    return "", False


def iter_unfenced_markdown_lines(text: str) -> Iterator[RenderedMarkdownLine]:
    """Yield classified source lines outside fenced code."""

    offset = 0
    in_html_comment = False
    fence_char = ""
    fence_length = 0
    raw_html_terminator = ""
    raw_html_until_blank = False
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if raw_html_terminator:
            if raw_html_terminator in line.casefold():
                raw_html_terminator = ""
            offset += len(raw_line)
            continue
        if raw_html_until_blank:
            if not line.strip():
                raw_html_until_blank = False
            offset += len(raw_line)
            continue
        starts_in_html_comment = in_html_comment
        if fence_char:
            closing_fence = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_char)}{{{fence_length},}}[ \t]*",
                line,
            )
            if closing_fence:
                fence_char = ""
                fence_length = 0
            offset += len(raw_line)
            continue

        indented_code = not starts_in_html_comment and MARKDOWN_INDENTED_CODE_RE.match(line)
        fence_open = (
            None if starts_in_html_comment or indented_code else MARKDOWN_FENCE_OPEN_RE.match(line)
        )
        if fence_open and fence_open.group("fence")[0] == "`" and "`" in line[fence_open.end() :]:
            fence_open = None
        if fence_open:
            fence = fence_open.group("fence")
            fence_char = fence[0]
            fence_length = len(fence)
            offset += len(raw_line)
            continue

        if not starts_in_html_comment and not indented_code:
            terminator, until_blank = _raw_html_block_start(line)
            if terminator or until_blank:
                if terminator and terminator not in line.casefold()[1:]:
                    raw_html_terminator = terminator
                raw_html_until_blank = until_blank
                offset += len(raw_line)
                continue

        if indented_code:
            visible_line = ""
        else:
            visible_line, in_html_comment = _visible_line_without_html_comments(
                line,
                in_html_comment,
            )
        heading_prefix = (
            None
            if starts_in_html_comment or indented_code
            else MARKDOWN_HEADING_PREFIX_RE.match(line)
        )
        yield RenderedMarkdownLine(
            source_offset=offset,
            raw_line=raw_line,
            visible_line=visible_line,
            starts_in_html_comment=starts_in_html_comment,
            source_content_starts_visible=(
                not starts_in_html_comment
                and not indented_code
                and not line.lstrip(" \t").startswith("<!--")
            ),
            source_heading_level=(len(heading_prefix.group("marks")) if heading_prefix else None),
        )
        offset += len(raw_line)


def markdown_heading_level(line: RenderedMarkdownLine) -> int | None:
    """Return a rendered CommonMark ATX heading level, or None."""

    match = MARKDOWN_HEADING_RE.fullmatch(line.visible_line)
    if (
        match is None
        or line.source_heading_level is None
        or len(match.group("marks")) != line.source_heading_level
    ):
        return None
    return line.source_heading_level


def is_rendered_markdown_heading(
    line: RenderedMarkdownLine,
    *,
    level: int,
    title: str,
) -> bool:
    """Return whether one visible line is the exact rendered heading."""

    match = MARKDOWN_HEADING_RE.fullmatch(line.visible_line)
    normalized_title = re.sub(r"[ \t]+", " ", title.strip())
    return bool(
        match
        and markdown_heading_level(line) == level
        and match.group("title") is not None
        and re.sub(r"[ \t]+", " ", match.group("title").strip()) == normalized_title
    )


def _is_valid_git_branch_ref(ref: str) -> bool:
    """Validate the branch-name subset required by a GitHub PR head ref."""

    forbidden = " ~^:?*[\\"
    if (
        not ref
        or ref == "@"
        or ref.startswith(("-", "/"))
        or ref.endswith(("/", "."))
        or ".." in ref
        or "@{" in ref
        or any(ord(character) < 32 or ord(character) == 127 for character in ref)
        or any(character in forbidden for character in ref)
    ):
        return False
    return all(
        segment and not segment.startswith(".") and not segment.endswith(".lock")
        for segment in ref.split("/")
    )


@dataclass(frozen=True)
class CanonicalFingerprintRecord:
    """Canonical mapping evidence reusable by one resolved duplicate thread."""

    fingerprint: str
    cause: str
    material_digest: str
    verified_fix: str
    urls: tuple[str, ...]


def _validate_fixed_mapping_block(
    lines: list[str], *, require_full_shas: bool = False
) -> list[str]:
    """Validate one disposition/proof block inside Fixed in Commit Mapping."""

    errors: list[str] = []
    disposition_values: list[str] = []
    has_sha_mapping = False
    has_url_only_mapping = False
    proof_prefixes: set[str] = set()
    detail_values: dict[str, list[str]] = {}
    commit_values: list[str] = []
    mapped_shas: list[str] = []

    for line in lines:
        if line.startswith("Disposition:"):
            disposition = line.removeprefix("Disposition:").strip()
            if disposition not in VALID_DISPOSITIONS:
                errors.append(
                    f"Invalid Disposition value: {disposition}. "
                    "Expected FIXED, NOT-A-BUG, or DEFERRED."
                )
            disposition_values.append(disposition)
            continue
        matched_detail = next(
            (prefix for prefix in DETAIL_PREFIXES[1:] if line.startswith(prefix)),
            None,
        )
        if matched_detail is not None:
            proof_value = line.removeprefix(matched_detail).strip()
            if not proof_value:
                errors.append(f"{matched_detail} proof value must not be empty.")
                continue
            proof_prefixes.add(matched_detail)
            detail_values.setdefault(matched_detail, []).append(proof_value)
            if matched_detail == "Commit:":
                commit_values.append(proof_value)
            continue
        if mapping_match := MAPPING_LINE_RE.match(line):
            has_sha_mapping = True
            mapped_shas.append(mapping_match.group(2))
            continue
        if THREAD_LINE_RE.match(line):
            has_url_only_mapping = True
            continue
        errors.append(f"Invalid mapping line format in canonical artifact: {line}")

    saw_thread_line = has_sha_mapping or has_url_only_mapping
    if len(disposition_values) > 1:
        errors.append("Fixed in Commit Mapping proof block must contain one Disposition line.")
    if not errors and not saw_thread_line:
        errors.append(
            "Fixed in Commit Mapping proof block must contain at least one '- <url>' "
            "or '- <url> -> <sha>' line."
        )
    if not errors and saw_thread_line and not disposition_values:
        errors.append("Missing 'Disposition:' when review-thread entries are present.")
    if not errors and saw_thread_line and not proof_prefixes:
        errors.append(
            "Missing proof detail (Commit:/Evidence:/Backlog:) when review-thread entries are present."
        )
    if errors or not disposition_values:
        return errors

    disposition = disposition_values[0]
    if disposition == "FIXED":
        uses_mapping_entries_preamble = any(
            value.strip().lower() == "see mapping entries below" for value in commit_values
        )
        if uses_mapping_entries_preamble and has_sha_mapping:
            errors.append(
                "Disposition FIXED with 'Commit: see mapping entries below' requires "
                "a following SHA mapping-only block."
            )
        if not has_sha_mapping:
            errors.append("Disposition FIXED requires '- <url> -> <sha>' mapping lines.")
        if has_url_only_mapping:
            errors.append("Disposition FIXED must not use URL-only review-thread lines.")
        if "Commit:" not in proof_prefixes:
            errors.append("Disposition FIXED requires a 'Commit:' proof line.")
        if "Evidence:" not in proof_prefixes:
            errors.append("Disposition FIXED requires an 'Evidence:' proof line.")
        invalid_commit_values = [
            value
            for value in commit_values
            if not (
                COMMIT_SHA_RE.fullmatch(value)
                or value.strip().lower() == "see mapping entries below"
            )
        ]
        if invalid_commit_values:
            errors.append(
                "Disposition FIXED Commit proof must be a commit SHA or "
                "'see mapping entries below'."
            )
        if require_full_shas:
            abbreviated = [
                sha
                for sha in [*mapped_shas, *commit_values]
                if COMMIT_SHA_RE.fullmatch(sha) and not FULL_COMMIT_SHA_RE.fullmatch(sha)
            ]
            if abbreviated:
                errors.append("Review-Seal-Version v1 requires full 40-character FIXED SHAs.")
        commit_shas = {value for value in commit_values if COMMIT_SHA_RE.fullmatch(value)}
        mapped_sha_values = set(mapped_shas)
        if commit_shas and mapped_sha_values - commit_shas:
            errors.append(
                "Disposition FIXED Commit SHA must match mapped SHA entries "
                "or use 'Commit: see mapping entries below'."
            )
    elif disposition == "NOT-A-BUG":
        if has_sha_mapping:
            errors.append("Disposition NOT-A-BUG must use URL-only review-thread lines.")
        if "Evidence:" not in proof_prefixes:
            errors.append("Disposition NOT-A-BUG requires an 'Evidence:' proof line.")
        if "Reason:" not in proof_prefixes:
            errors.append("Disposition NOT-A-BUG requires a 'Reason:' proof line.")
    elif disposition == "DEFERRED":
        if has_sha_mapping:
            errors.append("Disposition DEFERRED must use URL-only review-thread lines.")
        if "Backlog:" not in proof_prefixes:
            errors.append("Disposition DEFERRED requires a 'Backlog:' proof line.")

    fingerprint_fields = {
        "Fingerprint:",
        "Cause:",
        "Material-Digest:",
        "Verified-Fix:",
    }
    present_fingerprint_fields = fingerprint_fields & proof_prefixes
    if present_fingerprint_fields:
        if disposition != "NOT-A-BUG" or present_fingerprint_fields != fingerprint_fields:
            errors.append(
                "Fingerprint evidence is allowed only as one complete NOT-A-BUG v1 record."
            )
        elif any(len(detail_values.get(field, [])) != 1 for field in fingerprint_fields):
            errors.append("Fingerprint evidence fields must each appear exactly once.")
        else:
            fingerprint = detail_values["Fingerprint:"][0]
            cause = detail_values["Cause:"][0]
            material_digest = detail_values["Material-Digest:"][0]
            verified_fix = detail_values["Verified-Fix:"][0]
            if cause != UNAVAILABLE_REVIEW_REF_CAUSE:
                errors.append("Unsupported review fingerprint cause.")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
                errors.append("Fingerprint must use sha256:<64 lowercase hex>.")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", material_digest):
                errors.append("Material-Digest must use sha256:<64 lowercase hex>.")
            if not FULL_COMMIT_SHA_RE.fullmatch(verified_fix):
                errors.append("Verified-Fix must use a full 40-character SHA.")
    return errors


def _block_has_thread_entry(lines: list[str]) -> bool:
    return any(MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line) for line in lines)


def _block_has_sha_mapping(lines: list[str]) -> bool:
    return any(MAPPING_LINE_RE.match(line) for line in lines)


def _block_has_disposition(lines: list[str]) -> bool:
    return any(line.startswith("Disposition:") for line in lines)


def _is_mapping_only_block(lines: list[str]) -> bool:
    if not lines:
        return False
    return all(MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line) for line in lines)


def _is_sha_mapping_only_block(lines: list[str]) -> bool:
    if not lines:
        return False
    return all(MAPPING_LINE_RE.match(line) for line in lines)


def _split_fixed_mapping_blocks(raw_lines: list[str]) -> list[list[str]]:
    """Split physical blocks while preserving legacy mapping-first inline groups."""

    blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in raw_lines:
        if not line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue
        is_thread_line = bool(MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line))
        current_has_thread = _block_has_thread_entry(current_block)
        current_has_disposition = _block_has_disposition(current_block)
        if (
            is_thread_line
            and current_has_thread
            and current_has_disposition
            and not (current_block and current_block[0].startswith("Disposition:"))
        ):
            blocks.append(current_block)
            current_block = [line]
            continue
        if line.startswith("Disposition:") and _block_has_disposition(current_block):
            blocks.append(current_block)
            current_block = [line]
            continue
        current_block.append(line)
    if current_block:
        blocks.append(current_block)
    return blocks


def _is_mapping_entries_preamble(lines: list[str]) -> bool:
    """Return True for PR_2068-style proof preambles that name following mappings."""

    return (
        not _block_has_sha_mapping(lines)
        and any(line == "Commit: see mapping entries below" for line in lines)
        and any(line.startswith("Disposition: FIXED") for line in lines)
        and any(line.startswith("Evidence:") for line in lines)
    )


def _validate_mapping_entries_preamble(
    preamble: list[str],
    following: list[str] | None,
) -> list[str]:
    errors: list[str] = []
    for line in preamble:
        if (
            line.startswith("Disposition:")
            or line.startswith("Commit:")
            or line.startswith("Evidence:")
            or THREAD_LINE_RE.match(line)
        ):
            continue
        errors.append(f"Invalid mapping line format in canonical artifact: {line}")
    evidence_values = [
        line.removeprefix("Evidence:").strip() for line in preamble if line.startswith("Evidence:")
    ]
    if not evidence_values or any(not value for value in evidence_values):
        errors.append("Disposition FIXED requires a non-empty 'Evidence:' proof line.")
    if following is None or not _is_sha_mapping_only_block(following):
        errors.append(
            "Disposition FIXED with 'Commit: see mapping entries below' requires "
            "a following SHA mapping-only block."
        )
        return errors
    mapping_entries = {
        match.group(1): match.group(2)
        for line in following
        if (match := MAPPING_LINE_RE.match(line))
    }
    if not mapping_entries:
        errors.append(
            "Disposition FIXED with 'Commit: see mapping entries below' requires "
            "SHA mapping lines in the following block."
        )
    missing_urls = [
        match.group(1)
        for line in preamble
        if (match := THREAD_LINE_RE.match(line)) and match.group(1) not in mapping_entries
    ]
    if missing_urls:
        errors.append(
            "Disposition FIXED with 'Commit: see mapping entries below' is missing "
            f"following SHA mappings for: {', '.join(missing_urls)}."
        )
    return errors


def mapping_artifact_path(pr_number: int) -> Path:
    """Return canonical review mapping artifact path for a PR number."""
    return _review_dir() / f"PR_{pr_number}_FIXED_MAPPING.md"


def read_mapping_artifact(pr_number: int) -> str:
    """Read canonical review mapping artifact text."""
    path = mapping_artifact_path(pr_number)
    if not path.is_file():
        raise FileNotFoundError(f"Missing canonical review mapping artifact: {path}")
    return path.read_text(encoding="utf-8")


def extract_section(markdown_text: str, heading: str) -> str:
    """
    Extract section body for a markdown heading (## or ###).
    Returns content after heading until next heading at same or higher level.
    """
    lines = markdown_text.splitlines()
    inside = False
    collected: list[str] = []
    heading_level = len(heading) - len(heading.lstrip("#"))

    for line in lines:
        # Normalize multiple spaces (markdown allows "##  Title")
        if re.sub(r"\s+", " ", line.strip()) == re.sub(r"\s+", " ", heading):
            inside = True
            continue

        if inside:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                next_level = len(stripped) - len(stripped.lstrip("#"))
                if next_level <= heading_level:
                    break
            collected.append(line)

    return "\n".join(collected).strip()


def extract_discussion_thread_pass_section(markdown_text: str) -> str:
    """Extract ## Discussion Thread Pass section."""
    return extract_section(markdown_text, DISCUSSION_THREAD_PASS_HEADING)


def extract_fixed_mapping_section(markdown_text: str) -> str:
    """Extract Fixed in Commit Mapping section (## or ###)."""
    for heading in FIXED_MAPPING_HEADINGS:
        section = extract_section(markdown_text, heading)
        if section:
            return section
    return ""


def validate_discussion_thread_pass_section(section: str) -> list[str]:
    """Validate Discussion Thread Pass section; return list of errors."""
    errors: list[str] = []

    if not section:
        errors.append("Missing '## Discussion Thread Pass' section.")
        return errors

    if CHECKBOX_DISCUSSION_PASS not in section:
        errors.append("Missing checkbox: '- [x] Discussion-thread pass completed'.")

    if CHECKBOX_FIXED_MAPPING not in section:
        errors.append("Missing checkbox: '- [x] Fixed in commit mapping completed'.")

    return errors


def validate_fixed_mapping_section(section: str, *, require_full_shas: bool = False) -> list[str]:
    """Validate Fixed in Commit Mapping section; return list of errors."""
    errors: list[str] = []

    if not section:
        errors.append("Missing '## Fixed in Commit Mapping' section.")
        return errors

    raw_lines = [ln.strip() for ln in section.splitlines()]
    non_empty_lines = [line for line in raw_lines if line]
    if not non_empty_lines:
        errors.append("'## Fixed in Commit Mapping' section is empty.")
        return errors

    if NO_ACTIONABLE_LINE in non_empty_lines:
        if len(non_empty_lines) > 1:
            errors.append(
                "Invalid mixed mode: 'No actionable review comments' "
                "cannot appear together with SHA mappings."
            )
        return errors

    blocks = _split_fixed_mapping_blocks(raw_lines)

    saw_thread_line = any(
        MAPPING_LINE_RE.match(line) or THREAD_LINE_RE.match(line)
        for block in blocks
        for line in block
    )
    skip_indexes: set[int] = set()
    for index, block in enumerate(blocks):
        if index in skip_indexes:
            continue
        next_block = blocks[index + 1] if index + 1 < len(blocks) else None
        if _is_mapping_entries_preamble(block):
            errors.extend(_validate_mapping_entries_preamble(block, next_block))
            if next_block is not None and _is_mapping_only_block(next_block):
                skip_indexes.add(index + 1)
            continue
        if (
            _is_mapping_only_block(block)
            and next_block is not None
            and _block_has_disposition(next_block)
        ):
            errors.extend(
                _validate_fixed_mapping_block(
                    [*block, *next_block], require_full_shas=require_full_shas
                )
            )
            skip_indexes.add(index + 1)
            continue
        errors.extend(_validate_fixed_mapping_block(block, require_full_shas=require_full_shas))

    if not saw_thread_line and not errors:
        errors.append(
            "Fixed in Commit Mapping must contain at least one '- <url>' or "
            "'- <url> -> <sha>' line, or '- No actionable review comments'."
        )

    return errors


def validate_mapping_artifact_text(markdown_text: str) -> list[str]:
    """Validate full artifact text; return list of errors."""
    errors: list[str] = []

    discussion_section = extract_discussion_thread_pass_section(markdown_text)
    fixed_mapping_section = extract_fixed_mapping_section(markdown_text)

    version_matches = REVIEW_SEAL_VERSION_RE.findall(markdown_text)
    if len(version_matches) > 1:
        errors.append("Review-Seal-Version must appear at most once.")
    version = version_matches[0] if len(version_matches) == 1 else None
    if version is not None and version != "v1":
        errors.append(f"Unsupported Review-Seal-Version: {version}.")

    errors.extend(validate_discussion_thread_pass_section(discussion_section))
    errors.extend(
        validate_fixed_mapping_section(
            fixed_mapping_section,
            require_full_shas=version == "v1",
        )
    )
    if version == "v1":
        try:
            seal = parse_embedded_review_seal(markdown_text)
            records = parse_canonical_fingerprint_records(
                markdown_text,
                pr_number=seal["pr_number"],
            )
            if any(len(record.urls) != 1 for record in records.values()):
                raise ValueError("canonical fingerprint record must identify exactly one URL")
            if any(
                record.material_digest != seal["material"]["digest"] for record in records.values()
            ):
                raise ValueError("canonical fingerprint record does not match sealed material")
        except (ReviewEvidenceError, ValueError) as exc:
            errors.append(f"Invalid v1 review seal: {exc}")

    return errors


def review_seal_version(markdown_text: str) -> str | None:
    """Return the declared seal version after enforcing marker cardinality."""

    matches = REVIEW_SEAL_VERSION_RE.findall(markdown_text)
    if len(matches) > 1:
        raise ValueError("Review-Seal-Version must appear at most once")
    return matches[0] if matches else None


def parse_canonical_fingerprint_records(
    markdown_text: str, *, pr_number: int
) -> dict[str, CanonicalFingerprintRecord]:
    """Parse and cryptographically recompute canonical v1 fingerprint records."""

    section = extract_fixed_mapping_section(markdown_text)
    records: dict[str, CanonicalFingerprintRecord] = {}
    for block in _split_fixed_mapping_blocks([line.strip() for line in section.splitlines()]):
        values: dict[str, str] = {}
        urls: list[str] = []
        for line in block:
            if match := THREAD_LINE_RE.match(line):
                urls.append(match.group(1))
                continue
            for prefix in (
                "Disposition:",
                "Fingerprint:",
                "Cause:",
                "Material-Digest:",
                "Verified-Fix:",
            ):
                if line.startswith(prefix):
                    if prefix in values:
                        raise ValueError(f"duplicate {prefix} in fingerprint record")
                    values[prefix] = line.removeprefix(prefix).strip()
                    break
        if "Fingerprint:" not in values:
            continue
        required = {
            "Disposition:",
            "Fingerprint:",
            "Cause:",
            "Material-Digest:",
            "Verified-Fix:",
        }
        if set(values) != required or values["Disposition:"] != "NOT-A-BUG" or not urls:
            raise ValueError("canonical fingerprint record is incomplete")
        expected = unavailable_review_ref_fingerprint(
            pr_number=pr_number,
            material_digest=values["Material-Digest:"],
            verified_real_fix_sha=values["Verified-Fix:"],
        )
        fingerprint = values["Fingerprint:"]
        if values["Cause:"] != UNAVAILABLE_REVIEW_REF_CAUSE or fingerprint != expected:
            raise ValueError("canonical fingerprint record does not recompute")
        if fingerprint in records:
            raise ValueError("canonical fingerprint appears more than once")
        records[fingerprint] = CanonicalFingerprintRecord(
            fingerprint=fingerprint,
            cause=values["Cause:"],
            material_digest=values["Material-Digest:"],
            verified_fix=values["Verified-Fix:"],
            urls=tuple(sorted(urls)),
        )
    return records


def parse_fixed_mapping_entries(section: str) -> dict[str, str]:
    """
    Parse review-thread lines.
    Returns {url: sha_or_empty_string}
    """
    entries: dict[str, str] = {}

    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line or line == NO_ACTIONABLE_LINE:
            continue

        match = MAPPING_LINE_RE.match(line)
        if match:
            url, sha = match.groups()
            entries[url] = sha
            continue

        url_only_match = THREAD_LINE_RE.match(line)
        if url_only_match:
            entries[url_only_match.group(1)] = ""

    return entries


def has_no_actionable_marker(section: str) -> bool:
    """True if section contains 'No actionable review comments'."""
    return NO_ACTIONABLE_LINE in section


def render_phase2_body_mirror(pr_number: int, *, repository: str, ref: str) -> str:
    """Render the canonical PR-body mirror block from the artifact source of truth."""

    artifact_text = read_mapping_artifact(pr_number)
    errors = validate_mapping_artifact_text(artifact_text)
    if not errors and review_seal_version(artifact_text) != "v1":
        errors.append("Review-Seal-Version v1 is required before rendering closeout.")
    if errors:
        joined_errors = "; ".join(errors)
        raise RuntimeError(f"Cannot render PR body mirror for PR #{pr_number}: {joined_errors}")

    normalized_repository = repository.strip()
    normalized_ref = ref.strip()
    if not REPOSITORY_RE.fullmatch(normalized_repository):
        raise ValueError("repository must use the canonical owner/name form")
    if not _is_valid_git_branch_ref(normalized_ref):
        raise ValueError("ref must be a valid non-empty Git branch ref")
    encoded_ref = urllib.parse.quote(normalized_ref, safe="/-._~")
    artifact_path = f"docs/review/PR_{pr_number}_FIXED_MAPPING.md"
    artifact_url = f"https://github.com/{normalized_repository}/blob/{encoded_ref}/{artifact_path}"
    return "\n".join(
        [
            DISCUSSION_THREAD_PASS_HEADING,
            CHECKBOX_DISCUSSION_PASS,
            CHECKBOX_FIXED_MAPPING,
            "",
            "### Fixed in Commit Mapping",
            f"- [canonical artifact]({artifact_url})",
        ]
    )


def replace_phase2_body_mirror(
    body: str,
    pr_number: int,
    *,
    repository: str,
    ref: str,
) -> str:
    """Replace exactly one complete Phase2 body block with the canonical mirror."""

    rendered_lines = list(iter_unfenced_markdown_lines(body))
    starts = [
        line
        for line in rendered_lines
        if is_rendered_markdown_heading(
            line,
            level=2,
            title=DISCUSSION_THREAD_PASS_HEADING.removeprefix("## "),
        )
    ]
    if len(starts) != 1:
        raise ValueError("body must contain exactly one `## Discussion Thread Pass` Phase2 block")
    start_line = starts[0]
    start_end = start_line.source_offset + len(start_line.raw_line)
    following_h2_offsets = [
        line.source_offset
        for line in rendered_lines
        if line.source_offset >= start_end and markdown_heading_level(line) == 2
    ]
    if not following_h2_offsets:
        raise ValueError("Phase2 block must be followed by another H2 section")
    end = following_h2_offsets[0]
    mapping_starts = [
        line
        for line in rendered_lines
        if start_end <= line.source_offset < end
        and is_rendered_markdown_heading(
            line,
            level=3,
            title=FIXED_MAPPING_HEADINGS[1].removeprefix("### "),
        )
    ]
    if len(mapping_starts) != 1:
        raise ValueError(
            "`### Fixed in Commit Mapping` must appear exactly once inside the "
            "`## Discussion Thread Pass` block"
        )
    mirror = render_phase2_body_mirror(
        pr_number,
        repository=repository,
        ref=ref,
    )
    replaced = body[: start_line.source_offset] + mirror + "\n\n" + body[end:]
    marker_line = f"<!-- {PRE_CLOSEOUT_MARKER} -->"
    return "".join(
        line for line in replaced.splitlines(keepends=True) if line.rstrip("\r\n") != marker_line
    )

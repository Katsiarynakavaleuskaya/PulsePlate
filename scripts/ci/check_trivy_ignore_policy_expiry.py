from __future__ import annotations

import glob
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.check_react_router_rsc_premise import (  # noqa: E402
    PremiseScanError,
    scan_repository_package_roots as scan_react_router_rsc_premise,
)

# Allow trailing content after the date (e.g. "(manual removal)").
_EXPIRY_RE = re.compile(r"Suppression expires:\s*(\d{4}-\d{2}-\d{2})(?:\s|$)")
_REVIEW_BY_RE = re.compile(r"Review-by:\s*(\d{4}-\d{2}-\d{2})(?:\s|$)")
_CANONICAL_IGNORE_HEAD_LINE_RE = re.compile(r"[ \t]*ignore[ \t]+if[ \t]*\{[ \t]*(?:#.*)?")
_DEFAULT_IGNORE_LINE_RE = re.compile(r"[ \t]*default[ \t]+ignore[ \t]*:=[ \t]*false[ \t]*(?:#.*)?")
_REACT_ROUTER_RSC_CANONICAL_PREDICATES = (
    'input.VulnerabilityID == "GHSA-qwww-vcr4-c8h2"',
    'input.PkgName == "react-router"',
    'input.InstalledVersion == "7.18.1"',
    'input.PkgID == "react-router@7.18.1"',
    'input.FixedVersion == "8.3.0"',
)
_REACT_ROUTER_RSC_TARGET = {
    "VulnerabilityID": "GHSA-qwww-vcr4-c8h2",
    "PkgName": "react-router",
    "InstalledVersion": "7.18.1",
    "PkgID": "react-router@7.18.1",
    "FixedVersion": "8.3.0",
}


@dataclass(frozen=True)
class _RegoToken:
    kind: str
    value: str
    literal_value: str | None
    start: int
    end: int
    line: int
    depth: int


def _tokenize_rego(
    text: str,
    *,
    line_comments: list[tuple[int, str]] | None = None,
) -> tuple[tuple[_RegoToken, ...], dict[int, int]]:
    """Tokenize executable Rego while excluding comments and quoted/raw contents."""

    tokens: list[_RegoToken] = []
    brace_stack: list[int] = []
    brace_pairs: dict[int, int] = {}
    depth = 0
    index = 0
    line = 1
    while index < len(text):
        character = text[index]
        if character in " \t\r":
            index += 1
            continue
        if character == "\n":
            line += 1
            index += 1
            continue
        if character == "#":
            newline = text.find("\n", index)
            comment_end = len(text) if newline < 0 else newline
            if line_comments is not None:
                line_comments.append((line, text[index + 1 : comment_end]))
            index = comment_end
            continue
        if character in {'"', "`"}:
            quote = character
            start = index
            start_line = line
            index += 1
            escaped = False
            while index < len(text):
                character = text[index]
                if quote == '"' and escaped:
                    escaped = False
                elif quote == '"' and character == "\\":
                    escaped = True
                elif character == quote:
                    index += 1
                    break
                if character == "\n":
                    line += 1
                index += 1
            else:
                raise ValueError(f"unterminated string literal at line {start_line}")
            raw_literal = text[start:index]
            if quote == '"':
                try:
                    literal_value = json.loads(raw_literal)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid quoted string at line {start_line}: {exc.msg}"
                    ) from exc
            else:
                literal_value = raw_literal[1:-1]
            tokens.append(
                _RegoToken(
                    kind="string",
                    value=raw_literal,
                    literal_value=literal_value,
                    start=start,
                    end=index,
                    line=start_line,
                    depth=depth,
                )
            )
            continue
        start = index
        if character.isalpha() or character == "_":
            index += 1
            while index < len(text) and (text[index].isalnum() or text[index] == "_"):
                index += 1
            kind = "identifier"
            value = text[start:index]
        elif text.startswith(":=", index) or text.startswith("==", index):
            index += 2
            kind = "operator"
            value = text[start:index]
        else:
            index += 1
            kind = "symbol"
            value = character
        if value == "}" and not brace_stack:
            raise ValueError(f"unexpected closing brace at line {line}")
        token_index = len(tokens)
        tokens.append(
            _RegoToken(
                kind=kind,
                value=value,
                literal_value=None,
                start=start,
                end=index,
                line=line,
                depth=depth,
            )
        )
        if value == "{":
            brace_stack.append(token_index)
            depth += 1
        elif value == "}":
            opening_index = brace_stack.pop()
            brace_pairs[opening_index] = token_index
            depth -= 1
    if brace_stack:
        opening = tokens[brace_stack[-1]]
        raise ValueError(f"unterminated block opened at line {opening.line}")
    return tuple(tokens), brace_pairs


def _inspect_ignore_policy_source(text: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
    """Extract canonical-head bodies and identify every unsupported ignore construct."""

    tokens, brace_pairs = _tokenize_rego(text)
    source_lines = text.splitlines()
    ignore_blocks: list[str] = []
    unsupported_lines: set[int] = set()
    for index, token in enumerate(tokens):
        if token.depth != 0 or token.kind != "identifier":
            continue
        previous = tokens[index - 1] if index else None
        if token.value == "else" and not (
            previous is not None and previous.value == "." and previous.line == token.line
        ):
            unsupported_lines.add(token.line)
            continue
        if token.value != "ignore":
            continue
        if previous is not None and previous.value == "." and previous.line == token.line:
            continue
        source_line = source_lines[token.line - 1]
        if _DEFAULT_IGNORE_LINE_RE.fullmatch(source_line):
            continue
        if _CANONICAL_IGNORE_HEAD_LINE_RE.fullmatch(source_line):
            if (
                index + 2 < len(tokens)
                and tokens[index + 1].value == "if"
                and tokens[index + 1].line == token.line
                and tokens[index + 2].value == "{"
                and tokens[index + 2].line == token.line
            ):
                opening_index = index + 2
                closing_index = brace_pairs.get(opening_index)
                if closing_index is not None:
                    ignore_blocks.append(
                        text[tokens[opening_index].end : tokens[closing_index].start]
                    )
                    continue
        unsupported_lines.add(token.line)
    return tuple(ignore_blocks), tuple(sorted(unsupported_lines))


def _top_level_body_token_lines(body: str) -> tuple[tuple[_RegoToken, ...], ...]:
    tokens, _brace_pairs = _tokenize_rego(body)
    by_line: dict[int, list[_RegoToken]] = {}
    for token in tokens:
        if token.depth == 0:
            by_line.setdefault(token.line, []).append(token)
    return tuple(tuple(by_line[line]) for line in sorted(by_line))


def _top_level_body_token_expressions(
    body: str,
) -> tuple[tuple[tuple[_RegoToken, ...], ...], ...]:
    """Group following-line ``with`` modifiers with their executable expression."""

    expressions: list[list[tuple[_RegoToken, ...]]] = []
    for token_line in _top_level_body_token_lines(body):
        if token_line[0].value == "with" and expressions:
            expressions[-1].append(token_line)
            continue
        expressions.append([token_line])
    return tuple(tuple(expression) for expression in expressions)


def _direct_input_equality(tokens: tuple[_RegoToken, ...]) -> tuple[str, str] | None:
    if len(tokens) != 5:
        return None
    if (
        tokens[0].value == "input"
        and tokens[1].value == "."
        and tokens[2].kind == "identifier"
        and tokens[3].value == "=="
        and tokens[4].kind == "string"
        and tokens[4].literal_value is not None
    ):
        return tokens[2].value, tokens[4].literal_value
    if (
        tokens[0].kind == "string"
        and tokens[0].literal_value is not None
        and tokens[1].value == "=="
        and tokens[2].value == "input"
        and tokens[3].value == "."
        and tokens[4].kind == "identifier"
    ):
        return tokens[4].value, tokens[0].literal_value
    return None


def _with_modifier_target(tokens: tuple[_RegoToken, ...]) -> tuple[_RegoToken, ...] | None:
    """Return a complete following-line ``with`` target, or fail closed."""

    if not tokens or tokens[0].value != "with":
        return None
    separator_index = next(
        (index for index, token in enumerate(tokens[1:], start=1) if token.value == "as"),
        None,
    )
    if separator_index is None or separator_index == 1 or separator_index + 1 >= len(tokens):
        return None
    return tokens[1:separator_index]


def _with_target_can_affect_input_field(
    target: tuple[_RegoToken, ...],
    field: str,
) -> bool:
    """Return whether a ``with`` target can replace the referenced input field."""

    if not target or target[0].value != "input":
        return False
    if len(target) == 1:
        return True
    if target[1].value == ".":
        if len(target) < 3 or target[2].kind != "identifier":
            return True
        return target[2].value == field
    if target[1].value == "[":
        if (
            len(target) >= 4
            and target[2].kind == "string"
            and target[2].literal_value is not None
            and target[3].value == "]"
        ):
            return target[2].literal_value == field
        return True
    return True


def _direct_input_equality_expression(
    token_lines: tuple[tuple[_RegoToken, ...], ...],
) -> tuple[str, str] | None:
    """Prove a direct equality only across its complete executable expression."""

    if not token_lines:
        return None
    equality = _direct_input_equality(token_lines[0])
    if equality is None:
        return None
    field, _value = equality
    for modifier_tokens in token_lines[1:]:
        target = _with_modifier_target(modifier_tokens)
        if target is None or _with_target_can_affect_input_field(target, field):
            return None
    return equality


def _ignore_block_can_match_react_router_target(body: str) -> bool:
    """Conservatively reject blocks only when executable equality proves conflict."""

    for token_expression in _top_level_body_token_expressions(body):
        equality = _direct_input_equality_expression(token_expression)
        if equality is None:
            continue
        field, value = equality
        if field in _REACT_ROUTER_RSC_TARGET and value != _REACT_ROUTER_RSC_TARGET[field]:
            return False
    return True


def _ignore_block_predicates(body: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _is_canonical_react_router_body(body: str) -> bool:
    if _ignore_block_predicates(body) != _REACT_ROUTER_RSC_CANONICAL_PREDICATES:
        return False
    token_lines = _top_level_body_token_lines(body)
    if len(token_lines) != len(_REACT_ROUTER_RSC_TARGET):
        return False
    return all(
        _direct_input_equality(token_line) == expected
        for token_line, expected in zip(
            token_lines,
            _REACT_ROUTER_RSC_TARGET.items(),
            strict=True,
        )
    )


def _read_rego_text(policy_file: Path) -> str:
    """Read one Rego policy or raise a stable validation failure."""

    try:
        return policy_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"Unable to read Trivy ignore policy {policy_file}: {exc}") from exc


def _validate_react_router_rsc_suppression(
    policy_file: Path,
    *,
    text: str,
) -> list[str]:
    """Require one and only one exact five-predicate GHSA ignore block."""

    try:
        ignore_blocks, unsupported_lines = _inspect_ignore_policy_source(text)
    except ValueError as exc:
        return [f"React Router RSC suppression parsing failed in {policy_file}: {exc}"]
    if unsupported_lines:
        rendered_lines = ", ".join(str(line) for line in unsupported_lines)
        return [
            f"React Router RSC suppression in {policy_file} has unsupported top-level "
            f"ignore rule syntax at line(s) {rendered_lines}; only 'default ignore := "
            "false' and balanced 'ignore if {' blocks are permitted"
        ]
    target_capable_blocks = tuple(
        body for body in ignore_blocks if _ignore_block_can_match_react_router_target(body)
    )
    if not target_capable_blocks:
        return []
    canonical_blocks = tuple(
        body for body in target_capable_blocks if _is_canonical_react_router_body(body)
    )
    if len(canonical_blocks) > 1:
        return [
            f"React Router RSC suppression in {policy_file} must use exactly one GHSA ignore block"
        ]
    if not canonical_blocks:
        return [
            f"React Router RSC suppression in {policy_file} must contain exactly "
            "the canonical five predicates"
        ]
    if len(target_capable_blocks) > 1:
        return [
            f"React Router RSC suppression in {policy_file} has an additional ignore "
            "block capable of matching the canonical target tuple"
        ]
    return []


def _read_rego_line_comments(text: str) -> tuple[tuple[int, str], ...]:
    comments: list[tuple[int, str]] = []
    _tokenize_rego(text, line_comments=comments)
    return tuple(comments)


def _parse_expiry(path: Path, *, text: str) -> date:
    matches: list[date] = []
    for line_number, comment in _read_rego_line_comments(text):
        found = _EXPIRY_RE.search(comment)
        if found:
            try:
                matches.append(date.fromisoformat(found.group(1)))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid 'Suppression expires' date in {path}:{line_number}: "
                    f"{found.group(1)} ({exc})"
                ) from exc
    if not matches:
        raise ValueError(f"Missing 'Suppression expires: YYYY-MM-DD' in {path}")
    if len(matches) > 1:
        raise ValueError(
            f"Multiple 'Suppression expires: YYYY-MM-DD' entries found in {path}; "
            "expected exactly one expiry per policy file"
        )
    return matches[0]


def _parse_review_by_dates(path: Path, *, text: str) -> list[tuple[int, date]]:
    review_dates: list[tuple[int, date]] = []
    for line_number, comment in _read_rego_line_comments(text):
        found = _REVIEW_BY_RE.search(comment)
        if found:
            try:
                review_dates.append((line_number, date.fromisoformat(found.group(1))))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid 'Review-by' date in {path}:{line_number}: "
                    f"{found.group(1)} ({exc})"
                ) from exc
    return review_dates


def evaluate_policy_file(
    policy_file: Path,
    *,
    today: date,
    text: str | None = None,
) -> list[str]:
    if text is None:
        try:
            text = _read_rego_text(policy_file)
        except ValueError as exc:
            return [str(exc)]

    failures = _validate_react_router_rsc_suppression(policy_file, text=text)
    try:
        expiry = _parse_expiry(policy_file, text=text)
    except ValueError as exc:
        failures.append(str(exc))
        return failures

    if today > expiry:
        failures.append(
            f"Expired Trivy ignore policy: {policy_file} (expired {expiry}, today {today})"
        )

    try:
        review_by_dates = _parse_review_by_dates(policy_file, text=text)
    except ValueError as exc:
        failures.append(str(exc))
        return failures

    for line_number, review_by in review_by_dates:
        if today > review_by:
            failures.append(
                f"Stale Trivy suppression review date: {policy_file}:{line_number} "
                f"(review-by {review_by}, today {today})"
            )
    return failures


def _resolve_policy_files(repo_root: Path) -> list[Path]:
    env_path = os.environ.get("TRIVY_IGNORE_POLICY_PATH", "").strip()
    if env_path:
        # Allow comma-separated list (mirrors trivy-action inputs style).
        paths = [p.strip() for p in env_path.split(",") if p.strip()]
        resolved: list[Path] = []
        for raw in paths:
            if glob.has_magic(raw):
                resolved.extend(sorted(repo_root.glob(raw)))
                continue
            resolved.append((repo_root / raw).resolve())
        return resolved

    trivy_dir = repo_root / "trivy"
    return sorted(trivy_dir.glob("ignore-policy*.rego"))


def _contains_react_router_rsc_suppression(
    policy_file: Path,
    *,
    text: str | None = None,
) -> bool:
    """Detect any ignore block that could match the canonical target tuple."""

    if text is None:
        try:
            text = _read_rego_text(policy_file)
        except ValueError:
            return True
    try:
        ignore_blocks, unsupported_lines = _inspect_ignore_policy_source(text)
    except ValueError:
        return True
    if unsupported_lines:
        return True
    return any(_ignore_block_can_match_react_router_target(body) for body in ignore_blocks)


def main() -> int:
    repo_root = REPO_ROOT
    policy_files = _resolve_policy_files(repo_root)

    missing_files = [p for p in policy_files if not p.exists()]
    if missing_files:
        print("ERROR: Trivy ignore policy file(s) not found:")
        for p in missing_files:
            print(f"- {p}")
        return 1

    if not policy_files:
        print(
            "ERROR: No Trivy ignore policy files found. "
            "Set TRIVY_IGNORE_POLICY_PATH or add trivy/ignore-policy*.rego."
        )
        return 1

    today = datetime.now(UTC).date()
    failures: list[str] = []
    suppression_present = False

    for policy_file in policy_files:
        try:
            text = _read_rego_text(policy_file)
        except ValueError as exc:
            failures.append(str(exc))
            suppression_present = True
            continue
        failures.extend(evaluate_policy_file(policy_file, today=today, text=text))
        suppression_present = suppression_present or _contains_react_router_rsc_suppression(
            policy_file,
            text=text,
        )

    if suppression_present:
        try:
            violations = scan_react_router_rsc_premise(repo_root)
        except PremiseScanError as exc:
            failures.append(f"React Router RSC premise scan was incomplete: {exc}")
        else:
            failures.extend(
                f"React Router RSC suppression premise violated: {violation}"
                for violation in violations
            )

    if failures:
        print("ERROR: Trivy ignore policy expiry check failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

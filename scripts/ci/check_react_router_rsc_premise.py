"""Fail closed when PulsePlate starts using the suppressed React Router RSC surface."""

from __future__ import annotations

import argparse
from collections import deque
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_ROOT = REPO_ROOT / "frontend"

SOURCE_SUFFIXES = {
    ".cjs",
    ".cts",
    ".js",
    ".jsx",
    ".mjs",
    ".mts",
    ".ts",
    ".tsx",
}
GLOBAL_EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "artifacts",
    "node_modules",
    "worktrees",
}
ROOT_OUTPUT_DIRECTORIES = {"build", "dist"}
DEPENDENCY_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies")
_PACKAGE_MARKER_LABELS = {
    "@vitejs/plugin-rsc": "@vitejs/plugin-rsc",
    "react-server-dom-": "react-server-dom-*",
}
RUNTIME_MARKERS = (
    "unstable_matchRSCServerRequest",
    "unstable_routeRSCServerRequest",
    "react-router/internal/react-server",
    *_PACKAGE_MARKER_LABELS,
)
_REACT_SERVER_CONDITION_RE = re.compile(r"(?<![A-Za-z0-9_-])react-server(?![A-Za-z0-9_-])")
_REGEX_PREFIX_CHARACTERS = frozenset("([{=,:;!?&|+-*%^~")
_REGEX_PREFIX_KEYWORDS = ("await", "case", "delete", "return", "throw", "typeof", "void", "yield")
_REGEX_PREFIX_CONTEXT_LIMIT = max(len(keyword) for keyword in _REGEX_PREFIX_KEYWORDS) + 1
_SOURCE_IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_SOURCE_IDENTIFIER_FULL_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\Z")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class _VisibleCharacters(list[str]):
    """Retain full visible source plus bounded context for regex disambiguation."""

    def __init__(self) -> None:
        super().__init__()
        self._regex_prefix_context: deque[str] = deque(maxlen=_REGEX_PREFIX_CONTEXT_LIMIT)
        self._has_trailing_whitespace = False

    def append(self, character: str) -> None:
        """Append one source character and update bounded non-blank context."""

        super().append(character)
        if character.isspace():
            self._has_trailing_whitespace = True
            return
        if self._has_trailing_whitespace and self._regex_prefix_context:
            self._regex_prefix_context.append(" ")
        self._regex_prefix_context.append(character)
        self._has_trailing_whitespace = False

    def extend(self, characters: Iterable[str]) -> None:
        """Append source characters without bypassing context tracking."""

        for character in characters:
            self.append(character)

    @property
    def regex_prefix_context(self) -> str:
        """Return the bounded suffix of visible source with whitespace stripped."""

        return "".join(self._regex_prefix_context)


class PremiseScanError(RuntimeError):
    """Raised when the guard cannot prove that the RSC premise still holds."""


@dataclass(frozen=True)
class _SourceToken:
    """One bounded JavaScript token needed by the suppression premise."""

    kind: str
    value: str


def _relative_label(path: Path, root: Path) -> str:
    """Return a stable root-relative diagnostic label when possible."""

    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _canonical_root(root: Path) -> Path:
    """Resolve and validate the non-symlink frontend scan root."""

    try:
        metadata = root.lstat()
    except OSError as exc:
        raise PremiseScanError(f"unable to inspect frontend root {root}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise PremiseScanError(f"frontend root must not be a symlink: {root}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise PremiseScanError(f"frontend root is not a directory: {root}")
    try:
        return root.resolve(strict=True)
    except OSError as exc:
        raise PremiseScanError(f"unable to resolve frontend root {root}: {exc}") from exc


def _validate_candidate(path: Path, root: Path) -> str:
    """Read a regular in-root candidate file without following symlinks."""

    label = _relative_label(path, root)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise PremiseScanError(f"unable to inspect {label}: {exc}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise PremiseScanError(f"candidate path must not be a symlink: {label}")
    if not stat.S_ISREG(metadata.st_mode):
        raise PremiseScanError(f"candidate path is not a regular file: {label}")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise PremiseScanError(f"candidate path escapes frontend root: {label}") from exc
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PremiseScanError(f"unable to read {label}: {exc}") from exc


def _load_json_object(path: Path, root: Path, *, required: bool) -> dict[str, object] | None:
    """Load a metadata file as a JSON object or fail closed."""

    label = _relative_label(path, root)
    try:
        path.lstat()
    except FileNotFoundError:
        if required:
            raise PremiseScanError(f"required metadata file is missing: {label}") from None
        return None
    except OSError as exc:
        raise PremiseScanError(f"unable to inspect {label}: {exc}") from exc

    text = _validate_candidate(path, root)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PremiseScanError(
            f"invalid JSON in {label}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise PremiseScanError(f"expected a JSON object in {label}")
    return value


def _json_strings(
    value: object,
    path: tuple[str, ...] = (),
) -> Iterator[tuple[tuple[str, ...], str]]:
    """Yield JSON keys and string values with deterministic structural paths."""

    if isinstance(value, dict):
        for key in sorted(value, key=str):
            key_path = (*path, str(key))
            yield key_path, str(key)
            yield from _json_strings(value[key], key_path)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _json_strings(nested, (*path, str(index)))
    elif isinstance(value, str):
        yield path, value


def _append_package_markers(
    violations: list[str],
    *,
    filename: str,
    entries: Iterator[tuple[tuple[str, ...], str]],
) -> None:
    """Append package marker diagnostics from JSON metadata entries."""

    for path, value in entries:
        location = ".".join(path) or "<root>"
        for marker, diagnostic_label in _PACKAGE_MARKER_LABELS.items():
            if marker in value:
                violations.append(f"{filename}:{location}:{diagnostic_label}")


def _scan_package_metadata(root: Path) -> list[str]:
    """Return RSC markers found in package metadata and scripts."""

    violations: list[str] = []
    package_json = _load_json_object(root / "package.json", root, required=True)
    if package_json is None:
        raise PremiseScanError("required metadata file is missing: package.json")

    dependency_sections: dict[str, object] = {}
    for section in DEPENDENCY_SECTIONS:
        section_value = package_json.get(section, {})
        if not isinstance(section_value, dict):
            raise PremiseScanError(f"package.json:{section} must be a JSON object")
        for package_name, version in section_value.items():
            if not isinstance(version, str):
                raise PremiseScanError(f"package.json:{section}.{package_name} must be a string")
        dependency_sections[section] = section_value
    _append_package_markers(
        violations,
        filename="package.json",
        entries=_json_strings(dependency_sections),
    )

    scripts = package_json.get("scripts", {})
    if not isinstance(scripts, dict):
        raise PremiseScanError("package.json:scripts must be a JSON object")
    for script_name in sorted(scripts, key=str):
        command = scripts[script_name]
        if not isinstance(command, str):
            raise PremiseScanError(f"package.json:scripts.{script_name} must be a string")
        if _REACT_SERVER_CONDITION_RE.search(command):
            violations.append(f"package.json:scripts.{script_name}:react-server condition")

    package_lock = _load_json_object(root / "package-lock.json", root, required=True)
    if package_lock is None:
        raise PremiseScanError("required metadata file is missing: package-lock.json")
    for section in ("packages", "dependencies"):
        section_value = package_lock.get(section)
        if section_value is not None and not isinstance(section_value, dict):
            raise PremiseScanError(f"package-lock.json:{section} must be a JSON object")
    _append_package_markers(
        violations,
        filename="package-lock.json",
        entries=_json_strings(package_lock),
    )
    return violations


def _ends_with_regex_prefix_keyword(prefix: str) -> bool:
    """Return whether a source prefix permits a following regex literal."""

    return any(re.search(rf"\b{keyword}$", prefix) for keyword in _REGEX_PREFIX_KEYWORDS)


def _starts_regex_literal(visible: _VisibleCharacters) -> bool:
    """Distinguish a regex literal slash from division using bounded context."""

    prefix = visible.regex_prefix_context
    if not prefix:
        return True
    if prefix[-1] in _REGEX_PREFIX_CHARACTERS:
        return True
    return _ends_with_regex_prefix_keyword(prefix)


def _consume_regex_literal(
    text: str,
    *,
    start: int,
    visible: _VisibleCharacters,
    label: str,
) -> int:
    """Consume a JavaScript regex literal while preserving source offsets."""

    index = start
    in_character_class = False
    while index < len(text):
        character = text[index]
        visible.append("\n" if character == "\n" else " ")
        if character in "\r\n":
            raise PremiseScanError(f"unterminated regular expression literal in {label}")
        if character == "\\":
            index += 1
            if index >= len(text):
                break
            visible.append(" ")
            index += 1
            continue
        if character == "[":
            in_character_class = True
        elif character == "]":
            in_character_class = False
        elif character == "/" and not in_character_class:
            index += 1
            while index < len(text) and text[index].isalpha():
                visible.append(" ")
                index += 1
            return index
        index += 1
    raise PremiseScanError(f"unterminated regular expression literal in {label}")


def _append_code_tokens(tokens: list[_SourceToken], code: str) -> None:
    """Append identifiers and punctuation while discarding only whitespace."""

    index = 0
    while index < len(code):
        character = code[index]
        if character.isspace():
            index += 1
            continue
        identifier = _SOURCE_IDENTIFIER_RE.match(code, index)
        if identifier is not None:
            tokens.append(_SourceToken("identifier", identifier.group(0)))
            index = identifier.end()
            continue
        tokens.append(_SourceToken("punctuation", character))
        index += 1


def _source_analysis(
    text: str,
    *,
    label: str,
) -> tuple[list[str], str, tuple[_SourceToken, ...]]:
    """Return literals, visible text, and bounded syntax tokens."""

    literals: list[str] = []
    visible = _VisibleCharacters()
    tokens: list[_SourceToken] = []
    code_buffer: list[str] = []
    index = 0
    length = len(text)

    def flush_code_tokens() -> None:
        if code_buffer:
            _append_code_tokens(tokens, "".join(code_buffer))
            code_buffer.clear()

    while index < length:
        current = text[index]
        following = text[index + 1] if index + 1 < length else ""

        if current == "/" and following == "/":
            visible.extend((" ", " "))
            code_buffer.extend((" ", " "))
            index += 2
            while index < length and text[index] not in "\r\n":
                visible.append(" ")
                code_buffer.append(" ")
                index += 1
            continue

        if current == "/" and following == "*":
            visible.extend((" ", " "))
            code_buffer.extend((" ", " "))
            index += 2
            while index < length:
                if text[index] == "*" and index + 1 < length and text[index + 1] == "/":
                    visible.extend((" ", " "))
                    code_buffer.extend((" ", " "))
                    index += 2
                    break
                replacement = "\n" if text[index] == "\n" else " "
                visible.append(replacement)
                code_buffer.append(replacement)
                index += 1
            else:
                raise PremiseScanError(f"unterminated block comment in {label}")
            continue

        if current == "/" and _starts_regex_literal(visible):
            visible.append(" ")
            code_buffer.append(" ")
            index = _consume_regex_literal(
                text,
                start=index + 1,
                visible=visible,
                label=label,
            )
            continue

        if current == "'" and index > 0 and text[index - 1].isalnum():
            prefix = visible.regex_prefix_context
            if not _ends_with_regex_prefix_keyword(prefix):
                visible.append(current)
                code_buffer.append(current)
                index += 1
                continue

        if current not in {"'", '"', "`"}:
            visible.append(current)
            code_buffer.append(current)
            index += 1
            continue

        quote = current
        literal: list[str] = []
        flush_code_tokens()
        visible.append(current)
        index += 1
        while index < length:
            character = text[index]
            visible.append(character)
            if character == "\\":
                literal.append(character)
                index += 1
                if index >= length:
                    break
                literal.append(text[index])
                visible.append(text[index])
                index += 1
                continue
            if character == quote:
                literal_value = "".join(literal)
                literals.append(literal_value)
                tokens.append(
                    _SourceToken(
                        "template" if quote == "`" else "string",
                        literal_value,
                    )
                )
                index += 1
                break
            literal.append(character)
            index += 1
        else:
            raise PremiseScanError(f"unterminated string literal in {label}")
        if index >= length and (not visible or visible[-1] != quote):
            raise PremiseScanError(f"unterminated string literal in {label}")

    flush_code_tokens()
    return literals, "".join(visible), tuple(tokens)


def _source_literals_and_visible_text(text: str, *, label: str) -> tuple[list[str], str]:
    """Return exact string literals plus source text with comments and regexes elided."""

    literals, visible, _tokens = _source_analysis(text, label=label)
    return literals, visible


def _has_react_router_namespace_import(tokens: Sequence[_SourceToken]) -> bool:
    """Detect only runtime static namespace imports from exact `react-router`."""

    for index in range(len(tokens) - 5):
        if (
            tokens[index] != _SourceToken("identifier", "import")
            or tokens[index + 1] != _SourceToken("punctuation", "*")
            or tokens[index + 2] != _SourceToken("identifier", "as")
        ):
            continue
        for from_index in range(index + 4, min(index + 9, len(tokens) - 1)):
            if tokens[from_index] != _SourceToken("identifier", "from"):
                continue
            binding = _decode_identifier_tokens(tokens[index + 3 : from_index])
            module = tokens[from_index + 1]
            if (
                binding is not None
                and module.kind == "string"
                and _decode_javascript_ascii_escapes(module.value) == "react-router"
            ):
                return True
            break
    return False


def _decode_javascript_ascii_escapes(value: str) -> str | None:
    """Decode bounded ASCII escapes used by import specifiers and identifiers."""

    decoded: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(value):
            return None
        kind = value[index + 1]
        if kind == "x":
            digits = value[index + 2 : index + 4]
            width = 4
        elif kind == "u" and value[index + 2 : index + 3] != "{":
            digits = value[index + 2 : index + 6]
            width = 6
        elif kind == "u" and value[index + 2 : index + 3] == "{":
            closing = value.find("}", index + 3)
            if closing < 0:
                return None
            digits = value[index + 3 : closing]
            width = closing - index + 1
            if not 1 <= len(digits) <= 6:
                return None
        else:
            return None
        if not digits or any(digit not in _HEX_DIGITS for digit in digits):
            return None
        codepoint = int(digits, 16)
        if codepoint > 0x7F:
            return None
        decoded.append(chr(codepoint))
        index += width
    return "".join(decoded)


def _decode_identifier_tokens(tokens: Sequence[_SourceToken]) -> str | None:
    """Return one canonical ASCII identifier from bounded lexical tokens."""

    if not tokens:
        return None
    raw = "".join(token.value for token in tokens)
    decoded = _decode_javascript_ascii_escapes(raw)
    if decoded is None or _SOURCE_IDENTIFIER_FULL_RE.fullmatch(decoded) is None:
        return None
    return decoded


def _scan_source_file(path: Path, root: Path) -> list[str]:
    """Return fixed RSC marker diagnostics for one approved source file."""

    label = _relative_label(path, root)
    text = _validate_candidate(path, root)
    literals, visible, tokens = _source_analysis(text, label=label)
    violations = [f"{label}:{marker}" for marker in RUNTIME_MARKERS if marker in visible]
    if any(_REACT_SERVER_CONDITION_RE.search(literal) for literal in literals):
        violations.append(f"{label}:react-server condition")
    if _has_react_router_namespace_import(tokens):
        violations.append(f"{label}:react-router namespace import")
    return violations


def _walk_source_files(root: Path) -> Iterator[Path]:
    """Yield approved source files with fail-closed traversal containment."""

    def raise_traversal_error(error: OSError) -> None:
        """Promote os.walk traversal errors to stable guard failures."""

        raise PremiseScanError(f"unable to traverse frontend root: {error}") from error

    for current_raw, dirnames, filenames in os.walk(
        root,
        topdown=True,
        onerror=raise_traversal_error,
        followlinks=False,
    ):
        current = Path(current_raw)
        try:
            current.resolve(strict=True).relative_to(root)
        except (OSError, ValueError) as exc:
            raise PremiseScanError(
                f"traversal escaped frontend root at {_relative_label(current, root)}"
            ) from exc

        relative_current = current.relative_to(root)
        retained_directories: list[str] = []
        for dirname in sorted(dirnames):
            directory = current / dirname
            label = _relative_label(directory, root)
            try:
                metadata = directory.lstat()
            except OSError as exc:
                raise PremiseScanError(f"unable to inspect directory {label}: {exc}") from exc
            if stat.S_ISLNK(metadata.st_mode):
                raise PremiseScanError(f"directory must not be a symlink: {label}")
            try:
                directory.resolve(strict=True).relative_to(root)
            except (OSError, ValueError) as exc:
                raise PremiseScanError(f"directory escapes frontend root: {label}") from exc
            if dirname in GLOBAL_EXCLUDED_DIRECTORIES:
                continue
            if relative_current == Path() and dirname in ROOT_OUTPUT_DIRECTORIES:
                continue
            retained_directories.append(dirname)
        dirnames[:] = retained_directories

        for filename in sorted(filenames):
            path = current / filename
            if path.suffix in SOURCE_SUFFIXES:
                yield path


def scan_repository(root: Path) -> list[str]:
    """Return stable violations, or raise when the absence proof is incomplete."""

    canonical_root = _canonical_root(root)
    violations = _scan_package_metadata(canonical_root)
    for source_path in _walk_source_files(canonical_root):
        violations.extend(_scan_source_file(source_path, canonical_root))
    return sorted(set(violations))


def _argument_parser() -> argparse.ArgumentParser:
    """Build the command-line interface for the premise guard."""

    parser = argparse.ArgumentParser(
        description="Verify that the suppressed React Router RSC surface is absent."
    )
    parser.add_argument(
        "--frontend-root",
        type=Path,
        default=DEFAULT_FRONTEND_ROOT,
        help="frontend repository root (default: %(default)s)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the premise guard and return a stable process exit code."""

    args = _argument_parser().parse_args(argv)
    frontend_root = args.frontend_root
    if not frontend_root.is_absolute():
        frontend_root = REPO_ROOT / frontend_root
    try:
        violations = scan_repository(frontend_root)
    except PremiseScanError as exc:
        print(f"ERROR: React Router RSC premise scan was incomplete: {exc}")
        return 1

    if violations:
        print("ERROR: React Router RSC suppression premise violated:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("PASS: React Router RSC suppression premise holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

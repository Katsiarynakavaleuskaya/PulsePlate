"""Fail closed when PulsePlate starts using the suppressed React Router RSC surface."""

from __future__ import annotations

import argparse
from collections import deque
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import stat

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRONTEND_ROOT = REPO_ROOT / "frontend"

SOURCE_SUFFIXES = {
    ".cjs",
    ".cts",
    ".js",
    ".jsx",
    ".mdx",
    ".mjs",
    ".mts",
    ".ts",
    ".tsx",
}
HTML_SUFFIXES = {".html"}
GLOBAL_EXCLUDED_DIRECTORIES = {
    ".agents",
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
_TARGET_REACT_ROUTER_PACKAGE = "react-router"
_TARGET_REACT_ROUTER_VERSION = "7.18.1"
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
_SOURCE_IDENTIFIER_RE = re.compile(r"(?:[$_]|[^\W\d])(?:[$\w\u200c\u200d])*")
_PYTHON_INTERPRETER_RE = re.compile(r"python(?:\d+(?:\.\d+)*)?\Z")
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_JAVASCRIPT_SIMPLE_ESCAPES = {
    "0": "\0",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "'": "'",
    '"': '"',
    "\\": "\\",
}
_ECMASCRIPT_LINE_TERMINATORS = frozenset("\r\n\u2028\u2029")
_SHELL_INTERPRETERS = frozenset({"bash", "dash", "sh", "zsh"})
_SHELL_OPTIONS_WITH_ARGUMENT = frozenset({"--init-file", "--rcfile", "-O", "-o"})
_SHELL_CONTROL_TOKENS = frozenset({"&", "&&", "(", ")", ";", "|", "||"})
_SHELL_SOURCE_BUILTINS = frozenset({".", "source"})
_SHELL_UNSUPPORTED_COMMANDS = frozenset({"!", "{", "cd", "command", "env", "exec", "if"})
_SHELL_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_CLASSIC_JAVASCRIPT_MIME_TYPES = frozenset(
    {
        "application/ecmascript",
        "application/javascript",
        "application/x-ecmascript",
        "application/x-javascript",
        "text/ecmascript",
        "text/javascript",
        "text/jscript",
        "text/livescript",
        "text/x-ecmascript",
        "text/x-javascript",
    }
)
_TEMPLATE_INTERPOLATION_RSC_FRAGMENTS = (
    "@vitejs/plugin-rsc",
    "RSCServerRequest",
    "react-router",
    "react-server",
    "unstable_",
)


class _VisibleCharacters(list[str]):
    """Retain full visible source plus bounded context for regex disambiguation."""

    def __init__(self) -> None:
        super().__init__()
        self._regex_prefix_context: deque[str] = deque(maxlen=_REGEX_PREFIX_CONTEXT_LIMIT)
        self._has_trailing_whitespace = False
        self._has_trailing_line_terminator = False
        self._ends_with_postfix_update_operator = False

    def append(self, character: str) -> None:
        """Append one source character and update bounded non-blank context."""

        super().append(character)
        if character.isspace():
            self._has_trailing_whitespace = True
            if character in _ECMASCRIPT_LINE_TERMINATORS:
                self._has_trailing_line_terminator = True
            return
        if self._has_trailing_whitespace and self._regex_prefix_context:
            self._regex_prefix_context.append(" ")
        self._regex_prefix_context.append(character)
        self._has_trailing_whitespace = False
        self._has_trailing_line_terminator = False
        self._ends_with_postfix_update_operator = False

    def extend(self, characters: Iterable[str]) -> None:
        """Append source characters without bypassing context tracking."""

        for character in characters:
            self.append(character)

    def append_update_operator(self, operator: str, *, postfix: bool) -> None:
        """Append one update token and retain whether it ended an expression."""

        self.extend(operator)
        self._ends_with_postfix_update_operator = postfix

    @property
    def regex_prefix_context(self) -> str:
        """Return the bounded suffix of visible source with whitespace stripped."""

        return "".join(self._regex_prefix_context)

    @property
    def ends_with_postfix_update_operator(self) -> bool:
        """Return whether the last executable token was postfix ``++`` or ``--``."""

        return self._ends_with_postfix_update_operator

    @property
    def has_trailing_line_terminator(self) -> bool:
        """Return whether a line break follows the last executable token."""

        return self._has_trailing_line_terminator


class PremiseScanError(RuntimeError):
    """Raised when the guard cannot prove that the RSC premise still holds."""


@dataclass(frozen=True)
class _SourceToken:
    """One bounded JavaScript token needed by the suppression premise."""

    kind: str
    value: str


class _InlineModuleScriptParser(HTMLParser):
    """Collect executable inline module bodies from one HTML document."""

    def __init__(self, *, label: str) -> None:
        super().__init__(convert_charrefs=False)
        self._label = label
        self._inside_script = False
        self._is_module = False
        self._is_classic = False
        self._body: list[str] = []
        self.module_scripts: list[str] = []
        self.classic_scripts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "script":
            return
        if self._inside_script:
            raise PremiseScanError(f"nested script element in {self._label}")
        self._inside_script = True
        script_type = next(
            (
                (value or "").strip().lower().partition(";")[0]
                for name, value in attrs
                if name.lower() == "type"
            ),
            "",
        )
        has_source = any(name.lower() == "src" for name, _value in attrs)
        self._is_module = script_type == "module" and not has_source
        self._is_classic = not has_source and (
            not script_type or script_type in _CLASSIC_JAVASCRIPT_MIME_TYPES
        )
        self._body = []

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() == "script":
            self.handle_starttag(tag, attrs)
            self.set_cdata_mode("script")

    def handle_data(self, data: str) -> None:
        if self._inside_script and (self._is_module or self._is_classic):
            self._body.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self._inside_script:
            return
        if self._is_module:
            self.module_scripts.append("".join(self._body))
        elif self._is_classic:
            self.classic_scripts.append("".join(self._body))
        self._inside_script = False
        self._is_module = False
        self._is_classic = False
        self._body = []

    def finish(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Finish parsing and reject an unterminated script element."""

        self.close()
        if self._inside_script:
            raise PremiseScanError(f"unterminated script element in {self._label}")
        return tuple(self.module_scripts), tuple(self.classic_scripts)


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


def _load_json_object(path: Path, root: Path) -> dict[str, object]:
    """Load a metadata file as a JSON object or fail closed."""

    label = _relative_label(path, root)
    try:
        path.lstat()
    except FileNotFoundError:
        raise PremiseScanError(f"required metadata file is missing: {label}") from None
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


def _package_import_targets(
    value: object,
    path: tuple[str, ...],
) -> Iterator[tuple[tuple[str, ...], str]]:
    """Yield recursively nested package-import string targets."""

    if isinstance(value, dict):
        for key in sorted(value, key=str):
            yield from _package_import_targets(value[key], (*path, str(key)))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _package_import_targets(nested, (*path, str(index)))
    elif isinstance(value, str):
        yield path, value
    elif value is not None:
        location = ".".join(path) or "imports"
        raise PremiseScanError(
            f"package.json:{location} target must be a string, object, array, or null"
        )


def _is_react_router_package_target(value: str) -> bool:
    """Return whether one imports target resolves into the react-router package."""

    return value == "react-router" or value.startswith("react-router/")


def _is_react_router_npm_alias(value: str) -> bool:
    """Return whether an npm alias installs React Router under another name."""

    normalized = value.strip()
    return normalized == "npm:react-router" or normalized.startswith("npm:react-router@")


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


def _append_react_router_alias_markers(
    violations: list[str],
    *,
    filename: str,
    entries: Iterator[tuple[tuple[str, ...], str]],
) -> None:
    """Append diagnostics for npm aliases targeting the React Router package."""

    for path, value in entries:
        if _is_react_router_npm_alias(value):
            location = ".".join(path) or "<root>"
            violations.append(f"{filename}:{location}:react-router npm alias")


def _append_lockfile_named_alias_markers(
    violations: list[str],
    package_lock: dict[str, object],
) -> None:
    """Detect normalized lock entries whose install name hides React Router."""

    packages = package_lock.get("packages")
    if not isinstance(packages, dict):
        return
    for package_path, metadata in packages.items():
        if (
            not package_path
            or "node_modules/" not in str(package_path)
            or not isinstance(metadata, dict)
        ):
            continue
        installed_name = str(package_path).rsplit("node_modules/", maxsplit=1)[-1]
        if metadata.get("name") == "react-router" and installed_name != "react-router":
            violations.append(
                "package-lock.json:packages." f"{package_path}.name:react-router npm alias"
            )


def _package_lock_contains_target(
    package_lock: dict[str, object],
    *,
    label: str,
) -> bool:
    """Return whether one lockfile can produce the suppressed package tuple."""

    for section_name in ("packages", "dependencies"):
        section = package_lock.get(section_name, {})
        if not isinstance(section, dict):
            raise PremiseScanError(f"{label}:{section_name} must be a JSON object")
        for package_path, metadata in section.items():
            if not isinstance(metadata, dict):
                continue
            installed_name = str(package_path).rsplit("node_modules/", maxsplit=1)[-1]
            package_name = metadata.get("name", installed_name)
            if (
                package_name == _TARGET_REACT_ROUTER_PACKAGE
                and metadata.get("version") == _TARGET_REACT_ROUTER_VERSION
            ):
                return True
    return False


def _walk_package_lock_files(root: Path) -> Iterator[Path]:
    """Yield repository lockfiles without following excluded or symlinked trees."""

    def raise_traversal_error(error: OSError) -> None:
        raise PremiseScanError(f"unable to traverse repository root: {error}") from error

    for current_raw, dirnames, filenames in os.walk(
        root,
        topdown=True,
        onerror=raise_traversal_error,
        followlinks=False,
    ):
        current = Path(current_raw)
        retained_directories: list[str] = []
        for dirname in sorted(dirnames):
            if dirname in GLOBAL_EXCLUDED_DIRECTORIES or (
                "package.json" in filenames and dirname in ROOT_OUTPUT_DIRECTORIES
            ):
                continue
            directory = current / dirname
            label = _relative_label(directory, root)
            try:
                metadata = directory.lstat()
                directory.resolve(strict=True).relative_to(root)
            except (OSError, ValueError) as exc:
                raise PremiseScanError(f"unable to inspect directory {label}: {exc}") from exc
            if stat.S_ISLNK(metadata.st_mode):
                raise PremiseScanError(f"directory must not be a symlink: {label}")
            retained_directories.append(dirname)
        dirnames[:] = retained_directories
        for filename in ("npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock"):
            if filename in filenames:
                label = _relative_label(current / filename, root)
                raise PremiseScanError(
                    f"unsupported JavaScript lockfile cannot be scanned: {label}"
                )
        if "package-lock.json" in filenames:
            yield current / "package-lock.json"


def _shell_command_tokens(command: str, *, label: str, comments: bool) -> tuple[str, ...]:
    """Tokenize one bounded shell command or fail closed on malformed quoting."""

    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = "#" if comments else ""
    try:
        return tuple(lexer)
    except ValueError as exc:
        raise PremiseScanError(
            f"unable to parse delegated shell command in {label}: {exc}"
        ) from exc


def _delegated_shell_script_paths(
    command: str,
    *,
    root: Path,
    label: str,
    comments: bool = False,
) -> tuple[Path, ...]:
    """Resolve local scripts directly delegated from one package command."""

    if "\r" in command or "\n" in command:
        raise PremiseScanError(f"{label} uses an unsupported multiline shell command")
    tokens = _shell_command_tokens(command, label=label, comments=comments)
    if _SHELL_CONTROL_TOKENS.intersection(tokens):
        raise PremiseScanError(f"{label} uses an unsupported compound shell command")
    paths: list[Path] = []

    def append_local_path(candidate: str) -> None:
        if "$" in candidate or "\0" in candidate or ".." in Path(candidate).parts:
            raise PremiseScanError(
                f"{label} delegates to a shell script path that cannot be verified"
            )
        path = Path(candidate)
        if path.is_absolute():
            raise PremiseScanError(
                f"{label} delegates to an external shell script that cannot be verified"
            )
        paths.append(root / path)

    index = 0
    while index < len(tokens) and _SHELL_ASSIGNMENT_RE.match(tokens[index]):
        index += 1
    if index >= len(tokens):
        return ()

    executable = tokens[index]
    arguments = tokens[index + 1 :]
    if executable in _SHELL_UNSUPPORTED_COMMANDS:
        raise PremiseScanError(f"{label} uses an unsupported shell command: {executable}")
    if executable in _SHELL_SOURCE_BUILTINS:
        if not arguments:
            raise PremiseScanError(f"{label} has a source command without a script path")
        if "/" not in arguments[0]:
            raise PremiseScanError(
                f"{label} delegates to a shell script path that cannot be verified"
            )
        append_local_path(arguments[0])
        return tuple(paths)
    if _PYTHON_INTERPRETER_RE.fullmatch(Path(executable).name):
        for candidate in arguments:
            if candidate.startswith("-"):
                continue
            path = Path(candidate)
            if path.suffix != ".py" or ".." in path.parts:
                return ()
            append_local_path(candidate)
            break
        return tuple(paths)
    if Path(executable).name not in _SHELL_INTERPRETERS:
        if "/" in executable:
            if Path(executable).suffix in SOURCE_SUFFIXES | HTML_SUFFIXES:
                return ()
            append_local_path(executable)
        return tuple(paths)

    argument_index = 0
    while argument_index < len(arguments):
        candidate = arguments[argument_index]
        if candidate in {"-c", "--command"} or (
            candidate.startswith("-") and not candidate.startswith("--") and "c" in candidate[1:]
        ):
            raise PremiseScanError(f"{label} uses an unsupported shell command string")
        if candidate in _SHELL_OPTIONS_WITH_ARGUMENT:
            if argument_index + 1 >= len(arguments):
                raise PremiseScanError(f"{label} has a shell option without its required argument")
            argument_index += 2
            continue
        if (
            candidate.startswith("-")
            and not candidate.startswith("--")
            and candidate[-1:] in {"o", "O"}
        ):
            if argument_index + 1 >= len(arguments):
                raise PremiseScanError(f"{label} has a shell option without its required argument")
            argument_index += 2
            continue
        if candidate.startswith("-"):
            argument_index += 1
            continue
        append_local_path(candidate)
        break
    return tuple(paths)


def _sourced_shell_script_paths(text: str, *, root: Path, label: str) -> tuple[Path, ...]:
    """Return static local scripts sourced by one delegated shell script."""

    paths: list[Path] = []
    working_directory_changed = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line_label = f"{label}:{line_number}"
        tokens = _shell_command_tokens(raw_line, label=line_label, comments=True)
        if not tokens:
            continue
        index = 0
        while index < len(tokens) and _SHELL_ASSIGNMENT_RE.match(tokens[index]):
            index += 1
        if index >= len(tokens):
            continue
        command = tokens[index]
        if command == "cd":
            working_directory_changed = True
        if not _SHELL_SOURCE_BUILTINS.intersection(tokens):
            continue
        if command not in _SHELL_SOURCE_BUILTINS:
            if command in _SHELL_UNSUPPORTED_COMMANDS or _SHELL_CONTROL_TOKENS.intersection(tokens):
                raise PremiseScanError(f"{line_label} uses an unsupported sourced command")
            continue
        if working_directory_changed:
            raise PremiseScanError(f"{line_label} sources after an unsupported cwd change")
        paths.extend(
            _delegated_shell_script_paths(
                raw_line,
                root=root,
                label=line_label,
                comments=True,
            )
        )
    return tuple(paths)


def _reject_dynamic_shell_condition_values(text: str, *, label: str) -> None:
    """Fail closed on dynamic Node condition values in delegated shell scripts."""

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line_label = f"{label}:{line_number}"
        tokens = _shell_command_tokens(raw_line, label=line_label, comments=True)
        index = 0
        assignment_indexes: set[int] = set()
        while index < len(tokens) and _SHELL_ASSIGNMENT_RE.match(tokens[index]):
            assignment_indexes.add(index)
            index += 1
        if index < len(tokens) and tokens[index] == "export":
            assignment_indexes.update(
                candidate
                for candidate in range(index + 1, len(tokens))
                if _SHELL_ASSIGNMENT_RE.match(tokens[candidate])
            )
        for assignment_index in assignment_indexes:
            name, _, value = tokens[assignment_index].partition("=")
            if name == "NODE_OPTIONS" and ("$" in value or "`" in value):
                raise PremiseScanError(
                    f"NODE_OPTIONS value cannot be statically verified in {line_label}"
                )

        if index >= len(tokens) or Path(tokens[index]).name not in {"node", "nodejs"}:
            continue
        arguments = tokens[index + 1 :]
        for argument_index, argument in enumerate(arguments):
            value = argument.partition("=")[2] if argument.startswith("--conditions=") else ""
            if argument == "--conditions" and argument_index + 1 < len(arguments):
                value = arguments[argument_index + 1]
            if value and ("$" in value or "`" in value):
                raise PremiseScanError(
                    f"Node condition value cannot be statically verified in {line_label}"
                )


def _scan_delegated_script_file(
    path: Path,
    root: Path,
    *,
    active_paths: frozenset[Path] = frozenset(),
) -> list[str]:
    """Return RSC condition diagnostics from one delegated local script."""

    label = _relative_label(path, root)
    text = _validate_candidate(path, root)
    if path.suffix not in SOURCE_SUFFIXES and path.suffix != ".py":
        _reject_dynamic_shell_condition_values(text, label=label)
    resolved = path.resolve(strict=True)
    if resolved in active_paths:
        raise PremiseScanError(f"sourced script cycle detected at {label}")
    nested_active_paths = active_paths | {resolved}
    tokens = _shell_command_tokens(text, label=label, comments=True)
    violations: list[str] = []
    if any(_REACT_SERVER_CONDITION_RE.search(token) for token in tokens):
        violations.append(f"{label}:react-server condition")
    for sourced_path in _sourced_shell_script_paths(text, root=root, label=label):
        violations.extend(
            _scan_delegated_script_file(
                sourced_path,
                root,
                active_paths=nested_active_paths,
            )
        )
    return violations


def _npmrc_enables_react_server_condition(value: str) -> bool:
    """Return whether tokenized npm ``node-options`` enables ``react-server``."""

    try:
        tokens = tuple(shlex.split(value, comments=False, posix=True))
    except ValueError as exc:
        raise PremiseScanError(f"unable to parse .npmrc node-options: {exc}") from exc
    for index, option in enumerate(tokens):
        if option == "--conditions=react-server":
            return True
        if (
            option == "--conditions"
            and index + 1 < len(tokens)
            and tokens[index + 1] == "react-server"
        ):
            return True
    return False


def _scan_package_metadata(root: Path) -> list[str]:
    """Return RSC markers found in package metadata and scripts."""

    violations: list[str] = []
    package_json = _load_json_object(root / "package.json", root)

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
    _append_react_router_alias_markers(
        violations,
        filename="package.json",
        entries=_json_strings(dependency_sections),
    )

    package_imports = package_json.get("imports", {})
    if not isinstance(package_imports, dict):
        raise PremiseScanError("package.json:imports must be a JSON object")
    for path, target in _package_import_targets(package_imports, ("imports",)):
        if _is_react_router_package_target(target):
            location = ".".join(path)
            violations.append(f"package.json:{location}:react-router package target")

    scripts = package_json.get("scripts", {})
    if not isinstance(scripts, dict):
        raise PremiseScanError("package.json:scripts must be a JSON object")
    for script_name in sorted(scripts, key=str):
        command = scripts[script_name]
        if not isinstance(command, str):
            raise PremiseScanError(f"package.json:scripts.{script_name} must be a string")
        if _REACT_SERVER_CONDITION_RE.search(command):
            violations.append(f"package.json:scripts.{script_name}:react-server condition")
        label = f"package.json:scripts.{script_name}"
        for delegated_path in _delegated_shell_script_paths(
            command,
            root=root,
            label=label,
        ):
            violations.extend(_scan_delegated_script_file(delegated_path, root))

    package_lock = _load_json_object(root / "package-lock.json", root)
    for section in ("packages", "dependencies"):
        section_value = package_lock.get(section)
        if section_value is not None and not isinstance(section_value, dict):
            raise PremiseScanError(f"package-lock.json:{section} must be a JSON object")
    _append_package_markers(
        violations,
        filename="package-lock.json",
        entries=_json_strings(package_lock),
    )
    _append_react_router_alias_markers(
        violations,
        filename="package-lock.json",
        entries=_json_strings(package_lock),
    )
    _append_lockfile_named_alias_markers(violations, package_lock)

    npmrc_path = root / ".npmrc"
    try:
        npmrc_path.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise PremiseScanError(f"unable to inspect .npmrc: {exc}") from exc
    else:
        npmrc = _validate_candidate(npmrc_path, root)
        for raw_line in npmrc.splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", ";")):
                continue
            key, separator, value = line.partition("=")
            if (
                separator
                and key.strip().lower() == "node-options"
                and _npmrc_enables_react_server_condition(value)
            ):
                violations.append(".npmrc:node-options:react-server condition")
                break
    return violations


def _ends_with_regex_prefix_keyword(prefix: str) -> bool:
    """Return whether a source prefix permits a following regex literal."""

    for keyword in _REGEX_PREFIX_KEYWORDS:
        if not prefix.endswith(keyword):
            continue
        preceding_index = len(prefix) - len(keyword) - 1
        if preceding_index < 0:
            return True
        preceding = prefix[preceding_index]
        if preceding == "." or preceding in "$_\u200c\u200d" or preceding.isalnum():
            continue
        return True
    return False


def _has_unescaped_template_interpolation(value: str) -> bool:
    """Return whether a template body contains an executable ``${...}``."""

    index = 0
    while index < len(value) - 1:
        if value[index] == "\\":
            index += 2
            continue
        if value[index : index + 2] == "${":
            return True
        index += 1
    return False


def _starts_regex_literal(visible: _VisibleCharacters) -> bool:
    """Distinguish a regex literal slash from division using bounded context."""

    if visible.ends_with_postfix_update_operator:
        return False
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
        if character in _ECMASCRIPT_LINE_TERMINATORS:
            raise PremiseScanError(f"unterminated regular expression literal in {label}")
        if character == "\\":
            index += 1
            if index >= len(text):
                break
            if text[index] in _ECMASCRIPT_LINE_TERMINATORS:
                raise PremiseScanError(f"unterminated regular expression literal in {label}")
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

    code = _decode_javascript_source_escapes(code)
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
            while index < length and text[index] not in _ECMASCRIPT_LINE_TERMINATORS:
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
                replacement = "\n" if text[index] in _ECMASCRIPT_LINE_TERMINATORS else " "
                visible.append(replacement)
                code_buffer.append(replacement)
                index += 1
            else:
                raise PremiseScanError(f"unterminated block comment in {label}")
            continue

        if current in "+-" and following == current:
            visible.append_update_operator(
                current + following,
                postfix=(
                    not visible.has_trailing_line_terminator and not _starts_regex_literal(visible)
                ),
            )
            code_buffer.extend((current, following))
            index += 2
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
                if (
                    quote == "`"
                    and _has_unescaped_template_interpolation(literal_value)
                    and any(
                        fragment in _decode_javascript_source_escapes(literal_value)
                        for fragment in _TEMPLATE_INTERPOLATION_RSC_FRAGMENTS
                    )
                ):
                    raise PremiseScanError(f"RSC template interpolation in {label}")
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


def _is_react_router_module(token: _SourceToken) -> bool:
    """Return whether one literal token names the runtime package or a subpath."""

    if token.kind != "string":
        return False
    value = _decode_javascript_source_escapes(token.value)
    return value == "react-router" or value.startswith("react-router/")


def _static_string_concatenations(tokens: Sequence[_SourceToken]) -> tuple[str, ...]:
    """Fold contiguous ordinary-string ``+`` runs for marker matching."""

    composed: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.kind != "string":
            index += 1
            continue
        pieces = [_decode_javascript_source_escapes(token.value)]
        cursor = index
        while (
            cursor + 2 < len(tokens)
            and tokens[cursor + 1] == _SourceToken("punctuation", "+")
            and tokens[cursor + 2].kind == "string"
        ):
            pieces.append(_decode_javascript_source_escapes(tokens[cursor + 2].value))
            cursor += 2
        if len(pieces) > 1:
            composed.append("".join(pieces))
            index = cursor + 1
        else:
            index += 1
    return tuple(composed)


def _is_static_string_expression(tokens: Sequence[_SourceToken], start: int) -> bool:
    """Return whether one bounded expression is only static strings joined by ``+``."""

    index = start
    while index < len(tokens):
        token = tokens[index]
        if token.kind == "template":
            if _has_unescaped_template_interpolation(token.value):
                return False
        elif token.kind != "string":
            return False
        index += 1
        if index >= len(tokens) or tokens[index] != _SourceToken("punctuation", "+"):
            return index >= len(tokens) or tokens[index].value in ",;)]}"
        index += 1
    return False


def _reject_dynamic_condition_values(tokens: Sequence[_SourceToken], *, label: str) -> None:
    """Fail closed on dynamic ``NODE_OPTIONS`` or Node condition arguments."""

    for index, token in enumerate(tokens):
        is_node_options_property = (
            token == _SourceToken("identifier", "NODE_OPTIONS")
            and index > 0
            and tokens[index - 1] == _SourceToken("punctuation", ".")
            and index + 1 < len(tokens)
            and tokens[index + 1] == _SourceToken("punctuation", "=")
        )
        is_node_options_subscript = (
            token.kind == "string"
            and _decode_javascript_source_escapes(token.value) == "NODE_OPTIONS"
            and index > 0
            and tokens[index - 1] == _SourceToken("punctuation", "[")
            and index + 2 < len(tokens)
            and tokens[index + 1] == _SourceToken("punctuation", "]")
            and tokens[index + 2] == _SourceToken("punctuation", "=")
        )
        if is_node_options_property or is_node_options_subscript:
            rhs_index = index + (3 if is_node_options_subscript else 2)
            if not _is_static_string_expression(tokens, rhs_index):
                raise PremiseScanError(
                    f"NODE_OPTIONS value cannot be statically verified in {label}"
                )

        if token.kind not in {"string", "template"}:
            continue
        value = _decode_javascript_source_escapes(token.value)
        if value == "--conditions=":
            if not _is_static_string_expression(tokens, index):
                raise PremiseScanError(
                    f"Node condition value cannot be statically verified in {label}"
                )
        elif (
            value == "--conditions"
            and index + 1 < len(tokens)
            and tokens[index + 1] == _SourceToken("punctuation", ",")
            and not _is_static_string_expression(tokens, index + 2)
        ):
            raise PremiseScanError(f"Node condition value cannot be statically verified in {label}")


def _react_router_namespace_surfaces(tokens: Sequence[_SourceToken]) -> tuple[str, ...]:
    """Detect namespace-producing runtime forms for exact ``react-router``."""

    surfaces: set[str] = set()
    for index in range(len(tokens) - 5):
        if (
            tokens[index] != _SourceToken("identifier", "import")
            or tokens[index + 1] != _SourceToken("punctuation", "*")
            or tokens[index + 2] != _SourceToken("identifier", "as")
        ):
            continue
        for from_index in range(index + 4, len(tokens) - 1):
            token = tokens[from_index]
            if token == _SourceToken("punctuation", ";"):
                break
            if token != _SourceToken("identifier", "from"):
                continue
            module = tokens[from_index + 1]
            if _is_react_router_module(module):
                surfaces.add("react-router namespace import")
            break

    for index in range(len(tokens) - 1):
        token = tokens[index]
        if token.kind != "identifier" or token.value not in {"import", "require"}:
            continue
        preceded_by_dot = index > 0 and tokens[index - 1] == _SourceToken("punctuation", ".")
        is_module_require = (
            token.value == "require"
            and preceded_by_dot
            and index > 1
            and tokens[index - 2] == _SourceToken("identifier", "module")
            and (index < 3 or tokens[index - 3] != _SourceToken("punctuation", "."))
        )
        if preceded_by_dot and not is_module_require:
            continue
        if tokens[index + 1] != _SourceToken("punctuation", "("):
            continue
        single_string_literal = (
            index + 3 < len(tokens)
            and tokens[index + 2].kind == "string"
            and tokens[index + 3] == _SourceToken("punctuation", ")")
        )
        if not single_string_literal:
            surfaces.add(
                "dynamic import requires a single string literal"
                if token.value == "import"
                else "require requires a single string literal"
            )
            continue
        if _is_react_router_module(tokens[index + 2]):
            surfaces.add(
                "react-router dynamic import" if token.value == "import" else "react-router require"
            )

    for index, token in enumerate(tokens):
        if token != _SourceToken("identifier", "export"):
            continue
        for from_index in range(index + 1, len(tokens) - 1):
            candidate = tokens[from_index]
            if candidate == _SourceToken("punctuation", ";"):
                break
            if candidate != _SourceToken("identifier", "from"):
                continue
            if _is_react_router_module(tokens[from_index + 1]):
                surfaces.add("react-router re-export")
            break
    return tuple(sorted(surfaces))


def _decode_javascript_source_escapes(value: str) -> str:
    """Decode ECMAScript string/source escapes before security comparisons."""

    decoded: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(value):
            raise PremiseScanError("dangling escape in JavaScript source")

        escaped = value[index + 1]
        if escaped == "\r":
            index += 2
            if index < len(value) and value[index] == "\n":
                index += 1
            continue
        if escaped in {"\n", "\u2028", "\u2029"}:
            index += 2
            continue
        if escaped in "0123456789" and (
            escaped != "0" or (index + 2 < len(value) and value[index + 2].isdigit())
        ):
            raise PremiseScanError("legacy decimal escape in JavaScript source")
        if escaped in _JAVASCRIPT_SIMPLE_ESCAPES:
            decoded.append(_JAVASCRIPT_SIMPLE_ESCAPES[escaped])
            index += 2
            continue
        if escaped == "x":
            digits = value[index + 2 : index + 4]
            if len(digits) != 2 or any(digit not in _HEX_DIGITS for digit in digits):
                raise PremiseScanError("invalid hexadecimal escape in JavaScript source")
            decoded.append(chr(int(digits, 16)))
            index += 4
            continue
        if escaped == "u":
            if index + 2 < len(value) and value[index + 2] == "{":
                closing = value.find("}", index + 3)
                if closing < 0:
                    raise PremiseScanError("invalid Unicode escape in JavaScript source")
                digits = value[index + 3 : closing]
                if not 1 <= len(digits) <= 6 or any(digit not in _HEX_DIGITS for digit in digits):
                    raise PremiseScanError("invalid Unicode escape in JavaScript source")
                index = closing + 1
            else:
                digits = value[index + 2 : index + 6]
                if len(digits) != 4 or any(digit not in _HEX_DIGITS for digit in digits):
                    raise PremiseScanError("invalid Unicode escape in JavaScript source")
                index += 6
            codepoint = int(digits, 16)
            if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
                raise PremiseScanError("invalid Unicode escape in JavaScript source")
            decoded.append(chr(codepoint))
            continue

        decoded.append(escaped)
        index += 2
    return "".join(decoded)


def _scan_source_text(text: str, *, label: str) -> list[str]:
    """Return fixed RSC marker diagnostics for one JavaScript source body."""

    literals, visible, tokens = _source_analysis(text, label=label)
    _reject_dynamic_condition_values(tokens, label=label)
    decoded_visible = _decode_javascript_source_escapes(visible)
    composed_literals = _static_string_concatenations(tokens)
    marker_haystacks = (decoded_visible, *composed_literals)
    violations = [
        f"{label}:{marker}"
        for marker in RUNTIME_MARKERS
        if any(marker in haystack for haystack in marker_haystacks)
    ]
    if any(
        _REACT_SERVER_CONDITION_RE.search(_decode_javascript_source_escapes(literal))
        for literal in (*literals, *composed_literals)
    ):
        violations.append(f"{label}:react-server condition")
    violations.extend(f"{label}:{surface}" for surface in _react_router_namespace_surfaces(tokens))
    return violations


def _scan_source_file(path: Path, root: Path) -> list[str]:
    """Return fixed RSC marker diagnostics for one approved source file."""

    label = _relative_label(path, root)
    return _scan_source_text(_validate_candidate(path, root), label=label)


def _scan_html_file(path: Path, root: Path) -> list[str]:
    """Return RSC diagnostics from executable inline scripts."""

    label = _relative_label(path, root)
    parser = _InlineModuleScriptParser(label=label)
    parser.feed(_validate_candidate(path, root))
    violations: list[str] = []
    module_scripts, classic_scripts = parser.finish()
    for index, script in enumerate(module_scripts, start=1):
        violations.extend(
            _scan_source_text(
                script,
                label=f"{label}:inline-module-script[{index}]",
            )
        )
    for index, script in enumerate(classic_scripts, start=1):
        violations.extend(
            _scan_source_text(
                script,
                label=f"{label}:inline-classic-script[{index}]",
            )
        )
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
            if dirname in GLOBAL_EXCLUDED_DIRECTORIES:
                continue
            if relative_current == Path() and dirname in ROOT_OUTPUT_DIRECTORIES:
                continue
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
            retained_directories.append(dirname)
        dirnames[:] = retained_directories

        for filename in sorted(filenames):
            path = current / filename
            if path.suffix in SOURCE_SUFFIXES or path.suffix in HTML_SUFFIXES:
                yield path


def scan_repository(root: Path) -> list[str]:
    """Return stable violations, or raise when the absence proof is incomplete."""

    canonical_root = _canonical_root(root)
    violations = _scan_package_metadata(canonical_root)
    for source_path in _walk_source_files(canonical_root):
        if source_path.suffix in HTML_SUFFIXES:
            violations.extend(_scan_html_file(source_path, canonical_root))
        else:
            violations.extend(_scan_source_file(source_path, canonical_root))
    return sorted(set(violations))


def scan_repository_package_roots(root: Path) -> list[str]:
    """Scan every package root capable of producing the suppressed tuple."""

    canonical_root = _canonical_root(root)
    violations: list[str] = []
    for lock_path in _walk_package_lock_files(canonical_root):
        package_lock = _load_json_object(lock_path, canonical_root)
        lock_label = _relative_label(lock_path, canonical_root)
        if not _package_lock_contains_target(package_lock, label=lock_label):
            continue
        package_root = lock_path.parent
        prefix = (
            ""
            if package_root == canonical_root
            else f"{package_root.relative_to(canonical_root).as_posix()}/"
        )
        violations.extend(f"{prefix}{violation}" for violation in scan_repository(package_root))
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

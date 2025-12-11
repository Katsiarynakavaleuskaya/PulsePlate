"""Shared test utilities.

This module provides small helpers that are reused across multiple tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def create_selective_error(
    original_method: Callable[..., Any],
    target_path: Path,
    error_class: type[BaseException],
    message: str,
) -> Callable[..., Any]:
    """Return a function that raises only for the target path and delegates otherwise.

    Args:
        original_method: The original Path method to wrap (e.g., Path.mkdir, Path.write_text).
        target_path: The specific Path instance for which to raise an error.
        error_class: The exception class to raise (e.g., OSError, PermissionError).
        message: The error message to include in the raised exception.

    Returns:
        A wrapper function that selectively raises errors for ``target_path`` only.

    Example:
        >>> selective_mkdir = create_selective_error(
        ...     Path.mkdir, Path(\"/tmp/test\"), OSError, \"Permission denied\"
        ... )
        >>> selective_mkdir(Path(\"/tmp/test\"))  # Raises OSError
        >>> selective_mkdir(Path(\"/tmp/other\"))  # Delegates to original_method
    """

    def selective_error(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == target_path:
            raise error_class(message)
        return original_method(self, *args, **kwargs)

    return selective_error

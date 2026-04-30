from __future__ import annotations

from typing import Callable


def search_fn(pattern: str) -> list[str]:
    """Search the repository for test files or symbols matching pattern.

    Returns a list of matching file paths or grep result lines.

    TO IMPLEMENT: Replace this stub with a real implementation that searches
    the repository. Example using subprocess:

        import subprocess
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", "-l", pattern, "."],
            capture_output=True, text=True
        )
        return [line for line in result.stdout.splitlines() if line.strip()]
    """
    raise NotImplementedError(
        f"search_fn is a stub. Implement repository search for pattern: {pattern!r}. "
        "See SETUP.md §8 for implementation instructions."
    )


def read_file_fn(file_path: str, start_line: int, end_line: int) -> str:
    """Read lines start_line..end_line (1-indexed, inclusive) from file_path.

    Returns the file content as a string.

    TO IMPLEMENT: Replace this stub with a real file reading implementation.
    Example:

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return "".join(lines[start_line - 1:end_line])
    """
    raise NotImplementedError(
        f"read_file_fn is a stub. Implement file reading for {file_path!r} lines {start_line}-{end_line}. "
        "See SETUP.md §8 for implementation instructions."
    )

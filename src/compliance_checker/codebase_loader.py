"""Recursively load source files from a directory."""

from pathlib import Path

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv", ".tox", "dist", "build"}


def load_codebase(directory: str, extensions: list[str] | None = None) -> dict[str, str]:
    """Return {relative_path: file_contents} for all matching files."""
    if extensions is None:
        extensions = [".py"]

    root = Path(directory).resolve()
    files: dict[str, str] = {}

    for path in root.rglob("*"):
        # skip ignored directories
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in extensions:
            try:
                rel = str(path.relative_to(root))
                files[rel] = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass  # skip unreadable files

    return files

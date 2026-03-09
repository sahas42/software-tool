"""Recursively load source files from a directory, or fetch a digest via gitingest."""

from pathlib import Path
from gitingest import ingest

SKIP_DIRS = {"__pycache__", ".git", "node_modules", "venv", ".venv", ".tox", "dist", "build"}


def load_codebase(source: str, extensions: list[str] | None = None) -> dict[str, str] | str:
    """
    If source is a URL, returns a single text digest string via gitingest.
    If source is a local directory, returns {relative_path: file_contents}.
    """
    if source.startswith(("http://", "https://")):
        print(f"  Fetching repository digest from {source} via gitingest...")
        summary, tree, content = ingest(source)
        return content

    if extensions is None:
        extensions = [".py"]

    root = Path(source).resolve()
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

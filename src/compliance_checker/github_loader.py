"""
GitHub Private Repository Loader.

Uses the GitHub REST API with an OAuth access token to fetch
file contents from public AND private repositories.

Falls back to the public gitingest path if no token is provided.
"""

import os
from pathlib import Path
from typing import Optional

# Source file extensions the compliance checker cares about
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c",
    ".go", ".rb", ".rs", ".cs", ".php", ".swift", ".kt",
}

SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", "venv",
    ".venv", ".tox", "dist", "build", ".pytest_cache",
}


def _parse_repo_parts(repo_url: str) -> tuple[str, str]:
    """Extract owner/repo from a GitHub URL."""
    # Normalize: strip trailing .git and slashes
    url = repo_url.rstrip("/").removesuffix(".git")
    # Works for https://github.com/owner/repo
    parts = url.split("github.com/", 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot parse GitHub URL: {repo_url}")
    owner_repo = parts[1].strip("/")
    segments = owner_repo.split("/")
    if len(segments) < 2:
        raise ValueError(f"URL must include owner and repo name: {repo_url}")
    return segments[0], segments[1]


def load_private_repo(
    repo_url: str,
    access_token: str,
    extensions: Optional[list[str]] = None,
) -> dict[str, str]:
    """
    Fetch source files from a GitHub repo (public or private) using
    the authenticated GitHub REST API.

    Returns:
        dict mapping file path → file content (str)
    Raises:
        ValueError  – bad URL or repo not found / no permission
        RuntimeError – GitHub API error
    """
    from github import Github, GithubException  # PyGithub

    if extensions is None:
        extensions = list(SOURCE_EXTENSIONS)

    ext_set = {e if e.startswith(".") else f".{e}" for e in extensions}

    print(f"[GitHub OAuth Loader] Connecting to {repo_url} with token...")
    g = Github(access_token)

    try:
        owner, repo_name = _parse_repo_parts(repo_url)
        repo = g.get_repo(f"{owner}/{repo_name}")
    except GithubException as exc:
        raise ValueError(
            f"Cannot access repo '{repo_url}': {exc.data.get('message', str(exc))}"
        )

    files: dict[str, str] = {}
    _walk_tree(repo, "", ext_set, files)

    print(f"[GitHub OAuth Loader] Loaded {len(files)} source files.")
    return files


def _walk_tree(repo, path: str, ext_set: set, files: dict, depth: int = 0):
    """Recursively walk the repository tree and collect source files."""
    if depth > 10:  # Guard against absurdly deep repos
        return

    try:
        contents = repo.get_contents(path)
    except Exception as exc:
        print(f"  [warn] Could not read path '{path}': {exc}")
        return

    if not isinstance(contents, list):
        contents = [contents]

    for item in contents:
        # Skip ignored directories
        item_name = item.path.split("/")[-1]
        if item_name in SKIP_DIRS or item_name.startswith("."):
            continue

        if item.type == "dir":
            _walk_tree(repo, item.path, ext_set, files, depth + 1)
        elif item.type == "file":
            if Path(item.path).suffix in ext_set:
                try:
                    content = item.decoded_content.decode("utf-8", errors="replace")
                    files[item.path] = content
                except Exception as exc:
                    print(f"  [warn] Could not decode '{item.path}': {exc}")

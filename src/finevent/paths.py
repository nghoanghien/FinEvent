"""Path helpers for project artifacts."""

from __future__ import annotations

from pathlib import Path

from finevent.types import PathLike


def repo_root() -> Path:
    """Return the repository root for the src-layout package."""
    return Path(__file__).resolve().parents[2]


def resolve_project_path(path: PathLike, base_dir: Path | None = None) -> Path:
    """Resolve a project-relative path against the repository root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    root = base_dir or repo_root()
    return (root / candidate).resolve()


def ensure_directories(paths: list[PathLike]) -> list[Path]:
    """Create directories if missing and return resolved paths."""
    resolved: list[Path] = []
    for path in paths:
        resolved_path = resolve_project_path(path)
        resolved_path.mkdir(parents=True, exist_ok=True)
        resolved.append(resolved_path)
    return resolved

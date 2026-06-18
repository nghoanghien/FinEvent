"""Shared lightweight type aliases."""

from pathlib import Path
from typing import Any, TypeAlias

JsonDict: TypeAlias = dict[str, Any]
PathLike: TypeAlias = str | Path

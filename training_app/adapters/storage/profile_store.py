from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_profile(path: str | Path) -> Dict[str, Any]:
    """
    Load a user profile dict from JSON.
    Returns {} if file does not exist.
    """
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_profile(data: Dict[str, Any], path: str | Path) -> None:
    """
    Save a user profile dict to JSON (pretty printed).
    Creates parent directories.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

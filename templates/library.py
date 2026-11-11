"""The library's three JSON files, read once: brand tokens, templates and limits, and pins."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str) -> dict[str, Any]:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def tokens() -> dict[str, Any]:
    return _load("brand/tokens.json")


@lru_cache(maxsize=1)
def library() -> dict[str, Any]:
    return _load("library.json")


@lru_cache(maxsize=1)
def pins() -> dict[str, Any]:
    return _load("pins.json")


def size(name: str) -> tuple[int, int, dict[str, int]]:
    """(width, height, safe zone in px) of one of the three sizes."""
    s = tokens()["sizes"][name]
    return s["size"][0], s["size"][1], s["safe"]


def chain(template: str) -> list[tuple[str, str, Path]]:
    """[(name, engine, file)] in fallback order."""
    return [(n, e, HERE / f) for n, e, f in library()["chains"][template]]

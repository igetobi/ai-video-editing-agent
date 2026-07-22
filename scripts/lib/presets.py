"""Loader for the three configuration layers, resolved in order of specificity.

  1. config/brand.tokens.json   -> identity: colors, fonts, logo (swap once, rebrand all)
  2. config/formats.json        -> per-format rules (dims, which steps run, defaults)
  3. presets/<name>.json        -> a named look (signature-style, tiktok-raw-style, ...)

A style preset may reference brand tokens with ``{{token.path}}`` placeholders so a
single brand change propagates everywhere. ``resolve_style`` returns a fully-expanded
preset dict plus a fingerprint used to invalidate the render cache when the brand or
preset changes.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from . import project

_TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def _config_dir() -> Path:
    return project.repo_root() / "config"


def _presets_dir() -> Path:
    return project.repo_root() / "presets"


def load_json(path: Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.is_file():
        if default is not None:
            return default
        raise FileNotFoundError(p)
    return json.loads(p.read_text())


def load_brand() -> dict[str, Any]:
    return load_json(_config_dir() / "brand.tokens.json", default={})


def load_formats() -> dict[str, Any]:
    data = load_json(_config_dir() / "formats.json", default={})
    return {k: v for k, v in data.items() if not k.startswith("$")}


def load_format(name: str) -> dict[str, Any]:
    formats = load_formats()
    if name not in formats:
        raise KeyError(f"Unknown format '{name}'. Known: {', '.join(formats) or '(none)'}")
    return formats[name]


def _dig(tree: dict, dotted: str) -> Any:
    node: Any = tree
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _expand(value: Any, brand: dict) -> Any:
    """Recursively expand {{token.path}} references against brand tokens."""
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            found = _dig(brand, m.group(1))
            return str(found) if found is not None else m.group(0)
        return _TOKEN_RE.sub(repl, value)
    if isinstance(value, list):
        return [_expand(v, brand) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v, brand) for k, v in value.items()}
    return value


def resolve_style(name: str) -> tuple[dict[str, Any], str]:
    """Return (expanded_preset, fingerprint) for a named style preset."""
    brand = load_brand()
    raw = load_json(_presets_dir() / f"{name}.json")
    expanded = _expand(raw, brand)
    fp_blob = json.dumps({"brand": brand, "preset": expanded}, sort_keys=True, ensure_ascii=False)
    fingerprint = hashlib.sha256(fp_blob.encode("utf-8")).hexdigest()[:16]
    return expanded, fingerprint


def corrections_path() -> Path:
    return _presets_dir() / "caption-corrections.json"

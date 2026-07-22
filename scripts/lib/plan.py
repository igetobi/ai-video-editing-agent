"""The graphics plan: one "beat" per on-screen visual.

A beat is a time span on the *rough-cut timeline* plus everything needed to build
one HyperFrames composition for it (kind, copy, assets, preset, position). The plan
is reviewable, hand-editable JSON — the "second pass" step is literally editing beats
and re-running the builder.

Incremental re-render (the thing that makes iterating fast): each beat has an
``input_hash`` derived from its own fields + the preset it uses. build_graphics.py
only re-renders beats whose hash changed since the last render, so moving one
lower-third doesn't re-render the whole video.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Beat kinds map to composition templates in engine/templates/.
BEAT_KINDS = [
    "lower-third",     # name/title card, bottom third
    "top-card",        # explainer card, top half (short-explainer)
    "hook-card",       # full-bleed text hook (tiktok-raw)
    "callout",         # arrow/label pointing at screen content
    "list",            # animated bullet list
    "quote",           # pull quote
    "stat",            # big number / metric
    "b-roll",          # image/video cutaway overlay
    "logo-bug",        # persistent corner logo
    "zoom",            # ken-burns / punch-in emphasis (no graphic layer)
    "transition",      # shader/cut transition between beats
]


@dataclass
class Beat:
    id: str
    t_in: float                     # timeline seconds (on the rough cut)
    t_out: float
    kind: str = "lower-third"
    title: str = ""
    subtitle: str = ""
    body: list[str] = field(default_factory=list)   # bullets / lines
    assets: list[str] = field(default_factory=list)  # image/video/logo paths
    position: str = "auto"          # auto|top|bottom|center|tl|tr|bl|br
    preset: str = "signature-style"
    params: dict[str, Any] = field(default_factory=dict)  # freeform overrides
    enabled: bool = True
    note: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.t_out - self.t_in)

    def input_hash(self, preset_fingerprint: str = "") -> str:
        """Stable hash of everything that affects this beat's rendered output."""
        payload = {
            "kind": self.kind,
            "t_in": round(self.t_in, 3),
            "t_out": round(self.t_out, 3),
            "title": self.title,
            "subtitle": self.subtitle,
            "body": self.body,
            "assets": self.assets,
            "position": self.position,
            "preset": self.preset,
            "params": self.params,
            "preset_fp": preset_fingerprint,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "t_in": round(self.t_in, 3),
            "t_out": round(self.t_out, 3),
            "kind": self.kind,
            "title": self.title,
            "subtitle": self.subtitle,
            "body": self.body,
            "assets": self.assets,
            "position": self.position,
            "preset": self.preset,
            "params": self.params,
            "enabled": self.enabled,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Beat":
        return cls(
            id=d["id"],
            t_in=float(d["t_in"]),
            t_out=float(d["t_out"]),
            kind=d.get("kind", "lower-third"),
            title=d.get("title", ""),
            subtitle=d.get("subtitle", ""),
            body=d.get("body", []),
            assets=d.get("assets", []),
            position=d.get("position", "auto"),
            preset=d.get("preset", "signature-style"),
            params=d.get("params", {}),
            enabled=d.get("enabled", True),
            note=d.get("note", ""),
        )


@dataclass
class Plan:
    format: str = "long-form"
    fps: float = 30.0
    width: int = 1920
    height: int = 1080
    beats: list[Beat] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Plan":
        d = json.loads(Path(path).read_text())
        return cls(
            format=d.get("format", "long-form"),
            fps=float(d.get("fps", 30.0)),
            width=int(d.get("width", 1920)),
            height=int(d.get("height", 1080)),
            beats=[Beat.from_dict(b) for b in d.get("beats", [])],
            meta=d.get("meta", {}),
        )

    def save(self, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "format": self.format,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "beats": [b.to_dict() for b in self.beats],
            "meta": self.meta,
        }
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")

    def get(self, beat_id: str) -> Optional[Beat]:
        return next((b for b in self.beats if b.id == beat_id), None)

    def active(self) -> list[Beat]:
        return [b for b in self.beats if b.enabled and b.kind != "transition"]

"""The cut list (EDL): which spans of the raw clip survive, and in what order.

This is the single source of truth for the rough cut. The final timeline is simply
the kept segments concatenated in order. Because every segment carries the word
indices it came from, edits stay precise and reversible:

  * "trim the dead air"        -> drop/short-pad low-content segments
  * "you cut too close to X"   -> nudge a segment's ``src_in`` earlier (lead pad)
  * "leave that stumble out"   -> delete a segment or split and drop the middle
  * "put that line back"       -> re-add a segment from the raw source

Times are seconds in the *source* clip. Nothing here touches ffmpeg; apply_cuts.py
turns an EDL into a rendered rough cut.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class Segment:
    id: str
    src_in: float
    src_out: float
    text: str = ""
    word_start: Optional[int] = None  # inclusive flat word index in the transcript
    word_end: Optional[int] = None    # exclusive
    note: str = ""                    # human/agent annotation ("kept: hook")

    @property
    def duration(self) -> float:
        return max(0.0, self.src_out - self.src_in)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "src_in": round(self.src_in, 3),
            "src_out": round(self.src_out, 3),
            "text": self.text,
            "word_start": self.word_start,
            "word_end": self.word_end,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Segment":
        return cls(
            id=d["id"],
            src_in=float(d["src_in"]),
            src_out=float(d["src_out"]),
            text=d.get("text", ""),
            word_start=d.get("word_start"),
            word_end=d.get("word_end"),
            note=d.get("note", ""),
        )


@dataclass
class EDL:
    source: str
    fps: float = 30.0
    segments: list[Segment] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    # ---- IO -----------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "EDL":
        d = json.loads(Path(path).read_text())
        return cls(
            source=d["source"],
            fps=float(d.get("fps", 30.0)),
            segments=[Segment.from_dict(s) for s in d.get("segments", [])],
            meta=d.get("meta", {}),
        )

    def save(self, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "source": self.source,
            "fps": self.fps,
            "duration": round(self.timeline_duration, 3),
            "segments": [s.to_dict() for s in self.segments],
            "meta": self.meta,
        }
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")

    # ---- timeline math ------------------------------------------------
    @property
    def timeline_duration(self) -> float:
        return sum(s.duration for s in self.segments)

    def timeline_offset(self, seg_id: str) -> Optional[float]:
        """Start time of a segment on the *output* timeline."""
        offset = 0.0
        for s in self.segments:
            if s.id == seg_id:
                return offset
            offset += s.duration
        return None

    def source_to_timeline(self, src_t: float) -> Optional[float]:
        """Map a source-clip timestamp to its position on the output timeline."""
        offset = 0.0
        for s in self.segments:
            if s.src_in <= src_t < s.src_out:
                return offset + (src_t - s.src_in)
            offset += s.duration
        return None

    # ---- editing ------------------------------------------------------
    def renumber(self) -> None:
        for i, s in enumerate(self.segments):
            s.id = f"s{i:03d}"

    def get(self, seg_id: str) -> Optional[Segment]:
        return next((s for s in self.segments if s.id == seg_id), None)

    def pad(self, seg_id: str, lead: float = 0.0, tail: float = 0.0, clip_max: Optional[float] = None) -> None:
        """Extend a segment earlier (lead) and/or later (tail) in the source clip.

        This is the "you cut a little too close to that word" fix.
        """
        s = self.get(seg_id)
        if not s:
            raise KeyError(seg_id)
        s.src_in = max(0.0, s.src_in - lead)
        s.src_out = s.src_out + tail
        if clip_max is not None:
            s.src_out = min(s.src_out, clip_max)

    def delete(self, seg_id: str) -> None:
        self.segments = [s for s in self.segments if s.id != seg_id]

    def merge_adjacent(self, max_gap: float = 0.12) -> None:
        """Merge consecutive kept spans separated by <= max_gap in the source.

        Produces smoother audio than many hard micro-cuts.
        """
        if not self.segments:
            return
        merged = [self.segments[0]]
        for s in self.segments[1:]:
            last = merged[-1]
            if 0 <= s.src_in - last.src_out <= max_gap:
                last.src_out = s.src_out
                last.text = (last.text + " " + s.text).strip()
                if s.word_end is not None:
                    last.word_end = s.word_end
            else:
                merged.append(s)
        self.segments = merged
        self.renumber()

    def summary(self) -> str:
        n = len(self.segments)
        return f"{n} segments, {self.timeline_duration:.1f}s timeline (from source {self.source})"

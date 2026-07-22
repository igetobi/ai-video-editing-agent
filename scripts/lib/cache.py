"""Content-hash render cache — the engine behind fast incremental re-rendering.

The graphics builder renders one clip per beat. Rendering is the slow part, so we
never want to re-render a beat whose inputs did not change. This cache stores, per
beat id, the ``input_hash`` that produced the currently-rendered segment file.

On each build:
  * if the beat's current hash == cached hash AND the segment file exists -> skip
  * otherwise render, then record the new hash

That is exactly the "only render the part you changed" behavior — moving one card
re-renders one beat, not the whole video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


class RenderCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if self.path.is_file():
            try:
                self._data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                self._data = {}

    def cached_hash(self, beat_id: str) -> Optional[str]:
        return self._data.get(beat_id, {}).get("hash")

    def is_fresh(self, beat_id: str, current_hash: str, segment_file: Path) -> bool:
        return self.cached_hash(beat_id) == current_hash and Path(segment_file).is_file()

    def record(self, beat_id: str, current_hash: str, segment_file: Path) -> None:
        self._data[beat_id] = {"hash": current_hash, "file": str(segment_file)}

    def forget(self, beat_id: str) -> None:
        self._data.pop(beat_id, None)

    def prune(self, live_beat_ids: set[str]) -> list[str]:
        """Drop cache entries for beats that no longer exist. Returns removed ids."""
        removed = [bid for bid in self._data if bid not in live_beat_ids]
        for bid in removed:
            self._data.pop(bid, None)
        return removed

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2) + "\n")

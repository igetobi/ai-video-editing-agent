"""WhisperX word-level transcript model + brand/spelling corrections.

WhisperX emits JSON shaped like::

    {"segments": [{"start": .., "end": .., "text": "..",
                   "words": [{"word": "hi", "start": .., "end": .., "score": ..}, ...]}],
     "word_segments": [...]}

We normalize that into a flat, index-addressable list of Words. The flat index is
what the cut-list (edl.py) and captions reference, so an instruction like
"give word 42 a little more room before it" maps to an exact, deterministic edit.

Corrections (config/presets caption-corrections.json) are applied here, upstream of
everything, so a fixed brand spelling ("hyperframes" -> "HyperFrames") or a
misheard word flows into both the on-screen script and the captions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


@dataclass
class Word:
    text: str
    start: float
    end: float
    score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {"word": self.text, "start": self.start, "end": self.end, "score": self.score}


@dataclass
class Transcript:
    words: list[Word] = field(default_factory=list)
    language: str = "en"

    # ---- IO -----------------------------------------------------------
    @classmethod
    def from_whisperx(cls, path: Path) -> "Transcript":
        data = json.loads(Path(path).read_text())
        words: list[Word] = []
        segments = data.get("segments") or []
        for seg in segments:
            seg_words = seg.get("words")
            if seg_words:
                prev_end = seg.get("start", 0.0)
                for w in seg_words:
                    # WhisperX occasionally omits timings for numerals/punct.
                    start = w.get("start", prev_end)
                    end = w.get("end", start + 0.15)
                    words.append(
                        Word(
                            text=str(w.get("word", "")).strip(),
                            start=float(start),
                            end=float(end),
                            score=float(w.get("score", 1.0)),
                        )
                    )
                    prev_end = end
            else:
                # No word timings — fall back to segment granularity.
                words.append(
                    Word(
                        text=str(seg.get("text", "")).strip(),
                        start=float(seg.get("start", 0.0)),
                        end=float(seg.get("end", 0.0)),
                        score=1.0,
                    )
                )
        words = [w for w in words if w.text]
        return cls(words=words, language=data.get("language", "en"))

    @classmethod
    def load(cls, path: Path) -> "Transcript":
        data = json.loads(Path(path).read_text())
        words = [
            Word(text=w["word"], start=float(w["start"]), end=float(w["end"]), score=float(w.get("score", 1.0)))
            for w in data["words"]
        ]
        return cls(words=words, language=data.get("language", "en"))

    def save(self, path: Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        payload = {"language": self.language, "words": [w.to_dict() for w in self.words]}
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")

    # ---- views --------------------------------------------------------
    @property
    def duration(self) -> float:
        return self.words[-1].end if self.words else 0.0

    def text(self, start_idx: int = 0, end_idx: Optional[int] = None) -> str:
        end_idx = len(self.words) if end_idx is None else end_idx
        return " ".join(w.text for w in self.words[start_idx:end_idx]).strip()

    def slice(self, start_idx: int, end_idx: int) -> list[Word]:
        return self.words[start_idx:end_idx]

    # ---- corrections --------------------------------------------------
    def apply_corrections(self, corrections: "Corrections") -> int:
        """Apply brand/spelling corrections in place. Returns count changed."""
        changed = 0
        for w in self.words:
            new = corrections.fix(w.text)
            if new != w.text:
                w.text = new
                changed += 1
        return changed


class Corrections:
    """Case-insensitive whole-word replacements loaded from caption-corrections.json.

    Format::

        {"replace": {"hyperframes": "HyperFrames", "clod": "Claude"},
         "regex": [{"pattern": "\\byoutube\\b", "replace": "YouTube", "flags": "i"}]}
    """

    def __init__(self, replace: Optional[dict[str, str]] = None, regex: Optional[list[dict]] = None):
        self._replace = {k.lower(): v for k, v in (replace or {}).items()}
        self._regex = []
        for rule in regex or []:
            flags = re.IGNORECASE if "i" in rule.get("flags", "") else 0
            self._regex.append((re.compile(rule["pattern"], flags), rule["replace"]))

    @classmethod
    def load(cls, path: Path) -> "Corrections":
        if not Path(path).is_file():
            return cls()
        data = json.loads(Path(path).read_text())
        return cls(replace=data.get("replace"), regex=data.get("regex"))

    def fix(self, word: str) -> str:
        # Preserve surrounding punctuation while replacing the core token.
        m = re.match(r"^(\W*)(.*?)(\W*)$", word, re.DOTALL)
        if not m:
            return word
        lead, core, trail = m.groups()
        replaced = self._replace.get(core.lower())
        if replaced is not None:
            core = replaced
        for pattern, repl in self._regex:
            core = pattern.sub(repl, core)
        return f"{lead}{core}{trail}"


def find_word_index(words: Iterable[Word], text: str, near: float = 0.0) -> Optional[int]:
    """Best-effort locate the index of a spoken word by text, nearest to ``near`` sec.

    Lets natural-language edits ("more room before 'Claude'") resolve to an index.
    """
    text_l = text.strip().lower()
    best: Optional[int] = None
    best_dist = float("inf")
    for i, w in enumerate(words):
        if w.text.strip().lower().strip(".,!?") == text_l:
            dist = abs(w.start - near)
            if dist < best_dist:
                best, best_dist = i, dist
    return best

"""Pure cut-list logic: turn a word-level transcript into an EDL.

Silence removal is a side effect of how spans are built: a "span" is a maximal run
of kept words whose inter-word gaps stay under ``min_gap``. Wherever a gap exceeds
``min_gap`` (a pause) the span closes and the next span starts at the next word — so
the silence between them is never included. Filler hesitations (um/uh/erm) are
removed as words, which opens a gap and lets the same span logic cut them out.

Kept deliberately conservative: only unambiguous hesitations are auto-cut. Discourse
fillers (like/basically/actually) are *flagged* in each segment's note for review
instead of being auto-removed, because cutting them blindly mangles meaning. Set
``aggressive_filler`` to also cut those.
"""

from __future__ import annotations

from typing import Any

from .edl import EDL, Segment
from .transcript import Transcript

HARD_FILLERS = {"um", "uh", "erm", "hmm", "mmm", "umm", "uhh", "er", "ah", "uhm"}


def _norm(text: str) -> str:
    return text.lower().strip(" .,!?;:—-\"'")


def build_edl(t: Transcript, source: str, cfg: dict[str, Any], fps: float = 30.0) -> EDL:
    words = t.words
    min_gap = float(cfg.get("min_gap", 0.35))
    keep_pad = float(cfg.get("keep_pad", 0.08))
    merge_gap = float(cfg.get("merge_gap", 0.12))
    min_segment = float(cfg.get("min_segment", 0.20))
    drop_low_score = float(cfg.get("drop_low_score", 0.35))
    aggressive = bool(cfg.get("aggressive_filler", False))
    soft_fillers = {f.lower() for f in cfg.get("filler_words", []) if " " not in f}

    kept = [True] * len(words)
    soft_hits: dict[int, str] = {}
    for i, w in enumerate(words):
        norm = _norm(w.text)
        if not norm:
            kept[i] = False
            continue
        if norm in HARD_FILLERS:
            kept[i] = False
        elif w.score < drop_low_score and len(norm) <= 2:
            kept[i] = False  # low-confidence stray token (click/breath mis-transcribed)
        elif norm in soft_fillers:
            if aggressive:
                kept[i] = False
            else:
                soft_hits[i] = norm

    # Build spans over kept words.
    spans: list[dict] = []
    cur: dict | None = None
    for i, w in enumerate(words):
        if not kept[i]:
            continue
        if cur is None:
            cur = {"start_i": i, "end_i": i}
        else:
            gap = w.start - words[cur["end_i"]].end
            if gap > min_gap:
                spans.append(cur)
                cur = {"start_i": i, "end_i": i}
            else:
                cur["end_i"] = i
    if cur is not None:
        spans.append(cur)

    segments: list[Segment] = []
    for idx, s in enumerate(spans):
        fw = words[s["start_i"]]
        lw = words[s["end_i"]]
        src_in = max(0.0, fw.start - keep_pad)
        src_out = lw.end + keep_pad
        if src_out - src_in < min_segment:
            continue
        text = t.text(s["start_i"], s["end_i"] + 1)
        notes = [soft_hits[i] for i in range(s["start_i"], s["end_i"] + 1) if i in soft_hits]
        note = f"review filler: {', '.join(sorted(set(notes)))}" if notes else ""
        segments.append(
            Segment(
                id=f"s{idx:03d}",
                src_in=src_in,
                src_out=src_out,
                text=text,
                word_start=s["start_i"],
                word_end=s["end_i"] + 1,
                note=note,
            )
        )

    edl = EDL(source=source, fps=fps, segments=segments)
    edl.merge_adjacent(merge_gap)
    edl.renumber()
    edl.meta = {
        "source_duration": round(t.duration, 3),
        "timeline_duration": round(edl.timeline_duration, 3),
        "removed": round(t.duration - edl.timeline_duration, 3),
        "segment_count": len(edl.segments),
    }
    return edl

"""Pure cut-list logic: turn a word-level transcript into an EDL.

Silence removal is a side effect of how spans are built: a "span" is a maximal run
of kept words whose inter-word gaps stay under ``min_gap``. Wherever a gap exceeds
it (a pause) the span closes and the next span starts at the next word — so the
silence between them is never included. Filler hesitations (um/uh/erm) are removed
as words, which opens a gap and lets the same span logic cut them out.

Padding around each kept span is clamped to the *midpoint* of the gap to each
neighbour, so adjacent cuts can never overlap or re-introduce the silence/filler
that was removed between them.

A per-job ``excludes.json`` (bad takes / restarts) can drop spans by phrase,
``from → to`` range, or explicit source-time range — re-runnable and reversible.

Kept deliberately conservative: only unambiguous hesitations are auto-cut. Discourse
fillers (like/basically/actually) are *flagged* in each segment's note for review
instead of auto-removed. Set ``aggressive_filler`` to also cut those.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from .edl import EDL, Segment
from .transcript import Transcript, Word

HARD_FILLERS = {"um", "uh", "erm", "hmm", "mmm", "umm", "uhh", "er", "ah", "uhm", "mm", "mhm"}


def _norm(text: str) -> str:
    return text.lower().strip(" .,!?;:—-\"'")


def _tok(s: str) -> list[str]:
    return [t for t in (re.sub(r"[^a-z0-9]", "", w.lower()) for w in str(s).split()) if t]


def apply_excludes(words: list[Word], keep: list[bool], excludes: list) -> list[dict]:
    """Mark words matched by an excludes list as not-kept. Returns match report.

    Entry forms:
        "phrase" | {"phrase": "..."}      first contiguous word run matching
        {"from": "...", "to": "..."}      from start of `from` to end of next `to`
        {"start": s, "end": e}            explicit source-time range (seconds)
    """
    toks = [re.sub(r"[^a-z0-9]", "", w.text.lower()) for w in words]

    def find_seq(start: int, seq: list[str]) -> int:
        if not seq:
            return -1
        for i in range(start, len(toks) - len(seq) + 1):
            if toks[i:i + len(seq)] == seq:
                return i
        return -1

    report: list[dict] = []
    for ex in excludes:
        a = b = -1
        label = ""
        if isinstance(ex, str) or (isinstance(ex, dict) and ex.get("phrase")):
            seq = _tok(ex if isinstance(ex, str) else ex["phrase"])
            i = find_seq(0, seq)
            if i >= 0:
                a, b = i, i + len(seq)
            label = ex if isinstance(ex, str) else ex["phrase"]
        elif isinstance(ex, dict) and ex.get("from") and ex.get("to"):
            i = find_seq(0, _tok(ex["from"]))
            if i >= 0:
                st = _tok(ex["to"])
                j = find_seq(i, st)
                if j >= 0:
                    a, b = i, j + len(st)
            label = f"{ex['from']} … {ex['to']}"
        elif isinstance(ex, dict) and isinstance(ex.get("start"), (int, float)) and isinstance(ex.get("end"), (int, float)):
            for i, w in enumerate(words):
                mid = (w.start + w.end) / 2
                if ex["start"] <= mid <= ex["end"]:
                    if a < 0:
                        a = i
                    b = i + 1
            label = f"{ex['start']}-{ex['end']}s"
        if a >= 0 and b > a:
            for i in range(a, b):
                keep[i] = False
            report.append({"label": label, "matched": True, "removed": b - a})
        else:
            report.append({"label": label, "matched": False, "removed": 0})
    return report


def build_edl(
    t: Transcript, source: str, cfg: dict[str, Any], fps: float = 30.0,
    excludes: Optional[list] = None,
) -> EDL:
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
            kept[i] = False
        elif norm in soft_fillers:
            if aggressive:
                kept[i] = False
            else:
                soft_hits[i] = norm

    exclude_report: list[dict] = []
    if excludes:
        exclude_report = apply_excludes(words, kept, excludes)

    # Build spans (start/end word indices) over kept words.
    spans: list[dict] = []
    cur: dict | None = None
    for i, w in enumerate(words):
        if not kept[i]:
            continue
        if cur is None:
            cur = {"start_i": i, "end_i": i}
        elif w.start - words[cur["end_i"]].end > min_gap:
            spans.append(cur)
            cur = {"start_i": i, "end_i": i}
        else:
            cur["end_i"] = i
    if cur is not None:
        spans.append(cur)

    # Padding, clamped to the midpoint of the gap to each neighbour.
    segments: list[Segment] = []
    for idx, s in enumerate(spans):
        fw, lw = words[s["start_i"]], words[s["end_i"]]
        src_in = max(0.0, fw.start - keep_pad)
        src_out = lw.end + keep_pad
        if idx > 0:
            prev_end = words[spans[idx - 1]["end_i"]].end
            src_in = max(src_in, (prev_end + fw.start) / 2)
        if idx + 1 < len(spans):
            next_start = words[spans[idx + 1]["start_i"]].start
            src_out = min(src_out, (lw.end + next_start) / 2)
        if src_out - src_in < min_segment:
            continue
        text = t.text(s["start_i"], s["end_i"] + 1)
        notes = [soft_hits[i] for i in range(s["start_i"], s["end_i"] + 1) if i in soft_hits]
        note = f"review filler: {', '.join(sorted(set(notes)))}" if notes else ""
        segments.append(Segment(
            id=f"s{idx:03d}", src_in=src_in, src_out=src_out, text=text,
            word_start=s["start_i"], word_end=s["end_i"] + 1, note=note,
        ))

    edl = EDL(source=source, fps=fps, segments=segments)
    edl.merge_adjacent(merge_gap)
    edl.renumber()
    edl.meta = {
        "source_duration": round(t.duration, 3),
        "timeline_duration": round(edl.timeline_duration, 3),
        "removed": round(t.duration - edl.timeline_duration, 3),
        "segment_count": len(edl.segments),
        "excludes": exclude_report,
    }
    return edl
